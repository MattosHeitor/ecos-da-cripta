"""Variantes que antes eram só recolorações e agora têm sprite próprio.

Cada uma HERDA o bicho/humanoide de origem (mesmo esqueleto e animação) e, com o mixin
ComAcabamento (forja/criaturas/acabamento.py), troca materiais e acrescenta o que o nome promete:

    GoblinDasCavernas      pálido, olhos enormes que refletem a luz, cogumelo-lanterna
    GoblinBrutoSangrento   coberto de sangue, pintura de guerra, troféus de crânio na cintura
    EsqueletoMaldito       ossos escurecidos, chama de alma no peito, runas e aura roxa
    OrcDeSangue            pele rubra, cicatrizes rituais acesas, mão de sangue no peito
    AranhaVenenosa         marcas de alerta no abdômen e presas pingando veneno que brilha
    PalhacoPalido          rosto de giz, órbitas negras, sorriso costurado e balão vermelho
    BesouroDeBronze        carapaça de bronze com rebites, entalhes e azinhavre
    CriaVampiricaAnciao    velha e cinzenta, cabelo branco, capa nobre em farrapos, garras longas
    LouvaDeusOrquidea      rosa como uma orquídea, pétalas nas patas, pintas magenta
    CavaleiroOssudo        armadura velha enferrujada e com musgo, capa podre, olhos fantasmas
    MongeFlagelante        (forja de monstros) monge de capuz com as costas em carne viva e flagelo
    GolemDeEscoria         escória negra rachada de lava, pingando e soltando fumaça
    SombraDoHeroi          silhueta escura do herói, bordas de fumaça, olhos acesos e distorção
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, lerp, dir_ang, girar
from ..humanoide import quadro_cabeca, quadro_tronco, capa, capuz
from .. import texturas as T
from .. import fx
from ..criaturas.acabamento import ComAcabamento, olhos_humanoides
from ..criaturas.monstro import ForjaMonstro
from .inimigos_a import Goblin, Esqueleto, Orc
from .inimigos_b import Vampiro, Golem
from .bestas import Aranha, LouvaDeus, Besouro
from .novos import Palhaco
from .herois import Guerreiro, MADEIRA, OSSO

SANGUE = (120, 14, 24)
SANGUE_ESCURO = (70, 6, 14)


def mancha_de_sangue(tela, mask, ancora, quantidade=0.25, semente=1):
    T.manchas(tela, mask, ancora, SANGUE, escala=3, quantidade=quantidade, forca=0.8, semente=semente)


def caveirinha(tela, c, r=2.0):
    """Crânio minúsculo (troféus, enfeites)."""
    tela.chapado(tela.circulo(c, r), OSSO[4])
    tela.px(c[0] - 0.7, c[1], (30, 20, 20))
    tela.px(c[0] + 0.7, c[1], (30, 20, 20))
    tela.px(c[0], c[1] + r, OSSO[2])


# ============================================================
# GOBLINS
# ============================================================

class GoblinDasCavernas(ComAcabamento, Goblin):
    """Goblin que nunca viu o sol: pele pálida, olhos enormes que refletem a luz e um cogumelo-lanterna."""
    nome = "goblin_das_cavernas"
    pele = Mat((150, 158, 162), 6, relevo=1.0, satur=0.4)

    def cabeca(self, tela, J, ctx):
        tipo, self.tipo = self.tipo, "caverna"                 # mesma cabeça, sem o capacete
        super().cabeca(tela, J, ctx)
        self.tipo = tipo
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.95
        for x, r in ((w * 0.16, h * 0.12), (w * 0.44, h * 0.15)):          # olhos enormes
            c = C.pt(x, h * 0.1)
            tela.chapado(tela.circulo(c, r), (16, 20, 26))
            tela.chapado(tela.circulo(c + v2(0.4, 0), r * 0.62), (190, 240, 255), emite=True)
            tela.px(c[0] + 0.5, c[1], (20, 40, 60), emite=True)
            tela.px(c[0] - r * 0.3, c[1] - r * 0.4, (255, 255, 255), emite=True)
        tela.brilho(C.pt(w * 0.3, h * 0.1), 5, (150, 220, 255), 0.45)

    def acabar(self, tela, ctx, J):
        H = self.H
        mao = J["mao_b"]
        topo = mao + v2(-1, -H * 0.28)                                     # cogumelo-lanterna
        tela.pintar(tela.capsula(mao + v2(0, 2), topo, 0.9, 0.7), MADEIRA)
        chapeu = tela.elipse(topo[0], topo[1], H * 0.07, H * 0.045) & ~tela.poly(
            [topo + v2(-H, 1), topo + v2(H, 1), topo + v2(H, H), topo + v2(-H, H)])
        vivo = self.vivo(ctx)
        tela.chapado(chapeu, (120, 230, 220) if vivo else (70, 90, 90), emite=vivo)
        for dx in (-2, 1, 3):
            tela.px(topo[0] + dx, topo[1] - 1 - abs(dx) % 2, (230, 255, 250) if vivo else (110, 120, 120), emite=vivo)
        if vivo:
            tela.brilho(topo, H * 0.35, (110, 230, 220), 0.45 + 0.08 * math.sin(ctx.a * 2))
            T.particulas(tela, topo, (H * 0.08, H * 0.05), (160, 255, 240), n=4, fase=ctx.a, sobe=H * 0.15, semente=2)
        corpo = (tela.alfa > 0) & ~tela.emite                               # pintas bioluminescentes
        ys, xs, u, v = T.locais(tela, corpo, J["pelvis"])
        sel = T.hash2(u, v, 9) < 0.012
        if vivo:
            tela.cor[ys[sel], xs[sel]] = (110, 220, 210)
            tela.emite[ys[sel], xs[sel]] = True


class GoblinBrutoSangrento(ComAcabamento, Goblin):
    """Goblin bruto encharcado de sangue: pintura de guerra, maça pingando e crânios na cintura."""
    tipo = "bruto"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "goblin_bruto_sangrento"
        self.pele = Mat((118, 98, 70), 6, relevo=1.1)

    def cabeca(self, tela, J, ctx):
        super().cabeca(tela, J, ctx)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.95
        for k in range(3):                                                  # pintura de guerra
            a = C.pt(w * (0.05 + k * 0.17), h * 0.35)
            tela.traco(a, a + J["hu"] * (-h * 0.45) + v2(1, 0), (150, 20, 26), sobre=True)
        for x in (w * 0.2, w * 0.45):
            p = C.pt(x, h * 0.08)
            tela.px(p[0], p[1], (255, 60, 40), emite=True)

    def acabar(self, tela, ctx, J):
        H = self.H
        corpo = (tela.alfa > 0) & ~tela.emite
        mancha_de_sangue(tela, corpo, J["peito"], 0.28, semente=3)
        cabeca_maca = J["mao_f"] + dir_ang(J["arma_f"]) * H * 0.42
        regiao = tela.circulo(cabeca_maca, H * 0.09) & corpo
        ys, xs = np.nonzero(regiao)
        T.misturar_cor(tela, ys, xs, SANGUE, 0.6)
        T.escorrer(tela, regiao, cabeca_maca, SANGUE, densidade=0.5, comp=4, fase=ctx.a, molhado=0.3, semente=4)
        Q = quadro_tronco(J)
        for k in range(3):                                                  # troféus na cintura
            caveirinha(tela, Q.pt(-0.06 * H + k * 0.06 * H, -0.06 * H), r=H * 0.035)
        o = J["ombro_f"]
        for k in range(3):                                                  # cravos no ombro
            b = o + v2(-2 + k * 2, -1)
            tela.pintar(tela.poly([b + v2(-1, 0), b + v2(1, 0), b + v2(0.5, -H * 0.06)]), metal((110, 100, 96)))


# ============================================================
# MORTOS-VIVOS
# ============================================================

class EsqueletoMaldito(ComAcabamento, Esqueleto):
    """Esqueleto amaldiçoado: ossos escurecidos e rachados, chama de alma no peito, runas e aura roxa."""
    nome = "esqueleto_maldito"
    osso = Mat((128, 116, 132), 6, relevo=1.0, luz_hue=0.75, satur=0.6)
    olhos = (200, 110, 255)

    def acabar(self, tela, ctx, J):
        H = self.H
        vivo = self.vivo(ctx)
        corpo = (tela.alfa > 0) & ~tela.emite
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.1, H * 0.25), n=6, passos=4, cor=(40, 28, 50), emite=False,
                     semente=5)
        if not vivo:
            return
        fx.chama(tela, J["peito"] + v2(0, H * 0.05), H * 0.12, H * 0.08, fx.FOGO_ROXO, fase=ctx.a, linguas=2, brilho=False)
        tela.brilho(J["peito"], H * 0.2, (180, 90, 255), 0.4)
        for lado in ("f", "b"):                                             # runas nos ossos
            for t in (0.3, 0.7):
                p = lerp(J["ombro_" + lado], J["cotovelo_" + lado], t)
                tela.px(p[0], p[1], (210, 150, 255), emite=True)
        C = quadro_cabeca(J)
        fx.runa(tela, C.pt(J["P"]["cabeca"] * 0.1, J["P"]["cabeca"] * 0.3), (210, 150, 255), 1, forma=2)
        T.aura(tela, tela.alfa > 0, (150, 70, 220), raio=4, forca=0.3, fase=ctx.a)
        T.particulas(tela, v2(self.ancora[0], self.ancora[1] - H * 0.05), (H * 0.2, H * 0.03), (120, 60, 170), n=5,
                     fase=ctx.a, sobe=H * 0.2, emite=False, semente=6)


class CavaleiroOssudo(ComAcabamento, Esqueleto):
    """Cavaleiro de ossos amarelados numa armadura velha: ferrugem, musgo, capa podre e olhos fantasmas."""
    tipo = "cavaleiro"
    CAPA_PODRE = Mat((44, 52, 40), 6, desce=0.4, ruido=0.3, relevo=0.6)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "cavaleiro_ossudo"
        self.osso = Mat((206, 190, 150), 6, relevo=1.0, satur=0.6)
        self.olhos = (120, 200, 255)

    def antes(self, tela, ctx, J):
        capa(tela, J, self.CAPA_PODRE, comprimento=0.62, vento=0.03 * math.sin(ctx.a), rasgos=8, semente=7)

    def acabar(self, tela, ctx, J):
        H = self.H
        corpo = (tela.alfa > 0) & ~tela.emite
        T.manchas(tela, corpo, J["pelvis"], (112, 66, 40), escala=3, quantidade=0.3, forca=0.6, semente=8)   # ferrugem
        T.musgo(tela, corpo, J["pelvis"], cor=(62, 84, 44), alcance=2, quantidade=0.35, semente=9)
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.08, H * 0.2), n=4, passos=4, cor=(40, 34, 30), emite=False)
        if self.vivo(ctx):
            for p in olhos_humanoides(J):
                T.particulas(tela, p, (1, 1), (150, 220, 255), n=3, fase=ctx.a, sobe=H * 0.12, semente=int(p[0]))


class CriaVampiricaAnciao(ComAcabamento, Vampiro):
    """Cria vampírica anciã: pele cinzenta, cabelo branco ralo, capa nobre em farrapos e garras longas."""
    tipo = "cria"
    CAPA_NOBRE = Mat((70, 18, 32), 6, desce=0.35, ruido=0.25, relevo=0.6)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "cria_vampirica_anciao"
        self.pele = Mat((152, 154, 174), 6, satur=0.4)

    def antes(self, tela, ctx, J):
        capa(tela, J, self.CAPA_NOBRE, comprimento=0.55, vento=0.04 * math.sin(ctx.a), rasgos=9, semente=11, gola=True)

    def acabar(self, tela, ctx, J):
        H = self.H
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        rng = random.Random(12)
        for k in range(5):                                                  # cabelo branco ralo
            topo = C.pt(-h * 0.35 + k * h * 0.12, h * 0.42)
            comp = H * rng.uniform(0.1, 0.2)
            tela.tracos([topo, topo + v2(-2 + math.sin(ctx.a + k), comp * 0.6), topo + v2(-3, comp)], (214, 212, 220))
        queixo = C.pt(h * 0.45, -h * 0.4)
        tela.px(queixo[0], queixo[1], SANGUE)                                # sangue no queixo
        tela.px(queixo[0], queixo[1] + 1, SANGUE_ESCURO)
        for lado in ("f", "b"):                                             # garras longas
            m = J["mao_" + lado]
            d = m - J["cotovelo_" + lado]
            a = math.atan2(d[1], d[0])
            for k in (-1, 0, 1):
                p1 = m + v2(math.cos(a + k * 0.3), math.sin(a + k * 0.3)) * H * 0.07
                tela.traco(m, p1, (230, 222, 210))
        if self.vivo(ctx):
            for p in olhos_humanoides(J):
                tela.px(p[0], p[1], (255, 30, 30), emite=True)
                tela.brilho(p, 3, (255, 30, 30), 0.6)


class SombraDoHeroi(ComAcabamento, Guerreiro):
    """Sombra do Herói: o herói copiado vira silhueta escura que se desfaz em fumaça, de olhos acesos e
    com uma distorção sutil (linhas que tremem)."""
    nome = "sombra_do_heroi"
    COR = (18, 12, 28)
    BORDA = (150, 80, 230)

    def acabar(self, tela, ctx, J):
        corpo = tela.alfa > 0
        ys, xs = np.nonzero(corpo)
        tela.cor[ys, xs] = tela.cor[ys, xs] * 0.12 + np.array(self.COR, np.float32) * 0.88
        tela.emite[ys, xs] = False
        for d in ((1, 0), (-1, 0), (0, -1)):
            T.luz_de_borda(tela, corpo, self.BORDA, d, forca=0.4)
        vivo = self.vivo(ctx)
        if vivo:
            for p in olhos_humanoides(J):
                tela.px(p[0], p[1], (235, 215, 255), emite=True)
                tela.brilho(p, 4, (200, 150, 255), 0.7)
        T.esfumacar(tela, tela.alfa > 0, J["peito"], cor=(40, 24, 64), fase=ctx.a, comeu=0.4 if vivo else 0.7, fiapos=10,
                    sobe=10)
        rng = random.Random(ctx.i * 7 + len(ctx.anim))                      # distorção: linhas deslocadas
        for _ in range(3):
            y = rng.randrange(0, tela.h)
            alto = rng.randint(1, 3)
            passo = rng.choice((-2, -1, 1, 2))
            tela.cor[y:y + alto] = np.roll(tela.cor[y:y + alto], passo, axis=1)
            tela.alfa[y:y + alto] = np.roll(tela.alfa[y:y + alto], passo, axis=1)
        T.aura(tela, tela.alfa > 0, self.BORDA, raio=4, forca=0.3, fase=ctx.a)
        corpo = (tela.alfa > 0) & ~tela.emite
        tela.alfa[corpo] = np.minimum(tela.alfa[corpo], 225)
        tela.contorno_cor = (30, 10, 50)
        tela.contorno_alfa = 210


# ============================================================
# ORCS, BICHOS E CONSTRUTOS
# ============================================================

class OrcDeSangue(ComAcabamento, Orc):
    """Orc de pele rubra com cicatrizes rituais que brilham, mão de sangue no peito e cravos de osso."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "orc_de_sangue"
        self.pele = Mat((150, 70, 58), 6, relevo=1.15)

    def acabar(self, tela, ctx, J):
        H = self.H
        vivo = self.vivo(ctx)
        corpo = (tela.alfa > 0) & ~tela.emite
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.07, H * 0.15), n=4, passos=3, cor=(255, 70, 50), emite=vivo,
                     brilho=0.2 if vivo else 0.0, semente=13)
        Q = quadro_tronco(J)
        palma = Q.pt(0.03 * H, J["P"]["tronco"] * 0.6)                       # mão de sangue no peito
        tela.chapado(tela.circulo(palma, H * 0.025) & corpo, SANGUE_ESCURO)
        for k in range(4):
            dedo = palma + J["u"] * (H * 0.035) + v2((k - 1.5) * 1.2, 0)
            tela.chapado(tela.circulo(dedo, 0.8) & corpo, SANGUE_ESCURO)
        C = quadro_cabeca(J)                                                  # faixa negra nos olhos
        h = J["P"]["cabeca"]
        tela.traco(C.pt(0, h * 0.08), C.pt(h * 0.75, h * 0.06), (24, 14, 16), sobre=True)
        for p in olhos_humanoides(J):
            tela.px(p[0], p[1], (255, 50, 40), emite=vivo)
        for lado, esc in (("b", 0.8), ("f", 1.0)):                          # cravos de osso nos ombros
            o = J["ombro_" + lado]
            for k in range(2):
                b = o + v2(-2 + k * 3, -1)
                tela.pintar(tela.poly([b + v2(-1.3, 0), b + v2(1.3, 0), b + v2(-1, -H * 0.07 * esc)]), OSSO)
        lamina = J["mao_f"] + dir_ang(J["arma_f"]) * H * 0.4
        T.escorrer(tela, tela.circulo(lamina, H * 0.08) & corpo, lamina, SANGUE, densidade=0.5, comp=4, fase=ctx.a,
                   molhado=0.4, semente=14)


class AranhaVenenosa(ComAcabamento, Aranha):
    """Aranha venenosa: corpo verde-negro, marcas de alerta amarelas no abdômen e presas pingando veneno."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "aranha_venenosa"
        self.corpo = Mat((42, 56, 36), 6, ruido=0.5, dither=0.6)

    def acabar(self, tela, ctx, P):
        S = self.S
        vivo = not P["morto"]
        abd = tela.circulo(P["abd"], 0.3 * S) & (tela.alfa > 0) & ~tela.emite
        T.listras(tela, abd, P["abd"], (214, 226, 60), eixo=(1, 0.15), espaco=10, larg=2.2, ondula=0.4, forca=0.8)
        ys, xs, u, v = T.locais(tela, abd, P["abd"])
        cruz = (np.abs(u) < 1.5) & (np.abs(v + 2) < 4)                       # ampulheta vermelha
        T.misturar_cor(tela, ys[cruz], xs[cruz], (220, 40, 30), 0.8)
        presas = P["cab"] + v2(0.1 * S, 0.06 * S)
        if vivo:
            for k in range(2):                                              # gotas de veneno que brilham
                g = presas + v2(k * 2, 2 + (ctx.i + k) % 3)
                tela.px(g[0], g[1], (150, 255, 90), emite=True)
            tela.brilho(presas, 0.12 * S, (120, 240, 80), 0.4)


class BesouroDeBronze(ComAcabamento, Besouro):
    """Besouro de bronze: carapaça metálica com rebites, entalhes dourados, azinhavre e olhos âmbar."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "besouro_de_bronze"
        self.casca = metal((176, 118, 62), especular=(255, 228, 170), relevo=1.4, contraste=1.1)

    def antes(self, tela, ctx, P):
        """Crista de barbatanas de bronze rebitadas no dorso (atrás da carapaça, saindo por cima)."""
        S = self.S
        c = P["corpo"]
        for k, x in enumerate((-0.3, -0.15, 0.0, 0.15)):
            topo = c + v2(x * S, -0.28 * S * math.sqrt(max(0.0, 1 - (x / 0.45) ** 2)))
            alt = (0.13 + 0.05 * math.sin((k + 0.5) / 4 * math.pi)) * S
            aleta = [topo + v2(-0.06 * S, 0.06 * S), topo + v2(0.05 * S, 0.06 * S), topo + v2(-0.02 * S, -alt),
                     topo + v2(-0.09 * S, -alt * 0.7)]
            tela.pintar(tela.poly(aleta), self.casca.escuro(k % 2))
            tela.px(*(topo + v2(-0.03 * S, -alt * 0.4)), (255, 236, 190))

    def acabar(self, tela, ctx, P):
        S = self.S
        c = P["corpo"]
        cab, a = P["cab"], P["cab_ang"]                                      # chifre bifurcado de bronze
        garfo = [cab + girar(v2(0.11 * S, -0.16 * S), a), cab + girar(v2(0.2 * S, -0.2 * S), a),
                 cab + girar(v2(0.24 * S, -0.3 * S), a)]
        tela.pintar(tela.corrente(garfo, [0.03 * S, 0.02 * S, 0.5]), self.casca)
        casca = tela.elipse_girada(c, 0.45 * S, 0.28 * S, 0.0) & (tela.alfa > 0) & ~tela.emite
        T.manchas(tela, casca, c, (70, 150, 120), escala=3, quantidade=0.28, forca=0.6, semente=15)   # azinhavre
        for k in range(9):                                                  # rebites na borda
            a = math.pi + k / 8 * math.pi
            p = c + v2(math.cos(a) * 0.4 * S, math.sin(a) * 0.24 * S)
            tela.px(p[0], p[1], (255, 236, 190))
        for k in range(3):                                                  # entalhes em espiral
            r = 0.08 * S + k * 0.06 * S
            pts = [c + v2(math.cos(a) * r, math.sin(a) * r * 0.6 - 0.05 * S) for a in np.linspace(3.4, 6.0, 6)]
            for a_, b_ in zip(pts, pts[1:]):
                for x, y in T.bresenham(a_, b_):
                    if 0 <= x < tela.w and 0 <= y < tela.h and casca[y, x]:
                        tela.cor[y, x] = (110, 70, 34)
        if not P["morto"]:
            olho = P["cab"] + v2(0.06 * S, -0.02 * S)
            tela.px(olho[0], olho[1], (255, 180, 60), emite=True)
            tela.brilho(olho, 4, (255, 170, 60), 0.6)


class LouvaDeusOrquidea(ComAcabamento, LouvaDeus):
    """Louva-a-deus orquídea: rosa e branco como a flor, pétalas nas patas, pintas magenta e olhos verdes."""
    PETALA = Mat((240, 200, 222), 5, relevo=0.9)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "louva_a_deus_orquidea"
        self.corpo = Mat((232, 196, 214), 6, relevo=1.1, satur=0.7)

    def acabar(self, tela, ctx, P):
        S = self.S
        for lado in ("b", "f"):                                             # pétalas nos joelhos
            for L in P["pernas"][lado]:
                j = L[1]
                tela.pintar(tela.elipse_girada(j + v2(-0.02 * S, 0.01 * S), 0.045 * S, 0.022 * S, 0.5),
                            self.PETALA if lado == "f" else self.PETALA.escuro(1))
        fem = P["rapt"][2]
        tela.pintar(tela.elipse_girada(fem + v2(0, 0.02 * S), 0.05 * S, 0.025 * S, -0.4), self.PETALA)
        ponta = P["rapt"][-1]
        tela.chapado(tela.circulo(ponta, 0.015 * S) & (tela.alfa > 0), (200, 40, 140))
        corpo = (tela.alfa > 0) & ~tela.emite
        T.manchas(tela, corpo, P["base"], (190, 50, 150), escala=3, quantidade=0.12, forca=0.7, semente=16)
        if not P["morto"]:
            olho = P["cab"] + v2(0.02 * S, -0.02 * S)
            tela.px(olho[0], olho[1], (190, 255, 90), emite=True)
            tela.brilho(olho, 4, (170, 255, 80), 0.6)


class PalhacoPalido(ComAcabamento, Palhaco):
    """Palhaço pálido: rosto de giz rachado, órbitas negras, sorriso costurado até as orelhas e um balão."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "palhaco_palido"
        self.roupa_a = Mat((206, 202, 198), 6, ruido=0.25, satur=0.2, desce=0.3)
        self.roupa_b = Mat((36, 32, 42), 6, ruido=0.2, desce=0.3)
        self.cara = Mat((238, 236, 234), 6, satur=0.1, relevo=0.9)

    def antes(self, tela, ctx, J):
        H = self.H
        mao = J["mao_b"]
        balao = mao + v2(-H * 0.12 + math.sin(ctx.a) * 1.5, -H * 0.55)
        tela.tracos([mao, lerp(mao, balao, 0.5) + v2(2, 0), balao + v2(0, H * 0.06)], (180, 176, 170))
        tela.pintar(tela.elipse(balao[0], balao[1], H * 0.06, H * 0.075), Mat((180, 24, 34), 6, relevo=1.2,
                                                                                 especular=(255, 200, 200)))

    def acabar(self, tela, ctx, J):
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.82
        for x in (w * 0.22, w * 0.48):                                      # órbitas negras
            c = C.pt(x, h * 0.08)
            tela.chapado(tela.elipse(c[0], c[1], max(1.2, h * 0.12), max(1.2, h * 0.14)), (14, 10, 16))
            tela.px(c[0], c[1], (255, 255, 255), emite=self.vivo(ctx))
        lagrima = C.pt(w * 0.48, -h * 0.05)
        tela.traco(lagrima, lagrima + J["hu"] * (-h * 0.35), (30, 24, 34), sobre=True)
        boca = [C.pt(-w * 0.05, -h * 0.18), C.pt(w * 0.2, -h * 0.32), C.pt(w * 0.5, -h * 0.3), C.pt(w * 0.65, -h * 0.12)]
        tela.tracos(boca, (110, 14, 24))                                     # sorriso costurado até as orelhas
        for a, b in zip(boca, boca[1:]):
            meio = lerp(a, b, 0.5)
            tela.traco(meio + J["hu"] * 1.5, meio - J["hu"] * 1.5, (40, 20, 24))
        canto = boca[-1]
        tela.px(canto[0], canto[1] + 1, SANGUE)
        tela.px(canto[0], canto[1] + 2, SANGUE_ESCURO)
        rosto = tela.circulo(J["cabeca"], h * 0.6) & (tela.alfa > 0) & ~tela.emite
        T.rachaduras(tela, rosto, J["cabeca"], area=(h * 0.3, h * 0.3), n=2, passos=3, cor=(150, 146, 140), emite=False,
                     semente=17)


class GolemDeEscoria(ComAcabamento, Golem):
    """Golem de escória das forjas: pedra negra rachada de lava, pingando metal e soltando fumaça."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = "golem_de_escoria"
        self.pedra = Mat((60, 54, 54), 6, ruido=0.5, dither=0.5, relevo=1.3, satur=0.4)
        self.runa = (255, 120, 30)

    def acabar(self, tela, ctx, J):
        H = self.H
        esfriou = ctx.anim == "morte" and ctx.i >= 2
        corpo = (tela.alfa > 0) & ~tela.emite
        cor = (90, 70, 60) if esfriou else (255, 130, 40)
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.18, H * 0.3), n=9, passos=4, cor=cor, emite=not esfriou,
                     brilho=0.0 if esfriou else 0.25, semente=18)
        for lado in ("f", "b"):                                             # escória derretida pingando dos braços
            m = J["mao_" + lado]
            T.escorrer(tela, tela.circulo(m, H * 0.07) & corpo, m, (230, 100, 30) if not esfriou else (80, 60, 50),
                       densidade=0.45, comp=5, fase=ctx.a, molhado=0.3, semente=19)
        for lado in ("f", "b"):
            fx.fumaca(tela, J["ombro_" + lado] + v2(0, -4), H * 0.04, cor=(70, 64, 66), fase=ctx.a + (lado == "b"), n=3,
                      sobe=12)
        if not esfriou:
            T.particulas(tela, J["peito"], (H * 0.3, H * 0.3), (255, 160, 60), n=8, fase=ctx.a, sobe=H * 0.3, semente=20)


# ============================================================
# ORDEM CAÍDA (forja de monstros)
# ============================================================

class MongeFlagelante(ForjaMonstro):
    """Monge flagelante: capuz e hábito marrom, costas em carne viva, lágrimas de sangue e flagelo de nós."""
    nome = "monge_flagelante"
    H = 74
    estilo = "corte"
    semente = 73
    curvado = 0.32
    magreza = 0.88
    pele = Mat((180, 136, 112), 6, relevo=0.95)
    roupa = Mat((92, 64, 46), 6, desce=0.3, ruido=0.25, relevo=0.7)
    manga = Mat((92, 64, 46), 6, ruido=0.25, relevo=0.7)
    capuz_mat = Mat((80, 56, 40), 6, relevo=0.7)
    barra = 0.04
    rosto = "monge"
    garras = False
    CORDA = Mat((150, 122, 80), 5, ruido=0.5)
    COURO_FLAGELO = Mat((90, 58, 40), 5, relevo=0.8)

    def rosto_monge(self, tela, ctx, J):
        """Capuz fundo com o rosto magro à mostra: olhos fechados e lágrimas de sangue."""
        _, C, face = capuz(tela, J, self.capuz_mat, ponta=0.35, sombra=(30, 18, 16), larg=1.05)
        h = J["P"]["cabeca"]
        w = h * 0.95
        rosto = tela.poly(C.pts([(w * 0.12, h * 0.3), (w * 0.55, h * 0.2), (w * 0.6, -h * 0.4), (w * 0.15, -h * 0.4)])) & face
        tela.pintar(rosto, self.pele, plano=True)
        for x in (w * 0.28, w * 0.48):
            olho = C.pt(x, h * 0.06)
            tela.traco(olho + v2(-1, 0), olho + v2(1, 0), (50, 24, 20))
            for k in range(1, 4):
                tela.px(olho[0], olho[1] + k, SANGUE if k < 3 else SANGUE_ESCURO)
        tela.traco(C.pt(w * 0.3, -h * 0.28), C.pt(w * 0.52, -h * 0.28), (90, 40, 36))

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        costas = tela.poly(Q.pts([(-0.12 * H, T_ * 0.25), (-0.04 * H, T_ * 0.25), (-0.04 * H, T_ * 0.95), (-0.13 * H, T_ * 0.92)]))
        costas &= m
        tela.pintar(costas, self.pele, linha_interna=False)                  # costas em carne viva
        for k in range(5):
            a = Q.pt(-0.12 * H, T_ * (0.32 + k * 0.13))
            tela.traco(a, a + v2(0.07 * H, 0.03 * H), SANGUE, sobre=True)
        T.escorrer(tela, costas, J["pelvis"], SANGUE, densidade=0.4, comp=4, fase=ctx.a, molhado=0.35, semente=21)
        cordao = tela.poly(Q.pts([(-0.09 * H, -0.01 * H), (0.1 * H, 0.0), (0.1 * H, -0.03 * H), (-0.09 * H, -0.04 * H)]))
        tela.pintar(cordao & m, self.CORDA)                                  # cordão de penitente
        for k in range(6):                                                  # contas do terço
            p = Q.pt(0.05 * H, -0.04 * H) + v2(0.5, k * 1.6)
            tela.px(p[0], p[1], (60, 40, 30) if k % 2 else (120, 90, 60))
        return m

    def arma(self, tela, ctx, J):
        """Flagelo: cabo de madeira e cinco tiras de couro com nós ensanguentados."""
        H = self.H
        mao = J["mao_f"]
        d = dir_ang(J["arma_f"])
        tela.pintar(tela.capsula(mao - d * 3, mao + d * 4, 1.1), MADEIRA)
        base = mao + d * 4
        balanco = math.sin(ctx.a) * 0.25 if ctx.anim == "parado" else (1.1 if ctx.golpe else 0.4)
        for k in range(5):
            ang = J["arma_f"] + math.pi * 0.85 + balanco + (k - 2) * 0.18
            pts = [base]
            for j in range(1, 6):
                pts.append(base + dir_ang(ang + j * 0.06 * (k - 2)) * j * H * 0.045)
            tela.tracos(pts, self.COURO_FLAGELO[2] if k % 2 else self.COURO_FLAGELO[1])
            tela.px(pts[-1][0], pts[-1][1], SANGUE)
            tela.px(pts[3][0], pts[3][1], SANGUE_ESCURO)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            T.particulas(tela, base + dir_ang(J["arma_f"] + 2.6) * H * 0.2, (H * 0.08, H * 0.05), SANGUE, n=6, fase=ctx.a,
                         sobe=-4, emite=False)
