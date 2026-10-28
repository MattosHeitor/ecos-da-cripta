"""Mede a taxa de vitória de vários grupos (todas as classes) em vários níveis de ameaça.

    python ferramentas/balancear.py [runs por grupo] [ameaças separadas por vírgula]

Usa o piloto automático (ferramentas/simular_runs.py). Meta da etapa 8: no máximo 20% de vitória na
ameaça 0, caindo a cada nível de ameaça.
"""
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simular_runs import simular  # noqa: E402

GRUPOS = [["guerreiro", "sacerdote", "patrulheira"], ["barbaro", "mago", "ladino"],
          ["bardo", "monge", "feiticeira"], ["guerreiro", "bobo", "mago"]]


def main():
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    ameacas = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0]
    with Pool() as pool:
        for ameaca in ameacas:
            taxas = [simular(quantidade, grupo, ameaca, pool) for grupo in GRUPOS]
            print(f"== ameaça {ameaca}: " + "  ".join(f"{t:.0%}" for t in taxas) +
                  f"   (média {sum(taxas) / len(taxas):.0%}, máximo {max(taxas):.0%})\n")


if __name__ == "__main__":
    main()
