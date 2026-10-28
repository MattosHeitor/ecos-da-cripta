"""Etapa 1 da fase 2: controles, opções, áudio, componentes e navegação por teclado (sem janela)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from audio import GerenciadorDeAudio
from telas import comum
from telas.base import App
from telas.comum import TelaComBotoes
from ui.componentes import ListaSelecionavel, TextoRevelado, DialogoDeConfirmacao
from ui.controles import Controles
from ui.opcoes import Opcoes
from ui.widgets import Botao
from roguelike.progresso import Progresso


def tecla(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)


@pytest.fixture()
def app(tmp_path):
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    aplicativo = App(janela=False)
    aplicativo.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    yield aplicativo
    comum.ArquivoDaRun.caminho = None


def passo(app, eventos=(), n=2):
    for i in range(n):
        app.passo(1 / 30, list(eventos) if i == 0 else [])


# ---------------- controles ----------------
def test_setas_e_wasd_sao_direcoes():
    controles = Controles()
    assert controles.direcao(tecla(pygame.K_UP)) == (0, -1)
    assert controles.direcao(tecla(pygame.K_w)) == (0, -1)
    assert controles.direcao(tecla(pygame.K_d)) == (1, 0)
    assert controles.eh(tecla(pygame.K_RETURN), "confirmar")
    assert not controles.eh(tecla(pygame.K_x), "confirmar")


def test_remapear_troca_com_a_acao_que_usava_a_tecla():
    controles = Controles()
    controles.remapear("grupo", pygame.K_b)          # B era do baú
    assert controles.teclas["grupo"][0] == pygame.K_b
    assert pygame.K_g in controles.teclas["bau"]     # o baú ficou com o G antigo
    assert controles.acoes_da_tecla(pygame.K_b) == ["grupo"]


def test_remapear_para_a_outra_tecla_da_mesma_acao_so_troca_a_ordem():
    controles = Controles()
    controles.remapear("cima", pygame.K_w, posicao=0)
    assert controles.teclas["cima"] == [pygame.K_w, pygame.K_UP]


def test_restaurar_padrao():
    controles = Controles()
    controles.remapear("confirmar", pygame.K_x)
    controles.restaurar_padrao()
    assert controles.teclas["confirmar"][0] == pygame.K_RETURN


# ---------------- opções ----------------
def test_opcoes_limitam_volume_e_giram_velocidades():
    opcoes = Opcoes()
    for _ in range(20):
        opcoes.mudar_volume("musica", 1)
    assert opcoes.volume_musica == 1.0
    for _ in range(20):
        opcoes.mudar_volume("efeitos", -1)
    assert opcoes.volume_efeitos == 0.0
    opcoes.proxima_velocidade_combate()
    assert opcoes.velocidade_combate == 1.5
    opcoes.proxima_velocidade_texto(-1)
    assert opcoes.velocidade_texto == "lento"


def test_opcoes_salvam_e_carregam_com_as_teclas(tmp_path):
    caminho = str(tmp_path / "opcoes.json")
    opcoes = Opcoes()
    opcoes.volume_musica = 0.3
    opcoes.tela_cheia = True
    opcoes.controles.remapear("registro", pygame.K_r)
    opcoes.salvar(caminho)
    carregadas = Opcoes.carregar(caminho)
    assert carregadas.para_dict() == opcoes.para_dict()


def test_arquivo_de_opcoes_estragado_volta_ao_padrao(tmp_path):
    caminho = tmp_path / "opcoes.json"
    caminho.write_text("{ isso não é json", encoding="utf-8")
    assert Opcoes.carregar(str(caminho)).para_dict() == Opcoes().para_dict()


# ---------------- áudio ----------------
def test_audio_toca_o_que_existe_e_anota_o_que_falta():
    audio = GerenciadorDeAudio(Opcoes())
    audio.tocar("golpe")                              # gerado por ferramentas/gerar_sons.py
    audio.tocar("som_que_nao_existe")
    audio.musica("floresta")                          # gerada por ferramentas/gerar_musicas.py
    audio.musica("musica_que_nao_existe")
    assert list(audio.historico)[-2:] == ["golpe", "som_que_nao_existe"]
    assert "efeitos/som_que_nao_existe" in audio.faltando
    assert "efeitos/golpe" not in audio.faltando
    assert "musica/floresta" not in audio.faltando and "musica/musica_que_nao_existe" in audio.faltando


# ---------------- componentes ----------------
def test_lista_selecionavel_anda_dando_a_volta_e_rola():
    escolhidos = []
    lista = ListaSelecionavel(list("abcdef"), altura_item=20, ao_escolher=escolhidos.append, espaco=0)
    lista.rect = pygame.Rect(0, 0, 100, 60)          # cabem 3
    controles = Controles()
    lista.evento(tecla(pygame.K_UP), controles)
    assert lista.selecionado == "f" and lista.rolagem == 3
    lista.evento(tecla(pygame.K_DOWN), controles)
    assert lista.selecionado == "a" and lista.rolagem == 0
    lista.evento(tecla(pygame.K_RETURN), controles)
    assert escolhidos == ["a"]


def test_texto_revelado_aparece_aos_poucos_e_pode_pular():
    narracao = TextoRevelado("Olá, viajante.", letras_por_segundo=10)
    narracao.atualizar(0.3)
    assert narracao.visivel == "Olá" and not narracao.completo()
    narracao.pular()
    assert narracao.visivel == "Olá, viajante." and narracao.completo()
    assert TextoRevelado("tudo", None).completo()


def test_dialogo_comeca_no_cancelar():
    feito = []
    dialogo = DialogoDeConfirmacao("Vender", "Tem certeza?", [("Vender", lambda: feito.append(1)), ("Cancelar", None)])
    controles = Controles()
    dialogo.evento(tecla(pygame.K_RETURN), controles)  # Enter distraído = cancelar
    assert not dialogo.aberto and feito == []
    dialogo = DialogoDeConfirmacao("Vender", "Tem certeza?", [("Vender", lambda: feito.append(1)), ("Cancelar", None)])
    dialogo.evento(tecla(pygame.K_LEFT), controles)
    dialogo.evento(tecla(pygame.K_RETURN), controles)
    assert feito == [1]


# ---------------- navegação por teclado ----------------
class TelaGrade(TelaComBotoes):
    """Quatro botões em 2x2 para testar o foco."""

    def __init__(self, app):
        super().__init__(app)
        self.apertados = []

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        for i, (x, y) in enumerate(((100, 100), (300, 100), (100, 300), (300, 300))):
            self.botao(Botao((x, y, 120, 50), str(i), lambda i=i: self.apertados.append(i)))
        self.terminar_desenho(tela)


def test_setas_movem_o_foco_e_enter_aperta(app):
    tela = TelaGrade(app)
    app.trocar(tela)
    passo(app)
    passo(app, [tecla(pygame.K_DOWN)])               # primeiro aperto: foca o 1º botão
    assert tela.foco == (100, 100, 120, 50)
    passo(app, [tecla(pygame.K_d)])                  # D = direita
    assert tela.foco == (300, 100, 120, 50)
    passo(app, [tecla(pygame.K_DOWN)])
    assert tela.foco == (300, 300, 120, 50)
    passo(app, [tecla(pygame.K_RETURN)])
    assert tela.apertados == [3]
    assert "navegar" in app.audio.historico and "clique" in app.audio.historico


def test_tela_de_opcoes_pelo_teclado(app):
    from telas.opcoes import TelaOpcoes
    saiu = []
    tela = TelaOpcoes(app, lambda: saiu.append(True))
    app.trocar(tela)
    passo(app)
    antes = app.opcoes.volume_efeitos
    passo(app, [tecla(pygame.K_DOWN)])               # linha "efeitos"
    passo(app, [tecla(pygame.K_LEFT)])
    assert app.opcoes.volume_efeitos == pytest.approx(antes - 0.1)
    assert Opcoes.carregar().volume_efeitos == pytest.approx(antes - 0.1)   # já salvou
    passo(app, [tecla(pygame.K_DOWN), ])
    passo(app, [tecla(pygame.K_RIGHT)])              # velocidade do combate
    assert app.velocidade == 1.5
    passo(app, [tecla(pygame.K_ESCAPE)])
    assert saiu == [True]


def test_tela_de_controles_remapeia(app):
    from telas.opcoes import TelaControles
    tela = TelaControles(app, lambda: None)
    app.trocar(tela)
    passo(app)
    passo(app, [tecla(pygame.K_RETURN)])             # 1ª linha = "cima", coluna 1
    assert tela.esperando == "cima"
    passo(app, [tecla(pygame.K_i)])
    assert app.controles.teclas["cima"][0] == pygame.K_i
    passo(app, [tecla(pygame.K_RETURN)])
    passo(app, [tecla(pygame.K_5, "5")])             # números são fixos
    assert app.controles.teclas["cima"][0] == pygame.K_i and "fixas" in tela.mensagem


def test_vender_na_loja_pede_confirmacao(app):
    from roguelike import encontros as E
    from roguelike.classes import criar_heroi
    from telas import fluxo
    run = app.progresso.criar_run([criar_heroi("guerreiro")], "VENDA")
    run.opcoes = [E.EncontroLoja()]
    run.escolher(0)
    fluxo.resolver_encontro(app, run)
    loja = app.atual
    mochila = run.grupo.herois[0].inventario                # a loja vende da sua mochila (ou do baú, no botão)
    mochila.adicionar("osso", 3)
    ouro = run.grupo.ouro
    loja.vender("osso")
    assert loja.dialogo is not None
    passo(app, [tecla(pygame.K_RETURN)])             # foco começa em "Cancelar"
    assert mochila.itens["osso"] == 3 and loja.dialogo is None
    loja.vender("osso")
    passo(app, [tecla(pygame.K_LEFT)])               # "Todos x3"
    passo(app, [tecla(pygame.K_RETURN)])
    assert not mochila.tem("osso") and run.grupo.ouro > ouro
    run.grupo.bau.adicionar("osso", 1)
    loja.trocar_venda()                              # agora do baú da equipe
    loja.vender("osso")
    passo(app, [tecla(pygame.K_LEFT)])               # "Vender 1"
    passo(app, [tecla(pygame.K_RETURN)])
    assert not run.grupo.bau.tem("osso")


def test_titulo_tem_opcoes_e_musica(app):
    from telas.titulo import TelaTitulo
    app.trocar(TelaTitulo(app))
    passo(app)
    assert any(b.texto == "Opções" for b in app.atual.botoes)
    assert app.audio.musica_atual == "titulo"


def test_notificacao_aparece_e_some(app):
    app.notificar("Golpe aprimorado!", "Bola de Fogo virou Inferno")
    assert app.notificacoes.fila
    for _ in range(5):
        app.passo(1.0, [])
    assert not app.notificacoes.fila
