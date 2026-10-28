"""Opções do jogador (volume, velocidades, tela cheia, teclas), salvas em opcoes.json na pasta do jogador.

Ficam separadas do progresso (Brasas, conquistas) e da run: apagar o progresso não mexe nelas.
"""

import json

from caminhos import CAMINHOS, gravar_json
from ui.controles import Controles

ARQUIVO_DAS_OPCOES = "opcoes.json"

VELOCIDADES_DO_COMBATE = [1.0, 1.5, 2.0, 3.0]
# letras por segundo nos textos que "vão aparecendo" (eventos, falas); None = tudo de uma vez
VELOCIDADES_DO_TEXTO = {"lento": 30, "normal": 60, "rapido": 140, "instantaneo": None}
NOMES_VELOCIDADE_DO_TEXTO = {"lento": "Lento", "normal": "Normal", "rapido": "Rápido", "instantaneo": "Instantâneo"}


def limitar(valor, minimo=0.0, maximo=1.0):
    return max(minimo, min(maximo, valor))


class Opcoes:
    caminho = None                       # None = opcoes.json na pasta do jogador (as prévias trocam)

    def __init__(self):
        self.volume_musica = 0.6
        self.volume_efeitos = 0.8
        self.velocidade_combate = 1.0
        self.velocidade_texto = "normal"
        self.tela_cheia = False
        self.registro_aberto = True      # registro do combate aberto ou recolhido (tecla L)
        self.mostrar_pets = True         # o Rato Branco (e outros bichos liberados) no acampamento
        self.nome_do_jogador = ""        # partidas em grupo: o nome e a cor que os outros veem
        self.cor_do_jogador = 0          # (índice em regras.json multiplayer.cores)
        self.ultimo_endereco = ""        # o último código/IP digitado para entrar numa partida
        self.lobby_recolhido = {"jogadores": False, "conversa": False}   # painéis do lobby minimizados
        self.volta = None                # {"chave", "id_da_partida"}: voltar à última partida em grupo (MP8)
        self.avisou_firewall = False     # o aviso do firewall do Windows antes de hospedar a 1ª vez
        self.controles = Controles()

    # ---------------- mudanças (já validadas) ----------------
    def mudar_volume(self, qual, passo):
        """qual: "musica" ou "efeitos"; passo em décimos (ex.: +1 = +10%)."""
        atributo = f"volume_{qual}"
        setattr(self, atributo, round(limitar(getattr(self, atributo) + passo * 0.1), 2))

    def proxima_velocidade_combate(self, passo=1):
        lista = VELOCIDADES_DO_COMBATE
        atual = min(range(len(lista)), key=lambda i: abs(lista[i] - self.velocidade_combate))
        self.velocidade_combate = lista[(atual + passo) % len(lista)]

    def proxima_velocidade_texto(self, passo=1):
        lista = list(VELOCIDADES_DO_TEXTO)
        self.velocidade_texto = lista[(lista.index(self.velocidade_texto) + passo) % len(lista)]

    def letras_por_segundo(self):
        return VELOCIDADES_DO_TEXTO[self.velocidade_texto]

    # ---------------- salvar e carregar ----------------
    def para_dict(self):
        return {"volume_musica": self.volume_musica, "volume_efeitos": self.volume_efeitos,
                "velocidade_combate": self.velocidade_combate, "velocidade_texto": self.velocidade_texto,
                "tela_cheia": self.tela_cheia, "registro_aberto": self.registro_aberto,
                "mostrar_pets": self.mostrar_pets, "nome_do_jogador": self.nome_do_jogador,
                "cor_do_jogador": self.cor_do_jogador, "ultimo_endereco": self.ultimo_endereco,
                "lobby_recolhido": dict(self.lobby_recolhido), "volta": self.volta,
                "avisou_firewall": self.avisou_firewall, "teclas": self.controles.para_dict()}

    @classmethod
    def de_dict(cls, dados):
        opcoes = cls()
        opcoes.volume_musica = limitar(float(dados.get("volume_musica", opcoes.volume_musica)))
        opcoes.volume_efeitos = limitar(float(dados.get("volume_efeitos", opcoes.volume_efeitos)))
        velocidade = float(dados.get("velocidade_combate", 1.0))
        opcoes.velocidade_combate = velocidade if velocidade in VELOCIDADES_DO_COMBATE else 1.0
        texto = dados.get("velocidade_texto", "normal")
        opcoes.velocidade_texto = texto if texto in VELOCIDADES_DO_TEXTO else "normal"
        opcoes.tela_cheia = bool(dados.get("tela_cheia", False))
        opcoes.registro_aberto = bool(dados.get("registro_aberto", True))
        opcoes.mostrar_pets = bool(dados.get("mostrar_pets", True))
        opcoes.nome_do_jogador = str(dados.get("nome_do_jogador", ""))[:24]
        cor = dados.get("cor_do_jogador", 0)
        opcoes.cor_do_jogador = cor if isinstance(cor, int) and cor >= 0 else 0
        opcoes.ultimo_endereco = str(dados.get("ultimo_endereco", ""))[:40]
        recolhido = dados.get("lobby_recolhido") if isinstance(dados.get("lobby_recolhido"), dict) else {}
        opcoes.lobby_recolhido = {p: bool(recolhido.get(p, False)) for p in ("jogadores", "conversa")}
        volta = dados.get("volta")
        if isinstance(volta, dict) and isinstance(volta.get("chave"), str):
            opcoes.volta = {"chave": volta["chave"][:64], "id_da_partida": str(volta.get("id_da_partida", ""))[:32]}
        opcoes.avisou_firewall = bool(dados.get("avisou_firewall", False))
        opcoes.controles = Controles(dados.get("teclas"))
        return opcoes

    @classmethod
    def onde(cls):
        return cls.caminho or CAMINHOS.save(ARQUIVO_DAS_OPCOES)

    def salvar(self, caminho=None):
        gravar_json(caminho or self.onde(), self.para_dict())

    @classmethod
    def carregar(cls, caminho=None):
        """Sem arquivo (ou arquivo estragado), começa com as opções padrão."""
        caminho = caminho or cls.onde()
        try:
            with open(caminho, encoding="utf-8") as arquivo:
                return cls.de_dict(json.load(arquivo))
        except (OSError, ValueError, TypeError):
            return cls()
