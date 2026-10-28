"""Forja 1: animais, insetos e semelhantes.

    ForjaAnimal   base: animação (movimento), ordem de desenho (método-modelo) e morte
      Quadrupede  coluna curva, peito/barriga em perfil, pescoço, 4 patas com IK, cauda, asas opcionais
      Ave         corpo oval, pescoço, bico, 2 pernas finas, asas de penas (pousada ou voando)
      Inseto      cabeça/tórax/abdômen, 3 ou 4 pares de patas com joelho alto, élitros ou asas
      Verme       corpo comprido que ondula (sanguessugas, serpentes; centopeias com patinhas)

Um bicho novo é uma subclasse que só troca medidas, materiais e peças (Pata, Cauda, Asa, Cabeca)
e, se quiser, desenha detalhes próprios em detalhes(). Medidas em frações de S (o tamanho dele).
"""
import math

import numpy as np

from ..motor import Mat, v2, lerp, girar, misturar
from ..humanoide import sangue_no_chao
from ..personagens.bestas import Besta
from .. import texturas as T
from .. import fx
from .partes import Pata, Cauda, Asa, Cabeca, direcao


def tabela(ctx, valores):
    """Valor do quadro atual numa lista por quadro (ex.: [antecipação, golpe, impacto, volta])."""
    return valores[min(ctx.i, len(valores) - 1)]


class ForjaAnimal(Besta):
    """Base dos animais. As subclasses definem montar() (pontos do corpo) e as etapas do desenho."""

    geo_rapida = True
    S = 60
    proporcao = (2.2, 1.25)          # célula (largura, altura) em S
    pe = 0.48                        # âncora (pés) em fração da largura
    mat = Mat((100, 84, 70), 6, relevo=1.1, ruido=0.3, dither=0.45)
    mat_barriga = None               # cor da barriga (contrassombra), ou None
    cobertura = "pelo"               # pelo | escamas | quitina | penas | liso
    sangue = ((70, 6, 14), (110, 14, 24))
    morte_fumaca = None              # cor: o corpo se desfaz em fumaça ao morrer (espectros)
    aura_cor = None                  # brilho em volta da silhueta
    espectral = None                 # opacidade do corpo (0..1) das criaturas fantasmagóricas
    cor_espectral = (150, 210, 255)  # contraluz e névoa dos espectros
    semente = 5

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * self.proporcao[0]), int(S * self.proporcao[1])
        self.ancora = (int(self.larg * self.pe), self.alt - 3)

    # ---------------- animação ----------------
    def movimento(self, ctx):
        """Números de cada quadro (frações de S e radianos). As subclasses podem ajustar."""
        m = dict(bob=0.0, avanco=0.0, agacha=0.0, incl=0.0, cab=0.0, boca=0.0, cauda=0.0, rabo=0.0, passo=0.0,
                 passo_tras=0.0, salto=0.0, deitado=0.0, abertura=None, bater=0.0, fase=ctx.a, i=ctx.i, anim=ctx.anim,
                 golpe=ctx.golpe, ferido=ctx.anim == "dano", morto=ctx.morto)
        if ctx.anim == "parado":
            s = tabela(ctx, [0, 0.5, 1, 0.5])
            m.update(bob=s * 0.012, cauda=0.8, cab=0.035 * s)
        elif ctx.anim == "ataque":
            m.update(avanco=tabela(ctx, [-0.06, 0.28, 0.32, 0.08]), agacha=tabela(ctx, [0.07, -0.02, 0.0, 0.02]),
                     incl=tabela(ctx, [0.07, -0.12, 0.04, 0.0]), cab=tabela(ctx, [0.28, -0.15, 0.3, 0.05]),
                     boca=tabela(ctx, [0.15, 1.0, 0.5, 0.1]), passo=tabela(ctx, [0.0, 0.2, 0.18, 0.04]),
                     salto=tabela(ctx, [0.0, 0.07, 0.01, 0.0]), rabo=tabela(ctx, [-0.25, 0.35, 0.2, 0.0]))
        elif ctx.anim == "dano":
            m.update(avanco=tabela(ctx, [-0.12, -0.05]), incl=tabela(ctx, [-0.1, -0.04]), cab=tabela(ctx, [-0.4, -0.15]),
                     boca=tabela(ctx, [0.6, 0.2]), agacha=tabela(ctx, [0.03, 0.01]), rabo=tabela(ctx, [-0.4, -0.2]))
        elif ctx.anim == "morte":
            m.update(avanco=tabela(ctx, [-0.04, -0.06, -0.08, -0.08]), agacha=tabela(ctx, [0.08, 0.2, 0.3, 0.32]),
                     cab=tabela(ctx, [0.3, 0.5, 0.55, 0.6]), boca=tabela(ctx, [0.45, 0.5, 0.3, 0.25]),
                     deitado=tabela(ctx, [0.0, 0.0, 0.75, 1.0]), incl=tabela(ctx, [0.05, 0.12, 0.05, 0.02]),
                     rabo=tabela(ctx, [-0.2, -0.4, -0.5, -0.55]))
        elif ctx.anim == "correr":                  # galope: só quem pede a linha extra (animacoes_extras = (("correr", 4),))
            m.update(passo=tabela(ctx, [0.14, 0.04, -0.08, 0.02]), passo_tras=tabela(ctx, [-0.08, 0.06, 0.12, 0.0]),
                     salto=tabela(ctx, [0.05, 0.08, 0.0, 0.02]), bob=tabela(ctx, [-0.02, -0.04, 0.0, -0.01]),
                     incl=tabela(ctx, [0.05, -0.04, -0.06, 0.02]), cauda=1.2, rabo=tabela(ctx, [0.1, -0.1, -0.15, 0.05]))
        return m

    def pose(self, ctx):
        return self.montar(self.movimento(ctx))

    def montar(self, m):
        raise NotImplementedError

    # ---------------- desenho (método-modelo) ----------------
    def desenhar(self, tela, ctx, P):
        """Ordem fixa: aura, partes de trás, corpo, detalhes, partes da frente, efeitos e morte."""
        self.atras(tela, ctx, P)
        corpo = self.corpo(tela, ctx, P)
        self.detalhes(tela, ctx, P, corpo)
        self.frente(tela, ctx, P)
        self.efeitos(tela, ctx, P)
        self.fim(tela, ctx, P)

    def atras(self, tela, ctx, P):
        """Asa e patas do lado de lá, cauda."""

    def corpo(self, tela, ctx, P):
        return np.zeros((tela.h, tela.w), bool)

    def detalhes(self, tela, ctx, P, corpo):
        """Cicatrizes, listras, costelas... (as subclasses desenham aqui)."""

    def frente(self, tela, ctx, P):
        """Patas e asa do lado de cá."""

    def efeitos(self, tela, ctx, P):
        """Partículas, brilhos, rastros de golpe."""

    def cobrir(self, tela, mask, ancora, ang=math.pi, semente=0):
        """Aplica a cobertura do animal (pelo, escamas, quitina, penas) numa máscara já pintada."""
        if self.cobertura == "pelo":
            T.pelagem(tela, mask, ancora, ang=ang, comp=3, densidade=0.32, semente=semente,
                      contraste=0.24 if self.espectral is None else 0.12)
        elif self.cobertura == "escamas":
            T.escamas(tela, mask, ancora, tam=3)
        elif self.cobertura == "quitina":
            T.quitina(tela, mask, ancora, eixo=direcao(ang + math.pi), espaco=5, brilho=0.4, semente=semente)
        elif self.cobertura == "penas":
            T.penas(tela, mask, ancora, eixo=direcao(ang), tam=3)

    def espectralizar(self, tela, ctx, P):
        """Corpo de espectro: contraluz colorida, pés que se desfazem em névoa e corpo translúcido."""
        S, cor = self.S, self.cor_espectral
        corpo = (tela.alfa > 0) & ~tela.emite
        ys, xs = np.nonzero(corpo)                                       # brilho próprio: puxa para o tom do espírito
        tela.cor[ys, xs] = np.clip(tela.cor[ys, xs] * 0.72 + np.array(cor, np.float32) * 0.38, 0, 255)
        for d in ((1, 0), (-1, 0), (0, -1)):
            T.luz_de_borda(tela, corpo, misturar(cor, (255, 255, 255), 0.4), d, forca=0.45)
        pes = corpo & (np.arange(tela.h)[:, None] > self.ancora[1] - 0.1 * S)
        T.esfumacar(tela, pes, P["centro"], cor=misturar(cor, (30, 40, 60), 0.5), fase=ctx.a, comeu=0.55, fiapos=0)
        T.aura(tela, tela.alfa > 0, cor, raio=4, forca=0.3, fase=ctx.a)
        T.particulas(tela, P["centro"], (0.35 * S, 0.12 * S), cor, n=7, fase=ctx.a, sobe=0.3 * S, semente=self.semente)
        corpo = (tela.alfa > 0) & ~tela.emite
        y = np.arange(tela.h, dtype=np.float32)[:, None] * np.ones((1, tela.w), np.float32)
        some = np.clip((y - (self.ancora[1] - 0.3 * S)) / (0.3 * S), 0, 1)        # some aos poucos perto do chão
        alfa = (255 * self.espectral * (1 - 0.55 * some)).astype(np.uint8)
        tela.alfa[corpo] = np.minimum(tela.alfa[corpo], alfa[corpo])
        tela.contorno_alfa = int(255 * min(1.0, self.espectral + 0.1))
        tela.contorno_cor = misturar(cor, (10, 10, 30), 0.8)

    def fim(self, tela, ctx, P):
        """Espectro, aura, poça de sangue ou fumaça na morte."""
        if self.espectral is not None:
            self.espectralizar(tela, ctx, P)
        if self.aura_cor is not None and not (ctx.anim == "morte" and ctx.i >= 2):
            T.aura(tela, tela.mascara(), self.aura_cor, raio=4, forca=0.45, fase=ctx.a)
        if ctx.anim != "morte" or ctx.i < 2:
            return
        cx, chao = P["centro"][0], self.ancora[1]
        if self.morte_fumaca is not None:
            fx.fumaca(tela, v2(cx, chao - 0.15 * self.S), 0.1 * self.S, cor=self.morte_fumaca, fase=ctx.a, n=6, sobe=10)
            if ctx.i == 3:
                T.esfumacar(tela, tela.mascara(), P["centro"], cor=self.morte_fumaca, fase=ctx.a, comeu=0.5)
        elif self.sangue is not None:
            sangue_no_chao(tela, cx, chao + 1, self.S * (0.22 if ctx.i == 2 else 0.4), *self.sangue)


# ============================================================
# QUADRÚPEDE
# ============================================================

class Quadrupede(ForjaAnimal):
    """Lobos, felinos, cães, ratos, lagartos... (e dragões, com asas)."""

    comprimento = 0.6                 # anca -> cernelha
    altura_anca = 0.44                # altura da coluna sobre o chão
    altura_cernelha = 0.48
    arco = -0.03                      # curva das costas (negativo = arqueada para cima)
    perfil = ((0.0, 0.12, 0.11), (0.45, 0.095, 0.095), (1.0, 0.13, 0.19))   # (t, raio de cima, raio de baixo)
    pescoco = (0.17, -0.15)           # da cernelha até a nuca
    pescoco_larg = (0.12, 0.075)
    cabeca_ang = 0.15
    crina = 0                         # comprimento extra do pelo no dorso e pescoço
    pe_tras_x = -0.02                 # pés em relação à anca/cernelha
    pe_frente_x = 0.07
    pata_tras = Pata(comp=(0.2, 0.19, 0.13), joelho="frente", metatarso=0.35)
    pata_frente = Pata(comp=(0.19, 0.18, 0.08), grossura=(0.06, 0.04, 0.03, 0.026), joelho="tras", metatarso=0.12)
    cauda = Cauda()
    cabeca = Cabeca()
    asa = None
    mat_asa = None

    def _perfil(self, t):
        ts = [p[0] for p in self.perfil]
        return (float(np.interp(t, ts, [p[1] for p in self.perfil])), float(np.interp(t, ts, [p[2] for p in self.perfil])))

    def montar(self, m):
        S = self.S
        cx0, chao = self.ancora
        cx = cx0 + m["avanco"] * S
        deit = m["deitado"]
        alt_a = self.altura_anca - m["agacha"]
        alt_c = self.altura_cernelha - m["agacha"]
        r_chao = self._perfil(0)[1] + 0.02                              # deitado: barriga no chão
        alt_a = alt_a * (1 - deit) + r_chao * deit
        alt_c = alt_c * (1 - deit) + (self._perfil(1)[1] * 0.8 + 0.02) * deit
        A = v2(cx - self.comprimento * S / 2, chao - alt_a * S + m["bob"] * S)
        C = girar(A + v2(self.comprimento * S, -(alt_c - alt_a) * S), m["incl"], A)
        d = (C - A) / (np.linalg.norm(C - A) or 1)
        cima = v2(d[1], -d[0])
        M = (A + C) / 2 - cima * (self.arco * S)
        espinha = [(1 - t) ** 2 * A + 2 * (1 - t) * t * M + t ** 2 * C for t in np.linspace(0, 1, 12)]
        P = dict(m, A=A, C=C, cima=cima, d=d, espinha=espinha, centro=(A + C) / 2)

        # pescoço e cabeça
        ang_cab = self.cabeca_ang + m["incl"] + m["cab"]
        nuca = C + girar(v2(self.pescoco[0] * S, self.pescoco[1] * S), m["incl"] + m["cab"] * 0.4)
        if deit:
            deitada = v2(C[0] + self.pescoco[0] * S * 1.2, chao - self.cabeca.tam * S * 0.55)
            nuca = lerp(nuca, deitada, deit)
            ang_cab = ang_cab * (1 - deit) + 0.3 * deit
        P["nuca"], P["ang_cab"] = nuca, ang_cab

        # patas: pés fixos no chão (o corpo é que se mexe), com passo/salto no bote
        x_anca0 = cx0 - self.comprimento * S / 2
        pe_t = v2(x_anca0 + self.pe_tras_x * S + m["avanco"] * S * 0.45 + m["passo_tras"] * S, chao - 1)
        pe_f = v2(x_anca0 + self.comprimento * S + self.pe_frente_x * S + (m["avanco"] * 0.95 + m["passo"]) * S,
                  chao - 1 - m["salto"] * S)
        if deit:                                                            # patas esticadas no chão
            pe_t = lerp(pe_t, v2(A[0] - self.pata_tras.alcance * 0.85 * S, chao - 2), deit)
            pe_f = lerp(pe_f, v2(C[0] + self.pata_frente.alcance * 0.85 * S, chao - 3), deit)
        raiz_t = A - cima * (self._perfil(0)[1] * 0.25)
        raiz_f = C - cima * (self._perfil(1)[1] * 0.15) - d * (0.02 * S)
        lado_la = v2(0.03 * S, -0.02 * S)
        P["patas"] = {
            "tras_la": self.pata_tras.juntas(raiz_t + lado_la, pe_t + v2(0.07 * S, 0), S),
            "frente_la": self.pata_frente.juntas(raiz_f + lado_la, pe_f + v2(-0.06 * S, 0), S),
            "tras": self.pata_tras.juntas(raiz_t, pe_t, S),
            "frente": self.pata_frente.juntas(raiz_f, pe_f, S),
        }
        if self.cauda is not None:
            base = A - d * (self._perfil(0)[0] * 0.7 * S) + cima * (self._perfil(0)[0] * 0.4 * S)
            P["cauda"] = self.cauda.pontos(base, S, m["cauda"], m["fase"], m["rabo"] + m["incl"])
        if self.asa is not None:
            raiz_asa = lerp(A, C, 0.7) + cima * (self._perfil(0.7)[0] * S * 0.8)
            abertura = 0.15 if m["abertura"] is None else m["abertura"]
            P["asa"] = self.asa.pontos(raiz_asa, S, abertura, m["bater"])
            P["asa_la"] = self.asa.pontos(raiz_asa + v2(0.05 * S, -0.02 * S), S, abertura, m["bater"] - 0.12)
        return P

    def atras(self, tela, ctx, P):
        S = self.S
        escuro = self.mat.escuro(1)
        if self.asa is not None:
            self.asa.desenhar(tela, P["asa_la"], (self.mat_asa or self.mat).escuro(1), S, self.semente + 1)
        for nome, pata in (("tras_la", self.pata_tras), ("frente_la", self.pata_frente)):
            pata.desenhar(tela, P["patas"][nome], escuro, S, self.semente + 2)
        if self.cauda is not None:
            self.cauda.desenhar(tela, P["cauda"], self.mat, S, self.semente + 3)

    def corpo(self, tela, ctx, P):
        S = self.S
        A, C, cima, d = P["A"], P["C"], P["cima"], P["d"]
        topo, base = [], []
        for t, p in zip(np.linspace(0, 1, len(P["espinha"])), P["espinha"]):
            rc, rb = self._perfil(t)
            topo.append(p + cima * (rc * S))
            base.append(p - cima * (rb * S))
        m = tela.poly(topo + base[::-1])
        rc0, rb0 = self._perfil(0)
        m |= tela.circulo(A + cima * ((rc0 - rb0) / 2 * S), (rc0 + rb0) / 2 * S)
        rc1, rb1 = self._perfil(1)
        m |= tela.elipse_girada(C + cima * ((rc1 - rb1) / 2 * S) + d * (0.02 * S), (rc1 + rb1) / 2 * S * 0.95,
                                (rc1 + rb1) / 2 * S, math.atan2(d[1], d[0]))
        m |= tela.capsula(C + cima * (rc1 * 0.3 * S), P["nuca"], self.pescoco_larg[0] * S, self.pescoco_larg[1] * S)
        if self.cobertura == "pelo":                                            # silhueta peluda
            m |= T.tufos(tela, m, A, (0, -1), comp=2.2 + self.crina, espaco=2, inclina=-0.85, semente=self.semente)
            m |= T.tufos(tela, m, A, (0, 1), comp=2, espaco=3, inclina=0.7, semente=self.semente + 1)
        m = tela.pintar(m, self.mat)
        if self.mat_barriga is not None:                                       # barriga mais clara
            baixo = [p - cima * (self._perfil(t)[1] * 0.25 * S) for t, p in zip(np.linspace(0, 1, 12), P["espinha"])]
            fundo = [p - cima * (self._perfil(t)[1] * 1.3 * S) for t, p in zip(np.linspace(0, 1, 12), P["espinha"])]
            regiao = tela.poly(baixo + fundo[::-1]) & m
            ys, xs = np.nonzero(regiao)
            T.misturar_cor(tela, ys, xs, self.mat_barriga, 0.38 + 0.12 * tela.bayer[ys, xs])
        self.cobrir(tela, m, A, ang=math.atan2(-d[1], -d[0]), semente=self.semente)
        cab =self.cabeca.desenhar(tela, P["nuca"], P["ang_cab"], self.S, self.mat, boca=P["boca"], morto=P["morto"],
                                   fase=P["fase"], semente=self.semente + 4)
        return m | cab

    def frente(self, tela, ctx, P):
        S = self.S
        for nome, pata in (("tras", self.pata_tras), ("frente", self.pata_frente)):
            pata.desenhar(tela, P["patas"][nome], self.mat, S, self.semente + 5)
        if self.asa is not None:
            self.asa.desenhar(tela, P["asa"], self.mat_asa or self.mat, S, self.semente + 6)

    def ponta_da_boca(self, P):
        return P["nuca"] + direcao(P["ang_cab"]) * ((self.cabeca.focinho + 0.08) * self.S)


# ============================================================
# AVE
# ============================================================

class Ave(ForjaAnimal):
    """Corvos, garças, abutres. voa=True: fica no ar batendo as asas (pernas encolhidas)."""

    S = 44
    proporcao = (2.0, 1.8)
    cobertura = "penas"
    voa = False
    altura = 0.42                     # centro do corpo sobre o chão (pousada)
    altura_voo = 0.75
    corpo_r = (0.2, 0.13)             # raios do corpo oval
    corpo_ang = -0.25                 # inclinação do corpo (negativo = peito para cima)
    pescoco_pts = ((0.06, -0.06), (0.1, -0.12))   # da frente do peito até a nuca (em S)
    pescoco_larg = (0.07, 0.05)
    cabeca = Cabeca(estilo="ave", tam=0.1, focinho=0.12, olho_cor=(230, 40, 40))
    pata = Pata(comp=(0.14, 0.16), grossura=(0.03, 0.018, 0.016), joelho="tras", estilo="ave", cobertura="escamas",
                garra=(40, 36, 36))
    asa = Asa(envergadura=0.85, estilo="penas")
    mat_perna = Mat((70, 64, 60), 5, relevo=0.8)
    cauda_comp = 0.22
    leque_cauda = True                # False = sem leque de penas (morcegos)
    mat_asa = None                    # Mat das asas (None = o do corpo)
    sangue = ((70, 6, 14), (110, 14, 24))

    def movimento(self, ctx):
        m = super().movimento(ctx)
        m["abertura"] = 0.0
        m["bater"] = -0.55
        if self.voa and ctx.anim in ("parado", "ataque", "dano"):
            m["abertura"] = tabela(ctx, [1.0, 0.55, 0.15, 0.55])
            m["bater"] = tabela(ctx, [-0.25, 0.1, 0.55, 0.1])
            m["bob"] = tabela(ctx, [0.03, 0.0, -0.03, 0.0]) if ctx.anim == "parado" else m["bob"]
        if ctx.anim == "ataque":
            m["incl"] = tabela(ctx, [-0.15, 0.25, 0.3, 0.05])
            m["cab"] = tabela(ctx, [-0.35, 0.45, 0.55, 0.1])
            if not self.voa:
                m["abertura"] = tabela(ctx, [0.55, 0.25, 0.1, 0.0])
                m["bater"] = tabela(ctx, [-0.2, -0.5, -0.55, -0.55])
        if ctx.anim == "morte":
            m["abertura"] = tabela(ctx, [0.7, 0.6, 0.45, 0.4])               # asa cai aberta no chão
            m["bater"] = tabela(ctx, [0.1, -0.3, -0.7, -0.8])
        return m

    def montar(self, m):
        S = self.S
        cx0, chao = self.ancora
        deit = m["deitado"]
        alt = (self.altura_voo if self.voa and not deit else self.altura) - m["agacha"] * 0.5
        alt = alt * (1 - deit) + (self.corpo_r[1] + 0.02) * deit
        if self.voa and m["anim"] == "morte":
            alt = lerp(v2(self.altura_voo, 0), v2(self.corpo_r[1] + 0.02, 0), min(1, m["i"] / 2.0))[0]
        centro = v2(cx0 + m["avanco"] * S, chao - alt * S + m["bob"] * S)
        ang = self.corpo_ang + m["incl"] + deit * 0.3
        f = direcao(ang)
        cima = v2(f[1], -f[0])
        P = dict(m, centro=centro, ang=ang, f=f, cima=cima)
        peito = centro + f * (self.corpo_r[0] * 0.75 * S) + cima * (self.corpo_r[1] * 0.35 * S)
        pts = [peito]
        for x, y in self.pescoco_pts:
            pts.append(peito + girar(v2(x * S, y * S), m["incl"] * 0.5 + m["cab"] * 0.6))
        if deit:
            pts[-1] = lerp(pts[-1], v2(peito[0] + 0.12 * S, chao - self.cabeca.tam * S * 0.5), deit)
        P["pescoco"] = pts
        P["nuca"] = pts[-1]
        P["ang_cab"] = 0.1 + m["cab"] * 0.8 + m["incl"] * 0.3 + deit * 0.4
        quadril = centro + cima * (-self.corpo_r[1] * 0.55 * S) + f * (-0.02 * S)
        if self.voa and not deit:
            pe = quadril + v2(-0.04 * S, 0.12 * S)
        else:
            pe = v2(quadril[0] + 0.02 * S, chao - 1)
            if deit:
                pe = lerp(pe, quadril + v2(0.15 * S, -0.02 * S), deit)
        P["pernas"] = {"la": self.pata.juntas(quadril + v2(0.03 * S, -0.01 * S), pe + v2(0.04 * S, 0), S),
                       "ca": self.pata.juntas(quadril, pe, S)}
        rabo = centro - f * (self.corpo_r[0] * 0.85 * S)
        P["cauda"] = [rabo + girar(-f * (self.cauda_comp * S), a) for a in (-0.35, -0.12, 0.12)]
        P["rabo_base"] = rabo
        raiz = centro + cima * (self.corpo_r[1] * 0.55 * S) + f * (0.05 * S)
        P["asa"] = self.asa.pontos(raiz, S, m["abertura"], m["bater"] + ang)
        P["asa_la"] = self.asa.pontos(raiz + v2(0.04 * S, -0.02 * S), S, m["abertura"], m["bater"] + ang - 0.15)
        return P

    def atras(self, tela, ctx, P):
        S = self.S
        if P["abertura"] > 0.3:
            self.asa.desenhar(tela, P["asa_la"], (self.mat_asa or self.mat).escuro(1), S, self.semente + 1)
        self.pata.desenhar(tela, P["pernas"]["la"], self.mat_perna.escuro(1), S)
        for k, ponta in enumerate(P["cauda"] if self.leque_cauda else []):        # leque da cauda
            tela.pintar(tela.capsula(P["rabo_base"], ponta, 0.05 * S, 0.035 * S), self.mat.escuro(k % 2))

    def corpo(self, tela, ctx, P):
        S = self.S
        m = tela.elipse_girada(P["centro"], self.corpo_r[0] * S, self.corpo_r[1] * S, P["ang"])
        larg = [self.pescoco_larg[0] * S] + [self.pescoco_larg[1] * S] * (len(P["pescoco"]) - 1)
        m |= tela.corrente(P["pescoco"], larg)
        m = tela.pintar(m, self.mat)
        if self.mat_barriga is not None:
            barriga = tela.elipse_girada(P["centro"] - P["cima"] * (self.corpo_r[1] * 0.45 * S), self.corpo_r[0] * S * 0.8,
                                         self.corpo_r[1] * S * 0.55, P["ang"]) & m
            ys, xs = np.nonzero(barriga)
            T.misturar_cor(tela, ys, xs, self.mat_barriga, 0.35)
        self.cobrir(tela, m, P["centro"], ang=P["ang"] + math.pi)
        cab = self.cabeca.desenhar(tela, P["nuca"], P["ang_cab"], S, self.mat, boca=P["boca"], morto=P["morto"],
                                   fase=P["fase"], semente=self.semente)
        return m | cab

    def frente(self, tela, ctx, P):
        self.pata.desenhar(tela, P["pernas"]["ca"], self.mat_perna, self.S)
        self.asa.desenhar(tela, P["asa"], self.mat_asa or self.mat, self.S, self.semente + 6)


# ============================================================
# INSETO
# ============================================================

class Inseto(ForjaAnimal):
    """Besouros, formigas, aranhas (pares=4), louva-a-deus... Morre de patas para cima.

    Opcionais (desligados por padrão): cintura (formigas e vespas), listras no abdômen, ferrão e
    voa=True (vespas, moscas, mariposas: paira no ar zumbindo, patas penduradas, cai ao morrer).
    """

    S = 56
    proporcao = (2.4, 1.4)
    cobertura = "quitina"
    sangue = ((40, 60, 18), (80, 110, 30))
    altura = 0.26
    torax = (0.11, 0.09)
    abdomen = (0.24, 0.16)
    abdomen_ang = -0.12
    pares = 3
    abertura_patas = 0.62             # quanto os pés se afastam do corpo (em S)
    pata = Pata(comp=(0.2, 0.24), grossura=(0.03, 0.022, 0.012), joelho="cima", estilo="inseto", cobertura="quitina")
    cabeca = Cabeca(estilo="inseto", tam=0.12, olho_cor=(255, 80, 40))
    elitro = None                     # Mat da carapaça que cobre o abdômen (besouros)
    asa = None
    mat_asa = Mat((190, 200, 210), 4, relevo=0.4)
    cintura = 0.0                     # pecíolo entre tórax e abdômen (em S): formigas e vespas
    listras = None                    # (cor, quantas) faixas atravessando o abdômen
    ferrao = None                     # Mat do ferrão na ponta do abdômen
    voa = False                       # paira no ar (precisa de asa)
    altura_voo = 0.7                  # altura do tórax quando voa (em S)

    def movimento(self, ctx):
        m = super().movimento(ctx)
        m["abertura"] = 0.0
        if ctx.anim == "ataque":
            m["salto"] = tabela(ctx, [0.04, 0.12, 0.08, 0.0])
            if self.asa is not None:
                m["abertura"] = tabela(ctx, [0.6, 1.0, 0.8, 0.2])
        if self.voa and ctx.anim in ("parado", "ataque", "dano"):                # zumbido: a asa vai e volta
            m["abertura"] = 1.0
            m["bater"] = tabela(ctx, [-0.45, 0.2, -0.45, 0.2])
            if ctx.anim == "parado":
                m["bob"] = tabela(ctx, [0.02, 0.0, -0.02, 0.0])
        elif self.voa and ctx.anim == "morte":
            m["abertura"] = tabela(ctx, [1.0, 0.7, 0.3, 0.2])
        return m

    def montar(self, m):
        S = self.S
        cx0, chao = self.ancora
        deit = m["deitado"]
        alt_base = self.altura_voo if self.voa else self.altura
        if self.voa and m["anim"] == "morte":                                   # despenca até o chão
            alt_base = self.altura_voo + (self.altura - self.altura_voo) * min(1.0, m["i"] / 2.0)
        alt = (alt_base - m["agacha"] * 0.5) * (1 - deit) + (self.abdomen[1] + 0.01) * deit
        tor = v2(cx0 + m["avanco"] * S, chao - alt * S + m["bob"] * S)
        ang = m["incl"] * 0.6
        P = dict(m, torax=tor, centro=tor, ang=ang)
        P["abdomen"] = tor + girar(v2(-(self.torax[0] + self.abdomen[0] * 0.85 + self.cintura) * S, -0.02 * S), ang)
        P["nuca"] = tor + girar(v2(self.torax[0] * 0.8 * S, -0.01 * S), ang)
        P["ang_cab"] = 0.35 + m["cab"] * 0.7 + ang
        patas = {}
        for lado, dx_la in (("la", 0.05), ("ca", 0.0)):
            for j in range(self.pares):
                frac = j / max(1, self.pares - 1) - 0.5
                raiz = tor + v2((frac * self.torax[0] * 1.2 + dx_la) * S, self.torax[1] * 0.4 * S)
                x_pe = raiz[0] + frac * self.abertura_patas * S + (0.04 if lado == "la" else 0) * S
                alterna = (j + (lado == "la")) % 2
                y_pe = chao - 1 - (m["bob"] * S * 3 if alterna else 0)
                if m["golpe"] and j == self.pares - 1:                          # pata da frente ergue no bote
                    y_pe -= m["salto"] * S * 2.5
                    x_pe += 0.04 * S
                pe = v2(x_pe, y_pe)
                if self.voa:                                                    # no ar: patas dobradas para trás
                    pe = raiz + v2((frac * 0.08 - 0.1 - (0.02 if lado == "la" else 0)) * S, self.pata.alcance * 0.5 * S)
                    if m["golpe"] and j == self.pares - 1:
                        pe = pe + v2(0.16 * S, -0.04 * S)
                if deit:                                                        # patas encolhidas para cima
                    pe = lerp(pe, raiz + v2(frac * 0.1 * S, -0.16 * S), deit)
                patas[f"{lado}{j}"] = self.pata.juntas(raiz, pe, S)
        P["patas"] = patas
        if self.asa is not None:
            raiz = tor + v2(-0.02 * S, -self.torax[1] * 0.8 * S)
            P["asa"] = self.asa.pontos(raiz, S, m["abertura"], m["bater"] - 0.3)
            if self.voa:                                                        # a asa do lado de lá
                P["asa_la"] = self.asa.pontos(raiz + v2(0.03 * S, -0.01 * S), S, m["abertura"], m["bater"] - 0.5)
        return P

    def atras(self, tela, ctx, P):
        if self.voa and self.asa is not None and P["abertura"] > 0.05:
            self.asa.desenhar(tela, P["asa_la"], self.mat_asa.escuro(1), self.S)
        for j in range(self.pares):
            self.pata.desenhar(tela, P["patas"][f"la{j}"], self.mat.escuro(2), self.S)

    def eixo_do_abdomen(self, P):
        """Direção do abdômen para a FRENTE (da ponta até o tórax)."""
        return direcao(self.abdomen_ang + P["ang"])

    def desenhar_ferrao(self, tela, P):
        """Ferrão curvo na ponta do abdômen; estica no bote."""
        S, eixo = self.S, self.eixo_do_abdomen(P)
        base = P["abdomen"] - eixo * (self.abdomen[0] * S * 0.95)
        comp = (0.13 + (0.05 if P["golpe"] else 0.0)) * S
        meio = base - eixo * (comp * 0.55) + v2(0, comp * 0.12)
        ponta = base - eixo * comp + v2(0, comp * 0.4)
        tela.pintar(tela.corrente([base, meio, ponta], [0.03 * S, 0.016 * S, 0.5]), self.ferrao)

    def pintar_listras(self, tela, P, abdomen):
        """Faixas escuras atravessando o abdômen (vespas, abelhas), por cima do sombreamento."""
        cor, n = self.listras
        S, eixo = self.S, self.eixo_do_abdomen(P)
        normal = v2(-eixo[1], eixo[0])
        meia = self.abdomen[0] * S / (2 * n + 1) * 0.5                     # metade da largura de uma faixa
        for j in range(n):
            t = -1 + (2 * j + 1.5) / (2 * n + 1) * 2                        # faixas alternadas ao longo do abdômen
            c = P["abdomen"] + eixo * (t * self.abdomen[0] * S)
            alto = normal * (self.abdomen[1] * S * 1.3)
            faixa = tela.poly([c - eixo * meia - alto, c + eixo * meia - alto, c + eixo * meia + alto, c - eixo * meia + alto])
            tela.tingir(faixa & abdomen, cor, 0.85)

    def corpo(self, tela, ctx, P):
        S = self.S
        if self.ferrao is not None:
            self.desenhar_ferrao(tela, P)
        ab = tela.elipse_girada(P["abdomen"], self.abdomen[0] * S, self.abdomen[1] * S, self.abdomen_ang + P["ang"])
        m = tela.pintar(ab, self.mat)
        T.quitina(tela, m, P["abdomen"], eixo=direcao(P["ang"]), espaco=4, brilho=0.35)
        if self.listras is not None:
            self.pintar_listras(tela, P, m)
        if self.cintura > 0:                                                    # pecíolo fino até o tórax
            frente = P["abdomen"] + self.eixo_do_abdomen(P) * (self.abdomen[0] * S * 0.8)
            tras = P["torax"] - girar(v2(self.torax[0] * S * 0.7, 0), P["ang"])
            m |= tela.pintar(tela.capsula(frente, tras, 0.035 * S, 0.03 * S), self.mat)
        if self.elitro is not None:                                             # carapaça dos besouros
            el = tela.elipse_girada(P["abdomen"] + v2(0, -0.03 * S), self.abdomen[0] * S * 1.02, self.abdomen[1] * S * 0.85,
                                    self.abdomen_ang + P["ang"]) & ~tela.elipse_girada(
                P["abdomen"] + v2(0, self.abdomen[1] * S * 0.9), self.abdomen[0] * S * 1.2, self.abdomen[1] * S * 0.55, P["ang"])
            if P["abertura"] > 0.1:
                el = el & ~tela.poly([P["torax"], P["abdomen"] + v2(-self.abdomen[0] * S * 1.2, -self.abdomen[1] * S * 2),
                                      P["torax"] + v2(0, -S)])
            me = tela.pintar(el, self.elitro)
            T.quitina(tela, me, P["abdomen"], eixo=(0, 1), espaco=7, brilho=0.55, poros=0.06)
            costura = [P["abdomen"] + v2(self.abdomen[0] * S * 0.9, -self.abdomen[1] * S * 0.7),
                       P["abdomen"] + v2(-self.abdomen[0] * S * 0.9, -self.abdomen[1] * S * 0.45)]
            tela.traco(*costura, self.elitro[0], sobre=True)
            m |= me
        if self.asa is not None and P["abertura"] > 0.05:
            self.asa.desenhar(tela, P["asa"], self.mat_asa, S)
        tor = tela.pintar(tela.elipse_girada(P["torax"], self.torax[0] * S, self.torax[1] * S, P["ang"] - 0.1), self.mat)
        T.quitina(tela, tor, P["torax"], eixo=(1, 0), espaco=5, brilho=0.4)
        cab = self.cabeca.desenhar(tela, P["nuca"], P["ang_cab"], S, self.mat, boca=P["boca"], morto=P["morto"],
                                   fase=P["fase"])
        return m | tor | cab

    def frente(self, tela, ctx, P):
        for j in range(self.pares):
            self.pata.desenhar(tela, P["patas"][f"ca{j}"], self.mat, self.S)


# ============================================================
# VERME (sem patas ou com muitas patinhas)
# ============================================================

class Verme(ForjaAnimal):
    """Sanguessugas, vermes, serpentes e centopeias: um corpo comprido que ondula pelo chão.

    A espinha vai da cauda (t = 0, atrás) até a cabeça (t = 1, na frente). No bote a frente do
    corpo se ergue; na morte o corpo para de ondular e se encolhe no chão.
    """

    S = 56
    proporcao = (2.3, 1.2)
    pe = 0.45
    cobertura = "liso"
    comprimento = 1.1                 # em S
    segmentos = 14
    raio = ((0.0, 0.04), (0.3, 0.1), (0.75, 0.12), (1.0, 0.09))   # (t, raio em S)
    ondas = 1.2                       # quantas ondas cabem no corpo
    amplitude = 0.03
    ergue = 0.0                       # quanto a frente fica erguida parada (0..1)
    altura_bote = 0.45                # quanto a frente sobe no bote (em S)

    def _raio(self, t):
        ts = [r[0] for r in self.raio]
        return float(np.interp(t, ts, [r[1] for r in self.raio]))

    def movimento(self, ctx):
        m = super().movimento(ctx)
        m["ergue"] = self.ergue
        m["onda"] = 1.0
        if ctx.anim == "ataque":
            m["ergue"] = tabela(ctx, [self.ergue + 0.25, 1.0, 0.75, self.ergue + 0.15])
        elif ctx.anim == "dano":
            m["ergue"] = tabela(ctx, [self.ergue + 0.35, self.ergue + 0.15])
        elif ctx.anim == "morte":
            m["ergue"] = tabela(ctx, [self.ergue + 0.3, 0.1, 0.0, 0.0])
            m["onda"] = tabela(ctx, [0.8, 0.5, 0.2, 0.0])
        return m

    def montar(self, m):
        S = self.S
        cx, chao = self.ancora
        n = self.segmentos
        comp = self.comprimento * S
        x0 = cx - comp * 0.55 + m["avanco"] * S
        pts = []
        for k in range(n + 1):
            t = k / n
            x = x0 + t * comp
            r = self._raio(t) * S * (1 - 0.2 * m["deitado"])
            onda = math.sin(t * self.ondas * 2 * math.pi - m["fase"]) * self.amplitude * S * m["onda"]
            frente = max(0.0, (t - 0.55) / 0.45)
            sobe = frente ** 2 * m["ergue"] * self.altura_bote * S
            x -= frente ** 2 * m["ergue"] * 0.12 * S                       # a frente recua um pouco ao se erguer
            pts.append(v2(x, chao - r - 1 + onda - sobe + m["bob"] * S * 0.5))
        d = pts[-1] - pts[-2]
        P = dict(m, espinha=pts, centro=pts[n // 2], cabeca=pts[-1], ang_cab=math.atan2(d[1], d[0]))
        return P

    def larguras(self, P):
        n = len(P["espinha"]) - 1
        return [self._raio(k / n) * self.S * (1 - 0.2 * P["deitado"]) for k in range(n + 1)]

    def corpo(self, tela, ctx, P):
        larg = self.larguras(P)
        m = tela.corrente(P["espinha"], larg)
        m = tela.pintar(m, self.mat)
        if self.mat_barriga is not None:                                    # barriga: metade de baixo
            baixo = [p + v2(0, r * 0.35) for p, r in zip(P["espinha"], larg)]
            fundo = [p + v2(0, r * 1.4) for p, r in zip(P["espinha"], larg)]
            ys, xs = np.nonzero(tela.poly(baixo + fundo[::-1]) & m)
            T.misturar_cor(tela, ys, xs, self.mat_barriga, 0.4)
        self.cobrir(tela, m, P["espinha"][0], ang=P["ang_cab"] + math.pi)
        self.aneis(tela, P, m)
        return m | self.boca(tela, ctx, P)

    def aneis(self, tela, P, m):
        """Anéis/segmentos atravessando o corpo (as subclasses mudam)."""
        for a, b, r in zip(P["espinha"], P["espinha"][1:], self.larguras(P)):
            d = b - a
            n = v2(-d[1], d[0]) / (np.linalg.norm(d) or 1)
            c = lerp(a, b, 0.5)
            tela.traco(c - n * r, c + n * r, self.mat[1], sobre=True)

    def boca(self, tela, ctx, P):
        """Cabeça/boca na frente da espinha (as subclasses desenham)."""
        return np.zeros((tela.h, tela.w), bool)
