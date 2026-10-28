"""As luzes do salão da Cripta (tela de título), prontas em PNG: os três feixes do vitral e a névoa do piso.

    python ferramentas/sprites_macabros/gerar_luzes_do_salao.py     -> assets/salao_da_cripta/feixe_0..2.png, nevoa.png

O jogo fazia estas contas com o numpy ao abrir o título; agora só carrega as imagens (o numpy não vai no instalador).
As contas são as mesmas de antes (a geometria vem de visual/salao_da_cripta.py e do salao.json), para a tela de
1280x720. gerar_salao.py chama esta ferramenta no fim (mudou o vitral, os feixes acompanham).
"""

import json
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(RAIZ, "src"))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from visual.salao_da_cripta import PASTA, geometria_dos_feixes, vitral_na_tela  # noqa: E402

TAMANHO_DA_TELA = (1280, 720)


def feixe(topo, base, largura_topo, largura_base, cor, forca=0.5):
    """Feixe de luz do vitral até o chão: inclinado, mais largo embaixo, com as bordas e o pé se apagando."""
    x0 = int(min(topo[0] - largura_topo, base[0] - largura_base))
    x1 = int(max(topo[0] + largura_topo, base[0] + largura_base))
    y0, y1 = int(topo[1]), int(base[1])
    xs = np.arange(x0, x1, dtype=np.float32)[:, None]
    ys = np.arange(y0, y1, dtype=np.float32)[None, :]
    t = (ys - y0) / max(1, y1 - y0)
    centro = topo[0] + (base[0] - topo[0]) * t
    meia = (largura_topo + (largura_base - largura_topo) * t) / 2
    borda = np.clip(1 - np.abs(xs - centro) / meia, 0, 1) ** 0.9
    intensidade = forca * borda * (1 - t) ** 1.1 * np.clip(t * 6, 0, 1)
    rgb = np.dstack([intensidade * c for c in cor]).astype(np.uint8)
    return pygame.surfarray.make_surface(rgb)


def nevoa(largura=TAMANHO_DA_TELA[0], altura=150):
    """Faixa de névoa (manchas suaves) que corre devagar pelo piso, repetindo sem costura."""
    rng = np.random.default_rng(5)
    pequena = rng.random((altura // 10 + 1, largura // 40)).astype(np.float32)
    pequena = np.concatenate([pequena, pequena[:, :1]], axis=1)       # a ponta repete o começo: emenda sem costura
    grade = pygame.surfarray.make_surface((np.dstack([pequena.T * 255] * 3)).astype(np.uint8))
    suave = pygame.transform.smoothscale(grade, (largura + largura // 40, altura))
    valores = pygame.surfarray.array3d(suave)[:largura, :, 0].astype(np.float32) / 255
    queda = np.sin(np.linspace(0, math.pi, altura)) ** 1.5             # some em cima e embaixo
    alfa = np.clip((valores - 0.35) * 1.6, 0, 1) * queda[None, :] * 70
    sup = pygame.Surface((largura, altura), pygame.SRCALPHA)
    sup.fill((96, 90, 124, 0))
    pygame.surfarray.pixels_alpha(sup)[:, :] = alfa.astype(np.uint8)
    return sup


def luzes():
    """{nome do arquivo: superfície} das quatro luzes."""
    with open(os.path.join(PASTA, "salao.json"), encoding="utf-8") as arquivo:
        info = json.load(arquivo)
    imagens = {f"feixe_{k}.png": feixe(topo, base, largura_topo, largura_base, cor, forca)
               for k, (topo, base, largura_topo, largura_base, cor, forca)
               in enumerate(geometria_dos_feixes(vitral_na_tela(info), TAMANHO_DA_TELA))}
    imagens["nevoa.png"] = nevoa()
    return imagens


def main():
    pygame.init()
    for nome, imagem in luzes().items():
        pygame.image.save(imagem, os.path.join(PASTA, nome))
        print(f"{nome}: {imagem.get_width()}x{imagem.get_height()}")


if __name__ == "__main__":
    main()
