"""Posse: quem joga, a mochila e o ouro de cada um e o baú que a equipe divide.

    Jogador            uma pessoa jogando (no solo, uma só: "local"); comanda 1 ou mais heróis do grupo e tem
                       a SUA mochila (50 pilhas, que os heróis dele dividem) e o SEU ouro
    InventarioPessoal  a mochila de um jogador: só ele põe e tira dela
    BauDaEquipe        o baú do grupo, sem limite: qualquer jogador COLOCA (da mochila dele) e RETIRA (para a
                       mochila dele); cada movimento fica no registro (quem, com qual herói, o quê, quanto)
    Movimento          uma linha do registro

Passar um item para outro jogador = colocar no baú + o outro retirar. A regra de quem pode retirar fica num
lugar só (BauDaEquipe.pode_retirar). O arsenal do acampamento é outra coisa: guarda o que foi ganho depois da run.
"""

from roguelike.dados import regras
from roguelike.inventario import Inventario

MAXIMO_DO_REGISTRO = 60
JOGADOR_LOCAL = "local"            # o id de quem joga sozinho (e o padrão dos comandos)


def capacidade_da_mochila():
    """Pilhas da mochila de um jogador (regras.json "inventario")."""
    return regras()["inventario"]["pilhas_por_jogador"]


class Jogador:
    """Uma pessoa jogando: id (único na partida), nome, cor, a mochila dela e o ouro dela."""

    def __init__(self, identificador, nome, cor=None, ouro=0):
        self.id = identificador
        self.nome = nome
        self.cor = tuple(cor) if cor else None
        self.ouro = ouro
        self.mochila = InventarioPessoal(capacidade_da_mochila(), dono=self)

    def __eq__(self, outro):
        return isinstance(outro, Jogador) and outro.id == self.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Jogador({self.id!r}, {self.nome!r})"

    def para_dict(self):
        return {"id": self.id, "nome": self.nome, "cor": list(self.cor) if self.cor else None, "ouro": self.ouro,
                "mochila": dict(self.mochila.itens)}

    @classmethod
    def de_dict(cls, dados):
        jogador = cls(dados["id"], dados["nome"], dados.get("cor"), dados.get("ouro", 0))
        jogador.mochila.itens = dict(dados.get("mochila", {}))
        return jogador


def jogador_local():
    """O jogador de quem joga sozinho."""
    return Jogador(JOGADOR_LOCAL, "Você")


class Movimento:
    """Uma linha do registro do baú: qual jogador, com qual herói, colocou ou retirou o quê."""

    def __init__(self, jogador, acao, chave, quantidade, heroi=None):
        self.jogador = jogador
        self.acao = acao                       # "colocar" ou "retirar"
        self.chave = chave
        self.quantidade = quantidade
        self.heroi = heroi                     # nome do herói que fez (None = não se sabe)

    def __repr__(self):
        return f"Movimento({self.jogador.nome}, {self.heroi}, {self.acao}, {self.chave} x{self.quantidade})"

    def para_dict(self):
        return {"jogador": self.jogador.id, "acao": self.acao, "chave": self.chave, "quantidade": self.quantidade,
                "heroi": self.heroi}


class InventarioPessoal(Inventario):
    """A mochila de um jogador (com limite de pilhas). 'dono' é o Jogador; só ele mexe nela."""

    def __init__(self, capacidade=None, dono=None):
        super().__init__(capacidade)
        self.dono = dono

    def eh_de(self, jogador):
        return self.dono is None or self.dono == jogador

    def cheia(self):
        return self.capacidade is not None and len(self.itens) >= self.capacidade


class BauDaEquipe(Inventario):
    """O baú que o grupo divide (sem limite). Qualquer jogador coloca e retira; tudo fica registrado."""

    def __init__(self, capacidade=None):
        super().__init__(capacidade)
        self.registro = []

    # ---------------- regras ----------------
    def pode_retirar(self, jogador, chave, quantidade=1):
        """Quem pode pegar o quê (hoje: qualquer jogador, qualquer item que esteja aqui)."""
        return self.tem(chave, quantidade)

    def _anotar(self, jogador, acao, chave, quantidade, heroi):
        self.registro.append(Movimento(jogador, acao, chave, quantidade, heroi))
        del self.registro[:-MAXIMO_DO_REGISTRO]

    # ---------------- operações ----------------
    def colocar(self, jogador, origem, chave, quantidade=1, heroi=None):
        """O jogador põe no baú itens da mochila DELE. Devolve True se deu certo."""
        if isinstance(origem, InventarioPessoal) and not origem.eh_de(jogador):
            return False
        if not origem.tem(chave, quantidade) or not self.cabe(chave):
            return False
        origem.remover(chave, quantidade)
        self.adicionar(chave, quantidade)
        self._anotar(jogador, "colocar", chave, quantidade, heroi)
        return True

    def retirar(self, jogador, destino, chave, quantidade=1, heroi=None):
        """O jogador pega do baú para a mochila DELE. Devolve True se deu certo."""
        if isinstance(destino, InventarioPessoal) and not destino.eh_de(jogador):
            return False
        if not self.pode_retirar(jogador, chave, quantidade) or not destino.cabe(chave):
            return False
        self.remover(chave, quantidade)
        destino.adicionar(chave, quantidade)
        self._anotar(jogador, "retirar", chave, quantidade, heroi)
        return True

    def passar(self, de, origem, para, destino, chave, quantidade=1):
        """Um jogador passa itens para outro: coloca no baú e o outro retira. Só faz se as duas partes couberem."""
        if not destino.cabe(chave) or not origem.tem(chave, quantidade):
            return False
        if not self.colocar(de, origem, chave, quantidade):
            return False
        if self.retirar(para, destino, chave, quantidade):
            return True
        self.retirar(de, origem, chave, quantidade)          # não coube (não deveria acontecer): desfaz
        return False

    # ---------------- salvar ----------------
    def registro_para_dict(self):
        return [m.para_dict() for m in self.registro]

    def carregar_registro(self, dados, jogadores):
        """Volta o registro salvo (os jogadores pelo id; quem saiu da partida vira um Jogador só com o id)."""
        por_id = {j.id: j for j in jogadores}
        self.registro = [Movimento(por_id.get(d["jogador"]) or Jogador(d["jogador"], d["jogador"]), d["acao"],
                                   d["chave"], d["quantidade"], d.get("heroi")) for d in dados or []]

    @classmethod
    def a_partir_de(cls, inventario):
        bau = cls(inventario.capacidade)
        bau.itens = dict(inventario.itens)
        return bau
