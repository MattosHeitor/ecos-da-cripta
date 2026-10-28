"""Espelho Antigo: árvore de talentos de cada classe (as raças ficam com o Mago Ancião)."""

import pygame

from roguelike.classes import todas_as_classes
from roguelike.dados import regras
from roguelike.progresso import arvore_da_classe
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_do_acampamento
from ui import tema
from ui.desenho import texto, painel, barra, paragrafo
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto
from ui.widgets import Botao

AREA_ARVORE = pygame.Rect(250, 72, 660, 572)
TAMANHO_NO = (122, 76)                       # cabe o nome em 2 linhas + o "nível · custo"


class TelaEspelho(TelaComBotoes):
    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=150)
        self.classe = next(iter(todas_as_classes()))
        self.mensagem = ""
        self.lista = PainelRolavel(passo=60)

    def musica(self):
        return "acampamento"

    def voltar(self):
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def salvar(self, mensagem):
        self.app.progresso.salvar()
        self.mensagem = mensagem

    # ---------------- talentos ----------------
    def posicao_do_no(self, no):
        coluna, linha = no.posicao
        x = AREA_ARVORE.x + 30 + coluna * 125
        y = AREA_ARVORE.y + 40 + linha * 92
        return pygame.Rect(x, y, *TAMANHO_NO)

    def comprar(self, no):
        progresso = self.app.progresso
        if progresso.comprar_talento(self.classe, no.chave):
            self.salvar(f"{no.nome} aprendido.")
        elif not progresso.no_liberado(self.classe, no.chave):
            self.mensagem = "Esse talento ainda está bloqueado: aprenda um vizinho antes."
        elif progresso.niveis_do_no(self.classe, no.chave) >= no.maximo:
            self.mensagem = "Esse talento já está no máximo."
        else:
            self.mensagem = "Pontos de talento insuficientes (ganhe prestígio jogando com a classe)."

    def pedir_reinicio(self):
        """Pergunta antes de gastar Brasas para reiniciar a árvore."""
        preco = regras()["progresso"]["preco_reiniciar_arvore"]
        nome = todas_as_classes()[self.classe].nome
        self.confirmar("Reiniciar árvore", f"Reiniciar a árvore do {nome} por {preco} Brasas? Os pontos voltam.",
                       self.reiniciar, "Reiniciar")

    def reiniciar(self):
        if self.app.progresso.reiniciar_arvore(self.classe):
            self.salvar("Árvore reiniciada. Os pontos voltaram.")
        else:
            self.mensagem = "Nada para reiniciar ou Brasas insuficientes."

    def desenhar_talentos(self, tela):
        progresso = self.app.progresso
        classes = progresso.classes_liberadas()                  # (as secretas só depois de liberadas)
        # classes à esquerda (lista rolável)
        janela = pygame.Rect(16, 72, 222, 572)
        total = len(classes) * 60 - 6
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            for i, (chave, classe) in enumerate(classes.items()):
                nivel = progresso.nivel_de_prestigio(chave)
                botao = Botao((16, y0 + i * 60, largura, 54), classe.nome, (lambda c=chave: self.escolher_classe(c)),
                              subtexto=f"Prestígio {nivel}  ·  {progresso.pontos_livres(chave)} pontos")
                botao.selecionado = chave == self.classe
                self.botao(botao)

        painel(tela, AREA_ARVORE, "pedra")
        arvore = arvore_da_classe(self.classe)
        # linhas entre os nós
        for no in arvore.values():
            for requisito in no.requer:
                a, b = self.posicao_do_no(no), self.posicao_do_no(arvore[requisito])
                ligado = progresso.niveis_do_no(self.classe, requisito) > 0
                pygame.draw.line(tela, tema.OURO if ligado else (60, 52, 66), a.midtop, b.midbottom, 3)
        for no in arvore.values():
            rect = self.posicao_do_no(no)
            niveis = progresso.niveis_do_no(self.classe, no.chave)
            liberado = progresso.no_liberado(self.classe, no.chave)
            estilo = "ouro" if niveis >= no.maximo else ("osso" if niveis else ("ferro" if liberado else "pedra"))
            cor = tema.TEXTO if liberado else tema.TEXTO_APAGADO
            botao = Botao(rect, no.nome, (lambda n=no: self.comprar(n)), cor_texto=cor, estilo=estilo,
                          subtexto=f"{niveis}/{no.maximo}  ·  custo {no.custo}",
                          dica=(no.nome, f"{no.descricao()}\nCusto: {no.custo} ponto(s) por nível. Níveis: {niveis}/{no.maximo}."
                                + ("" if liberado else "\nBloqueado: aprenda um talento ligado a este.")))
            botao.fontes = (tema.mini(),)                  # a árvore toda com a mesma letra (nomes de 1 ou 2 linhas)
            self.botao(botao)

        # informações da classe
        direita = painel(tela, (922, 72, tema.LARGURA - 930, 572), "ferro")
        classe = classes[self.classe]
        y = direita.y + 16
        texto(tela, classe.nome, tema.media(), tema.TEXTO_TITULO, (direita.x + 16, y))
        y += 36
        nivel = progresso.nivel_de_prestigio(self.classe)
        maximo = regras()["progresso"]["prestigio_maximo"]
        texto(tela, f"Prestígio {nivel}/{maximo}", tema.normal(), tema.TEXTO, (direita.x + 16, y))
        y += 28
        if nivel < maximo:
            xp = progresso.xp_de_prestigio(self.classe)
            precisa = progresso.xp_para_proximo_prestigio(self.classe)
            barra(tela, (direita.x + 20, y, direita.width - 40, 10), xp / precisa, tema.XP, marcas=0)
            texto(tela, f"{xp}/{precisa} XP de prestígio", tema.mini(), tema.TEXTO_FRACO, (direita.x + 16, y + 14))
            y += 40
        texto(tela, f"Pontos livres: {progresso.pontos_livres(self.classe)} de {progresso.pontos_totais(self.classe)}",
              tema.normal(), tema.OURO_CLARO, (direita.x + 16, y))
        y += 34
        y = paragrafo(tela, "Jogar com a classe dá prestígio. Cada nível de prestígio dá 3 pontos para esta árvore. "
                            "Os talentos valem para todo herói desta classe no começo de cada run.",
                      tema.pequena(), tema.TEXTO_FRACO, (direita.x + 16, y), direita.width - 32)
        preco = regras()["progresso"]["preco_reiniciar_arvore"]
        self.botao(Botao((direita.x + 16, direita.bottom - 58, direita.width - 32, 44), f"Reiniciar árvore ({preco} Brasas)",
                         self.pedir_reinicio))

    def escolher_classe(self, chave):
        self.classe = chave
        self.mensagem = ""

    # ---------------- tela ----------------
    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_do_acampamento(tela, "Espelho Antigo", self.app.progresso, "Árvores de talentos")
        self.desenhar_talentos(tela)
        voltar = pygame.Rect(tema.LARGURA - 176, tema.ALTURA - 60, 160, 44)
        if self.mensagem:
            CaixaTexto((16, voltar.y, voltar.x - 32, voltar.height), tema.normal(), tema.OURO_CLARO, alinhamento="centro",
                       vertical="meio").desenhar(tela, self.mensagem)
        self.botao(Botao(voltar, "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
