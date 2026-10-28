"""Bando: um monte de bichos pequenos lutando como um lutador só (ex.: "Ratos ×12").

    Inimigo
    └── Bando     a vida é a de todos juntos; cada pedaço de vida perdido derruba alguns bichos

Na ficha (inimigos.json): "bando": {"quantos": 12, "nome": "Ratos"}. Números em regras.json "bandos":
- vivos(): quantos ainda estão de pé = quantos x fração da vida (arredondado para cima);
- o nome mostra o contador ("Ratos ×7") e o dano cai junto com o bando ("dano_perdido");
- golpes em área machucam mais ("area") e golpes de um alvo só, menos ("alvo_unico");
- cada bicho conta como um abate (bestiário e conquistas).
"""

import math

from roguelike.dados import regras
from roguelike.lutador import Inimigo


class Bando(Inimigo):
    eh_bando = True

    def __init__(self, chave, ficha):
        dados = ficha["bando"]
        self.quantos = dados["quantos"]
        super().__init__(chave, ficha)
        self.nome_do_bando = dados.get("nome", ficha["nome"])

    # ---------------- o contador ----------------
    @property
    def nome(self):
        return f"{self.nome_do_bando} ×{self.vivos()}"

    @nome.setter
    def nome(self, valor):
        self.nome_do_bando = valor                 # (o Lutador guarda o nome da ficha ao nascer)

    def vivos(self):
        """Quantos bichos ainda estão de pé."""
        if self.vida <= 0:
            return 0
        return max(1, min(self.quantos, math.ceil(self.quantos * self.vida / self.vida_maxima)))

    # ---------------- regras do bando ----------------
    def bonus(self, nome):
        """Com menos bichos, menos dentes: o dano causado cai junto com o bando."""
        total = super().bonus(nome)
        if nome == "dano_causado" and self.vida > 0:
            total -= regras()["bandos"]["dano_perdido"] * (1 - self.vivos() / self.quantos)
        return total

    def multiplicador_contra(self, direto):
        regra = regras()["bandos"]
        return 1 + (regra["alvo_unico"] if direto else regra["area"])

    def abates(self):
        return self.quantos
