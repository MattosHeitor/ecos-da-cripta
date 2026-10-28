"""Animações: biblioteca de poses humanoides e montagem das folhas de sprite."""
import json
import math
import os

import numpy as np
from PIL import Image

from .motor import Tela, lerp, v2
from .humanoide import esqueleto

# "sentado" é a pose do acampamento (em volta da fogueira); quem não senta (bestas, objetos) repete o "parado"
ANIMACOES = [("parado", 4), ("ataque", 4), ("dano", 2), ("morte", 4), ("sentado", 4)]


def misturar_pose(a, b, t):
    """Interpola duas poses (números e tuplas)."""
    r = dict(a)
    for k, vb in b.items():
        va = a.get(k, vb)
        if va is None or vb is None or isinstance(vb, (int, float)) and isinstance(va, bool):
            r[k] = vb if t >= 0.5 else va
        elif isinstance(vb, (int, float)) and isinstance(va, (int, float)):
            r[k] = va + (vb - va) * t
        elif isinstance(vb, (tuple, list)) and isinstance(va, (tuple, list)) and len(va) == len(vb):
            r[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
        else:
            r[k] = vb if t >= 0.5 else va
    return r


# ============================================================
# BIBLIOTECA DE POSES (frações de H; ângulos em radianos)
# ============================================================

def idle(base, i, amp=1.0):
    """Respiração: 4 quadros."""
    s = [0, 0.5, 1, 0.5][i]
    p = dict(base)
    p["respira"] = -0.7 * s * amp
    q = p.get("quadril", (0, 0))
    p["quadril"] = (q[0], q[1] + 0.006 * s * amp)
    for lado in ("f", "b"):
        k = "braco_" + lado
        if k in p and p.get("alvo_" + lado) is None:
            a1, a2 = p[k]
            p[k] = (a1 + 0.03 * s * amp * (1 if lado == "f" else -1), a2 + 0.04 * s * amp)
    if "arma_f" in p:
        p["arma_f"] = p["arma_f"] + 0.02 * s * amp
    return p


def sentado(base, i):
    """Sentado num tronco, de frente para o fogo, respirando devagar (4 quadros).

    A pélvis desce até a altura do assento e os pés vão para a frente; o IK dobra os joelhos.
    """
    s = [0, 0.5, 1, 0.5][i]
    p = dict(base)
    p.update(quadril=(-0.05, 0.255 + 0.004 * s), tronco=0.14, cabeca=0.02 - 0.03 * s, respira=-0.6 * s,
             pe_f=(0.19, 0.0), pe_b=(0.26, 0.0), joelho_f=-1, joelho_b=-1,
             braco_f=(0.45, 0.65), braco_b=(0.3, 0.8), alvo_f=None, alvo_b=None,
             arma_f=0.25, arma_b=0.0, giro=0.0, desloc=(0.0, 0.0))
    return p


def dano(base, i):
    p = dict(base)
    q = p.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=base.get("tronco", 0) - 0.32, cabeca=-0.35, quadril=(q[0] - 0.05, q[1] + 0.02))
        p["braco_b"] = (-0.6, 0.6)
        if p.get("alvo_f") is None:
            a1, a2 = p.get("braco_f", (0.2, 0.3))
            p["braco_f"] = (a1 - 0.3, a2 + 0.3)
        p["arma_f"] = p.get("arma_f", 0) - 0.35
    else:
        p.update(tronco=base.get("tronco", 0) - 0.15, cabeca=-0.12, quadril=(q[0] - 0.025, q[1] + 0.01))
        p["arma_f"] = p.get("arma_f", 0) - 0.15
    return p


def morte(base, i, H=None):
    """4 quadros: cambaleia, ajoelha, tomba para trás, caído."""
    p = dict(base)
    p["alvo_f"] = None
    p["alvo_b"] = None
    if i == 0:
        p.update(tronco=-0.35, cabeca=-0.5, quadril=(-0.05, 0.03), braco_f=(-0.3, 0.9), braco_b=(-0.9, 0.4),
                 arma_f=-0.6, pe_f=(-0.1, 0), pe_b=(0.06, 0))
    elif i == 1:
        # de joelhos, cabeça pendendo
        p.update(tronco=0.3, cabeca=0.5, quadril=(-0.04, 0.24), braco_f=(0.05, 0.15), braco_b=(-0.05, 0.1),
                 arma_f=1.75, pe_f=(-0.2, 0), pe_b=(0.1, 0))
    elif i == 2:
        # desabando sobre os joelhos
        p.update(tronco=1.05, cabeca=0.35, quadril=(-0.06, 0.29), braco_f=(-0.75, 0.1), braco_b=(-0.95, 0.15),
                 arma_f=2.4, pe_f=(-0.22, 0), pe_b=(0.08, 0))
    else:
        # caído de bruços
        p.update(tronco=0.0, cabeca=0.25, quadril=(0.0, 0.0), braco_f=(2.7, 0.3), braco_b=(0.4, 0.3),
                 arma_f=2.6, pe_f=(-0.03, 0), pe_b=(0.04, 0), giro=math.pi / 2, desloc=(-0.12, -0.07))
    return p


# poses de ataque: (antecipação, golpe, impacto, volta)
def ataque_corte(base, i):
    """Golpe de espada de uma mão, de cima para baixo."""
    p = dict(base)
    q = base.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=-0.18, cabeca=-0.05, quadril=(q[0] - 0.03, q[1] + 0.01), braco_f=(-2.5, -0.6), arma_f=-1.9,
                 braco_b=(0.5, 0.6))
    elif i == 1:
        p.update(tronco=0.32, cabeca=0.1, quadril=(q[0] + 0.1, q[1] + 0.05), braco_f=(1.75, 0.0), arma_f=1.45,
                 pe_b=(0.2, 0), pe_f=(-0.1, 0), braco_b=(-0.4, 0.3))
    elif i == 2:
        p.update(tronco=0.42, cabeca=0.15, quadril=(q[0] + 0.12, q[1] + 0.07), braco_f=(0.8, 0.1), arma_f=2.5,
                 pe_b=(0.22, 0), pe_f=(-0.1, 0), braco_b=(-0.5, 0.3))
    else:
        p.update(tronco=0.12, quadril=(q[0] + 0.04, q[1] + 0.02), braco_f=(0.4, 0.4), arma_f=1.0,
                 pe_b=(0.12, 0))
    return p


def ataque_estocada(base, i):
    p = dict(base)
    q = base.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=-0.12, quadril=(q[0] - 0.05, q[1] + 0.04), braco_f=(0.2, 1.6), arma_f=1.4,
                 braco_b=(0.6, 0.8), pe_f=(-0.1, 0))
    elif i == 1:
        p.update(tronco=0.38, quadril=(q[0] + 0.16, q[1] + 0.07), braco_f=(1.45, 0.05), arma_f=1.55,
                 braco_b=(-0.8, 0.2), pe_b=(0.3, 0), pe_f=(-0.12, 0), cabeca=0.1)
    elif i == 2:
        p.update(tronco=0.4, quadril=(q[0] + 0.17, q[1] + 0.08), braco_f=(1.5, 0.0), arma_f=1.6,
                 braco_b=(-0.9, 0.2), pe_b=(0.31, 0), pe_f=(-0.12, 0), cabeca=0.1)
    else:
        p.update(tronco=0.12, quadril=(q[0] + 0.05, q[1] + 0.02), braco_f=(0.6, 0.6), arma_f=1.2, pe_b=(0.14, 0))
    return p


def ataque_pesado(base, i):
    """Arma de duas mãos girando por cima da cabeça (machado, martelo)."""
    p = dict(base)
    q = base.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=-0.3, cabeca=-0.1, quadril=(q[0] - 0.05, q[1] + 0.02), braco_f=(-2.7, -0.3),
                 braco_b=(-2.6, -0.2), arma_f=-2.2, alvo_f=None, alvo_b=None)
    elif i == 1:
        p.update(tronco=0.25, cabeca=0.05, quadril=(q[0] + 0.08, q[1] + 0.06), braco_f=(2.2, 0.1),
                 braco_b=(2.1, 0.2), arma_f=0.9, alvo_f=None, alvo_b=None, pe_b=(0.2, 0))
    elif i == 2:
        p.update(tronco=0.55, cabeca=0.2, quadril=(q[0] + 0.1, q[1] + 0.12), braco_f=(1.1, 0.1),
                 braco_b=(1.0, 0.2), arma_f=2.2, alvo_f=None, alvo_b=None, pe_b=(0.22, 0), pe_f=(-0.14, 0))
    else:
        p.update(tronco=0.2, quadril=(q[0] + 0.04, q[1] + 0.04), braco_f=(0.6, 0.5), braco_b=(0.5, 0.6),
                 arma_f=1.4, alvo_f=None, alvo_b=None, pe_b=(0.12, 0))
    return p


def ataque_magia(base, i):
    """Ergue o cajado e projeta a mão de trás."""
    p = dict(base)
    q = base.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=-0.12, cabeca=-0.15, quadril=(q[0] - 0.02, q[1] + 0.01), braco_f=(2.6, 0.2), arma_f=0.1,
                 braco_b=(-0.6, 1.4))
    elif i == 1:
        p.update(tronco=0.22, cabeca=0.1, quadril=(q[0] + 0.05, q[1] + 0.03), braco_f=(2.2, 0.1), arma_f=0.4,
                 braco_b=(1.5, 0.05), pe_b=(0.16, 0))
    elif i == 2:
        p.update(tronco=0.26, cabeca=0.12, quadril=(q[0] + 0.06, q[1] + 0.04), braco_f=(2.0, 0.1), arma_f=0.5,
                 braco_b=(1.55, 0.0), pe_b=(0.17, 0))
    else:
        p.update(tronco=0.08, quadril=(q[0] + 0.02, q[1] + 0.01), braco_f=(0.9, 0.5), arma_f=0.2,
                 braco_b=(0.3, 0.5))
    return p


def ataque_garra(base, i):
    """Investida com garras (monstros sem arma)."""
    p = dict(base)
    q = base.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=-0.25, cabeca=0.1, quadril=(q[0] - 0.04, q[1] + 0.04), braco_f=(-2.3, -0.4),
                 braco_b=(-1.0, 0.5))
    elif i == 1:
        p.update(tronco=0.5, cabeca=0.2, quadril=(q[0] + 0.12, q[1] + 0.08), braco_f=(1.7, 0.1),
                 braco_b=(0.4, 0.6), pe_b=(0.24, 0), pe_f=(-0.12, 0))
    elif i == 2:
        p.update(tronco=0.6, cabeca=0.25, quadril=(q[0] + 0.13, q[1] + 0.1), braco_f=(0.6, 0.4),
                 braco_b=(1.6, 0.1), pe_b=(0.25, 0), pe_f=(-0.12, 0))
    else:
        p.update(tronco=0.25, quadril=(q[0] + 0.05, q[1] + 0.04), braco_f=(0.4, 0.5), braco_b=(0.2, 0.5),
                 pe_b=(0.12, 0))
    return p


def ataque_arco(base, i):
    p = dict(base)
    q = base.get("quadril", (0, 0))
    if i == 0:
        p.update(tronco=-0.05, braco_b=(1.55, 0.0), braco_f=(1.4, 1.4), arma_b=0.0, cabeca=0.05)
    elif i == 1:
        p.update(tronco=-0.1, braco_b=(1.6, 0.0), braco_f=(1.25, 2.1), arma_b=0.0, cabeca=0.05,
                 quadril=(q[0] - 0.02, q[1]))
    elif i == 2:
        p.update(tronco=-0.12, braco_b=(1.6, 0.0), braco_f=(0.6, 0.6), arma_b=-0.1, cabeca=0.0,
                 quadril=(q[0] - 0.03, q[1]))
    else:
        p.update(tronco=0.0, braco_b=(1.0, 0.3), braco_f=(0.3, 0.5), arma_b=0.1)
    return p


ESTILOS = {
    "corte": ataque_corte,
    "estocada": ataque_estocada,
    "pesado": ataque_pesado,
    "magia": ataque_magia,
    "garra": ataque_garra,
    "arco": ataque_arco,
}


# ============================================================
# FOLHA DE SPRITES
# ============================================================

class Ctx:
    """Informações do quadro que está sendo desenhado."""

    def __init__(self, anim, i, n, variante=None):
        self.anim = anim
        self.i = i
        self.n = n
        self.t = i / max(1, n)
        self.a = 2 * math.pi * i / max(1, n)
        self.v = variante or {}

    @property
    def golpe(self):
        return self.anim == "ataque" and self.i in (1, 2)

    @property
    def morto(self):
        return self.anim == "morte" and self.i == 3

    def __repr__(self):
        return f"Ctx({self.anim},{self.i})"


class Modelo:
    """Base para todos os personagens.

    Subclasses definem:
      - nome, H (altura em px), largura/altura da célula, âncora (pés)
      - pose(ctx) -> dict de pose (humanoides) ou qualquer coisa
      - desenhar(tela, ctx, pose)
    """
    nome = "modelo"
    H = 76
    larg = None
    alt = None
    ancora = None
    estilo = "corte"
    semente = 1
    borda_luz = (150, 130, 170)
    forca_borda = 0.25
    prop = None
    base = {}
    escala_jogo = 3
    geo_rapida = False      # True nas forjas novas (motor.Geo: máscaras recortadas, mais rápidas)
    animacoes_extras = ()   # linhas a mais no fim da folha, ex.: (("despertar", 4),) nas gárgulas
    armado = True           # False = folha "desarmada" do herói (a arma equipada vem numa camada por cima)
    adornos = ()            # peças de silhueta das roupas (personagens/adornos.py): atrás e na frente do herói

    def __init__(self, **variante):
        self.v = variante
        for k, val in variante.items():
            setattr(self, k, val)
        if self.larg is None:
            self.larg = int(self.H * 2.05)
        if self.alt is None:
            self.alt = int(self.H * 1.6)
        if self.ancora is None:
            self.ancora = (int(self.H * 1.08), self.alt - 4)

    # ----- poses padrão (humanoides) -----
    def pose_base(self):
        return dict(self.base)

    def pose(self, ctx):
        b = self.pose_base()
        if ctx.anim == "parado":
            return idle(b, ctx.i)
        if ctx.anim == "ataque":
            return ESTILOS[self.estilo](b, ctx.i)
        if ctx.anim == "dano":
            return dano(b, ctx.i)
        if ctx.anim == "sentado":
            return sentado(b, ctx.i)
        return morte(b, ctx.i)

    def esqueleto(self, pose):
        return esqueleto(self.H, self.ancora[0], self.ancora[1], pose, self.prop)

    def desenhar(self, tela, ctx, J):
        raise NotImplementedError

    def quadro(self, anim, i, n):
        ctx = Ctx(anim, i, n, self.v)
        tela = Tela(self.larg, self.alt, semente=self.semente + i, borda_luz=self.borda_luz,
                    forca_borda=self.forca_borda, geo_rapida=self.geo_rapida)
        p = self.pose(ctx)
        J = self.esqueleto(p) if isinstance(p, dict) else p
        for adorno in self.adornos:
            if adorno.atras:
                adorno(tela, ctx, J, self)
        self.desenhar(tela, ctx, J)
        for adorno in self.adornos:
            if not adorno.atras:
                adorno(tela, ctx, J, self)
        return tela.finalizar()

    def animacoes(self):
        """As linhas da folha: as de todos (ANIMACOES) e as extras deste modelo."""
        return ANIMACOES + list(self.animacoes_extras)

    def folha(self):
        quadros = {}
        for anim, n in self.animacoes():
            quadros[anim] = [self.quadro(anim, i, n) for i in range(n)]
        return quadros


def salvar_folha(modelo, pasta):
    """Monta a folha do modelo e grava <pasta>/<nome>.png. Devolve (meta do catálogo, quadros)."""
    folha, meta, quadros = montar_folha(modelo)
    os.makedirs(pasta, exist_ok=True)
    folha.save(os.path.join(pasta, modelo.nome + ".png"))
    return meta, quadros


def montar_folha(modelo):
    """A folha inteira só na memória (sem gravar): (imagem, meta do catálogo, quadros por animação)."""
    quadros = modelo.folha()
    W, Hc = modelo.larg, modelo.alt
    linhas = modelo.animacoes()
    colunas = max(n for _, n in linhas)
    folha = Image.new("RGBA", (W * colunas, Hc * len(linhas)), (0, 0, 0, 0))
    escala = 3 if modelo.H <= 96 else 2
    meta = {"nome": modelo.nome, "celula": [W, Hc], "ancora": list(modelo.ancora), "escala": escala,
            "animacoes": {}}
    for linha, (anim, n) in enumerate(linhas):
        for i, img in enumerate(quadros[anim]):
            folha.paste(img, (i * W, linha * Hc))
        meta["animacoes"][anim] = {"linha": linha, "quadros": n}
    return folha, meta, quadros
