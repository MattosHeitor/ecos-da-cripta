"""O salão da Cripta (fundo da tela de título), em camadas, na mesma densidade de pixels dos personagens (2x).

    python gerar_salao.py

Uma nave gótica vista da entrada, em perspectiva (ponto de fuga no meio, um pouco acima do altar):
    fundo.png    parede do fundo com o grande vitral aceso pela lua, o altar nos degraus, as naves laterais,
                 o piso de lajes em perspectiva e o tapete vermelho com debrum dourado
    colunas.png  as fileiras de colunas (das mais longe às mais perto), os arcos da abóbada, estandartes,
                 candelabros presos nas colunas e as estátuas de cavaleiros nos pedestais
    frente.png   as colunas mais perto (cortadas pela borda), teias nos cantos e os candelabros de chão
    salao.json   tamanho, paralaxe, as velas (para a luz e as chamas) e o vitral (para os feixes de luz)

Reaproveita as ferramentas de desenho de gerar_acampamento.py (camadas numpy, pontilhado de Bayer).
"""
import json
import math
import os

import numpy as np
from PIL import Image

from gerar_acampamento import (Camada, molde, poligono, elipse, ruido_2d, misturar, LIMIAR, YY, XX, W, H, MARGEM,
                               AQUI)

PASTA = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "assets", "salao_da_cripta")
FUGA = (MARGEM + 320, 118)                 # ponto de fuga
ALTURA_DA_CAMERA = 210
FUNDO_D = 3.3                               # profundidade da parede do fundo
LARGURA_DA_NAVE = 250
PE_DIREITO = 360
VELAS = []                                  # (x, y, força, camada) em pixels da camada
CAMADA = ["fundo"]                          # em que camada as velas desenhadas agora estão


def piso_y(d):
    return FUGA[1] + ALTURA_DA_CAMERA / d


def x_em(lado, d, largura=LARGURA_DA_NAVE):
    return FUGA[0] + lado * largura / d


def vela(c, x, y, forca=1.0):
    """Velinha de cera com o pavio aceso (a chama de verdade é desenhada pelo jogo, tremendo)."""
    c.pintar(poligono([(x - 1, y), (x + 1, y), (x + 1, y - 5), (x - 1, y - 5)]), (226, 214, 186))
    c.cor[int(y - 5), int(x)] = (160, 150, 130)
    c.pintar(poligono([(x - 1, y - 4), (x, y - 4), (x, y - 1), (x - 1, y - 1)]), (236, 228, 204))
    VELAS.append((float(x), float(y - 7), forca, CAMADA[0]))


# ============================================================
# FUNDO: parede, vitral, altar, naves laterais, piso e tapete
# ============================================================

def fundo(rng):
    c = Camada()
    tudo = np.ones((H, W), bool)
    c.degrade(tudo, [(8, 6, 14), (12, 10, 20), (16, 13, 26), (20, 16, 30)], np.clip(YY / 220, 0, 1))
    y_fundo = piso_y(FUNDO_D)
    x_e, x_d = x_em(-1, FUNDO_D), x_em(1, FUNDO_D)
    # naves laterais escuras (paredes que fogem para o fundo) com janelinhas estreitas
    for lado in (-1, 1):
        borda_perto = 0 if lado < 0 else W
        parede = poligono([(borda_perto, -10), (x_e if lado < 0 else x_d, y_fundo - PE_DIREITO / FUNDO_D),
                           (x_e if lado < 0 else x_d, y_fundo), (borda_perto, H)])
        c.degrade(parede, [(14, 11, 22), (19, 15, 28), (24, 19, 33)], np.clip(np.abs(XX - FUGA[0]) / 330, 0, 1))
        for d in (1.7, 2.35, 3.0):
            xj = x_em(lado, d, LARGURA_DA_NAVE * 1.45)
            yj = piso_y(d) - 190 / d
            larg, alt = 9 / d * 1.6, 70 / d
            janela = poligono([(xj - larg, yj), (xj + larg, yj), (xj + larg, yj - alt), (xj, yj - alt - larg * 1.4),
                               (xj - larg, yj - alt)])
            c.degrade(janela, [(70, 80, 140), (50, 56, 110), (36, 38, 80)], np.clip((YY - yj + alt) / alt, 0, 1))
            c.pintar(janela & (np.abs(XX - xj) < 0.6), (16, 12, 22))
    # parede do fundo em blocos de pedra
    parede = poligono([(x_e, y_fundo), (x_d, y_fundo), (x_d, -10), (x_e, -10)])
    c.degrade(parede, [(30, 26, 42), (26, 22, 38), (22, 18, 32)], np.clip(YY / 200, 0, 1))
    for y in range(0, int(y_fundo), 7):
        c.pintar(parede & (np.abs(YY - y) < 0.5), (18, 15, 27))
        desloc = 6 if (y // 7) % 2 else 0
        for x in range(int(x_e) + desloc, int(x_d), 13):
            c.pintar(parede & (np.abs(XX - x) < 0.5) & (YY > y) & (YY < y + 7), (18, 15, 27))
    # o grande vitral: arco ogival com três lancetas e uma rosácea no alto
    vx, vtopo, vbase, vlarg = FUGA[0], 14, y_fundo - 30, 44
    arco_y = vtopo + vlarg * 1.1
    janela = poligono([(vx - vlarg, vbase), (vx + vlarg, vbase), (vx + vlarg, arco_y)] +
                      [(vx + vlarg * math.cos(a), arco_y - vlarg * 1.15 * math.sin(a)) for a in np.linspace(0, math.pi, 24)] +
                      [(vx - vlarg, arco_y)])
    moldura = poligono([(vx - vlarg - 5, vbase + 4), (vx + vlarg + 5, vbase + 4), (vx + vlarg + 5, arco_y)] +
                       [(vx + (vlarg + 5) * math.cos(a), arco_y - (vlarg + 5) * 1.15 * math.sin(a)) for a in np.linspace(0, math.pi, 24)] +
                       [(vx - vlarg - 5, arco_y)])
    c.pintar(moldura, (46, 40, 60))
    c.pintar(moldura & ~janela & (XX > vx), (70, 64, 88))
    # vidros: muitas pecinhas (diagrama de Voronoi), cada uma com a cor do desenho naquele ponto:
    # fundo azul-noite, borda dourada em cada lanceta e, no meio, uma figura de manto vermelho com auréola
    pontos = np.array([(rng.uniform(vx - vlarg, vx + vlarg), rng.uniform(vtopo, vbase)) for _ in range(260)])
    ys, xs = np.nonzero(janela)
    dist = (xs[:, None] - pontos[None, :, 0]) ** 2 + ((ys[:, None] - pontos[None, :, 1]) * 0.8) ** 2
    ordem = np.argsort(dist, axis=1)[:, :2]
    d0 = dist[np.arange(len(xs)), ordem[:, 0]]
    d1 = dist[np.arange(len(xs)), ordem[:, 1]]
    figura_y0, figura_y1 = arco_y + 6, vbase - 10

    def cor_do_desenho(x, y, k):
        dx = x - vx
        lanceta = min(abs(dx - c_) for c_ in (-vlarg * 2 / 3, 0, vlarg * 2 / 3))
        if lanceta > vlarg / 3 - 4 and y > arco_y - 2:                      # borda de cada lanceta
            return [(214, 172, 70), (190, 140, 50), (60, 140, 110)][k % 3]
        if abs(dx) < vlarg / 3 - 2 and figura_y0 < y < figura_y1:           # a figura do meio
            t = (y - figura_y0) / (figura_y1 - figura_y0)
            if t < 0.16:
                return (250, 214, 120) if math.hypot(dx, (y - figura_y0 - 6) * 0.9) > 4 else (230, 190, 160)   # auréola e rosto
            meia = 4 + t * 10
            if abs(dx) < meia:
                return [(176, 36, 50), (150, 28, 44), (200, 60, 66)][k % 3]
        if abs(dx) > vlarg / 3 and figura_y0 < y < figura_y1 and (k % 5 == 0):
            return (230, 200, 90)                                             # estrelinhas nas lancetas dos lados
        return [(36, 60, 160), (48, 80, 190), (30, 46, 130), (70, 50, 150)][k % 4]

    claridade = np.clip(1.25 - (ys - vtopo) / (vbase - vtopo) * 0.5, 0.65, 1.25)
    cores_das_pecas = {}
    for k in range(len(xs)):
        peca = ordem[k, 0]
        if peca not in cores_das_pecas:
            cores_das_pecas[peca] = cor_do_desenho(pontos[peca, 0], pontos[peca, 1], int(peca))
        if d1[k] - d0[k] < 9:
            c.cor[ys[k], xs[k]] = (20, 14, 26)                                # chumbo
        else:
            c.cor[ys[k], xs[k]] = tuple(min(255, v * claridade[k]) for v in cores_das_pecas[peca])
        c.alfa[ys[k], xs[k]] = 255
    for dx in (-vlarg / 3, vlarg / 3):                                # mainéis de pedra entre as lancetas
        c.pintar(janela & (np.abs(XX - vx - dx) < 1.2) & (YY > arco_y - 4), (40, 34, 54))
    rosa_c, rosa_r = (vx, arco_y - vlarg * 0.35), vlarg * 0.55
    rosa = elipse(rosa_c[0], rosa_c[1], rosa_r, rosa_r)
    c.pintar(rosa & ~elipse(rosa_c[0], rosa_c[1], rosa_r - 2, rosa_r - 2), (40, 34, 54))
    for k in range(8):
        a = k * math.pi / 4
        c.pintar(molde(lambda d, a=a: d.line([rosa_c, (rosa_c[0] + math.cos(a) * rosa_r, rosa_c[1] + math.sin(a) * rosa_r)],
                                            fill=255, width=1)) & rosa, (40, 34, 54))
    for k in range(8):                                               # pétalas em vermelho e dourado
        a = k * math.pi / 4 + math.pi / 8
        petala = elipse(rosa_c[0] + math.cos(a) * rosa_r * 0.55, rosa_c[1] + math.sin(a) * rosa_r * 0.55, rosa_r * 0.28, rosa_r * 0.28)
        c.pintar(petala & rosa, (190, 50, 60) if k % 2 else (220, 176, 80))
    c.pintar(elipse(rosa_c[0], rosa_c[1], 4, 4), (250, 220, 120))
    c.pintar(janela & (YY > arco_y - 2) & (np.abs(YY - (vbase - (vbase - arco_y) * 0.45)) < 1), (40, 34, 54))
    # degraus e altar (pano vermelho, castiçais) embaixo do vitral
    for k, (larg, alt) in enumerate(((90, 4), (76, 4), (62, 4))):
        y = y_fundo - k * alt
        degrau = poligono([(vx - larg, y + 2), (vx + larg, y + 2), (vx + larg - 3, y - alt + 2), (vx - larg + 3, y - alt + 2)])
        c.pintar(degrau, (54, 48, 66))
        c.pintar(degrau & (YY < y - alt + 3.5), (84, 76, 98))
    topo_altar = y_fundo - 12 - 16
    altar = poligono([(vx - 30, y_fundo - 12), (vx + 30, y_fundo - 12), (vx + 30, topo_altar), (vx - 30, topo_altar)])
    c.pintar(altar, (62, 56, 74))
    c.pintar(altar & (YY < topo_altar + 2), (96, 88, 110))
    pano = poligono([(vx - 20, topo_altar), (vx + 20, topo_altar), (vx + 18, y_fundo - 13), (vx - 18, y_fundo - 13)])
    c.pintar(pano, (120, 24, 36))
    c.pintar(pano & (np.abs(XX - vx) < 2), (210, 170, 70))
    c.pintar(pano & (YY > y_fundo - 16), (210, 170, 70))
    for dx in (-24, -12, 12, 24):
        c.pintar(poligono([(vx + dx - 1.5, topo_altar), (vx + dx + 1.5, topo_altar), (vx + dx + 0.6, topo_altar - 4),
                           (vx + dx - 0.6, topo_altar - 4)]), (190, 150, 70))
        vela(c, vx + dx, topo_altar - 4, 0.7)
    # piso de lajes em perspectiva
    piso = YY > y_fundo
    c.degrade(piso, [(16, 14, 22), (20, 17, 27), (24, 21, 31), (27, 23, 34)], np.clip((YY - y_fundo) / (H - y_fundo), 0, 1))
    for d in np.linspace(1.0, FUNDO_D, 14):
        y = piso_y(d)
        c.pintar(piso & (np.abs(YY - y) < 0.5), (11, 9, 15))
    for k in range(-14, 15):
        x_fundo, x_perto = FUGA[0] + k * 13, FUGA[0] + k * 13 * (FUNDO_D / 0.85)
        linha = molde(lambda d, a=(x_fundo, y_fundo), b=(x_perto, H + 30): d.line([a, b], fill=255, width=1))
        c.pintar(piso & linha, (11, 9, 15))
    c.pontilhar(piso & (ruido_2d(rng, 3) > 0.74), (13, 11, 18), 0.4)
    c.pontilhar(piso & (ruido_2d(rng, 11) < 0.2), (32, 28, 40), 0.25)
    # tapete vermelho com debrum dourado e losangos, do pé da tela até os degraus
    def tapete_x(y, largura):
        d = ALTURA_DA_CAMERA / max(1.0, y - FUGA[1])
        return largura / d
    tapete = np.zeros((H, W), bool)
    for y in range(int(y_fundo) + 1, H):
        meia = tapete_x(y, 66)
        tapete[y, int(FUGA[0] - meia):int(FUGA[0] + meia) + 1] = True
    c.degrade(tapete, [(70, 12, 20), (96, 18, 28), (120, 24, 34), (134, 28, 38)], np.clip((YY - y_fundo) / (H - y_fundo), 0, 1))
    c.pontilhar(tapete & (ruido_2d(rng, 2, 4) > 0.7), (84, 14, 24), 0.4)
    for y in range(int(y_fundo) + 1, H):
        for fracao in (0.86, 0.94):
            for lado in (-1, 1):
                x = int(round(FUGA[0] + lado * tapete_x(y, 66) * fracao))
                c.cor[y, x] = (196, 152, 66)
    for d in (1.15, 1.45, 1.9, 2.6):
        y = piso_y(d)
        meia = tapete_x(y, 66) * 0.32
        c.pintar(poligono([(FUGA[0], y - meia * 0.35), (FUGA[0] + meia, y), (FUGA[0], y + meia * 0.35), (FUGA[0] - meia, y)]),
                 (200, 156, 70))
        c.pintar(poligono([(FUGA[0], y - meia * 0.15), (FUGA[0] + meia * 0.45, y), (FUGA[0], y + meia * 0.15), (FUGA[0] - meia * 0.45, y)]),
                 (110, 20, 30))
    return c, {"vitral": [float(vx), float(vtopo), float(vbase), float(vlarg)], "fundo_y": float(y_fundo)}


# ============================================================
# COLUNAS, ARCOS, ESTANDARTES, CANDELABROS E ESTÁTUAS
# ============================================================

def coluna(c, x, base, d, luz_do_lado=1):
    """Coluna gótica: base em degraus, fuste com caneluras, capitel; a face virada para o meio recebe a luz do vitral."""
    larg = 34 / d
    topo = base - PE_DIREITO / d
    fuste = poligono([(x - larg / 2, base - 8 / d), (x + larg / 2, base - 8 / d), (x + larg / 2, topo + 18 / d), (x - larg / 2, topo + 18 / d)])
    t = np.clip((XX - (x - larg / 2)) / larg, 0, 1)
    if luz_do_lado < 0:
        t = 1 - t
    c.degrade(fuste, [(22, 19, 32), (32, 28, 44), (44, 38, 58), (62, 56, 78)], t)
    for k in range(1, 5):                                            # caneluras
        xx = x - larg / 2 + k * larg / 5
        c.pintar(fuste & (np.abs(XX - xx) < 0.45), (18, 15, 27))
    sapata = poligono([(x - larg * 0.7, base), (x + larg * 0.7, base), (x + larg * 0.62, base - 9 / d), (x - larg * 0.62, base - 9 / d)])
    c.degrade(sapata, [(28, 24, 38), (40, 35, 52), (56, 50, 72)], np.clip(t, 0, 1))
    c.pintar(sapata & (YY < base - 8 / d), (74, 68, 92))
    capitel = poligono([(x - larg * 0.5, topo + 18 / d), (x + larg * 0.5, topo + 18 / d), (x + larg * 0.75, topo + 8 / d),
                        (x - larg * 0.75, topo + 8 / d)])
    c.pintar(capitel, (40, 35, 52))
    c.pintar(capitel & (YY < topo + 10 / d), (70, 64, 90))
    return topo + 8 / d


def arco(c, x0, x1, y, espessura, alt):
    """Arco ogival de pedra entre dois capitéis, com a nervura de baixo iluminada."""
    meio = (x0 + x1) / 2
    pts_fora, pts_dentro = [], []
    for k in range(25):
        t = k / 24
        x = x0 + (x1 - x0) * t
        h = alt * (1 - abs(2 * t - 1) ** 1.4)
        pts_fora.append((x, y - h - espessura))
        pts_dentro.append((x, y - h))
    acima = poligono(pts_fora + [(x1, -10), (x0, -10)])                # a parede que o arco segura (fecha a abóbada)
    c.degrade(acima, [(12, 10, 20), (18, 15, 27), (24, 20, 34)], np.clip((YY - (y - alt - 40)) / 60, 0, 1))
    forma = poligono(pts_fora + list(reversed(pts_dentro)))
    c.pintar(forma, (30, 26, 42))
    c.pintar(forma & np.roll(~forma, -1, 0), (70, 64, 92))
    return meio


def estandarte(c, x, topo, d, rng, cor=(124, 22, 34)):
    larg, comp = 22 / d, 130 / d
    c.pintar(poligono([(x - larg / 2 - 2, topo), (x + larg / 2 + 2, topo), (x + larg / 2 + 2, topo + 2), (x - larg / 2 - 2, topo + 2)]), (110, 84, 46))
    pano = poligono([(x - larg / 2, topo + 2), (x + larg / 2, topo + 2), (x + larg / 2, topo + comp), (x, topo + comp - larg * 0.5),
                     (x - larg / 2, topo + comp)])
    c.degrade(pano, [misturar(cor, (0, 0, 0), 0.5), cor, misturar(cor, (255, 200, 160), 0.15)],
              np.clip((XX - x + larg / 2) / larg, 0, 1))
    c.pintar(pano & (np.abs(XX - (x - larg / 2 + 1.5)) < 0.6), (196, 152, 66))
    c.pintar(pano & (np.abs(XX - (x + larg / 2 - 1.5)) < 0.6), (196, 152, 66))
    cy = topo + comp * 0.38                                            # emblema: cálice com chama
    s = larg / 22
    c.pintar(poligono([(x - 6 * s, cy - 4 * s), (x + 6 * s, cy - 4 * s), (x + 3 * s, cy + 3 * s), (x - 3 * s, cy + 3 * s)]), (214, 170, 80))
    c.pintar(poligono([(x - 1 * s, cy + 3 * s), (x + 1 * s, cy + 3 * s), (x + 1 * s, cy + 8 * s), (x - 1 * s, cy + 8 * s)]), (214, 170, 80))
    c.pintar(poligono([(x - 4 * s, cy + 8 * s), (x + 4 * s, cy + 8 * s), (x + 4 * s, cy + 9.5 * s), (x - 4 * s, cy + 9.5 * s)]), (214, 170, 80))
    c.pintar(poligono([(x, cy - 12 * s), (x + 3 * s, cy - 5 * s), (x - 3 * s, cy - 5 * s)]), (240, 120, 60))


def candelabro_de_parede(c, x, y, d, lado):
    """Braço de ferro saindo da coluna com três velas."""
    s = 1 / d
    braco_x = x + lado * 16 * s
    c.pintar(molde(lambda dd: dd.line([(x, y), (braco_x, y - 2 * s), (braco_x, y - 8 * s)], fill=255, width=max(1, int(2 * s)))),
             (60, 54, 66))
    prato = poligono([(braco_x - 9 * s, y - 8 * s), (braco_x + 9 * s, y - 8 * s), (braco_x + 6 * s, y - 6 * s), (braco_x - 6 * s, y - 6 * s)])
    c.pintar(prato, (90, 80, 70))
    for dx in (-6, 0, 6):
        vela(c, braco_x + dx * s, y - 8 * s, 0.8 if d < 1.8 else 0.55)


ESTATUAS = []                               # (x, topo do pedestal) para o jogo pôr o cavaleiro de pedra


def pedestal(c, x, base, d):
    """Pedestal de pedra em degraus, com friso; guarda onde o cavaleiro de pedra fica."""
    s = 1 / d
    ped = poligono([(x - 26 * s, base), (x + 26 * s, base), (x + 22 * s, base - 30 * s), (x - 22 * s, base - 30 * s)])
    c.pintar(ped, (44, 39, 56))
    c.pintar(ped & (YY < base - 27 * s), (80, 74, 98))
    c.pintar(ped & (np.abs(YY - (base - 15 * s)) < 0.6), (30, 26, 40))
    c.pintar(poligono([(x - 28 * s, base), (x + 28 * s, base), (x + 27 * s, base - 4 * s), (x - 27 * s, base - 4 * s)]), (56, 50, 70))
    ESTATUAS.append((float(x), float(base - 30 * s)))


def estatua(c, x, base, d, lado):
    """Cavaleiro de pedra num pedestal, com as mãos no punho da espada fincada (o lado da luz mais claro)."""
    s = 1 / d
    ped = poligono([(x - 26 * s, base), (x + 26 * s, base), (x + 22 * s, base - 30 * s), (x - 22 * s, base - 30 * s)])
    c.pintar(ped, (44, 39, 56))
    c.pintar(ped & (YY < base - 27 * s), (80, 74, 98))
    c.pintar(ped & (np.abs(YY - (base - 15 * s)) < 0.6), (30, 26, 40))
    b = base - 30 * s
    pedra, clara, escura = (66, 62, 80), (104, 98, 122), (40, 36, 52)
    pecas = [
        [(x - 14 * s, b), (x + 14 * s, b), (x + 11 * s, b - 52 * s), (x - 11 * s, b - 52 * s)],                     # saia/tabardo
        [(x - 13 * s, b - 50 * s), (x + 13 * s, b - 50 * s), (x + 15 * s, b - 82 * s), (x - 15 * s, b - 82 * s)],    # peito
        [(x - 20 * s, b - 78 * s), (x - 8 * s, b - 86 * s), (x + 8 * s, b - 86 * s), (x + 20 * s, b - 78 * s),
         (x + 18 * s, b - 72 * s), (x - 18 * s, b - 72 * s)],                                                      # ombreiras
    ]
    corpo = np.zeros((H, W), bool)
    for pts in pecas:
        corpo |= poligono(pts)
    corpo |= elipse(x, b - 94 * s, 9 * s, 10 * s)                                                                 # elmo
    corpo |= poligono([(x - 18 * s, b - 76 * s), (x - 22 * s, b - 4 * s), (x - 12 * s, b), (x - 12 * s, b - 60 * s)])   # capa
    c.pintar(corpo, pedra)
    lado_claro = corpo & ((XX - x) * lado < 0)
    c.pintar(lado_claro, misturar(pedra, clara, 0.5))
    c.pintar(corpo & ~np.roll(corpo, -lado if lado else 1, 1) & lado_claro, clara)
    c.pintar(elipse(x, b - 93 * s, 7 * s, 1.2 * s), escura)                                                        # viseira
    espada = poligono([(x - 2 * s, b + 0 * s), (x + 2 * s, b), (x + 2 * s, b - 46 * s), (x - 2 * s, b - 46 * s)])
    c.pintar(espada, (86, 82, 104))
    c.pintar(poligono([(x - 10 * s, b - 46 * s), (x + 10 * s, b - 46 * s), (x + 10 * s, b - 50 * s), (x - 10 * s, b - 50 * s)]), clara)
    c.pintar(elipse(x, b - 56 * s, 7 * s, 5 * s), clara)                                                           # mãos no punho
    c.pintar(corpo & (np.abs(YY - (b - 52 * s)) < 0.6), escura)


def colunas(rng):
    c = Camada()
    profundidades = (2.75, 2.05, 1.5)
    topos = {}
    for d in profundidades:                                           # das de trás para as da frente
        base = piso_y(d)
        for lado in (-1, 1):
            x = x_em(lado, d)
            topos[(d, lado)] = (x, coluna(c, x, base, d, luz_do_lado=-lado))
        # arco atravessando a nave entre o par de colunas
        (x0, y0), (x1, _) = topos[(d, -1)], topos[(d, 1)]
        arco(c, x0, x1, y0, 9 / d, 120 / d)
    for d in (2.05, 1.5):                                            # estandartes e candelabros nas faces de dentro
        for lado in (-1, 1):
            x = x_em(lado, d) - lado * 34 / d * 0.62
            estandarte(c, x, piso_y(d) - 290 / d, d, rng, cor=(124, 22, 34) if d < 1.8 else (40, 46, 96))
            candelabro_de_parede(c, x_em(lado, d) - lado * 17 / d, piso_y(d) - 150 / d, d, -lado)
    for lado in (-1, 1):                                              # pedestais das estátuas (a figura vem do jogo)
        pedestal(c, x_em(lado, 1.75, LARGURA_DA_NAVE * 0.95), piso_y(1.75), 1.75)
    # escuridão da abóbada lá em cima
    c.pontilhar((YY < 40) & (c.alfa > 0), (14, 11, 22), np.clip(1 - YY / 40, 0, 1) * 0.6)
    return c


# ============================================================
# FRENTE: colunas cortadas, teias e candelabros de chão
# ============================================================

def frente(rng):
    c = Camada()
    d = 1.02
    base = piso_y(d)
    for lado in (-1, 1):
        x = x_em(lado, d, LARGURA_DA_NAVE * 1.18)
        coluna(c, x, base + 40, d * 0.95, luz_do_lado=-lado)
    # candelabros de chão (sete velas) dos dois lados do tapete
    for lado in (-1, 1):
        x, base_c = FUGA[0] + lado * 150, H - 26
        c.pintar(poligono([(x - 9, base_c), (x + 9, base_c), (x + 4, base_c - 4), (x - 4, base_c - 4)]), (70, 62, 54))
        c.pintar(poligono([(x - 1.5, base_c - 4), (x + 1.5, base_c - 4), (x + 1.5, base_c - 66), (x - 1.5, base_c - 66)]), (84, 74, 60))
        for k in (-3, -2, -1, 1, 2, 3):
            xb = x + k * 6
            c.pintar(molde(lambda dd, xb=xb: dd.line([(x, base_c - 50), (xb, base_c - 56 - abs(k) * 2), (xb, base_c - 66)],
                                                    fill=255, width=1)), (110, 96, 70))
        for k in (-3, -2, -1, 0, 1, 2, 3):
            xb = x + k * 6
            c.pintar(poligono([(xb - 3, base_c - 66), (xb + 3, base_c - 66), (xb + 2, base_c - 68), (xb - 2, base_c - 68)]), (150, 126, 80))
            vela(c, xb, base_c - 68, 1.0)
    # teias nos cantos de cima
    for canto_x, sentido in ((0, 1), (W, -1)):
        teia = np.zeros((H, W), bool)
        for k in range(7):
            a = k * (math.pi / 2) / 6
            fim = (canto_x + sentido * math.cos(a) * 70, math.sin(a) * 70)
            teia |= molde(lambda dd, fim=fim: dd.line([(canto_x, 0), fim], fill=255, width=1))
        for r in (16, 30, 44, 58):
            pts = [(canto_x + sentido * math.cos(k * (math.pi / 2) / 6) * r * (0.92 + 0.08 * (k % 2)),
                    math.sin(k * (math.pi / 2) / 6) * r * (0.92 + 0.08 * (k % 2))) for k in range(7)]
            teia |= molde(lambda dd, pts=pts: dd.line(pts, fill=255, width=1))
        c.pontilhar(teia, (120, 116, 140), 0.85)
    return c


def main():
    os.makedirs(PASTA, exist_ok=True)
    VELAS.clear()
    ESTATUAS.clear()
    rng = np.random.default_rng(1347)
    CAMADA[0] = "fundo"
    camada_fundo, info = fundo(rng)
    salvar(camada_fundo, "fundo")
    CAMADA[0] = "colunas"
    salvar(colunas(rng), "colunas")
    CAMADA[0] = "frente"
    salvar(frente(rng), "frente")
    info.update({"tamanho": [W, H], "margem": MARGEM, "escala": 2, "fuga": list(FUGA),
                 "velas": [[round(x, 1), round(y, 1), f, camada] for x, y, f, camada in VELAS],
                 "estatuas": [[round(x, 1), round(y, 1)] for x, y in ESTATUAS],
                 "paralaxe": {"fundo": 0.2, "colunas": 0.5, "frente": 1.0}})
    with open(os.path.join(PASTA, "salao.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    previa = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    for nome in ("fundo", "colunas", "frente"):
        previa.alpha_composite(Image.open(os.path.join(PASTA, nome + ".png")))
    os.makedirs(os.path.join(AQUI, "previas"), exist_ok=True)
    previa.crop((MARGEM, 0, W - MARGEM, H)).resize((1280, 720), Image.NEAREST).save(os.path.join(AQUI, "previas", "previa_salao.png"))
    print(f"salão da cripta em {PASTA} ({len(VELAS)} velas)")
    import gerar_luzes_do_salao                        # os feixes do vitral e a névoa, prontos em PNG
    gerar_luzes_do_salao.main()


def salvar(camada, nome):
    rgba = np.dstack([np.clip(camada.cor, 0, 255), camada.alfa]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(os.path.join(PASTA, nome + ".png"))


if __name__ == "__main__":
    main()
