"""Feras feitas com a forja de animais (forja/criaturas/animal.py): lobos e as invocações animais.

    LoboSarnento            Bosque Carmesim: sarnento, costelas à mostra, baba de sangue
    LoboEspectral           invocação: fantasma azul translúcido que se desfaz em névoa
    LoboEspectralSelvagem   Cidadela: espectro de gelo, cristais nas costas e hálito de neve
    TigreEspiritual         familiar do Monge: tigre dourado com listras e chamas de espírito
    MacacoEspiritual        familiar do Monge: macaco de jade que arremessa pedras
    GarcaEspiritual         familiar do Monge: garça de luz com bico que dispara um raio
    Corvo                   familiar: corvo negro-violeta voando
    GatoNegro               familiar: gato preto de olhos amarelos, faíscas de azar
    SalamandraDeLava        Minas de Brasa: lagarto de obsidiana rachado de lava que cospe fogo
    SanguessugaColossal     Pântano: sanguessuga viscosa com ventosa de dentes
    Centopeia               centopeia gigante de carapaça rubra e patas amarelas
    MorcegoGigante          morcego de asas de couro rasgadas, orelhas enormes e presas
"""
import math

import numpy as np

from ..motor import Mat, v2, lerp, girar, misturar
from .. import texturas as T
from .. import fx
from ..criaturas.animal import ForjaAnimal, Quadrupede, Ave, Verme, tabela
from ..criaturas.partes import Pata, Cauda, Asa, Cabeca, Local, direcao

GELO_CRISTAL = Mat((150, 205, 240), 6, relevo=1.4, especular=(255, 255, 255), luz_hue=0.55)
FOGO_DE_ESPIRITO = [(120, 70, 10), (230, 150, 40), (255, 205, 100), (255, 240, 190), (255, 255, 235)]


def arranhoes(tela, origem, ang, comp, cor=(255, 236, 236), cor2=(210, 150, 170), larg=3.0):
    """Três arranhões curvos (golpe de garra)."""
    for k in (-1, 0, 1):
        ini = origem + direcao(ang + math.pi / 2) * (k * larg)
        pts = [ini + direcao(ang - 0.8 + t * 1.2) * (comp * t) for t in np.linspace(0, 1, 6)]
        tela.tracos(pts, cor if k == 0 else cor2, emite=True)
    tela.brilho(origem + direcao(ang) * comp * 0.5, comp * 0.6, cor2, 0.25)


# ============================================================
# LOBOS
# ============================================================

class LoboSarnento(Quadrupede):
    """Lobo magro de pelo falhado, costelas à mostra, olhos vermelhos e baba de sangue."""
    nome = "lobo_sarnento"
    S = 60
    proporcao = (2.35, 1.25)
    pe = 0.52
    mat = Mat((96, 80, 66), 6, relevo=1.15, ruido=0.18, dither=0.4)
    mat_barriga = (158, 132, 108)
    perfil = ((0.0, 0.11, 0.1), (0.45, 0.085, 0.075), (1.0, 0.125, 0.18))
    crina = 1
    pescoco = (0.19, -0.14)
    cabeca = Cabeca(tam=0.15, focinho=0.15, olho_cor=(255, 54, 30))
    semente = 11

    def detalhes(self, tela, ctx, P, corpo):
        S, A, C, cima = self.S, P["A"], P["C"], P["cima"]
        for k in range(3):                                                     # costelas
            p = lerp(A, C, 0.55 + k * 0.1) - cima * (0.01 * S)
            pts = [p, p - cima * (0.05 * S) + v2(-0.015 * S, 0), p - cima * (0.1 * S) + v2(-0.01 * S, 0)]
            for a, b in zip(pts, pts[1:]):
                for x, y in T.bresenham(a, b):
                    if 0 <= x < tela.w and 0 <= y < tela.h and corpo[y, x]:
                        tela.cor[y, x] *= 0.72
                        if x + 1 < tela.w and corpo[y, x + 1]:
                            tela.cor[y, x + 1] = np.minimum(tela.cor[y, x + 1] * 1.15, 255)
        T.manchas(tela, corpo, A, (150, 104, 96), escala=4, quantidade=0.16, forca=0.75, semente=3)   # sarna
        ombro = lerp(A, C, 0.85)                                               # cicatriz
        tela.traco(ombro + v2(-0.05 * S, -0.05 * S), ombro + v2(0.03 * S, 0.04 * S), (176, 150, 130), sobre=True)
        boca = self.ponta_da_boca(P) + v2(-0.05 * S, 0.03 * S)
        T.escorrer(tela, tela.circulo(boca, 0.05 * S) & corpo, boca, (140, 20, 26), densidade=0.6, comp=4,
                   fase=P["fase"], molhado=0.5, semente=4)


class LoboEspectral(Quadrupede):
    """Lobo fantasma azul: corpo translúcido, contraluz fria e patas que viram névoa."""
    nome = "lobo_espectral"
    S = 64
    proporcao = (2.25, 1.22)
    pe = 0.5
    mat = Mat((92, 126, 178), 6, relevo=1.0, ruido=0.08, especular=(210, 240, 255), luz_hue=0.55)
    mat_barriga = (170, 210, 240)
    crina = 2
    pescoco = (0.19, -0.14)
    cabeca = Cabeca(tam=0.15, focinho=0.15, olho_cor=(190, 250, 255))
    espectral = 0.78
    cor_espectral = (150, 215, 255)
    sangue = None
    morte_fumaca = (120, 170, 220)
    semente = 13

    def efeitos(self, tela, ctx, P):
        if P["golpe"]:
            boca = self.ponta_da_boca(P)
            T.particulas(tela, boca, (0.08 * self.S, 0.05 * self.S), self.cor_espectral, n=6, fase=P["fase"], sobe=4)


class LoboEspectralSelvagem(LoboEspectral):
    """Espectro de gelo da Cidadela: pelagem branca, cristais de gelo no dorso e hálito de neve."""
    nome = "lobo_espectral_selvagem"
    S = 66
    mat = Mat((214, 228, 244), 6, relevo=1.1, ruido=0.08, especular=(255, 255, 255), luz_hue=0.55)
    mat_barriga = (244, 250, 255)
    perfil = ((0.0, 0.13, 0.12), (0.45, 0.1, 0.1), (1.0, 0.15, 0.2))
    crina = 2
    cabeca = Cabeca(tam=0.16, focinho=0.15, olho_cor=(90, 210, 255))
    espectral = 0.9
    cor_espectral = (222, 242, 255)
    morte_fumaca = (200, 225, 245)
    semente = 17

    def detalhes(self, tela, ctx, P, corpo):
        S = self.S
        for k, t in enumerate((0.15, 0.32, 0.5, 0.68, 0.85, 1.02)):          # cristais no dorso
            p = P["espinha"][min(len(P["espinha"]) - 1, int(t * (len(P["espinha"]) - 1)))]
            if t > 1:
                p = lerp(P["C"], P["nuca"], 0.5)
            base = p + P["cima"] * (self._perfil(min(t, 1))[0] * S * 0.8)
            alto = S * (0.13 + 0.05 * (k % 3 == 1))
            ponta = base + P["cima"] * alto - P["d"] * (alto * 0.45)
            lado = P["d"] * (S * 0.03)
            T.cristal(tela, tela.poly([base - lado, base + lado, ponta]), GELO_CRISTAL, base, opacidade=0.85, facetas=1,
                      periodo=7, semente=k)
        T.manchas(tela, corpo, P["A"], (150, 200, 235), escala=4, quantidade=0.2, forca=0.45, semente=5)   # geada

    def efeitos(self, tela, ctx, P):
        S = self.S
        boca = self.ponta_da_boca(P)
        n = 16 if P["golpe"] else 4                                           # hálito de neve
        T.particulas(tela, boca + v2(0.06 * S, 0), (0.08 * S if P["golpe"] else 0.03 * S, 0.04 * S), (240, 250, 255),
                     n=n, fase=P["fase"], sobe=-2 if P["golpe"] else 5, semente=7)
        if P["golpe"]:
            tela.brilho(boca + v2(0.08 * S, 0), 0.12 * S, (200, 240, 255), 0.4)


# ============================================================
# FAMILIARES DO MONGE (espíritos)
# ============================================================

class TigreEspiritual(Quadrupede):
    """Tigre de espírito dourado: listras, olhos de sol e chamas fantasmas na cauda e nas patas."""
    nome = "tigre_espiritual"
    S = 70
    proporcao = (2.2, 1.2)
    pe = 0.5
    mat = Mat((226, 152, 64), 6, relevo=1.05, ruido=0.08, luz_hue=0.12, especular=(255, 240, 200))
    mat_barriga = (252, 228, 178)
    comprimento = 0.64
    altura_anca = 0.4
    altura_cernelha = 0.43
    perfil = ((0.0, 0.13, 0.12), (0.45, 0.11, 0.11), (1.0, 0.14, 0.18))
    pescoco = (0.15, -0.1)
    pescoco_larg = (0.13, 0.09)
    cabeca_ang = 0.08
    cabeca = Cabeca(estilo="felina", tam=0.17, focinho=0.07, orelha="redonda", olho_cor=(255, 245, 150))
    pata_tras = Pata(comp=(0.19, 0.17, 0.12), grossura=(0.075, 0.055, 0.042, 0.036), joelho="frente", metatarso=0.4)
    pata_frente = Pata(comp=(0.17, 0.16, 0.07), grossura=(0.07, 0.05, 0.04, 0.036), joelho="tras", metatarso=0.12)
    cauda = Cauda(comp=0.5, grossura=(0.04, 0.035, 0.032, 0.028), segmentos=7, ang=math.pi - 0.3, curva=1.2, estilo="lisa")
    espectral = 0.84
    cor_espectral = (255, 186, 80)
    sangue = None
    morte_fumaca = (230, 180, 100)
    semente = 19

    def detalhes(self, tela, ctx, P, corpo):
        S = self.S
        T.listras(tela, corpo, P["A"], (52, 22, 16), eixo=P["d"], espaco=7, larg=2.4, ondula=1.2, forca=0.95)
        k = self.cabeca.tam / 0.12                                            # focinho e bochechas brancos
        L = Local(P["nuca"], P["ang_cab"], S)
        claro = tela.elipse_girada(L(0.07 * k + self.cabeca.focinho * 0.5, 0.012 * k), 0.05 * k * S, 0.03 * k * S, L.ang)
        claro |= tela.elipse_girada(L(0.03 * k, 0.03 * k), 0.045 * k * S, 0.025 * k * S, L.ang)
        ys, xs = np.nonzero(claro & corpo & ~tela.emite)
        T.misturar_cor(tela, ys, xs, (252, 244, 226), 0.6)

    def efeitos(self, tela, ctx, P):
        S = self.S
        if P["deitado"] < 0.5:
            ponta = P["cauda"][-1]
            fx.chama(tela, ponta, 0.13 * S, 0.07 * S, FOGO_DE_ESPIRITO, fase=P["fase"], linguas=2)
            for nome in ("frente", "tras"):
                pe = P["patas"][nome][-1]
                fx.chama(tela, pe + v2(0.02 * S, 0), 0.07 * S, 0.06 * S, FOGO_DE_ESPIRITO, fase=P["fase"] + 1, brilho=False)
        if P["golpe"]:
            arranhoes(tela, P["patas"]["frente"][-1] + v2(0.04 * S, -0.1 * S), -0.3, 0.3 * S, cor2=(255, 200, 110))


class MacacoEspiritual(Quadrupede):
    """Macaco de jade meio em pé, cauda enrolada; no ataque arremessa uma pedra."""
    nome = "macaco_espiritual"
    S = 52
    proporcao = (2.0, 1.45)
    pe = 0.42
    mat = Mat((96, 186, 136), 6, relevo=1.1, ruido=0.06, luz_hue=0.45, especular=(230, 255, 240))
    mat_barriga = (170, 230, 190)
    comprimento = 0.3
    altura_anca = 0.3
    altura_cernelha = 0.52
    arco = -0.05
    perfil = ((0.0, 0.12, 0.11), (0.5, 0.1, 0.1), (1.0, 0.13, 0.12))
    pescoco = (0.07, -0.08)
    pescoco_larg = (0.08, 0.07)
    cabeca_ang = 0.0
    cabeca = Cabeca(estilo="primata", tam=0.22, focinho=0.06, orelha="redonda", olho_cor=(255, 255, 200))
    pata_tras = Pata(comp=(0.17, 0.16, 0.08), grossura=(0.065, 0.05, 0.04, 0.035), joelho="frente", metatarso=0.5,
                     estilo="mao")
    pata_frente = Pata(comp=(0.21, 0.21, 0.05), grossura=(0.05, 0.042, 0.036, 0.032), joelho="tras", metatarso=0.0,
                       estilo="mao")
    pe_tras_x = 0.02
    pe_frente_x = 0.14
    cauda = Cauda(comp=0.55, grossura=(0.035, 0.03, 0.025, 0.02), segmentos=9, ang=math.pi - 0.1, curva=-3.4, estilo="lisa")
    espectral = 0.84
    cor_espectral = (170, 255, 205)
    sangue = None
    morte_fumaca = (140, 220, 170)
    semente = 23

    def movimento(self, ctx):
        m = super().movimento(ctx)
        if ctx.anim == "ataque":                                              # arremesso por cima da cabeça
            m.update(salto=tabela(ctx, [0.5, 0.25, 0.08, 0.0]), passo=tabela(ctx, [-0.2, 0.15, 0.2, 0.05]),
                     avanco=tabela(ctx, [-0.05, 0.08, 0.1, 0.02]), boca=tabela(ctx, [0.3, 0.8, 0.4, 0.1]),
                     incl=tabela(ctx, [-0.15, 0.1, 0.12, 0.0]))
        return m

    def efeitos(self, tela, ctx, P):
        if P["anim"] != "ataque" or P["i"] == 3:
            return
        S = self.S
        mao = P["patas"]["frente"][-1]
        pedra = [mao + v2(0, -0.04 * S), mao + v2(0.4 * S, -0.12 * S), mao + v2(0.75 * S, -0.02 * S)][P["i"]]
        if P["i"] >= 1:
            for k in range(1, 4):
                rastro = pedra - v2(k * 0.07 * S, -k * 0.01 * S)
                tela.px(rastro[0], rastro[1], misturar(self.cor_espectral, (40, 60, 50), k / 4), emite=True)
        tela.pintar(tela.elipse(pedra[0], pedra[1], 0.045 * S, 0.035 * S), Mat((120, 116, 112), 5, relevo=1.2))
        tela.brilho(pedra, 0.08 * S, self.cor_espectral, 0.3)


class GarcaEspiritual(Ave):
    """Garça de luz em pernas longas; o bico dispara um raio dourado no ataque."""
    nome = "garca_espiritual"
    S = 60
    proporcao = (2.15, 1.95)
    pe = 0.42
    voa = False
    altura = 0.64
    corpo_r = (0.2, 0.11)
    corpo_ang = -0.15
    pescoco_pts = ((0.02, -0.1), (0.09, -0.18), (0.05, -0.28), (0.1, -0.34))
    pescoco_larg = (0.05, 0.035)
    cabeca = Cabeca(estilo="ave", tam=0.1, focinho=0.24, olho_cor=(255, 230, 140), crista=True,
                    bico_cor=Mat((232, 190, 90), 5, relevo=1.2, especular=(255, 250, 210)))
    pata = Pata(comp=(0.3, 0.32), grossura=(0.022, 0.014, 0.012), joelho="tras", estilo="ave", cobertura="escamas",
                garra=(200, 170, 90))
    mat_perna = Mat((200, 160, 80), 5, relevo=0.8)
    asa = Asa(envergadura=0.75, estilo="penas")
    mat = Mat((212, 226, 242), 6, relevo=1.0, ruido=0.06, luz_hue=0.55, especular=(255, 255, 255))
    cauda_comp = 0.16
    espectral = 0.86
    cor_espectral = (225, 240, 255)
    aura_cor = (255, 236, 180)
    sangue = None
    morte_fumaca = (220, 230, 250)
    semente = 29

    def movimento(self, ctx):
        m = super().movimento(ctx)
        if ctx.anim == "ataque":                                              # bote com o pescoço
            m.update(cab=tabela(ctx, [-0.6, 0.55, 0.6, 0.1]), incl=tabela(ctx, [-0.1, 0.18, 0.2, 0.0]),
                     boca=tabela(ctx, [0.0, 0.4, 0.2, 0.0]))
        return m

    def efeitos(self, tela, ctx, P):
        if not P["golpe"]:
            return
        S = self.S
        bico = P["nuca"] + direcao(P["ang_cab"]) * ((self.cabeca.focinho + 0.08) * S)
        d = direcao(P["ang_cab"])
        fim = bico + d * (0.55 * S)
        for k, cor in ((1, (255, 220, 120)), (0, (255, 252, 230))):
            tela.traco(bico + v2(0, k), fim + v2(0, k), cor, emite=True)
        tela.brilho(lerp(bico, fim, 0.5), 0.2 * S, (255, 230, 150), 0.5)
        T.particulas(tela, fim, (0.06 * S, 0.06 * S), (255, 240, 180), n=6, fase=P["fase"], sobe=3)


class Corvo(Ave):
    """Corvo negro-violeta voando: penas puídas, olho vermelho e bico curvo."""
    nome = "corvo"
    S = 56
    proporcao = (2.1, 1.85)
    pe = 0.46
    voa = True
    mat = Mat((46, 42, 62), 6, relevo=1.0, especular=(160, 160, 220), luz_hue=0.65, ruido=0.08)
    corpo_r = (0.21, 0.135)
    cabeca = Cabeca(estilo="ave", tam=0.11, focinho=0.11, olho_cor=(255, 40, 40), crista=True)
    asa = Asa(envergadura=0.72, estilo="penas")
    semente = 31

    def efeitos(self, tela, ctx, P):
        if P["golpe"]:
            bico = P["nuca"] + direcao(P["ang_cab"]) * ((self.cabeca.focinho + 0.08) * self.S)
            arranhoes(tela, bico, P["ang_cab"] - 0.2, 0.22 * self.S, larg=2.0)
        if P["anim"] == "dano":                                               # penas soltas
            T.particulas(tela, P["centro"], (0.25 * self.S, 0.15 * self.S), self.mat[2], n=5, fase=P["fase"],
                         sobe=-6, emite=False, semente=3)


class GatoNegro(Quadrupede):
    """Gato preto de costas arqueadas e olhos amarelos; deixa faíscas roxas de azar."""
    nome = "gato_negro"
    S = 46
    proporcao = (2.25, 1.3)
    pe = 0.48
    mat = Mat((52, 44, 64), 6, relevo=1.1, ruido=0.1, especular=(150, 140, 200), luz_hue=0.7)
    mat_barriga = None
    comprimento = 0.45
    altura_anca = 0.33
    altura_cernelha = 0.31
    arco = -0.07
    perfil = ((0.0, 0.1, 0.085), (0.5, 0.085, 0.075), (1.0, 0.1, 0.12))
    pescoco = (0.11, -0.11)
    pescoco_larg = (0.08, 0.06)
    cabeca_ang = 0.05
    cabeca = Cabeca(estilo="felina", tam=0.15, focinho=0.04, orelha="pontuda", olho_cor=(225, 255, 80), presas=False)
    pata_tras = Pata(comp=(0.16, 0.15, 0.09), grossura=(0.05, 0.032, 0.026, 0.024), joelho="frente", metatarso=0.45)
    pata_frente = Pata(comp=(0.15, 0.14, 0.05), grossura=(0.042, 0.028, 0.024, 0.022), joelho="tras", metatarso=0.1)
    cauda = Cauda(comp=0.55, grossura=(0.035, 0.032, 0.03, 0.022), segmentos=8, ang=-2.5, curva=1.7, estilo="pelo")
    crina = 0
    sangue = ((70, 6, 14), (110, 14, 24))
    semente = 37

    def movimento(self, ctx):
        m = super().movimento(ctx)
        if ctx.anim == "ataque":                                              # patada com as unhas
            m.update(salto=tabela(ctx, [0.05, 0.22, 0.12, 0.0]), boca=tabela(ctx, [0.6, 0.9, 0.5, 0.1]))
        return m

    def efeitos(self, tela, ctx, P):
        S = self.S
        if not P["morto"]:
            T.particulas(tela, P["centro"] + v2(0, -0.15 * S), (0.3 * S, 0.1 * S), (190, 110, 255), n=5,
                         fase=P["fase"], sobe=0.25 * S, semente=11)
        if P["golpe"]:
            arranhoes(tela, P["patas"]["frente"][-1] + v2(0.04 * S, -0.04 * S), -0.4, 0.3 * S,
                      cor2=(200, 130, 255), larg=2.0)


# ============================================================
# MINAS / PÂNTANO / CAVERNAS
# ============================================================

LAVA = (255, 140, 40)


class SalamandraDeLava(Quadrupede):
    """Lagarto de obsidiana rachado de lava, espinhos de magma no dorso; cospe fogo e esfria ao morrer."""
    nome = "salamandra_de_lava"
    S = 64
    proporcao = (2.2, 1.1)
    pe = 0.45
    cobertura = "escamas"
    mat = Mat((64, 50, 48), 6, relevo=1.25, ruido=0.15, especular=(160, 130, 120))
    mat_barriga = (126, 64, 34)
    comprimento = 0.5
    altura_anca = 0.2
    altura_cernelha = 0.21
    arco = -0.01
    perfil = ((0.0, 0.085, 0.07), (0.5, 0.08, 0.075), (1.0, 0.09, 0.09))
    pescoco = (0.12, -0.02)
    pescoco_larg = (0.08, 0.065)
    cabeca_ang = 0.05
    cabeca = Cabeca(estilo="reptil", tam=0.14, focinho=0.13, olho_cor=(255, 200, 60))
    pata_tras = Pata(comp=(0.11, 0.11, 0.06), grossura=(0.05, 0.04, 0.032, 0.03), joelho="frente", metatarso=0.6,
                     cobertura="escamas", garra=(40, 30, 30))
    pata_frente = Pata(comp=(0.1, 0.1, 0.04), grossura=(0.045, 0.036, 0.03, 0.028), joelho="tras", metatarso=0.2,
                       cobertura="escamas", garra=(40, 30, 30))
    pe_tras_x = -0.06
    pe_frente_x = 0.1
    cauda = Cauda(comp=0.7, grossura=(0.075, 0.055, 0.035, 0.012), segmentos=8, ang=math.pi - 0.08, curva=0.25,
                  estilo="escamas")
    sangue = ((120, 40, 10), (200, 90, 20))
    semente = 43

    def detalhes(self, tela, ctx, P, corpo):
        S = self.S
        esfriou = P["anim"] == "morte" and P["i"] >= 2
        cor = (90, 80, 76) if esfriou else LAVA
        T.rachaduras(tela, corpo, P["centro"], area=(0.4 * S, 0.08 * S), n=8, passos=4, cor=cor, emite=not esfriou,
                     semente=self.semente, brilho=0.0 if esfriou else 0.3)
        for k, t in enumerate(np.linspace(0.1, 1.0, 7)):                       # espinhos de magma
            i = int(t * (len(P["espinha"]) - 1))
            base = P["espinha"][i] + P["cima"] * (self._perfil(t)[0] * S * 0.85)
            alto = S * (0.05 + 0.025 * (k % 2))
            ponta = base + P["cima"] * alto - P["d"] * (alto * 0.5)
            lado = P["d"] * (S * 0.02)
            tela.pintar(tela.poly([base - lado, base + lado, ponta]), self.mat.escuro(1))
            if not esfriou:
                tela.px(ponta[0], ponta[1] + 1, (255, 190, 80), emite=True)

    def efeitos(self, tela, ctx, P):
        S = self.S
        if P["anim"] == "morte" and P["i"] >= 2:
            fx.fumaca(tela, P["centro"] + v2(0, -0.1 * S), 0.08 * S, cor=(80, 74, 76), fase=P["fase"], n=4, sobe=10)
            return
        T.particulas(tela, P["centro"] + v2(0, -0.1 * S), (0.35 * S, 0.06 * S), (255, 160, 60), n=6, fase=P["fase"],
                     sobe=0.3 * S, semente=3)
        if P["golpe"]:                                                         # sopro de lava
            boca = self.ponta_da_boca(P)
            fx.chama(tela, boca + v2(0.06 * S, 0.01 * S), 0.35 * S if P["i"] == 1 else 0.22 * S, 0.16 * S, fx.FOGO,
                     fase=P["fase"], inclina=1.6, linguas=3)


class SanguessugaColossal(Verme):
    """Sanguessuga gigante e viscosa: anéis brilhantes, barriga cheia de sangue e ventosa de dentes."""
    nome = "sanguessuga_colossal"
    S = 60
    proporcao = (2.1, 1.1)
    pe = 0.4
    comprimento = 1.35
    segmentos = 16
    raio = ((0.0, 0.06), (0.25, 0.13), (0.7, 0.15), (0.92, 0.1), (1.0, 0.08))
    ondas = 0.8
    amplitude = 0.025
    ergue = 0.1
    altura_bote = 0.5
    mat = Mat((58, 66, 46), 6, relevo=1.25, especular=(220, 230, 190), ruido=0.08)
    mat_barriga = (150, 46, 50)
    sangue = ((90, 10, 20), (140, 20, 30))
    semente = 47

    def aneis(self, tela, P, m):
        for a, b, r in zip(P["espinha"], P["espinha"][1:], self.larguras(P)):
            d = b - a
            n = v2(-d[1], d[0]) / (np.linalg.norm(d) or 1)
            c = lerp(a, b, 0.5)
            for x, y in T.bresenham(c - n * r * 0.9, c + n * r * 0.9):
                if 0 <= x < tela.w and 0 <= y < tela.h and m[y, x]:
                    tela.cor[y, x] *= 0.8
        topo = [p - v2(0, r * 0.45) for p, r in zip(P["espinha"], self.larguras(P))]          # listras laterais laranja
        for a, b in zip(topo, topo[1:]):
            for x, y in T.bresenham(a, b):
                if 0 <= x < tela.w and 0 <= y < tela.h and m[y, x]:
                    tela.cor[y, x] = tela.cor[y, x] * 0.4 + np.array((200, 120, 50), np.float32) * 0.6
        T.manchas(tela, m, P["espinha"][0], (30, 30, 24), escala=3, quantidade=0.22, forca=0.7, semente=5)
        T.brilho_umido(tela, m, P["espinha"][0], densidade=0.04)
        T.escorrer(tela, m, P["espinha"][0], (90, 100, 64), densidade=0.05, comp=2, fase=P["fase"], molhado=0.2)

    def boca(self, tela, ctx, P):
        S = self.S
        c = P["cabeca"] + direcao(P["ang_cab"]) * (0.03 * S)
        ventosa = tela.elipse_girada(c, 0.04 * S, 0.085 * S, P["ang_cab"])
        m = tela.pintar(ventosa, self.mat.claro(1))
        abre = P["boca"]
        if abre > 0.1:
            dentro = tela.elipse_girada(c + direcao(P["ang_cab"]) * 1.5, 0.02 * S, 0.06 * S * abre, P["ang_cab"])
            tela.chapado(dentro, (70, 8, 16))
            for k in range(8):                                                  # anel de dentes
                a = k / 8 * 2 * math.pi
                p = c + direcao(P["ang_cab"]) * 1.5 + girar(v2(math.cos(a) * 0.018 * S, math.sin(a) * 0.055 * S * abre),
                                                            P["ang_cab"])
                tela.px(p[0], p[1], (230, 216, 190))
            if P["golpe"]:
                T.escorrer(tela, dentro, c, (150, 16, 26), densidade=0.7, comp=4, fase=P["fase"], molhado=0.0)
        for k in range(3):                                                      # olhinhos
            p = c - direcao(P["ang_cab"]) * (0.05 * S + k * 2) + v2(0, -0.07 * S)
            tela.px(p[0], p[1], (20, 10, 10))
        return m


class Centopeia(Verme):
    """Centopeia gigante de carapaça rubra: dezenas de patas amarelas, presas venenosas e antenas."""
    nome = "centopeia"
    S = 70
    proporcao = (2.8, 1.4)
    pe = 0.53
    cobertura = "liso"
    comprimento = 1.7
    segmentos = 18
    raio = ((0.0, 0.035), (0.15, 0.055), (0.8, 0.065), (1.0, 0.055))
    ondas = 1.6
    amplitude = 0.02
    ergue = 0.6
    altura_bote = 0.7
    mat = Mat((120, 44, 30), 6, relevo=1.3, especular=(255, 200, 150), ruido=0.08)
    mat_pata = Mat((214, 172, 64), 5, relevo=1.0)
    cabeca = Cabeca(estilo="inseto", tam=0.13, olho_cor=(255, 60, 40))
    sangue = ((40, 60, 18), (80, 110, 30))
    semente = 53

    def patas(self, tela, P, lado):
        S = self.S
        chao = self.ancora[1]
        mat = self.mat_pata if lado == "ca" else self.mat_pata.escuro(2)
        larg = self.larguras(P)
        for k in range(1, len(P["espinha"]) - 1):
            p, r = P["espinha"][k], larg[k]
            base = p + v2(0.03 * S if lado == "la" else 0, r * 0.55)
            passo = math.sin(P["fase"] * 2 + k * 0.9 + (math.pi if lado == "la" else 0)) * 0.03 * S
            no_ar = base[1] < chao - 0.25 * S or P["deitado"] > 0.5
            pe = base + v2(0.05 * S + passo, 0.13 * S) if no_ar else v2(base[0] + 0.04 * S + passo, chao - 1)
            joelho = lerp(base, pe, 0.45) + v2(-0.04 * S, -0.05 * S)
            tela.pintar(tela.corrente([base, joelho, pe], [0.014 * S, 0.012 * S, 0.006 * S]), mat)
            tela.px(pe[0] + 1, pe[1], (60, 40, 20))

    def atras(self, tela, ctx, P):
        self.patas(tela, P, "la")
        cauda = P["espinha"][0]
        for dy in (-1, 1):                                                       # cercos da cauda
            tela.pintar(tela.corrente([cauda, cauda + v2(-0.12 * self.S, dy * 0.04 * self.S - 0.02 * self.S)],
                                      [0.014 * self.S, 0.4]), self.mat_pata.escuro(1))

    def frente(self, tela, ctx, P):
        self.patas(tela, P, "ca")

    def aneis(self, tela, P, m):
        for a, b, r in zip(P["espinha"], P["espinha"][1:], self.larguras(P)):
            d = b - a
            n = v2(-d[1], d[0]) / (np.linalg.norm(d) or 1)
            c = lerp(a, b, 0.5)
            tela.traco(c - n * r, c + n * r, (30, 10, 8), sobre=True)
            tela.traco(c - n * r + d * 0.15, c + n * r + d * 0.15, self.mat[4], sobre=True)
        T.quitina(tela, m, P["espinha"][0], eixo=(1, 0), espaco=50, brilho=0.22, poros=0.02)

    def boca(self, tela, ctx, P):
        base = P["cabeca"] - direcao(P["ang_cab"]) * (0.02 * self.S)
        return self.cabeca.desenhar(tela, base, P["ang_cab"] + 0.2, self.S, self.mat, boca=P["boca"], morto=P["morto"],
                                    fase=P["fase"])


class MorcegoGigante(ForjaAnimal):
    """Morcego gigante visto de frente: asas de couro abertas com ossos dos dedos, membrana rasgada e
    translúcida, pelagem, orelhas enormes, olhos vermelhos e presas."""
    nome = "morcego_gigante"
    S = 58
    proporcao = (2.3, 1.9)
    pe = 0.48
    cobertura = "pelo"
    mat = Mat((70, 54, 58), 6, relevo=1.1, ruido=0.15)
    mat_asa = Mat((74, 46, 56), 5, relevo=0.6, ruido=0.1)
    osso = Mat((138, 104, 106), 5, relevo=1.0)
    pele = Mat((150, 98, 104), 5, relevo=0.9)
    envergadura = 0.74
    altura_voo = 0.7
    semente = 59
    # asa direita aberta, em frações da envergadura (o ombro é a origem)
    ASA = dict(cotovelo=(0.24, -0.22), pulso=(0.5, -0.14), dedos=[(0.86, -0.34), (0.95, -0.02), (0.78, 0.2), (0.48, 0.3)],
               ancora=(0.08, 0.28))

    def movimento(self, ctx):
        m = super().movimento(ctx)
        m["bater"] = 0.0
        if ctx.anim in ("parado", "dano"):
            m["bater"] = tabela(ctx, [0.55, 0.1, -0.45, 0.1])
            m["bob"] = tabela(ctx, [0.03, 0.0, -0.03, 0.0])
        if ctx.anim == "ataque":
            m.update(bater=tabela(ctx, [0.7, -0.5, -0.3, 0.2]), avanco=tabela(ctx, [-0.05, 0.3, 0.32, 0.08]),
                     boca=tabela(ctx, [0.3, 1.0, 0.7, 0.1]))
        if ctx.anim == "morte":
            m["bater"] = tabela(ctx, [0.3, -0.3, -0.75, -0.85])
        return m

    def montar(self, m):
        S = self.S
        cx, chao = self.ancora
        cai = {"morte": [0.0, 0.3, 0.75, 0.82]}.get(m["anim"], [0, 0, 0, 0])[min(m["i"], 3)]
        alt = self.altura_voo * (1 - cai)
        centro = v2(cx + m["avanco"] * S, chao - alt * S + m["bob"] * S)
        P = dict(m, centro=centro, cai=cai)
        esc = self.envergadura * S
        for lado in (1, -1):
            ombro = centro + v2(lado * 0.06 * S, -0.09 * S)
            giro = -m["bater"] * lado
            def ponto(xy):
                return girar(ombro + v2(xy[0] * lado * esc, xy[1] * esc), giro, ombro)
            P["asa_" + ("d" if lado > 0 else "e")] = dict(raiz=ombro, cotovelo=ponto(self.ASA["cotovelo"]),
                                                          pulso=ponto(self.ASA["pulso"]),
                                                          dedos=[ponto(d) for d in self.ASA["dedos"]],
                                                          ancora=ponto(self.ASA["ancora"]))
        return P

    def asa(self, tela, A, lado, S):
        raiz, cot, pulso, dedos, anc = A["raiz"], A["cotovelo"], A["pulso"], A["dedos"], A["ancora"]
        contorno = [raiz, cot, pulso, dedos[0]]
        for i in range(1, len(dedos)):                                              # borda recortada entre os dedos
            contorno += [lerp(lerp(dedos[i - 1], dedos[i], 0.5), pulso, 0.28), dedos[i]]
        contorno += [lerp(lerp(dedos[-1], anc, 0.5), pulso, 0.2), anc]
        m = tela.poly(contorno)
        rng = np.random.default_rng(self.semente + (lado > 0))
        for _ in range(3):                                                          # rasgos
            i = int(rng.integers(0, len(dedos) - 1))
            c = lerp(lerp(dedos[i], dedos[i + 1], rng.uniform(0.3, 0.7)), pulso, rng.uniform(0.1, 0.3))
            r = S * rng.uniform(0.02, 0.035)
            m &= ~tela.poly([c + v2(-r, -r * 0.4), c + v2(r * 0.3, -r), c + v2(r, r * 0.5), c + v2(-r * 0.2, r)])
        tela.vidro(m, self.mat_asa if lado > 0 else self.mat_asa.escuro(1), 0.9)
        for d in dedos:                                                             # nervuras e ossos dos dedos
            tela.traco(lerp(pulso, d, 0.15), lerp(pulso, d, 0.6), self.mat_asa[0], sobre=True)
            tela.pintar(tela.capsula(pulso, d, S * 0.014, S * 0.005), self.osso)
        tela.pintar(tela.capsula(raiz, cot, S * 0.03, S * 0.022) | tela.capsula(cot, pulso, S * 0.022, S * 0.016), self.osso)
        gancho = pulso + v2(lado * S * 0.01, -S * 0.04)                                 # garra do polegar
        tela.traco(pulso, gancho, (226, 214, 196))
        tela.px(gancho[0] - lado, gancho[1], (226, 214, 196))

    def atras(self, tela, ctx, P):
        S = self.S
        for lado, nome in ((-1, "asa_e"), (1, "asa_d")):
            self.asa(tela, P[nome], lado, S)
        c = P["centro"]
        for dx in (-0.035, 0.035):                                                  # pés com garras pendurados
            pe = c + v2(dx * S, 0.17 * S)
            tela.pintar(tela.capsula(c + v2(dx * S, 0.08 * S), pe, S * 0.018, S * 0.012), self.pele.escuro(1))
            for k in (-1, 0, 1):
                tela.traco(pe, pe + v2(k * 1.5, 2.5), (226, 214, 196))

    def corpo(self, tela, ctx, P):
        S = self.S
        c = P["centro"]
        corpo = tela.elipse(c[0], c[1], 0.1 * S, 0.15 * S)
        corpo |= T.tufos(tela, corpo, c, (0, -1), comp=2.5, espaco=2, inclina=0.0, semente=3)
        corpo |= T.tufos(tela, corpo, c, (1, 0), comp=2, espaco=2, inclina=0.5, semente=4)
        corpo |= T.tufos(tela, corpo, c, (-1, 0), comp=2, espaco=2, inclina=-0.5, semente=5)
        m = tela.pintar(corpo, self.mat)
        T.pelagem(tela, m, c, ang=math.pi / 2, comp=3, densidade=0.3, semente=6)
        return m | self.cabeca(tela, ctx, P)

    def cabeca(self, tela, ctx, P):
        """Cabeça de frente: orelhas enormes, olhos vermelhos, folha nasal e presas."""
        S = self.S
        c = P["centro"] + v2(0, -0.17 * S)
        for lado in (-1, 1):
            orelha = [c + v2(lado * 0.03 * S, -0.03 * S), c + v2(lado * 0.075 * S, -0.02 * S), c + v2(lado * 0.07 * S, -0.16 * S)]
            tela.pintar(tela.poly(orelha), self.mat)
            dentro = [lerp(orelha[0], orelha[2], 0.25) + v2(lado * 1, 0), lerp(orelha[1], orelha[2], 0.25),
                      lerp(orelha[0], orelha[2], 0.8) + v2(lado * 1.5, 0)]
            tela.chapado(tela.poly(dentro), self.pele[1])
        m = tela.pintar(tela.circulo(c, 0.065 * S), self.mat)
        T.pelagem(tela, m, c, ang=math.pi / 2, comp=2, densidade=0.25, semente=7)
        focinho = c + v2(0, 0.025 * S)
        tela.pintar(tela.elipse(focinho[0], focinho[1], 0.035 * S, 0.028 * S), self.pele)
        tela.pintar(tela.poly([focinho + v2(-0.012 * S, -0.01 * S), focinho + v2(0.012 * S, -0.01 * S),
                               focinho + v2(0, -0.045 * S)]), self.pele.claro(1))           # folha nasal
        abre = P["boca"]
        boca = focinho + v2(0, 0.02 * S)
        tela.chapado(tela.elipse(boca[0], boca[1], 0.022 * S, max(0.8, 0.02 * S * abre)), (56, 8, 14))
        for dx in (-0.012, 0.012):                                                  # presas
            for i in range(2 if abre < 0.3 else 3):
                tela.px(boca[0] + dx * S, boca[1] - 1 + i, (234, 224, 200))
        for dx in (-0.028, 0.028):                                                  # olhos
            o = c + v2(dx * S, -0.012 * S)
            tela.chapado(tela.elipse(o[0], o[1], max(1.0, 0.012 * S), max(0.8, 0.009 * S)), (20, 8, 10))
            if not P["morto"]:
                tela.px(o[0], o[1], (255, 40, 40), emite=True)
                tela.brilho(o, 4, (255, 40, 40), 0.6)
        return m

    def efeitos(self, tela, ctx, P):
        if P["golpe"]:
            boca = P["centro"] + v2(0.04 * self.S, -0.11 * self.S)
            arranhoes(tela, boca, 0.6, 0.28 * self.S, larg=2.5)