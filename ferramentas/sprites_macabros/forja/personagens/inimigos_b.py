"""Inimigos: bruxas, vampiros, golens, lich, rei sombrio e inquisidor."""
import math

import numpy as np

from ..motor import Mat, metal, misturar, v2, lerp, dir_ang, norm, Quadro
from ..humanoide import (perna, braco, tronco, pescoco, cabeca_base, olho, manto, capa, capuz, cinto,
                         quadro_tronco, quadro_cabeca, sangue_no_chao, pe)
from ..anim import Modelo, idle, dano, morte, ESTILOS
from .. import armas, fx
from .herois import (PELE, COURO, COURO_ESC, ACO, FERRO, OURO_VELHO, MALHA, OSSO, MADEIRA, morte_extras,
                     golpe_rastro, PELE_PALIDA)
from .inimigos_a import FERRUGEM

PRETO = Mat((40, 34, 44), 6, ruido=0.12, desce=0.3, relevo=0.7, arredonda=0.6)


def garras(tela, J, lado, cor=(170, 160, 156), comp=4):
    c, m = J["cotovelo_" + lado], J["mao_" + lado]
    d = norm(m - c)
    n = v2(-d[1], d[0])
    for k in (-1, 0, 1):
        tela.traco(m + n * k * 1.2, m + d * comp + n * k * 1.6, cor)


def recalc(m, alt=1.6, larg=2.05):
    m.larg, m.alt = int(m.H * larg), int(m.H * alt)
    m.ancora = (int(m.H * 1.08), m.alt - 4)


# ============================================================
# BRUXA DO PÂNTANO e FREIRA PROFANA
# ============================================================

class Bruxa(Modelo):
    nome = "bruxa"
    H = 70
    estilo = "magia"
    tipo = "pantano"
    base = dict(tronco=0.38, cabeca=-0.3, quadril=(0, 0.05), braco_f=(0.7, 0.6), braco_b=(0.5, 1.3), arma_f=0.15,
                pe_f=(-0.07, 0), pe_b=(0.08, 0))
    prop = dict(ombros=0.22)

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "freira":
            self.nome = "freira_profana"
            self.H = 78
            self.base = dict(braco_f=(0.7, 0.7), braco_b=(0.9, 1.4), arma_f=0.05, pe_f=(-0.05, 0), pe_b=(0.06, 0),
                             tronco=0.05)
            recalc(self)
            self.manto = Mat((34, 30, 38), 6, desce=0.35, ruido=0.1, relevo=0.7, arredonda=0.6)
            self.pele = Mat((196, 186, 182), 6, satur=0.4)
            self.chamas = [(60, 6, 10), (150, 20, 24), (230, 60, 40), (255, 150, 110), (255, 230, 210)]
        else:
            self.manto = Mat((42, 52, 40), 6, desce=0.35, ruido=0.25, relevo=0.7, arredonda=0.6)
            self.pele = Mat((132, 146, 112), 6, satur=0.6)
            self.chamas = fx.FOGO_VERDE

    def desenhar(self, tela, ctx, J):
        H = self.H
        mt = self.manto
        fr = self.tipo == "freira"
        if fr:
            # véu longo atrás
            capa(tela, J, mt.escuro(1), comprimento=0.72, larg=0.13, rasgos=4, semente=2, vento=0.02 * math.sin(ctx.a))
        else:
            # cabelo grisalho comprido atrás
            C = quadro_cabeca(J)
            h = J["P"]["cabeca"]
            pts = [C.pt(-h * 0.3, h * 0.3), C.pt(-h * 0.8, -h * 0.4), C.pt(-h * 0.9 + math.sin(ctx.a), -h * 2.2),
                   C.pt(-h * 0.2, -h * 1.6), C.pt(h * 0.1, -h * 0.2)]
            tela.pintar(tela.poly(pts), Mat((150, 150, 156), 5, ruido=0.6, dither=0.8))
        braco(tela, J, "b", mt.escuro(1), self.pele.escuro(1), grossura=1.15)
        garras(tela, J, "b", comp=3)
        perna(tela, J, "b", mt.escuro(1), None, pe_mat=COURO_ESC)
        perna(tela, J, "f", mt, None, pe_mat=COURO_ESC)
        mm = manto(tela, J, mt, folga=0.06, rasgos=7, semente=4)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        if fr:
            # escapulário com coração sangrando
            esc = tela.poly(Q.pts([(-0.02 * H, T * 0.95), (0.05 * H, T * 0.95), (0.055 * H, -0.35 * H), (-0.015 * H, -0.35 * H)]))
            tela.pintar(esc & mm, Mat((110, 100, 96), 5, desce=0.3), linha_interna=False)
            c = Q.pt(0.018 * H, T * 0.55)
            tela.pintar(tela.poly([c + v2(-2.5, -1), c + v2(0, -2.5), c + v2(2.5, -1), c + v2(0, 3)]), Mat((140, 20, 30), 4))
            for k in range(4):
                p = c + v2(0, 3 + k * 2.5)
                tela.px(p[0] + (k % 2), p[1], (120, 14, 22))
            # rosário
            for k in range(7):
                p = Q.pt(-0.05 * H + k * 0.012 * H, T * 0.9 - k * 2.2)
                tela.px(p[0], p[1], (210, 200, 180))
        else:
            # xale roxo e amuletos
            xa = tela.poly(Q.pts([(-0.08 * H, T * 1.0), (0.08 * H, T * 1.0), (0.06 * H, T * 0.6), (0.0, T * 0.45),
                                  (-0.08 * H, T * 0.6)]))
            tela.pintar(xa, Mat((70, 40, 74), 5, ruido=0.3))
            for k in range(3):
                p = Q.pt(-0.02 * H + k * 0.03 * H, T * 0.35)
                tela.traco(p, p + v2(0, 4 + k), (90, 70, 50))
                tela.px(p[0], p[1] + 5 + k, OSSO[4] if k != 1 else (150, 30, 30))
        cinto(tela, J, COURO_ESC, altura=0.02)
        self.cabeca(tela, J, ctx)
        # cajado
        mf = J["mao_f"]
        if fr:
            topo = armas.cajado(tela, mf, J["arma_f"], H * 0.4, FERRO, atras=H * 0.5)
            d = dir_ang(J["arma_f"])
            n = v2(-d[1], d[0])
            # candelabro em cruz invertida com três velas
            tela.pintar(tela.capsula(topo - d * 4 - n * 6, topo - d * 4 + n * 6, 1.0), FERRO)
            for k, off in enumerate((-6, 0, 6)):
                b = topo - d * (4 if off else -1) + n * off
                tela.pintar(tela.capsula(b, b + d * 4, 1.2), Mat((210, 200, 180), 4))
                fx.chama(tela, b + d * 5, 4 + math.sin(ctx.a * 2 + k), 2.6, self.chamas, fase=ctx.a * 2 + k, brilho=False)
            tela.brilho(topo + d * 3, 12, (230, 70, 50), 0.45)
        else:
            topo = armas.cajado(tela, mf, J["arma_f"], H * 0.42, MADEIRA.escuro(1), atras=H * 0.48, torto=2.0)
            tela.pintar(tela.circulo(topo + v2(0, 1), 2.6), OSSO)
            tela.px(topo[0] + 1, topo[1] + 1, (20, 10, 14))
            fx.chama(tela, topo + v2(0, -1), 10 + math.sin(ctx.a * 2) * 1.5, 7, self.chamas, fase=ctx.a * 2)
        braco(tela, J, "f", mt, self.pele, grossura=1.15)
        garras(tela, J, "f", comp=3)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            c = J["mao_b"] + v2(5, 0)
            fx.chama(tela, c + v2(4, 3), 10, 8, self.chamas, fase=ctx.a, inclina=1.3)
            fx.orbe(tela, c + v2(6, -3), 3.2, self.chamas)
        # vaga-lumes / brasas flutuando
        for k in range(3):
            t = (ctx.i / 4 + k / 3) % 1
            p = J["pelvis"] + v2(math.cos(k * 2.1 + ctx.a) * H * 0.3, -t * H * 0.4 + H * 0.1)
            if tela.alfa[int(min(tela.h - 1, p[1])), int(min(tela.w - 1, p[0]))] == 0:
                tela.px(p[0], p[1], self.chamas[3], emite=True)
        morte_extras(tela, self, ctx, J)

    def cabeca(self, tela, J, ctx):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.85
        pele = self.pele
        if self.tipo == "freira":
            # touca branca e véu
            tela.pintar(tela.poly(C.pts([(-w * 0.7, h * 0.65), (w * 0.55, h * 0.68), (w * 0.72, -h * 0.2), (w * 0.4, -h * 0.75),
                                         (-w * 0.75, -h * 0.7)])), mt := self.manto)
            tela.pintar(tela.poly(C.pts([(-w * 0.1, h * 0.5), (w * 0.6, h * 0.5), (w * 0.66, -h * 0.4), (w * 0.0, -h * 0.55)])),
                        Mat((206, 200, 192), 5, relevo=0.6))
            rosto = tela.poly(C.pts([(w * 0.12, h * 0.35), (w * 0.62, h * 0.3), (w * 0.62, -h * 0.3), (w * 0.15, -h * 0.35)]))
            tela.pintar(rosto, pele, linha_interna=True)
            # venda ensanguentada
            tela.chapado(tela.poly(C.pts([(w * 0.1, h * 0.2), (w * 0.68, h * 0.18), (w * 0.68, h * 0.02), (w * 0.1, h * 0.04)])),
                         (120, 20, 28))
            tela.traco(C.pt(w * 0.15, h * 0.18), C.pt(w * 0.65, h * 0.16), (160, 40, 44))
            # lágrimas de sangue e boca costurada
            for x in (0.3, 0.52):
                tela.traco(C.pt(w * x, h * 0.0), C.pt(w * x, -h * 0.22), (110, 12, 20))
            tela.traco(C.pt(w * 0.3, -h * 0.25), C.pt(w * 0.58, -h * 0.26), (60, 30, 36))
            for k in range(3):
                p = C.pt(w * (0.33 + k * 0.1), -h * 0.25)
                tela.px(p[0], p[1] - 1, (40, 20, 24))
                tela.px(p[0], p[1] + 1, (40, 20, 24))
            return
        cr = [(-w * 0.45, h * 0.05), (-w * 0.4, h * 0.35), (w * 0.0, h * 0.48), (w * 0.4, h * 0.38), (w * 0.55, h * 0.1),
              (w * 0.95, -h * 0.15), (w * 0.6, -h * 0.18), (w * 0.62, -h * 0.35), (w * 0.85, -h * 0.55), (w * 0.4, -h * 0.5),
              (w * 0.0, -h * 0.45), (-w * 0.35, -h * 0.2)]
        tela.pintar(tela.poly(C.pts(cr)), pele)
        tela.px(*C.pt(w * 0.82, -h * 0.05), (70, 90, 50))
        p = C.pt(w * 0.38, h * 0.08)
        tela.px(p[0], p[1], (255, 230, 90), emite=True)
        tela.px(p[0] + 1, p[1], (220, 60, 30), emite=True)
        tela.traco(C.pt(w * 0.2, -h * 0.3), C.pt(w * 0.55, -h * 0.34), (40, 20, 26))
        tela.px(*C.pt(w * 0.35, -h * 0.36), OSSO[5])
        # chapéu torto e rasgado
        ch = Mat((36, 30, 40), 5, ruido=0.3)
        aba = tela.elipse_girada(C.pt(w * 0.05, h * 0.42), w * 1.15, h * 0.16, math.atan2(J["hu"][1], J["hu"][0]) + math.pi / 2 + 0.15)
        tela.pintar(aba, ch)
        s = math.sin(ctx.a)
        cone = [C.pt(-w * 0.55, h * 0.45), C.pt(w * 0.5, h * 0.5), C.pt(w * 0.1, h * 1.3), C.pt(-w * 0.3 + s * 0.5, h * 1.75),
                C.pt(-w * 0.9 + s, h * 1.85), C.pt(-w * 0.45, h * 1.2)]
        tela.pintar(tela.poly(cone), ch)
        tela.traco(C.pt(-w * 0.5, h * 0.58), C.pt(w * 0.45, h * 0.62), (90, 60, 30))


# ============================================================
# VAMPIROS
# ============================================================

class Vampiro(Modelo):
    nome = "vampiro"
    H = 82
    estilo = "garra"
    tipo = "conde"
    base = dict(braco_f=(0.25, 0.45), braco_b=(0.0, 0.3), pe_f=(-0.05, 0), pe_b=(0.07, 0), tronco=0.02)
    prop = dict(ombros=0.24, l_braco=0.03, l_antebraco=0.027)
    pele = Mat((196, 190, 200), 6, satur=0.5)

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "cria":
            self.nome = "cria_vampirica"
            self.H = 60
            self.base = dict(tronco=0.55, cabeca=-0.55, quadril=(0, 0.1), braco_f=(0.5, 0.8), braco_b=(0.2, 0.9),
                             pe_f=(-0.12, 0), pe_b=(0.12, 0))
            self.prop = dict(ombros=0.24, l_braco=0.03, l_antebraco=0.028, cabeca=0.15)
            recalc(self)
            self.pele = Mat((178, 150, 158), 6, satur=0.5)
        elif self.tipo == "noiva":
            self.nome = "noiva_vampira"
            self.H = 76
            self.estilo = "magia"
            self.base = dict(braco_f=(0.5, 0.9), braco_b=(0.2, 0.5), pe_f=(-0.04, 0), pe_b=(0.05, 0), arma_f=0.0)
            self.prop = dict(ombros=0.21, l_braco=0.027, l_antebraco=0.024, quadris=0.17)
            recalc(self)

    def pose(self, ctx):
        p = super().pose(ctx)
        if self.tipo == "noiva" and ctx.anim in ("parado", "dano", "ataque"):
            q = p.get("quadril", (0, 0))
            p["quadril"] = (q[0], q[1] - 0.06 + 0.01 * math.sin(ctx.a))  # flutua
            p["pe_f"] = (p["pe_f"][0], -0.06 + 0.01 * math.sin(ctx.a))
            p["pe_b"] = (p["pe_b"][0], -0.06 + 0.01 * math.sin(ctx.a))
        return p

    def desenhar(self, tela, ctx, J):
        if self.tipo == "cria":
            return self.cria(tela, ctx, J)
        if self.tipo == "noiva":
            return self.noiva(tela, ctx, J)
        H = self.H
        pele = self.pele
        preto = Mat((34, 28, 40), 6, ruido=0.08, relevo=0.7)
        verm = Mat((130, 16, 34), 6, relevo=0.6)
        abre = 0.12 if ctx.golpe else 0.03 * math.sin(ctx.a)
        capa(tela, J, preto, comprimento=0.8, larg=0.22, vento=abre + 0.04, rasgos=6, semente=17, forro=verm)
        braco(tela, J, "b", preto.escuro(1), pele.escuro(1))
        garras(tela, J, "b", comp=3)
        perna(tela, J, "b", preto.escuro(1), Mat((26, 22, 30), 5, especular=(120, 110, 130)), cano=0.4)
        perna(tela, J, "f", preto, Mat((30, 26, 34), 5, especular=(130, 120, 140)), cano=0.4)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        # casaca longa
        cas = tela.poly(Q.pts([(-0.08 * H, T * 0.2), (0.07 * H, T * 0.2), (0.09 * H, -0.24 * H), (0.03 * H, -0.2 * H),
                               (-0.1 * H, -0.26 * H)]))
        tela.pintar(cas, preto)
        tronco(tela, J, preto, cintura=0.12, peito=0.17)
        # colete vermelho, camisa e jabô
        col = tela.poly(Q.pts([(0.0, T * 0.15), (0.06 * H, T * 0.15), (0.065 * H, T * 0.9), (0.01 * H, T * 0.9)]))
        tela.pintar(col & tela.mascara(), verm, linha_interna=False)
        tela.pintar(tela.poly(Q.pts([(0.015 * H, T * 1.0), (0.06 * H, T * 1.0), (0.045 * H, T * 0.7), (0.02 * H, T * 0.72)])),
                    Mat((200, 196, 200), 4, relevo=0.5))
        # medalhão
        m = Q.pt(0.04 * H, T * 0.62)
        tela.pintar(tela.circulo(m, 1.8), OURO_VELHO)
        tela.px(m[0], m[1], (200, 20, 40), emite=True)
        pescoco(tela, J, pele, 0.03)
        self.cabeca_conde(tela, J, ctx)
        # gola alta da capa
        u = J["u"]
        f = v2(-u[1], u[0])
        for s, o in ((-1, J["ombro_f"]), (1, J["ombro_b"])):
            pts = [o, o + u * 9 + f * s * 2.5, J["pescoco"] + u * 2 + f * s * 1]
            tela.pintar(tela.poly(pts), verm if s > 0 else preto)
        braco(tela, J, "f", preto, pele)
        garras(tela, J, "f", comp=4)
        if ctx.anim == "ataque" and ctx.i == 1:
            # três rasgos de garra
            c = J["mao_f"] + v2(6, 0)
            for k in range(3):
                tela.traco(c + v2(-2 + k * 3, -8), c + v2(4 + k * 3, 8), (220, 40, 60), emite=True)
        morte_extras(tela, self, ctx, J)

    def cabeca_conde(self, tela, J, ctx):
        m, C = cabeca_base(tela, J, self.pele, orelha=False)
        h = J["P"]["cabeca"]
        w = h * 0.82
        # orelha pontuda
        tela.pintar(tela.poly(C.pts([(-w * 0.05, h * 0.1), (-w * 0.45, h * 0.45), (-w * 0.2, -h * 0.1)])), self.pele.escuro(1))
        # cabelo preto penteado com bico
        tela.pintar(tela.poly(C.pts([(-w * 0.55, -h * 0.1), (-w * 0.5, h * 0.42), (-w * 0.1, h * 0.58), (w * 0.35, h * 0.5),
                                     (w * 0.55, h * 0.3), (w * 0.3, h * 0.3), (w * 0.2, h * 0.18), (w * 0.05, h * 0.3),
                                     (-w * 0.25, h * 0.2), (-w * 0.4, -h * 0.25)])), Mat((30, 26, 34), 5, relevo=1.2))
        p = C.pt(w * 0.35, h * 0.06)
        tela.px(p[0], p[1], (255, 40, 50), emite=True)
        tela.brilho(p, 3.5, (255, 20, 40), 0.55)
        tela.traco(C.pt(w * 0.18, h * 0.16), C.pt(w * 0.5, h * 0.12), (40, 30, 40))
        tela.traco(C.pt(w * 0.25, -h * 0.28), C.pt(w * 0.55, -h * 0.26), (90, 20, 30))
        tela.px(*C.pt(w * 0.45, -h * 0.34), (240, 240, 240))
        tela.px(*C.pt(w * 0.32, -h * 0.34), (240, 240, 240))

    def cria(self, tela, ctx, J):
        H = self.H
        pele = self.pele
        trapo = Mat((60, 50, 56), 5, ruido=0.5)
        braco(tela, J, "b", pele.escuro(1), pele.escuro(1), grossura=0.95)
        garras(tela, J, "b", comp=4)
        perna(tela, J, "b", trapo.escuro(1), None, pe_mat=pele.escuro(1))
        perna(tela, J, "f", trapo, None, pe_mat=pele)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        tronco(tela, J, pele, cintura=0.12, peito=0.17, corcunda=0.04)
        # costelas, coluna saliente
        for k in range(4):
            tela.traco(Q.pt(-0.01 * H, T * (0.45 + k * 0.12)), Q.pt(0.07 * H, T * (0.42 + k * 0.12)), pele[2], sobre=True)
        for k in range(5):
            tela.px(*Q.pt(-0.09 * H, T * (0.3 + k * 0.14)), pele[5])
        # camisa rasgada pendurada
        tr = tela.poly(Q.pts([(-0.08 * H, T * 0.3), (0.06 * H, T * 0.2), (0.07 * H, -0.08 * H), (0.0, -0.02 * H), (-0.07 * H, -0.1 * H)]))
        tela.pintar(tr, trapo)
        pescoco(tela, J, pele, 0.035)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.85
        cr = [(-w * 0.5, h * 0.05), (-w * 0.4, h * 0.42), (w * 0.05, h * 0.52), (w * 0.42, h * 0.38), (w * 0.55, h * 0.1),
              (w * 0.6, -h * 0.25), (w * 0.4, -h * 0.55), (w * 0.0, -h * 0.5), (-w * 0.35, -h * 0.2)]
        tela.pintar(tela.poly(C.pts(cr)), pele)
        tela.pintar(tela.poly(C.pts([(-w * 0.1, h * 0.15), (-w * 0.7, h * 0.55), (-w * 0.25, -h * 0.05)])), pele.escuro(1))
        # boca escancarada com presas
        boca = tela.poly(C.pts([(w * 0.15, -h * 0.15), (w * 0.6, -h * 0.12), (w * 0.55, -h * 0.5), (w * 0.2, -h * 0.4)]))
        tela.chapado(boca, (40, 8, 14))
        for x in (0.25, 0.48):
            tela.traco(C.pt(w * x, -h * 0.15), C.pt(w * x, -h * 0.3), (235, 230, 220))
        for x in (0.3, 0.42):
            p = C.pt(w * x, h * 0.12)
            tela.px(p[0], p[1], (255, 40, 40), emite=True)
        tela.brilho(C.pt(w * 0.36, h * 0.12), 3.5, (255, 30, 30), 0.5)
        braco(tela, J, "f", pele, pele, grossura=0.95)
        garras(tela, J, "f", comp=4)
        if ctx.anim == "ataque" and ctx.i == 1:
            c = J["mao_f"] + v2(5, 0)
            for k in range(3):
                tela.traco(c + v2(-2 + k * 3, -7), c + v2(3 + k * 3, 7), (220, 40, 60), emite=True)
        morte_extras(tela, self, ctx, J)

    def noiva(self, tela, ctx, J):
        H = self.H
        pele = self.pele
        vestido = Mat((150, 140, 150), 6, desce=0.5, ruido=0.15, relevo=0.6, arredonda=0.6, satur=0.4)
        # cabelo negro longo flutuando
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        s = math.sin(ctx.a)
        cab = [C.pt(-h * 0.3, h * 0.45), C.pt(-h * 1.1, h * 0.0 + s), C.pt(-h * 1.6, -h * 1.4 + s * 1.5), C.pt(-h * 0.8, -h * 2.4),
               C.pt(-h * 0.2, -h * 1.0), C.pt(h * 0.2, h * 0.2)]
        tela.pintar(tela.poly(cab), Mat((26, 22, 30), 5, relevo=0.8))
        braco(tela, J, "b", pele.escuro(1), pele.escuro(1), grossura=0.9)
        garras(tela, J, "b", comp=3)
        mm = manto(tela, J, vestido, folga=0.1, rasgos=9, semente=6, barra=-0.03)
        # sangue escorrendo no vestido
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        for k in range(4):
            a0 = Q.pt(0.0 + k * 0.02 * H, T * 0.9)
            tela.traco(a0, a0 - J["u"] * (T * 0.4 + k * 4), (110, 14, 24), sobre=True)
        tela.pintar(tela.poly(Q.pts([(-0.05 * H, T * 0.98), (0.06 * H, T * 0.98), (0.05 * H, T * 0.75), (-0.04 * H, T * 0.72)])) &
                    mm, vestido.claro(1), linha_interna=False)
        pescoco(tela, J, pele, 0.026)
        m, C = cabeca_base(tela, J, pele, orelha=False)
        w = h * 0.82
        tela.pintar(tela.poly(C.pts([(-w * 0.55, -h * 0.2), (-w * 0.5, h * 0.42), (w * 0.0, h * 0.58), (w * 0.4, h * 0.5),
                                     (w * 0.58, h * 0.25), (w * 0.2, h * 0.32), (-w * 0.2, h * 0.1), (-w * 0.3, -h * 0.4)])),
                    Mat((26, 22, 30), 5))
        p = C.pt(w * 0.35, h * 0.06)
        tela.px(p[0], p[1], (255, 50, 70), emite=True)
        tela.brilho(p, 3, (255, 30, 60), 0.5)
        tela.traco(C.pt(w * 0.28, -h * 0.28), C.pt(w * 0.5, -h * 0.27), (130, 20, 36))
        tela.traco(C.pt(w * 0.4, -h * 0.3), C.pt(w * 0.4, -h * 0.55), (130, 14, 24))
        # véu rasgado
        tela.pintar(tela.poly(C.pts([(-w * 0.5, h * 0.55), (w * 0.3, h * 0.6), (-w * 0.6, -h * 0.9), (-w * 1.2, -h * 1.5)])),
                    Mat((190, 186, 196), 5, relevo=0.4, dither=0.9), linha_interna=False)
        braco(tela, J, "f", pele, pele, grossura=0.9)
        garras(tela, J, "f", comp=3)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            c = J["mao_b"] + v2(6, 0)
            cores = [(50, 4, 10), (130, 14, 30), (210, 40, 60), (255, 120, 140), (255, 220, 230)]
            fx.orbe(tela, c, 3.5, cores)
            for k in range(4):
                a = ctx.a + k * 1.6
                p = c + v2(math.cos(a), math.sin(a)) * 7
                tela.px(p[0], p[1], cores[3], emite=True)
        morte_extras(tela, self, ctx, J)


# ============================================================
# GOLENS (pedra / pedra carregando / carne)
# ============================================================

class Golem(Modelo):
    nome = "golem"
    H = 96
    estilo = "pesado"
    tipo = "pedra"
    carregando = False
    prop = dict(ombros=0.42, cabeca=0.12, pescoco=0.015, tronco=0.31, coxa=0.21, canela=0.2, braco=0.2, antebraco=0.21,
                l_braco=0.075, l_antebraco=0.085, l_coxa=0.085, l_canela=0.075, quadris=0.22, mao=0.11, pe=0.1, giro=0.6)
    base = dict(tronco=0.2, cabeca=0.1, quadril=(0, 0.03), braco_f=(0.15, 0.25), braco_b=(-0.05, 0.2), pe_f=(-0.09, 0),
                pe_b=(0.1, 0))

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "carne":
            self.nome = "golem_carne"
            self.H = 92
            self.prop = dict(self.prop, cabeca=0.15, l_braco=0.06, l_antebraco=0.066, ombros=0.38)
            self.estilo = "corte"
            self.base = dict(self.base, arma_f=0.6)
            recalc(self)
        elif self.carregando:
            self.nome = "golem_carregando"
        recalc(self, larg=2.2)
        self.pedra = Mat((112, 108, 108), 6, ruido=0.55, dither=0.5, relevo=1.2, satur=0.5)
        self.runa = (255, 150, 50) if self.carregando else (110, 230, 255)

    def desenhar(self, tela, ctx, J):
        if self.tipo == "carne":
            return self.carne(tela, ctx, J)
        H = self.H
        pd, pd2 = self.pedra, self.pedra.escuro(1)
        musgo = Mat((70, 96, 52), 5, ruido=0.8, dither=0.9)
        forca = 1.5 if self.carregando else 1.0
        brilho = (0.55 + 0.25 * math.sin(ctx.a * (2 if self.carregando else 1))) * forca
        self.braco_pedra(tela, J, "b", pd2)
        perna(tela, J, "b", pd2, None, grossura=1.0, pe_mat=pd2)
        perna(tela, J, "f", pd, None, grossura=1.0, pe_mat=pd)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        m = tronco(tela, J, pd, cintura=0.2, peito=0.32, ombros=0.4, corcunda=0.04)
        # placas de pedra e rachaduras com runas
        for k in range(3):
            tela.traco(Q.pt(-0.12 * H, T * (0.3 + k * 0.22)), Q.pt(0.12 * H, T * (0.34 + k * 0.2)), pd[1], sobre=True)
        tela.pintar(tela.elipse_girada(Q.pt(-0.08 * H, T * 0.95), H * 0.09, H * 0.03, 0.2) & m, musgo, linha_interna=False)
        c = Q.pt(0.03 * H, T * 0.6)
        tela.brilho(c, 12 * forca, self.runa, 0.5 * brilho)
        rachas = [c + v2(0, -8), c + v2(-3, -3), c, c + v2(4, 4), c + v2(1, 9)]
        tela.tracos(rachas, self.runa, emite=True, sobre=True)
        tela.traco(c, c + v2(-7, 4), self.runa, emite=True, sobre=True)
        if self.carregando:
            for k in range(5):
                a = k * 1.3 + ctx.a
                p0 = c + v2(math.cos(a), math.sin(a)) * 6
                tela.traco(p0, p0 + v2(math.cos(a), math.sin(a)) * 5, self.runa, emite=True, sobre=True)
            armas.faiscas(tela, c, (255, 220, 120), n=6, raio=H * 0.25, semente=ctx.i)
        tela.chapado(tela.circulo(c, 2.5), misturar(self.runa, (255, 255, 255), 0.4), emite=True)
        # cabeça pequena afundada
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        cab = tela.poly(C.pts([(-h * 0.6, -h * 0.3), (-h * 0.5, h * 0.5), (h * 0.5, h * 0.55), (h * 0.75, h * 0.0), (h * 0.6, -h * 0.5)]))
        tela.pintar(cab, pd)
        tela.chapado(tela.poly(C.pts([(h * 0.1, h * 0.12), (h * 0.7, h * 0.08), (h * 0.7, -h * 0.08), (h * 0.1, -h * 0.05)])),
                     self.runa, emite=True)
        tela.brilho(C.pt(h * 0.4, 0), 6, self.runa, 0.6 * brilho)
        # cristais nas costas
        for k, (x, alt) in enumerate(((-0.14, 0.16), (-0.08, 0.22), (-0.02, 0.14))):
            b = Q.pt(x * H, T * 0.95)
            tela.pintar(tela.poly([b - v2(2.5, 0), b + v2(2.5, 0), b + J["u"] * alt * H + v2(-2, 0)]),
                        Mat(misturar(self.runa, (60, 60, 80), 0.4), 5, relevo=1.4))
        if self.carregando:
            self.cristais_em_brasa(tela, ctx, J)
        self.braco_pedra(tela, J, "f", pd)
        if self.carregando and not (ctx.anim == "morte" and ctx.i >= 2):
            self.rochas_flutuando(tela, ctx, J)
        if ctx.anim == "ataque" and ctx.i == 2:
            # poeira e pedras do impacto
            p = J["mao_f"]
            for k in range(6):
                q = p + v2(-8 + k * 4, 6 - (k % 3) * 3)
                tela.pintar(tela.circulo(q, 1.6), pd.claro(1))
        if ctx.anim == "morte" and ctx.i == 3:
            # vira um monte de entulho
            pass

    def cristais_em_brasa(self, tela, ctx, J):
        """Golem carregando: um leque de cristais enormes e acesos rompendo as costas e os ombros."""
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        u = J["u"]
        f = Q.f
        cristal = Mat((255, 140, 50), 5, relevo=1.5, especular=(255, 240, 200))
        for k, (x, y, inc, alt, larg) in enumerate(((-0.17, 0.75, -0.75, 0.3, 4.0), (-0.11, 1.0, -0.35, 0.4, 4.6),
                                                    (-0.03, 1.08, -0.05, 0.3, 3.6), (-0.2, 0.45, -1.1, 0.22, 3.2))):
            b = Q.pt(x * H, T * y)
            d = dir_ang(math.atan2(u[0], -u[1]) + inc)
            n = v2(-d[1], d[0])
            ponta = b + d * alt * H
            m = tela.poly([b - n * larg, b + n * larg, lerp(b, ponta, 0.7) + n * larg * 0.7, ponta, lerp(b, ponta, 0.7) - n * larg * 0.6])
            tela.pintar(m, cristal if k % 2 == 0 else cristal.escuro(1))
            tela.traco(b + d * 2, lerp(b, ponta, 0.85), (255, 236, 180), emite=True, sobre=True)
        tela.brilho(Q.pt(-0.12 * H, T * 1.1), H * 0.3, self.runa, 0.35 + 0.15 * math.sin(ctx.a * 2))

    def rochas_flutuando(self, tela, ctx, J):
        """Pedaços de rocha arrancados do chão girando em volta dele, presos pela energia."""
        H = self.H
        centro = quadro_tronco(J).pt(0.0, J["P"]["tronco"] * 0.9)
        for k in range(4):
            a = ctx.a + k * math.pi / 2
            p = centro + v2(math.cos(a) * H * 0.42, math.sin(a) * H * 0.1 - H * 0.12 + math.sin(a * 2) * 2)
            if math.sin(a) < 0 and tela.alfa[int(min(tela.h - 1, max(0, p[1]))), int(min(tela.w - 1, max(0, p[0])))]:
                continue                                                        # atrás do golem: escondida
            r = 3.2 + k % 2
            tela.pintar(tela.poly([p + v2(-r, -r * 0.6), p + v2(r * 0.4, -r), p + v2(r, r * 0.3), p + v2(-r * 0.2, r)]),
                        self.pedra.claro(1))
            tela.px(p[0], p[1], self.runa, emite=True)
            tela.brilho(p, 5, self.runa, 0.3)

    def braco_pedra(self, tela, J, lado, mat):
        H = self.H
        o, c, m = J["ombro_" + lado], J["cotovelo_" + lado], J["mao_" + lado]
        tela.pintar(tela.circulo(o, H * 0.085), mat)
        tela.pintar(tela.capsula(o, c, H * 0.07, H * 0.065), mat)
        tela.pintar(tela.capsula(c, m, H * 0.075, H * 0.09), mat)
        tela.pintar(tela.circulo(m, H * 0.1), mat)
        d = norm(m - c)
        tela.traco(c + d * 3, m - d * 4, mat[1], sobre=True)
        tela.traco(m + v2(-2, -3), m + v2(3, 2), self.runa if lado == "f" else mat[1], emite=lado == "f", sobre=True)

    def carne(self, tela, ctx, J):
        H = self.H
        carne = Mat((168, 136, 128), 6, relevo=1.1, ruido=0.25, satur=0.6)
        carne2 = Mat((140, 150, 130), 6, relevo=1.1, ruido=0.25, satur=0.5)
        sutura = (60, 30, 34)
        braco(tela, J, "b", carne2.escuro(1), carne2.escuro(1), grossura=1.0)
        perna(tela, J, "b", Mat((60, 50, 46), 5), COURO_ESC.escuro(1), cano=0.5)
        perna(tela, J, "f", Mat((70, 58, 52), 5), COURO_ESC, cano=0.5)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        m = tronco(tela, J, carne, cintura=0.22, peito=0.32, ombros=0.38, barriga=0.04, corcunda=0.05)
        # retalho de pele de outra cor costurado
        ret = tela.poly(Q.pts([(-0.12 * H, T * 0.5), (0.02 * H, T * 0.55), (0.03 * H, T * 0.95), (-0.12 * H, T * 0.9)]))
        tela.pintar(ret & m, carne2, linha_interna=False)
        for pts in ([(-0.12, 0.5), (0.02, 0.55), (0.03, 0.95)], [(0.0, 0.1), (0.1, 0.4)], [(-0.1, 0.2), (-0.02, 0.35)]):
            P = [Q.pt(x * H, T * y) for x, y in pts]
            tela.tracos(P, sutura, sobre=True)
            for i in range(len(P) - 1):
                for t in np.linspace(0.1, 0.9, 4):
                    q = lerp(P[i], P[i + 1], t)
                    tela.px(q[0], q[1] - 1, (200, 190, 170))
        # parafusos nos ombros / pescoço
        for lado in ("f", "b"):
            p = J["ombro_" + lado] + J["u"] * 3
            tela.pintar(tela.capsula(p, p + J["u"] * 3, 1.3), FERRUGEM)
        # avental de açougueiro
        av = tela.poly(Q.pts([(-0.06 * H, T * 0.5), (0.1 * H, T * 0.5), (0.11 * H, -0.2 * H), (-0.07 * H, -0.2 * H)]))
        tela.pintar(av, Mat((120, 110, 96), 5, ruido=0.3, desce=0.3))
        tela.chapado(av & (tela.ruido_base > 0.15) & tela.poly(Q.pts([(-0.06 * H, T * 0.2), (0.11 * H, T * 0.2), (0.11 * H, -0.2 * H), (-0.06 * H, -0.2 * H)])),
                     (100, 14, 22))
        cinto(tela, J, COURO_ESC, fivela=FERRO)
        pescoco(tela, J, carne, 0.06)
        # cabeça: saco de estopa com um buraco de olho
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.9
        saco = tela.poly(C.pts([(-w * 0.55, -h * 0.45), (-w * 0.6, h * 0.35), (-w * 0.2, h * 0.65), (w * 0.3, h * 0.6),
                                (w * 0.6, h * 0.3), (w * 0.6, -h * 0.45)]))
        tela.pintar(saco, Mat((136, 112, 80), 5, ruido=0.8, dither=0.8))
        tela.traco(C.pt(-w * 0.6, -h * 0.3), C.pt(w * 0.6, -h * 0.3), Mat((80, 60, 40), 4)[1])
        p = C.pt(w * 0.35, h * 0.1)
        tela.chapado(tela.circulo(p, 1.6), (20, 10, 14))
        tela.px(p[0], p[1], (255, 220, 120), emite=True)
        tela.traco(C.pt(w * 0.1, -h * 0.12), C.pt(w * 0.55, -h * 0.15), (60, 20, 24))
        # arma: cutelo de açougue preso no braço + gancho
        mf = J["mao_f"]
        d = dir_ang(J["arma_f"])
        n = v2(-d[1], d[0])
        tela.pintar(tela.capsula(mf - d * 3, mf + d * 3, 1.4), MADEIRA)
        b = mf + d * 3
        lam = tela.poly([b - n * 1, b + d * H * 0.32 - n * 1, b + d * H * 0.34 + n * 8, b + d * 2 + n * 9])
        tela.pintar(lam, FERRUGEM)
        tela.chapado(lam & (tela.ruido_base > 0.28), (110, 16, 24))
        braco(tela, J, "f", carne, carne, grossura=1.0)
        tela.pintar(tela.circulo(mf, H * 0.06), carne)
        # gancho no braço de trás
        mb = J["mao_b"]
        tela.pintar(tela.corrente([mb, mb + v2(0, 6), mb + v2(3, 9), mb + v2(5, 6)], [1.2, 1.1, 1.0, 0.6]), FERRO)
        golpe_rastro(tela, ctx, J, H * 0.62, -1.2, 2.0, cor=(220, 190, 180))
        morte_extras(tela, self, ctx, J)


# ============================================================
# LICH — Lorde Sombrio flutuante
# ============================================================

class Lich(Modelo):
    nome = "lich"
    H = 86
    estilo = "magia"
    tipo = "lich"
    base = dict(quadril=(0, -0.1), pe_f=(-0.04, -0.1), pe_b=(0.05, -0.1), braco_f=(0.6, 0.5), braco_b=(0.4, 1.0),
                arma_f=0.05, tronco=0.05)
    prop = dict(ombros=0.27)

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "rei":
            self.nome = "rei_sombrio"
            self.H = 94
            recalc(self)
            self.manto = Mat((54, 36, 86), 6, desce=0.5, ruido=0.1, relevo=0.7, arredonda=0.6)
            self.fogo = fx.FOGO_ROXO
            self.olhos = (255, 210, 80)
        else:
            self.manto = Mat((40, 32, 60), 6, desce=0.5, ruido=0.1, relevo=0.7, arredonda=0.6)
            self.fogo = fx.FOGO_AZUL
            self.olhos = (150, 210, 255)

    def pose(self, ctx):
        p = super().pose(ctx)
        f = 0.012 * math.sin(ctx.a)
        if ctx.anim != "morte":
            q = p.get("quadril", (0, 0))
            p["quadril"] = (q[0], q[1] + f)
            p["pe_f"] = (p["pe_f"][0], -0.1 + f)
            p["pe_b"] = (p["pe_b"][0], -0.1 + f)
        return p

    def desenhar(self, tela, ctx, J):
        H = self.H
        mt = self.manto
        osso = Mat((200, 196, 180), 6, luz_hue=0.6, satur=0.6)
        rei = self.tipo == "rei"
        # aura
        if ctx.anim != "morte":
            tela.brilho(J["peito"], H * 0.55, mt[4], 0.25 + 0.05 * math.sin(ctx.a))
        capa(tela, J, mt.escuro(2), comprimento=0.75, larg=0.22, vento=0.04 + 0.03 * math.sin(ctx.a), rasgos=9, semente=23)
        if rei:
            braco(tela, J, "b", mt.escuro(1), osso.escuro(1), grossura=1.3)
        else:
            braco(tela, J, "b", mt.escuro(1), None, grossura=1.3)
            self.mao_osso(tela, J, "b", osso.escuro(1))
        mm = manto(tela, J, mt, folga=0.11, rasgos=10, semente=12, barra=0.02)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        if not rei:
            # peito aberto mostrando costelas
            pe = tela.poly(Q.pts([(-0.02 * H, T * 0.35), (0.07 * H, T * 0.35), (0.075 * H, T * 0.95), (-0.01 * H, T * 0.95)]))
            tela.chapado(pe & mm, (16, 10, 20))
            for k in range(4):
                y = 0.45 + k * 0.13
                tela.traco(Q.pt(0.0, T * y), Q.pt(0.07 * H, T * (y - 0.04)), osso[3], sobre=True)
            tela.brilho(Q.pt(0.03 * H, T * 0.6), 7, self.fogo[2], 0.5)
        else:
            # faixa com runas douradas
            for k in range(4):
                p = Q.pt(0.03 * H, T * (0.8 - k * 0.22))
                fx.runa(tela, p, OURO_VELHO[4], 1, forma=k, emite=False)
        # ombreiras de crânio
        for lado, m in (("b", osso.escuro(1)), ("f", osso)):
            p = J["ombro_" + lado] + J["u"] * 1.5
            tela.pintar(tela.elipse(p[0], p[1], 5, 4.2), m)
            tela.chapado(tela.circulo(p + v2(1, 0), 1.0), (16, 8, 14))
            tela.chapado(tela.circulo(p + v2(3.2, 0), 1.0), (16, 8, 14))
        # cabeça
        if rei:
            _, C, face = capuz(tela, J, mt, ponta=0.4, sombra=(8, 4, 12))
            h = J["P"]["cabeca"]
            w = h * 0.95
            for x in (w * 0.28, w * 0.5):
                p = C.pt(x, h * 0.05)
                tela.px(p[0], p[1], self.olhos, emite=True)
                tela.px(p[0] + 1, p[1], self.olhos, emite=True)
            tela.brilho(C.pt(w * 0.4, h * 0.05), 5, self.olhos, 0.6)
            self.coroa(tela, C, h, w * 0.9, ctx)
        else:
            C = quadro_cabeca(J)
            h = J["P"]["cabeca"]
            w = h * 0.85
            cr = [(-w * 0.5, h * 0.05), (-w * 0.42, h * 0.38), (-w * 0.05, h * 0.52), (w * 0.35, h * 0.45), (w * 0.55, h * 0.15),
                  (w * 0.58, -h * 0.1), (w * 0.45, -h * 0.45), (w * 0.0, -h * 0.4), (-w * 0.35, -h * 0.1)]
            tela.pintar(tela.poly(C.pts(cr)), osso)
            tela.traco(C.pt(w * 0.1, -h * 0.25), C.pt(w * 0.52, -h * 0.27), (16, 8, 14))
            for k in range(3):
                p = C.pt(w * (0.15 + k * 0.13), -h * 0.27)
                tela.px(p[0], p[1] - 1, osso[5])
            for x in (w * 0.18, w * 0.42):
                p = C.pt(x, h * 0.08)
                tela.chapado(tela.circulo(p, 1.5), (14, 8, 12))
                fx.chama(tela, p + v2(0, 0.5), 5 + math.sin(ctx.a * 2 + x), 2.4, self.fogo, fase=ctx.a * 2 + x, brilho=False)
            tela.brilho(C.pt(w * 0.3, h * 0.08), 7, self.fogo[2], 0.5)
            self.coroa(tela, C, h, w, ctx)
        # cajado / orbe
        mf = J["mao_f"]
        if rei:
            braco(tela, J, "f", mt, osso, grossura=1.3)
            c = mf + v2(4, -3)
            fx.orbe(tela, c, 4.0 + 0.5 * math.sin(ctx.a * 2), self.fogo, 1.2)
            for k in range(3):
                a = ctx.a + k * 2.1
                p = c + v2(math.cos(a) * 8, math.sin(a) * 3)
                tela.px(p[0], p[1], self.fogo[3], emite=True)
        else:
            topo = armas.cajado(tela, mf, J["arma_f"], H * 0.42, Mat((50, 40, 60), 5), atras=H * 0.45)
            tela.pintar(tela.circulo(topo, 3.6), osso)
            tela.px(topo[0] - 1, topo[1], (14, 8, 12))
            tela.px(topo[0] + 1.5, topo[1], (14, 8, 12))
            fx.chama(tela, topo + v2(0, -3), 13 + 2 * math.sin(ctx.a * 2), 8, self.fogo, fase=ctx.a * 2)
            braco(tela, J, "f", mt, None, grossura=1.3)
            self.mao_osso(tela, J, "f", osso)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            c = J["mao_b"] + v2(6, 0)
            fx.orbe(tela, c, 4.5, self.fogo, 1.2)
            fx.chama(tela, c + v2(-3, 2), 9, 8, self.fogo, fase=ctx.a, inclina=-1.2)
            if ctx.i == 2:
                fx.relampago(tela, c, c + v2(28, -4), self.fogo, semente=4, desvio=2, galhos=1)

    def mao_osso(self, tela, J, lado, osso):
        c, m = J["cotovelo_" + lado], J["mao_" + lado]
        d = norm(m - c)
        n = v2(-d[1], d[0])
        tela.pintar(tela.circulo(m, 1.8), osso)
        for k in (-1, 0, 1):
            tela.traco(m, m + d * 4 + n * k * 1.5, osso[4])

    def coroa(self, tela, C, h, w, ctx):
        y = h * 0.42 + math.sin(ctx.a) * 0.6
        pts = [(-w * 0.55, y), (w * 0.55, y), (w * 0.62, y + h * 0.45), (w * 0.35, y + h * 0.2), (w * 0.18, y + h * 0.6),
               (0.0, y + h * 0.22), (-w * 0.2, y + h * 0.62), (-w * 0.35, y + h * 0.2), (-w * 0.62, y + h * 0.45)]
        tela.pintar(tela.poly(C.pts(pts)), OURO_VELHO)
        p = C.pt(0.0, y + h * 0.1)
        tela.px(p[0], p[1], self.fogo[3], emite=True)


# ============================================================
# INQUISIDOR — armadura carmim, mitra de ferro e mangual
# ============================================================

class Inquisidor(Modelo):
    nome = "inquisidor"
    H = 86
    estilo = "corte"
    base = dict(braco_f=(0.4, 0.6), braco_b=(0.5, 1.1), arma_f=0.8, pe_f=(-0.07, 0), pe_b=(0.09, 0))
    prop = dict(ombros=0.29)
    armadura = metal((120, 36, 34), especular=(255, 170, 150), contraste=1.1)

    def desenhar(self, tela, ctx, J):
        H = self.H
        ar, ar2 = self.armadura, self.armadura.escuro(1)
        preto = Mat((36, 30, 36), 6, desce=0.3, relevo=0.6, arredonda=0.5)
        capa(tela, J, preto, comprimento=0.66, larg=0.18, vento=0.03 * math.sin(ctx.a) + (0.05 if ctx.golpe else 0),
             rasgos=6, semente=31, forro=Mat((96, 20, 24), 5))
        braco(tela, J, "b", MALHA.escuro(1), COURO_ESC, punho=ar2)
        # livro acorrentado na mão de trás
        mb = J["mao_b"]
        tela.pintar(tela.poly([mb + v2(-1, -4), mb + v2(6, -5), mb + v2(7, 4), mb + v2(0, 5)]), Mat((70, 30, 26), 5))
        tela.traco(mb + v2(0, -3.5), mb + v2(0.5, 4.5), (220, 210, 190))
        tela.pintar(tela.circulo(mb + v2(3.5, 0), 1.3), OURO_VELHO)
        perna(tela, J, "b", MALHA.escuro(1), ar2, cano=0.62)
        perna(tela, J, "f", MALHA, ar, cano=0.62)
        for lado, m in (("b", ar2), ("f", ar)):
            tela.pintar(tela.capsula(J["quadril_" + lado], lerp(J["quadril_" + lado], J["joelho_" + lado], 0.78), H * 0.05, H * 0.042), m)
            tela.pintar(tela.circulo(J["joelho_" + lado], H * 0.03), OURO_VELHO)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        # batina longa preta por baixo
        bat = tela.poly(Q.pts([(-0.09 * H, 0.05 * H), (0.09 * H, 0.05 * H), (0.1 * H, -0.3 * H), (0.03 * H, -0.27 * H),
                               (-0.02 * H, -0.32 * H), (-0.1 * H, -0.28 * H)]))
        tela.pintar(bat, preto)
        m = tronco(tela, J, ar, cintura=0.14, peito=0.21)
        # cruz dourada e rebites
        tela.traco(Q.pt(0.012 * H, T * 0.25), Q.pt(0.012 * H, T * 0.85), OURO_VELHO[5], sobre=True)
        tela.traco(Q.pt(-0.025 * H, T * 0.68), Q.pt(0.05 * H, T * 0.68), OURO_VELHO[5], sobre=True)
        for y in (0.3, 0.5):
            tela.traco(Q.pt(-0.08 * H, T * y), Q.pt(0.09 * H, T * (y + 0.02)), ar[1], sobre=True)
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO, larg=0.026)
        # pergaminhos pendurados (selos de pureza)
        for k in range(2):
            p = Q.pt(-0.05 * H + k * 0.06 * H, -0.01 * H)
            tela.pintar(tela.poly([p, p + v2(2.5, 0), p + v2(3, 8), p + v2(0.5, 9)]), Mat((200, 186, 150), 4))
            tela.pintar(tela.circulo(p + v2(1, 0), 1.3), Mat((150, 20, 24), 4))
        pescoco(tela, J, MALHA, 0.05)
        # elmo-mitra
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.92
        elmo = [(-w * 0.55, -h * 0.55), (-w * 0.6, h * 0.3), (-w * 0.35, h * 0.62), (-w * 0.15, h * 1.5), (w * 0.15, h * 1.75),
                (w * 0.35, h * 1.2), (w * 0.6, h * 0.35), (w * 0.62, -h * 0.4), (w * 0.4, -h * 0.62)]
        tela.pintar(tela.poly(C.pts(elmo)), ar)
        tela.traco(C.pt(-w * 0.5, h * 0.6), C.pt(w * 0.58, h * 0.55), OURO_VELHO[4], sobre=True)
        tela.traco(C.pt(w * 0.05, h * 1.4), C.pt(w * 0.05, h * 0.8), OURO_VELHO[5], sobre=True)
        tela.traco(C.pt(-w * 0.12, h * 1.15), C.pt(w * 0.22, h * 1.15), OURO_VELHO[5], sobre=True)
        # fenda em cruz com brilho
        tela.traco(C.pt(w * 0.1, h * 0.12), C.pt(w * 0.62, h * 0.12), (10, 4, 6))
        tela.traco(C.pt(w * 0.42, h * 0.35), C.pt(w * 0.42, -h * 0.35), (10, 4, 6))
        p = C.pt(w * 0.5, h * 0.12)
        tela.px(p[0], p[1], (255, 200, 120), emite=True)
        tela.brilho(p, 3, (255, 160, 80), 0.5)
        # mangual
        mf = J["mao_f"]
        osc = [0.4, 0.2, -0.2, 0.1][ctx.i % 4] if ctx.anim == "parado" else (1.6 if ctx.golpe else 0.5)
        ang = J["arma_f"] + 0.0
        fim = armas.mangual(tela, mf, ang, MADEIRA, FERRO, FERRO, comp_cabo=9, comp_corr=H * 0.18, oscila=osc + math.pi * 0.8,
                            raio=3.6)
        braco(tela, J, "f", MALHA, COURO_ESC, punho=ar)
        o, u = J["ombro_f"], J["u"]
        ang2 = math.atan2(u[1], u[0]) + 1.4
        tela.pintar(tela.elipse_girada(o + u * 1.5, H * 0.07, H * 0.052, ang2), ar)
        tela.pintar(tela.elipse_girada(o + u * 3.5, H * 0.045, H * 0.02, ang2), OURO_VELHO, linha_interna=False)
        golpe_rastro(tela, ctx, J, H * 0.62, -1.0, 2.2, cor=(240, 190, 170))
        morte_extras(tela, self, ctx, J)
