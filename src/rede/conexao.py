"""As pontas TCP. Threads só leem do socket e põem o que chegou numa fila; o jogo (a thread do pygame) tira da
fila a cada quadro (Partida.atualizar). Assim nada da partida é mexido por duas threads ao mesmo tempo.

    fila = queue.Queue()
    servidor = Servidor(fila, porta=47800)        # o host: aceita conexões ("nova", socket)
    conectar(fila, "192.168.0.15", 47800)         # o cliente: tenta em outra thread ("conectou" / "falhou")
    conexao = Conexao(socket, fila, etiqueta=3)   # cada mensagem vira (3, "mensagem", dict); a queda, (3, "fechou", motivo)
    conexao.enviar("chat", {"texto": "Olá!"})
"""

import select
import socket
import threading
import time

from rede.protocolo import Leitor, MensagemInvalida, codificar

ESPERA_DA_LEITURA = 0.25           # de quanto em quanto tempo a thread de leitura confere se deve parar
TEMPO_PARA_ENVIAR = 5.0            # um envio parado mais que isto derruba a conexão


class Conexao:
    """Uma conexão TCP com mensagens do jogo. 'etiqueta' diz de quem é cada coisa que vai para a fila."""

    def __init__(self, sock, fila, etiqueta=None):
        self.sock = sock
        self.fila = fila
        self.etiqueta = etiqueta
        self.aberta = True
        self.ultimo_contato = time.monotonic()
        self._leitor = Leitor()
        self._trava = threading.Lock()
        try:
            sock.settimeout(TEMPO_PARA_ENVIAR)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)     # mensagens pequenas saem na hora
        except OSError:
            pass
        self._thread = threading.Thread(target=self._ler, name=f"conexao-{etiqueta}", daemon=True)
        self._thread.start()

    def _ler(self):
        motivo = "A conexão caiu."
        while self.aberta:
            try:
                prontos, _, _ = select.select([self.sock], [], [], ESPERA_DA_LEITURA)
                if not prontos:
                    continue
                pedaco = self.sock.recv(65536)
            except (OSError, ValueError):
                break
            if not pedaco:
                motivo = "A outra ponta fechou a conexão."
                break
            self.ultimo_contato = time.monotonic()
            try:
                mensagens = self._leitor.alimentar(pedaco)
            except MensagemInvalida as erro:
                motivo = str(erro)
                break
            for mensagem in mensagens:
                self.fila.put((self.etiqueta, "mensagem", mensagem))
        if self.aberta:                               # caiu sozinha (não foi fechar() daqui)
            self.aberta = False
            self._soltar_socket()
            self.fila.put((self.etiqueta, "fechou", motivo))

    def enviar(self, tipo, dados=None):
        """Manda uma mensagem. Devolve False se a conexão já caiu (a queda chega na fila como "fechou")."""
        if not self.aberta:
            return False
        try:
            with self._trava:
                self.sock.sendall(codificar(tipo, dados))
            return True
        except OSError:
            self.aberta = False
            self._soltar_socket()
            self.fila.put((self.etiqueta, "fechou", "A conexão caiu."))
            return False

    def silencio(self):
        """Segundos desde a última coisa que chegou."""
        return time.monotonic() - self.ultimo_contato

    def fechar(self):
        """Fecha daqui (nada vai para a fila)."""
        self.aberta = False
        self._soltar_socket()

    def _soltar_socket(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class Servidor:
    """Escuta numa porta TCP; cada conexão nova vai para a fila como (None, "nova", socket).

    endereco "" = todas as interfaces (a rede local); os testes usam "127.0.0.1" (o Windows não pergunta nada do
    firewall para conexões só deste computador). porta 0 = o sistema escolhe (servidor.porta diz qual)."""

    def __init__(self, fila, porta, endereco=""):
        self.fila = fila
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):           # Windows: ninguém mais "divide" a porta da partida
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            self.sock.bind((endereco, porta))
            self.sock.listen(8)
        except OSError:
            self.sock.close()
            raise
        self.porta = self.sock.getsockname()[1]
        self.aberto = True
        self._thread = threading.Thread(target=self._aceitar, name="servidor", daemon=True)
        self._thread.start()

    def _aceitar(self):
        while self.aberto:
            try:
                prontos, _, _ = select.select([self.sock], [], [], ESPERA_DA_LEITURA)
                if not prontos:
                    continue
                novo, _ = self.sock.accept()
            except (OSError, ValueError):
                break
            self.fila.put((None, "nova", novo))

    def fechar(self):
        self.aberto = False
        try:
            self.sock.close()
        except OSError:
            pass


def conectar(fila, ip, porta, tempo):
    """Tenta conectar em outra thread (a tela não trava): põe (None, "conectou", socket) ou
    (None, "falhou", motivo claro) na fila."""
    def tentar():
        try:
            sock = socket.create_connection((ip, porta), timeout=tempo)
        except socket.timeout:
            fila.put((None, "falhou", f"Ninguém respondeu em {ip}:{porta} (tempo esgotado). Confira o código, se "
                                      "estão na mesma rede e se o firewall do host deixou o jogo entrar."))
        except ConnectionRefusedError:
            fila.put((None, "falhou", f"Não há partida aberta em {ip}:{porta}. O host já criou a partida?"))
        except OSError as erro:
            fila.put((None, "falhou", f"Não deu para conectar em {ip}:{porta} ({erro.strerror or erro})."))
        else:
            fila.put((None, "conectou", sock))
    threading.Thread(target=tentar, name="conectar", daemon=True).start()
