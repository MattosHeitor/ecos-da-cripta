"""Capitã da expedição: monta o grupo (1 a 5 heróis) e parte.

Aqui ficam a classe, a aparência, o nome e a semente. Cada cartão também REVISA o herói:
raça e subclasse (escolhidas com o Mago Ancião), golpes iniciais e o visual (Baú). Tudo fica
na expedição do progresso, então dá para ir e voltar entre os NPCs sem perder nada.
"""

import random

import pygame

from roguelike.classes import todas_as_classes, criar_heroi
from roguelike.racas import raca
from roguelike.run import nova_semente
from telas import fluxo
from telas.comum import TelaComBotoes, Fundo, existe_run_salva, sprite_da_vaga, cabecalho_do_acampamento
from ui import tema
from ui.desenho import texto, painel, paragrafo
from ui.componentes import AreaClicavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao, CampoDeTexto

LARGURA_CARTAO = 238
TOPO_CARTAO, ALTURA_CARTAO = 70, 500


def trocar(lista, atual, passo):
    indice = (lista.index(atual) + passo) % len(lista) if atual in lista else 0
    return lista[indice]


class TelaCapitao(TelaComBotoes):
    def __init__(self, app):
        super().__init__(app)
        self.fundo = Fundo("acampamento", escurecer=140)
        self.sorteio = random.Random()
        self.expedicao = app.progresso.expedicao_atual()
        self.campos = []
        self.refazer_campos()
        self.campo_semente = CampoDeTexto((560, tema.ALTURA - 66, 200, 44), self.expedicao.semente, maximo=10,
                                          maiusculas=True, rotulo="Semente (vazio = sorteada)")
        self._golpes_iniciais = {}

    def musica(self):
        return "acampamento"

    @property
    def vagas(self):
        return self.expedicao.vagas

    def guardar(self):
        """Passa os nomes e a semente digitados para a expedição e salva o progresso."""
        for vaga, campo in zip(self.vagas, self.campos):
            vaga.nome = campo.conteudo.strip()
        self.expedicao.semente = self.campo_semente.conteudo.strip()
        self.app.progresso.salvar()

    def voltar(self):
        self.guardar()
        fluxo.ir_para_acampamento(self.app)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    # ---------------- vagas ----------------
    def x_da_vaga(self, i):
        return 16 + i * (LARGURA_CARTAO + 12)

    def refazer_campos(self):
        self.campos = [CampoDeTexto((self.x_da_vaga(i) + 14, TOPO_CARTAO + 392, LARGURA_CARTAO - 28, 34), vaga.nome,
                                    maximo=12, rotulo="Nome") for i, vaga in enumerate(self.vagas)]

    def adicionar(self, classe=None):
        self.guardar()
        if self.expedicao.adicionar(classe, self.sorteio, self.app.progresso.classes_liberadas()) is not None:
            self.expedicao.validar(self.app.progresso)
            self.refazer_campos()

    def remover(self, vaga):
        self.guardar()
        if self.expedicao.remover(vaga):
            self.refazer_campos()

    def mudar_classe(self, vaga, passo):
        vaga.trocar_classe(trocar(list(self.app.progresso.classes_liberadas()), vaga.classe, passo))   # (sem as secretas)
        self.expedicao.validar(self.app.progresso)

    def mudar_aparencia(self, vaga, passo):
        vaga.aparencia = trocar(list(todas_as_classes()[vaga.classe].aparencias), vaga.aparencia, passo)

    def sem_subclasse(self):
        """A bênção "Aprendiz de Tudo" tira a subclasse de todos."""
        return "aprendiz" in self.app.progresso.especiais_equipados()

    def golpes_iniciais(self, vaga):
        """Os golpes com que o herói parte (equipados), em cache por classe/aparência/subclasse."""
        chave = (vaga.classe, vaga.aparencia, None if self.sem_subclasse() else vaga.subclasse)
        if chave not in self._golpes_iniciais:
            heroi = criar_heroi(chave[0], aparencia=chave[1], subclasse=chave[2])
            self._golpes_iniciais[chave] = [g.nome for g, _ in heroi.habilidades()]
        return self._golpes_iniciais[chave]

    def abrir_mago(self, indice, aba):
        self.guardar()
        from telas.mago_anciao import TelaMagoAnciao
        self.app.trocar(TelaMagoAnciao(self.app, aba, indice))

    def abrir_bau(self, vaga):
        self.guardar()
        from telas.bau import TelaBau
        self.app.trocar(TelaBau(self.app, vaga.classe))

    def em_grupo(self):
        """Montando os heróis para o lobby de uma partida em grupo (não se parte daqui: o host inicia)."""
        return self.app.partida is not None and self.app.partida.no_lobby()

    # ---------------- partir ----------------
    def partir(self):
        """Começa a run (pergunta antes se isso vai apagar uma run salva). No lobby: volta para ele."""
        if self.em_grupo():
            self.voltar()
            return
        if existe_run_salva():
            self.abrir_dialogo("Partir", "Já existe uma run salva. Começar outra apaga a run salva.",
                               [("Partir", self._partir), ("Cancelar", None)])
        else:
            self._partir()

    def _partir(self):
        self.guardar()
        herois = self.expedicao.criar_herois(self.app.progresso)
        fluxo.comecar_run(self.app, herois, self.expedicao.semente or None)

    # ---------------- eventos ----------------
    def ativar_campo(self, campo):
        for outro in [self.campo_semente] + self.campos:
            outro.ativo = outro is campo

    def evento(self, e):
        semente = [] if self.em_grupo() and not self.app.partida.eh_host else [self.campo_semente]
        for campo in semente + self.campos:
            if campo.evento(e) and e.type == pygame.KEYDOWN:
                return
        super().evento(e)

    def tecla(self, e):
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.partir()

    # ---------------- desenho ----------------
    def seletor(self, rect, rotulo, valor, menos, mais):
        """Linha "< valor >" com setas clicáveis."""
        rect = pygame.Rect(rect)
        texto(self.tela_atual, rotulo, tema.mini(), tema.TEXTO_FRACO, (rect.x, rect.y - 2), "bottomleft")
        self.botao(Botao((rect.x, rect.y, 30, rect.height), "<", menos))
        self.botao(Botao((rect.right - 30, rect.y, 30, rect.height), ">", mais))
        linha(self.tela_atual, valor, tema.pequena(), tema.TEXTO, (rect.centerx, rect.centery), rect.width - 68, "center")

    def desenhar_vaga(self, tela, i, vaga):
        x = self.x_da_vaga(i)
        rect = painel(tela, (x, TOPO_CARTAO, LARGURA_CARTAO, ALTURA_CARTAO), "ferro")
        classe = todas_as_classes()[vaga.classe]
        sprite = sprite_da_vaga(self.app.progresso, vaga)
        imagem = self.app.sprites.quadro(sprite, "parado", int(self.tempo * 4) % 4, 2)
        ax, ay = self.app.sprites.ancora(sprite, 2)
        tela.set_clip(rect.inflate(-6, -6))
        tela.blit(imagem, (rect.centerx - ax, rect.y + 162 - ay))
        tela.set_clip(None)
        linha(tela, classe.papel, tema.mini(), tema.TEXTO_FRACO, (rect.centerx, rect.y + 166), rect.width - 24, "midtop")
        if len(classe.aparencias) > 1:                # setas de aparência dos lados do sprite
            dica = ("Aparência", vaga.aparencia)
            self.botao(Botao((x + 8, rect.y + 80, 26, 40), "<", lambda: self.mudar_aparencia(vaga, -1), dica=dica))
            self.botao(Botao((rect.right - 34, rect.y + 80, 26, 40), ">", lambda: self.mudar_aparencia(vaga, 1), dica=dica))
        self.seletor((x + 14, rect.y + 208, LARGURA_CARTAO - 28, 28), "Classe", classe.nome,
                     lambda: self.mudar_classe(vaga, -1), lambda: self.mudar_classe(vaga, 1))
        # revisão: raça, subclasse e golpes iniciais
        subclasse = "sem subclasse" if self.sem_subclasse() else classe.subclasses[vaga.subclasse].nome
        trechos = [(f"Raça: {raca(vaga.raca).nome}", tema.OURO_CLARO), (f"Caminho: {subclasse}", tema.OURO_CLARO),
                   ("Golpes: " + ", ".join(self.golpes_iniciais(vaga)), tema.TEXTO_FRACO)]
        CaixaTexto(pygame.Rect(x + 14, rect.y + 244, LARGURA_CARTAO - 28, 118), tema.mini(), padding=0,
                   fontes=[tema.mini(), tema.fonte(12), tema.fonte(11)]).desenhar(tela, trechos)   # (golpes de nome longo)
        self.campos[i].desenhar(tela, self.mouse, self.tempo)
        self.botao(AreaClicavel(self.campos[i].rect, lambda c=self.campos[i]: self.ativar_campo(c)))
        largura = (LARGURA_CARTAO - 28 - 8) // 2
        self.botao(Botao((x + 14, rect.bottom - 40, largura, 32), "Raça", lambda: self.abrir_mago(i, "raca"),
                         dica=("Mago Ancião", "Escolher a raça e a subclasse deste herói.")))
        self.botao(Botao((x + 22 + largura, rect.bottom - 40, largura, 32), "Visual", lambda: self.abrir_bau(vaga),
                         dica=("Baú", "Trocar as skins da classe.")))
        if len(self.vagas) > 1:
            self.botao(Botao((rect.right - 34, rect.y + 8, 26, 26), "x", lambda: self.remover(vaga)))
        area_dica = pygame.Rect(rect.x + 36, rect.y, rect.width - 72, 176)
        if area_dica.collidepoint(self.mouse) and not self.sem_subclasse():
            sub = classe.subclasses[vaga.subclasse]
            self.dica = (f"{classe.nome} · {sub.nome}", f"{classe.descricao}\n{sub.descricao}\n"
                                                        f"Raça: {raca(vaga.raca).nome} — {raca(vaga.raca).descricao}")

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela)
        cabecalho_do_acampamento(tela, "Capitã da Expedição", self.app.progresso,
                                 f"Monte o grupo: {len(self.vagas)}/{self.expedicao.maximo()} heróis")
        for i, vaga in enumerate(self.vagas):
            self.desenhar_vaga(tela, i, vaga)
        if not self.expedicao.cheia():
            x = self.x_da_vaga(len(self.vagas))
            self.botao(Botao((x, TOPO_CARTAO, LARGURA_CARTAO, ALTURA_CARTAO), "+ Adicionar herói", self.adicionar,
                             estilo="pedra"))
        progresso = self.app.progresso
        avisos = ["Sozinho, os inimigos têm menos vida e dano. Cada herói a mais deixa os inimigos mais fortes."]
        nivel = progresso.nivel_de_ameaca()
        if nivel:
            from roguelike.dados import regras
            regra = regras()["ameaca"]
            avisos.append(f"Ameaça {nivel}: inimigos com +{round(regra['por_nivel']['vida_percentual'] * nivel * 100)}% "
                          f"de vida e +{round(regra['por_nivel']['dano_causado'] * nivel * 100)}% de dano; "
                          f"+{round(regra['brasas_por_nivel'] * nivel * 100)}% de Brasas")
        if progresso.bencaos_equipadas:
            from roguelike.progresso import bencaos as todas
            avisos.append("Bênçãos: " + ", ".join(todas()[c]["nome"] for c in progresso.bencaos_equipadas))
        if progresso.provisoes:
            from roguelike.itens import item
            avisos.append("Provisões: " + ", ".join(f"{item(c).nome} x{q}" for c, q in progresso.provisoes.items()))
        paragrafo(tela, "  ·  ".join(avisos), tema.mini(), tema.TEXTO_FRACO, (16, TOPO_CARTAO + ALTURA_CARTAO + 8), 530,
                  maximo_linhas=4, encolher=True)
        grupo = self.em_grupo()
        if existe_run_salva() and not grupo:
            texto(tela, "Atenção: partir substitui a run salva.", tema.pequena(), tema.SANGUE_CLARO, (16, tema.ALTURA - 22),
                  "midleft")
        if not grupo or self.app.partida.eh_host:            # (numa partida em grupo, a semente é a do host)
            self.campo_semente.desenhar(tela, self.mouse, self.tempo)
            self.botao(AreaClicavel(self.campo_semente.rect, lambda: self.ativar_campo(self.campo_semente)))
            self.botao(Botao((770, tema.ALTURA - 66, 110, 44), "Sortear",
                             lambda: setattr(self.campo_semente, "conteudo", nova_semente())))
        if grupo:
            self.botao(Botao((900, tema.ALTURA - 76, 200, 60), "Ao lobby", self.partir, "Enter", estilo="ouro",
                             dica=("Lobby", "Volta ao lobby com estes heróis (lá você marca Pronto).")))
        else:
            self.botao(Botao((900, tema.ALTURA - 76, 200, 60), "Partir!", self.partir, "Enter", estilo="ouro"))
        self.botao(Botao((1112, tema.ALTURA - 66, 152, 44), "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
