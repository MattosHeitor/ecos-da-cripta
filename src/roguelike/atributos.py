"""Atributos (FOR, DES, CON, INT, FÉ, SOR, CAR) e os valores que saem deles.

Os valores "derivados" (chance de crítico, esquiva, ganho de energia...)
seguem a fórmula do regras.json:

    valor = base + soma(atributo x peso)      limitado entre min e max
"""

from roguelike.dados import regras


def nomes_dos_atributos():
    """Lista dos 7 atributos, ex.: ["forca", "destreza", ...]."""
    return list(regras()["atributos"])


def sigla(atributo):
    """Nome curto para a tela, ex.: "forca" -> "FOR"."""
    return regras()["nomes_atributos"].get(atributo, atributo.upper())


def eh_derivado(nome):
    return nome in regras()["derivados"]


def valor_derivado(nome, atributos, bonus=0.0):
    """Calcula um valor derivado.

    - atributos: função que recebe o nome do atributo e devolve o valor dele.
    - bonus: soma dos bônus de itens, status e passivas.
    """
    formula = regras()["derivados"][nome]
    valor = formula["base"]
    for atributo in nomes_dos_atributos():
        peso = formula.get(atributo)
        if peso:
            valor += atributos(atributo) * peso
    valor += bonus
    return max(formula["min"], min(formula["max"], valor))


class Atributos:
    """Os pontos de atributo de um personagem (sem contar bônus)."""

    def __init__(self, valores=None):
        self.valores = {nome: 0 for nome in nomes_dos_atributos()}
        for nome, valor in (valores or {}).items():
            if nome not in self.valores:
                raise ValueError(f"Atributo desconhecido: {nome}")
            self.valores[nome] = valor

    def __getitem__(self, nome):
        return self.valores[nome]

    def aumentar(self, nome, quantidade=1):
        if nome not in self.valores:
            raise ValueError(f"Atributo desconhecido: {nome}")
        self.valores[nome] += quantidade

    def total(self):
        return sum(self.valores.values())

    def copia(self):
        return Atributos(dict(self.valores))

    def para_dict(self):
        return dict(self.valores)
