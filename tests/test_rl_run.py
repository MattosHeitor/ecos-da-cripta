"""Testes da estrutura da run: encontros, eventos, regiões, recompensas e save."""

import random

from roguelike.classes import criar_heroi
from roguelike.encontros import (GeradorDeEncontros, MontadorDeCombate, EncontroCombate, EncontroEvento,
                                 EncontroAltar, EncontroNecromante, EncontroTreinador, EncontroEntrada,
                                 TIPOS_DE_COMBATE)
from roguelike.eventos_run import todos_os_eventos, evento
from roguelike.inimigos import ficha
from roguelike.piloto_automatico import Piloto, grupo_padrao
from roguelike.regioes import regiao, todas_as_regioes
from roguelike.run import Run, normalizar_semente, VERSAO_DO_SAVE

from apoio_roguelike import SorteControlado


def run_de_teste(classes=("guerreiro", "sacerdote"), semente="TESTE1"):
    return Run(grupo_padrao(classes), semente=semente)


def vencer(run, encontro):
    """Simula uma vitória no encontro de combate (todos os inimigos caem)."""
    run.encontro = encontro
    combate = run.criar_combate(encontro)
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    return run.concluir_combate(combate)


# ---------------- semente ----------------

def test_semente_e_normalizada():
    assert normalizar_semente(" ab c1 ") == "ABC1"
    assert len(normalizar_semente("")) == 6


def test_mesma_semente_mesmas_opcoes():
    a = [o.nome for o in run_de_teste(semente="X1").opcoes_de_encontro()]
    b = [o.nome for o in run_de_teste(semente="X1").opcoes_de_encontro()]
    assert a == b


def test_sementes_diferentes_dao_runs_diferentes():
    vistas = {tuple(o.nome for o in run_de_teste(semente=f"S{i}").opcoes_de_encontro()) for i in range(15)}
    assert len(vistas) > 1


# ---------------- encontros ----------------

def test_tres_opcoes_com_pelo_menos_uma_luta():
    for i in range(30):
        opcoes = run_de_teste(semente=f"L{i}").opcoes_de_encontro()
        assert len(opcoes) == 3
        assert any(o.tipo in TIPOS_DE_COMBATE or o.tipo == "entrada" for o in opcoes)


def test_ultima_area_so_tem_o_chefe():
    run = run_de_teste()
    run.area = run.areas_da_regiao()
    opcoes = run.opcoes_de_encontro()
    assert len(opcoes) == 1 and opcoes[0].tipo == "chefe"
    assert opcoes[0].inimigos == ["aranha_mae"]


def test_altar_e_necromante_so_aparecem_com_heroi_caido():
    run = run_de_teste()
    gerador = GeradorDeEncontros(run, random.Random(1))
    assert not gerador.disponivel("altar") and not gerador.disponivel("necromante")
    run.grupo.herois[0].vida = 0
    assert gerador.disponivel("altar") and gerador.disponivel("necromante")


def test_horda_e_de_uma_familia_so_e_respeita_o_tamanho_do_grupo():
    for semente in range(20):
        montador = MontadorDeCombate(regiao("floresta"), 6, random.Random(semente), tamanho_do_grupo=1)
        horda = montador.horda()
        if horda.tipo == "horda":
            assert len({ficha(c)["familia"] for c in horda.inimigos}) == 1
        assert len(horda.inimigos) <= 3


def test_inimigos_das_regioes_existem():
    for r in todas_as_regioes().values():
        for chave in r.todos_os_inimigos():
            ficha(chave)
        assert r.chefe or not r.disponivel, r.chave        # fase jogável precisa de chefe


def test_treinador_ensina_a_especializacao_a_partir_do_nivel_5():
    run = run_de_teste(("guerreiro",))                    # grupo_padrao: Cavaleiro
    heroi = run.grupo.herois[0]
    encontro = EncontroTreinador("guerreiro", "cavaleiro")
    run.encontro = encontro
    assert not run.treinar(heroi)                         # nível 1: ainda não
    for _ in range(4):
        heroi.subir_nivel()
    assert encontro.herois_que_podem(run.grupo) == [heroi]
    assert run.treinar(heroi)
    assert heroi.especializacao.chave == "guardiao_juramentado"
    assert heroi.nome_da_classe() == "Guardião Juramentado"
    assert heroi.golpes.sabe("egide_sagrada")             # golpe da especialização
    assert heroi.golpes.sabe("muralha_de_ferro")          # Golpe de Escudo evoluiu
    assert not run.treinar(heroi)
    assert "guardiao_juramentado" in run.especializacoes_aprendidas


def test_especializacao_da_bonus_e_volta_do_save():
    from roguelike.classes import heroi_para_dict, heroi_de_dict
    run = run_de_teste(("guerreiro",))
    heroi = run.grupo.herois[0]
    bloqueio = heroi.stat("chance_bloqueio")
    for _ in range(4):
        heroi.subir_nivel()
    heroi.escolher_especializacao(heroi.subclasse.especializacoes["guardiao_juramentado"])
    assert heroi.stat("chance_bloqueio") > bloqueio
    copia = heroi_de_dict(heroi_para_dict(heroi))
    assert copia.especializacao.chave == "guardiao_juramentado"
    assert copia.stat("chance_bloqueio") == heroi.stat("chance_bloqueio")


def test_golpes_da_subclasse_chegam_nos_niveis_4_e_7():
    run = run_de_teste(("guerreiro",))
    heroi = run.grupo.herois[0]
    assert not heroi.golpes.sabe("lanca_da_justica")
    for _ in range(3):
        heroi.subir_nivel()                               # nível 4
    assert heroi.golpes.sabe("lanca_da_justica") and not heroi.golpes.sabe("juramento")
    for _ in range(3):
        heroi.subir_nivel()                               # nível 7
    assert heroi.golpes.sabe("juramento")
    novos = [c for c in ("lanca_da_justica", "juramento") if c not in heroi.golpes.equipados]
    assert all(c in heroi.golpes.pendentes for c in novos)        # espaços cheios: esperam a decisão


def test_altar_cobra_e_revive_com_vida_cheia():
    run = run_de_teste()
    caido = run.grupo.herois[0]
    caido.vida = 0
    run.encontro = EncontroAltar()
    run.grupo.ouro = 100
    assert not run.reviver_pago(caido)                  # 250 de ouro
    run.grupo.ouro = 300
    assert run.reviver_pago(caido)
    assert caido.vida == caido.vida_maxima and run.grupo.ouro == 50


def test_necromante_revive_com_metade():
    run = run_de_teste()
    caido = run.grupo.herois[0]
    caido.vida = 0
    run.encontro = EncontroNecromante()
    run.grupo.ouro = 100
    assert run.reviver_pago(caido)
    assert caido.vida == round(caido.vida_maxima * 0.5)


# ---------------- eventos ----------------

def test_todos_os_eventos_carregam():
    assert len(todos_os_eventos()) >= 15
    for e in todos_os_eventos().values():
        assert 2 <= len(e.opcoes) <= 4                  # a tela de evento cabe até 4 botões


def test_opcao_com_requisito_nao_cumprido_nao_vale():
    run = run_de_teste()
    run.grupo.ouro = 0
    poco = evento("poco_dos_desejos")
    assert not poco.opcoes[0].disponivel(run)
    assert poco.escolher(0, run, random.Random(1)) is None


def test_evento_que_da_ouro():
    run = run_de_teste()
    ouro = run.grupo.ouro
    evento("altar_esquecido").escolher(1, run, random.Random(1))
    assert run.grupo.ouro == ouro + 60
    assert run.efeitos_proximo_combate        # maldição para o próximo combate


def test_maldicao_vale_no_proximo_combate_e_depois_some():
    run = run_de_teste()
    evento("altar_esquecido").escolher(1, run, random.Random(1))
    combate = run.criar_combate(EncontroCombate("t", "", 1, ["goblin"]))
    assert all(h.tem_status("amaldicoado") for h in combate.herois)
    assert run.efeitos_proximo_combate == []


def test_recrutar_coloca_heroi_no_nivel_medio():
    run = run_de_teste(("guerreiro",))
    run.grupo.herois[0].nivel = 5
    evento("viajante_perdido").escolher(0, run, random.Random(3))
    assert len(run.grupo.herois) == 2
    novo = run.grupo.herois[1]
    assert novo.nivel == 5 and novo.classe.chave != "guerreiro"


def test_teste_de_atributo_usa_o_melhor_do_grupo():
    run = run_de_teste()
    resultado = evento("bau_trancado").escolher(0, run, SorteControlado(minimo=False))   # 1d10 = 10
    assert any("Clique" in t for t in resultado.textos)


def test_evento_pode_virar_combate():
    run = run_de_teste()
    run.encontro = EncontroEvento("caravana_saqueada")
    resultado = run.resolver_evento(1)
    assert resultado.combate is not None
    assert run.encontro.eh_combate()


def test_dano_de_evento_nunca_mata():
    run = run_de_teste()
    for heroi in run.grupo.herois:
        heroi.vida = 1
    evento("santuario_de_sangue").escolher(0, run, random.Random(1))
    assert all(h.vida == 1 for h in run.grupo.herois)


# ---------------- avanço e regiões ----------------

def test_avancar_area_descansa_o_grupo():
    run = run_de_teste()
    heroi = run.grupo.herois[0]
    heroi.vida = 5
    run.escolher(0)
    run.concluir_encontro()
    assert run.area == 2
    assert heroi.vida == 5 + max(10, int(heroi.vida_maxima * 0.15))


def test_vencer_o_chefe_da_floresta_abre_os_portoes_do_ato_2():
    run = run_de_teste()
    run.area = run.areas_da_regiao()
    chefe = run.opcoes_de_encontro()[0]
    run.escolher(0)
    recompensa = vencer(run, chefe)
    assert recompensa.itens.get("alma_da_mae_aranha") == 1
    assert "aranha_mae" in run.estatisticas["chefes"]
    run.concluir_encontro()
    portoes = run.opcoes_de_encontro()
    assert [p.tipo for p in portoes] == ["portao", "portao"] and run.regiao_atual == "floresta"
    abertos = [i for i, p in enumerate(portoes) if not p.bloqueado]
    assert abertos and all(regiao(portoes[i].destino).ato == 1 for i in abertos)       # fases do Ato II
    destino = portoes[abertos[0]].destino
    run.escolher(abertos[0])
    run.concluir_encontro()
    assert (run.regiao_atual, run.area) == (destino, 1) and run.portoes is None


def vencer_a_fase(run):
    run.area = run.areas_da_regiao()
    run.opcoes = None
    encontro = run.opcoes_de_encontro()[0]
    run.encontro = encontro
    combate = run.criar_combate(encontro)
    for _ in range(5):                                  # chefes com fases de vida seguram um golpe por fase
        for inimigo in list(combate.inimigos):
            combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    run.concluir_encontro()


def escolher_portao(run, destino):
    run.escolher([p.destino for p in run.opcoes_de_encontro()].index(destino))
    run.concluir_encontro()


def test_atos_ii_iii_e_a_catedral_final_tem_de_10_a_15_areas():
    run = run_de_teste()
    run.encontro = EncontroEntrada("minas")             # (o gerador não oferece mais esta passagem: é um ato)
    run.concluir_encontro()
    assert (run.regiao_atual, run.area) == ("minas", 1)
    vencer_a_fase(run)
    destinos = {p.destino: p.bloqueado for p in run.opcoes_de_encontro()}
    assert set(destinos) <= {"catacumbas_da_ordem_caida", "cidadela_congelada"} and False in destinos.values()
    escolher_portao(run, "catacumbas_da_ordem_caida")
    assert run.regiao_atual == "catacumbas_da_ordem_caida"
    vencer_a_fase(run)
    destinos = {p.destino: p.bloqueado for p in run.opcoes_de_encontro()}
    assert destinos == {"catedral": False, "catedral_do_eclipse": False}
    run.escolher([p.destino for p in run.opcoes].index("catedral"))
    run.concluir_encontro()
    assert run.regiao_atual == "catedral" and 10 <= run.areas_da_regiao() <= 15      # etapa 8 (antes: 3)


def test_circo_volta_para_a_catedral():
    run = run_de_teste()
    run.regiao_atual, run.area = "catedral", 2
    run.encontro = EncontroEntrada("circo")
    run.concluir_encontro()
    assert run.regiao_atual == "circo"
    run.area = run.areas_da_regiao()
    vencer(run, run.opcoes_de_encontro()[0])
    run.concluir_encontro()
    assert (run.regiao_atual, run.area) == ("catedral", 3)


def test_vencer_o_chefe_da_catedral_vence_a_run():
    run = run_de_teste()
    run.regiao_atual = "catedral"
    run.area = run.areas_da_regiao()
    vencer(run, run.opcoes_de_encontro()[0])
    run.concluir_encontro()
    assert run.resultado == "vitoria" and run.estado == "fim"
    assert run.brasas_ganhas() > 80


def test_derrota_acaba_a_run():
    run = run_de_teste()
    combate = run.criar_combate(EncontroCombate("t", "", 1, ["goblin"]))
    for heroi in run.grupo.herois:
        combate.causar_dano(heroi, 9999, None)
    combate.verificar_fim()
    run.concluir_combate(combate)
    assert run.resultado == "derrota" and run.terminou()
    resumo = run.resumo()
    assert resumo["semente"] == "TESTE1" and "brasas" in resumo


def test_inimigos_ficam_mais_fortes_a_cada_area():
    run = run_de_teste()
    fraco = run.criar_combate(EncontroCombate("t", "", 1, ["goblin"])).inimigos[0]
    run.perigo = 10
    forte = run.criar_combate(EncontroCombate("t", "", 1, ["goblin"])).inimigos[0]
    assert forte.vida_maxima > fraco.vida_maxima
    assert forte.stat("dano_causado") > fraco.stat("dano_causado")


def test_vitoria_da_xp_ouro_e_loot():
    run = run_de_teste()
    ouro = run.grupo.ouro
    recompensa = vencer(run, EncontroCombate("t", "", 3, ["goblin", "goblin", "aranha"]))
    assert recompensa.xp > 0 and recompensa.ouro > 0
    assert run.grupo.ouro == ouro + recompensa.ouro
    assert run.estatisticas["inimigos_derrotados"] == 3


# ---------------- salvar e carregar ----------------

def test_salvar_e_carregar_a_run(tmp_path):
    run = run_de_teste(("guerreiro", "mago"))
    heroi = run.grupo.herois[0]
    heroi.escolher_subclasse(heroi.classe.subclasses["cavaleiro"])
    heroi.ganhar_xp(200)
    heroi.inventario.adicionar("pocao_de_vida", 2)
    run.grupo.bau.adicionar("anel_de_sangue")
    run.grupo.equipar(heroi, "anel_de_sangue", run.grupo.bau)
    run.receber_itens({"ferro_negro": 2})
    run.opcoes_de_encontro()
    caminho = tmp_path / "run.json"
    run.salvar(str(caminho))

    carregada = Run.carregar(str(caminho))
    assert carregada.para_dict() == run.para_dict()
    novo = carregada.grupo.herois[0]
    assert novo.subclasse.chave == "cavaleiro" and novo.nivel == heroi.nivel
    assert novo.equipamento["amuleto"].chave == "anel_de_sangue"
    assert [o.nome for o in carregada.opcoes] == [o.nome for o in run.opcoes]


# ---------------- run inteira ----------------

def test_runs_inteiras_com_o_piloto_automatico_terminam():
    for semente in ("P1", "P2", "P3"):
        run = Run(grupo_padrao(["guerreiro", "sacerdote", "patrulheira"]), semente=semente)
        resumo = Piloto(run).jogar()
        assert resumo["resultado"] in ("vitoria", "derrota")
        assert resumo["areas_vencidas"] >= 1


def test_fechar_no_meio_do_combate_volta_para_o_mesmo_combate(tmp_path):
    # Salvar depois de escolher guarda o encontro: carregar não deixa "fugir" escolhendo outro
    run = run_de_teste()
    run.opcoes = [EncontroCombate("Emboscada", "goblins", 2, ["goblin", "goblin"]), EncontroEvento("altar_esquecido")]
    run.escolher(0)
    caminho = str(tmp_path / "run.json")
    run.salvar(caminho)
    carregada = Run.carregar(caminho)
    assert carregada.estado == "encontro"
    assert carregada.encontro.eh_combate() and carregada.encontro.nome == "Emboscada"
    assert carregada.escolher(1) is None                  # não dá para trocar de encontro
    assert carregada.para_dict() == run.para_dict()


def test_fechar_na_loja_ou_no_evento_volta_igual(tmp_path):
    from roguelike.encontros import EncontroLoja
    caminho = str(tmp_path / "run.json")
    run = run_de_teste()
    run.opcoes = [EncontroLoja()]
    run.escolher(0)
    run.salvar(caminho)
    carregada = Run.carregar(caminho)
    assert [(o.chave, o.preco) for o in carregada.loja_atual.ofertas] == [(o.chave, o.preco) for o in run.loja_atual.ofertas]

    run = run_de_teste()
    run.opcoes = [EncontroEvento("altar_esquecido")]
    run.escolher(0)
    run.salvar(caminho)
    carregada = Run.carregar(caminho)
    assert carregada.encontro.evento == "altar_esquecido"
    assert carregada.eventos_vistos == ["altar_esquecido"]   # não conta o evento duas vezes


def test_save_no_mapa_nao_tem_encontro_escolhido(tmp_path):
    run = run_de_teste()
    run.opcoes_de_encontro()
    caminho = str(tmp_path / "run.json")
    run.salvar(caminho)
    carregada = Run.carregar(caminho)
    assert carregada.estado == "escolha" and carregada.encontro is None


def test_evento_que_vira_combate_nao_pode_ser_salvo():
    # Senão daria para fechar o jogo, voltar ao evento com o prêmio já ganho e escolher outra opção
    run = run_de_teste()
    run.opcoes = [EncontroEvento("altar_esquecido")]
    run.escolher(0)
    assert run.pode_salvar()
    run.encontro = EncontroCombate("Emboscada", "goblins", 2, ["goblin"])     # o que resolver_evento faz
    assert not run.pode_salvar()


def test_save_antigo_da_fase_1_ainda_carrega(tmp_path):
    """Um run.json de antes da fase 2 (sem golpes/visual/especialização, herói sem subclasse) continua abrindo."""
    import json
    run = Run([criar_heroi("guerreiro"), criar_heroi("mago")], "ANTIGO")
    dados = run.para_dict()
    dados["versao"] = 1
    for heroi in dados["herois"]:
        for chave in ("golpes", "especializacao", "visual"):
            heroi.pop(chave, None)
    for chave in ("escolhido", "especializacoes_aprendidas"):
        dados.pop(chave, None)
    caminho = tmp_path / "run.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    carregada = Run.carregar(str(caminho))
    for heroi in carregada.grupo.herois:
        assert heroi.subclasse is not None                     # ganhou a primeira subclasse
        assert 1 <= len(heroi.golpes.equipados) <= heroi.golpes.espacos()
    assert carregada.para_dict()["versao"] == VERSAO_DO_SAVE
    assert carregada.areas_da_regiao() == regiao(carregada.regiao_atual).areas    # região em andamento: tamanho antigo


def test_progresso_antigo_sem_campos_novos_carrega(tmp_path):
    import json
    from roguelike.progresso import Progresso
    caminho = tmp_path / "progresso.json"
    caminho.write_text(json.dumps({"brasas": 40, "conquistas": ["chefe:aranha_mae"]}), encoding="utf-8")
    progresso = Progresso.carregar(str(caminho))
    assert progresso.brasas == 40 and progresso.abates == {} and progresso.visuais == {}
    assert progresso.verificar_conquistas()[0].chave == "orfa_da_teia"    # conquista antiga já vale para skins
