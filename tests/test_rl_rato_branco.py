"""Reino dos Ratos, etapa 1: o Rato Branco (um guia) leva ao bueiro escondido; o segredo atravessa as runs."""

import json
import os

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.encontros import EncontroEntrada
from roguelike.eventos_run import evento
from roguelike.guias import guia
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.progresso import Progresso
from roguelike.regioes import regiao, todas_as_regioes
from roguelike.run import Run

SUBTERRANEAS = ("catacumbas_da_ordem_caida", "minas", "minas_de_brasa")
CATALOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sprites_macabros",
                        "catalogo.json")


def run_nas_catacumbas(segredos=None):
    run = Run([criar_heroi("guerreiro"), criar_heroi("sacerdote")], "RATO", "catacumbas_da_ordem_caida")
    run.segredos = dict(segredos or {})
    run.area = 3
    return run


def carta_do_rato(run, monkeypatch):
    """Gera as opções da área com a chance do Rato Branco em 100% e devolve a carta dele (ou None)."""
    for chave in SUBTERRANEAS:
        monkeypatch.setitem(regiao(chave).entradas["reino_dos_ratos"], "chance", 1.0)
    run.opcoes = None
    return next((o for o in run.opcoes_de_encontro() if getattr(o, "guia", None) == "rato_branco"), None)


def seguir(run, carta, opcao=0):
    run.escolher(run.opcoes_de_encontro().index(carta))
    resultado = run.resolver_evento(opcao)
    run.estado, run.encontro = "escolha", None
    return resultado


# ---------------- dados ----------------

def test_rato_branco_so_aparece_nas_fases_subterraneas():
    for chave, fase in todas_as_regioes().items():
        regra = fase.entradas.get("reino_dos_ratos")
        if chave in SUBTERRANEAS:
            assert regra and regra["guia"] == "rato_branco" and 0 < regra["chance"] <= 0.1, chave
        else:
            assert regra is None, chave


def test_reino_e_secreto_opcional_e_aberto_desde_a_etapa_5c():
    reino = regiao("reino_dos_ratos")
    assert reino.opcional and reino.retorna and reino.ato is None      # como o Circo: fora dos atos, volta depois
    assert reino.disponivel and reino.selado                           # (o texto da passagem selada continua no JSON)
    from visual.cenario_macabro import catalogo                         # etapa 2A: cenário próprio (sem tinta provisória)
    assert f"{reino.cenario}_0" in catalogo() and not reino.paleta.get("tom")


def test_guia_tem_sprite_com_corrida_e_eventos_que_nao_caem_no_sorteio():
    rato = guia("rato_branco")
    with open(CATALOGO, encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)
    assert "correr" in catalogo[rato.sprite]["animacoes"]
    assert len(rato.passos) == 2
    for chave in rato.passos:
        passo = evento(chave)
        assert passo.so_por_guia and passo.sprite == rato.sprite
        assert not any(passo.aparece_em(fase) for fase in todas_as_regioes())


# ---------------- os passos ----------------

def test_seguir_a_primeira_vez_leva_ao_esconderijo_com_queijo(monkeypatch):
    run = run_nas_catacumbas()
    carta = carta_do_rato(run, monkeypatch)
    assert carta.tipo == "evento" and carta.evento == "rato_branco_esconderijo" and carta.nome == "Um Rato Branco"
    seguir(run, carta)
    assert run.segredos["rato_branco"] == 1
    assert run.tem_item("queijo_mofado")                  # (na mochila; antes da MP4, no baú)


def test_seguir_a_segunda_vez_acha_o_bueiro_e_depois_a_passagem_leva_ao_reino(monkeypatch):
    run = run_nas_catacumbas({"rato_branco": 1})
    carta = carta_do_rato(run, monkeypatch)
    assert carta.evento == "rato_branco_bueiro"
    seguir(run, carta)
    assert run.segredos["rato_branco"] == 2 and guia("rato_branco").completo(run.segredos)
    passagem = carta_do_rato(run, monkeypatch)
    assert isinstance(passagem, EncontroEntrada) and passagem.destino == "reino_dos_ratos" and not passagem.bloqueado
    assert run.escolher(run.opcoes_de_encontro().index(passagem)) is not None      # aberta (etapa 5C): entra
    run.concluir_encontro()
    assert run.regiao_atual == "reino_dos_ratos" and run.retorno[0] == "catacumbas_da_ordem_caida"


def test_deixar_o_rato_em_paz_nao_conta_e_ele_nao_volta_na_mesma_run(monkeypatch):
    run = run_nas_catacumbas()
    seguir(run, carta_do_rato(run, monkeypatch), opcao=1)
    assert run.segredos.get("rato_branco", 0) == 0
    assert carta_do_rato(run, monkeypatch) is None


def test_circo_continua_uma_passagem_aberta_e_sem_guia():
    passagem = EncontroEntrada("circo")
    assert not passagem.bloqueado and not getattr(passagem, "guia", None)


# ---------------- entre runs ----------------

def test_segredo_vai_para_o_progresso_e_para_a_proxima_run(tmp_path):
    caminho = str(tmp_path / "progresso.json")
    progresso = Progresso.carregar(caminho)
    run = progresso.criar_run([criar_heroi("guerreiro")], "UM")
    run.segredos["rato_branco"] = 1
    assert progresso.guardar_segredos(run) == ["rato_branco"]
    progresso.salvar()
    progresso = Progresso.carregar(caminho)
    assert progresso.segredos == {"rato_branco": 1}
    nova = progresso.criar_run([criar_heroi("guerreiro")], "DOIS")
    assert nova.segredos == {"rato_branco": 1}
    nova.segredos["rato_branco"] = 0                     # uma run nunca faz o segredo andar para trás
    assert progresso.guardar_segredos(nova) == [] and progresso.segredos["rato_branco"] == 1


def test_segredo_vai_no_save_da_run():
    run = run_nas_catacumbas({"rato_branco": 2})
    assert Run.de_dict(run.para_dict()).segredos == {"rato_branco": 2}


def test_aviso_da_descoberta_cabe_inteiro_na_notificacao():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    from telas.fluxo import TITULO_DA_DESCOBERTA
    from ui import tema
    from ui.componentes import Notificacoes
    from ui.texto import largura_do_texto
    interno = Notificacoes.LARGURA_MAXIMA - 28                     # a mesma conta de Notificacoes.desenhar
    titulo = min(largura_do_texto(TITULO_DA_DESCOBERTA, tema.normal()), interno // 2)
    assert largura_do_texto(guia("rato_branco").descoberta, tema.pequena()) <= interno - titulo - 16


# ---------------- o queijo ----------------

def test_queijo_mofado_atordoa_so_as_pestes():
    heroi = criar_heroi("guerreiro")
    ratos, goblin = criar_inimigo("enxame_de_ratos"), criar_inimigo("goblin")
    combate = Combate([heroi], [ratos, goblin])
    combate.iniciar()
    queijo = item("queijo_mofado")
    assert "só em" in queijo.resumo() and queijo.tier == 0              # tier 0: não aparece nas lojas
    combate.aplicar_efeitos(heroi, queijo.efeitos, [ratos, goblin], 1)
    assert "atordoado" in ratos.status and "atordoado" not in goblin.status
