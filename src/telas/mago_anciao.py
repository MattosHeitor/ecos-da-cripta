"""Mago Ancião: escolhe a RAÇA e a SUBCLASSE de cada herói da expedição, com prévia animada.

As raças se liberam aqui com Brasas; as subclasses, pelo prestígio da classe (jogando com ela).
O que é escolhido fica na expedição (progresso), e a Capitã parte com essas escolhas.
"""

import pygame

from roguelike.classes import todas_as_classes
from roguelike.golpes import golpe
from roguelike.progresso import descrever_conquista
from roguelike.racas import raca, todas_as_racas
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, sprite_da_vaga, desenhar_previa, cabecalho_do_acampamento, desenhar_abas
from ui import tema
from ui.desenho import texto, painel, paragrafo, titulo_de_painel
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao

ABAS = (("raca", "Raça"), ("subclasse", "Subclasse"))


class TelaMagoAnciao(TelaComBotoes):
    def __init__(self, app, aba="raca", indice=0):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=150)
        self.aba = aba
        self.expedicao = app.progresso.expedicao_atual()
        self.indice = min(indice, len(self.expedicao.vagas) - 1)
        self.vista = None                   # raça/subclasse em destaque (antes de escolher)
        self.mensagem = ""
        self.lista = PainelRolavel(passo=56)
        self.olhar_escolhida()

    def musica(self):
        return "acampamento"

    @property
    def progresso(self):
        return self.app.progresso

    @property
    def vaga(self):
        return self.expedicao.vagas[self.indice]

    def voltar(self):
        self.progresso.salvar()
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    # ---------------- ações ----------------
    def olhar_escolhida(self):
        self.vista = self.vaga.raca if self.aba == "raca" else self.vaga.subclasse

    def escolher_vaga(self, indice):
        self.indice = indice
        self.mensagem = ""
        self.olhar_escolhida()

    def trocar_aba(self, aba):
        self.aba = aba
        self.mensagem = ""
        self.olhar_escolhida()

    def ver(self, chave):
        self.vista = chave
        self.mensagem = ""

    def escolher_raca(self, chave):
        if self.progresso.tem_raca(chave):
            self.vaga.raca = chave
            self.progresso.salvar()
            self.mensagem = f"{self.vaga.nome} agora é {raca(chave).nome}."
            self.app.audio.tocar("item")

    def pedir_raca(self, chave):
        """Pergunta antes de gastar Brasas para liberar a raça."""
        dados = raca(chave)
        self.confirmar("Liberar raça", f"Liberar {dados.nome} por {dados.preco} Brasas? Vale para sempre.",
                       lambda: self.comprar_raca(chave), "Liberar")

    def comprar_raca(self, chave):
        if self.progresso.comprar_raca(chave):
            self.vaga.raca = chave
            self.progresso.salvar()
            self.mensagem = f"{raca(chave).nome} liberada!"
            self.app.audio.tocar("item")
        else:
            self.mensagem = "Brasas insuficientes ou raça bloqueada."

    def escolher_subclasse(self, chave):
        liberadas = [s.chave for s in self.progresso.subclasses_disponiveis(self.vaga.classe)]
        if chave in liberadas:
            self.vaga.subclasse = chave
            self.progresso.salvar()
            self.mensagem = f"{self.vaga.nome} segue o caminho: {todas_as_classes()[self.vaga.classe].subclasses[chave].nome}."
            self.app.audio.tocar("item")

    # ---------------- desenho ----------------
    def vaga_com(self, **mudancas):
        """Cópia da vaga com outra raça/subclasse (para a prévia mostrar antes de escolher)."""
        from roguelike.expedicao import Vaga
        dados = self.vaga.para_dict()
        dados.update(mudancas)
        return Vaga.de_dict(dados)

    def desenhar_vagas(self, tela):
        largura = 236
        for i, vaga in enumerate(self.expedicao.vagas):
            classe = todas_as_classes()[vaga.classe]
            botao = Botao((16 + i * (largura + 10), 68, largura, 54), vaga.nome or classe.nome, (lambda k=i: self.escolher_vaga(k)),
                          subtexto=f"{classe.nome} · {raca(vaga.raca).nome}")
            botao.selecionado = i == self.indice
            self.botao(botao)

    def desenhar_lista_de_racas(self, tela, area):
        """Lista rolável das raças (liberadas, à venda ou bloqueadas)."""
        racas = list(todas_as_racas().items())
        total = len(racas) * 56 - 4
        largura = PainelRolavel.largura_util(area, total)
        with self.rolavel(self.lista, area, total) as y0:
            for i, (chave, dados) in enumerate(racas):
                tem, visivel = self.progresso.tem_raca(chave), self.progresso.raca_visivel(chave)
                sub = "escolhida" if chave == self.vaga.raca else (
                    "liberada" if tem else (f"{dados.preco} Brasas" if visivel else "bloqueada"))
                botao = Botao((area.x, y0 + i * 56, largura, 52), dados.nome, (lambda c=chave: self.ver(c)), subtexto=sub,
                              cor_texto=tema.TEXTO if visivel else tema.TEXTO_APAGADO, estilo="osso" if tem else "ferro")
                botao.selecionado = chave == self.vista
                self.botao(botao)

    def desenhar_lista_de_subclasses(self, tela, area):
        classe = todas_as_classes()[self.vaga.classe]
        prestigio = self.progresso.nivel_de_prestigio(classe.chave)
        for i, (chave, sub) in enumerate(classe.subclasses.items()):
            liberada = sub.prestigio <= prestigio
            estado = "escolhida" if chave == self.vaga.subclasse else ("liberada" if liberada else f"prestígio {sub.prestigio}")
            botao = Botao((area.x, area.y + i * 60, area.width, 54), sub.nome, (lambda c=chave: self.ver(c)), subtexto=estado,
                          cor_texto=tema.TEXTO if liberada else tema.TEXTO_APAGADO, estilo="osso" if liberada else "ferro")
            botao.selecionado = chave == self.vista
            self.botao(botao)
        paragrafo(tela, f"{classe.nome}: prestígio {prestigio}. Jogue com a classe para liberar as outras subclasses.",
                  tema.pequena(), tema.TEXTO_FRACO, (area.x, area.y + len(classe.subclasses) * 60 + 8), area.width,
                  maximo_linhas=4, encolher=True)

    def desenhar_detalhe_da_raca(self, tela, area):
        dados = raca(self.vista)
        tem, visivel = self.progresso.tem_raca(dados.chave), self.progresso.raca_visivel(dados.chave)
        linha(tela, dados.nome, tema.media(), tema.TEXTO_TITULO if visivel else tema.TEXTO_APAGADO, (area.x, area.y),
              area.width)
        y = paragrafo(tela, dados.descricao, tema.pequena(), tema.TEXTO_FRACO, (area.x, area.y + 36), area.width,
                      maximo_linhas=4, encolher=True)
        trechos = [("• " + v, tema.CURA) for v in dados.vantagens] + [("• " + d, tema.SANGUE_CLARO) for d in dados.desvantagens]
        CaixaTexto(pygame.Rect(area.x, y + 8, area.width, area.bottom - 70 - y), tema.pequena(), padding=0,
                   maximo_linhas=12).desenhar(tela, trechos)
        botao = (area.x, area.bottom - 50, area.width, 46)
        if tem:
            escolhida = dados.chave == self.vaga.raca
            self.botao(Botao(botao, "Escolhida" if escolhida else f"Escolher para {self.vaga.nome}",
                             (lambda c=dados.chave: self.escolher_raca(c)), ativo=not escolhida, estilo="ouro"))
        elif not visivel:
            linha(tela, "Bloqueada: " + descrever_conquista(dados.conquista), tema.normal(), tema.TEXTO_APAGADO,
                  (area.centerx, area.bottom - 26), area.width, "center")
        else:
            self.botao(Botao(botao, f"Liberar ({dados.preco} Brasas)", (lambda c=dados.chave: self.pedir_raca(c)),
                             ativo=self.progresso.brasas >= dados.preco, estilo="ouro"))

    def desenhar_detalhe_da_subclasse(self, tela, area):
        classe = todas_as_classes()[self.vaga.classe]
        sub = classe.subclasses[self.vista]
        liberada = sub.prestigio <= self.progresso.nivel_de_prestigio(classe.chave)
        linha(tela, sub.nome, tema.media(), tema.TEXTO_TITULO if liberada else tema.TEXTO_APAGADO, (area.x, area.y), area.width)
        y = paragrafo(tela, sub.descricao, tema.pequena(), tema.TEXTO_FRACO, (area.x, area.y + 36), area.width,
                      maximo_linhas=3, encolher=True)
        trechos = []
        for passiva in sub.passivas:
            trechos.append((f"Passiva — {passiva.get('nome', '')}: {passiva.get('descricao', '')}", tema.OURO_CLARO))
        niveis = sub.niveis_golpes
        for chave, nivel in zip(sub.golpes, niveis):
            nome = golpe(chave).nome if self.progresso.golpe_descoberto(chave) else "???"
            trechos.append((f"Nível {nivel}: {nome}", tema.TEXTO))
        for esp in sub.especializacoes.values():
            trechos.append((f"Especialização: {esp.nome} (treinador, nível {esp.nivel_minimo})", tema.XP))
        CaixaTexto(pygame.Rect(area.x, y + 8, area.width, area.bottom - 70 - y), tema.pequena(), padding=0,
                   maximo_linhas=12).desenhar(tela, trechos)
        if liberada:
            escolhida = sub.chave == self.vaga.subclasse
            self.botao(Botao((area.x, area.bottom - 50, area.width, 46),
                             "Escolhida" if escolhida else f"Escolher para {self.vaga.nome}",
                             (lambda c=sub.chave: self.escolher_subclasse(c)), ativo=not escolhida, estilo="ouro"))
        else:
            texto(tela, f"Libera no prestígio {sub.prestigio} da classe", tema.normal(), tema.TEXTO_APAGADO,
                  (area.centerx, area.bottom - 26), "center")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        sem_subclasse = "aprendiz" in self.progresso.especiais_equipados()
        cabecalho_do_acampamento(tela, "Mago Ancião", self.progresso, "Raça e caminho de cada herói")
        self.desenhar_vagas(tela)
        desenhar_abas(self, (16, 130), ABAS, self.aba, self.trocar_aba, largura=150)
        lista = painel(tela, (16, 182, 300, 470), "ferro").inflate(-20, -20)
        if self.aba == "raca":
            self.desenhar_lista_de_racas(tela, pygame.Rect(lista.x, lista.y, lista.width, lista.height))
            previa = self.vaga_com(raca=self.vista)
        else:
            self.desenhar_lista_de_subclasses(tela, lista)
            previa = self.vaga_com(subclasse=self.vista)
        rect_previa = desenhar_previa(tela, self.app.sprites, sprite_da_vaga(self.progresso, previa),
                                      (328, 130, 300, 522), self.tempo, escala=4)
        classe = todas_as_classes()[previa.classe]
        titulo_de_painel(tela, rect_previa, f"{previa.nome} · {classe.nome}")
        detalhe = painel(tela, (640, 130, tema.LARGURA - 656, 522), "ferro").inflate(-32, -32)
        if self.aba == "raca":
            self.desenhar_detalhe_da_raca(tela, detalhe)
        elif sem_subclasse:
            paragrafo(tela, "A bênção Aprendiz de Tudo está equipada: ninguém usa subclasse nesta expedição.",
                      tema.normal(), tema.TEXTO_FRACO, detalhe.topleft, detalhe.width)
        else:
            self.desenhar_detalhe_da_subclasse(tela, detalhe)
        voltar = pygame.Rect(tema.LARGURA - 176, tema.ALTURA - 60, 160, 44)
        CaixaTexto((16, voltar.y, voltar.x - 32, voltar.height), tema.normal(), tema.OURO_CLARO, alinhamento="centro",
                   vertical="meio").desenhar(tela, self.mensagem)
        self.botao(Botao(voltar, "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
