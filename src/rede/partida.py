"""Partidas em grupo: o lobby e o começo da run, do lado do host e do lado de quem entra.

    partida = PartidaHost(progresso, "Ana", cor)                  # abre a porta (OSError: porta ocupada)
    partida = PartidaCliente(progresso, "Bia", cor, ip, porta)     # tenta entrar (em outra thread)
    partida.atualizar()                                            # a cada quadro: trata o que chegou
    partida.estado                                                 # "conectando", "lobby", "jogando" ou "encerrada"

As telas só chamam os métodos daqui (definir_meus_herois, marcar_pronto, falar_no_chat, mandar_emote, expulsar,
iniciar, fechar) e leem lobby, avisos (o que notificar), run_nova (a run que acabou de começar) e motivo_do_fim.

Entrada:  cliente -> "ola" {nome, cor, versao, assinatura, herois}; host -> "bem_vindo" {id, lobby, chat} ou
          "recusado" {motivo} (versão ou dados diferentes, partida cheia ou já começada).
Lobby:    "herois" e "pronto" (com o pacote dos heróis prontos) do cliente; "lobby" do host a cada mudança;
          "chat"/"emote"; o host pode "expulsar". Ninguém fala durante mais de tempo_sem_resposta: caiu.
Começo:   o host cria a run (Progresso.criar_run_em_grupo), recarrega ela do próprio JSON (assim host e clientes
          partem do MESMO dado) e manda "iniciar" {run}; cada cliente carrega e devolve "carregou" {impressao}; o
          host compara com a dele e manda "sincronia" a todos.
Run:      os comandos vão e voltam pelas sessões (rede/sessoes.py): "comando" -> "aplicar" (ou "recusa").
Votos:    (MP6) o caminho, as opções de evento e o "seguir" são votados: "votar" {chave, opcao} do cliente; o host
          abre a votação quando a tela DELE chega lá (abrir_votacao), manda "votacao" {chave, votos, restante} a
          cada mudança e, quando todos votaram (ou o tempo acabou), decide e executa o comando da opção vencedora.
          Quem caiu da partida não conta ("presenca" {desconectados, latencias}).
Fim:      depois da run, o host volta ao lobby ("voltou_ao_lobby"): dá para jogar outra com o mesmo grupo.

Robustez (MP8):
Volta:    no "bem_vindo" cada um ganha uma chave de volta (guardada nas Opções). Quem cai no meio da run tenta
          voltar sozinho (a cada intervalo_de_reconexao, por até tempo_para_voltar; enquanto isso a IA joga por
          ele); quem fechou o jogo entra de novo pelo código. O "ola" leva a chave; o host responde "retomar"
          {retomada, impressao, votacoes...}: a run do último ponto seguro + os comandos desde então
          (rede/retomada.py), e o cliente refaz tudo até o estado de agora (até no meio de uma luta).
Ressinc.: o cliente que dessincronizou pede "ressincronizar" e recebe o mesmo "retomar".
Ping:     "ping" {t} -> "pong" {t} nos dois sentidos: a latência de cada um (o host repassa na "presenca").
Salvar:   o host regrava a partida (partida_em_grupo.json) a cada comando; fechou ou caiu, retoma depois
          (PartidaHost(..., salva=dados)): todos começam fora e voltam pelo código, com a chave de cada um.
"""

import copy
import json
import queue
import time
import uuid

from rede.conexao import Conexao, Servidor, conectar
from rede.descoberta import Anunciante
from rede.lobby import JogadorNoLobby, Lobby, MensagemDeChat, cor_valida, resumos_validos
from rede.protocolo import PROTOCOLO, assinatura_dos_dados, configuracao, texto_limpo
from rede.retomada import Retomada, apagar_partida_salva, salvar_partida
from rede.votacao import Votacao
from versao import VERSAO

CONECTANDO, LOBBY, JOGANDO, ENCERRADA = "conectando", "lobby", "jogando", "encerrada"
ID_DO_HOST = "j1"
DURACAO_DO_BALAO = 3.0                  # segundos que um emote fica no balão sobre os heróis
ESPERA_PARA_FECHAR = 0.5                # depois de "recusado"/"expulso", o tempo de a mensagem chegar
PEDIR_O_ESTADO_DE_NOVO = 5.0            # dessincronizou: pede o estado ao host de tantos em tantos segundos


class Partida:
    """O que o host e quem entra têm em comum: o lobby, os avisos para a tela, a run e a sessão dela."""

    eh_host = False

    def __init__(self, progresso, nome, cor):
        self.progresso = progresso
        self.fila = queue.Queue()
        self.lobby = Lobby()
        self.eu = None                      # o meu id na partida ("j1" é o host)
        self.estado = CONECTANDO
        self.motivo_do_fim = None
        self.avisos = []                    # (título, texto) para a tela notificar
        self.run = None
        self.sessao = None
        self.run_nova = None                # a run que acabou de começar (o fluxo leva à fase e limpa)
        self.sincronia = {}                 # id -> True (mesmo estado do host), False (diferente) ou None (esperando)
        self.baloes = {}                    # id -> (texto, quando): o último emote de cada um
        self.desconectados = set()          # ids de quem caiu durante a run (a IA joga por eles; MP8: voltar)
        self.votos = {}                     # chave -> {"votos": {id: opção}, "restante": s, "quando": t, "decidida": opção}
        self.conversa_lida = 0              # quantas mensagens do chat este jogador já viu (a tela do lobby anota)
        self.ip_mostrado = None             # host: o IP que o lobby mostra (rede local ou o da VPN)
        self.latencias = {}                 # id -> ms (ida e volta até o host)
        self.retomou = False                # a run veio de uma retomada (o fluxo abre a tela do ponto em que está)
        self.ultimo_ping = time.monotonic()
        self.nome_pedido = nome
        self.cor_pedida = cor_valida(cor)

    # ---------------- para as telas ----------------
    @property
    def encerrada(self):
        return self.estado == ENCERRADA

    def no_lobby(self):
        return self.estado == LOBBY

    def meu(self):
        return self.lobby.jogador(self.eu)

    def pegar_avisos(self):
        avisos, self.avisos = self.avisos, []
        return avisos

    def pegar_run_nova(self):
        """(run, retomada?) da run que acabou de começar (ou de ser retomada), ou (None, False)."""
        run, self.run_nova = self.run_nova, None
        retomou, self.retomou = self.retomou and run is not None, False
        return run, retomou

    def latencia_de(self, identificador):
        """Ida e volta (ms) entre esse jogador e o host; None se ainda não mediu (o host: 0)."""
        return self.latencias.get(identificador)

    def balao_de(self, identificador):
        """O emote que o jogador mandou há pouco (para o balão sobre os heróis) ou None."""
        balao = self.baloes.get(identificador)
        if balao and time.monotonic() - balao[1] < DURACAO_DO_BALAO:
            return balao[0]
        return None

    def conectados(self):
        """Os ids de quem está jogando agora (sem quem caiu): são os que votam."""
        return [j.id for j in self.lobby.jogadores if j.id not in self.desconectados]

    def jogando(self):
        return self.estado == JOGANDO

    # ---------------- votações (as telas mostram; quem decide é o host) ----------------
    def votos_de(self, chave):
        """{id do jogador: opção} da votação 'chave' (vazio se ninguém votou ainda)."""
        return dict(self.votos.get(chave, {}).get("votos", {}))

    def restante_de(self, chave):
        """Segundos até o host decidir (None: a votação ainda não abriu no host)."""
        info = self.votos.get(chave)
        if not info or info.get("restante") is None:
            return None
        return max(0.0, info["restante"] - (time.monotonic() - info["quando"]))

    def decidida(self, chave):
        """A opção que venceu (None: ainda não decidiu)."""
        return self.votos.get(chave, {}).get("decidida")

    def faltam_votar(self, chave):
        votos = self.votos_de(chave)
        return [j for j in self.lobby.jogadores if j.id not in votos and j.id not in self.desconectados]

    def guardar_votacao(self, dados):
        chave = str(dados.get("chave", ""))
        info = self.votos.setdefault(chave, {"votos": {}})
        votos = dados.get("votos")
        if isinstance(votos, dict):
            info["votos"] = {str(i): o for i, o in votos.items() if isinstance(o, int)}
        if isinstance(dados.get("restante"), (int, float)):
            info["restante"], info["quando"] = float(dados["restante"]), time.monotonic()
        if isinstance(dados.get("decidida"), int):
            info["decidida"] = dados["decidida"]
        del_antigas(self.votos)

    # ---------------- o laço ----------------
    def atualizar(self):
        """Trata o que chegou pela rede (a cada quadro, na thread do jogo)."""
        while not self.encerrada:
            try:
                etiqueta, tipo, dados = self.fila.get_nowait()
            except queue.Empty:
                break
            self.tratar(etiqueta, tipo, dados)
        if not self.encerrada and self.sessao is not None and self.estado == JOGANDO:
            self.sessao.processar()                       # os comandos que esperavam a tela daqui
        if not self.encerrada:
            self.cuidar_das_conexoes()

    def tratar(self, etiqueta, tipo, dados):
        raise NotImplementedError

    def cuidar_das_conexoes(self):
        """Ping de tempos em tempos e quem ficou mudo demais."""

    def hora_do_ping(self):
        if time.monotonic() - self.ultimo_ping >= configuracao()["intervalo_do_ping"]:
            self.ultimo_ping = time.monotonic()
            return True
        return False

    def encerrar(self, motivo):
        if self.encerrada:
            return
        self.estado = ENCERRADA
        self.motivo_do_fim = motivo
        self.fechar_rede()

    def fechar_rede(self):
        """Fecha sockets e threads."""

    # ---------------- a run ----------------
    def comecar_run(self, run):
        """A run (nova ou retomada) passa a ser a da partida. Devolve a sessão dela."""
        from roguelike.estado import EstadoDoJogo
        from rede.sessoes import SessaoCliente, SessaoHost
        run.em_rede = True                  # (não vai para o run.json do jogo solo)
        self.run = run
        estado = EstadoDoJogo(run)
        if self.eh_host:
            self.sessao = SessaoHost(estado, self.eu, self.transmitir,
                                     lambda jogador, mensagem: self.enviar_para(jogador, "recusa", {"mensagem": mensagem}))
            self.sessao.ao_aceitar = self.comando_aceito
        else:
            self.sessao = SessaoCliente(estado, self.eu, self.mandar)
            self.sessao.conectado = self.conectado
        self.estado = JOGANDO
        self.run_nova = run
        self.votos = {}
        self.desconectados = set()
        return self.sessao

    def comando_aceito(self, dados):
        """(host) Cada comando aceito na run."""

    def conectado(self):
        return True

    def largar_run(self):
        """A run acabou e o grupo volta ao lobby (cada um desmarca o "Pronto")."""
        self.run = self.sessao = self.run_nova = None
        self.votos = {}
        self.desconectados = set()
        self.estado = LOBBY
        for jogador in self.lobby.jogadores:
            jogador.pronto, jogador.pacote = False, None


def del_antigas(votos, guardar=12):
    """Guarda só as últimas votações (as chaves mudam a cada tela)."""
    for chave in list(votos)[:-guardar]:
        del votos[chave]


# ============================================================
# HOST
# ============================================================

class PartidaHost(Partida):
    """Quem cria a partida: abre a porta, guarda o lobby de verdade, cria a run e confere os comandos.

    porta None = a de regras.json; 0 = qualquer livre (testes). endereco "" = a rede local; "127.0.0.1" = só
    este computador (testes). porta_descoberta False = sem anúncio na rede. salva = a partida salva (retomar):
    a run volta no ponto em que estava e os outros entram de novo pelo código."""

    eh_host = True

    def __init__(self, progresso, nome, cor, porta=None, endereco="", porta_descoberta=None, salva=None):
        super().__init__(progresso, nome, cor)
        regras_da_rede = configuracao()
        self.servidor = Servidor(self.fila, regras_da_rede["porta"] if porta is None else porta, endereco)
        self.porta = self.servidor.porta
        self.id_da_partida = uuid.uuid4().hex[:8]         # (só para a lista de partidas não repetir esta)
        self.conexoes = {}                  # número da conexão -> Conexao
        self.jogador_da_conexao = {}        # número da conexão -> id do jogador (depois do "ola")
        self.esperando_ola = {}             # número da conexão -> quando chegou
        self.fechar_em = {}                 # número da conexão -> quando fechar (depois de recusar ou expulsar)
        self.votacoes = {}                  # chave -> Votacao aberta (a tela do host chegou lá)
        self.adiantados = {}                # chave -> {id: opção}: votos que chegaram antes da tela do host
        self.preparadas = {}                # chave -> (opções, ao_decidir, prazo): "seguir" esperando o 1º voto
        self.decididas = []                 # chaves já decididas (voto atrasado não reabre)
        self.chaves = {}                    # id do jogador -> chave de volta (quem cair entra de novo com ela)
        self.ping_de = {}                   # id -> quando mandei o último ping (para medir a latência)
        self.retomada = None                # a run num ponto seguro + os comandos desde então (rede/retomada.py)
        self.salvar_ate = None              # quando regravar a partida salva (None: nada mudou)
        self.esperando_o_grupo = False      # retomada do save: o host espera os outros voltarem antes de seguir
        self._proxima_conexao = 1
        self._proximo_jogador = 2
        self.impressao_inicial = None
        self.eu = ID_DO_HOST
        self.lobby.entrar(ID_DO_HOST, nome, cor, host=True)
        self.estado = LOBBY
        self.anunciante = None
        if salva is not None:
            self.carregar_salva(salva)
        if porta_descoberta is not False:
            descoberta = regras_da_rede["porta_descoberta"] if porta_descoberta is None else porta_descoberta
            self.anunciante = Anunciante(descoberta, self.info_para_quem_procura, endereco)

    def info_para_quem_procura(self):
        fora = [self.lobby.jogador(i).nome for i in sorted(self.desconectados) if self.lobby.jogador(i) is not None]
        return {"nome": self.lobby.host().nome, "porta": self.porta, "jogadores": len(self.lobby.jogadores),
                "maximo": configuracao()["max_jogadores"], "aberta": self.estado == LOBBY and not self.lobby.cheio(),
                "id_da_partida": self.id_da_partida, "em_andamento": self.estado == JOGANDO, "fora": fora}

    # ---------------- retomar uma partida salva ----------------
    def carregar_salva(self, salva):
        """A partida salva volta: o grupo de antes (todos fora, menos o host) e a run no ponto em que estava.
        ValueError se não der para refazer a run."""
        jogadores = [JogadorNoLobby.de_dict(j) for j in salva["jogadores"] if isinstance(j, dict)]
        if not any(j.id == ID_DO_HOST for j in jogadores):
            raise ValueError("A partida salva não tem o host.")
        self.lobby.jogadores = jogadores
        for jogador in jogadores:
            jogador.host = jogador.id == ID_DO_HOST
        self.chaves = {str(i): str(c) for i, c in (salva.get("chaves") or {}).items()}
        self.id_da_partida = str(salva.get("id_da_partida") or self.id_da_partida)
        self._proximo_jogador = int(salva.get("proximo_jogador", len(jogadores) + 1))
        self.retomada = Retomada.de_dict(salva["retomada"])
        try:
            self.retomada.refazer(self.comecar_run)
        except Exception as erro:
            raise ValueError(f"A run salva não pôde ser refeita ({type(erro).__name__}).") from erro
        self.desconectados = {j.id for j in jogadores if j.id != self.eu}
        self.sincronia = {j.id: (True if j.id == self.eu else None) for j in jogadores}
        self.esperando_o_grupo = True
        self.retomou = True

    def faltam_voltar(self):
        """Quem ainda não voltou (a partida retomada do save espera por eles)."""
        return [j for j in self.lobby.jogadores if j.id in self.desconectados]

    def seguir_sem_esperar(self):
        """O host não espera mais: quem falta continua com a IA até voltar."""
        self.esperando_o_grupo = False

    def dados_para_salvar(self):
        return {"versao": VERSAO, "assinatura": assinatura_dos_dados(), "id_da_partida": self.id_da_partida,
                "jogadores": [j.para_dict() for j in self.lobby.jogadores], "chaves": dict(self.chaves),
                "proximo_jogador": self._proximo_jogador, "retomada": self.retomada.para_dict()}

    def salvar_agora(self):
        """Grava a partida (ou apaga, se a run acabou). Erro de disco não derruba a partida."""
        self.salvar_ate = None
        if self.retomada is None or self.run is None:
            return
        try:
            if self.run.terminou():
                apagar_partida_salva()
            else:
                salvar_partida(self.dados_para_salvar())
        except OSError:
            self.avisos.append(("Não deu para salvar a partida", "O disco recusou a gravação; a run segue."))

    def comando_aceito(self, dados):
        """Cada comando aceito: anota para quem voltar e marca para regravar o save (logo, sem travar a tela)."""
        if self.retomada is not None:
            self.retomada.anotar(dados, self.sessao.estado, configuracao()["comandos_por_ponto"])
            if self.salvar_ate is None:
                self.salvar_ate = time.monotonic() + 1.0
            if self.run.terminou():
                self.salvar_agora()                       # (a run acabou: o save some na hora)

    def marcar_ponto(self):
        """O estado de agora vira o ponto de retomada (se for seguro). Devolve True se marcou."""
        if self.retomada is None or self.sessao is None:
            return False
        marcou = self.retomada.marcar(self.sessao.estado)
        if marcou:
            self.sessao.ultima_impressao = self.sessao.estado.impressao_digital()   # (sem luta: é o estado de agora)
            self.salvar_agora()
        return marcou

    def pacote_de_retomada(self, identificador):
        """O que quem volta precisa para ficar igual ao host: a run do ponto, os comandos, quem está fora e as
        votações abertas."""
        votacoes = [v.para_dict() for v in self.votacoes.values()]
        votacoes += [{"chave": c, "votos": dict(v)} for c, v in self.adiantados.items()]
        return {"id": identificador, "chave": self.chaves.get(identificador), "id_da_partida": self.id_da_partida,
                "lobby": self.lobby.para_dict(), "chat": [m.para_dict() for m in self.lobby.chat[-20:]],
                "retomada": self.retomada.para_dict(), "impressao": self.sessao.ultima_impressao,
                "votacoes": votacoes, "desconectados": sorted(self.desconectados - {identificador}),
                "latencias": dict(self.latencias)}

    # ---------------- mandar ----------------
    def transmitir(self, tipo, dados=None):
        """Para todos que já entraram."""
        for numero in list(self.jogador_da_conexao):
            conexao = self.conexoes.get(numero)
            if conexao is not None:
                conexao.enviar(tipo, dados)

    def enviar_para(self, identificador, tipo, dados=None):
        numero = self.numero_de(identificador)
        if numero is not None and numero in self.conexoes:
            self.conexoes[numero].enviar(tipo, dados)

    def numero_de(self, identificador):
        return next((n for n, i in self.jogador_da_conexao.items() if i == identificador), None)

    def mandar_lobby(self):
        self.transmitir("lobby", self.lobby.para_dict())

    def sistema(self, texto):
        """Mensagem do jogo no chat (entrou, saiu...) e aviso na tela."""
        mensagem = MensagemDeChat("", "", (200, 190, 170), texto, sistema=True)
        self.lobby.falar(mensagem)
        self.transmitir("chat", mensagem.para_dict())
        self.avisos.append((texto, ""))

    def falar(self, jogador, texto, emote=False):
        mensagem = MensagemDeChat(jogador.id, jogador.nome, jogador.cor, texto, emote=emote)
        self.lobby.falar(mensagem)
        self.transmitir("chat", mensagem.para_dict())
        if emote:
            self.baloes[jogador.id] = (texto, time.monotonic())

    # ---------------- o que chega ----------------
    def tratar(self, etiqueta, tipo, dados):
        if tipo == "nova":
            numero, self._proxima_conexao = self._proxima_conexao, self._proxima_conexao + 1
            self.conexoes[numero] = Conexao(dados, self.fila, numero)
            self.esperando_ola[numero] = time.monotonic()
        elif tipo == "fechou":
            self.desconectou(etiqueta, dados)
        elif tipo == "mensagem" and etiqueta in self.conexoes:
            identificador = self.jogador_da_conexao.get(etiqueta)
            if identificador is None:
                if dados["tipo"] == "ola":
                    self.receber_ola(etiqueta, dados)
                return
            self.receber(identificador, dados["tipo"], dados["dados"])

    def receber_ola(self, numero, mensagem):
        conexao, dados = self.conexoes[numero], mensagem["dados"]
        motivo = None
        if mensagem.get("protocolo") != PROTOCOLO:
            motivo = "O jogo do host fala outra versão do protocolo: atualizem os dois para a mesma versão."
        elif dados.get("versao") != VERSAO:
            motivo = f"Versões diferentes: o host tem {VERSAO} e você tem {texto_limpo(dados.get('versao'), 12)}."
        elif dados.get("assinatura") != assinatura_dos_dados():
            motivo = "Os dados do jogo são diferentes nos dois computadores (arquivos mexidos?). Usem a mesma cópia."
        elif self.estado == JOGANDO and self.quem_volta(dados.get("volta")) is not None:
            self.esperando_ola.pop(numero, None)
            self.aceitar_volta(numero, self.quem_volta(dados.get("volta")))
            return
        elif self.estado != LOBBY:
            motivo = "A partida já começou (só quem já estava nela pode voltar)."
        elif self.lobby.cheio():
            motivo = f"A partida está cheia ({configuracao()['max_jogadores']} jogadores)."
        self.esperando_ola.pop(numero, None)
        if motivo:
            conexao.enviar("recusado", {"motivo": motivo})
            self.fechar_em[numero] = time.monotonic() + ESPERA_PARA_FECHAR
            return
        identificador = f"j{self._proximo_jogador}"
        self._proximo_jogador += 1
        jogador = self.lobby.entrar(identificador, dados.get("nome"), dados.get("cor"))
        jogador.herois = resumos_validos(dados.get("herois"))
        self.jogador_da_conexao[numero] = identificador
        self.chaves[identificador] = uuid.uuid4().hex
        conexao.enviar("bem_vindo", {"id": identificador, "lobby": self.lobby.para_dict(),
                                     "chat": [m.para_dict() for m in self.lobby.chat[-20:]],
                                     "chave": self.chaves[identificador], "id_da_partida": self.id_da_partida})
        self.sistema(f"{jogador.nome} entrou na partida.")
        self.mandar_lobby()

    def quem_volta(self, volta):
        """O id do jogador dono desta chave de volta (ou None)."""
        if not isinstance(volta, dict) or not isinstance(volta.get("chave"), str) or not volta["chave"]:
            return None
        return next((i for i, c in self.chaves.items() if c == volta["chave"] and i != self.eu
                     and self.lobby.jogador(i) is not None), None)

    def aceitar_volta(self, numero, identificador):
        """Quem caiu (ou fechou o jogo) voltou no meio da run: recebe o estado de agora e volta a mandar nos seus heróis."""
        antigo = self.numero_de(identificador)
        if antigo is not None:                            # a conexão velha ainda não tinha caído aqui: sai sem aviso
            self.jogador_da_conexao.pop(antigo, None)
            conexao_velha = self.conexoes.pop(antigo, None)
            if conexao_velha is not None:
                conexao_velha.fechar()
        self.jogador_da_conexao[numero] = identificador
        self.desconectados.discard(identificador)
        self.sincronia[identificador] = None
        self.conexoes[numero].enviar("retomar", self.pacote_de_retomada(identificador))
        if antigo is None:
            self.sistema(f"{self.lobby.jogador(identificador).nome} voltou à partida.")
        self.mandar_presenca()

    def mandar_presenca(self):
        self.transmitir("presenca", {"desconectados": sorted(self.desconectados), "latencias": dict(self.latencias)})

    def receber(self, identificador, tipo, dados):
        jogador = self.lobby.jogador(identificador)
        if jogador is None:
            return
        regras_da_rede = configuracao()
        if tipo == "herois" and self.estado == LOBBY:
            jogador.herois = resumos_validos(dados.get("herois"))
            jogador.pronto, jogador.pacote = False, None
            self.mandar_lobby()
        elif tipo == "pronto" and self.estado == LOBBY:
            motivo = self.ficar_pronto(jogador, bool(dados.get("pronto")), dados.get("pacote"))
            if motivo:
                self.enviar_para(identificador, "recusa", {"mensagem": motivo})
        elif tipo == "chat":
            texto = texto_limpo(dados.get("texto"), regras_da_rede["maximo_do_chat"])
            if texto:
                self.falar(jogador, texto)
        elif tipo == "emote":
            indice = dados.get("indice")
            if isinstance(indice, int) and 0 <= indice < len(regras_da_rede["emotes"]):
                self.falar(jogador, regras_da_rede["emotes"][indice], emote=True)
        elif tipo == "comando" and self.estado == JOGANDO and self.sessao is not None:
            self.sessao.receber(identificador, dados.get("comando"))          # (executa quando a tela deixar)
        elif tipo == "votar" and self.estado == JOGANDO:
            self.receber_voto(identificador, str(dados.get("chave", "")), dados.get("opcao"))
        elif tipo == "carregou" and self.estado == JOGANDO:
            igual = dados["igual"] if isinstance(dados.get("igual"), bool) else dados.get("impressao") == self.impressao_inicial
            self.sincronia[identificador] = igual
            if not igual:
                self.avisos.append(("Estado diferente", f"A run de {jogador.nome} não ficou igual à do host."))
            self.transmitir("sincronia", self.sincronia)
        elif tipo == "ressincronizar" and self.estado == JOGANDO and self.retomada is not None:
            self.sincronia[identificador] = None              # (dessincronizou lá: manda o estado de novo)
            self.enviar_para(identificador, "retomar", self.pacote_de_retomada(identificador))
        elif tipo == "ping":
            self.enviar_para(identificador, "pong", {"t": dados.get("t")})
        elif tipo == "pong" and isinstance(dados.get("t"), (int, float)):
            self.latencias[identificador] = max(0, round((time.monotonic() - dados["t"]) * 1000))
        elif tipo == "tchau":
            self.desconectou(self.numero_de(identificador), "saiu")

    def desconectou(self, numero, motivo=""):
        conexao = self.conexoes.pop(numero, None)
        if conexao is not None:
            conexao.fechar()
        self.esperando_ola.pop(numero, None)
        self.fechar_em.pop(numero, None)
        identificador = self.jogador_da_conexao.pop(numero, None)
        if identificador is None:
            return
        if self.estado == LOBBY:
            jogador = self.lobby.sair(identificador)
            self.sistema(f"{jogador.nome} saiu da partida.")
            self.mandar_lobby()
        else:
            jogador = self.lobby.jogador(identificador)
            self.desconectados.add(identificador)
            self.latencias.pop(identificador, None)
            self.sistema(f"{jogador.nome} caiu da partida (a IA joga por {jogador.nome} até voltar)."
                         if motivo != "saiu" else f"{jogador.nome} saiu da partida.")
            self.mandar_presenca()

    def cuidar_das_conexoes(self):
        agora = time.monotonic()
        regras_da_rede = configuracao()
        if self.hora_do_ping():
            self.latencias[self.eu] = 0
            self.transmitir("ping", {"t": agora})
            if self.jogador_da_conexao:
                self.mandar_presenca()                    # (quem caiu e a latência de cada um, para todos)
        if self.salvar_ate is not None and agora >= self.salvar_ate:
            self.salvar_agora()
        for numero, quando in list(self.fechar_em.items()):
            if agora >= quando:
                self.desconectou(numero)
        for numero, quando in list(self.esperando_ola.items()):
            if agora - quando > regras_da_rede["tempo_para_conectar"]:
                self.desconectou(numero)                  # conectou e não disse quem é
        for numero, conexao in list(self.conexoes.items()):
            if numero in self.jogador_da_conexao and conexao.silencio() > regras_da_rede["tempo_sem_resposta"]:
                self.desconectou(numero, "sem resposta")
        self.cuidar_das_votacoes()

    # ---------------- votações ----------------
    def abrir_votacao(self, chave, opcoes, ao_decidir, prazo=None, esperar_primeiro_voto=False):
        """A tela do host chegou a uma escolha do grupo: abre a votação (ou atualiza as opções e o que fazer).
        ao_decidir(opção) roda quando todos votarem ou o tempo acabar. esperar_primeiro_voto: o relógio só começa
        quando alguém votar (o "seguir" da loja não fecha sozinho enquanto todos ainda compram)."""
        if chave in self.decididas or not opcoes:
            return
        prazo = prazo or configuracao()["tempo_de_votacao"]
        votacao = self.votacoes.get(chave)
        if votacao is None:
            if esperar_primeiro_voto and not self.adiantados.get(chave):
                self.preparadas[chave] = (list(opcoes), ao_decidir, prazo)
                return
            votacao = Votacao(chave, opcoes, prazo, self.adiantados.pop(chave, {}))
            self.votacoes[chave] = votacao
            self.preparadas.pop(chave, None)
            self.anunciar_votacao(votacao)
        votacao.opcoes = list(opcoes)
        votacao.ao_decidir = ao_decidir

    def anunciar_votacao(self, votacao, decidida=None):
        dados = votacao.para_dict()
        if decidida is not None:
            dados["decidida"] = decidida
        self.guardar_votacao(dados)
        self.transmitir("votacao", dados)

    def votar(self, chave, opcao):
        self.receber_voto(self.eu, chave, opcao)

    def receber_voto(self, jogador, chave, opcao):
        if not isinstance(opcao, int) or chave in self.decididas:
            return
        votacao = self.votacoes.get(chave)
        if votacao is None and chave in self.preparadas:   # o primeiro voto de um "seguir": o relógio começa
            opcoes, ao_decidir, prazo = self.preparadas.pop(chave)
            votacao = self.votacoes[chave] = Votacao(chave, opcoes, prazo, self.adiantados.pop(chave, {}))
            votacao.ao_decidir = ao_decidir
        if votacao is None:                               # a tela do host ainda não chegou: guarda para depois
            self.adiantados.setdefault(chave, {})[jogador] = opcao
            self.guardar_votacao({"chave": chave, "votos": self.adiantados[chave]})
            self.transmitir("votacao", {"chave": chave, "votos": self.adiantados[chave]})
            return
        if votacao.votar(jogador, opcao):
            self.anunciar_votacao(votacao)

    def cuidar_das_votacoes(self):
        for chave, votacao in list(self.votacoes.items()):
            if not votacao.decidida(self.conectados()):
                continue
            del self.votacoes[chave]
            self.decididas = (self.decididas + [chave])[-60:]
            opcao = votacao.vencedora()
            self.anunciar_votacao(votacao, decidida=opcao)
            if votacao.ao_decidir is not None:
                votacao.ao_decidir(opcao)

    def voltar_ao_lobby(self):
        """A run acabou: o grupo volta ao lobby (quem caiu durante a run sai da lista)."""
        if self.estado != JOGANDO:
            return
        for identificador in self.desconectados:
            self.lobby.sair(identificador)
        self.largar_run()
        self.votacoes, self.adiantados, self.preparadas = {}, {}, {}
        self.retomada, self.salvar_ate, self.esperando_o_grupo = None, None, False
        apagar_partida_salva()                            # (a run acabou: não há o que retomar)
        self.transmitir("voltou_ao_lobby", {"lobby": self.lobby.para_dict()})

    # ---------------- o que o host faz (pela tela) ----------------
    def definir_meus_herois(self, resumos):
        meu = self.meu()
        meu.herois = resumos_validos(resumos)
        meu.pronto, meu.pacote = False, None
        self.mandar_lobby()

    def marcar_pronto(self, pronto, pacote=None):
        """Devolve o motivo de não poder (texto) ou None."""
        return self.ficar_pronto(self.meu(), pronto, pacote)

    def ficar_pronto(self, jogador, pronto, pacote):
        if pronto:
            motivo = validar_pacote(pacote)
            if motivo:
                return motivo
            jogador.pacote = pacote
        jogador.pronto = pronto and jogador.pacote is not None
        if not pronto:
            jogador.pacote = None
        self.mandar_lobby()
        return None

    def falar_no_chat(self, texto):
        texto = texto_limpo(texto, configuracao()["maximo_do_chat"])
        if texto:
            self.falar(self.meu(), texto)

    def mandar_emote(self, indice):
        emotes = configuracao()["emotes"]
        if 0 <= indice < len(emotes):
            self.falar(self.meu(), emotes[indice], emote=True)

    def expulsar(self, identificador):
        if identificador == self.eu or self.estado != LOBBY:
            return False
        numero = self.numero_de(identificador)
        jogador = self.lobby.sair(identificador)
        if numero is None or jogador is None:
            return False
        self.conexoes[numero].enviar("expulso", {"motivo": "O host tirou você da partida."})
        self.jogador_da_conexao.pop(numero, None)
        self.fechar_em[numero] = time.monotonic() + ESPERA_PARA_FECHAR
        self.sistema(f"{jogador.nome} foi tirado da partida.")
        self.mandar_lobby()
        return True

    def motivo_para_nao_iniciar(self):
        return self.lobby.motivo_para_nao_iniciar()

    def iniciar(self, semente=None):
        """Cria a run com os heróis de todos e manda a cada um. Devolve o motivo de não poder ou None."""
        from roguelike.posse import Jogador
        from roguelike.run import Run
        motivo = self.motivo_para_nao_iniciar()
        if motivo:
            return motivo
        participantes = [(Jogador(j.id, j.nome, j.cor), j.pacote) for j in self.lobby.jogadores]
        criada = self.progresso.criar_run_em_grupo(participantes, semente or None)
        texto = json.dumps(criada.para_dict(), ensure_ascii=False)
        run = Run.de_dict(json.loads(texto))          # o host parte do mesmo dado que os clientes recebem
        self.comecar_run(run)
        self.retomada = Retomada(json.loads(texto))   # (o começo da run já é um ponto seguro)
        self.impressao_inicial = self.sessao.estado.impressao_digital()
        self.sincronia = {j.id: (True if j.id == self.eu else None) for j in self.lobby.jogadores}
        self.transmitir("iniciar", {"run": json.loads(texto)})
        self.salvar_agora()
        return None

    def fechar(self):
        """O host sai: avisa todos e fecha a partida (no meio da run, ela fica salva para retomar)."""
        motivo, meu = "O host fechou a partida.", "Você fechou a partida."
        if self.estado == JOGANDO and self.retomada is not None and self.run is not None and not self.run.terminou():
            self.salvar_agora()
            motivo += " A run ficou salva com o host: quando ele retomar, entre de novo pelo código."
            meu += " A run ficou salva: \"Retomar partida\" continua de onde parou."
        self.transmitir("encerrada", {"motivo": motivo})
        if self.jogador_da_conexao:
            time.sleep(0.15)                              # (o aviso sai antes de os sockets fecharem)
        self.encerrar(meu)

    def fechar_rede(self):
        for conexao in list(self.conexoes.values()):
            conexao.fechar()
        self.conexoes.clear()
        self.servidor.fechar()
        if self.anunciante is not None:
            self.anunciante.fechar()


# ============================================================
# QUEM ENTRA
# ============================================================

class PartidaCliente(Partida):
    """Quem entra numa partida: conecta (em outra thread), se apresenta e segue o que o host manda.

    volta: a chave de volta guardada (Opções) de uma partida em que este jogador estava: se for a mesma, o host
    devolve a run no ponto em que está ("retomar") em vez do lobby."""

    def __init__(self, progresso, nome, cor, ip, porta, herois=(), volta=None):
        super().__init__(progresso, nome, cor)
        self.ip, self.porta = ip, porta
        self.conexao = None
        self.etiqueta = 0                   # cada conexão ao host tem a sua (o "fechou" de uma velha não conta)
        self.herois_iniciais = resumos_validos(list(herois))
        self.esperando_desde = time.monotonic()
        self.avisou_divergencia = False
        self.pediu_o_estado = 0.0           # quando pediu "ressincronizar" pela última vez
        self.lobby_que_voltou = None
        self.volta = volta if isinstance(volta, dict) else None
        self.chave_de_volta = None          # a chave desta partida (do "bem_vindo")
        self.id_da_partida = None
        self.volta_para_guardar = None      # a chave nova, para o fluxo guardar nas Opções
        self.reconectando = None            # {"desde", "proxima", "tentando", "tentativas", "motivo"} ou None
        conectar(self.fila, ip, porta, configuracao()["tempo_para_conectar"])

    def mandar(self, tipo, dados=None):
        if self.conexao is not None:
            self.conexao.enviar(tipo, dados)

    def conectado(self):
        return self.conexao is not None and self.conexao.aberta and self.reconectando is None

    def pegar_volta(self):
        volta, self.volta_para_guardar = self.volta_para_guardar, None
        return volta

    def latencia_de(self, identificador):
        """A minha (e a do host, que é a mesma ida e volta) eu meço; as dos outros o host manda."""
        host = self.lobby.host()
        if identificador == self.eu or (host is not None and identificador == host.id):
            return self.latencias.get(self.eu)
        return self.latencias.get(identificador)

    # ---------------- o que chega ----------------
    def tratar(self, etiqueta, tipo, dados):
        if tipo in ("fechou", "mensagem") and etiqueta != self.etiqueta:
            return                                        # (de uma conexão velha, de antes de voltar)
        if tipo == "conectou":
            self.etiqueta += 1
            self.conexao = Conexao(dados, self.fila, self.etiqueta)
            self.esperando_desde = time.monotonic()
            volta = {"chave": self.chave_de_volta} if self.chave_de_volta else self.volta
            self.mandar("ola", {"nome": self.nome_pedido, "cor": list(self.cor_pedida), "versao": VERSAO,
                                "assinatura": assinatura_dos_dados(), "herois": self.herois_iniciais, "volta": volta})
        elif tipo == "falhou":
            if self.reconectando is not None:
                self.tentar_de_novo()
            else:
                self.encerrar(dados)
        elif tipo == "fechou":
            self.conexao = None
            if self.reconectando is not None:
                self.tentar_de_novo()
            elif self.estado == JOGANDO and self.chave_de_volta:
                self.comecar_a_voltar(f"A conexão com o host caiu ({dados})")
            else:
                self.encerrar("O host recusou a conexão." if self.estado == CONECTANDO else
                              f"A conexão com o host caiu ({dados})")
        elif tipo == "mensagem":
            try:
                self.receber(dados["tipo"], dados["dados"])
            except (KeyError, TypeError, ValueError) as erro:
                self.encerrar(f"O host mandou algo que este jogo não entende ({type(erro).__name__}).")

    def receber(self, tipo, dados):
        if tipo == "recusado":
            self.encerrar(texto_limpo(dados.get("motivo"), 300) or "O host recusou a entrada.")
        elif tipo == "bem_vindo":
            self.eu = str(dados["id"])
            self.lobby.atualizar_de(dados.get("lobby"))
            self.lobby.chat = [MensagemDeChat.de_dict(m) for m in dados.get("chat", []) if isinstance(m, dict)]
            self.guardar_chave(dados)
            self.estado = LOBBY
        elif tipo == "retomar":
            self.retomar(dados)
        elif tipo == "ping":
            self.mandar("pong", {"t": dados.get("t")})
        elif tipo == "pong" and isinstance(dados.get("t"), (int, float)):
            self.latencias[self.eu] = max(0, round((time.monotonic() - dados["t"]) * 1000))
        elif tipo == "lobby":
            self.lobby.atualizar_de(dados)
        elif tipo == "chat":
            mensagem = MensagemDeChat.de_dict(dados)
            self.lobby.falar(mensagem)
            if mensagem.sistema:
                self.avisos.append((mensagem.texto, ""))
            elif mensagem.emote:
                self.baloes[mensagem.autor] = (mensagem.texto, time.monotonic())
        elif tipo in ("expulso", "encerrada"):
            self.encerrar(texto_limpo(dados.get("motivo"), 300) or "A partida acabou.")
        elif tipo == "recusa":
            self.avisos.append(("Não deu", texto_limpo(dados.get("mensagem"), 300)))
            if self.sessao is not None:
                self.sessao.recusas += 1
        elif tipo == "iniciar" and self.estado == LOBBY:
            self.carregar_run(dados.get("run"))
        elif tipo == "aplicar" and self.sessao is not None:
            self.sessao.aplicar(dados)                    # (processar() executa quando a tela deixar)
        elif tipo == "sincronia":
            self.sincronia = {str(i): v for i, v in dados.items()}
        elif tipo == "votacao":
            self.guardar_votacao(dados)
        elif tipo == "presenca":
            self.desconectados = {str(i) for i in dados.get("desconectados", [])}
            self.guardar_latencias(dados.get("latencias"))
        elif tipo == "voltou_ao_lobby" and self.estado == JOGANDO:
            self.lobby_que_voltou = dados.get("lobby")      # (volta depois de executar o que ainda está na fila)

    def guardar_chave(self, dados):
        chave = dados.get("chave")
        if isinstance(chave, str) and chave:
            self.chave_de_volta, self.id_da_partida = chave, str(dados.get("id_da_partida") or "")
            self.volta_para_guardar = {"chave": chave, "id_da_partida": self.id_da_partida}

    def guardar_latencias(self, latencias):
        if isinstance(latencias, dict):
            minha = self.latencias.get(self.eu)
            self.latencias = {str(i): v for i, v in latencias.items() if isinstance(v, (int, float))}
            if minha is not None:
                self.latencias[self.eu] = minha               # (a minha eu meço daqui)

    # ---------------- voltar à run ----------------
    def retomar(self, dados):
        """O host mandou a run do ponto seguro + os comandos: refaz tudo até o estado de agora (voltou depois de
        cair, entrou de novo com a chave ou dessincronizou)."""
        try:
            retomada = Retomada.de_dict(dados.get("retomada"))
            self.eu = str(dados["id"])
            self.guardar_chave(dados)
            self.lobby.atualizar_de(dados.get("lobby"))
            if not self.lobby.chat:
                self.lobby.chat = [MensagemDeChat.de_dict(m) for m in dados.get("chat", []) if isinstance(m, dict)]
            sessao = retomada.refazer(self.comecar_run)
        except Exception as erro:
            self.encerrar(f"Não deu para voltar à partida: a run do host não pôde ser refeita aqui "
                          f"({type(erro).__name__}).")
            return
        self.desconectados = {str(i) for i in dados.get("desconectados", [])}
        self.guardar_latencias(dados.get("latencias"))
        for votacao in dados.get("votacoes", []):
            if isinstance(votacao, dict):
                self.guardar_votacao(votacao)
        igual = sessao.estado.impressao_digital() == dados.get("impressao")
        self.mandar("carregou", {"igual": igual})
        if not igual:
            self.avisos.append(("Estado diferente", "A run refeita aqui não ficou igual à do host."))
        self.reconectando = None
        self.avisou_divergencia = False
        self.lobby_que_voltou = None
        self.retomou = True

    def comecar_a_voltar(self, motivo):
        """Caiu no meio da run: tenta voltar sozinho (a IA do host joga pelos meus heróis enquanto isso)."""
        agora = time.monotonic()
        self.conexao = None
        self.reconectando = {"desde": agora, "proxima": agora, "tentando": False, "tentativas": 0, "motivo": motivo}
        self.avisos.append(("Conexão perdida", "Tentando voltar à partida... (a IA joga pelos seus heróis até lá)"))

    def tentar_de_novo(self):
        if self.conexao is not None:
            self.conexao.fechar()
            self.conexao = None
        self.reconectando["tentando"] = False
        self.reconectando["proxima"] = time.monotonic() + configuracao()["intervalo_de_reconexao"]

    def cuidar_da_volta(self):
        regras_da_rede, agora, volta = configuracao(), time.monotonic(), self.reconectando
        if self.conexao is not None and agora - self.esperando_desde > regras_da_rede["tempo_para_conectar"]:
            self.tentar_de_novo()                         # conectou mas o host não respondeu ao "ola"
        if volta["tentando"]:
            return
        if agora - volta["desde"] > regras_da_rede["tempo_para_voltar"]:
            self.encerrar(f"{volta['motivo']} e não deu para voltar à partida. Se o host retomar a partida salva, "
                          "entre de novo pelo código: seus heróis voltam com você.")
        elif agora >= volta["proxima"]:
            volta["tentando"] = True
            volta["tentativas"] += 1
            conectar(self.fila, self.ip, self.porta, regras_da_rede["tempo_para_conectar"])

    def segundos_tentando_voltar(self):
        return time.monotonic() - self.reconectando["desde"] if self.reconectando is not None else 0.0

    def atualizar(self):
        super().atualizar()
        sessao = self.sessao
        if self.encerrada:
            return
        if sessao is not None and sessao.divergiu and self.conectado() and \
                time.monotonic() - self.pediu_o_estado > PEDIR_O_ESTADO_DE_NOVO:
            self.pediu_o_estado = time.monotonic()
            if not self.avisou_divergencia:
                self.avisou_divergencia = True
                self.avisos.append(("Partida dessincronizada", sessao.divergiu + " Buscando o estado do host..."))
            self.mandar("ressincronizar")
        if self.lobby_que_voltou is not None and (sessao is None or not (sessao.fila or sessao.aplicados)):
            self.largar_run()                               # o host voltou ao lobby e a run daqui já acabou
            self.lobby.atualizar_de(self.lobby_que_voltou)
            self.lobby_que_voltou = None

    def votar(self, chave, opcao):
        """Vota (o host decide). O voto aparece aqui na hora; a contagem de verdade volta do host."""
        info = self.votos.setdefault(chave, {"votos": {}})
        info["votos"][self.eu] = opcao
        self.mandar("votar", {"chave": chave, "opcao": opcao})

    def carregar_run(self, dados):
        from roguelike.run import Run
        try:
            run = Run.de_dict(dados)
        except Exception as erro:
            self.encerrar(f"Não deu para carregar a run do host ({type(erro).__name__}).")
            return
        self.comecar_run(run)
        self.mandar("carregou", {"impressao": self.sessao.estado.impressao_digital()})

    def cuidar_das_conexoes(self):
        regras_da_rede = configuracao()
        if self.reconectando is not None:
            self.cuidar_da_volta()
            return
        if self.conexao is None:
            return                                        # (conectar() tem o próprio tempo limite)
        if self.estado == CONECTANDO and time.monotonic() - self.esperando_desde > regras_da_rede["tempo_para_conectar"]:
            self.encerrar("O host não respondeu à entrada.")
            return
        if self.hora_do_ping():
            self.mandar("ping", {"t": time.monotonic()})
        if self.conexao.silencio() > regras_da_rede["tempo_sem_resposta"]:
            if self.estado == JOGANDO and self.chave_de_volta:
                self.conexao.fechar()
                self.comecar_a_voltar("O host parou de responder")
            else:
                self.encerrar("O host parou de responder.")

    # ---------------- o que eu faço (pela tela) ----------------
    def definir_meus_herois(self, resumos):
        self.herois_iniciais = resumos_validos(list(resumos))
        meu = self.meu()
        if meu is not None:
            meu.herois, meu.pronto = list(self.herois_iniciais), False
        self.mandar("herois", {"herois": self.herois_iniciais})

    def marcar_pronto(self, pronto, pacote=None):
        """O host confere o pacote; recusado, chega um aviso. Devolve None (ou o motivo, se nem dá para mandar)."""
        if pronto:
            motivo = validar_pacote(pacote, importar=False)
            if motivo:
                return motivo
        self.mandar("pronto", {"pronto": bool(pronto), "pacote": pacote if pronto else None})
        return None

    def falar_no_chat(self, texto):
        texto = texto_limpo(texto, configuracao()["maximo_do_chat"])
        if texto:
            self.mandar("chat", {"texto": texto})

    def mandar_emote(self, indice):
        self.mandar("emote", {"indice": indice})

    def fechar(self):
        self.mandar("tchau")
        if self.conexao is not None and self.conexao.aberta:
            time.sleep(0.1)                               # (o tchau sai antes de o socket fechar)
        self.encerrar("Você saiu da partida.")

    def fechar_rede(self):
        if self.conexao is not None:
            self.conexao.fechar()


# ============================================================
# CONFERIR O QUE VEM DE FORA
# ============================================================

def validar_pacote(pacote, importar=True):
    """O pacote de heróis de um jogador dá para usar? Devolve o motivo (texto) ou None.
    (No host também registra as peças de afixos dele: importar=True.)"""
    from roguelike.classes import heroi_de_dict
    from roguelike.dados import regras
    from roguelike.exemplares import importar as importar_exemplares
    from roguelike.itens import existe
    if not isinstance(pacote, dict) or not isinstance(pacote.get("herois"), list):
        return "Os heróis não chegaram direito."
    if not 1 <= len(pacote["herois"]) <= regras()["grupo"]["maximo"]:
        return "Número de heróis fora do permitido."
    provisoes = pacote.get("provisoes") or {}
    emprestados = pacote.get("emprestados") or {}
    ouro = pacote.get("ouro_extra", 0)
    if not isinstance(provisoes, dict) or not all(isinstance(c, str) and existe(c) and isinstance(q, int) and 0 <= q <= 99
                                                  for c, q in provisoes.items()):
        return "Provisões inválidas."
    if not isinstance(emprestados, dict) or not all(isinstance(q, int) and q >= 0 for q in emprestados.values()):
        return "Peças do arsenal inválidas."
    if not isinstance(ouro, int) or not 0 <= ouro <= 100000:
        return "Ouro inválido."
    if not isinstance(pacote.get("exemplares") or {}, dict):
        return "Peças com afixos inválidas."
    try:
        if importar:
            importar_exemplares(pacote.get("exemplares"))
        for dados in pacote["herois"]:
            heroi_de_dict(copy.deepcopy(dados))
    except Exception:
        return "Os heróis enviados não puderam ser lidos (versões diferentes?)."
    return None
