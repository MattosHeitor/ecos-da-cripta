"""Eventos do combate.

O combate não desenha nada: cada coisa que acontece vira um Evento.
A tela lê a lista de eventos para tocar animações, números de dano e
mensagens. Os testes também usam os eventos para conferir as regras.
"""


class Evento:
    """Algo que aconteceu no combate.

    tipo: "rodada", "turno", "habilidade", "dano", "esquiva", "cura",
          "status", "status_fim", "energia", "perdeu_vez", "concentrar",
          "morte", "invocacao", "reviver", "item", "fim";
          mecânicas de chefe: "fase_do_chefe", "escudo_quebrou", "aviso";
          ambiente (roguelike/ambiente.py): "ambiente" (a água subiu, a luz revelou alguém...).
    """

    def __init__(self, tipo, origem=None, alvo=None, valor=0, texto="", **extras):
        self.tipo = tipo
        self.origem = origem      # quem causou (Lutador ou None)
        self.alvo = alvo          # quem sofreu (Lutador ou None)
        self.valor = valor        # dano, cura, energia...
        self.texto = texto        # mensagem para o registro de combate
        self.critico = extras.pop("critico", False)
        self.bloqueou = extras.pop("bloqueou", False)
        self.extras = extras      # outros detalhes (nome do status, habilidade...)

    def __repr__(self):
        return f"Evento({self.tipo!r}, {self.texto!r})"
