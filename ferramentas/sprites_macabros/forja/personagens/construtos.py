"""Construtos e engenhocas (objetos animados que não são bichos nem humanoides).

    Torreta        Torreta Rúnica do Artífice: tripé de madeira cintado de ferro, carcaça de latão
                   com runas, engrenagem girando, núcleo de cristal e cano que dispara fogo rúnico
    RelicarioVivo  relicário gótico de ouro que flutua com asas, auréola e um crânio santo na janela
"""
import math

import numpy as np

from ..motor import Mat, metal, v2, lerp, girar
from ..personagens.bestas import Besta
from .. import texturas as T
from .. import fx, armas
from ..criaturas.partes import direcao

MADEIRA_VELHA = Mat((104, 72, 48), 5, relevo=1.0, ruido=0.2)
FERRO = metal((88, 86, 98), ruido=0.2)
LATAO = metal((176, 136, 64), especular=(255, 236, 170))
CRISTAL_RUNICO = Mat((90, 190, 240), 6, relevo=1.3, especular=(240, 255, 255), luz_hue=0.55)
RUNA = (120, 230, 255)


class Torreta(Besta):
    """Torreta rúnica: mira, recua ao disparar, solta faíscas ao apanhar e desmonta ao morrer."""

    geo_rapida = True
    nome = "torreta"
    S = 60

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 1.85), int(S * 1.4)
        self.ancora = (int(S * 0.8), self.alt - 3)

    def pose(self, ctx):
        cx, chao = self.ancora
        S = self.S
        P = dict(recuo=0.0, mira=-0.06, inclina=0.0, cai=0.0, fase=ctx.a, anim=ctx.anim, i=ctx.i, golpe=ctx.golpe,
                 vivo=not (ctx.anim == "morte" and ctx.i >= 1), giro=ctx.a)
        if ctx.anim == "parado":
            P["mira"] = -0.06 + math.sin(ctx.a) * 0.05
        elif ctx.anim == "ataque":
            P["recuo"], P["mira"] = [(0.0, -0.12), (-0.1, -0.1), (-0.05, -0.08), (0.0, -0.06)][ctx.i]
            P["giro"] = ctx.a * 2
        elif ctx.anim == "dano":
            P["inclina"] = [-0.18, -0.07][ctx.i]
        elif ctx.anim == "morte":
            P["inclina"] = [-0.15, 0.25, 0.6, 0.8][ctx.i]
            P["cai"] = [0.0, 0.1, 0.35, 0.5][ctx.i]
            P["mira"] = [-0.1, 0.3, 0.8, 1.1][ctx.i]
        P["cx"], P["chao"] = cx, chao
        P["centro"] = v2(cx, chao - (0.6 - P["cai"] * 0.5) * S)
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao, inc = P["cx"], P["chao"], P["inclina"]
        piv = v2(cx, chao)

        def g(p):
            return girar(p, inc, piv)
        topo = g(P["centro"] + v2(0, 0.14 * S))
        abre = 1 + P["cai"] * 1.6
        for k, dx in enumerate((0.3, -0.34, 0.02)):                      # tripé (a perna do meio fica atrás)
            pe = v2(cx + dx * S * abre, chao - 1)
            mat = MADEIRA_VELHA.escuro(1) if k == 2 else MADEIRA_VELHA
            m = tela.pintar(tela.capsula(topo, pe, 0.035 * S, 0.026 * S), mat)
            T.casca(tela, m, topo, eixo=pe - topo, espaco=3, ondula=0.4, escurece=0.75, fendas=0.02)
            for t in (0.35, 0.7):                                         # cintas de ferro
                c = lerp(topo, pe, t)
                tela.pintar(tela.circulo(c, 0.035 * S), FERRO)
            tela.pintar(tela.poly([pe + v2(-2, -2), pe + v2(2, -2), pe + v2(0, 2)]), FERRO)   # ponteira
        c = g(P["centro"])
        base = tela.elipse_girada(c + v2(0, 0.1 * S), 0.2 * S, 0.06 * S, inc)                 # prato de ferro
        tela.pintar(base, FERRO.escuro(1))
        carcaca = tela.elipse_girada(c, 0.22 * S, 0.16 * S, inc) | tela.poly(
            [c + v2(-0.22 * S, 0.02 * S), c + v2(0.2 * S, 0.02 * S), c + v2(0.16 * S, 0.12 * S), c + v2(-0.18 * S, 0.12 * S)])
        mc = tela.pintar(carcaca, LATAO)
        T.manchas(tela, mc, c, (70, 90, 60), escala=3, quantidade=0.18, forca=0.5)            # azinhavre
        for k in range(5):                                                                     # rebites
            p = c + v2(-0.16 * S + k * 0.08 * S, 0.1 * S)
            tela.px(p[0], p[1], LATAO[-1])
        vivo = P["vivo"]
        cor_runa = RUNA if vivo else (50, 70, 90)
        for k, x in enumerate((-0.12, 0.0, 0.12)):                                            # runas gravadas
            fx.runa(tela, c + v2(x * S, 0.04 * S), cor_runa, 2, forma=k, emite=vivo)
        eng = c + v2(-0.2 * S, -0.02 * S)                                                      # engrenagem girando
        tela.pintar(tela.circulo(eng, 0.075 * S), FERRO.claro(1))
        for k in range(8):
            a = k / 8 * math.tau + P["giro"] * (0.5 if vivo else 0)
            d = eng + direcao(a) * (0.085 * S)
            tela.pintar(tela.circulo(d, 0.022 * S), FERRO.claro(1))
        tela.chapado(tela.circulo(eng, 0.025 * S), (30, 26, 34))
        nucleo = c + v2(0.02 * S, -0.14 * S)                                                   # domo com cristal
        domo = tela.elipse(nucleo[0], nucleo[1], 0.09 * S, 0.075 * S)
        if vivo:
            T.cristal(tela, domo, CRISTAL_RUNICO, nucleo, opacidade=0.75, facetas=2, periodo=6,
                      nucleo=(nucleo, 0.08 * S, RUNA))
            tela.brilho(nucleo, 0.18 * S, RUNA, 0.35 + 0.1 * math.sin(P["fase"] * 2))
        else:
            tela.pintar(domo, Mat((60, 70, 80), 5))
            T.rachaduras(tela, domo, nucleo, area=(2, 2), n=2, passos=3, cor=(30, 30, 40), emite=False)
        d = direcao(P["mira"] + inc)                                                           # cano
        boca_base = c + v2(0.12 * S, -0.03 * S) + d * (P["recuo"] * S)
        boca = boca_base + d * (0.42 * S)
        tela.pintar(tela.capsula(boca_base, boca, 0.065 * S, 0.055 * S), FERRO.claro(1))
        for t in (0.25, 0.6):                                                                  # anéis de latão
            p = lerp(boca_base, boca, t)
            tela.pintar(tela.capsula(p - d * 1.5, p + d * 1.5, 0.075 * S, 0.075 * S), LATAO)
        tela.pintar(tela.circulo(boca, 0.08 * S), LATAO)
        tela.chapado(tela.circulo(boca + d * 1.5, 0.035 * S), (14, 10, 18))
        if vivo:
            fx.runa(tela, lerp(boca_base, boca, 0.43), RUNA, 1, forma=1)
        if P["anim"] == "ataque" and P["i"] in (1, 2):                                       # disparo rúnico
            fx.chama(tela, boca + d * 4, 0.22 * S if P["i"] == 1 else 0.12 * S, 0.14 * S, fx.FOGO_AZUL,
                     fase=P["fase"], inclina=1.6)
            if P["i"] == 1:
                fx.orbe(tela, boca + d * (0.4 * S), 0.06 * S, fx.FOGO_AZUL)
            tela.brilho(boca, 0.25 * S, (140, 210, 255), 0.7)
            fx.fumaca(tela, boca + v2(0, -4), 0.05 * S, cor=(110, 120, 140), fase=P["fase"], n=3, sobe=8)
        elif P["anim"] == "parado" and P["i"] == 2:
            T.particulas(tela, c + v2(-0.15 * S, -0.1 * S), (2, 2), (200, 200, 210), n=3, fase=P["fase"], sobe=6,
                         emite=False)                                                          # vapor
        if P["anim"] == "dano":
            armas.faiscas(tela, c + v2(0.05 * S, -0.05 * S), (255, 220, 120), n=7, raio=0.2 * S, semente=P["i"])
        if P["anim"] == "morte" and P["i"] >= 1:
            fx.fumaca(tela, c + v2(0, -6), 0.08 * S, fase=P["fase"], n=4, sobe=12)
            if P["i"] <= 2:
                armas.faiscas(tela, nucleo, (150, 220, 255), n=6, raio=0.15 * S, semente=P["i"] + 3)


# ============================================================
# RELICÁRIO VIVO (Catacumbas da Ordem Caída)
# ============================================================

OURO = metal((196, 152, 70), especular=(255, 240, 190))
VELUDO = Mat((96, 22, 34), 5, relevo=0.8, ruido=0.2)
OSSO_SANTO = Mat((222, 210, 180), 6, relevo=1.1)
LUZ_SANTA = (255, 236, 170)


class RelicarioVivo(Besta):
    """Relicário gótico que flutua com asas douradas: na janela, um crânio santo que brilha e dispara luz."""

    geo_rapida = True
    nome = "relicario_vivo"
    S = 50
    asa = None

    def __init__(self, **kw):
        super().__init__(**kw)
        from ..criaturas.partes import Asa
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.4), int(S * 1.9)
        self.ancora = (int(S * 0.9), self.alt - 3)
        self.asa = Asa(envergadura=0.62, estilo="penas")

    def pose(self, ctx):
        cx, chao = self.ancora
        S = self.S
        P = dict(fase=ctx.a, anim=ctx.anim, i=ctx.i, inclina=0.0, cai=0.0, avanco=0.0, raio=0.0, racha=False,
                 apagado=False, abertura=[1.0, 0.65, 0.3, 0.65][ctx.i % 4], bater=[-0.35, 0.0, 0.3, 0.0][ctx.i % 4])
        bob = 0.03 * S * math.sin(ctx.a)
        if ctx.anim == "ataque":
            P.update(avanco=[-0.06, 0.04, 0.03, 0.0][ctx.i], raio=[0.0, 1.0, 0.6, 0.0][ctx.i], inclina=[-0.1, 0.05, 0.03, 0][ctx.i])
        elif ctx.anim == "dano":
            P.update(inclina=[-0.25, -0.1][ctx.i], avanco=[-0.08, -0.03][ctx.i], racha=True)
        elif ctx.anim == "morte":
            P.update(inclina=[-0.2, 0.3, 0.55, 0.6][ctx.i], cai=[0.0, 0.25, 0.52, 0.55][ctx.i], racha=True, apagado=ctx.i >= 2,
                     abertura=[0.6, 1.0, 0.8, 0.9][ctx.i], bater=[0.0, -0.6, -1.0, -1.2][ctx.i])
            bob = 0.0
        P["centro"] = v2(cx + P["avanco"] * S, chao - (0.85 - P["cai"]) * S + bob)
        P["cx"], P["chao"] = cx, chao
        return P

    def desenhar(self, tela, ctx, P):
        S = self.S
        c, inc = P["centro"], P["inclina"]

        def g(x, y):
            return girar(c + v2(x * S, y * S), inc, c)
        raiz = g(-0.08, -0.15)
        raiz_la = g(0.12, -0.17)                                           # asa de lá, espelhada para a frente
        asa_la = self.asa.pontos(raiz_la, S, P["abertura"], -P["bater"] - inc)

        def espelhar(p):
            return v2(2 * raiz_la[0] - p[0], p[1])
        asa_la = {k: ([espelhar(q) for q in val] if isinstance(val, list) else espelhar(val) if isinstance(val, np.ndarray) else val)
                  for k, val in asa_la.items()}
        self.asa.desenhar(tela, asa_la, Mat((176, 160, 128), 6, relevo=1.0), S)
        if not P["cai"]:                                                   # correntes com incensários
            for k, x in enumerate((-0.18, 0.18)):
                topo = g(x, 0.2)
                bal = math.sin(P["fase"] + k * 1.7) * 0.06 * S
                fim = topo + v2(bal, 0.3 * S)
                for t in np.linspace(0, 1, 6):
                    p = lerp(topo, fim, t)
                    tela.px(p[0], p[1], OURO[2] if int(t * 5) % 2 else OURO[4])
                tela.pintar(tela.circulo(fim + v2(0, 0.04 * S), 0.045 * S), OURO)
                T.particulas(tela, fim + v2(0, 0.02 * S), (2, 2), (190, 180, 200), n=3, fase=P["fase"] + k, sobe=0.25 * S,
                             emite=False, semente=k)
        caixa = tela.poly([g(-0.24, 0.2), g(0.24, 0.2), g(0.24, -0.16), g(-0.24, -0.16)])          # corpo
        telhado = tela.poly([g(-0.28, -0.14), g(0.28, -0.14), g(0.0, -0.4)])
        base = tela.poly([g(-0.28, 0.18), g(0.28, 0.18), g(0.24, 0.26), g(-0.24, 0.26)])
        m = tela.pintar(caixa | telhado | base, OURO)
        painel = tela.poly([g(-0.2, 0.16), g(0.2, 0.16), g(0.2, -0.12), g(-0.2, -0.12)])
        tela.pintar(painel, VELUDO)
        for x in (-0.26, 0.26, 0.0):                                       # pináculos
            topo = g(x, -0.14 if x else -0.42)
            tela.pintar(tela.circulo(topo + v2(0, -0.03 * S), 0.035 * S), OURO.claro(1))
        cruz = g(0, -0.5)
        tela.traco(cruz + v2(0, -0.06 * S), cruz + v2(0, 0.05 * S), OURO[4])
        tela.traco(cruz + v2(-0.03 * S, -0.02 * S), cruz + v2(0.03 * S, -0.02 * S), OURO[4])
        janela_c = g(0.0, 0.02)                                            # janela em arco com o crânio
        janela = tela.elipse(janela_c[0], janela_c[1], 0.11 * S, 0.13 * S) | tela.poly(
            [janela_c + v2(-0.11 * S, 0), janela_c + v2(0.11 * S, 0), janela_c + v2(0.11 * S, 0.12 * S), janela_c + v2(-0.11 * S, 0.12 * S)])
        tela.chapado(janela, (30, 18, 22))
        tela.pintar(tela.circulo(janela_c + v2(0.01 * S, 0.02 * S), 0.07 * S), OSSO_SANTO)          # crânio
        for dx in (-0.025, 0.035):
            tela.chapado(tela.circulo(janela_c + v2(dx * S, 0.015 * S), 0.018 * S), (20, 10, 12))
            if not P["apagado"]:
                tela.px(janela_c[0] + dx * S, janela_c[1] + 0.015 * S, LUZ_SANTA, emite=True)
        tela.traco(janela_c + v2(-0.02 * S, 0.07 * S), janela_c + v2(0.04 * S, 0.07 * S), (60, 50, 40))
        if not P["apagado"]:
            T.cristal(tela, janela, Mat((220, 220, 180), 5, relevo=0.6), janela_c, opacidade=0.35, facetas=1, periodo=8,
                      nucleo=(janela_c, 0.15 * S, LUZ_SANTA))
            tela.brilho(janela_c, 0.3 * S, LUZ_SANTA, 0.45 + 0.1 * math.sin(P["fase"] * 2))
        if P["racha"]:
            T.rachaduras(tela, janela | m, janela_c, area=(0.12 * S, 0.12 * S), n=3, passos=4, cor=(40, 30, 30), emite=False,
                         semente=P["i"])
        for k in range(3):                                                 # entalhes no ouro
            y = -0.12 + k * 0.14
            tela.traco(g(-0.235, y), g(-0.21, y), OURO[1], sobre=True)
            tela.traco(g(0.21, y), g(0.235, y), OURO[1], sobre=True)
        asa = self.asa.pontos(raiz, S, P["abertura"], P["bater"] + inc)
        self.asa.desenhar(tela, asa, Mat((236, 224, 196), 6, relevo=1.0, especular=(255, 255, 240)), S)
        if not P["cai"]:                                                   # auréola
            aur = g(0.0, -0.62)
            anel = tela.elipse(aur[0], aur[1], 0.17 * S, 0.05 * S) & ~tela.elipse(aur[0], aur[1], 0.12 * S, 0.025 * S)
            tela.chapado(anel, (255, 226, 130), emite=True)
            tela.brilho(aur, 0.2 * S, LUZ_SANTA, 0.4)
        elif P["i"] >= 2:                                                  # pedaços da auréola no chão
            for k in range(3):
                p = v2(P["cx"] + (k - 1) * 0.2 * S + 0.3 * S, P["chao"] - 1)
                tela.traco(p, p + v2(3, -1), (200, 170, 100))
        if P["raio"]:                                                      # raio santo
            d = direcao(inc)
            ini = janela_c + d * (0.12 * S)
            fim = ini + d * (1.2 * S * P["raio"])
            for k, cor in ((-1, (255, 220, 140)), (0, (255, 252, 230)), (1, (255, 220, 140))):
                tela.traco(ini + v2(0, k), fim + v2(0, k), cor, emite=True)
            tela.brilho(lerp(ini, fim, 0.3), 0.35 * S, LUZ_SANTA, 0.6)
            T.particulas(tela, fim, (0.06 * S, 0.06 * S), LUZ_SANTA, n=8, fase=P["fase"], sobe=4)
        if P["anim"] == "dano":
            armas.faiscas(tela, janela_c, (255, 240, 180), n=6, raio=0.2 * S, semente=P["i"])
        if P["anim"] == "morte" and P["i"] >= 2:
            fx.fumaca(tela, c + v2(0, -0.1 * S), 0.08 * S, cor=(90, 84, 96), fase=P["fase"], n=4, sobe=10)
