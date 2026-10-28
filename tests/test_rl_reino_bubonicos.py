"""Reino dos Ratos, etapa 3C1: humanos bubônicos (Homem, Mendigo, Carrasco, Freira Roída) e os inimigos por zona."""

import random
from types import SimpleNamespace

from roguelike.ambiente import criar_ambientes
from roguelike.classes import criar_heroi
from roguelike.combate import Combate, ResultadoGolpe
from roguelike.efeitos_habilidade import Contexto
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo, ficha
from roguelike.regioes import regiao

NOVOS = ("homem_bubonico", "mendigo_bubonico", "carrasco_bubonico", "freira_roida")


def combate_com(inimigos, herois=None, ambientes=None, semente=1, ouro=None):
    combate = Combate(herois or [criar_heroi("guerreiro")], inimigos, random.Random(semente))
    combate.ambientes = criar_ambientes(ambientes)
    if ouro is not None:
        combate.grupo = SimpleNamespace(ouro=ouro)
    combate.iniciar()
    return combate


def turno_de(combate, lutador):
    combate.fila = [lutador]
    combate.comecar_turno()


# ---------------- Homem Bubônico ----------------

def test_homem_bubonico_solta_uma_ninhada_de_2_a_4_ratos_ao_cair():
    vistos = set()
    for semente in range(12):
        heroi, homem = criar_heroi("guerreiro"), criar_inimigo("homem_bubonico")
        combate = combate_com([homem], [heroi], semente=semente)
        combate.causar_dano(homem, 999, heroi)
        ninhada = [i for i in combate.inimigos if i.chave == "ninhada_de_ratos"]
        assert len(ninhada) == 1 and ninhada[0].esta_vivo() and not ninhada[0].eh_invocacao
        assert 2 <= ninhada[0].vivos() <= 4
        vistos.add(ninhada[0].vivos())
        assert not combate.verificar_fim()                               # a luta continua com os ratos
    assert len(vistos) > 1


# ---------------- Mendigo Bubônico ----------------

def test_mendigo_ignorado_bate_a_carteira_e_devolve_ao_cair():
    heroi, mendigo = criar_heroi("guerreiro"), criar_inimigo("mendigo_bubonico")
    combate = combate_com([mendigo, criar_inimigo("goblin")], [heroi], ouro=200)
    turno_de(combate, mendigo)                                           # 1º turno: só pede
    assert combate.grupo.ouro == 200
    combate.encerrar_turno()
    turno_de(combate, mendigo)                                           # ninguém deu atenção: roubou
    roubado = 200 - combate.grupo.ouro
    assert 10 <= roubado <= 30 and any(e.tipo == "roubo_de_ouro" for e in combate.eventos)
    combate.encerrar_turno()
    combate.causar_dano(mendigo, 1, heroi)                               # agora levou um golpe
    antes = combate.grupo.ouro
    turno_de(combate, mendigo)
    assert combate.grupo.ouro == antes
    combate.causar_dano(mendigo, 999, heroi)
    assert combate.grupo.ouro == 200                                     # caiu: o ouro volta


def test_mendigo_rouba_no_minimo_5():
    heroi, mendigo = criar_heroi("guerreiro"), criar_inimigo("mendigo_bubonico")
    combate = combate_com([mendigo], [heroi], ouro=20)
    turno_de(combate, mendigo)
    combate.encerrar_turno()
    turno_de(combate, mendigo)
    assert combate.grupo.ouro == 15


# ---------------- Carrasco Bubônico ----------------

def test_carrasco_dobra_o_dano_abaixo_de_25_por_cento():
    heroi, carrasco = criar_heroi("guerreiro"), criar_inimigo("carrasco_bubonico")
    combate = combate_com([carrasco], [heroi])
    golpes = []
    combate.golpear = lambda atacante, alvo, dano, **kw: golpes.append(dano) or ResultadoGolpe(alvo)
    efeito = golpe("machadada_do_carrasco").efeitos[0]
    for fracao in (0.5, 0.2):
        heroi.vida = int(heroi.vida_maxima * fracao)
        combate.rng = random.Random(7)                                   # mesmo sorteio de dano
        efeito.aplicar(combate, carrasco, [heroi], 1, Contexto())
    assert golpes[1] == 2 * golpes[0]
    assert "abaixo de 25% da vida" in efeito.resumo()
    assert ficha("carrasco_bubonico")["categoria"] == "elite" and "carrasco_bubonico" in regiao("reino_dos_ratos").elites


# ---------------- Freira Roída ----------------

def test_freira_roida_cura_os_ratos_e_espalha_a_peste():
    heroi, freira, ratazana = criar_heroi("guerreiro"), criar_inimigo("freira_roida"), criar_inimigo("ratazana_gigante")
    combate = combate_com([freira, ratazana], [heroi])
    ratazana.vida = ratazana.vida_maxima // 2
    antes = ratazana.vida
    freira.energia = 2
    combate.atual, combate.pode_agir = freira, True
    assert combate.usar_habilidade(freira, "prece_roedora")
    assert ratazana.vida > antes
    assert any(e.dados.get("status") == "peste" for e in golpe("hino_distorcido").efeitos)


# ---------------- zonas ----------------

def test_cada_zona_do_reino_sorteia_os_seus_inimigos():
    reino = regiao("reino_dos_ratos")
    total = 9
    for area in range(1, total):
        zona = reino.zona(area, total)
        sorteados = {reino.sortear_inimigo(random.Random(s), False, area, total) for s in range(40)}
        assert sorteados <= set(zona["inimigos"])
    galerias, mercado = reino.zona(1, total), reino.zona(total // 2, total)
    assert "homem_bubonico" in galerias["inimigos"] and "mendigo_bubonico" in mercado["inimigos"]


def test_fases_sem_zonas_sorteiam_igual_a_antes():
    floresta = regiao("floresta")
    for semente in range(20):
        assert floresta.sortear_inimigo(random.Random(semente), False, 3, 8) == \
               floresta.sortear_inimigo(random.Random(semente))


def test_ladrao_e_mendigo_somem_no_escuro():
    ladrao, mendigo, alquimista = criar_inimigo("rato_ladrao"), criar_inimigo("mendigo_bubonico"), criar_inimigo("rato_alquimista")
    combate = combate_com([ladrao, mendigo, alquimista], ambientes=[{"tipo": "escuridao"}])
    assert combate.oculto(ladrao) and combate.oculto(mendigo) and not combate.oculto(alquimista)


# ---------------- dados ----------------

def test_bubonicos_no_reino_com_sprite_e_familia():
    from roguelike.dados import carregar
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    reino = regiao("reino_dos_ratos")
    assert "bubonicos" in carregar("regioes")["familias"]
    for chave in NOVOS:
        assert chave in reino.todos_os_inimigos() and ficha(chave)["familia"] == "bubonicos"
        assert sprites.existe(chave) and criar_inimigo(chave).imune("peste")
    assert sprites.existe(criar_inimigo("ninhada_de_ratos").sprite)
