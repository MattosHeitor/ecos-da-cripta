"""Layout: dividir a tela em áreas sem sobrepor nada, e conferir se uma tela respeita isso.

Divisão (tudo em pixels da tela de 1280x720, que o App encaixa em qualquer janela ou tela cheia):

    corpo = area_util()                                   # a tela sem o cabeçalho e a faixa de baixo
    esquerda, meio, direita = colunas(corpo, [300, None, 290])    # None = o que sobrar
    cima, baixo = linhas(meio, [None, 56])
    for celula in grade(area, colunas=2, altura=150): ...

Conferência (testes e ferramentas/previa_telas.py): com ui.desenho.REGISTRO ligado, a tela anota
cada texto e moldura que desenha; conferir() devolve os problemas encontrados:

    - "fora da tela": texto ou moldura saindo da tela;
    - "vaza": texto ou moldura saindo da moldura em que está (a última desenhada embaixo dele);
    - "sobrepõe": duas molduras irmãs (dentro da mesma moldura) se cruzando.

O que é desenhado com recorte (painel rolável) conta só a parte visível.
"""

import pygame

from ui import tema

TOLERANCIA = 3                    # contorno do texto e cantos das molduras
CABECALHO = 68                    # faixa do título (y de 8 a 60) + respiro
RODAPE = 64                       # faixa dos botões de baixo


def area_util(cabecalho=CABECALHO, rodape=RODAPE, margem=16):
    """A tela inteira sem o cabeçalho e o rodapé."""
    return pygame.Rect(margem, cabecalho, tema.LARGURA - 2 * margem, tema.ALTURA - cabecalho - rodape)


def _dividir(total, medidas, espaco):
    """Tamanhos fixos ficam; os None dividem o que sobrar."""
    livres = medidas.count(None)
    sobra = total - sum(m for m in medidas if m is not None) - espaco * (len(medidas) - 1)
    flexivel = sobra // livres if livres else 0
    return [m if m is not None else flexivel for m in medidas]


def colunas(rect, larguras, espaco=12):
    """Divide o retângulo em colunas lado a lado. larguras: números ou None (= o que sobrar)."""
    rect = pygame.Rect(rect)
    x, saida = rect.x, []
    for largura in _dividir(rect.width, list(larguras), espaco):
        saida.append(pygame.Rect(x, rect.y, largura, rect.height))
        x += largura + espaco
    return saida


def linhas(rect, alturas, espaco=12):
    """Divide o retângulo em faixas, de cima para baixo. alturas: números ou None (= o que sobrar)."""
    rect = pygame.Rect(rect)
    y, saida = rect.y, []
    for altura in _dividir(rect.height, list(alturas), espaco):
        saida.append(pygame.Rect(rect.x, y, rect.width, altura))
        y += altura + espaco
    return saida


def grade(rect, quantidade, colunas=2, altura=100, espaco=12):
    """Células de uma grade com 'colunas' colunas e altura fixa (podem passar do fundo: use um painel rolável)."""
    rect = pygame.Rect(rect)
    largura = (rect.width - espaco * (colunas - 1)) // colunas
    return [pygame.Rect(rect.x + (i % colunas) * (largura + espaco), rect.y + (i // colunas) * (altura + espaco),
                        largura, altura) for i in range(quantidade)]


def altura_da_grade(quantidade, colunas=2, altura=100, espaco=12):
    """Altura total que grade() ocupa (para o painel rolável saber até onde rolar)."""
    fileiras = (quantidade + colunas - 1) // colunas
    return max(0, fileiras * (altura + espaco) - espaco)


# ============================================================
# CONFERÊNCIA
# ============================================================

class Problema:
    def __init__(self, tipo, rect, conteudo, dentro=None):
        self.tipo = tipo
        self.rect = rect
        self.conteudo = conteudo
        self.dentro = dentro

    def __repr__(self):
        onde = f" em {tuple(self.dentro)}" if self.dentro is not None else ""
        return f"<{self.tipo}: {self.conteudo!r} {tuple(self.rect)}{onde}>"


def _visivel(rect, recorte):
    return rect.clip(recorte) if recorte is not None else rect


def _contem(fora, dentro, folga=TOLERANCIA):
    return fora.inflate(2 * folga, 2 * folga).contains(dentro)


def conferir(registro, superficie, ignorar=()):
    """Problemas de layout do que foi desenhado na 'superficie' (a tela de 1280x720).

    registro: lista de ui.desenho.REGISTRO. ignorar: textos que podem passar (ex.: decoração de propósito).
    Uma janela modal (diálogo) escurece a tela: o que vem depois dela é conferido à parte.
    """
    camadas, atual = [], []
    for entrada in registro:
        if entrada[0] == "modal":
            camadas.append(atual)
            atual = []
        else:
            atual.append(entrada)
    camadas.append(atual)
    return [p for camada in camadas for p in _conferir_camada(camada, superficie, ignorar)]


def _conferir_camada(registro, superficie, ignorar):
    tela = superficie.get_rect()
    itens = []
    for tipo, rect, recorte, alvo, conteudo in registro:
        if alvo is not superficie:
            continue
        visivel = _visivel(rect, None if recorte == tela else recorte)   # recorte = a tela toda: não é rolagem
        if visivel.width <= 0 or visivel.height <= 0:
            continue                                     # todo escondido pelo recorte (rolado para fora)
        itens.append((tipo, rect, visivel, conteudo))
    problemas = []
    molduras = []                                        # (índice, rect visível, tipo) já desenhadas
    for indice, (tipo, rect, visivel, conteudo) in enumerate(itens):
        if conteudo in ignorar:
            continue
        if not _contem(tela, visivel):
            problemas.append(Problema("fora da tela", visivel, conteudo))
        centro = visivel.center
        dono = next((m for _, m, t in reversed(molduras) if m.collidepoint(centro) and m != visivel), None)
        if dono is not None and not _contem(dono, visivel):
            problemas.append(Problema("vaza", visivel, conteudo, dono))
        if tipo in ("painel", "camada"):
            molduras.append((indice, visivel, tipo))
    # textos que se cruzam (o contorno de 2 px de linhas seguidas não conta)
    textos = [(visivel, conteudo) for tipo, _, visivel, conteudo in itens if tipo == "texto" and conteudo.strip()
              and conteudo not in ignorar]
    for a in range(len(textos)):
        for b in range(a + 1, len(textos)):
            cruzam = textos[a][0].clip(textos[b][0])
            if cruzam.width > 6 and cruzam.height > 6:
                problemas.append(Problema("texto sobre texto", cruzam, f"{textos[a][1]} | {textos[b][1]}"))
    # molduras irmãs (mesmo dono) que se cruzam sem uma conter a outra
    paineis = [(i, m) for i, m, t in molduras if t == "painel"]
    for a in range(len(paineis)):
        for b in range(a + 1, len(paineis)):
            ra, rb = paineis[a][1], paineis[b][1]
            cruzam = ra.clip(rb)
            if cruzam.width > TOLERANCIA * 2 and cruzam.height > TOLERANCIA * 2 \
                    and not ra.contains(rb) and not rb.contains(ra):
                problemas.append(Problema("sobrepõe", cruzam, "molduras", ra))
    return problemas
