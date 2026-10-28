"""Heróis secretos do Reino dos Ratos (etapa 6; docs/planos/reino_dos_ratos.md). Mesmo esqueleto humanoide dos outros
heróis: cada um vira uma "geometria" nova (as camadas de raça, chapéus e equipamento saem para ele também).

    MedicoDaPeste   sobretudo encerado até a canela, capuz de couro sobre os ombros, máscara de bico com lentes acesas,
                    chapéu de aba larga, luvas e a bengala com uma lanceta na ponta (no golpe ele estoca com ela)
    SenhorDosRatos  (etapa 6B) manto de trapos com capuz, máscara da peste branca e fina com olhos vermelhos de mosca,
                    cajado torto com um crânio de rato numa mão e um livro na outra (abre no golpe), moscas em volta
                    e ratinhos aos pés
    EnxameDeMoscas  (invocação do Senhor dos Ratos) uma nuvem de moscas da forja de insetos (criaturas/demos.py), cada
                    uma batendo as asas no seu ritmo; no bote a nuvem avança, na morte elas caem

Os materiais vêm por kw (roupas.py faz as roupas das subclasses e especializações com outras cores e adornos).
"""
import math

from PIL import Image

from ..motor import Mat, metal, v2
from ..humanoide import perna, braco, pescoco, manto, capa, capuz, cinto, quadro_tronco, quadro_cabeca
from ..anim import Modelo
from .. import armas, fx
from ..criaturas.demos import MoscaDemo
from .herois import morte_extras, OSSO
from .adornos import caveirinha
from .bubonicos import ratinho


# ============================================================
# MÉDICO DA PESTE — máscara de bico preta com lentes verdes, chapéu de aba larga, sobretudo encerado
# ============================================================

class MedicoDaPeste(Modelo):
    nome = "medico_da_peste"
    H = 74
    estilo = "estocada"
    prop = dict(ombros=0.22, quadris=0.18)
    base = dict(braco_f=(0.45, 0.75), braco_b=(0.2, 0.75), arma_f=2.85, pe_f=(-0.07, 0), pe_b=(0.08, 0))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "medico_da_peste")
        self.casaco = kw.get("casaco", Mat((38, 36, 42), 6, desce=0.35, ruido=0.08, relevo=0.9, especular=(110, 112, 124)))
        self.chapeu = kw.get("chapeu", Mat((28, 26, 30), 6, relevo=0.8, ruido=0.1))
        self.mascara = kw.get("mascara", Mat((46, 40, 44), 6, relevo=1.1, ruido=0.15, especular=(120, 110, 116)))
        self.lentes = kw.get("lentes", (120, 255, 140))
        self.luvas = kw.get("luvas", Mat((54, 40, 34), 5, relevo=0.9, ruido=0.12))
        self.calca = kw.get("calca", Mat((44, 40, 40), 5, ruido=0.1))
        self.bota = kw.get("bota", Mat((40, 30, 26), 5, relevo=0.9, especular=(100, 84, 70)))
        self.fita = kw.get("fita", (110, 90, 60))                     # a fita do chapéu e as fivelas
        self.bengala = kw.get("bengala", Mat((44, 32, 28), 5, ruido=0.2))
        self.prata = kw.get("prata", metal((200, 204, 214), especular=(255, 255, 255)))

    def desenhar(self, tela, ctx, J):
        H = self.H
        s = math.sin(ctx.a)
        capa(tela, J, self.casaco.escuro(2), comprimento=0.58, vento=0.025 * s, larg=0.14, rasgos=2, semente=91)
        braco(tela, J, "b", self.casaco.escuro(1), self.luvas.escuro(1), grossura=1.15)
        perna(tela, J, "b", self.calca.escuro(1), self.bota.escuro(1), cano=0.45)
        perna(tela, J, "f", self.calca, self.bota, cano=0.45)
        mm = manto(tela, J, self.casaco, folga=0.07, rasgos=2, semente=93, barra=-0.06)
        self.frente_do_casaco(tela, J, mm)
        cinto(tela, J, Mat((50, 36, 30), 5, relevo=0.8), fivela=metal(self.fita), altura=0.02)
        self.frascos(tela, J)
        pescoco(tela, J, self.mascara.escuro(1), 0.04)
        self.capuz(tela, J, s)
        self.cabeca(tela, ctx, J)
        if self.armado:
            self.bengala_lanceta(tela, ctx, J)
        braco(tela, J, "f", self.casaco, self.luvas, grossura=1.15)
        tela.pintar(tela.circulo(J["mao_f"], H * 0.024), self.luvas)                  # a luva por cima do cabo
        if ctx.anim == "ataque" and ctx.i in (1, 2):                                  # uma baforada de ervas no bote
            boca = quadro_cabeca(J).pt(J["P"]["cabeca"] * 1.4, -J["P"]["cabeca"] * 0.65)
            for k in range(4):
                p = boca + v2(3 + k * 3, -1 - k * 1.5 + s)
                tela.px(p[0], p[1], (170, 220, 150) if k % 2 else (120, 180, 110), emite=k == 0)
        morte_extras(tela, self, ctx, J)

    def frente_do_casaco(self, tela, J, mm):
        """A abertura do sobretudo (uma linha escura até a barra) e os botões de couro."""
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        topo, fim = Q.pt(0.05 * H, T * 0.92), Q.pt(0.07 * H, -0.42 * H)
        tela.traco(topo, fim, self.casaco[0], sobre=True)
        for k in range(4):
            p = Q.pt(0.065 * H, T * (0.8 - k * 0.22))
            tela.px(p[0], p[1], self.fita)

    def frascos(self, tela, J):
        """Frasquinhos presos no cinto e uma bolsa de couro no quadril de trás."""
        H = self.H
        Q = quadro_tronco(J)
        for k, cor in enumerate(((120, 220, 120), (220, 80, 70), (230, 200, 90))):
            p = Q.pt((-0.03 + k * 0.035) * H, -0.01 * H)
            tela.pintar(tela.capsula(p, p + v2(0, H * 0.035), H * 0.011), Mat(cor, 5, relevo=1.2))
            tela.px(p[0], p[1] - 1, (200, 190, 170))
        bolsa = Q.pt(-0.07 * H, -0.02 * H)
        tela.pintar(tela.elipse(bolsa[0], bolsa[1] + H * 0.03, H * 0.035, H * 0.03), Mat((86, 60, 42), 5, relevo=0.9))

    def capuz(self, tela, J, s):
        """O capuz de couro encerado que cobre o pescoço e cai sobre os ombros (capelinha)."""
        H = self.H
        Q = quadro_tronco(J)
        T = J["P"]["tronco"]
        pts = Q.pts([(-0.13 * H, T * 0.98), (0.11 * H, T * 0.98), (0.12 * H, T * 0.66), (0.0, T * 0.6 + s * 0.3),
                     (-0.14 * H, T * 0.68)])
        tela.pintar(tela.poly(pts + [J["cabeca"] + J["hu"] * 0.5]), self.mascara.escuro(1))

    def cabeca(self, tela, ctx, J):
        """Cabeça coberta de couro, o bico comprido e costurado, as lentes acesas e o chapéu de aba larga."""
        C = quadro_cabeca(J)
        h = J["P"]["cabeca"]
        w = h * 0.9
        ang = math.atan2(J["hu"][1], J["hu"][0])
        tela.pintar(tela.elipse_girada(C.pt(w * 0.12, -h * 0.02), w * 0.6, h * 0.58, ang), self.mascara)
        bico = tela.poly(C.pts([(w * 0.4, h * 0.06), (w * 1.05, -h * 0.24), (w * 1.8, -h * 0.82), (w * 1.02, -h * 0.54),
                                (w * 0.4, -h * 0.38)]))
        tela.pintar(bico, self.mascara.claro(1))
        tela.traco(C.pt(w * 0.6, -h * 0.05), C.pt(w * 1.5, -h * 0.66), self.mascara[1], sobre=True)     # a costura
        tela.traco(C.pt(w * 0.55, h * 0.0), C.pt(w * 1.2, -h * 0.34), self.mascara[4], sobre=True)     # o brilho do couro
        for x in (w * 0.18, w * 0.44):                                                  # as lentes de vidro
            c = C.pt(x, h * 0.1)
            tela.pintar(tela.circulo(c, max(1.4, h * 0.15)), metal(self.fita))
            tela.chapado(tela.circulo(c, max(1.0, h * 0.1)), tuple(int(v * 0.3) for v in self.lentes))
            if not ctx.morto:
                tela.px(c[0], c[1], self.lentes, emite=True)
                tela.px(c[0] + 1, c[1], self.lentes, emite=True)
                tela.brilho(c, 3.5, self.lentes, 0.55)
        aba = tela.elipse_girada(C.pt(w * 0.12, h * 0.44), w * 1.12, h * 0.14, ang + math.pi / 2 + 0.08)
        tela.pintar(aba, self.chapeu)                                                   # a aba larga
        copa = tela.poly(C.pts([(-w * 0.36, h * 0.46), (w * 0.56, h * 0.46), (w * 0.46, h * 1.08), (-w * 0.3, h * 1.02)]))
        tela.pintar(copa, self.chapeu)
        tela.traco(C.pt(-w * 0.34, h * 0.57), C.pt(w * 0.53, h * 0.57), self.fita, sobre=True)            # a fita

    def bengala_lanceta(self, tela, ctx, J):
        """A bengala: castão de prata em cima e uma lanceta na ponta (que toca o chão parado e vai à frente no golpe)."""
        H = self.H
        mao, ang = J["mao_f"], J["arma_f"]
        ponta = armas.cajado(tela, mao, ang, H * 0.42, self.bengala, atras=H * 0.05)
        d = v2(math.sin(ang), -math.cos(ang))
        topo = mao - d * (H * 0.05)
        tela.pintar(tela.circulo(topo, H * 0.018), self.prata)                          # o castão
        armas.adaga(tela, ponta - d * (H * 0.01), ang, H * 0.07, self.prata, self.bengala, larg=0.7)
        if ctx.anim == "ataque" and ctx.i in (1, 2):                                  # o risco da estocada
            n = v2(-d[1], d[0])
            for lado in (-1, 1):
                tela.traco(mao + n * (lado * 2.5) + d * (H * 0.1), ponta + n * (lado * 2.5), (196, 206, 220))
            if ctx.i == 2:
                tela.brilho(ponta + d * (H * 0.06), 4, (230, 240, 255), 0.7)


# ============================================================
# SENHOR DOS RATOS — máscara branca de bico fino, olhos de mosca, trapos, cajado e livro, moscas e ratos
# ============================================================

class SenhorDosRatos(Modelo):
    nome = "senhor_dos_ratos"
    H = 74
    estilo = "magia"
    prop = dict(ombros=0.21, quadris=0.18)
    base = dict(braco_f=(0.55, 0.85), braco_b=(0.65, 1.55), arma_f=0.12, pe_f=(-0.06, 0), pe_b=(0.08, 0))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.nome = kw.get("nome", "senhor_dos_ratos")
        self.trapos = kw.get("trapos", Mat((70, 62, 56), 6, desce=0.4, ruido=0.35, relevo=0.8, dither=0.4))
        self.capuz_mat = kw.get("capuz", Mat((52, 46, 44), 6, relevo=0.8, ruido=0.3))
        self.mascara = kw.get("mascara", Mat((222, 214, 196), 6, relevo=1.0, ruido=0.12))
        self.olhos = kw.get("olhos", (220, 30, 30))
        self.livro = kw.get("livro", Mat((70, 40, 34), 5, relevo=0.9, ruido=0.2))
        self.magia = kw.get("magia", fx.FOGO_VERDE)
        self.moscas = kw.get("moscas", 6)                              # quantas moscas voam em volta
        self.ratos = kw.get("ratos", 2)                                # quantos ratinhos ficam aos pés
        self.pele = kw.get("pele", Mat((150, 146, 130), 5, relevo=0.9, satur=0.5))

    def desenhar(self, tela, ctx, J):
        H = self.H
        s = math.sin(ctx.a)
        golpe = ctx.anim == "ataque" and ctx.i in (1, 2)
        capa(tela, J, self.trapos.escuro(2), comprimento=0.6, vento=0.03 * s, larg=0.14, rasgos=8, semente=95)
        braco(tela, J, "b", self.trapos.escuro(1), None, grossura=1.1)
        perna(tela, J, "b", self.trapos.escuro(2), None, pe_mat=self.pele.escuro(1))
        perna(tela, J, "f", self.trapos.escuro(1), None, pe_mat=self.pele)
        manto(tela, J, self.trapos, folga=0.08, rasgos=9, semente=97, barra=-0.02)
        cinto(tela, J, Mat((96, 76, 52), 4, ruido=0.4), altura=0.03, larg=0.016)          # a corda na cintura
        pescoco(tela, J, self.capuz_mat.escuro(1), 0.04)
        self.cabeca(tela, ctx, J)
        if self.armado:
            self.cajado_de_rato(tela, ctx, J, golpe)
        braco(tela, J, "f", self.trapos, None, grossura=1.1)
        tela.pintar(tela.circulo(J["mao_f"], H * 0.022), self.pele)
        self.tomo(tela, ctx, J, golpe)
        self.moscas_em_volta(tela, ctx, J, golpe)
        if not (ctx.anim == "morte" and ctx.i >= 2):
            for k in range(self.ratos):                                                # os que o seguem
                ratinho(tela, v2(self.ancora[0] - H * (0.14 + 0.13 * k), self.ancora[1] - 2), olhando=1, fase=ctx.a + k)
        morte_extras(tela, self, ctx, J, cor=(40, 50, 20), cor2=(70, 90, 30))

    def cabeca(self, tela, ctx, J):
        """O capuz de trapos com o rosto na sombra e a máscara branca de bico fino, com olhos de mosca vermelhos."""
        _, C, _ = capuz(tela, J, self.capuz_mat, ponta=0.45, sombra=(12, 8, 10))
        h = J["P"]["cabeca"]
        w = h * 0.9
        bico = tela.poly(C.pts([(w * 0.4, h * 0.1), (w * 1.1, -h * 0.28), (w * 1.95, -h * 0.66), (w * 1.05, -h * 0.46),
                                (w * 0.42, -h * 0.34)]))
        tela.pintar(bico | tela.elipse(*C.pt(w * 0.32, -h * 0.02), w * 0.34, h * 0.4), self.mascara)
        tela.traco(C.pt(w * 0.85, -h * 0.2), C.pt(w * 1.0, -h * 0.4), self.mascara[1], sobre=True)        # uma rachadura
        for x, r in ((w * 0.2, 0.2), (w * 0.5, 0.17)):                                  # olhos de mosca (facetados)
            c = C.pt(x, h * 0.08)
            raio = max(1.6, h * r)
            tela.chapado(tela.circulo(c, raio), tuple(int(v * 0.55) for v in self.olhos))
            if not ctx.morto:
                tela.chapado(tela.circulo(c, raio * 0.7), self.olhos, emite=True)
                tela.px(c[0] - 0.5, c[1] - 0.7, (255, 170, 150), emite=True)
                tela.brilho(c, 3.5, self.olhos, 0.5)

    def cajado_de_rato(self, tela, ctx, J, golpe):
        """Cajado torto com um crânio de rato no alto (os olhos acendem verde no golpe)."""
        H = self.H
        topo = armas.cajado(tela, J["mao_f"], J["arma_f"], H * 0.34, Mat((76, 58, 42), 5, ruido=0.3), atras=H * 0.26,
                            torto=1.8)
        d = v2(math.sin(J["arma_f"]), -math.cos(J["arma_f"]))
        caveirinha(tela, topo + d * 2.2, r=H * 0.03, mat=OSSO, olhos=self.magia[3] if golpe else (60, 20, 20), emite=golpe)
        for k in (-1, 1):                                                              # dentinhos de rato
            tela.px(*(topo + d * (2.2 + H * 0.035) + v2(-d[1], d[0]) * k * 0.6), (238, 226, 184))
        if golpe:
            tela.brilho(topo + d * 2.5, 7, self.magia[2], 0.6)

    def tomo(self, tela, ctx, J, golpe):
        """O livro na mão de trás: fechado, com um crânio de rato na capa; no golpe ele abre e solta runas verdes."""
        if ctx.anim == "morte" and ctx.i >= 2:
            return
        H = self.H
        mao = J["mao_b"]
        if golpe:
            for lado in (-1, 1):                                                       # as duas folhas abertas
                folha = tela.poly([mao, mao + v2(lado * H * 0.07, -H * 0.02), mao + v2(lado * H * 0.07, H * 0.05),
                                   mao + v2(0, H * 0.06)])
                tela.pintar(folha, Mat((206, 196, 160), 4, relevo=0.6))
            tela.brilho(mao + v2(0, -H * 0.02), 8, self.magia[2], 0.7)
            for k in range(3):
                fx.runa(tela, mao + v2(H * (0.04 + k * 0.05), -H * (0.06 + k * 0.04)), self.magia[3], 2, forma=k)
            return
        capa_do_livro = tela.poly([mao + v2(-H * 0.04, -H * 0.03), mao + v2(H * 0.045, -H * 0.04),
                                   mao + v2(H * 0.05, H * 0.05), mao + v2(-H * 0.035, H * 0.06)])
        tela.pintar(capa_do_livro, self.livro)
        tela.traco(mao + v2(-H * 0.035, H * 0.055), mao + v2(H * 0.05, H * 0.045), (200, 190, 160))   # as páginas
        caveirinha(tela, mao + v2(H * 0.005, H * 0.008), r=H * 0.012, mat=OSSO, olhos=(120, 20, 20))
        tela.pintar(tela.circulo(mao + v2(-H * 0.045, H * 0.01), H * 0.02), self.pele.escuro(1))       # a mão

    def moscas_em_volta(self, tela, ctx, J, golpe):
        """Moscas zumbindo em volta da cabeça e dos ombros (no golpe elas voam para a frente)."""
        if ctx.anim == "morte" and ctx.i >= 3:
            return
        H = self.H
        centro = J["pescoco"] + v2(0, -H * 0.04)
        for k in range(self.moscas):
            a = ctx.a * (1.0 + 0.3 * (k % 3)) + k * 2.4
            r = H * (0.16 + 0.05 * ((k * 7) % 4))
            p = centro + v2(math.cos(a) * r, math.sin(a * 1.3) * r * 0.6)
            if golpe:
                p = p + v2(H * (0.12 + 0.03 * (k % 3)), 0)
            x, y = int(round(p[0])), int(round(p[1]))
            if 0 <= x < tela.w and 1 <= y < tela.h and tela.alfa[y, x] == 0:
                tela.px(x, y, (30, 28, 26))
                tela.px(x, y - 1, (180, 190, 200))


# ============================================================
# ENXAME DE MOSCAS — invocação: uma nuvem de moscas da forja de insetos
# ============================================================

class MoscaDoEnxame(MoscaDemo):
    """Uma mosca miúda da nuvem (a mosca da peste dos demos, menor)."""
    nome = "mosca_do_enxame"
    S = 20


class EnxameDeMoscas(Modelo):
    nome = "enxame_de_moscas"
    H = 40
    larg, alt = 124, 84
    ancora = (54, 80)
    LUGARES = ((-20, -30), (2, -40), (18, -28), (-6, -22), (12, -16), (-18, -14), (0, -30), (24, -40), (-26, -42))
    LINHA_DA_MOSCA = {"parado": "parado", "sentado": "parado", "ataque": "ataque", "dano": "dano", "morte": "morte"}

    def __init__(self, **kw):
        super().__init__(**kw)
        self.mosca = MoscaDoEnxame()
        self._quadros = {}

    def quadro_da_mosca(self, linha, j):
        n = dict(self.mosca.animacoes())[linha]
        chave = (linha, j % n)
        if chave not in self._quadros:
            self._quadros[chave] = self.mosca.quadro(linha, j % n, n)
        return self._quadros[chave]

    def quadro(self, anim, i, n):
        """A nuvem: cada mosca no seu lugar, balançando; no bote a nuvem avança; no dano ela se espalha; na morte
        as moscas despencam."""
        margem = 60                                                    # (moscas na borda não saem da imagem)
        imagem = Image.new("RGBA", (self.larg + 2 * margem, self.alt + 2 * margem), (0, 0, 0, 0))
        linha = self.LINHA_DA_MOSCA.get(anim, "parado")
        t = 2 * math.pi * i / max(1, n)
        ax, ay = self.mosca.ancora
        for k, (dx, dy) in enumerate(self.LUGARES):
            x = dx + 3 * math.sin(t + k * 1.7)
            y = dy + 2 * math.cos(t * 1.3 + k)
            if anim == "ataque":
                x += [0, 12, 18, 6][min(i, 3)] * (0.6 + 0.1 * (k % 4))
            elif anim == "dano":
                x, y = x * 1.3, y * 1.15
            elif anim == "morte":
                y = min(-4.0, y + i * (9 + k % 3 * 3))
            quadro = self.quadro_da_mosca(linha, i + k)
            imagem.alpha_composite(quadro, (int(round(margem + self.ancora[0] + x - ax)),
                                            int(round(margem + self.ancora[1] + y - ay))))
        return imagem.crop((margem, margem, margem + self.larg, margem + self.alt))
