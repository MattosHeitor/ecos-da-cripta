"""Golpes de um herói: o golpe novo (ou escolhido), os equipados e o grimório lado a lado.

Dois jeitos de abrir:
- com um golpe NOVO esperando (espaços cheios): o jogador escolhe qual golpe vai para o grimório
  para abrir espaço, ou guarda o novo no grimório. Nada se perde.
- para organizar: escolhe um golpe do grimório e troca por um dos equipados.

Arrastar e soltar também troca: o golpe novo (ou um do grimório) em cima de um equipado; um equipado
em cima do grimório guarda. As cartas mostram "se trocar" em verde (▲ melhor) e vermelho (▼ pior).
"""

import pygame

from roguelike.comandos import DecidirGolpeNovo, TrocarGolpe, GuardarGolpe, MelhorarHabilidade
from roguelike.golpes import golpe, NOMES_DE_ALVO, NOMES_DE_TIPO
from telas.comum import TelaComBotoes, Fundo, cabecalho
from ui import tema
from ui.desenho import texto, painel, titulo_de_painel
from ui.layout import colunas, grade, altura_da_grade, area_util
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao

CORES_DE_TIPO = {"fisico": (220, 170, 120), "magico": (170, 150, 240), "suporte": (140, 210, 150)}
ARRASTO_MINIMO = 8                        # pixels que o mouse anda antes de virar arrasto


def media_de_dano(atual, nivel):
    dano = atual.dano(nivel)
    if dano is None:
        return None
    minimo, maximo, golpes = dano
    return (minimo + maximo) / 2 * golpes


def diferencas(atual, nivel, comparar):
    """[(texto, melhor?)] do que muda ao pôr o golpe comparado no lugar deste (melhor None = só diferente)."""
    partes = []
    dano_novo, dano_este = media_de_dano(*comparar), media_de_dano(atual, nivel)
    if dano_novo is not None or dano_este is not None:
        diferenca = (dano_novo or 0) - (dano_este or 0)
        if abs(diferenca) >= 0.5:
            partes.append((f"dano {diferenca:+.0f}", diferenca > 0))
    custo = comparar[0].custo - atual.custo
    if custo:
        partes.append((f"custo {custo:+d}", custo < 0))
    return partes or [("efeito diferente", None)]


def desenhar_troca(tela, posicao, atual, nivel, comparar, largura=400):
    """Linha "Se trocar: ▲ dano +2  ▼ custo +1" (verde = melhor, vermelho = pior)."""
    x, y = texto(tela, "Se trocar:", tema.mini(), tema.TEXTO_FRACO, posicao).topright
    fim = posicao[0] + largura
    for conteudo, melhor in diferencas(atual, nivel, comparar):
        seta, cor = ("▲ ", tema.CURA) if melhor else (("▼ ", tema.SANGUE_CLARO) if melhor is False else ("", tema.TEXTO))
        rect = linha(tela, seta + conteudo, tema.mini(), cor, (x + 6, y), max(20, fim - x - 6))
        x = rect.right + 4


def desenhar_carta(tela, rect, atual, nivel, heroi, comparar=None, estilo="ferro", reserva=0, destaque=False):
    """Carta de um golpe, montada de cima para baixo em faixas que não se cruzam.

    Em cima: nome e nível; tipo/alvo e custo; dano. No meio: o efeito (a fonte encolhe se precisar).
    Embaixo: "se trocar" (se houver comparação) e 'reserva' pixels livres para os botões.
    destaque: a carta grande (mais clara, com a evolução por extenso)."""
    rect = pygame.Rect(rect)
    painel(tela, rect, estilo)
    interno = rect.inflate(-28, -24) if destaque else rect.inflate(-26, -16)
    x, y = interno.x, interno.y
    maximo = heroi.nivel_maximo_da(atual.chave)
    nivel_rect = texto(tela, f"nv {nivel}/{maximo}", tema.mini(), tema.TEXTO_FRACO, (interno.right, y + 3), "topright")
    if atual.evolucao_para and not destaque:              # estrela: este golpe evolui (detalhe na dica)
        nivel_rect = texto(tela, "★", tema.mini(), tema.OURO, (nivel_rect.x - 4, y + 3), "topright")
    linha(tela, atual.nome, tema.media() if destaque else tema.normal(), tema.OURO_CLARO if destaque else
          tema.TEXTO_TITULO, (x, y), nivel_rect.x - x - 8)
    y += 32 if destaque else 24
    custo = linha(tela, atual.texto_custo(), tema.mini(), tema.ENERGIA_CLARA, (interno.right, y), interno.width // 2,
                  "topright")
    linha(tela, f"{NOMES_DE_TIPO[atual.tipo]} · {NOMES_DE_ALVO[atual.alvo]}", tema.mini(), CORES_DE_TIPO[atual.tipo],
          (x, y), custo.x - x - 8)
    y += 21
    dano = atual.dano(nivel)
    if dano is not None and destaque:                     # na carta compacta o efeito já diz o dano
        minimo, maximo_dano, golpes = dano
        linha(tela, f"Dano {minimo}-{maximo_dano}" + (f" x{golpes}" if golpes > 1 else ""), tema.normal(),
              tema.TEXTO, (x, y), interno.width)
        y += 26
    fundo = interno.bottom - reserva
    if destaque and atual.evolucao_para:
        conteudo = f"★ Evolui para {golpe(atual.evolucao_para).nome}: {atual.texto_do_requisito()}"
        evolucao = CaixaTexto(pygame.Rect(x, 0, interno.width, 60), tema.pequena(), tema.OURO, maximo_linhas=3)
        altura = evolucao.altura_para([(conteudo, tema.OURO)])
        evolucao.rect = pygame.Rect(x, fundo - altura, interno.width, altura)
        evolucao.desenhar(tela, conteudo)
        fundo -= altura + 6
    if comparar is not None and comparar[0].chave != atual.chave:
        desenhar_troca(tela, (x, fundo - 20), atual, nivel, comparar, interno.width)
        fundo -= 24
    CaixaTexto(pygame.Rect(x, y + 2, interno.width, max(20, fundo - y - 4)),
               tema.normal() if destaque else tema.pequena(),
               tema.TEXTO if destaque else tema.TEXTO_FRACO).desenhar(tela, atual.resumo(nivel))
    return rect


def texto_da_dica(atual, nivel):
    """Dica de uma carta: o efeito e, se houver, a evolução."""
    partes = [atual.descricao, atual.resumo(nivel), f"Custo: {atual.texto_custo()}"]
    if atual.evolucao_para:
        partes.append(f"★ Evolui para {golpe(atual.evolucao_para).nome}: {atual.texto_do_requisito()}")
    return "\n".join(p for p in partes if p)


class TelaGolpes(TelaComBotoes):
    def __init__(self, app, heroi, ao_sair, run=None):
        super().__init__(app)
        self.heroi = heroi
        self.ao_sair = ao_sair
        self.run = run
        self._sessao_do_heroi = None          # sem run (ex.: num teste): uma sessão só com este herói
        self.fundo = Fundo("acampamento", escurecer=170)
        self.escolhido = None             # golpe do grimório escolhido para comparar/trocar
        self.mensagem = ""
        self.lista_equipados = PainelRolavel(passo=80)
        self.lista_grimorio = PainelRolavel(passo=60)
        self.arrasto = None               # {"chave", "origem", "inicio", "ativo"}
        self.alvos = []                   # [(rect visível, tipo, chave)] onde dá para soltar (refeito a cada quadro)

    @property
    def golpes(self):
        return self.heroi.golpes

    def sessao(self):
        if self.run is not None:
            return super().sessao()
        if self._sessao_do_heroi is None:
            from roguelike.estado import EstadoDoJogo
            from roguelike.sessao import SessaoLocal
            self._sessao_do_heroi = SessaoLocal(EstadoDoJogo(herois=[self.heroi]))
        return self._sessao_do_heroi

    @property
    def numero(self):
        return self.indice_do(self.heroi)

    @property
    def novo(self):
        """O golpe novo esperando decisão (ou None)."""
        return self.golpes.pendentes[0] if self.golpes.pendentes else None

    def voltar(self):
        for novo in list(self.golpes.pendentes):   # sair com golpes novos = guardar no grimório (dá para trocar depois)
            self.enviar(DecidirGolpeNovo(heroi=self.numero, novo=novo))     # (em grupo, o estado muda quando o host
        self.ao_sair()                                                       #  devolver: por isso a lista copiada)

    # ---------------- ações ----------------
    def trocar_pelo_novo(self, esquecido):
        nome = golpe(self.novo).nome
        self.enviar(DecidirGolpeNovo(heroi=self.numero, novo=self.novo, esquecido=esquecido))
        self.mensagem = f"{nome} equipado. {golpe(esquecido).nome} foi para o grimório."
        self.terminar_se_pronto()

    def guardar_novo(self):
        if self.novo is None:
            return
        nome = golpe(self.novo).nome
        self.enviar(DecidirGolpeNovo(heroi=self.numero, novo=self.novo))
        self.mensagem = f"{nome} foi para o grimório."
        self.terminar_se_pronto()

    def terminar_se_pronto(self):
        self.app.audio.tocar("clique")

    def escolher_do_grimorio(self, chave):
        self.escolhido = None if self.escolhido == chave else chave

    def trocar(self, equipado=None):
        if self.escolhido is None:
            return
        nome = golpe(self.escolhido).nome
        if self.enviar(TrocarGolpe(heroi=self.numero, chave=self.escolhido, equipado=equipado)):
            self.mensagem = f"{nome} equipado." + (f" {golpe(equipado).nome} foi para o grimório." if equipado else "")
            self.escolhido = None

    def guardar(self, chave):
        if self.enviar(GuardarGolpe(heroi=self.numero, chave=chave)):
            self.mensagem = f"{golpe(chave).nome} foi para o grimório."
        else:
            self.mensagem = "Precisa ficar pelo menos um golpe equipado."

    def melhorar(self, chave):
        if self.enviar(MelhorarHabilidade(heroi=self.numero, chave=chave)):
            self.mensagem = f"{golpe(chave).nome} subiu para o nível {self.heroi.nivel_da(chave)}."

    # ---------------- arrastar e soltar ----------------
    def alvo_em(self, posicao, tipos):
        return next(((tipo, chave) for rect, tipo, chave in reversed(self.alvos)
                     if tipo in tipos and rect.collidepoint(posicao)), None)

    def evento(self, e):
        if self.dialogo is None:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                origem = self.alvo_em(e.pos, ("novo", "grimorio", "equipado"))
                if origem is not None and not (origem[0] == "grimorio" and self.novo):
                    self.arrasto = {"origem": origem[0], "chave": origem[1], "inicio": e.pos, "ativo": False}
            elif e.type == pygame.MOUSEMOTION and self.arrasto is not None:
                inicio = self.arrasto["inicio"]
                if abs(e.pos[0] - inicio[0]) + abs(e.pos[1] - inicio[1]) > ARRASTO_MINIMO:
                    self.arrasto["ativo"] = True
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.arrasto is not None:
                arrasto, self.arrasto = self.arrasto, None
                if arrasto["ativo"]:
                    self.mouse = e.pos
                    self.soltar(arrasto, e.pos)
                    return
        super().evento(e)

    def destinos(self, origem):
        """Onde cada tipo de golpe arrastado pode cair."""
        return {"novo": ("equipado", "lista_grimorio"), "grimorio": ("equipado", "livre"),
                "equipado": ("lista_grimorio",)}[origem]

    def soltar(self, arrasto, posicao):
        """Solta o golpe arrastado: troca com o equipado de baixo, ocupa o espaço livre ou vai ao grimório."""
        destino = self.alvo_em(posicao, self.destinos(arrasto["origem"]))
        if destino is None:
            return
        tipo, chave = destino
        if arrasto["origem"] == "novo":
            if tipo == "equipado":
                self.trocar_pelo_novo(chave)
            else:
                self.guardar_novo()
        elif arrasto["origem"] == "grimorio":
            self.escolhido = arrasto["chave"]
            self.trocar(chave if tipo == "equipado" else None)
        elif tipo == "lista_grimorio":
            self.guardar(arrasto["chave"])
        self.app.audio.tocar("item")

    def alvo(self, rect, tipo, chave=None):
        """Registra uma área de arrastar/soltar (só a parte visível, dentro de painel rolável)."""
        rect = pygame.Rect(rect)
        if self._abertos:
            rect = rect.clip(self._abertos[-1].rect)
        self.alvos.append((rect, tipo, chave))

    def destacar_destino(self, tela, rect, tipo):
        """Contorno dourado pulsando no lugar onde o golpe arrastado pode cair."""
        if self.arrasto and self.arrasto["ativo"] and tipo in self.destinos(self.arrasto["origem"]):
            sob = pygame.Rect(rect).collidepoint(self.mouse)
            cor = tema.OURO_CLARO if sob else tema.OURO
            pygame.draw.rect(tela, cor, pygame.Rect(rect).inflate(4, 4), 3 if sob else 1)

    def desenhar_arrasto(self, tela):
        if not (self.arrasto and self.arrasto["ativo"]):
            return
        from ui.desenho import desenhar_placa
        desenhar_placa(tela, (self.mouse[0], self.mouse[1] - 18), golpe(self.arrasto["chave"]).nome, tema.normal())

    # ---------------- desenho ----------------
    def comparacao(self):
        chave = self.novo or self.escolhido
        return (golpe(chave), self.heroi.nivel_da(chave)) if chave else None

    def desenhar_destaque(self, tela, coluna):
        """Coluna da esquerda: a carta grande do golpe novo (ou do escolhido) e a explicação."""
        chave = self.novo or self.escolhido
        titulo = "Golpe novo!" if self.novo else ("Do grimório" if chave else "Comparar")
        painel(tela, coluna, "ouro" if self.novo else "ferro")
        topo = titulo_de_painel(tela, coluna, titulo)
        area = pygame.Rect(coluna.x + 12, topo, coluna.width - 24, coluna.bottom - topo - 12)
        if chave is None:
            CaixaTexto(area, tema.pequena(), tema.TEXTO_FRACO, padding=6).desenhar(
                tela, "Escolha um golpe do grimório (à direita) para comparar com os equipados e trocar. "
                      "Você também pode arrastá-lo até um espaço. Fora do combate dá para trocar à vontade.")
            return
        explicacao = ("Arraste para um golpe equipado (ou use Trocar pelo novo). O antigo vai para o grimório."
                      if self.novo else "Arraste para um espaço ou clique em Trocar no golpe que vai sair.")
        caixa_explicacao = CaixaTexto(pygame.Rect(area.x, 0, area.width, 90), tema.pequena(), tema.TEXTO_FRACO)
        altura = caixa_explicacao.altura_para([(explicacao, tema.TEXTO_FRACO)])
        carta = pygame.Rect(area.x, area.y, area.width, area.height - altura - 10)
        desenhar_carta(tela, carta, golpe(chave), self.heroi.nivel_da(chave), self.heroi, estilo="osso", destaque=True)
        self.alvo(carta, "novo" if self.novo else "grimorio", chave)
        caixa_explicacao.rect = pygame.Rect(area.x, carta.bottom + 10, area.width, altura)
        caixa_explicacao.desenhar(tela, explicacao)

    def desenhar_equipados(self, tela, coluna):
        """Coluna do meio: os golpes equipados em cartas compactas (3 fileiras de 2 na janela)."""
        painel(tela, coluna, "ferro")
        topo = titulo_de_painel(tela, coluna, f"Equipados ({len(self.golpes.equipados)}/{self.golpes.espacos()})")
        janela = pygame.Rect(coluna.x + 14, topo, coluna.width - 28, coluna.bottom - topo - 14)
        espacos = self.golpes.espacos()
        altura = (janela.height - 2 * 10) // 3                      # 3 fileiras inteiras: os 6 espaços sem rolar
        total = altura_da_grade(espacos, 2, altura, 10)
        largura = PainelRolavel.largura_util(janela, total)
        self.lista_equipados.passo = altura + 10                    # a roda do mouse anda uma fileira
        comparar = self.comparacao()
        with self.rolavel(self.lista_equipados, janela, total) as y0:
            for i, rect in enumerate(grade((janela.x, y0, largura, total), espacos, 2, altura, 10)):
                self.desenhar_espaco(tela, rect, i, comparar)

    def desenhar_espaco(self, tela, rect, i, comparar):
        """Um espaço de golpe: a carta compacta e o botão dela (ou "Espaço livre")."""
        if i >= len(self.golpes.equipados):
            painel(tela, rect, "pedra")
            texto(tela, "Espaço livre", tema.normal(), tema.TEXTO_APAGADO, (rect.centerx, rect.y + 28), "midtop")
            self.alvo(rect, "livre")
            self.destacar_destino(tela, rect, "livre")
            if self.escolhido and not self.novo:
                self.botao(Botao((rect.centerx - 80, rect.bottom - 46, 160, 36), "Equipar aqui", self.trocar,
                                 estilo="ouro"))
            return
        chave = self.golpes.equipados[i]
        atual, nivel = golpe(chave), self.heroi.nivel_da(chave)
        desenhar_carta(tela, rect, atual, nivel, self.heroi, comparar, reserva=32)
        self.alvo(rect, "equipado", chave)
        self.destacar_destino(tela, rect, "equipado")
        visivel = rect.clip(self._abertos[-1].rect) if self._abertos else rect
        if visivel.collidepoint(self.mouse) and not self.arrasto:
            self.dica = (f"{atual.nome} — nível {nivel}", texto_da_dica(atual, nivel))
        botao = pygame.Rect(rect.x + 12, rect.bottom - 38, rect.width - 24, 28)
        if self.novo:
            self.botao(Botao(botao, "Trocar pelo novo", (lambda c=chave: self.trocar_pelo_novo(c)), estilo="sangue"))
        elif self.escolhido:
            self.botao(Botao(botao, f"Trocar por {golpe(self.escolhido).nome}", (lambda c=chave: self.trocar(c))))
        else:
            metade = (botao.width - 8) // 2
            if len(self.golpes.equipados) > 1:
                self.botao(Botao((botao.x, botao.y, metade, botao.height), "Ao grimório",
                                 (lambda c=chave: self.guardar(c))))
            if self.heroi.pode_melhorar(chave):
                self.botao(Botao((botao.right - metade, botao.y, metade, botao.height), "+1 nível",
                                 (lambda c=chave: self.melhorar(c)), estilo="ouro"))

    def desenhar_grimorio(self, tela, rect):
        """Coluna da direita: o grimório (golpes guardados) numa lista rolável."""
        painel(tela, rect, "ferro")
        topo = titulo_de_painel(tela, rect, f"Grimório ({len(self.golpes.grimorio)})")
        janela = pygame.Rect(rect.x + 14, topo, rect.width - 28, rect.bottom - topo - 14)
        self.alvo(janela, "lista_grimorio")
        self.destacar_destino(tela, janela, "lista_grimorio")
        if not self.golpes.grimorio:
            CaixaTexto(janela, tema.pequena(), tema.TEXTO_FRACO, padding=4).desenhar(
                tela, "Vazio. Golpes que saem dos espaços ficam guardados aqui (arraste um equipado para cá).")
            return
        total = len(self.golpes.grimorio) * 60 - 6
        largura = PainelRolavel.largura_util(janela, total)
        with self.rolavel(self.lista_grimorio, janela, total) as y0:
            for i, chave in enumerate(self.golpes.grimorio):
                atual, nivel = golpe(chave), self.heroi.nivel_da(chave)
                caixa = pygame.Rect(janela.x, y0 + i * 60, largura, 54)
                botao = Botao(caixa, atual.nome, (lambda c=chave: self.escolher_do_grimorio(c)),
                              subtexto=f"{NOMES_DE_TIPO[atual.tipo]} · {atual.texto_custo()} · nv {nivel}",
                              ativo=self.novo is None, dica=(atual.nome, texto_da_dica(atual, nivel)))
                botao.selecionado = chave == self.escolhido
                self.botao(botao)
                self.alvo(caixa, "grimorio", chave)

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.alvos = []
        self.fundo.desenhar(tela)
        pontos = self.heroi.pontos_habilidade
        cabecalho(tela, f"Golpes de {self.heroi.nome}", direita=f"Pontos de golpe: {pontos}",
                  cor_direita=tema.OURO_CLARO if pontos else tema.TEXTO_FRACO)
        esquerda, meio, direita = colunas(area_util(), [300, None, 290], espaco=12)
        self.desenhar_destaque(tela, esquerda)
        self.desenhar_equipados(tela, meio)
        self.desenhar_grimorio(tela, direita)
        rodape = pygame.Rect(16, tema.ALTURA - 58, tema.LARGURA - 32, 46)
        if self.novo:
            self.botao(Botao((rodape.x, rodape.y, esquerda.width, rodape.height), "Guardar o novo no grimório",
                             self.guardar_novo))
        elif self.escolhido:
            self.botao(Botao((rodape.x, rodape.y, esquerda.width, rodape.height), "Cancelar escolha",
                             lambda: self.escolher_do_grimorio(None)))
        CaixaTexto((meio.x, rodape.y, meio.width, rodape.height), tema.pequena(), tema.OURO_CLARO, alinhamento="centro",
                   vertical="meio").desenhar(tela, self.mensagem)
        sair = "Pronto" if not self.golpes.pendentes else "Guardar e sair"
        self.botao(Botao((direita.x, rodape.y, direita.width, rodape.height), sair, self.voltar, "ESC", estilo="ouro",
                         dica=None if not self.golpes.pendentes else
                         ("Guardar e sair", "Os golpes novos vão para o grimório: dá para trocar depois.")))
        if self.arrasto and self.arrasto["ativo"]:
            self.dica = None
        self.terminar_desenho(tela)
        self.desenhar_arrasto(tela)
