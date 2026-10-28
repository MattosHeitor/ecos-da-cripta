"""Caminhos (caminhos.py), versão e tela cheia por Alt+Enter: a base da etapa MP1.

O conftest já manda a pasta do jogador para uma pasta temporária em todo teste.
"""

import glob
import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import caminhos as C
from caminhos import CAMINHOS, Caminhos
from versao import VERSAO

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------- pastas do jogo (só leitura) ----------------
def test_pasta_do_jogo_pelo_codigo_e_a_raiz_do_projeto():
    assert os.path.samefile(CAMINHOS.raiz, RAIZ)
    assert os.path.isfile(CAMINHOS.asset("sprites_macabros", "catalogo.json"))
    assert os.path.isfile(os.path.join(CAMINHOS.dados, "regras.json"))


def test_empacotado_le_da_pasta_do_executavel(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    caminhos = Caminhos()
    assert caminhos.raiz == str(tmp_path)
    assert caminhos.asset("fontes") == os.path.join(str(tmp_path), "assets", "fontes")
    assert caminhos.dados == os.path.join(str(tmp_path), "src", "roguelike", "dados")


def test_nenhum_modulo_monta_caminho_por_conta_propria():
    """Só caminhos.py (e o jogar.py, para achar src/) olham o __file__: o resto pede ao CAMINHOS."""
    usam = []
    for arquivo in glob.glob(os.path.join(RAIZ, "src", "**", "*.py"), recursive=True):
        with open(arquivo, encoding="utf-8") as f:
            if "__file__" in f.read():
                usam.append(os.path.relpath(arquivo, os.path.join(RAIZ, "src")))
    assert sorted(usam) == ["caminhos.py", "jogar.py"]


# ---------------- pasta do jogador ----------------
def test_pasta_do_jogador_no_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv(C.VARIAVEL_DA_PASTA, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert C.pasta_padrao_do_jogador() == os.path.join(str(tmp_path), "Ecos da Cripta")
    monkeypatch.setenv(C.VARIAVEL_DA_PASTA, str(tmp_path / "outra"))
    assert C.pasta_padrao_do_jogador() == str(tmp_path / "outra")


def test_saves_ficam_na_pasta_do_jogador():
    from roguelike.progresso import Progresso
    from telas.comum import ArquivoDaRun
    from ui.opcoes import Opcoes
    pasta = CAMINHOS.jogador
    assert Progresso().caminho == os.path.join(pasta, "progresso.json")
    assert Progresso.carregar().caminho == os.path.join(pasta, "progresso.json")
    assert ArquivoDaRun.onde() == os.path.join(pasta, "run.json")
    assert Opcoes.onde() == os.path.join(pasta, "opcoes.json")


def test_perfil_tem_save_separado():
    principal = CAMINHOS.save("progresso.json")
    CAMINHOS.usar_perfil("B")
    assert CAMINHOS.save("progresso.json") == os.path.join(CAMINHOS.base_do_jogador, "perfis", "B", "progresso.json")
    assert CAMINHOS.save("progresso.json") != principal
    CAMINHOS.usar_perfil(None)
    assert CAMINHOS.save("progresso.json") == principal


@pytest.mark.parametrize("nome", ["../fora", "com espaço", "a" * 25, "C:"])
def test_perfil_invalido(nome):
    with pytest.raises(ValueError):
        CAMINHOS.usar_perfil(nome)


def test_saves_antigos_sao_copiados_so_na_primeira_vez(tmp_path):
    antiga = tmp_path / "saves"
    antiga.mkdir()
    (antiga / "progresso.json").write_text('{"brasas": 7}', encoding="utf-8")
    (antiga / "opcoes.json").write_text("{}", encoding="utf-8")
    caminhos = Caminhos(raiz=str(tmp_path), jogador=str(tmp_path / "jogador"))
    assert caminhos.trazer_saves_antigos() == ["progresso.json", "opcoes.json"]
    assert json.loads((tmp_path / "jogador" / "progresso.json").read_text(encoding="utf-8")) == {"brasas": 7}
    assert (antiga / "progresso.json").exists()                        # o antigo fica (cópia de segurança)
    os.remove(tmp_path / "jogador" / "progresso.json")                 # ex.: "começar do zero"
    assert caminhos.trazer_saves_antigos() == []                       # não traz de volta
    assert not (tmp_path / "jogador" / "progresso.json").exists()


def test_sem_saves_antigos_nao_cria_nada(tmp_path):
    caminhos = Caminhos(raiz=str(tmp_path), jogador=str(tmp_path / "jogador"))
    assert caminhos.trazer_saves_antigos() == []
    assert not (tmp_path / "jogador").exists()


# ---------------- gravar ----------------
def test_gravar_json_sem_sobrar_temporario(tmp_path):
    caminho = str(tmp_path / "pasta" / "nova" / "x.json")
    C.gravar_json(caminho, {"a": "ç"})
    assert json.load(open(caminho, encoding="utf-8")) == {"a": "ç"}
    assert os.listdir(os.path.dirname(caminho)) == ["x.json"]


def test_gravar_json_espera_o_antivirus(monkeypatch, tmp_path):
    """No Windows o arquivo às vezes fica preso por um instante: tenta de novo antes de desistir."""
    trocar, falhas = os.replace, []

    def preso_uma_vez(origem, destino):
        if not falhas:
            falhas.append(1)
            raise PermissionError("em uso")
        trocar(origem, destino)

    monkeypatch.setattr(C.os, "replace", preso_uma_vez)
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    C.gravar_json(str(tmp_path / "x.json"), [1])
    assert falhas == [1] and json.load(open(tmp_path / "x.json")) == [1]


def test_saves_levam_a_versao_do_jogo():
    from roguelike.classes import criar_heroi
    from roguelike.progresso import Progresso
    progresso = Progresso()
    progresso.salvar()
    assert json.load(open(progresso.caminho, encoding="utf-8"))["versao_do_jogo"] == VERSAO
    assert Progresso.carregar().caminho == progresso.caminho             # e o campo a mais não atrapalha ao abrir
    run = progresso.criar_run([criar_heroi("guerreiro")], "VERSAO")
    caminho = CAMINHOS.save("run.json")
    run.salvar(caminho)
    assert json.load(open(caminho, encoding="utf-8"))["versao_do_jogo"] == VERSAO
    assert run.carregar(caminho).semente == "VERSAO"


def test_pasta_para_mostrar(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    pasta = os.path.join(str(tmp_path / "Roaming"), "Ecos da Cripta")
    assert C.pasta_para_mostrar(pasta) == os.path.join("%APPDATA%", "Ecos da Cripta")
    longa = os.path.join("C:\\", "a", "b", "c", "d")
    assert C.pasta_para_mostrar(longa) == os.path.join("...", "c", "d")


# ---------------- tela cheia e título ----------------
def test_alt_enter_alterna_tela_cheia():
    from telas.base import App, Tela
    app = App(janela=False)
    app.trocar(Tela(app))
    antes = app.opcoes.tela_cheia
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_LALT, unicode="")])
    assert app.opcoes.tela_cheia != antes
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r")])
    assert app.opcoes.tela_cheia != antes                               # Enter sozinho não mexe
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0, unicode="")])
    assert app.opcoes.tela_cheia == antes


@pytest.mark.parametrize("com_pets", [False, True])
def test_opcoes_cabem_sem_rolar(com_pets):
    """Todas as linhas das Opções aparecem de uma vez (o "Voltar" não fica escondido embaixo)."""
    from telas.base import App
    from roguelike.progresso import Progresso
    from telas.opcoes import TelaOpcoes
    app = App(janela=False)
    app.progresso = Progresso()
    if com_pets:
        app.progresso.conquistas.add("chefe:rei_dos_ratos")
    tela = TelaOpcoes(app, lambda: None)
    app.trocar(tela)
    app.passo(1 / 30, [])
    assert ("pets" in tela.linhas) == com_pets
    assert tela.lista.cabem() >= len(tela.linhas) and tela.lista.altura_item >= 36


def test_opcoes_mostram_a_pasta_dos_saves(monkeypatch):
    from telas.base import App
    from telas.opcoes import TelaOpcoes
    abertas = []
    monkeypatch.setattr("telas.opcoes.abrir_pasta", lambda pasta: abertas.append(pasta) or True)
    app = App(janela=False)
    tela = TelaOpcoes(app, lambda: None)
    assert "pasta" in tela.linhas and tela.valor("pasta").endswith("jogador")
    tela.ativar("pasta")
    assert abertas == [CAMINHOS.jogador]
