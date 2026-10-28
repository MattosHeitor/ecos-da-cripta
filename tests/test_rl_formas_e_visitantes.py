"""Dragão do Eclipse (3ª forma do Bispo, com barra própria e página no bestiário) e inimigos visitantes
(ajuste de força pelo tier da fase)."""

from roguelike.bestiario import secoes
from roguelike.combate import Combate
from roguelike.classes import criar_heroi
from roguelike.dados import carregar, sem_comentarios
from roguelike.inimigos import ajuste_de_tier, criar_inimigo, fichas


def test_bispo_vira_dragao_com_barra_nova_e_conta_o_abate_dos_dois():
    heroi = criar_heroi("guerreiro")
    bispo = criar_inimigo("bispo_eclipsado")
    combate = Combate([heroi], [bispo])
    combate.iniciar()
    while bispo.esta_vivo() and bispo.sprite != "dragao_do_eclipse":
        combate.causar_dano(bispo, 10, heroi)
    assert bispo.nome == "Dragão do Eclipse" and bispo.vida == bispo.vida_maxima
    assert bispo.formas == ["dragao_do_eclipse"]


def test_dragao_tem_pagina_na_catedral_do_eclipse_depois_do_bispo():
    lista = dict((chave, inimigos) for chave, _, inimigos in secoes())["catedral_do_eclipse"]
    assert lista.index("dragao_do_eclipse") == lista.index("bispo_eclipsado") + 1


def test_visitante_ganha_a_forca_media_da_fase():
    goblin = fichas()["goblin"]                         # tier 1
    assert ajuste_de_tier(goblin, 1) == {}
    ajuste = ajuste_de_tier(goblin, 2)
    assert ajuste["vida_percentual"] > 0.5 and ajuste["dano_causado"] > 0
    esqueleto = fichas()["esqueleto"]                   # tier 3 nas Minas de Brasa (tier 2): fica mais fraco
    assert ajuste_de_tier(esqueleto, 2)["dano_causado"] < 0


def test_inimigos_das_fases_existem():
    for chave, regiao in sem_comentarios(carregar("regioes")["regioes"]).items():
        for campo in ("inimigos", "elites", "mini_chefes", "formas_do_chefe"):
            for inimigo in regiao.get(campo, []):
                assert inimigo in fichas(), (chave, inimigo)
        for inimigo in regiao.get("pesos", {}):
            assert inimigo in regiao["inimigos"], (chave, inimigo)
