"""Testes de atributos, valores calculados e status."""

import pytest

from roguelike.atributos import Atributos, valor_derivado, sigla
from roguelike.classes import criar_heroi
from roguelike.inimigos import criar_inimigo
from roguelike.status import criar_status

from apoio_roguelike import combate_pronto, vez_de


# ---------------- atributos ----------------

def test_atributo_desconhecido_da_erro():
    with pytest.raises(ValueError):
        Atributos({"magia": 3})


def test_formula_do_critico_soma_os_pesos():
    valores = {"forca": 10, "destreza": 0, "constituicao": 0, "inteligencia": 0, "fe": 0, "sorte": 10, "carisma": 0}
    # 0.05 + 10 x 0.002 + 10 x 0.008
    assert valor_derivado("chance_critico", valores.get) == pytest.approx(0.15)


def test_valor_derivado_respeita_o_limite_maximo():
    valores = {nome: 0 for nome in ["forca", "destreza", "constituicao", "inteligencia", "fe", "sorte", "carisma"]}
    valores["sorte"] = 1000
    assert valor_derivado("chance_critico", valores.get) == 0.75


def test_sigla_dos_atributos():
    assert sigla("forca") == "FOR"
    assert sigla("fe") == "FÉ"


def test_constituicao_aumenta_a_vida_maxima():
    heroi = criar_heroi("guerreiro")
    antes = heroi.vida_maxima
    heroi.pontos_atributo = 2
    heroi.distribuir_ponto("constituicao")
    heroi.distribuir_ponto("constituicao")
    assert heroi.vida_maxima == antes + 2
    assert heroi.vida == heroi.vida_maxima


def test_destreza_da_iniciativa_a_cada_20_pontos():
    heroi = criar_heroi("guerreiro")
    minimo, maximo = heroi.faixa_de_iniciativa()
    heroi.atributos.aumentar("destreza", 20)
    assert heroi.faixa_de_iniciativa() == (minimo + 1, maximo + 1)


def test_status_soma_bonus_no_valor_final():
    heroi = criar_heroi("guerreiro")
    antes = heroi.stat("dano_causado")
    heroi.status["fortalecido"] = criar_status("fortalecido")
    assert heroi.stat("dano_causado") == pytest.approx(antes + 0.25)


# ---------------- status no combate ----------------

def test_veneno_causa_dano_no_inicio_do_turno():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.aplicar_status(heroi, "veneno", duracao=2, valor=3)
    vida = heroi.vida
    vez_de(combate, heroi)
    assert heroi.vida == vida - 3


def test_sangramento_acumula_e_o_dano_e_igual_aos_acumulos():
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([criar_heroi("guerreiro")], [goblin])
    combate.aplicar_status(goblin, "sangramento", acumulos=2)
    combate.aplicar_status(goblin, "sangramento", acumulos=3)
    assert goblin.acumulos_de("sangramento") == 5
    vida = goblin.vida
    vez_de(combate, goblin)
    assert goblin.vida == vida - 5


def test_escudo_absorve_o_dano_e_some_quando_quebra():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.aplicar_status(heroi, "escudo", valor=5)
    vida = heroi.vida
    combate.causar_dano(heroi, 8, None)
    assert heroi.vida == vida - 3
    assert not heroi.tem_status("escudo")


def test_atordoado_perde_a_vez():
    goblin = criar_inimigo("goblin")
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [goblin])
    combate.aplicar_status(goblin, "atordoado")
    for _ in range(4):
        atual = combate.comecar_turno()
        if atual is goblin:
            assert not combate.pode_agir
            break
        combate.concentrar(atual)
    assert not goblin.tem_status("atordoado")


def test_imune_resiste_ao_status():
    esqueleto = criar_inimigo("esqueleto")
    combate = combate_pronto([criar_heroi("guerreiro")], [esqueleto])
    assert combate.aplicar_status(esqueleto, "veneno", valor=3) is None
    assert not esqueleto.tem_status("veneno")


def test_buff_em_si_dura_ate_o_proximo_turno():
    heroi = criar_heroi("ladino")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, heroi)
    heroi.energia = 5
    assert combate.usar_habilidade(heroi, "bomba_de_fumaca")
    # Furtivo de 1 turno continua valendo durante o turno dos inimigos
    assert heroi.tem_status("furtivo")
    vez_de(combate, heroi)
    combate.concentrar(heroi)
    assert not heroi.tem_status("furtivo")


def test_purificar_remove_so_os_negativos():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.aplicar_status(heroi, "veneno", valor=2)
    combate.aplicar_status(heroi, "fortalecido")
    combate.purificar(heroi)
    assert not heroi.tem_status("veneno")
    assert heroi.tem_status("fortalecido")
