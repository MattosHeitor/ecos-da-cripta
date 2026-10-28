"""MP7: o inventário novo. Critérios de aceite: mover itens em 1 ou 2 cliques; o indicador de quem se beneficia
certo em todos os itens; nenhum texto cortado (as prévias da tela inteira são conferidas em test_ui_recorte)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelike import resumo_do_heroi as resumo
from roguelike.classes import criar_heroi
from roguelike.itens import item, todos_os_itens
from roguelike.progresso import Progresso
from ui import texto as T


@pytest.fixture
def app(tmp_path):
    from telas import comum
    from telas.base import App
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    aplicativo = App(janela=False)
    aplicativo.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    yield aplicativo
    comum.ArquivoDaRun.caminho = None


def quadros(app, n=2):
    for _ in range(n):
        app.passo(1 / 30, [])


def abrir(app, run):
    from telas import fluxo
    fluxo.abrir_inventario(app, run, lambda: None)
    quadros(app)
    return app.atual


def nova_run(app, classes=("guerreiro", "mago"), semente="MP7"):
    run = app.progresso.criar_run([criar_heroi(c) for c in classes], semente)
    for inventario in run.inventarios():
        inventario.itens.clear()
    return run


def area(tela, alvo):
    return next(r for r, a in tela.areas if a == alvo).center


def clique(app, posicao, mods=0, botao=1, monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr(pygame.key, "get_mods", lambda: mods)
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=posicao, button=botao)])
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=posicao, button=botao)])


# ---------------- quem se beneficia (regras) ----------------
def test_quem_se_beneficia_segue_a_nota_e_o_foco_da_classe():
    guerreiro, mago = criar_heroi("guerreiro"), criar_heroi("mago")
    assert resumo.pesos_do_heroi(mago)["magia"] > resumo.pesos_do_heroi(guerreiro)["magia"]      # (inteligência)
    assert resumo.pesos_do_heroi(guerreiro)["ataque"] > resumo.pesos_do_heroi(mago)["ataque"]    # (força)
    elmo = item("elmo_de_ferro")                                       # +1 defesa, -1 iniciativa
    lista = resumo.beneficiados(elmo, [guerreiro, mago])
    assert lista and lista[0][0] is guerreiro                          # o guerreiro (constituição) ganha mais
    assert resumo.beneficiados(item("pocao_de_vida"), [guerreiro]) == []          # consumível: ninguém
    guerreiro.equipar(elmo)
    assert guerreiro not in [h for h, _, _ in resumo.beneficiados(elmo, [guerreiro])]   # já tem: não é melhor


def test_peca_que_o_heroi_nao_pode_usar_nao_conta(monkeypatch):
    guerreiro, mago = criar_heroi("guerreiro"), criar_heroi("mago")
    elmo = item("elmo_de_ferro")
    assert guerreiro in [h for h, _, _ in resumo.beneficiados(elmo, [guerreiro, mago])]
    monkeypatch.setattr(elmo, "classes", ["mago"])                       # (só o mago pode usar)
    assert guerreiro not in [h for h, _, _ in resumo.beneficiados(elmo, [guerreiro, mago])]
    assert resumo.melhor_troca(guerreiro, elmo) is None and resumo.melhor_troca(mago, elmo) is not None


def test_indicador_certo_em_todos_os_itens(app):
    """Cada peça da tela mostra quem mais ganha (o mesmo que a regra calcula); a dica tem uma linha por herói."""
    run = nova_run(app, ("guerreiro", "mago", "patrulheira"))
    pecas = [c for c, i in todos_os_itens().items() if i.tipo == "equipamento" and i.tier == 1][:25]
    for chave in pecas:
        run.grupo.bau.adicionar(chave)
    tela = abrir(app, run)
    vistos = 0
    for rect, alvo in list(tela.areas):
        if alvo[0] != "item":
            continue
        peca = item(alvo[2])
        esperado = resumo.beneficiados(peca, run.grupo.herois)
        assert [h for h, _, _ in tela.beneficiados(peca)] == [h for h, _, _ in esperado]
        linhas = [t for t, _ in tela.trechos_do_beneficio(peca)]
        assert len(linhas) == len(run.grupo.herois)
        assert all(any(h.nome in linha for linha in linhas) for h in run.grupo.herois)
        vistos += 1
    assert vistos == len(pecas)


# ---------------- mover em 1 ou 2 cliques ----------------
def test_shift_clique_e_arrastar_levam_a_pilha_inteira(app, monkeypatch):
    run = nova_run(app)
    mochila = run.grupo.herois[0].inventario
    mochila.adicionar("osso", 7)
    tela = abrir(app, run)
    clique(app, area(tela, ("item", "mochila", "osso")), pygame.KMOD_LSHIFT, monkeypatch=monkeypatch)   # 1 clique
    assert run.grupo.bau.quantidade("osso") == 7 and not mochila.tem("osso")
    monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
    quadros(app, 1)
    origem, destino = area(tela, ("item", "bau", "osso")), area(tela, ("grade", "mochila"))
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=origem, button=1)])         # arrastar
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEMOTION, pos=destino, rel=(0, 0), buttons=(1, 0, 0))])
    app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEBUTTONUP, pos=destino, button=1)])
    assert mochila.quantidade("osso") == 7 and not run.grupo.bau.tem("osso")


def test_marcar_varios_e_mover_de_uma_vez(app, monkeypatch):
    run = nova_run(app)
    mochila = run.grupo.herois[0].inventario
    for chave, quantidade in (("osso", 3), ("couro_grosso", 2), ("pocao_de_vida", 1)):
        mochila.adicionar(chave, quantidade)
    tela = abrir(app, run)
    for chave in ("osso", "couro_grosso"):
        clique(app, area(tela, ("item", "mochila", chave)), pygame.KMOD_LCTRL, monkeypatch=monkeypatch)
    assert tela.marcados == {("mochila", "osso"), ("mochila", "couro_grosso")}
    monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
    botao = next(b for b in tela.botoes if b.texto.startswith("Mover marcados"))
    clique(app, botao.rect.center)                                     # o 2º clique: "Mover marcados (2)"
    assert run.grupo.bau.itens == {"osso": 3, "couro_grosso": 2} and mochila.itens == {"pocao_de_vida": 1}
    assert tela.marcados == set()


def test_botoes_de_mover_todos_os_materiais_e_consumiveis(app):
    run = nova_run(app)
    mochila = run.grupo.herois[0].inventario
    for chave, quantidade in (("osso", 3), ("couro_grosso", 2), ("pocao_de_vida", 2), ("botas_gastas", 1)):
        mochila.adicionar(chave, quantidade)
    tela = abrir(app, run)
    clique(app, next(b for b in tela.botoes if b.texto == "Materiais → baú").rect.center)
    assert run.grupo.bau.itens == {"osso": 3, "couro_grosso": 2}
    clique(app, next(b for b in tela.botoes if b.texto == "Consumíveis → baú").rect.center)
    assert run.grupo.bau.quantidade("pocao_de_vida") == 2 and mochila.itens == {"botas_gastas": 1}
    clique(app, next(b for b in tela.botoes if b.texto == "← Materiais").rect.center)
    assert mochila.quantidade("osso") == 3 and mochila.quantidade("couro_grosso") == 2
    assert run.grupo.bau.itens == {"pocao_de_vida": 2}


# ---------------- busca, filtros e ordem ----------------
def test_busca_e_filtros_valem_para_as_duas_grades(app):
    run = nova_run(app)
    run.grupo.herois[0].inventario.adicionar("osso", 2)
    run.grupo.herois[0].inventario.adicionar("botas_gastas")
    for chave in ("po_de_osso", "elmo_de_ferro", "espada_enferrujada"):
        if chave in todos_os_itens():
            run.grupo.bau.adicionar(chave)
    tela = abrir(app, run)

    def visiveis():
        quadros(app, 1)
        return {(a[1], a[2]) for _, a in tela.areas if a[0] == "item"}

    tela.campo_busca.conteudo = "ÓSSO"                                 # (sem diferença de acento e maiúscula)
    assert {c for _, c in visiveis()} <= {"osso", "po_de_osso"} and ("mochila", "osso") in visiveis()
    tela.limpar_filtros()
    tela.filtros["espaco"] = "botas"
    assert visiveis() == {("mochila", "botas_gastas")}
    tela.limpar_filtros()
    tela.filtros["tipo"] = "material"
    assert all(item(c).tipo == "material" for _, c in visiveis())
    tela.limpar_filtros()
    tela.filtros["raridade"] = "comum"
    assert all(item(c).raridade == "comum" for _, c in visiveis())


def test_digitar_na_busca_nao_aciona_atalhos(app):
    run = nova_run(app)
    tela = abrir(app, run)
    clique(app, tela.campo_busca.rect.center)
    indice = tela.indice
    app.passo(1 / 30, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode="e", mod=0),
                       pygame.event.Event(pygame.TEXTINPUT, text="e")])
    assert tela.campo_busca.conteudo == "e" and tela.indice == indice          # (E não trocou de herói)


# ---------------- em grupo ----------------
def test_em_grupo_so_os_meus_herois_e_a_borda_de_quem_e_melhor_para_outro(app):
    from roguelike.posse import Jogador
    run = nova_run(app, ("guerreiro", "mago"))
    bia = Jogador("bia", "Bia", (86, 146, 226))
    run.grupo.dar_heroi(run.grupo.herois[1], bia)
    tela = abrir(app, run)
    assert tela.fonte.herois() == run.grupo.herois[:1]                 # os retratos: só o meu
    assert tela.fonte.todos_os_herois() == run.grupo.herois            # o indicador: todos
    meu, dela = run.grupo.herois
    so_dela = next((p for c, p in todos_os_itens().items() if p.tipo == "equipamento"
                    and [h for h, _, _ in resumo.beneficiados(p, run.grupo.herois)] == [dela]), None)
    assert so_dela is not None and tela.so_para_outros(so_dela)
    assert not tela.so_para_outros(item("elmo_de_ferro"))
    trechos = tela.trechos_do_beneficio(so_dela)
    assert any("(Bia)" in t and t.startswith("▲") for t, _ in trechos)  # a dica diz de quem é o herói


# ---------------- nada cortado ----------------
def test_inventario_cheio_com_o_mouse_em_cada_coisa_sem_cortar(app):
    run = nova_run(app, ("guerreiro", "mago", "patrulheira", "sacerdote"))
    chaves = list(todos_os_itens())
    for chave in chaves[:50]:
        run.grupo.herois[0].inventario.adicionar(chave, 2)
    for chave in chaves[50:120]:
        run.grupo.bau.adicionar(chave, 3)
    for chave in ("capuz_do_coveiro", "casaco_do_coveiro", "botas_do_coveiro", "anel_do_pacto"):
        run.grupo.herois[0].equipar(item(chave))
    tela = abrir(app, run)
    antes = len(T.TRUNCAMENTOS)
    for rect, alvo in list(tela.areas):
        if alvo[0] in ("item", "espaco", "rapido", "retrato"):
            app.passo(1 / 30, [pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center, rel=(0, 0), buttons=(0, 0, 0))])
            app.passo(1 / 30, [])
    assert T.TRUNCAMENTOS[antes:] == []
