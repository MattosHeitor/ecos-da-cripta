"""Inimigos: goblins, esqueletos e orcs (com variantes para hordas)."""
import math

import numpy as np

from ..motor import Mat, metal, misturar, v2, lerp, dir_ang, norm, Quadro
from ..humanoide import (perna, braco, tronco, pescoco, cabeca_base, olho, manto, capa, capuz, cinto,
                         quadro_tronco, quadro_cabeca, sangue_no_chao, esqueleto)
from ..anim import Modelo, idle, dano, morte, ESTILOS
from .. import armas, fx
from .herois import (PELE, COURO, COURO_ESC, ACO, FERRO, OURO_VELHO, MALHA, OSSO, MADEIRA, morte_extras,
                     golpe_rastro)

FERRUGEM = metal((122, 104, 94), ruido=0.8, especular=(200, 185, 170), contraste=1.0)
TRAPO = Mat((86, 70, 54), 5, ruido=0.4, desce=0.2)


# ============================================================
# GOBLINS
# ============================================================

class Goblin(Modelo):
    nome = "goblin"
    H = 50
    estilo = "estocada"
    pele = Mat((104, 124, 74), 6, relevo=1.0)
    prop = dict(cabeca=0.21, pescoco=0.02, tronco=0.25, coxa=0.2, canela=0.19, braco=0.21, antebraco=0.2,
                ombros=0.27, l_braco=0.042, l_antebraco=0.036, l_coxa=0.06, l_canela=0.045, quadris=0.2, mao=0.06,
                pe=0.11)
    base = dict(tronco=0.38, cabeca=-0.3, quadril=(0.0, 0.07), braco_f=(0.5, 0.9), braco_b=(0.1, 0.7),
                arma_f=1.3, pe_f=(-0.1, 0), pe_b=(0.12, 0))
    tipo = "ladrao"
    escala_jogo = 3

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "xama":
            self.estilo = "magia"
            self.nome = "goblin_xama"
            self.base = dict(self.base, braco_f=(0.6, 0.6), arma_f=0.1)
        elif self.tipo == "bruto":
            self.nome = "goblin_bruto"
            self.H = 62
            self.estilo = "corte"
            self.larg, self.alt = int(self.H * 2.05), int(self.H * 1.6)
            self.ancora = (int(self.H * 1.08), self.alt - 4)
            self.prop = dict(self.prop, ombros=0.33, l_braco=0.055, l_antebraco=0.05, l_coxa=0.065, tronco=0.27)
            self.pele = Mat((92, 108, 70), 6, relevo=1.1)
            self.base = dict(self.base, arma_f=0.5, braco_f=(0.3, 0.6))

    def desenhar(self, tela, ctx, J):
        H = self.H
        pele, pe2 = self.pele, self.pele.escuro(1)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        braco(tela, J, "b", pe2, pe2)
        if self.tipo == "ladrao":
            armas.adaga(tela, J["mao_b"], 2.6, 7, FERRUGEM, COURO_ESC)
        perna(tela, J, "b", pe2, None, pe_mat=pe2)
        perna(tela, J, "f", pele, None, pe_mat=pele)
        # garras dos pés
        for lado in ("f", "b"):
            d = J["dedo_" + lado]
            tela.px(d[0] + 1, d[1], OSSO[4])
        tronco(tela, J, pele, cintura=0.16, peito=0.2, ombros=0.24, barriga=0.03)
        # costelas aparentes
        for k in range(3):
            tela.traco(Q.pt(-0.02 * H, T * (0.5 + k * 0.12)), Q.pt(0.07 * H, T * (0.47 + k * 0.12)), pele[2], sobre=True)
        # tanga de trapo e cinto com bugigangas
        tanga = tela.poly(Q.pts([(-0.09 * H, 0.04 * H), (0.1 * H, 0.04 * H), (0.08 * H, -0.16 * H), (0.03 * H, -0.12 * H),
                                 (-0.02 * H, -0.18 * H), (-0.08 * H, -0.1 * H)]))
        tela.pintar(tanga, TRAPO)
        cinto(tela, J, COURO_ESC, larg=0.03)
        for k in range(3):
            p = Q.pt(-0.06 * H + k * 0.05 * H, -0.02 * H)
            tela.px(p[0], p[1] + 2, OSSO[5] if k != 1 else (160, 140, 60))
            tela.px(p[0], p[1] + 3, OSSO[3])
        if self.tipo == "bruto":
            # placa de ferro amarrada no peito e ombreira de prego
            pl = tela.poly(Q.pts([(-0.05 * H, T * 0.35), (0.09 * H, T * 0.38), (0.08 * H, T * 0.85), (-0.06 * H, T * 0.8)]))
            tela.pintar(pl & tela.mascara(), FERRUGEM)
            for x, y in ((0.0, 0.42), (0.06, 0.45), (0.0, 0.75), (0.06, 0.77)):
                tela.px(*Q.pt(x * H, T * y), FERRO[5])
        if self.tipo == "xama":
            # colar de ossos e penas
            for k in range(5):
                p = Q.pt(-0.06 * H + k * 0.03 * H, T * 0.95 - abs(k - 2) * 0.8)
                tela.px(p[0], p[1], OSSO[5])
            capa(tela, J, Mat((60, 40, 50), 5, ruido=0.6), comprimento=0.35, larg=0.14, rasgos=6, semente=4)
        pescoco(tela, J, pele, 0.05)
        self.cabeca(tela, J, ctx)
        # arma
        mf = J["mao_f"]
        if self.tipo == "ladrao":
            armas.adaga(tela, mf, J["arma_f"], 11, FERRUGEM, COURO_ESC, larg=1.6)
        elif self.tipo == "bruto":
            armas.maca(tela, mf, J["arma_f"], H * 0.42, MADEIRA, MADEIRA.claro(1), raio=3.6, cravos=6)
            c = mf + dir_ang(J["arma_f"]) * H * 0.42
            for k in range(5):
                a = J["arma_f"] + k * 1.25
                p = c + dir_ang(a) * 5.5
                tela.px(p[0], p[1], FERRO[4])
        else:
            topo = armas.cajado(tela, mf, J["arma_f"], H * 0.45, MADEIRA, atras=H * 0.45, torto=1.5)
            tela.pintar(tela.circulo(topo, 3.2), OSSO)
            tela.px(topo[0] + 1, topo[1], (20, 10, 14))
            tela.px(topo[0] - 1, topo[1], (20, 10, 14))
            fx.chama(tela, topo + v2(0, -2), 9 + math.sin(ctx.a * 2), 6, fx.FOGO_VERDE, fase=ctx.a * 2)
            if ctx.golpe:
                fx.orbe(tela, J["mao_b"] + v2(3, 0), 3, fx.FOGO_VERDE)
                fx.chama(tela, J["mao_b"] + v2(8, 2), 8, 7, fx.FOGO_VERDE, fase=ctx.a, inclina=1.2)
        braco(tela, J, "f", pele, pele)
        tela.pintar(tela.circulo(mf, H * 0.045), pele)
        golpe_rastro(tela, ctx, J, H * 0.62, -1.0, 2.0) if self.tipo == "bruto" else None
        morte_extras(tela, self, ctx, J, cor=(40, 50, 18), cor2=(70, 86, 30))

    def cabeca(self, tela, J, ctx):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.95
        pele = self.pele
        s = math.sin(ctx.a)
        # orelha comprida (atrás)
        tela.pintar(tela.poly(C.pts([(-w * 0.2, h * 0.15), (-w * 1.15, h * 0.45 + s * 0.6), (-w * 0.95, h * 0.25),
                                     (-w * 0.2, -h * 0.15)])), pele.escuro(1))
        cr = [(-w * 0.5, h * 0.05), (-w * 0.4, h * 0.38), (-w * 0.05, h * 0.5), (w * 0.35, h * 0.42), (w * 0.52, h * 0.2),
              (w * 0.62, h * 0.0), (w * 0.85, -h * 0.12), (w * 0.62, -h * 0.2), (w * 0.62, -h * 0.32), (w * 0.4, -h * 0.5),
              (w * 0.0, -h * 0.48), (-w * 0.35, -h * 0.25)]
        tela.pintar(tela.poly(C.pts(cr)), pele)
        # orelha da frente
        tela.pintar(tela.poly(C.pts([(-w * 0.15, h * 0.2), (-w * 0.9, h * 0.62 - s * 0.6), (-w * 0.7, h * 0.35),
                                     (-w * 0.15, -h * 0.05)])), pele)
        tela.traco(C.pt(-w * 0.3, h * 0.25), C.pt(-w * 0.75, h * 0.48), (140, 80, 80), sobre=True)
        # olhos amarelos brilhando
        for x in (w * 0.2, w * 0.45):
            p = C.pt(x, h * 0.08)
            tela.px(p[0], p[1], (255, 210, 60), emite=True)
            tela.px(p[0] + 1, p[1], (200, 40, 20), emite=True)
        tela.traco(C.pt(w * 0.1, h * 0.18), C.pt(w * 0.55, h * 0.13), pele[0])
        # boca larga com dentes
        tela.traco(C.pt(w * 0.05, -h * 0.28), C.pt(w * 0.55, -h * 0.3), (30, 12, 16))
        for k in range(4):
            p = C.pt(w * (0.1 + k * 0.13), -h * 0.27)
            tela.px(p[0], p[1], OSSO[5] if k % 2 == 0 else OSSO[4])
        if self.tipo == "ladrao":
            # capacete-panela enferrujado
            tela.pintar(tela.poly(C.pts([(-w * 0.5, h * 0.25), (w * 0.5, h * 0.3), (w * 0.4, h * 0.62), (-w * 0.35, h * 0.6)])),
                        FERRUGEM)
            tela.traco(C.pt(-w * 0.55, h * 0.24), C.pt(w * 0.58, h * 0.29), FERRUGEM[1])
        elif self.tipo == "xama":
            # máscara de crânio de pássaro e penas
            tela.pintar(tela.poly(C.pts([(-w * 0.1, h * 0.45), (w * 0.4, h * 0.42), (w * 1.1, -h * 0.05), (w * 0.4, -h * 0.15),
                                         (-w * 0.05, -h * 0.05)])), OSSO)
            tela.px(*C.pt(w * 0.3, h * 0.12), (120, 255, 120), emite=True)
            tela.brilho(C.pt(w * 0.3, h * 0.12), 3, (100, 255, 100), 0.6)
            for k, cor in enumerate(((120, 30, 30), (40, 40, 60), (120, 30, 30))):
                b0 = C.pt(-w * 0.3 + k * 0.15 * w, h * 0.42)
                tela.traco(b0, b0 + J["hu"] * 6 + v2(-3 + k, 0), cor)


# ============================================================
# ESQUELETOS
# ============================================================

class Esqueleto(Modelo):
    nome = "esqueleto"
    H = 74
    estilo = "corte"
    tipo = "soldado"
    osso = Mat((196, 192, 178), 6, relevo=1.0, luz_hue=0.6, satur=0.7)
    olhos = (120, 255, 220)
    base = dict(braco_f=(0.4, 0.6), braco_b=(0.7, 0.8), arma_f=0.7, pe_f=(-0.07, 0), pe_b=(0.09, 0), tronco=0.08,
                cabeca=0.05)

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "arqueiro":
            self.nome = "esqueleto_arqueiro"
            self.estilo = "arco"
            self.base = dict(self.base, braco_b=(0.2, 0.15), braco_f=(0.15, 0.3), arma_b=0.0)
        elif self.tipo == "cavaleiro":
            self.nome = "esqueleto_cavaleiro"
            self.H = 80
            self.estilo = "pesado"
            self.olhos = (255, 90, 60)
            self.base = dict(self.base, braco_f=(0.3, 0.6), braco_b=(0.35, 0.7), arma_f=0.35)
            self._recalc()
        elif self.tipo == "gigante":
            self.nome = "ossario_gigante"
            self.H = 118
            self.estilo = "pesado"
            self.olhos = (255, 170, 60)
            self.prop = dict(ombros=0.34, cabeca=0.15)
            self.base = dict(self.base, braco_f=(0.3, 0.5), braco_b=(0.1, 0.5), arma_f=0.6, tronco=0.3, cabeca=-0.25, quadril=(0, 0.04))
            self._recalc()

    def _recalc(self):
        self.larg, self.alt = int(self.H * 2.05), int(self.H * 1.6)
        self.ancora = (int(self.H * 1.08), self.alt - 4)

    def pose(self, ctx):
        p = super().pose(ctx)
        if ctx.anim == "ataque" and self.tipo == "soldado":
            p["braco_b"] = (0.8, 0.9)
        return p

    def desenhar(self, tela, ctx, J):
        H = self.H
        if ctx.anim == "morte" and ctx.i >= 2:
            self.pilha(tela, ctx, J)
            return
        osso, o2 = self.osso, self.osso.escuro(1)
        g = H / 74
        gig = self.tipo == "gigante"
        esp = 2.3 if gig else 1.0
        if self.tipo == "cavaleiro":
            capa(tela, J, Mat((60, 30, 34), 5, ruido=0.4, relevo=0.6), comprimento=0.5, larg=0.13, rasgos=7, semente=8,
                 vento=0.03 * math.sin(ctx.a))
        # braço de trás
        self.braco_osso(tela, J, "b", o2, esp)
        if self.tipo == "soldado":
            # escudo redondo rachado
            m, c = armas.escudo(tela, J["mao_b"] + v2(1, 1), Mat((76, 54, 40), 5, ruido=0.6), FERRUGEM, larg=8, alt=8,
                                forma="redondo")
            tela.traco(c + v2(-2, -7), c + v2(1, 0), (30, 20, 20), sobre=True)
            tela.traco(c + v2(1, 0), c + v2(-1, 6), (30, 20, 20), sobre=True)
            tela.pintar(tela.circulo(c, 2), FERRUGEM)
        elif self.tipo == "arqueiro":
            mb = J["mao_b"]
            d = dir_ang(math.pi / 2 + J.get("arma_b", 0))
            puxa = 0.0
            flecha = None
            if ctx.anim == "ataque" and ctx.i in (0, 1):
                puxa = max(0.0, float(np.dot(mb - J["mao_f"], d)) - 3)
                flecha = (120, 100, 80)
            armas.arco_flecha(tela, mb, math.pi / 2 + J["arma_b"] + (0.3 if ctx.anim == "parado" else 0), H * 0.6,
                              Mat((70, 56, 46), 5), (150, 140, 120), puxa=puxa, flecha=flecha, ponta=FERRUGEM)
        self.perna_osso(tela, J, "b", o2, esp)
        self.perna_osso(tela, J, "f", osso, esp)
        if gig:
            self.corpo_gigante(tela, J, ctx)
        else:
            self.corpo(tela, J, ctx)
        self.cranio(tela, J, ctx)
        mf = J["mao_f"]
        a = J["arma_f"]
        if self.tipo == "soldado":
            armas.espada(tela, mf, a, H * 0.46, FERRUGEM, FERRUGEM.escuro(1), COURO_ESC, larg=1.5, guarda_larg=3.5)
        elif self.tipo == "cavaleiro":
            armas.espada(tela, mf, a, H * 0.6, FERRO, FERRUGEM, COURO_ESC, larg=2.2, guarda_larg=5.5, pomo=FERRUGEM,
                         sangue=0.3)
        elif gig:
            # clava feita de um fêmur gigante
            d = dir_ang(a)
            n = v2(-d[1], d[0])
            b = mf + d * H * 0.45
            tela.pintar(tela.capsula(mf - d * 6, b, 2.6, 4.0), osso)
            tela.pintar(tela.circulo(b + n * 3, 5.2) | tela.circulo(b - n * 3, 5.2), osso)
            for k in range(4):
                p = b + dir_ang(a + k * 1.5 - 1) * 7
                tela.pintar(tela.poly([p - n * 1, p + n * 1, p + dir_ang(a + k * 1.5 - 1) * 5]), FERRO)
        self.braco_osso(tela, J, "f", osso, esp)
        if self.tipo == "cavaleiro":
            # ombreira enferrujada
            o, u = J["ombro_f"], J["u"]
            tela.pintar(tela.elipse_girada(o + u * 1.5, H * 0.06, H * 0.045, math.atan2(u[1], u[0]) + 1.4), FERRUGEM)
        if self.tipo in ("cavaleiro", "gigante", "soldado"):
            golpe_rastro(tela, ctx, J, H * (0.7 if self.tipo != "soldado" else 0.62), -1.3, 2.0, cor=(180, 230, 220))

    # ---- partes ----
    def braco_osso(self, tela, J, lado, m, esp=1.0):
        o, c, mao = J["ombro_" + lado], J["cotovelo_" + lado], J["mao_" + lado]
        tela.pintar(tela.capsula(o, c, 1.3 * esp, 1.0 * esp), m)
        d = norm(mao - c)
        n = v2(-d[1], d[0])
        tela.pintar(tela.capsula(c + n * 0.5 * esp, mao + n * 0.5 * esp, 0.8 * esp) | tela.capsula(c - n * 0.6 * esp, mao - n * 0.3 * esp, 0.7 * esp), m)
        tela.pintar(tela.circulo(c, 1.5 * esp), m)
        # mão de ossos
        for k in (-1, 0, 1):
            tela.traco(mao, mao + d * 3 * esp + n * k * 1.2 * esp, m[3])

    def perna_osso(self, tela, J, lado, m, esp=1.0):
        q, j, t = J["quadril_" + lado], J["joelho_" + lado], J["tornozelo_" + lado]
        tela.pintar(tela.capsula(q, j, 1.6 * esp, 1.3 * esp), m)
        tela.pintar(tela.capsula(j, t, 1.2 * esp, 0.9 * esp), m)
        tela.pintar(tela.circulo(j, 1.9 * esp), m)
        tela.pintar(tela.poly([t + v2(-1.5, -1) * esp, t + v2(1, -1) * esp, J["dedo_" + lado] + v2(1, 0),
                               J["calcanhar_" + lado] + v2(0, 0.5)]), m)

    def corpo(self, tela, J, ctx, esp=1.0):
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        osso = self.osso
        # bacia
        tela.pintar(tela.poly(Q.pts([(-0.07 * H, 0.04 * H), (0.07 * H, 0.04 * H), (0.05 * H, -0.03 * H), (0.0, -0.01 * H),
                                     (-0.05 * H, -0.03 * H)])), osso)
        if self.tipo in ("soldado", "arqueiro"):
            # trapos pendurados
            tr = tela.poly(Q.pts([(-0.06 * H, 0.03 * H), (0.06 * H, 0.03 * H), (0.04 * H, -0.14 * H), (0.01 * H, -0.09 * H),
                                  (-0.03 * H, -0.16 * H)]))
            tela.pintar(tr, Mat((70, 40, 44), 5, ruido=0.5))
        # coluna
        for k in range(9):
            p = Q.pt(-0.015 * H, T * (0.05 + k * 0.11))
            tela.pintar(tela.circulo(p, 1.3 * esp), osso.escuro(1))
        # caixa torácica (costelas com vãos)
        cx = tela.poly(Q.pts([(-0.06 * H, T * 0.42), (0.04 * H, T * 0.38), (0.085 * H, T * 0.6), (0.075 * H, T * 0.92),
                              (-0.02 * H, T * 1.0), (-0.075 * H, T * 0.85)]))
        vaos = np.zeros_like(cx)
        for k in range(5):
            y = 0.47 + k * 0.105
            vaos |= tela.poly(Q.pts([(-0.04 * H, T * y), (0.1 * H, T * (y - 0.05)), (0.1 * H, T * (y - 0.02)),
                                     (-0.04 * H, T * (y + 0.035))]))
        tela.pintar(cx & ~vaos, osso)
        # esterno
        tela.traco(Q.pt(0.05 * H, T * 0.55), Q.pt(0.055 * H, T * 0.92), osso[2], sobre=True)
        if self.tipo == "cavaleiro":
            # couraça enferrujada sobre as costelas, malha rasgada
            sa = tela.poly(Q.pts([(-0.08 * H, 0.03 * H), (0.08 * H, 0.03 * H), (0.09 * H, -0.15 * H), (-0.09 * H, -0.13 * H)]))
            tela.pintar(sa, MALHA.escuro(1))
            m = tronco(tela, J, FERRUGEM, cintura=0.12, peito=0.18, topo=0.95, base=0.35)
            buraco = tela.elipse_girada(Q.pt(0.03 * H, T * 0.6), 3, 4, 0.4)
            tela.chapado(buraco & m, (20, 12, 16))
            tela.traco(Q.pt(0.0, T * 0.55), Q.pt(0.04 * H, T * 0.65), osso[4], sobre=True)

    def corpo_gigante(self, tela, J, ctx):
        """Ossário: esqueleto colossal com crânios presos e brasas no peito."""
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        osso = self.osso
        self.corpo(tela, J, ctx, esp=2.2)
        c = Q.pt(0.02 * H, T * 0.68)
        tela.brilho(c, 14, (255, 130, 40), 0.55 + 0.2 * math.sin(ctx.a))
        for k in range(3):
            p = c + v2(-3 + k * 3, (k % 2) * 2)
            tela.px(p[0], p[1], (255, 190, 80), emite=True)
        # correntes penduradas
        for k in range(2):
            a0 = Q.pt(-0.06 * H + k * 0.1 * H, T * 0.4)
            for j in range(6):
                q = a0 + v2(math.sin(ctx.a + j * 0.5) * 0.6, j * 2.2)
                tela.px(q[0], q[1], FERRO[3 + (j % 2)])
        # crânios nos ombros
        for lado in ("b", "f"):
            p = J["ombro_" + lado] + J["u"] * 2
            tela.pintar(tela.elipse(p[0], p[1], 4.5, 4.0), osso if lado == "f" else osso.escuro(1))
            tela.chapado(tela.circulo(p + v2(1, 0), 1.0), (20, 10, 14))
            tela.chapado(tela.circulo(p + v2(3.2, 0), 1.0), (20, 10, 14))

    def cranio(self, tela, J, ctx):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.85
        osso = self.osso
        cr = [(-w * 0.5, h * 0.05), (-w * 0.42, h * 0.38), (-w * 0.05, h * 0.52), (w * 0.35, h * 0.45), (w * 0.55, h * 0.15),
              (w * 0.58, -h * 0.1), (w * 0.45, -h * 0.2), (w * 0.0, -h * 0.15), (-w * 0.35, -h * 0.1)]
        tela.pintar(tela.poly(C.pts(cr)), osso)
        # mandíbula solta (abre no ataque)
        ab = 0.15 if ctx.golpe else (0.04 if ctx.i % 2 else 0.0)
        mand = [(w * 0.0, -h * 0.2), (w * 0.52, -h * (0.22 + ab)), (w * 0.48, -h * (0.42 + ab)), (w * 0.05, -h * (0.42 + ab * 0.5)),
                (-w * 0.12, -h * 0.25)]
        tela.pintar(tela.poly(C.pts(mand)), osso.escuro(1))
        for k in range(4):
            p = C.pt(w * (0.12 + k * 0.11), -h * 0.2)
            tela.px(p[0], p[1], osso[5])
        # órbitas e nariz
        for x in (w * 0.18, w * 0.42):
            p = C.pt(x, h * 0.08)
            tela.chapado(tela.circulo(p, 1.4), (14, 8, 12))
            tela.px(p[0], p[1], self.olhos, emite=True)
        tela.brilho(C.pt(w * 0.3, h * 0.08), 5, self.olhos, 0.45 + 0.15 * math.sin(ctx.a))
        tela.px(*C.pt(w * 0.5, -h * 0.05), (20, 10, 14))
        # rachadura
        tela.traco(C.pt(-w * 0.1, h * 0.5), C.pt(w * 0.05, h * 0.25), osso[1], sobre=True)
        if self.tipo == "cavaleiro":
            elmo = [(-w * 0.55, -h * 0.05), (-w * 0.5, h * 0.45), (w * 0.0, h * 0.62), (w * 0.4, h * 0.55), (w * 0.6, h * 0.25),
                    (w * 0.6, h * 0.18), (-w * 0.3, h * 0.2), (-w * 0.3, -h * 0.1)]
            tela.pintar(tela.poly(C.pts(elmo)), FERRUGEM)
            tela.traco(C.pt(-w * 0.1, h * 0.62), C.pt(-w * 0.2, h * 1.05), FERRUGEM[2])
            tela.traco(C.pt(-w * 0.2, h * 1.05), C.pt(-w * 0.45, h * 1.2), FERRUGEM[1])
        elif self.tipo == "gigante":
            # coroa de chifres
            for k, x in enumerate((-0.3, 0.05, 0.35)):
                b = C.pt(w * x, h * 0.45)
                tela.pintar(tela.poly([b - v2(1.5, 0), b + v2(1.5, 0), C.pt(w * (x - 0.15), h * (1.1 + 0.15 * (k % 2)))]),
                            Mat((60, 54, 50), 5))

    def pilha(self, tela, ctx, J):
        """Morte: o esqueleto desmonta numa pilha de ossos."""
        H = self.H
        cx, chao = self.ancora
        rng = np.random.default_rng(7)
        osso = self.osso
        esp = 1.6 if self.tipo == "gigante" else 1.0
        n = 14 if ctx.i == 3 else 10
        alt = 0.0 if ctx.i == 3 else 1.0
        for k in range(n):
            x = cx + (rng.random() - 0.5) * H * 0.55
            y = chao - 1.5 * esp - rng.random() * (3 * esp + alt * H * 0.15 * rng.random())
            a = rng.random() * math.pi
            L = (3 + rng.random() * 5) * esp
            d = v2(math.cos(a), math.sin(a) * 0.5) * L
            tela.pintar(tela.capsula(v2(x, y) - d, v2(x, y) + d, 1.0 * esp), osso if k % 2 else osso.escuro(1))
        # costelas
        c = v2(cx - H * 0.05, chao - 3 * esp)
        for k in range(4):
            tela.pintar(tela.capsula(c + v2(-5 + k * 3, 0) * esp, c + v2(-3 + k * 3, -5) * esp, 0.8 * esp), osso)
        # crânio por cima
        cc = v2(cx + H * 0.08, chao - 4 * esp - (H * 0.08 if ctx.i == 2 else 0))
        tela.pintar(tela.elipse(cc[0], cc[1], 4 * esp, 3.6 * esp), osso)
        for dx in (-1.5, 1.5):
            tela.chapado(tela.circulo(cc + v2(dx * esp, 0), 1.0 * esp), (14, 8, 12))
        if ctx.i == 2:
            tela.px(cc[0] + 1.5 * esp, cc[1], self.olhos, emite=True)
            tela.brilho(cc, 4, self.olhos, 0.3)
        # arma caída
        if self.tipo in ("soldado", "cavaleiro"):
            armas.espada(tela, v2(cx + H * 0.25, chao - 2), 1.65, H * 0.4, FERRUGEM, FERRUGEM.escuro(1), COURO_ESC)


# ============================================================
# ORCS
# ============================================================

class Orc(Modelo):
    nome = "orc"
    H = 86
    estilo = "corte"
    tipo = "guerreiro"
    pele = Mat((92, 106, 80), 6, relevo=1.15)
    prop = dict(ombros=0.34, cabeca=0.125, tronco=0.29, l_braco=0.056, l_antebraco=0.05, l_coxa=0.066,
                l_canela=0.052, quadris=0.2, mao=0.055, pe=0.09)
    base = dict(braco_f=(0.3, 0.6), braco_b=(-0.05, 0.4), arma_f=0.6, pe_f=(-0.08, 0), pe_b=(0.1, 0), tronco=0.12,
                cabeca=-0.08, quadril=(0, 0.02))

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "berserker":
            self.nome = "orc_berserker"
            self.pele = Mat((104, 110, 82), 6, relevo=1.15)
            self.base = dict(self.base, braco_b=(0.6, 0.8), arma_b=1.9)
        elif self.tipo == "senhor":
            self.nome = "orc_senhor_da_guerra"
            self.H = 104
            self.estilo = "pesado"
            self.pele = Mat((80, 92, 74), 6, relevo=1.15)
            self.larg, self.alt = int(self.H * 2.05), int(self.H * 1.6)
            self.ancora = (int(self.H * 1.08), self.alt - 4)
            self.base = dict(self.base, arma_f=0.4)

    def pose(self, ctx):
        p = super().pose(ctx)
        if self.tipo == "berserker" and ctx.anim == "ataque":
            # golpe cruzado com as duas armas
            p["braco_b"] = [(-2.2, -0.3), (1.7, 0.1), (1.0, 0.3), (0.6, 0.6)][ctx.i]
            p["arma_b"] = [-1.8, 1.4, 2.4, 1.6][ctx.i]
        return p

    def desenhar(self, tela, ctx, J):
        H = self.H
        pele, pe2 = self.pele, self.pele.escuro(1)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        sen = self.tipo == "senhor"
        if sen:
            capa(tela, J, Mat((70, 52, 44), 6, ruido=0.8, dither=0.7), comprimento=0.58, larg=0.2, rasgos=8, semente=21,
                 vento=0.02 * math.sin(ctx.a))
        braco(tela, J, "b", pe2, pe2)
        if self.tipo == "berserker":
            armas.machado(tela, J["mao_b"], J["arma_b"], H * 0.34, MADEIRA, FERRUGEM, tam=1.0, sangue=True)
            tela.pintar(tela.circulo(J["mao_b"], H * 0.04), pe2)
        perna(tela, J, "b", COURO_ESC.escuro(1), Mat((60, 50, 44), 5, ruido=0.8), cano=0.5)
        perna(tela, J, "f", COURO_ESC, Mat((76, 62, 52), 5, ruido=0.8), cano=0.5)
        tronco(tela, J, pele, cintura=0.17, peito=0.26, ombros=0.3, barriga=0.02)
        # músculos
        tela.traco(Q.pt(-0.05 * H, T * 0.7), Q.pt(0.08 * H, T * 0.66), pele[1], sobre=True)
        tela.traco(Q.pt(0.015 * H, T * 0.62), Q.pt(0.02 * H, T * 0.2), pele[1], sobre=True)
        if self.tipo == "berserker":
            # pintura de guerra vermelha e cicatrizes
            for k in range(3):
                tela.traco(Q.pt(-0.06 * H + k * 3, T * 0.95), Q.pt(-0.03 * H + k * 3, T * 0.3), (130, 22, 26), sobre=True)
            for k in range(3):
                tela.traco(Q.pt(0.03 * H, T * (0.3 + k * 0.1)), Q.pt(0.08 * H, T * (0.35 + k * 0.1)), pele[4], sobre=True)
        else:
            # arnês de couro
            tela.pintar(tela.poly(Q.pts([(-0.09 * H, T * 0.95), (-0.04 * H, T * 1.0), (0.09 * H, T * 0.25), (0.05 * H, T * 0.2)])) &
                        tela.mascara(), COURO_ESC)
            tela.pintar(tela.circulo(Q.pt(0.03 * H, T * 0.58), 2.2), FERRO)
        if sen:
            pl = tronco(tela, J, FERRO, cintura=0.16, peito=0.25, ombros=0.29, base=0.3)
            for k in range(4):
                tela.traco(Q.pt(-0.08 * H, T * (0.4 + k * 0.13)), Q.pt(0.1 * H, T * (0.42 + k * 0.13)), FERRO[1], sobre=True)
            # crânio humano preso no peito
            c = Q.pt(0.03 * H, T * 0.68)
            tela.pintar(tela.elipse(c[0], c[1], 3.5, 3.2), OSSO)
            tela.px(c[0] - 1, c[1], (20, 10, 14))
            tela.px(c[0] + 1.5, c[1], (20, 10, 14))
        # saiote e cinto com placas
        saia = tela.poly(Q.pts([(-0.1 * H, 0.04 * H), (0.1 * H, 0.04 * H), (0.11 * H, -0.17 * H), (0.04 * H, -0.13 * H),
                                (-0.01 * H, -0.19 * H), (-0.06 * H, -0.14 * H), (-0.11 * H, -0.18 * H)]))
        tela.pintar(saia, COURO)
        cinto(tela, J, COURO_ESC, fivela=OSSO, larg=0.032)
        pescoco(tela, J, pele, 0.06)
        self.cabeca(tela, J, ctx)
        mf = J["mao_f"]
        a = J["arma_f"]
        if self.tipo == "guerreiro":
            # cutelo enorme
            d = dir_ang(a)
            n = v2(-d[1], d[0])
            tela.pintar(tela.capsula(mf - d * 3, mf + d * 3, 1.3), COURO_ESC)
            b = mf + d * 3
            lam = tela.poly([b - n * 1.5, b + d * H * 0.38 - n * 1.5, b + d * H * 0.4 + n * 4, b + d * 4 + n * 8, b + n * 6])
            tela.pintar(lam, FERRUGEM)
            ms = lam & tela.poly([b + d * H * 0.2 + n * 2, b + d * H * 0.42 + n * 2, b + d * H * 0.42 + n * 9, b + d * H * 0.2 + n * 9])
            tela.chapado(ms & (tela.ruido_base > -0.1), (100, 12, 20))
            tela.px(*(b + d * 5 + n * 2), (20, 14, 16))
        elif self.tipo == "berserker":
            armas.machado(tela, mf, a, H * 0.36, MADEIRA, FERRUGEM, tam=1.1, sangue=True)
        else:
            armas.machado(tela, mf, a, H * 0.5, MADEIRA.escuro(1), FERRO, duplo=True, tam=1.5, sangue=True)
        braco(tela, J, "f", pele, pele)
        tela.pintar(tela.circulo(mf, H * 0.042), pele)
        # ombreira com espinhos
        o, u = J["ombro_f"], J["u"]
        ang = math.atan2(u[1], u[0]) + 1.4
        if self.tipo != "berserker":
            tela.pintar(tela.elipse_girada(o + u * 2, H * 0.07, H * 0.05, ang), FERRO)
            for k in range(3):
                b = o + u * (3 + k * 0.5) + v2(-4 + k * 4, 0)
                tela.pintar(tela.poly([b - v2(1.2, 0), b + v2(1.2, 0), b + u * 5]), OSSO)
        else:
            tela.pintar(tela.capsula(lerp(J["cotovelo_f"], mf, 0.3), mf, H * 0.05), COURO_ESC)
        golpe_rastro(tela, ctx, J, H * 0.7, -1.3, 2.0, cor=(230, 200, 190))
        morte_extras(tela, self, ctx, J, cor=(50, 8, 12), cor2=(90, 14, 20))

    def cabeca(self, tela, J, ctx):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.95
        pele = self.pele
        cr = [(-w * 0.5, h * 0.05), (-w * 0.45, h * 0.4), (-w * 0.0, h * 0.5), (w * 0.38, h * 0.42), (w * 0.55, h * 0.18),
              (w * 0.62, -h * 0.05), (w * 0.68, -h * 0.25), (w * 0.62, -h * 0.5), (w * 0.2, -h * 0.58), (-w * 0.2, -h * 0.45),
              (-w * 0.45, -h * 0.2)]
        tela.pintar(tela.poly(C.pts(cr)), pele)
        # orelha
        tela.pintar(tela.poly(C.pts([(-w * 0.2, h * 0.15), (-w * 0.65, h * 0.35), (-w * 0.25, -h * 0.05)])), pele.escuro(1))
        # sobrancelha pesada e olho vermelho
        tela.traco(C.pt(w * 0.1, h * 0.2), C.pt(w * 0.6, h * 0.12), pele[0])
        p = C.pt(w * 0.4, h * 0.05)
        tela.px(p[0], p[1], (255, 60, 40), emite=True)
        tela.brilho(p, 3, (255, 60, 30), 0.5)
        # presas
        for x in (0.25, 0.5):
            b = C.pt(w * x, -h * 0.38)
            tela.pintar(tela.poly([b - v2(1, 0), b + v2(1, 0), b + J["hu"] * 4.5]), OSSO)
        tela.traco(C.pt(w * 0.15, -h * 0.35), C.pt(w * 0.62, -h * 0.35), (30, 14, 16), sobre=True)
        if self.tipo == "guerreiro":
            # coque de guerra
            tela.pintar(tela.circulo(C.pt(-w * 0.25, h * 0.55), 2.6), Mat((30, 26, 30), 4))
            tela.traco(C.pt(-w * 0.25, h * 0.6), C.pt(-w * 0.8, h * 0.2), (40, 34, 38))
        elif self.tipo == "berserker":
            # moicano vermelho
            for k in range(6):
                b = C.pt(-w * 0.4 + k * w * 0.15, h * 0.45 + (0.05 * h if 1 < k < 4 else 0))
                tela.traco(b, b + J["hu"] * (4 + (k % 2)) + v2(-1, 0), (140, 30, 26) if k % 2 else (100, 20, 20))
        else:
            # elmo com chifres
            elmo = [(-w * 0.55, h * 0.0), (-w * 0.5, h * 0.48), (w * 0.0, h * 0.62), (w * 0.45, h * 0.52), (w * 0.62, h * 0.25),
                    (w * 0.62, h * 0.12), (-w * 0.2, h * 0.15), (-w * 0.35, -h * 0.05)]
            tela.pintar(tela.poly(C.pts(elmo)), FERRO)
            for s in (-1, 1):
                b = C.pt(w * (0.0 + 0.25 * s), h * 0.5)
                ch = [b, b + J["hu"] * 5 + v2(-3 * (1 if s < 0 else -0.5), 0), b + J["hu"] * 9 + v2(-6, 0)]
                tela.pintar(tela.corrente(ch, [2.0, 1.4, 0.5]), OSSO.escuro(1) if s < 0 else OSSO)
