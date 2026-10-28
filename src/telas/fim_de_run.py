"""Fim da run: resumo, Brasas, prestígio, conquistas e subclasses liberadas."""

import pygame

from roguelike.classes import todas_as_classes
from roguelike.progresso import descrever_conquista
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, desenhar_heroi_pequeno
from ui import tema
from ui.desenho import texto, painel
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto
from ui.widgets import Botao


class TelaFimDeRun(TelaComBotoes):
    def __init__(self, app, run, relatorio):
        super().__init__(app)
        self.run = run
        self.relatorio = relatorio
        self.resumo = run.resumo()
        self.vitoria = run.resultado == "vitoria"
        self.fuga = run.resultado == "fuga"                 # saiu vencendo o guardião: leva os itens
        self.fundo = Fundo(run.regiao_atual if self.vitoria or self.fuga else "titulo", escurecer=150)
        self.lista = PainelRolavel(passo=40)
        self.partida = app.partida if app.partida is not None and app.partida.run is run else None
        self.esperando_o_host = False           # (em grupo) quem entrou volta ao lobby quando o host voltar

    def musica(self):
        return "vitoria" if self.vitoria or self.fuga else "derrota"

    def musica_repete(self):
        return False

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)
        if self.esperando_o_host and (self.app.partida is None or self.app.partida.no_lobby()):
            fluxo.ir_para_acampamento(self.app)

    def voltar(self):
        """No solo, ao acampamento. Em grupo, ao lobby (o host leva todos; quem entrou espera o host)."""
        partida = self.partida
        if partida is not None and partida is self.app.partida and not partida.no_lobby():
            if not partida.eh_host:
                self.esperando_o_host = True
                return
            partida.voltar_ao_lobby()
        fluxo.ir_para_acampamento(self.app)

    def tecla(self, e):
        if e.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.voltar()

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        centro = tema.LARGURA // 2
        titulo = "A EXPEDIÇÃO VENCEU" if self.vitoria else ("A EXPEDIÇÃO ESCAPOU" if self.fuga else "A EXPEDIÇÃO CAIU")
        cor = tema.OURO_CLARO if self.vitoria else (tema.VELA if self.fuga else tema.SANGUE_CLARO)
        texto(tela, titulo, tema.grande(), cor, (centro, 14), "midtop")

        for i, heroi in enumerate(self.run.grupo.herois):
            x = centro - (len(self.run.grupo.herois) - 1) * 70 + i * 140
            desenhar_heroi_pequeno(tela, self.app.sprites, heroi, (x, 246), 2)

        resumo = self.resumo
        esquerda = painel(tela, (centro - 520, 256, 500, 360), "ferro")
        linhas = [
            ("Chegou a", f"{resumo['regiao']}, área {resumo['area']}"),
            ("Áreas vencidas", str(resumo["areas_vencidas"])),
            ("Inimigos derrotados", str(resumo["inimigos_derrotados"])),
            ("Itens obtidos", str(resumo["itens_obtidos"])),
            ("Ouro ganho", str(resumo["ouro_ganho"])),
            ("Chefes vencidos", str(len(resumo["chefes"]))),
            ("Semente", resumo["semente"]),
        ]
        texto(tela, "Resumo", tema.media(), tema.TEXTO_TITULO, (esquerda.x + 20, esquerda.y + 14))
        for i, (nome, valor) in enumerate(linhas):
            y = esquerda.y + 60 + i * 38
            texto(tela, nome, tema.normal(), tema.TEXTO_FRACO, (esquerda.x + 24, y))
            texto(tela, valor, tema.normal(), tema.TEXTO, (esquerda.right - 24, y), "topright")

        direita = painel(tela, (centro + 20, 256, 500, 360), "osso")
        texto(tela, "Para o acampamento", tema.media(), tema.TEXTO_TITULO, (direita.x + 20, direita.y + 14))
        texto(tela, f"+{self.relatorio.brasas} Brasas", tema.media(), tema.VELA, (direita.x + 24, direita.y + 60))
        trechos = self.trechos_do_relatorio()
        janela = pygame.Rect(direita.x + 24, direita.y + 100, direita.width - 40, direita.height - 112)
        caixa = CaixaTexto(pygame.Rect(0, 0, PainelRolavel.largura_util(janela, 10 ** 6), 10 ** 6), tema.pequena(),
                           fontes=[tema.pequena()])
        total = caixa.altura_para(trechos)
        caixa.rect = pygame.Rect(janela.x, 0, PainelRolavel.largura_util(janela, total), total)
        with self.rolavel(self.lista, janela, total) as y0:
            caixa.rect.y = y0
            caixa.desenhar(tela, trechos)

        if self.esperando_o_host:
            texto(tela, "Esperando o host voltar ao lobby...", tema.normal(), tema.TEXTO_FRACO,
                  (centro, tema.ALTURA - 56), "center")
        else:
            rotulo = "Voltar ao lobby" if self.partida is not None else "Voltar ao acampamento"
            self.botao(Botao((centro - 140, tema.ALTURA - 84, 280, 56), rotulo, self.voltar, "Enter", estilo="ouro"))
        self.terminar_desenho(tela)

    def trechos_do_relatorio(self):
        """[(texto, cor)] do que vai para o acampamento: arsenal, prestígio e conquistas novas."""
        trechos = []
        guardados = getattr(self.relatorio, "itens_guardados", [])
        if guardados:
            from roguelike.itens import item, ordem_da_raridade
            melhor = max((item(c) for c in guardados), key=lambda p: ordem_da_raridade(p.raridade))
            trechos.append((f"Arsenal: +{len(guardados)} peças (a melhor: {melhor.nome})", tema.COR_RARIDADE[melhor.raridade]))
        else:
            motivo = "nenhuma peça nova" if self.vitoria or self.fuga else "os itens se perderam"
            trechos.append((f"Arsenal: {motivo}", tema.TEXTO_FRACO))
        classes = todas_as_classes()
        for classe, (xp, niveis) in self.relatorio.prestigio.items():
            extra = f"  — prestígio {self.app.progresso.nivel_de_prestigio(classe)}!" if niveis else ""
            trechos.append((f"{classes[classe].nome}: +{xp} de prestígio{extra}", tema.OURO_CLARO if niveis else tema.TEXTO))
        novidades = [descrever_conquista(c) for c in self.relatorio.conquistas_novas]
        if self.relatorio.subclasses_novas:
            nomes = {s.chave: s.nome for c in classes.values() for s in c.subclasses.values()}
            novidades.append("Prestígio liberou subclasses novas na Capitã: " +
                             ", ".join(nomes.get(s, s) for s in self.relatorio.subclasses_novas))
        for chave in getattr(self.relatorio, "herois_novos", []):
            novidades.append(f"Herói novo no acampamento: {classes[chave].nome}!")
        for conquista in getattr(self.relatorio, "conquistas_feitas", []):
            from roguelike.skins import skin
            premio = f"skin {skin(conquista.skin).nome} liberada!" if conquista.skin else conquista.descricao
            novidades.append(f"Conquista {conquista.nome}: {premio}")
        if novidades:
            trechos.append(("Conquistas novas:", tema.TEXTO_TITULO))
            trechos += [(novidade, tema.CURA) for novidade in novidades]
        return trechos
