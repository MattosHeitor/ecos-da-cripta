"""Peças usadas por várias telas: fundo animado, cabeçalho da run, retratos e salvar.

Também guarda TelaComBotoes: uma Tela que redesenha os botões a cada quadro
e já cuida de cliques, dicas e do ESC.
"""

import os
from contextlib import contextmanager

import pygame

from caminhos import CAMINHOS
from telas.base import Tela
from ui import tema
from ui.desenho import texto, vinheta, escurecer_tela, painel
from ui.widgets import desenhar_dica

class Fundo:
    """Cenário macabro (camadas, luzes, partículas) + escurecimento + vinheta.

    lugar: "titulo", "acampamento" ou uma região ("floresta"...). Com 'area', usa a variante e a hora
    do dia da área (a céu aberto, o começo da região é de dia e o fim, à noite); 'total' = áreas da
    fase nesta run. Fundo.da_run(run) já passa tudo.
    figurantes: quem anda dentro do cenário (ex.: o Rato Branco correndo), atrás da camada da frente.
    """

    def __init__(self, lugar, escurecer=0, area=1, total=None):
        from visual.cenario_macabro import CenarioMacabro, cena_da_area, hora_da_area, paleta_do_lugar
        nome, variante = cena_da_area(lugar, area, total=total)
        self.cenario = CenarioMacabro(nome, variante, tema.LARGURA, tema.ALTURA, hora_da_area(lugar, area, total),
                                      paleta_do_lugar(lugar))
        self.escurecer = escurecer
        self.figurantes = []

    @classmethod
    def da_run(cls, run, escurecer=0):
        return cls(run.regiao_atual, escurecer, run.area, run.areas_da_regiao())

    def atualizar(self, dt):
        self.cenario.atualizar(dt)
        for figurante in self.figurantes:
            figurante.atualizar(dt)

    def desenhar(self, tela, frente=True):
        self.cenario.desenhar(tela)
        for figurante in self.figurantes:
            figurante.desenhar(tela)
        if frente:
            self.cenario.desenhar_frente(tela)
        if self.escurecer:
            escurecer_tela(tela, self.escurecer)
        tela.blit(vinheta(tela.get_size(), 180), (0, 0))


class TelaComBotoes(Tela):
    """Tela com botões refeitos a cada desenho, com teclado e mouse prontos.

    - Mouse: clique nos botões, botão direito = voltar, roda = rolagem (do painel sob o mouse).
    - Teclado: setas/WASD movem o FOCO para o botão mais próximo naquela direção,
      confirmar (Enter) aperta o botão focado, voltar (Esc) chama voltar(),
      Tab / Shift+Tab pulam para o próximo painel, PageUp/PageDown/Home/End rolam.
    - Painéis roláveis: with self.rolavel(painel, rect, altura) as y0 -> os botões criados dentro ficam
      recortados na janela do painel, e o painel rola sozinho até o botão focado pelo teclado.
    - Diálogo de confirmação: abrir_dialogo(...) bloqueia o resto da tela até a resposta.
    As telas só precisam desenhar os botões com self.botao(...) e, se quiserem, tratar
    outras teclas em tecla(e).
    """

    TAB_TROCA_PAINEL = True              # False nas telas em que o Tab tem outro uso (próximo herói)
    PAGINAS_ROLAM = True                 # False nas telas em que PageUp/PageDown têm outro uso (trocar herói)

    def __init__(self, app):
        super().__init__(app)
        self.botoes = []
        self.mouse = (0, 0)
        self.dica = None
        self.rolagem = 0
        self.foco = None                 # chave do botão focado (Botao.chave_foco)
        self.usando_teclado = False      # o destaque segue o teclado (e não o mouse)
        self.dialogo = None
        self._foco_achado = False
        self.paineis = []                # painéis roláveis desenhados neste quadro
        self._abertos = []               # pilha dos painéis abertos (desenhando dentro deles)

    @contextmanager
    def rolavel(self, painel, rect, altura_conteudo):
        """Desenha dentro de um PainelRolavel: devolve o y inicial do conteúdo (já rolado)."""
        y0 = painel.comecar(self.tela_atual, rect, altura_conteudo)
        self.paineis.append(painel)
        self._abertos.append(painel)
        try:
            yield y0
        finally:
            self._abertos.pop()
            painel.terminar(self.tela_atual)

    @property
    def controles(self):
        return self.app.controles

    def voltar(self):
        """O que o ESC (ou botão direito) faz. As telas mudam isso."""

    def abrir_dialogo(self, titulo, mensagem, opcoes):
        """Pergunta antes de algo sem volta. opcoes = [(rótulo, ação), ..., ("Cancelar", None)]."""
        from ui.componentes import DialogoDeConfirmacao
        self.dialogo = DialogoDeConfirmacao(titulo, mensagem, opcoes)

    def confirmar(self, titulo, mensagem, acao, rotulo="Confirmar"):
        """Atalho do "tem certeza?" para uma ação sem volta (gastar Brasas, descartar...)."""
        self.abrir_dialogo(titulo, mensagem, [(rotulo, acao), ("Cancelar", None)])

    def evento(self, e):
        if self.dialogo is not None:
            self.dialogo.evento(e, self.controles)
            if not self.dialogo.aberto:
                self.dialogo = None
            return
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
            if e.type != pygame.MOUSEWHEEL:
                self.mouse = e.pos
            if any(painel.evento(e) for painel in reversed(self.paineis)):     # roda, barra arrastada
                return
        if e.type == pygame.KEYDOWN and self._tecla_de_painel(e):
            return
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            self.usando_teclado = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            self.usando_teclado = False
            for botao in reversed(self.botoes):
                if botao.clicar(e.pos):
                    self.app.audio.tocar("clique")
                    return
            self.clique_livre(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.app.audio.tocar("voltar")
            self.voltar()
        elif e.type == pygame.MOUSEWHEEL:
            self.rolagem = max(0, self.rolagem - e.y)
        elif e.type == pygame.KEYDOWN:
            direcao = self.controles.direcao(e)
            if self.controles.eh(e, "voltar"):
                self.app.audio.tocar("voltar")
                self.voltar()
            elif direcao is not None and not self.tecla_de_direcao(e, direcao):
                self.mover_foco(*direcao)
            elif self.controles.eh(e, "confirmar") and self.usando_teclado and self.apertar_foco():
                return
            else:
                self.tecla(e)

    def tecla_de_direcao(self, e, direcao):
        """As telas podem usar as setas para outra coisa (devolvendo True)."""
        return False

    def _tecla_de_painel(self, e):
        """Tab/Shift+Tab (próximo painel) e PageUp/PageDown/Home/End (rolar). True se usou a tecla."""
        if e.key == pygame.K_TAB and self.TAB_TROCA_PAINEL:
            self.proximo_grupo(-1 if e.mod & pygame.KMOD_SHIFT else 1)
            return True
        paginas = (pygame.K_PAGEUP, pygame.K_PAGEDOWN) if self.PAGINAS_ROLAM else ()
        if e.key in paginas + (pygame.K_HOME, pygame.K_END):
            painel = self._painel_da_tecla()
            return painel is not None and painel.tecla(e)
        return False

    def _painel_da_tecla(self):
        """O painel que as teclas de rolagem movem: o do foco, o que está sob o mouse ou o maior."""
        focado = self._botao_focado()
        if self.usando_teclado and focado is not None and focado.painel is not None:
            return focado.painel
        rolaveis = [p for p in self.paineis if p.rola]
        sob_o_mouse = next((p for p in rolaveis if p.rect.collidepoint(self.mouse)), None)
        return sob_o_mouse or max(rolaveis, key=lambda p: p.rect.width * p.rect.height, default=None)

    def grupos_de_foco(self):
        """Os botões focáveis separados por painel (fora de painel = um grupo), na ordem de leitura."""
        grupos = {}
        for botao in self._focaveis():
            grupos.setdefault(id(botao.painel) if botao.painel is not None else None, []).append(botao)
        return sorted(grupos.values(), key=lambda lista: min((b.rect.y, b.rect.x) for b in lista))

    def proximo_grupo(self, passo=1):
        """Tab: leva o foco ao primeiro botão do próximo painel (com um só grupo, ao próximo botão)."""
        grupos = self.grupos_de_foco()
        self.usando_teclado = True
        if not grupos:
            return
        atual = self._botao_focado()
        if len(grupos) == 1:
            lista = sorted(grupos[0], key=lambda b: (b.rect.y, b.rect.x))
            indice = lista.index(atual) + passo if atual in lista else 0
            escolhido = lista[indice % len(lista)]
        else:
            indice = next((i for i, g in enumerate(grupos) if atual in g), -1 if passo > 0 else 0)
            grupo = grupos[(indice + passo) % len(grupos)]
            visiveis = [b for b in grupo if b.painel is None or b.painel.visivel(b.rect)] or grupo
            escolhido = min(visiveis, key=lambda b: (b.rect.y, b.rect.x))
        self.foco = escolhido.chave_foco
        self.app.audio.tocar("navegar")

    def clique_livre(self, posicao):
        """Clique fora dos botões."""

    def tecla(self, e):
        """Teclas além das de navegação (atalhos da tela, Enter sem foco...)."""

    # ---------------- foco do teclado ----------------
    def _focaveis(self):
        return [b for b in self.botoes if b.ativo and b.acao is not None and b.focavel]

    def _botao_focado(self):
        return next((b for b in self._focaveis() if b.chave_foco == self.foco), None)

    def mover_foco(self, dx, dy):
        """Vai para o botão mais perto na direção (dx, dy). Devolve False se não havia para onde ir
        (aí uma lista com rolagem rola)."""
        focaveis = self._focaveis()
        self.usando_teclado = True
        if not focaveis:
            painel = self._painel_da_tecla()
            if dy and painel is not None:
                painel.rolar(dy * painel.passo)
            return False
        atual = self._botao_focado()
        if atual is None:
            escolhido = min(focaveis, key=lambda b: (b.rect.y, b.rect.x))
        else:
            origem = atual.rect.center
            melhor, escolhido = None, None
            for botao in focaveis:
                if botao is atual:
                    continue
                vx, vy = botao.rect.centerx - origem[0], botao.rect.centery - origem[1]
                adiante = vx * dx + vy * dy
                if adiante <= 4:
                    continue
                desvio = abs(vx * dy - vy * dx)
                nota = adiante + desvio * 2
                if melhor is None or nota < melhor:
                    melhor, escolhido = nota, botao
            if escolhido is None:
                if dy:
                    self.rolagem = max(0, self.rolagem + dy)
                    painel = atual.painel or self._painel_da_tecla()   # sem botão adiante: rola o painel
                    if painel is not None:
                        painel.rolar(dy * painel.passo)
                return False
        self.foco = escolhido.chave_foco
        self.app.audio.tocar("navegar")
        return True

    def focar_primeiro(self):
        """Põe o foco no primeiro botão (ao abrir um menu pelo teclado)."""
        focaveis = self._focaveis()
        if focaveis:
            self.foco = min(focaveis, key=lambda b: (b.rect.y, b.rect.x)).chave_foco

    def apertar_foco(self):
        botao = self._botao_focado()
        if botao is None:
            return False
        self.app.audio.tocar("clique")
        botao.acao()
        return True

    # ---------------- desenho ----------------
    def botao(self, botao):
        """Registra e desenha um botão (chamado dentro de desenhar). Dentro de self.rolavel(...), o botão
        fica recortado na janela do painel e a chave do foco não muda quando a lista rola."""
        self.botoes.append(botao)
        if self._abertos:
            painel = self._abertos[-1]
            botao.painel = painel
            botao.recorte = painel.rect
            botao.chave_foco = (id(painel), botao.rect.x, botao.rect.y + round(painel.deslocamento),
                                botao.rect.width, botao.rect.height)
        if self.foco is not None and botao.chave_foco == self.foco and botao.ativo:
            botao.focado = self.usando_teclado
            self._foco_achado = True
            self._rect_do_foco = pygame.Rect(botao.rect)
        botao.desenhar(self.tela_atual, (-1, -1) if self.usando_teclado else self.mouse)
        if botao.dica and (botao.focado or (not self.usando_teclado and botao.em_cima(self.mouse))):
            self.dica = botao.dica
            self.posicao_da_dica = botao.rect.bottomright if botao.focado else self.mouse
        return botao

    def registrar(self, botao):
        """Registra um botão invisível (a tela já desenhou o que ele cobre: ícone, retrato...).
        Dentro de um painel rolável ele também fica recortado na janela e com a chave de foco estável."""
        self.botoes.append(botao)
        if self._abertos:
            painel = self._abertos[-1]
            botao.painel, botao.recorte = painel, painel.rect
            botao.chave_foco = (id(painel), botao.rect.x, botao.rect.y + round(painel.deslocamento),
                                botao.rect.width, botao.rect.height)
        if self.foco is not None and botao.chave_foco == self.foco and botao.ativo:
            botao.focado = self.usando_teclado
            self._foco_achado = True
            self._rect_do_foco = pygame.Rect(botao.rect)
            if botao.focado:
                pygame.draw.rect(self.tela_atual, tema.OURO_CLARO, botao.rect.inflate(6, 6), 2)
        return botao

    def comecar_desenho(self, tela):
        self.botoes = []
        self.paineis = []
        self.dica = None
        self.posicao_da_dica = self.mouse
        self.tela_atual = tela
        self._foco_achado = False

    def terminar_desenho(self, tela):
        if self.foco is not None and not self._foco_achado and self.usando_teclado:
            # o botão focado sumiu (a tela mudou): vai para o mais próximo
            focaveis = self._focaveis()
            if focaveis:
                cx, cy = getattr(self, "_rect_do_foco", pygame.Rect(0, 0, 0, 0)).center
                perto = min(focaveis, key=lambda b: (b.rect.centerx - cx) ** 2 + (b.rect.centery - cy) ** 2)
                self.foco = perto.chave_foco
        focado = self._botao_focado() if self.usando_teclado else None
        if focado is not None and focado.painel is not None and not focado.painel.visivel(focado.rect):
            focado.painel.mostrar(focado.rect)             # o foco do teclado nunca fica escondido
        if self.dica is not None and self.dialogo is None:
            titulo, conteudo = self.dica
            desenhar_dica(tela, self.posicao_da_dica, titulo, conteudo)
        if self.dialogo is not None:
            self.dialogo.desenhar(tela)

def confirmar_venda(tela, inventario, chave, ao_vender):
    """Abre o "tem certeza?" antes de vender (1 ou a pilha toda). ao_vender(ganho) recebe o ouro."""
    from roguelike.comandos import Vender
    from roguelike.itens import item
    objeto = item(chave)
    quantidade = inventario.itens.get(chave, 0)
    if quantidade <= 0:
        return
    preco = objeto.preco_de_venda()
    origem = tela.sessao().estado.origem_de(inventario)

    def vender(qtd):
        return lambda: ao_vender(tela.enviar(Vender(origem=origem, chave=chave, quantidade=qtd)).valor or 0)

    opcoes = [(f"Vender 1 (+{preco})", vender(1))]
    if quantidade > 1:
        opcoes.append((f"Todos x{quantidade} (+{preco * quantidade})", vender(quantidade)))
    opcoes.append(("Cancelar", None))
    tela.abrir_dialogo("Vender", f"Vender {objeto.nome}? Não dá para desfazer.", opcoes)


def cabecalho_da_run(tela, run, titulo=None, jogador=None):
    """Faixa de cima: região, área, o ouro e a mochila do 'jogador' (o deste computador), semente."""
    rect = pygame.Rect(8, 8, tema.LARGURA - 16, 52)
    painel(tela, rect, "ferro")
    from ui.desenho import losango, desenhar_placa
    from ui.texto import linha, largura_do_texto
    from visual.cenario_macabro import nome_da_hora
    regiao = run.regiao
    total = run.areas_da_regiao()
    ato = run.nome_do_ato()
    nome = titulo or regiao.nome
    largura_placa = min(370, largura_do_texto(nome, tema.media()) + 44)
    desenhar_placa(tela, (rect.x + 10 + largura_placa // 2, rect.centery), nome, tema.media(), tema.OURO_CLARO,
                   largura_placa)
    # trilha das áreas: um losango por área, a última é o chefe; embaixo, "Ato · Área · hora"
    largura = min(420, total * 34)
    x0 = rect.centerx - largura // 2
    y_trilha = rect.y + 18
    for i in range(total):
        x = x0 + i * (largura // max(1, total - 1)) if total > 1 else rect.centerx
        area = i + 1
        cor = tema.OURO_CLARO if area == run.area else (tema.OURO_ESCURO if area < run.area else (60, 52, 64))
        if i < total - 1:
            proximo = x0 + (i + 1) * (largura // max(1, total - 1))
            pygame.draw.line(tela, (60, 52, 64) if area >= run.area else tema.OURO_ESCURO, (x, y_trilha),
                             (proximo, y_trilha), 2)
        raio = 6 if area == run.area else 4
        if area == total:
            raio += 2
            cor = tema.SANGUE_CLARO if area == run.area else (120, 40, 44)
        losango(tela, (x, y_trilha), raio, cor)
    hora = f" · {nome_da_hora(run.hora())}" if regiao.ciclo else ""
    zona = run.zona()                                   # fases com zonas (Reino dos Ratos): o nome da zona
    if zona:
        hora += f" · {zona['nome']}"
    prefixo = f"{ato} · " if ato and not titulo else ""
    ameaca = f" · Ameaça {run.ameaca}" if getattr(run, "ameaca", 0) else ""
    linha(tela, f"{prefixo}Área {run.area}/{total}{hora}{ameaca}", tema.mini(), tema.TEXTO_FRACO,
          (rect.centerx, rect.bottom - 3), 420, "midbottom")
    jogador = jogador or run.grupo.jogadores[0]
    mochila = jogador.mochila
    linha(tela, f"Ouro {jogador.ouro}", tema.normal(), tema.OURO_MOEDA, (rect.right - 290, rect.y + 17), 120, "midleft")
    linha(tela, f"Mochila {len(mochila.itens)}/{mochila.capacidade}", tema.mini(),
          tema.SANGUE_CLARO if mochila.cheia() else tema.TEXTO_FRACO, (rect.right - 290, rect.y + 39), 120, "midleft")
    linha(tela, f"Semente {run.semente}", tema.pequena(), tema.TEXTO_FRACO, (rect.right - 14, rect.centery), 150,
          "midright")
    return rect


class ArquivoDaRun:
    """Onde a run em andamento é salva: run.json na pasta do jogador (caminho = outro arquivo, nos testes)."""

    caminho = None

    @classmethod
    def onde(cls):
        return cls.caminho or CAMINHOS.save("run.json")


def salvar_run(run):
    """Salva a run (no mapa ou ao escolher um encontro; ver Run.pode_salvar). A de uma partida em grupo não vai para
    o run.json do jogo solo (não apaga a run salva de ninguém; salvar a partida pelo host é da MP8)."""
    if getattr(run, "em_rede", False):
        return
    if run is not None and not run.terminou() and run.pode_salvar():
        run.salvar(ArquivoDaRun.onde())


def carregar_run():
    from roguelike.run import Run
    return Run.carregar(ArquivoDaRun.onde())


def apagar_save_da_run():
    if os.path.exists(ArquivoDaRun.onde()):
        os.remove(ArquivoDaRun.onde())


def existe_run_salva():
    return os.path.exists(ArquivoDaRun.onde())


NOMES_DOS_TIPOS = {"material": "Material", "equipamento": "Equipamento", "consumivel": "Consumível"}
NOMES_DAS_CATEGORIAS = {"minerio": "minério", "peca_circo": "peça do circo", "alma": "alma de chefe",
                        "pocao": "poção", "comida": "comida", "bomba": "bomba", "pergaminho": "pergaminho"}


def texto_do_item(objeto):
    """Descrição completa de um item para dicas e painéis de detalhe."""
    from roguelike.golpes import golpe
    from roguelike.progresso import texto_de_modificador
    from roguelike.dados import regras
    tipo = NOMES_DOS_TIPOS.get(objeto.tipo, objeto.tipo)
    if objeto.tipo == "equipamento":
        tipo = regras()["nomes_espacos"].get(objeto.espaco, objeto.espaco)
        if getattr(objeto, "maos", 1) >= 2:
            tipo += " (duas mãos)"
        elif getattr(objeto, "leve", False):
            tipo += " (leve: vai nas duas mãos)"
    elif objeto.categoria in NOMES_DAS_CATEGORIAS:
        tipo += f" ({NOMES_DAS_CATEGORIAS[objeto.categoria]})"
    partes = [f"{tipo} · {objeto.nome_da_raridade()}"]
    if objeto.descricao:
        partes.append(objeto.descricao)
    if objeto.modificadores:
        partes.append(", ".join(texto_de_modificador(c, v) for c, v in objeto.modificadores.items()))
    if objeto.tipo == "equipamento":
        from roguelike.exemplares import todos_os_afixos
        if objeto.afixos:
            partes.append("Afixos: " + ", ".join(todos_os_afixos()[a].nome for a, _ in objeto.afixos))
        if objeto.set:
            from roguelike.sets import todos_os_sets
            conjunto = todos_os_sets().get(objeto.set)
            if conjunto:
                bonus = "; ".join(f"{b.pecas} peças: {b.descricao}" for b in conjunto.bonus)
                partes.append(f"Set {conjunto.nome} — {bonus}")
        if objeto.travada():
            partes.append("Amaldiçoado: depois de equipado só sai na próxima fogueira.")
        if getattr(objeto, "imune", None):
            from roguelike.status import dados_do_status
            partes.append("Imune a: " + ", ".join(dados_do_status(s)["nome"] for s in objeto.imune))
        from roguelike.classes import todas_as_classes
        from roguelike.racas import todas_as_racas
        classes, racas = todas_as_classes(), todas_as_racas()
        restricoes = ([f"Só {', '.join(classes[c].nome if c in classes else c for c in objeto.classes)}"]
                      if objeto.classes else []) + \
            ([f"Raças: {', '.join(racas[r].nome if r in racas else r for r in objeto.racas)}"] if objeto.racas else [])
        if restricoes:
            partes.append(" · ".join(restricoes))
    for passiva in getattr(objeto, "passivas", []):
        partes.append(f"Passiva: {passiva.get('descricao') or passiva.get('nome', '')}")
    if getattr(objeto, "ensina", None):
        ensinado = golpe(objeto.ensina)
        partes.append(f"Ensina: {ensinado.nome} — {ensinado.descricao_curta()}")
        partes.append("Leia fora do combate (menu do item no Grupo).")
    if getattr(objeto, "habilidade", None):
        h = golpe(objeto.habilidade)
        partes.append(f"Ensina: {h.nome} — {h.resumo(1)}")
    if objeto.tipo == "consumivel":
        if not objeto.descricao:
            partes.append(objeto.resumo())
        if objeto.fora_de_combate and not getattr(objeto, "ensina", None):
            partes.append("Pode ser usado fora do combate.")
    partes.append(f"Vende por {objeto.preco_de_venda()} de ouro.")
    return "\n".join(partes)


def desenhar_heroi_pequeno(tela, sprites, heroi, posicao, escala=2, apagado=False):
    """Desenha o sprite parado de um herói com os pés em 'posicao' (morto = caído)."""
    anim, quadro = ("morte", 3) if not heroi.esta_vivo() else ("parado", 0)
    imagem = sprites.quadro(heroi.sprite, anim, quadro, escala)
    ax, ay = sprites.ancora(heroi.sprite, escala)
    if apagado:
        imagem = imagem.copy()
        imagem.set_alpha(120)
    tela.blit(imagem, (posicao[0] - ax, posicao[1] - ay))


def npc_do_encontro(run):
    """Ficha do NPC do encontro atual (dados/npcs.json) com uma fala sorteada pela semente, ou None.

    Sem "nome" na ficha (treinadores), o NPC usa o nome do encontro.
    """
    import random
    from roguelike.dados import carregar
    ficha = carregar("npcs").get(run.encontro.tipo) if run.encontro else None
    if not ficha:
        return None
    sorteio = random.Random(f"{run.semente}|{run.regiao_atual}|{run.area}|fala")
    return {"nome": run.encontro.nome, **ficha, "fala": sorteio.choice(ficha["falas"])}


def desenhar_npc(tela, sprites, nome, pe, escala, tempo, espelhar=False, contorno=None, efeito=None, anim="parado",
                sombra=True):
    """Um NPC respirando (animação parada ou "sentado") com os pés em 'pe' e uma sombra no chão.

    contorno = cor do destaque (mouse/foco em cima); efeito = "silhueta" para o que ainda é segredo.
    """
    if anim not in sprites.meta(nome)["animacoes"]:
        anim = "parado"                         # folha antiga, sem a linha da animação
    if sombra:
        caixa = sprites.caixa(nome, escala)
        mancha = pygame.Surface((caixa.width + 20, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(mancha, (0, 0, 0, 110), mancha.get_rect())
        tela.blit(mancha, mancha.get_rect(center=pe))
    imagem = sprites.quadro(nome, anim, int(tempo * 4) % sprites.quadros_de(nome, anim), escala, espelhar, efeito)
    ax, ay = sprites.ancora(nome, escala, espelhar)
    posicao = (round(pe[0] - ax), round(pe[1] - ay))
    if contorno is not None:
        borda = pygame.mask.from_surface(imagem).to_surface(setcolor=(*contorno, 255), unsetcolor=(0, 0, 0, 0))
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            tela.blit(borda, (posicao[0] + dx, posicao[1] + dy))
    tela.blit(imagem, posicao)


def area_do_sprite(sprites, nome, pe, escala, espelhar=False):
    """Retângulo do corpo do sprite na tela, com os pés em 'pe' (para clicar e passar o mouse)."""
    rel = sprites.caixa(nome, escala)
    if espelhar:
        rel = pygame.Rect(-rel.right, rel.y, rel.width, rel.height)
    return rel.move(round(pe[0]), round(pe[1]))


def sprite_da_vaga(progresso, vaga):
    """Sprite composto de um herói ainda na expedição: roupa da subclasse, skins e o traço da raça."""
    from roguelike.classes import todas_as_classes
    from roguelike.racas import raca
    from roguelike.skins import nome_do_sprite
    classe = todas_as_classes()[vaga.classe]
    subclasse = classe.subclasses.get(vaga.subclasse)
    base = subclasse.sprite if subclasse is not None and subclasse.sprite else classe.sprite_da_aparencia(vaga.aparencia)
    cosmetico = raca(vaga.raca).cosmetico
    return nome_do_sprite(base, progresso.visual_da_classe(vaga.classe), [cosmetico] if cosmetico else [])


def rosto_do_sprite(sprites, nome, tamanho):
    """Recorte da cabeça e do tronco do sprite (o "retrato" de quem não tem arte de retrato), guardado."""
    chave = ("rosto", nome, tamanho)
    if chave not in sprites._cache:
        imagem = sprites.quadro(nome, "parado", 0, 1)
        caixa = imagem.get_bounding_rect()
        lado = min(caixa.width, max(18, int(caixa.height * 0.55)))
        recorte = pygame.Rect(0, 0, lado, lado)
        recorte.midtop = (caixa.centerx, caixa.top)
        recorte = recorte.clip(imagem.get_rect())
        pedaco = imagem.subsurface(recorte)
        maior = max(recorte.width, recorte.height)
        vezes = max(1, tamanho // maior)
        if maior * vezes > tamanho:
            fator = tamanho / maior
            novo = (max(1, int(recorte.width * fator)), max(1, int(recorte.height * fator)))
        else:
            novo = (recorte.width * vezes, recorte.height * vezes)
        sprites._cache[chave] = pygame.transform.scale(pedaco, novo)
    return sprites._cache[chave]


def desenhar_rosto(tela, sprites, nome, rect, estilo="espaco", apagado=False):
    """Moldurinha com o rosto do herói (apagado = caído)."""
    rect = painel(tela, rect, estilo)
    imagem = rosto_do_sprite(sprites, nome, rect.width - 12)
    if apagado:
        imagem = imagem.copy()
        imagem.set_alpha(110)
    tela.blit(imagem, imagem.get_rect(center=rect.center))
    return rect


_retratos = {}


def retrato(nome):
    """Busto de assets/retratos/<nome>.png (feito por ferramentas/sprites_macabros/gerar_retratos.py), ou None."""
    if nome not in _retratos:
        caminho = CAMINHOS.asset("retratos", nome + ".png")
        imagem = pygame.image.load(caminho) if os.path.exists(caminho) else None
        if imagem is not None and pygame.display.get_surface() is not None:
            imagem = imagem.convert_alpha()
        _retratos[nome] = imagem
    return _retratos[nome]


def desenhar_retrato(tela, nome, rect, estilo="osso", escondido=False):
    """Painel com o retrato ampliado 2x (pixels nítidos). escondido = só a silhueta escura."""
    rect = painel(tela, rect, estilo)
    imagem = retrato(nome)
    if imagem is None:
        return rect
    imagem = pygame.transform.scale(imagem, (imagem.get_width() * 2, imagem.get_height() * 2))
    if escondido:
        imagem = pygame.mask.from_surface(imagem).to_surface(setcolor=(34, 26, 42, 255), unsetcolor=(0, 0, 0, 0))
    tela.set_clip(rect.inflate(-8, -8))
    tela.blit(imagem, imagem.get_rect(center=rect.center))
    tela.set_clip(None)
    return rect


def desenhar_previa(tela, sprites, nome, rect, tempo, escala=3, estilo="osso", efeito=None):
    """Painel com o sprite animado (de vez em quando mostra o golpe). Devolve o retângulo do painel."""
    rect = painel(tela, rect, estilo)
    animacao = "ataque" if int(tempo / 2.5) % 3 == 2 and efeito is None else "parado"
    quadro = int(tempo * 5) % sprites.quadros_de(nome, animacao)
    imagem = sprites.quadro(nome, animacao, quadro, escala, False, efeito)
    ax, ay = sprites.ancora(nome, escala)
    tela.set_clip(rect.inflate(-8, -8))
    tela.blit(imagem, (rect.centerx - ax, rect.bottom - 24 - ay))
    tela.set_clip(None)
    return rect


def cabecalho(tela, titulo, extra="", direita="", cor_direita=tema.VELA):
    """Faixa do topo: título à esquerda, um texto no meio e um à direita, cada um na sua parte
    (nenhum invade o outro: diminuem a fonte ou cortam com "...")."""
    from ui.texto import linha, largura_do_texto
    from ui.desenho import desenhar_placa
    topo = painel(tela, (8, 8, tema.LARGURA - 16, 52), "ferro")
    interno = topo.inflate(-32, 0)
    largura_direita = min(interno.width // 3, largura_do_texto(direita, tema.normal())) if direita else 0
    if direita:
        linha(tela, direita, tema.normal(), cor_direita, (interno.right, topo.centery), largura_direita, "midright")
    if extra:
        meio = interno.width // 3
        linha(tela, extra, tema.pequena(), tema.TEXTO_FRACO, (topo.centerx + 60, topo.centery), meio, "center")
        largura_titulo = topo.centerx + 60 - meio // 2 - interno.x - 16
    else:
        largura_titulo = interno.width - largura_direita - 24
    # o título numa placa dourada encostada à esquerda
    largura_placa = min(largura_titulo, largura_do_texto(titulo, tema.media()) + 44)
    desenhar_placa(tela, (interno.x - 6 + largura_placa // 2, topo.centery), titulo, tema.media(), tema.OURO_CLARO,
                   largura_placa)
    return topo


def cabecalho_do_acampamento(tela, titulo, progresso, extra=""):
    """Faixa do topo das telas do acampamento: título, um texto do meio e as Brasas."""
    return cabecalho(tela, titulo, extra, f"Brasas {progresso.brasas}")


def desenhar_abas(tela_com_botoes, posicao, abas, atual, ao_trocar, largura=170, altura=44, por_linha=None):
    """Fileira de abas [(chave, rótulo)]; a atual fica marcada. ao_trocar(chave).
    por_linha: quebra em mais fileiras (ex.: as muitas regiões do bestiário)."""
    from ui.widgets import Botao
    x, y = posicao
    for i, (chave, rotulo) in enumerate(abas):
        fila, coluna = divmod(i, por_linha) if por_linha else (0, i)
        botao = Botao((x + coluna * (largura + 10), y + fila * (altura + 6), largura, altura), rotulo,
                      (lambda c=chave: ao_trocar(c)))
        botao.selecionado = chave == atual
        tela_com_botoes.botao(botao)