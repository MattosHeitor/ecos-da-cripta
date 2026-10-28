"""Leitura dos arquivos de dados (JSON) da pasta roguelike/dados (o lugar vem de caminhos.py).

Cada arquivo é lido uma vez só e guardado. Chaves que começam com "_"
são comentários e são ignoradas pela função sem_comentarios().
"""

import json
import os

from caminhos import CAMINHOS

PASTA_DADOS = CAMINHOS.dados

_lidos = {}


def carregar(nome):
    """Devolve o conteúdo de dados/<nome>.json (já convertido para dict)."""
    if nome not in _lidos:
        caminho = os.path.join(PASTA_DADOS, nome + ".json")
        with open(caminho, encoding="utf-8") as arquivo:
            _lidos[nome] = json.load(arquivo)
    return _lidos[nome]


def sem_comentarios(dicionario):
    """O mesmo dicionário sem as chaves de comentário (que começam com "_")."""
    return {chave: valor for chave, valor in dicionario.items() if not chave.startswith("_")}


def regras():
    return carregar("regras")
