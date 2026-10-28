"""Reino dos Ratos, etapa 5R1: o Salão do Trono refeito em resolução dobrada, o trono de ratos e ouro (sprite
animado) e a água que segue o terreno (um chão por nível; os lutadores afundam a partir dos próprios pés)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

from roguelike.classes import criar_heroi
from roguelike.encontros import EncontroCombate, MontadorDeCombate
from roguelike.run import Run
from visual.cenario_macabro import CenarioMacabro, PASTA, carregar_camada, catalogo

from test_telas_fluxo import app, quadros  # noqa: F401  (fixture e ajudantes)

SALAO = "salao_do_trono_roedor_0"
ZONAS_COM_AGUA = ("reino_dos_ratos_0", "reino_dos_ratos_2", SALAO)


def pixels(chave, camada):
    sup = pygame.image.load(os.path.join(PASTA, f"{chave}_{camada}.png"))
    return pygame.surfarray.array3d(sup).transpose(1, 0, 2).astype(int), pygame.surfarray.array_alpha(sup).T


def test_salao_em_resolucao_dobrada_e_do_mesmo_tamanho_na_tela():
    pygame.init()
    assert pygame.image.load(os.path.join(PASTA, f"{SALAO}_ceu.png")).get_size() == (704, 360)
    assert carregar_camada(SALAO, "ceu").get_size() == (1408, 720)
    assert carregar_camada("reino_dos_ratos_0", "ceu").get_size() == (1408, 720)       # as de 352x180 seguem 4x


def test_zonas_com_agua_tem_um_chao_para_cada_nivel():
    for chave in ZONAS_COM_AGUA:
        assert catalogo()[chave]["chao_alagado"] == ["chao_agua1", "chao_agua2", "chao_agua3"], chave
        for nome in catalogo()[chave]["chao_alagado"]:
            assert os.path.exists(os.path.join(PASTA, f"{chave}_{nome}.png"))
    assert "chao_alagado" not in catalogo()["reino_dos_ratos_1"]                          # o Mercado é seco


def test_agua_segue_o_terreno():
    """Rasa = poças; Funda = quase todo o chão; Alta = tudo. O estrado do trono fica seco na rasa e só a alta cobre."""
    seco, alfa = pixels(SALAO, "chao")
    chao = alfa > 0
    cobertura = []
    for nivel in (1, 2, 3):
        alagado, _ = pixels(SALAO, f"chao_agua{nivel}")
        cobertura.append((np.abs(alagado - seco).sum(-1) > 12)[chao].mean())
    assert 0.08 < cobertura[0] < cobertura[1] <= cobertura[2] and cobertura[1] > 0.7
    estrado = (232, 300)                                                               # degrau de cima (y, x)
    rasa, _ = pixels(SALAO, "chao_agua1")
    alta, _ = pixels(SALAO, "chao_agua3")
    assert (rasa[estrado] == seco[estrado]).all()
    assert alta[estrado][1] >= alta[estrado][0] and (alta[estrado] != seco[estrado]).any()   # verde de esgoto


def test_cenario_mistura_os_chaos_e_esconde_o_no_da_rainha():
    pygame.init()
    tela = pygame.Surface((1280, 720))
    cenario = CenarioMacabro("salao_do_trono_roedor", 0)
    assert [nome for nome, _, _ in cenario.extras] == ["no_da_rainha"] and len(cenario.chaos) == 4
    for nivel in (0, 0.5, 1.7, 3, 9):
        cenario.alagar(nivel)
        cenario.desenhar(tela)
    assert cenario.agua == 3
    cenario.esconder("no_da_rainha")
    cenario.desenhar(tela)
    assert "no_da_rainha" in cenario.escondidas


def test_trono_de_ratos_e_ouro_no_estrado():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    assert sprites.existe("trono_dos_ratos") and sprites.quadros_de("trono_dos_ratos", "parado") == 6
    trono = catalogo()[SALAO]["trono"]
    assert trono["base"][0] == trono["pes"][0] == trono["assento"][0] == 176
    assert trono["assento"][1] < trono["pes"][1] < trono["base"][1] <= 118


def test_tela_de_combate_troca_o_chao_e_afunda_os_lutadores(app):  # noqa: F811
    from telas.combate.tela import TelaCombate
    run = Run([criar_heroi("guerreiro"), criar_heroi("sacerdote")], "AGUA", "reino_dos_ratos")
    run.area = 1                                                                       # Galerias Fétidas
    tela = TelaCombate(app, run, EncontroCombate("Teste", "", 1, ["rato_comum"]), lambda r: None)
    agua = next(a for a in tela.combate.ambientes if a.tipo == "agua")
    agua.nivel = 3
    app.trocar(tela)
    quadros(app, 90)
    assert tela.cenario.agua > 2.9
    for visual in tela.lado_herois:
        assert tela.ambiente.superficie(visual) == visual.alvo_y - tela.ambiente.altura_agua
    tela.desenhar(app.tela)


def test_salao_desenha_o_trono_e_o_rei_sentado_nele(app):  # noqa: F811
    from telas.combate.tela import TelaCombate
    run = Run([criar_heroi("guerreiro")], "TRONO", "reino_dos_ratos")
    total = run.areas_da_regiao()
    run.area = total
    encontro = MontadorDeCombate(run.regiao, total, run.rng("t"), 4, False, total).chefe()
    tela = TelaCombate(app, run, encontro, lambda r: None)
    assert tela.trono_pes == (640, 404)
    tela.no_trono = {"chave": "rei_dos_ratos"}
    app.trocar(tela)
    quadros(app, 3)
    tela.desenhar(app.tela)
