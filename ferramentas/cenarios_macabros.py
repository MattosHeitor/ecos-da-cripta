"""Gera os cenários macabros em pixel art (camadas PNG + cenarios.json).

    python ferramentas/cenarios_macabros.py

Cada cenário tem até 5 camadas de 352 x 180 pixels (o jogo amplia 4x):
    ceu    fundo mais distante (céu, parede, teto da caverna)
    longe  silhuetas distantes (morros, arcos, tenda)
    meio   árvores, pilares, lanternas...
    chao   o chão onde os personagens pisam (começa por volta de y = 118)
    frente detalhes que ficam NA FRENTE dos personagens (só nas bordas)

As 16 colunas a mais de cada lado deixam as camadas balançarem (paralaxe).
Também grava em cenarios.json as luzes (que tremulam) e as partículas de cada cena.

Estilo: paleta escura puxando para roxo/azul, luz quente de vela e fogo,
contorno escuro nas silhuetas e "pontilhado" (dithering) nos degradês.
"""

import json
import math
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

LARGURA, ALTURA = 352, 180
MARGEM = 16
HORIZONTE = 118          # onde o chão começa (os pés ficam por volta de y = 133 a 140)
CONTORNO = (8, 5, 10)
PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "cenarios_macabros")

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


# ============================================================
# FERRAMENTAS DE DESENHO (pixel por pixel)
# ============================================================

def camada():
    sup = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    sup.fill((0, 0, 0, 0))
    return sup


def misturar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def clarear(cor, quanto):
    return tuple(max(0, min(255, int(c + quanto))) for c in cor[:3])


def degrade(sup, y0, y1, cores, x0=0, x1=LARGURA):
    """Degradê vertical com pontilhado (as cores se misturam num xadrez organizado)."""
    partes = len(cores) - 1
    for y in range(max(0, y0), min(ALTURA, y1)):
        t = (y - y0) / max(1, y1 - y0 - 1) * partes
        i = min(int(t), partes - 1)
        fracao = t - i
        for x in range(x0, x1):
            sup.set_at((x, y), cores[i + 1] if BAYER[y % 4][x % 4] / 16 < fracao else cores[i])


def pontilhar(sup, rect, cor, densidade, so_onde_tem=False):
    """Espalha uma cor num xadrez (0 a 1). so_onde_tem: só pinta pixels já desenhados."""
    x0, y0, w, h = rect
    for y in range(max(0, y0), min(ALTURA, y0 + h)):
        for x in range(max(0, x0), min(LARGURA, x0 + w)):
            if BAYER[y % 4][x % 4] / 16 < densidade:
                if so_onde_tem and sup.get_at((x, y))[3] == 0:
                    continue
                sup.set_at((x, y), cor)


def poligono_pontilhado(sup, pontos, cor, densidade):
    """Polígono "transparente" feito de pontinhos (feixes e cones de luz)."""
    molde = camada()
    pygame.draw.polygon(molde, (255, 255, 255), pontos)
    mascara = pygame.mask.from_surface(molde)
    for y in range(ALTURA):
        for x in range(LARGURA):
            if mascara.get_at((x, y)) and BAYER[y % 4][x % 4] / 16 < densidade:
                sup.set_at((x, y), cor)


def halo(sup, centro, raio, cor, forca=0.5):
    """Brilho pontilhado em volta de um ponto (lua, vela, cristal)."""
    cx, cy = centro
    for y in range(int(cy - raio), int(cy + raio) + 1):
        for x in range(int(cx - raio), int(cx + raio) + 1):
            if 0 <= x < LARGURA and 0 <= y < ALTURA:
                d = math.hypot(x - cx, y - cy) / raio
                if d < 1 and BAYER[y % 4][x % 4] / 16 < (1 - d) * forca:
                    sup.set_at((x, y), cor)


def contornar(sup, cor=CONTORNO):
    """Contorno escuro de 1 pixel em volta de tudo o que foi desenhado."""
    mascara = pygame.mask.from_surface(sup)
    novos = []
    for y in range(ALTURA):
        for x in range(LARGURA):
            if not mascara.get_at((x, y)):
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < LARGURA and 0 <= ny < ALTURA and mascara.get_at((nx, ny)):
                        novos.append((x, y))
                        break
    for ponto in novos:
        sup.set_at(ponto, cor)


def luz_de_borda(sup, cor, dx=-1, dy=-1, base=None):
    """Clareia as bordas viradas para a luz (dá volume às silhuetas)."""
    mascara = pygame.mask.from_surface(sup)
    pontos = []
    for y in range(ALTURA):
        for x in range(LARGURA):
            if mascara.get_at((x, y)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < LARGURA and 0 <= ny < ALTURA) or not mascara.get_at((nx, ny)):
                    if base is None or sup.get_at((x, y))[:3] == base:
                        pontos.append((x, y))
    for ponto in pontos:
        sup.set_at(ponto, cor)


def retangulo(sup, cor, rect):
    pygame.draw.rect(sup, cor, rect)


def linha(sup, cor, a, b, largura=1):
    pygame.draw.line(sup, cor, a, b, largura)


def estrelas(sup, rng, quantidade, ate_y, cores=((150, 140, 170), (210, 200, 220), (110, 100, 140))):
    for _ in range(quantidade):
        x, y = rng.randrange(LARGURA), rng.randrange(ate_y)
        sup.set_at((x, y), rng.choice(cores))


def lua(sup, centro, raio, cor, cor_sombra, cor_halo, crateras=True, rng=None):
    halo(sup, centro, raio * 2.4, cor_halo, 0.35)
    pygame.draw.circle(sup, cor, centro, raio)
    # sombra num dos lados
    pygame.draw.circle(sup, cor_sombra, (centro[0] + raio // 3, centro[1] + raio // 4), raio - 2, draw_top_left=False,
                       draw_bottom_left=False)
    if crateras and rng is not None:
        for _ in range(5):
            r = rng.randint(1, max(1, raio // 4))
            pygame.draw.circle(sup, cor_sombra, (centro[0] + rng.randint(-raio // 2, raio // 2),
                                                 centro[1] + rng.randint(-raio // 2, raio // 2)), r)


def galho(sup, cor, x, y, angulo, comprimento, grossura, rng, profundidade=0):
    """Galho de árvore morta, que se divide em galhos menores."""
    fim_x = x + math.cos(angulo) * comprimento
    fim_y = y + math.sin(angulo) * comprimento
    linha(sup, cor, (x, y), (fim_x, fim_y), max(1, int(grossura)))
    if profundidade < 4 and comprimento > 4:
        for desvio in (-rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.7)):
            if rng.random() < 0.85:
                galho(sup, cor, fim_x, fim_y, angulo + desvio, comprimento * rng.uniform(0.55, 0.75),
                      grossura * 0.65, rng, profundidade + 1)


def arvore_morta(sup, cor, x, base, altura, rng, grossura=4):
    """Tronco torto com galhos secos."""
    xs = x
    for y in range(base, base - altura, -1):
        largura = max(1, int(grossura * (0.6 + 0.4 * (y - (base - altura)) / altura)))
        xs += rng.choice((0, 0, 0, 1, -1)) * 0.5
        retangulo(sup, cor, (int(xs) - largura // 2, y, largura, 1))
    for i in range(rng.randint(3, 5)):
        y = base - altura + rng.randint(0, altura // 2)
        angulo = -math.pi / 2 + rng.uniform(-1.2, 1.2)
        galho(sup, cor, xs, y, angulo, rng.randint(8, 18), max(1, grossura * 0.5), rng)
    # raízes
    for lado in (-1, 1):
        linha(sup, cor, (x, base - 2), (x + lado * rng.randint(4, 8), base + 1), 2)


def teia(sup, cor, centro, raio, rng):
    cx, cy = centro
    raios = rng.randint(6, 9)
    for i in range(raios):
        a = i / raios * math.tau + rng.uniform(-0.1, 0.1)
        linha(sup, cor, (cx, cy), (cx + math.cos(a) * raio, cy + math.sin(a) * raio))
    for r in range(3, int(raio), 3):
        pontos = [(cx + math.cos(i / raios * math.tau) * r, cy + math.sin(i / raios * math.tau) * r) for i in range(raios + 1)]
        pygame.draw.lines(sup, cor, False, pontos)


def cranio(sup, x, y, cor=(196, 186, 166)):
    retangulo(sup, cor, (x, y, 4, 3))
    retangulo(sup, cor, (x + 1, y + 3, 2, 1))
    sup.set_at((x + 1, y + 1), CONTORNO)
    sup.set_at((x + 2, y + 1), CONTORNO)


def osso(sup, x, y, cor=(186, 176, 156)):
    linha(sup, cor, (x, y), (x + 5, y + 1))
    sup.set_at((x - 1, y - 1), cor)
    sup.set_at((x + 6, y + 2), cor)


def vela(sup, x, y, altura=4, cor=(210, 200, 170)):
    retangulo(sup, cor, (x, y - altura, 2, altura))
    sup.set_at((x, y - altura - 1), (255, 200, 90))
    sup.set_at((x, y - altura - 2), (255, 240, 170))


def arco_gotico(sup, cor, x, topo, largura, altura):
    """Arco ogival (pontudo) preenchido."""
    meio = largura / 2
    for dy in range(altura):
        y = topo + dy
        if dy < meio * 1.2:
            t = dy / (meio * 1.2)
            metade = meio * math.sqrt(max(0.0, 1 - (1 - t) ** 2))
        else:
            metade = meio
        retangulo(sup, cor, (int(x + meio - metade), y, max(1, int(metade * 2)), 1))


def pedra(sup, cor, x, y, w, h):
    pygame.draw.ellipse(sup, cor, (x, y, w, h))
    pygame.draw.ellipse(sup, clarear(cor, 18), (x + 1, y, w - 3, max(1, h // 2)))


def chao_basico(sup, cores, rng, inicio=HORIZONTE):
    """Chão com degradê e textura (pedrinhas e sulcos)."""
    degrade(sup, inicio, ALTURA, cores)
    for _ in range(140):
        x, y = rng.randrange(LARGURA), rng.randrange(inicio + 2, ALTURA)
        sup.set_at((x, y), clarear(cores[0], rng.choice((-8, 10, 14))))
    # borda do horizonte
    linha(sup, clarear(cores[0], 16), (0, inicio), (LARGURA, inicio))


# ============================================================
# CENAS
# Cada função recebe um gerador de sorteio e a variante, e devolve
# (camadas, configuração). Configuração: luzes e partículas.
# ============================================================

def cena_floresta(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(12, 7, 18), (30, 12, 28), (62, 20, 34), (92, 32, 40)])
    estrelas(ceu, rng, 60, 70)
    lua_x = [250, 80, 300][variante]
    lua(ceu, (lua_x, rng.randint(32, 46)), 15, (176, 52, 48), (130, 34, 36), (90, 26, 36), rng=rng)

    # morros e árvores distantes, mais claros (o ar "apaga" o que está longe)
    cor_longe = (46, 24, 44)
    pontos = [(0, ALTURA)]
    for x in range(0, LARGURA + 8, 8):
        pontos.append((x, 92 + int(8 * math.sin(x * 0.035 + variante)) + rng.randint(-2, 2)))
    pontos.append((LARGURA, ALTURA))
    pygame.draw.polygon(longe, cor_longe, pontos)
    for _ in range(14):
        arvore_morta(longe, cor_longe, rng.randint(0, LARGURA), rng.randint(96, 104), rng.randint(20, 34), rng, 2)
    pontilhar(longe, (0, 90, LARGURA, 30), (70, 40, 62), 0.3, so_onde_tem=True)

    # árvores grandes no meio, com luz vermelha da lua nas bordas
    cor_arvore = (20, 11, 20)
    posicoes = [rng.randint(10, 60), rng.randint(110, 150), rng.randint(250, 290), rng.randint(320, 345)]
    for x in posicoes:
        arvore_morta(meio, cor_arvore, x, HORIZONTE + 4, rng.randint(70, 100), rng, rng.randint(5, 8))
    luz_de_borda(meio, (86, 30, 40), dx=1, dy=-1)
    contornar(meio)
    if variante != 1:
        for _ in range(2):
            x = rng.choice([v for v in range(30, 320, 10) if abs(v - lua_x) > 50])      # longe da lua
            teia(meio, (120, 112, 128), (x, rng.randint(30, 70)), rng.randint(9, 14), rng)

    chao_basico(chao, [(34, 26, 30), (24, 18, 24), (12, 8, 12)], rng)
    luzes = []
    for _ in range(18):                                # musgo
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 4, ALTURA - 4)
        retangulo(chao, (38, 46, 34), (x, y, rng.randint(3, 8), 1))
    for _ in range(6):                                 # cogumelos que brilham
        x, y = rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 2, HORIZONTE + 18)
        retangulo(chao, (60, 70, 80), (x, y, 1, 2))
        retangulo(chao, (90, 200, 220), (x - 1, y - 1, 3, 1))
        luzes.append([x, y - 1, 6, [90, 200, 230], 0.6])
    for _ in range(5):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 6, ALTURA - 6))
    cranio(chao, rng.randrange(40, LARGURA - 40), rng.randrange(HORIZONTE + 20, ALTURA - 8))
    if variante == 1:                                  # pântano: poças escuras que refletem a lua
        for _ in range(4):
            x, y = rng.randrange(0, LARGURA - 40), rng.randrange(HORIZONTE + 4, ALTURA - 10)
            pygame.draw.ellipse(chao, (20, 18, 30), (x, y, rng.randint(24, 44), rng.randint(4, 7)))
            linha(chao, (110, 40, 46), (x + 6, y + 2), (x + 14, y + 2))
    if variante == 2:                                  # ruínas e túmulos
        for _ in range(5):
            x = rng.randrange(10, LARGURA - 20)
            y = rng.randrange(HORIZONTE - 6, HORIZONTE + 4)
            retangulo(meio, (56, 50, 62), (x, y - 10, 7, 11))
            pygame.draw.circle(meio, (56, 50, 62), (x + 3, y - 10), 3)
            linha(meio, (30, 26, 34), (x + 3, y - 8), (x + 3, y - 3))
            linha(meio, (30, 26, 34), (x + 1, y - 6), (x + 5, y - 6))

    # frente: capim e espinhos só nas bordas de baixo
    for x in list(range(0, 50)) + list(range(LARGURA - 50, LARGURA)):
        if rng.random() < 0.5:
            altura = rng.randint(3, 10)
            linha(frente, (14, 10, 16), (x, ALTURA), (x + rng.randint(-2, 2), ALTURA - altura))
    configuracao = {"luzes": luzes,
                    "particulas": [["vaga_lume", 22], ["nevoa", 2]] if variante != 2 else [["vaga_lume", 12], ["cinza", 20], ["nevoa", 1]],
                    "cor_nevoa": [70, 50, 80]}
    return [ceu, longe, meio, chao, frente], configuracao


def cena_minas(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, ALTURA, [(10, 9, 14), (22, 18, 24), (30, 24, 28), (20, 16, 20)])
    for _ in range(400):                               # textura de rocha
        x, y = rng.randrange(LARGURA), rng.randrange(ALTURA)
        ceu.set_at((x, y), rng.choice(((26, 22, 28), (16, 13, 18), (34, 28, 32))))
    # teto com estalactites
    for x in range(0, LARGURA, 3):
        comprimento = rng.choice((4, 6, 8, 10, 14, 22)) if rng.random() < 0.6 else 3
        for dy in range(comprimento):
            largura = max(1, int(3 * (1 - dy / comprimento)))
            retangulo(meio, (14, 11, 16), (x, dy, largura, 1))

    # túnel ao fundo com brilho quente, vigas de madeira e trilhos
    luzes = []
    tx = rng.randint(140, 200)
    pygame.draw.ellipse(longe, (40, 26, 22), (tx - 34, 64, 68, 70))
    pygame.draw.ellipse(longe, (8, 6, 8), (tx - 26, 74, 52, 60))
    halo(longe, (tx, 108), 24, (90, 50, 28), 0.5)
    luzes.append([tx, 108, 22, [255, 150, 70], 0.3])
    cor_madeira = (72, 46, 30)
    if variante != 1:                                   # vigas de madeira (a caverna de cristais não tem)
        for x0 in (tx - 70, tx + 50, 20, LARGURA - 40):
            retangulo(longe, cor_madeira, (x0, 70, 5, 50))
            retangulo(longe, cor_madeira, (x0 + 18, 70, 5, 50))
            retangulo(longe, cor_madeira, (x0 - 3, 66, 29, 5))
            luz_de_borda(longe, (110, 74, 46), dx=-1, dy=0, base=cor_madeira)
    else:                                               # cristais gigantes ao fundo
        for x0 in (40, 110, 250, 310):
            altura = rng.randint(40, 70)
            pygame.draw.polygon(longe, (70, 40, 110), [(x0 - 8, HORIZONTE), (x0, HORIZONTE - altura), (x0 + 8, HORIZONTE)])
            linha(longe, (150, 100, 200), (x0, HORIZONTE - altura + 4), (x0 - 4, HORIZONTE - 4))
            luzes.append([x0, HORIZONTE - altura // 2, 26, [150, 80, 220], 0.3])
    contornar(longe)

    # pilares de rocha e cristais
    for x in (rng.randint(0, 30), rng.randint(300, 330)):
        pygame.draw.polygon(meio, (36, 30, 38), [(x - 10, HORIZONTE + 2), (x - 4, 10), (x + 8, 6), (x + 18, HORIZONTE + 2)])
    cores_cristal = [((90, 200, 220), (200, 250, 255)), ((170, 90, 220), (230, 190, 255))]
    for _ in range(12 if variante == 1 else 5):
        x, y = rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE - 30, HORIZONTE + 2)
        cor, brilho = rng.choice(cores_cristal)
        for k in range(rng.randint(2, 4)):
            altura = rng.randint(5, 11)
            base_x = x + k * 3 - 4
            pygame.draw.polygon(meio, cor, [(base_x, y), (base_x + 1, y - altura), (base_x + 3, y)])
            meio.set_at((base_x + 1, y - altura + 2), brilho)
        luzes.append([x, y - 5, 12, list(cor), 0.5])
    # lanternas penduradas
    for x in (rng.randint(60, 110), rng.randint(230, 290)):
        linha(meio, (40, 34, 40), (x, 0), (x, 46))
        retangulo(meio, (60, 40, 30), (x - 2, 46, 5, 6))
        retangulo(meio, (255, 190, 90), (x - 1, 48, 3, 3))
        luzes.append([x, 49, 20, [255, 170, 80], 0.8])
    contornar(meio)

    chao_basico(chao, [(38, 30, 32), (26, 20, 24), (12, 9, 12)], rng)
    # trilhos que vêm de longe
    for t in range(0, 12):
        y = HORIZONTE + 4 + t * 5
        largura = 30 + t * 14
        retangulo(chao, (60, 40, 28), (tx - largura // 2, y, largura, 2))
    linha(chao, (110, 110, 120), (tx - 12, HORIZONTE + 2), (tx - 90, ALTURA))
    linha(chao, (110, 110, 120), (tx + 12, HORIZONTE + 2), (tx + 90, ALTURA))
    for _ in range(14):
        pedra(chao, (52, 44, 48), rng.randrange(LARGURA), rng.randrange(HORIZONTE + 4, ALTURA - 4), rng.randint(4, 9), rng.randint(3, 5))
    if variante == 2:                                  # vagonete de minério
        x = rng.choice((30, 280))
        retangulo(meio, (70, 60, 66), (x, HORIZONTE - 8, 26, 10))
        retangulo(meio, (110, 100, 106), (x, HORIZONTE - 8, 26, 2))
        for k in range(5):
            meio.set_at((x + 4 + k * 4, HORIZONTE - 10), rng.choice(((90, 200, 220), (200, 170, 90), (120, 120, 130))))
        pygame.draw.circle(meio, (30, 26, 30), (x + 6, HORIZONTE + 2), 3)
        pygame.draw.circle(meio, (30, 26, 30), (x + 20, HORIZONTE + 2), 3)
    for x in list(range(0, 40, 6)) + list(range(LARGURA - 40, LARGURA, 6)):
        pedra(frente, (20, 16, 20), x, ALTURA - rng.randint(4, 9), rng.randint(6, 12), 9)
    configuracao = {"luzes": luzes, "particulas": [["poeira", 30], ["gota", 6]], "cor_nevoa": [40, 34, 40]}
    return [ceu, longe, meio, chao, frente], configuracao


def vitral(sup, x, topo, largura, altura, rng):
    """Janela gótica com vitral colorido e armação de chumbo."""
    arco_gotico(sup, CONTORNO, x - 2, topo - 2, largura + 4, altura + 4)
    cores = [(120, 30, 40), (40, 50, 120), (90, 40, 110), (150, 110, 40), (40, 90, 80)]
    for y in range(topo, topo + altura):
        for xx in range(x, x + largura):
            if sup.get_at((xx, y))[:3] == CONTORNO:
                bloco = ((xx - x) // 4) + ((y - topo) // 5) * 7
                cor = cores[(bloco * 7 + bloco // 3) % len(cores)]
                if (xx - x) % 4 == 0 or (y - topo) % 5 == 0:
                    cor = (14, 10, 16)
                sup.set_at((xx, y), cor)


def rosacea(sup, centro, raio):
    """Rosácea: vitral redondo com pétalas coloridas e raios de chumbo."""
    cx, cy = centro
    pygame.draw.circle(sup, CONTORNO, centro, raio + 2)
    cores = [(40, 60, 140), (80, 40, 120), (30, 90, 120), (120, 40, 60)]
    for y in range(cy - raio, cy + raio + 1):
        for x in range(cx - raio, cx + raio + 1):
            d = math.hypot(x - cx, y - cy)
            if d <= raio:
                angulo = math.atan2(y - cy, x - cx)
                fatia = int((angulo + math.pi) / math.tau * 12)
                anel = int(d / (raio / 4))
                cor = cores[(fatia + anel) % len(cores)]
                if anel in (1, 3) and fatia % 2:
                    cor = clarear(cor, 30)
                sup.set_at((x, y), cor)
    for k in range(12):
        a = k / 12 * math.tau
        linha(sup, (12, 10, 16), centro, (cx + math.cos(a) * raio, cy + math.sin(a) * raio))
    for r in (raio // 4, raio // 2, raio * 3 // 4):
        pygame.draw.circle(sup, (12, 10, 16), centro, r, 1)
    pygame.draw.circle(sup, (200, 180, 120), centro, 3)


def cena_catedral(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    cripta = variante == 2
    parede = [(14, 10, 20), (26, 18, 32), (36, 26, 42)] if not cripta else [(10, 14, 14), (18, 24, 22), (26, 32, 28)]
    degrade(ceu, 0, HORIZONTE + 4, parede)
    luzes = []
    if not cripta:
        # abóbadas no teto
        for x in range(-20, LARGURA + 40, 60):
            pygame.draw.arc(ceu, (44, 34, 52), (x, -30, 60, 60), math.pi, math.tau, 2)
        if variante == 0:
            # três vitrais grandes com feixes de luz roxa
            for x in (70, 160, 250):
                vitral(ceu, x, 22, 26, 60, rng)
                for k in range(0, 46):
                    pontilhar(longe, (x + 4 + k // 2, 82 + k, 18, 1), (90, 60, 110), 0.18)
                luzes.append([x + 13, 50, 26, [150, 90, 200], 0.2])
        else:
            # uma rosácea enorme no meio e janelas estreitas dos lados (luz azul de lua)
            rosacea(ceu, (176, 46), 34)
            for k in range(0, 70):
                pontilhar(longe, (150 + k // 3, 80 + k // 2, 52, 1), (70, 90, 140), 0.16)
            luzes.append([176, 46, 40, [90, 120, 220], 0.15])
            for x in (52, 96, 244, 288):
                vitral(ceu, x, 34, 12, 50, rng)
        # fileira de arcos distantes
        for x in range(0, LARGURA, 44):
            arco_gotico(longe, (40, 32, 50), x, 70, 30, 50)
            arco_gotico(longe, (20, 14, 26), x + 5, 78, 20, 42)
    else:
        # catacumba: nichos com crânios
        for y in range(16, HORIZONTE - 10, 18):
            for x in range(6 + (y // 18 % 2) * 12, LARGURA, 24):
                arco_gotico(longe, (12, 14, 14), x, y, 14, 14)
                cranio(longe, x + 5, y + 7, (170, 166, 140))
        for x in (90, 260):
            retangulo(meio, (40, 50, 40), (x, 56, 3, 8))
            pygame.draw.polygon(meio, (90, 240, 140), [(x - 1, 56), (x + 1, 49), (x + 4, 56)])
            luzes.append([x + 1, 53, 22, [100, 240, 150], 0.8])

    # pilares grandes
    cor_pedra = (56, 48, 64) if not cripta else (46, 54, 50)
    for x in (rng.randint(4, 24), rng.randint(312, 330)):
        retangulo(meio, cor_pedra, (x, 0, 18, HORIZONTE + 4))
        retangulo(meio, clarear(cor_pedra, -14), (x + 13, 0, 5, HORIZONTE + 4))
        for y in range(10, HORIZONTE, 14):
            linha(meio, clarear(cor_pedra, -20), (x, y), (x + 17, y))
        retangulo(meio, clarear(cor_pedra, 12), (x - 3, HORIZONTE - 4, 24, 8))
    # candelabros (velas com brilho quente) e estandartes
    for x in (rng.randint(60, 100), rng.randint(240, 290)):
        linha(meio, (60, 50, 40), (x, HORIZONTE + 2), (x, HORIZONTE - 26), 2)
        linha(meio, (60, 50, 40), (x - 8, HORIZONTE - 26), (x + 8, HORIZONTE - 26), 2)
        for dx in (-8, 0, 8):
            vela(meio, x + dx - 1, HORIZONTE - 27)
            luzes.append([x + dx, HORIZONTE - 32, 14, [255, 170, 80], 1.0])
    if variante == 0:
        for x in (rng.randint(110, 140), rng.randint(200, 230)):
            retangulo(meio, (100, 20, 30), (x, 8, 14, 46))
            pygame.draw.polygon(meio, (100, 20, 30), [(x, 54), (x + 7, 60), (x + 14, 54)])
            linha(meio, (180, 140, 60), (x, 8), (x + 13, 8))
            pygame.draw.circle(meio, (180, 140, 60), (x + 7, 26), 3, 1)
    contornar(meio)

    # chão de lajes em perspectiva + tapete vermelho
    degrade(chao, HORIZONTE, ALTURA, [(40, 32, 44), (28, 22, 32), (14, 10, 16)] if not cripta else
            [(32, 36, 34), (22, 26, 24), (10, 12, 12)])
    y = HORIZONTE
    passo = 3
    while y < ALTURA:
        linha(chao, (18, 14, 22), (0, y), (LARGURA, y))
        passo += 1
        y += passo
    for k in range(-12, 13):
        linha(chao, (18, 14, 22), (176 + k * 10, HORIZONTE), (176 + k * 40, ALTURA))
    if not cripta:
        pygame.draw.polygon(chao, (90, 20, 30), [(160, HORIZONTE), (192, HORIZONTE), (250, ALTURA), (102, ALTURA)])
        linha(chao, (150, 110, 50), (160, HORIZONTE), (102, ALTURA))
        linha(chao, (150, 110, 50), (192, HORIZONTE), (250, ALTURA))
    else:
        for _ in range(3):                              # caixões
            x, y = rng.randrange(20, LARGURA - 60), rng.randrange(HORIZONTE + 6, ALTURA - 20)
            pygame.draw.polygon(chao, (50, 36, 30), [(x, y + 3), (x + 6, y), (x + 34, y), (x + 40, y + 3), (x + 34, y + 7), (x + 6, y + 7)])
    for _ in range(6):
        vela(chao, rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 8, ALTURA - 4), rng.randint(2, 4))
    for _ in range(4):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 8, ALTURA - 6))
    configuracao = {"luzes": luzes, "particulas": [["poeira", 26], ["cinza", 10]] if not cripta else
                    [["poeira", 16], ["nevoa", 2]], "cor_nevoa": [40, 60, 50] if cripta else [60, 40, 70]}
    return [ceu, longe, meio, chao, frente], configuracao


def tenda_de_circo(sup, x, base, largura, altura, rng, cores=((112, 30, 40), (150, 132, 110))):
    """Tenda listrada (cores desbotadas), com uma bandeirinha em cima."""
    topo = base - altura
    for dx in range(-largura // 2, largura // 2):
        t = abs(dx) / (largura / 2)
        y0 = topo + int(t * t * altura * 0.55)
        cor = cores[(dx // 6) % 2]
        retangulo(sup, cor, (x + dx, y0, 1, base - y0))
    linha(sup, (40, 30, 30), (x, topo - 12), (x, topo))
    pygame.draw.polygon(sup, (150, 40, 40), [(x, topo - 12), (x + 8, topo - 10), (x, topo - 8)])
    # rasgos
    for _ in range(4):
        rx, ry = x + rng.randint(-largura // 3, largura // 3), base - rng.randint(4, altura // 2)
        pygame.draw.polygon(sup, (10, 6, 10), [(rx, ry), (rx + 3, ry + 6), (rx - 2, ry + 5)])
    retangulo(sup, (10, 6, 10), (x - 6, base - 18, 12, 18))     # entrada escura


def cena_circo(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(12, 8, 20), (28, 14, 36), (44, 30, 44), (66, 52, 40)])
    estrelas(ceu, rng, 40, 60)
    lua(ceu, (rng.randint(40, 90), 30), 11, (190, 200, 150), (140, 150, 110), (60, 70, 50), rng=rng)
    # roda-gigante distante
    if variante != 1:
        cx, cy = rng.randint(250, 300), 62
        pygame.draw.circle(longe, (40, 28, 46), (cx, cy), 28, 2)
        for k in range(8):
            a = k / 8 * math.tau
            linha(longe, (40, 28, 46), (cx, cy), (cx + math.cos(a) * 28, cy + math.sin(a) * 28))
            retangulo(longe, (52, 36, 56), (int(cx + math.cos(a) * 28) - 2, int(cy + math.sin(a) * 28), 5, 4))
        linha(longe, (40, 28, 46), (cx, cy), (cx - 16, HORIZONTE), 2)
        linha(longe, (40, 28, 46), (cx, cy), (cx + 16, HORIZONTE), 2)
    cores_tenda = [((112, 30, 40), (150, 132, 110)), ((70, 40, 90), (90, 120, 80)), ((40, 50, 100), (150, 132, 110))][variante]
    x_tenda = [rng.randint(150, 200), 110, 240][variante]
    tenda_de_circo(longe, x_tenda, HORIZONTE + 2, 140 if variante != 1 else 120, 74, rng, cores_tenda)
    if variante == 1:                                   # carrossel abandonado
        cx = 270
        pygame.draw.polygon(longe, (60, 30, 50), [(cx - 34, 70), (cx, 52), (cx + 34, 70)])
        retangulo(longe, (50, 26, 40), (cx - 34, 70, 68, 4))
        for k in range(-28, 32, 14):
            linha(longe, (120, 110, 90), (cx + k, 74), (cx + k, HORIZONTE - 6))
            retangulo(longe, (90, 80, 70), (cx + k - 3, 90 + (k % 3) * 4, 7, 5))
        retangulo(longe, (50, 26, 40), (cx - 38, HORIZONTE - 6, 76, 6))
    contornar(longe)
    pontilhar(longe, (0, 50, LARGURA, 70), (20, 10, 26), 0.25, so_onde_tem=True)

    # varal de lampadinhas
    luzes = []
    cores_lampada = [(240, 90, 80), (240, 210, 90), (110, 200, 120), (120, 150, 240)]
    for y_base in (24, 40):
        anterior = None
        for x in range(-10, LARGURA + 20, 22):
            y = y_base + int(6 * math.sin(x * 0.07 + y_base))
            if anterior:
                pygame.draw.line(meio, (30, 24, 30), anterior, (x, y))
            anterior = (x, y)
            if rng.random() < 0.75:
                cor = rng.choice(cores_lampada)
                retangulo(meio, cor, (x, y + 1, 2, 2))
                luzes.append([x + 1, y + 2, 7, list(cor), 0.45 if rng.random() < 0.7 else 0.0])
    # caixas, barris e uma jaula
    for _ in range(3):
        x = rng.randrange(10, LARGURA - 30)
        retangulo(meio, (70, 46, 32), (x, HORIZONTE - 12, 14, 14))
        linha(meio, (40, 26, 20), (x, HORIZONTE - 12), (x + 13, HORIZONTE + 1))
    if variante == 2:
        x = rng.choice((20, 270))
        retangulo(meio, (60, 30, 40), (x, HORIZONTE - 32, 56, 30))
        for k in range(0, 56, 5):
            linha(meio, (110, 100, 90), (x + k, HORIZONTE - 30), (x + k, HORIZONTE - 4))
        pygame.draw.circle(meio, (40, 30, 30), (x + 10, HORIZONTE), 5)
        pygame.draw.circle(meio, (40, 30, 30), (x + 46, HORIZONTE), 5)
    contornar(meio)

    chao_basico(chao, [(44, 32, 30), (30, 22, 22), (14, 10, 12)], rng)
    for _ in range(90):                                # confete velho e pipoca
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA)
        chao.set_at((x, y), rng.choice([(130, 60, 60), (130, 120, 60), (60, 100, 70), (70, 80, 130), (200, 190, 150)]))
    pygame.draw.ellipse(chao, (90, 30, 34), (40, HORIZONTE + 10, 272, 50), 2)     # borda do picadeiro
    configuracao = {"luzes": luzes, "particulas": [["confete", 26], ["nevoa", 1]], "cor_nevoa": [70, 60, 50]}
    return [ceu, longe, meio, chao, frente], configuracao


def tenda(sup, x, base, largura, altura, cores):
    """Tenda de lona com o mastro, a aba aberta (escura por dentro) e listras de costura."""
    clara, escura = cores
    topo = base - altura
    pygame.draw.polygon(sup, clara, [(x - largura // 2, base), (x, topo), (x + largura // 2, base)])
    pygame.draw.polygon(sup, escura, [(x, topo), (x + largura // 2, base), (x + largura // 6, base)])
    for k in range(-2, 3):                                  # costuras
        linha(sup, escura, (x, topo + 2), (x + k * largura // 6, base))
    pygame.draw.polygon(sup, (14, 8, 12), [(x - largura // 8, base), (x + 2, topo + altura // 3), (x + largura // 10, base)])
    linha(sup, (70, 50, 34), (x, topo), (x, topo - 8))
    pygame.draw.polygon(sup, (150, 40, 40), [(x, topo - 8), (x + 7, topo - 6), (x, topo - 4)])


def cena_acampamento(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(6, 8, 20), (14, 18, 38), (28, 28, 56), (44, 36, 62)])
    estrelas(ceu, rng, 140, 90)
    lua(ceu, (282, 30), 13, (210, 210, 190), (160, 160, 150), (60, 64, 90), rng=rng)
    cor_mata = (14, 16, 28)
    pontos = [(0, ALTURA)]
    for x in range(0, LARGURA + 4, 4):
        pontos.append((x, 84 + int(6 * math.sin(x * 0.05)) + rng.randint(-4, 2)))
    pontos.append((LARGURA, ALTURA))
    pygame.draw.polygon(longe, cor_mata, pontos)
    for _ in range(30):                                # pinheiros secos
        x, base = rng.randrange(LARGURA), rng.randint(86, 100)
        altura = rng.randint(14, 30)
        pygame.draw.polygon(longe, cor_mata, [(x - 5, base), (x, base - altura), (x + 5, base)])

    # tendas grandes nos dois cantos (atrás do Espelho/Grimório e do Mago/Baú) e uma pequena ao fundo
    luzes = []
    # (as tendas grandes são sprites da forja, desenhados pela tela do acampamento; aqui só uma tenda distante)
    tenda(longe, 236, HORIZONTE + 2, 34, 26, ((44, 34, 56), (32, 24, 42)))
    for x in (118, 236):                               # estandartes com a caneca da taverna
        linha(meio, (60, 44, 32), (x, HORIZONTE + 2), (x, HORIZONTE - 46))
        retangulo(meio, (40, 40, 70), (x + 1, HORIZONTE - 44, 9, 16))
        pygame.draw.polygon(meio, (40, 40, 70), [(x + 1, HORIZONTE - 28), (x + 5, HORIZONTE - 24), (x + 10, HORIZONTE - 28)])
        retangulo(meio, (150, 120, 70), (x + 4, HORIZONTE - 39, 3, 4))
    contornar(meio)
    luz_de_borda(meio, (150, 90, 50), dx=1, dy=0)

    chao_basico(chao, [(28, 30, 28), (20, 20, 22), (10, 10, 12)], rng)
    for _ in range(30):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA - 2)
        linha(chao, (34, 44, 32), (x, y), (x + rng.choice((-1, 1)), y - 2))
    configuracao = {"luzes": luzes, "particulas": [["vaga_lume", 16], ["nevoa", 1]], "cor_nevoa": [50, 50, 80]}
    return [ceu, longe, meio, chao, frente], configuracao


def cena_titulo(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, ALTURA, [(10, 4, 10), (40, 10, 22), (90, 22, 30), (40, 12, 22), (10, 6, 12)])
    lua(ceu, (176, 70), 42, (160, 40, 40), (120, 28, 32), (80, 20, 30), rng=rng)
    for y in (50, 64, 90):                              # nuvens passando pela lua
        for x in range(0, LARGURA, 2):
            if math.sin(x * 0.06 + y) > 0.2:
                pontilhar(ceu, (x, y + int(3 * math.sin(x * 0.11)), 2, 4), (24, 8, 16), 0.7)
    # penhasco com a catedral em ruínas
    cor = (12, 6, 12)
    pygame.draw.polygon(longe, cor, [(70, ALTURA), (110, 108), (150, 102), (210, 104), (250, 110), (290, ALTURA)])
    for x, w, h in ((120, 16, 40), (140, 30, 26), (166, 12, 64), (182, 30, 30), (214, 14, 44)):
        retangulo(longe, cor, (x, 104 - h, w, h))
        pygame.draw.polygon(longe, cor, [(x, 104 - h), (x + w // 2, 104 - h - w), (x + w, 104 - h)])
    for _ in range(9):                                  # janelas acesas
        x, y = rng.randint(124, 226), rng.randint(64, 98)
        if longe.get_at((x, y))[3]:
            retangulo(longe, (230, 150, 70), (x, y, 1, 2))
    # árvores mortas emoldurando
    for x in (20, 330):
        arvore_morta(meio, (6, 3, 8), x, ALTURA, 150, rng, 10)
    configuracao = {"luzes": [], "particulas": [["cinza", 40], ["relampago", 1]], "cor_nevoa": [60, 20, 40]}
    return [ceu, longe, meio, chao, frente], configuracao


# ============================================================
# SALÃO ASSOMBRADO (tela de título): o palácio em ruínas sobre a cripta
# ============================================================

def mascara_gotica(x, topo, largura, altura):
    """Máscara (pygame.mask) de um arco gótico preenchido."""
    molde = camada()
    arco_gotico(molde, (255, 255, 255), x, topo, largura, altura)
    return pygame.mask.from_surface(molde)


def janela_de_tempestade(sup, rng, x, topo, largura, altura, lua_raio=0):
    """Janela gótica com moldura de pedra, céu de tempestade, lua vermelha, chumbo e cortinas rasgadas."""
    arco_gotico(sup, (8, 5, 10), x - 4, topo - 4, largura + 8, altura + 6)
    arco_gotico(sup, (62, 52, 72), x - 2, topo - 2, largura + 4, altura + 3)
    mascara = mascara_gotica(x, topo, largura, altura)
    ceu_janela = camada()
    degrade(ceu_janela, topo, topo + altura, [(18, 6, 22), (46, 12, 34), (96, 24, 40), (60, 16, 32)], x, x + largura)
    estrelas(ceu_janela, rng, largura // 3, topo + altura * 2 // 3, ((200, 160, 190), (140, 100, 140)))
    if lua_raio:
        lua(ceu_janela, (x + largura // 2, topo + altura // 2 - 6), lua_raio, (196, 52, 48), (140, 30, 36), (120, 30, 40), rng=rng)
    for k in range(4):                                   # nuvens escuras passando
        cy = topo + rng.randint(altura // 4, altura - 8)
        for xx in range(x, x + largura):
            if math.sin(xx * 0.25 + k * 2) > 0.1:
                pontilhar(ceu_janela, (xx, cy + int(2 * math.sin(xx * 0.4)), 1, 3), (22, 8, 20), 0.75)
    for yy in range(topo, topo + altura):
        for xx in range(x, x + largura):
            if mascara.get_at((xx, yy)):
                sup.set_at((xx, yy), ceu_janela.get_at((xx, yy)))
    chumbo = (16, 10, 18)
    linha(sup, chumbo, (x + largura // 2, topo + 6), (x + largura // 2, topo + altura))
    for k in range(1, 4):
        yy = topo + altura * k // 4 + 4
        linha(sup, chumbo, (x + 1, yy), (x + largura - 2, yy))
    # cortinas vermelhas rasgadas, presas nos lados
    for lado in (0, 1):
        x0 = x - 6 if lado == 0 else x + largura - 2
        for dx in range(8):
            fundo = topo + altura + 6 - (dx * 3 if lado == 0 else (7 - dx) * 3) - rng.randint(0, 4)
            cor = (92, 16, 26) if dx % 3 else (130, 26, 36)
            retangulo(sup, cor, (x0 + dx, topo - 6, 1, max(4, fundo - topo + 6)))
        retangulo(sup, (150, 110, 50), (x0, topo + altura // 2, 8, 2))          # amarra dourada


def estatua_de_cavaleiro(sup, x, base, olhando=1):
    """Cavaleiro de pedra num pedestal, apoiado na espada."""
    pedra_ = (70, 64, 78)
    escura = (44, 40, 52)
    retangulo(sup, escura, (x - 9, base - 8, 18, 8))                     # pedestal
    retangulo(sup, pedra_, (x - 8, base - 9, 16, 2))
    retangulo(sup, pedra_, (x - 4, base - 30, 8, 22))                    # corpo
    retangulo(sup, pedra_, (x - 3, base - 37, 6, 7))                     # elmo
    linha(sup, (20, 16, 24), (x - 2, base - 34), (x + 2, base - 34))       # viseira
    pygame.draw.polygon(sup, pedra_, [(x - 6, base - 30), (x + 6, base - 30), (x + 7, base - 22), (x - 7, base - 22)])
    linha(sup, (96, 90, 104), (x + 5 * olhando, base - 38), (x + 5 * olhando, base - 9), 2)     # espada
    linha(sup, (96, 90, 104), (x + 2 * olhando, base - 31), (x + 8 * olhando, base - 31))
    pygame.draw.polygon(sup, escura, [(x - 7 * olhando, base - 28), (x - 13 * olhando, base - 26),
                                      (x - 12 * olhando, base - 14), (x - 7 * olhando, base - 12)])    # escudo


def lustre(sup, centro_x, y, largura, luzes):
    """Lustre de ferro com velas acesas, preso por corrente."""
    for yy in range(0, y, 3):                            # corrente
        sup.set_at((centro_x, yy), (60, 54, 62))
        sup.set_at((centro_x, yy + 1), (90, 82, 92))
    pygame.draw.ellipse(sup, (40, 34, 44), (centro_x - largura // 2, y, largura, 7), 2)
    pygame.draw.ellipse(sup, (70, 60, 72), (centro_x - largura // 2 + 4, y + 1, largura - 8, 4), 1)
    linha(sup, (40, 34, 44), (centro_x, y - 4), (centro_x, y + 6), 2)
    for k in range(7):
        a = k / 7 * math.pi
        vx = int(centro_x - math.cos(a) * (largura // 2 - 2))
        vy = y + 2 + int(math.sin(a) * 3)
        vela(sup, vx, vy, 3)
        luzes.append([vx, vy - 4, 12, [255, 170, 80], 1.0])


def cena_salao(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    luzes = []
    # parede de pedra com tijolos e sombras
    degrade(ceu, 0, HORIZONTE + 4, [(12, 8, 16), (22, 14, 28), (30, 20, 36), (24, 16, 30)])
    for y in range(0, HORIZONTE + 4, 6):
        deslocado = 6 if (y // 6) % 2 else 0
        linha(ceu, (10, 6, 12), (0, y), (LARGURA, y))
        for x in range(deslocado, LARGURA, 12):
            linha(ceu, (10, 6, 12), (x, y), (x, y + 5))
            if rng.random() < 0.25:
                pontilhar(ceu, (x + 1, y + 1, 10, 4), (36, 26, 42), 0.3)
    # três janelas: a do meio com a lua vermelha
    janela_de_tempestade(ceu, rng, 150, 10, 52, 78, lua_raio=13)
    for x in (60, 270):
        janela_de_tempestade(ceu, rng, x, 22, 22, 58)
    luzes.append([176, 40, 40, [170, 40, 50], 0.15])
    # feixes de luar descendo até o chão

    # escadaria subindo até a porta da cripta
    for k in range(10):
        largura = 104 - k * 7
        y = HORIZONTE - 2 - k * 3
        cor = (58, 48, 66) if k % 2 else (48, 40, 56)
        retangulo(longe, cor, (176 - largura // 2, y, largura, 3))
        linha(longe, (78, 68, 86), (176 - largura // 2, y), (176 + largura // 2 - 1, y))
    porta_topo, porta_base = 50, HORIZONTE - 30
    arco_gotico(longe, (30, 26, 34), 154, porta_topo - 4, 44, porta_base - porta_topo + 4)
    arco_gotico(longe, (14, 10, 16), 158, porta_topo, 36, porta_base - porta_topo)
    for yy in range(porta_topo + 16, porta_base, 7):                 # faixas de ferro da porta
        linha(longe, (52, 50, 58), (159, yy), (192, yy))
        longe.set_at((161, yy), (120, 110, 90))
        longe.set_at((190, yy), (120, 110, 90))
    linha(longe, (40, 36, 44), (176, porta_topo + 8), (176, porta_base))
    cranio(longe, 174, porta_topo + 22, (190, 180, 150))               # emblema de crânio
    for k in range(13):                                                  # runas verdes em volta do arco
        a = math.pi + k / 12 * math.pi
        rx, ry = int(176 + math.cos(a) * 24), int(porta_topo + 14 + math.sin(a) * 18)
        if 0 <= ry:
            longe.set_at((rx, ry), (110, 250, 150))
            luzes.append([rx, ry, 5, [90, 230, 140], 0.5]) if k % 3 == 0 else None
    luzes.append([176, porta_base - 10, 18, [80, 220, 130], 0.4])
    estatua_de_cavaleiro(longe, 118, HORIZONTE - 4, 1)
    estatua_de_cavaleiro(longe, 234, HORIZONTE - 4, -1)
    contornar(longe)
    luz_de_borda(longe, (110, 50, 70), dx=0, dy=-1)

    # colunas, estandartes, arandelas e o lustre
    for x, largura in ((8, 22), (322, 22), (86, 12), (256, 12)):
        retangulo(meio, (54, 46, 62), (x, 0, largura, HORIZONTE + 6))
        for k in range(2, largura - 1, 4):                               # caneluras
            linha(meio, (40, 34, 48), (x + k, 10), (x + k, HORIZONTE))
        retangulo(meio, (70, 62, 80), (x - 2, 6, largura + 4, 4))           # capitel
        retangulo(meio, (70, 62, 80), (x - 3, HORIZONTE, largura + 6, 6))   # base
        retangulo(meio, (38, 32, 46), (x + largura - 4, 0, 4, HORIZONTE + 6))
        if largura > 12:                                                 # arandela com vela
            ax = x + largura + 1 if x < 176 else x - 4
            retangulo(meio, (70, 60, 50), (ax, 64, 3, 2))
            vela(meio, ax, 64, 4)
            luzes.append([ax + 1, 58, 16, [255, 160, 80], 1.0])
    for x in (36, 302):                                                  # estandartes rasgados
        retangulo(meio, (96, 18, 28), (x, 0, 16, 52))
        for k in range(16):
            meio.set_at((x + k, 52 + (k * 7 % 5)), (96, 18, 28))
        pygame.draw.circle(meio, (170, 130, 60), (x + 8, 24), 4, 1)
        linha(meio, (170, 130, 60), (x + 8, 20), (x + 8, 28))
        linha(meio, (60, 50, 40), (x - 2, 0), (x + 18, 0), 2)
    lustre(meio, 176, 24, 40, luzes)
    contornar(meio)

    # chão de mármore xadrez em perspectiva, com o reflexo da janela e o tapete
    for y in range(HORIZONTE, ALTURA):
        dy = y - HORIZONTE + 5
        linha_xadrez = int(160 / dy)
        for x in range(LARGURA):
            coluna = math.floor((x - 176) / dy * 2.2)
            clara = (linha_xadrez + coluna) % 2 == 0
            cor = (44, 36, 50) if clara else (28, 22, 34)
            reflexo = max(0.0, 1 - abs(x - 176) / (30 + dy * 0.8))
            if reflexo > 0 and BAYER[y % 4][x % 4] / 16 < reflexo * 0.5:
                cor = clarear(cor, 24)
            chao.set_at((x, y), cor)
    pygame.draw.polygon(chao, (96, 16, 28), [(162, HORIZONTE), (190, HORIZONTE), (250, ALTURA), (102, ALTURA)])
    linha(chao, (170, 130, 60), (162, HORIZONTE), (102, ALTURA))
    linha(chao, (170, 130, 60), (190, HORIZONTE), (250, ALTURA))
    for x0, largura in ((60, 22), (270, 22)):                           # luar das janelas no chão
        poligono_pontilhado(chao, [(x0 + 4, HORIZONTE), (x0 + largura - 4, HORIZONTE), (x0 + largura + 26, ALTURA),
                                   (x0 + 14, ALTURA)], (86, 46, 66), 0.12)
    for k in range(6):                                                   # losangos dourados no tapete
        y = HORIZONTE + 6 + k * k * 2
        meio_x = 176
        pygame.draw.polygon(chao, (150, 110, 50), [(meio_x, y - 2), (meio_x + 3, y), (meio_x, y + 2), (meio_x - 3, y)])
    for _ in range(9):                                                   # rachaduras e cera derretida
        x, y = rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 6, ALTURA - 4)
        linha(chao, (12, 8, 14), (x, y), (x + rng.randint(-6, 6), y + rng.randint(1, 4)))
    for _ in range(4):
        osso(chao, rng.choice([rng.randrange(20, 90), rng.randrange(260, 330)]), rng.randrange(HORIZONTE + 8, ALTURA - 6))
    for x in (rng.randrange(40, 80), rng.randrange(270, 310)):
        cranio(chao, x, rng.randrange(HORIZONTE + 12, ALTURA - 10))

    # frente: teias nos cantos de cima, correntes e candelabros nos cantos de baixo
    teia(frente, (130, 120, 140), (16, 0), 26, rng)
    teia(frente, (130, 120, 140), (LARGURA - 16, 0), 30, rng)
    for x in (54, 300):
        for yy in range(0, 30 + (x % 7), 3):
            frente.set_at((x, yy), (70, 64, 74))
            frente.set_at((x, yy + 1), (100, 94, 104))
    for x in (26, LARGURA - 30):
        linha(frente, (24, 18, 26), (x, ALTURA), (x, ALTURA - 34), 2)
        linha(frente, (24, 18, 26), (x - 7, ALTURA - 34), (x + 7, ALTURA - 34), 2)
        for dx in (-7, 0, 7):
            vela(frente, x + dx - 1, ALTURA - 35, 3)
            luzes.append([x + dx, ALTURA - 40, 12, [255, 170, 80], 1.0])
    configuracao = {"luzes": luzes, "particulas": [["poeira", 34], ["nevoa", 2], ["relampago", 1]],
                    "cor_nevoa": [60, 40, 70]}
    return [ceu, longe, meio, chao, frente], configuracao


# ---------------- salas de chefe ----------------

def cena_ninho(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(8, 12, 12), (16, 24, 22), (26, 30, 30)])
    teia(longe, (60, 70, 66), (176, 50), 90, rng)
    teia(longe, (70, 80, 76), (40, 20), 40, rng)
    teia(longe, (70, 80, 76), (320, 30), 46, rng)
    luzes = []
    for _ in range(9):                                  # sacos de ovos pendurados
        x, y = rng.randrange(20, LARGURA - 20), rng.randrange(20, 80)
        linha(meio, (110, 120, 110), (x, 0), (x, y))
        pygame.draw.ellipse(meio, (190, 196, 170), (x - 4, y, 9, 12))
        pygame.draw.ellipse(meio, (230, 236, 210), (x - 2, y + 2, 4, 5))
        luzes.append([x, y + 6, 8, [190, 230, 160], 0.4])
    for x in (rng.randint(10, 40), rng.randint(300, 330)):  # casulos com ossos
        pygame.draw.ellipse(meio, (160, 164, 150), (x - 8, HORIZONTE - 34, 18, 34))
        cranio(meio, x - 1, HORIZONTE - 28)
    contornar(meio)
    chao_basico(chao, [(30, 34, 30), (20, 22, 20), (8, 10, 8)], rng)
    for _ in range(14):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA)
        linha(chao, (120, 130, 120), (x, y), (x + rng.randint(-20, 20), y + rng.randint(-3, 3)))
    for _ in range(6):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 6, ALTURA - 6))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["poeira", 20], ["nevoa", 2]],
                                              "cor_nevoa": [60, 80, 70]}


def cena_forja(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, ALTURA, [(14, 8, 8), (40, 16, 12), (70, 28, 18), (30, 12, 10)])
    luzes = []
    # fornalha gigante ao fundo
    pygame.draw.polygon(longe, (40, 26, 24), [(110, HORIZONTE), (130, 30), (222, 30), (242, HORIZONTE)])
    arco_gotico(longe, (10, 4, 4), 146, 60, 60, 58)
    arco_gotico(longe, (240, 110, 40), 152, 70, 48, 48)
    arco_gotico(longe, (255, 200, 90), 162, 84, 28, 34)
    luzes.append([176, 98, 46, [255, 130, 50], 0.9])
    for x in range(126, 230, 12):
        retangulo(longe, (60, 40, 36), (x, 30, 6, 4))
    contornar(longe)
    # correntes, bigornas e canais de lava
    for x in (rng.randint(30, 60), rng.randint(290, 320)):
        for y in range(0, 70, 4):
            pygame.draw.ellipse(meio, (70, 66, 70), (x - 1, y, 3, 5), 1)
        retangulo(meio, (60, 56, 64), (x - 12, HORIZONTE - 10, 26, 6))
        retangulo(meio, (60, 56, 64), (x - 6, HORIZONTE - 4, 14, 8))
    contornar(meio)
    chao_basico(chao, [(40, 26, 24), (28, 18, 18), (12, 8, 8)], rng)
    # canal de lava ATRÁS dos personagens (logo depois do horizonte)
    pontos = [(x, HORIZONTE + 2 + int(1.5 * math.sin(x * 0.08))) for x in range(0, LARGURA + 8, 8)]
    pygame.draw.lines(chao, (255, 120, 40), False, pontos, 3)
    pygame.draw.lines(chao, (255, 210, 110), False, pontos, 1)
    for k in range(0, LARGURA, 60):
        luzes.append([k + 30, HORIZONTE + 2, 16, [255, 120, 40], 0.5])
    # fendas brilhando no chão, longe de onde os pés ficam
    for _ in range(10):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 30, ALTURA - 2)
        comprimento = rng.randint(4, 12)
        linha(chao, (200, 80, 30), (x, y), (x + comprimento, y + rng.randint(-2, 2)))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["brasa", 40]], "cor_nevoa": [80, 30, 20]}


def cena_trono(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(10, 6, 12), (26, 10, 20), (44, 14, 24)])
    vitral(ceu, 150, 10, 52, 80, rng)
    lua(ceu, (176, 46), 14, (170, 40, 40), (130, 30, 34), (70, 20, 30))
    luzes = [[176, 46, 40, [200, 50, 60], 0.3]]
    # trono no fundo
    cor = (34, 24, 40)
    retangulo(longe, cor, (160, 60, 32, 58))
    pygame.draw.polygon(longe, cor, [(160, 60), (176, 36), (192, 60)])
    for dx in (-4, 32):
        retangulo(longe, cor, (160 + dx, 70, 4, 48))
    cranio(longe, 174, 48)
    retangulo(longe, (90, 20, 30), (164, 84, 24, 20))
    contornar(longe)
    luz_de_borda(longe, (90, 40, 60), dx=0, dy=-1)
    # estandartes e braseiros
    for x in (40, 290):
        retangulo(meio, (100, 18, 28), (x, 0, 22, 80))
        pygame.draw.polygon(meio, (100, 18, 28), [(x, 80), (x + 11, 90), (x + 22, 80)])
        pygame.draw.circle(meio, (170, 130, 60), (x + 11, 34), 6, 1)
    for x in (110, 242):
        retangulo(meio, (50, 44, 50), (x - 2, HORIZONTE - 22, 5, 24))
        pygame.draw.polygon(meio, (60, 54, 60), [(x - 8, HORIZONTE - 22), (x + 9, HORIZONTE - 22), (x + 5, HORIZONTE - 16), (x - 4, HORIZONTE - 16)])
        pygame.draw.polygon(meio, (255, 140, 50), [(x - 6, HORIZONTE - 22), (x, HORIZONTE - 36), (x + 7, HORIZONTE - 22)])
        pygame.draw.polygon(meio, (255, 220, 120), [(x - 2, HORIZONTE - 22), (x + 1, HORIZONTE - 30), (x + 3, HORIZONTE - 22)])
        luzes.append([x, HORIZONTE - 28, 30, [255, 140, 60], 1.0])
    contornar(meio)
    degrade(chao, HORIZONTE, ALTURA, [(36, 26, 36), (24, 16, 24), (10, 6, 10)])
    for k in range(-10, 11):
        linha(chao, (16, 10, 16), (176 + k * 8, HORIZONTE), (176 + k * 34, ALTURA))
    pygame.draw.polygon(chao, (100, 20, 30), [(164, HORIZONTE), (188, HORIZONTE), (236, ALTURA), (116, ALTURA)])
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["cinza", 24], ["brasa", 12]],
                                              "cor_nevoa": [60, 20, 30]}


def cena_picadeiro(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    # o lado de dentro da tenda: listras convergindo para o mastro
    for x in range(LARGURA):
        for y in range(HORIZONTE + 4):
            faixa = int((x - 176) / max(8, (HORIZONTE + 10 - y) * 0.6))
            cor = (90, 22, 32) if faixa % 2 == 0 else (120, 104, 90)
            escuro = 0.35 + 0.65 * (y / (HORIZONTE + 4))
            ceu.set_at((x, y), tuple(int(c * escuro) for c in cor))
    retangulo(ceu, (40, 30, 30), (174, 0, 4, HORIZONTE))
    # arquibancadas com olhos brilhando
    luzes = []
    for fileira in range(3):
        y = 84 + fileira * 10
        retangulo(longe, (16, 10, 16), (0, y, LARGURA, 6))
        for _ in range(8):
            x = rng.randrange(LARGURA)
            longe.set_at((x, y + 2), (230, 200, 90))
            longe.set_at((x + 2, y + 2), (230, 200, 90))
    # holofotes cruzados (cones de luz pontilhados)
    for x0, x1 in ((20, 220), (330, 130)):
        poligono_pontilhado(longe, [(x0 - 3, 0), (x0 + 3, 0), (x1 + 30, HORIZONTE + 30), (x1 - 30, HORIZONTE + 30)],
                            (170, 160, 130), 0.12)
        luzes.append([x1, HORIZONTE + 14, 46, [240, 230, 180], 0.25])
    chao_basico(chao, [(70, 56, 40), (50, 40, 30), (20, 16, 14)], rng)
    pygame.draw.ellipse(chao, (120, 30, 40), (20, HORIZONTE + 6, 312, 64), 3)
    for _ in range(80):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA)
        chao.set_at((x, y), rng.choice([(150, 70, 70), (150, 140, 70), (70, 120, 80), (80, 90, 150)]))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["confete", 40]], "cor_nevoa": [80, 60, 60],
                                              "holofotes": [[20, 220], [330, 130]]}



# ============================================================
# CÉUS DE DIA E DE ENTARDECER (as regiões a céu aberto passam do dia à noite)
# ============================================================

def nuvens(sup, rng, quantidade, faixa, cor, cor_borda):
    """Nuvens achatadas pontilhadas (grossas embaixo, ralas em cima)."""
    for _ in range(quantidade):
        cx, cy = rng.randrange(-20, LARGURA + 20), rng.randint(*faixa)
        largura, altura = rng.randint(30, 70), rng.randint(5, 10)
        for y in range(cy - altura, cy + altura // 2):
            for x in range(cx - largura // 2, cx + largura // 2):
                if 0 <= x < LARGURA and 0 <= y < ALTURA:
                    d = math.hypot((x - cx) / (largura / 2), (y - cy) / altura)
                    if d < 1 and BAYER[y % 4][x % 4] / 16 < (1 - d) * 1.6:
                        sup.set_at((x, y), cor_borda if y > cy - 1 else cor)


def sol(sup, centro, raio, cor, cor_halo, forca=0.45):
    halo(sup, centro, raio * 3, cor_halo, forca)
    pygame.draw.circle(sup, cor, centro, raio)
    pygame.draw.circle(sup, clarear(cor, 30), (centro[0] - raio // 3, centro[1] - raio // 3), max(1, raio // 3))


def ceu_de_dia(rng, nome, variante):
    """Dia nublado de fantasia sombria: cinza-azulado, sol pálido atrás das nuvens."""
    ceu = camada()
    degrade(ceu, 0, HORIZONTE + 4, [(70, 88, 112), (104, 120, 138), (146, 150, 150), (170, 160, 142)])
    sol(ceu, ([80, 250, 120][variante], rng.randint(24, 34)), 9, (244, 236, 200), (210, 210, 190), 0.4)
    nuvens(ceu, rng, 9, (16, 70), (176, 180, 186), (140, 146, 156))
    return ceu


def ceu_de_tarde(rng, nome, variante):
    """Entardecer: o sol vermelho descendo atrás dos morros, céu laranja e roxo."""
    ceu = camada()
    degrade(ceu, 0, HORIZONTE + 4, [(40, 26, 62), (96, 44, 74), (178, 74, 66), (236, 132, 70), (250, 186, 100)])
    estrelas(ceu, rng, 12, 24, cores=((200, 170, 200), (150, 120, 170)))
    sol(ceu, ([110, 230, 180][variante], 92), 16, (255, 150, 70), (250, 110, 60), 0.55)
    nuvens(ceu, rng, 7, (30, 80), (130, 56, 76), (210, 100, 70))
    return ceu


# Cenas a céu aberto: o céu de dia e de entardecer de cada uma
CEUS_EXTRAS = {"floresta": (ceu_de_dia, ceu_de_tarde), "circo": (ceu_de_dia, ceu_de_tarde)}

# Nome do cenário -> (função, variantes)
CENAS = {
    "floresta": (cena_floresta, 3), "minas": (cena_minas, 3), "catedral": (cena_catedral, 3),
    "circo": (cena_circo, 3), "acampamento": (cena_acampamento, 1), "titulo": (cena_salao, 1),
    "ninho": (cena_ninho, 1), "forja": (cena_forja, 1), "trono": (cena_trono, 1), "picadeiro": (cena_picadeiro, 1),
}
NOMES_DAS_CAMADAS = ("ceu", "longe", "meio", "chao", "frente")


def juntar_cenas_novas():
    """Cenas das fases novas (ferramentas/cenarios_fase4.py) entram no catálogo."""
    from cenarios_fase4 import CENAS_NOVAS, CEUS_NOVOS
    from cenarios_finais import CENAS_FINAIS
    from cenarios_reino_dos_ratos import CENAS_DO_REINO
    CENAS.update(CENAS_NOVAS)
    CENAS.update(CENAS_FINAIS)                  # versões detalhadas da Cidadela e da Catedral do Eclipse
    CENAS.update(CENAS_DO_REINO)                # fase secreta do Reino dos Ratos (zonas e sala do trono)
    CEUS_EXTRAS.update(CEUS_NOVOS)


def gerar(filtro=None):
    pygame.init()
    juntar_cenas_novas()
    os.makedirs(PASTA, exist_ok=True)
    catalogo = {}
    caminho_catalogo = os.path.join(PASTA, "cenarios.json")
    if filtro and os.path.exists(caminho_catalogo):
        with open(caminho_catalogo, encoding="utf-8") as arquivo:
            catalogo = json.load(arquivo)
    for nome, (funcao, variantes) in CENAS.items():
        if filtro and nome not in filtro:
            continue
        for variante in range(variantes):
            rng = random.Random(f"{nome}-{variante}")
            camadas, configuracao = funcao(rng, variante)
            for nome_camada, sup in zip(NOMES_DAS_CAMADAS, camadas):
                pygame.image.save(sup, os.path.join(PASTA, f"{nome}_{variante}_{nome_camada}.png"))
            for nome_camada, sup in configuracao.pop("_camadas", {}).items():     # chão alagado, nó da Rainha...
                pygame.image.save(sup, os.path.join(PASTA, f"{nome}_{variante}_{nome_camada}.png"))
            if nome in CEUS_EXTRAS:                           # céus de dia e de entardecer
                dia, tarde = CEUS_EXTRAS[nome]
                ceu_rng = random.Random(f"{nome}-{variante}-ceu")
                pygame.image.save(dia(ceu_rng, nome, variante), os.path.join(PASTA, f"{nome}_{variante}_ceu_dia.png"))
                pygame.image.save(tarde(ceu_rng, nome, variante), os.path.join(PASTA, f"{nome}_{variante}_ceu_tarde.png"))
                configuracao["ciclo"] = True
            configuracao["variantes"] = variantes
            catalogo[f"{nome}_{variante}"] = configuracao
            print("gerado:", nome, variante)
    with open(caminho_catalogo, "w", encoding="utf-8") as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=1)
    gerar_previa(catalogo)


def gerar_previa(catalogo):
    """Uma prancha com todos os cenários (camadas juntas), em tamanho 1x."""
    chaves = sorted(catalogo)
    colunas = 4
    linhas = (len(chaves) + colunas - 1) // colunas
    previa = pygame.Surface((colunas * (LARGURA - 2 * MARGEM) * 2, linhas * ALTURA * 2))
    for i, chave in enumerate(chaves):
        imagem = pygame.Surface((LARGURA, ALTURA))
        for nome_camada in NOMES_DAS_CAMADAS:
            caminho = os.path.join(PASTA, f"{chave}_{nome_camada}.png")
            if os.path.exists(caminho):
                camada_png = pygame.image.load(caminho)
                if camada_png.get_width() != LARGURA:                       # cena em resolução dobrada
                    camada_png = pygame.transform.smoothscale(camada_png, (LARGURA, ALTURA))
                imagem.blit(camada_png, (0, 0))
        recorte = imagem.subsurface((MARGEM, 0, LARGURA - 2 * MARGEM, ALTURA))
        grande = pygame.transform.scale(recorte, (recorte.get_width() * 2, ALTURA * 2))
        previa.blit(grande, ((i % colunas) * grande.get_width(), (i // colunas) * grande.get_height()))
    pasta_previas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "previas_ui")    # descartável (fora dos assets)
    os.makedirs(pasta_previas, exist_ok=True)
    pygame.image.save(previa, os.path.join(pasta_previas, "previa_cenarios_macabros.png"))


if __name__ == "__main__":
    gerar(sys.argv[1:] or None)
