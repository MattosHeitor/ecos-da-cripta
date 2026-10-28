"""Fase 3, etapa 6: a tela inicial (logo, menu pelo teclado, atalhos)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from roguelike.progresso import Progresso
from telas import comum
from telas.base import App


def test_titulo_abre_com_fade_e_o_atalho_leva_ao_acampamento(tmp_path):
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")           # sem run salva
    try:
        app = App(janela=False)
        app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
        from telas.titulo import TelaTitulo, logo
        tela = TelaTitulo(app)
        app.trocar(tela)
        app.passo(1 / 30, [])
        escuro = pygame.transform.average_color(app.tela)
        for _ in range(60):
            app.passo(1 / 30, [])
        claro = pygame.transform.average_color(app.tela)
        assert sum(claro[:3]) > sum(escuro[:3])                            # o fade do preto terminou
        assert [nome for nome, _, _ in tela.opcoes()][0] == "Acampamento"
        imagem = logo("TESTE", 40)
        cores = {imagem.get_at((x, y))[:3] for x in range(imagem.get_width()) for y in range(imagem.get_height())
                 if imagem.get_at((x, y))[3] == 255}
        assert any(r > 200 and g > 150 and b < 150 for r, g, b in cores)    # letras douradas, não brancas
        app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1, unicode="1", mod=0)])
        app.passo(1 / 30, [])
        assert type(app.atual).__name__ == "TelaAcampamento"
    finally:
        comum.ArquivoDaRun.caminho = None
