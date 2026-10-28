"""Tela de combate do roguelike.

Quem decide as regras é o Combate (roguelike/combate.py) e quem faz ele andar é o CondutorDoCombate
(roguelike/condutor.py). Esta tela:
1. quando as animações acabam, pede ao condutor mais um passo (turno, inimigo agindo, fim);
2. se for a vez de um herói, mostra os menus (Lutar / Itens / Concentrar) e a escolha do alvo, e manda a escolha
   como um comando (AgirNoCombate); herói com Decisor (ex.: IA) decide sozinho;
3. anima cada Evento devolvido pelo combate (investida, dano, cura, status...).

Numa partida em grupo (MP6), cada um escolhe só pelos SEUS heróis; na vez do herói de outro, a tela mostra
"Bia escolhendo..." e espera o comando chegar ("esperando_outro"); depois de mandar o seu, espera o host devolver
("aguardando"). O host dá a vez à IA de quem demorar mais que tempo_da_vez (ou cair da partida). Comandos que chegam
enquanto a tela anima esperam (aceita_comandos). A janela do fim vira uma votação: segue quando todos confirmarem.

Teclas: 1/2/3 ações, 1-8 habilidades, ←/→ página ou alvo, Enter confirma,
ESC volta/pausa, V muda a velocidade, segurar ESPAÇO acelera.
"""

import math
from collections import deque

import pygame

import efeitos
import efeitos_de_golpe
from roguelike import elementos
from roguelike.comandos import AgirNoCombate, ComecarCombate
from roguelike.condutor import ESPERANDO, FIM
from roguelike.dados import regras
from roguelike.ia import ia_do, IAChefe
from roguelike.itens import Consumivel, item
from roguelike.status import dados_do_status
from telas import em_grupo
from telas.comum import TelaComBotoes
from telas.combate.ambiente import VisualDoAmbiente
from telas.combate.edito import ProclamacaoDoEdito
from telas.combate.sons import som_do_golpe
from telas.combate.trono import CorridaAoTrono, VisualNoTrono
from telas.combate.visual import VisualLutador, organizar, separar_barras
from telas.combate.visual_bando import VisualBando
from telas.combate.visual_roda import VisualRoda, VisualRatoDaRoda
from ui import tema
from ui.desenho import painel, texto, icone_status, losango, escurecer_tela, vinheta, barra, anotar
from ui.componentes import BarraStatus, RegistroRolavel
from ui.texto import CaixaTexto, linha as linha_que_cabe
from ui.widgets import Botao
from visual.cenario_macabro import CenarioMacabro, cena_da_area, hora_da_area, paleta_do_lugar

PAINEL_Y = 588
CHAO = 532
TRONO_PES = (640, 408)          # onde o Rei dos Ratos senta no trono (sem o "trono" no cenarios.json)
SPRITE_DO_TRONO = "trono_dos_ratos"   # o trono de ratos e ouro (animado), no "trono" -> "base" do Salão do Trono
POR_PAGINA = 6                  # habilidades/itens por página (3 colunas x 2 linhas)

# Quem ataca de longe (projétil em vez de investida)
SPRITES_DE_LONGE = {"arqueira", "esqueleto_arqueiro", "mago_Fogo", "mago_Gelo", "mago_Raio", "bruxa", "goblin_xama",
                    "freira_profana", "lich", "noiva_vampira", "bardo", "torreta", "fada", "rei_sombrio", "dragao",
                    "dragao_osseo", "dragao_filhote", "rato_alquimista"}
PROJETEIS = {
    "flecha": ("flecha", (220, 200, 160)), "flecha_venenosa": ("flecha", (150, 220, 80)),
    "flecha_de_prata": ("flecha", (220, 230, 255)), "flecha_encantada": ("flecha", (150, 255, 200)),
    "flechada": ("flecha", (220, 200, 160)), "bola_de_fogo": ("bola", (250, 140, 40)),
    "lanca_de_gelo": ("lanca", (170, 230, 255)), "teia": ("teia", (230, 230, 230)),
    "frasco_de_veneno": ("bola", (140, 220, 80)), "frasco_cegante": ("bola", (236, 232, 200)),
}
CORES_DO_DANO = {"golpe": (244, 236, 226), "veneno": tema.VENENO, "queimadura": (250, 150, 60),
                 "sangramento": (232, 70, 64), "espinhos": (170, 220, 100), "dano_adiado": (200, 150, 230),
                 "peste": (190, 210, 90), "explosao": (255, 170, 80), "edito": (240, 90, 80)}
COR_FRACO, COR_RESISTE = (255, 214, 90), (170, 176, 190)
COR_FEBRE, COR_ALIVIO, COR_ENCANTO = (210, 230, 100), (150, 230, 160), (226, 160, 255)
COR_EDITO = (240, 214, 150)
CORES_DO_REGISTRO = {"dano": (226, 170, 160), "cura": (150, 220, 150), "morte": (240, 110, 100),
                     "habilidade": tema.TEXTO_TITULO, "status": (190, 170, 220), "rodada": tema.OURO,
                     "fim": tema.OURO_CLARO, "invocacao": (170, 200, 240), "item": (220, 200, 150),
                     "febre": COR_FEBRE, "encanto": COR_ENCANTO, "alivio": COR_ALIVIO, "roubo": (240, 200, 110), "fugiu": (240, 200, 110),
                     "reforco": (220, 190, 120), "protegeu": (230, 210, 150), "roubo_de_ouro": (240, 200, 110),
                     "edito": COR_EDITO, "desobedeceu": (240, 110, 100), "devorou": (240, 200, 110),
                     "ouro_devolvido": (240, 200, 110), "desceu_do_trono": (240, 200, 110)}


class TelaCombate(TelaComBotoes):
    def __init__(self, app, run, encontro, ao_terminar=None, condutor=None):
        super().__init__(app)
        self.run = run
        self.encontro = encontro
        self.ao_terminar = ao_terminar           # função(recompensa) chamada no fim
        outro = None if encontro is run.encontro else encontro.para_dict()        # (combate de teste)
        # (em grupo, o combate já começou pelo comando do host: o condutor vem pronto)
        self.condutor = condutor or self.enviar(ComecarCombate(encontro=outro)).valor
        self.combate = self.condutor.combate
        self.partida = em_grupo.partida_da(self)  # None no solo
        self.esperando_desde = 0.0              # quando começou a vez de agora (o tempo da vez, em grupo)
        self.registro_antes = 0                 # comandos executados quando a espera começou
        self.recusas_antes = 0
        self.sprites = app.sprites

        total = run.areas_da_regiao()
        nome, variante = cena_da_area(run.regiao_atual, run.area, encontro.tipo, total)
        self.cenario = CenarioMacabro(nome, variante, tema.LARGURA, tema.ALTURA,
                                      hora_da_area(run.regiao_atual, run.area, total), paleta_do_lugar(run.regiao_atual))
        self.efeitos = efeitos.GerenciadorEfeitos()
        self.ambiente = VisualDoAmbiente(self.combate, CHAO, PAINEL_Y)     # água e escuro (Reino dos Ratos)
        self.cenario.alagar(self.ambiente.nivel_da_agua())
        self.no_trono = dict(self.combate.de_volta) if self.combate.de_volta else None   # o Rei esperando no trono
        trono = self.cenario.config.get("trono", {})
        self.trono_pes = self.cenario.na_tela(trono["pes"]) if "pes" in trono else TRONO_PES
        self.corrida = None                     # o Rei correndo para o trono (CorridaAoTrono)
        self.proclamacao = None                 # o Édito Real grande no meio da tela (ProclamacaoDoEdito)
        if any(getattr(inimigo, "ficha", {}).get("no_da_roda") for inimigo in self.combate.inimigos):
            self.cenario.esconder("no_da_rainha")                         # a Rainha desceu do teto para a luta

        self.visuais = {}
        self.lado_herois, self.lado_inimigos = [], []
        for lutador in self.combate.herois:
            self.adicionar_visual(lutador)
        for lutador in self.combate.inimigos:
            self.adicionar_visual(lutador)
        self.reorganizar()

        self.fila = deque()
        self.espera = 0.4
        self.estado = "animando"                # animando, escolhendo, fim
        self.menu = "principal"                 # principal, habilidades, itens, alvo
        self.pagina = 0
        self.escolha = None                     # habilidade ou item escolhido
        self.alvos = []
        self.indice_alvo = 0
        self.registro = []
        self.banner = None                      # (texto, cor, início)
        self.recompensa = None
        self.pausado = False
        self.indice_pausa = 0
        self.tremor_ate = -1.0
        self.dica_pendente = None               # dica pedida durante o desenho (ícone, retrato)
        self.banner_habilidade = None           # (nome, início)
        self.em_destaque = None                 # (habilidade/item, nível) sob o foco/mouse: vai para a faixa
        self.focar_ao_desenhar = False          # menu aberto pelo teclado: foca o 1º botão
        self.barra_vida = BarraStatus(tema.VIDA_HEROI)
        self.registro_rolavel = RegistroRolavel(self.registro)
        self.barra_energia = BarraStatus(tema.ENERGIA, cor_atraso=tema.ENERGIA_CLARA)
        self.enfileirar()

    def musica(self):
        propria = next((i.ficha["musica"] for i in self.combate.inimigos if "musica" in getattr(i, "ficha", {})), None)
        if propria:                             # chefe com tema próprio (Mercador, Primeiro Herói)
            return propria
        if self.encontro.tipo in ("chefe", "mini_chefe", "fuga"):
            return "chefe"
        return self.run.musica()

    # ============================================================
    # VISUAIS
    # ============================================================

    def adicionar_visual(self, lutador):
        inimigo = lutador.lado == "inimigos"
        if getattr(lutador, "ficha", {}).get("no_da_roda"):                       # a Rainha dos Ratos: o nó da roda
            visual = VisualRoda(lutador, self.sprites, inimigo)
        elif getattr(lutador, "no", None) is not None and self.visual(lutador.no) is not None:   # um rato da roda
            visual = VisualRatoDaRoda(lutador, self.sprites, inimigo, self.visual(lutador.no))
        elif lutador.tem_status("no_trono") and "base" in self.cenario.config.get("trono", {}):  # A Corte Completa
            visual = VisualNoTrono(lutador, self.sprites, inimigo, self.trono_pes)
        else:
            classe = VisualBando if getattr(lutador, "eh_bando", False) else VisualLutador   # bando: vários bichos
            visual = classe(lutador, self.sprites, inimigo=inimigo)
        self.visuais[id(lutador)] = visual
        (self.lado_inimigos if visual.inimigo else self.lado_herois).append(visual)
        if not lutador.esta_vivo():
            visual.animador.tocar("morte")
            visual.animador.tempo = 10
            visual.morto_desde = -10
        return visual

    def visual(self, lutador):
        if lutador is None:
            return None
        return self.visuais.get(id(lutador))

    def reorganizar(self):
        organizar(self.lado_herois, False, CHAO)
        organizar([v for v in self.lado_inimigos if not getattr(v, "na_roda", False) and not getattr(v, "fixo", False)],
                  True, CHAO)                                    # (a roda e o Rei no trono ficam no lugar deles)

    def todos_os_visuais(self):
        return sorted(self.lado_herois + self.lado_inimigos, key=lambda v: v.y)

    # ============================================================
    # EVENTOS DO COMBATE -> ANIMAÇÕES
    # ============================================================

    def enfileirar(self):
        self.fila.extend(self.combate.pegar_eventos())

    def registrar(self, evento):
        if evento.texto and evento.tipo not in ("turno", "energia", "status_fim"):
            conteudo = evento.texto
            dono = getattr(evento.origem, "jogador", None) if self.partida is not None else None
            if dono is not None and evento.tipo in ("habilidade", "item", "concentrar"):
                conteudo = f"[{dono.nome}] {conteudo}"             # em grupo: de quem foi a ação
            self.registro.append((conteudo, CORES_DO_REGISTRO.get(evento.tipo, tema.TEXTO_FRACO)))
            del self.registro[:-80]                 # a mesma lista é lida pelo RegistroRolavel

    def flutuar(self, lutador, conteudo, cor, tamanho=24, altura=0):
        visual = self.visual(lutador)
        if visual is None:
            return
        caixa = visual.caixa()
        self.efeitos.adicionar(efeitos.TextoFlutuante(conteudo, caixa.centerx, caixa.top - 30 - altura, cor,
                                                      tema.fonte(tamanho)))

    def tocar(self, evento):
        """Mostra um evento e devolve quanto tempo esperar até o próximo."""
        self.registrar(evento)
        tipo = evento.tipo
        som = self.som_do_evento(evento)
        if som:
            self.app.audio.tocar(som)
        origem, alvo = self.visual(evento.origem), self.visual(evento.alvo)

        if tipo == "rodada":
            self.banner = (f"Rodada {evento.valor}", tema.OURO, self.tempo)
            return 0.55
        if tipo == "turno":
            return 0.12 if evento.origem.lado == "herois" else 0.3
        if tipo == "energia":
            # A energia do começo do turno já aparece no cartão; só mostra a das habilidades/itens
            if evento.extras.get("motivo") not in ("turno", "concentrar"):
                self.flutuar(evento.alvo, f"+{evento.valor} energia", tema.ENERGIA_CLARA, 15, 10)
            return 0.04
        if tipo == "habilidade":
            return self.animar_habilidade(evento)
        if tipo == "item":
            self.flutuar(evento.origem, evento.extras["item"].nome, (230, 210, 160), 18, 20)
            if origem:
                origem.atacar_parado()
            return 0.35
        if tipo == "dano":
            return self.animar_dano(evento, alvo)
        if tipo == "esquiva":
            if alvo:
                alvo.esquivar()
            self.flutuar(evento.alvo, "Esquivou!", (200, 220, 240), 18)
            return 0.12
        if tipo == "escudo":
            self.flutuar(evento.alvo, f"-{evento.valor} escudo", (150, 190, 240), 16, 18)
            return 0.05
        if tipo == "cura":
            self.flutuar(evento.alvo, f"+{evento.valor}", tema.CURA, 24)
            if alvo and evento.extras.get("motivo") != "roubo":
                x, y = alvo.centro()
                self.efeitos.adicionar(efeitos.Cura(x, y - 30, efeitos.CURA))
            return 0.1
        if tipo == "status":
            if alvo:
                status = evento.alvo.status.get(evento.extras.get("status"))
                if status is not None:
                    cor = (240, 140, 130) if status.tipo == "negativo" else (170, 210, 250)
                    self.flutuar(evento.alvo, status.nome, cor, 15, -18)
            return 0.08
        if tipo == "resistiu":
            self.flutuar(evento.alvo, "Resistiu!", (220, 220, 220), 16)
            return 0.08
        if tipo == "alivio":                                        # a Peste perdeu um nível
            self.flutuar(evento.alvo, f"{dados_do_status(evento.extras['status'])['nome']} -{evento.valor}", COR_ALIVIO, 15, -18)
            return 0.1
        if tipo == "roubo":                                         # o Rato Ladrão levou um consumível
            self.flutuar(evento.alvo, f"-1 {item(evento.extras['item']).nome}", (240, 200, 110), 16, 20)
            return 0.4
        if tipo == "roubo_de_ouro":                                 # o Mendigo Bubônico bateu a carteira
            self.flutuar(evento.origem, f"-{evento.valor} ouro", (240, 200, 110), 18, 20)
            return 0.5
        if tipo == "edito":                                         # o Rei dos Ratos ergueu o cetro e proclamou uma lei
            dados = dados_do_status(evento.extras["status"]) if evento.extras.get("status") else {}
            self.proclamacao = ProclamacaoDoEdito(dados.get("nome", evento.texto), dados.get("lei", ""), self.tempo,
                                                  (tema.LARGURA - 145, 117))       # (o centro do pergaminho)
            if origem:
                if self.sprites.tem_animacao(origem.nome_sprite, "decreto"):          # o cetro fica erguido
                    animador = origem.animador                      # (o golpe acabou de erguê-lo: segue do alto)
                    animador.tocar("decreto", segurar=ProclamacaoDoEdito.ENTRA + ProclamacaoDoEdito.FICA)
                    animador.tempo = (self.sprites.quadros_de(origem.nome_sprite, "decreto") - 1) / \
                        animador.VELOCIDADE["decreto"]
                x, y = origem.centro()
                self.efeitos.adicionar(efeitos.Onda(x, y, (236, 200, 120), 130))
            return ProclamacaoDoEdito.ENTRA + ProclamacaoDoEdito.FICA
        if tipo == "desobedeceu":                                   # castigo do édito
            self.flutuar(evento.alvo, "Desobedeceu!", tema.SANGUE_CLARO, 20, 34)
            self.efeitos.adicionar(efeitos.FlashTela((200, 40, 40), 0.18, transparencia=60))
            self.tremor_ate = self.tempo + 0.25
            return 0.45
        if tipo == "desceu_do_trono":                               # A Corte Completa: a Rainha caiu e o Rei salta
            if origem is not None and getattr(origem, "fixo", False):
                self.lado_inimigos.remove(origem)
                novo = self.adicionar_visual(evento.origem)         # (sem o No Trono: um visual comum, na fileira)
                novo.x, novo.y = origem.x, origem.y
                novo.vida_mostrada = origem.vida_mostrada
                self.reorganizar()
                x, y = origem.centro()
                self.efeitos.adicionar(efeitos.Onda(x, y, (236, 200, 120), 130))
            self.flutuar(evento.origem, "Desce do trono!", (240, 200, 110), 22, -110)   # (abaixo da barra do chefe)
            self.tremor_ate = self.tempo + 0.4
            return 0.8
        if tipo == "devorou":                                       # o Rei comeu o Queijo Real
            if alvo:
                alvo.sumir()
            self.flutuar(evento.origem, "Nhac!", (240, 200, 90), 22, 24)
            return 0.6
        if tipo == "ouro_devolvido":                                # os cofres do Rei se abrem
            self.flutuar(evento.origem, f"+{evento.valor} ouro", (240, 200, 110), 22, 24)
            return 0.7
        if tipo == "fugiu":                                         # saiu da luta vivo (Rato Ladrão)
            if origem and self.ao_trono(evento.origem, origem):     # o Rei dos Ratos corre para o trono
                self.flutuar(evento.origem, "Ao trono!", (240, 200, 110), 22, 24)
                return CorridaAoTrono.CORRER + CorridaAoTrono.SUBIR
            self.flutuar(evento.origem, "Fugiu!", (240, 200, 110), 20, 20)
            if origem:
                origem.sumir()
            return 0.6
        if tipo in ("febre", "encanto"):                            # Febre Negra / Encantado: age fora de si
            febre = tipo == "febre"
            self.flutuar(evento.origem, "Febre Negra!" if febre else "Encantado!", COR_FEBRE if febre else COR_ENCANTO, 20, 20)
            if origem:
                x, y = origem.centro()
                self.efeitos.adicionar(efeitos.Onda(x, y, (120, 150, 40) if febre else (170, 90, 220), 90))
            return 0.7
        if tipo == "perdeu_vez":
            self.flutuar(evento.origem, "Perdeu a vez!", (250, 230, 120), 18)
            return 0.6
        if tipo == "concentrar":
            if origem:
                x, y = origem.centro()
                self.efeitos.adicionar(efeitos.Onda(x, y, (120, 190, 250), 70))
            self.flutuar(evento.origem, "Concentrou", tema.ENERGIA_CLARA, 18, 20)
            return 0.4
        if tipo == "morte":
            if alvo:
                alvo.morrer()
            return 0.5
        if tipo == "sobreviveu":
            self.flutuar(evento.alvo, "Não caiu!", tema.OURO_CLARO, 20)
            return 0.3
        if tipo in ("invocacao", "reforco"):                      # reforço: inimigo de verdade (Arauto Roedor)
            novo = self.adicionar_visual(evento.alvo)
            novo.surgir()
            if self.no_trono and getattr(evento.alvo, "chave", None) == self.no_trono["chave"]:
                self.no_trono = None                               # o Rei salta do trono para a luta
                novo.x, novo.y = self.trono_pes
                self.tremor_ate = self.tempo + 0.4
            self.reorganizar()
            x, y = novo.alvo_x, novo.alvo_y - 40
            self.efeitos.adicionar(efeitos.Onda(x, y, (150, 120, 220) if tipo == "invocacao" else (220, 190, 120), 80))
            return 0.45
        if tipo == "protegeu":                                     # Guarda Real entrou na frente
            self.flutuar(evento.origem, "Protegeu!", (230, 210, 150), 18, 20)
            return 0.35
        if tipo == "dissipou":
            if origem:
                origem.sumir()
            return 0.2
        if tipo == "reviver":
            if alvo is None:                                       # inimigo reerguido: o visual dele já tinha sumido
                alvo = self.adicionar_visual(evento.alvo)
                alvo.surgir()
                self.reorganizar()
            if alvo:
                alvo.reviver()
                x, y = alvo.centro()
                self.efeitos.adicionar(efeitos.Cura(x, y, efeitos.ROXO if evento.extras.get("renasceu") else efeitos.LUZ))
            if evento.extras.get("renasceu"):
                self.flutuar(evento.alvo, "Ergueu-se!", (150, 220, 255), 20, 20)
                return 0.8
            return 0.5
        if tipo == "fim":
            vitoria = evento.extras.get("resultado") == "vitoria"
            if vitoria:
                self.efeitos.adicionar(efeitos.Confete(tema.LARGURA))
            return 0.8
        if tipo == "fase_do_chefe":
            nome = evento.extras.get("nome")
            self.banner = (f"Fase {evento.valor}" + (f": {nome}" if nome else ""), tema.SANGUE_CLARO, self.tempo)
            self.tremor_ate = self.tempo + 0.5
            if alvo:
                x, y = alvo.centro()
                self.efeitos.adicionar(efeitos.Onda(x, y, (230, 80, 70), 120))
            return 1.0
        if tipo == "escudo_quebrou":
            self.flutuar(evento.alvo, "Escudo partido!", (150, 220, 255), 22, 24)
            if alvo:
                x, y = alvo.centro()
                self.efeitos.adicionar(efeitos.Onda(x, y, (150, 220, 255), 100))
            return 0.5
        if tipo == "aviso":
            self.flutuar(evento.alvo, "!", tema.OURO_CLARO, 28, 30)
            return 0.5
        if tipo == "ambiente":                                      # a água subiu, algo se mexe no escuro...
            self.banner = (evento.texto, (140, 210, 160), self.tempo)
            return 0.8
        return 0.0

    def som_do_evento(self, evento):
        """Qual efeito sonoro acompanha cada evento do combate (None = nenhum)."""
        tipo = evento.tipo
        if tipo == "dano":
            efetividade, elemento = evento.extras.get("efetividade"), evento.extras.get("elemento")
            if evento.critico:
                return "critico"
            if efetividade == "fraco":
                return "fraco"
            if evento.bloqueou:
                return "bloqueio"
            if efetividade == "resiste":
                return "resistente"
            if elemento and elemento != elementos.PADRAO:
                return f"elemento_{elemento}"
            return "golpe"
        if tipo == "habilidade":
            if evento.extras["habilidade"].chave == "metamorfose_draconica":
                return "metamorfose"
            return som_do_golpe(evento.extras["habilidade"])
        if tipo == "inicio" and self.encontro.tipo in ("chefe", "mini_chefe", "fuga"):
            return "rugido"
        if tipo == "fase_do_chefe":
            return "rugido"
        if tipo == "escudo_quebrou":
            return "bloqueio"
        if tipo == "reviver" and evento.extras.get("renasceu"):
            return "renascer"
        if tipo == "fim":
            return "vitoria" if evento.extras.get("resultado") == "vitoria" else "derrota"
        return {"esquiva": "esquiva", "cura": "cura", "status": "status", "morte": "morte", "invocacao": "invocar",
                "reforco": "invocar", "reviver": "cura", "item": "item", "concentrar": "magia", "rodada": "navegar",
                "edito": "rugido", "desobedeceu": "critico", "ouro_devolvido": "item", "desceu_do_trono": "rugido"}.get(tipo)

    def de_longe(self, usuario, habilidade):
        return habilidade.chave in PROJETEIS or usuario.sprite in SPRITES_DE_LONGE

    def animar_habilidade(self, evento):
        habilidade = evento.extras["habilidade"]
        alvos = evento.extras.get("alvos", [])
        usuario = self.visual(evento.origem)
        self.banner_habilidade = (habilidade.nome, self.tempo)
        if usuario is None:
            return 0.2
        if habilidade.animacao and usuario.tocar_linha(habilidade.animacao):     # ex.: o Rei ergue o pergaminho
            return 0.75
        config = efeitos_de_golpe.config_do_golpe(habilidade.chave)
        if config is not None:
            return self.animar_golpe_proprio(usuario, alvos, config)
        if not habilidade.ofensiva():
            usuario.atacar_parado()
            for alvo in alvos:
                visual = self.visual(alvo)
                if visual is not None:
                    x, y = visual.centro()
                    self.efeitos.adicionar(efeitos.Onda(x, y + 20, (240, 210, 130), 60, achatada=True))
            return 0.35
        primeiro = self.visual(alvos[0]) if alvos else None
        if habilidade.alvo == "inimigos":
            usuario.atacar_parado()
            for alvo in alvos:
                visual = self.visual(alvo)
                if visual is not None:
                    x, y = visual.centro()
                    self.efeitos.adicionar(efeitos.Explosao(x, y, efeitos.FOGO if "fogo" in habilidade.chave else efeitos.ROXO, 14, 40))
            return 0.3
        de_longe = self.de_longe(evento.origem, habilidade) or getattr(usuario, "fixo", False)   # (o Rei no trono)
        if de_longe and primeiro is not None:
            usuario.atacar_parado()
            formato, cor = PROJETEIS.get(habilidade.chave) or getattr(usuario, "projetil", None) or ("bola", (170, 140, 240))
            inicio = usuario.origem_do_projetil() if hasattr(usuario, "origem_do_projetil") else usuario.centro()
            atraso = getattr(usuario, "atraso_do_projetil", 0.0)    # (o Rei solta o clarão quando aponta o cetro)
            for alvo in (alvos if habilidade.alvo != "aleatorio" else alvos[:3]):
                visual = self.visual(alvo)
                if visual is not None:
                    self.efeitos.adicionar(efeitos.Projetil(inicio, visual.centro(), cor, formato, 10, 0.3, atraso=atraso))
            return 0.32 + atraso
        if primeiro is not None:
            usuario.investir(primeiro.x)
            return usuario.tempo_ate_o_golpe()
        usuario.atacar_parado()
        return 0.25

    def animar_golpe_proprio(self, usuario, alvos, config):
        """Golpe com efeito próprio (dados/efeitos_golpes.json). Devolve quanto esperar até mostrar o dano."""
        visuais = [v for v in (self.visual(alvo) for alvo in alvos) if v is not None] or [usuario]
        atraso = 0.0
        if config.get("investe") and visuais[0] is not usuario:
            usuario.investir(visuais[0].x)
            atraso = usuario.tempo_ate_o_golpe()
        else:
            usuario.atacar_parado()
        pontos = [v.centro() for v in visuais]
        for efeito in efeitos_de_golpe.efeitos_do_golpe(config, usuario.centro(), pontos, CHAO, atraso):
            self.efeitos.adicionar(efeito)
        return atraso or efeitos_de_golpe.espera_do_golpe(config)

    def animar_dano(self, evento, alvo):
        motivo = evento.extras.get("motivo", "golpe")
        elemento = evento.extras.get("elemento")
        cor = CORES_DO_DANO.get(motivo, (244, 236, 226))
        if motivo == "golpe" and elemento not in (None, elementos.PADRAO):
            cor = elementos.cor(elemento)              # o número do dano tem a cor do elemento
        if evento.critico:
            self.flutuar(evento.alvo, f"{evento.valor}!", (255, 196, 70), 34)
            self.flutuar(evento.alvo, "CRÍTICO", (255, 140, 60), 16, 34)
            self.tremor_ate = self.tempo + 0.2
            self.efeitos.adicionar(efeitos.FlashTela((255, 240, 220), 0.12, transparencia=55))
        else:
            self.flutuar(evento.alvo, str(evento.valor), cor, 26)
        if evento.bloqueou:
            self.flutuar(evento.alvo, "bloqueou", (190, 190, 210), 14, -16)
        efetividade = evento.extras.get("efetividade")
        if efetividade == "fraco":
            self.flutuar(evento.alvo, "Fraco!", COR_FRACO, 17, 52 if evento.critico else 26)
        elif efetividade == "resiste":
            self.flutuar(evento.alvo, "Resistente", COR_RESISTE, 14, 52 if evento.critico else 26)
        if alvo is not None:
            alvo.levar_golpe(forte=evento.critico)
            x, y = alvo.centro()
            cores = {"veneno": efeitos.VENENO, "queimadura": efeitos.FOGO, "peste": efeitos.VENENO,
                     "explosao": efeitos.FOGO}.get(motivo, efeitos.SANGUE)
            self.efeitos.adicionar(efeitos.Explosao(x, y, cores, 16 if evento.critico else 8, 34, gravidade=300))
        return 0.13 if motivo == "golpe" else 0.25

    # ============================================================
    # ATUALIZAÇÃO (o "maestro" dos turnos)
    # ============================================================

    def atualizar(self, dt):
        super().atualizar(dt)
        acelerar = 3.0 if self.app.controles.segurando("acelerar") else 1.0
        dt_jogo = dt * self.app.velocidade * acelerar
        for visual in self.lado_herois + self.lado_inimigos:
            visual.superficie_da_agua = self.ambiente.superficie(visual)   # bichos que boiam sobem com a água
            visual.atualizar(dt_jogo)
        if any(v.mudou_de_tamanho for v in self.lado_herois + self.lado_inimigos):
            for visual in self.lado_herois + self.lado_inimigos:
                visual.mudou_de_tamanho = False
            self.reorganizar()
        self.efeitos.atualizar(dt_jogo)
        self.cenario.atualizar(dt)
        self.ambiente.atualizar(dt)
        self.cenario.alagar(self.ambiente.nivel_da_agua())                 # o chão do cenário segue a água
        if self.corrida is not None:
            self.corrida.atualizar(dt_jogo)
            if self.corrida.terminou():                                     # chegou: fica sentado no trono
                self.no_trono = {"chave": self.corrida.visual.nome_sprite}
                self.corrida = None
        self.limpar_visuais()
        if self.pausado:
            return

        if self.espera > 0:
            self.espera -= dt_jogo
            return
        if self.fila:
            self.espera = self.tocar(self.fila.popleft())
            return
        if self.estado in ("escolhendo", "esperando_outro", "aguardando"):
            self.cuidar_da_espera()
        if self.estado in ("fim", "escolhendo", "esperando_outro", "aguardando"):
            return
        passo = self.condutor.passo()               # o combate anda um pedaço (roguelike/condutor.py)
        self.enfileirar()
        if passo == FIM:
            self.terminar()
        elif passo == ESPERANDO:
            self.vez_do_heroi(self.combate.atual)

    def e_meu(self, heroi):
        """Quem joga neste computador escolhe por este herói? (no solo, sempre)"""
        if self.partida is None:
            return True
        return getattr(getattr(heroi, "jogador", None), "id", None) == self.partida.eu

    def vez_do_heroi(self, heroi):
        """Quem comanda o herói decide: com um Decisor (ex.: IA), na hora; senão, abre o menu. Em grupo, o herói de
        outro jogador: espera o comando dele chegar."""
        sessao = self.sessao()
        self.esperando_desde = self.tempo
        self.registro_antes = len(sessao.processador.registro)
        decisor = sessao.decisor_de(heroi)
        if decisor is not None and self.e_meu(heroi):
            self.mandar(decisor.comando(sessao.estado, heroi))
            return
        if self.e_meu(heroi):
            self.estado = "escolhendo"
            self.abrir_menu("principal")
        else:
            self.estado = "esperando_outro"

    def mandar(self, comando):
        """Manda a ação do herói. No solo (e no host) ela já aconteceu: anima. Em quem entrou, espera o host."""
        sessao = self.sessao()
        antes, recusas = len(sessao.processador.registro), getattr(sessao, "recusas", 0)
        resultado = self.enviar(comando)
        if not resultado:
            return resultado
        self.menu = "principal"
        if self.partida is None:
            self.estado = "animando"
            self.enfileirar()
            return resultado
        self.estado, self.registro_antes, self.recusas_antes = "aguardando", antes, recusas
        self.cuidar_da_espera()
        return resultado

    def cuidar_da_espera(self):
        """Em grupo: o comando da vez chegou (de quem for: o dono, a IA do host)? O host recusou o meu? E o host dá a
        vez à IA de quem demorou demais ou caiu da partida."""
        if self.partida is None:
            return
        sessao = self.sessao()
        if len(sessao.processador.registro) > self.registro_antes:
            self.estado, self.menu, self.escolha = "animando", "principal", None
            self.enfileirar()
            return
        if self.estado == "aguardando" and getattr(sessao, "recusas", 0) > self.recusas_antes:
            self.estado = "escolhendo"                              # (o host recusou: escolher de novo)
            self.abrir_menu("principal")
            return
        heroi = self.condutor.heroi_da_vez()
        if self.partida.eh_host and heroi is not None and self.estado != "aguardando":
            dono = getattr(getattr(heroi, "jogador", None), "id", None)
            demorou = self.tempo - self.esperando_desde > em_grupo.configuracao()["tempo_da_vez"]
            if dono in self.partida.desconectados or demorou:
                self.partida.sessao.agir_por(heroi)
                self.cuidar_da_espera()

    def aceita_comandos(self):
        """Em grupo: um comando que chegou pode ser executado agora? Só quando a tela chegou à vez de um herói (ou
        ao fim): antes disso, o processador faria a luta andar na frente das animações."""
        if self.estado == "fim":
            return True
        return self.estado in ("escolhendo", "esperando_outro", "aguardando") and not self.fila \
            and self.condutor.esperando()

    def limpar_visuais(self):
        mudou = False
        for lado in (self.lado_herois, self.lado_inimigos):
            for visual in list(lado):
                if visual.some_de_vez():
                    lado.remove(visual)
                    self.visuais.pop(id(visual.lutador), None)
                    mudou = True
        if mudou:
            self.reorganizar()

    def terminar(self):
        self.estado = "fim"
        self.recompensa = self.condutor.recompensa             # (o condutor já deu o XP, o ouro e o loot)
        if self.combate.resultado == "vitoria":
            self.banner = ("Vitória", tema.OURO_CLARO, self.tempo)
            if self.recompensa.niveis:
                self.app.audio.tocar("nivel")
        else:
            self.banner = ("Derrota", tema.SANGUE_CLARO, self.tempo)
        if self.partida is not None:                           # em grupo: cada um conta os abates no seu progresso
            from telas import fluxo
            fluxo.registrar_conquistas(self.app, self.run, getattr(self.recompensa, "abates", []))
            fluxo.avisar_lendarios(self.app, getattr(self.recompensa, "por_jogador", None))
            em_grupo.preparar(self, self.chave_de_seguir(), [0],
                              lambda _: fluxo.depois_do_combate_em_grupo(self.app, self.run), seguir=True,
                              chave_atual=lambda: self.chave_de_seguir() if self.app.partida is not None
                              and self.app.partida.sessao is not None
                              and self.app.partida.sessao.estado.condutor is self.condutor else None)

    def chave_de_seguir(self):
        """A votação "todos viram as recompensas" desta luta (igual em todo computador)."""
        run = self.run
        return f"seguir|combate|{run.regiao_atual}|{run.area}|{run.numero_do_combate}"

    def seguir_em_grupo(self, abrir_bau=False):
        """Em grupo, o Enter da janela do fim é um voto; "I" abre a mochila e volta para cá."""
        em_grupo.votar(self, self.chave_de_seguir(), 0)
        if abrir_bau:
            from telas import fluxo
            fluxo.abrir_inventario(self.app, self.run, ao_voltar=lambda: self.app.trocar(self), aba="mochila")

    # ============================================================
    # AÇÕES DO JOGADOR
    # ============================================================

    def heroi(self):
        return self.combate.atual if self.estado == "escolhendo" else None

    def abrir_menu(self, menu):
        self.menu = menu
        self.pagina = 0
        self.foco = None
        self.focar_ao_desenhar = self.usando_teclado
        if menu != "alvo":
            self.escolha = None

    def opcoes_do_menu(self):
        heroi = self.heroi()
        if self.menu == "habilidades":
            return [(h, n) for h, n in heroi.habilidades()]
        if self.menu == "itens":
            return [(objeto, quantidade) for objeto, quantidade in heroi.inventario.pilhas("consumivel")
                    if objeto.usavel_em_combate]
        return []

    def escolher(self, coisa):
        """Habilidade ou item escolhido: pede o alvo (se precisar) ou já usa."""
        heroi = self.heroi()
        self.escolha = coisa
        validos = self.combate.alvos_validos(heroi, coisa)
        if not validos:
            self.registro.append(("Não há alvos para isso.", tema.TEXTO_FRACO))
            return
        if coisa.escolhe_alvo() and len(validos) > 1:
            self.alvos = validos
            self.indice_alvo = 0
            self.menu = "alvo"
            return
        self.executar(validos[0] if coisa.escolhe_alvo() else None)

    def executar(self, alvo):
        heroi = self.heroi()
        coisa = self.escolha
        acao = "item" if isinstance(coisa, Consumivel) else "golpe"
        estado = self.sessao().estado
        self.mandar(AgirNoCombate(heroi=estado.indice_do(heroi), acao=acao, chave=coisa.chave,
                                  alvo=estado.referencia(alvo)))

    def concentrar(self):
        heroi = self.heroi()
        if heroi is not None:
            self.mandar(AgirNoCombate(heroi=self.indice_do(heroi), acao="concentrar"))

    def voltar(self):
        if self.menu == "alvo":
            self.menu = "itens" if isinstance(self.escolha, Consumivel) else "habilidades"
        elif self.menu in ("habilidades", "itens"):
            self.abrir_menu("principal")
        else:
            self.pausado = True

    # ============================================================
    # TECLADO E MOUSE
    # ============================================================

    def evento(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            self.usando_teclado = False
        if self.pausado:
            self.evento_pausa(e)
            return
        controles = self.app.controles
        if controles.eh(e, "velocidade"):
            self.trocar_velocidade()
            return
        if controles.eh(e, "registro"):
            self.alternar_registro()
            return
        if self.registro_rolavel.evento(e):
            return
        if self.estado == "fim":
            painel_do_loot = getattr(self, "painel_de_recompensas", None)
            if painel_do_loot is not None and painel_do_loot.varios:          # loot de vários jogadores: as abas
                if e.type == pygame.KEYDOWN and e.key == pygame.K_TAB:
                    painel_do_loot.trocar_aba(painel_do_loot.aba + 1)
                    return
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and painel_do_loot.clicar(e.pos):
                    return
            abrir_bau = e.type == pygame.KEYDOWN and e.key == pygame.K_i and self.combate.resultado == "vitoria"
            if controles.eh(e, "confirmar") or controles.eh(e, "acelerar") or abrir_bau or \
                    (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
                if not self.fila and self.partida is not None:
                    self.seguir_em_grupo(abrir_bau)
                elif not self.fila and self.ao_terminar is not None:
                    self.recompensa.abrir_bau = abrir_bau
                    self.ao_terminar(self.recompensa)
            return
        if e.type == pygame.MOUSEBUTTONDOWN:
            self.usando_teclado = False
            if e.button == 3:
                if self.estado == "escolhendo":
                    self.voltar()
                return
            if e.button == 1:
                for botao in self.botoes:
                    if botao.clicar(e.pos):
                        self.app.audio.tocar("clique")
                        return
                if self.estado == "escolhendo" and self.menu == "alvo":
                    for alvo in self.alvos:
                        visual = self.visual(alvo)
                        if visual is not None and visual.caixa().inflate(20, 20).collidepoint(e.pos):
                            self.executar(alvo)
                            return
            return
        if e.type != pygame.KEYDOWN:
            return
        if controles.eh(e, "voltar"):
            if self.estado == "escolhendo" and self.menu != "principal":
                self.voltar()
            else:
                self.pausado = True
                self.indice_pausa = 0
            return
        if self.estado != "escolhendo":
            return
        if self.menu == "alvo":
            self.tecla_no_alvo(e)
            return
        direcao = controles.direcao(e)
        if direcao is not None:
            if not self.mover_foco(*direcao) and direcao[0] and self.menu in ("habilidades", "itens"):
                self.virar_pagina(direcao[0])          # na borda, esquerda/direita trocam de página
            return
        if controles.eh(e, "confirmar") and self.usando_teclado and self.apertar_foco():
            return
        numero = int(e.unicode) if e.unicode and e.unicode.isdigit() else None
        if self.menu == "principal":
            if numero == 1:
                self.abrir_menu("habilidades")
            elif numero == 2:
                self.abrir_menu("itens")
            elif numero == 3:
                self.concentrar()
        elif self.menu in ("habilidades", "itens") and numero and 1 <= numero <= POR_PAGINA:
            opcoes = self.opcoes_do_menu()
            indice = self.pagina * POR_PAGINA + numero - 1
            if indice < len(opcoes) and self.pode_escolher(opcoes[indice][0]):
                self.escolher(opcoes[indice][0])

    def virar_pagina(self, passo):
        paginas = max(1, (len(self.opcoes_do_menu()) + POR_PAGINA - 1) // POR_PAGINA)
        if paginas > 1:
            self.pagina = (self.pagina + passo) % paginas
            self.foco = None
            self.focar_ao_desenhar = True
            self.app.audio.tocar("navegar")

    def tecla_no_alvo(self, e):
        controles = self.app.controles
        if controles.eh(e, "direita") or controles.eh(e, "baixo"):
            self.indice_alvo = (self.indice_alvo + 1) % len(self.alvos)
            self.app.audio.tocar("navegar")
        elif controles.eh(e, "esquerda") or controles.eh(e, "cima"):
            self.indice_alvo = (self.indice_alvo - 1) % len(self.alvos)
            self.app.audio.tocar("navegar")
        elif controles.eh(e, "confirmar"):
            self.executar(self.alvos[self.indice_alvo])

    def alternar_registro(self):
        self.app.opcoes.registro_aberto = not self.app.opcoes.registro_aberto
        self.app.salvar_opcoes()
    def pode_escolher(self, coisa):
        heroi = self.heroi()
        if isinstance(coisa, Consumivel):
            return bool(self.combate.alvos_validos(heroi, coisa))
        return coisa.pode_usar(heroi) and bool(self.combate.alvos_validos(heroi, coisa))

    def opcoes_da_pausa(self):
        def continuar():
            self.pausado = False

        return [("Continuar", continuar), (f"Velocidade: {self.app.velocidade:g}x", self.trocar_velocidade),
                ("Opções", self.abrir_opcoes), ("Sair do jogo", self.app.sair)]

    def trocar_velocidade(self):
        self.app.opcoes.proxima_velocidade_combate()
        self.app.salvar_opcoes()

    def abrir_opcoes(self):
        from telas.opcoes import TelaOpcoes
        self.app.trocar(TelaOpcoes(self.app, lambda: self.app.trocar(self)))

    def evento_pausa(self, e):
        controles = self.app.controles
        opcoes = self.opcoes_da_pausa()
        if controles.eh(e, "voltar"):
            self.pausado = False
        elif controles.eh(e, "cima") or controles.eh(e, "baixo"):
            self.indice_pausa = (self.indice_pausa + (1 if controles.eh(e, "baixo") else -1)) % len(opcoes)
            self.app.audio.tocar("navegar")
        elif controles.eh(e, "confirmar"):
            self.app.audio.tocar("clique")
            opcoes[self.indice_pausa][1]()
        elif e.type == pygame.MOUSEMOTION:
            for i, botao in enumerate(self.botoes):
                if botao.em_cima(e.pos):
                    self.indice_pausa = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for botao in self.botoes:
                if botao.clicar(e.pos):
                    return

    # ============================================================
    # DESENHO
    # ============================================================

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.em_destaque = None
        tremor = 0
        if self.tempo < self.tremor_ate:
            tremor = 4 if int(self.tempo * 60) % 2 else -4
        self.cenario.desenhar(tela, tremor // 2)
        self.ambiente.desenhar_brilho(tela)
        self.desenhar_trono(tela)

        destacados = self.destaques()
        visuais = self.todos_os_visuais()
        for visual in visuais:
            visual.oculto = self.combate.oculto(visual.lutador)            # no escuro: silhueta e olhos
            self.ambiente.desenhar_poca_ou_sombra(visual, tela)
        for visual in visuais:
            self.ambiente.desenhar_lutador(tela, visual, destacados.get(id(visual)))   # na água, afunda
        self.efeitos.desenhar(tela)
        self.cenario.desenhar_frente(tela)
        self.ambiente.desenhar_escuro(tela, self.visual)
        for visual in visuais:                                              # os olhos dos ocultos brilham no breu
            if visual.oculto and visual.lutador.esta_vivo() and visual.alfa > 0:
                visual.desenhar_olhos(tela)
        tela.blit(vinheta(tela.get_size(), 170), (0, 0))
        no_topo = self.chefes_no_topo()
        topo_minimo = 84 + (30 + 46 * len(no_topo) if no_topo else 0)
        opcoes = {}
        for visual in visuais:
            chefe = visual.inimigo and isinstance(ia_do(visual.lutador), IAChefe)
            opcoes[id(visual)] = dict(mostrar_nome=visual.inimigo, mostrar_energia=chefe,
                                      barra_na_cabeca=visual not in no_topo)
        # barras de lutadores vizinhos não se cruzam (nomes e números legíveis)
        posicoes = separar_barras([(v, v.rect_da_barra(tela, topo_minimo),
                                    lambda r, v=v: v.bloco_da_barra(r, **opcoes[id(v)]))
                                   for v in visuais if v.tem_barra()], topo_minimo)
        for visual in visuais:
            visual.desenhar_barra(tela, topo_minimo=topo_minimo, rect=posicoes.get(id(visual)), **opcoes[id(visual)])
            if opcoes[id(visual)]["mostrar_energia"] and visual.lutador.esta_vivo() and not isinstance(visual, VisualRoda) \
                    and not getattr(visual, "fixo", False):
                self.desenhar_intencao(tela, visual)     # (a Rainha e o Rei no trono: a intenção fica no painel deles)
        self.desenhar_barras_de_chefe(tela, no_topo)
        self.desenhar_seta_da_vez(tela)
        self.desenhar_marcador_de_alvo(tela)

        self.desenhar_fila_de_turnos(tela)
        self.desenhar_cabecalho(tela)
        dica = self.ambiente.desenhar_painel(tela, 14, 56, self.mouse)
        if dica is not None and self.dica_pendente is None and not self.usando_teclado:
            self.dica_pendente = dica
        self.desenhar_edito(tela)
        self.desenhar_painel_do_trono(tela, 56 + (128 if self.edito_ativo() else 0))     # (embaixo do pergaminho)
        self.desenhar_painel_da_roda(tela, 56 + 32 * len(self.combate.ambientes))
        self.desenhar_painel(tela)
        self.desenhar_faixa_de_descricao(tela)
        self.desenhar_banners(tela)
        if self.proclamacao is not None and self.proclamacao.ativa(self.tempo):
            self.proclamacao.desenhar(tela, self.tempo)
        if self.focar_ao_desenhar:
            self.focar_primeiro()
            self.focar_ao_desenhar = False
        self.preparar_dica()
        self.terminar_desenho(tela)
        if self.estado == "fim" and not self.fila:
            self.desenhar_fim(tela)
        if self.pausado:
            self.desenhar_pausa(tela)

    def destaques(self):
        """Contorno dourado em quem age; no menu de alvo, vermelho no alvo e os outros apagados."""
        destaques = {}
        atual = self.visual(self.combate.atual)
        if atual is not None and self.estado == "escolhendo":
            destaques[id(atual)] = "vez"
        if self.estado == "escolhendo" and self.menu == "alvo":
            for visual in self.lado_herois + self.lado_inimigos:
                if visual.lutador not in self.alvos and visual is not atual and visual.lutador.esta_vivo():
                    destaques[id(visual)] = "apagado"
            for i, alvo in enumerate(self.alvos):
                visual = self.visual(alvo)
                if visual is not None:
                    sob_mouse = not self.usando_teclado and visual.caixa().inflate(20, 20).collidepoint(self.mouse)
                    if sob_mouse:
                        self.indice_alvo = i              # o mouse também escolhe o alvo marcado
                    destaques[id(visual)] = "alvo" if (i == self.indice_alvo or sob_mouse) else None
        return destaques

    def alvo_marcado(self):
        if self.estado == "escolhendo" and self.menu == "alvo" and self.alvos:
            return self.alvos[self.indice_alvo % len(self.alvos)]
        return None

    def desenhar_marcador_de_alvo(self, tela):
        """Seta vermelha balançando em cima do alvo escolhido."""
        visual = self.visual(self.alvo_marcado())
        if visual is None:
            return
        x = visual.caixa().centerx
        y = max(92, visual.topo_da_barra - 10) - int(5 * abs(math.sin(self.tempo * 6)))
        pontos = [(x - 11, y - 14), (x + 11, y - 14), (x, y)]
        pygame.draw.polygon(tela, (10, 4, 6), [(px, py + 2) for px, py in pontos])
        pygame.draw.polygon(tela, tema.SANGUE_CLARO, pontos)
        pygame.draw.polygon(tela, tema.OURO_CLARO, pontos, 2)
    def desenhar_seta_da_vez(self, tela):
        visual = self.visual(self.combate.atual)
        if visual is None or not visual.lutador.esta_vivo():
            return
        x = visual.caixa().centerx
        y = getattr(visual, "topo_da_barra", visual.caixa().top - 40) - 12   # logo acima do nome/barra (espaço reservado)
        if visual.inimigo and isinstance(ia_do(visual.lutador), IAChefe):
            y = visual.topo_da_barra - 34                  # acima do "Próximo: ..." dos chefes
        y = max(70, y) + int(4 * abs(math.sin(self.tempo * 5)))
        losango(tela, (x, y), 7, tema.OURO_CLARO if visual.lutador.lado == "herois" else tema.SANGUE_CLARO)

    def chefes_no_topo(self):
        """Os chefes vivos (até 2): ganham a barra grande no topo da tela."""
        return [v for v in self.lado_inimigos if v.lutador.esta_vivo() and v.alfa >= 120 and not getattr(v, "fixo", False)
                and getattr(v.lutador, "categoria", "") == "chefe" and not v.lutador.eh_invocacao][:2]

    def desenhar_barras_de_chefe(self, tela, chefes):
        """Barra de chefe no topo, embaixo da fila de turnos: o nome (que muda com a forma, ex.: o Dragão do
        Eclipse) e uma barra larga, com a parte 'atrasada' descendo devagar."""
        for i, visual in enumerate(chefes):
            lutador = visual.lutador
            maximo = lutador.vida_maxima
            rect = pygame.Rect(0, 0, 560, 12)
            rect.midtop = (tema.LARGURA // 2, 128 + i * 46)             # o nome fica abaixo do "Rodada N" da fila
            texto(tela, lutador.nome, tema.normal(), tema.OURO_CLARO, (rect.centerx, rect.top - 4), "midbottom")
            barra(tela, rect, lutador.vida / maximo, tema.VIDA, visual.vida_mostrada / maximo, marcas=10)
            texto(tela, f"{lutador.vida}/{maximo}", tema.mini(), tema.TEXTO, (rect.right + 8, rect.centery), "midleft")
            for lado in (-1, 1):
                losango(tela, (rect.centerx + lado * (rect.width // 2 + 2), rect.centery), 5, tema.SANGUE_CLARO)

    # ---------------- Édito Real (Rei dos Ratos) ----------------
    def edito_ativo(self):
        """O Édito Real em vigor: (quem proclamou, status) ou None."""
        for inimigo in self.combate.inimigos:
            for status in inimigo.status.values() if inimigo.esta_vivo() else ():
                if dados_do_status(status.chave).get("classe") == "edito":
                    return inimigo, status
        return None

    def desenhar_edito(self, tela):
        """O pergaminho do Édito Real no alto, à direita: a lei, o castigo e quantos turnos do Rei faltam."""
        ativo = self.edito_ativo()
        if ativo is None or (self.proclamacao is not None and not self.proclamacao.chegou(self.tempo)):
            return 56                                                   # (a proclamação ainda está voando para cá)
        _, status = ativo
        dados = dados_do_status(status.chave)
        rect = pygame.Rect(tema.LARGURA - 276, 56, 262, 122)
        papel, sombra, tinta = (228, 206, 162), (178, 148, 104), (64, 34, 20)
        corpo = rect.inflate(-14, -14)
        pygame.draw.rect(tela, (18, 10, 8), corpo.inflate(4, 4))
        pygame.draw.rect(tela, papel, corpo)
        for x in range(corpo.left + 4, corpo.right - 4, 11):           # papel gasto
            pygame.draw.line(tela, sombra, (x, corpo.bottom - 3), (x + 5, corpo.bottom - 3))
            pygame.draw.line(tela, sombra, (x + 3, corpo.top + 3), (x + 6, corpo.top + 3))
        for y in (rect.top, rect.bottom - 12):                         # os dois rolos
            rolo = pygame.Rect(rect.left, y, rect.width, 12)
            pygame.draw.rect(tela, (18, 10, 8), rolo.inflate(2, 2), border_radius=6)
            pygame.draw.rect(tela, sombra, rolo, border_radius=6)
            pygame.draw.line(tela, papel, (rolo.left + 6, rolo.top + 3), (rolo.right - 6, rolo.top + 3))
        selo = (corpo.right - 16, corpo.bottom - 18)
        pygame.draw.circle(tela, (100, 12, 18), selo, 11)
        pygame.draw.circle(tela, (176, 32, 40), selo, 8)
        anotar("painel", rect, tela)
        texto(tela, "ÉDITO REAL", tema.mini(), (140, 28, 28), (corpo.centerx, corpo.top + 4), "midtop", contorno=False)
        linha_que_cabe(tela, status.nome, tema.normal(), tinta, (corpo.centerx, corpo.top + 20), corpo.width - 16,
                       "midtop", contorno=False)
        linha_que_cabe(tela, dados.get("lei", ""), tema.mini(), (96, 62, 36), (corpo.centerx, corpo.top + 46),
                       corpo.width - 16, "midtop", contorno=False)
        castigo = round(regras()["editos"]["castigo"] * 100)
        faltam = f"Vale por mais {status.duracao} turno{'s' if status.duracao != 1 else ''} do Rei"
        linha_que_cabe(tela, f"Desobedecer: -{castigo}% da vida", tema.mini(), (140, 28, 28),
                       (corpo.left + 8, corpo.top + 62), corpo.width - 40, contorno=False)
        linha_que_cabe(tela, faltam, tema.mini(), (96, 62, 36), (corpo.left + 8, corpo.top + 78), corpo.width - 40,
                       contorno=False)
        if rect.collidepoint(self.mouse):
            self.dica_pendente = (f"Édito Real: {status.nome}", status.descricao)
        return rect.bottom + 6

    # ---------------- Rainha dos Ratos e o trono ----------------
    def desenhar_trono(self, tela):
        """O trono de ratos e ouro do Salão do Trono (sprite animado no "trono" do cenário; na água, a base afunda)
        e o Rei dos Ratos sentado nele enquanto a Rainha luta (Combate.de_volta)."""
        trono = self.cenario.config.get("trono", {})
        if "base" in trono and self.sprites.existe(SPRITE_DO_TRONO):
            x, y = self.cenario.na_tela(trono["base"])
            quadro = int(self.tempo * 5) % self.sprites.quadros_de(SPRITE_DO_TRONO, "parado")
            imagem = self.sprites.quadro(SPRITE_DO_TRONO, "parado", quadro, 2)
            ax, ay = self.sprites.ancora(SPRITE_DO_TRONO, 2)
            area = imagem.get_rect(topleft=(x - ax, y - ay))
            agua = self.ambiente.nivel_da_agua()                           # a água encosta no estrado (alta: sobe)
            self.ambiente.desenhar_reflexo(tela, imagem, area.x, y + 36 - round(max(0.0, agua - 2) * 30),
                                           (SPRITE_DO_TRONO, quadro))
            self.ambiente.desenhar_na_agua(tela, lambda superficie: superficie.blit(imagem, area), area, y,
                                           area.width * 0.8, x, fator=0.45, anel=False)   # lá no fundo afunda menos
        if self.corrida is not None:                                    # o Rei ainda correndo para lá
            self.corrida.desenhar(tela, self.ambiente)
            return
        volta = self.no_trono
        if not volta or not self.sprites.existe(volta["chave"]):
            return
        nome = volta["chave"]
        quadro = int(self.tempo * 3) % self.sprites.quadros_de(nome, "sentado")
        imagem = self.sprites.quadro(nome, "sentado", quadro, 2, True)
        if any(isinstance(v, VisualRoda) for v in self.lado_inimigos):       # lá no fundo, esperando: mais escuro
            imagem = imagem.copy()
            imagem.fill((150, 138, 162, 255), special_flags=pygame.BLEND_RGBA_MULT)
        ax, ay = self.sprites.ancora(nome, 2, True)
        tela.blit(imagem, (self.trono_pes[0] - ax, self.trono_pes[1] - ay))

    def ao_trono(self, lutador, visual):
        """O Rei dos Ratos fugiu para o trono do cenário (Combate.proxima_parte traz o trono dele): em vez de sumir, ele
        corre até lá (CorridaAoTrono) e fica sentado. Devolve True se a corrida começou."""
        parte = self.combate.proxima_parte or {}
        trono = self.cenario.config.get("trono", {})
        if (parte.get("trono", {}).get("chave") != getattr(lutador, "chave", None) or "base" not in trono
                or not self.sprites.tem_animacao(visual.nome_sprite, "correr") or visual not in self.lado_inimigos):
            return False
        base = self.cenario.na_tela(trono["base"])
        lado = 1 if visual.x >= base[0] else -1
        self.lado_inimigos.remove(visual)                               # sai da fileira (e da barra de vida)
        self.corrida = CorridaAoTrono(visual, (base[0] + lado * 70, base[1] + 40), self.trono_pes)
        self.reorganizar()
        return True

    def desenhar_painel_da_roda(self, tela, y):
        """No alto à esquerda (embaixo do painel do ambiente): quem está na frente da roda da Rainha, quem vem no
        próximo giro, se o nó está exposto e quantos golpes tem a Roda Furiosa."""
        visual = next((v for v in self.lado_inimigos if isinstance(v, VisualRoda) and v.lutador.esta_vivo()), None)
        if visual is None:
            return
        no = visual.lutador
        passiva = next(p for p in no.passivas if hasattr(p, "proximo_giro"))
        rect = pygame.Rect(14, y, 330, 112)                              # (à esquerda da barra do chefe)
        painel(tela, rect, "pedra")
        texto(tela, "A Roda da Rainha", tema.pequena(), tema.OURO_CLARO, (rect.x + 12, rect.y + 6))
        nomes = lambda ratos: ", ".join(r.nome for r in ratos) or "—"     # noqa: E731
        linhas = [(f"Frente: {nomes(passiva.frente(no))}", tema.TEXTO),
                  (f"Depois: {nomes(passiva.proximo_giro(no))}", tema.TEXTO_FRACO)]
        exposto = not no.tem_status("no_fechado")
        linhas.append(("Nó EXPOSTO: fere a roda toda!" if exposto else "Nó fechado (abre na metade)",
                       tema.SANGUE_CLARO if exposto else tema.TEXTO_APAGADO))
        roda_furiosa = next((g for g, _ in no.habilidades() if g.chave == "roda_furiosa"), None)
        if roda_furiosa is not None:
            golpes = 1 + int(no.caidos() * roda_furiosa.efeitos[0].dados.get("golpes_por_caido", 0))
            linhas.append((f"Roda Furiosa: {golpes} golpe{'s' if golpes > 1 else ''} no grupo", (236, 170, 150)))
        for i, (conteudo, cor) in enumerate(linhas):
            linha_que_cabe(tela, conteudo, tema.mini(), cor, (rect.x + 12, rect.y + 30 + i * 19), rect.width - 24)
        if rect.collidepoint(self.mouse):
            self.dica_pendente = (passiva.nome or "A Roda", passiva.descricao)

    def desenhar_painel_do_trono(self, tela, y):
        """À direita, embaixo do pergaminho do Édito (A Corte Completa): o Rei governa do trono sem poder ser atingido,
        o que ele fará na vez dele e quando desce."""
        visual = next((v for v in self.lado_inimigos if getattr(v, "fixo", False) and v.lutador.esta_vivo()), None)
        if visual is None:
            return
        rei = visual.lutador
        passiva = next((p for p in rei.passivas if hasattr(p, "descer")), None)
        dados = passiva.dados if passiva is not None else {}
        rect = pygame.Rect(tema.LARGURA - 276, y, 262, 96)
        painel(tela, rect, "pedra")
        texto(tela, "O Rei no Trono", tema.pequena(), tema.OURO_CLARO, (rect.x + 12, rect.y + 6))
        intencao = ia_do(rei).intencao(rei, self.combate)
        linhas = [("Intocável: governa do trono", tema.TEXTO),
                  (f"Próximo: {intencao.nome if intencao else '—'}", (250, 170, 140)),
                  (dados.get("quando_desce", "Desce quando a Rainha cair"), tema.TEXTO_FRACO)]
        for i, (conteudo, cor) in enumerate(linhas):
            linha_que_cabe(tela, conteudo, tema.mini(), cor, (rect.x + 12, rect.y + 30 + i * 19), rect.width - 24)
        if rect.collidepoint(self.mouse) and passiva is not None:
            self.dica_pendente = (passiva.nome or "O Rei no Trono", passiva.descricao)

    def proibido_pelo_edito(self, coisa, alvo=None):
        """Usar isto (no alvo, se houver) desobedece um Édito Real? Golpes de área contam os alvos todos."""
        heroi = self.heroi()
        if heroi is None:
            return False
        tipo = "item" if isinstance(coisa, Consumivel) else "habilidade"
        if alvo is not None:
            alvos = [alvo]
        else:
            alvos = [] if coisa.escolhe_alvo() else self.combate.alvos_validos(heroi, coisa)
        return self.combate.proibicao(heroi, tipo, coisa, alvos) is not None

    def desenhar_intencao(self, tela, visual):
        intencao = ia_do(visual.lutador).intencao(visual.lutador, self.combate)
        if intencao is None:
            return
        y = max(84, visual.topo_da_barra - 2)
        texto(tela, f"Próximo: {intencao.nome}", tema.pequena(), (250, 170, 140), (visual.caixa().centerx, y), "midbottom")

    def retrato(self, lutador, tamanho=40):
        """Recorte da cabeça/tronco do sprite para a fila de turnos."""
        visual = self.visual(lutador)
        nome = visual.nome_sprite if visual else lutador.sprite
        chave = ("retrato", nome, tamanho, lutador.lado)
        cache = self.sprites._cache
        if chave not in cache:
            imagem = self.sprites.quadro(nome, "parado", 0, 1, lutador.lado == "inimigos",
                                         visual.tinta if visual else None)
            caixa = imagem.get_bounding_rect()
            lado = min(caixa.width, max(18, int(caixa.height * 0.55)))
            recorte = pygame.Rect(0, 0, lado, lado)
            recorte.midtop = (caixa.centerx, caixa.top)
            recorte = recorte.clip(imagem.get_rect())
            pedaco = imagem.subsurface(recorte)
            maior = max(recorte.width, recorte.height)
            if maior > tamanho:
                fator = tamanho / maior                      # grande demais: diminui para caber
                novo = (max(1, int(recorte.width * fator)), max(1, int(recorte.height * fator)))
            else:
                vezes = max(1, tamanho // maior)
                novo = (recorte.width * vezes, recorte.height * vezes)
            cache[chave] = pygame.transform.scale(pedaco, novo)
        return cache[chave]

    def desenhar_fila_de_turnos(self, tela):
        combate = self.combate
        ordem = []
        if combate.atual is not None and combate.atual.esta_vivo():
            ordem.append(combate.atual)
        ordem += [l for l in combate.proximos() if l not in ordem]
        ordem = ordem[:14]
        tamanho = 46
        largura = len(ordem) * (tamanho + 6) + 6
        x = (tema.LARGURA - largura) // 2
        self.rect_da_fila = pygame.Rect(x - 8, 6, largura + 16, tamanho + 18)
        if ordem:
            painel(tela, self.rect_da_fila, "pedra")
        for i, lutador in enumerate(ordem):
            rect = pygame.Rect(x + 6 + i * (tamanho + 6), 14, tamanho, tamanho)
            estilo = "ouro" if i == 0 else ("sangue" if lutador.lado == "inimigos" else "ferro")
            painel(tela, rect, estilo)
            imagem = self.retrato(lutador, tamanho - 10)
            tela.blit(imagem, imagem.get_rect(center=rect.center))
            if rect.collidepoint(self.mouse):
                self.dica_pendente = (lutador.nome, f"Iniciativa {getattr(lutador, 'iniciativa_rolada', '?')}")
        texto(tela, f"Rodada {combate.rodada}", tema.mini(), tema.TEXTO_FRACO,
              (self.rect_da_fila.centerx, self.rect_da_fila.bottom + 2), "midtop")

    def desenhar_cabecalho(self, tela):
        """Cantos de cima: fase e encontro à esquerda, teclas à direita (cada um na sua parte, sem tocar a fila)."""
        fila = getattr(self, "rect_da_fila", pygame.Rect(tema.LARGURA // 2, 6, 0, 64))
        esquerda = max(120, fila.left - 28)
        direita = max(120, tema.LARGURA - fila.right - 28)
        regiao = self.run.regiao
        zona = self.run.zona()                          # fases com zonas (Reino dos Ratos): "Reino dos Ratos · Mercado Roedor"
        nome = f"{regiao.nome} · {zona['nome']}" if zona else regiao.nome
        linha_que_cabe(tela, nome, tema.pequena(), tema.TEXTO_TITULO, (14, 12), esquerda)
        ameaca = f" · Ameaça {self.run.ameaca}" if getattr(self.run, "ameaca", 0) else ""
        linha_que_cabe(tela, f"Área {self.run.area}/{self.run.areas_da_regiao()} · {self.encontro.nome}{ameaca}", tema.mini(),
                       tema.TEXTO_FRACO, (14, 34), esquerda)
        linha_que_cabe(tela, f"Velocidade {self.app.velocidade:g}x (V)", tema.mini(), tema.TEXTO_APAGADO,
                       (tema.LARGURA - 14, 12), direita, "topright")
        linha_que_cabe(tela, "ESPAÇO acelera · ESC pausa", tema.mini(), tema.TEXTO_APAGADO, (tema.LARGURA - 14, 30),
                       direita, "topright")

    # ---------------- painel de baixo ----------------
    def desenhar_painel(self, tela):
        altura = tema.ALTURA - PAINEL_Y - 6
        # o meio é o mais largo: os nomes das habilidades precisam caber nos botões
        esquerda = pygame.Rect(6, PAINEL_Y, 340, altura)
        largura_registro = 260 if self.app.opcoes.registro_aberto else 40
        direita = pygame.Rect(tema.LARGURA - 6 - largura_registro, PAINEL_Y, largura_registro, altura)
        self.meio = pygame.Rect(esquerda.right + 6, PAINEL_Y, direita.x - esquerda.right - 12, altura)
        self.desenhar_cartao(tela, esquerda)
        self.desenhar_acoes(tela, self.meio)
        self.desenhar_registro(tela, direita)

    def desenhar_cartao(self, tela, rect):
        painel(tela, rect, "ferro")
        lutador = self.combate.atual
        if lutador is None:
            texto(tela, "Preparando...", tema.normal(), tema.TEXTO_FRACO, rect.center, "center")
            return
        retrato = self.retrato(lutador, 76)
        moldura_retrato = pygame.Rect(rect.x + 12, rect.y + 12, 86, 86)
        painel(tela, moldura_retrato, "sangue" if lutador.lado == "inimigos" else "osso")
        tela.blit(retrato, retrato.get_rect(center=moldura_retrato.center))
        x = moldura_retrato.right + 12
        nome_classe = lutador.nome_da_classe() if hasattr(lutador, "nome_da_classe") else lutador.categoria.replace("_", "-")
        nivel = f"  nv {lutador.nivel}" if hasattr(lutador, "nivel") else ""
        linha_que_cabe(tela, lutador.nome, tema.normal(), tema.TEXTO_TITULO, (x, rect.y + 8), rect.right - x - 12)
        dono = getattr(lutador, "jogador", None) if self.partida is not None and lutador.lado == "herois" else None
        if dono is not None:                                # em grupo: de quem é o herói, na cor do jogador
            linha_que_cabe(tela, f"{nome_classe.capitalize()}{nivel} · ", tema.mini(), tema.TEXTO_FRACO,
                           (x, rect.y + 32), rect.right - x - 12)
            deslocamento = tema.mini().size(f"{nome_classe.capitalize()}{nivel} · ")[0]
            linha_que_cabe(tela, dono.nome, tema.mini(), dono.cor or tema.TEXTO, (x + deslocamento, rect.y + 32),
                           max(10, rect.right - x - 12 - deslocamento))
        else:
            linha_que_cabe(tela, nome_classe.capitalize() + nivel, tema.mini(), tema.TEXTO_FRACO, (x, rect.y + 32),
                           rect.right - x - 12)
        visual = self.visual(lutador)
        largura = rect.right - x - 14
        coluna = 66                               # largura dos rótulos "Vida" e "Energia"
        texto(tela, "Vida", tema.mini(), tema.TEXTO_FRACO, (x, rect.y + 50))
        self.barra_vida.cor = tema.VIDA if lutador.lado == "inimigos" else tema.VIDA_HEROI
        self.barra_vida.desenhar(tela, (x + coluna, rect.y + 52, largura - coluna, 10), lutador.vida,
                                 lutador.vida_maxima, visual.vida_mostrada if visual else None)
        texto(tela, "Energia", tema.mini(), tema.ENERGIA, (x, rect.y + 70))
        self.barra_energia.marcas = max(1, min(lutador.energia_maxima, 10))
        self.barra_energia.desenhar(tela, (x + coluna, rect.y + 72, largura - coluna, 10), lutador.energia,
                                    min(lutador.energia_maxima, 10))
        xi = rect.x + 14
        for chave, status in lutador.status.items():
            icone = icone_status(chave)
            tela.blit(icone, (xi, rect.bottom - 26))
            area = pygame.Rect(xi, rect.bottom - 26, icone.get_width(), icone.get_height())
            if area.collidepoint(self.mouse):
                self.dica_pendente = (status.rotulo(), status.descricao)
            xi += icone.get_width() + 4

    def botao_de_acao(self, rect, rotulo, acao, atalho, ativo=True, subtexto=None, coisa=None, nivel=1):
        """Registra um botão do menu; o que está sob o foco/mouse vai para a faixa de descrição."""
        botao = self.botao(Botao(rect, rotulo, acao, atalho, ativo, subtexto=subtexto))
        if botao.focado or (not self.usando_teclado and botao.em_cima(self.mouse)):
            self.em_destaque = (coisa if coisa is not None else rotulo, nivel)
        return botao

    def desenhar_acoes(self, tela, rect):
        painel(tela, rect, "ferro")
        heroi = self.heroi()
        if heroi is None:
            atual = self.combate.atual
            mensagem, cor = ("..." if atual is None else f"Vez de {atual.nome}"), tema.TEXTO_FRACO
            if self.estado == "fim":
                mensagem = "Fim do combate"
            elif self.estado == "esperando_outro" and atual is not None:      # em grupo: o herói de outro jogador
                dono = getattr(atual, "jogador", None)
                restante = em_grupo.configuracao()["tempo_da_vez"] - (self.tempo - self.esperando_desde)
                caiu = dono is not None and dono.id in self.partida.desconectados
                mensagem = f"{dono.nome if dono else '?'} escolhendo por {atual.nome}..." + \
                           (" (a IA joga)" if caiu else f"  {max(0, int(restante))} s")
                cor = dono.cor if dono is not None and dono.cor else tema.TEXTO
            elif self.estado == "aguardando":
                mensagem = "Esperando o host..."
            linha_que_cabe(tela, mensagem, tema.media(), cor, rect.center, rect.width - 24, "center")
            return
        if self.menu == "principal":
            linha_que_cabe(tela, f"O que {heroi.nome} vai fazer?", tema.normal(), tema.TEXTO_TITULO,
                           (rect.centerx, rect.y + 10), rect.width - 24, "midtop")
            largura = (rect.width - 48) // 3
            itens = len([o for o, _ in heroi.inventario.pilhas("consumivel") if o.usavel_em_combate])
            opcoes = [("Lutar", "habilidades", lambda: self.abrir_menu("habilidades"), True),
                      ("Itens", f"{itens} tipo(s)", lambda: self.abrir_menu("itens"), itens > 0),
                      ("Concentrar", "+2 energia", self.concentrar, True)]
            for i, (nome, sub, acao, ativo) in enumerate(opcoes):
                self.botao_de_acao((rect.x + 12 + i * (largura + 12), rect.y + 44, largura, 62), nome, acao, str(i + 1),
                                   ativo, sub)
            return
        if self.menu == "alvo":
            alvo = self.alvo_marcado()
            linha_que_cabe(tela, f"{self.escolha.nome}: escolha o alvo", tema.normal(), tema.TEXTO_TITULO,
                           (rect.centerx, rect.y + 12), rect.width - 24, "midtop")
            proibido = self.proibido_pelo_edito(self.escolha, alvo)       # ex.: "Proibido Atacar o Rei"
            linha_que_cabe(tela, f"Alvo: {alvo.nome}   Vida {alvo.vida}/{alvo.vida_maxima}"
                           + ("   · Proibido pelo Édito!" if proibido else ""), tema.normal(),
                           tema.SANGUE_CLARO if proibido else tema.TEXTO, (rect.x + 20, rect.y + 52), rect.width - 40)
            linha_que_cabe(tela, "Setas trocam o alvo · Enter confirma · ou clique no alvo", tema.pequena(),
                           tema.TEXTO_FRACO, (rect.x + 20, rect.y + 84), rect.width - 168)
            self.botoes.append(Botao((rect.right - 128, rect.bottom - 42, 116, 32), "Voltar (ESC)", self.voltar))
            self.botoes[-1].desenhar(tela, self.mouse)
            return

        opcoes = self.opcoes_do_menu()
        paginas = max(1, (len(opcoes) + POR_PAGINA - 1) // POR_PAGINA)
        self.pagina = min(self.pagina, paginas - 1)
        visiveis = opcoes[self.pagina * POR_PAGINA:(self.pagina + 1) * POR_PAGINA]
        colunas, altura = 3, 48
        largura = (rect.width - 16 - (colunas - 1) * 6) // colunas
        for i, (coisa, valor) in enumerate(visiveis):
            linha, coluna = divmod(i, colunas)
            area = (rect.x + 8 + coluna * (largura + 6), rect.y + 12 + linha * (altura + 6), largura, altura)
            if isinstance(coisa, Consumivel):
                sub, nivel = f"x{valor}", 1
            else:
                sub, nivel = f"{coisa.texto_custo()} · nv {valor}", valor
                espera = self.heroi().recarga_de(coisa.chave)
                if espera:
                    sub = f"recarga: {espera} turno(s)"
            if self.proibido_pelo_edito(coisa):                     # Édito Real: dá para usar, mas custa caro
                sub = "Proibido pelo Édito!"
            self.botao_de_acao(area, coisa.nome, (lambda c=coisa: self.escolher(c)), str(i + 1), self.pode_escolher(coisa),
                               sub, coisa, nivel)
        if paginas > 1:
            texto(tela, f"página {self.pagina + 1}/{paginas}  (esquerda/direita na borda)", tema.mini(),
                  tema.TEXTO_FRACO, (rect.centerx, rect.bottom - 6), "midbottom")
        if not opcoes:
            texto(tela, "Nada para usar.", tema.normal(), tema.TEXTO_FRACO, rect.center, "center")

    DESCRICAO_DO_MENU = {"Lutar": "Escolher um golpe.", "Itens": "Usar um item da mochila (não gasta energia).",
                         "Concentrar": "Ganha +2 de energia e passa a vez."}

    def linhas_da_descricao(self):
        """Seções sobre o que está em destaque: nome e nível / efeito / custo · alvo (e o aviso, se não der)."""
        from roguelike.golpes import NOMES_DE_ALVO
        heroi = self.heroi()
        if heroi is None:
            return []
        if self.menu == "alvo" and self.escolha is not None:
            alvo = self.alvo_marcado()
            coisa = self.escolha
            nivel = heroi.nivel_da(coisa.chave) if not isinstance(coisa, Consumivel) else 1
            titulo = f"{coisa.nome}  >  {alvo.nome} ({alvo.vida}/{alvo.vida_maxima})"
        elif self.em_destaque is None:
            return []
        else:
            coisa, nivel = self.em_destaque
            if isinstance(coisa, str):
                return [(coisa, tema.TEXTO_TITULO), (self.DESCRICAO_DO_MENU.get(coisa, ""), tema.TEXTO)]
            titulo = coisa.nome + (f" (nível {nivel})" if not isinstance(coisa, Consumivel) else "")
        resumo = coisa.resumo(nivel) if not isinstance(coisa, Consumivel) else coisa.resumo()
        custo = coisa.texto_custo() if not isinstance(coisa, Consumivel) else "gasta o item"
        secoes = [(titulo, tema.TEXTO_TITULO), (resumo or coisa.descricao, tema.TEXTO),
                  (f"{custo}  ·  {NOMES_DE_ALVO.get(coisa.alvo, coisa.alvo)}", tema.ENERGIA_CLARA)]
        if self.menu != "alvo" and not self.pode_escolher(coisa):
            falta = "sem alvo válido" if isinstance(coisa, Consumivel) or coisa.pode_usar(heroi) else "energia insuficiente"
            if not isinstance(coisa, Consumivel) and heroi.recarga_de(coisa.chave):
                falta = f"em recarga por mais {heroi.recarga_de(coisa.chave)} turno(s)"
            secoes.append((f"Não dá para usar agora: {falta}.", tema.SANGUE_CLARO))
        return secoes

    def desenhar_faixa_de_descricao(self, tela):
        """Caixa logo acima do painel, na largura do menu: cada seção numa linha, quebrando dentro da caixa."""
        secoes = self.linhas_da_descricao()
        if not secoes:
            return
        caixa = CaixaTexto(pygame.Rect(self.meio.x, 0, self.meio.width, 140), tema.pequena(), alinhamento="centro",
                           padding=8, maximo_linhas=6)
        caixa.rect.height = caixa.altura_para(secoes)
        caixa.rect.bottom = PAINEL_Y - 4
        painel(tela, caixa.rect, "pedra")
        caixa.desenhar(tela, secoes)

    def desenhar_registro(self, tela, rect):
        """Registro da luta. Recolhido (tecla L ou clique), vira uma aba fina e o menu ganha espaço."""
        if not self.app.opcoes.registro_aberto:
            botao = Botao(rect, "", self.alternar_registro, estilo="ferro")
            botao.focavel = False                 # o teclado usa a tecla L
            self.botao(botao)
            rotulo = pygame.transform.rotate(tema.mini().render("REGISTRO (L)", tema.SUAVE, tema.TEXTO_FRACO), 90)
            tela.blit(rotulo, rotulo.get_rect(center=botao.rect.center))
            return
        painel(tela, rect, "ferro")
        # o texto não passa por baixo do botão de recolher: a área termina antes dele
        self.registro_rolavel.desenhar(tela, pygame.Rect(rect.x, rect.y, rect.width - 26, rect.height))
        recolher = Botao((rect.right - 34, rect.y + 6, 28, 24), "-", self.alternar_registro,
                         dica=("Recolher o registro", "Tecla L: mostra ou esconde o registro da luta."))
        recolher.focavel = False
        self.botao(recolher)
    # ---------------- sobreposições ----------------
    def desenhar_banners(self, tela):
        if self.banner is not None and self.estado != "fim":
            conteudo, cor, inicio = self.banner
            passado = self.tempo - inicio
            if passado < 1.0:
                alfa = int(255 * min(1, (1 - passado) * 3))
                texto(tela, conteudo, tema.grande(), cor, (tema.LARGURA // 2, 150), "center", alfa=alfa)
        banner = getattr(self, "banner_habilidade", None)
        if banner is not None and self.tempo - banner[1] < 1.1:
            alfa = int(255 * min(1, (1.1 - (self.tempo - banner[1])) * 3))
            chefes = len(self.chefes_no_topo())                         # (com chefe, fica embaixo da barra grande)
            y = 112 if not chefes else 128 + 46 * chefes + 6
            texto(tela, banner[0], tema.media(), tema.TEXTO_TITULO, (tema.LARGURA // 2, y), "center", alfa=alfa)

    def preparar_dica(self):
        """Escolhe a dica do quadro (ícone de status, retrato da fila ou lutador sob o mouse)."""
        dica = self.dica_pendente
        self.dica_pendente = None
        if dica is None and self.estado != "fim" and not self.usando_teclado:
            for visual in reversed(self.todos_os_visuais()):
                for area, status in visual.areas_de_status:
                    if area.collidepoint(self.mouse):
                        dica = (status.rotulo(), status.descricao)
                        break
                if dica is None and visual.alfa > 100 and visual.caixa().collidepoint(self.mouse):
                    if visual.oculto:                       # no escuro, ninguém sabe o que é
                        dica = ("???", "Algo se mexe no escuro. Sem luz, não dá para mirar nele "
                                       "(golpes em área acertam).")
                    else:
                        dica = self.dica_do_lutador(visual.lutador)
                if dica is not None:
                    break
        if dica is not None:
            self.dica = dica
            self.posicao_da_dica = self.mouse
    def dica_do_lutador(self, lutador):
        partes = [f"Vida {lutador.vida}/{lutador.vida_maxima}   Energia {lutador.energia}"]
        defesa = round(lutador.stat("defesa"))
        partes.append(f"Crítico {lutador.stat('chance_critico'):.0%}  Esquiva {lutador.stat('chance_esquiva'):.0%}"
                      f"  Bloqueio {lutador.stat('chance_bloqueio'):.0%}" + (f"  Defesa {defesa}" if defesa else ""))
        for status in lutador.status.values():
            partes.append(f"• {status.rotulo()}: {status.descricao}")
        imunidades = lutador.imunidades_atuais()
        if imunidades:
            from roguelike.status import dados_do_status
            partes.append("Imune a: " + ", ".join(dados_do_status(s)["nome"] for s in sorted(imunidades)))
        afinidades = elementos.texto_de_afinidades(*elementos.fraquezas_e_resistencias(lutador))
        if afinidades:
            partes.append(afinidades)
        intencao = ia_do(lutador).intencao(lutador, self.combate) if lutador.lado == "inimigos" else None
        if intencao is not None:
            partes.append(f"Próximo golpe: {intencao.nome} — {intencao.resumo()}")
        return lutador.nome, "\n".join(partes)

    def desenhar_fim(self, tela):
        escurecer_tela(tela, 150)
        anotar("modal", tela.get_rect(), tela)              # a janela fica por cima do combate (conferência)
        vitoria = self.combate.resultado == "vitoria"
        if vitoria and self.recompensa is not None:
            from telas.combate.recompensas import PainelDeRecompensas
            from telas.comum import texto_do_item
            from ui.widgets import desenhar_dica
            if getattr(self, "painel_de_recompensas", None) is None:
                self.painel_de_recompensas = PainelDeRecompensas(self.recompensa, self.run.grupo.jogadores,
                                                                 self.sessao().jogador)
            objeto = self.painel_de_recompensas.desenhar(tela, self.mouse)
            self.desenhar_votos_do_fim(tela)
            if objeto is not None:
                anotar("modal", tela.get_rect(), tela)          # a dica fica por cima da janela
                desenhar_dica(tela, self.mouse, objeto.nome, texto_do_item(objeto),
                              cor_titulo=tema.COR_RARIDADE.get(objeto.raridade, tema.TEXTO_TITULO))
            return
        trechos = [("O grupo caiu...", tema.TEXTO_FRACO)]
        # a janela cresce com o conteúdo (loot comprido, vários heróis subindo de nível)
        caixa = CaixaTexto(pygame.Rect(0, 0, 520, 340), tema.pequena(), alinhamento="centro", padding=20, maximo_linhas=12)
        rect = pygame.Rect(0, 0, 520, 100 + caixa.altura_para(trechos) + 34)
        rect.center = (tema.LARGURA // 2, 300)
        caixa.rect = pygame.Rect(rect.x, rect.y + 80, rect.width, rect.height - 114)
        painel(tela, rect, "ouro" if vitoria else "sangue")
        titulo = "VITÓRIA" if vitoria else "DERROTA"
        texto(tela, titulo, tema.titulo(), tema.OURO_CLARO if vitoria else tema.SANGUE_CLARO, (rect.centerx, rect.y + 20), "midtop")
        caixa.desenhar(tela, trechos)
        texto(tela, "Enter para continuar", tema.pequena(), tema.TEXTO_FRACO, (rect.centerx, rect.bottom - 14), "midbottom")
        self.desenhar_votos_do_fim(tela)

    def desenhar_votos_do_fim(self, tela):
        """Em grupo: quem já confirmou a janela do fim (e quanto falta)."""
        if self.partida is None:
            return
        chave = self.chave_de_seguir()
        pronto = em_grupo.meu_voto(self, chave) is not None
        rect = pygame.Rect(tema.LARGURA // 2 - 330, tema.ALTURA - 50, 660, 40)
        em_grupo.faixa(tela, rect, self.partida, chave, "Você confirmou. Seguir" if pronto else "Enter para seguir")

    def desenhar_pausa(self, tela):
        escurecer_tela(tela, 170)
        opcoes = self.opcoes_da_pausa()
        rect = pygame.Rect(0, 0, 360, 100 + len(opcoes) * 52)
        rect.center = (tema.LARGURA // 2, tema.ALTURA // 2)
        painel(tela, rect, "pedra")
        texto(tela, "Pausa", tema.grande(), tema.TEXTO_TITULO, (rect.centerx, rect.y + 16), "midtop")
        self.botoes = []
        for i, (nome, acao) in enumerate(opcoes):
            botao = Botao((rect.x + 40, rect.y + 76 + i * 52, rect.width - 80, 42), nome, acao)
            botao.focado = i == self.indice_pausa
            self.botoes.append(botao)
            botao.desenhar(tela, (-1, -1))
