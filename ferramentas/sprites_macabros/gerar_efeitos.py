"""Gera os projéteis do combate (assets/efeitos/*.png + efeitos.json) com a forja dos sprites.

Cada PNG tem duas linhas: VOO (4 quadros em loop, já com o rastro) e IMPACTO (5 quadros, tocados
uma vez no alvo). Tudo olha para a DIREITA (o jogo espelha). "centro" é o ponto do quadro que fica
na posição do projétil. Orbe e lança são pintados em branco/cinza: o jogo tinge com a cor do golpe.

    python gerar_efeitos.py
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image

from forja.motor import Tela, Mat, metal, v2, lerp
from forja import fx

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "..", "..", "assets", "efeitos")
VOO, IMPACTO = 4, 5

MADEIRA = Mat((150, 104, 62), 5, relevo=1.0, ruido=0.2)
FERRO = metal((124, 124, 136))
PENA = Mat((176, 40, 42), 5, relevo=0.8)
BRANCO = (255, 255, 255)
CLARO = (232, 232, 236)
CINZA = (196, 196, 204)


def tela(w, h, i):
    return Tela(w, h, semente=17 + i, forca_borda=0.0, geo_rapida=True)


def com_rastro(rastro, corpo, contorno=True):
    """O rastro (translúcido, sem contorno) fica atrás do corpo do projétil."""
    fundo = rastro.finalizar(contorno=False, borda=False)
    return Image.alpha_composite(fundo, corpo.finalizar(contorno=contorno, borda=False))


def direcao(a):
    return v2(math.cos(a), math.sin(a))


def translucido(t, mask, cor, alfa=255, emite=True):
    """Pinta cor única semitransparente (cria o pixel; onde já há algo, fica o mais opaco)."""
    mask = np.asarray(mask, bool)
    t.cor[mask] = np.array(cor, np.float32)
    t.alfa[mask] = np.maximum(t.alfa[mask], alfa)
    t.emite[mask] = emite


def estilhacos(t, c, raio, n, cor, tam=1.5, semente=0, emite=False, alfa=255):
    """Pedacinhos voando para fora do centro (lascas, cacos, brasas)."""
    rng = random.Random(semente)
    for k in range(n):
        a = k * 2 * math.pi / n + rng.uniform(-0.3, 0.3)
        p = c + direcao(a) * raio * rng.uniform(0.75, 1.1)
        q = p + direcao(a) * tam * 1.6
        translucido(t, t.capsula(p, q, max(0.6, tam * 0.5)), cor, alfa, emite)


def anel(t, c, r, larg, cor, alfa=255, emite=True):
    translucido(t, t.circulo(c, r) & ~t.circulo(c, max(0.1, r - larg)), cor, alfa, emite)


# ============================================================
# FLECHA
# ============================================================

def flecha_voo(i):
    t, r = tela(48, 12, i), tela(48, 12, i)
    rng = random.Random(i)
    for k, y in enumerate((5, 6, 7)):                                   # rastro: riscos de vento
        x0, x1 = rng.randint(0, 5), 12 + rng.randint(-2, 1)
        translucido(r, r.poly([v2(x0, y - 0.5), v2(x1, y - 0.5), v2(x1, y + 0.5), v2(x0, y + 0.5)]), (236, 228, 210),
                    90 if k == 1 else 50)
    s = (1 if i % 2 else -1) * 0.6
    t.pintar(t.poly([v2(13, 6), v2(19, 6), v2(10, 2 + s)]), PENA)          # penas
    t.pintar(t.poly([v2(13, 6), v2(19, 6), v2(10, 10 + s)]), PENA.escuro(1))
    t.traco(v2(12, 4 + s * 0.5), v2(17, 5.5), (230, 220, 210))
    t.pintar(t.capsula(v2(11, 6), v2(38, 6), 0.75), MADEIRA)               # haste
    t.px(11, 6, (60, 40, 30))
    t.pintar(t.poly([v2(37, 3.5), v2(45, 6), v2(37, 8.5), v2(38.5, 6)]), FERRO)    # ponta farpada
    t.traco(v2(38.5, 5.5), v2(44, 6), (230, 232, 240))
    return com_rastro(r, t)


def flecha_impacto(i):
    t = tela(32, 32, i)
    c = v2(16, 16)
    if i <= 1:                                                           # clarão em estrela
        r = 7 - i * 2
        for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
            t.chapado(t.poly([c + direcao(a) * r, c + direcao(a + 0.5) * 1.5, c + direcao(a - 0.5) * 1.5]), (255, 240, 200), emite=True)
        t.chapado(t.circulo(c, 2.2 - i * 0.6), BRANCO, emite=True)
        t.brilho(c, 9 - i * 2, (255, 230, 170), 0.8)
    if i >= 1:                                                           # lascas de madeira e poeira
        estilhacos(t, c, 3 + i * 3, 6 - (i >= 3) * 2, (150, 104, 62), 1.4, semente=3)
        fx.fumaca(t, c + v2(0, 2), 3 + i * 1.5, cor=(170, 160, 150), fase=i, n=3, sobe=i * 1.5)
    return t.finalizar(contorno=i <= 2)


# ============================================================
# ORBE (tingido pelo jogo)
# ============================================================

def orbe_voo(i):
    t, r = tela(28, 20, i), tela(28, 20, i)
    c = v2(18, 10)
    for k in range(6):                                                   # cauda de cometa
        p = c - v2(3 + k * 2.4, math.sin(i * 1.6 + k) * 0.8)
        translucido(r, r.circulo(p, 3.6 - k * 0.45), CLARO, 200 - k * 28)
    anel(t, c, 5.6, 1.2, CINZA)
    t.chapado(t.circulo(c, 4.2), CLARO, emite=True)
    t.chapado(t.circulo(c + v2(-1, -1), 2.2), BRANCO, emite=True)
    for k in range(3):                                                   # faíscas orbitando
        a = i * math.pi / 2 + k * 2 * math.pi / 3
        t.px(*(c + direcao(a) * 7.5), BRANCO, emite=True)
    t.brilho(c, 10, BRANCO, 0.75)
    return com_rastro(r, t, contorno=False)


def orbe_impacto(i):
    t = tela(36, 36, i)
    c = v2(18, 18)
    if i == 0:
        t.chapado(t.circulo(c, 6), BRANCO, emite=True)
        anel(t, c, 8.5, 1.5, CLARO)
        t.brilho(c, 14, BRANCO, 1.0)
    else:
        r = 7 + i * 2.5
        anel(t, c, r, 2.0 if i < 3 else 1.0, CLARO, alfa=255 if i < 3 else 150)
        estilhacos(t, c, r - 3, 8, BRANCO, 1.0, semente=5, emite=True, alfa=255 if i < 4 else 120)
        if i < 3:
            t.chapado(t.circulo(c, 4 - i), CLARO, emite=True)
            t.brilho(c, 10, BRANCO, 0.6 - i * 0.15)
    return t.finalizar(contorno=False)


# ============================================================
# LANÇA (tingida pelo jogo: gelo, luz, sombra...)
# ============================================================

CRISTAL = Mat((214, 214, 222), 5, relevo=1.3, especular=BRANCO)


def lanca_voo(i):
    t, r = tela(48, 12, i), tela(48, 12, i)
    rng = random.Random(i * 7)
    for k in range(5):                                                   # rastro de lascas de cristal e névoa
        x = 1 + k * 2.2 + rng.uniform(-0.8, 0.8)
        y = 6 + rng.uniform(-3, 3)
        translucido(r, r.poly([v2(x, y - 1.2), v2(x + 3, y), v2(x, y + 1.2)]), CLARO, 90 + k * 30)
    translucido(r, r.poly([v2(4, 5), v2(12, 5), v2(12, 7), v2(4, 7)]), CINZA, 60)
    t.pintar(t.capsula(v2(11, 6), v2(35, 6), 1.1), CRISTAL)                # haste
    t.traco(v2(12, 5), v2(34, 5), BRANCO)
    for x in (16, 24):                                                   # anéis de facetas
        t.traco(v2(x, 4.5), v2(x, 7.5), CINZA)
    t.pintar(t.poly([v2(33, 2.5), v2(47, 6), v2(33, 9.5), v2(35, 6)]), CRISTAL)     # ponta facetada
    t.traco(v2(35, 6), v2(46, 6), BRANCO)
    t.traco(v2(34, 3.5), v2(44, 5.5), CINZA)
    t.brilho(v2(44, 6), 6, BRANCO, 0.55)
    return com_rastro(r, t)


def lanca_impacto(i):
    t = tela(36, 36, i)
    c = v2(18, 18)
    if i == 0:
        t.chapado(t.circulo(c, 4), BRANCO, emite=True)
        t.brilho(c, 12, BRANCO, 0.9)
    rng = random.Random(9)
    for k in range(8):                                                   # a lança se estilhaça
        a = k * math.pi / 4 + rng.uniform(-0.2, 0.2)
        p = c + direcao(a) * (2 + i * 3.2)
        giro = a + i * 0.7
        t.pintar(t.poly([p + direcao(giro) * 3, p + direcao(giro + 2.3) * 1.5, p + direcao(giro - 2.3) * 1.5]), CRISTAL)
    if 1 <= i <= 3:
        anel(t, c, 4 + i * 3, 1.0, CLARO, alfa=160)
    return t.finalizar(contorno=i < 4)


# ============================================================
# TEIA
# ============================================================

SEDA = (232, 230, 222)


def rede(t, c, r, giro, cor=SEDA, raios=8):
    """Teia de aranha: raios e três voltas de fio (que cedem um pouco para dentro), em traços de 1 pixel."""
    pontos = lambda rr: [c + direcao(giro + k * 2 * math.pi / raios) * rr for k in range(raios)]
    for p in pontos(r):
        t.traco(c, p, cor)
    for rr in (r * 0.38, r * 0.7, r):
        ps = pontos(rr)
        for a, b in zip(ps, ps[1:] + ps[:1]):
            meio = lerp(a, b, 0.5) + (c - lerp(a, b, 0.5)) * 0.12
            t.tracos([a, meio, b], cor)


def teia_voo(i):
    t = tela(26, 24, i)
    c = v2(15, 12)
    t.traco(v2(1, 12 + (i % 2)), c - v2(9, 0), (150, 148, 142))                  # fio que ficou para trás
    rede(t, c, 9.5, i * math.pi / 16)
    for k in range(3):                                                   # gotas grudentas
        a = i * math.pi / 16 + k * 2.1
        t.px(*(c + direcao(a) * 6), (250, 255, 230))
    t.chapado(t.circulo(c, 1.6), SEDA)
    return t.finalizar()


def teia_impacto(i):
    t = tela(40, 40, i)
    c = v2(20, 20)
    r = (9, 14, 17, 18, 18)[i]
    rede(t, c, r, 0.2, cor=(SEDA, SEDA, SEDA, (200, 198, 190), (150, 148, 142))[i], raios=10)
    if i <= 1:
        estilhacos(t, c, r, 6, SEDA, 1.0, semente=2)
    return t.finalizar(contorno=i < 4)


# ============================================================
# BOLA DE FOGO
# ============================================================

def bola_de_fogo_voo(i):
    t, r = tela(36, 24, i), tela(36, 24, i)
    c = v2(24, 12)
    rng = random.Random(i * 3)
    for k in reversed(range(7)):                                         # cauda de fogo (da ponta para a bola)
        p = c - v2(3 + k * 2.6, math.sin(i * 1.7 + k * 1.3) * 1.4)
        translucido(r, r.circulo(p, 5.2 - k * 0.6), fx.FOGO[max(0, 3 - k // 2)], 255 - k * 25)
    for k in range(4):                                                   # brasas soltas
        p = c - v2(rng.uniform(8, 22), rng.uniform(-6, 6))
        r.px(p[0], p[1], fx.FOGO[3], emite=True)
    t.chapado(t.circulo(c, 6), fx.FOGO[2], emite=True)
    t.chapado(t.circulo(c + v2(0.8, -0.5), 4.2), fx.FOGO[3], emite=True)
    t.chapado(t.circulo(c + v2(1.4, -1), 2.2), fx.FOGO[4], emite=True)
    t.brilho(c, 12, (255, 150, 60), 0.85)
    return com_rastro(r, t, contorno=False)


def bola_de_fogo_impacto(i):
    t = tela(48, 48, i)
    c = v2(24, 26)
    if i == 0:
        t.chapado(t.circulo(c, 7), fx.FOGO[4], emite=True)
        anel(t, c, 9, 2, fx.FOGO[3])
        t.brilho(c, 18, (255, 170, 70), 1.0)
    elif i <= 2:                                                         # a explosão abre
        r = 9 + i * 3
        rng = random.Random(i)
        for k in range(9):
            p = c + direcao(k * 0.7 + i) * r * rng.uniform(0.3, 0.75)
            t.chapado(t.circulo(p, r * rng.uniform(0.35, 0.55)), fx.FOGO[1 + (k % 3)], emite=True)
        t.chapado(t.circulo(c, r * 0.45), fx.FOGO[4 - i], emite=True)
        estilhacos(t, c, r + 3, 10, fx.FOGO[3], 1.0, semente=i, emite=True)
        t.brilho(c, r + 8, (255, 140, 50), 0.8)
    else:                                                                # fumaça e brasas
        fx.fumaca(t, c, 6 + i * 2, cor=(70, 60, 62) if i == 3 else (90, 84, 88), fase=i, n=5, sobe=4 + i * 3)
        estilhacos(t, c - v2(0, i * 2), 10 + i * 3, 7, fx.FOGO[2], 0.8, semente=i, emite=True, alfa=255 if i == 3 else 140)
    return t.finalizar(contorno=i >= 3)


PROJETEIS = {
    "flecha": (flecha_voo, flecha_impacto, (24, 6), False),
    "orbe": (orbe_voo, orbe_impacto, (18, 10), True),
    "lanca": (lanca_voo, lanca_impacto, (26, 6), True),
    "teia": (teia_voo, teia_impacto, (15, 12), False),
    "bola_fogo": (bola_de_fogo_voo, bola_de_fogo_impacto, (24, 12), False),
}


def gerar(nome, voo, impacto, centro, tingir):
    quadros_voo = [voo(i) for i in range(VOO)]
    quadros_imp = [impacto(i) for i in range(IMPACTO)]
    (vw, vh), (iw, ih) = quadros_voo[0].size, quadros_imp[0].size
    folha = Image.new("RGBA", (max(vw * VOO, iw * IMPACTO), vh + ih), (0, 0, 0, 0))
    for i, q in enumerate(quadros_voo):
        folha.paste(q, (i * vw, 0))
    for i, q in enumerate(quadros_imp):
        folha.paste(q, (i * iw, vh))
    folha.save(os.path.join(PASTA, nome + ".png"))
    return {"voo": {"y": 0, "celula": [vw, vh], "quadros": VOO, "centro": list(centro)},
            "impacto": {"y": vh, "celula": [iw, ih], "quadros": IMPACTO, "centro": [iw // 2, ih // 2]},
            "tingir": tingir}


def main():
    meta = {"_comentario": "Gerado por ferramentas/sprites_macabros/gerar_efeitos.py: linha de voo (loop) e de impacto (uma vez)."}
    for nome, (voo, impacto, centro, tingir) in PROJETEIS.items():
        meta[nome] = gerar(nome, voo, impacto, centro, tingir)
        print(nome, "ok")
    with open(os.path.join(PASTA, "efeitos.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
