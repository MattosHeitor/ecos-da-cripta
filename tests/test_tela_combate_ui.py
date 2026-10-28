"""Etapa 2 da fase 2: tela de batalha (teclado, descrição curta, alvo, registro, dicas de status)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from jogar import criar_combate_de_teste
from roguelike.golpes import golpe
from roguelike.itens import item
from telas.base import App


def tecla(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)


def quadros(app, n=1, eventos=()):
    for i in range(n):
        app.passo(1 / 30, list(eventos) if i == 0 else [])


@pytest.fixture()
def combate(tmp_path):
    app = App(janela=False)
    app.velocidade = 4.0
    tela = criar_combate_de_teste(app, ["mago:Gelo", "guerreiro"], ["goblin", "aranha"], "floresta", 3, "UI-ETAPA2")
    app.trocar(tela)
    for _ in range(3000):
        if tela.estado == "escolhendo":
            break
        quadros(app)
    assert tela.estado == "escolhendo"
    return app, tela


def test_descricao_curta_tem_efeito_custo_e_alvo():
    linha = golpe("golpe_de_escudo").descricao_curta(1)
    assert "dano" in linha and "2 energia" in linha and "1 inimigo" in linha
    assert "1 aliado" in item("pocao_de_vida").descricao_curta()


def test_menu_inteiro_pelo_teclado(combate):
    app, tela = combate
    heroi = tela.combate.atual
    quadros(app, 2, [tecla(pygame.K_DOWN)])         # foca "Lutar"
    quadros(app, 2, [tecla(pygame.K_RETURN)])
    assert tela.menu == "habilidades"
    quadros(app, 2)                                   # o menu aberto pelo teclado já foca o 1º golpe
    primeiro = tela._botao_focado()
    assert primeiro is not None and primeiro.texto == heroi.habilidades()[0][0].nome
    secoes = tela.linhas_da_descricao()
    assert [s[0] for s in secoes][0].startswith(primeiro.texto), "nome e nível na 1ª linha"
    assert len(secoes) == 3 and "·" in secoes[2][0]                 # efeito, depois custo · alvo
    quadros(app, 2, [tecla(pygame.K_RETURN)])        # Cajado: pede alvo
    assert tela.menu == "alvo"
    antes = tela.indice_alvo
    quadros(app, 2, [tecla(pygame.K_RIGHT)])
    assert tela.indice_alvo != antes
    assert tela.linhas_da_descricao()[0][0].startswith(heroi.habilidades()[0][0].nome)
    quadros(app, 2, [tecla(pygame.K_RETURN)])
    assert tela.estado == "animando"


def test_alvo_apaga_quem_nao_pode_ser_escolhido(combate):
    app, tela = combate
    quadros(app, 2, [tecla(pygame.K_1, "1")])
    quadros(app, 2, [tecla(pygame.K_1, "1")])
    assert tela.menu == "alvo"
    destaques = tela.destaques()
    for heroi in tela.combate.herois:
        visual = tela.visual(heroi)
        if heroi is not tela.combate.atual:
            assert destaques.get(id(visual)) == "apagado"
    assert "alvo" in destaques.values()


def test_registro_recolhe_com_L_e_fica_salvo(combate):
    app, tela = combate
    assert app.opcoes.registro_aberto
    largura_antes = tela.meio.width
    quadros(app, 2, [tecla(pygame.K_l)])
    assert not app.opcoes.registro_aberto
    assert tela.meio.width > largura_antes           # o menu ganha o espaço do registro
    from ui.opcoes import Opcoes
    assert not Opcoes.carregar().registro_aberto


def test_icones_de_status_tem_dica(combate):
    app, tela = combate
    inimigo = tela.combate.inimigos[0]
    tela.combate.aplicar_status(inimigo, "sangramento", 3, 0, 2)
    quadros(app, 2)
    visual = tela.visual(inimigo)
    assert visual.areas_de_status
    area, status = visual.areas_de_status[0]
    quadros(app, 2, [pygame.event.Event(pygame.MOUSEMOTION, pos=area.center, rel=(0, 0), buttons=(0, 0, 0))])
    assert tela.dica is not None and tela.dica[0].startswith("Sangramento")
