"""Mixins de acabamento: reaproveitam um sprite pronto por herança e acrescentam camadas, sem
mexer na classe original.

    ComAcabamento   antes() desenha ATRÁS do corpo (vem primeiro, o corpo pinta por cima) e
                    acabar() desenha POR CIMA, depois do desenho original
    Corrompido      herói corrompido: o corpo escurece e perde a cor, veias que brilham, olhos
                    acesos, aura e fiapos de sombra; deformar() é o gancho de cada um

Uso (o mixin vem ANTES da classe original na herança):

    class CavaleiroCaido(Corrompido, Guerreiro):
        nome = "cavaleiro_caido"
        def deformar(self, tela, ctx, J): ...
"""
import numpy as np

from ..motor import misturar
from ..humanoide import quadro_cabeca
from .. import texturas as T
from .. import fx


class ComAcabamento:
    """Antes e depois do desenho original (método-modelo em volta do desenhar() herdado)."""

    def desenhar(self, tela, ctx, J):
        self.antes(tela, ctx, J)
        super().desenhar(tela, ctx, J)
        self.acabar(tela, ctx, J)

    def antes(self, tela, ctx, J):
        """Camadas de trás (capas, asas, auras)."""

    def acabar(self, tela, ctx, J):
        """Camadas da frente (sangue, runas, olhos, efeitos)."""

    @staticmethod
    def vivo(ctx):
        return not (ctx.anim == "morte" and ctx.i >= 2)


def olhos_humanoides(J):
    """Posições dos dois olhos numa cabeça humana do esqueleto padrão (o de lá e o de cá)."""
    C = quadro_cabeca(J)
    h = J["P"]["cabeca"]
    w = h * 0.82
    return [C.pt(w * 0.28, h * 0.08), C.pt(w * 0.5, h * 0.06)]


def escurecer_e_dessaturar(tela, quanto, tom=None, forca_tom=0.1):
    """Tira a cor e escurece tudo o que já foi pintado (menos o que emite luz)."""
    corpo = (tela.alfa > 0) & ~tela.emite
    ys, xs = np.nonzero(corpo)
    cor = tela.cor[ys, xs]
    cinza = cor.mean(-1, keepdims=True)
    nova = (cor * (1 - quanto) + cinza * quanto) * (1 - quanto * 0.45)
    if tom is not None:
        nova = nova * (1 - forca_tom) + np.array(tom, np.float32) * forca_tom
    tela.cor[ys, xs] = np.clip(nova, 0, 255)
    return corpo


class Corrompido(ComAcabamento):
    """Corrupção de um herói (os nomeados). As subclasses escolhem cores e desenham deformar()."""

    cor_corrupcao = (170, 60, 220)
    cor_olhos = (255, 40, 40)
    sombrio = 0.35
    veias = 5
    aura_raio = 4
    fiapos = (40, 20, 50)

    def acabar(self, tela, ctx, J):
        H = self.H
        vivo = self.vivo(ctx)
        corpo = escurecer_e_dessaturar(tela, self.sombrio, self.cor_corrupcao)
        if self.veias:
            T.rachaduras(tela, corpo, J["cintura"], area=(H * 0.1, H * 0.24), n=self.veias, passos=3, cor=self.cor_corrupcao,
                         emite=vivo, brilho=0.25 if vivo else 0.0, semente=getattr(self, "semente", 1))
        self.deformar(tela, ctx, J)
        if vivo:
            for p in olhos_humanoides(J) if self.cor_olhos is not None else []:
                tela.px(p[0], p[1], self.cor_olhos, emite=True)
                tela.brilho(p, 3.5, self.cor_olhos, 0.7)
            T.aura(tela, tela.alfa > 0, self.cor_corrupcao, raio=self.aura_raio, forca=0.35, fase=ctx.a)
            T.particulas(tela, J["peito"], (H * 0.25, H * 0.3), misturar(self.cor_corrupcao, self.fiapos, 0.4), n=7,
                         fase=ctx.a, sobe=H * 0.3, semente=5)
        elif ctx.i >= 2:
            fx.fumaca(tela, J["peito"], H * 0.08, cor=self.fiapos, fase=ctx.a, n=5, sobe=12)

    def deformar(self, tela, ctx, J):
        """Chifres, máscara, rachaduras... de cada corrompido."""
