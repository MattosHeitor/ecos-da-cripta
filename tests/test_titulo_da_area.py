"""Fase 4, etapa 1: tela de título da fase e os portões do fim de ato (sem texto cortado)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from roguelike.piloto_automatico import grupo_padrao
from roguelike.progresso import Progresso
from roguelike.regioes import todas_as_regioes, progressao
from roguelike.run import Run
from telas import comum
from telas.base import App
from ui import texto as T


def preparar(tmp_path):
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    app = App(janela=False)
    app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    return app


def test_titulo_de_cada_fase_sem_texto_cortado_e_segue_para_o_mapa(tmp_path):
    app = preparar(tmp_path)
    try:
        from telas.titulo_da_area import TelaTituloDaArea
        antes = len(T.TRUNCAMENTOS)
        for chave in todas_as_regioes():
            run = Run(grupo_padrao(("guerreiro",)), "TITULO")
            run.regiao_atual = chave
            seguiu = []
            tela = TelaTituloDaArea(app, run, lambda: seguiu.append(True))
            app.trocar(tela)
            for _ in range(60):
                app.passo(1 / 30, [])
            assert tela.nome.get_width() <= 1100 and not seguiu
            app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, unicode=" ", mod=0)])
            assert seguiu == [True]
        assert T.TRUNCAMENTOS[antes:] == []
    finally:
        comum.ArquivoDaRun.caminho = None


def test_portoes_de_todos_os_atos_desenham_sem_cortar(tmp_path):
    app = preparar(tmp_path)
    try:
        from telas.mapa import TelaMapa
        antes = len(T.TRUNCAMENTOS)
        for ato in progressao().atos:
            run = Run(grupo_padrao(("guerreiro", "mago")), "PORTOES")
            run.portoes = [[fase, fase in ("minas", "catedral", "floresta")] for fase in ato.fases]
            app.trocar(TelaMapa(app, run))
            app.passo(1 / 30, [])
            app.passo(1 / 30, [])
        assert T.TRUNCAMENTOS[antes:] == []
    finally:
        comum.ArquivoDaRun.caminho = None


def test_paleta_tinge_o_cenario_provisorio():
    pygame.init()
    from visual.cenario_macabro import CenarioMacabro, cena_da_area, paleta_do_lugar
    nome, variante = cena_da_area("floresta", 1, total=6)
    normal = pygame.Surface((1280, 720))
    tingido = pygame.Surface((1280, 720))
    CenarioMacabro(nome, variante, hora=1.0).desenhar(normal)
    CenarioMacabro(nome, variante, hora=1.0, paleta=(255, 150, 140)).desenhar(tingido)
    r1, g1, b1, _ = pygame.transform.average_color(normal)
    r2, g2, b2, _ = pygame.transform.average_color(tingido)
    assert g2 < g1 and r2 / max(1, g2) > r1 / max(1, g1)       # mais vermelho
    assert paleta_do_lugar("floresta") is None
