"""Prévia dos projéteis: antes (PNGs antigos) x depois (voo + impacto), com orbe e lança tingidos.

    python previa_efeitos.py      -> previas/efeitos_projeteis.png
"""
import json
import os

from PIL import Image, ImageChops, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "..", "..", "assets", "efeitos")
ANTES = os.path.join(AQUI, "previas", "antes", "efeitos")
CORES = {"orbe": [(170, 140, 240), (120, 220, 255), (250, 110, 60)], "lanca": [(170, 230, 255), (255, 220, 140), (190, 120, 255)]}
FUNDO = (30, 26, 38, 255)
ESC = 4


def tingir(img, cor):
    return ImageChops.multiply(img, Image.new("RGBA", img.size, (*cor, 255)))


def main():
    meta = json.load(open(os.path.join(PASTA, "efeitos.json"), encoding="utf-8"))
    linhas = []
    for nome, m in meta.items():
        if nome.startswith("_"):
            continue
        folha = Image.open(os.path.join(PASTA, nome + ".png")).convert("RGBA")
        for cor in CORES.get(nome, [None]):
            img = tingir(folha, cor) if cor else folha
            antes = Image.open(os.path.join(ANTES, nome + ".png")).convert("RGBA")
            antes = antes.resize((antes.width * 4 * ESC // 2, antes.height * 4 * ESC // 2), Image.NEAREST)  # como era (4x) na mesma escala
            if cor:
                antes = tingir(antes, cor)
            quadros = [antes]
            for linha in ("voo", "impacto"):
                w, h = m[linha]["celula"]
                for i in range(m[linha]["quadros"]):
                    q = img.crop((i * w, m[linha]["y"], (i + 1) * w, m[linha]["y"] + h))
                    quadros.append(q.resize((w * ESC, h * ESC), Image.NEAREST))
            altura = max(q.height for q in quadros) + 16
            linha_img = Image.new("RGBA", (sum(q.width + 12 for q in quadros) + 10, altura), FUNDO)
            x = 6
            for k, q in enumerate(quadros):
                linha_img.alpha_composite(q, (x, (altura - q.height) // 2))
                x += q.width + (30 if k == 0 or k == 4 else 12)
            ImageDraw.Draw(linha_img).text((4, 2), f"{nome}{' ' + str(cor) if cor else ''}  (antes | voo x4 | impacto x5)",
                                           fill=(230, 210, 160))
            linhas.append(linha_img)
    folha = Image.new("RGBA", (max(l.width for l in linhas), sum(l.height for l in linhas)), (12, 10, 16, 255))
    y = 0
    for l in linhas:
        folha.paste(l, (0, y))
        y += l.height
    folha.save(os.path.join(AQUI, "previas", "efeitos_projeteis.png"))
    print("ok")


if __name__ == "__main__":
    main()
