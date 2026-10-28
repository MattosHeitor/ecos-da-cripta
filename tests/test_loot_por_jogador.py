"""MP3: loot por jogador (roguelike/gerador_de_loot.py), prêmios de evento e a janela de recompensas.

Critérios de aceite: em várias batalhas, cada jogador recebe a mesma quantidade de prêmios e itens diferentes;
todos ganham um lendário no chefe.
"""

import os
import random
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from roguelike.classes import criar_heroi
from roguelike.dados import regras
from roguelike.encontros import EncontroCombate
from roguelike.gerador_de_loot import GeradorDeLoot, menor_tier, pecas_da_raridade
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.posse import Jogador
from roguelike.run import Run


def run_de_dois(classes_a=("guerreiro", "sacerdote"), classes_b=("mago", "patrulheira"), semente="LOOT"):
    """Dois jogadores: o local com classes_a e a Bia com classes_b."""
    herois = [criar_heroi(c) for c in classes_a + classes_b]
    run = Run(herois, semente)
    bia = Jogador("bia", "Bia")
    for heroi in herois[len(classes_a):]:
        run.grupo.dar_heroi(heroi, bia)
    return run


def combate_vencido(inimigos=("goblin", "goblin", "aranha")):
    return SimpleNamespace(derrotados=[criar_inimigo(c) for c in inimigos])


def loot(run, categoria="combate", estrelas=2, semente=1, inimigos=("goblin", "goblin", "aranha")):
    gerador = GeradorDeLoot(run)
    encontro = SimpleNamespace(tipo=categoria, estrelas=estrelas)
    return gerador.do_combate(combate_vencido(inimigos), encontro, random.Random(semente)), gerador.contagem


def pecas(itens):
    return [c for c in itens if item(c).tipo == "equipamento"]


# ---------------- a mesma quantidade, itens diferentes ----------------
@pytest.mark.parametrize("categoria", ["combate", "horda", "elite", "nomeado", "mini_chefe", "chefe"])
def test_mesma_quantidade_e_itens_diferentes_em_varias_batalhas(categoria):
    run = run_de_dois()
    iguais = 0
    for semente in range(25):
        por_jogador, contagem = loot(run, categoria, estrelas=3, semente=semente)
        assert set(por_jogador) == {"local", "bia"}
        assert contagem["local"] == contagem["bia"] > 0                  # mesmos heróis: mesma quantidade
        assert not set(pecas(por_jogador["local"])) & set(pecas(por_jogador["bia"]))   # nenhuma peça repetida
        iguais += por_jogador["local"] == por_jogador["bia"]
    assert iguais == 0                                                    # cada um sorteia o seu


def test_a_quantidade_segue_a_regra_do_json():
    run = run_de_dois(("guerreiro",), ("mago", "patrulheira"))
    premios = regras()["loot"]["premios"]
    _, contagem = loot(run, "combate", estrelas=3)
    esperado = lambda herois: int(premios["por_jogador"] + premios["por_heroi"] * herois + premios["por_estrela"] * 2)  # noqa: E731
    assert contagem["local"] == esperado(1) and contagem["bia"] == esperado(2)       # cota por herói


def test_todo_jogador_ganha_um_lendario_no_chefe_a_partir_do_ato_2():
    run = run_de_dois()
    run.regiao_atual = "minas"
    assert run.regiao.tier == 2 and menor_tier("lendario") > 2                # (lendárias só existem no tier 3)
    for semente in range(10):
        por_jogador, _ = loot(run, "chefe", estrelas=5, semente=semente, inimigos=("golem_carregando",))
        lendarias = {j: [c for c in pecas(itens) if item(c).raridade == "lendario"] for j, itens in por_jogador.items()}
        assert all(lendarias.values()), lendarias
        assert not set(lendarias["local"]) & set(lendarias["bia"])       # cada um a sua


def test_no_chefe_do_ato_1_a_garantida_e_epica_e_as_vezes_lendaria():
    """Lendária (tier 3) já no Ato I dobrava as vitórias do piloto: no tier 1 a garantida é épica (25% lendária)."""
    run = run_de_dois()
    assert run.regiao.tier == 1
    lendarias = 0
    for semente in range(40):
        por_jogador, _ = loot(run, "chefe", estrelas=5, semente=semente, inimigos=("aranha_mae",))
        for itens in por_jogador.values():
            raridades = [item(c).raridade for c in pecas(itens)]
            assert "epico" in raridades or "lendario" in raridades
            lendarias += "lendario" in raridades
    assert 0 < lendarias < 80


def test_mini_chefe_garante_epica_ou_lendaria_a_todos():
    run = run_de_dois()
    for semente in range(10):
        por_jogador, _ = loot(run, "mini_chefe", estrelas=5, semente=semente, inimigos=("orc_senhor_da_guerra",))
        for itens in por_jogador.values():
            assert any(item(c).raridade in ("epico", "lendario") for c in pecas(itens))


def test_linhas_garantidas_vao_para_todos():
    run = run_de_dois()
    por_jogador, _ = loot(run, "chefe", estrelas=5, inimigos=("aranha_mae",))
    assert all(itens.get("alma_da_mae_aranha") == 1 for itens in por_jogador.values())


def test_mesmo_combate_mesmo_loot():
    run = run_de_dois()
    assert loot(run, semente=7)[0] == loot(run, semente=7)[0]
    assert loot(run, semente=7)[0] != loot(run, semente=8)[0]


def test_pecas_preferem_quem_ajuda_os_herois_do_jogador():
    run = run_de_dois(("guerreiro",), ("mago",))
    gerador, rng = GeradorDeLoot(run), random.Random(3)
    guerreiro, mago = run.grupo.herois_de(run.grupo.jogador("local")), run.grupo.herois_de(run.grupo.jogador("bia"))

    def com(atributo, herois):
        return sum(atributo in item(gerador.peca(rng, herois)).modificadores for _ in range(600))

    assert com("forca", guerreiro) > com("forca", mago)
    assert com("inteligencia", mago) > com("inteligencia", guerreiro)


def test_peca_garantida_vem_do_tier_mais_baixo_em_que_a_raridade_existe():
    run = run_de_dois()
    gerador = GeradorDeLoot(run)
    epica = item(gerador.peca(random.Random(1), run.grupo.herois, exata="epico"))
    assert epica.raridade == "epico" and epica.tier == menor_tier("epico")
    assert all(p.tier >= 1 for p in pecas_da_raridade("lendario"))     # (as anãs e as almas, tier 0, não entram)


def test_gnomo_e_loot_extra_sao_do_dono():
    run = run_de_dois(("guerreiro", "sacerdote"), ("mago", "patrulheira"))
    bia = run.grupo.herois_de(run.grupo.jogador("bia"))
    bia[0].definir_raca("gnomo")
    gerador = GeradorDeLoot(run)
    extras_bia = sum(gerador.premios_do_dono(bia, random.Random(s)) for s in range(60))
    extras_local = sum(gerador.premios_do_dono(run.grupo.herois_de(run.grupo.jogador("local")), random.Random(s))
                       for s in range(60))
    assert extras_bia > 0 and extras_local == 0


# ---------------- na run ----------------
def vencer(run, encontro):
    run.encontro = encontro
    combate = run.criar_combate(encontro)
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    return run.concluir_combate(combate)


def test_recompensa_separada_por_jogador_e_a_soma():
    run = run_de_dois()
    recompensa = vencer(run, EncontroCombate("t", "", 2, ["goblin", "aranha"]))
    assert set(recompensa.por_jogador) == {"local", "bia"} and recompensa.premios["local"] == recompensa.premios["bia"]
    soma = {}
    for itens in recompensa.por_jogador.values():
        for chave, n in itens.items():
            soma[chave] = soma.get(chave, 0) + n
    assert recompensa.itens == soma
    for jogador, itens in recompensa.por_jogador.items():              # MP4: na mochila de cada um
        mochila = run.grupo.jogador(jogador).mochila
        assert all(mochila.tem(c, n) for c, n in itens.items())
    assert recompensa.no_bau == {}


def test_no_solo_e_um_jogador_so():
    run = Run([criar_heroi("guerreiro"), criar_heroi("sacerdote")], "SOLO")
    recompensa = vencer(run, EncontroCombate("t", "", 2, ["goblin", "aranha"]))
    assert list(recompensa.por_jogador) == ["local"] and recompensa.itens == recompensa.por_jogador["local"]


# ---------------- eventos ----------------
def test_premio_de_evento_e_de_cada_jogador():
    from roguelike.eventos_run import ResultadoEvento, criar_consequencia
    run = run_de_dois()
    resultado = ResultadoEvento()
    criar_consequencia({"tipo": "premio", "por_jogador": 1, "por_heroi": 2, "chance_de_equipamento": 0.5,
                        "raridade_minima": "raro", "chance_de_lendario": 1.0}).aplicar(run, random.Random(2), resultado)
    assert set(resultado.por_jogador) == {"local", "bia"}
    for itens in resultado.por_jogador.values():
        assert any(item(c).raridade == "lendario" for c in pecas(itens))
        assert all(item(c).raridade in ("raro", "epico", "lendario", "amaldicoado") for c in pecas(itens))
    assert any("Bia recebeu:" in t for t in resultado.textos) and any("Você recebeu:" in t for t in resultado.textos)


def test_item_de_evento_vai_para_cada_jogador():
    from roguelike.eventos_run import ResultadoEvento, criar_consequencia
    run = run_de_dois()
    resultado = ResultadoEvento()
    criar_consequencia({"tipo": "item", "chave": "osso", "quantidade": 2}).aplicar(run, random.Random(1), resultado)
    assert resultado.por_jogador == {"local": {"osso": 2}, "bia": {"osso": 2}}
    aleatorio = ResultadoEvento()
    criar_consequencia({"tipo": "item_aleatorio", "raridade": "raro", "item_tipo": "equipamento"}).aplicar(
        run, random.Random(1), aleatorio)
    assert set(aleatorio.por_jogador) == {"local", "bia"}


def test_o_que_o_evento_deu_fica_numa_frase_so():
    """Item da opção + prêmio: um "Recebeu: ..." só, com tudo (e não uma frase por consequência)."""
    from roguelike.eventos_run import evento
    run = Run([criar_heroi("guerreiro")], "FRASE")
    resultado = evento("altar_esquecido").escolher(1, run, random.Random(1))       # ouro + prêmio + maldição
    resultado2 = evento("bau_trancado").escolher(0, run, random.Random(5))
    for r in (resultado, resultado2):
        assert sum(t.count("Recebeu:") for t in r.textos) <= 1
    assert any("Recebeu:" in t for t in resultado.textos)


def test_todo_premio_dos_eventos_e_valido():
    """Todo "premio" do eventos.json abre (raridades e itens existem) e dá algo a cada jogador."""
    from roguelike.eventos_run import Premio, ResultadoEvento, todos_os_eventos

    def premios(efeitos):
        for efeito in efeitos:
            if isinstance(efeito, Premio):
                yield efeito
            for lado in ("sucesso", "falha", "premio"):
                from roguelike.eventos_run import criar_consequencia
                yield from premios([criar_consequencia(d) for d in efeito.dados.get(lado, []) if isinstance(d, dict)])

    run = run_de_dois()
    vistos = 0
    for evento in todos_os_eventos().values():
        for opcao in evento.opcoes:
            for premio in premios(opcao.consequencias):
                resultado = ResultadoEvento()
                premio.aplicar(run, random.Random(vistos), resultado)
                vistos += 1
                if premio.dados.get("por_heroi") or premio.dados.get("por_jogador"):
                    assert all(resultado.por_jogador.get(j) for j in ("local", "bia")), (evento.chave, premio.dados)
    assert vistos >= 15


# ---------------- a janela ----------------
def test_janela_de_recompensas_tem_uma_aba_por_jogador():
    from telas.combate.recompensas import PainelDeRecompensas
    run = run_de_dois()
    recompensa = vencer(run, EncontroCombate("t", "", 2, ["goblin", "aranha"]))
    painel = PainelDeRecompensas(recompensa, run.grupo.jogadores, local="bia")
    assert painel.varios and [n for _, n in painel.jogadores] == ["Bia", "Você"]       # quem joga aqui primeiro
    assert painel.itens_da_aba() == recompensa.por_jogador["bia"]
    painel.trocar_aba(1)
    assert painel.itens_da_aba() == recompensa.por_jogador["local"]
    solo = Run([criar_heroi("guerreiro")], "SOLO")
    assert not PainelDeRecompensas(vencer(solo, EncontroCombate("t", "", 1, ["goblin"])), solo.grupo.jogadores).varios
