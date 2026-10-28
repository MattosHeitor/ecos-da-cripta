"""Teste do jogo inteiro pelas telas, sem janela: título -> acampamento -> run -> encontros -> fim.

Os saves vão para uma pasta temporária (não mexe no progresso de verdade).
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelike import encontros as E
from roguelike.progresso import Progresso
from telas import comum, fluxo
from telas.base import App


@pytest.fixture()
def app(tmp_path):
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    aplicativo = App(janela=False)
    aplicativo.velocidade = 4.0
    aplicativo.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    yield aplicativo
    comum.ArquivoDaRun.caminho = None


def quadros(app, n=3, eventos=()):
    for i in range(n):
        app.passo(1 / 30, list(eventos) if i == 0 else [])


def tecla(app, k, unicode=""):
    quadros(app, 2, [pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)])


def comecar(app, classes=("guerreiro", "sacerdote")):
    from telas.capitao import TelaCapitao
    capitao = TelaCapitao(app)
    capitao.expedicao.vagas.clear()
    for classe in classes:
        capitao.adicionar(classe)
    capitao.campo_semente.conteudo = "FLUXO"
    app.trocar(capitao)
    quadros(app)
    tecla(app, pygame.K_RETURN, "\r")          # Enter = partir
    quadros(app)
    assert type(app.atual).__name__ == "TelaTituloDaArea"       # a fase se apresenta antes do mapa
    quadros(app, 12)
    tecla(app, pygame.K_SPACE, " ")
    return app.atual.run


def forcar_encontro(app, run, encontro):
    run.estado = "escolha"
    run.opcoes = [encontro]
    app.atual.escolher(0)
    quadros(app)


def test_telas_do_acampamento_abrem(app):
    from telas.titulo import TelaTitulo
    app.trocar(TelaTitulo(app))
    quadros(app)
    fluxo.ir_para_acampamento(app)
    esperadas = ["TelaEspelho", "TelaGrimorio", "TelaBestiario", "TelaTaverna", "TelaCapitao", "TelaMagoAnciao", "TelaBau",
                 "TelaInventario"]
    for numero, nome in enumerate(esperadas, start=1):
        tecla(app, pygame.K_1 + numero - 1, str(numero))
        quadros(app)
        assert type(app.atual).__name__ == nome
        tecla(app, pygame.K_ESCAPE)
        assert type(app.atual).__name__ == "TelaAcampamento"


def test_comecar_run_salva_e_mostra_o_mapa(app):
    run = comecar(app)
    assert type(app.atual).__name__ == "TelaMapa"
    assert os.path.exists(comum.ArquivoDaRun.caminho)
    assert run.semente == "FLUXO" and len(run.grupo.herois) == 2


def test_bau_da_equipe_e_fabricacao(app):
    """B abre o inventário no baú da equipe; F, a fabricação (que volta para o inventário)."""
    run = comecar(app)
    run.grupo.bau.adicionar("espada_enferrujada")
    run.grupo.bau.adicionar("erva_do_pantano", 2)
    run.grupo.bau.adicionar("olho_de_sapo")
    tecla(app, pygame.K_b, "b")
    tela = app.atual
    assert type(tela).__name__ == "TelaInventario"           # (MP7: a mochila e o baú lado a lado)
    quadros(app)
    tela.equipar("espada_enferrujada")
    assert run.grupo.herois[0].equipamento["arma"].chave == "espada_enferrujada"
    tecla(app, pygame.K_f, "f")
    fabricacao = app.atual
    assert type(fabricacao).__name__ == "TelaFabricacao"
    quadros(app)
    fabricacao.fabricar("pocao_de_vida")
    heroi = run.grupo.herois[0]
    assert heroi.inventario.tem("pocao_de_vida") or run.grupo.bau.tem("pocao_de_vida")
    tecla(app, pygame.K_ESCAPE)
    assert type(app.atual).__name__ == "TelaInventario"
    tecla(app, pygame.K_ESCAPE)
    assert type(app.atual).__name__ == "TelaMapa"


def test_loja_evento_servicos(app):
    run = comecar(app)
    forcar_encontro(app, run, E.EncontroLoja())
    loja = app.atual
    assert type(loja).__name__ == "TelaLoja"
    run.grupo.ouro = 999
    loja.comprar(0)
    quadros(app)
    tecla(app, pygame.K_ESCAPE)                          # sair da loja = próxima área
    assert type(app.atual).__name__ == "TelaMapa" and run.area == 2

    forcar_encontro(app, run, E.EncontroEvento("altar_esquecido"))
    tela = app.atual
    tecla(app, pygame.K_1, "1")
    assert tela.resultado is not None
    tecla(app, pygame.K_RETURN, "\r")                    # 1º Enter: mostra o resto do texto
    assert type(app.atual).__name__ == "TelaEvento" and tela.narracao.completo()
    tecla(app, pygame.K_RETURN, "\r")                    # 2º Enter: continua
    assert type(app.atual).__name__ == "TelaMapa" and run.area == 3

    guerreiro = run.grupo.herois[0]
    assert guerreiro.subclasse.chave == "cavaleiro"                # escolhida na Capitã
    for _ in range(4):
        guerreiro.subir_nivel()                                    # nível 5: pode se especializar
    forcar_encontro(app, run, E.EncontroTreinador("guerreiro", "cavaleiro"))
    app.atual.treinar(guerreiro)
    assert guerreiro.especializacao.chave == "guardiao_juramentado"
    assert "muralha_de_ferro" in guerreiro.golpes.equipados       # Golpe de Escudo evoluiu com a especialização
    tecla(app, pygame.K_RETURN, "\r")
    # golpes novos (níveis 3/4 e especialização) com os espaços cheios: a escolha aparece antes do mapa
    assert type(app.atual).__name__ == "TelaGolpes" and guerreiro.golpes.pendentes
    tecla(app, pygame.K_ESCAPE)                                   # sair = os novos vão para o grimório
    assert type(app.atual).__name__ == "TelaMapa" and not guerreiro.golpes.pendentes
    assert len(guerreiro.golpes.grimorio) >= 1

    run.grupo.herois[1].vida = 0
    run.grupo.ouro = 500
    forcar_encontro(app, run, E.EncontroAltar())
    app.atual.reviver(run.grupo.herois[1])
    assert run.grupo.herois[1].esta_vivo()
    tecla(app, pygame.K_RETURN, "\r")

    forcar_encontro(app, run, E.EncontroEntrada("minas"))
    tecla(app, pygame.K_RETURN, "\r")
    assert run.regiao_atual == "minas"


def test_portoes_do_fim_do_ato_no_mapa(app):
    run = comecar(app)
    run.portoes = [["minas", True], ["pantano_dos_afogados", False]]
    run.opcoes = None
    fluxo.ir_para_mapa(app, run)
    quadros(app)
    mapa = app.atual
    assert [o.tipo for o in run.opcoes_de_encontro()] == ["portao", "portao"]
    mapa.escolher(1)                                     # selado: nada acontece além do aviso
    quadros(app)
    assert app.atual is mapa and run.regiao_atual == run.regioes_visitadas[0]
    mapa.escolher(0)
    quadros(app)
    assert type(app.atual).__name__ == "TelaTituloDaArea" and run.regiao_atual == "minas" and run.area == 1
    quadros(app, 140)                                    # segue sozinha depois de alguns segundos
    assert type(app.atual).__name__ == "TelaMapa" and run.portoes is None


def test_combate_ate_a_derrota_e_fim_da_run(app):
    run = comecar(app, ("ladino",))
    forcar_encontro(app, run, E.EncontroCombate("Teste", "", 1, ["goblin"]))
    tela = app.atual
    assert type(tela).__name__ == "TelaCombate"
    for heroi in run.grupo.herois:                     # derrota forçada
        heroi.vida = 1
    for _ in range(2000):
        if tela.estado == "fim":
            break
        if tela.estado == "escolhendo":
            tela.combate.causar_dano(tela.combate.atual, 999, None)
            tela.combate.verificar_fim()
            tela.combate.encerrar_turno()
            tela.estado = "animando"
            tela.enfileirar()
        quadros(app, 1)
    quadros(app, 60)
    assert tela.combate.resultado == "derrota"
    tecla(app, pygame.K_RETURN, "\r")
    assert type(app.atual).__name__ == "TelaFimDeRun"
    assert not os.path.exists(comum.ArquivoDaRun.caminho)          # a run acabou: save apagado
    assert app.progresso.estatisticas["runs"] == 1
    tecla(app, pygame.K_RETURN, "\r")
    assert type(app.atual).__name__ == "TelaAcampamento"


def test_continuar_run_salva(app):
    run = comecar(app)
    run.grupo.ouro = 777
    fluxo.salvar_run(run)
    fluxo.continuar_run_salva(app)
    assert app.atual.run.grupo.ouro == 777


def test_continuar_run_fechada_no_meio_de_um_combate(app):
    run = comecar(app)
    forcar_encontro(app, run, E.EncontroCombate("Emboscada", "goblins", 2, ["goblin", "goblin"]))
    assert type(app.atual).__name__ == "TelaCombate"
    # o jogo "fecha" aqui; ao continuar, volta direto para o mesmo combate
    fluxo.continuar_run_salva(app)
    assert type(app.atual).__name__ == "TelaCombate"
    assert app.atual.run.encontro.nome == "Emboscada"

def test_opcoes_apagar_save_comeca_do_zero(app, tmp_path):
    from roguelike.classes import criar_heroi
    from telas.opcoes import TelaOpcoes
    from telas.titulo import TelaTitulo
    app.progresso.brasas = 999
    app.progresso.conquistas.add("chefe:aranha_mae")
    app.progresso.salvar()
    run = app.progresso.criar_run([criar_heroi("guerreiro")], "ZERO")
    run.salvar(comum.ArquivoDaRun.caminho)
    app.opcoes.volume_musica = 0.3
    opcoes = TelaOpcoes(app, lambda: None)
    app.trocar(opcoes)
    opcoes.ativar("apagar_save")
    assert opcoes.dialogo is not None                     # pergunta antes
    opcoes.dialogo.opcoes[0][1]()                         # "Apagar tudo"
    assert not os.path.exists(tmp_path / "progresso.json") and not comum.existe_run_salva()
    assert app.progresso.brasas == 0 and not app.progresso.conquistas
    assert app.progresso.caminho == str(tmp_path / "progresso.json")
    assert app.opcoes.volume_musica == 0.3                # as opções ficam
    quadros(app)
    assert isinstance(app.atual, TelaTitulo)
