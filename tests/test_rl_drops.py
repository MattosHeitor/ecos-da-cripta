"""Etapa 4: materiais-base, peças novas (uma por classe), receitas, sorteio de peças e janela de recompensas."""

import os
import random
from types import SimpleNamespace

import pygame
import pytest

from roguelike.classes import criar_heroi
from roguelike.dados import carregar, regras, sem_comentarios
from roguelike.fabricacao import todas_as_receitas
from roguelike.inimigos import fichas
from roguelike.itens import item, Equipamento
from roguelike.loot import chance_final, materiais_da_fase, multiplicador_de
from roguelike.run import Run, Recompensa

from test_telas_fluxo import app, comecar, quadros, tecla  # noqa: F401  (fixture e ajudantes)

MATERIAIS_BASE = ["linho_velho", "couro_de_lobo", "couro_de_aranha", "madeira_morta", "pena_de_corvo",
                  "sucata_de_ferro", "ferro_de_brasa", "ectoplasma", "cera_benta", "po_de_sombra"]
ITEM_DA_CLASSE = {"guerreiro": "escudo_torre_da_ordem_caida", "ladino": "punhal_da_meia_noite",
                  "mago": "tomo_das_cinzas_vivas", "sacerdote": "turibulo_da_ultima_chama",
                  "barbaro": "machado_uivante_do_degelo", "patrulheira": "arco_de_teixo_sussurrante",
                  "bardo": "alaude_de_cordas_de_prata", "bobo": "mascara_do_riso_eterno",
                  "monge": "faixas_do_mosteiro_esquecido", "feiticeira": "capuz_do_corvo"}
PASTA_ICONES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "itens_macabros")


def test_materiais_base_caem_de_inimigos_e_fases_que_existem():
    loot = carregar("loot")
    origens = set()
    for inimigo, linhas in sem_comentarios(loot["materiais_base"]).items():
        assert inimigo in fichas(), inimigo
        for linha in linhas:
            item(linha["item"])
            origens.add(linha["item"])
    regioes = sem_comentarios(carregar("regioes")["regioes"])
    for regiao in sem_comentarios(loot["materiais_da_fase"]):
        assert regiao in regioes, regiao
        origens |= {d["item"] for d in materiais_da_fase(regiao)}
    assert set(MATERIAIS_BASE) <= origens                     # todo material-base tem de onde cair


def test_cada_classe_tem_uma_peca_com_icone_e_visual_e_receita():
    visuais = sem_comentarios(carregar("visual_equipamentos")["pecas"])
    resultados = {r.resultado for r in todas_as_receitas().values()}
    for classe, chave in ITEM_DA_CLASSE.items():
        objeto = item(chave)
        nome_da_classe = carregar("classes")[classe]["nome"]
        assert isinstance(objeto, Equipamento) and objeto.descricao.startswith(nome_da_classe + ":"), (classe, objeto.descricao)
        assert chave in visuais and os.path.exists(os.path.join(PASTA_ICONES, chave + ".png"))
        assert chave in resultados


def test_a_maioria_das_pecas_novas_e_fabricavel_com_os_materiais_base():
    com_material_base = [r for r in todas_as_receitas().values()
                         if any(m in r.ingredientes for m in MATERIAIS_BASE) and item(r.resultado).tipo == "equipamento"]
    assert len(com_material_base) >= 60


def test_multiplicador_vale_para_materiais_e_consumiveis_mas_nao_para_pecas_nem_garantidos():
    drops = regras()["drops"]
    assert multiplicador_de("linho_velho") == drops["multiplicador_materiais"]
    assert multiplicador_de("pocao_de_vida") == drops["multiplicador_consumiveis"]
    assert chance_final("espada_enferrujada", 0.1) == pytest.approx(0.1)
    assert chance_final("linho_velho", 1.0) == 1.0


def test_sorteio_de_peca_respeita_o_tier_da_fase_e_o_minimo_do_chefe():
    from roguelike.gerador_de_loot import GeradorDeLoot
    run = Run([criar_heroi("guerreiro")], semente="PECAS")
    gerador, herois, rng = GeradorDeLoot(run), run.grupo.herois, random.Random(3)
    pecas = [item(gerador.peca(rng, herois)) for _ in range(300)]
    assert all(1 <= p.tier <= run.regiao.tier for p in pecas)
    assert {"comum", "incomum", "raro"} <= {p.raridade for p in pecas}
    do_chefe = [item(gerador.peca(rng, herois, minima="raro")).raridade for _ in range(100)]
    assert not {"comum", "incomum"} & set(do_chefe)


def test_chefe_sempre_da_peca_e_combate_comum_as_vezes():
    from roguelike.gerador_de_loot import GeradorDeLoot
    run = Run([criar_heroi("guerreiro")], semente="PECAS")
    combate = SimpleNamespace(derrotados=[])

    def pecas(categoria, semente):
        loot = GeradorDeLoot(run).do_combate(combate, SimpleNamespace(tipo=categoria, estrelas=1), random.Random(semente))
        return [c for c in loot["local"] if item(c).tipo == "equipamento"]

    assert all(pecas("chefe", s) for s in range(20))
    vezes = sum(bool(pecas("combate", s)) for s in range(400))
    assert 0 < vezes < 400 * 0.5


def test_janela_de_recompensas_separa_por_tipo_e_raridade():
    from telas.combate.recompensas import PainelDeRecompensas
    recompensa = Recompensa()
    recompensa.itens = {"tunica_de_linho_cru": 1, "machado_uivante_do_degelo": 1, "pocao_de_vida": 2, "linho_velho": 3}
    secoes = PainelDeRecompensas(recompensa).secoes
    assert [o.chave for o, _ in secoes["equipamento"]] == ["machado_uivante_do_degelo", "tunica_de_linho_cru"]
    assert [(o.chave, q) for o, q in secoes["consumivel"]] == [("pocao_de_vida", 2)]
    assert [(o.chave, q) for o, q in secoes["material"]] == [("linho_velho", 3)]


def test_tecla_i_na_vitoria_abre_o_bau_e_depois_segue(app):  # noqa: F811
    from telas import fluxo
    run = comecar(app)
    recompensa = Recompensa()
    recompensa.abrir_bau = True
    fluxo.depois_do_combate(app, run, recompensa)
    tela = app.atual
    assert type(tela).__name__ == "TelaInventario"           # (o loot está na mochila, ao lado do baú)
    quadros(app)
    tecla(app, pygame.K_ESCAPE)
    assert type(app.atual).__name__ != "TelaInventario"
