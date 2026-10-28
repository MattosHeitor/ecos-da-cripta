"""Peças de composição dos animais: Pata, Cauda, Asa e Cabeca.

Cada peça guarda só a FORMA (medidas em frações de S, o tamanho do animal). A posição de cada
quadro chega pelos métodos, então uma mesma peça serve para a folha inteira.
Ângulos: 0 = para a direita (frente), pi/2 = para baixo, pi = para trás, -pi/2 = para cima.
"""
import math

import numpy as np

from ..motor import Mat, v2, lerp, girar, misturar
from ..humanoide import ik
from .. import texturas as T

DENTE = (232, 222, 196)
DENTE_ROEDOR = (226, 192, 84)          # os incisivos amarelados dos ratos
ROSADO = (196, 112, 122)               # nariz e orelha por dentro dos roedores
BIGODE = (190, 180, 172)
BOCA = (56, 8, 14)
LINGUA = (150, 48, 58)
CHIFRE = Mat((150, 136, 112), 6, relevo=1.2, ruido=0.2)


def direcao(ang):
    return v2(math.cos(ang), math.sin(ang))


class Local:
    """Sistema de coordenadas de uma peça: x = para a frente da peça, y = para baixo dela (em S)."""

    def __init__(self, base, ang, S):
        self.b = v2(base)
        self.f = direcao(ang)
        self.n = v2(-self.f[1], self.f[0])
        self.S = S
        self.ang = ang

    def __call__(self, x, y):
        return self.b + self.f * (x * self.S) + self.n * (y * self.S)

    def pts(self, lista):
        return [self(x, y) for x, y in lista]


def larguras_interpoladas(grossura, n, S):
    """Espalha uma lista curta de grossuras por n pontos (afinando aos poucos)."""
    g = np.array(grossura, float)
    xs = np.linspace(0, 1, len(g))
    return [float(np.interp(t, xs, g)) * S for t in np.linspace(0, 1, n)]


# ============================================================
# PATA
# ============================================================

class Pata:
    """Pata articulada.

    comp: comprimento de cada segmento (2 ou 3). Com 3, o último (metatarso/metacarpo) sobe do
    pé inclinado 'metatarso' radianos para trás, e o resto é resolvido por IK até ele.
    joelho: para onde a articulação do meio aponta ("frente", "tras" ou "cima" nos insetos).
    estilo do pé: "pata", "mao", "ave", "inseto" ou "casco".
    """

    def __init__(self, comp=(0.2, 0.2, 0.1), grossura=(0.065, 0.045, 0.032, 0.026), joelho="frente",
                 estilo="pata", metatarso=0.35, garra=(222, 212, 190), dedos=3, cobertura="pelo"):
        self.comp = comp
        self.grossura = grossura
        self.joelho = joelho
        self.estilo = estilo
        self.metatarso = metatarso
        self.garra = garra
        self.dedos = dedos
        self.cobertura = cobertura

    @property
    def alcance(self):
        return sum(self.comp)

    def juntas(self, raiz, pe, S):
        """Pontos da raiz até o pé: [raiz, joelho, (tornozelo), pé]."""
        raiz, pe = v2(raiz), v2(pe)
        L = [c * S for c in self.comp]
        meio = None
        alvo = pe
        if len(L) == 3:
            meio = pe + direcao(-math.pi / 2 - self.metatarso) * L[2]
            alvo = meio
        joelho = self._ik(raiz, alvo, L[0], L[1])
        return [raiz, joelho] + ([meio] if meio is not None else []) + [pe]

    def _ik(self, a, t, l1, l2):
        j1, j2 = ik(a, t, l1, l2, 1), ik(a, t, l1, l2, -1)
        if self.joelho == "frente":
            return j1 if j1[0] >= j2[0] else j2
        if self.joelho == "tras":
            return j1 if j1[0] < j2[0] else j2
        return j1 if j1[1] < j2[1] else j2

    def desenhar(self, tela, pts, mat, S, semente=0):
        """Pinta a pata (segmentos, articulações, textura e o pé). Devolve a máscara."""
        larg = [g * S for g in self.grossura[:len(pts)]]
        larg += [larg[-1]] * (len(pts) - len(larg))
        m = tela.corrente(pts, larg)
        for p, r in zip(pts[1:-1], larg[1:-1]):
            m |= tela.circulo(p, r * 1.1)
        m = tela.pintar(m, mat)
        eixo = pts[-1] - pts[0]
        ang = math.atan2(eixo[1], eixo[0])
        if self.cobertura == "pelo":
            T.pelagem(tela, m, pts[0], ang=ang, comp=2, densidade=0.28, semente=semente)
        elif self.cobertura == "quitina":
            T.quitina(tela, m, pts[0], eixo=eixo, espaco=4, brilho=0.3, semente=semente)
            for p in pts[1:-1]:
                tela.chapado(tela.circulo(p, max(0.8, larg[1] * 0.55)) & m, mat[0])
        elif self.cobertura == "escamas":
            T.escamas(tela, m, pts[0], tam=2)
        self.pe(tela, pts, mat, S)
        return m

    def pe(self, tela, pts, mat, S):
        p, antes = pts[-1], pts[-2]
        g = self.grossura[-1] * S
        if self.estilo == "pata":
            c = p + v2(g * 0.7, -g * 0.35)
            tela.pintar(tela.elipse(c[0], c[1], g * 1.45, g * 0.85), mat)
            for k in range(1, self.dedos):
                x = c[0] - g * 0.6 + k * g * 1.2 / self.dedos + g * 0.4
                tela.traco(v2(x, c[1] - g * 0.3), v2(x + 0.5, c[1] + g * 0.7), mat[0], sobre=True)
            for k in range(self.dedos):
                q = v2(c[0] + g * 1.2 - k * 1.0, c[1] + g * 0.55)
                tela.px(q[0] + 1, q[1], self.garra)
        elif self.estilo == "mao":
            c = p + v2(g * 0.4, -g * 0.2)
            tela.pintar(tela.elipse(c[0], c[1], g * 1.2, g * 0.9), mat)
            for k in range(3):
                q = c + v2(g * (0.4 + k * 0.45), g * 0.55)
                tela.traco(q, q + v2(0.6, g * 0.6), mat[1])
        elif self.estilo == "ave":
            for ang, L in ((-0.25, 1.0), (0.15, 1.15), (0.55, 0.9), (math.pi + 0.3, 0.6)):
                fim = p + direcao(ang) * (g * 4.2 * L)
                tela.traco(p, fim, mat[2])
                tela.px(fim[0], fim[1] + 1, self.garra)
        elif self.estilo == "inseto":
            d = p - antes
            d = d / (np.linalg.norm(d) or 1)
            tela.traco(p, p + d * 2 + v2(1.5, 0), mat[1])
        elif self.estilo == "casco":
            tela.pintar(tela.poly([p + v2(-g, -g * 1.2), p + v2(g * 1.2, -g * 1.2), p + v2(g * 1.6, 0.5), p + v2(-g * 1.1, 0.5)]),
                        Mat((40, 32, 30), 4))


# ============================================================
# CAUDA
# ============================================================

class Cauda:
    """Cauda em segmentos que ondulam com 'balanco' e 'fase'.

    estilo: "pelo" (tufo peludo), "rato" (fina e anelada), "escamas", "espinhos" ou "lisa".
    """

    def __init__(self, comp=0.45, grossura=(0.055, 0.05, 0.035, 0.012), segmentos=6, ang=math.pi - 0.45,
                 curva=0.55, estilo="pelo", ponta=None):
        self.comp = comp
        self.grossura = grossura
        self.segmentos = segmentos
        self.ang = ang
        self.curva = curva
        self.estilo = estilo
        self.ponta = ponta

    def pontos(self, base, S, balanco=0.0, fase=0.0, ang_extra=0.0):
        n = self.segmentos
        passo = self.comp * S / n
        a = self.ang + ang_extra
        pts = [v2(base)]
        for k in range(n):
            a += self.curva / n + balanco * math.sin(fase - k * 0.8) * 0.3 * (k + 1) / n
            pts.append(pts[-1] + direcao(a) * passo)
        return pts

    def desenhar(self, tela, pts, mat, S, semente=0):
        larg = larguras_interpoladas(self.grossura, len(pts), S)
        m = tela.corrente(pts, larg)
        if self.estilo == "pelo":
            m |= T.tufos(tela, m, pts[0], (0, -1), comp=2.5, espaco=2, inclina=-0.9, semente=semente)
            m |= T.tufos(tela, m, pts[0], (0, 1), comp=2.5, espaco=2, inclina=0.9, semente=semente + 1)
        m = tela.pintar(m, mat)
        meio = pts[len(pts) // 2] - pts[0]
        ang = math.atan2(meio[1], meio[0])
        if self.estilo == "pelo":
            T.pelagem(tela, m, pts[0], ang=ang, comp=3, densidade=0.35, semente=semente)
        elif self.estilo == "rato":
            for i in range(1, len(pts) - 1):
                tela.traco(pts[i] + v2(0, -larg[i]), pts[i] + v2(0, larg[i]), mat[1], sobre=True)
        elif self.estilo == "escamas":
            T.escamas(tela, m, pts[0], tam=3)
        elif self.estilo == "espinhos":
            for i in range(1, len(pts) - 1):
                d = pts[i + 1] - pts[i - 1]
                n = v2(d[1], -d[0]) / (np.linalg.norm(d) or 1)
                if n[1] > 0:
                    n = -n
                base = pts[i]
                tela.pintar(tela.poly([base - d * 0.15, base + n * (larg[i] + S * 0.06), base + d * 0.15]), mat.escuro(1))
        return m


# ============================================================
# ASA
# ============================================================

class Asa:
    """Asa de "membrana" (morcego/dragão), "penas" (aves), "inseto" (translúcida) ou "mariposa"
    (larga e opaca, com nervuras, borda empoeirada e uma mancha em forma de olho).

    abertura: 0 = fechada junto ao corpo, 1 = aberta. bater: giro extra (negativo = para cima).
    """

    # pontos em fração da envergadura, raiz = (0, 0); a asa abre para trás e para cima
    POSES = {
        "aberta": dict(cotovelo=(-0.22, -0.4), pulso=(-0.48, -0.66),
                       dedos=[(-0.08, -1.02), (-0.66, -0.98), (-1.0, -0.6), (-1.0, -0.2)], ancora=(-0.46, 0.1)),
        "fechada": dict(cotovelo=(-0.16, -0.16), pulso=(-0.4, -0.26),
                        dedos=[(-0.44, -0.5), (-0.64, -0.38), (-0.74, -0.2), (-0.7, -0.04)], ancora=(-0.34, 0.06)),
    }

    def __init__(self, envergadura=0.8, estilo="membrana", rasgos=0, garra=(210, 200, 180), osso=None, opacidade=None,
                 detalhada=False):
        self.envergadura = envergadura
        self.estilo = estilo
        self.rasgos = rasgos
        self.garra = garra
        self.osso = osso
        self.opacidade = opacidade          # membrana translúcida (None = opaca)
        self.detalhada = detalhada          # painéis entre os dedos, recortes fundos e borda escura

    def pontos(self, raiz, S, abertura=1.0, bater=0.0):
        a, f = self.POSES["aberta"], self.POSES["fechada"]
        esc = self.envergadura * S
        raiz = v2(raiz)

        def p(xy_a, xy_f):
            q = lerp(xy_f, xy_a, abertura) * esc
            return girar(raiz + q, bater, raiz)
        return dict(raiz=raiz, cotovelo=p(a["cotovelo"], f["cotovelo"]), pulso=p(a["pulso"], f["pulso"]),
                    dedos=[p(da, df) for da, df in zip(a["dedos"], f["dedos"])], ancora=p(a["ancora"], f["ancora"]),
                    abertura=abertura)

    def desenhar(self, tela, P, mat, S, semente=0):
        if self.estilo == "inseto":
            return self._inseto(tela, P, mat, S)
        if self.estilo == "mariposa":
            return self._mariposa(tela, P, mat, S)
        if self.estilo == "penas":
            return self._penas(tela, P, mat, S)
        raiz, cot, pulso, dedos, anc = P["raiz"], P["cotovelo"], P["pulso"], P["dedos"], P["ancora"]
        contorno = [raiz, cot, pulso, dedos[0]]
        fundo = 0.3 if self.detalhada else 0.22
        for i in range(1, len(dedos)):
            meio = lerp(lerp(dedos[i - 1], dedos[i], 0.5), pulso, fundo)           # recorte entre os dedos
            contorno += [meio, dedos[i]]
        contorno += [lerp(lerp(dedos[-1], anc, 0.5), raiz, 0.22 if self.detalhada else 0.18), anc]
        m = tela.poly(contorno)
        rng = np.random.default_rng(semente)
        for _ in range(self.rasgos):                                  # furos e rasgos na membrana
            i = int(rng.integers(0, len(dedos) - 1))
            c = lerp(lerp(dedos[i], dedos[i + 1], rng.uniform(0.3, 0.7)), pulso, rng.uniform(0.15, 0.35))
            r = S * rng.uniform(0.02, 0.04)
            m &= ~tela.poly([c + v2(-r, -r * 0.4), c + v2(r * 0.3, -r), c + v2(r, r * 0.5), c + v2(-r * 0.2, r)])
        membrana = mat.copia(relevo=0.5, arredonda=0.35)
        m = tela.vidro(m, membrana, self.opacidade) if self.opacidade else tela.pintar(m, membrana)
        osso = self.osso or mat.claro(1)
        if self.detalhada:
            pontas = list(dedos) + [anc]
            for i in range(len(pontas) - 1):                          # painéis alternados entre os dedos
                if i % 2:
                    painel = tela.poly([pulso, pontas[i], pontas[i + 1]]) & m
                    ys, xs = np.nonzero(painel)
                    T.multiplicar(tela, ys, xs, 0.86)
                meio = lerp(lerp(pontas[i], pontas[i + 1], 0.5), pulso, 0.3)
                tela.traco(lerp(pulso, meio, 0.15), meio, mat[0], sobre=True)    # nervura do painel
            ys, xs = np.nonzero(T.borda(m, (0, 1)) | T.borda(m, (-1, 0)))         # borda de fora mais escura
            T.multiplicar(tela, ys, xs, 0.7)
            for d in dedos:
                tela.pintar(tela.capsula(pulso, d, S * 0.016, S * 0.005), osso)
        else:
            for d in dedos:                                           # nervuras/dedos
                tela.traco(lerp(pulso, d, 0.1), lerp(pulso, d, 0.55), mat[0], sobre=True)
                tela.pintar(tela.capsula(pulso, d, S * 0.014, S * 0.005), osso)
        tela.pintar(tela.capsula(raiz, cot, S * 0.03, S * 0.022) | tela.capsula(cot, pulso, S * 0.022, S * 0.016), osso)
        gancho = pulso + v2(S * 0.02, -S * 0.035)
        tela.traco(pulso, gancho, self.garra)
        tela.px(gancho[0] + 1, gancho[1] + 1, self.garra)
        return m

    def _penas(self, tela, P, mat, S, n=7):
        """Asa de ave pena por pena: rêmiges do fundo para a frente e as coberteiras por cima."""
        if P.get("abertura", 1) < 0.35:
            return self._penas_fechada(tela, P, mat, S)
        raiz, cot, pulso, dedos, anc = P["raiz"], P["cotovelo"], P["pulso"], P["dedos"], P["ancora"]
        trilha = [pulso] + list(dedos)                                 # curva das pontas
        comp = [float(np.linalg.norm(b - a)) for a, b in zip(trilha, trilha[1:])]
        total = sum(comp) or 1

        def na_trilha(t):
            alvo = t * total
            for (a, b), c in zip(zip(trilha, trilha[1:]), comp):
                if alvo <= c:
                    return lerp(a, b, alvo / (c or 1))
                alvo -= c
            return trilha[-1]
        m = np.zeros((tela.h, tela.w), bool)
        for k in reversed(range(n)):                                   # de trás (perto do corpo) para a ponta
            t = (k + 1) / n
            base = lerp(pulso, lerp(anc, raiz, 0.3), 1 - t * 0.85)
            ponta = na_trilha(1 - t * 0.98)
            pena = tela.capsula(base, ponta, S * 0.06, S * 0.03)
            m |= tela.pintar(pena, mat.escuro(1) if k % 2 else mat)
        coberteiras = tela.poly([raiz, cot, pulso, lerp(pulso, anc, 0.45), lerp(raiz, anc, 0.55)])
        m2 = tela.pintar(coberteiras, mat.claro(1))
        T.penas(tela, m2, raiz, eixo=pulso - raiz, tam=2)
        return m | m2

    def _penas_fechada(self, tela, P, mat, S):
        """Asa dobrada junto ao corpo: gota alongada com coberteiras e as pontas das rêmiges."""
        raiz = P["raiz"]
        alvo = sum(P["dedos"]) / len(P["dedos"])
        d = (alvo - raiz) / (np.linalg.norm(alvo - raiz) or 1)
        n = v2(-d[1], d[0])
        comp, larg = self.envergadura * S * 0.95, self.envergadura * S * 0.17
        pts = [raiz - n * larg * 0.6, raiz + d * comp * 0.3 - n * larg, raiz + d * comp * 0.75 - n * larg * 0.45,
               raiz + d * comp, raiz + d * comp * 0.7 + n * larg * 0.5, raiz + d * comp * 0.25 + n * larg * 0.75,
               raiz + n * larg * 0.4]
        m = tela.pintar(tela.poly(pts), mat)
        cob = tela.poly([raiz - n * larg * 0.6, raiz + d * comp * 0.3 - n * larg, raiz + d * comp * 0.45 + n * larg * 0.2,
                         raiz + n * larg * 0.4])
        m2 = tela.pintar(cob & m, mat.claro(1))
        T.penas(tela, m2, raiz, eixo=d, tam=2)
        for k in range(4):                                             # pontas das rêmiges
            a = raiz + d * comp * (0.45 + k * 0.08) + n * larg * (0.45 - k * 0.22)
            tela.traco(a, raiz + d * comp * (0.92 - k * 0.03) + n * larg * (0.2 - k * 0.12), mat[0], sobre=True)
        return m

    def _inseto(self, tela, P, mat, S):
        raiz, dedos = P["raiz"], P["dedos"]
        m = np.zeros((tela.h, tela.w), bool)
        for ponta, larg in ((dedos[1], 0.11), (dedos[2], 0.085)):
            d = ponta - raiz
            c = raiz + d * 0.5
            comp = float(np.linalg.norm(d)) * 0.55
            asa = tela.elipse_girada(c, comp, S * larg, math.atan2(d[1], d[0]))
            tela.vidro(asa, mat, 0.38)
            for t in (0.3, 0.6):
                tela.traco(raiz, lerp(c, ponta, t) + v2(0, S * 0.02), mat[1], sobre=True)
            m |= asa
        return m

    def _mariposa(self, tela, P, mat, S):
        """Par de asas largas: a de cima (triangular, com o olho) e a de baixo (arredondada), opacas."""
        raiz, dedos, anc = P["raiz"], P["dedos"], P["ancora"]
        baixa = (anc - raiz) * 0.35                                      # a asa de baixo fica mais baixa e para trás
        de_baixo = tela.casco([raiz, lerp(dedos[2], dedos[3], 0.3) + baixa, dedos[3] + baixa, anc + baixa, anc])
        canto = lerp(dedos[1], dedos[2], 0.5)
        de_cima = tela.casco([raiz, dedos[0], dedos[1], canto])
        po = mat.copia(relevo=0.45, arredonda=0.3, ruido=max(mat.ruido, 0.35))
        m = tela.pintar(de_baixo, po.escuro(1))
        m |= tela.pintar(de_cima, po)
        tela.traco(raiz, canto, mat[0], sobre=True)                       # onde a asa de cima cobre a de baixo
        for d in list(dedos) + [anc]:                                    # nervuras saindo da raiz
            tela.traco(lerp(raiz, d, 0.12), lerp(raiz, d, 0.8), mat[1], sobre=True)
        ys, xs = np.nonzero(T.borda(m, (0, -1)) | T.borda(m, (-1, 0)))   # borda empoeirada mais escura
        T.multiplicar(tela, ys, xs, 0.72)
        olho = lerp(raiz, lerp(dedos[0], dedos[1], 0.5), 0.55)           # mancha em forma de olho
        r = max(1.5, 0.11 * self.envergadura * S)
        tela.chapado(tela.circulo(olho, r) & m, mat[0])
        tela.chapado(tela.circulo(olho, r * 0.65) & m, mat[len(mat.cores) - 2])
        tela.px(olho[0], olho[1], mat[0])
        return m


# ============================================================
# CABEÇA
# ============================================================

class Cabeca:
    """Cabeça de fera. estilo: "canina", "felina", "primata", "morcego", "ave", "reptil", "inseto" ou "roedor".

    tam escala tudo (0.12 = lobo); focinho/bico em S. chifres: lista de
    (x, y, comprimento, ângulo local, curva, grossura) em frações de tam.
    orelha_dentro: cor de dentro da orelha (None = um tom do pelo; os roedores usam rosado).
    antena (insetos): "fio" (fina e comprida), "pluma" (mariposas), "clava" (com bolinha na ponta) ou None.
    """

    def __init__(self, estilo="canina", tam=0.12, focinho=0.13, orelha="pontuda", olho_cor=(255, 60, 40),
                 olho_brilho=True, presas=True, chifres=None, mat_chifre=None, bico_cor=None, crista=False,
                 orelha_dentro=None, antena="fio"):
        self.estilo = estilo
        self.tam = tam
        self.focinho = focinho
        self.orelha = orelha
        self.olho_cor = olho_cor
        self.olho_brilho = olho_brilho
        self.presas = presas
        self.chifres = chifres or []
        self.mat_chifre = mat_chifre or CHIFRE
        self.bico_cor = bico_cor
        self.crista = crista
        self.orelha_dentro = orelha_dentro
        self.antena = antena

    def desenhar(self, tela, base, ang, S, mat, boca=0.0, morto=False, fase=0.0, semente=0):
        """Desenha a cabeça; base = nuca (onde o pescoço encaixa). Devolve a máscara."""
        L = Local(base, ang, S)
        k = self.tam / 0.12
        metodo = getattr(self, "_" + self.estilo)
        m = metodo(tela, L, k, mat, boca, morto, fase, semente)
        for x, y, comp, a, curva, g in self.chifres:
            pts = [L(x * k, y * k)]
            aa = ang + a
            for i in range(4):
                aa += curva / 4
                pts.append(pts[-1] + direcao(aa) * (comp * k * S / 4))
            tela.pintar(tela.corrente(pts, [g * k * S, g * k * S * 0.8, g * k * S * 0.5, g * k * S * 0.3, 0.6]),
                        self.mat_chifre)
            for i in range(1, 4):
                tela.traco(pts[i] + v2(-1, 0), pts[i] + v2(1, 0), self.mat_chifre[1], sobre=True)
        return m

    # ----- olhos -----
    def _olho(self, tela, c, k, S, morto, cor=None, rx=0.017, ry=0.011):
        cor = cor or self.olho_cor
        tela.chapado(tela.elipse(c[0], c[1], max(1.0, rx * k * S), max(0.7, ry * k * S)), (18, 8, 12))
        if morto:
            tela.traco(c + v2(-1, 0), c + v2(1, 0), (60, 50, 50))
            return
        tela.px(c[0] + 0.5, c[1], cor, emite=True)
        tela.px(c[0] - 0.5, c[1], misturar(cor, (40, 0, 0), 0.4), emite=True)
        if self.olho_brilho:
            tela.brilho(c, 4 * k, cor, 0.75)

    def _dentes(self, tela, a, b, n, para_baixo=True, cor=DENTE):
        for i in range(n):
            p = lerp(a, b, (i + 0.5) / n)
            tela.px(p[0], p[1], cor)
            if i % 2 == 0:
                tela.px(p[0], p[1] + (1 if para_baixo else -1), misturar(cor, (120, 100, 80), 0.3))

    # ----- canina (lobos, cães, hienas) -----
    def _canina(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        escuro = mat.escuro(1)
        self._orelha(tela, L, k, escuro, -0.035)
        dobradica = L(0.03 * k, 0.026 * k)
        abre = boca * 0.6
        mandibula = [girar(p, abre, dobradica) for p in
                     L.pts([(0.035 * k, 0.02 * k), (0.055 * k + F * 0.95, 0.018 * k), (0.05 * k + F * 0.9, 0.036 * k),
                            (0.03 * k, 0.052 * k)])]
        if boca > 0.05:
            interior = [L(0.06 * k, 0.018 * k), L(0.065 * k + F, 0.012 * k), mandibula[1], dobradica]
            tela.chapado(tela.poly(interior), BOCA)
            lingua = lerp(dobradica, mandibula[1], 0.55)
            tela.chapado(tela.elipse(lingua[0], lingua[1] - 1, F * S * 0.28, max(1, 0.012 * S * k)), LINGUA)
        tela.pintar(tela.poly(mandibula), escuro)
        cranio = tela.elipse_girada(L(0.025 * k, -0.005 * k), 0.078 * k * S, 0.062 * k * S, L.ang)
        bochecha = tela.elipse_girada(L(0.02 * k, 0.028 * k), 0.062 * k * S, 0.04 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.055 * k, -0.058 * k), (0.06 * k + F * 0.6, -0.042 * k), (0.068 * k + F, -0.02 * k),
                                   (0.074 * k + F, 0.0), (0.066 * k + F, 0.013 * k), (0.06 * k, 0.022 * k)]))
        m = cranio | bochecha | focinho
        m |= T.tufos(tela, cranio | bochecha, L.b, (-1, 1), comp=2.5, espaco=2, inclina=0.2, semente=semente)
        m = tela.pintar(m, mat)
        T.pelagem(tela, m, L.b, ang=L.ang + math.pi, comp=2, densidade=0.25, semente=semente)
        tela.traco(L(0.065 * k, 0.016 * k), L(0.064 * k + F, 0.011 * k), mat[0])         # lábio
        if boca > 0.15 or self.presas:
            self._dentes(tela, L(0.07 * k, 0.019 * k), L(0.06 * k + F, 0.015 * k), 4 if boca > 0.15 else 0)
            if self.presas:
                for x in (0.045 * k + F * 0.8, 0.04 * k + F * 0.45):
                    p = L(x, 0.02 * k)
                    tela.px(p[0], p[1], DENTE)
                    tela.px(p[0], p[1] + 1, DENTE)
            if boca > 0.15:
                self._dentes(tela, mandibula[0] + (mandibula[1] - mandibula[0]) * 0.2, mandibula[1], 3, para_baixo=False)
        nariz = L(0.07 * k + F, -0.012 * k)
        tela.chapado(tela.circulo(nariz, max(1.0, 0.012 * k * S)), (22, 14, 18))
        tela.px(nariz[0] - 0.5, nariz[1] - 1, (110, 96, 104))
        self._olho(tela, L(0.072 * k, -0.03 * k), k, S, morto)
        tela.traco(L(0.05 * k, -0.052 * k), L(0.1 * k, -0.04 * k), mat[0])               # sobrancelha brava
        self._orelha(tela, L, k, mat, 0.0)
        return m

    def _orelha(self, tela, L, k, mat, dx):
        if self.orelha is None:
            return
        if self.orelha == "pontuda":
            pts = [(-0.02 + dx, -0.05), (0.03 + dx, -0.056), (-0.035 + dx, -0.16)]
        elif self.orelha == "larga":
            pts = [(-0.035 + dx, -0.045), (0.04 + dx, -0.06), (-0.02 + dx, -0.14)]
        elif self.orelha == "redonda":
            c = L((-0.035 + dx) * k, -0.02 * k)
            tela.pintar(tela.elipse(c[0], c[1], 0.03 * k * L.S, 0.035 * k * L.S), mat)
            tela.chapado(tela.elipse(c[0] + 0.5, c[1], 0.015 * k * L.S, 0.02 * k * L.S), self._cor_de_dentro(mat, dx))
            return
        else:
            return
        tri = L.pts([(x * k, y * k) for x, y in pts])
        tela.pintar(tela.poly(tri), mat)
        dentro = [lerp(tri[0], tri[2], 0.15) + (tri[1] - tri[0]) * 0.2, lerp(tri[1], tri[2], 0.2), lerp(tri[0], tri[2], 0.75)]
        tela.chapado(tela.poly(dentro), self._cor_de_dentro(mat, dx))

    def _cor_de_dentro(self, mat, dx):
        """Cor de dentro da orelha: um tom do pelo ou a cor própria (a orelha de trás, dx < 0, fica na sombra)."""
        if self.orelha_dentro is None:
            return mat[1]
        return self.orelha_dentro if dx >= 0 else misturar(self.orelha_dentro, mat[0], 0.45)

    # ----- felina (tigres, gatos) -----
    def _felina(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        escuro = mat.escuro(1)
        self._orelha(tela, L, k, escuro, -0.03)
        dobradica = L(0.03 * k, 0.03 * k)
        mandibula = [girar(p, boca * 0.75, dobradica) for p in
                     L.pts([(0.03 * k, 0.025 * k), (0.06 * k + F, 0.028 * k), (0.05 * k + F * 0.9, 0.045 * k), (0.025 * k, 0.05 * k)])]
        if boca > 0.05:
            tela.chapado(tela.poly([L(0.05 * k, 0.025 * k), L(0.07 * k + F, 0.02 * k), mandibula[1], dobradica]), BOCA)
        tela.pintar(tela.poly(mandibula), escuro)
        cranio = tela.elipse_girada(L(0.03 * k, -0.01 * k), 0.08 * k * S, 0.07 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.06 * k, -0.05 * k), (0.075 * k + F, -0.025 * k), (0.08 * k + F, 0.005 * k),
                                   (0.07 * k + F, 0.026 * k), (0.04 * k, 0.04 * k)]))
        m = cranio | focinho
        m |= T.tufos(tela, cranio, L.b, (-1, 1), comp=2.5, espaco=2, inclina=0.2, semente=semente)
        m = tela.pintar(m, mat)
        T.pelagem(tela, m, L.b, ang=L.ang + math.pi, comp=2, densidade=0.22, semente=semente)
        if self.presas:                                                                 # caninos longos
            for x in (0.06 * k + F * 0.75,):
                p = L(x, 0.027 * k)
                for i in range(3 if boca < 0.3 else 4):
                    tela.px(p[0], p[1] + i, DENTE)
        nariz = L(0.078 * k + F, -0.012 * k)
        tela.chapado(tela.circulo(nariz, max(1.0, 0.011 * k * S)), (60, 30, 36))
        for i in range(3):                                                              # bigodes
            a = L(0.06 * k + F, 0.008 * k + i * 0.008 * k)
            tela.traco(a, a + v2(S * 0.09 * k, (i - 0.5) * 2.2), (200, 196, 180))
        self._olho(tela, L(0.08 * k, -0.033 * k), k, S, morto, rx=0.02, ry=0.012)
        tela.traco(L(0.06 * k, -0.055 * k), L(0.105 * k, -0.045 * k), mat[0])
        self._orelha(tela, L, k, mat, 0.0)
        return m

    # ----- primata (macacos, carniçais) -----
    def _primata(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        self._orelha(tela, L, k, mat.escuro(1), -0.02)
        cranio = tela.circulo(L(0.02 * k, -0.02 * k), 0.07 * k * S)
        face = tela.elipse_girada(L(0.06 * k, 0.012 * k), 0.035 * k * S + F * S * 0.3, 0.04 * k * S, L.ang)
        m = tela.pintar(cranio | T.tufos(tela, cranio, L.b, (0, -1), comp=2.5, espaco=2, semente=semente), mat)
        T.pelagem(tela, m, L.b, ang=L.ang + math.pi * 0.8, comp=2, densidade=0.3, semente=semente)
        pele = Mat(misturar(mat.cores[3], (200, 150, 130), 0.5), 5)
        tela.pintar(face, pele)
        tela.chapado(tela.elipse_girada(L(0.06 * k, -0.025 * k), 0.04 * k * S, 0.012 * k * S, L.ang), mat[0])   # testa
        boca_c = L(0.075 * k + F * 0.3, 0.032 * k)
        tela.chapado(tela.elipse(boca_c[0], boca_c[1], 0.02 * k * S, max(0.6, boca * 0.025 * k * S)), BOCA)
        if boca > 0.2:
            self._dentes(tela, boca_c + v2(-0.02 * k * S, -1), boca_c + v2(0.02 * k * S, -1), 3)
        for dx in (0.055, 0.09):
            self._olho(tela, L(dx * k, -0.01 * k), k, S, morto, rx=0.012, ry=0.01)
        self._orelha(tela, L, k, mat, 0.0)
        return m

    # ----- morcego -----
    def _morcego(self, tela, L, k, mat, boca, morto, fase, semente):
        """Crânio redondo, focinho curto com folha nasal, orelhas enormes e presas compridas."""
        S, F = L.S, self.focinho
        pele = Mat(misturar(mat.cores[3], (170, 110, 110), 0.5), 5, relevo=0.9)
        for dx, m_orelha in ((-0.03, mat.escuro(1)), (0.0, mat)):
            tri = L.pts([((-0.03 + dx) * k, -0.03 * k), ((0.03 + dx) * k, -0.045 * k), ((-0.05 + dx) * k, -0.17 * k)])
            tela.pintar(tela.poly(tri), m_orelha)
            tela.chapado(tela.poly([lerp(tri[0], tri[1], 0.3), lerp(tri[1], tri[2], 0.25), lerp(tri[0], tri[2], 0.7)]), pele[1])
        dobradica = L(0.03 * k, 0.02 * k)
        mandibula = [girar(p, boca * 0.6, dobradica) for p in
                     L.pts([(0.03 * k, 0.015 * k), (0.05 * k + F, 0.018 * k), (0.03 * k, 0.04 * k)])]
        if boca > 0.05:
            tela.chapado(tela.poly([L(0.04 * k, 0.015 * k), L(0.055 * k + F, 0.01 * k), mandibula[1], dobradica]), BOCA)
        tela.pintar(tela.poly(mandibula), pele.escuro(1))
        cranio = tela.circulo(L(0.01 * k, -0.005 * k), 0.058 * k * S)
        m = tela.pintar(cranio | T.tufos(tela, cranio, L.b, (-1, 1), comp=2, espaco=2, semente=semente), mat)
        T.pelagem(tela, m, L.b, ang=L.ang + math.pi, comp=2, densidade=0.25, semente=semente)
        focinho = tela.poly(L.pts([(0.04 * k, -0.025 * k), (0.06 * k + F, -0.012 * k), (0.065 * k + F, 0.008 * k),
                                   (0.04 * k, 0.02 * k)]))
        tela.pintar(focinho, pele)
        folha = L.pts([(0.05 * k + F, -0.012 * k), (0.065 * k + F, -0.012 * k), (0.06 * k + F, -0.04 * k)])
        tela.pintar(tela.poly(folha), pele.claro(1))
        for x in (0.045 * k + F * 0.7, 0.04 * k + F * 0.35):          # presas
            p = L(x, 0.016 * k)
            for i in range(2 if boca < 0.3 else 3):
                tela.px(p[0], p[1] + i, DENTE)
        self._olho(tela, L(0.045 * k, -0.02 * k), k, S, morto, rx=0.013, ry=0.011)
        return m

    # ----- ave (corvos, garças) -----
    def _ave(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        bico = self.bico_cor or Mat((60, 56, 60), 5, relevo=1.3, especular=(200, 200, 210))
        dobradica = L(0.045 * k, 0.012 * k)
        de_baixo = [girar(p, boca * 0.5, dobradica) for p in
                    L.pts([(0.04 * k, 0.005 * k), (0.05 * k + F * 0.92, 0.012 * k), (0.045 * k, 0.025 * k)])]
        if boca > 0.05:
            tela.chapado(tela.poly([L(0.05 * k, 0.005 * k), L(0.05 * k + F, 0.006 * k), de_baixo[1], dobradica]), BOCA)
        tela.pintar(tela.poly(de_baixo), bico.escuro(1))
        cranio = tela.elipse_girada(L(0.0, -0.01 * k), 0.06 * k * S, 0.05 * k * S, L.ang)
        m = tela.pintar(cranio, mat)
        T.penas(tela, m, L.b, eixo=-L.f, tam=2)
        if self.crista:
            T.franja(tela, m, L.b, (-1, -1), comp=3, espaco=1, inclina=-0.3, semente=semente)
        de_cima = L.pts([(0.03 * k, -0.025 * k), (0.05 * k + F * 0.7, -0.008 * k), (0.06 * k + F, 0.012 * k),
                         (0.045 * k + F * 0.8, 0.008 * k), (0.035 * k, 0.012 * k)])
        tela.pintar(tela.poly(de_cima), bico)
        tela.traco(L(0.04 * k, 0.006 * k), L(0.05 * k + F * 0.8, 0.008 * k), bico[0])
        self._olho(tela, L(0.025 * k, -0.02 * k), k, S, morto, rx=0.012, ry=0.012)
        return m

    # ----- réptil (salamandras, lagartos, dragões) -----
    def _reptil(self, tela, L, k, mat, boca, morto, fase, semente):
        S, F = L.S, self.focinho
        escuro = mat.escuro(1)
        dobradica = L(0.0, 0.022 * k)
        mandibula = [girar(p, boca * 0.65, dobradica) for p in
                     L.pts([(0.0, 0.015 * k), (0.06 * k + F, 0.016 * k), (0.05 * k + F * 0.9, 0.034 * k), (-0.01 * k, 0.04 * k)])]
        if boca > 0.05:
            tela.chapado(tela.poly([L(0.02 * k, 0.015 * k), L(0.065 * k + F, 0.01 * k), mandibula[1], dobradica]), BOCA)
        m1 = tela.pintar(tela.poly(mandibula), escuro)
        cabeca = tela.poly(L.pts([(-0.04 * k, -0.035 * k), (0.03 * k, -0.05 * k), (0.06 * k + F * 0.7, -0.03 * k),
                                  (0.07 * k + F, -0.005 * k), (0.065 * k + F, 0.012 * k), (-0.035 * k, 0.025 * k)]))
        m = tela.pintar(cabeca, mat)
        T.escamas(tela, m | m1, L.b, tam=2)
        self._dentes(tela, L(0.02 * k, 0.017 * k), L(0.06 * k + F, 0.013 * k), 5)
        if boca > 0.15:
            self._dentes(tela, lerp(mandibula[0], mandibula[1], 0.2), mandibula[1], 4, para_baixo=False)
        narina = L(0.06 * k + F, -0.012 * k)
        tela.px(narina[0], narina[1], (20, 10, 10))
        olho = L(0.03 * k, -0.025 * k)
        self._olho(tela, olho, k, S, morto, rx=0.016, ry=0.012)
        tela.pintar(tela.poly(L.pts([(0.0, -0.045 * k), (0.06 * k, -0.04 * k), (0.03 * k, -0.03 * k)])), escuro)  # arcada
        return m | m1

    # ----- inseto (besouros, louva-a-deus, aranhas) -----
    def _inseto(self, tela, L, k, mat, boca, morto, fase, semente):
        S = L.S
        cab = tela.elipse_girada(L(0.02 * k, 0.0), 0.05 * k * S, 0.042 * k * S, L.ang)
        for lado, abre in ((-1, -boca), (1, boca)):                                    # mandíbulas
            raiz = L(0.055 * k, 0.012 * k + lado * 0.006 * k)
            pts = [raiz, raiz + direcao(L.ang + 0.4 * lado + abre * 0.5 * lado) * (0.04 * k * S),
                   raiz + direcao(L.ang + 0.9 * lado + abre * 0.6 * lado) * (0.065 * k * S)]
            tela.pintar(tela.corrente(pts, [0.014 * k * S, 0.01 * k * S, 0.5]), Mat((70, 40, 30), 5, relevo=1.2) if lado > 0 else mat.escuro(2))
        m = tela.pintar(cab, mat)
        T.quitina(tela, m, L.b, eixo=L.f, espaco=6, brilho=0.4)
        olho = L(0.04 * k, -0.012 * k)                                                  # olho composto
        tela.chapado(tela.elipse(olho[0], olho[1], 0.024 * k * S, 0.02 * k * S), (30, 10, 14))
        if not morto:
            for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, -1)):
                tela.px(olho[0] + dx, olho[1] + dy, self.olho_cor, emite=True)
            tela.px(olho[0] - 1, olho[1] - 1, (255, 240, 220), emite=True)
            if self.olho_brilho:
                tela.brilho(olho, 4 * k, self.olho_cor, 0.6)
        if self.antena is None:
            return m
        for lado in (-1, 1):                                                            # antenas
            pts = [L(0.03 * k, -0.035 * k)]
            a = L.ang - 1.9 - lado * 0.25
            for i in range(4):
                a += 0.35 + math.sin(fase + i + lado) * 0.12
                pts.append(pts[-1] + direcao(a) * (0.035 * k * S))
            cor = mat[1] if lado < 0 else mat[3]
            tela.tracos(pts, cor)
            if self.antena == "pluma":                                                  # mariposa: penugem dos dois lados
                for a_, b_ in zip(pts[1:], pts[2:]):
                    d = (b_ - a_) / (np.linalg.norm(b_ - a_) or 1)
                    n = v2(-d[1], d[0])
                    for s in (-1, 1):
                        tela.traco(a_, a_ + (n * s - d * 0.4) * max(1.5, 0.02 * k * S), cor)
            elif self.antena == "clava":                                                # bolinha na ponta
                tela.chapado(tela.circulo(pts[-1], max(0.8, 0.012 * k * S)), cor)
        return m

    # ----- roedor (ratos, ratazanas) -----
    def _roedor(self, tela, L, k, mat, boca, morto, fase, semente):
        """Focinho fino e comprido, nariz rosado, bigodes e os dois dentes da frente amarelos."""
        S, F = L.S, self.focinho
        escuro = mat.escuro(1)
        self._orelha(tela, L, k, escuro, -0.03)
        dobradica = L(0.03 * k, 0.022 * k)
        mandibula = [girar(p, boca * 0.5, dobradica) for p in
                     L.pts([(0.03 * k, 0.018 * k), (0.05 * k + F * 0.8, 0.02 * k), (0.03 * k, 0.04 * k)])]
        if boca > 0.05:
            interior = [L(0.05 * k, 0.016 * k), L(0.06 * k + F * 0.85, 0.014 * k), mandibula[1], dobradica]
            tela.chapado(tela.poly(interior), BOCA)
        tela.pintar(tela.poly(mandibula), escuro)
        cranio = tela.elipse_girada(L(0.02 * k, -0.008 * k), 0.07 * k * S, 0.055 * k * S, L.ang)
        focinho = tela.poly(L.pts([(0.04 * k, -0.05 * k), (0.06 * k + F * 0.55, -0.03 * k), (0.07 * k + F, -0.006 * k),
                                   (0.066 * k + F, 0.008 * k), (0.05 * k + F * 0.5, 0.02 * k), (0.03 * k, 0.03 * k)]))
        m = cranio | focinho
        m |= T.tufos(tela, cranio, L.b, (-1, 1), comp=2, espaco=2, inclina=0.2, semente=semente)
        m = tela.pintar(m, mat)
        T.pelagem(tela, m, L.b, ang=L.ang + math.pi, comp=2, densidade=0.25, semente=semente)
        dente = L(0.064 * k + F * 0.9, 0.016 * k)                                       # incisivos
        tela.px(dente[0], dente[1], DENTE_ROEDOR)
        tela.px(dente[0], dente[1] + 1, misturar(DENTE_ROEDOR, (120, 90, 40), 0.3))
        if boca > 0.15:
            tela.px(mandibula[1][0] - 1, mandibula[1][1] - 1, DENTE_ROEDOR)
        nariz = L(0.072 * k + F, -0.004 * k)
        tela.chapado(tela.circulo(nariz, max(0.9, 0.01 * k * S)), ROSADO)
        if not morto:                                                                   # bigodes balançando
            raiz = L(0.06 * k + F * 0.8, 0.0)
            comp = max(3.0, 0.07 * k * S)
            for a in (-0.35, 0.0, 0.3):
                tela.traco(raiz, raiz + direcao(L.ang + a + 0.08 * math.sin(fase + a * 4)) * comp, BIGODE)
        self._olho(tela, L(0.058 * k, -0.03 * k), k, S, morto, rx=0.014, ry=0.012)
        self._orelha(tela, L, k, mat, 0.0)
        return m
