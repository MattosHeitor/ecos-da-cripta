"""Fase 4, etapa 5: Minas de Brasa (explosão ao morrer, armas desgastadas, reforjar, receitas anãs)."""

from roguelike.classes import criar_heroi
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.piloto_automatico import grupo_padrao
from roguelike.progresso import Progresso

from apoio_roguelike import combate_pronto


def test_kobold_explode_ao_morrer():
    herois = [criar_heroi("guerreiro"), criar_heroi("mago")]
    kobold = criar_inimigo("kobold_dinamiteiro")
    combate = combate_pronto(herois, [kobold, criar_inimigo("goblin")])
    vidas = [h.vida for h in herois]
    combate.causar_dano(kobold, 999, herois[0])
    assert all(h.vida < v for h, v in zip(herois, vidas))


def test_minerador_volta_uma_vez():
    heroi = criar_heroi("guerreiro")
    minerador = criar_inimigo("minerador_amaldicoado")
    combate = combate_pronto([heroi], [minerador])
    combate.causar_dano(minerador, 999, heroi)
    assert minerador.esta_vivo()
    combate.causar_dano(minerador, 999, heroi)
    assert not minerador.esta_vivo()


def test_forjador_reforja_e_desgasta_armas_e_a_pedra_conserta():
    herois = [criar_heroi("guerreiro"), criar_heroi("sacerdote")]
    forjador = criar_inimigo("forjador_antigo")
    combate = combate_pronto(herois, [forjador])
    reforjar = next(p for p in forjador.passivas if p.dados["tipo"] == "a_cada_n_turnos")
    for _ in range(3):
        reforjar.inicio_do_turno(forjador, combate)
    assert forjador.tem_status("escudo")
    combate.aplicar_status(herois[0], "arma_desgastada")
    combate.atual, combate.pode_agir = herois[1], True
    combate.usar_item(herois[1], item("pedra_de_amolar"), herois[0])
    assert not herois[0].tem_status("arma_desgastada") and herois[0].tem_status("afiado")


def test_vencer_o_forjador_libera_as_receitas_anas_para_sempre():
    progresso = Progresso()
    run = progresso.criar_run(grupo_padrao(("guerreiro",)), "ANAO1")
    assert "martelo_do_forjador_antigo" not in run.descobertas
    progresso.conquistas.add("chefe:forjador_antigo")
    run = progresso.criar_run(grupo_padrao(("guerreiro",)), "ANAO2")
    assert {"martelo_do_forjador_antigo", "couraca_de_brasa"} <= run.descobertas
    for chave, n in {"martelo_partido": 1, "coracao_de_golem": 1, "minerio_de_brasa": 3}.items():
        run.grupo.bau.adicionar(chave, n)
    assert not run.fabricar("martelo_do_forjador_antigo")                 # sem Anão no grupo
    run.grupo.herois[0].definir_raca("anao_das_profundezas")
    assert run.fabricar("martelo_do_forjador_antigo")
    assert run.grupo.bau.tem("martelo_do_forjador_antigo")
