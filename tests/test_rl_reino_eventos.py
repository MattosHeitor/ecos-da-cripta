"""Reino dos Ratos, etapa 4A: eventos do Reino (Mercado Roedor, Prisioneiro na Gaiola, Banquete do Rei, Altar do
Queijo), eventos por zona e as consequências novas."""

import random

from roguelike.classes import criar_heroi
from roguelike.encontros import EncontroCombate, GeradorDeEncontros
from roguelike.eventos_run import evento, criar_consequencia, ResultadoEvento
from roguelike.itens import item
from roguelike.run import Run

NOVOS = ("mercado_do_rato_mercador", "prisioneiro_na_gaiola", "banquete_do_rei", "altar_do_queijo")


def run_no_reino(area=1, classes=("guerreiro", "sacerdote")):
    run = Run([criar_heroi(c) for c in classes], "EVENTOS", "reino_dos_ratos")
    run.area = area
    return run


def aplicar(run, dados, semente=1):
    resultado = ResultadoEvento()
    criar_consequencia(dados).aplicar(run, random.Random(semente), resultado)
    return resultado


# ---------------- por zona ----------------

def test_eventos_do_reino_aparecem_so_nas_suas_zonas():
    run = run_no_reino()
    total = run.areas_da_regiao()

    def possiveis(area):
        run.area = area
        return set(GeradorDeEncontros(run, random.Random(1)).eventos_possiveis()) & set(NOVOS)
    assert possiveis(1) == {"prisioneiro_na_gaiola"}                               # Galerias
    assert possiveis(total // 2) == {"mercado_do_rato_mercador", "prisioneiro_na_gaiola"}   # Mercado
    assert possiveis(total - 1) == {"banquete_do_rei", "altar_do_queijo"}           # Catedral Roída
    floresta = Run([criar_heroi("guerreiro")], "EVENTOS", "floresta")
    assert not set(GeradorDeEncontros(floresta, random.Random(1)).eventos_possiveis()) & set(NOVOS)


# ---------------- Mercado Roedor ----------------

def test_trocar_dois_queijos_precisa_de_dois_e_gasta_os_dois():
    run = run_no_reino()
    trocar = evento("mercado_do_rato_mercador").opcoes[0]
    run.grupo.bau.adicionar("queijo_mofado", 1)
    assert not trocar.disponivel(run)
    run.grupo.bau.adicionar("queijo_mofado", 1)
    assert trocar.disponivel(run)
    antes = len(run.todas_as_chaves())
    for consequencia in trocar.consequencias:
        consequencia.aplicar(run, random.Random(3), ResultadoEvento())
    assert run.quantidade_de("queijo_mofado") == 0 and len(run.todas_as_chaves()) >= antes - 1   # (MP3: + o prêmio)


def test_trocar_um_consumivel_qualquer():
    run = run_no_reino()
    trocar = evento("mercado_do_rato_mercador").opcoes[1]
    assert not trocar.disponivel(run)
    run.grupo.bau.adicionar("pocao_de_vida", 1)
    assert trocar.disponivel(run)
    resultado = aplicar(run, {"tipo": "trocar_consumivel", "raridade": "incomum"})
    assert run.quantidade_de("pocao_de_vida") == 0 and any("Entregou" in t for t in resultado.textos)


def test_roubar_o_mercado_traz_guardas_reais_na_proxima_luta():
    run = run_no_reino()
    aplicar(run, {"tipo": "reforcos_proximo_combate", "inimigos": ["rato_guarda_real", "rato_guarda_real"]})
    combate = run.criar_combate(EncontroCombate("t", "", 1, ["rato_comum"]))
    assert [i.chave for i in combate.inimigos].count("rato_guarda_real") == 2
    assert run.inimigos_extra_proximo_combate == []
    depois = run.criar_combate(EncontroCombate("t", "", 1, ["rato_comum"]))
    assert "rato_guarda_real" not in [i.chave for i in depois.inimigos]


# ---------------- Banquete e Peste fora da luta ----------------

def test_peste_de_evento_respeita_o_maximo_e_a_raca():
    run = run_no_reino()
    for _ in range(4):
        aplicar(run, {"tipo": "peste", "niveis": 2, "chance": 1.0})
    assert all(h.peste == 5 for h in run.grupo.herois)
    morto_vivo = criar_heroi("guerreiro")
    morto_vivo.definir_raca("revenante")
    escapou = 0
    for semente in range(40):
        outra = Run([morto_vivo], "EVENTOS", "reino_dos_ratos")
        morto_vivo.peste = 0
        aplicar(outra, {"tipo": "peste", "niveis": 1, "chance": 1.0}, semente)
        escapou += morto_vivo.peste == 0
    assert escapou > 10


# ---------------- Altar do Queijo ----------------

def test_bencao_do_queijo_vale_em_cada_luta_ate_vencer_o_chefe():
    run = run_no_reino()
    aplicar(run, {"tipo": "ate_o_chefe", "status": [{"status": "fortalecido", "duracao": 2}]})
    for _ in range(2):
        combate = run.criar_combate(EncontroCombate("t", "", 1, ["rato_comum"]))
        assert all(h.tem_status("fortalecido") for h in combate.herois)
    run.encontro = EncontroCombate("Chefe", "", 5, ["aranha_mae"], "chefe")
    combate = run.criar_combate()
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    assert run.efeitos_ate_o_chefe == []


def test_roubar_o_queijo_enfraquece_e_enfurece_o_chefe():
    normal = run_no_reino().criar_combate(EncontroCombate("Chefe", "", 5, ["aranha_mae"], "chefe")).inimigos[0]
    run = run_no_reino()
    aplicar(run, {"tipo": "ajuste_do_chefe", "modificadores": {"vida_percentual": -0.2, "dano_causado": 0.25}})
    chefe = run.criar_combate(EncontroCombate("Chefe", "", 5, ["aranha_mae"], "chefe")).inimigos[0]
    assert chefe.vida_maxima < normal.vida_maxima and chefe.stat("dano_causado") > normal.stat("dano_causado")
    comum = run.criar_combate(EncontroCombate("t", "", 1, ["rato_comum"])).inimigos[0]
    sem_ajuste = run_no_reino()
    sem_ajuste.numero_do_combate = run.numero_do_combate - 1
    comum_normal = sem_ajuste.criar_combate(EncontroCombate("t", "", 1, ["rato_comum"])).inimigos[0]
    assert comum.ajustes == comum_normal.ajustes                                    # só o chefe muda


# ---------------- save e dados ----------------

def test_o_que_fica_guardado_vai_no_save():
    run = run_no_reino()
    run.inimigos_extra_proximo_combate = ["rato_guarda_real"]
    run.efeitos_ate_o_chefe = [{"status": "fortalecido", "duracao": 2}]
    run.ajustes_do_chefe = {"vida_percentual": -0.2}
    copia = Run.de_dict(run.para_dict())
    assert copia.inimigos_extra_proximo_combate == ["rato_guarda_real"]
    assert copia.efeitos_ate_o_chefe == [{"status": "fortalecido", "duracao": 2}]
    assert copia.ajustes_do_chefe == {"vida_percentual": -0.2}


def test_eventos_do_reino_com_sprites_parados_e_requisitos_validos():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for chave in NOVOS:
        ev = evento(chave)
        assert ev.regioes == ["reino_dos_ratos"] and ev.zonas
        if ev.sprite:
            assert ev.parado and sprites.existe(ev.sprite)
        for opcao in ev.opcoes:
            if "item" in opcao.requisito:
                item(opcao.requisito["item"])
    assert len(evento("mercado_do_rato_mercador").opcoes) == 4
