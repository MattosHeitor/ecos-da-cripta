"""Chefes de destaque feitos com a forja de monstros.

    ForjadorAntigo       Minas de Brasa: autômato anão de bronze e ferro, barba de placas, engrenagens
                         girando, fornalha acesa no peito, chaminé fumegando, martelo rúnico e bigorna
    RainhaDeGeloEterno   Cidadela: rainha de vestes e coroa de gelo cristalino, cabelo branco ao vento,
                         cetro de gelo e uma nevasca girando em volta
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, dir_ang
from ..humanoide import cabeca_base, quadro_cabeca, quadro_tronco
from .. import texturas as T
from .. import fx, armas
from ..criaturas.monstro import ForjaMonstro
from ..criaturas.partes import direcao
from .monstros import estilhaco, NEVE

BRONZE = metal((160, 112, 64), especular=(255, 222, 160), ruido=0.15)
FERRO_VELHO = metal((86, 82, 92), ruido=0.3, especular=(200, 190, 190))
BRASA = (255, 140, 40)


def engrenagem(tela, c, r, fase, mat, dentes=8):
    """Engrenagem com dentes que gira com a fase."""
    tela.pintar(tela.circulo(c, r), mat)
    for k in range(dentes):
        a = k / dentes * 2 * math.pi + fase
        tela.pintar(tela.circulo(c + direcao(a) * (r * 1.1), r * 0.28), mat)
    tela.chapado(tela.circulo(c, r * 0.35), (30, 26, 30))
    tela.px(c[0], c[1], mat[-1])


# ============================================================
# FORJADOR ANTIGO
# ============================================================

class ForjadorAntigo(ForjaMonstro):
    """Autômato anão que ainda forja: corpo de bronze rebitado, barba de placas, olhos de fornalha,
    fornalha no peito com grade e fogo, engrenagens nos ombros, chaminé, martelo rúnico e bigorna."""
    nome = "forjador_antigo"
    H = 129                           # 1,4x o tamanho de um herói grande: chefe
    larg, alt = 295, 283
    ancora = (132, 280)
    estilo = "pesado"
    semente = 101
    pernas_comp = 0.72
    magreza = 1.7
    braco_grosso = (1.35, 1.5)
    cabeca_tam = 1.3
    curvado = 0.1
    barriga = 0.05
    corcunda = 0.04
    pele = BRONZE
    calca = FERRO_VELHO
    bota = FERRO_VELHO.escuro(1)
    rosto = "automato"
    garras = False
    sangue = ((50, 40, 36), (90, 60, 30))
    base = dict(arma_f=2.4, braco_f=(0.4, 0.8), braco_b=(0.2, 0.7))

    def vivo(self, ctx):
        return not (ctx.anim == "morte" and ctx.i >= 2)

    def atras(self, tela, ctx, J):
        H = self.H
        f = self.frente_do_corpo(J)
        base = J["ombro_b"] - f * (H * 0.06)                               # chaminé nas costas
        topo = base + J["u"] * (H * 0.22) - f * (H * 0.03)
        tela.pintar(tela.capsula(base, topo, H * 0.035, H * 0.03), FERRO_VELHO)
        tela.pintar(tela.capsula(topo, topo + J["u"] * 2, H * 0.045, H * 0.045), FERRO_VELHO.claro(1))
        fx.fumaca(tela, topo + J["u"] * 3, H * 0.05, cor=(80, 74, 76), fase=ctx.a, n=5, sobe=H * 0.22)
        if self.vivo(ctx):
            tela.px(topo[0], topo[1] - 2, BRASA, emite=True)
        super().atras(tela, ctx, J)

    def rosto_automato(self, tela, ctx, J):
        """Elmo anão com chifres curtos, viseira com olhos de fornalha e barba de placas de bronze."""
        H = self.H
        m, C = cabeca_base(tela, J, FERRO_VELHO, larg=0.62, nariz=False, orelha=False)
        h = J["P"]["cabeca"]
        w = h * 0.9
        vivo = self.vivo(ctx)
        for x in (w * 0.2, w * 0.45):                                      # olhos de fornalha
            p = C.pt(x, h * 0.06)
            tela.traco(p + v2(-1.5, 0), p + v2(1.5, 0), BRASA if vivo else (60, 40, 30), emite=vivo)
        if vivo:
            tela.brilho(C.pt(w * 0.33, h * 0.06), H * 0.06, BRASA, 0.6)
        for k in range(4):                                                  # rebites do elmo
            tela.px(*C.pt(-w * 0.3 + k * w * 0.25, h * 0.32), FERRO_VELHO[-1])
        for lado in (-1, 1):                                                # chifres curtos
            raiz = C.pt(w * (0.05 + 0.25 * lado), h * 0.45)
            pts = [raiz, raiz + J["hu"] * (h * 0.35) + v2(lado * h * 0.15 - h * 0.1, 0)]
            tela.pintar(tela.corrente(pts + [pts[-1] + v2(-h * 0.15, -h * 0.05)], [h * 0.12, h * 0.07, 0.6]),
                        Mat((200, 186, 160), 5, relevo=1.1))
        hu = J["hu"]
        frente = v2(-hu[1], hu[0])
        queixo = J["queixo"] + frente * (h * 0.15)
        for fila in range(4):                                               # barba de placas
            larg = h * (0.55 - fila * 0.1)
            y = queixo - hu * (h * 0.22 * fila)
            placa = tela.poly([y - frente * larg * 0.6, y + frente * larg * 0.6, y + frente * larg * 0.45 - hu * (h * 0.28),
                               y - frente * larg * 0.45 - hu * (h * 0.28)])
            tela.pintar(placa, BRONZE.claro(1) if fila % 2 else BRONZE.claro(2))
            tela.traco(y - frente * larg * 0.4 - hu * (h * 0.14), y + frente * larg * 0.4 - hu * (h * 0.14), BRONZE[1], sobre=True)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        for k in range(5):                                                  # rebites no peito
            for y in (0.3, 0.9):
                tela.px(*Q.pt(-0.08 * H + k * 0.045 * H, T_ * y), BRONZE[-1])
        c = Q.pt(0.04 * H, T_ * 0.55)                                       # fornalha no peito
        boca = tela.poly([c + v2(-H * 0.06, -H * 0.05), c + v2(H * 0.06, -H * 0.05), c + v2(H * 0.06, H * 0.05),
                          c + v2(-H * 0.06, H * 0.05)])
        vivo = self.vivo(ctx)
        tela.chapado(boca, (40, 14, 8))
        if vivo:
            fx.chama(tela, c + v2(0, H * 0.045), H * 0.09, H * 0.1, fx.FOGO, fase=ctx.a * 2, linguas=3, brilho=False)
            tela.brilho(c, H * 0.3, BRASA, 0.55 + 0.1 * math.sin(ctx.a * 2))
        for k in range(4):                                                  # grade da fornalha
            x = c[0] - H * 0.045 + k * H * 0.03
            tela.traco(v2(x, c[1] - H * 0.05), v2(x, c[1] + H * 0.05), FERRO_VELHO[1])
        tela.pintar(tela.poly([c + v2(-H * 0.07, -H * 0.065), c + v2(H * 0.07, -H * 0.065), c + v2(H * 0.07, -H * 0.05),
                               c + v2(-H * 0.07, -H * 0.05)]), FERRO_VELHO)
        for lado, sinal in (("b", -1), ("f", 1)):                           # engrenagens nos ombros
            engrenagem(tela, J["ombro_" + lado] + J["u"] * 2, H * 0.05, ctx.a * sinal * (1 if vivo else 0),
                       BRONZE.claro(1) if lado == "f" else BRONZE)
        return m

    def arma(self, tela, ctx, J):
        """Martelo de forja com runas que brilham; na pancada, a bigorna solta faíscas."""
        H = self.H
        armas.martelo(tela, J["mao_f"], J["arma_f"], H * 0.5, Mat((96, 66, 44), 5, ruido=0.2), FERRO_VELHO, tam=1.25)
        cabeca = J["mao_f"] + dir_ang(J["arma_f"]) * (H * 0.5 - 3)
        if self.vivo(ctx):
            fx.runa(tela, cabeca, BRASA, 2, forma=3)
        bigorna = v2(self.ancora[0] + H * 0.62, self.ancora[1])
        corpo = tela.poly([bigorna + v2(-H * 0.14, -H * 0.18), bigorna + v2(H * 0.2, -H * 0.18), bigorna + v2(H * 0.1, -H * 0.12),
                           bigorna + v2(H * 0.06, -H * 0.12), bigorna + v2(H * 0.09, 0), bigorna + v2(-H * 0.09, 0),
                           bigorna + v2(-H * 0.05, -H * 0.12), bigorna + v2(-H * 0.12, -H * 0.13)])
        tela.pintar(corpo & (tela.alfa == 0), FERRO_VELHO.escuro(1))
        if ctx.anim == "ataque" and ctx.i == 2:
            armas.faiscas(tela, bigorna + v2(0, -H * 0.2), (255, 220, 120), n=14, raio=H * 0.3, semente=3)
            tela.brilho(bigorna + v2(0, -H * 0.2), H * 0.35, BRASA, 0.6)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        vivo = self.vivo(ctx)
        T.rachaduras(tela, corpo, J["cintura"], area=(H * 0.12, H * 0.2), n=4, passos=3, cor=BRASA if vivo else (70, 50, 40),
                     emite=vivo, brilho=0.2 if vivo else 0.0, semente=102)
        T.manchas(tela, corpo, J["pelvis"], (70, 120, 100), escala=3, quantidade=0.15, forca=0.5, semente=103)  # azinhavre
        if vivo:
            T.particulas(tela, J["peito"], (H * 0.3, H * 0.25), BRASA, n=8, fase=ctx.a, sobe=H * 0.3, semente=104)
            for lado in ("f", "b"):                                         # vapor nas juntas
                T.particulas(tela, J["cotovelo_" + lado], (2, 2), (200, 200, 210), n=2, fase=ctx.a, sobe=H * 0.08,
                             emite=False, semente=105)


# ============================================================
# RAINHA DE GELO ETERNO
# ============================================================

class RainhaDeGeloEterno(ForjaMonstro):
    """Rainha de Gelo Eterno: vestes de gelo cristalino, coroa de pontas de cristal, cabelo branco ao vento,
    olhos de gelo, cetro de gelo eterno e uma nevasca girando em volta dela."""
    nome = "rainha_de_gelo_eterno"
    H = 132                           # 1,4x o tamanho de um herói grande: chefe
    larg, alt = 296, 309
    ancora = (132, 306)
    estilo = "magia"
    semente = 107
    magreza = 0.95
    pele = Mat((198, 222, 240), 6, relevo=1.0, luz_hue=0.55)
    roupa = Mat((122, 172, 222), 6, desce=0.3, ruido=0.1, relevo=0.8, luz_hue=0.55)
    manga = Mat((150, 196, 236), 6, ruido=0.1, relevo=0.8, luz_hue=0.55)
    calca = Mat((122, 172, 222), 6, relevo=0.8)
    manto_inteiro = True
    folga_manto = 0.17
    rosto = "rainha"
    olho_cor = (150, 240, 255)
    garras = False
    sangue = None

    def vivo(self, ctx):
        return not (ctx.anim == "morte" and ctx.i >= 2)

    def atras(self, tela, ctx, J):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        rng = random.Random(self.semente)
        for k in range(9):                                                  # cabelo branco ao vento
            topo = C.pt(-h * 0.4 + k * h * 0.08, h * 0.35)
            comp = H * rng.uniform(0.3, 0.5)
            vento = math.sin(ctx.a + k * 0.6) * 3
            pts = [topo, topo + v2(-H * 0.06 + vento * 0.4, comp * 0.4), topo + v2(-H * 0.14 + vento, comp * 0.8),
                   topo + v2(-H * 0.18 + vento * 1.3, comp)]
            tela.pintar(tela.corrente(pts, [1.6, 1.4, 1.1, 0.6]), Mat((236, 240, 246), 5, relevo=0.6) if k % 2
                        else Mat((206, 218, 232), 5, relevo=0.6))
        super().atras(tela, ctx, J)

    def rosto_rainha(self, tela, ctx, J):
        m, C = cabeca_base(tela, J, self.pele, larg=0.48)
        h = J["P"]["cabeca"]
        w = h * 0.82
        self._olho(tela, C.pt(w * 0.35, h * 0.08), ctx, raio=3.5)
        tela.traco(C.pt(w * 0.2, h * 0.2), C.pt(w * 0.52, h * 0.18), (90, 120, 160), sobre=True)   # sobrancelha
        tela.traco(C.pt(w * 0.3, -h * 0.26), C.pt(w * 0.5, -h * 0.27), (60, 90, 150))                # lábios azuis
        for k, (x, a, c) in enumerate(((-0.45, -2.1, 0.8), (-0.2, -1.85, 1.2), (0.05, -1.6, 1.7), (0.3, -1.35, 1.2),
                                       (0.52, -1.1, 0.8))):              # coroa de cristal
            estilhaco(tela, C.pt(h * x, h * 0.48), a + J["giro"], h * c, h * 0.13, semente=k)

    def arma(self, tela, ctx, J):
        """Cetro de gelo eterno: haste de cristal com uma grande ponta de gelo que brilha."""
        H = self.H
        d = dir_ang(J["arma_f"])
        a, topo = armas.haste(tela, J["mao_f"], J["arma_f"], H * 0.4, H * 0.55, Mat((170, 214, 240), 5, relevo=1.2), larg=1.3)
        ang = math.atan2(d[1], d[0])
        estilhaco(tela, topo, ang, H * 0.18, H * 0.04, semente=9)
        for lado in (-1, 1):
            estilhaco(tela, topo - d * (H * 0.03), ang + lado * 0.6, H * 0.08, H * 0.02, semente=10 + lado)
        if self.vivo(ctx):
            tela.brilho(topo + d * (H * 0.08), H * 0.2, (170, 240, 255), 0.5)
        if ctx.anim == "ataque" and ctx.i in (1, 2):                       # lança de gelo eterno
            f = self.frente_do_corpo(J)
            ponta = J["mao_b"] + f * (H * (0.4 if ctx.i == 1 else 0.8))
            estilhaco(tela, ponta - f * (H * 0.2), math.atan2(f[1], f[0]), H * 0.26, H * 0.04, semente=11)
            T.particulas(tela, ponta, (H * 0.12, H * 0.06), NEVE, n=12, fase=ctx.a, sobe=3, semente=12)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        vivo = self.vivo(ctx)
        vestes = corpo & (np.arange(tela.h)[:, None] > J["peito"][1])
        T.vitrificar(tela, vestes, J["pelvis"], opacidade=0.88, area=(H * 0.2, H * 0.25), semente=108)   # vestes de gelo
        for k in range(5):                                                  # pontas de gelo na barra
            p = v2(self.ancora[0] - H * 0.3 + k * H * 0.15, self.ancora[1] - 2)
            estilhaco(tela, p, -math.pi / 2 + (k - 2) * 0.2, H * 0.08, H * 0.025, semente=20 + k)
        if vivo:                                                            # a nevasca girando em volta
            c = J["peito"] + v2(0, H * 0.1)
            for k in range(3):
                pts = [c + v2(math.cos(t) * H * (0.5 + k * 0.08), math.sin(t) * H * 0.18 - k * H * 0.12)
                       for t in np.linspace(ctx.a + k * 2, ctx.a + k * 2 + 1.6, 7)]
                tela.tracos(pts, (210, 236, 252) if k % 2 else (160, 200, 236))
            for k in range(6):                                              # cacos de gelo orbitando
                a = ctx.a * 0.8 + k * math.pi / 3
                p = c + v2(math.cos(a) * H * 0.55, math.sin(a) * H * 0.16 - H * 0.1)
                estilhaco(tela, p, a * 2, H * 0.05, H * 0.015, semente=30 + k)
            T.particulas(tela, c, (H * 0.7, H * 0.6), NEVE, n=18, fase=ctx.a, sobe=-H * 0.4, emite=False, semente=109)
            T.aura(tela, tela.alfa > 0, (170, 230, 255), raio=5, forca=0.35, fase=ctx.a)
        elif ctx.i >= 2:                                                     # se desfaz em neve
            T.esfumacar(tela, tela.alfa > 0, J["peito"], cor=NEVE, fase=ctx.a, comeu=0.4 + 0.15 * ctx.i, fiapos=12, sobe=12)
