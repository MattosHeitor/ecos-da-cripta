"""Cenários macabros (gerados por ferramentas/cenarios_macabros.py).

    cenario = CenarioMacabro("catedral", variante=1)
    cenario.atualizar(dt)
    cenario.desenhar(tela)          # céu, fundo, chão, luzes e partículas de trás
    ... personagens ...
    cenario.desenhar_frente(tela)   # detalhes da frente, cinzas, névoa e relâmpago

As camadas balançam devagar em velocidades diferentes (paralaxe) e as luzes
(velas, cristais, lanternas, braseiros) tremulam. Cenas com "aurora" no cenarios.json ganham
cortinas de luz ondulando no céu (Aurora).

Dia e noite: as fases com "ciclo" no regioes.json (Floresta, Circo...) têm três céus (dia, entardecer e noite).
'hora' vai de 0 (dia) a 1 (noite): o céu e o tom das outras camadas se misturam, as luzes só
acendem quando escurece e os vagalumes aparecem à noite (de dia sobe poeira no ar).
hora_da_area() diz a hora de cada área: a primeira área de uma região é de dia e a do chefe é à noite.

Cenário de cada fase (regioes.json): "cenario" (ou "cenario_provisorio" enquanto a arte não existe),
"variantes" ao longo da fase, "sala_do_chefe" e "paleta" (tom que multiplica as cores das camadas).

Cenas mais detalhadas podem ter camadas em resolução maior (ex.: 704x360 = cada pixel vira 2x2): o tamanho na tela é
sempre o mesmo. As posições do cenarios.json (luzes, "trono") continuam na escala de 352x180.
Água (Reino dos Ratos): "chao_alagado" lista uma camada de chão por nível da água; alagar(nivel) troca o chão.
"camadas_extras" ({nome: camada de baixo}) são desenhadas logo depois da camada de baixo; esconder(nome) tira uma.
"""

import json
import math
import os
import random

import pygame

from caminhos import CAMINHOS
from visual.particulas import TIPOS

PASTA = CAMINHOS.asset("cenarios_macabros")
VEZES = 4                     # cada pixel do cenário vira 4x4 na tela
LARGURA_BASE = 352            # largura das camadas na escala de VEZES (as maiores são ampliadas menos)
MARGEM = 16                   # colunas a mais de cada lado (para balançar)
CAMADAS = ("ceu", "longe", "meio", "chao", "frente")
BALANCO = {"ceu": 1, "longe": 1, "meio": 0, "chao": 0, "frente": 2}   # em pixels do cenário

LUGARES_FIXOS = ("titulo", "acampamento")      # cenas que não são fases
# Tom das camadas: (multiplicador RGB depois de dobrar o brilho, soma) — a noite é o desenho original
TONS = {"dia": ((196, 192, 184), (8, 8, 12)), "tarde": ((196, 128, 118), (10, 2, 0))}
# o chão foi desenhado quase preto: de dia ele ganha um pouco mais de luz
LUZ_DO_CHAO = {"dia": (26, 24, 18), "tarde": (18, 8, 2)}
NOMES_DA_HORA = ((0.2, "Dia"), (0.45, "Tarde"), (0.7, "Entardecer"), (1.01, "Noite"))

_catalogo = None
_imagens = {}
_brilhos = {}


def catalogo():
    global _catalogo
    if _catalogo is None:
        caminho = os.path.join(PASTA, "cenarios.json")
        _catalogo = {}
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as arquivo:
                _catalogo = json.load(arquivo)
    return _catalogo


def dados_da_fase(lugar):
    """A Regiao do regioes.json (ou None para o título, o acampamento e cenas avulsas)."""
    from roguelike.regioes import todas_as_regioes
    return None if lugar in LUGARES_FIXOS else todas_as_regioes().get(lugar)


def hora_da_area(regiao, area, total=None):
    """0 = dia, 1 = noite. Fases cobertas (Minas, Catedral) e o acampamento ficam na noite (1).

    total = quantas áreas a fase tem nesta run (padrão: o tamanho original)."""
    fase = dados_da_fase(regiao)
    return fase.hora(area, total) if fase else 1.0


def paleta_do_lugar(regiao):
    """Tom (r, g, b) que multiplica o cenário da fase, ou None."""
    fase = dados_da_fase(regiao)
    tom = fase.paleta.get("tom") if fase else None
    return tuple(tom) if tom else None


def nome_da_hora(hora):
    return next(nome for limite, nome in NOMES_DA_HORA if hora < limite)


def tingir(imagem, tom, chao=False):
    """Versão de dia/entardecer de uma camada desenhada para a noite (só com pygame: dobra e tinge)."""
    multiplicar, somar = TONS[tom]
    clara = imagem.copy()
    clara.blit(imagem, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    clara.fill(multiplicar, special_flags=pygame.BLEND_RGB_MULT)
    clara.fill(somar, special_flags=pygame.BLEND_RGB_ADD)
    if chao:
        clara.fill(LUZ_DO_CHAO[tom], special_flags=pygame.BLEND_RGB_ADD)
    return clara


def misturar_camadas(a, b, t):
    """a com b por cima em transparência t (0 = só a, 1 = só b)."""
    if b is None or t <= 0:
        return a
    if a is None or t >= 1:
        return b
    resultado = a.copy()
    cima = b.copy()
    cima.set_alpha(int(255 * t))
    resultado.blit(cima, (0, 0))
    return resultado


_horas = {}


def camada_na_hora(chave, nome_camada, hora, paleta=None):
    """A camada já misturada para a hora e tingida pela paleta (guardada: a hora de um combate não muda)."""
    passo = round(hora * 8) / 8
    if passo >= 1 and paleta is None:
        return carregar_camada(chave, nome_camada)
    janela = pygame.display.get_surface() is not None
    guarda = (chave, nome_camada, passo, janela, paleta)  # com janela, a imagem é convertida (desenha bem mais rápido)
    if guarda not in _horas and paleta is not None:
        imagem = camada_na_hora(chave, nome_camada, hora)
        if imagem is not None:
            imagem = imagem.copy()
            imagem.fill(paleta, special_flags=pygame.BLEND_RGB_MULT)
        _horas[guarda] = imagem
    if guarda not in _horas:
        noite = carregar_camada(chave, nome_camada)
        if nome_camada == "ceu":
            dia, tarde = carregar_camada(chave, "ceu_dia"), carregar_camada(chave, "ceu_tarde")
        elif noite is not None:
            no_chao = nome_camada in ("chao", "frente")
            dia, tarde = tingir(noite, "dia", no_chao), tingir(noite, "tarde", no_chao)
        else:
            dia = tarde = None
        if passo <= 0.5:
            imagem = misturar_camadas(dia, tarde, passo * 2)
        else:
            imagem = misturar_camadas(tarde, noite, (passo - 0.5) * 2)
        if janela and imagem is not None:
            imagem = imagem.convert_alpha()
        _horas[guarda] = imagem
    return _horas[guarda]


def cenario_da_fase(fase):
    """A cena da fase: a de mesmo nome da fase, a do campo "cenario" ou, sem arte ainda, a provisória."""
    for nome in (fase.chave, fase.cenario):
        if f"{nome}_0" in catalogo():
            return nome
    return fase.cenario_provisorio or fase.chave


def cena_da_area(regiao, area, tipo_de_encontro=None, total=None):
    """(nome, variante) do cenário de uma área: as variantes se sucedem ao longo da fase e o chefe tem a sua sala."""
    fase = dados_da_fase(regiao)
    if fase is None:
        return regiao, 0
    if tipo_de_encontro == "chefe" and fase.sala_do_chefe and f"{fase.sala_do_chefe}_0" in catalogo():
        return fase.sala_do_chefe, 0
    nome = cenario_da_fase(fase)
    variante = fase.variante(area, total)
    return nome, variante if f"{nome}_{variante}" in catalogo() else 0


def carregar_camada(chave, nome_camada):
    """Camada ampliada. Guarda se já foi convertida para o formato da janela (desenha bem mais rápido)."""
    janela = pygame.display.get_surface() is not None
    guardada = _imagens.get((chave, nome_camada))
    if guardada is not None and (guardada[1] or not janela):
        return guardada[0]
    caminho = os.path.join(PASTA, f"{chave}_{nome_camada}.png")
    imagem = None
    if os.path.exists(caminho):
        pequena = pygame.image.load(caminho)
        vezes = max(1, round(VEZES * LARGURA_BASE / pequena.get_width()))      # 352 px -> 4x, 704 px -> 2x
        imagem = pygame.transform.scale(pequena, (pequena.get_width() * vezes, pequena.get_height() * vezes))
        if janela:
            imagem = imagem.convert_alpha()
        if imagem.get_bounding_rect().width == 0:
            imagem = None                              # camada vazia: nem desenha
    _imagens[(chave, nome_camada)] = (imagem, janela)
    return imagem


def brilho(raio, cor, forca):
    """Brilho pixelado em degraus (para somar à tela com BLEND_ADD)."""
    chave = (raio, tuple(cor), round(forca, 2))
    if chave not in _brilhos:
        lado = raio * 2 + 1
        pequena = pygame.Surface((lado, lado))
        pequena.fill((0, 0, 0))
        for y in range(lado):
            for x in range(lado):
                d = math.hypot(x - raio, y - raio) / raio
                if d < 1:
                    degrau = math.ceil((1 - d) * 4) / 4          # 4 degraus de luz
                    nivel = degrau * degrau * forca
                    pequena.set_at((x, y), tuple(int(c * nivel) for c in cor))
        _brilhos[chave] = pygame.transform.scale(pequena, (lado * VEZES, lado * VEZES))
    return _brilhos[chave]


class Luz:
    """Uma fonte de luz do cenário (vela, cristal...). 'tremula' de 0 a 1."""

    def __init__(self, x, y, raio, cor, tremula, intensidade=1.0):
        self.x, self.y, self.raio, self.cor, self.tremula = x, y, raio, cor, tremula
        self.fase = random.uniform(0, 10)
        self.niveis = [brilho(raio, cor, f * intensidade) for f in (0.22, 0.28, 0.34)]

    def desenhar(self, tela, tempo, deslocamento_x):
        oscilacao = math.sin(tempo * 7 + self.fase) * 0.6 + math.sin(tempo * 13.7 + self.fase * 2) * 0.4
        indice = 1 + round(oscilacao * self.tremula)
        imagem = self.niveis[max(0, min(2, indice))]
        x = (self.x - self.raio - MARGEM) * VEZES + deslocamento_x
        y = (self.y - self.raio) * VEZES
        tela.blit(imagem, (x, y), special_flags=pygame.BLEND_ADD)


class Nevoa:
    """Faixa de névoa pontilhada que atravessa a tela devagar."""

    def __init__(self, largura, y, altura, cor, velocidade, semente):
        self.largura, self.y, self.velocidade = largura, y, velocidade
        rng = random.Random(semente)
        pequena = pygame.Surface((largura // VEZES, altura // VEZES), pygame.SRCALPHA)
        pequena.fill((0, 0, 0, 0))
        for _ in range(26):
            cx, cy = rng.randrange(pequena.get_width()), rng.randrange(pequena.get_height())
            raio = rng.randint(6, 18)
            for yy in range(cy - raio, cy + raio):
                for xx in range(cx - raio * 2, cx + raio * 2):
                    d = math.hypot((xx - cx) / 2, yy - cy) / raio
                    if d < 1 and (xx + yy) % 2 == 0:
                        pequena.set_at((xx % pequena.get_width(), max(0, min(pequena.get_height() - 1, yy))),
                                       (*cor, int(55 * (1 - d))))
        self.imagem = pygame.transform.scale(pequena, (largura, altura))
        self.posicao = 0.0

    def atualizar(self, dt):
        self.posicao = (self.posicao + self.velocidade * dt) % self.largura

    def desenhar(self, tela):
        x = int(self.posicao) // VEZES * VEZES
        tela.blit(self.imagem, (x, self.y))
        tela.blit(self.imagem, (x - self.largura, self.y))


class Aurora:
    """Aurora: cortinas de luz que ondulam devagar no céu, desenhadas logo depois do céu (atrás das
    montanhas e muralhas). Cada coluna de 4 px é uma faixa vertical já pronta (luz somada à tela)."""

    NIVEIS = (0.45, 0.7, 1.0)

    def __init__(self, largura, cores, topo=60, altura=200):
        self.largura, self.topo = largura, topo
        self.faixas = [[self.faixa(cor, nivel, altura) for nivel in self.NIVEIS] for cor in cores]

    @staticmethod
    def faixa(cor, nivel, altura):
        """Faixa vertical: fraca em cima, mais forte perto da borda de baixo, e some de repente (como a aurora)."""
        faixa = pygame.Surface((VEZES, altura))
        faixa.fill((0, 0, 0))
        for y in range(0, altura, VEZES):
            t = y / altura
            forca = (t ** 1.6 if t < 0.82 else (1 - t) / 0.18 * 0.82 ** 1.6) * 0.42 * nivel
            faixa.fill(tuple(int(c * forca) for c in cor), (0, y, VEZES, VEZES))
        return faixa

    def desenhar(self, tela, tempo):
        n = len(self.faixas)
        for x in range(0, self.largura, VEZES):
            luz = math.sin(x * 0.011 + tempo * 0.5) + 0.6 * math.sin(x * 0.031 - tempo * 0.9)
            if luz < -0.4:
                continue                                       # vãos entre as cortinas
            nivel = 0 if luz < 0.3 else (1 if luz < 0.9 else 2)
            cor = int(x / self.largura * n + math.sin(tempo * 0.07) * n) % n
            onda = math.sin(x * 0.006 + tempo * 0.35) * 30 + math.sin(x * 0.017 - tempo * 0.6) * 12
            y = int(self.topo + onda) // VEZES * VEZES
            tela.blit(self.faixas[cor][nivel], (x, y), special_flags=pygame.BLEND_ADD)


_miniaturas = {}


def miniatura_da_fase(regiao, largura, altura):
    """Retrato pequeno da fase (cena de abertura, com a hora e a paleta dela) para portões e títulos."""
    chave = (regiao, largura, altura, pygame.display.get_surface() is not None)
    if chave not in _miniaturas:
        nome, variante = cena_da_area(regiao, 1)
        fase = dados_da_fase(regiao)
        cenario = CenarioMacabro(nome, variante, 1280, 720, 0.35 if fase and fase.ciclo else 1.0, paleta_do_lugar(regiao))
        grande = pygame.Surface((1280, 720))
        cenario.desenhar(grande)
        cenario.desenhar_frente(grande)
        _miniaturas[chave] = pygame.transform.smoothscale(grande, (largura, altura))
    return _miniaturas[chave]


class CenarioMacabro:
    def __init__(self, nome, variante=0, largura=1280, altura=720, hora=1.0, paleta=None):
        chave = f"{nome}_{variante}"
        if chave not in catalogo():
            chave = f"{nome}_0" if f"{nome}_0" in catalogo() else "floresta_0"
        self.chave = chave
        self.largura, self.altura = largura, altura
        self.config = catalogo().get(chave, {})
        # só as cenas a céu aberto mudam com a hora; as outras ficam como foram desenhadas (noite)
        self.hora = max(0.0, min(1.0, hora)) if self.config.get("ciclo") else 1.0
        self.paleta = tuple(paleta) if paleta else None
        self.camadas = [(nome_camada, camada_na_hora(chave, nome_camada, self.hora, self.paleta))
                        for nome_camada in CAMADAS]
        # chão de cada nível da água (o 0 é o chão seco) e camadas extras (ex.: o nó da Rainha no teto)
        self.chaos = [dict(self.camadas)["chao"]] + [camada_na_hora(chave, nome, self.hora, self.paleta)
                                                    for nome in self.config.get("chao_alagado", [])]
        self.agua = 0.0
        self.extras = [(nome, de_baixo, camada_na_hora(chave, nome, self.hora, self.paleta))
                       for nome, de_baixo in self.config.get("camadas_extras", {}).items()]
        self.escondidas = set()
        self.tempo = 0.0
        escuro = self.escuridao()
        self.luzes = [Luz(*dados, intensidade=escuro) for dados in self.config.get("luzes", []) if escuro > 0.15]
        chao = int(altura * 0.74)
        self.particulas = []
        self.nevoas = []
        self.relampago = False
        cor_nevoa = tuple(self.config.get("cor_nevoa", (60, 50, 70)))
        for tipo, quantidade in self.particulas_da_hora():
            if tipo == "nevoa":
                for k in range(quantidade):
                    self.nevoas.append(Nevoa(largura, chao - 70 + k * 46, 140, cor_nevoa, 10 + k * 7, f"{chave}{k}"))
            elif tipo == "relampago":
                self.relampago = True
            elif tipo in TIPOS:
                self.particulas.append(TIPOS[tipo](quantidade, largura, altura, chao))
        self.proximo_raio = random.uniform(3, 7)
        self.clarao = 0.0
        cores_aurora = self.config.get("aurora")
        self.aurora = Aurora(largura, [tuple(c) for c in cores_aurora]) if cores_aurora else None

    def escuridao(self):
        """0 de dia, 1 à noite (as luzes do cenário acendem conforme escurece)."""
        return max(0.0, min(1.0, (self.hora - 0.35) / 0.5))

    def particulas_da_hora(self):
        """Vagalumes só quando escurece; de dia, um pouco de poeira dourada no ar."""
        lista = []
        escuro = self.escuridao()
        for tipo, quantidade in self.config.get("particulas", []):
            if tipo == "vaga_lume" or tipo in self.config.get("noturnas", ()):    # só aparecem quando escurece
                quantidade = round(quantidade * escuro)
            if quantidade > 0:
                lista.append([tipo, quantidade])
        if self.config.get("ciclo") and escuro < 0.6:
            lista.append(["poeira", round(18 * (1 - escuro))])
        return lista

    @property
    def nome_da_hora(self):
        return nome_da_hora(self.hora)

    def atualizar(self, dt):
        self.tempo += dt
        for grupo in self.particulas:
            grupo.atualizar(dt)
        for nevoa in self.nevoas:
            nevoa.atualizar(dt)
        if self.relampago:
            self.proximo_raio -= dt
            self.clarao = max(0.0, self.clarao - dt * 3)
            if self.proximo_raio <= 0:
                self.clarao = 1.0
                self.proximo_raio = random.uniform(4, 9)

    def deslocamento(self, nome_camada):
        amplitude = BALANCO[nome_camada]
        fase = CAMADAS.index(nome_camada)
        return round(math.sin(self.tempo * 0.25 + fase) * amplitude) * VEZES - MARGEM * VEZES

    def na_tela(self, ponto):
        """Um ponto do cenarios.json (escala 352x180) na tela."""
        return (ponto[0] - MARGEM) * VEZES, ponto[1] * VEZES

    def alagar(self, nivel):
        """Nível da água (0 seco a 3 alto; entre dois níveis, os dois chãos se misturam)."""
        self.agua = max(0.0, min(float(len(self.chaos) - 1), nivel))

    def esconder(self, nome):
        """Tira uma camada extra (ex.: o nó da Rainha pendurado, quando ela desce para a luta)."""
        self.escondidas.add(nome)

    def desenhar_chao(self, tela, y):
        """O chão do nível da água; entre dois níveis, o de cima aparece por cima, transparente."""
        x = self.deslocamento("chao")
        nivel = int(self.agua)
        if self.chaos[nivel] is not None:
            tela.blit(self.chaos[nivel], (x, y))
        fracao = self.agua - nivel
        if fracao > 0.02 and nivel + 1 < len(self.chaos) and self.chaos[nivel + 1] is not None:
            de_cima = self.chaos[nivel + 1]
            de_cima.set_alpha(int(255 * fracao))
            tela.blit(de_cima, (x, y))
            de_cima.set_alpha(255)                      # (a imagem é guardada e usada por outros cenários)

    def desenhar(self, tela, y=0):
        tela.fill((6, 4, 8))
        for nome_camada, imagem in self.camadas:
            if imagem is None or nome_camada == "frente":
                continue
            if nome_camada == "chao":
                self.desenhar_chao(tela, y)
            else:
                tela.blit(imagem, (self.deslocamento(nome_camada), y))
            for nome, de_baixo, extra in self.extras:
                if de_baixo == nome_camada and extra is not None and nome not in self.escondidas:
                    tela.blit(extra, (self.deslocamento(nome_camada), y))
            if nome_camada == "ceu" and self.aurora is not None:
                self.aurora.desenhar(tela, self.tempo)
            if nome_camada == "meio":
                for luz in self.luzes:
                    luz.desenhar(tela, self.tempo, self.deslocamento("meio") + MARGEM * VEZES)
        for grupo in self.particulas:
            if not grupo.frente:
                grupo.desenhar(tela)
        if self.clarao > 0.6:
            claro = pygame.Surface(tela.get_size())
            claro.fill((40, 30, 50))
            tela.blit(claro, (0, 0), special_flags=pygame.BLEND_ADD)

    def desenhar_frente(self, tela, y=0):
        for grupo in self.particulas:
            if grupo.frente:
                grupo.desenhar(tela)
        for nevoa in self.nevoas:
            nevoa.desenhar(tela)
        imagem = dict(self.camadas).get("frente")
        if imagem is not None:
            tela.blit(imagem, (self.deslocamento("frente"), y))
