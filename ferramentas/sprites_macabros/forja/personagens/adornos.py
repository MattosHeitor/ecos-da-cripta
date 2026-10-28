"""Adornos de silhueta das roupas dos heróis (subclasses, especializações e skins).

Cada roupa (roupas.py) recebe uma lista de adornos: peças desenhadas por cima do mesmo modelo,
com o mesmo esqueleto e as mesmas poses. Modelo.quadro (anim.py) desenha os adornos "atrás"
ANTES do herói (o corpo e a capa os cobrem; aparecem em volta da silhueta) e os "da frente"
DEPOIS dele. Assim cada roupa ganha um contorno próprio sem copiar código do herói.

    atrás     arma_costas, estandarte, asas, aureola, fitas, manto_de_caudas, tentaculos, galhos, espinhos_costas,
              armadilhas, trofeu, aljava_grande, balao, gola_alta
    frente    ombreira, cintura, bandoleira, pteruges, manica, avental, tabardo_longo, raizes,
              contas_grandes, familiar, particulas, orbes

Uso (roupas.py):
    guerreiro("guerreiro_berserker", ..., adornos=(A.ombreira("espinhos"), A.arma_costas("machado")))

As peças do tronco não passam por cima do braço da frente (fora_do_braco), como no equipamento.
"""
import math

import numpy as np

from ..motor import Mat, metal, v2, lerp, dir_ang, norm, misturar
from ..humanoide import quadro_tronco, quadro_cabeca, capa as capa_nas_costas
from .. import armas, fx, texturas as T
from .herois import MADEIRA, COURO, COURO_ESC, OURO_VELHO, OSSO, FERRO

CORDA = (64, 44, 34)
SANGUE = (110, 14, 24)


# ============================================================
# REGISTRO
# ============================================================

class Adorno:
    """Uma peça de silhueta: a função que desenha, se vai atrás do herói e os parâmetros."""

    def __init__(self, desenho, atras, params):
        self.desenho = desenho
        self.atras = atras
        self.params = params

    def __call__(self, tela, ctx, J, modelo):
        self.desenho(tela, ctx, J, modelo, **self.params)

    def __repr__(self):
        return f"Adorno({self.desenho.__name__}, {'atrás' if self.atras else 'frente'})"


def _adorno(atras):
    def decorar(desenho):
        def criar(*args, **params):
            nomes = desenho.__code__.co_varnames[4:4 + len(args)]
            params.update(zip(nomes, args))
            return Adorno(desenho, atras, params)
        criar.__name__ = desenho.__name__
        criar.__doc__ = desenho.__doc__
        return criar
    return decorar


atras = _adorno(True)
frente = _adorno(False)


# ============================================================
# AJUDANTES
# ============================================================

def _ang(vetor):
    """Ângulo no padrão de dir_ang (0 = para cima, positivo gira para a direita)."""
    return math.atan2(vetor[0], -vetor[1])


def _base(J):
    """(H, quadro do tronco, altura do tronco, eixo cima, eixo frente, ângulo do tronco)."""
    Q = quadro_tronco(J)
    return J["H"], Q, J["P"]["tronco"], J["u"], Q.f, _ang(J["u"])


def _mat(cor, n=6, **kw):
    if isinstance(cor, Mat):
        return cor
    kw.setdefault("ruido", 0.12)
    return Mat(cor, n, **kw)


def _metal(cor):
    return cor if isinstance(cor, Mat) else metal(cor)


def braco_da_frente(tela, J):
    """Máscara do braço da frente (as peças do tronco ficam por baixo dele)."""
    S = J["P"]
    o, c, m = J["ombro_f"], J["cotovelo_f"], J["mao_f"]
    mask = tela.capsula(o, c, S["l_braco"] * 1.2, S["l_antebraco"] * 1.15)
    mask |= tela.capsula(c, m, S["l_antebraco"] * 1.15, S["l_antebraco"] * 1.0) | tela.circulo(m, S["mao"] * 0.9)
    return mask


def fora_do_braco(tela, J, mask):
    return mask & ~braco_da_frente(tela, J)


def vivo(ctx):
    """Efeitos soltos (partículas, orbes) somem quando o herói desaba."""
    return not (ctx.anim == "morte" and ctx.i >= 2)


def caveirinha(tela, c, r=2.0, mat=OSSO, olhos=(30, 20, 20), emite=False):
    tela.pintar(tela.circulo(c, r), mat)
    tela.pintar(tela.capsula(c + v2(0, r * 0.6), c + v2(0, r * 1.1), r * 0.55), mat.escuro(1), linha_interna=False)
    tela.px(c[0] - r * 0.4, c[1], olhos, emite=emite)
    tela.px(c[0] + r * 0.45, c[1], olhos, emite=emite)


# ============================================================
# ATRÁS: ARMAS E OBJETOS NAS COSTAS
# ============================================================

def _espada_fina(tela, mao, ang, comp, lamina, guarda):
    """Rapieira: lâmina fina e guarda de taça."""
    armas.espada(tela, mao, ang, comp, lamina, guarda, COURO_ESC, larg=0.8, ponta=0.1, guarda_larg=2.5, pomo=guarda)
    tela.pintar(tela.circulo(v2(mao) + dir_ang(ang) * 2.4, 1.8), guarda)


@atras
def arma_costas(tela, ctx, J, modelo, tipo="montante", metal_cor=(150, 150, 166), cabo=None, inclina=0.6):
    """Arma presa às costas, na diagonal: só o cabo ou a cabeça aparecem por cima do ombro."""
    H, Q, T_, u, f, au = _base(J)
    lam = _metal(metal_cor)
    cabo = cabo or MADEIRA
    c = Q.pt(-0.07 * H, T_ * 0.55)
    a = au - inclina
    d = dir_ang(a)
    n = v2(-d[1], d[0])
    if tipo == "montante":
        armas.espada(tela, c + d * H * 0.28, a + math.pi, H * 0.62, lam.claro(1), lam, COURO_ESC, larg=2.1,
                     guarda_larg=5.5, pomo=lam)
    elif tipo == "machado":
        armas.machado(tela, c - d * H * 0.2, a, H * 0.5, cabo, lam, duplo=True, tam=1.15)
    elif tipo == "tridente":
        base, topo = armas.haste(tela, c, a, H * 0.36, H * 0.36, cabo, 0.9)
        dentes = tela.capsula(topo - n * 4, topo + n * 4, 0.9)
        for k in (-4, 0, 4):
            p = topo + n * k
            comp = 7 if k == 0 else 5.5
            dentes |= tela.capsula(p, p + d * comp, 0.8)
            dentes |= tela.poly([p + d * comp - n * 1.4, p + d * comp + n * 1.4, p + d * (comp + 3)])
        tela.pintar(dentes, lam)
    elif tipo == "foice":
        armas.foice(tela, c - d * H * 0.24, a, H * 0.55, cabo, lam.claro(1), tam=1.15)
    elif tipo == "cutelo":                                                  # cutelo de açougueiro gigante
        _, topo = armas.haste(tela, c - d * H * 0.1, a, H * 0.12, H * 0.12, cabo, 1.2)
        lamina = [topo - n * 1.5, topo + d * H * 0.3 - n * 1.5, topo + d * H * 0.32 + n * 9, topo + n * 9.5 + d * 2]
        m = tela.pintar(tela.poly(lamina), lam)
        tela.traco(topo + n * 9.2 + d * 3, topo + d * H * 0.31 + n * 8.7, lam[6], sobre=True)
        tela.chapado(m & (tela.ruido_base > 0.12), SANGUE)
        tela.chapado(tela.circulo(topo + d * H * 0.25 + n * 2, 1.0) & m, (20, 14, 18))
    elif tipo == "arco":                                                    # arco longo pendurado, sem corda puxada
        a = au - 0.25
        d = dir_ang(a)
        n = v2(-d[1], d[0])
        pts = [c + d * H * 0.42 - n * 1, c + d * H * 0.2 - n * 4, c - n * 5, c - d * H * 0.2 - n * 4, c - d * H * 0.42 - n * 1]
        tela.pintar(tela.corrente(pts, [0.6, 1.1, 1.4, 1.1, 0.6]), cabo)
        tela.traco(pts[0], pts[-1], (200, 190, 160))
    elif tipo == "pa":
        _, topo = armas.haste(tela, c, a, H * 0.3, H * 0.3, cabo, 0.9)
        tela.pintar(tela.poly([topo - n * 3.6, topo + n * 3.6, topo + n * 3.4 + d * 7, topo + d * 9.5,
                               topo - n * 3.4 + d * 7]), lam)
        tela.pintar(tela.capsula(topo - d * 1, topo + d * 1.5, 1.4), lam.escuro(1))
        tela.pintar(tela.capsula(c - d * H * 0.3 - n * 2.5, c - d * H * 0.3 + n * 2.5, 0.8), cabo.escuro(1))
    elif tipo == "bastao":
        a = au - 1.15
        d = dir_ang(a)
        armas.haste(tela, c, a, H * 0.42, H * 0.42, cabo, 1.0)
        for s in (-1, 1):
            p = c + d * H * 0.42 * s
            tela.pintar(tela.capsula(p - d * s * 3.5, p, 1.5), lam)
    elif tipo == "vassoura":
        a = au - 1.0
        d = dir_ang(a)
        n = v2(-d[1], d[0])
        armas.haste(tela, c, a, H * 0.3, H * 0.28, cabo, 0.9)
        topo = c + d * H * 0.28
        palha = Mat((176, 140, 70), 5, ruido=0.6, dither=0.6)
        tela.pintar(tela.poly([topo - n * 2, topo + n * 2, topo + d * 13 + n * 5.5, topo + d * 15, topo + d * 13 - n * 5.5]),
                    palha)
        tela.traco(topo + n * 2.2, topo - n * 2.2, CORDA, sobre=True)
        T.listras(tela, tela.poly([topo, topo + d * 15 + n * 5, topo + d * 15 - n * 5]), topo, (110, 80, 40),
                  eixo=tuple(n), espaco=2, larg=0.6, ondula=0.3, forca=0.6)
    elif tipo == "besta":
        a = au - 0.35
        d = dir_ang(a)
        n = v2(-d[1], d[0])
        armas.haste(tela, c, a, H * 0.2, H * 0.24, cabo, 1.4)
        topo = c + d * H * 0.22
        arco = [topo - n * 9 - d * 3, topo - n * 4, topo, topo + n * 4, topo + n * 9 - d * 3]
        tela.pintar(tela.corrente(arco, [0.8, 1.2, 1.4, 1.2, 0.8]), lam)
        tela.tracos([arco[0], c + d * H * 0.05, arco[-1]], (190, 180, 160))
    elif tipo in ("rapieiras", "laminas"):
        for k, (a_k, desloc) in enumerate(((au - 0.3, -2), (au - 0.95, 2))):
            d_k = dir_ang(a_k)
            mao = c + d_k * H * 0.25 + f * desloc
            if tipo == "rapieiras":
                _espada_fina(tela, mao, a_k + math.pi, H * 0.5, lam.claro(1) if k else lam, OURO_VELHO)
            else:
                armas.espada(tela, mao, a_k + math.pi, H * 0.36, lam.claro(1) if k else lam, lam.escuro(1), COURO_ESC,
                             larg=1.4, guarda_larg=3.2, curva=1.2)


@atras
def estandarte(tela, ctx, J, modelo, cor=(150, 30, 34), emblema="cruz", cor_emblema=None):
    """Estandarte preso às costas: haste acima da cabeça, travessa e bandeira de cauda partida."""
    H, Q, T_, u, f, au = _base(J)
    pano = _mat(cor, desce=0.3, relevo=0.8)
    emb = cor_emblema or OURO_VELHO[4]
    base = Q.pt(-0.06 * H, T_ * 0.2)
    topo = J["topo"] + u * H * 0.36 - f * H * 0.13
    tela.pintar(tela.capsula(base, topo, 0.9), MADEIRA)
    travessa = topo - u * H * 0.03
    tela.pintar(tela.capsula(travessa, travessa - f * H * 0.22, 0.7), MADEIRA)
    tela.pintar(tela.circulo(topo + u * 1.5, 1.4), OURO_VELHO)
    s = math.sin(ctx.a)
    a, b = travessa - f * H * 0.01, travessa - f * H * 0.21
    fa = a - u * H * 0.3 - f * s * 1.0
    fb = b - u * H * 0.3 - f * s * 2.0
    m = tela.pintar(tela.poly([a, b, fb, lerp(fa, fb, 0.5) + u * H * 0.07, fa]), pano)
    centro = lerp(lerp(a, b, 0.5), lerp(fa, fb, 0.5), 0.42)
    if emblema == "cruz":
        tela.traco(centro - u * 4, centro + u * 4, emb, sobre=True)
        tela.traco(centro - f * 3 + u * 1.5, centro + f * 3 + u * 1.5, emb, sobre=True)
    elif emblema == "coroa":
        for k in (-2, 0, 2):
            tela.traco(centro + f * k - u * 1, centro + f * k + u * (2.5 if k == 0 else 1.5), emb, sobre=True)
        tela.traco(centro - f * 3 - u * 1, centro + f * 3 - u * 1, emb, sobre=True)
    elif emblema == "listras":
        T.listras(tela, m, centro, emb, eixo=tuple(f), espaco=3, larg=1.0, ondula=0.4, forca=0.9)
    elif emblema == "nota":
        from .acampamento import nota_musical
        nota_musical(tela, centro - f * 1 + u * 1, emb, emite=False)
    elif emblema == "sol":
        for k in range(8):
            tela.traco(centro, centro + dir_ang(k * math.pi / 4) * 3.2, emb, sobre=True)
        tela.pintar(tela.circulo(centro, 1.5), OURO_VELHO)


@atras
def asas(tela, ctx, J, modelo, estilo="penas", cor=(220, 214, 200), brilho=None):
    """Par de asas nas costas (penas, ossos ou mariposa); batem devagar no parado."""
    H, Q, T_, u, f, au = _base(J)
    raiz = Q.pt(-0.05 * H, T_ * 0.82)
    bate = 0.12 * math.sin(ctx.a) + (0.25 if ctx.golpe else 0)
    mat = _mat(cor, relevo=0.8)
    for lado, escala, m, desloc in (("longe", 0.8, mat.escuro(1), f * 3 + u * 2), ("perto", 1.0, mat, v2(0, 0))):
        r = raiz + desloc
        if estilo == "penas":
            for k in range(6):
                a = au - 0.25 - k * 0.3 - bate * (1 - k * 0.12)
                comp = H * (0.42 - k * 0.045) * escala
                d = dir_ang(a)
                p1 = r + d * comp
                tela.pintar(tela.poly([r + v2(-d[1], d[0]) * 1.4, p1 + v2(-d[1], d[0]) * 1.2, p1 + d * 2.5,
                                       p1 - v2(-d[1], d[0]) * 1.2, r - v2(-d[1], d[0]) * 1.4]), m)
            tela.pintar(tela.circulo(r, H * 0.05 * escala), m)
        elif estilo == "osso":
            braco_a = r + dir_ang(au - 0.6 - bate) * H * 0.18 * escala
            tela.pintar(tela.capsula(r, braco_a, 1.4, 1.1), OSSO.escuro(0 if lado == "perto" else 1))
            membrana = [braco_a]
            for k in range(4):
                a = au - 0.4 - k * 0.38 - bate
                ponta = braco_a + dir_ang(a) * H * (0.3 - k * 0.04) * escala
                tela.pintar(tela.capsula(braco_a, ponta, 1.0, 0.5), OSSO.escuro(0 if lado == "perto" else 1))
                membrana.append(ponta)
            membrana.append(r - u * H * 0.08)
            mm = tela.poly(membrana) & (tela.alfa == 0) & (tela.ruido_base > -0.28)
            tela.pintar(mm, m.escuro(2), linha_interna=False)
        else:                                                                   # mariposa
            for a0, rx, ry in ((au - 0.75 - bate, 0.2, 0.13), (au - 1.9 - bate * 0.5, 0.14, 0.09)):
                c = r + dir_ang(a0) * H * rx * escala
                lobo = tela.elipse_girada(c, H * rx * escala, H * ry * escala, a0 - math.pi / 2)
                tela.pintar(lobo, m)
                olho = brilho or (230, 230, 255)
                tela.chapado(tela.circulo(c + dir_ang(a0) * 2, 1.4 * escala) & lobo, olho, emite=bool(brilho))
                tela.px(*(c + dir_ang(a0) * 2), (20, 16, 30))
    if brilho and vivo(ctx):
        tela.brilho(raiz + dir_ang(au - 0.9) * H * 0.18, H * 0.25, brilho, 0.3)


@atras
def aureola(tela, ctx, J, modelo, estilo="sol", cor=(255, 210, 120), escala=1.0):
    """Disco ou anel atrás da cabeça e dos ombros: sol, runas, lua, eclipse, cristais, espinhos,
    louros, mandala ou lótus."""
    if not vivo(ctx):
        return
    H, Q, T_, u, f, au = _base(J)
    c = lerp(J["pescoco"], J["cabeca"], 0.55) - f * H * 0.05
    R = H * 0.2 * escala
    gira = ctx.a * 0.25
    if estilo == "sol":
        raios = []
        for k in range(20):
            a = k * math.pi / 10 + gira * 0.3
            rr = R * (1.35 if k % 2 == 0 else 1.08)
            raios.append(c + dir_ang(a) * rr)
        disco = tela.poly(raios)
        tela.brilho(c, R * 1.8, cor, 0.3 + 0.08 * math.sin(ctx.a))
        tela.pintar(disco & ~tela.circulo(c, R * 0.82), metal(cor), linha_interna=False)
        tela.pintar(tela.circulo(c, R * 0.82) & ~tela.circulo(c, R * 0.7), metal(cor).escuro(1), linha_interna=False)
    elif estilo in ("runas", "mandala"):
        anel = tela.circulo(c, R) & ~tela.circulo(c, R - 1.6)
        tela.chapado(anel, cor, emite=True)
        if estilo == "mandala":
            tela.chapado(tela.circulo(c, R * 0.72) & ~tela.circulo(c, R * 0.72 - 1), misturar(cor, (255, 255, 255), 0.3),
                         emite=True)
            for k in range(12):
                p = c + dir_ang(k * math.pi / 6 - gira) * R * 0.86
                tela.chapado(tela.circulo(p, 1.0), cor, emite=True)
        else:
            for k in range(6):
                fx.runa(tela, c + dir_ang(k * math.pi / 3 + gira) * (R + 3.2), cor, 2, forma=k)
        tela.brilho(c, R * 1.5, cor, 0.25 + 0.08 * math.sin(ctx.a))
    elif estilo == "lua":
        lua = tela.circulo(c - f * 2, R * 1.05) & ~tela.circulo(c + f * R * 0.45 - u * 1, R * 0.9)
        tela.pintar(lua, Mat(cor, 6, relevo=0.6, satur=0.6), linha_interna=False)
        tela.brilho(c - f * R * 0.6, R * 1.4, cor, 0.3)
        for k in range(3):
            p = c + dir_ang(-1.0 + k * 0.9 + gira) * R * 1.35
            tela.chapado(tela.poly([p - v2(1.2, 0), p - v2(0, 1.2), p + v2(1.2, 0), p + v2(0, 1.2)]), cor, emite=True)
    elif estilo == "eclipse":
        tela.brilho(c, R * 2.0, cor, 0.45 + 0.1 * math.sin(ctx.a))
        coroa = []
        for k in range(28):
            a = k * math.pi / 14 + gira
            coroa.append(c + dir_ang(a) * R * (1.25 if k % 2 == 0 else 1.05 + 0.08 * math.sin(k * 1.7 + ctx.a)))
        tela.chapado(tela.poly(coroa), cor, emite=True)
        tela.chapado(tela.circulo(c, R * 0.98), (14, 8, 18))
    elif estilo == "cristais":
        for k in range(9):
            a = -math.pi * 0.8 + k * math.pi * 0.2 + au
            fx.cristal(tela, c + dir_ang(a) * R * 0.6, a, R * (0.9 + 0.3 * (k % 2)), 2.2)
        tela.brilho(c, R * 1.4, cor, 0.25)
    elif estilo == "espinhos":
        pts = []
        for k in range(22):
            a = k * math.pi / 11 + gira * 0.2
            pts.append(c + dir_ang(a) * R * (1.4 if k % 2 == 0 else 0.95))
        tela.pintar(tela.poly(pts) & ~tela.circulo(c, R * 0.78), Mat(cor, 5, relevo=0.8), linha_interna=False)
        tela.brilho(c, R * 1.3, misturar(cor, (120, 255, 230), 0.5), 0.25)
    elif estilo == "louros":
        R = H * 0.11 * escala
        c = J["cabeca"] - f * 1
        folha = metal(cor)
        for s in (-1, 1):
            for k in range(6):
                a = math.pi + s * (0.35 + k * 0.38) + _ang(J["hu"])
                p = c + dir_ang(a) * R * 1.15
                tela.pintar(tela.elipse_girada(p, 2.0, 1.0, a + s * 0.8), folha, linha_interna=False)
    elif estilo == "lotus":
        for k in range(7):
            a = au - 1.35 + k * 0.45
            p = c + dir_ang(a) * R * 0.75
            tela.pintar(tela.elipse_girada(p, R * 0.55, R * 0.22, a - math.pi / 2), Mat(cor, 6, relevo=0.7))
        tela.brilho(c, R * 1.5, cor, 0.3)


@atras
def fitas(tela, ctx, J, modelo, cor=(170, 30, 40), n=2, comp=0.35, origem="costas", estilo="pano"):
    """Fitas finas esvoaçando para trás e caindo (pano, dragão de chamas, fumaça ou sangue)."""
    H, Q, T_, u, f, au = _base(J)
    raiz0 = Q.pt(-0.07 * H, T_ * (0.8 if origem == "costas" else 0.0))
    for i in range(n):
        raiz = raiz0 - u * i * 3
        pts = [raiz]
        for k in range(1, 8):
            t = k / 7
            onda = math.sin(ctx.a + t * 4.5 + i * 1.7) * (1 + t * 2.5)
            cai = H * (0.1 + 0.08 * i) * t ** 1.4 if estilo != "dragao" else H * 0.05 * t
            p = raiz - f * H * comp * t - u * cai + u * onda
            pts.append(p)
        larg = [1.5, 1.4, 1.25, 1.1, 0.95, 0.8, 0.6, 0.4] if estilo != "dragao" else [2.6, 2.4, 2.2, 2.0, 1.7, 1.4, 1.0, 0.5]
        mask = tela.corrente(pts, larg)
        if estilo == "fumaca":
            tela.vidro(mask & (tela.ruido_base > -0.35), _mat(cor, relevo=0.4), 0.6, linha_interna=False)
        elif estilo == "dragao":
            tela.chapado(mask, cor, emite=True)
            tela.chapado(tela.corrente(pts, [w * 0.45 for w in larg]), misturar(cor, (255, 250, 220), 0.6), emite=True)
            cab = pts[-1]
            tela.chapado(tela.poly([cab - u * 2, cab - f * 4, cab + u * 2]), cor, emite=True)
            tela.brilho(pts[3], H * 0.2, cor, 0.35)
        else:
            m = tela.pintar(mask, _mat(cor, relevo=0.6, desce=0.2))
            if estilo == "sangue":
                for p in pts[3::2]:
                    fx.gota_sangue(tela, p + u * 3)


@atras
def manto_de_caudas(tela, ctx, J, modelo, cor=(196, 128, 126), aneis=(132, 72, 76), n=6, comp=0.62, no=(84, 36, 44)):
    """Manto de caudas de rato atadas num nó de carne na nuca (o Manto da Roda): caem pelas costas, abrindo em leque
    para trás, balançando cada uma no seu ritmo, com os anéis da pele."""
    H, Q, T_, u, f, au = _base(J)
    raiz = Q.pt(-0.08 * H, T_ * 0.95)
    carne = _mat(cor, relevo=0.9, especular=misturar(cor, (255, 255, 255), 0.5))
    for i in range(n):
        abre = 0.04 + 0.16 * i / max(1, n - 1)                           # as de fora se abrem mais para trás
        pts = [raiz - f * i * 0.8]
        for k in range(1, 9):
            t = k / 8
            onda = math.sin(ctx.a + t * 3.5 + i * 1.3) * (0.4 + t * 1.8)
            pts.append(pts[0] - f * H * abre * t - u * H * comp * t * (1 - 0.06 * i) + f * onda)
        tela.pintar(tela.corrente(pts, [1.7, 1.6, 1.45, 1.3, 1.15, 1.0, 0.8, 0.6, 0.35]), carne if i % 2 == 0 else carne.escuro(1))
        for p in pts[2:8:2]:
            tela.px(*p, aneis)
    tela.pintar(tela.circulo(raiz - f * 2 + u * 1.5, H * 0.055), _mat(no, relevo=1.2, especular=(200, 120, 120)))


@atras
def tentaculos(tela, ctx, J, modelo, cor=(40, 70, 80), n=3, ventosas=(190, 170, 200), estilo="tentaculo"):
    """Tentáculos saindo das costas e se enrolando para trás (ou patas articuladas de aranha)."""
    H, Q, T_, u, f, au = _base(J)
    mat = _mat(cor, relevo=1.0, especular=misturar(cor, (255, 255, 255), 0.7))
    if estilo == "patas":
        for i in range(n):
            raiz = Q.pt(-0.07 * H, T_ * (0.35 + i * 0.18))
            a = au - 0.7 - i * 0.38 + 0.06 * math.sin(ctx.a + i)
            joelho = raiz + dir_ang(a) * H * (0.25 - i * 0.015)
            ponta = joelho + dir_ang(a - 2.2 + i * 0.15) * H * (0.27 - i * 0.02)
            m = mat.escuro(1) if i % 2 else mat
            tela.pintar(tela.corrente([raiz, joelho], [1.6, 1.3]), m)
            tela.pintar(tela.corrente([joelho, lerp(joelho, ponta, 0.6), ponta], [1.3, 0.9, 0.3]), m)
            tela.px(*joelho, ventosas)
        return
    for i in range(n):
        raiz = Q.pt(-0.05 * H, T_ * (0.3 + i * 0.25))
        a = au - 1.2 - i * 0.35 + 0.15 * math.sin(ctx.a + i)
        pts = [raiz]
        for k in range(1, 9):
            a += 0.18 + 0.1 * math.sin(ctx.a + i * 2 + k * 0.6)
            pts.append(pts[-1] + dir_ang(a) * H * 0.045)
        larg = [2.6 - k * 0.27 for k in range(9)]
        tela.pintar(tela.corrente(pts, larg), mat.escuro(1) if i % 2 else mat)
        for p in pts[1:6:2]:
            tela.px(*(p + u * 1), ventosas)


@atras
def galhos(tela, ctx, J, modelo, cor=(70, 52, 40), folhas=(70, 100, 50), flores=None):
    """Galhos secos brotando das costas e subindo atrás da cabeça, como chifres de cervo."""
    H, Q, T_, u, f, au = _base(J)
    casca = Mat(cor, 5, ruido=0.3, relevo=0.9)
    folha = Mat(folhas, 5, relevo=0.6) if folhas else None

    def ramo(p, a, comp, larg, nivel):
        fim = p + dir_ang(a) * comp
        tela.pintar(tela.capsula(p, fim, larg, larg * 0.65), casca)
        if nivel < 2:
            ramo(fim, a - 0.45, comp * 0.62, larg * 0.65, nivel + 1)
            ramo(fim, a + 0.4, comp * 0.55, larg * 0.6, nivel + 1)
        elif folha is not None:
            tela.pintar(tela.elipse_girada(fim, 1.8, 1.1, a), folha, linha_interna=False)
            if flores:
                tela.px(*fim, flores)

    for s, a0 in ((0, au - 0.35), (1, au - 0.95)):
        ramo(Q.pt(-0.06 * H, T_ * 0.85) + u * s * 2, a0 + 0.06 * math.sin(ctx.a), H * 0.17, 1.5, 0)


@atras
def espinhos_costas(tela, ctx, J, modelo, cor=(214, 202, 172), n=5):
    """Espinhos de osso saindo da coluna, apontando para trás e para cima."""
    H, Q, T_, u, f, au = _base(J)
    mat = Mat(cor, 6, relevo=1.1)
    for k in range(n):
        t = k / max(1, n - 1)
        base = Q.pt(-0.085 * H, T_ * (0.3 + t * 0.75))
        a = au - 0.9 - (1 - t) * 0.6
        comp = H * (0.11 + 0.07 * math.sin(math.pi * t))
        d = dir_ang(a)
        nrm = v2(-d[1], d[0])
        tela.pintar(tela.poly([base - nrm * 2.6 - d * 2, base + nrm * 2.6 - d * 2, base + d * comp * 0.6 + nrm * 0.8,
                               base + d * comp]), mat)


@atras
def armadilhas(tela, ctx, J, modelo, metal_cor=(110, 106, 112)):
    """Armadilha de dentes e um rolo de corda presos às costas."""
    H, Q, T_, u, f, au = _base(J)
    ferro = metal(metal_cor, ruido=0.3)
    c = Q.pt(-0.11 * H, T_ * 0.62)
    r = H * 0.085
    anel = tela.circulo(c, r) & ~tela.circulo(c, r - 1.6)
    dentes = np.zeros_like(anel)
    for k in range(10):
        a = k * math.pi / 5
        p = c + dir_ang(a) * (r - 1.2)
        dentes |= tela.poly([p + dir_ang(a + 1.57) * 1.2, p - dir_ang(a + 1.57) * 1.2, p - dir_ang(a) * 3.2])
    tela.pintar(anel | dentes, ferro)
    tela.pintar(tela.capsula(c - f * r, c + f * r * 0.2, 1.0), ferro.escuro(1))
    corda = Q.pt(-0.09 * H, T_ * 0.15)
    tela.pintar(tela.elipse_girada(corda, H * 0.06, H * 0.04, au + 0.3), Mat((150, 120, 80), 5, ruido=0.5))
    tela.pintar(tela.elipse_girada(corda, H * 0.035, H * 0.018, au + 0.3), Mat((90, 70, 50), 4), linha_interna=False)


@atras
def trofeu(tela, ctx, J, modelo, tipo="cranio", cor=(214, 202, 172)):
    """Troféu amarrado às costas: crânio chifrudo de fera ou escudos partidos dos inimigos."""
    H, Q, T_, u, f, au = _base(J)
    c = Q.pt(-0.1 * H, T_ * 0.75)
    if tipo == "cranio":
        osso = Mat(cor, 6, relevo=1.1)
        for s in (-1, 1):                                                   # chifres
            pts = [c + u * 2 + f * s * 2, c + u * 7 - f * 3 + f * s * 4, c + u * 12 - f * 8 + f * s * 3,
                   c + u * 13 - f * 12]
            tela.pintar(tela.corrente(pts, [1.8, 1.5, 1.0, 0.4]), osso.escuro(1 if s < 0 else 0))
        tela.pintar(tela.elipse_girada(c, H * 0.07, H * 0.055, au), osso)
        tela.pintar(tela.capsula(c - u * 2, c - u * 7 - f * 2, H * 0.03, H * 0.02), osso.escuro(1))
        for s in (-1.5, 1.5):
            tela.chapado(tela.circulo(c + f * s + u * 0.5, 1.0), (20, 12, 14))
        tela.traco(c + u * 4, c - u * 6, CORDA, sobre=True)
    else:                                                                    # escudos partidos
        for k, (dx, dy, ang, cor_k) in enumerate(((-0.13, 0.95, 0.5, (120, 30, 30)), (-0.2, 0.6, -0.3, (60, 70, 100)),
                                                  (-0.16, 0.25, 0.15, (90, 90, 60)))):
            cc = Q.pt(dx * H, T_ * dy)
            m, centro = armas.escudo(tela, cc, Mat(cor_k, 6, ruido=0.3), metal((110, 106, 112), ruido=0.3),
                                     larg=6.5, alt=8.5, ang=au + ang, forma="redondo" if k == 1 else "gota")
            fenda = [centro - u * 7 + f * 1, centro - u * 1 - f * 1, centro + u * 2 + f * 1, centro + u * 8 - f * 1]
            tela.tracos(fenda, (16, 10, 14), sobre=True)
        tela.traco(Q.pt(-0.15 * H, T_ * 0.95), Q.pt(0.0, T_ * 0.1), CORDA, sobre=True)


@atras
def aljava_grande(tela, ctx, J, modelo, cor=(92, 60, 42), penas=(200, 196, 180), n=9):
    """Aljava grande e cheia: um leque de flechas emplumadas acima do ombro."""
    H, Q, T_, u, f, au = _base(J)
    a0 = Q.pt(-0.09 * H, T_ * 1.18)
    a1 = Q.pt(-0.03 * H, T_ * 0.0)
    d = norm(a0 - a1)
    for k in range(n):
        a = _ang(d) + (k - n / 2) * 0.07
        p = a0 + dir_ang(a) * (3 + (k % 3) * 2)
        tela.traco(a0, p, (70, 52, 40))
        nrm = v2(-dir_ang(a)[1], dir_ang(a)[0])
        tela.pintar(tela.poly([p, p + dir_ang(a) * 4 + nrm * 1.3, p + dir_ang(a) * 5, p + dir_ang(a) * 4 - nrm * 1.3]),
                    Mat(penas if k % 3 else (150, 30, 34), 4, relevo=0.5), linha_interna=False)
    tela.pintar(tela.capsula(a0, a1, 3.4, 2.4), Mat(cor, 5, ruido=0.2))
    tela.traco(lerp(a0, a1, 0.2) + v2(-2, 0), lerp(a0, a1, 0.2) + v2(2, 0), OURO_VELHO[3], sobre=True)


@atras
def balao(tela, ctx, J, modelo, cor=(170, 24, 30)):
    """Um balão de festa amarrado nas costas, flutuando atrás da cabeça."""
    if not vivo(ctx):
        return
    H, Q, T_, u, f, au = _base(J)
    no = Q.pt(-0.07 * H, T_ * 0.6)
    c = J["topo"] - f * H * 0.18 + u * H * (0.12 + 0.015 * math.sin(ctx.a))
    fio = [no, lerp(no, c, 0.5) - f * 2 * math.sin(ctx.a), c + u * -H * 0.08]
    tela.tracos(fio, (200, 196, 190))
    mat = Mat(cor, 6, relevo=1.2, especular=(255, 230, 230))
    tela.pintar(tela.elipse_girada(c, H * 0.075, H * 0.09, 0.15 * math.sin(ctx.a)), mat)
    tela.pintar(tela.poly([c - u * H * 0.085 - f * 1.2, c - u * H * 0.085 + f * 1.2, c - u * H * 0.11]), mat.escuro(1))


@atras
def gola_alta(tela, ctx, J, modelo, estilo="rigida", cor=(60, 30, 40)):
    """Gola alta que sobe atrás da cabeça (rígida, babado, pele, arminho ou de ossos)."""
    H, Q, T_, u, f, au = _base(J)
    p = J["pescoco"]
    alta = 0.13 if estilo in ("rigida", "osso") else 0.09
    pts = [J["ombro_f"] - f * 2 - u * 1, p - f * H * 0.1 + u * H * alta, p - f * H * 0.02 + u * H * (alta + 0.03),
           p + f * H * 0.05 + u * H * (alta * 0.6), J["ombro_b"] + f * 3 - u * 1, p - u * H * 0.06]
    if estilo == "pele" or estilo == "arminho":
        mat = Mat(cor, 6, ruido=0.8, dither=0.7, relevo=0.8)
        m = tela.pintar(tela.casco(pts + [J["ombro_f"] - f * 4 - u * 4, J["ombro_b"] + f * 5 - u * 3]), mat)
        T.tufos(tela, m, p, (0, -1), comp=2, espaco=2)
        if estilo == "arminho":
            ys, xs = np.nonzero(m & (tela.ruido_base > 0.38))
            for y, x in zip(ys[::3], xs[::3]):
                tela.px(x, y, (20, 18, 22))
                tela.px(x, y + 1, (20, 18, 22))
    elif estilo == "babado":
        mat = Mat(cor, 6, relevo=0.7)
        for k in range(5):
            a = au - 1.3 + k * 0.6
            q = p + dir_ang(a) * H * 0.09 + u * 2
            tela.pintar(tela.elipse_girada(q, H * 0.05, H * 0.03, a), mat if k % 2 else mat.escuro(1))
    elif estilo == "osso":
        tela.pintar(tela.poly(pts), Mat((70, 60, 60), 5))
        for k in range(5):
            a = au - 1.25 + k * 0.32
            b = p + dir_ang(a) * H * 0.05
            tela.pintar(tela.poly([b - dir_ang(a + 1.57) * 1.4, b + dir_ang(a + 1.57) * 1.4, b + dir_ang(a) * H * 0.11]),
                        OSSO)
    else:
        mat = Mat(cor, 6, relevo=0.8)
        tela.pintar(tela.poly(pts), mat)
        tela.traco(pts[1], pts[2], misturar(cor, (255, 220, 160), 0.4), sobre=True)


# ============================================================
# FRENTE: OMBROS, CINTURA, TRONCO E PERNAS
# ============================================================

@frente
def ombreira(tela, ctx, J, modelo, estilo="espinhos", cor=(110, 110, 124), tam=1.0, brilho=None):
    """Ombreira grande no ombro da frente: espinhos, pele, dourada, crânio, brasa, gelo, folhas,
    cogumelos, selos, velas, ferro, couro ou jade."""
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    _ombreira(tela, ctx, J, estilo, cor, tam, brilho)
    _proteger_cabeca(tela, J, antes)


def _proteger_cabeca(tela, J, antes):
    """Devolve a cabeça do herói onde a peça passou por cima (o rosto nunca fica coberto)."""
    alfa, cor, emite, parte = antes
    cabeca = tela.circulo(J["cabeca"], J["P"]["cabeca"] * 0.72) & (alfa > 0)
    tela.alfa[cabeca] = alfa[cabeca]
    tela.cor[cabeca] = cor[cabeca]
    tela.emite[cabeca] = emite[cabeca]
    tela.parte[cabeca] = parte[cabeca]


def _ombreira(tela, ctx, J, estilo, cor, tam, brilho):
    H = J["H"]
    o, u = J["ombro_f"], J["u"]
    f = v2(-u[1], u[0])
    ang = math.atan2(u[1], u[0]) + 1.4
    c = o - u * 0.5 - f * 1.5
    rx, ry = H * 0.075 * tam, H * 0.056 * tam
    concha = tela.elipse_girada(c, rx, ry, ang)
    if estilo in ("espinhos", "ferro", "dourada", "selos", "velas", "jade"):
        mat = Mat(cor, 6, relevo=1.1, especular=(240, 250, 230)) if estilo == "jade" else metal(cor, ruido=0.25 if estilo == "ferro" else 0.0)
        tela.pintar(concha, mat)
        if estilo in ("dourada", "selos"):                                    # lâminas sobrepostas
            for k in (1, 2):
                tela.pintar(tela.elipse_girada(c - u * k * 2.4 - f * k * 0.5, rx * (1 - k * 0.12), ry * 0.7, ang), mat.escuro(k - 1))
        if estilo == "espinhos":
            for k in range(3):
                b = c + u * ry * 0.4 - f * (k - 1) * rx * 0.55
                a = _ang(u) - 0.5 - k * 0.25
                tela.pintar(tela.poly([b - dir_ang(a + 1.57) * 1.6, b + dir_ang(a + 1.57) * 1.6, b + dir_ang(a) * H * 0.07 * tam]),
                            mat.claro(1))
        if estilo == "ferro":
            for k in (-1, 0, 1):
                tela.px(*(c + f * k * rx * 0.55 + u * ry * 0.2), mat[1])
        if estilo == "selos":
            for k, dx in enumerate((-0.4, 0.3)):
                s = c - u * ry * 0.4 + f * rx * dx
                tela.pintar(tela.poly([s, s + v2(1.6, 0), s + v2(1.4, 7 + k * 2), s + v2(0.2, 6 + k * 2)]),
                            Mat((206, 190, 150), 4), linha_interna=False)
                tela.pintar(tela.circulo(s + v2(0.8, 0), 1.5), Mat((150, 20, 26), 4, relevo=0.6))
        if estilo == "velas":
            for k, dx in enumerate((-0.45, 0.05, 0.5)):
                b = c + u * ry * 0.5 + f * rx * dx
                alt = 3.5 + k % 2 * 2
                tela.pintar(tela.capsula(b, b + u * alt, 1.0), Mat((222, 212, 186), 4), linha_interna=False)
                if vivo(ctx):
                    fx.chama(tela, b + u * (alt + 1.5), 3.5 + math.sin(ctx.a * 2 + k), 2.2, fase=ctx.a * 2 + k, brilho=False)
            if vivo(ctx):
                tela.brilho(c + u * ry * 1.6, 8, (255, 190, 100), 0.4)
    elif estilo in ("pele", "couro"):
        mat = Mat(cor, 6, ruido=0.9 if estilo == "pele" else 0.2, dither=0.7, relevo=0.8)
        m = tela.pintar(tela.elipse_girada(c + u * 1, rx * 1.15, ry * 1.2, ang), mat)
        if estilo == "pele":
            T.tufos(tela, m, c, (0, 1), comp=2, espaco=2)
            T.pelagem(tela, m, c, ang=math.pi / 2, comp=2, densidade=0.4)
            for k in range(3):
                g = c - u * ry * 0.9 + f * (k - 1) * rx * 0.45
                tela.pintar(tela.poly([g - v2(0.8, 0), g + v2(0.8, 0), g + v2(0.2, 3.5)]), OSSO.escuro(0), linha_interna=False)
        else:
            for k in (1, 2):
                tela.traco(c - u * k * 2 - f * rx * 0.8, c - u * k * 2 + f * rx * 0.8, mat[1], sobre=True)
    elif estilo == "cranio":
        tela.pintar(concha, Mat((60, 50, 46), 5))
        caveirinha(tela, c + u * ry * 0.35, H * 0.045, OSSO, olhos=brilho or (20, 12, 14), emite=bool(brilho))
    elif estilo == "brasa":
        mat = Mat(cor, 5, ruido=0.4, relevo=1.2)
        m = tela.pintar(tela.elipse_girada(c + u * 1, rx * 1.1, ry * 1.25, ang), mat)
        T.rachaduras(tela, m, c, area=(rx, ry), n=4, passos=4, cor=brilho or (255, 120, 40))
        if vivo(ctx):
            T.particulas(tela, c + u * ry * 2, (rx, 2), brilho or (255, 150, 60), n=3, fase=ctx.a, sobe=8, semente=5)
    elif estilo == "gelo":
        tela.pintar(concha, metal(cor))
        for k in range(4):
            a = _ang(u) - 0.9 + k * 0.45
            fx.cristal(tela, c + u * ry * 0.3 - f * (k - 1.5) * 2, a, H * (0.06 + 0.025 * (k % 2)) * tam, 1.6)
    elif estilo in ("folhas", "cogumelos"):
        musgo = Mat((70, 96, 46), 6, ruido=0.6, dither=0.6)
        m = tela.pintar(tela.elipse_girada(c + u * 1, rx * 1.1, ry * 1.15, ang), musgo)
        T.tufos(tela, m, c, (0, -1), comp=2, espaco=2)
        if estilo == "cogumelos":
            for k, (dx, alt, cor_k) in enumerate(((-0.5, 3, cor), (0.15, 5, cor), (0.6, 2.5, (200, 190, 160)))):
                b = c + u * ry * 0.6 + f * rx * dx
                tela.pintar(tela.capsula(b, b + u * alt, 0.7), Mat((210, 200, 180), 4), linha_interna=False)
                tela.pintar(tela.elipse_girada(b + u * (alt + 0.8), 2.4 - k * 0.3, 1.4, _ang(u) + 1.57),
                            Mat(cor_k, 5, relevo=0.8))
        else:
            for k in range(4):
                a = _ang(u) - 1.0 + k * 0.6
                p = c + dir_ang(a) * rx * 0.95
                tela.pintar(tela.elipse_girada(p, 2.4, 1.1, a), Mat(cor, 5, relevo=0.6), linha_interna=False)


ITENS_DE_CINTO = ("cranio", "frasco", "livro", "bolsa", "cutelo", "gancho", "lanterna", "sino", "mascara", "boneco",
                  "cabaca", "berrante", "filacterio", "garras", "incensario", "caldeirao", "bainha", "faca", "chave",
                  "pergaminho", "chocalho")


def _item_de_cinto(tela, ctx, J, item, p, cor, i):
    """Um item pendurado no cinto, com o topo em p."""
    H = J["H"]
    s = math.sin(ctx.a + i)
    if item == "cranio":
        tela.traco(p, p + v2(0, 2), CORDA)
        caveirinha(tela, p + v2(0, 4), 2.1, OSSO)
    elif item == "frasco":
        tela.pintar(tela.capsula(p, p + v2(0, 1.5), 0.7), Mat((150, 140, 130), 3), linha_interna=False)
        tela.chapado(tela.circulo(p + v2(0, 3.6), 2.0), cor or (90, 200, 80), emite=True)
        tela.px(p[0] - 0.6, p[1] + 3, (240, 255, 230), emite=True)
    elif item == "livro":
        tela.tracos([p, p + v2(-1, 2), p + v2(0, 4)], (120, 120, 130))
        c = p + v2(0, 7)
        tela.pintar(tela.poly([c + v2(-3.5, -3.5), c + v2(3.5, -3), c + v2(3.5, 4), c + v2(-3.5, 3.5)]),
                    Mat(cor or (90, 40, 40), 5, relevo=0.8))
        tela.chapado(tela.poly([c + v2(2.6, -2.6), c + v2(3.8, -2.4), c + v2(3.8, 3.2), c + v2(2.6, 3.0)]), (220, 208, 180))
        tela.pintar(tela.circulo(c, 1.1), OURO_VELHO)
    elif item == "bolsa":
        tela.pintar(tela.elipse(p[0], p[1] + 3, 2.6, 3.0), Mat(cor or (110, 76, 50), 5, ruido=0.2))
        tela.traco(p + v2(-2, 1), p + v2(2, 1), COURO_ESC[1], sobre=True)
    elif item == "cutelo":
        tela.pintar(tela.capsula(p, p + v2(0.5, 3), 0.9), MADEIRA)
        lam = [p + v2(-1, 3), p + v2(4, 3), p + v2(4.5, 10), p + v2(-1, 9)]
        m = tela.pintar(tela.poly(lam), metal((150, 150, 160)))
        tela.chapado(m & (tela.ruido_base > 0.1), SANGUE)
    elif item == "gancho":
        tela.traco(p, p + v2(0, 3), (120, 120, 130))
        tela.pintar(tela.corrente([p + v2(0, 3), p + v2(0, 7), p + v2(2.5, 8.5), p + v2(3.5, 6.5)], [0.9, 0.9, 0.8, 0.5]),
                    metal((140, 136, 140)))
    elif item == "lanterna":
        tela.traco(p, p + v2(0, 2), CORDA)
        tela.pintar(tela.poly([p + v2(-2.5, 2), p + v2(2.5, 2), p + v2(2, 8), p + v2(-2, 8)]), metal((90, 86, 92)))
        tela.chapado(tela.poly([p + v2(-1.2, 3.2), p + v2(1.2, 3.2), p + v2(1, 7), p + v2(-1, 7)]), cor or (255, 200, 110),
                     emite=True)
        tela.brilho(p + v2(0, 5), 9, cor or (255, 200, 110), 0.45 + 0.1 * math.sin(ctx.a * 2))
    elif item in ("sino", "chocalho"):
        tela.traco(p, p + v2(0, 1.5), CORDA)
        tela.pintar(tela.poly([p + v2(-1.8, 4.5), p + v2(-1.2, 1.5), p + v2(1.2, 1.5), p + v2(1.8, 4.5)]),
                    metal(cor or (200, 160, 70)))
        tela.px(p[0], p[1] + 5, (40, 30, 20))
    elif item == "mascara":
        c = p + v2(0, 4)
        tela.pintar(tela.elipse(c[0], c[1], 3.0, 3.6), Mat(cor or (222, 214, 200), 6, relevo=1.0))
        for dx in (-1.2, 1.2):
            tela.chapado(tela.circulo(c + v2(dx, -0.6), 0.7), (20, 12, 20))
        tela.tracos([c + v2(-1.4, 1.6), c + v2(0, 2.3), c + v2(1.4, 1.6)], (120, 30, 40))
    elif item == "boneco":
        tela.traco(p, p + v2(0, 1.5), CORDA)
        c = p + v2(0, 3.5)
        pano = Mat(cor or (150, 130, 100), 5, ruido=0.4)
        tela.pintar(tela.circulo(c, 1.8) | tela.capsula(c + v2(0, 2), c + v2(0, 6), 1.6) |
                    tela.capsula(c + v2(-2.5, 3), c + v2(2.5, 3), 0.7) | tela.capsula(c + v2(0, 5.5), c + v2(-1.5, 8), 0.6) |
                    tela.capsula(c + v2(0, 5.5), c + v2(1.5, 8), 0.6), pano)
        tela.px(c[0] - 0.6, c[1], (20, 10, 10))
        tela.px(c[0] + 0.7, c[1], (20, 10, 10))
        tela.traco(c + v2(1.5, 2.5), c + v2(-1, 4.5), (200, 200, 210))           # alfinete
    elif item == "cabaca":
        tela.traco(p, p + v2(0, 1.5), CORDA)
        mat = Mat(cor or (170, 130, 60), 5, relevo=1.1)
        tela.pintar(tela.circulo(p + v2(0, 3), 1.8) | tela.circulo(p + v2(0, 6.5), 2.8), mat)
    elif item == "berrante":
        tela.pintar(tela.corrente([p + v2(-3, 2), p + v2(1, 3.5), p + v2(4, 2), p + v2(5, -1.5)], [2.0, 1.6, 1.1, 0.6]),
                    Mat(cor or (200, 186, 150), 6, relevo=1.0))
        tela.traco(p + v2(-1, 1.5), p + v2(-1, 4.5), OURO_VELHO[3], sobre=True)
    elif item == "filacterio":
        tela.traco(p, p + v2(0, 2), (120, 120, 130))
        tela.pintar(tela.poly([p + v2(0, 2), p + v2(2.2, 4.5), p + v2(0, 8), p + v2(-2.2, 4.5)]),
                    Mat(cor or (120, 240, 220), 5, relevo=1.0, especular=(240, 255, 250)))
        tela.brilho(p + v2(0, 5), 8, cor or (120, 240, 220), 0.5 + 0.15 * math.sin(ctx.a * 2))
    elif item == "garras":
        tela.traco(p + v2(-3, 0), p + v2(3, 0), CORDA)
        for k in (-2, 0, 2):
            q = p + v2(k, 0.5)
            tela.pintar(tela.corrente([q, q + v2(0.3, 2.5), q + v2(1.2, 4)], [0.9, 0.7, 0.3]), OSSO, linha_interna=False)
    elif item == "incensario":
        tela.tracos([p, p + v2(0.5 * s, 3)], (120, 104, 70))
        c = p + v2(0.5 * s, 5)
        tela.pintar(tela.circulo(c, 2.4) | tela.poly([c + v2(-1.5, -1.5), c + v2(1.5, -1.5), c + v2(0, -3.5)]),
                    metal((90, 110, 80)))
        tela.px(c[0], c[1], cor or (140, 255, 120), emite=True)
        if vivo(ctx):
            fx.fumaca(tela, c - v2(0, 3), 2.0, cor=misturar(cor or (140, 255, 120), (60, 70, 50), 0.6), fase=ctx.a, n=3, sobe=12)
    elif item == "caldeirao":
        tela.traco(p, p + v2(0, 2), (100, 100, 110))
        c = p + v2(0, 5)
        tela.pintar(tela.elipse(c[0], c[1], 3.2, 2.6) | tela.capsula(c + v2(-3.4, -2), c + v2(3.4, -2), 0.8), metal((70, 70, 80)))
        tela.chapado(tela.elipse(c[0], c[1] - 2, 2.4, 0.8), cor or (120, 220, 90), emite=True)
    elif item == "bainha":
        a = 2.2                                                              # rapieira pendurada na diagonal
        d = dir_ang(a)
        tela.pintar(tela.capsula(p - d * 2, p + d * H * 0.36, 1.1, 0.8), Mat(cor or (60, 40, 34), 5, relevo=0.8))
        tela.pintar(tela.circulo(p - d * 3, 2.2), OURO_VELHO)
        tela.pintar(tela.capsula(p - d * 3 - v2(0, 3), p - d * 6, 0.7), COURO_ESC)
    elif item == "faca":
        tela.pintar(tela.capsula(p, p + v2(0, 2.5), 0.8), COURO_ESC)
        tela.pintar(tela.poly([p + v2(-0.9, 2.5), p + v2(0.9, 2.5), p + v2(0.2, 8)]), metal(cor or (170, 170, 186)))
    elif item == "chave":
        tela.traco(p, p + v2(0, 1.5), CORDA)
        mat = metal(cor or (170, 132, 62))
        tela.pintar(tela.circulo(p + v2(0, 3), 1.5) | tela.capsula(p + v2(0, 4), p + v2(0, 8.5), 0.6) |
                    tela.capsula(p + v2(0, 8), p + v2(1.6, 8), 0.5), mat)
    elif item == "pergaminho":
        tela.pintar(tela.poly([p + v2(-1.5, 0), p + v2(1.5, 0), p + v2(1.2 + s * 0.3, 8), p + v2(-1.2 + s * 0.3, 7)]),
                    Mat(cor or (210, 196, 160), 5, relevo=0.5))
        tela.pintar(tela.circulo(p + v2(0, 0.5), 1.4), Mat((150, 20, 26), 4))


@frente
def cintura(tela, ctx, J, modelo, itens=("bolsa",), cores=None, altura=0.0):
    """Itens pendurados no cinto (veja ITENS_DE_CINTO), da frente para trás."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    xs = np.linspace(0.07, -0.08, max(2, len(itens)))[:len(itens)] if len(itens) > 1 else [0.06]
    for i, (item, x) in enumerate(zip(itens, xs)):
        cor = cores[i] if cores and i < len(cores) else None
        _item_de_cinto(tela, ctx, J, item, Q.pt(x * H, (altura - 0.015) * H), cor, i)
    _devolver_braco(tela, J, antes)


def _devolver_braco(tela, J, antes):
    """Desfaz o que foi pintado por cima do braço da frente (o braço continua na frente)."""
    alfa, cor, emite, parte = antes
    braco = braco_da_frente(tela, J) & (alfa > 0)
    tela.alfa[braco] = alfa[braco]
    tela.cor[braco] = cor[braco]
    tela.emite[braco] = emite[braco]
    tela.parte[braco] = parte[braco]


@frente
def bandoleira(tela, ctx, J, modelo, itens="facas", cor=(70, 46, 34), cor_item=None, n=5):
    """Correia na diagonal do peito com facas, frascos, estacas, dentes, cartas ou velas."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    a, b = Q.pt(-0.06 * H, T_ * 0.98), Q.pt(0.075 * H, T_ * 0.05)
    tela.pintar(tela.capsula(a, b, 1.3), Mat(cor, 5, ruido=0.2), linha_interna=True)
    for k in range(n):
        p = lerp(a, b, 0.18 + k * 0.66 / max(1, n - 1))
        if itens == "facas":
            tela.pintar(tela.capsula(p - u * 1.5, p + u * 0.5, 0.7), COURO_ESC, linha_interna=False)
            tela.pintar(tela.poly([p + u * 0.5 - f * 0.8, p + u * 0.5 + f * 0.8, p + u * 5]), metal(cor_item or (190, 190, 204)))
        elif itens == "frascos":
            tela.chapado(tela.circulo(p, 1.4), cor_item or (90, 200, 80), emite=True)
            tela.px(*(p + u * 1.8), (150, 140, 130))
        elif itens == "estacas":
            tela.pintar(tela.poly([p - f * 0.9 - u * 1, p + f * 0.9 - u * 1, p + u * 5]), Mat(cor_item or (190, 196, 210), 5),
                        linha_interna=False)
        elif itens == "dentes":
            tela.pintar(tela.poly([p - f * 0.8, p + f * 0.8, p - u * 3]), OSSO, linha_interna=False)
        elif itens == "cartas":
            tela.pintar(tela.poly([p - f * 1.2 - u * 1.5, p + f * 1.2 - u * 1.5, p + f * 1.2 + u * 1.8, p - f * 1.2 + u * 1.8]),
                        Mat((230, 224, 210), 4), linha_interna=False)
            tela.px(*p, cor_item or (170, 20, 30))
        elif itens == "velas":
            tela.pintar(tela.capsula(p, p + u * 2.5, 0.8), Mat((222, 212, 186), 4), linha_interna=False)
            tela.px(*(p + u * 3.5), (255, 200, 110), emite=True)
    _devolver_braco(tela, J, antes)


@frente
def pteruges(tela, ctx, J, modelo, cor=(120, 70, 40), comp=0.15, metal_cor=None, rasgado=False):
    """Saiote de tiras penduradas no cinto (gladiador; de lâminas, se metal_cor)."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    mat = metal(metal_cor) if metal_cor else Mat(cor, 5, ruido=0.3, relevo=0.7)
    for k in range(7):
        x = (-0.09 + k * 0.03) * H
        topo = Q.pt(x, 0.025 * H)
        c = comp * (0.75 + 0.25 * ((k * 7) % 3) / 2) if rasgado else comp
        fim = Q.pt(x + 0.01 * H * math.sin(ctx.a + k), -c * H)
        tela.pintar(tela.capsula(topo, fim, 1.25, 1.1 if not rasgado else 0.6), mat if k % 2 else mat.escuro(1))
        if metal_cor:
            tela.px(*lerp(topo, fim, 0.2), mat[6])
    tela.pintar(tela.capsula(Q.pt(-0.095 * H, 0.03 * H), Q.pt(0.09 * H, 0.03 * H), 1.5), Mat((60, 40, 34), 5))
    _devolver_braco(tela, J, antes)


@frente
def manica(tela, ctx, J, modelo, cor=(160, 160, 176)):
    """Braçal de lâminas segmentadas cobrindo o braço da frente (gladiador)."""
    S = J["P"]
    mat = metal(cor)
    o, c, m = J["ombro_f"], J["cotovelo_f"], J["mao_f"]
    pts = [lerp(o, c, t) for t in (0.0, 0.35, 0.7)] + [lerp(c, m, t) for t in (0.05, 0.4, 0.72)]
    for k, p in enumerate(pts):
        r = (S["l_braco"] if k < 3 else S["l_antebraco"]) * (1.35 - k * 0.03)
        tela.pintar(tela.circulo(p, r), mat if k % 2 == 0 else mat.escuro(1))


@frente
def avental(tela, ctx, J, modelo, cor=(170, 160, 140), sangue=True):
    """Avental de açougueiro do peito até a canela, manchado de sangue."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    s = math.sin(ctx.a) * 0.6
    pts = Q.pts([(-0.05 * H, T_ * 0.85), (0.075 * H, T_ * 0.85), (0.1 * H, T_ * 0.2), (0.13 * H + s, -0.32 * H),
                 (0.0 + s, -0.34 * H), (-0.08 * H, -0.3 * H), (-0.07 * H, T_ * 0.2)])
    m = tela.pintar(tela.poly(pts), Mat(cor, 6, desce=0.3, ruido=0.2, relevo=0.7))
    if sangue:
        T.manchas(tela, m, Q.o, SANGUE, escala=3, quantidade=0.35, forca=0.85, semente=7)
        T.escorrer(tela, m, Q.o, (90, 8, 18), densidade=0.25, comp=4, fase=ctx.a, semente=8)
    tela.traco(Q.pt(-0.05 * H, T_ * 0.85), J["pescoco"] - u * 1, CORDA, sobre=False)
    _devolver_braco(tela, J, antes)


@frente
def tabardo_longo(tela, ctx, J, modelo, cor=(200, 190, 160), emblema="cruz", cor_emblema=(150, 24, 30)):
    """Tabardo comprido do peito às canelas, com emblema bordado."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    s = math.sin(ctx.a) * 0.5
    pts = Q.pts([(-0.045 * H, T_ * 0.95), (0.06 * H, T_ * 0.95), (0.07 * H, -0.05 * H), (0.085 * H + s, -0.38 * H),
                 (0.03 * H + s, -0.34 * H), (-0.02 * H + s, -0.4 * H), (-0.06 * H, -0.36 * H)])
    m = tela.pintar(tela.poly(pts), Mat(cor, 6, desce=0.35, ruido=0.12, relevo=0.6))
    c = Q.pt(0.012 * H, T_ * 0.45)
    if emblema == "cruz":
        tela.pintar(tela.capsula(c + u * 5, c - u * 6, 1.0) | tela.capsula(c - f * 3.5 + u * 2, c + f * 3.5 + u * 2, 1.0),
                    Mat(cor_emblema, 5, relevo=0.5), linha_interna=False)
    elif emblema == "martelo":
        tela.pintar(tela.capsula(c + u * 4, c - u * 6, 0.8) | tela.poly([c + u * 5 - f * 3, c + u * 5 + f * 3, c + u * 2 + f * 3,
                                                                          c + u * 2 - f * 3]),
                    Mat(cor_emblema, 5, relevo=0.5), linha_interna=False)
    tela.traco(Q.pt(-0.045 * H, T_ * 0.95), Q.pt(-0.06 * H, -0.36 * H), misturar(cor, OURO_VELHO[3], 0.5), sobre=True)
    _devolver_braco(tela, J, antes)


@frente
def raizes(tela, ctx, J, modelo, cor=(84, 60, 44), n=4, flores=None):
    """Raízes que descem da cintura e se enroscam nas pernas até o chão."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    mat = Mat(cor, 5, ruido=0.3, relevo=0.9)
    for k in range(n):
        p = Q.pt((-0.07 + k * 0.045) * H, 0.0)
        pts = [p]
        lado = "f" if k % 2 else "b"
        for t in (0.35, 0.7, 1.0):
            alvo = lerp(J["joelho_" + lado], J["tornozelo_" + lado], max(0.0, t - 0.35) / 0.65) if t > 0.35 else J["joelho_" + lado]
            pts.append(lerp(p, alvo, t) + v2(math.sin(t * 7 + k) * 2.2, 0))
        tela.pintar(tela.corrente(pts, [1.3, 1.1, 0.8, 0.5]), mat if k % 2 else mat.escuro(1))
        if flores:
            tela.px(*pts[1], flores)
    _devolver_braco(tela, J, antes)


@frente
def contas_grandes(tela, ctx, J, modelo, cor=(96, 60, 40), borla=(170, 30, 30)):
    """Rosário de contas enormes no pescoço, com borla."""
    H, Q, T_, u, f, au = _base(J)
    antes = tela.alfa.copy(), tela.cor.copy(), tela.emite.copy(), tela.parte.copy()
    mat = Mat(cor, 5, relevo=1.2, especular=misturar(cor, (255, 240, 200), 0.6))
    pts = []
    for k in range(9):
        t = k / 8
        p = lerp(J["ombro_b"], J["ombro_f"], 0.05 + t * 0.9) - u * (1 + 9 * math.sin(t * math.pi))
        pts.append(p)
        tela.pintar(tela.circulo(p, 1.9), mat)
    fundo = pts[4] - u * 3
    tela.pintar(tela.circulo(fundo, 2.2), mat.claro(1))
    tela.pintar(tela.poly([fundo - u * 1.5 - f * 1.5, fundo - u * 1.5 + f * 1.5, fundo - u * 6 + f * 2, fundo - u * 6 - f * 2]),
                Mat(borla, 4, ruido=0.4), linha_interna=False)
    _devolver_braco(tela, J, antes)


@frente
def familiar(tela, ctx, J, modelo, tipo="corvo", cor=(40, 38, 52), olhos=(255, 60, 40)):
    """Bichinho de estimação no ombro de trás: corvo, gato ou sapo."""
    if ctx.anim == "morte" and ctx.i >= 1:
        return
    H, Q, T_, u, f, au = _base(J)
    c = J["ombro_f"] + u * 3 - f * H * 0.08
    s = math.sin(ctx.a)
    mat = Mat(cor, 6, relevo=0.9, ruido=0.2, especular=misturar(cor, (200, 220, 255), 0.5) if tipo == "corvo" else None)
    if tipo == "corvo":
        corpo = tela.elipse_girada(c + u * 2, 3.2, 2.2, au + 1.3)
        cab = c + u * 4.5 + f * 2.5
        tela.pintar(corpo | tela.circulo(cab, 1.9) | tela.poly([c + u * 1 - f * 2, c - f * 7 + u * (0.5 + s * 0.4),
                                                                 c - f * 6.5 + u * 2.5]), mat)
        tela.pintar(tela.poly([cab + f * 1.3 + u * 0.4, cab + f * 4.2 - u * 0.6, cab + f * 1.2 - u * 0.8]), Mat((50, 44, 40), 3),
                    linha_interna=False)
        tela.px(*(cab + f * 0.6 + u * 0.4), olhos, emite=True)
    elif tipo == "gato":
        corpo = tela.elipse_girada(c + u * 2, 3.6, 2.6, au + 1.5)
        cab = c + u * 4.6 + f * 2.2
        orelhas = tela.poly([cab + u * 1 - f * 1.8, cab + u * 3.6 - f * 1.2, cab + u * 1.4]) | \
            tela.poly([cab + u * 1 + f * 1.8, cab + u * 3.6 + f * 1.4, cab + u * 1.4])
        cauda = tela.corrente([c - f * 3, c - f * 5 - u * 1, c - f * 6 - u * (4 + s), c - f * 4.5 - u * (7 + s)], [1.0, 0.9, 0.8, 0.6])
        tela.pintar(corpo | tela.circulo(cab, 2.2) | orelhas | cauda, mat)
        tela.px(*(cab + f * 0.8 + u * 0.3), olhos, emite=True)
        tela.px(*(cab + f * 1.8 + u * 0.3), olhos, emite=True)
    else:                                                                    # sapo
        cab = c + u * 2.6 + f * 1.5
        tela.pintar(tela.elipse(c[0], c[1] - 1.5, 3.4, 2.4) | tela.circulo(cab, 2.0), mat)
        for dx in (-1, 1.2):
            q = cab + u * 1.8 + f * dx
            tela.pintar(tela.circulo(q, 1.0), mat.claro(1), linha_interna=False)
            tela.px(*q, olhos, emite=True)
        tela.traco(cab + f * 0.2 - u * 0.5, cab + f * 2.2 - u * 0.4, mat[0], sobre=True)


@frente
def particulas(tela, ctx, J, modelo, tipo="brasas", cor=None, n=10):
    """Partículas em volta do herói: brasas, neve, faíscas, pétalas, moscas, gotas, folhas, notas,
    vaga-lumes ou estrelas. Ficam só fora do corpo (não sujam a roupa)."""
    if not vivo(ctx):
        return
    H, Q, T_, u, f, au = _base(J)
    centro = Q.pt(-0.02 * H, T_ * 0.6)
    area = (H * 0.24, H * 0.32)
    rng = np.random.default_rng(len(tipo) * 31 + n)
    padrao = {"brasas": (255, 140, 50), "neve": (225, 240, 255), "faiscas": (230, 230, 255), "petalas": (250, 180, 210),
              "moscas": (34, 30, 30), "gotas": (150, 20, 30), "folhas": (150, 110, 50), "notas": (230, 200, 120),
              "vagalumes": (210, 255, 120), "estrelas": (230, 230, 255), "cinzas": (110, 104, 104)}
    cor = cor or padrao.get(tipo, (255, 255, 255))
    sobe = {"neve": -12, "petalas": -8, "folhas": -9, "gotas": -10, "moscas": 0, "notas": 9}.get(tipo, 12)
    for i in range(n):
        x0, y0 = rng.uniform(-1, 1) * area[0], rng.uniform(-1, 1) * area[1]
        t = (ctx.t + rng.random()) % 1
        if tipo == "moscas":
            p = centro + v2(x0 + math.cos(t * 2 * math.pi * 2 + i) * 4, y0 + math.sin(t * 2 * math.pi * 3 + i) * 3)
        else:
            p = centro + v2(x0 + math.sin(t * 2 * math.pi + i) * 2.5, y0 - t * sobe)
        x, y = int(round(p[0])), int(round(p[1]))
        if not (0 <= x < tela.w - 2 and 0 <= y < tela.h - 2) or tela.alfa[y, x] > 0:
            continue
        if tipo == "notas":
            from .acampamento import nota_musical
            if i % 3 == 0:
                nota_musical(tela, p, cor if i % 2 else misturar(cor, (190, 120, 255), 0.6))
        elif tipo in ("petalas", "folhas"):
            tela.px(x, y, cor)
            tela.px(x + 1, y, misturar(cor, (40, 30, 30), 0.3))
        elif tipo == "moscas":
            tela.px(x, y, cor)
            tela.px(x, y - 1, (170, 180, 200))
        elif tipo == "gotas":
            fx.gota_sangue(tela, p, cor)
        elif tipo in ("vagalumes", "estrelas", "faiscas", "brasas"):
            tela.px(x, y, misturar(cor, (40, 20, 30), max(0.0, t - 0.6) * 1.5), emite=True)
            if tipo in ("vagalumes", "estrelas"):
                tela.brilho(p, 3, cor, 0.5 * (1 - t))
            if tipo == "estrelas" and i % 2:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    tela.px(x + dx, y + dy, misturar(cor, (40, 40, 80), 0.5), emite=True)
        else:
            tela.px(x, y, cor)


@frente
def orbes(tela, ctx, J, modelo, tipo="cristal", cor=(150, 220, 255), n=3, raio=0.27):
    """Objetos girando em volta do herói (crânios, cristais, gotas, pedras rúnicas, olhos, espíritos,
    facas ou contas de jade). Atrás do corpo só aparecem em volta da silhueta."""
    if not vivo(ctx):
        return
    H, Q, T_, u, f, au = _base(J)
    centro = Q.pt(0.0, T_ * 0.7)
    for k in range(n):
        a = ctx.a + k * 2 * math.pi / n
        p = centro + f * math.cos(a) * H * raio + u * (math.sin(a * 2) * 3 + math.sin(a) * H * 0.06)
        atras_do_corpo = math.sin(a) < 0
        guarda = (tela.alfa.copy(), tela.cor.copy(), tela.emite.copy()) if atras_do_corpo else None
        if tipo == "cranio":
            caveirinha(tela, p, 2.2, OSSO, olhos=cor, emite=True)
            tela.brilho(p, 6, cor, 0.35)
        elif tipo == "cristal":
            fx.cristal(tela, p + u * 3, au + math.pi, 7, 1.8)
        elif tipo == "gota":
            tela.pintar(tela.circulo(p, 1.8) | tela.poly([p - f * 1.4, p + f * 1.4, p + u * 4]),
                        Mat(cor, 5, relevo=1.2, especular=(255, 200, 200)))
        elif tipo == "pedra":
            tela.pintar(tela.poly([p + v2(-2.5, -2), p + v2(2, -2.8), p + v2(2.8, 2), p + v2(-2, 2.6)]), Mat((90, 92, 104), 5, ruido=0.4))
            fx.runa(tela, p, cor, 1, forma=k)
        elif tipo == "olho":
            tela.pintar(tela.circulo(p, 2.4), Mat((222, 214, 206), 5, relevo=1.1))
            tela.chapado(tela.circulo(p + f * 0.8, 1.1), cor, emite=True)
            tela.px(*(p + f * 1.0), (10, 6, 10))
        elif tipo == "espirito":
            tela.vidro(tela.circulo(p, 2.4) | tela.poly([p - f * 2, p + f * 2, p - f * 5 - u * 1 * math.sin(ctx.a)]),
                       Mat(cor, 5, relevo=0.4), 0.6)
            tela.brilho(p, 7, cor, 0.4)
        elif tipo == "faca":
            ang = a * 2
            d = dir_ang(ang)
            armas.adaga(tela, p - d * 4, ang, 9, metal((200, 200, 214)), COURO_ESC, larg=1.0)
        elif tipo == "jade":
            tela.pintar(tela.circulo(p, 1.9), Mat(cor, 5, relevo=1.2, especular=(230, 255, 240)))
            tela.brilho(p, 5, cor, 0.3)
        if atras_do_corpo:                                                   # o corpo continua por cima
            alfa, cor_antes, emite = guarda
            cobre = alfa > 0
            tela.alfa[cobre] = alfa[cobre]
            tela.cor[cobre] = cor_antes[cobre]
            tela.emite[cobre] = emite[cobre]
