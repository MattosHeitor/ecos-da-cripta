"""A noite do acampamento: paisagem em camadas, luz da fogueira e as partículas que dão vida à cena.

    PaisagemNoturna   as camadas de assets/acampamento_noturno (geradas por gerar_acampamento.py), ampliadas 2x,
                      com paralaxe pelo mouse, nuvens e névoa deslizando, estrelas piscando e estrela cadente
    Iluminacao        mapa de luz (ambiente azulado da lua + luzes quentes) que multiplica os personagens,
                      brilho aditivo no chão, contraluz da fogueira e sombras alongadas para longe do fogo
    Fumaca, Brasas, Vagalumes   partículas simples (posição, velocidade, vida); Brasas.estalo = a fogueira crepitando

A tela do acampamento (telas/acampamento.py) desenha nesta ordem: fundo (com a névoa de longe) -> brilho do chão ->
plano do fundo (sombras, personagens iluminados, contraluz) -> névoa de perto -> planos do meio e da frente (idem) ->
fumaça/brasas -> moldura da frente.
"""

import json
import math
import os
import random

import pygame

from caminhos import CAMINHOS

PASTA = CAMINHOS.asset("acampamento_noturno")
CAMADAS_DO_FUNDO = ("ceu", "nuvens", "montanhas", "colina", "floresta", "chao")
NEVOAS = ("nevoa_longe", "nevoa_perto")       # faixas que deslizam: no pé da mata e no chão do plano do fundo
AMBIENTE = (88, 94, 136)                    # luz da lua sobre quem está longe do fogo
COR_DO_FOGO = (255, 164, 92)


def gradiente_radial(tamanho=128, curva=2.0):
    """Disco branco no meio que some até preto na borda (base de todas as luzes)."""
    sup = pygame.Surface((tamanho, tamanho))
    centro = (tamanho - 1) / 2
    for r in range(tamanho // 2, 0, -1):
        v = int(255 * (1 - (r / (tamanho / 2))) ** curva)
        pygame.draw.circle(sup, (v, v, v), (centro, centro), r)
    return sup


class PaisagemNoturna:
    """As camadas da paisagem, a paralaxe e os detalhes animados do céu."""

    def __init__(self, largura=1280, altura=720):
        with open(os.path.join(PASTA, "paisagem.json"), encoding="utf-8") as arquivo:
            self.info = json.load(arquivo)
        self.escala = self.info["escala"]
        self.margem = self.info["margem"] * self.escala
        self.camadas = {}
        tela_pronta = pygame.display.get_init() and pygame.display.get_surface() is not None
        for nome in CAMADAS_DO_FUNDO + ("frente",) + NEVOAS:
            caminho = os.path.join(PASTA, nome + ".png")
            if nome in NEVOAS and not os.path.exists(caminho):
                continue                       # (a névoa é um enfeite: sem o arquivo, a cena fica sem ela)
            img = pygame.image.load(caminho)
            if tela_pronta:
                img = img.convert() if nome == "ceu" else img.convert_alpha()     # o céu é opaco: cola mais rápido
            self.camadas[nome] = pygame.transform.scale(img, (img.get_width() * self.escala, img.get_height() * self.escala))
        self.pedacos = {nome: pedacos_com_desenho(self.camadas[nome]) for nome in ("nuvens", "frente") + NEVOAS
                        if nome in self.camadas}
        self.vento = self.info.get("vento_da_nevoa", {})
        self._terra = {}                       # montanhas + colina + floresta + chão juntos, por posição da paralaxe
        self.tamanho = (largura, altura)
        self.tempo = 0.0
        self.foco_x = 0.0                       # -1 a 1: onde o mouse está (paralaxe suave)
        self.alvo_x = 0.0
        self.rng = random.Random(7)
        self.cadente = None                    # estrela cadente: (x, y, vx, vy, vida)
        self.proxima_cadente = 6.0
        self.estrelas = [((x - self.info["margem"]) * self.escala, y * self.escala, self.rng.random() * 6.28)
                         for x, y in self.info["estrelas_grandes"]]
        self.cogumelos = [((x - self.info["margem"]) * self.escala, y * self.escala) for x, y in self.info["cogumelos"]]

    def mirar(self, mouse):
        self.alvo_x = max(-1.0, min(1.0, (mouse[0] - self.tamanho[0] / 2) / (self.tamanho[0] / 2)))

    def atualizar(self, dt):
        self.tempo += dt
        self.foco_x += (self.alvo_x - self.foco_x) * min(1.0, dt * 2.5)
        self.proxima_cadente -= dt
        if self.cadente is None and self.proxima_cadente <= 0:
            x = self.rng.uniform(200, self.tamanho[0] - 100)
            self.cadente = [x, self.rng.uniform(30, 160), -self.rng.uniform(380, 520), self.rng.uniform(120, 200), 0.0]
            self.proxima_cadente = self.rng.uniform(9, 18)
        if self.cadente is not None:
            self.cadente[0] += self.cadente[2] * dt
            self.cadente[1] += self.cadente[3] * dt
            self.cadente[4] += dt
            if self.cadente[4] > 0.9:
                self.cadente = None

    def deslocamento(self, nome):
        return -self.margem - self.foco_x * self.margem * self.info["paralaxe"].get(nome, 0)

    def desenhar_fundo(self, tela):
        tela.blit(self.camadas["ceu"], (round(self.deslocamento("ceu")), 0))
        self.desenhar_estrelas(tela)
        self.deslizar(tela, "nuvens", 4)                       # as nuvens deslizam devagar e dão a volta
        tela.blit(self.terra(), (0, 0))
        self.desenhar_nevoa(tela, "nevoa_longe")
        self.desenhar_cogumelos(tela)

    def deslizar(self, tela, nome, velocidade):
        """Cola uma camada que anda sozinha na horizontal e dá a volta (nuvens, névoa)."""
        largura = self.camadas[nome].get_width()
        x = (self.deslocamento(nome) - self.tempo * velocidade) % largura - largura
        for pedaco, (px, py) in self.pedacos[nome]:
            for volta in (0, largura):
                destino = x + volta + px
                if -pedaco.get_width() < destino < tela.get_width():
                    tela.blit(pedaco, (round(destino), py))

    def desenhar_nevoa(self, tela, nome):
        """Uma faixa de névoa ("nevoa_longe" no fundo; a tela cola a "nevoa_perto" entre o plano do fundo e o meio)."""
        if nome in self.camadas:
            self.deslizar(tela, nome, self.vento.get(nome, 5))

    def terra(self):
        """Montanhas, colina, floresta e chão já juntos (refeito só quando a paralaxe anda um degrau)."""
        degrau = round(self.foco_x * 16)
        if degrau not in self._terra:
            if len(self._terra) > 40:
                self._terra.clear()
            foco, self.foco_x = self.foco_x, degrau / 16
            junta = pygame.Surface(self.tamanho, pygame.SRCALPHA)
            for nome in ("montanhas", "colina", "floresta", "chao"):
                junta.blit(self.camadas[nome], (round(self.deslocamento(nome)), 0))
            self.foco_x = foco
            self._terra[degrau] = junta
        return self._terra[degrau]

    def desenhar_estrelas(self, tela):
        """As estrelas grandes piscam (uma cruzinha que acende e apaga) e, às vezes, uma estrela cadente."""
        dx = self.deslocamento("ceu") + self.margem
        for x, y, fase in self.estrelas:
            brilho = 0.5 + 0.5 * math.sin(self.tempo * 1.7 + fase)
            if brilho > 0.55:
                cor = (int(150 + 105 * brilho),) * 2 + (255,)
                cx, cy = int(x + dx), int(y)
                tamanho = 2 + int(brilho * 3)
                pygame.draw.line(tela, cor[:3], (cx - tamanho, cy), (cx + tamanho, cy))
                pygame.draw.line(tela, cor[:3], (cx, cy - tamanho), (cx, cy + tamanho))
        if self.cadente is not None:
            x, y, vx, vy, vida = self.cadente
            for k in range(10):
                t = k / 10
                alfa = (1 - t) * (1 - vida / 0.9)
                cor = tuple(int(c * alfa) for c in (230, 230, 255))
                px, py = x - vx * 0.05 * t, y - vy * 0.05 * t
                pygame.draw.rect(tela, cor, (px, py, 2, 2), 0)

    def desenhar_cogumelos(self, tela):
        for k, (x, y) in enumerate(self.cogumelos):
            forca = 0.5 + 0.5 * math.sin(self.tempo * 1.3 + k)
            brilho_aditivo(tela, (x + 2, y - 3), 10 + 4 * forca, (40, 90, 80), 0.6 + 0.4 * forca)

    def desenhar_frente(self, tela):
        x = round(self.deslocamento("frente"))
        for pedaco, (px, py) in self.pedacos["frente"]:
            tela.blit(pedaco, (x + px, py))


def pedacos_com_desenho(imagem, lado=96):
    """Corta a camada em quadrados e guarda só os que têm desenho (recortados): colar fica bem mais barato."""
    pedacos = []
    for y in range(0, imagem.get_height(), lado):
        for x in range(0, imagem.get_width(), lado):
            area = pygame.Rect(x, y, lado, lado).clip(imagem.get_rect())
            pedaco = imagem.subsurface(area)
            caixa = pedaco.get_bounding_rect()
            if caixa.width and caixa.height:
                pedacos.append((pedaco.subsurface(caixa).copy(), (area.x + caixa.x, area.y + caixa.y)))
    return pedacos


_GRADIENTES = {}


def gradiente(tamanho, curva=2.0):
    chave = (int(tamanho), curva)
    if chave not in _GRADIENTES:
        base = _GRADIENTES.setdefault(("base", curva), gradiente_radial(128, curva))
        _GRADIENTES[chave] = pygame.transform.smoothscale(base, (max(2, int(tamanho)), max(2, int(tamanho))))
    return _GRADIENTES[chave]


_BRILHOS = {}


def brilho_pronto(raio, cor, forca=1.0, achatar=1.0, curva=2.0):
    """O gradiente já no tamanho e na cor (guardado: raio e força arredondados para reaproveitar)."""
    raio, forca = int(raio) // 2 * 2, round(forca * 12) / 12
    chave = (raio, tuple(cor), forca, round(achatar, 2), curva)
    if chave not in _BRILHOS:
        if len(_BRILHOS) > 600:
            _BRILHOS.clear()
        luz = gradiente(raio * 2, curva).copy()
        if achatar != 1.0:
            luz = pygame.transform.smoothscale(luz, (int(raio * 2), max(2, int(raio * 2 * achatar))))
        luz.fill(tuple(min(255, int(c * forca)) for c in cor), special_flags=pygame.BLEND_RGB_MULT)
        _BRILHOS[chave] = luz
    return _BRILHOS[chave]


def brilho_aditivo(tela, centro, raio, cor, forca=1.0, achatar=1.0):
    """Luz somada à tela (clareia o que já está desenhado). achatar < 1 = elipse deitada (luz no chão)."""
    if raio < 2:
        return
    luz = brilho_pronto(raio, cor, forca, achatar)
    tela.blit(luz, luz.get_rect(center=(int(centro[0]), int(centro[1]))), special_flags=pygame.BLEND_RGB_ADD)


class Luz:
    def __init__(self, x, y, raio, cor, forca=1.0, tremor=0.0, achatar=1.0):
        self.x, self.y, self.raio, self.cor, self.forca, self.tremor = x, y, raio, cor, forca, tremor
        self.achatar = achatar


class Iluminacao:
    """Mapa de luz em 1/4 da resolução (fica suave ao ampliar) que multiplica a camada dos personagens."""

    REDUCAO = 4

    def __init__(self, tamanho=(1280, 720), ambiente=AMBIENTE):
        self.tamanho = tamanho
        self.ambiente = ambiente
        self.luzes = []
        self.tempo = 0.0
        self.pequeno = pygame.Surface((tamanho[0] // self.REDUCAO, tamanho[1] // self.REDUCAO))
        self._contraluz = {}

    def tremular(self, luz):
        """Multiplicador do tremor da chama (soma de senos: nunca repete igual)."""
        t = self.tempo * (1 + luz.x % 7 / 10)
        return 1 + luz.tremor * (0.55 * math.sin(t * 9.1) + 0.3 * math.sin(t * 15.7 + 1) + 0.15 * math.sin(t * 23.3 + 2))

    def mapa(self):
        """O mapa de luz do quadro, já ampliado para a tela."""
        r = self.REDUCAO
        self.pequeno.fill(self.ambiente)
        for luz in self.luzes:
            raio = luz.raio * self.tremular(luz) / r
            mancha = brilho_pronto(raio, luz.cor, luz.forca, luz.achatar, 1.6)
            self.pequeno.blit(mancha, mancha.get_rect(center=(luz.x / r, luz.y / r)), special_flags=pygame.BLEND_RGB_ADD)
        # amplia em dois passos: suave até a metade e dobra (bem mais barato que suavizar até o tamanho todo)
        meio = pygame.transform.smoothscale(self.pequeno, (self.tamanho[0] // 2, self.tamanho[1] // 2))
        return pygame.transform.scale(meio, self.tamanho)

    def iluminar(self, camada, mapa=None):
        """Multiplica a camada dos personagens pela luz (perto do fogo: cor quente; longe: azul da lua).

        mapa: o do quadro, já calculado (a tela ilumina os planos em duas passadas com o mesmo mapa)."""
        camada.blit(self.mapa() if mapa is None else mapa, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def contraluz(self, imagem, origem, fogo, chave):
        """Borda acesa do lado virado para a fogueira (o fogo recorta a silhueta). Devolve (superfície, posição)."""
        distancia = math.dist((origem[0] + imagem.get_width() / 2, origem[1] + imagem.get_height()), fogo)
        forca = max(0.0, 1 - distancia / 520)
        if forca <= 0.05:
            return None
        lado = 2 if fogo[0] > origem[0] + imagem.get_width() / 2 else -2
        nivel = round(forca * 6)
        cache = (chave, lado, nivel)
        if cache not in self._contraluz:
            mascara = pygame.mask.from_surface(imagem)
            borda = mascara.copy()
            borda.erase(mascara, (-lado, 0))
            cima = mascara.copy()
            cima.erase(mascara, (0, 2))
            if nivel >= 4:                                         # bem perto: o topo também acende
                borda.draw(cima, (0, 0))
            cor = tuple(int(c * nivel / 6 * 0.8) for c in COR_DO_FOGO)
            self._contraluz[cache] = borda.to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0))
        return self._contraluz[cache]


def sombra_no_chao(tela, pe, largura, fogo, forca=1.0):
    """Sombra do personagem esticada para longe da fogueira (e uma mancha escura nos pés)."""
    dx, dy = pe[0] - fogo[0], pe[1] - fogo[1]
    distancia = max(40.0, math.hypot(dx, dy))
    perto = max(0.0, 1 - distancia / 700)
    comprimento = largura * (0.9 + 1.4 * perto)
    deslocamento = dx / distancia * comprimento * 0.45
    alfa = int((60 + 80 * perto) * forca)
    mancha = pygame.Surface((int(comprimento + largura * 0.5), 18), pygame.SRCALPHA)
    pygame.draw.ellipse(mancha, (6, 4, 10, alfa), mancha.get_rect())
    tela.blit(mancha, mancha.get_rect(center=(pe[0] + deslocamento, pe[1] + 1)))
    pes = pygame.Surface((int(largura * 0.7), 10), pygame.SRCALPHA)
    pygame.draw.ellipse(pes, (4, 2, 8, int(120 * forca)), pes.get_rect())
    tela.blit(pes, pes.get_rect(center=(pe[0], pe[1])))


# ============================================================
# PARTÍCULAS
# ============================================================

class Particula:
    __slots__ = ("x", "y", "vx", "vy", "vida", "duracao", "tamanho", "fase")

    def __init__(self, x, y, vx, vy, duracao, tamanho, fase=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.vida, self.duracao, self.tamanho, self.fase = 0.0, duracao, tamanho, fase


class Fumaca:
    """Rolos de fumaça subindo da fogueira, crescendo, entortando com o vento e sumindo."""

    def __init__(self, origem, rng):
        self.origem, self.rng = origem, rng
        self.particulas = []
        self.espera = 0.0

    def atualizar(self, dt):
        self.espera -= dt
        if self.espera <= 0:
            self.espera = 0.16
            x, y = self.origem
            self.particulas.append(Particula(x + self.rng.uniform(-10, 10), y, self.rng.uniform(-4, 4),
                                             -self.rng.uniform(28, 40), self.rng.uniform(4.0, 5.5), self.rng.uniform(6, 9),
                                             self.rng.random() * 6.28))
        for p in self.particulas:
            p.vida += dt
            p.x += (p.vx + 10 * min(1.0, p.vida / 2) + math.sin(p.vida * 1.4 + p.fase) * 6) * dt
            p.y += p.vy * dt
        self.particulas = [p for p in self.particulas if p.vida < p.duracao]

    def desenhar(self, tela):
        for p in self.particulas:
            t = p.vida / p.duracao
            raio = p.tamanho + t * 26
            alfa = int(70 * (1 - t) * min(1.0, p.vida * 2))
            if alfa <= 2:
                continue
            bolha = pygame.Surface((int(raio * 2) + 2, int(raio * 2) + 2), pygame.SRCALPHA)
            cor = (int(80 - 30 * t), int(72 - 26 * t), int(90 - 20 * t), alfa)
            pygame.draw.circle(bolha, cor, (raio + 1, raio + 1), raio)
            tela.blit(bolha, (p.x - raio, p.y - raio))


class Brasas:
    """Fagulhas que saltam da fogueira, piscando, e apagam no ar."""

    CORES = ((255, 214, 120), (255, 150, 60), (230, 90, 40))

    def __init__(self, origem, rng):
        self.origem, self.rng = origem, rng
        self.particulas = []
        self.espera = 0.0

    def atualizar(self, dt):
        self.espera -= dt
        while self.espera <= 0:
            self.espera += 0.06
            x, y = self.origem
            self.particulas.append(Particula(x + self.rng.uniform(-24, 24), y + self.rng.uniform(-10, 10),
                                             self.rng.uniform(-22, 22), -self.rng.uniform(70, 150), self.rng.uniform(0.9, 2.0),
                                             self.rng.choice((2, 2, 4)), self.rng.random() * 6.28))
        for p in self.particulas:
            p.vida += dt
            p.x += (p.vx + math.sin(p.vida * 6 + p.fase) * 18) * dt
            p.y += p.vy * dt
            p.vy *= 0.985
        self.particulas = [p for p in self.particulas if p.vida < p.duracao]

    def estalo(self, quantidade=14):
        """A lenha estala: um punhado de fagulhas mais rápidas, abertas em leque (a tela também aviva a luz)."""
        x, y = self.origem
        for _ in range(quantidade):
            self.particulas.append(Particula(x + self.rng.uniform(-14, 14), y + self.rng.uniform(-6, 6),
                                             self.rng.uniform(-70, 70), -self.rng.uniform(150, 260),
                                             self.rng.uniform(0.6, 1.3), self.rng.choice((2, 2, 4)),
                                             self.rng.random() * 6.28))

    def desenhar(self, tela):
        for p in self.particulas:
            t = p.vida / p.duracao
            cor = self.CORES[min(2, int(t * 3))]
            if math.sin(p.vida * 20 + p.fase) < -0.6:
                continue                                          # pisca
            pygame.draw.rect(tela, cor, (round(p.x), round(p.y), p.tamanho, p.tamanho))


class Vagalumes:
    """Pontinhos verde-amarelos passeando devagar perto da mata, acendendo e apagando."""

    def __init__(self, rng, area, quantidade=16):
        self.rng, self.area = rng, pygame.Rect(area)
        self.particulas = [Particula(rng.uniform(self.area.left, self.area.right), rng.uniform(self.area.top, self.area.bottom),
                                     0, 0, 1, 2, rng.random() * 6.28) for _ in range(quantidade)]

    def atualizar(self, dt):
        for p in self.particulas:
            p.vida += dt
            p.vx += self.rng.uniform(-30, 30) * dt
            p.vy += self.rng.uniform(-30, 30) * dt
            p.vx, p.vy = max(-18, min(18, p.vx)), max(-12, min(12, p.vy))
            p.x += p.vx * dt
            p.y += p.vy * dt
            if not self.area.collidepoint(p.x, p.y):
                p.vx, p.vy = -p.vx, -p.vy
                p.x = max(self.area.left, min(self.area.right, p.x))
                p.y = max(self.area.top, min(self.area.bottom, p.y))

    def desenhar(self, tela):
        for p in self.particulas:
            forca = 0.5 + 0.5 * math.sin(p.vida * 2.2 + p.fase)
            if forca < 0.3:
                continue
            brilho_aditivo(tela, (p.x, p.y), 9 + 5 * forca, (110, 140, 50), forca)
            pygame.draw.rect(tela, (220, 255, 150), (round(p.x), round(p.y), 2, 2))
