"""O formato das mensagens: uma linha de JSON por mensagem, em UTF-8.

    {"tipo": "chat", "protocolo": 1, "dados": {"texto": "Olá!"}}\\n

Mensagens do cliente para o host: ola (com a chave de volta, se houver), herois, pronto, chat, emote, comando, votar,
carregou, ressincronizar, ping, pong, tchau.
Do host para os clientes: bem_vindo (com a chave de volta), recusado, lobby, chat, expulso, iniciar, retomar,
aplicar, recusa, sincronia, votacao, presenca (quem caiu e as latências), voltou_ao_lobby, encerrada, ping, pong.
(rede/partida.py trata cada uma.)

Ao entrar, o cliente manda a versão do jogo e a assinatura dos dados (um hash dos JSON de conteúdo): com qualquer
diferença os computadores não chegariam ao mesmo estado, então o host recusa com uma mensagem clara.
"""

import hashlib
import json
import os

PROTOCOLO = 1
LIMITE_DA_MENSAGEM = 8 * 1024 * 1024        # uma run inteira tem ~20 KB; mais que isto é erro (ou abuso)

_assinatura = None


class MensagemInvalida(Exception):
    """Chegou algo que não é uma mensagem do jogo (JSON quebrado, grande demais, sem tipo)."""


def configuracao():
    """Os números da rede (regras.json "multiplayer")."""
    from roguelike.dados import regras
    return regras()["multiplayer"]


def codificar(tipo, dados=None):
    """A mensagem pronta para mandar (bytes, terminada em \\n)."""
    texto = json.dumps({"tipo": tipo, "protocolo": PROTOCOLO, "dados": dados if dados is not None else {}},
                       ensure_ascii=False, separators=(",", ":"))
    return (texto + "\n").encode("utf-8")


class Leitor:
    """Junta os pedaços que chegam do socket e devolve as mensagens inteiras (o TCP não respeita as linhas)."""

    def __init__(self, limite=LIMITE_DA_MENSAGEM):
        self.limite = limite
        self.sobra = b""

    def alimentar(self, pedaco):
        """Os bytes que chegaram -> [mensagens completas] (dicts). Erro: MensagemInvalida."""
        self.sobra += pedaco
        mensagens = []
        while b"\n" in self.sobra:
            linha, self.sobra = self.sobra.split(b"\n", 1)
            if linha.strip():
                mensagens.append(decodificar(linha))
        if len(self.sobra) > self.limite:
            raise MensagemInvalida("Mensagem grande demais.")
        return mensagens


def decodificar(linha):
    try:
        mensagem = json.loads(linha.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise MensagemInvalida("Chegou algo que não é uma mensagem do jogo.") from None
    if not isinstance(mensagem, dict) or not isinstance(mensagem.get("tipo"), str):
        raise MensagemInvalida("Mensagem sem tipo.")
    if not isinstance(mensagem.get("dados"), dict):
        mensagem["dados"] = {}
    return mensagem


def assinatura_dos_dados():
    """Hash dos JSON de conteúdo (src/roguelike/dados): iguais nos dois computadores = mesmas regras."""
    global _assinatura
    if _assinatura is None:
        from caminhos import CAMINHOS
        resumo = hashlib.sha256()
        for nome in sorted(os.listdir(CAMINHOS.dados)):
            if nome.endswith(".json"):
                resumo.update(nome.encode("utf-8"))
                with open(os.path.join(CAMINHOS.dados, nome), "rb") as arquivo:
                    resumo.update(arquivo.read().replace(b"\r\n", b"\n"))
        _assinatura = resumo.hexdigest()[:16]
    return _assinatura


def texto_limpo(texto, maximo):
    """Texto de outra pessoa pronto para mostrar: sem quebras nem caracteres de controle, no tamanho máximo."""
    if not isinstance(texto, str):
        return ""
    limpo = "".join(c if c.isprintable() else " " for c in texto)
    return " ".join(limpo.split())[:maximo]
