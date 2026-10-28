"""Criaturas do Reino dos Ratos (docs/planos/reino_dos_ratos.md), feitas com a forja modular.

    RatoBranco       o guia: aparece correndo no mapa das fases subterrâneas e leva ao bueiro do Reino
    RatoComum        rato de esgoto pequeno; o jogo desenha vários dele para fazer o bando ("Ratos ×12")
    RatazanaGigante  o tanque: enorme, pelo eriçado, cicatrizes e uma orelha rasgada
    RatoDaPeste      doente e perigoso: pelo ralo esverdeado, bubões amarelos, baba verde e moscas em volta
    RatoNadador      liso, escuro e molhado, comprido como uma enguia (mergulha na água funda)
    RatoBombardeiro  barril de pólvora amarrado nas costas, pavio aceso; explode ao morrer

    RatoDePe         base dos ratos que andam de pé (forja de monstros + focinho de roedor + rabo)
    RatoLadrao       máscara de bandido, lenço no pescoço, saco de roubos nas costas e adaga
    RatoAlquimista   avental de couro, óculos na testa, frascos no cinto e um frasco verde na mão
    RatoXama         olhos roxos acesos, trapos, colar de ossinhos e cajado com crânio de rato
    RatoGuardaReal   dedal de elmo, tabardo vermelho com a coroa, lança de agulha e escudo de tampa de lata
    RatoArauto       gibão verde, chapéu de pena, corneta de osso e o estandarte do rato coroado nas costas
    RatoMercador     (evento) gordo, colete puído, monóculo de tampinha, mochila enorme de bugigangas e balança torta
    RatoRei          (chefe, refeito na 5R2) enorme e obeso, cabeça de ratazana velha, capa e gola de arminho, corrente
                     de rubis, coroa de ouro torta, cetro de ouro com queijo; linha "correr" (foge para o trono)
    QueijoReal       (objeto da luta do Rei) roda de queijo dourado numa bandeja de prata; o Rei come quando está mal
    NoDeCaudas       (chefe: a Rainha, refeita na 5R3) a coroa de ouro e joias presa num nó de caudas; linha "exposto"
    RatoDaRainha     base dos ratos da roda, de lado e presos pelo rabo ? coroa: Mordedor, Pestilento, Guincho e
                     Curandeiro; linha "correr" (pulam para fora e para dentro da coroa quando a roda gira)
    TronoDosRatos    (cenário animado do Salão do Trono) monte de ratos vivos e ouro com almofada, pano de arminho,
                     espaldar de veludo e postes com crânios e velas; o Rei senta nele

Os de quatro patas partem do RatoDemo (forja/criaturas/demos.py): mesmo corpo, outros números e cores.
Os de pé são como o Kobold Dinamiteiro (personagens/monstros.py): ForjaMonstro com um rosto próprio.
"""
import math
import random

import numpy as np

from ..motor import Mat, metal, v2, lerp, girar
from .. import texturas as T
from .. import fx, armas
from ..anim import idle, Ctx
from ..humanoide import quadro_tronco, manto, perna, braco
from .bestas import Besta
from ..criaturas.demos import RatoDemo, RatazanaDemo
from ..criaturas.monstro import ForjaMonstro
from ..criaturas.partes import Cabeca, Cauda, Local, direcao


class RatoBranco(RatoDemo):
    """Branco como osso lavado, olhos vermelhos e orelhas rosadas. Tem a linha extra "correr" (galope)."""
    nome = "rato_branco"
    mat = Mat((232, 226, 218), 6, relevo=1.0, ruido=0.16, dither=0.4)
    mat_barriga = (242, 234, 228)
    cabeca = Cabeca(estilo="roedor", tam=0.16, focinho=0.12, orelha="redonda", orelha_dentro=(226, 130, 142),
                    olho_cor=(255, 30, 40), olho_brilho=False)
    animacoes_extras = (("correr", 4),)
    semente = 31


class RatoComum(RatoDemo):
    """Rato de esgoto pardo, menor que o demo (o bando junta vários lado a lado)."""
    nome = "rato_comum"
    S = 26
    mat = Mat((96, 80, 70), 6, relevo=1.1, ruido=0.28, dither=0.45)
    mat_barriga = (150, 130, 116)
    cabeca = Cabeca(estilo="roedor", tam=0.17, focinho=0.12, orelha="redonda", orelha_dentro=(186, 106, 112),
                    olho_cor=(255, 46, 40), olho_brilho=False)
    semente = 41


class RatazanaGigante(RatazanaDemo):
    """Do tamanho de um cão: pelo eriçado e sujo, cicatrizes claras, sarna e baba de sangue."""
    nome = "ratazana_gigante"
    S = 60
    mat = Mat((70, 60, 58), 6, relevo=1.25, ruido=0.32, dither=0.45)
    mat_barriga = (124, 108, 100)
    crina = 1.6
    semente = 42

    def detalhes(self, tela, ctx, P, corpo):
        S, A, C, cima = self.S, P["A"], P["C"], P["cima"]
        T.manchas(tela, corpo, A, (120, 86, 84), escala=4, quantidade=0.14, forca=0.7, semente=6)      # sarna
        for t, comp in ((0.35, 0.09), (0.62, 0.07)):                                                  # cicatrizes
            meio = lerp(A, C, t) + cima * (0.06 * S)
            tela.traco(meio + v2(-comp * S * 0.5, -0.03 * S), meio + v2(comp * S * 0.5, 0.03 * S), (170, 150, 138),
                       sobre=True)
        boca = self.ponta_da_boca(P) + v2(-0.04 * S, 0.03 * S)
        regiao = tela.circulo(boca, 0.045 * S) & corpo
        T.escorrer(tela, regiao, boca, (130, 20, 26), densidade=0.5, comp=3, fase=P["fase"], molhado=0.5, semente=7)


class RatoDaPeste(RatoDemo):
    """Doente e perigoso: pelo ralo verde-acinzentado com falhas rosadas, bubões amarelos inchados,
    olhos leitosos, baba verde e três moscas rodando por cima."""
    nome = "rato_da_peste"
    S = 38
    mat = Mat((104, 110, 82), 6, relevo=1.1, ruido=0.3, dither=0.45)
    mat_barriga = (150, 150, 112)
    cabeca = Cabeca(estilo="roedor", tam=0.16, focinho=0.12, orelha="redonda", orelha_dentro=(170, 120, 110),
                    olho_cor=(200, 255, 140), olho_brilho=False)
    BUBAO = Mat((196, 194, 108), 5, relevo=1.1, dither=0.3, nivel=0.1)
    BUBOES = ((0.25, 0.12, 0.08), (0.58, 0.15, 0.07), (0.42, -0.01, 0.055))   # (t, altura, raio) em S
    semente = 43

    def detalhes(self, tela, ctx, P, corpo):
        S, A, C, cima = self.S, P["A"], P["C"], P["cima"]
        lombo = corpo & ~tela.circulo(P["nuca"], 0.2 * S)                     # a cabeça fica limpa (dá para ler)
        T.manchas(tela, lombo, A, (170, 124, 116), escala=4, quantidade=0.14, forca=0.75, semente=8)  # falhas no pelo
        T.manchas(tela, lombo, A, (70, 84, 50), escala=3, quantidade=0.15, forca=0.6, semente=9)      # mofo
        for t, altura, raio in self.BUBOES:                                                          # bubões
            centro = lerp(A, C, t) + cima * (altura * S)
            inflamado = tela.circulo(centro, raio * S * 1.45) & corpo & ~tela.circulo(centro, raio * S)
            tela.tingir(inflamado, (150, 64, 60), 0.55)                                              # pele vermelha em volta
            tela.pintar(tela.circulo(centro, raio * S), self.BUBAO, linha_interna=False)
            tela.px(centro[0] - raio * S * 0.35, centro[1] - raio * S * 0.4, (252, 246, 196))
        boca = self.ponta_da_boca(P) + v2(-0.04 * S, 0.03 * S)
        regiao = tela.circulo(boca, 0.05 * S) & corpo
        T.escorrer(tela, regiao, boca, (120, 170, 60), densidade=0.6, comp=4, fase=P["fase"], molhado=0.6, semente=10)

    def efeitos(self, tela, ctx, P):
        """Três moscas rodando em volta do lombo (somem quando ele cai)."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        S, centro = self.S, P["centro"]
        for k in range(3):
            ang = ctx.a * (1 if k % 2 else -1) + k * 2.1
            x = centro[0] + math.cos(ang) * 0.3 * S
            y = centro[1] - 0.28 * S + math.sin(ang * 2) * 0.07 * S
            tela.px(x, y, (26, 28, 22))
            tela.px(x + 1, y, (40, 44, 34))
            tela.px(x, y - 1, (150, 164, 176))                    # a asinha


class RatoNadador(RatoDemo):
    """Comprido e liso como uma enguia: pelo escuro colado de água, brilho molhado, gotas pingando e olho amarelo."""
    nome = "rato_nadador"
    S = 36
    mat = Mat((56, 62, 72), 6, relevo=1.3, ruido=0.18, dither=0.4, especular=(176, 204, 214))
    mat_barriga = (104, 112, 118)
    comprimento = 0.7
    perfil = ((0.0, 0.15, 0.13), (0.5, 0.11, 0.1), (1.0, 0.09, 0.1))
    cauda = Cauda(comp=1.15, grossura=(0.04, 0.03, 0.018, 0.008), segmentos=10, ang=math.pi - 0.1, curva=-0.3,
                  estilo="rato")
    cabeca = Cabeca(estilo="roedor", tam=0.15, focinho=0.15, orelha="redonda", orelha_dentro=(150, 96, 104),
                    olho_cor=(255, 200, 60), olho_brilho=False)
    semente = 44

    def detalhes(self, tela, ctx, P, corpo):
        T.brilho_umido(tela, corpo, P["A"], densidade=0.12)
        T.escorrer(tela, corpo, P["A"], (96, 136, 146), densidade=0.14, comp=3, fase=P["fase"], molhado=0.7, semente=11)


class RatoBombardeiro(RatoDemo):
    """Rato pardo com um barril de pólvora amarrado nas costas e o pavio aceso. Na morte, o barril explode."""
    nome = "rato_bombardeiro"
    S = 36
    mat = Mat((112, 86, 66), 6, relevo=1.1, ruido=0.26, dither=0.45)
    mat_barriga = (164, 140, 118)
    cabeca = Cabeca(estilo="roedor", tam=0.16, focinho=0.12, orelha="redonda", orelha_dentro=(196, 112, 122),
                    olho_cor=(255, 46, 40), olho_brilho=False)
    MADEIRA = Mat((126, 88, 54), 6, relevo=1.2, ruido=0.2)
    CINTA = metal((90, 86, 92), ruido=0.25)
    semente = 45

    def detalhes(self, tela, ctx, P, corpo):
        S, A, C, cima, d = self.S, P["A"], P["C"], P["cima"], P["d"]
        if ctx.anim == "morte" and ctx.i >= 2:
            return                                                     # o barril já voou pelos ares
        centro = lerp(A, C, 0.45) + cima * (0.17 * S)
        ang = math.atan2(d[1], d[0])
        barril = tela.elipse_girada(centro, 0.21 * S, 0.14 * S, ang)
        tela.pintar(barril, self.MADEIRA)
        for t in (-0.6, 0.0, 0.6):                                     # cintas de ferro
            p = centro + d * (t * 0.21 * S)
            tela.traco(p - cima * (0.13 * S), p + cima * (0.13 * S), self.CINTA[3], sobre=True)
        tela.traco(centro - cima * (0.13 * S), lerp(A, C, 0.45) - cima * (0.12 * S), (70, 52, 40), sobre=True)  # corda
        tela.px(*(centro + d * (0.3 * 0.21 * S)), (230, 220, 200))                                            # caveirinha pintada
        boca = centro + cima * (0.14 * S) + d * (0.05 * S)
        pavio = [boca, boca + cima * (0.05 * S) + d * (0.02 * S), boca + cima * (0.08 * S) - d * (0.02 * S)]
        tela.tracos(pavio, (60, 52, 44))
        if not ctx.morto:
            faisca = pavio[-1]
            tela.px(faisca[0], faisca[1], (255, 240, 160), emite=True)
            tela.brilho(faisca, 4, (255, 180, 60), 0.7)
            T.particulas(tela, faisca, (2, 2), (255, 200, 80), n=3, fase=ctx.a, sobe=4)

    def fim(self, tela, ctx, P):
        """Na morte, em vez de sangue: faíscas, a explosão do barril e o rato chamuscado na fumaça."""
        if ctx.anim != "morte":
            return super().fim(tela, ctx, P)
        S, c = self.S, P["centro"] - P["cima"] * (0.1 * self.S)
        if ctx.i == 0:
            armas.faiscas(tela, c, (255, 210, 90), n=6, raio=S * 0.2, semente=1)
        elif ctx.i == 1:
            fx.chama(tela, c + v2(0, S * 0.1), S * 0.45, S * 0.5, fx.FOGO, fase=ctx.a, linguas=4)
            armas.faiscas(tela, c, (255, 230, 140), n=14, raio=S * 0.45, semente=2)
        else:
            tela.tingir(tela.mascara() & ~tela.emite, (30, 22, 20), 0.6)
            fx.fumaca(tela, c + v2(0, -3), S * 0.12, cor=(70, 64, 66), fase=ctx.a, n=6, sobe=10)


# ============================================================
# RATOS DE PÉ (forja de monstros)
# ============================================================

class RatoDePe(ForjaMonstro):
    """Base dos ratos que andam de pé: corcunda, pernas curtas, focinho de roedor no lugar da cabeça, pelo e rabo.
    As roupas e os apetrechos ficam em vestes() (por cima do pelo) e arma() nas subclasses."""
    H = 50
    curvado = 0.25
    corcunda = 0.08
    pernas_comp = 0.72
    braco_longo = 0.85
    magreza = 1.2
    garras = False
    rosto = "roedor"
    olho_cor = (255, 46, 40)
    pele = Mat((100, 86, 78), 6, relevo=1.1, ruido=0.26, dither=0.45)
    focinho = Cabeca(estilo="roedor", tam=0.2, focinho=0.13, orelha="redonda", orelha_dentro=(196, 112, 122),
                     olho_cor=(255, 46, 40), olho_brilho=False)
    cauda = Cauda(comp=0.8, grossura=(0.035, 0.026, 0.016, 0.007), segmentos=9, ang=math.pi - 0.6, curva=-0.8,
                  estilo="rato")
    sangue = ((70, 6, 14), (110, 14, 24))

    def atras(self, tela, ctx, J):
        f = self.frente_do_corpo(J)
        base = J["pelvis"] - f * (self.H * 0.05)
        pts = self.cauda.pontos(base, self.H, balanco=0.6, fase=ctx.a, ang_extra=J["giro"])
        self.cauda.desenhar(tela, pts, self.pele.escuro(1), self.H)
        super().atras(tela, ctx, J)

    def local_da_cabeca(self, J):
        """O sistema de coordenadas da cabeça de roedor (o mesmo que a Cabeca usa ao desenhar)."""
        nuca, ang = self.eixo_da_cabeca(J)
        return Local(nuca, ang, self.H), self.focinho.tam / 0.12

    def rosto_roedor(self, tela, ctx, J):
        nuca, ang = self.eixo_da_cabeca(J)
        boca = 0.6 if ctx.golpe else 0.1
        self.focinho.desenhar(tela, nuca, ang, self.H, self.pele, boca=boca, morto=ctx.morto, fase=ctx.a,
                              semente=self.semente)
        self.na_cabeca(tela, ctx, J)

    def na_cabeca(self, tela, ctx, J):
        """Máscara, óculos, elmo... (subclasses)."""

    def corpo(self, tela, ctx, J):
        m = super().corpo(tela, ctx, J)
        T.pelagem(tela, m, J["pelvis"], ang=-math.pi / 2, comp=2, densidade=0.22, semente=self.semente, contraste=0.12)
        self.vestes(tela, ctx, J)
        return m

    def vestes(self, tela, ctx, J):
        """Roupas e apetrechos por cima do pelo (subclasses)."""


class RatoLadrao(RatoDePe):
    """Máscara de bandido nos olhos, lenço vermelho no pescoço, cinto, saco de roubos nas costas e uma adaga."""
    nome = "rato_ladrao"
    estilo = "corte"
    semente = 46
    pele = Mat((92, 80, 76), 6, relevo=1.1, ruido=0.26, dither=0.45)
    SACO = Mat((182, 156, 108), 6, relevo=1.0, ruido=0.25)
    LENCO = Mat((176, 52, 46), 5, relevo=0.9)
    LAMINA = metal((170, 172, 180), especular=(255, 255, 255))
    CABO = Mat((80, 56, 40), 5)

    def atras(self, tela, ctx, J):
        super().atras(tela, ctx, J)
        H, f = self.H, self.frente_do_corpo(J)
        centro = J["peito"] - f * (H * 0.12) + v2(0, H * 0.02)                      # o saco nas costas
        saco = tela.circulo(centro, H * 0.11) | tela.circulo(centro + v2(-H * 0.02, -H * 0.08), H * 0.06)
        tela.pintar(saco, self.SACO)
        tela.pintar(tela.circulo(centro + v2(H * 0.03, H * 0.03), H * 0.03), self.SACO.escuro(1))   # remendo
        tela.px(*(centro + v2(-H * 0.04, -H * 0.02)), (230, 200, 90))               # uma moeda escapando

    def na_cabeca(self, tela, ctx, J):
        L, k = self.local_da_cabeca(J)
        tela.chapado(tela.capsula(L(0.028 * k, -0.034 * k), L(0.078 * k, -0.031 * k), max(1.0, 0.012 * k * self.H)),
                     (30, 26, 36))                                                   # máscara de bandido
        if not ctx.morto:
            olho = L(0.058 * k, -0.03 * k)
            tela.px(olho[0], olho[1], self.olho_cor, emite=True)

    def vestes(self, tela, ctx, J):
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        lenco = tela.poly(Q.pts([(-0.08 * H, T_ * 1.02), (0.09 * H, T_ * 1.0), (0.04 * H, T_ * 0.6)]))
        tela.pintar(lenco, self.LENCO)
        tela.pintar(tela.capsula(Q.pt(-0.07 * H, T_ * 0.12), Q.pt(0.08 * H, T_ * 0.1), H * 0.018), Mat((60, 42, 34), 5))
        tela.chapado(tela.circulo(Q.pt(0.05 * H, T_ * 0.1), 1.0), (200, 170, 90))   # fivela

    def arma(self, tela, ctx, J):
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        armas.adaga(tela, J["mao_f"], J["arma_f"], self.H * 0.17, self.LAMINA, self.CABO)
        if ctx.golpe:
            armas.rastro(tela, J["ombro_f"], self.H * 0.2, self.H * 0.32, -1.2, 0.5)


class RatoAlquimista(RatoDePe):
    """Avental de couro, óculos de lente verde na testa, frascos no cinto e um frasco aceso na mão (que ele joga)."""
    nome = "rato_alquimista"
    estilo = "magia"
    semente = 47
    pele = Mat((120, 104, 92), 6, relevo=1.1, ruido=0.24, dither=0.45)
    AVENTAL = Mat((156, 120, 80), 6, relevo=0.8, desce=0.2, ruido=0.2)
    VIDRO = Mat((176, 196, 200), 5, relevo=1.2, especular=(255, 255, 255))
    CORES_DOS_FRASCOS = ((140, 220, 80), (236, 232, 200), (170, 110, 220))

    def na_cabeca(self, tela, ctx, J):
        L, k = self.local_da_cabeca(J)
        for x in (0.0, 0.04):                                                         # óculos na testa
            c = L(x * k, -0.07 * k)
            tela.pintar(tela.circulo(c, 0.022 * k * self.H), metal((160, 126, 64)))
            tela.chapado(tela.circulo(c, 0.012 * k * self.H), (120, 210, 150))
        tela.traco(L(-0.04 * k, -0.06 * k), L(0.06 * k, -0.075 * k), (60, 40, 30), sobre=True)

    def vestes(self, tela, ctx, J):
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        avental = tela.poly(Q.pts([(-0.04 * H, T_ * 0.86), (0.08 * H, T_ * 0.84), (0.1 * H, -T_ * 0.4),
                                   (-0.05 * H, -T_ * 0.42)]))
        tela.pintar(avental, self.AVENTAL)
        tela.traco(Q.pt(0.02 * H, T_ * 0.86), Q.pt(-0.03 * H, T_ * 1.0), (70, 50, 34), sobre=True)   # alça
        for i, cor in enumerate(self.CORES_DOS_FRASCOS):                              # frascos no cinto
            p = Q.pt((-0.05 + i * 0.045) * H, T_ * 0.1)
            tela.pintar(tela.capsula(p, p + v2(0, -H * 0.04), H * 0.016), Mat(cor, 5, relevo=1.2))

    def arma(self, tela, ctx, J):
        """O frasco verde na mão; no ataque ele voa girando."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            f = self.frente_do_corpo(J)
            p = J["mao_f"] + f * (H * (0.3 if ctx.i == 1 else 0.65)) + v2(0, -H * (0.2 if ctx.i == 1 else 0.1))
        else:
            p = J["mao_f"] + v2(0, -H * 0.03)
        cor = self.CORES_DOS_FRASCOS[0]
        tela.pintar(tela.circulo(p, H * 0.045), self.VIDRO)
        tela.chapado(tela.circulo(p + v2(0, H * 0.01), H * 0.03), cor, emite=True)
        tela.pintar(tela.capsula(p + v2(0, -H * 0.045), p + v2(0, -H * 0.07), H * 0.015), Mat((130, 90, 56), 4))
        tela.brilho(p, 6, cor, 0.5)


class RatoXama(RatoDePe):
    """Pelo escuro, olhos roxos acesos, trapos de pano roxo, colar de ossinhos e um cajado com um crânio de rato."""
    nome = "rato_xama"
    estilo = "magia"
    semente = 48
    pele = Mat((80, 72, 70), 6, relevo=1.1, ruido=0.26, dither=0.45)
    focinho = Cabeca(estilo="roedor", tam=0.2, focinho=0.13, orelha="redonda", orelha_dentro=(170, 104, 120),
                     olho_cor=(196, 120, 255), olho_brilho=True)
    TRAPOS = Mat((76, 54, 80), 5, desce=0.25, ruido=0.25, relevo=0.7)
    MADEIRA = Mat((92, 70, 50), 5, relevo=1.0, ruido=0.2)
    OSSO = Mat((222, 210, 184), 5, relevo=1.1)
    MAGIA = (196, 120, 255)

    def vestes(self, tela, ctx, J):
        H = self.H
        manto(tela, J, self.TRAPOS, folga=0.05, barra=0.32, rasgos=6, ombros=False, semente=self.semente)
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        for k in range(5):                                                            # colar de ossinhos
            p = Q.pt((-0.05 + k * 0.03) * H, T_ * (0.9 - abs(k - 2) * 0.04))
            tela.pintar(tela.capsula(p, p + v2(0, H * 0.025), H * 0.012), self.OSSO)

    def arma(self, tela, ctx, J):
        """O cajado com o crânio de rato no alto (a magia acende no ataque)."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        topo = armas.cajado(tela, J["mao_f"], J["arma_f"], H * 0.42, self.MADEIRA, atras=H * 0.3, torto=1.0)
        cranio = tela.circulo(topo, H * 0.045) | tela.circulo(topo + v2(H * 0.05, H * 0.01), H * 0.025)
        tela.pintar(cranio, self.OSSO)
        tela.px(topo[0] + 1, topo[1] - 1, (30, 20, 30))                              # órbita
        for k in (-1, 1):                                                             # penas penduradas
            base = topo + v2(k * H * 0.03, H * 0.04)
            tela.traco(base, base + v2(k * 1, H * 0.1 + math.sin(ctx.a + k) * 1), (110, 70, 120))
        forca = 0.9 if ctx.golpe else 0.4
        tela.brilho(topo, 7 if ctx.golpe else 4, self.MAGIA, forca)
        if not ctx.morto:
            T.particulas(tela, topo, (H * 0.06, H * 0.06), self.MAGIA, n=4, fase=ctx.a, sobe=H * 0.12, semente=self.semente)


class RatoGuardaReal(RatoDePe):
    """Mais forte que os outros: dedal de costura como elmo, tabardo vermelho com a coroa, lança de agulha e escudo de
    tampa de lata."""
    nome = "rato_guarda_real"
    estilo = "estocada"
    semente = 49
    H = 52
    magreza = 1.35
    curvado = 0.18
    pele = Mat((104, 92, 84), 6, relevo=1.1, ruido=0.24, dither=0.45)
    DEDAL = metal((188, 176, 140), especular=(255, 250, 220))
    LATA = metal((206, 208, 216), especular=(255, 255, 255))
    TABARDO = Mat((132, 34, 40), 5, relevo=0.8, desce=0.2)
    AGULHA = metal((200, 204, 214), especular=(255, 255, 255))
    OURO = (232, 196, 90)

    def na_cabeca(self, tela, ctx, J):
        L, k = self.local_da_cabeca(J)
        c = L(0.015 * k, -0.05 * k)
        elmo = tela.circulo(c, 0.052 * k * self.H) & ~tela.poly(L.pts([(-0.2 * k, -0.035 * k), (0.2 * k, -0.035 * k),
                                                                       (0.2 * k, 0.2 * k), (-0.2 * k, 0.2 * k)]))
        tela.pintar(elmo | tela.capsula(L(-0.04 * k, -0.035 * k), L(0.07 * k, -0.035 * k), 0.012 * k * self.H), self.DEDAL)
        for x, y in ((-0.01, -0.07), (0.02, -0.08), (0.045, -0.065), (0.0, -0.05), (0.03, -0.05)):   # furinhos do dedal
            p = L(x * k, y * k)
            tela.px(p[0], p[1], self.DEDAL[1])

    def vestes(self, tela, ctx, J):
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        tabardo = tela.poly(Q.pts([(-0.06 * H, T_ * 0.92), (0.08 * H, T_ * 0.9), (0.07 * H, -T_ * 0.3), (-0.05 * H, -T_ * 0.32)]))
        tela.pintar(tabardo, self.TABARDO)
        for x, y in ((0.0, 0.55), (0.02, 0.62), (0.04, 0.55), (0.0, 0.5), (0.02, 0.5), (0.04, 0.5)):   # a coroa
            p = Q.pt(x * H, T_ * y)
            tela.px(p[0], p[1], self.OURO)
        tela.pintar(tela.capsula(Q.pt(-0.07 * H, T_ * 0.1), Q.pt(0.08 * H, T_ * 0.08), H * 0.016), Mat((60, 42, 34), 5))

    def arma(self, tela, ctx, J):
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        armas.escudo(tela, J["mao_b"] + v2(H * 0.05, 0), self.LATA.claro(1), self.LATA, larg=H * 0.12, alt=H * 0.13,
                     forma="redondo")
        c = J["mao_b"] + v2(H * 0.05, 0)
        tela.traco(c + v2(-H * 0.06, 0), c + v2(H * 0.06, 0), self.LATA[1], sobre=True)    # anéis da tampa
        tela.chapado(tela.circulo(c, H * 0.02), self.LATA[len(self.LATA.cores) - 2])
        d = direcao(J["arma_f"])
        mao = J["mao_f"]
        tras, frente = mao - d * (H * 0.18), mao + d * (H * 0.42)                     # a agulha
        tela.pintar(tela.capsula(tras, frente, H * 0.016, H * 0.006), self.AGULHA)
        buraco = tras + d * (H * 0.04)
        tela.px(buraco[0], buraco[1], (40, 36, 44))
        tela.traco(tras + d * (H * 0.06), tras + d * (H * 0.11), (150, 40, 44))       # linha vermelha no buraco
        if ctx.golpe:
            tela.brilho(frente, 4, (255, 250, 230), 0.5)


class RatoArauto(RatoDePe):
    """Gibão verde com galões dourados, chapéu de pena, corneta de osso e o estandarte do rato coroado nas costas."""
    nome = "rato_arauto"
    estilo = "magia"
    semente = 50
    pele = Mat((110, 96, 86), 6, relevo=1.1, ruido=0.24, dither=0.45)
    GIBAO = Mat((58, 84, 56), 5, relevo=0.8, desce=0.2)
    ESTANDARTE = Mat((120, 30, 40), 5, relevo=0.6, desce=0.15)
    OSSO = Mat((226, 212, 182), 5, relevo=1.1)
    OURO = (232, 196, 90)

    def atras(self, tela, ctx, J):
        super().atras(tela, ctx, J)
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        base = J["ombro_b"] - self.frente_do_corpo(J) * (H * 0.06)
        topo = base + v2(-H * 0.02, -H * 0.62)
        tela.pintar(tela.capsula(base + v2(0, H * 0.1), topo, H * 0.012), Mat((90, 66, 44), 5))
        onda = math.sin(ctx.a) * H * 0.02
        pano = tela.poly([topo + v2(0, H * 0.02), topo + v2(-H * 0.2, H * 0.03 + onda), topo + v2(-H * 0.21, H * 0.2 + onda),
                          topo + v2(-H * 0.1, H * 0.16), topo + v2(0, H * 0.22)])
        tela.pintar(pano, self.ESTANDARTE)
        c = topo + v2(-H * 0.1, H * 0.1 + onda * 0.5)
        for dx, dy in ((-2, 0), (0, -1), (2, 0), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1)):   # a coroa
            tela.px(c[0] + dx, c[1] + dy, self.OURO)
        tela.px(topo[0], topo[1] - 1, self.OURO)

    def na_cabeca(self, tela, ctx, J):
        L, k = self.local_da_cabeca(J)
        chapeu = tela.poly(L.pts([(-0.05 * k, -0.045 * k), (0.07 * k, -0.05 * k), (0.03 * k, -0.085 * k), (-0.03 * k, -0.08 * k)]))
        tela.pintar(chapeu, self.GIBAO.escuro(1))
        pena = [L(-0.03 * k, -0.08 * k), L(-0.06 * k, -0.1 * k + math.sin(ctx.a) * 0.005 * k), L(-0.09 * k, -0.1 * k)]
        tela.tracos(pena, (200, 60, 56))

    def vestes(self, tela, ctx, J):
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        gibao = tela.poly(Q.pts([(-0.08 * H, T_ * 0.95), (0.08 * H, T_ * 0.92), (0.08 * H, -T_ * 0.2), (-0.08 * H, -T_ * 0.22)]))
        tela.pintar(gibao, self.GIBAO)
        for y in (0.7, 0.45, 0.2):                                                    # galões dourados
            tela.traco(Q.pt(-0.02 * H, T_ * y), Q.pt(0.07 * H, T_ * y), self.OURO, sobre=True)

    def arma(self, tela, ctx, J):
        """A corneta de osso; no ataque, o som sai em arcos."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        d = direcao(J["arma_f"] - 0.6)
        n = v2(-d[1], d[0])
        mao = J["mao_f"]
        pts = [mao - d * (H * 0.06), mao + d * (H * 0.04) - n * (H * 0.03), mao + d * (H * 0.13) - n * (H * 0.02)]
        tela.pintar(tela.corrente(pts, [H * 0.012, H * 0.022, H * 0.04]), self.OSSO)
        boca = pts[-1]
        tela.chapado(tela.circulo(boca, H * 0.022), (60, 44, 34))
        if ctx.golpe:
            ang = math.atan2(d[1], d[0])
            for r in ((0.06, 0.1), (0.14, 0.18)) if ctx.i == 1 else ((0.1, 0.14), (0.2, 0.24)):
                armas.rastro(tela, boca, H * r[0], H * r[1], ang - 0.6, ang + 0.6, cor=(240, 226, 170))


class RatoMercador(RatoDePe):
    """O mercador do Mercado Roedor (evento): gordo, colete puído, monóculo de tampinha, uma mochila enorme de
    bugigangas (vela, panela, osso, moedas) e a balança torta na mão."""
    nome = "rato_mercador"
    estilo = "magia"
    semente = 51
    H = 52
    magreza = 1.35
    pele = Mat((122, 100, 84), 6, relevo=1.1, ruido=0.24, dither=0.45)
    COLETE = Mat((96, 70, 104), 5, relevo=0.8, desce=0.2, ruido=0.3)
    MOCHILA = Mat((132, 108, 74), 6, relevo=1.0, ruido=0.3)
    LATAO = metal((176, 140, 70), especular=(255, 236, 170))

    def atras(self, tela, ctx, J):
        super().atras(tela, ctx, J)
        H, f = self.H, self.frente_do_corpo(J)
        c = J["peito"] - f * (H * 0.13) + v2(0, -H * 0.02)                          # a mochila enorme
        tela.pintar(tela.elipse(c[0], c[1], H * 0.13, H * 0.17), self.MOCHILA)
        topo = c + v2(0, -H * 0.17)
        tela.pintar(tela.capsula(topo + v2(-H * 0.02, 0), topo + v2(-H * 0.05, -H * 0.12), H * 0.016),
                    Mat((214, 200, 170), 4))                                        # uma vela torta
        tela.px(*(topo + v2(-H * 0.05, -H * 0.135)), (255, 200, 90), emite=True)
        tela.pintar(tela.circulo(topo + v2(H * 0.05, -H * 0.02), H * 0.04), metal((90, 86, 90)))   # panela
        tela.pintar(tela.capsula(c + v2(-H * 0.12, -H * 0.06), c + v2(-H * 0.2, -H * 0.12), H * 0.014),
                    Mat((222, 210, 184), 4))                                        # um osso saindo
        for k in range(3):                                                          # moedas penduradas
            tela.px(*(c + v2(-H * 0.06 + k * H * 0.05, H * 0.15)), (230, 190, 80))

    def na_cabeca(self, tela, ctx, J):
        L, k = self.local_da_cabeca(J)
        olho = L(0.058 * k, -0.03 * k)
        tela.chapado(tela.circulo(olho, 0.02 * k * self.H) & ~tela.circulo(olho, 0.012 * k * self.H), self.LATAO[3])
        tela.traco(olho + v2(0, 0.02 * k * self.H), olho + v2(-1, 0.06 * k * self.H), (60, 50, 40))     # a corrente

    def vestes(self, tela, ctx, J):
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        colete = tela.poly(Q.pts([(-0.08 * H, T_ * 0.95), (0.08 * H, T_ * 0.92), (0.09 * H, T_ * 0.05), (-0.08 * H, T_ * 0.02)]))
        mc = tela.pintar(colete, self.COLETE)
        T.manchas(tela, mc, J["pelvis"], (60, 44, 66), escala=3, quantidade=0.3, forca=0.6, semente=self.semente)
        for y in (0.7, 0.45, 0.2):                                                  # botões
            p = Q.pt(H * 0.06, T_ * y)
            tela.px(p[0], p[1], self.LATAO[3])

    def arma(self, tela, ctx, J):
        """A balança torta na mão: haste, travessão inclinado e os dois pratos."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        mao = J["mao_f"]
        topo = mao + v2(0, -H * 0.12)
        tela.traco(mao, topo, self.LATAO[1])
        inclina = 0.15 + math.sin(ctx.a) * 0.05
        a, b = topo + v2(-H * 0.08, -H * 0.08 * inclina), topo + v2(H * 0.08, H * 0.08 * inclina)
        tela.traco(a, b, self.LATAO[3])
        for ponta in (a, b):
            prato = ponta + v2(0, H * 0.06)
            tela.traco(ponta, prato, (90, 80, 60))
            tela.pintar(tela.elipse(prato[0], prato[1], H * 0.035, H * 0.012), self.LATAO)
        tela.px(*(b + v2(0, H * 0.05)), (230, 190, 80))                             # uma moeda num prato


# ============================================================
# O REI DOS RATOS (chefe, etapa 5A)
# ============================================================

class RatoRei(RatoDePe):
    """O Rei dos Ratos (refeito na etapa 5R2, pela foto do usuário): enorme e obeso, pelo cinza-escuro sarnento com
    falhas de pele rosada, barriga clara e flácida, mãos, pés e rabo rosados e pelados, olhos vermelhos, bigodes
    compridos e uma cicatriz no focinho. Capa de veludo vermelho roída com barra e gola de arminho (branco de pintas
    pretas), corrente de ouro com medalhões de rubi, anéis nos dedos, coroa de ouro torta com rubis (ainda com uma
    tampinha e um dente no lugar de duas pontas) e o cetro de ouro com um naco de queijo na ponta.

    Linhas: parado (8 quadros: coça a barriga, depois admira uma moeda), ataque (pancada de cetro), dano, morte (a
    coroa rola), sentado (no trono de ratos e ouro), decreto (ergue o cetro bem alto e lê o pergaminho), banquete (come
    um naco de queijo) e correr (6 quadros, de lado: a barriga balança, a capa voa, o rabo estica; ele sai da luta
    correndo para o trono). Na Corte Completa (5C) ele age sem sair do trono: trono_ataque (sentado, aponta o cetro e o
    queijo da ponta solta um clarão de ouro) e trono_decreto (sentado, ergue o cetro e lê o pergaminho)."""
    nome = "rei_dos_ratos"
    estilo = "corte"
    semente = 53
    H = 144
    magreza = 1.9
    curvado = 0.06
    corcunda = 0.04
    pernas_comp = 0.6
    braco_longo = 0.84
    braco_grosso = (1.15, 1.2)
    pele = Mat((80, 74, 76), 6, relevo=1.15, ruido=0.32, dither=0.5)
    cauda = Cauda(comp=0.78, grossura=(0.042, 0.032, 0.02, 0.009), segmentos=12, ang=math.pi - 0.45, curva=-0.8,
                  estilo="rato")
    BARRIGA = Mat((142, 128, 120), 6, relevo=1.35, ruido=0.24, dither=0.45)
    ROSA = Mat((200, 128, 130), 5, relevo=1.1, ruido=0.12)
    RABO = Mat((184, 120, 120), 6, relevo=1.2, ruido=0.1)
    VELUDO = Mat((136, 20, 34), 7, relevo=1.0, desce=0.28, ruido=0.14)
    ARMINHO = Mat((232, 224, 206), 5, relevo=1.15, ruido=0.16)
    OURO = metal((218, 170, 62), especular=(255, 244, 180))
    OURO_VELHO = metal((164, 120, 46))
    QUEIJO = Mat((248, 216, 122), 5, relevo=0.7, ruido=0.12)
    CASCA = Mat((206, 132, 48), 5, relevo=0.9)
    PERGAMINHO = Mat((224, 202, 158), 5, relevo=0.8)
    RUBI = ((120, 8, 22), (200, 24, 40), (255, 120, 120))
    TAMPINHA = (64, 114, 206)
    DENTE = (238, 226, 184)
    PELADO = (176, 108, 112)
    animacoes_extras = (("decreto", 4), ("banquete", 4), ("correr", 6), ("trono_ataque", 4), ("trono_decreto", 4))
    NO_TRONO = ("sentado", "trono_ataque", "trono_decreto")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.alt = int(self.H * 1.78)
        self.ancora = (int(self.H * 1.08), self.alt - 4)

    def animacoes(self):
        """O parado do Rei tem 8 quadros: 4 coçando a barriga e 4 admirando uma moeda."""
        return [(anim, 8 if anim == "parado" else n) for anim, n in super().animacoes()]

    # ---------------- poses ----------------
    def pose_no_trono(self, s=0.0):
        """Sentado no trono, largado e altivo (s = a respiração, de 0 a 1)."""
        p = self.pose_base()
        p.update(quadril=(-0.03, 0.07 + 0.004 * s), tronco=0.0, cabeca=-0.24 + 0.03 * s, respira=-0.6 * s,
                 pe_f=(0.16, -0.01), pe_b=(0.23, 0.0), joelho_f=-1, joelho_b=-1, braco_f=(0.55, 1.25 + 0.05 * s),
                 braco_b=(-0.45, 0.35), alvo_f=None, alvo_b=None)
        return p

    def pose(self, ctx):
        if ctx.anim not in ("parado", "decreto", "banquete", "correr") + self.NO_TRONO:
            return super().pose(ctx)
        i = ctx.i
        p = idle(self.pose_base(), i % 4)
        if ctx.anim == "parado":
            if i < 4:                                                   # coça a barriga
                p["braco_f"] = (0.2, 1.45 + (0.3 if i % 2 else 0.0))
            else:                                                       # admira a moeda
                p["braco_f"] = (0.95, 1.95)
                p["cabeca"] = p.get("cabeca", 0) + 0.15
            p["cabeca"] = p.get("cabeca", 0) - 0.18                     # o focinho empinado de quem manda
        elif ctx.anim == "decreto":                                     # ergue o cetro bem alto e lê o pergaminho
            p["braco_b"] = [(-1.4, 0.5), (-1.95, -0.35), (-2.1, -0.5), (-2.03, -0.42)][i]
            p["braco_f"] = [(0.6, 1.0), (1.25, 0.5), (1.4, 0.3), (1.35, 0.4)][i]
            p["tronco"] = p.get("tronco", 0) - [0.0, 0.1, 0.14, 0.1][i]
            p["cabeca"] = p.get("cabeca", 0) - [0.1, 0.3, 0.38, 0.3][i]
        elif ctx.anim == "banquete":                                    # leva o queijo à boca
            p["braco_f"] = [(0.5, 1.3), (1.15, 2.05), (1.05, 1.95), (0.35, 1.5)][i]
            p["cabeca"] = p.get("cabeca", 0) + [0.0, 0.12, 0.05, -0.05][i]
        elif ctx.anim == "correr":                                      # de lado, passadas curtas e a barriga sacudindo
            a = ctx.a
            s, c = math.sin(a), math.cos(a)
            p = self.pose_base()
            p.update(pe_f=(0.17 * s, -0.09 * max(0.0, c)), pe_b=(-0.17 * s, -0.09 * max(0.0, -c)),
                     quadril=(0.03, 0.035 + 0.03 * abs(c)), tronco=0.26, cabeca=-0.22,
                     braco_f=(0.25 - 0.8 * s, 1.2), braco_b=(-0.9 + 0.3 * s, 0.6))
        elif ctx.anim == "trono_ataque":                                # sentado: ergue o cetro e aponta para os heróis
            p = self.pose_no_trono()
            p["braco_f"] = [(2.75, -0.25), (2.05, -0.05), (1.62, 0.0), (1.1, 0.45)][i]
            p["tronco"] = [-0.06, 0.08, 0.12, 0.04][i]
            p["cabeca"] = -0.24 + [-0.08, 0.04, 0.06, 0.0][i]
        elif ctx.anim == "trono_decreto":                               # sentado: ergue o cetro e lê o pergaminho
            p = self.pose_no_trono()
            p["braco_b"] = [(-1.4, 0.5), (-1.95, -0.35), (-2.1, -0.5), (-2.03, -0.42)][i]
            p["braco_f"] = [(0.6, 1.0), (1.25, 0.5), (1.4, 0.3), (1.35, 0.4)][i]
            p["tronco"] = -[0.0, 0.06, 0.08, 0.06][i]
            p["cabeca"] = -0.24 - [0.0, 0.1, 0.14, 0.1][i]
        else:                                                           # sentado no trono, largado e altivo
            p = self.pose_no_trono([0, 0.5, 1, 0.5][i])
        p["tronco"] = p.get("tronco", 0) + self.curvado
        p["cabeca"] = p.get("cabeca", 0) - self.curvado * 0.75
        return p

    # ---------------- desenho ----------------
    def desenhar(self, tela, ctx, J):
        """Como a forja de monstros, mas com os pés e as mãos rosados e pelados."""
        self.atras(tela, ctx, J)
        self.membro_braco(tela, J, "b", self.pele.escuro(1), self.braco_grosso[0])
        for lado, mat in (("b", self.pele.escuro(1)), ("f", self.pele)):
            perna(tela, J, lado, mat, grossura=self.magreza ** 0.5)
            self.pe_rosado(tela, J, lado)
        corpo = self.corpo(tela, ctx, J)
        self.cabeca(tela, ctx, J)
        self.arma(tela, ctx, J)
        self.membro_braco(tela, J, "f", self.pele, self.braco_grosso[1])
        self.acabamento(tela, ctx, J, corpo)
        self.morte(tela, ctx, J)

    def pe_rosado(self, tela, J, lado):
        """Pé de rato: comprido, pelado e rosado, com o calcanhar alto, três dedos finos e unhas amareladas."""
        H = self.H
        mat = self.ROSA if lado == "f" else self.ROSA.escuro(1)
        tornozelo, dedo, calcanhar = J["tornozelo_" + lado], J["dedo_" + lado], J["calcanhar_" + lado]
        sola = tela.capsula(calcanhar + v2(0, -H * 0.012), dedo + v2(-H * 0.012, -H * 0.008), H * 0.02, H * 0.013)
        tela.pintar(sola | tela.circulo(tornozelo + v2(0, H * 0.006), H * 0.022), mat)
        for k in range(3):
            raiz = dedo + v2(-H * 0.014, -H * 0.012 + k * H * 0.005)
            ponta = dedo + v2(H * (0.012 + 0.004 * (k == 1)), -H * 0.008 + k * H * 0.006)
            tela.pintar(tela.capsula(raiz, ponta, 1.4, 0.9), mat, linha_interna=False)
            tela.px(ponta[0] + 1, ponta[1], self.DENTE)

    def membro_braco(self, tela, J, lado, mat, grossura=1.0):
        """Braço peludo e mão rosada de dedos finos, com anéis de ouro e rubi."""
        braco(tela, J, lado, mat, None, grossura=grossura)
        H = self.H
        mao, cot = J["mao_" + lado], J["cotovelo_" + lado]
        d = mao - cot
        d = d / max(1e-6, math.hypot(*d))
        rosa = self.ROSA if lado == "f" else self.ROSA.escuro(1)
        tela.pintar(tela.circulo(mao, H * 0.026 * grossura), rosa)
        for k, a in enumerate((-0.5, -0.15, 0.2, 0.55)):
            dd = v2(d[0] * math.cos(a) - d[1] * math.sin(a), d[0] * math.sin(a) + d[1] * math.cos(a))
            ponta = mao + dd * H * 0.045
            tela.pintar(tela.capsula(mao + dd * H * 0.015, ponta, 1.4, 1.0), rosa, linha_interna=False)
            if k in (1, 2):                                             # anéis
                anel = mao + dd * H * 0.026
                tela.px(anel[0], anel[1], (240, 200, 90))
                tela.px(anel[0], anel[1] - 1, self.RUBI[1] if k == 1 else (255, 230, 150))

    def atras(self, tela, ctx, J):
        """O rabo pelado (atrás de tudo), a capa de veludo com barra de arminho e o cetro na mão de trás."""
        H, f = self.H, self.frente_do_corpo(J)
        chao = self.ancora[1]
        caido = ctx.anim == "morte" and ctx.i >= 2
        correndo = ctx.anim == "correr"
        base = J["pelvis"] - f * (H * 0.07)
        pts = self.cauda.pontos(base, H, balanco=1.3 if correndo else 0.6, fase=ctx.a,
                                ang_extra=J["giro"] + (0.55 if correndo else 0.0))
        self.cauda.desenhar(tela, pts, self.RABO, H)
        for q in pts[2:-2:2]:                                           # anéis do rabo
            tela.px(q[0], q[1], self.RABO[1])
        self.capa(tela, ctx, J, caido, correndo, chao)
        if caido:                                                       # o cetro rolou para o chão
            a = v2(J["pelvis"][0] + H * 0.2, chao - H * 0.03)
            self.cetro(tela, a, a + v2(H * 0.42, -H * 0.02))
        elif ctx.anim not in ("ataque", "trono_ataque"):                # no ataque o cetro vai para a mão da frente
            ang = {"decreto": -1.62, "trono_decreto": -1.62, "correr": -2.25, "sentado": -2.4}.get(
                ctx.anim, -2.3 + math.sin(ctx.a) * 0.03)
            d = direcao(ang)
            brilho = 0.7 if ctx.anim in ("decreto", "trono_decreto") and ctx.i in (2, 3) else 0.0
            self.cetro(tela, J["mao_b"] - d * (H * 0.12), J["mao_b"] + d * (H * 0.5), brilho)

    def capa(self, tela, ctx, J, caido, correndo, chao):
        """A capa: veludo roído que desce dos ombros e se espalha no chão (voa para trás na corrida), dobras escuras,
        barra de arminho e furos de traça."""
        H, f = self.H, self.frente_do_corpo(J)
        if caido:
            capa = tela.elipse(J["pelvis"][0] - H * 0.06, chao - H * 0.04, H * 0.36, H * 0.07)
            tela.pintar(capa, self.VELUDO)
            self.arminho(tela, [v2(J["pelvis"][0] - H * 0.4, chao - H * 0.01), v2(J["pelvis"][0] + H * 0.28, chao - H * 0.01)],
                         H * 0.018)
            return
        onda = math.sin(ctx.a) * H * 0.012
        voa = H * 0.2 if correndo else 0.0
        sobe = (H * 0.16 + math.sin(ctx.a * 2) * H * 0.03) if correndo else 0.0
        topo_f = J["ombro_f"] + v2(0, -H * 0.04)
        topo_b = J["ombro_b"] - f * (H * 0.12) + v2(0, -H * 0.05)
        piso = v2(J["pelvis"][0], chao)
        barra = []
        for k in range(8):                                              # a barra ondulada, de trás para a frente
            t = k / 7
            p = lerp(piso - f * (H * 0.5 + voa) + v2(onda, -H * 0.02 - sobe), piso - f * (H * 0.04) + v2(0, -H * 0.02),
                     t)
            ondula = H * (0.035 if correndo else 0.008)
            barra.append(p + v2(0, math.sin(t * 9 + ctx.a * (2 if correndo else 1)) * ondula - (sobe * (1 - t) * 0.3)))
        costas = []                                                     # as costas da capa ondulam (voam na corrida)
        normal = barra[0] - topo_b
        normal = v2(normal[1], -normal[0]) / max(1e-6, math.hypot(*normal))
        for k in range(1, 6):
            t = k / 6
            onda_costas = H * (0.025 * math.sin(t * math.pi) + (0.03 * math.sin(t * 7 + ctx.a * 2) if correndo else 0))
            costas.append(lerp(topo_b, barra[0], t) - normal * onda_costas)
        capa = tela.poly([topo_f, topo_b] + costas + barra)
        for k in range(5):                                              # a barra roída e furos de traça
            capa &= ~tela.circulo(barra[1 + k] + v2(0, H * 0.012), H * (0.016 + 0.008 * (k % 2)))
        capa &= ~tela.circulo(lerp(topo_b, barra[2], 0.6), H * 0.014)
        tela.pintar(capa, self.VELUDO)
        for k in range(1, 5):                                           # dobras
            a = lerp(topo_b, topo_f, 0.2 + k * 0.12)
            b = barra[k + 1] + v2(0, -H * 0.03)
            tela.chapado(tela.capsula(a, lerp(a, b, 0.92), 0.7) & capa, (84, 10, 22))
        self.arminho(tela, [lerp(p, q, 0.5) for p, q in zip(barra, barra[1:])], H * 0.022)

    def arminho(self, tela, linha, larg):
        """Barra de arminho: pele branca e grossa, com as pontinhas pretas das caudas."""
        tela.pintar(tela.corrente(linha, [larg] * len(linha)), self.ARMINHO)
        for a, b in zip(linha, linha[1:]):
            p = lerp(a, b, 0.5)
            tela.chapado(tela.poly([p + v2(0, -larg * 0.6), p + v2(larg * 0.32, larg * 0.5), p + v2(-larg * 0.32, larg * 0.5)]),
                         (22, 18, 20))

    def cetro(self, tela, base, ponta, brilho=0.0):
        """Cetro de ouro com nós e rubis, um colar de joias e um naco de queijo furado na ponta."""
        H = self.H
        d = (ponta - base) / max(1e-6, math.hypot(*(ponta - base)))
        n = v2(-d[1], d[0])
        tela.pintar(tela.capsula(base, ponta, H * 0.012), self.OURO)
        for t in (0.22, 0.5, 0.78):                                     # nós
            tela.pintar(tela.elipse_girada(lerp(base, ponta, t), H * 0.012, H * 0.02, math.atan2(d[1], d[0])),
                        self.OURO_VELHO)
        meio = lerp(base, ponta, 0.5)
        tela.px(meio[0], meio[1], self.RUBI[1])
        tela.pintar(tela.elipse_girada(ponta, H * 0.016, H * 0.032, math.atan2(d[1], d[0])), self.OURO)   # colar
        for s in (-1, 1):
            q = ponta + n * s * H * 0.02
            tela.px(q[0], q[1], self.RUBI[1])
        bico = ponta + d * H * 0.008                                    # o naco de queijo: a ponta da fatia encaixada
        lado = [bico, bico + d * H * 0.12 + n * H * 0.062, bico + d * H * 0.1 - n * H * 0.05]   # no cetro, a casca em cima
        espessura = v2(H * 0.014, -H * 0.012)
        tela.pintar(tela.poly([lado[0], lado[1], lado[1] + espessura, lado[2] + espessura, lado[2]]), self.CASCA)
        queijo = tela.poly(lado)
        tela.pintar(queijo, self.QUEIJO)
        tela.pintar(tela.capsula(lado[1], lado[2], H * 0.011) & ~tela.poly([lado[0], lado[1], lado[2]]) |
                    tela.capsula(lado[1], lado[2], H * 0.008), self.CASCA)               # a casca larga em cima
        for t, s, r in ((0.55, 0.15, 0.013), (0.78, -0.2, 0.01), (0.4, -0.12, 0.007), (0.8, 0.35, 0.008)):
            c = bico + d * (H * 0.11 * t) + n * (H * 0.05 * s)
            tela.chapado(tela.circulo(c, H * r) & queijo, (180, 120, 42))
            tela.px(c[0] + 1, c[1] + 1, (236, 200, 120))
        if brilho:
            c = bico + d * H * 0.07
            tela.brilho(c, H * 0.16, (255, 210, 110), brilho)
            tela.px(c[0], c[1] - 2, (255, 250, 220), emite=True)

    def local_da_cabeca(self, J):
        """A cabeça do Rei é desenhada aqui mesmo (cabeca_de_rato), em frações de H: x para a frente, y para baixo."""
        nuca, ang = self.eixo_da_cabeca(J)
        return Local(nuca, ang, self.H), 1.0

    def rosto_roedor(self, tela, ctx, J):
        aberta = (ctx.golpe or (ctx.anim in ("decreto", "trono_decreto") and ctx.i in (1, 2, 3))
                  or (ctx.anim == "banquete" and ctx.i == 1) or ctx.anim == "correr"
                  or (ctx.anim == "trono_ataque" and ctx.i in (1, 2)))
        L, _ = self.local_da_cabeca(J)
        self.cabeca_de_rato(tela, ctx, L, 0.55 if aberta else 0.0)
        self.na_cabeca(tela, ctx, J)

    def cabeca_de_rato(self, tela, ctx, L, boca):
        """Cabeça de ratazana velha: crânio comprido, focinho fino, papada de rei gordo, focinho de baixo mais claro,
        orelha fina e rosada com uma mordida, olho vermelho de pálpebra pesada, nariz rosado, incisivos amarelos,
        bigodes compridos, a cicatriz no focinho e uma falha de sarna na bochecha."""
        H = self.H
        morto = ctx.morto
        if boca > 0:                                                    # a boca aberta: o escuro e o queixo caído
            dobra = L(0.07, 0.026)
            queixo = [girar(p, boca * 0.45, dobra) for p in (L(0.07, 0.02), L(0.19, 0.024), L(0.18, 0.038), L(0.08, 0.055))]
            tela.chapado(tela.poly([L(0.08, 0.02), L(0.2, 0.018), queixo[1], queixo[2], dobra]), (52, 12, 20))
            tela.pintar(tela.poly(queixo), self.pele.escuro(1))
            for x in (0.15, 0.17):                                      # dentinhos de baixo
                p = girar(L(x, 0.03), boca * 0.45, dobra)
                tela.px(p[0], p[1], self.DENTE)
        papada = tela.elipse_girada(L(0.035, 0.03), 0.062 * H, 0.036 * H, L.ang)
        cranio = tela.elipse_girada(L(0.04, -0.012), 0.076 * H, 0.06 * H, L.ang)
        focinho = tela.poly([L(0.07, -0.058), L(0.15, -0.04), L(0.205, -0.016), L(0.224, -0.002), L(0.218, 0.012),
                             L(0.17, 0.024), L(0.1, 0.04), L(0.05, 0.05)])
        cabeca = tela.pintar(papada | cranio | focinho, self.pele)
        T.pelagem(tela, cabeca, L.b, ang=L.ang + math.pi, comp=2, densidade=0.3, semente=self.semente + 3)
        claro = tela.elipse_girada(L(0.14, 0.016), 0.066 * H, 0.016 * H, L.ang) & cabeca          # focinho de baixo
        tela.pintar(claro, self.BARRIGA, linha_interna=False)
        sarna = L(0.02, 0.028)
        tela.chapado(tela.elipse(sarna[0], sarna[1], 2.4, 1.6) & cabeca, self.PELADO)
        tela.px(sarna[0] + 1, sarna[1] - 1, (140, 80, 86))
        tela.traco(L(0.13, -0.046), L(0.168, -0.012), (200, 140, 140), sobre=True)                 # cicatriz
        tela.traco(L(0.12, 0.026), L(0.2, 0.02), (36, 20, 26), sobre=True)                         # a boca
        orelha = tela.elipse_girada(L(-0.004, -0.06), 0.038 * H, 0.03 * H, L.ang - 1.0)
        orelha &= ~tela.circulo(L(-0.03, -0.088), 0.012 * H)                                        # a mordida
        tela.pintar(orelha, Mat((150, 108, 112), 5, relevo=1.0, ruido=0.15))
        dentro = tela.elipse_girada(L(0.004, -0.056), 0.026 * H, 0.019 * H, L.ang - 1.0) & orelha
        tela.chapado(dentro, (206, 128, 134))
        tela.traco(L(-0.004, -0.05), L(-0.012, -0.072), (170, 96, 104), sobre=True)               # veia
        nariz = L(0.221, 0.0)
        tela.chapado(tela.elipse(nariz[0], nariz[1], 0.012 * H, 0.009 * H), (206, 122, 130))
        tela.px(nariz[0] + 1, nariz[1] + 1, (90, 40, 46))
        for x in (0.196, 0.204):                                        # os incisivos amarelos
            tela.traco(L(x, 0.016), L(x, 0.034 + boca * 0.02), (232, 196, 96))
        olho = L(0.092, -0.03)
        tela.chapado(tela.elipse(olho[0], olho[1], 0.018 * H, 0.013 * H), (22, 10, 14))
        if morto:
            tela.traco(olho + v2(-2, 0), olho + v2(2, 0), (70, 56, 56))
        else:
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                tela.px(olho[0] + dx, olho[1] + dy, (255, 40, 30), emite=True)
            tela.px(olho[0] - 1, olho[1] - 1, (255, 230, 220), emite=True)
            tela.brilho(olho, 5, (255, 40, 30), 0.6)
        tela.tracos([L(0.07, -0.043), L(0.09, -0.047), L(0.112, -0.04)], (28, 18, 22))           # pálpebra pesada
        if not morto:                                                   # bigodes compridos balançando
            raiz = L(0.19, 0.004)
            for k, a in enumerate((-0.4, -0.18, 0.05, 0.28, 0.5)):
                comp = H * (0.12 + 0.02 * (k % 2))
                fim = raiz + direcao(L.ang + a + 0.06 * math.sin(ctx.a + k)) * comp
                tela.traco(raiz, fim, (196, 186, 176) if k % 2 else (150, 140, 134))

    def na_cabeca(self, tela, ctx, J):
        if ctx.anim == "morte" and ctx.i == 3:
            return                                                      # a coroa caiu (acabamento)
        L, _ = self.local_da_cabeca(J)
        balanca = math.sin(ctx.a * 2) * 0.06 if ctx.anim == "correr" else 0.0
        self.coroa(tela, lambda x, y: L(x + 0.034, y - 0.006), 1.0, balanca)

    def coroa(self, tela, L, k, balanca=0.0):
        """Coroa de ouro torta: aro com rubis, pontas com bolinhas (uma é um dente amarelo, outra segura uma tampinha
        de garrafa) e um rubi enorme na frente. L(x, y) = um ponto em frações de H (já na escala da cabeça)."""
        H, s = self.H, 1.5

        def P(x, y):                                                    # a coroa é maior que a cabeça pede
            q = v2(x, y + 0.066)
            q = v2(q[0] * math.cos(balanca) - q[1] * math.sin(balanca), q[0] * math.sin(balanca) + q[1] * math.cos(balanca))
            return L(0.006 + q[0] * s, -0.064 + q[1] * s)
        pontas = (-0.03, -0.012, 0.006, 0.024, 0.042)
        for j, x in enumerate(pontas):                                  # pontas (atrás do aro)
            y = -0.084 - (x + 0.034) * 0.17
            alto = 0.03 if j % 2 == 0 else 0.022
            if j == 3:                                                  # um dente amarelo no lugar da ponta
                tela.chapado(tela.poly([P(x - 0.008, y + 0.002), P(x + 0.008, y), P(x + 0.002, y - alto)]), self.DENTE)
                continue
            tela.pintar(tela.poly([P(x - 0.008, y + 0.003), P(x + 0.008, y + 0.001), P(x, y - alto)]), self.OURO)
            bola = P(x, y - alto)
            tela.pintar(tela.circulo(bola, 0.006 * k * H * s), self.OURO)
            if j == 1:                                                  # a tampinha presa numa ponta
                tela.chapado(tela.circulo(bola, 0.0075 * k * H * s), (40, 30, 30))
                tela.chapado(tela.circulo(bola, 0.0055 * k * H * s), self.TAMPINHA)
        aro = tela.poly([P(-0.038, -0.066), P(0.05, -0.08), P(0.052, -0.1), P(-0.036, -0.086)])
        tela.pintar(aro, self.OURO)
        for x in (-0.024, 0.026, 0.042):                               # rubis pequenos
            c = P(x, -0.078 - (x + 0.034) * 0.17)
            tela.chapado(tela.circulo(c, 0.004 * k * H * s), self.RUBI[1])
        c = P(0.006, -0.083)                                            # o rubi grande da frente
        tela.chapado(tela.elipse(c[0], c[1], 0.008 * k * H * s, 0.006 * k * H * s), self.RUBI[0])
        tela.chapado(tela.elipse(c[0], c[1], 0.006 * k * H * s, 0.0045 * k * H * s), self.RUBI[1])
        tela.px(c[0] - 1, c[1] - 1, self.RUBI[2])

    def vestes(self, tela, ctx, J):
        """A barriga enorme e clara (com falhas de sarna e o umbigo), a capa sobre o ombro, a gola de arminho e a
        corrente de ouro com os medalhões de rubi."""
        H = self.H
        Q, T_ = quadro_tronco(J), J["P"]["tronco"]
        eixo = Q.pt(0, T_) - Q.pt(0, 0)
        frente = Q.pt(H, 0) - Q.pt(0, 0)
        frente = frente / max(1e-6, math.hypot(*frente))
        sacode = math.cos(ctx.a * 2) * H * 0.012 if ctx.anim == "correr" else 0.0
        c = Q.pt(0.07 * H, T_ * 0.33) + v2(0, sacode)
        barriga = tela.elipse_girada(c, H * 0.205, H * 0.17, math.atan2(eixo[1], eixo[0]))
        m = tela.pintar(barriga, self.BARRIGA)
        T.pelagem(tela, m, c, ang=-math.pi / 2, comp=2, densidade=0.2, semente=self.semente + 1, contraste=0.12)
        for dx, dy, r in ((0.08, 0.06, 0.016), (-0.05, -0.08, 0.012)):  # falhas de sarna
            p = c + frente * (H * dx) + v2(0, H * dy)
            tela.chapado(tela.elipse(p[0], p[1], H * r, H * r * 0.7) & m, self.PELADO)
            tela.px(p[0] - 1, p[1], (140, 80, 86))
        umbigo = c + frente * (H * 0.13)
        tela.traco(umbigo, umbigo + v2(1, 2), self.BARRIGA[0])
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        manto = tela.poly(Q.pts([(-0.19 * H, T_ * 1.05), (0.0, T_ * 1.08), (-0.03 * H, T_ * 0.7), (-0.12 * H, T_ * 0.08),
                                 (-0.22 * H, T_ * 0.04)]))              # a capa sobre as costas e o ombro
        manto &= ~tela.circulo(Q.pt(-0.18 * H, T_ * 0.1), H * 0.022)
        tela.pintar(manto, self.VELUDO)
        self.arminho(tela, [Q.pt(-0.03 * H, T_ * 0.72), Q.pt(-0.08 * H, T_ * 0.4), Q.pt(-0.13 * H, T_ * 0.08)],
                     H * 0.02)
        gola = [Q.pt(-0.2 * H, T_ * 0.86), Q.pt(-0.06 * H, T_ * 0.8), Q.pt(0.06 * H, T_ * 0.8),
                Q.pt(0.15 * H, T_ * 0.76)]
        self.arminho(tela, gola, H * 0.034)                             # a gola de arminho
        elos = [lerp(lerp(Q.pt(-0.02 * H, T_ * 0.8), Q.pt(0.1 * H, T_ * 0.6), t),
                     lerp(Q.pt(0.1 * H, T_ * 0.6), Q.pt(0.17 * H, T_ * 0.76), t), t) for t in np.linspace(0, 1, 13)]
        for k, p in enumerate(elos):                                    # a corrente de ouro
            tela.pintar(tela.elipse(p[0], p[1], 2.0 if k % 2 else 1.3, 1.3 if k % 2 else 2.0), self.OURO,
                        linha_interna=False)
        for p, r in ((elos[7], 0.034), (elos[2], 0.022)):               # medalhões com rubi
            tela.pintar(tela.circulo(p, H * r), self.OURO)
            tela.chapado(tela.circulo(p, H * r * 0.55), self.RUBI[0])
            tela.chapado(tela.circulo(p + v2(-0.5, -0.5), H * r * 0.4), self.RUBI[1])
            tela.px(p[0] - 1, p[1] - 1, self.RUBI[2])

    def arma(self, tela, ctx, J):
        """No ataque, o cetro desce com a mão da frente (com rastro). Sentado (trono_ataque), o cetro segue o antebraço
        e o queijo da ponta solta um clarão de ouro quando ele aponta para os heróis."""
        if ctx.anim == "trono_ataque":
            self.cetro_apontado(tela, ctx, J)
            return
        if ctx.anim != "ataque":
            return
        H = self.H
        d = direcao(J["arma_f"])
        mao = J["mao_f"]
        self.cetro(tela, mao - d * (H * 0.1), mao + d * (H * 0.4))
        if ctx.golpe:
            ang = math.atan2(d[1], d[0])
            armas.rastro(tela, mao, H * 0.36, H * 0.48, ang - 1.1, ang + 0.1, cor=(240, 210, 120))

    def cetro_apontado(self, tela, ctx, J):
        """O cetro na mão da frente, na direção do antebraço; nos quadros 1 e 2 o queijo da ponta brilha e solta
        faíscas de ouro para a frente (a ordem do Rei)."""
        H = self.H
        mao = J["mao_f"]
        d = mao - J["cotovelo_f"]
        d = d / max(1e-6, math.hypot(*d))
        ponta = mao + d * (H * 0.4)
        forca = {1: 0.6, 2: 1.0}.get(ctx.i, 0.0)
        self.cetro(tela, mao - d * (H * 0.1), ponta, forca * 0.8)
        if not forca:
            return
        brilho = ponta + d * (H * 0.07)
        tela.brilho(brilho, H * (0.12 + 0.1 * forca), (255, 214, 120), forca)
        rng = random.Random(self.semente * 31 + ctx.i)
        for k in range(int(6 * forca)):                                 # faíscas voando para a frente
            p = brilho + d * (H * (0.04 + 0.05 * k)) + v2(rng.uniform(-1, 1), rng.uniform(-1, 1)) * (H * 0.025)
            tela.px(p[0], p[1], (255, 236, 160) if k % 2 else (240, 190, 80), emite=True)

    def acabamento(self, tela, ctx, J, corpo):
        super().acabamento(tela, ctx, J, corpo)
        H = self.H
        mao = J["mao_f"]
        if ctx.anim == "morte" and ctx.i == 3:                         # a coroa rolou para longe da cabeça
            nuca, _ = self.eixo_da_cabeca(J)
            chao = self.ancora[1]
            base = v2(nuca[0] + H * 0.22, chao - H * 0.02)
            self.coroa(tela, lambda x, y: base + v2((x - 0.006) * H, (y + 0.07) * H), 1.0, 0.5)
            return
        if ctx.anim == "morte":
            return
        if ctx.anim == "parado" and ctx.i >= 4:                         # a moeda que ele admira
            moeda = mao + v2(H * 0.01, -H * 0.035)
            tela.pintar(tela.circulo(moeda, H * 0.022), self.OURO)
            tela.chapado(tela.circulo(moeda, H * 0.011), (200, 150, 60))
            if ctx.i in (5, 6):
                tela.brilho(moeda + v2(-1, -1), 5, (255, 250, 200), 0.6)
        elif ctx.anim in ("decreto", "trono_decreto"):
            self.pergaminho(tela, mao, [0.04, 0.15, 0.22, 0.22][ctx.i])
        elif ctx.anim == "banquete" and ctx.i < 3:
            self.naco_de_queijo(tela, mao + v2(H * 0.01, -H * 0.02), mordido=ctx.i >= 2)
        elif ctx.anim == "correr":                                      # suor e poeira da corrida
            pisada = J["dedo_b"] if math.sin(ctx.a) > 0 else J["dedo_f"]
            for k in range(3):
                tela.px(pisada[0] - H * (0.05 + k * 0.03), pisada[1] - k, (110, 96, 90))

    def pergaminho(self, tela, mao, comprimento):
        """O pergaminho do édito, desenrolando para baixo, com linhas de texto e o selo de cera."""
        H = self.H
        topo = mao + v2(H * 0.01, -H * 0.01)
        folha = tela.poly([topo + v2(-H * 0.05, 0), topo + v2(H * 0.05, 0), topo + v2(H * 0.05, H * comprimento),
                           topo + v2(-H * 0.05, H * comprimento)])
        tela.pintar(folha, self.PERGAMINHO)
        for y in range(1, int(comprimento * 40)):                      # linhas do decreto
            yy = topo[1] + H * 0.035 + y * H * 0.025
            if yy < topo[1] + H * (comprimento - 0.03):
                tela.traco(v2(topo[0] - H * 0.035, yy), v2(topo[0] + H * (0.025 if y % 2 else 0.035), yy), (120, 90, 60))
        tela.pintar(tela.capsula(topo + v2(-H * 0.06, 0), topo + v2(H * 0.06, 0), H * 0.016), self.PERGAMINHO.escuro(1))
        if comprimento > 0.1:
            selo = topo + v2(0, H * (comprimento - 0.01))
            tela.chapado(tela.circulo(selo, H * 0.02), (170, 26, 32))
            tela.px(selo[0], selo[1], (230, 80, 80))

    def naco_de_queijo(self, tela, c, mordido=False):
        H = self.H
        naco = tela.poly([c + v2(-H * 0.05, H * 0.03), c + v2(H * 0.05, H * 0.03), c + v2(H * 0.02, -H * 0.04)])
        if mordido:
            naco &= ~tela.circulo(c + v2(H * 0.03, -H * 0.02), H * 0.025)
        tela.pintar(naco, self.QUEIJO)
        for p in (c + v2(-H * 0.015, H * 0.012), c + v2(H * 0.012, H * 0.005)):
            tela.px(p[0], p[1], (196, 150, 50))


# ============================================================
# A RAINHA DOS RATOS (chefe, etapa 5B; refeita na 5R3): a coroa-ninho no nó de caudas e os ratos da roda, de lado
# ============================================================
# Só os dois ratos da vez ficam do lado de fora (telas/combate/visual_roda.py): presos por um rabo comprido que sai da
# coroa, eles pulam para dentro dela quando a roda gira, e o próximo pula para fora. Os outros esperam lá dentro.


class RatoDaRainha(RatoDemo):
    """Rato da roda da Rainha, de lado como os outros ratos, preso pelo rabo à coroa: o toco do rabo é curto e a tela
    estende o resto até ela. Linha extra "correr" (para pular para fora e para dentro da coroa). meta_extra() grava no
    catálogo onde o toco termina ("rabo", em pixels a partir dos pés, virado para a direita)."""
    cauda = Cauda(comp=0.32, grossura=(0.045, 0.036, 0.028, 0.022), segmentos=5, ang=math.pi - 0.3, curva=-0.25,
                  estilo="rato")
    animacoes_extras = (("correr", 4),)

    def meta_extra(self):
        ponta = self.pose(Ctx("parado", 0, 4))["cauda"][-1]
        return {"rabo": [round(float(ponta[0]) - self.ancora[0]), round(float(ponta[1]) - self.ancora[1])]}


class MordedorDaRainha(RatoDaRainha):
    """O Mordedor: o maior da roda, pardo-escuro e eriçado, cheio de cicatrizes, com falhas de sarna e os incisivos
    amarelos enormes sempre à mostra (no bote, a boca escancara)."""
    nome = "mordedor_da_rainha"
    S = 48
    mat = Mat((82, 66, 60), 6, relevo=1.25, ruido=0.32, dither=0.45)
    mat_barriga = (140, 120, 106)
    crina = 1.2
    cabeca = Cabeca(estilo="roedor", tam=0.17, focinho=0.13, orelha="redonda", orelha_dentro=(180, 100, 108),
                    olho_cor=(255, 40, 30), olho_brilho=False)
    semente = 54

    def detalhes(self, tela, ctx, P, corpo):
        S, A, C, cima = self.S, P["A"], P["C"], P["cima"]
        T.manchas(tela, corpo & ~tela.circulo(P["nuca"], 0.2 * S), A, (150, 104, 100), escala=4, quantidade=0.1,
                  forca=0.7, semente=12)                                            # sarna
        for t, comp in ((0.28, 0.1), (0.5, 0.08), (0.7, 0.06)):                    # cicatrizes
            meio = lerp(A, C, t) + cima * (0.07 * S)
            tela.traco(meio + v2(-comp * S * 0.5, -0.03 * S), meio + v2(comp * S * 0.5, 0.03 * S), (180, 152, 140),
                       sobre=True)
        boca = self.ponta_da_boca(P)
        abre = 0.035 * S if ctx.golpe else 0.0
        for dx in (-0.016, 0.0):                                                   # os incisivos
            topo = boca + v2((dx - 0.02) * S, 0)
            tela.chapado(tela.poly([topo, topo + v2(0.013 * S, 0), topo + v2(0.009 * S, 0.065 * S + abre),
                                    topo + v2(0.002 * S, 0.065 * S + abre)]), (236, 208, 112))


class PestilentoDaRainha(RatoDaRainha, RatoDaPeste):
    """O Pestilento: o Rato da Peste preso na roda (mais esverdeado, bubões, baba verde e moscas)."""
    nome = "pestilento_da_rainha"
    S = 44
    mat = Mat((96, 112, 76), 6, relevo=1.15, ruido=0.32, dither=0.45)
    semente = 55


class GuinchoDaRainha(RatoDaRainha):
    """O Guincho: cinza-claro, orelhas enormes e a boca sempre meio aberta; no ataque o guincho sai em arcos."""
    nome = "guincho_da_rainha"
    S = 42
    mat = Mat((134, 128, 124), 6, relevo=1.15, ruido=0.24, dither=0.45)
    mat_barriga = (186, 178, 170)
    cabeca = Cabeca(estilo="roedor", tam=0.21, focinho=0.11, orelha="redonda", orelha_dentro=(222, 122, 132),
                    olho_cor=(255, 60, 50), olho_brilho=False)
    semente = 56

    def movimento(self, ctx):
        m = super().movimento(ctx)
        m["boca"] = max(m["boca"], 0.35)                                           # sempre guinchando
        return m

    def efeitos(self, tela, ctx, P):
        if ctx.anim != "ataque" or ctx.i not in (1, 2):
            return
        boca = self.ponta_da_boca(P)
        for r in ((0.14, 0.2), (0.27, 0.33)) if ctx.i == 1 else ((0.2, 0.26), (0.35, 0.41)):
            armas.rastro(tela, boca, self.S * r[0], self.S * r[1], -0.7, 0.7, cor=(236, 230, 210))


class CurandeiroDaRainha(RatoDaRainha):
    """O Curandeiro: pelo branco-sujo, olhos rosados, um ramo de erva verde na boca e uma luz verde fraca em volta."""
    nome = "curandeiro_da_rainha"
    S = 42
    mat = Mat((200, 192, 180), 6, relevo=1.05, ruido=0.2, dither=0.4)
    mat_barriga = (226, 218, 208)
    cabeca = Cabeca(estilo="roedor", tam=0.16, focinho=0.12, orelha="redonda", orelha_dentro=(232, 142, 152),
                    olho_cor=(255, 120, 150), olho_brilho=False)
    semente = 57

    def detalhes(self, tela, ctx, P, corpo):
        boca = self.ponta_da_boca(P)
        ramo = [boca + v2(-0.04 * self.S, 0.01 * self.S), boca + v2(0.05 * self.S, -0.025 * self.S)]
        tela.tracos(ramo, (70, 140, 60))
        for p in ramo:
            tela.chapado(tela.elipse(p[0], p[1], 0.022 * self.S, 0.014 * self.S), (120, 200, 90))

    def efeitos(self, tela, ctx, P):
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        tela.brilho(P["centro"], self.S * 0.38, (110, 220, 130), 0.25 + 0.1 * math.sin(ctx.a))


class NoDeCaudas(Besta):
    """A Rainha dos Ratos (refeita na 5R3, pela foto do usuário): uma coroa de ouro cravejada de joias presa num nó de
    caudas embaralhadas, o miolo da roda (vista um pouco de cima). Algumas caudas sobem e se enrolam por cima do aro, e
    uma luz doente brilha dentro da coroa. A tela estende um rabo do nó até cada rato.

    Linhas: parado (6: os rabos se contorcem, as joias faíscam, o nó pulsa), ataque (o nó aperta e a coroa sobe), dano,
    morte (os rabos se soltam e a coroa tomba de lado) e exposto (6: a coroa escorregou para o lado e o nó, à mostra,
    pulsa em vermelho: é a hora de acertá-lo)."""
    nome = "rainha_dos_ratos"
    S = 84
    geo_rapida = True
    animacoes_extras = (("exposto", 6),)
    RABO = Mat((178, 124, 120), 6, relevo=1.3, ruido=0.15)
    OURO = metal((220, 170, 60), especular=(255, 244, 180))
    OURO_ESCURO = metal((150, 104, 40))
    MIOLO = Mat((120, 30, 44), 6, relevo=1.2, ruido=0.25)
    JOIAS = ((200, 24, 40), (50, 90, 210), (60, 160, 80), (150, 60, 200))

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 1.6), int(S * 1.5)
        self.ancora = (self.larg // 2, self.alt // 2)

    def animacoes(self):
        return [("parado", 6), ("ataque", 4), ("dano", 2), ("morte", 4), ("sentado", 6)] + list(self.animacoes_extras)

    def pose(self, ctx):
        return {"anim": ctx.anim, "i": ctx.i, "a": ctx.a}

    def desenhar(self, tela, ctx, P):
        S = self.S
        anim, i, a = P["anim"], P["i"], P["a"]
        c = v2(self.larg / 2, self.alt / 2)
        tremor = (1.5 if i % 2 else -1.5) if anim == "dano" else 0.0
        c = c + v2(tremor, 0)
        aperta = {"ataque": [0.0, -0.08, -0.1, -0.03]}.get(anim, [0.0] * 6)[i]
        solto = {"morte": [0.03, 0.12, 0.2, 0.26]}.get(anim, [0.0] * 6)[i]
        pulso = 0.03 * math.sin(a) + aperta + solto
        anel = c + v2(0, 0.24 * S)                                      # o nó, no chão da roda
        rx, ry = 0.46 * S * (1 + pulso), 0.16 * S * (1 + pulso)
        exposto = anim == "exposto"
        caida = anim == "morte" and i >= 2
        self.anel_de_caudas(tela, anel, rx, ry, a, metade="tras", solto=solto)
        if exposto or caida:
            self.miolo(tela, anel, a, exposto)
        # a coroa: sobe no ataque, escorrega no exposto, tomba na morte
        centro = c + v2(0, (-0.06 * S if anim == "ataque" and i in (1, 2) else 0.0))
        inclina = 0.0
        if exposto:
            centro, inclina = c + v2(-0.2 * S, 0.06 * S), -0.32
        elif anim == "morte":
            centro, inclina = c + v2([0, 0.05, 0.16, 0.24][i] * S, [0, 0.04, 0.14, 0.2][i] * S), [0, 0.2, 0.9, 1.45][i]
        self.coroa(tela, centro, inclina, a, apagada=anim == "morte" and i >= 2)
        self.anel_de_caudas(tela, anel, rx, ry, a, metade="frente", solto=solto)
        if not (anim == "morte" and i >= 1):
            self.caudas_na_coroa(tela, centro, inclina, a)

    # ---------------- partes ----------------
    def anel_de_caudas(self, tela, anel, rx, ry, a, metade, solto=0.0):
        """O nó de caudas: rabos dando a volta no anel, uns por cima dos outros, com anéis marcados. metade = "tras"
        (atrás da coroa) ou "frente" (por cima da base dela)."""
        S = self.S
        rng = random.Random(9)
        for k in range(14):
            a0 = k * 2 * math.pi / 14 + rng.uniform(-0.2, 0.2) + a * 0.15
            a1 = a0 + rng.uniform(0.9, 1.6)
            meio = (a0 + a1) / 2
            na_frente = math.sin(meio) > 0
            if (metade == "frente") != na_frente:
                continue
            pts = []
            for t in np.linspace(0, 1, 6):
                ang = a0 + (a1 - a0) * t
                fora = 1 + 0.18 * math.sin(t * math.pi + k) + solto * 0.6
                sobe = math.sin(t * math.pi) * (0.05 * S if k % 2 else -0.02 * S) + solto * S * 0.5 * t
                pts.append(anel + v2(math.cos(ang) * rx * fora, math.sin(ang) * ry * fora + sobe))
            grossura = 0.05 * S if k % 3 else 0.042 * S
            mat = self.RABO if na_frente else self.RABO.escuro(1)
            tela.pintar(tela.corrente(pts, [grossura] * len(pts)), mat)
            for p in pts[1:-1]:
                tela.px(p[0], p[1], mat[1])

    def miolo(self, tela, anel, a, exposto):
        """O miolo do nó à mostra: carne escura cheia de veias, pulsando em vermelho quando está exposto."""
        S = self.S
        r = 0.2 * S * (1 + 0.08 * math.sin(a * 2))
        tela.pintar(tela.elipse(anel[0], anel[1] - 0.03 * S, r, r * 0.55), self.MIOLO)
        for k in range(5):                                              # veias
            ang = k * 1.3 + a * 0.3
            tela.traco(anel + v2(0, -0.03 * S), anel + v2(math.cos(ang) * r * 0.9, math.sin(ang) * r * 0.45 - 0.03 * S),
                       (70, 10, 24), sobre=True)
        if exposto:
            tela.brilho(anel + v2(0, -0.03 * S), S * 0.4, (255, 50, 50), 0.45 + 0.25 * math.sin(a * 2))
            tela.chapado(tela.elipse(anel[0], anel[1] - 0.04 * S, r * 0.3, r * 0.18), (255, 120, 110), emite=True)

    def coroa(self, tela, centro, inclina, a, apagada=False):
        """A coroa vista um pouco de cima: o aro (um cilindro de ouro), o escuro de dentro com uma luz doente, pontas
        com bolinhas de joia roxa, um rubi enorme na frente e safiras e esmeraldas pelo aro."""
        S = self.S
        rx, ry, alto = 0.32 * S, 0.1 * S, 0.2 * S
        topo = centro + v2(0, -0.1 * S)

        def G(p):                                                       # gira a coroa (escorregando / tombando)
            return girar(p, inclina, centro + v2(0, 0.12 * S))

        def borda(cy, ang):
            return v2(centro[0] + rx * math.cos(ang), cy + ry * math.sin(ang))
        alturas = (0.17, 0.22, 0.27, 0.22, 0.17)
        angulos_tras = [math.pi + (k + 0.5) * math.pi / 4 for k in range(4)]
        angulos_frente = [math.pi * (0.12 + 0.19 * k) for k in range(5)]
        for k, ang in enumerate(angulos_tras):                          # pontas de trás
            base = borda(topo[1], ang)
            h = 0.2 * S
            ponta = [G(base + v2(-0.035 * S, 0)), G(base + v2(0.035 * S, 0)), G(base + v2(0, -h))]
            tela.pintar(tela.poly(ponta), self.OURO_ESCURO)
            tela.pintar(tela.circulo(G(base + v2(0, -h)), 0.028 * S), self.OURO_ESCURO)
        dentro = tela.poly([G(borda(topo[1], t)) for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)])
        tela.chapado(dentro, (40, 12, 20))
        if not apagada:
            tela.brilho(G(topo), 0.2 * S, (200, 60, 90), 0.3 + 0.1 * math.sin(a * 2))
        aro = [G(borda(topo[1], t)) for t in np.linspace(0, math.pi, 14)] + \
              [G(borda(topo[1] + alto, t)) for t in np.linspace(math.pi, 0, 14)]
        tela.pintar(tela.poly(aro), self.OURO)
        for t in np.linspace(0.15, math.pi - 0.15, 9):                  # o friso do aro
            tela.px(*G(borda(topo[1] + alto * 0.82, t)), self.OURO[1])
        for k, ang in enumerate(angulos_frente):                        # pontas da frente com bolinhas de joia
            base = borda(topo[1], ang)
            h = alturas[k] * S
            ponta = [G(base + v2(-0.04 * S, 0.01 * S)), G(base + v2(0.04 * S, 0.01 * S)), G(base + v2(0, -h))]
            tela.pintar(tela.poly(ponta), self.OURO)
            bola = G(base + v2(0, -h))
            tela.chapado(tela.circulo(bola, 0.03 * S), (60, 20, 70) if apagada else self.JOIAS[3])
            if not apagada and (k + int(a * 1.5)) % 5 == 0:             # um brilho que corre pelas pontas
                tela.px(bola[0] - 1, bola[1] - 1, (255, 240, 255), emite=True)
        for t, cor, r in ((math.pi / 2, 0, 0.05), (math.pi * 0.28, 1, 0.032), (math.pi * 0.72, 2, 0.032),
                          (math.pi * 0.12, 2, 0.022), (math.pi * 0.88, 1, 0.022)):     # joias do aro
            p = G(borda(topo[1] + alto * 0.48, t))
            joia = self.JOIAS[cor] if not apagada else tuple(int(x * 0.4) for x in self.JOIAS[cor])
            tela.chapado(tela.elipse(p[0], p[1], r * S * 1.2, r * S), (70, 50, 20))
            tela.chapado(tela.elipse(p[0], p[1], r * S * 0.9, r * S * 0.75), joia)
            if not apagada:
                tela.px(p[0] - 1, p[1] - 1, (255, 230, 230))

    def caudas_na_coroa(self, tela, centro, inclina, a):
        """Dois rabos que sobem do nó e se enrolam na base do aro, em diagonal, segurando a coroa."""
        S = self.S
        for k, (x0, x1, y0, y1) in enumerate(((-0.36, 0.2, 0.2, 0.06), (0.36, -0.12, 0.22, 0.1))):
            mexe = math.sin(a + k * 2.5) * 0.012 * S
            pts = [centro + v2(x0 * S, y0 * S), centro + v2((x0 * 0.6 + x1 * 0.4) * S, (y0 * 0.4 + y1 * 0.6) * S + mexe),
                   centro + v2((x0 * 0.25 + x1 * 0.75) * S, y1 * S - mexe), centro + v2(x1 * S, (y1 + 0.03) * S)]
            pts = [girar(p, inclina * 0.7, centro + v2(0, 0.12 * S)) for p in pts]
            tela.pintar(tela.corrente(pts, [0.034 * S, 0.03 * S, 0.026 * S, 0.02 * S]), self.RABO)
            for p in pts[1:-1]:
                tela.px(p[0], p[1], self.RABO[1])


class QueijoReal(Besta):
    """O Queijo Real: uma roda enorme de queijo dourado com uma fatia cortada, numa bandeja de prata, e uma
    bandeirinha vermelha com a coroa do Rei. Não ataca; no dano treme e solta farelo; na morte se desfaz."""
    nome = "queijo_real"
    S = 40
    geo_rapida = True
    QUEIJO = Mat((240, 202, 92), 6, relevo=1.0, ruido=0.16)
    CASCA = Mat((210, 142, 54), 6, relevo=1.1, ruido=0.2)
    PRATA = metal((176, 178, 192), especular=(255, 255, 255))

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * 1.8), int(S * 1.5)
        self.ancora = (self.larg // 2, self.alt - 4)

    def pose(self, ctx):
        return {"anim": ctx.anim, "i": ctx.i, "a": ctx.a}

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        tela.pintar(tela.elipse(cx, chao - 2, 0.66 * S, 0.12 * S), self.PRATA)              # a bandeja
        tela.traco(v2(cx - 0.6 * S, chao - 2), v2(cx + 0.6 * S, chao - 2), self.PRATA[1], sobre=True)
        anim, i = P["anim"], P["i"]
        if anim == "morte" and i >= 1:
            self.pedacos(tela, cx, chao, i)
            return
        tremor = (1 if i % 2 else -1) if anim == "dano" else 0
        self.roda(tela, cx + tremor, chao - 4, rachado=anim == "morte")
        self.bandeira(tela, v2(cx - 0.12 * S + tremor, chao - 0.62 * S), P["a"])
        if anim == "dano":                                                                   # farelo
            for dx, dy in ((0.5, -0.4), (0.55, -0.25), (-0.5, -0.3)):
                tela.px(cx + dx * S, chao + dy * S, (236, 196, 90))

    def roda(self, tela, cx, base, rachado=False):
        """Cilindro baixo: lado de casca, tampa clara, fatia cortada mostrando o miolo com furos."""
        S = self.S
        rx, ry, alto = 0.5 * S, 0.16 * S, 0.3 * S
        topo = v2(cx, base - alto)
        baixo = v2(0, alto)

        def borda(graus):                                               # um ponto na borda da tampa
            a = math.radians(graus)
            return topo + v2(rx * math.cos(a), ry * math.sin(a))
        arco = [borda(g) for g in range(20, 86, 5)]                     # a fatia que falta, virada para a frente
        fatia = tela.poly([topo] + arco)
        vao = tela.poly([topo, arco[0], arco[0] + baixo, arco[-1] + baixo, arco[-1], topo + baixo]) | fatia
        lado = tela.elipse(cx, base, rx, ry) | tela.poly([v2(cx - rx, base), v2(cx + rx, base), v2(cx + rx, topo[1]),
                                                          v2(cx - rx, topo[1])])
        tela.pintar(lado & ~vao, self.CASCA)
        a, b = arco[0], arco[-1]                                        # as duas faces do miolo
        tela.pintar(tela.poly([topo, a, a + baixo, topo + baixo]), self.QUEIJO.escuro(1))
        tela.pintar(tela.poly([topo, b, b + baixo, topo + baixo]), self.QUEIJO.claro(1))
        tela.pintar(tela.elipse(topo[0], topo[1], rx, ry) & ~fatia, self.QUEIJO)
        for p, r in ((lerp(topo, b, 0.5) + baixo * 0.4, 0.035), (lerp(topo, b, 0.25) + baixo * 0.75, 0.025),
                     (lerp(topo, a, 0.55) + baixo * 0.5, 0.03), (topo + v2(-0.22 * S, -0.02 * S), 0.03),
                     (topo + v2(0.05 * S, -0.08 * S), 0.022), (v2(cx - 0.3 * S, base - 0.1 * S), 0.03)):
            tela.chapado(tela.elipse(p[0], p[1], r * S, r * S * 0.75), (196, 146, 52))        # furos
        if rachado:
            tela.tracos([v2(cx - 0.12 * S, topo[1] - 1), v2(cx - 0.06 * S, topo[1] + 0.1 * S), v2(cx - 0.14 * S, base)],
                        (110, 70, 30))

    def bandeira(self, tela, base, fase):
        S = self.S
        topo = base + v2(0, -0.3 * S)
        tela.traco(base, topo, (200, 170, 120))
        onda = math.sin(fase) * 0.02 * S
        pano = tela.poly([topo, topo + v2(0.2 * S, 0.03 * S + onda), topo + v2(0.18 * S, 0.11 * S + onda),
                          topo + v2(0, 0.1 * S)])
        tela.pintar(pano, Mat((170, 30, 40), 5, relevo=0.6))
        c = topo + v2(0.09 * S, 0.055 * S + onda * 0.5)
        for dx, dy in ((-2, 0), (0, -1), (2, 0), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1)):     # a coroa do Rei
            tela.px(c[0] + dx, c[1] + dy, (240, 200, 90))

    def pedacos(self, tela, cx, chao, i):
        """Morte: a roda se parte em pedaços (1), espalha (2) e vira um monte de farelo (3)."""
        S = self.S
        rng = random.Random(7 + i)
        espalha = [0, 0.1, 0.22, 0.3][i]
        for k in range(5 if i < 3 else 8):
            x = cx + (k - 2) * 0.18 * S * (1 + espalha * 2) + rng.uniform(-2, 2)
            tam = (0.16 - 0.04 * i) * S * rng.uniform(0.8, 1.2)
            y = chao - 3 - tam * 0.5
            pedaco = tela.poly([v2(x - tam, y + tam * 0.5), v2(x + tam, y + tam * 0.4), v2(x + tam * 0.3, y - tam * 0.7)])
            tela.pintar(pedaco, self.QUEIJO if k % 2 else self.CASCA)
        if i == 3:
            tela.traco(v2(cx + 0.3 * S, chao - 3), v2(cx + 0.6 * S, chao - 5), (200, 170, 120))  # a bandeirinha caída
            tela.chapado(tela.poly([v2(cx + 0.6 * S, chao - 5), v2(cx + 0.72 * S, chao - 9), v2(cx + 0.7 * S, chao - 4)]),
                         (170, 30, 40))


# ============================================================
# O TRONO DE RATOS E OURO (etapa 5R1: o cenário animado do Salão do Trono)
# ============================================================

class TronoDosRatos(Besta):
    """O trono do Rei dos Ratos: um monte de ratos vivos e ouro roubado. Atrás da almofada os ratos se empilham num
    encosto, coberto por um manto de veludo com barra de arminho, e no alto um crânio usa uma coroa torta. Em volta,
    montinhos de moedas, cálices, coroas, crânios e ossos; na frente, uma passadeira de veludo desce até o chão (o
    tapete do salão continua nela); dos lados, postes de ouro com crânios e velas de sebo.

    Só a linha "parado" (6 quadros): os ratos respiram, mexem a cabeça e o rabo e piscam; dois andam na base; as
    moedas brilham; as velas tremem. O jogo desenha o trono no Salão (cenarios.json "trono" -> "base" = a âncora) e o
    Rei senta na almofada (ASSENTO). As velas (VELAS) também acendem luzes no cenário (cenario_salao_do_trono.py)."""
    nome = "trono_dos_ratos"
    H = 132
    larg, alt = 252, 132
    ancora = (126, 128)
    geo_rapida = True
    semente = 58
    ASSENTO = (126, 62)
    VELAS = ((62, 30), (190, 30))
    PELOS = (Mat((70, 60, 58), 6, relevo=1.3, ruido=0.3, dither=0.5), Mat((92, 78, 70), 6, relevo=1.3, ruido=0.3),
             Mat((56, 50, 54), 6, relevo=1.3, ruido=0.3), Mat((110, 98, 90), 6, relevo=1.3, ruido=0.28))
    MONTE = Mat((40, 30, 30), 5, relevo=0.5, ruido=0.55, dither=0.6)
    VELUDO = Mat((134, 22, 36), 7, relevo=1.1, ruido=0.12, dither=0.4)
    ARMINHO = Mat((228, 222, 208), 5, relevo=1.0, ruido=0.12)
    OURO = metal((216, 170, 62), especular=(255, 242, 176))
    OURO_VELHO = metal((160, 118, 44))
    OSSO = Mat((218, 204, 174), 5, relevo=1.2)
    CERA = Mat((224, 212, 178), 5, relevo=0.8)
    RABO = Mat((172, 116, 114), 5, relevo=1.1)
    QUEIJO = Mat((232, 190, 80), 5, relevo=0.9)
    ORELHA = (186, 100, 110)
    PATA = (166, 98, 102)
    OLHO = (255, 46, 40)
    JOIAS = ((200, 30, 40), (60, 110, 210), (70, 170, 80), (150, 60, 190))
    # (x, y do meio do corpo, tamanho, para onde olha, inclinação: + = focinho para baixo, só a cabeça aparece)
    RATOS = ((24, 121, 1.4, -1, 0.05, False), (62, 119, 1.75, 1, -0.05, False), (42, 107, 1.55, 1, -0.32, False),
             (74, 98, 1.45, -1, 0.3, False), (98, 110, 1.4, -1, 0.12, False), (90, 84, 1.25, 1, -0.3, True),
             (228, 121, 1.4, 1, 0.05, False), (190, 119, 1.75, -1, -0.05, False), (210, 107, 1.55, -1, -0.32, False),
             (178, 98, 1.45, 1, 0.3, False), (154, 110, 1.4, 1, 0.12, False), (162, 84, 1.25, -1, -0.3, True))
    RATOS_DO_ENCOSTO = ((100, 56, 1.3, 1, -0.75, False), (152, 52, 1.3, -1, -0.7, False))
    MONTES_DE_OURO = ((32, 106, 12), (78, 92, 10), (110, 84, 9), (50, 126, 15), (102, 124, 10), (142, 84, 9),
                      (174, 92, 10), (220, 106, 12), (202, 126, 15), (150, 124, 10), (126, 127, 8))
    ENFEITES = (("cranio", 36, 114, 0.0, 1.1), ("cranio", 216, 116, 0.2, 1.1), ("cranio", 148, 96, -0.2, 0.9),
                ("calice", 64, 90, -0.3, 1.1), ("calice", 188, 88, 0.35, 1.0), ("coroa", 56, 109, -0.25, 1.0),
                ("coroa", 198, 108, 0.3, 1.0), ("castical", 168, 104, 0.5, 1.1), ("osso", 26, 110, -0.4, 0.9),
                ("osso", 232, 112, 0.5, 0.9), ("queijo", 84, 118, 0.0, 1.0), ("osso", 120, 100, 0.2, 1.0))

    def animacoes(self):
        return [("parado", 6)]

    def pose(self, ctx):
        return {"i": ctx.i}

    def topo_do_monte(self, x):
        """A linha de cima do monte (mais alto no meio, onde fica a almofada)."""
        d = min(1.0, abs(x - self.ancora[0]) / 118)
        return 66 + 60 * d ** 1.6

    def desenhar(self, tela, ctx, P):
        i = P["i"]
        rng = random.Random(self.semente)
        self.moedas = []
        for x, y in self.VELAS:
            self.poste(tela, x, y, i)
        self.encosto(tela, rng, i)
        self.monte(tela, rng)
        itens = [(y, lambda t, r=r: self.rato(t, r[:2], r[2], r[3], r[4], r[0] * 0.37, rng_pelo(r), i, r[5]))
                 for r in self.RATOS for y in (r[1],)]
        itens += [(y + r * 0.2, lambda t, x=x, y=y, r=r: self.monte_de_ouro(t, x, y, r, rng))
                  for x, y, r in self.MONTES_DE_OURO]
        itens += [(y + 0.5, lambda t, e=(tipo, x, y, ang, tam): getattr(self, e[0])(t, v2(e[1], e[2]), e[3], e[4]))
                  for tipo, x, y, ang, tam in self.ENFEITES]

        def rng_pelo(r):
            return self.PELOS[int(r[0] * 7 + r[1]) % len(self.PELOS)]
        for _, desenho in sorted(itens, key=lambda item: item[0]):
            desenho(tela)
        self.almofada(tela)
        self.passadeira(tela)
        for k, x0 in enumerate((70, 182)):                              # dois ratos andando na base do monte
            x = x0 + ((i * 3 + k * 7) % 18) * (1 if k == 0 else -1)
            self.rato(tela, (x, 125), 1.3, 1 if k == 0 else -1, 0.0, k * 2.0, self.PELOS[k], i)
        for _ in range(40):                                            # moedas espalhadas no chão, na frente
            self.moeda(tela, (rng.uniform(6, self.larg - 6), rng.uniform(124, 129)), rng.uniform(0.9, 1.15))
        for k in range(4):                                             # brilhos que andam pelas moedas
            x, y = self.moedas[(i * 11 + k * 37) % len(self.moedas)]
            tela.px(x, y - 1, (255, 252, 220), emite=True)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                tela.px(x + dx, y - 1 + dy, (255, 222, 140), emite=True)

    # ---------------- partes ----------------
    def poste(self, tela, x, chama_y, i):
        """Poste de ouro velho com nós, um crânio no alto e uma vela grossa de sebo em cima do crânio."""
        tela.pintar(tela.capsula(v2(x, 128), v2(x, chama_y + 30), 3.2), self.OURO_VELHO)
        for y in range(chama_y + 40, 128, 16):
            tela.pintar(tela.elipse(x, y, 4.6, 2.6), self.OURO)
        tela.pintar(tela.elipse(x, chama_y + 30, 7, 2.6), self.OURO)   # prato
        self.cranio(tela, v2(x, chama_y + 21), 0.0, 1.25)
        base, topo = v2(x, chama_y + 16), v2(x, chama_y + 4)           # vela de sebo com escorridos
        tela.pintar(tela.poly([base + v2(-3.4, 0), base + v2(3.4, 0), topo + v2(3.4, 1), topo + v2(-3.4, 0)]), self.CERA)
        for dx, comp in ((-2.6, 7), (1.8, 10), (3.2, 4)):
            tela.pintar(tela.capsula(topo + v2(dx, 1), topo + v2(dx, comp), 1.0, 1.4), self.CERA.claro(1),
                        linha_interna=False)
        tela.pintar(tela.capsula(topo + v2(-2, 14), topo + v2(-6, 21), 1.2, 1.8), self.CERA, linha_interna=False)
        fx.chama(tela, topo + v2(0, -1), 9, 5, fase=i * math.pi / 3, linguas=2, brilho=False)
        tela.brilho(topo + v2(0, -5), 16, (255, 170, 80), 0.45)

    def encosto(self, tela, rng, i):
        """O encosto: ratos empilhados atrás da almofada, um manto de veludo com barra de arminho jogado por cima,
        um crânio de coroa torta no alto e dois ratos subindo pelos lados."""
        cx = self.ancora[0]
        massa = tela.poly([v2(cx - 46, 76), v2(cx - 40, 50), v2(cx - 26, 34), v2(cx - 8, 26), v2(cx + 10, 26),
                           v2(cx + 28, 34), v2(cx + 42, 50), v2(cx + 48, 76)])
        tela.pintar(massa, self.MONTE)
        for k in range(10):                                            # vultos de ratos no escuro do encosto
            x, y = rng.uniform(cx - 38, cx + 38), rng.uniform(36, 72)
            tela.chapado(tela.elipse(x, y, rng.uniform(5, 8), rng.uniform(2.5, 4)) & massa, (28, 22, 22))
            if rng.random() < 0.5:
                tela.px(x + 4, y - 1, self.OLHO, emite=True)
        bainha = [v2(cx - 40, 58), v2(cx - 30, 64), v2(cx - 18, 60), v2(cx - 4, 66), v2(cx + 10, 61), v2(cx + 24, 66),
                  v2(cx + 36, 60), v2(cx + 44, 64)]
        manto = tela.poly([v2(cx - 30, 36), v2(cx - 12, 28), v2(cx + 12, 28), v2(cx + 30, 36), v2(cx + 44, 64)]
                          + bainha[::-1])
        for k in range(4):                                             # furos de rato no manto
            manto &= ~tela.circulo((cx - 24 + k * 16, 48 + (k % 2) * 6), 2.2)
        tela.pintar(manto, self.VELUDO.copia(desce=0.3))
        for x in (cx - 20, cx - 6, cx + 8, cx + 22):                   # dobras
            tela.chapado(tela.capsula(v2(x, 34), v2(x + (x - cx) * 0.2, 60), 0.6) & manto, (88, 14, 26))
        self.arminho(tela, bainha, 3.2)
        self.cranio(tela, v2(cx + 2, 24), 0.15, 1.5)                    # o crânio de coroa torta
        coroa = [v2(-11, 2), v2(-13, -9), v2(-7, -4), v2(-2, -13), v2(3, -4), v2(9, -11), v2(12, 0)]
        tela.pintar(tela.poly([v2(cx + 2, 16) + girar(p, -0.2) for p in coroa]), self.OURO)
        for k, cor in enumerate(self.JOIAS[:3]):
            tela.chapado(tela.circulo(v2(cx + 2, 16) + girar(v2(-6 + k * 6, -2), -0.2), 1.5), cor)
        for k, r in enumerate(self.RATOS_DO_ENCOSTO):
            sobe = (i + k * 3) % 6 * 0.8
            self.rato(tela, (r[0] + r[3] * sobe, r[1] - sobe), r[2], r[3], r[4], k * 1.7, self.PELOS[k + 1], i)

    def arminho(self, tela, linha, larg):
        """Barra de arminho seguindo uma linha: pele branca com as pintinhas pretas."""
        tela.pintar(tela.corrente(linha, [larg] * len(linha)), self.ARMINHO)
        for a, b in zip(linha, linha[1:]):
            p = lerp(a, b, 0.5)
            tela.chapado(tela.poly([p + v2(0, -1.6), p + v2(0.9, 1.2), p + v2(-0.9, 1.2)]), (22, 18, 20))

    def monte(self, tela, rng):
        """A massa escura do monte (o que fica entre os ratos e o ouro), com vultos e olhos lá no fundo."""
        contorno = [v2(4, 129)]
        for x in range(6, self.larg - 4, 6):
            contorno.append(v2(x, self.topo_do_monte(x) + rng.uniform(-2.5, 2.5)))
        contorno.append(v2(self.larg - 4, 129))
        m = tela.poly(contorno)
        tela.pintar(m, self.MONTE)
        for _ in range(50):
            x = rng.uniform(10, self.larg - 10)
            y = rng.uniform(self.topo_do_monte(x) + 3, 126)
            if rng.random() < 0.55:
                tela.chapado(tela.elipse(x, y, rng.uniform(5, 9), rng.uniform(2.5, 4)) & m, (28, 22, 22))
                if rng.random() < 0.25:
                    tela.px(x + 3, y - 1, self.OLHO, emite=True)
            else:
                tela.chapado(tela.elipse(x, y, rng.uniform(2, 3), 1.2) & m, (100, 74, 34))

    def rato(self, tela, c, tam, olhando, inclina, fase, mat, i, so_cabeca=False):
        """Um rato do monte, de lado: corpo com anca e pelo, cabeça de focinho comprido, orelha com o rosado dentro,
        olho vermelho (pisca), bigodes, patinhas e o rabo pelado em anéis, que balança."""
        c = v2(c)
        u = v2(olhando * math.cos(inclina), math.sin(inclina))
        w = v2(olhando * math.sin(inclina), -math.cos(inclina))
        resp = math.sin(fase + i * math.pi / 3)

        def L(x, y):
            return c + (u * x + w * y) * tam
        ang = math.atan2(u[1], u[0])
        cab = 0.7 * resp                                                # a cabeça mexe
        if not so_cabeca:
            balanca = math.sin(fase * 2 + i * math.pi / 3) * 2.5
            rabo = [L(-11, -1), L(-18, -2.5 + balanca * 0.5), L(-25, -5 + balanca), L(-30, -9 + balanca * 1.4)]
            tela.pintar(tela.corrente(rabo, [1.7 * tam, 1.3 * tam, 0.9 * tam, 0.5 * tam]), self.RABO,
                        linha_interna=False)
            for q in rabo[1:3]:
                tela.px(q[0], q[1], self.RABO[1])
            corpo = tela.elipse_girada(L(0, 0.3 * resp), 9.5 * tam, 5.3 * tam, ang) | tela.circulo(L(-5.5, 0.6),
                                                                                                    5.4 * tam)
            tela.pintar(corpo, mat)
            T.pelagem(tela, corpo, c, ang=math.atan2(-u[1], -u[0]), comp=2, densidade=0.28, semente=int(fase * 10))
            for x in (6.5, -7):                                         # patinhas
                tela.chapado(tela.elipse(*L(x, -5), 1.3 * tam, 0.8 * tam), self.PATA)
        else:
            for x in (4.5, 9):
                tela.chapado(tela.elipse(*L(x, -3.2), 1.3 * tam, 0.8 * tam), self.PATA)
        cabeca = tela.elipse_girada(L(8.5 + cab, 1.0), 5.2 * tam, 3.7 * tam, ang) | \
            tela.poly([L(10.5 + cab, 3.4), L(19.5 + cab, 0.0), L(10.5 + cab, -2.0)])
        tela.pintar(cabeca, mat.claro(1))
        tela.px(*L(19.5 + cab, 0.0), (176, 104, 112))                  # nariz
        orelha = tela.elipse_girada(L(6.2 + cab, 4.4), 2.0 * tam, 2.6 * tam, ang + 0.4)
        tela.pintar(orelha, mat.claro(2))
        tela.px(*L(6.4 + cab, 4.2), self.ORELHA)
        piscando = (int(fase * 3) + i) % 6 == 0
        olho = L(12.5 + cab, 2.0)
        tela.chapado(tela.elipse(olho[0], olho[1], 1.2 * tam, 0.9 * tam), (24, 16, 18))
        if not piscando:
            tela.px(olho[0], olho[1], self.OLHO, emite=True)
        for dy in (-1.4, 1.4):                                          # bigodes
            tela.traco(L(18 + cab, 0.3), L(23 + cab, 0.3 + dy), (108, 100, 96))

    def moeda(self, tela, c, tam=1.0):
        c = v2(c)
        tela.pintar(tela.elipse(c[0], c[1], 2.8 * tam, 1.3 * tam),
                    self.OURO if int(c[0] * 7 + c[1] * 3) % 10 > 2 else self.OURO_VELHO, linha_interna=True)
        self.moedas.append((c[0], c[1]))

    def monte_de_ouro(self, tela, x, y, r, rng):
        """Montinho de moedas: uma corcova de ouro com as moedas marcadas por cima (cada uma com a sua borda)."""
        tela.pintar(tela.elipse(x, y, r, r * 0.6), self.OURO_VELHO)
        for _ in range(int(r * 1.6)):
            dx = rng.uniform(-0.8, 0.8)
            dy = rng.uniform(-0.55, 0.3) * (1 - abs(dx) * 0.6)
            self.moeda(tela, (x + dx * r, y + dy * r), rng.uniform(0.9, 1.2))

    def calice(self, tela, p, ang, tam):
        d = v2(math.sin(ang), -math.cos(ang))
        n = v2(-d[1], d[0])
        tela.pintar(tela.elipse(p[0], p[1], 4 * tam, 1.4 * tam), self.OURO)
        tela.pintar(tela.capsula(p, p + d * 6 * tam, 1.1 * tam), self.OURO)
        topo = p + d * 7 * tam
        tela.pintar(tela.poly([topo - n * 2.4 * tam, topo + n * 2.4 * tam, topo + d * 6 * tam + n * 4.4 * tam,
                               topo + d * 6 * tam - n * 4.4 * tam]), self.OURO)
        tela.px(*(topo + d * 3 * tam), self.JOIAS[0])

    def cranio(self, tela, p, ang, tam):
        tela.pintar(tela.elipse(p[0], p[1], 5 * tam, 4.6 * tam), self.OSSO)
        tela.pintar(tela.poly([p + v2(-3.2, 2) * tam, p + v2(3.2, 2) * tam, p + v2(2.4, 5.6) * tam,
                               p + v2(-2.4, 5.6) * tam]), self.OSSO)
        for dx in (-1.8, 1.8):
            tela.chapado(tela.elipse(p[0] + dx * tam, p[1] + 0.8 * tam, 1.3 * tam, 1.5 * tam), (22, 12, 14))
        tela.chapado(tela.poly([p + v2(-0.6, 2.4) * tam, p + v2(0.6, 2.4) * tam, p + v2(0, 3.6) * tam]), (34, 20, 20))
        for dx in (-1.4, 0, 1.4):
            tela.px(p[0] + dx * tam, p[1] + 5 * tam, (70, 58, 50))

    def osso(self, tela, p, ang, tam):
        d = v2(math.cos(ang), math.sin(ang)) * 7 * tam
        tela.pintar(tela.capsula(p - d, p + d, 1.2 * tam), self.OSSO)
        for q in (p - d, p + d):
            tela.pintar(tela.circulo(q + v2(0, -0.8), 1.4 * tam) | tela.circulo(q + v2(0, 0.8), 1.4 * tam), self.OSSO)

    def coroa(self, tela, p, ang, tam):
        pts = [v2(-7, 3), v2(-8, -5), v2(-4, -1), v2(-1, -7), v2(2, -1), v2(6, -6), v2(7, 3)]
        tela.pintar(tela.poly([p + girar(q * tam, ang) for q in pts]), self.OURO)
        tela.px(p[0], p[1], self.JOIAS[int(abs(ang) * 10) % 4])

    def castical(self, tela, p, ang, tam):
        d = v2(math.sin(ang), -math.cos(ang))
        tela.pintar(tela.capsula(p, p + d * 12 * tam, 1.4 * tam), self.OURO_VELHO)
        tela.pintar(tela.elipse(*(p + d * 12 * tam), 3.4 * tam, 1.2 * tam), self.OURO)

    def queijo(self, tela, p, ang, tam):
        tela.pintar(tela.poly([p + v2(-6, 3) * tam, p + v2(6, 3) * tam, p + v2(2, -5) * tam]), self.QUEIJO)
        tela.px(p[0] - 1, p[1] + 1, (190, 140, 50))

    def almofada(self, tela):
        """A almofada de veludo no alto do monte (onde o Rei senta), com debrum e borlas de ouro."""
        cx, topo = self.ASSENTO
        corpo = tela.elipse(cx, topo + 5, 27, 6.5) | tela.poly([v2(cx - 27, topo + 5), v2(cx + 27, topo + 5),
                                                                  v2(cx + 23, topo + 11), v2(cx - 23, topo + 11)])
        tela.pintar(corpo, self.VELUDO)
        tela.chapado(tela.capsula(v2(cx - 25, topo + 4), v2(cx + 25, topo + 4), 0.7) & corpo, (214, 164, 66))
        for lado in (-1, 1):
            borla = v2(cx + lado * 27, topo + 7)
            tela.pintar(tela.poly([borla + v2(-2, 0), borla + v2(2, 0), borla + v2(3, 8), borla + v2(-3, 8)]),
                        self.OURO_VELHO)
            tela.pintar(tela.circulo(borla, 2.2), self.OURO)

    def passadeira(self, tela):
        """A passadeira de veludo que escorre da almofada até o chão (as bordas ondulam por cima dos ratos), com a
        franja dourada e a ponta roída."""
        cx, topo = self.ASSENTO
        y0 = topo + 9
        esquerda = [v2(cx - 10 - k * 1.2 + math.sin(k * 1.7) * 1.6, y0 + k * 6) for k in range(10)]
        direita = [v2(cx + 10 + k * 1.2 + math.sin(k * 1.3 + 1) * 1.6, y0 + k * 6) for k in range(10)]
        ponta = [v2(cx + 22, 127), v2(cx + 12, 125), v2(cx + 2, 128), v2(cx - 10, 124), v2(cx - 22, 127)]
        pano = tela.poly(direita + ponta + esquerda[::-1])
        for k in range(3):
            pano &= ~tela.circulo((cx - 12 + k * 13, 127), 2.2)
        tela.pintar(pano, self.VELUDO.copia(desce=0.3))
        for k in (-1, 0, 1):                                            # dobras
            tela.chapado(tela.capsula(v2(cx + k * 6, y0 + 6), v2(cx + k * 10, 122), 0.6) & pano, (88, 14, 26))
        for x in range(cx - 20, cx + 21, 3):                            # franja dourada
            tela.chapado(tela.capsula(v2(x, 123), v2(x, 126), 0.5) & pano, (206, 156, 60))
