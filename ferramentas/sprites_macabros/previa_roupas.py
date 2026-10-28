"""Prévia das roupas com adornos: por classe, o herói base e cada roupa (parado, ataque e morte).

Uso:
    python previa_roupas.py                 (todas, uma prancha por classe em previas/roupas/)
    python previa_roupas.py guerreiro mago  (só as geometrias pedidas)
"""
import os
import sys
from multiprocessing import Pool

from PIL import Image, ImageDraw

from forja.personagens.roupas import ROUPAS
from forja.personagens import herois as H, acampamento as C, herois_novos as N, herois_do_reino as R

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "previas", "roupas")
ESCALA = 3
QUADROS = (("parado", 0, 4), ("ataque", 1, 4), ("sentado", 0, 4), ("morte", 1, 4))

BASES = {"guerreiro": lambda: H.Guerreiro(), "paladino": lambda: H.Paladino(), "mago": lambda: H.MagoFogo(),
         "barbaro_Machado": lambda: H.Barbaro(arma="Machado"), "barbaro_Martelo": lambda: H.Barbaro(arma="Martelo"),
         "barbaro_Espada": lambda: H.Barbaro(arma="Espada"), "arqueira": lambda: H.Arqueira(),
         "assassina": lambda: H.Assassina(), "bardo": lambda: C.Bardo(), "bobo": lambda: C.BoboDaCorte(),
         "monge": lambda: N.Monge(), "feiticeira": lambda: N.Feiticeira(), "medico_da_peste": lambda: R.MedicoDaPeste(),
         "senhor_dos_ratos": lambda: R.SenhorDosRatos()}


def tiras(fabrica):
    """Os quadros de um modelo, recortados no mesmo enquadramento."""
    m = fabrica()
    imgs = [m.quadro(anim, i, n) for anim, i, n in QUADROS]
    caixas = [im.getbbox() for im in imgs if im.getbbox()]
    x0 = min(c[0] for c in caixas) - 2
    y0 = min(c[1] for c in caixas) - 2
    x1 = max(c[2] for c in caixas) + 2
    y1 = max(c[3] for c in caixas) + 2
    return m.nome, [im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * ESCALA, (y1 - y0) * ESCALA), Image.NEAREST) for im in imgs]


def prancha(geometria, entradas, destino):
    linhas = [tiras(BASES[geometria])] + [tiras(fab) for fab in entradas]
    larg = max(sum(im.width + 8 for im in ims) for _, ims in linhas) + 220
    alt = sum(max(im.height for im in ims) + 12 for _, ims in linhas) + 10
    img = Image.new("RGBA", (larg, alt), (30, 26, 34, 255))
    d = ImageDraw.Draw(img)
    y = 6
    for k, (nome, ims) in enumerate(linhas):
        d.text((10, y + 8), ("BASE: " if k == 0 else "") + nome, fill=(230, 200, 140, 255) if k == 0 else (200, 190, 210, 255))
        x = 210
        h = max(im.height for im in ims)
        for im in ims:
            img.alpha_composite(im, (x, y + h - im.height))
            x += im.width + 8
        y += h + 12
        d.line((10, y - 6, larg - 10, y - 6), fill=(60, 52, 66, 255))
    img.save(destino)
    return destino


def _uma(argumentos):
    geometria, nomes = argumentos
    entradas = [fab for nome, geo, fab in ROUPAS if geo == geometria and nome in nomes]
    return prancha(geometria, entradas, os.path.join(SAIDA, f"roupas_{geometria}.png"))


def main():
    filtro = sys.argv[1:]
    os.makedirs(SAIDA, exist_ok=True)
    por_geo = {}
    for nome, geo, _ in ROUPAS:
        if not filtro or any(f in geo or f in nome for f in filtro):
            por_geo.setdefault(geo, []).append(nome)
    with Pool() as pool:
        for caminho in pool.map(_uma, list(por_geo.items())):
            print(caminho)


if __name__ == "__main__":
    main()
