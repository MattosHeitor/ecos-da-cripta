"""Música e efeitos sonoros.

    app.audio.tocar("golpe")          # efeito curto (assets/sons/efeitos/golpe.wav)
    app.audio.musica("floresta")      # música em loop (assets/sons/musica/floresta.ogg, .mp3 ou .wav)
    app.audio.musica("vitoria", repetir=False)    # vinheta que toca uma vez

As músicas e os efeitos são gerados por código (ferramentas/gerar_musicas.py e gerar_sons.py).

Arquivo que não existe é só ignorado (o jogo funciona em silêncio) e fica anotado em
`faltando`, para saber quais sons ainda precisam ser feitos. Sem placa de som, nada toca.
"""

import os
from collections import deque

import pygame

from caminhos import CAMINHOS

PASTA_EFEITOS = CAMINHOS.asset("sons", "efeitos")
PASTA_MUSICA = CAMINHOS.asset("sons", "musica")
EXTENSOES_EFEITO = (".wav", ".ogg")
EXTENSOES_MUSICA = (".ogg", ".mp3", ".wav")

# Músicas que o jogo pede (para listar o que falta). Vêm de ferramentas/gerar_musicas.py.
MUSICAS = ["titulo", "acampamento", "floresta", "minas", "catedral", "circo", "chefe", "vitoria", "derrota",
           "bosque", "pantano", "catacumbas", "brasa", "cidadela", "eclipse", "mercador", "primeiro_heroi",
           "reino_galerias", "reino_mercado", "reino_catedral", "reino_trono", "reino_rei", "reino_rainha"]


def procurar(pasta, nome, extensoes):
    for extensao in extensoes:
        caminho = os.path.join(pasta, nome + extensao)
        if os.path.exists(caminho):
            return caminho
    return None


class GerenciadorDeAudio:
    def __init__(self, opcoes):
        self.opcoes = opcoes
        self.ativo = self._iniciar_mixer()
        self.sons = {}                   # nome -> pygame.mixer.Sound (ou None se não existe)
        self.musica_atual = None
        self.faltando = set()
        self.historico = deque(maxlen=30)   # últimos efeitos pedidos (ajuda nos testes)

    @staticmethod
    def _iniciar_mixer():
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return True
        except pygame.error:
            return False

    def _som(self, nome):
        if nome not in self.sons:
            caminho = procurar(PASTA_EFEITOS, nome, EXTENSOES_EFEITO)
            self.sons[nome] = None
            if caminho is None:
                self.faltando.add(f"efeitos/{nome}")
            elif self.ativo:
                try:
                    self.sons[nome] = pygame.mixer.Sound(caminho)
                except pygame.error:
                    self.faltando.add(f"efeitos/{nome}")
        return self.sons[nome]

    def tocar(self, nome, volume=1.0):
        """Toca um efeito curto (respeitando o volume dos efeitos)."""
        self.historico.append(nome)
        som = self._som(nome)
        if som is None or self.opcoes.volume_efeitos <= 0:
            return
        som.set_volume(self.opcoes.volume_efeitos * volume)
        som.play()

    def musica(self, nome, repetir=True):
        """Troca a música de fundo (com fade). A mesma música já tocando continua sem recomeçar.

        repetir=False: vinheta que toca uma vez só (vitória, derrota)."""
        if nome == self.musica_atual:
            return
        self.musica_atual = nome
        caminho = procurar(PASTA_MUSICA, nome, EXTENSOES_MUSICA) if nome else None
        if nome and caminho is None:
            self.faltando.add(f"musica/{nome}")
        if not self.ativo:
            return
        try:
            pygame.mixer.music.fadeout(600)
            if caminho is not None:
                pygame.mixer.music.load(caminho)
                pygame.mixer.music.set_volume(self.opcoes.volume_musica)
                pygame.mixer.music.play(-1 if repetir else 0, fade_ms=900 if repetir else 200)
        except pygame.error:
            self.faltando.add(f"musica/{nome}")

    def atualizar_volumes(self):
        """Chamado quando o jogador mexe no volume."""
        if self.ativo:
            try:
                pygame.mixer.music.set_volume(self.opcoes.volume_musica)
            except pygame.error:
                pass
