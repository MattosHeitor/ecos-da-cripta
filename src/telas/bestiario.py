"""Estudioso do bestiário: as páginas dos inimigos, por região.

Inimigo nunca derrotado aparece só como silhueta "???". Com abates, a página revela o nome, os
golpes, as fraquezas a elementos e, por fim, o loot conhecido (roguelike/bestiario.py).
"""

import pygame

from roguelike import elementos
from roguelike.bestiario import secoes, Pagina, total_conhecido
from roguelike.itens import item
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, cabecalho_do_acampamento, desenhar_abas, desenhar_previa
from ui import tema
from ui.desenho import texto, painel
from ui.layout import grade, altura_da_grade
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao

COLUNAS, ALTURA = 5, 100
ABAS_POR_LINHA = 7                           # 2 fileiras = 14 abas (o Reino dos Ratos é a 13ª)
TOPO = 164                                   # abaixo das duas fileiras de abas


class TelaBestiario(TelaComBotoes):
    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=160)
        self.secoes = secoes()
        self.secao = self.secoes[0][0]
        self.vista = None
        self.grade = PainelRolavel(passo=ALTURA + 6)          # os cartões dos inimigos (rola por fileira)
        self.lendo = False                           # mostrando a história do chefe em vez da ficha

    def musica(self):
        return "acampamento"

    def voltar(self):
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def trocar_secao(self, chave):
        self.secao = chave
        self.vista = None
        self.grade.ir_para(0, imediato=True)

    def inimigos(self):
        return next(lista for chave, _, lista in self.secoes if chave == self.secao)

    def ver(self, chave):
        if chave != self.vista:
            self.app.audio.tocar("pagina")
            self.lendo = False
        self.vista = chave

    def alternar_lore(self):
        self.lendo = not self.lendo
        self.app.audio.tocar("pagina")

    # ---------------- desenho ----------------
    def miniatura(self, nome, caixa, efeito):
        """O primeiro quadro do sprite, reduzido para caber no cartão (pixels nítidos)."""
        sprites = self.app.sprites
        chave = ("miniatura", nome, caixa.size, efeito)
        if chave not in sprites._cache:
            imagem = sprites.quadro(nome, "parado", 0, 1, False, efeito)
            corpo = imagem.get_bounding_rect()
            pedaco = imagem.subsurface(corpo) if corpo.width and corpo.height else imagem
            fator = min(caixa.width / max(1, pedaco.get_width()), caixa.height / max(1, pedaco.get_height()))
            fator = 2 if fator >= 2 else (1 if fator >= 1 else fator)
            tamanho = (max(1, int(pedaco.get_width() * fator)), max(1, int(pedaco.get_height() * fator)))
            sprites._cache[chave] = pygame.transform.scale(pedaco, tamanho)
        return sprites._cache[chave]

    def desenhar_cartao(self, tela, rect, pagina):
        self.botao(Botao(rect, "", (lambda c=pagina.chave: self.ver(c)), estilo="osso" if pagina.conhecido else "pedra",
                         selecionado=pagina.chave == self.vista))
        cabe = tema.mini().size(pagina.nome)[0] <= rect.width - 12
        area = pygame.Rect(rect.x + 8, rect.y + 6, rect.width - 16, rect.height - (30 if cabe else 44))
        imagem = self.miniatura(pagina.sprite, area, None if pagina.conhecido else "silhueta")
        tela.blit(imagem, imagem.get_rect(midbottom=area.midbottom))
        cor = tema.TEXTO if pagina.conhecido else tema.TEXTO_APAGADO
        if cabe:
            linha(tela, pagina.nome, tema.mini(), cor, (rect.centerx, rect.bottom - 8), rect.width - 12, "midbottom")
        else:                                       # nome comprido (Médico da Peste Corrompido): duas linhas menores
            CaixaTexto(pygame.Rect(rect.x + 6, rect.bottom - 44, rect.width - 12, 36), tema.fonte(12), cor,
                       alinhamento="centro", maximo_linhas=2).desenhar(tela, pagina.nome)
        if pagina.conhecido:
            texto(tela, str(pagina.abates), tema.mini(), tema.OURO, (rect.right - 8, rect.y + 6), "topright")

    def desenhar_detalhe(self, tela, rect, pagina):
        painel(tela, rect, "ferro")
        area = rect.inflate(-28, -28)
        if self.lendo and pagina.conhecido and pagina.lore():
            self.desenhar_historia(tela, area, pagina)
            return
        sprites = self.app.sprites
        escala = 2 if sprites.caixa(pagina.sprite, 2).width < area.width - 30 and sprites.caixa(pagina.sprite, 2).height < 190 else 1
        desenhar_previa(tela, sprites, pagina.sprite, (area.x, area.y, area.width, 220), self.tempo, escala, "pedra",
                        None if pagina.conhecido else "silhueta")
        y = area.y + 232
        linha(tela, pagina.nome, tema.media(), tema.TEXTO_TITULO, (area.x, y), area.width)
        if not pagina.conhecido:
            CaixaTexto(pygame.Rect(area.x, y + 40, area.width, 120), tema.pequena(), padding=0).desenhar(
                tela, "Ninguém voltou para contar como é. Derrote um para o Estudioso registrar a página.",
                tema.TEXTO_FRACO)
            return
        if pagina.lore():
            self.botao(Botao((area.right - 150, area.y + 6, 150, 34), "Ler a história", self.alternar_lore, estilo="osso"))
        trechos =[(f"{pagina.familia()} · {pagina.categoria()} · derrotados: {pagina.abates}", tema.OURO_CLARO),
                   ("Golpes: " + ", ".join(pagina.golpes()), tema.TEXTO)]
        if pagina.fraquezas_reveladas:
            fracos, resiste = pagina.afinidades()
            trechos.append((elementos.texto_de_afinidades(fracos, resiste) or "Sem fraquezas nem resistências.", tema.VELA))
        else:
            trechos.append((f"Fraquezas: ??? (mais {pagina.falta_para('fraquezas')} abate(s))", tema.TEXTO_APAGADO))
        if pagina.loot_revelado:
            itens = [f"{item(c).nome} ({int(chance * 100)}%)" for c, chance in pagina.loot()]
            trechos.append(("Loot: " + (", ".join(itens) or "nada de especial"), (220, 200, 150)))
        else:
            trechos.append((f"Loot: ??? (mais {pagina.falta_para('loot')} abate(s))", tema.TEXTO_APAGADO))
        CaixaTexto(pygame.Rect(area.x, y + 38, area.width, area.bottom - y - 38), tema.pequena(), padding=0,
                   maximo_linhas=14).desenhar(tela, trechos)

    def desenhar_historia(self, tela, area, pagina):
        """A história do chefe ocupa o painel: retrato pequeno ao lado do nome e o texto embaixo (o Rei e a Rainha dos
        Ratos têm duas partes: a segunda chega com mais vitórias)."""
        retrato = pygame.Rect(area.x, area.y, 84, 84)
        painel(tela, retrato, "pedra")
        imagem = self.miniatura(pagina.sprite, retrato.inflate(-10, -10), None)
        tela.blit(imagem, imagem.get_rect(midbottom=(retrato.centerx, retrato.bottom - 5)))
        self.botao(Botao((area.right - 150, area.y + 6, 150, 34), "Ficha", self.alternar_lore, estilo="osso"))
        linha(tela, pagina.nome, tema.media(), tema.TEXTO_TITULO, (retrato.right + 12, retrato.bottom - 34),
              area.right - retrato.right - 12)
        trechos = [(pagina.lore(), (220, 200, 160))]
        falta = pagina.falta_para_a_lore()
        if falta:
            trechos.append((f"O Estudioso ainda não sabe o resto: vença mais {falta} vez(es).", tema.TEXTO_APAGADO))
        topo = retrato.bottom + 14
        CaixaTexto(pygame.Rect(area.x, topo, area.width, area.bottom - topo), tema.pequena(), padding=0,
                   maximo_linhas=16).desenhar(tela, trechos)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        conhecidos, total = total_conhecido(self.app.progresso)
        cabecalho_do_acampamento(tela, "Estudioso do Bestiário", self.app.progresso, f"Páginas: {conhecidos}/{total}")
        desenhar_abas(self, (16, 66), [(c, n) for c, n, _ in self.secoes], self.secao, self.trocar_secao,
                      largura=(tema.LARGURA - 32 - (ABAS_POR_LINHA - 1) * 10) // ABAS_POR_LINHA, altura=36,
                      por_linha=ABAS_POR_LINHA)
        inimigos = self.inimigos()
        if self.vista not in inimigos:
            self.vista = inimigos[0] if inimigos else None
        janela = pygame.Rect(16, TOPO, 760, 644 - TOPO)
        total = altura_da_grade(len(inimigos), COLUNAS, ALTURA, 6)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.grade, janela, total) as y0:
            for chave, rect in zip(inimigos, grade((janela.x, y0, largura, total), len(inimigos), COLUNAS, ALTURA, 6)):
                self.desenhar_cartao(tela, rect, Pagina(chave, self.app.progresso))
        if self.vista is not None:
            self.desenhar_detalhe(tela, pygame.Rect(790, TOPO, tema.LARGURA - 806, 644 - TOPO), Pagina(self.vista, self.app.progresso))
        self.botao(Botao((tema.LARGURA - 176, tema.ALTURA - 60, 160, 44), "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
