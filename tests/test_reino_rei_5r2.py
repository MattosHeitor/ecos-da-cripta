"""Reino dos Ratos, etapa 5R2: o Rei dos Ratos refeito (linhas novas do sprite), a corrida até o trono quando a vida
dele acaba e a proclamação do Édito Real (grande no meio da tela, depois o pergaminho)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from roguelike.classes import criar_heroi
from roguelike.encontros import MontadorDeCombate
from roguelike.run import Run
from telas.combate.edito import ProclamacaoDoEdito
from telas.combate.trono import CorridaAoTrono
from visual.sprites_macabros import Animador, Sprites

from test_telas_fluxo import app, quadros  # noqa: F401  (fixture e ajudantes)


def tela_do_rei(app):  # noqa: F811
    from telas.combate.tela import TelaCombate
    run = Run([criar_heroi("guerreiro"), criar_heroi("sacerdote")], "REI", "reino_dos_ratos")
    total = run.areas_da_regiao()
    run.area = total
    encontro = MontadorDeCombate(run.regiao, total, run.rng("t"), 4, False, total).chefe()
    run.encontro, run.estado = encontro, "encontro"
    tela = TelaCombate(app, run, encontro, lambda r: None)
    app.trocar(tela)
    quadros(app, 2)
    return tela, tela.combate.inimigos[0]


def test_sprite_do_rei_tem_as_linhas_novas():
    sprites = Sprites()
    for linha, n in (("parado", 8), ("correr", 6), ("decreto", 4), ("banquete", 4), ("sentado", 4), ("morte", 4)):
        assert sprites.tem_animacao("rei_dos_ratos", linha) and sprites.quadros_de("rei_dos_ratos", linha) == n
    assert Animador.VELOCIDADE["correr"] > Animador.VELOCIDADE["parado"]


def test_animador_segura_o_ultimo_quadro():
    sprites = Sprites()
    animador = Animador(sprites, "rei_dos_ratos")
    animador.tocar("decreto", segurar=1.0)
    animador.atualizar(0.9)                                 # 4 quadros a 5 por segundo = 0,8 s
    assert animador.anim == "decreto" and animador.indice == 3
    animador.atualizar(1.0)
    assert animador.anim == "parado"


def test_corrida_vai_ate_o_estrado_e_pula_para_o_assento():
    class Visual:
        x, y = 860.0, 558.0
    corrida = CorridaAoTrono(Visual(), (710, 504), (640, 404))
    assert corrida.correndo() and corrida.para_a_esquerda()
    corrida.atualizar(CorridaAoTrono.CORRER)
    x, y, chao = corrida.posicao()
    assert (round(x), round(chao)) == (710, 504) and not corrida.terminou()
    corrida.atualizar(CorridaAoTrono.SUBIR)
    x, y, chao = corrida.posicao()
    assert corrida.terminou() and (round(x), round(y)) == (640, 404)


def test_rei_corre_para_o_trono_e_fica_sentado(app):  # noqa: F811
    tela, rei = tela_do_rei(app)
    for _ in range(4):
        tela.combate.causar_dano(rei, 9999, tela.combate.herois[0])
    tela.enfileirar()
    for _ in range(60):
        quadros(app, 1)
        if tela.corrida is not None:
            break
    assert tela.corrida is not None and tela.visual(rei) not in tela.lado_inimigos
    tela.desenhar(app.tela)                                 # (correndo)
    quadros(app, 90)
    assert tela.corrida is None and tela.no_trono == {"chave": "rei_dos_ratos"}
    tela.desenhar(app.tela)


def test_edito_aparece_grande_e_depois_vai_para_o_pergaminho(app):  # noqa: F811
    tela, rei = tela_do_rei(app)
    edito = next(p for p in rei.passivas if p.dados.get("golpe") == "edito_real")
    edito.disparar(rei, tela.combate)
    tela.estado, tela.menu = "animando", "principal"
    tela.enfileirar()
    for _ in range(60):
        quadros(app, 1)
        if tela.proclamacao is not None:
            break
    proclamacao = tela.proclamacao
    assert proclamacao is not None and proclamacao.ativa(tela.tempo) and not proclamacao.chegou(tela.tempo)
    assert tela.desenhar_edito(app.tela) == 56                     # o pergaminho espera a lei chegar
    assert tela.visual(rei).animador.anim == "decreto"             # o cetro erguido
    tela.desenhar(app.tela)
    assert proclamacao.chegou(proclamacao.inicio + proclamacao.duracao)


def test_proclamacao_desenha_em_todas_as_fases():
    pygame.init()
    tela = pygame.Surface((1280, 720))
    proclamacao = ProclamacaoDoEdito("Proibido Atacar o Rei", "Ninguém toca na Coroa.", 0.0, (1135, 117))
    for agora in (0.0, 0.1, 0.5, 1.5, 2.3, 2.6, 2.75):
        proclamacao.desenhar(tela, agora)
    assert not proclamacao.ativa(proclamacao.duracao + 0.01)
