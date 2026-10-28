"""Bardo (classe jogável) e os personagens do acampamento e das paradas da run.

Bardo, Taverneiro, Capitã, Mercador, Alquimista, Necromante, Mestre (treinadores),
Estudioso do bestiário, Mestre do Grimório e Mago Ancião (acampamento interativo).
Todos usam o mesmo esqueleto humanoide dos heróis (humanoide.py).
"""
import math

from ..motor import Mat, metal, v2, lerp, dir_ang, norm
from ..humanoide import (perna, braco, tronco, pescoco, cabeca_base, olho, manto, capa, capuz, cinto,
                         quadro_tronco, quadro_cabeca)
from ..anim import Modelo, idle
from .. import armas, fx
from .herois import (PELE, PELE_PALIDA, COURO, COURO_ESC, ACO, FERRO, OURO_VELHO, OSSO, MADEIRA, MALHA,
                     morte_extras, golpe_rastro)

CABELO_CASTANHO = Mat((86, 54, 38), 5, ruido=0.5)
CABELO_GRISALHO = Mat((150, 146, 140), 5, ruido=0.5)
CABELO_PRETO = Mat((40, 32, 40), 5, ruido=0.4)
LINHO = Mat((176, 162, 136), 6, desce=0.2, ruido=0.15)
LATAO = metal((176, 140, 70), especular=(255, 236, 170))


def nota_musical(tela, p, cor, emite=True):
    """Uma colcheia de 4 pixels de altura (para as canções do bardo)."""
    x, y = int(p[0]), int(p[1])
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (1, -1), (1, -2), (1, -3), (2, -3), (3, -2)):
        tela.px(x + dx, y + dy, cor, emite=emite)


def barba(tela, J, mat, comprimento=0.5, largura=0.55):
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.82
    pts = [(-w * 0.05, -h * 0.05), (w * 0.55, -h * 0.12), (w * 0.5, -h * (0.5 + comprimento * 0.4)),
           (w * 0.15, -h * (0.55 + comprimento)), (-w * 0.1, -h * (0.45 + comprimento * 0.6)), (-w * 0.25, -h * 0.25)]
    tela.pintar(tela.poly(C.pts([(x * largura / 0.55, y) for x, y in pts])), mat)


# ============================================================
# BARDO — trovador sombrio de chapéu emplumado e alaúde
# ============================================================

class Bardo(Modelo):
    nome = "bardo"
    H = 74
    estilo = "magia"
    prop = dict(ombros=0.23, quadris=0.18)
    base = dict(braco_f=(0.55, 1.1), braco_b=(0.75, 1.45), arma_f=0.0, pe_f=(-0.07, 0), pe_b=(0.08, 0))
    gibao = Mat((112, 26, 40), 6, desce=0.25, ruido=0.1)
    capa_mat = Mat((26, 54, 60), 6, desce=0.4, ruido=0.1, relevo=0.6, arredonda=0.5)
    chapeu = Mat((52, 24, 40), 6, relevo=0.8)

    def alaude(self, tela, J, ctx):
        """Alaúde preso ao peito: o corpo fica na barriga e o braço sobe para a frente."""
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        corpo = Q.pt(0.05 * H, T * 0.32)
        d = dir_ang(J["giro"] + 0.85)         # braço do instrumento: para cima e para a frente
        madeira = Mat((150, 92, 46), 6, relevo=1.1, especular=(240, 190, 120))
        tela.pintar(tela.capsula(corpo, corpo + d * H * 0.36, 1.6, 1.2), MADEIRA)
        tela.pintar(tela.elipse_girada(corpo, H * 0.11, H * 0.085, math.atan2(d[1], d[0])), madeira)
        tela.pintar(tela.circulo(corpo + d * H * 0.03, H * 0.025), Mat((30, 18, 14), 4))
        topo = corpo + d * H * 0.38
        tela.pintar(tela.poly([topo, topo + v2(3, -2), topo + v2(4, 1)]), MADEIRA.escuro(1))
        for k in (-1, 0, 1):                  # cordas
            tela.traco(corpo - d * 2 + v2(0, k * 0.6), topo, (210, 200, 170), sobre=True)

    def desenhar(self, tela, ctx, J):
        H = self.H
        vento = 0.03 * math.sin(ctx.a) + (0.05 if ctx.golpe else 0)
        capa(tela, J, self.capa_mat, comprimento=0.5, vento=vento, larg=0.15, rasgos=5, semente=21,
             forro=Mat((90, 30, 40), 5))
        braco(tela, J, "b", self.gibao.escuro(1), PELE, punho=COURO_ESC)
        perna(tela, J, "b", Mat((40, 36, 48), 5).escuro(1), COURO_ESC.escuro(1), cano=0.75)
        perna(tela, J, "f", Mat((40, 36, 48), 5), COURO_ESC, cano=0.75)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        saia = tela.poly(Q.pts([(-0.08 * H, 0.04 * H), (0.075 * H, 0.04 * H), (0.085 * H, -0.12 * H),
                                (0.02 * H, -0.1 * H), (-0.085 * H, -0.12 * H)]))
        tela.pintar(saia, self.gibao)
        tronco(tela, J, self.gibao, cintura=0.115, peito=0.17)
        for k in range(4):                    # botões e debrum dourado
            tela.px(*Q.pt(0.03 * H, T * (0.2 + k * 0.18)), OURO_VELHO[3])
        tela.traco(Q.pt(0.045 * H, T * 0.05), Q.pt(0.05 * H, T * 0.95), OURO_VELHO[2], sobre=True)
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO)
        if self.armado:
            self.alaude(tela, J, ctx)
        pescoco(tela, J, PELE, 0.03)
        # gola de babado
        tela.pintar(tela.elipse_girada(J["pescoco"] + J["u"] * 1, H * 0.06, H * 0.025, 0), LINHO.claro(1))
        cab, C = cabeca_base(tela, J, PELE)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.pintar(tela.poly(C.pts([(-w * 0.5, h * 0.2), (-w * 0.6, -h * 0.5), (-w * 0.2, -h * 0.3),
                                     (-w * 0.1, h * 0.3)])), CABELO_PRETO)
        olho(tela, C, w * 0.35, h * 0.05, (20, 12, 16), emite=False)
        tela.traco(C.pt(w * 0.32, -h * 0.25), C.pt(w * 0.5, -h * 0.2), (90, 40, 40))       # sorriso torto
        tela.traco(C.pt(w * 0.15, -h * 0.28), C.pt(w * 0.4, -h * 0.4), (40, 26, 30))       # cavanhaque
        # chapéu de aba larga com pluma
        aba = tela.elipse_girada(C.pt(w * 0.05, h * 0.42), w * 1.15, h * 0.16, math.atan2(J["hu"][0], -J["hu"][1]))
        copa = tela.poly(C.pts([(-w * 0.45, h * 0.4), (-w * 0.3, h * 0.95), (w * 0.35, h * 0.9), (w * 0.45, h * 0.4)]))
        tela.pintar(copa | aba, self.chapeu)
        tela.traco(C.pt(-w * 0.4, h * 0.5), C.pt(w * 0.42, h * 0.5), OURO_VELHO[2], sobre=True)
        s = math.sin(ctx.a)
        pluma = [C.pt(-w * 0.2, h * 0.7), C.pt(-w * 0.9, h * 1.3 + s * 0.5), C.pt(-w * 1.6, h * 1.0 + s), C.pt(-w * 1.9, h * 0.4 + s)]
        tela.pintar(tela.corrente(pluma, [1.8, 2.2, 1.6, 0.6]), Mat((170, 30, 40), 5, relevo=0.6))
        braco(tela, J, "f", self.gibao, PELE, punho=COURO_ESC)
        # notas musicais no ataque (e uma de vez em quando parado)
        if ctx.anim == "ataque" and ctx.i in (1, 2, 3):
            for k in range(3):
                p = J["mao_f"] + v2(6 + k * 7 + ctx.i * 3, -4 - k * 4 + (k % 2) * 6)
                nota_musical(tela, p, fx.FOGO_ROXO[3] if k % 2 else (240, 220, 140))
            tela.brilho(J["mao_f"] + v2(10, -6), 9, (200, 150, 255), 0.5)
        elif ctx.anim == "parado" and ctx.i == 2:
            nota_musical(tela, J["topo"] + v2(8, -4), (220, 200, 140))
        morte_extras(tela, self, ctx, J)


# ============================================================
# TAVERNEIRO — barrigudo, careca, avental e caneca
# ============================================================

class Taverneiro(Modelo):
    """Linha extra opcional "servir" (6 quadros, só nas folhas que a pedem em animacoes_extras): enche a caneca
    com a jarra da mão de trás, a espuma sobe e transborda, e ele ergue a caneca."""

    nome = "taverneiro"
    H = 76
    estilo = "garra"
    prop = dict(ombros=0.27, quadris=0.22, l_coxa=0.06, l_canela=0.045, l_braco=0.042, l_antebraco=0.038)
    base = dict(braco_f=(0.45, 1.5), braco_b=(0.2, 0.4), pe_f=(-0.08, 0), pe_b=(0.09, 0))
    # servir, quadro a quadro: (mão de trás em px a partir da caneca, ou None = jarra baixa; braço da frente;
    # inclinação da jarra, negativa = bico para a esquerda; espuma: 0 vazia .. 3 transbordando)
    SERVIR = ((None, (0.45, 1.5), 0.0, 0), ((6, -7), (0.5, 1.4), -0.4, 0), ((9, -10), (0.5, 1.4), -1.6, 1),
              ((9, -11), (0.5, 1.4), -1.9, 2), ((7, -6), (0.48, 1.45), -0.6, 3), (None, (0.35, 1.85), 0.0, 3))

    def pose(self, ctx):
        if ctx.anim != "servir":
            return super().pose(ctx)
        tras, frente, _, _ = self.SERVIR[ctx.i]
        p = idle(self.pose_base(), ctx.i % 4, amp=0.5)
        p.update(braco_f=frente, tronco=0.03 if ctx.i in (2, 3) else 0.0)
        if tras is None:
            p["braco_b"] = (0.25, 0.45)
        else:                                             # a mão de trás leva a jarra até a boca da caneca (IK)
            caneca = self.esqueleto(p)["mao_f"]
            p["alvo_b"] = (caneca[0] + tras[0], caneca[1] + tras[1])
        return p

    def jarra(self, tela, J, inclina):
        """Jarra de barro na mão de trás; inclinada, derrama um fio de cerveja até a caneca."""
        m = J["mao_b"]
        d = v2(math.sin(inclina), -math.cos(inclina))          # para onde aponta o bico
        n = v2(-d[1], d[0])
        corpo = m + d * 2
        tela.pintar(tela.elipse_girada(corpo, 3.6, 4.6, math.atan2(d[1], d[0]) + math.pi / 2), Mat((150, 86, 56), 5, relevo=1.0))
        tela.pintar(tela.capsula(corpo + d * 4, corpo + d * 6.5, 1.6, 1.4), Mat((150, 86, 56), 5).escuro(1))
        tela.traco(corpo - n * 3, corpo - n * 3 + d * 3, Mat((150, 86, 56), 5)[0])          # alça
        return corpo + d * 7

    @staticmethod
    def encher(tela, m, bico, servir):
        """A boca da caneca no "servir": vazia, cerveja subindo, espuma e espuma escorrendo; o fio da jarra."""
        _, _, inclina, espuma = servir
        if abs(inclina) >= 1.0:
            tela.traco(bico, v2(m[0] + 2, m[1] - 6), (226, 156, 54))
        if espuma == 0:
            tela.chapado(tela.elipse(m[0] + 2, m[1] - 6, 2.6, 0.9), (44, 28, 22))
        elif espuma == 1:
            tela.chapado(tela.elipse(m[0] + 2, m[1] - 6, 2.8, 1.0), (206, 132, 44))
        else:
            tela.pintar(tela.elipse(m[0] + 2, m[1] - 7 - (espuma - 2) * 0.8, 3.5 + (espuma - 2) * 0.6,
                                    1.6 + (espuma - 2) * 0.5), LINHO.claro(2))
        if espuma == 3:
            tela.traco(m + v2(5, -7), m + v2(5.5, -3), LINHO.claro(2)[3], sobre=True)                 # escorrendo

    def desenhar(self, tela, ctx, J):
        H = self.H
        camisa = Mat((104, 36, 40), 6, ruido=0.15)
        braco(tela, J, "b", camisa.escuro(1), PELE, grossura=1.1)
        perna(tela, J, "b", Mat((70, 52, 40), 5).escuro(1), COURO_ESC.escuro(1), grossura=1.15)
        perna(tela, J, "f", Mat((70, 52, 40), 5), COURO_ESC, grossura=1.15)
        tronco(tela, J, camisa, cintura=0.18, peito=0.2, barriga=0.06)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        avental = tela.poly(Q.pts([(-0.04 * H, T * 0.7), (0.07 * H, T * 0.7), (0.14 * H, T * 0.3), (0.1 * H, -0.2 * H),
                                   (-0.06 * H, -0.2 * H)]))
        tela.pintar(avental, LINHO)
        tela.pintar(tela.circulo(Q.pt(0.08 * H, -0.06 * H), 2.2), Mat((110, 40, 36), 4))   # mancha de vinho
        cinto(tela, J, COURO, altura=0.08)
        pescoco(tela, J, PELE, 0.05)
        cab, C = cabeca_base(tela, J, PELE, larg=0.56)
        h = J["P"]["cabeca"]
        w = h * 0.9
        barba_escura = Mat((62, 40, 30), 5, ruido=0.5)
        barba(tela, J, barba_escura, comprimento=0.8, largura=0.62)
        tela.traco(C.pt(w * 0.15, -h * 0.05), C.pt(w * 0.55, -h * 0.08), barba_escura[1])        # bigode
        olho(tela, C, w * 0.35, h * 0.12, (30, 20, 20), emite=False)
        tela.traco(C.pt(w * 0.25, h * 0.22), C.pt(w * 0.45, h * 0.2), CABELO_CASTANHO[0])       # sobrancelha
        tela.px(*C.pt(w * 0.0, h * 0.35), PELE[4])                                                 # brilho da careca
        servir = self.SERVIR[ctx.i] if ctx.anim == "servir" else None
        bico = self.jarra(tela, J, servir[2]) if servir is not None else None
        # caneca na mão da frente (com espuma)
        m = J["mao_f"]
        caneca = tela.poly([m + v2(-1, -6), m + v2(5, -6), m + v2(5, 2), m + v2(-1, 2)])
        tela.pintar(caneca, MADEIRA)
        tela.traco(m + v2(-1, -3), m + v2(5, -3), FERRO[2], sobre=True)
        if servir is None:
            tela.pintar(tela.elipse(m[0] + 2, m[1] - 7, 3.5, 1.6), LINHO.claro(2))
        else:
            self.encher(tela, m, bico, servir)
        braco(tela, J, "f", camisa, PELE, grossura=1.1)
        morte_extras(tela, self, ctx, J)


# ============================================================
# CAPITÃ — veterana de couraça, casaco vermelho e lança-estandarte
# ============================================================

class Capita(Modelo):
    nome = "capita"
    H = 76
    estilo = "estocada"
    prop = dict(ombros=0.23, quadris=0.19)
    base = dict(braco_f=(0.25, 0.9), braco_b=(0.55, 0.9), arma_f=-0.05, pe_f=(-0.07, 0), pe_b=(0.09, 0))
    casaco = Mat((112, 24, 30), 6, desce=0.35, ruido=0.1, relevo=0.7)

    def desenhar(self, tela, ctx, J):
        H = self.H
        vento = 0.03 * math.sin(ctx.a)
        capa(tela, J, self.casaco.escuro(1), comprimento=0.62, vento=vento, larg=0.14, rasgos=6, semente=31)
        braco(tela, J, "b", self.casaco.escuro(1), COURO_ESC, punho=ACO.escuro(1))
        perna(tela, J, "b", Mat((50, 44, 54), 5).escuro(1), COURO_ESC.escuro(1), cano=0.75)
        perna(tela, J, "f", Mat((50, 44, 54), 5), COURO_ESC, cano=0.75)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        aba = tela.poly(Q.pts([(-0.09 * H, 0.03 * H), (0.08 * H, 0.03 * H), (0.1 * H, -0.2 * H), (0.04 * H, -0.17 * H),
                               (-0.1 * H, -0.2 * H)]))
        tela.pintar(aba, self.casaco)
        tronco(tela, J, self.casaco, cintura=0.115, peito=0.17)
        peitoral = tela.poly(Q.pts([(-0.05 * H, T * 0.1), (0.06 * H, T * 0.1), (0.07 * H, T * 0.78), (-0.05 * H, T * 0.78)]))
        tela.pintar(peitoral & tela.mascara(), ACO, linha_interna=False)
        tela.traco(Q.pt(0.02 * H, T * 0.2), Q.pt(0.025 * H, T * 0.7), ACO[1], sobre=True)
        # faixa de oficial
        tela.traco(Q.pt(-0.06 * H, T * 0.9), Q.pt(0.07 * H, T * 0.05), OURO_VELHO[3], sobre=True)
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO)
        pescoco(tela, J, PELE, 0.03)
        cab, C = cabeca_base(tela, J, PELE)
        h = J["P"]["cabeca"]
        w = h * 0.82
        cabelo = tela.poly(C.pts([(-w * 0.55, h * 0.35), (w * 0.2, h * 0.56), (w * 0.5, h * 0.3), (w * 0.2, h * 0.3),
                                  (-w * 0.3, h * 0.0), (-w * 0.75, -h * 0.9), (-w * 0.9, -h * 0.4)]))
        tela.pintar(cabelo, CABELO_PRETO.claro(1))
        olho(tela, C, w * 0.35, h * 0.06, (40, 30, 30), emite=False)
        tela.traco(C.pt(w * 0.15, h * 0.25), C.pt(w * 0.3, -h * 0.15), (150, 80, 70))          # cicatriz
        # lança com estandarte
        mf = J["mao_f"]
        ang = math.pi / 2 + J["arma_f"] - 1.55 if ctx.anim != "ataque" else J["arma_f"]
        armas.lanca(tela, mf, ang, H * 0.45, MADEIRA, ACO, atras=H * 0.5)
        if ctx.anim == "parado":
            d = dir_ang(ang)
            topo = mf + d * H * 0.38
            s = math.sin(ctx.a)
            bandeira = [topo, topo + v2(-14, 1 + s), topo + v2(-13, 9 + s * 1.5), topo + v2(-2, 8)]
            tela.pintar(tela.poly(bandeira), Mat((120, 24, 30), 5, relevo=0.5))
            tela.px(*(topo + v2(-7, 4)), OURO_VELHO[3])
        braco(tela, J, "f", self.casaco, COURO_ESC, punho=ACO)
        golpe_rastro(tela, ctx, J, H * 0.6, -0.2, 0.3)
        morte_extras(tela, self, ctx, J)


# ============================================================
# MERCADOR — corcunda encapuzado com mochila enorme e lanterna
# ============================================================

class Mercador(Modelo):
    nome = "mercador"
    H = 70
    estilo = "garra"
    prop = dict(ombros=0.22, quadris=0.19)
    base = dict(braco_f=(0.5, 0.9), braco_b=(0.3, 0.6), arma_f=0.0, pe_f=(-0.07, 0), pe_b=(0.08, 0),
                tronco=0.25, cabeca=0.2)
    manto_mat = Mat((70, 62, 50), 6, desce=0.35, ruido=0.2, relevo=0.7)
    remendo = Mat((104, 74, 50), 5, ruido=0.3)
    cachecol = Mat((128, 42, 36), 5, relevo=0.6)
    cobertor = Mat((58, 78, 88), 5, relevo=0.8)

    def mochila(self, tela, J):
        """Mochila enorme nas costas: cobertor enrolado em cima, panela e pergaminho pendurados."""
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        costas = Q.pt(-0.12 * H, T * 0.55)
        tela.pintar(tela.elipse_girada(costas, H * 0.14, H * 0.18, 0.2), COURO.claro(1))
        for k in range(3):                    # correias
            tela.traco(costas + v2(-7, -4 + k * 6), costas + v2(7, -4 + k * 6), COURO_ESC[1], sobre=True)
        rolo = costas + v2(1, -H * 0.17)
        tela.pintar(tela.capsula(rolo + v2(-8, 0), rolo + v2(8, -2), 3.2), self.cobertor)
        tela.traco(rolo + v2(-3, -3), rolo + v2(-3, 3), COURO_ESC[1], sobre=True)
        tela.traco(rolo + v2(4, -4), rolo + v2(4, 2), COURO_ESC[1], sobre=True)
        tela.pintar(tela.circulo(costas + v2(-9, 6), H * 0.045), FERRO.escuro(1))                     # panela
        tela.pintar(tela.capsula(costas + v2(6, -10), costas + v2(9, -17), 1.5), LINHO.claro(1))      # pergaminho

    def lanterna(self, tela, J, ctx):
        """Cajado de caminhada na mão da frente, com a lanterna pendurada num gancho na ponta."""
        H = self.H
        mf = J["mao_f"]
        ang = 0.25 + J["arma_f"]
        base, topo = armas.haste(tela, mf, ang, H * 0.26, H * 0.3, MADEIRA, larg=1.1)
        d = dir_ang(ang)
        gancho = topo + v2(5, 1)
        tela.traco(topo, gancho, FERRO[2])
        balanco = math.sin(ctx.a) * 1.0
        lamp = gancho + v2(balanco, 8)
        tela.traco(gancho, lamp + v2(0, -4), FERRO[1])
        tela.pintar(tela.poly([lamp + v2(-3, -4), lamp + v2(3, -4), lamp + v2(3.5, 4), lamp + v2(-3.5, 4)]), FERRO)
        tela.chapado(tela.poly([lamp + v2(-2, -3), lamp + v2(2, -3), lamp + v2(2.5, 3), lamp + v2(-2.5, 3)]),
                     (255, 206, 110), emite=True)
        tela.pintar(tela.poly([lamp + v2(-4, -4), lamp + v2(4, -4), lamp + v2(0, -7)]), FERRO.escuro(1))
        tela.brilho(lamp, 12 + math.sin(ctx.a * 2) * 1.5, (255, 170, 80), 0.65)
        return d

    def desenhar(self, tela, ctx, J):
        H = self.H
        Q = quadro_tronco(J)
        self.mochila(tela, J)
        braco(tela, J, "b", self.manto_mat.escuro(1), PELE_PALIDA, grossura=1.25)
        perna(tela, J, "b", COURO_ESC, COURO_ESC.escuro(1), cano=0.5)
        perna(tela, J, "f", COURO_ESC, COURO_ESC, cano=0.5)
        manto(tela, J, self.manto_mat, folga=0.08, rasgos=5, semente=41, barra=0.04)
        remendo = tela.poly(Q.pts([(0.0, -0.2 * H), (0.06 * H, -0.19 * H), (0.055 * H, -0.27 * H), (0.005 * H, -0.28 * H)]))
        tela.pintar(remendo & tela.mascara(), self.remendo, linha_interna=False)
        for k in range(3):                    # pontos de costura do remendo
            tela.px(*Q.pt((0.01 + k * 0.02) * H, -0.2 * H), (40, 30, 24))
        cinto(tela, J, COURO_ESC, fivela=LATAO, altura=0.02)
        for k in range(3):                    # bolsinhas e moedas
            p = Q.pt((-0.05 + k * 0.045) * H, -0.03 * H)
            tela.pintar(tela.circulo(p, 2.2), COURO.claro(1) if k != 1 else LATAO)
        _, C, face = capuz(tela, J, self.manto_mat.claro(1), ponta=0.4)
        h = J["P"]["cabeca"]
        w = h * 0.95
        olho(tela, C, w * 0.38, h * 0.0, (250, 210, 120), brilho=(250, 200, 100))
        tela.pintar(tela.poly(C.pts([(w * 0.45, -h * 0.05), (w * 0.85, -h * 0.25), (w * 0.5, -h * 0.3)])), PELE_PALIDA)  # nariz
        # cachecol vermelho com a ponta caindo para trás
        pesc = J["pescoco"]
        tela.pintar(tela.elipse_girada(pesc + J["u"] * 1, H * 0.075, H * 0.03, 0.1), self.cachecol)
        s = math.sin(ctx.a)
        tela.pintar(tela.corrente([pesc + v2(-3, 1), pesc + v2(-7, 6 + s * 0.5), pesc + v2(-9, 12 + s)], [2.2, 2.0, 1.4]),
                    self.cachecol.escuro(1))
        self.lanterna(tela, J, ctx)
        braco(tela, J, "f", self.manto_mat, PELE_PALIDA, grossura=1.25)
        morte_extras(tela, self, ctx, J)

# ============================================================
# ALQUIMISTA — óculos de latão, avental queimado e frasco borbulhando
# ============================================================

class Alquimista(Modelo):
    nome = "alquimista"
    H = 74
    estilo = "magia"
    prop = dict(ombros=0.22)
    base = dict(braco_f=(0.65, 1.3), braco_b=(0.2, 0.5), arma_f=0.05, pe_f=(-0.06, 0), pe_b=(0.07, 0))
    tunica = Mat((70, 60, 92), 6, desce=0.4, ruido=0.12)

    def desenhar(self, tela, ctx, J):
        H = self.H
        braco(tela, J, "b", self.tunica.escuro(1), PELE_PALIDA, punho=COURO_ESC)
        perna(tela, J, "b", COURO_ESC, COURO_ESC.escuro(1), cano=0.5)
        perna(tela, J, "f", COURO_ESC, COURO_ESC, cano=0.5)
        manto(tela, J, self.tunica, folga=0.05, rasgos=4, semente=51, barra=0.02)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        avental = tela.poly(Q.pts([(-0.03 * H, T * 0.75), (0.07 * H, T * 0.75), (0.1 * H, -0.3 * H), (-0.05 * H, -0.3 * H)]))
        tela.pintar(avental & tela.mascara(), COURO, linha_interna=False)
        for k in range(3):                    # queimaduras no avental
            tela.px(*Q.pt((0.0 + k * 0.025) * H, -0.1 * H - k * 3), (40, 24, 20))
        cinto(tela, J, COURO_ESC, fivela=LATAO, altura=0.0)
        for k, cor in enumerate(((120, 220, 90), (220, 80, 80), (90, 150, 230))):       # frascos no cinto
            p = Q.pt((-0.06 + k * 0.04) * H, -0.04 * H)
            tela.pintar(tela.capsula(p, p + v2(0, 3), 1.4), Mat(cor, 4))
        pescoco(tela, J, PELE_PALIDA, 0.03)
        cab, C = cabeca_base(tela, J, PELE_PALIDA)
        h = J["P"]["cabeca"]
        w = h * 0.82
        # cabelo branco arrepiado
        for k in range(6):
            a = 1.0 + k * 0.35
            base = C.pt(-w * 0.2, h * 0.3)
            tela.traco(base, base + dir_ang(math.pi + a) * (5 + k % 2 * 2), CABELO_GRISALHO[3 - k % 2])
        # óculos de latão na testa e um olho arregalado
        for x in (w * 0.2, w * 0.5):
            tela.pintar(tela.circulo(C.pt(x, h * 0.35), 2.2), LATAO)
            tela.px(*C.pt(x, h * 0.35), (120, 200, 210), emite=True)
        olho(tela, C, w * 0.38, h * 0.04, (240, 240, 220), emite=False)
        tela.traco(C.pt(w * 0.3, -h * 0.28), C.pt(w * 0.5, -h * 0.26), (80, 50, 50))
        # frasco borbulhando na mão
        m = J["mao_f"]
        frasco = tela.circulo(m + v2(2, -4), 4.0) | tela.capsula(m + v2(2, -7), m + v2(2, -11), 1.2)
        tela.pintar(frasco, Mat((140, 170, 160), 5, especular=(230, 255, 240)))
        tela.chapado(tela.circulo(m + v2(2, -3), 2.8), (110, 220, 90), emite=True)
        for k in range(3):
            t = (ctx.i / 4 + k / 3) % 1
            tela.px(m[0] + 2 + math.sin(k * 2 + ctx.a) * 2, m[1] - 12 - t * 10, (170, 255, 140), emite=True)
        tela.brilho(m + v2(2, -4), 8, (120, 230, 90), 0.55)
        braco(tela, J, "f", self.tunica, PELE_PALIDA, punho=COURO_ESC)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            fx.fumaca(tela, J["mao_b"] + v2(8, -2), 5, cor=(110, 200, 90), fase=ctx.a, n=4, sobe=8)
        morte_extras(tela, self, ctx, J)


# ============================================================
# NECROMANTE — máscara de crânio, manto negro e cajado de chama verde
# ============================================================

class Necromante(Modelo):
    nome = "necromante"
    H = 80
    estilo = "magia"
    prop = dict(ombros=0.21, l_coxa=0.04, l_canela=0.032)
    base = dict(braco_f=(0.65, 0.8), braco_b=(0.2, 0.7), arma_f=0.05, pe_f=(-0.05, 0), pe_b=(0.07, 0))
    manto_mat = Mat((34, 30, 40), 6, desce=0.45, ruido=0.12, relevo=0.7, arredonda=0.6)

    def manga(self, tela, J, lado, mat):
        braco(tela, J, lado, mat, None, grossura=1.25)
        c, m = J["cotovelo_" + lado], J["mao_" + lado]
        d = norm(m - c)
        n = v2(-d[1], d[0])
        p0 = lerp(c, m, 0.35)
        tela.pintar(tela.poly([p0 + n * 2, m + n * 4.4, m - n * 4.4 + d, p0 - n * 2]), mat)
        tela.pintar(tela.circulo(m + d * 1.2, self.H * 0.024), OSSO.escuro(1))

    def desenhar(self, tela, ctx, J):
        H = self.H
        mt = self.manto_mat
        vento = 0.04 * math.sin(ctx.a) + (0.05 if ctx.golpe else 0)
        capa(tela, J, mt.escuro(1), comprimento=0.7, vento=vento, larg=0.17, rasgos=9, semente=61)
        self.manga(tela, J, "b", mt.escuro(1))
        perna(tela, J, "b", mt.escuro(2), mt.escuro(2), cano=0.4)
        perna(tela, J, "f", mt.escuro(1), mt.escuro(1), cano=0.4)
        manto(tela, J, mt, folga=0.08, rasgos=8, semente=62, barra=-0.01)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        for k in range(4):                     # colar de dedos
            tela.px(*Q.pt((-0.03 + k * 0.025) * H, T * 0.85), OSSO[3])
        cinto(tela, J, COURO_ESC, fivela=OSSO, altura=0.02)
        _, C, face = capuz(tela, J, mt, ponta=0.65)
        h = J["P"]["cabeca"]
        w = h * 0.95
        mascara = tela.poly(C.pts([(w * 0.08, h * 0.3), (w * 0.6, h * 0.22), (w * 0.6, -h * 0.45), (w * 0.15, -h * 0.5)]))
        tela.pintar(mascara & face, OSSO, linha_interna=False)
        for x in (w * 0.28, w * 0.5):
            tela.chapado(tela.circulo(C.pt(x, h * 0.04), 1.3), (10, 6, 10))
            tela.px(*C.pt(x, h * 0.04), (120, 255, 140), emite=True)
        for k in range(3):
            tela.px(*C.pt(w * (0.25 + k * 0.12), -h * 0.32), (20, 14, 18))
        # cajado com crânio e chama verde
        mf = J["mao_f"]
        topo = armas.cajado(tela, mf, J["arma_f"], H * 0.4, Mat((60, 50, 46), 5, ruido=0.3), atras=H * 0.5, torto=1.5)
        tela.pintar(tela.circulo(topo + v2(0, -2), 3.2), OSSO)
        tela.px(topo[0] + 1, topo[1] - 2, (10, 6, 10))
        tela.px(topo[0] - 1, topo[1] - 2, (10, 6, 10))
        fx.chama(tela, topo + v2(0, -5), 10 + 2 * math.sin(ctx.a * 2), 7, fx.FOGO_VERDE, fase=ctx.a * 2)
        self.manga(tela, J, "f", mt)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            fx.orbe(tela, J["mao_b"] + v2(6, -3), 3.5, fx.FOGO_VERDE)
            for k in range(3):
                fx.runa(tela, J["mao_b"] + v2(10 + k * 6, -10 + k * 5), (120, 255, 150), 2, forma=k)
        morte_extras(tela, self, ctx, J)


# ============================================================
# MESTRE — veterano grisalho, tapa-olho e montante apoiado no chão
# ============================================================

class Mestre(Modelo):
    nome = "mestre"
    H = 76
    estilo = "corte"
    base = dict(braco_f=(0.15, 0.6), braco_b=(0.3, 0.5), arma_f=0.3, pe_f=(-0.07, 0), pe_b=(0.09, 0))
    casaco = Mat((64, 52, 44), 6, desce=0.3, ruido=0.15)

    def desenhar(self, tela, ctx, J):
        H = self.H
        capa(tela, J, Mat((44, 40, 50), 6, desce=0.3), comprimento=0.6, vento=0.03 * math.sin(ctx.a), rasgos=6, semente=71)
        braco(tela, J, "b", self.casaco.escuro(1), PELE, punho=COURO_ESC)
        perna(tela, J, "b", MALHA.escuro(1), COURO_ESC.escuro(1), cano=0.65)
        perna(tela, J, "f", MALHA, COURO_ESC, cano=0.65)
        Q = quadro_tronco(J)
        aba = tela.poly(Q.pts([(-0.085 * H, 0.03 * H), (0.08 * H, 0.03 * H), (0.1 * H, -0.24 * H), (-0.1 * H, -0.24 * H)]))
        tela.pintar(aba, self.casaco)
        tronco(tela, J, self.casaco, cintura=0.12, peito=0.18)
        cinto(tela, J, COURO_ESC, fivela=FERRO)
        pescoco(tela, J, PELE, 0.035)
        cab, C = cabeca_base(tela, J, PELE.escuro(1))
        h = J["P"]["cabeca"]
        w = h * 0.82
        barba(tela, J, CABELO_GRISALHO, comprimento=0.7)
        tela.pintar(tela.poly(C.pts([(-w * 0.5, h * 0.3), (w * 0.3, h * 0.55), (w * 0.2, h * 0.35), (-w * 0.5, -h * 0.1)])),
                    CABELO_GRISALHO)
        # tapa-olho
        tela.traco(C.pt(-w * 0.3, h * 0.3), C.pt(w * 0.6, h * 0.0), (30, 22, 20))
        tela.pintar(tela.circulo(C.pt(w * 0.4, h * 0.06), 1.6), Mat((30, 22, 20), 4))
        # montante: ataque é um corte, parado fica apoiado
        mf = J["mao_f"]
        ang = J["arma_f"] if ctx.anim == "ataque" else 3.0
        armas.espada(tela, mf, ang, H * 0.62, ACO.claro(1), FERRO, COURO_ESC, larg=1.8, pomo=FERRO)
        braco(tela, J, "f", self.casaco, PELE, punho=COURO_ESC)
        golpe_rastro(tela, ctx, J, H * 0.8, -1.2, 2.0)
        morte_extras(tela, self, ctx, J)


# ============================================================
# BOBO DA CORTE (herói) — o bobo do circo, mas do lado dos vivos
# ============================================================

from .novos import Bobo as _BoboDoCirco


class BoboDaCorte(_BoboDoCirco):
    """Herói jogável: mesmo corpo e animações do bobo do circo, com roupa roxa e ocre,
    meia-máscara (o sorriso é dele mesmo) e bolas de malabares girando quando parado."""

    nome = "bobo"
    tipo = "heroi"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "bobo")
        self.cor_a = kw.get("cor_a", Mat((86, 40, 112), 6, ruido=0.15))
        self.cor_b = kw.get("cor_b", Mat((172, 132, 58), 6, ruido=0.15))

    def cabeca(self, tela, J, ctx):
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.85
        A, B = self.cor_a, self.cor_b
        s = math.sin(ctx.a)
        cabeca_base(tela, J, PELE)
        # chapéu de duas pontas caídas com guizos
        for base, meio, ponta, mat in (((-w * 0.2, h * 0.5), (-w * 1.2 + s * 0.4, h * 0.6), (-w * 1.3 + s * 0.6, -h * 0.1), A),
                                       ((w * 0.3, h * 0.5), (w * 1.0 - s * 0.4, h * 1.0), (w * 1.25 - s * 0.6, h * 0.45), B)):
            pts = [C.pt(*base), C.pt(*meio), C.pt(*ponta)]
            tela.pintar(tela.corrente(pts, [h * 0.32, h * 0.2, h * 0.08]), mat)
            tela.pintar(tela.circulo(C.pt(*ponta), 1.4), OURO_VELHO)
        tela.pintar(tela.poly(C.pts([(-w * 0.5, h * 0.25), (w * 0.5, h * 0.3), (w * 0.4, h * 0.62), (-w * 0.45, h * 0.58)])), B)
        # meia-máscara branca nos olhos; embaixo, o rosto e o sorriso de verdade
        mascara = Mat((226, 220, 212), 6, satur=0.2)
        tela.pintar(tela.poly(C.pts([(-w * 0.2, h * 0.28), (w * 0.45, h * 0.3), (w * 0.62, h * 0.05), (w * 0.5, -h * 0.08),
                                     (w * 0.05, -h * 0.05)])), mascara)
        olho(tela, C, w * 0.38, h * 0.1, (30, 16, 40), emite=False)
        tela.px(*C.pt(w * 0.5, h * 0.2), A[3])                                       # losango pintado na máscara
        tela.tracos([C.pt(w * 0.15, -h * 0.28), C.pt(w * 0.35, -h * 0.36), C.pt(w * 0.55, -h * 0.26)], (110, 40, 40))

    def desenhar(self, tela, ctx, J):
        super().desenhar(tela, ctx, J)
        if self.armado and ctx.anim == "parado":  # três bolas de malabares girando sobre a mão de trás
            centro = J["mao_b"] + v2(2, -16)
            for k, cor in enumerate(((200, 60, 60), (230, 200, 90), (110, 90, 200))):
                ang = ctx.a * 1.0 + k * 2.094
                p = centro + v2(math.cos(ang) * 6, math.sin(ang) * 4)
                tela.pintar(tela.circulo(p, 1.8), Mat(cor, 4, especular=(255, 250, 230)))


# ============================================================
# ESTUDIOSO DO BESTIÁRIO — velho erudito curvado sobre um tomo de monstros
# ============================================================

class Estudioso(Modelo):
    """O Estudioso do bestiário: velho erudito um pouco curvado, de casaco longo de lã verde-escura com capeleta, bolsa
    de pergaminhos a tiracolo, vidros de espécimes no cinto (um olho e um dente), colar de presas, óculos redondos,
    barba branca curta e uma pena atrás da orelha; lê um tomo grosso com cantoneiras de ferro e fita de marcar.

    Linha extra opcional "folhear" (6 quadros, só nas folhas que a pedem): a folha da direita sobe, passa por cima da
    lombada e deita do outro lado; o bicho desenhado muda e ele inclina a cabeça para ler."""

    nome = "estudioso"
    H = 72
    estilo = "magia"
    prop = dict(ombros=0.21)
    base = dict(braco_f=(0.9, 1.6), braco_b=(0.6, 1.5), arma_f=0.0, pe_f=(-0.06, 0), pe_b=(0.07, 0), tronco=0.1, cabeca=0.08)
    casaco = Mat((62, 82, 68), 6, desce=0.35, ruido=0.22, relevo=0.8)
    capeleta = Mat((58, 50, 60), 6, ruido=0.12, relevo=0.7)
    VIRADA = (0.0, 0.5, 1.3, 2.1, 2.8, math.pi)            # ângulo da folha em cada quadro do "folhear"

    def pose(self, ctx):
        if ctx.anim != "folhear":
            return super().pose(ctx)
        p = idle(self.pose_base(), 0)
        p["cabeca"] = 0.02 if ctx.i in (0, 5) else 0.14
        return p

    @staticmethod
    def folha_virando(tela, m, angulo):
        """A folha presa na lombada, girando de deitada à direita (0) até deitada à esquerda (pi)."""
        ponta = 8 * math.cos(angulo)
        ergue = 5 * math.sin(angulo)
        folha = tela.poly([m + v2(0, -4), m + v2(ponta, -4 - ergue), m + v2(ponta, 3 - ergue), m + v2(0, 3)])
        tela.chapado(folha, (236, 224, 192))
        tela.traco(m + v2(ponta, -4 - ergue), m + v2(ponta, 3 - ergue), (170, 150, 116))

    def desenhar(self, tela, ctx, J):
        H = self.H
        calca = Mat((54, 48, 50), 5)
        braco(tela, J, "b", self.casaco.escuro(1), PELE_PALIDA, punho=LINHO)
        perna(tela, J, "b", calca.escuro(1), COURO_ESC.escuro(1), cano=0.45)
        perna(tela, J, "f", calca, COURO_ESC, cano=0.45)
        self.bolsa(tela, J)
        manto(tela, J, self.casaco, folga=0.06, rasgos=2, semente=91, barra=-0.03)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        tela.traco(Q.pt(0.045 * H, T * 0.9), Q.pt(0.05 * H, -0.3 * H), self.casaco[1], sobre=True)        # abertura do casaco
        tela.traco(Q.pt(-0.07 * H, T * 0.95), Q.pt(0.06 * H, T * 0.05), COURO_ESC[2], sobre=True)          # alça da bolsa
        cinto(tela, J, COURO_ESC, fivela=LATAO, altura=0.04)
        self.vidros(tela, J, ctx)
        # capeleta sobre os ombros e o colar de presas
        capeleta = tela.poly(Q.pts([(-0.1 * H, T * 1.03), (0.08 * H, T * 1.02), (0.11 * H, T * 0.62), (0.0, T * 0.55),
                                    (-0.11 * H, T * 0.6)]))
        tela.pintar(capeleta, self.capeleta)
        tela.traco(Q.pt(-0.1 * H, T * 0.6), Q.pt(0.11 * H, T * 0.62), self.capeleta[4], sobre=True)
        for k in range(4):
            p = Q.pt((0.0 + k * 0.022) * H, T * (0.78 - k * 0.03))
            tela.chapado(tela.poly([p + v2(-1, 0), p + v2(1, 0), p + v2(0, 2.5)]), (232, 222, 196))
        pescoco(tela, J, PELE_PALIDA, 0.03)
        cab, C = cabeca_base(tela, J, PELE_PALIDA)
        h = J["P"]["cabeca"]
        w = h * 0.82
        branco = Mat((214, 210, 204), 5, ruido=0.4)
        tela.pintar(tela.poly(C.pts([(-w * 0.6, h * 0.2), (-w * 0.2, h * 0.32), (-w * 0.05, -h * 0.05), (-w * 0.45, -h * 0.45),
                                     (-w * 0.68, -h * 0.1)])), branco)                                  # cabelo só dos lados
        barba(tela, J, branco, comprimento=0.3, largura=0.6)
        tela.traco(C.pt(w * 0.18, h * 0.24), C.pt(w * 0.56, h * 0.2), (226, 222, 216))                # sobrancelha cerrada
        olho(tela, C, w * 0.5, h * 0.08, (30, 30, 40), emite=False)
        for x in (w * 0.3, w * 0.56):                                                                 # óculos: só o aro
            tela.px(*C.pt(x - w * 0.08, h * 0.08), (140, 110, 60))
            tela.px(*C.pt(x + w * 0.08, h * 0.08), (140, 110, 60))
        tela.traco(C.pt(w * 0.22, h * 0.14), C.pt(w * 0.64, h * 0.14), (140, 110, 60))
        pena = [C.pt(-w * 0.2, h * 0.18), C.pt(-w * 0.5, h * 0.42), C.pt(-w * 0.78, h * 0.5)]            # atrás da orelha
        tela.tracos(pena, (200, 194, 180))
        tela.px(*pena[0], (40, 34, 40))
        self.tomo(tela, J, ctx)
        braco(tela, J, "f", self.casaco, PELE_PALIDA, punho=LINHO)
        morte_extras(tela, self, ctx, J)

    def bolsa(self, tela, J):
        """Bolsa de couro a tiracolo, nas costas do quadril, com dois rolos de pergaminho para fora."""
        H = self.H
        Q = quadro_tronco(J)
        b = Q.pt(-0.1 * H, 0.02 * H)
        for k, dx in enumerate((-2, 2)):
            tela.pintar(tela.capsula(b + v2(dx, -3), b + v2(dx - 1, -10 - k * 2), 1.4), LINHO.claro(1))
        tela.pintar(tela.poly([b + v2(-5, -4), b + v2(5, -4), b + v2(6, 4), b + v2(-5, 5)]), COURO)
        tela.traco(b + v2(-5, -2), b + v2(5, -2), COURO_ESC[1], sobre=True)
        tela.px(b[0], b[1], LATAO[3])

    def vidros(self, tela, J, ctx):
        """Dois vidros de espécimes pendurados no cinto: um olho boiando em verde e um dente em âmbar."""
        H = self.H
        Q = quadro_tronco(J)
        for k, (liquido, coisa) in enumerate((((70, 120, 84), (226, 222, 210)), ((150, 108, 52), (232, 228, 214)))):
            p = Q.pt((0.01 + k * 0.045) * H, -0.05 * H) + v2(0, 3)
            vidro = tela.capsula(p + v2(0, -1.5), p + v2(0, 1.5), 1.5)
            tela.pintar(vidro, Mat((120, 136, 134), 4, especular=(220, 240, 236)))
            tela.chapado(vidro & tela.poly([p + v2(-2, 0), p + v2(2, 0), p + v2(2, 4), p + v2(-2, 4)]), liquido)
            tela.px(p[0], p[1] + 1, coisa)
            if k == 0:
                tela.px(p[0] + 0.6, p[1] + 1, (30, 30, 40))                                         # a pupila
            tela.traco(p + v2(-1, -2.5), p + v2(1, -2.5), COURO_ESC[1])                                 # rolha

    def tomo(self, tela, J, ctx):
        """O tomo aberto nas duas mãos: capa de couro com cantoneiras de ferro, páginas grossas, o bicho desenhado e a
        fita de marcar pendurada."""
        m = lerp(J["mao_f"], J["mao_b"], 0.5) + v2(2, -2)
        capa_livro = tela.poly([m + v2(-10, -5), m + v2(10, -5), m + v2(11, 4), m + v2(-11, 4)])
        tela.pintar(capa_livro, Mat((82, 40, 34), 5, ruido=0.2))
        for x in (-10, 10):                                                                           # cantoneiras
            tela.px(m[0] + x, m[1] - 5, FERRO[3])
            tela.px(m[0] + x * 1.05, m[1] + 4, FERRO[3])
        folhas = tela.poly([m + v2(-9, -4), m + v2(9, -4), m + v2(9, 3), m + v2(-9, 3)])
        tela.chapado(folhas, (222, 208, 172))
        tela.traco(m + v2(-9, 3), m + v2(9, 3), (190, 172, 134))                                        # a grossura das páginas
        tela.traco(m + v2(0, -4), m + v2(0, 3), (150, 130, 100))
        pagina = 0 if ctx.anim != "folhear" else (1 if ctx.i < 3 else 0)
        desenho = [((-6, -1), (-3, -2), (-4, 1)), ((2, 0), (5, -2), (6, 1))][pagina]
        for a, b, c in [desenho]:
            tela.traco(m + v2(*a), m + v2(*b), (60, 40, 30))
            tela.traco(m + v2(*b), m + v2(*c), (60, 40, 30))
        for k in range(3):                                                                            # linhas de texto
            tela.traco(m + v2(2 - 8 * (pagina == 1), -2 + k * 2), m + v2(7 - 8 * (pagina == 1), -2 + k * 2), (170, 150, 120))
        tela.traco(m + v2(0, 4), m + v2(1, 9), (150, 36, 40))                                          # fita de marcar
        if ctx.anim == "folhear" and 0 < ctx.i < 5:
            self.folha_virando(tela, m, self.VIRADA[ctx.i])


# ============================================================
# MESTRE DO GRIMÓRIO — encapuzado de roxo, com um grimório flutuando e runas em volta
# ============================================================

class MestreDoGrimorio(Modelo):
    nome = "mestre_do_grimorio"
    H = 76
    estilo = "magia"
    prop = dict(ombros=0.21, l_coxa=0.04, l_canela=0.032)
    base = dict(braco_f=(1.2, 1.0), braco_b=(0.9, 1.3), arma_f=0.0, pe_f=(-0.05, 0), pe_b=(0.07, 0))
    manto_mat = Mat((54, 36, 80), 6, desce=0.45, ruido=0.12, relevo=0.7, arredonda=0.6)

    def desenhar(self, tela, ctx, J):
        H = self.H
        mt = self.manto_mat
        capa(tela, J, mt.escuro(1), comprimento=0.7, vento=0.03 * math.sin(ctx.a), larg=0.16, rasgos=7, semente=93)
        braco(tela, J, "b", mt.escuro(1), PELE_PALIDA, grossura=1.2)
        perna(tela, J, "b", mt.escuro(2), mt.escuro(2), cano=0.4)
        perna(tela, J, "f", mt.escuro(1), mt.escuro(1), cano=0.4)
        manto(tela, J, mt, folga=0.08, rasgos=6, semente=95, barra=-0.01)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        tela.traco(Q.pt(0.03 * H, T * 0.95), Q.pt(0.05 * H, -0.4 * H), OURO_VELHO[2], sobre=True)        # debrum
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO, altura=0.02)
        _, C, face = capuz(tela, J, mt, ponta=0.6)
        h = J["P"]["cabeca"]
        w = h * 0.95
        for x in (w * 0.28, w * 0.5):
            tela.px(*C.pt(x, h * 0.02), (220, 170, 255), emite=True)
        tela.brilho(C.pt(w * 0.4, 0), 4, (200, 150, 255), 0.4, halo=False)
        # grimório flutuando à frente, aberto, subindo e descendo
        livro = lerp(J["mao_f"], J["mao_b"], 0.5) + v2(8, -10 + math.sin(ctx.a) * 2)
        tela.pintar(tela.poly([livro + v2(-8, -4), livro + v2(8, -4), livro + v2(9, 3), livro + v2(-9, 3)]), Mat((60, 30, 70), 5))
        tela.chapado(tela.poly([livro + v2(-7, -3), livro + v2(7, -3), livro + v2(7, 2), livro + v2(-7, 2)]), (210, 196, 230))
        tela.traco(livro + v2(0, -3), livro + v2(0, 2), (120, 90, 150))
        tela.brilho(livro, 12, (190, 140, 255), 0.55 + 0.15 * math.sin(ctx.a * 2))
        for k in range(4):                                  # runas orbitando o livro
            a = ctx.a + k * math.pi / 2
            fx.runa(tela, livro + v2(math.cos(a) * 14, math.sin(a) * 6 - 6), (210, 170, 255), 2, forma=k)
        braco(tela, J, "f", mt, PELE_PALIDA, grossura=1.2)
        morte_extras(tela, self, ctx, J)


# ============================================================
# MAGO ANCIÃO — barba branca até a cintura, chapéu alto de estrelas e cajado de cristal
# ============================================================

class MagoAnciao(Modelo):
    nome = "mago_anciao"
    H = 78
    estilo = "magia"
    prop = dict(ombros=0.21)
    base = dict(braco_f=(0.6, 0.7), braco_b=(0.2, 0.6), arma_f=0.05, pe_f=(-0.06, 0), pe_b=(0.07, 0))
    manto_mat = Mat((40, 50, 110), 6, desce=0.4, ruido=0.12, relevo=0.7, arredonda=0.6)

    def desenhar(self, tela, ctx, J):
        H = self.H
        mt = self.manto_mat
        capa(tela, J, mt.escuro(2), comprimento=0.66, vento=0.03 * math.sin(ctx.a), larg=0.15, rasgos=5, semente=97)
        braco(tela, J, "b", mt.escuro(1), PELE_PALIDA, grossura=1.2)
        perna(tela, J, "b", COURO_ESC, COURO_ESC.escuro(1), cano=0.5)
        perna(tela, J, "f", COURO_ESC, COURO_ESC, cano=0.5)
        manto(tela, J, mt, folga=0.07, rasgos=4, semente=99, barra=-0.005)
        Q = quadro_tronco(J)
        for k in range(6):                                  # estrelas bordadas
            p = Q.pt((-0.06 + (k % 3) * 0.05) * H, (-0.3 + (k // 3) * 0.25) * H)
            tela.px(p[0], p[1], (240, 220, 140))
        cinto(tela, J, COURO_ESC, fivela=OURO_VELHO, altura=0.02)
        pescoco(tela, J, PELE_PALIDA, 0.03)
        cab, C = cabeca_base(tela, J, PELE_PALIDA)
        h = J["P"]["cabeca"]
        w = h * 0.82
        barba(tela, J, Mat((226, 222, 214), 5, ruido=0.4), comprimento=2.2, largura=0.6)
        tela.traco(C.pt(w * 0.15, -h * 0.05), C.pt(w * 0.55, -h * 0.1), (200, 196, 190))          # bigode
        olho(tela, C, w * 0.36, h * 0.08, (120, 190, 255), brilho=(120, 190, 255))
        tela.traco(C.pt(w * 0.2, h * 0.2), C.pt(w * 0.48, h * 0.18), (220, 216, 210))             # sobrancelha
        # chapéu alto e torto
        s = math.sin(ctx.a)
        ang_aba = math.atan2(J["hu"][0], -J["hu"][1])
        aba = tela.elipse_girada(C.pt(w * 0.05, h * 0.42), w * 1.0, h * 0.14, ang_aba)
        cone = tela.poly(C.pts([(-w * 0.45, h * 0.42), (w * 0.45, h * 0.42), (w * 0.15, h * 1.4), (-w * 0.2 + s * 0.4, h * 2.1),
                                (-w * 0.45 + s * 0.6, h * 1.9), (-w * 0.25, h * 1.3)]))
        tela.pintar(cone | aba, mt.claro(1))
        for x, y in ((0.0, 0.8), (-0.2, 1.3), (0.1, 1.1)):
            tela.px(*C.pt(w * x, h * y), (250, 230, 150), emite=True)
        # cajado com cristal
        mf = J["mao_f"]
        topo = armas.cajado(tela, mf, J["arma_f"], H * 0.42, MADEIRA, atras=H * 0.5, torto=1.0)
        fx.cristal(tela, topo, J["arma_f"], 10, 2.6, fx.FOGO_AZUL)
        tela.brilho(topo + dir_ang(J["arma_f"]) * 6, 10, (130, 190, 255), 0.5 + 0.15 * s)
        braco(tela, J, "f", mt, PELE_PALIDA, grossura=1.2)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            fx.orbe(tela, J["mao_b"] + v2(6, -3), 3.5, fx.FOGO_AZUL)
        morte_extras(tela, self, ctx, J)