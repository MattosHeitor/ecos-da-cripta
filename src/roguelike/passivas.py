"""Passivas: efeitos permanentes de classes, subclasses, raças, bênçãos e amuletos.

No JSON uma passiva é um dicionário com "tipo" e os números dela, ex.:

    {"tipo": "vida_baixa", "limiar": 0.5, "modificadores": {"dano_causado": 0.3},
     "nome": "Fúria de sangue", "descricao": "Abaixo de 50% de vida causa +30% de dano."}

Cada tipo é uma subclasse de Passiva que muda só os "ganchos" que usa.

Mecânicas de chefe (reutilizáveis, no "passivas" da ficha do inimigos.json):
    fases_de_vida              ao cair abaixo de cada limiar, troca golpes/sprite, cura, invoca...
    invocar_periodico          invoca a cada N turnos (até um máximo vivo)
    escudo_elemental           quase imune até levar N golpes do elemento certo (pode se refazer)
    a_cada_n_turnos            a cada N turnos usa um golpe extra ou aplica status (ex.: congelar a fila)
    regenerar_com_invocacoes   cura no início do turno enquanto as suas criaturas viverem
    copiar_heroi               vira a sombra de um herói (aparência, atributos e golpes)
    fraqueza_contra            leva mais dano de quem está com um status (ex.: Forma de Dragão)
    guarda_costas              entra na frente de golpes de um alvo só contra chefes ou aliados feridos
    chamar_reforcos            se sobreviver N turnos, chama inimigos novos de verdade (Combate.reforcar)
    retirar_ao_trono           não cai na 1ª vez: foge e a luta continua contra outra parte (o Rei dos Ratos)
    roda / parte_da_roda       a Rainha dos Ratos: roda de ratos que gira, nó exposto (roguelike/roda.py)
    reinar_do_trono            age do trono sem poder ser atingido e desce quando um aliado cair (A Corte Completa)
"""

import math

from roguelike.eventos import Evento


class Passiva:
    def __init__(self, dados):
        self.dados = dict(dados)
        self.nome = dados.get("nome", "")
        self.descricao = dados.get("descricao", "")

    # ---------------- ganchos (o padrão é não fazer nada) ----------------
    def modificadores(self, dono):
        return {}

    def inicio_do_combate(self, dono, combate):
        pass

    def inicio_do_turno(self, dono, combate):
        pass

    def nova_rodada(self, dono, combate):
        """No começo de cada rodada, antes da iniciativa (ex.: a roda da Rainha gira)."""

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        """Pode diminuir o dano antes de ele ser aplicado (elemento = do golpe). Devolve o dano final."""
        return dano

    def dano_vindo_de(self, dono, dano, origem, combate):
        """Pode mudar o dano conforme QUEM bate (origem). Devolve o dano final."""
        return dano

    def ao_receber_dano(self, dono, dano, combate):
        pass

    def ao_causar_dano(self, dono, alvo, dano, combate):
        pass

    def evitar_morte(self, dono, combate):
        """Chamado quando o dono chegaria a 0 de vida. True = sobreviveu."""
        return False

    def renascer(self, dono, combate):
        """Chamado depois que o dono caiu. Devolve a fração de vida com que ele volta (0 = não volta)."""
        return 0

    def ao_morrer(self, dono, combate):
        """Chamado quando o dono cai de vez (depois de não renascer)."""

    def aliado_caiu(self, dono, caido, combate):
        """Chamado quando um aliado vivo do dono cai de vez (ex.: a Rainha cai e o Rei desce do trono)."""

    def ao_subir_nivel(self, dono):
        """Chamado quando um herói sobe de nível."""

    def interceptar(self, dono, atacante, habilidade, alvo, combate):
        """Um golpe de um alvo só vai acertar 'alvo' (aliado do dono). Devolve quem leva no lugar, ou None."""
        return None

    def fixos(self, dono):
        """Valores que ficam FIXOS, ignorando atributos e bônus (ex.: crítico sempre 5%)."""
        return {}


class PassivaBonus(Passiva):
    """Bônus fixos, ex.: {"chance_critico": 0.1}."""

    def modificadores(self, dono):
        return self.dados.get("modificadores", {})


class PassivaVidaBaixa(Passiva):
    """Bônus enquanto a vida estiver abaixo do limiar."""

    def modificadores(self, dono):
        if dono.esta_vivo() and dono.fracao_vida() <= self.dados.get("limiar", 0.35):
            return self.dados.get("modificadores", {})
        return {}


class PassivaGatilhoVidaBaixa(Passiva):
    """Uma vez por combate, ao cair abaixo do limiar, ganha status."""

    def inicio_do_combate(self, dono, combate):
        self.usada = False

    def ao_receber_dano(self, dono, dano, combate):
        if getattr(self, "usada", False) or not dono.esta_vivo():
            return
        if dono.fracao_vida() <= self.dados.get("limiar", 0.35):
            self.usada = True
            for status in self.dados.get("status", []):
                combate.aplicar_status(dono, status["status"], status.get("duracao"), status.get("valor", 0),
                                       status.get("acumulos", 1), dono)


class PassivaSobreviver(Passiva):
    """Uma vez por combate, sobrevive a um golpe fatal com um pouco de vida."""

    def inicio_do_combate(self, dono, combate):
        self.usada = False

    def evitar_morte(self, dono, combate):
        if getattr(self, "usada", False):
            return False
        self.usada = True
        dono.vida = self.dados.get("vida", 5)
        return True


class PassivaAdiarDano(Passiva):
    """Parte do dano recebido só chega no início do próximo turno."""

    def inicio_do_combate(self, dono, combate):
        self.guardado = 0

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        adiado = int(dano * self.dados.get("fracao", 0.3))
        self.guardado = getattr(self, "guardado", 0) + adiado
        return dano - adiado

    def inicio_do_turno(self, dono, combate):
        guardado = getattr(self, "guardado", 0)
        if guardado > 0:
            self.guardado = 0
            combate.causar_dano_direto(dono, guardado, None, motivo="dano_adiado", adiavel=False)


class PassivaStatusInicial(Passiva):
    """Começa cada combate com status (ex.: escudo)."""

    def inicio_do_combate(self, dono, combate):
        for status in self.dados.get("status", []):
            combate.aplicar_status(dono, status["status"], status.get("duracao"), status.get("valor", 0),
                                   status.get("acumulos", 1), dono)


class PassivaEnergiaInicial(Passiva):
    def inicio_do_combate(self, dono, combate):
        combate.dar_energia(dono, self.dados.get("quantidade", 1), motivo="passiva")


class PassivaRegenerarPerdida(Passiva):
    """Recupera uma fração da vida perdida no início de cada turno."""

    def inicio_do_turno(self, dono, combate):
        perdida = dono.vida_maxima - dono.vida
        cura = int(perdida * self.dados.get("fracao", 0.1))
        if cura > 0:
            combate.curar(dono, cura, dono, motivo="passiva")


class PassivaRouboPorSangramento(Passiva):
    """Rouba vida de acordo com o sangramento do alvo."""

    def ao_causar_dano(self, dono, alvo, dano, combate):
        acumulos = alvo.acumulos_de("sangramento")
        fracao = min(self.dados.get("maximo", 0.5), acumulos * self.dados.get("por_acumulo", 0.05))
        cura = int(dano * fracao)
        if cura > 0:
            combate.curar(dono, cura, dono, motivo="roubo")


class PassivaPontoExtra(Passiva):
    """Ponto de atributo extra a cada N níveis (raça humana)."""

    def ao_subir_nivel(self, dono):
        if dono.nivel % self.dados.get("a_cada", 2) == 0:
            dono.pontos_atributo += self.dados.get("pontos", 1)


class PassivaMaiorAtributo(Passiva):
    """Aumenta em uma porcentagem o maior atributo (sem contar bônus)."""

    def modificadores(self, dono):
        valores = dono.atributos.valores
        maior = max(valores, key=valores.get)
        return {maior: max(1, round(valores[maior] * self.dados.get("percentual", 0.05)))}


class PassivaStatusNosInimigos(Passiva):
    """No começo do combate, todos os inimigos recebem um status."""

    def inicio_do_combate(self, dono, combate):
        for alvo in combate.oponentes_de(dono):
            for status in self.dados.get("status", []):
                combate.aplicar_status(alvo, status["status"], status.get("duracao"), status.get("valor", 0),
                                       status.get("acumulos", 1), dono)


class PassivaInvocarNoInicio(Passiva):
    """Começa o combate com uma invocação."""

    def inicio_do_combate(self, dono, combate):
        combate.invocar(dono, self.dados["invocacao"], self.dados.get("nivel", 1))


class PassivaRenascer(Passiva):
    """Mortos-vivos: uma vez por combate, ao cair, levanta com parte da vida."""

    def inicio_do_combate(self, dono, combate):
        self.usada = False

    def renascer(self, dono, combate):
        if getattr(self, "usada", False):
            return 0
        self.usada = True
        return self.dados.get("vida", 0.3)


class PassivaStatusAoAcertar(Passiva):
    """Chance de aplicar status em quem o dono acerta (ex.: Meio-Demônio amaldiçoa)."""

    def ao_causar_dano(self, dono, alvo, dano, combate):
        if dano <= 0 or not alvo.esta_vivo() or combate.rng.random() >= self.dados.get("chance", 0.15):
            return
        for status in self.dados.get("status", []):
            combate.aplicar_status(alvo, status["status"], status.get("duracao"), status.get("valor", 0),
                                   status.get("acumulos", 1), dono)


class PassivaValoresFixos(Passiva):
    """Deixa valores fixos, ex.: {"chance_critico": 0.05, "dano_critico": 2.0}."""

    def fixos(self, dono):
        return self.dados.get("valores", {})


# ============================================================
# MECÂNICAS DE CHEFE
# ============================================================

def aplicar_lista_de_status(combate, alvos, lista, origem):
    for alvo in alvos:
        for status in lista:
            combate.aplicar_status(alvo, status["status"], status.get("duracao"), status.get("valor", 0),
                                   status.get("acumulos", 1), origem)


def alvos_do_grupo(dono, combate, grupo):
    """"si", "aliados" ou "oponentes" (padrão) -> lista de lutadores vivos."""
    if grupo == "si":
        return [dono]
    if grupo == "aliados":
        return combate.aliados_de(dono)
    return combate.oponentes_de(dono)


class PassivaDeTurnos(Passiva):
    """Base: conta os turnos do dono e dispara a cada "a_cada" turnos."""

    def inicio_do_combate(self, dono, combate):
        self.turnos = 0

    def inicio_do_turno(self, dono, combate):
        self.turnos = getattr(self, "turnos", 0) + 1
        if self.turnos % max(1, self.dados.get("a_cada", 3)) == 0:
            self.disparar(dono, combate)

    def disparar(self, dono, combate):
        pass


class PassivaFasesDeVida(Passiva):
    """Ao cair abaixo de cada limiar de vida, o chefe passa para a fase seguinte.

        {"tipo": "fases_de_vida", "fases": [
            {"limiar": 0.6, "nome": "Fúria", "texto": "...", "padrao": [...], "aprender": ["golpe"],
             "sprite": "outro_sprite", "curar": 0.2, "status": [...], "invocar": [{"invocacao": "x"}],
             "modificadores": {"dano_causado": 0.2}}]}

    Um golpe só não pula uma fase ("segurar", padrão true): a vida para no limiar e a fase começa.
    "forma": {"chave", "nome"} faz o chefe virar outro (ex.: o Dragão do Eclipse): troca o nome e, quando ele
    cair, conta também como abate dessa forma (página própria no bestiário). Com "curar": 1.0 ela ganha
    uma barra de vida nova e cheia.
    """

    def fases(self):
        return sorted(self.dados.get("fases", []), key=lambda f: -f["limiar"])

    def total(self):
        return len(self.fases()) + 1

    def proxima(self):
        fases, atual = self.fases(), getattr(self, "fase", 0)
        return fases[atual] if atual < len(fases) else None

    def inicio_do_combate(self, dono, combate):
        self.fase = 0
        combate.aplicar_status(dono, "fase_do_chefe", valor=1, origem=dono)

    def modificadores(self, dono):
        total = {}
        for fase in self.fases()[:getattr(self, "fase", 0)]:
            for chave, valor in fase.get("modificadores", {}).items():
                total[chave] = total.get(chave, 0) + valor
        return total

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        proxima = self.proxima()
        if proxima is None or not self.dados.get("segurar", True):
            return dano
        piso = max(1, int(proxima["limiar"] * dono.vida_maxima))
        if dono.vida > piso and dono.vida - dano < piso:
            return dono.vida - piso
        return dano

    def ao_receber_dano(self, dono, dano, combate):
        while dono.esta_vivo() and self.proxima() is not None and dono.fracao_vida() <= self.proxima()["limiar"]:
            self.entrar(dono, combate, self.proxima())

    def entrar(self, dono, combate, fase):
        self.fase += 1
        numero = self.fase + 1
        if "padrao" in fase:
            dono.padrao = list(fase["padrao"])
        for chave in fase.get("aprender", []):
            dono.niveis_habilidade[chave] = fase.get("nivel", 1)
        for chave in fase.get("esquecer", []):
            dono.niveis_habilidade.pop(chave, None)
        if fase.get("sprite"):
            dono.sprite = fase["sprite"]
        forma = fase.get("forma")
        if forma:                               # vira outro chefe: novo nome e, ao cair, conta também como abate dele
            dono.nome = forma.get("nome", dono.nome)
            dono.formas = getattr(dono, "formas", []) + [forma["chave"]]
        texto = fase.get("texto") or f"{dono.nome} entrou na fase {numero}!"
        combate.registrar(Evento("fase_do_chefe", dono, dono, numero, texto, nome=fase.get("nome", ""),
                                 total=self.total()))
        combate.aplicar_status(dono, "fase_do_chefe", valor=numero, origem=dono)
        if fase.get("curar"):
            combate.curar(dono, int(dono.vida_maxima * fase["curar"]), dono, motivo="fase")
        aplicar_lista_de_status(combate, [dono], fase.get("status", []), dono)
        for invocacao in fase.get("invocar", []):
            for _ in range(invocacao.get("quantidade", 1)):
                combate.invocar(dono, invocacao["invocacao"], invocacao.get("nivel", 1))


class PassivaInvocarPeriodico(PassivaDeTurnos):
    """A cada N turnos invoca criaturas, sem passar de "maximo" vivas ao mesmo tempo."""

    def modificadores(self, dono):
        return {"max_invocacoes": self.dados.get("maximo", 2)}

    def disparar(self, dono, combate):
        for _ in range(self.dados.get("quantidade", 1)):
            if len(combate.invocacoes_de(dono)) < self.dados.get("maximo", 2):
                combate.invocar(dono, self.dados["invocacao"], self.dados.get("nivel", 1))


class PassivaEscudoElemental(Passiva):
    """Quase imune ("reducao" do dano) até levar "golpes" golpes de um dos "elementos".

        {"tipo": "escudo_elemental", "elementos": ["fogo"], "golpes": 3, "reducao": 0.9, "refazer_a_cada": 4}
    """

    def inicio_do_combate(self, dono, combate):
        self.levantar(dono, combate)

    def levantar(self, dono, combate):
        self.pontos = self.dados.get("golpes", 3)
        self.turnos_sem_escudo = 0
        combate.aplicar_status(dono, "escudo_elemental", valor=self.pontos, origem=dono)

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        if getattr(self, "pontos", 0) <= 0:
            return dano
        if (elemento or "fisico") in self.dados.get("elementos", []):
            self.pontos -= 1
            if self.pontos <= 0:
                combate.remover_status(dono, "escudo_elemental")
                combate.registrar(Evento("escudo_quebrou", None, dono, texto=f"O escudo de {dono.nome} se partiu!"))
            elif dono.tem_status("escudo_elemental"):
                dono.status["escudo_elemental"].valor = self.pontos
            return dano
        reduzido = round(dano * (1 - self.dados.get("reducao", 0.9)))
        if dano > reduzido:
            combate.registrar(Evento("escudo", None, dono, dano - reduzido,
                                     f"O escudo de {dono.nome} absorveu {dano - reduzido}."))
        return reduzido

    def inicio_do_turno(self, dono, combate):
        refazer = self.dados.get("refazer_a_cada", 0)
        if getattr(self, "pontos", 0) > 0 or not refazer:
            return
        self.turnos_sem_escudo += 1
        if self.turnos_sem_escudo >= refazer:
            combate.registrar(Evento("aviso", dono, dono, texto=f"{dono.nome} refez o escudo!"))
            self.levantar(dono, combate)


class PassivaACadaNTurnos(PassivaDeTurnos):
    """A cada N turnos, de graça: usa um golpe ("golpe") e/ou aplica status num grupo.

        {"tipo": "a_cada_n_turnos", "a_cada": 4, "golpe": "nevasca", "texto": "A rainha ergue as mãos..."}
        {"tipo": "a_cada_n_turnos", "a_cada": 4, "alvo": "oponentes", "status": [{"status": "congelado"}]}
        {"tipo": "a_cada_n_turnos", "a_cada": 3, "reforcos": ["rato_comum"], "maximo_na_luta": 2}   (Combate.reforcar)
    """

    def disparar(self, dono, combate):
        if self.dados.get("texto"):
            combate.registrar(Evento("aviso", dono, dono, texto=self.dados["texto"]))
        if self.dados.get("golpe"):
            from roguelike.golpes import golpe as buscar_golpe
            golpe = buscar_golpe(self.dados["golpe"])
            alvos = combate.alvos_validos(dono, golpe)
            if golpe.escolhe_alvo() and alvos:
                alvos = [combate.rng.choice(alvos)]
            if alvos:
                combate.registrar(Evento("habilidade", dono, alvos[0] if len(alvos) == 1 else None,
                                         texto=f"{dono.nome} usou {golpe.nome}!", habilidade=golpe, alvos=list(alvos)))
                combate.aplicar_efeitos(dono, golpe.efeitos, alvos, self.dados.get("nivel", 1))
        if self.dados.get("status"):
            alvos = alvos_do_grupo(dono, combate, self.dados.get("alvo", "oponentes"))
            aplicar_lista_de_status(combate, alvos, self.dados["status"], dono)
        if self.dados.get("reforcos"):
            combate.reforcar(dono, list(self.dados["reforcos"]), limite_na_luta=self.dados.get("maximo_na_luta"),
                             texto=self.dados.get("texto_reforco", "{nome} atendeu ao chamado!"))


class PassivaRegenerarComInvocacoes(Passiva):
    """Cura "fracao" da vida máxima no início do turno enquanto as suas criaturas viverem.

    "de": [chaves] conta também aliados comuns com essas chaves (ex.: raízes que não são invocações).
    "por_criatura": true multiplica a cura pela quantidade viva.
    """

    def criaturas(self, dono, combate):
        filtro = self.dados.get("de")
        if not filtro:
            return combate.invocacoes_de(dono)
        return [a for a in combate.aliados_de(dono) if a is not dono and getattr(a, "chave", None) in filtro]

    def inicio_do_turno(self, dono, combate):
        vivas = self.criaturas(dono, combate)
        if not vivas or dono.vida >= dono.vida_maxima:
            return
        vezes = len(vivas) if self.dados.get("por_criatura") else 1
        cura = max(1, int(dono.vida_maxima * self.dados.get("fracao", 0.05) * vezes))
        combate.curar(dono, cura, dono, motivo="regeneracao")


# ============================================================
# INIMIGOS DAS FASES NOVAS
# ============================================================

class PassivaAoMorrer(Passiva):
    """Ao cair, aplica status num grupo (ex.: Fungo Esporento envenena todos os heróis).

        {"tipo": "ao_morrer", "alvo": "oponentes", "status": [{"status": "veneno", "valor": 2}], "texto": "..."}

    "alvo": "oponentes", "aliados" ou "todos" (os dois lados, ex.: o barril do Rato Bombardeiro).
    "reforcos": {"chaves": [...], "vivos": [2, 4]} = inimigos que saem dele ao cair (Combate.reforcar); num bando,
    "vivos" sorteia quantos bichos chegam (ex.: o Homem Bubônico solta uma ninhada de 2 a 4 ratos).
    """

    def alvos(self, dono, combate):
        alvo = self.dados.get("alvo", "oponentes")
        if alvo == "todos":
            return [l for l in combate.oponentes_de(dono) + combate.aliados_de(dono) if l is not dono]
        return combate.oponentes_de(dono) if alvo == "oponentes" else combate.aliados_de(dono)

    def ao_morrer(self, dono, combate):
        alvos = self.alvos(dono, combate)
        if not alvos:
            return
        if self.dados.get("texto"):
            combate.registrar(Evento("aviso", dono, dono, texto=self.dados["texto"]))
        if self.dados.get("dano"):                       # ex.: o Kobold Dinamiteiro explode
            from roguelike import elementos
            minimo, maximo = self.dados["dano"]
            elemento = self.dados.get("elemento")
            for alvo in alvos:
                dano = round(combate.rng.randint(minimo, maximo) * elementos.multiplicador(None, alvo, elemento))
                combate.causar_dano_direto(alvo, dano, dono, motivo="explosao", elemento=elemento,
                                           efetividade=elementos.efetividade(alvo, elemento) if elemento else None)
        aplicar_lista_de_status(combate, alvos, self.dados.get("status", []), dono)
        self.soltar_reforcos(dono, combate)

    def soltar_reforcos(self, dono, combate):
        reforcos = self.dados.get("reforcos")
        if not reforcos:
            return

        def menos_bichos(novo):                          # num bando, "vivos" sorteia quantos chegam
            if "vivos" in reforcos and getattr(novo, "eh_bando", False):
                quantos = combate.rng.randint(*reforcos["vivos"])
                novo.vida = max(1, math.ceil(novo.vida_maxima * quantos / novo.quantos))
        combate.reforcar(dono, reforcos["chaves"], texto=reforcos.get("texto", "{nome} sai de dentro de " + dono.nome + "!"),
                         preparar=menos_bichos)


class PassivaEsmola(Passiva):
    """Mendigo Bubônico: no 1º turno estende a tigela; depois, se ninguém o atacou desde o turno anterior dele,
    bate a carteira do grupo (entre "fracao" do ouro, no mínimo "minimo"). Se cair, o ouro roubado volta.

        {"tipo": "esmola", "fracao": [0.05, 0.15], "minimo": 5, "nome": "Uma Moedinha..."}
    """

    def inicio_do_combate(self, dono, combate):
        self.atacado, self.roubado, self.turnos = False, 0, 0

    def ao_receber_dano(self, dono, dano, combate):
        self.atacado = True

    def inicio_do_turno(self, dono, combate):
        self.turnos = getattr(self, "turnos", 0) + 1
        ignorado, self.atacado = not getattr(self, "atacado", False), False
        if self.turnos == 1:
            combate.registrar(Evento("aviso", dono, dono, texto=f"{dono.nome} estende a tigela: \"Uma moedinha...\""))
            return
        if not ignorado or combate.grupo is None or combate.grupo.ouro <= 0:
            return
        minimo, maximo = self.dados.get("fracao", [0.05, 0.15])
        ouro = combate.grupo.ouro
        quanto = min(ouro, max(self.dados.get("minimo", 5), round(ouro * combate.rng.uniform(minimo, maximo))))
        combate.grupo.ouro -= quanto
        self.roubado = getattr(self, "roubado", 0) + quanto
        combate.registrar(Evento("roubo_de_ouro", dono, dono, quanto,
                                 texto=f"Ninguém deu nada: {dono.nome} bateu a carteira do grupo (-{quanto} de ouro)!"))

    def ao_morrer(self, dono, combate):
        if getattr(self, "roubado", 0) and combate.grupo is not None:
            combate.grupo.ouro += self.roubado
            combate.registrar(Evento("aviso", dono, dono, texto=f"O ouro roubado volta para o grupo (+{self.roubado})."))
            self.roubado = 0


class PassivaDevolverOuro(Passiva):
    """Ao cair, devolve o ouro que cobrou (efeito "roubar_ouro"), vezes "multiplicador" (o Imposto Real volta em dobro).

        {"tipo": "devolver_ouro", "multiplicador": 2, "nome": "Cofres Abertos"}
    """

    def ao_morrer(self, dono, combate):
        roubado = getattr(dono, "ouro_roubado", 0)
        if not roubado or combate.grupo is None:
            return
        valor = round(roubado * self.dados.get("multiplicador", 1))
        combate.grupo.ouro += valor
        dono.ouro_roubado = 0
        combate.registrar(Evento("ouro_devolvido", dono, dono, valor,
                                 texto=f"Os cofres de {dono.nome} se abrem: +{valor} de ouro para o grupo!"))


class PassivaRetirarAoTrono(Passiva):
    """O Rei dos Ratos não cai na primeira vez: com a vida no fim, foge para o trono e a luta continua contra quem
    ele chamar ("segunda_parte", que a Run transforma na próxima parte da luta: roguelike/ondas.py). Ele volta
    quando ela cair ("vida_ao_voltar"), com o ouro do Imposto Real. Quem já voltou (retirada_feita) cai de verdade.

        {"tipo": "retirar_ao_trono", "segunda_parte": {"inimigos": ["rainha_dos_ratos"], "estrelas": 5,
         "vida_ao_voltar": 0.4, "nome": "...", "textos": {...}}}
    """

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        if getattr(dono, "retirada_feita", False) or not self.dados.get("segunda_parte"):
            return dano
        if getattr(self, "retirado", False):
            return 0                                       # (os golpes de área que ainda iam nele)
        if dano < dono.vida:
            return dano
        if dono.vida > 1:                                  # fica com 1 de vida e foge depois de sentir o golpe
            self.fugir_depois = True
            return dono.vida - 1
        self.retirar(dono, combate)
        return 0

    def ao_receber_dano(self, dono, dano, combate):
        if getattr(self, "fugir_depois", False) and not getattr(self, "retirado", False):
            self.retirar(dono, combate)

    def retirar(self, dono, combate):
        self.retirado, self.fugir_depois = True, False
        parte = dict(self.dados["segunda_parte"])
        parte["trono"] = {"chave": dono.chave, "vida": parte.pop("vida_ao_voltar", 0.4),
                          "ouro_roubado": getattr(dono, "ouro_roubado", 0),
                          "texto": self.dados.get("texto_volta", "{nome} salta do trono, furioso!")}
        combate.proxima_parte = parte
        combate.fugir(dono, texto=self.dados.get("texto", f"{dono.nome} foge para o trono!"))


class PassivaReinarDoTrono(Passiva):
    """A Corte Completa (modo difícil do Reino dos Ratos): o Rei governa do trono a luta toda. Enquanto "espera" (a
    Rainha) estiver viva, ele age (Éditos, Imposto...) com "padrao_no_trono" e os golpes de "aprender" (ex.: Contar as
    Moedas), mas fica No Trono: ninguém o atinge, nem em área. Quando ela cai, ele desce com no máximo "vida_ao_descer"
    da vida (já na fase que essa vida pede), esquece os golpes do trono e volta ao padrão de sempre. Não foge para o
    trono (a retirada já está feita).

        {"tipo": "reinar_do_trono", "espera": "rainha_dos_ratos", "vida_ao_descer": 0.5, "aprender": ["contar_moedas"],
         "padrao_no_trono": [...], "texto": "...", "texto_descer": "{nome} desce do trono!",
         "quando_desce": "Desce quando a Rainha cair"}      (o painel da tela de combate)
    """

    def inicio_do_combate(self, dono, combate):
        dono.retirada_feita = True
        self.padrao_de_sempre = getattr(dono, "padrao", None)
        if self.dados.get("padrao_no_trono"):
            dono.padrao = list(self.dados["padrao_no_trono"])
        for chave in self.dados.get("aprender", []):
            dono.niveis_habilidade[chave] = 1
        combate.marcar(dono, "no_trono", True, dono)
        if self.dados.get("texto"):
            combate.registrar(Evento("aviso", dono, dono, texto=self.dados["texto"].format(nome=dono.nome)))

    def aliado_caiu(self, dono, caido, combate):
        if getattr(caido, "chave", None) == self.dados.get("espera") and dono.tem_status("no_trono"):
            self.descer(dono, combate)

    def descer(self, dono, combate):
        combate.marcar(dono, "no_trono", False)
        dono.padrao = self.padrao_de_sempre
        for chave in self.dados.get("aprender", []):
            dono.niveis_habilidade.pop(chave, None)
        dono.vida = min(dono.vida, max(1, round(dono.vida_maxima * self.dados.get("vida_ao_descer", 1.0))))
        combate.registrar(Evento("desceu_do_trono", dono, dono, dono.vida,
                                 texto=self.dados.get("texto_descer", "{nome} desce do trono!").format(nome=dono.nome)))
        for passiva in dono.passivas:                      # a vida baixa já começa na fase certa (a Fúria do Rei)
            passiva.ao_receber_dano(dono, 0, combate)


class PassivaRoda(Passiva):
    """A Rainha dos Ratos (o nó, roguelike/roda.py): cria a roda de ratos e a faz girar uma casa por rodada. Só os
    "frente" ratos da frente agem e podem ser atingidos; os outros ficam Atrás da Roda. Com "exposto_com" da roda
    caída, o nó fica exposto: acertá-lo fere cada rato vivo com "fracao_no" do golpe. Ignorado por "fecha_em" turnos
    dele, o nó se fecha até outro rato cair. O último rato vivo fica em Fúria da Roda.

        {"tipo": "roda", "ratos": [...], "frente": 3, "exposto_com": 0.5, "fecha_em": 3, "fracao_no": 0.6}
    """

    def inicio_do_combate(self, dono, combate):
        if not dono.roda:
            dono.roda = combate.juntar(dono, self.dados["ratos"])
            for rato in dono.roda:
                rato.no = dono
        dono.giro = 0
        self.ignorado, self.atingido, self.fechado_por_descaso, self.caidos_ao_fechar = 0, False, False, 0
        self.exposto = False
        self.atualizar(dono, combate)

    def frente(self, dono, giro=None):
        return dono.frente(self.dados.get("frente", 3), giro)

    def proximo_giro(self, dono):
        """Quem fica na frente depois do próximo giro (a tela mostra)."""
        return self.frente(dono, dono.giro + 1)

    def nova_rodada(self, dono, combate):
        dono.giro += 1
        self.atualizar(dono, combate)

    def atualizar(self, dono, combate):
        """Marca quem está atrás da roda e abre ou fecha o nó."""
        frente = self.frente(dono)
        for rato in dono.ratos_vivos():
            combate.marcar(rato, "atras_da_roda", rato not in frente, dono)
        metade = dono.caidos() >= len(dono.roda) * self.dados.get("exposto_com", 0.5)
        exposto = metade and not self.fechado_por_descaso
        if exposto and not self.exposto:
            self.ignorado = 0
            combate.registrar(Evento("aviso", dono, dono, texto="O nó de caudas está exposto! Acertá-lo fere a roda inteira."))
        self.exposto = exposto
        combate.marcar(dono, "no_fechado", not exposto, dono)

    def dano_vindo_de(self, dono, dano, origem, combate):
        """Golpe no nó exposto: cada rato vivo sente uma parte dele (o nó em si não tem vida própria)."""
        self.atingido = True
        parte = max(1, round(dano * self.dados.get("fracao_no", 0.6)))
        for rato in dono.ratos_vivos():
            combate.causar_dano_direto(rato, parte, origem, motivo="no_de_caudas")
        return 0

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        return 0 if dono.roda else dano                    # (o que não vem de alguém não atravessa o nó)

    def inicio_do_turno(self, dono, combate):
        if self.exposto:
            self.ignorado = 0 if self.atingido else self.ignorado + 1
            if self.ignorado >= self.dados.get("fecha_em", 3):
                self.fechado_por_descaso, self.caidos_ao_fechar = True, dono.caidos()
                combate.registrar(Evento("aviso", dono, dono, texto="Ninguém tocou no nó: ele se fecha de novo!"))
                self.atualizar(dono, combate)
        self.atingido = False

    def rato_caiu(self, dono, combate):
        vivos = dono.ratos_vivos()
        if not vivos:
            if dono not in combate.derrotados:
                combate.morrer(dono)                       # sem ratos, a Rainha cai
            return
        if len(vivos) == 1:
            combate.aplicar_status(vivos[0], "furia_da_roda", origem=dono)
            combate.registrar(Evento("aviso", dono, vivos[0], texto=f"Sozinho na roda, o {vivos[0].nome} enlouquece!"))
        if self.fechado_por_descaso and dono.caidos() > self.caidos_ao_fechar:
            self.fechado_por_descaso = False               # mais um caiu: o nó se abre de novo
        self.atualizar(dono, combate)


class PassivaParteDaRoda(Passiva):
    """Rato preso na roda da Rainha: quando cai, avisa o nó (passiva "roda")."""

    def ao_morrer(self, dono, combate):
        no = getattr(dono, "no", None)
        for passiva in getattr(no, "passivas", []):
            if isinstance(passiva, PassivaRoda):
                passiva.rato_caiu(no, combate)


class PassivaFugirComRoubo(Passiva):
    """Rato Ladrão: depois de roubar (efeito "roubar_item"), foge em "turnos" turnos dele levando tudo.
    Se cair antes, o que roubou volta para a mochila de quem foi roubado (ou para o baú, se não couber).

        {"tipo": "fugir_com_roubo", "turnos": 2, "nome": "Pernas Leves"}
    """

    def inicio_do_combate(self, dono, combate):
        self.turnos = 0
        dono.roubados = []

    def inicio_do_turno(self, dono, combate):
        if not getattr(dono, "roubados", None):
            return
        self.turnos = getattr(self, "turnos", 0) + 1
        if self.turnos >= self.dados.get("turnos", 2):
            combate.fugir(dono, texto=f"{dono.nome} fugiu com o que roubou!")

    def ao_morrer(self, dono, combate):
        from roguelike.itens import item
        for chave, heroi in getattr(dono, "roubados", []):
            if not heroi.inventario.adicionar(chave) and combate.grupo is not None:
                combate.grupo.bau.adicionar(chave)
            combate.registrar(Evento("aviso", heroi, heroi, texto=f"{heroi.nome} recuperou {item(chave).nome}."))
        dono.roubados = []


class PassivaGuardaCostas(Passiva):
    """Guarda Real Roedor: entra na frente de um golpe de um alvo só contra um protegido, uma vez por rodada.
    Protege os chefes e mini-chefes do lado dele; sem eles, o aliado mais ferido abaixo de "abaixo" da vida.

        {"tipo": "guarda_costas", "abaixo": 0.5, "nome": "Pela Coroa!"}
    """

    def protegidos(self, dono, combate):
        aliados = [a for a in combate.aliados_de(dono) if a is not dono and not a.eh_invocacao]
        nobres = [a for a in aliados if getattr(a, "categoria", "comum") in ("chefe", "mini_chefe")]
        if nobres:
            return nobres
        feridos = [a for a in aliados if a.fracao_vida() < self.dados.get("abaixo", 0.5)]
        return [min(feridos, key=lambda a: a.fracao_vida())] if feridos else []

    def interceptar(self, dono, atacante, habilidade, alvo, combate):
        if alvo is dono or getattr(self, "rodada", None) == combate.rodada:
            return None
        if any(s.impede_acao() for s in dono.status.values()) or alvo not in self.protegidos(dono, combate):
            return None
        self.rodada = combate.rodada
        combate.registrar(Evento("protegeu", dono, alvo, texto=f"{dono.nome} entrou na frente de {alvo.nome}!"))
        return dono


class PassivaChamarReforcos(Passiva):
    """Arauto Roedor: se ainda estiver de pé no início do seu turno número "turnos", toca a corneta e chama
    reforços de verdade (Combate.reforcar), uma vez só. O status "corneta" mostra quantos turnos faltam.

        {"tipo": "chamar_reforcos", "turnos": 2, "sempre": ["rato_comum"], "um_de": ["ratazana_gigante", ...],
         "maximo_na_luta": 2}

    "maximo_na_luta": quantos reforços a luta inteira aceita (com vários Arautos, só o primeiro é atendido).
    """

    def inicio_do_combate(self, dono, combate):
        self.faltam = self.dados.get("turnos", 2)
        combate.aplicar_status(dono, "corneta", valor=self.faltam, origem=dono)

    def inicio_do_turno(self, dono, combate):
        if getattr(self, "faltam", 0) <= 0 or any(s.impede_acao() for s in dono.status.values()):
            return                                       # atordoado: este turno não conta para a corneta
        self.faltam -= 1
        if self.faltam > 0:
            if dono.tem_status("corneta"):
                dono.status["corneta"].valor = self.faltam
            return
        combate.remover_status(dono, "corneta")
        combate.registrar(Evento("aviso", dono, dono, texto=self.dados.get("texto", f"{dono.nome} sopra a corneta de osso!")))
        chaves = list(self.dados.get("sempre", []))
        if self.dados.get("um_de"):
            chaves.append(combate.rng.choice(self.dados["um_de"]))
        if not combate.reforcar(dono, chaves, limite_na_luta=self.dados.get("maximo_na_luta")):
            combate.registrar(Evento("aviso", dono, dono, texto="Ninguém mais responde à corneta."))


class PassivaMatilha(Passiva):
    """Mais forte a cada aliado vivo das chaves em "de" (lobos em matilha). Sem "de", conta qualquer aliado vivo
    (o Pingente do Nó de Caudas).

        {"tipo": "matilha", "de": ["lobo_sarnento"], "por_aliado": {"dano_causado": 0.1}}
    """

    def inicio_do_combate(self, dono, combate):
        self.combate = combate

    def modificadores(self, dono):
        combate = getattr(self, "combate", None)
        if combate is None:
            return {}
        filtro = self.dados.get("de")
        aliados = sum(1 for a in combate.aliados_de(dono)
                      if a is not dono and (filtro is None or getattr(a, "chave", None) in filtro))
        return {chave: valor * aliados for chave, valor in self.dados.get("por_aliado", {}).items()}


class PassivaFuriaAoPerderAliado(Passiva):
    """Quando um herói aliado cai (invocações não contam), o dono ganha um status (o Pingente do Nó de Caudas).

        {"tipo": "furia_ao_perder_aliado", "status": "fortalecido", "duracao": 2}
    """

    def aliado_caiu(self, dono, caido, combate):
        if not caido.eh_invocacao and dono.esta_vivo():
            combate.aplicar_status(dono, self.dados.get("status", "fortalecido"), self.dados.get("duracao"), origem=dono)


class PassivaEncantarNoInicio(Passiva):
    """No começo da luta, cada inimigo das "familias" (menos os chefes) tem "chance" de ganhar o status por 1 turno
    (o set Realeza Roedora: os ratos às vezes viram contra os outros).

        {"tipo": "encantar_no_inicio", "familias": ["pestes"], "chance": 0.25, "status": "encantado"}
    """

    def inicio_do_combate(self, dono, combate):
        for alvo in combate.oponentes_de(dono):
            familia = (getattr(alvo, "ficha", None) or {}).get("familia")
            if familia in self.dados.get("familias", []) and getattr(alvo, "categoria", "") not in ("chefe", "mini_chefe") \
                    and combate.rng.random() < self.dados.get("chance", 0.25):
                combate.aplicar_status(alvo, self.dados.get("status", "encantado"), self.dados.get("duracao", 1), origem=dono)


class PassivaPestePermanente(Passiva):
    """Começa toda luta com a Peste em pelo menos nível 1 (não soma: quem já tem fica como está). A fogueira cura,
    mas na luta seguinte ela volta (o preço do set Realeza Roedora)."""

    def inicio_do_combate(self, dono, combate):
        if not dono.tem_status("peste"):
            combate.aplicar_status(dono, "peste", origem=dono)


class PassivaBloquearPrimeiro(Passiva):
    """Anula por completo o primeiro golpe que recebe em cada combate (o escudo do Cavaleiro Ossudo)."""

    def inicio_do_combate(self, dono, combate):
        self.usada = False
        combate.aplicar_status(dono, "guarda_erguida", origem=dono)

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        if getattr(self, "usada", True) or dano <= 0:
            return dano
        self.usada = True
        combate.remover_status(dono, "guarda_erguida")
        combate.registrar(Evento("escudo", None, dono, dano, f"{dono.nome} aparou o golpe com o escudo!"))
        return 0


class PassivaImaterial(Passiva):
    """Golpes dos "elementos" (ex.: físico) quase atravessam sem ferir: só "reducao" do dano some (Lobo Espectral).
    Um pouco sempre passa: um grupo sem magia não fica preso num combate sem fim.

        {"tipo": "imaterial", "elementos": ["fisico"], "reducao": 0.6}
    """

    def reduzir_dano(self, dono, dano, combate, elemento=None):
        if (elemento or "fisico") in self.dados.get("elementos", ["fisico"]) and dano > 0:
            restante = max(1, round(dano * (1 - self.dados.get("reducao", 0.85))))
            texto = self.dados.get("texto", "O golpe atravessa {nome} quase sem feri-lo!").format(nome=dono.nome)
            combate.registrar(Evento("escudo", None, dono, dano - restante, texto))
            return restante
        return dano


class PassivaPedagio(PassivaDeTurnos):
    """A cada N turnos cobra pedágio: se ninguém o acertou desde a última cobrança, rouba ouro do grupo
    (ou, sem ouro, um consumível de um herói). Acertá-lo nesse meio-tempo "paga" com sangue.

        {"tipo": "pedagio", "a_cada": 3, "ouro": [8, 15]}
    """

    def inicio_do_combate(self, dono, combate):
        super().inicio_do_combate(dono, combate)
        self.atingido = False

    def ao_receber_dano(self, dono, dano, combate):
        self.atingido = True

    def disparar(self, dono, combate):
        if getattr(self, "atingido", False):
            self.atingido = False
            combate.registrar(Evento("aviso", dono, dono, texto=f"{dono.nome} aceita o sangue como pagamento."))
            return
        grupo = getattr(combate, "grupo", None)
        minimo, maximo = self.dados.get("ouro", [8, 15])
        if grupo is not None and grupo.ouro > 0:
            levado = min(grupo.ouro, combate.rng.randint(minimo, maximo))
            grupo.ouro -= levado
            combate.registrar(Evento("aviso", dono, dono, texto=f"{dono.nome} cobrou o pedágio: -{levado} de ouro!"))
            return
        from roguelike.itens import item
        mochilas = [(h, c) for h in combate.oponentes_de(dono) if hasattr(h, "inventario")
                    for c in list(h.inventario.itens) if item(c).tipo == "consumivel"]
        if mochilas:
            heroi, chave = combate.rng.choice(mochilas)
            heroi.inventario.remover(chave)
            combate.registrar(Evento("aviso", dono, heroi,
                                     texto=f"Sem ouro: {dono.nome} levou {item(chave).nome} de {heroi.nome}!"))


class PassivaCopiarHeroi(Passiva):
    """No começo do combate (ou ao ser invocada) vira a sombra de um herói: copia a aparência, parte dos
    atributos e alguns golpes equipados dele (Sombra do Herói, Catedral do Eclipse).

        {"tipo": "copiar_heroi", "golpes": 2, "atributos": 0.8}
    """

    def inicio_do_combate(self, dono, combate):
        herois = [h for h in combate.oponentes_de(dono) if not h.eh_invocacao and hasattr(h, "golpes")]
        if not herois or getattr(dono, "sombra_de", None):
            return
        heroi = combate.rng.choice(herois)
        dono.sombra_de = heroi.nome
        dono.nome = f"Sombra de {heroi.nome}"
        dono.sprite = heroi.sprite
        fracao = self.dados.get("atributos", 0.8)
        for nome, valor in heroi.atributos.para_dict().items():
            dono.atributos.valores[nome] = max(dono.atributos[nome], round(valor * fracao))
        for chave in heroi.golpes.equipados[:self.dados.get("golpes", 2)]:
            dono.niveis_habilidade.setdefault(chave, heroi.niveis_habilidade.get(chave, 1))
        combate.registrar(Evento("aviso", dono, heroi, texto=f"Uma sombra toma a forma de {heroi.nome}!"))


class PassivaFraquezaContra(Passiva):
    """Leva mais dano de quem está com um status, a partir de uma fase do chefe (Dragão do Eclipse x Draconiano
    em Forma de Dragão).

        {"tipo": "fraqueza_contra", "status": "forma_de_dragao", "multiplicador": 1.6, "desde_a_fase": 3}
    """

    def dano_vindo_de(self, dono, dano, origem, combate):
        fase = dono.status["fase_do_chefe"].valor if dono.tem_status("fase_do_chefe") else 1
        if fase < self.dados.get("desde_a_fase", 1) or not origem.tem_status(self.dados["status"]):
            return dano
        maior = round(dano * self.dados.get("multiplicador", 1.5))
        if maior > dano:
            combate.registrar(Evento("aviso", origem, dono, texto=self.dados.get("texto", "Golpe de dragão contra dragão!")))
        return maior


TIPOS_DE_PASSIVA = {
    "ponto_extra": PassivaPontoExtra,
    "maior_atributo": PassivaMaiorAtributo,
    "status_nos_inimigos": PassivaStatusNosInimigos,
    "invocar_no_inicio": PassivaInvocarNoInicio,
    "valores_fixos": PassivaValoresFixos,
    "bonus": PassivaBonus,
    "vida_baixa": PassivaVidaBaixa,
    "gatilho_vida_baixa": PassivaGatilhoVidaBaixa,
    "sobreviver": PassivaSobreviver,
    "adiar_dano": PassivaAdiarDano,
    "status_inicial": PassivaStatusInicial,
    "energia_inicial": PassivaEnergiaInicial,
    "regenerar_perdida": PassivaRegenerarPerdida,
    "roubo_por_sangramento": PassivaRouboPorSangramento,
    "renascer": PassivaRenascer,
    "status_ao_acertar": PassivaStatusAoAcertar,
    "fases_de_vida": PassivaFasesDeVida,
    "invocar_periodico": PassivaInvocarPeriodico,
    "escudo_elemental": PassivaEscudoElemental,
    "a_cada_n_turnos": PassivaACadaNTurnos,
    "regenerar_com_invocacoes": PassivaRegenerarComInvocacoes,
    "ao_morrer": PassivaAoMorrer,
    "pedagio": PassivaPedagio,
    "bloquear_primeiro": PassivaBloquearPrimeiro,
    "imaterial": PassivaImaterial,
    "matilha": PassivaMatilha,
    "furia_ao_perder_aliado": PassivaFuriaAoPerderAliado,
    "encantar_no_inicio": PassivaEncantarNoInicio,
    "peste_permanente": PassivaPestePermanente,
    "fugir_com_roubo": PassivaFugirComRoubo,
    "esmola": PassivaEsmola,
    "devolver_ouro": PassivaDevolverOuro,
    "retirar_ao_trono": PassivaRetirarAoTrono,
    "reinar_do_trono": PassivaReinarDoTrono,
    "roda": PassivaRoda,
    "parte_da_roda": PassivaParteDaRoda,
    "guarda_costas": PassivaGuardaCostas,
    "chamar_reforcos": PassivaChamarReforcos,
    "copiar_heroi": PassivaCopiarHeroi,
    "fraqueza_contra": PassivaFraquezaContra,
}


def criar_passiva(dados):
    try:
        return TIPOS_DE_PASSIVA[dados["tipo"]](dados)
    except KeyError:
        raise ValueError(f"Tipo de passiva desconhecido: {dados.get('tipo')}") from None
