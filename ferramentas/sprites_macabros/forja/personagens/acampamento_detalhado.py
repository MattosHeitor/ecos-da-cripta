"""Objetos do acampamento refeitos com mais capricho (etapa 5, 2ª rodada): perspectiva 3/4 com faces de tons
próprios (frente, topo e lado), tábuas, ferragens, rebites, brilhos e sujeira — em vez do sombreado
"almofadado" do motor, que deixava as caixas arredondadas.

    fogueira          pedras facetadas, cabaninha de toras chamuscadas com brasas nas rachaduras, chaleira
    taverna_fundo     barraca de madeira com telhado de duas águas em telhas, frontão com a placa da caneca,
                      toldo listrado, prateleiras, presuntos, barris e caixotes
    taverna_balcao    balcão com tampo, painéis entalhados, barrilzinho com torneira, canecas, queijo, pão e vela
    estande_de_armas  cavalete com telhadinho: montante, alabarda, lança, machado de duas lâminas, escudos,
                      elmo com pluma e um barril de flechas
    bau_ornamentado   baú aberto em 3/4: forro de veludo na tampa, ouro e joias dentro, tecidos escapando
    carroca           carroça coberta: tábuas, arcos da lona com dobras, rodas raiadas (e as de trás), carga
    espelho_antigo    espelho de pé (psiqué): colunas com pináculos, moldura oval dourada e o vidro encantado
    barril, caixotes  em 3/4, com tampo à mostra

Os nomes são os mesmos das versões anteriores (cenario_acampamento.py continua lá, intacto).
"""
import math
import random

from ..motor import Mat, metal, v2, lerp
from .. import fx
from .cenario_acampamento import (ObjetoDeCena, lanterna, lingua_de_fogo, garrafa, tora, GARRAFAS, CASCA, CERNE, OURO,
                                  OURO_ESCURO, FERRO_BATIDO, ACO, COURO, MUSGO, BRASA)
from .herois import FERRO

# madeiras em três tons de face (luz de cima: topo claro, frente média, lado escuro)
TABUA = Mat((120, 80, 50), 6, ruido=0.25, dither=0.3)
TABUA_TOPO = Mat((150, 104, 66), 6, ruido=0.25, dither=0.3)
TABUA_LADO = Mat((84, 54, 36), 6, ruido=0.25, dither=0.3)
TABUA_ESCURA = Mat((70, 46, 34), 6, ruido=0.3, dither=0.3)
TELHA = Mat((100, 68, 54), 6, ruido=0.25)                       # telhas de madeira escurecidas pelo tempo
TELHA_LADO = Mat((72, 50, 42), 6, ruido=0.25)
PEDRA_FACE = Mat((104, 98, 110), 5, ruido=0.25)
PEDRA_TOPO = Mat((136, 130, 140), 5, ruido=0.2)
PEDRA_SOMBRA = Mat((70, 66, 80), 5, ruido=0.25)
LONA_CRUA = Mat((176, 160, 128), 6, ruido=0.14)                # a lona da carroça, encardida de estrada
VELUDO = Mat((150, 30, 48), 5, ruido=0.1)
CARVALHO = Mat((96, 62, 40), 6, ruido=0.35, dither=0.3, relevo=0.8)            # madeira gasta (baú, carroça, balcão)
CARVALHO_LADO = Mat((70, 44, 30), 6, ruido=0.35, dither=0.3)
CARVALHO_TOPO = Mat((118, 80, 52), 6, ruido=0.3, dither=0.3)
LATAO_VELHO = metal((150, 112, 54), especular=(240, 214, 150))


# ============================================================
# AJUDANTES DE DESENHO EM 3/4
# ============================================================

def face(tela, pts, mat, desce=0.0, nivel=0.0):
    """Polígono pintado chapado (sem volume), com degradê opcional de cima para baixo."""
    m = tela.poly([v2(p) for p in pts])
    tela.pintar(m, mat.copia(desce=desce) if desce else mat, plano=True, nivel=nivel)
    return m


def caixa(tela, x, base, larg, alt, prof, frente=TABUA, topo=TABUA_TOPO, lado=TABUA_LADO):
    """Caixa em 3/4 (o fundo sobe para a direita). Devolve as máscaras (frente, topo, lado) e o deslocamento."""
    d = v2(prof * 0.6, -prof * 0.5)
    f = [v2(x, base), v2(x + larg, base), v2(x + larg, base - alt), v2(x, base - alt)]
    t = [f[3], f[2], f[2] + d, f[3] + d]
    l = [f[1], f[1] + d, f[2] + d, f[2]]
    ml = face(tela, l, lado, desce=0.2)
    mt = face(tela, t, topo)
    return face(tela, f, frente, desce=0.15), mt, ml, d


def tabuas(tela, mask, x0, x1, y0, y1, passo, cor, horizontal=False, nos=True):
    """Divisões de tábua dentro da máscara (verticais ou horizontais) e alguns nós da madeira."""
    if horizontal:
        y = y0 + passo
        while y < y1:
            tela.traco(v2(x0, y), v2(x1, y), cor, sobre=True)
            y += passo
    else:
        x = x0 + passo
        while x < x1:
            tela.traco(v2(x, y0), v2(x, y1), cor, sobre=True)
            x += passo
    if nos:
        rng = random.Random(int(x0 * 31 + y0 * 17))                 # mesmos nós em todos os quadros
        for _ in range(int(abs(x1 - x0) * abs(y1 - y0) / 260)):
            p = v2(rng.uniform(x0 + 2, x1 - 2), rng.uniform(y0 + 2, y1 - 2))
            if mask[int(p[1]) % mask.shape[0], int(p[0]) % mask.shape[1]]:
                tela.px(p[0], p[1], cor)
                tela.px(p[0] + 1, p[1], cor)


def rebites(tela, a, b, n, cor=(206, 200, 214)):
    for k in range(n):
        p = lerp(v2(a), v2(b), (k + 0.5) / n)
        tela.px(p[0], p[1], cor)


def lamina(tela, base, ponta, largura, cor=(178, 182, 196), fio=True):
    """Lâmina chata: metade de cima mais clara, sulco escuro no meio, fio brilhante e ponta."""
    base, ponta = v2(base), v2(ponta)
    d = ponta - base
    comp = math.hypot(*d) or 1
    u = d / comp
    n = v2(-u[1], u[0])
    corpo = [base + n * largura, ponta - u * largura * 1.4 + n * largura * 0.9, ponta,
             ponta - u * largura * 1.4 - n * largura * 0.9, base - n * largura]
    tela.chapado(tela.poly(corpo), cor)
    clara = tuple(min(255, int(c * 1.22)) for c in cor)
    tela.chapado(tela.poly([base, base + n * largura, ponta - u * largura * 1.4 + n * largura * 0.9, ponta]), clara)
    tela.traco(base + u * 2, ponta - u * largura * 2.5, tuple(int(c * 0.62) for c in cor))
    if fio:
        tela.traco(base + n * largura, ponta - u * largura * 1.4 + n * largura * 0.9, (250, 252, 255))
    return tela.poly(corpo)


def rocha(tela, centro, rx, ry, rng, quente=0.0, musgo=False, mat=PEDRA_FACE):
    """Pedra facetada: corpo, faceta de cima clara, base escura e (quente) o lado do fogo alaranjado."""
    c = v2(centro)
    pts = []
    for k in range(7):
        a = k * 2 * math.pi / 7 + rng.uniform(-0.25, 0.25)
        r = rng.uniform(0.85, 1.12)
        pts.append(c + v2(math.cos(a) * rx * r, math.sin(a) * ry * r))
    corpo = face(tela, pts, mat)
    topo = tela.poly([p for p in pts if p[1] < c[1] + ry * 0.1] + [c + v2(rx * 0.5, -ry * 0.05), c + v2(-rx * 0.6, 0)])
    tela.pintar(corpo & topo, PEDRA_TOPO, plano=True)
    tela.pintar(corpo & tela.elipse(c[0] + rx * 0.2, c[1] + ry * 0.75, rx * 1.1, ry * 0.5), PEDRA_SOMBRA, plano=True)
    tela.traco(c + v2(-rx * 0.55, -ry * 0.62), c + v2(rx * 0.3, -ry * 0.85), (176, 172, 180), sobre=True)
    if musgo:
        tela.chapado(corpo & tela.elipse(c[0] - rx * 0.3, c[1] - ry * 0.7, rx * 0.6, ry * 0.35), MUSGO)
        tela.px(c[0] - rx * 0.4, c[1] - ry * 0.9, (96, 128, 76))
    if quente:
        tela.tingir(corpo & tela.elipse(c[0], c[1] + ry * 0.4, rx * 0.95, ry * 0.7), (255, 140, 60), quente)
    return corpo


def barril_3d(tela, base, raio, alt, tampo=True):
    """Barril em 3/4: aduelas com volume, aros de ferro, e o tampo elíptico com as tábuas à mostra."""
    cx, chao = base
    corpo = tela.poly([v2(cx - raio * 0.86, chao - 1), v2(cx - raio, chao - alt * 0.5), v2(cx - raio * 0.86, chao - alt + 2),
                       v2(cx + raio * 0.86, chao - alt + 2), v2(cx + raio, chao - alt * 0.5), v2(cx + raio * 0.86, chao - 1)])
    corpo |= tela.elipse(cx, chao - 1, raio * 0.86, raio * 0.3)
    tela.pintar(corpo, Mat((136, 92, 56), 6, ruido=0.25, relevo=1.1, arredonda=1.6))
    for k in range(-2, 3):
        x = cx + k * raio * 0.36
        tela.traco(v2(x * 0.98 + cx * 0.02, chao - alt + 3), v2(x, chao - 2), (92, 60, 38), sobre=True)
    for t in (0.14, 0.4, 0.62, 0.88):
        y = chao - alt * t
        largura = raio * (0.88 + 0.12 * math.sin(math.pi * t))
        tela.pintar(tela.elipse(cx, y, largura, raio * 0.22) & ~tela.elipse(cx, y - 1.6, largura, raio * 0.22) & corpo,
                    FERRO_BATIDO, plano=True)
    if tampo:
        topo = tela.elipse(cx, chao - alt + 2, raio * 0.86, raio * 0.3)
        tela.pintar(topo, Mat((160, 116, 72), 5, ruido=0.2), plano=True)
        for k in (-1, 0, 1):
            tela.traco(v2(cx + k * raio * 0.3 - 1, chao - alt + 2 - raio * 0.22), v2(cx + k * raio * 0.3 + 1, chao - alt + 2 + raio * 0.22),
                       (110, 76, 46), sobre=True)
        tela.chapado(topo & ~tela.elipse(cx, chao - alt + 2, raio * 0.86 - 1.4, raio * 0.3 - 1), (84, 82, 94))
    return corpo


# ============================================================
# FOGUEIRA
# ============================================================

class Fogueira(ObjetoDeCena):
    nome = "fogueira"
    S = 64
    proporcao = (2.4, 2.6)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        c = v2(cx, chao - 0.16 * S)
        f = P["fase"]
        rng = tela.random
        rng.seed(7)
        rx, ry = 0.74 * S, 0.19 * S
        # chão chamuscado, cinza e a cama de brasas
        tela.chapado(tela.elipse(c[0], c[1] + 0.04 * S, 0.98 * S, 0.24 * S), (32, 24, 24))
        tela.chapado(tela.elipse(c[0], c[1] + 0.02 * S, 0.62 * S, 0.15 * S), (66, 58, 60))
        tela.chapado(tela.elipse(c[0], c[1], 0.5 * S, 0.12 * S) & (tela.bayer > 0), (90, 82, 82))
        # pedras de trás (a face de dentro, virada para o fogo, fica laranja)
        for k in range(8):
            a = math.pi + (k + 0.5) / 8 * math.pi
            rocha(tela, c + v2(math.cos(a) * rx, math.sin(a) * ry), 0.11 * S, 0.075 * S, rng, quente=0.4, musgo=k == 5)
        tela.chapado(tela.elipse(c[0], c[1] - 0.01 * S, 0.44 * S, 0.1 * S), (100, 30, 16), emite=True)
        tela.chapado(tela.elipse(c[0], c[1] - 0.02 * S, 0.34 * S, 0.075 * S), (210, 80, 26), emite=True)
        tela.chapado(tela.elipse(c[0], c[1] - 0.025 * S, 0.2 * S, 0.045 * S), (255, 176, 70), emite=True)
        for k in range(18):
            p = c + v2(rng.uniform(-0.38, 0.38) * S, rng.uniform(-0.07, 0.04) * S)
            tela.px(p[0], p[1], (255, 230, 150) if (P["i"] + k) % 3 else (120, 34, 20), emite=True)
        # cabaninha de toras: as de trás antes do fogo, as da frente depois
        topo = c + v2(0, -0.66 * S)
        angulos = [math.pi * (1.1 + 0.16 * k) for k in range(6)]
        toras = []
        for k, a in enumerate(angulos):
            pe = c + v2(math.cos(a) * 0.46 * S, math.sin(a) * 0.12 * S + 0.02 * S)
            ponta = topo + v2((k - 2.5) * 1.6, rng.uniform(-2, 2))
            toras.append((pe, ponta, math.sin(a) < 0))
        meio = c + v2(0, -0.3 * S)                                 # as da frente são curtas: o fogo cobre o resto
        toras += [(c + v2(-0.46 * S, 0.06 * S), meio + v2(-0.12 * S, 0.02 * S), False), (c + v2(0.46 * S, 0.07 * S), meio + v2(0.12 * S, 0.03 * S), False),
                  (c + v2(-0.08 * S, 0.12 * S), meio + v2(0.02 * S, 0.06 * S), False)]

        def tora_queimada(pe, ponta, frente):
            r = (0.072 if frente else 0.058) * S
            m = tela.capsula(pe, ponta, r, r * 0.8)
            tela.pintar(m, CASCA)
            d = ponta - pe
            comp = math.hypot(*d) or 1
            n = v2(-d[1], d[0]) / comp
            tela.traco(pe + n * r * 0.5, ponta + n * r * 0.4, CASCA[4], sobre=True)
            for k in range(int(comp / 5)):                           # riscos da casca
                p = lerp(pe, ponta, (k + 0.5) / max(1, int(comp / 5)))
                tela.traco(p - n * r * 0.4, p + n * r * 0.1, CASCA[0], sobre=True)
            queimado = m & tela.capsula(lerp(pe, ponta, 0.45), ponta, r * 1.3)
            tela.tingir(queimado, (34, 24, 24), 0.75)
            for k in range(4):                                     # brasa nas rachaduras do carvão
                p = lerp(pe, ponta, 0.55 + k * 0.1) + n * rng.uniform(-r * 0.5, r * 0.5)
                tela.px(p[0], p[1], (255, 140, 50), emite=True)
                tela.px(p[0] + 1, p[1], (255, 90, 30), emite=True)
            if frente:
                tela.pintar(tela.elipse_girada(pe, r * 0.55, r * 1.0, math.atan2(d[1], d[0])), CERNE, plano=True)
                tela.chapado(tela.elipse_girada(pe, r * 0.25, r * 0.5, math.atan2(d[1], d[0])), CERNE[1])

        for pe, ponta, atras in toras:
            if atras:
                tora_queimada(pe, ponta, False)
        linguas = ((-0.3, 0.5, 0.24, -0.35, 1.3), (0.3, 0.56, 0.24, 0.3, 2.2), (-0.14, 0.84, 0.3, -0.15, 0.4),
                   (0.15, 0.92, 0.3, 0.12, 3.1), (0.0, 1.2, 0.36, 0.0, 0.0), (0.0, 0.62, 0.18, 0.0, 1.7))
        for dx, alto, largo, inclina, atraso in linguas:
            altura = S * alto * (1 + 0.08 * math.sin(f * 2 + atraso * 2))
            lingua_de_fogo(tela, c + v2(dx * S, -0.08 * S), altura, S * largo, f + atraso, inclina)
        for k in range(3):                                         # fiapos de chama soltos subindo
            t = (P["i"] / 4 + k / 3) % 1
            p = c + v2(math.sin(k * 2.1 + f) * 0.12 * S, -1.05 * S - t * 0.3 * S)
            tela.chapado(tela.elipse(p[0], p[1], 1.4, 2.6 * (1 - t) + 0.6), fx.FOGO[2], emite=True)
        for pe, ponta, atras in toras:
            if not atras:
                tora_queimada(pe, ponta, True)
        for k in range(10):                                        # faíscas
            t = (P["i"] / 4 + k / 10) % 1
            p = c + v2(math.sin(k * 2.3 + f + t * 4) * 0.34 * S, -1.15 * S - t * 0.5 * S)
            tela.px(p[0], p[1], fx.FOGO[3 if k % 2 else 2], emite=True)
        # pedras da frente, maiores
        for k in range(9):
            a = (k + 0.5) / 9 * math.pi
            rocha(tela, c + v2(math.cos(a) * rx * 1.04, math.sin(a) * ry + 0.03 * S), (0.13 + 0.02 * (k % 3)) * S,
                  0.09 * S, rng, quente=0.3, musgo=k in (1, 6))
        # chaleira de ferro esquentando numa pedra ao lado
        ch = c + v2(0.84 * S, 0.02 * S)
        rocha(tela, ch + v2(0, 3), 0.1 * S, 0.06 * S, rng)
        corpo = tela.elipse(ch[0], ch[1] - 0.12 * S, 0.11 * S, 0.1 * S)
        tela.pintar(corpo, FERRO_BATIDO)
        tela.pintar(tela.elipse(ch[0], ch[1] - 0.21 * S, 0.06 * S, 0.02 * S), FERRO.claro(1))
        tela.pintar(tela.capsula(ch + v2(-0.1 * S, -0.12 * S), ch + v2(-0.17 * S, -0.19 * S), 1.2), FERRO_BATIDO)
        tela.tracos([ch + v2(-0.08 * S, -0.2 * S), ch + v2(0, -0.29 * S), ch + v2(0.08 * S, -0.2 * S)], FERRO[3])
        for k in range(3):
            t = (P["i"] / 4 + k / 3) % 1
            p = ch + v2(-0.18 * S + math.sin(t * 5) * 1.5, -0.22 * S - t * 0.3 * S)
            tela.px(p[0], p[1], (200, 196, 210) if t < 0.6 else (130, 126, 140))
        tela.brilho(c + v2(0, -0.4 * S), 0.95 * S, (255, 150, 60), 0.35)


# ============================================================
# BARRACA DA TAVERNA (fundo) E BALCÃO (frente)
# ============================================================

class BarracaDaTaverna(ObjetoDeCena):
    nome = "taverna_fundo"
    S = 66
    proporcao = (3.5, 2.4)

    def geometria(self):
        S = self.S
        cx, chao = self.ancora
        L = 1.0 * S
        d = v2(0.24 * S, -0.16 * S)
        beiral = chao - 1.28 * S
        return S, cx, chao, L, d, beiral

    def desenhar(self, tela, ctx, P):
        S, cx, chao, L, d, beiral = self.geometria()
        f = P["fase"]
        esq, dir_ = cx - L, cx + L
        # parede do fundo: tábuas deitadas, escuras, com nós
        fundo = [v2(esq, chao) + d, v2(dir_, chao) + d, v2(dir_, beiral) + d, v2(esq, beiral) + d]
        m = face(tela, fundo, TABUA_ESCURA, desce=0.25)
        tabuas(tela, m, esq + d[0], dir_ + d[0], beiral + d[1], chao + d[1], 6, TABUA_ESCURA[0], horizontal=True)
        # parede da direita (meia altura) e o chão de tábuas da barraca
        lado = [v2(dir_, chao), v2(dir_, chao) + d, v2(dir_, chao - 0.62 * S) + d, v2(dir_, chao - 0.62 * S)]
        ml = face(tela, lado, TABUA_LADO, desce=0.2)
        tabuas(tela, ml, dir_, dir_ + d[0], chao - 0.62 * S + d[1], chao, 4, TABUA_LADO[0])
        # prateleiras com garrafas, potes e um queijo; presuntos e ervas pendurados
        for n, y in enumerate((chao - 0.56 * S + d[1], chao - 0.84 * S + d[1])):
            prat = face(tela, [v2(esq + d[0] + 6, y), v2(dir_ + d[0] - 6, y), v2(dir_ + d[0] - 6, y + 2.5), v2(esq + d[0] + 6, y + 2.5)],
                        TABUA_TOPO)
            for lado_ in (-1, 1):
                x = cx + d[0] + lado_ * 0.6 * S
                tela.traco(v2(x, y + 3), v2(x + lado_ * 3, y + 7), TABUA_ESCURA[2])
            x = esq + d[0] + 12
            k = 0
            while x < dir_ + d[0] - 12:
                if n == 0 and k == 4:
                    tela.pintar(tela.elipse(x + 3, y - 3, 5, 3), Mat((230, 190, 90), 5), plano=True)       # queijo
                    tela.chapado(tela.poly([v2(x + 3, y - 3), v2(x + 8, y - 5), v2(x + 8, y - 2)]), (250, 220, 130))
                    x += 12
                elif n == 1 and k % 5 == 2:
                    pote = tela.poly([v2(x - 3, y), v2(x + 3, y), v2(x + 3.5, y - 6), v2(x - 3.5, y - 6)])
                    tela.pintar(pote, Mat((150, 100, 70), 5, relevo=1.0))
                    tela.chapado(tela.elipse(x, y - 6.5, 3.6, 1.2), (200, 180, 140))
                    x += 9
                else:
                    cor, tipo = GARRAFAS[(k + n * 3) % len(GARRAFAS)]
                    garrafa(tela, v2(x, y - 0.5), cor, tipo, 0.9 + 0.15 * ((k * 3 + n) % 3))
                    x += 8 + (k % 2) * 2
                k += 1
        # viga de cima com presunto, linguiças e maços de ervas
        viga_y = beiral + 0.1 * S
        tela.pintar(tela.capsula(v2(esq, viga_y) + d * 0.5, v2(dir_, viga_y) + d * 0.5, 2.2), TABUA)
        for k in range(7):
            x = esq + 20 + k * (2 * L - 40) / 6 + d[0] * 0.5
            y = viga_y + d[1] * 0.5
            balanco = math.sin(f + k) * 0.8
            if k == 3:                                             # presunto
                tela.traco(v2(x, y), v2(x + balanco, y + 4), (150, 130, 90))
                tela.pintar(tela.elipse(x + balanco, y + 10, 4, 6.5), Mat((160, 80, 64), 5, relevo=1.2))
                tela.chapado(tela.elipse(x + balanco, y + 15, 2, 1.4), (230, 210, 190))
            elif k % 2:
                for j in range(3):
                    tela.pintar(tela.capsula(v2(x + balanco * j * 0.4, y + 3 + j * 4.5), v2(x + balanco * (j + 1) * 0.4, y + 6 + j * 4.5), 1.6),
                                Mat((150, 70, 60), 4, relevo=1.2))
            else:
                tela.traco(v2(x, y), v2(x + balanco, y + 4), (150, 130, 90))
                for j in range(5):
                    tela.traco(v2(x + balanco, y + 4), v2(x + balanco + (j - 2) * 1.2, y + 11), (80 + j * 8, 120, 60))
        # postes (os da frente e o de trás à direita) com sapatas de pedra
        for x, desl in ((dir_, d), (esq, v2(0, 0)), (dir_, v2(0, 0))):
            base = v2(x, chao) + desl
            tela.pintar(tela.poly([base + v2(-3.5, 0), base + v2(3.5, 0), base + v2(3.5, beiral - chao - 2), base + v2(-3.5, beiral - chao - 2)]),
                        TABUA, plano=True)
            tela.traco(base + v2(-3.5, -1), base + v2(-3.5, beiral - chao), TABUA[4])
            rocha(tela, base + v2(0, -1.5), 6, 3.2, random.Random(int(x * 7 + desl[0])), musgo=True)      # sapata de pedra
        # telhado de duas águas em telhas, com o frontão virado para a frente
        cume = v2(cx, beiral - 0.66 * S)
        aba_e, aba_d = v2(esq - 0.18 * S, beiral + 3), v2(dir_ + 0.18 * S, beiral + 3)
        agua_d = [cume, aba_d, aba_d + d * 1.6, cume + d * 1.6]
        agua_e = [aba_e, cume, cume + d * 1.6, aba_e + d * 1.6]
        for pts, mat in ((agua_e, TELHA), (agua_d, TELHA_LADO)):
            m = face(tela, pts, mat)
            for k in range(1, 7):                                  # fileiras de telhas
                a, b = lerp(pts[0], pts[1], k / 7), lerp(pts[3], pts[2], k / 7)
                tela.traco(a, b, mat[0], sobre=True)
                for j in range(5):
                    p = lerp(a, b, (j + 0.5 * (k % 2)) / 5)
                    q = lerp(lerp(pts[0], pts[1], (k - 1) / 7), lerp(pts[3], pts[2], (k - 1) / 7), (j + 0.5 * (k % 2)) / 5)
                    tela.traco(p, q, mat[1], sobre=True)
        rng = random.Random(66)                                    # musgo nas telhas (o mesmo em todos os quadros)
        for _ in range(9):
            t, s = rng.uniform(0.15, 0.95), rng.uniform(0.0, 0.9)
            pts = agua_e if rng.random() < 0.5 else agua_d
            p = lerp(lerp(pts[0], pts[1], t), lerp(pts[3], pts[2], t), s)
            tela.chapado(tela.elipse(p[0], p[1], rng.uniform(2.5, 4.5), rng.uniform(1.2, 2.0)) & tela.poly(pts),
                         MUSGO if rng.random() < 0.6 else (44, 64, 44))
        frontao = [aba_e + v2(4, -1), cume + v2(0, 4), aba_d + v2(-4, -1)]
        mf = face(tela, frontao, Mat((150, 132, 108), 5, ruido=0.25), desce=0.4)     # reboco entre as vigas
        for a, b in ((aba_e + v2(10, -2), cume + v2(0, 10)), (cume + v2(0, 10), aba_d + v2(-10, -2)),     # enxaimel: as vigas
                     (lerp(aba_e, cume, 0.5) + v2(4, 2), aba_d + v2(-18, -2)), (lerp(cume, aba_d, 0.5) + v2(-4, 2), aba_e + v2(18, -2)),
                     (cume + v2(0, 6), v2(cx, beiral - 1))):
            tela.pintar(tela.capsula(a, b, 1.5) & mf, TABUA_ESCURA, plano=True)
        tela.pintar(tela.capsula(v2(aba_e[0] + 6, beiral - 1), v2(aba_d[0] - 6, beiral - 1), 1.8), TABUA_ESCURA)
        for a, b in ((aba_e, cume), (cume, aba_d)):                 # testeiras entalhadas
            tela.pintar(tela.capsula(a, b, 2.2), TABUA_TOPO)
            tela.traco(a + v2(0, -1.5), b + v2(0, -1.5), TABUA_TOPO[5], sobre=True)
        tela.pintar(tela.capsula(cume, cume + v2(0, -6), 1.3), FERRO_BATIDO)
        tela.pintar(tela.circulo(cume + v2(0, -7), 1.8), FERRO_BATIDO)
        # a placa da caneca, pendurada num braço de ferro preso no poste da direita (balança de leve)
        self.placa_da_caneca(tela, v2(dir_ + 2, beiral - 0.02 * S), f)
        # toldo listrado debaixo do beiral, com barra recortada e debrum dourado
        topo_t, baixo_t = beiral + 2, beiral + 0.2 * S
        recorte = []
        for k in range(19):
            x = esq - 0.12 * S + k * (2 * L + 0.24 * S) / 18
            recorte.append(v2(x, baixo_t + (6 if k % 2 else 0)))
        toldo = tela.poly([v2(esq - 0.12 * S, topo_t), v2(dir_ + 0.12 * S, topo_t)] + list(reversed(recorte)))
        tela.pintar(toldo, Mat((124, 42, 40), 6, ruido=0.12), plano=True)
        for k in range(9):
            x0 = esq - 0.12 * S + (2 * k + 1) * (2 * L + 0.24 * S) / 18
            faixa = tela.poly([v2(x0 - 4, topo_t), v2(x0 + 4, topo_t), v2(x0 + 6, baixo_t + 6), v2(x0 - 6, baixo_t + 6)]) & toldo
            tela.pintar(faixa, Mat((190, 176, 146), 6, ruido=0.12), plano=True)
        tela.traco(v2(esq - 0.12 * S, topo_t + 2), v2(dir_ + 0.12 * S, topo_t + 2), (60, 20, 24), sobre=True)
        tela.tracos(recorte, (226, 182, 86), sobre=True)
        for k in range(10):                                        # luzinhas na barra do toldo
            p = lerp(v2(esq - 4, baixo_t + 10), v2(dir_ + 4, baixo_t + 10), (k + 0.5) / 10) + v2(0, math.sin((k + 0.5) / 10 * math.pi) * 4)
            acesa = (k + P["i"]) % 3 != 0
            tela.chapado(tela.circulo(p, 1.3), (255, 214, 120) if acesa else (170, 110, 60), emite=True)
        for x in (esq - 0.04 * S, dir_ + 0.04 * S):
            lanterna(tela, v2(x, baixo_t + 4), f + x)
        # barris empilhados à esquerda e caixotes com garrafas à direita
        for x, y in ((esq - 0.36 * S, chao), (esq - 0.08 * S, chao + 2)):
            barril_3d(tela, v2(x, y), 0.16 * S, 0.42 * S)
        barril_3d(tela, v2(esq - 0.22 * S, chao - 0.42 * S), 0.15 * S, 0.38 * S)
        cx_c = dir_ + 0.32 * S
        caixa(tela, cx_c - 0.18 * S, chao + 2, 0.36 * S, 0.26 * S, 0.2 * S)
        caixa(tela, cx_c - 0.12 * S, chao + 2 - 0.26 * S, 0.26 * S, 0.2 * S, 0.16 * S)
        for k in range(3):
            cor, tipo = GARRAFAS[k + 1]
            garrafa(tela, v2(cx_c - 0.08 * S + k * 4.5, chao - 0.46 * S - 2), cor, "alta", 0.75)
        tela.pintar(tela.elipse(cx_c + 0.24 * S, chao - 0.06 * S, 0.11 * S, 0.09 * S), Mat((196, 166, 112), 5, relevo=0.9))


    def placa_da_caneca(self, tela, raiz, f):
        """Braço de ferro saindo da quina do telhado, com a mão-francesa embaixo, e a tábua da caneca pendurada em
        duas correntinhas (balança devagar)."""
        S = self.S
        braco = raiz + v2(0.42 * S, 0)
        tela.pintar(tela.capsula(raiz, braco, 1.2), FERRO_BATIDO)
        tela.tracos([raiz + v2(0, 0.16 * S), raiz + v2(0.12 * S, 0.06 * S), raiz + v2(0.24 * S, 0.01 * S)], FERRO_BATIDO[2])
        tela.pintar(tela.circulo(braco, 1.4), FERRO_BATIDO)
        balanco = math.sin(f) * 0.9
        w, h = 0.3 * S, 0.24 * S
        topo = raiz + v2(0.07 * S + balanco, 0.07 * S)
        for x in (0.05 * S, w - 0.05 * S):                        # correntinhas
            tela.traco(raiz + v2(0.07 * S + x, 1), topo + v2(x, 0), (110, 106, 118))
        tabua = [topo, topo + v2(w, 0), topo + v2(w, h), topo + v2(0, h)]
        tela.pintar(tela.poly(tabua), Mat((84, 56, 40), 5, ruido=0.3), plano=True)
        tela.tracos(tabua + [tabua[0]], (46, 30, 24))
        m = topo + v2(w * 0.44, h * 0.56)
        caneca = tela.poly([m + v2(-4, -4), m + v2(3, -4), m + v2(3, 5), m + v2(-4, 5)])
        tela.chapado(caneca, (206, 160, 70))
        tela.chapado(tela.capsula(m + v2(3, -2), m + v2(6, 2), 1.2) & ~caneca, (186, 140, 60))
        tela.chapado(tela.elipse(m[0] - 0.5, m[1] - 5, 4.6, 1.6), (238, 230, 210))
        tela.traco(m + v2(-4, -1), m + v2(3, -1), (150, 110, 50))


class BalcaoDaTaverna(BarracaDaTaverna):
    """O balcão da frente (por cima do Taverneiro): tampo grosso de tábua apoiado em dois barris, frente de tábuas na
    vertical com cintas de ferro, e em cima o barril de chope com torneira, canecas, comida e a vela."""
    nome = "taverna_balcao"

    def desenhar(self, tela, ctx, P):
        S, cx, chao, L, d, beiral = self.geometria()
        x0, largura, altura = cx - 0.92 * S, 1.84 * S, 0.44 * S
        dd = v2(0.22 * S * 0.6, -0.22 * S * 0.5)
        # a frente de tábuas na vertical, entre os dois barris, com duas cintas de ferro
        ini, fim = x0 + 0.2 * S, x0 + largura - 0.2 * S
        frente = face(tela, [v2(ini, chao), v2(fim, chao), v2(fim, chao - altura + 3), v2(ini, chao - altura + 3)],
                      CARVALHO, desce=0.3)
        tabuas(tela, frente, ini, fim, chao - altura + 3, chao, 0.1 * S, CARVALHO[0])
        for y in (chao - altura * 0.28, chao - altura * 0.74):
            tela.pintar(tela.poly([v2(ini, y - 1.5), v2(fim, y - 1.5), v2(fim, y + 1.5), v2(ini, y + 1.5)]), FERRO_BATIDO, plano=True)
            rebites(tela, v2(ini + 3, y), v2(fim - 3, y), 9)
        tela.tingir(frente & tela.poly([v2(ini, chao), v2(fim, chao), v2(fim, chao - 4), v2(ini, chao - 4)]), (40, 30, 26), 0.4)
        for x in (x0 + 0.1 * S, x0 + largura - 0.1 * S):            # os dois barris que seguram o tampo
            barril_3d(tela, v2(x, chao), 0.13 * S, altura - 2, tampo=False)
        # o tampo: uma tábua grossa, com o fio da frente gasto e a espessura à mostra
        y = chao - altura
        tampo = [v2(x0 - 3, y + 2), v2(x0 + largura + 3, y + 2), v2(x0 + largura + 3, y + 2) + dd, v2(x0 - 3, y + 2) + dd]
        face(tela, tampo, CARVALHO_TOPO)
        tela.pintar(tela.poly([v2(x0 - 3, y + 2), v2(x0 + largura + 3, y + 2), v2(x0 + largura + 3, y + 5), v2(x0 - 3, y + 5)]),
                    CARVALHO, plano=True)
        tela.traco(v2(x0 - 3, y + 2), v2(x0 + largura + 3, y + 2), CARVALHO_TOPO[5])
        for k in range(1, 3):                                       # emendas do tampo
            tela.traco(v2(x0 - 3, y + 2) + dd * (k / 3), v2(x0 + largura + 3, y + 2) + dd * (k / 3), CARVALHO_TOPO[1], sobre=True)
        # pano xadrez caído na ponta
        pano = face(tela, [v2(x0 + 3, y), v2(x0 + 17, y), v2(x0 + 15, y + 15), v2(x0 + 5, y + 13)], Mat((170, 60, 50), 5))
        for k in range(3):
            tela.traco(v2(x0 + 5 + k * 4, y + 1), v2(x0 + 6 + k * 4, y + 13), (220, 200, 170), sobre=True)
        tela.traco(v2(x0 + 4, y + 6), v2(x0 + 16, y + 7), (220, 200, 170), sobre=True)
        # barrilzinho deitado com torneira
        b = v2(x0 + 0.36 * S, y + dd[1] * 0.4)
        tela.pintar(tela.capsula(b + v2(-8, -6), b + v2(8, -6), 6.5), Mat((140, 94, 58), 6, relevo=1.1))
        for dx in (-5, 5):
            tela.traco(b + v2(dx, -12), b + v2(dx, 0), FERRO[2], sobre=True)
        tela.pintar(tela.elipse(b[0] + 9, b[1] - 6, 2.5, 6), Mat((170, 120, 76), 5), plano=True)
        tela.pintar(tela.capsula(b + v2(11, -4), b + v2(13, -1), 1.0), OURO)
        tela.pintar(tela.capsula(b + v2(-6, 0), b + v2(-4, 1), 1.2) | tela.capsula(b + v2(6, 0), b + v2(4, 1), 1.2), TABUA_ESCURA)
        # canecas com espuma, queijo, pão e garrafa
        for x in (x0 + 0.66 * S, x0 + 0.82 * S, x0 + 1.3 * S):
            yy = y + dd[1] * 0.3
            tela.pintar(tela.poly([v2(x - 4, yy), v2(x + 4, yy), v2(x + 4, yy - 10), v2(x - 4, yy - 10)]), Mat((112, 76, 50), 5), plano=True)
            tela.traco(v2(x - 4, yy - 3), v2(x + 4, yy - 3), FERRO[2], sobre=True)
            tela.traco(v2(x - 4, yy - 8), v2(x + 4, yy - 8), FERRO[2], sobre=True)
            tela.pintar(tela.capsula(v2(x + 5, yy - 8), v2(x + 5, yy - 3), 1.2), Mat((112, 76, 50), 5))
            tela.chapado(tela.elipse(x, yy - 11, 4.8, 2.0), (252, 244, 226))
            tela.px(x + 3, yy - 9, (252, 244, 226))
        q = v2(x0 + 1.05 * S, y + dd[1] * 0.5)
        tela.pintar(tela.elipse(q[0], q[1] - 3, 7, 3.5), Mat((226, 186, 84), 5), plano=True)
        tela.chapado(tela.poly([q + v2(0, -3), q + v2(7, -4), q + v2(7, 0), q + v2(0, 1)]), (250, 222, 130))
        tela.chapado(tela.elipse(q[0] - 2, q[1] - 5, 3.2, 1.2), (250, 222, 130))
        pao = v2(x0 + 1.5 * S, y + dd[1] * 0.4)
        tela.pintar(tela.elipse(pao[0], pao[1] - 3, 7, 3.5), Mat((196, 140, 76), 5, relevo=1.2))
        for k in (-3, 0, 3):
            tela.traco(pao + v2(k - 1, -5), pao + v2(k + 1, -3), (240, 210, 150), sobre=True)
        garrafa(tela, v2(x0 + 1.18 * S, y + dd[1] * 0.2), (70, 120, 70), "alta")
        vela = v2(x0 + largura - 0.14 * S, y + dd[1] * 0.4)
        tela.pintar(tela.elipse(vela[0], vela[1], 3.5, 1.2), metal((170, 140, 70)))
        tela.pintar(tela.capsula(vela, vela + v2(0, -8), 1.7), Mat((236, 226, 196), 4))
        tela.chapado(tela.poly([vela + v2(1.5, -6), vela + v2(2.2, -3), vela + v2(1.2, -4)]), (236, 226, 196))
        fx.chama(tela, vela + v2(0, -9), 5.5, 3, fase=P["fase"] * 2, brilho=False)
        tela.brilho(vela + v2(0, -11), 11, (255, 190, 100), 0.6)


# ============================================================
# ESTANDE DE ARMAS (o Arsenal)
# ============================================================

class EstandeDeArmas(ObjetoDeCena):
    """O Arsenal: um armeiro de campanha. À esquerda, um manequim de madeira com couraça, ombreira, elmo e tabardo;
    no meio, o cavalete (dois pés em "A" e a travessa) com as armas de haste encostadas e as espadas de ponta para
    baixo num cepo de encaixes; à direita, escudos encostados e um barril de flechas com um arco."""
    nome = "estande_de_armas"
    S = 48
    proporcao = (2.8, 2.5)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        tela.chapado(tela.elipse(cx, chao + 1, 1.3 * S, 0.1 * S), (14, 10, 14))
        cabo = Mat((92, 60, 40), 5, relevo=0.9)
        travessa_y = chao - 1.22 * S
        # os pés em "A" do cavalete e a travessa de cima (as armas encostam nela pela frente)
        for x in (cx - 0.5 * S, cx + 0.5 * S):
            for lado in (-1, 1):
                tela.pintar(tela.capsula(v2(x, travessa_y - 2), v2(x + lado * 0.13 * S, chao - 1), 2.0), TABUA)
            tela.pintar(tela.capsula(v2(x - 0.09 * S, chao - 0.35 * S), v2(x + 0.09 * S, chao - 0.35 * S), 1.3), TABUA_ESCURA)
        tela.pintar(tela.capsula(v2(cx - 0.66 * S, travessa_y), v2(cx + 0.66 * S, travessa_y), 2.6), TABUA_TOPO)
        for k in range(6):                                           # encaixes na travessa
            tela.chapado(tela.elipse(cx - 0.42 * S + k * 0.17 * S, travessa_y - 1.5, 1.5, 0.8), TABUA_ESCURA[0])
        # armas de haste encostadas: alabarda, lança com borla, glaive e uma lança curta
        self.alabarda(tela, v2(cx - 0.52 * S, chao - 1), v2(cx - 0.3 * S, chao - 1.74 * S), cabo)
        self.lanca(tela, v2(cx - 0.32 * S, chao - 1), v2(cx - 0.08 * S, chao - 1.88 * S), cabo, f)
        self.glaive(tela, v2(cx - 0.08 * S, chao - 1), v2(cx + 0.14 * S, chao - 1.68 * S), cabo)
        self.lanca(tela, v2(cx + 0.14 * S, chao - 1), v2(cx + 0.36 * S, chao - 1.56 * S), cabo, f + 1.3, borla=False)
        # o cepo das espadas, na frente: três espadas de ponta para baixo, guarda e punho para cima
        caixa(tela, cx - 0.4 * S, chao, 0.74 * S, 0.16 * S, 0.12 * S, TABUA, TABUA_TOPO, TABUA_LADO)
        for k, (cor_punho, pomo) in enumerate((((80, 44, 34), LATAO_VELHO), ((40, 38, 48), FERRO_BATIDO), ((110, 30, 36), OURO))):
            x = cx - 0.26 * S + k * 0.22 * S
            boca = v2(x, chao - 0.16 * S)
            lamina(tela, boca + v2(0, 0.02 * S), boca + v2(0, -0.46 * S), 0.028 * S)
            guarda = boca + v2(0, -0.46 * S)
            tela.pintar(tela.capsula(guarda + v2(-0.09 * S, 0), guarda + v2(0.09 * S, 0), 1.2), FERRO_BATIDO)
            tela.pintar(tela.capsula(guarda, guarda + v2(0, -0.15 * S), 1.3), Mat(cor_punho, 4))
            tela.pintar(tela.circulo(guarda + v2(0, -0.17 * S), 1.8), pomo)
            tela.chapado(tela.elipse(x, chao - 0.16 * S - 0.5, 2.2, 0.8), (30, 20, 18))
        self.manequim(tela, v2(cx - 1.0 * S, chao), f)
        # à direita: escudo de pipa e escudo redondo encostados, barril de flechas com um arco
        bf = v2(cx + 1.12 * S, chao)
        barril_3d(tela, bf, 0.14 * S, 0.36 * S, tampo=False)
        for k in range(7):
            topo_f = bf + v2(-0.09 * S + k * 0.03 * S, -0.62 * S - (k % 3) * 0.04 * S)
            tela.traco(bf + v2(-0.05 * S + k * 0.015 * S, -0.32 * S), topo_f, (150, 116, 70))
            tela.chapado(tela.poly([topo_f + v2(-1.4, 1), topo_f + v2(1.4, 1), topo_f + v2(0, -2)]), (226, 222, 214) if k % 2 else (176, 60, 54))
        arco = [bf + v2(0.16 * S, -0.02 * S), bf + v2(0.26 * S, -0.5 * S), bf + v2(0.2 * S, -0.98 * S)]
        tela.tracos(arco, (110, 74, 44))
        tela.traco(arco[0], arco[2], (200, 196, 180))
        pipa = [v2(cx + 0.72 * S, chao - 0.88 * S), v2(cx + 1.0 * S, chao - 0.84 * S), v2(cx + 0.98 * S, chao - 0.42 * S),
                v2(cx + 0.84 * S, chao - 0.02 * S), v2(cx + 0.7 * S, chao - 0.44 * S)]
        tela.pintar(tela.poly(pipa), Mat((44, 56, 96), 6, relevo=0.7))
        tela.tracos(pipa + [pipa[0]], (176, 146, 80), sobre=True)
        tela.pintar(tela.poly([pipa[0] + v2(0.13 * S, 0.06 * S), pipa[0] + v2(0.15 * S, 0.06 * S), pipa[3] + v2(0, -4),
                               pipa[3] + v2(-1, -4)]), Mat((206, 176, 96), 4), plano=True)
        centro = v2(cx + 0.52 * S, chao - 0.27 * S)
        redondo = tela.elipse(centro[0], centro[1], 0.26 * S, 0.27 * S)
        tela.pintar(redondo, Mat((120, 40, 40), 6, relevo=0.8))
        for a in (0.0, math.pi / 2):                                  # cruz pintada e o aro de ferro
            tela.chapado(redondo & tela.elipse_girada(centro, 0.27 * S, 0.035 * S, a), (200, 160, 80))
        tela.pintar(redondo & ~tela.elipse(centro[0], centro[1], 0.22 * S, 0.23 * S), FERRO_BATIDO, plano=True)
        tela.pintar(tela.circulo(centro, 0.07 * S), metal((170, 168, 180)))
        # um brilho que corre pelas lâminas
        alvos = [v2(cx - 0.3 * S, chao - 1.66 * S), v2(cx - 0.08 * S, chao - 1.84 * S), v2(cx + 0.16 * S, chao - 1.6 * S),
                 v2(cx - 0.04 * S, chao - 0.4 * S)]
        b = alvos[P["i"] % 4]
        tela.px(b[0], b[1], (255, 255, 236), emite=True)
        tela.brilho(b, 0.12 * S, (255, 240, 200), 0.3)

    def haste(self, tela, base, topo, cabo, largura=1.4):
        """Cabo de uma arma de haste encostada; devolve o ponto da cabeça como função p(ao_longo, ao_lado), em S,
        a partir do topo do cabo (ao_longo > 0 sobe pelo cabo; ao_lado > 0 vai para a direita dele)."""
        tela.pintar(tela.capsula(base, topo, largura), cabo)
        tela.traco(lerp(base, topo, 0.62), lerp(base, topo, 0.7), (60, 36, 26), sobre=True)            # empunhadura
        u = (topo - base) / (math.hypot(*(topo - base)) or 1)
        n = v2(-u[1], u[0])
        return lambda ao_longo, ao_lado: topo + u * ao_longo * self.S + n * ao_lado * self.S

    def alabarda(self, tela, base, topo, cabo):
        p = self.haste(tela, base, topo, cabo)
        lamina(tela, p(-0.12, 0), p(0.16, 0), 0.035 * self.S)
        machado = [p(-0.06, 0.02), p(0.0, 0.24), p(-0.16, 0.28), p(-0.32, 0.22), p(-0.24, 0.02)]
        tela.chapado(tela.poly(machado), (150, 152, 166))
        tela.chapado(tela.poly([machado[1], machado[2], machado[3], p(-0.16, 0.22)]), (196, 198, 212))
        tela.traco(machado[1], machado[3], (240, 242, 250))
        tela.chapado(tela.poly([p(-0.1, -0.02), p(-0.17, -0.14), p(-0.2, -0.02)]), (130, 132, 146))     # o esporão de trás

    def lanca(self, tela, base, topo, cabo, fase, borla=True):
        p = self.haste(tela, base, topo, cabo, 1.2)
        lamina(tela, p(-0.04, 0), p(0.2, 0), 0.04 * self.S)
        if borla:
            balanco = math.sin(fase) * 0.8
            tela.chapado(tela.poly([p(-0.06, -0.04), p(-0.06, 0.04), p(-0.22, 0.03) + v2(balanco, 0), p(-0.22, -0.03) + v2(balanco, 0)]),
                         (150, 36, 40))

    def glaive(self, tela, base, topo, cabo):
        p = self.haste(tela, base, topo, cabo)
        folha = [p(-0.14, -0.02), p(-0.12, 0.05), p(0.06, 0.1), p(0.26, 0.02), p(0.04, -0.03)]
        tela.chapado(tela.poly(folha), (166, 168, 182))
        tela.traco(folha[2], folha[3], (244, 246, 252))

    def manequim(self, tela, pe, f):
        """Manequim de armeiro: cruzeta de madeira, couraça com ombreira, tabardo azul e elmo no alto."""
        S = self.S
        base = [pe + v2(-0.22 * S, 0), pe + v2(0.22 * S, 0), pe + v2(0.18 * S, -0.05 * S), pe + v2(-0.18 * S, -0.05 * S)]
        face(tela, base, TABUA_ESCURA)
        poste_topo = pe + v2(0, -1.42 * S)
        tela.pintar(tela.capsula(pe + v2(0, -0.04 * S), poste_topo, 1.8), TABUA)
        ombro = pe + v2(0, -1.18 * S)
        tela.pintar(tela.capsula(ombro + v2(-0.2 * S, 0), ombro + v2(0.2 * S, 0), 1.6), TABUA)
        # tabardo por baixo da couraça (pende até os joelhos, com a cruz dourada)
        balanco = math.sin(f) * 0.6
        tabardo = [ombro + v2(-0.14 * S, 0.26 * S), ombro + v2(0.14 * S, 0.26 * S), ombro + v2(0.15 * S + balanco, 0.78 * S),
                   ombro + v2(0.0 + balanco, 0.72 * S), ombro + v2(-0.15 * S + balanco, 0.78 * S)]
        tela.pintar(tela.poly(tabardo), Mat((46, 60, 108), 6, ruido=0.08, relevo=0.8, desce=0.3))
        cruz = ombro + v2(balanco * 0.5, 0.52 * S)
        tela.chapado(tela.poly([cruz + v2(-1, -5), cruz + v2(1, -5), cruz + v2(1, 5), cruz + v2(-1, 5)]), (196, 160, 80))
        tela.chapado(tela.poly([cruz + v2(-4, -2), cruz + v2(4, -2), cruz + v2(4, 0), cruz + v2(-4, 0)]), (196, 160, 80))
        # couraça de aço (peito com a quilha no meio), faixa de couro e as ombreiras
        peito = [ombro + v2(-0.16 * S, -0.02 * S), ombro + v2(0.16 * S, -0.02 * S), ombro + v2(0.14 * S, 0.3 * S),
                 ombro + v2(0.0, 0.36 * S), ombro + v2(-0.14 * S, 0.3 * S)]
        tela.pintar(tela.poly(peito), ACO)
        tela.traco(ombro + v2(0, 0.0), ombro + v2(0, 0.34 * S), ACO[5], sobre=True)
        tela.traco(ombro + v2(-0.14 * S, 0.26 * S), ombro + v2(0.14 * S, 0.26 * S), (70, 46, 34), sobre=True)
        for lado in (-1, 1):
            tela.pintar(tela.elipse(ombro[0] + lado * 0.19 * S, ombro[1] + 0.03 * S, 0.09 * S, 0.07 * S), ACO.escuro(1))
            tela.traco(ombro + v2(lado * 0.13 * S, 0.06 * S), ombro + v2(lado * 0.25 * S, 0.06 * S), ACO[1], sobre=True)
        # elmo (bacinete com a fenda da viseira e um penacho curto)
        e = poste_topo + v2(0, 0.02 * S)
        cupula = tela.elipse(e[0], e[1], 0.12 * S, 0.13 * S) | tela.poly([e + v2(-0.12 * S, 0), e + v2(0.12 * S, 0),
                                                                        e + v2(0.11 * S, 0.17 * S), e + v2(-0.11 * S, 0.17 * S)])
        tela.pintar(cupula, ACO)
        tela.chapado(tela.poly([e + v2(-0.09 * S, 0.05 * S), e + v2(0.09 * S, 0.05 * S), e + v2(0.09 * S, 0.075 * S),
                                e + v2(-0.09 * S, 0.075 * S)]), (16, 12, 18))
        tela.traco(e + v2(0, -0.12 * S), e + v2(0, 0.16 * S), ACO[5], sobre=True)
        penacho = [e + v2(0, -0.12 * S), e + v2(-0.08 * S, -0.22 * S), e + v2(-0.2 * S, -0.2 * S + math.sin(f) * 0.8)]
        tela.pintar(tela.corrente(penacho, [1.6, 1.9, 0.8]), Mat((150, 36, 40), 5, relevo=0.6))


# ============================================================
# BAÚ DAS SKINS
# ============================================================

class BauOrnamentado(ObjetoDeCena):
    """O baú das skins: arca de carvalho gasto com cintas de ferro rebitadas e cantoneiras de latão, tampa abaulada
    aberta para trás (forrada de veludo desbotado, presa por uma corrente) e, dentro, o guarda-roupa dos heróis:
    roupas dobradas, um chapéu de pena, o cabo de uma espada e uma capa caída pela borda da frente."""
    nome = "bau_ornamentado"
    S = 44
    proporcao = (2.0, 2.0)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        larg, alt, prof = 1.24 * S, 0.5 * S, 0.36 * S
        x0, x1 = cx - larg / 2 - 0.06 * S, cx + larg / 2 - 0.06 * S
        d = v2(prof * 0.6, -prof * 0.5)
        topo = chao - alt
        tela.chapado(tela.elipse(cx + 0.06 * S, chao + 1, larg * 0.62, 3.5), (14, 10, 14))
        # tampa aberta e tombada para trás: o lado de dentro (tábuas e um painel de veludo) virado para nós, com o
        # arco da tampa abaulada no alto e a espessura da madeira aparecendo na borda
        dob_e, dob_d = v2(x0, topo) + d, v2(x1, topo) + d
        sobe = 0.44 * S
        arco = [lerp(dob_e, dob_d, t) + d * 0.45 + v2(0, -sobe - math.sin(math.pi * t) * 0.09 * S) for t in [k / 10 for k in range(11)]]
        casca = [dob_e + v2(-1, 0)] + [p + v2(0, -2.5) for p in arco] + [dob_d + v2(1, 0)]
        tela.pintar(tela.poly(casca), CARVALHO_TOPO, plano=True)                    # a espessura da tampa
        forro = [dob_e] + arco + [dob_d]
        mforro = face(tela, forro, CARVALHO_LADO, desce=0.35)
        tabuas(tela, mforro, dob_e[0], arco[-1][0], arco[5][1], dob_e[1], 0.12 * S, CARVALHO_LADO[0], horizontal=False, nos=False)
        painel = [lerp(dob_e, arco[1], 0.2) + v2(3, 0), lerp(dob_d, arco[9], 0.2) + v2(-3, 0), arco[9] + v2(-3, 3), arco[1] + v2(3, 3)]
        mpainel = face(tela, painel, Mat((92, 28, 38), 6, ruido=0.12), desce=0.4)
        for k in range(1, 3):                                                     # capitonê
            for j in range(1, 6):
                p = lerp(lerp(painel[0], painel[1], j / 6), lerp(painel[3], painel[2], j / 6), k / 3)
                tela.px(p[0], p[1], (58, 14, 24))
        tela.tracos(painel + [painel[0]], LATAO_VELHO[2], sobre=True)
        tela.tracos(arco, LATAO_VELHO[3], sobre=True)                             # debrum de latão na borda da tampa
        for t in (0.2, 0.8):                                                      # as cintas de ferro dão a volta na tampa
            a, b = lerp(dob_e, dob_d, t), arco[round(t * 10)]
            tela.pintar(tela.poly([a + v2(-2.2, 0), a + v2(2.2, 0), b + v2(2.2, -2), b + v2(-2.2, -2)]), FERRO_BATIDO.escuro(1), plano=True)
        # a corrente que segura a tampa (do canto da tampa até o lado da caixa)
        corrente = [lerp(dob_d + v2(-2, -sobe * 0.55), v2(x1, topo + 3) + d * 0.6, t / 6) for t in range(7)]
        for k, p in enumerate(corrente):
            tela.px(p[0], p[1] + math.sin(k * 1.3) * 0.6, (150, 146, 160) if k % 2 else (96, 92, 106))
        # o lado (direita) e a boca: o fundo escuro com o guarda-roupa dentro
        lado = [v2(x1, chao), v2(x1, chao) + d, v2(x1, topo) + d, v2(x1, topo)]
        mlado = face(tela, lado, CARVALHO_LADO, desce=0.25)
        tabuas(tela, mlado, x1, x1 + d[0], topo + d[1], chao, 0.13 * S, CARVALHO_LADO[0], horizontal=True, nos=False)
        boca = [v2(x0, topo), v2(x1, topo), v2(x1, topo) + d, v2(x0, topo) + d]
        face(tela, boca, Mat((36, 24, 24), 5))
        self.guarda_roupa(tela, x0, x1, topo, d, f)
        # a frente: tábuas deitadas, base mais escura, pés de bloco
        frente = face(tela, [v2(x0, chao), v2(x1, chao), v2(x1, topo), v2(x0, topo)], CARVALHO, desce=0.25)
        tabuas(tela, frente, x0, x1, topo, chao, 0.13 * S, CARVALHO[1], horizontal=True)
        tela.traco(v2(x0, topo), v2(x1, topo), CARVALHO_TOPO[5])                    # luz no fio da borda
        for x in (x0 + 2, x1 - 2):
            tela.chapado(tela.poly([v2(x - 2.5, chao + 2), v2(x + 2.5, chao + 2), v2(x + 2.5, chao - 1), v2(x - 2.5, chao - 1)]),
                         (44, 30, 24))
        # a capa: sai de dentro da arca, dobra na borda e cai pela frente em pregas, com a barra curva e o debrum dourado
        onda = math.sin(f) * 0.7
        dentro = v2(x0, topo) + d * 0.5
        barra = [v2(x0 + (0.5 - 0.46 * t) * S + onda * t, topo + (0.3 + 0.08 * math.sin(t * math.pi * 3)) * S + 3 * t * t)
                 for t in [k / 8 for k in range(9)]]
        capa = [dentro + v2(0.08 * S, 0), dentro + v2(0.44 * S, -1), v2(x0 + 0.48 * S, topo - 1)] + barra + \
               [v2(x0 + 0.02 * S, topo + 0.1 * S), v2(x0 + 0.02 * S, topo - 1)]
        mcapa = tela.poly(capa)
        tela.pintar(mcapa, Mat((36, 60, 50), 6, ruido=0.08, relevo=1.3, desce=0.25))
        tela.traco(v2(x0 + 0.02 * S, topo - 0.5), v2(x0 + 0.48 * S, topo - 0.5), (70, 104, 86), sobre=True)   # a dobra na borda
        for t in (0.25, 0.5, 0.75):                                               # pregas
            p = barra[round((1 - t) * 8)]
            tela.traco(v2(p[0] + 1, topo + 2), p + v2(0, -2), (20, 36, 30), sobre=True)
        tela.tracos(barra, (186, 150, 74), sobre=True)
        # ferragens: cintas de ferro rebitadas, cantoneiras de latão, alça de argola e o fecho com a fechadura
        for x in (x0 + larg * 0.22, x1 - larg * 0.22):
            cinta = tela.poly([v2(x - 2.4, chao), v2(x + 2.4, chao), v2(x + 2.4, topo), v2(x - 2.4, topo)]) & ~mcapa
            tela.pintar(cinta, FERRO_BATIDO, plano=True)
            rebites(tela, v2(x, topo + 2), v2(x, chao - 2), 4)
        tela.pintar(tela.poly([v2(x1 - 2.4, topo), v2(x1 + 2.4, topo), v2(x1 + 2.4, topo) + d, v2(x1 - 2.4, topo) + d]) & ~mcapa,
                    FERRO_BATIDO, plano=True)
        for xx, yy, sx, sy in ((x0, chao, 1, -1), (x1, chao, -1, -1), (x0, topo, 1, 1), (x1, topo, -1, 1)):
            canto = tela.poly([v2(xx, yy), v2(xx + sx * 7, yy), v2(xx + sx * 2, yy + sy * 2), v2(xx, yy + sy * 7)]) & ~mcapa
            tela.pintar(canto, LATAO_VELHO)
        tela.pintar(tela.poly([v2(x1, chao), v2(x1, chao) + d, v2(x1, chao - 5) + d, v2(x1, chao - 5)]), LATAO_VELHO.escuro(1), plano=True)
        alca = v2(x1, chao - alt * 0.5) + d * 0.5
        tela.pintar(tela.elipse(alca[0], alca[1] + 3, 2.4, 3.2) & ~tela.elipse(alca[0], alca[1] + 3, 1.1, 1.9), FERRO)
        fecho = v2(cx + 0.06 * S, topo + 2)
        tela.pintar(tela.poly([fecho + v2(-4, -2), fecho + v2(4, -2), fecho + v2(4, 6), fecho + v2(0, 8), fecho + v2(-4, 6)]),
                    LATAO_VELHO)
        tela.chapado(tela.circulo(fecho + v2(0, 1.5), 1.1) | tela.poly([fecho + v2(-0.6, 1.5), fecho + v2(0.6, 1.5),
                                                                      fecho + v2(0.7, 5), fecho + v2(-0.7, 5)]), (24, 16, 18))
        # um brilho que passeia pelo latão
        alvos = [v2(x0 + 2, topo + 2), fecho + v2(-2, -1), v2(x1 - 2, chao - 3), arco[5]]
        b = alvos[P["i"] % 4]
        tela.px(b[0], b[1], (255, 244, 200), emite=True)

    def guarda_roupa(self, tela, x0, x1, topo, d, f):
        """O que está dentro: roupas dobradas em pilha, um chapéu de pena por cima e o cabo de uma espada."""
        S = self.S
        fundo = v2(x0, topo) + d * 0.6
        for k, (cor, larg) in enumerate((((54, 58, 92), 0.6), ((104, 38, 44), 0.5), ((138, 112, 70), 0.4))):
            base = fundo + v2(0.36 * S + k * 0.04 * S, 1 - k * 3)
            dobra = [base, base + v2(larg * S, 0), base + v2(larg * S, -3) + d * 0.3, base + v2(0, -3) + d * 0.3]
            tela.pintar(tela.poly(dobra), Mat(cor, 5, ruido=0.08, relevo=0.6))
            tela.traco(base + v2(0, -1.5), base + v2(larg * S, -1.5), Mat(cor, 5)[1], sobre=True)       # a dobra do pano
        # chapéu de aba larga com pena, por cima da pilha
        c = fundo + v2(0.72 * S, -8)
        tela.pintar(tela.elipse(c[0], c[1] + 2.5, 0.2 * S, 2.2), Mat((48, 36, 42), 5))
        tela.pintar(tela.elipse(c[0], c[1] - 1, 0.1 * S, 0.11 * S) | tela.poly([c + v2(-0.1 * S, -1), c + v2(0.1 * S, -1),
                                                                              c + v2(0.1 * S, 2), c + v2(-0.1 * S, 2)]),
                    Mat((58, 42, 48), 5, relevo=1.0))
        tela.traco(c + v2(-0.1 * S, 1), c + v2(0.1 * S, 1), (164, 124, 66), sobre=True)
        balanco = math.sin(f) * 0.7
        pena = [c + v2(0.04 * S, -0.04 * S), c + v2(-0.08 * S, -0.2 * S + balanco), c + v2(-0.2 * S, -0.26 * S + balanco)]
        tela.pintar(tela.corrente(pena, [1.4, 1.7, 0.5]), Mat((170, 56, 50), 5, relevo=0.6))
        # o cabo de uma espada saindo pelo canto da esquerda (guarda, punho de couro e pomo)
        g = v2(x0 + 0.1 * S, topo - 0.08 * S)
        tela.pintar(tela.capsula(g + v2(-3, 1), g + v2(4, -2), 1.1), metal((150, 148, 160)))
        tela.pintar(tela.capsula(g + v2(0.5, -1), g + v2(-2.5, -0.18 * S), 1.2), Mat((88, 52, 36), 4))
        tela.pintar(tela.circulo(g + v2(-3, -0.2 * S), 1.6), LATAO_VELHO)


# ============================================================
# CARROÇA
# ============================================================

class Carroca(ObjetoDeCena):
    """A carroça do mercador: lona encardida com remendos e cordas, a placa da balança pendurada no lado, panelas,
    lampião, sacos e um barril amarrados, barro nas tábuas de baixo e o timão apoiado num toco."""
    nome = "carroca"
    S = 56
    proporcao = (3.1, 2.1)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        d = v2(0.26 * S, -0.16 * S)
        tela.chapado(tela.elipse(cx + 0.1 * S, chao, 1.3 * S, 0.1 * S), (16, 14, 18))

        def roda(c, r, mat_aro, mat_raio, escura=False):
            aro = tela.circulo(c, r) & ~tela.circulo(c, r * 0.8)
            tela.pintar(aro, mat_aro)
            tela.pintar(tela.circulo(c, r) & ~tela.circulo(c, r * 0.92), FERRO_BATIDO, plano=True)
            for k in range(10):
                a = k * math.pi / 5 + 0.15
                tela.pintar(tela.capsula(c, c + v2(math.cos(a), math.sin(a)) * r * 0.82, 1.1), mat_raio)
            tela.pintar(tela.circulo(c, r * 0.2), FERRO_BATIDO)
            tela.chapado(tela.circulo(c, r * 0.08), (30, 26, 30) if escura else (200, 196, 210))

        eixo_y = chao - 0.3 * S
        rodas = (cx - 0.66 * S, cx + 0.56 * S)
        for x in rodas:                                             # as rodas do outro lado (atrás, escuras)
            roda(v2(x, eixo_y) + d, 0.29 * S, TABUA_ESCURA, TABUA_ESCURA, True)
        # timão apoiado num toco
        tela.pintar(tela.capsula(v2(cx + 0.95 * S, chao - 0.46 * S), v2(cx + 1.48 * S, chao - 0.08 * S), 1.8), TABUA)
        tela.pintar(tela.capsula(v2(cx + 1.3 * S, chao - 0.2 * S), v2(cx + 1.3 * S, chao - 0.2 * S) + d * 0.6, 1.4), TABUA_ESCURA)
        caixa(tela, cx + 1.38 * S, chao, 0.16 * S, 0.1 * S, 0.1 * S, CASCA, CERNE, CASCA)
        # a caixa da carroça (lado comprido de frente)
        x0, x1 = cx - 1.0 * S, cx + 0.98 * S
        piso = chao - 0.44 * S
        topo_lateral = piso - 0.32 * S
        lateral, topo_l, fundo_l, _ = caixa(tela, x0, piso, x1 - x0, 0.32 * S, 0.5 * S, CARVALHO, CARVALHO_TOPO, CARVALHO_LADO)
        tabuas(tela, lateral, x0, x1, topo_lateral, piso, 0.08 * S, CARVALHO[1], horizontal=True)
        tela.tingir(lateral & tela.poly([v2(x0, piso), v2(x1, piso), v2(x1, piso - 0.1 * S), v2(x0, piso - 0.06 * S)]),
                    (58, 44, 34), 0.45)                                                  # barro da estrada
        for x in (x0 + 4, cx - 0.32 * S, cx + 0.34 * S, x1 - 4):
            tela.pintar(tela.poly([v2(x - 2, piso), v2(x + 2, piso), v2(x + 2, topo_lateral), v2(x - 2, topo_lateral)]), FERRO_BATIDO, plano=True)
            rebites(tela, v2(x, topo_lateral + 2), v2(x, piso - 2), 3)
        self.placa_do_mercador(tela, v2(cx + 0.02 * S, topo_lateral + 0.04 * S), f)
        # a lona vista de lado: meio-cilindro de topo reto e pontas arredondadas, com a parte de cima recuando
        arco_alt = 0.74 * S
        base_lona = topo_lateral + 2

        def contorno(desl, encolhe=0.0):
            pts = [v2(x0 + 2, base_lona) + desl]
            for j in range(41):
                t = j / 40
                h = arco_alt * max(0.0, 1 - abs(2 * t - 1) ** 5) ** 0.22 - encolhe
                pts.append(v2(x0 + 2 + t * (x1 - x0 - 4), base_lona - h) + desl)
            pts.append(v2(x1 - 2, base_lona) + desl)
            return pts
        fundo_lona = contorno(d)
        face(tela, fundo_lona, LONA_CRUA.copia(desce=0.2), nivel=-0.25)               # a lona do outro lado
        topo_lona = [p for p in contorno(v2(0, 0))[1:-1]]
        topo_fundo = [p for p in fundo_lona[1:-1]]
        face(tela, topo_lona + list(reversed(topo_fundo)), LONA_CRUA, nivel=0.15)       # o "teto" que recua
        frente_lona = face(tela, contorno(v2(0, 0)), LONA_CRUA.copia(desce=0.45))
        for k in range(1, 6):                                                       # arcos de madeira por baixo da lona
            t = k / 6
            x = x0 + 2 + t * (x1 - x0 - 4)
            h = arco_alt * max(0.0, 1 - abs(2 * t - 1) ** 5) ** 0.22
            tela.traco(v2(x, base_lona), v2(x, base_lona - h), LONA_CRUA[1], sobre=True)
            tela.traco(v2(x + 1, base_lona - 2), v2(x + 1, base_lona - h + 2), LONA_CRUA[5], sobre=True)
            tela.traco(v2(x, base_lona - h), v2(x, base_lona - h) + d, LONA_CRUA[2], sobre=True)
            for lado in (-4, 4):                                                    # a lona cede entre os arcos
                tela.traco(v2(x + lado, base_lona - h * 0.3), v2(x + lado * 1.5, base_lona - h * 0.85), LONA_CRUA[2], sobre=True)
        tela.tracos([p + v2(0, 1) for p in topo_lona], LONA_CRUA[5], sobre=True)       # luz no alto
        for k in range(int((x1 - x0) / 6)):                                         # barra franzida e amarrada
            x = x0 + 4 + k * 6
            tela.chapado(tela.elipse(x + 3, base_lona, 3, 1.6) & frente_lona, LONA_CRUA[1])
        # remendos de outros panos, costurados com pontos largos
        for px_, py_, w, h, cor in ((0.22, 0.4, 0.28, 0.2, (128, 100, 72)), (0.62, 0.26, 0.22, 0.17, (104, 110, 92)),
                                    (1.32, 0.46, 0.26, 0.19, (140, 116, 86))):
            r0 = v2(x0 + px_ * S, base_lona - py_ * S - h * S)
            remendo = tela.poly([r0, r0 + v2(w * S, 1), r0 + v2(w * S - 1, h * S), r0 + v2(1, h * S - 1)]) & frente_lona
            tela.pintar(remendo, Mat(cor, 5, ruido=0.1), plano=True)
            for j in range(int(w * S / 3)):
                tela.px(r0[0] + 1 + j * 3, r0[1] + 1, (60, 46, 36))
        # cordas cruzando a lona, presas na borda da caixa
        for a, b in (((0.12, 0.0), (0.7, 0.66)), ((0.7, 0.66), (1.24, 0.0)), ((0.86, 0.0), (1.4, 0.62)), ((1.4, 0.62), (1.9, 0.0))):
            pa = v2(x0 + a[0] * S, base_lona - a[1] * S)
            pb = v2(x0 + b[0] * S, base_lona - b[1] * S)
            tela.traco(pa, pb, (122, 96, 64), sobre=True)
            tela.traco(pa + v2(0, 1), pb + v2(0, 1), (70, 54, 40), sobre=True)
        # panelas penduradas no gancho da borda (balançam um pouco)
        for k, (dx, raio) in enumerate(((0.5, 0.07), (0.66, 0.055))):
            gancho = v2(x0 + dx * S, topo_lateral + 1)
            balanco = math.sin(f + k) * 0.8
            fundo = gancho + v2(balanco, 0.16 * S)
            tela.traco(gancho, fundo + v2(0, -raio * S), (90, 88, 100))
            tela.pintar(tela.elipse(fundo[0], fundo[1], raio * S, raio * S * 0.85), FERRO_BATIDO)
            tela.chapado(tela.elipse(fundo[0] - raio * S * 0.3, fundo[1] - raio * S * 0.3, 1.2, 1.0), (176, 174, 190))
        # boca da frente: escuro com luz de lampião lá dentro, e o franzido do cordão
        boca_c = v2(x1 - 0.06 * S, base_lona - arco_alt * 0.46) + d * 0.5
        boca = tela.elipse(boca_c[0], boca_c[1], 0.1 * S, 0.3 * S)
        tela.chapado(boca, (40, 28, 26))
        tela.chapado(boca & tela.elipse(boca_c[0] + 1, boca_c[1] + 0.12 * S, 0.06 * S, 0.14 * S), (206, 124, 56), emite=True)
        tela.chapado(boca & ~tela.elipse(boca_c[0], boca_c[1], 0.1 * S - 1.5, 0.3 * S - 1.5), LONA_CRUA[1])
        for k in range(4):                                           # cordas amarrando a lona
            x = x0 + 0.2 * S + k * 0.45 * S
            tela.traco(v2(x, topo_lateral + 1), v2(x + 2, topo_lateral - 0.1 * S), (150, 120, 80))
            tela.px(x + 2, topo_lateral - 0.1 * S, (190, 160, 110))
        # carga e penduricalhos: barril amarrado, balde, lanterna
        barril_3d(tela, v2(x0 + 0.08 * S, piso + 0.02 * S + 0.38 * S), 0.15 * S, 0.38 * S)
        balde = v2(cx - 0.05 * S, piso + 0.06 * S)
        tela.traco(balde + v2(-3, -4), balde + v2(0, -8), FERRO[2])
        tela.traco(balde + v2(3, -4), balde + v2(0, -8), FERRO[2])
        tela.pintar(tela.poly([balde + v2(-4, -4), balde + v2(4, -4), balde + v2(3, 4), balde + v2(-3, 4)]), TABUA)
        tela.traco(balde + v2(-4, -1), balde + v2(4, -1), FERRO[2], sobre=True)
        lanterna(tela, v2(x1 + d[0] * 0.3, topo_lateral - 0.1 * S), f, 0.9)
        # sacos de mantimentos encostados atrás, no chão
        for k, (dx, alt_s, larg_s) in enumerate(((-1.26, 0.26, 0.14), (-1.06, 0.2, 0.13))):
            b = v2(cx + dx * S, chao)
            saco = tela.poly([b + v2(-larg_s * S, 0), b + v2(larg_s * S, 0), b + v2(larg_s * S * 0.9, -alt_s * S * 0.6),
                              b + v2(larg_s * S * 0.3, -alt_s * S), b + v2(-larg_s * S * 0.4, -alt_s * S * 0.95),
                              b + v2(-larg_s * S, -alt_s * S * 0.5)])
            tela.pintar(saco, Mat((124, 98, 66), 5, ruido=0.3, relevo=1.3))
            amarrado = b + v2(0, -alt_s * S * 0.95)
            tela.chapado(tela.elipse(amarrado[0], amarrado[1] - 1, 2.2, 1.6), (104, 80, 54))
            tela.traco(amarrado + v2(-2, 1), amarrado + v2(2, 1), (70, 52, 38))
        for x in rodas:                                              # as rodas da frente
            roda(v2(x, eixo_y), 0.31 * S, CARVALHO, Mat((120, 84, 54), 5, relevo=0.8))
            tela.tingir(tela.circulo(v2(x, eixo_y), 0.31 * S) & tela.poly([v2(x - S, eixo_y + 0.14 * S), v2(x + S, eixo_y + 0.14 * S),
                                                                           v2(x + S, chao + 2), v2(x - S, chao + 2)]),
                        (58, 44, 34), 0.4)                                                # barro na parte de baixo da roda

    def placa_do_mercador(self, tela, topo, f):
        """Tábua pendurada no lado da carroça, com uma balança pintada em dourado (o sinal do mercador)."""
        S = self.S
        balanco = math.sin(f) * 0.5
        w, h = 0.36 * S, 0.2 * S
        c = topo + v2(balanco, 0.04 * S)
        for lado in (-1, 1):
            tela.traco(topo + v2(lado * w * 0.35, 0), c + v2(lado * w * 0.35, 0), (110, 90, 64))
        tabua = [c + v2(-w / 2, 0), c + v2(w / 2, 0), c + v2(w / 2, h), c + v2(-w / 2, h)]
        tela.pintar(tela.poly(tabua), Mat((70, 50, 40), 5, ruido=0.3), plano=True)
        tela.tracos(tabua + [tabua[0]], (40, 28, 24))
        m = c + v2(0, h * 0.5)
        dourado = (204, 168, 84)
        tela.traco(m + v2(0, -h * 0.34), m + v2(0, h * 0.32), dourado)
        tela.traco(m + v2(-w * 0.28, -h * 0.22), m + v2(w * 0.28, -h * 0.22), dourado)
        for lado in (-1, 1):
            prato = m + v2(lado * w * 0.28, h * 0.12)
            tela.traco(m + v2(lado * w * 0.28, -h * 0.22), prato, (150, 124, 66))
            tela.traco(prato + v2(-2, 0), prato + v2(2, 0), dourado)


# ============================================================
# ESPELHO DE PÉ (PSIQUÉ)
# ============================================================

class EspelhoAntigo(ObjetoDeCena):
    nome = "espelho_antigo"
    S = 60
    proporcao = (1.5, 2.1)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        ouro = metal((184, 140, 64), especular=(255, 240, 180))
        madeira = Mat((70, 40, 46), 6, ruido=0.2, relevo=1.0)
        # base: travessa com pés de garra
        tela.pintar(tela.capsula(v2(cx - 0.5 * S, chao - 0.08 * S), v2(cx + 0.5 * S, chao - 0.08 * S), 0.045 * S), madeira)
        for lado in (-1, 1):
            pe = v2(cx + lado * 0.56 * S, chao - 2)
            tela.pintar(tela.capsula(v2(cx + lado * 0.44 * S, chao - 0.08 * S), pe, 2.4, 2.0), madeira)
            for k in (-1, 0, 1):
                tela.pintar(tela.capsula(pe, pe + v2(lado * 2 + k * 2.2, 2), 1.1), ouro)
        # colunas laterais torneadas com pináculo dourado
        for lado in (-1, 1):
            x = cx + lado * 0.48 * S
            tela.pintar(tela.capsula(v2(x, chao - 0.1 * S), v2(x, chao - 1.55 * S), 0.04 * S), madeira)
            for y in (chao - 0.4 * S, chao - 0.8 * S, chao - 1.2 * S):
                tela.pintar(tela.elipse(x, y, 0.055 * S, 0.025 * S), madeira.claro(1))
            tela.pintar(tela.circulo(v2(x, chao - 1.6 * S), 0.05 * S), ouro)
            tela.pintar(tela.poly([v2(x - 2, chao - 1.64 * S), v2(x + 2, chao - 1.64 * S), v2(x, chao - 1.78 * S)]), ouro)
            tela.pintar(tela.circulo(v2(x, chao - 0.9 * S), 0.035 * S), ouro)                     # pino de giro
        # o espelho oval inclinado um pouco para trás
        c = v2(cx, chao - 0.92 * S)
        rx, ry = 0.38 * S, 0.62 * S
        tela.pintar(tela.elipse(c[0], c[1], rx + 3, ry + 3), metal((120, 86, 40)))
        tela.pintar(tela.elipse(c[0], c[1], rx + 1, ry + 1) & ~tela.elipse(c[0], c[1], rx - 3, ry - 3), ouro)
        for k in range(18):                                          # contas da moldura
            a = k * math.pi / 9
            tela.px(c[0] + math.cos(a) * (rx - 1), c[1] + math.sin(a) * (ry - 1), (255, 236, 160))
        vidro = tela.elipse(c[0], c[1], rx - 4, ry - 4)
        yy = c[1] - ry
        for k in range(6):                                           # degradê do vidro: violeta em cima, escuro embaixo
            faixa = vidro & tela.poly([v2(c[0] - rx, yy + k * ry / 3), v2(c[0] + rx, yy + k * ry / 3),
                                       v2(c[0] + rx, yy + (k + 1) * ry / 3 + 1), v2(c[0] - rx, yy + (k + 1) * ry / 3 + 1)])
            tela.chapado(faixa, [(96, 70, 150), (78, 54, 132), (62, 42, 112), (48, 32, 92), (36, 24, 72), (28, 18, 56)][k])
        for k in range(22):                                          # névoa girando devagar
            a = f * 0.5 + k * 0.8
            r = (0.08 + (k % 6) * 0.04) * S
            p = v2(c[0] + math.cos(a) * r * 0.9, c[1] + 0.1 * S + math.sin(a) * r * 1.3)
            tela.chapado(tela.circulo(p, 1.2 + (k % 3) * 0.6) & vidro, (120 + k * 3, 90 + k * 2, 200), emite=True)
        vulto = v2(c[0], c[1] + 0.18 * S)                            # o vulto encapuzado do outro lado
        tela.chapado((tela.circulo(vulto + v2(0, -0.2 * S), 0.075 * S) | tela.poly([vulto + v2(-0.13 * S, 0.34 * S),
                      vulto + v2(0.13 * S, 0.34 * S), vulto + v2(0.06 * S, -0.16 * S), vulto + v2(-0.06 * S, -0.16 * S)])) & vidro,
                     (18, 10, 32))
        for dx in (-1.5, 1.5):
            tela.px(vulto[0] + dx, vulto[1] - 0.21 * S, (230, 170, 255), emite=True)
        for k, (dx, larg) in enumerate(((-0.2, 3), (-0.08, 1.5))):    # reflexos diagonais
            x = c[0] + dx * S + ((P["i"] / 4) - 0.5) * 0.12 * S
            tela.chapado(tela.poly([v2(x, c[1] - ry), v2(x + larg, c[1] - ry), v2(x + larg - 0.3 * S, c[1] + ry),
                                    v2(x - 0.3 * S, c[1] + ry)]) & vidro, (170, 150, 226) if k == 0 else (130, 110, 200))
        tela.traco(c + v2(0.12 * S, -0.3 * S), c + v2(0.2 * S, -0.12 * S), (210, 200, 240), sobre=True)   # trinca
        tela.traco(c + v2(0.2 * S, -0.12 * S), c + v2(0.16 * S, -0.02 * S), (210, 200, 240), sobre=True)
        tela.brilho(c, 0.55 * S, (150, 90, 230), 0.35 + 0.1 * math.sin(f))
        # crista: crânio alado no alto da moldura e uma gota dourada embaixo
        cr = v2(c[0], c[1] - ry - 2)
        for lado in (-1, 1):
            tela.pintar(tela.poly([cr + v2(lado * 3, 2), cr + v2(lado * 15, -7), cr + v2(lado * 12, 0), cr + v2(lado * 16, 3),
                                   cr + v2(lado * 5, 6)]), metal((120, 86, 40)))
        tela.pintar(tela.circulo(cr, 4.4), Mat((220, 208, 178), 5))
        tela.chapado(tela.circulo(cr + v2(-1.6, 0), 1.0) | tela.circulo(cr + v2(1.6, 0), 1.0), (20, 10, 20))
        tela.pintar(tela.poly([v2(c[0] - 3, c[1] + ry + 2), v2(c[0] + 3, c[1] + ry + 2), v2(c[0], c[1] + ry + 9)]), ouro)
        # véu de veludo jogado sobre a coluna da direita
        x = cx + 0.48 * S
        veu = [v2(x - 6, chao - 1.56 * S), v2(x + 6, chao - 1.5 * S), v2(x + 8 + math.sin(f) * 0.8, chao - 0.95 * S),
               v2(x + 2, chao - 1.0 * S), v2(x - 2 + math.sin(f) * 0.8, chao - 0.88 * S), v2(x - 7, chao - 1.3 * S)]
        tela.pintar(tela.poly(veu), Mat((120, 28, 50), 5, relevo=0.9))
        tela.traco(veu[2], veu[2] + v2(0, 3), (226, 186, 90))
        tela.traco(veu[4], veu[4] + v2(0, 3), (226, 186, 90))


# ============================================================
# BARRIL E CAIXOTES EM 3/4
# ============================================================

class Barril(ObjetoDeCena):
    nome = "barril"
    S = 30
    proporcao = (1.4, 1.7)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        tela.chapado(tela.elipse(cx, chao, 0.52 * S, 0.08 * S), (16, 14, 18))
        barril_3d(tela, v2(cx, chao - 1), 0.46 * S, 1.2 * S)


class Caixotes(ObjetoDeCena):
    nome = "caixotes"
    S = 34
    proporcao = (2.0, 1.9)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        tela.chapado(tela.elipse(cx, chao, 0.9 * S, 0.08 * S), (16, 14, 18))
        for x, y, tam in ((cx - 0.8 * S, chao, 0.66), (cx + 0.02 * S, chao + 1, 0.58), (cx - 0.5 * S, chao - 0.66 * S, 0.56)):
            frente, topo, lado, d = caixa(tela, x, y, tam * S, tam * S, tam * S * 0.55)
            tela.tracos([v2(x + 2, y - 2), v2(x + tam * S - 2, y - tam * S + 2)], TABUA[1])
            tela.tracos([v2(x + 2, y - tam * S + 2), v2(x + tam * S - 2, y - 2)], TABUA[1])
            moldura = frente & ~tela.poly([v2(x + 2.5, y - 2.5), v2(x + tam * S - 2.5, y - 2.5), v2(x + tam * S - 2.5, y - tam * S + 2.5),
                                           v2(x + 2.5, y - tam * S + 2.5)])
            tela.pintar(moldura, TABUA_LADO, plano=True)
            for p in (v2(x + 1, y - 1), v2(x + tam * S - 1, y - 1), v2(x + 1, y - tam * S + 1), v2(x + tam * S - 1, y - tam * S + 1)):
                tela.px(p[0], p[1], (200, 196, 210))
        saco = v2(cx + 0.36 * S, chao - 0.62 * S)
        tela.pintar(tela.elipse(saco[0], saco[1], 0.2 * S, 0.14 * S), Mat((196, 164, 112), 5, relevo=0.9))
        tela.pintar(tela.capsula(saco + v2(0, -0.12 * S), saco + v2(0, -0.2 * S), 1.6), Mat((196, 164, 112), 5))
        tela.traco(saco + v2(-3, -0.12 * S), saco + v2(3, -0.12 * S), (120, 90, 60))


# ============================================================
# PAVILHÕES (as tendas grandes)
# ============================================================

class TendaGrande(ObjetoDeCena):
    """Pavilhão medieval: parede redonda listrada com dobras, telhado cônico em gomos, barrado recortado com
    debrum dourado, porta aberta com a luz lá dentro, pináculo com flâmula e cordas presas em estacas."""
    nome = "tenda_grande"
    S = 70
    proporcao = (2.2, 1.95)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.cores = kw.get("cores", ((112, 52, 92), (214, 196, 160)))

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        escura, clara = self.cores
        mat_e, mat_c = Mat(escura, 6, ruido=0.1), Mat(clara, 6, ruido=0.1)
        raio, parede = 0.78 * S, 0.62 * S
        topo_parede = chao - parede
        ponta = v2(cx, chao - 1.55 * S)
        tela.chapado(tela.elipse(cx, chao, raio * 1.1, 0.14 * S), (16, 14, 18))
        # cordas e estacas (atrás)
        for lado in (-1, 1):
            estaca = v2(cx + lado * 1.02 * S, chao - 2)
            tela.traco(v2(cx + lado * raio * 0.95, topo_parede - 2), estaca, (150, 130, 100))
            tela.pintar(tela.capsula(estaca, estaca + v2(-lado * 1, -5), 1.3), TABUA)
        # parede cilíndrica: listras verticais que se estreitam nas laterais (dá o volume), mais escura embaixo
        n = 12
        for k in range(n):
            a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
            x0_, x1_ = cx - math.cos(a0) * raio, cx - math.cos(a1) * raio
            curva0, curva1 = math.sin(a0) * 0.1 * S, math.sin(a1) * 0.1 * S
            gomo = [v2(x0_, chao + curva0 * 0.5), v2(x1_, chao + curva1 * 0.5), v2(x1_, topo_parede + curva1 * 0.3),
                    v2(x0_, topo_parede + curva0 * 0.3)]
            luz = 0.12 - abs(k - n * 0.62) / n * 0.5                     # mais claro um pouco à direita do meio
            face(tela, gomo, (mat_c if k % 2 else mat_e).copia(desce=0.4), nivel=luz)
            tela.traco(gomo[3], gomo[0], (mat_c if k % 2 else mat_e)[1], sobre=True)
        # porta aberta, com a aba presa por uma corda e o interior iluminado
        porta = [v2(cx - 0.18 * S, chao + 0.04 * S), v2(cx + 0.18 * S, chao + 0.04 * S), v2(cx + 0.12 * S, topo_parede + 0.12 * S),
                 v2(cx, topo_parede + 0.04 * S), v2(cx - 0.12 * S, topo_parede + 0.12 * S)]
        mp = tela.poly(porta)
        tela.chapado(mp, (52, 28, 22))
        tela.chapado(mp & tela.elipse(cx, chao - 0.06 * S, 0.14 * S, 0.3 * S), (214, 124, 52), emite=True)
        tela.chapado(mp & tela.elipse(cx, chao - 0.02 * S, 0.07 * S, 0.14 * S), (255, 196, 100), emite=True)
        tela.chapado(mp & tela.elipse(cx - 0.06 * S, chao, 0.08 * S, 0.035 * S), (90, 50, 40))
        tela.brilho(v2(cx, chao - 0.16 * S), 0.42 * S, (255, 150, 60), 0.4 + 0.06 * math.sin(f * 3))
        aba = [v2(cx + 0.02 * S, topo_parede + 0.06 * S), v2(cx + 0.18 * S, chao + 0.04 * S), v2(cx + 0.34 * S, chao),
               v2(cx + 0.26 * S, chao - 0.34 * S)]
        tela.pintar(tela.poly(aba), mat_c.copia(desce=0.3), plano=True, nivel=0.1)
        tela.traco(v2(cx + 0.24 * S, chao - 0.3 * S), v2(cx + 0.33 * S, chao - 0.26 * S), (226, 186, 90))
        # telhado cônico em gomos listrados
        for k in range(n):
            a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
            b0 = v2(cx - math.cos(a0) * raio * 1.06, topo_parede + math.sin(a0) * 0.1 * S * 0.3)
            b1 = v2(cx - math.cos(a1) * raio * 1.06, topo_parede + math.sin(a1) * 0.1 * S * 0.3)
            luz = 0.18 - abs(k - n * 0.62) / n * 0.55
            face(tela, [b0, b1, ponta], (mat_e if k % 2 else mat_c), nivel=luz)
            tela.traco(b0, ponta, (mat_e if k % 2 else mat_c)[1], sobre=True)
        # barrado recortado em dentes com debrum dourado
        for k in range(n * 2):
            a0, a1 = math.pi * k / (2 * n), math.pi * (k + 1) / (2 * n)
            p0 = v2(cx - math.cos(a0) * raio * 1.06, topo_parede + math.sin(a0) * 0.03 * S)
            p1 = v2(cx - math.cos(a1) * raio * 1.06, topo_parede + math.sin(a1) * 0.03 * S)
            dente = [p0, p1, lerp(p0, p1, 0.5) + v2(0, 0.12 * S)]
            face(tela, [p0 + v2(0, -2), p1 + v2(0, -2), p1 + v2(0, 2), p0 + v2(0, 2)], OURO_ESCURO.copia(), nivel=0.1)
            face(tela, dente, mat_e if k % 2 else mat_c, nivel=-0.05)
            tela.px(dente[2][0], dente[2][1], (226, 186, 90))
        # pináculo dourado com flâmula
        tela.pintar(tela.capsula(ponta, ponta + v2(0, -0.22 * S), 1.6), TABUA)
        tela.pintar(tela.circulo(ponta + v2(0, -0.24 * S), 2.2), OURO)
        pano = []
        for k in range(7):
            t = k / 6
            pano.append(ponta + v2(t * 0.3 * S, -0.22 * S + math.sin(f + t * 4) * 1.6 * t))
        for k in range(6, -1, -1):
            t = k / 6
            pano.append(ponta + v2(t * 0.3 * S, -0.13 * S + math.sin(f + t * 4) * 1.6 * t - t * 0.03 * S))
        tela.pintar(tela.poly(pano), Mat((170, 40, 44), 5, relevo=0.6))


# ============================================================
# TRONCO COMPRIDO (o banco em volta da fogueira)
# ============================================================

class TroncoComprido(ObjetoDeCena):
    """Uma tora comprida deitada na diagonal (a ponta de trás mais alta, perto do fogo; a da frente mais baixa, com os
    anéis do corte à mostra): o banco onde três se sentam lado a lado. Casca com nós, um toco de galho, musgo e o
    alto gasto e mais claro, de tanto sentarem. A âncora é o meio da tora, onde ela encosta no chão.

    comprimento e queda em pixels do desenho (quanto ela anda para a esquerda e desce da ponta de trás à da frente)."""
    nome = "tronco_comprido"
    S = 30
    comprimento = 137
    queda = 38

    def __init__(self, **kw):
        super().__init__(**kw)
        r = self.raio
        self.larg = int(self.comprimento + 2 * r + 8)
        self.alt = int(self.queda + 2 * r + 10)
        self.ancora = (self.larg // 2, int(self.alt - 5 - self.queda / 2))

    @property
    def raio(self):
        return 0.22 * self.S

    def desenhar(self, tela, ctx, P):
        r = self.raio
        cx, chao = self.ancora
        meio = v2(cx, chao - r)
        atras = meio + v2(self.comprimento / 2, -self.queda / 2)
        frente = meio + v2(-self.comprimento / 2, self.queda / 2)
        u = (frente - atras) / math.hypot(*(frente - atras))
        n = v2(-u[1], u[0])                                         # aponta para cima da tora (u vai para a esquerda)
        if n[1] > 0:
            n = -n
        tora(tela, frente, atras, r, mat=CASCA, ponta=False)       # (de frente para trás: a luz da casca fica em cima)
        angulo = math.atan2(u[1], u[0])                             # o corte da ponta da frente, com os anéis
        tela.pintar(tela.elipse_girada(frente, r * 0.45, r * 0.95, angulo), CERNE)
        tela.chapado(tela.elipse_girada(frente, r * 0.18, r * 0.45, angulo), CERNE[1])
        tela.px(frente[0], frente[1], CERNE[0])
        tela.traco(atras + n * r * 0.75 + u * 4, frente + n * r * 0.75 - u * 6, (120, 96, 74), sobre=True)  # o alto gasto
        tela.traco(atras + n * r * 0.55 + u * 6, frente + n * r * 0.55 - u * 8, (96, 76, 60), sobre=True)
        rng = random.Random(7)                                      # nós e musgo nos mesmos lugares em todos os quadros
        for t in (0.18, 0.47, 0.81):
            p = lerp(atras, frente, t) + n * rng.uniform(-0.3, 0.2) * r
            tela.chapado(tela.elipse(p[0], p[1], 2.0, 1.3), (44, 32, 26))
            tela.px(p[0] - 0.5, p[1] - 0.5, (110, 86, 66))
        for t in (0.08, 0.3, 0.62, 0.9):
            p = lerp(atras, frente, t) + n * r * 0.8
            tela.chapado(tela.elipse(p[0], p[1], rng.uniform(2.5, 4.5), 1.2) & tela.capsula(atras, frente, r), MUSGO)
        galho = lerp(atras, frente, 0.36) - n * r * 0.2 + u * 1
        tela.pintar(tela.capsula(galho, galho + v2(2, 5), 1.6), CASCA)            # toco de galho quebrado, embaixo
        tela.chapado(tela.elipse(galho[0] + 2, galho[1] + 5.5, 1.4, 0.8), CERNE[3])


# ============================================================
# VERSÕES DE LONGE (o acampamento em três planos de profundidade)
# ============================================================

MEIO, LONGE = 0.85, 0.7          # tamanho do plano do meio e do fundo em relação à frente (fogueira e heróis)


def na_distancia(classe, fator, sufixo, **kw):
    """A mesma forja desenhada MENOR (o pixel continua do mesmo tamanho): quem está mais longe da fogueira.

    Ampliar ou reduzir a folha pronta deixaria pixels de tamanhos diferentes; aqui o desenho já sai com menos pixels.
    Personagens encolhem pela altura H; objetos de cena, pelo módulo S. O nome ganha o sufixo ("meio", "longe")."""
    medida = "S" if issubclass(classe, ObjetoDeCena) else "H"
    nome = kw.pop("nome", classe.nome)
    kw[medida] = round(getattr(classe, medida) * fator)
    return classe(nome=f"{nome}_{sufixo}", **kw)