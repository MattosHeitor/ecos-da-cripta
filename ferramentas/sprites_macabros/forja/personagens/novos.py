"""Novos personagens: palhaços macabros, bobos da corte, flagelante e carniçal."""
import math

import numpy as np

from ..motor import Mat, metal, misturar, v2, lerp, dir_ang, norm, Quadro
from ..humanoide import (perna, braco, tronco, pescoco, cabeca_base, olho, manto, capa, capuz, cinto,
                         quadro_tronco, quadro_cabeca, sangue_no_chao, pe)
from ..anim import Modelo
from .. import armas, fx
from .herois import (PELE, COURO, COURO_ESC, ACO, FERRO, OURO_VELHO, MALHA, OSSO, MADEIRA, morte_extras,
                     golpe_rastro, PELE_PALIDA)
from .inimigos_a import FERRUGEM
from .inimigos_b import garras, recalc

SANGUE = (112, 12, 22)


def losangos(tela, mask, mat, tam=4.0, fase=0.0):
    """Padrão de losangos (arlequim) dentro de uma máscara."""
    yy, xx = np.mgrid[0:tela.h, 0:tela.w]
    a = ((xx + yy + fase) // tam).astype(int)
    b = ((xx - yy + 1000 + fase) // tam).astype(int)
    m = mask & ((a + b) % 2 == 0)
    tela.pintar(m, mat, linha_interna=False, plano=False)


def listras(tela, mask, mat, larg=3, ang=0.0):
    yy, xx = np.mgrid[0:tela.h, 0:tela.w]
    t = xx * math.cos(ang) + yy * math.sin(ang)
    m = mask & ((t // larg).astype(int) % 2 == 0)
    tela.pintar(m, mat, linha_interna=False)


def respingos(tela, mask, cor=SANGUE, limiar=0.32):
    tela.chapado(mask & (tela.ruido_base > limiar) & (tela.alfa > 0), cor)


def babado(tela, J, mat, larg=0.11, alt=0.035, pontas=7):
    """Gola de babado (rufo) em volta do pescoço."""
    H = J["H"]
    u = J["u"]
    f = v2(-u[1], u[0])
    c = J["pescoco"] - u * 1
    pts = []
    for i in range(pontas * 2 + 1):
        t = i / (pontas * 2)
        x = (t - 0.5) * 2 * larg * H * 0.5
        r = alt * H * (1.0 if i % 2 == 0 else 0.45)
        pts.append(c + f * x + u * r * 0.6)
    for i in range(pontas * 2, -1, -1):
        t = i / (pontas * 2)
        x = (t - 0.5) * 2 * larg * H * 0.5
        r = alt * H * (1.0 if i % 2 == 0 else 0.45)
        pts.append(c + f * x - u * r)
    tela.pintar(tela.poly(pts), mat)


# ============================================================
# PALHAÇOS MACABROS
# ============================================================

class Palhaco(Modelo):
    nome = "palhaco"
    H = 84
    estilo = "estocada"
    tipo = "esguio"
    prop = dict(ombros=0.23, l_braco=0.03, l_antebraco=0.026, l_coxa=0.045, l_canela=0.035, braco=0.18, antebraco=0.17,
                pe=0.12, cabeca=0.135)
    base = dict(tronco=0.15, cabeca=0.25, quadril=(0, 0.02), braco_f=(0.4, 1.0), braco_b=(-0.3, 0.6), arma_f=1.45,
                pe_f=(-0.08, 0), pe_b=(0.1, 0))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.roupa_a = Mat((150, 140, 128), 6, ruido=0.25, satur=0.5, desce=0.3)
        self.roupa_b = Mat((110, 24, 34), 6, ruido=0.2, desce=0.3)
        self.cara = Mat((222, 214, 206), 6, satur=0.3, relevo=0.9)
        if self.tipo == "gordo":
            self.nome = "palhaco_brutamontes"
            self.H = 92
            self.estilo = "pesado"
            self.prop = dict(ombros=0.34, l_braco=0.05, l_antebraco=0.046, l_coxa=0.07, l_canela=0.055, cabeca=0.14,
                             quadris=0.22, pe=0.12, mao=0.05)
            self.base = dict(tronco=0.05, cabeca=-0.1, braco_f=(0.3, 0.5), braco_b=(0.1, 0.4), arma_f=0.35,
                             pe_f=(-0.1, 0), pe_b=(0.12, 0), quadril=(0, 0.03))
            recalc(self)
            self.roupa_b = Mat((60, 74, 110), 6, ruido=0.25, desce=0.3)
        elif self.tipo == "boneco":
            self.nome = "palhacinho"
            self.H = 46
            self.prop = dict(ombros=0.26, cabeca=0.24, pescoco=0.015, tronco=0.24, coxa=0.2, canela=0.18, braco=0.18,
                             antebraco=0.17, l_braco=0.04, l_antebraco=0.036, l_coxa=0.06, l_canela=0.05, pe=0.14, mao=0.06)
            self.base = dict(tronco=0.05, cabeca=0.35, braco_f=(0.5, 0.8), braco_b=(-0.4, 0.3), arma_f=1.3,
                             pe_f=(-0.08, 0), pe_b=(0.1, 0))
            recalc(self)
            self.roupa_a = Mat((120, 40, 90), 6, ruido=0.2)
            self.roupa_b = Mat((50, 40, 60), 6, ruido=0.2)
            self.cara = Mat((226, 220, 214), 6, satur=0.2, relevo=1.3)

    def desenhar(self, tela, ctx, J):
        H = self.H
        a, b = self.roupa_a, self.roupa_b
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        gordo = self.tipo == "gordo"
        boneco = self.tipo == "boneco"
        if boneco:
            # balão murcho preso no pulso de trás
            mb = J["mao_b"]
            s = math.sin(ctx.a)
            topo = mb + v2(-6 + s, -H * 0.55)
            tela.tracos([mb, lerp(mb, topo, 0.5) + v2(2 * s, 0), topo], (160, 150, 150))
            bal = tela.elipse_girada(topo + v2(0, -5), 4.5, 6, 0.2 + s * 0.1)
            tela.pintar(bal, Mat((140, 20, 30), 5, relevo=1.3, especular=(255, 200, 200)))
        braco(tela, J, "b", b.escuro(1), Mat((210, 206, 200), 4).escuro(1), grossura=1.4 if not gordo else 1.1)
        perna(tela, J, "b", b.escuro(1), None, grossura=1.3, pe_mat=Mat((120, 20, 30), 5))
        perna(tela, J, "f", a if not gordo else b, None, grossura=1.3, pe_mat=Mat((140, 24, 34), 5))
        # sapatos enormes
        for lado in ("b", "f"):
            d = J["dedo_" + lado]
            sap = tela.elipse(d[0] + 1, d[1] - 1.5, H * 0.07, H * 0.03)
            tela.pintar(sap, Mat((120, 20, 30), 5) if lado == "f" else Mat((90, 16, 24), 5))
        if gordo:
            m = tronco(tela, J, a, cintura=0.24, peito=0.28, ombros=0.32, barriga=0.09)
            listras(tela, m, b, larg=3, ang=0.15)
            # suspensórios e remendo
            for x in (-0.03, 0.06):
                tela.traco(Q.pt(x * H, T * 1.0), Q.pt((x + 0.02) * H, T * 0.1), COURO_ESC[2], sobre=True)
            respingos(tela, m)
        else:
            calca = tela.poly(Q.pts([(-0.1 * H, 0.05 * H), (0.1 * H, 0.05 * H), (0.12 * H, -0.12 * H), (-0.12 * H, -0.12 * H)]))
            tela.pintar(calca, a)
            m = tronco(tela, J, a, cintura=0.14 if not boneco else 0.2, peito=0.2 if not boneco else 0.22, barriga=0.03)
            # metade vermelha (roupa partida)
            meio = tela.poly(Q.pts([(0.01 * H, -0.2 * H), (0.3 * H, -0.2 * H), (0.3 * H, T * 1.2), (0.01 * H, T * 1.2)]))
            tela.pintar(m & meio, b, linha_interna=False)
            respingos(tela, m)
        # pompons
        for k in range(3):
            p = Q.pt(0.03 * H, T * (0.25 + k * 0.22))
            tela.pintar(tela.circulo(p, max(1.2, H * 0.022)), Mat((40, 36, 44), 4) if k != 1 else Mat((130, 20, 30), 4))
        babado(tela, J, Mat((200, 194, 186), 5, ruido=0.3, relevo=0.6), larg=0.16 if not boneco else 0.2,
               alt=0.04 if not boneco else 0.05)
        self.cabeca(tela, J, ctx)
        mf = J["mao_f"]
        if gordo:
            # marreta de madeira gigante
            armas.martelo(tela, mf, J["arma_f"], H * 0.48, MADEIRA, Mat((120, 84, 56), 6, ruido=0.4), tam=1.3)
            d = dir_ang(J["arma_f"])
            c = mf + d * (H * 0.48 - 2.6)
            respingos(tela, tela.circulo(c, 8), limiar=0.1)
        elif boneco:
            armas.adaga(tela, mf, J["arma_f"], 8, ACO, Mat((140, 20, 30), 4))
        else:
            # faca de açougueiro longa
            d = dir_ang(J["arma_f"])
            n = v2(-d[1], d[0])
            tela.pintar(tela.capsula(mf - d * 3, mf + d * 1.5, 1.1), COURO_ESC)
            b0 = mf + d * 1.5
            lam = tela.poly([b0 + n * 1.2, b0 + d * 18 + n * 1.5, b0 + d * 22 - n * 0.5, b0 - n * 2.5])
            tela.pintar(lam, ACO)
            respingos(tela, lam, limiar=0.0)
        luva = Mat((210, 206, 200), 5)
        braco(tela, J, "f", a if not gordo else b, luva, grossura=1.4 if not gordo else 1.1)
        golpe_rastro(tela, ctx, J, H * (0.62 if gordo else 0.5), -1.2 if gordo else 0.9, 2.1 if gordo else 2.2,
                     cor=(230, 210, 210))
        morte_extras(tela, self, ctx, J)

    def cabeca(self, tela, J, ctx):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * (0.88 if self.tipo != "gordo" else 1.0)
        cara = self.cara
        boneco = self.tipo == "boneco"
        # tufos de cabelo laranja-sujo dos lados
        if not boneco:
            cab = Mat((170, 76, 36), 5, ruido=0.7, dither=0.8)
            for k in range(4):
                c = C.pt(-w * 0.45 - k * 0.6, h * (0.15 - k * 0.12))
                tela.pintar(tela.circulo(c, h * 0.22), cab, linha_interna=k == 0)
        cr = [(-w * 0.48, h * 0.05), (-w * 0.42, h * 0.4), (-w * 0.05, h * 0.55), (w * 0.35, h * 0.48), (w * 0.55, h * 0.2),
              (w * 0.6, -h * 0.15), (w * 0.45, -h * 0.45), (w * 0.05, -h * 0.52), (-w * 0.35, -h * 0.25)]
        tela.pintar(tela.poly(C.pts(cr)), cara)
        # olhos em losango preto com pupila brilhante
        for x in (w * 0.15, w * 0.42):
            c = C.pt(x, h * 0.1)
            los = tela.poly([c + J["hu"] * 3.2, c + v2(1.6, 0), c - J["hu"] * 3.2, c - v2(1.6, 0)])
            tela.chapado(los, (16, 10, 16))
            tela.px(c[0], c[1], (255, 240, 200) if not boneco else (140, 220, 255), emite=True)
        # nariz vermelho
        tela.pintar(tela.circulo(C.pt(w * 0.6, -h * 0.02), max(1.4, h * 0.14)), Mat((170, 20, 30), 5, relevo=1.4,
                                                                                         especular=(255, 200, 200)))
        # sorriso costurado de orelha a orelha
        pts = [C.pt(-w * 0.15, -h * 0.05), C.pt(w * 0.1, -h * 0.3), C.pt(w * 0.4, -h * 0.32), C.pt(w * 0.58, -h * 0.2)]
        boca = tela.corrente(pts, [1.0, 1.4, 1.4, 1.0])
        tela.chapado(boca, (120, 14, 26))
        tela.tracos(pts, (40, 6, 12))
        for k in range(1, 3):
            q = lerp(pts[k], pts[k + 1], 0.5)
            tela.px(q[0], q[1] - 1, (240, 236, 226))
        if self.tipo == "gordo":
            for k in range(4):
                q = lerp(pts[1], pts[3], k / 3)
                tela.px(q[0], q[1] + 1, (235, 230, 215))
        # rachaduras (boneco de porcelana)
        if boneco:
            tela.tracos([C.pt(w * 0.2, h * 0.5), C.pt(w * 0.05, h * 0.25), C.pt(w * 0.15, h * 0.12)], (90, 80, 84), sobre=True)
            tela.tracos([C.pt(-w * 0.3, -h * 0.1), C.pt(-w * 0.1, -h * 0.3)], (90, 80, 84), sobre=True)
            # chapeuzinho cônico listrado
            ch = tela.poly(C.pts([(-w * 0.3, h * 0.42), (w * 0.3, h * 0.5), (w * 0.05, h * 1.25)]))
            tela.pintar(ch, self.roupa_a)
            listras(tela, ch, self.roupa_b, 2, 0.7)
            tela.pintar(tela.circulo(C.pt(w * 0.05, h * 1.3), 1.6), Mat((220, 214, 200), 4))
        elif self.tipo == "gordo":
            # chapeuzinho coco minúsculo
            tela.pintar(tela.poly(C.pts([(-w * 0.15, h * 0.48), (w * 0.35, h * 0.5), (w * 0.3, h * 0.82), (-w * 0.08, h * 0.8)])),
                        Mat((40, 36, 40), 5))
            tela.traco(C.pt(-w * 0.28, h * 0.48), C.pt(w * 0.48, h * 0.5), (30, 26, 30))
        else:
            # cartola amassada e torta
            ct = tela.poly(C.pts([(-w * 0.35, h * 0.45), (w * 0.35, h * 0.55), (w * 0.5, h * 1.25), (-w * 0.05, h * 1.3)]))
            tela.pintar(ct, Mat((44, 38, 48), 5, ruido=0.2))
            tela.traco(C.pt(-w * 0.55, h * 0.42), C.pt(w * 0.55, h * 0.55), (30, 24, 32))
            tela.traco(C.pt(-w * 0.3, h * 0.62), C.pt(w * 0.38, h * 0.7), (120, 20, 30), sobre=True)


# ============================================================
# BOBOS DA CORTE
# ============================================================

class Bobo(Modelo):
    nome = "bobo_da_corte"
    H = 72
    estilo = "corte"
    tipo = "bobo"
    prop = dict(ombros=0.23, l_braco=0.03, l_antebraco=0.027, l_coxa=0.046, l_canela=0.036)
    base = dict(braco_f=(0.5, 0.9), braco_b=(0.6, 1.5), arma_f=1.3, arma_b=2.6, pe_f=(-0.09, 0), pe_b=(0.1, 0),
                tronco=0.1, quadril=(0, 0.03), cabeca=0.1)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.cor_a = Mat((110, 22, 30), 6, ruido=0.15)
        self.cor_b = Mat((38, 32, 44), 6, ruido=0.15)
        if self.tipo == "marionete":
            self.nome = "bobo_marionete"
            self.H = 76
            self.estilo = "estocada"
            self.base = dict(braco_f=(0.6, 0.6), braco_b=(-0.2, 0.9), arma_f=1.4, pe_f=(-0.05, -0.02), pe_b=(0.07, 0),
                             tronco=-0.05, cabeca=0.35)
            recalc(self, alt=1.75)
            self.cor_a = Mat((70, 60, 96), 6, ruido=0.15)
            self.cor_b = Mat((150, 140, 110), 6, ruido=0.2)
        elif self.tipo == "corcunda":
            self.nome = "bobo_corcunda"
            self.H = 56
            self.prop = dict(ombros=0.28, cabeca=0.17, l_braco=0.04, l_antebraco=0.036, l_coxa=0.058, l_canela=0.045,
                             braco=0.2, antebraco=0.19)
            self.base = dict(braco_f=(0.4, 0.7), braco_b=(0.2, 0.8), arma_f=0.4, pe_f=(-0.1, 0), pe_b=(0.12, 0),
                             tronco=0.55, cabeca=-0.5, quadril=(0, 0.08))
            recalc(self)
            self.cor_a = Mat((60, 84, 50), 6, ruido=0.2)
            self.cor_b = Mat((120, 96, 40), 6, ruido=0.2)

    def pose(self, ctx):
        p = super().pose(ctx)
        if self.tipo == "marionete" and ctx.anim == "parado":
            # balança pendurado nos fios, pés quase no ar
            s = math.sin(ctx.a)
            p["braco_b"] = (-0.2 + 0.3 * s, 0.9)
            p["pe_f"] = (-0.05, -0.02 - 0.02 * max(0, s))
            p["cabeca"] = 0.35 + 0.15 * s
        return p

    def desenhar(self, tela, ctx, J):
        H = self.H
        A, B = self.cor_a, self.cor_b
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        mar = self.tipo == "marionete"
        corc = self.tipo == "corcunda"
        if mar:
            return self.marionete(tela, ctx, J)
        braco(tela, J, "b", B.escuro(1), B.escuro(1))
        if not corc and self.armado:
            armas.adaga(tela, J["mao_b"], J["arma_b"], 10, ACO, OURO_VELHO, larg=1.4)
        perna(tela, J, "b", A.escuro(1), None, pe_mat=B.escuro(1))
        perna(tela, J, "f", B, None, pe_mat=A)
        # sapatos de bico enrolado
        for lado, m in (("b", B.escuro(1)), ("f", A)):
            d = J["dedo_" + lado]
            tela.pintar(tela.corrente([d, d + v2(3, -1), d + v2(4, -4)], [1.3, 1.0, 0.6]), m)
            tela.px(d[0] + 4, d[1] - 5, OURO_VELHO[5])
        # túnica em losangos com barra pontuda e sinos
        tun = tela.poly(Q.pts([(-0.09 * H, T * 0.3), (0.09 * H, T * 0.3), (0.12 * H, -0.16 * H), (0.06 * H, -0.1 * H),
                               (0.02 * H, -0.18 * H), (-0.03 * H, -0.1 * H), (-0.08 * H, -0.17 * H), (-0.11 * H, -0.1 * H)]))
        tela.pintar(tun, A)
        m = tronco(tela, J, A, cintura=0.13, peito=0.19, corcunda=0.07 if corc else 0.0, barriga=0.02 if corc else 0)
        losangos(tela, (m | tun), B, tam=4)
        for k, x in enumerate((0.12, 0.02, -0.08)):
            p = Q.pt(x * H, -0.17 * H)
            tela.pintar(tela.circulo(p + v2(0, 1), 1.2), OURO_VELHO)
        # gola pontuda
        u = J["u"]
        f = v2(-u[1], u[0])
        c = J["pescoco"] - u * 1
        gola = []
        for i in range(9):
            ang = math.pi * i / 8
            r = H * (0.085 if i % 2 == 0 else 0.045)
            gola.append(c + f * math.cos(ang) * r * 1.1 - u * math.sin(ang) * r * 0.9)
        tela.pintar(tela.poly([c + f * H * 0.06] + gola + [c - f * H * 0.06]), B)
        for i in range(0, 9, 2):
            ang = math.pi * i / 8
            r = H * 0.085
            p = c + f * math.cos(ang) * r * 1.1 - u * math.sin(ang) * r * 0.9
            tela.px(p[0], p[1], OURO_VELHO[5])
        self.cabeca(tela, J, ctx)
        mf = J["mao_f"]
        if corc:
            # marotte: cetro com um crânio de bobo e sinos
            d = dir_ang(J["arma_f"])
            topo = mf + d * H * 0.38
            tela.pintar(tela.capsula(mf - d * 4, topo, 1.0), MADEIRA)
            tela.pintar(tela.elipse(topo[0], topo[1] - 1, 3.5, 3.2), OSSO)
            tela.px(topo[0] + 0.5, topo[1] - 1, (20, 10, 14))
            tela.px(topo[0] + 2.5, topo[1] - 1, (20, 10, 14))
            for k, off in enumerate((-4, 0, 4)):
                q = topo + v2(off, -4 - (2 if k == 1 else 0))
                tela.pintar(tela.capsula(topo + v2(0, -2), q, 1.0), A if k % 2 else B)
                tela.pintar(tela.circulo(q, 1.0), OURO_VELHO)
        elif self.armado:
            armas.adaga(tela, mf, J["arma_f"], 12, ACO.claro(1), OURO_VELHO, larg=1.4)
        braco(tela, J, "f", A, B)
        golpe_rastro(tela, ctx, J, H * 0.5, -0.6, 2.1, cor=(240, 220, 200))
        morte_extras(tela, self, ctx, J)

    def cabeca(self, tela, J, ctx):
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.85
        A, B = self.cor_a, self.cor_b
        s = math.sin(ctx.a)
        # chapéu de três pontas com sinos
        pontas = [((-w * 0.2, h * 0.5), (-w * 1.3 + s * 0.5, h * 0.4), (-w * 1.35 + s * 0.5, -h * 0.25), A),
                  ((w * 0.0, h * 0.55), (w * 0.0, h * 1.35), (-w * 0.45, h * 1.6), B),
                  ((w * 0.3, h * 0.5), (w * 1.1 - s * 0.5, h * 0.95), (w * 1.25 - s * 0.5, h * 0.4), A)]
        for base, meio, ponta, mat in pontas:
            pts = [C.pt(*base), C.pt(meio[0], meio[1]), C.pt(*ponta)]
            tela.pintar(tela.corrente(pts, [h * 0.32, h * 0.2, h * 0.08]), mat)
            q = C.pt(*ponta)
            tela.pintar(tela.circulo(q, 1.3), OURO_VELHO)
        tela.pintar(tela.poly(C.pts([(-w * 0.5, h * 0.25), (w * 0.5, h * 0.3), (w * 0.4, h * 0.65), (-w * 0.45, h * 0.6)])), B)
        # máscara branca com lágrima negra e sorriso pintado
        cara = Mat((222, 216, 210), 6, satur=0.2)
        cr = [(-w * 0.35, h * 0.3), (w * 0.4, h * 0.32), (w * 0.58, h * 0.05), (w * 0.62, -h * 0.15), (w * 0.4, -h * 0.5),
              (w * 0.05, -h * 0.5), (-w * 0.3, -h * 0.2)]
        tela.pintar(tela.poly(C.pts(cr)), cara)
        for x in (w * 0.18, w * 0.45):
            tela.chapado(tela.circulo(C.pt(x, h * 0.08), 1.2), (16, 10, 16))
        tela.traco(C.pt(w * 0.45, h * 0.0), C.pt(w * 0.45, -h * 0.25), (20, 14, 22))
        tela.tracos([C.pt(w * 0.05, -h * 0.25), C.pt(w * 0.3, -h * 0.35), C.pt(w * 0.55, -h * 0.25)], (120, 14, 26))
        tela.px(*C.pt(w * 0.3, h * 0.08), (255, 220, 120), emite=True)

    def marionete(self, tela, ctx, J):
        H = self.H
        A, B = self.cor_a, self.cor_b
        madeira = Mat((150, 116, 80), 6, ruido=0.3, relevo=1.2)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        # fios subindo até o topo da célula (cortados quando morre)
        fios = () if (ctx.anim == "morte" and ctx.i >= 2) else ("mao_f", "mao_b", "topo", "joelho_f")
        for k in fios:
            p = J[k]
            tela.traco(p, v2(p[0] + (p[0] - self.ancora[0]) * 0.15, 0), (150, 146, 160))
        # cruzeta de controle não aparece (fora da tela) — só os fios
        self._membro_madeira(tela, J, "b", madeira.escuro(1), braco=True)
        self._membro_madeira(tela, J, "b", madeira.escuro(1), braco=False)
        self._membro_madeira(tela, J, "f", madeira, braco=False)
        tun = tela.poly(Q.pts([(-0.09 * H, T * 0.3), (0.09 * H, T * 0.3), (0.1 * H, -0.12 * H), (0.04 * H, -0.08 * H),
                               (0.0, -0.14 * H), (-0.05 * H, -0.08 * H), (-0.1 * H, -0.13 * H)]))
        tela.pintar(tun, A)
        m = tronco(tela, J, A, cintura=0.13, peito=0.18)
        losangos(tela, m | tun, B.escuro(1), tam=5)
        pescoco(tela, J, madeira, 0.02)
        # cabeça de porcelana rachada com bochechas pintadas
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.85
        por = Mat((228, 222, 214), 6, satur=0.2, relevo=1.2)
        cr = [(-w * 0.48, h * 0.05), (-w * 0.42, h * 0.4), (-w * 0.05, h * 0.55), (w * 0.35, h * 0.48), (w * 0.55, h * 0.2),
              (w * 0.6, -h * 0.15), (w * 0.45, -h * 0.45), (w * 0.05, -h * 0.52), (-w * 0.35, -h * 0.25)]
        tela.pintar(tela.poly(C.pts(cr)), por)
        buraco = tela.poly(C.pts([(-w * 0.1, h * 0.5), (w * 0.2, h * 0.45), (w * 0.05, h * 0.2), (-w * 0.25, h * 0.3)]))
        tela.chapado(buraco, (14, 8, 12))
        tela.tracos([C.pt(w * 0.05, h * 0.2), C.pt(w * 0.2, h * 0.0), C.pt(w * 0.1, -h * 0.2)], (100, 90, 96), sobre=True)
        for x in (w * 0.15, w * 0.42):
            tela.chapado(tela.circulo(C.pt(x, h * 0.08), 1.3), (16, 10, 16))
        tela.px(*C.pt(w * 0.42, h * 0.08), (200, 230, 255), emite=True)
        tela.px(*C.pt(w * 0.5, -h * 0.15), (180, 60, 70))
        tela.traco(C.pt(w * 0.15, -h * 0.32), C.pt(w * 0.5, -h * 0.3), (60, 30, 36))
        # mandíbula articulada (linhas de boneco ventríloquo)
        tela.traco(C.pt(w * 0.15, -h * 0.3), C.pt(w * 0.15, -h * 0.5), (120, 110, 110), sobre=True)
        # chapéu de bobo pequeno
        tela.pintar(tela.corrente([C.pt(-w * 0.2, h * 0.5), C.pt(-w * 0.9, h * 0.8), C.pt(-w * 1.1, h * 0.2)],
                                  [h * 0.3, h * 0.18, h * 0.08]), A)
        tela.pintar(tela.circulo(C.pt(-w * 1.1, h * 0.2), 1.3), OURO_VELHO)
        # florete
        mf = J["mao_f"]
        armas.espada(tela, mf, J["arma_f"], H * 0.42, ACO.claro(1), OURO_VELHO, OURO_VELHO, larg=0.8, guarda_larg=2.5, ponta=0.1)
        self._membro_madeira(tela, J, "f", madeira, braco=True)
        golpe_rastro(tela, ctx, J, H * 0.6, 1.2, 2.0, cor=(220, 220, 240))

    def _membro_madeira(self, tela, J, lado, mat, braco=True):
        if braco:
            a, b, c = J["ombro_" + lado], J["cotovelo_" + lado], J["mao_" + lado]
            r = 1.6
        else:
            a, b, c = J["quadril_" + lado], J["joelho_" + lado], J["tornozelo_" + lado]
            r = 2.0
        tela.pintar(tela.capsula(a, lerp(a, b, 0.85), r, r * 0.8), mat)
        tela.pintar(tela.capsula(lerp(b, c, 0.12), c, r * 0.85, r * 0.7), mat)
        tela.pintar(tela.circulo(b, r * 0.9), mat.escuro(1))
        if braco:
            tela.pintar(tela.circulo(c, r * 1.1), mat)
        else:
            tela.pintar(pe(tela, J, lado, 0.9), mat)


# ============================================================
# FLAGELANTE (penitente encapuzado) e CARNIÇAL
# ============================================================

class Flagelante(Modelo):
    nome = "flagelante"
    H = 76
    estilo = "corte"
    base = dict(braco_f=(0.2, 0.4), braco_b=(0.7, 1.4), arma_f=0.9, pe_f=(-0.06, 0), pe_b=(0.08, 0), tronco=0.12,
                cabeca=0.1)
    prop = dict(ombros=0.23)

    def desenhar(self, tela, ctx, J):
        H = self.H
        tunica = Mat((176, 168, 152), 6, desce=0.35, ruido=0.25, relevo=0.7, arredonda=0.6, satur=0.4)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        pele = PELE.escuro(1)
        braco(tela, J, "b", tunica.escuro(1), pele.escuro(1))
        perna(tela, J, "b", pele.escuro(1), None, pe_mat=pele.escuro(1))
        perna(tela, J, "f", pele, None, pe_mat=pele)
        mm = manto(tela, J, tunica, folga=0.05, rasgos=6, semente=14, barra=0.06)
        # costas abertas e ensanguentadas
        costas = tela.poly(Q.pts([(-0.12 * H, T * 0.2), (-0.045 * H, T * 0.2), (-0.04 * H, T * 0.95), (-0.12 * H, T * 0.95)]))
        tela.pintar(costas & mm, pele, linha_interna=False)
        for k in range(4):
            tela.traco(Q.pt(-0.11 * H, T * (0.35 + k * 0.15)), Q.pt(-0.05 * H, T * (0.42 + k * 0.15)), (130, 16, 24), sobre=True)
        # sangue escorrendo no tecido
        respingos(tela, mm & tela.poly(Q.pts([(-0.1 * H, -0.4 * H), (0.1 * H, -0.4 * H), (0.1 * H, T * 0.3), (-0.1 * H, T * 0.3)])),
                  limiar=0.25)
        # corda na cintura
        cinto(tela, J, Mat((150, 120, 80), 5, ruido=0.5), larg=0.016)
        p = Q.pt(0.04 * H, -0.01 * H)
        tela.traco(p, p + v2(1, 10), (150, 120, 80))
        tela.traco(p + v2(1, 0), p + v2(2, 9), (110, 86, 56))
        # capuz cônico (capirote) com furos para os olhos
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.95
        cone = [(-w * 0.62, -h * 0.75), (-w * 0.65, h * 0.2), (-w * 0.3, h * 0.55), (-w * 0.1, h * 2.3), (w * 0.15, h * 2.35),
                (w * 0.4, h * 0.6), (w * 0.62, h * 0.2), (w * 0.62, -h * 0.75)]
        tela.pintar(tela.poly(C.pts(cone)), tunica)
        # babeiro do capuz caindo no peito
        tela.pintar(tela.poly(C.pts([(-w * 0.62, -h * 0.5), (w * 0.62, -h * 0.5), (w * 0.8, -h * 1.5), (-w * 0.5, -h * 1.6)])),
                    tunica.escuro(1))
        for x in (w * 0.2, w * 0.45):
            c = C.pt(x, h * 0.1)
            tela.chapado(tela.elipse(c[0], c[1], 1.2, 1.5), (10, 6, 10))
            tela.px(c[0], c[1], (255, 230, 200), emite=True)
        tela.traco(C.pt(w * 0.45, -h * 0.05), C.pt(w * 0.5, -h * 0.6), (120, 14, 24), sobre=True)
        # cruz de madeira nas costas? — corrente-chicote (flagelo) com pontas de ferro
        mf = J["mao_f"]
        d = dir_ang(J["arma_f"])
        tela.pintar(tela.capsula(mf - d * 3, mf + d * 4, 1.1), MADEIRA)
        base = mf + d * 4
        osc = math.sin(ctx.a) * 0.3 if ctx.anim == "parado" else (1.2 if ctx.golpe else 0.5)
        for k in range(3):
            ang = J["arma_f"] + math.pi * 0.85 + osc + (k - 1) * 0.25
            pts = [base]
            for j in range(1, 6):
                pts.append(base + dir_ang(ang + j * 0.08 * (k - 1)) * j * H * 0.05)
            for j in range(len(pts) - 1):
                tela.traco(pts[j], pts[j + 1], FERRO[3] if j % 2 else FERRO[2])
            tela.pintar(tela.poly([pts[-1] + v2(-1.2, 0), pts[-1] + v2(1.2, 0), pts[-1] + dir_ang(ang) * 3]), FERRO)
        braco(tela, J, "f", tunica, pele)
        golpe_rastro(tela, ctx, J, H * 0.55, -0.6, 2.2, cor=(230, 200, 190))
        morte_extras(tela, self, ctx, J)


class Carnical(Modelo):
    nome = "carnical"
    H = 64
    estilo = "garra"
    prop = dict(ombros=0.25, cabeca=0.15, braco=0.21, antebraco=0.21, l_braco=0.032, l_antebraco=0.028, l_coxa=0.048,
                l_canela=0.036, mao=0.05)
    base = dict(tronco=0.7, cabeca=-0.7, quadril=(0, 0.13), braco_f=(0.1, 0.4), braco_b=(-0.2, 0.3), pe_f=(-0.13, 0),
                pe_b=(0.13, 0))

    def desenhar(self, tela, ctx, J):
        H = self.H
        pele = Mat((120, 128, 118), 6, satur=0.4, relevo=1.1, ruido=0.2)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        braco(tela, J, "b", pele.escuro(1), pele.escuro(1))
        garras(tela, J, "b", comp=5)
        perna(tela, J, "b", pele.escuro(1), None, pe_mat=pele.escuro(1))
        perna(tela, J, "f", pele, None, pe_mat=pele)
        tronco(tela, J, pele, cintura=0.11, peito=0.17, corcunda=0.05)
        for k in range(4):
            tela.traco(Q.pt(-0.02 * H, T * (0.42 + k * 0.13)), Q.pt(0.07 * H, T * (0.4 + k * 0.13)), pele[2], sobre=True)
        for k in range(6):
            tela.px(*Q.pt(-0.1 * H, T * (0.25 + k * 0.12)), pele[5])
        tr = tela.poly(Q.pts([(-0.07 * H, 0.04 * H), (0.07 * H, 0.04 * H), (0.05 * H, -0.12 * H), (-0.06 * H, -0.08 * H)]))
        tela.pintar(tr, Mat((60, 50, 46), 5, ruido=0.6))
        pescoco(tela, J, pele, 0.03)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.9
        cr = [(-w * 0.75, h * 0.25), (-w * 0.5, h * 0.48), (w * 0.0, h * 0.5), (w * 0.4, h * 0.38), (w * 0.58, h * 0.1),
              (w * 0.65, -h * 0.25), (w * 0.4, -h * 0.55), (w * 0.0, -h * 0.5), (-w * 0.45, -h * 0.1)]
        tela.pintar(tela.poly(C.pts(cr)), pele)
        boca = tela.poly(C.pts([(w * 0.05, -h * 0.12), (w * 0.62, -h * 0.15), (w * 0.55, -h * 0.5), (w * 0.1, -h * 0.42)]))
        tela.chapado(boca, (40, 10, 14))
        for k in range(4):
            p = C.pt(w * (0.15 + k * 0.12), -h * 0.15)
            tela.px(p[0], p[1], OSSO[5])
            tela.px(p[0] + 0.5, p[1] - 3, OSSO[4])
        for x in (w * 0.2, w * 0.45):
            p = C.pt(x, h * 0.12)
            tela.px(p[0], p[1], (230, 250, 230), emite=True)
        tela.brilho(C.pt(w * 0.32, h * 0.12), 3.5, (200, 255, 210), 0.45)
        braco(tela, J, "f", pele, pele)
        garras(tela, J, "f", comp=6)
        if ctx.anim == "ataque" and ctx.i == 1:
            c = J["mao_f"] + v2(5, 0)
            for k in range(3):
                tela.traco(c + v2(-2 + k * 3, -7), c + v2(3 + k * 3, 7), (220, 60, 60), emite=True)
        morte_extras(tela, self, ctx, J, cor=(40, 30, 20), cor2=(70, 50, 30))
