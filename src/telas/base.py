"""Base das telas: o App (janela e loop principal) e a classe Tela.

Cada tela implementa só o que precisa:
    evento(e)        teclado e mouse
    atualizar(dt)    animações (dt = segundos desde o último quadro)
    desenhar(tela)   desenho

As telas leem a run, mas não mudam nada nela: cada ação vira um Comando (roguelike/comandos.py) mandado por
self.enviar(comando), que passa pela sessão da run (roguelike/sessao.py; no solo, executa na hora).

O jogo desenha sempre numa tela de 1280x720 (App.tela). Com janela, apresentar() encaixa essa
imagem na janela de verdade, que tem o tamanho que couber no monitor (ou a tela cheia), com faixas
pretas; os eventos de mouse chegam já convertidos para 1280x720 (ui/escala.py).
"""

import os
import sys

import pygame

from ui import tema
from versao import NOME_DO_JOGO

MARGEM_DA_JANELA = (40, 110)        # folga para a borda da janela e a barra de tarefas (pixels da tela)
ID_DO_APP = "EcosDaCripta.Jogo"     # a barra de tarefas agrupa por ele (o instalador dá o mesmo aos atalhos)


def dar_identidade_no_windows():
    """A barra de tarefas mostra o ícone do jogo, e não o do Python, quando roda pelo código."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_DO_APP)
    except (AttributeError, OSError):
        pass


def colocar_icone():
    """O ícone da janela (assets/icone, gerado por ferramentas/gerar_icone.py). Devolve True se colocou."""
    from caminhos import CAMINHOS
    try:
        pygame.display.set_icon(pygame.image.load(CAMINHOS.asset("icone", "icone_32.png")))
        return True
    except (pygame.error, FileNotFoundError):
        return False


def tornar_dpi_consciente():
    """No Windows com escala de 125%/150%, faz o SDL ver os pixels reais de cada tela (senão a janela corta)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)        # por monitor: cada tela com seus pixels reais
    except (AttributeError, OSError):
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def alt_enter(e):
    """Alt+Enter: a tela cheia de todo jogo de Windows (fixo, além da tecla das Opções, que dá para trocar)."""
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and \
        bool(getattr(e, "mod", 0) & pygame.KMOD_ALT)


def escala_que_cabe(tamanho_da_tela, margem=MARGEM_DA_JANELA):
    """Quanto a janela de 1280x720 precisa encolher (< 1) para caber na tela, ou 1 se já cabe."""
    largura, altura = tamanho_da_tela
    return min(1.0, (largura - margem[0]) / tema.LARGURA, (altura - margem[1]) / tema.ALTURA)


class Tela:
    def __init__(self, app):
        self.app = app
        self.tempo = 0.0

    def ao_entrar(self):
        """Chamado quando a tela aparece: troca a música (se a tela tiver uma)."""
        musica = self.musica()
        if musica:
            self.app.audio.musica(musica, self.musica_repete())

    def ao_deixar_a_tela(self):
        """Chamado quando outra tela entra no lugar desta (ex.: parar de procurar partidas na rede).
        (Não confundir com o 'ao_sair' que várias telas recebem: a função que volta para quem as abriu.)"""

    def musica(self):
        """Nome da música desta tela (assets/sons/musica/<nome>.ogg) ou None para manter a atual."""
        return None

    def musica_repete(self):
        """False para vinhetas que tocam uma vez só (vitória, derrota)."""
        return True

    def evento(self, e):
        pass

    def atualizar(self, dt):
        self.tempo += dt

    def desenhar(self, tela):
        tela.fill(tema.FUNDO)

    # ---------------- comandos ----------------
    def sessao(self):
        """A sessão da run desta tela (App.sessao_da)."""
        return self.app.sessao_da(getattr(self, "run", None))

    def enviar(self, comando):
        """Manda uma ação do jogador (Comando). Devolve o Resultado (ok, mensagem, valor)."""
        return self.sessao().enviar(comando)

    def indice_do(self, heroi):
        """O número do herói na sessão (os comandos falam dos heróis por número)."""
        return self.sessao().estado.indice_do(heroi)

    def meu_jogador(self):
        """O jogador deste computador (a mochila e o ouro dele)."""
        return self.sessao().meu_jogador()


class App:
    """A janela do jogo. Guarda o que é compartilhado entre as telas:
    sprites, progresso, opções, controles, áudio e notificações.
    """

    FPS = 60
    DURACAO_TRANSICAO = 0.35

    def __init__(self, titulo=NOME_DO_JOGO, janela=True, opcoes=None):
        self.com_janela = janela
        if janela:
            tornar_dpi_consciente()
            dar_identidade_no_windows()
            os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.init()
        if janela:
            colocar_icone()                       # (antes da janela abrir: alguns sistemas não trocam depois)
            self.janela = pygame.display.set_mode(self.tamanho_da_janela(), pygame.RESIZABLE)
            self.tela = pygame.Surface((tema.LARGURA, tema.ALTURA)).convert()
        else:
            self.janela = self.tela = pygame.display.set_mode((tema.LARGURA, tema.ALTURA))
        pygame.display.set_caption(titulo)
        if janela:
            self.mostrar_carregando()
        self.relogio = pygame.time.Clock()
        self.rodando = True
        self.atual = None
        self.inicio_transicao = -10.0
        self.relogio_total = 0.0
        self.sessao = None                # a sessão da run em andamento (sessao_da)
        self.partida = None               # partida em grupo (rede/partida.py) ou None no jogo solo
        self.avisos_do_bau = {}           # (jogador, "pôs no baú"/"pegou do baú") -> itens juntados (fluxo)

        from audio import GerenciadorDeAudio
        from ui.componentes import Notificacoes
        from ui.opcoes import Opcoes
        from visual.sprites_macabros import Sprites
        self.opcoes = opcoes or Opcoes.carregar()
        self.controles = self.opcoes.controles
        self.audio = GerenciadorDeAudio(self.opcoes)
        self.notificacoes = Notificacoes()
        self.sprites = Sprites()
        if janela and self.opcoes.tela_cheia:
            self._trocar_modo_de_tela(cheia=True)

    # ---------------- opções ----------------
    @property
    def velocidade(self):
        """Velocidade das animações do combate (vem das opções)."""
        return self.opcoes.velocidade_combate

    @velocidade.setter
    def velocidade(self, valor):
        self.opcoes.velocidade_combate = valor

    def salvar_opcoes(self):
        self.opcoes.salvar()

    # ---------------- janela ----------------
    def mostrar_carregando(self):
        """O primeiro quadro, enquanto sprites, sons e fontes carregam: o ícone grande e o nome do jogo."""
        from caminhos import CAMINHOS
        from ui.texto import linha
        self.tela.fill((10, 6, 14))
        try:
            icone = pygame.image.load(CAMINHOS.asset("icone", "icone_256.png"))
            self.tela.blit(icone, icone.get_rect(center=(tema.LARGURA // 2, tema.ALTURA // 2 - 60)))
        except (pygame.error, FileNotFoundError):
            pass
        linha(self.tela, NOME_DO_JOGO, tema.grande(), tema.OURO_CLARO, (tema.LARGURA // 2, tema.ALTURA // 2 + 110),
              tema.LARGURA - 40, "center")
        linha(self.tela, "carregando...", tema.pequena(), tema.TEXTO_FRACO, (tema.LARGURA // 2, tema.ALTURA // 2 + 156),
              400, "center")
        self.apresentar()
        pygame.display.flip()
        pygame.event.pump()                       # (o Windows não acha que a janela travou)

    @staticmethod
    def tamanho_da_janela():
        """1280x720, ou menor se alguma tela ligada (ex.: notebook 1366x768) não comportar."""
        tamanhos = pygame.display.get_desktop_sizes() or [(tema.LARGURA, tema.ALTURA)]
        escala = min(escala_que_cabe(t) for t in tamanhos)
        return int(tema.LARGURA * escala), int(tema.ALTURA * escala)

    def _trocar_modo_de_tela(self, cheia):
        """Tela cheia na resolução atual do monitor (sem trocar o modo de vídeo) ou de volta à janela que cabe."""
        if not self.com_janela:
            return
        try:
            if cheia:
                self.janela = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.janela = pygame.display.set_mode(self.tamanho_da_janela(), pygame.RESIZABLE)
        except pygame.error:
            self.janela = pygame.display.set_mode(self.tamanho_da_janela(), pygame.RESIZABLE)

    def alternar_tela_cheia(self):
        self._trocar_modo_de_tela(not self.opcoes.tela_cheia)
        self.opcoes.tela_cheia = not self.opcoes.tela_cheia
        self.salvar_opcoes()

    def apresentar(self):
        """Encaixa a imagem de 1280x720 na janela (escala suave ao encolher, pixels inteiros ao ampliar)."""
        from ui.escala import ENCAIXE
        if self.janela is self.tela:
            return
        janela = pygame.display.get_surface()
        self.janela = janela
        ENCAIXE.ajustar(janela.get_size())
        tamanho = ENCAIXE.tamanho()
        if tamanho == self.tela.get_size():
            janela.blit(self.tela, ENCAIXE.deslocamento)
            return
        janela.fill((0, 0, 0))
        inteira = ENCAIXE.escala >= 1 and ENCAIXE.escala == int(ENCAIXE.escala)
        ajustada = (pygame.transform.scale if inteira else pygame.transform.smoothscale)(self.tela, tamanho)
        janela.blit(ajustada, ENCAIXE.deslocamento)

    # ---------------- sessão ----------------
    def sessao_da(self, run):
        """A sessão da run (no solo, uma SessaoLocal criada na primeira vez; uma run nova ganha uma sessão nova).
        A run de uma partida em grupo usa a sessão da partida (SessaoHost ou SessaoCliente: rede/sessoes.py)."""
        partida = self.partida
        if partida is not None and partida.sessao is not None and partida.sessao.estado.run is run:
            return partida.sessao
        if self.sessao is None or self.sessao.estado.run is not run:
            from roguelike.estado import EstadoDoJogo
            from roguelike.sessao import SessaoLocal
            self.sessao = SessaoLocal(EstadoDoJogo(run))
        return self.sessao

    # ---------------- telas ----------------
    def notificar(self, titulo, conteudo="", som="conquista"):
        """Aviso rápido no topo da tela (ex.: "Golpe aprimorado!")."""
        self.notificacoes.adicionar(titulo, conteudo)
        if som:
            self.audio.tocar(som)

    def trocar(self, nova):
        """Troca de tela com um escurecimento rápido."""
        if self.atual is not None and self.atual is not nova:
            self.atual.ao_deixar_a_tela()
        self.atual = nova
        self.inicio_transicao = self.relogio_total
        nova.ao_entrar()

    def sair(self):
        self.rodando = False

    def passo(self, dt, eventos):
        """Um quadro do jogo (separado do loop para poder testar sem janela)."""
        from ui.escala import converter_evento
        self.relogio_total += dt
        sem_conexao = self.partida is not None and getattr(self.partida, "reconectando", None) is not None
        for e in eventos:
            e = converter_evento(e)
            if e.type == pygame.QUIT:
                self.rodando = False
            elif self.controles.eh(e, "tela_cheia") or alt_enter(e):
                self.alternar_tela_cheia()
            elif sem_conexao:                         # tentando voltar à partida: a tela espera (ESC desiste)
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    from telas import fluxo
                    fluxo.sair_da_partida(self)
            elif self.atual is not None:
                self.atual.evento(e)
        if self.partida is not None:                  # a rede: o que chegou, avisos e troca de tela (fluxo)
            from telas import fluxo
            fluxo.seguir_a_partida(self)
        if self.atual is not None:
            self.atual.atualizar(dt)
            self.atual.desenhar(self.tela)
        self.desenhar_por_cima()
        self.notificacoes.atualizar(dt)
        self.notificacoes.desenhar(self.tela)
        passado = self.relogio_total - self.inicio_transicao
        if passado < self.DURACAO_TRANSICAO:
            escuro = pygame.Surface(self.tela.get_size())
            escuro.fill((4, 2, 6))
            escuro.set_alpha(int(255 * (1 - passado / self.DURACAO_TRANSICAO)))
            self.tela.blit(escuro, (0, 0))

    def desenhar_por_cima(self):
        """O que vale para qualquer tela numa partida em grupo: sem conexão (tentando voltar) ou conexão lenta."""
        if self.partida is not None:
            from telas.em_grupo import desenhar_conexao
            desenhar_conexao(self.tela, self.partida)

    def rodar(self):
        while self.rodando:
            dt = min(0.05, self.relogio.tick(self.FPS) / 1000)
            self.passo(dt, pygame.event.get())
            self.apresentar()
            pygame.display.flip()
        if self.partida is not None:                  # fechar a janela no meio de uma partida: avisa os outros
            self.partida.fechar()
        pygame.quit()
