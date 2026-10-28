"""Ferramentas para os testes do roguelike (sem tela)."""

from roguelike.combate import Combate


class SorteControlado:
    """Substitui o random.Random nos testes para o resultado ser sempre o mesmo.

    - random(): usa os valores da lista "sorteios" e depois devolve "padrao"
      (0.99 = nada de esquiva, crítico, bloqueio ou chance acontece);
    - randint(a, b): devolve sempre o máximo (ou o mínimo, se minimo=True);
    - choice/choices: o primeiro da lista.
    """

    def __init__(self, sorteios=(), padrao=0.99, minimo=False):
        self.sorteios = list(sorteios)
        self.padrao = padrao
        self.minimo = minimo

    def random(self):
        return self.sorteios.pop(0) if self.sorteios else self.padrao

    def randint(self, a, b):
        return a if self.minimo else b

    def choice(self, lista):
        return lista[0]

    def choices(self, lista, weights=None, k=1):
        return [lista[0]] * k

    def sample(self, lista, k):
        return list(lista)[:k]

    def shuffle(self, lista):
        pass


def combate_pronto(herois, inimigos, rng=None, ajustar_grupo=False):
    """Cria e inicia um combate (sem o ajuste de grupo, para os números ficarem simples)."""
    combate = Combate(herois, inimigos, rng or SorteControlado(), ajustar_grupo=ajustar_grupo)
    combate.iniciar()
    return combate


def vez_de(combate, lutador):
    """Avança os turnos até chegar a vez de 'lutador' (os outros só se concentram)."""
    for _ in range(50):
        atual = combate.comecar_turno()
        if atual is lutador and combate.pode_agir:
            return
        if combate.pode_agir:
            combate.concentrar(atual)
    raise AssertionError(f"A vez de {lutador.nome} não chegou")
