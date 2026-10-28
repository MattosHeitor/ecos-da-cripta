"""Humanos controlados pelos ratos (Reino dos Ratos, docs/planos/reino_dos_ratos.md, etapa 3C1).

    HomemBubonico     enorme e inchado, bubões e ratos se mexendo debaixo da pele; na morte, os ratos saem
    MendigoBubonico   magro e curvado num manto de trapos, capuz escuro com olhos amarelados e uma tigela de moedas
    CarrascoBubonico  capuz negro de carrasco, peito nu cheio de bubões, avental de couro e um machado enorme
    FreiraRoida       a Freira Profana (inimigos_b.Bruxa, tipo "freira") roída pelos ratos: hábito mordido,
                      um rato no ombro e velas de fogo verde (ComAcabamento: a classe antiga não muda)

    MedicoDaPesteCorrompido  mini-chefe: sobretudo encerado, chapéu de aba larga, máscara de bico rachada com lentes
                             vermelhas, miasma verde saindo do bico, bisturi e frascos; ratos espiando da barra
    FlautistaCaido           mini-chefe: o caçador de ratos em farrapos coloridos, olhos fundos, chapéu de pena, a
                             flauta na boca, notas no ar e ratos nos ombros e nos pés
    PrisioneiroNaGaiola      (evento) homem magro e doente agarrado às grades de uma gaiola pendurada por uma corrente;
                             um caroço se mexe debaixo da pele (será só a luz?)

Os outros são da forja de monstros (criaturas/monstro.py).
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, lerp
from ..humanoide import quadro_tronco, quadro_cabeca, cabeca_base, capuz, manto
from .. import texturas as T
from .. import fx, armas
from ..criaturas.monstro import ForjaMonstro
from ..criaturas.acabamento import ComAcabamento
from .inimigos_b import Bruxa

PELE_DOENTE = Mat((138, 120, 92), 6, relevo=1.0, ruido=0.2, nivel=-0.08)
BUBAO = Mat((206, 192, 104), 5, relevo=1.2, dither=0.3, nivel=0.08)
INFLAMADO = (150, 62, 58)
TRAPO_SUJO = Mat((76, 66, 54), 5, desce=0.3, ruido=0.28, relevo=0.7)
COURO_VELHO = Mat((86, 58, 40), 5, relevo=0.9, ruido=0.2)
RATO = (70, 62, 60)


def bubao(tela, centro, raio, corpo=None):
    """Um bubão: caroço amarelado com a pele vermelha em volta e um brilho."""
    if corpo is not None:
        tela.tingir(tela.circulo(centro, raio * 1.5) & corpo & ~tela.circulo(centro, raio), INFLAMADO, 0.5)
    tela.pintar(tela.circulo(centro, raio), BUBAO, linha_interna=False)
    tela.px(centro[0] - raio * 0.35, centro[1] - raio * 0.4, (250, 244, 196))


def ratinho(tela, c, olhando=1, fase=0.0):
    """Rato miúdo de silhueta (no ombro da freira, saindo do corpo do bubônico): corpo, cabeça, olho e rabo."""
    tela.chapado(tela.elipse(c[0], c[1], 3.2, 1.8), RATO)
    cabeca = c + v2(3.0 * olhando, -0.5)
    tela.chapado(tela.circulo(cabeca, 1.5), RATO)
    tela.px(cabeca[0] + olhando, cabeca[1] - 0.5, (230, 50, 40), emite=True)
    tela.px(cabeca[0] - olhando * 0.5, cabeca[1] - 2, (170, 110, 116))            # orelha
    rabo = [c - v2(3 * olhando, -0.5), c - v2(5 * olhando, -1.5 + math.sin(fase)), c - v2(7 * olhando, -1)]
    tela.tracos(rabo, (176, 130, 126))


# ============================================================
# HOMEM BUBÔNICO
# ============================================================

class HomemBubonico(ForjaMonstro):
    """Enorme e inchado, peito nu cheio de bubões, um olho leitoso e volumes de rato andando debaixo da pele.
    Na morte a pele estoura e os ratos saem correndo."""
    nome = "homem_bubonico"
    H = 84
    estilo = "pesado"
    semente = 81
    magreza = 1.5
    cabeca_tam = 0.95
    curvado = 0.15
    braco_grosso = (1.1, 1.15)
    pernas_comp = 0.9
    base = {"braco_f": (0.12, 0.3), "braco_b": (-0.05, 0.35)}                     # braços pesados caídos ao lado
    pele = PELE_DOENTE
    calca = Mat((60, 46, 36), 5, relevo=0.8, ruido=0.25, nivel=-0.22)
    rosto = "bubonico"
    olho_cor = None
    garras = False

    BUBOES = ((0.03, 0.72, 0.06), (-0.04, 0.48, 0.045), (0.06, 0.32, 0.05), (-0.03, 0.92, 0.04))   # (x, altura, raio)

    def rosto_bubonico(self, tela, ctx, J):
        """Cabeça inchada, olho leitoso, boca torta babando e um bubão enorme no pescoço."""
        m, C = cabeca_base(tela, J, self.pele, larg=0.6, nariz=True)
        h = J["P"]["cabeca"]
        w = h * 0.9
        tela.chapado(tela.circulo(C.pt(w * 0.34, h * 0.08), max(1.2, h * 0.1)), (214, 216, 200))     # olho leitoso
        tela.px(*C.pt(w * 0.12, h * 0.06), (40, 26, 26))                                            # o outro, fundo
        boca = [C.pt(w * 0.2, -h * 0.26), C.pt(w * 0.42, -h * 0.3), C.pt(w * 0.55, -h * 0.22)]
        tela.tracos(boca, (50, 20, 24))
        if not ctx.morto:
            T.escorrer(tela, tela.circulo(boca[1], h * 0.12) & m, boca[1], (170, 180, 120), densidade=0.5, comp=3,
                       fase=ctx.a, molhado=0.5, semente=self.semente)
        bubao(tela, C.pt(-w * 0.05, -h * 0.55), h * 0.2, m)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        T.manchas(tela, m, J["pelvis"], (130, 110, 96), escala=4, quantidade=0.2, forca=0.6, semente=self.semente)
        for x, y, r in self.BUBOES:
            bubao(tela, Q.pt(x * H, T_ * y), r * H, m)
        if not (ctx.anim == "morte" and ctx.i >= 2):                                   # ratos sob a pele
            for k in range(3):
                t = (ctx.a / (2 * math.pi) + k * 0.37) % 1
                c = Q.pt(H * (0.06 * math.sin(t * 6 + k)), T_ * (0.15 + 0.7 * t))
                volume = tela.elipse(c[0], c[1], H * 0.032, H * 0.02) & m
                tela.pintar(volume, self.pele.claro(1), linha_interna=False)
                tela.traco(c + v2(-H * 0.025, H * 0.02), c + v2(H * 0.025, H * 0.02), self.pele[1], sobre=True)
        cinto = tela.poly(Q.pts([(-H * 0.11, T_ * 0.06), (H * 0.13, T_ * 0.08), (H * 0.13, -T_ * 0.02), (-H * 0.11, -T_ * 0.04)]))
        tela.pintar(cinto & m, COURO_VELHO)
        return m

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        if ctx.anim == "morte" and ctx.i >= 2:                                         # a ninhada saindo
            rng = random.Random(self.semente)
            for k in range(3):
                c = v2(self.ancora[0] + rng.uniform(0.1, 0.6) * self.H, self.ancora[1] - 2 - k % 2)
                ratinho(tela, c, olhando=1 if k % 2 else -1, fase=ctx.a + k)


# ============================================================
# MENDIGO BUBÔNICO
# ============================================================

class MendigoBubonico(ForjaMonstro):
    """Magro e curvado num manto de trapos, capuz escuro com dois olhos amarelados e uma tigela de madeira com moedas."""
    nome = "mendigo_bubonico"
    H = 70
    estilo = "garra"
    semente = 82
    magreza = 0.72
    curvado = 0.45
    pernas_comp = 0.9
    pele = PELE_DOENTE
    roupa = TRAPO_SUJO
    manga = TRAPO_SUJO
    capuz_mat = Mat((60, 52, 44), 5, relevo=0.8, ruido=0.25)
    manto_inteiro = True
    folga_manto = 0.06
    trapos = 5
    rosto = "vazio"
    olho_cor = (220, 206, 130)
    garras = False

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        T.manchas(tela, m, J["pelvis"], (50, 44, 34), escala=3, quantidade=0.3, forca=0.6, semente=self.semente)
        return m

    def arma(self, tela, ctx, J):
        """A tigela de madeira com umas moedas (no ataque ele bate com ela)."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        c = J["mao_f"] + v2(H * 0.02, -H * 0.01)
        tigela = tela.elipse(c[0], c[1], H * 0.06, H * 0.035) & ~tela.poly([c + v2(-H, -H), c + v2(H, -H), c + v2(H, -1), c + v2(-H, -1)])
        tela.pintar(tigela, Mat((110, 78, 50), 5, relevo=1.0))
        for k in range(2):
            tela.px(c[0] - 1 + k * 2, c[1] - 1, (220, 186, 90))
        bubao(tela, J["mao_f"] + v2(-H * 0.03, H * 0.0), H * 0.018)


# ============================================================
# CARRASCO BUBÔNICO
# ============================================================

class CarrascoBubonico(ForjaMonstro):
    """Capuz negro de carrasco com os olhos amarelos nos furos, peito nu cheio de bubões, avental de couro e um
    machado enorme sujo de sangue."""
    nome = "carrasco_bubonico"
    H = 92
    estilo = "pesado"
    semente = 83
    magreza = 1.4
    braco_grosso = (1.3, 1.4)
    curvado = 0.08
    pele = Mat((146, 116, 94), 6, relevo=1.0, ruido=0.15, nivel=-0.06)
    calca = Mat((44, 36, 34), 5, relevo=0.8, ruido=0.2)
    bota = COURO_VELHO
    rosto = "carrasco"
    olho_cor = (230, 210, 90)
    garras = False
    CAPUZ = Mat((28, 24, 28), 6, relevo=0.8, ruido=0.12)
    LAMINA = metal((150, 150, 156), ruido=0.3, especular=(230, 230, 240))
    CABO = Mat((80, 56, 38), 5, relevo=1.0)

    def rosto_carrasco(self, tela, ctx, J):
        """Capuz fechado e pontudo; dois furos com os olhos amarelos lá dentro."""
        _, C, _ = capuz(tela, J, self.CAPUZ, ponta=0.7, aberto=False, larg=1.05)
        h = J["P"]["cabeca"]
        w = h * 0.9
        for x in (w * 0.24, w * 0.48):
            furo = C.pt(x, h * 0.1)
            tela.chapado(tela.elipse(furo[0], furo[1], max(1.4, w * 0.1), max(1.0, h * 0.07)), (6, 4, 6))
            if not ctx.morto:
                tela.px(furo[0], furo[1], self.olho_cor, emite=True)
                tela.brilho(furo, 2.5, self.olho_cor, 0.5)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        avental = tela.poly(Q.pts([(-H * 0.05, T_ * 0.55), (H * 0.09, T_ * 0.55), (H * 0.11, -T_ * 0.45), (-H * 0.06, -T_ * 0.48)]))
        mav = tela.pintar(avental, COURO_VELHO)
        T.manchas(tela, mav, J["pelvis"], (100, 20, 26), escala=3, quantidade=0.3, forca=0.75, semente=self.semente)
        tela.traco(Q.pt(-H * 0.05, T_ * 0.55), Q.pt(-H * 0.09, T_ * 0.95), COURO_VELHO[1], sobre=True)       # alça
        for x, y, r in ((0.03, 0.85, 0.035), (-0.05, 0.75, 0.03), (0.07, 0.68, 0.028)):
            bubao(tela, Q.pt(x * H, T_ * y), r * H, m)
        return m

    def arma(self, tela, ctx, J):
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        armas.machado(tela, J["mao_f"], J["arma_f"], self.H * 0.42, self.CABO, self.LAMINA, tam=1.5, sangue=True)


# ============================================================
# MINI-CHEFES (etapa 3C2)
# ============================================================

class MedicoDaPesteCorrompido(ForjaMonstro):
    """Alto, sobretudo encerado verde-escuro, luvas de couro, chapéu de aba larga e a máscara de bico rachada com
    lentes vermelhas; um miasma verde escorre do bico. Bisturi na mão, frascos no cinto e ratos espiando da barra."""
    nome = "medico_da_peste_corrompido"
    H = 90
    estilo = "estocada"
    semente = 84
    magreza = 0.95
    curvado = 0.12
    braco_longo = 1.1
    pele = Mat((58, 44, 36), 5, relevo=1.0, ruido=0.12)                                  # as luvas
    roupa = Mat((40, 48, 40), 6, desce=0.35, ruido=0.1, relevo=0.9, especular=(96, 118, 96))
    manga = Mat((36, 44, 36), 6, ruido=0.1, relevo=0.9)
    manto_inteiro = True
    folga_manto = 0.08
    rosto = "bico"
    olho_cor = (255, 60, 50)
    garras = False
    CHAPEU = Mat((30, 28, 30), 6, relevo=0.8, ruido=0.1)
    BICO = Mat((118, 96, 66), 6, relevo=1.1, ruido=0.2)
    MIASMA = (120, 200, 90)

    def rosto_bico(self, tela, ctx, J):
        """Cabeça coberta de couro, lentes redondas acesas, o bico comprido e o chapéu de aba larga."""
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.9
        tela.pintar(tela.elipse_girada(C.pt(w * 0.2, -h * 0.05), w * 0.62, h * 0.6, math.atan2(J["hu"][1], J["hu"][0])),
                    self.CHAPEU.claro(1))                                                  # capuz de couro
        bico = tela.poly(C.pts([(w * 0.42, h * 0.05), (w * 1.0, -h * 0.25), (w * 1.55, -h * 0.75), (w * 0.95, -h * 0.5),
                                (w * 0.42, -h * 0.38)]))
        mb = tela.pintar(bico, self.BICO)
        tela.traco(C.pt(w * 0.6, -h * 0.05), C.pt(w * 1.3, -h * 0.55), self.BICO[1], sobre=True)    # costura
        tela.traco(C.pt(w * 0.95, -h * 0.25), C.pt(w * 1.05, -h * 0.45), (60, 50, 40), sobre=True)   # rachadura
        ponta = C.pt(w * 1.5, -h * 0.72)
        if not ctx.morto:
            T.escorrer(tela, tela.circulo(ponta, h * 0.15) & mb, ponta, self.MIASMA, densidade=0.6, comp=3, fase=ctx.a,
                       molhado=0.5, semente=self.semente)
            T.particulas(tela, ponta, (h * 0.3, h * 0.2), self.MIASMA, n=4, fase=ctx.a, sobe=h * 0.6, semente=3)
        for x in (w * 0.2, w * 0.45):                                                       # as lentes
            c = C.pt(x, h * 0.1)
            tela.pintar(tela.circulo(c, h * 0.13), metal((150, 120, 60)))
            tela.chapado(tela.circulo(c, h * 0.08), (40, 6, 8))
            if not ctx.morto:
                tela.px(c[0], c[1], self.olho_cor, emite=True)
                tela.brilho(c, 3, self.olho_cor, 0.6)
        aba = tela.elipse_girada(C.pt(w * 0.15, h * 0.42), w * 1.05, h * 0.13,
                                 math.atan2(J["hu"][1], J["hu"][0]) + math.pi / 2 + 0.1)
        tela.pintar(aba, self.CHAPEU)                                                      # aba larga
        copa = tela.poly(C.pts([(-w * 0.35, h * 0.45), (w * 0.55, h * 0.45), (w * 0.45, h * 1.05), (-w * 0.3, h * 1.0)]))
        tela.pintar(copa, self.CHAPEU)
        tela.traco(C.pt(-w * 0.33, h * 0.55), C.pt(w * 0.52, h * 0.55), (90, 70, 40), sobre=True)   # fita

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        tela.pintar(tela.capsula(Q.pt(-H * 0.09, T_ * 0.12), Q.pt(H * 0.1, T_ * 0.14), H * 0.016), COURO_VELHO)
        for k, cor in enumerate(((120, 200, 90), (190, 60, 50), (120, 200, 90))):       # frascos no cinto
            p = Q.pt((-0.05 + k * 0.05) * H, T_ * 0.06)
            tela.pintar(tela.capsula(p, p + v2(0, H * 0.04), H * 0.014), Mat(cor, 5, relevo=1.2))
        return m

    def arma(self, tela, ctx, J):
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        armas.adaga(tela, J["mao_f"], J["arma_f"], self.H * 0.12, metal((200, 204, 214), especular=(255, 255, 255)),
                    Mat((40, 36, 34), 4), larg=0.8)
        if ctx.golpe:
            armas.rastro(tela, J["ombro_f"], self.H * 0.25, self.H * 0.36, -1.0, 0.6, cor=(220, 236, 220))

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        if not (ctx.anim == "morte" and ctx.i >= 2):
            ratinho(tela, v2(self.ancora[0] - self.H * 0.12, self.ancora[1] - 2), olhando=-1, fase=ctx.a)


class FlautistaCaido(ForjaMonstro):
    """O caçador de ratos que caiu: farrapos coloridos e desbotados (vermelho e mostarda), rosto magro de olhos fundos,
    chapéu pontudo com uma pena, a flauta de osso na boca, notas no ar e ratos no ombro e nos pés."""
    nome = "flautista_caido"
    H = 84
    estilo = "magia"
    semente = 85
    magreza = 0.85
    curvado = 0.18
    pele = Mat((170, 158, 146), 6, relevo=1.0, ruido=0.12)
    roupa = Mat((96, 40, 40), 5, desce=0.3, ruido=0.25, relevo=0.8)
    manga = Mat((132, 108, 60), 5, ruido=0.25, relevo=0.8)
    calca = Mat((60, 50, 44), 5, relevo=0.8, ruido=0.2)
    bota = COURO_VELHO
    manto_inteiro = False
    trapos = 3
    rosto = "flautista"
    olho_cor = (150, 230, 120)
    garras = False
    OSSO = Mat((226, 214, 186), 5, relevo=1.1)
    NOTA = (226, 170, 255)

    def rosto_flautista(self, tela, ctx, J):
        """Rosto magro, olhos fundos com um brilho verde, a flauta na boca e o chapéu pontudo com pena."""
        m, C = cabeca_base(tela, J, self.pele, larg=0.48, nariz=True)
        h = J["P"]["cabeca"]
        w = h * 0.85
        for x in (w * 0.24, w * 0.46):                                                     # olhos fundos
            c = C.pt(x, h * 0.08)
            tela.chapado(tela.circulo(c, max(1.2, h * 0.09)), (30, 20, 24))
            if not ctx.morto:
                tela.px(c[0], c[1], self.olho_cor, emite=True)
        boca = C.pt(w * 0.5, -h * 0.28)
        fim = J["mao_f"] if not (ctx.anim == "morte" and ctx.i >= 2) else boca + v2(self.H * 0.2, self.H * 0.1)
        tela.pintar(tela.capsula(boca, fim, max(0.8, h * 0.035), max(0.7, h * 0.03)), self.OSSO)   # a flauta, da boca à mão
        for t in (0.35, 0.5, 0.65, 0.8):
            p = lerp(boca, fim, t)
            tela.px(p[0], p[1], self.OSSO[1])
        chapeu = tela.poly(C.pts([(-w * 0.6, h * 0.35), (w * 0.62, h * 0.4), (w * 0.1, h * 0.75), (-w * 0.9, h * 1.35)]))
        tela.pintar(chapeu, self.roupa.escuro(1))
        base = C.pt(-w * 0.3, h * 0.6)
        pena = [base, base + v2(-h * 0.4, -h * 0.5 + math.sin(ctx.a) * 0.6), base + v2(-h * 0.9, -h * 0.75)]
        tela.tracos(pena, (230, 210, 120))

    def corpo(self, tela, ctx, J):
        """Túnica curta: o manto da forja recortado num raio em volta do quadril (vale em qualquer pose)."""
        roupa, self.roupa = self.roupa, None
        m = super().corpo(tela, ctx, J)                                                   # tronco e pescoço
        self.roupa = roupa
        H, Q, T_ = self.H, quadro_tronco(J), J["P"]["tronco"]
        gibao = tela.poly(Q.pts([(-H * 0.08, T_ * 1.0), (H * 0.08, T_ * 0.98), (H * 0.08, T_ * 0.05), (-H * 0.08, T_ * 0.02)]))
        m |= tela.pintar(gibao & m, self.manga)                                          # gibão mostarda
        alcance = float(np.linalg.norm(J["joelho_f"] - J["pelvis"])) * 0.85
        curta = tela.circulo(J["pelvis"], alcance)
        m |= manto(tela, J, self.roupa, folga=0.04, ombros=False, recorte=curta, semente=self.semente) & curta
        for k in range(3):                                                                # remendos
            p = Q.pt(H * (-0.04 + k * 0.04), T_ * (0.75 - k * 0.2))
            tela.chapado(tela.circulo(p, 1.2) & m, (90, 70, 40))
        return m

    def arma(self, tela, ctx, J):
        """Notas da melodia no ar (mais no ataque, quando ele encanta)."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        n = 4 if ctx.golpe else 2
        for k in range(n):
            t = (ctx.i / 4 + k / n) % 1
            p = J["mao_f"] + v2(H * (0.08 + t * 0.3), -H * (0.05 + t * 0.25) + math.sin(t * 6 + k) * 2)
            tela.px(p[0], p[1], self.NOTA, emite=True)
            tela.px(p[0] + 1, p[1] - 1, self.NOTA, emite=True)
            tela.traco(p + v2(1, -1), p + v2(1, -4), self.NOTA, emite=True)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        if not (ctx.anim == "morte" and ctx.i >= 2):
            ratinho(tela, J["ombro_b"] + v2(-1, -4 + math.sin(ctx.a) * 0.5), olhando=1, fase=ctx.a)
            for k, dx in enumerate((0.15, 0.32)):                                          # os que o seguem
                ratinho(tela, v2(self.ancora[0] - self.H * dx, self.ancora[1] - 2), olhando=1, fase=ctx.a + k)


# ============================================================
# EVENTOS (etapa 4A)
# ============================================================

class PrisioneiroNaGaiola(ForjaMonstro):
    """Homem magro e doente numa gaiola de ferro pendurada por uma corrente. As grades de trás ficam atrás dele e as
    da frente por cima; um caroço anda debaixo da pele do braço (o evento deixa a dúvida: é só a luz?)."""
    nome = "prisioneiro_na_gaiola"
    H = 64
    estilo = "garra"
    semente = 86
    magreza = 0.72
    curvado = 0.3
    pele = Mat((156, 138, 120), 6, relevo=1.0, ruido=0.15, nivel=-0.05)
    roupa = TRAPO_SUJO
    manto_inteiro = True
    folga_manto = 0.04
    trapos = 3
    rosto = "prisioneiro"
    olho_cor = None
    garras = False
    FERRO = metal((86, 84, 92), ruido=0.3)

    def gaiola(self):
        """(centro x, topo, chão, raio) da gaiola, em pixels da célula."""
        cx, chao = self.ancora[0] + self.H * 0.02, self.ancora[1] + 1
        return cx, chao - self.H * 1.12, chao, self.H * 0.36

    def atras(self, tela, ctx, J):
        cx, topo, chao, r = self.gaiola()
        tela.traco(v2(cx, 0), v2(cx, topo - r * 0.5), self.FERRO[1])                   # a corrente que segura
        for k in range(4):
            tela.px(cx + (1 if k % 2 else -1), topo - r * 0.5 - k * 4, self.FERRO[3])
        for x in (-0.6, -0.2, 0.2, 0.6):                                                  # grades de trás
            tela.traco(v2(cx + r * x, topo), v2(cx + r * x, chao), self.FERRO.escuro(1)[1])
        tela.pintar(tela.elipse(cx, chao, r * 1.05, 2.2), self.FERRO.escuro(1))       # o fundo da gaiola
        super().atras(tela, ctx, J)

    def rosto_prisioneiro(self, tela, ctx, J):
        """Rosto magro de barba rala, olhos fundos e boca aberta pedindo ajuda."""
        m, C = cabeca_base(tela, J, self.pele, larg=0.48, nariz=True)
        h = J["P"]["cabeca"]
        w = h * 0.85
        for x in (w * 0.24, w * 0.46):
            tela.chapado(tela.circulo(C.pt(x, h * 0.08), max(1.0, h * 0.08)), (40, 28, 30))
        tela.chapado(tela.elipse(C.pt(w * 0.42, -h * 0.26)[0], C.pt(w * 0.42, -h * 0.26)[1], max(1.0, w * 0.08),
                                 max(1.0, h * 0.08 + (1 if ctx.i % 2 else 0))), (40, 16, 20))
        T.manchas(tela, m, J["cabeca"], (90, 80, 70), escala=2, quantidade=0.35, forca=0.6, semente=self.semente)  # barba

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        if not (ctx.anim == "morte" and ctx.i >= 2):                                     # o caroço que anda
            t = (ctx.a / (2 * math.pi)) % 1
            c = lerp(J["ombro_f"], J["cotovelo_f"], 0.3 + 0.5 * t)
            tela.pintar(tela.elipse(c[0], c[1], self.H * 0.022, self.H * 0.014) & corpo, self.pele.claro(1),
                        linha_interna=False)
        cx, topo, chao, r = self.gaiola()
        for x in (-0.95, -0.4, 0.15, 0.7, 1.0):                                           # grades da frente
            tela.traco(v2(cx + r * x * 0.95, topo), v2(cx + r * x * 0.95, chao), self.FERRO[3])
        cupula = [v2(cx + math.cos(a) * r, topo - math.sin(a) * r * 0.5) for a in [i * math.pi / 8 for i in range(9)]]
        tela.tracos(cupula, self.FERRO[3])                                                 # a cúpula
        tela.pintar(tela.capsula(v2(cx - r, chao), v2(cx + r, chao), 1.2), self.FERRO)    # o aro de baixo
        tela.pintar(tela.capsula(v2(cx - r, topo), v2(cx + r, topo), 1.0), self.FERRO)    # o aro de cima


# ============================================================
# FREIRA ROÍDA (a Freira Profana roída pelos ratos)
# ============================================================

class FreiraRoida(ComAcabamento, Bruxa):
    """A Freira Profana de hábito cinza-podre, mordido nas bordas e furado, um rato no ombro, bubões e velas verdes."""

    def __init__(self, **kw):
        super().__init__(tipo="freira", **kw)
        self.nome = "freira_roida"
        self.manto = Mat((62, 56, 50), 6, desce=0.35, ruido=0.2, relevo=0.7, arredonda=0.6)
        self.pele = Mat((176, 168, 150), 6, satur=0.4)
        self.chamas = fx.FOGO_VERDE

    def acabar(self, tela, ctx, J):
        H = self.H
        corpo = tela.alfa > 0
        rng = random.Random(7)
        barra = [lerp(J["tornozelo_b"], J["tornozelo_f"], t) + v2(rng.uniform(-3, 3), rng.uniform(-2, 1)) for t in
                 (-0.4, 0.0, 0.5, 1.0, 1.4)]
        for p in barra:                                                                # mordidas na barra do hábito
            mordida = tela.circulo(p, rng.uniform(1.6, 2.6)) & corpo
            tela.alfa[mordida] = 0
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        for x, y in ((-0.05, 0.3), (0.04, -0.1), (-0.02, -0.3)):                        # furos roídos
            furo = tela.circulo(Q.pt(x * H, T_ * y), 1.4) & corpo
            tela.chapado(furo, (18, 12, 14))
        if self.vivo(ctx):
            ombro = J["ombro_b"] + v2(-1, -4 + math.sin(ctx.a) * 0.5)                   # o rato no ombro
            ratinho(tela, ombro, olhando=1, fase=ctx.a)
            C = quadro_cabeca(J)
            h = J["P"]["cabeca"]
            bubao(tela, C.pt(h * 0.5, -h * 0.35), h * 0.1)
