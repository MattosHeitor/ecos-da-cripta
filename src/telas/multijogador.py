"""Jogar em grupo: o seu nome e a sua cor, criar uma partida ou entrar numa (pelo código, pelo IP ou pela lista
das partidas achadas na rede local).

    ┌──── Você ────┐ ┌──── Criar partida ────┐ ┌──── Entrar em partida ────────┐
    │ nome, cor    │ │ você hospeda          │ │ código ou IP  [Entrar]        │
    └──────────────┘ └───────────────────────┘ │ partidas na rede (clique)     │
    mensagem / erro                 [Voltar]   └───────────────────────────────┘

Criar abre a porta (rede/partida.PartidaHost) e vai ao lobby; entrar conecta em segundo plano
(PartidaCliente) e, quando o host aceita, vai ao lobby. Se a partida acabar (recusa, queda, host saiu), o jogo
volta para cá com o motivo.

MP8: na 1ª vez que hospeda, um aviso do firewall do Windows. Com uma partida salva (o host fechou ou caiu no meio
da run), "Retomar partida" abre a run no ponto em que estava e espera o grupo (telas/retomada.py). Quem estava numa
partida em andamento volta a ela pelo código (ou pela lista): a chave de volta das Opções vai junto.
"""

import pygame

from rede.codigo import endereco_digitado
from rede.descoberta import Procurador
from rede.partida import PartidaCliente, PartidaHost
from rede.protocolo import configuracao
from rede.retomada import apagar_partida_salva, carregar_partida_salva, resumo_da_partida_salva
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho
from ui import tema
from ui.componentes import AreaClicavel
from ui.desenho import painel, titulo_de_painel, paragrafo
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao, CampoDeTexto

AVISO_DO_FIREWALL = ("Na primeira vez que você hospeda, o Windows pergunta se o Ecos da Cripta pode usar a rede. "
                     "Marque \"Redes privadas\" e clique em \"Permitir acesso\". Jogando pela Radmin VPN (ou outra "
                     "VPN), marque também \"Redes públicas\" se ela aparecer assim.")

VOCE = pygame.Rect(16, 72, 392, 330)
CRIAR = pygame.Rect(420, 72, 392, 330)
ENTRAR = pygame.Rect(824, 72, 440, 572)


class TelaMultijogador(TelaComBotoes):
    def __init__(self, app, erro=None):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=150)
        opcoes = app.opcoes
        regras_da_rede = configuracao()
        self.cores = [tuple(c) for c in regras_da_rede["cores"]]
        self.cor = min(opcoes.cor_do_jogador, len(self.cores) - 1)
        self.campo_nome = CampoDeTexto((VOCE.x + 24, VOCE.y + 92, VOCE.width - 48, 44), opcoes.nome_do_jogador,
                                       maximo=regras_da_rede["maximo_do_nome"], rotulo="Seu nome", dica="Como os outros te veem")
        self.campo_endereco = CampoDeTexto((ENTRAR.x + 24, ENTRAR.y + 92, ENTRAR.width - 180, 44), opcoes.ultimo_endereco,
                                           maximo=21, maiusculas=True, rotulo="Código ou IP do host",
                                           dica="ex.: 30AG-00F ou 192.168.0.15")
        self.mensagem = (erro, tema.SANGUE_CLARO) if erro else None
        self.procurador = Procurador(regras_da_rede["porta_descoberta"])
        self.salva = carregar_partida_salva()             # a partida que o host pode retomar (ou None)

    def musica(self):
        return "acampamento"

    def ao_entrar(self):
        super().ao_entrar()
        if not self.procurador.aberto:                       # (voltou a esta mesma tela)
            self.procurador = Procurador(configuracao()["porta_descoberta"])

    def ao_deixar_a_tela(self):
        self.procurador.fechar()

    # ---------------- ações ----------------
    def avisar(self, texto, erro=True):
        self.mensagem = (texto, tema.SANGUE_CLARO if erro else tema.OURO_CLARO)

    def guardar_nome(self):
        """Guarda nome e cor nas opções. Devolve o nome (ou None, se está vazio)."""
        nome = self.campo_nome.conteudo.strip()
        self.app.opcoes.nome_do_jogador = nome
        self.app.opcoes.cor_do_jogador = self.cor
        self.app.salvar_opcoes()
        if not nome:
            self.avisar("Escolha um nome primeiro: é como os outros vão te ver.")
            self.campo_nome.ativo = True
            return None
        return nome

    def depois_do_aviso_do_firewall(self, acao):
        """Na 1ª vez que hospeda: explica o que o Windows vai perguntar (e não pergunta de novo)."""
        if self.app.opcoes.avisou_firewall:
            acao()
            return

        def seguir():
            self.app.opcoes.avisou_firewall = True
            self.app.salvar_opcoes()
            acao()
        self.abrir_dialogo("Antes de hospedar", AVISO_DO_FIREWALL, [("Entendi", seguir), ("Cancelar", None)])

    def abrir_partida(self, **extras):
        """Abre a porta (e vai ao lobby, ou à espera do grupo numa partida retomada). Devolve True se abriu."""
        nome = self.guardar_nome()
        if nome is None:
            return False
        try:
            self.app.partida = PartidaHost(self.app.progresso, nome, self.cores[self.cor], **extras)
        except OSError:
            porta = configuracao()["porta"]
            self.avisar(f"Não deu para abrir a porta {porta}: outra cópia do jogo já hospeda neste PC? Feche-a e tente de novo.")
            return False
        except ValueError as erro:
            self.avisar(f"Não deu para retomar a partida salva: {erro}")
            return False
        return True

    def criar(self):
        if self.guardar_nome() is None:
            return

        def criar_de_verdade():
            if self.abrir_partida():
                fluxo.ir_para_acampamento(self.app)
        self.depois_do_aviso_do_firewall(criar_de_verdade)

    def retomar(self):
        """A partida salva: a run volta no ponto em que estava (o fluxo abre a espera do grupo)."""
        salva = carregar_partida_salva()
        if salva is None:
            self.salva = None
            self.avisar("A partida salva não existe mais (ou é de outra versão do jogo).")
            return
        if self.guardar_nome() is not None:
            self.depois_do_aviso_do_firewall(lambda: self.abrir_partida(salva=salva))

    def apagar_salva(self):
        def apagar():
            apagar_partida_salva()
            self.salva = None
            self.avisar("Partida salva apagada.", erro=False)
        self.confirmar("Apagar a partida salva", "A run em grupo salva some de vez (ninguém volta mais a ela).",
                       apagar, "Apagar")

    def entrar(self, endereco=None):
        nome = self.guardar_nome()
        if nome is None or self.conectando():
            return
        if endereco is None:
            try:
                endereco = endereco_digitado(self.campo_endereco.conteudo)
            except ValueError as erro:
                self.avisar(str(erro))
                return
            self.app.opcoes.ultimo_endereco = self.campo_endereco.conteudo.strip()
            self.app.salvar_opcoes()
        from telas.lobby import resumos_da_expedicao
        ip, porta = endereco
        self.app.partida = PartidaCliente(self.app.progresso, nome, self.cores[self.cor], ip, porta,
                                          resumos_da_expedicao(self.app), volta=self.app.opcoes.volta)
        self.avisar(f"Conectando a {ip}:{porta}...", erro=False)

    def minha_partida(self, partida):
        """A partida da lista é uma em andamento da qual eu faço parte (a chave de volta é dela)?"""
        volta = self.app.opcoes.volta or {}
        return partida.get("em_andamento") and partida.get("id_da_partida") and \
            partida["id_da_partida"] == volta.get("id_da_partida")

    def conectando(self):
        return self.app.partida is not None and not self.app.partida.encerrada

    def cancelar(self):
        if self.app.partida is not None:
            self.app.partida.fechar()
            self.app.partida = None
        self.avisar("Conexão cancelada.", erro=False)

    def voltar(self):
        if self.conectando():
            self.cancelar()
            return
        fluxo.ir_para_titulo(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)
        partida = self.app.partida
        if partida is not None and partida.no_lobby():          # o host aceitou: ao lobby
            fluxo.ir_para_acampamento(self.app)

    # ---------------- eventos ----------------
    def evento(self, e):
        for campo in (self.campo_nome, self.campo_endereco):
            if campo.evento(e) and e.type in (pygame.KEYDOWN, pygame.TEXTINPUT):
                if campo is self.campo_endereco and not campo.ativo and e.type == pygame.KEYDOWN and \
                        e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.entrar()                                    # Enter no campo do código = entrar
                return
        super().evento(e)

    def ativar(self, campo):
        for outro in (self.campo_nome, self.campo_endereco):
            outro.ativo = outro is campo

    # ---------------- desenho ----------------
    def desenhar_voce(self, tela):
        painel(tela, VOCE, "ferro")
        titulo_de_painel(tela, VOCE, "Você")
        self.campo_nome.desenhar(tela, self.mouse, self.tempo)
        self.botao(AreaClicavel(self.campo_nome.rect, lambda: self.ativar(self.campo_nome)))
        y = self.campo_nome.rect.bottom + 34
        linha(tela, "Sua cor", tema.mini(), tema.TEXTO_FRACO, (VOCE.x + 28, y - 18), 200)
        for i, cor in enumerate(self.cores):
            rect = pygame.Rect(VOCE.x + 24 + (i % 4) * 88, y + (i // 4) * 50, 78, 42)
            self.botao(Botao(rect, "", lambda k=i: setattr(self, "cor", k), selecionado=i == self.cor,
                             estilo="pedra"))
            pygame.draw.rect(tela, cor, rect.inflate(-18, -16), border_radius=4)
            if i == self.cor:
                pygame.draw.rect(tela, tema.OURO_CLARO, rect.inflate(-10, -8), 2, border_radius=5)
        nome = self.campo_nome.conteudo.strip() or "Seu nome"
        linha(tela, nome, tema.media(), self.cores[self.cor], (VOCE.centerx, VOCE.bottom - 34), VOCE.width - 40, "center")

    def desenhar_criar(self, tela):
        painel(tela, CRIAR, "ferro")
        topo = titulo_de_painel(tela, CRIAR, "Criar partida")
        if self.salva is not None:                        # uma run em grupo salva: retomar (ou apagar)
            paragrafo(tela, "Você hospeda: os outros entram pelo código do lobby ou pela lista da rede.",
                      tema.pequena(), tema.TEXTO, (CRIAR.x + 24, topo + 6), CRIAR.width - 48)
            caixa = painel(tela, (CRIAR.x + 16, CRIAR.bottom - 212, CRIAR.width - 32, 126), "pedra")
            linha(tela, "Partida salva (no meio da run)", tema.pequena(), tema.OURO_CLARO, (caixa.x + 14, caixa.y + 12),
                  caixa.width - 28)
            paragrafo(tela, resumo_da_partida_salva(self.salva), tema.mini(), tema.TEXTO, (caixa.x + 14, caixa.y + 36),
                      caixa.width - 28, maximo_linhas=2)
            self.botao(Botao((caixa.x + 14, caixa.bottom - 56, caixa.width - 136, 38), "Retomar partida", self.retomar,
                             estilo="ouro", ativo=not self.conectando(),
                             dica=("Retomar", "A run volta no ponto em que parou; o grupo entra de novo pelo código.")))
            self.botao(Botao((caixa.right - 114, caixa.bottom - 56, 100, 38), "Apagar", self.apagar_salva,
                             ativo=not self.conectando()))
        else:
            paragrafo(tela, "Você hospeda a partida: os outros entram pelo código que aparece no lobby ou pela lista "
                            "de partidas da rede. Até 4 jogadores e 5 heróis no total; cada um escolhe os seus na Capitã.",
                      tema.pequena(), tema.TEXTO, (CRIAR.x + 24, topo + 6), CRIAR.width - 48)
            paragrafo(tela, "Se o Windows perguntar, permita o jogo em Redes privadas.", tema.mini(), tema.TEXTO_FRACO,
                      (CRIAR.x + 24, CRIAR.bottom - 116), CRIAR.width - 48)
        self.botao(Botao((CRIAR.x + 24, CRIAR.bottom - 76, CRIAR.width - 48, 56), "Criar partida", self.criar,
                         estilo="pedra" if self.salva is not None else "ouro", ativo=not self.conectando()))

    def desenhar_entrar(self, tela):
        painel(tela, ENTRAR, "ferro")
        titulo_de_painel(tela, ENTRAR, "Entrar em partida")
        self.campo_endereco.desenhar(tela, self.mouse, self.tempo)
        self.botao(AreaClicavel(self.campo_endereco.rect, lambda: self.ativar(self.campo_endereco)))
        if self.conectando():
            self.botao(Botao((ENTRAR.right - 144, ENTRAR.y + 92, 120, 44), "Cancelar", self.cancelar))
        else:
            self.botao(Botao((ENTRAR.right - 144, ENTRAR.y + 92, 120, 44), "Entrar", lambda: self.entrar(), estilo="ouro"))
        y = ENTRAR.y + 156
        linha(tela, "Partidas na rede local", tema.normal(), tema.TEXTO_TITULO, (ENTRAR.x + 24, y), ENTRAR.width - 48)
        partidas = self.procurador.partidas()
        y += 34
        if not partidas:
            paragrafo(tela, "Procurando... (a lista se atualiza sozinha; se não aparecer, digite o código que o host vê "
                            "no lobby).", tema.pequena(), tema.TEXTO_FRACO, (ENTRAR.x + 24, y), ENTRAR.width - 48)
        for partida in partidas[:6]:
            minha = self.minha_partida(partida)
            pode = (partida["aberta"] or minha) and partida["mesma_versao"] and not self.conectando()
            titulo = f"Partida de {partida['nome']}"
            if not partida["mesma_versao"]:
                detalhe = f"versão {partida['versao']} (diferente)"
            elif minha:
                titulo, detalhe = f"Voltar à partida de {partida['nome']}", "em andamento · você estava nela"
            elif partida.get("em_andamento"):
                detalhe = "em andamento" + (f" · esperando {', '.join(partida['fora'])}" if partida.get("fora") else "")
            elif not partida["aberta"]:
                detalhe = "fechada (cheia)"
            else:
                detalhe = f"{partida['jogadores']}/{partida['maximo']} jogadores · {partida['ip']}"
            self.botao(Botao((ENTRAR.x + 24, y, ENTRAR.width - 48, 58), titulo,
                             (lambda p=partida: self.entrar((p["ip"], p["porta"]))), ativo=pode, subtexto=detalhe,
                             estilo="ouro" if minha and pode else "ferro"))
            y += 66
        paragrafo(tela, "Duas cópias no mesmo PC: abra a outra com --perfil B e entre em 127.0.0.1. Pela internet: "
                        "uma VPN (Tailscale, ZeroTier, Radmin) ou a porta aberta no roteador.", tema.mini(),
                  tema.TEXTO_FRACO, (ENTRAR.x + 24, ENTRAR.bottom - 84), ENTRAR.width - 48, maximo_linhas=3)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho(tela, "Jogar em grupo", "co-op na rede local")
        self.desenhar_voce(tela)
        self.desenhar_criar(tela)
        self.desenhar_entrar(tela)
        if self.mensagem:
            caixa = painel(tela, (16, 414, 796, 150), "pedra")
            CaixaTexto(caixa.inflate(-32, -24), tema.normal(), self.mensagem[1], alinhamento="centro",
                       vertical="meio").desenhar(tela, self.mensagem[0])
        self.botao(Botao((16, tema.ALTURA - 66, 180, 48), "Cancelar" if self.conectando() else "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
