"""Prévia dos itens da etapa 8: ícone ampliado, nome, raridade e o herói vestindo a peça.

    python previa_itens_etapa8.py            -> previas/itens_etapa8/icones.png e herois_*.png
"""
import json
import os
import sys

from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJETO = os.path.dirname(os.path.dirname(AQUI))
SAIDA = os.path.join(AQUI, "previas", "itens_etapa8")
CORES = {"comum": (170, 165, 160), "incomum": (110, 196, 96), "raro": (90, 150, 230), "epico": (175, 90, 220),
         "lendario": (235, 170, 60), "amaldicoado": (196, 40, 64)}


def itens_da_etapa():
    dados = json.load(open(os.path.join(PROJETO, "src", "roguelike", "dados", "itens.json"), encoding="utf-8"))["equipamentos"]
    dentro, lista = False, []
    for chave, info in dados.items():
        if chave == "_etapa8_cabeca":
            dentro = True
        if dentro and not chave.startswith("_"):
            lista.append((chave, info))
    return lista


def prancha_de_icones(itens, destino, colunas=6, zoom=4):
    cel_w, cel_h = 260, 20 * zoom + 12
    linhas = (len(itens) + colunas - 1) // colunas
    img = Image.new("RGBA", (colunas * cel_w + 10, linhas * cel_h + 10), (30, 26, 34, 255))
    d = ImageDraw.Draw(img)
    for i, (chave, info) in enumerate(itens):
        x, y = 6 + (i % colunas) * cel_w, 6 + (i // colunas) * cel_h
        icone = Image.open(os.path.join(PROJETO, "assets", "itens_macabros", chave + ".png")).convert("RGBA")
        img.alpha_composite(icone.resize((20 * zoom, 20 * zoom), Image.NEAREST), (x, y))
        cor = CORES.get(info["raridade"], (200, 200, 200)) + (255,)
        nome = info["nome"]
        partes = [nome[:22], nome[22:44]] if len(nome) > 22 else [nome]
        for k, parte in enumerate(partes):
            d.text((x + 20 * zoom + 6, y + 6 + k * 12), parte, fill=cor)
        d.text((x + 20 * zoom + 6, y + 6 + len(partes) * 12), f'{info["espaco"]} · {info["raridade"]}', fill=(150, 140, 160, 255))
    img.save(destino)


def pranchas_dos_herois(itens):
    """Cada herói vestindo peças da etapa 8 (o jogo compõe e tinge as camadas)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    sys.path.insert(0, os.path.join(PROJETO, "src"))
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    from roguelike.classes import criar_heroi
    from roguelike.itens import item
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    por_espaco = {}
    for chave, info in itens:
        por_espaco.setdefault(info["espaco"], []).append(chave)
    classes = ["guerreiro", "ladino", "mago", "sacerdote", "barbaro", "patrulheira", "bardo", "bobo", "monge", "feiticeira"]
    conjuntos = 4
    for c in range(conjuntos):
        quadros = []
        for k, classe in enumerate(classes):
            heroi = criar_heroi(classe)
            for espaco, chaves in por_espaco.items():
                heroi.equipar(item(chaves[(k + c * 3) % len(chaves)]))
            quadros.append(sprites.quadro(heroi.sprite, "parado", 0, 3))
        largura = sum(q.get_width() for q in quadros) + 10 * len(quadros)
        altura = max(q.get_height() for q in quadros) + 10
        tela = pygame.Surface((largura, altura), pygame.SRCALPHA)
        tela.fill((30, 26, 34, 255))
        x = 5
        for q in quadros:
            tela.blit(q, (x, altura - q.get_height() - 5))
            x += q.get_width() + 10
        pygame.image.save(tela, os.path.join(SAIDA, f"herois_{c + 1}.png"))


def main():
    os.makedirs(SAIDA, exist_ok=True)
    itens = itens_da_etapa()
    prancha_de_icones(itens, os.path.join(SAIDA, "icones.png"))
    pranchas_dos_herois(itens)
    print(f"{len(itens)} itens -> {SAIDA}")


if __name__ == "__main__":
    main()
