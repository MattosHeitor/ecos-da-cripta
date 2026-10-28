"""Equipamento visível no herói: uma camada por TIPO de peça (não por peça).

Cada tipo é uma função desenhar(tela, ctx, J, camada) e vira uma folha por geometria de herói
(camada_<geometria>_eq_<tipo>.png), com o mesmo esqueleto e as mesmas poses do herói: encaixa
quadro a quadro em qualquer roupa daquela geometria (como as skins de chapéu).

As partes que mudam de cor são pintadas em CINZA NEUTRO: o jogo tinge cada peça com a cor dela
(raridade, set ou a cor própria da peça, em dados/visual_equipamentos.json). Madeira, couro dos cabos,
cordas, ouro e chamas têm cor própria e não são tingidos. Para o jogo não precisar de numpy, cada quadro
já sai separado em dois (separar_tinta): as linhas normais têm só o que se tinge e as linhas "<anim>_fixo"
o resto; o jogo multiplica a primeira pela cor (um fill do pygame) e cola a segunda por cima.

    cabeça      elmo, elmo_chifrudo, capuz, coroa, mascara, veu
    peitoral    placas, couraca, tunica, ossos
    calças      calcas, grevas
    botas       botas
    capa        capa e manto (atrás do herói) + capa_gola e manto_gola (na frente)
    amuleto     colar, anel, estandarte (atrás), lanterna_cinto, rato_no_ombro
    arma        espada, espada_curva, adaga, adagas, machado, martelo, maca, mangual, chicote, foice,
                cajado, cetro, arco, alaude, pa, picareta
    secundária  escudo, broquel, lanterna, grimorio, adaga_b, picareta_b

ATRAS = tipos desenhados ATRÁS do herói (capas e estandarte); os outros vão por cima, nesta ordem:
pernas -> tronco -> pescoço -> cabeça -> mãos. Tudo que fica no tronco é apagado onde passa o braço
da frente, para o braço continuar por cima da armadura.
"""
import math

import numpy as np
from PIL import Image

from ..humanoide import quadro_tronco, quadro_cabeca, tronco, capa as capa_nas_costas, cinto
from ..motor import Mat, metal, v2, lerp, dir_ang
from .. import armas, texturas as T
from .herois import MADEIRA, COURO_ESC, OURO_VELHO, OSSO

NEUTRO_METAL = metal((222, 222, 226), especular=(255, 255, 255))
NEUTRO_PANO = Mat((220, 220, 220), 6, desce=0.3, ruido=0.1, relevo=0.8)
NEUTRO_COURO = Mat((216, 216, 216), 6, relevo=0.9, ruido=0.2)
NEUTRO_MADEIRA = Mat((216, 216, 216), 6, relevo=1.0, ruido=0.3)
NEUTRO_LUZ = (240, 240, 240)                  # gemas e runas: brilham na cor da peça
FIXO = "_fixo"                                # linhas da folha com o que não é tingido


def separar_tinta(img):
    """Separa um quadro em dois: o que o jogo tinge (cinza neutro) e o que fica com a cor própria
    (madeira, couro, ouro, chamas e os reflexos brancos do metal)."""
    a = np.asarray(img).copy()
    rgb = a[..., :3].astype(np.int16)
    neutro = ((rgb.max(axis=2) - rgb.min(axis=2)) <= 14) & (rgb.max(axis=2) < 245)
    tinta, fixo = a.copy(), a.copy()
    tinta[~neutro, 3] = 0
    fixo[neutro, 3] = 0
    return Image.fromarray(tinta, "RGBA"), Image.fromarray(fixo, "RGBA")
CORDA = (64, 44, 34)
CHAMA = (255, 200, 110)

# quanto da canela fica coberta pela barra da roupa (vestes longas): as calças só aparecem abaixo dela
BARRA = {"mago": 0.75, "feiticeira": 0.85, "medico_da_peste": 0.7, "senhor_dos_ratos": 0.85}


# ============================================================
# AJUDANTES
# ============================================================

def medidas_da_cabeca(J):
    h = J["P"]["cabeca"]
    return quadro_cabeca(J), h, h * 0.82


def apagar(tela, mask):
    tela.alfa[mask] = 0
    tela.emite[mask] = False


def sob_o_braco(tela, J):
    """Apaga a peça onde passa o braço da frente do herói (o braço fica por cima da armadura)."""
    S = J["P"]
    o, c, m = J["ombro_f"], J["cotovelo_f"], J["mao_f"]
    mask = tela.capsula(o, c, S["l_braco"] * 1.35, S["l_antebraco"] * 1.3)
    mask |= tela.capsula(c, m, S["l_antebraco"] * 1.3, S["l_antebraco"] * 1.1) | tela.circulo(m, S["mao"] * 0.95)
    apagar(tela, mask)


def maos(J, camada):
    """(mão da arma principal, mão da secundária)."""
    principal = camada.mao
    return principal, ("b" if principal == "f" else "f")


def empunhar(J, lado):
    return J["mao_" + lado], J.get("arma_" + lado, J["arma_f"])


def dedos_por_cima(tela, J, lado):
    """Os dedos do herói (na folha de baixo) ficam por cima do cabo."""
    apagar(tela, tela.circulo(J["mao_" + lado], J["P"]["mao"] * 0.7))


def gema(tela, c, raio=1.0, brilho=0.5):
    tela.chapado(tela.circulo(c, raio), NEUTRO_LUZ, emite=True)
    tela.brilho(c, 3 + raio * 2, NEUTRO_LUZ, brilho)


# ============================================================
# CABEÇA
# ============================================================

def elmo(tela, ctx, J, camada):
    """Elmo fechado: domo com crista, viseira de fenda e rebites."""
    C, h, w = medidas_da_cabeca(J)
    domo = C.pts([(-w * 0.98, -h * 0.1), (-w * 1.02, h * 0.35), (-w * 0.62, h * 0.78), (0, h * 0.9), (w * 0.62, h * 0.78),
                  (w * 1.02, h * 0.35), (w * 1.0, -h * 0.15), (w * 0.2, -h * 0.08)])
    tela.pintar(tela.poly(domo), NEUTRO_METAL)
    tela.traco(C.pt(w * 0.15, h * 0.12), C.pt(w * 0.98, h * 0.12), (14, 8, 16))             # fenda dos olhos
    tela.traco(C.pt(-w * 0.1, h * 0.9), C.pt(-w * 0.2, h * 0.3), NEUTRO_METAL[6], sobre=True)    # crista
    for x in (-w * 0.6, w * 0.1, w * 0.7):
        tela.px(*C.pt(x, h * 0.42), NEUTRO_METAL[1])


def elmo_chifrudo(tela, ctx, J, camada):
    """Elmo aberto de guerra com protetor de nariz e dois chifres curvos."""
    C, h, w = medidas_da_cabeca(J)
    domo = C.pts([(-w * 1.0, -h * 0.05), (-w * 1.02, h * 0.4), (-w * 0.55, h * 0.84), (w * 0.15, h * 0.9), (w * 0.68, h * 0.7),
                  (w * 0.92, h * 0.32), (w * 0.85, h * 0.12), (w * 0.15, h * 0.08)])
    tela.pintar(tela.poly(domo), NEUTRO_METAL)
    tela.pintar(tela.capsula(C.pt(w * 0.66, h * 0.2), C.pt(w * 0.7, -h * 0.28), h * 0.08), NEUTRO_METAL.claro(1))
    for dx, escala, mat in ((-w * 0.45, 0.85, OSSO.escuro(1)), (w * 0.05, 1.0, OSSO)):
        pts = [C.pt(dx, h * 0.7), C.pt(dx - w * 0.45 * escala, h * 1.0 * escala), C.pt(dx - w * 0.75 * escala, h * 1.45 * escala),
               C.pt(dx - w * 0.6 * escala, h * 1.85 * escala)]
        tela.pintar(tela.corrente(pts, [h * 0.16 * escala, h * 0.12 * escala, h * 0.07 * escala, h * 0.02]), mat)


def capuz(tela, ctx, J, camada):
    """Capuz de pano com ponta caída para trás; o rosto fica à mostra na sombra."""
    C, h, w = medidas_da_cabeca(J)
    pano = tela.poly(C.pts([(-w * 1.0, -h * 1.05), (-w * 1.12, h * 0.4), (-w * 0.6, h * 0.92), (w * 0.25, h * 0.86),
                            (w * 0.78, h * 0.5), (w * 0.86, -h * 0.05), (w * 0.7, -h * 0.9)]))
    ponta = tela.poly(C.pts([(-w * 0.5, h * 0.8), (-w * 1.5, h * 0.5), (-w * 1.7, -h * 0.1), (-w * 0.9, h * 0.3)]))
    rosto = tela.poly(C.pts([(w * 0.0, -h * 0.55), (-w * 0.05, h * 0.45), (w * 0.5, h * 0.5), (w * 1.1, h * 0.1),
                             (w * 1.1, -h * 0.6)]))
    tela.pintar((pano | ponta) & ~rosto, NEUTRO_PANO)
    tela.traco(C.pt(-w * 0.02, h * 0.45), C.pt(w * 0.5, h * 0.5), NEUTRO_PANO[1], sobre=True)       # borda do capuz


def coroa(tela, ctx, J, camada):
    """Aro com pontas (coroa ou de espinhos, conforme a cor)."""
    C, h, w = medidas_da_cabeca(J)
    y = h * 0.5
    aro = tela.capsula(C.pt(-w * 0.75, y), C.pt(w * 0.72, y + h * 0.04), h * 0.11)
    for k in range(5):
        x = -w * 0.6 + k * w * 0.32
        aro |= tela.poly([C.pt(x - w * 0.1, y), C.pt(x + w * 0.1, y), C.pt(x, y + h * (0.45 if k % 2 == 0 else 0.3))])
    tela.pintar(aro, NEUTRO_METAL)
    gema(tela, C.pt(w * 0.1, y + h * 0.02), 0.8, 0.35)


def mascara(tela, ctx, J, camada):
    """Meia-máscara de porcelana sobre o rosto, com olhos vazados e um sorriso pintado."""
    C, h, w = medidas_da_cabeca(J)
    face = tela.poly(C.pts([(w * 0.02, h * 0.48), (w * 0.62, h * 0.42), (w * 0.72, -h * 0.05), (w * 0.58, -h * 0.52),
                            (w * 0.12, -h * 0.56), (-w * 0.05, h * 0.0)]))
    tela.pintar(face, Mat((214, 214, 214), 6, relevo=1.1, especular=(255, 255, 255)))
    for x in (w * 0.3, w * 0.56):
        tela.chapado(tela.elipse(*C.pt(x, h * 0.1), max(1.0, h * 0.07), max(0.8, h * 0.05)), (16, 10, 18))
    tela.tracos([C.pt(w * 0.2, -h * 0.25), C.pt(w * 0.42, -h * 0.36), C.pt(w * 0.62, -h * 0.24)], (40, 30, 40))


def veu(tela, ctx, J, camada):
    """Véu translúcido caindo da cabeça pelas costas."""
    C, h, w = medidas_da_cabeca(J)
    s = math.sin(ctx.a) * h * 0.08
    pano = tela.poly(C.pts([(-w * 0.7, h * 0.75), (w * 0.4, h * 0.85), (w * 0.2, h * 0.3), (-w * 0.6 + s, -h * 1.6),
                            (-w * 1.6 + s, -h * 2.2), (-w * 1.4, -h * 0.4)]))
    tela.vidro(pano, NEUTRO_PANO.claro(1), 0.55)
    tela.traco(C.pt(-w * 0.7, h * 0.75), C.pt(w * 0.4, h * 0.85), NEUTRO_PANO[5], sobre=True)


# ============================================================
# PEITORAL
# ============================================================

def _saia(tela, J, mat, comp=0.1):
    H = J["H"]
    Q = quadro_tronco(J)
    return tela.pintar(tela.poly(Q.pts([(-0.09 * H, 0.03 * H), (0.085 * H, 0.03 * H), (0.1 * H, -comp * H),
                                        (-0.1 * H, -comp * H)])), mat)


def _ombreira(tela, J, mat, tam=1.0):
    H = J["H"]
    o, u = J["ombro_f"], J["u"]
    ang = math.atan2(u[1], u[0]) + 1.4
    tela.pintar(tela.elipse_girada(o + u * 1.5, H * 0.07 * tam, H * 0.052 * tam, ang), mat)
    tela.traco(o + u * 1.5 - v2(H * 0.05 * tam, 0), o + u * 1.5 + v2(H * 0.05 * tam, 0), mat[1], sobre=True)


def placas(tela, ctx, J, camada):
    """Armadura pesada: peito de placas sobrepostas, saia de lâminas, gorjal e ombreira grande."""
    H = J["H"]
    Q = quadro_tronco(J)
    T_ = J["P"]["tronco"]
    _saia(tela, J, NEUTRO_METAL.escuro(1), 0.11)
    tronco(tela, J, NEUTRO_METAL, cintura=0.14, peito=0.21)
    for y in (0.24, 0.38, 0.52):
        tela.traco(Q.pt(-0.08 * H, T_ * y), Q.pt(0.085 * H, T_ * (y + 0.02)), NEUTRO_METAL[1], sobre=True)
    tela.traco(Q.pt(0.03 * H, T_ * 0.3), Q.pt(0.035 * H, T_ * 0.9), NEUTRO_METAL[6], sobre=True)
    tela.pintar(tela.capsula(J["pescoco"] - J["u"] * 1, J["pescoco"] + J["u"] * 2, H * 0.05), NEUTRO_METAL.escuro(1))
    sob_o_braco(tela, J)
    _ombreira(tela, J, NEUTRO_METAL)


def couraca(tela, ctx, J, camada):
    """Couraça média de escamas sobrepostas, com cinto de couro e ombreira pequena."""
    _saia(tela, J, NEUTRO_COURO.escuro(1), 0.08)
    m = tronco(tela, J, NEUTRO_METAL.copia(relevo=1.2), cintura=0.135, peito=0.2)
    T.escamas(tela, m, quadro_tronco(J).o, tam=2)
    cinto(tela, J, COURO_ESC, fivela=OURO_VELHO)
    sob_o_braco(tela, J)
    _ombreira(tela, J, NEUTRO_METAL, 0.8)


def tunica(tela, ctx, J, camada):
    """Gibão, casaco ou veste de pano: corpo, aba até a coxa, gola e cinto."""
    H = J["H"]
    Q = quadro_tronco(J)
    T_ = J["P"]["tronco"]
    _saia(tela, J, NEUTRO_PANO.escuro(1), 0.16)
    tronco(tela, J, NEUTRO_PANO, cintura=0.13, peito=0.19)
    tela.tracos([Q.pt(-0.03 * H, T_ * 1.0), Q.pt(0.02 * H, T_ * 0.72), Q.pt(0.06 * H, T_ * 1.0)], NEUTRO_PANO[0])
    for k in range(3):                                                         # botões
        tela.px(*Q.pt(0.025 * H, T_ * (0.2 + k * 0.17)), NEUTRO_PANO[5])
    cinto(tela, J, COURO_ESC, fivela=OURO_VELHO)
    sob_o_braco(tela, J)


def ossos(tela, ctx, J, camada):
    """Armadura de ossos: costelas amarradas sobre o peito e um crânio pequeno no ombro."""
    H = J["H"]
    Q = quadro_tronco(J)
    T_ = J["P"]["tronco"]
    tronco(tela, J, NEUTRO_COURO.escuro(3), cintura=0.13, peito=0.19)
    for k in range(4):                                                         # costelas
        y = T_ * (0.3 + k * 0.15)
        tela.pintar(tela.corrente([Q.pt(-0.08 * H, y - 1), Q.pt(0.0, y + 1.5), Q.pt(0.085 * H, y)], [1.2, 1.4, 1.0]), NEUTRO_PANO.claro(1))
    tela.pintar(tela.capsula(Q.pt(0.02 * H, T_ * 0.2), Q.pt(0.025 * H, T_ * 0.95), H * 0.016), NEUTRO_PANO.claro(1))   # esterno
    sob_o_braco(tela, J)
    o = J["ombro_f"] + J["u"] * 2
    tela.pintar(tela.circulo(o, H * 0.04), NEUTRO_PANO.claro(1))
    for dx in (-1.2, 1.2):
        tela.px(o[0] + dx, o[1], (20, 12, 16))


# ============================================================
# PERNAS
# ============================================================

def _trecho(J, lado, camada):
    """Do quadril (ou da barra da veste longa) até o tornozelo."""
    q, j, t = J["quadril_" + lado], J["joelho_" + lado], J["tornozelo_" + lado]
    barra = BARRA.get(camada.geometria, 0.0)
    if barra:
        return [lerp(j, t, barra), t]
    return [q, j, t]


def calcas(tela, ctx, J, camada):
    S = J["P"]
    for lado, mat in (("b", NEUTRO_PANO.escuro(1)), ("f", NEUTRO_PANO)):
        pts = _trecho(J, lado, camada)
        larg = [S["l_coxa"] * 1.12, S["l_canela"] * 1.15, S["l_canela"] * 0.85][-len(pts):]
        tela.pintar(tela.corrente(pts, larg), mat)
    sob_o_braco(tela, J)


def grevas(tela, ctx, J, camada):
    S = J["P"]
    for lado, k in (("b", 1), ("f", 0)):
        pts = _trecho(J, lado, camada)
        if len(pts) == 3:
            tela.pintar(tela.capsula(pts[0], pts[1], S["l_coxa"] * 1.1, S["l_canela"] * 1.1), NEUTRO_PANO.escuro(2 + k))
        j, t = J["joelho_" + lado], J["tornozelo_" + lado]
        inicio = pts[0] if len(pts) == 2 else j
        tela.pintar(tela.capsula(inicio, lerp(inicio, t, 0.85), S["l_canela"] * 1.25, S["l_canela"] * 0.95), NEUTRO_METAL.escuro(k))
        if len(pts) == 3:
            tela.pintar(tela.circulo(j, S["l_canela"] * 1.3), NEUTRO_METAL.escuro(k).claro(1))
    sob_o_braco(tela, J)


def botas(tela, ctx, J, camada):
    h = J["P"]["cabeca"]
    for lado, mat in (("b", NEUTRO_COURO.escuro(1)), ("f", NEUTRO_COURO)):
        tornoz, dedo, calc = J["tornozelo_" + lado], J["dedo_" + lado], J["calcanhar_" + lado]
        joelho = J["joelho_" + lado]
        cano = tornoz + (joelho - tornoz) * 0.45
        tela.pintar(tela.capsula(cano, tornoz, h * 0.2, h * 0.19), mat)
        tela.pintar(tela.poly([calc + v2(0, -h * 0.28), tornoz + v2(0, -h * 0.05), dedo + v2(h * 0.08, -h * 0.12),
                               dedo + v2(h * 0.08, h * 0.04), calc + v2(0, h * 0.04)]), mat)
        tela.traco(cano + v2(-h * 0.2, 0), cano + v2(h * 0.2, 0), COURO_ESC[1], sobre=True)                 # dobra do cano
        tela.traco(calc + v2(0, h * 0.04), dedo + v2(h * 0.08, h * 0.04), COURO_ESC[0], sobre=True)          # sola


# ============================================================
# CAPA E MANTO (atrás) + golas (na frente)
# ============================================================

def capa(tela, ctx, J, camada):
    """Capa nas costas, mais longa e aberta que as capas das roupas (aparece em volta delas)."""
    vento = 0.04 * math.sin(ctx.a) + (0.06 if ctx.golpe else 0)
    capa_nas_costas(tela, J, NEUTRO_PANO, comprimento=0.68, vento=vento, larg=0.23, rasgos=4, semente=5)


def manto(tela, ctx, J, camada):
    vento = 0.04 * math.sin(ctx.a) + (0.06 if ctx.golpe else 0)
    capa_nas_costas(tela, J, NEUTRO_PANO, comprimento=0.84, vento=vento, larg=0.28, rasgos=7, semente=7,
                    forro=NEUTRO_PANO.escuro(3))


def _gola(tela, J, larg, alta, pele=False):
    H = J["H"]
    u, pescoco = J["u"], J["pescoco"]
    f = v2(-u[1], u[0])
    gola = tela.poly([J["ombro_f"] - f * 1 + u * 1, pescoco + u * H * alta - f * 2, pescoco + u * H * (alta + 0.02) + f * 2,
                      J["ombro_b"] + f * 2 + u * 1, J["ombro_b"] - u * H * larg, J["ombro_f"] - u * H * larg])
    m = tela.pintar(gola, NEUTRO_PANO.claro(1) if pele else NEUTRO_PANO)
    if pele:
        T.tufos(tela, m, pescoco, (0, -1), comp=2, espaco=2)
        T.pelagem(tela, m, pescoco, ang=math.pi / 2, comp=2, densidade=0.4)
    sob_o_braco(tela, J)
    tela.pintar(tela.circulo(J["ombro_f"] + u * 0.5, max(1.0, H * 0.022)), OURO_VELHO)                        # broche


def capa_gola(tela, ctx, J, camada):
    _gola(tela, J, 0.035, -0.045)


def manto_gola(tela, ctx, J, camada):
    _gola(tela, J, 0.05, -0.03, pele=True)


# ============================================================
# AMULETOS
# ============================================================

def colar(tela, ctx, J, camada):
    """Cordão no pescoço com um pingente que brilha na cor da peça."""
    H = J["H"]
    Q = quadro_tronco(J)
    T_ = J["P"]["tronco"]
    pingente = Q.pt(0.03 * H, T_ * 0.62)
    tela.tracos([J["ombro_b"] - J["u"] * 1, pingente, J["ombro_f"] - J["u"] * 1 + v2(-1, 0)], CORDA)
    tela.pintar(tela.poly([pingente + v2(-2, -1), pingente + v2(2, -1), pingente + v2(0, 3)]), NEUTRO_METAL)
    gema(tela, pingente + v2(0, 0.5), 0.7, 0.4)
    sob_o_braco(tela, J)


def rato_no_ombro(tela, ctx, J, camada):
    """Um ratinho sentado no ombro da frente (o Rato de Estimação, etapa 7A): o pelo se tinge na cor da peça; o olho, a
    orelha, o focinho e o rabo têm cor própria. Mexe o focinho no parado."""
    H = J["H"]
    u = J["u"]
    f = v2(-u[1], u[0])                                                    # para a frente do herói
    base = J["ombro_f"] - f * (H * 0.05) + u * (H * 0.03)                 # sentado no ombro, por fora do corpo
    s = math.sin(ctx.a * 2)

    def p(x, y):                                                           # virado para trás (não cobre o rosto)
        return base + v2(-x, y)
    corpo = tela.elipse(base[0], base[1], H * 0.052, H * 0.034)
    cabeca = tela.poly([p(H * 0.02, -H * 0.042), p(H * 0.094, -H * 0.014 + s * 0.4), p(H * 0.045, H * 0.014)])
    tela.pintar(corpo | cabeca, NEUTRO_PANO)
    tela.pintar(tela.circulo(p(H * 0.03, -H * 0.048), H * 0.017), NEUTRO_PANO)                     # a orelha
    rabo = [p(-H * 0.045, H * 0.012), p(-H * 0.07, H * 0.045), p(-H * 0.055, H * 0.085 + s * 0.6)]
    tela.tracos(rabo, (206, 146, 146))
    tela.px(*p(H * 0.03, -H * 0.048), (214, 150, 158))                                    # dentro da orelha
    tela.px(*p(H * 0.058, -H * 0.022), (230, 40, 40), emite=True)                          # o olho
    tela.px(*p(H * 0.095, -H * 0.014 + s * 0.4), (236, 160, 170))                          # o focinho


def anel(tela, ctx, J, camada):
    """Anel na mão da frente: um aro e um brilho na cor da peça."""
    m = J["mao_f"]
    tela.chapado(tela.circulo(m + v2(0.5, 0), 1.1) & ~tela.circulo(m + v2(0.5, 0), 0.4), NEUTRO_METAL[5])
    tela.brilho(m, 4, NEUTRO_LUZ, 0.45 + 0.1 * math.sin(ctx.a * 2))


def estandarte(tela, ctx, J, camada):
    """Estandarte preso às costas (como o sashimono): haste acima da cabeça, travessa e uma bandeira
    comprida de cauda partida, com um sol bordado, tremulando para trás."""
    H = J["H"]
    u = J["u"]
    base = J["ombro_b"] - u * H * 0.3
    topo = J["topo"] + u * H * 0.42 - v2(H * 0.1, 0)
    tela.pintar(tela.capsula(base, topo, 0.9), MADEIRA)
    travessa = topo - u * H * 0.03
    tela.pintar(tela.capsula(travessa, travessa - v2(H * 0.24, 0), 0.7), MADEIRA)
    tela.pintar(tela.circulo(topo + u * 1.5, 1.4), OURO_VELHO)                       # ponteira
    s = math.sin(ctx.a)
    a, b = travessa - v2(H * 0.01, 0), travessa - v2(H * 0.23, 0)
    fundo_a = a - u * H * 0.32 + v2(s * 1.5, 0)
    fundo_b = b - u * H * 0.32 + v2(s * 2.5, 0)
    pano = [a, b, fundo_b, lerp(fundo_a, fundo_b, 0.5) + u * H * 0.07, fundo_a]
    m = tela.pintar(tela.poly(pano), NEUTRO_PANO)
    tela.pintar(tela.poly([a, b, b - u * H * 0.04, a - u * H * 0.04]) & m, NEUTRO_PANO.escuro(2), linha_interna=False)
    centro = lerp(lerp(a, b, 0.5), lerp(fundo_a, fundo_b, 0.5), 0.45)
    for k in range(8):                                                            # sol bordado em ouro
        tela.traco(centro, centro + dir_ang(k * math.pi / 4) * 3.2, OURO_VELHO[4], sobre=True)
    tela.pintar(tela.circulo(centro, 1.6), OURO_VELHO)


def lanterna_cinto(tela, ctx, J, camada):
    """Lanterna pendurada no cinto, com a chama acesa."""
    H = J["H"]
    p = quadro_tronco(J).pt(0.08 * H, -0.02 * H) + v2(0, 3)
    tela.traco(p - v2(0, 4), p, CORDA)
    caixa = tela.poly([p + v2(-2.5, 0), p + v2(2.5, 0), p + v2(2, 6), p + v2(-2, 6)])
    tela.pintar(caixa, NEUTRO_METAL.escuro(1))
    tela.chapado(tela.poly([p + v2(-1.2, 1.2), p + v2(1.2, 1.2), p + v2(1, 5), p + v2(-1, 5)]), CHAMA, emite=True)
    tela.brilho(p + v2(0, 3), 9, CHAMA, 0.45 + 0.1 * math.sin(ctx.a * 2), halo=True)


# ============================================================
# ARMAS (mão principal)
# ============================================================

def arma(desenho, dedos=True):
    """Desenha a arma na mão principal da geometria e deixa os dedos do herói por cima do cabo."""
    def desenhar(tela, ctx, J, camada):
        lado, _ = maos(J, camada)
        mao, ang = empunhar(J, lado)
        desenho(tela, ctx, J, mao, ang, camada.modelo.H)
        if dedos:
            dedos_por_cima(tela, J, lado)
    return desenhar


def _espada(tela, ctx, J, mao, ang, H):
    armas.espada(tela, mao, ang, H * 0.5, NEUTRO_METAL.claro(1), NEUTRO_METAL, COURO_ESC, larg=1.6, pomo=NEUTRO_METAL)


def _espada_curva(tela, ctx, J, mao, ang, H):
    armas.espada(tela, mao, ang, H * 0.5, NEUTRO_METAL.claro(1), NEUTRO_METAL, COURO_ESC, larg=1.9, pomo=NEUTRO_METAL,
                 curva=2.2, guarda_larg=3.5)
    gema(tela, mao + dir_ang(ang) * 2.2, 0.6, 0.3)


def _adaga(tela, ctx, J, mao, ang, H):
    armas.adaga(tela, mao, ang, 12, NEUTRO_METAL.claro(1), COURO_ESC)


def _adagas(tela, ctx, J, mao, ang, H):
    armas.adaga(tela, mao, ang, 12, NEUTRO_METAL.claro(1), COURO_ESC)
    outra = "b" if mao is J["mao_f"] else "f"
    m2, a2 = empunhar(J, outra)
    armas.adaga(tela, m2, a2, 11, NEUTRO_METAL, COURO_ESC)


def _machado(tela, ctx, J, mao, ang, H):
    armas.machado(tela, mao, ang, H * 0.5, MADEIRA, NEUTRO_METAL, duplo=True, tam=1.3)


def _martelo(tela, ctx, J, mao, ang, H):
    armas.martelo(tela, mao, ang, H * 0.45, MADEIRA, NEUTRO_METAL, tam=1.0)


def _maca(tela, ctx, J, mao, ang, H):
    armas.maca(tela, mao, ang, H * 0.4, MADEIRA, NEUTRO_METAL, raio=3.6)


def _mangual(tela, ctx, J, mao, ang, H):
    armas.mangual(tela, mao, ang, MADEIRA, NEUTRO_METAL.escuro(1), NEUTRO_METAL, oscila=0.5 * math.sin(ctx.a) - 0.4)


def _chicote(tela, ctx, J, mao, ang, H):
    d = dir_ang(ang)
    tela.pintar(tela.capsula(mao - d * 3, mao + d * 3, 1.0), COURO_ESC)
    pts = [mao + d * 3]
    a = ang
    for k in range(7):                                                            # tira de couro em onda
        a += 0.35 * math.sin(ctx.a + k * 0.9) + (0.25 if ctx.anim != "ataque" else -0.05)
        pts.append(pts[-1] + dir_ang(a) * H * 0.07)
    tela.pintar(tela.corrente(pts, [1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]), NEUTRO_COURO)
    for p in pts[2::2]:                                                           # pregos
        tela.px(p[0], p[1] - 1, NEUTRO_METAL[6])


def _foice(tela, ctx, J, mao, ang, H):
    armas.foice(tela, mao, ang, H * 0.55, MADEIRA, NEUTRO_METAL, tam=1.05)


def _cajado(tela, ctx, J, mao, ang, H):
    topo = armas.cajado(tela, mao, ang, H * 0.4, NEUTRO_MADEIRA, atras=H * 0.45, torto=1.0)
    d = dir_ang(ang)
    n = v2(-d[1], d[0])
    for s in (-1, 1):                                                             # garras segurando a gema
        tela.pintar(tela.corrente([topo, topo + n * s * 2.5 + d * 2, topo + n * s * 1.5 + d * 5], [1.0, 0.8, 0.5]),
                    NEUTRO_MADEIRA.claro(1))
    gema(tela, topo + d * 3, 1.8, 0.55 + 0.15 * math.sin(ctx.a * 2))


def _cetro(tela, ctx, J, mao, ang, H):
    d = dir_ang(ang)
    topo = mao + d * H * 0.32
    tela.pintar(tela.capsula(mao - d * 4, topo, 1.0), NEUTRO_METAL)
    tela.pintar(tela.circulo(topo + d * 2, 2.6), NEUTRO_METAL.claro(1))
    for k in range(3):                                                            # coroa do cetro
        a = ang + (k - 1) * 0.7
        tela.pintar(tela.poly([topo + d * 2 + dir_ang(a + 0.3) * 2, topo + d * 2 + dir_ang(a - 0.3) * 2,
                               topo + d * 2 + dir_ang(a) * 5]), NEUTRO_METAL)
    gema(tela, topo + d * 2, 1.2, 0.5)


def _arco(tela, ctx, J, mao, ang, H):
    if mao is J["mao_b"]:                                                         # a patrulheira: mira com a mão de trás
        d = dir_ang(math.pi / 2 + J["arma_b"])
        puxa = 0.0
        if ctx.anim == "ataque" and ctx.i in (0, 1):
            puxa = max(0.0, float((mao - J["mao_f"]) @ d) - 3)
        flecha = (150, 120, 90) if ctx.anim == "ataque" and ctx.i in (0, 1) else None
        extra = 0.35 if ctx.anim == "parado" else 0.0
        armas.arco_flecha(tela, mao, math.pi / 2 + J["arma_b"] + extra, H * 0.62, NEUTRO_MADEIRA, (200, 186, 160),
                          puxa=puxa, flecha=flecha, ponta=COURO_ESC)
    else:                                                                         # os outros seguram em pé, apontado para a frente
        armas.arco_flecha(tela, mao, math.pi / 2, H * 0.58, NEUTRO_MADEIRA, (200, 186, 160))


def _alaude(tela, ctx, J, mao, ang, H):
    """Alaúde preso ao peito (como o do bardo)."""
    Q = quadro_tronco(J)
    T_ = J["P"]["tronco"]
    corpo = Q.pt(0.05 * H, T_ * 0.32)
    d = dir_ang(J["giro"] + 0.85)
    tela.pintar(tela.capsula(corpo, corpo + d * H * 0.36, 1.6, 1.2), MADEIRA)
    tela.pintar(tela.elipse_girada(corpo, H * 0.11, H * 0.085, math.atan2(d[1], d[0])), NEUTRO_MADEIRA)
    tela.pintar(tela.circulo(corpo + d * H * 0.03, H * 0.025), Mat((30, 18, 14), 4))
    topo = corpo + d * H * 0.38
    tela.pintar(tela.poly([topo, topo + v2(3, -2), topo + v2(4, 1)]), MADEIRA.escuro(1))
    for k in (-1, 0, 1):
        tela.traco(corpo - d * 2 + v2(0, k * 0.6), topo, (210, 200, 170), sobre=True)


def _pa(tela, ctx, J, mao, ang, H):
    d = dir_ang(ang)
    n = v2(-d[1], d[0])
    _, topo = armas.haste(tela, mao, ang, 6, H * 0.42, MADEIRA, 1.0)
    lamina = [topo - n * 4.2, topo + n * 4.2, topo + n * 4 + d * 8, topo + d * 11, topo - n * 4 + d * 8]
    tela.pintar(tela.poly(lamina), NEUTRO_METAL.claro(1))
    tela.traco(topo + d * 1, topo + d * 9, NEUTRO_METAL[2], sobre=True)
    tela.pintar(tela.capsula(topo - d * 1, topo + d * 1.5, 1.6), NEUTRO_METAL.escuro(1))        # alvado


def _picareta(tela, ctx, J, mao, ang, H, comp=0.42):
    d = dir_ang(ang)
    n = v2(-d[1], d[0])
    _, topo = armas.haste(tela, mao, ang, 3, H * comp, MADEIRA, 1.0)
    cabeca = [topo + n * 9 - d * 3, topo + n * 2 + d * 1.5, topo - n * 2 + d * 1.5, topo - n * 7 + d * 1, topo - n * 2 - d * 1.5,
              topo + n * 2 - d * 1.5]
    tela.pintar(tela.poly(cabeca), NEUTRO_METAL)


# ============================================================
# MÃO SECUNDÁRIA
# ============================================================

def secundaria(desenho, dedos=True):
    def desenhar(tela, ctx, J, camada):
        _, lado = maos(J, camada)
        mao, ang = empunhar(J, lado)
        desenho(tela, ctx, J, mao, ang, camada.modelo.H)
        if dedos:
            dedos_por_cima(tela, J, lado)
    return desenhar


def _escudo(tela, ctx, J, mao, ang, H):
    _, c = armas.escudo(tela, mao + v2(1, 3), NEUTRO_PANO.escuro(1), NEUTRO_METAL, larg=9, alt=14, ang=0.15 + J["giro"])
    tela.pintar(tela.circulo(c, 1.6), NEUTRO_METAL.claro(1))                       # umbo


def _broquel(tela, ctx, J, mao, ang, H):
    armas.escudo(tela, mao + v2(0, 1), NEUTRO_METAL.escuro(1), NEUTRO_METAL, larg=5.5, alt=5.5, forma="redondo")
    tela.pintar(tela.circulo(mao + v2(0, 1), 1.5), NEUTRO_METAL.claro(1))


def _lanterna(tela, ctx, J, mao, ang, H):
    p = mao + v2(0, 4)
    tela.traco(mao, p, CORDA)
    tela.pintar(tela.poly([p + v2(-3, 0), p + v2(3, 0), p + v2(2.5, 8), p + v2(-2.5, 8)]), NEUTRO_METAL.escuro(1))
    tela.chapado(tela.poly([p + v2(-1.5, 1.5), p + v2(1.5, 1.5), p + v2(1.2, 6.5), p + v2(-1.2, 6.5)]), CHAMA, emite=True)
    tela.brilho(p + v2(0, 4), 12, CHAMA, 0.5 + 0.1 * math.sin(ctx.a * 2))


def _grimorio(tela, ctx, J, mao, ang, H):
    c = mao + v2(1, 1)
    capa_ = tela.poly([c + v2(-4, -5), c + v2(4, -4), c + v2(4, 5), c + v2(-4, 4)])
    tela.pintar(capa_, NEUTRO_COURO.escuro(1))
    tela.chapado(tela.poly([c + v2(3, -3.5), c + v2(4.6, -3.2), c + v2(4.6, 4.2), c + v2(3, 4)]), (220, 208, 180))   # páginas
    gema(tela, c + v2(-0.5, 0), 1.0, 0.45 + 0.15 * math.sin(ctx.a * 2))


def _adaga_b(tela, ctx, J, mao, ang, H):
    armas.adaga(tela, mao, ang, 11, NEUTRO_METAL, COURO_ESC)


def _picareta_b(tela, ctx, J, mao, ang, H):
    _picareta(tela, ctx, J, mao, ang, H, comp=0.32)


# ============================================================
# ETAPA 8: TIPOS NOVOS (chapéus, asas, contas, armas e mão secundária)
# ============================================================

def chapeu(tela, ctx, J, camada, pontudo=False):
    """Chapéu de aba larga (ou pontudo de bruxa, com a ponta caída para trás)."""
    C, h, w = medidas_da_cabeca(J)
    s = math.sin(ctx.a)
    ang_aba = math.atan2(J["hu"][0], -J["hu"][1])
    aba = tela.elipse_girada(C.pt(w * 0.05, h * 0.45), w * 1.45, h * 0.2, ang_aba)
    if pontudo:
        copa = tela.poly(C.pts([(-w * 0.55, h * 0.45), (w * 0.55, h * 0.45), (w * 0.12, h * 1.25), (-w * 0.35 + s * 0.5, h * 1.85),
                                (-w * 1.0 + s, h * 1.7), (-w * 0.35, h * 1.1)]))
    else:
        copa = tela.poly(C.pts([(-w * 0.55, h * 0.42), (-w * 0.45, h * 1.05), (w * 0.4, h * 1.0), (w * 0.55, h * 0.42)]))
    tela.pintar(aba | copa, NEUTRO_PANO.escuro(1))
    tela.traco(C.pt(-w * 0.52, h * 0.56), C.pt(w * 0.55, h * 0.56), COURO_ESC[1], sobre=True)     # fita
    tela.pintar(tela.circulo(C.pt(w * 0.15, h * 0.56), max(0.8, h * 0.08)), OURO_VELHO)             # fivela


def asas(tela, ctx, J, camada):
    """Par de asas de penas nas costas (atrás do herói)."""
    from .adornos import asas as asas_de_adorno
    asas_de_adorno("penas", cor=(220, 220, 220))(tela, ctx, J, camada.modelo)


def contas(tela, ctx, J, camada):
    """Rosário de contas grandes no pescoço, com borla."""
    from .adornos import contas_grandes
    contas_grandes(cor=(214, 214, 214), borla=(150, 40, 40))(tela, ctx, J, camada.modelo)
    sob_o_braco(tela, J)


def _lanca(tela, ctx, J, mao, ang, H):
    armas.lanca(tela, mao, ang, H * 0.55, MADEIRA, NEUTRO_METAL.claro(1), atras=H * 0.3, larg_ponta=2.4)


def _tridente(tela, ctx, J, mao, ang, H):
    d = dir_ang(ang)
    n = v2(-d[1], d[0])
    _, topo = armas.haste(tela, mao, ang, H * 0.28, H * 0.5, MADEIRA, 0.9)
    dentes = tela.capsula(topo - n * 3.5, topo + n * 3.5, 0.8)
    for k in (-3.5, 0, 3.5):
        p = topo + n * k
        comp = 6.5 if k == 0 else 5
        dentes |= tela.capsula(p, p + d * comp, 0.7)
        dentes |= tela.poly([p + d * comp - n * 1.2, p + d * comp + n * 1.2, p + d * (comp + 2.5)])
    tela.pintar(dentes, NEUTRO_METAL)


def _rapieira(tela, ctx, J, mao, ang, H):
    armas.espada(tela, mao, ang, H * 0.52, NEUTRO_METAL.claro(1), NEUTRO_METAL, COURO_ESC, larg=0.8, ponta=0.1,
                 guarda_larg=2.4, pomo=NEUTRO_METAL)
    tela.pintar(tela.circulo(v2(mao) + dir_ang(ang) * 2.2, 1.8) & ~tela.circulo(v2(mao), 0.9), NEUTRO_METAL)   # taça


def _montante(tela, ctx, J, mao, ang, H):
    armas.espada(tela, mao, ang, H * 0.68, NEUTRO_METAL.claro(1), NEUTRO_METAL, COURO_ESC, larg=2.3, guarda_larg=6,
                 pomo=NEUTRO_METAL)


def _besta(tela, ctx, J, mao, ang, H):
    """Besta apontada para a frente: coronha de madeira, arco de metal e o virote armado."""
    a = math.pi / 2 - 0.12 + J["giro"]
    d = dir_ang(a)
    n = v2(-d[1], d[0])
    tela.pintar(tela.capsula(mao - d * 5, mao + d * H * 0.22, 1.4, 1.0), MADEIRA)
    frente = mao + d * H * 0.18
    arco = [frente - n * 8 - d * 3, frente - n * 3.5, frente, frente + n * 3.5, frente + n * 8 - d * 3]
    tela.pintar(tela.corrente(arco, [0.7, 1.1, 1.3, 1.1, 0.7]), NEUTRO_METAL)
    tela.tracos([arco[0], mao + d * 2, arco[-1]], (200, 186, 160))
    if not (ctx.anim == "ataque" and ctx.i == 2):
        tela.traco(mao + d * 2, frente + d * 3, (150, 120, 90))


def _varinha(tela, ctx, J, mao, ang, H):
    topo = armas.cajado(tela, mao, ang, H * 0.22, NEUTRO_MADEIRA, atras=H * 0.04, torto=0.6)
    gema(tela, topo + dir_ang(ang) * 1.2, 1.1, 0.5 + 0.15 * math.sin(ctx.a * 2))


def _garra_na_mao(tela, J, lado, H):
    c, m = J["cotovelo_" + lado], J["mao_" + lado]
    d = (m - c) / max(1e-6, float(np.hypot(*(m - c))))
    n = v2(-d[1], d[0])
    tela.pintar(tela.capsula(lerp(c, m, 0.35), m - d * 0.5, H * 0.03, H * 0.028), NEUTRO_METAL.escuro(1))     # braçal
    lam = np.zeros((tela.h, tela.w), bool)
    for k in (-1, 0, 1):
        base = m + n * k * 1.3
        lam |= tela.poly([base - n * 0.6, base + n * 0.6, base + d * (6.5 - abs(k)) + n * k * 1.2])
    tela.pintar(lam, NEUTRO_METAL.claro(1))


def _garras(tela, ctx, J, mao, ang, H):
    for lado in ("b", "f"):
        _garra_na_mao(tela, J, lado, H)


def _cutelo(tela, ctx, J, mao, ang, H):
    d = dir_ang(ang)
    n = v2(-d[1], d[0])
    tela.pintar(tela.capsula(mao - d * 3, mao + d * 3, 1.1), MADEIRA)
    b = mao + d * 3
    lam = tela.poly([b - n * 1, b + d * H * 0.26 - n * 1, b + d * H * 0.27 + n * 7, b + d * 1.5 + n * 7.5])
    tela.pintar(lam, NEUTRO_METAL)
    tela.traco(b + n * 7.2 + d * 2, b + d * H * 0.26 + n * 6.6, NEUTRO_METAL[6], sobre=True)
    tela.chapado(tela.circulo(b + d * H * 0.2 + n * 2, 0.9) & lam, (20, 14, 18))


def _escudo_torre(tela, ctx, J, mao, ang, H):
    _, c = armas.escudo(tela, mao + v2(1, 4), NEUTRO_PANO.escuro(1), NEUTRO_METAL, larg=8, alt=16, ang=0.1 + J["giro"],
                        forma="torre")
    for k in (-6, 0, 6):                                                          # rebites
        tela.px(*(c + v2(0, k)), NEUTRO_METAL[6])


def _orbe(tela, ctx, J, mao, ang, H):
    """Orbe flutuando acima da mão secundária, com um anel girando."""
    c = mao + v2(2, -7 + 1.2 * math.sin(ctx.a))
    tela.pintar(tela.circulo(c, 3.4), Mat((214, 214, 214), 6, relevo=1.5, especular=(255, 255, 255)))
    gema(tela, c + v2(-0.8, -0.8), 1.2, 0.6)
    anel = tela.elipse_girada(c, 5.2, 1.6, 0.25 * math.sin(ctx.a)) & ~tela.elipse_girada(c, 4.2, 0.8, 0.25 * math.sin(ctx.a))
    tela.chapado(anel & (tela.alfa == 0), NEUTRO_LUZ, emite=True)


def _turibulo(tela, ctx, J, mao, ang, H):
    """Turíbulo balançando na corrente, soltando fumaça."""
    osc = math.sin(ctx.a) * 0.4 + (0.7 if ctx.golpe else 0)
    fim = mao + v2(math.sin(osc), math.cos(osc)) * H * 0.17
    tela.tracos([mao, lerp(mao, fim, 0.5) + v2(0.5, 0), fim], (120, 104, 70))
    corpo = tela.circulo(fim + v2(0, 2.5), 2.8) | tela.poly([fim + v2(-2, 0), fim + v2(2, 0), fim + v2(0, -2.5)])
    tela.pintar(corpo, NEUTRO_METAL)
    tela.px(fim[0], fim[1] + 3, CHAMA, emite=True)
    from .. import fx
    fx.fumaca(tela, fim + v2(0, -2), 2.0, cor=(96, 90, 104), fase=ctx.a, n=3, sobe=12)


# ============================================================
# REGISTRO
# ============================================================

PECAS = {
    # cabeça
    "eq_elmo": elmo, "eq_elmo_chifrudo": elmo_chifrudo, "eq_capuz": capuz, "eq_coroa": coroa, "eq_mascara": mascara,
    "eq_veu": veu,
    # tronco e pernas
    "eq_placas": placas, "eq_couraca": couraca, "eq_tunica": tunica, "eq_ossos": ossos,
    "eq_calcas": calcas, "eq_grevas": grevas, "eq_botas": botas,
    # capa e amuletos
    "eq_capa": capa, "eq_capa_gola": capa_gola, "eq_manto": manto, "eq_manto_gola": manto_gola,
    "eq_colar": colar, "eq_anel": anel, "eq_estandarte": estandarte, "eq_lanterna_cinto": lanterna_cinto,
    # armas
    "eq_espada": arma(_espada), "eq_espada_curva": arma(_espada_curva), "eq_adaga": arma(_adaga), "eq_adagas": arma(_adagas),
    "eq_machado": arma(_machado), "eq_martelo": arma(_martelo), "eq_maca": arma(_maca), "eq_mangual": arma(_mangual),
    "eq_chicote": arma(_chicote), "eq_foice": arma(_foice), "eq_cajado": arma(_cajado), "eq_cetro": arma(_cetro),
    "eq_arco": arma(_arco), "eq_alaude": arma(_alaude, dedos=False), "eq_pa": arma(_pa), "eq_picareta": arma(_picareta),
    # mão secundária
    "eq_escudo": secundaria(_escudo), "eq_broquel": secundaria(_broquel), "eq_lanterna": secundaria(_lanterna, dedos=False),
    "eq_grimorio": secundaria(_grimorio), "eq_adaga_b": secundaria(_adaga_b), "eq_picareta_b": secundaria(_picareta_b),
    # etapa 8
    "eq_chapeu": chapeu, "eq_chapeu_pontudo": lambda tela, ctx, J, camada: chapeu(tela, ctx, J, camada, pontudo=True),
    "eq_asas": asas, "eq_contas": contas,
    "eq_lanca": arma(_lanca), "eq_tridente": arma(_tridente), "eq_rapieira": arma(_rapieira), "eq_montante": arma(_montante),
    "eq_besta": arma(_besta), "eq_varinha": arma(_varinha), "eq_garras": arma(_garras, dedos=False), "eq_cutelo": arma(_cutelo),
    "eq_escudo_torre": secundaria(_escudo_torre), "eq_orbe": secundaria(_orbe, dedos=False),
    "eq_turibulo": secundaria(_turibulo, dedos=False),
    # Reino dos Ratos (etapa 7A)
    "eq_rato_no_ombro": rato_no_ombro,
}

ATRAS = {"eq_capa", "eq_manto", "eq_estandarte", "eq_asas"}
