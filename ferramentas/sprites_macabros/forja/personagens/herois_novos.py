"""Monge e Feiticeira (classes jogáveis da fase 3). Mesmo esqueleto humanoide dos outros heróis.

Os materiais vêm por kw (roupas.py faz as roupas das subclasses e as skins com outras cores).
"""
import math

from ..motor import Mat, metal, v2, lerp, dir_ang, norm
from ..humanoide import perna, braco, tronco, pescoco, cabeca_base, olho, manto, capa, cinto, quadro_tronco
from ..anim import Modelo
from .. import armas, fx
from .herois import PELE, PELE_PALIDA, COURO_ESC, MADEIRA, morte_extras, golpe_rastro


# ============================================================
# MONGE — careca, túnica açafrão de um ombro só, contas de oração; luta de mãos nuas
# ============================================================

class Monge(Modelo):
    nome = "monge"
    H = 74
    estilo = "garra"
    prop = dict(ombros=0.24, quadris=0.18)
    base = dict(braco_f=(0.9, 1.4), braco_b=(0.5, 1.6), pe_f=(-0.09, 0), pe_b=(0.1, 0))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "monge")
        self.tunica = kw.get("tunica", Mat((206, 120, 40), 6, desce=0.3, ruido=0.12))
        self.faixa = kw.get("faixa", Mat((120, 30, 30), 5, relevo=0.6))
        self.calca = kw.get("calca", Mat((150, 84, 34), 5, ruido=0.1))
        self.contas = kw.get("contas", Mat((96, 60, 40), 4, especular=(220, 180, 120)))
        self.aura = kw.get("aura")              # cor da aura (especializações)

    def desenhar(self, tela, ctx, J):
        H = self.H
        if self.aura is not None and ctx.anim != "morte":
            tela.brilho(J["pelvis"] + J["u"] * H * 0.25, H * 0.42, self.aura, 0.35 + 0.1 * math.sin(ctx.a))
        braco(tela, J, "b", PELE.escuro(1), PELE.escuro(1), punho=Mat((230, 220, 200), 4))
        perna(tela, J, "b", self.calca.escuro(1), None, grossura=1.05, pe_mat=PELE.escuro(1))
        perna(tela, J, "f", self.calca, None, grossura=1.05, pe_mat=PELE)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        tronco(tela, J, PELE, cintura=0.12, peito=0.18)
        # túnica: cobre o ombro de trás e desce em diagonal, saia até o joelho
        tunica = tela.poly(Q.pts([(-0.1 * H, T * 0.95), (-0.02 * H, T * 1.0), (0.09 * H, T * 0.35), (0.11 * H, -0.2 * H),
                                  (-0.11 * H, -0.2 * H)]))
        tela.pintar(tunica, self.tunica)
        tela.traco(Q.pt(-0.02 * H, T * 0.98), Q.pt(0.09 * H, T * 0.36), self.tunica[1], sobre=True)
        cinto(tela, J, self.faixa, altura=0.03, larg=0.03)
        # ponta da faixa caindo
        s = math.sin(ctx.a)
        ponta = Q.pt(0.06 * H, 0.0)
        tela.pintar(tela.corrente([ponta, ponta + v2(1 + s * 0.5, 6), ponta + v2(2 + s, 11)], [1.6, 1.4, 1.0]), self.faixa)
        pescoco(tela, J, PELE, 0.036)
        # colar de contas
        for k in range(7):
            t = k / 6
            p = lerp(J["ombro_b"], J["ombro_f"], 0.15 + t * 0.7) + J["u"] * (-2 - 3 * math.sin(t * math.pi))
            tela.pintar(tela.circulo(p, 1.1), self.contas)
        cab, C = cabeca_base(tela, J, PELE)
        h = J["P"]["cabeca"]
        w = h * 0.82
        tela.px(*C.pt(-w * 0.05, h * 0.38), PELE[5])                                   # brilho da careca
        for k in range(3):                                                             # marcas de voto na testa
            tela.px(*C.pt(w * (0.05 + k * 0.12), h * 0.3), (150, 60, 40))
        olho(tela, C, w * 0.36, h * 0.06, (30, 20, 16), emite=False)
        tela.traco(C.pt(w * 0.22, h * 0.16), C.pt(w * 0.46, h * 0.18), (60, 40, 30))  # sobrancelha
        tela.traco(C.pt(w * 0.3, -h * 0.28), C.pt(w * 0.46, -h * 0.26), (110, 60, 50))
        braco(tela, J, "f", PELE, PELE, punho=Mat((230, 220, 200), 4))
        # golpe: punho brilhando e rastro
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            cor = self.aura or (255, 230, 160)
            tela.brilho(J["mao_f"], 8, cor, 0.8)
            armas.faiscas(tela, J["mao_f"] + v2(4, 0), cor, n=5, raio=6, semente=ctx.i)
        golpe_rastro(tela, ctx, J, H * 0.45, -0.4, 0.6, cor=(255, 236, 200))
        morte_extras(tela, self, ctx, J)


# ============================================================
# FEITICEIRA — chapéu pontudo de aba larga, vestido longo, cabelo comprido e varinha torta
# ============================================================

class Feiticeira(Modelo):
    nome = "feiticeira"
    H = 74
    estilo = "magia"
    prop = dict(ombros=0.2, quadris=0.19)
    base = dict(braco_f=(0.7, 0.8), braco_b=(0.2, 0.7), arma_f=0.15, pe_f=(-0.06, 0), pe_b=(0.07, 0))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "feiticeira")
        self.vestido = kw.get("vestido", Mat((70, 34, 92), 6, desce=0.45, ruido=0.12, relevo=0.7, arredonda=0.6))
        self.chapeu = kw.get("chapeu", Mat((40, 26, 52), 6, relevo=0.8))
        self.cabelo = kw.get("cabelo", Mat((150, 40, 40), 5, ruido=0.5))
        self.magia = kw.get("magia", fx.FOGO_ROXO)
        self.fivela = kw.get("fivela", metal((200, 200, 214)))

    def desenhar(self, tela, ctx, J):
        H = self.H
        s = math.sin(ctx.a)
        # cabelo comprido atrás do corpo
        topo = J["cabeca"] + J["hu"] * 2
        cabelo = [topo + v2(-2, 0), topo + v2(-6, 8 + s * 0.5), topo + v2(-7, 18 + s), topo + v2(-5, 26 + s)]
        tela.pintar(tela.corrente(cabelo, [4.2, 4.0, 3.2, 1.6]), self.cabelo.escuro(1))
        capa(tela, J, self.vestido.escuro(2), comprimento=0.6, vento=0.03 * s, larg=0.13, rasgos=6, semente=81)
        self.manga(tela, J, "b", self.vestido.escuro(1))
        perna(tela, J, "b", COURO_ESC, COURO_ESC.escuro(1), cano=0.5)
        perna(tela, J, "f", COURO_ESC, COURO_ESC, cano=0.5)
        mm = manto(tela, J, self.vestido, folga=0.08, rasgos=7, semente=83, barra=-0.01)
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        corpete = tela.poly(Q.pts([(-0.06 * H, T * 0.85), (0.07 * H, T * 0.85), (0.08 * H, T * 0.15), (-0.06 * H, T * 0.15)]))
        tela.pintar(corpete & mm, self.vestido.escuro(1), linha_interna=False)
        for k in range(4):                                         # laço do corpete
            tela.px(*Q.pt(0.02 * H, T * (0.25 + k * 0.17)), (200, 190, 170))
        cinto(tela, J, COURO_ESC, fivela=self.fivela, altura=0.04)
        # amuleto de lua e frasquinhos no cinto
        tela.pintar(tela.circulo(Q.pt(-0.05 * H, 0.0), 1.6), Mat((120, 220, 120), 4))
        pescoco(tela, J, PELE_PALIDA, 0.03)
        tela.pintar(tela.circulo(J["pescoco"] - J["u"] * 3, 1.4), self.fivela)
        cab, C = cabeca_base(tela, J, PELE_PALIDA)
        h = J["P"]["cabeca"]
        w = h * 0.82
        # franja
        tela.pintar(tela.poly(C.pts([(-w * 0.55, h * 0.3), (w * 0.35, h * 0.42), (w * 0.15, h * 0.12), (-w * 0.5, -h * 0.2)])),
                    self.cabelo)
        olho(tela, C, w * 0.36, h * 0.04, (60, 200, 90), brilho=(60, 220, 100), emite=True)
        tela.traco(C.pt(w * 0.3, -h * 0.28), C.pt(w * 0.46, -h * 0.24), (120, 40, 60))     # sorriso torto
        # chapéu pontudo de aba larga, ponta caída para trás
        ang_aba = math.atan2(J["hu"][0], -J["hu"][1])
        aba = tela.elipse_girada(C.pt(w * 0.05, h * 0.42), w * 1.3, h * 0.17, ang_aba)
        cone = tela.poly(C.pts([(-w * 0.5, h * 0.42), (w * 0.5, h * 0.42), (w * 0.1, h * 1.2), (-w * 0.35 + s * 0.5, h * 1.75),
                                (-w * 0.9 + s, h * 1.65), (-w * 0.3, h * 1.1)]))
        tela.pintar(cone | aba, self.chapeu)
        tela.traco(C.pt(-w * 0.48, h * 0.55), C.pt(w * 0.48, h * 0.55), self.fivela[3], sobre=True)
        tela.pintar(tela.circulo(C.pt(w * 0.1, h * 0.55), 1.3), self.fivela)
        # varinha torta com uma lua
        mf = J["mao_f"]
        d = dir_ang(J["arma_f"])
        n = v2(-d[1], d[0])
        if self.armado:
            topo_v = armas.cajado(tela, mf, J["arma_f"], H * 0.3, MADEIRA, atras=H * 0.18, torto=1.6)
            lua = tela.circulo(topo_v + d * 3, 3.2) & ~tela.circulo(topo_v + d * 3 + n * 1.6, 2.6)
            tela.chapado(lua, self.magia[3], emite=True)
            tela.brilho(topo_v + d * 3, 7, self.magia[2], 0.5 + 0.15 * s)
        self.manga(tela, J, "f", self.vestido)
        if ctx.anim == "ataque" and ctx.i in (1, 2):
            c = J["mao_b"] + v2(6, -3)
            fx.orbe(tela, c, 3.6, self.magia)
            for k in range(3):
                fx.runa(tela, c + v2(6 + k * 5, -8 + k * 5), self.magia[3], 2, forma=k)
        elif self.armado and ctx.anim == "parado" and ctx.i == 1:
            tela.px(*(topo_v + d * 7 + n * 2), self.magia[4], emite=True)
        morte_extras(tela, self, ctx, J)

    def manga(self, tela, J, lado, mat):
        braco(tela, J, lado, mat, None, grossura=1.15)
        c, m = J["cotovelo_" + lado], J["mao_" + lado]
        d = norm(m - c)
        n = v2(-d[1], d[0])
        p0 = lerp(c, m, 0.4)
        tela.pintar(tela.poly([p0 + n * 1.8, m + n * 4.0 + d * 0.5, m - n * 4.0 + d * 1.5, p0 - n * 1.8]), mat)
        tela.pintar(tela.circulo(m + d * 1.2, self.H * 0.024), PELE_PALIDA)
