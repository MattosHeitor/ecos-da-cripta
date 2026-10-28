"""Inteligência dos inimigos (e das invocações).

    IA            comum: sorteia uma habilidade útil e um alvo variado
    ├── IAAgressiva    prefere golpes caros e alvos com pouca vida
    ├── IASuporte      cura e fortalece os aliados antes de atacar
    └── IAPadrao       segue um padrão que depende da energia (ficha "padrao")
        └── IAChefe    o mesmo, revelando ao jogador o próximo golpe

A ficha do inimigo (inimigos.json) diz qual usar: "ia": "agressiva".
"""


class Escolha:
    def __init__(self, habilidade=None, alvo=None):
        self.habilidade = habilidade      # None = concentrar
        self.alvo = alvo


class IA:
    CHANCE_DE_GUARDAR_ENERGIA = 0.25

    # ---------------- habilidades ----------------
    def utilidade(self, habilidade, lutador, combate):
        """Peso da habilidade agora (0 = inútil)."""
        alvos = combate.alvos_validos(lutador, habilidade)
        if not alvos:
            return 0
        if habilidade.tem_efeito("reviver"):
            return 3
        if habilidade.tem_efeito("cura") and not habilidade.ofensiva():
            feridos = [a for a in alvos if a.fracao_vida() < 0.7]
            return 3 if feridos else 0
        if not habilidade.ofensiva():
            # Buff que todos os alvos já têm não serve
            novos = [e.dados["status"] for e in habilidade.efeitos if e.dados["tipo"] == "status"]
            if novos and all(a.tem_status(s) for a in alvos for s in novos):
                return 0
            if habilidade.tem_efeito("invocar"):
                return 2.5
            return 1.5
        return 1 + habilidade.custo * 0.6

    @staticmethod
    def desobedece(lutador, combate, habilidade, alvos=None):
        """Esta habilidade quebra um édito do outro lado (Rei dos Ratos)? Sem alvos: os de área contam todos."""
        if alvos is None:
            alvos = [] if habilidade.escolhe_alvo() else combate.alvos_validos(lutador, habilidade)
        return combate.proibicao(lutador, "habilidade", habilidade, alvos) is not None

    def opcoes(self, lutador, combate):
        opcoes = []
        for habilidade, nivel in lutador.habilidades():
            if habilidade.pode_usar(lutador) and not self.desobedece(lutador, combate, habilidade):
                peso = self.utilidade(habilidade, lutador, combate)
                if peso > 0:
                    opcoes.append((habilidade, peso))
        return opcoes

    def escolher_habilidade(self, lutador, combate, opcoes):
        habilidades = [h for h, _ in opcoes]
        pesos = [p for _, p in opcoes]
        return combate.rng.choices(habilidades, weights=pesos)[0]

    def deve_guardar_energia(self, lutador, combate, opcoes):
        """Se só sobrou o golpe grátis e existe algo melhor guardado, às vezes concentra."""
        caras = [h for h, _ in lutador.habilidades() if h.custo > lutador.energia]
        so_gratis = all(h.custo == 0 for h, _ in opcoes)
        return caras and so_gratis and combate.rng.random() < self.CHANCE_DE_GUARDAR_ENERGIA

    # ---------------- alvos ----------------
    def peso_do_alvo(self, alvo, lutador):
        # Invocações "chamam atenção" e absorvem golpes; furtividade (gnomos) faz ser menos escolhido;
        # objetos (o Queijo Real) quase não atraem golpes; o nó exposto da Rainha (fere a roda toda) atrai muito
        peso = 1.5 if alvo.eh_invocacao else (0.25 if getattr(alvo, "objeto", False) else 1.0)
        if getattr(alvo, "roda", None):
            peso = 3.0
        return peso * max(0.1, 1 - alvo.stat("furtividade"))

    def escolher_alvo(self, lutador, combate, habilidade):
        alvos = combate.alvos_validos(lutador, habilidade)
        if not alvos:
            return None
        alvos = [a for a in alvos if not self.desobedece(lutador, combate, habilidade, [a])] or alvos
        if habilidade.alvo == "aliado":
            if habilidade.tem_efeito("cura"):
                return min(alvos, key=lambda a: a.fracao_vida())
            return combate.rng.choice(alvos)
        if habilidade.alvo == "aliado_caido":
            return alvos[0]
        pesos = [self.peso_do_alvo(a, lutador) for a in alvos]
        return combate.rng.choices(alvos, weights=pesos)[0]

    # ---------------- decisão ----------------
    def escolher(self, lutador, combate):
        opcoes = self.opcoes(lutador, combate)
        if not opcoes or self.deve_guardar_energia(lutador, combate, opcoes):
            return Escolha()
        habilidade = self.escolher_habilidade(lutador, combate, opcoes)
        alvo = self.escolher_alvo(lutador, combate, habilidade) if habilidade.escolhe_alvo() else None
        return Escolha(habilidade, alvo)

    def intencao(self, lutador, combate):
        """O que ele pretende fazer (só os chefes revelam)."""
        return None


class IAAgressiva(IA):
    CHANCE_DE_GUARDAR_ENERGIA = 0.1

    def utilidade(self, habilidade, lutador, combate):
        peso = super().utilidade(habilidade, lutador, combate)
        return peso * 1.5 if habilidade.ofensiva() else peso * 0.5

    def peso_do_alvo(self, alvo, lutador):
        # Quanto menos vida, mais atraente
        return super().peso_do_alvo(alvo, lutador) * (1.3 - alvo.fracao_vida()) + 0.1


class IASuporte(IA):
    def utilidade(self, habilidade, lutador, combate):
        peso = super().utilidade(habilidade, lutador, combate)
        return peso * 2 if not habilidade.ofensiva() else peso


class IAPadrao(IA):
    """Segue a lista "padrao" da ficha, do maior requisito de energia ao menor:

        "padrao": [{"energia": 6, "habilidade": "terremoto"},
                   {"energia": 3, "habilidade": "golpe_duplo"},
                   {"energia": 0, "habilidade": "pisao"}]

    "vida_abaixo" (opcional) só usa a regra com a vida abaixo dessa fração (ex.: curar-se a 85%).
    "requer_aliado" (opcional) só usa a regra com um aliado vivo dessa chave (ex.: o Rei come o Queijo Real).
    Inimigos comuns com um truque (ex.: o Rato Bombardeiro ferido acende o pavio) usam esta; os chefes, a IAChefe.
    """

    def regra_para(self, lutador, energia, combate=None):
        for regra in getattr(lutador, "padrao", None) or lutador.ficha.get("padrao", []):
            if energia >= regra["energia"] and lutador.fracao_vida() <= regra.get("vida_abaixo", 1) \
                    and lutador.recarga_de(regra["habilidade"]) <= 0 \
                    and self.tem_o_aliado(lutador, combate, regra.get("requer_aliado")):
                return regra
        return None

    @staticmethod
    def tem_o_aliado(lutador, combate, chave):
        if chave is None or combate is None:
            return chave is None
        return any(getattr(a, "chave", None) == chave for a in combate.aliados_de(lutador))

    def escolher(self, lutador, combate):
        from roguelike.golpes import golpe as buscar
        regra = self.regra_para(lutador, lutador.energia, combate)
        if regra is not None:
            habilidade = buscar(regra["habilidade"])
            if habilidade.pode_usar(lutador) and combate.alvos_validos(lutador, habilidade):
                alvo = self.escolher_alvo(lutador, combate, habilidade) if habilidade.escolhe_alvo() else None
                return Escolha(habilidade, alvo)
        return super().escolher(lutador, combate)


class IAChefe(IAPadrao):
    """O padrão dos chefes, revelado ao jogador: a tela mostra a energia e o próximo golpe."""

    def intencao(self, lutador, combate):
        """A habilidade que ele vai usar no próximo turno (para o jogador se preparar)."""
        from roguelike.golpes import golpe as buscar
        energia = min(lutador.energia_maxima, lutador.energia + lutador.ganho_de_energia_fixo())
        regra = self.regra_para(lutador, energia, combate)
        return buscar(regra["habilidade"]) if regra else None


TIPOS_DE_IA = {
    "comum": IA,
    "agressiva": IAAgressiva,
    "suporte": IASuporte,
    "chefe": IAChefe,
    "padrao": IAPadrao,
}

_instancias = {}


def ia_do(lutador):
    """A IA de um lutador (heróis sem jogador, ex.: nos testes, usam a de suporte)."""
    ficha = getattr(lutador, "ficha", None)
    tipo = ficha.get("ia", "comum") if ficha else "suporte"
    if tipo not in _instancias:
        _instancias[tipo] = TIPOS_DE_IA[tipo]()
    return _instancias[tipo]
