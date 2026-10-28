"""Objetos da cena do acampamento (etapa 5: redesenhados com mais detalhe, na escala 2 dos personagens).

    fogueira                 anel de pedras com musgo, toras com casca e pontas em brasa, chamas em camadas
    taverna_fundo/_balcao    a barraca do Taverneiro em duas folhas (mesma célula e âncora): o fundo, o
                             Taverneiro no meio e o balcão por cima dele
    tenda_grande(_marrom)    lona costurada em gomos, remendos, cordas, estacas e a entrada acesa
    estande_de_armas         o Arsenal: cavalete com alabarda, lança, espada, machado, escudos, elmo e flâmula
    bau_ornamentado          o Baú das skins: madeira com ferragens douradas, tecidos e um chapéu escapando
    espelho_antigo           moldura dourada com crânio alado e névoa girando no vidro
    poste_de_lanterna        poste de ferro batido com volutas e lanterna de vidro
    tronco, barril, caixotes, lenha, caldeirao, pilha_de_livros
    novos: atril_do_grimorio, carroca, estandarte_da_expedicao, circulo_de_runas, tapete

São "bestas" sem corpo: pose() só devolve a fase da animação (chamas, luzes e panos mexendo).
"""
import math

from ..motor import Mat, metal, v2, lerp
from .. import fx
from .bestas import Besta
from .herois import FERRO, MADEIRA

# ---------------- materiais ----------------
MADEIRA_CLARA = Mat((132, 90, 54), 6, ruido=0.3)
MADEIRA_ESCURA = Mat((72, 48, 32), 6, ruido=0.3)
MADEIRA_VELHA = Mat((98, 70, 48), 6, ruido=0.45, relevo=0.9)
CASCA = Mat((78, 58, 44), 6, ruido=0.55, relevo=1.1)
CERNE = Mat((176, 132, 84), 5, ruido=0.2, relevo=0.6)
PEDRA = Mat((96, 90, 100), 5, relevo=1.2, ruido=0.3)
PEDRA_CLARA = Mat((120, 114, 122), 5, relevo=1.3, ruido=0.35)
MUSGO = (58, 84, 52)
LONA = Mat((150, 50, 46), 6, relevo=0.6, ruido=0.1)
LONA_CLARA = Mat((210, 190, 152), 6, relevo=0.6, ruido=0.1)
OURO = metal((190, 146, 64), especular=(255, 240, 180))
OURO_ESCURO = metal((126, 90, 42))
FERRO_BATIDO = metal((84, 82, 94))
ACO = metal((176, 178, 192), especular=(255, 255, 255))
COURO = Mat((96, 60, 38), 5, relevo=0.8, ruido=0.2)
BRASA = (255, 150, 60)


class ObjetoDeCena(Besta):
    S = 60
    proporcao = (1.6, 1.6)          # largura e altura da célula, em S
    pe = 0.5                         # onde fica a âncora na largura
    geo_rapida = True

    def __init__(self, **kw):
        super().__init__(**kw)
        S = self.S
        self.H = S
        self.larg, self.alt = int(S * self.proporcao[0]), int(S * self.proporcao[1])
        self.ancora = (int(self.larg * self.pe), self.alt - 3)

    def pose(self, ctx):
        return {"fase": ctx.a, "i": ctx.i}


# ============================================================
# AJUDANTES
# ============================================================

def lanterna(tela, ponta, fase, tam=1.0, cor=(255, 206, 110)):
    """Lanterna de ferro com vidros, telhadinho e argola, pendurada num gancho; a chama treme."""
    corpo = ponta + v2(0, 7 * tam)
    tela.traco(ponta, corpo + v2(0, -5 * tam), FERRO[1])
    tela.pintar(tela.circulo(ponta + v2(0, 1), 1.2 * tam), FERRO)
    vidro = tela.poly([corpo + v2(-3, -4) * tam, corpo + v2(3, -4) * tam, corpo + v2(3.6, 4) * tam, corpo + v2(-3.6, 4) * tam])
    tela.chapado(vidro, cor, emite=True)
    tela.chapado(tela.poly([corpo + v2(-1, -1) * tam, corpo + v2(1, -1) * tam, corpo + v2(1.2, 3) * tam,
                            corpo + v2(-1.2, 3) * tam]), (255, 248, 210), emite=True)
    for dx in (-3.3, 0, 3.3):                                       # grade de ferro
        tela.traco(corpo + v2(dx * 0.95, -4) * tam, corpo + v2(dx * 1.05, 4) * tam, FERRO[0])
    tela.pintar(tela.poly([corpo + v2(-4.5, -4) * tam, corpo + v2(4.5, -4) * tam, corpo + v2(0, -7.5) * tam]), FERRO.escuro(1))
    tela.pintar(tela.poly([corpo + v2(-4, 4) * tam, corpo + v2(4, 4) * tam, corpo + v2(3, 5.5) * tam, corpo + v2(-3, 5.5) * tam]), FERRO)
    tela.brilho(corpo, (14 + math.sin(fase * 2) * 1.5) * tam, (255, 170, 80), 0.75)


def pedra(tela, c, rx, ry, mat=PEDRA, musgo=False, aquecida=0.0):
    """Pedra arredondada com sombreado, musgo em cima e (aquecida) o lado do fogo alaranjado."""
    m = tela.elipse(c[0], c[1], rx, ry)
    tela.pintar(m, mat)
    if musgo:
        tela.chapado(m & tela.elipse(c[0] - rx * 0.2, c[1] - ry * 0.8, rx * 0.7, ry * 0.45), MUSGO)
        tela.px(c[0] - rx * 0.4, c[1] - ry * 0.55, (84, 116, 70))
    if aquecida:
        tela.tingir(m & tela.elipse(c[0], c[1] - ry * 0.5, rx * 0.9, ry * 0.6), (255, 140, 60), aquecida)
    return m


def tora(tela, a, b, r, mat=CASCA, ponta=True, brasa=False):
    """Tora com casca (riscos de textura), e a ponta cortada com os anéis do cerne."""
    tela.pintar(tela.capsula(a, b, r, r * 0.92), mat)
    d = b - a
    comp = math.hypot(*d) or 1
    n = v2(-d[1], d[0]) / comp
    for k in range(int(comp / 4)):                                 # riscos da casca
        p = lerp(a, b, (k + 0.5) / max(1, int(comp / 4)))
        lado = (k % 3 - 1) * 0.45
        tela.traco(p + n * r * lado - d / comp * 1.5, p + n * r * lado + d / comp * 1.5, mat[0], sobre=True)
    tela.traco(a - n * r * 0.55, b - n * r * 0.5, mat[4], sobre=True)              # luz de cima
    if ponta:
        tela.pintar(tela.elipse_girada(b, r * 0.45, r * 0.95, math.atan2(d[1], d[0])), CERNE)
        tela.chapado(tela.elipse_girada(b, r * 0.18, r * 0.45, math.atan2(d[1], d[0])), CERNE[1])
        tela.px(b[0], b[1], CERNE[0])
    if brasa:
        tela.chapado(tela.elipse_girada(a, r * 0.5, r * 0.9, math.atan2(d[1], d[0])), (40, 20, 18))
        tela.chapado(tela.elipse_girada(a, r * 0.28, r * 0.55, math.atan2(d[1], d[0])), BRASA, emite=True)
        tela.traco(a + d / comp * 2, a + d / comp * 6 + n * 1.5, (255, 110, 40), emite=True, sobre=True)


def flamula(tela, topo, comp, alt, fase, cor, cor_borda=(220, 180, 90), pontas=2):
    """Bandeirola de pano que ondula com o vento (fase), presa num mastro em 'topo'."""
    pts_cima, pts_baixo = [], []
    for k in range(9):
        t = k / 8
        onda = math.sin(fase + t * 4) * 2.2 * t
        pts_cima.append(topo + v2(t * comp, onda))
        pts_baixo.append(topo + v2(t * comp, alt * (1 - 0.15 * t) + onda))
    if pontas == 2:
        fim = [pts_cima[-1], pts_cima[-1] + v2(-comp * 0.18, alt * 0.5), pts_baixo[-1]]
    else:
        fim = [pts_cima[-1], pts_baixo[-1]]
    pano = tela.poly(pts_cima + fim[1:-1] + list(reversed(pts_baixo)))
    tela.pintar(pano, Mat(cor, 5, relevo=0.7, ruido=0.1))
    tela.tracos(pts_cima, cor_borda, sobre=True)
    return pano


# ============================================================
# FOGUEIRA
# ============================================================

def lingua_de_fogo(tela, base, altura, largura, fase, inclina=0.0, cores=fx.FOGO):
    """Uma língua de fogo em gota: fundo arredondado, barriga larga e ponta fina que ondula.

    Camadas de fora (vermelho) para dentro (miolo quase branco), cada uma menor e um pouco mais alta na base.
    """
    camadas = len(cores) - 1
    for k in range(camadas):
        esc = 1 - k / (camadas + 0.4)
        h, w = altura * esc, largura * esc * 0.5
        b = base + v2(0, -altura * 0.05 * k)
        lados = []
        n = 18
        for i in range(n + 1):
            t = i / n
            meia = w * math.sin(math.pi * (0.22 + 0.78 * t)) ** 0.9
            meio = inclina * t * t * h + math.sin(fase * 2 + t * 5 + k) * w * 0.22 * t
            lados.append((b + v2(meio, -t * h), meia))
        pts = [p + v2(-m, 0) for p, m in lados] + [p + v2(m, 0) for p, m in reversed(lados)]
        for i in range(1, 8):
            a = math.pi * i / 8
            pts.append(b + v2(math.cos(a) * w * 0.78, math.sin(a) * w * 0.45))
        tela.chapado(tela.poly(pts), cores[k + 1], emite=True)


class Fogueira(ObjetoDeCena):
    nome = "fogueira"
    S = 64
    proporcao = (2.2, 2.5)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        c = v2(cx, chao - 0.12 * S)
        f = P["fase"]
        rng = tela.random
        # chão chamuscado e cinzas
        tela.chapado(tela.elipse(c[0], c[1] + 0.02 * S, 0.86 * S, 0.2 * S), (34, 24, 24))
        tela.chapado(tela.elipse(c[0], c[1] + 0.01 * S, 0.66 * S, 0.14 * S), (52, 40, 38))
        # pedras de trás (o lado de dentro, virado para o fogo, fica alaranjado)
        for k in range(10):
            a = math.pi + (k + 0.5) / 10 * math.pi
            p = c + v2(math.cos(a) * 0.68 * S, math.sin(a) * 0.17 * S)
            pedra(tela, p, (0.1 + 0.03 * ((k * 7) % 3)) * S, 0.075 * S, PEDRA.escuro(1), musgo=k % 4 == 1, aquecida=0.35)
        # cama de brasas, com rachaduras acesas
        tela.chapado(tela.elipse(c[0], c[1] - 0.02 * S, 0.46 * S, 0.12 * S), (90, 26, 14), emite=True)
        tela.chapado(tela.elipse(c[0], c[1] - 0.03 * S, 0.36 * S, 0.085 * S), (200, 70, 22), emite=True)
        tela.chapado(tela.elipse(c[0], c[1] - 0.035 * S, 0.22 * S, 0.05 * S), (255, 160, 60), emite=True)
        for k in range(14):
            p = c + v2(rng.uniform(-0.4, 0.4) * S, rng.uniform(-0.08, 0.04) * S)
            tela.px(p[0], p[1], fx.FOGO[3] if (P["i"] + k) % 3 else (90, 30, 20), emite=True)
        # toras de trás (em pé, formando a cabaninha)
        tora(tela, c + v2(-0.34 * S, -0.02 * S), c + v2(0.02 * S, -0.5 * S), 0.06 * S, ponta=False, brasa=True)
        tora(tela, c + v2(0.36 * S, -0.02 * S), c + v2(0.0, -0.5 * S), 0.06 * S, ponta=False, brasa=True)
        # chamas: línguas em gota que sobem de dentro das toras
        linguas = ((-0.3, 0.46, 0.22, -0.35, 1.3), (0.3, 0.52, 0.22, 0.3, 2.2), (-0.13, 0.78, 0.28, -0.15, 0.4),
                   (0.15, 0.86, 0.28, 0.12, 3.1), (0.0, 1.1, 0.34, 0.0, 0.0))
        for dx, alto, largo, inclina, atraso in linguas:
            altura = S * alto * (1 + 0.08 * math.sin(f * 2 + atraso * 2))
            lingua_de_fogo(tela, c + v2(dx * S, -0.06 * S), altura, S * largo, f + atraso, inclina)
        # toras da frente cruzadas (cerne claro na ponta de fora, brasa na de dentro)
        tora(tela, c + v2(0.28 * S, -0.1 * S), c + v2(-0.58 * S, 0.06 * S), 0.075 * S)
        tora(tela, c + v2(-0.26 * S, -0.08 * S), c + v2(0.6 * S, 0.08 * S), 0.075 * S)
        for p in (c + v2(0.24 * S, -0.1 * S), c + v2(-0.22 * S, -0.08 * S)):
            tela.chapado(tela.circulo(p, 0.035 * S), BRASA, emite=True)
        # faíscas subindo em espiral
        for k in range(9):
            t = (P["i"] / 4 + k / 9) % 1
            p = c + v2(math.sin(k * 2.3 + f + t * 4) * 0.32 * S, -1.05 * S - t * 0.5 * S)
            tela.px(p[0], p[1], fx.FOGO[3 if k % 2 else 2], emite=True)
        # pedras da frente, maiores, com o topo iluminado pelo fogo
        for k in range(9):
            a = (k + 0.5) / 9 * math.pi
            p = c + v2(math.cos(a) * 0.7 * S, math.sin(a) * 0.17 * S + 0.03 * S)
            pedra(tela, p, (0.12 + 0.025 * ((k * 5) % 3)) * S, 0.085 * S, PEDRA_CLARA if k % 3 else PEDRA,
                  musgo=k % 4 == 0, aquecida=0.45)
        tela.brilho(c + v2(0, -0.35 * S), 0.9 * S, (255, 150, 60), 0.35)


# ============================================================
# BARRACA DA TAVERNA
# ============================================================

GARRAFAS = [((120, 40, 40), "redonda"), ((60, 110, 60), "alta"), ((150, 120, 50), "jarro"), ((70, 70, 140), "alta"),
            ((190, 170, 140), "redonda"), ((110, 50, 120), "alta"), ((60, 90, 70), "jarro")]


def garrafa(tela, base, cor, tipo, alt=1.0):
    vidro = Mat(cor, 4, especular=(255, 255, 240), relevo=1.4)
    if tipo == "redonda":
        tela.pintar(tela.circulo(base + v2(0, -3.2 * alt), 3.2 * alt), vidro)
        tela.pintar(tela.capsula(base + v2(0, -6 * alt), base + v2(0, -9 * alt), 0.9), vidro.escuro(1))
    elif tipo == "jarro":
        tela.pintar(tela.capsula(base + v2(0, -1), base + v2(0, -6 * alt), 2.8 * alt, 2.2 * alt), Mat(cor, 4, relevo=1.0))
        tela.pintar(tela.capsula(base + v2(2.5, -5 * alt), base + v2(3.5, -2 * alt), 0.7), Mat(cor, 4).escuro(1))
    else:
        tela.pintar(tela.capsula(base + v2(0, -1.5), base + v2(0, -8 * alt), 2.2, 1.9), vidro)
        tela.pintar(tela.capsula(base + v2(0, -8 * alt), base + v2(0, -12 * alt), 0.9), vidro.escuro(1))
    tela.chapado(tela.circulo(base + v2(0, -12.6 * alt if tipo == "alta" else -9.6 * alt), 0.9), (150, 110, 70))


class BarracaDaTaverna(ObjetoDeCena):
    nome = "taverna_fundo"
    S = 66
    proporcao = (3.3, 2.1)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        esq, dir_ = cx - 1.05 * S, cx + 1.05 * S
        topo = chao - 1.42 * S
        # parede de tábuas no fundo, com tábuas de tons diferentes e pregos
        parede = tela.poly([v2(esq + 4, chao - 0.3 * S), v2(dir_ - 4, chao - 0.3 * S), v2(dir_ - 4, topo + 0.18 * S),
                            v2(esq + 4, topo + 0.18 * S)])
        tela.pintar(parede, MADEIRA_ESCURA.escuro(1), plano=True)
        for k in range(12):
            x0 = esq + 4 + k * (dir_ - esq - 8) / 12
            x1 = x0 + (dir_ - esq - 8) / 12
            tabua = tela.poly([v2(x0, chao - 0.3 * S), v2(x1, chao - 0.3 * S), v2(x1, topo + 0.18 * S), v2(x0, topo + 0.18 * S)])
            if k % 3 == 1:
                tela.tingir(tabua, (60, 40, 30), 0.35)
            tela.traco(v2(x0, topo + 0.18 * S), v2(x0, chao - 0.3 * S), MADEIRA_ESCURA[0], sobre=True)
            tela.px(x0 + 2, topo + 0.24 * S, FERRO[3])
        # caveira de cervo com chifres no alto da parede (troféu da casa)
        cerv = v2(cx, topo + 0.32 * S)
        for lado in (-1, 1):
            tela.tracos([cerv + v2(lado * 3, -2), cerv + v2(lado * 9, -9), cerv + v2(lado * 11, -15)], (214, 200, 170))
            tela.traco(cerv + v2(lado * 8, -8), cerv + v2(lado * 14, -9), (214, 200, 170))
            tela.traco(cerv + v2(lado * 10, -12), cerv + v2(lado * 7, -16), (214, 200, 170))
        tela.pintar(tela.poly([cerv + v2(-4, -3), cerv + v2(4, -3), cerv + v2(2, 6), cerv + v2(-2, 6)]), Mat((220, 208, 180), 5))
        tela.chapado(tela.circulo(cerv + v2(-1.6, 0), 0.9) | tela.circulo(cerv + v2(1.6, 0), 0.9), (20, 10, 16))
        # prateleiras com garrafas variadas e um barrilzinho com torneira
        for n, y in enumerate((topo + 0.6 * S, topo + 0.9 * S)):
            tela.pintar(tela.capsula(v2(esq + 10, y), v2(dir_ - 10, y), 2.2), MADEIRA_CLARA)
            for lado in (-1, 1):                                   # mãos-francesas
                x = cx + lado * 0.75 * S
                tela.traco(v2(x, y + 1), v2(x + lado * 4, y + 6), MADEIRA_ESCURA[2])
            k = 0
            x = esq + 16
            while x < dir_ - 16:
                if n == 1 and abs(x - cx) < 0.18 * S:               # o barrilzinho no meio da prateleira de baixo
                    tela.pintar(tela.elipse(cx, y - 6, 8, 6), MADEIRA_CLARA)
                    for dy in (-9, -3):
                        tela.traco(v2(cx - 7, y + dy), v2(cx + 7, y + dy), FERRO[2], sobre=True)
                    tela.pintar(tela.circulo(v2(cx, y - 6), 2.4), MADEIRA_ESCURA)
                    tela.pintar(tela.capsula(v2(cx, y - 4), v2(cx, y + 1), 0.8), metal((170, 140, 70)))
                    x = cx + 0.18 * S + 2
                    continue
                cor, tipo = GARRAFAS[(k + n * 3) % len(GARRAFAS)]
                garrafa(tela, v2(x, y - 1.5), cor, tipo, 0.9 + 0.15 * ((k * 3 + n) % 3))
                x += 8 + (k % 2) * 2
                k += 1
        # ervas secando e linguiças penduradas na viga de cima
        viga = topo + 0.2 * S
        tela.pintar(tela.capsula(v2(esq, viga), v2(dir_, viga), 2.6), MADEIRA)
        for k in range(7):
            x = esq + 18 + k * (dir_ - esq - 36) / 6
            balanco = math.sin(f + k) * 0.8
            if k % 2:
                for j in range(3):                                  # linguiças em gomos
                    tela.pintar(tela.capsula(v2(x + balanco * j * 0.4, viga + 3 + j * 4.5),
                                             v2(x + balanco * (j + 1) * 0.4, viga + 6 + j * 4.5), 1.6),
                                Mat((150, 70, 60), 4, relevo=1.2))
            else:
                tela.traco(v2(x, viga), v2(x + balanco, viga + 4), (150, 130, 90))
                for j in range(5):                                  # maço de ervas de cabeça para baixo
                    tela.traco(v2(x + balanco, viga + 4), v2(x + balanco + (j - 2) * 1.2, viga + 11), (80 + j * 8, 120, 60))
        # quadro-negro com o "cardápio" riscado em giz
        quadro = v2(dir_ - 0.28 * S, topo + 1.06 * S)
        tela.pintar(tela.poly([quadro + v2(-9, -7), quadro + v2(9, -7), quadro + v2(9, 7), quadro + v2(-9, 7)]), MADEIRA_CLARA)
        tela.chapado(tela.poly([quadro + v2(-7, -5), quadro + v2(7, -5), quadro + v2(7, 5), quadro + v2(-7, 5)]), (30, 36, 34))
        for j in range(4):
            tela.traco(quadro + v2(-5, -3 + j * 2.2), quadro + v2(1 + (j * 3) % 5, -3 + j * 2.2), (200, 204, 196))
        # postes entalhados com base de pedra
        for x in (esq, dir_):
            tela.pintar(tela.capsula(v2(x, chao - 2), v2(x, topo - 6), 4.2), MADEIRA)
            for y in (topo + 0.4 * S, topo + 0.9 * S):
                tela.traco(v2(x - 3, y), v2(x + 3, y), MADEIRA[1], sobre=True)
            pedra(tela, v2(x, chao - 3), 6, 3.5, PEDRA)
        # toldo listrado em duas águas, com barra recortada e debrum dourado
        borda_y = topo + 0.14 * S
        roof = [v2(esq - 16, borda_y), v2(cx, topo - 0.32 * S), v2(dir_ + 16, borda_y)]
        recorte = []
        for k in range(17):
            x = esq - 16 + k * (dir_ - esq + 32) / 16
            recorte.append(v2(x, borda_y + (7 if k % 2 else 1)))
        tela.pintar(tela.poly(roof + list(reversed(recorte))), LONA)
        for k in range(8):
            x0 = esq - 16 + (2 * k + 1) * (dir_ - esq + 32) / 16
            faixa = [v2(x0 - 3, borda_y + 7), v2(x0 + (dir_ - esq) / 30, borda_y + 1),
                     lerp(roof[1], v2(x0, borda_y), 0.18), lerp(roof[1], v2(x0 - 7, borda_y), 0.22)]
            tela.pintar(tela.poly(faixa), LONA_CLARA)
        tela.tracos(recorte, (220, 176, 80), sobre=True)
        tela.traco(roof[1], roof[1] + v2(0, -5), MADEIRA[2])
        tela.pintar(tela.circulo(roof[1] + v2(0, -6), 2.2), OURO)
        # cordão de luzinhas na beira do toldo
        for k in range(9):
            t = (k + 0.5) / 9
            p = lerp(v2(esq - 8, borda_y + 9), v2(dir_ + 8, borda_y + 9), t) + v2(0, math.sin(t * math.pi) * 5)
            acesa = (k + P["i"]) % 3 != 0
            tela.chapado(tela.circulo(p, 1.3), (255, 214, 120) if acesa else (180, 120, 60), emite=True)
            if acesa:
                tela.brilho(p, 4, (255, 190, 90), 0.4)
        # lanternas nas pontas do toldo
        for x in (esq + 0.15 * S, dir_ - 0.15 * S):
            lanterna(tela, v2(x, borda_y + 8), f + x)
        # placa da caneca pendurada em correntes no poste da direita
        placa = v2(dir_ + 20, topo + 0.46 * S)
        braco_ = v2(dir_, topo + 0.24 * S)
        tela.pintar(tela.capsula(braco_, braco_ + v2(28, 0), 1.6), FERRO_BATIDO)
        for dx in (-8, 8):
            tela.traco(braco_ + v2(20 + dx, 0), placa + v2(dx, -10), FERRO[2])
        tela.pintar(tela.poly([placa + v2(-12, -10), placa + v2(12, -10), placa + v2(12, 10), placa + v2(-12, 10)]), MADEIRA_CLARA)
        tela.traco(placa + v2(-11, -9), placa + v2(11, -9), (220, 176, 80))
        tela.traco(placa + v2(-11, 9), placa + v2(11, 9), (220, 176, 80))
        tela.pintar(tela.poly([placa + v2(-6, -5), placa + v2(4, -5), placa + v2(4, 7), placa + v2(-6, 7)]),
                    Mat((220, 170, 60), 5, especular=(255, 240, 180)))
        tela.pintar(tela.capsula(placa + v2(4, -2), placa + v2(8, 3), 1.6), Mat((220, 170, 60), 5))
        tela.chapado(tela.elipse(placa[0] - 1, placa[1] - 6, 6, 2.2), (250, 245, 230))
        # pilha de barris à esquerda e caixote com garrafas à direita
        for x, y, r in ((esq - 10, chao, 0.2), (esq + 12, chao, 0.2), (esq + 1, chao - 0.42 * S, 0.19)):
            b = v2(x, y)
            corpo = tela.elipse(b[0], b[1] - r * S, r * 0.85 * S, r * 1.05 * S)
            tela.pintar(corpo, MADEIRA_CLARA)
            for dy in (-1.6, -1.0, -0.4):
                tela.traco(b + v2(-r * 0.8 * S, dy * r * S), b + v2(r * 0.8 * S, dy * r * S), FERRO[2], sobre=True)
            tela.pintar(tela.elipse(b[0], b[1] - r * 2 * S + 2, r * 0.6 * S, 1.6), MADEIRA_ESCURA)
        caixa = v2(dir_ + 26, chao)
        tela.pintar(tela.poly([caixa + v2(-12, 0), caixa + v2(12, 0), caixa + v2(12, -13), caixa + v2(-12, -13)]), MADEIRA_CLARA)
        tela.traco(caixa + v2(-12, -6), caixa + v2(12, -6), MADEIRA_CLARA[1], sobre=True)
        for k in range(4):
            cor, tipo = GARRAFAS[k + 2]
            garrafa(tela, caixa + v2(-8 + k * 5.3, -12), cor, "alta", 0.8)


class BalcaoDaTaverna(BarracaDaTaverna):
    """A frente do balcão: tábuas, painéis entalhados, canecas, garrafa, vela e um pano (por cima do Taverneiro)."""
    nome = "taverna_balcao"

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        esq, dir_ = cx - 0.95 * S, cx + 0.95 * S
        topo = chao - 0.44 * S
        frente = tela.poly([v2(esq, chao), v2(dir_, chao), v2(dir_, topo), v2(esq, topo)])
        tela.pintar(frente, MADEIRA_CLARA)
        for k in range(4):                                         # painéis entalhados
            x0 = esq + 5 + k * (dir_ - esq - 10) / 4
            x1 = x0 + (dir_ - esq - 10) / 4 - 4
            painel = tela.poly([v2(x0, chao - 4), v2(x1, chao - 4), v2(x1, topo + 6), v2(x0, topo + 6)])
            tela.pintar(painel, MADEIRA_CLARA.escuro(1))
            tela.traco(v2(x0, topo + 6), v2(x1, topo + 6), MADEIRA_CLARA[4], sobre=True)
            m = v2((x0 + x1) / 2, (chao + topo) / 2 + 1)
            tela.pintar(tela.poly([m + v2(0, -4), m + v2(3, 0), m + v2(0, 4), m + v2(-3, 0)]), OURO_ESCURO)
        tela.pintar(tela.capsula(v2(esq - 6, topo), v2(dir_ + 6, topo), 3.4), MADEIRA)
        tela.traco(v2(esq - 4, topo - 2), v2(dir_ + 4, topo - 2), MADEIRA[4], sobre=True)
        # pano xadrez caído na ponta do balcão
        pano = tela.poly([v2(esq + 2, topo - 2), v2(esq + 16, topo - 2), v2(esq + 14, topo + 14), v2(esq + 4, topo + 12)])
        tela.pintar(pano, Mat((170, 60, 50), 5, relevo=0.6))
        for k in range(3):
            tela.traco(v2(esq + 4 + k * 4, topo - 1), v2(esq + 5 + k * 4, topo + 12), (220, 200, 170), sobre=True)
        for x in (esq + 0.3 * S, esq + 0.48 * S, dir_ - 0.62 * S):  # canecas com espuma
            tela.pintar(tela.poly([v2(x - 4, topo - 2), v2(x + 4, topo - 2), v2(x + 4, topo - 12), v2(x - 4, topo - 12)]),
                        MADEIRA_ESCURA)
            tela.traco(v2(x - 4, topo - 5), v2(x + 4, topo - 5), FERRO[2], sobre=True)
            tela.pintar(tela.capsula(v2(x + 5, topo - 9), v2(x + 5, topo - 4), 1.2), MADEIRA_ESCURA)
            tela.chapado(tela.elipse(x, topo - 13, 4.8, 2.0), (250, 240, 220))
            tela.px(x - 2, topo - 11, (250, 240, 220))
        garrafa(tela, v2(dir_ - 0.42 * S, topo - 2), (70, 120, 70), "alta")
        vela = v2(dir_ - 0.2 * S, topo - 2)
        tela.pintar(tela.elipse(vela[0], vela[1], 3.5, 1.2), metal((170, 140, 70)))
        tela.pintar(tela.capsula(vela, vela + v2(0, -8), 1.7), Mat((236, 226, 196), 4))
        tela.chapado(tela.poly([vela + v2(1.5, -6), vela + v2(2.2, -3), vela + v2(1.2, -4)]), (236, 226, 196))
        fx.chama(tela, vela + v2(0, -9), 5.5, 3, fase=P["fase"] * 2, brilho=False)
        tela.brilho(vela + v2(0, -11), 11, (255, 190, 100), 0.6)


# ============================================================
# TRONCO, LIVROS, LANTERNA
# ============================================================

class Tronco(ObjetoDeCena):
    """Tronco deitado para sentar: casca com textura, musgo, um galhinho e os anéis no corte."""
    nome = "tronco"
    S = 30
    proporcao = (2.3, 1.0)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        a, b = v2(cx - 0.82 * S, chao - 0.3 * S), v2(cx + 0.82 * S, chao - 0.3 * S)
        tela.chapado(tela.elipse(cx, chao - 1, 0.9 * S, 0.08 * S), (18, 16, 20))
        tora(tela, a, b, 0.3 * S)
        tela.chapado(tela.elipse(cx - 0.3 * S, chao - 0.55 * S, 0.22 * S, 0.06 * S) & tela.capsula(a, b, 0.3 * S), MUSGO)
        for k in range(5):
            tela.px(cx - 0.45 * S + k * 3, chao - 0.57 * S, (84, 116, 70))
        tela.pintar(tela.capsula(v2(cx + 0.2 * S, chao - 0.5 * S), v2(cx + 0.3 * S, chao - 0.75 * S), 1.2), CASCA)
        tela.pintar(tela.circulo(v2(cx + 0.3 * S, chao - 0.78 * S), 1.6), Mat((90, 120, 70), 4))


class PilhaDeLivros(ObjetoDeCena):
    """Livros empilhados (lombadas com faixas douradas), pergaminhos e uma vela pingando cera."""
    nome = "pilha_de_livros"
    S = 34
    proporcao = (2.0, 2.1)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        y = chao
        livros = (((100, 40, 36), 0.72), ((50, 70, 110), 0.62), ((60, 100, 60), 0.68), ((120, 90, 40), 0.52), ((80, 40, 80), 0.46))
        for k, (cor, larg) in enumerate(livros):
            alt = 0.15 * S
            dx = ((k * 5) % 3 - 1) * 2
            capa = tela.poly([v2(cx - larg * S + dx, y), v2(cx + larg * S + dx, y), v2(cx + larg * S + dx, y - alt),
                              v2(cx - larg * S + dx, y - alt)])
            tela.pintar(capa, Mat(cor, 5, relevo=0.8))
            tela.traco(v2(cx - larg * S + dx + 2, y - alt * 0.5), v2(cx + larg * S + dx - 4, y - alt * 0.5), (226, 212, 176))
            for t in (0.2, 0.75):
                x = cx - larg * S + dx + t * 2 * larg * S
                tela.traco(v2(x, y - alt + 1), v2(x, y - 1), (220, 180, 80), sobre=True)
            y -= alt
        # pergaminho enrolado encostado na pilha
        tela.pintar(tela.capsula(v2(cx + 0.78 * S, chao - 2), v2(cx + 0.5 * S, chao - 0.48 * S), 2.4), Mat((216, 198, 152), 5))
        tela.chapado(tela.circulo(v2(cx + 0.5 * S, chao - 0.48 * S), 1.6), (180, 160, 120))
        tela.traco(v2(cx + 0.66 * S, chao - 0.2 * S), v2(cx + 0.7 * S, chao - 0.28 * S), (160, 40, 40))
        vela = v2(cx + 0.08 * S, y)
        tela.pintar(tela.elipse(vela[0], vela[1], 4, 1.4), metal((170, 140, 70)))
        tela.pintar(tela.capsula(vela, vela + v2(0, -0.38 * S), 0.075 * S), Mat((232, 222, 192), 4))
        tela.chapado(tela.poly([vela + v2(2, -0.3 * S), vela + v2(3, -0.12 * S), vela + v2(1.5, -0.18 * S)]), (232, 222, 192))
        fx.chama(tela, vela + v2(0, -0.41 * S), 6 + math.sin(P["fase"] * 2), 3.5, fase=P["fase"] * 2, brilho=False)
        tela.brilho(vela + v2(0, -0.48 * S), 15, (255, 190, 100), 0.6)


class PosteDeLanterna(ObjetoDeCena):
    """Poste de madeira com braço de ferro batido em voluta, lanterna de vidro e argolas para o varal."""
    nome = "poste_de_lanterna"
    S = 70
    proporcao = (1.1, 1.75)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        topo = v2(cx, chao - 1.5 * S)
        pedra(tela, v2(cx, chao - 2), 7, 3.5, PEDRA)
        tela.pintar(tela.capsula(v2(cx, chao - 2), topo, 2.8, 2.3), MADEIRA)
        for y in (chao - 0.5 * S, chao - 1.1 * S):
            tela.pintar(tela.capsula(v2(cx - 3, y), v2(cx + 3, y), 1.2), FERRO_BATIDO)
        braco_ = topo + v2(0.24 * S, 2)
        tela.pintar(tela.capsula(topo + v2(-2, 2), braco_, 1.6), FERRO_BATIDO)
        voluta = [topo + v2(2, 4)] + [topo + v2(4 + math.cos(a) * 4, 9 + math.sin(a) * 4) for a in
                                     [k * 0.6 - 1.4 for k in range(9)]]
        tela.tracos(voluta, FERRO[2])
        tela.pintar(tela.circulo(topo + v2(0, -1), 2.6), OURO)
        lanterna(tela, braco_ + v2(0, 1), P["fase"], 1.25)
        tela.pintar(tela.circulo(v2(cx - 3, topo[1] + 6), 1.4), FERRO)         # argola do varal


# ============================================================
# ESPELHO ANTIGO
# ============================================================

class EspelhoAntigo(ObjetoDeCena):
    nome = "espelho_antigo"
    S = 60
    proporcao = (1.4, 1.9)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        ouro, ouro_escuro = metal((176, 132, 60), especular=(255, 236, 170)), OURO_ESCURO
        larg, alt = 0.46 * S, 1.42 * S
        base = chao - 0.12 * S
        topo = base - alt
        for lado in (-1, 1):                                         # pés de garra
            pe = v2(cx + lado * 0.3 * S, chao - 2)
            tela.pintar(tela.capsula(v2(cx + lado * 0.12 * S, base), pe, 2.6, 2.0), ouro_escuro)
            for k in (-1, 0, 1):
                tela.pintar(tela.capsula(pe, pe + v2(lado * 3 + k * 2, 2), 1.2), ouro)

        def arco(margem):
            pts = [v2(cx - larg + margem, base - margem)]
            for k in range(13):
                a = math.pi + k / 12 * math.pi
                pts.append(v2(cx + math.cos(a) * (larg - margem), topo + larg + math.sin(a) * (larg - margem)))
            pts.append(v2(cx + larg - margem, base - margem))
            return tela.poly(pts)
        tela.pintar(arco(0), ouro_escuro)
        tela.pintar(arco(2) & ~arco(5), ouro)
        for k in range(10):                                          # contas entalhadas na moldura
            a = math.pi + (k + 0.5) / 10 * math.pi
            tela.px(cx + math.cos(a) * (larg - 3.5), topo + larg + math.sin(a) * (larg - 3.5), (255, 230, 150))
        vidro = arco(6)
        tela.chapado(vidro, (40, 24, 70))
        f = P["fase"]
        for k in range(30):                                          # névoa girando
            a = f * 0.5 + k * 0.7
            r = (0.12 + (k % 7) * 0.045) * S
            p = v2(cx + math.cos(a) * r * 0.8, topo + larg + 0.35 * S + math.sin(a) * r * 1.4)
            tela.chapado(tela.circulo(p, 1.6 + (k % 3)) & vidro, (110 + k * 3, 70 + k * 2, 190), emite=True)
        vulto = v2(cx, topo + larg + 0.55 * S)
        tela.chapado((tela.circulo(vulto + v2(0, -0.2 * S), 0.08 * S) | tela.poly([vulto + v2(-0.13 * S, 0.35 * S),
                      vulto + v2(0.13 * S, 0.35 * S), vulto + v2(0.06 * S, -0.16 * S), vulto + v2(-0.06 * S, -0.16 * S)])) & vidro,
                     (24, 12, 40))
        tela.px(vulto[0] + 2, vulto[1] - 0.21 * S, (220, 160, 255), emite=True)
        tela.brilho(v2(cx, topo + larg + 0.3 * S), 0.5 * S, (150, 90, 230), 0.35 + 0.1 * math.sin(f))
        faixa = (P["i"] / 4) * 2 * larg - larg
        tela.chapado(tela.poly([v2(cx + faixa, topo + 8), v2(cx + faixa + 3, topo + 8), v2(cx + faixa - 8, base - 8),
                                v2(cx + faixa - 11, base - 8)]) & vidro, (190, 170, 240))
        # véu de veludo jogado sobre o canto da moldura
        veu = tela.poly([v2(cx + larg * 0.1, topo + 2), v2(cx + larg + 3, topo + larg * 0.7), v2(cx + larg + 4, topo + larg * 1.9),
                         v2(cx + larg - 2, topo + larg * 1.6), v2(cx + larg * 0.55, topo + larg * 0.5)])
        tela.pintar(veu, Mat((120, 30, 50), 5, relevo=0.9))
        tela.traco(v2(cx + larg + 4, topo + larg * 1.9), v2(cx + larg + 4, topo + larg * 2.1), (220, 176, 80))
        c = v2(cx, topo + 2)                                           # crânio alado no topo
        for lado in (-1, 1):
            tela.pintar(tela.poly([c + v2(lado * 3, 2), c + v2(lado * 14, -6), c + v2(lado * 11, 1), c + v2(lado * 15, 4),
                                   c + v2(lado * 5, 6)]), ouro_escuro)
        tela.pintar(tela.circulo(c, 4.4), Mat((214, 202, 172), 5))
        tela.chapado(tela.circulo(c + v2(-1.6, 0), 1.0) | tela.circulo(c + v2(1.6, 0), 1.0), (20, 10, 20))
        for lado in (-1, 1):
            tela.pintar(tela.circulo(v2(cx + lado * (larg + 1), base - alt * 0.35), 2.6), ouro)


# ============================================================
# BAÚ DAS SKINS
# ============================================================

class BauOrnamentado(ObjetoDeCena):
    """Baú entreaberto com ferragens douradas: tecidos coloridos e um chapéu de pena escapam (são as skins)."""
    nome = "bau_ornamentado"
    S = 52
    proporcao = (1.8, 1.6)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        madeira = Mat((118, 72, 40), 6, ruido=0.35, relevo=1.0)
        larg = 0.64 * S
        topo_caixa = chao - 0.5 * S
        tela.chapado(tela.elipse(cx, chao, larg + 6, 3), (18, 14, 18))
        caixa = tela.poly([v2(cx - larg, chao), v2(cx + larg, chao), v2(cx + larg, topo_caixa), v2(cx - larg, topo_caixa)])
        tela.pintar(caixa, madeira)
        for k in range(1, 4):
            y = topo_caixa + k * 0.12 * S
            tela.traco(v2(cx - larg + 1, y), v2(cx + larg - 1, y), madeira[1], sobre=True)
        # tecidos pendurados para fora (veludo roxo, seda verde com franja dourada)
        for x0, cor, comp in ((cx - larg * 0.7, (120, 40, 140), 0.36), (cx + larg * 0.35, (40, 120, 90), 0.28)):
            onda = math.sin(f + x0) * 1.2
            pano = tela.poly([v2(x0, topo_caixa - 3), v2(x0 + 10, topo_caixa - 3), v2(x0 + 11 + onda, topo_caixa + comp * S),
                              v2(x0 + 1 + onda, topo_caixa + comp * S + 2)])
            tela.pintar(pano, Mat(cor, 5, relevo=0.8, especular=(255, 255, 255)))
            for k in range(5):
                tela.px(x0 + 1.5 + onda + k * 2, topo_caixa + comp * S + 1.5 - k * 0.3, (230, 190, 90))
        # luz dourada escapando pela fresta
        fresta = tela.poly([v2(cx - larg + 3, topo_caixa - 1), v2(cx + larg - 3, topo_caixa - 1),
                            v2(cx + larg - 5, topo_caixa - 4), v2(cx - larg + 5, topo_caixa - 4)])
        tela.chapado(fresta, (255, 214, 110), emite=True)
        tela.brilho(v2(cx, topo_caixa - 5), 0.6 * S, (255, 190, 90), 0.4 + 0.1 * math.sin(f * 2))
        # tampa arredondada entreaberta
        tampa = [v2(cx - larg - 1, topo_caixa - 4)]
        for k in range(9):
            a = math.pi + k / 8 * math.pi
            tampa.append(v2(cx + math.cos(a) * (larg + 1), topo_caixa - 7 + math.sin(a) * 0.26 * S))
        tampa.append(v2(cx + larg + 1, topo_caixa - 4))
        m_tampa = tela.poly(tampa)
        tela.pintar(m_tampa, madeira.claro(1))
        # chapéu de pena sobre a tampa
        chapeu = v2(cx - 0.18 * S, topo_caixa - 0.3 * S)
        tela.pintar(tela.elipse(chapeu[0], chapeu[1], 9, 2.4), Mat((50, 40, 70), 5))
        tela.pintar(tela.elipse(chapeu[0], chapeu[1] - 3.5, 5, 4), Mat((50, 40, 70), 5))
        tela.chapado(tela.poly([chapeu + v2(-5, -2), chapeu + v2(5, -2), chapeu + v2(5, -0.8), chapeu + v2(-5, -0.8)]), (200, 60, 60))
        pena = [chapeu + v2(3, -5), chapeu + v2(9, -14 + math.sin(f) * 1.5), chapeu + v2(14, -18 + math.sin(f) * 2)]
        tela.pintar(tela.corrente(pena, [1.8, 2.2, 0.6]), Mat((230, 220, 200), 5))
        # faixas de ferro com rebites e cantos dourados entalhados
        for x in (cx - larg * 0.55, cx + larg * 0.55):
            faixa = tela.poly([v2(x - 2.5, chao), v2(x + 2.5, chao), v2(x + 2.5, topo_caixa - 0.32 * S), v2(x - 2.5, topo_caixa - 0.32 * S)])
            tela.pintar(faixa & (caixa | m_tampa), FERRO_BATIDO)
            for y in range(int(topo_caixa - 0.22 * S), int(chao), 4):
                tela.px(x, y, (200, 196, 210))
        for lado in (-1, 1):
            for y in (chao - 3, topo_caixa + 1):
                canto = tela.poly([v2(cx + lado * larg, y - 5), v2(cx + lado * larg, y + 2),
                                   v2(cx + lado * (larg - 7), y + 2 if y > topo_caixa + 2 else y - 5)])
                tela.pintar(canto, OURO)
            tela.pintar(tela.circulo(v2(cx + lado * (larg + 1), chao - 0.28 * S), 2.2) & ~tela.circulo(v2(cx + lado * (larg + 1), chao - 0.28 * S), 1.0),
                        FERRO)                                                 # argolas
        fecho = v2(cx, topo_caixa + 2)
        tela.pintar(tela.poly([fecho + v2(-5, -6), fecho + v2(5, -6), fecho + v2(5, 4), fecho + v2(0, 8), fecho + v2(-5, 4)]), OURO)
        tela.chapado(tela.circulo(fecho + v2(0, -1), 2.0), (90 + int(60 * math.sin(f * 2)), 220, 255), emite=True)
        tela.brilho(fecho + v2(0, -1), 6, (120, 220, 255), 0.4)
        for k, (dx, dy) in enumerate(((-0.34, -0.06), (0.12, -0.12), (0.36, -0.04), (0.22, -0.2))):   # moedas
            moeda = v2(cx + dx * S, topo_caixa - 5 + dy * S)
            tela.pintar(tela.elipse(moeda[0], moeda[1], 2.6, 1.3), OURO)
        brilho = v2(cx + (P["i"] - 1.5) * 0.2 * S, topo_caixa - 11)
        for d in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            tela.px(brilho[0] + d[0], brilho[1] + d[1], (255, 250, 210), emite=True)


# ============================================================
# ESTANDE DE ARMAS (o Arsenal)
# ============================================================

class EstandeDeArmas(ObjetoDeCena):
    nome = "estande_de_armas"
    S = 48
    proporcao = (2.4, 2.3)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        madeira = Mat((110, 72, 44), 6, ruido=0.3, relevo=1.0)
        # cavalete: dois pés em A, travessa de cima com pontas entalhadas e a de baixo
        for x in (cx - 0.8 * S, cx + 0.8 * S):
            tela.pintar(tela.capsula(v2(x, chao), v2(x, chao - 1.35 * S), 0.065 * S), madeira)
            tela.pintar(tela.capsula(v2(x - 0.18 * S, chao), v2(x, chao - 0.3 * S), 0.04 * S), madeira.escuro(1))
            tela.pintar(tela.capsula(v2(x + 0.18 * S, chao), v2(x, chao - 0.3 * S), 0.04 * S), madeira.escuro(1))
        for y, r in ((chao - 1.26 * S, 0.055), (chao - 0.46 * S, 0.045)):
            tela.pintar(tela.capsula(v2(cx - 0.92 * S, y), v2(cx + 0.92 * S, y), r * S), madeira.claro(1))
            for lado in (-1, 1):
                tela.pintar(tela.circulo(v2(cx + lado * 0.94 * S, y), r * S * 1.25), OURO_ESCURO)
        balanco = math.sin(f) * 0.4
        # alabarda (a mais alta), lança, espada larga, machado e maça
        al_b, al_t = v2(cx - 0.62 * S, chao - 0.04 * S), v2(cx - 0.56 * S + balanco, chao - 1.9 * S)
        tela.pintar(tela.capsula(al_b, al_t, 0.032 * S), madeira.escuro(1))
        lam = [al_t + v2(0, 0.2 * S), al_t + v2(0.26 * S, 0.12 * S), al_t + v2(0.3 * S, 0.32 * S), al_t + v2(0, 0.38 * S)]
        tela.pintar(tela.poly(lam), ACO)
        tela.pintar(tela.poly([al_t + v2(-0.05 * S, 0.22 * S), al_t + v2(-0.16 * S, 0.3 * S), al_t + v2(-0.04 * S, 0.3 * S)]), ACO)
        tela.pintar(tela.poly([al_t + v2(-0.04 * S, 0.02 * S), al_t + v2(0.04 * S, 0.02 * S), al_t + v2(0, -0.16 * S)]), ACO)
        la_b, la_t = v2(cx - 0.36 * S, chao - 0.06 * S), v2(cx - 0.32 * S + balanco, chao - 1.7 * S)
        tela.pintar(tela.capsula(la_b, la_t, 0.028 * S), madeira.escuro(1))
        tela.pintar(tela.poly([la_t + v2(-0.06 * S, 0.13 * S), la_t + v2(0.06 * S, 0.13 * S), la_t + v2(0, -0.14 * S)]), ACO)
        tela.chapado(tela.poly([la_t + v2(-0.05 * S, 0.16 * S), la_t + v2(0.05 * S, 0.16 * S), la_t + v2(0.02 * S, 0.3 * S)]), (150, 40, 40))
        es_b, es_t = v2(cx - 0.1 * S, chao - 0.12 * S), v2(cx - 0.06 * S, chao - 1.55 * S)
        tela.pintar(tela.capsula(es_b + v2(0, -0.24 * S), es_t, 0.06 * S, 0.02 * S), ACO)
        tela.traco(es_b + v2(0, -0.28 * S), es_t + v2(0, 0.1 * S), ACO[6], sobre=True)
        tela.pintar(tela.capsula(es_b + v2(-0.15 * S, -0.24 * S), es_b + v2(0.15 * S, -0.24 * S), 0.03 * S), OURO)
        tela.pintar(tela.capsula(es_b, es_b + v2(0, -0.22 * S), 0.032 * S), COURO)
        tela.pintar(tela.circulo(es_b + v2(0, 0.02 * S), 0.045 * S), OURO)
        ma_b, ma_t = v2(cx + 0.18 * S, chao - 0.08 * S), v2(cx + 0.22 * S, chao - 1.32 * S)
        tela.pintar(tela.capsula(ma_b, ma_t, 0.035 * S), madeira.escuro(1))
        lamina = [ma_t + v2(0, 0.06 * S), ma_t + v2(0.3 * S, -0.04 * S), ma_t + v2(0.36 * S, 0.22 * S), ma_t + v2(0.3 * S, 0.44 * S),
                  ma_t + v2(0, 0.32 * S)]
        tela.pintar(tela.poly(lamina), FERRO_BATIDO)
        tela.traco(ma_t + v2(0.31 * S, -0.02 * S), ma_t + v2(0.33 * S, 0.42 * S), ACO[6], sobre=True)
        mc_b, mc_t = v2(cx + 0.44 * S, chao - 0.06 * S), v2(cx + 0.46 * S, chao - 1.0 * S)
        tela.pintar(tela.capsula(mc_b, mc_t, 0.03 * S), madeira.escuro(1))
        tela.pintar(tela.circulo(mc_t, 0.1 * S), FERRO_BATIDO)
        for k in range(6):
            a = k * math.pi / 3
            tela.pintar(tela.poly([mc_t + v2(math.cos(a - 0.3), math.sin(a - 0.3)) * 0.08 * S,
                                   mc_t + v2(math.cos(a), math.sin(a)) * 0.15 * S,
                                   mc_t + v2(math.cos(a + 0.3), math.sin(a + 0.3)) * 0.08 * S]), FERRO_BATIDO)
        # escudo redondo com emblema de crânio e escudo de pipa encostado
        centro = v2(cx + 0.7 * S, chao - 0.7 * S)
        tela.pintar(tela.circulo(centro, 0.3 * S), Mat((140, 40, 40), 6, relevo=1.0))
        tela.pintar(tela.circulo(centro, 0.3 * S) & ~tela.circulo(centro, 0.24 * S), FERRO_BATIDO)
        for k in range(8):
            a = k * math.pi / 4
            tela.px(centro[0] + math.cos(a) * 0.27 * S, centro[1] + math.sin(a) * 0.27 * S, (210, 206, 220))
        tela.pintar(tela.circulo(centro, 0.08 * S), OURO)
        pipa = [v2(cx - 0.92 * S, chao - 0.88 * S), v2(cx - 0.62 * S, chao - 0.88 * S), v2(cx - 0.6 * S, chao - 0.5 * S),
                v2(cx - 0.77 * S, chao - 0.12 * S), v2(cx - 0.94 * S, chao - 0.5 * S)]
        tela.pintar(tela.poly(pipa), Mat((50, 70, 120), 6, relevo=1.0))
        tela.tracos(pipa + [pipa[0]], (200, 170, 90), sobre=True)
        tela.traco(v2(cx - 0.77 * S, chao - 0.84 * S), v2(cx - 0.77 * S, chao - 0.2 * S), (220, 200, 140), sobre=True)
        tela.traco(v2(cx - 0.9 * S, chao - 0.62 * S), v2(cx - 0.64 * S, chao - 0.62 * S), (220, 200, 140), sobre=True)
        # elmo pousado no pé da direita e flâmula pendurada na travessa
        elmo = v2(cx + 0.8 * S, chao - 1.42 * S)
        tela.pintar(tela.elipse(elmo[0], elmo[1], 0.13 * S, 0.12 * S), ACO)
        tela.chapado(tela.poly([elmo + v2(-0.1 * S, 0), elmo + v2(0.1 * S, 0), elmo + v2(0.1 * S, 0.02 * S), elmo + v2(-0.1 * S, 0.02 * S)]),
                     (20, 16, 24))
        tela.pintar(tela.corrente([elmo + v2(0, -0.12 * S), elmo + v2(-0.08 * S, -0.22 * S), elmo + v2(-0.2 * S, -0.2 * S + math.sin(f) * 1.5)],
                                  [1.6, 1.8, 1.0]), Mat((170, 40, 40), 5))
        pano = tela.poly([v2(cx - 0.2 * S, chao - 1.22 * S), v2(cx + 0.06 * S, chao - 1.22 * S),
                          v2(cx + 0.06 * S + math.sin(f) * 1.2, chao - 0.86 * S), v2(cx - 0.07 * S + math.sin(f) * 1.2, chao - 0.94 * S),
                          v2(cx - 0.2 * S + math.sin(f) * 1.2, chao - 0.86 * S)])
        tela.pintar(pano, Mat((40, 40, 74), 5, relevo=0.7))
        tela.pintar(tela.circulo(v2(cx - 0.07 * S + math.sin(f) * 0.6, chao - 1.06 * S), 2.4), OURO)
        t = (P["i"] % 4) / 4                                          # brilho correndo pela espada
        brilho = es_t + (es_b - es_t) * t
        tela.px(brilho[0], brilho[1], (255, 255, 230), emite=True)
        tela.brilho(brilho, 0.16 * S, (255, 240, 200), 0.35)


# ============================================================
# TENDA GRANDE
# ============================================================

class TendaGrande(ObjetoDeCena):
    """Tenda de lona em gomos costurados, com remendos, cordas, estacas, flâmula e a entrada acesa por dentro."""
    nome = "tenda_grande"
    S = 70
    proporcao = (2.1, 1.6)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.lona = kw.get("lona", Mat((96, 50, 80), 6, relevo=0.9, ruido=0.15))

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        topo = v2(cx, chao - 1.3 * S)
        esq, dir_ = v2(cx - 0.9 * S, chao), v2(cx + 0.9 * S, chao)
        # tapete na porta
        tela.chapado(tela.elipse(cx - 0.04 * S, chao + 1, 0.42 * S, 0.06 * S), (110, 40, 40))
        tela.chapado(tela.elipse(cx - 0.04 * S, chao + 1, 0.34 * S, 0.035 * S), (170, 120, 60))
        # corpo com laterais levemente côncavas (a lona cede entre o mastro e as estacas)
        lado_e = [lerp(topo, esq, t) + v2(0.05 * S * math.sin(t * math.pi), 0) for t in (0, 0.25, 0.5, 0.75, 1)]
        lado_d = [lerp(topo, dir_, t) - v2(0.05 * S * math.sin(t * math.pi), 0) for t in (0, 0.25, 0.5, 0.75, 1)]
        corpo = tela.poly(lado_e + list(reversed(lado_d)))
        tela.pintar(corpo, self.lona)
        tela.pintar(corpo & tela.poly([topo, dir_, v2(cx + 0.3 * S, chao)]), self.lona.escuro(1))
        for k in (-0.6, -0.32, 0.12, 0.42, 0.68):                     # costuras dos gomos
            tela.traco(topo + v2(0, 4), v2(cx + k * S, chao), self.lona[1], sobre=True)
        for x, y, w, h in ((cx - 0.55 * S, chao - 0.38 * S, 9, 7), (cx + 0.46 * S, chao - 0.5 * S, 7, 8)):   # remendos
            remendo = tela.poly([v2(x, y), v2(x + w, y), v2(x + w, y + h), v2(x, y + h)]) & corpo
            tela.pintar(remendo, self.lona.claro(1))
            for k in range(0, w, 2):
                tela.px(x + k, y, self.lona[0])
                tela.px(x + k, y + h, self.lona[0])
        # entrada aberta: interior aceso, um saco de dormir e a aba amarrada
        entrada = tela.poly([v2(cx - 0.24 * S, chao), v2(cx - 0.02 * S, chao - 0.66 * S), v2(cx + 0.18 * S, chao)])
        tela.chapado(entrada, (54, 28, 20))
        tela.chapado(entrada & tela.elipse(cx - 0.03 * S, chao - 0.08 * S, 0.16 * S, 0.34 * S), (204, 116, 50), emite=True)
        tela.chapado(entrada & tela.elipse(cx - 0.03 * S, chao - 0.04 * S, 0.08 * S, 0.18 * S), (250, 180, 90), emite=True)
        tela.chapado(entrada & tela.elipse(cx - 0.12 * S, chao - 0.04 * S, 0.1 * S, 0.04 * S), (80, 50, 40))
        tela.brilho(v2(cx - 0.03 * S, chao - 0.2 * S), 0.4 * S, (255, 150, 60), 0.4 + 0.06 * math.sin(f * 3))
        aba = tela.poly([v2(cx - 0.02 * S, chao - 0.66 * S), v2(cx + 0.18 * S, chao), v2(cx + 0.34 * S, chao - 0.12 * S),
                         v2(cx + 0.22 * S, chao - 0.4 * S)])
        tela.pintar(aba, self.lona.claro(1))
        tela.traco(v2(cx + 0.2 * S, chao - 0.36 * S), v2(cx + 0.3 * S, chao - 0.3 * S), (180, 150, 100))
        # mastro, flâmula, cordas e estacas
        tela.pintar(tela.capsula(topo, topo + v2(0, -0.26 * S), 1.7), MADEIRA)
        tela.pintar(tela.circulo(topo + v2(0, -0.27 * S), 1.8), OURO)
        flamula(tela, topo + v2(0, -0.25 * S), 0.26 * S, 0.1 * S, f, (170, 40, 40))
        for lado in (-1, 1):
            estaca = v2(cx + lado * 1.12 * S, chao - 1)
            for alt in (0.25, 0.6):
                tela.traco(lerp(topo, v2(cx + lado * 0.9 * S, chao), alt), estaca, (150, 130, 100))
            tela.pintar(tela.capsula(estaca, estaca + v2(lado * -1, -6), 1.3), MADEIRA)


# ============================================================
# BARRIL, CAIXOTES, LENHA, CALDEIRÃO
# ============================================================

class Barril(ObjetoDeCena):
    nome = "barril"
    S = 30
    proporcao = (1.4, 1.65)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        tela.chapado(tela.elipse(cx, chao, 0.5 * S, 0.08 * S), (16, 14, 18))
        corpo = tela.elipse(cx, chao - 0.6 * S, 0.46 * S, 0.62 * S)
        tela.pintar(corpo, MADEIRA_CLARA)
        for dx in (-0.3, -0.15, 0.0, 0.15, 0.3):
            tela.traco(v2(cx + dx * S, chao - 1.12 * S), v2(cx + dx * S * 1.1, chao - 0.08 * S), MADEIRA_CLARA[1], sobre=True)
        for dy in (-1.0, -0.72, -0.48, -0.2):
            tela.pintar(tela.capsula(v2(cx - 0.45 * S, chao + dy * S), v2(cx + 0.45 * S, chao + dy * S), 1.0) & corpo, FERRO_BATIDO)
        tela.pintar(tela.elipse(cx, chao - 1.16 * S, 0.36 * S, 0.1 * S), MADEIRA_ESCURA)
        tela.chapado(tela.circulo(v2(cx + 0.1 * S, chao - 1.16 * S), 1.2), (30, 20, 16))


class Caixotes(ObjetoDeCena):
    nome = "caixotes"
    S = 34
    proporcao = (1.9, 1.8)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        tela.chapado(tela.elipse(cx, chao, 0.85 * S, 0.08 * S), (16, 14, 18))
        for x, y, tam in ((cx - 0.38 * S, chao, 0.7), (cx + 0.36 * S, chao, 0.62), (cx - 0.02 * S, chao - 0.7 * S, 0.58)):
            meio = tam * S / 2
            caixa = tela.poly([v2(x - meio, y), v2(x + meio, y), v2(x + meio, y - tam * S), v2(x - meio, y - tam * S)])
            tela.pintar(caixa, MADEIRA_CLARA)
            for k in (1, 2):
                tela.traco(v2(x - meio, y - tam * S * k / 3), v2(x + meio, y - tam * S * k / 3), MADEIRA_CLARA[1], sobre=True)
            moldura = caixa & ~tela.poly([v2(x - meio + 2, y - 2), v2(x + meio - 2, y - 2), v2(x + meio - 2, y - tam * S + 2),
                                          v2(x - meio + 2, y - tam * S + 2)])
            tela.pintar(moldura, MADEIRA_CLARA.escuro(1))
            tela.traco(v2(x - meio + 2, y - 2), v2(x + meio - 2, y - tam * S + 2), MADEIRA_CLARA[2], sobre=True)
            for px_, py_ in ((x - meio + 1, y - 1), (x + meio - 1, y - 1), (x - meio + 1, y - tam * S + 1), (x + meio - 1, y - tam * S + 1)):
                tela.px(px_, py_, (190, 190, 200))
        tela.pintar(tela.elipse(cx + 0.36 * S, chao - 0.66 * S, 0.14 * S, 0.06 * S), Mat((200, 160, 90), 5))   # saco de grãos
        tela.pintar(tela.circulo(v2(cx + 0.36 * S, chao - 0.76 * S), 0.12 * S), Mat((200, 170, 110), 5, relevo=0.8))


class Lenha(ObjetoDeCena):
    """Toras empilhadas (cernes à mostra) com um machado cravado num toco."""
    nome = "lenha"
    S = 34
    proporcao = (2.0, 1.6)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        tela.chapado(tela.elipse(cx, chao, 0.9 * S, 0.08 * S), (16, 14, 18))
        for fila, quantas in enumerate((4, 3, 2)):
            for k in range(quantas):
                c = v2(cx - 0.14 * S + (k - (quantas - 1) / 2) * 0.32 * S, chao - 0.15 * S - fila * 0.27 * S)
                tela.pintar(tela.circulo(c, 0.15 * S), CASCA)
                tela.pintar(tela.circulo(c, 0.11 * S), CERNE)
                tela.chapado(tela.circulo(c, 0.06 * S) & ~tela.circulo(c, 0.04 * S), CERNE[1])
                tela.px(c[0], c[1], CERNE[0])
        toco = v2(cx + 0.66 * S, chao)
        tela.pintar(tela.poly([toco + v2(-0.2 * S, 0), toco + v2(0.2 * S, 0), toco + v2(0.18 * S, -0.3 * S), toco + v2(-0.18 * S, -0.3 * S)]), CASCA)
        tela.pintar(tela.elipse(toco[0], toco[1] - 0.3 * S, 0.18 * S, 0.06 * S), CERNE)
        cabo = toco + v2(0.02 * S, -0.34 * S)
        tela.pintar(tela.capsula(cabo, cabo + v2(-0.3 * S, -0.42 * S), 1.4), MADEIRA_CLARA)
        tela.pintar(tela.poly([cabo + v2(-3, 1), cabo + v2(4, -3), cabo + v2(5, 3), cabo + v2(0, 5)]), metal((150, 150, 160)))


class Caldeirao(ObjetoDeCena):
    """Caldeirão borbulhando num tripé de galhos amarrados (a sopa da taverna)."""
    nome = "caldeirao"
    S = 34
    proporcao = (1.7, 2.0)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        for lado in (-1, 0, 1):
            tela.pintar(tela.capsula(v2(cx + lado * 0.52 * S, chao), v2(cx, chao - 1.12 * S), 1.0), CASCA)
        tela.traco(v2(cx - 3, chao - 1.0 * S), v2(cx + 3, chao - 1.02 * S), (160, 140, 100))
        tela.traco(v2(cx, chao - 1.05 * S), v2(cx, chao - 0.72 * S), FERRO[2])
        corpo = v2(cx, chao - 0.42 * S)
        tela.pintar(tela.elipse(corpo[0], corpo[1], 0.44 * S, 0.32 * S), FERRO_BATIDO)
        tela.pintar(tela.elipse(corpo[0], corpo[1] - 0.26 * S, 0.42 * S, 0.08 * S), FERRO.claro(1))
        tela.chapado(tela.elipse(corpo[0], corpo[1] - 0.26 * S, 0.35 * S, 0.06 * S), (110, 150, 70), emite=True)
        tela.chapado(tela.circulo(v2(corpo[0] - 2, corpo[1] - 0.27 * S), 1.2), (170, 210, 120), emite=True)
        for k in range(4):
            t = (P["i"] / 4 + k / 4) % 1
            p = corpo + v2((k - 1.5) * 0.12 * S + math.sin(t * 5) * 1.5, -0.32 * S - t * 0.6 * S)
            tela.px(p[0], p[1], (190, 210, 170) if t < 0.5 else (140, 150, 140), emite=True)
        for lado in (-1, 1):
            tela.pintar(tela.capsula(v2(cx + lado * 0.2 * S, chao - 0.12 * S), v2(cx + lado * 0.28 * S, chao), 1.3), FERRO_BATIDO)
        fx.chama(tela, v2(cx, chao - 1), 7 + math.sin(P["fase"] * 2), 0.32 * S, fx.FOGO, fase=P["fase"] * 2, brilho=False)
        tela.brilho(v2(cx, chao - 4), 0.5 * S, (255, 150, 60), 0.4)


# ============================================================
# NOVOS: ATRIL, CARROÇA, ESTANDARTE, CÍRCULO DE RUNAS, TAPETE
# ============================================================

class AtrilDoGrimorio(ObjetoDeCena):
    """Atril entalhado com o grimório aberto (runas acesas nas páginas) e um candelabro de três velas."""
    nome = "atril_do_grimorio"
    S = 44
    proporcao = (1.7, 2.2)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        madeira = Mat((92, 56, 40), 6, ruido=0.3, relevo=1.0)
        for lado in (-1, 1):                                          # pés em garra
            tela.pintar(tela.capsula(v2(cx, chao - 0.2 * S), v2(cx + lado * 0.32 * S, chao - 1), 1.8, 1.4), madeira)
            tela.pintar(tela.circulo(v2(cx + lado * 0.33 * S, chao - 1.5), 1.8), OURO_ESCURO)
        tela.pintar(tela.capsula(v2(cx, chao - 0.15 * S), v2(cx, chao - 1.02 * S), 2.6, 2.0), madeira)
        for y in (chao - 0.45 * S, chao - 0.8 * S):
            tela.pintar(tela.elipse(cx, y, 3.6, 1.6), madeira.claro(1))
        mesa = [v2(cx - 0.48 * S, chao - 1.0 * S), v2(cx + 0.48 * S, chao - 1.14 * S), v2(cx + 0.5 * S, chao - 1.06 * S),
                v2(cx - 0.46 * S, chao - 0.9 * S)]
        tela.pintar(tela.poly(mesa), madeira.claro(1))
        # livro aberto: capa vermelha, páginas curvas e runas que brilham
        capa = tela.poly([v2(cx - 0.44 * S, chao - 1.04 * S), v2(cx + 0.44 * S, chao - 1.18 * S), v2(cx + 0.42 * S, chao - 1.24 * S),
                          v2(cx - 0.46 * S, chao - 1.1 * S)])
        tela.pintar(capa, Mat((120, 30, 40), 5))
        lombada = v2(cx, chao - 1.15 * S)
        for lado in (-1, 1):
            canto_baixo = lombada + v2(lado * 0.42 * S, -lado * 0.07 * S + 0.02 * S)
            canto_cima = lombada + v2(lado * 0.4 * S, -lado * 0.07 * S - 0.2 * S)
            pagina = tela.poly([lombada + v2(0, 1), canto_baixo, canto_cima, lombada + v2(lado * 0.2 * S, -0.26 * S),
                                lombada + v2(0, -0.2 * S)])
            tela.pintar(pagina, Mat((228, 212, 172), 5, relevo=0.4), plano=True)
            tela.traco(lombada + v2(lado * 2, -0.2 * S), canto_cima, (190, 170, 130), sobre=True)
            for k in range(4):                                          # linhas de texto
                y = -0.16 * S + k * 0.04 * S
                tela.traco(lombada + v2(lado * 3, y), lombada + v2(lado * 0.34 * S, y - lado * 0.06 * S), (120, 100, 90), sobre=True)
            p = lombada + v2(lado * 0.2 * S, -0.12 * S - lado * 0.03 * S)
            fx.runa(tela, p, (150, 120, 255) if P["i"] % 2 else (220, 190, 255), 2, forma=1 + (lado > 0) * 2)
        tela.traco(lombada + v2(0, 1), lombada + v2(0, -0.2 * S), (150, 120, 90))
        tela.brilho(v2(cx, chao - 1.25 * S), 0.45 * S, (160, 110, 255), 0.45 + 0.1 * math.sin(f * 2))
        tela.traco(v2(cx + 2, chao - 1.14 * S), v2(cx + 4, chao - 0.86 * S), (180, 40, 40))            # fita marcadora
        # candelabro de três braços
        base = v2(cx + 0.62 * S, chao)
        tela.pintar(tela.elipse(base[0], base[1] - 1, 4, 1.6), OURO)
        tela.pintar(tela.capsula(base, base + v2(0, -0.95 * S), 1.0), OURO)
        for dx, dy in ((-5, -0.95), (0, -1.1), (5, -0.95)):
            topo = base + v2(dx, dy * S)
            tela.pintar(tela.capsula(base + v2(0, -0.85 * S), topo, 0.7), OURO)
            tela.pintar(tela.capsula(topo, topo + v2(0, -5), 1.2), Mat((236, 226, 196), 4))
            fx.chama(tela, topo + v2(0, -6), 4.5 + math.sin(f * 2 + dx), 2.4, fase=f * 2 + dx, brilho=False)
        tela.brilho(base + v2(0, -1.15 * S), 14, (255, 190, 100), 0.6)


class Carroca(ObjetoDeCena):
    """Carroça de viagem com cobertura de lona em arcos, rodas raiadas, barris, sacos e uma lanterna."""
    nome = "carroca"
    S = 56
    proporcao = (2.9, 1.9)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        madeira = Mat((104, 68, 42), 6, ruido=0.35, relevo=1.0)
        tela.chapado(tela.elipse(cx, chao, 1.3 * S, 0.1 * S), (16, 14, 18))
        caixa_y = chao - 0.42 * S
        # timão apoiado no chão (frente para a direita)
        tela.pintar(tela.capsula(v2(cx + 0.9 * S, caixa_y + 4), v2(cx + 1.42 * S, chao - 2), 1.6), madeira)
        tela.pintar(tela.capsula(v2(cx + 1.3 * S, chao - 4), v2(cx + 1.42 * S, chao - 2), 2.2), madeira.escuro(1))
        # caixa da carroça
        caixa = tela.poly([v2(cx - 1.0 * S, caixa_y), v2(cx + 0.95 * S, caixa_y), v2(cx + 0.95 * S, caixa_y - 0.3 * S),
                           v2(cx - 1.0 * S, caixa_y - 0.3 * S)])
        tela.pintar(caixa, madeira)
        for k in range(1, 3):
            tela.traco(v2(cx - 1.0 * S, caixa_y - k * 0.1 * S), v2(cx + 0.95 * S, caixa_y - k * 0.1 * S), madeira[1], sobre=True)
        for x in (cx - 0.95 * S, cx - 0.3 * S, cx + 0.35 * S, cx + 0.9 * S):
            tela.pintar(tela.capsula(v2(x, caixa_y), v2(x, caixa_y - 0.3 * S), 1.0), FERRO_BATIDO)
        # cobertura de lona em arcos
        lona = Mat((206, 190, 156), 6, relevo=0.8, ruido=0.12)
        pts = [v2(cx - 0.98 * S, caixa_y - 0.3 * S)]
        for k in range(15):
            t = k / 14
            pts.append(v2(cx - 0.98 * S + t * 1.9 * S, caixa_y - 0.3 * S - math.sin(t * math.pi) ** 0.6 * 0.78 * S))
        pts.append(v2(cx + 0.92 * S, caixa_y - 0.3 * S))
        coberta = tela.poly(pts)
        tela.pintar(coberta, lona)
        for k in range(1, 5):
            x = cx - 0.98 * S + k * 1.9 * S / 5
            tela.traco(v2(x, caixa_y - 0.3 * S), v2(x, caixa_y - 0.3 * S - math.sin(k / 5 * math.pi) ** 0.6 * 0.78 * S), lona[2], sobre=True)
        boca = tela.elipse(cx + 0.88 * S, caixa_y - 0.6 * S, 0.12 * S, 0.3 * S) & coberta
        tela.chapado(boca, (40, 30, 30))
        tela.chapado(boca & tela.elipse(cx + 0.9 * S, caixa_y - 0.5 * S, 0.06 * S, 0.16 * S), (190, 110, 50), emite=True)
        for k in range(3):                                            # cordas amarrando a lona
            x = cx - 0.7 * S + k * 0.6 * S
            tela.traco(v2(x, caixa_y - 0.3 * S), v2(x + 3, caixa_y - 0.06 * S), (150, 120, 80))
        # carga na traseira: barril e sacos
        b = v2(cx - 1.12 * S, chao - 2)
        tela.pintar(tela.elipse(b[0], b[1] - 0.24 * S, 0.18 * S, 0.24 * S), MADEIRA_CLARA)
        for dy in (-0.38, -0.12):
            tela.traco(b + v2(-0.17 * S, dy * S), b + v2(0.17 * S, dy * S), FERRO[2], sobre=True)
        for dx in (-0.66, -0.42):
            tela.pintar(tela.elipse(cx + dx * S, caixa_y - 0.34 * S, 0.12 * S, 0.1 * S), Mat((190, 160, 110), 5, relevo=0.8))
        # rodas raiadas
        for x in (cx - 0.62 * S, cx + 0.58 * S):
            c = v2(x, chao - 0.3 * S)
            aro = tela.circulo(c, 0.3 * S) & ~tela.circulo(c, 0.24 * S)
            tela.pintar(aro, madeira.escuro(1))
            tela.pintar(tela.circulo(c, 0.3 * S) & ~tela.circulo(c, 0.28 * S), FERRO_BATIDO)
            for k in range(8):
                a = k * math.pi / 4 + 0.2
                tela.traco(c, c + v2(math.cos(a), math.sin(a)) * 0.25 * S, madeira[2])
            tela.pintar(tela.circulo(c, 0.06 * S), FERRO_BATIDO)
        lanterna(tela, v2(cx + 0.82 * S, caixa_y - 0.36 * S), f, 0.9)


class EstandarteDaExpedicao(ObjetoDeCena):
    """Estandarte da expedição: mastro com travessa, pano vermelho com a chama dourada e borlas."""
    nome = "estandarte_da_expedicao"
    S = 60
    proporcao = (1.2, 2.5)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        pedra(tela, v2(cx - 4, chao - 2), 6, 3, PEDRA)
        pedra(tela, v2(cx + 5, chao - 1), 5, 2.6, PEDRA_CLARA)
        topo = v2(cx, chao - 2.25 * S)
        tela.pintar(tela.capsula(v2(cx, chao - 1), topo, 2.0, 1.7), MADEIRA)
        tela.pintar(tela.poly([topo + v2(-3, 0), topo + v2(3, 0), topo + v2(0, -9)]), OURO)
        trav = topo + v2(0, 6)
        tela.pintar(tela.capsula(trav + v2(-0.32 * S, 0), trav + v2(0.32 * S, 0), 1.4), MADEIRA_ESCURA)
        for lado in (-1, 1):
            tela.pintar(tela.circulo(trav + v2(lado * 0.33 * S, 0), 2.0), OURO)
        pts = []
        for k in range(9):
            t = k / 8
            pts.append(v2(cx - 0.3 * S + t * 0.6 * S, trav[1] + 2 + math.sin(f * 0.5 + t * 6) * 0.6))
        baixo_y = trav[1] + 0.95 * S
        rabo = [v2(cx + 0.3 * S + math.sin(f) * 1.5, baixo_y), v2(cx + math.sin(f + 1) * 1.5, baixo_y - 0.16 * S),
                v2(cx - 0.3 * S + math.sin(f + 2) * 1.5, baixo_y)]
        pano = tela.poly(pts + rabo)
        tela.pintar(pano, Mat((130, 30, 36), 6, relevo=0.8, ruido=0.08))
        borda = pano & ~tela.poly([p + v2(0, 2) for p in pts] + [rabo[0] + v2(-2, -3), rabo[1] + v2(0, -3), rabo[2] + v2(2, -3)])
        tela.chapado(borda, (214, 170, 80))
        # a chama dourada da expedição
        meio = v2(cx + math.sin(f + 1) * 0.8, trav[1] + 0.42 * S)
        tela.chapado(tela.poly([meio + v2(0, -10), meio + v2(6, 2), meio + v2(3, 7), meio + v2(-3, 7), meio + v2(-6, 2)]), (226, 178, 80))
        tela.chapado(tela.poly([meio + v2(0, -3), meio + v2(3, 4), meio + v2(-3, 4)]), (130, 30, 36))
        for lado in (-1, 1):                                          # borlas
            b = trav + v2(lado * 0.33 * S, 2)
            tela.traco(b, b + v2(0, 8), (214, 170, 80))
            tela.pintar(tela.capsula(b + v2(0, 8), b + v2(0, 12), 1.6, 0.8), OURO)


class CirculoDeRunas(ObjetoDeCena):
    """Círculo mágico no chão aos pés do Mago Ancião: dois anéis e runas girando, com luz azul-violeta."""
    nome = "circulo_de_runas"
    S = 60
    proporcao = (2.4, 0.9)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        f = P["fase"]
        c = v2(cx, chao - 0.22 * S)
        rx, ry = 1.0 * S, 0.22 * S
        tela.chapado(tela.elipse(c[0], c[1], rx, ry) & ~tela.elipse(c[0], c[1], rx - 1.6, ry - 1.0), (120, 110, 230), emite=True)
        tela.chapado(tela.elipse(c[0], c[1], rx * 0.72, ry * 0.72) & ~tela.elipse(c[0], c[1], rx * 0.72 - 1.2, ry * 0.72 - 0.8),
                     (170, 150, 255), emite=True)
        for k in range(12):                                            # runas girando entre os anéis
            a = k * math.pi / 6 + f * 0.25
            p = c + v2(math.cos(a) * rx * 0.86, math.sin(a) * ry * 0.86)
            fx.runa(tela, p, (210, 200, 255) if (k + P["i"]) % 3 else (150, 130, 255), 1, forma=k)
        for k in range(6):                                             # estrela de seis pontas achatada
            a1, a2 = k * math.pi / 3 + f * 0.1, (k + 2) * math.pi / 3 + f * 0.1
            tela.traco(c + v2(math.cos(a1) * rx * 0.68, math.sin(a1) * ry * 0.68),
                       c + v2(math.cos(a2) * rx * 0.68, math.sin(a2) * ry * 0.68), (130, 110, 240), emite=True)
        for k in range(5):                                             # fagulhas subindo
            t = (P["i"] / 4 + k / 5) % 1
            p = c + v2(math.cos(k * 1.3) * rx * 0.6, -t * 0.5 * S)
            tela.px(p[0], p[1], (200, 190, 255), emite=True)
        tela.brilho(c, 0.9 * S, (130, 110, 255), 0.4)


class Tapete(ObjetoDeCena):
    """Tapete oriental gasto, estendido no chão (debaixo do Baú e do Espelho)."""
    nome = "tapete"
    S = 50
    proporcao = (2.4, 0.7)

    def desenhar(self, tela, ctx, P):
        S = self.S
        cx, chao = self.ancora
        c = v2(cx, chao - 0.2 * S)
        larg, alt = 1.05 * S, 0.17 * S
        forma = tela.poly([c + v2(-larg, alt), c + v2(larg, alt), c + v2(larg * 0.86, -alt), c + v2(-larg * 0.86, -alt)])
        tela.pintar(forma, Mat((120, 36, 40), 5, relevo=0.3, ruido=0.2), plano=True)
        miolo = tela.poly([c + v2(-larg * 0.78, alt * 0.6), c + v2(larg * 0.78, alt * 0.6), c + v2(larg * 0.68, -alt * 0.6),
                           c + v2(-larg * 0.68, -alt * 0.6)])
        tela.chapado(miolo, (60, 40, 70))
        tela.chapado(tela.poly([c + v2(0, -alt * 0.5), c + v2(larg * 0.3, 0), c + v2(0, alt * 0.5), c + v2(-larg * 0.3, 0)]), (196, 150, 70))
        tela.chapado(tela.poly([c + v2(0, -alt * 0.25), c + v2(larg * 0.14, 0), c + v2(0, alt * 0.25), c + v2(-larg * 0.14, 0)]), (120, 36, 40))
        for lado in (-1, 1):                                          # franjas
            for k in range(6):
                y = c[1] - alt + k * alt * 2 / 5
                x = c[0] + lado * (larg * (0.86 + 0.14 * (y - c[1] + alt) / (2 * alt)))
                tela.traco(v2(x, y), v2(x + lado * 2, y), (220, 200, 160))
