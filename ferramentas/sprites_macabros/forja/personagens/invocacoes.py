"""Invocações (Fada, Sapo Venenoso) e objetos (Altar, Baú).

Não são humanoides: pose() devolve um dicionário de pontos (como as bestas).
Lobos, tigre, macaco, garça, corvo e gato estão em feras.py; a Torreta em construtos.py.
"""
import math

from ..motor import Mat, v2, dir_ang, girar
from .. import fx
from .bestas import Besta
from .herois import FERRO, OURO_VELHO, OSSO


# ============================================================
# FADA (andarilha feérica)
# ============================================================

class Fada(Besta):
    nome = "fada"
    S = 40

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.4), int(S * 2.4)
        self.ancora = (int(S * 1.1), self.alt - 3)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        altura, avanco, asa = 1.15, 0.0, math.sin(ctx.a * 2)
        if ctx.anim == "parado":
            altura += [0, 0.06, 0.1, 0.06][ctx.i]
        elif ctx.anim == "ataque":
            avanco = [0.0, 0.25, 0.3, 0.1][ctx.i]
        elif ctx.anim == "dano":
            avanco = [-0.15, -0.05][ctx.i]
        elif ctx.anim == "morte":
            altura = [1.0, 0.7, 0.3, 0.08][ctx.i]
            asa = -0.8
        corpo = v2(cx + avanco * S, chao - altura * S)
        return {"corpo": corpo, "asa": asa, "morta": ctx.anim == "morte" and ctx.i >= 2}

    def asa(self, tela, raiz, ponta_ang, comprimento, largura, mat, veia, viva):
        """Uma asa de libélula: lâmina comprida saindo das costas, com nervuras."""
        d = dir_ang(ponta_ang)
        centro = raiz + d * comprimento * 0.5
        giro = math.atan2(d[1], d[0])
        tela.pintar(tela.elipse_girada(centro, comprimento * 0.5, largura, giro), mat)
        n = v2(-d[1], d[0])
        tela.traco(raiz, raiz + d * comprimento * 0.92, veia, sobre=True, emite=viva)
        for k in (0.35, 0.65):                 # nervuras laterais
            base = raiz + d * comprimento * k
            tela.traco(base, base + d * comprimento * 0.2 + n * largura * 0.7, veia, sobre=True)

    def desenhar(self, tela, ctx, P):
        S = self.S
        c = P["corpo"]
        bate = P["asa"]
        viva = not P["morta"]
        membrana = Mat((176, 236, 214), 5, relevo=0.3, especular=(250, 255, 250))
        if not viva:
            membrana = membrana.escuro(2)
        veia = (120, 210, 180) if viva else (70, 110, 100)
        costas = c + v2(-0.05 * S, -0.08 * S)
        # par de trás (mais escuro), depois o par da frente — todos atrás do corpo
        for mat, deslocamento, abertura in ((membrana.escuro(1), v2(2, 0), 0.25), (membrana, v2(0, 0), 0.0)):
            raiz = costas + deslocamento
            self.asa(tela, raiz, -0.55 - abertura + bate * 0.3, 0.78 * S, 0.12 * S, mat, veia, viva)    # de cima
            self.asa(tela, raiz, -1.9 + abertura - bate * 0.2, 0.5 * S, 0.09 * S, mat, veia, viva)      # de baixo
        # vestido de pétalas
        petala = Mat((70, 150, 110), 5, relevo=0.6)
        tela.pintar(tela.poly([c + v2(-0.09 * S, 0.0), c + v2(0.09 * S, 0.0), c + v2(0.17 * S, 0.3 * S),
                               c + v2(0.02 * S, 0.25 * S), c + v2(-0.14 * S, 0.32 * S)]), petala)
        tela.pintar(tela.capsula(c + v2(0, 0.02 * S), c + v2(0, -0.13 * S), 0.07 * S, 0.055 * S), Mat((230, 210, 190), 5))
        perna_pe = c + v2(0.02 * S, 0.3 * S)
        tela.traco(perna_pe, perna_pe + v2(-1, 0.14 * S), (220, 200, 180))
        # braço estendido para a frente (no ataque aponta o feitiço)
        mao = c + v2((0.22 if ctx.anim == "ataque" else 0.12) * S, -0.06 * S)
        tela.traco(c + v2(0.02 * S, -0.1 * S), mao, (230, 210, 190))
        cabeca = c + v2(0.02 * S, -0.25 * S)
        tela.pintar(tela.circulo(cabeca, 0.12 * S), Mat((240, 222, 204), 5))
        # cabelo dourado comprido, esvoaçando para trás
        s = math.sin(ctx.a)
        cabelo = [cabeca + v2(1, -4), cabeca + v2(-4, -3), cabeca + v2(-8, 2 + s), cabeca + v2(-10, 7 + s * 1.5)]
        tela.pintar(tela.corrente(cabelo, [3.2, 3.0, 2.2, 1.0]), Mat((236, 206, 110), 5, relevo=0.6))
        tela.px(cabeca[0] + 3, cabeca[1], (40, 110, 70), emite=viva)
        if viva:
            tela.brilho(c, 15, (150, 255, 170), 0.55)
            for k in range(4):                 # pozinho brilhante caindo
                t = (ctx.i / 4 + k / 4) % 1
                tela.px(c[0] - 4 + k * 3, c[1] + 0.4 * S + t * 14, (220, 255, 200), emite=True)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            fx.orbe(tela, mao + v2(4, 0), 3, fx.FOGO_VERDE)

# ============================================================
# OBJETOS: ALTAR e BAÚ
# ============================================================

class Altar(Besta):
    nome = "altar"
    S = 60

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 1.6), int(S * 1.6)
        self.ancora = (int(S * 0.8), self.alt - 3)
        self.pedra = Mat((96, 88, 104), 6, relevo=1.1, ruido=0.25)

    def pose(self, ctx):
        return {"fase": ctx.a, "aceso": ctx.anim in ("parado", "ataque"), "brilha": ctx.anim == "ataque"}

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        topo = chao - 0.45 * S
        tela.pintar(tela.poly([v2(cx - 0.42 * S, chao), v2(cx + 0.42 * S, chao), v2(cx + 0.36 * S, topo),
                               v2(cx - 0.36 * S, topo)]), self.pedra)
        tela.pintar(tela.poly([v2(cx - 0.44 * S, topo), v2(cx + 0.44 * S, topo), v2(cx + 0.44 * S, topo - 5),
                               v2(cx - 0.44 * S, topo - 5)]), self.pedra.claro(1))
        tela.pintar(tela.poly([v2(cx - 0.12 * S, topo - 4), v2(cx + 0.12 * S, topo - 4), v2(cx + 0.16 * S, chao - 0.12 * S),
                               v2(cx - 0.16 * S, chao - 0.12 * S)]), Mat((110, 24, 32), 5, relevo=0.6))
        tela.traco(v2(cx - 0.12 * S, topo + 4), v2(cx + 0.12 * S, topo + 4), OURO_VELHO[3], sobre=True)
        # cruz flutuante
        cruz = v2(cx, topo - 0.3 * S + math.sin(P["fase"]) * 2)
        tela.pintar(tela.capsula(cruz + v2(0, -9), cruz + v2(0, 9), 1.6) | tela.capsula(cruz + v2(-6, -3), cruz + v2(6, -3), 1.6),
                    OURO_VELHO)
        tela.brilho(cruz, 14 if P["brilha"] else 10, (255, 230, 150), 0.8 if P["brilha"] else 0.45)
        if P["aceso"]:
            for dx in (-0.3, 0.3):
                b = v2(cx + dx * S, topo - 5)
                tela.pintar(tela.capsula(b, b + v2(0, -5), 1.4), OSSO)
                fx.chama(tela, b + v2(0, -6), 5, 3, fase=P["fase"] + dx * 3, brilho=False)


class Bau(Besta):
    nome = "bau"
    S = 48

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 1.8), int(S * 1.5)
        self.ancora = (int(S * 0.9), self.alt - 3)

    def pose(self, ctx):
        aberto = {"parado": 0.0, "ataque": [0.3, 0.8, 1.0, 1.0][ctx.i], "dano": 0.1, "morte": 1.0}[ctx.anim]
        return {"aberto": aberto, "fase": ctx.a}

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        madeira = Mat((110, 70, 42), 6, ruido=0.25)
        topo = chao - 0.45 * S
        caixa = tela.poly([v2(cx - 0.45 * S, chao), v2(cx + 0.45 * S, chao), v2(cx + 0.45 * S, topo), v2(cx - 0.45 * S, topo)])
        tela.pintar(caixa, madeira)
        if P["aberto"] > 0.2:
            tela.chapado(tela.poly([v2(cx - 0.4 * S, topo + 1), v2(cx + 0.4 * S, topo + 1), v2(cx + 0.36 * S, topo + 5),
                                    v2(cx - 0.36 * S, topo + 5)]), (255, 210, 90), emite=True)
            tela.brilho(v2(cx, topo - 4), 16 * P["aberto"], (255, 200, 90), 0.8)
        # tampa (gira para trás quando abre)
        piv = v2(cx - 0.45 * S, topo)
        a = -1.6 * P["aberto"]
        tampa = [girar(p, a, piv) for p in (v2(cx - 0.45 * S, topo), v2(cx + 0.45 * S, topo), v2(cx + 0.42 * S, topo - 0.22 * S),
                                            v2(cx - 0.42 * S, topo - 0.22 * S))]
        tela.pintar(tela.poly(tampa), madeira.claro(1))
        for dx in (-0.3, 0.3):                 # tiras de ferro
            tela.pintar(tela.poly([v2(cx + dx * S - 2, chao), v2(cx + dx * S + 2, chao), v2(cx + dx * S + 2, topo),
                                   v2(cx + dx * S - 2, topo)]), FERRO)
        tela.pintar(tela.circulo(v2(cx, topo + 3), 2.6), OURO_VELHO)


# ============================================================
# FAMILIARES (Monge: espíritos · Feiticeira: bichos)
# ============================================================

class SapoVenenoso(Besta):
    """Sapo gordo e verde-vivo, papo inchando e língua no ataque."""
    nome = "sapo_venenoso"
    S = 46

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 2.2), int(S * 1.3)
        self.ancora = (int(S * 0.9), self.alt - 3)
        self.pele = Mat((90, 170, 60), 6, relevo=1.0, especular=(220, 255, 180))
        self.barriga = Mat((210, 200, 120), 5)

    def pose(self, ctx):
        S = self.S
        cx, chao = self.ancora
        papo, salto, lingua, achata = 0.0, 0.0, 0.0, 0.0
        if ctx.anim == "parado":
            papo = [0.0, 0.5, 1.0, 0.5][ctx.i]
        elif ctx.anim == "ataque":
            salto, lingua = [(0.0, 0.0), (0.15, 1.0), (0.12, 0.8), (0.0, 0.0)][ctx.i]
        elif ctx.anim == "dano":
            achata = [0.3, 0.1][ctx.i]
        elif ctx.anim == "morte":
            achata = [0.2, 0.5, 0.8, 0.9][ctx.i]
        return {"c": v2(cx, chao - (0.32 - achata * 0.15) * S - salto * S), "papo": papo, "lingua": lingua,
                "achata": achata, "chao": chao, "morta": ctx.anim == "morte" and ctx.i >= 2}

    def desenhar(self, tela, ctx, P):
        S = self.S
        c = P["c"]
        a = P["achata"]
        for lado, mat in ((-1, self.pele.escuro(1)), (1, self.pele)):              # patas de trás dobradas
            q = c + v2(-0.15 * S, 0.1 * S)
            tela.pintar(tela.corrente([q, q + v2(-0.14 * S, 0.12 * S), q + v2(0.05 * S, P["chao"] - q[1] - 1)],
                                      [0.09 * S, 0.06 * S, 0.03 * S]), mat)
        tela.pintar(tela.elipse(c[0], c[1], 0.34 * S, (0.24 - a * 0.06) * S), self.pele)
        tela.pintar(tela.elipse(c[0] + 0.12 * S, c[1] + 0.1 * S, 0.18 * S, 0.1 * S), self.barriga)
        for k in range(5):                                                          # verrugas
            tela.px(c[0] - 0.2 * S + k * 0.08 * S, c[1] - 0.12 * S + (k % 2) * 0.05 * S, self.pele[1])
        papo = P["papo"]
        if papo:
            tela.pintar(tela.circulo(c + v2(0.24 * S, 0.06 * S), (0.05 + 0.04 * papo) * S), Mat((230, 220, 140), 4))
        for dx in (0.12, 0.26):                                                    # patas da frente
            p = c + v2(dx * S, 0.15 * S)
            tela.pintar(tela.capsula(p, v2(p[0] + 0.03 * S, P["chao"] - 1), 0.035 * S, 0.03 * S), self.pele)
        for dx in (0.12, 0.24):                                                    # olhos saltados
            o = c + v2(dx * S, -0.2 * S)
            tela.pintar(tela.circulo(o, 0.06 * S), self.pele.claro(1))
            if not P["morta"]:
                tela.chapado(tela.circulo(o + v2(0.01 * S, 0), 0.03 * S), (240, 200, 40), emite=True)
                tela.px(o[0] + 0.01 * S, o[1], (20, 10, 10))
        if P["lingua"] > 0:
            boca = c + v2(0.3 * S, -0.02 * S)
            tela.pintar(tela.capsula(boca, boca + v2(0.7 * S * P["lingua"], -0.04 * S), 0.025 * S), Mat((220, 80, 120), 4))
            tela.pintar(tela.circulo(boca + v2(0.7 * S * P["lingua"], -0.04 * S), 0.04 * S), Mat((230, 90, 130), 4))
        if not P["morta"]:
            for k in range(3):                                                      # bolhas de veneno
                t = (ctx.i / 4 + k / 3) % 1
                tela.px(c[0] - 0.1 * S + k * 0.1 * S, c[1] - 0.3 * S - t * 8, (150, 255, 90), emite=True)