"""Lendas: personagens únicos de destaque máximo.

    PrimeiroHeroi   chefe secreto atrás do altar: o primeiro paladino, em armadura antiga que brilha,
                    auréola dourada, runas acesas e partículas de luz; ao morrer vira luz
"""
import math

import numpy as np

from ..motor import Mat, metal, v2, misturar
from .. import texturas as T
from ..criaturas.acabamento import ComAcabamento, olhos_humanoides
from .herois import Paladino

LUZ_DOURADA = (255, 226, 140)


class PrimeiroHeroi(ComAcabamento, Paladino):
    """O Primeiro Herói: armadura antiga de marfim e ouro que emite luz, tabardo celeste, capa branca,
    auréola dourada atrás da cabeça, runas acesas e uma aura quase divina."""
    nome = "primeiro_heroi"
    marfim = metal((236, 224, 176), especular=(255, 255, 240), contraste=1.1)
    tabardo = Mat((64, 104, 186), 6, desce=0.3, ruido=0.1)
    capa_mat = Mat((236, 232, 220), 6, desce=0.5, ruido=0.08, relevo=0.6, arredonda=0.5)

    def antes(self, tela, ctx, J):
        if not self.vivo(ctx):
            return
        H = self.H
        c = J["cabeca"] - v2(-J["hu"][1], J["hu"][0]) * (H * 0.03)
        for k in range(16):                                                # raios da auréola girando
            a = ctx.a * 0.4 + k * math.pi / 8
            comp = H * (0.2 if k % 2 else 0.14)
            tela.chapado(tela.poly([c + v2(math.cos(a - 0.06), math.sin(a - 0.06)) * (H * 0.1),
                                    c + v2(math.cos(a + 0.06), math.sin(a + 0.06)) * (H * 0.1),
                                    c + v2(math.cos(a), math.sin(a)) * (H * 0.1 + comp)]),
                         (255, 240, 190) if k % 2 else (255, 214, 120), emite=True)
        tela.chapado(tela.circulo(c, H * 0.1) & ~tela.circulo(c, H * 0.085), (255, 250, 220), emite=True)
        tela.brilho(c, H * 0.35, LUZ_DOURADA, 0.5)

    def acabar(self, tela, ctx, J):
        H = self.H
        vivo = self.vivo(ctx)
        corpo = (tela.alfa > 0) & ~tela.emite
        ys, xs = np.nonzero(corpo)                                         # a armadura irradia luz
        tela.cor[ys, xs] = np.clip(tela.cor[ys, xs] * 0.88 + np.array((255, 240, 200), np.float32) * 0.14, 0, 255)
        for d in ((1, 0), (-1, 0), (0, -1)):
            T.luz_de_borda(tela, corpo, LUZ_DOURADA, d, forca=0.35)
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.06, H * 0.16), n=4, passos=3, cor=(255, 236, 160),
                     emite=vivo, brilho=0.25 if vivo else 0.0, semente=7)      # runas antigas acesas
        if vivo:
            for p in olhos_humanoides(J):
                tela.px(p[0], p[1], (255, 250, 210), emite=True)
                tela.brilho(p, 3, LUZ_DOURADA, 0.6)
            T.aura(tela, tela.alfa > 0, LUZ_DOURADA, raio=5, forca=0.45, fase=ctx.a)
            T.particulas(tela, J["peito"], (H * 0.4, H * 0.4), (255, 244, 200), n=10, fase=ctx.a, sobe=H * 0.45, semente=8)
            if ctx.golpe:
                T.particulas(tela, J["mao_f"], (H * 0.15, H * 0.15), (255, 255, 230), n=12, fase=ctx.a, sobe=H * 0.1, semente=9)
                tela.brilho(J["mao_f"], H * 0.3, LUZ_DOURADA, 0.6)
        else:                                                              # se desfaz em luz
            T.esfumacar(tela, tela.alfa > 0, J["peito"], cor=misturar(LUZ_DOURADA, (255, 255, 255), 0.4), fase=ctx.a,
                        comeu=0.45 + 0.15 * ctx.i, fiapos=12, sobe=14)
            T.particulas(tela, J["peito"], (H * 0.4, H * 0.2), (255, 244, 200), n=16, fase=ctx.a, sobe=H * 0.6, semente=10)
