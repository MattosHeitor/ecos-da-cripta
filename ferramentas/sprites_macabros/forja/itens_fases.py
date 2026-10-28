"""Ícones próprios dos itens das fases novas (Parte 2, Etapa 5), no lugar das formas genéricas recoloridas.

Mesma técnica da forja de itens (itens.py: 20x20, volume, contorno, brilho), com uma diferença:
borda_raridade = o contorno do ícone ganha a cor da raridade (incomum verde, raro azul, épico roxo,
lendário dourado, amaldiçoado vermelho), para o item ser reconhecido mesmo pequeno.

    materiais   vitral, cinzas, coracao_negro, cristais, pele, lagrima, nucleo, martelo_partido,
                osso_sagrado, ferro_de_cruzada, reliquia, lodo, escama_molhada, moeda, casca, canino,
                seiva, minerio_de_brasa
    equipamento pa, picareta, mascara, mangual
"""
import math

from .motor import Mat, metal, v2
from .itens import IconeForjado, MADEIRA, FERRO, OURO, perpendicular, ao_longo


class IconeDaFase(IconeForjado):
    borda_raridade = True


# ============================================================
# MATERIAIS
# ============================================================

class Vitral(IconeDaFase):
    """Caco de vitral: pedaços coloridos acesos, chumbo escuro e a borda lascada."""
    forma = "vitral"
    CORES = [(196, 44, 60), (60, 92, 200), (232, 184, 70)]

    def desenhar(self, tela):
        """Caco pontudo com seis pedaços de vidro (cada um mais claro em cima), chumbo e moldura de pedra."""
        caco = tela.poly([v2(4, 18), v2(5, 9), v2(8, 2), v2(14, 3.5), v2(17, 10), v2(13, 13), v2(11.5, 18.5)])
        tela.chapado(caco, (40, 30, 44))
        centros = [v2(7, 6), v2(12, 5), v2(6.5, 12.5), v2(11, 9.5), v2(15, 9.5), v2(9, 16)]
        cores = [self.cor, self.CORES[1], self.CORES[2], self.CORES[0], self.cor, self.CORES[1]]
        for y in range(20):                                                                   # cada pixel vai para o pedaço mais perto
            for x in range(20):
                if not caco[y, x]:
                    continue
                d = sorted((((x - c[0]) ** 2 + (y - c[1]) ** 2), k) for k, c in enumerate(centros))
                if d[1][0] - d[0][0] < 6:                                                     # perto da divisa: chumbo
                    continue
                cor = cores[d[0][1]]
                claro = 1.25 if y < centros[d[0][1]][1] else 1.0
                tela.px(x, y, tuple(min(255, int(c * claro)) for c in cor), emite=True)
        tela.traco(v2(8, 3), v2(10, 6.5), (255, 255, 250), emite=True)                        # reflexo
        tela.px(14, 6, (255, 255, 250), emite=True)
        tela.brilho(v2(10, 10), 8, self.cor, 0.4)


class Cinzas(IconeDaFase):
    """Montinho de cinza escura com brasas e um fio de fumaça (o sol negro esfarelado)."""
    forma = "cinzas"

    def desenhar(self, tela):
        monte = tela.poly([v2(2.5, 17), v2(6, 11), v2(10, 8.5), v2(14, 11), v2(17.5, 17)]) | tela.elipse(10, 17, 7.6, 2.4)
        tela.pintar(monte, self.mat(relevo=0.8, ruido=0.45))
        for p in (v2(7, 14), v2(11, 12), v2(13.5, 15.5), v2(9, 16.5)):                        # brasas
            tela.px(p[0], p[1], (255, 140, 60), emite=True)
        tela.chapado(tela.circulo(v2(10, 10.5), 1.6), (12, 6, 14))                            # o sol negro
        tela.chapado(tela.circulo(v2(10, 10.5), 2.3) & ~tela.circulo(v2(10, 10.5), 1.6), self.detalhe, emite=True)
        tela.tracos([v2(10, 8), v2(9, 6), v2(10.5, 4), v2(9.5, 2)], (120, 110, 126))           # fumaça
        tela.brilho(v2(10, 13), 6, (255, 120, 60), 0.35)


class CoracaoNegro(IconeDaFase):
    """Coração do Eclipse: coração negro rachado de luz, com a coroa dourada do sol negro em volta."""
    forma = "coracao_negro"

    def desenhar(self, tela):
        for k in range(12):                                                                   # coroa
            a = k * math.pi / 6
            tela.traco(v2(10 + math.cos(a) * 6.5, 10.5 + math.sin(a) * 6.5),
                       v2(10 + math.cos(a) * (8.8 if k % 2 else 7.8), 10.5 + math.sin(a) * (8.8 if k % 2 else 7.8)),
                       (255, 200, 110), emite=True)
        coracao = tela.circulo(v2(7.4, 8.5), 3.6) | tela.circulo(v2(12.6, 8.5), 3.6) | tela.poly([v2(4, 10), v2(16, 10), v2(10, 16.5)])
        tela.pintar(coracao, self.mat(relevo=1.5, especular=(200, 160, 255)))
        tela.tracos([v2(10, 6.5), v2(9, 9), v2(10.5, 11), v2(9.5, 13.5)], (255, 120, 70), emite=True)   # rachadura acesa
        tela.brilho(v2(10, 10.5), 10, (255, 160, 80), 0.55)


class Cristais(IconeDaFase):
    """Três prismas de gelo saindo de uma base, com faces de luz e sombra e um brilho frio."""
    forma = "cristais"

    def desenhar(self, tela):
        tela.pintar(tela.elipse(10, 16.5, 7, 2.2), Mat((120, 140, 170), 5, relevo=0.8))
        for base, topo, larg in ((v2(6.5, 16), v2(4.5, 6), 2.2), (v2(10, 16.5), v2(11, 1.5), 2.8), (v2(13.5, 16), v2(16.5, 7.5), 2.0)):
            n = perpendicular(base, topo)
            tela.pintar(tela.poly([base + n * larg, topo, base]), self.mat(relevo=1.2).escuro(1))
            tela.pintar(tela.poly([base, topo, base - n * larg]), self.mat(relevo=1.6, especular=(255, 255, 255)))
            tela.traco(base, topo, (245, 252, 255))
        tela.px(11, 4, (255, 255, 255), emite=True)
        tela.brilho(v2(10, 7), 7, self.cor, 0.5)


class Pele(IconeDaFase):
    """Pele dobrada com tufos na borda e um brilho espectral frio."""
    forma = "pele"

    def desenhar(self, tela):
        pele = tela.poly([v2(3, 7), v2(8, 3.5), v2(14.5, 4.5), v2(17.5, 9), v2(15.5, 15.5), v2(9, 17.5), v2(3.5, 14)])
        m = self.mat(relevo=0.8, ruido=0.35)
        tela.pintar(pele, m)
        for k in range(9):                                                                    # tufos da borda
            a = k * 0.7
            p = v2(10 + math.cos(a) * 7.5, 10.5 + math.sin(a) * 6.5)
            tela.traco(p, p + v2(math.cos(a), math.sin(a)) * 1.6, m[4])
        tela.tracos([v2(5, 10), v2(10, 8.5), v2(16, 10)], m[1])                                # dobra
        tela.brilho(v2(10, 10), 8, (170, 210, 255), 0.4)


class Lagrima(IconeDaFase):
    """Lágrima de gelo facetada, com geada em volta."""
    forma = "lagrima"

    def desenhar(self, tela):
        gota = tela.circulo(v2(10, 12.5), 5) | tela.poly([v2(10, 1.5), v2(14.3, 10), v2(5.7, 10)])
        tela.pintar(gota, self.mat(relevo=1.7, especular=(255, 255, 255)))
        for fim in (v2(6, 13), v2(10, 17), v2(14, 13)):                                       # facetas
            tela.traco(v2(10, 4), fim, self.mat()[5])
        tela.px(8, 9, (255, 255, 255), emite=True)
        for p in (v2(3, 6), v2(16.5, 4), v2(17, 15), v2(3.5, 16)):                            # geada
            tela.px(p[0], p[1], (230, 248, 255), emite=True)
        tela.brilho(v2(10, 11), 7, self.cor, 0.45)


class Nucleo(IconeDaFase):
    """Coração de golem: carcaça de bronze rebitada com a fornalha acesa no meio."""
    forma = "nucleo"

    def desenhar(self, tela):
        tela.pintar(tela.circulo(v2(10, 10), 7), metal((150, 108, 64)))
        tela.chapado(tela.circulo(v2(10, 10), 4), (60, 24, 14))
        tela.chapado(tela.circulo(v2(10, 10), 3), self.cor, emite=True)
        tela.chapado(tela.circulo(v2(9.5, 9.5), 1.4), (255, 230, 150), emite=True)
        for k in range(6):                                                                    # rebites
            a = k * math.pi / 3 + 0.5
            tela.px(10 + math.cos(a) * 5.6, 10 + math.sin(a) * 5.6, (220, 190, 130))
        tela.tracos([v2(13, 4), v2(14.5, 6.5), v2(16.5, 7)], (255, 150, 60), emite=True)        # fenda acesa
        tela.brilho(v2(10, 10), 8, self.cor, 0.55)


class MarteloPartido(IconeDaFase):
    """Cabeça de martelo rachada e o cabo partido ao meio."""
    forma = "martelo_partido"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(8.5, 9), v2(11, 13), 0.9), MADEIRA)
        tela.pintar(tela.poly([v2(13, 14.5), v2(17.5, 18), v2(16.5, 19), v2(12, 15.5)]), MADEIRA)          # pedaço do cabo
        cabeca = tela.poly([v2(3, 5), v2(12, 2.5), v2(14, 8), v2(5, 10.5)])
        tela.pintar(cabeca, self.metal())
        tela.tracos([v2(8, 3.5), v2(7.5, 6), v2(9, 7.5), v2(8.5, 9.5)], (30, 22, 26))         # rachadura
        for p in (v2(11.5, 13.5), v2(12, 12.5)):                                              # lascas
            tela.px(p[0], p[1], MADEIRA[4])


class OssoSagrado(IconeDaFase):
    """Osso com runas douradas e uma auréola: relíquia de cavaleiro."""
    forma = "osso_sagrado"

    def desenhar(self, tela):
        m = self.mat(relevo=1.0, ruido=0.1)
        tela.pintar(tela.capsula(v2(5, 15), v2(15, 7), 1.5), m)
        for c in (v2(3.5, 15), v2(5.5, 17), v2(14.5, 5), v2(16.5, 7)):
            tela.pintar(tela.circulo(c, 2.0), m)
        for p in (v2(8, 12.5), v2(10, 11), v2(12, 9.5)):
            tela.px(p[0], p[1], (230, 180, 70), emite=True)
        aureola = tela.elipse(10, 3, 4.5, 1.4) & ~tela.elipse(10, 3, 3, 0.7)
        tela.chapado(aureola, (255, 220, 120), emite=True)
        tela.brilho(v2(10, 4), 6, (255, 210, 120), 0.5)


class FerroDeCruzada(IconeDaFase):
    """Pedaço de placa de armadura com a cruz da Ordem, enferrujado."""
    forma = "ferro_de_cruzada"

    def desenhar(self, tela):
        placa = tela.poly([v2(3.5, 4), v2(16.5, 3), v2(17, 12), v2(10, 18), v2(3, 12)])
        tela.pintar(placa, metal((120, 116, 124)))
        ferrugem = Mat(self.cor, 5, ruido=0.5)
        for p in (v2(5, 6), v2(14, 13), v2(7, 14), v2(15.5, 6)):
            tela.chapado(tela.circulo(p, 1.8) & placa, ferrugem[3])
        tela.chapado(tela.poly([v2(9, 5), v2(11, 5), v2(11, 15), v2(9, 15)]), (150, 40, 40))     # a cruz
        tela.chapado(tela.poly([v2(6, 8), v2(14, 8), v2(14, 10), v2(6, 10)]), (150, 40, 40))
        tela.traco(v2(4, 4.5), v2(16, 3.5), (210, 210, 220))


class Reliquia(IconeDaFase):
    """Fragmento de relicário dourado partido, com a pedra ainda presa."""
    forma = "reliquia"

    def desenhar(self, tela):
        caixa = tela.poly([v2(4, 6), v2(12, 3), v2(16.5, 7), v2(15, 15), v2(11, 13), v2(9, 17), v2(4.5, 14)])
        tela.pintar(caixa, OURO)
        tela.tracos([v2(11, 13), v2(12, 9), v2(10, 7)], (70, 44, 20))                          # quebra
        for p in (v2(6, 8), v2(14, 9), v2(6.5, 12.5)):                                        # filigrana
            tela.px(p[0], p[1], (255, 236, 160))
        self.gema(tela, v2(8.5, 10), 2.0)


class Lodo(IconeDaFase):
    """Poça de lodo escuro com bolhas e um brilho molhado."""
    forma = "lodo"

    def desenhar(self, tela):
        lodo = tela.elipse(10, 14, 8, 4) | tela.circulo(v2(8, 10.5), 3.5) | tela.circulo(v2(12.5, 11), 2.6)
        tela.pintar(lodo, self.mat(relevo=1.3, especular=(150, 160, 120)))
        for c, r in ((v2(7, 9.5), 1.3), (v2(13, 10.5), 0.9), (v2(11, 15), 0.8)):                # bolhas
            tela.chapado(tela.circulo(c, r) & ~tela.circulo(c, r - 0.6), (110, 120, 90))
        tela.px(6, 13, (170, 180, 140))
        tela.traco(v2(15, 16), v2(15, 18.5), self.mat()[1])                                    # pingo


class EscamaMolhada(IconeDaFase):
    """Escama de afogado: verde-azulada, com algas presas e gota escorrendo."""
    forma = "escama_molhada"

    def desenhar(self, tela):
        escama = tela.poly([v2(10, 2), v2(16.5, 5), v2(16, 12), v2(10, 18), v2(4, 12), v2(3.5, 5)])
        tela.pintar(escama, self.mat(relevo=1.4, especular=(220, 255, 240)))
        for y in (6, 9.5, 13):                                                                # anéis de crescimento
            tela.traco(v2(5.5, y), v2(14.5, y - 0.5), self.mat()[1], sobre=True)
        tela.tracos([v2(4, 6), v2(6, 9), v2(5, 12)], (60, 110, 60))                            # alga
        tela.px(13, 16, (180, 230, 230))
        tela.px(13, 18, (180, 230, 230))
        tela.px(8, 5, (255, 255, 255))


class Moeda(IconeDaFase):
    """Moeda velha do barqueiro: furo no meio, caveira cunhada e borda gasta."""
    forma = "moeda"

    def desenhar(self, tela):
        tela.pintar(tela.circulo(v2(10, 10), 7), self.metal())
        tela.chapado(tela.circulo(v2(10, 10), 5.6) & ~tela.circulo(v2(10, 10), 5.0), self.metal()[1])
        tela.chapado(tela.circulo(v2(10, 8), 2.3), self.metal()[5])                            # caveira
        for x in (9, 11):
            tela.px(x, 8, (60, 40, 20))
        tela.chapado(tela.circulo(v2(10, 13), 1.1), (20, 14, 18))                             # furo
        tela.px(6, 6, (255, 245, 200))


class Casca(IconeDaFase):
    """Élitro de besouro: meia carapaça brilhante com a nervura do meio."""
    forma = "casca"

    def desenhar(self, tela):
        casca = tela.poly([v2(9, 2), v2(14, 4), v2(16, 10), v2(14, 16), v2(9, 18.5), v2(7, 12), v2(6.5, 5)])
        tela.pintar(casca, self.mat(relevo=1.6, especular=(220, 240, 200)))
        tela.tracos([v2(9, 3), v2(9.5, 10), v2(9, 18)], self.mat()[0])
        for p in (v2(12, 7), v2(13, 11), v2(11.5, 14)):                                       # pontinhos
            tela.px(p[0], p[1], self.mat()[1])
        tela.traco(v2(13, 4.5), v2(15, 9), (240, 255, 220))


class Canino(IconeDaFase):
    """Presa de lobo curva, com a raiz ensanguentada."""
    forma = "canino"

    def desenhar(self, tela):
        tela.pintar(tela.corrente([v2(5, 3), v2(10, 5), v2(14, 10), v2(15, 17.5)], [2.8, 2.4, 1.5, 0.3]),
                    self.mat(relevo=1.2, especular=(255, 250, 235)))
        tela.chapado(tela.circulo(v2(5, 3.5), 2.2) & tela.circulo(v2(5, 3.5), 3), (140, 30, 36))
        tela.traco(v2(8, 5), v2(13, 9.5), (255, 252, 240))


class Seiva(IconeDaFase):
    """Gota de seiva viva cor de sangue presa numa folha, com veias que pulsam."""
    forma = "seiva"

    def desenhar(self, tela):
        tela.pintar(tela.elipse_girada(v2(7, 14), 5.5, 2.4, -0.6), Mat((120, 30, 36), 5, relevo=0.8))      # folha
        gota = tela.circulo(v2(11.5, 10), 4.4) | tela.poly([v2(11.5, 2), v2(15.2, 8.5), v2(7.8, 8.5)])
        tela.pintar(gota, self.mat(relevo=1.5, especular=(255, 220, 220)))
        tela.tracos([v2(11, 6), v2(12, 9), v2(11, 12)], (255, 120, 110), emite=True)
        tela.px(9.5, 8, (255, 240, 240))
        tela.brilho(v2(11.5, 10), 6, self.cor, 0.4)


class MinerioDeBrasa(IconeDaFase):
    """Pedra escura com veios de lava acesos."""
    forma = "minerio_de_brasa"

    def desenhar(self, tela):
        pedra = tela.poly([v2(3, 12), v2(6, 6), v2(11, 4.5), v2(16, 7), v2(18, 13), v2(14.5, 17.5), v2(6, 17.5)])
        tela.pintar(pedra, Mat((70, 56, 54), 6, relevo=1.3, ruido=0.3))
        for pts in ([v2(5, 12), v2(8, 10), v2(11, 11.5), v2(15, 9)], [v2(9, 6), v2(10, 9)], [v2(8, 15), v2(12, 14), v2(14, 16)]):
            tela.tracos(pts, self.cor, emite=True)
        tela.px(11, 11.5, (255, 230, 150), emite=True)
        tela.brilho(v2(10, 11), 7, self.cor, 0.55)


class Couro(IconeDaFase):
    """Couro curtido enrolado e amarrado com tira: o rolo de frente, o lado de pelo para dentro."""
    forma = "couro"

    def desenhar(self, tela):
        m = self.mat(relevo=0.9, ruido=0.3)
        rolo = tela.capsula(v2(4.5, 13), v2(15.5, 7), 4.2)
        tela.pintar(rolo, m)
        tela.pintar(tela.elipse_girada(v2(15.3, 7.1), 2.4, 4.0, -0.5), m.escuro(1))              # ponta do rolo
        tela.chapado(tela.elipse_girada(v2(15.4, 7.0), 1.1, 2.2, -0.5), m[0])                    # espiral
        tela.traco(v2(5, 10), v2(13.5, 5.2), m[5])                                             # luz de cima
        for t in (0.35, 0.68):                                                                  # tiras
            a = ao_longo((4.5, 13), (15.5, 7), t)
            tela.traco(a + v2(-1.6, -3.4), a + v2(1.8, 3.6), (70, 46, 30), sobre=True)
        tela.pintar(tela.poly([v2(3, 15), v2(7, 14.5), v2(6, 18.5), v2(2.5, 17.5)]), m.escuro(1))  # aba solta


class Tora(IconeDaFase):
    """Tora de madeira morta: anéis no corte, casca rachada e um galho seco."""
    forma = "tora"

    def desenhar(self, tela):
        casca = self.mat(relevo=1.0, ruido=0.35)
        tela.pintar(tela.capsula(v2(4, 13), v2(14.5, 7.5), 4.0), casca)
        corte = tela.elipse_girada(v2(14.5, 7.5), 2.8, 4.0, -0.48)
        tela.pintar(corte, Mat((196, 160, 110), 5, relevo=0.6))
        tela.chapado(tela.elipse_girada(v2(14.5, 7.5), 1.5, 2.3, -0.48) & ~tela.elipse_girada(v2(14.5, 7.5), 0.8, 1.3, -0.48),
                     (150, 112, 70))                                                            # anel
        tela.px(14.5, 7.5, (120, 84, 50))
        for a, b in ((v2(5, 11), v2(10, 8.5)), (v2(6, 15), v2(11, 12.5))):                     # rachaduras da casca
            tela.traco(a, b, casca[0], sobre=True)
        tela.tracos([v2(8, 8.5), v2(7, 5), v2(5, 3.5)], casca[2])                               # galho seco


class Lingote(IconeDaFase):
    """Lingote de ferro em trapézio, com a marca do martelo. variacao "quente": brilha em brasa."""
    forma = "lingote"

    def desenhar(self, tela):
        topo = tela.poly([v2(5, 7), v2(15, 5), v2(17.5, 8.5), v2(7.5, 10.5)])
        frente = tela.poly([v2(7.5, 10.5), v2(17.5, 8.5), v2(17, 13), v2(7, 15.5)])
        lado = tela.poly([v2(5, 7), v2(7.5, 10.5), v2(7, 15.5), v2(3.5, 12)])
        tela.pintar(lado, self.metal().escuro(2))
        tela.pintar(frente, self.metal())
        tela.pintar(topo, self.mat(relevo=1.3, especular=(255, 245, 230)))
        tela.traco(v2(6, 7.2), v2(14.8, 5.3), (240, 236, 230))                                  # aresta
        tela.chapado(tela.circulo(v2(12, 11.8), 1.0), self.metal()[1])                           # marca do martelo
        if self.variacao == "quente":
            for pts in ([v2(8.5, 13.5), v2(12, 12.5), v2(16, 11)], [v2(9, 9), v2(13, 8)]):
                tela.tracos(pts, (255, 200, 110), emite=True)
            tela.brilho(v2(11, 10), 8, self.cor, 0.5)


class Ectoplasma(IconeDaFase):
    """Gosma de fantasma escorrendo PARA CIMA, com olhinhos fundos e brilho frio."""
    forma = "ectoplasma"

    def desenhar(self, tela):
        gosma = tela.elipse(10, 13, 6.5, 4.5) | tela.capsula(v2(7, 11), v2(6, 4), 1.6) | \
            tela.capsula(v2(11, 10), v2(12, 2.5), 2.0) | tela.capsula(v2(14, 12), v2(15.5, 6), 1.3)
        tela.pintar(gosma, self.mat(relevo=1.4, especular=(250, 255, 250)))
        for x in (8.5, 11.5):                                                                   # olhos
            tela.chapado(tela.circulo(v2(x, 13), 0.9), (24, 40, 36))
        tela.px(10, 15.5, (24, 40, 36))
        tela.px(11.5, 4, (255, 255, 255), emite=True)
        tela.brilho(v2(10, 10), 9, self.cor, 0.55)



# ============================================================
# EQUIPAMENTOS
# ============================================================

class Pa(IconeDaFase):
    """Pá de coveiro: cabo de madeira com punho em T e a lâmina com terra."""
    forma = "pa"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(3.5, 17.5), v2(12, 8), 0.9), MADEIRA)
        tela.pintar(tela.capsula(v2(2, 16), v2(5, 19), 0.8), MADEIRA)                          # punho em T
        lamina = tela.poly([v2(11, 5.5), v2(15, 1.5), v2(18.5, 5), v2(14.5, 9.5)])
        tela.pintar(lamina, self.metal())
        tela.chapado(tela.poly([v2(15.5, 2.5), v2(18, 5), v2(16.5, 6.5)]) & lamina, (90, 66, 44))   # terra
        tela.traco(v2(12, 6), v2(15, 3), self.metal()[6])


class Picareta(IconeDaFase):
    """Picareta-lâmina: cabeça de duas pontas, uma delas afiada como lâmina."""
    forma = "picareta"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(4, 18), v2(11.5, 7), 0.9), MADEIRA)
        cabeca = tela.poly([v2(3, 7), v2(9, 4), v2(12, 6.5), v2(17.5, 3), v2(14, 9), v2(11, 8.5), v2(5, 9.5)])
        tela.pintar(cabeca, self.metal())
        tela.traco(v2(12, 6.5), v2(17, 3.5), self.metal()[6])                                  # fio da lâmina
        tela.pintar(tela.circulo(v2(11, 7.2), 1.0), FERRO.escuro(1))


class Mascara(IconeDaFase):
    """Máscara de porcelana do Mercador: olhos vazados, sorriso pintado e uma rachadura."""
    forma = "mascara"

    def desenhar(self, tela):
        if self.variacao == "bico":
            self.bico(tela)
            return
        rosto = tela.elipse(10, 10, 6.5, 8)
        tela.pintar(rosto, self.mat(relevo=1.2, especular=(255, 255, 255)))
        for x in (7.3, 12.7):
            tela.chapado(tela.elipse(x, 8.5, 1.6, 1.1), (16, 10, 16))
        tela.tracos([v2(6, 13), v2(8, 14.5), v2(12, 14.5), v2(14, 13)], (140, 30, 40))         # sorriso
        tela.tracos([v2(11, 2.5), v2(10, 5), v2(11, 7)], (120, 110, 110))                       # rachadura
        tela.px(7.3, 11, self.detalhe)                                                         # lágrima pintada

    def bico(self, tela):
        """Máscara de médico da peste: couro com lentes redondas e o bico comprido cheio de ervas."""
        couro = self.mat(relevo=1.0, ruido=0.2)
        tela.pintar(tela.elipse(8, 7.5, 5.5, 5.5), couro)
        tela.pintar(tela.corrente([v2(9, 9), v2(13, 12), v2(17.5, 17.5)], [3.2, 2.2, 0.5]), couro)
        tela.traco(v2(10, 9.5), v2(16.5, 16.5), couro[1], sobre=True)                           # costura do bico
        for c in (v2(6, 6.5), v2(10, 6)):                                                     # lentes
            tela.pintar(tela.circulo(c, 1.7), Mat((40, 36, 40), 4, relevo=1.6, especular=(200, 230, 255)))
        tela.px(5.5, 6, (230, 240, 255), emite=True)
        tela.traco(v2(3, 5), v2(13, 3.5), (60, 44, 32))                                        # aba do chapéu


class Mangual(IconeDaFase):
    """Mangual: cabo, corrente e a bola de espinhos."""
    forma = "mangual"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(2.5, 18.5), v2(6.5, 12.5), 1.1), MADEIRA)
        tela.pintar(tela.circulo(v2(6.8, 12), 1.2), FERRO)                                    # argola do cabo
        elos = [v2(7.5 + k * 1.2, 10.8 - k * 0.5) for k in range(4)]                         # corrente caindo em curva
        for k, p in enumerate(elos):
            tela.px(p[0], p[1], (200, 200, 214) if k % 2 else (110, 108, 124))
        c = v2(14, 9.5)
        for k in range(8):                                                                    # espinhos
            a = k * math.pi / 4 + 0.2
            tela.pintar(tela.poly([c + v2(math.cos(a - 0.35), math.sin(a - 0.35)) * 3, c + v2(math.cos(a), math.sin(a)) * 5.4,
                                   c + v2(math.cos(a + 0.35), math.sin(a + 0.35)) * 3]), self.metal())
        tela.pintar(tela.circulo(c, 3.6), self.metal())
        tela.px(12.8, 8.2, (240, 240, 250))


FORMAS_DAS_FASES = {c.forma: c for c in (Vitral, Cinzas, CoracaoNegro, Cristais, Pele, Lagrima, Nucleo, MarteloPartido,
                                         OssoSagrado, FerroDeCruzada, Reliquia, Lodo, EscamaMolhada, Moeda, Casca,
                                         Canino, Seiva, MinerioDeBrasa, Pa, Picareta, Mascara, Mangual,
                                         Couro, Tora, Lingote, Ectoplasma)}
