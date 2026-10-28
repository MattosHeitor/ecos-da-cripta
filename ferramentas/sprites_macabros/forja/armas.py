"""Armas e efeitos de golpe."""
import math

import numpy as np

from .motor import dir_ang, norm, v2, lerp, misturar, rgb


def _eixos(ang):
    d = dir_ang(ang)
    n = np.array([-d[1], d[0]])
    return d, n


def espada(tela, mao, ang, comp, lamina, guarda, cabo, larg=1.6, ponta=0.18, pomo=None, sangue=0.0,
           guarda_larg=4.5, curva=0.0):
    d, n = _eixos(ang)
    mao = v2(mao)
    base = mao + d * 2.2
    fim = mao + d * comp
    # cabo
    tela.pintar(tela.capsula(mao - d * 3.2, mao + d * 1.5, 1.0), cabo)
    if pomo is not None:
        tela.pintar(tela.circulo(mao - d * 4.0, 1.4), pomo)
    # lâmina
    meio = lerp(base, fim, 1 - ponta)
    off = n * curva
    pts = [base + n * larg, meio + n * larg + off, fim + off * 1.3, meio - n * larg * 0.8 + off, base - n * larg]
    m = tela.poly(pts)
    tela.pintar(m, lamina)
    # sulco central (fuller)
    tela.traco(base + d * 1.5, lerp(base, meio, 0.85), lamina[len(lamina.cores) - 2], sobre=True)
    if sangue:
        t0 = 1 - sangue
        a = lerp(base, fim, t0)
        ms = tela.poly([a + n * larg, meio + n * larg, fim, meio - n * larg, a - n * larg]) & m
        tela.chapado(ms & (tela.ruido_base > -0.15), (105, 12, 22))
    # guarda
    tela.pintar(tela.capsula(base - n * guarda_larg - d * 0.3, base + n * guarda_larg - d * 0.3, 1.1), guarda)
    return m


def adaga(tela, mao, ang, comp, lamina, cabo, larg=1.2, reversa=False):
    if reversa:
        ang += math.pi
    d, n = _eixos(ang)
    mao = v2(mao)
    tela.pintar(tela.capsula(mao - d * 1.8, mao + d * 1.2, 0.9), cabo)
    base = mao + d * 1.6
    fim = mao + d * comp
    m = tela.poly([base + n * larg, lerp(base, fim, 0.55) + n * larg * 1.1, fim, base - n * larg * 0.6])
    tela.pintar(m, lamina)
    tela.pintar(tela.capsula(base - n * 2.4, base + n * 2.4, 0.8), cabo.claro(1))
    return m


def haste(tela, mao, ang, antes, depois, mat, larg=1.0):
    d, _ = _eixos(ang)
    mao = v2(mao)
    a, b = mao - d * antes, mao + d * depois
    tela.pintar(tela.capsula(a, b, larg), mat)
    return a, b


def machado(tela, mao, ang, comp, cabo, lamina, duplo=False, tam=1.0, sangue=False):
    d, n = _eixos(ang)
    a, topo = haste(tela, mao, ang, 4, comp, cabo, 1.1)
    c = topo - d * 3 * tam
    t = tam
    pts = [c + n * 1, c + n * 5 * t + d * 4 * t, c + n * 9 * t + d * 6 * t, c + n * 10 * t, c + n * 9 * t - d * 7 * t,
           c + n * 5 * t - d * 5 * t, c + n * 1 - d * 3]
    m = tela.poly(pts)
    if duplo:
        pts2 = [c - n * 1, c - n * 5 * t + d * 4 * t, c - n * 9 * t + d * 6 * t, c - n * 10 * t,
                c - n * 9 * t - d * 7 * t, c - n * 5 * t - d * 5 * t, c - n * 1 - d * 3]
        m |= tela.poly(pts2)
    tela.pintar(m, lamina)
    # fio
    tela.traco(c + n * 9 * t + d * 5 * t, c + n * 9 * t - d * 6 * t, lamina[len(lamina.cores) - 1], sobre=True)
    if sangue:
        ms = m & tela.poly([c + n * 6 * t + d * 6 * t, c + n * 11 * t + d * 6 * t, c + n * 11 * t - d * 2 * t,
                            c + n * 6 * t])
        tela.chapado(ms & (tela.ruido_base > -0.2), (100, 10, 20))
    tela.pintar(tela.capsula(c - d * 3.5, c + d * 3.5, 1.4), cabo.escuro(1))
    return m


def martelo(tela, mao, ang, comp, cabo, cabeca, tam=1.0, espinhos=False, mat_esp=None):
    d, n = _eixos(ang)
    a, topo = haste(tela, mao, ang, 4, comp, cabo, 1.1)
    c = topo - d * 2 * tam
    w, h = 9 * tam, 5.5 * tam
    pts = [c - n * w + d * h, c + n * w + d * h, c + n * w - d * h, c - n * w - d * h]
    m = tela.poly(pts)
    tela.pintar(m, cabeca)
    tela.pintar(tela.poly([c - n * (w + 1) + d * (h - 1.5), c - n * (w + 1) - d * (h - 1.5),
                           c - n * (w - 1.5) - d * (h - 1.5), c - n * (w - 1.5) + d * (h - 1.5)]), cabeca.escuro(1))
    tela.pintar(tela.poly([c + n * (w + 1) + d * (h - 1.5), c + n * (w + 1) - d * (h - 1.5),
                           c + n * (w - 1.5) - d * (h - 1.5), c + n * (w - 1.5) + d * (h - 1.5)]), cabeca.escuro(1))
    if espinhos:
        for s in (-1, 1):
            b = c + n * s * (w + 1)
            tela.pintar(tela.poly([b + d * 2, b - d * 2, b + n * s * 4]), mat_esp or cabeca)
        tela.pintar(tela.poly([c + d * (h + 0.5) - n * 2, c + d * (h + 0.5) + n * 2, c + d * (h + 5)]),
                    mat_esp or cabeca)
    return m


def maca(tela, mao, ang, comp, cabo, cabeca, raio=4.0, cravos=7):
    d, n = _eixos(ang)
    a, topo = haste(tela, mao, ang, 3.5, comp, cabo, 1.0)
    c = topo
    pts = []
    for i in range(cravos * 2):
        r = raio * (1.55 if i % 2 == 0 else 0.95)
        t = i * math.pi / cravos + ang
        pts.append(c + v2(math.cos(t), math.sin(t)) * r)
    tela.pintar(tela.poly(pts), cabeca)
    tela.pintar(tela.circulo(c, raio * 0.95), cabeca)
    return c


def mangual(tela, mao, ang, cabo, corrente, bola, comp_cabo=8, comp_corr=14, oscila=0.0, raio=3.5):
    d, n = _eixos(ang)
    a, topo = haste(tela, mao, ang, 3, comp_cabo, cabo, 1.0)
    d2 = dir_ang(ang + oscila)
    fim = topo + d2 * comp_corr
    for k in range(int(comp_corr // 2.2) + 1):
        p = lerp(topo, fim, k / max(1, int(comp_corr // 2.2)))
        tela.px(p[0], p[1], corrente[3 + (k % 2)])
    pts = []
    for i in range(16):
        r = raio * (1.6 if i % 2 == 0 else 1.0)
        t = i * math.pi / 8
        pts.append(fim + v2(math.cos(t), math.sin(t)) * r)
    tela.pintar(tela.poly(pts), bola)
    return fim


def lanca(tela, mao, ang, comp, cabo, ponta, atras=14, larg_ponta=2.3, gancho=False):
    d, n = _eixos(ang)
    a, topo = haste(tela, mao, ang, atras, comp, cabo, 0.9)
    m = tela.poly([topo - d * 1 + n * larg_ponta, topo + d * 8, topo - d * 1 - n * larg_ponta, topo - d * 3])
    if gancho:
        m |= tela.poly([topo - d * 2, topo - d * 1 - n * 5, topo + d * 2 - n * 6, topo - d * 0.5 - n * 2])
    tela.pintar(m, ponta)
    return topo


def foice(tela, mao, ang, comp, cabo, lamina, tam=1.0):
    d, n = _eixos(ang)
    a, topo = haste(tela, mao, ang, 6, comp, cabo, 1.0)
    pts = []
    for i in range(9):
        t = i / 8
        ang_l = math.pi * 0.95 * t
        r = 14 * tam
        p = topo + (-n * math.sin(ang_l) * r) + d * (math.cos(ang_l) * r * 0.45 - r * 0.45 + 0)
        pts.append(p)
    inner = []
    for i in range(8, -1, -1):
        t = i / 8
        ang_l = math.pi * 0.95 * t
        r = 14 * tam
        larg = 3.2 * tam * math.sin(math.pi * min(1, t * 1.2)) + 0.6
        p = topo + (-n * math.sin(ang_l) * (r - larg)) + d * (math.cos(ang_l) * r * 0.45 - r * 0.45 - larg)
        inner.append(p)
    tela.pintar(tela.poly(pts + inner), lamina)


def cajado(tela, mao, ang, comp, mat, atras=None, torto=0.0):
    d, n = _eixos(ang)
    mao = v2(mao)
    atras = comp * 0.85 if atras is None else atras
    a = mao - d * atras
    b = mao + d * comp
    meio = lerp(a, b, 0.6) + n * torto
    tela.pintar(tela.corrente([a, meio, b], [0.9, 1.1, 1.2]), mat)
    return b


def arco_flecha(tela, mao, ang, alt, madeira, corda, puxa=0.0, flecha=None, ponta=None):
    """Arco segurado pela mão (mão = centro do arco). ang = direção para onde aponta."""
    d, n = _eixos(ang)
    mao = v2(mao)
    topo = mao - n * alt * 0.5 - d * 2.5
    base = mao + n * alt * 0.5 - d * 2.5
    meio_t = mao - n * alt * 0.28 + d * 1.5
    meio_b = mao + n * alt * 0.28 + d * 1.5
    pts = [topo - d * 1 - n * 1.5, meio_t, mao + d * 1.5, meio_b, base - d * 1 + n * 1.5]
    tela.pintar(tela.corrente(pts, [0.7, 1.1, 1.3, 1.1, 0.7]), madeira)
    puxo = mao - d * (3 + puxa)
    tela.tracos([topo - d * 1 - n * 1.5, puxo, base - d * 1 + n * 1.5], corda)
    if flecha is not None:
        tela.traco(puxo, mao + d * 10, flecha)
        p = mao + d * 10
        tela.pintar(tela.poly([p + n * 1.6, p + d * 3.5, p - n * 1.6]), ponta)
        tela.px(puxo[0] - d[0], puxo[1] - d[1], (200, 190, 170))
    return puxo


def escudo(tela, centro, mat, borda, larg=8, alt=11, emblema=None, ang=0.0, forma="gota"):
    c = v2(centro)
    if forma == "gota":
        pts = [(-larg, -alt * 0.55), (larg, -alt * 0.55), (larg * 0.95, alt * 0.1), (larg * 0.5, alt * 0.6),
               (0, alt * 0.95), (-larg * 0.5, alt * 0.6), (-larg * 0.95, alt * 0.1)]
    elif forma == "redondo":
        pts = [(math.cos(t) * larg, math.sin(t) * alt) for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    else:  # torre
        pts = [(-larg, -alt), (larg, -alt), (larg, alt * 0.8), (0, alt), (-larg, alt * 0.8)]
    ca, sa = math.cos(ang), math.sin(ang)
    P = [c + v2(x * ca - y * sa, x * sa + y * ca) for x, y in pts]
    m = tela.poly(P)
    tela.pintar(m, borda)
    inner = tela.poly([c + (p - c) * 0.78 for p in P])
    tela.pintar(inner & m, mat, linha_interna=False)
    return m, c


def rastro(tela, centro, r_in, r_out, a0, a1, cor=(235, 225, 210), cor2=None, passos=24):
    """Arco de 'smear' do golpe (efeito clássico de pixel art)."""
    c = v2(centro)
    fora, dentro = [], []
    for i in range(passos + 1):
        t = i / passos
        a = a0 + (a1 - a0) * t
        esp = math.sin(math.pi * t) ** 0.7
        ro = r_out
        ri = r_out - (r_out - r_in) * esp
        fora.append(c + dir_ang(a) * ro)
        dentro.append(c + dir_ang(a) * ri)
    m = tela.poly(fora + dentro[::-1])
    m &= tela.alfa == 0
    cor2 = cor2 or misturar(cor, (90, 60, 120), 0.45)
    tela.chapado(m, cor2, emite=True)
    # borda externa mais clara
    fora2 = []
    for i in range(passos + 1):
        t = i / passos
        a = a0 + (a1 - a0) * t
        fora2.append(c + dir_ang(a) * (r_out - 1.2))
    m2 = tela.poly(fora + fora2[::-1]) & m
    tela.chapado(m2, cor, emite=True)
    return m


def faiscas(tela, c, cor, n=6, raio=8, semente=0):
    rng = np.random.default_rng(semente)
    for _ in range(n):
        a = rng.random() * 2 * math.pi
        r = rng.random() * raio
        p = v2(c) + v2(math.cos(a), math.sin(a)) * r
        tela.px(p[0], p[1], cor, emite=True)
