"""Mapa da área: o grupo descansa e escolhe 1 entre 3 encontros.

Daqui também dá para abrir o Grupo (atributos, habilidades, equipamento),
o Baú e a Fabricação. A run é salva sempre que esta tela abre.
Quando uma opção vem de um guia (ex.: o Rato Branco), ele atravessa o cenário correndo ao fundo
e a carta mostra o bicho no lugar do ícone.
"""

import pygame

from roguelike.comandos import EscolherEncontro, IniciarFuga
from roguelike.status import dados_do_status
from telas import em_grupo, fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_da_run, desenhar_heroi_pequeno
from ui import tema
from ui.desenho import texto, painel, paragrafo, barra, estrelas, escurecer_tela, icone_status, anotar
from ui.icones import icone_encontro
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao


class TelaMapa(TelaComBotoes):
    def __init__(self, app, run, mensagens=()):
        super().__init__(app)
        self.run = run
        self.fundo = Fundo.da_run(run, escurecer=70)
        self.mensagens = [(m, 0.0) for m in mensagens]
        self.menu_aberto = False
        guia = self.guia_no_mapa()
        self.bicho = None
        if guia is not None:                       # o guia atravessa o cenário, entre as cartas e os botões
            from visual.bicho_correndo import BichoCorrendo
            self.bicho = BichoCorrendo(app.sprites, guia.sprite, chao_y=640)
            self.fundo.figurantes.append(self.bicho)

    def guia_no_mapa(self):
        """O guia de alguma opção deste mapa (ex.: o Rato Branco), ou None."""
        from roguelike.guias import guia
        chave = next((o.guia for o in self.run.opcoes_de_encontro() if getattr(o, "guia", None)), None)
        return guia(chave) if chave else None

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def em_grupo(self):
        """A run é de uma partida em grupo (rede/partida.py)?"""
        partida = self.app.partida
        return partida is not None and partida.run is self.run

    def chave_do_caminho(self):
        """A votação deste mapa (muda com a área, a fase, cada Mapa Rasgado e os portões do fim do ato: eles abrem
        na mesma fase e área do chefe, cuja votação já foi decidida)."""
        run = self.run
        portoes = "|portoes" if run.portoes else ""
        return f"caminho|{run.regiao_atual}|{run.area}|{run.mapas_usados}|{len(run.regioes_visitadas)}{portoes}"

    def preparar_votacao(self):
        """(No host) o caminho é votado: a opção vencedora vira o EscolherEncontro de todos."""
        opcoes = [i for i, o in enumerate(self.run.opcoes_de_encontro()) if not getattr(o, "bloqueado", False)]
        sessao, run = self.sessao(), self.run
        em_grupo.preparar(self, self.chave_do_caminho(), opcoes, lambda i: sessao.enviar(EscolherEncontro(indice=i)),
                          chave_atual=lambda: self.chave_do_caminho() if run.estado == "escolha" else None)

    # ---------------- ações ----------------
    def escolher(self, indice):
        if getattr(self.run.opcoes_de_encontro()[indice], "bloqueado", False):
            if self.run.opcoes_de_encontro()[indice].tipo == "entrada":
                self.app.notificar("Passagem selada", "Ainda não é hora de descer. Escolha outro caminho.")
            else:
                self.app.notificar("Portão selado", "Esta fase ainda está sendo preparada. Escolha outro caminho.")
            return
        if self.em_grupo():                        # em grupo: um voto (o host decide pela maioria)
            em_grupo.votar(self, self.chave_do_caminho(), indice)
            return
        if self.enviar(EscolherEncontro(indice=indice)):
            fluxo.resolver_encontro(self.app, self.run)

    def abrir_grupo(self, aba="herois"):
        """Heróis (atributos e golpes), o inventário com o baú da equipe ou a fabricação; todos voltam ao mapa."""
        if aba == "bau":
            fluxo.abrir_inventario(self.app, self.run, aba="bau")
        elif aba == "fabricacao":
            fluxo.abrir_fabricacao(self.app, self.run)
        else:
            from telas.grupo import TelaGrupo
            self.app.trocar(TelaGrupo(self.app, self.run, aba, lambda: fluxo.ir_para_mapa(self.app, self.run)))

    def musica(self):
        return self.run.musica()

    def voltar(self):
        self.menu_aberto = not self.menu_aberto

    def fugir_em_grupo(self):
        """(Só o host) a fuga é do grupo inteiro: todos vão para a luta contra o guardião."""
        self.menu_aberto = False
        self.abrir_dialogo("Sair da run", "O grupo inteiro enfrenta o guardião da saída (um chefe mais forte). "
                                          "Vencendo, cada um leva as suas peças para o arsenal.",
                           [("Enfrentar o guardião", lambda: self.enviar(IniciarFuga())), ("Continuar a run", None)])

    def sair_para_o_titulo(self):
        fluxo.salvar_run(self.run)
        fluxo.ir_para_titulo(self.app)

    def tecla(self, e):
        if self.menu_aberto:
            return
        if e.unicode in ("1", "2", "3"):
            indice = int(e.unicode) - 1
            if indice < len(self.run.opcoes_de_encontro()):
                self.escolher(indice)
        elif self.controles.eh(e, "grupo"):
            self.abrir_grupo("herois")
        elif self.controles.eh(e, "bau"):
            self.abrir_grupo("bau")
        elif self.controles.eh(e, "inventario"):
            fluxo.abrir_inventario(self.app, self.run)
        elif self.controles.eh(e, "fabricar"):
            self.abrir_grupo("fabricacao")

    # ---------------- desenho ----------------
    def pendencias(self, heroi):
        avisos = []
        if heroi.pontos_atributo:
            avisos.append(f"{heroi.pontos_atributo} pts atributo")
        if heroi.pontos_habilidade:
            avisos.append(f"{heroi.pontos_habilidade} pts habilidade")
        if heroi.golpes.pendentes:
            avisos.append("golpe novo!")
        return avisos

    def desenhar_grupo(self, tela):
        rect = painel(tela, (8, 68, 300, 560), "ferro")
        texto(tela, "Grupo", tema.normal(), tema.TEXTO_TITULO, (rect.x + 14, rect.y + 10))
        altura = min(104, (rect.height - 44) // max(1, len(self.run.grupo.herois)))
        for i, heroi in enumerate(self.run.grupo.herois):
            y = rect.y + 40 + i * altura
            area = pygame.Rect(rect.x + 8, y, rect.width - 16, altura - 6)
            botao = Botao(area, "", (lambda: self.abrir_grupo("herois")), estilo="pedra")
            self.botao(botao)
            tela.set_clip(area)
            desenhar_heroi_pequeno(tela, self.app.sprites, heroi, (area.x + 40, area.bottom - 4), 1)
            tela.set_clip(None)
            x = area.x + 84
            cor = tema.TEXTO_TITULO if heroi.esta_vivo() else tema.TEXTO_APAGADO
            texto(tela, f"{heroi.nome}  nv {heroi.nivel}", tema.pequena(), cor, (x, area.y + 6))
            texto(tela, heroi.nome_da_classe(), tema.mini(), tema.TEXTO_FRACO, (x, area.y + 26))
            if self.em_grupo() and heroi.jogador is not None:          # de quem é o herói, na cor do jogador
                texto(tela, heroi.jogador.nome, tema.mini(), heroi.jogador.cor or tema.TEXTO,
                      (area.right - 8, area.y + 8), "topright")
            if heroi.esta_vivo():
                barra(tela, (x, area.y + 46, area.right - x - 46, 8), heroi.vida / heroi.vida_maxima, tema.VIDA_HEROI, marcas=0)
                texto(tela, f"{heroi.vida}", tema.mini(), tema.TEXTO, (area.right - 8, area.y + 42), "topright")
                barra(tela, (x, area.y + 60, area.right - x - 46, 4), heroi.xp / max(1, heroi.xp_para_proximo_nivel()),
                      tema.XP, marcas=0)
            else:
                texto(tela, "Caído", tema.pequena(), tema.SANGUE_CLARO, (x, area.y + 44))
            if heroi.peste > 0:                                  # a Peste segue entre as lutas
                icone = icone_status("peste")
                canto = (area.right - icone.get_width() - 8, area.y + 8)
                tela.blit(icone, canto)
                texto(tela, str(heroi.peste), tema.fonte(11), tema.TEXTO, (canto[0] + icone.get_width() - 2, canto[1] + 10))
                if pygame.Rect(canto, icone.get_size()).collidepoint(self.mouse):
                    self.dica = (f"Peste {heroi.peste}", dados_do_status("peste")["descricao"])
            avisos = self.pendencias(heroi)
            if avisos and altura > 70:
                texto(tela, " · ".join(avisos), tema.mini(), tema.OURO_CLARO, (x, area.y + 70))

    def desenhar_portao(self, tela, indice, encontro, rect):
        """Portão do fim de ato: retrato da fase, nome e descrição (selado = fase ainda sem conteúdo)."""
        from visual.cenario_macabro import miniatura_da_fase
        destaque = rect.collidepoint(self.mouse) and not self.menu_aberto and not encontro.bloqueado
        estilo = "ouro" if destaque else ("pedra" if encontro.bloqueado else "ferro")
        self.botao(Botao(rect, "", (lambda i=indice: self.escolher(i)), estilo=estilo))
        texto(tela, str(indice + 1), tema.normal(), tema.OURO, (rect.x + 14, rect.y + 10))
        retrato = pygame.Rect(rect.x + 14, rect.y + 44, rect.width - 28, 156)
        tela.blit(miniatura_da_fase(encontro.destino, retrato.width, retrato.height), retrato)
        if encontro.bloqueado:
            escuro = pygame.Surface(retrato.size, pygame.SRCALPHA)
            escuro.fill((0, 0, 0, 170))
            tela.blit(escuro, retrato)
            texto(tela, "SELADO", tema.grande(), tema.TEXTO_APAGADO, retrato.center, "center")
        pygame.draw.rect(tela, tema.OURO_ESCURO, retrato, 2)
        y = retrato.bottom + 12
        texto(tela, f"PORTÃO · {encontro.ato.upper()}", tema.mini(), tema.TEXTO_FRACO, (rect.centerx, y), "midtop")
        cor = tema.TEXTO_APAGADO if encontro.bloqueado else tema.TEXTO_TITULO
        y = CaixaTexto(pygame.Rect(rect.x + 12, y + 20, rect.width - 24, 62), tema.media(), cor,
                       alinhamento="centro", maximo_linhas=2).desenhar(tela, encontro.nome)
        CaixaTexto(pygame.Rect(rect.x + 18, y + 6, rect.width - 36, rect.bottom - y - 20), tema.pequena(),
                   tema.TEXTO_FRACO if encontro.bloqueado else tema.TEXTO, alinhamento="centro").desenhar(
            tela, encontro.descricao)

    def desenhar_guia(self, tela, chave, pe):
        """O guia na carta, respirando no lugar do ícone (pés em 'pe')."""
        from roguelike.guias import guia
        sprite = guia(chave).sprite
        sprites = self.app.sprites
        quadro = int(self.tempo * 5) % sprites.quadros_de(sprite, "parado")
        imagem = sprites.quadro(sprite, "parado", quadro, 2)
        ax, ay = sprites.ancora(sprite, 2)
        tela.blit(imagem, (round(pe[0] - ax), round(pe[1] - ay)))

    def desenhar_opcao(self, tela, indice, encontro, rect):
        if encontro.tipo == "portao":
            self.desenhar_portao(tela, indice, encontro, rect)
            return
        bloqueado = getattr(encontro, "bloqueado", False)
        destaque = rect.collidepoint(self.mouse) and not self.menu_aberto and not bloqueado
        perigo = encontro.tipo in ("elite", "nomeado", "mini_chefe", "chefe")
        estilo = "ouro" if destaque else ("pedra" if bloqueado else ("sangue" if perigo else "ferro"))
        botao = Botao(rect, "", (lambda i=indice: self.escolher(i)), estilo=estilo)
        self.botao(botao)
        texto(tela, str(indice + 1), tema.normal(), tema.OURO, (rect.x + 14, rect.y + 10))
        icone = icone_encontro(encontro.icone(), 7)
        if getattr(encontro, "guia", None):
            self.desenhar_guia(tela, encontro.guia, (rect.centerx, rect.y + 20 + icone.get_height() - 4))
            tipo = "SEGREDO · SELADO" if bloqueado else "SEGREDO"
        else:
            tela.blit(icone, icone.get_rect(midtop=(rect.centerx, rect.y + 20)))
            tipo = encontro.nome_do_tipo().upper()
        y = rect.y + 20 + icone.get_height() + 10
        texto(tela, tipo, tema.mini(), tema.SANGUE_CLARO if bloqueado else tema.TEXTO_FRACO, (rect.centerx, y), "midtop")
        y += 20
        y = CaixaTexto(pygame.Rect(rect.x + 12, y, rect.width - 24, 62), tema.media(),
                       tema.TEXTO_APAGADO if bloqueado else tema.TEXTO_TITULO,
                       alinhamento="centro", maximo_linhas=2).desenhar(tela, encontro.nome)
        if encontro.eh_combate():
            estrelas(tela, (rect.centerx - 46, y + 2), encontro.estrelas, 5, 8)
            y += 30
        y = paragrafo(tela, encontro.descricao, tema.pequena(), tema.TEXTO, (rect.x + 18, y + 4), rect.width - 36,
                      maximo_linhas=5, encolher=True)
        if encontro.eh_combate():
            texto(tela, encontro.texto_recompensa(), tema.mini(), tema.OURO, (rect.centerx, rect.bottom - 14), "midbottom")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_da_run(tela, self.run, jogador=self.meu_jogador())
        self.desenhar_grupo(tela)

        opcoes = self.run.opcoes_de_encontro()
        portoes = bool(opcoes) and opcoes[0].tipo == "portao"
        titulo = f"Fim do {self.run.nome_do_ato()}: escolha o portão" if portoes else "Escolha o próximo caminho"
        texto(tela, titulo, tema.media(), tema.OURO_CLARO if portoes else tema.TEXTO_TITULO, (796, 80), "midtop")
        largura = 300
        total = len(opcoes) * largura + (len(opcoes) - 1) * 16
        x0 = 796 - total // 2
        if self.em_grupo():
            self.preparar_votacao()
        for i, encontro in enumerate(opcoes):
            rect = pygame.Rect(x0 + i * (largura + 16), 120, largura, 440)
            self.desenhar_opcao(tela, i, encontro, rect)
            if self.em_grupo():                    # quem votou nesta carta (na cor de cada um)
                em_grupo.desenhar_votos(tela, self.app.partida, self.chave_do_caminho(), i, (rect.centerx, rect.bottom - 34))
        if len(opcoes) == 1 and opcoes[0].tipo == "chefe":
            texto(tela, "O chefe da região espera. Prepare o grupo antes!", tema.normal(), tema.SANGUE_CLARO,
                  (796, 574), "midtop")

        # barra de baixo
        acoes = [("Grupo", "G", lambda: self.abrir_grupo("herois")),
                 ("Inventário", "I", lambda: fluxo.abrir_inventario(self.app, self.run)),
                 ("Baú", "B", lambda: self.abrir_grupo("bau")),
                 ("Fabricação", "F", lambda: self.abrir_grupo("fabricacao")), ("Menu", "ESC", self.voltar)]
        for i, (nome, atalho, acao) in enumerate(acoes):
            self.botao(Botao((322 + i * 186, tema.ALTURA - 62, 176, 48), nome, acao, atalho))

        if self.em_grupo():
            self.desenhar_partida(tela)

        # mensagens (descanso, chegada numa região...)
        y = tema.ALTURA - 116
        for i, (mensagem, inicio) in enumerate(self.mensagens[-3:]):
            texto(tela, mensagem, tema.pequena(), tema.CURA if "Descanso" in mensagem else tema.OURO_CLARO,
                  (tema.LARGURA - 16, y + i * 20 - 40), "topright")

        if self.menu_aberto:
            self.botoes = []          # com o menu aberto, só os botões dele respondem
            self.dica = None
            self.desenhar_menu(tela)
        self.terminar_desenho(tela)

    def desenhar_partida(self, tela):
        """Faixa da partida em grupo: quem joga (na cor de cada um) e se todos estão com o mesmo estado."""
        partida = self.app.partida
        rect = painel(tela, (322, tema.ALTURA - 112, 930, 42), "pedra")
        x = rect.x + 16
        for jogador in self.run.grupo.jogadores:
            fora = jogador.id in getattr(partida, "desconectados", ())
            nome = jogador.nome + (" (caiu)" if fora else "")
            desenhado = texto(tela, nome, tema.pequena(), tema.TEXTO_APAGADO if fora else (jogador.cor or tema.TEXTO),
                              (x, rect.centery), "midleft")
            medida = None if fora else em_grupo.latencia(partida, jogador.id)
            if medida is not None:                         # a ida e volta até o host
                desenhado = texto(tela, medida[0], tema.mini(), medida[1], (desenhado.right + 6, rect.centery + 1),
                                  "midleft")
            x = desenhado.right + 18
        valores = [partida.sincronia.get(j.id) for j in self.run.grupo.jogadores]
        if False in valores:
            estado, cor = "estado DIFERENTE", tema.SANGUE_CLARO
        elif None in valores:
            estado, cor = "conferindo...", tema.TEXTO_FRACO
        else:
            estado, cor = "mesmo estado", tema.CURA
        direita = texto(tela, estado, tema.pequena(), cor, (rect.right - 16, rect.centery), "midright")
        votacao = em_grupo.texto_da_votacao(partida, self.chave_do_caminho(), "Caminho")   # quem falta votar e o tempo
        linha(tela, votacao, tema.pequena(), tema.OURO_CLARO, ((x + direita.x) // 2, rect.centery),
              max(40, direita.x - x - 24), "center")

    def desenhar_menu(self, tela):
        escurecer_tela(tela, 170)
        anotar("modal", tela.get_rect(), tela)              # o menu fica por cima do mapa (conferência)
        opcoes = [("Continuar", self.voltar), (f"Velocidade do combate: {self.app.velocidade:g}x", self.trocar_velocidade),
                  ("Opções", self.abrir_opcoes), ("Sair da run (fuga)", self.perguntar_fuga),
                  ("Salvar e voltar ao título", self.sair_para_o_titulo)]
        if self.em_grupo():                        # (a fuga é do grupo: só o host; a partida fica salva com ele)
            sair = "Fechar a partida" if self.app.partida.eh_host else "Sair da partida"
            extras = [("Enviar ouro", lambda: em_grupo.abrir_envio_de_ouro(self))]
            if self.app.partida.eh_host:
                extras.append(("Sair da run (fuga)", self.fugir_em_grupo))
            opcoes = opcoes[:3] + extras + [(sair, self.perguntar_saida_da_partida)]
        rect = painel(tela, pygame.Rect(tema.LARGURA // 2 - 190, 150, 380, max(386, 96 + len(opcoes) * 58)), "pedra")
        texto(tela, "Menu", tema.grande(), tema.TEXTO_TITULO, (rect.centerx, rect.y + 16), "midtop")
        for i, (nome, acao) in enumerate(opcoes):
            self.botao(Botao((rect.x + 30, rect.y + 80 + i * 58, rect.width - 60, 46), nome, acao))

    def perguntar_saida_da_partida(self):
        self.menu_aberto = False
        texto_saida = ("Fechar a partida? Todos saem, mas a run fica salva: \"Retomar partida\" (em Jogar em grupo) "
                       "continua de onde parou." if self.app.partida.eh_host else
                       "Sair da partida? O grupo continua (a IA joga pelos seus heróis) e você pode voltar pelo código.")
        self.abrir_dialogo("Sair", texto_saida, [("Sair", lambda: fluxo.sair_da_partida(self.app)), ("Ficar", None)])

    def perguntar_fuga(self):
        self.menu_aberto = False
        self.abrir_dialogo("Sair da run",
                           "Para sair, o grupo enfrenta um guardião: um chefe sorteado, mais forte que o normal. "
                           "Vencendo, a run termina e os equipamentos vão para o arsenal do acampamento. "
                           "Perdendo, tudo se perde.",
                           [("Enfrentar o guardião", self.fugir), ("Continuar a run", None)])

    def fugir(self):
        if self.enviar(IniciarFuga()):
            fluxo.resolver_encontro(self.app, self.run)

    def trocar_velocidade(self):
        self.app.opcoes.proxima_velocidade_combate()
        self.app.salvar_opcoes()

    def abrir_opcoes(self):
        from telas.opcoes import TelaOpcoes
        self.app.trocar(TelaOpcoes(self.app, lambda: self.app.trocar(self)))
