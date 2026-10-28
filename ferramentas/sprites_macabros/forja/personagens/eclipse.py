"""O culto do Eclipse (Catedral do Eclipse): todos dividem a mesma paleta (violeta, ouro, marfim e
luz vermelha) e o mesmo símbolo, o SOL NEGRO, para ficarem coerentes entre si.

    sol_negro()            disco negro com a coroa de fogo girando
    vitral()               preenche uma área com cacos de vitral luminosos e linhas de chumbo
    ClerigoDoEclipse       acólito de capuz e véu de malha vermelha, estola dourada e báculo do sol negro
    AnjoCorrompido         anjo caído: asas negras, auréola partida, venda sangrando e espada maculada
    BispoEclipsado         chefe: mitra de ouro, casula carmim, auréola de eclipse e báculo
    BispoEclipsadoVitral   2ª forma: o bispo fundido aos vitrais de um janelão gótico
    DragaoDoEclipse        3ª forma: dragão de escamas violetas, asas de membrana e a coroa do sol negro
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, lerp, dir_ang
from ..humanoide import cabeca_base, quadro_cabeca, quadro_tronco, capuz
from .. import texturas as T
from .. import fx, armas
from ..criaturas.monstro import ForjaMonstro
from ..criaturas.animal import Quadrupede, tabela
from ..criaturas.partes import Pata, Cauda, Asa, Cabeca, direcao

ROXO = Mat((62, 34, 86), 6, desce=0.35, ruido=0.15, relevo=0.7)
ROXO_ESCURO = Mat((44, 24, 62), 6, relevo=0.7)
OURO = metal((222, 176, 84), especular=(255, 244, 200))
OURO_VELHO = metal((150, 118, 66), especular=(220, 190, 130))
CARMIM = Mat((140, 24, 40), 6, relevo=0.8)
MARFIM = Mat((224, 214, 192), 6, desce=0.25, relevo=0.9)
PEDRA = Mat((118, 114, 122), 6, relevo=1.3, ruido=0.35, dither=0.45)
LUZ = (255, 80, 50)
CORONA = [(90, 10, 20), (200, 40, 40), (255, 120, 60), (255, 210, 140), (255, 250, 230)]
CORES_VITRAL = [(210, 44, 60), (54, 96, 210), (236, 196, 76), (140, 64, 190), (64, 170, 116), (230, 110, 50)]


def sol_negro(tela, c, r, fase, forca=1.0, raios=12, emite=True):
    """O símbolo do culto: disco negro com a coroa de fogo girando em volta."""
    c = v2(c)
    for k in range(raios):
        a = fase * 0.5 + k * 2 * math.pi / raios
        comp = r * (0.45 + 0.35 * (k % 2))
        p1, p2 = c + direcao(a - 0.13) * (r * 0.95), c + direcao(a + 0.13) * (r * 0.95)
        tela.chapado(tela.poly([p1, p2, c + direcao(a) * (r + comp)]), CORONA[3] if k % 2 else CORONA[2], emite=emite)
    tela.chapado(tela.circulo(c, r * 1.05) & ~tela.circulo(c, r * 0.9), CORONA[4], emite=emite)
    tela.chapado(tela.circulo(c, r * 0.9), (8, 4, 10))
    borda = tela.circulo(c + v2(-r * 0.15, -r * 0.1), r * 0.88) & ~tela.circulo(c, r * 0.8) & tela.circulo(c, r * 0.9)
    tela.chapado(borda, (60, 30, 80))
    if forca:
        tela.brilho(c, r * 2.3, CORONA[2], 0.45 * forca)


def vitral(tela, mask, ancora, celula=6, opacidade=0.92, semente=7, cores=CORES_VITRAL, brilho=1.0):
    """Cacos de vitral (células de Voronoi fixas à âncora) com linhas de chumbo; os cacos brilham."""
    mask = np.asarray(mask, bool)
    ys, xs, u, v = T.locais(tela, mask, ancora)
    if not len(ys):
        return mask
    gi, gj = np.floor_divide(u, celula), np.floor_divide(v, celula)          # célula da grade de cada pixel
    d1 = np.full(len(ys), 1e9)
    d2 = np.full(len(ys), 1e9)
    dono = np.zeros(len(ys), np.int64)
    for di in (-1, 0, 1):                                                    # só as 9 células vizinhas
        for dj in (-1, 0, 1):
            ci, cj = gi + di, gj + dj
            sx = (ci + T.hash2(ci, cj, semente)) * celula                    # semente fixa de cada célula
            sy = (cj + T.hash2(ci, cj, semente + 1)) * celula
            d = np.hypot(u - sx, v - sy)
            ident = ci * 7919 + cj * 104729
            mais_perto = d < d1
            d2 = np.where(mais_perto, d1, np.minimum(d2, d))
            d1 = np.where(mais_perto, d, d1)
            dono = np.where(mais_perto, ident, dono)
    paleta = np.array(cores, np.float32)
    cor = paleta[(T.hash2(dono, 0, semente + 2) * len(cores)).astype(int) % len(cores)]
    claro = (1.0 + 0.25 * np.clip(1 - d1 / celula, 0, 1)) * brilho       # cada caco mais claro no meio
    tela.cor[ys, xs] = np.clip(cor * claro[:, None], 0, 255)
    tela.alfa[ys, xs] = np.maximum(tela.alfa[ys, xs], int(255 * opacidade))
    tela.emite[ys, xs] = True
    chumbo = (d2 - d1) < 1.1
    tela.cor[ys[chumbo], xs[chumbo]] = (28, 22, 30)
    tela.emite[ys[chumbo], xs[chumbo]] = False
    tela.alfa[ys[chumbo], xs[chumbo]] = 255
    return mask


def cacos_voando(tela, centro, area, fase, n=8, semente=3, tam=3.0):
    """Cacos de vitral flutuando em volta (giram com a fase)."""
    rng = random.Random(semente)
    for k in range(n):
        a = fase * 0.6 + k * 2 * math.pi / n + rng.uniform(-0.3, 0.3)
        p = v2(centro) + v2(math.cos(a) * area[0], math.sin(a) * area[1] - rng.uniform(0, area[1] * 0.5))
        giro = a * 2
        tri = [p + direcao(giro) * tam, p + direcao(giro + 2.2) * tam * 0.7, p + direcao(giro + 4.0) * tam * 0.8]
        tela.chapado(tela.poly(tri), CORES_VITRAL[k % len(CORES_VITRAL)], emite=True)


# ============================================================
# CLÉRIGO DO ECLIPSE
# ============================================================

class ClerigoDoEclipse(ForjaMonstro):
    """Acólito do Eclipse: capuz violeta, véu de malha vermelha no rosto, estola dourada, incensário e báculo."""
    nome = "clerigo_do_eclipse"
    H = 80
    estilo = "magia"
    semente = 81
    curvado = 0.08
    magreza = 0.95
    pele = Mat((206, 176, 156), 6, relevo=0.9)
    roupa = ROXO
    manga = Mat((62, 34, 86), 6, ruido=0.15, relevo=0.7)
    calca = ROXO_ESCURO
    capuz_mat = ROXO_ESCURO
    manto_inteiro = True
    folga_manto = 0.08
    rosto = "veu"
    garras = False
    sangue = ((70, 6, 14), (110, 14, 24))

    def rosto_veu(self, tela, ctx, J):
        _, C, face = capuz(tela, J, self.capuz_mat, ponta=0.45, sombra=(10, 4, 12), larg=1.05)
        h = J["P"]["cabeca"]
        w = h * 0.95
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        for x in (w * 0.28, w * 0.48):                                      # olhos atrás do véu
            p = C.pt(x, h * 0.06)
            tela.px(p[0], p[1], LUZ if vivo else (60, 20, 20), emite=vivo)
        ys, xs = np.nonzero(face)
        malha = ((xs + ys) % 2 == 0)                                        # véu de malha vermelha
        tela.cor[ys[malha], xs[malha]] = (120, 20, 34)
        tela.traco(C.pt(w * 0.05, h * 0.32), C.pt(w * 0.62, h * 0.26), OURO[4], sobre=True)   # corrente na testa
        tela.px(*C.pt(w * 0.35, h * 0.3), (255, 220, 120))

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        for x in (0.02, 0.07):                                              # estola dourada até a barra
            faixa = tela.poly(Q.pts([(x * H, T_ * 0.95), ((x + 0.03) * H, T_ * 0.95), ((x + 0.04) * H, -0.5 * H),
                                     ((x + 0.01) * H, -0.5 * H)])) & m
            tela.pintar(faixa, CARMIM)
            ys, xs = np.nonzero(faixa)
            ouro = (ys % 4 == 0)
            tela.cor[ys[ouro], xs[ouro]] = OURO[4]
        sol_negro(tela, Q.pt(0.05 * H, T_ * 0.7), H * 0.035, ctx.a, forca=0.4)
        return m

    def arma(self, tela, ctx, J):
        H = self.H
        topo = armas.cajado(tela, J["mao_f"], J["arma_f"], H * 0.5, OURO_VELHO, atras=H * 0.45)
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        sol_negro(tela, topo + dir_ang(J["arma_f"]) * (H * 0.05), H * 0.055, ctx.a * 2, forca=1.0 if vivo else 0.0,
                  emite=vivo)
        if ctx.anim == "ataque" and ctx.i in (1, 2):                       # luz eclipsada
            c = topo + dir_ang(J["arma_f"]) * (H * 0.05)
            for k in range(8):
                a = k * math.pi / 4 + ctx.a
                tela.traco(c + direcao(a) * (H * 0.08), c + direcao(a) * (H * (0.2 if ctx.i == 1 else 0.14)), CORONA[3],
                           emite=True)
            tela.brilho(c, H * 0.35, LUZ, 0.6)
        mao = J["mao_b"]                                                    # incensário balançando
        bal = math.sin(ctx.a) * H * 0.04
        fim = mao + v2(bal, H * 0.14)
        tela.traco(mao, fim, OURO[3])
        tela.pintar(tela.circulo(fim + v2(0, 2), H * 0.025), OURO)
        if vivo:
            T.particulas(tela, fim, (2, 2), (150, 110, 170), n=4, fase=ctx.a, sobe=H * 0.2, emite=False, semente=2)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        if not (ctx.anim == "morte" and ctx.i >= 2):
            T.luz_de_borda(tela, corpo, (255, 90, 60), (1, 0), forca=0.25)


# ============================================================
# ANJO CORROMPIDO
# ============================================================

class AnjoCorrompido(ForjaMonstro):
    """Anjo caído: asas negras de penas, auréola partida flutuando, venda que sangra e espada maculada."""
    nome = "anjo_corrompido"
    H = 84
    estilo = "corte"
    semente = 85
    magreza = 0.9
    pele = Mat((178, 170, 180), 6, relevo=1.0, satur=0.3)
    roupa = Mat((38, 30, 44), 6, desce=0.3, ruido=0.15, relevo=0.6)
    barra = 0.04
    armadura = metal((150, 118, 70), ruido=0.3, especular=(230, 200, 140))
    rosto = "venda"
    garras = False
    PENAS = Mat((40, 34, 46), 6, relevo=0.9, especular=(140, 120, 170))
    ESPADA = metal((70, 64, 76), especular=(255, 120, 100))

    def atras(self, tela, ctx, J):
        H = self.H
        raiz = lerp(J["ombro_b"], J["pescoco"], 0.4) - self.frente_do_corpo(J) * (H * 0.03)
        asa = Asa(envergadura=0.78, estilo="penas")
        abre = 1.0 if ctx.golpe else 0.85
        bater = -0.15 + 0.06 * math.sin(ctx.a) + J["giro"]
        asa.desenhar(tela, asa.pontos(raiz + v2(H * 0.04, -H * 0.02), H, abre, bater - 0.35), self.PENAS.escuro(1), H)
        asa.desenhar(tela, asa.pontos(raiz, H, abre, bater), self.PENAS, H)
        super().atras(tela, ctx, J)

    def rosto_venda(self, tela, ctx, J):
        m, C = cabeca_base(tela, J, self.pele, larg=0.5)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.pintar(tela.poly(C.pts([(-w * 0.45, h * 0.2), (w * 0.62, h * 0.18), (w * 0.62, -h * 0.02), (-w * 0.45, 0)])),
                    Mat((30, 24, 32), 5, relevo=0.6))                       # venda
        for x in (w * 0.3, w * 0.5):                                        # sangue escorrendo da venda
            p = C.pt(x, -h * 0.02)
            for k in range(1, 4):
                tela.px(p[0], p[1] + k, (150, 14, 24) if k < 3 else (80, 6, 14))
        rng = random.Random(self.semente)
        for k in range(6):                                                  # cabelo negro comprido
            topo = C.pt(-w * 0.45 + k * w * 0.15, h * 0.45)
            comp = self.H * rng.uniform(0.15, 0.26)
            tela.tracos([topo, topo + v2(-2 + math.sin(ctx.a + k), comp * 0.5), topo + v2(-4, comp)], (24, 20, 28))
        if not (ctx.anim == "morte" and ctx.i >= 2):                        # auréola partida
            centro = J["cabeca"] + J["hu"] * (h * 0.9)
            for k, (a0, a1) in enumerate(((0.2, 1.6), (2.0, 3.2), (3.6, 5.6))):
                pedaco = [centro + v2(math.cos(a) * h * 0.6, math.sin(a) * h * 0.18) + v2(0, -k * 0.8 + math.sin(ctx.a + k))
                          for a in np.linspace(a0, a1, 6)]
                tela.tracos(pedaco, OURO_VELHO[4] if k != 1 else (255, 90, 60), emite=True)
            tela.brilho(centro, h * 0.9, (255, 120, 80), 0.3)

    def arma(self, tela, ctx, J):
        H = self.H
        armas.espada(tela, J["mao_f"], J["arma_f"], H * 0.55, self.ESPADA, OURO_VELHO, Mat((40, 30, 30), 4),
                              larg=1.8, sangue=0.3)
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        if vivo:                                                            # chama vermelha da espada maculada
            d = dir_ang(J["arma_f"])
            for t in (0.3, 0.55, 0.8):
                fx.chama(tela, J["mao_f"] + d * (H * 0.55 * t), H * 0.06, H * 0.04, fx.FOGO, fase=ctx.a + t * 4,
                         linguas=2, brilho=False)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            armas.rastro(tela, J["ombro_f"], H * 0.66, H * 0.72, -0.6, 2.0, cor=(255, 90, 70))

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.08, H * 0.2), n=5, passos=4, cor=LUZ, emite=vivo,
                     brilho=0.25 if vivo else 0.0, semente=86)
        if vivo:
            T.particulas(tela, J["ombro_b"], (H * 0.3, H * 0.2), (40, 34, 46), n=5, fase=ctx.a, sobe=-H * 0.3,
                         emite=False, semente=87)                           # penas caindo
            T.aura(tela, tela.alfa > 0, (200, 40, 50), raio=4, forca=0.3, fase=ctx.a)


# ============================================================
# BISPO ECLIPSADO (1ª e 2ª formas)
# ============================================================

class BispoEclipsado(ForjaMonstro):
    """O Bispo Eclipsado: mitra de ouro com o sol negro, casula carmim bordada, auréola de eclipse e báculo."""
    nome = "bispo_eclipsado"
    H = 92
    larg, alt = 184, 220
    ancora = (82, 217)
    estilo = "magia"
    semente = 89
    curvado = 0.05
    magreza = 1.15
    pele = Mat((206, 178, 156), 6, relevo=0.9)
    roupa = MARFIM
    manga = Mat((224, 214, 192), 6, relevo=0.9)
    calca = MARFIM
    manto_inteiro = True
    folga_manto = 0.12
    rosto = "bispo"
    garras = False
    olho_cor = (255, 210, 90)

    def atras(self, tela, ctx, J):
        H = self.H
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        if vivo:                                                            # auréola: o sol negro atrás da cabeça
            sol_negro(tela, J["cabeca"] - self.frente_do_corpo(J) * (H * 0.06) + J["hu"] * (H * 0.02), H * 0.13, ctx.a,
                      forca=0.8)
        Q = quadro_cabeca(J)                                                # fitas da mitra caindo nas costas
        h = J["P"]["cabeca"]
        for k in range(2):
            topo = Q.pt(-h * 0.45, h * 0.1 - k * 2)
            tela.pintar(tela.corrente([topo, topo + v2(-2, H * 0.12), topo + v2(-3 + math.sin(ctx.a) * 1.5, H * 0.22)],
                                      [1.6, 1.4, 1.2]), CARMIM if k else CARMIM.escuro(1))
        super().atras(tela, ctx, J)

    def rosto_bispo(self, tela, ctx, J):
        """Rosto velho e magro, olhos de ouro, barba branca e a mitra alta com o sol negro."""
        m, C = cabeca_base(tela, J, self.pele, larg=0.5)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.chapado(tela.elipse_girada(C.pt(w * 0.35, h * 0.08), max(1.2, w * 0.13), max(1.0, h * 0.08), 0), (30, 18, 16))
        self._olho(tela, C.pt(w * 0.36, h * 0.08), ctx, raio=3)
        barba = tela.poly(C.pts([(w * 0.0, -h * 0.15), (w * 0.62, -h * 0.2), (w * 0.4, -h * 0.75), (w * 0.1, -h * 0.65)]))
        tela.pintar(barba, Mat((214, 210, 204), 5, relevo=0.8))
        hu = J["hu"]
        frente = v2(-hu[1], hu[0])
        base = J["cabeca"] + hu * (h * 0.38)
        mitra = [base - frente * (h * 0.55), base + frente * (h * 0.55), base + frente * (h * 0.32) + hu * (h * 1.0),
                 base + hu * (h * 1.35), base - frente * (h * 0.32) + hu * (h * 1.0)]
        mm = tela.pintar(tela.poly(mitra), MARFIM.claro(1))
        tela.pintar(tela.poly([base - frente * (h * 0.08), base + frente * (h * 0.08), base + hu * (h * 1.3)]) & mm, OURO)
        tela.pintar(tela.capsula(base - frente * (h * 0.55), base + frente * (h * 0.55), h * 0.1, h * 0.1), OURO)
        sol_negro(tela, base + hu * (h * 0.6), h * 0.2, ctx.a, forca=0.3)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        casula = tela.poly(Q.pts([(-0.06 * H, T_ * 0.98), (0.12 * H, T_ * 0.98), (0.15 * H, -0.3 * H), (-0.04 * H, -0.32 * H)])) & m
        tela.pintar(casula, CARMIM)                                          # casula carmim
        ys, xs = np.nonzero(casula)
        tela.cor[ys[(ys % 6 == 0)], xs[(ys % 6 == 0)]] = OURO[3]            # bordado dourado
        cruz = tela.poly(Q.pts([(0.03 * H, T_ * 0.95), (0.06 * H, T_ * 0.95), (0.07 * H, -0.3 * H), (0.04 * H, -0.3 * H)]))
        tela.pintar(cruz & casula, OURO)
        tela.pintar(tela.poly(Q.pts([(-0.03 * H, T_ * 0.7), (0.13 * H, T_ * 0.72), (0.13 * H, T_ * 0.64), (-0.03 * H, T_ * 0.62)]))
                    & casula, OURO)
        sol_negro(tela, Q.pt(0.05 * H, T_ * 0.68), H * 0.035, ctx.a, forca=0.4)
        return m

    def arma(self, tela, ctx, J):
        """Báculo de ouro com a volta em espiral e o sol negro dentro; dispara o raio da aurora."""
        H = self.H
        d = dir_ang(J["arma_f"])
        n = v2(-d[1], d[0])
        a, topo = armas.haste(tela, J["mao_f"], J["arma_f"], H * 0.45, H * 0.55, OURO, larg=1.5)
        espiral = [topo + d * (H * 0.03 * math.sin(t)) + n * (H * 0.06 * (1 - math.cos(t)) * (1 - t / 9))
                   for t in np.linspace(0, 5.5, 12)]
        tela.pintar(tela.corrente(espiral, [1.6] * 12), OURO)
        centro = topo + n * (H * 0.05)
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        sol_negro(tela, centro, H * 0.035, ctx.a * 2, forca=0.6 if vivo else 0, emite=vivo)
        if ctx.anim == "ataque" and ctx.i in (1, 2):                       # raio da aurora
            f = self.frente_do_corpo(J)
            fim = centro + f * (H * (1.0 if ctx.i == 1 else 0.7)) + v2(0, H * 0.25)
            for k, cor in ((-1, CORONA[2]), (0, CORONA[4]), (1, CORONA[2])):
                tela.traco(centro + v2(0, k), fim + v2(0, k), cor, emite=True)
            tela.brilho(lerp(centro, fim, 0.5), H * 0.3, (255, 200, 120), 0.5)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        if not (ctx.anim == "morte" and ctx.i >= 2):
            T.luz_de_borda(tela, corpo, (255, 100, 60), (1, 0), forca=0.3)
            T.particulas(tela, J["peito"], (self.H * 0.35, self.H * 0.4), CORONA[3], n=6, fase=ctx.a, sobe=self.H * 0.3,
                         semente=90)


class BispoEclipsadoVitral(BispoEclipsado):
    """2ª forma: o Bispo abre os braços diante de um janelão gótico e os vitrais se fundem ao corpo dele."""
    nome = "bispo_eclipsado_vitral"
    larg, alt = 220, 239
    ancora = (110, 236)
    estilo = "magia"
    base = dict(braco_f=(2.3, 0.4), braco_b=(2.55, 0.3), arma_f=0.2)
    MOLDURA = Mat((98, 92, 104), 6, relevo=1.2, ruido=0.3)

    def janela(self, tela, ctx):
        H = self.H
        cx, chao = self.ancora
        topo = chao - H * 2.45
        larg = H * 0.85
        arranque = chao - H * 1.5                                            # onde o arco começa a curvar
        arco = [v2(cx - larg, chao - H * 0.05)]
        for t in np.linspace(0, 1, 12):                                     # arco ogival (lado esquerdo)
            arco.append(v2(cx - larg * math.cos(t * math.pi / 2) ** 0.8, arranque - (arranque - topo) * math.sin(t * math.pi / 2)))
        arco += [v2(2 * cx - p[0], p[1]) for p in reversed(arco[1:-1])]     # espelha para o lado direito
        arco += [v2(cx + larg, chao - H * 0.05)]
        fora = tela.poly(arco)
        base = v2(cx, chao)
        dentro = tela.poly([base + (p - base) * v2(0.88, 0.94) + v2(0, -H * 0.03) for p in arco])
        tela.pintar(fora & ~dentro, self.MOLDURA)
        quebrado = ctx.anim == "morte" and ctx.i >= 1
        vitral(tela, dentro & ~(tela.circulo(v2(cx + H * 0.1, chao - H * 1.1), H * 0.4) if quebrado else np.zeros_like(dentro)),
               v2(cx, chao), celula=7, semente=91, brilho=0.72)
        for k in range(1, 4):                                               # montantes de pedra
            x = cx - larg * 0.88 + k * larg * 0.44
            tela.traco(v2(x, chao - H * 0.06), v2(x, chao - H * 1.6), self.MOLDURA[1])
        rosa = v2(cx, chao - H * 1.85)
        tela.chapado(tela.circulo(rosa, H * 0.28) & ~tela.circulo(rosa, H * 0.25), self.MOLDURA[2])
        sol_negro(tela, rosa, H * 0.16, ctx.a, forca=0.0 if quebrado else 0.8)
        if not quebrado:
            tela.brilho(v2(cx, chao - H * 1.2), H * 1.0, (255, 200, 140), 0.25)

    def atras(self, tela, ctx, J):
        self.janela(tela, ctx)
        super().atras(tela, ctx, J)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        baixo = corpo & (np.arange(tela.h)[:, None] > J["pelvis"][1] + H * 0.05)    # a barra do manto vira vitral
        vitral(tela, baixo & (T.hash2(np.arange(tela.w)[None, :] // 5, np.arange(tela.h)[:, None] // 5, 3) < 0.55),
               J["pelvis"], celula=5, semente=92)
        cacos_voando(tela, J["peito"], (H * 0.55, H * 0.35), ctx.a, n=9, semente=93)
        figura = corpo | T.borda(tela.alfa > 0, (1, 0))
        T.aura(tela, figura, (255, 230, 180), raio=3, forca=0.5)                     # contorno de luz: destaca do vitral
        T.rachaduras(tela, corpo, J["peito"], area=(H * 0.1, H * 0.2), n=5, passos=4, cor=(255, 220, 160), emite=True,
                     brilho=0.25, semente=94)


# ============================================================
# DRAGÃO DO ECLIPSE (3ª forma)
# ============================================================

class DragaoDoEclipse(Quadrupede):
    """O Dragão do Eclipse: escamas violeta-negras com placas de ouro, asas de membrana rasgadas, coroa de
    chifres e a coroa do sol negro ardendo atrás dele. Cospe o sopro do eclipse e se estilhaça ao morrer."""
    nome = "dragao_do_eclipse"
    S = 96
    proporcao = (2.6, 2.2)
    pe = 0.5
    cobertura = "escamas"
    mat = Mat((56, 38, 74), 6, relevo=1.25, especular=(200, 160, 240), ruido=0.08)
    mat_barriga = (206, 166, 96)
    mat_asa = Mat((70, 34, 82), 6, relevo=0.5, ruido=0.1)
    comprimento = 0.62
    altura_anca = 0.44
    altura_cernelha = 0.52
    arco = -0.07
    perfil = ((0.0, 0.13, 0.12), (0.45, 0.12, 0.14), (1.0, 0.15, 0.2))
    pescoco = (0.27, -0.4)
    pescoco_larg = (0.13, 0.085)
    cabeca_ang = 0.3
    cabeca = Cabeca(estilo="reptil", tam=0.19, focinho=0.19, olho_cor=(255, 110, 40), mat_chifre=OURO_VELHO,
                    chifres=[(-0.04, -0.04, 0.24, -2.75, 0.8, 0.03), (-0.01, -0.045, 0.18, -2.45, 0.6, 0.024),
                             (0.02, -0.04, 0.12, -2.1, 0.4, 0.018)])
    pata_tras = Pata(comp=(0.22, 0.2, 0.12), grossura=(0.11, 0.085, 0.06, 0.05), joelho="frente", metatarso=0.5,
                     cobertura="escamas", garra=(240, 210, 130))
    pata_frente = Pata(comp=(0.2, 0.19, 0.07), grossura=(0.095, 0.07, 0.055, 0.048), joelho="tras", metatarso=0.15,
                       cobertura="escamas", garra=(240, 210, 130))
    cauda = Cauda(comp=0.9, grossura=(0.1, 0.08, 0.05, 0.015), segmentos=10, ang=math.pi - 0.25, curva=0.9, estilo="espinhos")
    asa = Asa(envergadura=1.05, estilo="membrana", rasgos=3, garra=(240, 210, 130), osso=Mat((170, 130, 100), 5),
              opacidade=0.85, detalhada=True)
    sangue = ((60, 10, 40), (110, 30, 70))
    semente = 95

    def movimento(self, ctx):
        m = super().movimento(ctx)
        m["abertura"] = 0.85 + 0.08 * math.sin(ctx.a)
        m["bater"] = -0.35 + 0.08 * math.sin(ctx.a)                         # asas abertas para trás e para cima
        if ctx.anim == "ataque":                                            # empina, abre as asas e cospe
            m.update(abertura=tabela(ctx, [0.9, 1.0, 1.0, 0.85]), bater=tabela(ctx, [-0.55, -0.15, -0.2, -0.3]),
                     incl=tabela(ctx, [-0.22, -0.12, -0.08, 0.0]), cab=tabela(ctx, [-0.35, 0.1, 0.15, 0.05]),
                     boca=tabela(ctx, [0.3, 1.0, 0.9, 0.2]), avanco=tabela(ctx, [-0.06, 0.05, 0.06, 0.02]),
                     passo=tabela(ctx, [0.0, 0.05, 0.05, 0.0]), salto=tabela(ctx, [0.06, 0.0, 0.0, 0.0]))
        elif ctx.anim == "morte":
            m["abertura"] = tabela(ctx, [0.8, 0.6, 0.45, 0.35])
            m["bater"] = tabela(ctx, [0.0, -0.3, -0.6, -0.7])
        return m

    def coroa(self, tela, ctx, P):
        S = self.S
        c = P["C"] + P["cima"] * (0.62 * S) - P["d"] * (0.3 * S)
        if P["anim"] == "morte" and P["i"] >= 1:                            # a coroa se estilhaça
            for k in range(10):
                a = k * 0.63 + P["i"] * 0.4
                p = c + direcao(a) * (0.2 * S + P["i"] * 0.06 * S) + v2(0, P["i"] * 0.06 * S)
                tri = [p, p + direcao(a + 2) * (0.03 * S), p + direcao(a + 4) * (0.025 * S)]
                tela.chapado(tela.poly(tri), CORONA[2 + k % 2] if P["i"] < 3 else (70, 30, 40), emite=P["i"] < 3)
            return
        sol_negro(tela, c, 0.24 * S, ctx.a, forca=1.0, raios=16)

    def atras(self, tela, ctx, P):
        self.coroa(tela, ctx, P)
        super().atras(tela, ctx, P)

    def detalhes(self, tela, ctx, P, corpo):
        S = self.S
        vivo = not P["morto"] and not (P["anim"] == "morte" and P["i"] >= 2)
        for k, t in enumerate(np.linspace(0.05, 1.0, 9)):                   # espinhos dorsais de ouro
            i = int(t * (len(P["espinha"]) - 1))
            base = P["espinha"][i] + P["cima"] * (self._perfil(t)[0] * S * 0.85)
            alto = S * (0.05 + 0.03 * (k % 2))
            ponta = base + P["cima"] * alto - P["d"] * (alto * 0.5)
            lado = P["d"] * (S * 0.02)
            tela.pintar(tela.poly([base - lado, base + lado, ponta]), OURO_VELHO)
        peito = lerp(P["A"], P["C"], 0.78) - P["cima"] * (0.06 * S)
        T.rachaduras(tela, corpo, peito, area=(0.15 * S, 0.1 * S), n=7, passos=4, cor=CORONA[3] if vivo else (80, 50, 60),
                     emite=vivo, brilho=0.35 if vivo else 0.0, semente=96)
        if vivo:
            tela.brilho(peito, 0.25 * S, CORONA[2], 0.35)

    def efeitos(self, tela, ctx, P):
        S = self.S
        vivo = not (P["anim"] == "morte" and P["i"] >= 2)
        boca = self.ponta_da_boca(P)
        if vivo:
            tela.brilho(boca, 0.06 * S, CORONA[3], 0.4)
            T.particulas(tela, P["centro"] + v2(0, -0.2 * S), (0.5 * S, 0.2 * S), CORONA[3], n=8, fase=P["fase"],
                         sobe=0.4 * S, semente=97)
        if P["golpe"]:                                                      # sopro do eclipse: cone contínuo
            d = direcao(P["ang_cab"] + 0.12)
            n = v2(-d[1], d[0])
            comp = (1.0 if P["i"] == 1 else 0.75) * S
            cores = [(70, 20, 110), (150, 50, 220), (230, 130, 255), (255, 230, 250)]
            for k, (cor, abre) in enumerate(zip(cores, (0.24, 0.17, 0.1, 0.04))):
                lado_a, lado_b = [], []
                for t in np.linspace(0, 1, 9):                              # bordas onduladas do cone
                    onda = math.sin(t * 9 + P["fase"] * 2 + k) * 0.015 * S
                    largura = (0.02 * S + abre * S * t) + onda
                    p = boca + d * (comp * t * (1 - k * 0.08))
                    lado_a.append(p + n * largura)
                    lado_b.append(p - n * largura)
                tela.chapado(tela.poly(lado_a + lado_b[::-1]), cor, emite=True)
            for k in range(3):                                              # ondas de calor (distorção)
                c = boca + d * (comp * (0.4 + k * 0.2))
                tela.tracos([c + n * (0.2 * S) + d * 2, c + n * (0.1 * S), c + n * (0.15 * S) - d * 2], (180, 120, 220))
            T.particulas(tela, boca + d * comp * 0.7, (0.25 * S, 0.12 * S), CORONA[3], n=12, fase=P["fase"], sobe=4,
                         semente=98)
            tela.brilho(boca + d * comp * 0.5, 0.5 * S, (200, 80, 220), 0.55)
        if P["anim"] == "morte" and P["i"] >= 2:
            fx.fumaca(tela, P["centro"], 0.12 * S, cor=(60, 40, 70), fase=P["fase"], n=6, sobe=16)
