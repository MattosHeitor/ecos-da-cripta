"""Prévia "antes x depois" de um lote de sprites, sem mexer nos assets do jogo.

    python previa_lote.py 2a lobo_sarnento torreta ...   -> previas/lote_2a.png e previas/lote_2a/<nome>.gif

"Antes" vem de previas/antes/ (cópia feita aqui na primeira vez, a partir de assets/sprites_macabros,
que também serve para desfazer). "Depois" é gerado agora pelas classes do CATALOGO de gerar_sprites.py.
"""
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw

from gerar_sprites import CATALOGO, PASTA as PASTA_ASSETS
from previa_forjas import prancha, gif, FUNDO

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "previas")
ANTES = os.path.join(PASTA, "antes")


def guardar_antes(nomes):
    """Copia a folha atual de cada nome (e a ficha do catálogo) para previas/antes, se ainda não copiou."""
    os.makedirs(ANTES, exist_ok=True)
    caminho = os.path.join(ANTES, "catalogo.json")
    fichas = json.load(open(caminho, encoding="utf-8")) if os.path.exists(caminho) else {}
    atual = json.load(open(os.path.join(PASTA_ASSETS, "catalogo.json"), encoding="utf-8"))
    for nome in nomes:
        if nome not in fichas and nome in atual:
            shutil.copy(os.path.join(PASTA_ASSETS, nome + ".png"), os.path.join(ANTES, nome + ".png"))
            fichas[nome] = atual[nome]
    json.dump(fichas, open(caminho, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return fichas


def quadros_antes(ficha, escala):
    """Parado, golpe, dano e morte da folha antiga."""
    folha = Image.open(os.path.join(ANTES, ficha["nome"] + ".png"))
    w, h = ficha["celula"]
    imgs = []
    for anim, i in (("parado", 0), ("ataque", 1), ("dano", 0), ("morte", 3)):
        linha = ficha["animacoes"][anim]["linha"]
        imgs.append(folha.crop((i * w, linha * h, (i + 1) * w, (linha + 1) * h)))
    caixas = [q.getbbox() for q in imgs if q.getbbox()]
    x0, y0 = min(c[0] for c in caixas), min(c[1] for c in caixas)
    x1, y1 = max(c[2] for c in caixas), max(c[3] for c in caixas)
    return [q.crop((x0, y0, x1, y1)).resize(((x1 - x0) * escala, (y1 - y0) * escala), Image.NEAREST) for q in imgs]


def modelo(nome):
    for fab, *_ in CATALOGO:
        m = fab()
        if m.nome == nome:
            return m
    raise KeyError(nome)


def main():
    """Argumentos: lote e nomes; "novo=antigo" compara com outro sprite (o que ele usava emprestado)."""
    lote = sys.argv[1]
    pares = [(a.split("=") + [a])[:2] for a in sys.argv[2:]]
    nomes = [novo for novo, _ in pares]
    antigos = {novo: antigo for novo, antigo in pares}
    fichas = guardar_antes(list(antigos.values()))
    fichas = {novo: fichas[antigo] for novo, antigo in antigos.items() if antigo in fichas}
    pasta_gif = os.path.join(PASTA, "lote_" + lote)
    os.makedirs(pasta_gif, exist_ok=True)
    blocos = []
    for nome in nomes:
        m = modelo(nome)
        escala = 3 if m.H <= 96 else 2
        quadros = m.folha()
        depois = prancha(m, quadros, escala)
        gif(m, quadros, escala, os.path.join(pasta_gif, nome + ".gif"))
        antes = quadros_antes(fichas[nome], escala) if nome in fichas else []
        alt_antes = max((q.height for q in antes), default=0)
        bloco = Image.new("RGBA", (max(depois.width, sum(q.width + 12 for q in antes) + 60), alt_antes + 30 + depois.height),
                          FUNDO)
        d = ImageDraw.Draw(bloco)
        d.text((6, 4), "ANTES" if antes else "ANTES: (novo)", fill=(200, 120, 120))
        x = 60
        for q in antes:
            bloco.alpha_composite(q, (x, 18 + alt_antes - q.height))
            x += q.width + 12
        d.line([(0, alt_antes + 24), (bloco.width, alt_antes + 24)], fill=(90, 70, 80), width=2)
        bloco.alpha_composite(depois, (0, alt_antes + 30))
        blocos.append(bloco)
        print(nome, "ok")
    largura = max(b.width for b in blocos)
    total = Image.new("RGBA", (largura, sum(b.height + 14 for b in blocos)), (12, 10, 14, 255))
    y = 0
    for b in blocos:
        total.alpha_composite(b, (0, y))
        y += b.height + 14
    saida = os.path.join(PASTA, f"lote_{lote}.png")
    total.save(saida)
    print("->", saida)


if __name__ == "__main__":
    main()
