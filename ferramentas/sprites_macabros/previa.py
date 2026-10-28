"""Gera uma prévia ampliada de um ou mais modelos (para conferência)."""
import sys
import importlib

from PIL import Image, ImageDraw

from forja.anim import ANIMACOES


def previa(modelos, saida, escala=3, fundo=(38, 34, 44), colunas=4, recorte=True):
    linhas = []
    for mod in modelos:
        quadros = mod.folha()
        W, H = mod.larg, mod.alt
        tiras = []
        for anim, n in ANIMACOES:
            tiras.extend(quadros[anim])
        # recorte comum
        if recorte:
            bbox = None
            for im in tiras:
                b = im.getbbox()
                if b is None:
                    continue
                bbox = b if bbox is None else (min(bbox[0], b[0]), min(bbox[1], b[1]), max(bbox[2], b[2]), max(bbox[3], b[3]))
            bbox = bbox or (0, 0, W, H)
            bbox = (max(0, bbox[0] - 2), max(0, bbox[1] - 2), min(W, bbox[2] + 2), min(H, bbox[3] + 2))
        else:
            bbox = (0, 0, W, H)
        tiras = [im.crop(bbox) for im in tiras]
        linhas.append((mod.nome, tiras))
    por_linha = 7
    lin2 = []
    for nome, tiras in linhas:
        for k in range(0, len(tiras), por_linha):
            lin2.append((nome if k == 0 else "", tiras[k:k + por_linha]))
    linhas = lin2
    cw = max(t[0].width for _, t in linhas)
    ch = max(t[0].height for _, t in linhas)
    n = max(len(t) for _, t in linhas)
    img = Image.new("RGBA", (cw * n * escala + 10, (ch * escala + 14) * len(linhas)), fundo + (255,))
    d = ImageDraw.Draw(img)
    for r, (nome, tiras) in enumerate(linhas):
        y = r * (ch * escala + 14)
        d.text((4, y + 1), nome, fill=(200, 190, 210, 255))
        for c, im in enumerate(tiras):
            big = im.resize((im.width * escala, im.height * escala), Image.NEAREST)
            img.alpha_composite(big, (c * cw * escala + 5, y + 12 + (ch - im.height) * escala))
    img.save(saida)
    return saida


if __name__ == "__main__":
    mod, cls = sys.argv[1], sys.argv[2]
    m = importlib.import_module("forja.personagens." + mod)
    kw = {}
    for a in sys.argv[4:]:
        k, v = a.split("=")
        kw[k] = eval(v)
    previa([getattr(m, cls)(**kw)], sys.argv[3])
