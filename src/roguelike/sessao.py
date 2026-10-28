"""Sessão: por onde as telas mandam comandos e leem o estado. A tela não sabe se o jogo é sozinho ou em rede.

    Sessao
    └── SessaoLocal    um computador só: o comando é executado na hora (no processador desta sessão)
        (MP5: SessaoHost confere e repassa para todos; SessaoCliente manda para o host e espera)

decisores: heróis que não são decididos por uma pessoa nesta tela (número do herói -> Decisor, ex.: DecisorIA para
quem desconectou). Sem decisor, quem comanda o herói escolhe na tela.
"""

from roguelike.posse import JOGADOR_LOCAL
from roguelike.processador import ProcessadorDeComandos


class Sessao:
    def __init__(self, estado, jogador=JOGADOR_LOCAL):
        self.estado = estado
        self.jogador = jogador            # quem está jogando neste computador
        self.decisores = {}

    def enviar(self, comando):
        raise NotImplementedError

    def meu_jogador(self):
        """O Jogador deste computador (dono da mochila e do ouro que a tela mostra). Sem ele no grupo: o primeiro."""
        grupo = self.estado.grupo
        if grupo is None:
            return None
        return grupo.jogador(self.jogador) or grupo.jogadores[0]

    def decisor_de(self, heroi):
        """O Decisor do herói (None = uma pessoa decide na tela)."""
        return self.decisores.get(self.estado.indice_do(heroi))


class SessaoLocal(Sessao):
    """Jogo num computador só: cada comando sai em nome do jogador local e é executado na hora."""

    def __init__(self, estado, jogador=JOGADOR_LOCAL):
        super().__init__(estado, jogador)
        self.processador = ProcessadorDeComandos(estado)

    def enviar(self, comando):
        comando.jogador = self.jogador
        return self.processador.executar(comando)
