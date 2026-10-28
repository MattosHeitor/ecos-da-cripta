"""Os cenários macabros existem e carregam para todas as áreas de todas as regiões."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from roguelike.regioes import todas_as_regioes
from visual.cenario_macabro import CenarioMacabro, catalogo, cena_da_area


def test_toda_area_tem_cenario():
    """Em qualquer tamanho sorteado (3 a 8 áreas, ou o original), toda área tem cena; fases novas usam a provisória."""
    for regiao in todas_as_regioes().values():
        for total in (3, 4, 6, 8, regiao.areas):
            for area in range(1, total + 1):
                nome, variante = cena_da_area(regiao.chave, area, total=total)
                assert f"{nome}_{variante}" in catalogo(), (regiao.chave, area, total)
        nome, variante = cena_da_area(regiao.chave, regiao.areas, "chefe")
        assert f"{nome}_{variante}" in catalogo()
        if regiao.sala_do_chefe:
            assert nome == regiao.sala_do_chefe


def test_variantes_mudam_ao_longo_da_regiao():
    vistas = {cena_da_area("floresta", area) for area in range(1, 9)}
    assert len(vistas) >= 3


def test_cenarios_carregam_e_animam():
    pygame.init()
    tela = pygame.Surface((1280, 720))
    for chave in catalogo():
        nome, variante = chave.rsplit("_", 1)
        cenario = CenarioMacabro(nome, int(variante))
        for _ in range(5):
            cenario.atualizar(0.1)
        cenario.desenhar(tela)
        cenario.desenhar_frente(tela)
        assert cenario.chave == chave
