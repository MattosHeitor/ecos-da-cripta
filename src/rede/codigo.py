"""O código da partida: o IP (e a porta, se não for a padrão) do host escrito em letras fáceis de ditar.

    codigo_de("192.168.0.15")            -> "30AG-00F"     (porta padrão: 7 letras)
    codigo_de("192.168.0.15", 50000)     -> "60N00-0ZGTG"  (outra porta: 10 letras)
    endereco_digitado("30ag-00f")        -> ("192.168.0.15", 47800)
    endereco_digitado("192.168.0.15:5000") -> ("192.168.0.15", 5000)

Sem um servidor no meio não existe código "de verdade": ele é só o endereço do host. Serve na rede local (ou numa
VPN como Tailscale/ZeroTier/Radmin). O alfabeto é o de Crockford: sem I, L, O e U (não se confundem com 1, 0 e V).
"""

import ipaddress
import socket

ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TROCAS = {"O": "0", "I": "1", "L": "1", "U": "V"}


def porta_padrao():
    from rede.protocolo import configuracao
    return configuracao()["porta"]


def codigo_de(ip, porta=None):
    """O código de um endereço IPv4 (com a porta só quando não é a padrão)."""
    numero = int(ipaddress.IPv4Address(ip))
    letras = 7
    if porta is not None and porta != porta_padrao():
        numero = (numero << 16) | int(porta)
        letras = 10
    codigo = ""
    for _ in range(letras):
        numero, resto = divmod(numero, 32)
        codigo = ALFABETO[resto] + codigo
    meio = 4 if letras == 7 else 5
    return codigo[:meio] + "-" + codigo[meio:]


def endereco_do_codigo(codigo):
    """(ip, porta) do código, ou None se não for um código."""
    limpo = "".join(TROCAS.get(c, c) for c in codigo.upper() if c not in "- ")
    if len(limpo) not in (7, 10) or any(c not in ALFABETO for c in limpo):
        return None
    numero = 0
    for c in limpo:
        numero = numero * 32 + ALFABETO.index(c)
    if len(limpo) == 10:
        numero, porta = numero >> 16, numero & 0xFFFF
    else:
        porta = porta_padrao()
    if numero >= 2 ** 32 or not 0 < porta < 65536:
        return None
    return str(ipaddress.IPv4Address(numero)), porta


def endereco_digitado(texto):
    """O que a pessoa digitou ("código", "IP" ou "IP:porta") -> (ip, porta). Não dá: ValueError com o motivo."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Digite o código da partida ou o IP do host.")
    host, _, porta = texto.rpartition(":") if ":" in texto else (texto, "", "")
    try:
        ipaddress.IPv4Address(host)
        eh_ip = True
    except ValueError:
        eh_ip = host.lower() == "localhost"
    if eh_ip:
        if porta and not (porta.isdigit() and 0 < int(porta) < 65536):
            raise ValueError(f"Porta inválida: {porta}")
        return ("127.0.0.1" if host.lower() == "localhost" else host), int(porta) if porta else porta_padrao()
    endereco = endereco_do_codigo(texto)
    if endereco is None:
        raise ValueError("Isso não é um código de partida nem um IP (ex.: 30AG-00F ou 192.168.0.15).")
    return endereco


def ips_deste_pc():
    """Os IPv4 deste computador: o da rede local primeiro e depois os das VPNs (Radmin, Tailscale, ZeroTier,
    Hamachi...), sem o 127.0.0.1. Quem joga por uma VPN usa o IP DELA (o host escolhe no lobby)."""
    ips = []
    principal = ip_na_rede()
    if principal != "127.0.0.1":
        ips.append(principal)
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127.") and not ip.startswith("169.254."):
                ips.append(ip)
    except OSError:
        pass
    return ips or ["127.0.0.1"]


def nome_da_rede(ip):
    """De que rede parece ser o IP (pela faixa que cada VPN costuma usar)."""
    partes = [int(p) for p in ip.split(".")]
    if partes[0] == 26:
        return "Radmin VPN"
    if partes[0] == 25:
        return "Hamachi"
    if partes[0] == 100 and 64 <= partes[1] <= 127:
        return "Tailscale"
    if partes[0] == 127:
        return "este PC"
    if ipaddress.IPv4Address(ip).is_private:
        return "rede local"                         # (a ZeroTier também usa estas faixas)
    return "internet"


def broadcasts_deste_pc():
    """O endereço de broadcast de cada rede deste PC (/8 na Radmin e na Hamachi, /24 nas outras), para a lista de
    partidas achar o host também pela VPN (o "<broadcast>" comum só sai pela rede principal)."""
    enderecos = []
    for ip in ips_deste_pc():
        if ip.startswith("127.") or nome_da_rede(ip) in ("Tailscale", "internet"):    # (Tailscale não repassa)
            continue
        prefixo = 8 if nome_da_rede(ip) in ("Radmin VPN", "Hamachi") else 24
        endereco = str(ipaddress.IPv4Network(f"{ip}/{prefixo}", strict=False).broadcast_address)
        if endereco not in enderecos:
            enderecos.append(endereco)
    return enderecos


def ip_na_rede():
    """O IP deste computador na rede local (o que os outros usam para entrar). Sem rede: 127.0.0.1."""
    teste = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        teste.connect(("10.255.255.255", 1))          # (UDP: não manda nada, só escolhe a interface de saída)
        return teste.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        teste.close()
