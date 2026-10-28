"""Paisagem noturna do acampamento em camadas (pixel art na MESMA densidade dos personagens: o jogo amplia 2x).

    python gerar_acampamento.py

Grava em assets/acampamento_noturno/:
    ceu.png        degradê da noite, Via Láctea, estrelas e a lua com halo
    nuvens.png     faixas finas de nuvem iluminadas por baixo pela lua (o jogo faz deslizar devagar)
    montanhas.png  duas cordilheiras com neve, mais claras na base (névoa)
    colina.png     a colina com as ruínas da Cripta (uma janela ainda acesa), cruzes e uma árvore morta
    floresta.png   pinheiros em duas fileiras com luz de lua na borda e a névoa no pé
    chao.png       capim, a clareira de terra batida, o caminho até a taverna, pedras, flores e cogumelos
    frente.png     moldura escura: troncos retorcidos nos cantos e capim alto embaixo (fica NA FRENTE de tudo)
    nevoa_longe.png, nevoa_perto.png   faixas de névoa (alfa em poucos degraus) que o jogo faz deslizar: a de longe
                   no pé da mata, a de perto no chão do plano do fundo (entre a taverna e os NPCs do meio)
    paisagem.json  tamanho, margem de paralaxe, posição da lua e as luzes fixas da paisagem

Tudo em 664 x 360 (640 + 12 de cada lado para a paralaxe). Estilo do jogo: noite puxando para roxo/azul,
pontilhado ordenado (Bayer) nos degradês, silhuetas com contorno escuro e luz de borda vinda da lua.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "assets", "acampamento_noturno")

MARGEM = 12
W, H = 640 + 2 * MARGEM, 360
HORIZONTE = 212                       # pé da floresta; o chão começa um pouco acima
LUA = (MARGEM + 392, 52)
CONTORNO = (8, 6, 14)
CENTRO_DA_COLINA = 214                # a Cripta fica à direita do painel de prestígio (canto de cima à esquerda)

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0)
YY, XX = np.mgrid[0:H, 0:W]
LIMIAR = BAYER[YY % 4, XX % 4]


# ============================================================
# FERRAMENTAS
# ============================================================

class Camada:
    """Imagem RGBA em numpy, com pintura por máscara."""

    def __init__(self):
        self.cor = np.zeros((H, W, 3), np.float32)
        self.alfa = np.zeros((H, W), np.uint8)

    def pintar(self, mask, cor):
        self.cor[mask] = cor
        self.alfa[mask] = 255

    def pontilhar(self, mask, cor, densidade):
        """Pinta só onde o pontilhado deixa (densidade 0..1, pode ser um array)."""
        m = mask & (LIMIAR < densidade)
        self.pintar(m, cor)

    def degrade(self, mask, cores, t):
        """Cores ao longo de t (0..1, array) com pontilhado entre um tom e o próximo."""
        partes = len(cores) - 1
        v = np.clip(t, 0, 0.9999) * partes
        i = np.floor(v).astype(int)
        frac = v - i
        i2 = np.minimum(i + (LIMIAR < frac), partes)
        paleta = np.array(cores, np.float32)
        self.cor[mask] = paleta[i2[mask]]
        self.alfa[mask] = 255

    def contornar(self, cor=CONTORNO):
        cheio = self.alfa > 0
        viz = np.zeros_like(cheio)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            viz |= np.roll(np.roll(cheio, dy, 0), dx, 1)
        self.pintar(viz & ~cheio, cor)

    def borda_de_luz(self, cor, dx=1, dy=-1, mask=None, forca=1.0):
        """Clareia a borda virada para a luz (dx, dy apontam para a luz)."""
        cheio = self.alfa > 0
        vizinho = np.roll(np.roll(cheio, -dy, 0), -dx, 1)
        borda = cheio & ~vizinho
        if mask is not None:
            borda &= mask
        self.cor[borda] = self.cor[borda] * (1 - forca) + np.array(cor, np.float32) * forca

    def salvar(self, nome):
        rgba = np.dstack([np.clip(self.cor, 0, 255), self.alfa]).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").save(os.path.join(PASTA, nome + ".png"))


def molde(desenho):
    """Máscara booleana desenhada com o ImageDraw do PIL (polígonos, elipses...)."""
    img = Image.new("L", (W, H), 0)
    desenho(ImageDraw.Draw(img))
    return np.asarray(img) > 127


def poligono(pts):
    return molde(lambda d: d.polygon([tuple(map(float, p)) for p in pts], fill=255))


def elipse(cx, cy, rx, ry):
    return molde(lambda d: d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255))


def ruido_1d(n, rng, escalas=((48, 1.0), (20, 0.45), (8, 0.2), (3, 0.08))):
    """Ruído suave em 1D (soma de oitavas interpoladas), entre -1 e 1."""
    total = np.zeros(n)
    for passo, peso in escalas:
        pontos = rng.uniform(-1, 1, n // passo + 3)
        x = np.arange(n) / passo
        i = np.floor(x).astype(int)
        f = x - i
        f = f * f * (3 - 2 * f)
        total += (pontos[i] * (1 - f) + pontos[i + 1] * f) * peso
    return total / sum(p for _, p in escalas)


def ruido_2d(rng, passo, passo_x=None):
    """Ruído suave 2D (valores aleatórios numa grade, interpolados), entre 0 e 1. passo_x: esticado na horizontal."""
    passo_x = passo_x or passo
    gh, gw = H // passo + 3, W // passo_x + 3
    grade = rng.uniform(0, 1, (gh, gw))
    y, x = YY / passo, XX / passo_x
    i, j = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = y - i, x - j
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = grade[i, j], grade[i, j + 1]
    c, d = grade[i + 1, j], grade[i + 1, j + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def misturar(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


# ============================================================
# CÉU
# ============================================================

def ceu(rng):
    c = Camada()
    tudo = np.ones((H, W), bool)
    t = np.clip(YY / (HORIZONTE + 10), 0, 1) ** 1.25
    c.degrade(tudo, [(5, 5, 16), (8, 9, 24), (12, 13, 33), (18, 18, 44), (27, 24, 56), (40, 31, 68), (58, 40, 80),
                     (80, 52, 88)], t)
    # halo da lua: anéis pontilhados clareando o céu
    d = np.hypot(XX - LUA[0], YY - LUA[1])
    for raio, cor, forca in ((92, (24, 24, 54), 0.5), (64, (34, 34, 70), 0.55), (42, (52, 52, 92), 0.6),
                             (30, (74, 74, 118), 0.7)):
        c.pontilhar(d < raio, cor, forca * np.clip(1.15 - d / raio, 0, 1))
    # Via Láctea: faixa diagonal de poeira de estrelas
    a, b = np.array([MARGEM - 40, 30.0]), np.array([W - 60, 168.0])
    direcao = (b - a) / np.linalg.norm(b - a)
    normal = np.array([-direcao[1], direcao[0]])
    dist = np.abs((XX - a[0]) * normal[0] + (YY - a[1]) * normal[1])
    nuvem = ruido_2d(rng, 18) * 0.65 + ruido_2d(rng, 7) * 0.35
    faixa = np.exp(-(dist / 26) ** 2) * nuvem * (YY < HORIZONTE - 20)
    c.pontilhar(faixa > 0.18, (30, 28, 62), np.clip(faixa * 0.9, 0, 0.6))
    c.pontilhar(faixa > 0.32, (46, 42, 84), np.clip(faixa * 0.7, 0, 0.45))
    c.pontilhar(faixa > 0.46, (66, 60, 108), np.clip(faixa * 0.5, 0, 0.3))
    # estrelas: muitas pequenas, algumas médias em cruz e poucas grandes com brilho
    ate = HORIZONTE - 14
    for _ in range(520):
        x, y = rng.integers(0, W), int(ate * rng.random() ** 1.35)
        brilho = rng.random() * (1.0 - y / ate * 0.6)
        if brilho < 0.25:
            continue
        cor = [(120, 116, 160), (170, 168, 210), (220, 220, 240), (240, 226, 200), (190, 210, 255)][rng.integers(0, 5)]
        cor = tuple(v * (0.5 + 0.5 * brilho) for v in cor)
        c.cor[y, x], c.alfa[y, x] = cor, 255
    for _ in range(int(220)):                                     # mais estrelas dentro da Via Láctea
        x, y = rng.integers(0, W), rng.integers(0, ate)
        if faixa[y, x] > 0.3 and rng.random() < 0.8:
            c.cor[y, x], c.alfa[y, x] = (200, 196, 230), 255
    estrelas_grandes = []
    for _ in range(26):
        x, y = rng.integers(8, W - 8), rng.integers(4, int(ate * 0.8))
        if np.hypot(x - LUA[0], y - LUA[1]) < 40:
            continue
        cor = [(230, 230, 255), (255, 236, 200), (200, 220, 255)][rng.integers(0, 3)]
        c.cor[y, x] = (255, 255, 255)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c.cor[y + dy, x + dx] = misturar(cor, (40, 40, 80), 0.35)
        estrelas_grandes.append([int(x), int(y)])
    for _ in range(5):                                            # as maiores, com raios longos
        x, y = rng.integers(20, W - 20), rng.integers(10, int(ate * 0.6))
        if np.hypot(x - LUA[0], y - LUA[1]) < 50:
            continue
        for k in range(1, 5):
            cor = misturar((240, 236, 255), (30, 30, 70), k / 5)
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                c.cor[y + dy, x + dx] = cor
        c.cor[y, x] = (255, 255, 255)
        estrelas_grandes.append([int(x), int(y)])
    lua(c, rng)
    return c, estrelas_grandes


def lua(c, rng):
    """Lua cheia levemente minguante: disco com sombreado, mares escuros, crateras e borda clara."""
    cx, cy = LUA
    r = 17
    d = np.hypot(XX - cx, YY - cy)
    disco = d <= r
    # sombra da fase: um disco deslocado escurece a borda esquerda
    sombra = np.hypot(XX - (cx - 9), YY - (cy + 2)) > r + 1
    luz = np.clip(((XX - cx) * 0.5 - (YY - cy) * 0.6) / r * 0.5 + 0.65, 0, 1)
    c.degrade(disco, [(116, 112, 132), (162, 158, 168), (206, 202, 196), (236, 232, 214), (250, 248, 236)], luz)
    mares = ruido_2d(rng, 6) > 0.6
    c.pontilhar(disco & mares, (150, 146, 160), 0.55)
    for _ in range(9):                                          # crateras
        a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0, r - 5)
        x, y, raio = cx + math.cos(a) * rr, cy + math.sin(a) * rr, rng.uniform(1.2, 2.8)
        cr = np.hypot(XX - x, YY - y) <= raio
        c.pintar(disco & cr, (140, 136, 150))
        c.pintar(disco & cr & (np.hypot(XX - x - 0.8, YY - y + 0.8) > raio), (230, 226, 210))
    c.pontilhar(disco & ~sombra, (70, 70, 110), 0.85)            # o lado na sombra fica azulado
    c.pontilhar(disco & ~sombra & (np.hypot(XX - (cx - 9), YY - (cy + 2)) > r + 3), (44, 44, 84), 0.7)
    c.pintar(disco & (d > r - 1) & sombra, (255, 252, 240))     # borda acesa


def nuvens(rng):
    """Fiapos de nuvem esticados na horizontal: corpo escuro, barriga acesa pela lua, pontas pontilhadas."""
    c = Camada()
    forma = ruido_2d(rng, 7, 40) * 0.55 + ruido_2d(rng, 4, 14) * 0.3 + ruido_2d(rng, 2, 5) * 0.15
    perto = np.clip(1 - np.hypot(XX - LUA[0], YY - LUA[1]) / 230, 0, 1)
    for centro, espessura in ((74, 7), (122, 5), (158, 6)):
        faixa = np.exp(-((YY - centro - 5 * np.sin(XX / 90 + centro)) / espessura) ** 2)
        valor = forma * faixa
        corpo = (valor > 0.42) & (YY < HORIZONTE - 34)
        fiapo = (valor > 0.34) & ~corpo & (YY < HORIZONTE - 34)
        c.degrade(corpo, [(20, 18, 42), (26, 23, 52), (34, 29, 62)], np.clip((valor - 0.42) * 4, 0, 1))
        c.pontilhar(fiapo, (24, 21, 48), 0.5)
        grossa = corpo & np.roll(corpo, 1, 0) & np.roll(corpo, 2, 0)          # só onde a nuvem tem corpo
        baixo = grossa & ~np.roll(corpo, -1, 0)                  # a lua acende a barriga das nuvens
        acesa = np.array((40, 36, 76), np.float32) + np.array((80, 76, 100), np.float32) * perto[..., None]
        c.cor[baixo] = acesa[baixo]
    return c


# ============================================================
# MONTANHAS, COLINA DA CRIPTA E FLORESTA
# ============================================================

def montanhas(rng):
    c = Camada()
    xs = np.arange(W)
    # picos triangulares (cada um com encostas tortas) somados a uma base ondulada
    longe = np.full(W, 176.0) + ruido_1d(W, rng, ((40, 1.0), (9, 0.3))) * 5
    topo_dos_picos = np.full(W, 999.0)
    for _ in range(11):
        xi, alt, larg = rng.uniform(0, W), rng.uniform(34, 70), rng.uniform(42, 90)
        tri = alt * np.clip(1 - np.abs(xs - xi) / larg, 0, 1) ** 1.25
        tri += ruido_1d(W, rng, ((6, 1.0), (2, 0.4))) * 2.5 * (tri > 2)
        longe = np.minimum(longe, 176 - tri)
        topo_dos_picos = np.where(176 - tri < longe + 0.5, 176 - alt, topo_dos_picos)
    mask = YY >= longe[None, :]
    t = np.clip((YY - longe[None, :]) / (HORIZONTE + 10 - longe[None, :]), 0, 1)
    c.degrade(mask, [(36, 34, 70), (42, 38, 76), (50, 44, 84), (64, 52, 94)], t)
    # neve nos topos, descendo em listras pelas ravinas (a encosta virada para a lua é mais clara)
    inclinacao = np.gradient(longe)
    profundidade = 10 + 14 * ruido_2d(rng, 9, 3)
    neve = mask & (YY < longe[None, :] + profundidade) & (longe[None, :] < 150)
    lado_da_lua = inclinacao[None, :] > 0
    c.degrade(neve & lado_da_lua, [(176, 180, 218), (136, 140, 190), (98, 100, 152)],
              np.clip((YY - longe[None, :]) / profundidade, 0, 1))
    c.degrade(neve & ~lado_da_lua, [(104, 106, 156), (78, 78, 128), (58, 56, 104)],
              np.clip((YY - longe[None, :]) / profundidade, 0, 1))
    c.pintar(mask & (YY < longe[None, :] + 1) & lado_da_lua, (206, 210, 236))
    # cordilheira mais perto, mais escura
    perto = 172 + ruido_1d(W, rng, ((70, 1.0), (24, 0.4), (7, 0.15))) * 16
    mask2 = YY >= perto[None, :]
    t2 = np.clip((YY - perto[None, :]) / (HORIZONTE + 10 - perto[None, :]), 0, 1)
    c.degrade(mask2, [(27, 26, 54), (32, 30, 62), (42, 38, 74), (58, 48, 88)], t2)
    borda = mask2 & (YY < perto[None, :] + 1.5) & (np.gradient(perto)[None, :] > -0.2)
    c.pintar(borda, (62, 62, 104))
    # névoa no pé das montanhas
    nevoa = (YY > HORIZONTE - 40) & (YY < HORIZONTE + 6)
    c.pontilhar(nevoa & mask, (78, 70, 108), np.clip((YY - (HORIZONTE - 40)) / 46, 0, 1) * 0.55)
    return c


def colina(rng):
    """Colina à esquerda com as ruínas da Cripta no alto, lápides na encosta e uma árvore morta."""
    c = Camada()
    xs = np.arange(W)
    centro = MARGEM + CENTRO_DA_COLINA
    # maciço rochoso: sobe da mata em degraus, platô reto no alto (onde a Cripta assenta) e desce em penhascos
    perfil = [(-214, 224), (-196, 204), (-184, 206), (-170, 186), (-156, 190), (-144, 166), (-130, 168), (-118, 146),
              (-104, 142), (-94, 128), (-88, 126), (-84, 118), (76, 118), (82, 126), (88, 124), (98, 140), (110, 143),
              (120, 160), (132, 157), (144, 178), (158, 182), (172, 198), (192, 202), (214, 224)]
    topo = np.interp(xs, [centro + dx for dx, _ in perfil], [y for _, y in perfil], left=400, right=400)
    platô = (xs > centro - 84) & (xs < centro + 76)
    serrilhado = ruido_1d(W, rng, ((11, 1.0), (4, 0.6), (2, 0.3))) * 7
    topo = topo + np.where(platô, 0, np.abs(serrilhado) * np.clip(np.abs(xs - centro + 4) / 120, 0.3, 1))
    mask = YY >= topo[None, :]
    profundidade = np.clip((YY - topo[None, :]) / 70, 0, 1)
    c.degrade(mask, [(40, 34, 62), (34, 29, 54), (28, 24, 46), (24, 20, 40)], profundidade)
    # estratos da rocha (faixas tortas) e rachaduras verticais
    estratos = np.sin((YY + ruido_2d(rng, 6, 30) * 10) / 4.5) > 0.82
    c.pontilhar(mask & estratos & (YY > topo[None, :] + 3), (20, 17, 34), 0.75)
    for _ in range(26):
        x = int(rng.integers(centro - 190, centro + 190))
        if not (0 <= x < W) or topo[x] > 300:
            continue
        y0 = int(topo[x]) + int(rng.integers(4, 20))
        comp = int(rng.integers(6, 18))
        for k in range(comp):
            xx = x + (k // 4) * int(rng.choice((-1, 1)))
            if 0 <= xx < W and mask[min(H - 1, y0 + k), xx]:
                c.cor[y0 + k, xx] = (16, 13, 28)
    # blocos de rocha facetados pela encosta: face da lua clara, face de baixo escura
    for _ in range(90):
        x = float(rng.uniform(centro - 200, centro + 200))
        xi = int(min(W - 1, max(0, x)))
        if topo[xi] > 300:
            continue
        y = topo[xi] + rng.uniform(2, 46)
        raio = rng.uniform(4, 11)
        lados = int(rng.integers(5, 8))
        pts = [(x + math.cos(k * 2 * math.pi / lados + rng.uniform(-0.3, 0.3)) * raio * rng.uniform(0.7, 1.15),
                y + math.sin(k * 2 * math.pi / lados) * raio * 0.6 * rng.uniform(0.7, 1.15)) for k in range(lados)]
        bloco = poligono(pts) & mask
        if not bloco.any():
            continue
        tom = rng.uniform(0.85, 1.15)
        c.pintar(bloco, tuple(v * tom for v in (34, 29, 54)))
        c.pintar(bloco & ((XX - x) - (YY - y) * 1.2 > raio * 0.15), tuple(v * tom for v in (52, 46, 82)))
        c.pintar(bloco & ((XX - x) - (YY - y) * 1.2 < -raio * 0.55), (21, 18, 36))
        borda = bloco & ~np.roll(bloco, 1, 0)
        c.pintar(borda & (XX > x - raio * 0.3), (78, 72, 112))
    # paredões verticais logo abaixo da beira do platô
    for borda_x, lado in ((centro - 84, -1), (centro + 76, 1)):
        parede = mask & (np.abs(XX - borda_x - lado * 6) < 7) & (YY < topo[None, :] + 26) & (YY > 118)
        c.pontilhar(parede & (np.sin(XX * 1.7) > 0.3), (22, 19, 38), 0.8)
    # a lua (à direita) acende as encostas e as quinas viradas para ela
    inclinacao = np.gradient(topo)
    lado_da_lua = mask & (inclinacao[None, :] > 0.15) & (YY < topo[None, :] + 10)
    c.pontilhar(lado_da_lua, (66, 60, 100), 0.6)
    c.borda_de_luz((96, 90, 136), dx=1, dy=-1, mask=mask, forca=1.0)
    c.pintar(mask & platô[None, :] & (YY < topo[None, :] + 1.5), (84, 78, 120))
    # musgo e moitas escuras agarradas na rocha
    for _ in range(40):
        x = int(rng.integers(centro - 190, centro + 190))
        if 0 <= x < W and topo[x] < 300:
            y = int(topo[x]) + int(rng.integers(0, 30))
            c.pintar(elipse(x, y, rng.uniform(1.5, 3.5), rng.uniform(1, 2)) & mask, (22, 30, 34))
    # a Cripta: nave, torre partida, campanário com cruz, contrafortes e arcos
    base = int(topo[centro]) - 3
    x0, s = centro - 34, 1.3
    # fundação de pedra (muro em blocos) entre o platô e a igreja
    fundacao = poligono([(centro - 82, base + 4), (centro + 74, base + 4), (centro + 72, base - 1), (centro - 80, base - 1)])
    c.pintar(fundacao, (36, 32, 56))
    for k in range(0, 156, 7):
        c.pintar(fundacao & (np.abs(XX - (centro - 80 + k + (3 if (k // 7) % 2 else 0))) < 0.6), (22, 19, 36))
    c.pintar(fundacao & (np.abs(YY - (base + 1.5)) < 0.6), (22, 19, 36))
    c.pintar(fundacao & (YY < base), (70, 64, 102))
    # escadaria esculpida descendo pela encosta direita até a mata
    for k in range(16):
        x = centro + 78 + k * 4 + (k % 2) * 2
        y = int(np.interp(x, xs, topo)) + 1
        c.pintar(poligono([(x - 2, y), (x + 2, y), (x + 2, y + 1), (x - 2, y + 1)]), (74, 68, 104))
        c.cor[y + 1, x - 2:x + 2] = (20, 17, 34)

    def p(dx, dy):
        """Ponto da Cripta: dx para a direita e dy para cima, a partir do canto de baixo da nave."""
        return (x0 + dx * s, base - dy * s)

    pecas = [
        [p(0, 0), p(0, 24), p(30, 40), p(60, 24), p(60, 0)],                                       # nave com telhado
        [p(42, 0), p(42, 56), p(45, 60), p(50, 76), p(55, 60), p(58, 56), p(58, 0)],              # campanário e flecha
        [p(-14, 0), p(-14, 34), p(-11, 39), p(-8, 31), p(-5, 37), p(-3, 28), p(0, 30), p(0, 0)],  # torre partida
        [p(60, 0), p(60, 14), p(66, 18), p(72, 14), p(72, 0)],                                     # capela do lado
        [p(-28, 0), p(-28, 12), p(-24, 16), p(-24, 0)],                                            # pedaço de muro
    ]
    cripta = np.zeros((H, W), bool)
    for pts in pecas:
        cripta |= poligono(pts)
    cripta |= poligono([p(49.4, 76), p(50.6, 76), p(50.6, 86), p(49.4, 86)])                      # cruz da flecha
    cripta |= poligono([p(46.5, 82.6), p(53.5, 82.6), p(53.5, 81.4), p(46.5, 81.4)])
    for k in range(4):                                                                             # contrafortes
        cripta |= poligono([p(5 + k * 13, 0), p(1 + k * 13, 0), p(5 + k * 13, 17)])
    arco_partido = molde(lambda d: d.arc([p(-24, 22)[0], p(-24, 22)[1], p(0, 2)[0], p(0, 2)[1] + 12], 190, 300,
                                         fill=255, width=2))
    cripta |= arco_partido
    c.pintar(cripta, (18, 15, 33))
    c.borda_de_luz((74, 68, 114), dx=1, dy=-1, mask=cripta, forca=0.9)
    rosa = elipse(*p(30, 26), 3.2 * s, 3.2 * s)                                                    # rosácea
    c.pintar(rosa, (120, 54, 60))
    c.pintar(rosa & (np.abs(XX - p(30, 26)[0]) < 0.8), (40, 20, 30))
    c.pintar(rosa & (np.abs(YY - p(30, 26)[1]) < 0.8), (40, 20, 30))
    for dx, dy, acesa in ((8, 6, False), (18, 6, True), (40, 6, False), (50, 36, True), (-8, 18, False),
                          (66, 4, True)):
        x, y = p(dx, dy)
        janela = poligono([(x - 1.6, y + 5), (x - 1.6, y), (x, y - 2.5), (x + 1.6, y), (x + 1.6, y + 5)])
        c.pintar(janela, (255, 196, 110) if acesa else (8, 6, 16))
        if acesa:
            c.pintar(janela & (YY > y + 1.5), (226, 124, 60))
    # lápides no platô, dos dois lados da igreja, e uma ou outra na encosta
    for k in range(16):
        x = int(centro - 82 + k * 10 + rng.integers(-2, 3))
        if x0 - 40 < x < x0 + 98:
            continue
        y = int(topo[min(W - 1, max(0, x))]) + int(rng.integers(0, 3))
        if rng.random() < 0.5:
            lapide = poligono([(x - 2, y + 1), (x - 2, y - 4), (x, y - 6), (x + 2, y - 4), (x + 2, y + 1)])
        else:
            lapide = poligono([(x - 0.5, y + 1), (x - 0.5, y - 7), (x + 0.5, y - 7), (x + 0.5, y + 1)]) | \
                poligono([(x - 2.5, y - 5), (x + 2.5, y - 5), (x + 2.5, y - 4), (x - 2.5, y - 4)])
        c.pintar(lapide, (34, 30, 54))
        c.pintar(lapide & ~np.roll(lapide, 1, 1), (62, 58, 98))
    # árvores mortas retorcidas na beira do platô
    arvore(c, centro - 78, int(topo[centro - 78]) + 1, 40, rng, (16, 14, 30), (60, 56, 94))
    arvore(c, centro + 104, int(topo[centro + 104]) + 2, 28, rng, (16, 14, 30), (60, 56, 94))
    return c


def arvore(c, x, base, altura, rng, cor, cor_luz, grossura=2.0):
    """Árvore seca: tronco torto que se divide em galhos finos (recursivo)."""
    linhas = []

    def galho(p, ang, comp, larg, nivel):
        q = (p[0] + math.cos(ang) * comp, p[1] - math.sin(ang) * comp)
        linhas.append((p, q, larg))
        if nivel <= 0 or comp < 3:
            return
        for desvio in (-0.5 - rng.random() * 0.3, 0.35 + rng.random() * 0.35):
            galho(q, ang + desvio, comp * (0.62 + rng.random() * 0.15), max(0.6, larg * 0.62), nivel - 1)

    galho((x, base), math.pi / 2 + rng.uniform(-0.15, 0.15), altura * 0.45, grossura, 4)
    mask = molde(lambda d: [d.line([p, q], fill=255, width=max(1, int(round(l)))) for p, q, l in linhas])
    c.pintar(mask, cor)
    c.pintar(mask & ~np.roll(mask, -1, 1), cor_luz)


def pinheiro(mask_pts, x, base, altura, largura):
    """Contorno de um pinheiro em camadas (saias serrilhadas)."""
    pts = [(x, base - altura)]
    camadas = max(3, int(altura / 9))
    for k in range(1, camadas + 1):
        y = base - altura + altura * k / camadas
        meia = largura * (k / camadas) ** 0.85
        pts.append((x + meia, y))
        if k < camadas:
            pts.append((x + meia * 0.45, y - 1))
    pts += [(x + 1, base), (x + 1, base + 3), (x - 1, base + 3), (x - 1, base)]
    esquerda = [(2 * x - px, py) for px, py in reversed(pts[1:-4])]
    mask_pts.append(pts[:-4] + [(x + 1, base), (x + 1, base + 3), (x - 1, base + 3), (x - 1, base)] + esquerda)


def floresta(rng):
    c = Camada()
    for fila, (base, alturas, cor, luz) in enumerate((
            (HORIZONTE - 2, (26, 58), (22, 26, 48), (54, 60, 96)),
            (HORIZONTE + 6, (36, 84), (13, 15, 30), (40, 44, 78)))):
        formas = []
        x = rng.integers(0, 10)
        while x < W:
            alt = rng.integers(*alturas)
            if fila == 1 and MARGEM + 250 < x < MARGEM + 390:      # atrás da taverna a mata é mais baixa
                alt = int(alt * 0.55)
            if MARGEM + CENTRO_DA_COLINA - 198 < x < MARGEM + CENTRO_DA_COLINA + 192:   # na frente do maciço também
                alt = int(alt * (0.72 if fila == 1 else 0.8))
            pinheiro(formas, x, base + rng.integers(-3, 4), alt, alt * rng.uniform(0.2, 0.28))
            x += rng.integers(7, 15) if fila == 0 else rng.integers(10, 20)
        mask = np.zeros((H, W), bool)
        for pts in formas:
            mask |= poligono(pts)
        mask |= (YY > base) & (YY < base + 6)
        anterior = c.alfa > 0
        c.pintar(mask, cor)
        c.borda_de_luz(luz, dx=1, dy=-1, mask=mask & ~anterior, forca=0.85)
        if fila == 0:                                           # névoa entre as duas fileiras
            nevoa = (YY > base - 26) & (YY < base + 4) & mask
            c.pontilhar(nevoa, (52, 52, 88), np.clip((YY - (base - 26)) / 30, 0, 1) * 0.5)
    # névoa baixa na frente da mata
    faixa = (YY > HORIZONTE - 6) & (YY < HORIZONTE + 22) & (c.alfa > 0)
    c.pontilhar(faixa, (44, 44, 76), np.clip(1 - np.abs(YY - HORIZONTE - 8) / 14, 0, 1) * 0.45)
    return c


# ============================================================
# CHÃO E MOLDURA DA FRENTE
# ============================================================

CLAREIRA = (MARGEM + 320, 300, 228, 58)          # centro x, y, raio x, raio y (a fogueira fica no meio)


def chao(rng):
    c = Camada()
    topo = HORIZONTE + 8 + ruido_1d(W, rng, ((40, 1.0), (9, 0.4))) * 2
    mask = YY >= topo[None, :]
    t = np.clip((YY - topo[None, :]) / (H - HORIZONTE), 0, 1)
    c.degrade(mask, [(16, 19, 28), (19, 23, 30), (22, 27, 32), (25, 30, 33), (27, 32, 34)], t)
    # manchas de capim mais claro e mais escuro
    manchas = ruido_2d(rng, 14)
    c.pontilhar(mask & (manchas > 0.62), (30, 38, 38), 0.45)
    c.pontilhar(mask & (manchas < 0.3), (14, 16, 24), 0.4)
    # clareira de terra batida em volta da fogueira e o caminho até a taverna
    cx, cy, rx, ry = CLAREIRA
    d = ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2
    largura_do_caminho = 9 + (YY - HORIZONTE) * 0.32
    caminho = (np.abs(XX - cx + 6 - (YY - cy) * 0.1) < largura_do_caminho) & (YY > HORIZONTE + 6) & (YY < cy)
    borda_irregular = ruido_2d(rng, 7) * 0.3 + ruido_2d(rng, 3) * 0.12
    terra = mask & ((d < 1.0 - borda_irregular) | (caminho & (ruido_2d(rng, 4) > 0.2 + (YY - HORIZONTE) / 400)))
    c.degrade(terra, [(28, 25, 30), (34, 29, 33), (40, 33, 35), (46, 37, 37)], np.clip(1.2 - d * 0.9, 0, 1))
    c.pontilhar(terra & (ruido_2d(rng, 2, 4) > 0.72), (24, 22, 27), 0.6)
    c.pontilhar(terra & (ruido_2d(rng, 2, 5) < 0.2), (54, 44, 42), 0.35)
    # sulcos de pegadas e de lenha arrastada (riscos curtos)
    for _ in range(26):
        x, y = rng.integers(cx - rx + 20, cx + rx - 20), rng.integers(cy - ry + 8, cy + ry - 6)
        if terra[y, x]:
            for k in range(rng.integers(3, 7)):
                if terra[y, x + k]:
                    c.cor[y, x + k] = (24, 21, 26)
                    c.cor[y - 1, x + k] = (52, 43, 41)
    # capim mais alto contornando a borda da clareira
    beira = mask & ~terra & (d < 1.45) & (d > 0.75)
    c.pontilhar(beira, (24, 32, 32), 0.55)
    # tufos de capim (riscos verticais) fora da clareira
    for _ in range(900):
        x, y = rng.integers(0, W), rng.integers(HORIZONTE + 10, H)
        if not mask[y, x] or terra[y, x]:
            continue
        alto = 1 + int((y - HORIZONTE) / 40) + rng.integers(0, 2)
        cor = [(28, 40, 38), (36, 50, 44), (22, 30, 32), (44, 58, 48)][rng.integers(0, 4)]
        for k in range(alto):
            yy, xx = y - k, x + (k // 2) * rng.choice((-1, 0, 1))
            if 0 <= yy < H and 0 <= xx < W:
                c.cor[yy, xx], c.alfa[yy, xx] = cor, 255
    # pedras: poucas, em grupinhos, com musgo, topo claro e sombra embaixo (maiores perto da câmera)
    for _ in range(16):
        gx, gy = rng.integers(0, W), rng.integers(HORIZONTE + 18, H - 6)
        if d[gy, gx] < 1.1:
            continue
        for _ in range(rng.integers(1, 4)):
            x, y = gx + rng.integers(-6, 7), gy + rng.integers(-2, 3)
            tam = 0.8 + (y - HORIZONTE) / 60 + rng.random() * 1.4
            pedra = elipse(x, y, tam * 1.6, tam)
            c.pintar(elipse(x + 1.5, y + tam * 0.8, tam * 1.7, tam * 0.5) & mask, (10, 11, 16))
            c.pintar(pedra, (40, 40, 52))
            c.pintar(pedra & (YY < y - tam * 0.1), (58, 58, 72))
            c.pintar(pedra & (YY < y - tam * 0.55) & (XX > x - tam * 0.8), (78, 78, 94))
            c.pintar(pedra & (YY > y + tam * 0.3) & (ruido_2d(rng, 2) > 0.5), (34, 50, 40))
    # florzinhas pálidas e cogumelos que brilham de leve
    for _ in range(70):
        x, y = rng.integers(0, W), rng.integers(HORIZONTE + 12, H - 2)
        if mask[y, x] and not terra[y, x]:
            c.cor[y, x] = [(170, 180, 220), (210, 200, 230), (200, 150, 190)][rng.integers(0, 3)]
            c.cor[y + 1, x] = (36, 52, 44)
    cogumelos = []
    for _ in range(12):
        x, y = rng.integers(MARGEM, W - MARGEM), rng.integers(HORIZONTE + 30, H - 10)
        if terra[y, x]:
            continue
        for k, dx in enumerate((0, 3)):
            chapeu = elipse(x + dx, y - 2 - k, 1.6, 1.0)
            c.pintar(chapeu, (120, 210, 200))
            c.cor[y - k, x + dx] = (190, 200, 190)
        cogumelos.append([int(x), int(y)])
    pedrinhas(c, rng, mask, d)
    return c, cogumelos


def pedrinhas(c, rng, mask, d):
    """Cascalho: pedrinhas na borda da clareira (onde a terra batida vira capim) e outras soltas no capim, maiores
    perto da câmera, com o topo claro e a sombra embaixo."""
    for _ in range(150):
        x, y = int(rng.integers(MARGEM, W - MARGEM)), int(rng.integers(HORIZONTE + 14, H - 4))
        borda = 0.85 < d[y, x] < 1.25
        if not mask[y, x] or not (borda or rng.random() < 0.25):
            continue
        tam = 0.6 + (y - HORIZONTE) / 110 + rng.random() * 0.7
        tom = rng.uniform(0.85, 1.15)
        pedra = elipse(x, y, tam * 1.4, tam * 0.9)
        c.pintar(elipse(x + 1, y + tam * 0.7, tam * 1.5, tam * 0.45) & mask, (12, 12, 18))
        c.pintar(pedra, tuple(v * tom for v in (46, 44, 56)))
        c.pintar(pedra & (YY < y - tam * 0.2), tuple(v * tom for v in (70, 68, 84)))


def frente(rng):
    """Moldura: troncos retorcidos nos cantos e capim alto embaixo, quase pretos (na frente de tudo)."""
    c = Camada()
    escuro, borda = (7, 6, 12), (30, 26, 44)
    # tronco da esquerda saindo do chão e um galho que entra na cena
    tronco = poligono([(0, H), (0, 120), (6, 108), (12, 96), (14, 120), (20, 170), (26, 250), (34, H)])
    tronco |= molde(lambda d: d.line([(10, 112), (34, 92), (52, 88), (70, 76)], fill=255, width=3))
    tronco |= molde(lambda d: d.line([(34, 92), (44, 70), (40, 52)], fill=255, width=2))
    tronco |= molde(lambda d: d.line([(52, 88), (62, 96), (66, 106)], fill=255, width=1))
    # tronco da direita, mais grosso, com um nó
    tronco |= poligono([(W, H), (W, 150), (W - 8, 140), (W - 14, 152), (W - 18, 200), (W - 22, 280), (W - 30, H)])
    tronco |= molde(lambda d: d.line([(W - 12, 158), (W - 34, 140), (W - 50, 136), (W - 62, 122)], fill=255, width=3))
    tronco |= molde(lambda d: d.line([(W - 34, 140), (W - 42, 118), (W - 38, 104)], fill=255, width=2))
    c.pintar(tronco, escuro)
    c.borda_de_luz(borda, dx=1, dy=-1, forca=1.0)
    # capim alto e samambaias na beira de baixo
    capim = np.zeros((H, W), bool)
    for _ in range(170):
        x = rng.integers(0, W)
        alto = rng.integers(5, 16) if (x < 110 or x > W - 110) else rng.integers(3, 8)
        curva = rng.uniform(-4, 4)
        capim |= molde(lambda d, x=x, alto=alto, curva=curva: d.line([(x, H), (x + curva * 0.4, H - alto * 0.6),
                                                                       (x + curva, H - alto)], fill=255, width=1))
    for x in (8, 46, W - 50, W - 14):                        # folhas de samambaia
        for k in range(6):
            ang = math.pi * (0.15 + k * 0.14)
            capim |= molde(lambda d, x=x, ang=ang: d.line([(x, H), (x + math.cos(ang) * 24, H - math.sin(ang) * 18)],
                                                          fill=255, width=2))
    c.pintar(capim, escuro)
    c.pintar(capim & ~np.roll(capim, 1, 0) & (YY < H - 2), (22, 22, 34))
    return c


# ============================================================
# NÉVOA
# ============================================================

# faixas: (nome, centro y, espessura, cor, degraus de alfa); o jogo faz cada uma deslizar devagar (paisagem.json)
NEVOAS = (("nevoa_longe", HORIZONTE + 2, 9, (78, 80, 120), (0, 34, 58, 82)),
          ("nevoa_perto", HORIZONTE + 22, 7, (92, 94, 134), (0, 28, 50, 72)))


def nevoa(rng, centro, espessura, cor, degraus):
    """Faixa de névoa deitada: rolos esticados na horizontal, mais densos no meio, com o alfa em poucos degraus
    (bordas nítidas, como o resto da pixel art). Ela dá a volta: as pontas emendam quando o jogo desliza a faixa."""
    c = Camada()
    forma = ruido_2d(rng, 8, 52) * 0.55 + ruido_2d(rng, 4, 20) * 0.3 + ruido_2d(rng, 2, 7) * 0.15
    emenda = np.clip(np.minimum(XX, W - 1 - XX) / 40, 0, 1)            # as pontas somem: a volta não aparece
    valor = np.exp(-((YY - centro - 3 * np.sin(XX / 70)) / espessura) ** 2) * (0.35 + 0.65 * forma) * emenda
    nivel = np.digitize(valor, (0.22, 0.42, 0.62))
    c.cor[:] = cor
    c.cor[nivel == len(degraus) - 1] = tuple(min(255, v + 14) for v in cor)        # o miolo mais claro
    c.alfa[:] = np.array(degraus, np.uint8)[nivel]
    return c


def main():
    os.makedirs(PASTA, exist_ok=True)
    rng = np.random.default_rng(1913)
    camada_ceu, estrelas = ceu(rng)
    camada_ceu.salvar("ceu")
    nuvens(rng).salvar("nuvens")
    montanhas(rng).salvar("montanhas")
    colina(rng).salvar("colina")
    floresta(rng).salvar("floresta")
    camada_chao, cogumelos = chao(rng)
    camada_chao.salvar("chao")
    frente(rng).salvar("frente")
    for nome, centro, espessura, cor, degraus in NEVOAS:
        nevoa(rng, centro, espessura, cor, degraus).salvar(nome)
    info = {"tamanho": [W, H], "margem": MARGEM, "escala": 2, "horizonte": HORIZONTE, "lua": list(LUA),
            "estrelas_grandes": estrelas, "cogumelos": cogumelos,
            "paralaxe": {"ceu": 0.15, "nuvens": 0.2, "montanhas": 0.3, "colina": 0.45, "floresta": 0.6, "chao": 0.0,
                         "nevoa_longe": 0.55, "nevoa_perto": 0.1, "frente": 1.0},
            "vento_da_nevoa": {"nevoa_longe": 6, "nevoa_perto": -9}}
    with open(os.path.join(PASTA, "paisagem.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    juntar_previa()
    print("paisagem do acampamento em", PASTA)


def juntar_previa():
    """Prévia com todas as camadas empilhadas (ampliada 2x), para conferir."""
    fundo = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    for nome in ("ceu", "nuvens", "montanhas", "colina", "floresta", "nevoa_longe", "chao", "nevoa_perto", "frente"):
        fundo.alpha_composite(Image.open(os.path.join(PASTA, nome + ".png")))
    os.makedirs(os.path.join(AQUI, "previas"), exist_ok=True)
    fundo.crop((MARGEM, 0, W - MARGEM, H)).resize((1280, 720), Image.NEAREST).save(os.path.join(AQUI, "previas", "previa_acampamento.png"))


if __name__ == "__main__":
    main()
