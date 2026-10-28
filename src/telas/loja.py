"""Loja (mercador ou alquimista): comprar e vender. Dá para abrir o Grupo para fabricar e vender."""

import pygame

from roguelike.comandos import Comprar, ConcluirEncontro
from roguelike.fabricacao import todas_as_receitas
from roguelike.itens import item
from telas import em_grupo, fluxo
from telas.comum import (TelaComBotoes, Fundo, cabecalho_da_run, texto_do_item, npc_do_encontro, desenhar_npc,
                         confirmar_venda)
from ui import tema
from ui.desenho import texto, painel, paragrafo, moldura, titulo_de_painel
from ui.icones import icone_item, icone_encontro
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao


class TelaLoja(TelaComBotoes):
    def __init__(self, app, run):
        super().__init__(app)
        self.run = run
        self.loja = run.loja_atual
        self.fundo = Fundo.da_run(run, escurecer=130)
        self.mensagem = "Clique numa oferta para comprar (com o seu ouro). O que comprar vai para a sua mochila."
        self.npc = npc_do_encontro(run)
        self.lista_ofertas = PainelRolavel(passo=62)
        self.lista_venda = PainelRolavel(passo=40)
        self.vender_do_bau = False          # o painel de venda mostra a sua mochila (ou o baú da equipe)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def musica(self):
        return self.run.musica()

    def voltar(self):
        self.sair()

    def chave_de_seguir(self):
        run = self.run
        return f"seguir|loja|{run.regiao_atual}|{run.area}|{run.numero_do_combate}"

    def sair(self):
        """Sai da loja (em grupo: um voto; o grupo segue quando todos tiverem terminado as compras)."""
        if em_grupo.partida_da(self) is not None:
            em_grupo.votar(self, self.chave_de_seguir(), 0)
            return
        fluxo.concluir_e_seguir(self.app, self.run)

    def comprar(self, indice):
        resultado = self.enviar(Comprar(indice=indice))
        self.mensagem = resultado.mensagem
        if resultado:
            self.app.audio.tocar("moeda")

    def de_onde_vende(self):
        return self.run.grupo.bau if self.vender_do_bau else self.meu_jogador().mochila

    def trocar_venda(self):
        self.vender_do_bau = not self.vender_do_bau
        self.lista_venda.ir_para(0, imediato=True)

    def vender(self, chave):
        def vendido(ganho):
            if ganho:
                self.mensagem = f"Vendeu {item(chave).nome} por {ganho} de ouro."
                self.app.audio.tocar("moeda")
        confirmar_venda(self, self.de_onde_vende(), chave, vendido)

    def abrir_grupo(self, aba):
        """Inventário (dá para vender das mochilas pelo menu de ações), fabricação ou os heróis; voltam à loja."""
        voltar = lambda: self.app.trocar(self)
        if aba in ("bau", "inventario"):
            fluxo.abrir_inventario(self.app, self.run, voltar, "mochila", self.loja)
        elif aba == "fabricacao":
            fluxo.abrir_fabricacao(self.app, self.run, voltar)
        else:
            from telas.grupo import TelaGrupo
            self.app.trocar(TelaGrupo(self.app, self.run, aba, voltar, loja=self.loja))

    def desenhar_oferta(self, tela, rect, i, oferta):
        """Uma oferta: ícone, nome (cor da raridade), estoque e preço."""
        pode = not oferta.esgotada() and self.meu_jogador().ouro >= oferta.preco
        if oferta.tipo == "receita":
            receita = todas_as_receitas()[oferta.chave]
            objeto = receita.item_resultado()
            dica = (oferta.nome(), "Revela a receita para fabricar:\n" + texto_do_item(objeto))
        else:
            objeto = item(oferta.chave)
            dica = (objeto.nome, texto_do_item(objeto))
        botao = Botao(rect, "", (lambda i=i: self.comprar(i)), ativo=pode, dica=dica,
                      estilo="osso" if oferta.tipo == "receita" else "ferro")
        self.botao(botao)
        tela.blit(icone_item(objeto, 3), (rect.x + 10, rect.y + 10))
        cor = tema.COR_RARIDADE[objeto.raridade] if not oferta.esgotada() else tema.TEXTO_APAGADO
        linha(tela, oferta.nome(), tema.pequena(), cor, (rect.x + 54, rect.y + 6), rect.width - 54 - 110)
        estoque = "esgotado" if oferta.esgotada() else f"estoque {oferta.estoque}"
        texto(tela, estoque, tema.mini(), tema.TEXTO_FRACO, (rect.x + 54, rect.y + 29))
        linha(tela, f"{oferta.preco} ouro", tema.normal(), tema.OURO_MOEDA if pode else tema.TEXTO_APAGADO,
              (rect.right - 12, rect.centery), 100, "midright")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela, frente=False)
        cabecalho_da_run(tela, self.run, self.loja.nome, jogador=self.meu_jogador())

        # ofertas
        esquerda = painel(tela, (8, 68, 620, 576), "ferro")
        topo = titulo_de_painel(tela, esquerda, "À venda")
        icone = icone_encontro("moeda" if self.run.encontro.tipo == "loja" else "frasco", 2)
        tela.blit(icone, (esquerda.x + 16, esquerda.y + 12))
        janela = pygame.Rect(esquerda.x + 14, topo, esquerda.width - 28, esquerda.bottom - topo - 14)
        total = len(self.loja.ofertas) * 62 - 6
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista_ofertas, janela, total) as y0:
            for i, oferta in enumerate(self.loja.ofertas):
                self.desenhar_oferta(tela, pygame.Rect(janela.x, y0 + i * 62, largura, 56), i, oferta)

        # o vendedor atrás do balcão, com uma fala
        if self.npc:
            balcao = painel(tela, (636, 68, tema.LARGURA - 644, 200), "pedra")
            desenhar_npc(tela, self.app.sprites, self.npc["sprite"], (balcao.x + 110, balcao.bottom - 14), 2, self.tempo)
            texto(tela, self.npc["nome"], tema.normal(), tema.TEXTO_TITULO, (balcao.x + 230, balcao.y + 22))
            fala = pygame.Rect(balcao.x + 220, balcao.y + 56, balcao.right - balcao.x - 236, 120)
            tela.blit(moldura(fala.width, fala.height, "osso"), fala.topleft)
            paragrafo(tela, f'"{self.npc["fala"]}"', tema.pequena(), tema.TEXTO, (fala.x + 16, fala.y + 16),
                      fala.width - 32, maximo_linhas=4, encolher=True)
            direita = painel(tela, (636, 276, tema.LARGURA - 644, 368), "ferro")
        else:
            direita = painel(tela, (636, 68, tema.LARGURA - 644, 576), "ferro")
        # vender (da sua mochila ou do baú da equipe)
        topo = titulo_de_painel(tela, direita, "Vender (do baú)" if self.vender_do_bau else "Vender (da mochila)")
        self.botao(Botao((direita.right - 128, direita.y + 10, 114, 30), "Mochila" if self.vender_do_bau else "Baú",
                         self.trocar_venda, dica=("Trocar", "Vender da sua mochila ou do baú da equipe.")))
        pilhas = self.de_onde_vende().pilhas()
        janela = pygame.Rect(direita.x + 14, topo, direita.width - 28, direita.bottom - topo - 14)
        total = len(pilhas) * 40 - 4
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista_venda, janela, total) as y0:
            for i, (objeto, quantidade) in enumerate(pilhas):
                rect = pygame.Rect(janela.x, y0 + i * 40, largura, 36)
                botao = Botao(rect, "", (lambda c=objeto.chave: self.vender(c)), dica=(objeto.nome, texto_do_item(objeto)))
                self.botao(botao)
                tela.blit(icone_item(objeto, 2), (rect.x + 8, rect.y + 6))
                linha(tela, f"{objeto.nome}  x{quantidade}", tema.pequena(), tema.COR_RARIDADE[objeto.raridade],
                      (rect.x + 42, rect.centery), rect.width - 42 - 60, "midleft")
                texto(tela, f"+{objeto.preco_de_venda()}", tema.pequena(), tema.OURO_MOEDA, (rect.right - 12, rect.centery),
                      "midright")
        if not pilhas:
            vazio = "O baú está vazio." if self.vender_do_bau else "A sua mochila está vazia."
            paragrafo(tela, vazio + " Também dá para vender pelo Inventário (botão direito num item > Vender).",
                      tema.pequena(), tema.TEXTO_FRACO, (direita.x + 14, direita.y + 56), direita.width - 28)

        partida = em_grupo.partida_da(self)
        largura_da_mensagem = tema.LARGURA - 596 - 32 - (176 if partida is not None else 0)
        if partida is not None and em_grupo.meu_voto(self, self.chave_de_seguir()) is not None:
            em_grupo.faixa(tela, (16, tema.ALTURA - 62, largura_da_mensagem, 48), partida, self.chave_de_seguir(),
                           "Saindo")                       # (já votou: quem falta terminar as compras)
        else:
            CaixaTexto((16, tema.ALTURA - 62, largura_da_mensagem, 48), tema.normal(), tema.OURO_CLARO,
                       vertical="meio").desenhar(tela, self.mensagem)
        if partida is not None:
            em_grupo.preparar(self, self.chave_de_seguir(), [0], lambda _: self.sessao().enviar(ConcluirEncontro()),
                              seguir=True, chave_atual=self.chave_de_seguir)
            self.botao(Botao((tema.LARGURA - 596 - 176, tema.ALTURA - 62, 166, 48), "Enviar ouro",
                             lambda: em_grupo.abrir_envio_de_ouro(self),
                             dica=("Enviar ouro", "Passa parte do seu ouro para outro jogador.")))
        self.botao(Botao((tema.LARGURA - 596, tema.ALTURA - 62, 180, 48), "Inventário",
                         (lambda: self.abrir_grupo("inventario")), "I",
                         dica=("Inventário", "Mochila e baú; dá para vender pelo botão direito num item.")))
        self.botao(Botao((tema.LARGURA - 404, tema.ALTURA - 62, 180, 48), "Fabricar", (lambda: self.abrir_grupo("fabricacao")), "F"))
        self.botao(Botao((tema.LARGURA - 212, tema.ALTURA - 62, 196, 48), "Sair da loja", self.sair, "ESC", estilo="ouro"))
        self.terminar_desenho(tela)

    def tecla(self, e):
        if self.controles.eh(e, "grupo"):
            self.abrir_grupo("herois")
        elif self.controles.eh(e, "inventario") or self.controles.eh(e, "bau"):
            self.abrir_grupo("inventario")
        elif self.controles.eh(e, "fabricar"):
            self.abrir_grupo("fabricacao")
