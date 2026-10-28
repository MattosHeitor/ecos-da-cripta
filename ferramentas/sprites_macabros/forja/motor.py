"""Motor de pixel art procedural.

Tudo é desenhado em baixa resolução (1 pixel = 1 pixel do sprite) numa
"tela" numpy. Cada parte do corpo é uma máscara que recebe sombreamento
volumétrico automático (como se fosse uma peça esculpida iluminada de cima),
quantizado numa rampa de cores com hue-shift (sombras puxando para roxo /
azul, luzes puxando para amarelo), no estilo de jogos como Blasphemous e
Castlevania.
"""
import colorsys
import math
import random

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

# Luz principal: vem de cima, um pouco da frente/direita (personagem olha p/ direita)
LUZ = np.array([0.42, -0.78, 0.62])
LUZ = LUZ / np.linalg.norm(LUZ)

# Cor do contorno externo (quase preto, puxado pro roxo)
CONTORNO = (14, 8, 18)

BAYER4 = (np.array([[0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5]]) / 16.0) - 0.47

SS = 4  # supersampling das máscaras


# ============================================================
# CORES
# ============================================================

def rgb(cor):
    if isinstance(cor, str):
        cor = cor.lstrip("#")
        return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(c) for c in cor[:3])


def misturar(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def escurecer(cor, f=0.6):
    return tuple(int(c * f) for c in rgb(cor))


def _hue_para(h, alvo, t):
    d = (alvo - h + 0.5) % 1.0 - 0.5
    return (h + d * t) % 1.0


def rampa(base, n=6, contraste=1.0, sombra_hue=0.74, luz_hue=0.11, shift=1.0, satur=1.0, topo=None):
    """Gera n cores do escuro ao claro a partir de uma cor base.

    A cor base fica mais ou menos no índice 60%.
    """
    r, g, b = [c / 255 for c in rgb(base)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    lmin = max(0.025, l * (1 - 0.78 * contraste))
    lmax = min(0.93, l + (1 - l) * 0.55 * contraste * min(1.0, 0.25 + l * 2.2)) if topo is None else topo
    cores = []
    for i in range(n):
        t = i / (n - 1)
        # curva: mais tons escuros (clima sombrio)
        tl = t ** 1.15
        li = lmin + (lmax - lmin) * tl
        hi = h
        if t < 0.6:
            hi = _hue_para(h, sombra_hue, 0.22 * shift * ((0.6 - t) / 0.6) ** 1.2)
        else:
            hi = _hue_para(h, luz_hue, 0.10 * shift * ((t - 0.6) / 0.4) ** 1.5)
        si = s * satur * (0.72 + 0.4 * math.sin(math.pi * min(1, t * 1.1)))
        if t > 0.85:
            si *= 0.85
        si = max(0, min(1, si))
        rr, gg, bb = colorsys.hls_to_rgb(hi, li, si)
        cores.append((int(rr * 255), int(gg * 255), int(bb * 255)))
    return cores


class Mat:
    """Material: rampa de cores + como ele reage à luz."""

    def __init__(self, base=None, n=6, rampa_cores=None, relevo=1.0, arredonda=1.0, ruido=0.0,
                 dither=0.35, nivel=0.0, especular=None, contraste=1.0, desce=0.0, linha=None,
                 semente=0, **kw_rampa):
        self.cores = list(rampa_cores) if rampa_cores else rampa(base, n, contraste=contraste, **kw_rampa)
        self.relevo = relevo
        self.arredonda = arredonda
        self.ruido = ruido
        self.dither = dither
        self.nivel = nivel          # desloca o tom todo (+ mais claro)
        self.especular = especular  # cor do brilho especular (metais)
        self.desce = desce          # escurece para baixo (mantos)
        self.linha = linha          # cor da linha interna
        self.semente = semente

    def copia(self, **kw):
        m = Mat.__new__(Mat)
        m.__dict__.update(self.__dict__)
        m.cores = list(self.cores)
        for k, v in kw.items():
            setattr(m, k, v)
        return m

    def escuro(self, k=1):
        """Mesma rampa deslocada para baixo (membros do lado de trás)."""
        n = len(self.cores)
        cores = [self.cores[max(0, i - k)] for i in range(n)]
        return self.copia(cores=cores, especular=None if k > 1 else self.especular)

    def claro(self, k=1):
        n = len(self.cores)
        cores = [self.cores[min(n - 1, i + k)] for i in range(n)]
        return self.copia(cores=cores)

    @property
    def cor_linha(self):
        if self.linha is not None:
            return rgb(self.linha)
        return misturar(self.cores[0], CONTORNO, 0.25)

    def __getitem__(self, i):
        return self.cores[max(0, min(len(self.cores) - 1, i))]


def metal(base, n=7, **kw):
    kw.setdefault("contraste", 1.25)
    kw.setdefault("relevo", 1.6)
    kw.setdefault("dither", 0.15)
    esp = kw.pop("especular", misturar(base, (255, 250, 235), 0.85))
    return Mat(base, n, especular=esp, **kw)


# ============================================================
# MÁSCARAS (geometria)
# ============================================================

class Geo:
    """Máscaras com supersampling.

    rapida=True desenha cada forma só no retângulo que ela ocupa (bem mais rápido em telas
    grandes). O PIL pode arredondar diferente alguns pixels de borda, então os sprites antigos
    usam rapida=False e saem idênticos ao que sempre foram; as forjas novas usam True.
    """

    MARGEM = 2

    def __init__(self, w, h, rapida=False):
        self.w, self.h = w, h
        self.rapida = rapida
        self._x0 = self._y0 = 0           # origem do recorte atual (em pixels)

    def _recorte(self, x_min, y_min, x_max, y_max):
        """Retângulo inteiro (x0, y0, x1, y1) dentro da tela, ou None se a forma está fora dela."""
        if not self.rapida:
            return 0, 0, self.w, self.h
        m = self.MARGEM
        x0, y0 = max(0, int(math.floor(x_min)) - m), max(0, int(math.floor(y_min)) - m)
        x1, y1 = min(self.w, int(math.ceil(x_max)) + m + 1), min(self.h, int(math.ceil(y_max)) + m + 1)
        if x0 >= x1 or y0 >= y1:
            return None
        return x0, y0, x1, y1

    def _desenhar(self, caixa, desenho, limiar):
        """Roda desenho(draw) numa imagem do tamanho da caixa e devolve a máscara da tela inteira."""
        mask = np.zeros((self.h, self.w), bool)
        if caixa is None:
            return mask
        x0, y0, x1, y1 = caixa
        self._x0, self._y0 = x0, y0
        img = Image.new("L", ((x1 - x0) * SS, (y1 - y0) * SS), 0)
        desenho(ImageDraw.Draw(img))
        self._x0 = self._y0 = 0
        a = np.asarray(img, dtype=np.float32) / 255.0
        a = a.reshape(y1 - y0, SS, x1 - x0, SS).mean(axis=(1, 3))
        mask[y0:y1, x0:x1] = a >= limiar
        return mask

    def _s(self, p):
        # (+ SS/2 - 0.5*SS) parece inútil, mas muda o arredondamento: mantém os sprites antigos idênticos
        return ((p[0] - self._x0) * SS + SS / 2 - 0.5 * SS, (p[1] - self._y0) * SS + SS / 2 - 0.5 * SS)

    def poly(self, pts, limiar=0.5):
        if len(pts) < 3:
            return np.zeros((self.h, self.w), bool)
        xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
        caixa = self._recorte(min(xs), min(ys), max(xs), max(ys))
        return self._desenhar(caixa, lambda d: d.polygon([self._s(p) for p in pts], fill=255), limiar)

    def elipse(self, cx, cy, rx, ry, limiar=0.5):
        caixa = self._recorte(cx - rx, cy - ry, cx + rx, cy + ry)

        def desenho(d):
            c = self._s((cx, cy))
            d.ellipse([c[0] - rx * SS, c[1] - ry * SS, c[0] + rx * SS, c[1] + ry * SS], fill=255)
        return self._desenhar(caixa, desenho, limiar)

    def circulo(self, c, r, limiar=0.5):
        return self.elipse(c[0], c[1], r, r, limiar)

    def elipse_girada(self, c, rx, ry, ang, limiar=0.5, lados=28):
        pts = []
        ca, sa = math.cos(ang), math.sin(ang)
        for i in range(lados):
            t = 2 * math.pi * i / lados
            x, y = math.cos(t) * rx, math.sin(t) * ry
            pts.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
        return self.poly(pts, limiar)

    def capsula(self, a, b, r1, r2=None, limiar=0.5):
        """Segmento com pontas arredondadas e espessura variável (membros)."""
        if r2 is None:
            r2 = r1
        r = max(r1, r2)
        caixa = self._recorte(min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r)

        def desenho(d):
            a2, b2 = self._s(a), self._s(b)
            dx, dy = b2[0] - a2[0], b2[1] - a2[1]
            L = math.hypot(dx, dy) or 1e-6
            px, py = -dy / L, dx / L
            R1, R2 = r1 * SS, r2 * SS
            d.polygon([(a2[0] + px * R1, a2[1] + py * R1), (b2[0] + px * R2, b2[1] + py * R2),
                       (b2[0] - px * R2, b2[1] - py * R2), (a2[0] - px * R1, a2[1] - py * R1)], fill=255)
            d.ellipse([a2[0] - R1, a2[1] - R1, a2[0] + R1, a2[1] + R1], fill=255)
            d.ellipse([b2[0] - R2, b2[1] - R2, b2[0] + R2, b2[1] + R2], fill=255)
        return self._desenhar(caixa, desenho, limiar)

    def corrente(self, pts, larguras, limiar=0.5):
        """Várias cápsulas em sequência (caudas, tentáculos, patas)."""
        m = np.zeros((self.h, self.w), bool)
        if not isinstance(larguras, (list, tuple)):
            larguras = [larguras] * len(pts)
        for i in range(len(pts) - 1):
            m |= self.capsula(pts[i], pts[i + 1], larguras[i], larguras[i + 1], limiar)
        return m

    def linha_fina(self, a, b):
        """Linha de 1 pixel (Bresenham)."""
        m = np.zeros((self.h, self.w), bool)
        for x, y in bresenham(a, b):
            if 0 <= x < self.w and 0 <= y < self.h:
                m[y, x] = True
        return m

    def casco(self, pts, limiar=0.5):
        """Envoltória convexa de pontos (mantos, vestidos)."""
        return self.poly(envoltoria(pts), limiar)


def desloca(a, dy, dx):
    """Desloca um array 2D/3D sem dar a volta nas bordas (preenche com zero)."""
    r = np.zeros_like(a)
    h, w = a.shape[:2]
    ys = slice(max(0, dy), h + min(0, dy))
    yd = slice(max(0, -dy), h + min(0, -dy))
    xs = slice(max(0, dx), w + min(0, dx))
    xd = slice(max(0, -dx), w + min(0, -dx))
    r[ys, xs] = a[yd, xd]
    return r


def bresenham(a, b):
    x0, y0 = int(round(a[0])), int(round(a[1]))
    x1, y1 = int(round(b[0])), int(round(b[1]))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


def envoltoria(pts):
    pts = sorted(set((float(p[0]), float(p[1])) for p in pts))
    if len(pts) <= 2:
        return pts

    def cruz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    baixo, cima = [], []
    for p in pts:
        while len(baixo) >= 2 and cruz(baixo[-2], baixo[-1], p) <= 0:
            baixo.pop()
        baixo.append(p)
    for p in reversed(pts):
        while len(cima) >= 2 and cruz(cima[-2], cima[-1], p) <= 0:
            cima.pop()
        cima.append(p)
    return baixo[:-1] + cima[:-1]


# ============================================================
# TELA
# ============================================================

class Tela:
    def __init__(self, w, h, semente=0, borda_luz=(150, 130, 170), forca_borda=0.28, geo_rapida=False):
        self.w, self.h = w, h
        self.geo = Geo(w, h, geo_rapida)
        self.cor = np.zeros((h, w, 3), np.float32)
        self.alfa = np.zeros((h, w), np.uint8)
        self.parte = np.zeros((h, w), np.int32)
        self.emite = np.zeros((h, w), bool)
        self.luz_extra = np.zeros((h, w, 3), np.float32)   # brilhos aditivos
        self.halo = np.zeros((h, w, 4), np.float32)        # halo fora do sprite
        self.prox = 1
        self.rng = np.random.default_rng(semente)
        self.random = random.Random(semente)
        self.borda_luz = borda_luz
        self.forca_borda = forca_borda
        self.contorno_alfa = 255          # contorno semitransparente (espectros)
        self.contorno_cor = None          # cor própria do contorno (None = o quase-preto padrão)
        yy, xx = np.mgrid[0:h, 0:w]
        self.bayer = BAYER4[yy % 4, xx % 4]
        self.ruido_base = self.rng.random((h, w)).astype(np.float32) - 0.5

    # ---------- geometria rápida ----------
    def __getattr__(self, nome):
        # atalhos: tela.poly(...) -> tela.geo.poly(...)
        geo = self.__dict__.get("geo")
        if geo is not None and hasattr(geo, nome):
            return getattr(geo, nome)
        raise AttributeError(nome)

    # ---------- pintura com sombreamento ----------
    def pintar(self, mask, mat, linha_interna=True, luz=None, recorte=None, sobre=None, nivel=0.0,
               plano=False, contorno_proprio=False):
        """Pinta uma máscara com sombreamento volumétrico.

        - linha_interna: desenha linha escura onde esta parte encosta em outra já pintada.
        - recorte: máscara que limita onde pintar (ex.: só por cima do corpo).
        - sobre: se True, só pinta onde já existe algo.
        - plano: sem volume (só gradiente de cima pra baixo).
        """
        mask = np.asarray(mask, bool)
        if recorte is not None:
            mask = mask & recorte
        if sobre:
            mask = mask & (self.alfa > 0)
        if not mask.any():
            return mask
        # trabalha só no retângulo da peça (+ folga do filtro); fora dele nada muda
        linhas, colunas = np.nonzero(mask.any(axis=1))[0], np.nonzero(mask.any(axis=0))[0]
        janela = (slice(max(0, linhas[0] - 5), min(self.h, linhas[-1] + 6)),
                  slice(max(0, colunas[0] - 5), min(self.w, colunas[-1] + 6)))
        mask_total, mask = mask, mask[janela]
        L = LUZ if luz is None else luz / np.linalg.norm(luz)
        cores = np.array(mat.cores, np.float32)
        n = len(cores)

        if plano:
            v = np.full(mask.shape, 0.6, np.float32)
        else:
            d = ndimage.distance_transform_edt(mask)
            m = d.max()
            cap = max(1.0, m * mat.arredonda)
            x = np.minimum(d, cap) / cap
            hgt = cap * np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1)) * mat.relevo
            hgt = ndimage.gaussian_filter(hgt, 0.7)
            gy, gx = np.gradient(hgt)
            nx, ny, nz = -gx, -gy, np.ones_like(gx)
            norma = np.sqrt(nx * nx + ny * ny + nz * nz)
            v = (nx * L[0] + ny * L[1] + nz * L[2]) / norma
            v = 0.58 + (v - L[2]) * 1.05

        if mat.desce:
            ys = np.where(mask.any(axis=1))[0]
            y0, y1 = ys.min(), max(ys.max(), ys.min() + 1)
            yy = np.arange(mask.shape[0], dtype=np.float32)[:, None]
            v = v - np.clip((yy - y0) / (y1 - y0), 0, 1) * mat.desce
        if mat.ruido:
            v = v + self.ruido_base[janela] * mat.ruido
        v = v + mat.nivel + nivel
        idx = np.floor(v * (n - 1) + 0.5 + self.bayer[janela] * mat.dither)
        idx = np.clip(idx, 0, n - 1).astype(int)
        out = cores[idx]
        if mat.especular is not None:
            esp = (v > 0.97) & mask
            out[esp] = np.array(rgb(mat.especular), np.float32)

        if linha_interna:
            borda = mask & ~ndimage.binary_erosion(mask)
            ja = self.alfa[janela] > 0
            viz = np.zeros_like(mask)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                viz |= desloca(ja & ~mask, dy, dx)
            linha = borda & viz
            out[linha] = np.array(mat.cor_linha, np.float32)

        if contorno_proprio:
            borda = mask & ~ndimage.binary_erosion(mask)
            out[borda] = np.array(mat.cor_linha, np.float32)

        self.cor[janela][mask] = out[mask]
        self.alfa[janela][mask] = 255
        self.parte[janela][mask] = self.prox
        self.emite[janela][mask] = False
        self.prox += 1
        return mask_total

    def vidro(self, mask, mat, opacidade=0.6, **kw):
        """Pinta com sombreamento, mas translúcido: mistura com o que já está atrás e,
        sobre o vazio, deixa o pixel semitransparente (gelo, cristal, espectros)."""
        mask = np.asarray(mask, bool)
        cor_antes, alfa_antes = self.cor.copy(), self.alfa.copy()
        mask = self.pintar(mask, mat, **kw)
        atras = mask & (alfa_antes > 0)
        self.cor[atras] = cor_antes[atras] * (1 - opacidade) + self.cor[atras] * opacidade
        vazio = mask & (alfa_antes == 0)
        self.alfa[vazio] = int(255 * opacidade)
        return mask

    def chapado(self, mask, cor, emite=False, alfa=255):
        """Pinta cor única, sem sombreamento (detalhes, olhos, sangue)."""
        mask = np.asarray(mask, bool)
        if alfa < 255:
            t = alfa / 255
            ja = self.alfa > 0
            m1 = mask & ja
            self.cor[m1] = self.cor[m1] * (1 - t) + np.array(rgb(cor), np.float32) * t
            return mask
        self.cor[mask] = np.array(rgb(cor), np.float32)
        self.alfa[mask] = 255
        self.emite[mask] = emite
        return mask

    def px(self, x, y, cor, emite=False):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cor[y, x] = rgb(cor)
            self.alfa[y, x] = 255
            self.emite[y, x] = emite

    def traco(self, a, b, cor, emite=False, sobre=False):
        for x, y in bresenham(a, b):
            if 0 <= x < self.w and 0 <= y < self.h:
                if sobre and self.alfa[y, x] == 0:
                    continue
                self.cor[y, x] = rgb(cor)
                self.alfa[y, x] = 255
                self.emite[y, x] = emite

    def tracos(self, pts, cor, emite=False, sobre=False):
        for i in range(len(pts) - 1):
            self.traco(pts[i], pts[i + 1], cor, emite, sobre)

    def escurecer_area(self, mask, f=0.6):
        mask = np.asarray(mask, bool) & (self.alfa > 0)
        self.cor[mask] *= f

    def tingir(self, mask, cor, t=0.5):
        mask = np.asarray(mask, bool) & (self.alfa > 0)
        self.cor[mask] = self.cor[mask] * (1 - t) + np.array(rgb(cor), np.float32) * t

    def brilho(self, c, raio, cor, forca=1.0, halo=True):
        """Luz emitida: clareia o que está perto e cria halo transparente."""
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        d = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / max(raio, 0.5)
        f = np.clip(1 - d, 0, 1) ** 1.6 * forca
        self.luz_extra += f[..., None] * np.array(rgb(cor), np.float32)[None, None, :] * 0.55
        if halo:
            a = self.halo
            a[..., :3] += f[..., None] * np.array(rgb(cor), np.float32)
            a[..., 3] += f

    def mascara(self):
        return self.alfa > 0

    # ---------- final ----------
    def finalizar(self, contorno=True, borda=True):
        cheio = self.alfa > 0
        cor = self.cor.copy()

        # luz de borda (contra-luz) no lado de trás (esquerda) e no topo
        if borda and self.forca_borda > 0:
            esq = cheio & ~desloca(cheio, 0, 1)
            topo = cheio & ~desloca(cheio, 1, 0)
            rim = (esq | (topo & ~desloca(cheio, 0, -1))) & ~self.emite
            t = self.forca_borda
            cor[rim] = cor[rim] * (1 - t) + np.array(self.borda_luz, np.float32) * t

        # brilhos aditivos
        luz = self.luz_extra
        cor = np.where(cheio[..., None] & ~self.emite[..., None], cor + luz * 0.9, cor)

        rgba = np.zeros((self.h, self.w, 4), np.float32)
        rgba[..., :3] = np.clip(cor, 0, 255)
        rgba[..., 3] = self.alfa

        if contorno:
            viz = np.zeros_like(cheio)
            soma = np.zeros((self.h, self.w, 3), np.float32)
            cont = np.zeros((self.h, self.w), np.float32)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                s = desloca(cheio, dy, dx)
                viz |= s
                c = desloca(rgba[..., :3], dy, dx)
                soma += c * s[..., None]
                cont += s
            fora = viz & ~cheio
            media = soma / np.maximum(cont, 1)[..., None]
            oc = np.array(CONTORNO if self.contorno_cor is None else self.contorno_cor, np.float32)
            c_out = oc * 0.82 + media * 0.18
            # partes que emitem luz ganham contorno colorido
            rgba[fora, :3] = c_out[fora]
            rgba[fora, 3] = self.contorno_alfa

        # halo transparente fora do sprite
        h = self.halo
        forca = np.clip(h[..., 3], 0, 1)
        vazio = rgba[..., 3] == 0
        tem = vazio & (forca > 0.08)
        if tem.any():
            corh = h[..., :3] / np.maximum(h[..., 3], 1e-5)[..., None]
            niveis = np.where(forca > 0.55, 150, np.where(forca > 0.28, 95, 50))
            # dither no anel mais externo
            niveis = np.where((forca <= 0.18) & (self.bayer > 0.1), 0, niveis)
            rgba[tem, :3] = corh[tem]
            rgba[tem, 3] = niveis[tem]

        return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


# ============================================================
# GEOMETRIA 2D
# ============================================================

def v2(x, y=None):
    if y is None:
        return np.array(x, dtype=float)
    return np.array([x, y], dtype=float)


def girar(p, ang, centro=(0, 0)):
    c = np.array(centro, float)
    p = np.array(p, float) - c
    ca, sa = math.cos(ang), math.sin(ang)
    return np.array([p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca]) + c


def norm(v):
    v = np.array(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def perp(v):
    """Perpendicular (gira 90° no sentido horário na tela)."""
    return np.array([-v[1], v[0]], float)


def lerp(a, b, t):
    return np.array(a, float) + (np.array(b, float) - np.array(a, float)) * t


def dir_ang(a):
    """Direção a partir de ângulo: 0 = para cima, positivo gira para a direita."""
    return np.array([math.sin(a), -math.cos(a)])


class Quadro:
    """Sistema de coordenadas local: origem + eixo 'cima'. x local = frente."""

    def __init__(self, origem, cima):
        self.o = np.array(origem, float)
        self.u = norm(cima)
        self.f = np.array([-self.u[1], self.u[0]])  # frente (direita quando em pé)
        # quando u = (0,-1) => f = (1, 0)

    def pt(self, x, y):
        """x = para frente, y = para cima (em pixels)."""
        return self.o + self.f * x + self.u * y

    def pts(self, lista):
        return [self.pt(x, y) for x, y in lista]
