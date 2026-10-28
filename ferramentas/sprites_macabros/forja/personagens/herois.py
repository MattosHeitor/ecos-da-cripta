"""Heróis jogáveis — versão sombria."""
import math

import numpy as np

from ..motor import Mat, metal, misturar, v2, lerp, dir_ang, norm, Quadro
from ..humanoide import (perna, braco, tronco, pescoco, cabeca_base, olho, manto, capa, capuz, cinto,
                         quadro_tronco, quadro_cabeca, sangue_no_chao, pe)
from ..anim import Modelo
from .. import armas

# ------------------------------------------------------------
# materiais comuns
# ------------------------------------------------------------
PELE = Mat((196, 150, 122), 6, relevo=0.9, dither=0.3)
PELE_PALIDA = Mat((190, 172, 160), 6, relevo=0.9, satur=0.6)
COURO = Mat((92, 60, 42), 5, ruido=0.12)
COURO_ESC = Mat((58, 40, 34), 5, ruido=0.12)
ACO = metal((122, 128, 146))
ACO_ESC = metal((86, 90, 108))
FERRO = metal((96, 92, 98), ruido=0.25)
OURO_VELHO = metal((170, 132, 62), especular=(255, 236, 170))
MALHA = Mat((98, 102, 116), 5, ruido=0.9, dither=0.9, relevo=0.6)
OSSO = Mat((214, 202, 172), 6)
MADEIRA = Mat((96, 66, 44), 5, ruido=0.2)


def morte_extras(tela, modelo, ctx, J, cor=(70, 6, 14), cor2=(110, 14, 24)):
    """Poça de sangue nos últimos quadros da morte."""
    if ctx.anim == "morte" and ctx.i >= 2:
        cx = modelo.ancora[0] + modelo.H * (0.2 if ctx.i == 2 else 0.4)
        sangue_no_chao(tela, cx, modelo.ancora[1] + 1, modelo.H * (0.16 if ctx.i == 2 else 0.34), cor, cor2)


def rosto_mascara(tela, J, capuz_mat, pele, mascara, cor_olho, ponta=0.3, emite=False):
    """Capuz aberto: rosto na sombra, olhos visíveis e pano cobrindo boca e nariz."""
    _, C, face = capuz(tela, J, capuz_mat, ponta=ponta, sombra=(16, 10, 18), larg=0.92)
    h = J["P"]["cabeca"]
    w = h * 0.95 * 0.92
    faixa = tela.poly(C.pts([(w * 0.12, h * 0.2), (w * 0.62, h * 0.18), (w * 0.62, -h * 0.05), (w * 0.15, -h * 0.05)]))
    tela.chapado(faixa & face, pele[1])
    tela.chapado(tela.poly(C.pts([(w * 0.2, h * 0.2), (w * 0.62, h * 0.18), (w * 0.62, h * 0.12), (w * 0.2, h * 0.14)])) & face,
                 pele[0])
    masc = tela.poly(C.pts([(w * 0.05, -h * 0.02), (w * 0.66, -h * 0.05), (w * 0.6, -h * 0.5), (w * 0.08, -h * 0.5)]))
    tela.pintar(masc & tela.mascara(), mascara, linha_interna=False)
    for x in (w * 0.3, w * 0.52):
        p = C.pt(x, h * 0.07)
        tela.px(p[0], p[1], cor_olho, emite=emite)
    return C


def golpe_rastro(tela, ctx, J, raio, a0, a1, cor=(214, 206, 228), centro=None, largura=0.22):
    """Arco do golpe no quadro 1 (e um resto fino no quadro 2)."""
    if ctx.anim != "ataque" or ctx.i not in (1, 2):
        return
    c = J["ombro_f"] if centro is None else centro
    if ctx.i == 1:
        armas.rastro(tela, c, raio * (1 - largura), raio, a0, a1, cor=cor)
    else:
        armas.rastro(tela, c, raio * (1 - largura * 0.35), raio, a1 - 0.6, a1 + 0.35, cor=cor)


# ============================================================
# GUERREIRO — cavaleiro caído de armadura escura
# ============================================================

class Guerreiro(Modelo):
    nome = "guerreiro"
    H = 76
    estilo = "corte"
    base = dict(braco_f=(0.35, 0.55), braco_b=(0.75, 0.9), arma_f=0.55, pe_f=(-0.07, 0), pe_b=(0.09, 0))
    tabardo = Mat((42, 52, 96), 6, desce=0.25, ruido=0.1)
    capa_mat = Mat((30, 30, 52), 6, desce=0.35, ruido=0.08, relevo=0.6, arredonda=0.5)
    aco = ACO

    def pose(self, ctx):
        p = super().pose(ctx)
        if ctx.anim == "ataque":
            p["braco_b"] = (0.6 if ctx.i else 0.9, 1.0)
        return p

    def desenhar(self, tela, ctx, J):
        H = self.H
        aco, aco_e = self.aco, self.aco.escuro(1)
        vento = 0.03 * math.sin(ctx.a) + (0.06 if ctx.golpe else 0)
        capa(tela, J, self.capa_mat, comprimento=0.6, vento=vento, rasgos=6, semente=3)

        # braço de trás (escudo)
        braco(tela, J, "b", MALHA.escuro(1), COURO_ESC, punho=aco_e)
        perna(tela, J, "b", MALHA.escuro(1), aco_e, grossura=1.05, cano=0.6)
        perna(tela, J, "f", MALHA, aco, grossura=1.05, cano=0.6)
        # joelheiras
        for lado, m in (("b", aco_e), ("f", aco)):
            tela.pintar(tela.circulo(J["joelho_" + lado], H * 0.03), m)
            # coxote
            tela.pintar(tela.capsula(J["quadril_" + lado], lerp(J["quadril_" + lado], J["joelho_" + lado], 0.75),
                                     H * 0.05, H * 0.042), m)

        # saia de malha + tabardo rasgado
        Q = quadro_tronco(J)
        saia = tela.poly(Q.pts([(-0.085 * H, 0.02 * H), (0.08 * H, 0.02 * H), (0.1 * H, -0.12 * H),
                                (-0.1 * H, -0.12 * H)]))
        tela.pintar(saia, MALHA)
        tab = Q.pts([(-0.035 * H, 0.04 * H), (0.045 * H, 0.04 * H), (0.05 * H, -0.2 * H), (0.03 * H, -0.17 * H),
                     (0.012 * H, -0.22 * H), (-0.01 * H, -0.18 * H), (-0.04 * H, -0.21 * H)])
        tela.pintar(tela.poly(tab), self.tabardo)

        # peitoral
        m = tronco(tela, J, aco, cintura=0.13, peito=0.19)
        T = J["P"]["tronco"]
        tela.traco(Q.pt(0.025 * H, T * 0.25), Q.pt(0.03 * H, T * 0.85), aco[len(aco.cores) - 1], sobre=True)
        tela.traco(Q.pt(0.015 * H, T * 0.25), Q.pt(0.02 * H, T * 0.85), aco[1], sobre=True)
        # placas da barriga
        for k, y in enumerate((0.2, 0.32)):
            tela.traco(Q.pt(-0.07 * H, T * y), Q.pt(0.075 * H, T * (y + 0.02)), aco[1], sobre=True)
        # tabardo sobre o peito com emblema
        tp = tela.poly(Q.pts([(-0.04 * H, T * 0.02), (0.05 * H, T * 0.02), (0.055 * H, T * 0.7), (-0.045 * H, T * 0.7)]))
        tela.pintar(tp & m, self.tabardo)
        # emblema: espada invertida
        e0, e1 = Q.pt(0.006 * H, T * 0.62), Q.pt(0.006 * H, T * 0.18)
        tela.traco(e0, e1, (170, 160, 150), sobre=True)
        tela.traco(Q.pt(-0.02 * H, T * 0.52), Q.pt(0.032 * H, T * 0.52), (170, 160, 150), sobre=True)
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO, altura=0.0)

        # escudo no braço de trás (na frente do corpo)
        if self.armado:
            mb = J["mao_b"]
            ang_e = 0.15 + J["giro"]
            sm, sc = armas.escudo(tela, mb + v2(1, 3), Mat((40, 46, 78), 6, ruido=0.3), ACO_ESC, larg=9, alt=14,
                                  ang=ang_e)
            # emblema do escudo: caveira estilizada / cruz quebrada
            tela.traco(sc + v2(0, -6), sc + v2(0, 7), (150, 140, 128), sobre=True)
            tela.traco(sc + v2(-4, -2), sc + v2(4, -2), (150, 140, 128), sobre=True)
            tela.px(sc[0] + 1, sc[1] + 2, (90, 10, 18))
            tela.px(sc[0] + 1, sc[1] + 3, (90, 10, 18))

        # gorjal e elmo
        pescoco(tela, J, MALHA, 0.045)
        self.elmo(tela, J, ctx)

        # braço da frente com espada
        mf = J["mao_f"]
        if self.armado:
            armas.espada(tela, mf, J["arma_f"], H * 0.5, ACO.claro(1), OURO_VELHO, COURO_ESC, larg=1.5, pomo=OURO_VELHO,
                         sangue=0.35 if ctx.anim != "parado" else 0.2)
        braco(tela, J, "f", MALHA, COURO_ESC, punho=aco)
        # ombreira grande
        o = J["ombro_f"]
        u = J["u"]
        tela.pintar(tela.elipse_girada(o + u * 1.5 - J["u"] * 0, H * 0.065, H * 0.05, math.atan2(u[1], u[0]) + 1.4), aco)
        tela.pintar(tela.elipse_girada(o - u * 2.5, H * 0.05, H * 0.03, math.atan2(u[1], u[0]) + 1.4), aco_e)

        golpe_rastro(tela, ctx, J, H * 0.74, -1.2, 2.0)
        morte_extras(tela, self, ctx, J)

    def elmo(self, tela, J, ctx):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.9
        pts = [(-w * 0.55, -h * 0.55), (-w * 0.6, h * 0.25), (-w * 0.35, h * 0.58), (w * 0.2, h * 0.6),
               (w * 0.58, h * 0.35), (w * 0.62, -h * 0.1), (w * 0.5, -h * 0.55), (0, -h * 0.62)]
        m = tela.poly(C.pts(pts))
        tela.pintar(m, self.aco)
        # crista
        tela.traco(C.pt(-w * 0.1, h * 0.62), C.pt(w * 0.55, h * 0.3), self.aco[len(self.aco.cores) - 1], sobre=True)
        # fenda do visor
        tela.traco(C.pt(w * 0.05, h * 0.08), C.pt(w * 0.62, h * 0.08), (12, 8, 14))
        tela.traco(C.pt(w * 0.15, h * 0.02), C.pt(w * 0.6, h * 0.02), (30, 24, 34), sobre=True)
        # furos de respiração
        for k in range(3):
            tela.px(*C.pt(w * 0.42, -h * (0.15 + k * 0.12)), (14, 10, 16))
        # pluma rasgada vermelho-escura
        pl = Mat((96, 20, 30), 5, relevo=0.6)
        s = math.sin(2 * math.pi * ctx.i / max(1, ctx.n))
        tela.pintar(tela.corrente([C.pt(-w * 0.1, h * 0.62), C.pt(-w * 0.7, h * 0.7 + s * 0.5),
                                   C.pt(-w * 1.25, h * 0.3 + s), C.pt(-w * 1.5, -h * 0.2 + s)],
                                  [1.6, 1.8, 1.3, 0.7]), pl)


# ============================================================
# PALADINO — penitente de armadura de marfim, coroa de espinhos e incensário
# ============================================================

class Paladino(Modelo):
    nome = "paladino"
    H = 78
    estilo = "corte"
    base = dict(braco_f=(0.3, 0.6), braco_b=(0.55, 0.5), arma_f=0.25, pe_f=(-0.07, 0), pe_b=(0.09, 0))
    marfim = metal((196, 186, 160), especular=(255, 250, 230), contraste=1.1)
    tabardo = Mat((110, 22, 30), 6, desce=0.3, ruido=0.12)
    capa_mat = Mat((168, 156, 136), 6, desce=0.55, ruido=0.12, relevo=0.6, arredonda=0.5)

    def desenhar(self, tela, ctx, J):
        H = self.H
        mf, mfe = self.marfim, self.marfim.escuro(1)
        vento = 0.03 * math.sin(ctx.a) + (0.07 if ctx.golpe else 0)
        # auréola de espinhos atrás da cabeça
        if ctx.anim != "morte" or ctx.i < 2:
            C = quadro_cabeca(J)
            c = C.pt(-1.5, 2)
            r = H * 0.105
            pts = []
            for k in range(24):
                ang = k * math.pi / 12 + ctx.a * 0.05
                rr = r * (1.35 if k % 2 == 0 else 1.0)
                pts.append(c + v2(math.cos(ang), math.sin(ang)) * rr)
            anel = tela.poly(pts) & ~tela.circulo(c, r * 0.78)
            tela.brilho(c, r * 2.2, (255, 200, 110), 0.35 + 0.1 * math.sin(ctx.a))
            tela.pintar(anel, OURO_VELHO, linha_interna=False)
        capa(tela, J, self.capa_mat, comprimento=0.64, vento=vento, rasgos=5, semente=7,
             forro=Mat((90, 16, 24), 5))

        # incensário pendurado no braço de trás
        mb = J["mao_b"]
        osc = math.sin(ctx.a) * 0.35 + (0.6 if ctx.golpe else 0)
        fim = mb + v2(math.sin(osc), math.cos(osc)) * H * 0.2
        tela.tracos([mb, lerp(mb, fim, 0.5) + v2(0.5, 0), fim], (120, 104, 70))
        inc = tela.elipse(fim[0], fim[1] + 2.5, 3, 3.5) | tela.poly([fim + v2(-2, 0), fim + v2(2, 0), fim + v2(0, -2.5)])
        tela.pintar(inc, OURO_VELHO)
        tela.px(fim[0], fim[1] + 3, (255, 160, 60), emite=True)
        tela.brilho(fim + v2(0, 3), 4, (255, 140, 50), 0.6)
        from .. import fx
        fx.fumaca(tela, fim + v2(0, -2), 2.2, fase=ctx.a, n=3, sobe=12)

        braco(tela, J, "b", mfe, COURO_ESC, punho=mfe)
        perna(tela, J, "b", MALHA.escuro(1), mfe, cano=0.62)
        perna(tela, J, "f", MALHA, mf, cano=0.62)
        for lado, m in (("b", mfe), ("f", mf)):
            tela.pintar(tela.capsula(J["quadril_" + lado], lerp(J["quadril_" + lado], J["joelho_" + lado], 0.8),
                                     H * 0.05, H * 0.04), m)
            tela.pintar(tela.circulo(J["joelho_" + lado], H * 0.028), OURO_VELHO)

        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        # tabardo longo e manchado
        tab = Q.pts([(-0.05 * H, 0.05 * H), (0.055 * H, 0.05 * H), (0.065 * H, -0.27 * H), (0.03 * H, -0.24 * H),
                     (0.0, -0.29 * H), (-0.03 * H, -0.25 * H), (-0.055 * H, -0.28 * H)])
        mt = tela.poly(tab)
        tela.pintar(mt, self.tabardo)
        mancha = tela.poly(Q.pts([(-0.06 * H, -0.18 * H), (0.07 * H, -0.16 * H), (0.07 * H, -0.3 * H), (-0.06 * H, -0.3 * H)]))
        tela.escurecer_area(mancha & mt & (tela.ruido_base > -0.3), 0.55)
        m = tronco(tela, J, mf, cintura=0.13, peito=0.2)
        # cruz dourada no peito
        tela.traco(Q.pt(0.008 * H, T * 0.3), Q.pt(0.008 * H, T * 0.82), OURO_VELHO[5], sobre=True)
        tela.traco(Q.pt(-0.03 * H, T * 0.66), Q.pt(0.045 * H, T * 0.66), OURO_VELHO[5], sobre=True)
        tela.traco(Q.pt(-0.07 * H, T * 0.94), Q.pt(0.06 * H, T * 0.94), OURO_VELHO[3], sobre=True)
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO)
        # cordão de contas pendurado
        for k in range(5):
            p = Q.pt(-0.05 * H + k * 0.7, -0.02 * H - k * 1.6)
            tela.px(p[0], p[1], (200, 190, 160))

        pescoco(tela, J, MALHA, 0.045)
        self.elmo(tela, J, ctx)

        mfm = J["mao_f"]
        if self.armado:
            armas.martelo(tela, mfm, J["arma_f"], H * 0.4, MADEIRA, OURO_VELHO, tam=0.62, espinhos=True, mat_esp=FERRO)
        braco(tela, J, "f", MALHA, COURO_ESC, punho=mf)
        o, u = J["ombro_f"], J["u"]
        ang = math.atan2(u[1], u[0]) + 1.4
        tela.pintar(tela.elipse_girada(o + u * 1.5, H * 0.068, H * 0.052, ang), mf)
        tela.pintar(tela.elipse_girada(o + u * 2.5, H * 0.04, H * 0.022, ang), OURO_VELHO, linha_interna=False)
        golpe_rastro(tela, ctx, J, H * 0.66, -1.2, 2.0, cor=(255, 225, 160))
        morte_extras(tela, self, ctx, J)

    def elmo(self, tela, J, ctx):
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.92
        pts = [(-w * 0.55, -h * 0.55), (-w * 0.6, h * 0.3), (-w * 0.25, h * 0.6), (w * 0.3, h * 0.58),
               (w * 0.6, h * 0.25), (w * 0.62, -h * 0.4), (w * 0.4, -h * 0.62), (-w * 0.2, -h * 0.62)]
        tela.pintar(tela.poly(C.pts(pts)), self.marfim)
        # visor em cruz
        tela.traco(C.pt(w * 0.1, h * 0.1), C.pt(w * 0.62, h * 0.1), (14, 8, 12))
        tela.traco(C.pt(w * 0.4, h * 0.38), C.pt(w * 0.4, -h * 0.35), (14, 8, 12))
        tela.traco(C.pt(w * 0.35, h * 0.38), C.pt(w * 0.35, -h * 0.35), (30, 20, 26), sobre=True)
        # coroa de espinhos de ferro
        for k in range(6):
            x = -w * 0.55 + k * w * 0.22
            base = C.pt(x, h * 0.42)
            tela.traco(base, C.pt(x + 1.2, h * 0.42 + 3 + (k % 2)), FERRO[2])
        tela.traco(C.pt(-w * 0.6, h * 0.4), C.pt(w * 0.62, h * 0.4), FERRO[1], sobre=True)
        # lágrima de sangue saindo do visor
        p = C.pt(w * 0.45, -h * 0.05)
        tela.px(p[0], p[1], (130, 16, 26))
        tela.px(p[0], p[1] + 1, (95, 10, 20))


# ============================================================
# BÁRBARO — guerreiro do norte com crânio de lobo e pintura de cinzas
# ============================================================

class Barbaro(Modelo):
    nome = "barbaro"
    H = 80
    arma = "Machado"
    prop = dict(ombros=0.3, l_braco=0.046, l_antebraco=0.04, l_coxa=0.06, l_canela=0.046, quadris=0.18)
    base = dict(braco_f=(0.25, 0.65), braco_b=(-0.15, 0.35), arma_f=0.45, pe_f=(-0.08, 0), pe_b=(0.1, 0))
    pele = Mat((176, 128, 98), 6, relevo=1.1, dither=0.3)
    pelagem = Mat((78, 66, 58), 6, ruido=0.9, dither=0.7, relevo=0.8)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "barbaro_" + self.arma)
        self.estilo = "corte" if self.arma == "Espada" else "pesado"

    def desenhar(self, tela, ctx, J):
        H = self.H
        pele, pe_esc = self.pele, self.pele.escuro(1)
        vento = 0.025 * math.sin(ctx.a) + (0.06 if ctx.golpe else 0)
        # manto de pele de lobo nas costas
        capa(tela, J, self.pelagem, comprimento=0.5, vento=vento, larg=0.18, rasgos=9, semente=11)

        braco(tela, J, "b", pe_esc, pe_esc, grossura=1.0)
        # faixas no antebraço de trás
        tela.pintar(tela.capsula(lerp(J["cotovelo_b"], J["mao_b"], 0.35), J["mao_b"], H * 0.036), COURO_ESC)
        perna(tela, J, "b", COURO_ESC.escuro(1), self.pelagem.escuro(1), cano=0.45, grossura=1.0)
        perna(tela, J, "f", COURO_ESC, self.pelagem, cano=0.45, grossura=1.0)
        # tronco nu, musculoso
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        tronco(tela, J, pele, cintura=0.15, peito=0.23, ombros=0.27)
        sombra = pele[1]
        # peitoral / abdômen
        tela.traco(Q.pt(-0.04 * H, T * 0.68), Q.pt(0.07 * H, T * 0.64), sombra, sobre=True)
        tela.traco(Q.pt(0.012 * H, T * 0.62), Q.pt(0.016 * H, T * 0.2), sombra, sobre=True)
        for y in (0.48, 0.36, 0.25):
            tela.traco(Q.pt(-0.025 * H, T * y), Q.pt(0.05 * H, T * (y + 0.01)), pele[2], sobre=True)
        # pintura de cinzas: mão de sangue no peito + listras
        cinza = (92, 88, 96)
        for k in range(3):
            tela.traco(Q.pt(-0.06 * H + k * 2, T * 0.9), Q.pt(-0.05 * H + k * 2.5, T * 0.72), cinza, sobre=True)
        mao_s = tela.elipse_girada(Q.pt(0.035 * H, T * 0.52), 2.4, 2.0, 0.3)
        tela.chapado(mao_s & (tela.alfa > 0), (110, 18, 24))
        for k in range(3):
            tela.px(*Q.pt(0.025 * H + k * 1.4, T * 0.6), (110, 18, 24))
        # cicatriz
        tela.traco(Q.pt(-0.08 * H, T * 0.45), Q.pt(-0.02 * H, T * 0.32), pele[4], sobre=True)
        # cinto largo e saiote de couro/pelo
        saia = tela.poly(Q.pts([(-0.09 * H, 0.03 * H), (0.085 * H, 0.03 * H), (0.1 * H, -0.15 * H), (0.05 * H, -0.12 * H),
                                (0.02 * H, -0.17 * H), (-0.03 * H, -0.13 * H), (-0.1 * H, -0.16 * H)]))
        tela.pintar(saia, COURO)
        cinto(tela, J, COURO_ESC, fivela=OSSO, larg=0.03)
        # colar de dentes
        for k in range(5):
            p = Q.pt(-0.045 * H + k * 2.2, T * 0.96 - abs(k - 2) * 0.8)
            tela.px(p[0], p[1], OSSO[5])
            tela.px(p[0], p[1] + 1, OSSO[3])

        pescoco(tela, J, pele, 0.05)
        self.cabeca(tela, J, ctx)

        mf = J["mao_f"]
        a = J["arma_f"]
        sangue = ctx.anim != "parado"
        if not self.armado:
            pass
        elif self.arma == "Espada":
            armas.espada(tela, mf, a, H * 0.55, FERRO.claro(1), FERRO, COURO_ESC, larg=2.2, guarda_larg=5,
                         sangue=0.4, pomo=FERRO)
        elif self.arma == "Machado":
            armas.machado(tela, mf, a, H * 0.48, MADEIRA, FERRO, duplo=False, tam=1.25, sangue=True)
        else:
            armas.martelo(tela, mf, a, H * 0.48, MADEIRA, Mat((96, 92, 92), 6, ruido=0.6), tam=1.2)
            # runas e sangue
            d = dir_ang(a)
            c = mf + d * (H * 0.48 - 2.4)
            tela.px(c[0], c[1], (140, 20, 28))
        braco(tela, J, "f", pele, pele, grossura=1.0)
        tela.pintar(tela.capsula(lerp(J["cotovelo_f"], J["mao_f"], 0.35), J["mao_f"], H * 0.04), COURO_ESC)
        tela.pintar(tela.circulo(J["mao_f"], H * 0.032), pele)
        # ombreira de pelo e osso
        o, u = J["ombro_f"], J["u"]
        tela.pintar(tela.elipse_girada(o + u * 1, H * 0.06, H * 0.045, math.atan2(u[1], u[0]) + 1.4), self.pelagem)
        golpe_rastro(tela, ctx, J, H * 0.72, -1.4, 2.0)
        morte_extras(tela, self, ctx, J)

    def cabeca(self, tela, J, ctx):
        H = self.H
        m, C = cabeca_base(tela, J, self.pele)
        h = J["P"]["cabeca"]
        w = h * 0.82
        # barba longa trançada, cinza-avermelhada
        barba = Mat((120, 74, 50), 5, ruido=0.5, dither=0.6)
        tela.pintar(tela.poly(C.pts([(-w * 0.1, -h * 0.05), (w * 0.58, -h * 0.15), (w * 0.5, -h * 0.5), (w * 0.25, -h * 0.95),
                                     (w * 0.05, -h * 0.7), (-w * 0.15, -h * 0.4)])), barba)
        # olho fundo, sobrancelha pesada
        olho(tela, C, w * 0.32, h * 0.02, (230, 220, 200), emite=False)
        tela.traco(C.pt(w * 0.12, h * 0.12), C.pt(w * 0.5, h * 0.1), self.pele[0])
        tela.traco(C.pt(w * 0.18, -h * 0.02), C.pt(w * 0.48, h * 0.02), (40, 36, 44), sobre=True)
        # crânio de lobo sobre a cabeça
        cr = C.pts([(-w * 0.62, h * 0.0), (-w * 0.55, h * 0.55), (-w * 0.1, h * 0.72), (w * 0.45, h * 0.58), (w * 0.95, h * 0.38),
                    (w * 1.05, h * 0.18), (w * 0.62, h * 0.15), (w * 0.2, h * 0.2), (-w * 0.3, h * 0.1)])
        tela.pintar(tela.poly(cr), OSSO)
        tela.px(*C.pt(w * 0.42, h * 0.38), (20, 10, 14))
        tela.px(*C.pt(w * 0.48, h * 0.38), (20, 10, 14))
        for k in range(3):
            p = C.pt(w * (0.65 + k * 0.13), h * 0.15)
            tela.px(p[0], p[1] - 0.0, OSSO[5])
            tela.px(p[0], p[1] + 1, OSSO[4])
        # orelhas
        tela.pintar(tela.poly(C.pts([(-w * 0.25, h * 0.6), (-w * 0.05, h * 1.0), (w * 0.1, h * 0.62)])), self.pelagem)
        # pelo caindo atrás da cabeça
        tela.pintar(tela.poly(C.pts([(-w * 0.62, h * 0.3), (-w * 0.95, -h * 0.4), (-w * 0.8, -h * 1.1), (-w * 0.3, -h * 0.6),
                                     (-w * 0.4, h * 0.1)])), self.pelagem)


# ============================================================
# MAGO — feiticeiro encapuzado; elemento muda manto e cajado
# ============================================================

# estilo = qual efeito de magia usar (Fogo, Gelo ou Raio); paleta = cores do efeito (fx.py)
ELEMENTOS = {
    "Fogo": dict(manto=(92, 22, 24), forro=(28, 18, 22), luz=None, olhos=(255, 170, 60)),
    "Gelo": dict(manto=(150, 172, 196), forro=(44, 58, 86), luz=None, olhos=(170, 235, 255)),
    "Raio": dict(manto=(40, 36, 92), forro=(18, 16, 40), luz=None, olhos=(255, 240, 140)),
    # roupas das subclasses e especializações (fase 2)
    "Morte": dict(manto=(34, 44, 36), forro=(160, 150, 130), olhos=(120, 255, 140), estilo="Raio", paleta="FOGO_VERDE"),
    "Cinzas": dict(manto=(46, 40, 40), forro=(150, 60, 24), olhos=(255, 140, 50), estilo="Fogo", paleta="FOGO"),
    "Inverno": dict(manto=(214, 226, 236), forro=(70, 110, 160), olhos=(210, 250, 255), estilo="Gelo", paleta="GELO"),
    "Runas": dict(manto=(60, 72, 96), forro=(170, 130, 60), olhos=(150, 200, 255), estilo="Raio", paleta="FOGO_AZUL"),
    "Sangue": dict(manto=(70, 10, 16), forro=(20, 8, 12), olhos=(255, 60, 60), estilo="Fogo", paleta="FOGO"),
    "Lich": dict(manto=(146, 168, 156), forro=(50, 70, 64), olhos=(120, 240, 230), estilo="Gelo", paleta="GELO"),
}


class MagoElemental(Modelo):
    nome = "mago_Fogo"
    H = 76
    elemento = "Fogo"
    estilo = "magia"
    base = dict(braco_f=(0.7, 0.75), braco_b=(0.15, 0.6), arma_f=0.05, pe_f=(-0.06, 0), pe_b=(0.07, 0))
    prop = dict(ombros=0.22)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "mago_" + self.elemento)
        e = ELEMENTOS[self.elemento]
        self.manto = Mat(e["manto"], 6, desce=0.45, ruido=0.12, relevo=0.7, arredonda=0.6)
        self.forro = Mat(e["forro"], 5, relevo=0.6)
        from .. import fx
        self.estilo_magia = e.get("estilo", self.elemento)
        self.cores = getattr(fx, e.get("paleta", {"Fogo": "FOGO", "Gelo": "GELO", "Raio": "RAIO"}.get(self.elemento, "RAIO")))
        self.olhos = e["olhos"]

    def desenhar(self, tela, ctx, J):
        from .. import fx
        H = self.H
        mt = self.manto
        vento = 0.03 * math.sin(ctx.a) + (0.05 if ctx.golpe else 0)
        capa(tela, J, mt.escuro(2), comprimento=0.66, vento=vento, larg=0.15, rasgos=7, semente=5)
        # braço de trás em manga larga
        self.manga(tela, J, "b", mt.escuro(1))
        perna(tela, J, "b", COURO_ESC, COURO_ESC.escuro(1), cano=0.5)
        perna(tela, J, "f", COURO_ESC, COURO_ESC, cano=0.5)
        mm = manto(tela, J, mt, folga=0.07, rasgos=6, semente=9, barra=-0.005)
        # faixa central escura e runas na barra
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        faixa = tela.poly(Q.pts([(-0.0 * H, T * 0.95), (0.04 * H, T * 0.95), (0.06 * H, -0.42 * H), (0.0, -0.42 * H)]))
        tela.pintar(faixa & mm, mt.escuro(2), linha_interna=False)
        # brasas/geada/faíscas subindo da barra
        for k in range(3):
            t = ((ctx.i / 4) + k / 3) % 1
            p = lerp(J["tornozelo_f"], J["tornozelo_b"], 0.2 + k * 0.3) + J["u"] * (3 + t * 14) + v2(math.sin(t * 6 + k), 0)
            if tela.alfa[int(min(tela.h - 1, max(0, p[1]))), int(min(tela.w - 1, max(0, p[0])))] == 0:
                tela.px(p[0], p[1], self.cores[3 - int(t * 2)], emite=True)
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO, altura=0.02)
        # bolsinhas e crânio pendurado na cintura
        p = Q.pt(-0.06 * H, -0.02 * H)
        tela.pintar(tela.circulo(p + v2(0, 3), 2.2), OSSO)
        tela.px(p[0] - 0.5, p[1] + 3, (20, 10, 14))
        tela.px(p[0] + 1, p[1] + 3, (20, 10, 14))
        # gola alta
        tela.pintar(tela.poly([J["ombro_f"] - J["u"] * 1, J["pescoco"] + J["u"] * 3 - v2(1, 0),
                               J["ombro_b"] - J["u"] * 1]), mt)
        # capuz
        _, C, face = capuz(tela, J, mt, ponta=0.55)
        h = J["P"]["cabeca"]
        w = h * 0.95
        brilho = 0.75 + 0.25 * math.sin(ctx.a)
        for x in (w * 0.28, w * 0.5):
            p = C.pt(x, h * 0.02)
            tela.px(p[0], p[1], self.olhos, emite=True)
        tela.brilho(C.pt(w * 0.4, 0), 4, self.olhos, 0.5 * brilho, halo=False)
        # queixo pálido e boca
        tela.px(*C.pt(w * 0.45, -h * 0.35), (60, 50, 56))

        # cajado
        mf = J["mao_f"]
        if self.armado:
            topo = armas.cajado(tela, mf, J["arma_f"], H * 0.38, MADEIRA, atras=H * 0.5, torto=1.2)
            self.foco(tela, topo, ctx, J)
        self.manga(tela, J, "f", mt)
        # magia na mão de trás no ataque
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            c = J["mao_b"] + dir_ang(J["giro"] + math.pi / 2) * 6
            if self.estilo_magia == "Fogo":
                fx.chama(tela, c + v2(3, 4), 12 if ctx.i == 1 else 9, 9, self.cores, fase=ctx.a, inclina=0.8)
                fx.orbe(tela, c + v2(5, -2), 3.5, self.cores)
            elif self.estilo_magia == "Gelo":
                for k in range(3):
                    fx.cristal(tela, c + v2(2, -3 + k * 3), math.pi / 2 + (k - 1) * 0.3, 9 + k * 2, 2.2)
                tela.brilho(c, 10, self.cores[2], 0.6)
            else:
                fx.relampago(tela, c, c + v2(30, -6 + ctx.i * 6), semente=ctx.i, galhos=2, grosso=True)
                fx.orbe(tela, c, 3, self.cores)
        if ctx.anim == "ataque" and ctx.i == 0:
            fx.orbe(tela, J["mao_b"] + v2(1, -2), 2.2, self.cores, 0.7)
        morte_extras(tela, self, ctx, J)

    def manga(self, tela, J, lado, mat):
        H = self.H
        braco(tela, J, lado, mat, None, grossura=1.25)
        c, m = J["cotovelo_" + lado], J["mao_" + lado]
        d = norm(m - c)
        n = v2(-d[1], d[0])
        p0 = lerp(c, m, 0.35)
        boca = m - d * 1
        tela.pintar(tela.poly([p0 + n * 2, boca + n * 4.2 + d * 0.5, boca - n * 4.2 + d * 1.5, p0 - n * 2]), mat)
        tela.pintar(tela.circulo(m + d * 1.2, H * 0.026), PELE_PALIDA)

    def foco(self, tela, topo, ctx, J):
        from .. import fx
        d = dir_ang(J["arma_f"])
        if self.estilo_magia == "Fogo":
            # braseiro de ferro com chamas
            tela.pintar(tela.poly([topo - v2(3, 0), topo + v2(3, 0), topo + v2(4, -5), topo + v2(-4, -5)]) &
                        ~tela.poly([topo + v2(-2, -1), topo + v2(2, -1), topo + v2(3, -5), topo + v2(-3, -5)]), FERRO)
            fx.chama(tela, topo + v2(0, -3), 13 + 2 * math.sin(ctx.a * 2), 9, self.cores, fase=ctx.a * 2)
        elif self.estilo_magia == "Gelo":
            tela.pintar(tela.capsula(topo, topo + d * 3, 1.6), FERRO)
            fx.cristal(tela, topo + d * 2, J["arma_f"], 12, 2.8)
            fx.cristal(tela, topo + d * 3, J["arma_f"] - 0.6, 7, 1.6)
            fx.cristal(tela, topo + d * 3, J["arma_f"] + 0.55, 6, 1.4)
            tela.brilho(topo + d * 7, 9, self.cores[2], 0.45 + 0.15 * math.sin(ctx.a))
        else:
            n = v2(-d[1], d[0])
            garra = [topo, topo + n * 4 + d * 3, topo + n * 3.5 + d * 8]
            garra2 = [topo, topo - n * 4 + d * 3, topo - n * 3.5 + d * 8]
            tela.pintar(tela.corrente(garra, [1.2, 1.0, 0.6]) | tela.corrente(garra2, [1.2, 1.0, 0.6]), OURO_VELHO)
            c = topo + d * 6
            fx.orbe(tela, c, 2.6 + 0.4 * math.sin(ctx.a * 2), self.cores)
            fx.relampago(tela, c, c + n * 8 * math.sin(ctx.a) + d * 6, semente=ctx.i + 3, desvio=2, galhos=0)


class MagoFogo(MagoElemental):
    elemento = "Fogo"


class MagoGelo(MagoElemental):
    elemento = "Gelo"


class MagoRaio(MagoElemental):
    elemento = "Raio"


# ============================================================
# ARQUEIRA — caçadora encapuzada de capa de musgo
# ============================================================

class Arqueira(Modelo):
    nome = "arqueira"
    H = 74
    estilo = "arco"
    prop = dict(ombros=0.22, quadris=0.18, l_coxa=0.048, l_canela=0.036, l_braco=0.03, l_antebraco=0.027)
    base = dict(braco_f=(0.15, 0.3), braco_b=(0.25, 0.15), arma_b=0.0, arma_f=0.0, pe_f=(-0.06, 0), pe_b=(0.08, 0))
    verde = Mat((52, 70, 46), 6, desce=0.3, ruido=0.15)
    capa_mat = Mat((40, 52, 38), 6, desce=0.4, ruido=0.2, relevo=0.6, arredonda=0.5)

    def pose(self, ctx):
        p = super().pose(ctx)
        if ctx.anim == "morte":
            p["arma_b"] = p.get("arma_f", 0)
        return p

    def desenhar(self, tela, ctx, J):
        H = self.H
        vento = 0.03 * math.sin(ctx.a)
        # aljava nas costas
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        a0 = Q.pt(-0.07 * H, T * 1.15)
        a1 = Q.pt(-0.02 * H, T * 0.2)
        for k in range(4):
            pf = a0 + v2(-2 + k * 1.6, -1 - (k % 2))
            tela.traco(pf, pf + (a1 - a0) * 0.3, (60, 46, 36))
            tela.px(pf[0], pf[1] - 1, (120, 20, 26))
            tela.px(pf[0] + 1, pf[1] - 1, (90, 14, 22))
        tela.pintar(tela.capsula(a0, a1, 2.4, 2.0), COURO)
        capa(tela, J, self.capa_mat, comprimento=0.55, vento=vento, larg=0.14, rasgos=7, semente=13)
        # arco (braço de trás) — fica atrás do corpo quando parado
        mb = J["mao_b"]
        d = dir_ang(math.pi / 2 + J["arma_b"])
        puxa = 0.0
        if ctx.anim == "ataque" and ctx.i in (0, 1):
            puxa = max(0.0, float(np.dot(mb - J["mao_f"], d)) - 3)
        flecha = (150, 120, 90) if (ctx.anim == "ataque" and ctx.i in (0, 1)) or ctx.anim == "parado" else None
        braco(tela, J, "b", self.verde.escuro(1), COURO_ESC, punho=COURO_ESC)
        if not self.armado:
            pass
        elif ctx.anim == "parado" or ctx.anim == "dano" or ctx.anim == "morte":
            armas.arco_flecha(tela, mb, math.pi / 2 + J["arma_b"] + (0.35 if ctx.anim == "parado" else 0),
                              H * 0.62, MADEIRA, (190, 180, 160))
        else:
            armas.arco_flecha(tela, mb, math.pi / 2 + J["arma_b"], H * 0.62, MADEIRA, (190, 180, 160), puxa=puxa,
                              flecha=flecha, ponta=FERRO)
        perna(tela, J, "b", self.verde.escuro(1), COURO_ESC.escuro(1), cano=0.7)
        perna(tela, J, "f", self.verde.escuro(1), COURO_ESC, cano=0.7)
        # túnica
        saia = tela.poly(Q.pts([(-0.08 * H, 0.05 * H), (0.075 * H, 0.05 * H), (0.09 * H, -0.12 * H), (0.03 * H, -0.1 * H),
                                (-0.01 * H, -0.14 * H), (-0.09 * H, -0.11 * H)]))
        tela.pintar(saia, self.verde)
        tronco(tela, J, self.verde, cintura=0.11, peito=0.16, ombros=0.2)
        # corselete de couro
        cors = tela.poly(Q.pts([(-0.06 * H, 0.0), (0.06 * H, 0.0), (0.07 * H, T * 0.62), (-0.06 * H, T * 0.62)]))
        tela.pintar(cors & tela.mascara(), COURO_ESC, linha_interna=False)
        for k in range(3):
            tela.traco(Q.pt(0.01 * H, T * (0.15 + k * 0.15)), Q.pt(0.05 * H, T * (0.17 + k * 0.15)), COURO[0], sobre=True)
        # alça da aljava
        tela.traco(Q.pt(-0.07 * H, T * 0.95), Q.pt(0.065 * H, T * 0.1), COURO_ESC[1], sobre=True)
        cinto(tela, J, COURO_ESC, fivela=FERRO)
        pescoco(tela, J, PELE, 0.03)
        # cabeça: trança, capuz aberto, rosto na sombra com máscara de pano
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tr = [C.pt(-w * 0.5, -h * 0.1), C.pt(-w * 0.8, -h * 0.6), C.pt(-w * 0.85, -h * 1.3)]
        tela.pintar(tela.corrente(tr, [1.4, 1.3, 0.9]), Mat((150, 70, 40), 5, ruido=0.5))
        rosto_mascara(tela, J, self.capa_mat, PELE, Mat((66, 46, 40), 5), (220, 235, 210))
        # braço da frente
        braco(tela, J, "f", self.verde, PELE, punho=COURO_ESC)
        if self.armado and ctx.anim == "ataque" and ctx.i == 2:
            # flecha voando
            c = mb + d * 14
            tela.traco(c, c + d * 14, (190, 170, 130), emite=True)
            tela.traco(c - d * 6, c, (120, 110, 140), emite=True)
        morte_extras(tela, self, ctx, J)


# ============================================================
# ASSASSINA — lâmina das sombras, faixa carmim e duas adagas
# ============================================================

class Assassina(Modelo):
    nome = "assassina"
    H = 72
    estilo = "estocada"
    prop = dict(ombros=0.22, quadris=0.17, l_coxa=0.05, l_canela=0.037, l_braco=0.033, l_antebraco=0.029)
    base = dict(braco_f=(0.2, 1.1), braco_b=(0.5, 1.9), arma_f=1.75, arma_b=0.3, pe_f=(-0.1, 0), pe_b=(0.11, 0),
                quadril=(0, 0.045), tronco=0.18, cabeca=-0.05)
    preto = Mat((52, 46, 58), 6, ruido=0.1, satur=0.6)
    carmim = Mat((122, 18, 34), 6, relevo=0.6)

    def desenhar(self, tela, ctx, J):
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        # faixa carmim esvoaçando
        s = math.sin(ctx.a)
        n0 = J["pescoco"] - J["u"] * 2
        f = v2(-J["u"][1], J["u"][0])
        pts = [n0, n0 - f * 8 + v2(0, 2 + s), n0 - f * 16 + v2(0, 5 - s * 1.5), n0 - f * 22 + v2(0, 9 + s * 2)]
        tela.pintar(tela.corrente(pts, [2.0, 1.8, 1.5, 1.0]), self.carmim)
        braco(tela, J, "b", self.preto.escuro(1), self.preto.escuro(1))
        if self.armado:
            armas.adaga(tela, J["mao_b"], J["arma_b"], 11, ACO, COURO_ESC)
        perna(tela, J, "b", self.preto.escuro(1), COURO_ESC.escuro(1), cano=0.6)
        perna(tela, J, "f", self.preto, COURO_ESC, cano=0.6)
        saia = tela.poly(Q.pts([(-0.07 * H, 0.04 * H), (0.07 * H, 0.04 * H), (0.04 * H, -0.18 * H), (-0.02 * H, -0.08 * H),
                                (-0.08 * H, -0.2 * H)]))
        tela.pintar(saia, self.preto.escuro(1))
        tronco(tela, J, self.preto, cintura=0.1, peito=0.15, ombros=0.19)
        # tiras cruzadas e faixa
        tela.traco(Q.pt(-0.06 * H, T * 0.95), Q.pt(0.06 * H, T * 0.15), COURO[1], sobre=True)
        tela.pintar(tela.poly(Q.pts([(-0.07 * H, 0.03 * H), (0.07 * H, 0.03 * H), (0.07 * H, -0.01 * H), (-0.07 * H, -0.01 * H)])),
                    self.carmim)
        # bainhas e frascos de veneno
        p = Q.pt(-0.07 * H, 0.0)
        tela.pintar(tela.capsula(p, p + v2(-2, 8), 1.2), COURO_ESC)
        f2 = Q.pt(0.06 * H, -0.01 * H)
        tela.chapado(tela.circulo(f2 + v2(0, 2), 1.3), (60, 150, 70), emite=True)
        pescoco(tela, J, self.preto, 0.03)
        # capuz e máscara
        rosto_mascara(tela, J, self.preto, PELE_PALIDA, Mat((34, 28, 38), 5), (235, 225, 245), ponta=0.4)
        braco(tela, J, "f", self.preto, self.preto.claro(1))
        if self.armado:
            armas.adaga(tela, J["mao_f"], J["arma_f"], 12, ACO.claro(1), COURO_ESC)
        if ctx.anim == "ataque" and ctx.i == 1:
            d = dir_ang(J["arma_f"])
            c = J["mao_f"] + d * 12
            for k in range(3):
                tela.traco(c - d * (10 + k * 4) + v2(0, k * 2 - 2), c - d * (2 + k * 3) + v2(0, k * 2 - 2),
                           (200, 190, 220), emite=True)
        morte_extras(tela, self, ctx, J)
