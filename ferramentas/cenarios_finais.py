"""Cenários de destaque das fases finais (Parte 2, Etapa 4), na mesma técnica de cenarios_macabros.py
(352x180, 5 camadas, luzes que tremulam e partículas), com mais textura, volume e luz:

    cidadela_congelada   muralhas de blocos de gelo com pingentes e estandartes congelados, montanhas e a
                         cidadela ao longe; nevasca e AURORA animada (config "aurora", desenhada pelo jogo)
    trono_de_gelo        salão de cristais, colunas que somem ao longe, trono de gelo facetado e luz fria
    catedral_do_eclipse  nave gótica sob o eclipse, vitrais vermelhos, colunas com gárgulas, feixes de luz
    altar_do_eclipse     altar central sob uma rosácea gigante com o eclipse no meio; luz vermelha e dourada

cenarios_macabros.juntar_cenas_novas() põe CENAS_FINAIS no catálogo (por cima das versões simples).
"""
import math

import pygame

from cenarios_macabros import (LARGURA, ALTURA, HORIZONTE, CONTORNO, BAYER, camada, degrade, estrelas, halo,
                               pontilhar, poligono_pontilhado, contornar, luz_de_borda, retangulo, linha, clarear,
                               misturar, arco_gotico, vela)

CENTRO = LARGURA // 2


# ============================================================
# FERRAMENTAS
# ============================================================

def blocos(sup, rect, cores, rng, alt=7, larg=14, junta=(20, 24, 36), brilho=None, lascas=0.25):
    """Parede de blocos (pedra ou gelo): cada bloco com um tom, juntas escuras, aresta de cima clara e lascas."""
    x0, y0, w, h = rect
    area = pygame.Rect(rect)
    for i, y in enumerate(range(y0, y0 + h, alt)):
        desloca = larg // 2 if i % 2 else 0
        for x in range(x0 - desloca, x0 + w, larg):
            r = pygame.Rect(x, y, larg, alt).clip(area)
            if r.w <= 0 or r.h <= 0:
                continue
            pygame.draw.rect(sup, rng.choice(cores), r)
            if brilho:
                linha(sup, brilho, (r.x, r.y), (r.right - 2, r.y))
            linha(sup, junta, (r.x, r.bottom - 1), (r.right - 1, r.bottom - 1))
            linha(sup, junta, (r.right - 1, r.y), (r.right - 1, r.bottom - 1))
            if rng.random() < lascas:
                sup.set_at((rng.randrange(r.x, r.right), rng.randrange(r.y, r.bottom)), junta)


def rachadura(sup, rng, x, y, passos, cor, desce=True):
    for _ in range(passos):
        sup.set_at((int(x), int(y)), cor)
        x += rng.choice((-1, 0, 1))
        y += 1 if desce else rng.choice((-1, 1))
        if not (0 <= x < LARGURA and 0 <= y < ALTURA):
            break


def pingentes(sup, rng, y, x0, x1, cores, densidade=0.5, comp=(3, 12)):
    """Pingentes de gelo pendurados de uma borda (com a aresta da luz mais clara)."""
    for x in range(x0, x1, 2):
        if rng.random() > densidade:
            continue
        c = rng.randint(*comp)
        larg = 1 if c < 6 else 2
        pygame.draw.polygon(sup, cores[0], [(x - larg, y), (x + larg, y), (x, y + c)])
        linha(sup, cores[1], (x - larg + 1, y), (x, y + c - 2))


def neve_no_topo(sup, cor, sombra, rng, espessura=2):
    """Neve assentada em tudo o que tem o céu em cima (pixel desenhado com vazio acima)."""
    mascara = pygame.mask.from_surface(sup)
    topos = [(x, y) for y in range(1, ALTURA) for x in range(LARGURA)
             if mascara.get_at((x, y)) and not mascara.get_at((x, y - 1))]
    for x, y in topos:
        e = espessura + (1 if rng.random() < 0.3 else 0)
        for k in range(e):
            if y - k >= 0:
                sup.set_at((x, y - k), cor)
        sup.set_at((x, y + 1), sombra) if y + 1 < ALTURA and mascara.get_at((x, y + 1)) else None


def prisma(sup, x, base, larg, alt, escuro, claro, brilho, inclina=0):
    """Cristal hexagonal: face da sombra, face da luz, aresta brilhante e ponta facetada."""
    topo = base - alt
    ponta = (x + inclina, topo - larg)
    pygame.draw.polygon(sup, escuro, [(x - larg, base), (x, base), (x + inclina, topo), (x - larg + inclina, topo + 2), ponta])
    pygame.draw.polygon(sup, claro, [(x, base), (x + larg, base), (x + larg + inclina, topo + 2), (x + inclina, topo), ponta])
    linha(sup, brilho, (x, base - 1), (x + inclina, topo))
    linha(sup, brilho, (x + inclina, topo), ponta)


def estandarte(sup, rng, x, topo, larg, alt, pano, borda, simbolo=None, gelo=None):
    """Estandarte pendurado com a barra rasgada (com crosta de gelo, se 'gelo')."""
    retangulo(sup, (60, 50, 44), (x - 2, topo - 2, larg + 4, 2))
    pontos = [(x, topo), (x + larg, topo), (x + larg, topo + alt)]
    for k in range(4, -1, -1):                                         # barra rasgada em pontas
        pontos.append((x + larg * k / 4, topo + alt - (4 if k % 2 else 0) - rng.randint(0, 3)))
    pygame.draw.polygon(sup, pano, pontos)
    linha(sup, borda, (x + 1, topo), (x + 1, topo + alt - 4))
    linha(sup, borda, (x + larg - 1, topo), (x + larg - 1, topo + alt - 4))
    if simbolo:
        simbolo(sup, x + larg // 2, topo + alt // 2 - 2)
    if gelo:
        for _ in range(larg * 2):
            px, py = rng.randrange(x, x + larg), rng.randrange(topo, topo + alt - 4)
            if sup.get_at((px, py))[3]:
                sup.set_at((px, py), gelo)


def simbolo_eclipse(sup, x, y, raio=3, cor=(220, 170, 80)):
    pygame.draw.circle(sup, cor, (x, y), raio + 1)
    pygame.draw.circle(sup, (10, 6, 12), (x, y), raio)
    for k in range(8):
        a = k * math.pi / 4
        sup.set_at((int(x + math.cos(a) * (raio + 3)), int(y + math.sin(a) * (raio + 3))), cor)


def sol_negro(sup, luzes, x, y, raio, rng, cores=((120, 20, 30), (220, 70, 40), (255, 170, 70), (255, 230, 160))):
    """O eclipse: coroa em camadas pontilhadas, labaredas, raios compridos, disco negro e anel de fogo."""
    halo(sup, (x, y), raio * 4.2, cores[0], 0.55)
    halo(sup, (x, y), raio * 2.6, cores[1], 0.6)
    for k in range(24):                                                 # raios da coroa
        a = k / 24 * math.tau + rng.uniform(-0.05, 0.05)
        comp = raio * (1.6 + 0.9 * (k % 2) + rng.uniform(0, 0.5))
        linha(sup, cores[2] if k % 2 else cores[1], (x + math.cos(a) * raio, y + math.sin(a) * raio),
              (x + math.cos(a) * comp, y + math.sin(a) * comp))
    for k in range(7):                                                  # labaredas
        a = rng.uniform(0, math.tau)
        base = (x + math.cos(a) * raio, y + math.sin(a) * raio)
        pygame.draw.polygon(sup, cores[2], [(base[0] + math.cos(a + 1.6) * 2, base[1] + math.sin(a + 1.6) * 2),
                                            (base[0] + math.cos(a) * raio * 0.55, base[1] + math.sin(a) * raio * 0.55),
                                            (base[0] + math.cos(a - 1.6) * 2, base[1] + math.sin(a - 1.6) * 2)])
    pygame.draw.circle(sup, cores[3], (x, y), raio + 2)
    pygame.draw.circle(sup, cores[2], (x, y), raio + 1)
    pygame.draw.circle(sup, (8, 4, 10), (x, y), raio)
    pygame.draw.circle(sup, (40, 14, 30), (x - raio // 4, y - raio // 4), raio - 2, 1)
    luzes.append([x, y, int(raio * 3.4), [255, 140, 70], 0.35])


def janela_gotica(sup, rng, x, topo, larg, alt, cores, chumbo=(16, 8, 12), moldura=(52, 40, 58), quebrado=0.0):
    """Janela ogival com vitral (blocos de cor e chumbo), mainel no meio e quadrifólio no arco."""
    arco_gotico(sup, moldura, x - 3, topo - 3, larg + 6, alt + 4)
    arco_gotico(sup, chumbo, x - 1, topo - 1, larg + 2, alt + 1)
    molde = camada()
    arco_gotico(molde, (255, 255, 255), x, topo, larg, alt)
    for y in range(topo, topo + alt):
        for xx in range(x, x + larg):
            if not molde.get_at((xx, y))[3]:
                continue
            bloco = ((xx - x) // 3) * 7 + ((y - topo) // 4) * 13
            cor = cores[(bloco * 5 + bloco // 7) % len(cores)]
            if (xx - x) % 3 == 0 or (y - topo) % 4 == 0:
                cor = chumbo
            elif rng.random() < quebrado:
                cor = (12, 6, 14)
            elif (y - topo) < alt * 0.35:
                cor = clarear(cor, 18)                                  # a luz entra mais forte em cima
            sup.set_at((xx, y), cor)
    linha(sup, moldura, (x + larg // 2, topo + larg // 2), (x + larg // 2, topo + alt))             # mainel
    c = (x + larg // 2, topo + larg // 2 + 1)
    for dx, dy in ((0, -2), (0, 2), (-2, 0), (2, 0)):                                               # quadrifólio
        pygame.draw.circle(sup, moldura, (c[0] + dx, c[1] + dy), 2, 1)


def coluna_gotica(sup, x, topo, base, larg, cor, rng):
    """Coluna em feixe (três fustes), capitel com folhagem e base larga; luz vinda da direita."""
    escuro, claro = clarear(cor, -18), clarear(cor, 16)
    retangulo(sup, cor, (x, topo, larg, base - topo))
    for k, dx in enumerate((1, larg // 2 - 1, larg - 3)):                                         # fustes
        retangulo(sup, escuro if k == 0 else (claro if k == 2 else cor), (x + dx, topo + 4, 2, base - topo - 8))
    for y in range(topo + 10, base - 6, 9):
        linha(sup, escuro, (x, y), (x + larg - 1, y))
    retangulo(sup, claro, (x - 3, topo, larg + 6, 4))                                              # capitel
    for k in range(0, larg + 6, 3):
        sup.set_at((x - 3 + k, topo + 4), escuro)
    retangulo(sup, cor, (x - 4, base - 6, larg + 8, 6))                                            # base
    linha(sup, claro, (x - 4, base - 6), (x + larg + 3, base - 6))
    for _ in range(3):
        rachadura(sup, rng, x + rng.randrange(larg), topo + rng.randrange(10, base - topo - 20), rng.randint(4, 9), escuro)


def gargula(sup, x, y, olha=1, pedra=(92, 86, 100)):
    """Gárgula agachada numa mísula da coluna (de lado): asa de morcego, chifres, boca aberta e olho aceso."""
    escuro, claro = clarear(pedra, -24), clarear(pedra, 18)
    p = lambda dx, dy: (x + olha * dx, y + dy)                          # desenha virada para 'olha'
    pygame.draw.polygon(sup, escuro, [p(-8, 10), p(8, 10), p(6, 14), p(-6, 14)])                  # mísula
    pygame.draw.polygon(sup, escuro, [p(-4, 14), p(4, 14), p(0, 20)])
    pygame.draw.polygon(sup, escuro, [p(-3, -2), p(-10, -16), p(-12, -10), p(-17, -12), p(-15, -5),
                                      p(-19, -6), p(-12, 3), p(-4, 4)])                           # asa
    for dx, dy in ((-10, -16), (-17, -12), (-19, -6)):
        linha(sup, claro, p(-4, 0), p(dx, dy))
    pygame.draw.ellipse(sup, pedra, pygame.Rect(min(p(-6, 0)[0], p(6, 0)[0]), y - 1, 13, 11))    # corpo agachado
    pygame.draw.polygon(sup, pedra, [p(-6, 10), p(-8, 3), p(-3, 6)])                              # pata de trás
    pygame.draw.polygon(sup, pedra, [p(4, 9), p(8, 4), p(9, 10)])                                 # garras na borda
    cab = p(7, -3)
    pygame.draw.circle(sup, pedra, cab, 4)
    pygame.draw.polygon(sup, pedra, [p(9, -5), p(13, -3), p(12, 0), p(8, 0)])                     # focinho
    linha(sup, escuro, p(8, -1), p(13, 0))                                                        # boca aberta
    linha(sup, claro, p(5, -7), p(2, -11))                                                        # chifres
    linha(sup, claro, p(8, -7), p(7, -11))
    linha(sup, claro, p(4, 0), p(9, 3))                                                           # luz na borda
    sup.set_at(p(9, -4), (255, 70, 50))                                                           # olho aceso


def anjo_sem_cabeca(sup, x, base, pedra=(110, 102, 116)):
    """Estátua de anjo decapitado: túnica com dobras e duas asas de penas abertas."""
    escuro, claro = clarear(pedra, -26), clarear(pedra, 18)
    for lado in (-1, 1):                                                # asas de penas
        for k in range(6):
            raiz = (x + lado * 4, base - 34 + k * 2)
            ponta = (x + lado * (22 - k * 2), base - 58 + k * 6)
            linha(sup, escuro if k % 2 else pedra, raiz, ponta, 3)
            linha(sup, claro, raiz, ponta)
    pygame.draw.polygon(sup, pedra, [(x - 7, base), (x + 7, base), (x + 5, base - 36), (x - 5, base - 36)])   # túnica
    for dx in (-3, 0, 3):
        linha(sup, escuro, (x + dx, base - 30), (x + dx * 1.5, base - 1))
    retangulo(sup, escuro, (x - 3, base - 39, 7, 3))                    # pescoço partido
    linha(sup, claro, (x - 5, base - 36), (x - 7, base))


def candelabro(sup, luzes, x, base, alt, velas=3, cor=(150, 112, 50), luz=(255, 180, 90)):
    linha(sup, cor, (x, base), (x, base - alt), 2)
    retangulo(sup, cor, (x - 4, base - 1, 9, 2))
    larg = (velas - 1) * 4
    linha(sup, cor, (x - larg // 2, base - alt), (x + larg // 2, base - alt))
    for k in range(velas):
        vx = x - larg // 2 + k * 4
        vela(sup, vx, base - alt, 4 + (k % 2) * 2)
        luzes.append([vx, base - alt - 6 - (k % 2) * 2, 12, list(luz), 1.0])


def chao_em_lajes(sup, cores, linha_cor, rng, centro=CENTRO):
    """Lajes em perspectiva: fileiras cada vez mais largas e juntas que fogem para o centro."""
    degrade(sup, HORIZONTE, ALTURA, cores)
    y, passo = HORIZONTE, 3
    while y < ALTURA:
        linha(sup, linha_cor, (0, y), (LARGURA, y))
        passo += 1
        y += passo
    for k in range(-14, 15):
        linha(sup, linha_cor, (centro + k * 10, HORIZONTE), (centro + k * 42, ALTURA))
    for _ in range(90):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA)
        sup.set_at((x, y), clarear(sup.get_at((x, y))[:3], rng.choice((-10, 12))))
    linha(sup, clarear(cores[0], 14), (0, HORIZONTE), (LARGURA, HORIZONTE))


def poca_de_luz(sup, centro, rx, ry, cor, forca=0.5):
    """Mancha de luz pontilhada no chão (luz de vitral, de fogo)."""
    cx, cy = centro
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if 0 <= x < LARGURA and HORIZONTE <= y < ALTURA:
                d = math.hypot((x - cx) / rx, (y - cy) / ry)
                if d < 1 and BAYER[y % 4][x % 4] / 16 < (1 - d) * forca:
                    sup.set_at((x, y), misturar(sup.get_at((x, y))[:3], cor, 0.55))


# ============================================================
# CIDADELA CONGELADA
# ============================================================

GELO_BLOCOS = [(118, 150, 186), (128, 162, 196), (108, 138, 176), (138, 170, 204)]
GELO_ESCURO = (52, 72, 104)
NEVE = (226, 236, 248)
NEVE_SOMBRA = (160, 182, 212)
PINGENTE = ((196, 226, 248), (250, 254, 255))
AURORA = [[90, 255, 170], [70, 220, 230], [150, 120, 255]]


def torre_distante(sup, x, base, larg, alt, rng, cor=(70, 92, 128), janela=(140, 210, 255), luzes=None):
    retangulo(sup, cor, (x, base - alt, larg, alt))
    pygame.draw.polygon(sup, clarear(cor, -12), [(x - 2, base - alt), (x + larg // 2, base - alt - larg - 6), (x + larg + 2, base - alt)])
    for k in range(rng.randint(1, 3)):
        y = base - alt + 6 + k * 9
        retangulo(sup, janela, (x + larg // 2 - 1, y, 2, 3))
        if luzes is not None and k == 0:
            luzes.append([x + larg // 2, y + 1, 8, list(janela), 0.3])


def cena_cidadela_congelada(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    degrade(ceu, 0, HORIZONTE + 4, [(6, 8, 22), (12, 20, 44), (22, 40, 70), (40, 72, 100), (70, 110, 130)])
    estrelas(ceu, rng, 90, 80, cores=((200, 220, 255), (150, 170, 220), (240, 245, 255), (120, 140, 190)))
    lua_x = [70, 290, 200][variante]
    halo(ceu, (lua_x, 22), 30, (60, 90, 140), 0.4)
    pygame.draw.circle(ceu, (230, 240, 255), (lua_x, 22), 9)
    pygame.draw.circle(ceu, (180, 200, 230), (lua_x + 3, 24), 7, draw_top_left=False, draw_bottom_left=False)

    # duas cordilheiras: a de trás azulada e apagada, a da frente com neve e sombra
    for camada_m, base_y, amp, cor, neve_cor in ((longe, 70, 18, (58, 76, 108), (150, 170, 200)),
                                                 (longe, 86, 12, (74, 94, 128), (210, 225, 242))):
        pts = [(0, ALTURA)]
        for x in range(0, LARGURA + 6, 6):
            pts.append((x, base_y + int(amp * math.sin(x * 0.021 + variante * 1.7 + base_y)) + rng.randint(-3, 3)))
        pts.append((LARGURA, ALTURA))
        pygame.draw.polygon(camada_m, cor, pts)
        for (x0, y0), (x1, y1) in zip(pts[1:-2], pts[2:-1]):                # picos nevados (encosta da lua)
            if y1 < base_y + amp * 0.2:
                pygame.draw.polygon(camada_m, neve_cor, [(x0, y0), (x1, y1), (x1, y1 + 5), (x0, y0 + 3)])
    pontilhar(longe, (0, 60, LARGURA, 50), (100, 130, 170), 0.12, so_onde_tem=True)
    # a cidadela ao longe, no alto do penhasco
    cx = [210, 120, 250][variante]
    pygame.draw.polygon(longe, (54, 70, 102), [(cx - 50, 100), (cx - 30, 78), (cx + 34, 76), (cx + 56, 100)])
    for k, (dx, larg, alt) in enumerate(((-26, 8, 26), (-12, 10, 40), (4, 12, 50), (20, 8, 30), (34, 6, 20))):
        torre_distante(longe, cx + dx, 80, larg, alt, rng, luzes=luzes if k % 2 == 0 else None)
    neve_no_topo(longe, (200, 216, 236), (110, 130, 160), rng, 1)

    # a muralha de gelo: blocos, ameias com neve, pingentes, estandartes congelados e braseiros azuis
    topo = HORIZONTE - 46
    blocos(meio, (0, topo, LARGURA, HORIZONTE - topo + 2), GELO_BLOCOS, rng, alt=8, larg=16, junta=GELO_ESCURO,
           brilho=(190, 216, 240), lascas=0.4)
    for x in range(0, LARGURA, 16):                                      # ameias
        blocos(meio, (x, topo - 9, 10, 9), GELO_BLOCOS, rng, alt=9, larg=10, junta=GELO_ESCURO, brilho=(200, 225, 245))
    for _ in range(9):
        rachadura(meio, rng, rng.randrange(LARGURA), topo + rng.randint(4, 20), rng.randint(8, 20), (70, 100, 140))
    if variante == 0:                                                    # torre de vigia com seteiras
        tx = 236
        blocos(meio, (tx, topo - 34, 34, 36), GELO_BLOCOS, rng, alt=8, larg=12, junta=GELO_ESCURO, brilho=(200, 225, 245))
        for x in range(tx, tx + 34, 9):
            blocos(meio, (x, topo - 42, 6, 8), GELO_BLOCOS, rng, alt=8, larg=6, junta=GELO_ESCURO)
        for y in (topo - 24, topo - 10):
            retangulo(meio, (14, 20, 36), (tx + 15, y, 3, 7))
    if variante == 1:                                                    # portão em arco com a grade presa no gelo
        gx = CENTRO - 24
        arco_gotico(meio, (24, 34, 56), gx, topo - 2, 48, HORIZONTE - topo + 2)
        for x in range(gx + 4, gx + 46, 6):
            linha(meio, (60, 70, 86), (x, topo + 12), (x, HORIZONTE))
        for y in range(topo + 18, HORIZONTE, 8):
            linha(meio, (60, 70, 86), (gx + 4, y), (gx + 44, y))
        poligono_pontilhado(meio, [(gx + 2, topo + 30), (gx + 46, topo + 30), (gx + 46, HORIZONTE), (gx + 2, HORIZONTE)],
                            (170, 210, 240), 0.35)                       # gelo cobrindo a grade
        for x in (gx - 30, gx + 64):                                     # guardas congelados em blocos de gelo
            retangulo(meio, (150, 186, 220), (x, HORIZONTE - 34, 14, 34))
            retangulo(meio, (90, 100, 116), (x + 4, HORIZONTE - 30, 6, 22))
            pygame.draw.circle(meio, (90, 100, 116), (x + 7, HORIZONTE - 33), 3)
            linha(meio, (230, 245, 255), (x + 1, HORIZONTE - 33), (x + 1, HORIZONTE - 2))
    if variante == 2:                                                    # brecha na muralha e espada gigante cravada
        pygame.draw.polygon(meio, (0, 0, 0, 0), [(150, topo - 10), (210, topo - 10), (200, topo + 20), (176, topo + 30), (160, topo + 18)])
        for _ in range(10):                                              # entulho de blocos
            x = rng.randint(140, 220)
            pygame.draw.rect(meio, rng.choice(GELO_BLOCOS), (x, HORIZONTE - rng.randint(4, 12), rng.randint(6, 12), 6))
        retangulo(meio, (150, 160, 176), (98, HORIZONTE - 64, 5, 58))
        pygame.draw.polygon(meio, (150, 160, 176), [(98, HORIZONTE - 64), (100, HORIZONTE - 72), (103, HORIZONTE - 64)])
        retangulo(meio, (90, 70, 50), (92, HORIZONTE - 8, 17, 3))
        linha(meio, (230, 240, 255), (99, HORIZONTE - 62), (99, HORIZONTE - 10))
    for x in (34, 316) if variante != 1 else (34, 316):                  # braseiros de fogo azul
        retangulo(meio, (54, 56, 66), (x - 1, HORIZONTE - 20, 3, 20))
        pygame.draw.polygon(meio, (70, 72, 84), [(x - 6, HORIZONTE - 24), (x + 7, HORIZONTE - 24), (x + 4, HORIZONTE - 19), (x - 3, HORIZONTE - 19)])
        pygame.draw.polygon(meio, (120, 200, 255), [(x - 4, HORIZONTE - 24), (x, HORIZONTE - 36), (x + 4, HORIZONTE - 24)])
        pygame.draw.polygon(meio, (220, 245, 255), [(x - 2, HORIZONTE - 24), (x, HORIZONTE - 30), (x + 2, HORIZONTE - 24)])
        luzes.append([x, HORIZONTE - 28, 26, [110, 190, 255], 0.75])
    xs_estandarte = [(90, 250), (80, 270), (60, 280)][variante]
    for x in xs_estandarte:
        estandarte(meio, rng, x, topo + 4, 14, 30, (46, 70, 120), (180, 200, 230), simbolo=lambda s, a, b: (
            pygame.draw.polygon(s, (190, 220, 250), [(a, b - 5), (a + 4, b), (a, b + 5), (a - 4, b)])), gelo=(200, 225, 245))
    luz_de_borda(meio, (200, 220, 255), dx=1, dy=-1)
    neve_no_topo(meio, NEVE, NEVE_SOMBRA, rng, 2)
    pingentes(meio, rng, topo, 0, LARGURA, PINGENTE, 0.35, (3, 10))
    contornar(meio)

    # chão de neve com montes soprados pelo vento, pegadas, gelo e cacos
    degrade(chao, HORIZONTE, ALTURA, [(206, 220, 238), (176, 194, 220), (132, 152, 186), (96, 112, 150)])
    for k in range(9):                                                   # dunas de neve (linhas de vento)
        y0 = HORIZONTE + 4 + k * 7
        pts = [(x, y0 + int(2 * math.sin(x * 0.05 + k))) for x in range(0, LARGURA + 4, 4)]
        pygame.draw.lines(chao, NEVE if k % 2 else NEVE_SOMBRA, False, pts)
    for _ in range(5):                                                   # gelo liso com reflexo
        x, y = rng.randrange(10, LARGURA - 40), rng.randrange(HORIZONTE + 10, ALTURA - 8)
        w = rng.randint(18, 36)
        pygame.draw.ellipse(chao, (120, 160, 200), (x, y, w, 4))
        linha(chao, (220, 240, 255), (x + 3, y + 1), (x + w // 2, y + 1))
    for k in range(10):                                                  # pegadas
        x, y = 60 + k * 22, HORIZONTE + 20 + (k % 2) * 4
        chao.set_at((x, y), (140, 160, 192))
        chao.set_at((x + 1, y), (140, 160, 192))
    for _ in range(60):
        chao.set_at((rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA)), (250, 252, 255))

    # frente: montes de neve nos cantos de baixo e pingentes no alto
    for x0, lado in ((0, 1), (LARGURA, -1)):
        pts = [(x0, ALTURA)] + [(x0 + lado * k * 6, ALTURA - 14 + int(k * k * 0.5)) for k in range(0, 9)] + [(x0 + lado * 54, ALTURA)]
        pygame.draw.polygon(frente, (210, 224, 242), pts)
        pontilhar(frente, (min(x0, x0 + lado * 54), ALTURA - 14, 54, 14), NEVE_SOMBRA, 0.2, so_onde_tem=True)
    contornar(frente, (40, 54, 80))
    return [ceu, longe, meio, chao, frente], {
        "luzes": luzes, "particulas": [["nevasca", 70], ["neve", 30], ["nevoa", 1]], "cor_nevoa": [190, 210, 235],
        "aurora": AURORA}


# ============================================================
# TRONO DE GELO
# ============================================================

def cena_trono_de_gelo(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    # parede do fundo: abóbada de gelo e uma floresta de cristais gigantes
    degrade(ceu, 0, HORIZONTE + 4, [(6, 12, 30), (14, 30, 62), (30, 62, 102), (60, 104, 146)])
    for x in range(-20, LARGURA + 40, 56):                               # nervuras da abóbada
        pygame.draw.arc(ceu, (90, 140, 190), (x, -36, 56, 72), math.pi, math.tau, 2)
    for _ in range(26):
        x = rng.randrange(-10, LARGURA + 10)
        alt = rng.randint(30, 80)
        prisma(ceu, x, HORIZONTE + 2, rng.randint(5, 10), alt, (40, 76, 120), (70, 116, 164), (150, 200, 240),
               rng.randint(-3, 3))
    pontilhar(ceu, (0, 30, LARGURA, HORIZONTE - 30), (30, 60, 100), 0.18, so_onde_tem=True)  # névoa fria entre os cristais
    # janela alta: o luar entra e cai em feixes sobre o trono
    halo(ceu, (CENTRO, 12), 26, (150, 210, 255), 0.6)
    pygame.draw.circle(ceu, (220, 240, 255), (CENTRO, 12), 8)
    poligono_pontilhado(longe, [(CENTRO - 8, 10), (CENTRO + 8, 10), (CENTRO + 46, HORIZONTE), (CENTRO - 46, HORIZONTE)],
                        (170, 220, 255), 0.22)

    # colunas de cristal em duas fileiras que somem ao longe
    for k, (dx, alt, larg) in enumerate(((60, 96, 8), (96, 84, 6), (124, 74, 5))):
        for lado in (-1, 1):
            x = CENTRO + lado * dx
            prisma(longe, x, HORIZONTE - k * 3, larg, alt, (60, 104, 156), (110, 164, 214), (210, 240, 255))
            luzes.append([x, HORIZONTE - alt // 2, 14, [140, 210, 255], 0.3])

    # o trono: degraus, assento facetado e um leque de lâminas de cristal no encosto
    for k, larg in enumerate((70, 58, 46)):
        y = HORIZONTE - 4 - k * 4
        retangulo(longe, (120, 170, 214), (CENTRO - larg // 2, y, larg, 4))
        linha(longe, (220, 240, 255), (CENTRO - larg // 2, y), (CENTRO + larg // 2 - 1, y))
    for k in range(-5, 6):                                               # encosto em leque
        a = -math.pi / 2 + k * 0.17
        comp = 58 - abs(k) * 6
        base = (CENTRO + k * 2, HORIZONTE - 30)
        ponta = (base[0] + math.cos(a) * comp, base[1] + math.sin(a) * comp)
        pygame.draw.polygon(longe, (150, 200, 240) if k % 2 else (110, 166, 220),
                            [(base[0] - 3, base[1]), ponta, (base[0] + 3, base[1])])
        linha(longe, (230, 248, 255), base, ponta)
    pygame.draw.polygon(longe, (130, 184, 230), [(CENTRO - 18, HORIZONTE - 16), (CENTRO + 18, HORIZONTE - 16),
                                                 (CENTRO + 14, HORIZONTE - 34), (CENTRO - 14, HORIZONTE - 34)])
    pygame.draw.polygon(longe, (90, 140, 196), [(CENTRO - 20, HORIZONTE - 12), (CENTRO + 20, HORIZONTE - 12),
                                                (CENTRO + 18, HORIZONTE - 18), (CENTRO - 18, HORIZONTE - 18)])
    halo(longe, (CENTRO, HORIZONTE - 74), 16, (180, 230, 255), 0.7)     # gema fria no topo do encosto
    pygame.draw.polygon(longe, (230, 250, 255), [(CENTRO, HORIZONTE - 82), (CENTRO + 4, HORIZONTE - 74),
                                                 (CENTRO, HORIZONTE - 66), (CENTRO - 4, HORIZONTE - 74)])
    luzes.append([CENTRO, HORIZONTE - 74, 34, [150, 220, 255], 0.5])
    contornar(longe, (14, 24, 44))

    # na frente das paredes: pilares enormes de gelo com pingentes e um lustre de cristal
    for x, larg in ((14, 22), (LARGURA - 36, 22)):
        retangulo(meio, (150, 196, 232), (x, 0, larg, HORIZONTE + 4))
        retangulo(meio, (110, 160, 210), (x + larg - 7, 0, 7, HORIZONTE + 4))
        linha(meio, (230, 248, 255), (x + 2, 0), (x + 2, HORIZONTE + 2))
        for y in range(8, HORIZONTE, 13):
            linha(meio, (90, 140, 196), (x, y), (x + larg - 1, y + 2))
        retangulo(meio, (170, 210, 240), (x - 4, HORIZONTE - 2, larg + 8, 6))
    linha(meio, (110, 150, 190), (CENTRO, 0), (CENTRO, 10))              # lustre
    pygame.draw.polygon(meio, (170, 214, 245), [(CENTRO - 20, 10), (CENTRO + 20, 10), (CENTRO + 10, 16), (CENTRO - 10, 16)])
    for k in range(-4, 5):
        pygame.draw.polygon(meio, (200, 235, 255), [(CENTRO + k * 5 - 1, 15), (CENTRO + k * 5 + 1, 15), (CENTRO + k * 5, 22 + (k % 2) * 4)])
        luzes.append([CENTRO + k * 5, 20, 8, [170, 230, 255], 0.6]) if k % 2 == 0 else None
    pingentes(meio, rng, 0, 0, LARGURA, PINGENTE, 0.3, (4, 14))
    contornar(meio, (14, 24, 44))

    # chão de gelo polido: reflexos do trono e das colunas, linhas de perspectiva e geada
    degrade(chao, HORIZONTE, ALTURA, [(160, 200, 234), (120, 164, 210), (76, 116, 168), (40, 70, 116)])
    poligono_pontilhado(chao, [(CENTRO - 30, HORIZONTE), (CENTRO + 30, HORIZONTE), (CENTRO + 22, HORIZONTE + 40),
                               (CENTRO - 22, HORIZONTE + 40)], (200, 236, 255), 0.35)        # reflexo do trono
    for k, dx in enumerate((60, 96, 124)):
        for lado in (-1, 1):
            x = CENTRO + lado * dx
            poligono_pontilhado(chao, [(x - 4, HORIZONTE), (x + 4, HORIZONTE), (x + 2, HORIZONTE + 26 - k * 5), (x - 2, HORIZONTE + 26 - k * 5)],
                                (190, 228, 252), 0.3)
    for k in range(-12, 13):
        linha(chao, (190, 225, 250), (CENTRO + k * 9, HORIZONTE), (CENTRO + k * 38, ALTURA))
    for _ in range(14):                                                  # geada: estrelinhas de seis pontas
        x, y = rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 8, ALTURA - 6)
        for a in range(3):
            ang = a * math.pi / 3
            linha(chao, (230, 246, 255), (x - math.cos(ang) * 3, y - math.sin(ang) * 2), (x + math.cos(ang) * 3, y + math.sin(ang) * 2))
    # frente: cristais brotando nos cantos de baixo
    for x, lado in ((10, 1), (LARGURA - 10, -1)):
        for k in range(4):
            prisma(frente, x + lado * k * 9, ALTURA + 2, 4 + k % 2, 18 + (3 - k) * 7, (70, 120, 176), (130, 186, 232),
                   (230, 248, 255), lado * 2)
    contornar(frente, (14, 24, 44))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["neve", 24], ["cintila", 40], ["nevoa", 1]],
                                              "cor_nevoa": [170, 210, 245]}


# ============================================================
# CATEDRAL DO ECLIPSE
# ============================================================

VITRAL_VERMELHO = [(150, 20, 34), (196, 36, 40), (120, 14, 30), (230, 90, 50), (220, 160, 60), (90, 20, 60)]
PEDRA = (70, 58, 76)


def cena_catedral_do_eclipse(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    # céu do eclipse visto pelo telhado em ruínas
    degrade(ceu, 0, HORIZONTE + 4, [(10, 4, 12), (30, 8, 22), (64, 14, 30), (96, 30, 36)])
    estrelas(ceu, rng, 40, 50, cores=((200, 150, 150), (240, 200, 180)))
    for _ in range(5):                                                   # nuvens finas acesas por baixo
        y = rng.randint(30, 70)
        x = rng.randint(-20, LARGURA)
        pontilhar(ceu, (x, y, rng.randint(40, 90), 3), (120, 40, 44), 0.5)
        pontilhar(ceu, (x + 4, y + 2, rng.randint(30, 60), 1), (200, 90, 60), 0.4)
    sol_negro(ceu, luzes, [CENTRO, 110, 240][variante], 26, 13, rng)

    # paredes da nave: arcos ogivais, vitrais vermelhos, abóbada nervurada aberta
    retangulo(longe, (40, 30, 46), (0, 46, LARGURA, HORIZONTE - 44))
    blocos(longe, (0, 46, LARGURA, HORIZONTE - 44), [(40, 30, 46), (44, 34, 50), (36, 28, 42)], rng, alt=6, larg=12,
           junta=(26, 18, 30), lascas=0.15)
    for x in range(-30, LARGURA + 60, 74):                               # abóbada em ruínas (nervuras partidas)
        pygame.draw.arc(longe, (56, 44, 64), (x, 6, 74, 84), 0, math.pi, 3)
        pygame.draw.arc(longe, (30, 22, 36), (x + 2, 8, 70, 80), 0.3, math.pi - 0.3, 1)
    for k, x in enumerate(range(26, LARGURA, 74)):
        janela_gotica(longe, rng, x, 52, 22, 50, VITRAL_VERMELHO, quebrado=0.06 + 0.06 * ((k + variante) % 2))
        luzes.append([x + 11, 72, 26, [230, 60, 50], 0.25])
        poligono_pontilhado(chao, [(x + 4, HORIZONTE), (x + 20, HORIZONTE), (x + 52, ALTURA), (x + 6, ALTURA)],
                            (150, 30, 40), 0.22)                         # a luz vermelha cai no chão
    pontilhar(longe, (0, 46, LARGURA, HORIZONTE - 44), (24, 16, 28), 0.15, so_onde_tem=True)
    contornar(longe)

    # colunas em feixe com gárgulas, estandartes do culto e candelabros
    xs = [(8, 108, 222, 322), (8, 96, 236, 322), (8, 130, 200, 322)][variante]
    for k, x in enumerate(xs):
        coluna_gotica(meio, x, 4, HORIZONTE + 4, 14, PEDRA, rng)
        olha = 1 if x < CENTRO else -1
        gx, gy = x + 7 + olha * 13, 30 + (k % 2) * 8
        gargula(meio, gx, gy, olha)
        luzes.append([gx + olha * 9, gy - 4, 7, [255, 70, 50], 0.6])
    for x in [(60, 280), (52, 286), (70, 268)][variante]:
        estandarte(meio, rng, x, 10, 16, 44, (110, 16, 28), (200, 150, 60), simbolo=lambda s, a, b: simbolo_eclipse(s, a, b))
    for x in [(52, 296), (40, 306), (60, 290)][variante]:
        candelabro(meio, luzes, x, HORIZONTE + 2, 26, 3)
    if variante == 0:                                                    # fileiras de bancos
        for x in (40, 252):
            for k in range(2):
                retangulo(meio, (54, 34, 28), (x + k * 6, HORIZONTE - 8 + k * 3, 58, 3))
                retangulo(meio, (40, 26, 22), (x + k * 6, HORIZONTE - 14 + k * 3, 3, 9))
    if variante == 1:                                                    # coluna caída e cacos
        pygame.draw.polygon(meio, PEDRA, [(150, HORIZONTE), (212, HORIZONTE - 10), (216, HORIZONTE - 2), (152, HORIZONTE + 6)])
        for _ in range(8):
            pygame.draw.rect(meio, clarear(PEDRA, rng.randint(-14, 10)), (rng.randint(140, 220), HORIZONTE - rng.randint(0, 6), 4, 3))
    if variante == 2:                                                    # braseiro do culto diante de um anjo sem cabeça
        anjo_sem_cabeca(meio, 176, HORIZONTE - 8)
        retangulo(meio, (60, 50, 50), (172, HORIZONTE - 8, 8, 8))
        pygame.draw.polygon(meio, (255, 120, 40), [(169, HORIZONTE - 8), (176, HORIZONTE - 22), (183, HORIZONTE - 8)])
        luzes.append([176, HORIZONTE - 14, 30, [255, 110, 50], 0.9])
    luz_de_borda(meio, (200, 80, 70), dx=-1, dy=-1)
    contornar(meio)

    # chão de lajes, poças de luz dos vitrais, cacos de vidro e o círculo do culto
    chao_em_lajes(chao, [(54, 42, 58), (38, 28, 42), (16, 10, 20)], (24, 16, 28), rng)
    for x in range(26, LARGURA, 74):
        poca_de_luz(chao, (x + 26, HORIZONTE + 30), 20, 8, (200, 40, 50), 0.6)
    for _ in range(24):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 4, ALTURA - 2)
        cor = rng.choice(VITRAL_VERMELHO)
        chao.set_at((x, y), cor)
        chao.set_at((x + 1, y), clarear(cor, 40))
    if variante == 1:
        pygame.draw.ellipse(chao, (150, 40, 40), (CENTRO - 40, HORIZONTE + 14, 80, 18), 1)
        pygame.draw.ellipse(chao, (150, 40, 40), (CENTRO - 32, HORIZONTE + 16, 64, 14), 1)
    # frente: bases de coluna quebradas nos cantos
    for x in (0, LARGURA - 30):
        pygame.draw.polygon(frente, PEDRA, [(x, ALTURA), (x + 4, ALTURA - 16), (x + 22, ALTURA - 20), (x + 30, ALTURA)])
        linha(frente, clarear(PEDRA, 16), (x + 4, ALTURA - 16), (x + 22, ALTURA - 20))
    contornar(frente)
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["poeira", 24], ["cinza", 18], ["brasa", 6]],
                                              "cor_nevoa": [90, 30, 50]}


# ============================================================
# ALTAR DO ECLIPSE
# ============================================================

OURO = (220, 170, 70)
OURO_CLARO = (255, 220, 130)


def rosacea_do_eclipse(sup, luzes, cx, cy, raio, rng):
    """Rosácea gigante de vidro vermelho e dourado, com o eclipse visto pelo vidro claro do meio."""
    pygame.draw.circle(sup, (60, 46, 66), (cx, cy), raio + 5)
    pygame.draw.circle(sup, CONTORNO, (cx, cy), raio + 1)
    cores = [(170, 24, 36), (210, 60, 40), (230, 150, 60), (120, 16, 40), (250, 200, 100)]
    for y in range(cy - raio, cy + raio + 1):
        for x in range(cx - raio, cx + raio + 1):
            d = math.hypot(x - cx, y - cy)
            if d > raio or d < raio * 0.3:
                continue
            a = math.atan2(y - cy, x - cx)
            fatia = int((a + math.pi) / math.tau * 16)
            anel = int((d - raio * 0.3) / (raio * 0.7 / 3))
            cor = cores[(fatia + anel * 2) % len(cores)]
            if (fatia + anel) % 2:
                cor = clarear(cor, 16)
            sup.set_at((x, y), cor)
    for k in range(16):                                                 # chumbo: raios e anéis
        a = k / 16 * math.tau
        linha(sup, (24, 12, 18), (cx + math.cos(a) * raio * 0.3, cy + math.sin(a) * raio * 0.3),
              (cx + math.cos(a) * raio, cy + math.sin(a) * raio))
    for r in (raio * 0.3, raio * 0.53, raio * 0.77, raio):
        pygame.draw.circle(sup, (24, 12, 18), (cx, cy), int(r), 1)
    for k in range(16):                                                 # lóbulos de pedra na borda
        a = (k + 0.5) / 16 * math.tau
        pygame.draw.circle(sup, (70, 54, 76), (int(cx + math.cos(a) * (raio + 3)), int(cy + math.sin(a) * (raio + 3))), 3)
    # o centro é vidro claro: vê-se o céu vermelho e o sol negro
    pygame.draw.circle(sup, (90, 24, 30), (cx, cy), int(raio * 0.3) - 1)
    sol_negro(sup, luzes, cx, cy, int(raio * 0.18), rng)


def cena_altar_do_eclipse(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    degrade(ceu, 0, HORIZONTE + 4, [(14, 6, 16), (28, 14, 30), (44, 24, 44)])
    blocos(ceu, (0, 0, LARGURA, HORIZONTE + 4), [(40, 30, 46), (46, 34, 52), (36, 26, 42)], rng, alt=6, larg=12,
           junta=(24, 16, 28), lascas=0.12)
    cx, cy = CENTRO, 50
    halo(ceu, (cx, cy), 90, (120, 30, 30), 0.35)
    rosacea_do_eclipse(ceu, luzes, cx, cy, 44, rng)
    for x in (40, 290):                                                 # janelas altas laterais
        janela_gotica(ceu, rng, x, 30, 18, 66, VITRAL_VERMELHO)
        luzes.append([x + 9, 56, 22, [230, 70, 50], 0.25])
    # feixes vermelhos e dourados da rosácea descendo até o altar
    for k, (dx0, dx1, cor) in enumerate(((-30, -70, (190, 40, 40)), (-10, -26, (240, 170, 70)), (10, 26, (240, 170, 70)),
                                         (30, 70, (190, 40, 40)))):
        poligono_pontilhado(longe, [(cx + dx0 - 4, cy + 20), (cx + dx0 + 4, cy + 20), (cx + dx1 + 10, HORIZONTE), (cx + dx1 - 10, HORIZONTE)],
                            cor, 0.2)

    # abside: arcos em volta e o altar sobre degraus, com frontal dourado e o símbolo do eclipse
    for x in (66, 248):
        arco_gotico(longe, (34, 24, 40), x, 64, 38, HORIZONTE - 64)
        arco_gotico(longe, (20, 12, 24), x + 6, 72, 26, HORIZONTE - 72)
    contornar(longe)
    for k, larg in enumerate((120, 100, 82)):                            # degraus
        y = HORIZONTE - 4 - k * 5
        retangulo(meio, (74, 60, 82), (cx - larg // 2, y, larg, 5))
        linha(meio, (110, 92, 118), (cx - larg // 2, y), (cx + larg // 2 - 1, y))
    retangulo(meio, (86, 70, 94), (cx - 32, HORIZONTE - 40, 64, 22))     # altar
    retangulo(meio, (120, 24, 36), (cx - 26, HORIZONTE - 38, 52, 20))
    for x in range(cx - 26, cx + 26, 4):                                 # franja dourada
        meio.set_at((x, HORIZONTE - 19), OURO)
    simbolo_eclipse(meio, cx, HORIZONTE - 29, 4, OURO)
    retangulo(meio, OURO, (cx - 36, HORIZONTE - 43, 72, 3))
    linha(meio, OURO_CLARO, (cx - 36, HORIZONTE - 43), (cx + 35, HORIZONTE - 43))
    pygame.draw.polygon(meio, OURO, [(cx - 4, HORIZONTE - 43), (cx, HORIZONTE - 56), (cx + 4, HORIZONTE - 43)])   # cálice/punhal
    for x in (cx - 50, cx + 50):                                         # candelabros altos
        candelabro(meio, luzes, x, HORIZONTE - 14, 30, 5, OURO, (255, 200, 110))
    for x, olha in ((cx - 92, 1), (cx + 92, -1)):                        # estátuas de acólitos com braseiros
        pygame.draw.polygon(meio, (90, 80, 96), [(x - 8, HORIZONTE), (x + 8, HORIZONTE), (x + 5, HORIZONTE - 34), (x - 5, HORIZONTE - 34)])
        pygame.draw.circle(meio, (90, 80, 96), (x, HORIZONTE - 38), 6)
        pygame.draw.polygon(meio, (20, 12, 24), [(x - 4 + olha * 2, HORIZONTE - 40), (x + 4 + olha * 2, HORIZONTE - 40), (x + olha * 2, HORIZONTE - 34)])
        bx = x + olha * 10
        retangulo(meio, (70, 56, 50), (bx - 4, HORIZONTE - 30, 9, 4))
        pygame.draw.polygon(meio, (255, 110, 40), [(bx - 4, HORIZONTE - 30), (bx, HORIZONTE - 42), (bx + 4, HORIZONTE - 30)])
        pygame.draw.polygon(meio, (255, 220, 120), [(bx - 2, HORIZONTE - 30), (bx, HORIZONTE - 36), (bx + 2, HORIZONTE - 30)])
        luzes.append([bx, HORIZONTE - 34, 26, [255, 110, 50], 0.85])
    for x in (12, LARGURA - 26):                                         # colunas em feixe nos cantos
        coluna_gotica(meio, x, 0, HORIZONTE + 4, 14, PEDRA, rng)
    for x in (cx - 70, cx + 70):                                         # correntes penduradas
        for y in range(0, 26, 3):
            meio.set_at((x + (y // 3) % 2, y), (80, 70, 70))
    luz_de_borda(meio, (240, 150, 80), dx=0, dy=-1)
    contornar(meio)

    # chão: tapete vermelho com bordas douradas, poça de luz dourada sob a rosácea, círculo ritual
    chao_em_lajes(chao, [(60, 46, 62), (42, 30, 46), (18, 10, 22)], (28, 18, 30), rng)
    pygame.draw.polygon(chao, (120, 20, 30), [(cx - 18, HORIZONTE), (cx + 18, HORIZONTE), (cx + 58, ALTURA), (cx - 58, ALTURA)])
    linha(chao, OURO, (cx - 18, HORIZONTE), (cx - 58, ALTURA))
    linha(chao, OURO, (cx + 18, HORIZONTE), (cx + 58, ALTURA))
    poca_de_luz(chao, (cx, HORIZONTE + 16), 70, 14, (250, 190, 90), 0.55)
    pygame.draw.ellipse(chao, OURO, (cx - 64, HORIZONTE + 22, 128, 26), 1)
    for k in range(12):                                                  # runas do círculo
        a = k / 12 * math.tau
        x, y = int(cx + math.cos(a) * 58), int(HORIZONTE + 35 + math.sin(a) * 11)
        chao.set_at((x, y), OURO_CLARO)
    # frente: velas no chão nos cantos
    for x in (14, 22, 30, LARGURA - 32, LARGURA - 24, LARGURA - 16):
        retangulo(frente, (210, 196, 170), (x, ALTURA - 10 - (x % 3) * 2, 3, 10 + (x % 3) * 2))
        frente.set_at((x + 1, ALTURA - 12 - (x % 3) * 2), (255, 220, 120))
        luzes.append([x + 1, ALTURA - 13 - (x % 3) * 2, 10, [255, 190, 90], 1.0])
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["brasa", 14], ["cinza", 14], ["poeira", 16], ["nevoa", 1]],
                                              "cor_nevoa": [110, 40, 50]}


CENAS_FINAIS = {
    "cidadela_congelada": (cena_cidadela_congelada, 3), "trono_de_gelo": (cena_trono_de_gelo, 1),
    "catedral_do_eclipse": (cena_catedral_do_eclipse, 3), "altar_do_eclipse": (cena_altar_do_eclipse, 1),
}
