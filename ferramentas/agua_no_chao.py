"""Chão alagado do Reino dos Ratos (etapa 5R1): uma versão da camada "chao" para cada nível da água, seguindo o
terreno.

    Rasa (1)   a água enche as juntas e os buracos do chão: poças espalhadas, achatadas pela perspectiva
    Funda (2)  cobre o chão; só os lugares altos (degraus, o estrado do trono) ficam de fora, molhados
    Alta (3)   cobre tudo e sobe um pouco pela base das paredes e dos móveis do fundo; lixo boiando

A água é turva (verde de esgoto) e reflete o que está atrás (as camadas ceu, longe e meio espelhadas na linha do
chão), com as luzes das velas virando faixas tremidas, ondinhas claras e a borda de cima das poças acesa.

    chao_alagado(camadas, configuracao, horizonte, luzes, semente, altura=None, vezes=1)
        grava os 3 chãos em configuracao["_camadas"] ("chao_agua1".."chao_agua3") e a lista em "chao_alagado"

altura: terreno (0 = chão; 0.5 = um degrau; 1 = alto) do tamanho da camada, ou None (tudo plano).
vezes: 1 nas cenas de 352x180, 2 nas de resolução dobrada (o tamanho das manchas e das ondas acompanha).
"""
import os
import sys

import numpy as np
import pygame
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites_macabros"))
from forja.texturas import hash2, ruido_suave  # noqa: E402

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16
AGUA_LONGE = np.array((42, 74, 52), np.float32)          # a água lá no fundo (pega mais o reflexo)
AGUA_PERTO = np.array((10, 24, 17), np.float32)          # a água perto da câmera (funda e escura)
ONDA = np.array((100, 158, 98), np.float32)
BORDA = np.array((150, 204, 136), np.float32)
REFLEXO = np.array((0.6, 0.8, 0.64), np.float32)         # o reflexo sai escuro e esverdeado
OPACIDADE = {1: 0.62, 2: 0.76, 3: 0.9}                    # quanto a água esconde o chão embaixo dela
FORCA_DO_REFLEXO = {1: 0.32, 2: 0.42, 3: 0.48}
LIMITE = {1: 0.6, 2: 0.06, 3: -9.0}                       # "fundura" mínima para ter água
SOBE = {1: 0, 2: 1, 3: 3}                                  # pixels que a água sobe pela base do fundo


def para_array(sup):
    """(rgb float HxWx3, alfa float HxW de 0 a 1) de uma Surface."""
    rgb = pygame.surfarray.array3d(sup).transpose(1, 0, 2).astype(np.float32)
    alfa = pygame.surfarray.array_alpha(sup).T.astype(np.float32) / 255
    return rgb, alfa


def para_superficie(rgb, alfa):
    altura, largura = alfa.shape
    sup = pygame.Surface((largura, altura), pygame.SRCALPHA)
    pixels = pygame.surfarray.pixels3d(sup)
    pixels[:] = np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2)
    del pixels
    canal = pygame.surfarray.pixels_alpha(sup)
    canal[:] = np.clip(alfa * 255, 0, 255).astype(np.uint8).T
    del canal
    return sup


def compor(camadas):
    """As camadas umas por cima das outras (o que a água reflete)."""
    fundo = None
    for sup in camadas:
        rgb, alfa = para_array(sup)
        fundo = rgb * alfa[..., None] if fundo is None else fundo * (1 - alfa[..., None]) + rgb * alfa[..., None]
    return fundo


def bayer(altura, largura):
    return np.tile(BAYER, (altura // 4 + 1, largura // 4 + 1))[:altura, :largura]


def degraus(f, n, b):
    """Quantiza 0..1 em n degraus com pontilhado (mistura de pixel art, sem degradê liso)."""
    return np.clip(np.floor(f * n + b) / n, 0, 1)


def misturar(a, b, t):
    t = np.asarray(t, np.float32)
    return a * (1 - t[..., None]) + b * t[..., None] if t.ndim else a * (1 - t) + b * t


def alagar(camadas, nivel, horizonte, luzes=(), semente=0, altura=None, vezes=1):
    """A camada "chao" (camadas[3]) alagada no nível 1, 2 ou 3. luzes: [(x, y, raio, cor)] em pixels da camada."""
    fundo = compor(camadas[:3])
    cor, alfa = para_array(camadas[3])
    alt, larg = alfa.shape
    yy, xx = np.mgrid[0:alt, 0:larg].astype(np.float32)
    b = bayer(alt, larg)
    piso = alfa > 0.5
    terreno = np.zeros((alt, larg), np.float32) if altura is None else np.asarray(altura, np.float32)
    z = np.clip((yy - horizonte) / max(1, alt - horizonte), 0, 1)           # 0 = lá no fundo, 1 = perto

    # onde a água chega: manchas no plano do chão (achatadas no fundo), juntas e buracos primeiro, terreno alto depois
    prof = (alt - horizonte) * np.log((0.16 + z) / 0.16) / 3.0
    u = (xx - larg / 2) / (0.25 + 0.75 * z)
    manchas = 0.7 * ruido_suave(u, prof * 2.2, 44 * vezes, semente) + 0.3 * ruido_suave(u, prof * 2.2, 16 * vezes,
                                                                                           semente + 7)
    lum = cor.mean(-1)
    juntas = piso & (lum < np.percentile(lum[piso], 28)) if piso.any() else np.zeros_like(piso)
    fundura = manchas + juntas * 0.08 - terreno * 1.6
    agua = piso & (fundura > LIMITE[nivel])
    if nivel < 3:                                                          # poças lisas, sem fiapo nem pixel solto
        forma = np.ones((1 + vezes, 3 + 2 * vezes), bool)
        agua = ndimage.binary_opening(ndimage.binary_closing(agua, forma), forma) & piso
        rotulos, n = ndimage.label(agua)
        if n:
            tamanhos = ndimage.sum(agua, rotulos, range(1, n + 1))
            agua &= np.isin(rotulos, np.nonzero(tamanhos >= 14 * vezes * vezes)[0] + 1)
    sobe = SOBE[nivel] * vezes
    parede = (yy >= horizonte - sobe) & (yy < horizonte) & ~piso & (fundo.sum(-1) > 0)

    # a cor da água: o chão visto através dela + a cor do esgoto + o reflexo do fundo
    base = AGUA_LONGE * (1 - z[..., None]) + AGUA_PERTO * z[..., None]
    agua_cor = misturar(cor * 0.6, base, np.float32(OPACIDADE[nivel]))
    ondula = np.round(np.sin(yy * 1.7 / vezes + xx * 0.05) * 0.6 * vezes)
    yr = np.clip(2 * horizonte - yy - 1, 0, alt - 1).astype(int)
    xr = np.clip(xx + ondula, 0, larg - 1).astype(int)
    reflexo = fundo[yr, xr] * REFLEXO
    forca = degraus(FORCA_DO_REFLEXO[nivel] * (1 - 0.5 * z), 4, b)
    agua_cor = misturar(agua_cor, reflexo, forca)

    # as luzes das velas viram faixas tremidas na água
    for lx, ly, raio, lcor in luzes:
        meio_y = 2 * horizonte - ly
        dist = np.abs(yy - meio_y) / max(1.0, raio * 1.3)
        tremido = np.round(np.sin(yy * 1.3 / vezes + lx) * 1.5 * vezes)
        largura = (1.5 + 2.5 * z) * vezes
        faixa = (np.abs(xx - lx - tremido) <= largura) & (dist < 1) & (yy > horizonte)
        intensidade = degraus((1 - dist) * 0.75, 3, b) * faixa
        agua_cor += np.array(lcor, np.float32)[None, None, :] * intensidade[..., None] * 0.55

    # ondinhas claras (mais perto = mais ondas) e a borda de cima das poças acesa
    ondas = (hash2((xx + (yy % 3) * 3) // (5 * vezes), yy // vezes, semente + 3) > 0.955 - 0.05 * z)
    agua_cor = np.where(ondas[..., None], misturar(agua_cor, ONDA, np.float32(0.55)), agua_cor)
    de_cima = np.zeros_like(agua)
    de_cima[1:] = agua[:-1]
    borda = agua & ~de_cima & (z > 0.06)
    agua_cor = np.where(borda[..., None], misturar(agua_cor, BORDA, np.float32(0.4)), agua_cor)

    # o chão que ficou de fora está molhado (mais escuro perto da água; no nível 2, todo)
    molhado = piso & ~agua & ndimage.binary_dilation(agua, iterations=2 * vezes)
    seco = cor.copy()
    seco[molhado] *= np.array((0.7, 0.76, 0.72), np.float32)
    if nivel >= 2:
        seco[piso & ~agua] *= np.array((0.82, 0.86, 0.82), np.float32)

    saida = np.where(agua[..., None], agua_cor, seco)
    saida_alfa = alfa.copy()
    if parede.any():                                                       # a água subindo pela base do fundo
        saida[parede] = misturar(fundo[parede] * REFLEXO, AGUA_LONGE * 0.8, np.float32(0.62))
        topo = parede & ~np.roll(parede, 1, axis=0)
        saida[topo] = misturar(saida[topo], BORDA, np.float32(0.6))
        saida_alfa[parede] = 1.0
    if nivel == 3:
        lixo_boiando(saida, agua, z, semente, vezes)
    return para_superficie(saida, saida_alfa)


def lixo_boiando(cor, agua, z, semente, vezes):
    """Na água alta: espuma, ossos, palha e um rato morto boiando."""
    rng = np.random.default_rng(semente + 11)
    alt, larg = agua.shape
    for k in range(18 * vezes):
        y, x = int(rng.integers(0, alt)), int(rng.integers(0, larg))
        if not agua[y, x] or z[y, x] < 0.08:
            continue
        tam = max(1, int((1 + 3 * z[y, x]) * vezes))
        tipo = k % 4
        if tipo == 0:                                                      # espuma
            for dx in range(-tam, tam + 1):
                if 0 <= x + dx < larg and (dx + y) % 2 == 0:
                    cor[y, x + dx] = (120, 150, 112)
        elif tipo == 1:                                                    # osso
            cor[y, max(0, x - tam):min(larg, x + tam + 1)] = (196, 186, 160)
            cor[min(alt - 1, y + 1), max(0, x - tam):min(larg, x + tam + 1)] = (90, 84, 70)
        elif tipo == 2:                                                    # palha
            for dx in range(-tam - 1, tam + 2):
                if 0 <= x + dx < larg:
                    cor[max(0, y - (dx > 0)), x + dx] = (150, 126, 70)
        else:                                                              # rato morto de barriga para cima
            cor[y, max(0, x - tam):min(larg, x + tam + 1)] = (70, 60, 58)
            cor[max(0, y - 1), max(0, x - tam + 1):min(larg, x + tam)] = (110, 96, 92)
            if x + tam + 1 < larg:
                cor[y, x + tam + 1:min(larg, x + tam + 1 + 2 * tam)] = (150, 100, 100)


def chao_alagado(camadas, configuracao, horizonte, luzes, semente, altura=None, vezes=1):
    """Grava os 3 chãos alagados nas camadas extras da cena e a lista em configuracao["chao_alagado"]."""
    extras = configuracao.setdefault("_camadas", {})
    luzes = [(x, y, raio, cor) for x, y, raio, cor, *_ in luzes]
    for nivel in (1, 2, 3):
        extras[f"chao_agua{nivel}"] = alagar(camadas, nivel, horizonte, luzes, semente, altura, vezes)
    configuracao["chao_alagado"] = [f"chao_agua{nivel}" for nivel in (1, 2, 3)]
