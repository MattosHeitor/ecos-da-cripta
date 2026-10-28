"""Confere se a forja ainda gera EXATAMENTE os sprites que estão no jogo, pixel a pixel, sem gravar nada.

    python conferir_identicos.py                 (personagens, inimigos, roupas e objetos; sem as camadas)
    python conferir_identicos.py aranha lobo     (só os nomes que contêm esses textos)
    python conferir_identicos.py --camadas       (inclui as ~1000 camadas de skins e equipamento: demora)

Rode antes e depois de mexer na forja: uma folha que mudou sem querer aparece como DIFERENTE.
Também confere a ficha do catálogo (célula, âncora, escala e linhas de animação).
Sai com código 1 se algo mudou (dá para usar em testes).
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image

from forja.anim import montar_folha
from gerar_sprites import CATALOGO, PASTA

CAMPOS_DO_CATALOGO = ("celula", "ancora", "escala", "animacoes")


def conferir_um(argumentos):
    """Gera uma folha na memória e compara com o PNG do jogo. Devolve (nome, situação, detalhe) ou None."""
    indice, filtro, com_camadas, catalogo = argumentos
    fabrica, familia, *_ = CATALOGO[indice]
    if familia == "camadas" and not com_camadas:
        return None
    modelo = fabrica()
    if filtro and not any(f in modelo.nome for f in filtro):
        return None
    caminho = os.path.join(PASTA, modelo.nome + ".png")
    if not os.path.exists(caminho):
        return modelo.nome, "SEM PNG", "a folha ainda não foi gerada"
    folha, meta, _ = montar_folha(modelo)
    nova = np.asarray(folha.convert("RGBA"))
    atual = np.asarray(Image.open(caminho).convert("RGBA"))
    if nova.shape != atual.shape:
        return modelo.nome, "DIFERENTE", f"tamanho {atual.shape[1]}x{atual.shape[0]} -> {nova.shape[1]}x{nova.shape[0]}"
    diferentes = int(np.any(nova != atual, axis=2).sum())
    if diferentes:
        return modelo.nome, "DIFERENTE", f"{diferentes} pixels"
    ficha = catalogo.get(modelo.nome, {})
    campos = [c for c in CAMPOS_DO_CATALOGO if ficha.get(c) != meta.get(c)]
    if campos:
        return modelo.nome, "CATÁLOGO", "muda: " + ", ".join(campos)
    return modelo.nome, "igual", ""


def conferir(filtro=(), com_camadas=False):
    """Confere todas as folhas pedidas. Devolve a lista de (nome, situação, detalhe)."""
    with open(os.path.join(PASTA, "catalogo.json"), encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)
    tarefas = [(i, list(filtro), com_camadas, catalogo) for i in range(len(CATALOGO))]
    with Pool() as pool:
        return [r for r in pool.map(conferir_um, tarefas) if r is not None]


def main():
    argumentos = sys.argv[1:]
    com_camadas = "--camadas" in argumentos
    filtro = [a for a in argumentos if not a.startswith("--")]
    inicio = time.time()
    resultados = conferir(filtro, com_camadas)
    problemas = [r for r in resultados if r[1] != "igual"]
    for nome, situacao, detalhe in problemas:
        print(f"  {situacao:10} {nome}  ({detalhe})")
    print(f"{len(resultados)} folhas conferidas em {time.time() - inicio:.0f}s: "
          f"{len(resultados) - len(problemas)} iguais, {len(problemas)} com diferença")
    sys.exit(1 if problemas else 0)


if __name__ == "__main__":
    main()
