"""Peças de desenho da interface: textos, molduras, barras, pontos de energia e ícones.

As molduras e barras são desenhadas em tamanho pequeno, pixel por pixel,
e depois ampliadas 2x sem suavizar (fica com cara de pixel art).
"""

import math

import pygame

from ui import tema
from ui.tema import PIXEL

_cache = {}

# Conferência de layout (testes e ferramentas/previa_telas.py): quando for uma lista, texto() e painel()
# anotam o que desenharam como (tipo, retângulo, recorte, superfície, conteúdo). Ver ui/layout.py.
REGISTRO = None


def anotar(tipo, rect, tela, conteudo=""):
    """Guarda um desenho no REGISTRO (se a conferência estiver ligada)."""
    if REGISTRO is not None:
        REGISTRO.append((tipo, pygame.Rect(rect), tela.get_clip(), tela, conteudo))


def guardar(chave, criar):
    if chave not in _cache:
        _cache[chave] = criar()
    return _cache[chave]


def ampliar(imagem, vezes=PIXEL):
    return pygame.transform.scale(imagem, (imagem.get_width() * vezes, imagem.get_height() * vezes))


# ============================================================
# TEXTOS
# ============================================================

def sem_ligaduras(conteudo):
    """A Pixelify junta "fi" e "fl" num símbolo só (parece "ñ"): um caractere invisível separa as letras.
    A fonte arredondada não tem esse problema (e o caractere invisível viraria um quadradinho nela)."""
    if not tema.LIGADURAS:
        return conteudo
    return conteudo.replace("fi", "f‌i").replace("fl", "f‌l")


def render(conteudo, fonte, cor, contorno=True):
    """Imagem do texto com contorno escuro (fica legível sobre qualquer fundo)."""
    def criar():
        limpo = sem_ligaduras(conteudo)
        frente = fonte.render(limpo, tema.SUAVE, cor)
        if not contorno:
            return frente
        escuro = fonte.render(limpo, tema.SUAVE, (8, 5, 10))
        imagem = pygame.Surface((frente.get_width() + 4, frente.get_height() + 4), pygame.SRCALPHA)
        for dx, dy in ((0, 2), (2, 0), (4, 2), (2, 4), (4, 4)):
            imagem.blit(escuro, (dx, dy))
        imagem.blit(frente, (2, 2))
        return imagem
    return guardar(("texto", conteudo, id(fonte), cor, contorno), criar)


def texto(tela, conteudo, fonte, cor, posicao, ancora="topleft", contorno=True, alfa=None):
    """Desenha o texto. ancora: "topleft", "center", "midtop", "topright"... Devolve o retângulo."""
    imagem = render(str(conteudo), fonte, cor, contorno)
    rect = imagem.get_rect(**{ancora: posicao})
    if alfa is not None:
        imagem = imagem.copy()
        imagem.set_alpha(alfa)
    tela.blit(imagem, rect)
    anotar("texto", rect, tela, str(conteudo))
    return rect


def quebrar(conteudo, fonte, largura):
    """Divide o texto em linhas que cabem na largura (medida exata: ver ui/texto.py)."""
    from ui.texto import quebrar_linhas
    return quebrar_linhas(conteudo, fonte, largura)


def paragrafo(tela, conteudo, fonte, cor, posicao, largura, espaco=2, maximo_linhas=None, encolher=False):
    """Texto com quebra de linha numa largura fixa (usa a CaixaTexto). Devolve o y logo abaixo do texto.

    maximo_linhas: com mais linhas, encolhe a fonte (encolher=True) ou corta com "...".
    """
    from ui.texto import CaixaTexto
    caixa = CaixaTexto(pygame.Rect(posicao[0], posicao[1], largura, 10_000), fonte, cor, espaco=espaco,
                       maximo_linhas=maximo_linhas, fontes=None if encolher else [fonte])
    return caixa.desenhar(tela, conteudo)


# ============================================================
# MOLDURAS GÓTICAS
# ============================================================

def moldura(largura, altura, estilo="ferro"):
    """Moldura de madeira entalhada com filete dourado (ui/molduras.py) no tamanho pedido (em pixels da tela)."""
    from ui.molduras import moldura_pequena
    largura, altura = max(12, int(largura)), max(12, int(altura))

    def criar():
        pequena = moldura_pequena(largura // PIXEL, altura // PIXEL, estilo)
        grande = ampliar(pequena)
        if (largura, altura) != grande.get_size():
            final = pygame.Surface((largura, altura), pygame.SRCALPHA)
            final.fill((0, 0, 0, 0))
            final.blit(pygame.transform.scale(grande, (largura, altura)), (0, 0))
            return final
        return grande
    return guardar(("moldura", largura, altura, estilo), criar)


def painel(tela, rect, estilo="ferro"):
    rect = pygame.Rect(rect)
    tela.blit(moldura(rect.width, rect.height, estilo), rect.topleft)
    anotar("painel", rect, tela, estilo)
    return rect


def desenhar_placa(tela, centro, conteudo, fonte=None, cor=tema.OURO_CLARO, largura_maxima=None):
    """Placa dourada de título (com pontas) e o texto dentro dela. Devolve o retângulo da placa."""
    from ui.molduras import placa
    from ui.texto import largura_do_texto, linha
    fonte = fonte or tema.normal()
    altura = fonte.get_height() + 10
    largura = largura_do_texto(conteudo, fonte) + 44
    if largura_maxima:
        largura = min(largura, largura_maxima)
    largura, altura = largura + largura % 2, altura + altura % 2
    imagem = guardar(("placa", largura, altura), lambda: ampliar(placa(largura // PIXEL, altura // PIXEL)))
    rect = imagem.get_rect(center=centro)
    tela.blit(imagem, rect)
    linha(tela, conteudo, fonte, cor, (rect.centerx, rect.centery - 1), rect.width - 36, "center")
    return rect


def titulo_de_painel(tela, rect, conteudo, cor=tema.OURO_CLARO):
    """Placa dourada com o título, no alto do painel. Devolve o y onde o conteúdo começa."""
    rect = pygame.Rect(rect)
    altura = tema.normal().get_height() + 10
    placa = desenhar_placa(tela, (rect.centerx, rect.y + 8 + altura // 2), conteudo, tema.normal(), cor,
                           rect.width - 32)
    return placa.bottom + 8


def losango(tela, centro, raio, cor):
    x, y = centro
    pygame.draw.polygon(tela, (8, 6, 10), [(x, y - raio - 2), (x + raio + 2, y), (x, y + raio + 2), (x - raio - 2, y)])
    pygame.draw.polygon(tela, cor, [(x, y - raio), (x + raio, y), (x, y + raio), (x - raio, y)])


# ============================================================
# BARRAS
# ============================================================

def barra(tela, rect, fracao, cor, atrasada=None, cor_atraso=tema.VIDA_ATRASO, marcas=10, texto_dentro=None):
    """Barra ornamentada: sulco escuro, preenchimento com brilho, parte "atrasada" e ponteiras de ferro."""
    rect = pygame.Rect(rect)
    fracao = max(0.0, min(1.0, fracao))
    pygame.draw.rect(tela, (6, 4, 8), rect.inflate(4, 4))
    pygame.draw.rect(tela, tema.FERRO_ESCURO, rect.inflate(2, 2))
    pygame.draw.rect(tela, (18, 12, 18), rect)

    if atrasada is not None and atrasada > fracao:
        largura = int(rect.width * min(1.0, atrasada))
        pygame.draw.rect(tela, cor_atraso, (rect.x, rect.y, largura, rect.height))

    largura = int(rect.width * fracao)
    if largura > 0:
        pygame.draw.rect(tela, cor, (rect.x, rect.y, largura, rect.height))
        clara = tuple(min(255, c + 60) for c in cor)
        escura = tuple(c // 2 for c in cor)
        pygame.draw.rect(tela, clara, (rect.x, rect.y, largura, max(1, rect.height // 4)))
        pygame.draw.rect(tela, escura, (rect.x, rect.bottom - max(1, rect.height // 5), largura, max(1, rect.height // 5)))

    if marcas and rect.width > 60:
        for i in range(1, marcas):
            x = rect.x + rect.width * i // marcas
            pygame.draw.line(tela, (10, 6, 10), (x, rect.y + rect.height // 2), (x, rect.bottom - 1))

    # Ponteiras de ferro
    for x in (rect.x - 4, rect.right):
        pygame.draw.rect(tela, (6, 4, 8), (x - 1, rect.y - 3, 6, rect.height + 6))
        pygame.draw.rect(tela, tema.FERRO, (x, rect.y - 2, 4, rect.height + 4))
        pygame.draw.rect(tela, tema.FERRO_CLARO, (x, rect.y - 2, 4, 2))

    if texto_dentro:
        texto(tela, texto_dentro, tema.mini(), tema.TEXTO, rect.center, "center")
    return rect


def pontos_de_energia(tela, posicao, atual, maximo, tamanho=6, cor=tema.ENERGIA):
    """Losangos de energia (cheios e vazios)."""
    x, y = posicao
    for i in range(maximo):
        centro = (x + i * (tamanho * 2 + 3) + tamanho, y + tamanho)
        if i < atual:
            losango(tela, centro, tamanho, cor)
            pygame.draw.line(tela, tema.ENERGIA_CLARA, (centro[0] - 1, centro[1] - tamanho + 2), (centro[0] - 1, centro[1] - 1))
        else:
            losango(tela, centro, tamanho, (34, 30, 44))
    return x + maximo * (tamanho * 2 + 3)


def estrelas(tela, posicao, quantidade, maximo=5, tamanho=7):
    """Estrelas de dificuldade (pixeladas)."""
    x, y = posicao
    for i in range(maximo):
        cor = tema.OURO if i < quantidade else (50, 44, 54)
        cx = x + i * (tamanho * 2 + 2) + tamanho
        pontos = []
        for k in range(10):
            raio = tamanho if k % 2 == 0 else tamanho * 0.45
            angulo = -math.pi / 2 + k * math.pi / 5
            pontos.append((cx + math.cos(angulo) * raio, y + tamanho + math.sin(angulo) * raio))
        pygame.draw.polygon(tela, (8, 6, 10), [(px + 1, py + 1) for px, py in pontos])
        pygame.draw.polygon(tela, cor, pontos)
    return x + maximo * (tamanho * 2 + 2)


# ============================================================
# ÍCONES DE STATUS (pixel art desenhada por código)
# ============================================================

DESENHOS_DE_STATUS = {
    # chave: (cor de fundo, cor do símbolo, símbolo 7x7 com "#")
    "sangramento": ((90, 14, 20), (230, 70, 60), ["...#...", "..###..", ".#####.", ".#####.", "#######", ".#####.", "..###.."]),
    "veneno": ((30, 60, 20), (160, 240, 90), [".#...#.", "..###..", ".#.#.#.", ".#####.", "..###..", ".#.#.#.", "#.....#"]),
    "queimadura": ((80, 30, 10), (250, 160, 50), ["...#...", "..##...", "..###..", ".####..", ".#####.", "#######", ".#####."]),
    "congelado": ((20, 50, 80), (190, 236, 255), ["...#...", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "...#..."]),
    "atordoado": ((70, 60, 20), (250, 230, 110), ["#.....#", ".#...#.", "...#...", "..###..", "...#...", ".#...#.", "#.....#"]),
    "amaldicoado": ((50, 20, 60), (200, 130, 240), ["..###..", ".#####.", "##.#.##", "#######", ".#####.", "..#.#..", "..#.#.."]),
    "enfraquecido": ((50, 40, 40), (180, 160, 150), ["...#...", "...#...", "...#...", "#..#..#", ".#.#.#.", "..###..", "...#..."]),
    "marcado": ((80, 20, 20), (250, 120, 100), ["..###..", ".#...#.", "#..#..#", "#.###.#", "#..#..#", ".#...#.", "..###.."]),
    "lento": ((40, 40, 60), (150, 160, 200), ["#######", ".#...#.", "..#.#..", "...#...", "..#.#..", ".#...#.", "#######"]),
    "fortalecido": ((80, 20, 20), (250, 110, 90), ["...#...", "..###..", ".#####.", "...#...", "...#...", "...#...", "...#..."]),
    "inspirado": ((70, 60, 20), (255, 220, 120), ["...#...", "...#...", "#######", ".#####.", "..###..", ".##.##.", "#.....#"]),
    "evasivo": ((30, 50, 60), (160, 230, 240), ["#......", ".##....", "...##..", ".....##", "...##..", ".##....", "#......"]),
    "protegido": ((50, 50, 70), (200, 200, 230), ["#######", "#.....#", "#.###.#", "#.###.#", ".#.#.#.", "..#.#..", "...#..."]),
    "energizado": ((20, 50, 80), (120, 200, 255), ["....##.", "...##..", "..##...", ".#####.", "...##..", "..##...", ".##...."]),
    "regeneracao": ((20, 60, 30), (130, 240, 130), ["...#...", "...#...", "...#...", "#######", "...#...", "...#...", "...#..."]),
    "escudo": ((50, 50, 70), (180, 200, 240), [".#####.", "#######", "#######", "#######", ".#####.", "..###..", "...#..."]),
    "provocacao": ((80, 40, 10), (250, 170, 70), ["#.....#", "##...##", ".#####.", "..###..", ".#####.", "##...##", "#.....#"]),
    "furtivo": ((25, 20, 35), (140, 120, 170), ["..###..", ".#####.", "##.#.##", "#######", "#######", "#.#.#.#", "......."]),
    "contra_ataque": ((60, 50, 60), (230, 220, 230), ["#.....#", ".#...#.", "..#.#..", "...#...", "..#.#..", ".#...#.", "#.....#"]),
    "espinhos": ((30, 50, 20), (170, 220, 100), ["#..#..#", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "#..#..#"]),
    "amedrontado": ((50, 30, 60), (220, 200, 240), ["..###..", ".#####.", "#.#.#.#", "#######", "#.###.#", ".#...#.", "..###.."]),
    "enraizado": ((40, 24, 16), (170, 110, 70), ["...#...", "..##...", "...#...", "..#.#..", ".#..#..", "#...#.#", "#..#..#"]),
    "enlameado": ((40, 34, 20), (140, 120, 70), [".......", "..###..", ".#####.", "#######", "#.###.#", "##.#.##", "#######"]),
    "cego": ((30, 30, 30), (220, 220, 220), [".......", ".#####.", "#.....#", "#######", "#.....#", ".#####.", "......."]),
    "iluminado": ((70, 60, 20), (255, 230, 120), ["...#...", ".#.#.#.", "..###..", "###.###", "..###..", ".#.#.#.", "...#..."]),
    "guarda_erguida": ((60, 56, 50), (230, 220, 190), ["#######", "#.....#", "#.###.#", "#.###.#", ".#.#.#.", "..#.#..", "...#..."]),
    "arma_desgastada": ((50, 40, 30), (190, 140, 100), ["......#", ".....#.", "....#..", "..##...", ".#.#...", "#...#..", "......."]),
    "afiado": ((60, 60, 70), (230, 235, 250), ["......#", ".....##", "....##.", "...##..", ".###...", "##.....", "#......"]),
    "aquecido": ((70, 30, 10), (255, 170, 80), ["...#...", "..##...", "..###..", ".####..", ".#####.", "#######", ".#####."]),
    "escudo_elemental": ((30, 40, 70), (150, 220, 255), ["..###..", ".#####.", "##.####", "###.###", ".##.##.", "..###..", "...#..."]),
    "fase_do_chefe": ((70, 20, 30), (250, 200, 110), ["#.#.#.#", "#######", "#######", ".......", ".#####.", ".#.#.#.", ".#####."]),
    "encharcado": ((20, 44, 40), (110, 200, 150), ["...#...", "..###..", "..###..", ".......", "#.#.#.#", ".#.#.#.", "#######"]),
    "nadando": ((20, 44, 40), (170, 230, 170), [".......", "..##..#", ".####.#", "#.#####", ".####.#", "..##..#", "#.#.#.#"]),
    "escuridao": ((14, 12, 24), (190, 180, 230), ["..###..", ".##....", "##.....", "##.....", "##.....", ".##....", "..###.."]),
    "peste": ((40, 46, 14), (196, 214, 92), ["##...##", "#######", "#.###.#", "#######", ".#####.", "..###..", "...#..."]),
    "na_superficie": ((20, 44, 40), (150, 220, 200), ["...#...", "..#.#..", ".#...#.", ".......", "#.#.#.#", ".#.#.#.", "......."]),
    "definhando": ((40, 34, 24), (190, 170, 120), ["#.....#", ".#...#.", "..#.#..", "...#...", "...#...", "..###..", ".#####."]),
    "corneta": ((60, 50, 30), (236, 220, 170), ["......#", ".....##", "....###", "#.#####", "#######", "#.#####", "......."]),
    "encantado": ((50, 24, 60), (236, 170, 255), ["...##..", "...#.#.", "...#..#", "...#...", ".###...", "####...", ".##...."]),
    "edito_sem_cura": ((90, 20, 26), (236, 214, 160), ["######.", ".#...#.", ".#.#.#.", ".#####.", ".#.#.#.", ".#...#.", "######."]),
    "edito_sem_magia": ((90, 20, 26), (236, 214, 160), ["######.", ".#...#.", ".#.#.#.", ".##.##.", ".#.#.#.", ".#...#.", "######."]),
    "edito_sem_atacar": ((90, 20, 26), (236, 214, 160), ["######.", ".#...#.", ".##.##.", ".#.#.#.", ".##.##.", ".#...#.", "######."]),
    "edito_ajoelhem_se": ((90, 20, 26), (236, 214, 160), ["######.", ".#...#.", ".#.#.#.", ".#...#.", ".#.#.#.", ".#...#.", "######."]),
    "cofre_real": ((70, 52, 20), (240, 200, 90), ["..###..", ".#...#.", "#.###.#", "#.#...#", "#.###.#", ".#...#.", "..###.."]),
    "atras_da_roda": ((40, 30, 40), (170, 130, 128), ["..###..", ".#...#.", "#..#..#", "#.###.#", "#..#..#", ".#...#.", "..###.."]),
    "no_fechado": ((50, 24, 30), (200, 150, 146), ["#.#.#.#", ".#####.", "##.#.##", "#.###.#", "##.#.##", ".#####.", "#.#.#.#"]),
    "silenciado": ((40, 40, 60), (220, 220, 240), ["#.....#", ".#...#.", "..###..", "..#.#..", "..###..", ".#...#.", "#.....#"]),
    "furia_da_roda": ((90, 20, 20), (255, 120, 90), ["#..#..#", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "#..#..#"]),
    "no_trono": ((70, 20, 30), (240, 200, 90), ["#.#.#..", "#####..", ".###...", "#####.#", "#...#.#", "#######", "#.....#"]),
}


def icone_status(chave, vezes=2):
    """Ícone 9x9 (ampliado) do status."""
    def criar():
        fundo, frente, desenho = DESENHOS_DE_STATUS.get(chave, ((60, 60, 60), (220, 220, 220), ["#######"] * 7))
        pequena = pygame.Surface((9, 9), pygame.SRCALPHA)
        pequena.fill((8, 6, 10))
        pequena.fill(fundo, (1, 1, 7, 7))
        for y, linha in enumerate(desenho):
            for x, c in enumerate(linha):
                if c == "#" and 0 <= x < 7:
                    pequena.set_at((x + 1, y + 1), frente)
        return ampliar(pequena, vezes)
    return guardar(("icone_status", chave, vezes), criar)


def escurecer_tela(tela, alfa=150, cor=(0, 0, 0)):
    camada = guardar(("escuro", tela.get_size(), alfa, cor), lambda: _camada(tela.get_size(), (*cor, alfa)))
    tela.blit(camada, (0, 0))


def _camada(tamanho, cor):
    camada = pygame.Surface(tamanho, pygame.SRCALPHA)
    camada.fill(cor)
    return camada


def vinheta(tamanho, forca=200):
    """Bordas escuras (dá um ar de quadro antigo)."""
    def criar():
        largura, altura = tamanho
        pequena = pygame.Surface((largura // 8, altura // 8), pygame.SRCALPHA)
        cx, cy = pequena.get_width() / 2, pequena.get_height() / 2
        for y in range(pequena.get_height()):
            for x in range(pequena.get_width()):
                d = ((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2
                pequena.set_at((x, y), (0, 0, 0, int(max(0, min(1, (d - 0.45) / 0.8)) * forca)))
        return pygame.transform.smoothscale(pequena, tamanho)
    return guardar(("vinheta", tamanho, forca), criar)
