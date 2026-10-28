"""Reino dos Ratos, etapa 5A: o Rei dos Ratos (Édito Real, Imposto Real, Corte Real, Banquete com o Queijo Real e a
Fúria) e o Queijo Real, um objeto que não age nem conta para vencer."""

import random

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.encontros import EncontroCombate, MontadorDeCombate
from roguelike.golpes import golpe
from roguelike.grupo import Grupo
from roguelike.ia import ia_do, IA
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.regioes import regiao
from roguelike.run import Run


def luta(classes=("guerreiro", "sacerdote", "mago"), com_queijo=True, ouro=100):
    herois = [criar_heroi(c) for c in classes]
    inimigos = [criar_inimigo("rei_dos_ratos")] + ([criar_inimigo("queijo_real")] if com_queijo else [])
    combate = Combate(herois, inimigos, random.Random(1))
    combate.grupo = Grupo(herois)
    combate.grupo.ouro = ouro
    combate.iniciar()
    return combate, combate.inimigos[0], herois


def proclamar(combate, rei, chave):
    combate.aplicar_status(rei, chave, 2, origem=rei)


def vez_de(combate, lutador):
    combate.atual, combate.pode_agir = lutador, True


# ---------------- chefe do Reino e o Queijo Real ----------------

def test_rei_e_o_chefe_do_reino_e_vem_com_o_queijo():
    reino = regiao("reino_dos_ratos")
    assert reino.chefe == "rei_dos_ratos"
    encontro = MontadorDeCombate(reino, 6, random.Random(1), 3, False, 6).chefe()
    assert encontro.tipo == "chefe" and encontro.inimigos == ["rei_dos_ratos", "queijo_real"]
    run = Run([criar_heroi("guerreiro")], "REI", "reino_dos_ratos")
    run.ajustes_do_chefe = {"vida_percentual": -0.2}                # roubaram o queijo do altar
    combate = run.criar_combate(encontro)
    rei, queijo = combate.inimigos
    assert rei.ajustes["vida_percentual"] < queijo.ajustes["vida_percentual"]


def test_queijo_nao_age_nao_conta_abate_e_nao_segura_a_luta():
    combate, rei, herois = luta()
    queijo = combate.inimigos[1]
    combate.nova_rodada()
    assert queijo not in combate.fila and rei in combate.fila
    assert queijo.abates() == 0
    for _ in range(2):                                  # (a Fúria segura um golpe só no limiar de 50%)
        combate.causar_dano(rei, 99999, herois[0])
    combate.verificar_fim()
    assert combate.resultado == "vitoria" and queijo.esta_vivo()


# ---------------- Édito Real ----------------

def test_edito_sorteia_uma_lei_por_vez_e_nunca_repete_a_ultima():
    combate, rei, _ = luta()
    efeito = golpe("edito_real").efeitos[0]
    vistas = []
    for _ in range(8):
        efeito.aplicar(combate, rei, [rei], 1, None)
        editos = [c for c in rei.status if c.startswith("edito_")]
        assert len(editos) == 1
        vistas.append(editos[0])
    assert all(a != b for a, b in zip(vistas, vistas[1:]))
    assert rei.status[vistas[-1]].duracao == 2


def test_cada_edito_proibe_o_que_diz():
    combate, rei, (guerreiro, sacerdote, mago) = luta()
    proclamar(combate, rei, "edito_sem_cura")
    assert combate.proibicao(sacerdote, "habilidade", golpe("cura_sagrada"), [guerreiro])
    assert combate.proibicao(guerreiro, "item", item("pocao_de_vida"), [guerreiro])
    assert not combate.proibicao(guerreiro, "habilidade", golpe("golpe"), [rei])
    combate.remover_status(rei, "edito_sem_cura")
    proclamar(combate, rei, "edito_sem_magia")
    assert combate.proibicao(mago, "habilidade", golpe("bola_de_fogo"), [rei])
    assert not combate.proibicao(guerreiro, "habilidade", golpe("golpe"), [rei])
    combate.remover_status(rei, "edito_sem_magia")
    proclamar(combate, rei, "edito_sem_atacar")
    queijo = combate.inimigos[1]
    assert combate.proibicao(guerreiro, "habilidade", golpe("golpe"), [rei])
    assert combate.proibicao(guerreiro, "habilidade", golpe("redemoinho"), [rei, queijo])     # área também conta
    assert not combate.proibicao(guerreiro, "habilidade", golpe("golpe"), [queijo])
    combate.remover_status(rei, "edito_sem_atacar")
    proclamar(combate, rei, "edito_ajoelhem_se")
    assert combate.proibicao(guerreiro, "habilidade", golpe("golpe"), [queijo])
    assert not combate.proibicao(guerreiro, "concentrar", None, [])


def test_desobedecer_custa_um_quarto_da_vida_e_obedecer_nao_custa_nada():
    combate, rei, (guerreiro, _, _) = luta()
    queijo = combate.inimigos[1]
    proclamar(combate, rei, "edito_sem_atacar")
    guerreiro.energia = 10
    vez_de(combate, guerreiro)
    antes = guerreiro.vida
    assert combate.usar_habilidade(guerreiro, "golpe", queijo)
    assert guerreiro.vida == antes
    vez_de(combate, guerreiro)
    assert combate.usar_habilidade(guerreiro, "golpe", rei)
    castigo = round(guerreiro.vida_maxima * 0.25)
    assert guerreiro.vida <= antes - castigo
    assert any(e.tipo == "desobedeceu" and e.alvo is guerreiro for e in combate.eventos)


def test_herois_automaticos_obedecem_os_editos():
    combate, rei, (guerreiro, sacerdote, mago) = luta()
    proclamar(combate, rei, "edito_sem_magia")
    for _ in range(10):
        mago.energia = 10
        escolha = ia_do(mago).escolher(mago, combate)
        assert escolha.habilidade is None or not IA.desobedece(mago, combate, escolha.habilidade)
    combate.remover_status(rei, "edito_sem_magia")
    proclamar(combate, rei, "edito_sem_atacar")
    guerreiro.energia = 0
    assert all(ia_do(guerreiro).escolher_alvo(guerreiro, combate, golpe("golpe")) is not rei for _ in range(10))


# ---------------- Imposto, Corte, Banquete e Fúria ----------------

def test_imposto_leva_ouro_engorda_o_cofre_e_volta_em_dobro():
    combate, rei, (guerreiro, _, _) = luta(ouro=200)
    rei.retirada_feita = True                           # o Rei que já voltou do trono (5B) cai de verdade
    defesa = rei.stat("defesa")
    for _ in range(4):
        rei.energia = 10
        vez_de(combate, rei)
        combate.usar_habilidade(rei, "imposto_real", guerreiro)
    roubado = rei.ouro_roubado
    assert roubado > 0 and combate.grupo.ouro == 200 - roubado
    assert rei.acumulos_de("cofre_real") == 2 and rei.stat("defesa") == defesa + 2
    for _ in range(2):
        combate.causar_dano(rei, 99999, guerreiro)
    assert combate.grupo.ouro == 200 + roubado


def test_corte_real_chama_no_maximo_dois_na_luta():
    combate, rei, _ = luta()
    for _ in range(4):
        rei.energia, rei.recargas = 10, {}
        vez_de(combate, rei)
        combate.usar_habilidade(rei, "corte_real")
    chegaram = [i for i in combate.inimigos if i.chave in ("rato_guarda_real", "rato_comum")]
    assert len(chegaram) == 2


def test_banquete_so_com_o_queijo_vivo_e_a_vida_baixa():
    combate, rei, herois = luta()
    rei.energia = 0
    assert ia_do(rei).escolher(rei, combate).habilidade.chave != "banquete_real"
    rei.vida = round(rei.vida_maxima * 0.3)
    assert ia_do(rei).escolher(rei, combate).habilidade.chave == "banquete_real"
    vida = rei.vida
    vez_de(combate, rei)
    combate.usar_habilidade(rei, "banquete_real")
    assert rei.vida > vida and all(i.chave != "queijo_real" for i in combate.inimigos)
    sem_queijo, rei2, _ = luta(com_queijo=False)
    rei2.vida, rei2.energia = round(rei2.vida_maxima * 0.3), 0
    assert ia_do(rei2).escolher(rei2, sem_queijo).habilidade.chave != "banquete_real"


def test_furia_abaixo_da_metade():
    combate, rei, herois = luta()
    dano = rei.stat("dano_causado")
    combate.causar_dano(rei, round(rei.vida_maxima * 0.6), herois[0])
    assert rei.stat("dano_causado") > dano
    assert any(e.tipo == "fase_do_chefe" for e in combate.eventos)


def test_sprites_do_rei_e_do_queijo():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for linha in ("decreto", "banquete", "sentado"):
        assert sprites.tem_animacao("rei_dos_ratos", linha)
    assert sprites.quadros_de("rei_dos_ratos", "parado") == 8
    assert sprites.existe("queijo_real")
