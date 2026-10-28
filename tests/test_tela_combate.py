"""Teste da tela de combate SEM janela (o pygame desenha numa tela invisível).

Joga combates inteiros apertando teclas, para garantir que a interface não quebra:
habilidades com alvo, itens, concentrar, invocações e o fim da luta.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from jogar import criar_combate_de_teste
from telas.base import App


@pytest.fixture(scope="module")
def app():
    aplicativo = App(janela=False)
    aplicativo.velocidade = 4.0          # animações 4x mais rápidas no teste
    # (sem pygame.quit(): as fontes guardadas em cache seriam fechadas e os outros testes cairiam)
    return aplicativo


def tecla(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)


def quadros(app, n, eventos=()):
    for i in range(n):
        app.passo(1 / 30, list(eventos) if i == 0 else [])


def esperar_vez(app, tela, limite=3000):
    for _ in range(limite):
        if tela.estado in ("escolhendo", "fim"):
            return
        quadros(app, 1)
    raise AssertionError("o combate travou esperando a vez")


def jogar_ate_o_fim(app, tela, acoes):
    """Repete as ações (listas de teclas) até o combate acabar."""
    for rodada in range(200):
        esperar_vez(app, tela)
        if tela.estado == "fim":
            return
        for k, u in acoes[rodada % len(acoes)]:
            quadros(app, 2, [tecla(k, u)])
        quadros(app, 2, [tecla(pygame.K_RETURN, "\r")])
        if tela.estado == "escolhendo":
            # a ação não valeu (sem energia/alvo): volta até o menu principal e concentra
            while tela.menu != "principal":
                quadros(app, 1, [tecla(pygame.K_ESCAPE)])
            quadros(app, 1, [tecla(pygame.K_3, "3")])
        assert not tela.pausado
    raise AssertionError("o combate não terminou")


UM, DOIS, TRES = (pygame.K_1, "1"), (pygame.K_2, "2"), (pygame.K_3, "3")


def test_combate_inteiro_pela_tela(app):
    terminou = []
    tela = criar_combate_de_teste(app, ["guerreiro", "sacerdote"], ["goblin", "aranha"], "floresta", 2, "UI1")
    tela.ao_terminar = terminou.append
    app.trocar(tela)
    jogar_ate_o_fim(app, tela, [[UM, UM], [DOIS, UM], [TRES], [UM, DOIS]])
    quadros(app, 120)
    assert tela.combate.resultado in ("vitoria", "derrota")
    quadros(app, 2, [tecla(pygame.K_RETURN, "\r")])
    assert terminou, "o fim do combate deveria chamar ao_terminar"


def test_combate_com_chefe_e_invocacoes(app):
    tela = criar_combate_de_teste(app, ["mago:Gelo", "patrulheira", "bardo"], ["aranha_mae"], "floresta", 6, "UI2")
    tela.ao_terminar = lambda recompensa: None
    app.trocar(tela)
    # a 3ª ação usa o pergaminho do lobo (item 3 da lista), para testar invocação dos heróis
    jogar_ate_o_fim(app, tela, [[UM, DOIS], [DOIS, TRES], [UM, UM], [TRES]])
    assert tela.estado == "fim"


def test_pausa_nao_quebra(app):
    tela = criar_combate_de_teste(app, ["ladino"], ["goblin"], "floresta", 1, "UI3")
    app.trocar(tela)
    esperar_vez(app, tela)
    quadros(app, 2, [tecla(pygame.K_ESCAPE)])
    assert tela.pausado
    quadros(app, 2, [tecla(pygame.K_ESCAPE)])
    assert not tela.pausado
