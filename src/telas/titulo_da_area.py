"""Transição ao entrar numa fase: o cenário dela aparece do escuro com o ato, o nome e a frase de abertura.

Fecha sozinha depois de alguns segundos ou com qualquer tecla/clique e chama 'depois' (o mapa).
"""

import math

import pygame

from telas.base import Tela
from telas.comum import Fundo
from telas.titulo import logo
from ui import tema
from ui.desenho import texto, losango
from ui.texto import CaixaTexto

DURACAO = 4.2                 # segundos até seguir sozinha
ESCURO_INICIAL = 0.8          # fade do preto
PULAR_DEPOIS = 0.3            # ignora cliques acidentais logo ao abrir
TAMANHOS_DO_NOME = (64, 56, 48, 40)
LARGURA_MAXIMA = 1100


def nome_em_ouro(nome):
    """O nome da fase em letras douradas, na maior fonte que couber na largura."""
    for tamanho in TAMANHOS_DO_NOME:
        imagem = logo(nome, tamanho)
        if imagem.get_width() <= LARGURA_MAXIMA:
            return imagem
    return pygame.transform.smoothscale(imagem, (LARGURA_MAXIMA, int(imagem.get_height() * LARGURA_MAXIMA
                                                                       / imagem.get_width())))


class TelaTituloDaArea(Tela):
    def __init__(self, app, run, depois, retorno=False):
        super().__init__(app)
        self.run = run
        self.depois = depois
        self.regiao = run.regiao
        self.fundo = Fundo.da_run(run, escurecer=60)
        self.nome = nome_em_ouro(self.regiao.nome)
        self.retorno = retorno                  # voltando de uma região opcional (ex.: depois do Circo)
        self.saiu = False

    def musica(self):
        return self.regiao.musica

    def seguir(self):
        if not self.saiu:
            self.saiu = True
            self.depois()

    def evento(self, e):
        if self.tempo < PULAR_DEPOIS:
            return
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.seguir()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)
        if self.tempo >= DURACAO:
            self.seguir()

    def surgir(self, inicio, duracao=0.6):
        """0 -> 1 a partir de 'inicio' (suave)."""
        t = max(0.0, min(1.0, (self.tempo - inicio) / duracao))
        return t * t * (3 - 2 * t)

    def subtitulo(self):
        if self.retorno:
            return "De volta a"
        ato = self.run.nome_do_ato()
        return ato.upper() if ato else "PASSAGEM"

    def desenhar(self, tela):
        self.fundo.desenhar(tela)
        centro = tema.LARGURA // 2
        meio = tema.ALTURA // 2 - 40

        faixa = pygame.Surface((tema.LARGURA, 250), pygame.SRCALPHA)
        faixa.fill((0, 0, 0, int(150 * self.surgir(0.2))))
        tela.blit(faixa, (0, meio - 110))

        alfa = int(255 * self.surgir(0.4))
        texto(tela, self.subtitulo(), tema.normal(), tema.OURO, (centro, meio - 80), "center", alfa=alfa)

        entrada = self.surgir(0.7, 0.8)
        nome = self.nome.copy()
        nome.set_alpha(int(255 * entrada))
        tela.blit(nome, nome.get_rect(center=(centro, meio - 10 + (1 - entrada) * 20)))

        linha = self.surgir(1.1)
        largura = int(320 * linha)
        if largura > 0:
            for lado in (-1, 1):
                pygame.draw.line(tela, tema.SANGUE, (centro + lado * 30, meio + 44), (centro + lado * largura, meio + 44), 2)
            losango(tela, (centro, meio + 44), 6, tema.OURO)

        if self.surgir(1.3) > 0:
            frase = pygame.Surface((900, 64), pygame.SRCALPHA)
            CaixaTexto(frase.get_rect(), tema.media(), tema.TEXTO, alinhamento="centro", maximo_linhas=2).desenhar(
                frase, self.regiao.titulo)
            frase.set_alpha(int(255 * self.surgir(1.3)))
            tela.blit(frase, frase.get_rect(midtop=(centro, meio + 60)))

        if self.surgir(1.8) > 0:
            total = self.run.areas_da_regiao()
            hora = " · começa de dia" if self.regiao.ciclo and self.run.area == 1 else ""
            detalhe = f"Área {self.run.area} de {total}" if self.retorno else f"{total} áreas até o chefe{hora}"
            if getattr(self.run, "ameaca", 0):
                detalhe += f" · Ameaça {self.run.ameaca}"
            texto(tela, detalhe, tema.pequena(), tema.TEXTO_FRACO, (centro, meio + 134), "center",
                  alfa=int(255 * self.surgir(1.8)))

        if self.tempo > 1.5:
            pulso = 120 + int(80 * math.sin(self.tempo * 3))
            texto(tela, "qualquer tecla para seguir", tema.mini(), (pulso, pulso, pulso), (centro, tema.ALTURA - 30),
                  "center")

        if self.tempo < ESCURO_INICIAL:
            escuro = pygame.Surface(tela.get_size())
            escuro.fill((0, 0, 0))
            escuro.set_alpha(int(255 * (1 - self.tempo / ESCURO_INICIAL)))
            tela.blit(escuro, (0, 0))
