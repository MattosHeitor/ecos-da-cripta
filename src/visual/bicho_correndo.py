"""Um bicho que atravessa a tela correndo ao fundo de tempos em tempos (ex.: o Rato Branco no mapa).

No meio do caminho ele para, olha para o grupo e segue. Usa a linha "correr" do sprite se existir
(senão, o "parado" deslizando). Vai entre o cenário e a interface: os painéis passam por cima dele.

    rato = BichoCorrendo(app.sprites, "rato_branco", chao_y=640)
    rato.atualizar(dt)
    rato.desenhar(tela)
"""

import random


class BichoCorrendo:
    VELOCIDADE = 300            # pixels por segundo
    QUADROS_POR_SEGUNDO = 12
    PAUSA_NO_MEIO = 0.9         # segundos parado, olhando
    ESPERA = (2.5, 5.0)         # segundos fora da tela entre uma corrida e outra

    def __init__(self, sprites, nome, chao_y, escala=2, largura_da_tela=1280, primeira_espera=0.4, semente=7):
        self.sprites = sprites
        self.nome = nome
        self.chao_y = chao_y
        self.escala = escala
        self.inicio, self.fim = -160, largura_da_tela + 160
        self.rng = random.Random(semente)
        self.espera = primeira_espera
        self.x = None               # None = fora da tela, esperando
        self.parada = None          # x onde ele vai parar nesta corrida
        self.parado_ha = 0.0
        self.tempo = 0.0

    def correr_a_partir_de(self, x, parar_em=None):
        """Começa uma corrida (as prévias usam para pôr o bicho num ponto certo da tela)."""
        self.x = x
        self.parada = parar_em if parar_em is not None else self.rng.uniform(0.35, 0.65) * self.fim
        self.parado_ha = 0.0

    def parado(self):
        return self.x is not None and self.parada is not None and self.x >= self.parada and \
            self.parado_ha < self.PAUSA_NO_MEIO

    def atualizar(self, dt):
        self.tempo += dt
        if self.x is None:
            self.espera -= dt
            if self.espera <= 0:
                self.correr_a_partir_de(self.inicio)
            return
        if self.parado():
            self.parado_ha += dt
            return
        self.x += self.VELOCIDADE * dt
        if self.x > self.fim:
            self.x = None
            self.espera = self.rng.uniform(*self.ESPERA)

    def desenhar(self, tela):
        if self.x is None:
            return
        anim = "parado" if self.parado() or not self.sprites.tem_animacao(self.nome, "correr") else "correr"
        velocidade = 5 if anim == "parado" else self.QUADROS_POR_SEGUNDO
        quadro = int(self.tempo * velocidade) % self.sprites.quadros_de(self.nome, anim)
        imagem = self.sprites.quadro(self.nome, anim, quadro, self.escala)
        ax, ay = self.sprites.ancora(self.nome, self.escala)
        tela.blit(imagem, (round(self.x - ax), round(self.chao_y - ay)))
