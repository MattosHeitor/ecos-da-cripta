"""Reino dos Ratos, etapa 7A: materiais do Reino (e de onde caem), receitas (as melhores na forja anã), consumíveis
(Veneno de Rato, Sais de Cheiro, Ratoeira, Vela de Sebo) e itens avulsos (Pingente do Nó de Caudas, Machado do
Carrasco, Lança de Agulha, Escudo de Tampa de Lata, Botas de Esgoto, Capuz de Trapos, Rato de Estimação)."""

import json
import os
import random

from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.dados import carregar, sem_comentarios
from roguelike.fabricacao import todas_as_receitas, receitas_reveladas_por
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAIS = ["pelo_sarnento", "dente_amarelo", "cauda_atada", "bubao_seco", "tampinha_dourada", "naco_de_queijo_real",
             "moeda_do_esgoto", "pena_do_xama", "no_de_caudas"]
CONSUMIVEIS = ["veneno_de_rato", "sais_de_cheiro", "ratoeira", "vela_de_sebo"]
PECAS = ["pingente_do_no_de_caudas", "machado_do_carrasco", "lanca_de_agulha", "escudo_de_tampa_de_lata", "botas_de_esgoto",
         "capuz_de_trapos", "rato_de_estimacao"]


def fontes_de(chave):
    loot = sem_comentarios(carregar("loot")["inimigos"])
    return {inimigo for inimigo, linhas in loot.items() if any(l["item"] == chave for l in linhas)}


def test_materiais_caem_no_reino_e_o_no_so_da_rainha():
    for chave in MATERIAIS:
        assert item(chave).tier == 0 and fontes_de(chave), chave
    assert fontes_de("no_de_caudas") == {"rainha_dos_ratos"}
    assert fontes_de("naco_de_queijo_real") == {"rei_dos_ratos", "queijo_real"}
    for chave in CONSUMIVEIS:
        assert chave in [c["item"] for c in carregar("regioes")["regioes"]["reino_dos_ratos"]["consumiveis_da_area"]]


def test_receitas_do_reino_e_da_forja_ana():
    receitas = todas_as_receitas()
    for chave in CONSUMIVEIS + PECAS:
        assert chave in receitas and receitas[chave].escondida, chave
    assert "veneno_de_rato" in receitas_reveladas_por("bubao_seco")
    for chave in ("machado_do_carrasco", "pingente_do_no_de_caudas"):
        assert receitas[chave].requer_raca == "anao_das_profundezas"
        assert not receitas[chave].liberada_para({"humano"}) and receitas[chave].liberada_para({"anao_das_profundezas"})


def combate(herois=None, inimigos=None):
    herois = herois or [criar_heroi("guerreiro"), criar_heroi("sacerdote")]
    inimigos = inimigos or [criar_inimigo("rato_comum"), criar_inimigo("goblin")]
    c = Combate(herois, inimigos, random.Random(7))
    c.iniciar()
    return c


def test_consumiveis_do_reino():
    c = combate()
    guerreiro, sacerdote = c.herois
    rato, goblin = c.inimigos
    efeito = item("veneno_de_rato").efeitos[0]
    assert efeito.dados["bonus_contra_natureza"] == {"pestes": 2.0} and "triplo" in efeito.resumo()
    assert efeito.bonus_contra_natureza(rato) == 2.0 and efeito.bonus_contra_natureza(goblin) == 0.0
    c.aplicar_efeitos(sacerdote, item("ratoeira").efeitos, [goblin], 1)
    assert not goblin.tem_status("atordoado")                                     # só pestes
    c.aplicar_efeitos(sacerdote, item("ratoeira").efeitos, [rato], 1)
    assert rato.tem_status("atordoado") or rato.imune("atordoado")
    c.aplicar_status(guerreiro, "atordoado")
    c.aplicar_status(guerreiro, "encantado")
    c.aplicar_efeitos(sacerdote, item("sais_de_cheiro").efeitos, [guerreiro], 1)
    assert not guerreiro.tem_status("atordoado") and not guerreiro.tem_status("encantado")
    c.aplicar_efeitos(sacerdote, item("vela_de_sebo").efeitos, [guerreiro], 1)
    assert guerreiro.tem_status("iluminado")


def test_machado_dobra_o_dano_em_quem_esta_quase_morto_e_a_lanca_fura_a_defesa():
    machado = criar_heroi("guerreiro")
    machado.equipar(item("machado_do_carrasco"))
    assert machado.bonus("dano_vida_baixa") == 1.0
    alvo = criar_inimigo("orc")
    c = combate([machado], [alvo])
    alvo.ajustes["defesa"] = -alvo.stat("defesa")                                 # sem defesa: o dano fica limpo
    alvo.ajustes["vida_maxima"] = alvo.ajustes.get("vida_maxima", 0) + 1000        # (a vida que sobra não limita o golpe)
    alvo.curar_tudo()
    c.rng = random.Random(1)
    machado.ajustes["chance_critico"] = -1
    alvo.ajustes["chance_esquiva"] = -1
    alvo.ajustes["chance_bloqueio"] = -1
    cheio = c.golpear(machado, alvo, 10).dano
    alvo.vida = round(alvo.vida_maxima * 0.2)
    baixo = c.golpear(machado, alvo, 10).dano
    assert baixo == 2 * cheio
    lanca = criar_heroi("guerreiro")
    lanca.equipar(item("lanca_de_agulha"))
    assert lanca.bonus("penetracao") == 2


def test_botas_de_esgoto_na_agua_alta_e_rato_de_estimacao():
    from roguelike.ambiente import criar_ambientes
    botas, outro = criar_heroi("guerreiro"), criar_heroi("sacerdote")
    botas.equipar(item("botas_de_esgoto"))
    c = Combate([botas, outro], [criar_inimigo("rato_comum")], random.Random(2))
    c.ambientes = criar_ambientes([{"tipo": "agua", "nivel_inicial": 3}])
    c.iniciar()
    c.nova_rodada()
    assert outro.tem_status("encharcado") and not botas.tem_status("encharcado")
    assert not any(e.tipo == "resistiu" and e.alvo is botas for e in c.eventos)    # (sem "Resistiu!" toda rodada)
    dono = criar_heroi("bardo")
    dono.equipar(item("rato_de_estimacao"))
    assert dono.bonus("loot_extra") == 0.15


def test_pingente_mais_forte_com_o_grupo_e_furioso_quando_um_cai():
    dono, a, b = criar_heroi("guerreiro"), criar_heroi("sacerdote"), criar_heroi("mago")
    dono.equipar(item("pingente_do_no_de_caudas"))
    c = combate([dono, a, b], [criar_inimigo("goblin")])
    laco = next(p for p in dono.passivas if p.dados.get("tipo") == "matilha")
    assert abs(laco.modificadores(dono)["dano_causado"] - 0.08) < 1e-9              # 2 aliados vivos
    c.causar_dano(a, 99999, c.inimigos[0])
    assert dono.tem_status("fortalecido") and abs(laco.modificadores(dono)["dano_causado"] - 0.04) < 1e-9


def test_visual_e_icone_de_toda_peca_nova():
    visuais = sem_comentarios(carregar("visual_equipamentos")["pecas"])
    for chave in MATERIAIS + CONSUMIVEIS + PECAS:
        assert os.path.exists(os.path.join(RAIZ, "assets", "itens_macabros", chave + ".png")), chave
    for chave in PECAS:
        assert chave in visuais, chave
    assert visuais["rato_de_estimacao"]["tipo"] == "rato_no_ombro"
    with open(os.path.join(RAIZ, "assets", "sprites_macabros", "catalogo.json"), encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)
    geometrias = {m["geometria"] for nome, m in catalogo.items() if nome.startswith("camada_") and "geometria" in m}
    for geometria in geometrias:
        assert f"camada_{geometria}_eq_rato_no_ombro" in catalogo, geometria
