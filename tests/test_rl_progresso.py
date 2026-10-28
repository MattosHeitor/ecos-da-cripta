"""Testes da progressão permanente: prestígio, talentos, bênçãos, raças e conquistas."""

import pytest

from roguelike.classes import criar_heroi, todas_as_classes
from roguelike.dados import regras
from roguelike.passivas import criar_passiva
from roguelike.progresso import Progresso, arvore_da_classe, bencaos, racas
from roguelike.run import Run

from test_rl_run import vencer


def progresso_com_prestigio(classe="guerreiro", nivel=10, brasas=1000):
    progresso = Progresso()
    progresso.prestigio[classe] = {"nivel": nivel, "xp": 0}
    progresso.brasas = brasas
    return progresso


# ---------------- prestígio ----------------

def test_prestigio_sobe_de_nivel_e_para_no_maximo():
    progresso = Progresso()
    assert progresso.ganhar_prestigio("mago", progresso.xp_para_proximo_prestigio("mago")) == 1
    assert progresso.nivel_de_prestigio("mago") == 1
    progresso.ganhar_prestigio("mago", 10 ** 7)
    assert progresso.nivel_de_prestigio("mago") == regras()["progresso"]["prestigio_maximo"]


def test_cada_nivel_de_prestigio_da_3_pontos():
    progresso = progresso_com_prestigio(nivel=4)
    assert progresso.pontos_totais("guerreiro") == 12


# ---------------- árvores de talentos ----------------

def test_toda_classe_tem_arvore_valida():
    for chave, classe in todas_as_classes().items():
        arvore = arvore_da_classe(chave)
        assert len(arvore) >= 12, chave
        for no in arvore.values():
            for requisito in no.requer:
                assert requisito in arvore, (chave, no.chave)
            efeito = no.efeito
            if efeito["tipo"] == "nivel_habilidade":
                assert efeito["habilidade"] in classe.habilidades, (chave, no.chave)
            if efeito["tipo"] == "passiva":
                criar_passiva(efeito["passiva"])
            assert no.descricao()


def test_arvore_completa_cabe_nos_pontos_do_prestigio_maximo():
    maximo = regras()["progresso"]["prestigio_maximo"] * regras()["progresso"]["pontos_por_prestigio"]
    for chave in todas_as_classes():
        total = sum(no.custo * no.maximo for no in arvore_da_classe(chave).values())
        assert total <= maximo, chave


def test_no_so_libera_depois_do_vizinho():
    progresso = progresso_com_prestigio()
    assert not progresso.pode_comprar_talento("guerreiro", "a1")
    assert progresso.comprar_talento("guerreiro", "raiz")
    assert progresso.comprar_talento("guerreiro", "a1")
    assert progresso.pontos_gastos("guerreiro") == 2


def test_no_tem_limite_de_niveis():
    progresso = progresso_com_prestigio()
    progresso.comprar_talento("guerreiro", "raiz")
    assert not progresso.comprar_talento("guerreiro", "raiz")


def test_sem_pontos_nao_compra():
    progresso = progresso_com_prestigio(nivel=0)
    assert not progresso.comprar_talento("guerreiro", "raiz")


def test_reiniciar_arvore_custa_brasas_e_devolve_os_pontos():
    progresso = progresso_com_prestigio(brasas=100)
    progresso.comprar_talento("guerreiro", "raiz")
    assert progresso.reiniciar_arvore("guerreiro")
    assert progresso.pontos_gastos("guerreiro") == 0
    assert progresso.brasas == 100 - regras()["progresso"]["preco_reiniciar_arvore"]


def test_talentos_valem_na_run():
    progresso = progresso_com_prestigio()
    for no in ("raiz", "a1", "a1", "b1", "b1", "c1"):
        assert progresso.comprar_talento("guerreiro", no)
    heroi = criar_heroi("guerreiro")
    forca = heroi.atributo("forca")
    progresso.preparar_heroi(heroi, 1)
    assert heroi.atributo("forca") == forca + 3        # raiz +1, a1 x2
    assert heroi.nivel_da("golpe") == 3                 # b1 x2
    assert heroi.vida == heroi.vida_maxima


# ---------------- bênçãos ----------------

def test_bencoes_validas():
    for chave, dados in bencaos().items():
        assert 1 <= dados["espacos"] <= 5, chave
        assert 10 <= dados["preco"] <= 300, chave
        for passiva in dados.get("passivas", []):
            criar_passiva(passiva)


def test_comprar_e_equipar_bencao_respeita_os_5_espacos():
    progresso = Progresso()
    progresso.brasas = 10000
    for chave in ("ultimo_suspiro", "sangue_frio", "mao_firme"):
        assert progresso.comprar_bencao(chave)
    assert progresso.equipar_bencao("ultimo_suspiro")      # 3 espaços
    assert progresso.equipar_bencao("sangue_frio")         # 2 espaços
    assert not progresso.equipar_bencao("mao_firme")       # não cabe
    progresso.desequipar_bencao("sangue_frio")
    assert progresso.equipar_bencao("mao_firme")


def test_nao_equipa_bencao_que_nao_comprou():
    assert not Progresso().equipar_bencao("vigor")


def test_bencao_escondida_precisa_da_conquista():
    progresso = Progresso()
    progresso.brasas = 1000
    assert not progresso.bencao_visivel("coroa_de_teias")
    assert not progresso.comprar_bencao("coroa_de_teias")
    progresso.conquistas.add("chefe:aranha_mae")
    assert progresso.comprar_bencao("coroa_de_teias")


def test_mao_firme_fixa_o_critico():
    progresso = Progresso()
    progresso.bencaos_compradas = ["mao_firme"]
    progresso.equipar_bencao("mao_firme")
    heroi = criar_heroi("ladino")
    heroi.atributos.aumentar("sorte", 30)
    progresso.preparar_heroi(heroi, 1)
    assert heroi.stat("chance_critico") == 0.05 and heroi.stat("dano_critico") == 2.0


def test_aprendiz_de_tudo():
    progresso = progresso_com_prestigio()
    progresso.comprar_talento("guerreiro", "raiz")
    progresso.bencaos_compradas = ["aprendiz_de_tudo"]
    progresso.equipar_bencao("aprendiz_de_tudo")
    referencia = criar_heroi("guerreiro")
    Progresso().preparar_heroi(referencia, 1)                # só a raça (humano)
    heroi = criar_heroi("guerreiro")
    progresso.preparar_heroi(heroi, 1)
    assert heroi.nivel_da("cura_sagrada") == 1 and heroi.nivel_da("flecha") == 1
    assert heroi.atributo("forca") == referencia.atributo("forca")     # sem árvore
    assert heroi.vida_maxima == referencia.vida_maxima + 35
    assert not heroi.escolher_subclasse(heroi.classe.subclasses["cavaleiro"])


def test_lobo_solitario_so_vale_sozinho():
    progresso = Progresso()
    progresso.bencaos_compradas = ["lobo_solitario"]
    progresso.equipar_bencao("lobo_solitario")
    sozinho, em_grupo = criar_heroi("guerreiro"), criar_heroi("guerreiro")
    progresso.preparar_heroi(sozinho, 1)
    progresso.preparar_heroi(em_grupo, 2)
    assert sozinho.stat("dano_causado") > em_grupo.stat("dano_causado")


def test_bencoes_de_run():
    progresso = Progresso()
    progresso.bencaos_compradas = ["bolsa_pesada", "bencao_do_colecionador"]
    progresso.equipar_bencao("bolsa_pesada")
    progresso.equipar_bencao("bencao_do_colecionador")
    run = progresso.criar_run([criar_heroi("guerreiro")], "B1")
    assert run.grupo.ouro == regras()["economia"]["ouro_inicial"] + 60
    assert run.bonus_loot == pytest.approx(0.25)


# ---------------- raças ----------------

def test_racas_validas():
    assert "humano" in racas() and racas()["humano"]["preco"] == 0
    for chave, dados in racas().items():
        for passiva in dados.get("passivas", []):
            criar_passiva(passiva)


def test_humano_ganha_ponto_extra_a_cada_2_niveis():
    heroi = criar_heroi("guerreiro")
    Progresso().preparar_heroi(heroi, 1)
    heroi.subir_nivel()                                      # nível 2
    assert heroi.pontos_atributo == regras()["nivel"]["pontos_atributo"] + 1
    heroi.subir_nivel()                                      # nível 3
    assert heroi.pontos_atributo == 2 * regras()["nivel"]["pontos_atributo"] + 1


def test_raca_nao_comprada_vira_humano():
    heroi = criar_heroi("guerreiro")
    heroi.raca = "revenante"
    Progresso().preparar_heroi(heroi, 1)
    assert heroi.raca == "humano"


def test_comprar_raca_e_usar():
    progresso = Progresso()
    progresso.brasas = 500
    assert progresso.comprar_raca("anao_das_profundezas")
    heroi = criar_heroi("guerreiro")
    defesa = heroi.stat("defesa")
    heroi.raca = "anao_das_profundezas"
    progresso.preparar_heroi(heroi, 1)
    assert heroi.stat("defesa") == defesa + 1


def test_raca_escondida_precisa_da_conquista():
    progresso = Progresso()
    progresso.brasas = 500
    assert not progresso.comprar_raca("hemofago")
    progresso.conquistas.add("derrotou:vampiro")
    assert progresso.comprar_raca("hemofago")


# ---------------- fim da run ----------------

def test_fim_de_run_da_brasas_prestigio_e_conquistas():
    progresso = Progresso()
    run = progresso.criar_run([criar_heroi("guerreiro")], "FIM")
    run.area = run.areas_da_regiao()                         # a área do chefe (o tamanho é sorteado na run)
    vencer(run, run.opcoes_de_encontro()[0])
    run.concluir_encontro()
    run.subclasses_aprendidas.append("cavaleiro")
    relatorio = progresso.registrar_fim_de_run(run)
    assert relatorio.brasas > 0 and progresso.brasas == relatorio.brasas
    assert "chefe:aranha_mae" in progresso.conquistas
    assert "item:alma_da_mae_aranha" in progresso.conquistas
    assert "subclasse:cavaleiro" in progresso.conquistas
    assert progresso.estatisticas["runs"] == 1
    assert relatorio.prestigio["guerreiro"][0] > 0


def test_subclasses_liberadas_pelo_prestigio():
    progresso = Progresso()
    assert [s.chave for s in progresso.subclasses_disponiveis("guerreiro")] == ["cavaleiro"]
    progresso.prestigio["guerreiro"] = {"nivel": 3, "xp": 0}
    assert [s.chave for s in progresso.subclasses_disponiveis("guerreiro")] == ["cavaleiro", "berserker"]
    progresso.prestigio["guerreiro"] = {"nivel": 6, "xp": 0}
    assert len(progresso.subclasses_disponiveis("guerreiro")) == 3


def test_fim_de_run_avisa_subclasse_liberada_pelo_prestigio():
    progresso = Progresso()
    progresso.prestigio["guerreiro"] = {"nivel": 2, "xp": 0}
    run = progresso.criar_run([criar_heroi("guerreiro", subclasse="cavaleiro")], "PRESTIGIO")
    run.estatisticas["areas"] = 40                       # prestígio de sobra para subir de nível
    relatorio = progresso.registrar_fim_de_run(run)
    assert progresso.nivel_de_prestigio("guerreiro") >= 3
    assert "berserker" in relatorio.subclasses_novas


# ---------------- salvar ----------------

def test_progresso_salva_e_carrega(tmp_path):
    progresso = progresso_com_prestigio()
    progresso.comprar_talento("guerreiro", "raiz")
    progresso.comprar_bencao("vigor")
    progresso.equipar_bencao("vigor")
    progresso.conquistas.add("vitoria")
    caminho = str(tmp_path / "progresso.json")
    progresso.salvar(caminho)
    assert Progresso.carregar(caminho).para_dict() == progresso.para_dict()


def test_carregar_sem_arquivo_comeca_do_zero(tmp_path):
    progresso = Progresso.carregar(str(tmp_path / "nao_existe.json"))
    assert progresso.brasas == 0 and progresso.racas_compradas == ["humano"]


def test_run_com_talentos_salva_e_carrega_igual(tmp_path):
    progresso = progresso_com_prestigio()
    for no in ("raiz", "c1", "c2", "a1"):
        progresso.comprar_talento("guerreiro", no)
    progresso.comprar_bencao("vigor")
    progresso.equipar_bencao("vigor")
    heroi = criar_heroi("guerreiro")
    run = progresso.criar_run([heroi], "SAVE")
    caminho = str(tmp_path / "run.json")
    run.salvar(caminho)
    novo = Run.carregar(caminho).grupo.herois[0]
    assert novo.atributo("forca") == heroi.atributo("forca")
    assert novo.vida_maxima == heroi.vida_maxima
    assert novo.stat("reducao_bloqueio") == pytest.approx(heroi.stat("reducao_bloqueio"))
    assert novo.vida == heroi.vida
