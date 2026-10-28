"""Testes das regras do combate: iniciativa, energia, golpes, alvos e fim da luta."""

import random


from roguelike.classes import criar_heroi
from roguelike.combate import Combate, ajuste_de_grupo
from roguelike.dados import regras
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo

from apoio_roguelike import SorteControlado, combate_pronto, vez_de


# ---------------- iniciativa e turnos ----------------

def test_maior_iniciativa_age_primeiro_e_invocacoes_por_ultimo():
    lento = criar_inimigo("golem")             # iniciativa 1 a 4
    rapido = criar_heroi("ladino")            # iniciativa 6 a 12
    combate = combate_pronto([rapido], [lento])
    combate.invocar(rapido, "esqueleto_servo")
    combate.nova_rodada()
    assert combate.fila[0] is rapido
    assert combate.fila[-1].eh_invocacao


def test_cada_rodada_rola_a_iniciativa_de_novo():
    herois = [criar_heroi("ladino"), criar_heroi("guerreiro")]
    combate = Combate(herois, [criar_inimigo("goblin")], random.Random(3), ajustar_grupo=False)
    combate.iniciar()
    ordens = set()
    for _ in range(20):
        combate.nova_rodada()
        ordens.add(tuple(l.nome for l in combate.fila))
    assert len(ordens) > 1


def test_concentrar_da_energia_e_passa_a_vez():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    vez_de(combate, heroi)
    energia = heroi.energia
    assert combate.concentrar(heroi)
    assert heroi.energia == energia + 2
    assert not combate.pode_agir


def test_ganho_de_energia_no_inicio_do_turno_pode_acontecer():
    heroi = criar_heroi("mago")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")], SorteControlado(padrao=0.0))
    energia = heroi.energia
    vez_de(combate, heroi)
    assert heroi.energia > energia


def test_habilidade_sem_energia_nao_pode_ser_usada():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, heroi)
    heroi.energia = 0
    assert not combate.usar_habilidade(heroi, "redemoinho")
    assert combate.pode_agir            # a vez não foi gasta


def test_nao_age_fora_da_sua_vez():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, goblin)
    assert not combate.usar_habilidade(heroi, "golpe", goblin)


# ---------------- golpes ----------------

def test_golpe_sem_sorte_causa_o_dano_maximo_da_habilidade():
    heroi = criar_heroi("guerreiro")          # FOR 6: 5 + 6 x 0,3 = 6,8 (antes do bônus de dano)
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, heroi)
    vida = goblin.vida
    combate.usar_habilidade(heroi, "golpe", goblin)
    assert goblin.vida == vida - round(6.8 * (1 + heroi.stat("dano_causado")))


def test_esquiva_anula_o_golpe():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    combate.rng = SorteControlado(sorteios=[0.0])    # primeiro sorteio = esquiva
    resultado = combate.golpear(heroi, goblin, 10)
    assert resultado.esquivou and goblin.vida == goblin.vida_maxima


def test_critico_multiplica_o_dano():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    goblin.vida_da_ficha = 100
    goblin.curar_tudo()
    combate = combate_pronto([heroi], [goblin])
    combate.rng = SorteControlado(sorteios=[0.99, 0.0])   # não esquiva, crítico
    resultado = combate.golpear(heroi, goblin, 10)
    assert resultado.critico
    assert resultado.dano == round(10 * heroi.stat("dano_critico") * (1 + heroi.stat("dano_causado")))


def test_bloqueio_reduz_o_dano():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    goblin.vida_da_ficha = 100
    goblin.curar_tudo()
    combate = combate_pronto([heroi], [goblin])
    combate.rng = SorteControlado(sorteios=[0.99, 0.99, 0.0])   # sem esquiva, sem crítico, bloqueia
    resultado = combate.golpear(heroi, goblin, 10)
    assert resultado.bloqueou
    assert resultado.dano == round(10 * (1 + heroi.stat("dano_causado")) * (1 - goblin.stat("reducao_bloqueio")))


def test_ataque_de_varios_golpes_rola_cada_golpe():
    heroi = criar_heroi("barbaro")
    goblin = criar_inimigo("goblin")
    goblin.vida_da_ficha = 100
    goblin.curar_tudo()
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, heroi)
    heroi.energia = 5
    combate.pegar_eventos()
    combate.usar_habilidade(heroi, "rajada_selvagem", goblin)
    danos = [e for e in combate.pegar_eventos() if e.tipo == "dano"]
    assert len(danos) == 4


def test_defesa_reduz_e_dano_minimo_e_1():
    heroi = criar_heroi("guerreiro")
    golem = criar_inimigo("golem")            # defesa 5
    combate = combate_pronto([heroi], [golem])
    assert combate.golpear(heroi, golem, 3).dano == 1


def test_roubo_de_vida_cura_o_atacante():
    heroi = criar_heroi("guerreiro")
    heroi.vida = 10
    goblin = criar_inimigo("goblin")
    goblin.vida_da_ficha = 100
    goblin.curar_tudo()
    combate = combate_pronto([heroi], [goblin])
    resultado = combate.golpear(heroi, goblin, 10, roubo=0.5)
    assert heroi.vida == 10 + int(resultado.dano * 0.5)


def test_contra_ataque_revida_golpe_direto():
    heroi = criar_heroi("ladino")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    combate.aplicar_status(heroi, "contra_ataque", valor=4)
    combate.golpear(goblin, heroi, 3)
    assert goblin.vida == goblin.vida_maxima - round(4 * (1 + heroi.stat("dano_causado")))


# ---------------- alvos ----------------

def test_provocacao_obriga_a_atacar_o_provocador():
    tanque, mago = criar_heroi("guerreiro"), criar_heroi("mago")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([tanque, mago], [goblin])
    combate.aplicar_status(tanque, "provocacao")
    assert combate.alvos_validos(goblin, golpe("facada")) == [tanque]


def test_furtivo_nao_pode_ser_alvo_de_ataque_direto():
    ladino, guerreiro = criar_heroi("ladino"), criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([ladino, guerreiro], [goblin])
    combate.aplicar_status(ladino, "furtivo")
    assert combate.alvos_validos(goblin, golpe("facada")) == [guerreiro]
    # ataques em área ainda acertam
    assert ladino in combate.alvos_validos(goblin, golpe("bomba_goblin"))


def test_alvo_invalido_nao_gasta_a_vez():
    heroi = criar_heroi("sacerdote")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, heroi)
    heroi.energia = 5
    assert not combate.usar_habilidade(heroi, "cura_sagrada", goblin)
    assert combate.pode_agir


# ---------------- grupo, fim da luta, invocações ----------------

def test_ajuste_de_grupo():
    tabela = regras()["grupo"]["por_tamanho"]
    assert ajuste_de_grupo(3) == tabela["3"]
    # quanto maior o grupo, mais fortes os inimigos
    for n in range(1, 5):
        assert ajuste_de_grupo(n + 1)["vida_percentual"] > ajuste_de_grupo(n)["vida_percentual"]
        assert ajuste_de_grupo(n + 1)["dano_causado"] > ajuste_de_grupo(n)["dano_causado"]
    sozinho = ajuste_de_grupo(1)
    assert sozinho["chance_esquiva"] < 0 and sozinho["chance_bloqueio"] < 0
    assert sozinho["vida_percentual"] < 0 and sozinho["dano_causado"] < 0
    # fora da tabela usa o tamanho mais próximo, e mexer no resultado não estraga a tabela
    assert ajuste_de_grupo(0) == tabela["1"] and ajuste_de_grupo(9) == tabela["5"]
    ajuste_de_grupo(2)["vida_percentual"] = 99
    assert ajuste_de_grupo(2) == tabela["2"]

def test_inimigos_ganham_vida_com_grupo_maior():
    sozinho = criar_inimigo("orc")
    em_grupo = criar_inimigo("orc")
    Combate([criar_heroi("guerreiro")], [sozinho])
    Combate([criar_heroi("guerreiro") for _ in range(3)], [em_grupo])
    base = em_grupo.vida_base()
    assert em_grupo.vida_maxima == round(base * (1 + ajuste_de_grupo(3)["vida_percentual"]))
    assert sozinho.vida_maxima == round(base * (1 + ajuste_de_grupo(1)["vida_percentual"]))
    assert em_grupo.vida == em_grupo.vida_maxima


def test_vitoria_quando_todos_os_inimigos_caem():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([heroi], [goblin])
    combate.causar_dano(goblin, 999, heroi)
    combate.verificar_fim()
    assert combate.resultado == "vitoria"
    assert combate.derrotados == [goblin]
    assert combate.xp_ganho() == goblin.recompensa_xp


def test_derrota_quando_todos_os_herois_caem():
    heroi = criar_heroi("guerreiro")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.causar_dano(heroi, 999, None)
    combate.verificar_fim()
    assert combate.resultado == "derrota"


def test_invocacao_luta_do_lado_de_quem_chamou_e_tem_limite():
    heroi = criar_heroi("mago")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    for _ in range(4):
        combate.invocar(heroi, "esqueleto_servo")
    servos = combate.invocacoes_de(heroi)
    assert len(servos) == int(heroi.stat("max_invocacoes"))
    assert all(s.lado == "herois" for s in servos)


def test_invocacao_nao_conta_para_a_vitoria_dos_inimigos():
    heroi = criar_heroi("guerreiro")
    aranha_mae = criar_inimigo("aranha_mae")
    combate = combate_pronto([heroi], [aranha_mae])
    combate.invocar(aranha_mae, "filhote_invocado")
    combate.causar_dano(aranha_mae, 9999, heroi)
    combate.verificar_fim()
    assert combate.resultado == "vitoria"
    assert all(not i.eh_invocacao for i in combate.inimigos)


def test_reviver_traz_o_heroi_caido():
    caido, sacerdote = criar_heroi("guerreiro"), criar_heroi("sacerdote")
    combate = combate_pronto([caido, sacerdote], [criar_inimigo("goblin")])
    combate.causar_dano(caido, 999, None)
    assert not caido.esta_vivo()
    assert combate.reviver(caido, 0.5)
    assert caido.vida == round(caido.vida_maxima * 0.5)


def test_combate_inteiro_com_ia_sempre_termina():
    for semente in range(20):
        herois = [criar_heroi("guerreiro"), criar_heroi("sacerdote"), criar_heroi("mago", aparencia="Gelo")]
        inimigos = [criar_inimigo("aranha"), criar_inimigo("goblin_xama"), criar_inimigo("carnical")]
        combate = Combate(herois, inimigos, random.Random(semente))
        combate.iniciar()
        for _ in range(2000):
            if combate.resultado is not None:
                break
            combate.comecar_turno()
            if combate.pode_agir:
                combate.agir_ia()
        assert combate.resultado in ("vitoria", "derrota")
