"""Lutadores: tudo o que luta no combate.

    Lutador (base)
    ├── Heroi       controlado pelo jogador; tem classe, nível, XP e equipamento
    ├── Inimigo     controlado por uma IA; dá XP, ouro e loot
    │   ├── Invocacao   criada por uma habilidade; luta do lado de quem a chamou
    │   └── Bando       um monte de bichos pequenos num lutador só, "Ratos ×12" (roguelike/bando.py)

O valor final de qualquer número (crítico, esquiva, dano causado...) é
calculado por stat(nome): fórmula dos atributos + bônus de status,
passivas, equipamento e ajustes de dificuldade.
"""

from roguelike.atributos import Atributos, valor_derivado, eh_derivado
from roguelike.dados import regras
from roguelike.elementos import resistencias_do_inimigo, como_modificadores
from roguelike.golpes import golpe, GerenciadorDeGolpes
from roguelike.inventario import Inventario
from roguelike.passivas import criar_passiva


class Lutador:
    def __init__(self, nome, sprite, atributos=None, habilidades=None, passivas=None,
                 iniciativa=(3, 8), imunidades=(), lado="inimigos"):
        self.nome = nome
        self.sprite = sprite                          # nome do sprite em assets/sprites_macabros
        self.atributos = atributos if isinstance(atributos, Atributos) else Atributos(atributos)
        self.niveis_habilidade = {}                   # chave da habilidade -> nível
        for chave in habilidades or []:
            self.aprender(chave)
        self.passivas = [p if not isinstance(p, dict) else criar_passiva(p) for p in passivas or []]
        self.faixa_iniciativa = tuple(iniciativa)
        self.imunidades = set(imunidades)
        self.lado = lado                              # "herois" ou "inimigos"
        self.eh_invocacao = False
        self.ajustes = {}                             # bônus de dificuldade (grupo, região...)
        self.status = {}                              # chave -> Status
        self.recargas = {}                            # golpe -> turnos até poder usar de novo
        self.energia = 0
        self._somando_passivas = False
        self.vida = 0                                 # (a vida máxima pode depender da vida atual)
        self.vida = self.vida_maxima

    # ============================================================
    # VIDA
    # ============================================================

    def vida_base(self):
        raise NotImplementedError

    @property
    def vida_maxima(self):
        base = self.vida_base() * (1 + self.bonus("vida_percentual"))
        return max(1, round(base + self.bonus("vida_maxima")))

    def esta_vivo(self):
        return self.vida > 0

    def fracao_vida(self):
        return self.vida / self.vida_maxima

    def curar_tudo(self):
        self.vida = self.vida_maxima

    # ============================================================
    # ATRIBUTOS E VALORES CALCULADOS
    # ============================================================

    def fontes_de_bonus(self):
        """Dicionários de bônus que valem agora. Subclasses acrescentam (ex.: equipamento)."""
        yield self.ajustes
        for status in self.status.values():
            yield status.modificadores()

    def bonus(self, nome):
        """Soma de todos os bônus de um valor (sem a fórmula dos atributos)."""
        total = sum(fonte.get(nome, 0) for fonte in self.fontes_de_bonus())
        # Uma passiva pode depender da vida (que depende de bônus): evita repetir sem fim
        if not self._somando_passivas:
            self._somando_passivas = True
            try:
                total += sum(p.modificadores(self).get(nome, 0) for p in self.passivas)
            finally:
                self._somando_passivas = False
        return total

    def atributo(self, nome):
        return self.atributos[nome] + self.bonus(nome)

    def stat(self, nome):
        """Valor final, ex.: stat("chance_critico") -> 0.12."""
        for passiva in self.passivas:
            fixos = passiva.fixos(self)
            if nome in fixos:
                return fixos[nome]
        if eh_derivado(nome):
            return valor_derivado(nome, self.atributo, self.bonus(nome))
        return self.bonus(nome)

    def faixa_de_iniciativa(self):
        """(mínimo, máximo) da iniciativa, rolada a cada rodada."""
        regra = regras()["iniciativa"]
        extra = self.atributo("destreza") // regra["destreza_por_ponto"] + int(self.bonus("iniciativa"))
        minimo, maximo = self.faixa_iniciativa
        maximo += self.nivel_para_iniciativa() // regra["niveis_por_ponto"]
        return max(0, minimo + extra), max(0, maximo + extra)

    def nivel_para_iniciativa(self):
        return 0

    @property
    def energia_maxima(self):
        return regras()["energia"]["maxima"] + int(self.bonus("energia_maxima"))

    def energia_inicial(self):
        return regras()["energia"]["inicial"]

    # ============================================================
    # HABILIDADES
    # ============================================================

    def aprender(self, chave, nivel=1):
        golpe(chave)                 # confere se existe
        self.niveis_habilidade.setdefault(chave, nivel)

    def nivel_da(self, chave):
        return self.niveis_habilidade.get(chave, 0)

    def habilidades(self):
        """Lista de (Habilidade, nível) na ordem em que foram aprendidas."""
        return [(golpe(chave), nivel) for chave, nivel in self.niveis_habilidade.items()]

    # ============================================================
    # STATUS
    # ============================================================

    def tem_status(self, chave):
        return chave in self.status

    def acumulos_de(self, chave):
        status = self.status.get(chave)
        return status.acumulos if status else 0

    def imune(self, chave):
        return chave in self.imunidades_atuais()

    def imunidades_atuais(self):
        return set(self.imunidades)

    def sprite_atual(self):
        """O sprite agora: um status de transformação (Forma de Dragão) troca o desenho."""
        for status in self.status.values():
            if status.sprite():
                return status.sprite()
        return self.sprite

    def preparar_para_combate(self):
        self.status = {}
        self.recargas = {}
        self.energia = self.energia_inicial()

    def multiplicador_contra(self, direto):
        """Quanto um golpe machuca este lutador: direto = de um alvo só. (Bandos sofrem mais em área.)"""
        return 1.0

    # ---------------- recargas (golpes que esperam alguns turnos) ----------------
    def recarga_de(self, chave):
        return self.recargas.get(chave, 0)

    def passar_recargas(self):
        """Início do turno do lutador: cada recarga anda 1."""
        self.recargas = {chave: turnos - 1 for chave, turnos in self.recargas.items() if turnos > 1}

    def __repr__(self):
        return f"{type(self).__name__}({self.nome!r}, {self.vida}/{self.vida_maxima})"


class Heroi(Lutador):
    """Herói do jogador.

    Composição: o herói TEM uma TrilhaDeClasse (classe + subclasse + especialização) e um
    GerenciadorDeGolpes. As propriedades classe/subclasse/especializacao leem da trilha.
    """

    def __init__(self, classe, nome, aparencia=None):
        from roguelike.especialidades import TrilhaDeClasse
        self.trilha = TrilhaDeClasse(classe)
        self.nivel = 1
        self.xp = 0
        self.pontos_atributo = 0
        self.pontos_habilidade = 0
        self.aparencia = aparencia or classe.aparencia_padrao
        self.raca = "humano"              # chave da raça (definir_raca aplica os efeitos)
        self.dados_da_raca = None         # a Raca aplicada (None = herói de teste, sem efeitos de raça)
        self._passivas_da_raca = []
        self.subclasse_bloqueada = False  # algumas bênçãos tiram a subclasse
        self.inventario = Inventario(regras()["inventario"]["pilhas_por_heroi"])
        # os 8 espaços do boneco + o consumível usado sozinho no início do combate (roguelike/equipamentos.py)
        from roguelike.equipamentos import Equipamentos
        self.equipamentos = Equipamentos(self)
        self._passivas_do_equipamento = {}
        self.passivas_extras = []         # raça, bênçãos, talentos (dados, para salvar)
        self.visual = {}                  # skins: {"roupa": chave, "chapeu": chave, "arma": chave}
        self.golpes_raros = []            # golpes raros liberados por conquistas (aprendidos no nível deles)
        self.peste = 0                    # nível da Peste que segue entre as lutas (até a fogueira ou o Tônico)
        self.golpes = GerenciadorDeGolpes(self)   # espaços + grimório (criado antes: o Lutador já aprende)
        super().__init__(
            nome, classe.sprite_da_aparencia(self.aparencia), classe.atributos_iniciais.copia(),
            classe.habilidades_iniciais(self.aparencia), classe.passivas, classe.iniciativa, lado="herois",
        )
        self._passivas_fixas = list(self.passivas)

    # ---------------- classe, subclasse e especialização (vêm da trilha) ----------------
    @property
    def classe(self):
        return self.trilha.classe

    @property
    def subclasse(self):
        return self.trilha.subclasse

    @property
    def especializacao(self):
        return self.trilha.especializacao

    @property
    def equipamento(self):
        """Os espaços de equipamento (o Equipamentos funciona como o dicionário espaço -> peça)."""
        return self.equipamentos

    def _atualizar_roupa(self):
        """Sprite = roupa da trilha (ou skin de roupa) + traço da raça + peças equipadas + chapéu e arma das skins.

        A peça de cabeça some quando o herói usa uma skin de chapéu (a skin escolhida manda). Com arma
        equipada, a roupa é a desarmada (roguelike/visual_equipamento.py)."""
        from roguelike.skins import nome_do_sprite
        from roguelike.visual_equipamento import camadas_do_equipamento, tem_arma
        extras = [self.dados_da_raca.cosmetico] if self.dados_da_raca and self.dados_da_raca.cosmetico else []
        extras += camadas_do_equipamento(self.equipamentos, sem_cabeca=bool(self.visual.get("chapeu")))
        self.sprite = nome_do_sprite(self.trilha.sprite(self.classe.sprite_da_aparencia(self.aparencia)), self.visual,
                                     extras, desarmado=tem_arma(self.equipamentos))

    def vestir(self, visual):
        """Aplica as skins escolhidas (só visual)."""
        self.visual = {camada: chave for camada, chave in visual.items() if chave}
        self._atualizar_roupa()

    # ---------------- raça ----------------
    def definir_raca(self, chave):
        """Aplica a raça: bônus, imunidades, passivas dos dons, golpe racial e o traço visual."""
        from roguelike.racas import raca
        antes = self.vida_maxima
        self.dados_da_raca = raca(chave)
        self.raca = self.dados_da_raca.chave
        self._passivas_da_raca = self.dados_da_raca.criar_passivas()
        self._atualizar_passivas()
        self._atualizar_roupa()
        self._ajustar_vida(antes)

    def imunidades_atuais(self):
        raciais = self.dados_da_raca.imunidades if self.dados_da_raca is not None else set()
        das_pecas = {s for _, peca in self.equipamentos.pecas() for s in getattr(peca, "imune", [])}
        return set(self.imunidades) | raciais | das_pecas

    def golpes_raciais(self):
        return self.dados_da_raca.golpes() if self.dados_da_raca else []

    def preparar_para_combate(self):
        """Começa a luta sem status, menos a Peste, que vem da luta anterior (self.peste = nível)."""
        super().preparar_para_combate()
        if self.peste > 0:
            from roguelike.status import criar_status
            self.status["peste"] = criar_status("peste", acumulos=self.peste)

    # ---------------- vida e bônus ----------------
    def vida_base(self):
        regra = regras()["vida"]
        return (self.classe.vida_base + self.atributo("constituicao") * regra["por_constituicao"]
                + (self.nivel - 1) * regra["por_nivel"])

    def fontes_de_bonus(self):
        yield from super().fontes_de_bonus()
        yield regras()["herois"]["modificadores"]
        if self.dados_da_raca is not None:
            yield self.dados_da_raca.modificadores
        for especialidade in self.trilha.ativas():
            if especialidade.modificadores:
                yield especialidade.modificadores
        yield from self.equipamentos.modificadores()

    # ---------------- equipamento ----------------
    def equipar(self, item, espaco=None):
        """Coloca o item (ver Equipamentos.equipar). Devolve (deu_certo, [itens que saíram])."""
        antes = self.vida_maxima
        deu_certo, saiu = self.equipamentos.equipar(item, espaco)
        if deu_certo:
            self._equipamento_mudou(antes)
        return deu_certo, saiu

    def desequipar(self, espaco):
        """Tira o item do espaço e o devolve (None se vazio ou se é amaldiçoado e ainda está preso)."""
        antes = self.vida_maxima
        antigo = self.equipamentos.desequipar(espaco)
        if antigo is not None:
            self._equipamento_mudou(antes)
        return antigo

    def _equipamento_mudou(self, vida_maxima_antes):
        """Refaz as passivas das peças e dos sets, o sprite (camadas) e acompanha a vida."""
        self._passivas_do_equipamento = {origem: [criar_passiva(p) for p in lista]
                                         for origem, lista in self.equipamentos.passivas().items()}
        self._atualizar_passivas()
        self._atualizar_roupa()
        self._ajustar_vida(vida_maxima_antes)
        self.golpes.ajustar_espacos()

    def _atualizar_passivas(self):
        self.passivas = list(self._passivas_fixas) + list(getattr(self, "_passivas_da_raca", []))
        for lista in self._passivas_do_equipamento.values():
            self.passivas.extend(lista)

    def _ajustar_vida(self, vida_maxima_antes):
        """Ao trocar equipamento, a vida acompanha o aumento (e nunca passa do máximo)."""
        if not self.esta_vivo():
            return
        self.vida = max(1, min(self.vida_maxima, self.vida + max(0, self.vida_maxima - vida_maxima_antes)))

    def aprender(self, chave, nivel=1, perguntar=True):
        """Aprende um golpe (ver GerenciadorDeGolpes.aprender). Devolve um ResultadoAprendizado."""
        return self.golpes.aprender(chave, nivel, perguntar)

    def habilidades(self):
        """Os golpes do menu de combate: os equipados + os da arma/amuleto + o golpe racial."""
        lista = [(golpe(chave), self.niveis_habilidade[chave]) for chave in self.golpes.equipados]
        for chave in self.golpes_extras():
            lista.append((golpe(chave), 1))
        return lista

    def golpes_extras(self):
        """Golpes fora dos espaços: os que o equipamento ensina e os raciais (sempre nível 1)."""
        extras = self.habilidades_do_equipamento()
        return extras + [c for c in self.golpes_raciais() if c not in extras and c not in self.niveis_habilidade]

    def todos_os_golpes(self):
        """Equipados, grimório e pendentes (para a tela do grupo)."""
        return [(golpe(chave), nivel) for chave, nivel in self.niveis_habilidade.items()]

    def habilidades_do_equipamento(self):
        chaves = []
        for item in self.equipamento.values():
            chave = getattr(item, "habilidade", None)
            if chave and chave not in self.niveis_habilidade and chave not in chaves:
                chaves.append(chave)
        return chaves

    def nivel_da(self, chave):
        if chave in self.niveis_habilidade:
            return self.niveis_habilidade[chave]
        return 1 if chave in self.golpes_extras() else 0

    def nivel_para_iniciativa(self):
        return self.nivel

    # ---------------- nível ----------------
    def xp_para_proximo_nivel(self):
        regra = regras()["nivel"]
        return regra["xp_base"] + regra["xp_por_nivel"] * (self.nivel - 1)

    def nivel_maximo(self):
        return regras()["nivel"]["maximo"]

    def ganhar_xp(self, quantidade):
        """Soma XP e sobe de nível quantas vezes der. Devolve quantos níveis subiu."""
        if not self.esta_vivo():
            return 0
        quantidade = round(quantidade * (1 + self.bonus("xp_ganho")))     # humanos aprendem mais rápido
        self.xp += quantidade
        subiu = 0
        while self.nivel < self.nivel_maximo() and self.xp >= self.xp_para_proximo_nivel():
            self.xp -= self.xp_para_proximo_nivel()
            self.subir_nivel()
            subiu += 1
        if self.nivel >= self.nivel_maximo():
            self.xp = 0
        return subiu

    def subir_nivel(self):
        antes = self.vida_maxima
        regra = regras()["nivel"]
        self.nivel += 1
        self.pontos_atributo += regra["pontos_atributo"]
        self.pontos_habilidade += regra["pontos_habilidade"]
        for passiva in self.passivas:
            passiva.ao_subir_nivel(self)
        self.vida += self.vida_maxima - antes        # a vida nova já vem cheia
        for chave in self.golpes_do_nivel(self.nivel):
            if self.aprender(chave).situacao != "ja_sabe":
                titulo = "Golpe raro!" if golpe(chave).raro else "Golpe novo!"
                self.golpes.avisos.append((titulo, f"{self.nome} aprendeu {golpe(chave).nome}"))

    def golpes_do_nivel(self, nivel):
        """Golpes que chegam neste nível: da classe, da subclasse e os raros liberados."""
        chaves = list(self.classe.golpes_no_nivel(nivel))
        if self.subclasse is not None:
            chaves += self.subclasse.golpes_no_nivel(nivel)
        chaves += [c for c in self.golpes_raros if golpe(c).nivel_do_raro == nivel]
        return [c for i, c in enumerate(chaves) if c not in chaves[:i]]

    def distribuir_ponto(self, atributo):
        if self.pontos_atributo <= 0:
            return False
        antes = self.vida_maxima
        self.atributos.aumentar(atributo)
        self.pontos_atributo -= 1
        self.vida += max(0, self.vida_maxima - antes)
        return True

    # ---------------- habilidades ----------------
    def nivel_maximo_da(self, chave):
        limite = golpe(chave).nivel_maximo
        especiais = []
        if self.subclasse is not None:
            especiais += self.subclasse.golpes
        if self.especializacao is not None:
            especiais += self.especializacao.golpes
        if chave in especiais:
            return max(limite, regras()["nivel"]["maximo_habilidade_subclasse"])
        return limite

    def pode_melhorar(self, chave):
        return (self.pontos_habilidade > 0 and chave in self.niveis_habilidade
                and self.niveis_habilidade[chave] < self.nivel_maximo_da(chave))

    def melhorar_habilidade(self, chave):
        if not self.pode_melhorar(chave):
            return False
        self.niveis_habilidade[chave] += 1
        self.pontos_habilidade -= 1
        return True

    def escolher_subclasse(self, subclasse, inicial=False):
        """Põe a subclasse na trilha (vale até o fim da run).

        inicial=True (Capitã): o golpe-assinatura entra no lugar do último golpe da classe, que vai
        para o grimório. Os golpes dos níveis já alcançados também são aprendidos.
        """
        if (self.subclasse is not None or self.subclasse_bloqueada
                or subclasse not in self.classe.subclasses.values()):
            return False
        self.trilha.subclasse = subclasse
        for chave in subclasse.golpes_ate_o_nivel(self.nivel):
            resultado = self.aprender(chave)
            if inicial and chave == subclasse.assinatura and resultado.situacao == "escolher":
                self.golpes.decidir(chave, self.golpes.equipados[-1])
        self._passivas_fixas.extend(criar_passiva(p) for p in subclasse.passivas)
        self._atualizar_passivas()
        self._atualizar_roupa()
        return True

    def pode_especializar(self, especializacao):
        return (self.subclasse is not None and self.especializacao is None
                and especializacao.subclasse is self.subclasse and self.nivel >= especializacao.nivel_minimo)

    def escolher_especializacao(self, especializacao, forcar=False):
        """Forma avançada da subclasse (treinador). Dá bônus, uma passiva e um golpe novo."""
        if not forcar and not self.pode_especializar(especializacao):
            return False
        self.trilha.especializacao = especializacao
        if especializacao.golpe:
            self.aprender(especializacao.golpe)
        self._passivas_fixas.extend(criar_passiva(p) for p in especializacao.passivas)
        self._atualizar_passivas()
        self._atualizar_roupa()
        return True

    def adicionar_passiva(self, dados):
        """Passiva de raça, bênção ou talento (fica salva com o herói)."""
        passiva = criar_passiva(dados)
        self._passivas_fixas.append(passiva)
        self.passivas_extras.append(dados)
        self._atualizar_passivas()
        return passiva

    def nome_da_classe(self):
        return self.trilha.nome()


_variantes_usadas = {}


def sprite_da_ficha(chave, ficha):
    """O sprite de um inimigo. Com "variantes" na ficha (só visual), cada um que surge pega a próxima
    da lista; é um contador, não sorteio, para não mexer na sorte do combate."""
    variantes = ficha.get("variantes")
    if not variantes:
        return ficha.get("sprite", chave)
    vez = _variantes_usadas.get(chave, 0)
    _variantes_usadas[chave] = vez + 1
    return variantes[vez % len(variantes)]


class Inimigo(Lutador):
    """Inimigo criado a partir de uma ficha do inimigos.json (ver inimigos.py)."""

    def __init__(self, chave, ficha):
        self.chave = chave
        self.ficha = ficha
        self.vida_da_ficha = ficha["vida"]
        self.defesa_base = ficha.get("defesa", 0)
        self.categoria = ficha.get("categoria", "comum")      # comum, elite, mini_chefe ou chefe
        self.eh_chefe = self.categoria in ("mini_chefe", "chefe")
        self.objeto = ficha.get("objeto", False)             # não age nem conta para vencer (ex.: Queijo Real)
        self.recompensa_xp = ficha.get("xp", 5)
        self.recompensa_ouro = tuple(ficha.get("ouro", (1, 3)))
        # Fraquezas e resistências a elementos (família + exceções do elementos.json + ficha)
        self.resistencias = resistencias_do_inimigo(chave, ficha.get("familia"), ficha.get("resistencias"))
        self._modificadores_de_elemento = como_modificadores(self.resistencias)
        super().__init__(
            ficha["nome"], sprite_da_ficha(chave, ficha), ficha.get("atributos"), ficha.get("habilidades"),
            ficha.get("passivas"), ficha.get("iniciativa", (3, 8)), ficha.get("imune", ()), lado="inimigos",
        )
        for chave_habilidade, nivel in ficha.get("niveis", {}).items():
            self.niveis_habilidade[chave_habilidade] = nivel
        self.padrao = list(ficha.get("padrao", []))           # ataques do chefe (uma fase de vida pode trocar)

    def vida_base(self):
        return self.vida_da_ficha * regras()["escala_inimigos"]["vida_base"]

    def fontes_de_bonus(self):
        yield from super().fontes_de_bonus()
        yield {"defesa": self.defesa_base}
        yield self.ficha.get("bonus", {})
        yield self._modificadores_de_elemento

    def energia_inicial(self):
        return self.ficha.get("energia_inicial", regras()["energia"]["inicial"])

    def ganho_de_energia_fixo(self):
        """Chefes podem ganhar energia garantida a cada turno (ficha "energia_por_turno")."""
        return self.ficha.get("energia_por_turno", 0)

    def abates(self):
        """Quantos abates ele vale no bestiário e nas conquistas (um bando vale um por bicho; um objeto, nenhum)."""
        return 0 if self.objeto else 1


class Invocacao(Inimigo):
    """Criatura invocada. Fica mais forte com o nível da habilidade que a chamou."""

    def __init__(self, chave, ficha, dono, nivel=1):
        super().__init__(chave, ficha)
        self.dono = dono
        self.lado = dono.lado
        self.eh_invocacao = True
        self.rodadas_restantes = ficha.get("duracao")      # None = fica até morrer
        crescimento = nivel - 1
        self.ajustes = {"vida_percentual": 0.2 * crescimento, "dano_causado": 0.15 * crescimento}
        self.vida = self.vida_maxima

    def vida_base(self):
        return self.vida_da_ficha          # invocações não usam o fator de vida dos inimigos
