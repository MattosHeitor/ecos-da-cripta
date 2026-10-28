"""Fase 4, equipamentos E1 nas telas: arsenal no acampamento, fuga pelo mapa, Grupo com 9 espaços e a janela."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelike.progresso import Progresso
from telas import comum, fluxo
from telas.base import App
from ui import texto as T


@pytest.fixture()
def app(tmp_path):
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    aplicativo = App(janela=False)
    aplicativo.velocidade = 4.0
    aplicativo.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    yield aplicativo
    comum.ArquivoDaRun.caminho = None


def quadros(app, n=3):
    for _ in range(n):
        app.passo(1 / 30, [])


def test_arsenal_da_e_tira_pecas_sem_cortar_texto(app):
    from telas.inventario import TelaInventario
    progresso = app.progresso
    progresso.arsenal.guardar(["machado_orc", "escudo_de_madeira", "capuz_do_coveiro", "coroa_de_espinhos_maldita"])
    antes = len(T.TRUNCAMENTOS)
    fluxo.abrir_arsenal(app)
    tela = app.atual
    assert isinstance(tela, TelaInventario)
    quadros(app)
    tela.equipar("escudo_de_madeira")
    tela.equipar("machado_orc")                              # duas mãos: o escudo sai
    vaga = progresso.expedicao_atual().vagas[0]
    assert vaga.equipamento == {"arma": "machado_orc"}
    assert tela.heroi.equipamento["arma"].chave == "machado_orc"      # o boneco já mostra
    tela.indice = 1
    tela.equipar("machado_orc")                              # só existe um
    assert "arma" not in progresso.expedicao_atual().vagas[1].equipamento
    tela.indice = 0
    tela.desequipar("arma")
    assert vaga.equipamento == {}
    quadros(app)
    assert T.TRUNCAMENTOS[antes:] == []
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0)])
    quadros(app)
    assert type(app.atual).__name__ == "TelaAcampamento"


def clique(app, posicao, botao=1, soltar=True):
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=posicao, button=botao)])
    if soltar:
        app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=posicao, button=botao)])


def area_de(tela, alvo):
    return next(rect for rect, a in tela.areas if a == alvo)


def test_inventario_da_run_arrasta_duplo_clique_e_compara(app):
    run = app.progresso.criar_run(app.progresso.expedicao_atual().criar_herois(app.progresso), "INVENT")
    run.grupo.bau.adicionar("botas_gastas")
    run.grupo.bau.adicionar("elmo_de_ferro")
    run.grupo.bau.adicionar("osso", 3)
    fluxo.abrir_inventario(app, run, aba="bau")                    # (abre na mochila; aqui, os itens estão no baú)
    tela = app.atual
    quadros(app)
    heroi = tela.heroi
    # arrastar as botas até o espaço das botas
    origem = area_de(tela, ("item", "bau", "botas_gastas")).center
    destino = area_de(tela, ("espaco", "botas")).center
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=origem, button=1)])
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEMOTION, pos=destino, rel=(0, 0), buttons=(1, 0, 0))])
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=destino, button=1)])
    assert heroi.equipamento["botas"].chave == "botas_gastas"
    # duplo clique no elmo equipa
    quadros(app, 1)
    alvo = area_de(tela, ("item", "bau", "elmo_de_ferro")).center
    clique(app, alvo)
    clique(app, alvo)
    assert heroi.equipamento["cabeca"].chave == "elmo_de_ferro"
    # comparar: o capuz troca esquiva/defesa em relação ao elmo
    from roguelike.itens import item
    diferencas = __import__("roguelike.resumo_do_heroi", fromlist=["x"]).comparar(heroi, item("capuz_de_viajante"))
    assert diferencas["defesa"] < 0 and diferencas["esquiva"] > 0
    # filtro de materiais e descarte com o botão direito
    tela.filtros["tipo"] = "material"
    quadros(app)
    clique(app, area_de(tela, ("item", "bau", "osso")).center, botao=3, soltar=False)
    assert tela.dialogo is not None
    tela.descartar("osso")
    assert run.grupo.bau.quantidade("osso") == 2
    tela.dialogo = None
    # teclado: Q/E trocam de herói
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode="e", mod=0)])
    assert tela.indice == 1


def test_inventario_abre_pelo_mapa_com_i(app):
    run = app.progresso.criar_run(app.progresso.expedicao_atual().criar_herois(app.progresso), "TECLAI")
    fluxo.ir_para_mapa(app, run)
    quadros(app)
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, unicode="i", mod=0)])
    quadros(app)
    assert type(app.atual).__name__ == "TelaInventario"
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0)])
    quadros(app)
    assert type(app.atual).__name__ == "TelaMapa"


def test_sair_da_run_pelo_menu_leva_ao_guardiao(app):
    run = app.progresso.criar_run(app.progresso.expedicao_atual().criar_herois(app.progresso), "FUGA")
    fluxo.ir_para_mapa(app, run)
    quadros(app)
    mapa = app.atual
    mapa.perguntar_fuga()
    assert mapa.dialogo is not None
    mapa.fugir()
    quadros(app)
    assert type(app.atual).__name__ == "TelaCombate" and app.atual.encontro.tipo == "fuga"


def test_painel_do_grupo_com_nove_espacos_sem_cortar(app):
    from roguelike.itens import item
    from telas.grupo import TelaGrupo
    run = app.progresso.criar_run(app.progresso.expedicao_atual().criar_herois(app.progresso), "GRUPO")
    heroi = run.grupo.herois[0]
    for chave in ("capuz_do_coveiro", "casaco_do_coveiro", "grevas_de_ferro_negro", "botas_do_enforcado", "capa_de_la",
                  "anel_do_pacto", "faca_enferrujada", "escudo_de_ferro_negro"):
        heroi.equipar(item(chave))
    antes = len(T.TRUNCAMENTOS)
    app.trocar(TelaGrupo(app, run, "herois", lambda: None))
    quadros(app)
    assert T.TRUNCAMENTOS[antes:] == []


def test_encaixe_converte_o_mouse_da_janela_para_o_jogo():
    from ui.escala import Encaixe
    encaixe = Encaixe()
    encaixe.ajustar((1169, 658))                             # notebook 1366x768: a janela encolhe
    assert encaixe.para_o_jogo((584, 329)) == (639, 360)
    encaixe.ajustar((1920, 1080))                            # tela cheia: 1,5x
    assert encaixe.para_o_jogo((960, 540)) == (640, 360)
    encaixe.ajustar((1920, 1200))                            # monitor 16:10: faixas pretas em cima e embaixo
    assert encaixe.deslocamento == (0, 60) and encaixe.para_o_jogo((0, 60)) == (0, 0)


def test_fim_de_run_da_fuga_mostra_o_arsenal(app):
    from telas.fim_de_run import TelaFimDeRun
    run = app.progresso.criar_run(app.progresso.expedicao_atual().criar_herois(app.progresso), "FIM")
    run.grupo.bau.adicionar("capuz_do_coveiro")
    run.resultado = "fuga"
    relatorio = app.progresso.registrar_fim_de_run(run)
    assert relatorio.itens_guardados == ["capuz_do_coveiro"]
    antes = len(T.TRUNCAMENTOS)
    tela = TelaFimDeRun(app, run, relatorio)
    app.trocar(tela)
    quadros(app)
    assert tela.fuga and T.TRUNCAMENTOS[antes:] == []

def test_inventario_com_peca_sob_o_mouse_e_set_sem_cortar(app):
    from roguelike.itens import item
    run = app.progresso.criar_run(app.progresso.expedicao_atual().criar_herois(app.progresso), "CORTE")
    heroi = run.grupo.herois[0]
    for chave in ("capuz_do_coveiro", "casaco_do_coveiro", "botas_do_coveiro", "anel_do_pacto"):
        heroi.equipar(item(chave))
    run.receber_itens({"pa_do_coveiro": 1, "espada_de_prata": 1, "osso": 2})
    fluxo.abrir_inventario(app, run)
    tela = app.atual
    quadros(app)
    antes = len(T.TRUNCAMENTOS)
    for rect, alvo in list(tela.areas):
        if alvo[0] in ("item", "espaco"):
            app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center, rel=(0, 0), buttons=(0, 0, 0))])
            app.passo(1 / 30, [])
    assert T.TRUNCAMENTOS[antes:] == []