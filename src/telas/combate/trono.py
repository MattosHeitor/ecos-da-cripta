"""O Rei dos Ratos e o trono do Salão do Trono.

    CorridaAoTrono   (etapa 5R2) quando a vida dele acaba pela 1ª vez (passiva retirar_ao_trono), ele vira de lado e
                     corre em pé até o estrado (linha "correr" do sprite), pula para cima do monte de ratos e ouro e
                     senta (linha "sentado"). A tela desenha a corrida logo depois do trono (atrás dos lutadores) e,
                     quando ela termina, deixa o Rei sentado (TelaCombate.no_trono).
    VisualNoTrono    (etapa 5C, A Corte Completa) o Rei governa do trono a luta toda: age sentado (linhas
                     trono_ataque e trono_decreto) e desce quando a Rainha cai (passiva reinar_do_trono).
"""

import math

from telas.combate.visual import VisualLutador, suave

VELOCIDADE = 12                 # quadros por segundo da linha "correr"
PASSO = 7                       # pulinhos por corrida (a barriga sobe e desce)


def mistura(a, b, t):
    return a + (b - a) * t


class CorridaAoTrono:
    CORRER, SUBIR = 1.5, 0.6            # segundos

    def __init__(self, visual, estrado, assento):
        """visual: o VisualLutador do Rei; estrado: onde ele para, na frente do estrado (os pés); assento: os pés dele
        quando senta no trono."""
        self.visual = visual
        self.de = (visual.x, visual.y)
        self.estrado = estrado
        self.assento = assento
        self.tempo = 0.0

    @property
    def duracao(self):
        return self.CORRER + self.SUBIR

    def atualizar(self, dt):
        self.tempo += dt

    def terminou(self):
        return self.tempo >= self.duracao

    def correndo(self):
        return self.tempo < self.CORRER

    def posicao(self):
        """(x, y dos pés, y do chão embaixo dele): corre até o estrado (pulando a cada passada), depois pula em arco
        até o assento."""
        if self.correndo():
            t = self.tempo / self.CORRER
            x, y = mistura(self.de[0], self.estrado[0], t), mistura(self.de[1], self.estrado[1], t)
            return x, y - abs(math.sin(t * math.pi * PASSO)) * 6, y
        t = suave(min(1.0, (self.tempo - self.CORRER) / self.SUBIR))
        x, y = mistura(self.estrado[0], self.assento[0], t), mistura(self.estrado[1], self.assento[1], t)
        return x, y - math.sin(t * math.pi) * 46, y

    def quadro(self, sprites, nome):
        """(linha, índice) do sprite: correndo; no ar, o quadro da passada mais aberta; caindo sentado no fim."""
        if self.correndo():
            return "correr", int(self.tempo * VELOCIDADE) % sprites.quadros_de(nome, "correr")
        t = (self.tempo - self.CORRER) / self.SUBIR
        return ("correr", 1) if t < 0.75 else ("sentado", 0)

    def para_a_esquerda(self):
        return self.estrado[0] < self.de[0]

    def desenhar(self, tela, ambiente):
        """O Rei correndo (virado para onde vai); no chão alagado ele afunda e faz ondas como os outros."""
        visual, sprites = self.visual, self.visual.sprites
        nome = visual.nome_sprite
        if not sprites.tem_animacao(nome, "correr"):
            return
        linha, indice = self.quadro(sprites, nome)
        espelhar = self.para_a_esquerda() if linha == "correr" else True
        imagem = sprites.quadro(nome, linha, indice, visual.escala, espelhar)
        ax, ay = sprites.ancora(nome, visual.escala, espelhar)
        x, y, chao = self.posicao()
        area = imagem.get_rect(topleft=(round(x - ax), round(y - ay)))
        if self.correndo():
            ambiente.desenhar_na_agua(tela, lambda superficie: superficie.blit(imagem, area), area.inflate(8, 8),
                                      chao, area.width * 0.5, x)
        else:
            tela.blit(imagem, area)


class VisualNoTrono(VisualLutador):
    """O Rei sentado no assento do trono do cenário, agindo dali sem investir (a passiva reinar_do_trono o deixa No
    Trono). O Animador segue as linhas de sempre ("parado", "ataque", "decreto"...) e o desenho troca cada uma pela
    linha sentada do sprite (LINHAS_SENTADAS; as outras viram o "sentado"). Não tem barra, porque ninguém o atinge: a
    tela mostra o painel "O Rei no Trono". Quando ele desce, a tela troca este visual por um comum."""

    LINHAS_SENTADAS = {"ataque": "trono_ataque", "decreto": "trono_decreto"}
    PONTA_DO_CETRO = (95, -98)          # no quadro em que ele aponta (pixels da célula, virado para a direita)
    fixo = True                         # fora das fileiras (TelaCombate.reorganizar)
    no_ar = True                        # lá no alto do trono a água não o cobre
    projetil = ("bola", (244, 204, 96))  # os golpes de um alvo só saem do cetro como um clarão de ouro
    atraso_do_projetil = 2 / 11         # sai no 3º quadro do trono_ataque (o "ataque" toca a 11 quadros por segundo)

    def __init__(self, lutador, sprites, inimigo, assento):
        super().__init__(lutador, sprites, inimigo)
        self.escala = 2                 # o tamanho do trono (como o Rei sentado da luta da Rainha)
        self.colocar(*assento, imediato=True)
        self.caixas = {}

    def linha_desenhada(self):
        """(linha, quadro) do sprite para o que o Animador está tocando agora."""
        sentada = self.LINHAS_SENTADAS.get(self.animador.anim)
        if sentada and self.sprites.tem_animacao(self.nome_sprite, sentada):
            return sentada, self.animador.indice
        return "sentado", int(self.tempo * 3) % self.sprites.quadros_de(self.nome_sprite, "sentado")

    def investir(self, alvo_x):
        self.atacar_parado()            # do trono ele não sai: aponta o cetro

    def caixa(self):
        """O corpo sentado (sempre o 1º quadro do "sentado": textos e efeitos não pulam quando ele ergue o cetro)."""
        if "sentado" not in self.caixas:
            imagem = self.sprites.quadro(self.nome_sprite, "sentado", 0, self.escala, self.inimigo)
            ax, ay = self.sprites.ancora(self.nome_sprite, self.escala, self.inimigo)
            self.caixas["sentado"] = imagem.get_bounding_rect().move(-ax, -ay)
        return self.caixas["sentado"].move(round(self.x), round(self.y))

    def origem_do_projetil(self):
        dx, dy = self.PONTA_DO_CETRO
        return (round(self.x + (-dx if self.inimigo else dx) * self.escala), round(self.y + dy * self.escala))

    def tem_barra(self):
        return False

    def desenhar_barra(self, tela, **opcoes):
        """Sem barra: só guarda onde fica a seta da vez (em cima da coroa)."""
        self.areas_de_status = []
        self.topo_da_barra = self.caixa().top + 34

    def desenhar_sombra(self, tela):
        pass                            # sentado no trono (a sombra é a do trono)

    def desenhar(self, tela, destaque=None):
        if self.alfa <= 0:
            return
        linha, indice = self.linha_desenhada()
        efeito = "branco" if self.tempo < self.piscar_ate else self.tinta
        imagem = self.sprites.quadro(self.nome_sprite, linha, indice, self.escala, self.inimigo, efeito)
        ax, ay = self.sprites.ancora(self.nome_sprite, self.escala, self.inimigo)
        self.desenhar_quadro(tela, imagem, round(self.x - ax), round(self.y - ay), destaque, self.alfa)
