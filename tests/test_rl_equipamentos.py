"""Fase 4, equipamentos E1: espaços, duas mãos, restrições, amaldiçoados, sets, afixos, arsenal e fuga."""

import random

from roguelike.arsenal import Arsenal
from roguelike.classes import criar_heroi, heroi_para_dict, heroi_de_dict
from roguelike.combate import Combate
from roguelike.exemplares import criar_exemplar, exemplar
from roguelike.itens import item, criar_equipamento, Arma, Armadura, Acessorio
from roguelike.piloto_automatico import grupo_padrao
from roguelike.progresso import Progresso
from roguelike.run import Run

from apoio_roguelike import SorteControlado


def nova_run(classes=("guerreiro", "sacerdote"), semente="EQUIPA"):
    return Run(grupo_padrao(classes), semente=semente)


# ---------------- espaços e regras ----------------

def test_oito_espacos_mais_o_consumivel():
    heroi = criar_heroi("guerreiro")
    assert list(heroi.equipamento) == ["cabeca", "peitoral", "calcas", "botas", "capa", "amuleto", "arma",
                                       "arma_secundaria", "consumivel"]
    assert isinstance(item("espada_enferrujada"), Arma) and isinstance(item("botas_gastas"), Armadura)
    assert isinstance(item("anel_de_sangue"), Acessorio)


def test_duas_maos_e_mao_secundaria_se_excluem():
    heroi = criar_heroi("guerreiro")
    assert heroi.equipar(item("escudo_de_madeira"))[0]
    ok, saiu = heroi.equipar(item("machado_orc"))                  # duas mãos: o escudo sai
    assert ok and [p.chave for p in saiu] == ["escudo_de_madeira"] and heroi.equipamento["arma_secundaria"] is None
    ok, saiu = heroi.equipar(item("broquel_de_ferro"))              # escudo com arma de duas mãos: a arma sai
    assert ok and [p.chave for p in saiu] == ["machado_orc"] and heroi.equipamento["arma"] is None
    heroi.equipar(item("espada_enferrujada"))
    assert heroi.equipamento["arma"].chave == "espada_enferrujada"


def test_restricao_de_classe_e_de_raca():
    so_mago = criar_equipamento("teste_cajado", {"nome": "T", "espaco": "arma", "classes": ["mago"]})
    so_anao = criar_equipamento("teste_elmo", {"nome": "T", "espaco": "cabeca", "racas": ["anao_das_profundezas"]})
    guerreiro = criar_heroi("guerreiro")
    assert not guerreiro.equipar(so_mago)[0]
    assert guerreiro.equipamentos.motivo_para_nao_equipar(so_mago) == "Classe não pode usar"
    assert not guerreiro.equipar(so_anao)[0]
    guerreiro.definir_raca("anao_das_profundezas")
    assert guerreiro.equipar(so_anao)[0]


def test_amaldicoado_trava_ate_a_fogueira():
    run = nova_run()
    heroi = run.grupo.herois[0]
    run.grupo.bau.adicionar("anel_do_pacto")
    assert run.grupo.equipar(heroi, "anel_do_pacto", run.grupo.bau)
    assert not run.grupo.desequipar(heroi, "amuleto")                     # presa
    run.grupo.bau.adicionar("anel_de_sangue")
    assert not run.grupo.equipar(heroi, "anel_de_sangue", run.grupo.bau)   # nem trocar
    run.fogueira()
    assert run.grupo.desequipar(heroi, "amuleto")


def test_amaldicoado_trava_continua_no_save():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("botas_do_enforcado"))
    copia = heroi_de_dict(heroi_para_dict(heroi))
    assert copia.desequipar("botas") is None and "botas" in copia.equipamentos.travados


# ---------------- atributos novos ----------------

def test_precisao_anula_esquiva():
    atacante, alvo = criar_heroi("guerreiro"), criar_heroi("ladino")
    alvo.ajustes["chance_esquiva"] = 0.3
    combate = Combate([atacante], [alvo], SorteControlado(sorteios=[0.2]), ajustar_grupo=False)
    assert combate.golpear(atacante, alvo, 5).esquivou
    atacante.ajustes["precisao"] = 0.3
    combate = Combate([atacante], [alvo], SorteControlado(sorteios=[0.2]), ajustar_grupo=False)
    assert not combate.golpear(atacante, alvo, 5).esquivou


def test_magia_e_resistencia_magica_so_nos_elementos():
    from roguelike.elementos import multiplicador
    atacante, alvo = criar_heroi("mago"), criar_heroi("guerreiro")
    base_fogo, base_fisico = multiplicador(atacante, alvo, "fogo"), multiplicador(atacante, alvo, "fisico")
    alvo.ajustes["resistencia_magica"] = 0.5
    atacante.ajustes["dano_magico"] = 0.2
    assert abs(multiplicador(atacante, alvo, "fogo") - base_fogo * 0.5 * 1.2) < 1e-9
    assert multiplicador(atacante, alvo, "fisico") == base_fisico


# ---------------- sets ----------------

def test_bonus_de_set_com_2_3_e_4_pecas():
    heroi = criar_heroi("guerreiro")
    vida = heroi.vida_maxima
    for chave in ("capuz_do_coveiro", "botas_do_coveiro"):
        heroi.equipar(item(chave))
    (conjunto, pecas, ativos), = heroi.equipamentos.sets_ativos()
    assert conjunto.nome == "Vigília do Coveiro" and pecas == 2 and len(ativos) == 1
    assert heroi.vida_maxima == vida + 6
    heroi.equipar(item("casaco_do_coveiro"))
    heroi.equipar(item("pa_do_coveiro"))
    assert any(p.nome == "Terra Fresca" for p in heroi.passivas)           # passiva das 4 peças
    heroi.desequipar("arma")
    assert not any(p.nome == "Terra Fresca" for p in heroi.passivas)


# ---------------- afixos ----------------

def test_exemplar_com_afixos_e_deterministico():
    a = criar_exemplar("espada_de_prata", random.Random("A"))
    b = criar_exemplar("espada_de_prata", random.Random("A"))
    assert a.chave != b.chave or a is b
    assert len(a.afixos) == 2 and a.nome.startswith("Espada de Prata Lunar ") and a.nome.endswith("+1")
    assert [x[0] for x in a.afixos] == [x[0] for x in b.afixos]
    for afixo, valores in a.afixos:
        for nome, valor in valores.items():
            assert a.modificadores[nome] != item("espada_de_prata").modificadores.get(nome) or valor == 0
    assert item(a.chave) is a and isinstance(a, Arma) and a.base == "espada_de_prata"


def test_drop_raro_vira_exemplar_e_salva(tmp_path):
    run = nova_run()
    recebidos = run.receber_itens({"arco_de_osso": 1, "espada_enferrujada": 1, "osso": 2})
    chave = next(c for c in recebidos if c.startswith("arco_de_osso#"))
    assert "espada_enferrujada" in recebidos and recebidos["osso"] == 2          # comum não ganha afixo
    heroi = run.grupo.herois[1]
    assert run.grupo.equipar(heroi, chave, run.grupo.bau)
    caminho = str(tmp_path / "run.json")
    run.salvar(caminho)
    import roguelike.exemplares as E
    E._registro.pop(chave)                                                       # como se o jogo reabrisse
    carregada = Run.carregar(caminho)
    assert carregada.grupo.herois[1].equipamento["arma"].nome == item(chave).nome
    assert exemplar(chave) is not None


# ---------------- arsenal ----------------

def test_arsenal_so_guarda_vencendo_ou_fugindo(tmp_path):
    progresso = Progresso()
    run = progresso.criar_run(grupo_padrao(("guerreiro",)), "ARS1")
    run.grupo.bau.adicionar("espada_enferrujada")
    run.grupo.bau.adicionar("osso", 3)
    run.resultado = "derrota"
    assert progresso.registrar_fim_de_run(run).itens_guardados == []
    run.resultado = "vitoria"
    relatorio = progresso.registrar_fim_de_run(run)
    assert relatorio.itens_guardados == ["espada_enferrujada"] and progresso.arsenal.quantidade("espada_enferrujada") == 1
    caminho = str(tmp_path / "p.json")
    progresso.salvar(caminho)
    assert Progresso.carregar(caminho).arsenal.quantidade("espada_enferrujada") == 1


def test_equipamento_inicial_vem_emprestado_do_arsenal():
    progresso = Progresso()
    progresso.arsenal.guardar(["machado_orc", "botas_gastas"])
    expedicao = progresso.expedicao_atual()
    expedicao.vagas[0].equipamento = {"arma": "machado_orc", "botas": "botas_gastas"}
    expedicao.vagas[1].equipamento = {"arma": "machado_orc"}                      # só existe um machado
    expedicao.validar(progresso)
    assert "arma" not in expedicao.vagas[1].equipamento
    run = progresso.criar_run(expedicao.criar_herois(progresso), "ARS2")
    heroi = run.grupo.herois[0]
    assert heroi.equipamento["arma"].chave == "machado_orc" and heroi.equipamento["botas"].chave == "botas_gastas"
    assert progresso.arsenal.quantidade("machado_orc") == 1                         # continua lá
    run.resultado = "vitoria"
    assert progresso.registrar_fim_de_run(run).itens_guardados == []                # emprestado não duplica
    assert progresso.arsenal.quantidade("machado_orc") == 1


def test_arsenal_respeita_a_capacidade(monkeypatch):
    arsenal = Arsenal()
    monkeypatch.setattr(Arsenal, "capacidade", staticmethod(lambda: 2))
    guardadas = arsenal.guardar(["espada_enferrujada", "espada_de_prata", "faca_enferrujada"])
    assert arsenal.total() == 2 and arsenal.quantidade("espada_de_prata") == 1 and len(guardadas) == 2


# ---------------- fuga ----------------

def test_fuga_enfrenta_um_chefe_mais_forte_e_leva_os_itens():
    progresso = Progresso()
    run = progresso.criar_run(grupo_padrao(("guerreiro", "sacerdote")), "FUGA1")
    run.grupo.bau.adicionar("botas_de_viajante")
    encontro = run.iniciar_fuga()
    assert encontro.tipo == "fuga" and encontro.inimigos[0] in run.chefes_de_fuga() and run.estado == "encontro"
    combate = run.criar_combate()
    normal = Combate(run.grupo.herois, [__import__("roguelike.inimigos", fromlist=["x"]).criar_inimigo(encontro.inimigos[0])],
                     random.Random(1))
    assert combate.inimigos[0].vida_maxima > normal.inimigos[0].vida_maxima
    for _ in range(5):                                   # chefes com fases de vida seguram um golpe por fase
        for inimigo in list(combate.inimigos):
            combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    assert run.resultado == "fuga" and run.terminou()
    assert "botas_de_viajante" in progresso.registrar_fim_de_run(run).itens_guardados


# ---------------- visual ----------------

def test_pecas_aparecem_no_sprite_e_a_skin_de_chapeu_manda():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("capuz_de_viajante"))
    heroi.equipar(item("botas_gastas"))
    assert "+@eq_capuz" in heroi.sprite and "+@eq_botas" in heroi.sprite
    heroi.vestir({"chapeu": "aureola"} if "aureola" in __import__("roguelike.skins", fromlist=["x"]).todas_as_skins()
                 else {})
    if heroi.visual.get("chapeu"):
        assert "+@eq_capuz" not in heroi.sprite and "+@eq_botas" in heroi.sprite


# ---------------- saves antigos ----------------

def test_save_antigo_com_armadura_e_dois_amuletos():
    heroi = criar_heroi("guerreiro")
    dados = heroi_para_dict(heroi)
    dados["equipamento"] = {"arma": "espada_enferrujada", "armadura": "elmo_berserker",
                            "amuleto1": "anel_de_sangue", "amuleto2": "olho_de_vidro", "consumivel": None}
    copia = heroi_de_dict(dados)
    assert copia.equipamento["cabeca"].chave == "elmo_berserker"
    assert copia.equipamento["amuleto"].chave == "anel_de_sangue"
    assert copia.inventario.tem("olho_de_vidro")                                    # o 2º amuleto vai para a mochila
