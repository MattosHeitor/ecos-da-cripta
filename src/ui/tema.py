"""Paleta de cores e fontes da interface (no mesmo tom dos sprites).

Sombras puxando para roxo/azul, metais escuros e luz quente de vela.
"""

import os

import pygame

from caminhos import CAMINHOS

LARGURA, ALTURA = 1280, 720
PIXEL = 2                       # tamanho do "pixel grande" da interface

# ---------------- cores ----------------
FUNDO = (12, 9, 15)
PEDRA_ESCURA = (26, 21, 30)
PEDRA = (44, 37, 50)
PEDRA_CLARA = (74, 64, 80)
FERRO_ESCURO = (38, 36, 48)
FERRO = (78, 74, 90)
FERRO_CLARO = (128, 122, 140)
OURO_ESCURO = (120, 82, 36)
OURO = (206, 160, 82)
OURO_CLARO = (246, 214, 140)
SANGUE_ESCURO = (70, 14, 22)
SANGUE = (150, 30, 38)
SANGUE_CLARO = (214, 64, 58)
OSSO = (216, 206, 182)
VELA = (255, 196, 110)

TEXTO = (232, 222, 204)
TEXTO_FRACO = (150, 138, 132)
TEXTO_APAGADO = (92, 84, 90)
TEXTO_TITULO = (236, 196, 120)

VIDA = (178, 36, 44)
VIDA_ATRASO = (246, 214, 180)
VIDA_HEROI = (150, 34, 40)
ENERGIA = (88, 172, 224)
ENERGIA_CLARA = (176, 226, 255)
CURA = (110, 214, 110)
XP = (196, 150, 230)
VENENO = (150, 220, 80)
OURO_MOEDA = (240, 196, 80)

ESTILOS_DE_MOLDURA = {
    #            borda escura,  metal,        luz,          sombra,       fundo (com transparência)
    "ferro":   ((8, 6, 10), FERRO, FERRO_CLARO, FERRO_ESCURO, (20, 15, 24, 236)),
    "ouro":    ((10, 6, 4), OURO, OURO_CLARO, OURO_ESCURO, (28, 20, 18, 240)),
    "sangue":  ((10, 4, 6), SANGUE, SANGUE_CLARO, SANGUE_ESCURO, (26, 12, 16, 236)),
    "osso":    ((10, 8, 8), (168, 156, 132), OSSO, (96, 86, 72), (24, 20, 22, 236)),
    "pedra":   ((6, 4, 8), PEDRA_CLARA, (110, 98, 116), PEDRA, (16, 12, 20, 245)),
}

COR_RARIDADE = {
    "comum": (170, 165, 160),
    "incomum": (110, 196, 96),
    "raro": (96, 156, 236),
    "epico": (184, 98, 228),
    "lendario": (240, 176, 64),
    "amaldicoado": (206, 44, 70),
}

# ---------------- fontes ----------------
# M PLUS Rounded 1c: arredondada e fácil de ler (Bold nos textos, ExtraBold nos títulos).
# Ela é vetorial: desenha com suavização (SUAVE). Sem os arquivos, volta para a Pixelify Sans (pixel, sem suavizar).
PASTA_FONTES = CAMINHOS.asset("fontes")
CAMINHO_FONTE = os.path.join(PASTA_FONTES, "MPLUSRounded1c-Bold.ttf")
CAMINHO_FONTE_TITULO = os.path.join(PASTA_FONTES, "MPLUSRounded1c-ExtraBold.ttf")
CAMINHO_FONTE_PIXEL = os.path.join(PASTA_FONTES, "PixelifySans.ttf")
TAMANHO_TITULO = 22                     # daqui para cima usa o peso de título
ARREDONDADA = os.path.exists(CAMINHO_FONTE)
SUAVE = ARREDONDADA                     # suavizar as bordas das letras (fonte vetorial)
LIGADURAS = not ARREDONDADA             # só a Pixelify junta "fi"/"fl" num símbolo (ui.desenho separa)
_fontes = {}


def fonte(tamanho):
    """A fonte do jogo no tamanho pedido (em pixels)."""
    if tamanho not in _fontes:
        if ARREDONDADA:
            caminho = CAMINHO_FONTE_TITULO if tamanho >= TAMANHO_TITULO and os.path.exists(CAMINHO_FONTE_TITULO) \
                else CAMINHO_FONTE
            _fontes[tamanho] = pygame.font.Font(caminho, tamanho)
        elif os.path.exists(CAMINHO_FONTE_PIXEL):
            _fontes[tamanho] = pygame.font.Font(CAMINHO_FONTE_PIXEL, tamanho)
        else:
            _fontes[tamanho] = pygame.font.Font(None, int(tamanho * 1.4))
    return _fontes[tamanho]


# Tamanhos usados no jogo (a arredondada é mais alta e larga que a Pixelify no mesmo tamanho)
def mini():
    return fonte(13)


def pequena():
    return fonte(15 if ARREDONDADA else 16)


def normal():
    return fonte(18 if ARREDONDADA else 19)


def media():
    return fonte(22 if ARREDONDADA else 24)


def grande():
    return fonte(32 if ARREDONDADA else 34)


def titulo():
    return fonte(54 if ARREDONDADA else 58)
