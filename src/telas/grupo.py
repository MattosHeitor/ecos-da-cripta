"""Grupo: os heróis (atributos, golpes, equipamento e a mochila do jogador, que os heróis dele dividem).

Abre do mapa da área (e da loja). O inventário com o baú da equipe (telas/inventario.py) e a fabricação
(telas/fabricacao.py) são telas próprias: os botões do topo levam a elas e elas voltam para cá.
"""

import pygame

from roguelike.atributos import nomes_dos_atributos, sigla
from roguelike.comandos import (DistribuirPonto, MelhorarHabilidade, Equipar, Desequipar, UsarItem, MoverItem)
from roguelike.dados import regras
from roguelike.itens import item
from telas.comum import TelaComBotoes, Fundo, texto_do_item, confirmar_venda
from ui import tema
from ui.desenho import texto, painel, paragrafo
from ui.icones import quadro_de_item
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha as ajustar_linha
from ui.widgets import Botao


class TelaGrupo(TelaComBotoes):
    TAB_TROCA_PAINEL = False                 # aqui o Tab passa para o próximo herói

    def __init__(self, app, run, aba="herois", ao_sair=None, loja=None):
        super().__init__(app)
        self.run = run
        self.grupo = run.grupo
        self.aba = aba
        self.ao_sair = ao_sair
        self.loja = loja                     # aberta pela loja: dá para vender
        self.fundo = Fundo.da_run(run, escurecer=170)
        meus = [i for i, h in enumerate(run.grupo.herois) if getattr(h, "jogador", None) == self.meu_jogador()]
        self.indice_heroi = meus[0] if meus else 0          # (partida em grupo: o 1º herói de quem joga aqui)
        self.selecao = None                  # ("mochila", chave), ("bau", chave) ou ("espaco", espaco)
        self.filtro = "todos"
        self.mensagem = ""
        self.lista_golpes = PainelRolavel(passo=34)
        self.paineis_de_grade = {}           # origem ("bau", "mochila") -> PainelRolavel

    # ---------------- utilidades ----------------
    @property
    def heroi(self):
        return self.grupo.herois[min(self.indice_heroi, len(self.grupo.herois) - 1)]

    def voltar(self):
        if self.ao_sair is not None:
            self.ao_sair()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def avisar(self, mensagem):
        self.mensagem = mensagem

    def tecla(self, e):
        if self.controles.eh(e, "proximo_heroi"):
            self.indice_heroi = (self.indice_heroi + 1) % len(self.grupo.herois)
            self.selecao = None
        elif self.controles.eh(e, "inventario") or self.controles.eh(e, "bau"):
            self.trocar_aba("bau")
        elif self.controles.eh(e, "fabricar"):
            self.trocar_aba("fabricacao")

    # ---------------- ações (cada uma vira um comando) ----------------
    def origem(self, inventario):
        """"bau" ou o número do herói dono da mochila (como os comandos falam do lugar de um item)."""
        return self.sessao().estado.origem_de(inventario)

    def aumentar_atributo(self, atributo):
        self.enviar(DistribuirPonto(heroi=self.indice_do(self.heroi), atributo=atributo))

    def melhorar(self, chave):
        if self.enviar(MelhorarHabilidade(heroi=self.indice_do(self.heroi), chave=chave)):
            self.avisar("Habilidade melhorada!")

    def equipar(self, chave, origem):
        if self.enviar(Equipar(heroi=self.indice_do(self.heroi), chave=chave, origem=self.origem(origem))):
            self.avisar(f"{item(chave).nome} equipado em {self.heroi.nome}.")
            self.selecao = None
        else:
            self.avisar("Não dá para equipar isso.")

    def desequipar(self, espaco):
        if self.enviar(Desequipar(heroi=self.indice_do(self.heroi), espaco=espaco)):
            self.avisar("Item guardado na mochila (ou no baú, se estiver cheia).")
        self.selecao = None

    def usar(self, chave, origem):
        if self.enviar(UsarItem(heroi=self.indice_do(self.heroi), chave=chave, origem=self.origem(origem))):
            self.avisar(f"{item(chave).nome} usado em {self.heroi.nome}.")
        else:
            self.avisar("Não teve efeito.")
        if not origem.tem(chave):
            self.selecao = None
        if self.heroi.golpes.pendentes:          # leu um tomo com os espaços cheios: escolher agora
            self.abrir_golpes()

    def abrir_golpes(self):
        from telas.golpes import TelaGolpes
        self.app.trocar(TelaGolpes(self.app, self.heroi, lambda: self.app.trocar(self), self.run))

    def mover(self, chave, origem, destino, nome_destino):
        """Mochila do herói <-> baú da equipe (o herói coloca ou retira, como manda o baú)."""
        de, para = self.origem(origem), self.origem(destino)
        if self.enviar(MoverItem(chave=chave, de=de, para=para)):
            self.avisar(f"{item(chave).nome} foi para {nome_destino}.")
        else:
            self.avisar("Não cabe (a mochila tem limite de pilhas).")
        if not origem.tem(chave):
            self.selecao = None

    def vender(self, chave, origem):
        def vendido(ganho):
            if ganho:
                self.avisar(f"Vendido por {ganho} de ouro.")
                self.app.audio.tocar("moeda")
            if not origem.tem(chave):
                self.selecao = None
        confirmar_venda(self, origem, chave, vendido)


    # ---------------- peças da tela ----------------
    def desenhar_seletor_de_herois(self, tela, y=72):
        largura = min(220, (tema.LARGURA - 32) // max(1, len(self.grupo.herois)) - 8)
        for i, heroi in enumerate(self.grupo.herois):
            sub = f"{heroi.nome_da_classe()} nv {heroi.nivel}" + ("" if heroi.esta_vivo() else " · caído")
            if heroi.pontos_atributo or heroi.pontos_habilidade:
                sub += " · pontos!"
            botao = Botao((16 + i * (largura + 8), y - 2, largura, 54), heroi.nome, (lambda i=i: self.escolher_heroi(i)),
                          subtexto=sub)
            botao.selecionado = i == self.indice_heroi
            self.botao(botao)

    def escolher_heroi(self, indice):
        self.indice_heroi = indice
        if self.selecao and self.selecao[0] != "bau":
            self.selecao = None

    def grade(self, tela, inventario, area, origem, colunas, tamanho=52, filtro=None):
        """Grade de itens de um inventário, rolável quando não cabe. Clique seleciona."""
        pilhas = inventario.pilhas(None if filtro in (None, "todos") else filtro)
        passo = tamanho + 6

        def altura(n_colunas):
            return ((len(pilhas) + n_colunas - 1) // n_colunas) * passo - 6

        colunas = max(1, min(colunas, (area.width + 6) // passo))
        total = altura(colunas)
        if total > area.height:                          # vai rolar: a barra toma um pouco da largura
            colunas = max(1, min(colunas, (PainelRolavel.largura_util(area, total) + 6) // passo))
            total = altura(colunas)
        painel_da_grade = self.paineis_de_grade.setdefault(origem, PainelRolavel(passo=passo))
        with self.rolavel(painel_da_grade, area, total) as y0:
            for i, (objeto, quantidade) in enumerate(pilhas):
                linha, coluna = divmod(i, colunas)
                pos = (area.x + coluna * passo, y0 + linha * passo)
                selecionado = self.selecao == (origem, objeto.chave)
                rect = quadro_de_item(tela, objeto, pos, tamanho, quantidade, selecionado)
                botao = self.registrar(Botao(rect, "", (lambda c=objeto.chave, r=rect: self.selecionar(origem, c, r))))
                if botao.em_cima(self.mouse):
                    self.dica = (objeto.nome, texto_do_item(objeto))
        return len(pilhas)

    def selecionar(self, origem, chave, ancora=None):
        """Seleciona um item e abre o menu de ações ao lado dele."""
        self.selecao = (origem, chave)
        self.ancora_menu = ancora

    def clique_livre(self, posicao):
        self.selecao = None             # clicar fora fecha o menu de ações

    # ---------------- aba: heróis ----------------
    def desenhar_atributos(self, tela, rect):
        heroi = self.heroi
        painel(tela, rect, "ferro")
        texto(tela, "Atributos", tema.normal(), tema.TEXTO_TITULO, (rect.x + 14, rect.y + 10))
        cor = tema.OURO_CLARO if heroi.pontos_atributo else tema.TEXTO_FRACO
        texto(tela, f"Pontos: {heroi.pontos_atributo}", tema.pequena(), cor, (rect.right - 14, rect.y + 14), "topright")
        y = rect.y + 44
        descricoes = regras()["descricao_atributos"]
        for atributo in nomes_dos_atributos():
            base, total = heroi.atributos[atributo], heroi.atributo(atributo)
            linha = pygame.Rect(rect.x + 12, y, rect.width - 24, 28)
            if linha.collidepoint(self.mouse):
                self.dica = (sigla(atributo), descricoes[atributo])
            texto(tela, sigla(atributo), tema.normal(), tema.TEXTO, (linha.x + 4, linha.centery), "midleft")
            valor = f"{total}" + (f"  ({base}{'+' if total >= base else ''}{total - base})" if total != base else "")
            texto(tela, valor, tema.normal(), tema.OURO_CLARO, (linha.x + 70, linha.centery), "midleft")
            if heroi.pontos_atributo > 0:
                self.botao(Botao((linha.right - 34, linha.y, 32, 28), "+", (lambda a=atributo: self.aumentar_atributo(a))))
            y += 31
        y += 8
        pygame.draw.line(tela, tema.OURO_ESCURO, (rect.x + 20, y), (rect.right - 20, y), 2)
        y += 10
        minimo, maximo = heroi.faixa_de_iniciativa()
        valores = [
            ("Vida", f"{heroi.vida}/{heroi.vida_maxima}" + (f"   Peste {heroi.peste}" if heroi.peste else "")),
            ("Crítico", f"{heroi.stat('chance_critico'):.0%}  (x{heroi.stat('dano_critico'):.2f})"),
            ("Esquiva", f"{heroi.stat('chance_esquiva'):.0%}"),
            ("Bloqueio", f"{heroi.stat('chance_bloqueio'):.0%}  (-{heroi.stat('reducao_bloqueio'):.0%} dano)"),
            ("Defesa", f"{round(heroi.stat('defesa'))}"),
            ("Iniciativa", f"{minimo}–{maximo}"),
            ("Energia/turno", f"{heroi.stat('ganho_energia'):.0%}"),
            ("Dano / cura", f"{1 + heroi.stat('dano_causado'):.0%} / {heroi.stat('cura_causada'):.0%}"),
            ("Roubo de vida", f"{heroi.stat('roubo_vida'):.0%}"),
        ]
        for nome, valor in valores:
            if y > rect.bottom - 22:
                break
            texto(tela, nome, tema.pequena(), tema.TEXTO_FRACO, (rect.x + 16, y))
            texto(tela, valor, tema.pequena(), tema.TEXTO, (rect.right - 16, y), "topright")
            y += 22

    def desenhar_habilidades(self, tela, rect):
        heroi = self.heroi
        painel(tela, rect, "ferro")
        texto(tela, "Golpes", tema.normal(), tema.TEXTO_TITULO, (rect.x + 14, rect.y + 10))
        cor = tema.OURO_CLARO if heroi.pontos_habilidade else tema.TEXTO_FRACO
        texto(tela, f"Pontos: {heroi.pontos_habilidade}", tema.pequena(), cor, (rect.right - 14, rect.y + 14), "topright")
        lista = heroi.habilidades()
        altura = 34
        botao_grimorio = pygame.Rect(rect.x + 10, rect.bottom - 140 - 44, rect.width - 20, 34)
        janela = pygame.Rect(rect.x + 10, rect.y + 42, rect.width - 20, botao_grimorio.y - 6 - rect.y - 42)
        total = len(lista) * altura - 4
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista_golpes, janela, total) as y:
            for habilidade, nivel in lista:
                self.desenhar_golpe(tela, pygame.Rect(janela.x, y, largura, altura - 4), habilidade, nivel)
                y += altura
        grimorio = len(heroi.golpes.grimorio)
        self.botao(Botao(botao_grimorio, f"Golpes e grimório ({grimorio} guardados)",
                         self.abrir_golpes, estilo="ouro" if heroi.golpes.pendentes else "ferro"))

        # subclasse e passivas
        y = rect.bottom - 140
        pygame.draw.line(tela, tema.OURO_ESCURO, (rect.x + 20, y), (rect.right - 20, y), 2)
        y += 8
        if heroi.especializacao is not None:
            esp = heroi.especializacao
            texto(tela, f"{heroi.subclasse.nome} > {esp.nome}", tema.normal(), tema.OURO, (rect.x + 14, y))
            paragrafo(tela, esp.descricao, tema.pequena(), tema.TEXTO_FRACO, (rect.x + 14, y + 28),
                      rect.width - 28, maximo_linhas=2, encolher=True)
        elif heroi.subclasse is not None:
            from roguelike.regioes import regiao
            esp = next(iter(heroi.subclasse.especializacoes.values()))
            texto(tela, f"Subclasse: {heroi.subclasse.nome}", tema.normal(), tema.OURO, (rect.x + 14, y))
            paragrafo(tela, f"Próximo passo: {esp.nome} — treinador em {regiao(esp.regiao).nome} ou na Catedral, "
                            f"a partir do nível {esp.nivel_minimo}.", tema.pequena(), tema.TEXTO_FRACO,
                      (rect.x + 14, y + 28), rect.width - 28, maximo_linhas=3, encolher=True)
        else:
            texto(tela, "Sem subclasse (bênção Aprendiz de Tudo).", tema.pequena(), tema.TEXTO_FRACO, (rect.x + 14, y))
        nomes = [p.nome for p in heroi.passivas if p.nome]
        area = pygame.Rect(rect.x + 14, rect.bottom - 36, rect.width - 28, 26)
        texto(tela, f"Passivas: {len(nomes)} (passe o mouse)", tema.pequena(), tema.TEXTO_FRACO, area.topleft)
        if area.collidepoint(self.mouse):
            descricoes = [f"• {p.nome}: {p.descricao}" if p.descricao else f"• {p.nome}" for p in heroi.passivas if p.nome]
            self.dica = ("Passivas", "\n".join(descricoes) or "Nenhuma.")

    def desenhar_golpe(self, tela, linha, habilidade, nivel):
        """Uma linha da lista de golpes: nome, nível/custo e o "+" de melhorar (a dica mostra o próximo nível)."""
        heroi = self.heroi
        maximo = heroi.nivel_maximo_da(habilidade.chave) if habilidade.chave in heroi.niveis_habilidade else nivel
        proximo = f"\nNível {nivel + 1}: {habilidade.resumo(nivel + 1)}" if nivel < maximo else "\n(nível máximo)"
        if linha.collidepoint(self.mouse) and (self._abertos[-1].rect.collidepoint(self.mouse) if self._abertos else True):
            self.dica = (f"{habilidade.nome} — nível {nivel}",
                         f"{habilidade.descricao}\n{habilidade.resumo(nivel)}\nCusto: {habilidade.texto_custo()}{proximo}")
        painel(tela, linha, "pedra")
        ajustar_linha(tela, habilidade.nome, tema.pequena(), tema.TEXTO, (linha.x + 10, linha.centery),
                      linha.width - 200, "midleft")
        ajustar_linha(tela, f"nv {nivel}/{maximo}   {habilidade.texto_custo()}", tema.mini(), tema.TEXTO_FRACO,
                      (linha.right - 44, linha.centery), 140, "midright")
        if heroi.pode_melhorar(habilidade.chave):
            self.botao(Botao((linha.right - 34, linha.y + 1, 30, linha.height - 2), "+",
                             (lambda c=habilidade.chave: self.melhorar(c))))

    def desenhar_equipamento(self, tela, rect):
        heroi = self.heroi
        painel(tela, rect, "ferro")
        texto(tela, "Equipamento", tema.normal(), tema.TEXTO_TITULO, (rect.x + 14, rect.y + 10))
        nomes = regras()["nomes_espacos"]
        espacos = regras()["espacos"]
        coluna = (rect.width - 28) // 2
        linhas = (len(espacos) + 1) // 2
        for i, espaco in enumerate(espacos):            # duas colunas: 9 espaços (8 do boneco + automático)
            x = rect.x + 14 + (i // linhas) * coluna
            y = rect.y + 40 + (i % linhas) * 46
            objeto = heroi.equipamento.get(espaco)
            largura = coluna - 52
            if objeto is None:
                painel(tela, (x, y, 42, 42), "espaco")
                ajustar_linha(tela, nomes[espaco], tema.mini(), tema.TEXTO_APAGADO, (x + 48, y + 1), largura)
                ajustar_linha(tela, "vazio", tema.mini(), tema.TEXTO_APAGADO, (x + 48, y + 21), largura)
                continue
            caixa = quadro_de_item(tela, objeto, (x, y), 42, selecionado=self.selecao == ("espaco", espaco))
            self.botoes.append(Botao(caixa, "", (lambda e=espaco, r=caixa: self.selecionar("espaco", e, r))))
            if espaco == "consumivel":
                extra = f" (x{heroi.inventario.quantidade(objeto.chave)})"
            elif espaco in heroi.equipamentos.travados:
                extra = " · preso"
            else:
                extra = ""
            ajustar_linha(tela, nomes[espaco] + extra, tema.mini(),
                          tema.SANGUE_CLARO if "preso" in extra else tema.TEXTO_FRACO, (x + 48, y + 1), largura)
            ajustar_linha(tela, objeto.nome, tema.mini(), tema.COR_RARIDADE[objeto.raridade], (x + 48, y + 21), largura)
            if caixa.collidepoint(self.mouse):
                preso = "\nAmaldiçoado: preso até a próxima fogueira." if "preso" in extra else ""
                self.dica = (objeto.nome, texto_do_item(objeto) + preso + "\nClique para selecionar.")
        y = rect.y + 40 + linhas * 46
        texto(tela, f"Mochila ({len(heroi.inventario.itens)}/{heroi.inventario.capacidade})", tema.normal(),
              tema.TEXTO_TITULO, (rect.x + 14, y + 4))
        self.grade(tela, heroi.inventario, pygame.Rect(rect.x + 14, y + 34, rect.width - 28, 120), "mochila", 6, 50)

    def opcoes_da_selecao(self):
        """(nome, ação) possíveis para o item selecionado (equipar, usar, mover, vender...)."""
        if self.selecao is None:
            return []
        origem_nome, chave = self.selecao
        heroi = self.heroi
        if origem_nome == "espaco":
            if heroi.equipamento.get(chave) is None:
                self.selecao = None
                return []
            return [("Tirar", lambda: self.desequipar(chave))]
        origem = heroi.inventario if origem_nome == "mochila" else self.grupo.bau
        if not origem.tem(chave):
            self.selecao = None
            return []
        objeto = item(chave)
        opcoes = []
        if objeto.tipo == "equipamento":
            opcoes.append((f"Equipar em {heroi.nome}", lambda: self.equipar(chave, origem)))
        elif objeto.tipo == "consumivel" and origem_nome == "mochila":
            opcoes.append(("Usar sozinho no combate", lambda: self.equipar(chave, origem)))
        if getattr(objeto, "ensina", None):
            if objeto.pode_ler(heroi):
                opcoes.append((f"{heroi.nome} lê (aprende {objeto.golpe().nome})", lambda: self.usar(chave, origem)))
        elif objeto.tipo == "consumivel" and objeto.fora_de_combate:
            opcoes.append((f"Usar em {heroi.nome}", lambda: self.usar(chave, origem)))
        if origem_nome == "mochila":
            opcoes.append(("Guardar no baú", lambda: self.mover(chave, origem, self.grupo.bau, "o baú")))
        else:
            opcoes.append(("Pegar para a mochila", lambda: self.mover(chave, origem, heroi.inventario, "a mochila")))
        if self.loja is not None:
            opcoes.append((f"Vender (+{objeto.preco_de_venda()} ouro)", lambda: self.vender(chave, origem)))
        return opcoes

    def desenhar_menu_de_acoes(self, tela):
        """Menu pequeno ao lado do item clicado (desenhado por cima de tudo)."""
        opcoes = self.opcoes_da_selecao()
        ancora = getattr(self, "ancora_menu", None)
        if not opcoes or ancora is None:
            return
        largura, altura = 230, 36
        rect = pygame.Rect(ancora.right + 6, ancora.y, largura + 16, len(opcoes) * (altura + 4) + 12)
        if rect.right > tema.LARGURA - 8:
            rect.right = ancora.x - 6
        rect.bottom = min(rect.bottom, tema.ALTURA - 72)
        painel(tela, rect, "pedra")
        for i, (nome, acao) in enumerate(opcoes):
            self.botao(Botao((rect.x + 8, rect.y + 6 + i * (altura + 4), largura, altura), nome, acao))
        self.dica = None

    def desenhar_aba_herois(self, tela):
        self.desenhar_seletor_de_herois(tela)
        heroi = self.heroi
        topo = 132
        self.desenhar_atributos(tela, pygame.Rect(8, topo, 300, 512))
        self.desenhar_habilidades(tela, pygame.Rect(316, topo, 460, 512))
        self.desenhar_equipamento(tela, pygame.Rect(784, topo, tema.LARGURA - 792, 512))
        if not heroi.esta_vivo():
            texto(tela, f"{heroi.nome} está caído. Use uma Pena da Fênix, um altar ou um necromante.", tema.normal(),
                  tema.SANGUE_CLARO, (tema.LARGURA // 2, 652), "midtop")

    # ---------------- tela ----------------
    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela, frente=False)
        topo = painel(tela, (8, 8, tema.LARGURA - 16, 56), "ferro")
        abas = [("herois", "Heróis", None), ("bau", "Inventário e baú", "I"), ("fabricacao", "Fabricação", "F")]
        x = topo.x + 12
        for aba, nome, atalho in abas:
            largura = 200 if aba == "bau" else 150
            self.botao(Botao((x, topo.y + 8, largura, 40), nome, (lambda a=aba: self.trocar_aba(a)), atalho,
                             selecionado=self.aba == aba))
            x += largura + 10
        texto(tela, f"Ouro {self.meu_jogador().ouro}", tema.normal(), tema.OURO_MOEDA, (topo.right - 200, topo.centery),
              "midleft")
        self.desenhar_aba_herois(tela)
        voltar = pygame.Rect(tema.LARGURA - 196, tema.ALTURA - 62, 180, 48)
        if self.mensagem:
            CaixaTexto((24, voltar.y, voltar.x - 48, voltar.height), tema.normal(), tema.OURO_CLARO,
                       vertical="meio").desenhar(tela, self.mensagem)
        nome_voltar = "Voltar à loja" if self.loja is not None else "Voltar"
        self.botao(Botao(voltar, nome_voltar, self.voltar, "ESC"))
        self.desenhar_menu_de_acoes(tela)                 # por cima de tudo
        self.terminar_desenho(tela)

    def trocar_aba(self, aba):
        """Heróis fica aqui; o baú (inventário) e a fabricação são telas próprias, que voltam para cá."""
        from telas import fluxo
        voltar = lambda: self.app.trocar(TelaGrupo(self.app, self.run, "herois", self.ao_sair, self.loja))
        if aba == "bau":
            fluxo.abrir_inventario(self.app, self.run, voltar, "bau", self.loja, self.indice_heroi)
        elif aba == "fabricacao":
            fluxo.abrir_fabricacao(self.app, self.run, voltar, self.indice_heroi)
        else:
            self.aba = "herois"
            self.selecao = None

    def ao_entrar(self):
        super().ao_entrar()
        if self.aba in ("bau", "fabricacao"):              # aberto direto numa dessas abas: vai para a tela dela
            aba, self.aba = self.aba, "herois"
            self.trocar_aba(aba)
