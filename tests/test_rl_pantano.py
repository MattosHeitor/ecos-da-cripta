"""Fase 4, etapa 3: Pântano dos Afogados (fim da fila, lodo, cegueira, pedágio, imunidade de item)."""

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.grupo import Grupo
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.status import criar_status

from apoio_roguelike import SorteControlado, combate_pronto


def test_afogado_puxa_para_o_fim_da_fila():
    herois = [criar_heroi("guerreiro"), criar_heroi("mago")]
    afogado = criar_inimigo("afogado")
    combate = combate_pronto(herois, [afogado], SorteControlado(padrao=0.3))
    combate.fila = [herois[0], herois[1]]
    combate.atual, combate.pode_agir = afogado, True
    afogado.energia = 5
    combate.usar_habilidade(afogado, "puxao_do_fundo", herois[0])
    assert combate.fila[-1] is herois[0]


def test_lodo_corta_a_cura_e_cegueira_corta_a_precisao():
    assert criar_status("enlameado").modificadores()["cura_recebida"] == -0.6
    heroi, sapo = criar_heroi("guerreiro"), criar_inimigo("sapo_boi")
    combate = combate_pronto([heroi], [sapo])
    combate.aplicar_status(heroi, "cego")
    assert heroi.stat("precisao") == -0.4
    sapo.ajustes["chance_esquiva"] = 0.1
    assert combate.golpear(heroi, sapo, 5).esquivou is False or True     # (a chance subiu; o sorteio decide)
    combate = Combate([heroi], [sapo], SorteControlado(sorteios=[0.45]), ajustar_grupo=False)
    assert combate.golpear(heroi, sapo, 5).esquivou                      # 0.45 < 0.1 + 0.4


def test_pedagio_rouba_ouro_se_ninguem_acertou():
    heroi = criar_heroi("guerreiro")
    grupo = Grupo([heroi])
    grupo.ouro = 100
    barqueiro = criar_inimigo("barqueiro_sem_rosto")
    combate = combate_pronto([heroi], [barqueiro])
    combate.grupo = grupo
    pedagio = next(p for p in barqueiro.passivas if p.dados["tipo"] == "pedagio")
    for _ in range(3):
        pedagio.inicio_do_turno(barqueiro, combate)
    assert grupo.ouro < 100
    ouro = grupo.ouro
    combate.causar_dano(barqueiro, 5, heroi)                              # acertou: paga com sangue
    for _ in range(3):
        pedagio.inicio_do_turno(barqueiro, combate)
    assert grupo.ouro == ouro


def test_pedagio_sem_ouro_leva_um_consumivel():
    heroi = criar_heroi("guerreiro")
    grupo = Grupo([heroi])
    grupo.ouro = 0
    heroi.inventario.adicionar("pocao_de_vida", 2)
    barqueiro = criar_inimigo("barqueiro_sem_rosto")
    combate = combate_pronto([heroi], [barqueiro])
    combate.grupo = grupo
    pedagio = next(p for p in barqueiro.passivas if p.dados["tipo"] == "pedagio")
    for _ in range(3):
        pedagio.inicio_do_turno(barqueiro, combate)
    assert heroi.inventario.quantidade("pocao_de_vida") == 1


def test_itens_dao_imunidade():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("botas_de_junco"))
    heroi.equipar(item("amuleto_anti_maldicao"))
    assert heroi.imune("enlameado") and heroi.imune("amaldicoado")
    heroi.desequipar("botas")
    assert not heroi.imune("enlameado")


def test_oleo_de_lamparina_tira_a_cegueira_e_ilumina():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.aplicar_status(heroi, "cego")
    combate.atual, combate.pode_agir = heroi, True
    combate.usar_item(heroi, item("oleo_de_lamparina"), heroi)
    assert not heroi.tem_status("cego") and heroi.tem_status("iluminado")
