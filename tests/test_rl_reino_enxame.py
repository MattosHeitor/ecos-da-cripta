"""Reino dos Ratos, etapa 4B: o Enxame de Ratos das Galerias, um combate em ondas (roguelike/ondas.py) com
"continuar ou fugir" entre as ondas, fôlego, prêmio no fim e a tela entre as ondas."""

import random

import pygame

from roguelike.classes import criar_heroi
from roguelike.encontros import EncontroEvento, GeradorDeEncontros
from roguelike.eventos_run import evento
from roguelike.ondas import CombateEmOndas
from roguelike.run import Run, Recompensa

from test_telas_fluxo import app, comecar, quadros, tecla  # noqa: F401  (fixture e ajudantes)

CHAVE = "enxame_de_ratos_nas_galerias"


def no_enxame(run=None, opcao=0):
    """Run nas Galerias diante do Enxame, já com a opção escolhida."""
    run = run or Run([criar_heroi(c) for c in ("guerreiro", "sacerdote")], "ENXAME", "reino_dos_ratos")
    run.regiao_atual, run.area = "reino_dos_ratos", 1
    run.encontro, run.estado = EncontroEvento(CHAVE), "encontro"
    resultado = run.resolver_evento(opcao)
    return run, resultado


def vencer_a_onda(run):
    combate = run.criar_combate()
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    return run.concluir_combate(combate)


def test_enxame_so_nas_galerias():
    run = Run([criar_heroi("guerreiro")], "ENXAME", "reino_dos_ratos")
    total = run.areas_da_regiao()
    for area, aparece in ((1, True), (total // 2, False), (total - 1, False)):
        run.area = area
        assert (CHAVE in GeradorDeEncontros(run, random.Random(1)).eventos_possiveis()) == aparece


def test_enfrentar_comeca_a_primeira_onda_com_as_outras_ja_sorteadas():
    run, resultado = no_enxame()
    assert isinstance(run.ondas, CombateEmOndas) and run.ondas.total == 3
    assert resultado.combate is run.encontro and run.encontro.eh_combate()
    assert run.encontro.nome == "Enxame de Ratos · Onda 1/3" and run.encontro.estrelas == 2
    assert [o["estrelas"] for o in run.ondas.ondas] == [2, 3, 4]
    assert all(len(o["inimigos"]) == 2 for o in run.ondas.ondas)
    outra, _ = no_enxame()
    assert outra.ondas.ondas == run.ondas.ondas                     # mesma semente, mesmas ondas


def test_vencer_uma_onda_da_folego_e_libera_a_proxima():
    run, _ = no_enxame()
    sem_folego, _ = no_enxame()
    sem_folego.ondas.folego = 0
    assert run.proxima_onda() is None                                # ainda lutando a primeira
    for heroi in run.grupo.herois + sem_folego.grupo.herois:
        heroi.vida = heroi.vida_maxima // 2
    vencer_a_onda(run)
    vencer_a_onda(sem_folego)
    assert run.ondas.vencidas == 1 and not run.ondas.em_luta()
    folego = run.ondas.folego
    assert folego > 0 and all(h.vida == s.vida + int(h.vida_maxima * folego)
                              for h, s in zip(run.grupo.herois, sem_folego.grupo.herois))
    encontro = run.proxima_onda()
    assert encontro is run.encontro and encontro.estrelas == 3 and encontro.nome.endswith("Onda 2/3")
    assert run.ondas.em_luta()


def test_fugir_leva_o_que_ganhou_mas_nao_o_premio():
    run, _ = no_enxame()
    vencer_a_onda(run)
    ouro = run.grupo.ouro
    resultado = run.encerrar_ondas()
    assert run.ondas is None and run.grupo.ouro == ouro
    assert any("correm pelos canos" in t for t in resultado.textos)


def test_vencer_as_tres_da_o_premio_do_ninho():
    run, _ = no_enxame()
    for _ in range(3):
        vencer_a_onda(run)
        run.proxima_onda()
    assert run.ondas.terminou() and run.proxima_onda() is None
    ouro, queijos = run.grupo.ouro, run.quantidade_de("queijo_mofado")
    resultado = run.encerrar_ondas()
    assert run.grupo.ouro == ouro + 40 and run.quantidade_de("queijo_mofado") == queijos + 1
    assert any("(Raro)" in t for t in resultado.textos) and run.ondas is None


def test_onda_com_mais_estrelas_da_mais_xp():
    run, _ = no_enxame()
    run.ondas.ondas = [{"estrelas": 2, "inimigos": ["rato_comum"]}, {"estrelas": 4, "inimigos": ["rato_comum"]}]
    run.encontro = run.ondas.encontro()
    primeira = vencer_a_onda(run).xp
    run.proxima_onda()
    assert vencer_a_onda(run).xp > primeira


def test_as_ondas_nao_vao_no_save_e_somem_na_proxima_area():
    run, _ = no_enxame()
    assert not run.pode_salvar()                       # como todo evento que virou luta: o save antigo vale
    vencer_a_onda(run)
    run.encerrar_ondas()
    run.ondas = CombateEmOndas("x", [{"estrelas": 1, "inimigos": ["rato_comum"]}])
    run.concluir_encontro()
    assert run.ondas is None and run.area == 2


def test_fugir_pelos_canos_e_o_queijo():
    fuga = evento(CHAVE).opcoes[1].consequencias[0]
    assert fuga.dados["tipo"] == "teste" and fuga.dados["atributo"] == "destreza"
    assert {c["tipo"] for c in fuga.dados["falha"]} == {"dano_grupo", "peste"}
    run, _ = no_enxame(opcao=2)                         # sem queijo: não vale
    assert run.ondas is None and run.encontro.tipo == "evento"
    run.grupo.bau.adicionar("queijo_mofado", 1)
    resultado = run.resolver_evento(2)
    assert resultado.combate is None and run.quantidade_de("queijo_mofado") == 0


def test_tela_entre_as_ondas_continua_ou_foge(app):  # noqa: F811
    from telas import fluxo
    run = comecar(app)
    no_enxame(run)
    vencer_a_onda(run)
    fluxo.depois_do_combate(app, run, Recompensa())
    assert type(app.atual).__name__ == "TelaEntreOndas"
    quadros(app)
    tecla(app, pygame.K_1, "1")                        # continuar: a onda 2 começa
    assert type(app.atual).__name__ == "TelaCombate" and run.encontro.estrelas == 3
    vencer_a_onda(run)
    fluxo.depois_do_combate(app, run, Recompensa())
    area = run.area
    tecla(app, pygame.K_3, "3")                        # fugir com o que já ganhou
    assert run.ondas is None
    tecla(app, pygame.K_RETURN, "\r")                  # mostra o texto inteiro
    tecla(app, pygame.K_RETURN, "\r")                  # continuar
    assert run.area == area + 1 and type(app.atual).__name__ != "TelaEntreOndas"
