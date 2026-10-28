"""Etapa 8: fases de 10 a 15 áreas (inclusive as finais) e nível de ameaça que cresce com as vitórias."""

import random

from roguelike.classes import criar_heroi
from roguelike.dados import regras
from roguelike.encontros import EncontroCombate
from roguelike.progresso import Progresso
from roguelike.regioes import progressao, todas_as_regioes
from roguelike.run import Run


def test_toda_fase_tem_de_10_a_15_areas_ate_as_finais():
    for chave in todas_as_regioes():
        tamanhos = {progressao().sortear_tamanho(chave, random.Random(s)) for s in range(40)}
        assert min(tamanhos) >= 10 and max(tamanhos) <= 15, (chave, tamanhos)
    finais = [f for ato in progressao().atos if ato.final for f in ato.fases]
    assert finais and all(progressao().sortear_tamanho(f, random.Random(1)) >= 10 for f in finais)


def test_ameaca_sobe_com_as_vitorias_e_tem_maximo(tmp_path):
    progresso = Progresso.carregar(str(tmp_path / "p.json"))
    assert progresso.nivel_de_ameaca() == 0
    progresso.estatisticas["vitorias"] = 3
    assert progresso.nivel_de_ameaca() == 3
    progresso.estatisticas["vitorias"] = 999
    assert progresso.nivel_de_ameaca() == regras()["ameaca"]["maximo"]
    run = progresso.criar_run([criar_heroi("guerreiro")], "AMEACA")
    assert run.ameaca == regras()["ameaca"]["maximo"]


def test_ameaca_fortalece_os_inimigos_e_da_mais_brasas():
    calma = Run([criar_heroi("guerreiro")], "MESMA")
    tensa = Run([criar_heroi("guerreiro")], "MESMA")
    tensa.ameaca = 4
    encontro = EncontroCombate("Teste", "", 1, ["goblin"])
    goblin_calmo = calma.criar_combate(encontro).inimigos[0]
    goblin_tenso = tensa.criar_combate(encontro).inimigos[0]
    assert goblin_tenso.vida_maxima > goblin_calmo.vida_maxima
    for run in (calma, tensa):
        run.estatisticas["areas"] = 20
        run.resultado = "vitoria"
    assert tensa.brasas_ganhas() > calma.brasas_ganhas()


def test_ameaca_vai_no_save():
    run = Run([criar_heroi("guerreiro")], "SALVA")
    run.ameaca = 2
    assert Run.de_dict(run.para_dict()).ameaca == 2
