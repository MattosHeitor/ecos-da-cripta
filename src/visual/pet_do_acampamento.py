"""O bicho do acampamento (o Rato Branco, depois de vencer o Reino dos Ratos; regras.json "pets").

Fica num lugar perto do fogo, sentado ou cheirando o chão, e de vez em quando corre até outro lugar. Só visual:
a tela do acampamento o põe na cena como os outros (pelos pés), com o quadro de "anim" e o lado de "espelhar".

    pet = PetDoAcampamento("rato_branco", [(700, 652), (1034, 628)], olhar_para=(640, 612))
    pet.atualizar(dt)
    pet.pe, pet.anim, pet.espelhar
"""

import math
import random


class PetDoAcampamento:
    VELOCIDADE = 170            # pixels por segundo, correndo
    PARADO = (4.0, 9.0)         # segundos num lugar antes de correr para outro
    CICLO = 7.0                 # parado: senta um tempo, levanta e cheira, senta de novo

    def __init__(self, sprite, lugares, olhar_para=None, semente=3):
        self.sprite = sprite
        self.lugares = [tuple(lugar) for lugar in lugares]
        self.olhar_para = olhar_para            # parado, olha para cá (a fogueira); o sprite olha para a direita
        self.rng = random.Random(semente)
        self.lugar = 0
        self.pe = self.lugares[0]
        self.destino = None                     # índice do lugar para onde está correndo
        self.espera = self.rng.uniform(*self.PARADO)
        self.tempo = 0.0
        self.espelhar = self.virado_para(self.olhar_para)

    def virado_para(self, ponto):
        return ponto is not None and ponto[0] < self.pe[0]

    @property
    def correndo(self):
        return self.destino is not None

    @property
    def anim(self):
        if self.correndo:
            return "correr"
        return "sentado" if self.tempo % self.CICLO < self.CICLO * 0.65 else "parado"

    def correr_para(self, indice):
        self.destino = indice
        self.espelhar = self.virado_para(self.lugares[indice])

    def atualizar(self, dt):
        self.tempo += dt
        if not self.correndo:
            self.espera -= dt
            if self.espera <= 0 and len(self.lugares) > 1:
                self.correr_para(self.rng.choice([i for i in range(len(self.lugares)) if i != self.lugar]))
            return
        alvo = self.lugares[self.destino]
        dx, dy = alvo[0] - self.pe[0], alvo[1] - self.pe[1]
        distancia = math.hypot(dx, dy)
        passo = self.VELOCIDADE * dt
        if distancia <= passo:                  # chegou: senta e volta a olhar para o fogo
            self.pe, self.lugar, self.destino = alvo, self.destino, None
            self.espera = self.rng.uniform(*self.PARADO)
            self.espelhar = self.virado_para(self.olhar_para)
        else:
            self.pe = (self.pe[0] + dx / distancia * passo, self.pe[1] + dy / distancia * passo)
