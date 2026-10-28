"""Efeitos visuais próprios de alguns golpes (chefes e inimigos de destaque).

Quais golpes têm efeito próprio fica em roguelike/dados/efeitos_golpes.json. É SÓ visual: dano,
alvos e regras continuam no combate. Golpe fora do JSON usa os efeitos genéricos da tela de combate.

Todos herdam efeitos.Efeito e desenham em "pixels grandes" (quadradinhos de 4 px), como o resto:

    Estilhacos   cacos de vitral coloridos voando do alvo
    Feixe        raio de luz do usuário até o alvo (cresce, treme e some)
    Sopro        jato de partículas do usuário até o alvo (fogo, eclipse, gelo, seiva)
    SolNegro     disco negro com a coroa de fogo abrindo sobre o alvo
    Garras       três rasgos curvos paralelos
    Raizes       raízes que rompem o chão em volta do alvo e voltam para baixo
    Chuva        gotas (seiva, sangue) caindo sobre o alvo
    Nevasca      neve girando em volta do alvo
    Clarao       clarão de luz com raios (luz cegante, luz primordial)
"""

import math
import random

from efeitos import (Efeito, Explosao, Onda, Corte, Projetil, Cristais, FlashTela, Particula, PIXEL,
                     quadradinho, linha_pixelada, desenhar_brilho, brilho_suave)

PALETAS = {
    "eclipse": [(255, 240, 220), (255, 160, 70), (210, 50, 50), (110, 30, 90), (30, 10, 30)],
    "vitral": [(210, 44, 60), (54, 96, 210), (236, 196, 76), (140, 64, 190), (64, 170, 116), (230, 110, 50)],
    "ouro": [(255, 250, 220), (255, 226, 140), (232, 178, 58)],
    "gelo": [(230, 248, 255), (160, 220, 245), (90, 150, 210)],
    "fogo": [(255, 230, 140), (255, 150, 40), (210, 60, 30), (120, 26, 20)],
    "lava": [(255, 220, 120), (255, 120, 30), (180, 40, 20), (60, 20, 16)],
    "roxo": [(240, 200, 255), (190, 110, 255), (120, 50, 190), (60, 20, 90)],
    "sombra": [(150, 90, 220), (80, 40, 130), (30, 16, 50)],
    "sangue": [(230, 70, 60), (170, 30, 40), (100, 14, 24)],
    "seiva": [(250, 90, 80), (200, 30, 40), (120, 14, 24)],
    "raiz": [(130, 90, 60), (96, 62, 44), (64, 40, 30)],
    "pedra": [(170, 166, 176), (120, 116, 126), (80, 76, 86)],
    "petalas": [(250, 200, 214), (230, 90, 120), (180, 30, 60)],
}


def paleta(nome_ou_lista, padrao="ouro"):
    if isinstance(nome_ou_lista, list):
        return [tuple(c) for c in nome_ou_lista]
    return PALETAS.get(nome_ou_lista or padrao, PALETAS[padrao])


_config = None


def config_do_golpe(chave):
    """A configuração do efeito próprio de um golpe (dados/efeitos_golpes.json), ou None."""
    global _config
    if _config is None:
        from roguelike.dados import carregar, sem_comentarios
        try:
            _config = sem_comentarios(carregar("efeitos_golpes"))
        except FileNotFoundError:
            _config = {}
    return _config.get(chave)


# ============================================================
# EFEITOS
# ============================================================

class Estilhacos(Efeito):
    """Cacos de vitral coloridos estourando do alvo, girando e caindo."""

    def __init__(self, x, y, cores, quantidade=20, atraso=0):
        super().__init__(0.9, atraso)
        self.x, self.y = x, y
        self.cores = cores
        self.cacos = []
        for _ in range(quantidade):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(120, 320)
            self.cacos.append([x, y, math.cos(a) * v, math.sin(a) * v - 120, random.uniform(0, 6.3),
                               random.uniform(-12, 12), random.choice(cores), random.choice((1, 2))])

    def atualizar(self, dt):
        super().atualizar(dt)
        if not self.ativo():
            return
        for c in self.cacos:
            c[3] += 500 * dt
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[4] += c[5] * dt

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        if p < 0.25:
            desenhar_brilho(tela, (255, 240, 210), (self.x, self.y), 60 * (1 - p * 2), 200)
        for x, y, _, _, giro, _, cor, tam in self.cacos:
            for k in range(tam + 1):                                 # caco: 2-3 blocos em linha girada
                quadradinho(tela, cor, x + math.cos(giro) * PIXEL * 2 * k, y + math.sin(giro) * PIXEL * 2 * k, PIXEL * 2)
            quadradinho(tela, (255, 255, 255), x, y)                 # reflexo do vidro


class Feixe(Efeito):
    """Raio de luz que sai do usuário e atinge o alvo: cresce, treme e some."""

    def __init__(self, inicio, fim, cores, atraso=0, grossura=3):
        super().__init__(0.55, atraso)
        self.inicio, self.fim = inicio, fim
        self.cores = cores
        self.grossura = grossura

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        alcance = min(1.0, p / 0.3)
        forca = 1.0 if p < 0.7 else (1 - p) / 0.3
        fim = (self.inicio[0] + (self.fim[0] - self.inicio[0]) * alcance, self.inicio[1] + (self.fim[1] - self.inicio[1]) * alcance)
        tremor = 1 if int(self.tempo * 30) % 2 else 0
        grosso = max(1, int(self.grossura * forca) + tremor)
        linha_pixelada(tela, self.cores[-1], self.inicio, fim, PIXEL * (grosso + 1))
        linha_pixelada(tela, self.cores[min(1, len(self.cores) - 1)], self.inicio, fim, PIXEL * grosso)
        linha_pixelada(tela, self.cores[0], self.inicio, fim, PIXEL)
        brilho_suave(tela, self.cores[1 % len(self.cores)], fim, 50 * forca + 10, 200 * forca)
        brilho_suave(tela, self.cores[0], self.inicio, 30 * forca + 8, 160 * forca)


class Sopro(Efeito):
    """Jato de partículas do usuário até o alvo (bafo de fogo, eclipse, gelo, seiva)."""

    def __init__(self, inicio, fim, cores, atraso=0, quantidade=7):
        super().__init__(0.7, atraso)
        self.inicio, self.fim = inicio, fim
        self.cores = cores
        self.quantidade = quantidade
        self.particulas = []

    def atualizar(self, dt):
        super().atualizar(dt)
        for particula in self.particulas:
            particula.atualizar(dt)
        if self.ativo() and self.progresso() < 0.65:
            dx, dy = self.fim[0] - self.inicio[0], self.fim[1] - self.inicio[1]
            for _ in range(self.quantidade):
                espalha = random.uniform(-0.18, 0.18)
                vx = dx * 2.6 - dy * espalha * 2.6
                vy = dy * 2.6 + dx * espalha * 2.6
                self.particulas.append(Particula(self.inicio[0], self.inicio[1], vx, vy, random.choice(self.cores),
                                                 random.uniform(0.25, 0.4), random.uniform(5, 10)))

    def desenhar(self, tela):
        if not self.ativo():
            return
        for particula in self.particulas:
            if particula.viva():
                particula.desenhar(tela)
        p = self.progresso()
        if 0.2 < p < 0.85:
            brilho_suave(tela, self.cores[1], self.fim, 60, 150)


class SolNegro(Efeito):
    """O símbolo do Eclipse abrindo sobre o alvo: coroa de fogo girando em volta de um disco negro."""

    def __init__(self, x, y, cores, atraso=0, raio=46):
        super().__init__(0.9, atraso)
        self.x, self.y = x, y
        self.cores = cores
        self.raio = raio

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        abre = min(1.0, p / 0.3)
        forca = 1.0 if p < 0.65 else (1 - p) / 0.35
        r = self.raio * abre
        brilho_suave(tela, self.cores[2], (self.x, self.y), r * 2.0 + 8, 180 * forca)
        for k in range(14):                                          # raios da coroa
            a = self.tempo * 3 + k * math.pi / 7
            comp = r * (1.5 if k % 2 else 1.25)
            inicio = (self.x + math.cos(a) * r, self.y + math.sin(a) * r)
            fim = (self.x + math.cos(a) * comp, self.y + math.sin(a) * comp)
            linha_pixelada(tela, self.cores[1] if k % 2 else self.cores[0], inicio, fim, PIXEL * 2)
        if r >= PIXEL:
            desenhar_brilho(tela, self.cores[0], (self.x, self.y), r + PIXEL, 255 * forca)
            desenhar_brilho(tela, (10, 4, 12), (self.x, self.y), r, 255)


class Garras(Efeito):
    """Três rasgos curvos e paralelos (garras, lâminas)."""

    def __init__(self, x, y, cor, atraso=0, tamanho=70):
        super().__init__(0.35, atraso)
        self.x, self.y = x, y
        self.cor = cor
        self.tamanho = tamanho

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        cresce = min(1.0, p * 3)
        for k in range(3):
            desloca = (k - 1) * 16
            pontos = []
            for i in range(7):
                t = i / 6 * cresce
                x = self.x + self.tamanho * (0.5 - t) + desloca
                y = self.y - self.tamanho * 0.5 + self.tamanho * t + math.sin(t * math.pi) * 22
                pontos.append((x, y))
            for a, b in zip(pontos, pontos[1:]):
                if p < 0.6:
                    linha_pixelada(tela, self.cor, a, b, PIXEL * 3)
                linha_pixelada(tela, (255, 255, 255), a, b, PIXEL)


class Raizes(Efeito):
    """Raízes que rompem o chão em volta do alvo, se erguem e voltam para baixo."""

    def __init__(self, x, y_chao, cores, atraso=0, quantidade=6):
        super().__init__(0.9, atraso)
        self.x, self.y = x, y_chao
        self.cores = cores
        self.raizes = [(random.uniform(-70, 70), random.uniform(70, 150), random.uniform(-0.5, 0.5)) for _ in range(quantidade)]

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        cresce = p / 0.3 if p < 0.3 else (1.0 if p < 0.7 else (1 - p) / 0.3)
        for k, (dx, altura, curva) in enumerate(self.raizes):
            pontos = []
            for i in range(6):
                t = i / 5 * cresce
                pontos.append((self.x + dx + math.sin(t * 3 + k) * 10 + curva * altura * t, self.y - altura * t))
            for i, (a, b) in enumerate(zip(pontos, pontos[1:])):
                grossura = PIXEL * max(1, 3 - i // 2)
                linha_pixelada(tela, self.cores[min(2, len(self.cores) - 1)], a, b, grossura + PIXEL)
                linha_pixelada(tela, self.cores[0], a, b, grossura)
            if cresce > 0.5:
                quadradinho(tela, (230, 50, 60), pontos[-1][0], pontos[-1][1], PIXEL * 2)
        for k in range(5):                                           # terra levantando
            quadradinho(tela, self.cores[-1], self.x + (k - 2) * 24, self.y - 4 * cresce)


class Chuva(Efeito):
    """Gotas caindo sobre o alvo (seiva, sangue, veneno)."""

    def __init__(self, x, y, cores, atraso=0, quantidade=26, largura=110):
        super().__init__(0.9, atraso)
        self.x, self.y = x, y
        self.cores = cores
        self.gotas = [(random.uniform(-largura / 2, largura / 2), random.uniform(0, 0.5), random.choice(cores))
                      for _ in range(quantidade)]

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        for dx, saida, cor in self.gotas:
            t = (p - saida) / 0.45
            if 0 <= t <= 1:                                          # gota: cabeça larga e rastro fino
                y = self.y - 180 + 200 * t
                quadradinho(tela, cor, self.x + dx, y, PIXEL * 2)
                quadradinho(tela, cor, self.x + dx, y - PIXEL * 2)
                quadradinho(tela, cor, self.x + dx, y - PIXEL * 3)
            elif 1 < t < 1.4:                                        # respingo
                for lado in (-2, -1, 1, 2):
                    quadradinho(tela, cor, self.x + dx + lado * PIXEL, self.y + 20 - (2 - abs(lado)) * PIXEL)


class Nevasca(Efeito):
    """Neve girando em volta do alvo, cada vez mais fechada."""

    def __init__(self, x, y, cores, atraso=0, quantidade=30):
        super().__init__(0.9, atraso)
        self.x, self.y = x, y
        self.cores = cores
        self.flocos = [(random.uniform(0, 6.3), random.uniform(40, 90), random.uniform(-40, 40), random.choice(cores))
                       for _ in range(quantidade)]

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        forca = min(1.0, p * 4) * (1 - p * 0.6)
        brilho_suave(tela, self.cores[1], (self.x, self.y), 90, 200 * forca)
        for k, (a, r, dy, cor) in enumerate(self.flocos):
            ang = a + p * 7
            raio = r * (1 - p * 0.5)
            x, y = self.x + math.cos(ang) * raio, self.y + dy + math.sin(ang) * raio * 0.35
            atras = (x - math.sin(ang) * raio * 0.25, y + math.cos(ang) * raio * 0.1)    # rastro do giro
            linha_pixelada(tela, self.cores[-1], atras, (x, y))
            quadradinho(tela, cor, x, y, PIXEL * 2 if k % 3 == 0 else PIXEL)


class Clarao(Efeito):
    """Clarão de luz com raios saindo do alvo (luz que cega, luz primordial)."""

    def __init__(self, x, y, cores, atraso=0, raio=70):
        super().__init__(0.6, atraso)
        self.x, self.y = x, y
        self.cores = cores
        self.raio = raio

    def desenhar(self, tela):
        if not self.ativo():
            return
        p = self.progresso()
        forca = 1 - p
        brilho_suave(tela, self.cores[1], (self.x, self.y), self.raio * (0.6 + p), 230 * forca)
        desenhar_brilho(tela, self.cores[0], (self.x, self.y), self.raio * 0.4 * forca + 6, 255)
        for k in range(8):
            a = k * math.pi / 4 + 0.3
            inicio = (self.x + math.cos(a) * 20, self.y + math.sin(a) * 20)
            fim = (self.x + math.cos(a) * self.raio * (0.8 + p), self.y + math.sin(a) * self.raio * (0.8 + p))
            linha_pixelada(tela, self.cores[0], inicio, fim, PIXEL * (2 if p < 0.5 else 1))


# ============================================================
# FÁBRICA
# ============================================================

# Quanto o combate espera (sem investida) até mostrar o dano: o instante em que cada efeito "acerta"
ESPERA = {"estilhacos": 0.25, "feixe": 0.22, "sopro": 0.4, "sol_negro": 0.35, "garras": 0.15, "corte": 0.15,
          "raizes": 0.3, "chuva": 0.45, "nevasca": 0.4, "clarao": 0.2, "impacto": 0.2, "explosao": 0.2,
          "projetil": 0.3, "cristais": 0.3}


def partes_do_golpe(config):
    """Um golpe pode juntar vários efeitos ("partes"); sem "partes", a própria configuração é o efeito."""
    return config.get("partes") or [config]


def espera_do_golpe(config):
    if "espera" in config:
        return config["espera"]
    return max(parte.get("atraso", 0) + ESPERA.get(parte["tipo"], 0.3) for parte in partes_do_golpe(config))


def efeito_da_parte(parte, cores, inicio, x, y, chao, a):
    """Os efeitos de uma parte do golpe sobre um alvo em (x, y)."""
    tipo = parte["tipo"]
    if parte.get("do_alto"):                                         # luz que desce do céu sobre o alvo
        inicio = (x, y - 380)
    if tipo == "estilhacos":
        return [Estilhacos(x, y, cores, parte.get("quantidade", 20), atraso=a)]
    if tipo == "feixe":
        return [Feixe(inicio, (x, y), cores, atraso=a, grossura=parte.get("grossura", 3)),
                Explosao(x, y, cores, 14, 40, atraso=a + 0.18)]
    if tipo == "sopro":
        return [Sopro(inicio, (x, y), cores, atraso=a)]
    if tipo == "sol_negro":
        return [SolNegro(x, y, cores, atraso=a, raio=parte.get("raio", 46))]
    if tipo == "garras":
        return [Garras(x, y, cores[1 % len(cores)], atraso=a)]
    if tipo == "corte":
        return [Corte(x, y, cores[1 % len(cores)], parte.get("tamanho", 70), atraso=a, quantidade=parte.get("quantidade", 2))]
    if tipo == "raizes":
        return [Raizes(x, chao, cores, atraso=a)]
    if tipo == "chuva":
        return [Chuva(x, y, cores, atraso=a)]
    if tipo == "nevasca":
        return [Nevasca(x, y, cores, atraso=a)]
    if tipo == "clarao":
        return [Clarao(x, y, cores, atraso=a, raio=parte.get("raio", 70))]
    if tipo == "impacto":                                            # pancada no chão: onda + lascas
        return [Onda(x, chao - 10, cores[0], parte.get("raio", 110), atraso=a, achatada=True),
                Explosao(x, chao - 20, cores, 22, 46, atraso=a, gravidade=500)]
    if tipo == "explosao":
        return [Explosao(x, y, cores, parte.get("quantidade", 26), parte.get("raio", 50), atraso=a)]
    if tipo == "projetil":
        return [Projetil(inicio, (x, y), cores[1 % len(cores)], parte.get("formato", "bola"), 10, 0.3, atraso=a,
                         rastro=cores)]
    if tipo == "cristais":
        return [Cristais(x, chao, atraso=a)]
    return []


def efeitos_do_golpe(config, inicio, alvos, chao, atraso=0.0):
    """Monta a lista de efeitos de um golpe a partir da configuração do JSON.

    inicio = centro de quem usa; alvos = centros dos alvos; atraso = espera até o golpe (investida).
    """
    lista = []
    for parte in partes_do_golpe(config):
        cores = paleta(parte.get("cores", config.get("cores")))
        for i, (x, y) in enumerate(alvos):
            lista += efeito_da_parte(parte, cores, inicio, x, y, chao, atraso + parte.get("atraso", 0) + i * 0.06)
    if config.get("flash"):
        lista.append(FlashTela(tuple(config["flash"]), 0.25, atraso=atraso, transparencia=90))
    return lista
