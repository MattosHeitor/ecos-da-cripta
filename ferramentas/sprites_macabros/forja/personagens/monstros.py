"""Humanoides distorcidos feitos com a forja de monstros (forja/criaturas/monstro.py).

    Afogado               pele inchada pálida-esverdeada, algas, água escorrendo e correntes
    BruxaDoLodo           bruxa coberta de lodo, cabelo de algas, olhos acesos e cajado com bola de lodo
    BarqueiroSemRosto     chefe: capuz vazio, manto em farrapos, remo e barco com a lanterna dos afogados
    MineradorAmaldicoado  capacete com lamparina, picareta, corpo rachado com brasas e minério
    KoboldDinamiteiro     lagartinho de óculos e bandoleira de dinamite; explode ao morrer
    DraconianoRenegado    guerreiro dracônico de escamas rubras, chifres, asas rasgadas e lança
    SentinelaDeGelo       guardião de gelo translúcido com ombreiras de cristal e alabarda
    ArautoDaNevasca       espectro de manto gelado, coroa de cristal e trompa; sopra a nevasca
    MercadorMascarado     chefe secreto: alto e curvado, veludo gasto, máscara de porcelana rachada com o vazio atrás
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, lerp, dir_ang
from ..humanoide import cabeca_base, quadro_cabeca, quadro_tronco
from .. import texturas as T
from .. import fx, armas
from ..criaturas.monstro import ForjaMonstro
from ..criaturas.partes import Cabeca, Cauda, Asa, direcao

AGUA = ((40, 66, 76), (70, 106, 118))
LODO = ((58, 70, 32), (88, 104, 46))
MADEIRA_PODRE = Mat((84, 62, 46), 6, relevo=1.0, ruido=0.25)
FERRUGEM = metal((112, 84, 70), ruido=0.35)


# ============================================================
# PÂNTANO DOS AFOGADOS
# ============================================================

class Afogado(ForjaMonstro):
    """Cadáver inchado que saiu do pântano: braços estendidos, algas, correntes e água pingando."""
    nome = "afogado"
    H = 72
    semente = 51
    curvado = 0.22
    magreza = 1.25
    barriga = 0.035
    braco_longo = 1.1
    cabeca_tam = 1.12
    pele = Mat((150, 172, 150), 6, relevo=1.0, ruido=0.15, satur=0.55)
    roupa = Mat((62, 58, 50), 5, desce=0.3, ruido=0.3, relevo=0.7)
    trapos = 6
    rosto = "afogado"
    correntes = 2
    escorre = (96, 140, 150)
    sangue = AGUA
    base = dict(braco_f=(1.15, 0.3), braco_b=(0.95, 0.35))

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        T.manchas(tela, corpo, J["pelvis"], (66, 96, 58), escala=3, quantidade=0.2, forca=0.7, semente=2)   # algas
        T.brilho_umido(tela, tela.mascara(), J["pelvis"], densidade=0.05)
        rng = random.Random(self.semente)
        for lado in ("f", "b"):                                         # algas penduradas nos braços
            c = lerp(J["cotovelo_" + lado], J["mao_" + lado], 0.3)
            for k in range(2):
                comp = self.H * rng.uniform(0.06, 0.12)
                tela.tracos([c + v2(k * 2, 0), c + v2(k * 2 - 1 + math.sin(ctx.a + k), comp)], (54, 84, 50))
        if ctx.anim != "morte":
            self.poca(tela, v2(self.ancora[0], self.ancora[1] + 1), self.H * 0.26, *AGUA)


class BruxaDoLodo(ForjaMonstro):
    """Bruxa corcunda coberta de lodo: chapéu podre, cabelo de algas, olhos acesos e bola de lodo."""
    nome = "bruxa_do_lodo"
    H = 74
    estilo = "magia"
    semente = 53
    curvado = 0.3
    corcunda = 0.06
    magreza = 0.85
    braco_longo = 1.1
    pele = Mat((120, 140, 100), 6, relevo=1.0, ruido=0.2, satur=0.5)
    roupa = Mat((58, 66, 40), 5, desce=0.3, ruido=0.3, relevo=0.7)
    manto_inteiro = True
    manga = Mat((58, 66, 40), 5, ruido=0.3, relevo=0.7)
    trapos = 4
    rosto = "bruxa"
    olho_cor = (220, 255, 90)
    escorre = LODO[1]
    sangue = LODO
    cajado = Mat((70, 52, 40), 5, ruido=0.3)

    def rosto_bruxa(self, tela, ctx, J):
        """Rosto de bruxa: nariz adunco com verrugas, olho aceso, sorriso torto, cabelo de algas e chapéu."""
        H = self.H
        m, C = cabeca_base(tela, J, self.pele, larg=0.5, nariz=False)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.pintar(tela.poly(C.pts([(w * 0.42, h * 0.1), (w * 1.0, -h * 0.2), (w * 0.85, -h * 0.25), (w * 0.45, -h * 0.12)])),
                    self.pele.claro(1))
        tela.px(*C.pt(w * 0.8, -h * 0.12), self.pele[1])
        tela.chapado(tela.elipse_girada(C.pt(w * 0.3, h * 0.08), max(1.2, w * 0.13), max(1.0, h * 0.09), 0), (14, 10, 6))
        self._olho(tela, C.pt(w * 0.32, h * 0.08), ctx)
        tela.traco(C.pt(w * 0.05, -h * 0.3), C.pt(w * 0.45, -h * 0.34), (30, 14, 10))
        tela.px(*C.pt(w * 0.2, -h * 0.36), (210, 200, 150))
        rng = random.Random(self.semente)
        for k in range(7):                                              # cabelo de algas
            topo = C.pt(w * (-0.5 + k * 0.1), h * 0.4)
            comp = H * rng.uniform(0.16, 0.3)
            balanco = math.sin(ctx.a + k * 0.7) * 1.2
            pts = [topo, topo + v2(-2 + balanco, comp * 0.5), topo + v2(-3 + balanco * 1.6, comp)]
            tela.pintar(tela.corrente(pts, [1.1, 0.9, 0.6]), Mat((48, 76, 42) if k % 2 else (66, 98, 52), 4, relevo=0.6))
        aba = C.pt(0, h * 0.4)                                          # chapéu pontudo e podre
        hu = J["hu"]
        frente = v2(-hu[1], hu[0])
        ponta = aba + hu * (h * 1.6) - frente * (h * 0.9)
        chapeu = tela.poly([aba - frente * (h * 1.0), aba + frente * (h * 1.05), aba + frente * (h * 0.4) + hu * (h * 0.25),
                            lerp(aba, ponta, 0.6) + frente * (h * 0.2), ponta, aba - frente * (h * 0.35) + hu * (h * 0.3)])
        mc = tela.pintar(chapeu, self.roupa.escuro(1))
        T.escorrer(tela, mc, aba, LODO[1], densidade=0.35, comp=3, fase=ctx.a, molhado=0.4, semente=3)

    def arma(self, tela, ctx, J):
        H = self.H
        topo = armas.cajado(tela, J["mao_f"], J["arma_f"], H * 0.5, self.cajado, torto=2.0)
        self.bola(tela, topo, H * 0.05, ctx)
        if ctx.anim == "ataque" and ctx.i in (1, 2):                   # bola de lodo voando
            frente = self.frente_do_corpo(J)
            alvo = J["mao_b"] + frente * (H * (0.15 if ctx.i == 1 else 0.5)) + v2(0, -H * 0.03 * ctx.i)
            self.bola(tela, alvo, H * 0.07, ctx)
            for k in range(1, 4):
                rastro = alvo - frente * (k * H * 0.05)
                tela.px(rastro[0], rastro[1] + k, LODO[1])

    def bola(self, tela, c, r, ctx):
        m = tela.pintar(tela.circulo(c, r), Mat(LODO[1], 5, relevo=1.3, especular=(200, 230, 140)))
        tela.brilho(c, r * 2.5, (150, 220, 80), 0.3)
        T.escorrer(tela, m, c, LODO[0], densidade=0.6, comp=3, fase=ctx.a, molhado=0.3, semente=5)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        T.manchas(tela, corpo, J["pelvis"], LODO[1], escala=4, quantidade=0.3, forca=0.75, semente=4)
        if ctx.anim != "morte":
            self.poca(tela, v2(self.ancora[0], self.ancora[1] + 1), self.H * 0.28, *LODO)


class BarqueiroSemRosto(ForjaMonstro):
    """Chefe do Pântano: figura alta de capuz vazio, de pé num barco, com remo e lanterna verde."""
    nome = "barqueiro_sem_rosto"
    H = 96
    larg, alt = 211, 202
    ancora = (94, 199)
    estilo = "pesado"
    semente = 55
    curvado = 0.12
    magreza = 1.25
    braco_longo = 1.2
    cabeca_tam = 1.2
    corcunda = 0.04
    pele = Mat((176, 168, 156), 6, relevo=1.1)
    roupa = Mat((44, 38, 58), 6, desce=0.35, ruido=0.2, relevo=0.6)
    manto_inteiro = True
    folga_manto = 0.13
    manga = Mat((44, 38, 58), 6, ruido=0.2, relevo=0.7)
    trapos = 8
    rosto = "vazio"
    olho_cor = None
    garras = False
    sangue = None
    base = dict(braco_f=(0.55, 0.9), braco_b=(0.85, 0.75), arma_f=2.65, pe_f=(-0.05, 0), pe_b=(0.06, 0))
    conves = 0.17                                                       # altura do conves (fração de H)

    def balanco(self, ctx):
        """Sobe e desce do barco na água (e afunda na morte)."""
        if ctx.anim == "morte":
            return [0.0, 0.04, 0.1, 0.16][ctx.i]
        return 0.012 * math.sin(ctx.a)

    def pose(self, ctx):
        p = super().pose(ctx)
        q = p.get("quadril", (0, 0))
        p["quadril"] = (q[0], q[1] - self.conves + self.balanco(ctx))
        return p

    def casco(self, tela, ctx, frente):
        """Barco de tábuas: costado de lá (atrás do barqueiro) ou de cá (na frente das pernas)."""
        H = self.H
        cx, chao = self.ancora
        b = self.balanco(ctx) * H
        y_borda = chao - H * 0.16 + b
        popa = v2(cx - H * 0.92, chao - H * 0.3 + b)
        proa = v2(cx + H * 0.98, chao - H * 0.36 + b)
        if not frente:
            borda = [popa + v2(4, 3), v2(cx - H * 0.4, y_borda - 2), v2(cx + H * 0.5, y_borda - 2), proa + v2(-4, 3)]
            tela.pintar(tela.corrente(borda, [2.2, 2.0, 2.0, 2.2]), MADEIRA_PODRE.escuro(2))
            for k in range(6):                                          # moedas do pedágio na popa
                m = popa + v2(H * 0.12 + k * 3, H * 0.1 - (k % 2) * 2)
                tela.chapado(tela.elipse(m[0], m[1], 1.6, 1.0), (196, 160, 70) if k % 2 else (150, 116, 50))
            return
        quilha = [popa, popa + v2(H * 0.08, H * 0.04), v2(cx - H * 0.62, chao - H * 0.02 + b), v2(cx + H * 0.55, chao - H * 0.02 + b),
                  proa + v2(-H * 0.12, H * 0.2), proa]
        borda = [proa, v2(cx + H * 0.5, y_borda), v2(cx - H * 0.4, y_borda), popa]
        m = tela.pintar(tela.poly(quilha + borda), MADEIRA_PODRE)
        T.casca(tela, m, popa, eixo=(1, 0.04), espaco=4, ondula=0.5, escurece=0.6, fendas=0.02)
        for k in range(6):                                              # cavernas (costelas do barco)
            x = cx - H * 0.55 + k * H * 0.22
            tela.traco(v2(x, y_borda + 2), v2(x + 2, chao - H * 0.04 + b), MADEIRA_PODRE[1], sobre=True)
        tela.pintar(tela.corrente(borda, [2.4, 2.2, 2.2, 2.4]), MADEIRA_PODRE.claro(1))
        T.musgo(tela, m, popa, cor=(52, 72, 44), alcance=2, quantidade=0.3)
        caveira = proa + v2(-2, 2)                                      # figura de proa: caveira
        tela.pintar(tela.circulo(caveira, H * 0.04), Mat((200, 190, 166), 5))
        for dx in (-1.5, 1.5):
            tela.px(caveira[0] + dx, caveira[1], (20, 12, 14))
        tela.traco(caveira + v2(-1.5, 2.5), caveira + v2(1.5, 2.5), (40, 30, 30))
        self.lanterna(tela, ctx, proa)

    def lanterna(self, tela, ctx, proa):
        H = self.H
        haste = [proa + v2(-H * 0.06, 0), proa + v2(-H * 0.04, -H * 0.4), proa + v2(H * 0.06, -H * 0.5)]
        tela.pintar(tela.corrente(haste, [1.4, 1.2, 1.0]), MADEIRA_PODRE.escuro(1))
        gancho = haste[-1]
        bal = math.sin(ctx.a) * 1.5
        luz = gancho + v2(bal, H * 0.08)
        tela.traco(gancho, luz + v2(0, -H * 0.03), (60, 56, 50))
        corpo = tela.poly([luz + v2(-H * 0.03, -H * 0.035), luz + v2(H * 0.03, -H * 0.035), luz + v2(H * 0.025, H * 0.04),
                           luz + v2(-H * 0.025, H * 0.04)])
        tela.pintar(corpo, FERRUGEM)
        acesa = not (ctx.anim == "morte" and ctx.i >= 2)
        if acesa:
            vidro = tela.elipse(luz[0], luz[1] + 1, H * 0.017, H * 0.028)
            tela.chapado(vidro, (180, 255, 150), emite=True)
            fx.chama(tela, luz + v2(0, H * 0.02), H * 0.04, H * 0.025, fx.FOGO_VERDE, fase=ctx.a, brilho=False)
            tela.brilho(luz, H * 0.3, (140, 230, 120), 0.5 + 0.08 * math.sin(ctx.a * 2))

    def agua(self, tela, ctx):
        H = self.H
        cx, chao = self.ancora
        fundo = tela.poly([v2(cx - H * 0.98, chao - H * 0.04), v2(cx + H * 1.1, chao - H * 0.04), v2(cx + H * 1.1, chao + 2),
                           v2(cx - H * 0.98, chao + 2)])
        tela.chapado(fundo, (22, 32, 42))
        for k in range(7):                                              # marolas que andam
            x = cx - H * 0.9 + ((k * 0.3 + ctx.i * 0.07) % 2.0) * H
            y = chao - H * 0.03 + (k % 3)
            tela.traco(v2(x, y), v2(x + H * 0.08, y), (70, 100, 120))
        T.particulas(tela, v2(cx, chao - H * 0.08), (H * 0.9, H * 0.03), (90, 110, 130), n=10, fase=ctx.a, sobe=H * 0.06,
                     emite=False, semente=4)
        if ctx.anim == "morte" and ctx.i >= 1:                         # bolhas do barco afundando
            T.particulas(tela, v2(cx, chao - H * 0.06), (H * 0.6, H * 0.03), (140, 180, 200), n=8, fase=ctx.a, sobe=H * 0.12,
                         emite=False, semente=9)

    def atras(self, tela, ctx, J):
        self.casco(tela, ctx, frente=False)
        super().atras(tela, ctx, J)

    def arma(self, tela, ctx, J):
        """Remo de duas mãos: cabo comprido e pá larga; no golpe levanta um jorro d'água."""
        H = self.H
        d = dir_ang(J["arma_f"])
        n = v2(-d[1], d[0])
        a, b = armas.haste(tela, J["mao_f"], J["arma_f"], H * 0.3, H * 0.62, MADEIRA_PODRE.claro(1), larg=1.6)
        pa = tela.poly([b - d * (H * 0.02) + n * (H * 0.035), b + d * (H * 0.2) + n * (H * 0.05), b + d * (H * 0.24),
                        b + d * (H * 0.2) - n * (H * 0.05), b - d * (H * 0.02) - n * (H * 0.035)])
        mp = tela.pintar(pa, MADEIRA_PODRE)
        T.casca(tela, mp, b, eixo=d, espaco=3, ondula=0.4, escurece=0.7)
        if ctx.anim == "ataque" and ctx.i == 2:
            jorro = b + d * (H * 0.2)
            T.particulas(tela, jorro, (H * 0.12, H * 0.05), (150, 190, 210), n=16, fase=ctx.a, sobe=H * 0.15, emite=False)
            armas.rastro(tela, J["ombro_f"], H * 0.74, H * 0.8, 0.4, 2.2, cor=(150, 190, 215))

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        rng = random.Random(self.semente)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        if not (ctx.anim == "morte" and ctx.i >= 2):                  # o vazio do capuz se mexe
            for k in range(4):
                p = C.pt(h * (0.15 + rng.random() * 0.3), h * (-0.25 + 0.5 * ((rng.random() + ctx.i / 4) % 1)))
                tela.px(p[0], p[1], (70, 40, 110), emite=True)
        self.casco(tela, ctx, frente=True)
        self.agua(tela, ctx)


# ============================================================
# MINAS DE BRASA
# ============================================================

class MineradorAmaldicoado(ForjaMonstro):
    """Minerador morto que não parou de cavar: capacete com lamparina, picareta, brasas e minério no corpo."""
    nome = "minerador_amaldicoado"
    H = 74
    estilo = "pesado"
    semente = 57
    curvado = 0.18
    magreza = 0.95
    pele = Mat((88, 72, 66), 6, relevo=1.0, ruido=0.25)
    calca = Mat((86, 70, 52), 5, ruido=0.3, relevo=0.8)
    bota = Mat((50, 40, 36), 5, ruido=0.2)
    brasas = (255, 140, 40)
    rosto = "monstro"
    olho_cor = (255, 170, 60)
    sangue = ((40, 30, 28), (90, 40, 20))
    base = dict(arma_f=1.9, braco_f=(0.5, 0.9), braco_b=(0.4, 1.0))

    def cabeca(self, tela, ctx, J):
        super().cabeca(tela, ctx, J)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.9
        capacete = tela.poly(C.pts([(-w * 0.6, h * 0.12), (-w * 0.45, h * 0.5), (0, h * 0.68), (w * 0.45, h * 0.52),
                                    (w * 0.62, h * 0.12)]))
        aba = tela.poly(C.pts([(-w * 0.75, h * 0.14), (w * 0.8, h * 0.14), (w * 0.8, h * 0.05), (-w * 0.75, h * 0.05)]))
        mc = tela.pintar(capacete | aba, FERRUGEM)
        T.manchas(tela, mc, J["cabeca"], (70, 50, 40), escala=2, quantidade=0.3, forca=0.6)
        lampada = C.pt(w * 0.5, h * 0.38)                              # lamparina na testa
        tela.pintar(tela.circulo(lampada, h * 0.18), metal((170, 136, 70), especular=(255, 236, 170)))
        acesa = not (ctx.anim == "morte" and ctx.i >= 1)
        tela.chapado(tela.circulo(lampada + v2(0.5, 0), h * 0.1), (255, 236, 150) if acesa else (60, 50, 40), emite=acesa)
        if acesa:
            tela.brilho(lampada, h * 2.2, (255, 210, 120), 0.6 + 0.08 * math.sin(ctx.a * 2))

    def arma(self, tela, ctx, J):
        """Picareta: cabo de madeira e cabeça de ferro curva com duas pontas."""
        H = self.H
        d = dir_ang(J["arma_f"])
        n = v2(-d[1], d[0])
        a, topo = armas.haste(tela, J["mao_f"], J["arma_f"], 3, H * 0.4, MADEIRA_PODRE, larg=1.2)
        c = topo - d * 1.5
        cabeca = [c + n * (H * 0.16) - d * (H * 0.05), c + n * (H * 0.05) + d * 2, c - n * (H * 0.05) + d * 2,
                  c - n * (H * 0.15) - d * (H * 0.03), c - n * (H * 0.05) - d * 1.5, c + n * (H * 0.05) - d * 1.5]
        tela.pintar(tela.poly(cabeca), FERRUGEM)
        tela.pintar(tela.capsula(c - d * 3, c + d * 3, 1.6), FERRUGEM.escuro(1))
        if ctx.anim == "ataque" and ctx.i == 2:
            armas.faiscas(tela, c + n * (H * 0.16), (255, 200, 90), n=8, raio=H * 0.12, semente=2)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        rng = random.Random(self.semente)
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        for k, cor in enumerate(((210, 50, 60), (230, 150, 50), (120, 200, 230))):   # minério brotando do corpo
            p = Q.pt(-H * (0.05 - k * 0.03), T_ * (0.6 + k * 0.12))
            ang = rng.uniform(-2.4, -0.8)
            ponta = p + direcao(ang) * (H * rng.uniform(0.05, 0.08))
            lado = direcao(ang + math.pi / 2) * (H * 0.018)
            mat = Mat(cor, 5, relevo=1.4, especular=(255, 255, 255))
            tela.pintar(tela.poly([p - lado, p + lado, ponta]), mat)
            tela.brilho(ponta, H * 0.05, cor, 0.3)
        if not ctx.morto:
            T.particulas(tela, J["peito"], (H * 0.2, H * 0.15), (255, 150, 60), n=5, fase=ctx.a, sobe=H * 0.25, semente=5)


class KoboldDinamiteiro(ForjaMonstro):
    """Kobold de óculos de mina e bandoleira de dinamite; joga bananas acesas e explode ao morrer."""
    nome = "kobold_dinamiteiro"
    H = 46
    estilo = "corte"
    semente = 61
    curvado = 0.3
    pernas_comp = 0.8
    magreza = 1.05
    pele = Mat((154, 86, 58), 6, relevo=1.05, ruido=0.12)
    rosto = "kobold"
    olho_cor = (255, 220, 80)
    sangue = ((70, 6, 14), (110, 14, 24))
    focinho = Cabeca(estilo="reptil", tam=0.15, focinho=0.12, olho_cor=(255, 220, 80),
                     chifres=[(-0.03, -0.035, 0.08, -2.7, 0.6, 0.016)])
    cauda = Cauda(comp=0.5, grossura=(0.06, 0.045, 0.03, 0.01), segmentos=6, ang=math.pi - 0.9, curva=0.7, estilo="escamas")
    DINAMITE = Mat((190, 50, 44), 5, relevo=1.1)

    def atras(self, tela, ctx, J):
        f = self.frente_do_corpo(J)
        base = J["pelvis"] - f * (self.H * 0.05)
        pts = self.cauda.pontos(base, self.H, balanco=0.6, fase=ctx.a, ang_extra=J["giro"])
        self.cauda.desenhar(tela, pts, self.pele.escuro(1), self.H)
        super().atras(tela, ctx, J)

    def rosto_kobold(self, tela, ctx, J):
        nuca, ang = self.eixo_da_cabeca(J)
        boca = 0.6 if ctx.golpe else 0.1
        self.focinho.desenhar(tela, nuca, ang, self.H, self.pele, boca=boca, morto=ctx.morto, fase=ctx.a)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        for x in (-0.05, 0.25):                                         # óculos de mina na testa
            c = C.pt(h * x, h * 0.55)
            tela.pintar(tela.circulo(c, h * 0.2), metal((160, 126, 64)))
            tela.chapado(tela.circulo(c, h * 0.11), (120, 200, 210))
            tela.px(c[0] - 0.5, c[1] - 0.5, (230, 250, 255))
        tela.traco(C.pt(-h * 0.5, h * 0.5), C.pt(h * 0.5, h * 0.55), (60, 40, 30), sobre=True)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        T.escamas(tela, m, J["pelvis"], tam=2)
        Q = quadro_tronco(J)
        H, T_ = self.H, J["P"]["tronco"]
        alca = [Q.pt(-H * 0.07, T_ * 0.95), Q.pt(H * 0.07, T_ * 0.1)]          # bandoleira
        tela.pintar(tela.capsula(*alca, H * 0.025), Mat((90, 62, 40), 5))
        for k in range(3):
            p = lerp(*alca, 0.25 + k * 0.25)
            tela.pintar(tela.capsula(p + v2(0, -H * 0.04), p + v2(0, H * 0.03), H * 0.022), self.DINAMITE)
        return m

    def arma(self, tela, ctx, J):
        H = self.H
        explodiu = ctx.anim == "morte"
        if explodiu:
            return
        if ctx.anim == "ataque" and ctx.i in (1, 2):                   # dinamite voando
            f = self.frente_do_corpo(J)
            p = J["mao_f"] + f * (H * (0.35 if ctx.i == 1 else 0.75)) + v2(0, -H * (0.25 if ctx.i == 1 else 0.15))
            ang = ctx.a * 2
        else:
            p, ang = J["mao_f"], J["arma_f"]
        d = dir_ang(ang)
        tela.pintar(tela.capsula(p - d * (H * 0.05), p + d * (H * 0.05), H * 0.028), self.DINAMITE)
        pavio = p + d * (H * 0.09)
        tela.traco(p + d * (H * 0.05), pavio, (70, 60, 50))
        tela.px(pavio[0], pavio[1], (255, 240, 160), emite=True)
        tela.brilho(pavio, 4, (255, 180, 60), 0.7)
        T.particulas(tela, pavio, (2, 2), (255, 200, 80), n=3, fase=ctx.a, sobe=4)

    def morte(self, tela, ctx, J):
        """Pavio Curto: a bandoleira explode."""
        H = self.H
        if ctx.anim != "morte":
            return
        c = J["peito"]
        if ctx.i == 0:
            armas.faiscas(tela, c, (255, 210, 90), n=6, raio=H * 0.15, semente=1)
        elif ctx.i == 1:
            fx.chama(tela, c + v2(0, H * 0.15), H * 0.55, H * 0.6, fx.FOGO, fase=ctx.a, linguas=4)
            armas.faiscas(tela, c, (255, 230, 140), n=14, raio=H * 0.45, semente=2)
        else:
            tela.tingir(tela.mascara() & ~tela.emite, (30, 22, 20), 0.6)
            fx.fumaca(tela, c + v2(0, -4), H * 0.12, cor=(70, 64, 66), fase=ctx.a, n=6, sobe=14)


class DraconianoRenegado(ForjaMonstro):
    """Draconiano renegado: escamas rubras com placas claras no ventre, chifres, asas rasgadas e lança."""
    nome = "draconiano_renegado"
    H = 82
    estilo = "estocada"
    semente = 63
    curvado = 0.06
    magreza = 1.1
    pele = Mat((166, 50, 44), 6, relevo=1.1, ruido=0.1)
    armadura = metal((80, 76, 84), ruido=0.3)
    bota = metal((74, 70, 78), ruido=0.3)
    larg = 196
    ancora = (84, 127)
    rosto = "draconico"
    olho_cor = (255, 200, 60)
    focinho = Cabeca(estilo="reptil", tam=0.13, focinho=0.12, olho_cor=(255, 200, 60), mat_chifre=Mat((210, 196, 168), 6),
                     chifres=[(-0.04, -0.035, 0.18, -2.75, 0.9, 0.022), (-0.01, -0.04, 0.12, -2.5, 0.6, 0.016)])
    cauda = Cauda(comp=0.55, grossura=(0.07, 0.055, 0.035, 0.012), segmentos=7, ang=math.pi - 1.0, curva=0.9, estilo="escamas")
    asa = Asa(envergadura=0.55, estilo="membrana", rasgos=3)
    LANCA = metal((150, 150, 160), especular=(255, 250, 240))

    def atras(self, tela, ctx, J):
        H = self.H
        raiz = lerp(J["ombro_b"], J["pescoco"], 0.3)
        abre = 0.75 if ctx.golpe else 0.35 + 0.1 * math.sin(ctx.a)
        self.asa.desenhar(tela, self.asa.pontos(raiz, H, abre, -0.2 + J["giro"]), self.pele.escuro(1), H, self.semente)
        f = self.frente_do_corpo(J)
        pts = self.cauda.pontos(J["pelvis"] - f * (H * 0.06), H, balanco=0.5, fase=ctx.a, ang_extra=J["giro"])
        self.cauda.desenhar(tela, pts, self.pele.escuro(1), H)
        super().atras(tela, ctx, J)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        T.escamas(tela, m, J["pelvis"], tam=3)
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        for k in range(5):                                              # placas do ventre
            y = T_ * (0.15 + k * 0.13)
            placa = tela.poly(Q.pts([(H * 0.02, y - 2), (H * 0.075, y - 2), (H * 0.075, y + 1.5), (H * 0.02, y + 1.5)])) & m
            tela.pintar(placa, Mat((222, 172, 118), 5, relevo=0.8))
        return m

    def rosto_draconico(self, tela, ctx, J):
        nuca, ang = self.eixo_da_cabeca(J)
        boca = 0.5 if ctx.golpe else 0.0
        self.focinho.desenhar(tela, nuca, ang, self.H, self.pele, boca=boca, morto=ctx.morto, fase=ctx.a)
        if not ctx.morto:                                               # fumaça e brasa nas narinas
            narina = nuca + direcao(ang) * (self.H * (0.13 + self.focinho.focinho) * 0.9)
            T.particulas(tela, narina, (2, 1), (255, 150, 60) if ctx.golpe else (110, 100, 100), n=3, fase=ctx.a, sobe=6,
                         emite=ctx.golpe)

    def arma(self, tela, ctx, J):
        H = self.H
        topo = armas.lanca(tela, J["mao_f"], J["arma_f"], H * 0.55, MADEIRA_PODRE.escuro(1), self.LANCA, atras=H * 0.3,
                           larg_ponta=2.8)
        if ctx.anim == "ataque" and ctx.i == 1:
            d = dir_ang(J["arma_f"])
            for k in range(3):                                          # linhas de velocidade da estocada
                a = topo - d * (H * (0.12 + k * 0.1)) + v2(0, (k - 1) * 3)
                tela.traco(a, a + d * (H * 0.08), (240, 220, 200), emite=True)


# ============================================================
# CIDADELA CONGELADA
# ============================================================

GELO = Mat((156, 210, 242), 6, relevo=1.4, especular=(255, 255, 255), luz_hue=0.55)
GELO_FUNDO = Mat((72, 124, 176), 6, relevo=1.2, luz_hue=0.55)
NEVE = (236, 246, 255)


def estilhaco(tela, base, ang, comp, larg, mat=GELO, opacidade=0.85, semente=0):
    """Ponta de cristal de gelo (espinhos de ombro, coroa, cacos no chão)."""
    d = direcao(ang)
    n = v2(-d[1], d[0])
    m = tela.poly([base - n * larg, base + d * comp * 0.7 - n * larg * 0.6, base + d * comp, base + n * larg])
    return T.cristal(tela, m, mat, base, opacidade=opacidade, facetas=1, periodo=6, semente=semente)


class SentinelaDeGelo(ForjaMonstro):
    """Guardião de gelo translúcido da Cidadela: ombreiras de cristal, coração congelado e alabarda."""
    nome = "sentinela_de_gelo"
    H = 88
    estilo = "pesado"
    semente = 65
    magreza = 1.45
    braco_grosso = (1.1, 1.2)
    curvado = 0.05
    pele = GELO_FUNDO
    calca = GELO_FUNDO
    bota = GELO
    rosto = "elmo_gelo"
    garras = False
    sangue = None
    base = dict(arma_f=0.15, braco_f=(0.4, 0.9), braco_b=(0.3, 1.0))

    def rosto_elmo_gelo(self, tela, ctx, J):
        H = self.H
        m, C = cabeca_base(tela, J, GELO, larg=0.58, nariz=False, orelha=False)
        h = J["P"]["cabeca"]
        w = h * 0.9
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        tela.traco(C.pt(w * 0.05, h * 0.05), C.pt(w * 0.6, h * 0.02), (190, 245, 255) if vivo else (60, 80, 100), emite=vivo)
        if vivo:
            tela.brilho(C.pt(w * 0.4, h * 0.03), H * 0.06, (150, 230, 255), 0.6)
        for k, (x, a) in enumerate(((-0.3, -1.9), (0.0, -1.6), (0.3, -1.3))):         # coroa de espinhos de gelo
            estilhaco(tela, C.pt(w * x, h * 0.42), a + J["giro"], h * (0.9 if k == 1 else 0.65), h * 0.15, semente=k)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        couraca = tela.poly(Q.pts([(-H * 0.1, T_ * 0.25), (H * 0.11, T_ * 0.28), (H * 0.13, T_ * 0.75), (H * 0.05, T_ * 1.0),
                                   (-H * 0.12, T_ * 0.95)]))                    # couraça de gelo grossa
        m |= tela.pintar(couraca, GELO)
        for k in range(3):
            y = T_ * (0.35 + k * 0.17)
            tela.traco(Q.pt(-H * 0.09, y), Q.pt(H * 0.11, y + 1), GELO[1], sobre=True)
        peito = J["peito"]
        vivo = not (ctx.anim == "morte" and ctx.i >= 2)
        tela.chapado(tela.circulo(peito + self.frente_do_corpo(J) * (H * 0.03), H * 0.035), (170, 240, 255) if vivo else (60, 90, 120),
                     emite=vivo)                                                 # coração congelado
        if vivo:
            tela.brilho(peito, H * 0.12, (120, 220, 255), 0.45 + 0.1 * math.sin(ctx.a * 2))
        return m

    def arma(self, tela, ctx, J):
        """Alabarda de gelo: haste escura, lâmina de machado e ponta de cristal."""
        H = self.H
        d = dir_ang(J["arma_f"])
        n = v2(-d[1], d[0])
        a, topo = armas.haste(tela, J["mao_f"], J["arma_f"], H * 0.25, H * 0.62, GELO_FUNDO.escuro(1), larg=1.4)
        meia_lua = [topo - d * (H * 0.03) + n * (H * 0.02)]                      # lâmina em meia-lua
        for t in np.linspace(0, 1, 7):
            a_l = -0.2 + t * (math.pi * 0.85)
            meia_lua.append(topo - d * (H * (0.09 - 0.1 * math.cos(a_l))) + n * (H * (0.04 + 0.12 * math.sin(a_l) + 0.02)))
        meia_lua += [topo - d * (H * 0.18) + n * (H * 0.02), topo - d * (H * 0.1) + n * (H * 0.06)]
        T.cristal(tela, tela.poly(meia_lua), GELO, topo, opacidade=0.9, facetas=2, periodo=9)
        tela.pintar(tela.poly([topo - d * (H * 0.08) - n * (H * 0.01), topo - d * (H * 0.12) - n * (H * 0.07),
                               topo - d * (H * 0.06) - n * (H * 0.02)]), GELO)          # esporão de trás
        estilhaco(tela, topo - d * 2, ang=math.atan2(d[1], d[0]), comp=H * 0.14, larg=H * 0.025)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            armas.rastro(tela, J["ombro_f"], H * 0.76, H * 0.8, -0.5, 1.9, cor=(170, 225, 250))
            T.particulas(tela, topo, (H * 0.12, H * 0.08), NEVE, n=10, fase=ctx.a, sobe=4)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        for lado, esc in (("b", 0.8), ("f", 1.0)):                               # ombreiras de cristal
            o = J["ombro_" + lado]
            ang = math.atan2(J["u"][1], J["u"][0]) + 1.4
            tela.pintar(tela.elipse_girada(o + J["u"] * 1.5, H * 0.08 * esc, H * 0.06 * esc, ang), GELO)
            for k, a in enumerate((-2.2, -1.7, -1.2)):
                estilhaco(tela, o + v2(0, -H * 0.02), a + J["giro"], H * 0.12 * esc * (1.25 if k == 1 else 1), H * 0.032,
                          semente=k + 3)
        T.vitrificar(tela, tela.mascara(), J["peito"], opacidade=0.9, area=(H * 0.15, H * 0.3), semente=self.semente)
        if ctx.anim != "morte":
            T.particulas(tela, J["peito"], (H * 0.35, H * 0.3), NEVE, n=8, fase=ctx.a, sobe=-H * 0.2, emite=False,
                         semente=4)
        elif ctx.i >= 2:                                                         # se parte em cacos
            rng = random.Random(ctx.i)
            for k in range(7):
                p = v2(self.ancora[0] + rng.uniform(-0.4, 0.6) * H, self.ancora[1] - 1)
                estilhaco(tela, p, rng.uniform(-2.6, -0.5), H * rng.uniform(0.05, 0.1), H * 0.02, semente=k)


class ArautoDaNevasca(ForjaMonstro):
    """Arauto da nevasca: espectro de manto gelado, coroa de cristal, olhos brancos e trompa de osso."""
    nome = "arauto_da_nevasca"
    H = 80
    estilo = "magia"
    semente = 67
    magreza = 0.9
    braco_longo = 1.1
    pele = Mat((196, 218, 238), 6, relevo=1.0, luz_hue=0.55)
    roupa = Mat((128, 158, 200), 6, desce=0.35, ruido=0.15, relevo=0.6, luz_hue=0.55)
    manga = Mat((128, 158, 200), 6, ruido=0.15, relevo=0.6, luz_hue=0.55)
    capuz_mat = Mat((96, 124, 170), 6, relevo=0.7, luz_hue=0.55)
    calca = Mat((128, 158, 200), 6, relevo=0.6, luz_hue=0.55)
    manto_inteiro = True
    folga_manto = 0.1
    trapos = 6
    rosto = "vazio"
    olho_cor = (220, 248, 255)
    garras = False
    sangue = None
    OSSO_TROMPA = Mat((226, 216, 190), 6, relevo=1.2)

    def cabeca(self, tela, ctx, J):
        super().cabeca(tela, ctx, J)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        for k, (x, a, c) in enumerate(((-0.45, -2.1, 0.7), (-0.15, -1.8, 1.0), (0.15, -1.5, 0.85), (0.4, -1.25, 0.6))):
            estilhaco(tela, C.pt(h * x, h * 0.5), a + J["giro"], h * c, h * 0.13, semente=k)

    def arma(self, tela, ctx, J):
        """Trompa de osso com aros de prata na cintura; no ataque, a rajada de neve sai da mão."""
        H = self.H
        f = self.frente_do_corpo(J)
        quadril = lerp(J["quadril_f"], J["pelvis"], 0.3)
        trompa = [quadril + v2(-H * 0.03, 0), quadril + v2(H * 0.03, H * 0.05), quadril + v2(H * 0.09, H * 0.03)]
        tela.pintar(tela.corrente(trompa, [H * 0.012, H * 0.02, H * 0.03]), self.OSSO_TROMPA)
        tela.traco(trompa[1] + v2(0, -2), trompa[1] + v2(0, 2), (190, 200, 210))
        if ctx.anim == "ataque" and ctx.i in (1, 2):                             # rajada de neve em cone
            mao = J["mao_b"]
            alcance = H * (0.6 if ctx.i == 1 else 0.85)
            n = v2(-f[1], f[0])
            for k in range(4):
                abre = (k - 1.5) * 0.12
                pts = [mao + f * (alcance * t) + n * (alcance * t * abre + math.sin(t * 9 + k + ctx.a) * H * 0.02)
                       for t in np.linspace(0.12, 0.9 - 0.1 * (k % 2), 8)]
                tela.tracos(pts, (210, 236, 252) if k % 2 else (160, 205, 240), emite=True)
            for k in range(18):
                t = (k * 0.37 + ctx.i * 0.21) % 1
                p = mao + f * (alcance * (0.15 + 0.8 * t)) + n * (alcance * t * 0.35 * math.sin(k * 2.3))
                tela.px(p[0], p[1], NEVE, emite=True)
            tela.brilho(mao + f * (alcance * 0.3), H * 0.2, (190, 230, 255), 0.4)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        pes = corpo & (np.arange(tela.h)[:, None] > self.ancora[1] - 0.12 * H)
        T.esfumacar(tela, pes, J["pelvis"], cor=(200, 225, 245), fase=ctx.a, comeu=0.5, fiapos=6, sobe=6)
        T.aura(tela, tela.mascara(), (170, 220, 255), raio=4, forca=0.3, fase=ctx.a)
        if not ctx.morto:
            T.particulas(tela, J["pelvis"], (H * 0.4, H * 0.35), NEVE, n=12, fase=ctx.a, sobe=-H * 0.25, emite=False,
                         semente=6)
        if ctx.anim == "morte" and ctx.i >= 2:
            fx.fumaca(tela, J["peito"], H * 0.1, cor=(210, 230, 245), fase=ctx.a, n=6, sobe=12)


# ============================================================
# CHEFE SECRETO: O MERCADOR MASCARADO
# ============================================================

OURO_MERCADOR = metal((150, 118, 62), especular=(232, 210, 150), ruido=0.2)        # ouro velho, sem brilho de joia
VELUDO_MERCADOR = Mat((48, 18, 28), 6, desce=0.35, ruido=0.16, relevo=0.8)         # vinho quase preto, gasto
COURO_BOLSA = Mat((92, 64, 44), 5, relevo=1.1, ruido=0.25)
PORCELANA = Mat((226, 218, 204), 6, relevo=1.0, ruido=0.06, especular=(250, 248, 240))
RENDA_AMARELADA = Mat((206, 192, 156), 5, relevo=0.9, ruido=0.12)
VAZIO = (6, 2, 8)                                                                    # o que há atrás da máscara


class MercadorMascarado(ForjaMonstro):
    """Alto e curvado sob um manto de veludo vinho quase preto, gasto, com uma gola de babados amarelada.
    A máscara de porcelana está rachada e falta um pedaço: atrás dela só há escuridão, e no fundo dos olhos brilham
    duas moedas ("a máscara não esconde um rosto, e sim o preço que ele já pagou"). O sorriso pintado é largo demais
    e costurado. Dedos longos, unhas compridas e anéis; chaves, ampulheta, bolsas e um cordão de dentes.
    Na morte, a máscara cai partida e o capuz fica vazio."""
    nome = "mercador_mascarado"
    H = 92
    estilo = "estocada"
    semente = 71
    magreza = 1.08
    cabeca_tam = 1.2
    curvado = 0.22
    braco_longo = 1.18
    base = {"braco_b": (0.25, 0.45)}                                                  # a mão de trás fica junto ao corpo
    pele = Mat((196, 188, 176), 6, relevo=0.9, ruido=0.08)                              # mãos pálidas e magras
    roupa = VELUDO_MERCADOR
    manga = Mat((44, 16, 26), 6, ruido=0.16, relevo=0.8)
    capuz_mat = Mat((34, 12, 20), 6, relevo=0.8, ruido=0.15)
    manto_inteiro = True
    folga_manto = 0.12
    trapos = 4
    rosto = "mascara_mercador"
    olho_cor = (255, 206, 96)
    garras = True

    def caiu(self, ctx):
        return ctx.anim == "morte" and ctx.i >= 2

    def rosto_mascara_mercador(self, tela, ctx, J):
        """Capuz fundo, babados amarelados e a máscara de porcelana rachada (na morte, só o vazio)."""
        from ..humanoide import capuz
        _, C, face = capuz(tela, J, self.capuz_mat, ponta=0.42, sombra=VAZIO, larg=1.16)
        h = J["P"]["cabeca"]
        w = h * 0.9
        self.babados(tela, C, w, h)
        if self.caiu(ctx):                                                     # a máscara caiu: o capuz está vazio
            for x in (w * 0.24, w * 0.46):
                tela.px(*C.pt(x, h * 0.06), (90, 70, 30))
            return
        oval = [C.pt(w * (0.34 + math.cos(a) * 0.4), h * (-0.04 + math.sin(a) * (0.52 if math.sin(a) > 0 else 0.56)))
                for a in np.linspace(0, 2 * math.pi, 24)[:-1]]
        mm = tela.pintar(tela.poly(oval), PORCELANA, nivel=0.18)
        lado = tela.poly(C.pts([(-w * 0.1, h * 0.5), (w * 0.06, h * 0.5), (w * 0.04, -h * 0.75), (-w * 0.1, -h * 0.75)]))
        ys, xs = np.nonzero(lado & mm)
        T.multiplicar(tela, ys, xs, 0.88)                                       # o lado da máscara na sombra
        lasca = tela.poly(C.pts([(w * 0.5, h * 0.48), (w * 0.72, h * 0.3), (w * 0.7, h * 0.1), (w * 0.58, h * 0.22),
                                 (w * 0.52, h * 0.36)]))
        tela.chapado(lasca & mm, VAZIO)                                          # falta um pedaço: escuridão
        tela.px(*C.pt(w * 0.62, h * 0.24), (150, 30, 40), emite=True)
        rach = C.pts([(w * 0.52, h * 0.3), (w * 0.44, h * 0.16), (w * 0.47, h * 0.04), (w * 0.38, -h * 0.12),
                      (w * 0.41, -h * 0.26)])
        tela.tracos(rach, (96, 86, 80), sobre=True)                              # a rachadura que desce pelo rosto
        for x in (w * 0.2, w * 0.48):                                            # os olhos: buracos com uma moeda no fundo
            olho = tela.elipse_girada(C.pt(x, h * 0.08), max(1.4, w * 0.12), max(1.0, h * 0.075), 0.1)
            tela.chapado(olho & mm, VAZIO)
            if not ctx.morto:
                moeda = C.pt(x + w * 0.02, h * 0.07)
                tela.px(moeda[0], moeda[1], self.olho_cor, emite=True)
                tela.brilho(moeda, 2.5, self.olho_cor, 0.6)
            sujeira = C.pt(x - w * 0.02, -h * 0.02)                              # escorrido de sujeira sob o olho
            tela.traco(sujeira, sujeira + v2(0.5, h * 0.2), (150, 140, 126), sobre=True)
        sorriso = C.pts([(w * 0.02, -h * 0.18), (w * 0.12, -h * 0.3), (w * 0.3, -h * 0.35), (w * 0.5, -h * 0.31),
                         (w * 0.66, -h * 0.14)])
        tela.tracos(sorriso, (110, 16, 26), sobre=True)                          # sorriso largo demais...
        for p in sorriso[1:-1]:                                                  # ...e costurado (um pontinho de linha)
            tela.px(p[0], p[1] - 1, (60, 14, 18))

    def babados(self, tela, C, w, h):
        """Gola de babados amarelada sob a máscara (cada dobra é um semicírculo)."""
        centro = C.pt(w * 0.2, -h * 0.72)
        gola = tela.elipse(centro[0], centro[1], w * 0.62, h * 0.2)
        for k in range(7):
            a = math.pi * (0.1 + 0.8 * k / 6)
            p = centro + v2(math.cos(a) * w * 0.6, math.sin(a) * h * 0.16)
            gola |= tela.circulo(p, h * 0.1)
        mg = tela.pintar(gola, RENDA_AMARELADA)
        for k in range(6):                                                       # as dobras
            x = centro[0] - w * 0.45 + k * w * 0.18
            tela.traco(v2(x, centro[1] - h * 0.12), v2(x + 1, centro[1] + h * 0.14), RENDA_AMARELADA[1], sobre=True)
        T.manchas(tela, mg, centro, (150, 130, 90), escala=3, quantidade=0.3, forca=0.6, semente=self.semente)

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        borda = tela.poly(Q.pts([(H * 0.06, T_ * 0.9), (H * 0.085, T_ * 0.9), (H * 0.12, -H * 0.42), (H * 0.095, -H * 0.42)])) & m
        tela.pintar(borda, OURO_MERCADOR)                                         # debrum de ouro velho, gasto
        dentes = [Q.pt(H * (-0.04 + k * 0.028), T_ * (0.8 - 0.12 * math.sin(math.pi * k / 5))) for k in range(6)]
        tela.tracos(dentes, (70, 56, 40))                                         # cordão de dentes
        for p in dentes[1:-1]:
            tela.traco(p, p + v2(0, 2), (226, 216, 196))
        cinto = tela.poly(Q.pts([(-H * 0.1, T_ * 0.1), (H * 0.12, T_ * 0.12), (H * 0.12, T_ * 0.03), (-H * 0.1, T_ * 0.01)]))
        tela.pintar(cinto & m, COURO_BOLSA.escuro(1))
        self.penduricalhos(tela, ctx, Q, T_)
        return m

    def penduricalhos(self, tela, ctx, Q, T_):
        """Pendurado no cinto: um molho de chaves, uma ampulheta (vende segundos de vida) e duas bolsas."""
        H = self.H
        balanco = math.sin(ctx.a) * 1.0
        argola = Q.pt(-H * 0.07, T_ * 0.04)                                       # chaves
        tela.traco(argola, argola + v2(balanco, H * 0.05), (60, 54, 50))
        for k in range(3):
            topo = argola + v2(balanco + (k - 1) * 2, H * 0.05)
            fim = topo + v2((k - 1) * 0.6, H * 0.06)
            tela.traco(topo, fim, (150, 140, 120))
            tela.px(fim[0] + 1, fim[1], (150, 140, 120))
        alca = Q.pt(H * 0.05, T_ * 0.04)                                          # ampulheta
        c = alca + v2(balanco * 0.5, H * 0.08)
        a, b = H * 0.03, H * 0.045
        vidro = tela.poly([c + v2(-a, -b), c + v2(a, -b), c + v2(0, 0)]) | tela.poly([c + v2(0, 0), c + v2(a, b), c + v2(-a, b)])
        tela.pintar(vidro, Mat((150, 170, 180), 5, relevo=1.2, especular=(255, 255, 255)))
        tela.chapado(tela.poly([c + v2(-a * 0.7, b * 0.85), c + v2(a * 0.7, b * 0.85), c + v2(0, b * 0.25)]), (200, 170, 100))
        tela.px(c[0], c[1], (200, 170, 100))                                       # o fio de areia caindo
        for y in (-b, b):
            tela.traco(c + v2(-a - 1, y), c + v2(a + 1, y), (70, 50, 36))
        tela.traco(alca, c + v2(0, -b), (70, 50, 36))
        for x in (H * 0.12, -H * 0.02):                                            # bolsas de couro
            topo = Q.pt(x, T_ * 0.02)
            saco = tela.circulo(topo + v2(0, H * 0.05), H * 0.035) | tela.poly([topo + v2(-2, 0), topo + v2(2, 0), topo + v2(0, H * 0.035)])
            tela.pintar(saco, COURO_BOLSA)
            tela.traco(topo + v2(-2, 1), topo + v2(2, 1), OURO_MERCADOR[2])

    def arma(self, tela, ctx, J):
        """Adaga fina e curva; anéis em todos os dedos."""
        if self.caiu(ctx):
            return
        H = self.H
        armas.adaga(tela, J["mao_f"], J["arma_f"], H * 0.22, metal((150, 156, 166), especular=(240, 240, 250), ruido=0.2),
                    OURO_MERCADOR, larg=1.3)
        for lado in ("f", "b"):
            m = J["mao_" + lado]
            for k, cor in enumerate(((200, 170, 80), (150, 30, 40), (200, 170, 80))):
                tela.px(m[0] + k - 1, m[1] + 1, cor)
        if ctx.anim == "ataque" and ctx.i == 1:
            d = dir_ang(J["arma_f"])
            ponta = J["mao_f"] + d * (H * 0.22)
            for k in range(3):
                a = ponta - d * (H * (0.1 + k * 0.08)) + v2(0, (k - 1) * 3)
                tela.traco(a, a + d * (H * 0.06), (220, 214, 200), emite=True)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        if not self.caiu(ctx):                                                    # fiapos de fumaça na barra do manto
            fx.fumaca(tela, v2(self.ancora[0] + H * 0.02, self.ancora[1] - H * 0.04), H * 0.08, cor=(46, 36, 50),
                      fase=ctx.a, n=4, sobe=H * 0.08)
        if ctx.anim == "dano":                                                   # moedas caindo dos bolsos
            T.particulas(tela, J["pelvis"], (H * 0.15, H * 0.1), (230, 196, 100), n=7, fase=ctx.a, sobe=-H * 0.25,
                         emite=False, semente=ctx.i)
        if self.caiu(ctx):                                                       # a máscara partida no chão e moedas
            rng = random.Random(3)
            for k in range(10):
                p = v2(self.ancora[0] + rng.uniform(-0.2, 0.7) * H, self.ancora[1] + rng.choice((-1, 0)))
                tela.px(p[0], p[1], (230, 196, 100) if k % 2 else (170, 136, 60))
            chao = self.ancora[1]
            for k, (dx, larg) in enumerate(((0.75, 0.06), (0.86, 0.045))):
                c = v2(self.ancora[0] + dx * H, chao - 2)
                caco = tela.elipse(c[0], c[1], H * larg, H * 0.022) & (tela.alfa == 0)
                tela.pintar(caco, PORCELANA, nivel=0.05)
                if k == 0:
                    tela.px(c[0] + 1, c[1] - 1, VAZIO)
                    tela.traco(c + v2(-H * 0.03, 0), c + v2(H * 0.02, -1), (110, 16, 26))
