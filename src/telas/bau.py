"""Baú do acampamento: as roupas, chapéus e encantamentos guardados de cada classe.

Escolha a classe e troque as skins na tela de Visual (a mesma de sempre). As skins de conquista
se liberam jogando; as raras são compradas na vitrine do Taverneiro.
"""

import pygame

from roguelike.classes import todas_as_classes
from roguelike.skins import CAMADAS, skins_para, skin, nome_do_sprite
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_do_acampamento, desenhar_npc
from ui import tema
from ui.desenho import texto
from ui.texto import linha
from ui.widgets import Botao

COLUNAS = 6                                   # 2 fileiras = 12 classes (com as secretas)
LARGURA, ALTURA = 199, 270


class TelaBau(TelaComBotoes):
    def __init__(self, app, classe=None):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=150)
        self.classe = classe if classe in todas_as_classes() else None

    def musica(self):
        return "acampamento"

    @property
    def progresso(self):
        return self.app.progresso

    def voltar(self):
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def abrir(self, chave):
        from telas.visual_heroi import TelaVisual
        self.app.trocar(TelaVisual(self.app, chave, None, lambda: self.app.trocar(TelaBau(self.app, chave))))

    def contagem(self, chave):
        """(skins liberadas, total) da classe."""
        todas = [s for camada in CAMADAS for s in skins_para(chave, camada)]
        return sum(1 for s in todas if self.progresso.skin_liberada(s.chave)), len(todas)

    def desenhar_classe(self, tela, rect, chave, classe):
        visual = self.progresso.visual_da_classe(chave)
        nome = nome_do_sprite(classe.sprite_da_aparencia(classe.aparencia_padrao), visual)
        liberadas, total = self.contagem(chave)
        dica = "\n".join(f"{c.capitalize()}: {skin(visual[c]).nome}" for c in CAMADAS if visual.get(c)) or "Sem skins equipadas."
        botao = self.botao(Botao(rect, "", (lambda c=chave: self.abrir(c)), dica=(classe.nome, dica),
                                 selecionado=chave == self.classe))
        destaque = botao.focado or botao.selecionado or (not self.usando_teclado and botao.em_cima(self.mouse))
        tela.set_clip(rect.inflate(-6, -6))
        desenhar_npc(tela, self.app.sprites, nome, (rect.centerx, rect.bottom - 64), 2, self.tempo,
                     contorno=tema.OURO_CLARO if destaque else None)
        tela.set_clip(None)
        linha(tela, classe.nome, tema.normal(), tema.TEXTO_TITULO, (rect.centerx, rect.bottom - 52), rect.width - 20, "midtop")
        texto(tela, f"Skins: {liberadas}/{total}", tema.pequena(), tema.TEXTO_FRACO, (rect.centerx, rect.bottom - 26), "midtop")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_do_acampamento(tela, "Baú", self.progresso, "Escolha a classe para trocar as skins")
        for i, (chave, classe) in enumerate(self.progresso.classes_liberadas().items()):   # (sem as secretas)
            fila, coluna = divmod(i, COLUNAS)
            rect = pygame.Rect(16 + coluna * (LARGURA + 11), 72 + fila * (ALTURA + 10), LARGURA, ALTURA)
            self.desenhar_classe(tela, rect, chave, classe)
        compradas = len(self.progresso.skins_compradas)
        texto(tela, f"Skins raras compradas: {compradas}. A vitrine do Taverneiro muda a cada run.", tema.pequena(),
              tema.TEXTO_FRACO, (16, tema.ALTURA - 36), "midleft")
        self.botao(Botao((tema.LARGURA - 176, tema.ALTURA - 60, 160, 44), "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
