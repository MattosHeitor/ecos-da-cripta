"""Camadas cosméticas que se sobrepõem aos heróis (skins de chapéu e de arma).

Uma CamadaVisual usa o MESMO modelo do herói (mesmo esqueleto, mesmas poses, mesma célula e
âncora), mas desenha só o acessório. Por isso encaixa quadro a quadro em cima de qualquer roupa
daquele herói.

    camada_<geometria>_<acessorio>.png      ex.: camada_guerreiro_aureola.png

Para criar um acessório novo: escreva uma função desenhar(tela, ctx, J, camada) e ponha em
ACESSORIOS. A "geometria" diz de qual modelo vem o esqueleto (ver GEOMETRIAS).
"""
import math

from ..anim import Modelo
from ..humanoide import quadro_cabeca
from ..motor import Mat, metal, v2, dir_ang
from .. import fx
from . import herois as H
from . import acampamento as C
from . import herois_novos as N
from . import herois_do_reino as R
from .herois import OSSO
from .equipamento import PECAS, FIXO, separar_tinta

# geometria -> (fábrica do modelo, quanto o topo da cabeça sobe por causa do chapéu, mão da arma, tamanho da arma em H)
GEOMETRIAS = {
    "guerreiro": (lambda: H.Guerreiro(), 0.3, "f", 0.5),
    "paladino": (lambda: H.Paladino(), 0.45, "f", 0.42),
    "barbaro_Machado": (lambda: H.Barbaro(arma="Machado"), 0.1, "f", 0.5),
    "barbaro_Espada": (lambda: H.Barbaro(arma="Espada"), 0.1, "f", 0.5),
    "barbaro_Martelo": (lambda: H.Barbaro(arma="Martelo"), 0.1, "f", 0.5),
    "mago": (lambda: H.MagoFogo(), 0.65, "f", 0.55),
    "arqueira": (lambda: H.Arqueira(), 0.45, "b", 0.32),
    "assassina": (lambda: H.Assassina(), 0.45, "f", 0.17),
    "bardo": (lambda: C.Bardo(), 0.8, "f", 0.32),
    "bobo": (lambda: C.BoboDaCorte(), 1.15, "f", 0.17),
    "monge": (lambda: N.Monge(), 0.0, "f", 0.1),
    "feiticeira": (lambda: N.Feiticeira(), 1.5, "f", 0.3),
    "medico_da_peste": (lambda: R.MedicoDaPeste(), 0.75, "f", 0.42),
    "senhor_dos_ratos": (lambda: R.SenhorDosRatos(), 0.35, "f", 0.34),
}


# ============================================================
# ADORNOS DE CABEÇA (skins de "chapéu")
# ============================================================

def acima_da_cabeca(J, camada, quanto=1.0):
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    return C, h, C.pt(0, h * (quanto + camada.topo_extra))


def aureola(tela, ctx, J, camada):
    _, h, c = acima_da_cabeca(J, camada, 1.05)
    anel = tela.elipse(c[0], c[1], h * 0.8, h * 0.24) & ~tela.elipse(c[0], c[1] + 0.4, h * 0.52, h * 0.1)
    tela.chapado(anel, (255, 226, 140), emite=True)
    tela.brilho(c, h * 1.3, (255, 214, 120), 0.55 + 0.1 * math.sin(ctx.a))


def chifres_de_osso(tela, ctx, J, camada):
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.85
    topo = 0.35 + camada.topo_extra * 0.6
    for lado in (-1, 1):
        pts = [C.pt(lado * w * 0.35, h * topo), C.pt(lado * w * 0.85, h * (topo + 0.35)),
               C.pt(lado * w * 0.95, h * (topo + 0.85)), C.pt(lado * w * 0.65, h * (topo + 1.15))]
        tela.pintar(tela.corrente(pts, [h * 0.2, h * 0.16, h * 0.1, h * 0.03]), OSSO)


def coroa_partida(tela, ctx, J, camada):
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.8
    y = 0.55 + camada.topo_extra
    pontas = [(-w * 0.5, h * y), (-w * 0.5, h * (y + 0.45)), (-w * 0.25, h * (y + 0.25)), (0, h * (y + 0.55)),
              (w * 0.2, h * (y + 0.2)), (w * 0.5, h * (y + 0.42)), (w * 0.5, h * y)]
    tela.pintar(tela.poly(C.pts(pontas)), metal((200, 160, 70)))
    tela.traco(C.pt(w * 0.05, h * (y + 0.05)), C.pt(-w * 0.1, h * (y + 0.4)), (40, 24, 20), sobre=True)   # rachadura
    tela.chapado(tela.circulo(C.pt(0, h * (y + 0.18)), 1.0), (220, 40, 60), emite=True)


def chama_fantasma(tela, ctx, J, camada):
    _, h, c = acima_da_cabeca(J, camada, 1.0)
    fx.chama(tela, c + v2(0, 2), h * 1.1 + 2 * math.sin(ctx.a * 2), h * 0.7, fx.FOGO_AZUL, fase=ctx.a * 2)
    tela.brilho(c, h * 1.1, (120, 190, 255), 0.5)


def coroa_de_espinhos(tela, ctx, J, camada):
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.85
    y = 0.42 + camada.topo_extra
    galho = Mat((96, 70, 44), 5, ruido=0.3)
    tela.pintar(tela.capsula(C.pt(-w * 0.55, h * y), C.pt(w * 0.55, h * (y + 0.05)), h * 0.09), galho)
    for k in range(6):
        x = -w * 0.5 + k * w * 0.2
        tela.traco(C.pt(x, h * (y + 0.05)), C.pt(x + w * 0.05, h * (y + 0.3)), galho[3], sobre=True)
    tela.px(*C.pt(w * 0.1, h * (y - 0.1)), (170, 20, 30))                        # gota de sangue


def mascara_de_bico(couro=(50, 40, 36), especular=(140, 120, 100), lentes=(200, 160, 70), chapeu=(30, 26, 30), aba=1.0,
                    brilho=False):
    """Máscara de bico com chapéu de couro. Padrão = a Máscara da Peste da Taverna; a do Doutor (Reino dos Ratos) é preta,
    de lentes verdes acesas e aba larga."""
    def desenhar(tela, ctx, J, camada):
        C, h, w = medidas_da_cabeca(J)
        couro_ = Mat(couro, 5, relevo=1.0, especular=especular)
        tela.pintar(tela.poly(C.pts([(w * 0.1, h * 0.3), (w * 0.55, h * 0.2), (w * 1.35, -h * 0.25), (w * 0.5, -h * 0.35),
                                     (w * 0.1, -h * 0.3)])), couro_)
        for x in (w * 0.3, w * 0.52):                                         # lentes de vidro
            tela.chapado(tela.circulo(C.pt(x, h * 0.08), max(1.0, h * 0.09)), lentes, emite=True)
        tela.pintar(tela.poly(C.pts([(-w * 0.55 * aba, h * 0.45), (w * 0.55 * aba, h * 0.5), (w * 0.4, h * 0.85),
                                     (-w * 0.4, h * 0.85)])), Mat(chapeu, 5))  # chapéu de couro
        if brilho:
            tela.brilho(C.pt(w * 0.41, h * 0.08), h * 0.5, lentes, 0.45 + 0.1 * math.sin(ctx.a * 2))
    return desenhar


def chapeu_pontudo(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    y = h * (0.36 + camada.topo_extra * 0.5)
    s = math.sin(ctx.a) * h * 0.06
    pano_ = Mat((40, 30, 56), 6, relevo=0.9)
    aba = tela.elipse_girada(C.pt(w * 0.05, y), w * 1.2, h * 0.15, math.atan2(J["hu"][0], -J["hu"][1]))
    cone = tela.poly(C.pts([(-w * 0.5, y), (w * 0.5, y), (w * 0.1, y + h * 0.8), (-w * 0.3 + s, y + h * 1.4),
                            (-w * 0.8 + s, y + h * 1.25), (-w * 0.3, y + h * 0.7)]))
    tela.pintar(cone | aba, pano_)
    tela.traco(C.pt(-w * 0.48, y + h * 0.12), C.pt(w * 0.48, y + h * 0.12), (200, 200, 214), sobre=True)


def chama_verde(tela, ctx, J, camada):
    _, h, c = acima_da_cabeca(J, camada, 0.95)
    fx.chama(tela, c + v2(0, 2), h * 1.2 + 2 * math.sin(ctx.a * 2), h * 0.75, fx.FOGO_VERDE, fase=ctx.a * 2)
    tela.brilho(c, h * 1.1, (120, 255, 150), 0.5)


# ---------------- Reino dos Ratos (etapa 7C: conquistas do Reino) ----------------

TAMPINHAS = ((186, 40, 44), (220, 176, 64), (64, 96, 176))


def coroa_de_tampinhas(tela, ctx, J, camada):
    """Aro de lata torto com três tampinhas de pé (vermelha, dourada e azul), serrilhadas na borda."""
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.8
    y = 0.45 + camada.topo_extra
    tela.pintar(tela.capsula(C.pt(-w * 0.6, h * y), C.pt(w * 0.6, h * (y + 0.08)), h * 0.12), metal((150, 146, 140)))
    r = max(1.5, h * 0.21)
    for k, cor in enumerate(TAMPINHAS):
        c = C.pt(-w * 0.4 + k * w * 0.4, h * (y + 0.3 + 0.1 * (k == 1)))
        tela.pintar(tela.circulo(c, r), metal(cor))
        for a in range(0, 360, 90):                                           # o serrilhado da tampinha
            tela.px(*(c + dir_ang(math.radians(a + 45)) * r), tuple(v // 2 for v in cor))
        tela.px(*c, tuple(min(255, v + 70) for v in cor), emite=True)


def coroa_do_esgoto(tela, ctx, J, camada):
    """Coroa de ferro de bueiro: grade enferrujada de pontas tortas, crânio de rato na frente e lodo verde pingando."""
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.85
    y = 0.48 + camada.topo_extra
    ferro = Mat((96, 72, 52), 5, relevo=1.1, ruido=0.35, especular=(176, 132, 90))
    forma = tela.capsula(C.pt(-w * 0.6, h * y), C.pt(w * 0.6, h * (y + 0.05)), h * 0.13)
    for k, alto in enumerate((0.42, 0.62, 0.78, 0.58, 0.4)):                  # as barras da grade, tortas
        x = -w * 0.5 + k * w * 0.25
        forma |= tela.capsula(C.pt(x, h * y), C.pt(x + (k - 2) * w * 0.05, h * (y + alto)), h * 0.08, h * 0.05)
    tela.pintar(forma, ferro)
    cranio = C.pt(w * 0.18, h * (y + 0.02))                                  # crânio de rato: focinho para a frente
    tela.pintar(tela.elipse(cranio[0], cranio[1], h * 0.2, h * 0.13) | tela.circulo(cranio + v2(h * 0.2, h * 0.03), h * 0.08),
                OSSO)
    tela.px(*(cranio + v2(h * 0.02, -h * 0.03)), (40, 20, 20))
    for x, fase in ((-w * 0.5, 0), (-w * 0.15, 2)):                           # o lodo escorre e pinga (atrás do rosto)
        topo = C.pt(x, h * (y - 0.06))
        fim = topo + v2(0, h * (0.05 + 0.05 * ((ctx.i + fase) % 4)))
        tela.chapado(tela.capsula(topo, fim, h * 0.07, h * 0.09), (88, 140, 50))
        tela.px(*(fim + v2(0, 1)), (150, 210, 90), emite=True)
    tela.brilho(C.pt(0, h * (y + 0.25)), h * 0.9, (110, 200, 80), 0.22)


def chapeu_de_flautista(tela, ctx, J, camada):
    """O chapéu do caçador de ratos: pontudo e caído para trás, vermelho desbotado, faixa mostarda e uma pena longa."""
    C, h, w = medidas_da_cabeca(J)
    y = h * (0.36 + camada.topo_extra * 0.5)
    s = math.sin(ctx.a) * h * 0.05
    feltro = Mat((128, 42, 40), 6, relevo=0.9, ruido=0.18)
    aba = tela.elipse_girada(C.pt(w * 0.1, y), w * 1.05, h * 0.14, math.atan2(J["hu"][0], -J["hu"][1]))
    copa = tela.poly(C.pts([(-w * 0.58, y), (w * 0.62, y + h * 0.04), (w * 0.12, y + h * 0.5), (-w * 0.95 + s, y + h * 0.95)]))
    tela.pintar(copa | aba, feltro)
    tela.traco(C.pt(-w * 0.5, y + h * 0.12), C.pt(w * 0.55, y + h * 0.14), (190, 150, 64), sobre=True)
    base = C.pt(-w * 0.2, y + h * 0.2)
    pena = [base, base + v2(-h * 0.5, -h * 0.55 + s), base + v2(-h * 1.1, -h * 0.85 + s * 1.5)]
    tela.pintar(tela.corrente(pena, [h * 0.11, h * 0.09, h * 0.03]), Mat((232, 212, 122), 5, relevo=0.6))


# ============================================================
# ENCANTAMENTOS DE ARMA (skins de "arma")
# ============================================================

def ponto_da_arma(J, camada, t):
    mao = J["mao_" + camada.mao]
    angulo = J.get("arma_" + camada.mao, J.get("arma_f", 0.0))
    return mao + dir_ang(angulo) * camada.modelo.H * camada.comprimento * t


def encanto(paleta, sobe=0.0, raio=1.1):
    """Faíscas ao longo da arma que se mexem a cada quadro."""
    def desenhar(tela, ctx, J, camada):
        for k in range(7):
            t = (k + 0.5) / 7
            p = ponto_da_arma(J, camada, t)
            balanco = math.sin(ctx.a * 2 + k * 1.7)
            p = p + v2(balanco * 1.5, -sobe * ((ctx.i + k) % 4))
            tela.chapado(tela.circulo(p, raio * (0.7 + 0.3 * ((k + ctx.i) % 2))), paleta[3 if k % 2 else 2], emite=True)
        meio = ponto_da_arma(J, camada, 0.6)
        tela.brilho(meio, camada.modelo.H * camada.comprimento * 0.55, paleta[2], 0.5)
    return desenhar


# ============================================================
# TRAÇOS DE RAÇA (racas.json "cosmetico": desenhados por cima de qualquer roupa)
# ============================================================

def medidas_da_cabeca(J):
    """Quadro da cabeça, altura h e largura w (as mesmas de humanoide.cabeca_base)."""
    h = J["P"]["cabeca"]
    return quadro_cabeca(J), h, h * 0.82


def gorro_de_gnomo(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    y = h * (0.36 + camada.topo_extra * 0.5)
    balanco = math.sin(ctx.a) * h * 0.08
    pts = [(-w * 0.62, y), (w * 0.58, y), (w * 0.2, y + h * 0.7), (-w * 0.35 + balanco, y + h * 1.25),
           (-w * 0.75 + balanco, y + h * 1.45), (-w * 0.45, y + h * 0.6)]
    tela.pintar(tela.poly(C.pts(pts)), Mat((196, 40, 44), 6, relevo=1.0, ruido=0.1))
    tela.pintar(tela.capsula(C.pt(-w * 0.66, y), C.pt(w * 0.62, y), h * 0.12), Mat((150, 28, 34), 5, relevo=0.8))
    tela.chapado(tela.circulo(C.pt(-w * 0.75 + balanco, y + h * 1.45), h * 0.12), (236, 230, 220))


def barba_trancada(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    pelo = Mat((168, 96, 48), 6, relevo=0.9, ruido=0.25)
    tela.pintar(tela.poly(C.pts([(-w * 0.1, -h * 0.05), (w * 0.62, -h * 0.12), (w * 0.58, -h * 0.55),
                                 (w * 0.3, -h * 0.8), (w * 0.0, -h * 0.6)])), pelo)
    for x in (w * 0.18, w * 0.45):                     # duas tranças com argolas de metal
        topo, fim = C.pt(x, -h * 0.6), C.pt(x - w * 0.05, -h * 1.15 + math.sin(ctx.a + x) * 0.6)
        tela.pintar(tela.capsula(topo, fim, h * 0.11, h * 0.07), pelo.escuro(1))
        tela.pintar(tela.circulo(C.pt(x - w * 0.03, -h * 0.85), h * 0.09), metal((200, 160, 70)))


def orelha_pontuda(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    pele = Mat((156, 136, 178), 6, relevo=1.0)
    tela.pintar(tela.poly(C.pts([(w * 0.02, -h * 0.2), (-w * 0.2, h * 0.18), (-w * 1.05, h * 0.75),
                                 (-w * 0.45, -h * 0.12)])), pele)


def presas(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    for x in (w * 0.34, w * 0.62):
        tela.pintar(tela.poly(C.pts([(x - w * 0.1, -h * 0.42), (x + w * 0.08, -h * 0.42), (x + w * 0.06, h * 0.02)])),
                    OSSO)


def olhos_brilhantes(cor):
    def desenhar(tela, ctx, J, camada):
        C, h, w = medidas_da_cabeca(J)
        p = C.pt(w * 0.3, h * 0.06)
        tela.chapado(tela.circulo(p, max(1.0, h * 0.07)), cor, emite=True)
        tela.brilho(p, h * 0.55, cor, 0.55 + 0.15 * math.sin(ctx.a * 2))
    return desenhar


def chifres_curvos(cor, para_tras=True, olho=None):
    def desenhar(tela, ctx, J, camada):
        C, h, w = medidas_da_cabeca(J)
        topo = h * (0.4 + camada.topo_extra * 0.6)
        lado = -1 if para_tras else 1
        for dx, escala in ((w * 0.05, 1.0), (-w * 0.3, 0.8)):
            pts = [C.pt(dx, topo), C.pt(dx + lado * w * 0.35 * escala, topo + h * 0.4 * escala),
                   C.pt(dx + lado * w * 0.75 * escala, topo + h * 0.55 * escala),
                   C.pt(dx + lado * w * 1.0 * escala, topo + h * (0.4 if para_tras else 0.75) * escala)]
            tela.pintar(tela.corrente(pts, [h * 0.14 * escala, h * 0.1 * escala, h * 0.07 * escala, h * 0.02]),
                        Mat(cor, 6, relevo=1.3))
        if olho:
            olhos_brilhantes(olho)(tela, ctx, J, camada)
    return desenhar


# ============================================================
# PEÇAS DE EQUIPAMENTO (itens.json "camada": aparecem no herói quando equipadas)
# ============================================================

def elmo_de_ferro(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    domo = C.pts([(-w * 0.98, -h * 0.1), (-w * 1.02, h * 0.35), (-w * 0.62, h * 0.78), (0, h * 0.88), (w * 0.62, h * 0.78),
                  (w * 1.02, h * 0.35), (w * 1.0, -h * 0.12), (w * 0.2, -h * 0.05)])
    tela.pintar(tela.poly(domo), metal((140, 140, 156)))
    tela.traco(C.pt(w * 0.15, h * 0.12), C.pt(w * 0.98, h * 0.12), (14, 8, 16))           # fenda dos olhos
    tela.traco(C.pt(-w * 0.1, h * 0.88), C.pt(-w * 0.2, h * 0.3), (190, 190, 205), sobre=True)


def capuz(tela, ctx, J, camada):
    C, h, w = medidas_da_cabeca(J)
    pano_ = Mat((70, 62, 54), 6, relevo=0.9, ruido=0.15)
    capa_ = tela.poly(C.pts([(-w * 1.0, -h * 1.05), (-w * 1.12, h * 0.4), (-w * 0.6, h * 0.92), (w * 0.25, h * 0.86),
                             (w * 0.78, h * 0.5), (w * 0.86, -h * 0.05), (w * 0.7, -h * 0.9)]))
    rosto = tela.poly(C.pts([(w * 0.0, -h * 0.55), (-w * 0.05, h * 0.45), (w * 0.5, h * 0.5), (w * 1.1, h * 0.1),
                             (w * 1.1, -h * 0.6)]))
    tela.pintar(capa_ & ~rosto, pano_)


def botas(tela, ctx, J, camada):
    h = J["P"]["cabeca"]
    couro = Mat((84, 56, 36), 6, relevo=0.9, ruido=0.2)
    for lado in ("b", "f"):
        tornoz, dedo, calc = J.get("tornozelo_" + lado), J.get("dedo_" + lado), J.get("calcanhar_" + lado)
        if tornoz is None or dedo is None:
            continue
        joelho = J.get("joelho_" + lado, tornoz + v2(0, -h))
        cano = tornoz + (joelho - tornoz) * 0.45
        tela.pintar(tela.capsula(cano, tornoz, h * 0.2, h * 0.19), couro if lado == "f" else couro.escuro(1))
        tela.pintar(tela.poly([calc + v2(0, -h * 0.28), tornoz + v2(0, -h * 0.05), dedo + v2(h * 0.08, -h * 0.12),
                               dedo + v2(h * 0.08, h * 0.04), calc + v2(0, h * 0.04)]),
                    couro if lado == "f" else couro.escuro(1))
        tela.traco(cano + v2(-h * 0.2, 0), cano + v2(h * 0.2, 0), (40, 26, 20), sobre=True)


def escudo_na_mao(tela, ctx, J, camada):
    h = J["P"]["cabeca"]
    centro = J.get("mao_b")
    if centro is None:
        return
    centro = centro + v2(-h * 0.1, -h * 0.05)
    madeira_ = Mat((122, 84, 52), 6, relevo=1.0, ruido=0.25)
    tela.pintar(tela.circulo(centro, h * 0.85), madeira_)
    tela.pintar(tela.circulo(centro, h * 0.85) & ~tela.circulo(centro, h * 0.68), metal((110, 108, 120)))
    tela.pintar(tela.circulo(centro, h * 0.2), metal((170, 170, 186)))


def gola_de_capa(tela, ctx, J, camada):
    h = J["P"]["cabeca"]
    pescoco, ombro_f, ombro_b, u = J["pescoco"], J["ombro_f"], J["ombro_b"], J["u"]
    pano_ = Mat((120, 34, 40), 6, relevo=0.8, ruido=0.1)
    balanco = math.sin(ctx.a) * h * 0.06
    costas = ombro_b - ombro_f                         # a capa cai pelas costas (lado do ombro de trás)
    pts = [pescoco + u * h * 0.3, ombro_b + u * h * 0.2 + costas * 0.2,
           ombro_b + costas * 0.45 - u * h * 1.6 + v2(balanco, 0), ombro_b - u * h * 1.8 + v2(balanco * 0.5, 0),
           pescoco - u * h * 0.5]
    tela.pintar(tela.poly(pts), pano_)
    tela.pintar(tela.capsula(pescoco + u * h * 0.1, ombro_f + u * h * 0.1, h * 0.14), pano_.escuro(1))   # gola
    tela.chapado(tela.circulo(ombro_f + u * h * 0.05, max(1.0, h * 0.12)), (220, 180, 80))             # broche


def elmo_do_cavaleiro_ossudo(tela, ctx, J, camada):
    """Elmo feito de crânio: domo de osso, órbitas fundas na frente e dois chifres curtos."""
    C, h, w = medidas_da_cabeca(J)
    domo = C.pts([(-w * 1.0, -h * 0.05), (-w * 1.04, h * 0.4), (-w * 0.6, h * 0.82), (0, h * 0.92), (w * 0.62, h * 0.8),
                  (w * 1.04, h * 0.38), (w * 1.02, -h * 0.25), (w * 0.4, -h * 0.4)])
    tela.pintar(tela.poly(domo), OSSO)
    for x in (w * 0.35, w * 0.75):                                     # órbitas
        tela.chapado(tela.circulo(C.pt(x, h * 0.12), max(1.0, h * 0.12)), (14, 8, 14))
    tela.traco(C.pt(w * 0.5, -h * 0.05), C.pt(w * 0.5, -h * 0.3), (60, 50, 40), sobre=True)
    for lado in (-1, 1):
        tela.pintar(tela.corrente([C.pt(lado * w * 0.55, h * 0.7), C.pt(lado * w * 0.9, h * 1.05)], [h * 0.1, h * 0.03]), OSSO)


ACESSORIOS = {
    "aureola": aureola,
    "chifres_de_osso": chifres_de_osso,
    "coroa_partida": coroa_partida,
    "chama_fantasma": chama_fantasma,
    "brasa": encanto(fx.FOGO, sobe=1.0),
    "geada": encanto(fx.GELO, raio=0.9),
    "sombra": encanto(fx.FOGO_ROXO, sobe=0.6),
    "ouro": encanto([(90, 60, 20), (170, 120, 40), (240, 200, 90), (255, 240, 170), (255, 255, 230)], raio=0.8),
    # skins raras (vitrine do Taverneiro)
    "coroa_de_espinhos": coroa_de_espinhos,
    "mascara_da_peste": mascara_de_bico(),
    "chapeu_pontudo": chapeu_pontudo,
    "chama_verde": chama_verde,
    "peconha": encanto(fx.FOGO_VERDE, sobe=0.8),
    "sangria": encanto([(60, 4, 10), (110, 10, 20), (180, 30, 40), (230, 70, 70), (255, 140, 140)], sobe=-0.6),
    "estelar": encanto([(60, 60, 120), (130, 140, 230), (210, 220, 255), (255, 255, 255), (255, 255, 255)], raio=0.7),
    # conquistas do Reino dos Ratos (etapa 7C)
    "coroa_de_tampinhas": coroa_de_tampinhas,
    "mascara_do_doutor": mascara_de_bico(couro=(30, 28, 32), especular=(110, 110, 120), lentes=(110, 230, 110),
                                         chapeu=(20, 18, 22), aba=1.4, brilho=True),
    "chapeu_de_flautista": chapeu_de_flautista,
    "coroa_do_esgoto": coroa_do_esgoto,
    "luz_limpa": encanto([(70, 110, 100), (150, 210, 190), (224, 255, 244), (255, 255, 255), (255, 255, 250)], sobe=0.5,
                         raio=0.8),
    # traços de raça
    "raca_gnomo": gorro_de_gnomo,
    "raca_anao": barba_trancada,
    "raca_elfo": orelha_pontuda,
    "raca_orc": presas,
    "raca_morto_vivo": olhos_brilhantes((120, 220, 255)),
    "raca_hemofago": olhos_brilhantes((240, 40, 50)),
    "raca_draconiano": chifres_curvos((176, 66, 40)),
    "raca_demonio": chifres_curvos((70, 24, 34), para_tras=False, olho=(255, 90, 40)),
    # peças de equipamento
    "eq_elmo": elmo_de_ferro,
    "eq_capuz": capuz,
    "eq_botas": botas,
    "eq_escudo": escudo_na_mao,
    "eq_gola": gola_de_capa,
    "elmo_cavaleiro_ossudo": elmo_do_cavaleiro_ossudo,
}
# equipamento visível por tipo de peça (forja/personagens/equipamento.py; substitui os eq_* acima de mesmo nome)
ACESSORIOS.update(PECAS)


class CamadaVisual(Modelo):
    """Só o acessório, desenhado com o esqueleto e as poses do herói da geometria.

    As peças de equipamento (tingivel) saem com o dobro de linhas: "<anim>" com o que o jogo tinge
    e "<anim>_fixo" com o que fica com a cor própria (ver equipamento.separar_tinta)."""

    def __init__(self, geometria, acessorio):
        fabrica, self.topo_extra, self.mao, self.comprimento = GEOMETRIAS[geometria]
        self.modelo = fabrica()
        self.geometria = geometria
        self.acessorio = acessorio
        self.tingivel = acessorio in PECAS
        self._planos = {}
        super().__init__()
        for atributo in ("H", "prop", "base", "estilo", "larg", "alt", "ancora", "semente"):
            setattr(self, atributo, getattr(self.modelo, atributo))
        self.nome = f"camada_{geometria}_{acessorio}"

    def pose(self, ctx):
        return self.modelo.pose(ctx)

    def animacoes(self):
        linhas = super().animacoes()
        if self.tingivel:
            linhas = linhas + [(anim + FIXO, n) for anim, n in linhas]
        return linhas

    def quadro(self, anim, i, n):
        if not self.tingivel:
            return super().quadro(anim, i, n)
        base = anim[:-len(FIXO)] if anim.endswith(FIXO) else anim
        if (base, i) not in self._planos:                       # desenha uma vez e separa os dois planos
            self._planos[(base, i)] = separar_tinta(super().quadro(base, i, n))
        tinta, fixo = self._planos[(base, i)]
        return fixo if anim.endswith(FIXO) else tinta

    def desenhar(self, tela, ctx, J):
        ACESSORIOS[self.acessorio](tela, ctx, J, self)
