"""Fase 4, etapa 1: fases (regiões) em atos, tamanho sorteado, portões, noite, pesos e drops da área."""

import random

from roguelike.encontros import GeradorDeEncontros, MontadorDeCombate
from roguelike.inimigos import ficha
from roguelike.itens import item
from roguelike.loja import Alquimista
from roguelike.piloto_automatico import grupo_padrao
from roguelike.regioes import Regiao, regiao, todas_as_regioes, progressao
from roguelike.run import Run


def nova_run(semente="ATOS1"):
    return Run(grupo_padrao(("guerreiro", "sacerdote")), semente=semente)


def fase_de_teste(**extras):
    dados = {"nome": "Teste", "areas": 6, "tier": 1, "inimigos": ["goblin"], "chefe": "aranha_mae"}
    dados.update(extras)
    return Regiao("teste", dados)


# ---------------- dados ----------------

def test_toda_fase_dos_atos_existe_e_tem_titulo():
    for ato in progressao().atos:
        for chave in ato.fases:
            fase = regiao(chave)
            assert fase.ato == ato.indice and fase.titulo and fase.musica
    assert regiao("circo").ato is None                      # o Circo continua como passagem que volta
    assert regiao("catedral").final and regiao("catedral_do_eclipse").final
    assert "enxame" in progressao().atos[-1].secretos       # vaga do destino secreto (desligada)


def test_fases_novas_prontas_ou_seladas_com_cenario_provisorio_e_itens_validos():
    novas = ["bosque_carmesim", "pantano_dos_afogados", "minas_de_brasa", "catacumbas_da_ordem_caida",
             "cidadela_congelada", "catedral_do_eclipse"]
    from visual.cenario_macabro import catalogo
    for chave in novas:
        fase = regiao(chave)
        if fase.disponivel:                               # pronta: arte própria, chefe e inimigos
            assert f"{fase.cenario}_0" in catalogo() and fase.chefe and fase.inimigos, chave
            assert fase.sala_do_chefe and f"{fase.sala_do_chefe}_0" in catalogo(), chave
        else:                                             # selada: cenário provisório tingido
            assert fase.cenario_provisorio and fase.paleta.get("tom"), chave
    for fase in todas_as_regioes().values():
        for drop in fase.drops_da_area + fase.consumiveis_da_area:
            item(drop["item"])
    # nada do que existia mudou
    assert [regiao(c).chefe for c in ("floresta", "minas", "catedral", "circo")] == \
           ["aranha_mae", "golem_carregando", "dragao_osseo", "rei_sombrio"]


# ---------------- tamanho sorteado ----------------

def test_fases_tem_de_10_a_15_areas_ate_as_finais():
    """Etapa 8: todas as fases (antes 4 a 8, e 3 nas finais) sorteiam de 10 a 15 áreas."""
    tamanhos = set()
    for i in range(60):
        run = nova_run(f"T{i}")
        for chave in ("floresta", "minas", "circo", "catedral", "catedral_do_eclipse"):
            assert 10 <= run.areas_da_regiao(chave) <= 15
            tamanhos.add(run.areas_da_regiao(chave))
    assert tamanhos == set(range(10, 16))
    assert nova_run("IGUAL").areas_da_regiao("floresta") == nova_run("IGUAL").areas_da_regiao("floresta")


def test_ultima_area_sorteada_e_o_chefe_e_a_anterior_prepara():
    run = nova_run()
    total = run.areas_da_regiao()
    run.area = total - 1
    assert any(o.tipo in ("descanso", "loja", "alquimista") for o in run.opcoes_de_encontro())
    run.area, run.opcoes = total, None
    assert [o.tipo for o in run.opcoes_de_encontro()] == ["chefe"]


def test_passagens_contam_no_tamanho_original():
    catedral = regiao("catedral")
    assert [catedral.area_original(a, 3) for a in (1, 2, 3)] == [4, 8, 12]
    assert regiao("floresta").area_original(5) == 5


# ---------------- começo e portões ----------------

def test_fase_inicial_sorteada_entre_as_disponiveis(monkeypatch):
    assert {nova_run(f"I{i}").regiao_atual for i in range(30)} == {"floresta", "bosque_carmesim"}
    monkeypatch.setattr(regiao("bosque_carmesim"), "disponivel", False)
    assert {nova_run(f"I{i}").regiao_atual for i in range(10)} == {"floresta"}


def test_portoes_mostram_as_abertas_primeiro_e_completam_com_seladas(monkeypatch):
    ato2 = progressao().atos[1]
    for chave in ato2.fases[1:]:                          # só as Minas abertas
        monkeypatch.setattr(regiao(chave), "disponivel", False)
    portoes = progressao().portoes(ato2, random.Random(3))
    assert len(portoes) == 2 and ("minas", True) in portoes and sum(1 for _, a in portoes if a) == 1
    for chave in ato2.fases:
        monkeypatch.setattr(regiao(chave), "disponivel", True)
    portoes = progressao().portoes(ato2, random.Random(3))
    assert len(portoes) == 2 and all(aberta for _, aberta in portoes)


def test_ato_sem_fase_disponivel_e_pulado(monkeypatch):
    assert progressao().proximo_ato(1).nome == "Ato III"
    for chave in progressao().atos[2].fases:                      # sem nenhuma fase pronta, o ato é pulado
        monkeypatch.setattr(regiao(chave), "disponivel", False)
    assert progressao().proximo_ato(1).nome == "Ato Final"
    assert progressao().proximo_ato(0).nome == "Ato II"
    assert progressao().proximo_ato(3) is None


def test_portao_selado_nao_pode_ser_escolhido():
    run = nova_run()
    run.portoes = [["pantano_dos_afogados", False], ["minas", True]]
    opcoes = run.opcoes_de_encontro()
    assert opcoes[0].bloqueado and run.escolher(0) is None and run.estado == "escolha"
    assert run.escolher(1) is opcoes[1]
    run.concluir_encontro()
    assert run.regiao_atual == "minas" and run.area == 1


def test_destino_secreto_so_abre_com_os_marcos(monkeypatch):
    final = progressao().atos[-1]
    assert final.secretos_abertos(["chefe:aranha_mae"]) == []      # "enxame" está desligado e ainda não existe
    monkeypatch.setattr(final, "secretos", {"circo": {"ativo": True, "marcos": ["chefe:aranha_mae"]}})
    assert final.secretos_abertos([]) == []
    assert final.secretos_abertos(["chefe:aranha_mae"]) == ["circo"]
    portoes = progressao().portoes(final, random.Random(1), ["chefe:aranha_mae"])
    assert ("circo", True) in portoes


def test_gerador_nao_oferece_passagem_para_fase_de_ato():
    run = nova_run()
    for area in range(1, run.areas_da_regiao()):
        for semente in range(15):
            run.area = area
            gerador = GeradorDeEncontros(run, random.Random(semente))
            assert all(o.tipo != "entrada" for o in gerador.gerar())        # Floresta -> Minas virou portão


def test_save_guarda_tamanhos_e_portoes(tmp_path):
    run = nova_run()
    run.areas_da_regiao()
    run.portoes = [["minas", True], ["minas_de_brasa", False]]
    run.opcoes_de_encontro()
    caminho = str(tmp_path / "run.json")
    run.salvar(caminho)
    carregada = Run.carregar(caminho)
    assert carregada.para_dict() == run.para_dict()
    assert [o.destino for o in carregada.opcoes] == ["minas", "minas_de_brasa"] and carregada.opcoes[1].bloqueado


# ---------------- noite, pesos e drops ----------------

def test_inimigos_noturnos_so_aparecem_a_noite():
    fase = fase_de_teste(ciclo=True, inimigos_noturnos=["morcego_gigante"], pesos={"morcego_gigante": 50})
    assert not fase.eh_noite(1, 6) and fase.eh_noite(6, 6) and fase.hora(1, 6) == 0.0
    rng = random.Random(1)
    de_dia = {fase.sortear_inimigo(rng, noite=False) for _ in range(60)}
    a_noite = {fase.sortear_inimigo(rng, noite=True) for _ in range(60)}
    assert de_dia == {"goblin"} and "morcego_gigante" in a_noite
    montador = MontadorDeCombate(fase, 5, random.Random(2), 3, noite=True)
    assert "morcego_gigante" in montador.comuns(10)
    assert fase_de_teste().hora(1, 6) == 1.0 and fase_de_teste().eh_noite(1, 6)   # fase coberta: sempre noite


def test_pesos_dos_inimigos():
    fase = fase_de_teste(inimigos=["goblin", "aranha"], pesos={"aranha": 0})
    rng = random.Random(4)
    assert {fase.sortear_inimigo(rng) for _ in range(50)} == {"goblin"}


def test_drops_e_consumiveis_da_area():
    fase = fase_de_teste(drops_da_area=[{"item": "ferro_negro", "chance": 1.0, "quantidade": [2, 2]}],
                         consumiveis_da_area=[{"item": "pocao_de_vida", "chance": 0.0}])
    assert fase.sortear_drops(random.Random(1)) == {"ferro_negro": 2}
    alquimista = Alquimista(random.Random(1), 1, (), fase.consumiveis_a_venda())
    assert "pocao_de_vida" in [o.chave for o in alquimista.ofertas]


def test_run_usa_os_drops_da_fase(monkeypatch):
    from roguelike.encontros import EncontroCombate
    run = nova_run()
    monkeypatch.setattr(run.regiao, "drops_da_area", [{"item": "ferro_negro", "chance": 1.0}])
    run.encontro = EncontroCombate("t", "", 1, ["goblin"])
    combate = run.criar_combate()
    for inimigo in combate.inimigos:
        combate.causar_dano(inimigo, 9999, run.grupo.herois[0])
    combate.verificar_fim()
    assert run.concluir_combate(combate).itens.get("ferro_negro", 0) >= 1


def test_inimigos_das_fases_existem():
    for fase in todas_as_regioes().values():
        for chave in fase.todos_os_inimigos():
            ficha(chave)


def test_multiplicador_do_ato_equilibra_os_inimigos(monkeypatch):
    from roguelike.encontros import EncontroCombate
    run = nova_run()
    run.regiao_atual, run.perigo = "minas", 6
    monkeypatch.setattr(regiao("minas"), "multiplicador_inimigos", {})
    normal = run.criar_combate(EncontroCombate("t", "", 1, ["orc"])).inimigos[0]
    monkeypatch.setattr(regiao("minas"), "multiplicador_inimigos", {"vida_percentual": 0.5, "dano_causado": 0.5})
    fraco = run.criar_combate(EncontroCombate("t", "", 1, ["orc"])).inimigos[0]
    assert abs(fraco.vida_maxima - normal.vida_maxima * 0.5) <= 1 and fraco.vida == fraco.vida_maxima
    assert abs((1 + fraco.stat("dano_causado")) - (1 + normal.stat("dano_causado")) * 0.5) < 0.01