"""MP2: comandos, processador, condutor do combate e determinismo.

O critério de aceite: a mesma semente + a mesma sequência de comandos gera sempre o mesmo estado (impressão
digital), no mesmo processo e em processos diferentes (com PYTHONHASHSEED diferentes: pega ordem de set).
"""

import json
import os
import subprocess
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from roguelike import comandos as C
from roguelike.classes import criar_heroi
from roguelike.condutor import DecisorIA, ESPERANDO, FIM
from roguelike.encontros import EncontroCombate
from roguelike.estado import BAU, EstadoDoJogo
from roguelike.piloto_automatico import Piloto, grupo_padrao
from roguelike.posse import Jogador
from roguelike.processador import ComandoRecusado, ProcessadorDeComandos
from roguelike.progresso import Progresso

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = ("guerreiro", "sacerdote", "patrulheira")


def nova_run(semente="DETERMINISMO", classes=CLASSES):
    return Progresso().criar_run(grupo_padrao(classes), semente)


def jogar_com_o_piloto(semente="DETERMINISMO", areas=200):
    run = nova_run(semente)
    piloto = Piloto(run)
    piloto.jogar(areas)
    return piloto


# ---------------- comandos ----------------
def test_todo_comando_vai_e_volta_do_json():
    for tipo, classe in C.COMANDOS.items():
        comando = classe(jogador="bia", **{nome: padrao for nome, padrao in classe.campos.items()})
        dados = json.loads(json.dumps(comando.para_dict()))
        volta = C.criar_comando(dados)
        assert type(volta) is classe and volta.para_dict() == comando.para_dict() and volta.jogador == "bia", tipo


def test_comando_com_dado_desconhecido_nao_existe():
    with pytest.raises(TypeError):
        C.Comprar(indice=0, preco=1)


def test_recusado_nao_muda_nada_nem_entra_no_registro():
    run = nova_run()
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    antes = processador.estado.impressao_digital()
    assert not processador.executar(C.EscolherEncontro(indice=99))               # caminho que não existe
    assert not processador.executar(C.DistribuirPonto(heroi=7, atributo="forca"))  # herói que não existe
    assert not processador.executar(C.AgirNoCombate(heroi=0, acao="concentrar"))  # não há combate
    assert processador.registro == [] and processador.estado.impressao_digital() == antes


def test_so_quem_comanda_o_heroi_age_com_ele():
    run = nova_run()
    run.grupo.dar_heroi(run.grupo.herois[1], Jogador("bia", "Bia"))
    run.grupo.herois[0].pontos_atributo = run.grupo.herois[1].pontos_atributo = 1
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    recusado = processador.executar(C.DistribuirPonto(jogador="local", heroi=1, atributo="forca"))
    assert not recusado and "outro jogador" in recusado.mensagem
    assert processador.executar(C.DistribuirPonto(jogador="bia", heroi=1, atributo="forca"))
    assert processador.executar(C.DistribuirPonto(jogador="local", heroi=0, atributo="forca"))
    assert not processador.executar(C.MoverItem(jogador="bia", chave="osso", de=0, para=BAU))   # mochila do outro


def test_mover_vender_e_equipar_por_comando():
    run = nova_run()
    estado = EstadoDoJogo(run)
    processador = ProcessadorDeComandos(estado)
    run.grupo.bau.adicionar("espada_enferrujada")
    run.grupo.bau.adicionar("osso", 3)
    assert processador.executar(C.MoverItem(chave="osso", de=BAU, para=0, quantidade=2))
    assert run.grupo.herois[0].inventario.quantidade("osso") >= 2 and run.grupo.bau.quantidade("osso") == 1
    ouro = run.grupo.ouro
    venda = processador.executar(C.Vender(origem=0, chave="osso", quantidade=2))
    assert venda and venda.valor > 0 and run.grupo.ouro == ouro + venda.valor
    equipou = processador.executar(C.Equipar(heroi=0, chave="espada_enferrujada", origem=BAU))
    assert equipou and run.grupo.herois[0].equipamento["arma"].chave == "espada_enferrujada"
    assert estado.origem_de(run.grupo.bau) == BAU
    assert estado.origem_de(run.grupo.herois[2].inventario) == 0       # (MP4: a mochila é do jogador, o 1º herói dele)
    assert [d["tipo"] for d in processador.registro] == ["mover_item", "vender", "equipar"]


# ---------------- condutor ----------------
def test_condutor_espera_o_heroi_e_so_aceita_o_heroi_da_vez():
    run = nova_run()
    estado = EstadoDoJogo(run)
    processador = ProcessadorDeComandos(estado)
    condutor = processador.executar(C.ComecarCombate(encontro=EncontroCombate("t", "", 1, ["goblin"]).para_dict())).valor
    assert condutor.avancar_ate_decisao() == ESPERANDO
    vez = estado.indice_do(condutor.heroi_da_vez())
    outro = next(i for i in range(len(run.grupo.herois)) if i != vez)
    assert not processador.executar(C.AgirNoCombate(heroi=outro, acao="concentrar"))
    assert processador.executar(C.AgirNoCombate(heroi=vez, acao="concentrar"))
    assert not condutor.esperando()


def test_decisor_ia_nao_gasta_o_sorteio_do_combate():
    """Decidir pelo herói (desconectado, piloto) não pode mudar o que acontece depois."""
    run = nova_run()
    estado = EstadoDoJogo(run)
    condutor = ProcessadorDeComandos(estado).executar(C.ComecarCombate(
        encontro=EncontroCombate("t", "", 1, ["goblin", "aranha"]).para_dict())).valor
    condutor.avancar_ate_decisao()
    antes = estado.impressao_digital()
    comando = DecisorIA().comando(estado, condutor.heroi_da_vez())
    assert isinstance(comando, C.AgirNoCombate) and estado.impressao_digital() == antes


def test_piloto_vence_um_combate_so_por_comandos():
    piloto = Piloto(nova_run())
    condutor = piloto.enviar(C.ComecarCombate(encontro=EncontroCombate("t", "", 1, ["goblin"]).para_dict())).valor
    while condutor.avancar_ate_decisao() == ESPERANDO:
        assert piloto.enviar(DecisorIA().comando(piloto.estado, condutor.heroi_da_vez()))
    assert condutor.passo() == FIM and condutor.recompensa is not None and condutor.combate.resultado == "vitoria"
    assert {d["tipo"] for d in piloto.processador.registro} == {"comecar_combate", "agir_no_combate"}


def test_piloto_desiste_de_uma_luta_que_nao_acaba(monkeypatch):
    """Trava de segurança do simulador: luta empatada para sempre (ninguém fere ninguém) vira derrota."""
    import roguelike.piloto_automatico as P
    monkeypatch.setattr(P, "LIMITE_DE_DECISOES", 2)
    run = nova_run()
    run.encontro = EncontroCombate("t", "", 5, ["aranha_mae"], "chefe")
    piloto = Piloto(run)
    piloto.lutar()
    assert run.resultado == "derrota" and piloto.estado.condutor.terminou()


# ---------------- determinismo ----------------
def test_mesma_semente_e_mesmos_comandos_dao_o_mesmo_estado():
    """O critério de aceite da MP2: o registro do piloto, refeito numa run nova com a mesma semente."""
    piloto = jogar_com_o_piloto()
    registro = piloto.processador.registro
    tipos = {d["tipo"] for d in registro}
    assert {"escolher_encontro", "comecar_combate", "agir_no_combate", "concluir_encontro"} <= tipos
    assert len(registro) > 100
    outra = ProcessadorDeComandos(EstadoDoJogo(nova_run()))
    outra.refazer(registro)
    assert outra.estado.impressao_digital() == piloto.estado.impressao_digital()
    assert outra.estado.run.para_dict() == piloto.estado.run.para_dict()


def test_outra_semente_da_outro_estado():
    a, b = jogar_com_o_piloto("UMA", 3), jogar_com_o_piloto("OUTRA", 3)
    assert a.estado.impressao_digital() != b.estado.impressao_digital()


def test_refazer_em_outra_semente_nao_chega_ao_mesmo_estado():
    """Com outra semente o registro deixa de bater: algum comando é recusado (ComandoRecusado) ou o fim é outro."""
    piloto = jogar_com_o_piloto(areas=4)
    outra = ProcessadorDeComandos(EstadoDoJogo(nova_run("OUTRA-SEMENTE")))
    try:
        outra.refazer(piloto.processador.registro)
    except ComandoRecusado:
        return
    assert outra.estado.impressao_digital() != piloto.estado.impressao_digital()


ROTEIRO = r"""
import sys
sys.path.insert(0, sys.argv[1])
from roguelike.piloto_automatico import Piloto, grupo_padrao
from roguelike.progresso import Progresso
piloto = Piloto(Progresso().criar_run(grupo_padrao(["guerreiro", "sacerdote", "patrulheira"]), "DETERMINISMO"))
piloto.jogar()
print(piloto.estado.impressao_digital(), len(piloto.processador.registro))
"""


def test_mesmo_estado_em_processos_diferentes(tmp_path):
    """Dois processos com PYTHONHASHSEED diferentes (a ordem dos set muda) chegam ao mesmo estado."""
    saidas = []
    for semente_do_hash in ("0", "4242"):
        ambiente = dict(os.environ, PYTHONHASHSEED=semente_do_hash, ECOS_DA_CRIPTA_DADOS=str(tmp_path / "dados"))
        processo = subprocess.run([sys.executable, "-c", ROTEIRO, os.path.join(RAIZ, "src")], cwd=RAIZ,
                                  env=ambiente, capture_output=True, text=True, timeout=600)
        assert processo.returncode == 0, processo.stderr
        saidas.append(processo.stdout.split()[-2:])
    assert saidas[0] == saidas[1]
    assert saidas[0][0] == jogar_com_o_piloto().estado.impressao_digital()


# ---------------- pelas telas ----------------
def test_o_que_se_faz_nas_telas_vira_comando_e_da_para_refazer(tmp_path):
    """Uma luta pela tela de combate (heróis no DecisorIA), a volta ao mapa e uma ação no grupo: refeitas do zero
    a partir do registro da sessão, chegam ao mesmo estado (nenhuma tela mexe na run por fora dos comandos)."""
    from telas import comum, fluxo
    from telas.base import App
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    try:
        app = App(janela=False)
        app.velocidade = 4.0
        app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
        run = app.progresso.criar_run(grupo_padrao(CLASSES), "TELAS")
        fluxo.ir_para_mapa(app, run)
        app.passo(1 / 30, [])
        combate = next(i for i, o in enumerate(run.opcoes_de_encontro()) if o.eh_combate())
        app.atual.escolher(combate)
        tela = app.atual
        assert type(tela).__name__ == "TelaCombate"
        sessao = app.sessao_da(run)
        sessao.decisores = {i: DecisorIA() for i in range(len(run.grupo.herois))}
        for _ in range(20000):
            app.passo(1 / 30, [])
            if tela.estado == "fim" and not tela.fila:
                break
        assert tela.estado == "fim"
        tela.ao_terminar(tela.recompensa)                 # Enter na janela de recompensas
        app.passo(1 / 30, [])
        if run.terminou():
            pytest.skip("o grupo caiu na primeira luta (semente ruim para este teste)")
        from telas.grupo import TelaGrupo
        grupo = TelaGrupo(app, run, "herois", lambda: None)
        heroi = run.grupo.herois[0]
        if heroi.pontos_atributo:                         # (subiu de nível na luta)
            grupo.aumentar_atributo(heroi.classe.atributos_principais[0])
        registro = sessao.processador.registro
        assert registro[0]["tipo"] == "escolher_encontro" and registro[1]["tipo"] == "comecar_combate"
        assert any(d["tipo"] == "agir_no_combate" for d in registro) and registro[-1]["tipo"] in (
            "concluir_encontro", "distribuir_ponto")
        refeita = ProcessadorDeComandos(EstadoDoJogo(Progresso().criar_run(grupo_padrao(CLASSES), "TELAS")))
        refeita.refazer(registro)
        assert refeita.estado.impressao_digital() == sessao.estado.impressao_digital()
        assert refeita.estado.run.para_dict() == run.para_dict()
    finally:
        comum.ArquivoDaRun.caminho = None
