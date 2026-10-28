"""Reino dos Ratos, etapa 3B: Rato Ladrão (rouba e foge), Rato Nadador (mergulha na água funda),
Rato Bombardeiro (explode em todos), Rato Alquimista (frascos e cura dos ratos), Rato Xamã (praga e reerguer),
Guarda Real Roedor (entra na frente) e Arauto Roedor (chama reforços)."""

import random

from roguelike.ambiente import criar_ambientes
from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.efeitos_habilidade import Contexto, criar_efeito
from roguelike.ia import ia_do
from roguelike.inimigos import criar_inimigo, ficha

NOVOS = ("rato_ladrao", "rato_nadador", "rato_bombardeiro", "rato_alquimista", "rato_xama", "rato_guarda_real",
         "rato_arauto")


def combate_com(inimigos, herois=None, ambientes=None, semente=1):
    combate = Combate(herois or [criar_heroi("guerreiro")], inimigos, random.Random(semente))
    combate.ambientes = criar_ambientes(ambientes)
    combate.iniciar()
    return combate


def turno_de(combate, lutador):
    """Faz o lutador começar um turno agora (e devolve se ele ainda pode agir)."""
    combate.fila = [lutador]
    combate.comecar_turno()
    return combate.pode_agir


def vez_de(combate, lutador):
    combate.atual, combate.pode_agir = lutador, True


# ---------------- Rato Ladrão ----------------

def heroi_com_pocoes(quantidade=2):
    heroi = criar_heroi("guerreiro")
    heroi.inventario.adicionar("pocao_de_vida", quantidade)
    return heroi


def roubar(combate, ladrao, heroi):
    criar_efeito({"tipo": "roubar_item"}).aplicar(combate, ladrao, [heroi], 1, Contexto())


def test_ladrao_rouba_um_consumivel_e_foge_em_2_turnos():
    heroi, ladrao = heroi_com_pocoes(), criar_inimigo("rato_ladrao")
    combate = combate_com([ladrao, criar_inimigo("goblin")], [heroi])
    roubar(combate, ladrao, heroi)
    assert heroi.inventario.quantidade("pocao_de_vida") == 1 and ladrao.roubados == [("pocao_de_vida", heroi)]
    assert any(e.tipo == "roubo" for e in combate.eventos)
    assert turno_de(combate, ladrao)                               # 1º turno depois do roubo: ainda está aqui
    combate.encerrar_turno()
    assert not turno_de(combate, ladrao)                           # 2º: fugiu
    assert ladrao not in combate.inimigos and ladrao not in combate.derrotados
    assert any(e.tipo == "fugiu" for e in combate.eventos)
    assert heroi.inventario.quantidade("pocao_de_vida") == 1      # a poção foi embora com ele


def test_derrotar_o_ladrao_devolve_o_que_ele_roubou():
    heroi, ladrao = heroi_com_pocoes(), criar_inimigo("rato_ladrao")
    combate = combate_com([ladrao, criar_inimigo("goblin")], [heroi])
    roubar(combate, ladrao, heroi)
    combate.causar_dano(ladrao, 999, heroi)
    assert heroi.inventario.quantidade("pocao_de_vida") == 2
    assert ladrao in combate.derrotados


def test_ladrao_sem_nada_para_roubar_nao_foge():
    heroi, ladrao = criar_heroi("guerreiro"), criar_inimigo("rato_ladrao")
    combate = combate_com([ladrao], [heroi])
    roubar(combate, ladrao, heroi)
    for _ in range(3):
        assert turno_de(combate, ladrao)
        combate.encerrar_turno()
    assert ladrao in combate.inimigos


# ---------------- Rato Nadador ----------------

def test_nadador_mergulha_na_agua_funda_e_nao_na_rasa():
    heroi, nadador, goblin = criar_heroi("guerreiro"), criar_inimigo("rato_nadador"), criar_inimigo("goblin")
    combate = combate_com([nadador, goblin], [heroi], [{"tipo": "agua", "nivel_inicial": 2}])
    assert combate.oculto(nadador) and not combate.oculto(goblin)
    assert combate.alvos_validos(heroi, criar_heroi("guerreiro").habilidades()[0][0]) == [goblin]
    rasa = combate_com([criar_inimigo("rato_nadador")], ambientes=[{"tipo": "agua", "nivel_inicial": 1}])
    assert not rasa.oculto(rasa.inimigos[0])


def test_bote_saindo_da_agua_machuca_mais_e_ele_fica_na_superficie():
    heroi, nadador = criar_heroi("guerreiro"), criar_inimigo("rato_nadador")
    combate = combate_com([nadador, criar_inimigo("goblin")], [heroi], [{"tipo": "agua", "nivel_inicial": 2}])
    agua = combate.ambientes[0]
    assert agua.multiplicador_de_dano(nadador, heroi, "fisico", combate) == 1.5
    vez_de(combate, nadador)
    assert combate.usar_habilidade(nadador, "mordida", heroi)
    assert nadador.tem_status("na_superficie") and not combate.oculto(nadador)
    assert agua.multiplicador_de_dano(nadador, heroi, "fisico", combate) == 1.0
    turno_de(combate, nadador)                                     # o próximo turno dele: ainda na superfície
    assert not combate.oculto(nadador)
    combate.encerrar_turno()                                       # e mergulha de novo
    assert combate.oculto(nadador)


# ---------------- Rato Bombardeiro ----------------

def test_bombardeiro_explode_em_herois_e_ratos_ao_morrer():
    heroi, bombardeiro, bando = criar_heroi("guerreiro"), criar_inimigo("rato_bombardeiro"), criar_inimigo("rato_comum")
    combate = combate_com([bombardeiro, bando], [heroi])
    vida_heroi, vida_bando = heroi.vida, bando.vida
    combate.causar_dano(bombardeiro, 999, heroi)
    assert heroi.vida < vida_heroi and bando.vida < vida_bando
    assert any(e.tipo == "dano" and e.extras.get("motivo") == "explosao" for e in combate.eventos)


def test_pavio_aceso_derruba_o_bombardeiro_e_explode():
    heroi, bombardeiro = criar_heroi("guerreiro"), criar_inimigo("rato_bombardeiro")
    combate = combate_com([bombardeiro, criar_inimigo("goblin")], [heroi])
    bombardeiro.energia = 3
    vez_de(combate, bombardeiro)
    assert combate.usar_habilidade(bombardeiro, "pavio_aceso", heroi)
    assert not bombardeiro.esta_vivo() and bombardeiro in combate.derrotados
    assert any(e.extras.get("motivo") == "explosao" for e in combate.eventos if e.tipo == "dano")


def test_bombardeiro_ferido_acende_o_pavio():
    bombardeiro = criar_inimigo("rato_bombardeiro")
    combate = combate_com([bombardeiro])
    bombardeiro.energia = 3
    assert ia_do(bombardeiro).escolher(bombardeiro, combate).habilidade.chave == "mordida"
    bombardeiro.vida = int(bombardeiro.vida_maxima * 0.4)
    assert ia_do(bombardeiro).escolher(bombardeiro, combate).habilidade.chave == "pavio_aceso"


# ---------------- Rato Alquimista ----------------

def test_alquimista_cura_os_ratos_e_envenena():
    heroi, alquimista, ratazana = criar_heroi("guerreiro"), criar_inimigo("rato_alquimista"), criar_inimigo("ratazana_gigante")
    combate = combate_com([alquimista, ratazana], [heroi])
    ratazana.vida = ratazana.vida_maxima // 2
    antes = ratazana.vida
    alquimista.energia = 2
    vez_de(combate, alquimista)
    assert combate.usar_habilidade(alquimista, "remedio_de_esgoto")
    assert ratazana.vida > antes
    assert any(e.dados["tipo"] == "status" and e.dados["status"] == "veneno"
               for e in criar_inimigo("rato_alquimista").habilidades()[0][0].efeitos)


# ---------------- Rato Xamã ----------------

def test_xama_reergue_um_rato_caido_sem_contar_o_abate_duas_vezes():
    heroi, xama, ratazana = criar_heroi("guerreiro"), criar_inimigo("rato_xama"), criar_inimigo("ratazana_gigante")
    combate = combate_com([xama, ratazana], [heroi])
    combate.causar_dano(ratazana, 999, heroi)
    assert ratazana in combate.derrotados
    xama.energia = 3
    vez_de(combate, xama)
    assert combate.usar_habilidade(xama, "reerguer", ratazana)
    assert ratazana.esta_vivo() and ratazana.vida == round(ratazana.vida_maxima * 0.4)
    assert ratazana not in combate.derrotados and xama.recarga_de("reerguer") == 3
    combate.causar_dano(ratazana, 999, heroi)
    assert combate.derrotados.count(ratazana) == 1


def test_praga_do_xama_seca_os_atributos():
    heroi = criar_heroi("guerreiro")
    combate = combate_com([criar_inimigo("rato_xama")], [heroi])
    antes = {a: heroi.atributo(a) for a in ("forca", "destreza", "inteligencia", "fe")}
    combate.aplicar_status(heroi, "definhando")
    assert all(heroi.atributo(a) == valor - 2 for a, valor in antes.items())


# ---------------- Guarda Real Roedor ----------------

def golpe_simples(heroi):
    return next(h for h, _ in heroi.habilidades() if h.escolhe_alvo() and h.ofensiva() and h.custo == 0)


def alvos_do_ultimo_golpe(combate):
    return [e for e in combate.eventos if e.tipo == "habilidade"][-1].extras["alvos"]


def test_guarda_entra_na_frente_do_rato_ferido_uma_vez_por_rodada():
    heroi, guarda, ratazana = criar_heroi("guerreiro"), criar_inimigo("rato_guarda_real"), criar_inimigo("ratazana_gigante")
    combate = combate_com([guarda, ratazana], [heroi])
    combate.rodada = 1
    vez_de(combate, heroi)
    combate.usar_habilidade(heroi, golpe_simples(heroi), ratazana)
    assert alvos_do_ultimo_golpe(combate) == [ratazana]               # com vida cheia, ninguém protege
    ratazana.vida = ratazana.vida_maxima // 3
    vez_de(combate, heroi)
    combate.usar_habilidade(heroi, golpe_simples(heroi), ratazana)
    assert alvos_do_ultimo_golpe(combate) == [guarda]
    assert any(e.tipo == "protegeu" for e in combate.eventos)
    vez_de(combate, heroi)
    combate.usar_habilidade(heroi, golpe_simples(heroi), ratazana)
    assert alvos_do_ultimo_golpe(combate) == [ratazana]               # só uma vez por rodada


def test_guarda_protege_chefes_mesmo_com_vida_cheia():
    heroi, guarda, chefe = criar_heroi("guerreiro"), criar_inimigo("rato_guarda_real"), criar_inimigo("mercador_mascarado")
    combate = combate_com([guarda, chefe], [heroi])
    combate.rodada = 1
    vez_de(combate, heroi)
    combate.usar_habilidade(heroi, golpe_simples(heroi), chefe)
    assert alvos_do_ultimo_golpe(combate) == [guarda]


# ---------------- Arauto Roedor ----------------

def test_arauto_chama_reforcos_de_verdade_no_2o_turno():
    heroi, arauto = criar_heroi("guerreiro"), criar_inimigo("rato_arauto")
    combate = combate_com([arauto], [heroi])
    assert arauto.status["corneta"].valor == 2
    turno_de(combate, arauto)
    assert arauto.status["corneta"].valor == 1 and len(combate.inimigos) == 1
    combate.encerrar_turno()
    turno_de(combate, arauto)
    novos = combate.inimigos[1:]
    assert len(novos) == 2 and novos[0].chave == "rato_comum" and not any(n.eh_invocacao for n in novos)
    assert all(n.ajustes == arauto.ajustes for n in novos) and not arauto.tem_status("corneta")
    assert sum(1 for e in combate.eventos if e.tipo == "reforco") == 2
    combate.encerrar_turno()
    turno_de(combate, arauto)                                         # uma vez só
    assert len(combate.inimigos) == 3


def test_arauto_atordoado_nao_conta_o_turno_da_corneta():
    heroi, arauto = criar_heroi("guerreiro"), criar_inimigo("rato_arauto")
    combate = combate_com([arauto], [heroi])
    combate.aplicar_status(arauto, "atordoado")
    turno_de(combate, arauto)
    assert arauto.status["corneta"].valor == 2


# ---------------- dados ----------------

def test_ratos_3b_no_reino_com_sprite_e_familia_pestes():
    from roguelike.regioes import regiao
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for chave in NOVOS:
        assert chave in regiao("reino_dos_ratos").inimigos
        assert ficha(chave)["familia"] == "pestes" and criar_inimigo(chave).imune("peste")
        assert sprites.existe(chave)
