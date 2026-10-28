"""Esqueleto humanoide (poses por ângulos + IK) e peças genéricas do corpo."""
import math

import numpy as np

from .motor import Quadro, dir_ang, norm, v2, girar, lerp, misturar, rgb

# Proporções em fração da altura total H (heroicas / realistas, ~7,3 cabeças)
PROP = dict(
    cabeca=0.132, pescoco=0.032, tronco=0.285, coxa=0.235, canela=0.225, tornozelo=0.035,
    braco=0.168, antebraco=0.152, mao=0.042, pe=0.082,
    ombros=0.25, quadris=0.165, giro=0.55,
    l_coxa=0.052, l_canela=0.04, l_braco=0.036, l_antebraco=0.032,
)

POSE_BASE = dict(
    quadril=(0.0, 0.0), tronco=0.0, cabeca=0.0, pelvis=None,
    pe_f=(-0.06, 0.0), pe_b=(0.07, 0.0), joelho_f=-1, joelho_b=-1,
    braco_f=(0.15, 0.25), braco_b=(-0.12, 0.3), alvo_f=None, alvo_b=None,
    arma_f=0.35, arma_b=0.0, giro=0.0, pivo=None, desloc=(0.0, 0.0),
    respira=0.0,
)


def dir_baixo(a):
    """0 = para baixo, positivo gira para a frente (direita)."""
    return np.array([math.sin(a), math.cos(a)])


def ik(a, t, l1, l2, lado):
    a, t = np.array(a, float), np.array(t, float)
    d = t - a
    dist = float(np.linalg.norm(d))
    dist = max(1e-3, min(dist, l1 + l2 - 1e-3))
    d = norm(d)
    x = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(0.0, l1 * l1 - x * x))
    n = np.array([-d[1], d[0]])
    return a + d * x + n * h * lado


def esqueleto(H, cx, chao, pose=None, prop=None):
    P = dict(PROP)
    if prop:
        P.update(prop)
    S = {k: v * H if k != "giro" else v for k, v in P.items()}
    p = dict(POSE_BASE)
    if pose:
        p.update(pose)

    J = {"H": H, "P": S, "chao": chao}
    perna = S["coxa"] + S["canela"]
    alt_quadril = S["tornozelo"] + perna * 0.975
    qx, qy = p["quadril"]
    pelvis = v2(cx + qx * H, chao - alt_quadril + qy * H)
    if p["pelvis"] is not None:
        pelvis = v2(p["pelvis"])

    t = p["tronco"]
    u = dir_ang(t)
    f = np.array([-u[1], u[0]])
    resp = p["respira"]
    pescoco = pelvis + u * (S["tronco"] + resp)
    J["pelvis"] = pelvis
    J["pescoco"] = pescoco
    J["peito"] = pelvis + u * (S["tronco"] * 0.66 + resp)
    J["cintura"] = pelvis + u * (S["tronco"] * 0.3)

    g = S["giro"]
    meio_ombro = S["ombros"] / 2
    J["ombro_f"] = pescoco - u * (H * 0.03) - f * (meio_ombro * g * 0.95)
    J["ombro_b"] = pescoco - u * (H * 0.035) + f * (meio_ombro * g * 0.75)

    # quadris acompanham pouco a inclinação do tronco
    up = dir_ang(t * 0.35)
    fp = np.array([-up[1], up[0]])
    meio_q = S["quadris"] / 2
    J["quadril_f"] = pelvis - fp * (meio_q * g) + up * (H * 0.01)
    J["quadril_b"] = pelvis + fp * (meio_q * g * 0.8) + up * (H * 0.015)

    # cabeça
    hu = dir_ang(t + p["cabeca"])
    J["cabeca"] = pescoco + hu * (S["pescoco"] + S["cabeca"] * 0.5)
    J["topo"] = J["cabeca"] + hu * (S["cabeca"] * 0.5)
    J["queixo"] = J["cabeca"] - hu * (S["cabeca"] * 0.5)

    # pernas (IK até o pé)
    for lado in ("f", "b"):
        dx, dy = p["pe_" + lado]
        chao_pe = v2(cx + dx * H, chao + dy * H)
        tornoz = chao_pe + v2(0, -S["tornozelo"])
        quad = J["quadril_" + lado]
        joelho = ik(quad, tornoz, S["coxa"], S["canela"], p["joelho_" + lado])
        J["joelho_" + lado] = joelho
        J["tornozelo_" + lado] = tornoz
        J["dedo_" + lado] = tornoz + v2(S["pe"], S["tornozelo"] * 0.85)
        J["calcanhar_" + lado] = tornoz + v2(-S["pe"] * 0.28, S["tornozelo"] * 0.85)

    # braços
    for lado in ("f", "b"):
        ombro = J["ombro_" + lado]
        alvo = p["alvo_" + lado]
        if alvo is not None:
            alvo = v2(alvo[0] * H, alvo[1] * H) + ombro if abs(alvo[0]) < 3 else v2(alvo)
            cot = ik(ombro, alvo, S["braco"], S["antebraco"], 1)
            d = norm(alvo - cot)
            mao = cot + d * S["antebraco"]
        else:
            a1, a2 = p["braco_" + lado]
            cot = ombro + dir_baixo(a1 + t) * S["braco"]
            mao = cot + dir_baixo(a1 + a2 + t) * S["antebraco"]
        J["cotovelo_" + lado] = cot
        J["mao_" + lado] = mao
        J["arma_" + lado] = p["arma_" + lado]

    # transformação global (morte, quedas)
    giro = p["giro"]
    dx, dy = p["desloc"]
    pivo = v2(cx, chao) if p["pivo"] is None else v2(p["pivo"])
    for k, val in list(J.items()):
        if isinstance(val, np.ndarray) and val.shape == (2,):
            if giro:
                val = girar(val, giro, pivo)
            J[k] = val + v2(dx * H, dy * H)
    J["arma_f"] += giro
    J["arma_b"] += giro
    J["u"] = norm(J["pescoco"] - J["pelvis"])
    J["hu"] = norm(J["topo"] - J["cabeca"])
    J["giro"] = giro
    J["pose"] = p
    return J


def quadro_tronco(J):
    return Quadro(J["pelvis"], J["u"])


def quadro_cabeca(J):
    return Quadro(J["cabeca"], J["hu"])


# ============================================================
# PEÇAS GENÉRICAS
# ============================================================

def perna(tela, J, lado, calca, bota=None, grossura=1.0, cano=0.55, pe_mat=None, recorte=None):
    S = J["P"]
    q, j, t = J["quadril_" + lado], J["joelho_" + lado], J["tornozelo_" + lado]
    g = grossura
    m = tela.capsula(q, j, S["l_coxa"] * g, S["l_canela"] * g * 1.08)
    m |= tela.capsula(j, t, S["l_canela"] * g * 1.05, S["l_canela"] * g * 0.7)
    tela.pintar(m, calca, recorte=recorte)
    if bota is not None:
        b0 = lerp(t, j, cano)
        mb = tela.capsula(b0, t, S["l_canela"] * g * 1.12, S["l_canela"] * g * 0.85)
        mb |= pe(tela, J, lado, g)
        tela.pintar(mb, bota)
    elif pe_mat is not None:
        tela.pintar(pe(tela, J, lado, g), pe_mat)


def pe(tela, J, lado, g=1.0):
    S = J["P"]
    t = J["tornozelo_" + lado]
    dedo, calc = J["dedo_" + lado], J["calcanhar_" + lado]
    alt = S["l_canela"] * g
    return tela.poly([t + (calc - t) * 0.6 + v2(-alt * 0.6, -alt * 0.9), t + v2(alt * 0.8, -alt * 0.5),
                      dedo + v2(0, -alt * 0.9), dedo + v2(alt * 0.4, 0.4), calc + v2(0, 0.4)])


def braco(tela, J, lado, manga, mao=None, grossura=1.0, recorte=None, punho=None, so_mao=False):
    S = J["P"]
    o, c, m = J["ombro_" + lado], J["cotovelo_" + lado], J["mao_" + lado]
    g = grossura
    if not so_mao:
        mk = tela.capsula(o, c, S["l_braco"] * g * 1.1, S["l_antebraco"] * g)
        mk |= tela.capsula(c, m, S["l_antebraco"] * g, S["l_antebraco"] * g * 0.8)
        tela.pintar(mk, manga, recorte=recorte)
        if punho is not None:
            p0 = lerp(c, m, 0.45)
            tela.pintar(tela.capsula(p0, m, S["l_antebraco"] * g * 1.15, S["l_antebraco"] * g * 0.95), punho)
    if mao is not None:
        tela.pintar(tela.circulo(m, S["mao"] * g * 0.75), mao)


def tronco(tela, J, mat, cintura=0.11, peito=0.17, ombros=None, topo=1.0, base=0.0, recorte=None,
           barriga=0.0, corcunda=0.0):
    """Tronco em 3/4. Larguras em fração de H."""
    H = J["H"]
    T = J["P"]["tronco"]
    Q = quadro_tronco(J)
    ombros = J["P"]["ombros"] / H * 0.82 if ombros is None else ombros
    cw, pw, sw = cintura * H, peito * H, ombros * H
    pts = [(-cw * 0.55, base * T), (cw * 0.45 + barriga * H * 0.5, base * T),
           (pw * 0.45 + barriga * H, T * 0.45), (pw * 0.5, T * 0.72), (sw * 0.42, T * 0.92 * topo),
           (sw * 0.2, T * topo + 1), (-sw * 0.35, T * topo + 1), (-sw * 0.58 - corcunda * H, T * 0.9 * topo),
           (-pw * 0.55 - corcunda * H, T * 0.68), (-cw * 0.6, T * 0.3)]
    m = tela.poly(Q.pts(pts))
    tela.pintar(m, mat, recorte=recorte)
    return m


def pescoco(tela, J, mat, larg=0.035):
    H = J["H"]
    tela.pintar(tela.capsula(J["pescoco"] - J["u"] * H * 0.02, J["cabeca"] - J["hu"] * H * 0.02,
                             larg * H, larg * H * 0.9), mat)


def cabeca_base(tela, J, pele, larg=0.5, mandibula=True, nariz=True, orelha=True):
    """Crânio de perfil 3/4 olhando para a direita."""
    H = J["H"]
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.82 * (larg / 0.5)
    pts = [(-w * 0.5, h * 0.1), (-w * 0.45, h * 0.38), (-w * 0.1, h * 0.52), (w * 0.3, h * 0.46),
           (w * 0.5, h * 0.2), (w * 0.56, -h * 0.02), (w * 0.62 if nariz else w * 0.52, -h * 0.1),
           (w * 0.5, -h * 0.2), (w * 0.44, -h * 0.4), (w * 0.15, -h * 0.52), (-w * 0.12, -h * 0.45),
           (-w * 0.4, -h * 0.18)]
    m = tela.poly(C.pts(pts))
    tela.pintar(m, pele)
    if orelha:
        tela.pintar(tela.elipse_girada(C.pt(-w * 0.12, -h * 0.02), 1.2, 1.8, 0), pele.escuro(1))
    return m, C


def olho(tela, C, x, y, cor, brilho=None, emite=True, raio=3.0):
    p = C.pt(x, y)
    tela.px(p[0], p[1], cor, emite=emite)
    if brilho:
        tela.brilho(p, raio, brilho, 0.8)


# ============================================================
# ROUPAS / MANTOS / CAPAS
# ============================================================

def manto(tela, J, mat, folga=0.06, barra=0.0, rasgos=0, ombros=True, recorte=None, cintura=None,
          semente=0, sobre_pernas=True):
    """Manto/vestido longo: envoltória de ombros, quadris, joelhos e tornozelos."""
    H = J["H"]
    u = J["u"]
    f = np.array([-u[1], u[0]])
    fl = folga * H
    pts = []
    if ombros:
        pts += [J["ombro_f"] - f * 1.5 + u * 1, J["ombro_b"] + f * 1.5 + u * 1, J["pescoco"] + u * 1]
    else:
        c = J["cintura"] if cintura is None else cintura
        pts += [c - f * H * 0.07, c + f * H * 0.065]
    for lado in ("f", "b"):
        s = -1 if lado == "f" else 1
        pts += [J["quadril_" + lado] + f * s * H * 0.05]
        pts += [J["joelho_" + lado] + f * s * fl * 0.6]
        pts += [J["tornozelo_" + lado] + f * s * fl + J["hu"] * 0 - u * (barra * H)]
        pts += [J["dedo_" + lado] - u * (barra * H)]
    m = tela.casco(pts)
    # rasgos na barra
    if rasgos:
        a = J["tornozelo_f"] - f * fl - u * (barra * H)
        b = J["dedo_b"] + f * fl * 0.5 - u * (barra * H)
        rng = tela.random
        rng.seed(semente)
        for i in range(rasgos):
            t = (i + 0.5) / rasgos
            p = lerp(a, b, t)
            larg = H * 0.03
            fundo = H * (0.03 + 0.05 * rng.random())
            if rng.random() < 0.6:
                m &= ~tela.poly([p - f * larg, p + f * larg, p + u * fundo])
            else:
                m |= tela.poly([p - f * larg * 0.8, p + f * larg * 0.8, p - u * fundo * 0.6])
    tela.pintar(m, mat, recorte=recorte)
    return m


def capa(tela, J, mat, comprimento=0.62, vento=0.0, larg=0.16, rasgos=5, semente=0, gola=False,
         forro=None):
    """Capa nas costas: pende pelo eixo do tronco, abre para trás (esquerda)."""
    H = J["H"]
    u = J["u"]
    f = np.array([-u[1], u[0]])
    topo_f = J["ombro_f"] + u * 1.5
    topo_b = J["ombro_b"] + u * 1.5
    base_y = -comprimento * H
    meio = J["pescoco"] - f * H * 0.02
    fundo_a = meio + u * base_y - f * (larg * H + vento * H)
    fundo_b = meio + u * base_y + f * (larg * H * 0.25 - vento * H * 0.4)
    lateral = meio + u * (base_y * 0.5) - f * (larg * H * 0.75 + vento * H * 0.6)
    pts = [topo_b, topo_f - f * 1.5, lateral, fundo_a]
    rng = tela.random
    rng.seed(semente)
    n = max(2, rasgos)
    for i in range(1, n):
        t = i / n
        p = lerp(fundo_a, fundo_b, t)
        prof = H * (0.02 + 0.06 * rng.random()) * (1 if i % 2 else -0.4)
        pts.append(p + u * prof)
    pts += [fundo_b, J["pelvis"] + f * H * 0.02, topo_b + f * 1]
    m = tela.poly(pts)
    if forro is not None:
        tela.pintar(m, forro)
        m2 = tela.poly([topo_b, topo_f - f * 1.5, lateral + f * 2, fundo_a + f * 3 + u * 3, fundo_b + u * 2,
                        J["pelvis"] + f * H * 0.02])
        tela.pintar(m & m2, mat, linha_interna=False)
    else:
        tela.pintar(m, mat)
    if gola:
        g = tela.poly([J["ombro_f"] - f * 2, J["pescoco"] + u * H * 0.05 - f * 2, J["pescoco"] + u * H * 0.07 + f * 1,
                       J["ombro_b"] + f * 2])
        tela.pintar(g, mat.claro(1))
    return m


def capuz(tela, J, mat, ponta=0.5, aberto=True, sombra=(10, 6, 14), larg=1.0):
    """Capuz cobrindo a cabeça, rosto na sombra."""
    H = J["H"]
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.95 * larg
    pts = [(-w * 0.62, -h * 0.75), (-w * 0.7, h * 0.15), (-w * 0.35, h * 0.62), (-w * (0.3 + ponta), h * (0.3 + ponta * 0.3)),
           (w * 0.15, h * 0.68), (w * 0.55, h * 0.4), (w * 0.68, -h * 0.05), (w * 0.62, -h * 0.75)]
    m = tela.poly(C.pts(pts))
    tela.pintar(m, mat)
    face = None
    if aberto:
        face = tela.poly(C.pts([(w * 0.05, h * 0.35), (w * 0.58, h * 0.22), (w * 0.62, -h * 0.55), (w * 0.12, -h * 0.5),
                                (-w * 0.05, -h * 0.1)]))
        tela.chapado(face, sombra)
    return m, C, face


def cinto(tela, J, mat, fivela=None, altura=0.0, larg=0.022):
    H = J["H"]
    Q = quadro_tronco(J)
    y = altura * H
    m = tela.poly(Q.pts([(-0.072 * H, y - larg * H), (0.07 * H, y - larg * H), (0.072 * H, y + larg * H),
                         (-0.074 * H, y + larg * H)]))
    tela.pintar(m, mat)
    if fivela is not None:
        p = Q.pt(0.02 * H, y)
        tela.pintar(tela.circulo(p, max(1.0, larg * H * 0.9)), fivela)


def sangue_no_chao(tela, cx, chao, larg, cor=(70, 6, 14), cor2=(110, 14, 24)):
    m = tela.elipse(cx, chao - 0.5, larg, max(1.2, larg * 0.16))
    tela.chapado(m & (tela.alfa == 0), cor)
    m2 = tela.elipse(cx - larg * 0.2, chao - 0.8, larg * 0.5, max(0.8, larg * 0.07))
    tela.chapado(m2 & (tela.parte == 0), cor2)


def gotas(tela, pts, cor=(120, 10, 22)):
    for p in pts:
        tela.px(p[0], p[1], cor)
