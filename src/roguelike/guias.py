"""Guias: um bicho que aparece no mapa e, seguido várias vezes (contando todas as runs), abre uma passagem secreta.

É o mesmo mecanismo das passagens do Circo ("entradas" no regioes.json), com um passo a mais: a entrada
diz "guia": "rato_branco" e, até o segredo estar completo, a carta do mapa é um evento do guia em vez da
passagem. Cada evento seguido soma 1 ao segredo (consequência "segredo"), que fica no progresso.

    passos = ["rato_branco_esconderijo", "rato_branco_bueiro"]
    segredo 0 -> evento do 1º passo · segredo 1 -> evento do 2º passo · segredo 2 -> a passagem (selada até a fase existir)
"""

from roguelike.dados import carregar, sem_comentarios


class Guia:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]                  # título da carta enquanto ele só aparece
        self.descricao = dados.get("descricao", "")
        self.sprite = dados["sprite"]              # quem corre ao fundo do mapa e do evento
        self.passos = list(dados["passos"])        # eventos (eventos.json, com "so_por_guia")
        self.descoberta = dados.get("descoberta", "")   # aviso quando o último passo é dado

    def passo(self, segredos):
        """Quantas vezes já foi seguido (0, 1, ...)."""
        return segredos.get(self.chave, 0)

    def completo(self, segredos):
        """Todos os passos feitos: a passagem foi descoberta."""
        return self.passo(segredos) >= len(self.passos)

    def evento_da_vez(self, segredos):
        """O evento do próximo passo, ou None se o segredo já está completo."""
        passo = self.passo(segredos)
        return self.passos[passo] if passo < len(self.passos) else None

    def encontro(self, run, destino):
        """A carta do mapa: o evento da vez ou, com o segredo completo, a passagem. None = não aparece nesta área."""
        from roguelike.encontros import EncontroEntrada, EncontroEvento
        chave_evento = self.evento_da_vez(run.segredos)
        if chave_evento is None:
            encontro = EncontroEntrada(destino)
        elif chave_evento in run.eventos_vistos:            # já apareceu nesta run (e o grupo não seguiu)
            return None
        else:
            encontro = EncontroEvento(chave_evento)
            encontro.nome, encontro.descricao = self.nome, self.descricao
        encontro.guia = self.chave
        return encontro

    def __repr__(self):
        return f"Guia({self.chave!r})"


_guias = {}


def todos_os_guias():
    if not _guias:
        for chave, dados in sem_comentarios(carregar("regioes").get("guias", {})).items():
            _guias[chave] = Guia(chave, dados)
    return _guias


def guia(chave):
    return todos_os_guias()[chave]
