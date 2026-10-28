"""Etapa 3: mochila (com dono), baú da equipe (colocar/retirar com registro) e fabricação que usa a mochila do
herói + o baú. MP2: o dono é o Jogador que comanda o herói. MP4: a mochila é do jogador (os heróis dele a dividem)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from roguelike.classes import criar_heroi
from roguelike.fabricacao import Estoque, situacao, SO_MOCHILA, COM_BAU, FALTA, receita
from roguelike.grupo import Grupo
from roguelike.inventario import Inventario
from roguelike.posse import Jogador, InventarioPessoal, BauDaEquipe


def grupo_de_dois():
    return Grupo([criar_heroi("guerreiro", "Doran"), criar_heroi("mago", "Ilse")])


def grupo_de_dois_jogadores():
    """Doran com o jogador local, Ilse com a Bia (como seria no multiplayer)."""
    grupo = grupo_de_dois()
    grupo.dar_heroi(grupo.herois[1], Jogador("bia", "Bia"))
    return grupo


def test_no_solo_um_jogador_comanda_todos_e_e_dono_das_mochilas():
    grupo = grupo_de_dois()
    doran, ilse = grupo.herois
    assert [j.id for j in grupo.jogadores] == ["local"]
    assert isinstance(doran.inventario, InventarioPessoal) and doran.inventario.dono == doran.jogador
    assert doran.jogador == ilse.jogador and isinstance(grupo.bau, BauDaEquipe)
    assert grupo.herois_de(doran.jogador) == [doran, ilse]


def test_dar_um_heroi_a_outro_jogador_leva_a_mochila():
    grupo = grupo_de_dois_jogadores()
    doran, ilse = grupo.herois
    assert [j.id for j in grupo.jogadores] == ["local", "bia"]
    assert ilse.jogador.nome == "Bia" and ilse.inventario.dono == ilse.jogador and doran.jogador.id == "local"
    assert grupo.herois_de(grupo.jogador("bia")) == [ilse]


def test_colocar_e_retirar_do_bau_so_mexe_nas_proprias_mochilas():
    grupo = grupo_de_dois_jogadores()
    doran, ilse = grupo.herois
    doran.inventario.adicionar("osso", 3)
    assert not grupo.bau.colocar(ilse.jogador, doran.inventario, "osso")       # não é mochila da Bia
    assert grupo.colocar_no_bau(doran, "osso", 2)
    assert grupo.bau.quantidade("osso") == 2 and doran.inventario.quantidade("osso") == 1
    assert not grupo.bau.retirar(doran.jogador, ilse.inventario, "osso")       # para a mochila de outro: não
    assert grupo.pegar_do_bau(ilse, "osso")
    assert ilse.inventario.quantidade("osso") == 1
    acoes = [(m.jogador.nome, m.heroi, m.acao, m.quantidade) for m in grupo.bau.registro]
    assert acoes == [("Você", "Doran", "colocar", 2), ("Bia", "Ilse", "retirar", 1)]


def test_quem_comanda_cada_heroi_vai_no_save_da_run():
    from roguelike.progresso import Progresso
    from roguelike.run import Run
    run = Progresso().criar_run([criar_heroi("guerreiro", "Doran"), criar_heroi("mago", "Ilse")], "DONOS")
    run.grupo.dar_heroi(run.grupo.herois[1], Jogador("bia", "Bia", (200, 80, 80)))
    copia = Run.de_dict(run.para_dict())
    doran, ilse = copia.grupo.herois
    assert [j.id for j in copia.grupo.jogadores] == ["local", "bia"] and ilse.jogador.cor == (200, 80, 80)
    assert doran.jogador.id == "local" and ilse.jogador.id == "bia" and ilse.inventario.dono == ilse.jogador
    antigo = run.para_dict()
    antigo.pop("jogadores")
    for heroi in antigo["herois"]:
        heroi.pop("jogador")
    velha = Run.de_dict(antigo)                                                 # save de antes: tudo do local
    assert {h.jogador.id for h in velha.grupo.herois} == {"local"}


def test_passar_um_item_vai_pelo_bau_e_respeita_a_mochila_cheia():
    sozinho = grupo_de_dois()
    assert sozinho.herois[0].inventario is sozinho.herois[1].inventario          # o mesmo jogador: mesma mochila
    sozinho.herois[0].inventario.adicionar("osso")
    assert not sozinho.passar(*sozinho.herois, "osso")                            # (não há o que passar)
    grupo = grupo_de_dois_jogadores()
    doran, ilse = grupo.herois
    doran.inventario.adicionar("pocao_de_vida", 2)
    assert grupo.passar(doran, ilse, "pocao_de_vida")
    assert ilse.inventario.quantidade("pocao_de_vida") == 1 and grupo.bau.quantidade("pocao_de_vida") == 0
    doran.inventario.adicionar("osso", 1)
    for i in range(ilse.inventario.capacidade - len(ilse.inventario.itens)):   # mochila dela lotada de pilhas
        ilse.inventario.itens[f"x{i}"] = 1
    assert not grupo.passar(doran, ilse, "osso")                                # pilha nova não cabe
    assert grupo.passar(doran, ilse, "pocao_de_vida")                           # na pilha que ela já tem, cabe
    assert doran.inventario.quantidade("osso") == 1 and grupo.bau.quantidade("osso") == 0   # nada se perdeu


def test_baú_antigo_vira_baú_da_equipe():
    grupo = grupo_de_dois()
    antigo = Inventario()
    antigo.adicionar("osso", 4)
    grupo.bau = antigo                                                          # (como o save antigo carrega)
    assert isinstance(grupo.bau, BauDaEquipe) and grupo.bau.quantidade("osso") == 4


def test_estoque_gasta_primeiro_a_mochila_e_depois_o_bau():
    mochila, bau = InventarioPessoal(10, Jogador("a", "A")), BauDaEquipe()
    mochila.adicionar("osso", 2)
    bau.adicionar("osso", 5)
    estoque = Estoque(mochila, bau)
    assert estoque.quantidade("osso") == 7 and estoque.remover("osso", 4)
    assert mochila.quantidade("osso") == 0 and bau.quantidade("osso") == 3


def test_situacao_da_receita_e_fabricar_com_a_mochila_e_o_bau():
    from roguelike.progresso import Progresso
    run = Progresso().criar_run([criar_heroi("guerreiro", "Doran")], "POSSE")
    heroi, bau = run.grupo.herois[0], run.grupo.bau
    pocao = receita("pocao_de_vida")
    heroi.inventario.itens.clear()
    bau.itens.clear()
    assert situacao(pocao, heroi.inventario, bau) == FALTA
    for chave, n in pocao.ingredientes.items():
        bau.adicionar(chave, n)
    assert situacao(pocao, heroi.inventario, bau) == COM_BAU
    for chave, n in pocao.ingredientes.items():
        bau.remover(chave, n)
        heroi.inventario.adicionar(chave, n)
    assert situacao(pocao, heroi.inventario, bau) == SO_MOCHILA
    assert run.fabricar("pocao_de_vida", heroi)
    assert heroi.inventario.tem("pocao_de_vida")                               # o feito vai para a mochila dele


def test_arrastar_da_mochila_para_a_aba_do_bau_e_shift_clique_de_volta(tmp_path, monkeypatch):
    from roguelike.progresso import Progresso
    from telas import comum, fluxo
    from telas.base import App
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    try:
        app = App(janela=False)
        app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
        run = app.progresso.criar_run([criar_heroi("guerreiro", "Doran"), criar_heroi("mago", "Ilse")], "ARRASTO")
        mochila = run.grupo.herois[0].inventario
        mochila.itens.clear()
        mochila.adicionar("osso", 1)
        fluxo.abrir_inventario(app, run, lambda: None)
        tela = app.atual
        for _ in range(3):
            app.passo(0.1, [])
        origem = next(r for r, a in tela.areas if a == ("item", "mochila", "osso")).center   # (MP7: lado a lado)
        destino = next(r for r, a in tela.areas if a == ("grade", "bau")).center
        app.passo(0.1, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=origem, button=1)])
        app.passo(0.1, [pygame.event.Event(pygame.MOUSEMOTION, pos=destino, rel=(0, 0), buttons=(1, 0, 0))])
        app.passo(0.1, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=destino, button=1)])
        assert run.grupo.bau.tem("osso") and not mochila.tem("osso")
        app.passo(0.1, [])
        no_bau = next(r for r, a in tela.areas if a == ("item", "bau", "osso")).center
        monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_LSHIFT)
        app.passo(0.1, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=no_bau, button=1)])
        assert mochila.tem("osso") and not run.grupo.bau.tem("osso")
        assert [m.acao for m in run.grupo.bau.registro] == ["colocar", "retirar"]
    finally:
        comum.ArquivoDaRun.caminho = None
