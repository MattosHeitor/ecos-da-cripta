"""O lobby em dados (sem rede e sem pygame): quem está, com que cor, quais heróis, quem está pronto e o chat.

O host guarda o Lobby de verdade e manda uma cópia (para_dict) a todos sempre que algo muda; os clientes só
desenham a cópia. Cada jogador escolhe os heróis na própria Capitã: no lobby aparece um resumo deles
(nome, classe, raça e o sprite) e, ao marcar "Pronto", vai para o host o "pacote" com os heróis prontos
(Progresso.pacote_para_partida), que só o host guarda.
"""

from rede.protocolo import configuracao, texto_limpo


class JogadorNoLobby:
    def __init__(self, identificador, nome, cor, host=False):
        self.id = identificador
        self.nome = nome
        self.cor = tuple(cor)
        self.host = host
        self.pronto = False
        self.herois = []                 # resumos: {"nome", "classe", "raca", "sprite"}
        self.pacote = None               # (só no host) os heróis prontos para a run

    def para_dict(self):
        return {"id": self.id, "nome": self.nome, "cor": list(self.cor), "host": self.host, "pronto": self.pronto,
                "herois": [dict(h) for h in self.herois]}

    @classmethod
    def de_dict(cls, dados):
        jogador = cls(str(dados.get("id", "?")), texto_limpo(dados.get("nome", "?"), 24), cor_valida(dados.get("cor")),
                      bool(dados.get("host")))
        jogador.pronto = bool(dados.get("pronto"))
        jogador.herois = resumos_validos(dados.get("herois"))
        return jogador


class MensagemDeChat:
    def __init__(self, autor, nome, cor, texto, emote=False, sistema=False):
        self.autor, self.nome, self.cor = autor, nome, tuple(cor)
        self.texto, self.emote, self.sistema = texto, emote, sistema

    def para_dict(self):
        return {"autor": self.autor, "nome": self.nome, "cor": list(self.cor), "texto": self.texto,
                "emote": self.emote, "sistema": self.sistema}

    @classmethod
    def de_dict(cls, dados):
        return cls(str(dados.get("autor", "")), texto_limpo(dados.get("nome", ""), 24), cor_valida(dados.get("cor")),
                   texto_limpo(dados.get("texto", ""), configuracao()["maximo_do_chat"]), bool(dados.get("emote")),
                   bool(dados.get("sistema")))


class Lobby:
    def __init__(self):
        self.jogadores = []
        self.chat = []
        self.falas = 0                   # quantas mensagens já chegaram (o chat guarda só as últimas)

    # ---------------- quem está ----------------
    def jogador(self, identificador):
        return next((j for j in self.jogadores if j.id == identificador), None)

    def host(self):
        return next((j for j in self.jogadores if j.host), None)

    def cheio(self):
        return len(self.jogadores) >= configuracao()["max_jogadores"]

    def cor_livre(self, pedida, menos=None):
        """A cor pedida, se ninguém (fora 'menos') a usa; senão a primeira livre da paleta."""
        usadas = {j.cor for j in self.jogadores if j is not menos}
        pedida = tuple(pedida)
        if pedida not in usadas:
            return pedida
        return next((tuple(c) for c in configuracao()["cores"] if tuple(c) not in usadas), pedida)

    def nome_livre(self, pedido, menos=None):
        """O nome pedido (limpo); repetido, ganha um número ("Bia 2")."""
        base = texto_limpo(pedido, configuracao()["maximo_do_nome"]) or "Jogador"
        usados = {j.nome for j in self.jogadores if j is not menos}
        nome, n = base, 2
        while nome in usados:
            nome, n = f"{base} {n}", n + 1
        return nome

    def entrar(self, identificador, nome, cor, host=False):
        jogador = JogadorNoLobby(identificador, "", (0, 0, 0), host)
        jogador.nome = self.nome_livre(nome)
        jogador.cor = self.cor_livre(cor_valida(cor))
        self.jogadores.append(jogador)
        return jogador

    def sair(self, identificador):
        jogador = self.jogador(identificador)
        if jogador is not None:
            self.jogadores.remove(jogador)
        return jogador

    # ---------------- começar ----------------
    def total_de_herois(self):
        return sum(len(j.herois) for j in self.jogadores)

    def motivo_para_nao_iniciar(self):
        """Por que o host ainda não pode começar (texto) ou None."""
        from roguelike.dados import regras
        maximo = regras()["grupo"]["maximo"]
        if len(self.jogadores) < 2:
            return "Esperando alguém entrar (para jogar sozinho, use o Acampamento)."
        if self.total_de_herois() > maximo:
            return (f"O grupo tem {self.total_de_herois()} heróis e o máximo é {maximo}: alguém precisa levar "
                    "menos (Capitã).")
        faltam = [j.nome for j in self.jogadores if not j.pronto]
        if faltam:
            return "Esperando ficar pronto: " + ", ".join(faltam) + "."
        return None

    # ---------------- chat ----------------
    def falar(self, mensagem):
        self.chat.append(mensagem)
        self.falas += 1
        del self.chat[:-configuracao()["linhas_do_chat"]]

    def ultimas(self, quantas):
        """As últimas 'quantas' mensagens que chegaram (as que ainda estão guardadas)."""
        return self.chat[len(self.chat) - min(len(self.chat), max(0, quantas)):]

    # ---------------- cópia para os clientes ----------------
    def para_dict(self):
        return {"jogadores": [j.para_dict() for j in self.jogadores]}

    def atualizar_de(self, dados):
        """O cliente troca a lista de jogadores pela que o host mandou (o chat continua o daqui)."""
        lista = dados.get("jogadores") if isinstance(dados, dict) else None
        self.jogadores = [JogadorNoLobby.de_dict(j) for j in lista if isinstance(j, dict)] if isinstance(lista, list) else []


def cor_valida(cor):
    """(r, g, b) inteiros de 0 a 255 (qualquer outra coisa vira a primeira cor da paleta)."""
    try:
        r, g, b = (int(c) for c in cor)
        if all(0 <= c <= 255 for c in (r, g, b)):
            return r, g, b
    except (TypeError, ValueError):
        pass
    return tuple(configuracao()["cores"][0])


def resumos_validos(herois):
    """Os resumos dos heróis de um jogador, só com textos curtos (no máximo 5)."""
    if not isinstance(herois, list):
        return []
    validos = []
    for heroi in herois[:5]:
        if isinstance(heroi, dict):
            validos.append({campo: texto_limpo(heroi.get(campo, ""), 200 if campo == "sprite" else 32)
                            for campo in ("nome", "classe", "raca", "sprite")})
    return validos
