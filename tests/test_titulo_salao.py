"""Etapa 6: o salão da Cripta na tela de título (camadas, velas, feixes, estátuas e o reflexo do logo)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from telas.base import App


def test_salao_tem_camadas_velas_feixes_e_estatuas():
    app = App(janela=False)
    from visual.salao_da_cripta import SalaoDaCripta
    salao = SalaoDaCripta()
    assert set(salao.camadas) == {"fundo", "colunas", "frente"}
    assert len(salao.velas) >= 20 and {v[3] for v in salao.velas} == {"fundo", "colunas", "frente"}
    assert len(salao.feixes) == 3
    assert len(salao.estatuas(app.sprites)) == 2
    tela = pygame.Surface((1280, 720))
    salao.desenhar_fundo(tela)
    salao.desenhar_colunas(tela, app.sprites)
    salao.desenhar_frente(tela)
    vx, vtopo, vbase, _ = salao.vitral
    r, g, b, _ = tela.get_at((int(vx), int((vtopo + vbase) / 2)))
    assert b > 60                                              # o vitral aceso pela lua


def test_reflexo_do_logo_fica_so_nas_letras():
    App(janela=False)
    from telas.titulo import logo, faixa_de_brilho
    imagem = logo("ECOS", 60)
    faixa = faixa_de_brilho(imagem, 0.5)
    for x in range(faixa.get_width()):
        for y in range(faixa.get_height()):
            if faixa.get_at((x, y))[3] > 0:
                assert imagem.get_at((x, y))[3] > 0              # nunca acende fora das letras
