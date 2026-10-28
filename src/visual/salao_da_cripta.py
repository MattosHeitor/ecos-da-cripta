"""O salão da Cripta (fundo da tela de título): camadas de assets/salao_da_cripta (gerar_salao.py) e a vida da cena.

    SalaoDaCripta   paralaxe pelo mouse, feixes de luz coloridos descendo do vitral com poeira dançando dentro,
                    o halo da lua atrás do vidro, chamas das velas tremendo (e a luz delas no chão), cavaleiros de
                    pedra nos pedestais (o sprite do paladino virado estátua) e névoa baixa correndo no piso

Ordem: fundo -> feixes e poeira -> (morcegos de longe) -> colunas, estátuas -> chamas e brilhos -> névoa ->
(grupo e morcegos de perto, desenhados pela tela) -> frente.

Os três feixes de luz e a névoa são imagens prontas (feixe_0..2.png e nevoa.png, para a tela de 1280x720), feitas por
ferramentas/sprites_macabros/gerar_luzes_do_salao.py: o jogo só carrega (assim não precisa do numpy).
"""

import json
import math
import os
import random

import pygame

from caminhos import CAMINHOS
from visual.acampamento_noturno import brilho_aditivo, brilho_pronto

PASTA = CAMINHOS.asset("salao_da_cripta")
CAMADAS = ("fundo", "colunas", "frente")
CORES_DOS_FEIXES = ((70, 90, 190), (170, 60, 70), (200, 160, 70))


def canto_do_feixe(topo, base, largura_topo, largura_base):
    """O canto de cima à esquerda da imagem do feixe (onde ela é desenhada)."""
    return int(min(topo[0] - largura_topo, base[0] - largura_base)), int(topo[1])


def geometria_dos_feixes(vitral, tamanho):
    """Os três feixes, um por lanceta do vitral, abrindo até o tapete: [(topo, base, largura_topo, largura_base,
    cor, força)]. A ferramenta das luzes usa a mesma conta para desenhar as imagens."""
    vx, vtopo, vbase, vlarg = vitral
    chao = tamanho[1] - 40
    return [((vx + dx * vlarg, vbase - 40), (vx + dx * vlarg * 4.4, chao), vlarg * 0.6, vlarg * 2.4,
             CORES_DOS_FEIXES[k], 0.55) for k, dx in enumerate((-2 / 3, 0, 2 / 3))]


def vitral_na_tela(info):
    """O vitral do salao.json em pixels da tela: (x, topo, base, largura)."""
    escala, margem = info["escala"], info["margem"] * info["escala"]
    vx, vtopo, vbase, vlarg = info["vitral"]
    return vx * escala - margem, vtopo * escala, vbase * escala, vlarg * escala


class SalaoDaCripta:
    def __init__(self, largura=1280, altura=720):
        with open(os.path.join(PASTA, "salao.json"), encoding="utf-8") as arquivo:
            self.info = json.load(arquivo)
        self.escala = self.info["escala"]
        self.margem = self.info["margem"] * self.escala
        tela_pronta = pygame.display.get_init() and pygame.display.get_surface() is not None
        self.camadas = {}
        for nome in CAMADAS:
            img = pygame.image.load(os.path.join(PASTA, nome + ".png"))
            img = (img.convert() if nome == "fundo" else img.convert_alpha()) if tela_pronta else img
            self.camadas[nome] = pygame.transform.scale(img, (img.get_width() * self.escala, img.get_height() * self.escala))
        self.tamanho = (largura, altura)
        self.tempo = 0.0
        self.foco_x, self.alvo_x = 0.0, 0.0
        self.rng = random.Random(11)
        self.velas = [(self.para_tela(x), y * self.escala, forca, camada, self.rng.random() * 6.28)
                      for x, y, forca, camada in self.info["velas"]]
        self.vitral = vitral_na_tela(self.info)
        self.feixes = self.criar_feixes()
        self.poeira = [[self.rng.uniform(0, 1), self.rng.uniform(0, 1), self.rng.uniform(0, 6.28), self.rng.randrange(3)]
                       for _ in range(70)]
        self.nevoa = self.criar_nevoa()
        self._estatuas = None
        self._feixes_prontos = {}

    def para_tela(self, x):
        return x * self.escala - self.margem

    # ---------------- preparação ----------------
    def criar_feixes(self):
        """Três feixes, um por lanceta do vitral, abrindo até o tapete (as imagens vêm prontas: feixe_k.png)."""
        feixes = []
        for k, (topo, base, largura_topo, largura_base, _, _) in enumerate(geometria_dos_feixes(self.vitral, self.tamanho)):
            imagem = pygame.image.load(os.path.join(PASTA, f"feixe_{k}.png"))
            feixes.append((imagem, topo, base, k, canto_do_feixe(topo, base, largura_topo, largura_base)))
        return feixes

    def criar_nevoa(self):
        """Faixa de névoa (manchas suaves) que corre devagar pelo piso, repetindo (pronta: nevoa.png)."""
        return pygame.image.load(os.path.join(PASTA, "nevoa.png"))

    def estatuas(self, sprites):
        """O paladino virado cavaleiro de pedra (cinza-azulado, com o lado da luz mais claro), um de cada lado."""
        if self._estatuas is None:
            base = sprites.quadro("paladino", "parado", 0, 2)
            pedra = pygame.transform.grayscale(base)
            pedra.fill((118, 116, 140), special_flags=pygame.BLEND_RGB_MULT)                 # pedra fria e fosca
            pedra.fill((18, 16, 26), special_flags=pygame.BLEND_RGB_ADD)
            musgo = pygame.mask.from_surface(pedra)                                           # a base escurecida de limo
            base_escura = pygame.Surface(pedra.get_size(), pygame.SRCALPHA)
            altura_img = pedra.get_height()
            for y in range(altura_img):
                t = max(0.0, (y / altura_img - 0.6) / 0.4)
                pygame.draw.line(base_escura, (int(255 - 90 * t), int(255 - 70 * t), int(255 - 90 * t), 255), (0, y), (pedra.get_width(), y))
            pedra.blit(base_escura, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            del musgo
            self._estatuas = []
            for (x, y), espelhar in zip(self.info["estatuas"], (False, True)):
                imagem = pygame.transform.flip(pedra, True, False) if espelhar else pedra
                ax, ay = sprites.ancora("paladino", 2, espelhar)
                self._estatuas.append((imagem, (self.para_tela(x) - ax, y * self.escala - ay)))
        return self._estatuas

    # ---------------- tempo ----------------
    def mirar(self, mouse):
        self.alvo_x = max(-1.0, min(1.0, (mouse[0] - self.tamanho[0] / 2) / (self.tamanho[0] / 2)))

    def atualizar(self, dt):
        self.tempo += dt
        self.foco_x += (self.alvo_x - self.foco_x) * min(1.0, dt * 2.5)
        for grao in self.poeira:
            grao[1] += dt * 0.02
            grao[0] += math.sin(self.tempo * 0.7 + grao[2]) * dt * 0.01
            if grao[1] > 1:
                grao[1] -= 1

    def feixe_com_forca(self, k, forca):
        """O feixe k já escurecido (12 níveis guardados: não copia nem tinge a cada quadro)."""
        nivel = round(forca * 12)
        chave = (k, nivel)
        if chave not in self._feixes_prontos:
            img = self.feixes[k][0].copy()
            img.fill((int(255 * nivel / 12),) * 3, special_flags=pygame.BLEND_RGB_MULT)
            self._feixes_prontos[chave] = img
        return self._feixes_prontos[chave]

    def deslocamento(self, nome):
        return -self.foco_x * self.margem * self.info["paralaxe"].get(nome, 0)

    # ---------------- desenho ----------------
    def desenhar_fundo(self, tela):
        dx = self.deslocamento("fundo")
        tela.blit(self.camadas["fundo"], (round(dx) - self.margem, 0))
        vx, vtopo, vbase, vlarg = self.vitral
        pulso = 0.85 + 0.15 * math.sin(self.tempo * 0.6)
        brilho_aditivo(tela, (vx + dx, (vtopo + vbase) / 2), vlarg * 2.6, (60, 60, 120), pulso)       # a lua atrás do vidro
        for imagem, topo, base, k, canto in self.feixes:
            forca = 0.75 + 0.25 * math.sin(self.tempo * 0.5 + k * 1.7)       # nuvens passando na frente da lua
            tela.blit(self.feixe_com_forca(k, forca), (canto[0] + dx, canto[1]), special_flags=pygame.BLEND_RGB_ADD)
        self.desenhar_poeira(tela, dx)
        self.desenhar_chamas(tela, "fundo")

    def desenhar_poeira(self, tela, dx):
        """Grãos de poeira subindo devagar dentro dos feixes (brilham mais no meio da luz)."""
        for u, v, fase, k in self.poeira:
            imagem, topo, base, _, _ = self.feixes[k]
            x = topo[0] + (base[0] - topo[0]) * v + (u - 0.5) * (60 + 200 * v) + dx
            y = topo[1] + (base[1] - topo[1]) * (1 - v)
            brilho = 0.5 + 0.5 * math.sin(self.tempo * 2 + fase)
            if brilho < 0.25:
                continue
            cor = tuple(int(c * (0.4 + 0.6 * brilho)) for c in (220, 210, 240))
            pygame.draw.rect(tela, cor, (round(x), round(y), 2, 2))

    def desenhar_colunas(self, tela, sprites):
        dx = self.deslocamento("colunas")
        tela.blit(self.camadas["colunas"], (round(dx) - self.margem, 0))
        for imagem, (x, y) in self.estatuas(sprites):
            tela.blit(imagem, (round(x + dx), round(y)))
        self.desenhar_chamas(tela, "colunas")

    def desenhar_nevoa(self, tela):
        largura = self.nevoa.get_width()
        x = -(self.tempo * 12) % largura
        y = self.tamanho[1] - self.nevoa.get_height() + 10
        tela.blit(self.nevoa, (x - largura, y))
        tela.blit(self.nevoa, (x, y))

    def desenhar_frente(self, tela):
        dx = self.deslocamento("frente")
        tela.blit(self.camadas["frente"], (round(dx) - self.margem, 0))
        self.desenhar_chamas(tela, "frente")

    def desenhar_chamas(self, tela, camada):
        """Chama de cada vela (gota que tremula) e a luz quente em volta; as do chão acendem o piso."""
        dx = self.deslocamento(camada)
        indice = -1
        for x, y, forca, onde, fase in self.velas:
            if onde != camada:
                continue
            indice += 1                                                # (contando só as desta camada)
            x += dx
            tremor = 0.8 + 0.2 * math.sin(self.tempo * 11 + fase) + 0.1 * math.sin(self.tempo * 23 + fase * 2)
            brilho_aditivo(tela, (x, y), (18 + 30 * forca) * tremor, (150, 86, 34), 0.9)
            altura = (5 + 3 * forca) * tremor
            pontas = [(x - 2, y + 3), (x + 2, y + 3), (x + math.sin(self.tempo * 9 + fase) * 1.2, y + 3 - altura * 2)]
            pygame.draw.polygon(tela, (255, 150, 60), pontas)
            pygame.draw.polygon(tela, (255, 236, 160), [(x - 1, y + 3), (x + 1, y + 3), (x, y + 3 - altura)])
            if camada == "frente" and indice % 7 == 3:                  # a vela do meio acende o chão do candelabro
                brilho_aditivo(tela, (x, self.tamanho[1] - 50), 190, (90, 52, 20), 0.8 * tremor, achatar=0.3)
