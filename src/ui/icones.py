"""Ícones em pixel art: itens e tipos de encontro.

Itens: os ícones 20x20 da FORJA DE ITENS (assets/itens_macabros/<chave>.png, gerados por
ferramentas/sprites_macabros/gerar_itens.py). Item sem ícone forjado usa o desenho 12x12 abaixo.

Cada desenho 12x12 é uma grade de letras:
    "#" contorno escuro   "a" cor principal   "b" luz   "c" sombra   "d" detalhe   "." vazio
A cor principal muda de item para item (poção vermelha, azul, verde...).
"""

import os

import pygame

from caminhos import CAMINHOS
from ui import tema
from ui.desenho import guardar

PASTA_ICONES_FORJADOS = CAMINHOS.asset("itens_macabros")
TAMANHO_FORJADO = 20

DESENHOS = {
    "frasco": ["....###.....", "....#d#.....", "....#d#.....", "...#bab#....", "..#baaaa#...", ".#baaaaaa#..",
               ".#aaaaaaa#..", ".#aaaaaac#..", ".#caaaacc#..", "..#ccccc#...", "...#####....", "............"],
    "pao": ["............", "............", "...######...", "..#bbbbbb#..", ".#baaaaaab#.", ".#aadaadaa#.",
            ".#aaaaaaaa#.", ".#caaaaaac#.", "..#cccccc#..", "...######...", "............", "............"],
    "bomba": [".......#d...", "......#.d...", ".....##.....", "...#####....", "..#baaaa#...", ".#baaaaaa#..",
              ".#aaaaaaa#..", ".#aaaaaaa#..", ".#caaaaac#..", "..#ccccc#...", "...#####....", "............"],
    "pergaminho": ["............", ".##########.", "#bbbbbbbbbb#", "#c########c#", ".#aaaaaaaa#.", ".#adddddda#.",
                   ".#aaaaaaaa#.", ".#adddddda#.", ".#aaaaaaaa#.", "#c########c#", "#bbbbbbbbbb#", ".##########."],
    "espada": ["..........##", ".........#b#", "........#ba#", ".......#ba#.", "......#ba#..", ".....#ba#...",
               ".##.#ba#....", ".#d#ba#.....", "..#dc#......", ".#d##d#.....", "#d#..#d#....", "##....##...."],
    "adaga": ["............", "............", ".......##...", "......#b#...", ".....#ba#...", "....#ba#....",
              "...#ba#.....", ".##ba#......", ".#dd#.......", "#d##d#......", "##..##......", "............"],
    "machado": ["....###.....", "...#bbb#....", "..#baaab#...", "..#aaaaa#...", "..#caaa##...", "...#cc#d#...",
                "....##.d#...", ".......d#...", "......#d#...", "......#d#...", ".....#d#....", ".....##....."],
    "martelo": ["..#######...", ".#bbbbbbb#..", ".#aaaaaaa#..", ".#ccccccc#..", "..####d##...", ".....#d#....",
                ".....#d#....", ".....#d#....", ".....#d#....", ".....#d#....", ".....#d#....", ".....###...."],
    "arco": ["...##.......", "..#b.#......", "..#a..#.....", ".#a....#....", ".#a.....#...", ".#a.....d#..",
             ".#a.....d#..", ".#a.....#...", ".#a....#....", "..#a..#.....", "..#c.#......", "...##......."],
    "cajado": [".........##.", "........#bb#", "........#ab#", ".........##.", "........#d#.", ".......#d#..",
               "......#d#...", ".....#d#....", "....#d#.....", "...#d#......", "..#d#.......", "..##........"],
    "foice": ["...######...", "..#bbbbbb#..", ".#a#####aa#.", "#a#.....#a#.", "##......#d#.", ".......#d#..",
              "......#d#...", ".....#d#....", "....#d#.....", "...#d#......", "..#d#.......", "..##........"],
    "alaude": [".........##.", "........#d#.", ".......#d#..", "......#d#...", "...####d....", "..#bbaa#....",
               ".#baadaa#...", ".#aadddaa#..", ".#aaadaac#..", "..#aaacc#...", "...#####....", "............"],
    "armadura": ["............", ".###....###.", "#bba#..#abb#", "#baaa##aaab#", ".#aaaaaaaa#.", ".#aadaadaa#.",
                 ".#aaaaaaaa#.", ".#aaadaaaa#.", ".#caaaaaac#.", "..#cccccc#..", "...######...", "............"],
    "manto": ["....####....", "...#bbbb#...", "..#baaaab#..", "..#a#..#a#..", ".#aa#..#aa#.", ".#aaa##aaa#.",
              "#baaaaaaaab#", "#aaaaaaaaaa#", "#aaaaaaaaaa#", "#caacaacaac#", ".##########.", "............"],
    "anel": ["............", "....####....", "...#bddb#...", "..#d####d#..", ".#aa#..#aa#.", ".#a#....#a#.",
             ".#a#....#a#.", ".#c#....#c#.", "..#cc##cc#..", "...######...", "............", "............"],
    "pingente": ["..#......#..", "...#....#...", "....#..#....", ".....##.....", "....#bb#....", "...#baab#...",
                 "..#baaaab#..", "..#aadaaa#..", "..#caaaac#..", "...#caac#...", "....#cc#....", ".....##....."],
    "osso": ["............", ".##......##.", "#bb#....#bb#", "#bab####bab#", ".#aaaaaaaa#.", ".#aaaaaaaa#.",
             ".#caaaaaac#.", "#cac####cac#", "#cc#....#cc#", ".##......##.", "............", "............"],
    "presa": ["............", "...######...", "..#bbbbbb#..", "..#baaaaa#..", "...#aaaa#...", "...#aaac#...",
              "....#aac#...", "....#ac#....", ".....#c#....", ".....##.....", "............", "............"],
    "olho": ["............", "............", "...######...", "..#bbbbbb#..", ".#baa##aab#.", "#baa#dd#aab#",
             "#aaa#dd#aaa#", ".#caa##aac#.", "..#cccccc#..", "...######...", "............", "............"],
    "planta": [".....##.....", "....#bb#....", "...#baab#...", "..#baaaab#..", "..#aaaaaa#..", "...#aac#....",
               "##..#d#..##.", "#a#.#d#.#a#.", ".#a##d##a#..", "..##ddd##...", "....#d#.....", "....###....."],
    "gota": [".....##.....", ".....##.....", "....#ba#....", "....#ba#....", "...#baaa#...", "..#baaaaa#..",
             "..#aaaaaa#..", ".#aaaaaaaa#.", ".#caaaaaac#.", "..#caaaac#..", "...######...", "............"],
    "minerio": ["............", "....####....", "..##bbaa##..", ".#bbaaaaaa#.", ".#baadaaaa#.", "#baaaaadaa#.",
                "#aaaaaaaaac#", "#aadaaaaacc#", ".#caaaaccc#.", "..#cccccc#..", "...######...", "............"],
    "escama": ["............", "...######...", "..#bbbbbb#..", ".#baaaaaab#.", ".#aaddddaa#.", ".#aaaaaaaa#.",
               ".#aadddda#..", "..#aaaaaa#..", "...#aaac#...", "....#cc#....", ".....##.....", "............"],
    "fio": ["............", "..########..", "..#dddddd#..", "...#bbbb#...", "...#aaaa#...", "...#abab#...",
            "...#aaaa#...", "...#baba#...", "...#aaaa#...", "..#dddddd#..", "..########..", "............"],
    "alma": ["....#..#....", "...#b##b#...", "..#bab#ba#..", "..#aaabaa#..", ".#aaaaaaaa#.", ".#aabddbaa#.",
             ".#aadddda#..", ".#aaabbaaa#.", "..#caaaac#..", "...#cccc#...", "....####....", "............"],
    "bola": ["............", "....####....", "...#bbaa#...", "..#baaaaa#..", ".#baaaaaaa#.", ".#aaaaaaaa#.",
             ".#aaaaaaac#.", ".#aaaaaacc#.", "..#aaaccc#..", "...#cccc#...", "....####....", "............"],
    "bolsa": ["............", "....#dd#....", "...#d##d#...", "....####....", "...#bbaa#...", "..#baaaaa#..",
              ".#baaaaaaa#.", ".#aaaaaaaa#.", ".#caaaaaac#.", "..#cccccc#..", "...######...", "............"],
}

# Ícones dos encontros
DESENHOS_DE_ENCONTRO = {
    "espadas": ["##........##", "#b#......#b#", ".#a#....#a#.", "..#a#..#a#..", "...#a##a#...", "....#aa#....",
                "....#aa#....", "...#d##d#...", "..#d#..#d#..", ".#d#....#d#.", "#d#......#d#", "##........##"],
    "horda": ["............", ".###....###.", "#bab#..#bab#", "#d#d#..#d#d#", ".###.##.###.", "....#bb#....",
              "...#babb#...", "...#d#d##...", "....####....", "............", "............", "............"],
    "caveira": ["...######...", "..#bbbbbb#..", ".#baaaaaab#.", ".#aaaaaaaa#.", ".#a##aa##a#.", ".#a##aa##a#.",
                ".#aaaa#aaa#.", "..#aa##aa#..", "..#a#a#a#..", "...#a#a#...", "....###.....", "............"],
    "coroa": ["............", "#...#..#...#", "##.##..##.##", "#b#b#..#b#b#", "#bab#bb#bab#", "#aaaaaaaaaa#",
              "#adaadaadaa#", "#aaaaaaaaaa#", "#cccccccccc#", "############", "............", "............"],
    "chifres": ["#..........#", "#b#......#b#", ".#a#....#a#.", ".#a#....#a#.", "..#a####a#..", "..#aaaaaa#..",
                ".#a##aa##a#.", ".#a##aa##a#.", ".#aaaaaaaa#.", "..#aa##aa#..", "...#aaaa#...", "....####...."],
    "interrogacao": ["...######...", "..#bbbbbb#..", ".#ba####ab#.", ".#a#....#a#.", "......#aa#..", ".....#aa#...",
                     "....#aa#....", "....#aa#....", ".....##.....", "....#bb#....", "....#aa#....", ".....##....."],
    "livro": ["............", ".####..####.", "#bbbb##bbbb#", "#adda##adda#", "#aaaa##aaaa#", "#adda##adda#",
              "#aaaa##aaaa#", "#adda##adda#", "#aaaa##aaaa#", "#cccc##cccc#", ".##########.", "............"],
    "moeda": ["............", "...######...", "..#bbbbbb#..", ".#baaaaaab#.", ".#aaddddaa#.", ".#aadaaaaa#.",
              ".#aaddddaa#.", ".#aaaaadaa#.", ".#caddddac#.", "..#cccccc#..", "...######...", "............"],
    "altar": ["....####....", "....#bb#....", ".####bb####.", ".#bbbbbbbb#.", ".####aa####.", "....#aa#....",
              "....#aa#....", "..########..", ".#bbbbbbbb#.", ".#aaaaaaaa#.", ".#cccccccc#.", ".##########."],
    "cranio": ["............", "...######...", "..#aaaaaa#..", ".#aaaaaaaa#.", ".#d##aa##d#.", ".#a##aa##a#.",
               ".#aaa##aaa#.", "..#a####a#..", "..#a#a#a#...", "...#####....", "..d......d..", ".d........d."],
    "fogueira": ["....#.......", "...#b#..#...", "...#ba##b#..", "..#baab#a#..", "..#aaaaaaa#.", ".#aaaddaaa#.",
                 ".#aaddddaa#.", "..#adddda#..", ".##########.", "#cc#cc#cc#c#", ".##########.", "............"],
    "portal": ["....####....", "...#bbbb#...", "..#b####b#..", ".#b#dddd#b#.", ".#a#dddd#a#.", ".#a#dddd#a#.",
               ".#a#dddd#a#.", ".#a#dddd#a#.", ".#a#dddd#a#.", ".#c######c#.", ".##########.", "............"],
    "chefe": ["#.#.####.#.#", "#d#d#bb#d#d#", "#dddddddddd#", ".#baaaaaab#.", ".#a##aa##a#.", ".#a##aa##a#.",
              ".#aaaa#aaa#.", "..#aa##aa#..", "..#a#a#a#a#.", "...#a#a#a#..", "....#####...", "............"],
}

# Cor principal de cada ícone de encontro
CORES_DE_ENCONTRO = {
    "espadas": (180, 180, 196), "horda": (210, 200, 170), "caveira": (226, 216, 196), "coroa": (232, 186, 80),
    "chifres": (190, 60, 60), "interrogacao": (180, 150, 230), "livro": (150, 100, 70), "moeda": (236, 190, 80),
    "altar": (210, 200, 180), "cranio": (170, 220, 170), "fogueira": (240, 140, 50), "portal": (120, 90, 180),
    "chefe": (226, 210, 190),
}
DETALHE_DE_ENCONTRO = {"espadas": (120, 80, 40), "horda": (40, 20, 20), "caveira": (40, 20, 20), "coroa": (190, 50, 60),
                       "chifres": (250, 220, 120), "livro": (230, 220, 190), "moeda": (150, 100, 30),
                       "cranio": (120, 200, 120), "fogueira": (255, 220, 120), "portal": (40, 20, 60),
                       "chefe": (200, 40, 40)}


def misturar(cor, fator):
    return tuple(max(0, min(255, int(c * fator))) for c in cor)


def pintar(desenho, cor, detalhe, vezes):
    """Transforma a grade de letras numa imagem ampliada."""
    pequena = pygame.Surface((12, 12), pygame.SRCALPHA)
    pequena.fill((0, 0, 0, 0))
    cores = {"#": (12, 8, 14), "a": cor, "b": misturar(cor, 1.35), "c": misturar(cor, 0.6), "d": detalhe}
    for y, linha in enumerate(desenho):
        for x, letra in enumerate(linha):
            if letra in cores:
                pequena.set_at((x, y), cores[letra])
    return pygame.transform.scale(pequena, (12 * vezes, 12 * vezes))


# ---------------- itens ----------------

PALAVRAS = [
    # (pedaço da chave, desenho, cor) — o primeiro que combinar vale
    ("pocao_de_vida", "frasco", (200, 40, 50)), ("pocao_grande", "frasco", (220, 50, 70)),
    ("elixir_de_energia", "frasco", (70, 150, 230)), ("antidoto", "frasco", (110, 200, 90)),
    ("tonico", "frasco", (230, 120, 50)), ("oleo", "frasco", (160, 150, 120)), ("elixir", "frasco", (150, 80, 200)),
    ("pena", "pingente", (240, 120, 50)), ("pao", "pao", (190, 140, 80)), ("ensopado", "pao", (140, 110, 70)),
    ("bomba", "bomba", (70, 66, 80)), ("frasco_de_veneno", "frasco", (120, 200, 60)), ("agua_benta", "frasco", (190, 220, 250)),
    ("po_cegante", "bolsa", (200, 170, 220)), ("pergaminho", "pergaminho", (220, 200, 150)),
    ("arco", "arco", (150, 110, 70)), ("cajado", "cajado", (150, 120, 220)), ("cetro", "cajado", (120, 220, 200)),
    ("martelo", "martelo", (150, 150, 170)), ("machado", "machado", (160, 160, 180)), ("clava", "martelo", (120, 90, 60)),
    ("faca", "adaga", (170, 150, 140)), ("adaga", "adaga", (60, 50, 70)), ("foice", "foice", (170, 190, 150)),
    ("alaude", "alaude", (170, 110, 60)), ("chicote", "fio", (120, 80, 60)), ("presa_do_dragao", "espada", (230, 220, 200)),
    ("manto", "manto", (90, 80, 130)), ("capa", "manto", (140, 30, 40)), ("veste", "manto", (220, 210, 180)),
    ("gibao", "armadura", (140, 100, 60)), ("cota", "armadura", (120, 150, 90)), ("elmo", "armadura", (150, 70, 60)),
    ("armadura_de_ossos", "armadura", (220, 210, 190)), ("placas", "armadura", (200, 150, 80)),
    ("couraca", "armadura", (160, 70, 60)), ("armadura", "armadura", (80, 80, 100)),
    ("anel", "anel", (200, 40, 50)), ("olho", "olho", (230, 220, 200)), ("nariz", "bola", (220, 40, 40)),
    ("colar", "pingente", (220, 210, 190)), ("rosario", "pingente", (150, 30, 40)), ("veu", "manto", (230, 230, 240)),
    ("guizo", "bola", (220, 190, 60)), ("talisma", "pingente", (240, 140, 50)), ("coracao", "gota", (180, 30, 50)),
    ("relicario", "pingente", (220, 190, 120)), ("estandarte", "pergaminho", (170, 40, 40)), ("fios", "fio", (220, 200, 160)),
    ("amuleto", "pingente", (220, 210, 190)),
    ("alma", "alma", (150, 120, 240)), ("osso", "osso", (226, 218, 196)), ("po_de_osso", "bolsa", (220, 210, 190)),
    ("cranio", "alma", (220, 210, 190)), ("medula", "osso", (240, 200, 160)), ("filacteria", "frasco", (120, 230, 200)),
    ("seda", "fio", (230, 230, 230)), ("dente", "presa", (230, 220, 180)), ("presa", "presa", (240, 230, 210)),
    ("ferrao", "presa", (200, 50, 50)), ("unha", "presa", (150, 160, 120)), ("lamina", "presa", (150, 200, 120)),
    ("erva", "planta", (90, 160, 70)), ("cogumelo", "planta", (90, 170, 230)), ("petala", "planta", (230, 120, 200)),
    ("sangue", "gota", (160, 20, 30)), ("tinta", "gota", (210, 40, 40)), ("cera", "gota", (60, 50, 60)),
    ("ferro_negro", "minerio", (70, 70, 90)), ("prata", "minerio", (200, 210, 230)), ("obsidiana", "minerio", (60, 40, 90)),
    ("pedra", "minerio", (130, 120, 140)), ("nucleo", "alma", (100, 200, 230)), ("escama", "escama", (200, 80, 50)),
    ("quitina", "escama", (110, 130, 80)), ("carapaca", "escama", (100, 80, 60)), ("placa", "escama", (200, 150, 80)),
    ("pata", "presa", (150, 90, 60)), ("ovo", "bola", (230, 230, 210)), ("couro", "bolsa", (140, 100, 60)),
    ("trapo", "bolsa", (120, 110, 90)), ("tecido", "bolsa", (200, 60, 60)), ("mola", "fio", (150, 120, 90)),
    ("maquiagem", "bolsa", (240, 240, 240)), ("balao", "bola", (200, 60, 160)), ("sino", "bola", (200, 170, 80)),
    ("luva", "bola", (200, 60, 50)), ("fio_de_marionete", "fio", (230, 220, 200)), ("carne", "gota", (190, 90, 90)),
    ("totem", "pingente", (190, 170, 130)), ("selo", "bola", (190, 40, 40)), ("coroa", "pingente", (230, 190, 80)),
    ("asa", "manto", (80, 60, 90)), ("glandula", "gota", (130, 220, 70)),
]

DESENHO_POR_TIPO = {"equipamento": ("espada", (170, 170, 190)), "consumivel": ("frasco", (180, 120, 200)),
                    "material": ("bolsa", (150, 130, 110))}


def desenho_do_item(objeto):
    for pedaco, desenho, cor in PALAVRAS:
        if pedaco in objeto.chave:
            return desenho, cor
    return DESENHO_POR_TIPO.get(objeto.tipo, ("bolsa", (150, 130, 110)))


def icone_forjado(chave, vezes):
    """Ícone 20x20 da forja ampliado por um fator inteiro perto de 12*vezes (ou None se não existir)."""
    caminho = os.path.join(PASTA_ICONES_FORJADOS, chave + ".png")
    if not os.path.exists(caminho):
        return None
    imagem = pygame.image.load(caminho)
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        imagem = imagem.convert_alpha()
    fator = max(1, round(12 * vezes / TAMANHO_FORJADO))
    return pygame.transform.scale(imagem, (TAMANHO_FORJADO * fator, TAMANHO_FORJADO * fator))


def icone_item(objeto, vezes=3):
    """Ícone do item: o da forja de itens; sem ele, o desenho 12x12 antigo."""
    def criar():
        forjado = icone_forjado(getattr(objeto, "base", objeto.chave), vezes)       # exemplar usa o ícone da ficha
        if forjado is not None:
            return forjado
        desenho, cor = desenho_do_item(objeto)
        detalhe = misturar(cor, 0.45) if objeto.raridade == "comum" else tema.COR_RARIDADE[objeto.raridade]
        return pintar(DESENHOS[desenho], cor, detalhe, vezes)
    return guardar(("icone_item", objeto.chave, vezes), criar)


def icone_encontro(nome, vezes=3):
    def criar():
        cor = CORES_DE_ENCONTRO.get(nome, (200, 200, 200))
        detalhe = DETALHE_DE_ENCONTRO.get(nome, misturar(cor, 0.4))
        return pintar(DESENHOS_DE_ENCONTRO.get(nome, DESENHOS_DE_ENCONTRO["interrogacao"]), cor, detalhe, vezes)
    return guardar(("icone_encontro", nome, vezes), criar)


def quadro_de_item(tela, objeto, posicao, tamanho=48, quantidade=None, selecionado=False):
    """Quadradinho de inventário: moldura na cor da raridade, ícone e quantidade."""
    from ui.desenho import painel, texto
    rect = pygame.Rect(posicao[0], posicao[1], tamanho, tamanho)
    painel(tela, rect, "ouro" if selecionado else "espaco")       # espaço afundado com cantinhos dourados
    cor = tema.COR_RARIDADE[objeto.raridade]
    pygame.draw.rect(tela, cor, rect.inflate(-10, -10), 1 if objeto.raridade == "comum" else 2)
    icone = icone_item(objeto, max(2, (tamanho - 12) // 12))
    tela.blit(icone, icone.get_rect(center=rect.center))
    if quantidade and quantidade > 1:
        texto(tela, str(quantidade), tema.mini(), tema.TEXTO, (rect.right - 4, rect.bottom - 2), "bottomright")
    return rect
