"""Efeitos visuais próprios dos golpes (dados/efeitos_golpes.json): só visual, mas não pode quebrar."""

import pygame

import efeitos_de_golpe as G
from roguelike.dados import carregar, sem_comentarios
from roguelike.golpes import todas_as_chaves


def configs():
    return sem_comentarios(carregar("efeitos_golpes"))


def test_todo_golpe_do_json_existe_e_usa_tipos_e_paletas_validos():
    golpes = set(todas_as_chaves())
    for chave, config in configs().items():
        assert chave in golpes, chave
        for parte in G.partes_do_golpe(config):
            assert parte["tipo"] in G.ESPERA, (chave, parte["tipo"])
            cores = parte.get("cores", config.get("cores"))
            assert cores is None or isinstance(cores, list) or cores in G.PALETAS, (chave, cores)


def test_efeitos_rodam_ate_o_fim_sem_erro():
    tela = pygame.Surface((1280, 720))
    for chave, config in configs().items():
        lista = G.efeitos_do_golpe(config, (300, 400), [(900, 420), (1000, 430)], 532, atraso=0.1)
        assert lista, chave
        for _ in range(120):                                       # 2 segundos a 60 quadros
            for efeito in lista:
                efeito.atualizar(1 / 60)
                efeito.desenhar(tela)
        assert all(efeito.terminou() for efeito in lista), chave
        assert 0 < G.espera_do_golpe(config) < 1.5
