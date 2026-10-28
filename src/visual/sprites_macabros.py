"""Carregador dos sprites macabros (assets/sprites_macabros).

Cada folha tem as linhas parado (4 quadros), ataque (4), dano (2), morte (4) e sentado (4); alguns
sprites têm linhas extras (as gárgulas têm "despertar": a estátua que ganha vida ao entrar na luta).
Os desenhos olham para a DIREITA; inimigos são espelhados.
O "pé" (âncora) de cada personagem está no catalogo.json.

Heróis com skins têm nome composto: "guerreiro_berserker+@aureola+@brasa". A base é a roupa;
cada "@acessorio" vira a camada "camada_<geometria da roupa>_<acessorio>", desenhada por cima
no mesmo quadro (as camadas são geradas com o mesmo esqueleto, então encaixam).
Peças de equipamento levam a cor junto ("@eq_placas:404c4c"): a parte neutra da camada é multiplicada
pela cor e a linha "<anim>_fixo" (madeira, couro, ouro) entra por cima; camadas "atras" (capas) vão
antes da roupa. Com arma equipada, a roupa é a "<roupa>_desarmado".

    sprites = Sprites()
    animador = Animador(sprites, "esqueleto")
    animador.tocar("ataque")            # toca uma vez e volta ao "parado"
    animador.atualizar(dt)
    animador.desenhar(tela, x_pe, y_pe, olhando_esquerda=True)
"""

import json
import os

import pygame

from caminhos import CAMINHOS

PASTA = CAMINHOS.asset("sprites_macabros")

# Nome desconhecido vira um esqueleto acinzentado (o jogo nunca quebra por falta de sprite)
RESERVA = ("esqueleto", (120, 120, 120))
COR_SILHUETA = (34, 26, 42, 255)
SUFIXO_DESARMADO = "_desarmado"      # roupa do herói sem a arma da classe (a equipada vem numa camada)
PLANO_FIXO = "_fixo"                 # camadas de equipamento: linha com o que NÃO é tingido


def tingir(imagem, cor, forca=0.55):
    """Copia a imagem misturando os pixels com uma cor (mantém a transparência)."""
    multiplicada = imagem.copy()
    multiplicada.fill((*cor, 255), special_flags=pygame.BLEND_RGBA_MULT)
    multiplicada.set_alpha(int(255 * forca))
    copia = imagem.copy()
    copia.blit(multiplicada, (0, 0))
    return copia


def clarear_inteiro(imagem):
    """Silhueta branca (piscar quando leva dano)."""
    copia = imagem.copy()
    copia.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return copia


class Sprites:
    def __init__(self, pasta=PASTA):
        self.pasta = pasta
        with open(os.path.join(pasta, "catalogo.json"), encoding="utf-8") as arquivo:
            self.catalogo = json.load(arquivo)
        self._folhas = {}
        self._cache = {}

    def partes(self, nome):
        """"guerreiro+@aureola" -> ("guerreiro", ["camada_guerreiro_aureola"]). Camadas que não existem são ignoradas."""
        base, camadas = self.partes_com_cor(nome)
        return base, [camada for camada, _ in camadas]

    def partes_com_cor(self, nome):
        """"guerreiro+@aureola+@eq_elmo:84868e" -> ("guerreiro", [("camada_guerreiro_aureola", None),
        ("camada_guerreiro_eq_elmo", (132, 134, 142))]). Uma roupa "_desarmado" que não existe vira a normal."""
        base, *extras = nome.split("+")
        if base not in self.catalogo and base.endswith(SUFIXO_DESARMADO):
            base = base[:-len(SUFIXO_DESARMADO)]
        geometria = self.catalogo.get(base, {}).get("geometria")
        camadas = []
        for extra in extras:
            extra, _, cor = extra.partition(":")
            camada = f"camada_{geometria}_{extra[1:]}" if extra.startswith("@") else extra
            if camada in self.catalogo:
                camadas.append((camada, tuple(int(cor[k:k + 2], 16) for k in (0, 2, 4)) if cor else None))
        return base, camadas

    def existe(self, nome):
        return self.partes(nome)[0] in self.catalogo

    def nome_real(self, nome):
        """O sprite que existe de verdade (ou a reserva) e a cor para tingir."""
        base = self.partes(nome)[0]
        if base in self.catalogo:
            return base, None
        return RESERVA

    def meta(self, nome):
        return self.catalogo[self.nome_real(nome)[0]]

    def quadros_de(self, nome, anim):
        return self.meta(nome)["animacoes"][anim]["quadros"]

    def tem_animacao(self, nome, anim):
        """Linhas extras só de alguns sprites (ex.: "despertar" das gárgulas)."""
        return anim in self.meta(nome)["animacoes"]

    def escala_padrao(self, nome):
        return self.meta(nome).get("escala", 3)

    def _folha(self, nome):
        if nome not in self._folhas:
            img = pygame.image.load(os.path.join(self.pasta, nome + ".png"))
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            self._folhas[nome] = img
        return self._folhas[nome]

    def quadro(self, nome, anim="parado", i=0, escala=2, espelhar=False, efeito=None):
        """Imagem de um quadro já ampliado (pixels nítidos).

        efeito: None, "branco" (piscar de dano), "silhueta" (bestiário/grimório: só a sombra)
        ou uma cor (tingir, ex.: heróis corrompidos).
        """
        chave = (nome, anim, i, escala, espelhar, efeito)
        if chave in self._cache:
            return self._cache[chave]
        base, camadas = self.partes_com_cor(nome)
        img = self._sem_efeito(base, anim, i, escala, espelhar)
        if camadas:                          # herói com skins/equipamento: camadas de trás, roupa, camadas da frente
            junto = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            atras = [c for c in camadas if self.catalogo[c[0]].get("atras")]
            for camada, cor in atras:
                junto.blit(self._camada(camada, cor, anim, i, escala, espelhar), (0, 0))
            junto.blit(img, (0, 0))
            for camada, cor in camadas:
                if (camada, cor) not in atras:
                    junto.blit(self._camada(camada, cor, anim, i, escala, espelhar), (0, 0))
            img = junto
        if efeito == "branco":
            img = clarear_inteiro(img)
        elif efeito == "silhueta":
            img = pygame.mask.from_surface(img).to_surface(setcolor=COR_SILHUETA, unsetcolor=(0, 0, 0, 0))
        elif efeito is not None:
            img = tingir(img, efeito)
        self._cache[chave] = img
        return img

    def _sem_efeito(self, nome, anim, i, escala, espelhar):
        """Um quadro de uma folha só, ampliado (e espelhado), sem efeito."""
        chave = ("puro", nome, anim, i, escala, espelhar)
        if chave not in self._cache:
            real, cor_substituto = self.nome_real(nome)
            meta = self.catalogo[real]
            n = meta["animacoes"][anim]["quadros"]
            w, h = meta["celula"]
            linha = meta["animacoes"][anim]["linha"]
            sub = self._folha(real).subsurface(((i % n) * w, linha * h, w, h))
            img = pygame.transform.scale(sub, (int(w * escala), int(h * escala)))
            if espelhar:
                img = pygame.transform.flip(img, True, False)
            if cor_substituto is not None:
                img = tingir(img, cor_substituto, 0.7)
            self._cache[chave] = img
        return self._cache[chave]

    def _camada(self, camada, cor, anim, i, escala, espelhar):
        """Camada de equipamento: a parte neutra multiplicada pela cor da peça + a parte de cor própria."""
        if not self.catalogo[camada].get("tingivel"):
            return self._sem_efeito(camada, anim, i, escala, espelhar)
        chave = ("tinta", camada, cor, anim, i, escala, espelhar)
        if chave not in self._cache:
            img = self._sem_efeito(camada, anim, i, escala, espelhar).copy()
            if cor is not None:
                img.fill((*cor, 255), special_flags=pygame.BLEND_RGBA_MULT)
            img.blit(self._sem_efeito(camada, anim + PLANO_FIXO, i, escala, espelhar), (0, 0))
            self._cache[chave] = img
        return self._cache[chave]

    def ancora(self, nome, escala=2, espelhar=False):
        """Posição dos pés dentro do quadro ampliado."""
        meta = self.meta(nome)
        ax, ay = meta["ancora"]
        if espelhar:
            ax = meta["celula"][0] - ax
        return ax * escala, ay * escala

    def caixa(self, nome, escala=2):
        """Retângulo do corpo no 1º quadro (relativo aos pés): (esquerda, topo, largura, altura)."""
        chave = ("caixa", nome, escala)
        if chave not in self._cache:
            img = self.quadro(nome, "parado", 0, escala)
            rect = img.get_bounding_rect()
            ax, ay = self.ancora(nome, escala)
            self._cache[chave] = pygame.Rect(rect.x - ax, rect.y - ay, rect.width, rect.height)
        return self._cache[chave]


class Animador:
    """Controla qual animação está tocando para um personagem."""

    VELOCIDADE = {"parado": 5, "ataque": 11, "dano": 9, "morte": 7, "despertar": 6, "decreto": 5, "banquete": 5,
                  "correr": 12}
    OUTRAS = 7              # linhas extras sem velocidade própria

    def __init__(self, sprites, nome):
        self.sprites = sprites
        self.nome = nome
        self.anim = "parado"
        self.tempo = 0.0
        self.depois = "parado"
        self.segurar = 0.0

    def tocar(self, anim, depois="parado", segurar=0.0):
        """Toca 'ataque', 'dano' ou 'morte' uma vez (morte fica no último quadro). segurar: segundos parado no último
        quadro antes de voltar (ex.: o Rei com o cetro erguido enquanto o Édito está na tela)."""
        if self.anim == "morte" and anim != "parado":
            return
        self.anim = anim
        self.tempo = 0.0
        self.depois = depois
        self.segurar = segurar

    def reviver(self):
        self.anim = "parado"
        self.tempo = 0.0

    def atualizar(self, dt):
        self.tempo += dt
        n = self.sprites.quadros_de(self.nome, self.anim)
        if self.anim not in ("parado", "morte") and \
                self.tempo >= n / self.VELOCIDADE.get(self.anim, self.OUTRAS) + self.segurar:
            self.anim = self.depois
            self.tempo = 0.0
            self.segurar = 0.0

    @property
    def indice(self):
        n = self.sprites.quadros_de(self.nome, self.anim)
        i = int(self.tempo * self.VELOCIDADE.get(self.anim, self.OUTRAS))
        if self.anim == "parado":
            return i % n
        return min(i, n - 1)
