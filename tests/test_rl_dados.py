"""Confere se os arquivos JSON estão coerentes (nomes que apontam para coisas que existem)."""

import json
import os

from roguelike.classes import todas_as_classes
from roguelike.dados import regras
from roguelike.golpes import golpe, todas_as_chaves
from roguelike.inimigos import fichas, fichas_de_invocacao, criar_inimigo
from roguelike.lutador import Heroi

PASTA_SPRITES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sprites_macabros")



def catalogo_de_sprites():
    with open(os.path.join(PASTA_SPRITES, "catalogo.json"), encoding="utf-8") as arquivo:
        return json.load(arquivo)


def test_todas_as_habilidades_carregam_e_descrevem():
    for chave in todas_as_chaves():
        h = golpe(chave)
        assert h.resumo(1) or h.efeitos == [], chave


def test_status_usados_existem():
    for chave in todas_as_chaves():
        for efeito in golpe(chave).efeitos:
            if efeito.dados["tipo"] == "status":
                assert efeito.dados["status"] in regras()["status"], chave


def test_invocacoes_usadas_existem():
    for chave in todas_as_chaves():
        for efeito in golpe(chave).efeitos:
            if efeito.dados["tipo"] == "invocar":
                assert efeito.dados["invocacao"] in fichas_de_invocacao(), chave


def test_classes_apontam_para_habilidades_existentes():
    for classe in todas_as_classes().values():
        nomes = list(classe.habilidades)
        for sub in classe.subclasses.values():
            nomes += sub.golpes
            for esp in sub.especializacoes.values():
                nomes += esp.golpes
        for nome in nomes:
            golpe(nome)


def test_inimigos_validos_e_padrao_usa_habilidades_dele():
    for chave, ficha in fichas().items():
        inimigo = criar_inimigo(chave)
        assert inimigo.vida > 0
        for regra in ficha.get("padrao", []):
            assert regra["habilidade"] in ficha["habilidades"], chave
            # a energia pedida pela regra precisa pagar a habilidade
            assert regra["energia"] >= golpe(regra["habilidade"]).custo, (chave, regra)
        for status in ficha.get("imune", []):
            assert status in regras()["status"], chave


def test_cada_inimigo_tem_sprite():
    catalogo = catalogo_de_sprites()
    for chave, ficha in list(fichas().items()) + list(fichas_de_invocacao().items()):
        sprite = ficha.get("sprite", chave)
        assert sprite in catalogo, sprite
        if chave in catalogo and "familia" in ficha:      # invocações não têm família
            assert catalogo[chave]["familia"] == ficha["familia"], chave


def test_sprites_dos_herois_existem():
    catalogo = catalogo_de_sprites()
    for classe in todas_as_classes().values():
        for sprite in classe.aparencias.values():
            assert sprite in catalogo, sprite


def test_npcs_tem_sprite_e_falas():
    from roguelike.dados import carregar
    catalogo = catalogo_de_sprites()
    for tipo, ficha in carregar("npcs").items():
        if tipo.startswith("_"):
            continue
        assert ficha["sprite"] in catalogo, tipo
        assert ficha["falas"], tipo
    # os do acampamento e o baú também existem
    for sprite in ("taverneiro", "capita", "bau"):
        assert sprite in catalogo, sprite


def test_heroi_e_inimigo_sao_lutadores():
    # Herança: tudo o que luta é um Lutador
    from roguelike.lutador import Lutador
    from roguelike.classes import criar_heroi
    assert isinstance(criar_heroi("bardo"), Heroi)
    assert isinstance(criar_heroi("bardo"), Lutador)
    assert isinstance(criar_inimigo("goblin"), Lutador)


def test_todo_item_tem_icone_da_forja():
    """Cada item precisa de assets/itens_macabros/<chave>.png (rode ferramentas/sprites_macabros/gerar_itens.py)."""
    from roguelike.itens import todos_os_itens
    pasta = os.path.join(os.path.dirname(PASTA_SPRITES), "itens_macabros")
    faltando = [chave for chave in todos_os_itens() if not os.path.exists(os.path.join(pasta, chave + ".png"))]
    assert not faltando, f"Sem ícone forjado: {faltando}"


def test_icone_do_item_usa_a_forja_com_ampliacao_inteira():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    from roguelike.itens import item
    from ui.icones import icone_item
    for vezes, lado in ((2, 20), (3, 40), (4, 40), (5, 60)):
        assert icone_item(item("pocao_de_vida"), vezes).get_size() == (lado, lado)
