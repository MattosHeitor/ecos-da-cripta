"""Forja 3: monstros distorcidos e humanoides.

ForjaMonstro usa o mesmo esqueleto dos heróis (humanoide.py: proporções humanas, IK, poses de
ataque de anim.ESTILOS) e acrescenta:

    deformações   corcunda, corpo curvado, braços longos, assimetria, cabeça grande/pequena,
                  magreza, pernas curtas/longas, barriga
    kits          rostos (vazio, monstro, caveira, máscara, afogado), armadura quebrada, trapos,
                  correntes, garras
    acabamentos   líquido escorrendo, rachaduras com brasa, aura, partículas

Um monstro novo é uma subclasse que troca esses atributos e, se quiser, sobrescreve uma etapa
do desenho (arma(), atras(), acabamento()...).
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, lerp
from ..anim import Modelo
from ..humanoide import (perna, braco, tronco, pescoco, cabeca_base, manto, capuz, quadro_tronco,
                         quadro_cabeca, sangue_no_chao)
from ..personagens.herois import OSSO
from .. import texturas as T
from .partes import direcao

PELE_PODRE = Mat((128, 120, 118), 6, relevo=1.0, ruido=0.2, satur=0.5)
TRAPO = Mat((64, 54, 52), 5, desce=0.25, ruido=0.25, relevo=0.7)
FERRUGEM = (110, 58, 34)
GARRA = (226, 216, 196)


class ForjaMonstro(Modelo):
    """Humanoide deformado. Atributos de classe = a receita do monstro."""

    geo_rapida = True
    H = 76
    estilo = "garra"
    semente = 31
    # ----- deformações -----
    corcunda = 0.0                    # fração de H
    curvado = 0.0                     # tronco inclinado para a frente (radianos)
    braco_longo = 1.0
    braco_grosso = (1.0, 1.0)         # (braço de trás, braço da frente): assimetria
    cabeca_tam = 1.0
    magreza = 1.0
    pernas_comp = 1.0
    barriga = 0.0
    # ----- aparência -----
    pele = PELE_PODRE
    roupa = None                      # Mat do manto/túnica (None = sem roupa)
    manto_inteiro = False             # True = manto até os pés; False = saia rasgada da cintura
    barra = 0.1                       # altura da barra da saia sobre o chão (0.35+ = túnica curta)
    folga_manto = 0.07                # quanto o manto abre na barra
    calca = None                      # Mat das pernas (None = pele à mostra)
    manga = None                      # Mat das mangas (None = braço nu); a mão continua de pele
    bota = None                       # Mat das botas/grevas
    capuz_mat = None                  # Mat do capuz (rosto "vazio")
    trapos = 0                        # tiras penduradas na cintura e nos braços
    armadura = None                   # Mat de metal: peitoral e ombreira quebrados
    rosto = "monstro"                 # monstro | vazio | caveira | mascara | afogado
    olho_cor = (255, 70, 40)
    garras = True
    correntes = 0
    escorre = None                    # cor de líquido escorrendo do corpo
    brasas = None                     # cor das rachaduras que brilham
    aura_cor = None
    sangue = ((70, 6, 14), (110, 14, 24))

    def __init__(self, **kw):
        g = self.magreza
        self.prop = dict(braco=0.168 * self.braco_longo, antebraco=0.152 * self.braco_longo,
                         cabeca=0.132 * self.cabeca_tam, coxa=0.235 * self.pernas_comp, canela=0.225 * self.pernas_comp,
                         l_coxa=0.052 * g, l_canela=0.04 * g, l_braco=0.036 * g, l_antebraco=0.032 * g)
        super().__init__(**kw)

    # ---------------- pose ----------------
    def pose_base(self):
        b = dict(braco_f=(0.3, 0.5), braco_b=(-0.15, 0.55), pe_f=(-0.08, 0), pe_b=(0.1, 0),
                 quadril=(0.0, 0.02 * self.curvado))
        b.update(self.base)
        return b

    def pose(self, ctx):
        p = super().pose(ctx)
        if not (ctx.anim == "morte" and ctx.i >= 2):        # a curvatura vale em toda pose de pé
            p["tronco"] = p.get("tronco", 0) + self.curvado
            p["cabeca"] = p.get("cabeca", 0) - self.curvado * 0.75
        return p

    # ---------------- desenho (método-modelo) ----------------
    def desenhar(self, tela, ctx, J):
        """Ordem: trás, braço de trás, pernas, corpo, cabeça, braço da frente/arma, acabamentos, morte."""
        escuro = self.pele.escuro(1)
        self.atras(tela, ctx, J)
        self.membro_braco(tela, J, "b", escuro, self.braco_grosso[0])
        calca = self.calca or self.pele
        for lado, mat in (("b", calca.escuro(1)), ("f", calca)):
            bota = None if self.bota is None else (self.bota.escuro(1) if lado == "b" else self.bota)
            perna(tela, J, lado, mat, bota=bota, pe_mat=mat if self.calca is None else None, grossura=self.magreza ** 0.5)
            if self.garras and self.bota is None:
                self.unhas(tela, J["dedo_" + lado], 0.0, 2)
        corpo = self.corpo(tela, ctx, J)
        self.cabeca(tela, ctx, J)
        self.arma(tela, ctx, J)
        self.membro_braco(tela, J, "f", self.pele, self.braco_grosso[1])
        self.acabamento(tela, ctx, J, corpo)
        self.morte(tela, ctx, J)

    def atras(self, tela, ctx, J):
        """Capa, asas, aura de trás... (subclasses)."""
        if self.roupa is not None and self.trapos:
            self.tiras(tela, ctx, J, atras=True)

    def membro_braco(self, tela, J, lado, mat, grossura=1.0):
        manga = mat if self.manga is None else (self.manga if lado == "f" else self.manga.escuro(1))
        braco(tela, J, lado, manga, mat, grossura=grossura * (1.25 if self.manga is not None else 1.0))
        if self.garras:
            m, c = J["mao_" + lado], J["cotovelo_" + lado]
            d = m - c
            self.unhas(tela, m, math.atan2(d[1], d[0]), 3, comp=self.H * 0.045 * grossura)

    def unhas(self, tela, base, ang, n, comp=None):
        comp = comp or self.H * 0.025
        for k in range(n):
            a = ang + (k - (n - 1) / 2) * 0.35
            meio = base + direcao(a) * comp * 0.6
            ponta = meio + direcao(a + 0.5) * comp * 0.5
            tela.tracos([base, meio, ponta], GARRA)

    def corpo(self, tela, ctx, J):
        H = self.H
        m = tronco(tela, J, self.pele, cintura=0.1 * self.magreza, peito=0.15 * self.magreza, barriga=self.barriga,
                   corcunda=self.corcunda)
        if self.magreza < 0.95:                                      # costelas à mostra
            Q = quadro_tronco(J)
            T_ = J["P"]["tronco"]
            for k in range(3):
                y = T_ * (0.45 + k * 0.1)
                tela.traco(Q.pt(-0.02 * H, y), Q.pt(0.05 * H, y - 1), self.pele[1], sobre=True)
        pescoco(tela, J, self.pele, 0.03 * self.magreza)
        if self.roupa is not None:
            if self.manto_inteiro:
                m |= manto(tela, J, self.roupa, folga=self.folga_manto, rasgos=7, semente=self.semente)
            else:
                m |= manto(tela, J, self.roupa, folga=self.folga_manto * 0.7, rasgos=6, ombros=False, semente=self.semente,
                           barra=self.barra)
        if self.armadura is not None:
            m |= self.armadura_quebrada(tela, J)
        return m

    def armadura_quebrada(self, tela, J):
        """Peitoral com um rombo (a pele aparece), rachaduras, amassados e ferrugem; ombreira partida."""
        H = self.H
        Q = quadro_tronco(J)
        T_ = J["P"]["tronco"]
        placa = tela.poly(Q.pts([(-0.07 * H, T_ * 0.35), (0.08 * H, T_ * 0.38), (0.085 * H, T_ * 0.8),
                                 (0.02 * H, T_ * 0.98), (-0.07 * H, T_ * 0.85)]))
        rng = random.Random(self.semente)
        c = Q.pt(0.03 * H, T_ * rng.uniform(0.5, 0.65))
        rombo = tela.poly([c + v2(math.cos(a), math.sin(a)) * H * 0.035 * (0.6 + 0.6 * rng.random())
                           for a in np.linspace(0, 2 * math.pi, 9)[:-1]])
        mp = tela.pintar(placa & ~rombo, self.armadura)
        T.rachaduras(tela, mp, c, area=(4, 4), n=3, passos=4, cor=self.armadura[0], emite=False, semente=self.semente)
        T.manchas(tela, mp, c, FERRUGEM, escala=3, quantidade=0.3, forca=0.65, semente=self.semente)
        o = J["ombro_f"]
        ang = math.atan2(J["u"][1], J["u"][0]) + 1.4
        ombreira = tela.elipse_girada(o + J["u"] * 1.5, H * 0.07, H * 0.05, ang)
        ombreira &= ~tela.poly([o + v2(H * 0.02, H * 0.0), o + v2(H * 0.09, -H * 0.02), o + v2(H * 0.09, H * 0.06)])
        mo = tela.pintar(ombreira, self.armadura)
        T.manchas(tela, mo, o, FERRUGEM, escala=3, quantidade=0.3, forca=0.6, semente=self.semente + 1)
        for k in range(2):                                          # rebites
            p = o + v2(-H * 0.03 + k * H * 0.03, -H * 0.01)
            tela.px(p[0], p[1], self.armadura[-1])
        return mp | mo

    def tiras(self, tela, ctx, J, atras=False):
        """Trapos pendurados que balançam com a animação."""
        H = self.H
        rng = random.Random(self.semente + (7 if atras else 0))
        mat = self.roupa.escuro(1) if atras else self.roupa
        for k in range(self.trapos // (2 if atras else 1)):
            base = lerp(J["quadril_b"], J["quadril_f"], rng.random()) + v2(0, H * 0.06)
            comp = H * rng.uniform(0.12, 0.25)
            vento = math.sin(ctx.a + k) * 2 + (4 if ctx.golpe else 0)
            pts = [base, base + v2(-vento * 0.4, comp * 0.5), base + v2(-vento - 1, comp)]
            tela.pintar(tela.corrente(pts, [H * 0.018, H * 0.014, H * 0.008]), mat)

    def cabeca(self, tela, ctx, J):
        getattr(self, "rosto_" + self.rosto)(tela, ctx, J)

    def arma(self, tela, ctx, J):
        """Armas (subclasses). O padrão é atacar com as garras: três arranhões curvos à frente da mão."""
        if self.estilo != "garra" or ctx.anim != "ataque" or ctx.i not in (1, 2):
            return
        H = self.H
        mao = J["mao_f"]
        d = mao - J["cotovelo_f"]
        ang = math.atan2(d[1], d[0])
        comp = H * (0.3 if ctx.i == 1 else 0.18)
        for k in (-1, 0, 1):
            ini = mao + direcao(ang + math.pi / 2) * (k * H * 0.035) + direcao(ang) * (H * 0.03)
            pts = [ini + direcao(ang - 0.9 + t * 1.3) * (comp * t) for t in np.linspace(0, 1, 6)]
            tela.tracos(pts, (255, 236, 236) if k == 0 else (210, 150, 160), emite=True)
        tela.brilho(mao + direcao(ang) * comp * 0.5, comp * 0.5, (255, 200, 210), 0.25)

    def acabamento(self, tela, ctx, J, corpo):
        H = self.H
        if self.roupa is not None and self.trapos:
            self.tiras(tela, ctx, J)
        for k in range(self.correntes):                               # correntes presas no pulso
            mao = J["mao_b" if k % 2 else "mao_f"]
            fim = mao + v2(-H * 0.06 - k * 3, H * 0.18 + math.sin(ctx.a + k) * 2)
            self.corrente(tela, mao, fim)
        if self.escorre is not None:
            T.escorrer(tela, corpo, J["pelvis"], self.escorre, densidade=0.22, comp=5, fase=ctx.a, molhado=0.45,
                       semente=self.semente)
        if self.brasas is not None and not ctx.morto:
            T.rachaduras(tela, corpo, J["cintura"], area=(H * 0.08, H * 0.2), n=6, passos=3, cor=self.brasas,
                         semente=self.semente, brilho=0.3)
        if self.aura_cor is not None and not (ctx.anim == "morte" and ctx.i >= 2):
            T.aura(tela, tela.mascara(), self.aura_cor, raio=4, forca=0.45, fase=ctx.a)

    def corrente(self, tela, a, b, cor_escura=(40, 38, 44), cor_clara=(150, 146, 156)):
        """Corrente de elos alternados (de frente e de lado)."""
        n = max(2, int(np.linalg.norm(b - a) / 3))
        for i in range(n):
            p = lerp(a, b, (i + 0.5) / n)
            if i % 2:
                tela.traco(p + v2(0, -1), p + v2(0, 1), cor_clara)
            else:
                anel = tela.elipse(p[0], p[1], 1.6, 1.2) & ~tela.elipse(p[0], p[1], 0.6, 0.4)
                tela.chapado(anel, cor_escura)
                tela.px(p[0] - 1, p[1] - 1, cor_clara)

    def morte(self, tela, ctx, J):
        if ctx.anim == "morte" and ctx.i >= 2 and self.sangue is not None:
            cx = self.ancora[0] + self.H * (0.2 if ctx.i == 2 else 0.4)
            sangue_no_chao(tela, cx, self.ancora[1] + 1, self.H * (0.16 if ctx.i == 2 else 0.34), *self.sangue)

    # ---------------- auxiliares ----------------
    def eixo_da_cabeca(self, J):
        """(nuca, ângulo) para pôr uma Cabeca de fera (partes.py) no lugar da cabeça humana."""
        hu = J["hu"]
        frente = v2(-hu[1], hu[0])
        h = J["P"]["cabeca"]
        return J["cabeca"] - frente * (h * 0.35) - hu * (h * 0.1), math.atan2(frente[1], frente[0])

    def frente_do_corpo(self, J):
        u = J["u"]
        return v2(-u[1], u[0])

    def poca(self, tela, centro, larg, cor, cor2=None):
        """Poça no chão (água, lodo, sangue): só onde não há nada pintado, então fica atrás do corpo."""
        m = tela.elipse(centro[0], centro[1], larg, max(1.2, larg * 0.14)) & (tela.alfa == 0)
        tela.chapado(m, cor)
        if cor2 is not None:
            tela.chapado(tela.elipse(centro[0] - larg * 0.25, centro[1] - 0.5, larg * 0.4, 0.6) & m, cor2)

    # ---------------- kits de rosto ----------------
    def _olho(self, tela, p, ctx, raio=3.0, cor=None):
        cor = cor or self.olho_cor
        if cor is None:
            return
        if ctx.morto:
            tela.px(p[0], p[1], (30, 20, 24))
            return
        tela.px(p[0], p[1], cor, emite=True)
        tela.brilho(p, raio, cor, 0.8)

    def rosto_monstro(self, tela, ctx, J):
        """Crânio deformado: órbita funda com brilho, boca rasgada até a bochecha, buraco de nariz."""
        m, C = cabeca_base(tela, J, self.pele, larg=0.52, nariz=False)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.chapado(tela.elipse_girada(C.pt(w * 0.3, h * 0.08), max(1.2, w * 0.14), max(1.0, h * 0.09), 0), (16, 6, 10))
        tela.pintar(tela.capsula(C.pt(w * 0.05, h * 0.22), C.pt(w * 0.55, h * 0.16), h * 0.06, h * 0.04), self.pele.claro(1))
        self._olho(tela, C.pt(w * 0.33, h * 0.08), ctx)
        boca = [C.pt(-w * 0.05, -h * 0.18), C.pt(w * 0.55, -h * 0.22)]
        abre = 1.5 if ctx.golpe else 0.5
        tela.chapado(tela.poly([boca[0], boca[1], C.pt(w * 0.5, -h * 0.22 - abre), C.pt(w * 0.05, -h * 0.2 - abre)]),
                     (30, 6, 10))
        for k in range(5):
            p = lerp(boca[0], boca[1], (k + 0.5) / 5)
            tela.px(p[0], p[1], GARRA)
        tela.px(*C.pt(w * 0.52, -h * 0.02), (20, 8, 10))
        return m

    def rosto_vazio(self, tela, ctx, J):
        """Capuz fundo: só escuridão e dois pontos de luz no lugar dos olhos."""
        _, C, face = capuz(tela, J, self.capuz_mat or self.roupa or TRAPO, ponta=0.55, sombra=(6, 3, 8), larg=1.1)
        h = J["P"]["cabeca"]
        w = h * 0.95
        for x in (w * 0.28, w * 0.5):
            self._olho(tela, C.pt(x, h * 0.04), ctx, raio=3.5)
        T.franja(tela, face, J["cabeca"], (0, 1), comp=2, espaco=2, inclina=0.3, semente=self.semente)

    def rosto_caveira(self, tela, ctx, J):
        """Crânio: órbitas escuras com uma brasa no fundo, dentes e mandíbula solta."""
        m, C = cabeca_base(tela, J, OSSO, larg=0.5, nariz=False, orelha=False)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.chapado(tela.elipse_girada(C.pt(w * 0.3, h * 0.06), max(1.4, w * 0.16), max(1.2, h * 0.12), 0), (12, 6, 10))
        self._olho(tela, C.pt(w * 0.32, h * 0.05), ctx)
        tela.px(*C.pt(w * 0.5, -h * 0.06), (20, 10, 12))
        for k in range(4):
            p = C.pt(w * (0.12 + k * 0.12), -h * 0.28)
            tela.traco(p, p + v2(0, 2), (60, 50, 44))
        T.rachaduras(tela, m, C.pt(0, h * 0.3), area=(2, 2), n=1, passos=4, cor=(80, 70, 60), emite=False)

    def rosto_mascara(self, tela, ctx, J, mat=None):
        """Máscara ornamentada de metal cobrindo o rosto, com furos que brilham."""
        cabeca_base(tela, J, self.pele, larg=0.5)
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.82
        mat = mat or metal((180, 150, 80), especular=(255, 240, 180))
        masc = tela.poly(C.pts([(w * 0.05, h * 0.45), (w * 0.55, h * 0.38), (w * 0.66, h * 0.0), (w * 0.58, -h * 0.4),
                                (w * 0.25, -h * 0.52), (w * 0.02, -h * 0.3)]))
        mm = tela.pintar(masc, mat)
        tela.traco(C.pt(w * 0.1, h * 0.25), C.pt(w * 0.6, h * 0.2), mat[1], sobre=True)
        tela.traco(C.pt(w * 0.15, -h * 0.25), C.pt(w * 0.55, -h * 0.3), mat[1], sobre=True)
        tela.chapado(tela.elipse_girada(C.pt(w * 0.38, h * 0.1), max(1.2, w * 0.12), max(0.8, h * 0.06), 0) & mm, (10, 4, 6))
        self._olho(tela, C.pt(w * 0.4, h * 0.1), ctx)

    def rosto_afogado(self, tela, ctx, J):
        """Cabeça inchada, olhos leitosos sem pupila, boca aberta e algas no lugar do cabelo."""
        m, C = cabeca_base(tela, J, self.pele, larg=0.6, nariz=True)
        h = J["P"]["cabeca"]
        w = h * 0.9
        for x in (w * 0.22, w * 0.42):
            tela.chapado(tela.circulo(C.pt(x, h * 0.06), max(1.0, h * 0.08)), (210, 222, 210))
        tela.chapado(tela.elipse_girada(C.pt(w * 0.4, -h * 0.25), max(1.0, w * 0.1), max(1.0, h * 0.1 + (1 if ctx.golpe else 0)), 0),
                     (16, 20, 18))
        rng = random.Random(self.semente)
        for k in range(6):                                          # algas penduradas
            topo = C.pt(w * (-0.4 + k * 0.12), h * 0.45)
            comp = h * rng.uniform(0.6, 1.3)
            pts = [topo, topo + v2(-1 + math.sin(ctx.a + k), comp * 0.5), topo + v2(-2 + math.sin(ctx.a + k + 1) * 1.5, comp)]
            tela.tracos(pts, (40, 70, 44) if k % 2 else (60, 96, 50))
        T.brilho_umido(tela, m, J["cabeca"], densidade=0.08)
