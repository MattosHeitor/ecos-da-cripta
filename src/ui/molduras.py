"""Molduras do tema "quadro antigo": madeira escura entalhada, filetes e cantoneiras douradas, fundo de couro
ou de pergaminho escuro. Tudo desenhado por código, em "pixels de desenho" (ampliados 2x como o resto da
interface).

    moldura(largura, altura, "ferro")      -> Surface pronta (guardada por tamanho e estilo)
    placa(largura, altura)                 -> plaquinha dourada de título, com pontas

Estilos (os nomes antigos continuam valendo em todas as telas):
    ferro       painel/botão comum: madeira, couro, filete dourado
    pedra       secundário: madeira escura, couro escuro, filete apagado
    osso        cartão de informação: madeira, pergaminho escuro
    ouro        destaque (selecionado, foco, ação principal): filete dourado claro e fundo mais quente
    sangue      perigo: madeira avermelhada e couro vinho
    pressionado botão apertado (relevo invertido)
    desativado  botão que não responde (sem dourado, sem cor)
    espaco      espaço de item: fundo afundado com cantinhos dourados

A grossura da madeira acompanha o tamanho: botões pequenos ganham uma borda fina; painéis grandes, a
moldura larga com sulco, filete duplo e cantoneiras.
"""

import math

import pygame

# rampas (escuro -> claro)
MADEIRA = [(22, 12, 8), (44, 24, 14), (70, 40, 22), (98, 60, 32), (128, 84, 48)]
MADEIRA_ESCURA = [(14, 8, 6), (30, 17, 11), (48, 28, 17), (68, 42, 25), (90, 58, 34)]
MADEIRA_RUBRA = [(24, 8, 8), (50, 16, 14), (78, 26, 22), (106, 40, 30), (136, 58, 40)]
MADEIRA_CINZA = [(20, 18, 18), (34, 31, 30), (50, 46, 44), (66, 61, 58), (84, 78, 74)]
OURO = [(92, 58, 22), (150, 104, 44), (206, 160, 82), (246, 214, 140), (255, 240, 196)]
OURO_APAGADO = [(54, 40, 22), (86, 64, 36), (118, 90, 54), (150, 118, 76), (176, 146, 100)]
CONTORNO = (10, 6, 4)

# estilo -> (madeira, cor do fundo, ouro, filete duplo, fundo "afundado")
ESTILOS = {
    "ferro": (MADEIRA, (36, 25, 22), OURO, True),
    "pedra": (MADEIRA_ESCURA, (24, 17, 16), OURO_APAGADO, True),
    "osso": (MADEIRA, (62, 50, 38), OURO, True),
    "ouro": (MADEIRA, (76, 50, 28), [OURO[2], OURO[3], OURO[4], OURO[4], (255, 250, 230)], True),
    "sangue": (MADEIRA_RUBRA, (46, 18, 20), OURO, True),
    "pressionado": (MADEIRA_ESCURA, (30, 20, 16), OURO, False),
    "desativado": (MADEIRA_CINZA, (30, 27, 27), MADEIRA_CINZA, False),
    "espaco": (MADEIRA_ESCURA, (16, 11, 10), OURO, False),
}

_texturas = {}


def _ruido(x, y, semente=0):
    """Número de 0 a 1 que só depende de (x, y): textura estável, sem sorteio."""
    return ((x * 73856093) ^ (y * 19349663) ^ (semente * 83492791)) % 1000 / 1000.0


def _faixa_de_madeira(comprimento, grossura, rampa, semente):
    """Tira de madeira com veio ao longo do comprimento (horizontal). Guardada e reaproveitada."""
    chave = ("madeira", comprimento, grossura, id(rampa), semente)
    if chave not in _texturas:
        img = pygame.Surface((comprimento, grossura))
        for y in range(grossura):
            for x in range(comprimento):
                veio = math.sin(x * 0.33 + math.sin(y * 0.9 + semente) * 2.2 + _ruido(y, 0, semente) * 3) * 0.5 + 0.5
                indice = 1 + int(veio * 2.2 + _ruido(x, y, semente) * 0.8)
                img.set_at((x, y), rampa[min(4, max(1, indice))])
        _texturas[chave] = img
    return _texturas[chave]


def _ladrilho_de_fundo(cor, semente=3, lado=48):
    """Ladrilho de couro/pergaminho: manchas suaves em volta da cor (repete sem emenda visível)."""
    chave = ("fundo", cor, semente, lado)
    if chave not in _texturas:
        img = pygame.Surface((lado, lado))
        for y in range(lado):
            for x in range(lado):
                n = (_ruido(x // 2, y // 2, semente) * 0.6 + _ruido(x, y, semente + 1) * 0.4)
                f = 0.9 + n * 0.18
                img.set_at((x, y), tuple(max(0, min(255, int(c * f))) for c in cor))
        _texturas[chave] = img
    return _texturas[chave]


def _filete(img, rect, ouro):
    """Filete de 1 pixel: luz em cima/esquerda, sombra embaixo/direita."""
    x, y, w, h = rect
    if w < 2 or h < 2:
        return
    pygame.draw.line(img, ouro[3], (x, y), (x + w - 1, y))
    pygame.draw.line(img, ouro[3], (x, y), (x, y + h - 1))
    pygame.draw.line(img, ouro[1], (x, y + h - 1), (x + w - 1, y + h - 1))
    pygame.draw.line(img, ouro[1], (x + w - 1, y), (x + w - 1, y + h - 1))


def _cantoneira(img, cx, cy, sx, sy, tamanho, ouro):
    """Cantoneira dourada em L sobre a madeira, com rebite e pontas em losango (sx, sy = para onde o canto aponta)."""
    largura, altura = img.get_size()

    def px(x, y, cor):
        X, Y = cx + sx * x, cy + sy * y
        if 0 <= X < largura and 0 <= Y < altura:
            img.set_at((X, Y), cor)
    for i in range(tamanho):
        for j in range(3):
            cor = ouro[3] if j == 0 else (ouro[2] if j == 1 else ouro[1])
            px(i, j, cor)
            px(j, i, cor)
    for i in range(tamanho + 1):
        px(i, 3, CONTORNO)
        px(3, i, CONTORNO)
    for j in range(3):
        px(tamanho, j, CONTORNO)
        px(j, tamanho, CONTORNO)
    px(1, 1, ouro[4])                                       # rebite no canto
    px(2, 1, ouro[2])
    px(1, 2, ouro[2])
    for d in (-1, 0, 1):
        px(tamanho - 2 + abs(d), 1 + d, ouro[3])
        px(1 + d, tamanho - 2 + abs(d), ouro[3])


def _grossura(largura, altura):
    """Madeira fina nos botões, larga nos painéis grandes (em pixels de desenho)."""
    menor = min(largura, altura)
    if menor < 31:                                          # botões e linhas de lista (até 60 px na tela)
        return 1
    if menor < 60:
        return 3
    if menor < 200:
        return 4
    return 5


def moldura_pequena(largura, altura, estilo="ferro", semente=1):
    """A moldura em pixels de desenho (depois ampliada pela ui.desenho)."""
    madeira, fundo, ouro, duplo = ESTILOS.get(estilo, ESTILOS["ferro"])
    img = pygame.Surface((largura, altura), pygame.SRCALPHA)
    img.fill((0, 0, 0, 0))
    g = _grossura(largura, altura)
    interno = pygame.Rect(g + 1, g + 1, largura - 2 * g - 2, altura - 2 * g - 2)
    if interno.width <= 0 or interno.height <= 0:
        img.fill(CONTORNO)
        img.fill(madeira[2], (1, 1, max(0, largura - 2), max(0, altura - 2)))
        return img
    # fundo: couro/pergaminho ladrilhado, mais escuro perto da borda
    ladrilho = _ladrilho_de_fundo(fundo, semente)
    for y in range(interno.y, interno.bottom, ladrilho.get_height()):
        for x in range(interno.x, interno.right, ladrilho.get_width()):
            img.blit(ladrilho, (x, y), (0, 0, min(ladrilho.get_width(), interno.right - x),
                                        min(ladrilho.get_height(), interno.bottom - y)))
    sombra = pygame.Surface(interno.size, pygame.SRCALPHA)
    for k in range(min(6, interno.width // 4, interno.height // 4)):
        pygame.draw.rect(sombra, (0, 0, 0, 34 - k * 5), sombra.get_rect().inflate(-2 * k, -2 * k), 1)
    if estilo in ("pressionado", "espaco"):                 # afundado: sombra forte em cima
        pygame.draw.line(sombra, (0, 0, 0, 120), (0, 0), (interno.width, 0))
        pygame.draw.line(sombra, (0, 0, 0, 80), (0, 1), (interno.width, 1))
    img.blit(sombra, interno.topleft)
    # madeira: as 4 tiras, cantos em meia-esquadria (o contorno escuro separa)
    pygame.draw.rect(img, CONTORNO, img.get_rect(), 1)
    horizontal = _faixa_de_madeira(largura, g, madeira, semente)
    img.blit(horizontal, (0, 1), (0, 0, largura - 2, g))
    img.blit(pygame.transform.flip(horizontal, True, False), (1, altura - 1 - g), (0, 0, largura - 2, g))
    vertical = pygame.transform.rotate(_faixa_de_madeira(altura, g, madeira, semente + 5), 90)
    img.blit(vertical, (1, 1), (0, 0, g, altura - 2))
    img.blit(vertical, (largura - 1 - g, 1), (0, 0, g, altura - 2))
    pygame.draw.rect(img, CONTORNO, img.get_rect(), 1)
    if estilo != "pressionado":                             # relevo: luz em cima, sombra embaixo
        pygame.draw.line(img, madeira[4], (2, 1), (largura - 3, 1))
        pygame.draw.line(img, madeira[0], (2, altura - 2), (largura - 3, altura - 2))
    else:
        pygame.draw.line(img, madeira[0], (2, 1), (largura - 3, 1))
        pygame.draw.line(img, madeira[4], (2, altura - 2), (largura - 3, altura - 2))
    if g >= 4:                                              # sulco do entalhe no meio da madeira
        meio = g // 2
        pygame.draw.rect(img, madeira[0], (meio, meio, largura - 2 * meio, altura - 2 * meio), 1)
        pygame.draw.rect(img, madeira[4], (meio + 1, meio + 1, largura - 2 * meio - 2, altura - 2 * meio - 2), 1)
    # filete(s) dourado(s) por dentro da madeira
    pygame.draw.rect(img, CONTORNO, interno.inflate(2, 2), 1)
    if duplo and g >= 4:
        _filete(img, interno.inflate(4, 4), ouro)
        pygame.draw.rect(img, CONTORNO, interno.inflate(2, 2), 1)
    _filete(img, interno, ouro)
    if estilo == "ouro" and g < 4:                           # destaque: filete de 2 px (o de fora, sobre a madeira)
        _filete(img, interno.inflate(2, 2), ouro)
    if estilo == "espaco":                                  # cantinhos dourados do espaço de item
        for cx, cy, sx, sy in ((interno.x, interno.y, 1, 1), (interno.right - 1, interno.y, -1, 1),
                               (interno.x, interno.bottom - 1, 1, -1), (interno.right - 1, interno.bottom - 1, -1, -1)):
            for i in range(min(4, interno.width // 3)):
                img.set_at((cx + sx * i, cy), ouro[3])
                img.set_at((cx, cy + sy * i), ouro[3])
    if g >= 4:                                              # cantoneiras: quase só na madeira (não cobrem o conteúdo)
        tamanho = min(g + 4, largura // 4, altura // 4)
        for cx, cy, sx, sy in ((0, 0, 1, 1), (largura - 1, 0, -1, 1), (0, altura - 1, 1, -1),
                               (largura - 1, altura - 1, -1, -1)):
            _cantoneira(img, cx, cy, sx, sy, tamanho, ouro)
    elif estilo != "desativado" and min(largura, altura) >= 8:     # botões: um rebite dourado em cada canto
        for cx, cy in ((g + 1, g + 1), (largura - 2 - g, g + 1), (g + 1, altura - 2 - g), (largura - 2 - g, altura - 2 - g)):
            img.set_at((cx, cy), ouro[4] if estilo == "ouro" else ouro[2])
    return img


def borda_interna(largura, altura):
    """Quanto da moldura (em pixels da TELA, já ampliada) é madeira + filete: o conteúdo começa depois."""
    return (_grossura(largura // 2, altura // 2) + 2) * 2


def placa(largura, altura, cor_fundo=(58, 18, 20)):
    """Plaquinha dourada de título com pontas (em pixels de desenho)."""
    img = pygame.Surface((largura, altura), pygame.SRCALPHA)
    meio = altura // 2
    fora = [(0, meio), (4, 0), (largura - 5, 0), (largura - 1, meio), (largura - 5, altura - 1), (4, altura - 1)]
    dentro = [(2, meio), (5, 1), (largura - 6, 1), (largura - 3, meio), (largura - 6, altura - 2), (5, altura - 2)]
    pygame.draw.polygon(img, CONTORNO, fora)
    pygame.draw.polygon(img, cor_fundo, dentro)
    pygame.draw.polygon(img, OURO[2], dentro, 1)
    pygame.draw.line(img, OURO[3], (6, 2), (largura - 7, 2))
    pygame.draw.line(img, OURO[1], (6, altura - 3), (largura - 7, altura - 3))
    for x in (8, largura - 9):
        img.set_at((x, meio), OURO[4])
        img.set_at((x, meio - 1), OURO[2])
        img.set_at((x, meio + 1), OURO[2])
    return img
