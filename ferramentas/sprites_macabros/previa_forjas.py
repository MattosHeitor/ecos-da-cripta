"""Prévia das forjas: todas as animações de cada criatura de demonstração, ampliadas.

    python previa_forjas.py                 -> previas/forjas.png e um .gif animado por criatura
    python previa_forjas.py lobo            -> só as que têm "lobo" no nome
"""
import os
import sys
import time

from PIL import Image, ImageDraw

from forja.criaturas import demos

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "previas")
FUNDO = (28, 24, 34, 255)
CHAO = (52, 44, 50, 255)
ANIMS = ("parado", "ataque", "dano", "morte")


def modelos(filtro):
    lista = [getattr(demos, n)() for n in demos.__all__]
    return [m for m in lista if not filtro or any(f in m.nome for f in filtro)]


def caixa_comum(quadros):
    """Menor retângulo que contém todos os quadros (mesmo enquadramento em todos)."""
    caixas = [q.getbbox() for qs in quadros.values() for q in qs if q.getbbox()]
    return (min(c[0] for c in caixas), min(c[1] for c in caixas), max(c[2] for c in caixas), max(c[3] for c in caixas))


def prancha(modelo, quadros, escala):
    x0, y0, x1, y1 = caixa_comum(quadros)
    w, h = (x1 - x0) * escala, (y1 - y0) * escala
    chao_y = (modelo.ancora[1] - y0) * escala
    img = Image.new("RGBA", (w * 4 + 50, (h + 18) * len(ANIMS) + 26), FUNDO)
    d = ImageDraw.Draw(img)
    d.text((6, 6), f"{modelo.nome}  ({modelo.larg}x{modelo.alt}, {type(modelo).__mro__[1].__name__})", fill=(230, 210, 170))
    for linha, anim in enumerate(ANIMS):
        y = 26 + linha * (h + 18)
        d.text((6, y), anim, fill=(170, 160, 190))
        for i, q in enumerate(quadros[anim]):
            x = 44 + i * w
            d.line([(x, y + 12 + chao_y), (x + w - 4, y + 12 + chao_y)], fill=CHAO, width=2)
            q = q.crop((x0, y0, x1, y1)).resize((w, h), Image.NEAREST)
            img.alpha_composite(q, (x, y + 12))
    return img


def gif(modelo, quadros, escala, caminho):
    x0, y0, x1, y1 = caixa_comum(quadros)
    seq = quadros["parado"] * 3 + quadros["ataque"] + quadros["parado"] * 2 + quadros["dano"] + quadros["parado"] * 2 + \
        quadros["morte"] + [quadros["morte"][-1]] * 3
    tempos = [200] * 12 + [110] * 4 + [200] * 8 + [130] * 2 + [200] * 8 + [180] * 4 + [400] * 3
    imgs = []
    for q in seq:
        fundo = Image.new("RGBA", ((x1 - x0) * escala, (y1 - y0) * escala), FUNDO)
        fundo.alpha_composite(q.crop((x0, y0, x1, y1)).resize(fundo.size, Image.NEAREST))
        imgs.append(fundo.convert("RGB"))
    imgs[0].save(caminho, save_all=True, append_images=imgs[1:], duration=tempos[:len(imgs)], loop=0)


def main():
    os.makedirs(PASTA, exist_ok=True)
    pranchas = []
    for m in modelos(sys.argv[1:]):
        t = time.time()
        quadros = m.folha()
        escala = 3 if m.H <= 96 else 2
        pranchas.append(prancha(m, quadros, escala))
        gif(m, quadros, escala, os.path.join(PASTA, m.nome + ".gif"))
        print(f"{m.nome}: {time.time() - t:.1f}s")
    largura = max(p.width for p in pranchas)
    total = Image.new("RGBA", (largura, sum(p.height + 8 for p in pranchas)), FUNDO)
    y = 0
    for p in pranchas:
        total.alpha_composite(p, (0, y))
        y += p.height + 8
    saida = os.path.join(PASTA, "forjas.png" if not sys.argv[1:] else "forjas_" + "_".join(sys.argv[1:]) + ".png")
    total.save(saida)
    print("->", saida)


if __name__ == "__main__":
    main()
