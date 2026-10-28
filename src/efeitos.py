"""Efeitos visuais da batalha em "pixels grandes" (combinam com a pixel art).

- partículas são quadradinhos de 4 x 4 (ou 8 x 8 quando estão grandes);
- brilhos, ondas e cristais são desenhados em 1/4 do tamanho e
  ampliados 4 vezes sem suavizar (bordas em degraus);
- os projéteis (bola de fogo, flecha, lança de gelo/osso, teia, orbe) são sprites de
  assets/efeitos (pixel art já pronta; se faltar o PNG, o projétil vira um brilho).
"""

import json
import math
import os
import random

import pygame

from caminhos import CAMINHOS

# Paletas de cores usadas pelos efeitos (poucas cores, como na pixel art)
FOGO = [(255, 214, 96), (242, 140, 40), (206, 66, 54), (122, 26, 34)]
GELO = [(216, 244, 255), (140, 208, 240), (74, 140, 192)]
RAIO = [(255, 255, 230), (255, 230, 110), (232, 178, 58)]
ROXO = [(210, 170, 255), (150, 100, 200), (98, 58, 150)]
SANGUE = [(224, 72, 58), (184, 40, 43), (122, 26, 34)]
CURA = [(180, 255, 170), (110, 220, 110), (60, 160, 80)]
PEDRA = [(146, 140, 154), (98, 92, 108), (204, 200, 210)]
VENENO = [(190, 255, 130), (150, 242, 80), (74, 140, 50)]
LUZ = [(255, 250, 220), (244, 210, 122), (232, 178, 58)]
MADEIRA = [(160, 106, 58), (122, 74, 42)]

PIXEL = 4
PASTA_EFEITOS = CAMINHOS.asset("efeitos")


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def na_grade(valor):
    """Arredonda para a grade de 4 pixels."""
    return int(valor) // PIXEL * PIXEL


def ampliar(imagem, vezes=PIXEL):
    largura, altura = imagem.get_size()
    return pygame.transform.scale(imagem, (largura * vezes, altura * vezes))


def quadradinho(tela, cor, x, y, tamanho=PIXEL):
    """Um "pixel grande" alinhado na grade."""
    tela.fill(cor, (na_grade(x), na_grade(y), tamanho, tamanho))


def linha_pixelada(tela, cor, inicio, fim, grossura=PIXEL):
    """Linha feita de quadradinhos, de 4 em 4 pixels."""
    passos = max(1, int(max(abs(fim[0] - inicio[0]), abs(fim[1] - inicio[1])) / PIXEL))
    for i in range(passos + 1):
        x = inicio[0] + (fim[0] - inicio[0]) * i / passos
        y = inicio[1] + (fim[1] - inicio[1]) * i / passos
        tela.fill(cor, (na_grade(x - grossura / 2), na_grade(y - grossura / 2), grossura, grossura))


_cache_brilhos = {}


def guardar(chave, criar):
    """Guarda imagens prontas (brilhos, anéis) para não refazer a cada quadro."""
    if chave not in _cache_brilhos:
        if len(_cache_brilhos) > 400:
            _cache_brilhos.clear()
        _cache_brilhos[chave] = criar()
    return _cache_brilhos[chave]


def desenhar_brilho(tela, cor, centro, raio, transparencia):
    """Círculo de luz semitransparente com borda em degraus de 4 pixels."""
    raio_pequeno = int(raio) // PIXEL
    transparencia = int(min(255, transparencia)) // 16 * 16
    if raio_pequeno <= 0 or transparencia <= 0:
        return

    def criar():
        pequena = pygame.Surface((raio_pequeno * 2 + 1, raio_pequeno * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(pequena, (*cor[:3], transparencia), (raio_pequeno, raio_pequeno), raio_pequeno)
        return ampliar(pequena)

    imagem = guardar(("brilho", tuple(cor[:3]), raio_pequeno, transparencia), criar)
    tela.blit(imagem, (na_grade(centro[0]) - raio_pequeno * PIXEL, na_grade(centro[1]) - raio_pequeno * PIXEL))


def brilho_suave(tela, cor, centro, raio, intensidade):
    """Brilho que vai sumindo nas bordas: 4 círculos em degraus, cada um mais forte no meio."""
    raio_pequeno = int(raio) // PIXEL
    intensidade = int(max(0, min(255, intensidade))) // 16 * 16
    if raio_pequeno <= 0 or intensidade <= 0:
        return

    def criar():
        pequena = pygame.Surface((raio_pequeno * 2 + 1, raio_pequeno * 2 + 1), pygame.SRCALPHA)
        for i in range(4):
            r = int(raio_pequeno * (1 - i / 4))
            camada = pygame.Surface(pequena.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(camada, (*cor[:3], intensidade // 4), (raio_pequeno, raio_pequeno), r)
            pequena.blit(camada, (0, 0))
        return ampliar(pequena)

    imagem = guardar(("suave", tuple(cor[:3]), raio_pequeno, intensidade), criar)
    tela.blit(imagem, (na_grade(centro[0]) - raio_pequeno * PIXEL, na_grade(centro[1]) - raio_pequeno * PIXEL))


def anel_pixelado(tela, cor, centro, raio_x, raio_y, grossura=1):
    """Elipse (só o contorno) com traço de 4 pixels."""
    rx, ry = max(1, int(raio_x) // PIXEL), max(1, int(raio_y) // PIXEL)

    def criar():
        pequena = pygame.Surface((rx * 2 + 1, ry * 2 + 1), pygame.SRCALPHA)
        pygame.draw.ellipse(pequena, cor, (0, 0, rx * 2 + 1, ry * 2 + 1), min(grossura, rx, ry))
        return ampliar(pequena)

    imagem = guardar(("anel", tuple(cor[:3]), rx, ry, grossura), criar)
    tela.blit(imagem, (na_grade(centro[0]) - rx * PIXEL, na_grade(centro[1]) - ry * PIXEL))


def girar(x, y, angulo):
    """Gira o ponto (x, y) em volta de (0, 0)."""
    return (
        x * math.cos(angulo) - y * math.sin(angulo),
        x * math.sin(angulo) + y * math.cos(angulo),
    )


# ------------------------------------------------------------
# Sprites dos projéteis
# ------------------------------------------------------------

# Cada PNG de assets/efeitos tem a linha de VOO (loop) e a de IMPACTO (uma vez); efeitos.json diz
# o tamanho dos quadros e o "centro" (o ponto que fica na posição do projétil). Gerados por
# ferramentas/sprites_macabros/gerar_efeitos.py. Orbe e lança são brancos: a cor do golpe os pinta.
ESCALA_PROJETIL = 2                   # a mesma dos personagens no combate
QUADROS_POR_SEGUNDO = 16

_meta_projeteis = None
_quadros_projeteis = {}


def meta_dos_projeteis():
    global _meta_projeteis
    if _meta_projeteis is None:
        caminho = os.path.join(PASTA_EFEITOS, "efeitos.json")
        _meta_projeteis = {}
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as arquivo:
                _meta_projeteis = json.load(arquivo)
    return _meta_projeteis


def quadros_do_projetil(nome, linha, cor=None, escala=ESCALA_PROJETIL, espelhar=False):
    """([quadros já ampliados, pintados e virados], centro) da linha "voo" ou "impacto". None se faltar o PNG."""
    chave = (nome, linha, cor, escala, espelhar)
    if chave not in _quadros_projeteis:
        meta = meta_dos_projeteis().get(nome)
        caminho = os.path.join(PASTA_EFEITOS, nome + ".png")
        if meta is None or not os.path.exists(caminho):
            _quadros_projeteis[chave] = None
            return None
        folha = pygame.image.load(caminho)
        if pygame.display.get_surface() is not None:
            folha = folha.convert_alpha()
        dados = meta[linha]
        w, h = dados["celula"]
        quadros = []
        for i in range(dados["quadros"]):
            quadro = folha.subsurface((i * w, dados["y"], w, h)).copy()
            if cor is not None and meta.get("tingir"):
                quadro.fill((*cor[:3], 255), special_flags=pygame.BLEND_RGBA_MULT)
            quadro = ampliar(quadro, escala)
            if espelhar:
                quadro = pygame.transform.flip(quadro, True, False)
            quadros.append(quadro)
        cx, cy = dados["centro"]
        if espelhar:
            cx = w - cx
        _quadros_projeteis[chave] = (quadros, (cx * escala, cy * escala))
    return _quadros_projeteis[chave]


# ============================================================
# PARTÍCULA
# ============================================================

class Particula:
    """Quadradinho colorido que se move e diminui até sumir."""

    def __init__(self, x, y, vx, vy, cor, duracao, tamanho, gravidade=0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.cor = cor
        self.duracao = duracao
        self.tamanho = tamanho
        self.gravidade = gravidade
        self.tempo = 0

    def atualizar(self, dt):
        self.tempo += dt
        self.vy += self.gravidade * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def viva(self):
        return self.tempo < self.duracao

    def desenhar(self, tela):
        resto = 1 - self.tempo / self.duracao
        # Grande no começo (8 x 8), pequeno no fim (4 x 4)
        lado = PIXEL * 2 if self.tamanho * resto > 4 else PIXEL
        quadradinho(tela, self.cor, self.x, self.y, lado)


def criar_particulas(x, y, cores, quantidade, velocidade, duracao, tamanho, gravidade=0):
    """Cria partículas saindo de (x, y) para todos os lados."""
    particulas = []

    for _ in range(quantidade):
        angulo = random.uniform(0, 2 * math.pi)
        rapidez = random.uniform(velocidade * 0.3, velocidade)

        particulas.append(Particula(
            x, y,
            math.cos(angulo) * rapidez,
            math.sin(angulo) * rapidez,
            random.choice(cores),
            random.uniform(duracao * 0.5, duracao),
            random.uniform(tamanho * 0.5, tamanho),
            gravidade
        ))

    return particulas


# ============================================================
# CLASSE BASE DOS EFEITOS
# ============================================================

class Efeito:
    """Classe base de todo efeito visual.

    - duracao: quanto tempo (em segundos) o efeito fica na tela.
    - atraso: quanto tempo esperar antes de começar.
    - proximos: efeitos que começam quando este terminar
      (ex.: a explosão que aparece quando a bola de fogo chega).
    - bloqueia: se True, o jogador espera o efeito acabar para jogar.
    """

    bloqueia = True

    def __init__(self, duracao, atraso=0):
        self.duracao = duracao
        self.tempo = -atraso
        self.proximos = []

    def atualizar(self, dt):
        self.tempo += dt

    def ativo(self):
        return self.tempo >= 0

    def terminou(self):
        return self.tempo >= self.duracao

    def progresso(self):
        # 0.0 no começo e 1.0 no fim
        return max(0.0, min(1.0, self.tempo / self.duracao))

    def desenhar(self, tela):
        pass


# ============================================================
# EFEITOS
# ============================================================

class Explosao(Efeito):
    """Clarão no centro e quadradinhos voando para todos os lados."""

    def __init__(self, x, y, cores, quantidade=30, raio=50, atraso=0, gravidade=250):
        super().__init__(0.8, atraso)
        self.x = x
        self.y = y
        self.cores = cores
        self.quantidade = quantidade
        self.raio = raio
        self.gravidade = gravidade
        self.particulas = []
        self.criada = False

    def atualizar(self, dt):
        super().atualizar(dt)
        if not self.ativo():
            return

        if not self.criada:
            self.particulas = criar_particulas(
                self.x, self.y, self.cores, self.quantidade,
                self.raio * 5, 0.7, 7, self.gravidade
            )
            self.criada = True

        for particula in self.particulas:
            particula.atualizar(dt)

    def desenhar(self, tela):
        if not self.ativo():
            return

        p = self.progresso()
        if p < 0.4:
            forca = 1 - p / 0.4
            desenhar_brilho(tela, self.cores[-1], (self.x, self.y), self.raio * (0.6 + p * 2), 170 * forca)
            desenhar_brilho(tela, self.cores[0], (self.x, self.y), self.raio * 0.6 * forca + 4, 230)

        for particula in self.particulas:
            if particula.viva():
                particula.desenhar(tela)


class Onda(Efeito):
    """Anel que cresce (onda de choque). Achatada = no chão."""

    def __init__(self, x, y, cor, raio_final=120, atraso=0, achatada=False):
        super().__init__(0.5, atraso)
        self.x = x
        self.y = y
        self.cor = cor
        self.raio_final = raio_final
        self.achatada = achatada

    def desenhar(self, tela):
        if not self.ativo():
            return

        p = self.progresso()
        raio = self.raio_final * p
        if raio < 8:
            return

        # Começa grosso (2 "pixels grandes") e afina
        grossura = 2 if p < 0.5 else 1
        raio_y = raio * 0.3 if self.achatada else raio
        anel_pixelado(tela, self.cor, (self.x, self.y), raio, raio_y, grossura)


class Corte(Efeito):
    """Riscos de golpe (espada, garra) feitos de quadradinhos."""

    def __init__(self, x, y, cor, tamanho=60, atraso=0, quantidade=3):
        super().__init__(0.35, atraso)
        self.x = x
        self.y = y
        self.cor = cor
        self.tamanho = tamanho
        self.quantidade = quantidade

    def desenhar(self, tela):
        if not self.ativo():
            return

        p = self.progresso()
        crescimento = min(1.0, p * 2.5)
        grosso = p < 0.6          # no fim o risco afina

        for i in range(self.quantidade):
            deslocamento = (i - (self.quantidade - 1) / 2) * 20
            inicio = (self.x - self.tamanho / 2, self.y - self.tamanho / 2 + deslocamento)
            fim_total = (self.x + self.tamanho / 2, self.y + self.tamanho / 2 + deslocamento)
            fim = (
                inicio[0] + (fim_total[0] - inicio[0]) * crescimento,
                inicio[1] + (fim_total[1] - inicio[1]) * crescimento,
            )
            if grosso:
                linha_pixelada(tela, self.cor, inicio, fim, PIXEL * 3)
            linha_pixelada(tela, (255, 255, 255), inicio, fim, PIXEL)


class Projetil(Efeito):
    """Algo que voa de um ponto a outro: bola de energia, flecha, lança, teia."""

    def __init__(self, inicio, fim, cor, formato="bola", tamanho=10, duracao=0.35,
                 atraso=0, rastro=None, altura_arco=0):
        super().__init__(duracao, atraso)
        self.inicio = inicio
        self.fim = fim
        self.cor = cor
        self.formato = formato
        self.tamanho = tamanho
        self.rastro = rastro or [cor]
        self.altura_arco = altura_arco
        self.particulas = []
        nome = self.qual_projetil()
        escala = ESCALA_PROJETIL + (1 if tamanho >= 13 else 0)
        espelhar = self.fim[0] < self.inicio[0]
        self.voo = quadros_do_projetil(nome, "voo", tuple(self.cor[:3]), escala, espelhar)
        impacto = quadros_do_projetil(nome, "impacto", tuple(self.cor[:3]), escala, espelhar)
        if impacto is not None:                  # ao chegar, o impacto toca no alvo
            self.proximos.append(ImpactoDoProjetil(self.fim, impacto))

    def qual_projetil(self):
        """Qual PNG usar: flecha, teia, lança, bola de fogo (bolas laranja/vermelhas) ou orbe."""
        if self.formato in ("flecha", "teia", "lanca"):
            return self.formato
        r, _, b = self.cor[:3]
        return "bola_fogo" if r > 200 and b < 100 else "orbe"

    def posicao(self):
        p = self.progresso()
        x = self.inicio[0] + (self.fim[0] - self.inicio[0]) * p
        y = self.inicio[1] + (self.fim[1] - self.inicio[1]) * p
        y -= math.sin(p * math.pi) * self.altura_arco
        return x, y

    def atualizar(self, dt):
        super().atualizar(dt)

        for particula in self.particulas:
            particula.atualizar(dt)

        if self.ativo() and not self.terminou():
            # Deixa um rastro de quadradinhos pelo caminho
            x, y = self.posicao()
            for _ in range(2):
                self.particulas.append(Particula(
                    x, y,
                    random.uniform(-40, 40), random.uniform(-40, 40),
                    random.choice(self.rastro), 0.3, self.tamanho * 0.6
                ))

    def desenhar(self, tela):
        for particula in self.particulas:
            if particula.viva():
                particula.desenhar(tela)

        if not self.ativo():
            return

        x, y = self.posicao()
        if self.voo is not None:
            quadros, (cx, cy) = self.voo
            imagem = quadros[int(self.tempo * QUADROS_POR_SEGUNDO) % len(quadros)]
            tela.blit(imagem, (round(x - cx), round(y - cy)))
        else:
            desenhar_brilho(tela, self.cor, (x, y), self.tamanho * 1.5, 230)


class ImpactoDoProjetil(Efeito):
    """O impacto do projétil no alvo (estilhaços, clarão, teia grudando...): toca uma vez e some."""

    bloqueia = False

    def __init__(self, posicao, impacto):
        self.quadros, self.centro = impacto
        super().__init__(len(self.quadros) / (QUADROS_POR_SEGUNDO + 4))
        self.posicao = posicao

    def desenhar(self, tela):
        if not self.ativo():
            return
        imagem = self.quadros[min(len(self.quadros) - 1, int(self.progresso() * len(self.quadros)))]
        tela.blit(imagem, (round(self.posicao[0] - self.centro[0]), round(self.posicao[1] - self.centro[1])))


class Raio(Efeito):
    """Relâmpago caindo do céu sobre o alvo, feito de quadradinhos."""

    def __init__(self, x, y, atraso=0, cor=(255, 235, 110)):
        super().__init__(0.45, atraso)
        self.x = x
        self.y = y
        self.cor = cor
        self.pontos = []
        self.tempo_para_trocar = 0

    def gerar_caminho(self):
        # Linha em zigue-zague do topo da tela até o alvo
        self.pontos = []
        topo_x = self.x + random.uniform(-50, 50)
        for i in range(9):
            p = i / 8
            x = topo_x + (self.x - topo_x) * p
            if 0 < i < 8:
                x += random.uniform(-20, 20)
            self.pontos.append((x, self.y * p))

    def atualizar(self, dt):
        super().atualizar(dt)
        if not self.ativo():
            return

        # O raio "treme": troca de forma várias vezes
        self.tempo_para_trocar -= dt
        if self.tempo_para_trocar <= 0:
            self.gerar_caminho()
            self.tempo_para_trocar = 0.05

    def desenhar(self, tela):
        if not self.ativo() or not self.pontos:
            return

        forca = 1 - self.progresso()
        desenhar_brilho(tela, self.cor, (self.x, self.y), 70, 140 * forca)
        for inicio, fim in zip(self.pontos, self.pontos[1:]):
            if forca > 0.4:
                linha_pixelada(tela, self.cor, inicio, fim, PIXEL * 3)
            linha_pixelada(tela, (255, 255, 255), inicio, fim, PIXEL)


class Cristais(Efeito):
    """Cristais de gelo que nascem do chão em volta do alvo."""

    def __init__(self, x, y_chao, atraso=0):
        super().__init__(1.0, atraso)
        self.x = x
        self.y = y_chao

        # Cada cristal: (deslocamento x, altura, largura)
        self.cristais = []
        for _ in range(9):
            self.cristais.append((random.uniform(-70, 70), random.uniform(50, 130), random.uniform(14, 24)))

        # Os mais altos são desenhados primeiro (ficam atrás)
        self.cristais.sort(key=lambda cristal: -cristal[1])

    def desenhar(self, tela):
        if not self.ativo():
            return

        p = self.progresso()
        if p < 0.25:
            crescimento = p / 0.25
        elif p > 0.75:
            crescimento = (1 - p) / 0.25
        else:
            crescimento = 1

        desenhar_brilho(tela, (120, 200, 255), (self.x, self.y - 90), 100, 70 * crescimento)

        # Desenha pequeno (1/4) e amplia: os cristais ficam com bordas de pixel
        largura, altura = 200 // PIXEL, 150 // PIXEL
        pequena = pygame.Surface((largura, altura), pygame.SRCALPHA)
        for dx, altura_cristal, largura_cristal in self.cristais:
            base_x = (100 + dx) / PIXEL
            pontos = [
                (base_x - largura_cristal / 2 / PIXEL, altura),
                (base_x + largura_cristal / 2 / PIXEL, altura),
                (base_x + dx * 0.15 / PIXEL, altura - altura_cristal * crescimento / PIXEL),
            ]
            pygame.draw.polygon(pequena, (140, 208, 240), pontos)
            pygame.draw.polygon(pequena, (216, 244, 255), pontos, 1)
        tela.blit(ampliar(pequena), (na_grade(self.x - 100), na_grade(self.y - 150)))


class Cura(Efeito):
    """Brilho e quadradinhos subindo (poções, cura do chefe)."""

    def __init__(self, x, y, cores, atraso=0):
        super().__init__(1.0, atraso)
        self.x = x
        self.y = y
        self.cores = cores
        self.particulas = []

    def atualizar(self, dt):
        super().atualizar(dt)
        if not self.ativo():
            return

        if self.tempo < 0.7:
            for _ in range(2):
                self.particulas.append(Particula(
                    self.x + random.uniform(-45, 45), self.y + random.uniform(-10, 80),
                    0, random.uniform(-130, -60),
                    random.choice(self.cores), 0.7, random.uniform(3, 6)
                ))

        for particula in self.particulas:
            particula.atualizar(dt)

    def desenhar(self, tela):
        if not self.ativo():
            return

        desenhar_brilho(tela, self.cores[1], (self.x, self.y + 20), 80, 70 * (1 - self.progresso()))

        for i, particula in enumerate(self.particulas):
            if not particula.viva():
                continue

            if i % 4 == 0:
                # Algumas partículas viram um sinal de "+" (5 quadradinhos)
                x, y = particula.x, particula.y
                for dx, dy in ((0, 0), (-PIXEL, 0), (PIXEL, 0), (0, -PIXEL), (0, PIXEL)):
                    quadradinho(tela, particula.cor, x + dx, y + dy)
            else:
                particula.desenhar(tela)


class FlashTela(Efeito):
    """A tela inteira pisca com uma cor (acerto crítico, explosão)."""

    def __init__(self, cor, duracao=0.3, atraso=0, transparencia=150):
        super().__init__(duracao, atraso)
        self.cor = cor
        self.transparencia = transparencia

    def desenhar(self, tela):
        if not self.ativo():
            return

        camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        camada.fill((*self.cor, int(self.transparencia * (1 - self.progresso()))))
        tela.blit(camada, (0, 0))


class TextoFlutuante(Efeito):
    """Texto que sobe e some (números de dano, "CRÍTICO!")."""

    bloqueia = False

    def __init__(self, texto, x, y, cor, fonte, atraso=0):
        super().__init__(1.1, atraso)
        self.x = x
        self.y = y
        self.imagem = fonte.render(texto, True, cor)
        self.sombra = fonte.render(texto, True, (0, 0, 0))

    def desenhar(self, tela):
        if not self.ativo():
            return

        p = self.progresso()
        subida = 40 * (1 - (1 - p) ** 2)

        if p < 0.6:
            transparencia = 255
        else:
            transparencia = int(255 * (1 - p) / 0.4)

        # Sobe de 4 em 4 pixels, como o resto da pixel art
        x = self.x - self.imagem.get_width() // 2
        y = na_grade(self.y - subida)

        self.sombra.set_alpha(transparencia)
        self.imagem.set_alpha(transparencia)
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            tela.blit(self.sombra, (x + dx, y + dy))
        tela.blit(self.imagem, (x, y))


class Confete(Efeito):
    """Chuva de confetes coloridos (vitória)."""

    bloqueia = False

    def __init__(self, largura):
        super().__init__(3.0)
        cores = [(224, 72, 58), (244, 210, 122), (150, 242, 80), (110, 160, 240), (150, 100, 200)]
        self.particulas = []
        for _ in range(120):
            self.particulas.append(Particula(
                random.uniform(0, largura), random.uniform(-300, 0),
                random.uniform(-30, 30), random.uniform(80, 200),
                random.choice(cores), random.uniform(2.0, 3.0), random.uniform(3, 6)
            ))

    def atualizar(self, dt):
        super().atualizar(dt)
        for particula in self.particulas:
            particula.atualizar(dt)

    def desenhar(self, tela):
        for particula in self.particulas:
            if particula.viva():
                particula.desenhar(tela)


# ============================================================
# GERENCIADOR
# ============================================================

class GerenciadorEfeitos:
    """Guarda os efeitos ativos, atualiza e desenha todos."""

    def __init__(self):
        self.lista = []

    def adicionar(self, efeito):
        self.lista.append(efeito)

    def atualizar(self, dt):
        continuam = []

        for efeito in self.lista:
            efeito.atualizar(dt)

            if efeito.terminou():
                # Quando um efeito termina, os "próximos" começam
                continuam += efeito.proximos
            else:
                continuam.append(efeito)

        self.lista = continuam

    def desenhar(self, tela):
        for efeito in self.lista:
            efeito.desenhar(tela)

    def ocupado(self):
        # Existe algum efeito que o jogador precisa esperar?
        for efeito in self.lista:
            if efeito.bloqueia:
                return True
        return False

    def limpar(self):
        self.lista = []
