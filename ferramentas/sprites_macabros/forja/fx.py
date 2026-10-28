"""Efeitos mágicos em pixel art: chamas, orbes, raios, gelo, fumaça, runas."""
import math

import numpy as np

from .motor import v2, lerp, dir_ang, misturar, rgb, bresenham

FOGO = [(120, 20, 10), (205, 60, 18), (250, 140, 40), (255, 222, 120), (255, 250, 220)]
FOGO_VERDE = [(20, 70, 30), (40, 150, 60), (110, 225, 90), (200, 255, 170), (240, 255, 230)]
FOGO_AZUL = [(20, 30, 110), (40, 90, 220), (100, 170, 255), (190, 230, 255), (240, 250, 255)]
FOGO_ROXO = [(50, 10, 70), (110, 30, 160), (180, 80, 240), (230, 170, 255), (250, 235, 255)]
GELO = [(40, 70, 120), (80, 140, 200), (140, 205, 240), (210, 245, 255), (250, 255, 255)]
RAIO = [(60, 50, 140), (130, 120, 255), (200, 200, 255), (255, 250, 200), (255, 255, 255)]
SANGUE = [(50, 4, 10), (95, 10, 20), (140, 20, 30), (190, 45, 50)]


def chama(tela, base, altura, largura, cores=FOGO, fase=0.0, linguas=3, emite=True, inclina=0.0, brilho=True):
    """Chama em camadas com línguas que ondulam conforme 'fase' (0..2pi)."""
    base = v2(base)
    camadas = len(cores) - 1
    for k in range(camadas):
        esc = 1 - k / (camadas + 0.6)
        pts = []
        h = altura * esc
        w = largura * esc * 0.5
        n = 14
        # lado esquerdo subindo, línguas no topo, lado direito descendo
        for i in range(n + 1):
            t = i / n
            ang = math.pi * t
            x = -math.cos(ang) * w
            # topo pontudo com línguas
            ling = 0.55 + 0.45 * abs(math.sin(t * math.pi * linguas + fase * (1 + k * 0.3) + k))
            y = -math.sin(ang) ** 0.6 * h * ling
            x += inclina * (-y / max(h, 1)) * w + math.sin(fase + t * 4) * w * 0.15 * (-y / max(h, 1))
            pts.append(base + v2(x, y))
        pts.append(base + v2(w * 0.6, h * 0.12))
        pts.append(base + v2(-w * 0.6, h * 0.12))
        m = tela.poly(pts)
        tela.chapado(m, cores[k + 1] if k == 0 else cores[k + 1], emite=emite)
    # contorno vermelho escuro por baixo das bordas
    if brilho:
        tela.brilho(base + v2(0, -altura * 0.4), max(altura, largura) * 1.1, cores[2], 0.55)


def orbe(tela, c, r, cores, brilho=1.0):
    c = v2(c)
    tela.chapado(tela.circulo(c, r), cores[1], emite=True)
    tela.chapado(tela.circulo(c + v2(-r * 0.15, -r * 0.15), r * 0.7), cores[2], emite=True)
    tela.chapado(tela.circulo(c + v2(-r * 0.3, -r * 0.3), max(0.6, r * 0.35)), cores[-1], emite=True)
    tela.brilho(c, r * 3.2, cores[2], 0.7 * brilho)


def relampago(tela, a, b, cores=RAIO, semente=0, desvio=3.0, galhos=1, grosso=False):
    rng = np.random.default_rng(semente)
    a, b = v2(a), v2(b)
    pts = [a]
    n = max(3, int(np.linalg.norm(b - a) / 4))
    d = b - a
    nrm = v2(-d[1], d[0]) / (np.linalg.norm(d) + 1e-6)
    for i in range(1, n):
        t = i / n
        pts.append(a + d * t + nrm * (rng.random() - 0.5) * 2 * desvio)
    pts.append(b)
    for i in range(len(pts) - 1):
        if grosso:
            tela.traco(pts[i] + v2(1, 0), pts[i + 1] + v2(1, 0), cores[2], emite=True)
        tela.traco(pts[i], pts[i + 1], cores[-1], emite=True)
    for g in range(galhos):
        k = int(rng.integers(1, len(pts) - 1))
        fim = pts[k] + nrm * (rng.random() - 0.5) * 16 + d * 0.15
        tela.traco(pts[k], fim, cores[2], emite=True)
    for p in pts[::2]:
        tela.brilho(p, 5, cores[1], 0.35)


def cristal(tela, base, ang, comp, larg, cores=GELO):
    d = dir_ang(ang)
    n = v2(-d[1], d[0])
    base = v2(base)
    pts = [base - n * larg, base + d * comp * 0.75 - n * larg * 0.9, base + d * comp, base + d * comp * 0.7 + n * larg,
           base + n * larg * 0.8]
    m = tela.poly(pts)
    tela.chapado(m, cores[1], emite=True)
    meio = tela.poly([base, base + d * comp * 0.72 - n * larg * 0.5, base + d * comp * 0.95, base + n * larg * 0.3])
    tela.chapado(m & meio, cores[2], emite=True)
    tela.traco(base + d * comp * 0.2, base + d * comp * 0.85, cores[-1], emite=True, sobre=True)
    return m


def fumaca(tela, c, r, cor=(70, 66, 78), fase=0.0, n=4, sobe=10):
    c = v2(c)
    for k in range(n):
        t = ((fase / (2 * math.pi)) + k / n) % 1
        p = c + v2(math.sin(t * 6 + k) * 3, -t * sobe)
        rr = r * (0.5 + t)
        m = tela.circulo(p, rr) & (tela.alfa == 0)
        tela.chapado(m & (tela.bayer > (t - 0.5)), misturar(cor, (30, 26, 36), t * 0.5))


def runa(tela, c, cor, tam=2, forma=0, emite=True):
    c = v2(c)
    x, y = c
    formas = [
        [((0, -tam), (0, tam)), ((-tam, -tam + 1), (tam, tam - 1))],
        [((-tam, -tam), (tam, -tam)), ((0, -tam), (0, tam)), ((-tam, tam), (0, tam))],
        [((-tam, tam), (0, -tam)), ((0, -tam), (tam, tam)), ((-tam + 1, 0), (tam - 1, 0))],
        [((0, -tam), (0, tam)), ((0, -tam), (tam, -tam + 1)), ((0, 0), (tam, 1))],
    ]
    for a, b in formas[forma % len(formas)]:
        tela.traco(c + v2(a), c + v2(b), cor, emite=emite)


def gota_sangue(tela, p, cor=SANGUE[2]):
    p = v2(p)
    tela.px(p[0], p[1], cor)
    tela.px(p[0], p[1] + 1, SANGUE[1])
