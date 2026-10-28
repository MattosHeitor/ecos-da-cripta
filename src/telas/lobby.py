"""Lobby de uma partida em grupo, desenhado sobre a cena do acampamento (é uma TelaAcampamento).

Em volta da fogueira sentam os heróis de TODOS os jogadores, com o nome do dono na cor dele; um emote aparece
num balão sobre os heróis de quem mandou. Os NPCs continuam funcionando (Capitã, Mago, Espelho...) e voltam
para cá (fluxo.ir_para_acampamento); abrir um deles tira o "Pronto" (os heróis podem mudar).

    ┌ Jogadores 2/4 ───┐                                   ┌ Conversa ─────────┐
    │ ● Ana (host) ✓   │        (a cena com os heróis)     │ Ana: bora!        │
    │ ● Bia  3 heróis  │                                   │ [escreva...]      │
    │ código 30AG-00F  │                                   │ emotes            │
    └──────────────────┘                                   └───────────────────┘
    [Sair]  [Ajustar meus heróis]  [Pronto!]  [Iniciar]          o que falta para começar

O host vê o código da partida (e o IP), pode tirar alguém e inicia quando todos estiverem prontos. Com mais de
uma rede no PC (ex.: Radmin VPN), o host troca qual IP o código mostra. Os dois painéis recolhem (▲) numa aba
pequena para ver a cena; a aba da conversa conta as mensagens novas e mostra a última por alguns segundos.
"""

import pygame

from roguelike.classes import todas_as_classes
from rede.codigo import codigo_de, ips_deste_pc, nome_da_rede
from rede.protocolo import configuracao
from telas import em_grupo, fluxo
from telas.acampamento import TelaAcampamento
from telas.comum import sprite_da_vaga
from ui import tema
from ui.desenho import anotar, desenhar_placa, painel, titulo_de_painel, texto
from ui.componentes import AreaClicavel
from ui.texto import CaixaTexto, largura_do_texto, linha, quebrar_linhas
from ui.widgets import Botao, CampoDeTexto

JOGADORES = pygame.Rect(16, 66, 330, 420)
CONVERSA = pygame.Rect(934, 66, 330, 420)
ALTURA_DO_EMOTE = 32
ABA_JOGADORES = pygame.Rect(JOGADORES.x, JOGADORES.y, 250, 56)           # os painéis recolhidos
ABA_CONVERSA = pygame.Rect(CONVERSA.right - 250, CONVERSA.y, 250, 56)
SEGUNDOS_DA_ULTIMA_FALA = 6.0            # com a conversa recolhida, a fala nova aparece embaixo da aba


def resumos_da_expedicao(app):
    """Os heróis da minha expedição como o lobby mostra: nome, classe, raça e o sprite (com as minhas skins)."""
    progresso = app.progresso
    resumos = []
    for vaga in progresso.expedicao_atual().vagas:
        classe = todas_as_classes()[vaga.classe]
        resumos.append({"nome": vaga.nome or classe.nome, "classe": vaga.classe, "raca": vaga.raca,
                        "sprite": sprite_da_vaga(progresso, vaga)})
    return resumos


class VagaDoLobby:
    """Um herói de algum jogador, sentado na fogueira do lobby."""

    def __init__(self, resumo, jogador):
        self.nome = resumo.get("nome", "")
        self.classe = resumo.get("classe", "")
        self.raca = resumo.get("raca", "humano")
        self.sprite = resumo.get("sprite", "")
        self.jogador = jogador


class TelaLobby(TelaAcampamento):
    def __init__(self, app):
        super().__init__(app)
        self.partida = app.partida
        regras_da_rede = configuracao()
        self.campo_chat = CampoDeTexto((CONVERSA.x + 14, CONVERSA.bottom - 58, CONVERSA.width - 28, 42), "",
                                       maximo=regras_da_rede["maximo_do_chat"], dica="Escreva e aperte Enter",
                                       enviar_com_enter=True)
        self._sprites_seguros = {}
        meu = self.partida.meu()
        resumos = resumos_da_expedicao(app)
        if meu is not None and meu.herois != resumos:                 # mudou algo na Capitã/Mago/Baú
            self.partida.definir_meus_herois(resumos)
        self.ips = ips_deste_pc() if self.partida.eh_host else []
        if self.partida.ip_mostrado not in self.ips:
            self.partida.ip_mostrado = self.ips[0] if self.ips else None
        self.falas_vistas = self.partida.lobby.falas        # para saber quando chegou uma fala nova
        self.chegou_em = None

    # ---------------- painéis ----------------
    @property
    def endereco(self):
        """(ip, porta) que o código mostra (host) ou None."""
        return (self.partida.ip_mostrado, self.partida.porta) if self.partida.eh_host else None

    def recolhido(self, painel):
        return self.app.opcoes.lobby_recolhido.get(painel, False)

    def recolher(self, painel, recolher=True):
        """Minimiza (ou abre de novo) "jogadores" ou "conversa"; fica guardado nas Opções."""
        self.app.opcoes.lobby_recolhido[painel] = recolher
        self.app.salvar_opcoes()
        if painel == "conversa" and recolher:
            self.campo_chat.ativo = False

    def novas_na_conversa(self):
        """As mensagens dos outros que chegaram enquanto a conversa estava recolhida."""
        lobby = self.partida.lobby
        return [m for m in lobby.ultimas(lobby.falas - self.partida.conversa_lida) if m.autor != self.partida.eu]

    def trocar_ip(self):
        """O próximo IP deste PC (rede local, Radmin, Tailscale...) no código da partida."""
        if len(self.ips) > 1:
            atual = self.ips.index(self.partida.ip_mostrado) if self.partida.ip_mostrado in self.ips else -1
            self.partida.ip_mostrado = self.ips[(atual + 1) % len(self.ips)]

    # ---------------- quem está na cena ----------------
    def vagas(self):
        return [VagaDoLobby(resumo, jogador) for jogador in self.partida.lobby.jogadores
                for resumo in jogador.herois][:5]

    def sprite_do_heroi(self, vaga):
        """O sprite que o dono mandou (conferido uma vez: nome estranho vira o padrão da classe)."""
        if vaga.sprite not in self._sprites_seguros:
            seguro = None
            try:
                if self.app.sprites.existe(vaga.sprite):
                    self.app.sprites.quadro(vaga.sprite, "parado", 0, 2)
                    seguro = vaga.sprite
            except Exception:
                seguro = None
            if seguro is None:
                classe = todas_as_classes().get(vaga.classe) or next(iter(todas_as_classes().values()))
                seguro = classe.sprite_da_aparencia(classe.aparencia_padrao)
            self._sprites_seguros[vaga.sprite] = seguro
        return self._sprites_seguros[vaga.sprite]

    @staticmethod
    def placa_do_heroi(vaga):
        classe = todas_as_classes().get(vaga.classe)
        return vaga.nome or "?", f"{classe.nome if classe else '?'} · de {vaga.jogador.nome}"

    # ---------------- ações ----------------
    def abrir(self, chave):
        """Os NPCs abrem como no acampamento; os heróis podem mudar, então o "Pronto" sai."""
        meu = self.partida.meu()
        if meu is not None and meu.pronto:
            self.partida.marcar_pronto(False)
        super().abrir(chave)

    def ajustar_herois(self):
        self.abrir("capitao")

    def alternar_pronto(self):
        meu = self.partida.meu()
        if meu is None:
            return
        if meu.pronto:
            self.partida.marcar_pronto(False)
            return
        motivo = self.partida.marcar_pronto(True, self.app.progresso.pacote_para_partida())
        if motivo:
            self.app.notificar("Não deu", motivo, som="voltar")

    def iniciar(self):
        semente = self.app.progresso.expedicao_atual().semente
        motivo = self.partida.iniciar(semente)
        if motivo:
            self.app.notificar("Ainda não", motivo, som="voltar")

    def voltar(self):
        texto_saida = "Fechar a partida? Todos voltam ao título." if self.partida.eh_host else "Sair da partida?"
        self.abrir_dialogo("Sair", texto_saida, [("Sair", lambda: fluxo.sair_da_partida(self.app)), ("Ficar", None)])

    def perguntar_expulsao(self, jogador):
        self.abrir_dialogo("Tirar da partida", f"Tirar {jogador.nome} da partida?",
                           [("Tirar", lambda: self.partida.expulsar(jogador.id)), ("Cancelar", None)])

    # ---------------- eventos ----------------
    def evento(self, e):
        if self.dialogo is None and not self.recolhido("conversa") and self.campo_chat.evento(e) and e.type in (
                pygame.KEYDOWN, pygame.TEXTINPUT):
            enviado = self.campo_chat.pegar_enviado()
            if enviado:
                self.partida.falar_no_chat(enviado)
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.campo_chat.ativo = False
            return
        super().evento(e)

    def tecla(self, e):
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_t) and not self.usando_teclado:
            if self.recolhido("conversa"):                  # Enter (ou T) abre a conversa
                self.recolher("conversa", False)
            self.campo_chat.ativo = True
            return
        super().tecla(e)

    # ---------------- desenho ----------------
    def desenhar_etiquetas(self, tela, desenhados):
        """O nome do dono, na cor dele, sobre cada herói; o balão do emote sobre o primeiro herói de cada um."""
        com_balao = set()
        vagas = self.vagas()
        for imagem, posicao, _, quem in desenhados:
            if not (isinstance(quem, tuple) and quem[0] == "heroi") or quem[1] >= len(vagas):
                continue
            vaga = vagas[quem[1]]
            caixa = imagem.get_bounding_rect().move(posicao)
            fonte = tema.mini()
            largura = min(130, fonte.size(vaga.jogador.nome)[0] + 16)
            etiqueta = pygame.Rect(0, 0, largura, 20)
            etiqueta.midbottom = (caixa.centerx, caixa.top - 2)
            fundo = pygame.Surface(etiqueta.size, pygame.SRCALPHA)
            fundo.fill((10, 6, 12, 190))
            tela.blit(fundo, etiqueta)
            pygame.draw.rect(tela, vaga.jogador.cor, etiqueta, 1, border_radius=3)
            linha(tela, vaga.jogador.nome, fonte, vaga.jogador.cor, etiqueta.center, etiqueta.width - 8, "center")
            balao = self.partida.balao_de(vaga.jogador.id)
            if balao and vaga.jogador.id not in com_balao:
                com_balao.add(vaga.jogador.id)
                largura = min(220, tema.pequena().size(balao)[0] + 24)
                rect = pygame.Rect(0, 0, largura, 30)
                rect.midbottom = (caixa.centerx, etiqueta.top - 6)
                painel(tela, rect, "osso")
                linha(tela, balao, tema.pequena(), tema.TEXTO, rect.center, rect.width - 14, "center")

    def botao_de_recolher(self, rect, painel_):
        self.botao(Botao((rect.right - 40, rect.y + 9, 28, 28), "▲", lambda: self.recolher(painel_), estilo="pedra",
                         dica=("Minimizar", "Recolhe o painel numa aba pequena (clique nela para abrir de novo).")))

    def desenhar_aba_dos_jogadores(self, tela):
        lobby = self.partida.lobby
        prontos = sum(1 for j in lobby.jogadores if j.pronto)
        sub = f"{prontos}/{len(lobby.jogadores)} pronto" + ("s" if len(lobby.jogadores) != 1 else "")
        if self.partida.eh_host:
            sub += " · " + codigo_de(*self.endereco)
        self.botao(Botao(ABA_JOGADORES, f"Jogadores {len(lobby.jogadores)}/{configuracao()['max_jogadores']}  ▼",
                         lambda: self.recolher("jogadores", False), subtexto=sub,
                         dica=("Jogadores", "Abrir o painel de novo.")))

    def desenhar_aba_da_conversa(self, tela):
        novas = self.novas_na_conversa()
        sub = (f"{len(novas)} mensage" + ("ns novas" if len(novas) != 1 else "m nova")) if novas else "nada novo"
        self.botao(Botao(ABA_CONVERSA, "Conversa  ▼", lambda: self.recolher("conversa", False), subtexto=sub,
                         estilo="ouro" if novas else "ferro", cor_texto=tema.OURO_CLARO if novas else tema.TEXTO,
                         dica=("Conversa", "Abrir a conversa (ou aperte Enter/T).")))
        lobby = self.partida.lobby
        if lobby.falas != self.falas_vistas:
            self.falas_vistas = lobby.falas
            self.chegou_em = self.tempo if novas and lobby.chat[-1] is novas[-1] else None
        if novas and self.chegou_em is not None and self.tempo - self.chegou_em < SEGUNDOS_DA_ULTIMA_FALA:
            ultima = novas[-1]
            fala = ultima.texto if ultima.sistema else f"{ultima.nome}: {ultima.texto}"
            fonte = tema.pequena()
            largura = min(CONVERSA.width, fonte.size(fala)[0] + 28)
            rect = pygame.Rect(CONVERSA.right - largura, ABA_CONVERSA.bottom + 6, largura, 34)
            painel(tela, rect, "osso")
            linha(tela, fala, fonte, tema.TEXTO if ultima.sistema else ultima.cor, rect.center, rect.width - 20,
                  "center")

    def desenhar_jogadores(self, tela):
        lobby = self.partida.lobby
        if self.recolhido("jogadores"):
            self.desenhar_aba_dos_jogadores(tela)
            return
        painel(tela, JOGADORES, "ferro")
        topo = titulo_de_painel(tela, JOGADORES, f"Jogadores {len(lobby.jogadores)}/{configuracao()['max_jogadores']}")
        self.botao_de_recolher(JOGADORES, "jogadores")
        y = topo + 2
        for jogador in lobby.jogadores:
            linha_rect = pygame.Rect(JOGADORES.x + 12, y, JOGADORES.width - 24, 56)
            painel(tela, linha_rect, "ouro" if jogador.id == self.partida.eu else "pedra")
            pygame.draw.circle(tela, jogador.cor, (linha_rect.x + 20, linha_rect.centery), 9)
            pygame.draw.circle(tela, (20, 12, 16), (linha_rect.x + 20, linha_rect.centery), 9, 2)
            nome = jogador.nome + (" (host)" if jogador.host else "") + (" · você" if jogador.id == self.partida.eu else "")
            linha(tela, nome, tema.pequena(), jogador.cor, (linha_rect.x + 38, linha_rect.y + 8), linha_rect.width - 110)
            herois = len(jogador.herois)
            linha(tela, f"{herois} herói" + ("s" if herois != 1 else ""), tema.mini(), tema.TEXTO_FRACO,
                  (linha_rect.x + 38, linha_rect.y + 32), 120)
            estado, cor = ("Pronto", tema.CURA) if jogador.pronto else ("escolhendo...", tema.TEXTO_FRACO)
            linha(tela, estado, tema.pequena(), cor, (linha_rect.right - 12, linha_rect.y + 8), 110, "topright")
            medida = em_grupo.latencia(self.partida, jogador.id)      # a ida e volta até o host
            if medida is not None:
                com_tirar = self.partida.eh_host and not jogador.host
                linha(tela, medida[0], tema.mini(), medida[1], (linha_rect.right - (78 if com_tirar else 12),
                                                                 linha_rect.y + 32), 70, "topright")
            if self.partida.eh_host and not jogador.host:
                self.botao(Botao((linha_rect.right - 70, linha_rect.y + 28, 60, 24), "Tirar",
                                 (lambda j=jogador: self.perguntar_expulsao(j)),
                                 dica=("Tirar da partida", f"{jogador.nome} volta para a tela de jogar em grupo.")))
            y += 62
        base = JOGADORES.bottom - 128
        if self.partida.eh_host:
            ip, porta = self.endereco
            linha(tela, f"Código da partida · {nome_da_rede(ip)}", tema.mini(), tema.TEXTO_FRACO,
                  (JOGADORES.centerx, base), JOGADORES.width - 24, "midtop")
            linha(tela, codigo_de(ip, porta), tema.grande(), tema.OURO_CLARO, (JOGADORES.centerx, base + 18), 300, "midtop")
            porta_extra = "" if porta == configuracao()["porta"] else f":{porta}"
            if len(self.ips) > 1:                       # mais de uma rede (ex.: Radmin VPN): o host escolhe
                botao = Botao((JOGADORES.x + 12, base + 64, JOGADORES.width - 24, 26),
                              f"IP {ip}{porta_extra} · trocar de rede", self.trocar_ip, estilo="pedra",
                              dica=("Outra rede", f"Este PC está em {len(self.ips)} redes. Mostre o código da rede em "
                                                  "que os outros estão (jogando pela Radmin VPN, o IP dela)."))
                botao.fontes = [tema.mini()]
                self.botao(botao)
            else:
                linha(tela, f"IP {ip}{porta_extra}", tema.mini(), tema.TEXTO_FRACO, (JOGADORES.centerx, base + 70),
                      JOGADORES.width - 24, "midtop")
            linha(tela, f"no mesmo PC: 127.0.0.1{porta_extra}", tema.mini(), tema.TEXTO_FRACO,
                  (JOGADORES.centerx, base + 94), JOGADORES.width - 24, "midtop")
        else:
            host = lobby.host()
            linha(tela, f"Partida de {host.nome if host else '?'}", tema.normal(), tema.TEXTO_TITULO,
                  (JOGADORES.centerx, base + 30), JOGADORES.width - 24, "midtop")

    def desenhar_conversa(self, tela):
        if self.recolhido("conversa"):
            self.desenhar_aba_da_conversa(tela)
            return
        self.partida.conversa_lida = self.partida.lobby.falas          # aberta: tudo lido
        self.falas_vistas = self.partida.lobby.falas
        painel(tela, CONVERSA, "ferro")
        topo = titulo_de_painel(tela, CONVERSA, "Conversa")
        self.botao_de_recolher(CONVERSA, "conversa")
        emotes_y = self.campo_chat.rect.y - 8 - 2 * (ALTURA_DO_EMOTE + 4)     # os emotes entre as falas e o campo
        area = pygame.Rect(CONVERSA.x + 16, topo, CONVERSA.width - 32, emotes_y - topo - 6)
        fonte = tema.pequena()
        altura_linha = fonte.get_linesize()
        linhas = []                                    # (pedaço, prefixo na cor do jogador, cor dele, cor do resto)
        for mensagem in self.partida.lobby.chat:
            if mensagem.sistema:
                prefixo, corpo, resto = "", mensagem.texto, tema.TEXTO_FRACO
            elif mensagem.emote:
                prefixo, corpo, resto = "", f"* {mensagem.nome}: {mensagem.texto}", mensagem.cor
            else:
                prefixo = f"{mensagem.nome}: "
                corpo, resto = prefixo + mensagem.texto, tema.TEXTO
            for i, pedaco in enumerate(quebrar_linhas(corpo, fonte, area.width)):
                linhas.append((pedaco, prefixo if i == 0 else "", mensagem.cor, resto))
        cabem = max(1, area.height // altura_linha)
        y = area.bottom - min(cabem, len(linhas)) * altura_linha
        for pedaco, prefixo, cor, resto in linhas[-cabem:]:
            if prefixo and pedaco.startswith(prefixo):
                texto(tela, prefixo, fonte, cor, (area.x, y))
                texto(tela, pedaco[len(prefixo):], fonte, resto, (area.x + largura_do_texto(prefixo, fonte), y))
            else:
                texto(tela, pedaco, fonte, resto, (area.x, y))
            y += altura_linha
        self.campo_chat.desenhar(tela, self.mouse, self.tempo, tema.pequena())
        self.botao(AreaClicavel(self.campo_chat.rect, lambda: setattr(self.campo_chat, "ativo", True)))
        emotes = configuracao()["emotes"]
        largura = (CONVERSA.width - 28 - 2 * 6) // 3
        for i, emote in enumerate(emotes[:6]):
            rect = (CONVERSA.x + 14 + (i % 3) * (largura + 6), emotes_y + (i // 3) * (ALTURA_DO_EMOTE + 4), largura,
                    ALTURA_DO_EMOTE)
            self.botao(Botao(rect, emote, (lambda k=i: self.partida.mandar_emote(k)), estilo="pedra",
                             dica=("Emote", "Aparece num balão sobre os seus heróis e na conversa.")))

    def desenhar_barra(self, tela):
        meu = self.partida.meu()
        pronto = meu is not None and meu.pronto
        self.botao(Botao((16, tema.ALTURA - 60, 140, 46), "Sair", self.voltar, "ESC"))
        self.botao(Botao((166, tema.ALTURA - 60, 250, 46), "Ajustar meus heróis", self.ajustar_herois,
                         dica=("Capitã", "Classe, nome e quantos heróis você leva (raça e visual pelo cartão).")))
        self.botao(Botao((426, tema.ALTURA - 60, 200, 46), "Não estou pronto" if pronto else "Pronto!",
                         self.alternar_pronto, estilo="pedra" if pronto else "ouro"))
        if self.partida.eh_host:
            motivo = self.partida.motivo_para_nao_iniciar()
            self.botao(Botao((636, tema.ALTURA - 60, 200, 46), "Iniciar", self.iniciar, ativo=motivo is None,
                             estilo="ouro", dica=("Iniciar a run", motivo or "Todos prontos: a expedição parte!")))
            aviso = motivo or "Todos prontos!"
        else:
            aviso = "Esperando o host iniciar." if pronto else "Escolha seus heróis e marque Pronto."
        CaixaTexto((850, tema.ALTURA - 62, tema.LARGURA - 866, 50), tema.pequena(), tema.OURO_CLARO, alinhamento="centro",
                   vertical="meio", maximo_linhas=2).desenhar(tela, aviso)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.em_destaque = self.registrar_areas()
        desenhados = self.desenhar_cena(tela)
        self.desenhar_etiquetas(tela, desenhados)
        anotar("modal", tela.get_rect(), tela)            # o lobby fica por cima da cena (conferência)
        desenhar_placa(tela, (tema.LARGURA // 2, 34), "Partida em grupo", tema.media(), tema.OURO_CLARO)
        self.desenhar_jogadores(tela)
        self.desenhar_conversa(tela)
        self.desenhar_nome(tela, desenhados)
        self.desenhar_barra(tela)
        self.terminar_desenho(tela)
