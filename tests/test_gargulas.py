"""Gárgulas Vivas: 3 variantes de sprite (só visual) e a animação "despertar" (pedra -> viva)."""

import json
import os

from roguelike.dados import carregar, sem_comentarios
from roguelike.inimigos import criar_inimigo

CATALOGO = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites_macabros", "catalogo.json")


def test_variantes_existem_e_tem_despertar():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    for ficha in sem_comentarios(carregar("inimigos")["inimigos"]).values():
        for sprite in ficha.get("variantes", []):
            assert sprite in catalogo, sprite
    for nome in ("gargula_viva", "gargula_calha", "gargula_quimera"):
        assert "despertar" in catalogo[nome]["animacoes"]


def test_cada_gargula_que_surge_usa_a_proxima_variante_com_a_mesma_ficha():
    gargulas = [criar_inimigo("gargula_viva") for _ in range(3)]
    assert {g.sprite for g in gargulas} == {"gargula_viva", "gargula_calha", "gargula_quimera"}
    assert len({(g.vida_maxima, g.defesa_base, tuple(g.ficha["habilidades"])) for g in gargulas}) == 1
