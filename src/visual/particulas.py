"""Partículas de clima dos cenários, em "pixels grandes" (quadradinhos de 4x4).

    Particulas
    ├── VagaLume   pisca e passeia devagar
    ├── Brasa      sobe balançando e apaga
    ├── Cinza      cai devagar, levada pelo vento
    ├── Poeira     flutua quase parada
    ├── Gota       cai do teto (cavernas)
    ├── Confete    cai girando (circo)
    ├── Neve       flocos caindo devagar
    ├── Nevasca    neve com vento forte, riscada em diagonal
    ├── Cintila    brilhos de cristal que acendem e apagam
    ├── GotaVerde  gota de esgoto (Gota de outra cor)           ┐
    ├── Vapor      fiapos que sobem do chão e somem             │ Reino dos Ratos
    ├── Mosca      voa em voltas tortas em torno de um ponto    │ (docs/planos/reino_dos_ratos.md)
    └── Olhos      pares de olhos vermelhos piscando no escuro  ┘

Cada tipo muda só como nasce e como se mexe.
"""

import math
import random

PIXEL = 4


def na_grade(valor):
    return int(valor) // PIXEL * PIXEL


class Particulas:
    """Um grupo de partículas do mesmo tipo."""

    frente = False                 # True = desenhada na frente dos personagens

    def __init__(self, quantidade, largura, altura, chao):
        self.largura, self.altura, self.chao = largura, altura, chao
        self.rng = random.Random(id(self))
        self.tempo = 0.0
        self.lista = [self.nascer(inicio=True) for _ in range(quantidade)]

    def nascer(self, inicio=False):
        """Devolve [x, y, vx, vy, vida, fase]."""
        raise NotImplementedError

    def mover(self, p, dt):
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt

    def morreu(self, p):
        return p[4] <= 0 or not (-20 <= p[0] <= self.largura + 20) or not (-20 <= p[1] <= self.altura + 20)

    def cor(self, p):
        return (255, 255, 255)

    def atualizar(self, dt):
        self.tempo += dt
        for i, p in enumerate(self.lista):
            self.mover(p, dt)
            if self.morreu(p):
                self.lista[i] = self.nascer()

    def desenhar(self, tela):
        for p in self.lista:
            cor = self.cor(p)
            if cor is not None:
                tela.fill(cor, (na_grade(p[0]), na_grade(p[1]), PIXEL, PIXEL))


class VagaLume(Particulas):
    def nascer(self, inicio=False):
        r = self.rng
        return [r.uniform(0, self.largura), r.uniform(self.altura * 0.35, self.chao + 60), r.uniform(-12, 12),
                r.uniform(-8, 8), r.uniform(4, 9), r.uniform(0, 6)]

    def mover(self, p, dt):
        p[2] += math.sin(self.tempo * 1.3 + p[5]) * 10 * dt
        p[3] += math.cos(self.tempo * 1.1 + p[5]) * 10 * dt
        super().mover(p, dt)

    def cor(self, p):
        brilho = math.sin(self.tempo * 3 + p[5])
        if brilho < -0.3:
            return None
        return (220, 240, 120) if brilho > 0.5 else (130, 160, 60)


class Brasa(Particulas):
    def nascer(self, inicio=False):
        r = self.rng
        y = r.uniform(0, self.altura) if inicio else self.altura + 4
        return [r.uniform(0, self.largura), y, r.uniform(-10, 10), r.uniform(-60, -25), r.uniform(4, 10), r.uniform(0, 6)]

    def mover(self, p, dt):
        p[2] = math.sin(self.tempo * 2 + p[5]) * 18
        super().mover(p, dt)

    def cor(self, p):
        return (255, 190, 90) if p[4] > 3 else ((220, 100, 40) if p[4] > 1.2 else (110, 40, 30))


class Cinza(Particulas):
    frente = True

    def nascer(self, inicio=False):
        r = self.rng
        y = r.uniform(0, self.altura) if inicio else -4
        return [r.uniform(0, self.largura + 100), y, r.uniform(-20, -6), r.uniform(10, 26), 99, r.uniform(0, 6)]

    def mover(self, p, dt):
        p[2] = -14 + math.sin(self.tempo + p[5]) * 10
        super().mover(p, dt)

    def cor(self, p):
        return (120, 110, 120) if int(p[5] * 10) % 2 else (80, 72, 84)


class Poeira(Particulas):
    def nascer(self, inicio=False):
        r = self.rng
        return [r.uniform(0, self.largura), r.uniform(0, self.chao + 40), r.uniform(-4, 4), r.uniform(-3, 3),
                r.uniform(6, 14), r.uniform(0, 6)]

    def cor(self, p):
        if math.sin(self.tempo * 0.8 + p[5]) < 0:
            return None
        return (110, 100, 96)


class Gota(Particulas):
    def nascer(self, inicio=False):
        r = self.rng
        y = r.uniform(0, 300) if inicio else r.uniform(-200, 0)
        return [r.uniform(0, self.largura), y, 0, r.uniform(180, 260), 99, 0]

    def morreu(self, p):
        return p[1] > self.chao + 30

    def cor(self, p):
        return (120, 150, 180)


class Confete(Particulas):
    frente = True
    CORES = [(150, 60, 60), (150, 130, 60), (70, 120, 80), (80, 90, 150), (130, 80, 130)]

    def nascer(self, inicio=False):
        r = self.rng
        y = r.uniform(0, self.altura) if inicio else -6
        return [r.uniform(0, self.largura), y, r.uniform(-10, 10), r.uniform(20, 40), 99, r.uniform(0, 6)]

    def mover(self, p, dt):
        p[2] = math.sin(self.tempo * 2 + p[5]) * 20
        super().mover(p, dt)

    def cor(self, p):
        if math.sin(self.tempo * 6 + p[5]) < -0.6:
            return None                    # girando de lado: some por um instante
        return self.CORES[int(p[5] * 10) % len(self.CORES)]


class Neve(Particulas):
    """Flocos caindo devagar e balançando com o vento (Cidadela Congelada)."""
    frente = True

    def nascer(self, inicio=False):
        r = self.rng
        y = r.uniform(0, self.altura) if inicio else -4
        return [r.uniform(-60, self.largura), y, r.uniform(4, 16), r.uniform(18, 40), 99, r.uniform(0, 6)]

    def mover(self, p, dt):
        p[2] = 10 + math.sin(self.tempo * 1.3 + p[5]) * 14
        super().mover(p, dt)

    def cor(self, p):
        return (235, 240, 250) if int(p[5] * 10) % 3 else (180, 200, 225)


class Nevasca(Particulas):
    """Neve tocada por vento forte: flocos rápidos em diagonal, riscados pelo movimento (Cidadela)."""
    frente = True

    def nascer(self, inicio=False):
        r = self.rng
        x = r.uniform(-200, self.largura) if inicio else r.uniform(-260, -10)
        return [x, r.uniform(-20, self.altura), r.uniform(220, 320), r.uniform(50, 110), 99, r.uniform(0, 6)]

    def mover(self, p, dt):
        p[3] = 70 + math.sin(self.tempo * 2.1 + p[5]) * 40       # rajadas
        super().mover(p, dt)

    def desenhar(self, tela):
        for p in self.lista:
            x, y = na_grade(p[0]), na_grade(p[1])
            perto = int(p[5] * 10) % 4 == 0
            tela.fill((235, 242, 252) if perto else (190, 206, 230), (x, y, PIXEL * 2 if perto else PIXEL, PIXEL))
            if perto:                                                 # rastro do floco mais perto
                tela.fill((150, 170, 205), (x - PIXEL * 2, y - PIXEL, PIXEL * 2, PIXEL))


class Cintila(Particulas):
    """Brilhos de cristal que acendem e apagam no lugar (salão de gelo)."""

    def nascer(self, inicio=False):
        r = self.rng
        return [r.uniform(0, self.largura), r.uniform(0, self.chao + 30), 0, 0, r.uniform(3, 7), r.uniform(0, 6)]

    def cor(self, p):
        brilho = math.sin(self.tempo * 2.5 + p[5] * 3)
        if brilho < 0.4:
            return None
        return (240, 250, 255) if brilho > 0.85 else (140, 200, 245)


class GotaVerde(Gota):
    """Gota de esgoto, pingando dos canos (Reino dos Ratos)."""

    def cor(self, p):
        return (110, 170, 90) if int(p[0]) % 3 else (70, 120, 60)


class Vapor(Particulas):
    """Fiapos de vapor fétido que sobem devagar do chão, balançam e somem."""

    def nascer(self, inicio=False):
        r = self.rng
        y = r.uniform(self.chao - 120, self.chao + 40) if inicio else r.uniform(self.chao, self.chao + 50)
        return [r.uniform(0, self.largura), y, 0, r.uniform(-16, -8), r.uniform(4, 8), r.uniform(0, 6)]

    def mover(self, p, dt):
        p[2] = math.sin(self.tempo * 0.9 + p[5]) * 8
        super().mover(p, dt)

    def cor(self, p):
        if (int(p[1]) // PIXEL + int(p[5] * 10)) % 2:          # pontilhado: fiapo ralo
            return None
        return (96, 112, 92) if p[4] > 2.5 else (62, 72, 60)


class Mosca(Particulas):
    """Moscas zumbindo em voltas tortas em volta de um ponto (lixo, carne, queijo)."""
    frente = True

    def __init__(self, quantidade, largura, altura, chao):
        rng = random.Random(quantidade * 7 + largura)
        self.centros = [(rng.uniform(80, largura - 80), rng.uniform(chao - 160, chao + 30)) for _ in range(3)]
        super().__init__(quantidade, largura, altura, chao)

    def nascer(self, inicio=False):
        r = self.rng
        cx, cy = r.choice(self.centros)
        return [cx, cy, r.uniform(28, 60), r.uniform(18, 40), 99, r.uniform(0, 6), cx, cy]

    def mover(self, p, dt):
        t = self.tempo * 3 + p[5]
        p[0] = p[6] + math.sin(t * 1.7) * p[2] + math.sin(t * 4.3) * 6       # voltas tortas
        p[1] = p[7] + math.cos(t * 1.3) * p[3] + math.sin(t * 5.1) * 4

    def cor(self, p):
        return (180, 190, 170) if math.sin(self.tempo * 30 + p[5]) > 0.6 else (24, 20, 18)   # asa brilha de vez em quando


class Olhos(Particulas):
    """Pares de olhos vermelhos no escuro: aparecem, piscam devagar e somem para surgir noutro canto."""

    def nascer(self, inicio=False):
        r = self.rng
        return [r.uniform(20, self.largura - 20), r.uniform(self.altura * 0.12, self.chao - 10), 0, 0,
                r.uniform(3, 8), r.uniform(0, 6)]

    def desenhar(self, tela):
        for p in self.lista:
            if p[4] < 0.4 or math.sin(self.tempo * 0.7 + p[5] * 3) > 0.92:      # acabando de chegar/ir, ou piscando
                continue
            cor = (230, 40, 40) if math.sin(self.tempo * 1.9 + p[5]) > -0.2 else (130, 16, 22)
            x, y = na_grade(p[0]), na_grade(p[1])
            tela.fill(cor, (x, y, PIXEL, PIXEL))
            tela.fill(cor, (x + PIXEL * 2, y, PIXEL, PIXEL))


TIPOS = {"vaga_lume": VagaLume, "brasa": Brasa, "cinza": Cinza, "poeira": Poeira, "gota": Gota, "confete": Confete,
         "neve": Neve, "nevasca": Nevasca, "cintila": Cintila,
         "gota_verde": GotaVerde, "vapor": Vapor, "mosca": Mosca, "olhos": Olhos}
