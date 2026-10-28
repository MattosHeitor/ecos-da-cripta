"""Inimigos que nasceram das demonstrações das forjas e a Árvore Faminta da Mãe-Raiz."""

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.inimigos import criar_inimigo

NOVOS = ("lobo_carnical", "besouro_chifrudo", "corvo_carniceiro", "cogumelo_pustulento", "penitente_deformado",
         "carnical_esqueletico")


def test_mae_raiz_chama_a_arvore_faminta_ao_florescer_sem_perder_a_raiz():
    heroi = criar_heroi("guerreiro")
    mae = criar_inimigo("mae_raiz")
    combate = Combate([heroi], [mae])
    combate.iniciar()
    assert [i.chave for i in combate.invocacoes_de(mae)] == ["raiz_sanguinea"]
    while mae.fracao_vida() > 0.5:
        combate.causar_dano(mae, 5, heroi)
    assert sorted(i.chave for i in combate.invocacoes_de(mae)) == ["arvore_faminta", "raiz_sanguinea"]


def test_versoes_novas_lutam_e_morrem_sem_erro():
    for chave in NOVOS:
        heroi = criar_heroi("guerreiro")
        inimigo = criar_inimigo(chave)
        combate = Combate([heroi], [inimigo])
        combate.iniciar()
        while inimigo.esta_vivo():
            combate.causar_dano(inimigo, 7, heroi)
        combate.verificar_fim()
        assert inimigo in combate.derrotados, chave
