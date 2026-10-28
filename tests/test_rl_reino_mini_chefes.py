"""Reino dos Ratos, etapa 3C2: o status Encantado, o Médico da Peste Corrompido, o Flautista Caído (mini-chefes por
zona, com escolta) e a Flauta do Caçador de Ratos."""

import random

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.encontros import MontadorDeCombate
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo, ficha
from roguelike.itens import item
from roguelike.loot import tabela_de
from roguelike.regioes import regiao

TOTAL = 9


def combate_com(inimigos, herois=None, semente=1):
    combate = Combate(herois or [criar_heroi("guerreiro")], inimigos, random.Random(semente))
    combate.iniciar()
    return combate


def turno_de(combate, lutador):
    combate.fila = [lutador]
    combate.comecar_turno()


def ultimo_golpe(combate):
    return [e for e in combate.eventos if e.tipo == "habilidade"][-1]


# ---------------- Encantado ----------------

def test_heroi_encantado_ataca_um_aliado_e_o_encanto_passa():
    guerreiro, sacerdote = criar_heroi("guerreiro"), criar_heroi("sacerdote")
    combate = combate_com([criar_inimigo("goblin")], [guerreiro, sacerdote])
    combate.aplicar_status(guerreiro, "encantado")
    turno_de(combate, guerreiro)
    assert any(e.tipo == "encanto" for e in combate.eventos)
    evento = ultimo_golpe(combate)
    assert evento.origem is guerreiro and evento.extras["alvos"] == [sacerdote]
    assert not combate.pode_agir and not guerreiro.tem_status("encantado")


def test_encantado_sozinho_ataca_a_si_mesmo():
    guerreiro = criar_heroi("guerreiro")
    combate = combate_com([criar_inimigo("goblin")], [guerreiro])
    combate.aplicar_status(guerreiro, "encantado")
    turno_de(combate, guerreiro)
    assert ultimo_golpe(combate).extras["alvos"] == [guerreiro]


def test_melodia_do_cacador_encanta_so_os_bandos_e_eles_mordem_os_companheiros():
    heroi = criar_heroi("guerreiro")
    bando, ratazana = criar_inimigo("rato_comum"), criar_inimigo("ratazana_gigante")
    combate = combate_com([bando, ratazana], [heroi])
    heroi.aprender("melodia_do_cacador", perguntar=False)
    for _ in range(10):                                            # (80% de chance: tenta até pegar)
        if bando.tem_status("encantado"):
            break
        heroi.energia = 2
        combate.atual, combate.pode_agir = heroi, True
        combate.usar_habilidade(heroi, "melodia_do_cacador")
    assert bando.tem_status("encantado") and not ratazana.tem_status("encantado")
    turno_de(combate, bando)
    assert ultimo_golpe(combate).extras["alvos"] == [ratazana]


# ---------------- mini-chefes por zona ----------------

def montador(area):
    return MontadorDeCombate(regiao("reino_dos_ratos"), area, random.Random(1), 3, False, TOTAL)


def test_cada_zona_tem_o_seu_mini_chefe_com_escolta():
    reino = regiao("reino_dos_ratos")
    galerias, catedral = 1, TOTAL - 1
    assert reino.mini_chefes_da_area(galerias, TOTAL) == ["medico_da_peste_corrompido"]
    assert reino.mini_chefes_da_area(catedral, TOTAL) == ["flautista_caido"]
    assert reino.mini_chefes_da_area(TOTAL // 2, TOTAL) == []        # o Mercado não tem
    encontro = montador(galerias).mini_chefe()
    assert encontro.inimigos == ["medico_da_peste_corrompido", "mendigo_bubonico"]          # com o seu "paciente"
    assert montador(catedral).mini_chefe().inimigos == ["flautista_caido"]                  # ele chama os bandos
    assert all(c in reino.todos_os_inimigos() for c in ("medico_da_peste_corrompido", "flautista_caido"))


# ---------------- Médico da Peste Corrompido ----------------

def test_medico_trata_os_bubonicos_a_cada_3_turnos_e_a_sangria_rouba_vida():
    medico, homem = criar_inimigo("medico_da_peste_corrompido"), criar_inimigo("homem_bubonico")
    combate = combate_com([medico, homem])
    homem.vida = homem.vida_maxima // 2
    for _ in range(3):
        turno_de(combate, medico)
        combate.encerrar_turno()
    assert homem.vida > homem.vida_maxima // 2 and homem.tem_status("fortalecido")
    dano = next(e for e in golpe("sangria").efeitos if e.dados["tipo"] == "dano")
    assert golpe("sangria").alvo == "inimigos" and dano.dados["roubo"] > 0
    assert ficha("medico_da_peste_corrompido")["categoria"] == "mini_chefe"


# ---------------- Flautista Caído ----------------

def test_flautista_chama_bandos_ate_2_por_luta_e_nao_se_encanta():
    heroi, flautista = criar_heroi("guerreiro"), criar_inimigo("flautista_caido")
    combate = combate_com([flautista], [heroi])
    assert flautista.imune("encantado")
    for _ in range(9):
        turno_de(combate, flautista)
        combate.encerrar_turno()
    chegaram = [i for i in combate.inimigos if i.chave == "rato_comum"]
    assert len(chegaram) == 2 and not any(i.eh_invocacao for i in chegaram)


def test_flautista_deixa_a_flauta_que_ensina_a_melodia():
    assert any(linha["item"] == "flauta_do_cacador_de_ratos" and linha["chance"] == 1.0
               for linha in tabela_de("flautista_caido"))
    flauta = item("flauta_do_cacador_de_ratos")
    assert flauta.espaco == "arma_secundaria" and flauta.habilidade == "melodia_do_cacador"
    heroi = criar_heroi("guerreiro")
    heroi.equipar(flauta)
    assert "melodia_do_cacador" in [h.chave for h, _ in heroi.habilidades()]


def test_mini_chefes_com_sprite():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for chave in ("medico_da_peste_corrompido", "flautista_caido"):
        assert sprites.existe(chave) and criar_inimigo(chave).imune("peste")
