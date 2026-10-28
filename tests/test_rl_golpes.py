"""Golpes: espaços equipados (regras: 6), grimório, golpes novos, evolução, tomos e save."""

import random

from roguelike.classes import criar_heroi, heroi_para_dict, heroi_de_dict
from roguelike.golpes import golpe, evolucoes, todas_as_chaves, GerenciadorDeGolpes
from roguelike.grupo import Grupo
from roguelike.itens import item, todos_os_itens
from roguelike.run import Run
from roguelike.piloto_automatico import Piloto, grupo_padrao


GUERREIRO_EXTRAS = ("lanca_da_justica", "juramento", "frenesi", "sede_de_sangue")


def cheio(classe="guerreiro", extras=GUERREIRO_EXTRAS, **kw):
    """Herói com todos os espaços ocupados (os golpes que sobrarem vão para o grimório)."""
    heroi = criar_heroi(classe, **kw)
    for chave in extras:
        if len(heroi.golpes.equipados) < GerenciadorDeGolpes.espacos_base():
            heroi.aprender(chave)
    assert len(heroi.golpes.equipados) == GerenciadorDeGolpes.espacos_base()
    return heroi


def test_heroi_comeca_com_os_golpes_iniciais_equipados():
    assert GerenciadorDeGolpes.espacos_base() == 6
    for classe in ("guerreiro", "mago", "bardo", "bobo"):
        heroi = grupo_padrao([classe])[0]
        assert len(heroi.golpes.equipados) == min(GerenciadorDeGolpes.espacos_base(), len(heroi.niveis_habilidade))
        assert [g.chave for g, _ in heroi.habilidades()] == heroi.golpes.equipados


def test_com_espacos_cheios_o_golpe_novo_espera_decisao():
    heroi = cheio()
    resultado = heroi.aprender("baluarte")
    assert resultado.situacao == "escolher"
    assert heroi.golpes.pendentes == ["baluarte"]
    assert "baluarte" not in [g.chave for g, _ in heroi.habilidades()]   # ainda não vai para o combate
    assert heroi.aprender("baluarte").situacao == "ja_sabe"


def test_trocar_pelo_novo_manda_o_antigo_para_o_grimorio():
    heroi = cheio()
    heroi.aprender("baluarte")
    assert heroi.golpes.decidir("baluarte", "desafio")
    assert heroi.golpes.equipados[2] == "baluarte"                       # no mesmo lugar do antigo
    assert heroi.golpes.grimorio == ["desafio"] and not heroi.golpes.pendentes
    assert heroi.nivel_da("desafio") == 1                                  # nada se perde


def test_recusar_guarda_o_novo_no_grimorio_e_da_para_trocar_depois():
    heroi = cheio()
    heroi.aprender("baluarte")
    heroi.golpes.decidir("baluarte")
    assert heroi.golpes.grimorio == ["baluarte"]
    assert heroi.golpes.trocar("baluarte", "redemoinho")
    assert "baluarte" in heroi.golpes.equipados and heroi.golpes.grimorio == ["redemoinho"]


def test_guardar_deixa_ao_menos_um_golpe_e_libera_espaco():
    heroi = criar_heroi("ladino")
    for chave in list(heroi.golpes.equipados)[:-1]:
        assert heroi.golpes.guardar(chave)
    assert not heroi.golpes.guardar(heroi.golpes.equipados[0])
    assert heroi.aprender("passo_sombrio").situacao == "equipado"     # tinha espaço livre


def test_evolucao_por_nivel_mantem_lugar_e_nivel():
    heroi = criar_heroi("guerreiro")
    heroi.niveis_habilidade["golpe"] = 3
    for _ in range(7):
        heroi.subir_nivel()                                               # nível 8
    feitas = heroi.golpes.verificar_evolucoes()
    assert feitas == [("golpe", "corte_veterano")]
    assert heroi.golpes.equipados[0] == "corte_veterano" and heroi.nivel_da("corte_veterano") == 3
    assert "Golpe aprimorado!" in [titulo for titulo, _ in heroi.golpes.pegar_avisos()]


def test_evolucao_por_especializacao_e_por_marco():
    run = Run(grupo_padrao(["guerreiro", "sacerdote"]), "EVOLUI")
    guerreiro, sacerdote = run.grupo.herois
    run.verificar_evolucoes()
    assert not guerreiro.golpes.sabe("muralha_de_ferro")          # só Cavaleiro ainda não basta
    for _ in range(4):
        guerreiro.subir_nivel()
    guerreiro.escolher_especializacao(guerreiro.subclasse.especializacoes["guardiao_juramentado"])
    run.verificar_evolucoes()
    assert guerreiro.golpes.sabe("muralha_de_ferro") and not guerreiro.golpes.sabe("golpe_de_escudo")
    assert not sacerdote.golpes.sabe("milagre")
    run.estatisticas["chefes"].append("aranha_mae")
    run.verificar_evolucoes()
    assert sacerdote.golpes.sabe("milagre")


def test_todas_as_evolucoes_apontam_para_golpes_que_existem():
    chaves = set(todas_as_chaves())
    for origem, dados in evolucoes().items():
        assert origem in chaves and dados["para"] in chaves, origem
        assert golpe(origem).texto_do_requisito()


def test_tomo_ensina_fora_do_combate_e_nao_entra_no_combate():
    heroi = cheio("mago", ("lanca_de_gelo", "corrente_de_raios", "toque_da_morte"), subclasse="piromante")
    grupo = Grupo([heroi])
    grupo.bau.adicionar("tomo_do_baluarte")
    tomo = item("tomo_do_baluarte")
    assert not tomo.usavel_em_combate and not heroi.equipar(tomo)[0]
    assert grupo.usar_fora_do_combate("tomo_do_baluarte", grupo.bau, heroi, random.Random(1))
    assert heroi.golpes.pendentes == ["baluarte"] and not grupo.bau.tem("tomo_do_baluarte")
    grupo.bau.adicionar("tomo_do_baluarte")
    assert not grupo.usar_fora_do_combate("tomo_do_baluarte", grupo.bau, heroi, random.Random(1))  # já sabe


def test_todos_os_tomos_ensinam_golpes_que_existem():
    tomos = [i for i in todos_os_itens().values() if getattr(i, "ensina", None)]
    assert len(tomos) >= 6
    for tomo in tomos:
        assert tomo.golpe().nome


def test_golpes_salvam_e_carregam():
    heroi = criar_heroi("guerreiro")
    heroi.aprender("baluarte")
    heroi.golpes.decidir("baluarte", "desafio")
    heroi.aprender("lanca_da_justica")                                    # fica pendente
    copia = heroi_de_dict(heroi_para_dict(heroi))
    assert copia.golpes.para_dict() == heroi.golpes.para_dict()


def test_save_antigo_sem_golpes_equipa_os_primeiros():
    heroi = cheio()
    heroi.aprender("baluarte", perguntar=False)
    dados = heroi_para_dict(heroi)
    dados.pop("golpes")
    copia = heroi_de_dict(dados)
    assert len(copia.golpes.equipados) == GerenciadorDeGolpes.espacos_base() and copia.golpes.grimorio == ["baluarte"]


def test_piloto_decide_os_golpes_novos():
    run = Run(grupo_padrao(["guerreiro"]), "PILOTO-GOLPES")
    heroi = run.grupo.herois[0]
    heroi.aprender("lanca_da_justica")
    Piloto(run).decidir_golpes()
    assert not heroi.golpes.pendentes
    assert any(golpe(c).custo == 0 for c in heroi.golpes.equipados), "nunca fica sem golpe grátis"
