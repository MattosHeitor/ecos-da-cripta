"""Evento de escolha: um texto e 2 a 4 opções. Algumas opções levam a um combate.

Eventos com "sprite" (ex.: o Rato Branco) mostram o bicho no lugar do "?" e correndo ao pé da tela (com
"parado": true, só no lugar do "?", ex.: o Rato Mercador). Ao continuar, os passos de segredo dados no evento
vão para o progresso (valem mesmo se a run acabar mal).
"""

import pygame

from roguelike.comandos import ResolverEvento
from roguelike.eventos_run import evento as buscar_evento
from roguelike.itens import item
from telas import em_grupo, fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_da_run
from ui import tema
from ui.componentes import TextoRevelado
from ui.desenho import texto, painel, paragrafo
from ui.icones import icone_encontro
from ui.widgets import Botao


def texto_do_requisito(requisito):
    if "ouro" in requisito:
        return f"precisa de {requisito['ouro']} de ouro"
    if "item" in requisito:
        quantidade = requisito.get("quantidade", 1)
        return f"precisa de {item(requisito['item']).nome}" + (f" x{quantidade}" if quantidade > 1 else "")
    if requisito.get("consumivel"):
        return "precisa de um consumível"
    if requisito.get("vaga_no_grupo"):
        return "o grupo está cheio"
    if requisito.get("caido"):
        return "precisa de um herói caído"
    return ""


class TelaEvento(TelaComBotoes):
    def __init__(self, app, run):
        super().__init__(app)
        self.run = run
        self.evento_da_run = buscar_evento(run.encontro.evento)
        self.fundo = Fundo.da_run(run, escurecer=150)
        self.resultado = None
        self.narracao = TextoRevelado(self.evento_da_run.texto, app.opcoes.letras_por_segundo())
        self.bicho = None
        if self.evento_da_run.sprite and not self.evento_da_run.parado:    # correndo ao pé da tela, abaixo do painel
            from visual.bicho_correndo import BichoCorrendo
            self.bicho = BichoCorrendo(app.sprites, self.evento_da_run.sprite, chao_y=tema.ALTURA - 14)

    def musica(self):
        return self.run.musica()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)
        self.narracao.atualizar(dt)
        if self.bicho is not None:
            self.bicho.atualizar(dt)

    def evento(self, e):
        # enquanto o texto aparece, confirmar/clicar só mostra o resto
        if not self.narracao.completo() and (self.controles.eh(e, "confirmar") or
                                             (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)):
            self.narracao.pular()
            return
        super().evento(e)

    # ---------------- em grupo: as opções são votadas e o "Continuar" espera todos ----------------
    def chave(self, parte="opcao"):
        run = self.run
        return f"evento|{parte}|{run.regiao_atual}|{run.area}|{run.numero_do_combate}|{self.evento_da_run.chave}"

    def opcoes_validas(self):
        return [i for i, o in enumerate(self.evento_da_run.opcoes) if o.disponivel(self.run)]

    def preparar_votacoes(self):
        """(No host) a opção vencedora vira o ResolverEvento de todos; o "seguir", a luta ou o fim do encontro."""
        from roguelike.comandos import ComecarCombate, ConcluirEncontro
        sessao = self.sessao()
        if self.resultado is None:
            em_grupo.preparar(self, self.chave(), self.opcoes_validas(),
                              lambda i: sessao.enviar(ResolverEvento(indice=i)), chave_atual=self.chave)
        else:
            em_grupo.preparar(self, self.chave("seguir"), [0], lambda _: sessao.enviar(
                ComecarCombate() if self.run.encontro is not None and self.run.encontro.eh_combate()
                else ConcluirEncontro()), seguir=True, chave_atual=lambda: self.chave("seguir"))

    def ao_aplicar(self, dados, resultado):
        """(Em grupo) o evento foi resolvido pela opção do grupo: o resultado aparece aqui também."""
        if dados.get("tipo") == "resolver_evento" and self.resultado is None and resultado.valor is not None:
            self.resultado = resultado.valor
            self.narracao = TextoRevelado(" ".join(self.resultado.textos), self.app.opcoes.letras_por_segundo())

    # ---------------- ações ----------------
    def escolher(self, indice):
        if self.resultado is not None:
            return
        if em_grupo.partida_da(self) is not None:
            em_grupo.votar(self, self.chave(), indice)
            return
        self.resultado = self.enviar(ResolverEvento(indice=indice)).valor
        if self.resultado is not None:
            self.narracao = TextoRevelado(" ".join(self.resultado.textos), self.app.opcoes.letras_por_segundo())

    def continuar(self):
        if self.resultado is None:
            return
        if em_grupo.partida_da(self) is not None:
            em_grupo.votar(self, self.chave("seguir"), 0)
            return
        fluxo.guardar_segredos(self.app, self.run)
        if self.resultado.combate is not None:
            fluxo.resolver_encontro(self.app, self.run)       # o encontro virou um combate
        else:
            fluxo.concluir_e_seguir(self.app, self.run)

    def tecla(self, e):
        if self.resultado is None and e.unicode in ("1", "2", "3", "4"):
            indice = int(e.unicode) - 1
            if indice < len(self.evento_da_run.opcoes) and self.evento_da_run.opcoes[indice].disponivel(self.run):
                self.escolher(indice)
        elif self.resultado is not None and (self.controles.eh(e, "confirmar") or self.controles.eh(e, "acelerar")):
            self.continuar()

    ALTURA_DO_BICHO = 110                       # o sprite do evento cabe nesta altura (pés em cima do título)

    def desenhar_bicho(self, tela, pe):
        """O sprite do evento respirando, com os pés em 'pe' (3x os pequenos, menos os maiores)."""
        sprites, nome = self.app.sprites, self.evento_da_run.sprite
        escala = 3
        while escala > 1 and sprites.caixa(nome, escala).height > self.ALTURA_DO_BICHO:
            escala -= 1
        quadro = int(self.tempo * 5) % sprites.quadros_de(nome, "parado")
        imagem = sprites.quadro(nome, "parado", quadro, escala)
        ax, ay = sprites.ancora(nome, escala)
        tela.blit(imagem, (round(pe[0] - ax), round(pe[1] - ay)))

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
        if self.bicho is not None:
            self.bicho.desenhar(tela)
        cabecalho_da_run(tela, self.run, jogador=self.meu_jogador())
        rect = painel(tela, pygame.Rect(tema.LARGURA // 2 - 380, 90, 760, 560), "osso")
        if self.evento_da_run.sprite:              # o bicho do evento no lugar do "?"
            self.desenhar_bicho(tela, (rect.centerx, rect.y + 84))
        else:
            icone = icone_encontro("interrogacao", 5)
            tela.blit(icone, icone.get_rect(midtop=(rect.centerx, rect.y + 16)))
        texto(tela, self.evento_da_run.nome, tema.grande(), tema.TEXTO_TITULO, (rect.centerx, rect.y + 90), "midtop")
        if self.resultado is None:
            y = paragrafo(tela, self.narracao.visivel, tema.normal(), tema.TEXTO, (rect.x + 40, rect.y + 144),
                          rect.width - 80)
            if not self.narracao.completo():
                self.dica_de_pular(tela, rect)
                return
            y += 20
            for i, opcao in enumerate(self.evento_da_run.opcoes):
                disponivel = opcao.disponivel(self.run)
                rotulo = opcao.texto if disponivel else f"{opcao.texto}  ({texto_do_requisito(opcao.requisito)})"
                botao = self.botao(Botao((rect.x + 40, y + i * 62, rect.width - 80, 52), rotulo,
                                         (lambda i=i: self.escolher(i)), str(i + 1), ativo=disponivel,
                                         selecionado=partida is not None and em_grupo.meu_voto(self, self.chave()) == i))
                if partida is not None:                  # quem votou nesta opção
                    em_grupo.desenhar_votos(tela, partida, self.chave(), i, (botao.rect.right - 4, botao.rect.bottom + 4),
                                            "bottomright")
            if partida is not None:
                em_grupo.faixa(tela, (rect.x + 40, rect.bottom - 54, rect.width - 80, 40), partida, self.chave())
        else:
            y = paragrafo(tela, self.evento_da_run.texto, tema.normal(), tema.TEXTO_FRACO, (rect.x + 40, rect.y + 144),
                          rect.width - 80) + 16
            paragrafo(tela, self.narracao.visivel, tema.normal(), tema.OURO_CLARO, (rect.x + 40, y), rect.width - 80)
            if not self.narracao.completo():
                self.dica_de_pular(tela, rect)
                return
            nome = "Lutar!" if self.resultado.combate is not None else "Continuar"
            if partida is not None:                      # em grupo: segue quando todos confirmarem
                pronto = em_grupo.meu_voto(self, self.chave("seguir")) is not None
                self.botao(Botao((rect.x + 40, rect.bottom - 72, 220, 52), nome, self.continuar, "Enter",
                                 estilo="pedra" if pronto else "ouro", selecionado=pronto))
                em_grupo.faixa(tela, (rect.x + 272, rect.bottom - 66, rect.width - 312, 40), partida,
                               self.chave("seguir"), "Seguir")
            else:
                self.botao(Botao((rect.centerx - 120, rect.bottom - 72, 240, 52), nome, self.continuar, "Enter",
                                 estilo="ouro"))
        self.terminar_desenho(tela)
