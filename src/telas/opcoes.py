"""Opções (volume, velocidades, tela cheia, pasta dos saves, apagar o save) e Controles (remapear teclas).

As duas telas recebem 'ao_sair': a função que volta para quem abriu (título, acampamento,
menu do mapa ou pausa do combate). Tudo é salvo na hora em opcoes.json, na pasta do jogador (caminhos.py).
"""

import pygame

from caminhos import CAMINHOS, abrir_pasta, pasta_para_mostrar
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo
from ui import tema
from ui.componentes import ListaSelecionavel, Deslizador, Painel
from ui.controles import ACOES, nome_da_tecla
from ui.desenho import texto, painel
from ui.opcoes import NOMES_VELOCIDADE_DO_TEXTO
from ui.texto import linha as linha_de_texto
from ui.widgets import Botao

TECLAS_FIXAS = {getattr(pygame, f"K_{n}") for n in range(1, 10)}     # números dos menus


class TelaComLista(TelaComBotoes):
    """Base das telas de opções: uma lista de linhas; esquerda/direita mudam o valor da linha."""

    def __init__(self, app, ao_sair, linhas, altura_item=52):
        super().__init__(app)
        self.ao_sair = ao_sair
        self.fundo = Fundo("titulo", escurecer=150)
        self.lista = ListaSelecionavel(linhas, altura_item, ao_escolher=self.ativar, espaco=6)

    def voltar(self):
        self.ao_sair()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def ativar(self, linha):
        """Enter (ou clique) na linha."""

    def mudar(self, linha, passo):
        """Esquerda/direita na linha."""

    def evento(self, e):
        if self.dialogo is None and e.type == pygame.KEYDOWN:
            controles = self.controles
            if controles.eh(e, "esquerda") or controles.eh(e, "direita"):
                self.mudar(self.lista.selecionado, 1 if controles.eh(e, "direita") else -1)
                return
            if controles.eh(e, "cima") or controles.eh(e, "baixo"):
                self.lista.evento(e, controles)
                self.app.audio.tocar("navegar")
                return
            if controles.eh(e, "confirmar"):
                self.app.audio.tocar("clique")
                self.lista.evento(e, controles)
                return
        if e.type == pygame.MOUSEMOTION:
            self.lista.evento(e, self.controles)
        super().evento(e)


class TelaOpcoes(TelaComLista):
    LINHAS = ["musica", "efeitos", "combate", "texto", "tela_cheia", "controles", "pasta", "apagar_save", "voltar"]
    NOMES = {"musica": "Volume da música", "efeitos": "Volume dos efeitos", "combate": "Velocidade do combate",
             "texto": "Velocidade do texto", "tela_cheia": "Tela cheia", "controles": "Controles...",
             "pasta": "Abrir a pasta dos saves", "apagar_save": "Apagar save e começar do zero", "voltar": "Voltar",
             "pets": "Bichos no acampamento"}

    ALTURA_MAXIMA_DA_LINHA = 48

    def __init__(self, app, ao_sair):
        self.linhas = self.linhas_visiveis(app)
        super().__init__(app, ao_sair, self.linhas, altura_item=self.ALTURA_MAXIMA_DA_LINHA)
        self.deslizador = Deslizador()
        self.areas_de_deslizador = {}

    @classmethod
    def linhas_visiveis(cls, app):
        """As linhas de sempre; "pets" só depois de liberar um bicho (o Rato Branco: não entrega o segredo antes)."""
        progresso = getattr(app, "progresso", None)
        if progresso is None or not progresso.pets_liberados():
            return list(cls.LINHAS)
        return cls.LINHAS[:5] + ["pets"] + cls.LINHAS[5:]

    @property
    def opcoes(self):
        return self.app.opcoes

    def salvar(self):
        self.app.salvar_opcoes()

    def mudar(self, linha, passo):
        opcoes = self.opcoes
        if linha in ("musica", "efeitos"):
            opcoes.mudar_volume(linha, passo)
            self.app.audio.atualizar_volumes()
        elif linha == "combate":
            opcoes.proxima_velocidade_combate(passo)
        elif linha == "texto":
            opcoes.proxima_velocidade_texto(passo)
        elif linha == "tela_cheia":
            self.app.alternar_tela_cheia()
        elif linha == "pets":
            opcoes.mostrar_pets = not opcoes.mostrar_pets
        else:
            return
        self.app.audio.tocar("navegar")
        self.salvar()

    def ativar(self, linha):
        if linha == "controles":
            self.app.trocar(TelaControles(self.app, lambda: self.app.trocar(self)))
        elif linha == "pasta":
            if not abrir_pasta(CAMINHOS.jogador):
                self.app.notificar("Pasta dos saves", pasta_para_mostrar(CAMINHOS.jogador), som=None)
        elif linha == "apagar_save":
            self.abrir_dialogo("Apagar save",
                               "Apagar TODO o progresso e começar do zero? Brasas, prestígio, talentos, raças, bênçãos, "
                               "skins, conquistas, bestiário, arsenal e a run em andamento serão perdidos para sempre. "
                               "As opções e as teclas continuam.",
                               [("Apagar tudo", lambda: fluxo.comecar_do_zero(self.app)), ("Cancelar", None)])
        elif linha == "voltar":
            self.voltar()
        else:
            self.mudar(linha, 1)

    def clique_livre(self, posicao):
        for linha, rect in self.areas_de_deslizador.items():
            if rect.inflate(0, 16).collidepoint(posicao):
                setattr(self.opcoes, f"volume_{linha}", Deslizador.valor_no_ponto(rect, posicao[0]))
                self.app.audio.atualizar_volumes()
                self.app.audio.tocar("navegar")
                self.salvar()
                return
        indice = self.lista.item_no_ponto(posicao)
        if indice is not None:
            self.lista.indice = indice
            self.ativar(self.linhas[indice])

    def valor(self, linha):
        opcoes = self.opcoes
        if linha == "combate":
            return f"{opcoes.velocidade_combate:g}x"
        if linha == "texto":
            return NOMES_VELOCIDADE_DO_TEXTO[opcoes.velocidade_texto]
        if linha == "tela_cheia":
            return "Sim" if opcoes.tela_cheia else "Não"
        if linha == "pets":
            return "Mostrar" if opcoes.mostrar_pets else "Esconder"
        if linha == "pasta":
            return pasta_para_mostrar(CAMINHOS.jogador)
        return ""

    def desenhar_linha(self, tela, linha, area, selecionada):
        perigo = linha == "apagar_save"
        painel(tela, area, ("sangue" if perigo else "ouro") if selecionada else "pedra")
        cor = tema.OURO_CLARO if selecionada else (tema.SANGUE_CLARO if perigo else tema.TEXTO)
        texto(tela, self.NOMES[linha], tema.normal(), cor, (area.x + 18, area.centery), "midleft")
        valor_rect = pygame.Rect(area.x + 330, area.y + 8, area.width - 350, area.height - 16)
        if linha in ("musica", "efeitos"):
            barra_rect = pygame.Rect(valor_rect.x, valor_rect.centery - 6, valor_rect.width - 70, 12)
            self.areas_de_deslizador[linha] = barra_rect
            self.deslizador.desenhar(tela, barra_rect, getattr(self.opcoes, f"volume_{linha}"), selecionada)
        elif linha in ("combate", "texto", "tela_cheia", "pets"):
            self.botao(Botao((valor_rect.x, valor_rect.y, 34, valor_rect.height), "<", lambda: self.mudar(linha, -1)))
            self.botao(Botao((valor_rect.right - 34, valor_rect.y, 34, valor_rect.height), ">",
                             lambda: self.mudar(linha, 1)))
            texto(tela, self.valor(linha), tema.normal(), tema.TEXTO, valor_rect.center, "center")
        elif linha == "pasta":
            linha_de_texto(tela, self.valor(linha), tema.pequena(), tema.TEXTO_FRACO, valor_rect.center,
                           valor_rect.width, "center")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        area = Painel((tema.LARGURA // 2 - 380, 68, 760, 640), "pedra", "Opções").desenhar(tela)
        lista = pygame.Rect(area.x + 10, area.y + 14, area.width - 20, area.height - 70)
        espaco = self.lista.espaco                  # todas as linhas cabem sem rolar (com ou sem a dos bichos)
        self.lista.altura_item = min(self.ALTURA_MAXIMA_DA_LINHA, (lista.height + espaco) // len(self.linhas) - espaco)
        self.lista.desenhar(tela, lista, self.desenhar_linha)
        texto(tela, "Cima/baixo: escolher   ·   Esquerda/direita: mudar   ·   Esc: voltar", tema.pequena(),
              tema.TEXTO_FRACO, (tema.LARGURA // 2, area.bottom - 14), "midbottom")
        self.terminar_desenho(tela)


class TelaControles(TelaComLista):
    """Remapear teclas: escolha a ação e a coluna (1ª ou 2ª tecla), aperte Enter e depois a tecla nova."""

    def __init__(self, app, ao_sair):
        super().__init__(app, ao_sair, list(ACOES) + ["restaurar", "voltar"], altura_item=36)
        self.coluna = 0
        self.esperando = None            # ação esperando a tecla nova
        self.mensagem = ""
        self.celulas = {}

    def mudar(self, linha, passo):
        if linha in ACOES:
            self.coluna = (self.coluna + passo) % 2
            self.app.audio.tocar("navegar")

    def ativar(self, linha):
        if linha == "voltar":
            self.voltar()
        elif linha == "restaurar":
            self.abrir_dialogo("Restaurar teclas", "Voltar todas as teclas para o padrão?",
                               [("Restaurar", self.restaurar), ("Cancelar", None)])
        else:
            self.esperando = linha
            self.mensagem = f"Aperte a nova tecla para '{ACOES[linha][0]}' (Esc cancela)"

    def restaurar(self):
        self.app.controles.restaurar_padrao()
        self.app.salvar_opcoes()
        self.mensagem = "Teclas restauradas."

    def evento(self, e):
        if self.esperando is not None:
            if e.type == pygame.KEYDOWN:
                self.capturar(e.key)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for (acao, coluna), rect in self.celulas.items():
                if rect.collidepoint(e.pos):
                    self.coluna = coluna
                    self.lista.indice = self.lista.itens.index(acao)
                    self.ativar(acao)
                    return
        super().evento(e)

    def capturar(self, tecla):
        acao, self.esperando = self.esperando, None
        if tecla == pygame.K_ESCAPE:
            self.mensagem = "Cancelado."
        elif tecla in TECLAS_FIXAS:
            self.mensagem = "As teclas 1 a 9 são fixas dos menus."
        else:
            self.app.controles.remapear(acao, tecla, self.coluna)
            self.app.salvar_opcoes()
            self.mensagem = f"{ACOES[acao][0]}: {self.app.controles.texto_da_acao(acao)}"
            self.app.audio.tocar("clique")

    def desenhar_linha(self, tela, linha, area, selecionada):
        painel(tela, area, "ouro" if selecionada else "pedra")
        cor = tema.OURO_CLARO if selecionada else tema.TEXTO
        if linha not in ACOES:
            nome = "Restaurar padrão" if linha == "restaurar" else "Voltar"
            texto(tela, nome, tema.normal(), cor, area.center, "center")
            return
        texto(tela, ACOES[linha][0], tema.pequena(), cor, (area.x + 16, area.centery), "midleft")
        teclas = self.app.controles.teclas[linha]
        for coluna in range(2):
            rect = pygame.Rect(area.x + 360 + coluna * 170, area.y + 4, 160, area.height - 8)
            self.celulas[(linha, coluna)] = rect
            marcada = selecionada and coluna == self.coluna
            esperando = marcada and self.esperando == linha
            painel(tela, rect, "sangue" if esperando else ("ouro" if marcada else "ferro"))
            nome = "..." if esperando else (nome_da_tecla(teclas[coluna]) if coluna < len(teclas) else "—")
            texto(tela, nome, tema.pequena(), tema.TEXTO, rect.center, "center")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        area = Painel((tema.LARGURA // 2 - 380, 20, 760, 680), "pedra", "Controles").desenhar(tela)
        self.celulas = {}
        texto(tela, "Tecla 1", tema.mini(), tema.TEXTO_FRACO, (area.x + 10 + 360 + 80, area.y + 2), "midtop")
        texto(tela, "Tecla 2", tema.mini(), tema.TEXTO_FRACO, (area.x + 10 + 530 + 80, area.y + 2), "midtop")
        self.lista.desenhar(tela, pygame.Rect(area.x + 10, area.y + 20, area.width - 30, area.height - 70),
                            self.desenhar_linha)
        mensagem = self.mensagem or "Enter na tecla para trocar · esquerda/direita escolhe a coluna"
        texto(tela, mensagem, tema.pequena(), tema.OURO_CLARO if self.mensagem else tema.TEXTO_FRACO,
              (tema.LARGURA // 2, area.bottom - 12), "midbottom")
        self.terminar_desenho(tela)
