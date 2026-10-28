"""Raças (racas.json): bônus, penalidades, imunidades, um traço visual e dons especiais.

    Raca
     ├── modificadores   bônus e penalidades fixos (entram no stat() do herói)
     ├── imunidades      status que não pegam (Morto-Vivo: veneno e sangramento)
     ├── cosmetico       camada desenhada por cima do herói (gorro do gnomo, barba do anão...)
     └── dons            lista de DomRacial:
           DomPassivo      uma passiva de passivas.py (Fúria do Meio-Orc...)
           DomDeGolpe      golpe racial fora dos espaços, com recarga (Metamorfose do Draconiano)
           DomDeLoot       chance de um item extra por combate (Gnomo)
           DomDeForja      libera as receitas com "requer_raca" (Anão)
           DomDeRenascer   levanta uma vez por combate (Morto-Vivo)

A raça NÃO fica salva como passivas no herói: o herói guarda só a chave (heroi.raca) e
Heroi.definir_raca() monta tudo de novo ao criar ou carregar, então mudar o JSON vale até para saves antigos.
"""

from roguelike.dados import carregar, sem_comentarios
from roguelike.passivas import criar_passiva

RACA_PADRAO = "humano"


class DomRacial:
    """Um poder da raça. Subclasses mudam só o que usam."""

    def __init__(self, dados):
        self.dados = dict(dados)
        self.nome = dados.get("nome", "")

    def passivas(self):
        """Dados das passivas que este dom põe no herói."""
        return []

    def golpes(self):
        """Golpes raciais (aparecem no menu de combate, fora dos espaços)."""
        return []

    def chance_de_loot(self):
        return 0.0

    def forja(self):
        return False


class DomPassivo(DomRacial):
    def passivas(self):
        return [self.dados["passiva"]]


class DomDeGolpe(DomRacial):
    def golpes(self):
        return [self.dados["golpe"]]


class DomDeLoot(DomRacial):
    def chance_de_loot(self):
        return self.dados.get("chance", 0.3)


class DomDeForja(DomRacial):
    def forja(self):
        return True


class DomDeRenascer(DomRacial):
    def passivas(self):
        return [{"tipo": "renascer", "vida": self.dados.get("vida", 0.3), "nome": self.nome}]


TIPOS_DE_DOM = {"passivo": DomPassivo, "golpe": DomDeGolpe, "loot": DomDeLoot, "forja": DomDeForja,
                "renascer": DomDeRenascer}


def criar_dom(dados):
    try:
        return TIPOS_DE_DOM[dados["tipo"]](dados)
    except KeyError:
        raise ValueError(f"Tipo de dom racial desconhecido: {dados.get('tipo')}") from None


class Raca:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.preco = dados.get("preco", 0)
        self.conquista = dados.get("conquista")
        self.descricao = dados.get("descricao", "")
        self.vantagens = list(dados.get("vantagens", []))
        self.desvantagens = list(dados.get("desvantagens", []))
        self.modificadores = dict(dados.get("modificadores", {}))
        self.imunidades = set(dados.get("imunidades", []))
        self.cosmetico = dados.get("cosmetico")
        self.dons = [criar_dom(d) for d in dados.get("dons", [])]

    # ---------------- o que a raça dá ----------------
    def criar_passivas(self):
        """Passivas novas (cada herói tem as suas, porque elas guardam estado no combate)."""
        return [criar_passiva(p) for dom in self.dons for p in dom.passivas()]

    def golpes(self):
        return [chave for dom in self.dons for chave in dom.golpes()]

    def chance_de_loot(self):
        return sum(dom.chance_de_loot() for dom in self.dons)

    def forja(self):
        return any(dom.forja() for dom in self.dons)

    def __repr__(self):
        return f"Raca({self.chave!r})"


_racas = {}


def todas_as_racas():
    """{chave: Raca} na ordem do JSON."""
    if not _racas:
        for chave, dados in sem_comentarios(carregar("racas")).items():
            _racas[chave] = Raca(chave, dados)
    return _racas


def raca(chave):
    """A Raca da chave (desconhecida = humano, para saves antigos)."""
    racas = todas_as_racas()
    return racas.get(chave) or racas[RACA_PADRAO]


# Passivas que as raças antigas (fase 2) gravavam em heroi.passivas_extras: saem ao carregar
PASSIVAS_ANTIGAS = [
    {"tipo": "ponto_extra", "a_cada": 2, "pontos": 1, "nome": "Adaptável"},
    {"tipo": "maior_atributo", "percentual": 0.05, "nome": "Talento Natural"},
    {"tipo": "regenerar_perdida", "fracao": 0.1, "nome": "Carne Morta"},
    {"tipo": "bonus", "modificadores": {"cura_recebida": -0.3, "chance_bloqueio": -0.05}, "nome": "Corpo Frio"},
    {"tipo": "roubo_por_sangramento", "por_acumulo": 0.05, "maximo": 0.5, "nome": "Sede de Sangue"},
    {"tipo": "bonus", "modificadores": {"roubo_vida": 0.03, "vida_percentual": -0.2}, "nome": "Pálido"},
    {"tipo": "bonus", "modificadores": {"defesa": 1, "constituicao": 2, "dano_recebido": -0.05,
                                        "chance_esquiva": -0.05, "iniciativa": -1}, "nome": "Pele de Pedra"},
    {"tipo": "bonus", "modificadores": {"destreza": 2, "chance_esquiva": 0.05, "chance_critico": 0.03,
                                        "vida_percentual": -0.1}, "nome": "Graça Élfica"},
    {"tipo": "bonus", "modificadores": {"forca": 3, "dano_causado": 0.05, "inteligencia": -2,
                                        "ganho_energia": -0.1}, "nome": "Sangue Orc"},
]
