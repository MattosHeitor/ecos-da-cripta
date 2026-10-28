"""Retomar uma partida salva (o host): a run voltou no ponto em que estava e o grupo entra de novo pelo código.

    ┌──────────── Retomando a partida ────────────┐
    │ Floresta Morta, área 3                       │
    │ ● Ana (host)         pronta                  │
    │ ● Bia                esperando...            │
    │ código 30AG-00F  (IP ... · trocar de rede)   │
    └──────────────────────────────────────────────┘
    [Fechar]                         [Seguir sem quem falta]

Quem volta recebe a run no mesmo ponto (rede/retomada.py). Com todos de volta, o grupo segue sozinho; "Seguir sem
quem falta" deixa a IA jogar por quem ainda não voltou (pode voltar depois, a qualquer momento).
"""

import pygame

from rede.codigo import codigo_de, ips_deste_pc, nome_da_rede
from rede.protocolo import configuracao
from telas import em_grupo, fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho
from ui import tema
from ui.desenho import painel, titulo_de_painel, paragrafo
from ui.texto import linha
from ui.widgets import Botao

QUADRO = pygame.Rect(290, 92, 700, 500)
SEGUNDOS_ANTES_DE_SEGUIR = 1.0          # todos voltaram: o host vê a lista completa antes de a run continuar


class TelaRetomada(TelaComBotoes):
    def __init__(self, app):
        super().__init__(app)
        self.partida = app.partida
        self.fundo = Fundo("acampamento", escurecer=160)
        self.ips = ips_deste_pc()
        if self.partida.ip_mostrado not in self.ips:
            self.partida.ip_mostrado = self.ips[0]
        self.todos_desde = None

    def musica(self):
        return "acampamento"

    @staticmethod
    def aceita_comandos():
        """Os comandos de quem já voltou esperam o host seguir (a tela dele ainda não é a da run)."""
        return False

    def seguir(self):
        """Continua a run (quem falta fica com a IA até voltar)."""
        if self.app.partida is not self.partida or self.partida.run is None:
            return
        self.partida.seguir_sem_esperar()
        fluxo.retomar_em_grupo(self.app, self.partida.run)

    def trocar_ip(self):
        if len(self.ips) > 1:
            atual = self.ips.index(self.partida.ip_mostrado) if self.partida.ip_mostrado in self.ips else -1
            self.partida.ip_mostrado = self.ips[(atual + 1) % len(self.ips)]

    def voltar(self):
        self.abrir_dialogo("Fechar", "Fechar a partida? Ela continua salva para retomar depois.",
                           [("Fechar", lambda: fluxo.sair_da_partida(self.app)), ("Ficar", None)])

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)
        if self.app.partida is not self.partida:
            return
        if not self.partida.faltam_voltar():               # todos de volta: segue sozinho num instante
            self.todos_desde = self.tempo if self.todos_desde is None else self.todos_desde
            if self.tempo - self.todos_desde >= SEGUNDOS_ANTES_DE_SEGUIR:
                self.seguir()
        else:
            self.todos_desde = None

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho(tela, "Retomar partida", "esperando o grupo voltar")
        partida, run = self.partida, self.partida.run
        painel(tela, QUADRO, "ferro")
        topo = titulo_de_painel(tela, QUADRO, "Retomando a partida")
        linha(tela, f"{run.regiao.nome}, área {run.area}", tema.normal(), tema.TEXTO_TITULO, (QUADRO.centerx, topo + 4),
              QUADRO.width - 48, "midtop")
        y = topo + 44
        for jogador in partida.lobby.jogadores:
            rect = pygame.Rect(QUADRO.x + 24, y, QUADRO.width - 48, 50)
            fora = jogador.id in partida.desconectados
            painel(tela, rect, "pedra" if fora else "ouro")
            pygame.draw.circle(tela, jogador.cor, (rect.x + 22, rect.centery), 9)
            nome = jogador.nome + (" (host)" if jogador.host else "")
            linha(tela, nome, tema.pequena(), jogador.cor, (rect.x + 42, rect.centery), rect.width - 260, "midleft")
            if fora:
                estado, cor = "esperando...", tema.TEXTO_FRACO
            else:
                medida = em_grupo.latencia(partida, jogador.id)
                estado, cor = "de volta" + (f" · {medida[0]}" if medida else ""), tema.CURA
            linha(tela, estado, tema.pequena(), cor, (rect.right - 16, rect.centery), 220, "midright")
            y += 58
        ip, porta = partida.ip_mostrado, partida.porta
        porta_extra = "" if porta == configuracao()["porta"] else f":{porta}"
        base = QUADRO.bottom - 172
        linha(tela, f"Código da partida · {nome_da_rede(ip)}", tema.mini(), tema.TEXTO_FRACO,
              (QUADRO.centerx, base), QUADRO.width - 48, "midtop")
        linha(tela, codigo_de(ip, porta), tema.grande(), tema.OURO_CLARO, (QUADRO.centerx, base + 18), 400, "midtop")
        if len(self.ips) > 1:
            botao = Botao((QUADRO.centerx - 170, base + 66, 340, 26), f"IP {ip}{porta_extra} · trocar de rede",
                          self.trocar_ip, estilo="pedra")
            botao.fontes = [tema.mini()]
            self.botao(botao)
        else:
            linha(tela, f"IP {ip}{porta_extra} · no mesmo PC: 127.0.0.1{porta_extra}", tema.mini(), tema.TEXTO_FRACO,
                  (QUADRO.centerx, base + 70), QUADRO.width - 48, "midtop")
        paragrafo(tela, "Cada um entra de novo pelo código (ou pela lista da rede), no mesmo computador de antes: "
                        "os heróis voltam com o dono.", tema.mini(), tema.TEXTO_FRACO, (QUADRO.x + 24, base + 100),
                  QUADRO.width - 48, maximo_linhas=2)
        faltam = partida.faltam_voltar()
        self.botao(Botao((16, tema.ALTURA - 66, 180, 48), "Fechar", self.voltar, "ESC"))
        rotulo = "Seguir" if not faltam else "Seguir sem quem falta"
        self.botao(Botao((tema.LARGURA - 336, tema.ALTURA - 66, 320, 48), rotulo, self.seguir, estilo="ouro",
                         dica=("Seguir", "Quem ainda não voltou fica com a IA e pode voltar a qualquer momento.")))
        self.terminar_desenho(tela)
