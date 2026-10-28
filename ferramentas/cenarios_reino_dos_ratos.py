"""Cenários do Reino dos Ratos (docs/planos/reino_dos_ratos.md, etapa 2A), na técnica de cenarios_macabros.py
(352x180, 5 camadas, luzes que tremulam e partículas). Pouca luz: velas, brilho verde da água e lampiões.

    reino_dos_ratos         uma zona por variante (regioes.json "zonas"):
                              0  Galerias Fétidas   túneis de tijolo, canos pingando, água verde, ossos e lixo
                              1  Mercado Roedor     barracas de restos humanos, velas em crânios, varais de trapos, moedas
                              2  Catedral Roída     capela afundada, vitrais quebrados, bancos roídos, queijo e ouro
    salao_do_trono_roedor   sala dos chefes (em cenario_salao_do_trono.py, resolução dobrada)

Partículas novas (src/visual/particulas.py): gota_verde, vapor, mosca e olhos (pares de olhos vermelhos no escuro).
cenarios_macabros.juntar_cenas_novas() põe CENAS_DO_REINO no catálogo.

    python ferramentas/cenarios_macabros.py reino_dos_ratos salao_do_trono_roedor
"""
import math

import pygame

from cenarios_macabros import (LARGURA, ALTURA, HORIZONTE, camada, degrade, halo, pontilhar, poligono_pontilhado,
                               contornar, luz_de_borda, retangulo, linha, clarear, vela, osso, cranio,
                               chao_basico, pedra)
from cenarios_finais import blocos, janela_gotica, estandarte, coluna_gotica, chao_em_lajes, poca_de_luz, candelabro, \
    rachadura
from agua_no_chao import chao_alagado
from cenario_salao_do_trono import cena_salao_do_trono

CENTRO = LARGURA // 2
TIJOLO = [(52, 42, 38), (58, 46, 40), (46, 38, 34), (50, 44, 36)]
TIJOLO_JUNTA = (24, 18, 18)
LODO = (74, 104, 50)
AGUA = (20, 40, 28)
AGUA_BRILHO = (90, 150, 80)
FERRUGEM = (92, 58, 38)
MADEIRA = (70, 48, 32)
VELUDO = (118, 22, 32)
OURO = (214, 170, 70)
OURO_CLARO = (255, 222, 130)
QUEIJO = (222, 186, 84)
OLHO = (220, 36, 40)


# ============================================================
# FERRAMENTAS
# ============================================================

def rato_pequeno(sup, x, y, olha=1, cor=(34, 28, 30), olho=OLHO):
    """Silhueta de rato de poucos pixels: corpo, focinho, orelha, cauda e o olhinho vermelho."""
    pygame.draw.ellipse(sup, cor, (x - 3, y - 2, 7, 3))
    sup.set_at((x + 4 * olha, y - 1), cor)
    sup.set_at((x + 2 * olha, y - 3), cor)
    linha(sup, (64, 50, 52), (x - 3 * olha, y), (x - 8 * olha, y + 1))
    if olho:
        sup.set_at((x + 3 * olha, y - 2), olho)


def simbolo_rato_coroado(sup, x, y, pelo=(160, 150, 140), coroa=OURO):
    """O brasão do Reino: cabeça de rato de frente, olhos vermelhos e uma coroa torta."""
    for dx in (-3, 3):
        pygame.draw.circle(sup, pelo, (x + dx, y - 1), 2)                          # orelhas
    pygame.draw.circle(sup, pelo, (x, y + 2), 3)
    pygame.draw.polygon(sup, pelo, [(x - 2, y + 3), (x + 2, y + 3), (x, y + 7)])     # focinho
    sup.set_at((x - 1, y + 2), OLHO)
    sup.set_at((x + 1, y + 2), OLHO)
    pygame.draw.polygon(sup, coroa, [(x - 3, y - 2), (x + 3, y - 3), (x + 3, y - 7), (x + 1, y - 5), (x, y - 8),
                                     (x - 1, y - 5), (x - 3, y - 6)])                 # torta: um lado mais alto


def cano(sup, pontos, larg=4, cor=FERRUGEM):
    """Cano enferrujado por uma sequência de pontos (só retas horizontais/verticais), com brilho e juntas."""
    escuro, claro = clarear(cor, -28), clarear(cor, 26)
    for a, b in zip(pontos, pontos[1:]):
        linha(sup, cor, a, b, larg)
    for a, b in zip(pontos, pontos[1:]):
        horizontal = a[1] == b[1]
        meia = larg // 2
        if horizontal:
            linha(sup, claro, (a[0], a[1] - meia), (b[0], b[1] - meia))
            linha(sup, escuro, (a[0], a[1] + meia - 1), (b[0], b[1] + meia - 1))
        else:
            linha(sup, claro, (a[0] - meia, a[1]), (b[0] - meia, b[1]))
            linha(sup, escuro, (a[0] + meia - 1, a[1]), (b[0] + meia - 1, b[1]))
        comprimento = int(math.hypot(b[0] - a[0], b[1] - a[1]))
        for k in range(10, comprimento, 18):                                         # juntas
            t = k / comprimento
            jx, jy = int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t)
            if horizontal:
                retangulo(sup, escuro, (jx, jy - meia - 1, 2, larg + 2))
            else:
                retangulo(sup, escuro, (jx - meia - 1, jy, larg + 2, 2))


def boca_de_cano(sup, luzes, x, y, larg=6, pinga=8):
    """A ponta do cano: boca escura e um fio de lodo verde escorrendo."""
    pygame.draw.ellipse(sup, clarear(FERRUGEM, 10), (x - larg // 2 - 1, y - 2, larg + 2, 4))
    pygame.draw.ellipse(sup, (10, 14, 10), (x - larg // 2, y - 1, larg, 2))
    linha(sup, LODO, (x, y + 1), (x, y + pinga))
    sup.set_at((x, y + pinga + 1), AGUA_BRILHO)
    luzes.append([x, y + pinga, 6, [90, 170, 90], 0.3])


def agua_de_esgoto(sup, rng, topo, base, luzes=None):
    """Canal de água verde e grossa: superfície pontilhada, reflexos, espuma e lixo boiando."""
    degrade(sup, topo, base, [(30, 58, 36), AGUA, (12, 26, 18)])
    for _ in range(int(LARGURA * (base - topo) / 40)):                               # reflexos
        x, y = rng.randrange(LARGURA), rng.randrange(topo + 1, base)
        linha(sup, rng.choice((AGUA_BRILHO, (60, 110, 64))), (x, y), (x + rng.randint(2, 7), y))
    linha(sup, (110, 160, 90), (0, topo), (LARGURA, topo))                         # borda da água
    for _ in range(10):                                                              # lixo e espuma boiando
        x, y = rng.randrange(LARGURA), rng.randrange(topo + 1, base - 1)
        retangulo(sup, rng.choice(((70, 60, 44), (110, 100, 80), (150, 150, 120))), (x, y, rng.randint(1, 3), 1))
    if luzes is not None:
        for x in range(30, LARGURA, 90):
            luzes.append([x + rng.randint(-10, 10), (topo + base) // 2, 14, [80, 170, 90], 0.25])


def lixo(sup, rng, x, y, n=8):
    """Montinho de lixo: tábuas, trapos, cacos e ossinhos."""
    for _ in range(n):
        cor = rng.choice(((70, 56, 40), (90, 80, 64), (56, 60, 44), (120, 110, 90), (40, 34, 30)))
        retangulo(sup, cor, (x + rng.randint(-6, 6), y - rng.randint(0, 3), rng.randint(2, 5), rng.randint(1, 2)))
    if rng.random() < 0.6:
        osso(sup, x + rng.randint(-4, 2), y - 1)


def vela_em_cranio(sup, luzes, x, y):
    """Crânio com uma vela derretendo em cima (luz amarela e baixa)."""
    cranio(sup, x, y)
    vela(sup, x + 1, y, 3, (200, 190, 150))
    linha(sup, (200, 190, 150), (x + 1, y), (x, y + 2))                              # cera escorrida
    luzes.append([x + 1, y - 5, 12, [255, 190, 100], 0.9])


def pilha_de_moedas(sup, rng, x, base, larg, alt):
    """Montanha de moedas: triângulo pontilhado de ouro com brilhos."""
    for y in range(base - alt, base):
        meia = int(larg / 2 * (y - (base - alt)) / alt)
        for xx in range(x - meia, x + meia + 1):
            sup.set_at((xx, y), rng.choice((OURO, (180, 140, 56), (150, 110, 44))))
    for _ in range(larg // 3):
        sup.set_at((x + rng.randint(-larg // 3, larg // 3), base - rng.randint(1, alt)), OURO_CLARO)


def fatia_de_queijo(sup, x, y, tam=6):
    """Cunha de queijo com buracos (vista de lado)."""
    pygame.draw.polygon(sup, QUEIJO, [(x, y), (x + tam, y), (x + tam, y - tam // 2), (x, y - 1)])
    linha(sup, clarear(QUEIJO, 28), (x, y - 1), (x + tam, y - tam // 2))
    sup.set_at((x + tam // 2, y - 1), (150, 110, 40))


def pilha_de_queijo(sup, rng, x, base, n=6):
    """Rodas e cunhas de queijo empilhadas (algumas mordidas)."""
    for k in range(n):
        cx, cy = x + rng.randint(-10, 10), base - 3 - (k // 3) * 5
        pygame.draw.ellipse(sup, QUEIJO, (cx - 5, cy - 3, 10, 6))
        pygame.draw.ellipse(sup, clarear(QUEIJO, 24), (cx - 4, cy - 3, 8, 3))
        sup.set_at((cx - 2, cy), (150, 110, 40))
        if rng.random() < 0.5:                                                       # mordida
            pygame.draw.circle(sup, (0, 0, 0, 0), (cx + 5, cy - 2), 2)
    for _ in range(3):
        fatia_de_queijo(sup, x + rng.randint(-14, 8), base, rng.randint(5, 7))


def varal_de_trapos(sup, rng, a, b, cores, curva=8):
    """Corda caída entre dois pontos com trapos pendurados de pontas rasgadas."""
    pontos = [(a[0] + (b[0] - a[0]) * t / 20, a[1] + (b[1] - a[1]) * t / 20 + math.sin(math.pi * t / 20) * curva)
              for t in range(21)]
    pygame.draw.lines(sup, (40, 32, 28), False, pontos, 1)
    for k in range(2, 19, 3):
        x, y = pontos[k]
        larg, alt = rng.randint(4, 7), rng.randint(6, 11)
        cor = rng.choice(cores)
        pygame.draw.polygon(sup, cor, [(x, y), (x + larg, y), (x + larg, y + alt), (x + larg // 2, y + alt - 2),
                                       (x + 1, y + alt + 1)])
        linha(sup, clarear(cor, 20), (x, y), (x + larg, y))


def barraca(sup, rng, luzes, x, base, larg, alt, pano, mercadoria):
    """Barraca de feira dos ratos: estacas tortas, toldo de trapos rasgados, balcão e a mercadoria."""
    topo = base - alt
    for dx in (0, larg - 3):                                                         # estacas
        linha(sup, MADEIRA, (x + dx, base), (x + dx + rng.randint(-1, 1), topo), 3)
    toldo = [(x - 4, topo + 2), (x + larg // 2, topo - 8), (x + larg + 4, topo + 2)]
    for k in range(9, -1, -1):                                                       # barra rasgada do toldo
        toldo.append((x - 4 + (larg + 8) * k / 9, topo + 8 + (3 if k % 2 else 0) + rng.randint(0, 2)))
    pygame.draw.polygon(sup, pano[0], toldo)
    for k in range(0, larg + 8, 6):                                                  # listras do pano
        linha(sup, pano[1], (x - 4 + k, topo + 2 - int(8 * (1 - abs(k - larg / 2 - 4) / (larg / 2 + 4)))),
              (x - 4 + k, topo + 8), 2)
    retangulo(sup, clarear(MADEIRA, 10), (x - 2, base - 12, larg + 4, 4))           # balcão
    retangulo(sup, MADEIRA, (x, base - 8, larg, 8))
    linha(sup, clarear(MADEIRA, 30), (x - 2, base - 12), (x + larg + 1, base - 12))
    y = base - 13
    if mercadoria == "restos":                                                       # restos humanos
        for k in range(4):
            cranio(sup, x + 3 + k * (larg - 8) // 3, y - 3)
        for k in range(3):
            osso(sup, x + 4 + k * 9, y - 6)
        pygame.draw.ellipse(sup, (150, 70, 70), (x + larg // 2 - 3, y - 3, 7, 3))   # um pedaço de carne
        for k in range(3):                                                           # mãos penduradas no toldo
            hx = x + 6 + k * (larg - 12) // 2
            linha(sup, (40, 32, 28), (hx, topo + 8), (hx, topo + 14))
            retangulo(sup, (170, 140, 120), (hx - 1, topo + 14, 3, 4))
            for d in range(3):
                sup.set_at((hx - 1 + d, topo + 18), (150, 120, 100))
    elif mercadoria == "queijo":
        for k in range(3):
            fatia_de_queijo(sup, x + 3 + k * (larg - 8) // 3, y, 6)
        for k in range(2):                                                           # potes
            retangulo(sup, (90, 110, 80), (x + larg - 10 + k * 5, y - 6, 4, 6))
            sup.set_at((x + larg - 9 + k * 5, y - 5), (160, 200, 140))
    else:                                                                            # quinquilharias: moedas, anéis, dentes
        for _ in range(14):
            sup.set_at((x + rng.randint(2, larg - 3), y - rng.randint(0, 2)), rng.choice((OURO, OURO_CLARO, (220, 210, 190))))
        pygame.draw.circle(sup, OURO, (x + larg // 2, y - 3), 2, 1)
    vela_em_cranio(sup, luzes, x + larg - 2, base - 16)
    placa = (x + larg // 2 - 6, topo + 18)                                           # plaquinha com o brasão
    retangulo(sup, (50, 36, 26), (placa[0], placa[1], 12, 11))
    simbolo_rato_coroado(sup, placa[0] + 6, placa[1] + 4)


OSSO_CLARO = (214, 204, 180)


# ============================================================
# ZONA 1: GALERIAS FÉTIDAS
# ============================================================

def cena_galerias_fetidas(rng):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    degrade(ceu, 0, ALTURA, [(6, 8, 6), (12, 16, 12), (18, 22, 16), (10, 12, 10)])

    # parede de tijolos com o túnel principal (arco redondo) que some ao longe
    blocos(longe, (0, 0, LARGURA, HORIZONTE + 2), TIJOLO, rng, alt=6, larg=12, junta=TIJOLO_JUNTA, lascas=0.2)
    pontilhar(longe, (0, HORIZONTE - 34, LARGURA, 36), (44, 62, 34), 0.35, so_onde_tem=True)        # lodo nas paredes
    for _ in range(14):                                                              # manchas de água escorrida
        x = rng.randrange(LARGURA)
        for y in range(rng.randint(0, 30), rng.randint(40, HORIZONTE)):
            if rng.random() < 0.7:
                longe.set_at((x, y), (36, 44, 30))
    tx = CENTRO + rng.randint(-30, 30)
    for k, (larg, cor) in enumerate(((112, (64, 52, 46)), (98, (10, 12, 10)), (70, (20, 22, 16)), (52, (8, 10, 8)),
                                     (34, (16, 18, 12)), (22, (6, 8, 6)))):
        arco = pygame.Rect(0, 0, larg, int(larg * 1.25))
        arco.midbottom = (tx, HORIZONTE + 6 - k * 3)
        pygame.draw.ellipse(longe, cor, arco)
    retangulo(longe, (0, 0, 0, 0), (0, HORIZONTE + 3, LARGURA, ALTURA))
    halo(longe, (tx, HORIZONTE - 4), 22, (60, 110, 64), 0.6)                         # brilho verde lá no fundo
    luzes.append([tx, HORIZONTE - 6, 26, [80, 190, 100], 0.3])
    for x in (rng.randint(24, 60), rng.randint(290, 330)):                           # túneis laterais menores
        arco = pygame.Rect(0, 0, 34, 40)
        arco.midbottom = (x, HORIZONTE + 2)
        pygame.draw.ellipse(longe, (60, 48, 42), arco.inflate(6, 6))
        pygame.draw.ellipse(longe, (10, 12, 10), arco)
        for k in range(5):                                                           # grade enferrujada
            linha(longe, FERRUGEM, (arco.x + 5 + k * 6, arco.y + 4), (arco.x + 5 + k * 6, arco.bottom - 2))
        for k in range(2):
            sup_y = arco.y + 12 + k * 12
            linha(longe, FERRUGEM, (arco.x + 2, sup_y), (arco.right - 3, sup_y))
        sup_x = x + rng.choice((-6, 6))
        longe.set_at((sup_x, HORIZONTE - 8), OLHO)                                   # alguém olhando de trás da grade
        longe.set_at((sup_x + 2, HORIZONTE - 8), OLHO)

    # canos no teto e nas paredes, pingando lodo; um beiral com ratos; lampião fraco
    cano(meio, [(0, 18), (LARGURA, 18)], 5)
    cano(meio, [(0, 30), (120, 30), (120, 62)], 4)
    boca_de_cano(meio, luzes, 120, 64)
    cano(meio, [(LARGURA, 40), (262, 40), (262, 74)], 4)
    boca_de_cano(meio, luzes, 262, 76, pinga=12)
    for _ in range(26):                                                              # lodo pingando do teto
        x = rng.randrange(LARGURA)
        comp = rng.randint(2, 9)
        linha(meio, LODO, (x, 21), (x, 21 + comp))
        meio.set_at((x, 22 + comp), AGUA_BRILHO)
    retangulo(meio, (46, 40, 36), (0, HORIZONTE - 36, 90, 4))                        # beiral
    linha(meio, (80, 70, 60), (0, HORIZONTE - 36), (89, HORIZONTE - 36))
    for k in range(3):
        rato_pequeno(meio, 32 + k * 20, HORIZONTE - 37, olha=1 if k % 2 else -1)
    lx = rng.randint(170, 220)
    linha(meio, (36, 30, 30), (lx, 21), (lx, 44))                                    # lampião pendurado
    retangulo(meio, (50, 40, 30), (lx - 3, 44, 7, 8))
    retangulo(meio, (200, 210, 120), (lx - 2, 46, 5, 4))
    luzes.append([lx, 48, 22, [210, 220, 130], 0.6])
    luz_de_borda(meio, (120, 150, 90), dx=0, dy=-1)
    contornar(meio)

    # chão: canal de água verde atrás e a calçada de pedra onde se luta
    chao_basico(chao, [(44, 44, 34), (30, 30, 24), (12, 12, 10)], rng)
    agua_de_esgoto(chao, rng, HORIZONTE + 1, HORIZONTE + 12, luzes)
    retangulo(chao, (66, 62, 50), (0, HORIZONTE + 12, LARGURA, 2))                   # meio-fio da calçada
    for x in range(0, LARGURA, 9):
        linha(chao, (34, 32, 26), (x, HORIZONTE + 12), (x, HORIZONTE + 13))
    for _ in range(5):
        lixo(chao, rng, rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 20, ALTURA - 6))
    for _ in range(5):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 18, ALTURA - 4))
    for _ in range(4):                                                               # poças verdes
        pygame.draw.ellipse(chao, (28, 52, 34), (rng.randrange(10, LARGURA - 40), rng.randrange(HORIZONTE + 18, ALTURA - 8),
                                                 rng.randint(12, 26), rng.randint(3, 5)))
    for _ in range(3):
        rato_pequeno(chao, rng.randrange(30, LARGURA - 30), rng.randrange(HORIZONTE + 18, ALTURA - 8), rng.choice((-1, 1)))

    # frente: cano grosso no canto esquerdo e entulho no direito
    cano(frente, [(24, 0), (24, ALTURA)], 9, clarear(FERRUGEM, -14))                # (x >= 16: fora da margem de balanço)
    cano(frente, [(24, 112), (36, 112)], 5, clarear(FERRUGEM, -14))
    boca_de_cano(frente, luzes, 38, 112, 6, 10)
    for x in range(LARGURA - 50, LARGURA - 16, 5):
        pedra(frente, (30, 30, 24), x, ALTURA - rng.randint(5, 10), rng.randint(6, 11), 9)
    contornar(frente)
    configuracao = {"luzes": luzes, "particulas": [["gota_verde", 8], ["vapor", 8], ["mosca", 10], ["olhos", 6], ["nevoa", 2]],
                    "cor_nevoa": [60, 84, 58]}
    return [ceu, longe, meio, chao, frente], configuracao


# ============================================================
# ZONA 2: MERCADO ROEDOR
# ============================================================

PANOS = [((100, 30, 30), (140, 110, 70)), ((50, 70, 50), (130, 120, 90)), ((70, 50, 80), (150, 130, 90))]
TRAPOS = [(120, 90, 60), (90, 40, 40), (70, 80, 60), (130, 120, 100), (80, 60, 90)]


def cena_mercado_roedor(rng):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    degrade(ceu, 0, ALTURA, [(10, 8, 8), (20, 16, 14), (28, 22, 18), (14, 10, 10)])

    # salão abobadado de tijolo com arcos; ao fundo, mais barracas acesas
    blocos(longe, (0, 0, LARGURA, HORIZONTE + 2), [(46, 36, 32), (52, 40, 36), (42, 34, 30)], rng, alt=6, larg=12,
           junta=(22, 16, 16), lascas=0.18)
    for x in range(-20, LARGURA + 40, 92):
        arco = pygame.Rect(x, 26, 70, 110)
        pygame.draw.ellipse(longe, (60, 46, 40), arco.inflate(8, 8))
        pygame.draw.ellipse(longe, (12, 10, 10), arco)
        for k in range(3):                                                           # barraquinhas ao longe
            bx = arco.x + 10 + k * 18
            retangulo(longe, (30, 22, 20), (bx, HORIZONTE - 14, 12, 10))
            pygame.draw.polygon(longe, rng.choice(((70, 26, 26), (40, 54, 38))), [(bx - 2, HORIZONTE - 14), (bx + 6, HORIZONTE - 20),
                                                                                  (bx + 14, HORIZONTE - 14)])
            longe.set_at((bx + 6, HORIZONTE - 12), (255, 200, 100))
            luzes.append([bx + 6, HORIZONTE - 12, 7, [255, 180, 90], 0.6])
    retangulo(longe, (0, 0, 0, 0), (0, HORIZONTE + 3, LARGURA, ALTURA))
    varal_de_trapos(longe, rng, (0, 34), (LARGURA, 30), TRAPOS, curva=10)
    contornar(longe)

    # as barracas da frente (restos humanos, queijo e quinquilharias) e varais por cima
    for x, larg, alt, mercadoria, pano in ((22, 64, 64, "restos", PANOS[0]), (142, 58, 58, "queijo", PANOS[1]),
                                           (262, 66, 66, "quinquilharias", PANOS[2])):
        barraca(meio, rng, luzes, x, HORIZONTE + 2, larg, alt, pano, mercadoria)
    varal_de_trapos(meio, rng, (0, 10), (LARGURA, 14), TRAPOS, curva=14)
    for x in (110, 236):                                                             # postes com velas em crânios
        linha(meio, MADEIRA, (x, HORIZONTE + 2), (x, HORIZONTE - 40), 2)
        vela_em_cranio(meio, luzes, x - 1, HORIZONTE - 44)
    luz_de_borda(meio, (230, 170, 100), dx=0, dy=-1)
    contornar(meio)

    # chão de paralelepípedos, moedas espalhadas, poças e ratos correndo
    chao_basico(chao, [(46, 38, 32), (32, 26, 22), (12, 10, 8)], rng)
    y, passo = HORIZONTE + 3, 3
    while y < ALTURA:                                                                # pedras em fileiras
        for x in range(-(y % 7), LARGURA, 9):
            pygame.draw.ellipse(chao, clarear((46, 38, 32), rng.randint(-8, 8)), (x, y, 8, passo))
        y += passo + 1
        passo += 1
    for _ in range(40):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 3, ALTURA - 2)
        chao.set_at((x, y), rng.choice((OURO, OURO_CLARO, (170, 130, 50))))
    for _ in range(3):
        pygame.draw.ellipse(chao, (30, 50, 34), (rng.randrange(20, LARGURA - 40), rng.randrange(HORIZONTE + 12, ALTURA - 8),
                                                 rng.randint(14, 24), 4))
    for _ in range(4):
        rato_pequeno(chao, rng.randrange(30, LARGURA - 30), rng.randrange(HORIZONTE + 12, ALTURA - 8), rng.choice((-1, 1)))
    for _ in range(3):
        lixo(chao, rng, rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 16, ALTURA - 6), 5)

    # frente: caixotes à esquerda, saco de moedas furado à direita
    for k in range(2):
        retangulo(frente, (64, 44, 30), (16 + k * 18, ALTURA - 20 + k * 6, 20, 20))
        for d in range(0, 20, 5):
            linha(frente, (44, 30, 20), (16 + k * 18, ALTURA - 20 + k * 6 + d), (35 + k * 18, ALTURA - 20 + k * 6 + d))
    pygame.draw.ellipse(frente, (110, 90, 60), (LARGURA - 48, ALTURA - 22, 28, 26))
    linha(frente, (70, 54, 36), (LARGURA - 38, ALTURA - 22), (LARGURA - 32, ALTURA - 26), 2)
    pilha_de_moedas(frente, rng, LARGURA - 54, ALTURA, 18, 6)
    contornar(frente)
    configuracao = {"luzes": luzes, "particulas": [["mosca", 16], ["poeira", 10], ["olhos", 8], ["vapor", 3]],
                    "cor_nevoa": [70, 60, 50]}
    return [ceu, longe, meio, chao, frente], configuracao


# ============================================================
# ZONA 3: CATEDRAL ROÍDA
# ============================================================

VITRAL_APAGADO = [(110, 40, 40), (70, 84, 50), (80, 66, 110), (130, 104, 56), (60, 50, 70)]
PEDRA_LIMOSA = (70, 74, 64)
PEDRA_ESCURA = (40, 44, 38)
TERRA = (46, 34, 26)


def banco_de_igreja(sup, rng, x, y, larg):
    """Banco de igreja de madeira escura: laterais altas de ponta redonda, assento e encosto de duas tábuas.
    O encosto está roído aos pedaços e às vezes falta um trecho de tábua."""
    madeira, escura, clara = (72, 48, 34), (42, 28, 20), (110, 76, 50)
    retangulo(sup, escura, (x, y - 13, larg, 2))                                     # encosto
    retangulo(sup, madeira, (x, y - 10, larg, 2))
    linha(sup, clara, (x, y - 13), (x + larg - 1, y - 13))
    retangulo(sup, madeira, (x, y - 4, larg, 3))                                     # assento
    linha(sup, clara, (x, y - 4), (x + larg - 1, y - 4))
    retangulo(sup, escura, (x, y - 1, larg, 1))
    for k in range(0, larg, 2):                                                      # mordidas no encosto
        if rng.random() < 0.35:
            for d in range(rng.randint(1, 2)):
                sup.set_at((x + k, y - 13 + d), (0, 0, 0, 0))
    if rng.random() < 0.6:                                                           # um trecho de tábua faltando
        retangulo(sup, (0, 0, 0, 0), (x + rng.randint(5, larg - 14), y - 10, rng.randint(5, 9), 2))
    for dx in (0, larg - 3):                                                         # laterais de ponta redonda
        retangulo(sup, madeira, (x + dx, y - 15, 3, 16))
        sup.set_at((x + dx + 1, y - 16), madeira)
        linha(sup, clara, (x + dx, y - 15), (x + dx, y))


def rosacea_quebrada(sup, rng, luzes, cx, cy, raio, cores=VITRAL_APAGADO):
    """Rosácea de vitral numa moldura de pedra, com fatias estilhaçadas (buracos escuros) e uma rachadura."""
    pygame.draw.circle(sup, (78, 82, 70), (cx, cy), raio + 5)
    pygame.draw.circle(sup, (22, 22, 18), (cx, cy), raio + 1)
    faltando = {rng.randrange(16) for _ in range(5)}
    for y in range(cy - raio, cy + raio + 1):
        for x in range(cx - raio, cx + raio + 1):
            d = math.hypot(x - cx, y - cy)
            if d > raio:
                continue
            fatia = int((math.atan2(y - cy, x - cx) + math.pi) / math.tau * 16) % 16
            anel = min(2, int(d / raio * 3))
            if fatia in faltando and anel >= 1:
                cor = (10, 10, 8)
            else:
                cor = cores[(fatia + anel * 3) % len(cores)]
                cor = clarear(cor, 26) if anel == 0 else cor
            sup.set_at((x, y), cor)
    for k in range(16):                                                              # chumbo
        a = k / 16 * math.tau
        linha(sup, (20, 16, 14), (cx + math.cos(a) * raio / 3, cy + math.sin(a) * raio / 3),
              (cx + math.cos(a) * raio, cy + math.sin(a) * raio))
    for r in (raio // 3, 2 * raio // 3, raio):
        pygame.draw.circle(sup, (20, 16, 14), (cx, cy), r, 1)
    for k in range(16):                                                              # lóbulos de pedra na borda
        a = (k + 0.5) / 16 * math.tau
        pygame.draw.circle(sup, (88, 92, 80), (int(cx + math.cos(a) * (raio + 3)), int(cy + math.sin(a) * (raio + 3))), 2)
    rachadura(sup, rng, cx - raio // 2, cy - raio - 3, raio * 2, (14, 12, 10))
    luzes.append([cx, cy, raio + 14, [130, 150, 110], 0.2])


def estatua_do_rato_santo(sup, luzes, x, base, pedra=(100, 104, 92)):
    """O "santo" dos ratos: estátua de um rato de manto e coroa dourada, com um cetro de osso e uma roda de queijo
    nas mãos. Os olhos de vidro vermelho brilham no escuro."""
    escuro, claro = clarear(pedra, -28), clarear(pedra, 22)
    retangulo(sup, escuro, (x - 13, base - 8, 26, 8))                                # pedestal
    retangulo(sup, pedra, (x - 11, base - 11, 22, 3))
    linha(sup, claro, (x - 13, base - 8), (x + 12, base - 8))
    pygame.draw.polygon(sup, pedra, [(x - 10, base - 11), (x + 10, base - 11), (x + 6, base - 38), (x - 6, base - 38)])
    for dx in (-4, 0, 4):                                                            # dobras do manto
        linha(sup, escuro, (x + dx, base - 34), (x + int(dx * 1.6), base - 12))
    linha(sup, claro, (x - 6, base - 38), (x - 10, base - 11))
    for dx in (-5, 5):                                                               # orelhas
        pygame.draw.circle(sup, pedra, (x + dx, base - 47), 3)
        sup.set_at((x + dx, base - 47), escuro)
    pygame.draw.circle(sup, pedra, (x, base - 42), 5)                                # cabeça e focinho
    pygame.draw.polygon(sup, pedra, [(x - 3, base - 40), (x + 3, base - 40), (x, base - 34)])
    sup.set_at((x, base - 34), escuro)
    linha(sup, claro, (x - 4, base - 45), (x - 2, base - 47))
    for dx in (-2, 2):
        sup.set_at((x + dx, base - 43), OLHO)
    luzes.append([x, base - 43, 10, [230, 40, 40], 0.35])
    pygame.draw.polygon(sup, OURO, [(x - 5, base - 46), (x + 5, base - 47), (x + 5, base - 52), (x + 3, base - 49),
                                    (x + 1, base - 54), (x - 1, base - 49), (x - 4, base - 51)])   # coroa torta
    linha(sup, OURO_CLARO, (x - 5, base - 46), (x - 4, base - 51))
    linha(sup, OSSO_CLARO, (x + 9, base - 12), (x + 12, base - 48), 2)               # cetro de osso
    pygame.draw.circle(sup, OSSO_CLARO, (x + 12, base - 49), 2)
    pygame.draw.ellipse(sup, QUEIJO, (x - 6, base - 31, 12, 7))                      # a roda de queijo nas mãos
    linha(sup, clarear(QUEIJO, 26), (x - 5, base - 31), (x + 4, base - 31))
    sup.set_at((x - 2, base - 28), (150, 110, 40))


def cena_catedral_roida(rng):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    degrade(ceu, 0, ALTURA, [(6, 8, 6), (14, 16, 12), (22, 24, 18)])

    # a abóbada da capela (arcos nervurados) com um rombo à esquerda: terra, raízes e um facho de luz doente
    blocos(longe, (0, 22, LARGURA, HORIZONTE - 20), [(54, 56, 48), (60, 62, 52), (48, 50, 44)], rng, alt=6, larg=12,
           junta=(26, 28, 22), lascas=0.2)
    retangulo(longe, PEDRA_ESCURA, (0, 0, LARGURA, 22))
    for x in range(-44, LARGURA + 60, 88):                                           # nervuras da abóbada
        pygame.draw.arc(longe, (82, 86, 72), (x, -6, 88, 64), 0, math.pi, 3)
        pygame.draw.arc(longe, (30, 32, 26), (x + 3, -3, 82, 58), 0.25, math.pi - 0.25, 1)
    rombo = [(80, 0), (150, 0), (146, 10), (134, 18), (120, 22), (102, 19), (90, 12)]
    pygame.draw.polygon(longe, TERRA, rombo)
    pontilhar(longe, (80, 0, 70, 22), (64, 48, 34), 0.3, so_onde_tem=True)
    for _ in range(9):                                                               # raízes penduradas
        x, y = rng.randint(90, 142), rng.randint(10, 18)
        pontos = [(x, y)]
        for _ in range(rng.randint(4, 8)):
            pontos.append((pontos[-1][0] + rng.choice((-1, 0, 1)), pontos[-1][1] + 3))
        pygame.draw.lines(longe, (70, 52, 38), False, pontos, 1)
    poligono_pontilhado(longe, [(100, 18), (132, 18), (166, HORIZONTE + 2), (118, HORIZONTE + 2)], (110, 136, 100), 0.07)
    luzes.append([118, 30, 30, [140, 180, 120], 0.15])
    # a marca da enchente: abaixo dela, pedra encharcada e lodo
    pontilhar(longe, (0, HORIZONTE - 26, LARGURA, 28), (40, 56, 34), 0.45, so_onde_tem=True)
    linha(longe, (30, 40, 26), (0, HORIZONTE - 26), (LARGURA, HORIZONTE - 26))
    # vitrais: dois lancetas laterais quebrados (um remendado com trapo) e a rosácea atrás do santo
    for x, quebrado in ((50, 0.45), (280, 0.3)):
        janela_gotica(longe, rng, x, 30, 22, 52, VITRAL_APAGADO, quebrado=quebrado)
        luzes.append([x + 11, 52, 20, [140, 160, 110], 0.2])
    pygame.draw.polygon(longe, (96, 78, 52), [(55, 64), (63, 63), (64, 70), (56, 71)])    # trapo tapando um buraco
    linha(longe, (130, 106, 72), (55, 64), (63, 63))
    linha(longe, (60, 46, 30), (57, 67), (63, 66))
    rosacea_quebrada(longe, rng, luzes, CENTRO, 42, 21)
    for x in (98, 236):                                                              # estandartes do rato coroado, roídos
        estandarte(longe, rng, x, 26, 18, 44, (100, 20, 28), OURO, simbolo=lambda s, a, b: simbolo_rato_coroado(s, a, b))
        for _ in range(5):
            longe.set_at((x + rng.randint(1, 16), rng.randint(40, 66)), (0, 0, 0, 0))
    retangulo(longe, (0, 0, 0, 0), (0, HORIZONTE + 3, LARGURA, ALTURA))
    contornar(longe)

    # colunas (a da direita partida), o santo dos ratos atrás do altar, bancos, queijo e ouro
    coluna_gotica(meio, 22, 18, HORIZONTE + 4, 12, PEDRA_LIMOSA, rng)
    coluna_gotica(meio, 316, 56, HORIZONTE + 4, 12, PEDRA_LIMOSA, rng)
    for x in range(312, 334):                                                        # topo partido da coluna
        for y in range(52, 52 + rng.randint(3, 9)):
            meio.set_at((x, y), (0, 0, 0, 0))
    for _ in range(7):                                                               # pedras caídas dela
        pedra(meio, PEDRA_LIMOSA, rng.randint(292, 330), HORIZONTE - rng.randint(0, 3), rng.randint(4, 7), rng.randint(3, 4))
    ax = CENTRO
    estatua_do_rato_santo(meio, luzes, ax, HORIZONTE - 16)
    retangulo(meio, (64, 66, 58), (ax - 24, HORIZONTE - 22, 48, 22))                 # altar
    retangulo(meio, (92, 96, 82), (ax - 28, HORIZONTE - 26, 56, 5))
    linha(meio, (120, 124, 108), (ax - 28, HORIZONTE - 26), (ax + 27, HORIZONTE - 26))
    simbolo_rato_coroado(meio, ax, HORIZONTE - 13, (120, 124, 108))                  # entalhado na frente
    for dx in (-14, 10):                                                             # oferendas: queijo no altar
        fatia_de_queijo(meio, ax + dx, HORIZONTE - 27, 6)
    for x in (ax - 36, ax + 36):
        candelabro(meio, luzes, x, HORIZONTE - 2, 24, 3)
    for k in range(2):                                                               # bancos em fileiras
        banco_de_igreja(meio, rng, 40 + k * 6, HORIZONTE - 8 + k * 7, 56)
        banco_de_igreja(meio, rng, 254 - k * 6, HORIZONTE - 8 + k * 7, 56)
    rato_pequeno(meio, 64, HORIZONTE - 22, 1)
    rato_pequeno(meio, 286, HORIZONTE - 22, -1)
    pilha_de_queijo(meio, rng, 124, HORIZONTE + 2, 7)                                # (no facho de luz)
    pilha_de_moedas(meio, rng, 232, HORIZONTE + 2, 30, 12)
    halo(meio, (232, HORIZONTE - 4), 12, OURO_CLARO, 0.25)
    luz_de_borda(meio, (170, 180, 120), dx=0, dy=-1)
    contornar(meio)

    # chão de lajes alagado: lâmina de água no fundo refletindo os vitrais, poças, moedas e farelos
    chao_em_lajes(chao, [(54, 58, 48), (38, 42, 34), (14, 16, 12)], (26, 30, 22), rng)
    agua_de_esgoto(chao, rng, HORIZONTE + 1, HORIZONTE + 8)
    for x0, larg in ((50, 22), (CENTRO - 21, 42), (280, 22)):                         # reflexos dos vitrais na água
        for x in range(x0, x0 + larg):
            for y in range(HORIZONTE + 2, HORIZONTE + 8):
                if rng.random() < 0.35:
                    chao.set_at((x, y), clarear(rng.choice(VITRAL_APAGADO), -20))
    for x in (60, 170, 290):
        poca_de_luz(chao, (x, HORIZONTE + 26), 30, 6, (40, 70, 50), 0.8)
    poca_de_luz(chao, (142, HORIZONTE + 14), 30, 7, (110, 140, 100), 0.45)           # onde o facho bate no chão
    for _ in range(22):
        chao.set_at((rng.randrange(LARGURA), rng.randrange(HORIZONTE + 9, ALTURA - 2)), rng.choice((OURO, QUEIJO)))
    for _ in range(3):
        rato_pequeno(chao, rng.randrange(40, LARGURA - 40), rng.randrange(HORIZONTE + 16, ALTURA - 8), rng.choice((-1, 1)))

    # frente: banco tombado à esquerda e entulho da abóbada à direita
    banco_de_igreja(frente, rng, 18, ALTURA - 2, 36)
    for x in range(LARGURA - 52, LARGURA - 16, 6):
        pedra(frente, clarear(PEDRA_LIMOSA, -16), x, ALTURA - rng.randint(5, 11), rng.randint(6, 11), 10)
    contornar(frente)
    configuracao = {"luzes": luzes, "particulas": [["gota_verde", 6], ["mosca", 8], ["poeira", 14], ["olhos", 6], ["nevoa", 2]],
                    "cor_nevoa": [70, 84, 70]}
    return [ceu, longe, meio, chao, frente], configuracao


def cena_reino_dos_ratos(rng, variante):
    """As 3 zonas do Reino, uma por variante (regioes.json "zonas"): Galerias, Mercado e Catedral Roída.
    As zonas com água (Galerias e Catedral) ganham um chão para cada nível dela (agua_no_chao.py)."""
    camadas, configuracao = (cena_galerias_fetidas, cena_mercado_roedor, cena_catedral_roida)[variante](rng)
    if variante in (0, 2):
        chao_alagado(camadas, configuracao, HORIZONTE, configuracao["luzes"], semente=variante)
    return camadas, configuracao


# O Salão do Trono (sala dos chefes) é feito em resolução dobrada em cenario_salao_do_trono.py (etapa 5R1).
CENAS_DO_REINO = {"reino_dos_ratos": (cena_reino_dos_ratos, 3), "salao_do_trono_roedor": (cena_salao_do_trono, 1)}
