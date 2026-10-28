"""MP8: robustez do multiplayer.

O critério de aceite: desconectar e reconectar um jogador no meio da batalha sem quebrar a run. Aqui:
- a retomada (o ponto seguro + os comandos) refaz o estado de agora em qualquer ponto de uma run (até numa luta);
- quem volta com a chave recebe a run no mesmo ponto; quem dessincronizou pede o estado e fica igual;
- duas App de verdade: a Bia cai no meio da luta, a IA joga por ela, ela volta sozinha e o grupo segue igual;
- o host fecha no meio da luta, retoma a partida salva e a Bia volta pelo código;
- mensagens repetidas, latência, avisos do baú e de lendário, o aviso do firewall e a lista com "Voltar à partida".
Tudo em 127.0.0.1 (o Windows não pergunta do firewall nos testes).
"""

import copy
import json
import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelike import comandos as C
from roguelike.comandos import criar_comando
from roguelike.dados import regras
from roguelike.estado import BAU, EstadoDoJogo
from roguelike.processador import ProcessadorDeComandos
from roguelike.progresso import Progresso
from roguelike.run import Run
from rede.partida import PartidaCliente, PartidaHost
from rede.retomada import Retomada, carregar_partida_salva, ponto_seguro
from rede.sessoes import SessaoCliente
from test_coop import Dupla, ate_a_luta
from test_rede import COR, LOCAL, esperar, partidas, todos_prontos   # noqa: F401 (partidas é a fixture)


class SessaoDeTeste:
    """O mínimo que a Retomada pede de uma sessão (Partida.comecar_run devolve uma de verdade)."""

    def __init__(self, run):
        self.estado = EstadoDoJogo(run)
        self.processador = ProcessadorDeComandos(self.estado)


# ---------------- a retomada (lógica) ----------------
def test_retomada_refaz_o_estado_de_agora_em_qualquer_ponto():
    """O piloto joga algumas áreas; a cada comando o "host" anota. Em vários pontos (no mapa, no meio de lutas),
    a run do ponto seguro + os comandos dá exatamente o estado de agora, e o ponto anda (a lista não cresce sem fim)."""
    from roguelike.piloto_automatico import Piloto, grupo_padrao
    inicio = json.loads(json.dumps(Progresso().criar_run(grupo_padrao(["guerreiro", "sacerdote", "patrulheira"]),
                                                         "DETERMINISMO").para_dict()))
    piloto = Piloto(Run.de_dict(copy.deepcopy(inicio)))
    piloto.jogar(10)
    registro = piloto.processador.registro
    assert len(registro) > 80
    host = SessaoDeTeste(Run.de_dict(copy.deepcopy(inicio)))
    retomada = Retomada(copy.deepcopy(inicio))
    bases, conferidos, em_luta = set(), 0, 0
    for i, dados in enumerate(registro):
        assert host.processador.executar(criar_comando(dados))
        retomada.anotar(copy.deepcopy(dados), host.estado, comandos_por_ponto=40)
        bases.add(retomada.seq_da_base)
        assert len(retomada.comandos) <= 40 or not ponto_seguro(host.estado)
        if i % 9 == 0 or i == len(registro) - 1:
            volta = retomada.refazer(SessaoDeTeste)
            assert volta.estado.impressao_digital() == host.estado.impressao_digital(), f"comando {i}: {dados}"
            assert volta.seq == i + 1
            conferidos += 1
            em_luta += host.estado.condutor is not None and not host.estado.condutor.terminou()
    assert len(bases) >= 4 and conferidos >= 10 and em_luta >= 2       # o ponto andou; conferiu até no meio de lutas


def test_aplicar_repetido_e_ignorado_e_buraco_dessincroniza():
    run = Progresso().criar_run(__import__("roguelike.piloto_automatico", fromlist=["grupo_padrao"])
                                .grupo_padrao(["guerreiro"]), "SEQ")
    sessao = SessaoCliente(EstadoDoJogo(run), "local", lambda tipo, dados=None: None)
    sessao.aplicar({"seq": 1, "comando": C.Prosseguir(tela="fim").para_dict()})
    sessao.aplicar({"seq": 1, "comando": C.Prosseguir(tela="fim").para_dict()})      # repetido (ex.: antes de retomar)
    sessao.processar()
    assert sessao.seq == 1 and sessao.divergiu is None and len(sessao.processador.registro) == 1
    sessao.aplicar({"seq": 3, "comando": C.Prosseguir(tela="fim").para_dict()})      # pulou o 2
    sessao.processar()
    assert sessao.divergiu and "Faltou" in sessao.divergiu
    sessao.conectado = lambda: False                                                # caiu: nada sai daqui
    assert not sessao.enviar(C.Prosseguir(tela="fim"))


# ---------------- voltar pela rede (só a lógica) ----------------
def comecar(host, clientes, semente="VOLTA"):
    todos_prontos(host, clientes)
    assert host.iniciar(semente) is None
    assert esperar(lambda: all(c.run is not None for c in clientes) and None not in host.sincronia.values(),
                   host, *clientes)


def mover_ossos(partida, quantos=1):
    """Um comando qualquer de quem joga nesta partida (osso da mochila para o baú)."""
    heroi = next(i for i, h in enumerate(partida.run.grupo.herois) if h.jogador.id == partida.eu)
    return partida.sessao.enviar(C.MoverItem(chave="osso", de=heroi, para=BAU, quantidade=quantos))


def test_quem_volta_com_a_chave_recebe_a_run_no_mesmo_ponto(partidas):
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    comecar(host, [bia, caio])
    for partida in (host, bia, caio):
        partida.run.grupo.jogador("j2").mochila.adicionar("osso", 5)
    host.marcar_ponto()                                            # (mexemos na run fora dos comandos: ponto novo)
    assert mover_ossos(bia) and esperar(lambda: host.sessao.seq == 1, host, bia, caio)
    chave = bia.chave_de_volta
    assert chave and bia.id_da_partida == host.id_da_partida
    bia.conexao.fechar()                                           # o jogo da Bia fechou (sem tchau)
    assert esperar(lambda: "j2" in host.desconectados, host, caio)
    estranho = PartidaCliente(Progresso(), "Zé", COR, LOCAL, host.porta, volta={"chave": "outra"})
    assert esperar(lambda: estranho.encerrada, host, estranho, caio)
    assert "já começou" in estranho.motivo_do_fim
    volta = PartidaCliente(Progresso(), "Bia", COR, LOCAL, host.porta, volta={"chave": chave})
    try:
        assert esperar(lambda: volta.run is not None and host.sincronia.get("j2") is True, host, volta, caio)
        assert volta.eu == "j2" and "j2" not in host.desconectados and volta.pegar_run_nova()[1]   # (retomou)
        assert volta.sessao.seq == host.sessao.seq == 1
        assert volta.sessao.estado.impressao_digital() == host.sessao.estado.impressao_digital()
        assert any("Bia voltou" in m.texto for m in host.lobby.chat)
        assert mover_ossos(volta)                                  # volta a mandar nos heróis dela
        assert esperar(lambda: caio.sessao.seq == 2 and volta.sessao.seq == 2, host, volta, caio)
        assert caio.sessao.estado.impressao_digital() == volta.sessao.estado.impressao_digital() == \
            host.sessao.estado.impressao_digital()
    finally:
        volta.fechar()
        estranho.fechar()


def test_quem_dessincroniza_pede_o_estado_e_fica_igual(partidas):
    host, (bia,) = partidas("Ana", "Bia")
    comecar(host, [bia])
    for partida in (host, bia):
        partida.run.grupo.jogador("j2").mochila.adicionar("osso", 5)
    host.marcar_ponto()
    bia.run.grupo.jogador("j2").mochila.adicionar("osso", 1)       # algo mudou só aqui
    assert mover_ossos(bia)
    assert esperar(lambda: bia.sessao.divergiu is not None, host, bia)
    assert esperar(lambda: bia.sessao.divergiu is None and bia.sessao.seq == host.sessao.seq == 1, host, bia)
    assert bia.sessao.estado.impressao_digital() == host.sessao.estado.impressao_digital()
    assert bia.run.grupo.jogador("j2").mochila.quantidade("osso") == 4


def test_latencia_de_cada_um(partidas, monkeypatch):
    monkeypatch.setitem(regras()["multiplayer"], "intervalo_do_ping", 0.05)
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    assert esperar(lambda: host.latencia_de("j2") is not None and bia.latencia_de("j2") is not None
                   and bia.latencia_de("j3") is not None, host, bia, caio)
    assert host.latencia_de("j1") == 0 and bia.latencia_de("j1") == bia.latencia_de("j2") < 1000


def test_host_salva_a_partida_e_retoma_depois(partidas):
    host, (bia,) = partidas("Ana", "Bia")
    comecar(host, [bia], "SALVA")
    for partida in (host, bia):
        partida.run.grupo.jogador("j2").mochila.adicionar("osso", 5)
    host.marcar_ponto()
    assert mover_ossos(bia) and esperar(lambda: bia.sessao.seq == 1, host, bia)
    impressao, chave = host.sessao.estado.impressao_digital(), bia.chave_de_volta
    host.fechar()                                                  # no meio da run: fica salva
    assert esperar(lambda: bia.encerrada, bia) and "ficou salva" in bia.motivo_do_fim
    salva = carregar_partida_salva()
    assert salva is not None and len(salva["retomada"]["comandos"]) == 1
    de_novo = PartidaHost(Progresso(), "Ana", COR, porta=0, endereco=LOCAL, porta_descoberta=False, salva=salva)
    volta = PartidaCliente(Progresso(), "Bia", COR, LOCAL, de_novo.porta, volta={"chave": chave})
    try:
        assert de_novo.jogando() and de_novo.esperando_o_grupo and [j.nome for j in de_novo.faltam_voltar()] == ["Bia"]
        assert de_novo.sessao.estado.impressao_digital() == impressao and de_novo.sessao.seq == 1
        assert esperar(lambda: volta.run is not None and not de_novo.faltam_voltar(), de_novo, volta)
        assert volta.sessao.estado.impressao_digital() == impressao
        assert mover_ossos(volta) and esperar(lambda: volta.sessao.seq == 2, de_novo, volta)
        de_novo.voltar_ao_lobby()                                  # a run acabou: não há mais o que retomar
        assert carregar_partida_salva() is None
    finally:
        volta.fechar()
        de_novo.fechar()


# ---------------- as telas: cair e voltar no meio da luta ----------------
def ate_o_proximo_mapa_igual(dupla, area, segundos=150):
    """As duas App no mapa de uma área depois de 'area', com o mesmo estado (ou a run acabou)."""
    def chegou():
        run = dupla.host.run
        if run is None or run.terminou():
            return True
        return all(type(a.atual).__name__ == "TelaMapa" for a in dupla.apps) and run.area > area and \
            dupla.mesmo_estado()
    return dupla.rodar(chegou, segundos)


def test_cai_no_meio_da_luta_volta_sozinha_e_a_run_segue(tmp_path, monkeypatch):
    """O critério de aceite da MP8."""
    monkeypatch.setitem(regras()["multiplayer"], "intervalo_de_reconexao", 0.2)
    dupla = Dupla(tmp_path)
    try:
        host, bia, bia_app = dupla.host, dupla.bia, dupla.bia_app
        assert host.marcar_ponto()                    # (a Dupla mexeu na run fora dos comandos: o ponto vem depois)
        assert ate_a_luta(dupla)
        seq = host.sessao.seq
        assert dupla.rodar(lambda: host.sessao.seq >= seq + 2, 30)
        area = host.run.area
        bia.conexao.fechar()                                       # a rede da Bia caiu no meio da luta
        bia.fila.put((bia.etiqueta, "fechou", "a rede caiu"))
        assert dupla.rodar(lambda: "j2" in host.desconectados, 10, quem=[dupla.host_app])
        assert bia_app.partida is bia                              # (a Bia ainda não percebeu: a tela dela parou)
        dupla.rodar(lambda: False, 1.5, quem=[dupla.host_app])      # a IA joga pelos heróis dela um pouco
        assert dupla.rodar(lambda: bia.reconectando is not None or bia.run is not None and "j2" not in host.desconectados,
                           10)
        assert dupla.rodar(lambda: bia.reconectando is None and "j2" not in host.desconectados
                           and host.sincronia.get("j2") is True, 20)
        assert bia_app.partida is bia and not bia.encerrada
        assert type(bia_app.atual).__name__ in ("TelaCombate", "TelaMapa", "TelaEvento", "TelaLoja", "TelaServico",
                                                "TelaEntreOndas", "TelaTituloDaArea")
        depois = len(host.sessao.processador.registro)
        assert ate_o_proximo_mapa_igual(dupla, area)
        assert bia.sessao.divergiu is None
        meus = [d for d in host.sessao.processador.registro[depois:] if d.get("jogador") == "j2"]
        assert meus, "a Bia não voltou a mandar nos heróis dela"
        assert any("Bia voltou" in m.texto for m in host.lobby.chat)
    finally:
        dupla.fechar()


def test_host_fecha_no_meio_da_luta_e_retoma(tmp_path, monkeypatch):
    """O host fecha o jogo no meio da luta; depois retoma a partida salva e a Bia entra de novo pelo código."""
    from telas import fluxo
    dupla = Dupla(tmp_path)
    try:
        host_app, bia_app = dupla.host_app, dupla.bia_app
        assert dupla.host.marcar_ponto()
        assert ate_a_luta(dupla)
        seq = dupla.host.sessao.seq
        assert dupla.rodar(lambda: dupla.host.sessao.seq >= seq + 2 and dupla.mesmo_estado(), 30)
        area, impressao = dupla.host.run.area, dupla.host.sessao.ultima_impressao
        fluxo.sair_da_partida(host_app)                            # (Fechar a partida: fica salva)
        assert dupla.rodar(lambda: bia_app.partida is None, 10)
        assert type(bia_app.atual).__name__ == "TelaMultijogador" and "ficou salva" in bia_app.atual.mensagem[0]
        salva = carregar_partida_salva()
        host_app.partida = PartidaHost(host_app.progresso, "Ana", (214, 72, 72), porta=0, endereco=LOCAL,
                                       porta_descoberta=False, salva=salva)
        dupla.host = host_app.partida
        assert dupla.host.sessao.ultima_impressao == impressao
        host_app.passo(0.1, [])
        assert type(host_app.atual).__name__ == "TelaRetomada"
        assert bia_app.opcoes.volta and bia_app.opcoes.volta["id_da_partida"] == dupla.host.id_da_partida
        bia_app.partida = PartidaCliente(bia_app.progresso, "Bia", (86, 146, 226), LOCAL, dupla.host.porta,
                                         volta=bia_app.opcoes.volta)
        dupla.bia = bia_app.partida
        assert dupla.rodar(lambda: type(host_app.atual).__name__ != "TelaRetomada", 20)   # todos de volta: segue
        assert ate_o_proximo_mapa_igual(dupla, area)
        assert dupla.bia.sessao.divergiu is None
    finally:
        dupla.fechar()


# ---------------- avisos e telas ----------------
def test_avisos_do_baú_juntam_e_lendario_avisa(tmp_path):
    from types import SimpleNamespace
    from telas import fluxo
    from telas.base import App
    from roguelike.itens import todos_os_itens
    app = App(janela=False)
    jogadores = {"j1": SimpleNamespace(nome="Ana"), "j2": SimpleNamespace(nome="Bia")}
    app.partida = SimpleNamespace(eu="j1", lobby=SimpleNamespace(jogador=jogadores.get))
    try:
        for _ in range(3):
            fluxo.anotar_aviso_do_bau(app, {"tipo": "mover_item", "jogador": "j2", "chave": "osso", "de": 1,
                                            "para": BAU, "quantidade": 2})
        fluxo.anotar_aviso_do_bau(app, {"tipo": "mover_item", "jogador": "j1", "chave": "osso", "de": 0, "para": BAU})
        fluxo.mostrar_avisos_do_bau(app)
        assert app.notificacoes.fila == []                          # (ainda juntando)
        app.relogio_total += 5
        fluxo.mostrar_avisos_do_bau(app)
        textos = [f"{titulo} {texto}" for titulo, texto, *_ in app.notificacoes.fila]
        assert len(textos) == 1 and "Bia pôs no baú" in textos[0] and "x6" in textos[0]   # um aviso só, juntado
        lendaria = next(c for c, i in todos_os_itens().items() if getattr(i, "raridade", "") == "lendario")
        fluxo.avisar_lendarios(app, {"j2": {lendaria: 1}, "j1": {"osso": 1}})
        textos = [f"{titulo} {texto}" for titulo, texto, *_ in app.notificacoes.fila]
        assert any("Bia ganhou um lendário" in t for t in textos) and len(textos) == 2   # (o osso não é lendário)
    finally:
        app.partida = None


@pytest.fixture
def app_da_tela(tmp_path, monkeypatch):
    from telas import comum, multijogador
    from telas.base import App

    class ProcuradorComMinhaPartida:
        aberto = True

        def __init__(self, *args, **kwargs):
            pass

        def partidas(self):
            return [{"ip": LOCAL, "porta": 1, "nome": "Ana", "jogadores": 2, "maximo": 4, "versao": "?",
                     "aberta": False, "mesma_versao": True, "id_da_partida": "abc123", "em_andamento": True,
                     "fora": ["Bia"]}]

        def fechar(self):
            self.aberto = False
    monkeypatch.setattr(multijogador, "Procurador", ProcuradorComMinhaPartida)
    monkeypatch.setattr(multijogador, "PartidaHost",
                        lambda progresso, nome, cor, **extras: PartidaHost(progresso, nome, cor, porta=0, endereco=LOCAL,
                                                                           porta_descoberta=False, **extras))
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    aplicativo = App(janela=False)
    aplicativo.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    yield aplicativo
    if aplicativo.partida is not None and not aplicativo.partida.encerrada:
        aplicativo.partida.fechar()
    comum.ArquivoDaRun.caminho = None


def test_aviso_do_firewall_so_na_primeira_vez(app_da_tela):
    from telas import fluxo
    from ui.opcoes import Opcoes
    app = app_da_tela
    fluxo.abrir_multijogador(app)
    tela = app.atual
    tela.campo_nome.conteudo = "Ana"
    tela.criar()
    assert app.partida is None and tela.dialogo is not None             # primeiro o aviso
    entendi = next(acao for rotulo, acao in tela.dialogo.opcoes if rotulo == "Entendi")
    entendi()
    app.passo(0.1, [])
    assert app.partida is not None and type(app.atual).__name__ == "TelaLobby"
    assert Opcoes.carregar().avisou_firewall
    fluxo.sair_da_partida(app)
    fluxo.abrir_multijogador(app)
    app.atual.campo_nome.conteudo = "Ana"
    app.atual.criar()                                                   # a segunda vez vai direto
    app.passo(0.1, [])
    assert type(app.atual).__name__ == "TelaLobby"


def test_lista_mostra_voltar_a_minha_partida(app_da_tela):
    from telas import fluxo
    app = app_da_tela
    app.opcoes.volta = {"chave": "x", "id_da_partida": "abc123"}
    fluxo.abrir_multijogador(app)
    app.passo(0.1, [])
    botao = next(b for b in app.atual.botoes if b.texto.startswith("Voltar à partida de Ana"))
    assert botao.ativo
    app.opcoes.volta = {"chave": "x", "id_da_partida": "outra"}
    app.passo(0.1, [])
    botao = next(b for b in app.atual.botoes if b.texto == "Partida de Ana")
    assert not botao.ativo and "esperando Bia" in botao.subtexto
