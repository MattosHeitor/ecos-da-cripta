"""Visual de um bando na arena (roguelike/bando.py): vários bichos do mesmo sprite, cada um no seu ritmo.

O VisualBando É UM VisualLutador (herança): muda só as medidas e o desenho. Quantos bichos aparecem segue
o contador do bando ("Ratos ×7"): quem cai faz a animação de morte e some aos poucos.
"""

import math

import pygame

from roguelike.dados import regras
from telas.combate.visual import VisualLutador
from visual.sprites_macabros import Animador

# Onde cada bicho fica em volta dos pés do bando: x em larguras do sprite, y em pixels. O 1º é o último a cair.
POSICOES = ((0.0, 6), (-0.45, -8), (0.42, -10), (-0.8, 4), (0.75, 2), (-0.2, -22), (0.25, 16), (-0.62, 18))


class AnimadoresDoBando:
    """Um Animador por bicho, usado como se fosse um só (tocar, atualizar, reviver, anim, indice, tempo)."""

    def __init__(self, sprites, nome, quantos):
        self.lista = [Animador(sprites, nome) for _ in range(quantos)]
        self.tempo = 0.0

    @property
    def tempo(self):
        return self.lista[0].tempo

    @tempo.setter
    def tempo(self, valor):
        for i, animador in enumerate(self.lista):           # cada um respira num ritmo
            animador.tempo = valor + i * 0.37

    @property
    def anim(self):
        return self.lista[0].anim

    @property
    def indice(self):
        return self.lista[0].indice

    def tocar(self, anim, depois="parado"):
        for animador in self.lista:
            animador.tocar(anim, depois)

    def reviver(self):
        for animador in self.lista:
            animador.reviver()

    def atualizar(self, dt):
        for animador in self.lista:
            animador.atualizar(dt)


class VisualBando(VisualLutador):
    def __init__(self, lutador, sprites, inimigo):
        super().__init__(lutador, sprites, inimigo)
        self.maximo = min(len(POSICOES), regras()["bandos"]["desenho_maximo"], lutador.quantos)
        agora = self.mostrados()
        self.alfas = [255.0 if i < agora else 0.0 for i in range(self.maximo)]
        self.caindo = [None if i < agora else -10.0 for i in range(self.maximo)]   # quando cada um caiu

    def usar_sprite(self, nome):
        super().usar_sprite(nome)
        self.animador = AnimadoresDoBando(self.sprites, nome, len(POSICOES))
        self.animador.tempo = (id(self.lutador) % 100) / 37

    # ---------------- quantos e onde ----------------
    def mostrados(self):
        """Quantos bichos desenhar agora (proporcional aos vivos do bando)."""
        vivos = self.lutador.vivos()
        if vivos <= 0:
            return 0
        return max(1, math.ceil(self.maximo * vivos / self.lutador.quantos))

    def visiveis(self):
        return [i for i in range(self.maximo) if self.alfas[i] > 0]

    def largura_de_um(self):
        return super().largura()

    def largura(self):
        """Largura do bando inteiro (não muda quando os bichos caem: a fileira não pula)."""
        xs = [dx for dx, _ in POSICOES[:self.maximo]]
        return round(self.largura_de_um() * (1 + max(xs) - min(xs)))

    def deslocamento_do(self, i):
        """Onde o bicho i fica em relação aos pés do bando (boiando, o bando se espalha menos para baixo e para cima)."""
        dx, dy = POSICOES[i]
        aperto = 1 - 0.6 * min(1.0, -self.boia / 20)
        return round(dx * self.largura_de_um()), round(dy * aperto)

    def caixa_de(self, i):
        return super().caixa().move(*self.deslocamento_do(i))

    def caixa(self):
        rects = [self.caixa_de(i) for i in self.visiveis()] or [super().caixa()]
        return rects[0].unionall(rects[1:])

    # ---------------- animação ----------------
    def atualizar(self, dt):
        super().atualizar(dt)
        agora = self.mostrados()
        for i in range(self.maximo):
            if i < agora:
                if self.caindo[i] is not None:                  # voltou (cura do bando)
                    self.caindo[i] = None
                    self.animador.lista[i].reviver()
                self.alfas[i] = min(255.0, self.alfas[i] + dt * 600)
                continue
            if self.caindo[i] is None:                          # este acabou de cair
                self.caindo[i] = self.tempo
                self.animador.lista[i].tocar("morte")
            if self.tempo - self.caindo[i] > 0.5:
                self.alfas[i] = max(0.0, self.alfas[i] - dt * 500)

    # ---------------- desenho ----------------
    def ordem(self):
        """Os de trás (y menor) primeiro."""
        return sorted(self.visiveis(), key=lambda i: POSICOES[i][1])

    def posicao_do_quadro(self, i):
        ax, ay = self.sprites.ancora(self.nome_sprite, self.escala, self.inimigo)
        dx, dy = self.deslocamento_do(i)
        return round(self.x + self.deslocamento_x() - ax + dx), round(self.y + self.deslocamento_y() - ay + dy)

    def desenhar_sombra(self, tela):
        if self.alfa < 40 or self.deslocamento_y() < 0:          # boiando: sem sombra no chão
            return
        largura = max(24, int(self.largura_de_um() * 0.45))
        for i in self.ordem():
            sombra = pygame.Surface((largura, max(6, largura // 5)), pygame.SRCALPHA)
            alfa = int(100 * min(self.alfa, self.alfas[i]) / 255)
            pygame.draw.ellipse(sombra, (0, 0, 0, alfa), sombra.get_rect())
            dx, dy = self.deslocamento_do(i)
            tela.blit(sombra, (round(self.x + self.deslocamento_x() + dx - largura / 2),
                               round(self.y + dy - sombra.get_height() / 2)))

    def desenhar(self, tela, destaque=None):
        if self.alfa <= 0:
            return
        if self.oculto and self.lutador.esta_vivo():
            self.desenhar_no_escuro(tela)
            return
        efeito = "branco" if self.tempo < self.piscar_ate else self.tinta
        for i in self.ordem():
            animador = self.animador.lista[i]
            imagem = self.sprites.quadro(self.nome_sprite, animador.anim, animador.indice, self.escala, self.inimigo, efeito)
            x, y = self.posicao_do_quadro(i)
            self.desenhar_quadro(tela, imagem, x, y, destaque, int(min(self.alfa, self.alfas[i])))

    def desenhar_no_escuro(self, tela):
        for i in self.ordem():
            animador = self.animador.lista[i]
            imagem = self.sprites.quadro(self.nome_sprite, animador.anim, animador.indice, self.escala, self.inimigo,
                                         "silhueta").copy()
            imagem.set_alpha(150)
            tela.blit(imagem, self.posicao_do_quadro(i))

    def desenhar_olhos(self, tela):
        """No breu, um par de olhinhos vermelhos por bicho (piscando cada um na sua hora)."""
        for i in self.visiveis():
            if math.sin(self.tempo * 1.7 + i * 1.3) < -0.85:
                continue
            caixa = self.caixa_de(i)
            x = round(caixa.left + caixa.width * (0.2 if self.inimigo else 0.8))
            y = round(caixa.top + caixa.height * 0.35)
            for dx in (-4, 2):
                tela.fill((110, 14, 20), (x + dx - 1, y - 1, 5, 5))
                tela.fill((240, 50, 44), (x + dx, y, 3, 3))
