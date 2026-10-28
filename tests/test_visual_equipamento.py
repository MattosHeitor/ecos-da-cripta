"""Equipamento visível no herói (só visual): toda peça aparece, em toda geometria, na ordem certa."""

import json
import os

import pygame

from roguelike.classes import criar_heroi
from roguelike.itens import item, todos_os_itens, Equipamento
from roguelike.visual_equipamento import camadas_da_peca, visual_da_peca

CATALOGO = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites_macabros", "catalogo.json")


def catalogo():
    return json.load(open(CATALOGO, encoding="utf-8"))


def test_toda_peca_tem_visual_e_camada_em_toda_geometria():
    cat = catalogo()
    geometrias = {m["geometria"] for m in cat.values() if m.get("familia") == "camadas"}
    for peca in todos_os_itens().values():
        if not isinstance(peca, Equipamento):
            continue
        assert visual_da_peca(peca) is not None, peca.chave
        for espaco in peca.espacos_possiveis():
            for token in camadas_da_peca(peca, espaco):
                nome = token.partition(":")[0]
                for g in geometrias:
                    assert f"camada_{g}_{nome}" in cat, (peca.chave, g, nome)


def test_arma_equipada_desarma_a_roupa_e_capa_vai_atras():
    heroi = criar_heroi("guerreiro")
    assert "_desarmado" not in heroi.sprite
    heroi.equipar(item("machado_orc"))
    heroi.equipar(item("capa_de_la"))
    base, *camadas = heroi.sprite.split("+")
    assert base.endswith("_desarmado")
    assert any(c.startswith("@eq_machado:") for c in camadas) and any(c.startswith("@eq_capa:") for c in camadas)
    cat = catalogo()
    assert cat["camada_guerreiro_eq_capa"].get("atras") and not cat["camada_guerreiro_eq_capa_gola"].get("atras")


def test_placas_do_juramento_vao_no_peitoral():
    """Etapa 6: o espaço "armadura" não existe mais; as Placas equipam e aparecem no herói."""
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("placas_do_juramento"))
    assert heroi.equipamento["peitoral"].chave == "placas_do_juramento"
    assert "+@eq_placas:" in heroi.sprite
    assert not [p.chave for p in todos_os_itens().values() if isinstance(p, Equipamento) and "armadura" in p.espacos_possiveis()]


def test_skin_de_chapeu_esconde_a_peca_de_cabeca():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("elmo_de_ferro"))
    assert "+@eq_elmo:" in heroi.sprite
    heroi.vestir({"chapeu": "aureola"})
    assert "+@eq_elmo:" not in heroi.sprite


def test_camada_tingida_e_composta_no_jogo():
    pygame.init()
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("elmo_de_ferro"))
    vermelho = heroi.sprite.replace(heroi.sprite.split(":")[-1][:6], "c02020")
    a = sprites.quadro(heroi.sprite, "parado", 0, 1)
    b = sprites.quadro(vermelho, "parado", 0, 1)
    assert a.get_size() == b.get_size()
    assert pygame.image.tostring(a, "RGBA") != pygame.image.tostring(b, "RGBA")       # a cor muda o elmo
    assert sprites.existe("monge_desarmado+@eq_espada:808080")                        # sem folha desarmada: a normal
