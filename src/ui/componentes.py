"""Componentes de interface reutilizáveis (todas as telas usam estes, em vez de redesenhar à mão).

- Painel: moldura gótica com título opcional;
- Tooltip: caixa de dica (título + texto);
- BarraStatus: barra com número (vida, energia, XP);
- ListaSelecionavel: lista vertical navegável por teclado e mouse, com rolagem;
- Deslizador: valor de 0 a 100% (volume);
- AreaClicavel: área invisível que age como botão (NPCs, retratos);
- DialogoDeConfirmacao: "Tem certeza?" antes de ações sem volta;
- Notificacoes: avisos rápidos no topo da tela ("Golpe aprimorado!");
- TextoRevelado: texto que aparece letra por letra;
- RegistroRolavel: mensagens com quebra de linha e rolagem (registro da batalha).
Texto em caixa: ui.texto.CaixaTexto (todas as peças acima a usam).

Botao e CampoDeTexto ficam em ui.widgets (este módulo os reexporta).
"""

import pygame

from ui import tema
from ui.desenho import painel, titulo_de_painel, texto, barra, escurecer_tela, losango
from ui.escala import posicao_do_mouse
from ui.widgets import Botao, CampoDeTexto, desenhar_dica

__all__ = ["Botao", "CampoDeTexto", "Painel", "Tooltip", "BarraStatus", "ListaSelecionavel", "Deslizador",
           "AreaClicavel", "DialogoDeConfirmacao", "Notificacoes", "TextoRevelado", "RegistroRolavel"]


class Painel:
    """Moldura com título opcional. desenhar() devolve o retângulo útil (abaixo do título)."""

    def __init__(self, rect, estilo="ferro", titulo=None):
        self.rect = pygame.Rect(rect)
        self.estilo = estilo
        self.titulo = titulo

    def desenhar(self, tela):
        painel(tela, self.rect, self.estilo)
        if not self.titulo:
            return self.rect.inflate(-24, -24)
        topo = titulo_de_painel(tela, self.rect, self.titulo)
        return pygame.Rect(self.rect.x + 12, topo, self.rect.width - 24, self.rect.bottom - topo - 12)


class Tooltip:
    """Dica com título e texto. Perto do painel de baixo, aparece em cima dele."""

    def __init__(self, titulo, conteudo="", largura=300, cor_titulo=tema.TEXTO_TITULO):
        self.titulo = titulo
        self.conteudo = conteudo
        self.largura = largura
        self.cor_titulo = cor_titulo

    def desenhar(self, tela, posicao):
        return desenhar_dica(tela, posicao, self.titulo, self.conteudo, self.largura, self.cor_titulo)


class BarraStatus:
    """Barra com o número escrito: "31/40". A parte "atrasada" mostra o dano que acabou de entrar.

    numero: "direita" (ao lado da barra), "dentro" ou None.
    """

    def __init__(self, cor, rotulo="", numero="direita", marcas=10, cor_atraso=tema.VIDA_ATRASO):
        self.cor = cor
        self.rotulo = rotulo
        self.numero = numero
        self.marcas = marcas
        self.cor_atraso = cor_atraso

    def desenhar(self, tela, rect, atual, maximo, atrasada=None):
        rect = pygame.Rect(rect)
        maximo = max(1, maximo)
        largura_numero = 0
        texto_numero = f"{max(0, int(atual))}/{int(maximo)}"
        if self.numero == "direita":
            largura_numero = tema.mini().size(texto_numero)[0] + 10
        area = pygame.Rect(rect.x, rect.y, rect.width - largura_numero, rect.height)
        if self.rotulo:
            texto(tela, self.rotulo, tema.mini(), tema.TEXTO_FRACO, (area.x, area.y - 2), "bottomleft")
        fracao_atrasada = None if atrasada is None else atrasada / maximo
        barra(tela, area, atual / maximo, self.cor, fracao_atrasada, self.cor_atraso, self.marcas,
              texto_numero if self.numero == "dentro" else None)
        if self.numero == "direita":
            texto(tela, texto_numero, tema.mini(), tema.TEXTO, (rect.right, area.centery), "midright")
        return area


class ListaSelecionavel:
    """Lista vertical. Teclado: cima/baixo movem, confirmar escolhe. Mouse: passar seleciona,
    clicar escolhe, roda rola.

    desenhar_item(tela, item, area, selecionado) desenha cada linha; ao_escolher(item) é chamado
    ao confirmar.
    """

    def __init__(self, itens, altura_item=40, ao_escolher=None, espaco=4):
        self.itens = list(itens)
        self.altura_item = altura_item
        self.espaco = espaco
        self.ao_escolher = ao_escolher
        self.indice = 0
        self.rolagem = 0
        self.rect = pygame.Rect(0, 0, 0, 0)

    @property
    def selecionado(self):
        return self.itens[self.indice] if self.itens else None

    def cabem(self):
        return max(1, (self.rect.height + self.espaco) // (self.altura_item + self.espaco))

    def mover(self, passo):
        if not self.itens:
            return
        self.indice = (self.indice + passo) % len(self.itens)
        self._mostrar_selecionado()

    def _mostrar_selecionado(self):
        if self.indice < self.rolagem:
            self.rolagem = self.indice
        elif self.indice >= self.rolagem + self.cabem():
            self.rolagem = self.indice - self.cabem() + 1

    def area_do_item(self, i):
        y = self.rect.y + (i - self.rolagem) * (self.altura_item + self.espaco)
        return pygame.Rect(self.rect.x, y, self.rect.width, self.altura_item)

    def item_no_ponto(self, posicao):
        for i in range(self.rolagem, min(len(self.itens), self.rolagem + self.cabem())):
            if self.area_do_item(i).collidepoint(posicao):
                return i
        return None

    def escolher(self):
        if self.selecionado is not None and self.ao_escolher is not None:
            self.ao_escolher(self.selecionado)

    def _rolar_para(self, rolagem):
        self.rolagem = max(0, min(len(self.itens) - self.cabem(), rolagem))

    def trilho(self):
        return pygame.Rect(self.rect.right + 4, self.rect.y, 8, self.rect.height)

    def polegar(self):
        trilho = self.trilho()
        altura = max(20, trilho.height * self.cabem() // max(1, len(self.itens)))
        y = trilho.y + (trilho.height - altura) * self.rolagem // max(1, len(self.itens) - self.cabem())
        return pygame.Rect(trilho.x, y, trilho.width, altura)

    def evento(self, e, controles):
        """Devolve True se a lista usou o evento."""
        if e.type == pygame.KEYDOWN:
            if controles.eh(e, "cima"):
                self.mover(-1)
                return True
            if controles.eh(e, "baixo"):
                self.mover(1)
                return True
            if controles.eh(e, "confirmar"):
                self.escolher()
                return True
            if e.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                passo = self.cabem() * (1 if e.key == pygame.K_PAGEDOWN else -1)
                self.indice = max(0, min(len(self.itens) - 1, self.indice + passo))
                self._mostrar_selecionado()
                return True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and len(self.itens) > self.cabem() \
                and self.trilho().inflate(6, 0).collidepoint(e.pos):
            self._arrasto = e.pos[1] - self.polegar().y           # barra arrastável
            return True
        elif e.type == pygame.MOUSEMOTION and getattr(self, "_arrasto", None) is not None:
            livre = max(1, self.trilho().height - self.polegar().height)
            fracao = (e.pos[1] - self._arrasto - self.trilho().y) / livre
            self._rolar_para(round(fracao * (len(self.itens) - self.cabem())))
            return True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and getattr(self, "_arrasto", None) is not None:
            self._arrasto = None
            return True
        elif e.type == pygame.MOUSEMOTION:
            i = self.item_no_ponto(e.pos)
            if i is not None:
                self.indice = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            i = self.item_no_ponto(e.pos)
            if i is not None:
                self.indice = i
                self.escolher()
                return True
        elif e.type == pygame.MOUSEWHEEL and self.rect.collidepoint(posicao_do_mouse()):
            self.rolagem = max(0, min(len(self.itens) - self.cabem(), self.rolagem - e.y))
            return True
        return False

    def desenhar(self, tela, rect, desenhar_item):
        self.rect = pygame.Rect(rect)
        self.rolagem = max(0, min(self.rolagem, len(self.itens) - self.cabem()))
        anterior = tela.get_clip()
        tela.set_clip(self.rect.clip(anterior))                  # nada da lista vaza da janela dela
        for i in range(self.rolagem, min(len(self.itens), self.rolagem + self.cabem())):
            desenhar_item(tela, self.itens[i], self.area_do_item(i), i == self.indice)
        tela.set_clip(anterior)
        if len(self.itens) > self.cabem():          # barra de rolagem (arrastável)
            trilho = self.trilho()
            pygame.draw.rect(tela, (14, 10, 16), trilho)
            pygame.draw.rect(tela, tema.PEDRA_ESCURA, trilho, 1)
            polegar = self.polegar()
            ativo = getattr(self, "_arrasto", None) is not None or polegar.collidepoint(posicao_do_mouse())
            pygame.draw.rect(tela, tema.OURO_CLARO if ativo else tema.OURO_ESCURO, polegar)
            pygame.draw.rect(tela, (8, 5, 10), polegar, 1)


class Deslizador:
    """Valor de 0 a 1 (volume). Clique na barra põe o valor no ponto clicado."""

    def desenhar(self, tela, rect, valor, selecionado=False):
        rect = pygame.Rect(rect)
        barra(tela, rect, valor, tema.OURO if selecionado else tema.OURO_ESCURO, marcas=10)
        x = rect.x + int(rect.width * valor)
        losango(tela, (x, rect.centery), rect.height // 2 + 4, tema.OURO_CLARO if selecionado else tema.OSSO)
        texto(tela, f"{round(valor * 100)}%", tema.pequena(), tema.TEXTO, (rect.right + 14, rect.centery), "midleft")
        return rect

    @staticmethod
    def valor_no_ponto(rect, x, passo=0.1):
        bruto = (x - rect.x) / max(1, rect.width)
        return round(max(0.0, min(1.0, round(bruto / passo) * passo)), 2)


class AreaClicavel(Botao):
    """Botão invisível (um NPC, um retrato). Só mostra um contorno quando está com o foco."""

    def __init__(self, rect, acao, dica=None, contorno=True):
        super().__init__(rect, "", acao, dica=dica)
        self.contorno = contorno

    def desenhar(self, tela, mouse):
        if self.focado and self.contorno:
            pygame.draw.rect(tela, tema.OURO_CLARO, self.rect, 2)
            for x, y in (self.rect.topleft, self.rect.topright, self.rect.bottomleft, self.rect.bottomright):
                losango(tela, (x, y), 4, tema.OURO)


class DialogoDeConfirmacao:
    """Janela "Tem certeza?" por cima da tela.

    opcoes: lista de (rótulo, ação). A ÚLTIMA é o "cancelar" (usada pelo ESC e com o foco no começo,
    para um Enter distraído nunca fazer nada sem volta).
    """

    LARGURA = 520

    def __init__(self, titulo, mensagem, opcoes):
        self.titulo = titulo
        self.mensagem = mensagem
        self.opcoes = list(opcoes)
        self.indice = len(self.opcoes) - 1
        self.aberto = True
        self.botoes = []

    def escolher(self, indice):
        self.aberto = False
        acao = self.opcoes[indice][1]
        if acao is not None:
            acao()

    def evento(self, e, controles):
        if e.type == pygame.KEYDOWN:
            if controles.eh(e, "voltar"):
                self.escolher(len(self.opcoes) - 1)
            elif controles.eh(e, "esquerda") or controles.eh(e, "cima"):
                self.indice = (self.indice - 1) % len(self.opcoes)
            elif controles.eh(e, "direita") or controles.eh(e, "baixo"):
                self.indice = (self.indice + 1) % len(self.opcoes)
            elif controles.eh(e, "confirmar"):
                self.escolher(self.indice)
        elif e.type == pygame.MOUSEMOTION:
            for i, botao in enumerate(self.botoes):
                if botao.em_cima(e.pos):
                    self.indice = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, botao in enumerate(self.botoes):
                if botao.em_cima(e.pos):
                    self.escolher(i)
                    return
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.escolher(len(self.opcoes) - 1)

    def desenhar(self, tela):
        """Até 3 opções: lado a lado. Mais que isso (menu de ações de um item): uma embaixo da outra."""
        escurecer_tela(tela, 160)
        from ui.desenho import anotar
        anotar("modal", tela.get_rect(), tela, "diálogo")          # (a conferência de layout recomeça aqui)
        from ui.texto import CaixaTexto, linha
        mensagem = CaixaTexto(pygame.Rect(0, 0, self.LARGURA, 300), tema.normal(), alinhamento="centro", padding=24,
                              maximo_linhas=8)
        altura_mensagem = mensagem.altura_para([(self.mensagem, tema.TEXTO)]) if self.mensagem else 0
        empilhar = len(self.opcoes) > 3
        altura_botoes = len(self.opcoes) * 50 + 18 if empilhar else 74
        rect = pygame.Rect(0, 0, self.LARGURA, 54 + altura_mensagem + altura_botoes)
        rect.center = (tela.get_width() // 2, tela.get_height() // 2)
        painel(tela, rect, "sangue")
        linha(tela, self.titulo, tema.media(), tema.TEXTO_TITULO, (rect.centerx, rect.y + 16), rect.width - 48, "midtop")
        if self.mensagem:
            mensagem.rect = pygame.Rect(rect.x, rect.y + 38, rect.width, altura_mensagem)
            mensagem.desenhar(tela, self.mensagem)
        self.botoes = []
        if empilhar:
            caixas = [(rect.x + 40, rect.bottom - altura_botoes + i * 50, rect.width - 80, 44)
                      for i in range(len(self.opcoes))]
        else:
            largura = min(180, (rect.width - 40 - 12 * (len(self.opcoes) - 1)) // len(self.opcoes))
            total = largura * len(self.opcoes) + 12 * (len(self.opcoes) - 1)
            caixas = [(rect.centerx - total // 2 + i * (largura + 12), rect.bottom - 62, largura, 44)
                      for i in range(len(self.opcoes))]
        for i, ((rotulo, _), caixa) in enumerate(zip(self.opcoes, caixas)):
            botao = Botao(caixa, rotulo)
            botao.focado = i == self.indice
            botao.desenhar(tela, (-1, -1))
            self.botoes.append(botao)


class Notificacoes:
    """Avisos rápidos que descem no topo da tela e somem sozinhos."""

    DURACAO = 3.2

    def __init__(self):
        self.fila = []                   # [titulo, texto, cor, tempo]

    def adicionar(self, titulo, conteudo="", cor=tema.OURO_CLARO):
        self.fila.append([titulo, conteudo, cor, 0.0])

    def atualizar(self, dt):
        if self.fila:
            self.fila[0][3] += dt          # uma de cada vez
            if self.fila[0][3] >= self.DURACAO:
                self.fila.pop(0)

    LARGURA_MAXIMA = 620
    ALTURA = 44                          # cabe dentro da faixa do cabeçalho (y 8 a 60): não cobre o conteúdo

    def desenhar(self, tela):
        """Faixa de uma linha só ("Título · texto"), descendo para dentro do cabeçalho das telas."""
        if not self.fila:
            return
        from ui.texto import linha, largura_do_texto
        titulo, conteudo, cor, tempo = self.fila[0]
        entrada = min(1.0, tempo / 0.25, (self.DURACAO - tempo) / 0.35)
        largura_titulo = largura_do_texto(titulo, tema.normal())
        largura_conteudo = largura_do_texto(conteudo, tema.pequena()) if conteudo else 0
        largura = min(self.LARGURA_MAXIMA, max(240, largura_titulo + largura_conteudo + (60 if conteudo else 40)))
        rect = pygame.Rect(0, 0, largura, self.ALTURA)
        rect.midtop = (tela.get_width() // 2, int(-self.ALTURA + (self.ALTURA + 12) * max(0.0, entrada)))
        painel(tela, rect, "ouro")
        interno = rect.inflate(-28, 0)
        if not conteudo:
            linha(tela, titulo, tema.normal(), cor, rect.center, interno.width, "center")
            return
        largura_titulo = min(largura_titulo, interno.width // 2)
        linha(tela, titulo, tema.normal(), cor, (interno.x, rect.centery), largura_titulo, "midleft")
        linha(tela, conteudo, tema.pequena(), tema.TEXTO, (interno.x + largura_titulo + 16, rect.centery),
              interno.width - largura_titulo - 16, "midleft")


class TextoRevelado:
    """Texto que aparece aos poucos. letras_por_segundo=None mostra tudo de uma vez."""

    def __init__(self, conteudo, letras_por_segundo=60):
        self.conteudo = conteudo
        self.letras_por_segundo = letras_por_segundo
        self.tempo = 0.0

    def atualizar(self, dt):
        self.tempo += dt

    def completo(self):
        return self.letras_por_segundo is None or self.tempo * self.letras_por_segundo >= len(self.conteudo)

    def pular(self):
        """Mostra o resto do texto (o jogador apertou confirmar)."""
        self.tempo = float("inf")

    @property
    def visivel(self):
        if self.completo():
            return self.conteudo
        return self.conteudo[:int(self.tempo * self.letras_por_segundo)]


class RegistroRolavel:
    """Lista de mensagens (texto, cor) com quebra de linha. Mostra as mais recentes embaixo;
    a roda do mouse sobre ele rola para ver as antigas (e volta sozinha ao fim quando chega mensagem nova)."""

    def __init__(self, mensagens, fonte=None, padding=10):
        self.mensagens = mensagens              # lista compartilhada (quem registra só faz append)
        self.fonte = fonte or tema.mini()
        self.padding = padding
        self.rolagem = 0                        # quantas linhas acima do fim
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._vistas = 0

    def linhas(self, largura):
        from ui.texto import quebrar_linhas
        return [(linha, cor) for conteudo, cor in self.mensagens for linha in quebrar_linhas(conteudo, self.fonte, largura)]

    def cabem(self):
        return max(1, (self.rect.height - 2 * self.padding) // (self.fonte.get_height() + 1))

    def evento(self, e):
        """Roda do mouse em cima do registro: rola. Devolve True se usou o evento."""
        if e.type == pygame.MOUSEWHEEL and self.rect.collidepoint(posicao_do_mouse()):
            self.rolar(e.y)
            return True
        return False

    def rolar(self, passos):
        total = len(self.linhas(self.rect.width - 2 * self.padding))
        self.rolagem = max(0, min(max(0, total - self.cabem()), self.rolagem + passos))

    def desenhar(self, tela, rect):
        self.rect = pygame.Rect(rect)
        if len(self.mensagens) != self._vistas:  # mensagem nova: volta para o fim
            self._vistas = len(self.mensagens)
            self.rolagem = 0
        linhas = self.linhas(self.rect.width - 2 * self.padding)
        cabem = self.cabem()
        fim = len(linhas) - self.rolagem
        y = self.rect.y + self.padding
        for conteudo, cor in linhas[max(0, fim - cabem):fim]:
            texto(tela, conteudo, self.fonte, cor, (self.rect.x + self.padding, y))
            y += self.fonte.get_height() + 1
        x = self.rect.right - 12
        if fim - cabem > 0:                      # há mensagens mais antigas
            pygame.draw.polygon(tela, tema.OURO, [(x - 4, self.rect.y + 12), (x + 4, self.rect.y + 12), (x, self.rect.y + 7)])
        if self.rolagem > 0:                     # há mensagens mais novas embaixo
            b = self.rect.bottom - 8
            pygame.draw.polygon(tela, tema.OURO, [(x - 4, b - 5), (x + 4, b - 5), (x, b)])
