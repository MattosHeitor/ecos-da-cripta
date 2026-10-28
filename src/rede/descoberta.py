"""Achar partidas na rede local sem digitar nada (UDP, biblioteca padrão).

    Procurador (quem quer entrar)  de segundo em segundo grita "procura" para a rede inteira (broadcast), para
                                   cada rede do PC (a Radmin VPN também) e para este computador (127.0.0.1: duas
                                   cópias do jogo no mesmo PC)
    Anunciante (o host)            escuta na porta de descoberta e responde a quem procura: nome, porta, vagas

    procurador = Procurador(porta=47801)
    procurador.partidas()          # [{"ip", "porta", "nome", "jogadores", "maximo", "versao"}], as vistas há pouco

Se a porta de descoberta estiver ocupada (outra cópia hospedando no mesmo PC), o anúncio não funciona, mas o
código e o IP continuam valendo.
"""

import json
import socket
import threading
import time

from rede.codigo import broadcasts_deste_pc
from rede.protocolo import PROTOCOLO
from versao import NOME_DO_JOGO, VERSAO

INTERVALO = 1.0                 # segundos entre um grito e outro
VALIDADE = 3.5                  # some da lista a partida que não responde há este tempo


class Anunciante:
    """O host responde "estou aqui" a quem procura. info() devolve o que dizer (nome, porta, jogadores...)."""

    def __init__(self, porta, info, endereco=""):
        self.info = info
        self.aberto = False
        self.porta = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((endereco, porta))
            self.sock.settimeout(0.3)
            self.porta = self.sock.getsockname()[1]
        except OSError:
            self.sock.close()
            return                                    # (sem anúncio: entram pelo código)
        self.aberto = True
        threading.Thread(target=self._responder, name="anunciante", daemon=True).start()

    def _responder(self):
        while self.aberto:
            try:
                dados, origem = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                pedido = json.loads(dados.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            if not isinstance(pedido, dict) or pedido.get("tipo") != "procura" or pedido.get("jogo") != NOME_DO_JOGO:
                continue
            resposta = {"tipo": "partida", "jogo": NOME_DO_JOGO, "protocolo": PROTOCOLO, "versao": VERSAO, **self.info()}
            try:
                self.sock.sendto(json.dumps(resposta).encode("utf-8"), origem)
            except OSError:
                pass

    def fechar(self):
        self.aberto = False
        try:
            self.sock.close()
        except OSError:
            pass


class Procurador:
    """Procura partidas na rede local enquanto estiver aberto. destinos: para onde gritar; endereco_local: onde
    ouvir as respostas ("127.0.0.1" nos testes: o Windows não pergunta do firewall)."""

    def __init__(self, porta, destinos=None, endereco_local=""):
        self.porta = porta
        self.destinos = destinos or ["<broadcast>", *broadcasts_deste_pc(), "127.0.0.1"]
        self.achadas = {}                             # (ip, porta) -> (info, quando)
        self._trava = threading.Lock()
        self.aberto = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind((endereco_local, 0))
            self.sock.settimeout(0.25)
        except OSError:
            self.aberto = False
            self.sock.close()
            return
        threading.Thread(target=self._procurar, name="procurador", daemon=True).start()

    def _procurar(self):
        pedido = json.dumps({"tipo": "procura", "jogo": NOME_DO_JOGO}).encode("utf-8")
        ultimo = 0.0
        while self.aberto:
            if time.monotonic() - ultimo >= INTERVALO:
                ultimo = time.monotonic()
                for destino in self.destinos:
                    try:
                        self.sock.sendto(pedido, (destino, self.porta))
                    except OSError:
                        pass                          # (sem rede: só o 127.0.0.1 responde)
            try:
                dados, (ip, _) = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                if not self.aberto:
                    break
                continue
            try:
                info = json.loads(dados.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            if not isinstance(info, dict) or info.get("tipo") != "partida" or info.get("jogo") != NOME_DO_JOGO:
                continue
            porta = info.get("porta")
            if not isinstance(porta, int):
                continue
            with self._trava:
                self.achadas[(ip, porta)] = (info, time.monotonic())

    def partidas(self):
        """As partidas que responderam há pouco, sem repetir (a mesma por 127.0.0.1 e pelo IP da rede fica uma)."""
        agora = time.monotonic()
        with self._trava:
            vivas = [(ip, porta, info) for (ip, porta), (info, quando) in self.achadas.items()
                     if agora - quando <= VALIDADE]
        lista, vistas = [], set()
        for ip, porta, info in sorted(vivas, key=lambda v: (v[0] == "127.0.0.1", v[0])):
            chave = (info.get("id_da_partida"), porta)
            if chave in vistas:
                continue
            vistas.add(chave)
            fora = info.get("fora") if isinstance(info.get("fora"), list) else []
            lista.append({"ip": ip, "porta": porta, "nome": str(info.get("nome", "?"))[:24],
                          "jogadores": info.get("jogadores", 0), "maximo": info.get("maximo", 0),
                          "versao": info.get("versao", "?"), "aberta": bool(info.get("aberta", True)),
                          "mesma_versao": info.get("versao") == VERSAO and info.get("protocolo") == PROTOCOLO,
                          "id_da_partida": str(info.get("id_da_partida") or ""),
                          "em_andamento": bool(info.get("em_andamento")), "fora": [str(n)[:24] for n in fora[:4]]})
        return lista

    def fechar(self):
        self.aberto = False
        try:
            self.sock.close()
        except OSError:
            pass
