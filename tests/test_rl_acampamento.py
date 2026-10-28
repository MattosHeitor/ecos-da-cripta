"""Fase 3, etapa 3: acampamento interativo (expedição, Taverneiro, bestiário, grimório), golpes novos,
golpes raros por conquista, Monge e Feiticeira com familiares."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from roguelike.classes import criar_heroi, todas_as_classes, heroi_para_dict, heroi_de_dict
from roguelike.conquistas import todas_as_conquistas, conquista_do_golpe
from roguelike.expedicao import Expedicao
from roguelike.golpes import golpe, todas_as_chaves, GerenciadorDeGolpes
from roguelike.inimigos import criar_inimigo, fichas_de_invocacao
from roguelike.progresso import Progresso, dados_da_taverna
from roguelike.skins import skins_a_venda

from apoio_roguelike import combate_pronto, vez_de


# ============================================================
# EXPEDIÇÃO
# ============================================================

def test_expedicao_padrao_salva_e_valida():
    progresso = Progresso()
    expedicao = progresso.expedicao_atual()
    assert [v.classe for v in expedicao.vagas] == ["guerreiro", "sacerdote", "patrulheira"]
    vaga = expedicao.adicionar("monge")
    vaga.raca = "draconiano"                         # não comprada: volta a humano
    vaga.subclasse = "mestre_da_serenidade"          # prestígio 6: volta à primeira
    expedicao.validar(progresso)
    assert vaga.raca == "humano" and vaga.subclasse == "punho_de_ferro"
    progresso.racas_compradas.append("gnomo")
    vaga.raca = "gnomo"
    copia = Progresso.de_dict(progresso.para_dict()).expedicao_atual()
    assert [v.para_dict() for v in copia.vagas] == [v.para_dict() for v in expedicao.vagas]


def test_expedicao_cria_os_herois_da_run():
    progresso = Progresso()
    progresso.racas_compradas.append("gnomo")
    expedicao = Expedicao.padrao()
    expedicao.vagas[0].raca = "gnomo"
    expedicao.vagas[0].nome = "Pip"
    run = progresso.criar_run(expedicao.criar_herois(progresso), "EXPEDICAO")
    pip = run.grupo.herois[0]
    assert pip.nome == "Pip" and pip.raca == "gnomo" and "+@raca_gnomo" in pip.sprite
    assert expedicao.remover(expedicao.vagas[0]) and len(expedicao.vagas) == 2
    while not expedicao.cheia():
        expedicao.adicionar()
    assert expedicao.adicionar() is None


# ============================================================
# TAVERNEIRO
# ============================================================

def test_provisoes_vao_para_a_mochila_e_somem_depois():
    progresso = Progresso()
    progresso.brasas = 100
    maximo = dados_da_taverna()["provisoes"]["maximo"]
    for _ in range(maximo):
        assert progresso.comprar_provisao("pocao_de_vida")
    assert not progresso.comprar_provisao("antidoto")             # a mochila de provisões encheu
    run = progresso.criar_run([criar_heroi("guerreiro")], "PROVISOES")
    assert run.grupo.herois[0].inventario.quantidade("pocao_de_vida") == maximo     # (MP4: a mochila do jogador)
    assert progresso.provisoes == {} and run.estatisticas["itens_obtidos"] == 0


def test_vitrine_e_boatos_mudam_a_cada_run_e_skin_rara_so_comprada():
    progresso = Progresso()
    progresso.brasas = 500
    antes = progresso.vitrine()
    assert len(antes) == dados_da_taverna()["vitrine"]["quantidade"]
    assert set(antes) <= {s.chave for s in skins_a_venda()}
    assert progresso.vitrine() == antes and progresso.boatos() == progresso.boatos()   # estável na mesma run
    chave = antes[0]
    assert not progresso.skin_liberada(chave)
    assert progresso.comprar_skin(chave) and progresso.skin_liberada(chave)
    assert not progresso.comprar_skin(chave)
    mudou = False
    for _ in range(6):
        progresso.estatisticas["runs"] += 1
        mudou |= progresso.vitrine() != antes
    assert mudou
    fora = next(s.chave for s in skins_a_venda() if s.chave not in progresso.vitrine())
    assert not progresso.comprar_skin(fora)                      # só compra o que está na vitrine


# ============================================================
# GOLPES: 6 ESPAÇOS, NOVOS POR NÍVEL, DESCOBERTOS E RAROS
# ============================================================

def test_seis_espacos_e_golpes_de_classe_nos_niveis_3_e_6():
    assert GerenciadorDeGolpes.espacos_base() == 6
    for chave, classe in todas_as_classes().items():
        assert set(classe.golpes_por_nivel) == {3, 6}, chave
        heroi = criar_heroi(chave)
        for _ in range(5):
            heroi.subir_nivel()                                   # nível 6
        for golpe_do_nivel in classe.golpes_por_nivel.values():
            assert heroi.golpes.sabe(golpe_do_nivel), (chave, golpe_do_nivel)


def test_golpes_descobertos_entram_no_catalogo():
    progresso = Progresso()
    run = progresso.criar_run([criar_heroi("monge")], "DESCOBRE")
    assert progresso.golpe_descoberto("palma_aberta") and not progresso.golpe_descoberto("cem_punhos")
    heroi = run.grupo.herois[0]
    for _ in range(5):
        heroi.subir_nivel()
    progresso.registrar_combate(run, [])
    assert progresso.golpe_descoberto("cem_punhos")


def test_todo_raro_tem_conquista_classe_e_nivel():
    raros = [c for c in todas_as_chaves() if golpe(c).raro]
    assert len(raros) >= len(todas_as_classes())
    for chave in raros:
        g = golpe(chave)
        assert conquista_do_golpe(chave) is not None, chave
        assert g.classes_do_raro and set(g.classes_do_raro) <= set(todas_as_classes())
    cobertas = {c for chave in raros for c in golpe(chave).classes_do_raro}
    assert cobertas == set(todas_as_classes())                   # toda classe tem pelo menos um raro


def test_conquista_libera_o_raro_e_o_heroi_aprende_no_nivel_dele():
    progresso = Progresso()
    sem = progresso.criar_run([criar_heroi("guerreiro")], "RARO1").grupo.herois[0]
    assert sem.golpes_raros == []
    progresso.conquistas.add("chefe:orc_senhor_da_guerra")
    feitas = progresso.verificar_conquistas()
    assert "senhor_da_guerra_caido" in {c.chave for c in feitas}
    heroi = progresso.criar_run([criar_heroi("guerreiro")], "RARO2").grupo.herois[0]
    assert heroi.golpes_raros == ["lamina_do_rei_caido"]
    for _ in range(3):
        heroi.subir_nivel()
    assert not heroi.golpes.sabe("lamina_do_rei_caido")
    heroi.subir_nivel()                                           # nível 5
    assert heroi.golpes.sabe("lamina_do_rei_caido")
    assert ("Golpe raro!", f"{heroi.nome} aprendeu Lâmina do Rei Caído") in heroi.golpes.pegar_avisos()
    assert heroi_de_dict(heroi_para_dict(heroi)).golpes_raros == ["lamina_do_rei_caido"]


# ============================================================
# BESTIÁRIO E GRIMÓRIO
# ============================================================

def test_bestiario_revela_aos_poucos():
    from roguelike.bestiario import secoes, Pagina, total_conhecido
    progresso = Progresso()
    todos = [c for _, _, lista in secoes() for c in lista]
    from roguelike.inimigos import fichas
    assert set(fichas()) <= set(todos)
    pagina = Pagina("esqueleto", progresso)
    assert pagina.nome == "???" and not pagina.conhecido
    progresso.abates["esqueleto"] = 1
    pagina = Pagina("esqueleto", progresso)
    assert pagina.nome == "Esqueleto" and not pagina.fraquezas_reveladas
    progresso.abates["esqueleto"] = 10
    pagina = Pagina("esqueleto", progresso)
    assert pagina.fraquezas_reveladas and pagina.loot_revelado and "luz" in pagina.afinidades()[0]
    assert Pagina("aranha_mae", type("P", (), {"abates": {"aranha_mae": 1}})()).fraquezas_reveladas   # chefes: 1 basta
    assert total_conhecido(progresso)[0] == 1


def test_grimorio_mostra_tudo_que_a_classe_pode_ter():
    from roguelike.grimorio import secoes_da_classe, total_da_classe
    progresso = Progresso()
    for chave, classe in todas_as_classes().items():
        secoes = secoes_da_classe(chave)
        nomes = [s.chave for s in secoes]
        assert nomes[0] == "classe" and set(classe.subclasses) <= set(nomes) and "raros" in nomes, chave
        todas = [e.chave for s in secoes for e in s.entradas]
        assert set(classe.habilidades) <= set(todas)
        for sub in classe.subclasses.values():
            assert set(sub.golpes) <= set(todas)
        assert total_da_classe(chave, progresso) == (0, len(set(todas)))
    progresso.golpes_descobertos.add("golpe")
    assert total_da_classe("guerreiro", progresso)[0] == 1


# ============================================================
# MONGE, FEITICEIRA E FAMILIARES
# ============================================================

def test_monge_e_feiticeira_tem_tudo_que_uma_classe_precisa():
    from roguelike.progresso import arvore_da_classe
    for chave in ("monge", "feiticeira"):
        classe = todas_as_classes()[chave]
        assert len(classe.subclasses) == 3 and [s.prestigio for s in classe.subclasses.values()] == [0, 3, 6]
        assert arvore_da_classe(chave)
        for sub in classe.subclasses.values():
            heroi = criar_heroi(chave, subclasse=sub.chave)
            assert heroi.golpes.sabe(sub.assinatura)


def test_familiares_lutam_do_lado_do_grupo():
    invocacoes = fichas_de_invocacao()
    for chave in ("garca_espiritual", "tigre_espiritual", "macaco_espiritual", "corvo", "gato_negro", "sapo_venenoso"):
        assert chave in invocacoes
    feiticeira = criar_heroi("feiticeira")
    combate = combate_pronto([feiticeira], [criar_inimigo("goblin")])
    vez_de(combate, feiticeira)
    feiticeira.energia = 5
    assert combate.usar_habilidade(feiticeira, "chamar_corvo")
    corvo = next(l for l in combate.herois if l.eh_invocacao)
    assert corvo.nome == "Corvo" and corvo.lado == "herois"
    # o familiar age sozinho (IA) na vez dele
    for _ in range(30):
        atual = combate.comecar_turno()
        if atual is corvo and combate.pode_agir:
            assert combate.agir_ia()
            break
        if combate.pode_agir:
            combate.concentrar(atual)
    else:
        raise AssertionError("o corvo não agiu")


def test_caminho_do_espirito_chama_mais_familiares():
    monge = criar_heroi("monge", subclasse="caminho_do_espirito")
    assert monge.stat("max_invocacoes") == 3
    combate = combate_pronto([monge], [criar_inimigo("orc")])
    vez_de(combate, monge)
    monge.energia = 10
    assert combate.usar_habilidade(monge, "espirito_guardiao")
    assert len(combate.invocacoes_de(monge)) == 1


def test_todas_as_conquistas_tem_premio():
    for conquista in todas_as_conquistas().values():
        assert conquista.skin or conquista.golpe


# ============================================================
# INSÍGNIAS E PRESTÍGIO
# ============================================================

def test_insignias_mostram_conquistas_e_o_proximo_marco_do_prestigio():
    from roguelike.insignias import insignias_de_conquista, prestigio_das_classes
    progresso = Progresso()
    insignias = insignias_de_conquista(progresso)
    assert len(insignias) == len(todas_as_conquistas()) and not any(i.feita for i in insignias)
    assert all(i.premio for i in insignias)
    progresso.conquistas.add("vitoria")
    progresso.verificar_conquistas()
    assert any(i.feita for i in insignias_de_conquista(progresso))
    monge = prestigio_das_classes(progresso, ["monge"])[0]
    assert monge.nivel == 0 and monge.proxima_subclasse.chave == "caminho_do_espirito"
    assert "prestígio 3" in monge.texto_do_proximo() and monge.fracao() == 0
    progresso.ganhar_prestigio("monge", 10 ** 8)
    monge = prestigio_das_classes(progresso, ["monge"])[0]
    assert monge.no_maximo and monge.fracao() == 1.0 and monge.texto_do_proximo() == "prestígio máximo"


def test_todo_humanoide_do_acampamento_sabe_sentar():
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    for nome in ("capita", "estudioso", "monge", "feiticeira", "guerreiro", "mago_Fogo", "camada_monge_raca_gnomo"):
        assert "sentado" in sprites.meta(nome)["animacoes"], nome
    for objeto in ("fogueira", "taverna_fundo", "taverna_balcao", "tronco", "pilha_de_livros", "poste_de_lanterna"):
        assert objeto in sprites.catalogo, objeto
