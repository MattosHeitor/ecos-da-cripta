"""Tira um print (PNG) de cada tela do jogo, sem abrir janela, para comparar antes/depois.

    python ferramentas/previa_telas.py antes          -> ferramentas/previas_ui/antes/<tela>.png
    python ferramentas/previa_telas.py depois golpes  (só as telas cujo nome contém "golpes")

Usa saves temporários: nunca mexe no seu progresso nem nas suas opções.
Cada cena prepara um caso "difícil" (listas cheias, golpe novo pendente, notificação no topo...).
"""

import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "src"))

import pygame  # noqa: E402

PASTA_SAIDA = os.path.join(RAIZ, "ferramentas", "previas_ui")


def preparar_app(pasta_temp):
    """App sem janela, com opções e progresso em pasta temporária e um progresso 'cheio'."""
    from caminhos import CAMINHOS
    from telas.base import App
    from roguelike.progresso import Progresso
    from roguelike.racas import todas_as_racas
    CAMINHOS.usar_pasta_do_jogador(pasta_temp)        # opções, progresso e run vão para a pasta temporária
    app = App(janela=False)
    app.progresso = Progresso.carregar()
    app.progresso.brasas = 1234
    app.progresso.racas_compradas = list(todas_as_racas())
    app.progresso.abates.update({"goblin": 10, "aranha_mae": 3, "lich": 1, "esqueleto": 25, "bispo_eclipsado": 1})
    app.progresso.expedicao_atual().adicionar("sacerdote")
    app.progresso.expedicao_atual().adicionar("monge")
    app.progresso.expedicao_atual().adicionar("feiticeira")
    return app


def mostrar(app, tela, quadros=4, eventos=()):
    """Troca para a tela e roda alguns quadros (a transição escura termina)."""
    if tela is not None:
        app.trocar(tela)
    for _ in range(quadros):
        app.passo(0.2, list(eventos))


def criar_run(app, classes=("sacerdote", "guerreiro", "mago", "bardo"), semente="PREVIA"):
    from roguelike.classes import criar_heroi
    herois = [criar_heroi(c) for c in classes]
    for nome, heroi in zip(("Helka", "Doran", "Ilse", "Corvino"), herois):
        heroi.nome = nome
    run = app.progresso.criar_run(herois, semente)
    for heroi in herois:
        for chave, qtd in (("pocao_de_vida", 3), ("bomba_de_fogo", 2), ("osso", 7), ("couro_grosso", 4)):
            heroi.inventario.adicionar(chave, qtd)
    for chave in ("espada_de_prata", "capuz_de_viajante", "botas_gastas", "seda", "quitina", "escama"):
        run.grupo.bau.adicionar(chave, 2)
    return run


def heroi_com_golpe_novo(app):
    """Sacerdote com os 6 espaços cheios e um golpe novo esperando decisão (o caso da foto)."""
    from roguelike.classes import criar_heroi
    from roguelike.grimorio import secoes_da_classe
    heroi = criar_heroi("sacerdote")
    heroi.nome = "Helka"
    chaves = [e.chave for s in secoes_da_classe("sacerdote") for e in s.entradas if s.chave != "raros"]
    for chave in chaves:
        if len(heroi.golpes.equipados) >= heroi.golpes.espacos():
            break
        if not heroi.golpes.sabe(chave):
            heroi.aprender(chave)
    novo = next(c for c in chaves if not heroi.golpes.sabe(c))
    heroi.aprender(novo)
    return heroi


# ---------------- cenas ----------------

def cena_titulo(app):
    from telas.titulo import TelaTitulo
    mostrar(app, TelaTitulo(app), quadros=10)          # 2 s: o fade acabou e o reflexo passa pelo logo


def cena_titulo_com_run_salva(app):
    """Com uma run salva aparecem 4 opções (Continuar primeiro); o teclado desce até a segunda."""
    from telas import fluxo
    from telas.titulo import TelaTitulo
    run = criar_run(app)
    fluxo.salvar_run(run)
    tela = TelaTitulo(app)
    mostrar(app, tela, quadros=12)
    tela.mover_foco(0, 1)
    mostrar(app, None, quadros=1)
    salvar(app, "titulo_com_run_salva")


def cena_acampamento(app):
    from telas.acampamento import TelaAcampamento
    mostrar(app, TelaAcampamento(app))


def cena_acampamento_destaques(app):
    """O nome só aparece com o mouse em cima (Taverneiro) ou com o foco do teclado (Mago Ancião)."""
    from telas.acampamento import TelaAcampamento, NPCS
    tela = TelaAcampamento(app)
    mostrar(app, tela, quadros=8)
    taverneiro = next(p for p in NPCS if p.chave == "taverneiro")
    tela.mouse = tela.area_do_ponto(taverneiro).center
    mostrar(app, None)
    salvar(app, "acampamento_mouse")
    mago = next(p for p in NPCS if p.chave == "mago")
    area = tela.area_do_ponto(mago)
    botao = next(b for b in tela.botoes if b.rect == area)
    tela.usando_teclado, tela.foco = True, botao.chave_foco
    mostrar(app, None)
    salvar(app, "acampamento_teclado")


def cena_golpes_novo(app):
    from telas.golpes import TelaGolpes
    heroi = heroi_com_golpe_novo(app)
    mostrar(app, TelaGolpes(app, heroi, lambda: None), quadros=1)
    app.notificar("Golpe novo!", f"{heroi.nome} aprendeu um golpe", som=None)
    mostrar(app, None, quadros=2)


def cena_golpes_organizar(app):
    """Grimório cheio (todos os golpes da classe e de outras): a lista precisa rolar."""
    from telas.golpes import TelaGolpes
    from roguelike.grimorio import secoes_da_classe
    heroi = heroi_com_golpe_novo(app)
    for classe in ("sacerdote", "mago"):
        for chave in [e.chave for s in secoes_da_classe(classe) for e in s.entradas]:
            if not heroi.golpes.sabe(chave):
                heroi.aprender(chave)
    while heroi.golpes.pendentes:
        heroi.golpes.decidir(heroi.golpes.pendentes[0])
    tela = TelaGolpes(app, heroi, lambda: None)
    tela.escolher_do_grimorio(heroi.golpes.grimorio[0])
    mostrar(app, tela)


def cena_visual_sacerdote(app):
    from telas.visual_heroi import TelaVisual
    mostrar(app, TelaVisual(app, "sacerdote", None, lambda: None))


def cena_bau_skins(app):
    from telas.bau import TelaBau
    mostrar(app, TelaBau(app))


def cena_espelho(app):
    from telas.espelho import TelaEspelho
    mostrar(app, TelaEspelho(app))


def cena_capita(app):
    from telas.capitao import TelaCapitao
    mostrar(app, TelaCapitao(app))


def cena_mago_anciao(app):
    from telas.mago_anciao import TelaMagoAnciao
    mostrar(app, TelaMagoAnciao(app))


def cena_mago_anciao_subclasse(app):
    from telas.mago_anciao import TelaMagoAnciao
    tela = TelaMagoAnciao(app)
    tela.trocar_aba("subclasse")
    mostrar(app, tela)


def cena_taverna(app):
    from telas.taverna import TelaTaverna
    for aba in ("bencaos", "provisoes", "raridades"):
        mostrar(app, TelaTaverna(app, aba))
        salvar(app, f"taverna_{aba}")


def cena_bestiario(app):
    from telas.bestiario import TelaBestiario
    tela = TelaBestiario(app)
    tela.ver("goblin")
    mostrar(app, tela)
    salvar(app, "bestiario")
    maior = max(tela.secoes, key=lambda s: len(s[2]))[0]           # a seção com mais inimigos
    tela.trocar_secao(maior)
    mostrar(app, None)
    salvar(app, "bestiario_secao_maior")


def cena_grimorio_mestre(app):
    from telas.grimorio import TelaGrimorio
    app.progresso.golpes_descobertos |= {"golpe", "bola_de_fogo"}
    mostrar(app, TelaGrimorio(app, "mago"))


def cena_insignias(app):
    from telas.insignias import TelaInsignias
    mostrar(app, TelaInsignias(app))


def cena_opcoes(app):
    from telas.opcoes import TelaOpcoes, TelaControles
    mostrar(app, TelaOpcoes(app, lambda: None))
    salvar(app, "opcoes")
    mostrar(app, TelaControles(app, lambda: None))
    salvar(app, "opcoes_controles")


def cena_mapa(app):
    from telas import fluxo
    run = criar_run(app)
    fluxo.ir_para_mapa(app, run)
    mostrar(app, None)


def cena_grupo(app):
    from telas.grupo import TelaGrupo
    run = criar_run(app)
    mostrar(app, TelaGrupo(app, run, "herois", lambda: None))
    salvar(app, "grupo_herois")


def cena_inventario(app):
    """MP7: a mochila, o herói e o baú lado a lado (com o indicador de quem se beneficia), uma peça sob o mouse
    (a dica compara com todos do grupo), a busca/filtros, os marcados e o histórico do baú."""
    from telas import fluxo
    run = criar_run(app)
    doran = run.grupo.herois[0]
    doran.inventario.adicionar("osso", 3)
    run.grupo.colocar_no_bau(doran, "osso", 2)
    run.grupo.pegar_do_bau(run.grupo.herois[1], "osso")
    for chave in ("elmo_de_ferro", "capuz_de_viajante", "cajado_de_freixo", "anel_do_pacto"):
        run.grupo.bau.adicionar(chave)
    fluxo.abrir_inventario(app, run, lambda: None)
    mostrar(app, None)
    salvar(app, "inventario")
    tela = app.atual
    rect = next(r for r, a in tela.areas if a == ("item", "bau", "elmo_de_ferro"))
    mostrar(app, None, quadros=2, eventos=[pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center, rel=(0, 0),
                                                               buttons=(0, 0, 0))])
    salvar(app, "inventario_dica_do_grupo")
    tela.campo_busca.conteudo = "os"
    tela.filtros["tipo"] = "material"
    tela.marcados = {("mochila", "osso"), ("mochila", "couro_grosso")}
    mostrar(app, None, quadros=1)
    salvar(app, "inventario_filtros_e_marcados")
    tela.limpar_filtros()
    tela.marcados = set()
    app.atual.mostrar_historico()
    mostrar(app, None, quadros=1)
    salvar(app, "inventario_historico")


def cena_inventario_em_grupo(app):
    """MP7: em grupo, só os meus heróis nos retratos; a peça melhor para o herói da Bia brilha na minha mochila."""
    from telas import fluxo
    host, bia = _run_em_grupo(app)
    try:
        from roguelike import resumo_do_heroi as resumo
        from roguelike.itens import todos_os_itens
        run = host.run
        meu = next(h for h in run.grupo.herois if h.jogador.id == "j1")
        for chave, peca in todos_os_itens().items():          # uma peça que só serve para os heróis da Bia
            lista = resumo.beneficiados(peca, run.grupo.herois) if peca.tipo == "equipamento" else []
            if lista and all(h.jogador.id == "j2" for h, _, _ in lista):
                meu.inventario.adicionar(chave)
                break
        meu.inventario.adicionar("elmo_de_ferro")
        fluxo.abrir_inventario(app, run, lambda: None)
        mostrar(app, None, quadros=2)
        salvar(app, "inventario_em_grupo")
    finally:
        bia.fechar()
        host.fechar()
        app.partida = None


def cena_inventario_menu_da_loja(app):
    """Inventário aberto pela loja: o botão direito num item da mochila (com Vender)."""
    from roguelike import encontros as E
    from telas import fluxo
    run = criar_run(app)
    run.estado, run.opcoes = "escolha", [E.EncontroLoja()]
    run.escolher(0)
    run.grupo.herois[0].inventario.adicionar("pocao_de_vida", 2)
    fluxo.abrir_inventario(app, run, lambda: None, "mochila", run.loja_atual)
    mostrar(app, None)
    app.atual.menu_de_acoes(("item", "mochila", "pocao_de_vida"))
    mostrar(app, None, quadros=1)


def cena_arsenal(app):
    from telas import fluxo
    app.progresso.arsenal.guardar(["machado_orc", "escudo_de_madeira", "capuz_do_coveiro", "espada_de_prata"])
    fluxo.abrir_arsenal(app)
    mostrar(app, None)


def cena_fabricacao(app):
    """Receitas nos três grupos (só mochila, com o baú, faltando) e a Forja dos Anões."""
    from telas import fluxo
    run = criar_run(app)
    run.grupo.herois[0].inventario.adicionar("erva_do_pantano", 2)
    run.grupo.bau.adicionar("olho_de_sapo", 2)
    run.grupo.bau.adicionar("ferro_negro", 1)
    fluxo.abrir_fabricacao(app, run, lambda: None)
    mostrar(app, None)
    salvar(app, "fabricacao")
    app.atual.trocar_aba("forja")
    mostrar(app, None)
    salvar(app, "fabricacao_forja")


def cena_loja(app):
    from roguelike import encontros as E
    from telas import fluxo
    run = criar_run(app)
    for nome, encontro in (("loja", E.EncontroLoja()), ("evento", E.EncontroEvento("altar_esquecido")),
                           ("altar", E.EncontroAltar())):
        run.estado, run.opcoes = "escolha", [encontro]
        run.escolher(0)
        fluxo.resolver_encontro(app, run)
        mostrar(app, None)
        salvar(app, f"encontro_{nome}")


def cena_combate(app):
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    inimigos = ["goblin", "aranha", "esqueleto_arqueiro"]
    encontro = EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos)
    mostrar(app, TelaCombate(app, run, encontro, lambda r: None), quadros=12)


def cena_combate_menu_golpes(app):
    """Vez de um herói com o menu de golpes aberto (e o registro aberto)."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    inimigos = ["orc", "lich", "goblin_xama", "aranha_filhote", "esqueleto"]
    tela = TelaCombate(app, run, EncontroCombate("Horda", descrever_inimigos(inimigos), 3, inimigos), lambda r: None)
    mostrar(app, tela, quadros=1)
    for _ in range(300):                          # anima até ser a vez de um herói
        if tela.heroi() is not None:
            break
        app.passo(0.2, [])
    if tela.heroi() is not None:
        tela.abrir_menu("habilidades")
    mostrar(app, None, quadros=2)


ROUPAS_DA_ETAPA4 = {
    "guerreiro": ["elmo_do_vigia_afogado", "placas_da_vigilia_eterna", "grevas_do_cavaleiro_ossudo", "botinas_ferradas",
                  "capa_do_carrasco", "medalha_de_estanho", "maca_de_ferro_batido", "escudo_torre_da_ordem_caida"],
    "ladino": ["capuz_de_estopa", "casaca_do_duelista", "calcas_do_cacador_noturno", "botas_de_feltro_silencioso",
               "manto_de_fumaca", "olho_de_gato_preto", "punhal_da_meia_noite", "adaga_de_aparar"],
    "mago": ["coroa_de_velas_do_bispo", "gibao_acolchoado", "calcas_de_lona", "sandalias_de_corda",
             "capa_de_chuva_encerada", "saquinho_de_ervas", "cetro_de_ambar", "tomo_das_cinzas_vivas"],
    "sacerdote": ["tiara_de_ossos", "couraca_do_sol_negro", "calcoes_de_viajante", "botas_de_pantano",
                  "manto_do_peregrino", "rosario_de_contas_de_ferro", "mangual_de_correntes_sacras", "turibulo_da_ultima_chama"],
    "barbaro": ["elmo_de_chifres_partidos", "pele_do_lobo_espectral", "coxotes_do_gladiador", "botas_ferradas_de_gelo",
                "manto_do_matilheiro", "cordao_de_dente_de_lobo", "machado_uivante_do_degelo", "broquel_cravejado"],
    "patrulheira": ["capuz_de_estopa", "couraca_de_escamas_de_afogado", "perneiras_de_couro_cru", "botas_de_batedor",
                    "capa_de_penas_de_corvo", "frasco_de_sangue_seco", "arco_de_teixo_sussurrante"],
    "bardo": ["coroa_do_rei_mendigo", "cota_de_aneis_enferrujada", "calcas_de_lona", "botas_do_mensageiro_sem_cabeca",
              "asas_rasgadas_do_anjo_caido", "colar_de_linguas_cortadas", "alaude_de_cordas_de_prata"],
    "bobo": ["mascara_do_riso_eterno", "tunica_de_linho_cru", "calcas_de_pele_de_carnical", "sandalias_de_corda",
             "capa_de_saco", "moeda_furada_da_sorte", "cimitarra_de_cinzas", "lanterna_de_coveiro"],
    "monge": ["mascara_de_bico_da_peste", "faixas_do_mosteiro_esquecido", "calcoes_de_viajante", "sandalias_de_corda",
              "manto_do_peregrino", "sino_do_penitente", "cajado_de_freixo"],
    "feiticeira": ["capuz_do_corvo", "peitoral_de_ossos_de_gigante", "grevas_de_bronze", "passos_do_andarilho_eterno",
                   "capa_de_penas_de_corvo", "coracao_de_pedra_gelida", "lamina_do_eclipse", "grimorio_de_pele_costurada"],
}


def cena_itens_novos(app):
    """Os 10 heróis vestindo peças da etapa 4 (um print do inventário por classe)."""
    from telas import fluxo
    classes = list(ROUPAS_DA_ETAPA4)
    for inicio in range(0, len(classes), 4):
        grupo = classes[inicio:inicio + 4]
        run = criar_run(app, tuple(grupo))
        for heroi, classe in zip(run.grupo.herois, grupo):
            for chave in ROUPAS_DA_ETAPA4[classe]:
                run.grupo.bau.adicionar(chave)
                run.grupo.equipar(heroi, chave, run.grupo.bau)
        for indice, classe in enumerate(grupo):
            fluxo.abrir_inventario(app, run, lambda: None, "bau", indice=indice)
            mostrar(app, None)
            salvar(app, f"itens_novos_{classe}")


def cena_recompensas(app):
    """Janela de recompensas do fim do combate (loot grande, com a dica de um item sob o mouse)."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.run import Recompensa
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    inimigos = ["goblin", "aranha"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    mostrar(app, tela, quadros=1)
    recompensa = Recompensa()
    recompensa.xp, recompensa.ouro = 46, 31
    recompensa.itens = {"machado_uivante_do_degelo": 1, "capuz_do_corvo": 1, "botas_de_batedor": 1, "tunica_de_linho_cru": 1,
                        "pocao_de_vida": 2, "pao_duro": 1, "linho_velho": 3, "couro_de_lobo": 2, "couro_de_aranha": 1,
                        "madeira_morta": 2, "sucata_de_ferro": 4, "ectoplasma": 1, "seda": 2, "osso": 3}
    recompensa.niveis = [(run.grupo.herois[0], 1)]
    tela.combate.resultado = "vitoria"
    tela.recompensa, tela.estado = recompensa, "fim"
    tela.fila.clear()
    tela.mouse = (tema_centro_x() - 260, 300)
    mostrar(app, None, quadros=2)


def cena_recompensas_mochila_cheia(app):
    """MP4: o loot que não coube na mochila foi para o baú (o rodapé avisa)."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.run import Recompensa
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    inimigos = ["goblin", "aranha"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    mostrar(app, tela, quadros=1)
    recompensa = Recompensa()
    recompensa.xp, recompensa.ouro = 30, 18
    recompensa.itens = {"capuz_do_corvo": 1, "pocao_de_vida": 2, "osso": 3, "seda": 2}
    recompensa.por_jogador = {"local": dict(recompensa.itens)}
    recompensa.no_bau = {"local": {"capuz_do_corvo": 1, "seda": 2}}
    tela.combate.resultado = "vitoria"
    tela.recompensa, tela.estado = recompensa, "fim"
    tela.fila.clear()
    mostrar(app, None, quadros=2)


class _ProcuradorDaPrevia:
    """As prévias não procuram partidas na rede de verdade (UDP): duas partidas de exemplo."""
    aberto = True

    def __init__(self, *args, **kwargs):
        pass

    def partidas(self):
        return [{"ip": "192.168.0.15", "porta": 47800, "nome": "Ana", "jogadores": 2, "maximo": 4, "versao": "1.1.0",
                 "aberta": True, "mesma_versao": True},
                {"ip": "192.168.0.22", "porta": 47800, "nome": "Caio", "jogadores": 1, "maximo": 4, "versao": "1.0.9",
                 "aberta": True, "mesma_versao": False}]

    def fechar(self):
        pass


def _partida_de_dois(app, host_aqui=True):
    """Uma partida em 127.0.0.1: o app é o host (ou a Bia) e o outro lado roda só a lógica. Devolve (host, bia)."""
    import time
    from types import SimpleNamespace
    from rede.partida import PartidaCliente, PartidaHost
    from roguelike.progresso import Progresso
    from telas.lobby import resumos_da_expedicao
    cores = __import__("roguelike.dados", fromlist=["regras"]).regras()["multiplayer"]["cores"]
    progresso_do_outro = Progresso()
    expedicao = progresso_do_outro.expedicao_atual()
    expedicao.vagas = []
    for classe in ("mago", "bardo"):
        expedicao.adicionar(classe, __import__("random").Random(len(expedicao.vagas)))
    if host_aqui:
        app.progresso.expedicao_atual().vagas = app.progresso.expedicao_atual().vagas[:3]
        host = PartidaHost(app.progresso, "Ana", cores[0], porta=0, endereco="127.0.0.1", porta_descoberta=False)
        bia = PartidaCliente(progresso_do_outro, "Bia", cores[1], "127.0.0.1", host.porta,
                             resumos_da_expedicao(SimpleNamespace(progresso=progresso_do_outro)))
        app.partida, outro = host, bia
    else:
        app.progresso.expedicao_atual().vagas = app.progresso.expedicao_atual().vagas[:2]
        host = PartidaHost(progresso_do_outro, "Ana", cores[0], porta=0, endereco="127.0.0.1", porta_descoberta=False)
        host.definir_meus_herois(resumos_da_expedicao(SimpleNamespace(progresso=progresso_do_outro)))
        bia = PartidaCliente(app.progresso, "Bia", cores[1], "127.0.0.1", host.porta, resumos_da_expedicao(app))
        app.partida, outro = bia, host
    fim = time.monotonic() + 5
    while time.monotonic() < fim and not (bia.no_lobby() and len(host.lobby.jogadores) == 2):
        app.passo(0.02, [])
        outro.atualizar()
        time.sleep(0.01)
    return host, bia


def _rodar(app, outro, condicao, quadros=200):
    import time
    for _ in range(quadros):
        if outro.sessao is not None:
            outro.sessao.pegar_aplicados()            # (o outro lado não tem telas: ninguém reage)
        if condicao():
            return
        app.passo(0.02, [])
        outro.atualizar()
        time.sleep(0.01)


def cena_multijogador(app):
    """MP5: Jogar em grupo (nome, cor, criar, entrar pelo código e a lista de partidas da rede) e um erro."""
    from telas import fluxo, multijogador
    original = multijogador.Procurador
    multijogador.Procurador = _ProcuradorDaPrevia
    try:
        app.opcoes.nome_do_jogador = "Bia"
        app.opcoes.ultimo_endereco = "30AG-00F"
        fluxo.abrir_multijogador(app)
        mostrar(app, None)
        salvar(app, "multijogador")
        fluxo.abrir_multijogador(app, "Versões diferentes: o host tem 1.1.0 e você tem 1.0.9.")
        mostrar(app, None)
        salvar(app, "multijogador_erro")
    finally:
        multijogador.Procurador = original


def cena_lobby(app):
    """MP5: o lobby do host (a Bia entrou, falou, mandou um emote e está pronta) e o lobby visto pela Bia."""
    from rede.protocolo import configuracao as configuracao_da_rede
    from telas import fluxo
    for host_aqui in (True, False):
        host, bia = _partida_de_dois(app, host_aqui)
        outro = bia if host_aqui else host
        try:
            bia.falar_no_chat("Bora pegar o Bispo! Levo o mago e a bardo.")
            host.falar_no_chat("Fechado. Eu vou de linha de frente.")
            bia.mandar_emote(3)
            bia.marcar_pronto(True, bia.progresso.pacote_para_partida())
            _rodar(app, outro, lambda: host.lobby.jogador("j2").pronto and len(bia.lobby.chat) >= 4)
            fluxo.ir_para_acampamento(app)
            mostrar(app, None, quadros=2)
            app.partida.baloes["j2"] = (app.partida.baloes.get("j2") or ("Boa!", 0))[0], __import__("time").monotonic()
            salvar(app, "lobby_host" if host_aqui else "lobby_cliente")
            if host_aqui:
                tela = app.atual                              # o host está em duas redes (a da casa e a Radmin VPN)
                tela.ips = ["192.168.0.15", "26.140.22.7"]
                app.partida.ip_mostrado = "26.140.22.7"
                porta_de_verdade = app.partida.porta          # (a prévia abriu numa porta qualquer: mostra a padrão,
                app.partida.porta = configuracao_da_rede()["porta"]   # como no jogo: código de 7 letras)
                salvar(app, "lobby_vpn")
                app.partida.porta = porta_de_verdade
                tela.recolher("jogadores")                    # os dois painéis minimizados; a Bia fala de novo
                tela.recolher("conversa")
                mostrar(app, None, quadros=1)
                bia.falar_no_chat("Vou pegar mais uma poção na Taverna.")
                _rodar(app, outro, lambda: len(host.lobby.chat) >= 5)
                mostrar(app, None, quadros=1)
                salvar(app, "lobby_recolhido")
                tela.recolher("jogadores", False)
                tela.recolher("conversa", False)
        finally:
            bia.fechar()
            host.fechar()
            app.partida = None


def cena_mapa_em_grupo(app):
    """MP5: a run do grupo começou: o mapa com o dono de cada herói e "mesmo estado em todos"."""
    host, bia = _partida_de_dois(app)
    try:
        host.marcar_pronto(True, app.progresso.pacote_para_partida())
        bia.marcar_pronto(True, bia.progresso.pacote_para_partida())
        _rodar(app, bia, lambda: host.motivo_para_nao_iniciar() is None)
        host.iniciar("PREVIA")
        _rodar(app, bia, lambda: bia.run is not None and None not in host.sincronia.values()
               and type(app.atual).__name__ == "TelaTituloDaArea")
        app.atual.seguir()
        mostrar(app, None, quadros=3)
        salvar(app, "mapa_em_grupo")
    finally:
        bia.fechar()
        host.fechar()
        app.partida = None


def _run_em_grupo(app):
    """Uma run em grupo já começada (o app é o host; a Bia roda só a lógica). Devolve (host, bia)."""
    host, bia = _partida_de_dois(app)
    host.marcar_pronto(True, app.progresso.pacote_para_partida())
    bia.marcar_pronto(True, bia.progresso.pacote_para_partida())
    _rodar(app, bia, lambda: host.motivo_para_nao_iniciar() is None)
    host.iniciar("PREVIA")
    _rodar(app, bia, lambda: bia.run is not None and type(app.atual).__name__ == "TelaTituloDaArea")
    app.atual.seguir()
    mostrar(app, None, quadros=2)
    return host, bia


def cena_mapa_votacao(app):
    """MP6: o caminho por votação (a Bia já votou; falta a Ana) e o menu com Enviar ouro e a fuga do host."""
    host, bia = _run_em_grupo(app)
    try:
        tela = app.atual
        bia.votar(tela.chave_do_caminho(), len(tela.run.opcoes_de_encontro()) - 1)
        _rodar(app, bia, lambda: host.votos_de(tela.chave_do_caminho()))
        mostrar(app, None, quadros=2)
        salvar(app, "mapa_votacao")
        tela.menu_aberto = True
        mostrar(app, None, quadros=1)
        salvar(app, "mapa_menu_em_grupo")
    finally:
        bia.fechar()
        host.fechar()
        app.partida = None


class _ProcuradorComPartidaEmAndamento(_ProcuradorDaPrevia):
    """A lista da rede com a partida em andamento da qual o jogador daqui fazia parte (MP8)."""

    def partidas(self):
        return [{"ip": "192.168.0.15", "porta": 47800, "nome": "Ana", "jogadores": 2, "maximo": 4, "versao": "1.1.0",
                 "aberta": False, "mesma_versao": True, "id_da_partida": "abc123", "em_andamento": True, "fora": ["Bia"]},
                {"ip": "192.168.0.22", "porta": 47800, "nome": "Caio", "jogadores": 3, "maximo": 4, "versao": "1.1.0",
                 "aberta": False, "mesma_versao": True, "id_da_partida": "zzz", "em_andamento": True,
                 "fora": ["Duda"]}] + super().partidas()[:1]


def cena_robustez(app):
    """MP8: a latência no mapa, "conexão perdida" e "conexão lenta" (na Bia), a espera do grupo ao retomar a
    partida salva (no host) e Jogar em grupo com a partida salva e "Voltar à partida" na lista."""
    import time
    from rede.partida import PartidaHost
    from rede.retomada import carregar_partida_salva
    from telas import fluxo, multijogador
    host, bia = _run_em_grupo(app)
    try:
        host.latencias["j2"] = 38
        mostrar(app, None, quadros=2)
        salvar(app, "mapa_latencia")
        host.fechar()                                       # fica salva; o host retoma: espera a Bia
        app.partida = PartidaHost(app.progresso, "Ana", (214, 72, 72), porta=0, endereco="127.0.0.1",
                                  porta_descoberta=False, salva=carregar_partida_salva())
        mostrar(app, None, quadros=2)
        salvar(app, "retomada_esperando")
    finally:
        bia.fechar()
        if app.partida is not None:
            app.partida.fechar()
        app.partida = None
    host, bia = _partida_de_dois(app, host_aqui=False)       # agora o app é a Bia
    try:
        host.marcar_pronto(True, host.progresso.pacote_para_partida())
        bia.marcar_pronto(True, app.progresso.pacote_para_partida())
        _rodar(app, host, lambda: host.motivo_para_nao_iniciar() is None)
        host.iniciar("PREVIA")
        _rodar(app, host, lambda: bia.run is not None and type(app.atual).__name__ == "TelaTituloDaArea")
        app.atual.seguir()
        mostrar(app, None, quadros=2)
        bia.cuidar_das_conexoes = lambda: None                # (a prévia só desenha: nada de reconectar de verdade)
        bia.latencias["j2"] = 420
        mostrar(app, None, quadros=1)
        salvar(app, "conexao_lenta")
        bia.reconectando = {"desde": time.monotonic() - 12, "proxima": 0, "tentando": True, "tentativas": 4,
                            "motivo": "A conexão caiu"}
        mostrar(app, None, quadros=1)
        salvar(app, "sem_conexao")
        bia.reconectando = None
    finally:
        bia.fechar()
        host.fechar()
        app.partida = None
    original = multijogador.Procurador
    multijogador.Procurador = _ProcuradorComPartidaEmAndamento
    try:
        app.opcoes.nome_do_jogador = "Bia"
        app.opcoes.volta = {"chave": "x", "id_da_partida": "abc123"}
        fluxo.abrir_multijogador(app)
        mostrar(app, None)
        salvar(app, "multijogador_com_partida_salva")
        app.atual.criar()                                    # 1ª vez hospedando: o aviso do firewall
        mostrar(app, None, quadros=1)
        salvar(app, "aviso_do_firewall")
    finally:
        multijogador.Procurador = original


def cena_combate_em_grupo(app):
    """MP6: a luta em grupo na vez de um herói da Bia ("Bia escolhendo...") e o fim com a votação de seguir."""
    from roguelike.comandos import EscolherEncontro
    host, bia = _run_em_grupo(app)
    try:
        run = host.run
        combate = next(i for i, o in enumerate(run.opcoes_de_encontro()) if o.eh_combate())
        host.sessao.enviar(EscolherEncontro(indice=combate))
        _rodar(app, bia, lambda: type(app.atual).__name__ == "TelaCombate")
        tela = app.atual
        host.sessao.decisores = {i: __import__("roguelike.condutor", fromlist=["x"]).DecisorIA()
                                 for i, h in enumerate(run.grupo.herois) if h.jogador.id == "j1"}
        _rodar(app, bia, lambda: tela.estado == "esperando_outro", quadros=400)
        mostrar(app, None, quadros=1)
        salvar(app, "combate_vez_da_bia")
        tela.registro.append(("[Bia] Kael usou Bola de Fogo!", (240, 214, 150)))
        from roguelike.run import Recompensa
        recompensa = Recompensa()
        recompensa.xp, recompensa.ouro = 40, 22
        recompensa.por_jogador = {"j1": {"osso": 2, "pocao_de_vida": 1, "botas_gastas": 1},
                                  "j2": {"couro_grosso": 2, "pao_duro": 1, "capuz_de_viajante": 1}}
        recompensa.premios = {"j1": 3, "j2": 3}
        recompensa.ouro_por_jogador = {"j1": 13, "j2": 9}
        recompensa.itens = {**recompensa.por_jogador["j1"], **recompensa.por_jogador["j2"]}
        tela.combate.resultado, tela.condutor.recompensa = "vitoria", recompensa
        tela.terminar()
        tela.fila.clear()
        host.votar(tela.chave_de_seguir(), 0)
        _rodar(app, bia, lambda: host.votos_de(tela.chave_de_seguir()))
        mostrar(app, None, quadros=2)
        salvar(app, "combate_fim_em_grupo")
    finally:
        bia.fechar()
        host.fechar()
        app.partida = None


def cena_recompensas_de_dois_jogadores(app):
    """MP3: o loot de um chefe separado por jogador (uma aba para cada um; aberta a do jogador daqui)."""
    from roguelike.condutor import FIM
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.posse import Jogador
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    bia = Jogador("bia", "Bia")
    for heroi in run.grupo.herois[2:]:
        run.grupo.dar_heroi(heroi, bia)
    inimigos = ["aranha_mae"]
    tela = TelaCombate(app, run, EncontroCombate("Mãe Aranha", descrever_inimigos(inimigos), 5, inimigos, "chefe"),
                       lambda r: None)
    mostrar(app, tela, quadros=1)
    for inimigo in list(tela.combate.inimigos):
        tela.combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    tela.combate.verificar_fim()
    while tela.condutor.passo() != FIM:
        pass
    tela.terminar()
    tela.fila.clear()
    mostrar(app, None, quadros=2)


def tema_centro_x():
    from ui import tema
    return tema.LARGURA // 2


def cena_fim_de_run(app):
    from telas.fim_de_run import TelaFimDeRun
    run = criar_run(app)
    run.resultado = "vitoria"
    for chave in ("goblin", "lich", "aranha_mae"):
        app.progresso.abates[chave] = app.progresso.abates.get(chave, 0) + 50
    relatorio = app.progresso.registrar_fim_de_run(run)
    mostrar(app, TelaFimDeRun(app, run, relatorio))


def cena_servicos(app):
    """Treinador, descanso e necromante (a tela de serviço de cada um)."""
    from roguelike import encontros as E
    from roguelike.classes import todas_as_classes
    from telas import fluxo
    run = criar_run(app)
    classe = todas_as_classes()["sacerdote"]
    sub = next(iter(classe.subclasses))
    for nome, encontro in (("treinador", E.EncontroTreinador("sacerdote", sub)), ("descanso", E.EncontroDescanso()),
                           ("necromante", E.EncontroNecromante())):
        run.estado, run.opcoes = "escolha", [encontro]
        run.escolher(0)
        fluxo.resolver_encontro(app, run)
        mostrar(app, None)
        salvar(app, f"encontro_{nome}")


def cena_nomes_longos_e_mochilas_cheias(app):
    """Nomes de 14 letras, mochilas e baú lotados: tudo precisa caber ou rolar."""
    from roguelike.itens import todos_os_itens
    from telas.grupo import TelaGrupo
    from telas.inventario import TelaInventario, FonteDaRun
    run = criar_run(app)
    for heroi, nome in zip(run.grupo.herois, ("Wolfgangusmaxi", "Bartholomeuzzz", "Maximilianaaaa", "Esmeraldinaaaa")):
        heroi.nome = nome[:14]
    chaves = list(todos_os_itens())
    for chave in chaves[:60]:
        run.grupo.bau.adicionar(chave, 3)
    for chave in chaves[60:110]:                     # a mochila (dos heróis do jogador) cheia: 50 pilhas
        run.grupo.herois[0].inventario.adicionar(chave, 2)
    mostrar(app, TelaGrupo(app, run, "herois", lambda: None))
    salvar(app, "cheio_grupo_herois")
    mostrar(app, TelaInventario(app, FonteDaRun(run), lambda: None, run))
    salvar(app, "cheio_inventario")


def cena_taverna_mascarado(app):
    from telas.taverna import TelaTaverna
    app.progresso.conquistas.add("chefe:mercador_mascarado")
    mostrar(app, TelaTaverna(app, "mascarado"))


def cena_mercador_redesenhado(app):
    """O Mercador Mascarado redesenhado (2026-10-14): o retrato novo na aba Mascarado da Taverna.
    (A luta contra ele fica de fora: o nome do chefe no topo cruza o "Rodada N" da fila, problema antigo das lutas
    de chefe, anotado nas pendências.)"""
    from telas.taverna import TelaTaverna
    app.progresso.conquistas.add("chefe:mercador_mascarado")
    mostrar(app, TelaTaverna(app, "mascarado"))
    salvar(app, "mercador_taverna")


def cena_titulo_da_area(app):
    from telas.titulo_da_area import TelaTituloDaArea
    run = criar_run(app)
    mostrar(app, TelaTituloDaArea(app, run, lambda: None), quadros=6)


def cena_roupas_em_combate(app):
    """Etapa 7: roupas de subclasse com adornos e equipamento por cima (elmo, capa, arma) no combate."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.itens import item
    from telas.combate.tela import TelaCombate
    run = criar_run(app, ("guerreiro", "sacerdote", "bardo", "mago"))
    for heroi, sub, pecas in zip(run.grupo.herois, ("berserker", "druida", "bardo_dos_sussurros", "necromante"),
                                 (("elmo_de_chifres_partidos", "capa_de_saco"), ("capa_de_penas_de_corvo",),
                                  ("capuz_de_estopa",), ("manto_do_peregrino", "espada_de_prata"))):
        heroi.escolher_subclasse(heroi.classe.subclasses[sub], inicial=True)
        for chave in pecas:
            heroi.equipar(item(chave))
    inimigos = ["besouro_de_bronze", "besouro_carniceiro"]               # sem chefe: a barra de chefe é outra tela
    encontro = EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos)
    mostrar(app, TelaCombate(app, run, encontro, lambda r: None), quadros=12)


def cena_etapa8_ameaca_e_itens(app):
    """Etapa 8: grupo com 4 runs vencidas (Ameaça 4) na Capitã, no mapa (fase de 10 a 15 áreas) e no combate;
    e o inventário com peças novas equipadas e no baú."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.itens import item
    from telas import fluxo
    from telas.capitao import TelaCapitao
    from telas.combate.tela import TelaCombate
    app.progresso.estatisticas["vitorias"] = 4
    mostrar(app, TelaCapitao(app))
    salvar(app, "etapa8_capita_ameaca")
    run = criar_run(app)
    run.ameaca = app.progresso.nivel_de_ameaca()
    run.area = 7
    fluxo.ir_para_mapa(app, run)
    mostrar(app, None)
    salvar(app, "etapa8_mapa_ameaca")
    pecas = (("chapeu_do_cacador_de_bruxas", "gibao_do_espadachim", "rapieira_de_salao", "manto_do_ceifador_silencioso"),
             ("coroa_de_galhos_secos", "turibulo_da_ultima_vigilia", "asas_de_vitral"),
             ("elmo_do_dragao_jovem", "montante_do_executor", "grevas_do_tita_de_brasa"),
             ("chapeu_pontudo_da_bruxa_velha", "alaude_de_cordas_de_tripa", "contas_de_madeira_de_freixo"))
    for heroi, chaves in zip(run.grupo.herois, pecas):
        for chave in chaves:
            heroi.equipar(item(chave))
    for chave in ("bastiao_do_juramento", "orbe_da_tempestade_presa", "besta_de_caca", "garras_de_ferro", "tridente_de_pescador"):
        run.grupo.bau.adicionar(chave, 1)
    inimigos = ["goblin", "aranha", "esqueleto_arqueiro"]
    encontro = EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos)
    mostrar(app, TelaCombate(app, run, encontro, lambda r: None), quadros=12)
    salvar(app, "etapa8_combate_ameaca")
    fluxo.abrir_inventario(app, run, lambda: None, "bau")
    mostrar(app, None)
    salvar(app, "etapa8_inventario")


def cena_rato_branco(app):
    """Reino dos Ratos, etapa 1: o Rato Branco no mapa das Catacumbas (correndo ao fundo e na carta), os dois
    eventos (esconderijo e bueiro, com o resultado e o aviso da descoberta) e a passagem selada no fim."""
    from roguelike.regioes import regiao
    from telas import fluxo
    from telas.mapa import TelaMapa
    entradas = [regiao(c).entradas["reino_dos_ratos"] for c in ("catacumbas_da_ordem_caida", "minas", "minas_de_brasa")]
    chances = [e["chance"] for e in entradas]
    for entrada in entradas:                          # o rato é raro: na prévia ele aparece sempre
        entrada["chance"] = 1.0
    try:
        for passo, nome in ((0, "esconderijo"), (1, "bueiro"), (2, "passagem_selada")):
            run = criar_run(app)
            run.regiao_atual = "catacumbas_da_ordem_caida"
            run.regioes_visitadas.append(run.regiao_atual)
            run.area, run.segredos, run.opcoes = 3, {"rato_branco": passo}, None
            mapa = TelaMapa(app, run)
            mostrar(app, mapa)
            mapa.bicho.correr_a_partir_de(620, parar_em=620)          # parado no meio, olhando para o grupo
            mostrar(app, None, quadros=1)
            salvar(app, f"rato_branco_mapa_{nome}")
            if passo == 2:
                break
            indice = next(i for i, o in enumerate(run.opcoes) if getattr(o, "guia", None))
            run.escolher(indice)
            fluxo.resolver_encontro(app, run)
            tela = app.atual
            tela.narracao.pular()
            tela.bicho.correr_a_partir_de(300, parar_em=10 ** 6)      # correndo ao pé da tela
            mostrar(app, None, quadros=1)
            salvar(app, f"rato_branco_evento_{nome}")
            tela.escolher(0)
            tela.narracao.pular()
            fluxo.guardar_segredos(app, run)                          # no bueiro: aviso da passagem descoberta
            mostrar(app, None, quadros=1)
            salvar(app, f"rato_branco_resultado_{nome}")
    finally:
        for entrada, chance in zip(entradas, chances):
            entrada["chance"] = chance


def cena_reino_zonas(app):
    """Reino dos Ratos, etapa 2A: título da fase, o mapa (nome da zona no cabeçalho) e o combate em cada uma das
    3 zonas, e o combate na sala do trono."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    from telas.mapa import TelaMapa
    from telas.titulo_da_area import TelaTituloDaArea
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    mostrar(app, TelaTituloDaArea(app, run, lambda: None), quadros=6)
    salvar(app, "reino_titulo")
    inimigos = ["enxame_de_ratos", "carnical", "enxame_de_ratos"]
    for nome, area in (("galerias", 1), ("mercado", total // 2), ("catedral", total - 1)):
        run.area, run.opcoes = area, None
        mostrar(app, TelaMapa(app, run))
        salvar(app, f"reino_mapa_{nome}")
        encontro = EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos)
        mostrar(app, TelaCombate(app, run, encontro, lambda r: None), quadros=12)
        salvar(app, f"reino_combate_{nome}")
    run.area, run.opcoes = total, None
    encontro = EncontroCombate("Salão do Trono", "", 5, ["enxame_de_ratos"], "chefe")
    mostrar(app, TelaCombate(app, run, encontro, lambda r: None), quadros=12)
    salvar(app, "reino_combate_salao_do_trono")


def cena_reino_ambiente(app):
    """Reino dos Ratos, etapa 2B: a água alta nas Galerias (heróis Encharcados), o Mercado no escuro sem luz (um
    inimigo oculto: só os olhos) e com uma lanterna (círculo de luz), a Catedral com os dois, e a dica do painel."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.itens import item
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    inimigos = ["enxame_de_ratos", "carnical", "enxame_de_ratos"]

    def combate(area, oculto=False):
        run.area = area
        tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
        if oculto:                                    # (os ratos que somem no escuro chegam na etapa 3)
            alvo = tela.combate.inimigos[1]
            alvo.ficha = dict(alvo.ficha, some_no_escuro=True)
        mostrar(app, tela, quadros=12)
        return tela

    tela = combate(1)
    tela.combate.ambientes[0].nivel = 3                # água alta
    tela.combate.ambientes[0].aplicar(tela.combate)
    mostrar(app, None, quadros=8)
    salvar(app, "reino_ambiente_agua_alta")
    tela.mouse = (40, 70)                              # a dica do painel
    mostrar(app, None, quadros=1)
    salvar(app, "reino_ambiente_dica_da_agua")
    combate(total // 2, oculto=True)
    salvar(app, "reino_ambiente_escuro_sem_luz")
    run.grupo.herois[1].equipar(item("lanterna_de_mao"))
    combate(total // 2, oculto=True)
    salvar(app, "reino_ambiente_escuro_com_lanterna")
    run.grupo.herois[1].desequipar("arma_secundaria")
    combate(total - 1, oculto=True)
    salvar(app, "reino_ambiente_catedral")


def cena_reino_peste(app):
    """Reino dos Ratos, etapa 3A: o bando de ratos (cheio e pela metade), a Ratazana e o Rato da Peste, heróis com
    Peste (vinda da luta anterior), a dica do ícone, a Febre Negra, e a Peste no painel do mapa e na tela do grupo."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    from telas.grupo import TelaGrupo
    from telas.mapa import TelaMapa
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    run.area = 2
    helka, doran = run.grupo.herois[0], run.grupo.herois[1]
    helka.peste, doran.peste = 3, 1                    # (vieram da luta anterior)
    inimigos = ["rato_comum", "ratazana_gigante", "rato_da_peste"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    mostrar(app, tela, quadros=12)
    salvar(app, "reino_peste_combate")

    bando = tela.combate.inimigos[0]
    bando.vida = bando.vida_maxima // 2                # metade dos ratos caiu
    mostrar(app, None, quadros=8)
    salvar(app, "reino_peste_bando_pela_metade")

    visual = tela.visual(helka)
    area = next(r for r, s in visual.areas_de_status if s.chave == "peste")
    tela.mouse = area.center                           # a dica da Peste
    mostrar(app, None, quadros=1)
    salvar(app, "reino_peste_dica")

    tela.mouse = (0, 0)
    tela.combate.aplicar_status(doran, "peste", acumulos=4)
    tela.combate.atual, tela.combate.pode_agir = doran, True
    tela.combate.delirar(doran, doran.status["peste"])
    tela.enfileirar()
    mostrar(app, None, quadros=3)
    salvar(app, "reino_peste_febre_negra")

    doran.peste = 5
    mostrar(app, TelaMapa(app, run))
    salvar(app, "reino_peste_mapa")
    mostrar(app, TelaGrupo(app, run, "herois", lambda: None))
    salvar(app, "reino_peste_grupo")


def cena_reino_ratos_especiais(app):
    """Reino dos Ratos, etapa 3B1: Nadador submerso na água funda (só olhos), Ladrão roubando e fugindo, Bombardeiro
    ferido avisando o Pavio Aceso e explodindo, Alquimista com o frasco; a dica da água com os submersos."""
    from roguelike.efeitos_habilidade import Contexto, criar_efeito
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    run.area = 1
    inimigos = ["rato_nadador", "rato_ladrao", "rato_bombardeiro", "rato_alquimista"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    combate = tela.combate
    nadador, ladrao, bombardeiro, _ = combate.inimigos
    combate.ambientes[0].nivel = 2                     # água funda: o Nadador mergulha
    bombardeiro.vida = int(bombardeiro.vida_maxima * 0.4)
    bombardeiro.energia = 3                            # ferido e com energia: avisa o Pavio Aceso
    mostrar(app, tela, quadros=10)
    salvar(app, "reino_3b_combate")

    tela.mouse = (40, 70)                              # a dica da água (com os submersos)
    mostrar(app, None, quadros=1)
    salvar(app, "reino_3b_dica_agua")
    tela.mouse = (0, 0)

    heroi = run.grupo.herois[1]
    criar_efeito({"tipo": "roubar_item"}).aplicar(combate, ladrao, [heroi], 1, Contexto())
    tela.enfileirar()
    mostrar(app, None, quadros=3)
    salvar(app, "reino_3b_roubo")

    combate.fugir(ladrao, texto=f"{ladrao.nome} fugiu com o que roubou!")
    tela.enfileirar()
    mostrar(app, None, quadros=3)
    salvar(app, "reino_3b_fuga")

    combate.causar_dano(bombardeiro, 999, heroi)       # o barril explode em todos
    tela.enfileirar()
    mostrar(app, None, quadros=4)
    salvar(app, "reino_3b_explosao")


def cena_reino_bubonicos(app):
    """Reino dos Ratos, etapa 3C1: o Homem Bubônico e o Carrasco nas Galerias (e a ninhada que sai do Homem), o Mendigo
    e o Ladrão escondidos no escuro do Mercado (o Mendigo bate a carteira) e a Freira Roída na Catedral."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()

    def combate(area, inimigos, tipo="combate"):
        run.area = area
        tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 3, inimigos, tipo),
                           lambda r: None)
        mostrar(app, tela, quadros=10)
        return tela

    tela = combate(1, ["carrasco_bubonico", "homem_bubonico", "rato_comum"], "elite")
    salvar(app, "reino_3c1_galerias")
    homem = tela.combate.inimigos[1]
    tela.combate.causar_dano(homem, 999, run.grupo.herois[1])
    tela.enfileirar()
    mostrar(app, None, quadros=14)
    salvar(app, "reino_3c1_ninhada")

    tela = combate(total // 2, ["mendigo_bubonico", "rato_alquimista", "rato_ladrao"])
    mendigo = tela.combate.inimigos[0]
    run.grupo.ouro = 120
    for _ in range(2):                                 # 1º turno pede; no 2º, ignorado, bate a carteira
        mendigo.passivas[0].inicio_do_turno(mendigo, tela.combate)
    tela.enfileirar()
    mostrar(app, None, quadros=3)
    salvar(app, "reino_3c1_mercado_mendigo")

    combate(total - 1, ["freira_roida", "rato_xama", "rato_guarda_real"])
    salvar(app, "reino_3c1_catedral")


def cena_reino_eventos(app):
    """Reino dos Ratos, etapa 4A: os quatro eventos (Mercado Roedor com o Rato Mercador, Prisioneiro na Gaiola,
    Banquete do Rei e Altar do Queijo) com as opções, e o resultado de roubar o queijo do altar."""
    from roguelike.encontros import EncontroEvento
    from telas.evento import TelaEvento
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    run.grupo.bau.adicionar("queijo_mofado", 1)
    total = run.areas_da_regiao()
    for chave, area in (("mercado_do_rato_mercador", total // 2), ("prisioneiro_na_gaiola", 1),
                        ("banquete_do_rei", total - 1), ("altar_do_queijo", total - 1)):
        run.area = area
        run.encontro, run.estado = EncontroEvento(chave), "encontro"
        tela = TelaEvento(app, run)
        mostrar(app, tela, quadros=2)
        tela.narracao.pular()
        mostrar(app, None, quadros=1)
        salvar(app, f"reino_4a_{chave}")
    tela.escolher(2)                                   # roubar o queijo dourado
    tela.narracao.pular()
    mostrar(app, None, quadros=1)
    salvar(app, "reino_4a_altar_do_queijo_roubado")


def cena_reino_enxame(app):
    """Reino dos Ratos, etapa 4B: o evento do Enxame de Ratos, a onda 2 no combate, a tela entre as ondas (grupo
    ferido e com Peste, a próxima onda) e, depois da última, o ninho e o prêmio."""
    from roguelike.encontros import EncontroEvento
    from telas.evento import TelaEvento
    from telas.entre_ondas import TelaEntreOndas
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    run.area = 1
    run.encontro, run.estado = EncontroEvento("enxame_de_ratos_nas_galerias"), "encontro"
    tela = TelaEvento(app, run)
    mostrar(app, tela, quadros=2)
    tela.narracao.pular()
    mostrar(app, None, quadros=1)
    salvar(app, "reino_4b_enxame_evento")

    run.resolver_evento(0)
    run.ondas.vencer()
    for heroi, fracao, peste in zip(run.grupo.herois, (0.8, 0.35, 0.6, 0.0), (0, 2, 0, 0)):
        heroi.vida, heroi.peste = round(heroi.vida_maxima * fracao), peste
    tela = TelaEntreOndas(app, run)
    mostrar(app, tela, quadros=2)
    tela.narracao.pular()
    mostrar(app, None, quadros=1)
    salvar(app, "reino_4b_entre_ondas")

    run.proxima_onda()
    mostrar(app, TelaCombate(app, run, run.encontro, lambda r: None), quadros=8)
    salvar(app, "reino_4b_onda_2")

    run.ondas.vencer()
    run.proxima_onda()
    run.ondas.vencer()
    tela = TelaEntreOndas(app, run)
    mostrar(app, tela, quadros=2)
    tela.narracao.pular()
    mostrar(app, None, quadros=1)
    salvar(app, "reino_4b_fim_das_ondas")
    tela.encerrar()
    tela.narracao.pular()
    mostrar(app, None, quadros=1)
    salvar(app, "reino_4b_premio")


def cena_reino_rei(app):
    """Reino dos Ratos, etapa 5A: o Rei dos Ratos no Salão do Trono com o Queijo Real; um Édito Real em vigor (o
    pergaminho) e o menu de golpes de um herói marcando o que é proibido; depois um herói desobedece, o Rei come o
    queijo e entra em Fúria."""
    from roguelike.encontros import MontadorDeCombate
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    run.area = total
    encontro = MontadorDeCombate(run.regiao, total, run.rng("previa"), 4, False, total).chefe()
    tela = TelaCombate(app, run, encontro, lambda r: None)
    combate = tela.combate
    rei = combate.inimigos[0]
    combate.aplicar_status(rei, "edito_sem_magia", 2, origem=rei)
    mostrar(app, tela, quadros=1)
    for _ in range(300):                          # anima até ser a vez de um herói
        if tela.heroi() is not None:
            break
        app.passo(0.2, [])
    maga = next(h for h in combate.herois if h.classe.chave == "mago")
    combate.atual, combate.pode_agir = maga, True    # a vez da maga: as magias aparecem proibidas
    maga.energia = 6
    tela.estado = "escolhendo"
    tela.abrir_menu("habilidades")
    mostrar(app, None, quadros=2)
    salvar(app, "reino_5a_rei_edito")

    heroi = next(h for h in combate.herois if h.esta_vivo())
    combate.remover_status(rei, "edito_sem_magia")
    combate.aplicar_status(rei, "edito_sem_atacar", 2, origem=rei)
    combate.vigiar_editos(heroi, "habilidade", heroi.habilidades()[0][0], [rei])
    rei.vida = round(rei.vida_maxima * 0.35)
    for passiva in rei.passivas:                  # a vida baixa faz a Fúria começar
        passiva.ao_receber_dano(rei, 1, combate)
    combate.atual, combate.pode_agir = rei, True
    combate.usar_habilidade(rei, "banquete_real")
    tela.estado, tela.menu = "animando", "principal"
    tela.enfileirar()
    mostrar(app, None, quadros=26)
    salvar(app, "reino_5a_rei_banquete_furia")


def cena_reino_rainha(app):
    """Reino dos Ratos, etapa 5B: o Rei foge para o trono (a pausa para itens, sem fuga), a Rainha dos Ratos com a
    roda inteira e o Rei sentado no trono ao fundo, a roda pela metade com o nó exposto, e o Rei voltando."""
    from roguelike.encontros import MontadorDeCombate
    from telas.entre_ondas import TelaEntreOndas
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    run.area = total
    run.encontro = MontadorDeCombate(run.regiao, total, run.rng("previa"), 4, False, total).chefe()
    run.estado = "encontro"
    combate = run.criar_combate()
    rei = combate.inimigos[0]
    for _ in range(4):                            # o Rei cai: foge para o trono
        combate.causar_dano(rei, 9999, run.grupo.herois[0])
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 9999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    for heroi, fracao in zip(run.grupo.herois, (0.7, 0.45, 0.9, 0.6)):
        heroi.vida = round(heroi.vida_maxima * fracao)
    tela = TelaEntreOndas(app, run)
    mostrar(app, tela, quadros=2)
    tela.narracao.pular()
    mostrar(app, None, quadros=1)
    salvar(app, "reino_5b_pausa_do_trono")

    run.proxima_onda()
    tela = TelaCombate(app, run, run.encontro, lambda r: None)
    mostrar(app, tela, quadros=12)
    salvar(app, "reino_5b_rainha")

    rainha = tela.combate.inimigos[0]
    for rato in rainha.roda[1:8:2]:                # metade da roda cai: o nó fica exposto
        tela.combate.causar_dano(rato, 9999, run.grupo.herois[0])
    tela.enfileirar()
    mostrar(app, None, quadros=14)
    salvar(app, "reino_5b_no_exposto")

    for rato in list(rainha.ratos_vivos()):
        tela.combate.causar_dano(rato, 9999, run.grupo.herois[0])
    tela.combate.verificar_fim()
    tela.enfileirar()
    mostrar(app, None, quadros=90)
    salvar(app, "reino_5b_rei_volta")


def cena_reino_5r1_salao_e_agua(app):
    """Reino dos Ratos, etapa 5R1: o Salão do Trono refeito (trono de ratos e ouro, rosácea, nó da Rainha no teto)
    nos 4 níveis da água (o chão troca e os lutadores afundam), o Rei sentado no trono na luta da Rainha, e a água
    funda nas Galerias e alta na Catedral Roída."""
    from roguelike.encontros import MontadorDeCombate, EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    run.area = total
    encontro = MontadorDeCombate(run.regiao, total, run.rng("previa"), 4, False, total).chefe()
    tela = TelaCombate(app, run, encontro, lambda r: None)
    mostrar(app, tela, quadros=2)
    agua = next(a for a in tela.combate.ambientes if a.tipo == "agua")
    for nivel, nome in ((0, "seca"), (1, "rasa"), (2, "funda"), (3, "alta")):
        agua.nivel = nivel
        mostrar(app, None, quadros=12)
        salvar(app, f"reino_5r1_salao_agua_{nome}")
    agua.nivel = 1
    tela.no_trono = {"chave": "rei_dos_ratos"}                    # (como na luta da Rainha)
    tela.lado_inimigos[0].sumir()
    mostrar(app, None, quadros=8)
    salvar(app, "reino_5r1_rei_no_trono")
    inimigos = ["rato_comum", "ratazana_gigante", "rato_da_peste"]
    for area, nivel, nome in ((1, 2, "galerias_agua_funda"), (total - 1, 3, "catedral_agua_alta")):
        run.area = area
        tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos),
                           lambda r: None)
        mostrar(app, tela, quadros=2)
        next(a for a in tela.combate.ambientes if a.tipo == "agua").nivel = nivel
        mostrar(app, None, quadros=12)
        salvar(app, f"reino_5r1_{nome}")


def cena_reino_5r2_rei(app):
    """Reino dos Ratos, etapa 5R2: o Rei dos Ratos refeito no Salão; ele ergue o cetro e o Édito Real aparece grande
    em vermelho e dourado (entrando e voando para o pergaminho); depois a vida acaba, ele corre de lado até o trono
    e fica sentado nele."""
    from roguelike.encontros import MontadorDeCombate
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    run.area = total
    encontro = MontadorDeCombate(run.regiao, total, run.rng("previa"), 4, False, total).chefe()
    tela = TelaCombate(app, run, encontro, lambda r: None)
    combate = tela.combate
    rei = combate.inimigos[0]
    mostrar(app, tela, quadros=1)
    for _ in range(300):                          # anima até ser a vez de um herói
        if tela.heroi() is not None:
            break
        app.passo(0.2, [])
    salvar(app, "reino_5r2_rei_na_luta")

    edito = next(p for p in rei.passivas if p.dados.get("golpe") == "edito_real")
    edito.disparar(rei, combate)                  # o Rei ergue o cetro e proclama (a passiva de 3 em 3 turnos)
    tela.estado, tela.menu = "animando", "principal"
    tela.enfileirar()
    for _ in range(40):
        if tela.proclamacao is not None:
            break
        app.passo(0.1, [])
    for _ in range(6):
        app.passo(0.1, [])
    salvar(app, "reino_5r2_edito_proclamado")
    for _ in range(19):
        app.passo(0.1, [])
    salvar(app, "reino_5r2_edito_voando")
    for _ in range(8):
        app.passo(0.1, [])
    salvar(app, "reino_5r2_edito_no_pergaminho")

    for _ in range(4):                            # a vida acaba: ele corre para o trono
        combate.causar_dano(rei, 9999, run.grupo.herois[0])
    tela.enfileirar()
    for _ in range(60):
        if tela.corrida is not None:
            break
        app.passo(0.1, [])
    for _ in range(6):
        app.passo(0.1, [])
    salvar(app, "reino_5r2_rei_correndo")
    for _ in range(40):
        if tela.corrida is None:
            break
        app.passo(0.1, [])
    app.passo(0.3, [])
    salvar(app, "reino_5r2_rei_no_trono")


def cena_reino_5r3_roda(app):
    """Reino dos Ratos, etapa 5R3: a Rainha refeita como coroa-ninho (a coroa presa no nó de caudas, os dois ratos da
    vez do lado de fora, presos pelo rabo, e os outros esperando lá dentro): descendo do teto, a luta, o meio de um
    giro (um pula para dentro da coroa, o outro troca de fileira) e a roda já girada."""
    from roguelike.encontros import MontadorDeCombate
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    run.area = total
    run.encontro = MontadorDeCombate(run.regiao, total, run.rng("previa"), 4, False, total).chefe()
    run.estado = "encontro"
    combate = run.criar_combate()
    rei = combate.inimigos[0]
    for _ in range(4):                            # o Rei cai: foge para o trono
        combate.causar_dano(rei, 9999, run.grupo.herois[0])
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 9999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    run.proxima_onda()
    tela = TelaCombate(app, run, run.encontro, lambda r: None)
    app.trocar(tela)
    for _ in range(4):
        app.passo(0.15, [])
    salvar(app, "reino_5r3_descendo")
    mostrar(app, None, quadros=10)
    salvar(app, "reino_5r3_roda")
    rainha = tela.combate.inimigos[0]
    roda = next(p for p in rainha.passivas if hasattr(p, "proximo_giro"))
    roda.nova_rodada(rainha, tela.combate)        # a roda gira uma casa (como no começo de uma rodada)
    for _ in range(3):
        app.passo(0.1, [])
    salvar(app, "reino_5r3_girando")
    mostrar(app, None, quadros=8)
    salvar(app, "reino_5r3_girou")


def cena_reino_5c_corte_completa(app):
    """Reino dos Ratos, etapa 5C: a 2ª carta do chefe depois da 1ª vitória (A Corte Completa); o Rei governando do
    trono enquanto a Rainha luta (o painel "O Rei no Trono"), proclamando o Édito sentado, apontando o cetro (o clarão
    de ouro vai até o herói); a Rainha cai e ele salta do trono; e a aba do Reino no bestiário (7 abas por fileira)."""
    from roguelike.encontros import MontadorDeCombate
    from roguelike.eventos import Evento
    from roguelike.golpes import golpe
    from telas import fluxo
    from telas.bestiario import TelaBestiario
    from telas.combate.tela import TelaCombate
    app.progresso.conquistas.add("chefe:rei_dos_ratos")
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()
    run.area = total
    fluxo.ir_para_mapa(app, run)
    mostrar(app, None)
    salvar(app, "reino_5c_mapa_duas_cartas")

    encontro = MontadorDeCombate(run.regiao, total, run.rng("previa"), 4, False, total).modo_dificil()
    tela = TelaCombate(app, run, encontro, lambda r: None)
    combate = tela.combate
    rei = next(i for i in combate.inimigos if i.chave == "rei_dos_ratos")
    mostrar(app, tela, quadros=1)
    for _ in range(300):                          # anima até ser a vez de um herói
        if tela.heroi() is not None:
            break
        app.passo(0.2, [])
    salvar(app, "reino_5c_rei_no_trono")

    edito = next(p for p in rei.passivas if p.dados.get("golpe") == "edito_real")
    edito.disparar(rei, combate)                  # o Rei ergue o cetro sentado e proclama
    tela.estado, tela.menu = "animando", "principal"
    tela.enfileirar()
    for _ in range(40):
        if tela.proclamacao is not None:
            break
        app.passo(0.1, [])
    for _ in range(6):
        app.passo(0.1, [])
    salvar(app, "reino_5c_edito_sentado")
    for _ in range(30):
        app.passo(0.1, [])
    salvar(app, "reino_5c_edito_e_painel")

    imposto = golpe("imposto_real")               # do trono: aponta o cetro e o clarão de ouro voa até o herói
    alvo = run.grupo.herois[1]
    combate.registrar(Evento("habilidade", rei, alvo, texto=f"{rei.nome} usou {imposto.nome}!", habilidade=imposto,
                             alvos=[alvo]))
    combate.aplicar_efeitos(rei, imposto.efeitos, [alvo], 1)
    tela.enfileirar()
    for _ in range(6):
        app.passo(0.05, [])
    salvar(app, "reino_5c_cetro_apontado")

    rainha = next(i for i in combate.inimigos if i.chave == "rainha_dos_ratos")
    for rato in list(rainha.roda):                # a Rainha cai: o Rei salta do trono
        combate.causar_dano(rato, 9999, run.grupo.herois[0])
    tela.enfileirar()
    for _ in range(300):
        if not any(getattr(v, "fixo", False) for v in tela.lado_inimigos):
            break
        app.passo(0.1, [])
    app.passo(0.1, [])
    salvar(app, "reino_5c_rei_salta")
    mostrar(app, None, quadros=10)
    salvar(app, "reino_5c_rei_na_luta")

    app.progresso.abates.update({"rei_dos_ratos": 1, "rainha_dos_ratos": 1, "rato_comum": 40, "ratazana_gigante": 6,
                                 "medico_da_peste_corrompido": 1, "mordedor_da_rainha": 3, "queijo_real": 1})
    tela = TelaBestiario(app)
    tela.trocar_secao("reino_dos_ratos")
    tela.ver("rei_dos_ratos")
    mostrar(app, tela)
    salvar(app, "reino_5c_bestiario")


def cena_heroi_medico(app):
    """Etapa 6A: o Médico da Peste liberado (a Rainha caiu): a tela de herói novo, a Capitã, o Mago Ancião (as
    subclasses), o acampamento com ele na fogueira, o Espelho (a árvore), o Grimório, o Baú com 11 classes e o combate
    com o menu de golpes dele aberto."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas import fluxo
    from telas.bau import TelaBau
    from telas.capitao import TelaCapitao
    from telas.combate.tela import TelaCombate
    from telas.espelho import TelaEspelho
    from telas.grimorio import TelaGrimorio
    from telas.mago_anciao import TelaMagoAnciao
    progresso = app.progresso
    progresso.conquistas.add("chefe:rainha_dos_ratos")
    fluxo.ir_para_acampamento(app)
    mostrar(app, None, quadros=14)
    salvar(app, "medico_novo_heroi")
    expedicao = progresso.expedicao_atual()
    expedicao.vagas[1].trocar_classe("medico_da_peste")
    mostrar(app, TelaCapitao(app))
    salvar(app, "medico_capita")
    tela = TelaMagoAnciao(app)
    tela.escolher_vaga(1)
    tela.trocar_aba("subclasse")
    mostrar(app, tela)
    salvar(app, "medico_mago_anciao")
    fluxo.ir_para_acampamento(app)
    mostrar(app, None, quadros=8)
    salvar(app, "medico_acampamento")
    tela = TelaEspelho(app)
    tela.escolher_classe("medico_da_peste")
    mostrar(app, tela)
    salvar(app, "medico_espelho")
    progresso.golpes_descobertos |= {"lanceta", "tonico_amargo", "frasco_de_fumaca", "unguento_de_ervas", "cauterizar"}
    mostrar(app, TelaGrimorio(app, "medico_da_peste"))
    salvar(app, "medico_grimorio")
    mostrar(app, TelaBau(app))
    salvar(app, "medico_bau")

    from roguelike.classes import criar_heroi
    herois = [criar_heroi("guerreiro"), criar_heroi("medico_da_peste", subclasse="boticario"), criar_heroi("sacerdote")]
    herois[1].nome = "Ilse"
    run = progresso.criar_run(herois, "MEDICO")
    for heroi in herois:
        for _ in range(5):
            heroi.subir_nivel()
        heroi.curar_tudo()
    inimigos = ["rato_da_peste", "ratazana_gigante", "rato_alquimista"]
    run.regiao_atual = "reino_dos_ratos"
    run.area = 2
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    mostrar(app, tela, quadros=1)
    for _ in range(300):                          # anima até ser a vez do Médico
        if tela.heroi() is herois[1]:
            break
        if tela.heroi() is not None:
            tela.concentrar()
        app.passo(0.2, [])
    if tela.heroi() is not None:
        tela.abrir_menu("habilidades")
    mostrar(app, None, quadros=2)
    salvar(app, "medico_combate_golpes")


def cena_heroi_senhor(app):
    """Etapa 6B: o Senhor dos Ratos liberado (venceu A Corte Completa): a tela de herói novo, a Capitã, o Mago Ancião,
    o Grimório com as 12 classes, o Baú, e o combate com os ratos, a ratazana e o enxame de moscas dele."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.golpes import golpe
    from telas import fluxo
    from telas.bau import TelaBau
    from telas.capitao import TelaCapitao
    from telas.combate.tela import TelaCombate
    from telas.grimorio import TelaGrimorio
    from telas.mago_anciao import TelaMagoAnciao
    progresso = app.progresso
    progresso.conquistas |= {"chefe:rainha_dos_ratos", "feito:corte_completa"}
    progresso.herois_anunciados.add("medico_da_peste")
    fluxo.ir_para_acampamento(app)
    mostrar(app, None, quadros=14)
    salvar(app, "senhor_novo_heroi")
    expedicao = progresso.expedicao_atual()
    expedicao.vagas[1].trocar_classe("senhor_dos_ratos")
    expedicao.vagas[2].trocar_classe("medico_da_peste")
    mostrar(app, TelaCapitao(app))
    salvar(app, "senhor_capita")
    tela = TelaMagoAnciao(app)
    tela.escolher_vaga(1)
    tela.trocar_aba("subclasse")
    mostrar(app, tela)
    salvar(app, "senhor_mago_anciao")
    progresso.golpes_descobertos |= {"toque_pestilento", "chamar_ratos", "nuvem_de_moscas", "sugar_a_vida"}
    mostrar(app, TelaGrimorio(app, "senhor_dos_ratos"))
    salvar(app, "senhor_grimorio")
    mostrar(app, TelaBau(app))
    salvar(app, "senhor_bau")

    from roguelike.classes import criar_heroi
    herois = [criar_heroi("guerreiro"), criar_heroi("senhor_dos_ratos", subclasse="rei_dos_bandos"), criar_heroi("sacerdote")]
    herois[1].nome = "Corvo"
    run = progresso.criar_run(herois, "SENHOR")
    for heroi in herois:
        for _ in range(5):
            heroi.subir_nivel()
        heroi.curar_tudo()
    inimigos = ["carnical", "esqueleto", "orc"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    mostrar(app, tela, quadros=1)
    senhor = herois[1]
    for chave in ("chamar_ratazana", "chamar_ratos"):                             # o bando atende
        tela.combate.aplicar_efeitos(senhor, golpe(chave).efeitos, [senhor], 1)
    tela.enfileirar()
    mostrar(app, None, quadros=12)
    salvar(app, "senhor_combate_bando")
    for invocacao in list(tela.combate.invocacoes_de(senhor))[1:]:                # (os ratos se vão: espaço para o enxame)
        tela.combate.morrer(invocacao)
    tela.combate.aplicar_efeitos(senhor, golpe("nuvem_de_moscas").efeitos, [senhor], 1)
    tela.enfileirar()
    for _ in range(300):                                                       # anima até ser a vez de um herói
        if tela.heroi() is senhor:
            break
        if tela.heroi() is not None:
            tela.concentrar()
        app.passo(0.2, [])
    if tela.heroi() is not None:
        tela.abrir_menu("habilidades")
    mostrar(app, None, quadros=2)
    salvar(app, "senhor_combate_moscas")


def cena_reino_7a_itens(app):
    """Etapa 7A: os itens do Reino. O inventário com os materiais e os consumíveis no baú; heróis vestindo as peças
    (o Rato de Estimação no ombro, o Machado do Carrasco, a Lança de Agulha...); a fabricação com as receitas do Reino e a
    Forja dos Anões com o Machado e o Pingente; e as recompensas de vencer a Rainha (o Nó de Caudas)."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.run import Recompensa
    from telas import fluxo
    from telas.combate.tela import TelaCombate
    materiais = ["pelo_sarnento", "dente_amarelo", "cauda_atada", "bubao_seco", "tampinha_dourada", "naco_de_queijo_real",
                 "moeda_do_esgoto", "pena_do_xama", "no_de_caudas"]
    consumiveis = ["veneno_de_rato", "sais_de_cheiro", "ratoeira", "vela_de_sebo", "queijo_mofado", "tonico_do_medico"]
    run = criar_run(app, ("guerreiro", "sacerdote", "mago", "bardo"))
    for chave in materiais + consumiveis:
        run.grupo.bau.adicionar(chave, 3)
    vestir = {0: ["machado_do_carrasco", "capuz_de_trapos", "botas_de_esgoto", "pingente_do_no_de_caudas"],
              1: ["rato_de_estimacao", "escudo_de_tampa_de_lata"], 2: ["lanca_de_agulha", "rato_de_estimacao"]}
    for indice, chaves in vestir.items():
        for chave in chaves:
            run.grupo.bau.adicionar(chave)
            run.grupo.equipar(run.grupo.herois[indice], chave, run.grupo.bau)
    for chave in materiais:
        run.descobertas.update(__import__("roguelike.fabricacao", fromlist=["x"]).receitas_reveladas_por(chave))
    fluxo.abrir_inventario(app, run, lambda: None, "bau")
    mostrar(app, None)
    salvar(app, "reino_7a_inventario")
    for indice in (0, 1):
        fluxo.abrir_inventario(app, run, lambda: None, "bau", indice=indice)
        mostrar(app, None)
        salvar(app, f"reino_7a_vestido_{indice}")
    run.grupo.herois[0].raca = "anao_das_profundezas"
    fluxo.abrir_fabricacao(app, run, lambda: None)
    mostrar(app, None)
    salvar(app, "reino_7a_fabricacao")
    app.atual.trocar_aba("forja")
    mostrar(app, None)
    salvar(app, "reino_7a_forja_ana")
    inimigos = ["rato_comum", "ratazana_gigante"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    mostrar(app, tela, quadros=1)
    recompensa = Recompensa()
    recompensa.xp, recompensa.ouro = 160, 94
    recompensa.itens = {"no_de_caudas": 1, "cauda_atada": 3, "tonico_do_medico": 2, "glandula_de_veneno": 1, "couro_grosso": 2,
                        "pelo_sarnento": 2, "dente_amarelo": 1}
    tela.combate.resultado = "vitoria"
    tela.recompensa, tela.estado = recompensa, "fim"
    tela.fila.clear()
    mostrar(app, None, quadros=2)
    salvar(app, "reino_7a_recompensa_da_rainha")


def cena_reino_7b_sets(app):
    """Etapa 7B: os três sets do Reino vestidos por inteiro (Guarda Real Roedora no guerreiro, Realeza Roedora no bardo,
    Traje do Médico da Peste no médico) e a dica de uma peça com os bônus do set."""
    from roguelike.classes import criar_heroi
    from telas import fluxo
    app.progresso.conquistas.add("chefe:rainha_dos_ratos")
    herois = [criar_heroi("guerreiro"), criar_heroi("bardo"), criar_heroi("medico_da_peste")]
    for nome, heroi in zip(("Helka", "Corvino", "Ilse"), herois):
        heroi.nome = nome
    run = app.progresso.criar_run(herois, "SETS")
    sets = [["elmo_de_dedal", "tabardo_da_coroa", "lanca_de_agulha", "escudo_de_tampa_de_lata"],
            ["coroa_do_rei_dos_ratos", "capa_de_veludo_roido", "cetro_do_rei_dos_ratos", "anel_de_tampinha"],
            ["mascara_de_bico_da_peste", "sobretudo_encerado", "botas_enceradas", "bengala_do_medico"]]
    for heroi, pecas in zip(herois, sets):
        for chave in pecas:
            run.grupo.bau.adicionar(chave)
            run.grupo.equipar(heroi, chave, run.grupo.bau)
    for indice, nome in enumerate(("guarda_real", "realeza", "traje_do_medico")):
        fluxo.abrir_inventario(app, run, lambda: None, "bau", indice=indice)
        mostrar(app, None)
        salvar(app, f"reino_7b_{nome}")
    fluxo.abrir_inventario(app, run, lambda: None, "bau", indice=1)
    mostrar(app, None)
    app.atual.mouse = (70, 150)                                   # em cima da Coroa: a dica com os bônus do set
    app.atual.usando_teclado = False
    mostrar(app, None, quadros=2)
    salvar(app, "reino_7b_dica_do_set")


def cena_reino_7c_integracao(app):
    """Etapa 7C: as Insígnias do Reino (feitas), o Baú com o Manto da Roda e os chapéus novos no Senhor dos Ratos, a
    história do Rei em duas partes (1 e 3 vitórias), o Rato Branco no acampamento (sentado e correndo), as Opções com a
    linha dos bichos e um combate com os heróis usando as skins novas."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas import fluxo
    from telas.bau import TelaBau
    from telas.bestiario import TelaBestiario
    from telas.combate.tela import TelaCombate
    from telas.insignias import TelaInsignias
    from telas.opcoes import TelaOpcoes
    progresso = app.progresso
    progresso.abates.update({"rato_comum": 160, "ratazana_gigante": 22, "rato_da_peste": 50, "rainha_dos_ratos": 3,
                             "rei_dos_ratos": 1, "flautista_caido": 1})
    progresso.conquistas |= {"chefe:rainha_dos_ratos", "chefe:rei_dos_ratos", "chefe:flautista_caido",
                             "feito:corte_completa", "feito:imune"}
    progresso.herois_anunciados |= {"medico_da_peste", "senhor_dos_ratos"}
    progresso.verificar_conquistas()
    tela = TelaInsignias(app)
    mostrar(app, tela)
    tela.lista.ir_para(300, imediato=True)
    mostrar(app, None, quadros=2)
    salvar(app, "reino_7c_insignias")
    tela.lista.ir_para(9999, imediato=True)
    mostrar(app, None, quadros=2)
    salvar(app, "reino_7c_insignias_fim")
    progresso.equipar_skin("senhor_dos_ratos", "roupa", "manto_da_roda")
    progresso.equipar_skin("senhor_dos_ratos", "chapeu", "coroa_do_esgoto")
    progresso.equipar_skin("senhor_dos_ratos", "arma", "luz_limpa")
    mostrar(app, TelaBau(app, "senhor_dos_ratos"))
    salvar(app, "reino_7c_bau_senhor")
    bestiario = TelaBestiario(app)
    bestiario.trocar_secao("reino_dos_ratos")
    bestiario.ver("rei_dos_ratos")
    bestiario.lendo = True
    mostrar(app, bestiario)
    salvar(app, "reino_7c_lore_1_vitoria")
    progresso.abates["rei_dos_ratos"] = 3
    mostrar(app, None, quadros=1)
    salvar(app, "reino_7c_lore_3_vitorias")
    fluxo.ir_para_acampamento(app)
    mostrar(app, None, quadros=8)
    salvar(app, "reino_7c_acampamento_rato")
    pet = app.atual.pets[0]
    pet.correr_para(1)
    for _ in range(9):
        app.passo(0.1, [])
    salvar(app, "reino_7c_acampamento_rato_correndo")
    mostrar(app, TelaOpcoes(app, lambda: None))
    salvar(app, "reino_7c_opcoes")
    for classe, camada, chave in (("guerreiro", "chapeu", "coroa_de_tampinhas"), ("medico_da_peste", "chapeu", "chapeu_de_flautista"),
                                  ("bardo", "chapeu", "mascara_do_doutor"), ("guerreiro", "arma", "luz_limpa")):
        progresso.equipar_skin(classe, camada, chave)
    run = criar_run(app, ("guerreiro", "medico_da_peste", "senhor_dos_ratos", "bardo"))
    inimigos = ["rato_comum", "rato_da_peste"]
    mostrar(app, TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None),
            quadros=8)
    salvar(app, "reino_7c_combate_com_as_skins")


def cena_reino_mini_chefes(app):
    """Reino dos Ratos, etapa 3C2: o Médico da Peste Corrompido (com o Mendigo) usando a Sangria nas Galerias, e o
    Flautista Caído na Catedral Roída chamando um bando e encantando um herói."""
    from roguelike.encontros import EncontroCombate
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    total = run.areas_da_regiao()

    run.area = 1
    inimigos = ["medico_da_peste_corrompido", "mendigo_bubonico"]
    tela = TelaCombate(app, run, EncontroCombate("Médico da Peste Corrompido", "", 5, inimigos, "mini_chefe"), lambda r: None)
    mostrar(app, tela, quadros=8)
    salvar(app, "reino_3c2_medico")
    combate = tela.combate
    medico = combate.inimigos[0]
    medico.energia = 5
    combate.atual, combate.pode_agir = medico, True
    combate.usar_habilidade(medico, "sangria")
    tela.enfileirar()
    mostrar(app, None, quadros=5)
    salvar(app, "reino_3c2_medico_sangria")

    run.area = total - 1
    tela = TelaCombate(app, run, EncontroCombate("Flautista Caído", "", 5, ["flautista_caido"], "mini_chefe"), lambda r: None)
    mostrar(app, tela, quadros=8)
    combate = tela.combate
    flautista = combate.inimigos[0]
    flautista.passivas[0].disparar(flautista, combate)            # a marcha: chega um bando
    heroi = run.grupo.herois[1]
    combate.aplicar_status(heroi, "encantado", origem=flautista)
    tela.enfileirar()
    mostrar(app, None, quadros=16)
    salvar(app, "reino_3c2_flautista")


def cena_reino_flauta_do_cacador(app):
    """Reino dos Ratos, etapa 3C2: um herói com a Flauta do Caçador de Ratos encanta o bando, e os ratos mordem a
    Ratazana."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from roguelike.itens import item
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    run.area = run.areas_da_regiao() - 1
    bardo = run.grupo.herois[3]
    bardo.equipar(item("flauta_do_cacador_de_ratos"))
    inimigos = ["rato_comum", "ratazana_gigante"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    combate = tela.combate
    bando = combate.inimigos[0]
    mostrar(app, tela, quadros=6)
    combate.aplicar_status(bando, "encantado", origem=bardo)
    combate.fila = [bando]
    combate.comecar_turno()
    tela.enfileirar()
    tela.condutor.turno_em_andamento = True
    mostrar(app, None, quadros=3)
    salvar(app, "reino_3c2_flauta_encanta_o_bando")


def cena_reino_corte_dos_ratos(app):
    """Reino dos Ratos, etapa 3B2: Xamã, Guarda Real e Arauto (com a corneta contando), o Guarda entrando na frente
    da Ratazana ferida, os reforços chegando e o Xamã reerguendo um rato caído."""
    from roguelike.encontros import EncontroCombate, descrever_inimigos
    from telas.combate.tela import TelaCombate
    run = criar_run(app)
    run.regiao_atual = "reino_dos_ratos"
    run.regioes_visitadas.append(run.regiao_atual)
    run.area = run.areas_da_regiao() // 2              # Mercado Roedor (escuro, sem água)
    inimigos = ["rato_guarda_real", "ratazana_gigante", "rato_xama", "rato_arauto"]
    tela = TelaCombate(app, run, EncontroCombate("Combate", descrever_inimigos(inimigos), 2, inimigos), lambda r: None)
    combate = tela.combate
    guarda, ratazana, xama, arauto = combate.inimigos
    mostrar(app, tela, quadros=8)
    salvar(app, "reino_3b2_combate")

    visual = tela.visual(arauto)
    area = next((r for r, s in visual.areas_de_status if s.chave == "corneta"), None)
    if area is not None:
        tela.mouse = area.center                       # a dica da corneta
        mostrar(app, None, quadros=1)
        salvar(app, "reino_3b2_dica_corneta")
        tela.mouse = (0, 0)

    heroi = run.grupo.herois[1]
    ratazana.vida = ratazana.vida_maxima // 3
    combate.rodada = max(1, combate.rodada)
    combate.atual, combate.pode_agir = heroi, True
    golpe = next(h for h, _ in heroi.habilidades() if h.escolhe_alvo() and h.ofensiva() and h.custo == 0)
    combate.usar_habilidade(heroi, golpe, ratazana)
    tela.enfileirar()
    mostrar(app, None, quadros=3)
    salvar(app, "reino_3b2_guarda_protege")

    combate.reforcar(arauto, ["rato_comum", "rato_da_peste"], limite_na_luta=2)
    tela.enfileirar()
    mostrar(app, None, quadros=4)
    salvar(app, "reino_3b2_reforcos")

    combate.causar_dano(ratazana, 999, heroi)
    tela.enfileirar()
    mostrar(app, None, quadros=8)                      # o corpo some da arena
    combate.reviver(ratazana, 0.4, xama, texto=f"{xama.nome} reergueu {ratazana.nome}!")
    tela.enfileirar()
    mostrar(app, None, quadros=3)
    salvar(app, "reino_3b2_reerguer")


CENAS = {nome[5:]: f for nome, f in sorted(globals().items()) if nome.startswith("cena_")}
PASTA_ATUAL = None                    # None = só confere (testes), sem gravar PNG
_salvas = []
_problemas = {}


def salvar(app, nome):
    """Redesenha a tela atual conferindo o layout (ui/layout.py) e os textos cortados, e salva o PNG."""
    from ui import desenho
    from ui import texto as modulo_texto
    from ui.layout import conferir, Problema
    cortes_antes = len(modulo_texto.TRUNCAMENTOS)
    desenho.REGISTRO = []
    try:
        app.atual.desenhar(app.tela)
        problemas = conferir(desenho.REGISTRO, app.tela)
    finally:
        desenho.REGISTRO = None
    app.desenhar_por_cima()                          # (o aviso de conexão de uma partida em grupo, como no jogo)
    problemas += [Problema("cortado com ...", pygame.Rect(0, 0, largura, 0), conteudo)
                  for conteudo, largura in modulo_texto.TRUNCAMENTOS[cortes_antes:]]
    _problemas[nome] = problemas
    app.notificacoes.desenhar(app.tela)
    if PASTA_ATUAL is not None:
        pygame.image.save(app.tela, os.path.join(PASTA_ATUAL, nome + ".png"))
    _salvas.append(nome)


def rodar_cenas(filtro=()):
    """Roda as cenas (todas, ou as que contêm algum texto do filtro).

    Devolve ({print: [problemas]}, [(cena, erro)])."""
    from caminhos import CAMINHOS
    pasta_do_jogador = (CAMINHOS.base_do_jogador, CAMINHOS.perfil)   # preparar_app troca: volta no fim
    _salvas.clear()
    _problemas.clear()
    falhas = []
    try:
        for nome, cena in CENAS.items():
            if filtro and not any(f in nome for f in filtro):
                continue
            with tempfile.TemporaryDirectory() as pasta_temp:
                try:
                    app = preparar_app(pasta_temp)
                    antes = len(_salvas)
                    cena(app)
                    if len(_salvas) == antes:      # a cena não salvou sozinha: salva o quadro final
                        salvar(app, nome)
                except Exception as erro:          # uma cena quebrada não impede as outras
                    falhas.append((nome, repr(erro)))
    finally:
        CAMINHOS.base_do_jogador, CAMINHOS.perfil = pasta_do_jogador
    return dict(_problemas), falhas


def main():
    global PASTA_ATUAL
    rotulo = sys.argv[1] if len(sys.argv) > 1 else "atual"
    filtro = sys.argv[2:]
    PASTA_ATUAL = os.path.join(PASTA_SAIDA, rotulo)
    os.makedirs(PASTA_ATUAL, exist_ok=True)
    _, falhas = rodar_cenas(filtro)
    print(f"{len(_salvas)} prints em {PASTA_ATUAL}")
    relatorio = []
    for nome in _salvas:
        lista = _problemas.get(nome, [])
        relatorio.append(f"{nome}: {len(lista)} problema(s)")
        relatorio += [f"    {p}" for p in lista]
    with open(os.path.join(PASTA_ATUAL, "problemas.txt"), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(relatorio) + "\n")
    print(f"layout: {sum(len(v) for v in _problemas.values())} problema(s) (detalhes em problemas.txt)")
    for nome, erro in falhas:
        print(f"  FALHOU {nome}: {erro}")


if __name__ == "__main__":
    main()
