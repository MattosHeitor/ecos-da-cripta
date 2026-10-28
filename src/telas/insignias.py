"""Insígnias: todas as conquistas (feitas e por fazer, com o progresso e o prêmio) e o prestígio de
cada classe (barra de XP e o próximo marco). Abre pelo quadro de insígnias do acampamento.
"""

import pygame

from roguelike.insignias import insignias_de_conquista, prestigio_das_classes
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_do_acampamento, desenhar_abas
from ui import tema
from ui.desenho import texto, painel, barra, losango
from ui.layout import grade, altura_da_grade
from ui.rolagem import PainelRolavel
from ui.texto import escrever, linha
from ui.widgets import Botao

ABAS = (("conquistas", "Conquistas"), ("prestigio", "Prestígio"))


def desenhar_medalha(tela, centro, raio, feita, golpe=False):
    """Medalha redonda: dourada quando feita; roxa para conquistas de golpe raro; apagada se falta."""
    if feita:
        borda, miolo = (tema.OURO, (150, 90, 210)) if golpe else (tema.OURO, tema.OURO_CLARO)
    else:
        borda, miolo = (tema.FERRO, tema.PEDRA)
    pygame.draw.circle(tela, (8, 6, 10), (centro[0], centro[1] + 2), raio)
    pygame.draw.circle(tela, borda, centro, raio)
    pygame.draw.circle(tela, miolo, centro, raio - 3)
    if feita:
        losango(tela, centro, max(3, raio // 2), tema.OURO_ESCURO if not golpe else tema.OURO_CLARO)
    else:
        texto(tela, "?", tema.mini(), tema.TEXTO_APAGADO, centro, "center")


def desenhar_escudo(tela, rect, nivel, ativo):
    """Escudinho de prestígio com o número do nível."""
    def escudo(r):
        return [r.topleft, r.topright, (r.right, r.centery + 2), r.midbottom, (r.left, r.centery + 2)]

    rect = pygame.Rect(rect)
    pygame.draw.polygon(tela, tema.OURO if ativo else tema.FERRO, escudo(rect))
    pygame.draw.polygon(tela, tema.SANGUE_ESCURO if ativo else tema.PEDRA_ESCURA, escudo(rect.inflate(-6, -6)))
    texto(tela, str(nivel), tema.mini(), tema.OURO_CLARO if ativo else tema.TEXTO_APAGADO, (rect.centerx, rect.centery - 1),
          "center")


class TelaInsignias(TelaComBotoes):
    def __init__(self, app, aba="conquistas"):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=160)
        self.aba = aba
        self.lista = PainelRolavel(passo=108)

    def musica(self):
        return "acampamento"

    def voltar(self):
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def trocar_aba(self, aba):
        self.aba = aba
        self.lista.ir_para(0, imediato=True)

    def janela(self):
        """A grade rolável: das abas até acima do botão Voltar."""
        return pygame.Rect(16, 120, tema.LARGURA - 32, tema.ALTURA - 72 - 120)

    def desenhar_conquistas(self, tela):
        insignias = insignias_de_conquista(self.app.progresso)
        janela = self.janela()
        total = altura_da_grade(len(insignias), 5, 100, 8)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            for insignia, rect in zip(insignias, grade((janela.x, y0, largura, total), len(insignias), 5, 100, 8)):
                self.desenhar_insignia(tela, rect, insignia)

    def desenhar_insignia(self, tela, rect, insignia):
        """Cartão de uma conquista: medalha e nome em cima; descrição com o progresso; o prêmio embaixo."""
        painel(tela, rect, "ouro" if insignia.feita else "pedra")
        desenhar_medalha(tela, (rect.x + 20, rect.y + 16), 10, insignia.feita, bool(insignia.conquista.golpe))
        cor = tema.TEXTO_TITULO if insignia.feita else tema.TEXTO_FRACO
        linha(tela, insignia.conquista.nome, tema.pequena(), cor, (rect.x + 36, rect.y + 6), rect.width - 44)
        interno = pygame.Rect(rect.x + 10, rect.y + 28, rect.width - 20, rect.height - 34)
        linha(tela, insignia.premio, tema.mini(), tema.OURO if insignia.feita else tema.VELA, interno.bottomleft,
              interno.width, "bottomleft")
        escrever(tela, f"{insignia.conquista.descricao} ({insignia.texto_do_progresso})",
                 pygame.Rect(interno.x, interno.y, interno.width, interno.height - 20), tema.mini(),
                 tema.TEXTO if insignia.feita else tema.TEXTO_APAGADO, padding=0)

    def desenhar_prestigio(self, tela):
        classes = prestigio_das_classes(self.app.progresso)
        janela = self.janela()
        total = altura_da_grade(len(classes), 2, 98, 8)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            for p, celula in zip(classes, grade((janela.x, y0, largura, total), len(classes), 2, 98, 8)):
                self.desenhar_classe(tela, celula, p)

    def desenhar_classe(self, tela, celula, p):
        """Cartão de prestígio de uma classe: escudo com o nível, barra de XP e o próximo marco."""
        rect = painel(tela, celula, "ferro")
        desenhar_escudo(tela, (rect.x + 14, rect.y + 16, 34, 40), p.nivel, p.nivel > 0)
        linha(tela, f"{p.classe.nome} — prestígio {p.nivel}/{p.maximo}", tema.normal(), tema.TEXTO_TITULO,
              (rect.x + 60, rect.y + 10), rect.width - 76)
        barra(tela, (rect.x + 60, rect.y + 42, rect.width - 76, 12), p.fracao(), tema.XP, marcas=0)
        progresso = "completo" if p.no_maximo else f"{p.xp}/{p.precisa} XP de prestígio"
        linha(tela, progresso, tema.mini(), tema.TEXTO_FRACO, (rect.x + 60, rect.y + 58), rect.width - 76)
        linha(tela, "Próximo: " + p.texto_do_proximo(), tema.mini(), tema.OURO_CLARO, (rect.x + 60, rect.y + 76),
              rect.width - 76)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        feitas = sum(1 for i in insignias_de_conquista(self.app.progresso) if i.feita)
        cabecalho_do_acampamento(tela, "Insígnias", self.app.progresso,
                                 f"Conquistas: {feitas}/{len(insignias_de_conquista(self.app.progresso))}")
        desenhar_abas(self, (16, 66), ABAS, self.aba, self.trocar_aba)
        if self.aba == "conquistas":
            self.desenhar_conquistas(tela)
        else:
            self.desenhar_prestigio(tela)
        self.botao(Botao((tema.LARGURA - 176, tema.ALTURA - 60, 160, 44), "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
