"""A Rainha dos Ratos na arena (roguelike/roda.py), refeita na etapa 5R3: a coroa-ninho e os ratos da vez.

    VisualRoda(VisualLutador)         a coroa no nó de caudas (a Rainha), no chão atrás dos ratos: desce do teto ao
                                      entrar; lá dentro, um par de olhos vermelhos por rato esperando a vez; com metade
                                      da roda caída a coroa tomba e o nó à mostra pulsa em vermelho (linha "exposto")
    VisualRatoDaRoda(VisualLutador)   um rato da roda, de lado como os outros inimigos. Só os dois da frente ficam do
                                      lado de fora, um em cada fileira, presos por um rabo comprido que sai da coroa;
                                      quando a roda gira, o que sai da frente corre e pula para dentro da coroa e o
                                      próximo pula de lá para o lugar vago (os outros esperam dentro dela)

A ordem da roda vem do nó (NoDeCaudas.frente): o 1º da frente fica na fileira da frente, o 2º na de trás.
"""

import math

import pygame

from telas.combate.visual import VisualLutador, suave

CENTRO = (1112, 436)             # o meio da coroa na arena (o anel do nó encosta no chão da fileira de trás)
TETO = (1008, 88)                # de onde ela desce (o nó pendurado no teto do Salão do Trono)
LUGARES = ((880, 558), (994, 502))   # os pés dos dois ratos da vez: fileira da frente e fileira de trás
BOCA = (-6, -20)                 # a boca da coroa (de onde eles pulam), a partir do meio dela
SAIDA_DO_RABO = (-46, 26)        # de onde os rabos saem do nó, a partir do meio da coroa
OLHOS = ((-30, -14), (-10, -10), (12, -13), (32, -9), (-20, -4), (22, -4))   # lugares dos olhos lá dentro
TEMPO_DA_DESCIDA = 1.4
COR_DO_RABO, CONTORNO = (186, 126, 124), (30, 12, 18)
CHAO_DA_LUZ = 540                # onde a luz da coroa bate no chão da luta


def mistura(a, b, t):
    return a + (b - a) * t


class VisualRoda(VisualLutador):
    na_roda = True
    no_ar = True                     # (a coroa fica em cima do nó: a água não a afunda)

    def __init__(self, lutador, sprites, inimigo):
        super().__init__(lutador, sprites, inimigo)
        self.ratos = []                      # VisualRatoDaRoda de cada rato (eles se registram)
        self.descida = 0.0                   # 0 = pendurada no teto, 1 = no lugar
        self.x, self.y = TETO

    def usar_sprite(self, nome):
        super().usar_sprite(nome)
        self.escala = 2

    def colocar(self, x, y, imediato=False):
        """A coroa não entra nas fileiras dos inimigos: fica sempre no CENTRO."""

    def atualizar(self, dt):
        super().atualizar(dt)
        self.descida = min(1.0, self.descida + dt / TEMPO_DA_DESCIDA)
        t = suave(self.descida)
        self.x, self.y = mistura(TETO[0], CENTRO[0], t), mistura(TETO[1], CENTRO[1], t)
        self.alvo_x, self.alvo_y = self.x, self.y

    def pronta(self):
        return self.descida >= 1.0

    def exposto(self):
        return self.lutador.esta_vivo() and not self.lutador.tem_status("no_fechado")

    def boca(self):
        return self.x + BOCA[0], self.y + BOCA[1]

    def saida_do_rabo(self):
        return self.x + SAIDA_DO_RABO[0], self.y + SAIDA_DO_RABO[1]

    # ---------------- medidas ----------------
    def imagem_atual(self):
        efeito = "branco" if self.tempo < self.piscar_ate else None
        anim, indice = self.animador.anim, self.animador.indice
        if anim == "parado" and self.exposto() and self.sprites.tem_animacao(self.nome_sprite, "exposto"):
            anim = "exposto"                  # a coroa tombou: o nó à mostra pulsa em vermelho
            indice = int(self.tempo * 6) % self.sprites.quadros_de(self.nome_sprite, "exposto")
        return self.sprites.quadro(self.nome_sprite, anim, indice, self.escala, False, efeito)

    def caixa(self):
        return self.imagem_atual().get_bounding_rect().move(*self.canto())

    def canto(self):
        imagem = self.imagem_atual()
        return round(self.x - imagem.get_width() / 2), round(self.y - imagem.get_height() / 2)

    def tem_barra(self):
        return False                          # a Rainha tem a barra grande no topo da tela

    def desenhar_sombra(self, tela):
        """A luz doente da coroa no chão (vermelho-arroxeada, pulsando) e a sombra embaixo dela."""
        if self.alfa < 40:
            return
        forca = self.alfa / 255 * min(1.0, self.descida)
        luz = pygame.Surface((420, 56))
        luz.fill((0, 0, 0))
        for k, (folga, intensidade) in enumerate(((0, 0.1), (50, 0.12), (110, 0.14))):
            rect = luz.get_rect().inflate(-folga * 2, -folga * 0.35)
            f = intensidade * forca * (1 + 0.25 * math.sin(self.tempo * 2 + k))
            pygame.draw.ellipse(luz, (int(150 * f * (k + 1)), int(36 * f * (k + 1)), int(90 * f * (k + 1))), rect)
        tela.blit(luz, (round(self.x - 230), CHAO_DA_LUZ - 28), special_flags=pygame.BLEND_RGB_ADD)

    # ---------------- desenho ----------------
    def desenhar(self, tela, destaque=None):
        if self.alfa <= 0:
            return
        imagem = self.imagem_atual()
        x, y = self.canto()
        if self.exposto():                    # o nó exposto: um contorno vermelho fraco pulsando (dá para acertar)
            contorno = pygame.mask.from_surface(imagem).to_surface(setcolor=(230, 60, 50, 255), unsetcolor=(0, 0, 0, 0))
            contorno.set_alpha(70 + int(60 * math.sin(self.tempo * 6)))
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                tela.blit(contorno, (x + dx, y + dy))
        self.desenhar_quadro(tela, imagem, x, y, destaque, self.alfa)
        if self.lutador.esta_vivo() and not self.exposto():
            self.desenhar_olhos_de_dentro(tela)

    def desenhar_olhos_de_dentro(self, tela):
        """Um par de olhos vermelhos lá no escuro da coroa para cada rato esperando a vez (piscam de vez em quando)."""
        dentro = [r for r in self.ratos if r.dentro()]
        for k, rato in enumerate(dentro[:len(OLHOS)]):
            if math.sin(self.tempo * 1.3 + rato.vaga * 2.1) < -0.92:
                continue                      # piscou
            dx, dy = OLHOS[k]
            x, y = round(self.x + dx), round(self.y + dy)
            for olho in (-5, 5):
                tela.fill((110, 12, 20), (x + olho - 3, y - 2, 6, 5))
                tela.fill((255, 56, 44), (x + olho - 2, y - 1, 4, 3))
                tela.fill((255, 200, 180), (x + olho - 2, y - 1, 1, 1))


class VisualRatoDaRoda(VisualLutador):
    """Um rato da roda: dentro da coroa (não aparece), saindo/entrando (uma corrida com pulo em arco entre a boca da
    coroa e o lugar dele) ou do lado de fora, como qualquer inimigo, preso pelo rabo."""

    na_roda = True                   # (fora das fileiras: o lugar vem da roda)

    def __init__(self, lutador, sprites, inimigo, roda):
        self.roda = roda                      # o VisualRoda da coroa
        self.lugar = None                     # 0 = fileira da frente, 1 = de trás, None = dentro da coroa
        self.viagem = None                    # pulando para fora, para dentro ou trocando de fileira
        self.pulo = 0.0
        super().__init__(lutador, sprites, inimigo)
        self.vaga = len(roda.ratos)
        roda.ratos.append(self)
        self.x, self.y = roda.boca()
        self.alfa = 0

    @property
    def no_ar(self):
        return self.viagem is not None or self.lugar is None

    def colocar(self, x, y, imediato=False):
        """Fica onde a roda manda (atualizar)."""

    def atras(self):
        return self.lutador.tem_status("atras_da_roda")

    def dentro(self):
        return self.lutador.esta_vivo() and self.lugar is None and self.viagem is None and self.roda.pronta()

    def lugar_desejado(self):
        """0 ou 1 para os dois da vez (NoDeCaudas.frente), None para quem espera dentro da coroa."""
        no = self.lutador.no
        vivos = no.ratos_vivos()
        if not self.roda.pronta() or self.lutador not in vivos:
            return None
        relativo = (vivos.index(self.lutador) - no.giro) % len(vivos)
        return relativo if relativo < 2 else None

    def atualizar(self, dt):
        super().atualizar(dt)
        if not self.lutador.esta_vivo():
            self.viagem = None
            self.pulo = 0.0
            return                            # caído: fica onde está (a morte e o sumiço são os de sempre)
        desejado = self.lugar_desejado()
        if self.viagem is None and desejado != self.lugar and self.roda.pronta():
            self.comecar_viagem(desejado)
        if self.viagem is not None:
            self.andar(dt)
        elif self.lugar is not None:
            self.alvo_x, self.alvo_y = LUGARES[self.lugar]
            self.alfa = 255
        else:
            self.x, self.y = self.roda.boca()
            self.alvo_x, self.alvo_y = self.x, self.y
            self.alfa = 0

    def comecar_viagem(self, desejado):
        de = (self.x, self.y) if self.lugar is not None else self.roda.boca()
        para = LUGARES[desejado] if desejado is not None else self.roda.boca()
        tipo = "sai" if self.lugar is None else ("entra" if desejado is None else "troca")
        espera = 0.3 * desejado if tipo == "sai" and desejado else 0.0       # o 2º espera o 1º sair da coroa
        self.viagem = {"tipo": tipo, "de": de, "para": para, "t": -espera, "duracao": 0.5 if tipo == "troca" else 0.8}
        self.lugar = desejado

    def andar(self, dt):
        """Corre com um pulo em arco; sai da coroa aparecendo e entra nela sumindo."""
        v = self.viagem
        v["t"] += dt
        t = max(0.0, min(1.0, v["t"] / v["duracao"]))
        (x0, y0), (x1, y1) = v["de"], v["para"]
        self.x, self.y = mistura(x0, x1, t), mistura(y0, y1, t)
        self.alvo_x, self.alvo_y = self.x, self.y
        self.pulo = math.sin(t * math.pi) * (24 if v["tipo"] == "troca" else 80)
        if v["tipo"] == "sai":
            self.alfa = 0 if v["t"] < 0 else int(255 * min(1.0, t * 5))
        elif v["tipo"] == "entra":
            self.alfa = int(255 * min(1.0, (1 - t) * 5))
        else:
            self.alfa = 255
        if v["t"] >= v["duracao"]:
            self.viagem, self.pulo = None, 0.0
            if self.lugar is None:
                self.alfa = 0

    def deslocamento_y(self):
        return super().deslocamento_y() - self.pulo

    def tem_barra(self):
        return super().tem_barra() and self.lugar is not None and self.viagem is None and not self.atras()

    def some_de_vez(self):
        return self.alfa <= 0 and not self.lutador.esta_vivo() and self.morto_desde is not None

    # ---------------- o rabo ----------------
    def ponta_do_rabo(self):
        """Onde o toco do rabo dele termina, na tela (o catálogo diz "rabo"; virado para a esquerda, o rabo fica à
        direita)."""
        dx, dy = self.sprites.meta(self.nome_sprite).get("rabo", (-30, -8))
        espelhado = self.espelhado()
        return (self.x + self.deslocamento_x() + (-dx if espelhado else dx) * self.escala,
                self.y + self.deslocamento_y() + dy * self.escala)

    def espelhado(self):
        if self.viagem is not None:
            return self.viagem["para"][0] < self.viagem["de"][0]          # virado para onde corre
        return self.inimigo

    def desenhar_rabo(self, tela):
        """O rabo da coroa até ele: uma corda grossa de carne rosada com anéis, pendendo e balançando; em pixels de
        2x2 (como os sprites)."""
        inicio = self.roda.saida_do_rabo()
        fim = self.ponta_do_rabo()
        meio = ((inicio[0] + fim[0]) / 2 + math.sin(self.roda.tempo * 2.6 + self.vaga) * 5,
                max(inicio[1], fim[1]) + 16 + math.cos(self.roda.tempo * 2.2 + self.vaga) * 4)
        pontos = []
        for k in range(17):
            t = k / 16
            x = (1 - t) ** 2 * inicio[0] + 2 * (1 - t) * t * meio[0] + t * t * fim[0]
            y = (1 - t) ** 2 * inicio[1] + 2 * (1 - t) * t * meio[1] + t * t * fim[1]
            pontos.append((x, y, 5.0 - 1.6 * t))
        x0 = int(min(p[0] for p in pontos) - 8) // 2 * 2
        y0 = int(min(p[1] for p in pontos) - 8) // 2 * 2
        largura = int(max(p[0] for p in pontos) + 8 - x0) // 2 + 1
        altura = int(max(p[1] for p in pontos) + 8 - y0) // 2 + 1
        pequena = pygame.Surface((largura, altura), pygame.SRCALPHA)
        claro = tuple(min(255, c + 34) for c in COR_DO_RABO)
        escuro = tuple(int(c * 0.72) for c in COR_DO_RABO)
        local = [((x - x0) / 2, (y - y0) / 2, r / 2 + 0.6) for x, y, r in pontos]
        for x, y, r in local:
            pygame.draw.circle(pequena, CONTORNO, (round(x), round(y)), round(r + 1))
        for k, (x, y, r) in enumerate(local):
            pygame.draw.circle(pequena, escuro if k % 3 == 0 else COR_DO_RABO, (round(x), round(y)), round(r))
            if k % 2 == 0:
                pequena.set_at((round(x), round(y - r * 0.5)), claro)
        grande = pygame.transform.scale(pequena, (largura * 2, altura * 2))
        grande.set_alpha(self.alfa)
        tela.blit(grande, (x0, y0))

    def desenhar_sombra(self, tela):
        if self.viagem is None and self.lugar is not None:
            super().desenhar_sombra(tela)

    def desenhar(self, tela, destaque=None):
        if self.alfa <= 0:
            return
        if self.lutador.esta_vivo() or self.morto_desde is not None:
            self.desenhar_rabo(tela)
        if self.viagem is None:
            super().desenhar(tela, destaque)
            return
        quadros = self.sprites.quadros_de(self.nome_sprite, "correr")       # correndo e pulando
        espelhar = self.espelhado()
        imagem = self.sprites.quadro(self.nome_sprite, "correr", int(self.tempo * 12) % quadros, self.escala, espelhar)
        ax, ay = self.sprites.ancora(self.nome_sprite, self.escala, espelhar)
        self.desenhar_quadro(tela, imagem, round(self.x - ax), round(self.y - self.pulo - ay), None, self.alfa)
