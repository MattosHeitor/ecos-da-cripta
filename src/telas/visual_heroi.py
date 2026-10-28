"""Visual do herói (Baú/Capitã): escolher as skins de roupa, chapéu e arma.

À esquerda, a prévia grande e animada do herói (passar o mouse numa skin prova ela na prévia, mesmo
bloqueada). À direita, abas Roupa / Chapéu / Arma com a lista rolável: cada skin bloqueada mostra a
conquista que a libera e uma barra de progresso; as raras dizem que estão na vitrine do Taverneiro.
A escolha vale para a classe inteira e fica salva no progresso permanente.
"""

import pygame

from roguelike.classes import todas_as_classes
from roguelike.conquistas import conquista_da_skin
from roguelike.skins import CAMADAS, NOMES_DAS_CAMADAS, skins_para, nome_do_sprite, skin
from telas.comum import TelaComBotoes, Fundo, desenhar_previa, cabecalho, desenhar_abas
from ui import tema
from ui.desenho import painel, barra, titulo_de_painel
from ui.layout import colunas, area_util
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao

ALTURA_LINHA = 66


class TelaVisual(TelaComBotoes):
    def __init__(self, app, chave_classe, chave_subclasse, ao_sair):
        super().__init__(app)
        self.classe = todas_as_classes()[chave_classe]
        self.subclasse = self.classe.subclasses.get(chave_subclasse) if chave_subclasse else None
        self.ao_sair = ao_sair
        self.fundo = Fundo("acampamento", escurecer=170)
        self.mensagem = ""
        self.aba = CAMADAS[0]
        self.lista = PainelRolavel(passo=ALTURA_LINHA)
        self.provando = None              # (camada, chave) da skin sob o mouse: aparece na prévia

    @property
    def progresso(self):
        return self.app.progresso

    def voltar(self):
        self.ao_sair()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def trocar_aba(self, aba):
        self.aba = aba
        self.lista.ir_para(0, imediato=True)

    def sprite_da_previa(self, provar=None):
        """O sprite com as skins equipadas (e, provando, a skin sob o mouse no lugar da da camada dela)."""
        base = (self.subclasse.sprite if self.subclasse and self.subclasse.sprite
                else self.classe.sprite_da_aparencia(self.classe.aparencia_padrao))
        visual = dict(self.progresso.visual_da_classe(self.classe.chave))
        if provar is not None:
            camada, chave = provar
            visual[camada] = chave
        return nome_do_sprite(base, {c: k for c, k in visual.items() if k})

    def escolher(self, camada, chave):
        if self.progresso.equipar_skin(self.classe.chave, camada, chave):
            self.progresso.salvar()
            self.mensagem = f"{NOMES_DAS_CAMADAS[camada]}: {skin(chave).nome if chave else 'padrão'}"
            self.app.audio.tocar("item")
            if camada != self.aba:
                self.trocar_aba(camada)

    def contagem(self, camada=None):
        """(liberadas, total) das skins da classe (numa camada ou em todas)."""
        todas = [s for c in ([camada] if camada else CAMADAS) for s in skins_para(self.classe.chave, c)]
        return sum(1 for s in todas if self.progresso.skin_liberada(s.chave)), len(todas)

    # ---------------- desenho ----------------
    def desenhar_previa(self, tela, rect):
        """A prévia grande: o herói animado, o nome e o que está equipado em cada camada."""
        painel(tela, rect, "ferro")
        titulo = self.classe.nome + (f" · {self.subclasse.nome}" if self.subclasse else "")
        topo = titulo_de_painel(tela, rect, titulo)
        resumo = pygame.Rect(rect.x + 16, rect.bottom - 16 - 3 * 24, rect.width - 32, 3 * 24)
        palco = pygame.Rect(rect.x + 14, topo, rect.width - 28, resumo.y - 10 - topo)
        nome = self.sprite_da_previa(self.provando)
        escala = 5 if self.app.sprites.caixa(nome, 5).height < palco.height - 40 else 4
        desenhar_previa(tela, self.app.sprites, nome, palco, self.tempo, escala, "osso")
        if self.provando is not None:
            linha(tela, "provando", tema.mini(), tema.OURO, (palco.centerx, palco.y + 10), palco.width, "midtop")
        visual = self.progresso.visual_da_classe(self.classe.chave)
        for i, camada in enumerate(CAMADAS):
            atual = visual.get(camada)
            y = resumo.y + i * 24
            linha(tela, f"{NOMES_DAS_CAMADAS[camada]}:", tema.pequena(), tema.TEXTO_FRACO, (resumo.x, y), 90)
            linha(tela, skin(atual).nome if atual else "padrão", tema.pequena(), tema.OURO_CLARO if atual else tema.TEXTO,
                  (resumo.x + 96, y), resumo.width - 96)

    def desenhar_lista(self, tela, rect):
        """Abas Roupa / Chapéu / Arma (com a contagem) e a lista rolável de skins da aba."""
        painel(tela, rect, "ferro")
        abas = []
        for camada in CAMADAS:
            liberadas, total = self.contagem(camada)
            abas.append((camada, f"{NOMES_DAS_CAMADAS[camada]} {liberadas}/{total}"))
        largura_aba = (rect.width - 28 - 2 * 10) // 3
        desenhar_abas(self, (rect.x + 14, rect.y + 14), abas, self.aba, self.trocar_aba, largura=largura_aba, altura=40)
        janela = pygame.Rect(rect.x + 14, rect.y + 66, rect.width - 28, rect.height - 80)
        atual = self.progresso.visual_da_classe(self.classe.chave).get(self.aba)
        opcoes = [None] + skins_para(self.classe.chave, self.aba)
        total = len(opcoes) * ALTURA_LINHA - 6
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            for i, opcao in enumerate(opcoes):
                self.desenhar_opcao(tela, pygame.Rect(janela.x, y0 + i * ALTURA_LINHA, largura, ALTURA_LINHA - 6),
                                    self.aba, opcao, atual)

    def desenhar_opcao(self, tela, caixa, camada, opcao, atual):
        """Uma linha: nome, situação (liberada, rara ou bloqueada) e a barra de progresso da conquista."""
        if opcao is None:
            botao = Botao(caixa, "Padrão", lambda c=camada: self.escolher(c, None), subtexto="sem skin",
                          dica=("Padrão", "A roupa da classe, sem skin."))
            botao.mostrar_rotulo = False
            botao.selecionado = atual is None
            self.botao(botao)
            self.escrever_linha(tela, caixa, "Padrão", "sem skin", tema.TEXTO, None, selecionada=botao.selecionado)
            return
        liberada = self.progresso.skin_liberada(opcao.chave)
        conquista = conquista_da_skin(opcao.chave)
        fracao = None
        if liberada:
            sub, dica = ("rara · comprada" if opcao.preco else "liberada"), (opcao.nome, opcao.descricao)
        elif opcao.preco or conquista is None:
            sub = f"rara · vitrine do Taverneiro ({opcao.preco} Brasas)"
            dica = (opcao.nome, f"{opcao.descricao}\nSkin rara: aparece de vez em quando na vitrine do Taverneiro "
                                f"({opcao.preco} Brasas).")
        else:
            feito, precisa = conquista.progresso(self.progresso)
            fracao = min(1.0, feito / max(1, precisa))
            sub = f"bloqueada · {conquista.nome}: {conquista.texto_do_progresso(self.progresso)}"
            dica = (opcao.nome, f"{opcao.descricao}\nConquista: {conquista.nome} — {conquista.descricao}\n"
                                f"Progresso: {conquista.texto_do_progresso(self.progresso)}")
        botao = Botao(caixa, opcao.nome, lambda c=camada, k=opcao.chave: self.escolher(c, k), ativo=liberada,
                      dica=dica, subtexto=sub)
        botao.mostrar_rotulo = False                           # o conteúdo (nome, situação, barra) vem abaixo
        botao.selecionado = atual == opcao.chave
        self.botao(botao)
        if botao.em_cima(self.mouse) and not self.usando_teclado or botao.focado:
            self.provando = (camada, opcao.chave)
        self.escrever_linha(tela, caixa, opcao.nome, sub, tema.TEXTO if liberada else tema.TEXTO_FRACO, fracao,
                            selecionada=botao.selecionado)

    def escrever_linha(self, tela, caixa, nome, situacao, cor, fracao, selecionada=False):
        """O texto de uma linha (desenhado por cima do botão, que tem o rótulo vazio)."""
        interno = caixa.inflate(-24, -12)
        if selecionada:
            linha(tela, "equipada", tema.mini(), tema.OURO, (interno.right, interno.y), 90, "topright")
        linha(tela, nome, tema.normal(), tema.OURO_CLARO if selecionada else cor, interno.topleft,
              interno.width - (96 if selecionada else 0))
        if fracao is None:
            linha(tela, situacao, tema.mini(), tema.TEXTO_FRACO, interno.bottomleft, interno.width, "bottomleft")
            return
        largura_barra = min(140, interno.width // 3)
        linha(tela, situacao, tema.mini(), tema.TEXTO_FRACO, interno.bottomleft, interno.width - largura_barra - 12,
              "bottomleft")
        barra(tela, (interno.right - largura_barra, interno.bottom - 12, largura_barra, 8), fracao, tema.XP, marcas=0)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.provando = None
        self.fundo.desenhar(tela)
        liberadas, total = self.contagem()
        cabecalho(tela, f"Visual — {self.classe.nome}", direita=f"Skins liberadas: {liberadas}/{total}",
                  cor_direita=tema.OURO_CLARO)
        previa, lista = colunas(area_util(), [460, None], espaco=12)
        self.desenhar_lista(tela, lista)
        self.desenhar_previa(tela, previa)                     # depois da lista: já sabe qual skin está sendo provada
        pronto = pygame.Rect(tema.LARGURA - 216, tema.ALTURA - 58, 200, 46)
        rodape = pygame.Rect(16, pronto.y, pronto.x - 32, pronto.height)
        CaixaTexto(rodape, tema.pequena(), tema.TEXTO_FRACO, vertical="meio").desenhar(
            tela, [(self.mensagem, tema.OURO_CLARO)] if self.mensagem else
            [("Skins são só visuais e valem para a classe inteira. Passe o mouse numa skin para prová-la; "
              "as bloqueadas mostram a conquista que libera.", tema.TEXTO_FRACO)])
        self.botao(Botao(pronto, "Pronto", self.voltar, "ESC", estilo="ouro"))
        self.terminar_desenho(tela)
