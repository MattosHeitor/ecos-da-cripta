"""Encontros de serviço: treinador de subclasse, altar, necromante, descanso maior e passagem."""

import pygame

from roguelike.comandos import ConcluirEncontro, DescansoMaior, Treinar, Reviver
from telas import em_grupo, fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_da_run, desenhar_heroi_pequeno, npc_do_encontro, desenhar_npc
from ui import tema
from ui.desenho import texto, painel, paragrafo, moldura, quebrar
from ui.icones import icone_encontro
from ui.texto import linha
from ui.widgets import Botao


class TelaServico(TelaComBotoes):
    def __init__(self, app, run):
        super().__init__(app)
        self.run = run
        self.encontro = run.encontro
        self.fundo = Fundo.da_run(run, escurecer=140)
        self.mensagens = []
        self.npc = npc_do_encontro(run)
        self.partida = em_grupo.partida_da(self)
        if self.encontro.tipo == "descanso":
            if self.partida is None or self.partida.eh_host:       # (em grupo, o host descansa por todos)
                self.mostrar_descanso(self.enviar(DescansoMaior()).valor)
            else:
                self.mensagens = ["O grupo se acomoda junto à fogueira..."]

    def mostrar_descanso(self, curados):
        self.mensagens = [f"{h.nome} recuperou {v} de vida." for h, v in (curados or {}).items() if v > 0] or \
                         ["Todos já estavam com a vida cheia."]

    def ao_aplicar(self, dados, resultado):
        """(Em grupo) o descanso do host chegou: as curas aparecem aqui também."""
        if dados.get("tipo") == "descanso_maior":
            self.mostrar_descanso(resultado.valor)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def musica(self):
        return self.run.musica()

    def voltar(self):
        self.seguir()

    # ---------------- seguir (em grupo: por votação) ----------------
    def chave(self):
        run = self.run
        return f"servico|{self.encontro.tipo}|{run.regiao_atual}|{run.area}|{run.numero_do_combate}"

    def preparar_votacao(self):
        """(No host) a passagem é votada (entrar ou seguir em frente); os outros serviços, o "seguir" de todos."""
        sessao = self.sessao()
        if self.encontro.tipo == "entrada":
            em_grupo.preparar(self, self.chave(), [0, 1],
                              lambda i: sessao.enviar(ConcluirEncontro(pular_passagem=i == 1)), chave_atual=self.chave)
        else:
            em_grupo.preparar(self, self.chave(), [0], lambda _: sessao.enviar(ConcluirEncontro()), seguir=True,
                              chave_atual=self.chave)

    def seguir(self):
        if self.partida is not None:
            em_grupo.votar(self, self.chave(), 0)
            return
        fluxo.concluir_e_seguir(self.app, self.run)

    def ignorar_passagem(self):
        if self.partida is not None:
            em_grupo.votar(self, self.chave(), 1)
            return
        fluxo.concluir_e_seguir(self.app, self.run, pular_passagem=True)     # sem passagem: só avança a área

    # ---------------- ações ----------------
    def treinar(self, heroi):
        resultado = self.enviar(Treinar(heroi=self.indice_do(heroi)))
        if resultado:
            self.mensagens.append(resultado.mensagem)
            fluxo.mostrar_avisos(self.app, self.run)

    def reviver(self, heroi):
        self.mensagens.append(self.enviar(Reviver(caido=self.indice_do(heroi))).mensagem)     # (paga com o seu ouro)

    # ---------------- desenho ----------------
    def desenhar_herois(self, tela, rect, filtro, rotulo, acao):
        """Mostra os heróis que podem receber o serviço, cada um com um botão."""
        herois = [h for h in self.run.grupo.herois if filtro(h)]
        if not herois:
            return False
        largura = min(200, (rect.width - 40) // len(herois) - 10)
        for i, heroi in enumerate(herois):
            x = rect.x + 20 + i * (largura + 10)
            desenhar_heroi_pequeno(tela, self.app.sprites, heroi, (x + largura // 2, rect.y + 150), 1)
            linha(tela, heroi.nome, tema.pequena(), tema.TEXTO, (x + largura // 2, rect.y + 160), largura, "midtop")
            self.botao(Botao((x, rect.y + 188, largura, 44), rotulo, (lambda h=heroi: acao(h))))
        return True

    def desenhar_npc_ao_lado(self, tela):
        """Quem oferece o serviço fica à esquerda do painel, com uma fala acima."""
        largura = tema.LARGURA // 2 - 420 - 24
        fala = f'"{self.npc["fala"]}"'
        linhas = min(6, len(quebrar(fala, tema.pequena(), largura - 28)))
        caixa = pygame.Rect(12, 96, largura, 30 + linhas * (tema.pequena().get_linesize() + 2))
        tela.blit(moldura(caixa.width, caixa.height, "osso"), caixa.topleft)
        paragrafo(tela, fala, tema.pequena(), tema.TEXTO, (caixa.x + 14, caixa.y + 14), caixa.width - 28, maximo_linhas=6, encolher=True)
        pe = (caixa.centerx, tema.ALTURA - 110)
        desenhar_npc(tela, self.app.sprites, self.npc["sprite"], pe, 2, self.tempo)
        linha(tela, self.npc["nome"], tema.normal(), tema.TEXTO_TITULO, (pe[0], pe[1] + 14), largura, "midtop")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_da_run(tela, self.run, jogador=self.meu_jogador())
        if self.npc:
            self.desenhar_npc_ao_lado(tela)
        encontro = self.encontro
        rect = painel(tela, pygame.Rect(tema.LARGURA // 2 - 420, 90, 840, 560), "osso")
        icone = icone_encontro(encontro.icone(), 6)
        tela.blit(icone, icone.get_rect(midtop=(rect.centerx, rect.y + 16)))
        linha(tela, encontro.nome, tema.grande(), tema.TEXTO_TITULO, (rect.centerx, rect.y + 100), rect.width - 40, "midtop")
        y = paragrafo(tela, encontro.descricao, tema.normal(), tema.TEXTO, (rect.x + 40, rect.y + 150), rect.width - 80)
        area = pygame.Rect(rect.x + 20, y + 10, rect.width - 40, 250)

        tipo = encontro.tipo
        if tipo == "treinador":
            if not self.desenhar_herois(tela, area, lambda h: h in encontro.herois_que_podem(self.run.grupo),
                                        "Treinar", self.treinar):
                texto(tela, "Ninguém pode aprender agora.", tema.normal(), tema.TEXTO_FRACO, area.center, "center")
        elif tipo in ("altar", "necromante"):
            texto(tela, f"Seu ouro: {self.meu_jogador().ouro}   ·   Preço: {encontro.preco()}", tema.normal(), tema.OURO_MOEDA,
                  (rect.centerx, y + 4), "midtop")
            if not self.desenhar_herois(tela, area.move(0, 20), lambda h: not h.esta_vivo(), "Reviver", self.reviver):
                texto(tela, "Ninguém precisa ser revivido.", tema.normal(), tema.TEXTO_FRACO, area.center, "center")
        elif tipo == "entrada":
            entrar = self.botao(Botao((rect.centerx - 250, rect.bottom - 80, 240, 52), "Entrar", self.seguir, "Enter",
                                      estilo="ouro"))
            pular = self.botao(Botao((rect.centerx + 10, rect.bottom - 80, 240, 52), "Seguir em frente", self.ignorar_passagem))
            if self.partida is not None:                     # quem votou em cada um
                for indice, botao in ((0, entrar), (1, pular)):
                    em_grupo.desenhar_votos(tela, self.partida, self.chave(), indice, (botao.rect.centerx, botao.rect.y - 4))

        yy = area.bottom + 10
        cabem = max(0, (rect.bottom - 72 - 8 - yy - (48 if self.partida is not None else 0)) // 26)
        for mensagem in (self.mensagens[-cabem:] if cabem else []):
            linha(tela, mensagem, tema.normal(), tema.OURO_CLARO, (rect.centerx, yy), rect.width - 40, "midtop")
            yy += 26
        if self.partida is not None:
            self.preparar_votacao()
            em_grupo.faixa(tela, (rect.x + 40, rect.bottom - 128 if tipo == "entrada" else rect.bottom - 120,
                                  rect.width - 80, 40), self.partida, self.chave(),
                           "Passagem" if tipo == "entrada" else "Seguir")
        if tipo != "entrada":
            self.botao(Botao((rect.centerx - 120, rect.bottom - 72, 240, 52), "Continuar", self.seguir, "Enter", estilo="ouro"))
        self.terminar_desenho(tela)

    def tecla(self, e):
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.seguir()
