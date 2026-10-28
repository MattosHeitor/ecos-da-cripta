"""Tela de título: o salão da Cripta (visual/salao_da_cripta.py), o grupo à contraluz na entrada e o menu.

Abre com um fade do preto; o logo "Ecos da Cripta" desce na frente do vitral, com letras de metal dourado e um
brilho que passa de tempos em tempos. Morcegos voam em duas profundidades (atrás e na frente das colunas).
Menu numa moldura de madeira e ouro: continuar a run salva, acampamento, jogar em grupo, opções ou sair (setas +
Enter, mouse ou atalhos 1 a 5).
"""

import math
import random

import pygame

from telas import fluxo
from telas.comum import TelaComBotoes, existe_run_salva, sprite_da_vaga
from ui import tema
from ui.desenho import texto, losango, painel, vinheta
from visual.salao_da_cripta import SalaoDaCripta
from visual.acampamento_noturno import brilho_aditivo
from ui.widgets import Botao
from versao import NOME_DO_JOGO, VERSAO

TITULO_DO_JOGO = NOME_DO_JOGO
SUBTITULO = "um roguelike sombrio por turnos"
FADE = 1.4                    # segundos do preto até a cena
ENTRADA_DO_LOGO = 1.1         # o logo desce nesse tempo
COR_SILHUETA = (22, 12, 24)


def logo(conteudo, tamanho):
    """O título em letras douradas com degradê, contorno vermelho-escuro e sombra (desenhado uma vez)."""
    fonte = tema.fonte(tamanho)
    texto_branco = fonte.render(conteudo, tema.SUAVE, (255, 255, 255))
    largura, altura = texto_branco.get_size()
    branco = pygame.Surface((largura, altura), pygame.SRCALPHA)       # (o texto sem suavização vem com colorkey)
    branco.blit(texto_branco, (0, 0))
    degrade = pygame.Surface((largura, altura), pygame.SRCALPHA)
    for y in range(altura):
        t = y / max(1, altura - 1)
        cor = (int(250 - 90 * t), int(222 - 130 * t), int(150 - 110 * t))     # dourado claro -> bronze
        pygame.draw.line(degrade, (*cor, 255), (0, y), (largura, y))
    letras = branco.copy()
    letras.blit(degrade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    mascara = pygame.mask.from_surface(branco)                      # bisel: borda de cima clara, de baixo escura
    for desloc, cor in (((0, 2), (255, 246, 206)), ((0, -2), (120, 62, 26))):
        borda = mascara.copy()
        borda.erase(mascara, desloc)
        letras.blit(borda.to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
    contorno = fonte.render(conteudo, tema.SUAVE, (90, 14, 24))
    sombra = fonte.render(conteudo, tema.SUAVE, (8, 4, 8))
    final = pygame.Surface((largura + 12, altura + 12), pygame.SRCALPHA)
    final.blit(sombra, (8, 10))
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)):
        final.blit(contorno, (5 + dx, 5 + dy))
    final.blit(letras, (5, 5))
    return final


def brilho_do_logo(imagem):
    """Halo atrás do logo: elipses concêntricas em cores já "multiplicadas" (para somar à tela com BLEND_ADD)."""
    largura, altura = imagem.get_size()
    halo = pygame.Surface((largura + 160, altura + 120))
    halo.fill((0, 0, 0))
    centro = (halo.get_width() // 2, halo.get_height() // 2)
    for passo in range(14, 0, -1):                   # de fora para dentro: cada elipse um pouco mais forte
        t = passo / 14
        forca = 0.32 * (1 - t) ** 1.5
        rect = pygame.Rect(0, 0, int(halo.get_width() * t), int(halo.get_height() * t))
        rect.center = centro
        pygame.draw.ellipse(halo, (int(255 * forca), int(110 * forca), int(50 * forca)), rect)
    return halo


def faixa_de_brilho(logo_imagem, progresso):
    """O reflexo que passa pelas letras (progresso 0..1): uma faixa diagonal clara, só por cima do metal."""
    largura, altura = logo_imagem.get_size()
    faixa = pygame.Surface((largura, altura), pygame.SRCALPHA)
    x = -80 + (largura + 160) * progresso
    pygame.draw.polygon(faixa, (255, 248, 220, 150), [(x, 0), (x + 26, 0), (x + 26 - altura * 0.5, altura), (x - altura * 0.5, altura)])
    pygame.draw.polygon(faixa, (255, 248, 220, 80), [(x + 34, 0), (x + 42, 0), (x + 42 - altura * 0.5, altura), (x + 34 - altura * 0.5, altura)])
    letras = logo_imagem.copy()
    letras.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)          # a forma das letras, branca (a transparência fica)
    faixa.blit(letras, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return faixa


class Morcego:
    """Um morcego em silhueta cruzando o salão numa onda. longe = menor, mais escuro e atrás das colunas."""

    def __init__(self, rng, longe=False):
        self.rng = rng
        self.longe = longe
        self.recomecar(primeira=True)

    def recomecar(self, primeira=False):
        rng = self.rng
        self.para_direita = rng.random() < 0.5
        self.x = rng.uniform(0, tema.LARGURA) if primeira else (-60 if self.para_direita else tema.LARGURA + 60)
        self.y = rng.uniform(60, 260) if self.longe else rng.uniform(150, 420)
        self.velocidade = rng.uniform(50, 90) if self.longe else rng.uniform(90, 160)
        self.fase = rng.uniform(0, 6)
        self.escala = 1 if self.longe else 2

    def atualizar(self, dt):
        self.x += self.velocidade * dt * (1 if self.para_direita else -1)
        self.fase += dt * 2
        if self.x < -80 or self.x > tema.LARGURA + 80:
            self.recomecar()

    def desenhar(self, tela, sprites, tempo):
        cor = (14, 8, 18) if self.longe else COR_SILHUETA
        imagem = sprites.quadro("morcego_gigante", "parado", int(tempo * 10 + self.fase) % 4, self.escala,
                                not self.para_direita, cor)
        tela.blit(imagem, imagem.get_rect(center=(self.x, self.y + math.sin(self.fase) * (8 if self.longe else 14))))


class TelaTitulo(TelaComBotoes):
    def __init__(self, app):
        super().__init__(app)
        self.salao = SalaoDaCripta()
        self.tem_save = existe_run_salva()
        rng = random.Random(7)
        self.morcegos_longe = [Morcego(rng, longe=True) for _ in range(4)]
        self.morcegos = [Morcego(rng) for _ in range(3)]
        self.logo = logo(TITULO_DO_JOGO.upper(), 92)
        self.halo = brilho_do_logo(self.logo)
        self.focar_ao_abrir = True
        self._silhuetas = {}

    def musica(self):
        return "titulo"

    def abrir_opcoes(self):
        from telas.opcoes import TelaOpcoes
        self.app.trocar(TelaOpcoes(self.app, lambda: fluxo.ir_para_titulo(self.app)))

    def atualizar(self, dt):
        super().atualizar(dt)
        self.salao.mirar(self.mouse)
        self.salao.atualizar(dt)
        for morcego in self.morcegos_longe + self.morcegos:
            morcego.atualizar(dt)

    def tecla(self, e):
        opcoes = self.opcoes()
        if e.unicode and e.unicode.isdigit() and 1 <= int(e.unicode) <= len(opcoes):
            opcoes[int(e.unicode) - 1][2]()
            return
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.tem_save:
                fluxo.continuar_run_salva(self.app)
            else:
                fluxo.ir_para_acampamento(self.app)

    def voltar(self):
        self.app.sair()

    def opcoes(self):
        lista = []
        if self.tem_save:
            lista.append(("Continuar a run", "a expedição espera no mapa", lambda: fluxo.continuar_run_salva(self.app)))
        lista.append(("Acampamento", "montar o grupo e partir" if not self.tem_save else "começar outra run",
                      lambda: fluxo.ir_para_acampamento(self.app)))
        lista.append(("Jogar em grupo", "criar ou entrar numa partida na rede", lambda: fluxo.abrir_multijogador(self.app)))
        lista.append(("Opções", "som, velocidade e teclas", self.abrir_opcoes))
        lista.append(("Sair", "até a próxima noite", self.app.sair))
        return lista

    # ---------------- desenho ----------------
    def silhueta(self, nome, quadro):
        """O herói todo escuro, recortado contra a luz do salão (guardado por quadro), com a borda acesa pelas velas."""
        chave = (nome, quadro)
        if chave not in self._silhuetas:
            imagem = self.app.sprites.quadro(nome, "parado", quadro, 2, False, "silhueta").copy()
            imagem.fill((60, 44, 60), special_flags=pygame.BLEND_RGB_MULT)
            mascara = pygame.mask.from_surface(imagem)
            borda = mascara.copy()
            borda.erase(mascara, (-2, 0))                       # o lado direito, virado para o candelabro
            imagem.blit(borda.to_surface(setcolor=(176, 104, 52, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
            self._silhuetas[chave] = imagem
        return self._silhuetas[chave]

    def desenhar_grupo(self, tela):
        """O grupo da expedição em silhueta, parado na entrada do salão (primeiro plano, à esquerda)."""
        progresso = self.app.progresso
        base_y = tema.ALTURA - 40
        sombra = pygame.Surface((440, 50), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (0, 0, 0, 150), sombra.get_rect())
        tela.blit(sombra, (-30, base_y - 22))
        vagas = progresso.expedicao_atual().vagas[:5] if progresso else []
        for i, vaga in enumerate(vagas):
            nome = sprite_da_vaga(progresso, vaga)
            pe = (60 + i * 58, base_y + (i % 2) * 8)
            imagem = self.silhueta(nome, int(self.tempo * 3 + i) % 4)
            ax, ay = self.app.sprites.ancora(nome, 2)
            tela.blit(imagem, (pe[0] - ax, pe[1] - ay))

    def desenhar_logo(self, tela, centro):
        entrada = min(1.0, max(0.0, (self.tempo - 0.3) / ENTRADA_DO_LOGO))
        suave = entrada * entrada * (3 - 2 * entrada)
        y = 108 - (1 - suave) * 60
        pulso = 0.6 + 0.4 * math.sin(self.tempo * 1.6)
        halo = self.halo.copy()
        nivel = int(255 * pulso * suave)
        halo.fill((nivel, nivel, nivel), special_flags=pygame.BLEND_RGB_MULT)
        tela.blit(halo, halo.get_rect(center=(centro, y)), special_flags=pygame.BLEND_ADD)
        logo_atual = self.logo.copy()
        ciclo = (self.tempo - ENTRADA_DO_LOGO - 0.3) % 6.0          # a cada 6 s um reflexo atravessa as letras
        if suave >= 1 and ciclo < 1.2:
            logo_atual.blit(faixa_de_brilho(self.logo, ciclo / 1.2), (0, 0))
        logo_atual.set_alpha(int(255 * suave))
        tela.blit(logo_atual, logo_atual.get_rect(center=(centro, y)))
        if suave > 0.6:
            alfa = int(255 * (suave - 0.6) / 0.4)
            texto(tela, SUBTITULO, tema.normal(), tema.TEXTO_TITULO, (centro, y + 70), "center", alfa=alfa)
            largura = 250
            for lado in (-1, 1):
                pygame.draw.line(tela, tema.OURO_ESCURO if hasattr(tema, "OURO_ESCURO") else tema.SANGUE,
                                 (centro + lado * 44, y + 98), (centro + lado * largura, y + 98), 2)
                losango(tela, (centro + lado * (largura + 8), y + 98), 5, tema.SANGUE_CLARO)
            losango(tela, (centro, y + 98), 7, tema.OURO)

    def desenhar_menu(self, tela, centro):
        """As opções dentro de uma moldura de madeira e ouro, com velas acesas ao lado da escolhida."""
        opcoes = self.opcoes()
        altura_botao, espaco = 54, 10
        largura = 400
        topo = 248 if self.tem_save else 268
        moldura = pygame.Rect(0, 0, largura, 36 + len(opcoes) * (altura_botao + espaco) - espaco)
        moldura.midtop = (centro, topo)
        painel(tela, moldura, "ouro")
        for lado in (-1, 1):                                    # florões nas pontas de cima e de baixo
            for y in (moldura.top + 6, moldura.bottom - 6):
                losango(tela, (moldura.centerx + lado * (largura // 2 - 22), y), 4, tema.OURO)
        for i, (nome, dica, acao) in enumerate(opcoes):
            rect = (moldura.x + 20, moldura.y + 18 + i * (altura_botao + espaco), largura - 40, altura_botao)
            botao = self.botao(Botao(rect, nome, acao, str(i + 1), subtexto=dica))
            if botao.focado or (not self.usando_teclado and botao.em_cima(self.mouse)):
                for lado in (-1, 1):                          # velas acesas dos lados da opção escolhida
                    x = moldura.centerx + lado * (largura // 2 + 22)
                    y = botao.rect.centery
                    brilho_aditivo(tela, (x, y - 10), 30, (150, 86, 34), 0.9)
                    pygame.draw.rect(tela, (226, 212, 180), (x - 3, y - 4, 6, 18))
                    chama = 5 + int(2 * math.sin(self.tempo * 12 + lado))
                    pygame.draw.polygon(tela, (255, 170, 60), [(x - 3, y - 4), (x, y - 4 - chama * 2), (x + 3, y - 4)])
                    pygame.draw.polygon(tela, (255, 240, 170), [(x - 1, y - 4), (x, y - 4 - chama), (x + 1, y - 4)])
        if self.tem_save:
            texto(tela, "Começar uma run nova apaga a run salva.", tema.mini(), tema.TEXTO_FRACO,
                  (centro, moldura.bottom + 8), "midtop")

    def desenhar_rodape(self, tela):
        progresso = self.app.progresso
        estatisticas = progresso.estatisticas
        rect = painel(tela, (tema.LARGURA // 2 - 330, tema.ALTURA - 54, 660, 38), "ferro")
        feitas = len(progresso.conquistas_feitas)
        linha = (f"Brasas {progresso.brasas}   ·   Runs {estatisticas['runs']}   ·   Vitórias {estatisticas['vitorias']}"
                 f"   ·   Melhor marca: {estatisticas['melhor_areas']} áreas   ·   Insígnias {feitas}")
        texto(tela, linha, tema.pequena(), tema.TEXTO, rect.center, "center")
        teclas = self.app.controles.texto_da_acao("tela_cheia")
        texto(tela, f"{teclas} ou Alt+Enter: tela cheia   ·   v{VERSAO}", tema.mini(), tema.TEXTO_FRACO,
              (tema.LARGURA - 12, tema.ALTURA - 10), "bottomright")

    def desenhar_cena(self, tela):
        self.salao.desenhar_fundo(tela)
        for morcego in self.morcegos_longe:
            morcego.desenhar(tela, self.app.sprites, self.tempo)
        self.salao.desenhar_colunas(tela, self.app.sprites)
        self.salao.desenhar_nevoa(tela)
        for morcego in self.morcegos:
            morcego.desenhar(tela, self.app.sprites, self.tempo)
        self.desenhar_grupo(tela)
        self.salao.desenhar_frente(tela)
        tela.blit(vinheta(tela.get_size(), 170), (0, 0))

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.desenhar_cena(tela)
        centro = tema.LARGURA // 2
        self.desenhar_logo(tela, centro)
        self.desenhar_menu(tela, centro)
        self.desenhar_rodape(tela)
        if self.focar_ao_abrir:                           # o teclado já começa na primeira opção
            self.focar_primeiro()
            self.focar_ao_abrir = False
        if self.tempo < FADE:
            escuro = pygame.Surface(tela.get_size())
            escuro.fill((0, 0, 0))
            escuro.set_alpha(int(255 * (1 - self.tempo / FADE)))
            tela.blit(escuro, (0, 0))
        self.terminar_desenho(tela)