"""A tela do jogo tem sempre 1280x720; a janela de verdade pode ter outro tamanho.

O App desenha tudo numa superfície de 1280x720 e a encaixa na janela (com faixas pretas).
Aqui fica a conversão entre os dois: posição do mouse na janela -> posição no jogo.
"""

import pygame

from ui import tema


class Encaixe:
    """Onde a imagem de 1280x720 fica dentro da janela: escala e deslocamento."""

    def __init__(self):
        self.escala = 1.0
        self.deslocamento = (0, 0)

    def ajustar(self, tamanho_da_janela):
        largura, altura = tamanho_da_janela
        self.escala = min(largura / tema.LARGURA, altura / tema.ALTURA)
        tamanho = self.tamanho()
        self.deslocamento = ((largura - tamanho[0]) // 2, (altura - tamanho[1]) // 2)

    def tamanho(self):
        return round(tema.LARGURA * self.escala), round(tema.ALTURA * self.escala)

    def para_o_jogo(self, posicao):
        """Posição na janela -> posição na tela de 1280x720."""
        x, y = posicao
        ox, oy = self.deslocamento
        return int((x - ox) / self.escala), int((y - oy) / self.escala)


ENCAIXE = Encaixe()


def posicao_do_mouse():
    """pygame.mouse.get_pos() já convertido para a tela do jogo."""
    return ENCAIXE.para_o_jogo(pygame.mouse.get_pos())


def converter_evento(e):
    """Eventos de mouse com a posição convertida (os outros voltam iguais)."""
    if e.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) or ENCAIXE.escala == 1 \
            and ENCAIXE.deslocamento == (0, 0):
        return e
    dados = dict(e.dict)
    dados["pos"] = ENCAIXE.para_o_jogo(e.pos)
    if "rel" in dados:
        dados["rel"] = (int(e.rel[0] / ENCAIXE.escala), int(e.rel[1] / ENCAIXE.escala))
    return pygame.event.Event(e.type, dados)
