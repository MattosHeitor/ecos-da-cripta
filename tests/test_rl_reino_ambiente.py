"""Reino dos Ratos, etapa 2B: ambientes de combate (água subindo e escuridão) e a ligação deles com as zonas.

Os inimigos nadadores e os que somem no escuro chegam na etapa 3; aqui um goblin é marcado só no teste.
"""

import random

from roguelike.ambiente import AguaSubindo, Escuridao, criar_ambientes
from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.run import Run


def goblin(**marcas):
    inimigo = criar_inimigo("goblin")
    inimigo.ficha = dict(inimigo.ficha, **marcas)          # (cópia: a ficha do jogo não muda)
    return inimigo


def combate_com(ambientes, inimigos=None, herois=None, semente=1):
    combate = Combate(herois or [criar_heroi("guerreiro")], inimigos or [criar_inimigo("goblin")], random.Random(semente))
    combate.ambientes = criar_ambientes(ambientes)
    combate.iniciar()
    return combate


# ---------------- água ----------------

def test_agua_sobe_a_cada_3_rodadas_ate_a_alta():
    combate = combate_com([{"tipo": "agua"}])
    agua = combate.ambientes[0]
    assert isinstance(agua, AguaSubindo) and agua.nome_do_nivel == "Rasa"
    niveis = []
    for _ in range(8):
        combate.nova_rodada()
        niveis.append(agua.nivel)
    assert niveis == [1, 1, 1, 2, 2, 2, 3, 3]                 # rodada 1 só começa a contar
    assert any(e.tipo == "ambiente" and "Funda" in e.texto for e in combate.eventos)


def test_agua_alta_encharca_os_herois_e_da_forca_aos_nadadores():
    nadador, comum = goblin(nadador=True), criar_inimigo("goblin")
    combate = combate_com([{"tipo": "agua", "nivel_inicial": 3}], [nadador, comum])
    heroi = combate.herois[0]
    assert heroi.tem_status("encharcado") and nadador.tem_status("nadando") and not comum.tem_status("nadando")
    combate.remover_status(heroi, "encharcado")
    combate.nova_rodada()                                     # a água continua alta: volta
    assert heroi.tem_status("encharcado")


def test_agua_funda_e_alta_enfraquecem_o_fogo():
    assert [AguaSubindo({"nivel_inicial": n}).multiplicador_de_dano(None, None, "fogo", None) for n in range(4)] == \
           [1.0, 1.0, 0.8, 0.6]
    assert AguaSubindo({"nivel_inicial": 3}).multiplicador_de_dano(None, None, "fisico", None) == 1.0
    danos = []
    for nivel in (1, 3):                                      # mesmo sorteio: só a água muda
        combate = combate_com([{"tipo": "agua", "nivel_inicial": nivel}])
        alvo = combate.inimigos[0]
        alvo.vida = 999                                       # (não morre: o dano não é cortado pela vida)
        danos.append(combate.golpear(combate.herois[0], alvo, 20, ignora_esquiva=True, ignora_bloqueio=True,
                                     elemento="fogo").dano)
    assert danos[1] < danos[0]


# ---------------- escuridão ----------------

def test_no_escuro_quem_some_nao_pode_ser_alvo_de_um_alvo_so():
    sombrio, visivel = goblin(some_no_escuro=True), criar_inimigo("goblin")
    combate = combate_com([{"tipo": "escuridao"}], [sombrio, visivel])
    heroi = combate.herois[0]
    assert combate.oculto(sombrio) and not combate.oculto(visivel)
    assert combate.alvos_validos(heroi, golpe("golpe")) == [visivel]
    assert sombrio in combate.alvos_validos(heroi, golpe("redemoinho"))      # golpe em área acerta


def test_todos_ocultos_golpeia_as_cegas_e_eles_esquivam_mais():
    sombrio = goblin(some_no_escuro=True)
    combate = combate_com([{"tipo": "escuridao"}], [sombrio])
    heroi = combate.herois[0]
    assert combate.alvos_validos(heroi, golpe("golpe")) == [sombrio]
    assert combate.ambientes[0].esquiva_extra(heroi, sombrio, combate) == 0.5


def test_lanterna_revela_os_ocultos_e_ilumina_quem_carrega():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("lanterna_de_mao"))
    sombrio = goblin(some_no_escuro=True)
    combate = combate_com([{"tipo": "escuridao"}], [sombrio], [heroi])
    escuridao = combate.ambientes[0]
    assert isinstance(escuridao, Escuridao) and escuridao.tem_luz(combate)
    assert not combate.oculto(sombrio) and heroi.tem_status("iluminado")
    assert "luz" in escuridao.resumo(combate)


def test_vela_tambem_e_luz():
    sombrio = goblin(some_no_escuro=True)
    combate = combate_com([{"tipo": "escuridao"}], [sombrio])
    assert combate.oculto(sombrio)
    combate.aplicar_status(combate.herois[0], "iluminado", 3)               # Vela de Vigília, Óleo de Lamparina
    assert not combate.oculto(sombrio)


# ---------------- zonas e o resto do jogo ----------------

def test_cada_zona_do_reino_traz_os_seus_ambientes():
    run = Run([criar_heroi("guerreiro")], "AMBIENTE", "reino_dos_ratos")
    total = run.areas_da_regiao()
    esperado = {1: ["agua"], total // 2: ["escuridao"], total - 1: ["agua", "escuridao"], total: ["agua"]}
    for area, tipos in esperado.items():
        run.area = area
        assert [a.tipo for a in run.criar_combate(_encontro()).ambientes] == tipos, area
    run.area = total
    assert run.criar_combate(_encontro()).ambientes[0].sobe_a_cada == 5           # no Salão do Trono, devagar


def test_fases_sem_zona_nao_tem_ambiente():
    run = Run([criar_heroi("guerreiro")], "AMBIENTE", "floresta")
    assert run.criar_combate(_encontro()).ambientes == []


def _encontro():
    from roguelike.encontros import EncontroCombate
    return EncontroCombate("Teste", "", 1, ["goblin"])
