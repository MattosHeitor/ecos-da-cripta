"""Galeria do equipamento visível: cada classe com vários conjuntos de peças de verdade, montados pelo
próprio jogo (equipar -> nome do sprite -> composição em visual/sprites_macabros.py).

    python previa_equipamento.py      -> previas/equipamento_galeria.png e previas/equipamento_pecas.png
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "src"))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from roguelike.classes import criar_heroi, todas_as_classes  # noqa: E402
from roguelike.itens import item, todos_os_itens, Equipamento  # noqa: E402
from visual.sprites_macabros import Sprites  # noqa: E402

CONJUNTOS = {
    "sem nada": [],
    "Ferro Negro": ["elmo_de_ferro_negro", "armadura_de_ferro_negro", "grevas_de_ferro_negro", "botas_gastas",
                    "capa_de_la", "espada_de_prata", "escudo_de_ferro_negro"],
    "Coveiro": ["capuz_do_coveiro", "casaco_do_coveiro", "calcas_de_couro", "botas_do_coveiro", "manto_de_trapos",
                "lanterna_das_profundezas", "pa_do_coveiro"],
    "Fúria": ["elmo_berserker", "couraca_de_brasa", "grevas_de_ferro", "botas_de_viajante", "manto_do_rei_sombrio",
              "estandarte_portatil", "machado_de_magma"],
    "Mística": ["mascara_do_mercador", "veste_sagrada", "calcas_de_couro", "botas_de_junco", "manto_de_seda",
                "coracao_pulsante", "cajado_runico"],
    "Sombra": ["coroa_de_espinhos_maldita", "armadura_de_ossos", "calcas_de_couro", "botas_do_enforcado", "capa_do_conde",
               "anel_do_pacto", "adagas_de_obsidiana"],
}
FUNDO, TEXTO = (26, 22, 32), (230, 210, 160)


def vestir(classe, pecas, raca=None):
    heroi = criar_heroi(classe)
    if raca:
        heroi.definir_raca(raca)
    for chave in pecas:
        try:
            heroi.equipar(item(chave))
        except KeyError:                      # espaço que o jogo não tem
            print("não equipa:", chave)
    return heroi


def quadro(sprites, heroi, anim, i, escala=2):
    return sprites.quadro(heroi.sprite, anim, i, escala)


def grade(linhas, rotulos_colunas, saida, celula):
    fonte = pygame.font.SysFont("consolas", 14)
    w, h = celula
    folha = pygame.Surface((140 + w * len(rotulos_colunas), 24 + h * len(linhas)))
    folha.fill(FUNDO)
    for c, rotulo in enumerate(rotulos_colunas):
        folha.blit(fonte.render(rotulo, True, TEXTO), (140 + c * w + 6, 4))
    for r, (rotulo, imagens) in enumerate(linhas):
        folha.blit(fonte.render(rotulo, True, TEXTO), (6, 24 + r * h + h // 2))
        for c, img in enumerate(imagens):
            x = 140 + c * w + (w - img.get_width()) // 2
            folha.blit(img, (x, 24 + r * h + h - img.get_height()))
    pygame.image.save(folha, saida)


def main():
    sprites = Sprites()
    pasta = os.path.join(AQUI, "previas")
    linhas = []
    for chave in todas_as_classes():
        imagens = []
        for nome, pecas in CONJUNTOS.items():
            heroi = vestir(chave, pecas)
            imagens.append(quadro(sprites, heroi, "parado", 0))
            if nome != "sem nada":
                imagens.append(quadro(sprites, heroi, "ataque", 1))
        linhas.append((chave, imagens))
    rotulos = ["sem nada"] + [r for nome in list(CONJUNTOS)[1:] for r in (nome, "(golpe)")]
    grade(linhas, rotulos, os.path.join(pasta, "equipamento_galeria.png"), (190, 210))

    # todas as 85 peças, uma a uma, no guerreiro (raça humana) e no mago anão
    pecas = sorted((i for i in todos_os_itens().values() if isinstance(i, Equipamento)), key=lambda p: (p.espaco, p.chave))
    linhas = []
    for k in range(0, len(pecas), 10):
        grupo = pecas[k:k + 10]
        imagens = []
        for peca in grupo:
            imagens.append(quadro(sprites, vestir("guerreiro", [peca.chave]), "parado", 0))
        linhas.append((f"{k + 1}-{k + len(grupo)}", imagens))
    grade(linhas, [""] * 10, os.path.join(pasta, "equipamento_pecas.png"), (170, 190))

    # compatibilidade: raças (traço por cima), skins de roupa (desarmadas também) e de chapéu/arma
    casos = [("guerreiro", "anao_das_profundezas", {}, "Ferro Negro"), ("mago", "meio_orc", {}, "Mística"),
             ("patrulheira", "elfo_sombrio", {"roupa": "capa_da_lua"}, "Sombra"),
             ("barbaro", "draconiano", {"roupa": "pele_de_urso", "arma": "brasa"}, "Fúria"),
             ("bardo", "gnomo", {"roupa": "gibao_do_circo"}, "Coveiro"),
             ("sacerdote", "meio_demonio", {"roupa": "armadura_da_aurora", "chapeu": "aureola"}, "Ferro Negro")]
    linhas = []
    for classe, raca, skins, conjunto in casos:
        heroi = vestir(classe, CONJUNTOS[conjunto], raca)
        heroi.vestir(skins)
        imagens = [quadro(sprites, heroi, "parado", 0), quadro(sprites, heroi, "ataque", 1), quadro(sprites, heroi, "dano", 0)]
        linhas.append((f"{classe}/{raca[:10]}", imagens))
    grade(linhas, ["parado", "golpe", "dano"], os.path.join(pasta, "equipamento_racas_skins.png"), (200, 210))
    print("ok")


if __name__ == "__main__":
    main()
