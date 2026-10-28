"""Conquistas que liberam skins e golpes raros (conquistas.json).

    Conquista (base: nome, descrição, skin e/ou golpe raro que libera)
     ├── ConquistaDeAbates   derrote N inimigos (de uma lista, de uma família ou quaisquer)
     └── ConquistaDeMarco    algo aconteceu: chefe derrotado, região alcançada, vitória

O progresso permanente (Progresso) guarda os abates e os marcos; cada conquista só sabe
dizer quanto já foi feito: progresso(progresso) -> (atual, total).
"""

from roguelike.dados import carregar, sem_comentarios


class Conquista:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.descricao = dados.get("descricao", "")
        self.skin = dados.get("skin")
        self.golpe = dados.get("golpe")            # golpe raro (habilidades.json "raro")

    def progresso(self, progresso):
        """(quanto já foi feito, quanto precisa)."""
        raise NotImplementedError

    def concluida(self, progresso):
        atual, total = self.progresso(progresso)
        return atual >= total

    def texto_do_progresso(self, progresso):
        atual, total = self.progresso(progresso)
        return f"{min(atual, total)}/{total}"


class ConquistaDeAbates(Conquista):
    def __init__(self, chave, dados):
        super().__init__(chave, dados)
        self.inimigos = list(dados.get("inimigos", []))
        self.familia = dados.get("familia")
        self.quantidade = dados["quantidade"]

    def conta(self, chave_inimigo):
        """Este inimigo conta para a conquista?"""
        if self.inimigos:
            return chave_inimigo in self.inimigos
        if self.familia:
            from roguelike.inimigos import fichas
            ficha = fichas().get(chave_inimigo)
            return ficha is not None and ficha.get("familia") == self.familia
        return True

    def progresso(self, progresso):
        return sum(n for chave, n in progresso.abates.items() if self.conta(chave)), self.quantidade


class ConquistaDeMarco(Conquista):
    def __init__(self, chave, dados):
        super().__init__(chave, dados)
        self.marco = dados["marco"]

    def progresso(self, progresso):
        return (1 if self.marco in progresso.conquistas else 0), 1

    def texto_do_progresso(self, progresso):
        return "feito" if self.concluida(progresso) else "a fazer"


TIPOS = {"abates": ConquistaDeAbates, "marco": ConquistaDeMarco}

_conquistas = {}


def todas_as_conquistas():
    if not _conquistas:
        for chave, dados in sem_comentarios(carregar("conquistas")).items():
            _conquistas[chave] = TIPOS[dados["tipo"]](chave, dados)
    return _conquistas


def conquista_da_skin(chave_skin):
    """A conquista que libera esta skin (ou None)."""
    return next((c for c in todas_as_conquistas().values() if c.skin == chave_skin), None)


def conquista_do_golpe(chave_golpe):
    """A conquista que libera este golpe raro (ou None)."""
    return next((c for c in todas_as_conquistas().values() if c.golpe == chave_golpe), None)
