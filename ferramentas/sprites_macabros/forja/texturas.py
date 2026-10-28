"""Texturas e acabamentos reutilizáveis: pelagem, quitina, escamas, casca, musgo, rachaduras com
brasa, líquido escorrendo, cristal translúcido, aura, fumaça e partículas.

Quase todas trabalham sobre o que JÁ foi pintado (escurecem/clareiam a cor do sombreamento),
então servem para qualquer material. Elas recebem uma 'ancora': um ponto que acompanha a peça.
O padrão da textura é calculado em relação a ela, e por isso anda junto com a peça entre os
quadros da animação, em vez de "nadar" por cima.
"""
import math
import random

import numpy as np
from scipy import ndimage

from .motor import v2, rgb, misturar, bresenham


# ============================================================
# BASE
# ============================================================

def hash2(x, y, semente=0):
    """Número pseudoaleatório fixo em [0, 1) para cada (x, y) inteiro (funciona com arrays)."""
    x = np.asarray(x, np.int64)
    y = np.asarray(y, np.int64)
    h = (x * 374761393 + y * 668265263 + semente * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFF) / 65536.0


def locais(tela, mask, ancora):
    """Coordenadas inteiras dos pixels da máscara relativas à âncora: (ys, xs, u, v)."""
    ys, xs = np.nonzero(mask)
    ax, ay = int(round(float(ancora[0]))), int(round(float(ancora[1])))
    return ys, xs, xs - ax, ys - ay


def multiplicar(tela, ys, xs, fator):
    """Escurece (<1) ou clareia (>1) os pixels."""
    if len(ys):
        f = np.asarray(fator, np.float32)
        tela.cor[ys, xs] = np.clip(tela.cor[ys, xs] * (f[:, None] if f.ndim else f), 0, 255)


def misturar_cor(tela, ys, xs, cor, t):
    """Puxa os pixels na direção de uma cor (t de 0 a 1)."""
    if len(ys):
        t = np.asarray(t, np.float32)
        t = t[..., None] if t.ndim else t
        tela.cor[ys, xs] = tela.cor[ys, xs] * (1 - t) + np.array(rgb(cor), np.float32) * t


def pintado(tela, mask):
    return np.asarray(mask, bool) & (tela.alfa > 0)


def borda(mask, direcao):
    """Pixels da máscara cujo vizinho na direção (dx, dy) está fora dela."""
    dx, dy = direcao
    viz = np.zeros_like(mask)
    h, w = mask.shape
    ys = slice(max(0, -dy), h - max(0, dy))
    yd = slice(max(0, dy), h - max(0, -dy))
    xs = slice(max(0, -dx), w - max(0, dx))
    xd = slice(max(0, dx), w - max(0, -dx))
    viz[ys, xs] = mask[yd, xd]
    return mask & ~viz


# ============================================================
# PELE, PELO, QUITINA, ESCAMAS
# ============================================================

def tufos(tela, mask, ancora, direcao=(0, -1), comp=3, espaco=3, larg=1.4, inclina=-0.6, semente=2):
    """Máscara de tufos (triângulos) brotando da borda. Somada à máscara ANTES do pintar(),
    vira silhueta peluda/espinhenta já sombreada junto com o corpo."""
    mask = np.asarray(mask, bool)
    b = borda(mask, direcao)
    ys, xs, u, v = locais(tela, b, ancora)
    out = np.zeros_like(mask)
    if not len(ys):
        return out
    dx, dy = direcao
    ao_longo = u * (-dy) + v * dx
    sel = (np.mod(ao_longo, espaco) == 0) & (hash2(u, v, semente) < 0.85)
    ang = math.atan2(dy, dx) + inclina * (1 if dy <= 0 else -1)
    d = v2(math.cos(ang), math.sin(ang))
    t = v2(-dy, dx) * larg
    for x, y, hh in zip(xs[sel], ys[sel], hash2(u[sel], v[sel], semente + 1)):
        p = v2(x, y)
        n = comp * (0.6 + 0.8 * hh)
        out |= tela.poly([p - t, p + t, p + d * n])
    return out


def pelagem(tela, mask, ancora, ang=math.pi, comp=3, densidade=0.3, contraste=0.24, semente=1):
    """Fios de pelo: traços curtos na direção 'ang' (0 = direita, pi = para trás) que escurecem
    (e às vezes clareiam de leve) a cor já pintada."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    h = hash2(u, v, semente)
    sel = h < densidade
    d = (math.cos(ang), math.sin(ang))
    for x, y, hh in zip(xs[sel], ys[sel], h[sel]):
        escuro = (hh * 13.7) % 1 < 0.78
        f = 1 - contraste if escuro else 1 + contraste * 0.45
        n = comp - 1 + int((hh * 7.3) % 1 * 2.5)
        for k in range(n):
            px, py = int(round(x + d[0] * k)), int(round(y + d[1] * k))
            if 0 <= px < tela.w and 0 <= py < tela.h and mask[py, px]:
                tela.cor[py, px] = np.clip(tela.cor[py, px] * f, 0, 255)


def franja(tela, mask, ancora, direcao=(0, -1), comp=2, espaco=3, inclina=-0.6, escurece=0.9, semente=2,
           so_vazio=True):
    """Tufos saindo da borda para fora (pelo eriçado, espinhos, fiapos de trapo)."""
    mask = pintado(tela, mask)
    b = borda(mask, direcao)
    ys, xs, u, v = locais(tela, b, ancora)
    if not len(ys):
        return
    h = hash2(u, v, semente + 7)
    sel = h < 1.0 / espaco
    ang = math.atan2(direcao[1], direcao[0]) + inclina * (1 if direcao[1] <= 0 else -1)
    for x, y, hh in zip(xs[sel], ys[sel], h[sel]):
        n = max(1, comp + int((hh * espaco * 5.1) % 2) - (1 if hh * espaco < 0.3 else 0))
        cor = tela.cor[y, x] * escurece
        for k in range(1, n + 1):
            px, py = int(round(x + math.cos(ang) * k)), int(round(y + math.sin(ang) * k))
            if 0 <= px < tela.w and 0 <= py < tela.h and (tela.alfa[py, px] == 0 or not so_vazio):
                tela.cor[py, px] = cor
                tela.alfa[py, px] = 255
                tela.emite[py, px] = False


def quitina(tela, mask, ancora, eixo=(1, 0), espaco=5, brilho=0.4, poros=0.03, semente=3):
    """Placas de carapaça: sulcos transversais ao eixo, borda clara em cada placa e brilho úmido."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    e = np.array(eixo, float) / (np.linalg.norm(eixo) or 1)
    s = u * e[0] + v * e[1]
    pos = np.mod(s, espaco)
    sulco = pos < 1
    multiplicar(tela, ys[sulco], xs[sulco], 0.58)
    crista = (pos >= 1) & (pos < 2)
    multiplicar(tela, ys[crista], xs[crista], 1.18)
    furo = hash2(u, v, semente) < poros
    multiplicar(tela, ys[furo], xs[furo], 0.7)
    if brilho:
        lum = tela.cor[ys, xs].mean(-1)
        limiar = np.percentile(lum, 90)
        topo = lum >= limiar
        misturar_cor(tela, ys[topo], xs[topo], (245, 240, 255), brilho)


def escamas(tela, mask, ancora, tam=3, escurece=0.7, clareia=1.15):
    """Escamas em fileiras desencontradas (répteis, dragões, peixes)."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    linha = np.floor_divide(v, tam)
    cx = np.mod(u + (linha % 2) * (tam // 2), tam)
    cy = np.mod(v, tam)
    contorno = (cy == tam - 1) | ((cx == 0) & (cy >= tam // 2))
    multiplicar(tela, ys[contorno], xs[contorno], escurece)
    topo = (cy == 0) & (cx > 0) & (cx < tam - 1)
    multiplicar(tela, ys[topo], xs[topo], clareia)


def penas(tela, mask, ancora, eixo=(-1, 0.25), tam=4, escurece=0.66, clareia=1.12):
    """Penas sobrepostas: fileiras de 'escamas' alongadas na direção do eixo, com raque clara."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    e = np.array(eixo, float) / (np.linalg.norm(eixo) or 1)
    n = np.array([-e[1], e[0]])
    a = u * e[0] + v * e[1]
    b = u * n[0] + v * n[1]
    fila = np.floor(b / tam)
    pos = np.mod(a + (fila % 2) * tam, tam * 2)
    contorno = (np.mod(b, tam) < 1) | (pos < 1)
    multiplicar(tela, ys[contorno], xs[contorno], escurece)
    raque = np.abs(np.mod(b, tam) - tam / 2) < 0.5
    multiplicar(tela, ys[raque & ~contorno], xs[raque & ~contorno], clareia)


def manchas(tela, mask, ancora, cor, escala=5, quantidade=0.35, forca=0.7, semente=4):
    """Manchas irregulares (pelagem malhada, mofo, apodrecimento, ferrugem)."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    campo = ruido_suave(u, v, escala, semente)
    sel = campo > 1 - quantidade
    t = np.clip((campo[sel] - (1 - quantidade)) / max(quantidade, 1e-3) * 2.5, 0, 1) * forca
    misturar_cor(tela, ys[sel], xs[sel], cor, t)


def listras(tela, mask, ancora, cor, eixo=(1, 0), espaco=6, larg=1.6, ondula=1.5, forca=0.85, semente=5):
    """Listras transversais ao eixo, onduladas (tigre, zebra, tatuagens)."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    e = np.array(eixo, float) / (np.linalg.norm(eixo) or 1)
    n = np.array([-e[1], e[0]])
    a = u * e[0] + v * e[1]
    b = u * n[0] + v * n[1]
    a = a + np.sin(b * 0.45 + hash2(np.floor_divide(a, espaco), 0, semente) * 6) * ondula
    pos = np.mod(a, espaco)
    larg_local = larg * (0.6 + 0.8 * hash2(np.floor_divide(a, espaco), np.floor_divide(b, 3), semente + 1))
    sel = pos < larg_local
    misturar_cor(tela, ys[sel], xs[sel], cor, forca)


def ruido_suave(u, v, escala, semente=0):
    """Ruído de valor interpolado (manchas suaves), em [0, 1)."""
    fu, fv = np.asarray(u, float) / escala, np.asarray(v, float) / escala
    iu, iv = np.floor(fu).astype(np.int64), np.floor(fv).astype(np.int64)
    tu, tv = fu - iu, fv - iv
    tu, tv = tu * tu * (3 - 2 * tu), tv * tv * (3 - 2 * tv)
    a, b = hash2(iu, iv, semente), hash2(iu + 1, iv, semente)
    c, d = hash2(iu, iv + 1, semente), hash2(iu + 1, iv + 1, semente)
    return (a * (1 - tu) + b * tu) * (1 - tv) + (c * (1 - tu) + d * tu) * tv


# ============================================================
# MADEIRA, PEDRA, MUSGO
# ============================================================

def casca(tela, mask, ancora, eixo=(0, -1), espaco=4, ondula=1.4, escurece=0.55, clareia=1.15, fendas=0.05,
          semente=6):
    """Casca de árvore: sulcos ondulados ao longo do 'eixo' (a direção do veio) com cristas claras."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    e = np.array(eixo, float) / (np.linalg.norm(eixo) or 1)
    n = np.array([-e[1], e[0]])
    a = u * e[0] + v * e[1]
    b = u * n[0] + v * n[1]
    col = np.floor_divide(b, espaco)
    b2 = b + np.sin(a * 0.32 + hash2(col, 0, semente) * 6.3) * ondula
    pos = np.mod(b2, espaco)
    sulco = pos < 1.1
    multiplicar(tela, ys[sulco], xs[sulco], escurece)
    crista = (pos >= 1.1) & (pos < 2)
    multiplicar(tela, ys[crista], xs[crista], clareia)
    fenda = (hash2(np.floor_divide(a, 3), col, semente + 3) < fendas) & ~sulco
    multiplicar(tela, ys[fenda], xs[fenda], escurece * 0.9)


def no_da_madeira(tela, c, rx, ry, cor_escura=(30, 18, 14)):
    """Nó na casca: anel escuro com miolo e um fio de luz por cima."""
    m = tela.elipse(c[0], c[1], rx, ry) & (tela.alfa > 0)
    dentro = tela.elipse(c[0], c[1], max(0.6, rx - 1), max(0.6, ry - 1))
    ys, xs = np.nonzero(m & ~dentro)
    misturar_cor(tela, ys, xs, cor_escura, 0.7)
    ys, xs = np.nonzero(m & dentro)
    multiplicar(tela, ys, xs, 0.8)
    tela.px(c[0] - rx * 0.3, c[1] - ry, misturar(tela.cor[int(c[1]) % tela.h, int(c[0]) % tela.w], (255, 230, 200), 0.3))


def musgo(tela, mask, ancora, cor=(70, 96, 40), alcance=3, quantidade=0.55, semente=7):
    """Musgo/limo nas superfícies viradas para cima, em manchas com bordas pontilhadas."""
    mask = pintado(tela, mask)
    topo = borda(mask, (0, -1))
    perto = ndimage.binary_dilation(topo, iterations=alcance, structure=np.array([[0, 0, 0], [0, 1, 0], [0, 1, 0]], bool))
    alvo = perto & mask
    ys, xs, u, v = locais(tela, alvo, ancora)
    if not len(ys):
        return
    campo = ruido_suave(u, v, 4, semente)
    sel = campo + tela.bayer[ys, xs] * 0.35 > 1 - quantidade
    escuro = np.array(rgb(cor), np.float32)
    lum = tela.cor[ys[sel], xs[sel]].mean(-1, keepdims=True) / 140.0
    tela.cor[ys[sel], xs[sel]] = np.clip(escuro * (0.55 + 0.6 * lum), 0, 255)


def rachaduras(tela, mask, ancora, area=(10, 10), n=4, passos=6, cor=(255, 130, 40), emite=True, semente=8,
               brilho=0.3, borda_cor=None):
    """Rachaduras em zigue-zague. Com 'emite', viram fendas de brasa/luz com halo;
    sem, são fissuras escuras (pedra, osso, gelo)."""
    mask = pintado(tela, mask)
    rng = random.Random(semente)
    ax, ay = float(ancora[0]), float(ancora[1])
    borda_cor = borda_cor or (misturar(cor, (40, 10, 0), 0.55) if emite else None)
    caminho_total = []
    for _ in range(n):
        p = v2(ax + rng.uniform(-area[0], area[0]), ay + rng.uniform(-area[1], area[1]))
        ang = rng.uniform(0, 2 * math.pi)
        pts = [p]
        for _ in range(passos):
            ang += rng.uniform(-0.9, 0.9)
            p = p + v2(math.cos(ang), math.sin(ang)) * rng.uniform(1.5, 3.0)
            pts.append(p)
        caminho_total.append(pts)
    for pts in caminho_total:
        for i in range(len(pts) - 1):
            for x, y in bresenham(pts[i], pts[i + 1]):
                if not (0 <= x < tela.w and 0 <= y < tela.h and mask[y, x]):
                    continue
                if borda_cor is not None:
                    for dx, dy in ((1, 0), (0, 1)):
                        qx, qy = x + dx, y + dy
                        if 0 <= qx < tela.w and 0 <= qy < tela.h and mask[qy, qx] and not tela.emite[qy, qx]:
                            tela.cor[qy, qx] = tela.cor[qy, qx] * 0.5 + np.array(rgb(borda_cor), np.float32) * 0.5
                tela.cor[y, x] = rgb(cor)
                tela.emite[y, x] = emite
        if emite and brilho:
            tela.brilho(pts[len(pts) // 2], 5, cor, brilho, halo=False)
    return caminho_total


# ============================================================
# LÍQUIDOS
# ============================================================

def escorrer(tela, mask, ancora, cor, densidade=0.25, comp=6, fase=0.0, molhado=0.55, semente=9, gota=True,
             brilho_cor=None):
    """Líquido escorrendo pela peça e pingando da borda de baixo (lodo, água, sangue, cera).

    O fio que pinga cresce e encolhe com a 'fase' (anima sozinho nos quadros)."""
    mask = pintado(tela, mask)
    if not mask.any():
        return
    cor = np.array(rgb(cor), np.float32)
    brilho_cor = np.array(rgb(brilho_cor or misturar(tuple(cor), (255, 255, 255), 0.55)), np.float32)
    ax = int(round(float(ancora[0])))
    colunas = np.nonzero(mask.any(axis=0))[0]
    for x in colunas:
        h = float(hash2(x - ax, 0, semente))
        if h >= densidade:
            continue
        linhas = np.nonzero(mask[:, x])[0]
        y_topo, y_base = linhas[0], linhas[-1]
        inicio = int(y_topo + (y_base - y_topo) * ((h / densidade * 3.7) % 1) * 0.6)
        for y in range(inicio, y_base + 1):                                       # trilha molhada
            if mask[y, x]:
                tela.cor[y, x] = tela.cor[y, x] * (1 - molhado) + cor * molhado
        if 0 <= x - 1 and mask[min(y_base, inicio + 1), x - 1]:
            tela.cor[min(y_base, inicio + 1), x - 1] = brilho_cor
        n = int(round(comp * (0.3 + 0.7 * ((h * 11.3) % 1)) * (0.55 + 0.45 * math.sin(fase + h * 40))))
        for k in range(1, n + 1):                                                # fio pingando
            y = y_base + k
            if y < tela.h and tela.alfa[y, x] == 0:
                tela.cor[y, x] = cor
                tela.alfa[y, x] = 255
        if gota and n >= 2 and y_base + n + 2 < tela.h and tela.alfa[y_base + n + 2, x] == 0:
            tela.cor[y_base + n + 2, x] = brilho_cor
            tela.alfa[y_base + n + 2, x] = 255


def brilho_umido(tela, mask, ancora, densidade=0.05, cor=(235, 245, 230), semente=10):
    """Pontos de reflexo molhado nas partes mais iluminadas (pele afogada, lodo, olhos)."""
    mask = pintado(tela, mask)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return
    lum = tela.cor[ys, xs].mean(-1)
    claro = lum >= np.percentile(lum, 75)
    sel = claro & (hash2(u, v, semente) < densidade)
    misturar_cor(tela, ys[sel], xs[sel], cor, 0.75)


# ============================================================
# CRISTAL, AURA, FUMAÇA, PARTÍCULAS
# ============================================================

def cristal(tela, mask, mat, ancora, opacidade=0.62, facetas=4, reflexo=0.55, periodo=11, semente=11,
            nucleo=None):
    """Cristal/gelo translúcido: sombreado, semitransparente, com arestas de facetas claras e
    uma faixa diagonal de reflexo 'falso' (o brilho de vidro)."""
    mask = tela.vidro(mask, mat, opacidade)
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return mask
    rng = random.Random(semente)
    for _ in range(facetas):                                                     # arestas internas
        a = v2(float(ancora[0]) + rng.uniform(-8, 8), float(ancora[1]) + rng.uniform(-10, 10))
        ang = rng.uniform(-1.2, 1.2) - math.pi / 2
        b = a + v2(math.cos(ang), math.sin(ang)) * rng.uniform(6, 16)
        for x, y in bresenham(a, b):
            if 0 <= x < tela.w and 0 <= y < tela.h and mask[y, x]:
                tela.cor[y, x] = np.clip(tela.cor[y, x] * 1.25 + 18, 0, 255)
    if reflexo:                                                                   # faixa de reflexo
        d = np.mod(u + v * 0.75, periodo)
        faixa = (d < 1.6) | ((d > 3.2) & (d < 3.9))
        misturar_cor(tela, ys[faixa], xs[faixa], (250, 252, 255), reflexo)
        tela.alfa[ys[faixa], xs[faixa]] = np.maximum(tela.alfa[ys[faixa], xs[faixa]], 225)
    topo = borda(mask, (0, -1)) | borda(mask, (-1, 0))                            # aresta iluminada
    yt, xt = np.nonzero(topo)
    misturar_cor(tela, yt, xt, (235, 250, 255), 0.6)
    tela.alfa[yt, xt] = np.maximum(tela.alfa[yt, xt], 235)
    if nucleo is not None:                                                         # brilho interno
        c, r, cor = nucleo
        tela.brilho(c, r, cor, 0.5, halo=False)
    return mask


def vitrificar(tela, mask, ancora, opacidade=0.86, reflexo=0.35, periodo=24, facetas=6, area=(10, 14), semente=14,
               cor_borda=(235, 250, 255)):
    """Transforma em cristal/gelo o que JÁ foi pintado: arestas de facetas, faixa diagonal de reflexo,
    bordas claras e um pouco de transparência (o fundo aparece através)."""
    mask = pintado(tela, mask) & ~tela.emite
    ys, xs, u, v = locais(tela, mask, ancora)
    if not len(ys):
        return mask
    rng = random.Random(semente)
    for _ in range(facetas):
        a = v2(float(ancora[0]) + rng.uniform(-area[0], area[0]), float(ancora[1]) + rng.uniform(-area[1], area[1]))
        ang = rng.uniform(-1.3, 1.3) - math.pi / 2
        b = a + v2(math.cos(ang), math.sin(ang)) * rng.uniform(5, 14)
        for x, y in bresenham(a, b):
            if 0 <= x < tela.w and 0 <= y < tela.h and mask[y, x]:
                tela.cor[y, x] = np.clip(tela.cor[y, x] * 1.22 + 16, 0, 255)
    d = np.mod(u + v * 0.75, periodo)
    faixa = (d < 1.2) & (hash2(np.floor_divide(u + v * 0.75, periodo).astype(np.int64), 0, semente) < 0.5)
    misturar_cor(tela, ys[faixa], xs[faixa], (250, 252, 255), reflexo)
    topo = borda(mask, (0, -1)) | borda(mask, (-1, 0))
    yt, xt = np.nonzero(topo)
    misturar_cor(tela, yt, xt, cor_borda, 0.45)
    corpo = mask & ~topo
    corpo[ys[faixa], xs[faixa]] = False
    tela.alfa[corpo] = np.minimum(tela.alfa[corpo], int(255 * opacidade))
    return mask


def aura(tela, mask, cor, raio=5, forca=0.6, fase=0.0, pulsar=0.25):
    """Brilho em volta da silhueta (vai para o halo semitransparente fora do sprite)."""
    mask = np.asarray(mask, bool)
    if not mask.any():
        return
    dist = ndimage.distance_transform_edt(~mask)
    f = np.clip(1 - dist / raio, 0, 1) ** 1.4 * forca * (1 + pulsar * math.sin(fase))
    f[mask] = 0
    tela.halo[..., :3] += f[..., None] * np.array(rgb(cor), np.float32)
    tela.halo[..., 3] += f


def luz_de_borda(tela, mask, cor, direcao=(1, 0), forca=0.5, largura=1):
    """Contraluz colorida no lado de onde vem uma luz forte (fogo, eclipse, lua)."""
    mask = pintado(tela, mask)
    alvo = borda(mask, direcao)
    for _ in range(largura - 1):
        alvo |= borda(mask & ~alvo, direcao)
    ys, xs = np.nonzero(alvo & ~tela.emite)
    misturar_cor(tela, ys, xs, cor, forca)


def esfumacar(tela, mask, ancora, cor=(20, 16, 28), fase=0.0, comeu=0.45, fiapos=8, sobe=8, semente=12):
    """Bordas que se desfazem em fumaça: corrói a silhueta com ruído e solta fiapos para cima."""
    mask = pintado(tela, mask)
    perto = mask & ~ndimage.binary_erosion(mask, iterations=2)
    ys, xs, u, v = locais(tela, perto, ancora)
    if len(ys):
        campo = ruido_suave(u, v - fase * 3, 3, semente)
        some = campo > 1 - comeu
        tela.alfa[ys[some], xs[some]] = 0
    rng = random.Random(semente)
    topo = np.argwhere(borda(mask, (0, -1)))
    if not len(topo):
        return
    for i in range(fiapos):
        y, x = topo[rng.randrange(len(topo))]
        t = (fase / (2 * math.pi) + i / fiapos) % 1
        for k in range(int(2 + t * sobe)):
            px = int(round(x + math.sin(k * 0.7 + i + fase) * 1.5))
            py = int(y - k - t * 2)
            if 0 <= px < tela.w and 0 <= py < tela.h and tela.alfa[py, px] == 0 and tela.bayer[py, px] > t - 0.6:
                tela.cor[py, px] = rgb(cor)
                tela.alfa[py, px] = 255


def particulas(tela, centro, area, cor, n=8, fase=0.0, sobe=10, semente=13, emite=True, brilho=0.0, tam=1,
               apagar=None):
    """Partículas flutuando (esporos, brasas, neve, luz). A posição dá a volta com a 'fase',
    então o loop dos quadros fica perfeito."""
    rng = random.Random(semente)
    c = v2(centro)
    apagar = apagar or misturar(cor, (20, 16, 24), 0.6)
    for i in range(n):
        x0, y0 = rng.uniform(-area[0], area[0]), rng.uniform(-area[1], area[1])
        t = (fase / (2 * math.pi) + rng.random()) % 1
        p = c + v2(x0 + math.sin(t * 2 * math.pi + i) * 2, y0 - t * sobe)
        cor_t = misturar(cor, apagar, max(0.0, t - 0.5) * 1.6)
        for dx in range(tam):
            for dy in range(tam):
                tela.px(p[0] + dx, p[1] + dy, cor_t, emite=emite)
        if brilho:
            tela.brilho(p, 3, cor, brilho * (1 - t), halo=True)
