"""Sets de equipamento (sets.json): peças que, juntas, dão bônus com 2, 3 e 4 equipadas."""

from roguelike.dados import carregar, sem_comentarios


class BonusDeSet:
    def __init__(self, pecas, dados):
        self.pecas = pecas                           # quantas peças precisam estar equipadas
        self.modificadores = dict(dados.get("modificadores", {}))
        self.passivas = list(dados.get("passivas", []))
        self.descricao = dados.get("descricao", "")


class ConjuntoDeEquipamento:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.pecas = list(dados["pecas"])
        self.bonus = sorted((BonusDeSet(int(n), b) for n, b in dados["bonus"].items()), key=lambda b: b.pecas)

    def ativos(self, quantidade):
        """Bônus liberados com 'quantidade' peças equipadas."""
        return [b for b in self.bonus if quantidade >= b.pecas]

    def __repr__(self):
        return f"ConjuntoDeEquipamento({self.chave!r})"


_sets = {}


def todos_os_sets():
    if not _sets:
        for chave, dados in sem_comentarios(carregar("sets")).items():
            _sets[chave] = ConjuntoDeEquipamento(chave, dados)
    return _sets


def conjunto(chave):
    return todos_os_sets()[chave]
