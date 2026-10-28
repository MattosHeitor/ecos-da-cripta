"""Criaturas de demonstração das forjas (prévia da Etapa 1). Viraram inimigos do jogo com nome próprio
em personagens/da_forja.py (ex.: LoboCarnicalDemo -> LoboCarnical)."""
import numpy as np

import math

from ..motor import Mat, metal, v2, lerp
from .. import texturas as T
from .partes import Asa, Cabeca, Cauda, Pata
from .animal import Quadrupede, Ave, Inseto
from .planta import Arvore, Cogumelo
from .monstro import ForjaMonstro

__all__ = ["LoboCarnicalDemo", "BesouroDemo", "CorvoDemo", "ArvoreFamintaDemo", "CogumeloDemo", "PenitenteDemo", "CarnicalDemo",
           "RatoDemo", "RatazanaDemo", "FormigaDemo", "VespaDemo", "MoscaDemo", "MariposaDemo"]


class LoboCarnicalDemo(Quadrupede):
    """Lobo sarnento e esfomeado: pelo falhado, costelas, cicatriz e baba de sangue."""
    nome = "demo_lobo_carnical"
    S = 62
    proporcao = (2.5, 1.3)
    pe = 0.53
    mat = Mat((92, 80, 70), 6, relevo=1.15, ruido=0.18, dither=0.4)
    mat_barriga = (156, 134, 112)
    crina = 1
    cabeca = Cabeca(tam=0.15, focinho=0.15, olho_cor=(255, 54, 30))
    pescoco = (0.19, -0.14)
    semente = 11

    def detalhes(self, tela, ctx, P, corpo):
        S, A, C, cima = self.S, P["A"], P["C"], P["cima"]
        for k in range(3):                                                     # costelas
            p = lerp(A, C, 0.55 + k * 0.1) - cima * (0.01 * S)
            pts = [p, p - cima * (0.05 * S) + v2(-0.015 * S, 0), p - cima * (0.1 * S) + v2(-0.01 * S, 0)]
            for a, b in zip(pts, pts[1:]):
                for x, y in T.bresenham(a, b):
                    if 0 <= x < tela.w and 0 <= y < tela.h and corpo[y, x]:
                        tela.cor[y, x] *= 0.72
                        if x + 1 < tela.w and corpo[y, x + 1]:
                            tela.cor[y, x + 1] = np.minimum(tela.cor[y, x + 1] * 1.15, 255)
        T.manchas(tela, corpo, A, (150, 104, 96), escala=4, quantidade=0.16, forca=0.75, semente=3)   # sarna
        ombro = lerp(A, C, 0.85)
        tela.traco(ombro + v2(-0.05 * S, -0.05 * S), ombro + v2(0.03 * S, 0.04 * S), (176, 150, 130), sobre=True)
        boca = self.ponta_da_boca(P) + v2(-0.05 * self.S, 0.03 * self.S)
        regiao = tela.circulo(boca, 0.05 * S) & corpo
        T.escorrer(tela, regiao, boca, (140, 20, 26), densidade=0.6, comp=4, fase=P["fase"], molhado=0.5, semente=4)


class BesouroDemo(Inseto):
    """Besouro de carapaça brilhante que abre os élitros e as asas para investir."""
    nome = "demo_besouro"
    S = 54
    mat = Mat((60, 44, 52), 6, relevo=1.3, especular=(220, 200, 240), dither=0.3)
    elitro = Mat((70, 40, 96), 7, relevo=1.6, especular=(235, 210, 255), dither=0.25)
    asa = Asa(envergadura=0.6, estilo="inseto")
    cabeca = Cabeca(estilo="inseto", tam=0.13, olho_cor=(255, 120, 40),
                    chifres=[(0.06, -0.03, 0.12, -0.6, -0.5, 0.025)])


class CorvoDemo(Ave):
    """Corvo carniceiro voando: penas negro-azuladas, olho vermelho e bico curvo."""
    nome = "demo_corvo"
    voa = True
    mat = Mat((44, 42, 58), 6, relevo=1.0, especular=(150, 160, 210), luz_hue=0.6)
    cabeca = Cabeca(estilo="ave", tam=0.11, focinho=0.1, olho_cor=(255, 40, 40), crista=True)
    asa = Asa(envergadura=0.7, estilo="penas")
    corpo_r = (0.22, 0.14)


class ArvoreFamintaDemo(Arvore):
    """Árvore faminta: olhos de brasa, boca de farpas, seiva acesa nas fendas e braços de raiz."""
    nome = "demo_arvore_faminta"
    bracos = ((0.48, 1, 0.55, 0.06), (0.55, -1, 0.5, 0.05))


class CogumeloDemo(Cogumelo):
    """Cogumelo pustulento: chapéu sangrento com pintas que brilham e nuvem de esporos."""
    nome = "demo_cogumelo"

class PenitenteDemo(ForjaMonstro):
    """Penitente deformado: corcunda, braço direito comprido, capuz vazio, armadura partida e correntes."""
    nome = "demo_penitente"
    H = 78
    corcunda = 0.09
    curvado = 0.5
    braco_longo = 1.25
    braco_grosso = (0.85, 1.35)
    magreza = 0.9
    pele = Mat((132, 116, 124), 6, relevo=1.0, ruido=0.18, satur=0.5)
    roupa = Mat((58, 40, 44), 5, desce=0.3, ruido=0.25, relevo=0.7)
    trapos = 6
    armadura = metal((104, 100, 106), ruido=0.25)
    rosto = "vazio"
    olho_cor = (255, 200, 120)
    correntes = 2
    escorre = (120, 12, 20)


class CarnicalDemo(ForjaMonstro):
    """Carniçal esquelético: costelas, cabeça grande, boca rasgada e garras compridas."""
    nome = "demo_carnical"
    H = 70
    curvado = 0.45
    braco_longo = 1.35
    cabeca_tam = 1.15
    magreza = 0.75
    pernas_comp = 0.9
    pele = Mat((150, 150, 128), 6, relevo=1.0, ruido=0.2, satur=0.4)
    rosto = "monstro"
    olho_cor = (200, 255, 120)
    aura_cor = (90, 140, 60)


# ============================================================
# Preparação para o Reino dos Ratos e os Insetos (docs/planos/): só parâmetros e peças da forja
# ============================================================

class RatoDemo(Quadrupede):
    """Rato de esgoto: corcunda, traseiro largo, cabeça de roedor e cauda fina e anelada."""
    nome = "demo_rato"
    S = 34
    proporcao = (2.9, 1.15)
    pe = 0.5
    mat = Mat((88, 76, 72), 6, relevo=1.1, ruido=0.25, dither=0.45)
    mat_barriga = (158, 140, 130)
    comprimento = 0.62
    altura_anca = 0.3
    altura_cernelha = 0.25
    arco = -0.1
    perfil = ((0.0, 0.17, 0.15), (0.5, 0.13, 0.12), (1.0, 0.1, 0.11))
    pescoco = (0.1, -0.03)
    pescoco_larg = (0.1, 0.08)
    cabeca_ang = 0.3
    pata_tras = Pata(comp=(0.13, 0.12, 0.07), grossura=(0.06, 0.04, 0.03, 0.025), joelho="frente", metatarso=0.4,
                     garra=(196, 140, 140))
    pata_frente = Pata(comp=(0.1, 0.1, 0.04), grossura=(0.045, 0.03, 0.022, 0.02), joelho="tras", metatarso=0.15,
                       garra=(196, 140, 140))
    cauda = Cauda(comp=0.95, grossura=(0.04, 0.03, 0.018, 0.008), segmentos=9, ang=math.pi - 0.15, curva=-0.5,
                  estilo="rato")
    cabeca = Cabeca(estilo="roedor", tam=0.16, focinho=0.12, orelha="redonda", orelha_dentro=(196, 112, 122),
                    olho_cor=(255, 40, 40), olho_brilho=False)
    semente = 21

    def movimento(self, ctx):
        """Bicho baixo: agacha menos (senão o corpo afunda no chão ao morrer)."""
        m = super().movimento(ctx)
        m["agacha"] *= 0.45
        return m


class RatazanaDemo(RatoDemo):
    """A mesma classe do rato com outros números: maior, mais escura, pelo eriçado e olho amarelo."""
    nome = "demo_ratazana"
    S = 52
    mat = Mat((62, 54, 56), 6, relevo=1.2, ruido=0.3, dither=0.45)
    crina = 1
    cabeca = Cabeca(estilo="roedor", tam=0.15, focinho=0.13, orelha="redonda", orelha_dentro=(170, 96, 106),
                    olho_cor=(255, 200, 40))
    semente = 22


class FormigaDemo(Inseto):
    """Formiga-soldado: cintura fina, cabeça grande de mandíbulas e carapaça vermelho-escura."""
    nome = "demo_formiga"
    S = 44
    mat = Mat((104, 34, 26), 6, relevo=1.3, especular=(255, 190, 160), dither=0.3)
    torax = (0.1, 0.065)
    abdomen = (0.17, 0.13)
    cintura = 0.05
    altura = 0.3
    cabeca = Cabeca(estilo="inseto", tam=0.17, olho_cor=(255, 230, 120))
    semente = 23


class VespaDemo(Inseto):
    """Vespa voando: abdômen listrado de preto, cintura fina, ferrão que estica no bote."""
    nome = "demo_vespa"
    S = 46
    proporcao = (2.4, 1.7)
    voa = True
    mat = Mat((210, 150, 40), 6, relevo=1.2, especular=(255, 240, 180), dither=0.3)
    torax = (0.1, 0.08)
    abdomen = (0.2, 0.12)
    abdomen_ang = -0.35
    cintura = 0.04
    listras = ((24, 16, 14), 3)
    ferrao = Mat((40, 28, 24), 5, relevo=1.2)
    asa = Asa(envergadura=0.55, estilo="inseto")
    cabeca = Cabeca(estilo="inseto", tam=0.13, olho_cor=(255, 60, 40))
    semente = 25


class MoscaDemo(Inseto):
    """Mosca da peste voando: corpo verde-metálico, olhos enormes vermelhos e antenas curtas de clava."""
    nome = "demo_mosca"
    S = 40
    proporcao = (2.2, 1.7)
    voa = True
    altura_voo = 0.75
    mat = Mat((40, 70, 52), 6, relevo=1.3, especular=(170, 255, 190), dither=0.3)
    torax = (0.12, 0.1)
    abdomen = (0.16, 0.12)
    abdomen_ang = -0.2
    asa = Asa(envergadura=0.5, estilo="inseto")
    mat_asa = Mat((200, 210, 190), 4, relevo=0.4)
    cabeca = Cabeca(estilo="inseto", tam=0.16, olho_cor=(255, 30, 30), antena="clava")
    aura_cor = (110, 150, 60)
    semente = 26


class MariposaDemo(Inseto):
    """Mariposa lunar voando: asas grandes e claras, corpo peludo e antenas de pluma."""
    nome = "demo_mariposa"
    S = 48
    proporcao = (2.4, 1.9)
    voa = True
    altura_voo = 0.85
    mat = Mat((150, 140, 120), 6, relevo=0.9, ruido=0.4, dither=0.5)
    torax = (0.1, 0.08)
    abdomen = (0.18, 0.1)
    abdomen_ang = -0.25
    asa = Asa(envergadura=0.75, estilo="mariposa")
    mat_asa = Mat((186, 184, 160), 6, relevo=0.5, ruido=0.4, dither=0.5)
    cabeca = Cabeca(estilo="inseto", tam=0.12, olho_cor=(150, 200, 255), antena="pluma")
    aura_cor = (170, 190, 255)
    semente = 27