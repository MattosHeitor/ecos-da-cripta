"""O ambiente na tela de combate (roguelike/ambiente.py, Reino dos Ratos):

    - a água: o cenário troca o chão conforme o nível (poças, depois tudo coberto: CenarioMacabro.alagar); cada
      lutador afunda a partir dos próprios pés (a parte de baixo fica turva e esverdeada) com um anel de ondas onde a
      água corta o corpo; na água rasa, uma poça embaixo de cada um; ondinhas claras andando pelo chão alagado;
    - o escuro por cima da luta, com círculos de luz em volta de quem carrega lanterna ou tocha;
    - o painel no canto de cima: um quadrinho por ambiente (ícone + estado); a dica explica o que ele faz.

Os inimigos ocultos no escuro são desenhados pelo próprio VisualLutador (silhueta e um par de olhos), e os que
boiam ("boia": true na ficha, ex.: ratos) sobem até a superfície da água (VisualLutador.deslocamento_y).
"""

import math

import pygame

from ui import tema
from ui.desenho import painel, icone_status
from ui.texto import linha, largura_do_texto

ALTURA_DA_AGUA = (0, 12, 30, 56)            # quanto os lutadores afundam, por nível (Seca, Rasa, Funda, Alta)
HORIZONTE = 472                             # onde começa o chão dos cenários na tela (y 118 x 4)
TURVO = (112, 150, 124, 205)                # a parte de baixo da linha d'água (multiplica as cores e a opacidade)
MAIS_FUNDO = (150, 170, 160, 190)           # e mais ainda a partir de 14 px abaixo dela
ONDA = (150, 214, 150)
POCA = (22, 50, 34)
ESCURO = (4, 4, 10)
ICONES = {"agua": "encharcado", "escuridao": "escuridao"}
CORES = {"agua": (140, 210, 160), "escuridao": (190, 180, 230)}


class VisualDoAmbiente:
    def __init__(self, combate, chao, fundo_y):
        self.combate = combate
        self.chao = chao                    # y dos pés dos lutadores
        self.fundo_y = fundo_y              # onde começa o painel de baixo
        self.tempo = 0.0
        self.altura_agua = float(self.altura_alvo())
        self.camada = None                  # rascunho do tamanho da tela (para afundar um lutador de cada vez)
        self._reflexos = {}                 # imagem já virada e tingida, por quadro

    def do_tipo(self, tipo):
        return next((a for a in self.combate.ambientes if a.tipo == tipo), None)

    def altura_alvo(self):
        agua = self.do_tipo("agua")
        return ALTURA_DA_AGUA[agua.nivel] if agua else 0

    def atualizar(self, dt):
        self.tempo += dt
        self.altura_agua += (self.altura_alvo() - self.altura_agua) * min(1.0, dt * 2.0)

    def alagado(self):
        return self.altura_agua > 1

    def nivel_da_agua(self):
        """O nível com fração (a água sobe devagar entre dois níveis): o cenário mistura os dois chãos."""
        for k in range(len(ALTURA_DA_AGUA) - 1):
            baixo, cima = ALTURA_DA_AGUA[k], ALTURA_DA_AGUA[k + 1]
            if self.altura_agua <= cima:
                return k + max(0.0, self.altura_agua - baixo) / (cima - baixo)
        return float(len(ALTURA_DA_AGUA) - 1)

    def superficie(self, visual=None):
        """y da superfície da água na tela (None sem água): os bichos que boiam ficam nela. Cada lutador afunda a
        partir dos próprios pés (fileira da frente e de trás)."""
        if not self.alagado():
            return None
        pes = visual.alvo_y if visual is not None else self.chao
        return pes - self.altura_agua

    # ---------------- na cena ----------------
    def desenhar_brilho(self, tela):
        """Ondinhas claras andando devagar pelo chão alagado (água funda e alta), mais largas perto da câmera."""
        if self.nivel_da_agua() < 1.5:
            return
        largura = tela.get_width()
        camada = pygame.Surface((largura, self.fundo_y - HORIZONTE), pygame.SRCALPHA)
        for k in range(46):
            z = ((k * 37) % 46) / 46                                         # 0 = lá no fundo, 1 = perto
            y = int((self.fundo_y - HORIZONTE) * z ** 1.4)
            x = int((k * 233 + self.tempo * (8 + 22 * z) * (1 if k % 2 else -1)) % (largura + 60)) - 30
            brilho = 0.5 + 0.5 * math.sin(self.tempo * 1.7 + k * 1.3)
            camada.fill((*ONDA, int(30 + 70 * brilho)), (x, y, int(8 + 18 * z), 2))
        tela.blit(camada, (0, HORIZONTE))

    def desenhar_lutador(self, tela, visual, destaque=None):
        """O lutador na água: a parte abaixo da linha d'água fica turva, com o anel de ondas (fora da água, normal)."""
        if not self.alagado() or getattr(visual, "no_ar", False) or visual.alfa <= 0:
            visual.desenhar(tela, destaque)
            return
        corpo = visual.caixa()
        coluna = pygame.Rect(corpo.x - corpo.width // 2 - 60, 0, corpo.width * 2 + 120, corpo.bottom + 60)
        self.desenhar_na_agua(tela, lambda superficie: visual.desenhar(superficie, destaque), coluna,   # (golpes e
                              visual.y, corpo.width, corpo.centerx)                    # braços erguidos saem da caixa)

    def desenhar_poca_ou_sombra(self, visual, tela):
        """Na água rasa o chão tem poças: cada lutador ganha uma poça embaixo (na funda, nem sombra)."""
        if not self.alagado() or getattr(visual, "no_ar", False):
            visual.desenhar_sombra(tela)
            return
        if self.nivel_da_agua() > 1.5 or visual.alfa < 40:
            return
        largura = max(60, int(visual.largura() * 0.9))
        poca = pygame.Surface((largura, max(12, largura // 5)), pygame.SRCALPHA)
        pygame.draw.ellipse(poca, (*POCA, 190), poca.get_rect())
        pygame.draw.ellipse(poca, (*ONDA, 70), poca.get_rect(), 2)
        tela.blit(poca, (round(visual.x - largura / 2), round(visual.y - poca.get_height() / 2)))

    def desenhar_na_agua(self, tela, desenhar, area, pes, largura, centro_x, fator=1.0, anel=True):
        """Desenha algo de pé na água: desenhar(superfície) pinta numa camada de rascunho; o que fica abaixo da linha
        d'água (pes - fundura) sai turvo e esverdeado, e um anel de ondas marca onde a água corta o corpo."""
        fundura = self.altura_agua * fator
        area = area.clip(tela.get_rect())
        if fundura <= 1 or area.width <= 0 or area.height <= 0:
            desenhar(tela)
            return
        if self.camada is None or self.camada.get_size() != tela.get_size():
            self.camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        self.camada.fill((0, 0, 0, 0), area)
        desenhar(self.camada)
        linha_dagua = round(pes - fundura)
        for topo, cor in ((linha_dagua, TURVO), (linha_dagua + 14, MAIS_FUNDO)):
            baixo = pygame.Rect(area.x, topo, area.width, area.bottom - topo).clip(area)
            if baixo.height > 0:
                self.camada.subsurface(baixo).fill(cor, special_flags=pygame.BLEND_RGBA_MULT)
        tela.blit(self.camada, area.topleft, area)
        if anel:
            self.desenhar_anel(tela, centro_x, linha_dagua, max(36, int(largura * 0.75)))

    def desenhar_reflexo(self, tela, imagem, x, topo, chave):
        """Reflexo na água funda e alta (ex.: o trono): a imagem de cabeça para baixo, escura e esverdeada, sumindo
        para baixo e tremendo em faixas. topo = onde a água encosta na base do que reflete."""
        nivel = self.nivel_da_agua()
        if nivel < 1.2:
            return
        if self._reflexos.get(chave) is None:
            reflexo = pygame.transform.flip(imagem, False, True)
            reflexo.fill((80, 120, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
            altura = reflexo.get_height()
            some = pygame.Surface(reflexo.get_size(), pygame.SRCALPHA)
            for y in range(0, altura, 2):
                some.fill((255, 255, 255, int(150 * max(0.0, 1 - y / (altura * 0.6)))), (0, y, reflexo.get_width(), 2))
            reflexo.blit(some, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self._reflexos[chave] = reflexo
        reflexo = self._reflexos[chave]
        forca = int(255 * min(1.0, (nivel - 1.2) / 0.8))
        for y in range(0, reflexo.get_height(), 4):                             # faixas tremidas
            if topo + y >= self.fundo_y:
                break
            dx = round(math.sin(self.tempo * 2.2 + y * 0.35) * 2)
            faixa = reflexo.subsurface((0, y, reflexo.get_width(), min(4, reflexo.get_height() - y)))
            faixa.set_alpha(forca)
            tela.blit(faixa, (x + dx, topo + y))

    def desenhar_anel(self, tela, x, y, largura):
        """O anel de ondas em volta de quem está na água (dois anéis que se abrem devagar)."""
        altura = max(8, largura // 5)
        anel = pygame.Surface((largura + 24, altura + 10), pygame.SRCALPHA)
        for k in range(2):
            fase = (self.tempo * 0.6 + k * 0.5) % 1.0
            rect = pygame.Rect(0, 0, int(largura * (0.75 + 0.3 * fase)), int(altura * (0.75 + 0.3 * fase)))
            rect.center = anel.get_rect().center
            pygame.draw.ellipse(anel, (*ONDA, int(150 * (1 - fase))), rect, 2)
        tela.blit(anel, (round(x - anel.get_width() / 2), round(y - anel.get_height() / 2)))

    def desenhar_escuro(self, tela, visual_de):
        """O escuro por cima da luta; quem carrega luz abre um círculo em volta de si (visual_de: lutador -> visual)."""
        escuridao = self.do_tipo("escuridao")
        if escuridao is None:
            return
        portadores = escuridao.portadores_de_luz(self.combate)
        camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        camada.fill((*ESCURO, 140 if portadores else 160))
        for heroi in portadores:
            visual = visual_de(heroi)
            if visual is None:
                continue
            cx, cy = visual.centro()
            tremor = math.sin(self.tempo * 9 + cx) * 4
            for raio, alfa in ((240, 88), (180, 52), (120, 18)):              # o círculo de luz em degraus
                pygame.draw.circle(camada, (*ESCURO, alfa), (int(cx), int(cy)), int(raio + tremor))
        tela.blit(camada, (0, 0))

    # ---------------- painel ----------------
    def desenhar_painel(self, tela, x, y, mouse):
        """Um quadrinho por ambiente. Devolve a dica (título, texto) do que está sob o mouse, ou None."""
        dica = None
        for ambiente in self.combate.ambientes:
            rotulo = ambiente.resumo(self.combate)
            largura = min(300, largura_do_texto(rotulo, tema.mini()) + 44)
            rect = pygame.Rect(x, y, largura, 28)
            painel(tela, rect, "pedra")
            tela.blit(icone_status(ICONES.get(ambiente.tipo, "cego"), 2), (rect.x + 6, rect.y + 5))
            linha(tela, rotulo, tema.mini(), CORES.get(ambiente.tipo, tema.TEXTO), (rect.x + 30, rect.centery),
                  largura - 36, "midleft")
            if rect.collidepoint(mouse):
                dica = (ambiente.nome, ambiente.descricao(self.combate))
            y += 32
        return dica
