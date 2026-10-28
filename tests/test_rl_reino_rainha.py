"""Reino dos Ratos, etapa 5B: a Rainha dos Ratos (a roda que gira, o nó exposto, a Roda Furiosa, o Silenciado e a
fúria do último rato) e a luta em duas partes: o Rei foge para o trono, a Rainha desce e o Rei volta quando ela cai."""

import random

import pygame

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.encontros import EncontroCombate, MontadorDeCombate
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo
from roguelike.regioes import regiao
from roguelike.roda import NoDeCaudas
from roguelike.run import Run, Recompensa

from test_telas_fluxo import app, comecar, quadros, tecla  # noqa: F401  (fixture e ajudantes)


def luta_da_rainha():
    herois = [criar_heroi(c) for c in ("guerreiro", "sacerdote", "mago")]
    combate = Combate(herois, [criar_inimigo("rainha_dos_ratos")], random.Random(2))
    combate.iniciar()
    return combate, combate.inimigos[0], herois


def matar(combate, lutador, quem):
    combate.causar_dano(lutador, 99999, quem)


# ---------------- a roda ----------------

def test_rainha_e_o_no_de_uma_roda_de_oito_ratos():
    combate, rainha, _ = luta_da_rainha()
    assert isinstance(rainha, NoDeCaudas) and len(rainha.roda) == 8
    assert {r.nome for r in rainha.roda} == {"Mordedor", "Pestilento", "Guincho", "Curandeiro"}
    assert rainha.vida == sum(r.vida for r in rainha.roda) and rainha.vida_maxima == rainha.vida
    assert all(r.ajustes == rainha.ajustes for r in rainha.roda)


def test_so_os_da_frente_agem_e_podem_ser_atingidos():
    combate, rainha, (guerreiro, _, _) = luta_da_rainha()
    passiva = next(p for p in rainha.passivas if hasattr(p, "proximo_giro"))
    frente = passiva.frente(rainha)
    assert len(frente) == 2
    assert set(combate.alvos_validos(guerreiro, golpe("golpe"))) == set(frente)
    assert set(combate.alvos_validos(guerreiro, golpe("redemoinho"))) == set(frente)     # área também não passa
    combate.nova_rodada()
    girou = passiva.frente(rainha)
    assert girou != frente and girou[:1] == frente[1:]                                  # andou uma casa
    assert all(r in combate.fila for r in girou)
    assert not any(r in combate.fila for r in rainha.roda if r not in girou)
    assert passiva.proximo_giro(rainha)[:1] == girou[1:]


def test_no_exposto_com_metade_da_roda_caida_fere_todos():
    combate, rainha, (guerreiro, _, _) = luta_da_rainha()
    assert rainha.tem_status("no_fechado") and rainha not in combate.alvos_validos(guerreiro, golpe("golpe"))
    for rato in rainha.roda[:4]:
        matar(combate, rato, guerreiro)
    assert not rainha.tem_status("no_fechado") and rainha in combate.alvos_validos(guerreiro, golpe("golpe"))
    antes = [r.vida for r in rainha.ratos_vivos()]
    combate.causar_dano(rainha, 20, guerreiro)
    assert [r.vida for r in rainha.ratos_vivos()] == [v - 15 for v in antes]           # 75% em cada rato


def test_no_ignorado_por_tres_turnos_fecha_ate_outro_rato_cair():
    combate, rainha, (guerreiro, _, _) = luta_da_rainha()
    for rato in rainha.roda[:4]:
        matar(combate, rato, guerreiro)
    passiva = next(p for p in rainha.passivas if hasattr(p, "proximo_giro"))
    for _ in range(3):
        passiva.inicio_do_turno(rainha, combate)
    assert rainha.tem_status("no_fechado")
    matar(combate, rainha.ratos_vivos()[0], guerreiro)
    assert not rainha.tem_status("no_fechado")


def test_ultimo_rato_enlouquece_e_a_rainha_cai_com_ele():
    combate, rainha, (guerreiro, _, _) = luta_da_rainha()
    for rato in rainha.roda[:7]:
        matar(combate, rato, guerreiro)
    ultimo = rainha.ratos_vivos()[0]
    assert ultimo.tem_status("furia_da_roda") and ultimo.stat("dano_causado") >= 1.0
    matar(combate, ultimo, guerreiro)
    assert not rainha.esta_vivo() and rainha in combate.derrotados
    assert combate.verificar_fim() and combate.resultado == "vitoria"


def test_roda_furiosa_ganha_golpes_quando_os_ratos_caem():
    combate, rainha, (guerreiro, _, _) = luta_da_rainha()

    def golpes():
        antes = len([e for e in combate.eventos if e.tipo in ("dano", "esquiva") and e.alvo is guerreiro])
        combate.aplicar_efeitos(rainha, golpe("roda_furiosa").efeitos, [guerreiro], 1)
        return len([e for e in combate.eventos if e.tipo in ("dano", "esquiva") and e.alvo is guerreiro]) - antes
    guerreiro.vida = 99999
    assert golpes() == 1
    for rato in rainha.roda[:4]:
        matar(combate, rato, criar_heroi("mago"))
    assert golpes() == 3


def test_silenciado_so_deixa_golpes_sem_custo():
    combate, _, (guerreiro, _, _) = luta_da_rainha()
    guerreiro.energia = 10
    combate.aplicar_status(guerreiro, "silenciado")
    assert golpe("golpe").pode_usar(guerreiro) and not golpe("redemoinho").pode_usar(guerreiro)


def test_curandeiro_cura_os_ratos_mas_nao_o_no():
    combate, rainha, (guerreiro, _, _) = luta_da_rainha()
    curandeiro = next(r for r in rainha.roda if r.nome == "Curandeiro")
    for rato in rainha.roda:
        rato.vida = rato.vida_maxima // 2
    combate.aplicar_efeitos(curandeiro, golpe("lambida_da_roda").efeitos, combate.aliados_de(curandeiro), 1)
    assert all(r.vida > r.vida_maxima // 2 for r in rainha.roda)
    assert not any(e.tipo == "cura" and e.alvo is rainha for e in combate.eventos)


# ---------------- o Rei foge para o trono e volta ----------------

def run_no_trono():
    run = Run([criar_heroi(c) for c in ("guerreiro", "sacerdote", "mago")], "TRONO", "reino_dos_ratos")
    run.area = run.areas_da_regiao()
    run.encontro = MontadorDeCombate(regiao("reino_dos_ratos"), run.area, random.Random(1), 3, False, run.area).chefe()
    run.estado = "encontro"
    return run


def vencer(run, combate):
    for _ in range(4):
        for inimigo in list(combate.inimigos):
            matar(combate, inimigo, run.grupo.herois[0])
    combate.verificar_fim()
    return run.concluir_combate(combate)


def test_rei_foge_para_o_trono_e_a_rainha_vem_na_segunda_parte():
    run = run_no_trono()
    combate = run.criar_combate()
    rei = combate.inimigos[0]
    rei.ouro_roubado = 30
    vencer(run, combate)
    assert rei.esta_vivo() and rei not in combate.derrotados and "rei_dos_ratos" not in run.estatisticas["chefes"]
    ondas = run.ondas
    assert ondas is not None and ondas.sem_fuga and ondas.vencidas == 1 and ondas.total == 2
    assert [ondas.nome_da_onda(1), ondas.nome_da_onda(2)] == ["O Rei", "A Rainha"]
    encontro = run.proxima_onda()
    assert encontro.tipo == "chefe" and encontro.inimigos == ["rainha_dos_ratos"]
    assert encontro.trono["chave"] == "rei_dos_ratos" and encontro.trono["ouro_roubado"] == 30


def test_rei_volta_quando_a_rainha_cai_e_so_entao_a_luta_acaba():
    run = run_no_trono()
    primeira = run.criar_combate()
    primeira.inimigos[0].ouro_roubado = 30                        # o Imposto Real da 1ª parte
    vencer(run, primeira)
    run.proxima_onda()
    combate = run.criar_combate()
    assert combate.de_volta is not None
    rainha = combate.inimigos[0]
    for rato in list(rainha.roda):
        matar(combate, rato, run.grupo.herois[0])
    assert not combate.verificar_fim()
    rei = next(i for i in combate.inimigos if i.chave == "rei_dos_ratos")
    assert abs(rei.fracao_vida() - 0.2) < 0.01 and rei.tem_status("fase_do_chefe") and rei.status["fase_do_chefe"].valor == 2
    assert rei.ouro_roubado == 30 and getattr(rei, "retirada_feita", False)
    for _ in range(2):
        matar(combate, rei, run.grupo.herois[0])
    assert not rei.esta_vivo() and combate.verificar_fim() and combate.resultado == "vitoria"
    run.concluir_combate(combate)
    assert {"rainha_dos_ratos", "rei_dos_ratos"} <= set(run.estatisticas["chefes"]) and run.ondas.terminou()


def test_tela_da_pausa_nao_deixa_fugir_e_o_fim_vai_direto_ao_mapa(app):  # noqa: F811
    from telas import fluxo
    run = comecar(app)
    trono = run_no_trono()
    run.regiao_atual, run.area, run.encontro, run.estado = trono.regiao_atual, trono.area, trono.encontro, "encontro"
    vencer(run, run.criar_combate())
    fluxo.depois_do_combate(app, run, Recompensa())
    assert type(app.atual).__name__ == "TelaEntreOndas"
    quadros(app)
    tecla(app, pygame.K_3, "3")                                    # não há fuga
    assert run.ondas is not None and type(app.atual).__name__ == "TelaEntreOndas"
    tecla(app, pygame.K_1, "1")                                    # Enfrentar a Rainha
    assert type(app.atual).__name__ == "TelaCombate" and run.encontro.inimigos == ["rainha_dos_ratos"]
    run.ondas.vencer()
    fluxo.depois_do_combate(app, run, Recompensa())
    assert run.ondas is None and type(app.atual).__name__ != "TelaEntreOndas"


def test_sprites_da_rainha_e_da_roda():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for nome in ("rainha_dos_ratos", "mordedor_da_rainha", "pestilento_da_rainha", "guincho_da_rainha",
                 "curandeiro_da_rainha"):
        assert sprites.existe(nome)
    from roguelike.dados import carregar
    assert carregar("regioes")["regioes"]["reino_dos_ratos"]["formas_do_chefe"] == ["rainha_dos_ratos"]   # bestiário
