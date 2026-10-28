"""Combate por turnos com vários lutadores de cada lado.

Como usar (é o que a tela de combate faz):

    combate = Combate(herois, inimigos, rng)
    combate.iniciar()
    while combate.resultado is None:
        lutador = combate.comecar_turno()        # rola iniciativa se a rodada acabou
        if not combate.pode_agir:
            continue                             # atordoado, congelado ou morreu no início
        if combate.vez_do_jogador():
            combate.usar_habilidade(lutador, habilidade, alvo)   # ou concentrar / usar_item
        else:
            combate.agir_ia()
        eventos = combate.pegar_eventos()        # para animar na tela

Regras principais:
- A cada rodada todos rolam iniciativa (dentro da faixa mínima/máxima);
  maior age primeiro e invocações agem sempre por último.
- No início do turno: chance de ganhar energia, passivas e status (veneno...).
- Cada golpe rola esquiva, crítico e bloqueio separadamente.
- Não dá para fugir nem pular turno: as ações são Lutar, Itens e Concentrar.
"""

import random

from roguelike import elementos
from roguelike.dados import regras
from roguelike.eventos import Evento
from roguelike.golpes import golpe as buscar_golpe
from roguelike.efeitos_habilidade import Contexto
from roguelike.status import criar_status, dados_do_status

LIMITE_VIDA_BAIXA = 0.25       # "dano_vida_baixa" (equipamento) vale em alvos com até esta fração da vida


class ResultadoGolpe:
    def __init__(self, alvo):
        self.alvo = alvo
        self.acertou = False
        self.esquivou = False
        self.critico = False
        self.bloqueou = False
        self.dano = 0


def ajuste_de_grupo(quantidade_de_herois):
    """Bônus dos inimigos pelo tamanho do grupo de heróis (tabela regras.json "grupo.por_tamanho")."""
    regra = regras()["grupo"]
    tamanho = min(max(1, quantidade_de_herois), regra["maximo"])
    return dict(regra["por_tamanho"][str(tamanho)])

def somar_ajustes(lutador, ajuste):
    for chave, valor in ajuste.items():
        lutador.ajustes[chave] = lutador.ajustes.get(chave, 0) + valor


class Combate:
    def __init__(self, herois, inimigos, rng=None, ajustar_grupo=True):
        self.rng = rng or random.Random()
        self.herois = list(herois)
        self.inimigos = list(inimigos)
        self.rodada = 0
        self.fila = []                 # quem ainda vai agir nesta rodada
        self.ordem_da_rodada = []      # a ordem completa da rodada (para a tela)
        self.atual = None
        self.pode_agir = False
        self.resultado = None          # None, "vitoria" ou "derrota"
        self.derrotados = []           # inimigos derrotados (para XP, ouro e loot)
        self.eventos = []              # tudo o que aconteceu
        self.grupo = None              # o Grupo da run (ouro e mochilas), quando o combate é de uma run
        self.ambientes = []            # água subindo, escuridão... (roguelike/ambiente.py), pela zona da run
        self.reforcos_chamados = 0     # inimigos que chegaram no meio da luta (Combate.reforcar)
        self.de_volta = None           # quem espera fora da luta e volta quando os outros caem (o Rei no trono)
        self.proxima_parte = None      # a luta continua depois desta (o Rei fugiu para o trono: vem a Rainha)
        self.status_nos_herois = set() # status que algum herói pegou nesta luta (o desafio "Imune" do Reino)
        self._novos = []               # eventos ainda não entregues à tela
        # Heróis caídos podem estar na lista (para serem revividos), mas não contam no ajuste
        vivos = [h for h in self.herois if h.esta_vivo()]
        self.ajuste_inimigos = ajuste_de_grupo(len(vivos)) if ajustar_grupo else {}
        for inimigo in self.inimigos:
            somar_ajustes(inimigo, self.ajuste_inimigos)
            inimigo.curar_tudo()

    # ============================================================
    # EVENTOS
    # ============================================================

    def registrar(self, evento):
        self.eventos.append(evento)
        self._novos.append(evento)
        return evento

    def pegar_eventos(self):
        """Eventos novos desde a última chamada."""
        novos, self._novos = self._novos, []
        return novos

    # ============================================================
    # LADOS
    # ============================================================

    def lado(self, lutador):
        return self.herois if lutador.lado == "herois" else self.inimigos

    def aliados_de(self, lutador):
        return [l for l in self.lado(lutador) if l.esta_vivo()]

    def oponentes_de(self, lutador):
        lado = self.inimigos if lutador.lado == "herois" else self.herois
        return [l for l in lado if l.esta_vivo()]

    def todos_vivos(self):
        return [l for l in self.herois + self.inimigos if l.esta_vivo()]

    def vez_do_jogador(self):
        """True se é a vez de um herói (não invocação) escolher a ação."""
        return (self.resultado is None and self.pode_agir and self.atual is not None
                and self.atual.lado == "herois" and not self.atual.eh_invocacao)

    # ============================================================
    # INÍCIO E RODADAS
    # ============================================================

    def iniciar(self):
        for lutador in self.herois + self.inimigos:
            if lutador.esta_vivo():
                lutador.preparar_para_combate()
            else:                                   # caído desde a luta anterior: nada dela sobra (recargas, energia),
                lutador.status, lutador.recargas, lutador.energia = {}, {}, 0   # igual à run carregada do save
        for lutador in self.todos_vivos():
            for passiva in lutador.passivas:
                passiva.inicio_do_combate(lutador, self)
        self.registrar(Evento("inicio", texto="O combate começou!"))
        for ambiente in self.ambientes:
            ambiente.iniciar(self)

    def rolar_iniciativa(self, lutador):
        minimo, maximo = lutador.faixa_de_iniciativa()
        return self.rng.randint(minimo, max(minimo, maximo))

    def nova_rodada(self):
        self.rodada += 1
        for lutador in self.todos_vivos():                 # antes da iniciativa (ex.: a roda da Rainha gira)
            for passiva in lutador.passivas:
                passiva.nova_rodada(lutador, self)
        rolagens = []
        for lutador in self.todos_vivos():
            if getattr(lutador, "objeto", False) or any(s.fora_da_fila() for s in lutador.status.values()):
                continue                                   # objetos (o Queijo Real) e os ratos de trás da roda
            valor = self.rolar_iniciativa(lutador)
            lutador.iniciativa_rolada = valor
            # Desempate: mais destreza, depois sorteio. Invocações sempre no fim.
            rolagens.append(((lutador.eh_invocacao, -valor, -lutador.atributo("destreza"), self.rng.random()), lutador))
        rolagens.sort(key=lambda par: par[0])
        self.fila = [lutador for _, lutador in rolagens]
        self.ordem_da_rodada = list(self.fila)
        self.registrar(Evento("rodada", valor=self.rodada, texto=f"— Rodada {self.rodada} —", ordem=list(self.fila)))
        for ambiente in self.ambientes:
            ambiente.nova_rodada(self)

    def oculto(self, lutador):
        """Escondido pelo ambiente (ex.: no escuro, sem luz): não pode ser alvo de golpes de um alvo só."""
        return any(ambiente.oculto(lutador, self) for ambiente in self.ambientes)

    def proximos(self):
        """Quem ainda vai agir nesta rodada (para a fila de turnos na tela)."""
        return [l for l in self.fila if l.esta_vivo()]

    # ============================================================
    # TURNOS
    # ============================================================

    def comecar_turno(self):
        """Passa a vez para o próximo lutador e aplica o início do turno."""
        if self.resultado is not None:
            return None
        self.atual = None
        while self.atual is None:
            if not self.proximos():
                self.nova_rodada()
            candidato = self.fila.pop(0)
            if candidato.esta_vivo():
                self.atual = candidato

        lutador = self.atual
        self.pode_agir = True
        self.registrar(Evento("turno", lutador, texto=f"Vez de {lutador.nome}."))

        # Energia: a parte inteira é garantida e o resto é chance
        ganho = lutador.stat("ganho_energia")
        energia = int(ganho) + (1 if self.rng.random() < ganho - int(ganho) else 0)
        energia += getattr(lutador, "ganho_de_energia_fixo", lambda: 0)()
        if energia > 0:
            self.dar_energia(lutador, energia, motivo="turno")
        lutador.passar_recargas()

        for passiva in lutador.passivas:
            passiva.inicio_do_turno(lutador, self)
        for status in list(lutador.status.values()):
            if lutador.esta_vivo():
                status.inicio_do_turno(lutador, self)

        if not lutador.esta_vivo() or lutador not in self.lado(lutador):    # caiu ou fugiu no início do turno
            self.pode_agir = False
            self.verificar_fim()
            return lutador

        impedimento = next((s for s in lutador.status.values() if s.perde_a_vez(self.rng)), None)
        febre = next((s for s in lutador.status.values() if s.delira()), None)
        if impedimento is not None:
            self.registrar(Evento("perdeu_vez", lutador, texto=f"{lutador.nome} está {impedimento.nome.lower()} e perdeu a vez!",
                                  status=impedimento.chave))
            self.encerrar_turno()
        elif febre is not None:
            self.delirar(lutador, febre)
        return lutador

    def delirar(self, lutador, status):
        """O lutador age fora de si neste turno; o status diz como (Status.delirio):
        Febre Negra (Peste no máximo): golpe e alvo sorteados entre todos, e a doença volta a um nível mais baixo;
        Encantado: um golpe de um alvo só num aliado (sozinho, nele mesmo)."""
        jeito = status.delirio()
        status.ao_delirar()
        self.registrar(Evento(jeito["evento"], lutador, lutador, texto=jeito["texto"].format(nome=lutador.nome),
                              status=status.chave))
        opcoes = [h for h, _ in lutador.habilidades()
                  if h.pode_usar(lutador) and h.alvo != "aliado_caido" and self.alvos_validos(lutador, h)]
        if jeito["so_golpes"]:
            opcoes = [h for h in opcoes if h.ofensiva() and h.escolhe_alvo()]
        if not opcoes:
            self.concentrar(lutador)
            return
        habilidade = self.rng.choice(opcoes)
        if jeito["alvos"] == "aliados":
            candidatos = [a for a in self.aliados_de(lutador) if a is not lutador] or [lutador]
        else:
            candidatos = self.todos_vivos()
        alvo = self.rng.choice(candidatos) if habilidade.escolhe_alvo() else None
        if not self.usar_habilidade(lutador, habilidade, alvo, qualquer_alvo=True):
            self.concentrar(lutador)

    def encerrar_turno(self):
        lutador = self.atual
        self.pode_agir = False
        if lutador is not None and lutador.esta_vivo():
            for chave, status in list(lutador.status.items()):
                if status.fim_do_turno():
                    self.remover_status(lutador, chave)
            if lutador.eh_invocacao and lutador.rodadas_restantes is not None:
                lutador.rodadas_restantes -= 1
                if lutador.rodadas_restantes <= 0:
                    self.registrar(Evento("dissipou", lutador, texto=f"{lutador.nome} se desfez."))
                    self.morrer(lutador, mensagem=False)
        self.verificar_fim()

    def verificar_fim(self):
        if self.resultado is not None:
            return True
        if not any(h.esta_vivo() and not h.eh_invocacao for h in self.herois):
            self.resultado = "derrota"
            self.registrar(Evento("fim", texto="O grupo foi derrotado...", resultado="derrota"))
        elif not any(i.esta_vivo() and not i.eh_invocacao and not getattr(i, "objeto", False) for i in self.inimigos):
            if self.de_volta is not None:                  # quem esperava no trono volta para a luta (o Rei dos Ratos)
                self.trazer_de_volta()
                return False
            self.resultado = "vitoria"
            for invocacao in [i for i in self.inimigos if i.eh_invocacao]:
                self.inimigos.remove(invocacao)
            self.registrar(Evento("fim", texto="Vitória!", resultado="vitoria"))
        return self.resultado is not None

    # ============================================================
    # AÇÕES
    # ============================================================

    def _pode_agir_agora(self, lutador):
        return self.resultado is None and self.pode_agir and lutador is self.atual

    def alvos_validos(self, usuario, habilidade):
        """Quem pode ser escolhido como alvo desta habilidade."""
        tipo = habilidade.alvo
        if tipo == "si":
            return [usuario]
        if tipo in ("aliado", "aliados"):
            return self.aliados_de(usuario)
        if tipo == "aliado_caido":
            return [l for l in self.lado(usuario) if not l.esta_vivo() and not l.eh_invocacao]

        oponentes = [o for o in self.oponentes_de(usuario) if not any(s.intocavel() for s in o.status.values())]
        if tipo != "inimigo":
            return oponentes
        # no escuro: só os que se vê (se todos estão ocultos, golpeia às cegas: o alvo esquiva mais)
        oponentes = [o for o in oponentes if not self.oculto(o)] or oponentes
        visiveis = [o for o in oponentes if not any(s.esconde() for s in o.status.values())] or oponentes
        provocadores = [o for o in visiveis if any(s.provoca() for s in o.status.values())]
        return provocadores or visiveis

    def usar_habilidade(self, usuario, habilidade, alvo=None, qualquer_alvo=False):
        """Usa uma habilidade (objeto ou chave). Devolve False se a ação não vale.

        qualquer_alvo: aceita qualquer lutador vivo como alvo (Febre Negra: golpe sem rumo)."""
        if isinstance(habilidade, str):
            habilidade = buscar_golpe(habilidade)
        nivel = usuario.nivel_da(habilidade.chave)
        if not self._pode_agir_agora(usuario) or nivel == 0 or not habilidade.pode_usar(usuario):
            return False
        validos = self.alvos_validos(usuario, habilidade)
        if habilidade.escolhe_alvo():
            if alvo is None and len(validos) == 1:
                alvo = validos[0]
            if alvo not in validos and not (qualquer_alvo and alvo is not None and alvo.esta_vivo()):
                return False
            alvos = [self.interceptar(usuario, habilidade, alvo)]
        else:
            alvos = validos
        if not alvos:
            return False

        usuario.energia -= habilidade.custo
        if habilidade.custo_vida:
            usuario.vida = max(1, usuario.vida - habilidade.custo_vida)
        if habilidade.recarga:
            usuario.recargas[habilidade.chave] = habilidade.recarga
        self.registrar(Evento("habilidade", usuario, alvos[0] if len(alvos) == 1 else None,
                              texto=f"{usuario.nome} usou {habilidade.nome}!", habilidade=habilidade,
                              alvos=list(alvos)))
        self.aplicar_efeitos(usuario, habilidade.efeitos, alvos, nivel)
        self.luz_que_alivia(usuario, habilidade, alvos)
        for ambiente in self.ambientes:                              # ex.: o Rato Nadador vem à tona
            ambiente.depois_da_acao(usuario, habilidade, self)
        if not qualquer_alvo:                                        # (no delírio ninguém responde pelo que faz)
            self.vigiar_editos(usuario, "habilidade", habilidade, alvos + ([alvo] if alvo is not None else []))

        # Atacar tira a furtividade
        if habilidade.ofensiva() and usuario.tem_status("furtivo"):
            self.remover_status(usuario, "furtivo")
        self.encerrar_turno()
        return True

    # ---------------- éditos (leis do Rei dos Ratos) ----------------
    def proibicao(self, usuario, tipo, coisa, alvos=()):
        """O édito que esta ação desobedece: (dono, status) ou None. Os éditos ficam nos oponentes do usuário."""
        for dono in self.oponentes_de(usuario):
            for status in dono.status.values():
                if status.proibe(dono, usuario, tipo, coisa, list(alvos)):
                    return dono, status
        return None

    def vigiar_editos(self, usuario, tipo, coisa, alvos=()):
        """Depois da ação: quem desobedeceu um édito leva o castigo (regras.json "editos")."""
        quebrado = self.proibicao(usuario, tipo, coisa, alvos)
        if quebrado is None or not usuario.esta_vivo():
            return
        dono, status = quebrado
        dano = max(1, round(usuario.vida_maxima * regras()["editos"]["castigo"]))
        self.registrar(Evento("desobedeceu", dono, usuario, dano, texto=f"{usuario.nome} desobedeceu o édito "
                                                                       f"\"{status.nome}\"!", status=status.chave))
        self.causar_dano_direto(usuario, dano, dono, motivo="edito", adiavel=False)

    def interceptar(self, usuario, habilidade, alvo):
        """Um guarda-costas do lado do alvo pode entrar na frente de um golpe de um alvo só (Guarda Real Roedor)."""
        if not habilidade.ofensiva() or alvo.lado == usuario.lado:
            return alvo
        for guarda in self.aliados_de(alvo):
            for passiva in guarda.passivas:
                novo = passiva.interceptar(guarda, usuario, habilidade, alvo, self)
                if novo is not None:
                    return novo
        return alvo

    def luz_que_alivia(self, usuario, habilidade, alvos):
        """Curas de luz (elemento luz ou regras.json "curas_de_luz") tiram níveis dos status com "luz_alivia" (a Peste)."""
        if habilidade.elemento != "luz" and habilidade.chave not in regras().get("curas_de_luz", []):
            return
        curados = []
        for efeito in habilidade.efeitos:
            if efeito.dados["tipo"] == "cura":
                curados += [usuario] if efeito.dados.get("em") == "usuario" else list(alvos)
        for alvo in [a for i, a in enumerate(curados) if a not in curados[:i] and a.esta_vivo()]:
            for chave in [c for c in alvo.status if dados_do_status(c).get("luz_alivia")]:
                self.aliviar(alvo, chave, dados_do_status(chave)["luz_alivia"], usuario)

    def concentrar(self, usuario):
        """Recupera energia e passa a vez."""
        if not self._pode_agir_agora(usuario):
            return False
        quantidade = regras()["energia"]["concentrar"] + int(usuario.bonus("energia_concentrar"))
        self.registrar(Evento("concentrar", usuario, texto=f"{usuario.nome} se concentrou."))
        self.dar_energia(usuario, quantidade, motivo="concentrar")
        self.encerrar_turno()
        return True

    def usar_item(self, usuario, item, alvo=None):
        """Usa um consumível (precisa ter .nome, .alvo e .efeitos). Quem chama tira do inventário."""
        if not self._pode_agir_agora(usuario):
            return False
        alvos = self.alvos_do_item(usuario, item, alvo)
        if not alvos:
            return False
        self.registrar(Evento("item", usuario, alvos[0] if len(alvos) == 1 else None,
                              texto=f"{usuario.nome} usou {item.nome}.", item=item, alvos=list(alvos)))
        self.aplicar_efeitos(usuario, item.efeitos, alvos, 1)
        self.vigiar_editos(usuario, "item", item, alvos)
        self.encerrar_turno()
        return True

    def alvos_do_item(self, usuario, item, alvo=None):
        validos = self.alvos_validos(usuario, item)
        if item.alvo in ("inimigo", "aliado", "aliado_caido"):
            return [alvo] if alvo in validos else ([validos[0]] if alvo is None and len(validos) == 1 else [])
        return validos

    def agir_ia(self):
        """O lutador da vez (inimigo ou invocação) escolhe e faz a ação."""
        from roguelike.ia import ia_do
        lutador = self.atual
        if not self._pode_agir_agora(lutador):
            return False
        escolha = ia_do(lutador).escolher(lutador, self)
        if escolha.habilidade is None or not self.usar_habilidade(lutador, escolha.habilidade, escolha.alvo):
            return self.concentrar(lutador)
        return True

    def aplicar_efeitos(self, usuario, efeitos, alvos, nivel):
        contexto = Contexto()
        for efeito in efeitos:
            efeito.aplicar(self, usuario, alvos, nivel, contexto)
        return contexto

    # ============================================================
    # GOLPES E DANO
    # ============================================================

    def golpear(self, atacante, alvo, dano_base, ignora_esquiva=False, ignora_bloqueio=False, roubo=0,
                direto=True, revide=False, elemento=None):
        """Um golpe: rola esquiva, crítico e bloqueio, e aplica o dano (com a afinidade ao elemento)."""
        elemento = elemento or elementos.PADRAO
        resultado = ResultadoGolpe(alvo)
        if not alvo.esta_vivo():
            return resultado

        esquiva = alvo.stat("chance_esquiva") - atacante.stat("precisao")      # precisão anula parte da esquiva
        esquiva += sum(ambiente.esquiva_extra(atacante, alvo, self) for ambiente in self.ambientes)
        if not ignora_esquiva and self.rng.random() < esquiva:
            resultado.esquivou = True
            self.registrar(Evento("esquiva", atacante, alvo, texto=f"{alvo.nome} esquivou!"))
            return resultado

        dano = dano_base
        if self.rng.random() < atacante.stat("chance_critico") + alvo.stat("critico_recebido"):
            resultado.critico = True
            dano *= atacante.stat("dano_critico")
        dano *= (1 + atacante.stat("dano_causado")) * (1 + alvo.stat("dano_recebido"))
        dano *= elementos.multiplicador(atacante, alvo, elemento)
        dano *= alvo.multiplicador_contra(direto)                           # bandos: área machuca mais
        for ambiente in self.ambientes:                                     # ex.: água funda enfraquece o fogo
            dano *= ambiente.multiplicador_de_dano(atacante, alvo, elemento, self)
        if alvo.fracao_vida() <= LIMITE_VIDA_BAIXA:                         # ex.: o Machado do Carrasco
            dano *= 1 + atacante.bonus("dano_vida_baixa")
        if not ignora_bloqueio and self.rng.random() < alvo.stat("chance_bloqueio"):
            resultado.bloqueou = True
            dano *= 1 - alvo.stat("reducao_bloqueio")
        defesa = max(0, round(alvo.stat("defesa")) - round(atacante.bonus("penetracao")))    # ex.: a Lança de Agulha
        dano = max(1, round(dano) - defesa)

        resultado.acertou = True
        resultado.dano = self.causar_dano(alvo, dano, atacante, motivo="golpe",
                                          critico=resultado.critico, bloqueou=resultado.bloqueou,
                                          elemento=elemento, efetividade=elementos.efetividade(alvo, elemento))

        roubo_total = roubo + atacante.stat("roubo_vida")
        if roubo_total > 0 and resultado.dano > 0 and atacante.esta_vivo():
            self.curar(atacante, int(resultado.dano * roubo_total), atacante, motivo="roubo")
        for passiva in atacante.passivas:
            passiva.ao_causar_dano(atacante, alvo, resultado.dano, self)
        if direto and not revide:
            for status in list(alvo.status.values()):
                status.ao_ser_golpeado(alvo, atacante, self)
        return resultado

    def causar_dano(self, alvo, dano, origem, motivo="golpe", critico=False, bloqueou=False, adiavel=True,
                    elemento=None, efetividade=None):
        """Tira vida do alvo (passando por passivas e escudos). Devolve o dano real.

        elemento/efetividade ("fraco", "resiste" ou None) só vão para o evento (a tela mostra "Fraco!").
        """
        if not alvo.esta_vivo() or dano <= 0:
            return 0
        if adiavel and origem is not None and origem is not alvo:
            for passiva in alvo.passivas:
                dano = passiva.dano_vindo_de(alvo, dano, origem, self)
        if adiavel:
            for passiva in alvo.passivas:
                dano = passiva.reduzir_dano(alvo, dano, self, elemento)
        for chave, status in list(alvo.status.items()):
            antes = dano
            dano = status.absorver(dano)
            if antes != dano:
                self.registrar(Evento("escudo", origem, alvo, antes - dano, f"O escudo de {alvo.nome} absorveu {antes - dano}."))
            if status.duracao <= 0:
                self.remover_status(alvo, chave)
        real = min(dano, alvo.vida)
        alvo.vida -= real
        if real <= 0:
            return 0

        nomes ={"golpe": "", "sangramento": " (sangramento)", "veneno": " (veneno)", "queimadura": " (queimadura)",
                 "espinhos": " (espinhos)", "dano_adiado": " (dano adiado)",
                 "explosao": " (explosão)", "peste": " (peste)", "edito": " (castigo do édito)"}
        texto = f"{alvo.nome} sofreu {real} de dano{nomes.get(motivo, '')}"
        texto += "  CRÍTICO!" if critico else ""
        texto += "  (bloqueou)" if bloqueou else ""
        texto += {"fraco": "  Fraco!", "resiste": "  (resistiu)"}.get(efetividade, "")
        self.registrar(Evento("dano", origem, alvo, real, texto, critico=critico, bloqueou=bloqueou, motivo=motivo,
                              elemento=elemento, efetividade=efetividade))

        if real > 0:
            for passiva in alvo.passivas:
                passiva.ao_receber_dano(alvo, real, self)
        if alvo.vida <= 0:
            if any(p.evitar_morte(alvo, self) for p in alvo.passivas):
                self.registrar(Evento("sobreviveu", alvo, alvo, alvo.vida, f"{alvo.nome} se recusou a cair!"))
            else:
                self.morrer(alvo)
        return real

    # Status como veneno usam o mesmo caminho (sem crítico nem bloqueio)
    causar_dano_direto = causar_dano

    def morrer(self, lutador, mensagem=True):
        lutador.vida = 0
        lutador.status = {}
        if mensagem:
            self.registrar(Evento("morte", None, lutador, texto=f"{lutador.nome} caiu!"))
            # Mortos-vivos: uma passiva pode trazer o lutador de volta (uma vez por combate)
            for passiva in [] if lutador.eh_invocacao else lutador.passivas:
                percentual = passiva.renascer(lutador, self)
                if percentual:
                    self.reviver(lutador, percentual, lutador, texto=f"{lutador.nome} se ergueu do túmulo!",
                                 renasceu=True)
                    return
            for passiva in lutador.passivas:                 # ex.: o Fungo estoura em esporos
                passiva.ao_morrer(lutador, self)
            for aliado in self.aliados_de(lutador):          # ex.: a Rainha caiu e o Rei desce do trono
                for passiva in aliado.passivas:
                    passiva.aliado_caiu(aliado, lutador, self)
        if lutador.eh_invocacao:
            lado = self.lado(lutador)
            if lutador in lado:
                lado.remove(lutador)
        elif lutador.lado == "inimigos" and lutador not in self.derrotados:
            self.derrotados.append(lutador)

    def fugir(self, lutador, texto=None):
        """O lutador sai da luta vivo (ex.: o Rato Ladrão com o que roubou): não conta como derrotado."""
        lado = self.lado(lutador)
        if lutador in lado:
            lado.remove(lutador)
        if lutador in self.fila:
            self.fila.remove(lutador)
        lutador.status = {}
        self.registrar(Evento("fugiu", lutador, lutador, texto=texto or f"{lutador.nome} fugiu!"))
        self.verificar_fim()

    def curar(self, alvo, valor, origem, motivo="cura"):
        if not alvo.esta_vivo() or valor <= 0:
            return 0
        valor = round(valor * alvo.stat("cura_recebida"))
        real = max(0, min(valor, alvo.vida_maxima - alvo.vida))
        alvo.vida += real
        if real > 0:
            self.registrar(Evento("cura", origem, alvo, real, f"{alvo.nome} recuperou {real} de vida.", motivo=motivo))
        return real

    def dar_energia(self, alvo, quantidade, motivo=""):
        antes = alvo.energia
        alvo.energia = max(0, min(alvo.energia_maxima, alvo.energia + quantidade))
        ganho = alvo.energia - antes
        if ganho:
            self.registrar(Evento("energia", alvo, alvo, ganho, f"{alvo.nome} ganhou {ganho} de energia.", motivo=motivo))
        return ganho

    # ============================================================
    # STATUS, REVIVER E INVOCAÇÕES
    # ============================================================

    def aplicar_status(self, alvo, chave, duracao=None, valor=0, acumulos=1, origem=None):
        if not alvo.esta_vivo():
            return None
        if alvo.imune(chave):
            self.registrar(Evento("resistiu", origem, alvo, texto=f"{alvo.nome} resistiu!", status=chave))
            return None
        resistencia = alvo.bonus(f"resiste_{chave}")        # ex.: raças contra a Peste (negativo = pega mais)
        if resistencia > 0 and self.rng.random() < resistencia:
            self.registrar(Evento("resistiu", origem, alvo, texto=f"{alvo.nome} resistiu!", status=chave))
            return None
        if resistencia < 0 and self.rng.random() < -resistencia:
            acumulos += 1
        novo = criar_status(chave, duracao, valor, acumulos, origem)
        novo.duracao += self.duracao_extra(novo, origem)
        if chave in alvo.status:
            alvo.status[chave].juntar(novo)
        else:
            alvo.status[chave] = novo
        atual = alvo.status[chave]
        if alvo in self.herois:
            self.status_nos_herois.add(chave)
        if alvo is self.atual and self.pode_agir:
            atual.pular_proximo_fim = True
        self.registrar(Evento("status", origem, alvo, texto=f"{alvo.nome}: {atual.rotulo()}", status=chave))
        return atual

    @staticmethod
    def duracao_extra(status, origem):
        """Turnos a mais vindos de quem aplica (itens): "duracao_bencaos" nos status positivos e
        "duracao_maldicoes" nos negativos que não tiram a vez nem são marcadores."""
        if origem is None or not hasattr(origem, "stat"):
            return 0
        classe = dados_do_status(status.chave)["classe"]
        if status.tipo == "positivo" and classe != "marcador":
            return int(origem.stat("duracao_bencaos"))
        if status.tipo == "negativo" and classe not in ("perde_vez", "marcador"):
            return int(origem.stat("duracao_maldicoes"))
        return 0

    def marcar(self, alvo, chave, ligado, origem=None):
        """Liga ou desliga um status marcador sem anunciar (ex.: quem está atrás da roda da Rainha, a cada giro)."""
        if ligado and chave not in alvo.status:
            alvo.status[chave] = criar_status(chave, origem=origem)
        elif not ligado:
            alvo.status.pop(chave, None)

    def remover_status(self, alvo, chave):
        status = alvo.status.pop(chave, None)
        if status is not None:
            self.registrar(Evento("status_fim", None, alvo, texto=f"{status.nome} de {alvo.nome} acabou.", status=chave))

    def purificar(self, alvo, quantidade=99):
        negativos = [chave for chave, s in alvo.status.items() if s.tipo == "negativo"]
        for chave in negativos[:quantidade]:
            self.aliviar(alvo, chave)

    def aliviar(self, alvo, chave, niveis=1, origem=None):
        """Tira o status (ou só alguns níveis, na Peste: Status.aliviar decide)."""
        status = alvo.status.get(chave)
        if status is None:
            return
        if status.aliviar(niveis):
            self.remover_status(alvo, chave)
        else:
            self.registrar(Evento("alivio", origem, alvo, niveis, f"{status.nome} de {alvo.nome} cedeu: {status.rotulo()}.",
                                  status=chave))

    def reviver(self, alvo, percentual, origem=None, texto=None, **extras):
        if alvo.esta_vivo() or alvo.eh_invocacao:
            return False
        if alvo in self.derrotados:                  # inimigo reerguido (Rato Xamã): só conta quando cair de novo
            self.derrotados.remove(alvo)
        alvo.status = {}
        alvo.vida = max(1, round(alvo.vida_maxima * percentual))
        alvo.energia = alvo.energia_inicial()
        self.registrar(Evento("reviver", origem, alvo, alvo.vida, texto or f"{alvo.nome} voltou à luta!", **extras))
        return True

    def reforcar(self, dono, chaves, maximo=6, limite_na_luta=None, texto="{nome} atendeu ao chamado!", preparar=None):
        """Inimigos novos DE VERDADE entram na luta do lado do dono (o Arauto Roedor chama reforços): dão XP, loot e
        abates como os outros. Vêm com os mesmos ajustes do dono (grupo, perigo da run...). No máximo "maximo" vivos
        e, com limite_na_luta, no máximo esse tanto de reforços somando a luta inteira. texto: "{nome}" = o que chegou.
        preparar(novo): ajeita cada um antes de ele entrar (ex.: a ninhada chega com menos ratos)."""
        from roguelike.inimigos import criar_inimigo
        lado = self.lado(dono)
        vagas = max(0, maximo - len([l for l in lado if l.esta_vivo()]))
        if limite_na_luta is not None:
            vagas = min(vagas, max(0, limite_na_luta - self.reforcos_chamados))
        novos = []
        for chave in chaves[:vagas]:
            novo = criar_inimigo(chave)
            novo.ajustes = dict(dono.ajustes)
            novo.curar_tudo()
            novo.preparar_para_combate()
            if preparar is not None:
                preparar(novo)
            lado.append(novo)
            for passiva in novo.passivas:
                passiva.inicio_do_combate(novo, self)
            self.registrar(Evento("reforco", dono, novo, texto=texto.format(nome=novo.nome)))
            novos.append(novo)
        self.reforcos_chamados += len(novos)
        return novos

    def juntar(self, dono, chaves):
        """Inimigos que fazem parte do dono (os ratos da roda da Rainha): entram no começo, sem anúncio, com os
        ajustes dele (grupo, perigo da run...)."""
        from roguelike.inimigos import criar_inimigo
        novos = []
        for chave in chaves:
            novo = criar_inimigo(chave)
            novo.ajustes = dict(dono.ajustes)
            novo.curar_tudo()
            novo.preparar_para_combate()
            self.lado(dono).append(novo)
            for passiva in novo.passivas:
                passiva.inicio_do_combate(novo, self)
            novos.append(novo)
        return novos

    def trazer_de_volta(self):
        """Quem esperava no trono volta quando os outros caem (de_volta = {"chave", "vida", "texto", ...}): com parte
        da vida, já na fase que essa vida pede (a Fúria do Rei) e sem fugir de novo. "ouro_roubado" volta com ele."""
        volta, self.de_volta = self.de_volta, None
        dono = next((i for i in reversed(self.derrotados) if i.categoria == "chefe"), None) or self.inimigos[0]

        def preparar(novo):
            novo.vida = max(1, round(novo.vida_maxima * volta.get("vida", 1.0)))
            novo.retirada_feita = True
            novo.ouro_roubado = volta.get("ouro_roubado", 0)
        novos = self.reforcar(dono, [volta["chave"]], maximo=99, texto=volta.get("texto", "{nome} voltou para a luta!"),
                              preparar=preparar)
        for novo in novos:
            for passiva in novo.passivas:                  # a vida baixa já começa na fase certa
                passiva.ao_receber_dano(novo, 0, self)

    def invocacoes_de(self, dono):
        return [l for l in self.lado(dono) if l.eh_invocacao and l.esta_vivo() and l.dono is dono]

    def invocar(self, dono, chave, nivel=1):
        from roguelike.inimigos import criar_invocacao
        atuais = self.invocacoes_de(dono)
        limite = int(dono.stat("max_invocacoes"))
        if limite <= 0:
            return None
        if len(atuais) >= limite:
            # A mais antiga vai embora para dar lugar à nova
            self.registrar(Evento("dissipou", atuais[0], texto=f"{atuais[0].nome} se desfez."))
            self.morrer(atuais[0], mensagem=False)
        criatura = criar_invocacao(chave, dono, nivel)
        if dono.lado == "inimigos":
            somar_ajustes(criatura, self.ajuste_inimigos)
            criatura.curar_tudo()
        criatura.preparar_para_combate()
        self.lado(dono).append(criatura)
        for passiva in criatura.passivas:
            passiva.inicio_do_combate(criatura, self)
        self.registrar(Evento("invocacao", dono, criatura, texto=f"{dono.nome} invocou {criatura.nome}!"))
        return criatura

    # ============================================================
    # RECOMPENSAS
    # ============================================================

    def xp_ganho(self):
        return sum(inimigo.recompensa_xp for inimigo in self.derrotados)

    def ouro_ganho(self):
        return sum(self.rng.randint(*inimigo.recompensa_ouro) for inimigo in self.derrotados)
