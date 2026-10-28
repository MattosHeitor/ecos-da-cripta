"""Gera retratos (bustos) de personagens para as telas do jogo, em assets/retratos/<nome>.png.

    python gerar_retratos.py

O retrato usa a MESMA classe do sprite de combate, só que desenhada maior (H alto): a cabeça e os
ombros viram uma imagem de LADO x LADO pixels, que o jogo mostra ampliada 2x.
"""
import os

import numpy as np

from forja.personagens.monstros import MercadorMascarado

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "assets", "retratos")
LADO = 88


class RetratoDoMercador(MercadorMascarado):
    """O Mercador Mascarado em escala de retrato."""
    nome = "mercador_mascarado"
    H = 190


def busto(modelo, lado=LADO):
    """Recorta cabeça e ombros (quadrado de 'lado' pixels) do 1º quadro parado."""
    img = modelo.quadro("parado", 0, 4)
    alfa = np.asarray(img)[..., 3] > 0
    ys, xs = np.nonzero(alfa)
    topo = ys.min()
    faixa = alfa[topo:topo + lado // 3]
    cx = int(np.nonzero(faixa.any(axis=0))[0].mean())
    x0, y0 = cx - lado // 2, topo - 4
    return img.crop((x0, y0, x0 + lado, y0 + lado))


def main():
    os.makedirs(PASTA, exist_ok=True)
    for classe in (RetratoDoMercador,):
        m = classe()
        caminho = os.path.join(PASTA, m.nome + ".png")
        busto(m).save(caminho)
        print("->", caminho)


if __name__ == "__main__":
    main()
