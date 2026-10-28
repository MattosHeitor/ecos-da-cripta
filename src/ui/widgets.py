"""Botões e caixas de dica (tooltip)."""

import pygame

from ui import tema
from ui.desenho import painel, texto, moldura


class Botao:
    """Botão com moldura gótica. Clique, atalho de teclado e dica ao passar o mouse.

    - acao: função chamada ao clicar (ou None);
    - atalho: texto mostrado no canto (ex.: "1");
    - dica: (título, texto) mostrado ao passar o mouse (ou com o foco do teclado);
    - ativo=False: aparece apagado e não responde;
    - focado: o "cursor" do teclado está nele (a tela marca isso a cada quadro).
    """

    def __init__(self, rect, texto_botao, acao=None, atalho=None, ativo=True, dica=None, subtexto=None,
                 cor_texto=tema.TEXTO, estilo="ferro", selecionado=False):
        self.rect = pygame.Rect(rect)
        self.texto = texto_botao
        self.acao = acao
        self.atalho = atalho
        self.ativo = ativo
        self.dica = dica
        self.subtexto = subtexto
        self.cor_texto = cor_texto
        self.estilo = estilo
        self.selecionado = selecionado   # marcado (aba atual, item escolhido): passe ANTES de desenhar
        self.focado = False
        self.focavel = True              # False: só o mouse alcança (atalhos secundários)
        self.mostrar_rotulo = True       # False: a tela desenha o conteúdo por cima (o texto continua no botão)
        self.fontes = None               # fontes permitidas no rótulo (None: a maior que couber)
        self.painel = None               # PainelRolavel em que o botão está (a tela marca)
        self.recorte = None              # janela visível: fora dela o botão não responde ao mouse
        self._chave_foco = None

    @property
    def chave_foco(self):
        """Identidade do botão para o foco do teclado (no painel rolável não muda ao rolar)."""
        return self._chave_foco if self._chave_foco is not None else tuple(self.rect)

    @chave_foco.setter
    def chave_foco(self, valor):
        self._chave_foco = valor

    def em_cima(self, posicao):
        return self.rect.collidepoint(posicao) and (self.recorte is None or self.recorte.collidepoint(posicao))

    def clicar(self, posicao):
        """Chama a ação se o clique foi no botão. Devolve True se usou o clique."""
        if self.ativo and self.em_cima(posicao) and self.acao is not None:
            self.acao()
            return True
        return False

    def estado(self, mouse):
        """"desativado", "pressionado" (mouse apertado em cima), "destaque" (selecionado, foco, mouse) ou "normal"."""
        if not self.ativo:
            return "desativado"
        em_cima = self.em_cima(mouse)
        if em_cima and pygame.mouse.get_pressed()[0]:
            return "pressionado"
        if self.selecionado or self.focado or em_cima:
            return "destaque"
        return "normal"

    def desenhar(self, tela, mouse):
        estado = self.estado(mouse)
        estilo = {"desativado": "desativado", "pressionado": "pressionado", "destaque": "ouro"}.get(estado, self.estilo)
        if estado == "desativado" and self.estilo == "ouro":
            estilo = "desativado"
        painel(tela, self.rect, estilo)
        cor = {"desativado": tema.TEXTO_APAGADO, "destaque": tema.OURO_CLARO, "pressionado": tema.OURO}.get(
            estado, self.cor_texto)
        if estado == "pressionado":                       # o rótulo afunda junto com o botão
            self.rect.move_ip(0, 2)
            self.desenhar_rotulo(tela, cor)
            self.rect.move_ip(0, -2)
        else:
            self.desenhar_rotulo(tela, cor)
        if self.atalho:
            texto(tela, self.atalho, tema.mini(), tema.OURO if self.ativo else tema.TEXTO_APAGADO,
                  (self.rect.x + 7, self.rect.y + 4))

    def desenhar_rotulo(self, tela, cor):
        """Rótulo centralizado com margem (CaixaTexto: diminui a fonte ou quebra em 2 linhas se precisar).
        O subtexto fica numa faixa própria embaixo, sem encostar no rótulo."""
        from ui.texto import CaixaTexto
        from ui.molduras import borda_interna
        if not self.mostrar_rotulo or (not self.texto and not self.subtexto):
            return
        borda = borda_interna(self.rect.width, self.rect.height)       # o rótulo não encosta na madeira
        # espaço do atalho no canto (dos dois lados, para o rótulo continuar centralizado)
        margem = max(22, tema.mini().size(self.atalho)[0] + 12) if self.atalho else borda + 2
        vertical = 5 if borda <= 8 else borda - 2                       # o texto fica dentro do filete dourado
        area = pygame.Rect(self.rect.x + margem, self.rect.y + vertical, self.rect.width - 2 * margem,
                           self.rect.height - 2 * vertical)
        if self.subtexto:
            altura_sub = tema.mini().get_height()
            sub = pygame.Rect(area.x, area.bottom - altura_sub, area.width, altura_sub)
            CaixaTexto(sub, tema.mini(), alinhamento="centro", vertical="base", maximo_linhas=1).desenhar(
                tela, self.subtexto, tema.TEXTO_FRACO if self.ativo else tema.TEXTO_APAGADO)
            area.height -= altura_sub
        if self.texto:
            # a maior fonte cuja linha cabe na altura que sobra (a CaixaTexto ainda quebra/diminui pela largura)
            permitidas = self.fontes or (tema.normal(), tema.pequena(), tema.mini())
            candidatas = [f for f in permitidas if f.get_height() <= area.height]
            fontes = candidatas or [tema.mini()]
            CaixaTexto(area, fontes[0], cor, alinhamento="centro", vertical="meio", espaco=0, fontes=fontes).desenhar(
                tela, self.texto)


class CampoDeTexto:
    """Caixa onde o jogador digita (semente, nome do herói, chat).

    As letras vêm do TEXTINPUT do SDL (acentos do teclado brasileiro: ´ + a = á). O KEYDOWN também traz a letra
    (é o que os testes mandam); quando o TEXTINPUT da mesma tecla chega logo depois, ele SUBSTITUI o que o KEYDOWN
    pôs (assim nada sai dobrado, e o "á" entra no lugar do "a"). enviar_com_enter: o Enter não sai do campo
    (o chat lê 'enviado' e limpa)."""

    def __init__(self, rect, conteudo="", maximo=14, maiusculas=False, rotulo="", dica="", enviar_com_enter=False):
        self.rect = pygame.Rect(rect)
        self.conteudo = conteudo
        self.maximo = maximo
        self.maiusculas = maiusculas
        self.rotulo = rotulo
        self.dica = dica                     # texto apagado no campo vazio ("Seu nome")
        self.enviar_com_enter = enviar_com_enter
        self.ativo = False
        self.enviado = None                  # o que estava escrito quando apertaram Enter (enviar_com_enter)
        self._da_ultima_tecla = ""           # o que o último KEYDOWN pôs (o TEXTINPUT da mesma tecla troca)

    def _inserir(self, letras):
        letras = "".join(c for c in letras if c.isprintable())
        if self.maiusculas:
            letras = letras.upper()
        self.conteudo += letras[:max(0, self.maximo - len(self.conteudo))]

    def evento(self, e):
        """Devolve True se o evento foi usado pelo campo."""
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.ativo = self.rect.collidepoint(e.pos)
            self._da_ultima_tecla = ""
            return self.ativo
        if not self.ativo:
            return False
        if e.type == pygame.TEXTINPUT:
            ultima, self._da_ultima_tecla = self._da_ultima_tecla, ""
            if ultima and (e.text == ultima or len(e.text) == 1):       # a mesma tecla (ou a letra composta)
                self.conteudo = self.conteudo[:-len(ultima)]
            self._inserir(e.text)
            return True
        if e.type != pygame.KEYDOWN:
            return False
        self._da_ultima_tecla = ""
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.enviar_com_enter:
            self.enviado, self.conteudo = self.conteudo, ""
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_TAB):
            self.ativo = False
        elif e.key == pygame.K_BACKSPACE:
            self.conteudo = self.conteudo[:-1]
        elif e.unicode and e.unicode.isprintable():
            antes = len(self.conteudo)
            self._inserir(e.unicode)
            self._da_ultima_tecla = self.conteudo[antes:]
        return True

    def pegar_enviado(self):
        enviado, self.enviado = self.enviado, None
        return enviado

    def desenhar(self, tela, mouse, tempo=0.0, fonte=None):
        from ui.texto import linha
        estilo = "ouro" if self.ativo or self.rect.collidepoint(mouse) else "pedra"
        painel(tela, self.rect, estilo)
        if self.rotulo:
            texto(tela, self.rotulo, tema.mini(), tema.TEXTO_FRACO, (self.rect.x + 4, self.rect.y - 4), "bottomleft")
        fonte = fonte or tema.normal()
        cursor = "_" if self.ativo and int(tempo * 2) % 2 == 0 else ""
        if not self.conteudo and self.dica and not self.ativo:
            linha(tela, self.dica, fonte, tema.TEXTO_APAGADO, (self.rect.x + 12, self.rect.centery),
                  self.rect.width - 24, "midleft")
            return
        mostrado = self.conteudo + cursor
        largura = self.rect.width - 24
        while mostrado and fonte.size(mostrado)[0] > largura:      # texto comprido: mostra o fim (onde se digita)
            mostrado = mostrado[1:]
        texto(tela, mostrado or " ", fonte, tema.TEXTO, (self.rect.x + 12, self.rect.centery), "midleft")


def desenhar_dica(tela, posicao, titulo, conteudo, largura=300, cor_titulo=tema.TEXTO_TITULO):
    """Caixa de dica perto do mouse (sem sair da tela). Ver também ui.componentes.Tooltip.
    conteudo: um texto ou uma lista de trechos [(texto, cor)] (ex.: o que melhora em verde e o que piora em vermelho)."""
    from ui.texto import CaixaTexto, linha
    corpo = CaixaTexto(pygame.Rect(0, 0, largura, 400), tema.pequena(), padding=12, maximo_linhas=18)
    trechos = conteudo if isinstance(conteudo, list) else [(conteudo, tema.TEXTO)]
    altura_corpo = corpo.altura_para(trechos) - 12 if conteudo else 0
    altura = 16 + tema.normal().get_height() + altura_corpo + 6
    x, y = posicao[0] + 18, posicao[1] + 18
    if x + largura > tela.get_width() - 4:
        x = posicao[0] - largura - 12
    if posicao[1] > tela.get_height() * 0.75:
        # Perto do painel de baixo: a dica aparece em cima dele (para não cobrir os botões)
        y = int(tela.get_height() * 0.81) - altura
    elif y + altura > tela.get_height() - 4:
        y = tela.get_height() - altura - 4
    x, y = max(4, x), max(4, y)
    rect = pygame.Rect(x, y, largura, altura)
    tela.blit(moldura(rect.width, rect.height, "pedra"), rect.topleft)
    from ui.desenho import anotar
    anotar("modal", rect, tela)                      # (conferência: a dica cobre o que está embaixo, de propósito)
    anotar("camada", rect, tela, "dica")             # fica por cima de tudo (de propósito)
    linha(tela, titulo, tema.normal(), cor_titulo, (x + 12, y + 10), largura - 24)
    if conteudo:
        corpo.rect = pygame.Rect(x, y + 2 + tema.normal().get_height(), largura, altura_corpo + 12)
        corpo.desenhar(tela, conteudo)
    return rect
