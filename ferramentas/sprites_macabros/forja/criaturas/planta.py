"""Forja 2: plantas e fungos.

    ForjaPlanta   base: tronco/caule retorcido, raízes no chão, rosto (olhos fundos e boca de
                  farpas), braços de raiz, casca/musgo/seiva brilhante e a animação
      Arvore      galhos que se ramificam (gerados uma vez, iguais em todos os quadros), folhas,
                  cipós pendurados
      Cogumelo    chapéu com lamelas, pintas que brilham, anel no caule e nuvem de esporos

Os galhos e raízes são sorteados com a semente da criatura no __init__ e só balançam a cada
quadro, então a silhueta é estável na animação.
"""
import math
import random

import numpy as np

from ..motor import Mat, v2, lerp, misturar
from ..personagens.bestas import Besta
from .. import texturas as T
from .. import fx
from .partes import direcao, Local

CASCA = Mat((88, 62, 48), 6, relevo=1.25, ruido=0.2, dither=0.4)
DENTE_DE_FARPA = Mat((196, 176, 140), 5, relevo=1.0)
GARGANTA = (34, 6, 10)


def ponto_na_linha(pts, t):
    """Ponto a uma fração t (0..1) do comprimento de uma polilinha, e a direção ali."""
    comp = [float(np.linalg.norm(b - a)) for a, b in zip(pts, pts[1:])]
    alvo = max(0.0, min(1.0, t)) * (sum(comp) or 1)
    for (a, b), c in zip(zip(pts, pts[1:]), comp):
        if alvo <= c:
            d = (b - a) / (c or 1)
            return a + d * alvo, d
        alvo -= c
    return pts[-1], (pts[-1] - pts[-2]) / (np.linalg.norm(pts[-1] - pts[-2]) or 1)


class ForjaPlanta(Besta):
    """Base das plantas: tronco, raízes, rosto, braços e animação de balanço/bote/murchar."""

    geo_rapida = True
    S = 72
    proporcao = (2.3, 1.9)
    pe = 0.42
    semente = 21
    # tronco
    altura = 1.05                     # em S
    larg_base, larg_topo = 0.42, 0.22
    torcao = 0.06                     # ondulação lateral do tronco
    nos = 3                           # nós na casca
    mat_tronco = CASCA
    casca = True                      # textura de casca (False = caule liso)
    musgo = (62, 84, 40)              # cor do musgo, ou None
    seiva = (230, 60, 40)             # rachaduras brilhantes, ou None
    espinhos = 0                      # quantos espinhos brotam dos lados do tronco
    mat_espinho = Mat((200, 180, 150), 5, relevo=1.1)
    # raízes
    n_raizes = 5
    raiz_comp = 0.55
    # rosto (None = sem rosto)
    rosto_t = 0.62                    # altura do rosto no tronco (0..1)
    olho_cor = (255, 190, 60)
    olho_tam = 0.07
    boca_larg = 0.2
    # braços de raiz: (t no tronco, lado 1 = da frente / -1 = de trás, comprimento, grossura[, ângulo de repouso])
    bracos = ()
    mat_braco = None

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * self.proporcao[0]), int(S * self.proporcao[1])
        self.ancora = (int(self.larg * self.pe), self.alt - 3)
        rng = random.Random(self.semente)
        self.raizes = [dict(lado=(-1 if k % 2 else 1), comp=self.raiz_comp * rng.uniform(0.55, 1.0),
                            arco=rng.uniform(0.02, 0.06), fase=rng.uniform(0, 6.3), x=rng.uniform(-0.4, 0.4))
                       for k in range(self.n_raizes)]
        self.gerar()

    def gerar(self):
        """Sorteia as partes fixas da planta (as subclasses acrescentam galhos, chapéu...)."""

    # ---------------- animação ----------------
    def movimento(self, ctx):
        i = ctx.i
        m = dict(balanco=math.sin(ctx.a), inclina=0.0, boca=0.12, chicote=0.0, queda=0.0, afunda=0.0,
                 fase=ctx.a, i=i, anim=ctx.anim, golpe=ctx.golpe, ferido=ctx.anim == "dano", morto=ctx.morto)
        if ctx.anim == "parado":
            m.update(inclina=0.025 * math.sin(ctx.a), boca=0.1 + 0.06 * (1 + math.sin(ctx.a)) / 2)
        elif ctx.anim == "ataque":
            m.update(inclina=[-0.09, 0.2, 0.16, 0.04][i], boca=[0.35, 1.0, 0.7, 0.2][i], chicote=[-0.3, 1.0, 0.8, 0.15][i],
                     balanco=[-1, 1, 0.8, 0.2][i])
        elif ctx.anim == "dano":
            m.update(inclina=[-0.12, -0.05][i], boca=[0.8, 0.4][i], balanco=[-1.2, -0.5][i])
        elif ctx.anim == "morte":
            q = [0.15, 0.4, 0.75, 1.0][i]
            m.update(queda=q, inclina=-0.4 * q, boca=[0.9, 0.7, 0.5, 0.45][i], afunda=0.3 * q, balanco=-q)
        return m

    def pose(self, ctx):
        return self.montar(self.movimento(ctx))

    def montar(self, m):
        S = self.S
        cx, chao = self.ancora
        rng = random.Random(self.semente)
        fase0 = rng.uniform(0, 6.3)
        altura = self.altura * (1 - m["afunda"]) * S
        espinha = []
        for t in np.linspace(0, 1, 14):
            x = math.sin(t * math.pi * 1.4 + fase0) * self.torcao * S
            dobra = math.sin(m["inclina"] * t * 1.6) * altura * t * 0.9
            espinha.append(v2(cx + x + dobra, chao - altura * t * math.cos(m["inclina"] * t)))
        P = dict(m, espinha=espinha, centro=espinha[len(espinha) // 2])
        P["bracos"] = [self.pontos_do_braco(b, P) for b in self.bracos]
        return P

    def largura(self, t):
        bojo = 1 + 0.1 * math.sin(t * 9 + self.semente) + (0.45 * (1 - t / 0.15) if t < 0.15 else 0)
        return (self.larg_base + (self.larg_topo - self.larg_base) * t) * bojo * self.S

    # ---------------- desenho ----------------
    def desenhar(self, tela, ctx, P):
        """Método-modelo: raízes, partes de trás, tronco, rosto, partes da frente, efeitos e morte."""
        self.raizes_no_chao(tela, P)
        self.atras(tela, ctx, P)
        tronco = self.tronco(tela, P)
        if self.rosto_t is not None:
            self.rosto(tela, P, tronco)
        self.frente(tela, ctx, P)
        self.efeitos(tela, ctx, P)
        self.murchar(tela, P)

    def atras(self, tela, ctx, P):
        for b, pts in zip(self.bracos, P["bracos"]):
            if b[1] < 0:
                self.desenhar_braco(tela, pts, b, (self.mat_braco or self.mat_tronco).escuro(1))

    def frente(self, tela, ctx, P):
        for b, pts in zip(self.bracos, P["bracos"]):
            if b[1] > 0:
                self.desenhar_braco(tela, pts, b, self.mat_braco or self.mat_tronco)

    def efeitos(self, tela, ctx, P):
        """Esporos, folhas caindo... (subclasses)."""

    def tronco(self, tela, P):
        S = self.S
        esq, dir_ = [], []
        for t, p in zip(np.linspace(0, 1, len(P["espinha"])), P["espinha"]):
            _, d = ponto_na_linha(P["espinha"], t)
            n = v2(-d[1], d[0])
            w = self.largura(t) / 2
            esq.append(p + n * w)
            dir_.append(p - n * w)
        m = tela.poly(esq + dir_[::-1])
        m |= tela.elipse(P["espinha"][-1][0], P["espinha"][-1][1], self.largura(1) / 2, self.largura(1) * 0.3)
        m = tela.pintar(m, self.mat_tronco)
        base = P["espinha"][0]
        if self.casca:
            T.casca(tela, m, base, eixo=P["espinha"][-1] - base, espaco=4, ondula=1.6, semente=self.semente)
        else:
            T.casca(tela, m, base, eixo=P["espinha"][-1] - base, espaco=6, ondula=0.6, escurece=0.85, clareia=1.05,
                    fendas=0.0, semente=self.semente)
        rng = random.Random(self.semente + 1)
        for _ in range(self.nos):
            t = rng.uniform(0.15, 0.85)
            if self.rosto_t is not None and abs(t - self.rosto_t) < 0.2:
                continue
            p, d = ponto_na_linha(P["espinha"], t)
            c = p + v2(-d[1], d[0]) * (self.largura(t) * rng.uniform(-0.3, 0.3))
            T.no_da_madeira(tela, c, S * 0.035, S * 0.05)
        for k in range(self.espinhos):                                      # espinhos curvos
            t = rng.uniform(0.12, 0.92)
            lado = 1 if k % 2 else -1
            p, d = ponto_na_linha(P["espinha"], t)
            n = v2(-d[1], d[0]) * lado
            raiz = p + n * (self.largura(t) * 0.45)
            ponta = raiz + n * (S * rng.uniform(0.06, 0.1)) + d * (S * 0.05)
            larg = v2(d) * (S * 0.025)
            tela.pintar(tela.poly([raiz - larg, raiz + larg, ponta]), self.mat_espinho)
        if self.musgo is not None:
            T.musgo(tela, m, base, cor=self.musgo, alcance=2, quantidade=0.45, semente=self.semente)
            T.manchas(tela, m, base, misturar(self.musgo, (20, 20, 10), 0.3), escala=5, quantidade=0.12, forca=0.6)
        if self.seiva is not None and not P["morto"]:
            T.rachaduras(tela, m, P["espinha"][4], area=(self.largura(0.3) * 0.3, S * 0.18), n=3, passos=5, cor=self.seiva,
                         semente=self.semente, brilho=0.35 * (1 - P["queda"]))
        return m

    def raizes_no_chao(self, tela, P):
        S = self.S
        chao = self.ancora[1]
        base = P["espinha"][0]
        for r in self.raizes:
            lado = r["lado"]
            ini = v2(base[0] + lado * self.largura(0) * 0.3 + r["x"] * S * 0.2, chao - S * 0.05)
            fim = v2(ini[0] + lado * r["comp"] * S, chao - 1 + math.sin(P["fase"] + r["fase"]) * 0.6)
            meio = lerp(ini, fim, 0.45) + v2(0, -r["arco"] * S)
            pts = [ini, meio, lerp(meio, fim, 0.6) + v2(0, -r["arco"] * S * 0.3), fim]
            mask = tela.corrente(pts, [S * 0.07, S * 0.045, S * 0.025, S * 0.008])
            mask &= tela.poly([v2(0, 0), v2(tela.w, 0), v2(tela.w, chao), v2(0, chao)])
            m = tela.pintar(mask, self.mat_tronco.escuro(1))
            T.casca(tela, m, ini, eixo=fim - ini, espaco=3, ondula=0.8, semente=self.semente + 9)

    # ---------------- braços de raiz ----------------
    def pontos_do_braco(self, b, P):
        S = self.S
        t, lado, comp = b[:3]
        ombro, d = ponto_na_linha(P["espinha"], t)
        ombro = ombro + v2(-d[1], d[0]) * (-lado * self.largura(t) * 0.3)
        repouso = b[4] if len(b) > 4 else (0.9 if lado > 0 else 1.9)        # para baixo e à frente / para trás
        golpe = -0.25
        ang = repouso + (golpe - repouso) * max(0.0, P["chicote"]) + 0.12 * P["balanco"] + P["queda"] * 0.6
        if P["chicote"] < 0:
            ang += P["chicote"] * -0.9
        pts = [ombro]
        a = ang
        for k in range(4):
            a += (0.35 - 0.6 * max(0.0, P["chicote"])) * (1 if k % 2 else -0.6)
            pts.append(pts[-1] + direcao(a) * (comp * S / 4))
        return pts

    def desenhar_braco(self, tela, pts, b, mat):
        S = self.S
        g = b[3] * S
        m = tela.pintar(tela.corrente(pts, [g, g * 0.8, g * 0.6, g * 0.45, g * 0.35]), mat)
        T.casca(tela, m, pts[0], eixo=pts[-1] - pts[0], espaco=3, ondula=0.8, semente=self.semente + 5)
        d = pts[-1] - pts[-2]
        ang = math.atan2(d[1], d[0])
        for k in (-0.6, 0.0, 0.55):                          # dedos de graveto
            ponta = pts[-1] + direcao(ang + k) * (S * 0.09)
            dobra = lerp(pts[-1], ponta, 0.6) + direcao(ang + k + 1.2) * 1.5
            tela.pintar(tela.corrente([pts[-1], dobra, ponta], [g * 0.35, g * 0.22, 0.5]), mat)

    # ---------------- rosto ----------------
    def rosto(self, tela, P, tronco):
        """Olhos fundos que brilham e uma boca enorme cheia de farpas, entalhados no tronco."""
        S = self.S
        p, d = ponto_na_linha(P["espinha"], self.rosto_t)
        frente = v2(-d[1], d[0]) * -1
        if frente[0] < 0:
            frente = -frente
        w = self.largura(self.rosto_t)
        centro = p + frente * (w * 0.12)
        L = Local(centro, math.atan2(d[1], d[0]) + math.pi / 2, S)
        vivo = not P["morto"] and P["queda"] < 0.7
        r = self.olho_tam
        P["rosto_pos"] = dict(olhos=[], vivo=vivo)               # onde ficou cada coisa (para as subclasses)
        for x, esc in ((-0.85, 0.8), (0.75, 1.0)):            # olho de lá menor (3/4); x em raios de olho
            c = L(x * r * 1.25, -0.05)
            P["rosto_pos"]["olhos"].append((c, r * S * esc))
            rx, ry = r * S * esc, r * S * esc * 0.72
            jag = [c + v2(math.cos(a) * rx * (0.85 + 0.25 * math.sin(a * 5 + x * 9)),
                          math.sin(a) * ry * (0.85 + 0.25 * math.cos(a * 4 + x * 7))) for a in np.linspace(0, 2 * math.pi, 14)[:-1]]
            tela.chapado(tela.poly(jag), (14, 6, 10))
            sobrancelha = [c + v2(-rx * 1.2, -ry * (1.4 if x > 0 else 1.0)), c + v2(rx * 1.1, -ry * (0.9 if x > 0 else 1.4))]
            tela.pintar(tela.capsula(*sobrancelha, S * 0.022 * esc, S * 0.016 * esc), self.mat_tronco.claro(1))
            if vivo:
                iris = tela.circulo(c + v2(rx * 0.15, ry * 0.05), max(1.2, rx * 0.5))
                tela.chapado(iris, self.olho_cor, emite=True)
                tela.chapado(tela.circulo(c + v2(rx * 0.25, ry * 0.05), max(0.6, rx * 0.2)), (40, 10, 0), emite=True)
                tela.px(c[0] - rx * 0.1, c[1] - ry * 0.3, (255, 250, 220), emite=True)
                tela.brilho(c, rx * 2.4, self.olho_cor, 0.55)
        abre = P["boca"]
        bc = L(0.0, 0.11 + 0.02 * abre)
        bw = self.boca_larg * S / 2
        bh = (0.025 + 0.13 * abre) * S / 2
        P["rosto_pos"].update(boca=bc, bw=bw, bh=bh)
        contorno = []
        for a in np.linspace(0, 2 * math.pi, 18)[:-1]:
            ondula = 1 + 0.18 * math.sin(a * 6 + 1.3)
            contorno.append(bc + v2(math.cos(a) * bw * ondula, math.sin(a) * bh * ondula * (1.25 if math.sin(a) > 0 else 1)))
        boca = tela.poly(contorno)
        tela.chapado(boca, GARGANTA)
        if vivo and self.seiva is not None:
            tela.brilho(bc + v2(0, bh * 0.3), bw * 0.8, self.seiva, 0.35 * abre, halo=False)
        n = 7
        for k in range(n):                                    # farpas de cima e de baixo
            x = -bw * 0.85 + k * bw * 1.7 / (n - 1)
            comp = bh * (0.55 + 0.45 * ((k * 37 % 5) / 4))
            topo = bc + v2(x, -bh * 0.95)
            tela.pintar(tela.poly([topo + v2(-1.6, 0), topo + v2(1.6, 0), topo + v2(0.4, comp)]) & boca, DENTE_DE_FARPA)
            if k % 2 == 0:
                base = bc + v2(x + 1, bh * 1.1)
                tela.pintar(tela.poly([base + v2(-1.5, 0), base + v2(1.5, 0), base + v2(0, -comp * 0.8)]) & boca, DENTE_DE_FARPA)
        labio = tela.poly(contorno) & ~tela.poly([bc + (q - bc) * 0.86 for q in contorno])
        ys, xs = np.nonzero(labio)
        T.multiplicar(tela, ys, xs, 0.55)

    def murchar(self, tela, P):
        """Na morte a planta escurece e perde a cor aos poucos."""
        q = P["queda"]
        if q > 0:
            tela.tingir(tela.mascara() & ~tela.emite, (40, 34, 36), 0.45 * q)


# ============================================================
# ÁRVORE
# ============================================================

class Arvore(ForjaPlanta):
    """Árvore com galhos ramificados, folhas nas pontas e cipós pendurados."""

    n_galhos = 4
    profundidade = 3
    galho_comp = 0.42
    galho_larg = 0.07
    abertura = 1.1                    # quanto os galhos se abrem para os lados (radianos)
    folhas = Mat((150, 34, 38), 5, relevo=0.8, ruido=0.25)    # None = galhos secos
    folhas_por_ponta = 4
    cipos = 4
    cor_cipo = (54, 70, 40)

    def gerar(self):
        rng = random.Random(self.semente + 2)
        self.galhos = []

        def brota(pai, t, ang, comp, larg, nivel):
            g = dict(pai=pai, t=t, ang=ang, comp=comp, larg=larg, nivel=nivel, dobra=rng.uniform(-0.6, 0.6),
                     frente=rng.random() < 0.5, filhos=0)
            self.galhos.append(g)
            idx = len(self.galhos) - 1
            if nivel < self.profundidade:
                for _ in range(rng.choice((1, 2, 2))):
                    self.galhos[idx]["filhos"] += 1
                    brota(idx, rng.uniform(0.45, 0.95), rng.uniform(-0.75, 0.75), comp * rng.uniform(0.5, 0.72),
                          larg * 0.6, nivel + 1)
        for k in range(self.n_galhos):
            frac = k / max(1, self.n_galhos - 1) * 2 - 1
            brota(None, rng.uniform(0.78, 1.0), frac * self.abertura + rng.uniform(-0.15, 0.15),
                  self.galho_comp * rng.uniform(0.75, 1.1), self.galho_larg, 1)
        self.cipo_galhos = [rng.randrange(len(self.galhos)) for _ in range(self.cipos)]

    def montar(self, m):
        P = super().montar(m)
        S = self.S
        pontos = []
        for g in self.galhos:
            if g["pai"] is None:
                base, d = ponto_na_linha(P["espinha"], g["t"])
                ang_pai = math.atan2(d[1], d[0])
            else:
                pai = pontos[g["pai"]]
                base, d = ponto_na_linha(pai, g["t"])
                ang_pai = math.atan2(d[1], d[0])
            ang = ang_pai + g["ang"] + m["balanco"] * 0.05 * g["nivel"] + m["queda"] * 0.35 * g["nivel"] * (1 if g["ang"] > 0 else -1)
            ang += m["chicote"] * 0.08 * g["nivel"]
            meio = base + direcao(ang + g["dobra"] * 0.5) * (g["comp"] * S * 0.5)
            fim = meio + direcao(ang - g["dobra"] * 0.4) * (g["comp"] * S * 0.5)
            pontos.append([base, meio, fim])
        P["galhos"] = pontos
        return P

    def _galhos(self, tela, P, frente):
        S = self.S
        mat = self.mat_tronco if frente else self.mat_tronco.escuro(1)
        for g, pts in zip(self.galhos, P["galhos"]):
            if g["frente"] != frente and g["nivel"] > 1:
                continue
            if g["nivel"] == 1 and not frente:
                continue
            L = g["larg"] * S
            m = tela.pintar(tela.corrente(pts, [L, L * 0.7, max(0.6, L * 0.35)]), mat)
            T.casca(tela, m, pts[0], eixo=pts[-1] - pts[0], espaco=3, ondula=0.6, semente=self.semente)
        for g, pts in zip(self.galhos, P["galhos"]):
            if g["filhos"] or self.folhas is None or g["frente"] != frente:
                continue
            self._folhas(tela, pts[-1], P, g)

    def _folhas(self, tela, ponta, P, g):
        S = self.S
        rng = random.Random(int(g["t"] * 1000) + self.semente)
        cair = P["queda"]
        for k in range(self.folhas_por_ponta):
            if rng.random() < cair:
                continue
            c = ponta + v2(rng.uniform(-0.06, 0.06) * S, rng.uniform(-0.05, 0.04) * S)
            c = c + v2(math.sin(P["fase"] + k) * 0.6, 0)
            folha = tela.elipse_girada(c, S * rng.uniform(0.028, 0.04), S * 0.018, rng.uniform(0, 3.1))
            mf = tela.pintar(folha, self.folhas if k % 2 else self.folhas.escuro(1))
            tela.traco(c - v2(S * 0.02, 0), c + v2(S * 0.02, 0), self.folhas[0], sobre=True)
            if k == 0:
                T.escorrer(tela, mf, c, self.folhas[2], densidade=0.25, comp=3, fase=P["fase"], molhado=0.0, semente=k)

    def atras(self, tela, ctx, P):
        self._galhos(tela, P, False)
        super().atras(tela, ctx, P)

    def frente(self, tela, ctx, P):
        self._galhos(tela, P, True)
        S = self.S
        for k, i in enumerate(self.cipo_galhos):                   # cipós pendurados que balançam
            pts = P["galhos"][i]
            topo = lerp(pts[1], pts[2], 0.4)
            comp = S * (0.12 + 0.05 * (k % 3))
            meio = topo + v2(math.sin(P["fase"] + k) * 1.5, comp * 0.5)
            fim = topo + v2(math.sin(P["fase"] + k + 0.8) * 2.5, comp)
            tela.tracos([topo, meio, fim], self.cor_cipo)
            tela.px(fim[0], fim[1] + 1, misturar(self.cor_cipo, (0, 0, 0), 0.4))
        super().frente(tela, ctx, P)

    def efeitos(self, tela, ctx, P):
        if self.folhas is not None and (P["ferido"] or P["queda"] > 0):            # folhas caindo
            topo = P["espinha"][-1]
            T.particulas(tela, topo + v2(0, self.S * 0.2), (self.S * 0.4, self.S * 0.2), self.folhas[2], n=6,
                         fase=-P["fase"], sobe=-self.S * 0.3, emite=False, semente=self.semente)


# ============================================================
# COGUMELO
# ============================================================

class Cogumelo(ForjaPlanta):
    """Fungo andante: caule liso com anel, chapéu com lamelas e pintas, nuvem de esporos."""

    S = 54
    proporcao = (2.0, 1.7)
    pe = 0.45
    altura = 0.62
    larg_base, larg_topo = 0.3, 0.22
    torcao = 0.03
    casca = False
    nos = 0
    musgo = None
    seiva = None
    n_raizes = 3
    raiz_comp = 0.3
    mat_tronco = Mat((214, 196, 166), 6, relevo=0.9, ruido=0.12)
    rosto_t = 0.5
    olho_cor = (200, 255, 110)
    olho_tam = 0.05
    boca_larg = 0.16
    chapeu = Mat((150, 40, 60), 6, relevo=1.2, especular=(255, 190, 200), ruido=0.15)
    chapeu_r = (0.5, 0.3)
    lamelas = (96, 70, 66)
    pintas = (236, 228, 190)
    pintas_brilham = (190, 255, 120)    # cor das pintas que emitem luz, ou None
    esporos = (190, 240, 110)
    anel_t = 0.78

    def tronco(self, tela, P):
        m = super().tronco(tela, P)
        S = self.S
        p, d = ponto_na_linha(P["espinha"], self.anel_t)                   # anel (saia) do caule
        n = v2(-d[1], d[0])
        w = self.largura(self.anel_t) * 0.62
        anel = tela.poly([p + n * w, p - n * w, p - n * (w * 1.25) - d * (S * 0.07), p + n * (w * 1.25) - d * (S * 0.07)])
        tela.pintar(anel, self.mat_tronco.escuro(1))
        self._chapeu(tela, P)
        return m

    def _chapeu(self, tela, P):
        S = self.S
        topo, d = ponto_na_linha(P["espinha"], 1.0)
        ang = math.atan2(d[1], d[0]) + math.pi / 2
        rx, ry = self.chapeu_r[0] * S, self.chapeu_r[1] * S
        L = Local(topo, ang, 1.0)
        domo = [L(math.cos(a) * rx, -math.sin(a) * ry) for a in np.linspace(0, math.pi, 16)]
        cupula = tela.poly(domo + [L(-rx * 1.02, 3), L(rx * 1.02, 3)])
        baixo = tela.poly([L(-rx * 0.98, 2), L(rx * 0.98, 2), L(rx * 0.6, ry * 0.32), L(-rx * 0.6, ry * 0.32)])
        tela.chapado(baixo, self.lamelas)                                    # lamelas por baixo
        for k in range(9):
            x = -rx * 0.9 + k * rx * 1.8 / 8
            tela.traco(L(x, 2), L(x * 0.65, ry * 0.3), misturar(self.lamelas, (20, 10, 10), 0.5), sobre=True)
        m = tela.pintar(cupula, self.chapeu)
        rng = random.Random(self.semente + 4)
        for k in range(7):                                                   # pintas (algumas brilham)
            a = rng.uniform(0.25, 2.9)
            rr = rng.uniform(0.25, 0.85)
            c = L(math.cos(a) * rx * rr, -math.sin(a) * ry * rr * 0.85)
            raio = S * rng.uniform(0.025, 0.045)
            brilha = self.pintas_brilham is not None and k % 3 == 0 and not P["morto"]
            tela.chapado(tela.circulo(c, raio) & m, self.pintas_brilham if brilha else self.pintas, emite=brilha)
            if brilha:
                tela.brilho(c, raio * 3, self.pintas_brilham, 0.4)
        T.manchas(tela, m, topo, misturar(self.chapeu[2], (30, 10, 20), 0.4), escala=3, quantidade=0.18, forca=0.5)
        T.escorrer(tela, m, topo, misturar(self.chapeu[1], (40, 0, 10), 0.3), densidade=0.18, comp=4,
                   fase=P["fase"], molhado=0.25, semente=self.semente)
        P["chapeu_centro"] = L(0, -ry * 0.4)

    def efeitos(self, tela, ctx, P):
        if self.esporos is None or P["morto"]:
            return
        c = P.get("chapeu_centro", P["espinha"][-1])
        S = self.S
        if P["golpe"]:                                                       # nuvem de esporos no golpe
            nuvem = c + v2(S * 0.55, S * 0.1)
            fx.fumaca(tela, nuvem, S * 0.12, cor=misturar(self.esporos, (60, 60, 40), 0.55), fase=P["fase"], n=5, sobe=6)
            T.particulas(tela, nuvem, (S * 0.3, S * 0.18), self.esporos, n=22, fase=P["fase"], sobe=6, semente=3)
            tela.brilho(nuvem, S * 0.3, self.esporos, 0.3)
        else:
            T.particulas(tela, c, (S * 0.4, S * 0.15), self.esporos, n=6, fase=P["fase"], sobe=S * 0.3, semente=5)
