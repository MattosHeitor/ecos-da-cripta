"""Painel rolável: uma janela (moldura) por onde o conteúdo comprido passa, sempre recortado nela.

    self.lista = PainelRolavel()                      # guardado na tela (lembra a posição da rolagem)
    ...
    with self.rolavel(self.lista, area, altura_total) as y0:     # TelaComBotoes.rolavel
        for i, item in enumerate(itens):
            self.botao(Botao((area.x, y0 + i * 54, largura, 50), ...))

- Roda do mouse em cima rola; a barra da direita pode ser arrastada (ou clicada para pular uma página);
  PageUp/PageDown/Home/End rolam o painel do foco (ou o que está sob o mouse).
- Tudo o que é desenhado entre comecar() e terminar() fica recortado na janela: nada vaza.
- mostrar(rect) rola até um retângulo (o botão focado pelo teclado nunca fica escondido).
- A rolagem anda suave até o alvo.
"""

import pygame

from ui import tema
from ui.escala import posicao_do_mouse

LARGURA_BARRA = 8
FOLGA_BARRA = 6                   # espaço entre o conteúdo e a barra
POLEGAR_MINIMO = 24
SUAVIDADE = 0.45                  # fração do caminho até o alvo andada a cada quadro


class PainelRolavel:
    def __init__(self, passo=56):
        self.passo = passo                    # pixels por "clique" da roda do mouse
        self.rect = pygame.Rect(0, 0, 0, 0)   # a janela na tela
        self.altura_conteudo = 0
        self.deslocamento = 0.0               # quanto do conteúdo já subiu (animado)
        self.alvo = 0.0
        self.arrastando = None                # distância do mouse ao topo do polegar, durante o arraste
        self._recortes = []

    # ---------------- medidas ----------------
    @property
    def maximo(self):
        return max(0, self.altura_conteudo - self.rect.height)

    @property
    def rola(self):
        """True se o conteúdo é maior que a janela (aí aparece a barra)."""
        return self.maximo > 0

    @staticmethod
    def largura_util(rect, altura_conteudo):
        """Largura que sobra para o conteúdo (desconta a barra se ela vai aparecer)."""
        rect = pygame.Rect(rect)
        return rect.width - (LARGURA_BARRA + FOLGA_BARRA if altura_conteudo > rect.height else 0)

    def _limitar(self):
        self.alvo = max(0.0, min(float(self.maximo), self.alvo))
        self.deslocamento = max(0.0, min(float(self.maximo), self.deslocamento))

    def trilho(self):
        return pygame.Rect(self.rect.right - LARGURA_BARRA, self.rect.y, LARGURA_BARRA, self.rect.height)

    def polegar(self):
        trilho = self.trilho()
        altura = max(POLEGAR_MINIMO, trilho.height * self.rect.height // max(1, self.altura_conteudo))
        y = trilho.y + (trilho.height - altura) * self.deslocamento / max(1, self.maximo)
        return pygame.Rect(trilho.x, round(y), LARGURA_BARRA, altura)

    # ---------------- movimento ----------------
    def rolar(self, pixels):
        self.alvo += pixels
        self._limitar()

    def ir_para(self, y, imediato=False):
        self.alvo = float(y)
        self._limitar()
        if imediato:
            self.deslocamento = self.alvo

    def mostrar(self, rect, margem=8):
        """Rola o mínimo para o retângulo (em coordenadas da tela, já deslocado) ficar todo visível."""
        rect = pygame.Rect(rect)
        topo_conteudo = rect.y - self.rect.y + self.deslocamento
        if rect.height + 2 * margem >= self.rect.height or topo_conteudo - margem < self.alvo:
            self.alvo = topo_conteudo - margem
        elif topo_conteudo + rect.height + margem > self.alvo + self.rect.height:
            self.alvo = topo_conteudo + rect.height + margem - self.rect.height
        self._limitar()

    def visivel(self, rect):
        """O retângulo (da tela) está inteiro dentro da janela?"""
        return self.rect.contains(pygame.Rect(rect))

    # ---------------- eventos ----------------
    def evento(self, e):
        """Roda, arraste e clique na barra. Devolve True se usou o evento."""
        if e.type == pygame.MOUSEWHEEL and self.rola and self.rect.collidepoint(posicao_do_mouse()):
            self.rolar(-e.y * self.passo)
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rola and self.trilho().inflate(6, 0).collidepoint(e.pos):
            polegar = self.polegar()
            if polegar.inflate(6, 0).collidepoint(e.pos):
                self.arrastando = e.pos[1] - polegar.y
            else:                                         # clique no trilho: pula uma página
                self.rolar(self.rect.height * (1 if e.pos[1] > polegar.centery else -1))
            return True
        if e.type == pygame.MOUSEMOTION and self.arrastando is not None:
            trilho = self.trilho()
            livre = max(1, trilho.height - self.polegar().height)
            self.ir_para((e.pos[1] - self.arrastando - trilho.y) / livre * self.maximo, imediato=True)
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.arrastando is not None:
            self.arrastando = None
            return True
        return False

    def tecla(self, e):
        """PageUp/PageDown/Home/End. Devolve True se usou a tecla."""
        if e.type != pygame.KEYDOWN or not self.rola:
            return False
        if e.key == pygame.K_PAGEUP:
            self.rolar(-self.rect.height + self.passo // 2)
        elif e.key == pygame.K_PAGEDOWN:
            self.rolar(self.rect.height - self.passo // 2)
        elif e.key == pygame.K_HOME:
            self.ir_para(0)
        elif e.key == pygame.K_END:
            self.ir_para(self.maximo)
        else:
            return False
        return True

    # ---------------- desenho ----------------
    def comecar(self, tela, rect, altura_conteudo):
        """Abre o recorte na janela e devolve o y onde o conteúdo começa (já rolado)."""
        self.rect = pygame.Rect(rect)
        self.altura_conteudo = int(altura_conteudo)
        self._limitar()
        if self.arrastando is None:
            falta = self.alvo - self.deslocamento
            self.deslocamento = self.alvo if abs(falta) < 1 else self.deslocamento + falta * SUAVIDADE
        anterior = tela.get_clip()
        self._recortes.append(anterior)
        tela.set_clip(self.rect.clip(anterior))
        return self.rect.y - round(self.deslocamento)

    def terminar(self, tela):
        """Fecha o recorte e desenha a barra (só se o conteúdo não coube)."""
        tela.set_clip(self._recortes.pop() if self._recortes else None)
        if not self.rola:
            return
        trilho = self.trilho()
        pygame.draw.rect(tela, (14, 10, 16), trilho)
        pygame.draw.rect(tela, tema.PEDRA_ESCURA, trilho, 1)
        polegar = self.polegar()
        ativo = self.arrastando is not None or polegar.inflate(6, 0).collidepoint(posicao_do_mouse())
        pygame.draw.rect(tela, tema.OURO_CLARO if ativo else tema.OURO_ESCURO, polegar)
        pygame.draw.rect(tela, (8, 5, 10), polegar, 1)
        if self.deslocamento > 1:                         # setinhas no trilho: há mais em cima / embaixo
            _seta(tela, (trilho.centerx, trilho.y + 1), -1)
        if self.deslocamento < self.maximo - 1:
            _seta(tela, (trilho.centerx, trilho.bottom - 2), 1)


def _seta(tela, ponta, sentido):
    x, y = ponta
    pygame.draw.polygon(tela, tema.OURO_CLARO, [(x - 3, y - 3 * sentido), (x + 3, y - 3 * sentido), (x, y)])
