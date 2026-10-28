"""Visualizador dos sprites macabros (pygame).

    python visualizar.py

Teclas
  G          modo GALERIA (todos os personagens de uma família)
  H          modo HORDA (herói contra uma horda aleatória)
  ← / →      troca a família (galeria) ou o herói (horda)
  1 2 3 4    animação: parado / ataque / dano / morte (galeria)
  A          um inimigo da horda ataca     D  o herói ataca
  X          mata um inimigo da horda      R  nova horda
  + / -      zoom          ESC  sair

Usa o carregador do próprio jogo (src/visual/sprites_macabros.py); as funções abaixo só juntam o que o
visualizador precisa (nomes por família, desenhar pelos pés, animador com escala).
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

import pygame  # noqa: E402

from visual.sprites_macabros import Sprites, Animador  # noqa: E402

LARG, ALT = 1280, 720
CHAO = 560
ANIMS = ["parado", "ataque", "dano", "morte"]


def nomes_da_familia(sprites, familia):
    return [nome for nome, meta in sprites.catalogo.items() if meta.get("familia") == familia]


def familias(sprites):
    vistas = []
    for meta in sprites.catalogo.values():
        if meta.get("familia") not in vistas:
            vistas.append(meta.get("familia"))
    return vistas


def desenhar(sprites, tela, nome, anim, i, x_pe, y_pe, escala, olhando_esquerda=False):
    """Desenha o quadro com os pés em (x_pe, y_pe)."""
    imagem = sprites.quadro(nome, anim, i, escala, olhando_esquerda)
    ax, ay = sprites.ancora(nome, escala, olhando_esquerda)
    tela.blit(imagem, (round(x_pe - ax), round(y_pe - ay)))


class AnimadorComEscala(Animador):
    """O Animador do jogo com uma escala fixa e um jeito de se desenhar."""

    def __init__(self, sprites, nome, escala=2):
        super().__init__(sprites, nome)
        self.escala = escala

    def desenhar(self, tela, x_pe, y_pe, olhando_esquerda=False):
        desenhar(self.sprites, tela, self.nome, self.anim, self.indice, x_pe, y_pe, self.escala, olhando_esquerda)


def fundo(larg, alt, semente=3):
    """Cenário noturno simples: céu, lua de sangue, ruínas e chão de pedra."""
    rng = random.Random(semente)
    img = pygame.Surface((larg, alt))
    for y in range(alt):
        t = y / alt
        cor = (int(18 + 30 * t), int(12 + 8 * t), int(26 + 10 * t))
        pygame.draw.line(img, cor, (0, y), (larg, y))
    for _ in range(140):
        x, y = rng.randrange(larg), rng.randrange(int(alt * 0.6))
        b = rng.randrange(60, 160)
        img.set_at((x, y), (b, b - 20, b))
    # lua
    for r, a in ((110, 18), (80, 30), (60, 60)):
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (170, 40, 40, a), (r, r), r)
        img.blit(s, (larg - 260 - r, 120 - r))
    pygame.draw.circle(img, (150, 36, 36), (larg - 260, 120), 46)
    pygame.draw.circle(img, (120, 26, 30), (larg - 245, 110), 12)
    # silhueta de catedral em ruínas
    base = CHAO - 40
    cor = (24, 16, 28)
    for x, w, h in ((80, 60, 220), (150, 120, 160), (290, 40, 260), (340, 140, 120), (520, 50, 200), (900, 70, 180),
                    (980, 30, 240), (1030, 110, 140)):
        pygame.draw.rect(img, cor, (x, base - h, w, h + 40))
        pygame.draw.polygon(img, cor, [(x, base - h), (x + w // 2, base - h - w * 0.8), (x + w, base - h)])
        for k in range(2):
            pygame.draw.rect(img, (60, 20, 26), (x + w // 2 - 3, base - h + 30 + k * 50, 6, 14))
    # chão
    pygame.draw.rect(img, (30, 24, 32), (0, CHAO - 10, larg, alt - CHAO + 10))
    pygame.draw.rect(img, (44, 36, 46), (0, CHAO - 10, larg, 4))
    for _ in range(300):
        x, y = rng.randrange(larg), rng.randrange(CHAO, alt)
        img.set_at((x, y), (50, 42, 52))
    return img


def sombra(tela, x, y, larg):
    s = pygame.Surface((larg, larg // 4), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 110), s.get_rect())
    tela.blit(s, (x - larg // 2, y - larg // 8))


class Visualizador:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARG, ALT))
        pygame.display.set_caption("Sprites Macabros")
        self.sp = Sprites()
        self.fundo = fundo(LARG, ALT)
        self.fonte = pygame.font.SysFont("georgia", 22)
        self.fonte_p = pygame.font.SysFont("georgia", 15)
        self.relogio = pygame.time.Clock()
        self.modo = "galeria"
        self.familias = familias(self.sp)
        self.fam = 0
        self.anim = 0
        self.zoom = 3
        self.herois = nomes_da_familia(self.sp, "herois")
        self.heroi = 0
        self.tempo = 0.0
        self.nova_horda()

    # ---------------- horda ----------------
    def nova_horda(self):
        fams = [f for f in self.familias if f != "herois"]
        fam = random.choice(fams)
        nomes = nomes_da_familia(self.sp, fam)
        lideres =[n for n in nomes if self.sp.catalogo[n]["papel"] in ("chefe", "chefe_de_horda", "elite")]
        tropa = [n for n in nomes if n not in lideres] or nomes
        escolhidos = []
        if lideres:
            escolhidos.append(random.choice(lideres))
        for _ in range(random.randint(5, 7)):
            escolhidos.append(random.choice(tropa))
        self.horda_familia = fam
        self.horda = []
        for k, nome in enumerate(escolhidos):
            linha = k % 3
            col = k // 3
            x = 700 + col * 185 + linha * 55 + (40 if k == 0 else 0)
            y = CHAO - 40 + linha * 38
            esc = 2 if self.sp.catalogo[nome]["tamanho"] in ("pequeno", "medio") else 2
            a = AnimadorComEscala(self.sp, nome, escala=esc)
            a.tempo = random.random()
            self.horda.append([a, x, y])
        self.horda.sort(key=lambda e: e[2])
        self.anim_heroi = AnimadorComEscala(self.sp, self.herois[self.heroi], escala=3)

    def desenhar_horda(self):
        h = self.anim_heroi
        sombra(self.tela, 300, CHAO + 30, 110)
        h.desenhar(self.tela, 300, CHAO + 30)
        for a, x, y in self.horda:
            sombra(self.tela, x, y, 70)
            a.desenhar(self.tela, x, y, olhando_esquerda=True)
        self.texto(f"HORDA: {self.horda_familia.replace('_', ' ')}", 20, 16, (230, 190, 120))
        self.texto("A ataque inimigo   D ataque do herói   X matar   R nova horda   ←/→ herói   G galeria", 20, ALT - 30,
                   (170, 160, 180), self.fonte_p)

    # ---------------- galeria ----------------
    def desenhar_galeria(self):
        fam = self.familias[self.fam]
        nomes = nomes_da_familia(self.sp, fam)
        anim = ANIMS[self.anim]
        n = len(nomes)
        larg_total = LARG - 80
        passo = larg_total / max(1, n)
        z = self.zoom if n <= 6 else max(2, self.zoom - 1)
        for k, nome in enumerate(nomes):
            x = 40 + passo * (k + 0.5)
            q = self.sp.quadros_de(nome, anim)
            vel = 6 if anim == "parado" else 7
            i = int(self.tempo * vel) % (q + (3 if anim != "parado" else 0))
            i = min(i, q - 1)
            sombra(self.tela, x, CHAO, 60 * z // 3)
            desenhar(self.sp, self.tela, nome, anim, i, x, CHAO, z)
            s = self.fonte_p.render(nome, True, (200, 190, 210))
            self.tela.blit(s, (x - s.get_width() / 2, CHAO + 40 + (k % 2) * 20))
        self.texto(f"{fam.replace('_', ' ').upper()}  —  {anim}", 20, 16, (230, 190, 120))
        self.texto("←/→ família   1-4 animação   +/- zoom   H horda", 20, ALT - 30, (170, 160, 180), self.fonte_p)

    def texto(self, t, x, y, cor, fonte=None):
        fonte = fonte or self.fonte
        self.tela.blit(fonte.render(t, True, (0, 0, 0)), (x + 2, y + 2))
        self.tela.blit(fonte.render(t, True, cor), (x, y))

    # ---------------- laço ----------------
    def eventos(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type != pygame.KEYDOWN:
                continue
            k = e.key
            if k == pygame.K_ESCAPE:
                return False
            if k == pygame.K_g:
                self.modo = "galeria"
            elif k == pygame.K_h:
                self.modo = "horda"
            elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.zoom = min(5, self.zoom + 1)
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.zoom = max(1, self.zoom - 1)
            if self.modo == "galeria":
                if k == pygame.K_RIGHT:
                    self.fam = (self.fam + 1) % len(self.familias)
                elif k == pygame.K_LEFT:
                    self.fam = (self.fam - 1) % len(self.familias)
                elif pygame.K_1 <= k <= pygame.K_4:
                    self.anim = k - pygame.K_1
                    self.tempo = 0
            else:
                vivos = [h for h in self.horda if h[0].anim != "morte"]
                if k == pygame.K_r:
                    self.nova_horda()
                elif k in (pygame.K_RIGHT, pygame.K_LEFT):
                    self.heroi = (self.heroi + (1 if k == pygame.K_RIGHT else -1)) % len(self.herois)
                    self.anim_heroi = AnimadorComEscala(self.sp, self.herois[self.heroi], escala=3)
                elif k == pygame.K_a and vivos:
                    random.choice(vivos)[0].tocar("ataque")
                    self.anim_heroi.tocar("dano")
                elif k == pygame.K_d:
                    self.anim_heroi.tocar("ataque")
                    if vivos:
                        min(vivos, key=lambda h: h[1])[0].tocar("dano")
                elif k == pygame.K_x and vivos:
                    min(vivos, key=lambda h: h[1])[0].tocar("morte")
        return True

    def rodar(self, salvar=None, quadros=None):
        rodando = True
        cont = 0
        while rodando:
            dt = self.relogio.tick(60) / 1000
            self.tempo += dt
            rodando = self.eventos()
            for a, _, _ in self.horda:
                a.atualizar(dt)
            self.anim_heroi.atualizar(dt)
            self.tela.blit(self.fundo, (0, 0))
            if self.modo == "galeria":
                self.desenhar_galeria()
            else:
                self.desenhar_horda()
            pygame.display.flip()
            cont += 1
            if quadros and cont >= quadros:
                if salvar:
                    pygame.image.save(self.tela, salvar)
                break
        pygame.quit()


if __name__ == "__main__":
    v = Visualizador()
    # modo de teste: python visualizar.py --foto saida.png [galeria|horda] [familia]
    if "--foto" in sys.argv:
        i = sys.argv.index("--foto")
        saida = sys.argv[i + 1]
        resto = sys.argv[i + 2:]
        if resto:
            v.modo = resto[0]
        if len(resto) > 1 and resto[1] in v.familias:
            v.fam = v.familias.index(resto[1])
        if len(resto) > 2:
            v.anim = int(resto[2])
        v.rodar(salvar=saida, quadros=20)
    else:
        v.rodar()
