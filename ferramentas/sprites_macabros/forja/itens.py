"""Forja de ITENS: ícones 20x20 em pixel art, com o mesmo motor dos personagens
(materiais com volume, pontilhado, contorno escuro, luz de borda e brilhos).

    IconeForjado (base: tela 20x20, cores, raridade)
     ├── armas:       Espada, Adaga, Machado, Martelo, Clava, Cajado, Foice, Arco, Alaude, Chicote
     ├── armaduras:   Peitoral, Manto, Elmo
     ├── amuletos:    Anel, Pingente, Coroa, Estandarte
     ├── consumíveis: Frasco, Pao, Tigela, Bomba, Pergaminho, Tomo, Bolsa
     └── materiais:   Osso, Presa, Olho, Erva, Cogumelo, Flor, Gota, Minerio, Escama, Novelo,
                      Alma, Cranio, Bola, Sino, Pena, Tecido, Asa, Carne, Coracao, Selo, Mola, Luva

Para um item novo: escolha uma forma (FORMAS) e cores. O gerador (gerar_itens.py) decide
sozinho pela chave do item (PALAVRAS), ou pelo campo "icone" do itens.json:
    "icone": {"forma": "espada", "cor": [150, 160, 190], "detalhe": [190, 40, 50]}
"""
import math

from .motor import Tela, Mat, metal, v2

T = 20                                   # tamanho do ícone (pixels)

CORES_RARIDADE = {"comum": None, "incomum": (110, 196, 96), "raro": (90, 150, 230), "epico": (175, 90, 220),
                  "lendario": (240, 190, 80), "amaldicoado": (200, 40, 60)}

MADEIRA = Mat((122, 82, 50), 6, relevo=0.9, ruido=0.2)
COURO = Mat((104, 66, 44), 6, relevo=0.9, ruido=0.15)
OURO = metal((196, 152, 70))
FERRO = metal((120, 118, 132))
OSSO_MAT = Mat((222, 212, 186), 6, relevo=1.0, ruido=0.12)
VIDRO = Mat((170, 196, 206), 6, relevo=1.4, especular=(250, 255, 255), dither=0.2)
PAPEL = Mat((214, 196, 150), 6, relevo=0.5, ruido=0.1)


def ao_longo(a, b, t):
    a, b = v2(a), v2(b)
    return a + (b - a) * t


def perpendicular(a, b):
    d = v2(b) - v2(a)
    n = math.hypot(d[0], d[1]) or 1
    return v2(-d[1] / n, d[0] / n)


class IconeForjado:
    """Base de todos os ícones. 'cor' = cor principal; 'detalhe' = gema/joia/líquido secundário."""

    forma = "base"
    borda_raridade = False               # True: o contorno ganha a cor da raridade (ícones de itens_fases.py)

    def __init__(self, cor=(150, 150, 160), detalhe=None, raridade="comum", semente=0, variacao=""):
        self.cor = tuple(cor)
        self.raridade = raridade
        self.detalhe = tuple(detalhe) if detalhe else (CORES_RARIDADE.get(raridade) or (180, 40, 50))
        self.semente = semente
        self.variacao = variacao          # ex.: "couro", "cota", "osso" (muda o material)

    @property
    def raro(self):
        return self.raridade in ("epico", "lendario")

    def mat(self, cor=None, **kw):
        return Mat(cor or self.cor, 6, **kw)

    def metal(self, cor=None):
        return metal(cor or self.cor)

    def gema(self, tela, c, r=1.4):
        """Pedra preciosa na cor do detalhe (brilha nos itens épicos e lendários)."""
        tela.pintar(tela.circulo(c, r), Mat(self.detalhe, 5, relevo=1.6, especular=(255, 255, 255)))
        if self.raro:
            tela.brilho(c, 4.5, self.detalhe, 0.6)

    def desenhar(self, tela):
        raise NotImplementedError

    def gerar(self):
        """Desenha e devolve a imagem (PIL RGBA 20x20)."""
        tela = Tela(T, T, semente=self.semente, forca_borda=0.22)
        cor_da_raridade = CORES_RARIDADE.get(self.raridade)
        if self.borda_raridade and cor_da_raridade:
            tela.contorno_cor = tuple(int(c * 0.75) for c in cor_da_raridade)
        self.desenhar(tela)
        if self.raridade == "lendario":
            tela.brilho(v2(10, 10), 11, self.detalhe, 0.25)
        return tela.finalizar()


# ============================================================
# ARMAS (cabo embaixo à esquerda, ponta em cima à direita)
# ============================================================

class Espada(IconeForjado):
    forma = "espada"
    comprimento = 1.0

    def desenhar(self, tela):
        base, ponta = v2(7, 13), ao_longo((7, 13), (16.5, 3.5), self.comprimento)
        tela.pintar(tela.capsula(base, ponta, 1.7, 0.5), self.metal())
        tela.traco(ao_longo(base, ponta, 0.1), ao_longo(base, ponta, 0.85), self.metal()[5], sobre=True)
        n = perpendicular(base, ponta)
        tela.pintar(tela.capsula(base + n * 3.2, base - n * 3.2, 1.0), OURO if self.raridade != "comum" else FERRO)
        tela.pintar(tela.capsula(v2(6, 14), v2(4, 16), 1.0), COURO)
        self.gema(tela, v2(3.3, 16.7), 1.3)


class Adaga(Espada):
    forma = "adaga"
    comprimento = 0.62


class Machado(IconeForjado):
    forma = "machado"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4, 17), v2(13, 5), 0.9), MADEIRA)
        lamina = tela.poly([v2(10, 3), v2(15, 1.5), v2(18, 6), v2(16.5, 10.5), v2(12, 8.5)])
        tela.pintar(lamina, self.metal())
        tela.traco(v2(15.5, 2), v2(17.6, 6.5), self.metal()[6], sobre=True)
        tela.pintar(tela.circulo(v2(12.3, 6.2), 1.2), FERRO.escuro(1))


class Martelo(IconeForjado):
    forma = "martelo"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4, 17), v2(12.5, 6.5), 0.9), MADEIRA)
        c = v2(13, 6)
        cabeca = tela.elipse_girada(c, 5.2, 2.8, -0.8)
        tela.pintar(cabeca, self.metal())
        self.gema(tela, c, 1.1)


class Clava(IconeForjado):
    forma = "clava"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4, 17), v2(13, 6), 1.0, 2.6), self.mat(relevo=1.1, ruido=0.25))
        for p in (v2(11, 5), v2(15, 6.5), v2(13.5, 9.5), v2(10, 8.5), v2(14.5, 3)):
            tela.pintar(tela.circulo(p, 0.8), FERRO.claro(1))


class Cajado(IconeForjado):
    forma = "cajado"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4.5, 18), v2(12.5, 6.5), 0.9, 0.8), MADEIRA)
        orbe = v2(14, 5)
        for ang in (-0.5, 1.3, 3.0):              # garras segurando o orbe
            p = orbe + v2(math.cos(ang), math.sin(ang)) * 3.2
            tela.pintar(tela.capsula(v2(12.5, 6.5), p, 0.6), MADEIRA.escuro(1))
        tela.pintar(tela.circulo(orbe, 2.4), Mat(self.cor, 5, relevo=1.6, especular=(255, 255, 255)))
        tela.brilho(orbe, 5, self.cor, 0.7)


class Foice(IconeForjado):
    forma = "foice"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(5, 18), v2(11, 3), 0.8), MADEIRA)
        lamina = [v2(11, 3), v2(15, 2.5), v2(18, 5), v2(18.5, 9), v2(17, 12)]
        tela.pintar(tela.corrente(lamina, [1.4, 1.8, 1.6, 1.1, 0.4]), self.metal())


class Arco(IconeForjado):
    forma = "arco"

    def desenhar(self, tela):
        arco = [v2(7, 1.5), v2(12, 4), v2(14.5, 10), v2(12, 16), v2(7, 18.5)]
        tela.pintar(tela.corrente(arco, [0.7, 1.2, 1.5, 1.2, 0.7]), self.mat(relevo=1.0))
        tela.traco(v2(7, 2), v2(7, 18), (220, 214, 196))
        tela.pintar(tela.circulo(v2(14.5, 10), 1.0), COURO)


class Alaude(IconeForjado):
    forma = "alaude"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(9, 11), v2(16.5, 2.5), 1.1), MADEIRA.escuro(1))
        tela.pintar(tela.elipse_girada(v2(7.5, 13.5), 5.4, 4.2, -0.8), self.mat(relevo=1.1))
        tela.pintar(tela.circulo(v2(7.5, 13.5), 1.4), Mat((26, 16, 14), 4))
        tela.traco(v2(5, 16), v2(16, 3), (226, 214, 180), sobre=True)


class Chicote(IconeForjado):
    forma = "chicote"

    def desenhar(self, tela):
        tela.pintar(tela.elipse(10, 9, 6, 5) & ~tela.elipse(10, 9, 3.4, 2.6), self.mat(relevo=1.2))     # chicote enrolado
        tela.pintar(tela.capsula(v2(4, 13), v2(2.5, 18), 1.2), COURO)
        for p in (v2(10, 4), v2(15.5, 9), v2(10, 14), v2(4.5, 9)):
            tela.px(p[0], p[1], (210, 210, 220))


# ============================================================
# ARMADURAS
# ============================================================

class Peitoral(IconeForjado):
    forma = "peitoral"

    def desenhar(self, tela):
        corpo = tela.poly([v2(3, 5), v2(7.5, 3.5), v2(12.5, 3.5), v2(17, 5), v2(16, 10), v2(15, 17), v2(10, 18.5),
                           v2(5, 17), v2(4, 10)])
        gola = tela.elipse(10, 3.5, 2.6, 1.6)
        tela.alfa[gola] = 0
        corpo &= ~gola
        if self.variacao in ("couro", "seda", "pano"):
            tela.pintar(corpo, self.mat(relevo=0.8, ruido=0.2))
        elif self.variacao == "osso":
            tela.pintar(corpo, OSSO_MAT)
            for y in (8, 11, 14):
                tela.traco(v2(6, y), v2(14, y), OSSO_MAT[1], sobre=True)
        else:
            tela.pintar(corpo, self.metal())
            if self.variacao == "cota":
                for y in range(6, 17, 2):                 # anéis da cota de malha
                    for x in range(5 + (y // 2) % 2, 16, 2):
                        if tela.alfa[y, x]:
                            tela.px(x, y, self.metal()[1])
        tela.traco(v2(10, 5.5), v2(10, 17), self.metal()[1] if not self.variacao else self.mat()[1], sobre=True)
        tela.pintar(tela.poly([v2(5, 13), v2(15, 13), v2(15, 14.5), v2(5, 14.5)]) & corpo, COURO.escuro(1))
        self.gema(tela, v2(10, 13.8), 1.0)


class Manto(IconeForjado):
    forma = "manto"

    def desenhar(self, tela):
        capa = tela.poly([v2(7, 2.5), v2(13, 2.5), v2(15, 7), v2(17.5, 18), v2(2.5, 18), v2(5, 7)])
        tela.pintar(capa, self.mat(desce=0.35, relevo=0.8))
        capuz = tela.elipse(10, 5, 3.4, 3)
        tela.chapado(capuz & tela.elipse(10, 5.8, 2.2, 2.2), (14, 8, 16))
        for x in (6.5, 10, 13.5):
            tela.traco(v2(x, 9), v2(x + (x - 10) * 0.3, 17), self.mat()[1], sobre=True)
        self.gema(tela, v2(10, 8.3), 1.0)


class Elmo(IconeForjado):
    forma = "elmo"

    def desenhar(self, tela):
        domo = tela.elipse(10, 10, 6.5, 7.5) & tela.poly([v2(0, 0), v2(20, 0), v2(20, 16), v2(0, 16)])
        tela.pintar(domo, self.metal())
        tela.chapado(tela.poly([v2(5, 9), v2(15, 9), v2(15, 10.5), v2(5, 10.5)]), (14, 8, 16))
        for lado in (-1, 1):                       # chifres
            tela.pintar(tela.corrente([v2(10 + lado * 5.5, 6), v2(10 + lado * 8, 3), v2(10 + lado * 8.5, 0.8)],
                                      [1.4, 1.0, 0.4]), OSSO_MAT)


class ElmoSimples(IconeForjado):
    """Elmo fechado com fenda e crista (sem chifres)."""
    forma = "elmo_simples"

    def desenhar(self, tela):
        domo = tela.elipse(10, 10.5, 6.5, 7.5) & tela.poly([v2(0, 0), v2(20, 0), v2(20, 17), v2(0, 17)])
        tela.pintar(domo, self.metal())
        tela.chapado(tela.poly([v2(5.5, 9.5), v2(14.5, 9.5), v2(14.5, 11), v2(5.5, 11)]), (14, 8, 16))
        tela.traco(v2(10, 3.5), v2(10, 9), self.metal()[5], sobre=True)
        tela.pintar(tela.capsula(v2(10, 3), v2(10, 1.2), 1.0), self.metal(self.detalhe))


class Capuz(IconeForjado):
    """Capuz de pano com a abertura escura do rosto."""
    forma = "capuz"

    def desenhar(self, tela):
        capuz = tela.poly([v2(10, 1.5), v2(15.5, 6), v2(17, 17.5), v2(3, 17.5), v2(4.5, 6)])
        tela.pintar(capuz, self.mat(relevo=0.9, ruido=0.15))
        tela.chapado(tela.elipse(10, 11, 3.6, 4.2), (14, 8, 16))
        tela.traco(v2(10, 2.5), v2(10, 6.5), self.mat()[1], sobre=True)
        self.gema(tela, v2(10, 16.2), 1.0)


class Calcas(IconeForjado):
    forma = "calcas"

    def desenhar(self, tela):
        cintura = tela.poly([v2(4.5, 2.5), v2(15.5, 2.5), v2(15.5, 5), v2(4.5, 5)])
        perna_e = tela.poly([v2(4.5, 4.5), v2(10, 4.5), v2(9, 18), v2(4.5, 18)])
        perna_d = tela.poly([v2(10, 4.5), v2(15.5, 4.5), v2(15.5, 18), v2(11, 18)])
        material = self.metal() if self.variacao == "metal" else self.mat(relevo=0.9, ruido=0.2)
        tela.pintar(perna_e | perna_d, material)
        tela.pintar(cintura, COURO.escuro(1))
        tela.traco(v2(10, 5), v2(10.2, 18), (20, 12, 16), sobre=True)
        for y in (10.5,):                            # joelheiras / remendos
            tela.traco(v2(5, y), v2(8.8, y), material[1], sobre=True)
            tela.traco(v2(11.3, y), v2(15, y), material[1], sobre=True)
        self.gema(tela, v2(10, 3.7), 0.9)


class Botas(IconeForjado):
    forma = "botas"

    def desenhar(self, tela):
        for dx in (-2.5, 3.5):                      # bota de trás e da frente
            cano = tela.poly([v2(5 + dx, 3), v2(10 + dx, 3), v2(10 + dx, 13), v2(14.5 + dx, 14.5), v2(14.5 + dx, 17.5),
                              v2(5 + dx, 17.5)])
            tela.pintar(cano, self.mat(relevo=0.9, ruido=0.15) if dx > 0 else self.mat(relevo=0.9).escuro(1))
            tela.traco(v2(5 + dx, 6), v2(10 + dx, 6), COURO[1], sobre=True)
            tela.chapado(tela.poly([v2(5 + dx, 16.5), v2(14.5 + dx, 16.5), v2(14.5 + dx, 17.6), v2(5 + dx, 17.6)]),
                         (24, 16, 18))
        self.gema(tela, v2(10.5, 6), 0.9)


class Escudo(IconeForjado):
    forma = "escudo"

    def desenhar(self, tela):
        corpo = tela.poly([v2(3, 3), v2(17, 3), v2(17, 9), v2(10, 18.5), v2(3, 9)])
        if self.variacao == "metal":
            tela.pintar(corpo, self.metal())
        else:
            tela.pintar(corpo, self.mat(relevo=0.9, ruido=0.25))
            for x in (6.5, 10, 13.5):               # tábuas
                tela.traco(v2(x, 3.5), v2(x, 14), self.mat()[1], sobre=True)
        tela.traco(v2(3.5, 7), v2(16.5, 7), FERRO[2], sobre=True)
        tela.pintar(tela.circulo(v2(10, 8.5), 1.8), FERRO)
        self.gema(tela, v2(10, 8.5), 0.9)


class Lanterna(IconeForjado):
    forma = "lanterna"

    def desenhar(self, tela):
        tela.traco(v2(10, 1.5), v2(10, 4), FERRO[1])
        tela.pintar(tela.poly([v2(6, 4), v2(14, 4), v2(15, 6), v2(5, 6)]), self.metal())
        tela.chapado(tela.poly([v2(6.5, 6), v2(13.5, 6), v2(13.5, 15), v2(6.5, 15)]), (255, 206, 110), emite=True)
        for x in (6.5, 10, 13.5):
            tela.traco(v2(x, 6), v2(x, 15), self.metal()[1], sobre=True)
        tela.pintar(tela.poly([v2(5, 15), v2(15, 15), v2(14, 17.5), v2(6, 17.5)]), self.metal())
        tela.brilho(v2(10, 10.5), 6, (255, 180, 90), 0.6)


class Vela(IconeForjado):
    forma = "vela"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(7, 8), v2(13, 8), v2(13, 17), v2(7, 17)]), self.mat(relevo=0.7))
        tela.pintar(tela.poly([v2(5, 17), v2(15, 17), v2(15, 19), v2(5, 19)]), self.metal((150, 120, 70)))
        tela.traco(v2(10, 8), v2(10, 6), (40, 30, 30))
        tela.chapado(tela.poly([v2(8.5, 6), v2(10, 1.5), v2(11.5, 6)]), (255, 200, 90), emite=True)
        tela.chapado(tela.poly([v2(9.4, 6), v2(10, 3.5), v2(10.6, 6)]), (255, 250, 220), emite=True)
        tela.brilho(v2(10, 4.5), 5, (255, 200, 110), 0.6)


# ============================================================
# AMULETOS E ACESSÓRIOS
# ============================================================

class Anel(IconeForjado):
    forma = "anel"

    def desenhar(self, tela):
        aro = tela.elipse(10, 12, 6, 5.2) & ~tela.elipse(10, 12, 3.8, 3.2)
        tela.pintar(aro, self.metal())
        tela.pintar(tela.elipse(10, 6.5, 2.6, 2.2), OURO)
        self.gema(tela, v2(10, 6.3), 1.8)


class Pingente(IconeForjado):
    forma = "pingente"

    def desenhar(self, tela):
        for lado in (-1, 1):
            tela.traco(v2(10 + lado * 6, 1), v2(10 + lado * 1.5, 8), (200, 190, 150))
        corpo = tela.elipse(10, 12.5, 4.3, 5.2)
        tela.pintar(corpo, self.mat(relevo=1.3))
        self.gema(tela, v2(10, 12.5), 2.0)


class Coroa(IconeForjado):
    forma = "coroa"

    def desenhar(self, tela):
        coroa = tela.poly([v2(3, 16), v2(3, 7), v2(6, 11), v2(10, 4), v2(14, 11), v2(17, 7), v2(17, 16)])
        tela.pintar(coroa, self.metal())
        tela.traco(v2(3.5, 14), v2(16.5, 14), self.metal()[1], sobre=True)
        for x in (6, 10, 14):
            self.gema(tela, v2(x, 14.8 if x != 10 else 12), 1.0)


class Estandarte(IconeForjado):
    forma = "estandarte"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4, 19), v2(4, 1.5), 0.8), MADEIRA)
        bandeira = tela.poly([v2(5, 2.5), v2(17, 2.5), v2(17, 13), v2(11, 10.5), v2(5, 13)])
        tela.pintar(bandeira, self.mat(relevo=0.6))
        self.gema(tela, v2(11, 6.5), 1.6)


# ============================================================
# CONSUMÍVEIS
# ============================================================

class Frasco(IconeForjado):
    """Poção: vidro, líquido na cor do item e rolha. variacao "alto" = garrafa comprida."""
    forma = "frasco"

    def desenhar(self, tela):
        alto = self.variacao == "alto"
        tela.pintar(tela.capsula(v2(10, 2.5), v2(10, 7), 1.6), VIDRO)
        corpo = tela.elipse(10, 12.5, 4.2, 6) if alto else tela.circulo(v2(10, 12.6), 5.6)
        tela.pintar(corpo, VIDRO)
        interior = tela.elipse(10, 12.7, 3.0, 4.8) if alto else tela.circulo(v2(10, 12.8), 4.4)
        nivel = 10.5 if alto else 10
        liquido = interior & tela.poly([v2(0, nivel), v2(20, nivel), v2(20, 20), v2(0, 20)])
        tela.pintar(liquido, Mat(self.cor, 6, relevo=1.2, nivel=0.1))
        tela.pintar(tela.poly([v2(8.6, 1), v2(11.4, 1), v2(11.4, 3), v2(8.6, 3)]), Mat((130, 90, 56), 4))
        tela.px(7.5, 9.5, (250, 255, 255))
        tela.px(7, 10.5, (230, 240, 245))
        if self.raro:
            tela.brilho(v2(10, 13), 6, self.cor, 0.5)


class Pao(IconeForjado):
    forma = "pao"

    def desenhar(self, tela):
        tela.pintar(tela.elipse(10, 12, 7.5, 4.8), self.mat(relevo=1.2, ruido=0.2))
        for x in (6.5, 10, 13.5):
            tela.traco(v2(x - 1, 9.5), v2(x + 1, 11.5), self.mat()[1], sobre=True)


class Queijo(IconeForjado):
    """Fatia de queijo em cunha, com buracos; 'detalhe' = cor das manchas de mofo."""
    forma = "queijo"

    def desenhar(self, tela):
        lado = tela.poly([v2(3, 15.5), v2(17, 15.5), v2(17, 7.5), v2(3, 12)])
        topo = tela.poly([v2(3, 12), v2(17, 7.5), v2(15.5, 5.5), v2(2.5, 10.5)])
        massa = self.mat(relevo=0.8, ruido=0.15)
        tela.pintar(lado, massa)
        tela.pintar(topo, massa.claro(1), plano=True)
        for c, r in ((v2(7, 13.6), 1.2), (v2(12, 12.2), 1.4), (v2(15.2, 14), 0.9), (v2(10, 9.2), 0.8)):   # buracos
            tela.chapado(tela.circulo(c, r) & (lado | topo), massa[1])
        for x, y in ((5, 11), (6, 14.5), (13.5, 7.5), (16, 10.5), (9, 15)):                             # mofo
            tela.px(x, y, self.detalhe)
            tela.px(x + 1, y, tuple(int(c * 0.7) for c in self.detalhe))


class Rato(IconeForjado):
    """Um ratinho sentado, de lado, com rabo enrolado; 'cor' = o pelo, 'detalhe' = os olhos (Rato de Estimação)."""
    forma = "rato"

    def desenhar(self, tela):
        pelo = self.mat(relevo=1.1, ruido=0.3)
        tela.tracos([v2(5, 15), v2(2.5, 13), v2(3, 10), v2(5.5, 10.5)], (200, 140, 140))               # o rabo
        corpo = tela.elipse(9.5, 13, 5.2, 3.8)
        cabeca = tela.poly([v2(12, 9), v2(17.5, 11.5), v2(16, 13.5), v2(12, 13.5)])
        tela.pintar(corpo | cabeca, pelo)
        tela.pintar(tela.circulo(v2(12.6, 8.2), 1.8), pelo.claro(1))                                  # a orelha
        tela.px(12.6, 8.2, (210, 140, 150))
        tela.px(15, 11, self.detalhe, emite=True)                                                     # o olho
        tela.px(17.6, 12, (230, 150, 160))                                                            # o focinho
        for x in (7, 11):                                                                             # as patinhas
            tela.px(x, 16.4, (210, 150, 150))


class Flauta(IconeForjado):
    """Flauta reta de osso na diagonal, com os furos e uma fita; 'detalhe' = cor da fita."""
    forma = "flauta"

    def desenhar(self, tela):
        a, b = v2(4, 16.5), v2(16.5, 3.5)
        tela.pintar(tela.capsula(a, b, 1.5, 1.2), self.mat(relevo=1.1, ruido=0.12))
        tela.pintar(tela.capsula(b, b + v2(1.6, -1.6), 1.0), self.mat(relevo=1.0).escuro(1))     # bocal
        for t in (0.3, 0.42, 0.54, 0.66, 0.78):                                                  # os furos
            p = a + (b - a) * t
            tela.px(p[0], p[1], self.mat()[0])
        fita = a + (b - a) * 0.15
        tela.tracos([fita, fita + v2(-1.5, 2.5), fita + v2(0.5, 4)], self.detalhe)


class Tigela(IconeForjado):
    forma = "tigela"

    def desenhar(self, tela):
        tigela = tela.elipse(10, 12, 7.5, 5.5) & tela.poly([v2(0, 11), v2(20, 11), v2(20, 20), v2(0, 20)])
        tela.pintar(tigela, MADEIRA)
        tela.pintar(tela.elipse(10, 11, 7.3, 2.2), self.mat(relevo=0.7, ruido=0.3))
        for x, y in ((7, 6), (10, 4.5), (13, 6.5)):     # fumaça
            tela.px(x, y, (190, 190, 180))
            tela.px(x + 1, y - 1.5, (150, 150, 145))


class Bomba(IconeForjado):
    forma = "bomba"

    def desenhar(self, tela):
        tela.pintar(tela.circulo(v2(9, 12), 6.2), self.mat(relevo=1.4, especular=(230, 230, 240)))
        tela.pintar(tela.poly([v2(11.5, 5), v2(14, 6.5), v2(13, 8), v2(10.5, 6.5)]), FERRO)
        tela.pintar(tela.corrente([v2(13, 6), v2(15, 4), v2(16, 2)], [0.7, 0.6, 0.5]), COURO)
        tela.chapado(tela.circulo(v2(16.5, 1.8), 1.0), (255, 210, 110), emite=True)
        tela.brilho(v2(16.5, 1.8), 3.5, (255, 160, 60), 0.9)


class Pergaminho(IconeForjado):
    forma = "pergaminho"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(4, 4), v2(16, 4), v2(16, 16), v2(4, 16)]), PAPEL)
        for y in (4, 16):
            tela.pintar(tela.capsula(v2(3, y), v2(17, y), 1.5), PAPEL.escuro(1))
        for y in (7, 9.5, 12):
            tela.traco(v2(6, y), v2(14 - (y % 3), y), (110, 80, 60), sobre=True)
        tela.pintar(tela.circulo(v2(13, 13), 1.8), Mat(self.cor, 5, relevo=1.4))     # selo de cera na cor do item


class Tomo(IconeForjado):
    forma = "tomo"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(5, 3), v2(16.5, 4), v2(16.5, 18), v2(5, 17)]), PAPEL.claro(1))
        capa = tela.poly([v2(3, 2.5), v2(14.5, 3.5), v2(14.5, 17.5), v2(3, 16.5)])
        tela.pintar(capa, self.mat(relevo=0.9, ruido=0.15))
        tela.pintar(tela.capsula(v2(3.3, 3), v2(3.3, 16.5), 1.0), Mat(self.cor, 6).escuro(1))      # lombada
        for p in (v2(4.5, 4), v2(13.5, 4.8), v2(4.5, 15.5), v2(13.5, 16.5)):
            tela.px(p[0], p[1], OURO[4])
        self.gema(tela, v2(9, 10), 2.0)


class Bolsa(IconeForjado):
    forma = "bolsa"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(5, 8), v2(15, 8), v2(17, 14), v2(15, 18), v2(5, 18), v2(3, 14)]),
                    self.mat(relevo=1.0, ruido=0.2))
        tela.pintar(tela.poly([v2(7, 4), v2(13, 4), v2(14, 8), v2(6, 8)]), self.mat(relevo=0.8).escuro(1))
        tela.traco(v2(6, 8), v2(14, 8), COURO[1])
        self.gema(tela, v2(10, 13), 1.2)


# ============================================================
# MATERIAIS
# ============================================================

class Osso(IconeForjado):
    forma = "osso"

    def desenhar(self, tela):
        m = self.mat(relevo=1.0, ruido=0.1)
        tela.pintar(tela.capsula(v2(5, 14), v2(15, 6), 1.5), m)
        for c in (v2(3.5, 14), v2(5.5, 16), v2(14.5, 4), v2(16.5, 6)):
            tela.pintar(tela.circulo(c, 2.0), m)


class Presa(IconeForjado):
    forma = "presa"

    def desenhar(self, tela):
        tela.pintar(tela.corrente([v2(6, 3), v2(11, 5), v2(14, 10), v2(14, 17)], [2.6, 2.3, 1.5, 0.3]),
                    self.mat(relevo=1.2, especular=(255, 250, 235)))
        tela.pintar(tela.elipse(6.5, 3.5, 3, 2), COURO)


class Olho(IconeForjado):
    forma = "olho"

    def desenhar(self, tela):
        tela.pintar(tela.circulo(v2(10, 10), 6.6), Mat((226, 214, 200), 6, relevo=1.4))
        tela.pintar(tela.circulo(v2(11.2, 9.2), 3.2), Mat(self.cor, 5, relevo=1.2))
        tela.chapado(tela.circulo(v2(11.5, 9), 1.3), (10, 6, 10))
        tela.px(10, 8, (255, 255, 255))
        for a, b in ((v2(4, 9), v2(6, 10)), (v2(5, 14), v2(7, 12.5)), (v2(14, 15), v2(13, 13))):
            tela.traco(a, b, (170, 40, 46), sobre=True)


class Erva(IconeForjado):
    forma = "erva"

    def desenhar(self, tela):
        tela.pintar(tela.corrente([v2(10, 18), v2(10, 11), v2(11, 5)], [0.8, 0.7, 0.5]), Mat((70, 100, 50), 5))
        folha = self.mat(relevo=1.0)
        for c, ang in ((v2(6.5, 11), 0.6), (v2(13.5, 10), -0.6), (v2(8, 6), 0.9), (v2(13, 5), -0.9)):
            tela.pintar(tela.elipse_girada(c, 3.6, 1.6, ang), folha)


class Cogumelo(IconeForjado):
    forma = "cogumelo"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(10, 17.5), v2(10, 10), 1.8, 1.4), Mat((214, 204, 180), 5))
        chapeu = tela.elipse(10, 9, 7, 5) & tela.poly([v2(0, 0), v2(20, 0), v2(20, 10.5), v2(0, 10.5)])
        tela.pintar(chapeu, self.mat(relevo=1.3, especular=(255, 255, 255)))
        for p in (v2(7, 6), v2(12, 5), v2(14, 8)):
            tela.chapado(tela.circulo(p, 0.7), (240, 250, 255), emite=True)
        tela.brilho(v2(10, 7), 7, self.cor, 0.45)


class Flor(IconeForjado):
    forma = "flor"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(10, 18), v2(10, 10), 0.6), Mat((70, 110, 60), 5))
        for k in range(5):
            ang = k * 1.2566 - 1.57
            tela.pintar(tela.elipse_girada(v2(10, 8) + v2(math.cos(ang), math.sin(ang)) * 3.2, 2.6, 1.6, ang),
                        self.mat(relevo=1.0))
        tela.pintar(tela.circulo(v2(10, 8), 1.6), Mat(self.detalhe, 4))


class Gota(IconeForjado):
    forma = "gota"

    def desenhar(self, tela):
        gota = tela.circulo(v2(10, 12.5), 5.4) | tela.poly([v2(10, 1.5), v2(14.6, 10), v2(5.4, 10)])
        tela.pintar(gota, self.mat(relevo=1.5, especular=(255, 245, 240)))
        tela.px(8, 10, (255, 230, 230))


class Minerio(IconeForjado):
    forma = "minerio"

    def desenhar(self, tela):
        pedra = tela.poly([v2(3, 12), v2(6, 7), v2(11, 6), v2(16, 8), v2(18, 13), v2(15, 17.5), v2(6, 18)])
        tela.pintar(pedra, Mat((96, 88, 100), 6, relevo=1.2, ruido=0.2))
        cristal = self.mat(relevo=1.7, especular=(255, 255, 255))
        for base, topo in ((v2(8, 10), v2(7, 2.5)), (v2(11, 9), v2(13, 1.5)), (v2(14, 11), v2(17, 5))):
            n = perpendicular(base, topo)
            tela.pintar(tela.poly([base + n * 1.7, topo, base - n * 1.7]), cristal)
        if self.raro or self.variacao == "brilha":
            tela.brilho(v2(11, 5), 6, self.cor, 0.5)


class Escama(IconeForjado):
    forma = "escama"

    def desenhar(self, tela):
        escama = tela.poly([v2(10, 2), v2(16.5, 5), v2(16, 12), v2(10, 18.5), v2(4, 12), v2(3.5, 5)])
        tela.pintar(escama, self.mat(relevo=1.3, especular=(255, 245, 225)))
        tela.traco(v2(10, 4), v2(10, 16), self.mat()[1], sobre=True)
        for y in (7, 11):
            tela.traco(v2(6, y), v2(14, y), self.mat()[2], sobre=True)


class Novelo(IconeForjado):
    forma = "novelo"

    def desenhar(self, tela):
        tela.pintar(tela.circulo(v2(10, 10.5), 6.4), self.mat(relevo=1.1))
        for k in range(-2, 3):
            tela.traco(v2(5 + k, 6 - k), v2(14 + k, 15 - k), self.mat()[1], sobre=True)
        tela.pintar(tela.corrente([v2(15, 14), v2(17, 17), v2(14.5, 19)], [0.6, 0.6, 0.5]), self.mat())


class Alma(IconeForjado):
    """Chama-fantasma com rosto (almas de chefe): sempre brilha."""
    forma = "alma"

    def desenhar(self, tela):
        chama = tela.circulo(v2(10, 12), 5.5) | tela.poly([v2(10, 1), v2(15, 9), v2(5, 9)]) | \
            tela.poly([v2(5, 10), v2(3, 3), v2(8, 8)]) | tela.poly([v2(15, 10), v2(17, 3.5), v2(12, 8)])
        tela.pintar(chama, Mat(self.cor, 6, relevo=1.2, nivel=0.15))
        for x in (8, 12):
            tela.chapado(tela.elipse(x, 11.5, 1.1, 1.6), (16, 8, 24))
        tela.chapado(tela.elipse(10, 15, 1.2, 0.8), (16, 8, 24))
        tela.brilho(v2(10, 11), 9, self.cor, 0.8)


class Cranio(IconeForjado):
    forma = "cranio"

    def desenhar(self, tela):
        tela.pintar(tela.circulo(v2(10, 8.5), 6.3) | tela.poly([v2(6.5, 12), v2(13.5, 12), v2(12.5, 17), v2(7.5, 17)]),
                    self.mat(relevo=1.1, ruido=0.12))
        for x in (7.5, 12.5):
            tela.chapado(tela.circulo(v2(x, 9.5), 1.6), (14, 8, 14))
        tela.chapado(tela.poly([v2(10, 11.5), v2(11, 13), v2(9, 13)]), (14, 8, 14))
        for x in (8.5, 10, 11.5):
            tela.px(x, 16, (40, 30, 30))
        if self.raro:
            for x in (7.5, 12.5):
                tela.chapado(tela.circulo(v2(x, 9.5), 0.7), self.detalhe, emite=True)
            tela.brilho(v2(10, 9.5), 6, self.detalhe, 0.5)


class Bola(IconeForjado):
    """Esfera simples: ovo, nariz de palhaço, balão (variacao "balao": com cordão)."""
    forma = "bola"

    def desenhar(self, tela):
        if self.variacao == "ovo":
            tela.pintar(tela.elipse(10, 11, 5, 6.5), self.mat(relevo=1.3, especular=(255, 255, 250)))
            return
        tela.pintar(tela.circulo(v2(10, 9), 6), self.mat(relevo=1.4, especular=(255, 240, 240)))
        if self.variacao == "balao":
            tela.traco(v2(10, 15), v2(9, 19), (210, 200, 180))


class Sino(IconeForjado):
    forma = "sino"

    def desenhar(self, tela):
        sino = tela.poly([v2(7, 5), v2(13, 5), v2(15, 13), v2(17, 15), v2(3, 15), v2(5, 13)]) | tela.circulo(v2(10, 5.5), 3)
        tela.pintar(sino, self.metal())
        tela.pintar(tela.circulo(v2(10, 16.5), 1.6), self.metal().escuro(1))
        tela.pintar(tela.capsula(v2(10, 1.5), v2(10, 3), 0.8), FERRO)
        if self.variacao == "rachado":
            tela.tracos([v2(8, 6), v2(9, 9), v2(8, 12)], (30, 20, 20), sobre=True)


class Pena(IconeForjado):
    forma = "pena"

    def desenhar(self, tela):
        tela.pintar(tela.elipse_girada(v2(10.5, 9), 7.5, 3.2, -0.9), self.mat(relevo=0.9, nivel=0.05))
        tela.traco(v2(4, 17), v2(15.5, 2.5), Mat(self.cor, 6)[1], sobre=False)
        if self.raro or self.variacao == "fogo":
            tela.brilho(v2(11, 8), 7, self.cor, 0.6)


class Tecido(IconeForjado):
    forma = "tecido"

    def desenhar(self, tela):
        pano = tela.poly([v2(3, 6), v2(15, 3.5), v2(17.5, 13), v2(5, 17)])
        tela.pintar(pano, self.mat(relevo=0.6, ruido=0.25))
        if self.variacao == "listras":
            for k in range(4):
                tela.traco(v2(4 + k * 3.5, 6 - k * 0.6), v2(6 + k * 3.5, 16.5 - k * 0.9), self.detalhe, sobre=True)
        else:
            tela.traco(v2(5, 10), v2(16, 8), self.mat()[1], sobre=True)
            tela.traco(v2(8, 15), v2(15, 12.5), self.mat()[1], sobre=True)


class Asa(IconeForjado):
    forma = "asa"

    def desenhar(self, tela):
        membrana = tela.poly([v2(3, 4), v2(17, 3), v2(14, 8), v2(16, 11), v2(12, 13), v2(13, 17), v2(5, 12)])
        tela.pintar(membrana, self.mat(relevo=0.7))
        for fim in (v2(17, 3), v2(16, 11), v2(13, 17)):
            tela.traco(v2(3, 4), fim, Mat((40, 30, 40), 4)[2], sobre=True)


class Carne(IconeForjado):
    forma = "carne"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4, 16), v2(9, 11), 1.2), OSSO_MAT)
        tela.pintar(tela.elipse_girada(v2(12, 8), 6, 4.5, -0.7), self.mat(relevo=1.2, ruido=0.2))
        for a, b in ((v2(9, 6), v2(13, 10)), (v2(11, 4.5), v2(15, 8.5))):
            tela.traco(a, b, (60, 20, 26), sobre=True)          # pontos de costura


class Coracao(IconeForjado):
    forma = "coracao"

    def desenhar(self, tela):
        coracao = tela.circulo(v2(7, 8), 4.2) | tela.circulo(v2(13, 8), 4.2) | tela.poly([v2(3, 9.5), v2(17, 9.5), v2(10, 18)])
        tela.pintar(coracao, self.mat(relevo=1.4, especular=(255, 220, 220)))
        tela.traco(v2(10, 6), v2(9, 12), self.mat()[1], sobre=True)
        if self.raro:
            tela.brilho(v2(10, 10), 7, self.cor, 0.5)


class Selo(IconeForjado):
    forma = "selo"

    def desenhar(self, tela):
        borda = tela.poly([v2(10 + 7 * math.cos(a * 0.5236), 10 + 7 * math.sin(a * 0.5236) * (1 if a % 2 else 0.9))
                           for a in range(12)])
        tela.pintar(borda, self.mat(relevo=1.2))
        tela.pintar(tela.circulo(v2(10, 10), 4), self.mat(relevo=0.6).escuro(1))
        tela.tracos([v2(8, 8), v2(12, 8), v2(10, 12), v2(8, 8)], self.detalhe, sobre=True)


class Mola(IconeForjado):
    forma = "mola"

    def desenhar(self, tela):
        pts = [v2(5 if k % 2 else 15, 3 + k * 2.2) for k in range(7)]
        tela.pintar(tela.corrente(pts, [1.0] * len(pts)), self.metal())


class Luva(IconeForjado):
    forma = "luva"

    def desenhar(self, tela):
        palma = tela.elipse(10, 12, 5, 5.5)
        dedos = [tela.capsula(v2(6 + k * 2.6, 9), v2(6 + k * 2.6, 3.5 + abs(k - 1.5)), 1.2) for k in range(4)]
        polegar = tela.capsula(v2(6, 12), v2(3, 9), 1.3)
        mascara = palma | polegar
        for d in dedos:
            mascara |= d
        tela.pintar(mascara, self.mat(relevo=1.0))
        for k in range(4):
            tela.px(6 + k * 2.6, 3.8 + abs(k - 1.5), (220, 220, 230))          # cravos
        tela.pintar(tela.poly([v2(5, 16), v2(15, 16), v2(15, 19), v2(5, 19)]), COURO)               # punho


class Totem(IconeForjado):
    forma = "totem"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(6, 3), v2(14, 3), v2(15, 18), v2(5, 18)]), self.mat(relevo=1.0, ruido=0.2))
        for y in (7, 13):
            for x in (8, 12):
                tela.chapado(tela.circulo(v2(x, y), 1.0), (20, 10, 14))
            tela.traco(v2(7, y + 2.5), v2(13, y + 2.5), (40, 26, 20), sobre=True)
        self.gema(tela, v2(10, 3.5), 1.2)


FORMAS = {c.forma: c for c in (Espada, Adaga, Machado, Martelo, Clava, Cajado, Foice, Arco, Alaude, Chicote, Peitoral,
                               Manto, Elmo, Anel, Pingente, Coroa, Estandarte, Frasco, Pao, Tigela, Bomba, Pergaminho,
                               Tomo, Bolsa, Osso, Presa, Olho, Erva, Cogumelo, Flor, Gota, Minerio, Escama, Novelo, Alma,
                               Cranio, Bola, Sino, Pena, Tecido, Asa, Carne, Coracao, Selo, Mola, Luva, Totem,
                               ElmoSimples, Capuz, Calcas, Botas, Escudo, Lanterna, Vela, Queijo, Flauta, Rato)}

# (pedaço da chave do item, forma, cor, variação) — o primeiro que combinar vale. Ordem importa!
PALAVRAS = [
    # consumíveis
    ("pocao_grande", "frasco", (210, 40, 60), "alto"), ("pocao_de_vida", "frasco", (200, 36, 48), ""),
    ("elixir_de_energia", "frasco", (70, 150, 230), "alto"), ("elixir_sombrio", "frasco", (130, 60, 190), "alto"),
    ("antidoto", "frasco", (110, 200, 90), ""), ("tonico", "frasco", (230, 120, 50), ""),
    ("oleo", "frasco", (160, 150, 110), "alto"), ("frasco_de_veneno", "frasco", (120, 200, 60), ""),
    ("agua_benta", "frasco", (190, 220, 250), ""), ("pena_da_fenix", "pena", (240, 120, 50), "fogo"),
    ("pao", "pao", (184, 132, 76), ""), ("ensopado", "tigela", (120, 100, 60), ""),
    ("bomba", "bomba", (64, 60, 74), ""), ("po_cegante", "bolsa", (200, 170, 220), ""),
    ("pergaminho_do_esqueleto", "pergaminho", (226, 216, 196), ""), ("pergaminho_do_lobo", "pergaminho", (140, 180, 230), ""),
    ("pergaminho_da_torreta", "pergaminho", (110, 150, 220), ""), ("pergaminho_da_fada", "pergaminho", (120, 230, 160), ""),
    ("pergaminho_de_protecao", "pergaminho", (230, 200, 120), ""), ("pergaminho_da_tempestade", "pergaminho", (170, 140, 255), ""),
    ("tomo_da_presa", "tomo", (90, 110, 60), ""), ("tomo_do_folego", "tomo", (150, 90, 50), ""),
    ("tomo_do_baluarte", "tomo", (90, 100, 140), ""), ("tomo_das_sombras", "tomo", (50, 40, 70), ""),
    ("tomo_da_maldicao", "tomo", (110, 30, 50), ""), ("tomo_do_toque_frio", "tomo", (70, 110, 120), ""),
    ("tomo_da_chuva_viva", "tomo", (60, 120, 70), ""), ("tomo_da_execucao", "tomo", (120, 20, 30), ""),
    # armas
    ("presa_do_dragao", "espada", (230, 220, 196), ""), ("espada_de_prata", "espada", (200, 210, 230), ""),
    ("espada", "espada", (150, 140, 130), ""), ("adagas", "adaga", (70, 50, 100), ""), ("faca", "adaga", (150, 130, 120), ""),
    ("arco_de_seda", "arco", (220, 220, 230), ""), ("arco", "arco", (220, 210, 186), ""),
    ("cetro", "cajado", (120, 230, 200), ""), ("cajado_runico", "cajado", (110, 160, 255), ""), ("cajado", "cajado", (180, 230, 120), ""),
    ("martelo_da_forja", "martelo", (200, 110, 60), ""), ("martelo", "martelo", (190, 190, 210), ""),
    ("machado", "machado", (150, 150, 168), ""), ("clava", "clava", (120, 86, 56), ""),
    ("foice_do_ceifador", "foice", (150, 160, 190), ""), ("foice", "foice", (150, 200, 110), ""),
    ("alaude", "alaude", (150, 96, 56), ""), ("chicote", "chicote", (110, 72, 50), ""),
    # armaduras
    ("gibao", "peitoral", (128, 88, 56), "couro"), ("cota", "peitoral", (120, 150, 90), "cota"),
    ("elmo", "elmo", (130, 130, 146), ""), ("armadura_de_ossos", "peitoral", (220, 210, 190), "osso"),
    ("placas", "peitoral", (200, 150, 80), ""), ("couraca", "peitoral", (150, 70, 56), ""),
    ("armadura", "peitoral", (78, 78, 96), ""), ("veste", "manto", (220, 210, 180), ""),
    ("manto_do_rei", "manto", (70, 30, 90), ""), ("manto_de_seda", "manto", (200, 200, 214), ""),
    ("manto", "manto", (110, 100, 80), ""), ("capa", "manto", (140, 28, 40), ""),
    # amuletos
    ("anel", "anel", (196, 152, 70), ""), ("olho_de_vidro", "olho", (110, 180, 230), ""), ("olho_da_aranha", "olho", (200, 40, 60), ""),
    ("nariz", "bola", (220, 40, 40), ""), ("colar", "pingente", (226, 214, 186), ""), ("rosario", "pingente", (150, 30, 40), ""),
    ("veu", "manto", (230, 230, 240), ""), ("guizo", "sino", (220, 190, 70), ""), ("talisma", "pingente", (240, 140, 50), ""),
    ("coracao", "coracao", (180, 30, 50), ""), ("relicario", "pingente", (220, 190, 120), ""),
    ("estandarte", "estandarte", (160, 34, 40), ""), ("fios", "novelo", (220, 200, 160), ""), ("amuleto", "pingente", (226, 214, 190), ""),
    # materiais
    ("alma_da_mae_aranha", "alma", (170, 230, 150), ""), ("alma_do_golem", "alma", (250, 150, 70), ""),
    ("alma_do_dragao_osseo", "alma", (160, 240, 230), ""), ("alma_do_rei_sombrio", "alma", (170, 110, 250), ""),
    ("alma_do_lich", "alma", (110, 210, 255), ""), ("alma_do_senhor_da_guerra", "alma", (240, 80, 70), ""),
    ("alma_do_dragao_jovem", "alma", (255, 120, 60), ""), ("alma_do_ossario", "alma", (230, 226, 200), ""),
    ("alma_do_brutamontes", "alma", (240, 120, 180), ""),
    ("alma", "alma", (150, 120, 240), ""), ("po_de_osso", "bolsa", (220, 210, 190), ""), ("cranio", "cranio", (220, 210, 190), ""),
    ("totem", "totem", (190, 170, 130), ""), ("medula", "osso", (240, 200, 160), ""), ("osso", "osso", (226, 216, 196), ""),
    ("filacteria", "frasco", (120, 230, 200), "alto"), ("seda", "novelo", (234, 234, 234), ""),
    ("dente_de_dragao", "presa", (240, 226, 190), ""), ("dente", "presa", (230, 220, 180), ""), ("presa", "presa", (240, 230, 210), ""),
    ("ferrao", "presa", (200, 50, 50), ""), ("unha", "presa", (150, 160, 120), ""), ("lamina_de_louva", "presa", (150, 200, 120), ""),
    ("erva", "erva", (90, 160, 70), ""), ("cogumelo", "cogumelo", (90, 170, 230), ""), ("petala", "flor", (230, 120, 200), ""),
    ("sangue", "gota", (160, 20, 30), ""), ("tinta", "gota", (210, 40, 40), ""), ("cera", "gota", (60, 50, 64), ""),
    ("ferro_negro", "minerio", (80, 80, 104), ""), ("prata", "minerio", (200, 214, 236), "brilha"),
    ("obsidiana", "minerio", (90, 50, 130), "brilha"), ("pedra_runica", "minerio", (110, 160, 230), "brilha"),
    ("nucleo", "alma", (100, 200, 230), ""), ("escama", "escama", (200, 80, 50), ""), ("quitina", "escama", (110, 130, 80), ""),
    ("carapaca", "escama", (100, 80, 60), ""), ("placa_de_bronze", "escama", (200, 150, 80), ""),
    ("pata", "presa", (150, 90, 60), ""), ("ovo", "bola", (230, 230, 210), "ovo"), ("couro", "tecido", (140, 100, 62), ""),
    ("trapo", "tecido", (120, 110, 90), ""), ("tecido_listrado", "tecido", (230, 220, 200), "listras"),
    ("mola", "mola", (150, 110, 80), ""), ("maquiagem", "frasco", (240, 236, 230), ""), ("balao", "bola", (200, 60, 160), "balao"),
    ("sino", "sino", (190, 160, 80), "rachado"), ("luva", "luva", (200, 50, 46), ""), ("fio_de_marionete", "novelo", (230, 220, 200), ""),
    ("carne", "carne", (190, 90, 90), ""), ("selo", "selo", (190, 40, 40), ""), ("coroa", "coroa", (230, 190, 80), ""),
    ("asa", "asa", (80, 60, 90), ""), ("glandula", "gota", (130, 220, 70), ""), ("olho", "olho", (220, 200, 90), ""),
]

FORMA_POR_TIPO = {"equipamento": ("espada", (170, 170, 190), ""), "consumivel": ("frasco", (180, 120, 200), ""),
                  "material": ("bolsa", (150, 130, 110), "")}


from .itens_fases import FORMAS_DAS_FASES  # noqa: E402  (formas próprias dos itens das fases novas)

FORMAS.update(FORMAS_DAS_FASES)

from .itens_etapa8 import FORMAS_ETAPA8  # noqa: E402  (lança, besta, chapéu, orbe... dos itens da etapa 8)

FORMAS.update(FORMAS_ETAPA8)


def icone_do_item(chave, dados, tipo):
    """Cria o IconeForjado de um item do itens.json (campo "icone" > PALAVRAS > tipo)."""
    raridade = dados.get("raridade", "comum")
    escolhido = dados.get("icone")
    if escolhido:
        forma, cor, variacao = escolhido["forma"], escolhido.get("cor", (160, 160, 170)), escolhido.get("variacao", "")
    else:
        forma, cor, variacao = next(((f, c, v) for pedaco, f, c, v in PALAVRAS if pedaco in chave), FORMA_POR_TIPO[tipo])
    detalhe = (escolhido or {}).get("detalhe")
    return FORMAS[forma](cor, detalhe, raridade, semente=sum(map(ord, chave)), variacao=variacao)
