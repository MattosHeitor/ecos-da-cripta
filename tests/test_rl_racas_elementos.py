"""Fase 3, etapa 2: elementos (fraquezas e resistências) e raças (bônus, dons, renascer, forja anã)."""

import glob
import json
import os
import random

import pytest

from roguelike import elementos
from roguelike.classes import criar_heroi, heroi_para_dict, heroi_de_dict
from roguelike.golpes import golpe, todas_as_chaves
from roguelike.inimigos import criar_inimigo
from roguelike.racas import todas_as_racas, raca, PASSIVAS_ANTIGAS

from apoio_roguelike import SorteControlado, combate_pronto, vez_de

PASTA_DADOS = os.path.join(os.path.dirname(__file__), "..", "src", "roguelike", "dados")


def heroi_da_raca(classe, chave_raca, **kw):
    heroi = criar_heroi(classe, **kw)
    heroi.definir_raca(chave_raca)
    heroi.curar_tudo()
    return heroi


# ============================================================
# DADOS
# ============================================================

def test_jsons_nao_tem_chaves_repetidas():
    """Chave repetida no JSON faz a última sobrescrever a primeira sem aviso (já aconteceu com golpes)."""
    def sem_repetir(pares):
        chaves = [k for k, _ in pares]
        repetidas = {k for k in chaves if chaves.count(k) > 1}
        assert not repetidas, f"{arquivo}: {repetidas}"
        return dict(pares)

    for arquivo in glob.glob(os.path.join(PASTA_DADOS, "*.json")):
        with open(arquivo, encoding="utf-8") as f:
            json.load(f, object_pairs_hook=sem_repetir)


def test_todo_golpe_tem_elemento_valido():
    validos = set(elementos.todos())
    for chave in todas_as_chaves():
        g = golpe(chave)
        assert g.elemento in validos, chave
        for efeito in g.efeitos:
            if efeito.dados["tipo"] == "dano":
                assert efeito.elemento == g.elemento


def test_resistencias_usam_familias_e_inimigos_que_existem():
    from roguelike.dados import carregar, sem_comentarios
    fichas = sem_comentarios(carregar("inimigos")["inimigos"])
    familias = {f["familia"] for f in fichas.values()}
    dados = elementos.dados()
    assert set(dados["familias"]) <= familias
    assert set(dados["inimigos"]) <= set(fichas)
    for tabela in list(dados["familias"].values()) + list(dados["inimigos"].values()):
        assert set(tabela) <= set(elementos.todos())


# ============================================================
# ELEMENTOS NO COMBATE
# ============================================================

def test_morto_vivo_e_fraco_a_luz_e_resiste_a_veneno():
    esqueleto = criar_inimigo("esqueleto")
    assert elementos.efetividade(esqueleto, "luz") == "fraco"
    assert elementos.efetividade(esqueleto, "veneno") == "resiste"
    assert elementos.efetividade(esqueleto, "fisico") is None
    fracos, resiste = elementos.fraquezas_e_resistencias(esqueleto)
    assert "luz" in fracos and "veneno" in resiste
    texto = elementos.texto_de_afinidades(fracos, resiste)
    assert texto.startswith("Fraco a: ") and "luz" in texto and "Resiste a: veneno" in texto


def test_golpe_de_fogo_bate_mais_no_fraco_e_menos_no_resistente():
    def dano_de(chave_inimigo, elemento):
        mago = criar_heroi("mago")
        inimigo = criar_inimigo(chave_inimigo)
        combate = combate_pronto([mago], [inimigo])
        inimigo.vida = 9999                               # o dano não é cortado pela vida que sobra
        combate.golpear(mago, inimigo, 40, elemento=elemento, ignora_bloqueio=True)
        evento = [e for e in combate.pegar_eventos() if e.tipo == "dano"][-1]
        return evento.valor, evento.extras["efetividade"]

    fogo, situacao = dano_de("goblin", "fogo")          # goblins: fogo +25%
    assert situacao == "fraco" and fogo > dano_de("goblin", "fisico")[0]
    fogo, situacao = dano_de("dragao", "fogo")          # dragões: fogo -50%
    assert situacao == "resiste" and fogo < dano_de("dragao", "fisico")[0]
    assert dano_de("orc", "raio")[1] is None


def test_queimadura_e_fogo_e_o_veneno_quase_nao_pega_em_morto_vivo():
    from roguelike.status import criar_status
    goblin, esqueleto = criar_inimigo("goblin"), criar_inimigo("carnical")
    combate = combate_pronto([criar_heroi("mago")], [goblin, esqueleto])
    queimadura = criar_status("queimadura", valor=8)
    antes = goblin.vida
    queimadura.inicio_do_turno(goblin, combate)
    assert antes - goblin.vida == 10                    # 8 * 1.25
    evento = [e for e in combate.pegar_eventos() if e.tipo == "dano"][-1]
    assert evento.extras["elemento"] == "fogo" and evento.extras["efetividade"] == "fraco"
    veneno = criar_status("veneno", valor=8)
    antes = esqueleto.vida
    veneno.inicio_do_turno(esqueleto, combate)
    assert antes - esqueleto.vida == 2                  # 8 * 0.25


def test_resumo_do_golpe_mostra_o_elemento():
    assert "dano de fogo" in golpe("bola_de_fogo").resumo()
    assert "de fogo" not in golpe("golpe").resumo()


# ============================================================
# RAÇAS
# ============================================================

def test_ha_nove_racas_e_as_chaves_antigas_continuam():
    chaves = set(todas_as_racas())
    assert len(chaves) == 9
    assert {"humano", "revenante", "hemofago", "anao_das_profundezas", "elfo_sombrio", "meio_orc",
            "gnomo", "draconiano", "meio_demonio"} == chaves
    assert raca("nao_existe").chave == "humano"


def test_toda_raca_com_cosmetico_tem_camada_para_todo_heroi():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    geometrias = {m["geometria"] for m in sprites.catalogo.values() if m.get("geometria") and m["nome"].startswith("camada_")}
    for r in todas_as_racas().values():
        if r.cosmetico:
            for geometria in geometrias:
                assert f"camada_{geometria}_{r.cosmetico}" in sprites.catalogo, (geometria, r.cosmetico)


def test_raca_entra_no_sprite_e_nos_bonus():
    heroi = heroi_da_raca("guerreiro", "anao_das_profundezas")
    assert "+@raca_anao" in heroi.sprite
    humano = criar_heroi("guerreiro")
    assert heroi.stat("defesa") == humano.stat("defesa") + 1
    gnomo = heroi_da_raca("guerreiro", "gnomo")
    assert gnomo.vida_maxima < humano.vida_maxima and gnomo.stat("furtividade") == 0.5


def test_humano_ganha_mais_xp():
    humano = heroi_da_raca("guerreiro", "humano")
    orc = heroi_da_raca("guerreiro", "meio_orc")
    humano.ganhar_xp(5)
    orc.ganhar_xp(5)
    assert humano.xp == 6 and orc.xp == 5


def test_gnomo_e_menos_escolhido_pela_ia():
    from roguelike.ia import IA
    gnomo, humano = heroi_da_raca("ladino", "gnomo"), heroi_da_raca("ladino", "humano")
    goblin = criar_inimigo("goblin")
    assert IA().peso_do_alvo(gnomo, goblin) == pytest.approx(IA().peso_do_alvo(humano, goblin) * 0.5)


def test_morto_vivo_renasce_uma_vez_por_combate():
    heroi = heroi_da_raca("guerreiro", "revenante")
    combate = combate_pronto([heroi, criar_heroi("mago")], [criar_inimigo("goblin")])
    combate.causar_dano(heroi, 999, None)
    assert heroi.esta_vivo() and heroi.vida == round(heroi.vida_maxima * 0.1)
    eventos = combate.pegar_eventos()
    assert any(e.tipo == "reviver" and e.extras.get("renasceu") for e in eventos)
    combate.causar_dano(heroi, 999, None)
    assert not heroi.esta_vivo()                        # a segunda vez fica no chão
    # no combate seguinte renasce de novo
    heroi.vida = heroi.vida_maxima
    combate2 = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate2.causar_dano(heroi, 999, None)
    assert heroi.esta_vivo()


def test_morto_vivo_e_imune_a_veneno_e_sangramento():
    heroi = heroi_da_raca("guerreiro", "revenante")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    assert combate.aplicar_status(heroi, "veneno", 3, 4) is None
    assert combate.aplicar_status(heroi, "sangramento", 3) is None
    assert heroi.imune("veneno") and "sangramento" in heroi.imunidades_atuais()


def test_draconiano_tem_golpe_racial_com_recarga_e_vira_dragao():
    heroi = heroi_da_raca("guerreiro", "draconiano")
    assert "metamorfose_draconica" in [g.chave for g, _ in heroi.habilidades()]
    assert "metamorfose_draconica" not in heroi.golpes.equipados          # fica fora dos espaços
    combate = combate_pronto([heroi], [criar_inimigo("golem")])
    vez_de(combate, heroi)
    heroi.energia = 5
    assert combate.usar_habilidade(heroi, "metamorfose_draconica")
    assert heroi.tem_status("forma_de_dragao") and heroi.sprite_atual() == "dragao_filhote"
    assert heroi.recarga_de("metamorfose_draconica") == 6
    vez_de(combate, heroi)
    heroi.energia = 5
    assert not golpe("metamorfose_draconica").pode_usar(heroi)
    for _ in range(5):
        combate.concentrar(heroi)
        vez_de(combate, heroi)
    assert heroi.recarga_de("metamorfose_draconica") == 0 and golpe("metamorfose_draconica").pode_usar(heroi)
    assert heroi.imune("queimadura")


def test_meio_demonio_pode_amaldicoar_quem_acerta():
    heroi = heroi_da_raca("guerreiro", "meio_demonio")
    alvo = criar_inimigo("orc")
    combate = combate_pronto([heroi], [alvo], rng=SorteControlado(padrao=0.01))   # todas as chances acontecem
    combate.golpear(heroi, alvo, 10, ignora_esquiva=True, ignora_bloqueio=True)
    assert alvo.tem_status("amaldicoado")


def test_meio_orc_entra_em_furia_com_pouca_vida():
    heroi = heroi_da_raca("barbaro", "meio_orc")
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.causar_dano(heroi, int(heroi.vida * 0.7), None)
    assert heroi.tem_status("fortalecido") and heroi.tem_status("inspirado")


def test_elfo_comeca_evasivo():
    heroi = heroi_da_raca("ladino", "elfo_sombrio")
    combate_pronto([heroi], [criar_inimigo("goblin")])
    assert heroi.tem_status("evasivo")


def test_raca_volta_ao_carregar_e_saves_antigos_perdem_as_passivas_velhas():
    heroi = heroi_da_raca("mago", "revenante")
    dados = heroi_para_dict(heroi)
    dados["passivas_extras"] = list(PASSIVAS_ANTIGAS[2:4]) + [{"tipo": "bonus", "modificadores": {"sorte": 1}, "nome": "Bênção"}]
    carregado = heroi_de_dict(dados)
    assert carregado.raca == "revenante" and carregado.dados_da_raca is raca("revenante")
    assert [p["nome"] for p in carregado.passivas_extras] == ["Bênção"]
    assert any(type(p).__name__ == "PassivaRenascer" for p in carregado.passivas)
    assert "+@raca_morto_vivo" in carregado.sprite


# ============================================================
# GNOMO (LOOT) E ANÃO (FORJA)
# ============================================================

def nova_run(racas_dos_herois):
    from roguelike.run import Run
    herois = []
    for chave_raca in racas_dos_herois:
        herois.append(heroi_da_raca("guerreiro", chave_raca))
    return Run(herois, "RACAS")


def test_gnomo_acha_itens_extras():
    """O dom de loot do gnomo dá chance de prêmios a mais ao dono dele (gerador_de_loot.py)."""
    from roguelike.gerador_de_loot import GeradorDeLoot
    gnomos, humanos = nova_run(["gnomo", "gnomo"]), nova_run(["humano", "humano"])
    extras = [GeradorDeLoot(gnomos).premios_do_dono(gnomos.grupo.herois, random.Random(s)) for s in range(40)]
    assert sum(1 for e in extras if e) >= 10
    assert not any(GeradorDeLoot(humanos).premios_do_dono(humanos.grupo.herois, random.Random(s)) for s in range(40))


def test_so_o_anao_forja_os_lendarios_anoes():
    exclusivas = {"machado_runico", "martelo_trovejante", "placas_do_juramento", "anel_da_montanha",
                  "lanterna_das_profundezas"}
    sem_anao = nova_run(["humano"])
    com_anao = nova_run(["humano", "anao_das_profundezas"])
    assert not exclusivas & {r.chave for r in sem_anao.receitas_visiveis()}
    assert exclusivas <= {r.chave for r in com_anao.receitas_visiveis()}
    for run in (sem_anao, com_anao):
        run.grupo.bau.adicionar("ferro_negro", 3)
        run.grupo.bau.adicionar("pedra_runica", 3)
        run.grupo.bau.adicionar("nucleo_runico", 1)
    assert not sem_anao.fabricar("machado_runico")
    assert com_anao.fabricar("machado_runico") and com_anao.grupo.bau.tem("machado_runico")
    from roguelike.itens import item
    assert item("machado_runico").raridade == "lendario"


def test_texto_dos_modificadores_de_elemento():
    from roguelike.progresso import texto_de_modificador
    assert texto_de_modificador("dano_causado_raio", 0.25) == "+25% de dano de raio"
    assert texto_de_modificador("dano_recebido_fogo", -0.3) == "-30% de dano de fogo recebido"
