"""Catálogo do Mestre do Grimório: todos os golpes que cada classe PODE ter e de onde vêm.

Só mostra; trocar golpes continua sendo durante a run (tela de golpes). Um golpe que nenhum
herói teve ainda numa run aparece como "???" (progresso.golpes_descobertos).

    secoes_da_classe("monge") -> [Secao("Classe", [Entrada...]), Secao("Punho de Ferro", ...), ...]
"""

from roguelike.classes import todas_as_classes
from roguelike.conquistas import conquista_do_golpe
from roguelike.golpes import golpe, todas_as_chaves


class Entrada:
    """Um golpe do catálogo e como ele é aprendido."""

    def __init__(self, chave, origem, detalhe=None):
        self.chave = chave
        self.origem = origem                 # curto, para o cartão: "Golpe inicial", "Cavaleiro, nível 4"
        self.detalhe = detalhe or origem     # completo, para o painel: "Evolução de Bola de Fogo (virar ...)"

    @property
    def golpe(self):
        return golpe(self.chave)

    def descoberta(self, progresso):
        return progresso.golpe_descoberto(self.chave)

    def __repr__(self):
        return f"Entrada({self.chave!r})"


class Secao:
    def __init__(self, chave, nome, entradas):
        self.chave = chave
        self.nome = nome
        self.entradas = entradas

    def descobertas(self, progresso):
        return sum(1 for e in self.entradas if e.descoberta(progresso))


def _evolucoes_de(chaves):
    """Golpes aprimorados a partir de 'chaves' (seguindo a cadeia de evoluções)."""
    entradas, fila = [], list(chaves)
    vistos = set(chaves)
    while fila:
        origem = golpe(fila.pop(0))
        novo = origem.evolucao_para
        if novo and novo not in vistos:
            vistos.add(novo)
            fila.append(novo)
            requisito = origem.texto_do_requisito()
            entradas.append(Entrada(novo, f"Evolui de {origem.nome}",
                                    f"Evolução de {origem.nome}" + (f": {requisito}" if requisito else "")))
    return entradas


def secoes_da_classe(chave_classe):
    classe = todas_as_classes()[chave_classe]
    secoes = []
    entradas = [Entrada(c, "Golpe inicial") for c in classe.habilidades]
    entradas += [Entrada(c, f"Nível {n} (qualquer caminho)") for n, c in sorted(classe.golpes_por_nivel.items())]
    secoes.append(Secao("classe", classe.nome, entradas))
    proprios = [e.chave for e in entradas]
    for sub in classe.subclasses.values():
        lista = [Entrada(c, f"{sub.nome}, nível {n}") for c, n in zip(sub.golpes, sub.niveis_golpes)]
        for esp in sub.especializacoes.values():
            detalhe = f"Especialização {esp.nome} (com o treinador, a partir do nível {esp.nivel_minimo})"
            lista += [Entrada(c, esp.nome, detalhe) for c in esp.golpes]
        secoes.append(Secao(sub.chave, sub.nome, lista))
        proprios += [e.chave for e in lista]
    evolucoes = _evolucoes_de(proprios)
    if evolucoes:
        secoes.append(Secao("evolucoes", "Evoluções", evolucoes))
    raros = []
    for chave in todas_as_chaves():
        g = golpe(chave)
        if g.raro and chave_classe in g.classes_do_raro:
            conquista = conquista_do_golpe(chave)
            nome = conquista.nome if conquista else "?"
            raros.append(Entrada(chave, f"Raro · {nome}",
                                 f"Golpe raro: liberado pela conquista {nome}; na run, chega no nível {g.nivel_do_raro}"))
    if raros:
        secoes.append(Secao("raros", "Raros", raros))
    return secoes


def total_da_classe(chave_classe, progresso):
    """(golpes descobertos, total) da classe."""
    entradas = {e.chave for s in secoes_da_classe(chave_classe) for e in s.entradas}
    return sum(1 for c in entradas if progresso.golpe_descoberto(c)), len(entradas)
