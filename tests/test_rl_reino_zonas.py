"""Reino dos Ratos, etapa 2A: as zonas (cenário, nome e música), a sala do trono e as partículas novas."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from audio import MUSICAS, PASTA_MUSICA, EXTENSOES_MUSICA, procurar
from roguelike.classes import criar_heroi
from roguelike.regioes import regiao, todas_as_regioes
from roguelike.run import Run
from visual.cenario_macabro import CenarioMacabro, catalogo, cena_da_area
from visual.particulas import TIPOS

ZONAS = ["Galerias Fétidas", "Mercado Roedor", "Catedral Roída"]


def test_as_zonas_se_sucedem_ao_longo_da_fase_e_o_chefe_tem_o_salao():
    reino = regiao("reino_dos_ratos")
    for total in (10, 12, 15):
        nomes = [reino.zona(area, total)["nome"] for area in range(1, total)]
        assert nomes[0] == ZONAS[0] and nomes[-1] == ZONAS[2] and ZONAS[1] in nomes, total
        assert nomes == sorted(nomes, key=ZONAS.index)                     # sempre na ordem, sem voltar
        assert reino.zona(total, total)["nome"] == "Salão do Trono"
        assert reino.musica_da_area(total, total) == "reino_trono"


def test_cada_zona_tem_cenario_proprio_e_musica_que_existe():
    reino = regiao("reino_dos_ratos")
    for area, nome in ((1, "reino_dos_ratos"), (12, "salao_do_trono_roedor")):
        cena, _ = cena_da_area("reino_dos_ratos", area, "chefe" if area == 12 else None, total=12)
        assert cena == nome
    for variante in (0, 1, 2):
        assert f"reino_dos_ratos_{variante}" in catalogo()
    for zona in reino.zonas + [reino.zona_do_chefe]:
        assert zona["musica"] in MUSICAS and procurar(PASTA_MUSICA, zona["musica"], EXTENSOES_MUSICA), zona


def test_fases_sem_zonas_continuam_com_a_mesma_musica():
    for chave, fase in todas_as_regioes().items():
        if not fase.zonas:
            assert all(fase.musica_da_area(area, 12) == fase.musica for area in range(1, 13)), chave
            assert fase.zona(3, 12) is None


def test_a_run_sabe_a_zona_e_a_musica_da_area():
    run = Run([criar_heroi("guerreiro")], "ZONAS", "reino_dos_ratos")
    total = run.areas_da_regiao()
    assert run.zona()["nome"] == ZONAS[0] and run.musica() == "reino_galerias"
    run.area = total
    assert run.zona()["nome"] == "Salão do Trono" and run.musica() == "reino_trono"
    floresta = Run([criar_heroi("guerreiro")], "ZONAS", "floresta")
    assert floresta.zona() is None and floresta.musica() == "floresta"


def test_salao_do_trono_guarda_o_lugar_do_rei_no_meio_do_cenario():
    """O Rei, ao sair da luta, senta no trono como parte do cenário (etapa 5): o assento fica no centro e acima
    do chão da luta, longe das barras de vida e da fila de turnos."""
    trono = catalogo()["salao_do_trono_roedor_0"]["trono"]
    (x, y), (pes_x, pes_y) = trono["assento"], trono["pes"]
    assert 160 <= x <= 192 and x == pes_x                     # 352 px de largura: o centro é 176
    assert 60 <= y < pes_y <= 118                             # 118 = onde começa o chão (HORIZONTE)


def test_particulas_do_reino_animam_e_desenham():
    pygame.init()
    tela = pygame.Surface((1280, 720))
    for tipo in ("gota_verde", "vapor", "mosca", "olhos"):
        grupo = TIPOS[tipo](12, 1280, 720, 532)
        for _ in range(20):
            grupo.atualizar(0.1)
        grupo.desenhar(tela)
    for chave in ("reino_dos_ratos_0", "reino_dos_ratos_1", "reino_dos_ratos_2", "salao_do_trono_roedor_0"):
        cenario = CenarioMacabro(*chave.rsplit("_", 1)[0:1], int(chave.rsplit("_", 1)[1]))
        assert {"olhos", "mosca"} & {tipo for tipo, _ in cenario.config["particulas"]}, chave
        cenario.atualizar(0.5)
        cenario.desenhar(tela)
        cenario.desenhar_frente(tela)
