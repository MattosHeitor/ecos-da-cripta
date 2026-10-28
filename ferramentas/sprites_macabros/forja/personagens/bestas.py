"""Bestas: aranhas, insetos gigantes e dragões (corpos não-humanos)."""
import math

import numpy as np

from ..motor import Mat, metal, v2, lerp, dir_ang, norm, girar
from ..anim import Modelo
from ..humanoide import sangue_no_chao
from .. import armas, fx
from .herois import OSSO

SANGUE_INSETO = ((40, 60, 18), (80, 110, 30))


def refletir_y(P, eixo):
    """Espelha os pontos verticalmente (bicho morto de barriga para cima)."""
    out = {}
    for k, p in P.items():
        if isinstance(p, np.ndarray) and p.shape == (2,):
            out[k] = v2(p[0], 2 * eixo - p[1])
        elif isinstance(p, list) and p and isinstance(p[0], np.ndarray):
            out[k] = [v2(q[0], 2 * eixo - q[1]) for q in p]
        else:
            out[k] = p
    return out


def transformar(P, ang=0.0, pivo=(0, 0), desloc=(0, 0)):
    out = {}
    d = v2(desloc)
    for k, p in P.items():
        if isinstance(p, np.ndarray) and p.shape == (2,):
            out[k] = girar(p, ang, pivo) + d
        elif isinstance(p, list) and p and isinstance(p[0], np.ndarray):
            out[k] = [girar(q, ang, pivo) + d for q in p]
        else:
            out[k] = p
    return out


def perna_articulada(tela, pts, larguras, mat, pelos=False, cor_pelo=None):
    tela.pintar(tela.corrente(pts, larguras), mat)
    for p in pts[1:-1]:
        tela.pintar(tela.circulo(p, larguras[1] * 1.05), mat)
    if pelos:
        for i in range(len(pts) - 1):
            for t in (0.3, 0.6):
                q = lerp(pts[i], pts[i + 1], t)
                d = norm(pts[i + 1] - pts[i])
                n = v2(-d[1], d[0])
                tela.px(*(q + n * (larguras[i] + 1)), cor_pelo or mat[0])


class Besta(Modelo):
    """Base para corpos não-humanos: pose() devolve um dicionário de pontos."""

    def esqueleto(self, pose):
        return pose

    def quadro(self, anim, i, n):
        """Bestas e objetos não sentam: a linha "sentado" repete o "parado"."""
        return super().quadro("parado" if anim == "sentado" else anim, i, n)


# ============================================================
# ARANHAS
# ============================================================

class Aranha(Besta):
    nome = "aranha"
    S = 60
    tipo = "comum"

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "filhote":
            self.nome = "aranha_filhote"
            self.S = 34
            self.corpo = Mat((92, 74, 62), 6, ruido=0.5, dither=0.6)
        elif self.tipo == "mae":
            self.nome = "aranha_mae"
            self.S = 96
            self.corpo = Mat((44, 34, 46), 6, ruido=0.5, dither=0.6)
        else:
            self.corpo = Mat((70, 52, 44), 6, ruido=0.5, dither=0.6)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.6), int(S * 1.45)
        self.ancora = (int(S * 1.3), self.alt - 3)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        alt = 0.42 * S
        bob = 0.0
        incl = 0.0
        avanco = 0.0
        presas = 0.0
        ergue = 0.0
        if ctx.anim == "parado":
            bob = [0, 0.6, 1, 0.6][ctx.i] * 0.025 * S
        elif ctx.anim == "ataque":
            incl, avanco, ergue, presas = [(-0.35, -0.05, 1.0, 0.3), (0.12, 0.28, 0.4, 1.0), (0.18, 0.32, 0.1, 0.6),
                                           (0.05, 0.1, 0.0, 0.2)][ctx.i]
        elif ctx.anim == "dano":
            incl, avanco = [(-0.25, -0.12), (-0.1, -0.05)][ctx.i]
        P = {}
        ct = v2(cx + 0.12 * S + avanco * S, chao - alt + bob)
        if ctx.anim == "morte":
            alt2 = [0.36, 0.22, 0.2, 0.2][ctx.i] * S
            ct = v2(cx + 0.05 * S, chao - alt2)
            incl = [-0.2, 0.08, 0, 0][ctx.i]
        P["ct"] = ct
        P["abd"] = ct + girar(v2(-0.55 * S, -0.04 * S), incl)
        P["cab"] = ct + girar(v2(0.3 * S, 0.03 * S), incl)
        P["incl"] = incl
        P["presas"] = presas
        pes_b = [-0.75, -0.3, 0.38, 0.85]
        pes_f = [-0.88, -0.42, 0.28, 0.98]
        for lado, pes in (("b", pes_b), ("f", pes_f)):
            pernas = []
            for k in range(4):
                quadril = ct + girar(v2((-0.1 + k * 0.08) * S, 0.03 * S), incl)
                pe = v2(cx + pes[k] * S + avanco * S * (0.6 if k > 1 else 0.3), chao - 1)
                if ctx.anim == "ataque" and k >= 2:
                    pe = pe + v2(0.1 * S * ergue, -0.55 * S * ergue * (1.0 if k == 3 else 0.6))
                if ctx.anim == "morte":
                    spread = [1.0, 1.15, 1.25, 1.25][ctx.i]
                    pe = v2(cx + pes[k] * S * spread, chao - 1)
                    if ctx.i == 3:
                        # patas encolhidas
                        pe = quadril + v2((pes[k] * 0.35) * S, -0.18 * S)
                joelho = lerp(quadril, pe, 0.42) + v2(0, -0.38 * S - (0.1 * S * ergue if k >= 2 else 0))
                if ctx.anim == "morte" and ctx.i == 3:
                    joelho = lerp(quadril, pe, 0.5) + v2(pes[k] * 0.12 * S, -0.22 * S)
                tarso = lerp(joelho, pe, 0.72) + v2(0.04 * S * np.sign(pes[k]), -0.02 * S)
                pernas.append([quadril, joelho, tarso, pe])
            P["pernas_" + lado] = pernas
        if ctx.anim == "morte" and ctx.i == 3:
            P = refletir_y(P, ct[1])
            P = transformar(P, desloc=(0, (chao - 0.36 * S) - P["abd"][1]))
        P["morto"] = ctx.anim == "morte" and ctx.i >= 2
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        c = self.corpo
        larg = [0.05 * S, 0.042 * S, 0.03 * S, 0.016 * S]
        larg = [max(0.7, x) for x in larg]
        for perna in P["pernas_b"]:
            perna_articulada(tela, perna, larg, c.escuro(2))
        # abdômen
        incl = P["incl"]
        abd = tela.elipse_girada(P["abd"], 0.42 * S, 0.34 * S, incl - 0.12)
        tela.pintar(abd, c)
        # marca no abdômen
        a = P["abd"]
        if self.tipo == "comum":
            k = 0.12 * S
            cr = tela.elipse(a[0] - 0.05 * S, a[1] - 0.08 * S, k, k * 0.9)
            tela.pintar(cr & abd, Mat((180, 170, 150), 5), linha_interna=False)
            for dx in (-0.4, 0.4):
                tela.chapado(tela.circulo(a + v2(-0.05 * S + dx * k, -0.08 * S), k * 0.28), (30, 20, 24))
            tela.traco(a + v2(-0.05 * S - k * 0.5, -0.08 * S + k * 0.7), a + v2(-0.05 * S + k * 0.5, -0.08 * S + k * 0.7),
                       (30, 20, 24), sobre=True)
        elif self.tipo == "mae":
            hg = tela.poly([a + v2(-0.08 * S, -0.2 * S), a + v2(0.08 * S, -0.2 * S), a + v2(0.0, -0.08 * S),
                            a + v2(0.08 * S, 0.04 * S), a + v2(-0.08 * S, 0.04 * S), a + v2(0.0, -0.08 * S)])
            tela.chapado(hg & abd, (170, 20, 30), emite=True)
            tela.brilho(a + v2(0, -0.08 * S), 0.15 * S, (200, 20, 30), 0.3)
            # saco de ovos preso na ponta
            if not P["morto"]:
                e = a + girar(v2(-0.42 * S, 0.12 * S), incl)
                ov = tela.elipse(e[0], e[1], 0.17 * S, 0.15 * S)
                tela.pintar(ov, Mat((200, 196, 186), 5, ruido=0.4, relevo=0.8))
                for kk in range(5):
                    q = e + v2(math.cos(kk * 1.3) * 0.1 * S, math.sin(kk * 1.3) * 0.08 * S)
                    tela.px(q[0], q[1], (150, 140, 120))
        # pelos no contorno
        rng = np.random.default_rng(1)
        for kk in range(int(S * 0.5)):
            ang = rng.random() * math.pi * 2
            p = a + v2(math.cos(ang) * 0.43 * S, math.sin(ang) * 0.35 * S)
            tela.px(p[0], p[1], c[1])
        # cefalotórax e cabeça
        tela.pintar(tela.elipse_girada(P["ct"], 0.24 * S, 0.19 * S, incl), c.claro(1))
        cab = P["cab"]
        tela.pintar(tela.elipse_girada(cab, 0.15 * S, 0.13 * S, incl), c)
        # presas
        pr = P["presas"]
        for k, dy in enumerate((0.0, 0.05)):
            b = cab + girar(v2(0.1 * S, (0.06 + dy) * S), incl)
            pts = [b, b + v2(0.05 * S + pr * 0.04 * S, 0.06 * S), b + v2(0.01 * S, 0.12 * S + pr * 0.04 * S)]
            tela.pintar(tela.corrente(pts, [0.03 * S, 0.02 * S, 0.008 * S + 0.4]), Mat((170, 150, 120), 5) if k else Mat((140, 120, 96), 5))
        if pr > 0.5:
            tela.px(*(cab + v2(0.1 * S, 0.2 * S)), (120, 230, 80), emite=True)
        # olhos vermelhos (vários)
        if not P["morto"]:
            olhos = [(0.08, -0.04, 0.03), (0.12, -0.02, 0.025), (0.04, -0.06, 0.02), (0.1, -0.08, 0.018), (0.14, -0.06, 0.015)]
            for x, y, r in olhos:
                q = cab + girar(v2(x * S, y * S), incl)
                tela.chapado(tela.circulo(q, max(0.6, r * S)), (230, 30, 40), emite=True)
                tela.px(q[0] - 0.3, q[1] - 0.3, (255, 200, 200), emite=True)
            tela.brilho(cab + v2(0.09 * S, -0.05 * S), 0.12 * S, (255, 30, 40), 0.4)
        else:
            for x, y in ((0.08, -0.04), (0.12, -0.02)):
                tela.px(*(cab + v2(x * S, y * S)), (60, 20, 24))
        for perna in P["pernas_f"]:
            perna_articulada(tela, perna, larg, c, pelos=S > 50)
        if ctx.anim == "morte" and ctx.i >= 2:
            cx, chao = self.ancora
            sangue_no_chao(tela, cx, chao, S * 0.5, (40, 60, 18), (80, 110, 30))


# ============================================================
# LOUVA-A-DEUS GIGANTE
# ============================================================

class LouvaDeus(Besta):
    nome = "louva_a_deus"
    S = 88

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.3), int(S * 1.4)
        self.ancora = (int(S * 1.05), self.alt - 3)
        self.corpo = Mat((118, 122, 90), 6, ruido=0.3, satur=0.6, relevo=1.1)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        bob = 0.0
        golpe = 0.0  # 0 dobrado, 1 esticado
        recuo = 0.0
        incl = -0.3
        if ctx.anim == "parado":
            bob = [0, 0.5, 1, 0.5][ctx.i] * 0.015 * S
        elif ctx.anim == "ataque":
            golpe, recuo, incl = [(-0.4, -0.05, -0.45), (1.0, 0.12, -0.05), (0.85, 0.14, 0.0), (0.2, 0.04, -0.25)][ctx.i]
        elif ctx.anim == "dano":
            recuo, incl = [(-0.08, -0.55), (-0.04, -0.42)][ctx.i]
        baixa = 0.0
        if ctx.anim == "morte":
            recuo, incl, baixa, golpe = [(-0.06, -0.55, 0.0, 0.0), (0.0, -0.9, 0.12, -0.2), (0.05, -1.25, 0.22, 0.3),
                                         (0.08, -1.4, 0.26, 0.4)][ctx.i]
        P = {"golpe": golpe}
        base = v2(cx + recuo * S, chao - 0.36 * S + bob + baixa * S)
        P["base"] = base
        P["abd0"] = base + v2(-0.04 * S, 0.0)
        P["abd1"] = base + v2(-0.58 * S, 0.12 * S)
        P["pesc"] = base + dir_ang(-incl) * 0.0 + v2(math.sin(-incl * -1) * 0.0, 0) + girar(v2(0, -0.48 * S), -incl * -1)
        P["pesc"] = base + v2(math.sin(-incl) * -0.48 * S * -1, -math.cos(incl) * 0.48 * S)
        pesc = P["pesc"]
        P["cab"] = pesc + v2(0.06 * S, -0.05 * S)
        ombro = lerp(base, pesc, 0.72)
        P["ombro"] = ombro
        # pata raptorial
        if golpe >= 0:
            cox = ombro + v2(0.06 * S + 0.05 * S * golpe, 0.12 * S - 0.04 * S * golpe)
            fem = cox + lerp(v2(0.1 * S, -0.2 * S), v2(0.3 * S, -0.02 * S), golpe)
            tib = fem + lerp(v2(-0.03 * S, 0.17 * S), v2(0.26 * S, 0.08 * S), golpe)
        else:
            g = -golpe
            cox = ombro + v2(0.02 * S, 0.06 * S)
            fem = cox + lerp(v2(0.1 * S, -0.2 * S), v2(-0.02 * S, -0.3 * S), g)
            tib = fem + lerp(v2(-0.03 * S, 0.17 * S), v2(0.1 * S, -0.1 * S), g)
        P["rapt"] = [ombro, cox, fem, tib]
        P["rapt_b"] = [ombro + v2(0.03 * S, -0.01 * S), cox + v2(0.04 * S, -0.02 * S), fem + v2(0.03 * S, -0.03 * S),
                       tib + v2(0.03 * S, -0.03 * S)]
        pernas = {}
        for lado, offs in (("b", (0.18, -0.48)), ("f", (0.1, -0.58))):
            L = []
            for k, (q, px) in enumerate(((base + v2(-0.02 * S, 0.02 * S), offs[0]), (base + v2(-0.1 * S, 0.04 * S), offs[1]))):
                pe = v2(cx + px * S + recuo * S * 0.3, chao - 1)
                joelho = lerp(q, pe, 0.45) + v2(0, -0.22 * S)
                L.append([q, joelho, pe])
            pernas[lado] = L
        P["pernas"] = pernas
        if ctx.anim == "morte" and ctx.i >= 1:
            for lado in ("b", "f"):
                for L in P["pernas"][lado]:
                    L[1] = lerp(L[0], L[2], 0.5) + v2(0, -0.08 * S * (3 - ctx.i))
                    L[2] = L[2] + v2((L[2][0] - cx) * 0.3, 0)
        P["morto"] = ctx.anim == "morte" and ctx.i >= 3
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        c = self.corpo
        cb = c.escuro(2)
        for L in P["pernas"]["b"]:
            perna_articulada(tela, L, [0.02 * S, 0.016 * S, 0.01 * S], cb)
        # pata raptorial de trás
        self.raptorial(tela, P["rapt_b"], cb)
        # abdômen segmentado
        a0, a1 = P["abd0"], P["abd1"]
        abd = tela.capsula(a0, a1, 0.09 * S, 0.06 * S) | tela.elipse_girada(lerp(a0, a1, 0.55), 0.3 * S, 0.12 * S,
                                                                             math.atan2(a1[1] - a0[1], a1[0] - a0[0]))
        tela.pintar(abd, c)
        for k in range(1, 6):
            q = lerp(a0, a1, k / 6)
            d = norm(a1 - a0)
            n = v2(-d[1], d[0])
            tela.traco(q - n * 0.13 * S, q + n * 0.13 * S, c[1], sobre=True)
        # asas dobradas (folha seca translúcida)
        asa = tela.elipse_girada(lerp(a0, a1, 0.45) + v2(0, -0.06 * S), 0.33 * S, 0.07 * S,
                                 math.atan2(a1[1] - a0[1], a1[0] - a0[0]) - 0.05)
        tela.pintar(asa, Mat((96, 90, 64), 5, relevo=0.4, dither=0.8), linha_interna=True)
        tela.traco(lerp(a0, a1, 0.1) + v2(0, -0.06 * S), lerp(a0, a1, 0.8) + v2(0, -0.05 * S), c[0], sobre=True)
        # protórax longo
        tela.pintar(tela.capsula(P["base"], P["pesc"], 0.06 * S, 0.035 * S), c)
        for L in P["pernas"]["f"]:
            perna_articulada(tela, L, [0.022 * S, 0.018 * S, 0.012 * S], c.escuro(1))
        # cabeça triangular com olhos enormes
        cab = P["cab"]
        hd = tela.poly([cab + v2(-0.08 * S, -0.04 * S), cab + v2(0.08 * S, -0.06 * S), cab + v2(0.03 * S, 0.1 * S)])
        tela.pintar(hd, c.claro(1))
        for dx in (-0.06, 0.06):
            o = cab + v2(dx * S, -0.05 * S)
            tela.pintar(tela.circulo(o, 0.035 * S), Mat((120, 26, 30), 5, relevo=1.3, especular=(255, 200, 190)))
        if not P["morto"]:
            tela.px(*(cab + v2(0.06 * S, -0.05 * S)), (255, 120, 100), emite=True)
        # antenas
        tela.traco(cab + v2(0.0, -0.08 * S), cab + v2(0.18 * S, -0.3 * S), c[3])
        tela.traco(cab + v2(-0.02 * S, -0.08 * S), cab + v2(0.08 * S, -0.34 * S), c[2])
        # pata raptorial da frente
        self.raptorial(tela, P["rapt"], c)
        if ctx.anim == "ataque" and ctx.i == 1:
            tib = P["rapt"][-1]
            armas.rastro(tela, P["rapt"][1], 0.3 * S, 0.42 * S, 0.0, 2.2, cor=(220, 230, 200))
        if ctx.anim == "morte" and ctx.i >= 2:
            cx, chao = self.ancora
            sangue_no_chao(tela, cx - 0.3 * S, chao, S * 0.35, *SANGUE_INSETO)

    def raptorial(self, tela, pts, mat):
        S = self.S
        ombro, cox, fem, tib = pts
        tela.pintar(tela.capsula(ombro, cox, 0.03 * S, 0.028 * S), mat)
        tela.pintar(tela.capsula(cox, fem, 0.034 * S, 0.026 * S), mat)
        # espinhos do fêmur
        d = norm(fem - cox)
        n = v2(-d[1], d[0])
        for k in range(1, 4):
            q = lerp(cox, fem, k / 4.2)
            tela.traco(q + n * 0.03 * S, q + n * 0.06 * S + d * 0.02 * S, OSSO[4])
        # tíbia em forma de foice
        d2 = norm(tib - fem)
        n2 = v2(-d2[1], d2[0])
        lam = tela.poly([fem + n2 * 0.02 * S, tib + n2 * 0.005 * S, tib + d2 * 0.05 * S - n2 * 0.02 * S, fem - n2 * 0.025 * S])
        tela.pintar(lam, mat.claro(1))
        tela.traco(fem - n2 * 0.02 * S, tib + d2 * 0.04 * S - n2 * 0.015 * S, OSSO[5], sobre=True)


# ============================================================
# BESOURO CARNICEIRO
# ============================================================

class Besouro(Besta):
    nome = "besouro_carniceiro"
    S = 76

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.3), int(S * 1.15)
        self.ancora = (int(S * 1.1), self.alt - 3)
        self.casca = metal((30, 40, 44), especular=(120, 190, 170), contraste=0.9, relevo=1.4, luz_hue=0.45)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        bob, avanco, cab_ang, ab = 0.0, 0.0, 0.0, 0.0
        if ctx.anim == "parado":
            bob = [0, 0.5, 1, 0.5][ctx.i] * 0.02 * S
            ab = [0, 0.3, 0.6, 0.3][ctx.i]
        elif ctx.anim == "ataque":
            avanco, cab_ang, ab = [(-0.1, 0.35, 1.0), (0.3, -0.45, 0.2), (0.32, -0.3, 0.8), (0.1, 0.0, 0.3)][ctx.i]
        elif ctx.anim == "dano":
            avanco, cab_ang = [(-0.12, 0.3), (-0.05, 0.1)][ctx.i]
        P = {"cab_ang": cab_ang, "ab": ab}
        corpo = v2(cx + avanco * S, chao - 0.4 * S + bob)
        P["corpo"] = corpo
        P["pronoto"] = corpo + v2(0.32 * S, 0.02 * S)
        P["cab"] = P["pronoto"] + girar(v2(0.17 * S, 0.06 * S), cab_ang)
        pernas = {}
        for lado, xs in (("b", (-0.35, 0.05, 0.45)), ("f", (-0.45, 0.0, 0.52))):
            L = []
            for k, x in enumerate(xs):
                q = corpo + v2((-0.15 + k * 0.2) * S, 0.12 * S)
                pe = v2(cx + x * S + avanco * S * 0.5, chao - 1)
                joelho = lerp(q, pe, 0.5) + v2(0.05 * S * np.sign(x + 0.01), -0.14 * S)
                L.append([q, joelho, pe])
            pernas[lado] = L
        P["pernas"] = pernas
        if ctx.anim == "morte":
            P = transformar(P, [-0.15, 0.06, 0.03, 0.0][ctx.i], (cx, chao), (0, [0.0, 0.06, 0.12, 0.14][ctx.i] * S))
            if ctx.i >= 1:
                for lado in ("b", "f"):
                    for L in P["pernas"][lado]:
                        L[-1] = v2(L[-1][0] + (L[-1][0] - cx) * 0.4, chao - 1)
                        L[1] = lerp(L[0], L[-1], 0.5) + v2(0, -0.04 * S)
            P["cab_ang"] = 0.4 * ctx.i
        P["morto"] = ctx.anim == "morte" and ctx.i >= 2
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        cs = self.casca
        perna_mat = Mat((40, 34, 36), 5, relevo=1.2, especular=(140, 160, 150))
        for L in P["pernas"]["b"]:
            perna_articulada(tela, L, [0.03 * S, 0.024 * S, 0.012 * S], perna_mat.escuro(1))
        # élitros (carapaça)
        c = P["corpo"]
        car = tela.elipse_girada(c, 0.45 * S, 0.28 * S, 0.0)
        car &= ~tela.poly([c + v2(-S, 0.12 * S), c + v2(S, 0.12 * S), c + v2(S, S), c + v2(-S, S)]) | tela.elipse_girada(c, 0.45 * S, 0.16 * S, 0)
        tela.pintar(car, cs)
        tela.traco(c + v2(-0.42 * S, -0.02 * S), c + v2(0.3 * S, -0.1 * S), cs[1], sobre=True)
        # barriga segmentada por baixo
        bar = tela.elipse_girada(c + v2(0.02 * S, 0.1 * S), 0.38 * S, 0.1 * S, 0.0)
        tela.pintar(bar, Mat((70, 50, 44), 5))
        for k in range(5):
            x = -0.25 + k * 0.12
            tela.traco(c + v2(x * S, 0.04 * S), c + v2(x * S + 0.02 * S, 0.17 * S), (40, 26, 26), sobre=True)
        # pronoto e cabeça com chifre e mandíbulas
        pr = P["pronoto"]
        tela.pintar(tela.elipse_girada(pr, 0.15 * S, 0.14 * S, 0.0), cs.escuro(1))
        cab = P["cab"]
        a = P["cab_ang"]
        tela.pintar(tela.elipse_girada(cab, 0.1 * S, 0.08 * S, a), cs.escuro(1))
        chifre = [cab + girar(v2(0.0, -0.04 * S), a), cab + girar(v2(0.12 * S, -0.18 * S), a), cab + girar(v2(0.08 * S, -0.32 * S), a)]
        tela.pintar(tela.corrente(chifre, [0.045 * S, 0.03 * S, 0.008 * S + 0.5]), cs)
        ab = P["ab"]
        for k, s in enumerate((-1, 1)):
            b = cab + girar(v2(0.08 * S, 0.03 * S), a)
            pts = [b, b + girar(v2(0.08 * S, s * 0.02 * S * (1 + ab)), a), b + girar(v2(0.12 * S, s * -0.03 * S), a)]
            tela.pintar(tela.corrente(pts, [0.02 * S, 0.014 * S, 0.5]), Mat((90, 30, 30), 5, especular=(220, 120, 110)))
        if not P["morto"]:
            o = cab + girar(v2(0.02 * S, -0.02 * S), a)
            tela.px(o[0], o[1], (255, 200, 60), emite=True)
            tela.brilho(o, 3, (255, 180, 40), 0.5)
        for L in P["pernas"]["f"]:
            perna_articulada(tela, L, [0.032 * S, 0.026 * S, 0.014 * S], perna_mat)
        # restos de carne presos (é carniceiro)
        if ctx.anim == "ataque" and ctx.i == 1:
            for k in range(3):
                y = c[1] - 0.1 * S + k * 0.12 * S
                tela.traco(v2(c[0] - 0.7 * S, y), v2(c[0] - 0.5 * S, y), (180, 190, 200), emite=True)
        if ctx.anim == "morte" and ctx.i >= 2:
            cx, chao = self.ancora
            sangue_no_chao(tela, cx, chao, S * 0.45, *SANGUE_INSETO)


# ============================================================
# VESPA SANGRENTA (voa)
# ============================================================

class Vespa(Besta):
    nome = "vespa_sangrenta"
    S = 60

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.4), int(S * 1.9)
        self.ancora = (int(S * 1.15), self.alt - 3)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        voo = 0.85 * S
        bob = math.sin(ctx.a) * 0.04 * S
        asa = ctx.i % 2
        dobra = 0.0
        avanco = 0.0
        if ctx.anim == "ataque":
            dobra, avanco = [(0.3, -0.1), (1.0, 0.3), (0.9, 0.3), (0.3, 0.1)][ctx.i]
        elif ctx.anim == "dano":
            avanco = [-0.15, -0.06][ctx.i]
        P = {"asa": asa, "dobra": dobra}
        tor = v2(cx + avanco * S, chao - voo + bob)
        if ctx.anim == "morte":
            tor = v2(cx, chao - [0.75, 0.45, 0.16, 0.1][ctx.i] * S)
            P["asa"] = 2
        P["torax"] = tor
        P["cab"] = tor + v2(0.2 * S, -0.02 * S)
        # abdômen curva para baixo/frente quando ataca
        a0 = tor + v2(-0.14 * S, 0.05 * S)
        ang = 0.5 + dobra * 1.2
        P["abd"] = [a0]
        for k in range(1, 5):
            P["abd"].append(P["abd"][-1] + v2(-math.cos(ang * k / 4) * 0.1 * S, math.sin(ang * k / 4) * 0.08 * S + 0.02 * S))
        P["ferrao"] = P["abd"][-1] + v2(-math.cos(ang) * 0.12 * S, math.sin(ang) * 0.12 * S)
        pernas = []
        for k in range(3):
            q = tor + v2((-0.06 + k * 0.06) * S, 0.08 * S)
            pernas.append([q, q + v2(0.04 * S, 0.12 * S), q + v2(-0.02 * S + k * 0.02 * S, 0.24 * S)])
        P["pernas"] = pernas
        if ctx.anim == "morte" and ctx.i >= 2:
            P = refletir_y(P, tor[1])
            P = transformar(P, desloc=(0, -0.05 * S))
            for L in P["pernas"]:
                L[-1] = lerp(L[0], L[-1], 0.5)
        P["morto"] = ctx.anim == "morte" and ctx.i >= 2
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        preto = Mat((40, 32, 36), 6, relevo=1.2, especular=(160, 140, 150))
        verm = Mat((140, 26, 30), 6, relevo=1.2, especular=(255, 160, 140))
        tor = P["torax"]
        # asas (translúcidas, batendo)
        asa_cor = Mat((150, 150, 170), 4, relevo=0.3, dither=0.9)
        angs = {0: (-0.9, -1.2), 1: (-0.2, -0.45), 2: (-1.4, -1.7)}[P["asa"]]
        for k, a in enumerate(angs):
            base = tor + v2(-0.02 * S, -0.06 * S)
            d = v2(math.cos(math.pi + a), math.sin(math.pi + a))
            c = base + d * 0.24 * S
            m = tela.elipse_girada(c, 0.26 * S, 0.08 * S, math.atan2(d[1], d[0]))
            if k == 0:
                tela.pintar(m, asa_cor.escuro(1), linha_interna=False)
            else:
                tela.pintar(m & (tela.bayer > -0.2), asa_cor, linha_interna=False)
            tela.traco(base, base + d * 0.45 * S, (90, 80, 100), sobre=True)
        for L in P["pernas"]:
            perna_articulada(tela, L, [0.016 * S, 0.012 * S, 0.006 * S + 0.3], preto.escuro(1))
        # abdômen listrado
        abd = P["abd"]
        larg = [0.11 * S, 0.14 * S, 0.13 * S, 0.1 * S, 0.06 * S]
        for k in range(len(abd) - 1):
            seg = tela.capsula(abd[k], abd[k + 1], larg[k], larg[k + 1])
            tela.pintar(seg, verm if k % 2 == 0 else preto)
        tela.pintar(tela.corrente([abd[-1], P["ferrao"]], [0.025 * S, 0.004 * S + 0.4]), Mat((200, 190, 170), 4))
        # tórax e cabeça
        tela.pintar(tela.elipse(tor[0], tor[1], 0.13 * S, 0.11 * S), preto)
        tela.pintar(tela.capsula(tor + v2(0.02 * S, -0.05 * S), tor + v2(0.06 * S, 0.0), 0.04 * S), verm)
        cab = P["cab"]
        tela.pintar(tela.elipse(cab[0], cab[1], 0.09 * S, 0.1 * S), preto)
        tela.pintar(tela.elipse(cab[0] + 0.02 * S, cab[1] - 0.01 * S, 0.05 * S, 0.07 * S),
                    Mat((150, 30, 30), 5, relevo=1.4, especular=(255, 210, 200)))
        if not P["morto"]:
            tela.px(cab[0] + 0.04 * S, cab[1] - 0.03 * S, (255, 220, 200), emite=True)
        for s in (-1, 1):
            b = cab + v2(0.07 * S, 0.06 * S)
            tela.traco(b, b + v2(0.05 * S, s * 0.03 * S + 0.03 * S), (200, 180, 140))
        tela.traco(cab + v2(0.02 * S, -0.09 * S), cab + v2(0.14 * S, -0.22 * S), (60, 50, 56))
        if ctx.anim == "ataque" and ctx.i == 1:
            p = P["ferrao"]
            tela.brilho(p, 4, (180, 255, 120), 0.6)
            tela.px(p[0], p[1] + 1, (150, 255, 100), emite=True)
        if ctx.anim == "morte" and ctx.i >= 2:
            cx, chao = self.ancora
            sangue_no_chao(tela, cx, chao, S * 0.3, *SANGUE_INSETO)
# ============================================================
# DRAGÕES
# ============================================================

class Dragao(Besta):
    nome = "dragao"
    S = 120
    tipo = "vermelho"

    def __init__(self, **kw):
        super().__init__(**kw)
        if self.tipo == "osseo":
            self.nome = "dragao_osseo"
            self.escamas = Mat((60, 56, 60), 6, ruido=0.4)
            self.barriga = Mat((190, 184, 168), 6, luz_hue=0.6, satur=0.5)
            self.asa = Mat((70, 60, 66), 5, relevo=0.4, ruido=0.4)
            self.fogo = fx.FOGO_VERDE
            self.olho = (140, 255, 120)
        elif self.tipo == "filhote":
            self.nome = "dragao_filhote"
            self.S = 64
            self.escamas = Mat((60, 74, 50), 6, ruido=0.3)
            self.barriga = Mat((170, 150, 100), 6)
            self.asa = Mat((90, 60, 50), 5, relevo=0.4)
            self.fogo = fx.FOGO
            self.olho = (255, 220, 60)
        else:
            self.nome = "dragao"
            self.escamas = Mat((84, 24, 30), 6, ruido=0.4, satur=0.85)
            self.barriga = Mat((150, 108, 72), 6, satur=0.8)
            self.asa = Mat((54, 22, 30), 5, relevo=0.4, ruido=0.15)
            self.fogo = fx.FOGO
            self.olho = (255, 220, 60)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 3.2), int(S * 1.35)
        self.ancora = (int(S * 1.35), self.alt - 3)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        bob = 0.0
        pesc = 0.0      # 0 normal, >0 cabeça vai pra frente/baixo
        asa = 0.0
        boca = 0.0
        fogo = 0
        recuo = 0.0
        if ctx.anim == "parado":
            bob = [0, 0.5, 1, 0.5][ctx.i] * 0.012 * S
            asa = [0, 0.15, 0.3, 0.15][ctx.i]
        elif ctx.anim == "ataque":
            pesc, asa, boca, fogo, recuo = [(-0.5, 0.5, 0.3, 0, -0.04), (0.8, -0.3, 1.0, 1, 0.04), (0.85, -0.2, 1.0, 2, 0.05),
                                            (0.3, 0.1, 0.3, 0, 0.01)][ctx.i]
        elif ctx.anim == "dano":
            pesc, recuo, asa = [(-0.7, -0.06, 0.6), (-0.3, -0.03, 0.3)][ctx.i]
        P = {"boca": boca, "fogo": fogo, "asa": asa}
        corpo = v2(cx - 0.05 * S + recuo * S, chao - 0.42 * S + bob)
        P["corpo"] = corpo
        P["peito"] = corpo + v2(0.28 * S, -0.06 * S)
        P["quadril"] = corpo + v2(-0.25 * S, 0.0)
        # pescoço em S
        base = P["peito"] + v2(0.06 * S, -0.08 * S)
        alvo = base + lerp(v2(0.2 * S, -0.48 * S), v2(0.48 * S, -0.12 * S), max(0, pesc)) + v2(min(0, pesc) * 0.15 * S, min(0, pesc) * 0.1 * S)
        P["pescoco"] = [base, lerp(base, alvo, 0.33) + v2(0.08 * S, -0.02 * S), lerp(base, alvo, 0.66) + v2(-0.02 * S, -0.03 * S), alvo]
        P["cab_ang"] = 0.25 + pesc * 0.35
        P["cab"] = alvo
        # cauda
        q = P["quadril"]
        P["cauda"] = [q, q + v2(-0.25 * S, 0.12 * S), q + v2(-0.5 * S, 0.3 * S + bob), q + v2(-0.72 * S, 0.36 * S),
                      q + v2(-0.85 * S, 0.28 * S + math.sin(ctx.a) * 0.03 * S)]
        # pernas: quadril -> joelho -> tornozelo -> pé
        pernas = {}
        for lado, dx in (("b", 0.04), ("f", -0.04)):
            tr = P["quadril"] + v2(dx * S, 0.05 * S)
            pe_t = v2(tr[0] + 0.05 * S, chao - 1)
            jt = tr + v2(0.14 * S, 0.14 * S)
            tt = v2(pe_t[0] - 0.08 * S, chao - 0.1 * S)
            fr = P["peito"] + v2(dx * S, 0.08 * S)
            pe_f = v2(fr[0] + 0.06 * S, chao - 1)
            jf = fr + v2(-0.02 * S, 0.17 * S)
            pernas[lado] = ([tr, jt, tt, pe_t], [fr, jf, pe_f])
        P["pernas"] = pernas
        # asas
        P["ombro_asa"] = corpo + v2(0.12 * S, -0.16 * S)
        if ctx.anim == "morte":
            ang = [0.0, 0.0, 0.0, 0.0][ctx.i]
            caida = [0.0, 0.12, 0.22, 0.28][ctx.i] * S
            P = transformar(P, 0.0, (cx, chao), (0, caida * 0.6))
            P["cab"] = P["cab"] + v2(0.05 * S * ctx.i, caida * 0.9)
            P["pescoco"][-1] = P["cab"]
            P["pescoco"][-2] = P["pescoco"][-2] + v2(0, caida * 0.5)
            P["asa"] = [0.5, -0.4, -0.9, -1.2][ctx.i]
            for lado in ("b", "f"):
                tras, frente = P["pernas"][lado]
                for L in (tras, frente):
                    L[-1] = v2(L[-1][0] + (0.04 * S * ctx.i), self.ancora[1] - 1)
            P["cab_ang"] = 0.6 + 0.2 * ctx.i
        P["morto"] = ctx.anim == "morte" and ctx.i >= 3
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        esc, bar, asa = self.escamas, self.barriga, self.asa
        osseo = self.tipo == "osseo"
        # asa de trás
        self.desenhar_asa(tela, P, asa.escuro(1), lado=-1)
        # pernas de trás (lado de lá)
        tras, frente = P["pernas"]["b"]
        perna_articulada(tela, tras, [0.09 * S, 0.06 * S, 0.035 * S, 0.03 * S], esc.escuro(2))
        perna_articulada(tela, frente, [0.06 * S, 0.045 * S, 0.03 * S], esc.escuro(2))
        # cauda
        cau = P["cauda"]
        tela.pintar(tela.corrente(cau, [0.13 * S, 0.1 * S, 0.07 * S, 0.04 * S, 0.015 * S]), esc)
        tela.pintar(tela.poly([cau[-1] + v2(0, -0.05 * S), cau[-1] + v2(-0.1 * S, -0.02 * S), cau[-1] + v2(0, 0.05 * S)]), esc.escuro(1))
        # corpo
        c = P["corpo"]
        corpo = tela.elipse_girada(c, 0.36 * S, 0.2 * S, -0.08)
        corpo |= tela.elipse(P["peito"][0], P["peito"][1], 0.17 * S, 0.19 * S)
        tela.pintar(corpo, esc)
        if osseo:
            # costelas expostas no corpo
            for k in range(6):
                x = c[0] - 0.2 * S + k * 0.08 * S
                tela.traco(v2(x, c[1] - 0.15 * S), v2(x + 0.04 * S, c[1] + 0.12 * S), bar[4], sobre=True)
            tela.chapado(tela.elipse(c[0], c[1], 0.2 * S, 0.08 * S) & corpo & (tela.bayer > 0.0), (20, 14, 18))
            tela.brilho(c, 0.25 * S, self.fogo[2], 0.35 + 0.1 * math.sin(ctx.a))
        # barriga com placas
        bm = tela.elipse_girada(c + v2(0.08 * S, 0.1 * S), 0.32 * S, 0.1 * S, -0.15) & corpo
        tela.pintar(bm, bar, linha_interna=False)
        for k in range(7):
            x = c[0] - 0.15 * S + k * 0.06 * S
            tela.traco(v2(x, c[1] + 0.02 * S), v2(x + 0.02 * S, c[1] + 0.2 * S), bar[1], sobre=True)
        # espinhos nas costas
        for k in range(6):
            p = c + v2(-0.3 * S + k * 0.1 * S, -0.18 * S + abs(k - 3) * 0.01 * S)
            tela.pintar(tela.poly([p + v2(-0.03 * S, 0.02 * S), p + v2(0.03 * S, 0.02 * S), p + v2(-0.02 * S, -0.07 * S)]),
                        bar.escuro(1) if not osseo else Mat((200, 194, 180), 5))
        # pescoço
        pes = P["pescoco"]
        tela.pintar(tela.corrente(pes, [0.11 * S, 0.085 * S, 0.07 * S, 0.06 * S]), esc)
        pm = tela.corrente([lerp(pes[0], pes[1], 0.3) + v2(0.04 * S, 0.02 * S), pes[2] + v2(0.03 * S, 0.02 * S),
                            pes[3] + v2(0.02 * S, 0.03 * S)], [0.05 * S, 0.04 * S, 0.03 * S])
        tela.pintar(pm & tela.mascara(), bar, linha_interna=False)
        for k in range(4):
            p = lerp(pes[0], pes[3], k / 4) + v2(-0.05 * S, -0.04 * S)
            tela.pintar(tela.poly([p + v2(-0.02 * S, 0.02 * S), p + v2(0.02 * S, 0.02 * S), p + v2(-0.03 * S, -0.05 * S)]), bar.escuro(1))
        self.cabeca(tela, ctx, P)
        # pernas da frente (lado de cá)
        tras, frente = P["pernas"]["f"]
        perna_articulada(tela, tras, [0.1 * S, 0.065 * S, 0.04 * S, 0.035 * S], esc)
        perna_articulada(tela, frente, [0.065 * S, 0.05 * S, 0.035 * S], esc)
        for L in (tras, frente):
            pe = L[-1]
            for k in range(3):
                tela.px(pe[0] + 0.04 * S + k * 0.02 * S, pe[1] - 0.5, OSSO[4])
        # asa da frente
        self.desenhar_asa(tela, P, asa, lado=1)
        if P["fogo"]:
            self.sopro(tela, ctx, P)
        if ctx.anim == "morte" and ctx.i >= 2:
            cx, chao = self.ancora
            sangue_no_chao(tela, cx + 0.3 * S, chao, S * (0.25 if ctx.i == 2 else 0.4))

    def desenhar_asa(self, tela, P, mat, lado):
        S = self.S
        o = P["ombro_asa"] + v2(-0.04 * S * (1 if lado < 0 else 0), -0.02 * S * (1 if lado < 0 else 0))
        a = P["asa"]
        esc = 1.0 if lado > 0 else 0.85
        cot = o + v2(-0.12 * S, -0.3 * S - a * 0.15 * S) * esc
        pulso = cot + v2(-0.3 * S, -0.18 * S - a * 0.2 * S) * esc
        dedos = [pulso + v2(-0.35 * S, 0.12 * S + a * 0.1 * S) * esc, pulso + v2(-0.2 * S, 0.32 * S + a * 0.12 * S) * esc,
                 pulso + v2(0.02 * S, 0.42 * S) * esc, cot + v2(0.1 * S, 0.4 * S) * esc]
        mem = [o, cot, pulso, dedos[0]]
        for i in range(len(dedos) - 1):
            mem.append(lerp(dedos[i], dedos[i + 1], 0.5) + v2(0.05 * S, -0.06 * S))
            mem.append(dedos[i + 1])
        mem.append(o + v2(0.05 * S, 0.08 * S))
        m = tela.poly(mem)
        if self.tipo == "osseo":
            # membrana rasgada: furos
            for k in range(4):
                c = lerp(pulso, dedos[k], 0.6) + v2(0.03 * S, 0.0)
                m &= ~tela.elipse(c[0], c[1], 0.05 * S, 0.035 * S)
        tela.pintar(m, mat)
        osso = mat.claro(2) if self.tipo != "osseo" else Mat((196, 190, 176), 5)
        tela.pintar(tela.corrente([o, cot, pulso], [0.035 * S, 0.03 * S, 0.025 * S]), osso)
        for d in dedos:
            tela.pintar(tela.capsula(pulso, d, 0.016 * S, 0.008 * S + 0.3), osso)
        tela.pintar(tela.poly([pulso + v2(-0.02 * S, 0), pulso + v2(0.02 * S, 0), pulso + v2(0.0, -0.07 * S)]), Mat((210, 200, 180), 4))

    def cabeca(self, tela, ctx, P):
        S = self.S
        cab = P["cab"]
        a = P["cab_ang"]
        esc, bar = self.escamas, self.barriga
        R = lambda x, y: cab + girar(v2(x * S, y * S), a)
        boca = P["boca"]
        osseo = self.tipo == "osseo"
        # chifres para trás
        for dy, m in ((0.0, Mat((200, 190, 170), 5).escuro(1)), (0.02, Mat((210, 200, 180), 5))):
            tela.pintar(tela.corrente([R(-0.04, -0.05 + dy), R(-0.14, -0.1 + dy), R(-0.24, -0.06 + dy)], [0.025 * S, 0.016 * S, 0.004 * S + 0.4]), m)
        # crânio
        cr = [R(-0.07, -0.06), R(0.05, -0.08), R(0.2, -0.04), R(0.26, 0.0), R(0.25, 0.03), R(0.06, 0.03), R(-0.06, 0.05)]
        tela.pintar(tela.poly(cr), esc if not osseo else Mat((196, 190, 176), 6, luz_hue=0.6, satur=0.5))
        # mandíbula
        mand = [R(-0.04, 0.03), R(0.06, 0.03 + boca * 0.04), R(0.23, 0.05 + boca * 0.1), R(0.2, 0.08 + boca * 0.1), R(-0.02, 0.08)]
        tela.pintar(tela.poly(mand), esc.escuro(1) if not osseo else Mat((170, 164, 150), 5))
        if boca > 0.2:
            interior = tela.poly([R(0.04, 0.03), R(0.24, 0.02), R(0.22, 0.05 + boca * 0.09), R(0.04, 0.05)])
            tela.chapado(interior, (60, 10, 14))
            tela.brilho(R(0.2, 0.05), 0.08 * S, self.fogo[2], 0.6)
        for k in range(5):
            p = R(0.08 + k * 0.035, 0.03)
            tela.px(p[0], p[1], OSSO[5])
        # olho
        if not P["morto"]:
            o = R(0.04, -0.03)
            tela.chapado(tela.elipse(o[0], o[1], 0.016 * S, 0.012 * S), self.olho, emite=True)
            tela.px(o[0], o[1], (30, 10, 10), emite=True)
            tela.brilho(o, 0.05 * S, self.olho, 0.5)
        else:
            tela.traco(R(0.02, -0.03), R(0.06, -0.03), (30, 10, 10))
        tela.px(*R(0.24, -0.01), (30, 10, 10))
        # fumaça das narinas (parado)
        if ctx.anim == "parado":
            fx.fumaca(tela, R(0.26, -0.03), 0.02 * S, fase=ctx.a, n=3, sobe=0.12 * S)

    def sopro(self, tela, ctx, P):
        S = self.S
        cab = P["cab"]
        a = P["cab_ang"]
        boca = cab + girar(v2(0.24 * S, 0.05 * S), a)
        d = girar(v2(1, 0), a + 0.15)
        comp = (0.6 if P["fogo"] == 1 else 0.9) * S
        n = v2(-d[1], d[0])
        rng = np.random.default_rng(ctx.i * 7 + P["fogo"])
        cores = self.fogo
        bolas = []
        for i in range(12):
            t = (i + 0.5) / 12
            cen = boca + d * comp * t + n * math.sin(t * 8 + ctx.i * 2) * 0.03 * S * t
            r = (0.025 + 0.11 * t) * S
            bolas.append((cen, r, t))
        for camada, (cor, f) in enumerate(((cores[1], 1.0), (cores[2], 0.72), (cores[3], 0.45), (cores[4], 0.22))):
            for cen, r, t in bolas:
                if camada >= 2 and t > 0.8:
                    continue
                pts = []
                for k in range(12):
                    ang = 2 * math.pi * k / 12
                    rr = r * f * (0.75 + 0.45 * rng.random())
                    pts.append(cen + v2(math.cos(ang), math.sin(ang)) * rr)
                tela.chapado(tela.poly(pts), cor, emite=True)
        for k in range(10):
            t = rng.random()
            q = boca + d * comp * (0.3 + t * 0.8) + n * (rng.random() - 0.5) * 0.3 * S
            tela.px(q[0], q[1], cores[3], emite=True)
        tela.brilho(boca + d * comp * 0.55, comp * 0.42, self.fogo[2], 0.3)
