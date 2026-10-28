"""A proclamação do Édito Real (etapa 5R2): quando o Rei dos Ratos ergue o cetro, a lei da rodada aparece grande no
meio da tela, em letras vermelhas de contorno dourado ("ÉDITO REAL" em ouro em cima, a lei no meio e a explicação
embaixo), numa faixa escura com filetes de ouro. Ela entra crescendo com um clarão, um brilho passa pelas letras, e
no fim ela encolhe e voa até o pergaminho do canto (que só aparece quando ela chega).
"""

import pygame

from ui import tema
from ui.desenho import anotar

VERMELHO_CLARO, VERMELHO_ESCURO = (240, 70, 60), (140, 12, 24)
OURO, OURO_ESCURO = (238, 190, 92), (110, 70, 24)
SOMBRA = (18, 4, 8)
CENTRO_Y = 228


def letreiro(conteudo, fonte, topo, baixo, borda, grossura=2):
    """Texto com degradê de cima para baixo, contorno grosso de outra cor e sombra embaixo."""
    branco = fonte.render(conteudo, True, (255, 255, 255))
    largura, altura = branco.get_size()
    degrade = pygame.Surface((largura, altura), pygame.SRCALPHA)
    for y in range(altura):
        t = y / max(1, altura - 1)
        degrade.fill(tuple(int(a + (b - a) * t) for a, b in zip(topo, baixo)) + (255,), (0, y, largura, 1))
    pintado = branco.copy()
    pintado.blit(degrade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    contorno = fonte.render(conteudo, True, borda)
    sombra = fonte.render(conteudo, True, SOMBRA)
    g = grossura
    sup = pygame.Surface((largura + 2 * g + 4, altura + 2 * g + 5), pygame.SRCALPHA)
    for dx in range(-g, g + 1):
        for dy in range(-g, g + 1):
            sup.blit(sombra, (g + dx + 3, g + dy + 4))
    for dx in range(-g, g + 1):
        for dy in range(-g, g + 1):
            if dx or dy:
                sup.blit(contorno, (g + dx, g + dy))
    sup.blit(pintado, (g, g))
    return sup


class ProclamacaoDoEdito:
    ENTRA, FICA, VOA = 0.3, 1.9, 0.5

    def __init__(self, lei, explicacao, inicio, destino):
        """lei: o nome do édito ("Proibido Curar"); explicacao: a frase da lei; destino: o centro do pergaminho."""
        self.inicio = inicio
        self.destino = destino
        self.titulo = letreiro("ÉDITO REAL", tema.fonte(24), (255, 236, 170), OURO, SOMBRA, 2)
        self.lei = letreiro(lei.upper(), tema.fonte(50), VERMELHO_CLARO, VERMELHO_ESCURO, OURO, 3)
        self.brilho = letreiro(lei.upper(), tema.fonte(50), (255, 244, 210), (255, 200, 120), OURO, 3)
        self.explicacao = letreiro(explicacao, tema.fonte(20), (236, 220, 180), (200, 170, 120), SOMBRA, 1) \
            if explicacao else None

    @property
    def duracao(self):
        return self.ENTRA + self.FICA + self.VOA

    def ativa(self, agora):
        return agora - self.inicio < self.duracao

    def chegou(self, agora):
        """Já chegou ao pergaminho (o pergaminho pode aparecer)."""
        return agora - self.inicio >= self.ENTRA + self.FICA + self.VOA * 0.8

    def montar(self, largura):
        """A placa inteira (faixa, filetes, título, lei e explicação) numa superfície só (montada uma vez)."""
        if getattr(self, "_placa", None) is None or self._placa.get_width() != largura:
            self._placa = self._montar(largura)
        return self._placa.copy()

    def _montar(self, largura):
        altura = 150
        meio = largura // 2
        placa = pygame.Surface((largura, altura), pygame.SRCALPHA)
        for y in range(0, altura, 2):                                   # a faixa escura: forte no meio, some nas pontas
            forca_y = min(1.0, (1 - abs(y - altura / 2) / (altura / 2)) * 1.6)
            for x in range(0, largura, 16):
                forca_x = max(0.0, 1 - (abs(x + 8 - meio) / 470) ** 2)
                placa.fill((10, 2, 6, int(175 * forca_y * forca_x)), (x, y, 16, 2))
        for y in (16, altura - 18):                                     # filetes de ouro com losangos nas pontas
            pygame.draw.line(placa, OURO_ESCURO, (meio - 330, y + 1), (meio + 330, y + 1), 3)
            pygame.draw.line(placa, OURO, (meio - 330, y), (meio + 330, y), 2)
            for x in (meio - 336, meio + 336, meio):
                pygame.draw.polygon(placa, OURO, [(x - 6, y), (x, y - 6), (x + 6, y), (x, y + 6)])
                pygame.draw.polygon(placa, VERMELHO_ESCURO, [(x - 3, y), (x, y - 3), (x + 3, y), (x, y + 3)])
        placa.blit(self.titulo, self.titulo.get_rect(midtop=(meio, 22)))
        placa.blit(self.lei, self.lei.get_rect(center=(meio, 76)))
        if self.explicacao is not None:
            placa.blit(self.explicacao, self.explicacao.get_rect(midtop=(meio, 104)))
        return placa

    def desenhar(self, tela, agora):
        passado = agora - self.inicio
        if passado < 0 or passado >= self.duracao:
            return
        placa = self.montar(tela.get_width())
        if self.ENTRA <= passado < self.ENTRA + self.FICA:              # o brilho passando pelas letras
            t = (passado - self.ENTRA) / (self.FICA * 0.6)
            if t < 1:
                rect = self.lei.get_rect(center=(placa.get_width() // 2, 76))
                faixa = pygame.Rect(rect.x + int((rect.width + 80) * t) - 60, rect.y, 34, rect.height)
                placa.set_clip(faixa)
                placa.blit(self.brilho, rect)
                placa.set_clip(None)
        centro = (tela.get_width() // 2, CENTRO_Y)
        if passado < self.ENTRA:                                        # entra crescendo de longe, com um clarão
            t = passado / self.ENTRA
            escala, alfa = 1.35 - 0.35 * t, int(255 * t)
        elif passado < self.ENTRA + self.FICA:
            escala, alfa = 1.0, 255
        else:                                                           # encolhe e voa até o pergaminho
            t = (passado - self.ENTRA - self.FICA) / self.VOA
            t = t * t * (3 - 2 * t)
            escala, alfa = 1.0 - 0.75 * t, int(255 * (1 - t * 0.7))
            centro = (centro[0] + (self.destino[0] - centro[0]) * t, centro[1] + (self.destino[1] - centro[1]) * t)
        if escala != 1.0:
            placa = pygame.transform.smoothscale(placa, (max(1, int(placa.get_width() * escala)),
                                                         max(1, int(placa.get_height() * escala))))
        placa.set_alpha(alfa)
        rect = placa.get_rect(center=(round(centro[0]), round(centro[1])))
        anotar("modal", rect, tela)                                     # (a placa fica por cima de tudo)
        tela.blit(placa, rect)
        if passado < self.ENTRA * 1.5:                                  # o clarão dourado da entrada
            clarao = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            clarao.fill((255, 210, 120, int(70 * (1 - passado / (self.ENTRA * 1.5)))))
            tela.blit(clarao, (0, 0))
