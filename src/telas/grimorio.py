"""Mestre do Grimório: o catálogo dos golpes de cada classe, subclasse, evolução e os raros.

Só mostra (trocar golpes é durante a run). Golpes que nenhum herói teve ainda aparecem como "???",
com a pista de onde se aprende. Os raros mostram a conquista que os libera e o progresso dela.
"""

import pygame

from roguelike.classes import todas_as_classes
from roguelike.conquistas import conquista_do_golpe
from roguelike.elementos import nome as nome_do_elemento, cor as cor_do_elemento, PADRAO
from roguelike.golpes import NOMES_DE_ALVO, NOMES_DE_TIPO
from roguelike.grimorio import secoes_da_classe, total_da_classe
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_do_acampamento
from ui import tema
from ui.desenho import painel, losango
from ui.layout import colunas, grade, altura_da_grade
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao


class TelaGrimorio(TelaComBotoes):
    def __init__(self, app, classe=None):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=160)
        self.classe = classe if classe in todas_as_classes() else next(iter(todas_as_classes()))
        self.secao = "classe"
        self.vista = None
        self.lista_secoes = PainelRolavel()
        self.lista_golpes = PainelRolavel(passo=64)

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

    def trocar_classe(self, chave):
        self.classe = chave
        self.secao = "classe"
        self.vista = None
        self.lista_secoes.ir_para(0, imediato=True)
        self.lista_golpes.ir_para(0, imediato=True)

    def trocar_secao(self, chave):
        self.secao = chave
        self.vista = None
        self.lista_golpes.ir_para(0, imediato=True)

    def ver(self, entrada):
        if entrada.chave != self.vista:
            self.app.audio.tocar("pagina")
        self.vista = entrada.chave

    # ---------------- desenho ----------------
    def desenhar_classes(self, tela):
        classes = self.progresso.classes_liberadas()             # (as secretas só depois de liberadas)
        largura = min(116, (tema.LARGURA - 32 - (len(classes) - 1) * 8) // len(classes))   # cabem todas na fileira
        for i, (chave, classe) in enumerate(classes.items()):
            descobertos, total = total_da_classe(chave, self.progresso)
            nome = classe.nome_que_cabe(tema.pequena(), largura - 12)            # (estreito: "Médico", "Bobo")
            botao = Botao((16 + i * (largura + 8), 64, largura, 52), nome, (lambda c=chave: self.trocar_classe(c)),
                          subtexto=f"{descobertos}/{total}", dica=(classe.nome, classe.descricao))
            botao.selecionado = chave == self.classe
            self.botao(botao)

    def desenhar_secoes(self, tela, secoes, janela):
        """Coluna da esquerda: as seções (classe, subclasses, evoluções, raros) numa lista rolável."""
        total = len(secoes) * 60 - 6
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista_secoes, janela, total) as y0:
            for i, secao in enumerate(secoes):
                botao = Botao((janela.x, y0 + i * 60, largura, 54), secao.nome, (lambda c=secao.chave: self.trocar_secao(c)),
                              subtexto=f"{secao.descobertas(self.progresso)}/{len(secao.entradas)} descobertos")
                botao.selecionado = secao.chave == self.secao
                self.botao(botao)

    def desenhar_cartoes(self, tela, entradas, janela):
        """Meio: os golpes da seção em cartões (2 colunas), numa grade rolável."""
        total = altura_da_grade(len(entradas), 2, 66, 6)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista_golpes, janela, total) as y0:
            for entrada, rect in zip(entradas, grade((janela.x, y0, largura, total), len(entradas), 2, 66, 6)):
                self.desenhar_cartao(tela, rect, entrada)

    def desenhar_cartao(self, tela, rect, entrada):
        descoberta = entrada.descoberta(self.progresso)
        self.botao(Botao(rect, "", (lambda e=entrada: self.ver(e)), estilo="osso" if descoberta else "pedra",
                         selecionado=entrada.chave == self.vista))
        g = entrada.golpe
        if descoberta:
            elemento = g.elemento if g.elemento != PADRAO else None
            if elemento:
                losango(tela, (rect.x + 14, rect.y + 16), 5, cor_do_elemento(elemento))
            cor = tema.OURO_CLARO if g.raro else tema.TEXTO_TITULO
            linha(tela, g.nome, tema.normal(), cor, (rect.x + 26, rect.y + 6), rect.width - 36)
        else:
            linha(tela, "???", tema.normal(), tema.TEXTO_APAGADO, (rect.x + 26, rect.y + 6), rect.width - 36)
        linha(tela, entrada.origem, tema.mini(), tema.TEXTO_FRACO if descoberta else tema.TEXTO_APAGADO,
              (rect.x + 26, rect.bottom - 8), rect.width - 36, "bottomleft")

    def desenhar_detalhe(self, tela, rect, entrada):
        painel(tela, rect, "ferro")
        area = rect.inflate(-28, -28)
        g = entrada.golpe
        descoberta = entrada.descoberta(self.progresso)
        linha(tela, g.nome if descoberta else "???", tema.media(), tema.OURO_CLARO if g.raro else tema.TEXTO_TITULO,
              area.topleft, area.width)
        trechos = [(entrada.detalhe, tema.XP)]
        conquista = conquista_do_golpe(g.chave) if g.raro else None
        if conquista is not None:
            feita = conquista.chave in self.progresso.conquistas_feitas
            trechos.append((f"{conquista.descricao} ({'liberado' if feita else conquista.texto_do_progresso(self.progresso)})",
                            tema.OURO if feita else tema.TEXTO_FRACO))
        if descoberta:
            elemento = f" · {nome_do_elemento(g.elemento)}" if g.elemento != PADRAO else ""
            trechos += [(f"{NOMES_DE_TIPO.get(g.tipo, g.tipo)}{elemento} · {g.texto_custo()} · "
                         f"{NOMES_DE_ALVO.get(g.alvo, g.alvo)}", tema.ENERGIA_CLARA),
                        (g.descricao, tema.TEXTO_FRACO), (g.resumo(1), tema.TEXTO)]
        else:
            trechos.append(("Nenhum herói teve este golpe ainda. Aprenda numa run para ver o que ele faz.",
                            tema.TEXTO_APAGADO))
        CaixaTexto(pygame.Rect(area.x, area.y + 40, area.width, area.height - 40), tema.pequena(), padding=0,
                   maximo_linhas=16).desenhar(tela, trechos)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_do_acampamento(tela, "Mestre do Grimório", self.progresso, "Os golpes que cada herói pode ter")
        self.desenhar_classes(tela)
        secoes = secoes_da_classe(self.classe)
        corpo = pygame.Rect(16, 122, tema.LARGURA - 32, tema.ALTURA - 72 - 122)
        esquerda, meio, direita = colunas(corpo, [220, 548, None], espaco=12)
        self.desenhar_secoes(tela, secoes, esquerda)
        secao = next((s for s in secoes if s.chave == self.secao), secoes[0])
        if self.vista not in [e.chave for e in secao.entradas]:
            self.vista = secao.entradas[0].chave if secao.entradas else None
        self.desenhar_cartoes(tela, secao.entradas, meio)
        vista = next((e for e in secao.entradas if e.chave == self.vista), None)
        if vista is not None:
            self.desenhar_detalhe(tela, direita, vista)
        voltar = pygame.Rect(tema.LARGURA - 176, tema.ALTURA - 60, 160, 44)
        linha(tela, "Para trocar os golpes de um herói, use a tela de golpes durante a run.", tema.pequena(),
              tema.TEXTO_FRACO, (16, voltar.centery), voltar.x - 32, "midleft")
        self.botao(Botao(voltar, "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
