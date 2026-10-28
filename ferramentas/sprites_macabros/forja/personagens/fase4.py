"""Criaturas das fases novas da fase 4 (uma seção por fase).

CriaturaSimples é a base das que não têm esqueleto próprio: balança no "parado", avança no
"ataque", recua no "dano" e afunda/cai na "morte". As subclasses só desenham o corpo.
"""
import math

from ..motor import Mat, metal, v2
from .. import fx
from .bestas import Besta
from .invocacoes import SapoVenenoso
from .inimigos_b import Inquisidor

CASCA = Mat((92, 58, 40), 6, relevo=1.2, ruido=0.35)
CASCA_ESCURA = CASCA.escuro(1)
PALHA = Mat((196, 160, 84), 6, relevo=0.8, ruido=0.4)
ESTOPA = Mat((150, 120, 84), 6, relevo=0.8, ruido=0.3)


class CriaturaSimples(Besta):
    S = 56
    proporcao = (1.8, 1.6)            # largura e altura da célula, em S
    pe = 0.5                           # posição da âncora na largura

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * self.proporcao[0]), int(S * self.proporcao[1])
        self.ancora = (int(self.larg * self.pe), self.alt - 3)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        bob = avanco = queda = 0.0
        if ctx.anim == "parado":
            bob = [0, 0.5, 1, 0.5][ctx.i] * 0.02 * S
        elif ctx.anim == "ataque":
            avanco = [-0.05, 0.25, 0.3, 0.08][ctx.i]
        elif ctx.anim == "dano":
            avanco = [-0.12, -0.05][ctx.i]
        elif ctx.anim == "morte":
            queda = [0.15, 0.45, 0.8, 1.0][ctx.i]
        return {"cx": cx + avanco * S, "chao": chao, "bob": bob, "golpe": ctx.anim == "ataque" and ctx.i in (1, 2),
                "ferido": ctx.anim == "dano", "queda": queda, "fase": ctx.a, "i": ctx.i}


# ============================================================
# BOSQUE CARMESIM
# ============================================================

class EspantalhoPossuido(CriaturaSimples):
    """Espantalho de estopa e palha, sorriso costurado brilhando e chapéu furado; flutua do poste."""
    nome = "espantalho_possuido"
    S = 58
    proporcao = (2.8, 2.3)            # largo: na morte ele tomba para a frente
    pe = 0.33

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao, q = P["cx"], P["chao"], P["queda"]
        giro = q * 1.5
        def pt(x, y):                              # ponto girado em volta do pé do poste (queda)
            dx, dy = x * S, -y * S
            return v2(cx + dx * math.cos(giro) - dy * math.sin(giro), chao + dx * math.sin(giro) + dy * math.cos(giro) - P["bob"])
        tela.pintar(tela.capsula(pt(0, 0), pt(0, 1.75), 0.05 * S), CASCA)                     # poste
        braco = 0.15 if P["golpe"] else 0.0
        esq, dir_ = pt(-0.62, 1.32 + braco), pt(0.62, 1.32 - braco * 2)
        tela.pintar(tela.capsula(esq, dir_, 0.045 * S), CASCA_ESCURA)                          # travessa
        tela.pintar(tela.poly([pt(-0.32, 1.42), pt(0.32, 1.42), pt(0.28, 0.7), pt(0.12, 0.62), pt(-0.06, 0.72),
                               pt(-0.24, 0.62), pt(-0.3, 0.72)]), ESTOPA)                        # camisa rasgada
        tela.traco(pt(-0.05, 1.4), pt(-0.02, 0.8), (90, 60, 40), sobre=True)
        for mao in (esq, dir_):                                                                  # tufos de palha
            for k in range(4):
                tela.traco(mao, mao + v2((k - 1.5) * 3, 6 + k), PALHA[3 if k % 2 else 2])
        if P["golpe"]:
            fx.chama(tela, dir_ + v2(4, 2), 0.3 * S, 0.14 * S, fx.FOGO, fase=P["fase"] * 2)       # garra de fogo-fátuo
        cabeca = pt(0, 1.62)
        tela.pintar(tela.circulo(cabeca, 0.2 * S), ESTOPA.claro(1))
        for dx in (-0.08, 0.08):
            tela.chapado(tela.circulo(cabeca + v2(dx * S, -0.03 * S), 0.035 * S), (255, 150, 40), emite=q < 0.6)
        boca = [cabeca + v2(-0.1 * S, 0.07 * S), cabeca + v2(0.1 * S, 0.07 * S)]
        tela.traco(*boca, (255, 140, 40), emite=q < 0.6)
        for k in range(5):                                                                        # pontos da costura
            x = -0.08 + k * 0.04
            tela.px(cabeca[0] + x * S, cabeca[1] + 0.05 * S, (60, 30, 20))
        aba = cabeca + v2(0, -0.14 * S)
        tela.pintar(tela.poly([aba + v2(-0.3 * S, 0.03 * S), aba + v2(0.3 * S, 0.03 * S), aba + v2(0.12 * S, -0.02 * S),
                               aba + v2(0.04 * S, -0.3 * S), aba + v2(-0.12 * S, -0.02 * S)]), Mat((70, 56, 44), 5, ruido=0.3))
        if q < 0.6:
            tela.brilho(cabeca, 0.4 * S, (255, 140, 40), 0.25 + 0.08 * math.sin(P["fase"] * 2))


# ============================================================
# PÂNTANO DOS AFOGADOS
# ============================================================

AGUA = (40, 60, 70)


def poca(tela, cx, chao, largura, S):
    """Poça d'água escura sob os pés (com um brilho na borda)."""
    tela.chapado(tela.elipse(cx, chao - 2, largura * S, 0.06 * S), AGUA)
    tela.traco(v2(cx - largura * 0.5 * S, chao - 3), v2(cx - largura * 0.1 * S, chao - 3), (90, 130, 140))


class SapoBoi(SapoVenenoso):
    """Sapo enorme cor de lama, papo amarelo e olhos alaranjados que cospem uma névoa que cega."""
    nome = "sapo_boi"
    S = 72

    def __init__(self, **kw):
        super().__init__(**kw)
        self.pele = Mat((104, 100, 54), 6, relevo=1.1, especular=(200, 210, 150))
        self.barriga = Mat((220, 190, 90), 5)
# ============================================================
# CATACUMBAS DA ORDEM CAÍDA
# ============================================================

FOGO_SANTO = [(120, 70, 20), (220, 150, 40), (255, 210, 110), (255, 245, 200), (255, 255, 240)]


class EnxameDeRatos(CriaturaSimples):
    """Um monte de ratos de olhos vermelhos que se mexe como um bicho só."""
    nome = "enxame_de_ratos"
    S = 64
    proporcao = (2.2, 1.2)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao, q = P["cx"], P["chao"], P["queda"]
        vivos = 7 - int(q * 6)
        avanco = 0.25 * S if P["golpe"] else 0.0
        pelo = Mat((80, 70, 66), 5, relevo=1.0, ruido=0.4)
        for k in range(vivos):
            x = cx + (k - 3) * 0.2 * S + math.sin(k * 2.7 + P["fase"] * 2) * 0.05 * S + (avanco if k % 2 else avanco * 0.5)
            y = chao - 0.1 * S - (k % 3) * 0.12 * S
            corpo = v2(x, y)
            tela.pintar(tela.elipse(corpo[0], corpo[1], 0.13 * S, 0.08 * S), pelo if k % 2 else pelo.escuro(1))
            tela.pintar(tela.poly([corpo + v2(0.1 * S, -0.04 * S), corpo + v2(0.22 * S, 0.0), corpo + v2(0.1 * S, 0.04 * S)]), pelo)
            tela.px(corpo[0] + 0.15 * S, corpo[1] - 0.02 * S, (240, 40, 40), emite=True)
            tela.traco(corpo + v2(-0.12 * S, 0), corpo + v2(-0.28 * S, 0.04 * S + math.sin(k + P["fase"]) * 2), (170, 120, 120))


class InquisidorPenitente(Inquisidor):
    """O Inquisidor da Ordem caída: armadura de osso branco, maior, com fogo sagrado nas mãos."""
    nome = "inquisidor_penitente"
    H = 96
    armadura = metal((196, 186, 160), especular=(255, 250, 230), contraste=1.1)

    def desenhar(self, tela, ctx, J):
        super().desenhar(tela, ctx, J)
        for lado in ("f", "b"):
            mao = J["mao_" + lado]
            fx.chama(tela, mao + v2(0, -2), self.H * (0.16 + (0.08 if ctx.golpe else 0)), self.H * 0.1, FOGO_SANTO,
                     fase=ctx.a * 2 + (1 if lado == "b" else 0))
        tela.brilho(J["cabeca"], self.H * 0.25, (255, 220, 140), 0.25)
