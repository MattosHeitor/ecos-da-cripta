"""Inventário (MP7): a mochila de um lado, o herói no meio e o baú da equipe do outro, lado a lado.

    [ buscar...  ] [Tipo: Tudo] [Espaço: Todos] [Raridade: Todas] [Ordem: Raridade] [Limpar]
    ┌── Mochila 37/50 ──┐ ┌──── retratos dos meus heróis ────┐ ┌── Baú da equipe ── Histórico ┐
    │ grade             │ │ espaços  [herói]  espaços        │ │ grade                        │
    │ [Materiais → baú] │ │ itens rápidos · sets             │ │ [← Materiais] [← Consumíveis] │
    └───────────────────┘ └──────────────────────────────────┘ └──────────────────────────────┘
    [ atributos do herói: HP, energia, ataque... com ▲▼ ao passar o mouse numa peça ]
    [Mover marcados (3)]                    mensagem                    [Fabricação] [Voltar]

A mochila é do JOGADOR (roguelike/posse.py): os heróis dele a dividem. O baú é de todos. Mover em 1 ou 2 cliques:
    arrastar e soltar     item -> espaço do boneco ou o boneco: equipa; item -> a outra grade: leva a pilha inteira;
                          peça do boneco -> uma grade: tira (na do baú, segue para o baú)
    duplo clique          equipa ou usa (Enter, no teclado)
    Shift+clique          a pilha vai para o outro lado (mochila <-> baú)
    Ctrl+clique           marca vários; Shift+clique (ou arrastar) num marcado leva todos; "Mover marcados"
    botões                todos os materiais / todos os consumíveis para o outro lado
    botão direito         menu (equipar, usar, guardar 1 ou todos, vender na loja, descartar); Delete descarta
Busca e filtros (tipo, espaço, raridade) e a ordem valem para as duas grades.

QUEM SE BENEFICIA: cada peça mostra uma seta verde e o rosto do herói (de qualquer jogador) que mais ganha com ela
(roguelike/resumo_do_heroi.beneficiados); a dica compara com o equipado de cada herói do grupo (verde melhor,
vermelho pior). Peça da minha mochila que é melhor para o herói de OUTRO jogador ganha uma borda dourada: mande ao
baú.

A mesma tela serve ao acampamento. Quem diz de onde vêm os itens é a "fonte" (padrão Strategy):
    FonteDaRun            os meus heróis da run, a minha mochila e o baú da equipe
    FonteDoAcampamento    heróis da expedição; o estande de armas (arsenal), peças emprestadas
"""

import unicodedata

import pygame

from roguelike import resumo_do_heroi as resumo
from roguelike.comandos import Equipar, Desequipar, MoverItem, Descartar, UsarItem
from roguelike.dados import regras
from roguelike.estado import BAU
from roguelike.equipamentos import nome_do_espaco
from roguelike.itens import item, existe, ordem_da_raridade
from telas.comum import (TelaComBotoes, Fundo, cabecalho_da_run, cabecalho_do_acampamento, desenhar_previa,
                         texto_do_item, desenhar_rosto, rosto_do_sprite)
from ui import tema
from ui.desenho import texto, painel, titulo_de_painel
from ui.icones import quadro_de_item, icone_item
from ui.rolagem import PainelRolavel
from ui.texto import linha, CaixaTexto
from ui.widgets import Botao, CampoDeTexto

ESQUERDA = ("cabeca", "peitoral", "calcas", "botas")
DIREITA = ("capa", "amuleto", "arma", "arma_secundaria")
TIPOS = (("tudo", "Tudo"), ("arma", "Armas"), ("armadura", "Armaduras"), ("acessorio", "Acessórios"),
         ("consumivel", "Consumíveis"), ("material", "Materiais"))
ORDENS = (("raridade", "Raridade"), ("nome", "Nome"), ("tipo", "Tipo"))
CELULA, ESPACO_ENTRE = 52, 6
DUPLO_CLIQUE = 0.35
ARRASTO_MINIMO = 6
VERDE, VERMELHO = (110, 210, 110), (230, 90, 80)
ROTULO_CURTO = {"resistencia_magica": "Res. mágica"}       # a faixa de atributos tem ~100 px por atributo
# silhueta apagada desenhada no espaço vazio (a peça "típica" de cada espaço)
SILHUETA_DO_ESPACO = {"cabeca": "elmo_de_ferro", "peitoral": "gibao_de_couro", "calcas": "calcas_de_couro",
                      "botas": "botas_gastas", "capa": "capa_de_la", "amuleto": "amuleto_de_osso",
                      "arma": "espada_enferrujada", "arma_secundaria": "escudo_de_madeira", "consumivel": "pocao_de_vida"}
_silhuetas = {}

# lugares na tela (1280x720)
BARRA = pygame.Rect(8, 66, 1264, 40)
MOCHILA = pygame.Rect(8, 112, 384, 494)
HEROI = pygame.Rect(400, 112, 480, 494)
BAU_RECT = pygame.Rect(888, 112, 384, 494)
HEROI_DO_ACAMPAMENTO = pygame.Rect(8, 112, 480, 494)
ESTANDE = pygame.Rect(496, 112, 776, 494)
ATRIBUTOS = pygame.Rect(8, 612, 1264, 52)
BOTOES_Y = 670


def silhueta(espaco, tamanho):
    """Ícone escuro e transparente da peça típica do espaço (guardado)."""
    chave = (espaco, tamanho)
    if chave not in _silhuetas:
        imagem = icone_item(item(SILHUETA_DO_ESPACO[espaco]), max(2, (tamanho - 12) // 12)).copy()
        imagem.fill((70, 64, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
        imagem.set_alpha(150)
        _silhuetas[chave] = imagem
    return _silhuetas[chave]


def tipo_da_peca(objeto):
    """Categoria do filtro: arma, armadura, acessorio, consumivel ou material."""
    return getattr(objeto, "tipo_de_peca", objeto.tipo)


def sem_acento(texto_):
    return "".join(c for c in unicodedata.normalize("NFD", texto_.lower()) if unicodedata.category(c) != "Mn")


# ============================================================
# FONTES (de onde vêm os heróis e os itens)
# ============================================================

class FonteDaRun:
    """Os meus heróis da run (no solo, todos), a minha mochila e o baú da equipe que todos dividem."""
    titulo = "Inventário"
    mostra_consumivel = True                      # o espaço de uso automático só existe na run
    tem_mochilas = True

    def __init__(self, run, loja=None):
        self.run = run
        self.loja = loja                          # aberta pela loja: dá para vender
        self.tela = None                          # a TelaInventario: é por ela que os comandos saem

    def conectar(self, tela):
        self.tela = tela

    def enviar(self, comando):
        return self.tela.enviar(comando)

    def numero(self, heroi):
        return self.tela.indice_do(heroi)

    def lugar(self, inventario):
        """"bau" ou o número do herói dono da mochila (como os comandos falam do lugar de um item)."""
        return self.tela.sessao().estado.origem_de(inventario)

    @property
    def grupo(self):
        return self.run.grupo

    def todos_os_herois(self):
        """Todos os heróis do grupo (de todos os jogadores): o indicador de quem se beneficia olha todos."""
        return self.grupo.herois

    def herois(self):
        """Os heróis que eu comando (em grupo, só os meus; no solo, todos)."""
        meu = self.tela.meu_jogador() if self.tela is not None else None
        meus = [h for h in self.grupo.herois if meu is None or getattr(h, "jogador", None) == meu]
        return meus or self.grupo.herois

    def grades(self, heroi):
        """[(lado, título, inventário)] das grades: a mochila (do jogador do herói) e o baú."""
        mochila = heroi.inventario
        return [("mochila", f"Mochila {len(mochila.itens)}/{mochila.capacidade}", mochila),
                ("bau", f"Baú da equipe ({sum(self.grupo.bau.itens.values())})", self.grupo.bau)]

    def livres(self, chave, quantidade):
        return quantidade

    def equipar(self, heroi, chave, espaco=None, origem=None):
        """Duplo clique num item: equipa a peça, usa o consumível (fora do combate) ou o deixa no uso automático.
        Devolve (mensagem, deu_certo). Quem decide se pode são os comandos (roguelike/comandos.py)."""
        objeto = item(chave)
        origem = origem if origem is not None else heroi.inventario
        numero, lugar = self.numero(heroi), self.lugar(origem)
        if objeto.tipo == "material":
            return "Materiais servem para fabricar.", False
        if objeto.tipo == "consumivel" and objeto.fora_de_combate:
            resultado = self.enviar(UsarItem(heroi=numero, chave=chave, origem=lugar))
            return resultado.mensagem, resultado.ok
        if objeto.tipo == "consumivel" and origem is not heroi.inventario:      # o uso automático sai da mochila dele
            if not self.enviar(MoverItem(chave=chave, de=BAU, para=numero, quantidade=origem.quantidade(chave))):
                return "A mochila está cheia.", False
            lugar = numero
        resultado = self.enviar(Equipar(heroi=numero, chave=chave, origem=lugar, espaco=espaco))
        return resultado.mensagem, resultado.ok

    def desequipar(self, heroi, espaco):
        resultado = self.enviar(Desequipar(heroi=self.numero(heroi), espaco=espaco))
        return resultado.mensagem, resultado.ok

    def mover(self, chave, de, para, quantidade=1):
        """Leva itens entre o baú ("bau") e a mochila (de um herói). Devolve (mensagem, deu_certo)."""
        if de == para:
            return "", False
        resultado = self.enviar(MoverItem(chave=chave, de=BAU if de == BAU else self.numero(de),
                                          para=BAU if para == BAU else self.numero(para), quantidade=quantidade))
        return resultado.mensagem, resultado.ok

    def descartar(self, heroi, chave, origem=None):
        origem = origem if origem is not None else heroi.inventario
        return self.enviar(Descartar(origem=self.lugar(origem), chave=chave)).ok


class FonteDoAcampamento:
    """Heróis da expedição e o estande de armas (o arsenal: só o que foi ganho depois de runs)."""
    titulo = "Arsenal"
    mostra_consumivel = False
    tem_mochilas = False
    loja = None

    def __init__(self, progresso):
        self.progresso = progresso
        self.expedicao = progresso.expedicao_atual()
        self.expedicao.validar(progresso)
        self._herois = None

    @property
    def arsenal(self):
        return self.progresso.arsenal

    def herois(self):
        """Os heróis como vão partir (raça, talentos, skins e as peças escolhidas)."""
        if self._herois is None:
            herois = self.expedicao.criar_herois(self.progresso)
            for heroi, vaga in zip(herois, self.expedicao.vagas):
                self.progresso.preparar_heroi(heroi, len(herois))
                for espaco, chave in vaga.equipamento.items():
                    if existe(chave):
                        heroi.equipar(item(chave), espaco)
                heroi.equipamentos.liberar_malditos()          # no acampamento nada fica preso
                heroi.curar_tudo()
            self._herois = herois
        return self._herois

    def todos_os_herois(self):
        return self.herois()

    def mudou(self):
        self._herois = None
        self.progresso.salvar()

    def vaga_de(self, heroi):
        return self.expedicao.vagas[self.herois().index(heroi)]

    def grades(self, heroi):
        return [("arsenal", f"Estande de armas ({self.arsenal.total()}/{self.arsenal.capacidade()})", self.arsenal)]

    def livres(self, chave, quantidade):
        return quantidade - self.expedicao.em_uso(chave)

    def equipar(self, heroi, chave, espaco=None, origem=None):
        motivo = self.expedicao.escolher_peca(self.vaga_de(heroi), chave, self.arsenal, espaco)
        if motivo:
            return motivo, False
        nome = heroi.nome
        self.mudou()
        return f"{item(chave).nome} vai com {nome}.", True

    def desequipar(self, heroi, espaco):
        chave = self.vaga_de(heroi).equipamento.pop(espaco, None)
        if chave is None:
            return "Nada para tirar.", False
        self.mudou()
        return f"{item(chave).nome} voltou ao estande.", True

    def mover(self, chave, de, para, quantidade=1):
        return "", False

    def descartar(self, heroi, chave, origem=None):
        if not self.arsenal.remover(chave):
            return False
        self.expedicao.validar_equipamento(self.arsenal)
        self.mudou()
        return True


# ============================================================
# TELA
# ============================================================

class TelaInventario(TelaComBotoes):
    PAGINAS_ROLAM = False                         # PageUp/PageDown trocam de herói (como Q/E)

    def __init__(self, app, fonte, ao_voltar, run=None, indice=0, aba=None, ao_fabricar=None):
        super().__init__(app)
        self.fonte = fonte
        if hasattr(fonte, "conectar"):              # a FonteDaRun manda os comandos por esta tela
            fonte.conectar(self)
        self.ao_voltar = ao_voltar
        self.ao_fabricar = ao_fabricar
        self.run = run
        self.fundo = Fundo.da_run(run, escurecer=170) if run is not None else Fundo("acampamento", escurecer=160)
        herois = fonte.herois()
        if run is not None and indice < len(run.grupo.herois) and run.grupo.herois[indice] in herois:
            self.indice = herois.index(run.grupo.herois[indice])          # (o índice vem do grupo inteiro)
        else:
            self.indice = 0
        # ('aba' era a grade aberta, até a MP6; agora as duas ficam lado a lado e o parâmetro só fica por compatibilidade)
        self.filtros = {"tipo": "tudo", "espaco": "todos", "raridade": "todas"}
        self.ordem = "raridade"
        self.campo_busca = CampoDeTexto((BARRA.x, BARRA.y, 250, BARRA.height), "", maximo=20, dica="Buscar item...")
        self.mensagem = None                      # (texto, cor, quando)
        self.selecionado = None                   # alvo escolhido (mouse ou teclado)
        self.marcados = set()                     # (lado, chave) marcados com Ctrl+clique
        self.em_cima = None                       # alvo sob o mouse (ou o foco do teclado)
        self.pressionado = None                   # (alvo, posição) do botão do mouse apertado
        self.arrastando = None
        self.ultimo_clique = (None, -10.0)
        self.areas = []                           # [(rect, alvo)] desenhados neste quadro
        self.rolagens = {}                        # lado -> PainelRolavel
        self._beneficio = {}                      # (chave da peça, assinatura do grupo) -> beneficiados
        self._assinatura = None

    def musica(self):
        return self.run.musica() if self.run is not None else "acampamento"

    @property
    def heroi(self):
        herois = self.fonte.herois()
        self.indice = min(self.indice, len(herois) - 1)
        return herois[self.indice]

    def voltar(self):
        self.ao_voltar()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    # ---------------- de onde é cada item ----------------
    def inventario_do_lado(self, lado):
        return next(inventario for chave, _, inventario in self.fonte.grades(self.heroi) if chave == lado)

    def dono_e_origem(self, alvo):
        """(herói, inventário) de onde o item do alvo está: o herói atual e a mochila dele, ou (None, baú/estande)."""
        tipo = alvo[0]
        if tipo == "item":
            lado = alvo[1]
            return (self.heroi if lado == "mochila" else None), self.inventario_do_lado(lado)
        if tipo == "rapido":
            return self.heroi, self.heroi.inventario
        return self.heroi, None

    @staticmethod
    def chave_do(alvo):
        return alvo[-1] if alvo and alvo[0] in ("item", "rapido") else None

    @staticmethod
    def lado_do(alvo):
        """De que grade é o item ("mochila", "bau", "arsenal"); os rápidos são da mochila."""
        if alvo[0] == "item":
            return alvo[1]
        return "mochila" if alvo[0] == "rapido" else None

    # ---------------- ações ----------------
    def avisar(self, mensagem, deu_certo=True):
        if mensagem:
            self.mensagem = (mensagem, tema.CURA if deu_certo else tema.SANGUE_CLARO, self.tempo)
            self.app.audio.tocar("item" if deu_certo else "voltar")

    def trocar_heroi(self, passo):
        self.indice = (self.indice + passo) % len(self.fonte.herois())
        self.selecionado = None

    def equipar(self, chave, espaco=None, heroi=None, origem=None):
        heroi = heroi or self.heroi
        if origem is None:                        # sem dizer de onde: a mochila e depois o baú (ou o estande)
            origem = next((inv for _, _, inv in self.fonte.grades(heroi) if inv.quantidade(chave) > 0), None)
        mensagem, ok = self.fonte.equipar(heroi, chave, espaco, origem)
        self.avisar(mensagem, ok)
        if ok:
            self.selecionado = None

    def desequipar(self, espaco):
        mensagem, ok = self.fonte.desequipar(self.heroi, espaco)
        self.avisar(mensagem, ok)

    def mover(self, chave, de, para, quantidade=1):
        mensagem, ok = self.fonte.mover(chave, de, para, quantidade)
        self.avisar(mensagem, ok)
        return ok

    def mover_pilha(self, lado, chave):
        """A pilha inteira para o outro lado (mochila -> baú ou baú -> mochila). Devolve se deu certo."""
        inventario = self.inventario_do_lado(lado)
        quantidade = inventario.quantidade(chave)
        if quantidade <= 0 or not self.fonte.tem_mochilas:
            return False
        if lado == "mochila":
            return self.mover(chave, self.heroi, "bau", quantidade)
        return self.mover(chave, "bau", self.heroi, quantidade)

    def mover_marcados(self, lado=None):
        """Todos os marcados (de 'lado', ou dos dois) para o outro lado."""
        movidos = 0
        for lado_do_item, chave in sorted(self.marcados):
            if lado is None or lado_do_item == lado:
                movidos += bool(self.mover_pilha(lado_do_item, chave))
        self.marcados = {m for m in self.marcados if lado is not None and m[0] != lado}
        if movidos > 1:
            self.avisar(f"{movidos} pilhas movidas.")

    def mover_todos(self, lado, tipo):
        """Todos os materiais (ou consumíveis) de uma grade para a outra."""
        pilhas = [o.chave for o, _ in self.inventario_do_lado(lado).pilhas(tipo)]
        movidos = sum(1 for chave in pilhas if self.mover_pilha(lado, chave))
        nome = "materiais" if tipo == "material" else "consumíveis"
        if not pilhas:
            self.avisar(f"Não há {nome} aí.", False)
        elif movidos:
            destino = "o baú" if lado == "mochila" else "a mochila"
            self.avisar(f"{movidos} pilha(s) de {nome} para {destino}.")

    def para_o_outro_lado(self, alvo):
        """Shift+clique: a pilha vai para o outro lado; num item marcado, vão todos os marcados."""
        chave, lado = self.chave_do(alvo), self.lado_do(alvo)
        if chave is None or not self.fonte.tem_mochilas or lado not in ("mochila", "bau"):
            return
        if (lado, chave) in self.marcados:
            self.mover_marcados()
        else:
            self.mover_pilha(lado, chave)
        self.selecionado = None

    def marcar(self, alvo):
        """Ctrl+clique: marca/desmarca (para mover vários de uma vez)."""
        chave, lado = self.chave_do(alvo), self.lado_do(alvo)
        if chave is None or lado not in ("mochila", "bau"):
            return
        self.marcados ^= {(lado, chave)}
        self.app.audio.tocar("navegar")

    def ativar(self, alvo):
        """Enter ou duplo clique: equipa/usa o item (no herói atual) ou tira a peça do espaço."""
        tipo = alvo[0]
        if tipo == "espaco":
            if self.heroi.equipamento.get(alvo[1]) is not None:
                self.desequipar(alvo[1])
            return
        if tipo == "retrato":
            self.indice = alvo[1]
            return
        chave = self.chave_do(alvo)
        if chave is None:
            return
        _, origem = self.dono_e_origem(alvo)
        self.equipar(chave, origem=origem)

    def perguntar_descarte(self, chave, origem=None):
        objeto = item(chave)
        aviso = " O estande perde a peça para sempre." if isinstance(self.fonte, FonteDoAcampamento) else ""
        self.abrir_dialogo("Descartar", f"Jogar fora {objeto.nome}? Não dá para desfazer.{aviso}",
                           [("Descartar", lambda: self.descartar(chave, origem)), ("Cancelar", None)])

    def descartar(self, chave, origem=None):
        if origem is None:                        # sem dizer de onde: a mochila e depois o baú (ou o estande)
            origem = next((inv for _, _, inv in self.fonte.grades(self.heroi) if inv.quantidade(chave) > 0), None)
        nome = item(chave).nome
        if self.fonte.descartar(self.heroi, chave, origem):
            self.avisar(f"{nome} foi descartado.", True)
            self.selecionado = None

    def vender(self, chave, origem):
        """Pergunta antes (vender 1 ou a pilha toda) — vender não tem volta."""
        from telas.comum import confirmar_venda

        def vendido(ganho):
            self.avisar(f"Vendeu {item(chave).nome} por {ganho} de ouro." if ganho else "Não deu para vender.",
                        bool(ganho))
        confirmar_venda(self, origem, chave, vendido)

    def menu_de_acoes(self, alvo):
        """Botão direito: o que dá para fazer com o item (equipar, usar, guardar, pegar, vender, descartar)."""
        chave = self.chave_do(alvo)
        if chave is None:
            return
        objeto = item(chave)
        dono, origem = self.dono_e_origem(alvo)
        quem = self.heroi
        lado = self.lado_do(alvo)
        opcoes = []
        if objeto.tipo == "equipamento":
            opcoes.append((f"Equipar em {quem.nome}", lambda: self.equipar(chave, heroi=quem, origem=origem)))
        elif objeto.tipo == "consumivel":
            opcoes.append((f"Usar ({quem.nome})", lambda: self.equipar(chave, heroi=quem, origem=origem)))
        if self.fonte.tem_mochilas and lado in ("mochila", "bau"):
            quantidade = origem.quantidade(chave)
            para = "baú" if lado == "mochila" else "a mochila"
            if lado == "mochila":
                opcoes.append(("Guardar 1 no baú", lambda: self.mover(chave, quem, "bau")))
            else:
                opcoes.append(("Pegar 1 para a mochila", lambda: self.mover(chave, "bau", quem)))
            if quantidade > 1:
                opcoes.append((f"Todos x{quantidade} para {para}", lambda: self.mover_pilha(lado, chave)))
        if self.fonte.loja is not None and origem is not None:
            opcoes.append((f"Vender (+{objeto.preco_de_venda()} ouro)", lambda: self.vender(chave, origem)))
        opcoes.append(("Descartar...", lambda: self.perguntar_descarte(chave, origem)))
        opcoes.append(("Cancelar", None))
        self.abrir_dialogo(objeto.nome, "", opcoes)

    def mostrar_historico(self, quantos=7):
        """Os últimos movimentos do baú da equipe: "Você (Doran) guardou Osso x2"."""
        linhas = []
        for movimento in reversed(self.fonte.grupo.bau.registro[-quantos:]):
            quem = movimento.jogador.nome + (f" ({movimento.heroi})" if movimento.heroi else "")
            acao = "guardou" if movimento.acao == "colocar" else "pegou"
            nome = item(movimento.chave).nome if existe(movimento.chave) else movimento.chave
            linhas.append(f"{quem} {acao} {nome}" + (f" x{movimento.quantidade}" if movimento.quantidade > 1 else ""))
        self.abrir_dialogo("Histórico do baú", "\n".join(linhas) or "Ninguém mexeu no baú ainda.", [("Fechar", None)])

    # ---------------- filtros e ordem ----------------
    def proximo(self, filtro, opcoes):
        valores = [v for v, _ in opcoes]
        self.filtros[filtro] = valores[(valores.index(self.filtros[filtro]) + 1) % len(valores)]
        self.app.audio.tocar("navegar")

    def opcoes_de_espaco(self):
        nomes = regras()["nomes_espacos"]
        return [("todos", "Todos")] + [(e, nomes[e]) for e in ESQUERDA + DIREITA]

    def opcoes_de_raridade(self):
        return [("todas", "Todas")] + [(r, d.get("nome", r)) for r, d in regras()["raridades"].items()]

    def trocar_ordem(self):
        chaves = [c for c, _ in ORDENS]
        self.ordem = chaves[(chaves.index(self.ordem) + 1) % len(chaves)]

    def limpar_filtros(self):
        self.filtros = {"tipo": "tudo", "espaco": "todos", "raridade": "todas"}
        self.campo_busca.conteudo = ""
        self.ordem = "raridade"

    def passa_nos_filtros(self, peca):
        filtros = self.filtros
        if filtros["tipo"] != "tudo" and tipo_da_peca(peca) != filtros["tipo"]:
            return False
        if filtros["espaco"] != "todos" and (peca.tipo != "equipamento" or filtros["espaco"] not in peca.espacos_possiveis()):
            return False
        if filtros["raridade"] != "todas" and peca.raridade != filtros["raridade"]:
            return False
        busca = sem_acento(self.campo_busca.conteudo.strip())
        return not busca or busca in sem_acento(peca.nome)

    def itens_visiveis(self, inventario):
        pilhas = [(p, n) for p, n in inventario.pilhas() if self.passa_nos_filtros(p)]
        if self.ordem == "nome":
            pilhas.sort(key=lambda par: par[0].nome)
        elif self.ordem == "tipo":
            pilhas.sort(key=lambda par: (tipo_da_peca(par[0]), -ordem_da_raridade(par[0].raridade)))
        else:
            pilhas.sort(key=lambda par: (-ordem_da_raridade(par[0].raridade), par[0].nome))
        return pilhas

    # ---------------- quem se beneficia ----------------
    def assinatura_do_grupo(self):
        """Muda quando o equipamento, o nível ou os atributos de alguém mudam (aí a conta é refeita)."""
        return tuple((id(h), h.nivel, tuple(sorted(h.atributos.para_dict().items())),
                      tuple((e, p.chave if p else None) for e, p in sorted(h.equipamentos.espacos.items())))
                     for h in self.fonte.todos_os_herois())

    def beneficiados(self, peca):
        """[(herói, nota, diferenças)] de quem fica melhor com a peça (guardado até o grupo mudar)."""
        chave = (peca.chave, self._assinatura)
        if chave not in self._beneficio:
            if len(self._beneficio) > 4000:
                self._beneficio.clear()
            self._beneficio[chave] = resumo.beneficiados(peca, self.fonte.todos_os_herois())
        return self._beneficio[chave]

    def eh_meu(self, heroi):
        return heroi in self.fonte.herois()

    def so_para_outros(self, peca):
        """A peça melhora alguém, mas nenhum dos MEUS heróis (em grupo: mande ao baú)."""
        lista = self.beneficiados(peca)
        return bool(lista) and not any(self.eh_meu(h) for h, _, _ in lista)

    def dono_de(self, heroi):
        jogador = getattr(heroi, "jogador", None)
        return jogador.nome if jogador is not None and self.run is not None and len(self.run.grupo.jogadores) > 1 else None

    def desenhar_beneficio(self, tela, caixa, peca, lado):
        """A seta verde e o rosto de quem mais ganha com a peça; borda dourada se for melhor para o herói de outro
        jogador e estiver na minha mochila (mande ao baú)."""
        lista = self.beneficiados(peca)
        if not lista:
            return
        melhor = lista[0][0]
        pygame.draw.polygon(tela, VERDE, [(caixa.x + 4, caixa.y + 13), (caixa.x + 10, caixa.y + 4), (caixa.x + 16, caixa.y + 13)])
        pygame.draw.polygon(tela, (20, 40, 20), [(caixa.x + 4, caixa.y + 13), (caixa.x + 10, caixa.y + 4),
                                                 (caixa.x + 16, caixa.y + 13)], 1)
        rosto = rosto_do_sprite(self.app.sprites, melhor.sprite, 18)
        moldura = pygame.Rect(caixa.right - 22, caixa.y + 2, 20, 20)
        pygame.draw.rect(tela, (16, 10, 14), moldura)
        tela.blit(rosto, rosto.get_rect(center=moldura.center))
        dono = getattr(melhor, "jogador", None)
        cor = dono.cor if dono is not None and dono.cor and self.dono_de(melhor) else tema.OURO
        pygame.draw.rect(tela, cor, moldura, 1)
        if lado == "mochila" and self.so_para_outros(peca):
            borda = 2 if int(self.tempo * 2) % 2 == 0 else 1
            pygame.draw.rect(tela, tema.OURO_CLARO, caixa.inflate(4, 4), borda)

    def trechos_do_beneficio(self, peca):
        """Na dica: para cada herói do grupo, o que melhora (verde) ou piora (vermelho) se trocar pela peça."""
        nomes = resumo.nomes_dos_atributos()
        trechos = []
        for heroi in self.fonte.todos_os_herois()[:6]:
            troca = resumo.melhor_troca(heroi, peca)
            dono = self.dono_de(heroi)
            quem = heroi.nome + (f" ({dono})" if dono else "")
            if troca is None:
                trechos.append((f"· {quem}: não usa", tema.TEXTO_APAGADO))
                continue
            nota, _, diferencas = troca
            partes = [f"{nomes[c]} {resumo.formatar_diferenca(c, d)}" for c, d in
                      sorted(diferencas.items(), key=lambda par: -abs(par[1] * resumo.pesos_do_heroi(heroi).get(par[0], 0)))][:4]
            if nota > regras()["beneficio_de_pecas"]["minimo"]:
                trechos.append((f"▲ {quem}: " + (", ".join(partes) or "melhor"), VERDE))
            elif nota < -regras()["beneficio_de_pecas"]["minimo"]:
                trechos.append((f"▼ {quem}: " + (", ".join(partes) or "pior"), VERMELHO))
            else:
                trechos.append((f"= {quem}: quase igual", tema.TEXTO_FRACO))
        return trechos

    def dica_do_item(self, peca, heroi, lado="mochila"):
        """Texto do item + a comparação com o equipado de cada herói do grupo (verde melhor, vermelho pior)."""
        trechos = [(texto_do_item(peca), tema.TEXTO)]
        if peca.tipo == "equipamento":
            trechos += self.trechos_do_beneficio(peca)
            trechos.append(("Duplo clique ou arraste para equipar. Botão direito: mais ações.", tema.TEXTO_FRACO))
        elif peca.tipo == "consumivel":
            trechos.append(("Duplo clique: usar agora (ou deixar no uso automático). Botão direito: mais ações.",
                            tema.TEXTO_FRACO))
        if self.fonte.tem_mochilas and lado in ("mochila", "bau"):
            trechos.append(("Shift+clique: a pilha vai para o baú." if lado == "mochila" else
                            "Shift+clique: a pilha vai para a mochila.", tema.TEXTO_FRACO))
        return trechos

    # ---------------- mouse: duplo clique e arrastar ----------------
    def alvo_em(self, posicao):
        return next((alvo for rect, alvo in reversed(self.areas) if rect.collidepoint(posicao)), None)

    def evento(self, e):
        if self.dialogo is None and self.campo_busca.evento(e) and e.type in (pygame.KEYDOWN, pygame.TEXTINPUT):
            return
        if self.dialogo is None:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                alvo = self.alvo_em(e.pos)
                teclas = pygame.key.get_mods()
                if alvo is not None and alvo[0] in ("item", "rapido") and teclas & pygame.KMOD_CTRL:
                    self.mouse, self.usando_teclado = e.pos, False
                    self.marcar(alvo)
                    return
                if alvo is not None and alvo[0] in ("item", "rapido") and teclas & pygame.KMOD_SHIFT:
                    self.mouse, self.usando_teclado = e.pos, False
                    self.para_o_outro_lado(alvo)
                    return
                if alvo is not None and alvo[0] in ("item", "espaco", "rapido"):
                    self.mouse, self.usando_teclado = e.pos, False
                    self.apertar(alvo, e.pos)
                    return
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
                alvo = self.alvo_em(e.pos)
                if alvo is not None and self.chave_do(alvo) is not None:
                    self.menu_de_acoes(alvo)
                    return
            elif e.type == pygame.MOUSEMOTION and self.pressionado is not None:
                origem = self.pressionado[1]
                if abs(e.pos[0] - origem[0]) + abs(e.pos[1] - origem[1]) > ARRASTO_MINIMO:
                    self.arrastando = self.pressionado[0]
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.pressionado is not None:
                self.soltar(e.pos)
                return
        super().evento(e)

    def apertar(self, alvo, posicao):
        anterior, quando = self.ultimo_clique
        if anterior == alvo and self.tempo - quando < DUPLO_CLIQUE:
            self.ultimo_clique = (None, -10.0)
            self.ativar(alvo)
            return
        self.ultimo_clique = (alvo, self.tempo)
        self.selecionado = alvo
        self.pressionado = (alvo, posicao)

    def soltar(self, posicao):
        """Solta o que estava sendo arrastado (veja as regras no começo do arquivo)."""
        arrastado, self.arrastando, self.pressionado = self.arrastando, None, None
        if arrastado is None:
            return
        destino = self.alvo_em(posicao)
        if destino is None:
            return
        tipo, alvo = arrastado[0], destino[0]
        lado_destino = destino[1] if alvo in ("grade", "item") else None
        if tipo == "espaco":
            if lado_destino is not None:
                espaco = arrastado[1]
                peca = self.heroi.equipamento.get(espaco)
                self.desequipar(espaco)
                if peca is not None and lado_destino == "bau" and self.heroi.inventario.tem(peca.chave):
                    self.mover(peca.chave, self.heroi, "bau")
            return
        chave, lado = self.chave_do(arrastado), self.lado_do(arrastado)
        _, origem = self.dono_e_origem(arrastado)
        if alvo in ("espaco", "boneco"):
            self.equipar(chave, destino[1] if alvo == "espaco" else None, origem=origem)
        elif self.fonte.tem_mochilas and lado_destino in ("mochila", "bau") and lado_destino != lado:
            if (lado, chave) in self.marcados:
                self.mover_marcados(lado)
            else:
                self.mover_pilha(lado, chave)

    # ---------------- teclado ----------------
    def tecla(self, e):
        if e.key in (pygame.K_q, pygame.K_PAGEUP):
            self.trocar_heroi(-1)
        elif e.key in (pygame.K_e, pygame.K_PAGEDOWN):
            self.trocar_heroi(1)
        elif e.unicode and e.unicode.isdigit() and 1 <= int(e.unicode) <= len(self.fonte.herois()):
            self.indice = int(e.unicode) - 1
        elif e.key in (pygame.K_DELETE, pygame.K_x):
            alvo = self.alvo_do_foco() or self.selecionado
            if alvo is not None and self.chave_do(alvo) is not None:
                self.perguntar_descarte(self.chave_do(alvo), self.dono_e_origem(alvo)[1])
        elif self.controles.eh(e, "fabricar") and self.ao_fabricar is not None:
            self.ao_fabricar(self.indice_no_grupo())

    def indice_no_grupo(self):
        """O número do herói atual no grupo inteiro (a lista daqui, em grupo, tem só os meus)."""
        if self.run is None:
            return self.indice
        return self.run.grupo.herois.index(self.heroi)

    def alvo_do_foco(self):
        return getattr(self._botao_focado(), "alvo", None)

    # ============================================================
    # DESENHO
    # ============================================================
    def registrar(self, rect, alvo):
        """Área de mouse (e botão focável para o teclado: Enter ativa)."""
        rect = pygame.Rect(rect)
        botao = Botao(rect, "", (lambda a=alvo: self.ativar(a)))
        botao.alvo = alvo
        if self._abertos:                                 # dentro de painel rolável: só a parte visível responde
            painel_aberto = self._abertos[-1]
            botao.painel, botao.recorte = painel_aberto, painel_aberto.rect
            botao.chave_foco = (id(painel_aberto), rect.x, rect.y + round(painel_aberto.deslocamento), rect.width,
                                rect.height)
            rect = rect.clip(painel_aberto.rect)
        self.areas.append((rect, alvo))
        self.botoes.append(botao)
        if self.foco == botao.chave_foco and self.usando_teclado:
            self._foco_achado = True
            pygame.draw.rect(self.tela_atual, tema.OURO_CLARO, rect.inflate(6, 6), 2)
        if (not self.usando_teclado and rect.collidepoint(self.mouse)) or (self.usando_teclado and self.foco == botao.chave_foco):
            self.em_cima = alvo

    def realcar_destino(self, tela, rect, tipos, lado=None):
        """Contorno dourado onde o item arrastado pode cair."""
        if not self.arrastando or not pygame.Rect(rect).collidepoint(self.mouse) or self.arrastando[0] not in tipos:
            return
        if lado is not None and self.lado_do(self.arrastando) == lado:
            return
        pygame.draw.rect(tela, tema.OURO_CLARO, pygame.Rect(rect).inflate(6, 6), 2)

    # ---------------- barra de busca e filtros ----------------
    def desenhar_barra(self, tela):
        self.campo_busca.desenhar(tela, self.mouse, self.tempo, tema.pequena())
        x = self.campo_busca.rect.right + 8
        rotulos = [
            (f"Tipo: {dict(TIPOS)[self.filtros['tipo']]}", 168, lambda: self.proximo("tipo", TIPOS)),
            (f"Espaço: {dict(self.opcoes_de_espaco())[self.filtros['espaco']]}", 186,
             lambda: self.proximo("espaco", self.opcoes_de_espaco())),
            (f"Raridade: {dict(self.opcoes_de_raridade())[self.filtros['raridade']]}", 180,
             lambda: self.proximo("raridade", self.opcoes_de_raridade())),
            (f"Ordem: {dict(ORDENS)[self.ordem]}", 160, self.trocar_ordem),
            ("Limpar", 78, self.limpar_filtros),
        ]
        for rotulo, largura, acao in rotulos:
            self.botao(Botao((x, BARRA.y, largura, BARRA.height), rotulo, acao, estilo="pedra"))
            x += largura + 8
        linha(tela, "▲ + rosto: melhor para quem", tema.mini(), tema.TEXTO_FRACO,
              (BARRA.right, BARRA.centery), BARRA.right - x, "midright")

    # ---------------- grades (mochila / baú / estande) ----------------
    def desenhar_grade(self, tela, rect, lado, titulo, inventario):
        painel(tela, rect, "ferro")
        topo = titulo_de_painel(tela, rect, titulo)
        com_botoes = self.fonte.tem_mochilas
        baixo = rect.bottom - (58 if com_botoes else 14)
        grade = pygame.Rect(rect.x + 14, topo + 2, rect.width - 28, baixo - topo - 2)
        if lado == "mochila" and inventario.cheia():             # cheia: avisa o que acontece com o resto
            aviso = pygame.Rect(grade.x, grade.bottom - 26, grade.width, 26)
            linha(tela, "Cheia: o que chegar vai para o baú.", tema.mini(), tema.SANGUE_CLARO, aviso.center,
                  aviso.width, "center")
            grade.height -= 30
        self.areas.append((grade, ("grade", lado)))
        self.realcar_destino(tela, grade, ("item", "espaco", "rapido"), lado)
        pilhas = self.itens_visiveis(inventario)
        if not pilhas:
            CaixaTexto(grade.inflate(-30, -80), tema.pequena(), tema.TEXTO_FRACO, alinhamento="centro",
                       vertical="meio").desenhar(tela, self.texto_vazio(lado, inventario))
        else:
            passo = CELULA + ESPACO_ENTRE
            colunas = max(1, (grade.width + ESPACO_ENTRE) // passo)
            total = ((len(pilhas) + colunas - 1) // colunas) * passo
            colunas = max(1, (PainelRolavel.largura_util(grade, total) + ESPACO_ENTRE) // passo)
            total = ((len(pilhas) + colunas - 1) // colunas) * passo
            rolagem = self.rolagens.setdefault(lado, PainelRolavel(passo=passo))
            with self.rolavel(rolagem, grade, total) as y0:
                for i, (peca, quantidade) in enumerate(pilhas):
                    fila, coluna = divmod(i, colunas)
                    self.desenhar_celula(tela, (grade.x + coluna * passo, y0 + fila * passo), lado, peca, quantidade)
        if com_botoes:
            largura = (rect.width - 28 - 8) // 2
            y = rect.bottom - 50
            if lado == "mochila":
                rotulos = (("Materiais → baú", "material"), ("Consumíveis → baú", "consumivel"))
            else:
                rotulos = (("← Materiais", "material"), ("← Consumíveis", "consumivel"))
            for i, (rotulo, tipo) in enumerate(rotulos):
                destino = "o baú" if lado == "mochila" else "a mochila"
                self.botao(Botao((rect.x + 14 + i * (largura + 8), y, largura, 38), rotulo,
                                 (lambda t=tipo: self.mover_todos(lado, t)), estilo="pedra",
                                 dica=("Mover tudo", f"Leva todas as pilhas desse tipo para {destino}.")))

    def desenhar_celula(self, tela, posicao, lado, peca, quantidade):
        alvo = ("item", lado, peca.chave)
        livres = self.fonte.livres(peca.chave, quantidade)
        caixa = quadro_de_item(tela, peca, posicao, CELULA, quantidade if quantidade > 1 else None,
                               selecionado=self.selecionado == alvo)
        if livres <= 0:
            escuro = pygame.Surface(caixa.size, pygame.SRCALPHA)
            escuro.fill((0, 0, 0, 150))
            tela.blit(escuro, caixa)
            texto(tela, "em uso", tema.mini(), tema.TEXTO_APAGADO, (caixa.centerx, caixa.bottom - 2), "midbottom")
        if peca.tipo == "equipamento" and peca.travada():
            pygame.draw.rect(tela, tema.COR_RARIDADE["amaldicoado"], caixa.inflate(2, 2), 1)
        self.desenhar_beneficio(tela, caixa, peca, lado)
        if (lado, peca.chave) in self.marcados:                 # marcado (Ctrl+clique)
            pygame.draw.rect(tela, tema.OURO_CLARO, caixa.inflate(2, 2), 3)
            pygame.draw.circle(tela, tema.OURO_CLARO, (caixa.x + 6, caixa.bottom - 7), 5)
        self.registrar(caixa, alvo)
        if self.em_cima == alvo and not self.arrastando:
            self.dica = (peca.nome, self.dica_do_item(peca, self.heroi, lado))

    def texto_vazio(self, lado, inventario):
        if lado == "arsenal" and not inventario.pilhas():
            return ("O estande está vazio. Vença uma run (ou fuja derrotando o guardião da saída) para guardar "
                    "aqui os equipamentos conquistados.")
        if inventario.pilhas():
            return "Nada aqui com estes filtros."
        if lado == "mochila":
            return "A mochila está vazia. O que você ganha cai aqui (se estiver cheia, no baú da equipe)."
        return "O baú da equipe está vazio. Shift+clique num item da mochila (ou arraste até aqui) para dividir com todos."

    # ---------------- o herói (meio) ----------------
    def desenhar_espaco(self, tela, espaco, posicao, tamanho=60):
        heroi = self.heroi
        peca = heroi.equipamento.get(espaco)
        rect = pygame.Rect(posicao[0], posicao[1], tamanho, tamanho)
        if peca is None:
            painel(tela, rect, "espaco")
            imagem = silhueta(espaco, tamanho)
            tela.blit(imagem, imagem.get_rect(center=rect.center))
        else:
            quadro_de_item(tela, peca, rect.topleft, tamanho, selecionado=self.selecionado == ("espaco", espaco))
            if espaco in heroi.equipamentos.travados:
                pygame.draw.rect(tela, tema.COR_RARIDADE["amaldicoado"], rect.inflate(4, 4), 2)
        self.realcar_destino(tela, rect, ("item", "rapido"))
        self.registrar(rect, ("espaco", espaco))
        if self.em_cima == ("espaco", espaco) and not self.arrastando:
            if peca is None:
                self.dica = (nome_do_espaco(espaco), "Vazio. Arraste uma peça para cá (ou dê duplo clique nela).")
            else:
                preso = "\nAmaldiçoado: preso até a próxima fogueira." if espaco in heroi.equipamentos.travados else ""
                self.dica = (f"{nome_do_espaco(espaco)}: {peca.nome}",
                             texto_do_item(peca) + preso + "\nDuplo clique ou arraste para fora para tirar.")
        return rect

    def desenhar_retratos(self, tela, area):
        """Os meus heróis para alternar (clique, Q/E ou 1 a 5)."""
        herois = self.fonte.herois()
        tamanho, espaco = 48, 8
        x = area.centerx - (len(herois) * (tamanho + espaco) - espaco) // 2
        for i, heroi in enumerate(herois):
            rect = pygame.Rect(x + i * (tamanho + espaco), area.y, tamanho, tamanho)
            desenhar_rosto(tela, self.app.sprites, heroi.sprite, rect, "ouro" if i == self.indice else "espaco",
                           apagado=not heroi.esta_vivo())
            self.registrar(rect, ("retrato", i))
            if self.em_cima == ("retrato", i) and not self.arrastando:
                self.dica = (heroi.nome, f"{heroi.nome_da_classe()} · nv {heroi.nivel} — tecla {i + 1}")

    def desenhar_heroi(self, tela, rect):
        painel(tela, rect, "ferro")
        heroi = self.heroi
        self.desenhar_retratos(tela, pygame.Rect(rect.x, rect.y + 12, rect.width, 48))
        linha(tela, f"{heroi.nome} · {heroi.nome_da_classe()} · nv {heroi.nivel}", tema.normal(), tema.OURO_CLARO,
              (rect.centerx, rect.y + 66), rect.width - 40, "midtop")
        topo = rect.y + 98
        x_esquerda, x_direita = rect.x + 18, rect.right - 18 - 60
        for i, espaco in enumerate(ESQUERDA):
            self.desenhar_espaco(tela, espaco, (x_esquerda, topo + i * 66))
        for i, espaco in enumerate(DIREITA):
            self.desenhar_espaco(tela, espaco, (x_direita, topo + i * 66))
        previa = pygame.Rect(x_esquerda + 72, topo, x_direita - x_esquerda - 84, 4 * 66 - 6)
        desenhar_previa(tela, self.app.sprites, heroi.sprite, previa, self.tempo, 3)
        self.areas.append((previa, ("boneco", None)))
        self.realcar_destino(tela, previa, ("item", "rapido"))
        self.desenhar_rapidos(tela, pygame.Rect(rect.x + 18, topo + 4 * 66, rect.width - 36, 76))
        self.desenhar_sets(tela, pygame.Rect(rect.x + 18, rect.bottom - 52, rect.width - 36, 44))

    def desenhar_rapidos(self, tela, area):
        """Itens rápidos: o espaço de uso automático e os consumíveis da mochila do herói."""
        linha(tela, "Itens rápidos (consumíveis da mochila)" if self.fonte.mostra_consumivel else
              "No acampamento só se escolhem as peças.", tema.mini(), tema.TEXTO_FRACO, area.topleft, area.width)
        if not self.fonte.mostra_consumivel:
            return
        y = area.y + 22
        self.desenhar_espaco(tela, "consumivel", (area.x, y), 52)
        x = area.x + 66
        for objeto, quantidade in self.heroi.inventario.pilhas("consumivel"):
            if x + 52 > area.right:
                break                                      # (os outros continuam na mochila, ao lado)
            caixa = quadro_de_item(tela, objeto, (x, y), 52, quantidade if quantidade > 1 else None,
                                   selecionado=self.selecionado == ("rapido", objeto.chave))
            self.registrar(caixa, ("rapido", objeto.chave))
            if self.em_cima == ("rapido", objeto.chave) and not self.arrastando:
                self.dica = (objeto.nome, self.dica_do_item(objeto, self.heroi, "mochila"))
            x += 58

    def desenhar_sets(self, tela, rect):
        """Uma linha com os sets ativos (o detalhe fica na dica) e as peças presas."""
        heroi = self.heroi
        sets = heroi.equipamentos.sets_ativos()
        presos = [nome_do_espaco(e) for e in heroi.equipamentos.travados if heroi.equipamento.get(e)]
        trechos = []
        if sets:
            trechos.append(("Sets: " + " · ".join(f"{c.nome} {p}/{len(c.pecas)}" for c, p, _ in sets), tema.OURO_CLARO))
        if presos:
            trechos.append(("Amaldiçoado, preso até a fogueira: " + ", ".join(presos), tema.COR_RARIDADE["amaldicoado"]))
        if not trechos:
            dica = "Arraste ou dê duplo clique para equipar." + (" Ctrl+clique marca vários." if self.fonte.tem_mochilas else "")
            trechos.append((dica, tema.TEXTO_APAGADO))
        CaixaTexto(rect, tema.mini(), vertical="meio").desenhar(tela, trechos)
        if sets and rect.collidepoint(self.mouse):
            detalhe = []
            for conjunto, pecas, ativos in sets:
                detalhe.append(f"{conjunto.nome} ({pecas}/{len(conjunto.pecas)})")
                detalhe += [f"{'◆' if b in ativos else '·'} {b.pecas} peças: {b.descricao}" for b in conjunto.bonus]
            self.dica = ("Sets", "\n".join(detalhe))

    # ---------------- atributos (embaixo) ----------------
    def peca_em_foco(self):
        """A peça sob o mouse (ou arrastada/selecionada) que dá para comparar com o equipado."""
        for alvo in (self.em_cima, self.arrastando, self.selecionado):
            chave = self.chave_do(alvo) if alvo else None
            if chave and existe(chave) and item(chave).tipo == "equipamento":
                return item(chave)
        return None

    def desenhar_atributos(self, tela):
        """Os 12 atributos do herói numa faixa; com uma peça em foco, ▲ verde / ▼ vermelho do que muda."""
        painel(tela, ATRIBUTOS, "pedra")
        heroi = self.heroi
        peca = self.peca_em_foco()
        diferencas = resumo.comparar(heroi, peca) if peca is not None else None
        valores = resumo.valores(heroi)
        nomes = resumo.nomes_dos_atributos()
        largura = (ATRIBUTOS.width - 24) // len(nomes)
        for i, (chave, nome) in enumerate(nomes.items()):
            x = ATRIBUTOS.x + 12 + i * largura
            linha(tela, ROTULO_CURTO.get(chave, nome), tema.mini(), tema.TEXTO_FRACO, (x + 4, ATRIBUTOS.y + 5), largura - 8)
            valor = linha(tela, resumo.formatar(chave, valores[chave]), tema.pequena(), tema.TEXTO,
                          (x + 4, ATRIBUTOS.y + 24), largura // 2)
            diferenca = (diferencas or {}).get(chave)
            if diferenca:
                cor, seta = (VERDE, "▲") if diferenca > 0 else (VERMELHO, "▼")
                linha(tela, f"{seta}{resumo.formatar_diferenca(chave, diferenca)}", tema.mini(), cor,
                      (valor.right + 2, ATRIBUTOS.y + 27), x + largura - valor.right - 6)

    # ---------------- tela ----------------
    def desenhar_arrasto(self, tela):
        if not self.arrastando:
            return
        if self.arrastando[0] == "espaco":
            peca = self.heroi.equipamento.get(self.arrastando[1])
        else:
            peca = item(self.chave_do(self.arrastando))
        if peca is not None:
            icone = icone_item(peca, 4)
            tela.blit(icone, icone.get_rect(center=self.mouse))
            lado = self.lado_do(self.arrastando) if self.arrastando[0] != "espaco" else None
            quantos = len([m for m in self.marcados if m[0] == lado]) if (lado, peca.chave) in self.marcados else 0
            if quantos > 1:
                texto(tela, f"+{quantos - 1}", tema.pequena(), tema.OURO_CLARO, (self.mouse[0] + 18, self.mouse[1] + 10))

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.areas = []
        self.em_cima = None
        self._assinatura = self.assinatura_do_grupo()
        self.fundo.desenhar(tela)
        if self.run is not None:
            cabecalho_da_run(tela, self.run, self.fonte.titulo, jogador=self.meu_jogador())
        else:
            cabecalho_do_acampamento(tela, self.fonte.titulo, self.app.progresso, "Equipamento inicial da expedição")
        self.desenhar_barra(tela)
        grades = self.fonte.grades(self.heroi)
        if self.fonte.tem_mochilas:
            (lado_m, titulo_m, mochila), (lado_b, titulo_b, bau) = grades
            self.desenhar_grade(tela, MOCHILA, lado_m, titulo_m, mochila)
            self.desenhar_grade(tela, BAU_RECT, lado_b, titulo_b, bau)
            self.desenhar_heroi(tela, HEROI)
        else:
            lado, titulo, inventario = grades[0]
            self.desenhar_heroi(tela, HEROI_DO_ACAMPAMENTO)
            self.desenhar_grade(tela, ESTANDE, lado, titulo, inventario)
        self.desenhar_atributos(tela)                    # depois das grades: compara a peça sob o mouse
        voltar = pygame.Rect(tema.LARGURA - 176, BOTOES_Y, 168, 44)
        x_direita = voltar.x
        if self.ao_fabricar is not None:
            x_direita -= 186
            self.botao(Botao((x_direita, BOTOES_Y, 178, 44), "Fabricação", lambda: self.ao_fabricar(self.indice_no_grupo()),
                             "F"))
        if self.fonte.tem_mochilas:
            x_direita -= 206
            self.botao(Botao((x_direita, BOTOES_Y, 198, 44), "Histórico do baú", self.mostrar_historico,
                             dica=("Histórico do baú", "Quem colocou e quem retirou o quê (os últimos movimentos).")))
        x_esquerda = 8
        if self.marcados:
            self.botao(Botao((8, BOTOES_Y, 250, 44), f"Mover marcados ({len(self.marcados)})", self.mover_marcados,
                             estilo="ouro", dica=("Mover marcados", "Leva cada pilha marcada para o outro lado.")))
            self.botao(Botao((266, BOTOES_Y, 120, 44), "Desmarcar", lambda: setattr(self, "marcados", set())))
            x_esquerda = 394
        if self.mensagem and self.tempo - self.mensagem[2] < 3.5:
            CaixaTexto((x_esquerda, BOTOES_Y, x_direita - x_esquerda - 8, 44), tema.normal(), self.mensagem[1],
                       alinhamento="centro", vertical="meio").desenhar(tela, self.mensagem[0])
        self.botao(Botao(voltar, "Voltar", self.voltar, "ESC"))
        if self.arrastando:
            self.dica = None
        self.terminar_desenho(tela)
        self.desenhar_arrasto(tela)
