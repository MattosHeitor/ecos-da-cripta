"""Cenários das fases novas da fase 4 (mesma técnica de cenarios_macabros.py: 352x180, 5 camadas).

cenarios_macabros.gerar() junta CENAS_NOVAS e CEUS_NOVOS aos dele. Uma seção por fase.
config "noturnas": partículas que só aparecem quando escurece (ex.: a névoa do Bosque).
"""
import math

import pygame

from cenarios_macabros import (LARGURA, ALTURA, HORIZONTE, camada, degrade, estrelas, lua, galho, pontilhar,
                               contornar, luz_de_borda, chao_basico, retangulo, linha, osso, cranio,
                               ceu_de_dia, ceu_de_tarde)


# ============================================================
# BOSQUE CARMESIM
# ============================================================

def copa(sup, rng, centro, raio, cores):
    """Copa de folhas: muitos tufos em tons de vermelho, mais claros em cima (luz da lua)."""
    cx, cy = centro
    for _ in range(int(raio * 3)):
        a = rng.uniform(0, math.tau)
        d = raio * math.sqrt(rng.random())
        x, y = int(cx + math.cos(a) * d * 1.3), int(cy + math.sin(a) * d * 0.8)
        tom = cores[0] if y > cy + raio * 0.2 else (cores[1] if y > cy - raio * 0.3 else cores[2])
        pygame.draw.circle(sup, tom, (x, y), rng.randint(2, 4))


def arvore_carmesim(sup, rng, x, base, altura, grossura, cores_copa, cor_tronco=(34, 16, 18)):
    topo = base - altura
    pygame.draw.polygon(sup, cor_tronco, [(x - grossura, base), (x + grossura, base), (x + grossura // 2, topo + 10),
                                          (x - grossura // 2, topo + 10)])
    for lado in (-1, 1):                               # raízes aparentes
        linha(sup, cor_tronco, (x + lado * grossura, base), (x + lado * (grossura + 6), base + 2), 2)
    for k in range(3):
        galho(sup, cor_tronco, x, topo + 14 + k * 6, -math.pi / 2 + rng.uniform(-0.9, 0.9), rng.randint(10, 18), 2, rng)
    copa(sup, rng, (x, topo + 6), altura * 0.32, cores_copa)


def cena_bosque_carmesim(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(14, 6, 16), (40, 10, 24), (84, 18, 32), (120, 30, 36)])
    estrelas(ceu, rng, 50, 60)
    lua(ceu, ([90, 260, 180][variante], rng.randint(28, 40)), 14, (220, 120, 100), (170, 80, 70), (120, 40, 40), rng=rng)

    # morro e bosque distante, avermelhado e apagado pela névoa
    pontos = [(0, ALTURA)] + [(x, 90 + int(7 * math.sin(x * 0.04 + variante * 2)) + rng.randint(-2, 2))
                              for x in range(0, LARGURA + 8, 8)] + [(LARGURA, ALTURA)]
    pygame.draw.polygon(longe, (54, 22, 36), pontos)
    for _ in range(16):
        x = rng.randint(0, LARGURA)
        copa(longe, rng, (x, rng.randint(80, 92)), rng.randint(7, 11), ((70, 24, 36), (86, 30, 42), (100, 40, 50)))
    pontilhar(longe, (0, 84, LARGURA, 30), (110, 60, 70), 0.25, so_onde_tem=True)

    # árvores grandes de folhas cor de sangue
    folhas = ((110, 16, 26), (156, 30, 38), (200, 60, 60))
    xs = [rng.randint(8, 50), rng.randint(110, 150), rng.randint(240, 280), rng.randint(310, 345)]
    if variante == 1:                                   # bosque fechado: mais árvores
        xs += [rng.randint(60, 100), rng.randint(190, 220)]
    for x in xs:
        arvore_carmesim(meio, rng, x, HORIZONTE + 4, rng.randint(70, 96), rng.randint(4, 7), folhas)
    luz_de_borda(meio, (200, 90, 80), dx=1, dy=-1)
    contornar(meio)
    if variante == 1:                                   # musgo pendurado
        for _ in range(10):
            x, y = rng.randrange(LARGURA), rng.randint(20, 60)
            linha(meio, (70, 40, 50), (x, y), (x + rng.randint(-1, 1), y + rng.randint(8, 18)))
    if variante == 2:                                   # círculo de pedras antigas (altar druida)
        for k in range(6):
            x = 60 + k * 48 + rng.randint(-6, 6)
            altura = rng.randint(14, 22)
            retangulo(meio, (60, 54, 66), (x, HORIZONTE - altura, 8, altura + 2))
            linha(meio, (110, 40, 50), (x + 2, HORIZONTE - altura + 4), (x + 5, HORIZONTE - altura + 8))

    chao_basico(chao, [(46, 18, 22), (32, 12, 16), (14, 6, 8)], rng)
    luzes = []
    for _ in range(26):                                 # folhas caídas
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA - 2)
        chao.set_at((x, y), rng.choice([(150, 30, 36), (190, 60, 50), (120, 20, 30)]))
    for _ in range(5):                                  # cogumelos de chapéu vermelho
        x, y = rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 2, HORIZONTE + 16)
        retangulo(chao, (200, 190, 160), (x, y, 1, 2))
        retangulo(chao, (200, 40, 44), (x - 1, y - 1, 3, 1))
    for _ in range(3):                                  # seiva brilhando nas raízes
        x, y = rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 4, HORIZONTE + 24)
        retangulo(chao, (230, 60, 60), (x, y, 2, 1))
        luzes.append([x, y, 7, [240, 70, 60], 0.5])
    for _ in range(3):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 8, ALTURA - 6))
    for x in list(range(0, 50)) + list(range(LARGURA - 50, LARGURA)):   # samambaias vermelhas na frente
        if rng.random() < 0.45:
            altura = rng.randint(4, 12)
            linha(frente, (60, 14, 22), (x, ALTURA), (x + rng.randint(-3, 3), ALTURA - altura))
    configuracao = {"luzes": luzes, "particulas": [["vaga_lume", 26], ["nevoa", 3], ["poeira", 6]],
                    "noturnas": ["nevoa"], "cor_nevoa": [120, 60, 70]}
    return [ceu, longe, meio, chao, frente], configuracao


def cena_raizal(rng, variante):
    """Sala da Mãe-Raiz: raízes gigantes em arco e poças de seiva brilhando."""
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(10, 4, 8), (30, 8, 14), (60, 14, 20)])
    luzes = []
    # árvore-mãe gigante ao fundo
    pygame.draw.polygon(longe, (30, 12, 14), [(130, HORIZONTE), (150, 20), (202, 20), (222, HORIZONTE)])
    copa(longe, rng, (176, 22), 60, ((70, 10, 18), (100, 18, 26), (130, 30, 34)))
    for dx in (-10, 10):
        pygame.draw.circle(longe, (255, 60, 50), (176 + dx, 64), 2)
        luzes.append([176 + dx, 64, 10, [255, 60, 50], 0.6])
    contornar(longe)
    # raízes em arco por cima da cena
    for x0, x1 in ((0, 120), (60, 210), (230, 352), (150, 300)):
        pontos = [(x, HORIZONTE + 2 - int(60 * math.sin(math.pi * (x - x0) / (x1 - x0)))) for x in range(x0, x1 + 1, 6)]
        pygame.draw.lines(meio, (40, 18, 18), False, pontos, 6)
        pygame.draw.lines(meio, (70, 34, 30), False, pontos, 2)
    contornar(meio)
    chao_basico(chao, [(44, 16, 20), (30, 10, 14), (12, 4, 6)], rng)
    for _ in range(5):                                  # poças de seiva
        x, y = rng.randrange(10, LARGURA - 40), rng.randrange(HORIZONTE + 6, ALTURA - 10)
        pygame.draw.ellipse(chao, (150, 20, 30), (x, y, rng.randint(18, 34), rng.randint(4, 6)))
        luzes.append([x + 10, y + 2, 12, [230, 50, 50], 0.45])
    for _ in range(4):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 6, ALTURA - 6))
    cranio(chao, rng.randrange(40, LARGURA - 40), rng.randrange(HORIZONTE + 16, ALTURA - 8))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["vaga_lume", 14], ["nevoa", 2]],
                                              "cor_nevoa": [110, 40, 50]}


# ============================================================
# PÂNTANO DOS AFOGADOS
# ============================================================

def arvore_do_brejo(sup, rng, x, base, altura, cor=(18, 22, 18)):
    """Árvore torta do brejo com barbas de musgo penduradas."""
    topo = base - altura
    pontos = [(x - 3, base), (x + 3, base), (x + 2 + rng.randint(-3, 3), topo + 8), (x - 2, topo + 8)]
    pygame.draw.polygon(sup, cor, pontos)
    for k in range(4):
        galho(sup, cor, x, topo + 10 + k * 5, -math.pi / 2 + rng.uniform(-1.2, 1.2), rng.randint(10, 20), 2, rng)
    for _ in range(7):                                  # musgo pendurado
        mx, my = x + rng.randint(-16, 16), topo + rng.randint(4, 24)
        linha(sup, (44, 66, 46), (mx, my), (mx + rng.randint(-1, 1), my + rng.randint(6, 16)))


def agua_parada(sup, rng, topo, cor=(14, 26, 28), brilho=(70, 110, 110)):
    """Faixa de água escura com reflexos e vitórias-régias."""
    pygame.draw.rect(sup, cor, (0, topo, LARGURA, ALTURA - topo))
    for _ in range(40):
        x, y = rng.randrange(LARGURA), rng.randrange(topo + 2, ALTURA)
        linha(sup, brilho, (x, y), (x + rng.randint(3, 9), y))
    for _ in range(9):
        x, y = rng.randrange(LARGURA), rng.randrange(topo + 6, ALTURA - 4)
        pygame.draw.ellipse(sup, (40, 80, 40), (x, y, 7, 3))


def cena_pantano_dos_afogados(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(8, 14, 14), (18, 30, 30), (34, 50, 46), (50, 66, 56)])
    estrelas(ceu, rng, 35, 50)
    lua(ceu, ([70, 280, 200][variante], rng.randint(26, 38)), 12, (190, 210, 170), (150, 170, 130), (80, 110, 90), rng=rng)
    pontos = [(0, ALTURA)] + [(x, 98 + int(5 * math.sin(x * 0.05 + variante)) + rng.randint(-2, 2))
                              for x in range(0, LARGURA + 8, 8)] + [(LARGURA, ALTURA)]
    pygame.draw.polygon(longe, (26, 40, 38), pontos)
    for _ in range(12):
        arvore_do_brejo(longe, rng, rng.randint(0, LARGURA), rng.randint(98, 104), rng.randint(18, 30), (30, 46, 42))
    pontilhar(longe, (0, 88, LARGURA, 30), (60, 80, 70), 0.3, so_onde_tem=True)
    for x in [rng.randint(10, 50), rng.randint(130, 170), rng.randint(270, 340)]:
        arvore_do_brejo(meio, rng, x, HORIZONTE + 4, rng.randint(70, 95))
    luz_de_borda(meio, (70, 120, 100), dx=1, dy=-1)
    contornar(meio)
    luzes = []
    if variante == 1:                                   # casas afundadas
        for x in (90, 230):
            pygame.draw.polygon(meio, (36, 32, 30), [(x, HORIZONTE + 2), (x, HORIZONTE - 18), (x + 14, HORIZONTE - 30),
                                                      (x + 28, HORIZONTE - 18), (x + 28, HORIZONTE + 2)])
            retangulo(meio, (200, 180, 90), (x + 10, HORIZONTE - 14, 4, 4))
            luzes.append([x + 12, HORIZONTE - 12, 8, [220, 190, 100], 0.5])
    if variante == 2:                                   # cruzes meio afundadas
        for _ in range(6):
            x = rng.randrange(20, LARGURA - 20)
            linha(meio, (60, 56, 52), (x, HORIZONTE + 2), (x + rng.randint(-2, 2), HORIZONTE - 14), 2)
            linha(meio, (60, 56, 52), (x - 4, HORIZONTE - 10), (x + 4, HORIZONTE - 11), 2)
    chao_basico(chao, [(30, 34, 26), (22, 24, 18), (10, 12, 8)], rng)
    agua_parada(chao, rng, HORIZONTE + 1)
    for _ in range(4):                                  # lanternas boiando (luz verde)
        x, y = rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 4, HORIZONTE + 30)
        retangulo(chao, (40, 40, 36), (x - 1, y - 2, 3, 3))
        chao.set_at((x, y - 1), (150, 255, 160))
        luzes.append([x, y - 1, 9, [120, 255, 150], 0.5])
    for x in list(range(0, 50)) + list(range(LARGURA - 50, LARGURA)):   # juncos na frente
        if rng.random() < 0.5:
            altura = rng.randint(5, 16)
            linha(frente, (24, 36, 22), (x, ALTURA), (x + rng.randint(-2, 2), ALTURA - altura))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["nevoa", 3], ["vaga_lume", 14], ["gota", 4]],
                                              "cor_nevoa": [80, 110, 100]}


def cena_embarcadouro(rng, variante):
    """Sala do Barqueiro: píer de madeira apodrecida, água negra e dezenas de lanternas verdes."""
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(4, 8, 8), (10, 20, 20), (20, 34, 32)])
    luzes = []
    for _ in range(16):                                 # lanternas ao longe sobre a água
        x, y = rng.randrange(LARGURA), rng.randrange(60, HORIZONTE - 4)
        longe.set_at((x, y), (150, 255, 170))
        luzes.append([x, y, 6, [110, 230, 140], 0.35])
    pygame.draw.rect(longe, (8, 16, 16), (0, HORIZONTE - 20, LARGURA, 22))
    for k in range(-6, 7):                              # tábuas do píer em perspectiva
        linha(meio, (60, 44, 30), (176 + k * 6, HORIZONTE - 18), (176 + k * 24, HORIZONTE + 4))
    pygame.draw.polygon(meio, (50, 36, 26), [(150, HORIZONTE - 18), (202, HORIZONTE - 18), (250, HORIZONTE + 4), (102, HORIZONTE + 4)], 0)
    for x in (110, 150, 202, 242):                      # estacas
        retangulo(meio, (34, 26, 20), (x, HORIZONTE - 34, 4, 36))
    contornar(meio)
    chao_basico(chao, [(16, 24, 24), (10, 16, 16), (4, 8, 8)], rng)
    agua_parada(chao, rng, HORIZONTE + 1, (8, 16, 18), (50, 90, 90))
    for _ in range(6):
        x, y = rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 6, ALTURA - 6)
        chao.set_at((x, y), (220, 180, 70))             # moedas no fundo raso
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["nevoa", 4], ["gota", 6]],
                                              "cor_nevoa": [70, 100, 90]}


# ============================================================
# CATACUMBAS DA ORDEM CAÍDA
# ============================================================

def nicho_de_ossos(sup, rng, x, y, largura, altura):
    """Nicho escavado na parede, cheio de crânios empilhados."""
    pygame.draw.rect(sup, (16, 12, 14), (x, y, largura, altura))
    for linha_y in range(y + altura - 4, y + 2, -4):
        for coluna_x in range(x + 2, x + largura - 3, 4):
            if rng.random() < 0.85:
                cranio(sup, coluna_x, linha_y)


def cena_catacumbas_da_ordem_caida(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(10, 8, 10), (22, 18, 20), (34, 28, 30)])
    # parede de pedra com nichos de ossos e arcos
    pygame.draw.rect(longe, (40, 34, 36), (0, 10, LARGURA, HORIZONTE - 8))
    for y in range(14, HORIZONTE, 10):                            # fiadas de pedra
        deslocado = 0 if (y // 10) % 2 else 8
        for x in range(-deslocado, LARGURA, 16):
            pygame.draw.rect(longe, (30, 26, 28), (x, y, 16, 10), 1)
    for k in range(5):
        x = 14 + k * 70 + rng.randint(-4, 4)
        nicho_de_ossos(longe, rng, x, 40 + (k % 2) * 8, 34, 30)
    pontilhar(longe, (0, 10, LARGURA, HORIZONTE - 8), (60, 54, 54), 0.08)
    luzes = []
    for x in (60, 176, 292):                                      # arcos e tochas
        pygame.draw.arc(meio, (54, 46, 48), (x - 34, 0, 68, 60), 0, math.pi, 5)
        retangulo(meio, (54, 46, 48), (x - 36, 28, 6, HORIZONTE - 26))
        retangulo(meio, (54, 46, 48), (x + 30, 28, 6, HORIZONTE - 26))
    for x in (40, 120, 232, 312):
        retangulo(meio, (60, 44, 30), (x, 60, 3, 10))
        pygame.draw.polygon(meio, (255, 170, 60), [(x - 2, 60), (x + 1, 52), (x + 4, 60)])
        luzes.append([x + 1, 56, 22, [255, 160, 70], 0.8])
    if variante == 1:                                             # estandartes rasgados da Ordem
        for x in (96, 256):
            retangulo(meio, (110, 100, 80), (x, 6, 18, 46))
            pygame.draw.polygon(meio, (110, 100, 80), [(x, 52), (x + 9, 60), (x + 18, 52)])
            linha(meio, (60, 30, 30), (x + 9, 14), (x + 9, 40), 2)
            linha(meio, (60, 30, 30), (x + 3, 22), (x + 15, 22), 2)
    if variante == 2:                                             # sarcófagos abertos
        for x in (70, 250):
            pygame.draw.rect(meio, (70, 64, 62), (x, HORIZONTE - 14, 40, 14))
            pygame.draw.rect(meio, (90, 82, 78), (x - 4, HORIZONTE - 22, 26, 6))
    contornar(meio)
    chao_basico(chao, [(46, 40, 40), (32, 28, 28), (14, 12, 12)], rng)
    for _ in range(8):
        osso(chao, rng.randrange(10, LARGURA - 10), rng.randrange(HORIZONTE + 4, ALTURA - 4))
    for _ in range(3):
        cranio(chao, rng.randrange(20, LARGURA - 20), rng.randrange(HORIZONTE + 10, ALTURA - 6))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["poeira", 30], ["cinza", 10]],
                                              "cor_nevoa": [60, 50, 50]}


def cena_capela_profanada(rng, variante):
    """Sala do Inquisidor: capela da Ordem com o altar em chamas sagradas e vitrais quebrados."""
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(14, 8, 8), (30, 16, 12), (50, 26, 18)])
    luzes = []
    for x in (70, 282):                                           # janelas altas quebradas
        pygame.draw.polygon(longe, (90, 70, 50), [(x - 14, 90), (x - 14, 30), (x, 14), (x + 14, 30), (x + 14, 90)])
        pygame.draw.polygon(longe, (20, 12, 10), [(x - 10, 88), (x - 10, 32), (x, 20), (x + 10, 32), (x + 10, 88)])
        for _ in range(6):
            longe.set_at((x + rng.randint(-8, 8), rng.randint(34, 86)), rng.choice([(200, 60, 50), (220, 180, 80), (80, 120, 200)]))
    pygame.draw.rect(longe, (70, 60, 56), (140, HORIZONTE - 30, 72, 30))          # altar
    pygame.draw.rect(longe, (110, 96, 80), (136, HORIZONTE - 34, 80, 6))
    for k in range(5):                                            # chamas sagradas sobre o altar
        x = 148 + k * 14
        pygame.draw.polygon(longe, (255, 200, 90), [(x - 4, HORIZONTE - 34), (x, HORIZONTE - 52 - (k % 2) * 6), (x + 4, HORIZONTE - 34)])
        pygame.draw.polygon(longe, (255, 245, 200), [(x - 1, HORIZONTE - 34), (x, HORIZONTE - 44), (x + 1, HORIZONTE - 34)])
        luzes.append([x, HORIZONTE - 42, 26, [255, 210, 120], 0.9])
    contornar(longe)
    for x in (30, 322):                                           # colunas
        retangulo(meio, (60, 52, 50), (x - 6, 0, 12, HORIZONTE + 2))
    contornar(meio)
    degrade(chao, HORIZONTE, ALTURA, [(54, 44, 40), (36, 28, 26), (14, 10, 10)])
    for k in range(-10, 11):
        linha(chao, (30, 22, 20), (176 + k * 8, HORIZONTE), (176 + k * 34, ALTURA))
    pygame.draw.polygon(chao, (110, 30, 30), [(160, HORIZONTE), (192, HORIZONTE), (240, ALTURA), (112, ALTURA)])
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["brasa", 26], ["cinza", 16]],
                                              "cor_nevoa": [80, 50, 40]}


# ============================================================
# MINAS DE BRASA
# ============================================================

def rio_de_lava(sup, luzes, y, espessura=3):
    pontos = [(x, y + int(1.5 * math.sin(x * 0.07))) for x in range(0, LARGURA + 8, 8)]
    pygame.draw.lines(sup, (255, 110, 30), False, pontos, espessura)
    pygame.draw.lines(sup, (255, 220, 120), False, pontos, 1)
    for k in range(0, LARGURA, 50):
        luzes.append([k + 25, y, 18, [255, 120, 40], 0.5])


def cena_minas_de_brasa(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(20, 8, 6), (46, 16, 10), (80, 28, 14), (40, 14, 8)])
    luzes = []
    # paredes da caverna com veios de brasa
    pontos = [(0, 0)] + [(x, 30 + int(12 * math.sin(x * 0.05 + variante)) + rng.randint(-3, 3)) for x in range(0, LARGURA + 8, 8)] + [(LARGURA, 0)]
    pygame.draw.polygon(longe, (34, 24, 22), pontos)
    pontos = [(0, ALTURA)] + [(x, 86 + int(8 * math.sin(x * 0.04 + variante * 2)) + rng.randint(-2, 2)) for x in range(0, LARGURA + 8, 8)] + [(LARGURA, ALTURA)]
    pygame.draw.polygon(longe, (44, 30, 26), pontos)
    for _ in range(14):                                     # veios de minério de brasa
        x, y = rng.randrange(LARGURA), rng.choice([rng.randint(6, 34), rng.randint(88, 110)])
        linha(longe, (230, 100, 40), (x, y), (x + rng.randint(-8, 8), y + rng.randint(-4, 4)))
        luzes.append([x, y, 6, [255, 120, 40], 0.4])
    contornar(longe)
    # pilares anões entalhados e trilhos
    for x in (40, 176, 312):
        retangulo(meio, (64, 50, 44), (x - 8, 20, 16, HORIZONTE - 18))
        retangulo(meio, (90, 70, 56), (x - 10, 20, 20, 5))
        retangulo(meio, (90, 70, 56), (x - 10, HORIZONTE - 6, 20, 6))
        linha(meio, (40, 30, 26), (x - 4, 30), (x + 4, 30))
    if variante == 1:                                       # carrinho de mina com brasas
        pygame.draw.polygon(meio, (70, 60, 56), [(120, HORIZONTE - 14), (150, HORIZONTE - 14), (146, HORIZONTE - 2), (124, HORIZONTE - 2)])
        for x in (126, 144):
            pygame.draw.circle(meio, (40, 36, 36), (x, HORIZONTE), 3)
        for k in range(4):
            meio.set_at((128 + k * 5, HORIZONTE - 15), (255, 140, 50))
        luzes.append([135, HORIZONTE - 16, 14, [255, 130, 50], 0.6])
    if variante == 2:                                       # caldeira e correntes
        pygame.draw.circle(meio, (60, 52, 50), (260, HORIZONTE - 22), 18)
        pygame.draw.circle(meio, (255, 120, 40), (260, HORIZONTE - 22), 6)
        luzes.append([260, HORIZONTE - 22, 24, [255, 120, 40], 0.7])
        for y in range(0, 50, 4):
            pygame.draw.ellipse(meio, (70, 66, 70), (230, y, 3, 5), 1)
    contornar(meio)
    chao_basico(chao, [(50, 34, 28), (34, 22, 18), (14, 8, 6)], rng)
    rio_de_lava(chao, luzes, HORIZONTE + 3)
    for _ in range(10):                                     # fendas brilhando
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 30, ALTURA - 2)
        linha(chao, (200, 80, 30), (x, y), (x + rng.randint(4, 12), y + rng.randint(-2, 2)))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["brasa", 36], ["cinza", 16]],
                                              "cor_nevoa": [90, 40, 20]}


def cena_forja_antiga(rng, variante):
    """Sala do Forjador Antigo: bigorna gigante entre estátuas de reis anões e uma fornalha que nunca apagou."""
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(24, 10, 6), (54, 20, 10), (90, 36, 16)])
    luzes = []
    pygame.draw.polygon(longe, (50, 34, 28), [(96, HORIZONTE), (110, 18), (242, 18), (256, HORIZONTE)])   # fornalha
    pygame.draw.polygon(longe, (255, 140, 50), [(140, HORIZONTE - 2), (150, 50), (202, 50), (212, HORIZONTE - 2)])
    pygame.draw.polygon(longe, (255, 220, 120), [(160, HORIZONTE - 2), (168, 70), (184, 70), (192, HORIZONTE - 2)])
    luzes.append([176, 80, 50, [255, 140, 50], 1.0])
    for x in (30, 322):                                     # estátuas de reis anões
        retangulo(longe, (70, 60, 56), (x - 10, 40, 20, HORIZONTE - 40))
        pygame.draw.circle(longe, (80, 70, 64), (x, 34), 9)
        pygame.draw.polygon(longe, (80, 70, 64), [(x - 7, 38), (x + 7, 38), (x, 58)])                  # barba de pedra
        retangulo(longe, (150, 120, 60), (x - 9, 24, 18, 4))                                             # coroa
    contornar(longe)
    pygame.draw.polygon(meio, (70, 66, 74), [(140, HORIZONTE - 10), (212, HORIZONTE - 10), (200, HORIZONTE - 4), (152, HORIZONTE - 4)])
    retangulo(meio, (60, 56, 64), (166, HORIZONTE - 4, 20, 8))
    contornar(meio)
    chao_basico(chao, [(56, 36, 28), (36, 22, 16), (14, 8, 6)], rng)
    for k in range(-8, 9):
        linha(chao, (80, 40, 20), (176 + k * 10, HORIZONTE), (176 + k * 30, ALTURA))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["brasa", 50]], "cor_nevoa": [100, 50, 20]}


# ============================================================
# CIDADELA CONGELADA
# ============================================================

def torre_de_gelo(sup, x, base, largura, altura, cor=(120, 150, 180), cor_borda=(200, 225, 245)):
    """Torre com ameias e telhado pontudo, coberta de gelo."""
    pygame.draw.rect(sup, cor, (x, base - altura, largura, altura))
    for k in range(0, largura, 6):
        pygame.draw.rect(sup, cor, (x + k, base - altura - 4, 4, 4))
    pygame.draw.polygon(sup, cor_borda, [(x - 2, base - altura - 4), (x + largura // 2, base - altura - 22),
                                         (x + largura + 2, base - altura - 4)])
    linha(sup, cor_borda, (x, base - altura), (x + largura, base - altura))
    pygame.draw.rect(sup, (60, 90, 130), (x + largura // 2 - 2, base - altura + 10, 4, 7))


def cena_cidadela_congelada(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(10, 14, 30), (24, 34, 60), (50, 70, 100), (90, 110, 140)])
    estrelas(ceu, rng, 60, 70, cores=((200, 220, 255), (150, 170, 220), (240, 245, 255)))
    lua(ceu, ([60, 290, 180][variante], rng.randint(24, 36)), 13, (220, 235, 255), (170, 190, 220), (100, 130, 180), rng=rng)
    pontos = [(0, ALTURA)] + [(x, 80 + int(14 * math.sin(x * 0.03 + variante))) for x in range(0, LARGURA + 8, 8)] + [(LARGURA, ALTURA)]
    pygame.draw.polygon(longe, (90, 110, 140), pontos)                                      # montanhas nevadas
    for x in range(0, LARGURA, 8):
        y = 80 + int(14 * math.sin(x * 0.03 + variante))
        linha(longe, (220, 230, 245), (x, y), (x + 8, y + rng.randint(-1, 1)))
    torre_de_gelo(longe, 140 + variante * 20, 100, 30, 46)
    torre_de_gelo(longe, 210 + variante * 10, 100, 22, 34)
    pontilhar(longe, (0, 70, LARGURA, 40), (160, 180, 210), 0.12, so_onde_tem=True)
    luzes = []
    # muralha da frente, coberta de gelo
    pygame.draw.rect(meio, (100, 120, 150), (0, HORIZONTE - 34, LARGURA, 36))
    for x in range(0, LARGURA, 12):
        pygame.draw.rect(meio, (100, 120, 150), (x, HORIZONTE - 40, 8, 6))
        pygame.draw.rect(meio, (220, 235, 250), (x, HORIZONTE - 40, 8, 2))
    for _ in range(14):                                                                        # pingentes
        x = rng.randrange(LARGURA)
        pygame.draw.polygon(meio, (200, 230, 250), [(x - 2, HORIZONTE - 34), (x, HORIZONTE - 34 + rng.randint(5, 12)), (x + 2, HORIZONTE - 34)])
    if variante == 1:                                                                          # portão congelado
        pygame.draw.rect(meio, (40, 60, 90), (156, HORIZONTE - 30, 40, 32))
        pygame.draw.arc(meio, (200, 225, 245), (156, HORIZONTE - 46, 40, 34), 0, math.pi, 3)
    if variante == 2:                                                                          # estátuas de guardas congelados
        for x in (80, 270):
            retangulo(meio, (170, 200, 230), (x, HORIZONTE - 58, 10, 24))
            pygame.draw.circle(meio, (190, 215, 240), (x + 5, HORIZONTE - 62), 5)
    for x in (40, 312):                                                                        # braseiros azuis
        retangulo(meio, (60, 60, 70), (x - 2, HORIZONTE - 50, 5, 12))
        pygame.draw.polygon(meio, (120, 200, 255), [(x - 4, HORIZONTE - 50), (x, HORIZONTE - 62), (x + 4, HORIZONTE - 50)])
        luzes.append([x, HORIZONTE - 56, 20, [120, 200, 255], 0.7])
    contornar(meio)
    chao_basico(chao, [(200, 214, 230), (160, 176, 200), (110, 124, 150)], rng)               # neve
    for _ in range(40):
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 2, ALTURA)
        chao.set_at((x, y), (240, 245, 255))
    for _ in range(4):
        x, y = rng.randrange(10, LARGURA - 40), rng.randrange(HORIZONTE + 8, ALTURA - 8)
        pygame.draw.ellipse(chao, (150, 190, 220), (x, y, rng.randint(14, 30), 3))            # placas de gelo
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["neve", 60], ["nevoa", 1]],
                                              "cor_nevoa": [180, 200, 230]}


def cena_trono_de_gelo(rng, variante):
    """Sala da Rainha: salão de gelo azul, trono de cristal e colunas de pingentes."""
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(10, 20, 40), (24, 46, 80), (50, 90, 130)])
    luzes = []
    for x in range(0, LARGURA, 40):                                                            # paredes de cristal
        pygame.draw.polygon(longe, (90, 140, 190), [(x, HORIZONTE), (x + 8, 20), (x + 20, 4), (x + 32, 20), (x + 40, HORIZONTE)])
        linha(longe, (190, 225, 250), (x + 20, 6), (x + 20, HORIZONTE - 4))
    pygame.draw.polygon(longe, (170, 210, 245), [(146, HORIZONTE), (152, 50), (176, 24), (200, 50), (206, HORIZONTE)])   # trono
    pygame.draw.polygon(longe, (120, 170, 220), [(160, HORIZONTE), (164, 64), (188, 64), (192, HORIZONTE)])
    luzes.append([176, 50, 40, [150, 220, 255], 0.8])
    contornar(longe)
    for x in (30, 322):
        retangulo(meio, (150, 190, 230), (x - 6, 0, 12, HORIZONTE + 2))
        for k in range(5):
            pygame.draw.polygon(meio, (210, 235, 250), [(x - 6, 12 + k * 18), (x - 12, 18 + k * 18), (x - 6, 22 + k * 18)])
    contornar(meio)
    degrade(chao, HORIZONTE, ALTURA, [(150, 190, 225), (110, 150, 190), (60, 90, 130)])
    for k in range(-10, 11):
        linha(chao, (200, 230, 250), (176 + k * 8, HORIZONTE), (176 + k * 34, ALTURA))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["neve", 40]], "cor_nevoa": [180, 210, 240]}


# ============================================================
# CATEDRAL DO ECLIPSE
# ============================================================

CORES_VITRAL = [(170, 40, 60), (50, 80, 180), (210, 170, 60), (110, 50, 150), (50, 140, 100)]


def sol_negro(sup, luzes, x, y, raio):
    """Eclipse: disco negro com coroa dourada e raios."""
    for k in range(16):
        a = k / 16 * math.tau
        linha(sup, (230, 180, 100), (x + int(math.cos(a) * raio), y + int(math.sin(a) * raio)),
              (x + int(math.cos(a) * raio * (1.6 + 0.3 * (k % 2))), y + int(math.sin(a) * raio * (1.6 + 0.3 * (k % 2)))))
    pygame.draw.circle(sup, (255, 214, 140), (x, y), raio + 2)
    pygame.draw.circle(sup, (10, 6, 14), (x, y), raio)
    luzes.append([x, y, raio * 3, [255, 200, 130], 0.7])


def vitral(sup, rng, x, topo, largura, altura, quebrado=0.0):
    """Janela gótica com painéis coloridos (alguns faltando)."""
    pygame.draw.polygon(sup, (60, 50, 70), [(x - largura // 2 - 2, topo + altura), (x - largura // 2 - 2, topo + largura // 2),
                                            (x, topo - 2), (x + largura // 2 + 2, topo + largura // 2), (x + largura // 2 + 2, topo + altura)])
    for py in range(topo + 2, topo + altura - 1, 5):
        for px in range(x - largura // 2, x + largura // 2, 4):
            if py < topo + largura // 2 and abs(px + 2 - x) > (py - topo):
                continue
            cor = (14, 10, 18) if rng.random() < quebrado else rng.choice(CORES_VITRAL)
            pygame.draw.rect(sup, cor, (px, py, 3, 4))


def cena_catedral_do_eclipse(rng, variante):
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(8, 4, 14), (24, 12, 36), (50, 26, 60)])
    luzes = []
    sol_negro(ceu, luzes, [176, 90, 260][variante], 26, 12)
    # nave da catedral: paredes altas com vitrais, teto aberto mostrando o eclipse
    pygame.draw.rect(longe, (40, 32, 50), (0, 44, LARGURA, HORIZONTE - 42))
    for x in range(0, LARGURA, 88):
        pygame.draw.polygon(longe, (40, 32, 50), [(x, 46), (x + 44, 4), (x + 88, 46)])
    for k, x in enumerate(range(44, LARGURA, 88)):
        vitral(longe, rng, x, 30, 22, 60, quebrado=0.25 + 0.15 * ((k + variante) % 2))
        luzes.append([x, 60, 26, list(CORES_VITRAL[(k + variante) % 5]), 0.5])
    pontilhar(longe, (0, 44, LARGURA, HORIZONTE - 42), (60, 50, 72), 0.08, so_onde_tem=True)
    contornar(longe)
    for x in (24, 112, 240, 328):                                                               # colunas góticas
        retangulo(meio, (64, 54, 76), (x - 5, 10, 10, HORIZONTE - 8))
        pygame.draw.polygon(meio, (80, 68, 92), [(x - 8, 12), (x, 2), (x + 8, 12)])
    if variante == 1:                                                                           # bancos tombados
        for x in (70, 270):
            retangulo(meio, (60, 40, 30), (x, HORIZONTE - 8, 34, 4))
            retangulo(meio, (50, 34, 26), (x + 2, HORIZONTE - 14, 3, 8))
    if variante == 2:                                                                           # anjo de pedra sem cabeça
        retangulo(meio, (110, 104, 116), (170, HORIZONTE - 34, 12, 28))
        pygame.draw.polygon(meio, (110, 104, 116), [(170, HORIZONTE - 30), (150, HORIZONTE - 50), (166, HORIZONTE - 24)])
        pygame.draw.polygon(meio, (110, 104, 116), [(182, HORIZONTE - 30), (202, HORIZONTE - 50), (186, HORIZONTE - 24)])
    for x in (68, 284):                                                                         # velas roxas
        retangulo(meio, (200, 190, 170), (x, HORIZONTE - 18, 3, 10))
        pygame.draw.polygon(meio, (200, 140, 255), [(x - 1, HORIZONTE - 18), (x + 1, HORIZONTE - 24), (x + 3, HORIZONTE - 18)])
        luzes.append([x + 1, HORIZONTE - 21, 16, [200, 140, 255], 0.7])
    contornar(meio)
    degrade(chao, HORIZONTE, ALTURA, [(54, 44, 62), (36, 28, 44), (14, 10, 18)])
    for k in range(-10, 11):
        linha(chao, (30, 22, 36), (176 + k * 8, HORIZONTE), (176 + k * 34, ALTURA))
    for _ in range(18):                                                                         # cacos de vitral no chão
        x, y = rng.randrange(LARGURA), rng.randrange(HORIZONTE + 4, ALTURA - 2)
        pygame.draw.rect(chao, rng.choice(CORES_VITRAL), (x, y, 2, 1))
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["cinza", 30], ["poeira", 20]],
                                              "cor_nevoa": [70, 50, 90]}


def cena_altar_do_eclipse(rng, variante):
    """Sala do Bispo: altar sob uma rosácea gigante, com o sol negro no centro."""
    ceu, longe, meio, chao, frente = camada(), camada(), camada(), camada(), camada()
    degrade(ceu, 0, HORIZONTE + 4, [(10, 4, 16), (30, 14, 40), (60, 30, 70)])
    luzes = []
    pygame.draw.rect(longe, (44, 34, 54), (0, 0, LARGURA, HORIZONTE))
    cx, cy = 176, 50
    for anel, raio in enumerate((44, 34, 24)):                                                  # rosácea
        for k in range(16):
            a0, a1 = k / 16 * math.tau, (k + 1) / 16 * math.tau
            pontos = [(cx, cy)] + [(cx + int(math.cos(a0 + (a1 - a0) * t / 3) * raio), cy + int(math.sin(a0 + (a1 - a0) * t / 3) * raio))
                                   for t in range(4)]
            pygame.draw.polygon(longe, CORES_VITRAL[(k + anel) % 5], pontos)
        pygame.draw.circle(longe, (30, 24, 36), (cx, cy), raio, 1)
    sol_negro(longe, luzes, cx, cy, 13)
    for x in (60, 292):
        vitral(longe, rng, x, 26, 20, 64, quebrado=0.4)
    contornar(longe)
    pygame.draw.rect(meio, (80, 70, 90), (140, HORIZONTE - 22, 72, 22))                         # altar
    pygame.draw.rect(meio, (210, 170, 90), (136, HORIZONTE - 26, 80, 4))
    for x in (150, 202):
        retangulo(meio, (200, 190, 170), (x, HORIZONTE - 36, 3, 10))
        pygame.draw.polygon(meio, (255, 210, 140), [(x - 1, HORIZONTE - 36), (x + 1, HORIZONTE - 42), (x + 3, HORIZONTE - 36)])
        luzes.append([x + 1, HORIZONTE - 39, 18, [255, 210, 140], 0.8])
    for x in (20, 332):
        retangulo(meio, (64, 54, 76), (x - 7, 0, 14, HORIZONTE + 2))
    contornar(meio)
    degrade(chao, HORIZONTE, ALTURA, [(60, 48, 70), (40, 30, 50), (16, 10, 20)])
    for k in range(-10, 11):
        linha(chao, (34, 24, 40), (176 + k * 8, HORIZONTE), (176 + k * 34, ALTURA))
    pygame.draw.polygon(chao, (90, 40, 120), [(160, HORIZONTE), (192, HORIZONTE), (240, ALTURA), (112, ALTURA)])   # tapete
    return [ceu, longe, meio, chao, frente], {"luzes": luzes, "particulas": [["cinza", 24], ["brasa", 8]],
                                              "cor_nevoa": [90, 60, 110]}


CENAS_NOVAS = {
    "bosque_carmesim": (cena_bosque_carmesim, 3), "raizal": (cena_raizal, 1),
    "pantano_dos_afogados": (cena_pantano_dos_afogados, 3), "embarcadouro": (cena_embarcadouro, 1),
    "catacumbas_da_ordem_caida": (cena_catacumbas_da_ordem_caida, 3), "capela_profanada": (cena_capela_profanada, 1),
    "minas_de_brasa": (cena_minas_de_brasa, 3), "forja_antiga": (cena_forja_antiga, 1),
    "cidadela_congelada": (cena_cidadela_congelada, 3), "trono_de_gelo": (cena_trono_de_gelo, 1),
    "catedral_do_eclipse": (cena_catedral_do_eclipse, 3), "altar_do_eclipse": (cena_altar_do_eclipse, 1),
}
CEUS_NOVOS = {"bosque_carmesim": (ceu_de_dia, ceu_de_tarde), "pantano_dos_afogados": (ceu_de_dia, ceu_de_tarde)}
