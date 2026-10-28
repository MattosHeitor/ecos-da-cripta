"""Controles: liga AÇÕES do jogo ("confirmar", "cima"...) a TECLAS, e deixa o jogador remapear.

As telas perguntam pela ação, nunca pela tecla:

    if app.controles.eh(evento, "confirmar"): ...

Cada ação tem até 2 teclas (ex.: seta para cima e W). As teclas de número (1–9) dos menus
são fixas e não entram aqui.
"""

import pygame

# ação -> (nome mostrado na tela de controles, teclas padrão)
ACOES = {
    "cima": ("Cima", [pygame.K_UP, pygame.K_w]),
    "baixo": ("Baixo", [pygame.K_DOWN, pygame.K_s]),
    "esquerda": ("Esquerda", [pygame.K_LEFT, pygame.K_a]),
    "direita": ("Direita", [pygame.K_RIGHT, pygame.K_d]),
    "confirmar": ("Confirmar", [pygame.K_RETURN, pygame.K_KP_ENTER]),
    "voltar": ("Voltar / pausa", [pygame.K_ESCAPE]),
    "grupo": ("Abrir o grupo", [pygame.K_g]),
    "bau": ("Abrir o baú", [pygame.K_b]),
    "inventario": ("Abrir o inventário", [pygame.K_i]),
    "fabricar": ("Abrir a fabricação", [pygame.K_f]),
    "proximo_heroi": ("Próximo herói", [pygame.K_TAB]),
    "velocidade": ("Velocidade do combate", [pygame.K_v]),
    "acelerar": ("Acelerar animações (segurar)", [pygame.K_SPACE]),
    "registro": ("Mostrar/ocultar registro", [pygame.K_l]),
    "tela_cheia": ("Tela cheia", [pygame.K_F11]),
}
MAXIMO_DE_TECLAS = 2
DIRECOES = {"cima": (0, -1), "baixo": (0, 1), "esquerda": (-1, 0), "direita": (1, 0)}


def nome_da_tecla(tecla):
    """Nome curto e legível de uma tecla (ex.: "Enter", "Seta cima", "W")."""
    especiais = {pygame.K_UP: "Seta cima", pygame.K_DOWN: "Seta baixo", pygame.K_LEFT: "Seta esq.",
                 pygame.K_RIGHT: "Seta dir.", pygame.K_RETURN: "Enter", pygame.K_KP_ENTER: "Enter (num)",
                 pygame.K_ESCAPE: "Esc", pygame.K_SPACE: "Espaço", pygame.K_TAB: "Tab",
                 pygame.K_BACKSPACE: "Apagar"}
    if tecla in especiais:
        return especiais[tecla]
    nome = pygame.key.name(tecla)
    return nome.upper() if len(nome) == 1 else nome.capitalize()


class Controles:
    def __init__(self, teclas=None):
        """teclas: {ação: [códigos]} salvos nas opções (o que faltar usa o padrão)."""
        self.teclas = {acao: list(padrao) for acao, (_, padrao) in ACOES.items()}
        for acao, lista in (teclas or {}).items():
            if acao in self.teclas:
                self.teclas[acao] = [int(t) for t in lista][:MAXIMO_DE_TECLAS]

    def acoes_da_tecla(self, tecla):
        return [acao for acao, lista in self.teclas.items() if tecla in lista]

    def eh(self, evento, acao):
        """O evento é um aperto de tecla ligado a esta ação?"""
        return evento.type == pygame.KEYDOWN and evento.key in self.teclas[acao]

    def segurando(self, acao):
        """Alguma tecla da ação está pressionada agora (para "segurar para acelerar")."""
        apertadas = pygame.key.get_pressed()
        return any(tecla < len(apertadas) and apertadas[tecla] for tecla in self.teclas[acao])

    def direcao(self, evento):
        """(dx, dy) se o evento for uma tecla de direção, senão None."""
        for acao, vetor in DIRECOES.items():
            if self.eh(evento, acao):
                return vetor
        return None

    def remapear(self, acao, tecla, posicao=0):
        """Põe a tecla na ação. Se outra ação usava essa tecla, ela recebe a tecla antiga (troca)."""
        lista = self.teclas[acao]
        if tecla in lista:                     # a tecla já é desta ação: só troca de posição
            i = lista.index(tecla)
            if posicao < len(lista):
                lista[i], lista[posicao] = lista[posicao], lista[i]
            return
        antiga = lista[posicao] if posicao < len(lista) else None
        for outra, teclas in self.teclas.items():
            if outra != acao and tecla in teclas:
                indice = teclas.index(tecla)
                if antiga is not None and antiga not in teclas:
                    teclas[indice] = antiga
                else:
                    teclas.pop(indice)
        if posicao < len(lista):
            lista[posicao] = tecla
        else:
            lista.append(tecla)
        del lista[MAXIMO_DE_TECLAS:]

    def restaurar_padrao(self):
        self.teclas = {acao: list(padrao) for acao, (_, padrao) in ACOES.items()}

    def texto_da_acao(self, acao):
        return " / ".join(nome_da_tecla(t) for t in self.teclas[acao]) or "—"

    def para_dict(self):
        return {acao: list(lista) for acao, lista in self.teclas.items()}
