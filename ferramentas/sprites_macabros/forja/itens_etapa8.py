"""Formas de ícone dos itens da etapa 8 (mesma base IconeForjado de itens.py).

    armas:      Lanca, Tridente, Rapieira, Montante, Besta, Varinha, Garra, Cutelo
    secundária: EscudoTorre, Orbe, Turibulo
    cabeça:     Chapeu (variação "pontudo")
    amuleto:    Contas
"""
import math

from .motor import Mat, v2
from .itens import IconeForjado, MADEIRA, COURO, OURO, FERRO, ao_longo, perpendicular


class Lanca(IconeForjado):
    forma = "lanca"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(2.5, 18.5), v2(14, 6), 0.8), MADEIRA)
        ponta = tela.poly([v2(13, 7.5), v2(16.5, 2), v2(18.5, 1.5), v2(17.8, 3.5), v2(14.5, 8.5)])
        tela.pintar(ponta, self.metal())
        tela.pintar(tela.capsula(v2(12.5, 7.2), v2(14.3, 8.8), 1.1), COURO)
        self.gema(tela, v2(13.4, 8), 0.8)


class Tridente(IconeForjado):
    forma = "tridente"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(3, 18.5), v2(12, 8), 0.8), MADEIRA)
        base, ponta = v2(12, 8), v2(16.5, 2.5)
        n = perpendicular(base, ponta)
        dentes = tela.capsula(base + n * 3.6, base - n * 3.6, 0.8)
        for k in (-3.2, 0, 3.2):
            a = base + n * k
            b = a + (ponta - base) * (1.0 if k == 0 else 0.8)
            dentes |= tela.capsula(a, b, 0.7, 0.4)
        tela.pintar(dentes, self.metal())


class Rapieira(IconeForjado):
    forma = "rapieira"

    def desenhar(self, tela):
        base, ponta = v2(6.5, 13.5), v2(18, 2)
        tela.pintar(tela.capsula(base, ponta, 0.9, 0.35), self.metal())
        tela.pintar(tela.circulo(base, 2.6) & ~tela.circulo(base + v2(-0.6, 0.6), 1.4), OURO)       # guarda de taça
        tela.pintar(tela.capsula(v2(5.5, 14.5), v2(3.5, 16.5), 0.9), COURO)
        self.gema(tela, v2(2.8, 17.2), 1.1)


class Montante(IconeForjado):
    forma = "montante"

    def desenhar(self, tela):
        base, ponta = v2(6, 14), v2(18, 2)
        tela.pintar(tela.capsula(base, ponta, 2.3, 0.7), self.metal())
        tela.traco(ao_longo(base, ponta, 0.08), ao_longo(base, ponta, 0.85), self.metal()[5], sobre=True)
        n = perpendicular(base, ponta)
        tela.pintar(tela.capsula(base + n * 4.2, base - n * 4.2, 1.1), FERRO if self.raridade == "comum" else OURO)
        tela.pintar(tela.capsula(v2(5, 15), v2(2.5, 17.5), 1.0), COURO)
        self.gema(tela, v2(2, 18), 1.1)


class Besta(IconeForjado):
    forma = "besta"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(3, 15), v2(15, 6), 1.3, 1.0), self.mat(relevo=0.9, ruido=0.2))
        arco = [v2(9, 2), v2(12, 6), v2(13.5, 8.5), v2(16.5, 11), v2(19, 13.5)]
        tela.pintar(tela.corrente(arco, [0.6, 1.0, 1.2, 1.0, 0.6]), FERRO)
        tela.tracos([v2(9, 2), v2(8, 10), v2(19, 13.5)], (220, 210, 190))
        tela.traco(v2(8, 10), v2(16.5, 4), (150, 120, 90))
        self.gema(tela, v2(5, 13.5), 1.0)


class Varinha(IconeForjado):
    forma = "varinha"

    def desenhar(self, tela):
        tela.pintar(tela.corrente([v2(4, 17.5), v2(9, 11), v2(11.5, 9.5), v2(15, 4.5)], [1.0, 0.9, 0.8, 0.6]),
                    self.mat(relevo=1.0, ruido=0.25))
        tela.pintar(tela.capsula(v2(4, 17.5), v2(6, 15), 1.2), COURO)
        tela.pintar(tela.circulo(v2(15.5, 4), 1.8), Mat(self.detalhe, 5, relevo=1.5, especular=(255, 255, 255)))
        tela.brilho(v2(15.5, 4), 5, self.detalhe, 0.6)


class Garra(IconeForjado):
    forma = "garra"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(3, 17.5), v2(10, 17.5), v2(10.5, 10), v2(4, 10)]), COURO)          # punho de couro
        for k, dx in enumerate((4.5, 7.5, 10.5)):
            tela.pintar(tela.poly([v2(dx, 10.5), v2(dx + 2, 10.5), v2(dx + 5.5, 1.5 + k)]), self.metal())
        tela.traco(v2(3.5, 13), v2(10, 13), FERRO[1], sobre=True)
        self.gema(tela, v2(6.8, 15), 1.0)


class Cutelo(IconeForjado):
    forma = "cutelo"

    def desenhar(self, tela):
        tela.pintar(tela.capsula(v2(3, 18), v2(7.5, 13.5), 1.1), MADEIRA)
        lamina = tela.poly([v2(7, 14.5), v2(16.5, 5), v2(18.5, 7.5), v2(18, 11), v2(10.5, 17.5)])
        tela.pintar(lamina, self.metal())
        tela.traco(v2(17.5, 7), v2(11, 16.5), self.metal()[6], sobre=True)
        tela.chapado(tela.circulo(v2(14.5, 10), 1.0), (20, 14, 18))


class EscudoTorre(IconeForjado):
    forma = "escudo_torre"

    def desenhar(self, tela):
        corpo = tela.poly([v2(4, 1.5), v2(16, 1.5), v2(16, 15.5), v2(10, 18.5), v2(4, 15.5)])
        tela.pintar(corpo, self.metal())
        tela.pintar(tela.poly([v2(5.8, 3.3), v2(14.2, 3.3), v2(14.2, 14.6), v2(10, 16.6), v2(5.8, 14.6)]) & corpo,
                    self.metal().escuro(1), linha_interna=False)
        tela.traco(v2(10, 3.5), v2(10, 16), FERRO[5], sobre=True)
        tela.traco(v2(6, 8), v2(14, 8), FERRO[5], sobre=True)
        self.gema(tela, v2(10, 8), 1.2)


class Orbe(IconeForjado):
    forma = "orbe"

    def desenhar(self, tela):
        tela.pintar(tela.poly([v2(6, 18), v2(14, 18), v2(12.5, 14.5), v2(7.5, 14.5)]), FERRO)                   # base
        tela.pintar(tela.circulo(v2(10, 8.5), 6), Mat(self.cor, 6, relevo=1.6, especular=(255, 255, 255)))
        tela.chapado(tela.circulo(v2(8, 6.5), 1.6), (255, 255, 255), emite=True)
        tela.brilho(v2(10, 8.5), 9, self.cor, 0.55)


class Turibulo(IconeForjado):
    forma = "turibulo"

    def desenhar(self, tela):
        tela.tracos([v2(10, 0.5), v2(10.5, 4), v2(10, 6.5)], (180, 160, 110))
        corpo = tela.circulo(v2(10, 12), 5) | tela.poly([v2(6.5, 9), v2(13.5, 9), v2(10, 5.5)])
        tela.pintar(corpo, self.metal())
        for x in (7.5, 10, 12.5):
            tela.chapado(tela.circulo(v2(x, 12.5), 0.7), (255, 190, 90), emite=True)
        tela.brilho(v2(10, 12.5), 6, (255, 170, 80), 0.45)
        tela.chapado(tela.poly([v2(8, 17), v2(12, 17), v2(11, 18.5), v2(9, 18.5)]), self.metal()[1])


class Chapeu(IconeForjado):
    forma = "chapeu"

    def desenhar(self, tela):
        mat = self.mat(relevo=0.8, ruido=0.15)
        aba = tela.elipse(10, 14.5, 9, 2.6)
        if self.variacao == "pontudo":
            copa = tela.poly([v2(5.5, 14), v2(14.5, 14), v2(11.5, 6), v2(13, 2.5), v2(16.5, 3.5), v2(14, 1), v2(9, 3.5)])
        else:
            copa = tela.poly([v2(5, 14.5), v2(6, 6), v2(14, 5.5), v2(15, 14.5)])
        tela.pintar(aba | copa, mat)
        tela.traco(v2(5.5, 12.5), v2(14.5, 12.5), COURO[1], sobre=True)
        tela.pintar(tela.circulo(v2(10, 12.5), 1.2), OURO)
        self.gema(tela, v2(10, 12.5), 0.8)


class Contas(IconeForjado):
    forma = "contas"

    def desenhar(self, tela):
        mat = self.mat(relevo=1.3, especular=(250, 240, 210))
        for k in range(11):
            a = math.pi * (0.1 + 0.8 * k / 10)
            p = v2(10 - math.cos(a) * 7, 3 + math.sin(a) * 9)
            tela.pintar(tela.circulo(p, 1.5), mat if k % 2 else mat.escuro(1))
        tela.pintar(tela.circulo(v2(10, 13.5), 1.9), mat.claro(1))
        tela.pintar(tela.poly([v2(8.5, 15), v2(11.5, 15), v2(12.5, 19), v2(7.5, 19)]), Mat(self.detalhe, 5, ruido=0.4))


FORMAS_ETAPA8 = {c.forma: c for c in (Lanca, Tridente, Rapieira, Montante, Besta, Varinha, Garra, Cutelo, EscudoTorre, Orbe,
                                      Turibulo, Chapeu, Contas)}
