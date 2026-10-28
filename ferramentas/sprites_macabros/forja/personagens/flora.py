"""Plantas e fungos feitos com a forja de plantas (forja/criaturas/planta.py).

    RaizSanguinea   invocação da Mãe-Raiz: raiz espinhenta que brota do chão com um bulbo de
                    seiva pulsando e se estica para agarrar
    FungoEsporento  cogumelo andante de chapéu vermelho; ao morrer estoura numa nuvem de esporos
"""
import math

import numpy as np

from ..motor import Mat, v2, lerp, misturar
from .. import texturas as T
from .. import fx
from ..criaturas.planta import ForjaPlanta, Cogumelo, Arvore

SEIVA = (230, 40, 50)


class RaizSanguinea(ForjaPlanta):
    """Raiz retorcida cheia de espinhos; o bulbo de seiva na ponta pulsa e o ataque é um bote."""
    nome = "raiz_sanguinea"
    S = 50
    proporcao = (1.75, 1.85)
    pe = 0.4
    semente = 41
    altura = 1.1
    larg_base, larg_topo = 0.2, 0.08
    torcao = 0.12
    nos = 1
    mat_tronco = Mat((86, 54, 44), 6, relevo=1.2, ruido=0.2, dither=0.4)
    musgo = None
    seiva = SEIVA
    espinhos = 9
    n_raizes = 4
    raiz_comp = 0.4
    rosto_t = None

    def movimento(self, ctx):
        m = super().movimento(ctx)
        if ctx.anim == "ataque":                                              # bote até o alvo
            m["inclina"] = [-0.25, 0.6, 0.5, 0.12][ctx.i]
        elif ctx.anim == "parado":
            m["inclina"] = 0.08 * math.sin(ctx.a)
        elif ctx.anim == "morte":
            m["afunda"] = [0.1, 0.3, 0.55, 0.7][ctx.i]
        return m

    def tronco(self, tela, P):
        m = super().tronco(tela, P)
        S = self.S
        topo = P["espinha"][-1]
        pulsa = 1 + 0.12 * math.sin(P["fase"] * 2)
        r = 0.1 * S * pulsa * (1 - P["queda"] * 0.5)
        bulbo = tela.elipse(topo[0], topo[1] - r * 0.4, r, r * 1.15)                 # bulbo de seiva
        mb = tela.pintar(bulbo, Mat(misturar(SEIVA, (90, 10, 20), 0.35 + 0.4 * P["queda"]), 6, relevo=1.3,
                                    especular=(255, 200, 200)))
        for a in (0.4, 1.6, 2.7, 3.9, 5.1):                                          # veias
            p = topo + v2(math.cos(a) * r * 0.9, math.sin(a) * r - r * 0.4)
            tela.traco(lerp(topo + v2(0, -r * 0.4), p, 0.3), p, (90, 10, 20), sobre=True)
        if not P["morto"]:
            tela.brilho(topo + v2(0, -r * 0.4), r * 2.5, SEIVA, 0.45 * (1 - P["queda"]))
            T.escorrer(tela, mb, topo, (150, 16, 24), densidade=0.35, comp=4, fase=P["fase"], molhado=0.0)
        return m | mb


class FungoEsporento(Cogumelo):
    """Cogumelo andante de chapéu vermelho pintado e cara boba; os esporos envenenam (e estouram na morte)."""
    nome = "fungo_esporento"
    S = 50
    proporcao = (1.7, 1.6)
    pe = 0.45
    semente = 43
    altura = 0.58
    chapeu = Mat((188, 36, 42), 6, relevo=1.2, especular=(255, 190, 180), ruido=0.12)
    chapeu_r = (0.46, 0.28)
    mat_tronco = Mat((224, 208, 172), 6, relevo=0.9, ruido=0.12)
    olho_cor = (230, 255, 90)
    pintas = (240, 232, 214)
    pintas_brilham = (210, 255, 110)
    esporos = (190, 240, 90)

    def efeitos(self, tela, ctx, P):
        if P["anim"] != "morte" or P["i"] == 0:
            return super().efeitos(tela, ctx, P)
        S = self.S
        c = P["espinha"][-1] + v2(0, -S * 0.1)                         # Esporos Póstumos: a nuvem estoura
        raio = S * (0.18 + 0.1 * P["i"])
        fx.fumaca(tela, c, raio, cor=misturar(self.esporos, (60, 70, 40), 0.5), fase=P["fase"], n=6, sobe=8)
        T.particulas(tela, c, (raio * 1.6, raio), self.esporos, n=26, fase=P["fase"], sobe=S * 0.2, semente=P["i"])
        tela.brilho(c, raio * 1.5, self.esporos, 0.35)


class MaeRaiz(Arvore):
    """A Mãe-Raiz: árvore-mãe enorme, retorcida e bela. Olhos grandes e penetrantes de íris dourada e pupila
    em fenda, boca imensa cheia de farpas com seiva acesa no fundo, braços de raiz, flores e esporos."""
    nome = "mae_raiz"
    S = 96
    proporcao = (2.4, 2.25)
    pe = 0.45
    semente = 61
    altura = 1.25
    larg_base, larg_topo = 0.62, 0.34
    torcao = 0.1
    nos = 4
    mat_tronco = Mat((94, 62, 48), 6, relevo=1.3, ruido=0.2, dither=0.4)
    musgo = (70, 92, 46)
    seiva = (240, 50, 50)
    espinhos = 6
    n_raizes = 8
    raiz_comp = 0.85
    rosto_t = 0.55
    olho_tam = 0.12
    olho_cor = (255, 206, 80)
    boca_larg = 0.44
    bracos = ((0.8, 1, 0.75, 0.085, 0.25), (0.82, -1, 0.7, 0.075, 2.3))
    n_galhos = 6
    galho_comp = 0.46
    galho_larg = 0.085
    abertura = 1.25
    folhas = Mat((178, 26, 46), 5, relevo=0.8, ruido=0.25)
    folhas_por_ponta = 6
    cipos = 6
    FLOR = (250, 214, 226)

    def rosto(self, tela, P, tronco):
        super().rosto(tela, P, tronco)
        R = P["rosto_pos"]
        for c, r in R["olhos"]:                                            # pálpebras de casca e pupila em fenda
            anel = tela.elipse(c[0], c[1], r * 1.45, r * 1.1) & ~tela.elipse(c[0], c[1], r * 1.05, r * 0.8) & tronco
            ys, xs = np.nonzero(anel)
            T.multiplicar(tela, ys, xs, 0.55)
            if R["vivo"]:
                tela.traco(c + v2(r * 0.25, -r * 0.35), c + v2(r * 0.25, r * 0.35), (30, 6, 0), emite=True)
                tela.chapado(tela.circulo(c + v2(r * 0.25, 0), max(1.0, r * 0.65)) & ~tela.circulo(c + v2(r * 0.25, 0), max(0.6, r * 0.45)),
                             (255, 150, 40), emite=True)
        bc, bw, bh = R["boca"], R["bw"], R["bh"]
        if R["vivo"]:                                                      # brasa de seiva no fundo da garganta
            tela.chapado(tela.elipse(bc[0], bc[1] + bh * 0.2, bw * 0.45, bh * 0.45), (170, 20, 30), emite=True)
            tela.brilho(bc, bw * 1.2, (240, 50, 50), 0.4)
            boca = tela.elipse(bc[0], bc[1], bw * 1.1, bh * 1.4)
            T.escorrer(tela, boca & tronco, bc, (180, 20, 30), densidade=0.4, comp=6, fase=P["fase"], molhado=0.0, semente=3)

    def efeitos(self, tela, ctx, P):
        super().efeitos(tela, ctx, P)
        S = self.S
        for g, pts in zip(self.galhos, P["galhos"]):                        # flores nas pontas dos galhos
            if g["filhos"] or P["queda"] > 0.5:
                continue
            c = pts[-1] + v2(2, -1)
            for k in range(5):
                a = k * 1.256 + P["fase"] * 0.2
                tela.px(c[0] + math.cos(a) * 1.6, c[1] + math.sin(a) * 1.6, self.FLOR)
            tela.px(c[0], c[1], (255, 220, 90), emite=True)
        if not P["morto"]:
            T.particulas(tela, P["espinha"][-1] + v2(0, 0.2 * S), (0.6 * S, 0.3 * S), (255, 120, 120), n=10,
                         fase=P["fase"], sobe=0.4 * S, semente=7)
