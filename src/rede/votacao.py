"""Votação de uma partida em grupo: o caminho no mapa, a opção de um evento, continuar ou fugir das ondas e o
"todos prontos para seguir" (recompensas, loja, serviços: uma opção só).

    votacao = Votacao("caminho|floresta|3|0", opcoes=[0, 1, 2], prazo=40)
    votacao.votar("j2", 1)
    votacao.decidida(eleitores)     # todos votaram ou o tempo acabou?
    votacao.vencedora()             # a mais votada; empate (ou ninguém votou): sorteio

A chave diz de qual tela é a votação (sai do estado da run: igual em todo computador). Só o host decide; o
sorteio do empate sai da própria chave (o mesmo empate dá o mesmo resultado se a partida for refeita).
"""

import random
import time


class Votacao:
    def __init__(self, chave, opcoes, prazo, votos=None):
        self.chave = chave
        self.opcoes = list(opcoes)
        self.prazo = prazo
        self.inicio = time.monotonic()
        self.votos = {}                         # id do jogador -> opção
        self.ao_decidir = None                  # (só no host) o que fazer com a opção vencedora
        for jogador, opcao in (votos or {}).items():
            self.votar(jogador, opcao)

    def votar(self, jogador, opcao):
        """Vale o último voto de cada um; opção que não existe não conta. Devolve True se contou."""
        if opcao not in self.opcoes:
            return False
        self.votos[jogador] = opcao
        return True

    def restante(self):
        return max(0.0, self.prazo - (time.monotonic() - self.inicio))

    def faltam(self, eleitores):
        """Quem ainda não votou."""
        return [e for e in eleitores if e not in self.votos]

    def decidida(self, eleitores):
        return not self.faltam(eleitores) or self.restante() <= 0

    def vencedora(self):
        contagem = {}
        for opcao in self.votos.values():
            if opcao in self.opcoes:
                contagem[opcao] = contagem.get(opcao, 0) + 1
        sorteio = random.Random(f"voto|{self.chave}")
        if not contagem:
            return sorteio.choice(self.opcoes)
        maximo = max(contagem.values())
        empatadas = sorted(o for o, n in contagem.items() if n == maximo)
        return empatadas[0] if len(empatadas) == 1 else sorteio.choice(empatadas)

    def para_dict(self):
        return {"chave": self.chave, "opcoes": list(self.opcoes), "votos": dict(self.votos),
                "restante": round(self.restante(), 1)}
