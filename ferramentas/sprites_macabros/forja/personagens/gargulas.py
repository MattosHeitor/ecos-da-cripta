"""Gárgulas Vivas da Catedral do Eclipse: três ramificações fiéis às gárgulas góticas de verdade
(pedra esculpida, asas de morcego, chifres, bocas de calha, garras, desgaste, líquen e musgo).

    Gargula            base das três (forja de animais) com o ciclo PEDRA -> VIVA: a linha extra "despertar"
                       leva a estátua até a pose viva (as fendas acendem, os olhos abrem, a poeira cai);
                       na morte a luz apaga, ela volta a ser pedra e desmorona em entulho
    CabecaDePedra      cabeças esculpidas: careta de demônio, bica d'água, leão de juba e bode
    GargulaSentinela   a clássica: sentada nas patas de trás, asas fechadas como capa, chifres e careta
    GargulaCalha       a bica: corpo comprido e baixo, pescoço esticado, calha no dorso e boca que verte água
    GargulaQuimera     leão (juba esculpida), bode (cabeça e chifres saindo das costas) e ave (asas de penas
                       e garras de águia)
"""
import math
import random

import numpy as np

from ..anim import Ctx
from ..motor import Mat, v2, lerp, girar, misturar
from .. import texturas as T
from .. import fx
from ..criaturas.animal import Quadrupede, tabela
from ..criaturas.partes import Pata, Cauda, Asa, Cabeca, direcao

LUZ_VEIOS = (255, 96, 50)            # a luz vermelha do Eclipse correndo nas fendas (a mesma da catedral)
POEIRA = (164, 156, 146)
BOCA_PEDRA = (30, 24, 28)
ORBITA = (22, 16, 20)
DENTE_PEDRA = (200, 194, 180)
GARRA_PEDRA = (206, 200, 206)

GRANITO = Mat((118, 116, 126), 6, relevo=1.35, ruido=0.4, dither=0.5)
PEDRA_MOLHADA = Mat((98, 106, 102), 6, relevo=1.3, ruido=0.45, dither=0.5, especular=(190, 214, 214))
ARENITO = Mat((142, 128, 106), 6, relevo=1.35, ruido=0.4, dither=0.5)
AGUA = Mat((112, 152, 178), 4, relevo=0.4, especular=(235, 248, 255))


# ============================================================
# PEDRA: desgaste, estátua e desmoronamento
# ============================================================

def misturar_movimentos(a, b, t):
    """Mistura dois movimentos (só os números): t = 0 é 'a' (a estátua), t = 1 é 'b' (a pose viva)."""
    m = dict(b)
    for k, vb in b.items():
        va = a.get(k)
        numeros = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (va, vb))
        if numeros and k != "i":
            m[k] = va * (1 - t) + vb * t
    return m


def esculpir(tela, mask, ancora, semente, liquen, musgo, umida=False):
    """Pedra velha de catedral: poros, faixas de chuva escorrida, fuligem, líquen e musgo no que é de cima."""
    mask = T.pintado(tela, mask)
    ys, xs, u, v = T.locais(tela, mask, ancora)
    if not len(ys):
        return
    poros = T.hash2(u, v, semente) < 0.1
    T.multiplicar(tela, ys[poros], xs[poros], 0.86)
    chuva = T.ruido_suave(u, v * 0.12, 2.5, semente + 1) > 0.66                  # faixas verticais da chuva
    T.multiplicar(tela, ys[chuva], xs[chuva], 0.84)
    T.manchas(tela, mask, ancora, (52, 50, 54), escala=4, quantidade=0.25, forca=0.35, semente=semente + 2)
    T.manchas(tela, mask, ancora, liquen, escala=3, quantidade=0.18, forca=0.5, semente=semente + 3)
    T.musgo(tela, mask, ancora, cor=musgo, alcance=2 if umida else 1, quantidade=0.45 if umida else 0.25, semente=semente + 4)
    if umida:
        T.escorrer(tela, mask, ancora, (58, 70, 72), densidade=0.18, comp=3, molhado=0.35, semente=semente + 5, gota=False)
        T.brilho_umido(tela, mask, ancora, densidade=0.06, cor=(200, 220, 222), semente=semente + 6)


def petrificar(tela, quanto):
    """A estátua: a cor cai para o cinza frio da pedra parada, com poeira assentada por cima (quanto 0..1)."""
    corpo = (tela.alfa > 0) & ~tela.emite
    ys, xs = np.nonzero(corpo)
    if not len(ys) or quanto <= 0:
        return
    c = tela.cor[ys, xs]
    cinza = c.mean(axis=1, keepdims=True) * np.array((0.98, 0.98, 1.02), np.float32)
    alvo = cinza * 0.8 + np.array(POEIRA, np.float32) * 0.2
    tela.cor[ys, xs] = c * (1 - 0.55 * quanto) + alvo * (0.55 * quanto)
    ys, xs = np.nonzero(T.borda(corpo, (0, -1)))
    T.misturar_cor(tela, ys, xs, POEIRA, 0.45 * quanto)


def lascas(tela, centro, area, cor, n, queda, semente=0):
    """Lascas de pedra se soltando do corpo e caindo (no despertar e ao apanhar)."""
    rng = random.Random(semente)
    for _ in range(n):
        p = v2(centro) + v2(rng.uniform(-area[0], area[0]), rng.uniform(-area[1], area[1]) + queda * rng.uniform(0.5, 1.0))
        tela.px(p[0], p[1], cor)
        if rng.random() < 0.4:
            tela.px(p[0] + 1, p[1], misturar(cor, (40, 38, 44), 0.4))


def desmoronar(tela, chao, forca, semente=0, bloco=5):
    """A pedra cede: o sprite se parte em blocos (como cantaria) que escorregam até o chão e viram
    um monte de entulho. forca 0 = inteiro, 1 = só entulho."""
    ys, xs = np.nonzero(tela.alfa > 0)
    if not len(ys) or forca <= 0:
        return
    fileira = ys // bloco
    coluna = (xs + (fileira % 2) * (bloco // 2)) // bloco               # blocos desencontrados
    h1, h2, h3 = (T.hash2(coluna, fileira, semente + k) for k in range(3))
    altura = np.maximum(0, chao - fileira * bloco)                       # o mesmo para o bloco inteiro
    ny = np.minimum(chao, ys + (altura * forca * (0.72 + 0.22 * h1)).astype(int))
    nx = np.clip(xs + ((h2 - 0.5) * altura * forca * 0.9).astype(int), 0, tela.w - 1)
    fica = h3 > 0.3 * forca                                              # um pouco vira pó
    face = np.ones(len(ys), np.float32)                                  # aresta de cima clara, de baixo escura
    face[ys % bloco == 0] = 1 + 0.14 * min(1.0, forca * 3)
    face[ys % bloco == bloco - 1] = 1 - 0.22 * min(1.0, forca * 3)
    cor, alfa, parte = tela.cor.copy(), tela.alfa.copy(), tela.parte.copy()
    tela.cor[:] = 0
    tela.alfa[:] = 0
    tela.parte[:] = 0
    tela.emite[:] = False
    tela.luz_extra[:] = 0
    tela.halo[:] = 0
    sel = np.nonzero(fica)[0]
    sel = sel[np.argsort(ys[sel], kind="stable")]                       # os de baixo ficam por cima
    oy, ox, ty, tx = ys[sel], xs[sel], ny[sel], nx[sel]
    tela.cor[ty, tx] = np.clip(cor[oy, ox] * face[sel][:, None], 0, 255)
    tela.alfa[ty, tx] = alfa[oy, ox]
    tela.parte[ty, tx] = parte[oy, ox]


# ============================================================
# CABEÇAS ESCULPIDAS
# ============================================================

class CabecaDePedra(Cabeca):
    """Cabeças esculpidas. Os olhos são órbitas vazias: quem acende a luz deles é a gárgula, que sabe
    o quanto está viva. A cada desenho guarda 'olhos' (posições) e 'bica' (de onde sai a água)."""

    def __init__(self, estilo="careta", **kw):
        super().__init__(estilo=estilo, presas=False, olho_brilho=False, **kw)
        self.olhos = []
        self.bica = None

    def desenhar(self, *args, **kw):
        self.olhos, self.bica = [], None
        return super().desenhar(*args, **kw)

    def _orbita(self, tela, c, k, S, rx=0.016, ry=0.011):
        tela.chapado(tela.elipse(c[0], c[1], max(1.0, rx * k * S), max(0.8, ry * k * S)), ORBITA)
        self.olhos.append(c)

    def _boca(self, tela, L, k, mat, abre, pontos_mandibula, dobradica, frente):
        """Mandíbula girada na dobradiça, céu da boca escuro e as duas fileiras de dentes de pedra."""
        mandibula = [girar(p, abre, dobradica) for p in L.pts(pontos_mandibula)]
        tela.chapado(tela.poly([L(*frente[0]), L(*frente[1]), mandibula[1], dobradica]), BOCA_PEDRA)
        m = tela.pintar(tela.poly(mandibula), mat.escuro(1))
        self._dentes(tela, L(*frente[0]) + v2(0, 1), L(*frente[1]) + v2(0, 1), 4, cor=DENTE_PEDRA)
        if abre > 0.2:
            self._dentes(tela, lerp(mandibula[0], mandibula[1], 0.3), mandibula[1], 3, para_baixo=False, cor=DENTE_PEDRA)
        return m, mandibula

    # ----- careta de demônio (a gárgula clássica) -----
    def _careta(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        orelha = L.pts([(-0.01 * k, -0.045 * k), (-0.12 * k, -0.12 * k), (-0.05 * k, -0.015 * k)])     # de morcego
        tela.pintar(tela.poly(orelha), mat.escuro(1))
        abre = 0.32 + boca * 0.5                                           # a careta nunca fecha de todo
        mb, mandibula = self._boca(tela, L, k, mat, abre,
                                   [(0.0, 0.025 * k), (0.05 * k + F, 0.03 * k), (0.045 * k + F * 0.9, 0.05 * k), (0.0, 0.06 * k)],
                                   L(0.0, 0.03 * k), ((0.02 * k, 0.022 * k), (0.06 * k + F, 0.018 * k)))
        cranio = tela.elipse_girada(L(0.02 * k, -0.01 * k), 0.075 * k * S, 0.065 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.04 * k, -0.05 * k), (0.06 * k + F * 0.7, -0.035 * k), (0.072 * k + F, -0.012 * k),
                                   (0.068 * k + F, 0.02 * k), (0.03 * k, 0.035 * k)]))
        m = tela.pintar(cranio | focinho, mat)
        tela.pintar(tela.poly(L.pts([(0.03 * k, -0.068 * k), (0.105 * k, -0.052 * k), (0.11 * k, -0.036 * k),
                                     (0.045 * k, -0.045 * k)])), mat.claro(1))                    # arcada pesada
        tela.traco(L(0.05 * k, -0.04 * k), L(0.108 * k, -0.034 * k), mat[0])
        self._orbita(tela, L(0.08 * k, -0.026 * k), k, S)
        tela.traco(L(0.062 * k, -0.018 * k), L(0.05 * k + F * 0.8, -0.004 * k), mat[1])           # rugas do focinho
        tela.traco(L(0.06 * k, -0.008 * k), L(0.045 * k + F * 0.7, 0.006 * k), mat[1])
        nariz = L(0.07 * k + F, -0.012 * k)
        tela.px(nariz[0], nariz[1], BOCA_PEDRA)
        presa = L(0.045 * k + F * 0.8, 0.024 * k)                                                  # presa do canto
        for i in range(3):
            tela.px(presa[0], presa[1] + i, DENTE_PEDRA)
        if abre > 0.3:                                                                              # língua de fora
            ponta = lerp(L(0.05 * k + F, 0.03 * k), mandibula[1], 0.5) + v2(0, 1)
            tela.chapado(tela.elipse(ponta[0], ponta[1], max(1.0, 0.018 * k * S), max(1.0, 0.01 * k * S)), (104, 86, 86))
        return m | mb

    # ----- bica d'água (gárgula de calha) -----
    def _bica(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        tela.pintar(tela.poly(L.pts([(-0.02 * k, -0.035 * k), (-0.09 * k, -0.075 * k), (-0.04 * k, -0.01 * k)])),
                    mat.escuro(1))                                                                  # orelha deitada
        abre = 0.5 + boca * 0.35                                                                    # boca de cano
        mb, mandibula = self._boca(tela, L, k, mat, abre,
                                   [(0.0, 0.02 * k), (0.06 * k + F, 0.024 * k), (0.055 * k + F * 0.95, 0.04 * k), (0.0, 0.05 * k)],
                                   L(0.0, 0.025 * k), ((0.02 * k, 0.016 * k), (0.07 * k + F, 0.012 * k)))
        cranio = tela.elipse_girada(L(0.02 * k, -0.005 * k), 0.08 * k * S, 0.05 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.03 * k, -0.04 * k), (0.07 * k + F * 0.8, -0.028 * k), (0.078 * k + F, -0.008 * k),
                                   (0.072 * k + F, 0.014 * k), (0.02 * k, 0.03 * k)]))
        m = tela.pintar(cranio | focinho, mat)
        tela.traco(L(-0.05 * k, -0.046 * k), L(0.06 * k + F * 0.8, -0.03 * k), (34, 32, 38))       # a calha
        tela.traco(L(-0.04 * k, -0.04 * k), L(0.05 * k + F * 0.8, -0.025 * k), mat[4])
        self._orbita(tela, L(0.055 * k, -0.026 * k), k, S, rx=0.013, ry=0.009)
        tela.pintar(tela.poly(L.pts([(0.035 * k, -0.045 * k), (0.085 * k, -0.04 * k), (0.06 * k, -0.033 * k)])), mat.claro(1))
        self.bica = lerp(L(0.07 * k + F, 0.012 * k), mandibula[1], 0.45)
        return m | mb

    # ----- leão de juba esculpida (quimera) -----
    def _leao(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        c = L(-0.005 * k, -0.005 * k)
        juba = tela.pintar(tela.elipse_girada(c, 0.095 * k * S, 0.09 * k * S, L.ang), mat.escuro(1))
        for j in range(11):                                                                         # cachos da juba
            a = L.ang + math.pi * 0.4 + j * (math.pi * 1.25 / 10)
            p = c + direcao(a) * (0.08 * k * S)
            juba |= tela.pintar(tela.circulo(p, 0.03 * k * S), mat if j % 2 else mat.claro(1))
            tela.px(p[0], p[1], mat[1])
        abre = boca * 0.7
        mb, mandibula = self._boca(tela, L, k, mat, abre,
                                   [(0.03 * k, 0.025 * k), (0.055 * k + F, 0.03 * k), (0.05 * k + F * 0.9, 0.045 * k), (0.025 * k, 0.05 * k)],
                                   L(0.03 * k, 0.03 * k), ((0.05 * k, 0.025 * k), (0.068 * k + F, 0.02 * k)))
        cranio = tela.elipse_girada(L(0.03 * k, -0.01 * k), 0.07 * k * S, 0.062 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.06 * k, -0.045 * k), (0.075 * k + F, -0.022 * k), (0.08 * k + F, 0.005 * k),
                                   (0.07 * k + F, 0.026 * k), (0.04 * k, 0.04 * k)]))
        m = tela.pintar(cranio | focinho, mat)
        nariz = L(0.078 * k + F, -0.014 * k)
        tela.chapado(tela.poly([nariz + v2(-2, -1), nariz + v2(1, -1), nariz + v2(0, 1)]), mat[1])
        tela.traco(L(0.06 * k, -0.052 * k), L(0.105 * k, -0.04 * k), mat[0])                       # cenho
        self._orbita(tela, L(0.08 * k, -0.03 * k), k, S, rx=0.018)
        for x in (0.06 * k + F * 0.75,):                                                            # caninos
            p = L(x, 0.027 * k)
            for i in range(3):
                tela.px(p[0], p[1] + i, DENTE_PEDRA)
        return m | mb | juba

    # ----- bode (a segunda cabeça da quimera) -----
    def _bode(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        tela.pintar(tela.poly(L.pts([(-0.01 * k, -0.02 * k), (-0.07 * k, 0.01 * k), (-0.04 * k, 0.03 * k)])),
                    mat.escuro(1))                                                                  # orelha caída
        cranio = tela.elipse_girada(L(0.0, -0.005 * k), 0.05 * k * S, 0.045 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.02 * k, -0.035 * k), (0.06 * k + F * 0.9, -0.016 * k), (0.066 * k + F, 0.004 * k),
                                   (0.056 * k + F, 0.02 * k), (0.01 * k, 0.03 * k)]))
        m = tela.pintar(cranio | focinho, mat)
        barba = tela.poly(L.pts([(0.03 * k + F * 0.5, 0.02 * k), (0.052 * k + F * 0.6, 0.022 * k), (0.035 * k + F * 0.45, 0.085 * k)]))
        m |= tela.pintar(barba, mat.escuro(1))
        boca_a, boca_b = L(0.04 * k + F * 0.6, 0.016 * k), L(0.064 * k + F, 0.01 * k + boca * 0.012 * k)
        tela.traco(boca_a, boca_b, BOCA_PEDRA)
        tela.px(*L(0.064 * k + F, -0.006 * k), BOCA_PEDRA)
        self._orbita(tela, L(0.035 * k, -0.02 * k), k, S, rx=0.014, ry=0.008)                       # pupila de bode
        return m


# ============================================================
# BASE: PEDRA -> VIVA
# ============================================================

class Gargula(Quadrupede):
    """Base das gárgulas (método-modelo). desenhar(): corpo -> desgaste da pedra -> estátua (se ainda não
    acordou) -> luz da vida (fendas, olhos, runa) -> efeitos -> desmoronar (na morte).

    O quanto ela está viva sai de VIDA: 0 no 1º quadro do "despertar" (estátua) até 1 no último;
    na "morte" vai de volta a 0 e QUEDA diz quanto da pedra já desmoronou."""

    animacoes_extras = (("despertar", 4),)
    VIDA = {"despertar": (0.0, 0.35, 0.7, 1.0), "morte": (0.75, 0.4, 0.1, 0.0)}
    QUEDA = (0.0, 0.0, 0.18, 1.0)
    S = 60
    proporcao = (2.2, 1.9)
    pe = 0.5
    cobertura = "liso"
    sangue = None
    mat = GRANITO
    veios = 3                                   # quantas fendas acendem quando está viva
    runa = True                                 # sol negro esculpido no peito
    cor_olhos = (255, 150, 60)
    liquen = (124, 132, 104)
    musgo = (72, 84, 62)
    umida = False
    pose_estatua = dict(agacha=0.04, cab=0.14, boca=0.0, abertura=0.06, bater=-0.3, cauda=0.0, bob=0.0, rabo=0.0)
    espreguicar = dict(abertura=0.62, bater=-0.05, cab=-0.18, boca=0.9)     # 3º quadro do despertar: o rugido
    semente = 90

    def vida(self, ctx):
        return tabela(ctx, self.VIDA[ctx.anim]) if ctx.anim in self.VIDA else 1.0

    def movimento_vivo(self, ctx):
        """Movimento acordada (as ramificações ajustam o parado e o bote)."""
        return super().movimento(ctx)

    def movimento(self, ctx):
        if ctx.anim not in self.VIDA:
            return self.movimento_vivo(ctx)
        viva = self.movimento_vivo(Ctx("parado", 0, 4))
        m = misturar_movimentos(dict(viva, **self.pose_estatua), viva, self.vida(ctx))
        if ctx.anim == "despertar" and ctx.i == 2:
            m.update(self.espreguicar)
        if ctx.anim == "morte":
            m["agacha"] += tabela(ctx, [0.02, 0.04, 0.05, 0.05])           # cede sobre as patas
        m.update(fase=ctx.a, i=ctx.i, anim=ctx.anim, golpe=False, ferido=False, morto=ctx.morto)
        return m

    def olhos(self, P):
        return self.cabeca.olhos

    # ---------------- desenho ----------------
    def desenhar(self, tela, ctx, P):
        self.atras(tela, ctx, P)
        corpo = self.corpo(tela, ctx, P)
        self.detalhes(tela, ctx, P, corpo)
        self.frente(tela, ctx, P)
        self.desgastar(tela, ctx, P)
        vida = self.vida(ctx)
        petrificar(tela, 1 - vida)
        self.acender(tela, ctx, P, vida)
        self.efeitos(tela, ctx, P)
        self.desmoronar_na_morte(tela, ctx, P)

    def desgastar(self, tela, ctx, P):
        S = self.S
        pedra = tela.mascara() & ~tela.emite
        esculpir(tela, pedra, self.ancora, self.semente, self.liquen, self.musgo, self.umida)
        quebrada = P["ferido"] or P["anim"] == "morte"
        T.rachaduras(tela, pedra, P["centro"], area=(0.2 * S, 0.16 * S), n=7 if quebrada else 3, passos=4,
                     cor=(46, 44, 50), emite=False, semente=self.semente + 5)

    def acender(self, tela, ctx, P, vida):
        """A vida da gárgula é luz: fendas de brasa do Eclipse, olhos acesos e a runa do peito."""
        S = self.S
        if vida > 0.05:
            pedra = tela.mascara() & ~tela.emite
            cor = misturar((80, 30, 22), LUZ_VEIOS, vida)
            T.rachaduras(tela, pedra, P["centro"], area=(0.22 * S, 0.14 * S), n=1 + int(round((self.veios - 1) * vida)),
                         passos=5, cor=cor, emite=vida > 0.3, brilho=0.15 * vida, semente=self.semente + 7,
                         borda_cor=misturar(cor, (40, 36, 44), 0.75))
            T.luz_de_borda(tela, pedra, LUZ_VEIOS, (1, 0), forca=0.18 * vida)
        if vida > 0.25:
            cor = misturar((90, 30, 20), self.cor_olhos, vida)
            for olho in self.olhos(P):
                tela.px(olho[0] + 0.5, olho[1], cor, emite=True)
                tela.px(olho[0] - 0.5, olho[1], misturar(cor, (60, 10, 0), 0.4), emite=True)
                tela.brilho(olho, 3 + 3 * vida, self.cor_olhos, 0.7 * vida)
        if self.runa and vida > 0.5:
            peito = lerp(P["A"], P["C"], 0.85) - P["cima"] * (0.05 * S)
            fx.runa(tela, peito, LUZ_VEIOS, 2, forma=1)
            tela.brilho(peito, 0.1 * S, LUZ_VEIOS, 0.35 * vida)

    def efeitos(self, tela, ctx, P):
        S, chao = self.S, self.ancora[1]
        if (ctx.anim == "despertar" and ctx.i in (1, 2)) or ctx.anim == "dano":
            lascas(tela, P["centro"], (0.25 * S, 0.12 * S), self.mat[3], 8, (ctx.i + 1) * 0.12 * S, self.semente + ctx.i)
        if ctx.anim == "despertar" and ctx.i in (1, 2):
            fx.fumaca(tela, v2(P["centro"][0], chao - 0.06 * S), 0.07 * S, cor=POEIRA, fase=ctx.a, n=4, sobe=6)
        if P["golpe"]:
            T.particulas(tela, v2(P["centro"][0], chao - 4), (0.3 * S, 0.05 * S), POEIRA, n=8, fase=P["fase"],
                         sobe=0.12 * S, emite=False, semente=6)

    def desmoronar_na_morte(self, tela, ctx, P):
        if ctx.anim != "morte":
            return
        queda = tabela(ctx, self.QUEDA)
        if queda > 0:
            desmoronar(tela, self.ancora[1], queda, self.semente)
            fx.fumaca(tela, v2(P["centro"][0], self.ancora[1] - 0.12 * self.S), 0.1 * self.S, cor=POEIRA, fase=ctx.a,
                      n=6, sobe=10)


# ============================================================
# AS TRÊS RAMIFICAÇÕES
# ============================================================

class GargulaSentinela(Gargula):
    """A clássica, de vigia na cornija: sentada nas patas de trás, asas fechadas como capa, chifres
    de carneiro, careta de demônio com a língua de fora e cauda de espinhos enrolada nos pés."""
    nome = "gargula_viva"                       # a forma principal (a do bestiário)
    mat = GRANITO
    mat_asa = GRANITO.escuro(1)
    comprimento = 0.28
    altura_anca = 0.17
    altura_cernelha = 0.5
    arco = -0.05
    perfil = ((0.0, 0.13, 0.12), (0.5, 0.11, 0.1), (1.0, 0.13, 0.14))
    pescoco = (0.07, -0.08)
    pescoco_larg = (0.09, 0.08)
    cabeca_ang = 0.3
    cabeca = CabecaDePedra("careta", tam=0.19, focinho=0.06, mat_chifre=GRANITO.claro(1),
                           chifres=[(-0.02, -0.045, 0.17, -2.3, 2.4, 0.028), (0.03, -0.055, 0.07, -1.9, 0.3, 0.013)])
    pata_tras = Pata(comp=(0.15, 0.14, 0.09), grossura=(0.08, 0.06, 0.05, 0.045), joelho="frente", metatarso=0.9,
                     cobertura=None, garra=GARRA_PEDRA)
    pata_frente = Pata(comp=(0.19, 0.19, 0.05), grossura=(0.06, 0.05, 0.045, 0.04), joelho="tras", metatarso=0.0,
                       estilo="mao", cobertura=None, garra=GARRA_PEDRA)
    pe_tras_x = 0.16
    pe_frente_x = 0.02
    cauda = Cauda(comp=0.42, grossura=(0.05, 0.04, 0.03, 0.012), segmentos=7, ang=math.pi * 0.62, curva=-1.6,
                  estilo="espinhos")
    asa = Asa(envergadura=0.62, estilo="membrana", garra=GARRA_PEDRA, osso=GRANITO.claro(1), detalhada=True)
    semente = 91

    def movimento_vivo(self, ctx):
        m = super().movimento_vivo(ctx)
        m.update(abertura=0.14 + 0.04 * math.sin(ctx.a), bater=-0.35)
        if ctx.anim == "ataque":                    # salta da cornija: asas abertas e garras na frente
            m.update(abertura=tabela(ctx, [0.5, 1.0, 0.8, 0.3]), bater=tabela(ctx, [-0.5, 0.15, 0.3, -0.2]),
                     salto=tabela(ctx, [0.0, 0.22, 0.06, 0.0]), avanco=tabela(ctx, [-0.05, 0.38, 0.42, 0.1]),
                     boca=tabela(ctx, [0.3, 1.0, 0.6, 0.1]))
        return m


class GargulaCalha(Gargula):
    """A gárgula de calha (a função original das gárgulas): corpo comprido e baixo agarrado à beirada,
    pescoço esticado para a frente, a calha correndo pelo dorso e a boca de bica que verte água sem parar."""
    nome = "gargula_calha"
    proporcao = (2.5, 1.7)
    pe = 0.42
    mat = PEDRA_MOLHADA
    mat_asa = PEDRA_MOLHADA.escuro(1)
    umida = True
    runa = False
    liquen = (112, 132, 108)
    musgo = (64, 88, 64)
    cor_olhos = (255, 170, 80)
    comprimento = 0.62
    altura_anca = 0.27
    altura_cernelha = 0.27
    arco = -0.05
    perfil = ((0.0, 0.1, 0.09), (0.5, 0.09, 0.085), (1.0, 0.11, 0.12))
    pescoco = (0.22, -0.01)
    pescoco_larg = (0.08, 0.065)
    cabeca_ang = 0.18
    cabeca = CabecaDePedra("bica", tam=0.16, focinho=0.12, mat_chifre=PEDRA_MOLHADA.claro(1),
                           chifres=[(-0.03, -0.03, 0.09, -2.8, 0.3, 0.016)])
    pata_tras = Pata(comp=(0.13, 0.12, 0.07), grossura=(0.065, 0.05, 0.04, 0.036), joelho="frente", metatarso=0.6,
                     cobertura=None, garra=GARRA_PEDRA)
    pata_frente = Pata(comp=(0.13, 0.12, 0.04), grossura=(0.05, 0.04, 0.035, 0.032), joelho="tras", metatarso=0.1,
                       estilo="mao", cobertura=None, garra=GARRA_PEDRA)
    pe_tras_x = 0.0
    pe_frente_x = 0.06
    cauda = Cauda(comp=0.4, grossura=(0.06, 0.045, 0.03, 0.014), segmentos=7, ang=math.pi - 0.15, curva=0.5,
                  estilo="espinhos")
    asa = Asa(envergadura=0.45, estilo="membrana", rasgos=1, garra=GARRA_PEDRA, osso=PEDRA_MOLHADA.claro(1), detalhada=True)
    pose_estatua = dict(Gargula.pose_estatua, cab=0.08)
    espreguicar = dict(abertura=0.55, bater=-0.1, cab=-0.12, boca=0.9)
    semente = 93

    def movimento_vivo(self, ctx):
        m = super().movimento_vivo(ctx)
        m.update(abertura=0.12 + 0.03 * math.sin(ctx.a), bater=-0.2)
        if ctx.anim == "ataque":                    # estica o pescoço e cospe o jorro
            m.update(avanco=tabela(ctx, [-0.06, 0.12, 0.14, 0.04]), cab=tabela(ctx, [0.2, -0.1, -0.05, 0.05]),
                     boca=tabela(ctx, [0.2, 1.0, 1.0, 0.2]), abertura=tabela(ctx, [0.2, 0.45, 0.4, 0.2]))
        return m

    def corpo(self, tela, ctx, P):
        m = super().corpo(tela, ctx, P)
        topo = [p + P["cima"] * (self._perfil(t)[0] * self.S * 0.8)
                for t, p in zip(np.linspace(0, 1, len(P["espinha"])), P["espinha"])]
        tela.tracos(topo, (34, 32, 38))                                    # a calha correndo pelo dorso
        tela.tracos([p + v2(0, 1) for p in topo], self.mat[4])
        return m

    def efeitos(self, tela, ctx, P):
        super().efeitos(tela, ctx, P)
        boca = self.cabeca.bica
        if boca is not None:
            self.jorro(tela, boca, ctx, forte=P["golpe"])

    def jorro(self, tela, boca, ctx, forte=False):
        """Água vertendo da bica em arco até o chão (no bote vira um jato para a frente)."""
        S, chao = self.S, self.ancora[1]
        alcance, grossura = ((0.95 * S, 0.035 * S) if forte else (0.16 * S, 0.016 * S))
        queda = max(4.0, chao - boca[1])
        pts = [boca + v2(alcance * t, queda * t * t) for t in np.linspace(0, 1, 9)]
        fio = tela.corrente(pts, [grossura * (1 + 0.6 * t) for t in np.linspace(0, 1, 9)]) & (tela.alfa == 0)
        tela.vidro(fio, AGUA, 0.75)
        fase = ctx.a / (2 * math.pi)
        for t in np.linspace(0, 1, 9)[1:]:                                 # reflexos descendo pelo fio
            if (t * 3 - fase) % 1 < 0.35:
                p = boca + v2(alcance * t, queda * t * t)
                tela.px(p[0], p[1], AGUA[3])
        fim = pts[-1]
        for k in range(5):                                                 # respingo no chão
            a = math.pi + (k + 0.5) * math.pi / 5
            p = fim + direcao(a) * (2 + (k + ctx.i) % 3) * (1.6 if forte else 1.0)
            tela.px(p[0], p[1] - 1, AGUA[2])


class GargulaQuimera(Gargula):
    """A quimera: corpo e cabeça de leão (juba esculpida em cachos), a cabeça de bode com chifres
    saindo das costas e o que é de ave (asas de penas de pedra e garras de águia nas patas da frente)."""
    nome = "gargula_quimera"
    S = 64
    proporcao = (2.4, 1.9)
    pe = 0.48
    mat = ARENITO
    mat_asa = ARENITO.claro(1)
    liquen = (150, 146, 100)
    musgo = (88, 98, 60)
    cor_olhos = (255, 196, 90)
    comprimento = 0.46
    altura_anca = 0.34
    altura_cernelha = 0.4
    arco = -0.04
    perfil = ((0.0, 0.12, 0.11), (0.5, 0.1, 0.11), (1.0, 0.14, 0.17))
    pescoco = (0.1, -0.1)
    pescoco_larg = (0.11, 0.09)
    cabeca_ang = 0.12
    cabeca = CabecaDePedra("leao", tam=0.17, focinho=0.05)
    bode = CabecaDePedra("bode", tam=0.14, focinho=0.06, mat_chifre=ARENITO.claro(1),
                         chifres=[(-0.01, -0.035, 0.22, -2.5, 1.7, 0.026)])
    pata_tras = Pata(comp=(0.17, 0.15, 0.1), grossura=(0.08, 0.06, 0.045, 0.04), joelho="frente", metatarso=0.45,
                     cobertura=None, garra=GARRA_PEDRA)
    pata_frente = Pata(comp=(0.18, 0.17, 0.05), grossura=(0.06, 0.045, 0.035, 0.03), joelho="tras", metatarso=0.05,
                       estilo="ave", cobertura=None, garra=GARRA_PEDRA)
    pe_tras_x = -0.02
    pe_frente_x = 0.07
    cauda = Cauda(comp=0.5, grossura=(0.035, 0.03, 0.022, 0.016), segmentos=8, ang=math.pi - 0.9, curva=1.6, estilo="lisa")
    asa = Asa(envergadura=0.7, estilo="penas")
    espreguicar = dict(abertura=0.7, bater=-0.1, cab=-0.15, boca=0.9)
    semente = 95

    def movimento_vivo(self, ctx):
        m = super().movimento_vivo(ctx)
        m.update(abertura=0.2 + 0.04 * math.sin(ctx.a), bater=-0.15)
        if ctx.anim == "ataque":                    # bote de leão com as asas abertas
            m.update(abertura=tabela(ctx, [0.6, 1.0, 0.9, 0.4]), bater=tabela(ctx, [-0.3, 0.1, 0.2, -0.1]),
                     salto=tabela(ctx, [0.0, 0.12, 0.03, 0.0]))
        return m

    def olhos(self, P):
        return self.cabeca.olhos + self.bode.olhos

    def detalhes(self, tela, ctx, P, corpo):
        ponta = P["cauda"][-1]                                             # tufo esculpido na ponta da cauda
        tela.pintar(tela.elipse(ponta[0], ponta[1], 0.035 * self.S, 0.025 * self.S), self.mat.escuro(1))

    def frente(self, tela, ctx, P):
        """Patas e asa de cá e, por cima, a cabeça de bode saindo das costas."""
        super().frente(tela, ctx, P)
        S = self.S
        dorso = lerp(P["A"], P["C"], 0.4) + P["cima"] * (self._perfil(0.4)[0] * S * 0.7)
        nuca = dorso + direcao(-1.35 + P["incl"]) * (0.2 * S)
        tela.pintar(tela.capsula(dorso, nuca, 0.055 * S, 0.042 * S), self.mat)
        self.bode.desenhar(tela, nuca, -0.35 + P["incl"] + P["cab"] * 0.5, S, self.mat, boca=P["boca"] * 0.6,
                           morto=P["morto"], fase=P["fase"], semente=self.semente + 9)
