"""Acampamento (o "lobby" entre as runs): uma clareira na mata, à noite, em volta da fogueira.

Três planos de profundidade. O pixel tem sempre o mesmo tamanho (2x): quem está mais longe é DESENHADO menor pela
forja (as versões "_meio", com 85%, e "_longe", com 70%: forja/personagens/acampamento_detalhado.na_distancia), em vez
de ampliar ou reduzir a folha pronta (o que deixaria pixels de tamanhos diferentes).

    fundo   (70%)  tendas, caixotes, carroça, os postes do varal e a barraca do Taverneiro; a névoa de perto passa no
                   pé deles
    meio    (85%)  Espelho, Mestre do Grimório e Estudioso à esquerda; Arsenal e Mago Ancião (no círculo de runas) à
                   direita; os dois estandartes da expedição marcam o caminho até a taverna
    frente  (100%) a fogueira no centro, a Capitã e os heróis da expedição em dois troncos compridos (3 lugares de
                   cada lado, acompanhando a curva da clareira), a lenha e o
                   caldeirão num canto e o Baú no outro (desenhado a 85%: no tamanho cheio ficava da altura de uma
                   pessoa), e o Rato Branco depois de vencer o Reino

A luz vem da fogueira (quente, tremendo, e de vez em quando estala) e das lanternas; longe delas, o azul da lua
(visual/acampamento_noturno.py). Todos respiram devagar; o Taverneiro às vezes serve uma caneca e o Estudioso vira a
página (linhas extras dos sprites, Gesto). O nome e a função de cada um aparecem só com o mouse em cima (ou o foco do
teclado), numa placa de madeira e ouro, e ele ganha um contorno dourado suave: setas passam de um a outro, Enter abre,
1 a 8 são atalhos. Nos cantos de cima, sobre o céu: prestígio do grupo (esquerda) e Brasas, Bênçãos e Insígnias (direita).
"""

import math
import random

import pygame

from roguelike.classes import todas_as_classes
from roguelike.insignias import insignias_de_conquista, prestigio_das_classes
from roguelike.racas import raca
from telas import fluxo
from telas.comum import TelaComBotoes, existe_run_salva, sprite_da_vaga, area_do_sprite
from ui import tema
from ui.desenho import texto, painel, barra, desenhar_placa, anotar, vinheta, losango
from ui.componentes import AreaClicavel
from ui.texto import linha
from ui.widgets import Botao
from visual.acampamento_noturno import (PaisagemNoturna, Iluminacao, Luz, Fumaca, Brasas, Vagalumes, brilho_aditivo,
                                        sombra_no_chao, COR_DO_FOGO)

ESCALA = 2                                   # o pixel de todos (a distância está no desenho, não na escala)
CHAO_DO_FUNDO, CHAO_DO_MEIO = 468, 552       # a linha dos pés de cada plano (a frente fica em volta do fogo)
FIM_DO_FUNDO = 500                           # quem tem os pés acima disto é do plano do fundo (a névoa passa na frente)
FOGUEIRA = (640, 616)                        # pés da fogueira
CENTRO_DO_FOGO = (640, 552)                  # de onde sai a luz
TAVERNA = (640, CHAO_DO_FUNDO)


class Gesto:
    """De vez em quando o personagem faz um gesto (uma linha extra do sprite, tocada uma vez) e volta ao parado."""

    def __init__(self, anim, intervalo, velocidade=5.0, semente=1):
        self.anim, self.intervalo, self.velocidade = anim, intervalo, velocidade
        self.rng = random.Random(semente)
        self.proximo = self.rng.uniform(2.0, intervalo[0])
        self.inicio = None

    def quadro(self, tempo, quadros):
        """O quadro do gesto agora, ou None (está no parado)."""
        if self.inicio is None:
            if tempo < self.proximo:
                return None
            self.inicio = tempo
        i = int((tempo - self.inicio) * self.velocidade)
        if i < quadros:
            return i
        self.inicio, self.proximo = None, tempo + self.rng.uniform(*self.intervalo)
        return None


class Ponto:
    """Um personagem (ou objeto) com quem se fala: abre uma tela."""

    def __init__(self, chave, nome, funcao, sprite, pe, espelhar=False, anim="parado", gesto=None):
        self.chave, self.nome, self.funcao, self.sprite = chave, nome, funcao, sprite
        self.pe, self.espelhar, self.anim, self.gesto = pe, espelhar, anim, gesto


# na ordem dos atalhos 1 a 8 (o sprite já é o do plano: "_meio" e "_longe" são as versões desenhadas menores)
NPCS = [
    Ponto("espelho", "Espelho", "Talentos", "espelho_antigo_meio", (96, CHAO_DO_MEIO)),
    Ponto("grimorio", "Grimório", "Catálogo de golpes", "mestre_do_grimorio_meio", (224, CHAO_DO_MEIO)),
    Ponto("estudioso", "Estudioso", "Bestiário", "estudioso_meio", (350, CHAO_DO_MEIO), gesto=("folhear", (6.0, 11.0))),
    Ponto("taverneiro", "Taverneiro", "Bênçãos e provisões", "taverneiro_longe", (TAVERNA[0], TAVERNA[1] - 15),
          gesto=("servir", (7.0, 13.0))),
    Ponto("capitao", "Capitã", "Líder da expedição", "capita", (520, 618), anim="sentado"),
    Ponto("mago", "Mago Ancião", "Raça e caminho", "mago_anciao_meio", (1176, CHAO_DO_MEIO), espelhar=True),
    Ponto("bau", "Baú", "Skins", "bau_ornamentado_meio", (1176, 672), espelhar=True),
    Ponto("arsenal", "Arsenal", "Armas guardadas", "estande_de_armas_meio", (984, CHAO_DO_MEIO), espelhar=True),
]
# os dois bancos de tronco, um de cada lado do fogo (o da direita é o da esquerda espelhado): pés = o meio da tora
TRONCOS = [("tronco_comprido", (407, 640), False), ("tronco_comprido", (873, 640), True)]
ORDEM_DOS_TRONCOS = 600                      # na ordem de desenho: antes da fogueira e de quem está sentado neles
# lugares dos heróis da expedição nos troncos, de frente para o fogo: 3 por tronco, a 100 px um do outro, descendo
# com a tora (a Capitã fica no lugar de trás do tronco da esquerda); (pés, espelhar = olhar para a esquerda)
LUGARES = [((760, 618), True), ((420, 646), False), ((860, 646), True), ((320, 674), False), ((960, 674), True)]
# cenário: (sprite, pés, espelhar)
ENFEITES = [
    # fundo
    ("tenda_grande_longe", (110, CHAO_DO_FUNDO), False), ("tenda_grande_marrom_longe", (1170, CHAO_DO_FUNDO), True),
    ("caixotes_longe", (240, CHAO_DO_FUNDO + 8), False), ("barril_longe", (1048, CHAO_DO_FUNDO + 8), True),
    ("carroca_longe", (350, CHAO_DO_FUNDO), False),
    ("poste_de_lanterna_longe", (508, CHAO_DO_FUNDO + 2), False), ("poste_de_lanterna_longe", (772, CHAO_DO_FUNDO + 2), True),
    # meio
    ("tapete_meio", (96, CHAO_DO_MEIO + 6), False), ("circulo_de_runas_meio", (1176, CHAO_DO_MEIO + 6), False),
    ("estandarte_da_expedicao_meio", (444, CHAO_DO_MEIO - 6), False),
    ("estandarte_da_expedicao_meio", (836, CHAO_DO_MEIO - 6), True),
    # frente
    ("lenha", (98, 664), False), ("caldeirao", (196, 678), False), ("tapete_meio", (1176, 678), True),
]
CHAO_PRIMEIRO = {"tapete", "tapete_meio", "circulo_de_runas_meio"}     # deitados no chão: antes de todos
# o varal de bandeirolas entre o alto dos dois postes (pontas)
VARAL = ((514, 318), (766, 318))
CORES_DO_VARAL = ((150, 40, 44), (196, 156, 70), (52, 70, 120), (60, 100, 70))
# luzes fixas: (x, y, raio, cor, força, tremor); a primeira é a fogueira
LUZES = [
    (*CENTRO_DO_FOGO, 560, COR_DO_FOGO, 1.0, 0.06),
    (640, 400, 240, (255, 176, 100), 0.55, 0.03),                                 # dentro da barraca
    (532, 346, 130, (255, 190, 110), 0.5, 0.05), (748, 346, 130, (255, 190, 110), 0.5, 0.05),   # lanternas dos postes
    (110, 432, 120, (255, 150, 70), 0.35, 0.04), (1170, 432, 120, (255, 150, 70), 0.35, 0.04),  # portas das tendas
    (1176, 520, 200, (140, 120, 255), 0.5, 0.04),                                 # círculo de runas do Mago
    (290, 470, 130, (170, 130, 255), 0.4, 0.03),                                  # grimório flutuando
    (96, 440, 140, (150, 90, 230), 0.3, 0.02),                                    # névoa do Espelho
    (1176, 630, 120, (255, 200, 110), 0.5, 0.03),                                 # ouro do Baú
    (196, 656, 90, (255, 150, 70), 0.3, 0.06),                                    # brasa sob o caldeirão
]
ESTALOS = (2.5, 6.0)                          # segundos entre um estalo da fogueira e outro
DICA_DE_TECLAS = "Passe o mouse ou use as setas  ·  Enter abre  ·  1 a 8: atalhos"


class TelaAcampamento(TelaComBotoes):
    def __init__(self, app):
        super().__init__(app)
        rng = random.Random(42)
        self.rng = rng
        self.paisagem = PaisagemNoturna()
        self.luz = Iluminacao()
        self.luz.luzes = [Luz(x, y, r, cor, forca, tremor) for x, y, r, cor, forca, tremor in LUZES]
        self.fumaca = Fumaca((CENTRO_DO_FOGO[0], CENTRO_DO_FOGO[1] - 70), rng)
        self.brasas = Brasas((CENTRO_DO_FOGO[0], CENTRO_DO_FOGO[1] - 20), rng)
        self.vagalumes = Vagalumes(rng, (40, 420, 1200, 230))
        self.camada = pygame.Surface((tema.LARGURA, tema.ALTURA), pygame.SRCALPHA)
        self.em_destaque = None                 # chave do NPC (ou ("heroi", i)) sob o mouse/foco neste quadro
        self._contornos = {}
        self.balcao = None                      # (imagem, posição, chave) do balcão no quadro: corta o contorno do Taverneiro
        self._insignias = None
        self.gestos = {p.chave: Gesto(p.gesto[0], p.gesto[1], semente=i + 11)
                       for i, p in enumerate(NPCS) if p.gesto is not None}
        self.proximo_estalo = rng.uniform(*ESTALOS)
        self.clarao = 0.0                       # a fogueira aviva por um instante quando estala
        self.pets = self.criar_pets()

    def criar_pets(self):
        """Os bichos liberados (o Rato Branco depois do Reino), se as Opções deixam mostrar."""
        from roguelike.dados import regras
        from visual.pet_do_acampamento import PetDoAcampamento
        if not self.app.opcoes.mostrar_pets:
            return []
        dados = regras().get("pets", {})
        return [PetDoAcampamento(dados[c]["sprite"], dados[c]["lugares"], olhar_para=FOGUEIRA, semente=i + 3)
                for i, c in enumerate(self.progresso.pets_liberados())]

    def musica(self):
        return "acampamento"

    @property
    def progresso(self):
        return self.app.progresso

    # ============================================================
    # AÇÕES
    # ============================================================
    def abrir_opcoes(self):
        from telas.opcoes import TelaOpcoes
        self.app.trocar(TelaOpcoes(self.app, lambda: fluxo.ir_para_acampamento(self.app)))

    def abrir_insignias(self):
        from telas.insignias import TelaInsignias
        self.app.trocar(TelaInsignias(self.app))

    def abrir(self, chave):
        app = self.app
        if chave == "espelho":
            from telas.espelho import TelaEspelho
            app.trocar(TelaEspelho(app))
        elif chave == "bau":
            from telas.bau import TelaBau
            app.audio.tocar("bau")
            app.trocar(TelaBau(app))
        elif chave == "estudioso":
            from telas.bestiario import TelaBestiario
            app.trocar(TelaBestiario(app))
        elif chave == "taverneiro":
            from telas.taverna import TelaTaverna
            app.trocar(TelaTaverna(app))
        elif chave == "grimorio":
            from telas.grimorio import TelaGrimorio
            app.trocar(TelaGrimorio(app, self.progresso.expedicao_atual().vagas[0].classe))
        elif chave == "mago":
            from telas.mago_anciao import TelaMagoAnciao
            app.trocar(TelaMagoAnciao(app))
        elif chave == "arsenal":
            fluxo.abrir_arsenal(app)
        else:
            from telas.capitao import TelaCapitao
            app.trocar(TelaCapitao(app))

    def voltar(self):
        fluxo.ir_para_titulo(self.app)

    def tecla(self, e):
        if e.unicode and len(e.unicode) == 1 and e.unicode in "12345678":
            self.abrir(NPCS[int(e.unicode) - 1].chave)

    def atualizar(self, dt):
        super().atualizar(dt)
        self.paisagem.mirar(self.mouse)
        self.paisagem.atualizar(dt)
        self.luz.tempo += dt
        self.fumaca.atualizar(dt)
        self.brasas.atualizar(dt)
        self.vagalumes.atualizar(dt)
        self.crepitar(dt)
        for pet in self.pets:
            pet.atualizar(dt)

    def crepitar(self, dt):
        """De vez em quando a lenha estala: um leque de fagulhas e a luz da fogueira aviva e volta."""
        self.proximo_estalo -= dt
        if self.proximo_estalo <= 0:
            self.proximo_estalo = self.rng.uniform(*ESTALOS)
            self.brasas.estalo(self.rng.randint(8, 16))
            self.clarao = 1.0
        self.clarao = max(0.0, self.clarao - dt * 3.5)
        self.luz.luzes[0].forca = LUZES[0][4] * (1 + 0.18 * self.clarao)

    # ============================================================
    # QUEM ESTÁ NA CENA
    # ============================================================
    def vagas(self):
        return self.progresso.expedicao_atual().vagas[:len(LUGARES)]

    def sprite_do_heroi(self, vaga):
        """O sprite de um herói em volta da fogueira (o lobby troca: lá cada um traz o seu)."""
        return sprite_da_vaga(self.progresso, vaga)

    @staticmethod
    def placa_do_heroi(vaga):
        """(nome, "Classe · Raça") da placa de um herói com o mouse em cima."""
        classe = todas_as_classes()[vaga.classe]
        return vaga.nome or classe.nome, f"{classe.nome} · {raca(vaga.raca).nome}"

    def atores(self):
        """Tudo o que fica de pé na cena: (pés y, tipo, dados), do fundo para a frente."""
        itens = []
        for sprite, pe, espelhar in ENFEITES:
            itens.append((-1 if sprite in CHAO_PRIMEIRO else pe[1], "enfeite", (sprite, pe, espelhar)))
        for tronco in TRONCOS:
            itens.append((ORDEM_DOS_TRONCOS, "enfeite", tronco))
        for ponto in NPCS:
            if ponto.chave == "taverneiro":
                itens.append((TAVERNA[1], "taverna", ponto))
                continue
            itens.append((ponto.pe[1], "npc", ponto))
        for i, vaga in enumerate(self.vagas()):
            pe, espelhar = LUGARES[i]
            itens.append((pe[1], "heroi", (i, vaga, pe, espelhar)))
        itens.append((FOGUEIRA[1], "enfeite", ("fogueira", FOGUEIRA, False)))
        for pet in self.pets:
            itens.append((pet.pe[1], "pet", pet))
        return sorted(itens, key=lambda item: item[0])

    def area_do_ponto(self, ponto):
        sprites = self.app.sprites
        area = area_do_sprite(sprites, ponto.sprite, ponto.pe, ESCALA, ponto.espelhar)
        if ponto.chave == "taverneiro":                   # a barraca inteira conta
            area = area.union(area_do_sprite(sprites, "taverna_balcao_longe", TAVERNA, ESCALA)).inflate(-84, 0)
        return area

    def registrar_areas(self):
        """Áreas de clique (focáveis pelo teclado: as setas andam entre eles). Devolve quem está em destaque."""
        destaque = None
        # de trás para a frente: o clique (que procura do último para o primeiro) e o destaque ficam com quem está na frente
        for ponto in sorted(NPCS, key=lambda p: TAVERNA[1] if p.chave == "taverneiro" else p.pe[1]):
            botao = self.registrar(AreaClicavel(self.area_do_ponto(ponto), lambda c=ponto.chave: self.abrir(c), contorno=False))
            if self.usando_teclado and self.foco == botao.chave_foco:
                destaque = ponto.chave
            elif not self.usando_teclado and botao.em_cima(self.mouse):
                destaque = ponto.chave
        for i, vaga in enumerate(self.vagas()):
            pe, espelhar = LUGARES[i]
            area = area_do_sprite(self.app.sprites, self.sprite_do_heroi(vaga), pe, ESCALA, espelhar)
            botao = AreaClicavel(area, lambda: self.abrir("capitao"), contorno=False)
            botao.focavel = False
            self.botoes.append(botao)
            if not self.usando_teclado and botao.em_cima(self.mouse):
                destaque = ("heroi", i)
        return destaque

    # ============================================================
    # DESENHO DA CENA
    # ============================================================
    def quadro(self, sprite, anim, espelhar, deslocamento=0.0, velocidade=4, gesto=None):
        sprites = self.app.sprites
        if gesto is not None and sprites.tem_animacao(sprite, gesto.anim):
            i = gesto.quadro(self.tempo, sprites.quadros_de(sprite, gesto.anim))
            if i is not None:
                return sprites.quadro(sprite, gesto.anim, i, ESCALA, espelhar), (sprite, gesto.anim, i, espelhar)
        if anim not in sprites.meta(sprite)["animacoes"]:
            anim = "parado"
        i = int((self.tempo + deslocamento) * velocidade) % sprites.quadros_de(sprite, anim)
        return sprites.quadro(sprite, anim, i, ESCALA, espelhar), (sprite, anim, i, espelhar)

    def colar(self, sprite, pe, espelhar=False, anim="parado", deslocamento=0.0, velocidade=4, sombra=True, gesto=None):
        """Põe o sprite na camada dos personagens (a luz é aplicada depois) e devolve o que precisa de contraluz."""
        imagem, chave = self.quadro(sprite, anim, espelhar, deslocamento, velocidade, gesto)
        ax, ay = self.app.sprites.ancora(sprite, ESCALA, espelhar)
        posicao = (round(pe[0] - ax), round(pe[1] - ay))
        if sombra:
            largura = self.app.sprites.caixa(sprite, ESCALA).width
            sombra_no_chao(self.camada_do_chao, pe, min(largura, 160), CENTRO_DO_FOGO, 0.6 if pe[1] < FIM_DO_FUNDO else 1.0)
        self.camada.blit(imagem, posicao)
        return imagem, posicao, chave

    def colar_ator(self, tipo, dados):
        """Um ator da cena (de atores()) na camada; devolve (imagem, posição, chave, quem) se ele recebe contraluz."""
        if tipo == "enfeite":
            sprite, pe, espelhar = dados
            fogo = sprite == "fogueira"
            self.colar(sprite, pe, espelhar, velocidade=6 if fogo else 3, sombra=sprite not in CHAO_PRIMEIRO and not fogo)
            return None
        if tipo == "taverna":
            self.colar("taverna_fundo_longe", TAVERNA, sombra=False)
            ator = self.colar(dados.sprite, dados.pe, velocidade=2.5, sombra=False, gesto=self.gestos.get(dados.chave))
            self.balcao = self.colar("taverna_balcao_longe", TAVERNA, sombra=False)     # cobre o Taverneiro da cintura para baixo
            return (*ator, dados.chave)
        if tipo == "npc":
            return (*self.colar(dados.sprite, dados.pe, dados.espelhar, dados.anim, deslocamento=len(dados.chave) * 0.3,
                                velocidade=2.5, gesto=self.gestos.get(dados.chave)), dados.chave)
        if tipo == "pet":
            return (*self.colar(dados.sprite, dados.pe, dados.espelhar, dados.anim,
                                velocidade=12 if dados.correndo else 4), "pet")
        i, vaga, pe, espelhar = dados
        return (*self.colar(self.sprite_do_heroi(vaga), pe, espelhar, "sentado", deslocamento=i * 0.37, velocidade=2.5),
                ("heroi", i))

    def iluminar_plano(self, tela, atores, mapa, desenhados):
        """Cola um plano (sombras no chão, os atores na camada iluminada) e a contraluz da fogueira por cima."""
        self.camada.fill((0, 0, 0, 0))
        deste = [ator for ator in (self.colar_ator(tipo, dados) for _, tipo, dados in atores) if ator is not None]
        self.luz.iluminar(self.camada, mapa)
        tela.blit(self.camada, (0, 0))
        for imagem, posicao, chave, _ in deste:           # contraluz da fogueira (depois da luz: fica viva)
            borda = self.luz.contraluz(imagem, posicao, CENTRO_DO_FOGO, chave)
            if borda is not None:
                tela.blit(borda, posicao, special_flags=pygame.BLEND_RGB_ADD)
        desenhados += deste

    def desenhar_cena(self, tela):
        """Fundo, chão aceso, o plano do fundo, a névoa, o meio e a frente, partículas e a moldura da frente."""
        self.paisagem.desenhar_fundo(tela)
        fogo = self.luz.tremular(self.luz.luzes[0]) * (1 + 0.15 * self.clarao)
        brilho_aditivo(tela, (FOGUEIRA[0], FOGUEIRA[1] - 10), 470, (120, 62, 26), min(1.0, fogo), achatar=0.34)
        brilho_aditivo(tela, (TAVERNA[0], TAVERNA[1] + 4), 190, (70, 40, 18), 1.0, achatar=0.3)
        brilho_aditivo(tela, (1176, 560), 140, (34, 28, 80), 1.0, achatar=0.32)
        self.vagalumes.desenhar(tela)
        self.camada_do_chao = tela
        mapa = self.luz.mapa()
        atores = self.atores()
        desenhados = []                                   # (imagem, posição, chave, quem) para o destaque e o nome
        self.iluminar_plano(tela, [a for a in atores if 0 <= a[0] < FIM_DO_FUNDO], mapa, desenhados)
        self.desenhar_varal(tela)
        self.paisagem.desenhar_nevoa(tela, "nevoa_perto")
        self.iluminar_plano(tela, [a for a in atores if not 0 <= a[0] < FIM_DO_FUNDO], mapa, desenhados)
        self.fumaca.desenhar(tela)
        self.brasas.desenhar(tela)
        for imagem, posicao, chave, quem in desenhados:
            if quem == self.em_destaque:
                self.desenhar_contorno(tela, imagem, posicao, chave, self.balcao if quem == "taverneiro" else None)
        self.paisagem.desenhar_frente(tela)
        tela.blit(vinheta(tela.get_size(), 150), (0, 0))
        return desenhados

    def desenhar_contorno(self, tela, imagem, posicao, chave, na_frente=None):
        """Contorno suave em volta de quem está em destaque: um fio dourado rente à silhueta e um halo que se desfaz
        para fora (por fora do corpo, sem fundo nenhum), pulsando devagar.

        na_frente: (imagem, posição, chave) do que cobre parte dele (o balcão na frente do Taverneiro): ali não há contorno."""
        cache = (chave, na_frente[2] if na_frente else None)
        if cache not in self._contornos:
            mascara = pygame.mask.from_surface(imagem)
            margem = 8
            tamanho = (mascara.get_size()[0] + 2 * margem, mascara.get_size()[1] + 2 * margem)
            coberto = pygame.mask.Mask(tamanho)
            if na_frente is not None:
                frente, onde, _ = na_frente
                coberto.draw(pygame.mask.from_surface(frente),
                             (onde[0] - posicao[0] + margem, onde[1] - posicao[1] + margem))

            def engrossada(raio):
                grossa = pygame.mask.Mask(tamanho)
                for dx in range(-raio, raio + 1):
                    for dy in range(-raio, raio + 1):
                        if dx * dx + dy * dy <= raio * raio + raio:
                            grossa.draw(mascara, (margem + dx, margem + dy))
                return grossa

            contorno = pygame.Surface(tamanho, pygame.SRCALPHA)
            anterior = engrossada(2)
            for raio, alfa in ((8, 22), (6, 46), (4, 84)):            # halo: de fora para dentro, cada vez mais forte
                anel = engrossada(raio)
                anel.erase(anterior, (0, 0))
                anel.erase(coberto, (0, 0))
                contorno.blit(anel.to_surface(setcolor=(*tema.OURO, alfa), unsetcolor=(0, 0, 0, 0)), (0, 0))
            fio = anterior
            fio.erase(mascara, (margem, margem))
            fio.erase(coberto, (0, 0))
            contorno.blit(fio.to_surface(setcolor=(*tema.OURO_CLARO, 235), unsetcolor=(0, 0, 0, 0)), (0, 0))
            self._contornos[cache] = (contorno, margem)
        contorno, margem = self._contornos[cache]
        contorno.set_alpha(int(205 + 50 * math.sin(self.tempo * 3.2)))
        tela.blit(contorno, (posicao[0] - margem, posicao[1] - margem))

    def desenhar_varal(self, tela):
        """Cordão de bandeirolas entre as lanternas dos dois postes, balançando devagar."""
        (x0, y0), (x1, y1) = VARAL
        pontos = []
        for k in range(31):
            t = k / 30
            pontos.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + math.sin(t * math.pi) * (18 + 2 * math.sin(self.tempo * 0.8))))
        pygame.draw.lines(tela, (30, 24, 26), False, pontos, 2)
        for k in range(2, 29, 3):
            x, y = pontos[k]
            balanco = math.sin(self.tempo * 1.6 + k) * 1.5
            cor = tuple(int(c * 0.8) for c in CORES_DO_VARAL[(k // 3) % len(CORES_DO_VARAL)])   # longe: mais apagadas
            escura = tuple(int(c * 0.55) for c in cor)
            pygame.draw.polygon(tela, escura, [(x - 5, y + 1), (x + 5, y + 1), (x + balanco, y + 12)])
            pygame.draw.polygon(tela, cor, [(x - 4, y + 1), (x + 4, y + 1), (x + balanco, y + 10)])

    def desenhar_nome(self, tela, desenhados):
        """Placa de madeira e ouro com o nome (e a função) de quem está em destaque, logo acima da cabeça."""
        if self.em_destaque is None:
            return
        for imagem, posicao, _, quem in desenhados:
            if quem != self.em_destaque:
                continue
            caixa = imagem.get_bounding_rect().move(posicao)
            if isinstance(quem, tuple):
                titulo, funcao = self.placa_do_heroi(self.vagas()[quem[1]])
            else:
                indice = next(i for i, p in enumerate(NPCS) if p.chave == quem)
                titulo, funcao = f"{indice + 1}. {NPCS[indice].nome}", NPCS[indice].funcao
            fonte_titulo, fonte = tema.normal(), tema.pequena()
            largura = min(300, max(fonte_titulo.size(titulo)[0], fonte.size(funcao)[0]) + 44)
            placa = pygame.Rect(0, 0, largura, 64)
            placa.midbottom = (caixa.centerx, caixa.top - 6)
            placa.clamp_ip(pygame.Rect(16, 140, tema.LARGURA - 32, tema.ALTURA - 200))
            painel(tela, placa, "ferro")
            linha(tela, titulo, fonte_titulo, tema.OURO_CLARO, (placa.centerx, placa.y + 10), placa.width - 24, "midtop")
            linha(tela, funcao, fonte, tema.TEXTO, (placa.centerx, placa.y + 36), placa.width - 24, "midtop")
            return

    # ============================================================
    # HUD: PRESTÍGIO, BRASAS, BÊNÇÃOS E INSÍGNIAS (sobre o céu, nos cantos de cima)
    # ============================================================
    def classes_do_grupo(self):
        classes = []
        for vaga in self.progresso.expedicao_atual().vagas:
            if vaga.classe not in classes:
                classes.append(vaga.classe)
        return classes

    def desenhar_prestigio(self, tela):
        """Placa compacta: classe e nível de prestígio, barrinha de XP; o próximo marco vai na dica."""
        prestigios = prestigio_das_classes(self.progresso, self.classes_do_grupo())
        rect = painel(tela, (16, 12, 268, 40 + len(prestigios) * 22), "ferro")
        texto(tela, "Prestígio do grupo", tema.pequena(), tema.OURO_CLARO, (rect.x + 14, rect.y + 8))
        for i, p in enumerate(prestigios):
            y = rect.y + 33 + i * 22
            linha_rect = pygame.Rect(rect.x + 10, y - 2, rect.width - 20, 20)
            nome = p.classe.nome_que_cabe(tema.mini(), 104 - tema.mini().size(f" {p.nivel}")[0])
            linha(tela, f"{nome} {p.nivel}", tema.mini(), tema.TEXTO_TITULO, (rect.x + 14, y), 104)
            barra(tela, (rect.x + 122, y + 5, 84, 7), p.fracao(), tema.XP, marcas=0)
            texto(tela, "máx." if p.no_maximo else f"{p.xp}/{p.precisa}", tema.mini(), tema.TEXTO_FRACO,
                  (rect.right - 12, y), "topright")
            if linha_rect.collidepoint(self.mouse) and not self.usando_teclado:
                self.dica = (f"{p.classe.nome}: prestígio {p.nivel}/{p.maximo}", "Próximo: " + p.texto_do_proximo())
                self.posicao_da_dica = self.mouse

    def desenhar_recursos(self, tela):
        """Placa da direita: Brasas, Bênçãos e Insígnias (clique abre as insígnias)."""
        from telas.insignias import desenhar_escudo
        progresso = self.progresso
        if self._insignias is None:                       # o progresso não muda com a tela aberta: conta uma vez só
            self._insignias = insignias_de_conquista(progresso)
        insignias = self._insignias
        feitas = sum(1 for i in insignias if i.feita)
        rect = pygame.Rect(tema.LARGURA - 16 - 296, 12, 296, 112)
        quadro = AreaClicavel(rect, self.abrir_insignias, contorno=False)
        quadro.focavel = False
        self.botoes.append(quadro)
        em_cima = quadro.em_cima(self.mouse) and not self.usando_teclado
        painel(tela, rect, "ouro" if em_cima else "ferro")
        losango(tela, (rect.x + 20, rect.y + 20), 6, (255, 150, 60))
        texto(tela, "Brasas", tema.pequena(), tema.TEXTO_TITULO, (rect.x + 34, rect.y + 10))
        texto(tela, str(progresso.brasas), tema.pequena(), tema.OURO_CLARO, (rect.right - 14, rect.y + 10), "topright")
        bencaos = len(progresso.bencaos_equipadas)
        from roguelike.dados import regras
        espacos = regras()["progresso"].get("espacos_de_bencao", 5)
        texto(tela, "Bênçãos", tema.pequena(), tema.TEXTO_TITULO, (rect.x + 34, rect.y + 34))
        texto(tela, f"{bencaos}/{espacos}", tema.pequena(), tema.TEXTO, (rect.right - 14, rect.y + 34), "topright")
        texto(tela, "Insígnias", tema.pequena(), tema.TEXTO_TITULO, (rect.x + 34, rect.y + 58))
        texto(tela, f"{feitas}/{len(insignias)}", tema.pequena(), tema.TEXTO, (rect.right - 14, rect.y + 58), "topright")
        losango(tela, (rect.x + 20, rect.y + 44), 5, tema.OURO)
        losango(tela, (rect.x + 20, rect.y + 68), 5, tema.XP)
        prestigios = prestigio_das_classes(progresso)
        largura = (rect.width - 24) // max(1, len(prestigios))
        for i, p in enumerate(prestigios):
            area = pygame.Rect(rect.x + 12 + i * largura + (largura - 20) // 2, rect.y + 82, 20, 22)
            desenhar_escudo(tela, area, p.nivel, p.nivel > 0)
            if area.collidepoint(self.mouse) and not self.usando_teclado:
                andamento = "Completo" if p.no_maximo else f"{p.xp}/{p.precisa} XP"
                self.dica = (f"{p.classe.nome}: prestígio {p.nivel}/{p.maximo}", f"{andamento}\nPróximo: {p.texto_do_proximo()}")
                self.posicao_da_dica = self.mouse
        if em_cima and self.dica is None:
            self.dica = ("Insígnias", "Clique para ver todas as conquistas e o prestígio de cada classe.")
            self.posicao_da_dica = self.mouse

    # ============================================================
    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.em_destaque = self.registrar_areas()
        desenhados = self.desenhar_cena(tela)
        anotar("modal", tela.get_rect(), tela)            # o HUD fica por cima da cena (conferência)
        desenhar_placa(tela, (tema.LARGURA // 2, 34), "Acampamento", tema.media(), tema.OURO_CLARO)
        self.desenhar_prestigio(tela)
        self.desenhar_recursos(tela)
        self.desenhar_nome(tela, desenhados)
        self.botao(Botao((16, tema.ALTURA - 48, 140, 36), "Voltar", self.voltar, "ESC"))
        self.botao(Botao((tema.LARGURA - 156, tema.ALTURA - 48, 140, 36), "Opções", self.abrir_opcoes))
        if existe_run_salva():
            texto(tela, "Há uma run salva: começar outra vai substituí-la.", tema.pequena(), tema.SANGUE_CLARO,
                  (tema.LARGURA // 2, tema.ALTURA - 46), "center")
        texto(tela, DICA_DE_TECLAS, tema.mini(), tema.TEXTO_FRACO, (tema.LARGURA // 2, tema.ALTURA - 20), "center")
        self.terminar_desenho(tela)
