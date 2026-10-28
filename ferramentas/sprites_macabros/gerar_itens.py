"""Gera os ícones de TODOS os itens (forja/itens.py) em assets/itens_macabros/<chave>.png.

    python gerar_itens.py                 # todos
    python gerar_itens.py tomo espada     # só os itens cuja chave contém esses pedaços

Também salva previas/galeria_itens.png (todos lado a lado, ampliados) para conferir.
"""
import json
import os
import sys

from PIL import Image

from forja.itens import icone_do_item, T

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJETO = os.path.dirname(os.path.dirname(AQUI))
DADOS = os.path.join(PROJETO, "src", "roguelike", "dados", "itens.json")
PASTA = os.path.join(PROJETO, "assets", "itens_macabros")
SECOES = {"materiais": "material", "equipamentos": "equipamento", "consumiveis": "consumivel", "tomos": "consumivel"}


def itens_do_jogo():
    with open(DADOS, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    for secao, tipo in SECOES.items():
        for chave, info in dados.get(secao, {}).items():
            if not chave.startswith("_"):
                yield chave, info, tipo


def galeria(imagens, caminho, colunas=14, zoom=3):
    folha = Image.new("RGBA", (colunas * (T + 4) * zoom, ((len(imagens) + colunas - 1) // colunas) * (T + 4) * zoom),
                      (38, 32, 44, 255))
    for i, imagem in enumerate(imagens):
        x, y = (i % colunas) * (T + 4) * zoom, (i // colunas) * (T + 4) * zoom
        folha.alpha_composite(imagem.resize((T * zoom, T * zoom), Image.NEAREST), (x + 2 * zoom, y + 2 * zoom))
    folha.save(caminho)


def main():
    filtro = sys.argv[1:]
    os.makedirs(PASTA, exist_ok=True)
    imagens = []
    for chave, info, tipo in itens_do_jogo():
        caminho = os.path.join(PASTA, chave + ".png")
        if not filtro or any(f in chave for f in filtro):
            icone_do_item(chave, info, tipo).gerar().save(caminho)
        if os.path.exists(caminho):
            imagens.append(Image.open(caminho).convert("RGBA"))
    os.makedirs(os.path.join(AQUI, "previas"), exist_ok=True)
    galeria(imagens, os.path.join(AQUI, "previas", "galeria_itens.png"))
    print(f"{len(imagens)} ícones em {PASTA}")


if __name__ == "__main__":
    main()