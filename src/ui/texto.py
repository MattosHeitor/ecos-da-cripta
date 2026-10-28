"""Texto dentro de caixas: o único jeito do jogo pôr texto num espaço limitado.

    caixa = CaixaTexto(rect, tema.pequena(), alinhamento="centro", padding=6)
    caixa.desenhar(tela, "Melodia Dissonante (nv 1): 70% de chance...")

O que a CaixaTexto garante:
- quebra por largura REAL em pixels (mede o contorno e o ajuste do "fi" que o desenho usa);
- palavras maiores que a caixa são partidas;
- padding interno e alinhamento (esquerda, centro, direita; topo, meio, base);
- se não couber, tenta fontes menores; se ainda não couber, corta a última linha com "...".
  Cada corte fica anotado em TRUNCAMENTOS (os testes conferem que as telas não cortam texto).
"""

import pygame

from ui import tema
from ui.desenho import texto as desenhar_texto, sem_ligaduras

CONTORNO = 4                     # o texto do jogo é desenhado com 2 px de contorno de cada lado
RETICENCIAS = "..."
TRUNCAMENTOS = []                # (texto, largura) — só para conferência nos testes


_larguras = {}                   # (texto, fonte) -> largura (medir é caro e a tela redesenha 60x por segundo)
_quebras = {}                    # (texto, fonte, largura, contorno) -> linhas


def largura_do_texto(conteudo, fonte, contorno=True):
    """Largura exata que o texto ocupa ao ser desenhado."""
    if not conteudo:
        return 0
    chave = (conteudo, id(fonte))
    if chave not in _larguras:
        if len(_larguras) > 20000:
            _larguras.clear()
        _larguras[chave] = fonte.size(sem_ligaduras(conteudo))[0]
    return _larguras[chave] + (CONTORNO if contorno else 0)


def altura_da_linha(fonte, espaco=2):
    return fonte.get_height() + espaco


def _partir_palavra(palavra, fonte, largura, contorno):
    """Divide uma palavra que sozinha não cabe na largura."""
    pedacos, atual = [], ""
    for letra in palavra:
        if largura_do_texto(atual + letra, fonte, contorno) <= largura or not atual:
            atual += letra
        else:
            pedacos.append(atual)
            atual = letra
    if atual:
        pedacos.append(atual)
    return pedacos


def quebrar_linhas(conteudo, fonte, largura, contorno=True):
    """Lista de linhas que cabem na largura (respeita "\\n"). O resultado fica guardado."""
    chave = (str(conteudo), id(fonte), largura, contorno)
    if chave not in _quebras:
        if len(_quebras) > 5000:
            _quebras.clear()
        _quebras[chave] = _quebrar(str(conteudo), fonte, largura, contorno)
    return list(_quebras[chave])


def _quebrar(conteudo, fonte, largura, contorno):
    linhas = []
    for paragrafo in str(conteudo).split("\n"):
        atual = ""
        for palavra in paragrafo.split(" "):
            if not palavra:
                continue
            if largura_do_texto(palavra, fonte, contorno) > largura:
                if atual:
                    linhas.append(atual)
                pedacos = _partir_palavra(palavra, fonte, largura, contorno)
                linhas.extend(pedacos[:-1])
                atual = pedacos[-1]
                continue
            teste = f"{atual} {palavra}" if atual else palavra
            if largura_do_texto(teste, fonte, contorno) <= largura:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


def cortar(linha, fonte, largura, contorno=True, sempre=False):
    """A linha termina com "..." para caber na largura (sempre=True: põe "..." mesmo se já cabia)."""
    if not sempre and largura_do_texto(linha, fonte, contorno) <= largura:
        return linha
    while linha and largura_do_texto(linha.rstrip() + RETICENCIAS, fonte, contorno) > largura:
        linha = linha[:-1]
    return linha.rstrip() + RETICENCIAS


class CaixaTexto:
    """Um retângulo onde o texto sempre cabe.

    fontes: da maior para a menor, as que podem ser tentadas (padrão: a fonte pedida e as menores
    do tema). maximo_linhas limita as linhas; sem ele, o limite é a altura da caixa.
    """

    ALINHAMENTO = {"esquerda": "left", "centro": "centerx", "direita": "right"}

    def __init__(self, rect, fonte=None, cor=tema.TEXTO, alinhamento="esquerda", vertical="topo", padding=0,
                 espaco=2, fontes=None, contorno=True, maximo_linhas=None):
        self.rect = pygame.Rect(rect)
        fonte = fonte or tema.normal()
        self.fontes = fontes or [f for f in (fonte, tema.pequena(), tema.mini()) if f.get_height() <= fonte.get_height()]
        self.cor = cor
        self.alinhamento = alinhamento
        self.vertical = vertical
        self.padding = padding
        self.espaco = espaco
        self.contorno = contorno
        self.maximo_linhas = maximo_linhas

    @property
    def interno(self):
        return self.rect.inflate(-2 * self.padding, -2 * self.padding)

    def _cabem(self, fonte):
        cabem = max(1, (self.interno.height + self.espaco) // altura_da_linha(fonte, self.espaco))
        return min(cabem, self.maximo_linhas) if self.maximo_linhas else cabem

    def ajustar(self, trechos):
        """Escolhe a fonte e monta as linhas. trechos = [(texto, cor), ...] (cada um começa numa linha nova).

        Devolve (fonte, [(linha, cor), ...], cortou).
        """
        largura = self.interno.width
        for fonte in self.fontes:
            linhas = [(linha, cor) for conteudo, cor in trechos
                      for linha in quebrar_linhas(conteudo, fonte, largura, self.contorno)]
            if len(linhas) <= self._cabem(fonte):
                return fonte, linhas, False
        fonte = self.fontes[-1]
        linhas = linhas[:self._cabem(fonte)]
        ultima, cor = linhas[-1]
        linhas[-1] = (cortar(ultima, fonte, largura, self.contorno, sempre=True), cor)
        TRUNCAMENTOS.append((" ".join(c for c, _ in trechos), largura))
        return fonte, linhas, True

    def altura_para(self, trechos):
        """Altura (com padding) que os trechos ocupam: serve para caixas que crescem com o texto."""
        fonte, linhas, _ = self.ajustar(trechos)
        return len(linhas) * altura_da_linha(fonte, self.espaco) - self.espaco + 2 * self.padding

    def desenhar(self, tela, conteudo, cor=None):
        """conteudo: texto, ou lista de (texto, cor). Devolve o y logo abaixo do texto."""
        trechos = conteudo if isinstance(conteudo, list) else [(str(conteudo), cor or self.cor)]
        fonte, linhas, _ = self.ajustar(trechos)
        interno = self.interno
        altura = len(linhas) * altura_da_linha(fonte, self.espaco) - self.espaco
        y = {"topo": interno.y, "meio": interno.centery - altura // 2, "base": interno.bottom - altura}[self.vertical]
        x = getattr(interno, self.ALINHAMENTO[self.alinhamento])
        ancora = {"esquerda": "topleft", "centro": "midtop", "direita": "topright"}[self.alinhamento]
        for linha, cor_linha in linhas:
            desenhar_texto(tela, linha, fonte, cor_linha, (x, y), ancora, self.contorno)
            y += altura_da_linha(fonte, self.espaco)
        return y


def escrever(tela, conteudo, rect, fonte=None, cor=tema.TEXTO, alinhamento="esquerda", vertical="topo", **kw):
    """Atalho: CaixaTexto(rect, ...).desenhar(tela, conteudo)."""
    return CaixaTexto(rect, fonte, cor, alinhamento, vertical, **kw).desenhar(tela, conteudo)


def linha(tela, conteudo, fonte, cor, posicao, largura, ancora="topleft", contorno=True):
    """Uma linha só que cabe na largura (diminui a fonte ou corta com "..."). Devolve o retângulo.
    contorno=False: sem a sombra escura (texto escuro sobre papel, ex.: o pergaminho do Édito Real)."""
    for candidata in (fonte, tema.pequena(), tema.mini()):
        if candidata.get_height() <= fonte.get_height() and largura_do_texto(conteudo, candidata) <= largura:
            return desenhar_texto(tela, conteudo, candidata, cor, posicao, ancora, contorno)
    menor = tema.mini()
    TRUNCAMENTOS.append((conteudo, largura))
    return desenhar_texto(tela, cortar(conteudo, menor, largura), menor, cor, posicao, ancora, contorno)
