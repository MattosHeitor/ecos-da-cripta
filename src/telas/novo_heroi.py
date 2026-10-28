"""Herói novo: uma classe secreta acabou de ser liberada (classes.json "requer"; ex.: o Médico da Peste, ao derrubar
a Rainha dos Ratos). Aparece no caminho para o acampamento (fluxo.ir_para_acampamento), uma vez por classe.

O herói sai da sombra (silhueta -> cores) sob um facho de luz, com o nome em ouro, o papel, a frase de anúncio e a
descrição. Qualquer tecla ou clique segue para 'depois' (o acampamento, ou o próximo herói a anunciar).
"""

import math

import pygame

from roguelike.classes import classe as buscar_classe
from telas.base import Tela
from telas.comum import Fundo
from telas.titulo_da_area import nome_em_ouro
from ui import tema
from ui.desenho import texto, losango
from ui.texto import CaixaTexto

PULAR_DEPOIS = 1.2            # dá tempo de ver o herói antes de um clique apressado
SAI_DA_SOMBRA = (0.6, 1.6)    # quando a silhueta começa e termina de ganhar cor
ESCALA = 3


class TelaNovoHeroi(Tela):
    def __init__(self, app, chave_classe, depois):
        super().__init__(app)
        self.classe = buscar_classe(chave_classe)
        self.sprite = self.classe.sprite_da_aparencia(self.classe.aparencia_padrao)
        self.depois = depois
        self.fundo = Fundo("acampamento", escurecer=190)
        self.nome = nome_em_ouro(self.classe.nome)
        self.saiu = False

    def musica(self):
        return "acampamento"

    def seguir(self):
        if not self.saiu:
            self.saiu = True
            self.depois()

    def evento(self, e):
        if self.tempo >= PULAR_DEPOIS and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.seguir()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def surgir(self, inicio, duracao=0.6):
        t = max(0.0, min(1.0, (self.tempo - inicio) / duracao))
        return t * t * (3 - 2 * t)

    def desenhar_heroi(self, tela, pe):
        """O facho de luz, a sombra no chão e o herói saindo da silhueta (as cores sobem por cima dela)."""
        sprites = self.app.sprites
        luz = pygame.Surface((360, 520), pygame.SRCALPHA)
        forca = self.surgir(0.2, 1.0)
        for k in range(12):                                              # o facho vem de cima, mais largo embaixo
            alfa = int((10 + k * 3) * forca)
            larg = 60 + k * 22
            pygame.draw.polygon(luz, (255, 222, 150, alfa), [(180 - 30, 0), (180 + 30, 0), (180 + larg // 2, 520),
                                                             (180 - larg // 2, 520)])
        tela.blit(luz, luz.get_rect(midbottom=(pe[0], pe[1] + 30)))
        mancha = pygame.Surface((200, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(mancha, (0, 0, 0, 140), mancha.get_rect())
        tela.blit(mancha, mancha.get_rect(center=pe))
        quadro = int(self.tempo * 5) % sprites.quadros_de(self.sprite, "parado")
        ax, ay = sprites.ancora(self.sprite, ESCALA)
        posicao = (pe[0] - ax, pe[1] - ay)
        tela.blit(sprites.quadro(self.sprite, "parado", quadro, ESCALA, False, "silhueta"), posicao)
        cor = self.surgir(*SAI_DA_SOMBRA)
        if cor > 0:
            imagem = sprites.quadro(self.sprite, "parado", quadro, ESCALA).copy()
            imagem.set_alpha(int(255 * cor))
            tela.blit(imagem, posicao)

    def desenhar(self, tela):
        self.fundo.desenhar(tela)
        self.desenhar_heroi(tela, (330, 600))
        x, largura = 560, 660                                            # a coluna de texto, à direita do herói
        centro = x + largura // 2
        alfa = int(255 * self.surgir(0.8))
        texto(tela, "UM HERÓI NOVO NO ACAMPAMENTO", tema.normal(), tema.OURO, (centro, 150), "center", alfa=alfa)
        entrada = self.surgir(1.1, 0.8)
        nome = self.nome.copy()
        nome.set_alpha(int(255 * entrada))
        if nome.get_width() > largura:
            nome = pygame.transform.smoothscale(nome, (largura, int(nome.get_height() * largura / nome.get_width())))
        tela.blit(nome, nome.get_rect(center=(centro, 220 + (1 - entrada) * 20)))
        risco = int(260 * self.surgir(1.5))
        if risco > 0:
            for lado in (-1, 1):
                pygame.draw.line(tela, tema.SANGUE, (centro + lado * 30, 278), (centro + lado * risco, 278), 2)
            losango(tela, (centro, 278), 6, tema.OURO)
        if self.surgir(1.7) > 0:
            camada = pygame.Surface((largura, 300), pygame.SRCALPHA)
            texto(camada, self.classe.papel.upper(), tema.pequena(), tema.SANGUE_CLARO, (largura // 2, 4), "midtop")
            y = CaixaTexto(pygame.Rect(0, 34, largura, 96), tema.media(), tema.TEXTO_TITULO, alinhamento="centro",
                           maximo_linhas=3).desenhar(camada, self.classe.anuncio)
            CaixaTexto(pygame.Rect(30, y + 16, largura - 60, 120), tema.normal(), tema.TEXTO, alinhamento="centro",
                       maximo_linhas=4).desenhar(camada, self.classe.descricao)
            camada.set_alpha(int(255 * self.surgir(1.7)))
            tela.blit(camada, (x, 300))
        if self.tempo > PULAR_DEPOIS:
            pulso = 120 + int(80 * math.sin(self.tempo * 3))
            texto(tela, "Ele já espera na Capitã · qualquer tecla para seguir", tema.mini(), (pulso, pulso, pulso),
                  (tema.LARGURA // 2, tema.ALTURA - 30), "center")
