"""O estado do jogo que os comandos mudam: a run e o combate em andamento.

Um comando acha tudo aqui por NÚMERO, nunca por objeto: herói 0, 1...; inventário "bau" ou o número do herói
(a mochila dele); lutador ["herois", 2] ou ["inimigos", 0]. Assim o mesmo comando vale em outro computador
(multiplayer) e ao refazer a partida do zero (teste de determinismo).

impressao_digital() resume o estado inteiro num hash: duas máquinas (ou duas vezes a mesma partida) com a mesma
semente e os mesmos comandos têm de chegar à mesma impressão digital.
"""

import hashlib
import json

from roguelike.posse import JOGADOR_LOCAL

BAU = "bau"
LADOS = ("herois", "inimigos")


class EstadoDoJogo:
    def __init__(self, run=None, herois=None):
        self.run = run
        self._herois = list(herois or [])     # sem run (ex.: a tela de golpes num teste), só os heróis
        self.condutor = None                  # o CondutorDoCombate do combate em andamento

    # ---------------- o que há ----------------
    @property
    def grupo(self):
        return self.run.grupo if self.run is not None else None

    @property
    def combate(self):
        return self.condutor.combate if self.condutor is not None else None

    def herois(self):
        return self.run.grupo.herois if self.run is not None else self._herois

    # ---------------- números <-> objetos ----------------
    def heroi(self, indice):
        """O herói com esse número (ou None)."""
        herois = self.herois()
        return herois[indice] if isinstance(indice, int) and 0 <= indice < len(herois) else None

    def indice_do(self, heroi):
        return next(i for i, h in enumerate(self.herois()) if h is heroi)

    def inventario(self, origem):
        """"bau" -> o baú da equipe; um número -> a mochila desse herói (ou None)."""
        if origem == BAU:
            return self.grupo.bau if self.grupo is not None else None
        heroi = self.heroi(origem)
        return heroi.inventario if heroi is not None else None

    def origem_de(self, inventario):
        """O contrário de inventario(): "bau" ou o número do herói dono da mochila."""
        if self.grupo is not None and inventario is self.grupo.bau:
            return BAU
        return next(i for i, h in enumerate(self.herois()) if h.inventario is inventario)

    def lutador(self, referencia):
        """["herois" | "inimigos", número] -> o lutador do combate em andamento (ou None)."""
        if self.combate is None or not referencia:
            return None
        lado, indice = referencia
        lista = self.combate.herois if lado == "herois" else self.combate.inimigos
        return lista[indice] if lado in LADOS and 0 <= indice < len(lista) else None

    def referencia(self, lutador):
        if lutador is None:
            return None
        lista = self.combate.herois if lutador.lado == "herois" else self.combate.inimigos
        return [lutador.lado, next(i for i, l in enumerate(lista) if l is lutador)]

    # ---------------- quem manda ----------------
    def pode_comandar(self, jogador, heroi):
        """O jogador comanda esse herói? (sem run, ou herói sem jogador: só o local)"""
        dono = getattr(heroi, "jogador", None)
        return (dono.id if dono is not None else JOGADOR_LOCAL) == jogador

    # ---------------- combate ----------------
    def comecar_combate(self, encontro=None):
        """Monta o combate do encontro (o da run, se não vier outro) e o condutor que faz ele andar."""
        from roguelike.condutor import CondutorDoCombate
        self.condutor = CondutorDoCombate(self.run, encontro or self.run.encontro)
        return self.condutor

    def avancar_combate(self):
        """Leva o combate em andamento até a próxima decisão de herói (ou até o fim, que dá a recompensa)."""
        condutor = self.condutor
        if condutor is not None and not condutor.terminou() and not condutor.esperando():
            condutor.avancar_ate_decisao()

    # ---------------- impressão digital ----------------
    def impressao_digital(self):
        """Hash do estado inteiro (run + combate em andamento). Igual em todo lugar = estados iguais.

        O que a run só sorteia na primeira consulta (as opções do mapa, o tamanho da fase) é sorteado antes: assim
        não importa se uma tela já desenhou o mapa e a outra não (o sorteio é o mesmo nas duas)."""
        run = self.run
        if run is not None and not run.terminou():
            run.areas_da_regiao()
            if run.estado == "escolha":
                run.opcoes_de_encontro()
        partes = {"run": run.para_dict() if run is not None else None,
                  "combate": resumo_do_combate(self.combate) if self.combate is not None else None}
        texto = json.dumps(partes, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def resumo_do_combate(combate):
    """O que muda num combate, em dados simples (para a impressão digital)."""
    def lutador(l):
        return {"chave": getattr(l, "chave", l.nome), "nome": l.nome, "vida": l.vida, "energia": l.energia,
                "recargas": dict(sorted(l.recargas.items())), "quantos": getattr(l, "quantos", None),
                "status": {c: [s.duracao, s.valor, s.acumulos] for c, s in sorted(l.status.items())}}

    def nome(l):
        return l.nome if l is not None else None

    estado_do_sorteio = hashlib.sha256(repr(combate.rng.getstate()).encode()).hexdigest()
    return {"rodada": combate.rodada, "resultado": combate.resultado, "atual": nome(combate.atual),
            "pode_agir": combate.pode_agir, "fila": [nome(l) for l in combate.fila],
            "herois": [lutador(l) for l in combate.herois], "inimigos": [lutador(l) for l in combate.inimigos],
            "derrotados": [nome(l) for l in combate.derrotados], "sorteio": estado_do_sorteio}
