"""Inventário: uma mochila de pilhas (chave do item -> quantidade).

Cada jogador tem uma mochila (posse.InventarioPessoal, com limite de pilhas) que os heróis dele
dividem, e o grupo tem um baú compartilhado (sem limite). Em combate o herói só usa o que está
na mochila (heroi.inventario).
"""

from roguelike.itens import item


class Inventario:
    def __init__(self, capacidade=None):
        self.capacidade = capacidade          # máximo de pilhas diferentes (None = sem limite)
        self.itens = {}                       # chave -> quantidade (na ordem em que chegaram)

    # ---------------- consulta ----------------
    def quantidade(self, chave):
        return self.itens.get(chave, 0)

    def tem(self, chave, quantidade=1):
        return self.quantidade(chave) >= quantidade

    def cabe(self, chave):
        return self.capacidade is None or chave in self.itens or len(self.itens) < self.capacidade

    def pilhas(self, tipo=None):
        """Lista de (Item, quantidade), opcionalmente só de um tipo ("material"...)."""
        resultado = []
        for chave, quantidade in self.itens.items():
            objeto = item(chave)
            if tipo is None or objeto.tipo == tipo:
                resultado.append((objeto, quantidade))
        return resultado

    def vazio(self):
        return not self.itens

    def __contains__(self, chave):
        return self.tem(chave)

    # ---------------- mudanças ----------------
    def adicionar(self, chave, quantidade=1):
        """Guarda o item. Devolve False se não houver espaço."""
        item(chave)                           # confere se existe
        if quantidade <= 0:
            return True
        if not self.cabe(chave):
            return False
        self.itens[chave] = self.quantidade(chave) + quantidade
        return True

    def remover(self, chave, quantidade=1):
        """Tira o item. Devolve False se não houver o suficiente."""
        if not self.tem(chave, quantidade):
            return False
        self.itens[chave] -= quantidade
        if self.itens[chave] == 0:
            del self.itens[chave]
        return True

    def mover_para(self, destino, chave, quantidade=1):
        """Passa itens para outro inventário (só se couber lá)."""
        if not self.tem(chave, quantidade) or not destino.cabe(chave):
            return False
        self.remover(chave, quantidade)
        destino.adicionar(chave, quantidade)
        return True

    # ---------------- salvar ----------------
    def para_dict(self):
        return {"capacidade": self.capacidade, "itens": dict(self.itens)}

    @classmethod
    def de_dict(cls, dados):
        inventario = cls(dados.get("capacidade"))
        inventario.itens = dict(dados.get("itens", {}))
        return inventario
