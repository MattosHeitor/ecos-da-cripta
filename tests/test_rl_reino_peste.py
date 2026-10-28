"""Reino dos Ratos, etapa 3A: o status Peste (níveis, Febre Negra, cura, raças, entre as lutas),
o Tônico do Médico, o sistema de bandos ("Ratos ×12") e os três primeiros ratos."""

import random

from roguelike.bando import Bando
from roguelike.classes import criar_heroi, heroi_para_dict, heroi_de_dict
from roguelike.combate import Combate
from roguelike.dados import regras
from roguelike.encontros import EncontroCombate
from roguelike.inimigos import criar_inimigo, ficha
from roguelike.itens import item
from roguelike.run import Run


def combate_com(herois=None, inimigos=None, semente=1):
    combate = Combate(herois or [criar_heroi("guerreiro")], inimigos or [criar_inimigo("goblin")], random.Random(semente))
    combate.iniciar()
    return combate


def com_peste(combate, heroi, nivel):
    return combate.aplicar_status(heroi, "peste", acumulos=nivel)


# ---------------- o status ----------------

def test_peste_acumula_ate_o_nivel_5_e_nao_acaba_sozinha():
    combate = combate_com()
    heroi = combate.herois[0]
    for _ in range(7):
        com_peste(combate, heroi, 1)
    peste = heroi.status["peste"]
    assert peste.nivel == 5 and peste.rotulo() == "Peste 5 (Febre Negra)"
    for _ in range(10):
        assert peste.fim_do_turno() is False


def test_peste_tira_vida_por_nivel_e_corta_a_cura_a_partir_do_3():
    tabela = regras()["status"]["peste"]["dano_por_nivel"]
    for nivel in (1, 2, 3, 4):
        combate = combate_com()
        heroi = combate.herois[0]
        com_peste(combate, heroi, nivel)
        antes = heroi.vida
        heroi.status["peste"].inicio_do_turno(heroi, combate)
        assert antes - heroi.vida == tabela[nivel - 1]
        assert heroi.stat("cura_recebida") < 1.0 if nivel >= 3 else heroi.stat("cura_recebida") >= 1.0


def test_febre_negra_faz_o_heroi_agir_sem_rumo_e_volta_ao_nivel_3():
    combate = combate_com()
    heroi = combate.herois[0]
    com_peste(combate, heroi, 5)
    combate.fila = [heroi]
    combate.ordem_da_rodada = [heroi]
    combate.comecar_turno()
    tipos = [e.tipo for e in combate.eventos]
    assert "febre" in tipos
    assert any(e.tipo in ("habilidade", "concentrar") and e.origem is heroi for e in combate.eventos)
    assert not combate.pode_agir                                  # o jogador não escolhe nada neste turno
    assert heroi.acumulos_de("peste") == 3


def test_purificar_tira_um_nivel_e_o_tonico_tira_tudo():
    combate = combate_com()
    heroi = combate.herois[0]
    com_peste(combate, heroi, 3)
    combate.aplicar_status(heroi, "veneno", 2, 2)
    combate.purificar(heroi)                                      # (Antídoto) o veneno sai, a Peste cede 1
    assert not heroi.tem_status("veneno") and heroi.acumulos_de("peste") == 2
    assert any(e.tipo == "alivio" for e in combate.eventos)
    tonico = item("tonico_do_medico")
    combate.atual, combate.pode_agir = heroi, True
    assert combate.usar_item(heroi, tonico, heroi)
    assert not heroi.tem_status("peste")


def test_cura_de_luz_tira_um_nivel():
    sacerdote = criar_heroi("sacerdote")
    sacerdote.aprender("cura_sagrada")
    combate = combate_com([sacerdote])
    com_peste(combate, sacerdote, 2)
    combate.atual, combate.pode_agir = sacerdote, True
    assert combate.usar_habilidade(sacerdote, "cura_sagrada", sacerdote)
    assert sacerdote.acumulos_de("peste") == 1


def test_racas_resistem_ou_pegam_mais_facil():
    def tentativas(raca):
        pegou, niveis = 0, 0
        for semente in range(60):
            heroi = criar_heroi("guerreiro")
            heroi.definir_raca(raca)
            combate = combate_com([heroi], semente=semente)
            if com_peste(combate, heroi, 1):
                pegou += 1
                niveis += heroi.acumulos_de("peste")
        return pegou, niveis
    humano, morto_vivo, anao, gnomo = (tentativas(r) for r in ("humano", "revenante", "anao_das_profundezas", "gnomo"))
    assert humano == (60, 60)
    assert morto_vivo[0] < anao[0] < humano[0]
    assert gnomo[0] == 60 and gnomo[1] > 60                       # gnomos às vezes pegam 2 níveis de uma vez


def test_ratos_sao_imunes_a_peste():
    for chave in ("rato_comum", "ratazana_gigante", "rato_da_peste"):
        assert criar_inimigo(chave).imune("peste")


# ---------------- entre as lutas ----------------

def vencer(run, inimigos=("goblin",)):
    run.encontro = EncontroCombate("t", "", 1, list(inimigos))
    combate = run.criar_combate()
    return combate


def test_peste_segue_para_a_proxima_luta_e_a_fogueira_cura():
    run = Run([criar_heroi("guerreiro")], "PESTE", "reino_dos_ratos")
    heroi = run.grupo.herois[0]
    combate = vencer(run)
    com_peste(combate, heroi, 2)
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 99999, heroi)
    combate.verificar_fim()
    run.concluir_combate(combate)
    assert heroi.peste == 2 and heroi.status == {}
    combate = vencer(run)                                         # a próxima luta já começa com a Peste
    assert heroi.acumulos_de("peste") == 2
    run.fogueira()
    assert heroi.peste == 0


def test_tonico_fora_da_luta_e_peste_no_save():
    run = Run([criar_heroi("guerreiro")], "PESTE", "reino_dos_ratos")
    heroi = run.grupo.herois[0]
    heroi.peste = 3
    assert heroi_de_dict(heroi_para_dict(heroi)).peste == 3
    run.grupo.bau.adicionar("tonico_do_medico")
    assert run.usar_fora_do_combate("tonico_do_medico", run.grupo.bau, heroi)
    assert heroi.peste == 0 and not run.grupo.bau.tem("tonico_do_medico")


# ---------------- bandos ----------------

def test_bando_conta_os_ratos_pela_vida():
    bando = criar_inimigo("rato_comum")
    assert isinstance(bando, Bando) and bando.quantos == 12 and bando.nome == "Ratos ×12"
    bando.vida = bando.vida_maxima // 2
    assert bando.nome == "Ratos ×6"
    bando.vida = 1
    assert bando.vivos() == 1
    bando.vida = 0
    assert bando.vivos() == 0


def test_bando_perde_dano_com_menos_ratos():
    bando = criar_inimigo("rato_comum")
    cheio = bando.stat("dano_causado")
    bando.vida = bando.vida_maxima // 2
    perdido = regras()["bandos"]["dano_perdido"]
    assert abs((cheio - bando.stat("dano_causado")) - perdido * 0.5) < 1e-9


def test_area_machuca_mais_o_bando_e_alvo_unico_menos():
    regra = regras()["bandos"]
    bando, goblin = criar_inimigo("rato_comum"), criar_inimigo("goblin")
    assert bando.multiplicador_contra(False) == 1 + regra["area"]
    assert bando.multiplicador_contra(True) == 1 + regra["alvo_unico"]
    assert goblin.multiplicador_contra(False) == goblin.multiplicador_contra(True) == 1.0


def test_bando_vale_um_abate_por_rato():
    run = Run([criar_heroi("guerreiro")], "BANDO", "reino_dos_ratos")
    combate = vencer(run, ["rato_comum"])
    combate.causar_dano(combate.inimigos[0], 99999, run.grupo.herois[0])
    combate.verificar_fim()
    recompensa = run.concluir_combate(combate)
    assert recompensa.abates.count("rato_comum") == 12


def test_ratos_novos_estao_no_reino_com_sprite_e_familia_pestes():
    from roguelike.regioes import regiao
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for chave in ("rato_comum", "ratazana_gigante", "rato_da_peste"):
        assert chave in regiao("reino_dos_ratos").inimigos
        assert ficha(chave)["familia"] == "pestes"
        assert sprites.existe(chave)
    assert "tonico_do_medico" in regiao("reino_dos_ratos").consumiveis_a_venda()
