"""MP5: rede e lobby. Protocolo, código da partida, lobby e partidas de verdade (sockets em 127.0.0.1, no mesmo
processo: host + clientes). Critério de aceite: entram no lobby, conversam e iniciam a run com o MESMO estado.

Tudo escuta só em 127.0.0.1 (o Windows não pergunta do firewall) e em portas livres (porta 0).
"""

import json
import random
import socket
import time

import pytest

from roguelike import comandos as C
from roguelike.dados import regras
from roguelike.estado import BAU
from roguelike.progresso import Progresso
from rede.codigo import codigo_de, endereco_do_codigo, endereco_digitado
from rede.descoberta import Anunciante, Procurador
from rede.lobby import Lobby, cor_valida
from rede.partida import PartidaCliente, PartidaHost, validar_pacote
from rede.protocolo import Leitor, MensagemInvalida, codificar, texto_limpo, PROTOCOLO

LOCAL = "127.0.0.1"
COR = (214, 72, 72)


def esperar(condicao, *partidas, tempo=6.0):
    """Roda as partidas (atualizar) até a condição valer (ou o tempo acabar)."""
    fim = time.monotonic() + tempo
    while time.monotonic() < fim:
        for partida in partidas:
            partida.atualizar()
        if condicao():
            return True
        time.sleep(0.01)
    return False


def resumo(nome, classe="guerreiro"):
    return {"nome": nome, "classe": classe, "raca": "humano", "sprite": classe}


def progresso_com(classes):
    progresso = Progresso()
    expedicao = progresso.expedicao_atual()
    expedicao.vagas = []
    for classe in classes:
        expedicao.adicionar(classe, random.Random(len(expedicao.vagas)))
    return progresso


@pytest.fixture
def partidas():
    """Cria um host e clientes; no fim, fecha todos."""
    criadas = []

    def criar(*nomes, classes=(("guerreiro",), ("mago",), ("sacerdote",), ("patrulheira",))):
        host = PartidaHost(progresso_com(classes[0]), nomes[0], COR, porta=0, endereco=LOCAL, porta_descoberta=False)
        criadas.append(host)
        clientes = []
        for i, nome in enumerate(nomes[1:], start=1):          # um de cada vez: a ordem (e os ids) fica certa
            cliente = PartidaCliente(progresso_com(classes[i]), nome, COR, LOCAL, host.porta, [resumo(nome)])
            criadas.append(cliente)
            clientes.append(cliente)
            assert esperar(lambda: cliente.no_lobby() and len(host.lobby.jogadores) == i + 1, host, *clientes)
        assert esperar(lambda: all(len(c.lobby.jogadores) == len(nomes) for c in clientes), host, *clientes)
        return host, clientes

    yield criar
    for partida in criadas:
        if not partida.encerrada:
            partida.fechar()


def todos_prontos(host, clientes):
    host.definir_meus_herois([resumo("A")])
    host.marcar_pronto(True, host.progresso.pacote_para_partida())
    for cliente in clientes:
        cliente.definir_meus_herois([resumo(cliente.nome_pedido)])
        cliente.marcar_pronto(True, cliente.progresso.pacote_para_partida())
    assert esperar(lambda: all(j.pronto for j in host.lobby.jogadores), host, *clientes)


# ---------------- protocolo ----------------
def test_mensagens_chegam_inteiras_mesmo_em_pedacos():
    bytes_ = codificar("chat", {"texto": "olá, ação! ☠"}) + codificar("ping") + codificar("lobby", {"x": [1, 2]})
    leitor = Leitor()
    recebidas = []
    for i in range(len(bytes_)):                      # um byte de cada vez (o TCP pode picar assim)
        recebidas += leitor.alimentar(bytes_[i:i + 1])
    assert [m["tipo"] for m in recebidas] == ["chat", "ping", "lobby"]
    assert recebidas[0]["dados"]["texto"] == "olá, ação! ☠" and recebidas[0]["protocolo"] == PROTOCOLO


def test_mensagem_estragada_ou_grande_demais():
    with pytest.raises(MensagemInvalida):
        Leitor().alimentar(b"isto nao e json\n")
    with pytest.raises(MensagemInvalida):
        Leitor().alimentar(b'{"sem": "tipo"}\n')
    with pytest.raises(MensagemInvalida):
        Leitor(limite=100).alimentar(b"x" * 200)      # sem fim de linha e já grande demais
    assert Leitor().alimentar(b'{"tipo": "ping", "dados": 3}\n')[0]["dados"] == {}


def test_texto_de_fora_fica_limpo():
    assert texto_limpo("oi\n\tvocê\x07  aí", 50) == "oi você aí"
    assert texto_limpo("a" * 300, 10) == "a" * 10 and texto_limpo(None, 10) == "" and texto_limpo(5, 10) == ""
    assert cor_valida([300, 0, 0]) == tuple(regras()["multiplayer"]["cores"][0]) and cor_valida((1, 2, 3)) == (1, 2, 3)


# ---------------- código da partida ----------------
def test_codigo_da_partida_vai_e_volta():
    sorteio = random.Random(3)
    padrao = regras()["multiplayer"]["porta"]
    for _ in range(200):
        ip = ".".join(str(sorteio.randint(0, 255)) for _ in range(4))
        porta = sorteio.choice([padrao, sorteio.randint(1, 65535)])
        codigo = codigo_de(ip, porta)
        assert len(codigo.replace("-", "")) == (7 if porta == padrao else 10)
        assert endereco_do_codigo(codigo) == (ip, porta)
        assert endereco_do_codigo(codigo.lower().replace("0", "o").replace("-", " ")) == (ip, porta)   # ditado
    assert endereco_digitado("192.168.0.15") == ("192.168.0.15", padrao)
    assert endereco_digitado(" 10.0.0.2:5000 ") == ("10.0.0.2", 5000)
    assert endereco_digitado("localhost") == ("127.0.0.1", padrao)
    for errado in ("", "batata", "10.0.0.2:99999", "999.1.1.1"):
        with pytest.raises(ValueError):
            endereco_digitado(errado)


def test_lista_de_partidas_procura_tambem_pela_vpn(monkeypatch):
    """Cada rede do PC ganha o seu broadcast (a Radmin VPN é /8); a Tailscale não repassa broadcast."""
    from rede import codigo
    monkeypatch.setattr(codigo, "ips_deste_pc", lambda: ["192.168.0.15", "26.140.22.7", "100.90.1.2"])
    assert codigo.broadcasts_deste_pc() == ["192.168.0.255", "26.255.255.255"]


# ---------------- lobby (dados) ----------------
def test_lobby_diz_o_que_falta_para_comecar():
    lobby = Lobby()
    ana = lobby.entrar("j1", "Ana", COR, host=True)
    assert "Esperando alguém" in lobby.motivo_para_nao_iniciar()
    bia = lobby.entrar("j2", "Ana", COR)
    assert bia.nome == "Ana 2" and bia.cor != ana.cor                 # nome e cor repetidos: ajustados
    ana.herois, bia.herois = [resumo("x")] * 3, [resumo("y")] * 3
    assert "6 heróis" in lobby.motivo_para_nao_iniciar()
    bia.herois = bia.herois[:2]
    assert "Ana, Ana 2" in lobby.motivo_para_nao_iniciar()
    ana.pronto = bia.pronto = True
    assert lobby.motivo_para_nao_iniciar() is None


def test_pacote_de_herois_e_conferido():
    progresso = progresso_com(("guerreiro", "mago"))
    pacote = progresso.pacote_para_partida()
    assert validar_pacote(pacote) is None and len(pacote["herois"]) == 2
    assert validar_pacote(None) and validar_pacote({"herois": []}) and validar_pacote({"herois": [{"x": 1}]})
    assert validar_pacote({**pacote, "provisoes": {"nao_existe": 1}})
    assert validar_pacote({**pacote, "ouro_extra": -5})


# ---------------- partidas de verdade ----------------
def test_entrar_no_lobby_e_ver_os_outros(partidas):
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    for partida in (host, bia, caio):
        assert [j.nome for j in partida.lobby.jogadores] == ["Ana", "Bia", "Caio"]
    assert len({j.cor for j in host.lobby.jogadores}) == 3              # (todos pediram a mesma cor)
    assert bia.eu == "j2" and caio.eu == "j3" and host.lobby.host().id == "j1"
    assert bia.meu().herois == [resumo("Bia")]
    avisos = [t for t, _ in host.pegar_avisos()]
    assert "Bia entrou na partida." in avisos and "Caio entrou na partida." in avisos


def ola_com(porta, **mudancas):
    """Entra "na mão" (socket cru) com um "ola" mexido; devolve a primeira resposta do host."""
    from rede.protocolo import assinatura_dos_dados
    from versao import VERSAO
    dados = {"nome": "X", "cor": [1, 2, 3], "versao": VERSAO, "assinatura": assinatura_dos_dados(), "herois": []}
    dados.update(mudancas)
    with socket.create_connection((LOCAL, porta), timeout=3) as sock:
        sock.sendall(codificar("ola", dados))
        leitor, fim = Leitor(), time.monotonic() + 3
        while time.monotonic() < fim:
            yield_ = leitor.alimentar(sock.recv(65536))
            if yield_:
                return yield_[0]
    return None


def test_versao_ou_dados_diferentes_sao_recusados(partidas):
    host, _ = partidas("Ana")
    respostas = {}
    import threading

    def entrar(chave, **mudancas):
        respostas[chave] = ola_com(host.porta, **mudancas)
    for chave, mudancas in (("versao", {"versao": "0.0.1"}), ("dados", {"assinatura": "outra"})):
        tarefa = threading.Thread(target=entrar, args=(chave,), kwargs=mudancas)
        tarefa.start()
        assert esperar(lambda: not tarefa.is_alive(), host)
    assert respostas["versao"]["tipo"] == "recusado" and "Versões diferentes" in respostas["versao"]["dados"]["motivo"]
    assert respostas["dados"]["tipo"] == "recusado" and "dados do jogo" in respostas["dados"]["dados"]["motivo"]
    assert [j.nome for j in host.lobby.jogadores] == ["Ana"]


def test_partida_cheia_recusa_com_motivo(partidas, monkeypatch):
    monkeypatch.setitem(regras()["multiplayer"], "max_jogadores", 2)
    host, _ = partidas("Ana", "Bia")
    caio = PartidaCliente(Progresso(), "Caio", COR, LOCAL, host.porta)
    assert esperar(lambda: caio.encerrada, host, caio)
    assert "cheia" in caio.motivo_do_fim and len(host.lobby.jogadores) == 2


def test_ninguem_na_porta_da_erro_claro():
    with socket.socket() as livre:                     # uma porta que ninguém escuta
        livre.bind((LOCAL, 0))
        porta = livre.getsockname()[1]
    cliente = PartidaCliente(Progresso(), "Bia", COR, LOCAL, porta)
    assert esperar(lambda: cliente.encerrada, cliente)
    assert str(porta) in cliente.motivo_do_fim


def test_chat_e_emote_chegam_a_todos(partidas):
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    bia.falar_no_chat("bora, galera! ação\n")
    host.mandar_emote(3)
    assert esperar(lambda: all(len([m for m in p.lobby.chat if not m.sistema]) == 2 for p in (host, bia, caio)),
                   host, bia, caio)
    no_host = [(m.nome, m.texto, m.emote) for m in host.lobby.chat if not m.sistema]
    assert set(no_host) == {("Bia", "bora, galera! ação", False), ("Ana", regras()["multiplayer"]["emotes"][3], True)}
    for partida in (host, bia, caio):                          # todos na ordem em que o host recebeu
        assert [(m.nome, m.texto, m.emote) for m in partida.lobby.chat if not m.sistema] == no_host
        assert partida.balao_de("j1") == regras()["multiplayer"]["emotes"][3]


def test_host_tira_alguem(partidas):
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    assert host.expulsar(bia.eu) and not host.expulsar(host.eu)
    assert esperar(lambda: bia.encerrada and len(caio.lobby.jogadores) == 2, host, bia, caio)
    assert "tirou você" in bia.motivo_do_fim and [j.nome for j in caio.lobby.jogadores] == ["Ana", "Caio"]


def test_iniciar_a_run_com_o_mesmo_estado_em_todos(partidas):
    """O critério de aceite: entram, conversam e iniciam a run; todos com a mesma impressão digital."""
    host, (bia, caio) = partidas("Ana", "Bia", "Caio", classes=(("guerreiro", "sacerdote"), ("mago",), ("ladino",)))
    bia.progresso.provisoes = {"pocao_de_vida": 2}
    assert "Esperando ficar pronto" in host.iniciar()
    todos_prontos(host, [bia, caio])
    assert host.iniciar("GRUPO") is None
    assert esperar(lambda: all(p.run is not None for p in (bia, caio)) and None not in host.sincronia.values(),
                   host, bia, caio)
    assert host.sincronia == {"j1": True, "j2": True, "j3": True}
    assert esperar(lambda: bia.sincronia == host.sincronia, host, bia, caio)
    impressao = host.sessao.estado.impressao_digital()
    assert all(p.sessao.estado.impressao_digital() == impressao for p in (bia, caio))
    run = bia.run
    assert run.semente == "GRUPO" and [j.id for j in run.grupo.jogadores] == ["j1", "j2", "j3"]
    assert [h.jogador.id for h in run.grupo.herois] == ["j1", "j1", "j2", "j3"]
    assert run.grupo.jogador("j2").mochila.quantidade("pocao_de_vida") == 2    # as provisões da Bia, na mochila dela
    assert all(j.ouro == regras()["economia"]["ouro_inicial"] for j in run.grupo.jogadores)
    assert getattr(run, "em_rede", False) and bia.run_nova is run and host.run_nova is host.run


def test_comandos_pela_rede_deixam_todos_iguais(partidas):
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    todos_prontos(host, [bia, caio])
    host.iniciar("CMDS")
    assert esperar(lambda: bia.run is not None and caio.run is not None, host, bia, caio)
    for partida in (host, bia, caio):                      # o mesmo osso na mochila da Bia, em todo lugar
        partida.run.grupo.jogador("j2").mochila.adicionar("osso", 3)
    heroi_da_bia = next(i for i, h in enumerate(bia.run.grupo.herois) if h.jogador.id == "j2")
    assert bia.sessao.enviar(C.MoverItem(chave="osso", de=heroi_da_bia, para=BAU, quantidade=2))
    assert esperar(lambda: caio.sessao.seq == 1 and bia.sessao.seq == 1, host, bia, caio)
    assert not caio.sessao.enviar(C.MoverItem(chave="osso", de=heroi_da_bia, para=BAU))   # mochila da Bia: recusa aqui
    caio.mandar("comando", {"comando": C.MoverItem(jogador="j2", chave="osso", de=heroi_da_bia, para=BAU).para_dict()})
    assert esperar(lambda: any(t == "Não deu" for t, _ in caio.pegar_avisos()), host, bia, caio)   # (o host ignora o "j2")
    meu = next(i for i, h in enumerate(host.run.grupo.herois) if h.jogador.id == "j1")
    assert host.sessao.enviar(C.MoverItem(chave="osso", de=BAU, para=meu))
    assert esperar(lambda: bia.sessao.seq == 2 and caio.sessao.seq == 2, host, bia, caio)
    impressao = host.sessao.estado.impressao_digital()
    assert all(p.sessao.estado.impressao_digital() == impressao for p in (bia, caio))
    assert host.run.grupo.bau.quantidade("osso") == 1 and host.run.grupo.jogador("j1").mochila.tem("osso")
    assert bia.sessao.divergiu is None and caio.sessao.divergiu is None
    assert host.sessao.processador.registro == bia.sessao.processador.registro == caio.sessao.processador.registro


def test_comando_que_nao_existe_nao_derruba_o_host(partidas):
    host, (bia,) = partidas("Ana", "Bia")
    todos_prontos(host, [bia])
    host.iniciar()
    assert esperar(lambda: bia.run is not None, host, bia)
    for lixo in ({"tipo": "nao_existe"}, {"tipo": "mover_item", "chave": 5, "de": "x", "para": [1]}, None, "texto"):
        bia.mandar("comando", {"comando": lixo})
    assert esperar(lambda: len([a for a in bia.pegar_avisos() if a[0] == "Não deu"]) >= 1, host, bia)
    assert not host.encerrada and host.sessao.seq == 0


def test_saidas_e_quedas(partidas):
    host, (bia, caio) = partidas("Ana", "Bia", "Caio")
    bia.fechar()
    assert esperar(lambda: len(host.lobby.jogadores) == 2, host, caio)
    caio.conexao.fechar()                                     # caiu (sem tchau)
    assert esperar(lambda: len(host.lobby.jogadores) == 1, host)
    avisos = [t for t, _ in host.pegar_avisos()]
    assert "Bia saiu da partida." in avisos and "Caio saiu da partida." in avisos


def test_host_fecha_e_todos_sabem(partidas):
    host, (bia,) = partidas("Ana", "Bia")
    host.fechar()
    assert esperar(lambda: bia.encerrada, bia)
    assert bia.motivo_do_fim == "O host fechou a partida."


def test_silencio_demais_derruba(partidas, monkeypatch):
    host, (bia,) = partidas("Ana", "Bia")
    monkeypatch.setitem(regras()["multiplayer"], "intervalo_do_ping", 999)     # ninguém pinga
    monkeypatch.setitem(regras()["multiplayer"], "tempo_sem_resposta", 0.3)
    time.sleep(0.4)
    assert esperar(lambda: bia.encerrada and len(host.lobby.jogadores) == 1, host, bia)
    assert "parou de responder" in bia.motivo_do_fim or "caiu" in bia.motivo_do_fim    # (quem percebe antes)


HOST_EM_OUTRO_PROCESSO = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
from roguelike.progresso import Progresso
from rede.partida import PartidaHost
progresso = Progresso()
host = PartidaHost(progresso, "Ana", (214, 72, 72), porta=0, endereco="127.0.0.1", porta_descoberta=False)
print(host.porta, flush=True)
fim = time.monotonic() + 60
while time.monotonic() < fim and not host.encerrada:
    host.atualizar()
    if host.run is None and len(host.lobby.jogadores) == 2 and host.lobby.jogadores[1].pronto:
        host.marcar_pronto(True, progresso.pacote_para_partida())
        host.iniciar("DOIS-PROCESSOS")
    if host.sessao is not None and host.sessao.seq >= 1:
        print("FIM", host.sessao.estado.impressao_digital(), flush=True)
        time.sleep(0.3)
        host.fechar()
        break
    time.sleep(0.01)
"""


def test_duas_copias_do_jogo_em_processos_diferentes(tmp_path):
    """Como duas janelas no mesmo PC: o host noutro processo (outro PYTHONHASHSEED); entram, iniciam, um comando
    vai e volta e os dois terminam com a mesma impressão digital."""
    import os
    import subprocess
    import sys
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ambiente = dict(os.environ, PYTHONHASHSEED="4242", ECOS_DA_CRIPTA_DADOS=str(tmp_path / "host"))
    processo = subprocess.Popen([sys.executable, "-c", HOST_EM_OUTRO_PROCESSO, os.path.join(raiz, "src")], cwd=raiz,
                                env=ambiente, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        porta = int(processo.stdout.readline())
        progresso = progresso_com(("mago",))
        progresso.provisoes = {"pocao_de_vida": 2}                # (vão para a mochila da Bia nos dois lados)
        bia = PartidaCliente(progresso, "Bia", COR, LOCAL, porta, [resumo("Bia", "mago")])
        assert esperar(lambda: bia.no_lobby(), bia, tempo=15)
        bia.marcar_pronto(True, progresso.pacote_para_partida())
        assert esperar(lambda: bia.run is not None and bia.sincronia.get("j2") is True, bia, tempo=15)
        heroi = next(i for i, h in enumerate(bia.run.grupo.herois) if h.jogador.id == "j2")
        assert bia.sessao.enviar(C.MoverItem(chave="pocao_de_vida", de=heroi, para=BAU))
        assert esperar(lambda: bia.sessao.seq >= 1, bia, tempo=15)
        linha = processo.stdout.readline()                      # o host imprime a impressão dele depois do comando
        assert linha.startswith("FIM"), processo.stderr.read()
        assert linha.split()[1] == bia.sessao.estado.impressao_digital()
        assert bia.run.grupo.bau.quantidade("pocao_de_vida") == 1 and bia.sessao.divergiu is None
        assert esperar(lambda: bia.encerrada, bia, tempo=10)          # o host fecha: a Bia fica sabendo
        assert bia.motivo_do_fim.startswith("O host fechou a partida.")
        assert "ficou salva" in bia.motivo_do_fim                  # (MP8: no meio da run, ela fica salva com o host)
    finally:
        try:
            processo.wait(timeout=20)
        except subprocess.TimeoutExpired:
            processo.kill()


def test_achar_a_partida_na_rede():
    info = {"nome": "Ana", "porta": 47999, "jogadores": 1, "maximo": 4, "aberta": True, "id_da_partida": "abc"}
    anunciante = Anunciante(0, lambda: info, LOCAL)
    procurador = Procurador(anunciante.porta, destinos=[LOCAL], endereco_local=LOCAL)
    try:
        assert anunciante.aberto and procurador.aberto
        fim = time.monotonic() + 5
        while time.monotonic() < fim and not procurador.partidas():
            time.sleep(0.05)
        achadas = procurador.partidas()
        assert len(achadas) == 1 and achadas[0]["nome"] == "Ana" and achadas[0]["porta"] == 47999
        assert achadas[0]["mesma_versao"] and achadas[0]["ip"] == LOCAL
    finally:
        procurador.fechar()
        anunciante.fechar()


def test_porta_ocupada_da_erro_ao_criar(partidas):
    host, _ = partidas("Ana")
    with pytest.raises(OSError):
        PartidaHost(Progresso(), "Bia", COR, porta=host.porta, endereco=LOCAL, porta_descoberta=False)


def test_run_em_grupo_nao_vai_para_o_save_solo(tmp_path):
    from roguelike.run import Run
    from telas import comum
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    try:
        run = Progresso().criar_run(Progresso().expedicao_atual().criar_herois(Progresso()), "SOLO")
        run.em_rede = True
        comum.salvar_run(run)
        assert not comum.existe_run_salva()
        del run.em_rede
        comum.salvar_run(run)
        assert comum.existe_run_salva() and Run.carregar(comum.ArquivoDaRun.onde()).semente == "SOLO"
    finally:
        comum.ArquivoDaRun.caminho = None


def test_mensagem_de_lobby_aguenta_lixo():
    lobby = Lobby()
    lobby.atualizar_de({"jogadores": [{"id": 1, "nome": "x\n" * 50, "cor": "azul", "herois": "nada"}, "lixo"]})
    jogador = lobby.jogadores[0]
    assert jogador.id == "1" and "\n" not in jogador.nome and jogador.herois == [] and len(jogador.cor) == 3
    lobby.atualizar_de("não é dict")
    assert lobby.jogadores == []
    assert json.loads(json.dumps(Lobby().para_dict())) == {"jogadores": []}
