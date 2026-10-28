"""Fase 3, etapa 4: as regiões a céu aberto passam do dia à noite ao longo das áreas."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from visual.cenario_macabro import CenarioMacabro, hora_da_area, nome_da_hora, catalogo, PASTA


def test_hora_anda_do_dia_a_noite_nas_regioes_a_ceu_aberto():
    assert hora_da_area("floresta", 1) == 0.0 and hora_da_area("floresta", 8) == 1.0
    assert 0 < hora_da_area("floresta", 4) < 1
    assert hora_da_area("circo", 1) == 0.0 and hora_da_area("circo", 5) == 1.0
    assert hora_da_area("minas", 1) == 1.0 and hora_da_area("catedral", 3) == 1.0     # lugares cobertos
    assert nome_da_hora(0.0) == "Dia" and nome_da_hora(1.0) == "Noite" and nome_da_hora(0.5) == "Entardecer"


def test_cenas_com_ciclo_tem_ceu_de_dia_e_de_entardecer():
    for chave, config in catalogo().items():
        if config.get("ciclo"):
            for sufixo in ("ceu_dia", "ceu_tarde"):
                assert os.path.exists(os.path.join(PASTA, f"{chave}_{sufixo}.png")), (chave, sufixo)
    assert catalogo()["floresta_0"].get("ciclo") and not catalogo()["minas_0"].get("ciclo")


def test_de_dia_as_luzes_apagam_e_os_vagalumes_somem():
    dia, noite = CenarioMacabro("floresta", 0, hora=0.0), CenarioMacabro("floresta", 0, hora=1.0)
    assert noite.luzes and not dia.luzes
    tipos_dia = [type(p).__name__ for p in dia.particulas]
    tipos_noite = [type(p).__name__ for p in noite.particulas]
    assert "VagaLume" in tipos_noite and "VagaLume" not in tipos_dia and "Poeira" in tipos_dia
    # o céu de dia é mais claro que o de noite
    def brilho(cenario):
        tela = pygame.Surface((1280, 720))
        cenario.desenhar(tela)
        r, g, b, _ = pygame.transform.average_color(tela, (0, 0, 1280, 300))
        return r + g + b
    assert brilho(dia) > brilho(noite) + 60


def test_lugar_coberto_ignora_a_hora():
    assert CenarioMacabro("minas", 0, hora=0.0).hora == 1.0
