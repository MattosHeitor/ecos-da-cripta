"""Inimigos nomeados com sprite próprio (antes usavam o sprite de um herói jogável sem mudança).

Os heróis corrompidos herdam a classe do herói de origem com o mixin Corrompido
(forja/criaturas/acabamento.py): o corpo escurece e perde a cor, veias brilham, os olhos acendem e
uma aura sobe. Cada um ainda troca materiais e desenha a própria deformação em deformar():

    Gnarl                 Rei dos Goblins: maior, coroa de ossos, manto de pele e maça cravejada
    CacadoraCorrompida    arqueira de capa negra, veias roxas, arco de osso e flechas de chama roxa
    CavaleiroCaido        armadura rachada e enferrujada, brilho vermelho no visor, espada de sombra
    BarbaroPossuido       chifres de demônio rasgando a cabeça, veias de brasa e fumaça vermelha
    FeiticeiraRenegada    manto rasgado, fogo virado em chama roxo-negra e orbes escuros girando
    AssassinaSemRosto     capuz com um rosto liso e branco, sem nada; adaga pingando veneno
    PaladinoProfano       armadura de marfim enegrecida, auréola invertida em brasa e lágrimas de sangue
"""
import math

import numpy as np

from ..motor import Mat, metal, v2, dir_ang
from ..humanoide import quadro_cabeca, quadro_tronco, capa
from .. import texturas as T
from .. import fx
from ..criaturas.acabamento import Corrompido, olhos_humanoides
from .herois import Guerreiro, Paladino, Barbaro, MagoElemental, Arqueira, Assassina, OSSO
from .variantes import GoblinBrutoSangrento, caveirinha


# ============================================================
# GNARL, REI DOS GOBLINS
# ============================================================

class Gnarl(GoblinBrutoSangrento):
    """Gnarl, Rei dos Goblins: um bruto maior com coroa de ossos, manto de pele e colar de dentes."""
    MANTO = Mat((96, 74, 56), 6, ruido=0.6, dither=0.6, relevo=0.8)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "gnarl"
        self.H = 68
        self.larg, self.alt = int(self.H * 2.05), int(self.H * 1.6)
        self.ancora = (int(self.H * 1.08), self.alt - 4)
        self.pele = Mat((106, 104, 70), 6, relevo=1.1)

    def antes(self, tela, ctx, J):
        m = capa(tela, J, self.MANTO, comprimento=0.5, vento=0.03 * math.sin(ctx.a), larg=0.2, rasgos=7, semente=31,
                 gola=True)
        T.pelagem(tela, m, J["pescoco"], ang=math.pi / 2, comp=3, densidade=0.4, semente=31)

    def cabeca(self, tela, J, ctx):
        super().cabeca(tela, J, ctx)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        for k in range(5):                                                  # coroa de ossos
            x = -h * 0.35 + k * h * 0.2
            base = C.pt(x, h * 0.45)
            ponta = base + J["hu"] * (h * (0.45 if k % 2 == 0 else 0.3))
            tela.pintar(tela.poly([base - v2(1.2, 0), base + v2(1.2, 0), ponta]), OSSO)
        tela.traco(C.pt(-h * 0.45, h * 0.45), C.pt(h * 0.55, h * 0.48), (170, 140, 60))
        tela.px(*C.pt(h * 0.05, h * 0.47), (200, 30, 40))

    def acabar(self, tela, ctx, J):
        super().acabar(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        for k in range(6):                                                  # colar de dentes
            p = Q.pt(-0.05 * H + k * 0.025 * H, J["P"]["tronco"] * 0.93 - abs(k - 2.5) * 0.7)
            tela.px(p[0], p[1], OSSO[5])
            tela.px(p[0], p[1] + 1, OSSO[3])
        caveirinha(tela, Q.pt(0.04 * H, J["P"]["tronco"] * 0.8), r=H * 0.03)


# ============================================================
# HERÓIS CORROMPIDOS
# ============================================================

class CacadoraCorrompida(Corrompido, Arqueira):
    """A Caçadora Corrompida: capa negra em farrapos, veias roxas, arco de osso e flechas de chama roxa."""
    nome = "cacadora_corrompida"
    verde = Mat((50, 44, 54), 6, desce=0.3, ruido=0.15)
    capa_mat = Mat((34, 24, 40), 6, desce=0.4, ruido=0.25, relevo=0.6, arredonda=0.5)
    cor_corrupcao = (180, 70, 240)
    semente = 41

    def deformar(self, tela, ctx, J):
        H = self.H
        mao = J["mao_b"]
        for k in (-1, 1):                                                   # espinhos de osso no arco
            p = mao + v2(-1, k * H * 0.14)
            tela.pintar(tela.poly([p + v2(-1, 0), p + v2(1, 0), p + v2(-2, k * H * 0.05)]), OSSO.escuro(1))
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            ponta = mao + v2(H * 0.15 if ctx.i == 1 else H * 0.5, 0)
            fx.chama(tela, ponta, H * 0.1, H * 0.06, fx.FOGO_ROXO, fase=ctx.a, inclina=1.6, brilho=True)


class CavaleiroCaido(Corrompido, Guerreiro):
    """O Cavaleiro Caído: armadura rachada e enferrujada, tabardo rasgado e espada envolta em sombra."""
    nome = "cavaleiro_caido"
    tabardo = Mat((70, 18, 24), 6, desce=0.25, ruido=0.2)
    capa_mat = Mat((22, 20, 28), 6, desce=0.35, ruido=0.2, relevo=0.6, arredonda=0.5)
    aco = metal((96, 88, 92), ruido=0.55, especular=(190, 170, 160))
    cor_corrupcao = (220, 40, 50)
    sombrio = 0.3
    semente = 43

    def deformar(self, tela, ctx, J):
        H = self.H
        corpo = (tela.alfa > 0) & ~tela.emite
        T.manchas(tela, corpo, J["pelvis"], (100, 56, 36), escala=3, quantidade=0.3, forca=0.6, semente=44)   # ferrugem
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.08, H * 0.2), n=5, passos=4, cor=(24, 18, 22), emite=False,
                     semente=45)
        d = dir_ang(J["arma_f"])
        for t in (0.3, 0.55, 0.8):                                          # sombra subindo da lâmina
            p = J["mao_f"] + d * (H * 0.5 * t)
            T.particulas(tela, p, (2, 2), (150, 40, 60), n=2, fase=ctx.a + t * 3, sobe=H * 0.1, semente=int(t * 10))


class BarbaroPossuido(Corrompido, Barbaro):
    """O Bárbaro Possuído: chifres de demônio rasgando a cabeça, veias de brasa e fumaça vermelha."""
    nome = "barbaro_possuido"
    arma = "Machado"
    pele = Mat((150, 98, 90), 6, relevo=1.1, dither=0.3)
    cor_corrupcao = (255, 70, 30)
    cor_olhos = (255, 200, 60)
    veias = 8
    semente = 47
    CHIFRE = Mat((150, 120, 104), 6, relevo=1.3, especular=(240, 220, 200))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "barbaro_possuido"

    def deformar(self, tela, ctx, J):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        for k, (x, curva) in enumerate(((-0.15, -0.5), (0.2, -0.35))):     # chifres
            pts = [C.pt(h * x, h * 0.4)]
            a = math.atan2(J["hu"][1], J["hu"][0]) - 0.6
            for i in range(4):
                a += curva * 0.45
                pts.append(pts[-1] + v2(math.cos(a), math.sin(a)) * (h * 0.42))
            tela.pintar(tela.corrente(pts, [h * 0.18, h * 0.14, h * 0.1, h * 0.06, 0.6]),
                        self.CHIFRE if k else self.CHIFRE.escuro(1))
        if self.vivo(ctx):
            fx.fumaca(tela, J["peito"] + v2(0, -H * 0.1), H * 0.06, cor=(110, 30, 26), fase=ctx.a, n=4, sobe=14)


class FeiticeiraRenegada(Corrompido, MagoElemental):
    """A Feiticeira Renegada: manto rasgado, o fogo virou chama roxo-negra e orbes escuros giram em volta."""
    elemento = "Fogo"
    cor_corrupcao = (190, 80, 255)
    cor_olhos = (230, 150, 255)
    semente = 49

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "feiticeira_renegada"
        self.manto = Mat((48, 28, 58), 6, desce=0.45, ruido=0.2, relevo=0.7, arredonda=0.6)
        self.forro = Mat((110, 30, 60), 5, relevo=0.6)
        self.cores = fx.FOGO_ROXO
        self.olhos = (230, 150, 255)

    def deformar(self, tela, ctx, J):
        H = self.H
        if not self.vivo(ctx):
            return
        centro = J["peito"] + v2(0, -H * 0.05)
        for k in range(3):                                                  # orbes escuros girando
            a = ctx.a + k * 2.1
            p = centro + v2(math.cos(a) * H * 0.22, math.sin(a) * H * 0.08)
            tela.chapado(tela.circulo(p, H * 0.025), (30, 10, 40), emite=True)
            tela.px(p[0] - 0.5, p[1] - 0.5, (200, 120, 255), emite=True)
            tela.brilho(p, 4, (170, 80, 240), 0.4)
        rosto = tela.circulo(J["cabeca"], J["P"]["cabeca"] * 0.6) & (tela.alfa > 0) & ~tela.emite
        T.rachaduras(tela, rosto, J["cabeca"], area=(3, 3), n=2, passos=3, cor=(200, 110, 255), emite=True, brilho=0.0)


class AssassinaSemRosto(Corrompido, Assassina):
    """A Assassina Sem Rosto: no capuz, um rosto liso e branco, sem olhos nem boca; adaga pingando veneno."""
    nome = "assassina_sem_rosto"
    carmim = Mat((40, 70, 40), 6, relevo=0.6)
    cor_corrupcao = (90, 220, 120)
    cor_olhos = None
    sombrio = 0.4
    semente = 51
    ROSTO = Mat((236, 232, 228), 6, satur=0.1, relevo=1.0)

    def deformar(self, tela, ctx, J):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.95 * 0.92
        liso = tela.poly(C.pts([(w * 0.02, h * 0.4), (w * 0.62, h * 0.3), (w * 0.72, -h * 0.2), (w * 0.45, -h * 0.55),
                                (w * 0.08, -h * 0.48)]))
        tela.pintar(liso & (tela.alfa > 0), self.ROSTO, plano=True, nivel=0.15)      # o rosto liso, sem nada
        ys, xs = np.nonzero(liso & (tela.alfa > 0))
        if len(ys):
            sombra = xs < np.median(xs)
            T.multiplicar(tela, ys[sombra], xs[sombra], 0.85)
        lamina = J["mao_f"] + dir_ang(J["arma_f"]) * H * 0.18
        if self.vivo(ctx):
            for k in range(2):
                g = lamina + v2(k, 2 + (ctx.i + k) % 3)
                tela.px(g[0], g[1], (120, 255, 120), emite=True)
            tela.brilho(lamina, 4, (100, 240, 110), 0.45)


class PaladinoProfano(Corrompido, Paladino):
    """O Paladino Profano: marfim enegrecido, tabardo roxo, auréola invertida em brasa e lágrimas de sangue."""
    nome = "paladino_profano"
    marfim = metal((70, 64, 66), especular=(220, 180, 120), contraste=1.1)
    tabardo = Mat((54, 22, 56), 6, desce=0.3, ruido=0.12)
    capa_mat = Mat((40, 34, 40), 6, desce=0.55, ruido=0.15, relevo=0.6, arredonda=0.5)
    cor_corrupcao = (255, 50, 40)
    sombrio = 0.25
    semente = 53

    def deformar(self, tela, ctx, J):
        h = J["P"]["cabeca"]
        vivo = self.vivo(ctx)
        if vivo:                                                            # auréola invertida, em brasa
            centro = J["cabeca"] + J["hu"] * (h * 0.95)
            anel = tela.elipse(centro[0], centro[1], h * 0.6, h * 0.18) & ~tela.elipse(centro[0], centro[1], h * 0.42, h * 0.08)
            tela.chapado(anel & (tela.alfa == 0), (255, 90, 40), emite=True)
            for k in range(4):                                              # pontas viradas para baixo
                p = centro + v2((k - 1.5) * h * 0.3, h * 0.12)
                tela.traco(p, p + v2(0, h * 0.25), (255, 120, 50), emite=True)
            tela.brilho(centro, h * 1.2, (255, 70, 40), 0.45)
        for p in olhos_humanoides(J):                                       # lágrimas de sangue
            for k in range(1, 4):
                tela.px(p[0], p[1] + k, (150, 14, 24) if k < 3 else (80, 6, 14))
