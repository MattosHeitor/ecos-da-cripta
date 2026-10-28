"""Entre as ondas de um combate em ondas (roguelike/ondas.py; ex.: o Enxame de Ratos das Galerias).

Mostra as ondas vencidas, como o grupo está (sem descanso entre as ondas) e a próxima onda. O grupo continua,
usa itens ou foge com o que já ganhou. Depois da última onda, o botão do prêmio.
"""

import pygame

from roguelike.comandos import ContinuarOndas, EncerrarOndas
from roguelike.encontros import descrever_inimigos
from roguelike.status import dados_do_status
from telas import em_grupo, fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_da_run, desenhar_heroi_pequeno
from ui import tema
from ui.componentes import TextoRevelado
from ui.desenho import texto, painel, paragrafo, barra, losango, estrelas, icone_status
from ui.widgets import Botao


class TelaEntreOndas(TelaComBotoes):
    def __init__(self, app, run):
        super().__init__(app)
        self.run = run
        self.ondas = run.ondas
        self.fundo = Fundo.da_run(run, escurecer=150)
        self.resultado = None
        self.narracao = TextoRevelado(self.ondas.texto("fim" if self.ondas.terminou() else "entre"),
                                      app.opcoes.letras_por_segundo())

    def musica(self):
        return self.run.musica()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)
        self.narracao.atualizar(dt)

    def evento(self, e):
        # enquanto o texto aparece, confirmar/clicar só mostra o resto
        if not self.narracao.completo() and (self.controles.eh(e, "confirmar") or
                                             (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)):
            self.narracao.pular()
            return
        super().evento(e)

    # ---------------- em grupo: continuar/fugir e o "seguir" são votados ----------------
    def chave(self, parte="ondas"):
        run = self.run
        vencidas = self.ondas.vencidas if self.ondas is not None else "fim"
        return f"ondas|{parte}|{run.regiao_atual}|{run.area}|{run.numero_do_combate}|{vencidas}"

    def preparar_votacoes(self):
        """(No host) 0 = continuar (ou o prêmio, depois da última onda), 1 = fugir com o que já ganhou."""
        from roguelike.comandos import ConcluirEncontro
        sessao, run = self.sessao(), self.run
        if self.resultado is not None:
            em_grupo.preparar(self, self.chave("seguir"), [0], lambda _: sessao.enviar(ConcluirEncontro()), seguir=True,
                              chave_atual=lambda: self.chave("seguir"))
        elif self.ondas.terminou():
            em_grupo.preparar(self, self.chave(), [0], lambda _: sessao.enviar(EncerrarOndas()),
                              chave_atual=lambda: self.chave() if run.ondas is self.ondas else None)
        else:
            opcoes = [0] if self.ondas.sem_fuga else [0, 1]
            em_grupo.preparar(self, self.chave(), opcoes,
                              lambda i: sessao.enviar(ContinuarOndas() if i == 0 else EncerrarOndas()),
                              chave_atual=lambda: self.chave() if run.ondas is self.ondas else None)

    def ao_aplicar(self, dados, resultado):
        """(Em grupo) o grupo fugiu ou recolheu o prêmio: o resultado aparece aqui também."""
        if dados.get("tipo") == "encerrar_ondas" and self.resultado is None and resultado.valor is not None:
            self.resultado = resultado.valor
            self.narracao = TextoRevelado(" ".join(self.resultado.textos), self.app.opcoes.letras_por_segundo())

    # ---------------- ações ----------------
    def continuar_lutando(self):
        if self.resultado is not None:
            return
        if em_grupo.partida_da(self) is not None:
            em_grupo.votar(self, self.chave(), 0)
            return
        if self.enviar(ContinuarOndas()):
            fluxo.resolver_encontro(self.app, self.run)

    def usar_itens(self):
        if self.resultado is None:
            fluxo.abrir_inventario(self.app, self.run, ao_voltar=lambda: fluxo.mostrar_entre_ondas(self.app, self.run),
                                   aba="mochila")

    def encerrar(self):
        """Fugir com o que já ganhou ou, depois da última onda, recolher o prêmio."""
        if self.resultado is not None:
            return
        if em_grupo.partida_da(self) is not None:
            em_grupo.votar(self, self.chave(), 0 if self.ondas.terminou() else 1)
            return
        self.resultado = self.enviar(EncerrarOndas()).valor
        self.narracao = TextoRevelado(" ".join(self.resultado.textos), self.app.opcoes.letras_por_segundo())

    def seguir(self):
        if self.resultado is None:
            return
        if em_grupo.partida_da(self) is not None:
            em_grupo.votar(self, self.chave("seguir"), 0)
            return
        fluxo.concluir_e_seguir(self.app, self.run)

    def tecla(self, e):
        if self.resultado is not None:
            if self.controles.eh(e, "confirmar") or self.controles.eh(e, "acelerar"):
                self.seguir()
        elif self.ondas.terminou():
            if e.unicode == "1":
                self.encerrar()
        elif e.unicode in ("1", "2") or (e.unicode == "3" and not self.ondas.sem_fuga):
            (self.continuar_lutando, self.usar_itens, self.encerrar)[int(e.unicode) - 1]()

    # ---------------- desenho ----------------
    def desenhar_trilha(self, tela, rect):
        """As ondas como losangos ligados: vencidas em ouro, a próxima acesa, as outras apagadas."""
        total, espaco, y = self.ondas.total, 90, rect.y + 34
        x0 = rect.centerx - (total - 1) * espaco // 2
        pygame.draw.line(tela, tema.FERRO_ESCURO, (x0, y), (x0 + (total - 1) * espaco, y), 3)
        for i in range(total):
            x = x0 + i * espaco
            cor = tema.OURO if i < self.ondas.vencidas else (tema.VELA if i == self.ondas.vencidas else (50, 44, 54))
            losango(tela, (x, y), 11, (8, 6, 10))
            losango(tela, (x, y), 9, cor)
            texto(tela, self.ondas.nome_da_onda(i + 1), tema.mini(),
                  tema.TEXTO_FRACO if i >= self.ondas.vencidas else tema.OURO_CLARO, (x, y + 16), "midtop")

    def desenhar_grupo(self, tela, rect):
        """Uma faixa com cada herói: sprite, nome, vida (e a Peste, que segue para a próxima onda)."""
        herois = self.run.grupo.herois
        largura = rect.width // max(1, len(herois))
        for i, heroi in enumerate(herois):
            celula = pygame.Rect(rect.x + i * largura, rect.y, largura - 8, rect.height)
            tela.set_clip(celula)
            desenhar_heroi_pequeno(tela, self.app.sprites, heroi, (celula.x + 22, celula.bottom - 10), 1)
            tela.set_clip(None)
            x = celula.x + 48
            cor = tema.TEXTO_TITULO if heroi.esta_vivo() else tema.TEXTO_APAGADO
            texto(tela, heroi.nome, tema.mini(), cor, (x, celula.y + 8))
            if heroi.esta_vivo():
                barra(tela, (x, celula.y + 32, celula.right - x - 8, 8), heroi.vida / heroi.vida_maxima, tema.VIDA_HEROI,
                      marcas=0)
                texto(tela, f"{heroi.vida}/{heroi.vida_maxima}", tema.mini(), tema.TEXTO, (x, celula.y + 46))
            else:
                texto(tela, "Caído", tema.mini(), tema.SANGUE_CLARO, (x, celula.y + 30))
            if heroi.peste > 0:
                icone = icone_status("peste")
                canto = (celula.right - icone.get_width() - 8, celula.y + 54)
                tela.blit(icone, canto)
                texto(tela, str(heroi.peste), tema.fonte(11), tema.TEXTO, (canto[0] + icone.get_width() - 2, canto[1] + 10))
                if pygame.Rect(canto, icone.get_size()).collidepoint(self.mouse):
                    self.dica = (f"Peste {heroi.peste}", dados_do_status("peste")["descricao"])

    def desenhar_proxima(self, tela, rect, y):
        proxima = self.ondas.proxima()
        if proxima is None:
            return
        texto(tela, f"{self.ondas.nome_da_onda(self.ondas.atual + 1)}:", tema.pequena(), tema.TEXTO_TITULO, (rect.x + 40, y))
        estrelas(tela, (rect.x + 148, y + 2), proxima["estrelas"])
        paragrafo(tela, descrever_inimigos(proxima["inimigos"]), tema.pequena(), tema.TEXTO_FRACO, (rect.x + 40, y + 26),
                  rect.width - 80)

    def dica_de_pular(self, tela, rect):
        texto(tela, "Enter ou clique: mostrar tudo", tema.pequena(), tema.TEXTO_APAGADO, (rect.centerx, rect.bottom - 20),
              "midbottom")
        self.terminar_desenho(tela)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        partida = em_grupo.partida_da(self)
        if partida is not None:
            self.preparar_votacoes()
        self.fundo.desenhar(tela)
        cabecalho_da_run(tela, self.run, jogador=self.meu_jogador())
        rect = painel(tela, pygame.Rect(tema.LARGURA // 2 - 380, 90, 760, 560), "osso")
        if partida is not None:                              # em grupo: quem votou e quanto falta (embaixo do painel)
            chave = self.chave("seguir") if self.resultado is not None else self.chave()
            em_grupo.faixa(tela, (rect.x, rect.bottom + 6, rect.width, 40), partida, chave)
        self.desenhar_trilha(tela, rect)
        texto(tela, self.ondas.nome, tema.grande(), tema.TEXTO_TITULO, (rect.centerx, rect.y + 76), "midtop")
        if self.resultado is not None:
            paragrafo(tela, self.narracao.visivel, tema.normal(), tema.OURO_CLARO, (rect.x + 40, rect.y + 130),
                      rect.width - 80)
            if not self.narracao.completo():
                self.dica_de_pular(tela, rect)
                return
            self.botao(Botao((rect.centerx - 120, rect.bottom - 72, 240, 52), "Continuar", self.seguir, "Enter",
                             estilo="ouro"))
            self.terminar_desenho(tela)
            return
        paragrafo(tela, self.narracao.visivel, tema.normal(), tema.TEXTO, (rect.x + 40, rect.y + 130), rect.width - 80)
        if not self.narracao.completo():
            self.dica_de_pular(tela, rect)
            return
        self.desenhar_grupo(tela, pygame.Rect(rect.x + 40, rect.y + 222, rect.width - 80, 84))
        largura = rect.width - 80
        if self.ondas.terminou():
            rotulo = self.ondas.textos.get("botao_premio", "Recolher o prêmio")
            self.botao(Botao((rect.x + 40, rect.bottom - 74, largura, 52), rotulo, self.encerrar, "1", estilo="ouro"))
        else:
            self.desenhar_proxima(tela, rect, rect.y + 322)
            seguinte = self.ondas.textos.get("botao_continuar") or \
                f"Continuar lutando (onda {self.ondas.atual + 1} de {self.ondas.total})"
            self.botao(Botao((rect.x + 40, rect.bottom - 136, largura, 52), seguinte, self.continuar_lutando, "1",
                             estilo="ouro" if self.ondas.sem_fuga else "ferro"))
            if self.ondas.sem_fuga:                         # (a luta do Rei: só se preparar e seguir)
                self.botao(Botao((rect.x + 40, rect.bottom - 74, largura, 52), "Usar itens", self.usar_itens, "2"))
            else:
                metade = (largura - 12) // 2
                self.botao(Botao((rect.x + 40, rect.bottom - 74, metade, 52), "Usar itens", self.usar_itens, "2"))
                self.botao(Botao((rect.right - 40 - metade, rect.bottom - 74, metade, 52), "Fugir com o que já ganhou",
                                 self.encerrar, "3"))
        self.terminar_desenho(tela)
