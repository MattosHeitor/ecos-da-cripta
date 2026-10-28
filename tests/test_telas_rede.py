"""MP5 nas telas: o campo de texto com acentos, "Jogar em grupo" no título, criar/entrar, o lobby e o começo
da run pela interface (o outro lado da partida roda só a lógica, no mesmo processo, em 127.0.0.1)."""

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelike.progresso import Progresso
from rede.partida import PartidaCliente, PartidaHost
from ui.widgets import CampoDeTexto

LOCAL = "127.0.0.1"
COR = (86, 146, 226)


class ProcuradorDeMentira:
    """No lugar do Procurador (UDP na rede inteira): nos testes nada escuta fora do 127.0.0.1."""
    aberto = True

    def __init__(self, *args, **kwargs):
        pass

    def partidas(self):
        return [{"ip": LOCAL, "porta": 1, "nome": "Zé", "jogadores": 1, "maximo": 4, "versao": "?", "aberta": True,
                 "mesma_versao": True}]

    def fechar(self):
        self.aberto = False


@pytest.fixture
def app(tmp_path, monkeypatch):
    from telas import comum, multijogador
    from telas.base import App
    monkeypatch.setattr(multijogador, "Procurador", ProcuradorDeMentira)
    monkeypatch.setattr(multijogador, "PartidaHost",            # o host da tela também só em 127.0.0.1, porta livre
                        lambda progresso, nome, cor: PartidaHost(progresso, nome, cor, porta=0, endereco=LOCAL,
                                                                 porta_descoberta=False))
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    aplicativo = App(janela=False)
    aplicativo.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    aplicativo.opcoes.avisou_firewall = True          # (o aviso da 1ª vez tem o seu próprio teste)
    yield aplicativo
    if aplicativo.partida is not None and not aplicativo.partida.encerrada:
        aplicativo.partida.fechar()
    comum.ArquivoDaRun.caminho = None


def quadros(app, n=2, eventos=()):
    for i in range(n):
        app.passo(1 / 30, list(eventos) if i == 0 else [])


def rodar_ate(app, condicao, *outras, tempo=6.0):
    fim = time.monotonic() + tempo
    while time.monotonic() < fim:
        app.passo(1 / 30, [])
        for partida in outras:
            partida.atualizar()
        if condicao():
            return True
        time.sleep(0.005)
    return False


def tecla(chave, letra=""):
    return pygame.event.Event(pygame.KEYDOWN, key=chave, unicode=letra, mod=0)


def letras(texto):
    return pygame.event.Event(pygame.TEXTINPUT, text=texto)


# ---------------- campo de texto ----------------
def test_campo_de_texto_com_acentos_sem_dobrar():
    campo = CampoDeTexto((0, 0, 200, 40), maximo=10)
    campo.ativo = True
    for evento in (tecla(pygame.K_o, "o"), letras("o"), tecla(pygame.K_l, "l"), letras("l"),
                   tecla(0, ""), tecla(pygame.K_a, "á"), letras("á")):      # (´ + a no teclado brasileiro)
        campo.evento(evento)
    assert campo.conteudo == "olá"
    campo.evento(letras("ção"))                       # só TEXTINPUT (IME, colar)
    campo.evento(tecla(pygame.K_x, "x"))              # só KEYDOWN (como os testes antigos mandam)
    assert campo.conteudo == "oláçãox"
    campo.evento(letras("12345"))
    assert campo.conteudo == "oláçãox123"              # (máximo de 10)
    campo.evento(tecla(pygame.K_BACKSPACE))
    assert campo.conteudo == "oláçãox12"


def test_campo_do_chat_envia_com_enter_e_continua_aberto():
    campo = CampoDeTexto((0, 0, 200, 40), maximo=50, enviar_com_enter=True)
    campo.ativo = True
    campo.evento(letras("bora!"))
    campo.evento(tecla(pygame.K_RETURN))
    assert campo.pegar_enviado() == "bora!" and campo.conteudo == "" and campo.ativo
    assert campo.pegar_enviado() is None


# ---------------- título e "Jogar em grupo" ----------------
def test_titulo_leva_a_jogar_em_grupo(app):
    from telas import fluxo
    fluxo.ir_para_titulo(app)
    quadros(app)
    nomes = [nome for nome, _, _ in app.atual.opcoes()]
    assert "Jogar em grupo" in nomes
    app.atual.opcoes()[nomes.index("Jogar em grupo")][2]()
    quadros(app)
    assert type(app.atual).__name__ == "TelaMultijogador"


def test_sem_nome_nao_cria_e_codigo_errado_explica(app):
    from telas import fluxo
    fluxo.abrir_multijogador(app)
    tela = app.atual
    quadros(app)
    tela.campo_nome.conteudo = ""
    tela.criar()
    assert app.partida is None and "nome" in tela.mensagem[0]
    tela.campo_nome.conteudo = "Bia"
    tela.campo_endereco.conteudo = "BATATA"
    tela.entrar()
    assert app.partida is None and "código" in tela.mensagem[0]
    assert app.opcoes.nome_do_jogador == "Bia"                     # o nome fica guardado nas opções


def test_criar_partida_abre_o_lobby_e_o_outro_entra(app):
    from telas import fluxo
    fluxo.abrir_multijogador(app)
    tela = app.atual
    tela.campo_nome.conteudo = "Ana"
    tela.criar()
    quadros(app)
    assert type(app.atual).__name__ == "TelaLobby" and app.partida.eh_host
    host = app.partida
    bia = PartidaCliente(Progresso(), "Bia", COR, LOCAL, host.porta,
                         [{"nome": "Kael", "classe": "mago", "raca": "humano", "sprite": "mago"}])
    try:
        assert rodar_ate(app, lambda: len(host.lobby.jogadores) == 2 and bia.no_lobby(), bia)
        lobby = app.atual
        quadros(app)
        nomes = [v.jogador.nome for v in lobby.vagas()]
        assert "Bia" in nomes and "Ana" in nomes                   # os heróis de todos em volta da fogueira
        bia.falar_no_chat("oi!")
        assert rodar_ate(app, lambda: any(m.texto == "oi!" for m in host.lobby.chat), bia)
        lobby.campo_chat.ativo = True                              # o host responde pelo campo do chat
        quadros(app, 1, [letras("olá"), tecla(pygame.K_RETURN)])
        assert rodar_ate(app, lambda: any(m.texto == "olá" for m in bia.lobby.chat), bia)
    finally:
        bia.fechar()


def test_paineis_do_lobby_recolhem_e_abrem(app):
    """Jogadores e Conversa minimizam numa aba (guardado nas Opções); a aba conta as falas novas; Enter abre."""
    from telas import fluxo
    from ui.opcoes import Opcoes
    fluxo.abrir_multijogador(app)
    app.atual.campo_nome.conteudo = "Ana"
    app.atual.criar()
    quadros(app)
    host = app.partida
    bia = PartidaCliente(Progresso(), "Bia", COR, LOCAL, host.porta)
    try:
        assert rodar_ate(app, lambda: bia.no_lobby() and len(host.lobby.jogadores) == 2, bia)
        lobby = app.atual
        quadros(app)
        rotulos = [b.texto for b in lobby.botoes]
        assert rotulos.count("▲") == 2                             # um "minimizar" em cada painel
        lobby.recolher("jogadores")
        lobby.recolher("conversa")
        quadros(app)
        assert Opcoes.carregar().lobby_recolhido == {"jogadores": True, "conversa": True}
        assert not any(b.texto == "Olá!" for b in lobby.botoes)   # (os emotes somem com a conversa)
        bia.falar_no_chat("bora?")
        assert rodar_ate(app, lambda: any(m.texto == "bora?" for m in host.lobby.chat), bia)
        quadros(app)
        aba = next(b for b in lobby.botoes if b.texto.startswith("Conversa"))
        assert aba.subtexto == "1 mensagem nova" and lobby.chegou_em is not None
        fluxo.ir_para_acampamento(app)                             # voltar de um NPC: continua recolhido
        quadros(app)
        lobby = app.atual
        assert lobby.recolhido("jogadores") and len(lobby.novas_na_conversa()) == 1
        quadros(app, 1, [tecla(pygame.K_RETURN)])                  # Enter abre a conversa já no campo
        assert not lobby.recolhido("conversa") and lobby.campo_chat.ativo
        quadros(app)
        assert lobby.novas_na_conversa() == [] and lobby.recolhido("jogadores")
        next(b for b in lobby.botoes if b.texto.startswith("Jogadores")).acao()
        assert not lobby.recolhido("jogadores")
    finally:
        bia.fechar()


def test_host_em_duas_redes_troca_o_ip_do_codigo(app, monkeypatch):
    from rede.codigo import nome_da_rede
    from telas import fluxo, lobby as modulo_lobby
    monkeypatch.setattr(modulo_lobby, "ips_deste_pc", lambda: ["192.168.0.15", "26.140.22.7"])   # casa + Radmin
    fluxo.abrir_multijogador(app)
    app.atual.campo_nome.conteudo = "Ana"
    app.atual.criar()
    quadros(app)
    lobby = app.atual
    assert lobby.endereco == ("192.168.0.15", app.partida.porta)   # a rede local primeiro
    lobby.trocar_ip()
    quadros(app)
    assert lobby.endereco == ("26.140.22.7", app.partida.porta)
    assert any(b.texto.startswith("IP 26.140.22.7") for b in lobby.botoes)
    fluxo.ir_para_acampamento(app)                                 # a escolha vale enquanto a partida durar
    assert app.atual.endereco[0] == "26.140.22.7"
    assert [nome_da_rede(ip) for ip in ("26.1.2.3", "25.1.2.3", "100.90.1.2", "192.168.0.15", "10.147.17.5")] == [
        "Radmin VPN", "Hamachi", "Tailscale", "rede local", "rede local"]


def test_lobby_ate_a_run_pela_tela(app):
    """O host (pela tela) e a Bia (só a lógica): prontos, Iniciar, a fase e o mapa em grupo com o mesmo estado."""
    from telas import fluxo
    fluxo.abrir_multijogador(app)
    app.atual.campo_nome.conteudo = "Ana"
    app.atual.criar()
    quadros(app)
    host = app.partida
    progresso_da_bia = Progresso()
    progresso_da_bia.expedicao_atual().vagas = progresso_da_bia.expedicao_atual().vagas[:1]
    app.progresso.expedicao_atual().vagas = app.progresso.expedicao_atual().vagas[:2]
    bia = PartidaCliente(progresso_da_bia, "Bia", COR, LOCAL, host.porta)
    try:
        assert rodar_ate(app, lambda: bia.no_lobby(), bia)
        lobby = app.atual
        lobby.alternar_pronto()
        bia.marcar_pronto(True, progresso_da_bia.pacote_para_partida())
        assert rodar_ate(app, lambda: host.motivo_para_nao_iniciar() is None, bia)
        lobby.iniciar()
        assert rodar_ate(app, lambda: type(app.atual).__name__ == "TelaTituloDaArea", bia)
        app.atual.seguir()
        quadros(app)
        mapa = app.atual
        assert type(mapa).__name__ == "TelaMapa" and mapa.em_grupo()
        assert rodar_ate(app, lambda: bia.run is not None and None not in host.sincronia.values(), bia)
        assert host.sincronia == {"j1": True, "j2": True}
        assert app.sessao_da(host.run) is host.sessao
        mapa.escolher(0)                                           # (escolher em grupo é da MP6)
        assert host.run.estado == "escolha"
        quadros(app)
        from telas import comum
        assert not comum.existe_run_salva()                       # a run do grupo não vira a run salva do solo
    finally:
        bia.fechar()


def test_quem_entra_pela_tela_chega_ao_lobby_e_a_run(app):
    """A Bia pela tela (entrar com o IP) e o host só na lógica."""
    from telas import fluxo
    progresso_do_host = Progresso()
    progresso_do_host.expedicao_atual().vagas = progresso_do_host.expedicao_atual().vagas[:1]
    host = PartidaHost(progresso_do_host, "Ana", (214, 72, 72), porta=0, endereco=LOCAL, porta_descoberta=False)
    try:
        app.progresso.expedicao_atual().vagas = app.progresso.expedicao_atual().vagas[:1]
        fluxo.abrir_multijogador(app)
        tela = app.atual
        tela.campo_nome.conteudo = "Bia"
        tela.campo_endereco.conteudo = f"{LOCAL}:{host.porta}"
        tela.entrar()
        assert rodar_ate(app, lambda: type(app.atual).__name__ == "TelaLobby", host)
        bia = app.partida
        app.atual.alternar_pronto()
        host.marcar_pronto(True, progresso_do_host.pacote_para_partida())
        assert rodar_ate(app, lambda: host.motivo_para_nao_iniciar() is None, host)
        assert host.iniciar() is None
        assert rodar_ate(app, lambda: type(app.atual).__name__ == "TelaTituloDaArea", host)
        assert bia.sessao.estado.impressao_digital() == host.sessao.estado.impressao_digital()
        app.atual.seguir()
        quadros(app)
        from telas.inventario import TelaInventario
        fluxo.abrir_inventario(app, bia.run)                       # a Bia mexe na mochila: passa pelo host
        tela = app.atual
        assert isinstance(tela, TelaInventario)
        meu = tela.heroi
        meu.inventario.adicionar("osso")
        host.run.grupo.jogador(bia.eu).mochila.adicionar("osso")
        tela.mover("osso", meu, "bau")
        assert rodar_ate(app, lambda: host.run.grupo.bau.tem("osso") and bia.run.grupo.bau.tem("osso"), host)
        host.fechar()                                              # o host fecha: a Bia volta com o motivo
        assert rodar_ate(app, lambda: type(app.atual).__name__ == "TelaMultijogador")
        assert "fechou" in app.atual.mensagem[0] and app.partida is None
    finally:
        if not host.encerrada:
            host.fechar()
