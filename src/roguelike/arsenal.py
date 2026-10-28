"""Arsenal: equipamentos guardados entre runs (o estande de armas do acampamento).

As peças só entram quando a run termina vencida ou com a fuga (enfrentando o chefe da saída).
Na expedição, cada herói pode levar peças do arsenal (equipamento inicial): elas são emprestadas,
ou seja, continuam no arsenal e não contam de novo quando a run termina.
"""

from roguelike.dados import regras
from roguelike.exemplares import exportar, importar
from roguelike.itens import item, existe, ordem_da_raridade


class Arsenal:
    def __init__(self):
        self.pecas = {}                     # chave do item (ou do exemplar) -> quantidade

    @staticmethod
    def capacidade():
        return regras()["arsenal"]["capacidade"]

    def total(self):
        return sum(self.pecas.values())

    def quantidade(self, chave):
        return self.pecas.get(chave, 0)

    def pilhas(self):
        """[(Item, quantidade)] da raridade maior para a menor."""
        pilhas = [(item(c), n) for c, n in self.pecas.items() if existe(c)]
        return sorted(pilhas, key=lambda p: (-ordem_da_raridade(p[0].raridade), p[0].nome))

    def guardar(self, chaves):
        """Guarda as peças (lista de chaves, repetidas = várias). Devolve as que ficaram (acima da
        capacidade, saem primeiro as de raridade menor)."""
        for chave in chaves:
            self.pecas[chave] = self.pecas.get(chave, 0) + 1
        descartadas = self.aparar()
        guardadas = list(chaves)
        for chave in descartadas:
            if chave in guardadas:
                guardadas.remove(chave)
        return guardadas

    def aparar(self):
        """Respeita a capacidade tirando as peças mais simples. Devolve as que saíram."""
        saiu = []
        while self.total() > self.capacidade():
            pior = min(self.pecas, key=lambda c: (ordem_da_raridade(item(c).raridade), item(c).preco))
            self.remover(pior)
            saiu.append(pior)
        return saiu

    def remover(self, chave, quantidade=1):
        if self.quantidade(chave) < quantidade:
            return False
        self.pecas[chave] -= quantidade
        if self.pecas[chave] <= 0:
            del self.pecas[chave]
        return True

    # ---------------- salvar ----------------
    def para_dict(self):
        return {"pecas": dict(self.pecas), "exemplares": exportar([c for c in self.pecas if "#" in c])}

    @classmethod
    def de_dict(cls, dados):
        arsenal = cls()
        dados = dados or {}
        importar(dados.get("exemplares", {}))
        arsenal.pecas = {c: n for c, n in dados.get("pecas", {}).items() if existe(c) and n > 0}
        return arsenal
