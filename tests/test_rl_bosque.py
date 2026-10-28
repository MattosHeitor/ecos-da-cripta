"""Fase 4, etapa 2: Bosque Carmesim (medo, enraizar, esporos póstumos, matilha, Mãe-Raiz, consumíveis)."""

import random

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.encontros import MontadorDeCombate
from roguelike.eventos_run import todos_os_eventos
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.regioes import regiao
from roguelike.status import criar_status

from apoio_roguelike import SorteControlado, combate_pronto


def test_amedrontado_tira_dano_e_as_vezes_a_vez():
    medo = criar_status("amedrontado")
    assert medo.modificadores()["dano_causado"] == -0.25
    assert medo.perde_a_vez(SorteControlado(sorteios=[0.1]))
    assert not medo.perde_a_vez(SorteControlado(sorteios=[0.9]))
    heroi = criar_heroi("guerreiro")
    espantalho = criar_inimigo("espantalho_possuido")
    combate = combate_pronto([heroi], [espantalho])
    assert combate.aplicar_status(espantalho, "amedrontado") is None          # imune ao medo
    assert combate.aplicar_status(heroi, "amedrontado") is not None


def test_enraizado_perde_a_vez():
    assert criar_status("enraizado").perde_a_vez(SorteControlado())


def test_fungo_envenena_todos_ao_morrer():
    herois = [criar_heroi("guerreiro"), criar_heroi("mago")]
    fungo = criar_inimigo("fungo_esporento")
    combate = combate_pronto(herois, [fungo, criar_inimigo("goblin")])
    combate.causar_dano(fungo, 999, herois[0])
    assert all(h.tem_status("veneno") for h in herois)


def test_matilha_fica_mais_forte_com_lobos_vivos():
    lobos = [criar_inimigo("lobo_sarnento") for _ in range(3)]
    combate = combate_pronto([criar_heroi("guerreiro")], lobos)
    forte = lobos[0].stat("dano_causado")
    combate.causar_dano(lobos[1], 999, None)
    assert lobos[0].stat("dano_causado") < forte


def test_lobos_chegam_em_matilha():
    bosque = regiao("bosque_carmesim")
    for semente in range(30):
        montador = MontadorDeCombate(bosque, 3, random.Random(semente), 3)
        inimigos = montador.comuns(2)
        if "lobo_sarnento" in inimigos:
            assert inimigos.count("lobo_sarnento") >= 2 and len(inimigos) <= montador.limite
            return
    raise AssertionError("nenhuma matilha sorteada")


def test_espantalho_so_aparece_a_noite():
    bosque = regiao("bosque_carmesim")
    rng = random.Random(3)
    de_dia = {bosque.sortear_inimigo(rng, noite=False) for _ in range(200)}
    a_noite = {bosque.sortear_inimigo(rng, noite=True) for _ in range(200)}
    assert "espantalho_possuido" not in de_dia and "espantalho_possuido" in a_noite


def test_mae_raiz_regenera_com_raizes_e_floresce():
    herois = [criar_heroi("guerreiro"), criar_heroi("sacerdote")]
    mae = criar_inimigo("mae_raiz")
    combate = combate_pronto(herois, [mae])
    raizes = combate.invocacoes_de(mae)
    assert len(raizes) == 1                                                  # começa com uma raiz
    mae.vida = mae.vida_maxima // 3 * 2
    antes = mae.vida
    for passiva in mae.passivas:
        passiva.inicio_do_turno(mae, combate)
    assert mae.vida > antes                                                  # seiva enquanto a raiz vive
    for raiz in combate.invocacoes_de(mae):
        combate.causar_dano(raiz, 999, herois[0])
    combate.causar_dano(mae, 99999, herois[0])                               # para em 50%: floração
    assert mae.esta_vivo() and "florescer_sangrento" in mae.niveis_habilidade
    assert combate.invocacoes_de(mae)                                        # a floração chama outra raiz


def test_cogumelo_da_energia_e_as_vezes_envenena():
    heroi = criar_heroi("guerreiro")
    combate = Combate([heroi], [criar_inimigo("goblin")], SorteControlado(sorteios=[0.05]), ajustar_grupo=False)
    combate.iniciar()
    combate.atual, combate.pode_agir = heroi, True
    energia = heroi.energia
    combate.usar_item(heroi, item("cogumelo_brilhante"), heroi)
    assert heroi.energia == energia + 2 and heroi.tem_status("veneno")


def test_bosque_divide_eventos_com_a_floresta():
    da_floresta = [e for e in todos_os_eventos().values() if e.regioes and "floresta" in e.regioes]
    assert da_floresta and all(e.aparece_em("bosque_carmesim") for e in da_floresta)
    assert not any(e.aparece_em("minas") for e in da_floresta if "minas" not in e.regioes)
