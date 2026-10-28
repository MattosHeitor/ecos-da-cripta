"""Visual de cada lutador na arena: sprite animado, posição, investida, piscar e barra de vida.

O VisualLutador só DESENHA: quem decide o que acontece é o Combate
(roguelike/combate.py). A tela lê os eventos e chama investir(), levar_golpe()...
"""

import math

import pygame

from ui import tema
from ui.desenho import barra, icone_status, texto, pontos_de_energia
from visual.sprites_macabros import Animador

# Heróis corrompidos (sprites de herói usados por inimigos) ficam avermelhados
COR_CORROMPIDO = (170, 70, 80)
COR_SOMBRA = (34, 20, 64)    # Sombras do Herói (Catedral do Eclipse): cópias escuras de um herói do grupo
LARGURA_MAXIMA = 330          # sprites mais largos que isso são desenhados em tamanho 1x
AFUNDA_NA_AGUA = 10           # quem boia ("boia" na ficha) fica com os pés este tanto abaixo da superfície


def suave(p):
    return p * p * (3 - 2 * p)


class VisualLutador:
    TEMPO_IDA, TEMPO_PARADO, TEMPO_VOLTA = 0.16, 0.12, 0.2

    def __init__(self, lutador, sprites, inimigo):
        self.lutador = lutador
        self.sprites = sprites
        self.inimigo = inimigo                       # inimigos olham para a esquerda
        self.sprite_base = lutador.sprite if sprites.existe(lutador.sprite) else "esqueleto"
        self.usar_sprite(self.sprite_base)
        if sprites.tem_animacao(self.nome_sprite, "despertar"):
            self.animador.tocar("despertar")         # gárgula: a estátua ganha vida ao entrar na luta
        corrompido = inimigo and sprites.meta(self.nome_sprite).get("familia") == "herois"
        self.tinta = COR_SOMBRA if getattr(lutador, "sombra_de", None) else COR_CORROMPIDO if corrompido else None

        self.x = self.y = 0.0                        # posição atual dos pés
        self.alvo_x = self.alvo_y = 0.0              # para onde está indo (reorganizar a fila)
        self.investida = None                        # (início, deslocamento x)
        self.recuo = None                            # (início, direção) ao esquivar
        self.piscar_ate = -1.0
        self.tremer_ate = -1.0
        self.tempo = 0.0
        self.vida_mostrada = float(lutador.vida)    # a barra desce devagar
        self.alfa = 255
        self.aparecendo = 0.0                        # invocações surgem aos poucos (0 a 1)
        self.sumindo = False
        self.morto_desde = None
        self.topo_da_barra = 0                       # onde termina o que foi desenhado em cima da barra
        self.areas_de_status = []                    # (retângulo, status) dos ícones, para as dicas
        self.mudou_de_tamanho = False
        self.oculto = False                          # no escuro, sem luz (a tela atualiza a cada quadro)
        self.superficie_da_agua = None               # y da água (Reino dos Ratos; a tela atualiza a cada quadro)
        self.boia = 0.0                              # quanto subiu para boiar na água (negativo = para cima)

    def usar_sprite(self, nome):
        """Troca a folha desenhada (no começo e nas transformações, ex.: Forma de Dragão)."""
        self.nome_sprite = nome
        self.animador = Animador(self.sprites, nome)
        self.animador.tempo = (id(self.lutador) % 100) / 37      # cada um respira num ritmo
        # Chefes podem ser maiores (ficam sozinhos do lado deles)
        limite = 520 if getattr(self.lutador, "eh_chefe", False) else LARGURA_MAXIMA
        self.escala = 2 if self.sprites.caixa(nome, 2).width <= limite else 1

    def acompanhar_transformacao(self):
        if not self.lutador.esta_vivo():
            return                                   # caído: mantém a animação de morte
        desejado = self.lutador.sprite_atual()
        if not self.sprites.existe(desejado):
            desejado = self.sprite_base
        if desejado != self.nome_sprite:
            self.usar_sprite(desejado)
            self.piscar_ate = self.tempo + 0.25
            self.mudou_de_tamanho = True             # a tela reorganiza as fileiras

    # ============================================================
    # POSIÇÃO E MEDIDAS
    # ============================================================

    def colocar(self, x, y, imediato=False):
        self.alvo_x, self.alvo_y = x, y
        if imediato:
            self.x, self.y = x, y

    def caixa(self):
        """Retângulo do corpo na tela (para clicar e posicionar barras)."""
        rel = self.sprites.caixa(self.nome_sprite, self.escala)
        if self.inimigo:
            rel = pygame.Rect(-rel.right, rel.y, rel.width, rel.height)
        return rel.move(round(self.x + self.deslocamento_x()), round(self.y + self.deslocamento_y()))

    def largura(self):
        return self.sprites.caixa(self.nome_sprite, self.escala).width

    def centro(self):
        return self.caixa().center

    def topo(self):
        return self.caixa().top

    # ============================================================
    # ANIMAÇÕES
    # ============================================================

    def investir(self, alvo_x):
        """Corre até perto do alvo, bate e volta."""
        distancia = alvo_x - self.x
        # para um pouco antes do alvo (não entra no corpo dele)
        parar = distancia - math.copysign(min(abs(distancia), 90), distancia)
        self.investida = (self.tempo, parar * 0.9)
        self.animador.tocar("ataque")

    def tempo_ate_o_golpe(self):
        return self.TEMPO_IDA + self.TEMPO_PARADO * 0.3

    def atacar_parado(self):
        self.animador.tocar("ataque")

    def tocar_linha(self, nome):
        """Toca uma linha própria do sprite (ex.: o "decreto" do Rei dos Ratos). False se ele não tem essa linha."""
        if not self.sprites.tem_animacao(self.nome_sprite, nome):
            return False
        self.animador.tocar(nome)
        return True

    def levar_golpe(self, forte=False):
        if self.lutador.esta_vivo():
            self.animador.tocar("dano")
        self.piscar_ate = self.tempo + 0.1
        if forte:
            self.tremer_ate = self.tempo + 0.25

    def esquivar(self):
        self.recuo = (self.tempo, 1 if self.inimigo else -1)

    def morrer(self):
        self.animador.tocar("morte")
        self.morto_desde = self.tempo

    def reviver(self):
        self.animador.reviver()
        self.morto_desde = None
        self.sumindo = False
        self.alfa = 255

    def surgir(self):
        self.aparecendo = 0.01

    def sumir(self):
        self.sumindo = True

    def deslocamento_x(self):
        dx = 0.0
        if self.investida is not None:
            inicio, distancia = self.investida
            t = self.tempo - inicio
            if t < self.TEMPO_IDA:
                dx = distancia * suave(t / self.TEMPO_IDA)
            elif t < self.TEMPO_IDA + self.TEMPO_PARADO:
                dx = distancia
            elif t < self.TEMPO_IDA + self.TEMPO_PARADO + self.TEMPO_VOLTA:
                dx = distancia * (1 - suave((t - self.TEMPO_IDA - self.TEMPO_PARADO) / self.TEMPO_VOLTA))
        if self.recuo is not None:
            inicio, direcao = self.recuo
            t = self.tempo - inicio
            if t < 0.3:
                dx += direcao * 34 * math.sin(t / 0.3 * math.pi)
        if self.tempo < self.tremer_ate:
            dx += math.sin(self.tempo * 90) * 4
        return dx

    def deslocamento_y(self):
        """Na água, quem boia sobe até a superfície (e balança de leve)."""
        if self.boia > -1:
            return 0.0
        return self.boia + math.sin(self.tempo * 2.4 + id(self.lutador) % 5) * 1.5

    def boia_na_agua(self):
        """Boia quem tem "boia" na ficha, está vivo e não está submerso (o Rato Nadador mergulha)."""
        ficha = getattr(self.lutador, "ficha", None) or {}
        return ficha.get("boia", False) and self.lutador.esta_vivo() and not self.oculto

    def ocupado(self):
        if self.investida is not None and self.tempo - self.investida[0] < self.TEMPO_IDA + self.TEMPO_PARADO + self.TEMPO_VOLTA:
            return True
        return False

    def atualizar(self, dt):
        self.tempo += dt
        self.acompanhar_transformacao()
        self.animador.atualizar(dt)
        # anda até a posição nova (quando a fila se reorganiza)
        self.x += (self.alvo_x - self.x) * min(1, dt * 8)
        self.y += (self.alvo_y - self.y) * min(1, dt * 8)
        # barra de vida "atrasada"
        self.vida_mostrada += (self.lutador.vida - self.vida_mostrada) * min(1, dt * 3)
        alvo = 0.0                                   # boiar: sobe até a água (caído, afunda de volta)
        if self.superficie_da_agua is not None and self.boia_na_agua():
            alvo = min(0.0, self.superficie_da_agua + AFUNDA_NA_AGUA - self.y)
        self.boia += (alvo - self.boia) * min(1, dt * 4)
        if self.aparecendo:
            self.aparecendo = min(1.0, self.aparecendo + dt * 3)
            self.alfa = int(255 * self.aparecendo)
            if self.aparecendo >= 1:
                self.aparecendo = 0.0
        if self.sumindo:
            self.alfa = max(0, self.alfa - int(dt * 400))
        elif self.morto_desde is not None and self.inimigo and self.tempo - self.morto_desde > 1.1:
            self.alfa = max(0, self.alfa - int(dt * 300))

    def some_de_vez(self):
        """True quando o visual pode ser removido da arena."""
        return self.alfa <= 0 and (self.sumindo or self.inimigo)

    # ============================================================
    # DESENHO
    # ============================================================

    def desenhar_sombra(self, tela):
        if self.alfa < 40 or self.deslocamento_y() < 0:          # boiando: sem sombra no chão
            return
        largura = max(40, int(self.largura() * 0.55))
        sombra = pygame.Surface((largura, max(8, largura // 5)), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (0, 0, 0, int(110 * self.alfa / 255)), sombra.get_rect())
        tela.blit(sombra, (round(self.x + self.deslocamento_x() - largura / 2), round(self.y - sombra.get_height() / 2)))

    def desenhar(self, tela, destaque=None):
        """destaque: None, "vez" (a vez dele), "alvo" (pode ser escolhido) ou "apagado"."""
        if self.alfa <= 0:
            return
        if self.oculto and self.lutador.esta_vivo():
            self.desenhar_no_escuro(tela)
            return
        efeito = "branco" if self.tempo < self.piscar_ate else self.tinta
        anim, indice = self.animador.anim, self.animador.indice
        imagem = self.sprites.quadro(self.nome_sprite, anim, indice, self.escala, self.inimigo, efeito)
        ax, ay = self.sprites.ancora(self.nome_sprite, self.escala, self.inimigo)
        x = round(self.x + self.deslocamento_x() - ax)
        y = round(self.y + self.deslocamento_y() - ay)
        self.desenhar_quadro(tela, imagem, x, y, destaque, self.alfa)

    def desenhar_quadro(self, tela, imagem, x, y, destaque, alfa):
        """Um quadro do sprite em (x, y) com a aura dourada, o contorno do destaque e a transparência."""
        if getattr(self.lutador, "dourado", False) and destaque not in ("vez", "alvo") and self.lutador.esta_vivo():
            # elite de aura dourada: contorno dourado mais fraco, sempre pulsando
            aura = pygame.mask.from_surface(imagem).to_surface(setcolor=(255, 210, 90, 255), unsetcolor=(0, 0, 0, 0))
            aura.set_alpha(110 + int(70 * math.sin(self.tempo * 3)))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)):
                tela.blit(aura, (x + dx, y + dy))
        if destaque in ("vez", "alvo"):
            # contorno pulsando em volta do personagem
            cor = tema.OURO_CLARO if destaque == "vez" else tema.SANGUE_CLARO
            contorno = pygame.mask.from_surface(imagem).to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0))
            contorno.set_alpha(190 + int(65 * math.sin(self.tempo * 7)))
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2), (-4, 0), (4, 0)):
                tela.blit(contorno, (x + dx, y + dy))

        if alfa < 255 or destaque == "apagado":
            imagem = imagem.copy()
            imagem.set_alpha(alfa if destaque != "apagado" else min(alfa, 110))
        tela.blit(imagem, (x, y))

    def desenhar_no_escuro(self, tela):
        """Oculto no escuro: só uma silhueta apagada (os olhos vêm depois do escuro, em desenhar_olhos)."""
        anim, indice = self.animador.anim, self.animador.indice
        imagem = self.sprites.quadro(self.nome_sprite, anim, indice, self.escala, self.inimigo, "silhueta").copy()
        imagem.set_alpha(150)
        ax, ay = self.sprites.ancora(self.nome_sprite, self.escala, self.inimigo)
        tela.blit(imagem, (round(self.x + self.deslocamento_x() - ax), round(self.y + self.deslocamento_y() - ay)))

    def desenhar_olhos(self, tela):
        """Um par de olhos vermelhos piscando no breu (desenhado por cima do escuro: eles brilham)."""
        if math.sin(self.tempo * 1.7 + id(self.lutador) % 7) < -0.9:
            return                                   # piscou
        caixa = self.caixa()
        x = round(caixa.left + caixa.width * (0.25 if self.inimigo else 0.75))
        y = round(caixa.top + caixa.height * 0.3)
        for dx in (-6, 4):
            tela.fill((110, 14, 20), (x + dx - 2, y - 2, 8, 8))
            tela.fill((240, 50, 44), (x + dx, y, 4, 4))

    def tem_barra(self):
        return self.lutador.esta_vivo() and self.alfa >= 120 and not self.oculto

    def rect_da_barra(self, tela, topo_minimo=84):
        """Onde a barra de vida fica: em cima da cabeça, sem sair da tela."""
        caixa = self.caixa()
        largura = max(70, min(150, caixa.width))
        rect = pygame.Rect(0, 0, largura, 8)
        rect.midbottom = (caixa.centerx, caixa.top - 10)
        rect.top = max(topo_minimo, rect.top)
        numero = tema.mini().size(f"{self.lutador.vida}/{self.lutador.vida_maxima}")[0]
        rect.right = min(rect.right, tela.get_width() - numero - 12)    # o número da vida não sai da tela
        rect.left = max(rect.left, 8)
        return rect

    def bloco_da_barra(self, rect, mostrar_nome=False, mostrar_energia=False, barra_na_cabeca=True):
        """Retângulo de tudo o que a barra desenha (nome, pontos, vida + número, energia, status)."""
        numero = tema.mini().size(f"{self.lutador.vida}/{self.lutador.vida_maxima}")[0] + 8 if barra_na_cabeca else 0
        if numero and not self.inimigo:
            numero += tema.mini().size(f"· {self.lutador.energia}")[0] + 4
        bloco = pygame.Rect(rect.x, rect.y, rect.width + numero, rect.height + (6 if not self.inimigo else 0))
        topo = rect.top - 2
        if mostrar_nome and barra_na_cabeca:
            nome = tema.mini().size(self.lutador.nome)[0] + 4
            topo -= tema.mini().get_height()
            bloco.union_ip(pygame.Rect(rect.centerx - nome // 2, topo, nome, rect.top - topo))
        if mostrar_energia:
            topo -= 14
            bloco.union_ip(pygame.Rect(rect.centerx - 55, topo, 110, 14))
        bloco.union_ip(pygame.Rect(rect.centerx - 9, topo - 20, 18, 20))   # o losango da vez fica aqui
        if self.lutador.status:
            bloco.height += 26
        return bloco

    def desenhar_barra(self, tela, mostrar_nome=False, mostrar_energia=False, barra_na_cabeca=True, topo_minimo=84,
                       rect=None):
        """Barra de vida com número, energia (heróis) e ícones de status em cima da cabeça.

        barra_na_cabeca=False: o chefe tem a barra grande no topo da tela; aqui ficam só a energia e os status.
        rect: posição já arrumada pela tela (separar_barras), para não cruzar com a de outro lutador."""
        self.areas_de_status = []
        lutador = self.lutador
        if not self.tem_barra():
            return
        rect = pygame.Rect(rect) if rect is not None else self.rect_da_barra(tela, topo_minimo)
        maximo = lutador.vida_maxima
        if barra_na_cabeca:
            cor = tema.VIDA if self.inimigo else tema.VIDA_HEROI
            barra(tela, rect, lutador.vida / maximo, cor, self.vida_mostrada / maximo, marcas=0)
            escudo = lutador.status.get("escudo")
            if escudo is not None and escudo.valor > 0:
                pygame.draw.rect(tela, (150, 190, 240), (rect.x, rect.y - 4, min(rect.width, int(rect.width * escudo.valor / maximo)), 3))
            numero = texto(tela, f"{lutador.vida}/{maximo}", tema.mini(), tema.TEXTO, (rect.right + 6, rect.centery),
                           "midleft")
            if not self.inimigo:                                       # energia na mesma linha: "29/34 · 2"
                texto(tela, f"· {lutador.energia}", tema.mini(), tema.ENERGIA_CLARA, (numero.right, rect.centery), "midleft")
        else:
            mostrar_nome = False                                       # o nome já está na barra do topo
        embaixo = rect.bottom
        if not self.inimigo:
            # energia dos heróis: barrinha azul logo abaixo da vida
            energia = pygame.Rect(rect.x, rect.bottom + 3, rect.width, 3)
            maximo_energia = max(1, min(lutador.energia_maxima, 10))
            pygame.draw.rect(tela, (8, 6, 12), energia.inflate(2, 2))
            pygame.draw.rect(tela, tema.ENERGIA, (energia.x, energia.y, energia.width * min(lutador.energia, maximo_energia)
                                                  // maximo_energia, energia.height))
            embaixo = energia.bottom
        topo = rect.top - 2
        if mostrar_nome:
            topo = texto(tela, lutador.nome, tema.mini(), tema.TEXTO_FRACO, (rect.centerx, topo), "midbottom").top
        if mostrar_energia:
            maximo_pontos = min(lutador.energia_maxima, 10)
            largura_pontos = maximo_pontos * 11
            pontos_de_energia(tela, (rect.centerx - largura_pontos // 2, topo - 12), lutador.energia, maximo_pontos, 4)
            topo -= 14
        self.topo_da_barra = topo
        # ícones de status embaixo da barra (a tela mostra a dica de cada um ao passar o mouse)
        x = rect.x
        for chave, status in lutador.status.items():
            icone = icone_status(chave)
            tela.blit(icone, (x, embaixo + 4))
            self.areas_de_status.append((pygame.Rect(x, embaixo + 4, icone.get_width(), icone.get_height()), status))
            if status.acumulos > 1 or status.valor:
                numero = status.acumulos if status.acumulos > 1 else status.valor
                texto(tela, str(numero), tema.fonte(11), tema.TEXTO, (x + icone.get_width() - 2, embaixo + 14), "topleft")
            x += icone.get_width() + 3


def separar_barras(itens, topo_minimo=84, espaco=4):
    """Arruma as barras de vida para nenhuma cruzar com outra.

    itens: [(visual, rect da barra, função rect -> bloco)]. A de baixo fica; a que cruza sobe
    (ou, sem espaço em cima, desce). Devolve {id(visual): rect}."""
    postos, saida = [], {}
    for visual, rect, bloco_de in sorted(itens, key=lambda item: -item[1].y):
        rect = pygame.Rect(rect)
        for _ in range(12):
            bloco = bloco_de(rect)
            outro = next((b for b in postos if b.colliderect(bloco)), None)
            if outro is None:
                break
            subir = bloco.bottom - outro.top + espaco
            if rect.y - subir >= topo_minimo:
                rect.y -= subir
            else:
                rect.y += outro.bottom - bloco.top + espaco
        postos.append(bloco_de(rect))
        saida[id(visual)] = rect
    return saida


def organizar(visuais, inimigo, chao=578):
    """Coloca os lutadores de um lado em duas fileiras, sem amontoar.

    Heróis ficam à esquerda (o primeiro mais à frente), inimigos à direita.
    """
    if not visuais:
        return
    sentido = -1 if not inimigo else 1
    inicio = 500 if not inimigo else 780
    borda = 14 if not inimigo else 1266            # até onde o último pode ir
    meias = [v.largura() * 0.5 for v in visuais]
    passos = [max(96, (meias[i] + meias[i + 1]) * 0.7 + 20) for i in range(len(visuais) - 1)]
    # Se não couber: primeiro avança até 90 px para o meio da tela, depois aperta os espaços (até 45%)
    largura_total = meias[0] * 0.6 + sum(passos) + meias[-1]
    falta = largura_total - abs(borda - inicio)
    if falta > 0:
        inicio -= sentido * min(90, falta)
    primeiro = inicio + sentido * meias[0] * 0.6
    ultimo = primeiro + sentido * (sum(passos) + meias[-1])
    excesso = (borda - ultimo) * sentido
    if excesso < 0 and passos:
        fator = max(0.45, 1 + excesso / sum(passos))
        passos = [p * fator for p in passos]
    x = primeiro
    for i, visual in enumerate(visuais):
        fileira = i % 2                      # 0 = frente, 1 = trás
        y = chao + 26 if fileira == 0 else chao - 30
        visual.colocar(x, y, imediato=(visual.x == 0 and visual.y == 0))
        if i < len(passos):
            x += sentido * passos[i]
