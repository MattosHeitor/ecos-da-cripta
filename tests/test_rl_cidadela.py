"""Fase 4, etapa 6: Cidadela Congelada (imaterial, escudo de gelo, congelamento em área, itens de calor)."""

from roguelike.classes import criar_heroi
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.regioes import todas_as_regioes

from apoio_roguelike import combate_pronto


def test_cidadela_esta_aberta_e_sempre_de_noite():
    cidadela = todas_as_regioes()["cidadela_congelada"]
    assert cidadela.disponivel and cidadela.chefe == "rainha_de_gelo_eterno"
    assert cidadela.sala_do_chefe == "trono_de_gelo" and cidadela.musica == "cidadela"


def test_lobo_espectral_quase_nao_sente_golpes_fisicos():
    heroi = criar_heroi("guerreiro")
    lobo = criar_inimigo("lobo_espectral_selvagem")
    combate = combate_pronto([heroi], [lobo])
    fisico = combate.causar_dano(lobo, 20, heroi)
    assert 0 < fisico <= 8
    assert combate.causar_dano(lobo, 20, heroi, elemento="fogo") > fisico


def test_sentinela_comeca_revidando():
    assert criar_inimigo("sentinela_de_gelo") is not None
    heroi = criar_heroi("guerreiro")
    sentinela = criar_inimigo("sentinela_de_gelo")
    combate_pronto([heroi], [sentinela])
    assert sentinela.tem_status("contra_ataque")


def test_rainha_congela_o_salao_e_a_capa_protege():
    herois = [criar_heroi("guerreiro"), criar_heroi("mago")]
    herois[1].equipar(item("capa_de_pele_branca"))
    rainha = criar_inimigo("rainha_de_gelo_eterno")
    combate = combate_pronto(herois, [rainha])
    inverno = next(p for p in rainha.passivas if p.dados["tipo"] == "a_cada_n_turnos")
    for _ in range(5):
        inverno.inicio_do_turno(rainha, combate)
    assert herois[0].tem_status("congelado")
    assert not herois[1].tem_status("congelado")


def test_escudo_de_gelo_so_cai_com_fogo():
    heroi = criar_heroi("guerreiro")
    rainha = criar_inimigo("rainha_de_gelo_eterno")
    combate = combate_pronto([heroi], [rainha])
    assert rainha.tem_status("escudo_elemental")
    assert combate.causar_dano(rainha, 20, heroi) < 20
    for _ in range(3):
        combate.causar_dano(rainha, 1, heroi, elemento="fogo")
    assert not rainha.tem_status("escudo_elemental")


def test_hidromel_descongela_e_aquece():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    heroi.vida -= 20
    combate.aplicar_status(heroi, "lento")
    combate.atual, combate.pode_agir = heroi, True
    combate.usar_item(heroi, item("hidromel_quente"), heroi)
    assert not heroi.tem_status("lento") and heroi.tem_status("aquecido")
