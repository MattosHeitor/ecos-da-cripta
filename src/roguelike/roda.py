"""A Rainha dos Ratos (Reino dos Ratos, etapa 5B): uma roda de ratos presos pelas caudas num nó.

    NoDeCaudas(Inimigo)   o nó no meio da roda, que é a Rainha: a vida dela é a soma da vida dos ratos da roda

Os ratos são inimigos de verdade (vida, nome e papel), criados pelo nó no começo da luta (passiva "roda" em
passivas.py, que também faz a roda girar). Quando o último rato cai, a Rainha cai junto. A ficha do nó tem
"no_da_roda": true (inimigos.criar_inimigo escolhe esta classe).
"""

from roguelike.lutador import Inimigo


class NoDeCaudas(Inimigo):
    def __init__(self, chave, ficha):
        self.roda = []                         # os ratos, na ordem em que estão presos na roda
        self.giro = 0                          # quantas casas a roda já girou
        super().__init__(chave, ficha)

    @property
    def vida(self):
        return sum(r.vida for r in self.roda) if self.roda else self._vida

    @vida.setter
    def vida(self, valor):
        self._vida = valor                     # (só vale antes de a roda se formar)

    @property
    def vida_maxima(self):
        return sum(r.vida_maxima for r in self.roda) if self.roda else super().vida_maxima

    def ratos_vivos(self):
        return [r for r in self.roda if r.esta_vivo()]

    def caidos(self):
        return len(self.roda) - len(self.ratos_vivos())

    def frente(self, quantos, giro=None):
        """Os ratos virados para os heróis agora (ou depois de girar até 'giro')."""
        vivos = self.ratos_vivos()
        if not vivos:
            return []
        giro = self.giro if giro is None else giro
        return [vivos[(giro + k) % len(vivos)] for k in range(min(quantos, len(vivos)))]
