"""O Salão do Trono do Reino dos Ratos (sala dos chefes), refeito com mais detalhe (etapa 5R1).

Resolução dobrada: 704x360 (cada pixel vira 2x2 na tela, como os chefes; as outras cenas são 352x180 em 4x4),
pintado com o motor das forjas (máscaras com sombreamento volumétrico, rampas de cor, contorno) e iluminado em
degraus pontilhados pelas velas, pela rosácea e pelo brilho verde do esgoto.

    ceu    abóbada de tijolos úmidos com nervuras, o grande arco ogival e a rosácea quebrada com o rato coroado
    longe  colunas góticas, cortinas de veludo roídas, estandartes do rato coroado, canos, correntes
    meio   candelabros altos de ouro, montes de tesouro (moedas, cálices, baú, queijo), ossada, a boca do cano
    chao   lajes molhadas em perspectiva, o estrado do trono (2 degraus) e o tapete vermelho roído
    frente moedas, crânio e vela à esquerda; tambor de coluna caído, rato morto e coroa à direita
    no_da_rainha  (camada extra, depois de "longe") a coroa presa num nó de caudas pendurada no teto, com os ratos

O trono de ratos e ouro NÃO está no cenário: é um sprite animado (forja: TronoDosRatos) que a tela desenha em
"trono" -> "base" (cenarios.json, na escala antiga de 352x180, como as luzes); o Rei senta em "pes".
Água: agua_no_chao.py faz o chão de cada nível, com o estrado alto (só a água alta cobre).

    python ferramentas/cenarios_macabros.py salao_do_trono_roedor
"""
import math
import os
import random
import sys

import numpy as np
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "sprites_macabros"))
from forja.motor import Tela, Mat, metal, v2, lerp  # noqa: E402
from forja.texturas import hash2, ruido_suave  # noqa: E402
from forja import fx  # noqa: E402
from agua_no_chao import chao_alagado, para_superficie, bayer, degraus  # noqa: E402

V = 2                                   # pixels daqui por pixel da escala antiga (352x180)
LARG, ALT = 352 * V, 180 * V
HOR = 118 * V                           # onde o chão começa
CX = LARG // 2
BAYER = bayer(ALT, LARG)

# ---------------- materiais ----------------
PEDRA = Mat((96, 84, 80), 6, relevo=1.0, ruido=0.22, dither=0.45)
PEDRA_CLARA = Mat((120, 108, 98), 6, relevo=1.1, ruido=0.2, dither=0.45)
VELUDO = Mat((136, 24, 38), 7, relevo=1.15, ruido=0.1, dither=0.4)
VELUDO_ESCURO = Mat((92, 16, 28), 6, relevo=1.0, ruido=0.12)
OURO = metal((214, 168, 60), especular=(255, 240, 170))
OURO_VELHO = metal((168, 126, 50))
FERRO = metal((78, 76, 86))
FERRUGEM = Mat((112, 66, 40), 6, relevo=1.25, ruido=0.4, dither=0.5)
MADEIRA = Mat((92, 60, 38), 6, relevo=0.7, ruido=0.3)
OSSO = Mat((218, 204, 174), 5, relevo=1.2, ruido=0.1)
CERA = Mat((224, 212, 178), 5, relevo=0.8)
QUEIJO = Mat((232, 188, 78), 5, relevo=0.9)
CASCA = Mat((200, 132, 50), 5, relevo=1.0)
LODO = Mat((72, 124, 58), 5, relevo=0.7, ruido=0.2)
PELO = Mat((64, 56, 56), 6, relevo=1.2, ruido=0.35, dither=0.5)
RABO = Mat((168, 118, 116), 5, relevo=1.1)

TIJOLOS = ((60, 42, 40), (68, 48, 44), (52, 38, 36), (64, 50, 42), (58, 44, 44))
JUNTA = (20, 13, 15)
OLHO = (255, 44, 40)
FOGO_DE_VELA = [(120, 30, 10), (220, 90, 24), (255, 170, 60), (255, 228, 140), (255, 250, 220)]

LUZ_AMBIENTE = np.array((0.3, 0.26, 0.36), np.float32)
CANDELABROS = (246, 458)
VELAS_DOS_CANDELABROS = ((-14, 6), (0, 0), (14, 6))
BASE_DO_TRONO = HOR - 4                          # o trono fica no degrau de cima do estrado
VELAS_DO_TRONO = ((288, 134), (416, 134))        # TronoDosRatos.VELAS + a base do trono (CX - 126, BASE - 128)
BOCA_DO_CANO = (648, 180)
VELA_DA_FRENTE = (74, 318)


def luzes_da_cena():
    """Luzes que pintam o cenário: [(x, y, raio, cor, força)] em pixels daqui."""
    luzes = [(x, 128, 160, (255, 178, 96), 0.9) for x in CANDELABROS]
    luzes += [(x, y, 96, (255, 180, 96), 0.55) for x, y in VELAS_DO_TRONO]
    luzes.append((CX, 92, 200, (170, 196, 110), 0.42))                        # a rosácea acesa por trás
    luzes.append((*BOCA_DO_CANO, 120, (90, 190, 90), 0.55))                    # o lodo verde do cano
    luzes.append((*VELA_DA_FRENTE, 70, (255, 176, 96), 0.55))                  # a vela no crânio (frente)
    luzes.append((CX, 290, 260, (200, 150, 110), 0.22))                         # o chão da luta, à meia-luz
    return luzes


def luzes_do_jogo():
    """Luzes que tremulam no jogo (cenarios.json "luzes"): [(x, y, raio, cor, tremula)] em pixels daqui."""
    luzes = [(x + dx, 116 + dy, 24, (255, 190, 100), 0.9) for x in CANDELABROS for dx, dy in VELAS_DOS_CANDELABROS]
    luzes += [(x, y - 8, 30, (255, 180, 96), 0.8) for x, y in VELAS_DO_TRONO]
    luzes.append((CX, 92, 60, (190, 210, 120), 0.15))
    luzes.append((*BOCA_DO_CANO, 40, (90, 190, 90), 0.3))
    luzes.append((VELA_DA_FRENTE[0], VELA_DA_FRENTE[1] - 50, 28, (255, 176, 96), 1.0))
    return luzes


def nova_tela(semente, borda=(170, 120, 90), forca_borda=0.22):
    return Tela(LARG, ALT, semente=semente, borda_luz=borda, forca_borda=forca_borda, geo_rapida=True)


def iluminar(tela, luzes, ambiente=LUZ_AMBIENTE, ate=None):
    """Luz em degraus pontilhados: cada pixel pintado (que não emite luz) é multiplicado pela luz que chega nele."""
    yy, xx = np.mgrid[0:ALT, 0:LARG].astype(np.float32)
    luz = np.broadcast_to(ambiente, (ALT, LARG, 3)).copy()
    for x, y, raio, cor, forca in luzes:
        d = np.sqrt((xx - x) ** 2 + ((yy - y) * 1.15) ** 2) / raio
        f = np.clip(1 - d, 0, 1) ** 1.5 * forca
        luz += f[..., None] * (np.array(cor, np.float32) / 255)[None, None, :]
    luz = np.minimum(luz, 1.55)
    luz = degraus(luz / 1.6, 10, BAYER[..., None]) * 1.6
    alvo = (tela.alfa > 0) & ~tela.emite
    if ate is not None:
        alvo &= ate
    tela.cor[alvo] *= luz[alvo]


def finalizar(tela, contorno=True):
    imagem = tela.finalizar(contorno=contorno)
    rgba = np.asarray(imagem, np.float32)
    return para_superficie(rgba[..., :3], rgba[..., 3] / 255)


def pts(lista, dx=0, dy=0):
    return [v2(x + dx, y + dy) for x, y in lista]


# ============================================================
# TEXTURAS (numpy, direto nos pixels da tela)
# ============================================================

def tijolos(tela, x0, y0, x1, y1, semente, larg=16, alt=7, cores=TIJOLOS, quebrados=0.04):
    """Parede de tijolos: cada um com um tom e um grão, aresta de cima clara, junta escura e alguns arrancados."""
    ys, xs = np.mgrid[y0:y1, x0:x1]
    fileira = (ys - y0) // alt
    desl = (fileira % 2) * (larg // 2) + (hash2(fileira, 0, semente) * 4).astype(int)
    coluna = (xs - x0 + desl) // larg
    bx, by = (xs - x0 + desl) % larg, (ys - y0) % alt
    tom = np.array(cores, np.float32)[(hash2(coluna, fileira, semente) * len(cores)).astype(int)]
    variacao = 0.86 + 0.26 * hash2(coluna * 7 + 3, fileira * 5, semente + 1)
    grao = 1 + (hash2(xs, ys, semente + 2) - 0.5) * 0.18
    cor = tom * (variacao * grao)[..., None]
    cor[by == 0] *= 1.2
    cor[bx == 1] *= 1.08
    cor[by == alt - 2] *= 0.84
    cor[bx == larg - 1] *= 0.86
    junta = (by == alt - 1) | (bx == 0)
    cor[junta] = JUNTA
    buraco = hash2(coluna * 5 + 1, fileira * 11 + 2, semente + 3) < quebrados
    fundo_do_buraco = buraco & ~junta
    cor[fundo_do_buraco] = np.array((24, 16, 18), np.float32) * (1 + 0.6 * (by[fundo_do_buraco] >= alt - 3))[:, None]
    tela.cor[y0:y1, x0:x1] = cor
    tela.alfa[y0:y1, x0:x1] = 255


def sujeira(tela, x0, y0, x1, y1, semente, umido=60, musgo=26):
    """Escorridos de umidade (faixas escuras de cima para baixo), salitre, a parede encharcada perto do chão e
    musgo no rodapé."""
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    cor = tela.cor[y0:y1, x0:x1]
    escorre = ruido_suave(xs * 3.2, ys * 0.06, 9, semente)
    comprimento = ruido_suave(xs * 0.4, 0 * ys, 13, semente + 1)
    faixa = (escorre > 0.6) & ((ys - y0) / max(1, y1 - y0) < 0.3 + comprimento * 0.9)
    cor[faixa & (BAYER[y0:y1, x0:x1] < 0.7)] *= np.array((0.72, 0.76, 0.74), np.float32)
    salitre = (ruido_suave(xs * 2.5, ys * 0.12, 7, semente + 2) > 0.8) & (BAYER[y0:y1, x0:x1] < 0.3)
    cor[salitre] = cor[salitre] * 0.6 + np.array((150, 150, 136), np.float32) * 0.4
    perto = np.clip((ys - (y1 - umido)) / umido, 0, 1)
    cor *= (1 - 0.32 * degraus(perto, 4, BAYER[y0:y1, x0:x1]))[..., None]
    cor[..., 1] += perto * 6
    verde = (ys > y1 - musgo) & (ruido_suave(xs, ys * 1.5, 6, semente + 3) + perto * 0.4 > 0.78)
    cor[verde] = np.array(((44, 70, 36), (60, 92, 44), (36, 56, 30)), np.float32)[
        (hash2(xs[verde], ys[verde], semente + 4) * 3).astype(int)]
    tela.cor[y0:y1, x0:x1] = cor


def sombra_vertical(tela, y0, y1, forca, x0=0, x1=LARG):
    """Escurece de cima (forca) para baixo (nada), em degraus pontilhados: o teto some no escuro."""
    ys = np.arange(y0, y1, dtype=np.float32)[:, None]
    t = 1 - (ys - y0) / max(1, y1 - y0)
    f = 1 - forca * degraus(np.broadcast_to(t, (y1 - y0, x1 - x0)), 6, BAYER[y0:y1, x0:x1])
    tela.cor[y0:y1, x0:x1] *= f[..., None]


def juntas_de_pedra(tela, mask, x0, y0, alt, larg, semente, cor=(30, 24, 26)):
    """Blocos de cantaria por cima de uma peça já pintada: juntas escuras e aresta de cima clara."""
    ys, xs = np.nonzero(mask)
    fileira = (ys - y0) // alt
    by = (ys - y0) % alt
    bx = (xs - x0 + (fileira % 2) * (larg // 2)) % larg
    junta = (by == alt - 1) | (bx == 0)
    tela.cor[ys[junta], xs[junta]] = cor
    claro = by == 0
    tela.cor[ys[claro], xs[claro]] *= 1.15
    lasca = hash2(xs // 3, ys // 2, semente) > 0.985
    tela.cor[ys[lasca], xs[lasca]] *= 0.7


# ============================================================
# PEÇAS (motor das forjas)
# ============================================================

def arco_ogival(cx, base, meia, apice, passos=24):
    """Pontos de um arco ogival (da esquerda, subindo, até a direita)."""
    r = ((apice - base) ** 2 + meia ** 2) / (2 * meia)              # raio dos dois arcos que se cruzam no ápice
    esq, dir_ = cx - meia + r, cx + meia - r                         # centros (na altura da base)
    a_topo = math.atan2(base - apice, esq - cx)
    lado_esq = [v2(esq - r * math.cos(a), base - r * math.sin(a)) for a in np.linspace(0, a_topo, passos)]
    lado_dir = [v2(dir_ + r * math.cos(a), base - r * math.sin(a)) for a in np.linspace(a_topo, 0, passos)]
    return lado_esq + lado_dir[1:]


def aduelas(tela, cx, base, meia, apice, grossura, n, mat, semente):
    """O arco feito de pedras em cunha (cada uma com o seu volume), com a pedra-chave maior no alto."""
    fora = arco_ogival(cx, base, meia, apice, 60)
    dentro = arco_ogival(cx, base, meia - grossura, apice + grossura * 1.15, 60)
    total = len(fora) - 1
    for k in range(n):
        i0, i1 = round(k * total / n), round((k + 1) * total / n)
        bloco = fora[i0:i1 + 1] + dentro[i0:i1 + 1][::-1]
        chave = k == n // 2
        if chave:
            meio_f, meio_d = fora[(i0 + i1) // 2], dentro[(i0 + i1) // 2]
            bloco = [fora[i0] + v2(-2, -4), meio_f + v2(0, -8), fora[i1] + v2(2, -4), dentro[i1], meio_d + v2(0, 4),
                     dentro[i0]]
        tom = mat.copia(nivel=(hash2(k, 3, semente) - 0.5) * 0.18 + (0.08 if chave else 0))
        tela.pintar(tela.poly(bloco), tom)


def coluna_gotica(tela, x, topo, base, larg, semente):
    """Coluna em feixe: fuste grosso com dois finos dos lados, capitel com folhas e base com molduras."""
    for dx, w in ((-larg * 0.42, larg * 0.24), (larg * 0.42, larg * 0.24), (0, larg * 0.62)):
        fuste = tela.poly(pts([(x + dx - w / 2, topo + 14), (x + dx + w / 2, topo + 14), (x + dx + w / 2, base - 14),
                               (x + dx - w / 2, base - 14)]))
        tela.pintar(fuste, PEDRA if dx == 0 else PEDRA.escuro(1))
        juntas_de_pedra(tela, fuste, int(x + dx - w / 2), topo, 22, 200, semente)
    capitel = tela.poly(pts([(x - larg * 0.7, topo), (x + larg * 0.7, topo), (x + larg * 0.56, topo + 10),
                             (x + larg * 0.5, topo + 16), (x - larg * 0.5, topo + 16), (x - larg * 0.56, topo + 10)]))
    tela.pintar(capitel, PEDRA_CLARA)
    for k in range(5):                                                 # folhas esculpidas do capitel
        fx_ = x - larg * 0.5 + k * larg * 0.25
        tela.pintar(tela.elipse(fx_, topo + 9, 4, 5), PEDRA_CLARA.claro(1))
        tela.px(fx_, topo + 12, (40, 32, 34))
    abaco = tela.poly(pts([(x - larg * 0.78, topo - 5), (x + larg * 0.78, topo - 5), (x + larg * 0.74, topo + 1),
                           (x - larg * 0.74, topo + 1)]))
    tela.pintar(abaco, PEDRA)
    for k, (w, h) in enumerate(((0.62, 5), (0.7, 4), (0.8, 6))):     # molduras da base
        y = base - 14 + sum(hh for _, hh in ((0.62, 5), (0.7, 4), (0.8, 6))[:k])
        tela.pintar(tela.poly(pts([(x - larg * w, y), (x + larg * w, y), (x + larg * w, y + h),
                                   (x - larg * w, y + h)])), PEDRA_CLARA if k == 1 else PEDRA)


VITRAL = np.array(((132, 26, 34), (168, 104, 40), (74, 104, 52), (70, 56, 118), (150, 120, 58), (104, 30, 50),
                   (92, 120, 64), (60, 70, 110)), np.float32)


def rosacea(tela, c, r, semente):
    """A rosácea quebrada: vidro em painéis pequenos (chumbo escuro entre eles), apagado e encardido, aceso por
    trás (emite luz); um rombo grande e painéis arrancados (só o breu). Tracery de pedra: o anel do meio, os raios,
    o anel de fora com uma roda de lóbulos e a moldura; no medalhão, o perfil do rato coroado."""
    c = v2(c)
    yy, xx = np.mgrid[0:ALT, 0:LARG].astype(np.float32)
    dx, dy = xx - c[0], yy - c[1]
    d = np.sqrt(dx * dx + dy * dy)
    ang = (np.arctan2(dy, dx) + math.pi) / (2 * math.pi)
    anel = np.digitize(d, (r * 0.24, r * 0.42, r * 0.62, r * 0.8))
    setores = np.where(anel >= 3, 32, 16)
    setor = (ang * setores).astype(int) % setores
    painel = anel * 64 + setor
    vidro = (d < r - 2) & (anel >= 1)
    cor = VITRAL[(hash2(painel, anel, semente) * len(VITRAL)).astype(int)]
    cor = cor * (0.62 + 0.3 * hash2(painel, 7, semente + 1))[..., None]
    cor *= (0.86 + 0.22 * hash2(xx // 2, yy // 2, semente + 2))[..., None]               # encardido
    chumbo = np.zeros_like(vidro)
    chumbo[:, 1:] |= painel[:, 1:] != painel[:, :-1]
    chumbo[1:, :] |= painel[1:, :] != painel[:-1, :]
    rombo = (ruido_suave(xx, yy, 9, semente + 3) + np.clip((d - r * 0.3) / r, 0, 1) * 0.3
             + np.clip((dx - dy) / (r * 3), -0.2, 0.2) > 0.78)
    arrancado = (hash2(painel, 13, semente + 4) < 0.16) | rombo
    cor[chumbo] = (26, 20, 22)
    cor[arrancado & vidro] = (12, 8, 12)
    tela.cor[vidro] = cor[vidro]
    tela.alfa[vidro] = 255
    tela.emite[vidro & ~arrancado & ~chumbo] = True
    cacos = rombo & vidro & ~ndimage.binary_erosion(rombo) & (BAYER < 0.5)      # cacos na borda do rombo
    tela.cor[cacos] = (200, 190, 150)
    for k in range(16):                                                # raios de pedra
        a = (k + 0.5) / 16 * 2 * math.pi
        u = v2(math.cos(a), math.sin(a))
        tela.pintar(tela.capsula(c + u * r * 0.24, c + u * r * 0.8, 1.3), PEDRA_CLARA, linha_interna=False)
    for k in range(16):                                                # roda de lóbulos entre o anel e a moldura
        a = (k + 0.5) / 16 * 2 * math.pi
        p = c + v2(math.cos(a), math.sin(a)) * r * 0.9
        lobulo = tela.circulo(p, r * 0.1) & ~tela.circulo(p, r * 0.1 - 1.4)
        tela.pintar(lobulo, PEDRA_CLARA, linha_interna=False)
    for raio, esp in ((r * 0.24, 2.2), (r * 0.8, 1.8)):
        tela.pintar(tela.circulo(c, raio + esp) & ~tela.circulo(c, raio - esp), PEDRA_CLARA, linha_interna=False)
    tela.pintar(tela.circulo(c, r + 7) & ~tela.circulo(c, r - 1), PEDRA)
    for k in range(24):                                                # dentes da moldura
        a = k / 24 * 2 * math.pi
        tela.pintar(tela.circulo(c + v2(math.cos(a), math.sin(a)) * (r + 7), 2.2), PEDRA_CLARA)
    medalhao = tela.circulo(c, r * 0.24 - 2)                           # o rato coroado no vidro âmbar
    tela.chapado(medalhao, (190, 140, 62), emite=True)
    s = r * 0.024
    cabeca = [c + v2(-9, 5) * s, c + v2(-4, -3) * s, c + v2(3, -2) * s, c + v2(11, 3) * s, c + v2(4, 6) * s,
              c + v2(-3, 9) * s]
    tela.chapado(tela.poly(cabeca) & medalhao, (44, 22, 26), emite=True)
    tela.chapado(tela.circulo(c + v2(-4, -4) * s, 3 * s) & medalhao, (44, 22, 26), emite=True)
    coroa = [c + v2(-8, -4) * s, c + v2(-8, -11) * s, c + v2(-4, -7) * s, c + v2(-1, -12) * s, c + v2(2, -7) * s,
             c + v2(6, -11) * s, c + v2(5, -3) * s]
    tela.chapado(tela.poly(coroa), (250, 214, 110), emite=True)
    tela.px(c[0] + 6 * s, c[1] + 1 * s, (255, 70, 60), emite=True)


def cortina(tela, x0, x1, preso_x, preso_y, base, semente, lado=1):
    """Cortina de veludo pesada: vários tubos (as dobras, cada um com volume) que descem do teto, são amarrados
    num cordão dourado e se abrem embaixo, com a barra roída e furos de rato."""
    rng = random.Random(semente)
    n = max(5, int((x1 - x0) / 9))
    for k in range(n):
        t = k / (n - 1)
        topo_x = x0 + (x1 - x0) * t
        meio_x = preso_x + (topo_x - preso_x) * 0.18
        fim_x = preso_x + (topo_x - preso_x) * 0.75
        larg = rng.uniform(6.5, 9.5)
        caminho = [v2(topo_x, -4), v2(topo_x * 0.4 + meio_x * 0.6, preso_y * 0.55), v2(meio_x, preso_y),
                   v2(fim_x, base - rng.uniform(0, 10))]
        tubo = tela.corrente(caminho, [larg, larg * 0.9, larg * 0.55, larg * 1.05])
        tela.pintar(tubo, VELUDO if k % 2 else VELUDO.escuro(1))
    barra = tela.alfa > 0
    ys, xs = np.mgrid[0:ALT, 0:LARG]
    roida = barra & (ys > base - 18) & (ruido_suave(xs, ys, 4, semente) > 0.55 + (base - ys) / 40)
    for k in range(int((x1 - x0) / 7)):                                 # mordidas e furos de traça
        x, y = rng.uniform(x0, x1), rng.uniform(preso_y + 10, base - 6)
        roida |= tela.circulo((x, y), rng.uniform(1.2, 2.6)) & barra & (rng.random() < 0.6)
    regiao = (xs >= min(x0, preso_x) - 12) & (xs <= max(x1, preso_x) + 12)
    tela.alfa[roida & regiao] = 0
    for k in range(3):                                                  # o cordão dourado com a borla
        a, b = v2(preso_x - 8 * lado, preso_y - 3 + k * 3), v2(preso_x + 30 * lado, preso_y + 3 + k * 2)
        tela.pintar(tela.capsula(a, b, 1.8), OURO_VELHO, linha_interna=False)
    borla = v2(preso_x + 30 * lado, preso_y + 6)
    tela.pintar(tela.poly([borla + v2(-4, 0), borla + v2(4, 0), borla + v2(6, 18), borla + v2(-6, 18)]), OURO_VELHO)
    tela.pintar(tela.circulo(borla, 4.5), OURO)


def estandarte(tela, x, topo, larg, alt, semente):
    """Estandarte vermelho com o rato coroado bordado em ouro, a barra em pontas roídas e um furo."""
    rng = random.Random(semente)
    tela.pintar(tela.capsula(v2(x - larg / 2 - 6, topo), v2(x + larg / 2 + 6, topo), 2.2), OURO_VELHO)
    for lado in (-1, 1):
        tela.pintar(tela.circulo((x + lado * (larg / 2 + 7), topo), 3.4), OURO)
    contorno = [v2(x - larg / 2, topo + 2), v2(x + larg / 2, topo + 2), v2(x + larg / 2, topo + alt)]
    for k in range(5):                                                  # pontas, cada uma com um tamanho
        t = 1 - (k + 0.5) / 5
        contorno.append(v2(x - larg / 2 + larg * t, topo + alt + (8 if k % 2 == 0 else -2) + rng.uniform(-3, 3)))
    contorno.append(v2(x - larg / 2, topo + alt))
    pano = tela.poly(contorno)
    pano &= ~tela.circulo((x + larg * 0.22, topo + alt * 0.78), 2.5)
    tela.pintar(pano, VELUDO.copia(desce=0.35))
    for k in range(1, 4):                                               # dobras
        xx = x - larg / 2 + k * larg / 4
        tela.chapado(tela.capsula(v2(xx, topo + 6), v2(xx + 1, topo + alt - 4), 0.6) & pano, (96, 16, 28))
    for y in (topo + 7, topo + alt - 6):                                # barras douradas bordadas
        tela.chapado(tela.capsula(v2(x - larg / 2 + 2, y), v2(x + larg / 2 - 2, y), 0.7) & pano, (200, 150, 60))
    c = v2(x, topo + alt * 0.45)                                        # o rato coroado
    tela.chapado(tela.poly([c + v2(-7, 6), c + v2(-2, -3), c + v2(5, -2), c + v2(9, 4), c + v2(2, 8)]), (226, 178, 74))
    tela.chapado(tela.circulo(c + v2(-2, -3), 2.6), (226, 178, 74))
    tela.chapado(tela.poly([c + v2(-6, -6), c + v2(-5, -11), c + v2(-2, -7), c + v2(1, -12), c + v2(3, -7),
                            c + v2(6, -10), c + v2(5, -4)]), (250, 214, 110))
    tela.px(c[0] + 4, c[1] + 1, (60, 10, 14))


def chama(tela, base, altura=7, fase=0.0):
    fx.chama(tela, base, altura, 4.2, cores=FOGO_DE_VELA, fase=fase, linguas=2, brilho=False)


def vela(tela, base, altura, semente, larg=3.2):
    """Vela de sebo grossa, com a cera escorrida pelos lados, e a chama."""
    rng = random.Random(semente)
    base = v2(base)
    topo = base + v2(0, -altura)
    tela.pintar(tela.poly([base + v2(-larg, 0), base + v2(larg, 0), topo + v2(larg, 1), topo + v2(-larg, 0)]), CERA)
    for _ in range(2):                                                  # escorridos
        x = rng.uniform(-larg, larg)
        comp = rng.uniform(altura * 0.3, altura * 0.8)
        tela.pintar(tela.capsula(topo + v2(x, 1), topo + v2(x, comp), 1.1, 1.5), CERA.claro(1), linha_interna=False)
    tela.px(topo[0], topo[1] - 1, (40, 30, 26))
    chama(tela, topo + v2(0, -1), 7, fase=semente)


def candelabro(tela, x, base, topo, semente):
    """Candelabro alto de ouro: pés de garra, haste com nós, três braços com pratos e velas de sebo grossas."""
    for lado in (-1, 0, 1):                                             # os três pés
        tela.pintar(tela.corrente([v2(x, base - 16), v2(x + lado * 9, base - 6), v2(x + lado * 13, base)],
                                  [2.4, 2.2, 2.0]), OURO_VELHO)
    tela.pintar(tela.capsula(v2(x, base - 14), v2(x, topo + 14), 2.4), OURO)
    for y in np.linspace(base - 20, topo + 22, 4):                     # nós da haste
        tela.pintar(tela.elipse(x, y, 4.2, 3), OURO)
    for lado in (-1, 1):                                                # braços curvos
        tela.pintar(tela.corrente([v2(x, topo + 26), v2(x + lado * 10, topo + 24), v2(x + lado * 14, topo + 14),
                                   v2(x + lado * 14, topo + 8)], [1.8, 1.8, 1.6, 1.6]), OURO)
    for dx, dy in ((-14, 6), (0, 0), (14, 6)):
        prato = v2(x + dx, topo + 8 + dy)
        tela.pintar(tela.elipse(prato[0], prato[1], 5.5, 2), OURO)
        vela(tela, prato + v2(0, -1), 10 + (4 if dx == 0 else 0), semente + dx)


def moedas(tela, rng, x0, x1, base, altura, n):
    """Monte de moedas: muitas moedinhas de ouro deitadas (elipses), mais altas no meio do monte."""
    for _ in range(n):
        t = rng.random()
        x = x0 + (x1 - x0) * t
        topo = base - altura * math.sin(t * math.pi) ** 0.8
        y = rng.uniform(topo, base - 1)
        mat = OURO if rng.random() < 0.7 else OURO_VELHO
        tela.pintar(tela.elipse(x, y, rng.uniform(2.2, 3.4), rng.uniform(1.0, 1.6)), mat, linha_interna=True)
        if rng.random() < 0.08:
            tela.px(x - 1, y - 1, (255, 250, 210))


def cranio(tela, c, tam=1.0, mat=OSSO):
    c = v2(c)
    tela.pintar(tela.elipse(c[0], c[1], 5 * tam, 4.6 * tam), mat)
    tela.pintar(tela.poly([c + v2(-3.4 * tam, 2 * tam), c + v2(3.4 * tam, 2 * tam), c + v2(2.6 * tam, 6 * tam),
                           c + v2(-2.6 * tam, 6 * tam)]), mat)
    for dx in (-1.8, 1.8):
        tela.chapado(tela.elipse(c[0] + dx * tam, c[1] + 0.6 * tam, 1.3 * tam, 1.5 * tam), (20, 12, 14))
    tela.chapado(tela.poly([c + v2(-0.6 * tam, 2.4 * tam), c + v2(0.6 * tam, 2.4 * tam), c + v2(0, 3.6 * tam)]),
                 (30, 18, 18))
    for dx in (-1.6, -0.2, 1.2):
        tela.px(c[0] + dx * tam, c[1] + 5 * tam, (60, 50, 44))


def osso(tela, a, b, larg=1.4):
    a, b = v2(a), v2(b)
    tela.pintar(tela.capsula(a, b, larg), OSSO)
    for p in (a, b):
        d = (b - a) / max(1e-6, np.hypot(*(b - a)))
        n = v2(-d[1], d[0])
        tela.pintar(tela.circulo(p + n * larg * 0.8, larg * 1.1) | tela.circulo(p - n * larg * 0.8, larg * 1.1), OSSO)


def calice(tela, base, tam=1.0, deitado=False):
    base = v2(base)
    if deitado:
        tela.pintar(tela.poly([base + v2(-6 * tam, -1), base + v2(4 * tam, -4 * tam), base + v2(6 * tam, 0),
                               base + v2(-5 * tam, 2)]), OURO)
        tela.pintar(tela.elipse(base[0] + 6 * tam, base[1] - 2 * tam, 1.6 * tam, 3 * tam), OURO_VELHO)
        return
    tela.pintar(tela.elipse(base[0], base[1] - 1, 4 * tam, 1.4 * tam), OURO)
    tela.pintar(tela.capsula(base + v2(0, -2), base + v2(0, -7 * tam), 1.2 * tam), OURO)
    copa = tela.poly([base + v2(-5 * tam, -13 * tam), base + v2(5 * tam, -13 * tam), base + v2(2.6 * tam, -7 * tam),
                      base + v2(-2.6 * tam, -7 * tam)])
    tela.pintar(copa, OURO)
    tela.px(base[0] - 2, base[1] - 11 * tam, (190, 30, 40))


def bau(tela, base, larg=26, alt=14):
    """Baú aberto, transbordando moedas."""
    x, y = base
    caixa = tela.poly(pts([(x - larg / 2, y - alt), (x + larg / 2, y - alt), (x + larg / 2, y), (x - larg / 2, y)]))
    tela.pintar(caixa, MADEIRA)
    for dx in (-larg / 2 + 3, larg / 2 - 3):
        tela.pintar(tela.capsula(v2(x + dx, y - alt), v2(x + dx, y), 1.4), FERRO, linha_interna=False)
    tampa = tela.poly(pts([(x - larg / 2, y - alt), (x + larg / 2, y - alt), (x + larg / 2 + 2, y - alt - 12),
                           (x - larg / 2 + 2, y - alt - 14)]))
    tela.pintar(tampa, MADEIRA.escuro(1))
    tela.pintar(tela.elipse(x, y - alt, larg / 2 - 1, 4), OURO)
    tela.pintar(tela.circulo((x, y - alt / 2), 2), OURO_VELHO)


def queijo(tela, base, r=9, mordido=True):
    """Roda de queijo (mordida, com furos)."""
    x, y = base
    lado = tela.elipse(x, y - r * 0.35, r, r * 0.38) | tela.poly(pts([(x - r, y - r * 0.35), (x + r, y - r * 0.35),
                                                                       (x + r, y - r * 0.9), (x - r, y - r * 0.9)]))
    tampa = tela.elipse(x, y - r * 0.9, r, r * 0.38)
    if mordido:
        for k in range(3):
            lado &= ~tela.circulo((x + r * 0.7, y - r * (0.4 + k * 0.25)), r * 0.28)
            tampa &= ~tela.circulo((x + r * 0.75, y - r * (0.85 + k * 0.1)), r * 0.3)
    tela.pintar(lado, CASCA)
    tela.pintar(tampa, QUEIJO)
    for dx, dy in ((-0.4, -0.95), (0.2, -0.8), (-0.1, -1.05)):
        tela.chapado(tela.elipse(x + dx * r, y + dy * r, 1.2, 0.7), (180, 130, 50))


def rato_morto(tela, c, tam=1.0, olhando=1):
    """Rato morto deitado de lado, patinhas para cima e o rabo largado."""
    c = v2(c)
    tela.pintar(tela.elipse(c[0], c[1], 9 * tam, 4.5 * tam), PELO)
    tela.pintar(tela.poly([c + v2(olhando * 7 * tam, -3 * tam), c + v2(olhando * 14 * tam, 0),
                           c + v2(olhando * 7 * tam, 3 * tam)]), PELO)
    tela.px(c[0] + olhando * 9 * tam, c[1] - 1, (30, 20, 20))
    for dx in (-4, 2):
        tela.traco(c + v2(dx * tam, -4 * tam), c + v2(dx * tam + 1, -7 * tam), (170, 120, 116))
    tela.pintar(tela.corrente([c + v2(-olhando * 8 * tam, 1), c + v2(-olhando * 16 * tam, 3),
                               c + v2(-olhando * 24 * tam, 1)], [1.4, 1.0, 0.6]), RABO, linha_interna=False)


def rato_vivo(tela, c, tam, olhando, fase=0.0, mat=PELO):
    """Rato pequeno, visto de lado (no monte de ossos): corpo, focinho, orelha, olho vermelho e rabo."""
    c = v2(c)
    tela.pintar(tela.elipse(c[0], c[1], 7 * tam, 4 * tam), mat)
    focinho = [c + v2(olhando * 5 * tam, -3 * tam), c + v2(olhando * 12 * tam, 0.5 * tam),
               c + v2(olhando * 5 * tam, 2.5 * tam)]
    tela.pintar(tela.poly(focinho), mat)
    tela.pintar(tela.circulo(c + v2(olhando * 4 * tam, -4 * tam), 2.2 * tam), RABO)
    tela.px(c[0] + olhando * 8 * tam, c[1] - 1.2 * tam, OLHO, emite=True)
    tela.pintar(tela.corrente([c + v2(-olhando * 6 * tam, 1), c + v2(-olhando * 12 * tam, 3 + math.sin(fase) * 2),
                               c + v2(-olhando * 18 * tam, 1)], [1.2, 0.9, 0.5]), RABO, linha_interna=False)


# ============================================================
# AS CAMADAS
# ============================================================

def camada_do_fundo(rng):
    """ceu: a parede e a abóbada, o grande arco ogival atrás do trono e a rosácea."""
    tela = nova_tela(1, forca_borda=0.0)
    tijolos(tela, 0, 0, LARG, HOR + 6, 11)
    sujeira(tela, 0, 0, LARG, HOR + 6, 12)
    sombra_vertical(tela, 0, 90, 0.72)
    # tocas de rato no rodapé, com olhos no escuro
    for x in (120, 214, 506, 590):
        toca = tela.elipse(x, HOR + 2, 7, 8) & (np.mgrid[0:ALT, 0:LARG][0] < HOR + 2)
        tela.chapado(toca, (10, 6, 8))
        if x in (120, 590):
            for dx in (-2, 2):
                tela.px(x + dx, HOR - 3, OLHO, emite=True)
    # nervuras da abóbada saindo das colunas
    for x0, lado in ((150, 1), (554, -1)):
        tela.pintar(tela.corrente([v2(x0, 46), v2(x0 + lado * 70, 8), v2(x0 + lado * 150, -8)], [5, 5, 5]),
                    PEDRA.escuro(1))
        tela.pintar(tela.corrente([v2(x0, 46), v2(x0 - lado * 50, 10), v2(x0 - lado * 110, -6)], [5, 5, 5]),
                    PEDRA.escuro(1))
    # o nicho do trono: o arco ogival com o fundo afundado na sombra
    nicho = tela.poly(arco_ogival(CX, 150, 96, 34, 40) + [v2(CX + 96, HOR + 6), v2(CX - 96, HOR + 6)])
    tela.cor[nicho] *= 0.5
    rosacea(tela, (CX, 96), 50, 13)
    aduelas(tela, CX, 150, 112, 18, 16, 21, PEDRA, 14)
    for lado in (-1, 1):                                                # ombreiras do arco
        x0 = CX + lado * 104
        ombreira = tela.poly(pts([(x0 - 8, 148), (x0 + 8, 148), (x0 + 8, HOR + 6), (x0 - 8, HOR + 6)]))
        tela.pintar(ombreira, PEDRA)
        juntas_de_pedra(tela, ombreira, x0 - 8, 148, 14, 30, 15)
    iluminar(tela, luzes_da_cena())
    raios_de_luz(tela)
    return finalizar(tela, contorno=False)


def raios_de_luz(tela):
    """Fachos finos de luz pálida descendo da rosácea (pontilhado ralo, some no meio do caminho)."""
    yy, xx = np.mgrid[0:ALT, 0:LARG].astype(np.float32)
    for inclina, larg, forca in ((-0.34, 5, 0.2), (-0.12, 7, 0.24), (0.1, 6, 0.22), (0.3, 4, 0.16)):
        t = (yy - 120) / (HOR - 120)
        centro = CX + (yy - 96) * inclina
        dentro = (np.abs(xx - centro) < larg * (0.7 + t)) & (t > 0) & (t < 1)
        sel = dentro & (BAYER < forca * np.sin(np.clip(t, 0, 1) * math.pi) ** 0.7)
        tela.cor[sel] = tela.cor[sel] * 0.6 + np.array((200, 196, 160), np.float32) * 0.4


def camada_longe(rng):
    """longe: colunas, cortinas, estandartes, canos e correntes."""
    tela = nova_tela(2)
    for x in (150, 554):
        coluna_gotica(tela, x, 44, HOR + 4, 46, 21 + x)
    for x in (204, 500):
        estandarte(tela, x, 30, 30, 112, 22 + x)
    # canos enferrujados correndo pela parede, com registro e gotas de lodo
    for (a, b) in (((0, 128), (128, 128)), ((576, 120), (704, 120))):
        tela.pintar(tela.capsula(v2(*a), v2(*b), 4), FERRUGEM)
        for x in range(a[0] + 10, b[0], 26):
            tela.pintar(tela.elipse(x, a[1], 2.4, 5.5), FERRUGEM.escuro(1))
    tela.pintar(tela.capsula(v2(600, 120), v2(600, 168), 3.5), FERRUGEM)
    tela.pintar(tela.circulo((100, 128), 7) & ~tela.circulo((100, 128), 4.5), FERRO)
    for x in (52, 610, 660):
        tela.chapado(tela.capsula(v2(x, 132), v2(x, 138), 1.2), (90, 160, 80), emite=True)
    # correntes pendendo da abóbada
    for x, comp in ((214, 70), (232, 44), (480, 58), (494, 90)):
        for y in range(0, comp, 5):
            elo = tela.elipse(x + (y // 5) % 2 * 0.5, y, 1.8 if (y // 5) % 2 else 1.2, 2.8)
            tela.pintar(elo, FERRO, linha_interna=False)
        if comp > 80:                                                   # um gancho com um rato pendurado
            rato_morto(tela, (x + 2, comp + 10), 0.8, olhando=1)
    cortina(tela, -6, 100, 34, 168, HOR + 8, 23, lado=-1)
    cortina(tela, 604, 710, 670, 168, HOR + 8, 24, lado=1)
    iluminar(tela, luzes_da_cena())
    return finalizar(tela)


def camada_meio(rng):
    """meio: candelabros, os montes de tesouro, a ossada e a boca do cano despejando lodo."""
    tela = nova_tela(3, borda=(220, 170, 110), forca_borda=0.26)
    r = random.Random(31)
    # tesouro à esquerda: baú, moedas, cálices, queijo e crânios
    moedas(tela, r, 96, 196, HOR + 2, 18, 170)
    bau(tela, (130, HOR - 4))
    queijo(tela, (178, HOR + 1), 11)
    calice(tela, (108, HOR - 6), 1.1)
    calice(tela, (158, HOR - 2), 0.9, deitado=True)
    cranio(tela, (196, HOR - 2), 1.1)
    moedas(tela, r, 96, 204, HOR + 4, 6, 70)
    # a ossada à direita: ossos, crânios, uma coroa torta e ratos rondando
    for k in range(26):
        a = v2(r.uniform(520, 600), r.uniform(HOR - 16, HOR + 2))
        osso(tela, a, a + v2(r.uniform(-12, 12), r.uniform(-4, 4)), r.uniform(1.0, 1.6))
    for x, y, t in ((532, HOR - 6, 1.2), (556, HOR - 14, 1.0), (580, HOR - 4, 1.3), (548, HOR, 0.9)):
        cranio(tela, (x, y), t)
    moedas(tela, r, 520, 604, HOR + 4, 6, 50)
    rato_vivo(tela, (566, HOR - 22), 1.0, -1)
    rato_vivo(tela, (512, HOR - 2), 0.9, 1)
    # a boca do cano grande na parede da direita, despejando lodo verde até o chão
    bx, by = BOCA_DO_CANO
    tela.pintar(tela.circulo((bx, by), 24), FERRUGEM)
    tela.pintar(tela.circulo((bx, by), 18), FERRUGEM.escuro(2))
    tela.chapado(tela.circulo((bx - 1, by + 1), 15), (12, 14, 10))
    for k in range(8):                                                  # rebites
        a = k / 8 * 2 * math.pi
        tela.pintar(tela.circulo((bx + math.cos(a) * 21, by + math.sin(a) * 21), 1.6), FERRO, linha_interna=False)
    jorro = tela.poly(pts([(bx - 10, by + 8), (bx + 6, by + 10), (bx + 9, HOR + 4), (bx - 14, HOR + 4)]))
    tela.pintar(jorro, LODO.copia(desce=-0.2))
    for k in range(5):
        x = bx - 10 + k * 4
        tela.chapado(tela.capsula(v2(x, by + 12), v2(x + 1, HOR + 2), 0.7) & jorro, (150, 220, 120), emite=True)
    tela.chapado(tela.circulo((bx - 2, by + 6), 9) & ~tela.circulo((bx - 2, by + 2), 9), (120, 200, 100), emite=True)
    # candelabros dos dois lados do trono
    for x in CANDELABROS:
        candelabro(tela, x, HOR + 4, 104, 41 + x)
    iluminar(tela, luzes_da_cena())
    return finalizar(tela)


# ---------------- o chão ----------------

def degraus_do_estrado():
    """(x0, x1, topo da face de cima, topo do espelho, base) de cada degrau, do de baixo para o de cima."""
    return ((226, 478, HOR + 2, HOR + 6, HOR + 14), (256, 448, HOR - 6, HOR - 2, HOR + 4))


def camada_do_chao(rng):
    """chao: lajes molhadas em perspectiva, o estrado de dois degraus e o tapete vermelho roído até a frente.
    Devolve (camada, terreno) — o terreno diz à água onde é alto."""
    tela = nova_tela(4, forca_borda=0.0)
    yy, xx = np.mgrid[0:ALT, 0:LARG].astype(np.float32)
    terreno = np.zeros((ALT, LARG), np.float32)
    piso = yy >= HOR
    # perspectiva: o ponto de fuga fica acima do chão (na altura dos olhos)
    fuga_y = HOR - 150
    s = np.clip((yy - fuga_y) / (ALT - fuga_y), 0.05, 1)
    mx = (xx - CX) / s                                                  # x "no mundo"
    mz = 1 / s                                                          # profundidade
    ix = np.floor(mx / 46 + 0.5 * (np.floor(mz * 7.5) % 2)).astype(int)
    iz = np.floor(mz * 7.5).astype(int)
    tom = np.array(((70, 58, 56), (60, 50, 50), (78, 64, 58), (56, 48, 48), (66, 58, 54)), np.float32)
    cor = tom[(hash2(ix, iz, 41) * 5).astype(int)] * (0.9 + 0.2 * hash2(xx // 2, yy // 2, 42))[..., None]
    junta = np.zeros_like(piso)
    junta[1:, :] |= iz[1:, :] != iz[:-1, :]
    junta[:, 1:] |= ix[:, 1:] != ix[:, :-1]
    cor[junta] = (24, 18, 18)
    de_baixo = np.zeros_like(piso)
    de_baixo[:-1, :] = junta[1:, :]
    cor[de_baixo & ~junta] *= 0.8
    aresta = np.zeros_like(piso)
    aresta[1:, :] = junta[:-1, :]
    cor[aresta & ~junta] *= 1.18
    rach = (ruido_suave(mx * 0.5, mz * 40, 3, 43) > 0.83) & (BAYER < 0.6)          # rachaduras e limo nas juntas
    cor[rach] *= 0.55
    limo = junta & (ruido_suave(xx, yy, 9, 44) > 0.55)
    cor[limo] = (40, 64, 34)
    # o chão escurece longe das velas e perto da câmera fica úmido e brilhante
    brilho = (hash2(xx // 3, yy, 45) > 0.985) & (yy > HOR + 30)
    cor[brilho] = cor[brilho] * 0.5 + np.array((150, 140, 120), np.float32) * 0.5
    tela.cor[piso] = cor[piso]
    tela.alfa[piso] = 255
    # o tapete vermelho roído, do estrado até a frente (com franja dourada e mordidas)
    meia = 40 + (yy - HOR) * 0.75
    no_tapete = piso & (np.abs(xx - CX) < meia) & (yy > HOR + 12)
    borda = no_tapete & (np.abs(xx - CX) > meia - 3 - (yy - HOR) * 0.02)
    trama = (126 + 18 * (hash2(xx // 2, yy, 46) - 0.5))
    tapete = np.stack([trama, trama * 0.18, trama * 0.26], -1)
    tapete *= (1 - 0.35 * (ruido_suave(xx, yy * 2, 14, 47) > 0.62))[..., None]               # manchas
    mordida = no_tapete & (np.abs(xx - CX) > meia - 10) & (ruido_suave(xx, yy, 5, 48) > 0.6)
    tela.cor[no_tapete] = tapete[no_tapete]
    tela.cor[borda] = np.array((196, 150, 60), np.float32)
    tela.cor[mordida] = cor[mordida]
    gasto = no_tapete & (ruido_suave(xx * 0.7, yy * 1.6, 10, 49) > 0.72) & (BAYER < 0.5) & ~borda
    tela.cor[gasto] *= 0.65
    # o estrado do trono (dois degraus de pedra; o de cima fica bem seco: a água só cobre na alta)
    for k, (x0, x1, topo, espelho, base) in enumerate(degraus_do_estrado()):
        face = tela.poly(pts([(x0 + 4, topo), (x1 - 4, topo), (x1, espelho), (x0, espelho)]))
        frente = tela.poly(pts([(x0, espelho), (x1, espelho), (x1, base), (x0, base)]))
        tela.pintar(face, PEDRA_CLARA, plano=True)
        tela.pintar(frente, PEDRA)
        juntas_de_pedra(tela, frente, x0, espelho, 30, 26, 50 + k)
        terreno[face | frente] = 0.55 if k == 0 else 0.9
    passadeira = tela.poly(pts([(CX - 34, HOR - 6), (CX + 34, HOR - 6), (CX + 40, HOR + 14), (CX - 40, HOR + 14)]))
    tela.pintar(passadeira, VELUDO_ESCURO, plano=True)                    # o tapete sobe o estrado
    for y in (HOR - 2, HOR + 6):
        tela.chapado(tela.capsula(v2(CX - 38, y), v2(CX + 38, y), 0.5) & passadeira, (60, 8, 16))
    # moedas, ossos, um cálice caído e a grade do ralo
    r = random.Random(51)
    for _ in range(90):
        x, y = r.uniform(30, LARG - 30), r.uniform(HOR + 16, ALT - 4)
        tam = 0.6 + (y - HOR) / (ALT - HOR) * 1.2
        tela.pintar(tela.elipse(x, y, 2.2 * tam, 1.0 * tam), OURO if r.random() < 0.8 else OURO_VELHO,
                    linha_interna=False)
    for _ in range(9):
        a = v2(r.uniform(40, LARG - 40), r.uniform(HOR + 20, ALT - 10))
        osso(tela, a, a + v2(r.uniform(-14, 14), r.uniform(-3, 3)), 1.2)
    calice(tela, (226, HOR + 40), 1.2, deitado=True)
    ralo = tela.elipse(548, 300, 20, 7)
    tela.pintar(ralo, FERRO)
    for k in range(-16, 18, 5):
        tela.chapado(tela.capsula(v2(548 + k, 295), v2(548 + k, 305), 0.8) & ralo, (12, 10, 12))
    # o lodo do cano correndo pelo chão até o ralo
    for k in range(40):
        t = k / 39
        p = lerp(v2(BOCA_DO_CANO[0] - 4, HOR + 2), v2(560, 298), t) + v2(math.sin(t * 9) * 4, 0)
        tela.pintar(tela.elipse(p[0], p[1], 6 + t * 6, 2 + t * 2), LODO, linha_interna=False)
    iluminar(tela, luzes_da_cena(), ate=piso | (tela.alfa > 0))
    return finalizar(tela, contorno=False), terreno


def camada_da_frente(rng):
    """frente (só nos cantos de baixo): moedas, crânio com vela e cálice à esquerda; tambor de coluna caído, rato
    morto e uma coroa à direita."""
    tela = nova_tela(5, borda=(230, 170, 110), forca_borda=0.3)
    r = random.Random(61)
    moedas(tela, r, 26, 150, ALT + 2, 30, 210)
    calice(tela, (118, ALT - 18), 1.5, deitado=True)
    cranio(tela, (74, ALT - 34), 2.0)
    vela(tela, (74, ALT - 44), 12, 62, larg=3.6)
    tambor = tela.elipse(640, ALT - 18, 46, 20) | tela.poly(pts([(594, ALT - 18), (686, ALT - 18), (686, ALT + 4),
                                                                   (594, ALT + 4)]))
    tela.pintar(tambor, PEDRA)
    tela.pintar(tela.elipse(596, ALT - 6, 10, 20), PEDRA_CLARA)
    for k in range(4):
        tela.chapado(tela.capsula(v2(606 + k * 18, ALT - 34), v2(606 + k * 18, ALT + 2), 0.8) & tambor, (54, 46, 46))
    rato_morto(tela, (612, ALT - 42), 1.4, olhando=-1)
    coroa = [v2(556, ALT - 6), v2(552, ALT - 22), v2(560, ALT - 14), v2(566, ALT - 26), v2(572, ALT - 14),
             v2(580, ALT - 22), v2(578, ALT - 4)]
    tela.pintar(tela.poly(coroa), OURO)
    for x, c in ((560, (200, 30, 40)), (570, (60, 130, 200))):
        tela.chapado(tela.circulo((x, ALT - 10), 1.6), c)
    iluminar(tela, luzes_da_cena(), ambiente=LUZ_AMBIENTE * 0.8)
    return finalizar(tela)


def camada_do_no_da_rainha(rng):
    """no_da_rainha: a coroa da Rainha presa num nó de caudas, pendurada por correntes nas sombras do teto, com os
    ratos amarrados pendendo em volta (a tela esconde esta camada quando a Rainha desce para a luta)."""
    tela = nova_tela(6, borda=(170, 100, 100), forca_borda=0.25)
    c = v2(536, 44)
    for dx in (-14, 0, 14):                                             # as correntes até a escuridão
        for y in range(0, 30, 4):
            tela.pintar(tela.elipse(c[0] + dx * (1 - y / 44), y, 1.4 if (y // 4) % 2 else 2.2, 2.6), FERRO,
                        linha_interna=False)
    r = random.Random(71)
    for k in range(8):                                                  # ratos amarrados pendendo em volta
        a = math.pi * (0.05 + 0.9 * k / 7)
        fim = c + v2(math.cos(a) * 44, 8 + math.sin(a) * 30)
        rabo = [c + v2(math.cos(a) * 10, 6), lerp(c, fim, 0.55) + v2(0, 6), fim]
        tela.pintar(tela.corrente(rabo, [2.0, 1.6, 1.2]), RABO, linha_interna=False)
        giro = math.atan2(fim[1] - c[1], fim[0] - c[0])
        u = v2(math.cos(giro), math.sin(giro))
        tela.pintar(tela.elipse_girada(fim + u * 8, 9, 4.6, giro), PELO.claro(r.randint(0, 1)))
        tela.pintar(tela.poly([fim + u * 14 + v2(-u[1], u[0]) * 3, fim + u * 21, fim + u * 14 - v2(-u[1], u[0]) * 3]),
                    PELO)
        tela.pintar(tela.circulo(fim + u * 12 + v2(-u[1], u[0]) * 3.5, 2.2), RABO)
        tela.px(*(fim + u * 16 + v2(-u[1], u[0]) * 1.2), OLHO, emite=True)
    for k in range(10):                                                 # o nó de caudas embaixo da coroa
        a = k * 0.63
        p0 = c + v2(math.cos(a) * 18, 8 + math.sin(a) * 6)
        p1 = c + v2(math.cos(a + 2.4) * 18, 8 + math.sin(a + 2.4) * 6)
        tela.pintar(tela.corrente([p0, lerp(p0, p1, 0.5) + v2(0, -4 + k % 3 * 4), p1], [2.2, 2.2, 2.2]),
                    RABO.escuro(k % 2))
    coroa = [c + v2(-18, 6), c + v2(-20, -12), c + v2(-12, -3), c + v2(-7, -17), c + v2(0, -5), c + v2(7, -17),
             c + v2(12, -3), c + v2(20, -12), c + v2(18, 6)]
    tela.pintar(tela.poly(coroa), OURO)
    tela.pintar(tela.capsula(c + v2(-18, 4), c + v2(18, 4), 2.6), OURO_VELHO)
    for k, cor in enumerate(((190, 30, 40), (60, 110, 200), (80, 160, 80), (140, 60, 180))):
        tela.chapado(tela.circulo(c + v2(-11 + k * 7.3, 4), 1.9), cor)
    for k in range(5):                                                  # caudas enroladas por cima da coroa
        a = 0.4 + k * 0.55
        p0 = c + v2(-20 + k * 9, -2 - (k % 2) * 4)
        tela.pintar(tela.corrente([p0, p0 + v2(4, 9), p0 + v2(9, 2)], [1.8, 1.8, 1.6]), RABO, linha_interna=True)
    tela.brilho(c + v2(0, 6), 46, (170, 40, 50), 0.45)
    iluminar(tela, [(536, 50, 80, (190, 60, 60), 0.6)], ambiente=LUZ_AMBIENTE * 0.9)
    return finalizar(tela)


def cena_salao_do_trono(rng, variante):
    """As 5 camadas + o nó da Rainha e o chão de cada nível da água; posições do cenarios.json na escala antiga."""
    ceu = camada_do_fundo(rng)
    longe = camada_longe(rng)
    meio = camada_meio(rng)
    chao, terreno = camada_do_chao(rng)
    frente = camada_da_frente(rng)
    luzes = luzes_do_jogo()
    configuracao = {
        "luzes": [[round(x / V), round(y / V), round(raio / V), list(cor), tremula] for x, y, raio, cor, tremula in luzes],
        "particulas": [["mosca", 12], ["poeira", 22], ["olhos", 12], ["gota_verde", 5]],
        "cor_nevoa": [80, 40, 40],
        "trono": {"base": [CX // V, BASE_DO_TRONO // V], "assento": [CX // V, 85], "pes": [CX // V, 101]},
        "camadas_extras": {"no_da_rainha": "longe"},
        "_camadas": {"no_da_rainha": camada_do_no_da_rainha(rng)},
    }
    camadas = [ceu, longe, meio, chao, frente]
    chao_alagado(camadas, configuracao, HOR, [(x, y, raio * 1.4, cor) for x, y, raio, cor, _ in luzes], 5,
                 altura=terreno, vezes=V)
    return camadas, configuracao
