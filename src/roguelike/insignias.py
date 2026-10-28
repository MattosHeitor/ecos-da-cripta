"""Insígnias: as conquistas e os níveis de prestígio do jogador (quadro do acampamento).

    insignias_de_conquista(progresso)   -> [InsigniaDeConquista]  (feita ou não, com o progresso)
    prestigio_das_classes(progresso)    -> [PrestigioDaClasse]    (nível, XP e o próximo marco)
"""

from roguelike.classes import todas_as_classes
from roguelike.conquistas import todas_as_conquistas
from roguelike.dados import regras


class InsigniaDeConquista:
    def __init__(self, conquista, progresso):
        self.conquista = conquista
        self.feita = conquista.chave in progresso.conquistas_feitas
        self.texto_do_progresso = "feita" if self.feita else conquista.texto_do_progresso(progresso)

    @property
    def premio(self):
        """O que ela libera: "Skin: Auréola", "Golpe raro: Réquiem" ou os dois ("Chapéu de Flautista + golpe raro")."""
        from roguelike.golpes import golpe
        from roguelike.skins import skin
        if self.conquista.skin and self.conquista.golpe:
            return f"{skin(self.conquista.skin).nome} + golpe raro"
        if self.conquista.skin:
            return f"Skin: {skin(self.conquista.skin).nome}"
        if self.conquista.golpe:
            return f"Golpe raro: {golpe(self.conquista.golpe).nome}"
        return ""


class PrestigioDaClasse:
    """Onde a classe está no prestígio e o que vem a seguir (subclasses nos níveis 3 e 6)."""

    def __init__(self, classe, progresso):
        self.classe = classe
        self.nivel = progresso.nivel_de_prestigio(classe.chave)
        self.maximo = regras()["progresso"]["prestigio_maximo"]
        self.xp = progresso.xp_de_prestigio(classe.chave)
        self.precisa = progresso.xp_para_proximo_prestigio(classe.chave)
        proximas = sorted((s for s in classe.subclasses.values() if s.prestigio > self.nivel), key=lambda s: s.prestigio)
        self.proxima_subclasse = proximas[0] if proximas else None

    @property
    def no_maximo(self):
        return self.nivel >= self.maximo

    def fracao(self):
        return 1.0 if self.no_maximo else min(1.0, self.xp / max(1, self.precisa))

    def texto_curto(self):
        """Para o painel do acampamento: "Caminho do Espírito (pr. 3)"."""
        if self.no_maximo:
            return "máximo"
        if self.proxima_subclasse is not None:
            return f"{self.proxima_subclasse.nome} (pr. {self.proxima_subclasse.prestigio})"
        return f"pr. {self.nivel + 1}: mais talentos"

    def texto_do_proximo(self):
        if self.no_maximo:
            return "prestígio máximo"
        if self.proxima_subclasse is not None:
            return f"{self.proxima_subclasse.nome} no prestígio {self.proxima_subclasse.prestigio}"
        return f"prestígio {self.nivel + 1}: +{regras()['progresso']['pontos_por_prestigio']} pontos de talento"


def insignias_de_conquista(progresso):
    return [InsigniaDeConquista(c, progresso) for c in todas_as_conquistas().values()]


def prestigio_das_classes(progresso, chaves=None):
    classes = todas_as_classes()
    chaves = chaves or list(progresso.classes_liberadas())          # (as secretas só depois de liberadas)
    return [PrestigioDaClasse(classes[c], progresso) for c in chaves]
