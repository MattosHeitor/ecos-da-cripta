"""Reino dos Ratos, etapa 7B: os três sets do Reino — Realeza Roedora (mais ouro; ratos que viram contra os outros, mas
Peste permanente), Traje do Médico da Peste (imune à Peste; curas que tiram Peste e veneno) e Guarda Real Roedora
(bloqueio, defesa e o herói que entra na frente do aliado mais ferido)."""

import random

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.sets import todos_os_sets

SETS = {"realeza_roedora": ["coroa_do_rei_dos_ratos", "capa_de_veludo_roido", "cetro_do_rei_dos_ratos", "anel_de_tampinha"],
        "traje_do_medico": ["mascara_de_bico_da_peste", "sobretudo_encerado", "botas_enceradas", "bengala_do_medico"],
        "guarda_real_roedora": ["elmo_de_dedal", "tabardo_da_coroa", "lanca_de_agulha", "escudo_de_tampa_de_lata"]}


def vestir(heroi, pecas):
    for chave in pecas:
        assert heroi.equipar(item(chave))[0], chave
    return heroi


def test_tres_sets_com_as_pecas_e_os_bonus():
    sets = todos_os_sets()
    for chave, pecas in SETS.items():
        assert sets[chave].pecas == pecas
        assert all(item(p).set == chave for p in pecas)
        assert {b.pecas for b in sets[chave].bonus} >= {2, 4}
    assert item("coroa_do_rei_dos_ratos").raridade == "amaldicoado"            # amaldiçoado leve: só a coroa trava
    assert item("mascara_de_bico_da_peste").imune == ["veneno"]                  # a máscara que já existia não mudou


def test_realeza_mais_ouro_ratos_que_viram_e_a_peste_que_nao_sai():
    rei = vestir(criar_heroi("bardo"), SETS["realeza_roedora"][:2])
    assert abs(rei.bonus("ouro_extra") - 0.25) < 1e-9                             # 10% da coroa + 15% do set
    vestir(rei, SETS["realeza_roedora"][2:])
    ratos = [criar_inimigo("ratazana_gigante") for _ in range(12)]
    c = Combate([rei], ratos, random.Random(3))
    c.iniciar()
    encantados = sum(1 for r in ratos if r.tem_status("encantado"))
    assert 0 < encantados < 12 and rei.acumulos_de("peste") == 1
    c2 = Combate([rei], [criar_inimigo("goblin")], random.Random(4))
    rei.peste = 3
    c2.iniciar()
    assert rei.acumulos_de("peste") == 3                                         # não soma: só garante o nível 1


def test_traje_do_medico_imune_e_curas_que_limpam():
    medico = vestir(criar_heroi("medico_da_peste"), SETS["traje_do_medico"][:2])
    assert medico.bonus("resiste_peste") >= 1.0                                  # 2 peças: imune
    c = Combate([medico, criar_heroi("guerreiro")], [criar_inimigo("goblin")], random.Random(5))
    c.iniciar()
    assert all(c.aplicar_status(medico, "peste") is None for _ in range(10))
    vestir(medico, SETS["traje_do_medico"][2:])
    guerreiro = c.herois[1]
    c.aplicar_status(guerreiro, "peste", acumulos=3)
    c.aplicar_status(guerreiro, "veneno", valor=2)
    guerreiro.vida = 5
    c.aplicar_efeitos(medico, golpe("costura_rapida").efeitos, [guerreiro], 1)    # uma cura qualquer
    assert guerreiro.acumulos_de("peste") == 2 and not guerreiro.tem_status("veneno")


def test_guarda_real_entra_na_frente_do_aliado_mais_ferido():
    guarda = vestir(criar_heroi("guerreiro"), SETS["guarda_real_roedora"])
    ferido = criar_heroi("mago")
    orc = criar_inimigo("orc")
    c = Combate([guarda, ferido], [orc], random.Random(6))
    c.iniciar()
    ferido.vida = 3
    assert c.interceptar(orc, golpe("golpe"), ferido) is guarda
    assert c.interceptar(orc, golpe("golpe"), ferido) is ferido                  # uma vez por rodada
