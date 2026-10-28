"""Simula muitas runs com o piloto automático para ajudar a balancear.

    python ferramentas/simular_runs.py [quantidade] [classes separadas por vírgula] [ameaça]

Mostra até onde os grupos chegam, em que nível, quantos combates vencem e a taxa de vitória.
As runs rodam em paralelo (uma por processo); ameaça = nível de ameaça da run (regras.json "ameaca").
"""
import os
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from roguelike.run import Run  # noqa: E402
from roguelike.piloto_automatico import Piloto, grupo_padrao  # noqa: E402


def uma_run(argumentos):
    numero, classes, ameaca = argumentos
    run = Run(grupo_padrao(classes), semente=f"SIM{numero}")
    run.ameaca = ameaca
    resumo = Piloto(run).jogar()
    onde = "VITÓRIA" if resumo["resultado"] == "vitoria" else f"{resumo['regiao']} área {resumo['area']}"
    return onde, max(h.nivel for h in run.grupo.herois), resumo["areas_vencidas"], resumo["brasas"]


def simular(quantidade, classes, ameaca=0, pool=None):
    """Roda as runs e devolve a taxa de vitória (0 a 1); imprime o resumo."""
    tarefas = [(numero, classes, ameaca) for numero in range(quantidade)]
    resultados = (pool.map(uma_run, tarefas) if pool else [uma_run(t) for t in tarefas])
    fins = Counter(onde for onde, *_ in resultados)
    niveis = [r[1] for r in resultados]
    areas = [r[2] for r in resultados]
    brasas = [r[3] for r in resultados]
    taxa = fins["VITÓRIA"] / quantidade
    print(f"Grupo: {', '.join(classes)}  ({quantidade} runs, ameaça {ameaca})  vitória {taxa:.0%}")
    for onde, vezes in fins.most_common(6):
        print(f"  {vezes:4d}x  {onde}")
    print(f"  áreas vencidas (média) {sum(areas) / len(areas):.1f}   nível final (média) {sum(niveis) / len(niveis):.1f}"
          f"   brasas (média) {sum(brasas) / len(brasas):.0f}")
    return taxa


if __name__ == "__main__":
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    classes = sys.argv[2].split(",") if len(sys.argv) > 2 else ["guerreiro", "sacerdote", "patrulheira"]
    ameaca = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    with Pool() as pool:
        simular(quantidade, classes, ameaca, pool)
