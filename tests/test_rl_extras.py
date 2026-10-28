"""Fase 4, etapa 8: chefes secretos, elites douradas, provisões do Taverneiro, loja do Mascarado, lore e receitas."""

from roguelike import encontros
from roguelike.bestiario import Pagina, secoes
from roguelike.dados import regras
from roguelike.encontros import EncontroCombate, GeradorDeEncontros
from roguelike.fabricacao import todas_as_receitas
from roguelike.inimigos import fichas
from roguelike.itens import item, todos_os_itens
from roguelike.piloto_automatico import grupo_padrao
from roguelike.progresso import Progresso
from roguelike.regioes import chefes_secretos

from test_rl_run import run_de_teste


def secretos_garantidos(monkeypatch):
    """Todos os chefes secretos com 100% de chance (o resto das regras fica igual)."""
    certos = {c: {**d, "chance": 1.0} for c, d in chefes_secretos().items()}
    monkeypatch.setattr(encontros, "chefes_secretos", lambda: certos)


def test_mercador_mascarado_aparece_no_meio_do_caminho(monkeypatch):
    secretos_garantidos(monkeypatch)
    run = run_de_teste()
    run.regiao_atual, run.area = "pantano_dos_afogados", 3
    opcoes = GeradorDeEncontros(run, run.rng("teste")).gerar()
    secreto = [o for o in opcoes if o.tipo == "secreto"]
    assert secreto and secreto[0].inimigos == ["mercador_mascarado"]
    run.regiao_atual, run.area = "floresta", 3                          # Ato I: não aparece
    assert not [o for o in GeradorDeEncontros(run, run.rng("teste")).gerar() if o.tipo == "secreto"]


def test_primeiro_heroi_so_com_os_dois_finais_vencidos(monkeypatch):
    secretos_garantidos(monkeypatch)
    run = run_de_teste()
    run.regiao_atual = "catedral"
    run.area = run.areas_da_regiao()
    assert [o.tipo for o in GeradorDeEncontros(run, run.rng("t")).gerar()] == ["chefe"]
    run.conquistas_permanentes = {"chefe:dragao_osseo", "chefe:bispo_eclipsado"}
    opcoes = GeradorDeEncontros(run, run.rng("t")).gerar()
    assert [o.tipo for o in opcoes] == ["chefe", "secreto"] and opcoes[1].inimigos == ["primeiro_heroi"]


def test_vencer_o_primeiro_heroi_tambem_vence_a_run():
    run = run_de_teste()
    run.regiao_atual = "catedral_do_eclipse"
    run.area = run.areas_da_regiao()
    run.opcoes = [EncontroCombate("O Primeiro Herói", "", 5, ["primeiro_heroi"], "secreto")]
    run.escolher(0)
    combate = run.criar_combate()
    for _ in range(4):
        for inimigo in list(combate.inimigos):
            combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    recompensa = run.concluir_combate(combate)
    run.concluir_encontro()
    assert run.resultado == "vitoria"
    assert any(c.split("#")[0] == "estandarte_do_primeiro_heroi" for c in recompensa.itens)       # (lendário vem com afixos)
    assert "primeiro_heroi" in run.estatisticas["chefes"]


def test_elite_dourada_e_mais_forte_e_da_equipamento(monkeypatch):
    monkeypatch.setitem(regras()["dourados"], "chance", 1.0)
    run = run_de_teste()
    run.area = 3
    run.opcoes = [EncontroCombate("t", "", 1, ["goblin"], "combate")]
    run.escolher(0)
    normal = run_de_teste().criar_combate(EncontroCombate("t", "", 1, ["goblin"], "combate")).inimigos[0]
    combate = run.criar_combate()
    dourado = combate.inimigos[0]
    assert dourado.dourado and dourado.vida_maxima > normal.vida_maxima
    combate.causar_dano(dourado, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    recompensa = run.concluir_combate(combate)
    raridades = regras()["dourados"]["raridades"]
    assert any(todos_os_itens().get(c.split("#")[0]) is not None and item(c).raridade in raridades
               and item(c).tipo != "consumivel" for c in recompensa.itens)


def test_mapa_rasgado_troca_os_caminhos():
    run = run_de_teste()
    run.area = 2
    antes = [o.nome for o in run.opcoes_de_encontro()]
    run.grupo.bau.adicionar("mapa_rasgado", 3)
    trocou = False
    for _ in range(3):
        assert run.usar_fora_do_combate("mapa_rasgado", run.grupo.bau, run.grupo.herois[0])
        trocou = trocou or [o.nome for o in run.opcoes] != antes
    assert trocou and not run.grupo.bau.tem("mapa_rasgado")
    run.area = run.areas_da_regiao()                                   # no chefe não vale
    run.opcoes = None
    run.grupo.bau.adicionar("mapa_rasgado")
    assert not run.usar_fora_do_combate("mapa_rasgado", run.grupo.bau, run.grupo.herois[0])


def test_incenso_amedronta_o_proximo_combate_e_nao_se_usa_em_combate():
    run = run_de_teste()
    run.grupo.bau.adicionar("incenso")
    assert not item("incenso").usavel_em_combate
    assert run.usar_fora_do_combate("incenso", run.grupo.bau, run.grupo.herois[0])
    combate = run.criar_combate(EncontroCombate("t", "", 1, ["goblin"], "combate"))
    assert combate.inimigos[0].tem_status("amedrontado")


def test_ensopado_cura_o_grupo_todo():
    run = run_de_teste()
    for heroi in run.grupo.herois:
        heroi.vida -= 10
    run.grupo.bau.adicionar("ensopado_da_taverna")
    assert run.usar_fora_do_combate("ensopado_da_taverna", run.grupo.bau, run.grupo.herois[0])
    assert all(h.vida > h.vida_maxima - 10 for h in run.grupo.herois)


def test_loja_do_mascarado_so_abre_depois_de_vence_lo():
    progresso = Progresso()
    progresso.brasas = 500
    assert not progresso.comprar_provisao("vitral_partido", "mascarado")
    progresso.conquistas.add("chefe:mercador_mascarado")
    for _ in range(3):
        progresso.comprar_provisao("vitral_partido", "mascarado")
    assert progresso.provisoes == {"vitral_partido": 2}                  # máximo 2 desta loja
    assert progresso.comprar_provisao("incenso")                          # a outra loja conta à parte
    run = progresso.criar_run(grupo_padrao(("guerreiro",)), "MASCARA")
    assert run.grupo.herois[0].inventario.quantidade("vitral_partido") == 2      # (na mochila de quem comprou)
    assert "chefe:mercador_mascarado" in run.conquistas_permanentes


def test_todo_chefe_tem_lore_e_os_secretos_tem_secao():
    chefes = [c for c, f in fichas().items() if f.get("categoria") == "chefe"]
    progresso = Progresso()
    for chave in chefes:
        progresso.abates[chave] = 1
        assert Pagina(chave, progresso).lore(), chave
    assert Pagina("bispo_eclipsado", Progresso()).lore() is None             # só depois de vencer
    segredos = next(lista for chave, _, lista in secoes() if chave == "segredos")
    assert set(segredos) == {"mercador_mascarado", "primeiro_heroi"}


def test_materiais_das_fases_novas_viram_receitas():
    usados = set()
    for receita in todas_as_receitas().values():
        usados |= set(receita.ingredientes)
    novos = ["presa_de_lobo", "seiva_viva", "lodo_negro", "escama_de_afogado", "moeda_do_barqueiro", "osso_consagrado",
             "ferro_de_cruzada", "fragmento_de_reliquia", "minerio_de_brasa", "cristal_glacial", "pele_de_lobo_espectral",
             "lagrima_congelada", "vitral_partido", "cinza_do_eclipse", "coracao_do_eclipse"]
    assert set(novos) <= usados
