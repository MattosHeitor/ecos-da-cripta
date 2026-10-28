"""Taverna: o Taverneiro tem quatro coisas para oferecer.

- Bênçãos: modificadores de run (5 espaços), comprados com Brasas;
- Provisões: consumíveis comprados com Brasas que vão para a sua mochila no começo da próxima run;
- Boatos: dicas sobre fraquezas e segredos (mudam a cada run);
- Raridades: skins raras à venda (a vitrine muda depois de cada run);
- Mascarado: a loja do Mercador Mascarado (só depois de vencê-lo; vira provisão da próxima run).
"""

import pygame

from roguelike.dados import regras
from roguelike.itens import item
from roguelike.progresso import bencaos, descrever_conquista, dados_da_taverna
from roguelike.skins import skin, nome_do_sprite
from telas import fluxo
from telas.comum import (TelaComBotoes, Fundo, cabecalho_do_acampamento, desenhar_abas, desenhar_previa, desenhar_npc,
                         desenhar_retrato)
from ui import tema
from ui.desenho import texto, painel, losango
from ui.icones import icone_item
from ui.layout import grade, altura_da_grade
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, escrever, linha
from ui.widgets import Botao

ABAS = (("bencaos", "Bênçãos"), ("provisoes", "Provisões"), ("boatos", "Boatos"), ("raridades", "Raridades"),
        ("mascarado", "Mascarado"))
NOMES_DAS_CAMADAS = {"roupa": "Roupa", "chapeu": "Chapéu", "arma": "Arma"}


class TelaTaverna(TelaComBotoes):
    def __init__(self, app, aba="bencaos"):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=150)
        self.aba = aba
        self.mensagem = ""
        self.aviso = ""
        self.lista = PainelRolavel()

    def musica(self):
        return "acampamento"

    @property
    def progresso(self):
        return self.app.progresso

    def voltar(self):
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def trocar_aba(self, aba):
        self.aba = aba
        self.mensagem = ""
        self.lista.ir_para(0, imediato=True)

    # ============================================================
    # BÊNÇÃOS
    # ============================================================
    def clicar_bencao(self, chave):
        """Comprar (pergunta antes: gastar Brasas não tem volta), equipar ou tirar."""
        dados = bencaos()[chave]
        if chave not in self.progresso.bencaos_compradas and self.progresso.brasas >= dados["preco"]:
            self.confirmar("Comprar bênção", f"Comprar {dados['nome']} por {dados['preco']} Brasas? Não dá para desfazer.",
                           lambda: self.usar_bencao(chave), "Comprar")
            return
        self.usar_bencao(chave)

    def usar_bencao(self, chave):
        progresso = self.progresso
        dados = bencaos()[chave]
        if chave not in progresso.bencaos_compradas:
            if progresso.comprar_bencao(chave):
                self.mensagem = f"{dados['nome']} comprada!"
                progresso.equipar_bencao(chave)
            else:
                self.mensagem = "Brasas insuficientes."
        elif chave in progresso.bencaos_equipadas:
            progresso.desequipar_bencao(chave)
            self.mensagem = f"{dados['nome']} guardada."
        elif progresso.equipar_bencao(chave):
            self.mensagem = f"{dados['nome']} equipada."
        else:
            self.mensagem = "Não cabe: libere espaços tirando outra bênção."
        progresso.salvar()

    def desenhar_espacos(self, tela, rect):
        progresso = self.progresso
        total = regras()["progresso"]["espacos_de_bencao"]
        largura = (rect.width - 32 - (total - 1) * 8) // total
        x = rect.x + 16
        espaco = 0
        for chave in progresso.bencaos_equipadas:
            dados = bencaos()[chave]
            ocupa = dados["espacos"]
            area = pygame.Rect(x + espaco * (largura + 8), rect.y + 36, largura * ocupa + 8 * (ocupa - 1), 36)
            painel(tela, area, "ouro")
            escrever(tela, dados["nome"], area, tema.pequena(), tema.OURO_CLARO, "centro", "meio", padding=4)
            espaco += ocupa
        for i in range(espaco, total):
            painel(tela, (x + i * (largura + 8), rect.y + 36, largura, 36), "pedra")
        texto(tela, f"Espaços: {progresso.espacos_usados()}/{total}   ·   Clique numa bênção para comprar; depois, "
                    "para equipar ou tirar.", tema.pequena(), tema.TEXTO_FRACO, (rect.x + 16, rect.y + 10))

    ALTURA_CARTAO = 134                   # nome + 3 linhas de descrição + estado

    def janela_da_grade(self, topo):
        """Retângulo da grade rolável: do 'topo' até acima do rodapé."""
        return pygame.Rect(16, topo, tema.LARGURA - 32, tema.ALTURA - 72 - topo)

    def desenhar_bencaos(self, tela):
        progresso = self.progresso
        self.desenhar_espacos(tela, painel(tela, (16, 120, tema.LARGURA - 32, 84), "ferro"))
        visiveis = [c for c in bencaos() if progresso.bencao_visivel(c)]
        escondidas = [c for c in bencaos() if not progresso.bencao_visivel(c)]
        chaves = visiveis + escondidas
        janela = self.janela_da_grade(212)
        total = altura_da_grade(len(chaves), 4, self.ALTURA_CARTAO, 8)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            for chave, rect in zip(chaves, grade((janela.x, y0, largura, total), len(chaves), 4, self.ALTURA_CARTAO, 8)):
                self.desenhar_bencao(tela, rect, chave, chave in escondidas)

    def desenhar_bencao(self, tela, rect, chave, escondida):
        """Cartão de uma bênção: nome e espaços em cima, descrição no meio, estado embaixo (faixas separadas)."""
        progresso = self.progresso
        dados = bencaos()[chave]
        interno = rect.inflate(-28, -16)
        if escondida:
            painel(tela, rect, "pedra")
            linha(tela, "Bênção escondida", tema.normal(), tema.TEXTO_APAGADO, interno.topleft, interno.width)
            escrever(tela, "Para liberar: " + descrever_conquista(dados.get("conquista", "")),
                     pygame.Rect(interno.x, interno.y + 30, interno.width, interno.height - 30), tema.pequena(),
                     tema.TEXTO_APAGADO)
            return
        comprada = chave in progresso.bencaos_compradas
        equipada = chave in progresso.bencaos_equipadas
        estilo = "ouro" if equipada else ("osso" if comprada else "ferro")
        if comprada:
            estado = "Equipada (clique para tirar)" if equipada else "Comprada (clique para equipar)"
        else:
            estado = f"Comprar: {dados['preco']} Brasas"
        self.botao(Botao(rect, "", (lambda c=chave: self.clicar_bencao(c)), estilo=estilo,
                         ativo=comprada or progresso.brasas >= dados["preco"],
                         dica=(dados["nome"], f"{dados['descricao']}\nOcupa {dados['espacos']} espaço(s).")))
        linha(tela, dados["nome"], tema.normal(), tema.TEXTO_TITULO, interno.topleft, interno.width - 14 * dados["espacos"])
        for k in range(dados["espacos"]):
            losango(tela, (interno.right - 4 - k * 14, interno.y + 12), 5, tema.OURO)
        escrever(tela, dados["descricao"], pygame.Rect(interno.x, interno.y + 26, interno.width, interno.height - 26 - 26),
                 tema.mini())
        cor = tema.OURO if equipada else (tema.TEXTO_FRACO if comprada else tema.VELA)
        linha(tela, estado, tema.pequena(), cor, interno.bottomleft, interno.width, "bottomleft")

    # ============================================================
    # PROVISÕES
    # ============================================================
    def pedir_provisao(self, chave, preco, loja="provisoes"):
        """Pergunta antes de gastar Brasas numa provisão."""
        self.confirmar("Comprar provisão", f"Comprar {item(chave).nome} por {preco} Brasas para a próxima run?",
                       lambda: self.comprar_provisao(chave, loja), "Comprar")

    def comprar_provisao(self, chave, loja="provisoes"):
        if self.progresso.comprar_provisao(chave, loja):
            self.progresso.salvar()
            self.mensagem = f"{item(chave).nome} guardado para a próxima run."
            self.app.audio.tocar("moeda")
        elif self.progresso.total_de_provisoes(loja) >= dados_da_taverna()[loja]["maximo"]:
            self.mensagem = "Esta loja já encheu a sua mochila de provisões."
        else:
            self.mensagem = "Brasas insuficientes."

    def desenhar_provisoes(self, tela, loja="provisoes"):
        regra = dados_da_taverna()[loja]
        progresso = self.progresso
        topo = painel(tela, (16, 120, tema.LARGURA - 32, 64), "ferro")
        guardadas = ", ".join(f"{item(c).nome} x{q}" for c, q in progresso.provisoes.items()) or "nada ainda"
        linha(tela, f"Para a próxima run ({progresso.total_de_provisoes(loja)}/{regra['maximo']} desta loja): {guardadas}",
              tema.normal(), tema.OURO_CLARO, (topo.x + 16, topo.centery), topo.width - 32, "midleft")
        itens = list(regra["itens"].items())
        cheia = progresso.total_de_provisoes(loja) >= regra["maximo"]
        janela = self.janela_da_grade(196)
        if loja == "mascarado":                     # o retrato do Mercador ocupa uma coluna à esquerda
            retrato = pygame.Rect(16, janela.y, 192, 192)
            self.desenhar_retrato_do_mercador(tela, retrato)
            janela = pygame.Rect(retrato.right + 16, janela.y, janela.right - retrato.right - 16, janela.height)
        colunas_da_grade = max(1, min(4, janela.width // 300))     # cartões de ~300 px: a descrição cabe
        total = altura_da_grade(len(itens), colunas_da_grade, 114, 8)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            celulas = grade((janela.x, y0, largura, total), len(itens), colunas_da_grade, 114, 8)
            for (chave, preco), rect in zip(itens, celulas):
                objeto = item(chave)
                self.botao(Botao(rect, "", (lambda c=chave, p=preco: self.pedir_provisao(c, p, loja)),
                                 ativo=not cheia and progresso.brasas >= preco,
                                 dica=(objeto.nome, objeto.descricao or objeto.resumo())))
                tela.blit(icone_item(objeto, 3), (rect.x + 12, rect.y + 12))
                linha(tela, objeto.nome, tema.normal(), tema.COR_RARIDADE[objeto.raridade], (rect.x + 80, rect.y + 8),
                      rect.width - 92)
                escrever(tela, objeto.descricao or objeto.resumo(), pygame.Rect(rect.x + 80, rect.y + 36, rect.width - 92, 44),
                         tema.mini(), tema.TEXTO_FRACO)
                linha(tela, f"{preco} Brasas", tema.normal(), tema.VELA, (rect.right - 14, rect.bottom - 6),
                      rect.width - 92, "bottomright")
        self.aviso = ("O Mercador tira as coisas da carroça com um sorriso pintado. Vão para a sua mochila quando a "
                      "expedição partir." if loja == "mascarado" else
                      "As provisões vão para a sua mochila quando a expedição parte. Só valem para a próxima run.")

    def desenhar_mascarado(self, tela):
        if self.progresso.loja_liberada("mascarado"):
            self.desenhar_provisoes(tela, "mascarado")
            return
        self.desenhar_retrato_do_mercador(tela, (16, 120, 192, 192), escondido=True)
        rect = painel(tela, (224, 120, tema.LARGURA - 240, 200), "pedra")
        escrever(tela, "Uma carroça coberta por um pano, trancada com sete cadeados. \"Ela é de um amigo meu\", diz o Taverneiro, "
                       "\"um mercador de máscara que anda pelas estradas do meio do caminho. Se você o vencer, ele "
                       "passa a vender para você.\"", rect.inflate(-40, -40), tema.normal(), tema.TEXTO_FRACO, vertical="meio")

    def desenhar_retrato_do_mercador(self, tela, rect, escondido=False):
        """Retrato do Mercador Mascarado (só a silhueta enquanto ele não foi vencido) e a fala dele."""
        rect = desenhar_retrato(tela, "mercador_mascarado", rect, "pedra" if escondido else "osso", escondido)
        fala = "\"...\"" if escondido else "\"Tudo tem preço.\""
        nome = "???" if escondido else "O Mercador Mascarado"
        linha(tela, nome, tema.normal(), tema.TEXTO_TITULO, (rect.x, rect.bottom + 12), rect.width)
        escrever(tela, fala, pygame.Rect(rect.x, rect.bottom + 40, rect.width, 60), tema.pequena(), tema.TEXTO_FRACO)

    # ============================================================
    # BOATOS
    # ============================================================
    def desenhar_boatos(self, tela):
        esquerda = painel(tela, (16, 120, 320, 520), "pedra")
        desenhar_npc(tela, self.app.sprites, "taverneiro", (esquerda.centerx, esquerda.bottom - 70), 4, self.tempo)
        linha(tela, "\"Senta aí. Ouvi umas coisas...\"", tema.pequena(), tema.TEXTO_FRACO,
              (esquerda.centerx, esquerda.bottom - 40), esquerda.width - 24, "midtop")
        boatos = self.progresso.boatos()
        janela = pygame.Rect(352, 120, tema.LARGURA - 368, esquerda.height)
        total = max(0, len(boatos) * 176 - 12)
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista, janela, total) as y0:
            for i, boato in enumerate(boatos):
                rect = painel(tela, (janela.x, y0 + i * 176, largura, 164), "osso")
                losango(tela, (rect.x + 24, rect.y + 30), 6, tema.OURO)
                escrever(tela, boato, pygame.Rect(rect.x + 44, rect.y + 12, rect.width - 60, rect.height - 24),
                         tema.normal(), tema.TEXTO, vertical="meio")
        self.aviso = "Os boatos mudam a cada run."

    # ============================================================
    # RARIDADES (vitrine de skins)
    # ============================================================
    def pedir_skin(self, chave):
        """Pergunta antes de gastar Brasas numa skin rara."""
        s = skin(chave)
        self.confirmar("Comprar skin", f"Comprar {s.nome} por {s.preco} Brasas?", lambda: self.comprar_skin(chave),
                       "Comprar")

    def comprar_skin(self, chave):
        if self.progresso.comprar_skin(chave):
            self.progresso.salvar()
            self.mensagem = f"{skin(chave).nome} comprada! Equipe no Baú."
            self.app.audio.tocar("moeda")
        else:
            self.mensagem = "Brasas insuficientes."

    def sprite_de_exemplo(self, s):
        """Uma classe vestindo a skin, para a prévia."""
        from roguelike.classes import todas_as_classes
        classes = todas_as_classes()
        chave = s.classes[0] if s.classes else ("mago" if s.camada == "chapeu" else "guerreiro")
        classe = classes[chave]
        return nome_do_sprite(classe.sprite_da_aparencia(classe.aparencia_padrao), {s.camada: s.chave})

    def desenhar_raridades(self, tela):
        vitrine = self.progresso.vitrine()
        largura = (tema.LARGURA - 32 - 2 * 12) // 3
        for i, chave in enumerate(vitrine):
            s = skin(chave)
            rect = pygame.Rect(16 + i * (largura + 12), 120, largura, 520)
            desenhar_previa(tela, self.app.sprites, self.sprite_de_exemplo(s), (rect.x, rect.y, rect.width, 330), self.tempo,
                            estilo="ouro" if chave in self.progresso.skins_compradas else "osso")
            linha(tela, s.nome, tema.media(), tema.TEXTO_TITULO, (rect.x + 4, rect.y + 340), rect.width - 8)
            para_quem = "qualquer classe" if not s.classes else ", ".join(c.capitalize() for c in s.classes)
            escrever(tela, f"{NOMES_DAS_CAMADAS[s.camada]} · {para_quem}\n{s.descricao}",
                     pygame.Rect(rect.x + 4, rect.y + 376, rect.width - 8, 80), tema.pequena(), tema.TEXTO_FRACO)
            if chave in self.progresso.skins_compradas:
                linha(tela, "Comprada — equipe no Baú", tema.normal(), tema.OURO, (rect.centerx, rect.bottom - 26),
                      rect.width, "center")
            else:
                self.botao(Botao((rect.x, rect.bottom - 50, rect.width, 46), f"Comprar ({s.preco} Brasas)",
                                 (lambda c=chave: self.pedir_skin(c)), ativo=self.progresso.brasas >= s.preco, estilo="ouro"))
        if not vitrine:
            texto(tela, "Nada na vitrine hoje.", tema.media(), tema.TEXTO_FRACO, (tema.LARGURA // 2, 380), "center")
        self.aviso = "A vitrine muda depois de cada run."

    # ============================================================
    # TELA
    # ============================================================
    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_do_acampamento(tela, "Taverna", self.progresso)
        desenhar_abas(self, (16, 66), ABAS, self.aba, self.trocar_aba)
        self.aviso = ""
        {"bencaos": self.desenhar_bencaos, "provisoes": self.desenhar_provisoes, "boatos": self.desenhar_boatos,
         "raridades": self.desenhar_raridades, "mascarado": self.desenhar_mascarado}[self.aba](tela)
        voltar = pygame.Rect(tema.LARGURA - 176, tema.ALTURA - 60, 160, 44)
        trechos = [(t, cor) for t, cor in ((self.aviso, tema.TEXTO_FRACO), (self.mensagem, tema.OURO_CLARO)) if t]
        if trechos:
            CaixaTexto((16, voltar.y - 4, voltar.x - 32, voltar.height + 8), tema.pequena(), vertical="meio").desenhar(
                tela, trechos)
        self.botao(Botao(voltar, "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
