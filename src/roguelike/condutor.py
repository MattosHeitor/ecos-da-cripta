"""O andamento de um combate, fora da tela: passa a vez, faz os inimigos agirem e espera os heróis decidirem.

    condutor = CondutorDoCombate(run, encontro)
    passo = condutor.passo()        # a tela chama quando as animações acabam; o combate anda um pedaço

O que passo() devolve:
    TURNO       começou o turno de alguém (início do turno: energia, veneno, perder a vez...)
    AGIU        um inimigo ou uma invocação agiu
    PASSOU      o turno acabou (o próximo passo começa outro)
    ESPERANDO   é a vez de um herói: quem o comanda manda um comando AgirNoCombate (tela, rede ou IA)
    FIM         acabou; condutor.recompensa já tem o XP, o ouro e o loot (Run.concluir_combate)

O condutor nunca decide pelos heróis: a decisão vira um comando (roguelike/comandos.py). Os passos dele dependem
só do estado, então a mesma semente + os mesmos comandos dão sempre o mesmo combate, em qualquer computador.

Decisores (quem escolhe pelo herói quando não é uma pessoa):
    DecisorIA   escolhe como o piloto automático (o melhor golpe pela nota; poção com pouca vida) sem usar o
                sorteio do combate: serve para o herói de quem desconectou e para o piloto automático.
"""

TURNO, AGIU, PASSOU, ESPERANDO, FIM = "turno", "agiu", "passou", "esperando", "fim"
LIMITE_DE_PASSOS = 20000              # trava de segurança de avancar_ate_decisao


class CondutorDoCombate:
    def __init__(self, run, encontro):
        self.run = run
        self.encontro = encontro
        self.combate = run.criar_combate(encontro)
        self.turno_em_andamento = False
        self.recompensa = None

    def esperando(self):
        """É a vez de um herói decidir?"""
        return self.turno_em_andamento and self.combate.vez_do_jogador()

    def heroi_da_vez(self):
        return self.combate.atual if self.esperando() else None

    def terminou(self):
        return self.recompensa is not None

    def passo(self):
        """Faz o combate andar um pedaço (ver o topo do arquivo)."""
        combate = self.combate
        if combate.resultado is not None:
            if self.recompensa is None:
                self.recompensa = self.run.concluir_combate(combate, self.encontro)
            return FIM
        if not self.turno_em_andamento:
            combate.comecar_turno()
            self.turno_em_andamento = True
            return TURNO
        if combate.pode_agir:
            if combate.vez_do_jogador():
                return ESPERANDO
            combate.agir_ia()
            return AGIU
        self.turno_em_andamento = False
        return PASSOU

    def avancar_ate_decisao(self):
        """Anda até a vez de um herói (ou o fim), sem animação. Devolve ESPERANDO ou FIM."""
        for _ in range(LIMITE_DE_PASSOS):
            passo = self.passo()
            if passo in (ESPERANDO, FIM):
                return passo
        raise RuntimeError("O combate não terminou (passos demais).")


# ============================================================
# DECISORES
# ============================================================

class Decisor:
    """Escolhe a ação de um herói na vez dele. comando() devolve um AgirNoCombate."""

    def comando(self, estado, heroi):
        raise NotImplementedError


class DecisorIA(Decisor):
    """Joga pelo herói como o piloto automático: poção com pouca vida, senão o golpe de nota mais alta.
    Não usa sorteio (nem o do combate): decidir aqui não muda o que acontece depois."""

    VIDA_PARA_POCAO = 0.35
    POCAO = "pocao_de_vida"

    def comando(self, estado, heroi):
        from roguelike.comandos import AgirNoCombate
        from roguelike.itens import item
        combate = estado.combate
        indice = estado.indice_do(heroi)
        if heroi.fracao_vida() < self.VIDA_PARA_POCAO and heroi.inventario.tem(self.POCAO) \
                and combate.proibicao(heroi, "item", item(self.POCAO), [heroi]) is None:
            return AgirNoCombate(heroi=indice, acao="item", chave=self.POCAO, alvo=estado.referencia(heroi))
        habilidade, alvo = melhor_acao(heroi, combate)
        if habilidade is None:
            return AgirNoCombate(heroi=indice, acao="concentrar")
        return AgirNoCombate(heroi=indice, acao="golpe", chave=habilidade.chave, alvo=estado.referencia(alvo))


def valor_da_acao(heroi, habilidade, nivel, combate):
    """Uma nota simples para cada habilidade: dano esperado, cura necessária ou buff."""
    from roguelike.efeitos_habilidade import bonus_de_atributos
    alvos = combate.alvos_validos(heroi, habilidade)
    if not alvos:
        return 0
    nota = 0.0
    for efeito in habilidade.efeitos:
        tipo = efeito.dados["tipo"]
        if tipo == "dano":
            minimo, maximo = efeito.no_nivel("dano", nivel)
            por_golpe = (minimo + maximo) / 2 + bonus_de_atributos(heroi, efeito.dados.get("escala"))
            quantos = 1 if habilidade.alvo in ("inimigo", "aleatorio") else len(alvos)
            nota += por_golpe * efeito.no_nivel("golpes", nivel, 1) * quantos
        elif tipo == "cura":
            feridos = [a for a in alvos if a.fracao_vida() < 0.5]
            nota += 12 * len(feridos)
        elif tipo == "reviver":
            nota += 30
        elif tipo == "invocar":
            nota += 6 if len(combate.invocacoes_de(heroi)) < 2 else 0
        elif tipo == "status" and not habilidade.ofensiva():
            novos = [a for a in alvos if not a.tem_status(efeito.dados["status"])]
            nota += 2 * len(novos)
        elif tipo == "status":
            nota += 2
    return nota - habilidade.custo * 0.8


def melhor_acao(heroi, combate):
    """(habilidade, alvo) de nota mais alta que não desobedece um édito, ou (None, None) para concentrar."""
    from roguelike.ia import IA
    melhor, melhor_nota = None, 0
    for habilidade, nivel in heroi.habilidades():
        if habilidade.pode_usar(heroi) and not IA.desobedece(heroi, combate, habilidade):     # Édito Real
            nota = valor_da_acao(heroi, habilidade, nivel, combate)
            if nota > melhor_nota:
                melhor, melhor_nota = habilidade, nota
    if melhor is None:
        return None, None
    alvos = combate.alvos_validos(heroi, melhor)
    alvos = [a for a in alvos if not IA.desobedece(heroi, combate, melhor, [a])] or alvos
    if melhor.alvo == "aliado":
        return melhor, min(alvos, key=lambda a: a.fracao_vida())
    if melhor.alvo == "inimigo":
        return melhor, min(alvos, key=lambda a: a.vida)       # termina quem está quase morrendo
    return melhor, (alvos[0] if melhor.escolhe_alvo() else None)
