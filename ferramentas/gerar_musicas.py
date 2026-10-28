"""Compõe as músicas do jogo por código (síntese com numpy/scipy) em assets/sons/musica/<nome>.wav.

    python ferramentas/gerar_musicas.py               # todas
    python ferramentas/gerar_musicas.py floresta chefe

Cada música é uma "partitura" curta escrita em Python: acordes, uma melodia sorteada pela escala
(sempre a mesma, a semente é fixa) e instrumentos sintetizados:

    flauta      seno com vibrato e ar soprando           timpano     tambor afinado que cai de tom
    cravo       corda beliscada brilhante + oitava       metais      naipe de dente-de-serra filtrado
    tremolo     (efeito) o volume das cordas pulsando rápido
    alaude      corda dedilhada (Karplus-Strong)        coro        vozes "aah" (formantes)
    orgao       tubos com harmônicos e tremolo           sino        metal desafinado que some aos poucos
    caixinha    caixinha de música (seno agudo)          baixo       seno grave
    tambor      bumbo de guerra                          caixa       ruído curto (caixa/chocalho)
    vento       ruído filtrado subindo e descendo        crepitar    estalos de fogueira

Depois vem um reverb (salão de pedra) e o loop é emendado sem estalo: a "cauda" do fim é somada ao
começo. Vitória e derrota são vinhetas curtas (tocam uma vez). Para trocar por música de verdade,
ponha um .ogg/.mp3 com o MESMO nome na pasta (o jogo prefere .ogg).
"""

import os
import sys
import wave

import numpy as np
from scipy.signal import lfilter, butter

TAXA = 22050
VOLUME_MEDIO = 0.2
PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sons", "musica")


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def tempo(segundos):
    return np.arange(int(TAXA * segundos)) / TAXA


def envelope(n, ataque, soltura):
    env = np.ones(n)
    a, s = min(n, max(1, int(TAXA * ataque))), min(n, max(1, int(TAXA * soltura)))
    env[:a] = np.linspace(0, 1, a)
    env[-s:] *= np.linspace(1, 0, s)
    return env


def passa_baixa(sinal, corte):
    b, a = butter(2, min(0.99, corte / (TAXA / 2)))
    return lfilter(b, a, sinal)


def passa_faixa(sinal, centro, largura):
    baixo, alto = max(20, centro - largura / 2), min(TAXA / 2 - 50, centro + largura / 2)
    b, a = butter(2, [baixo / (TAXA / 2), alto / (TAXA / 2)], btype="band")
    return lfilter(b, a, sinal)


# ============================================================
# INSTRUMENTOS (cada um devolve um array com o som de UMA nota)
# ============================================================

def alaude(midi, duracao, brilho=0.5, rng=None):
    """Corda dedilhada (Karplus-Strong): um ruído curto passando num laço com atraso que vai abafando."""
    rng = rng or np.random.default_rng(int(midi * 7))
    n = int(TAXA * (duracao + 0.6))
    atraso = max(2, int(round(TAXA / hz(midi))))
    excitacao = np.zeros(n)
    excitacao[:atraso] = passa_baixa(rng.uniform(-1, 1, atraso), 1500 + 5000 * brilho)
    perda = 0.996 - 0.004 * (1 - brilho)
    a = np.zeros(atraso + 2)
    a[0] = 1
    a[atraso] = -0.5 * perda
    a[atraso + 1] = -0.5 * perda
    som = lfilter([1.0], a, excitacao)
    return som * envelope(n, 0.002, 0.25)


def sino(midi, duracao, velocidade=3.0):
    t = tempo(duracao + 1.5)
    f = hz(midi)
    parciais = ((1, 1.0), (2.01, 0.5), (2.76, 0.35), (5.4, 0.2), (8.93, 0.08))
    som = sum(peso * np.sin(2 * np.pi * f * k * t) * np.exp(-t * velocidade * (1 + k * 0.4)) for k, peso in parciais)
    return som * envelope(len(t), 0.003, 0.3)


def caixinha(midi, duracao):
    """Caixinha de música: seno agudo com um pouco de terceiro harmônico, levemente desafinado."""
    t = tempo(duracao + 0.8)
    f = hz(midi) * (1 + 0.004 * np.sin(midi))
    som = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 3 * t)) * np.exp(-t * 4.5)
    return som * envelope(len(t), 0.002, 0.2)


def baixo(midi, duracao):
    t = tempo(duracao)
    f = hz(midi)
    som = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t) + 0.1 * np.sin(2 * np.pi * f * 3 * t)
    return som * envelope(len(t), 0.02, min(0.3, duracao * 0.4))


def serra(f, t, harmonicos=10):
    """Onda dente-de-serra suave (soma de harmônicos, sem chiado)."""
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harmonicos + 1) if f * k < TAXA / 2.2)


def pad(midis, duracao, ataque=1.2, soltura=1.5, corte=1400):
    """Acorde longo de cordas/sintetizador, com vozes um pouco desafinadas (dá corpo)."""
    t = tempo(duracao + soltura)
    som = np.zeros(len(t))
    for m in midis:
        for desafino in (-0.003, 0.0, 0.003):
            som += serra(hz(m) * (1 + desafino), t, 6)
    som = passa_baixa(som, corte)
    return som * envelope(len(t), ataque, soltura) / max(1, len(midis))


def orgao(midis, duracao, soltura=0.8):
    t = tempo(duracao + soltura)
    tremolo = 1 + 0.08 * np.sin(2 * np.pi * 5.5 * t)
    som = np.zeros(len(t))
    for m in midis:
        f = hz(m)
        for k, peso in ((1, 1.0), (2, 0.6), (3, 0.35), (4, 0.3), (6, 0.15), (8, 0.12)):
            if f * k < TAXA / 2.2:
                som += peso * np.sin(2 * np.pi * f * k * t)
    return som * tremolo * envelope(len(t), 0.15, soltura) / max(1, len(midis))


def coro(midis, duracao, vogal="a"):
    """Vozes: dente-de-serra com vibrato, passando por filtros nos formantes da vogal."""
    formantes = {"a": ((700, 130), (1150, 160), (2600, 250)), "o": ((450, 100), (800, 120), (2830, 250)),
                 "u": ((325, 80), (700, 100), (2530, 200))}[vogal]
    t = tempo(duracao + 1.2)
    vibrato = 1 + 0.006 * np.sin(2 * np.pi * 5 * t)
    fonte = np.zeros(len(t))
    for m in midis:
        for desafino in (-0.004, 0.004):
            fase = np.cumsum(hz(m) * (1 + desafino) * vibrato) / TAXA
            fonte += sum(np.sin(2 * np.pi * fase * k) / k for k in range(1, 14) if hz(m) * k < TAXA / 2.2)
    som = sum(passa_faixa(fonte, centro, largura) * (1.0 / (i + 1)) for i, (centro, largura) in enumerate(formantes))
    return som * envelope(len(t), 0.6, 1.2) / max(1, len(midis))


def tambor(duracao=0.6, forca=1.0, rng=None):
    rng = rng or np.random.default_rng(3)
    t = tempo(duracao)
    freq = 45 + 75 * np.exp(-t * 18)
    corpo = np.sin(2 * np.pi * np.cumsum(freq) / TAXA) * np.exp(-t * 6)
    batida = passa_baixa(rng.uniform(-1, 1, len(t)), 900) * np.exp(-t * 40) * 0.6
    return (corpo + batida) * forca


def caixa(duracao=0.18, centro=2200, rng=None):
    rng = rng or np.random.default_rng(5)
    t = tempo(duracao)
    return passa_faixa(rng.uniform(-1, 1, len(t)), centro, centro * 0.8) * np.exp(-t * 25) * 1.6


def vento(segundos, rng, forca=1.0):
    """Ruído filtrado com o volume subindo e descendo (rajadas)."""
    t = tempo(segundos)
    ruido = passa_baixa(rng.uniform(-1, 1, len(t)), 500)
    ruido = ruido - passa_baixa(ruido, 120)
    rajadas = 0.5 + 0.5 * np.sin(2 * np.pi * t / 7.3) * np.sin(2 * np.pi * t / 3.1 + 1)
    return ruido * rajadas * forca * 3


def crepitar(segundos, rng, densidade=6.0):
    """Estalos curtos e aleatórios (lenha queimando)."""
    n = int(TAXA * segundos)
    som = np.zeros(n)
    for _ in range(int(segundos * densidade)):
        inicio = rng.integers(0, n - 400)
        estalo = rng.uniform(-1, 1, 300) * np.exp(-np.arange(300) / 40)
        som[inicio:inicio + 300] += passa_faixa(estalo, rng.uniform(1500, 4000), 1500) * rng.uniform(0.3, 1.0)
    return som


# ============================================================
# REVERB E PARTITURA
# ============================================================

def flauta(midi, duracao, vibrato=5.0, sopro=0.25):
    """Flauta: seno com vibrato que cresce, um pouco de 2º harmônico e o ar soprando (ruído filtrado)."""
    t = tempo(duracao + 0.3)
    profundidade = np.clip(t / max(0.01, duracao * 0.5), 0, 1) * 0.006
    fase = 2 * np.pi * np.cumsum(hz(midi) * (1 + profundidade * np.sin(2 * np.pi * vibrato * t))) / TAXA
    som = np.sin(fase) + 0.18 * np.sin(2 * fase)
    ar = passa_faixa(np.random.default_rng(int(midi)).uniform(-1, 1, len(t)), hz(midi) * 2, hz(midi) * 1.5)
    return (som + ar * sopro) * envelope(len(t), 0.08, 0.35)


def timpano(midi, duracao=1.2, forca=1.0):
    """Tímpano afinado: seno grave que cai um pouco de tom, com o 'tum' do couro e um ronco que some."""
    t = tempo(duracao)
    f = hz(midi) * (1 + 0.04 * np.exp(-t * 18))
    corpo = np.sin(2 * np.pi * np.cumsum(f) / TAXA) * np.exp(-t * 2.2)
    batida = passa_baixa(np.random.default_rng(int(midi * 3)).uniform(-1, 1, len(t)), 400) * np.exp(-t * 30)
    return (corpo + batida * 0.8) * forca


def cravo(midi, duracao, rng=None):
    """Cravo: corda beliscada bem brilhante, com a oitava de cima junto."""
    return alaude(midi, duracao, 0.95, rng) + 0.35 * alaude(midi + 12, duracao, 0.9, rng)


def tremolo(som, velocidade=7.0, profundidade=0.6):
    """Tremolo (arco de cordas tremendo): o volume pulsa rápido."""
    t = np.arange(len(som)) / TAXA
    return som * (1 - profundidade * 0.5 * (1 + np.sin(2 * np.pi * velocidade * t)))


def reverb(sinal, tamanho=1.0, mistura=0.3):
    """Reverb de Schroeder: 4 pentes em paralelo e 2 passa-tudo em série."""
    molhado = np.zeros(len(sinal))
    for atraso, ganho in ((1116, 0.84), (1188, 0.83), (1277, 0.82), (1356, 0.81)):
        d = int(atraso * tamanho * TAXA / 44100)
        a = np.zeros(d + 1)
        a[0], a[d] = 1, -ganho
        molhado += lfilter([1.0], a, sinal)
    for atraso, ganho in ((225, 0.5), (556, 0.5)):
        d = int(atraso * TAXA / 44100)
        b = np.zeros(d + 1)
        b[0], b[d] = -ganho, 1
        a = np.zeros(d + 1)
        a[0], a[d] = 1, -ganho
        molhado = lfilter(b, a, molhado)
    molhado = passa_baixa(molhado, 5000)
    return sinal * (1 - mistura) + molhado * mistura * 0.25


class Partitura:
    """Uma música: 'por' coloca notas no tempo (em batidas); 'render' devolve o áudio final."""

    def __init__(self, bpm, compassos, batidas_por_compasso=4, loop=True, semente=1):
        self.bpm = bpm
        self.batida = 60.0 / bpm
        self.batidas_por_compasso = batidas_por_compasso
        self.duracao = compassos * batidas_por_compasso * self.batida
        self.loop = loop
        self.audio = np.zeros(int(TAXA * (self.duracao + 6)))
        self.rng = np.random.default_rng(semente)

    def segundos(self, batida):
        return batida * self.batida

    def por(self, som, batida, volume=1.0):
        inicio = int(TAXA * self.segundos(batida))
        if inicio >= len(self.audio):
            return
        fim = min(len(self.audio), inicio + len(som))
        self.audio[inicio:fim] += som[:fim - inicio] * volume

    def por_em_segundos(self, som, segundos, volume=1.0):
        inicio = int(TAXA * segundos)
        fim = min(len(self.audio), inicio + len(som))
        self.audio[inicio:fim] += som[:fim - inicio] * volume

    def render(self, sala=1.0, mistura=0.3):
        audio = reverb(self.audio, sala, mistura)
        n = int(TAXA * self.duracao)
        if self.loop:                                   # a cauda do fim volta para o começo: emenda sem estalo
            final = audio[:n].copy()
            cauda = audio[n:]
            final[:len(cauda)] += cauda[:n]
            audio = final
        else:
            audio = audio[:n + int(TAXA * 3)]
            audio *= envelope(len(audio), 0.001, 1.5)
        pico = np.max(np.abs(audio)) or 1.0
        audio = audio / pico * 0.85
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > VOLUME_MEDIO:                          # todas as músicas com mais ou menos o mesmo volume
            audio *= VOLUME_MEDIO / rms
        return audio


def melodia(rng, escala, compassos, notas_por_compasso, inicio=0, tonica=0):
    """Melodia em passos pela escala (grau a grau, às vezes um salto), voltando para a tônica no fim."""
    graus = []
    grau = tonica
    for i in range(compassos * notas_por_compasso):
        passo = rng.choice([-2, -1, -1, 0, 1, 1, 2, 3, -3], p=[.08, .22, .12, .06, .22, .14, .08, .04, .04])
        grau = int(np.clip(grau + passo, -3, len(escala) + 3))
        graus.append(grau)
    graus[-1] = tonica
    return [escala[g % len(escala)] + 12 * (g // len(escala)) + inicio for g in graus]


MENOR = [0, 2, 3, 5, 7, 8, 10]
FRIGIO = [0, 1, 3, 5, 7, 8, 10]
MENOR_HARMONICA = [0, 2, 3, 5, 7, 8, 11]
DORICO = [0, 2, 3, 5, 7, 9, 10]


# ============================================================
# AS MÚSICAS
# ============================================================

def titulo():
    """Ré menor, lento: coro e órgão grave, sinos ao longe — a Catedral no penhasco."""
    p = Partitura(56, 12, semente=11)
    acordes = [[50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 49, 52]] * 3          # Dm Bb C A
    for c, acorde in enumerate(acordes):
        p.por(coro(acorde, p.segundos(4) + 0.4, "a"), c * 4, 0.9)
        p.por(baixo(acorde[0] - 12, p.segundos(4)), c * 4, 0.8)
        p.por(orgao([acorde[0] - 12], p.segundos(4)), c * 4, 0.25)
    for c in range(0, 12, 2):
        p.por(sino(74 if c % 4 == 0 else 69, 3), c * 4 + 0.0, 0.25)
    for i, nota in enumerate(melodia(p.rng, MENOR, 6, 2, inicio=62)):
        p.por(sino(nota, 2.5, 2.0), 16 + i * 2, 0.18)
    return p.render(1.6, 0.45)


def acampamento():
    """Lá dórico, aconchegante: alaúde dedilhando, cordas suaves e a fogueira estalando."""
    p = Partitura(84, 16, semente=21)
    acordes = [[57, 60, 64], [55, 59, 62], [53, 57, 60], [55, 59, 62]] * 4           # Am G F G
    for c, acorde in enumerate(acordes):
        p.por(pad(acorde, p.segundos(4), 0.8, 1.0, 900), c * 4, 0.35)
        p.por(baixo(acorde[0] - 12, p.segundos(2)), c * 4, 0.6)
        p.por(baixo(acorde[0] - 12, p.segundos(2)), c * 4 + 2, 0.4)
        arpejo = [acorde[0], acorde[1], acorde[2], acorde[1] + 12, acorde[2], acorde[1]]
        for k, nota in enumerate(arpejo + arpejo[:2]):
            p.por(alaude(nota, 0.5, 0.45, p.rng), c * 4 + k * 0.5, 0.45)
    for i, nota in enumerate(melodia(p.rng, DORICO, 8, 2, inicio=69)):
        p.por(alaude(nota, 1.0, 0.7, p.rng), 32 + i * 2, 0.5)
    p.por_em_segundos(crepitar(p.duracao, p.rng, 5), 0, 0.25)
    return p.render(0.9, 0.25)


def floresta():
    """Mi frígio, sombrio: vento, notas soltas de alaúde, um bordão grave e um assobio de coruja."""
    p = Partitura(68, 12, semente=31)
    p.por_em_segundos(vento(p.duracao + 2, p.rng, 0.8), 0, 0.5)
    for c in range(12):
        raiz = [40, 41, 40, 38][c % 4]
        p.por(pad([raiz, raiz + 7], p.segundos(4), 1.8, 1.8, 600), c * 4, 0.45)
    notas = melodia(p.rng, FRIGIO, 12, 2, inicio=64)
    for i, nota in enumerate(notas):
        if p.rng.random() < 0.7:
            p.por(alaude(nota, 1.6, 0.3, p.rng), i * 2 + p.rng.choice([0, 0.5]), 0.5)
    for c in (3, 9):                                         # coruja: dois "uuu" descendo
        t = tempo(0.7)
        uivo = np.sin(2 * np.pi * np.cumsum(np.linspace(520, 470, len(t))) / TAXA) * envelope(len(t), 0.1, 0.4)
        p.por(uivo, c * 4 + 1, 0.12)
        p.por(uivo, c * 4 + 2, 0.12)
    return p.render(1.3, 0.4)


def minas():
    """Mi menor, mecânico: bigorna batendo, baixo em ostinato, gotas pingando no escuro."""
    p = Partitura(92, 16, semente=41)
    for c in range(16):
        raiz = [40, 40, 43, 38][c % 4]
        for k, nota in enumerate([raiz, raiz, raiz + 7, raiz + 12, raiz + 7, raiz, raiz + 3, raiz]):
            p.por(baixo(nota - 12, p.segundos(0.5)), c * 4 + k * 0.5, 0.55)
        p.por(tambor(0.5, 0.8, p.rng), c * 4, 0.6)
        p.por(tambor(0.5, 0.5, p.rng), c * 4 + 2.5, 0.5)
        p.por(sino(88, 0.3, 14), c * 4 + 1, 0.12)                     # bigorna
        p.por(sino(88, 0.3, 14), c * 4 + 3, 0.1)
        if c % 2:
            p.por(pad([raiz + 12, raiz + 19], p.segundos(8), 1.5, 1.5, 700), c * 4, 0.25)
    for _ in range(30):                                                  # gotas
        p.por(caixinha(int(p.rng.integers(84, 96)), 0.2), float(p.rng.uniform(0, 64)), 0.08)
    for i, nota in enumerate(melodia(p.rng, MENOR, 8, 2, inicio=64)):
        p.por(sino(nota, 1.5, 3.5), 32 + i * 2, 0.15)
    return p.render(1.4, 0.35)


def catedral():
    """Dó menor, solene: órgão, coro e sinos — velas que nunca apagam."""
    p = Partitura(54, 12, semente=51)
    acordes = [[48, 51, 55], [44, 48, 51], [46, 50, 53], [43, 47, 50]] * 3          # Cm Ab Bb G
    for c, acorde in enumerate(acordes):
        p.por(orgao(acorde + [acorde[0] - 12], p.segundos(4) + 0.3), c * 4, 0.55)
        if c >= 4:
            p.por(coro([n + 12 for n in acorde], p.segundos(4) + 0.3, "o"), c * 4, 0.6)
    for c in range(0, 12, 4):
        for k, nota in enumerate((72, 67, 63)):
            p.por(sino(nota, 3, 2.2), c * 4 + k * 1.5, 0.22)
    for i, nota in enumerate(melodia(p.rng, MENOR_HARMONICA, 8, 2, inicio=60)):
        p.por(orgao([nota + 12], p.segundos(2)), 16 + i * 2, 0.2)
    return p.render(2.0, 0.5)


def circo():
    """Valsa desafinada em Ré menor (3/4): caixinha de música, órgão de rua e um baixo trôpego."""
    p = Partitura(132, 32, batidas_por_compasso=3, semente=61)
    acordes = [[50, 53, 57], [52, 55, 58], [50, 53, 57], [45, 49, 52], [46, 50, 53], [44, 47, 50], [45, 49, 52], [50, 53, 57]]
    for c in range(32):
        acorde = acordes[c % 8]
        b = c * 3
        p.por(baixo(acorde[0] - 12, p.segundos(1)), b, 0.6)
        for k in (1, 2):
            p.por(orgao([n + 12 for n in acorde], p.segundos(0.8), 0.1), b + k, 0.18)
    notas = melodia(p.rng, MENOR_HARMONICA, 32, 3, inicio=74)
    for i, nota in enumerate(notas):
        if i % 3 != 1 or p.rng.random() < 0.5:
            desafino = 0.3 if p.rng.random() < 0.15 else 0.0               # uma nota torta de vez em quando
            p.por(caixinha(nota + desafino, 0.6), i, 0.45)
    return p.render(1.1, 0.3)


def chefe():
    """Ré menor com trítono, 140 bpm: tambores de guerra, baixo agressivo e metais."""
    p = Partitura(140, 16, semente=71)
    for c in range(16):
        raiz = [38, 38, 44, 37][c % 4]                                     # D D Ab C# (trítono e sensível)
        for k in range(8):
            p.por(baixo(raiz - 12 + (12 if k in (3, 7) else 0), p.segundos(0.5)), c * 4 + k * 0.5, 0.6)
        for k in (0, 1.5, 2, 3.5):
            p.por(tambor(0.45, 1.0, p.rng), c * 4 + k, 0.7)
        p.por(caixa(rng=p.rng), c * 4 + 1, 0.4)
        p.por(caixa(rng=p.rng), c * 4 + 3, 0.4)
        t = tempo(p.segundos(1.5))
        metal = passa_baixa(serra(hz(raiz + 12), t, 12) + serra(hz(raiz + 19), t, 12), 1800)
        p.por(metal * envelope(len(t), 0.02, 0.3), c * 4, 0.25)
    for i, nota in enumerate(melodia(p.rng, MENOR_HARMONICA, 8, 4, inicio=62)):
        t = tempo(p.segundos(1))
        p.por(passa_baixa(serra(hz(nota), t, 10), 2200) * envelope(len(t), 0.01, 0.1), 32 + i, 0.22)
    return p.render(0.8, 0.22)


def vitoria():
    """Vinheta curta: fanfarra de metais e sinos, terminando num acorde aberto."""
    p = Partitura(100, 2, loop=False, semente=81)
    for k, nota in enumerate((62, 66, 69, 74)):
        t = tempo(p.segundos(1 if k < 3 else 4))
        som = passa_baixa(serra(hz(nota), t, 12), 2500) * envelope(len(t), 0.02, 0.3)
        p.por(som, k * 0.75, 0.4)
        p.por(sino(nota + 12, 2.5, 2.5), k * 0.75, 0.25)
    p.por(pad([50, 57, 62, 66], p.segundos(6), 0.2, 2.5, 1600), 2.25, 0.5)
    p.por(tambor(0.8, 1.0), 2.25, 0.6)
    return p.render(1.4, 0.4)


def derrota():
    """Vinheta curta: coro descendo em lamento, um sino fúnebre no fim."""
    p = Partitura(60, 2, loop=False, semente=91)
    for k, acorde in enumerate(([57, 60, 64], [55, 58, 62], [53, 57, 60])):
        p.por(coro(acorde, p.segundos(2) + 0.6, "u"), k * 2.5, 0.8)
    p.por(baixo(33, p.segundos(6)), 0, 0.5)
    p.por(sino(45, 4, 1.5), 6.5, 0.5)
    return p.render(1.8, 0.5)


# ============================================================
# FASE 4: AS FASES NOVAS
# ============================================================

def bosque():
    """Lá menor harmônica, misteriosa: arpejos de alaúde como harpa, sino distante e a névoa (vento)."""
    p = Partitura(72, 12, semente=101)
    p.por_em_segundos(vento(p.duracao + 2, p.rng, 0.5), 0, 0.35)
    acordes = [[45, 48, 52], [41, 45, 48], [43, 47, 50], [40, 44, 47]] * 3            # Am F G E
    for c, acorde in enumerate(acordes):
        p.por(pad([n - 12 for n in acorde], p.segundos(4), 1.5, 1.5, 700), c * 4, 0.35)
        for k, nota in enumerate([acorde[0], acorde[2], acorde[1] + 12, acorde[2] + 12]):
            p.por(alaude(nota + 12, 1.0, 0.6, p.rng), c * 4 + k, 0.35)
    for c in (2, 6, 10):
        p.por(sino(81, 3, 1.6), c * 4 + 2, 0.15)
    for i, nota in enumerate(melodia(p.rng, MENOR_HARMONICA, 6, 2, inicio=69)):
        p.por(caixinha(nota, 1.2), 24 + i * 2, 0.3)
    return p.render(1.5, 0.45)


def pantano():
    """Si frígio, arrastada: baixo pesado, bolhas no lodo, coaxar distante e vento úmido."""
    p = Partitura(60, 12, semente=111)
    p.por_em_segundos(vento(p.duracao + 2, p.rng, 0.4), 0, 0.3)
    for c in range(12):
        raiz = [35, 36, 35, 33][c % 4]
        p.por(baixo(raiz, p.segundos(4)), c * 4, 0.6)
        p.por(pad([raiz + 12, raiz + 19], p.segundos(4), 2.0, 2.0, 500), c * 4, 0.35)
    for _ in range(40):                                                    # bolhas
        p.por(caixinha(int(p.rng.integers(52, 62)), 0.25), float(p.rng.uniform(0, 48)), 0.12)
    for c in (1, 5, 9):                                                    # coaxar: serra curta e filtrada
        t = tempo(0.25)
        coaxo = passa_baixa(serra(hz(40), t, 8), 900) * envelope(len(t), 0.01, 0.1)
        for k in range(3):
            p.por(coaxo, c * 4 + 2 + k * 0.4, 0.2)
    for i, nota in enumerate(melodia(p.rng, FRIGIO, 6, 2, inicio=59)):
        p.por(alaude(nota, 1.8, 0.25, p.rng), 12 + i * 2, 0.35)
    return p.render(1.4, 0.4)


def catacumbas():
    """Fá menor, procissão: coro grave, tambor lento e sino fúnebre — penitentes que não descansam."""
    p = Partitura(52, 12, semente=121)
    acordes = [[41, 44, 48], [39, 43, 46], [37, 41, 44], [36, 40, 43]] * 3            # Fm Eb Db C
    for c, acorde in enumerate(acordes):
        p.por(coro(acorde, p.segundos(4) + 0.4, "o"), c * 4, 0.75)
        p.por(baixo(acorde[0] - 12, p.segundos(4)), c * 4, 0.6)
        p.por(tambor(0.8, 0.7, p.rng), c * 4, 0.5)
        p.por(tambor(0.8, 0.4, p.rng), c * 4 + 2, 0.4)
    for c in range(0, 12, 3):
        p.por(sino(53, 4, 1.4), c * 4, 0.3)
    for i, nota in enumerate(melodia(p.rng, MENOR, 6, 2, inicio=65)):
        p.por(orgao([nota], p.segundos(2)), 24 + i * 2, 0.2)
    return p.render(2.2, 0.55)


def brasa():
    """Mi menor harmônica, 100 bpm: bigornas, tambores de forja, baixo forte e fogo crepitando."""
    p = Partitura(100, 16, semente=131)
    p.por_em_segundos(crepitar(p.duracao, p.rng, 9), 0, 0.35)
    for c in range(16):
        raiz = [40, 40, 36, 35][c % 4]
        for k, nota in enumerate([raiz, raiz + 12, raiz, raiz + 7]):
            p.por(baixo(nota - 12, p.segundos(1)), c * 4 + k, 0.6)
        p.por(tambor(0.5, 1.0, p.rng), c * 4, 0.7)
        p.por(tambor(0.5, 0.7, p.rng), c * 4 + 2, 0.6)
        for k in (1, 1.5, 3):
            p.por(sino(91, 0.25, 16), c * 4 + k, 0.13)                           # marteladas
    for i, nota in enumerate(melodia(p.rng, MENOR_HARMONICA, 8, 2, inicio=64)):
        t = tempo(p.segundos(2))
        p.por(passa_baixa(serra(hz(nota), t, 10), 1600) * envelope(len(t), 0.05, 0.6), 32 + i * 2, 0.18)
    return p.render(1.0, 0.3)


def metais(midis, duracao, corte=1600, ataque=0.08):
    """Naipe de metais: dente-de-serra filtrado, crescendo devagar (fanfarra, 'swell')."""
    t = tempo(duracao)
    som = sum(serra(hz(m), t, 12) for m in midis) / max(1, len(midis))
    return passa_baixa(som, corte) * envelope(len(t), ataque, min(0.6, duracao * 0.4))


def cidadela():
    """Si menor, gélida, em três partes (a nevasca não para):
    A  vento, bordão grave, cordas em tremolo e caixinha de gelo em arpejos;
    B  a flauta canta o tema, coro distante, tímpano surdo e sinos respondendo;
    A' tudo junto e mais agudo, depois volta ao vento (o loop emenda)."""
    p = Partitura(64, 20, semente=141)
    p.por_em_segundos(vento(p.duracao + 2, p.rng, 1.2), 0, 0.4)
    p.por_em_segundos(vento(p.duracao + 2, np.random.default_rng(7), 0.7), 0, 0.2)        # segunda rajada, defasada
    harmonia = ([[47, 50, 54], [43, 47, 50], [45, 49, 52], [42, 46, 49]] * 2 +               # A: Bm G A F#
                [[40, 43, 47], [47, 50, 54], [43, 47, 50], [42, 46, 49]] * 2 +               # B: Em Bm G F#
                [[47, 50, 54], [43, 47, 50], [45, 49, 52], [42, 46, 49]])                    # A'
    for c, acorde in enumerate(harmonia):
        p.por(baixo(acorde[0] - 12, p.segundos(4)), c * 4, 0.45)
        p.por(tremolo(pad(acorde, p.segundos(4), 1.6, 1.8, 2400), 6.5, 0.5), c * 4, 0.32 if c < 16 else 0.42)
        for k, nota in enumerate([acorde[0] + 24, acorde[2] + 24, acorde[1] + 24, acorde[2] + 24]):   # arpejo de gelo
            if c < 8 or c >= 16 or k % 2 == 0:
                p.por(caixinha(nota, 0.9), c * 4 + k + 0.5, 0.16)
        if 8 <= c < 16:
            p.por(coro([n + 12 for n in acorde], p.segundos(4) + 0.4, "u"), c * 4, 0.3)
            p.por(timpano(acorde[0] - 12, 1.6, 0.8), c * 4, 0.35)
        if c >= 16:
            p.por(coro([n + 12 for n in acorde], p.segundos(4) + 0.4, "a"), c * 4, 0.4)
            p.por(timpano(acorde[0] - 12, 1.6, 1.0), c * 4, 0.45)
            p.por(timpano(acorde[0] - 12, 1.0, 0.7), c * 4 + 2, 0.35)
    tema = [71, 74, 73, 71, 69, 71, 66, 0, 67, 69, 71, 74, 73, 71, 73, 0,                    # a flauta (Si menor)
            76, 74, 73, 71, 73, 69, 71, 0, 66, 67, 69, 71, 70, 66, 71, 0]
    for i, nota in enumerate(tema[:24]):                                                     # partes B e A'
        if nota:
            p.por(flauta(nota, p.segundos(2) * 0.95), 32 + i * 2, 0.5)
    for c in range(0, 20, 2):                                                                # sinos de gelo ao longe
        p.por(sino(83 if c % 4 == 0 else 78, 3.5, 2.5), c * 4 + 3, 0.1)
    return p.render(2.6, 0.6)


def eclipse():
    """Dó# menor, épica, em três partes (o sol negro sobre a Catedral):
    A  bordão de órgão, coro sussurrado, sino da torre e o tímpano batendo como um coração;
    B  baixo pulsando, órgão em acordes, o tema no coro e metais crescendo, cordas em tremolo;
    C  clímax: rufar de tímpanos, metais no agudo, coro inteiro e sinos — e volta ao bordão."""
    p = Partitura(62, 24, semente=151)
    harmonia = ([[49, 52, 56], [45, 49, 52], [47, 51, 54], [44, 48, 51]] * 2 +               # C#m A B G#
                [[49, 52, 56], [42, 45, 49], [44, 48, 51], [49, 52, 56]] * 2 +               # C#m F#m G# C#m
                [[45, 49, 52], [47, 51, 54], [44, 48, 51], [49, 52, 56]] * 2)                # A B G# C#m
    for c, acorde in enumerate(harmonia):
        parte = 0 if c < 8 else (1 if c < 16 else 2)
        p.por(orgao([acorde[0] - 12, acorde[0] - 24] if parte == 0 else acorde + [acorde[0] - 12], p.segundos(4) + 0.3),
              c * 4, 0.45)
        p.por(coro([n + 12 for n in acorde], p.segundos(4) + 0.3, "o" if parte == 0 else "a"), c * 4, (0.3, 0.45, 0.6)[parte])
        p.por(sino(49 + 12, 4, 1.4), c * 4, 0.16 if parte < 2 else 0.24)                     # o sino da torre
        p.por(timpano(acorde[0] - 24, 0.9, 0.9), c * 4, 0.4)                                 # coração: tum-tum
        p.por(timpano(acorde[0] - 24, 0.7, 0.6), c * 4 + 0.5, 0.3)
        if parte >= 1:
            for k in range(8):                                                               # baixo pulsando
                p.por(baixo(acorde[0] - 12 + (7 if k in (3, 7) else 0), p.segundos(0.5)), c * 4 + k * 0.5, 0.42)
            p.por(tremolo(pad([n + 24 for n in acorde], p.segundos(4), 0.6, 1.0, 3200), 8.0, 0.7), c * 4, 0.16)
            p.por(metais([acorde[0], acorde[2]], p.segundos(4), 1400 if parte == 1 else 2200, 1.2), c * 4, 0.16 if parte == 1 else 0.24)
        if parte == 2:
            for k in range(16):                                                              # rufar
                p.por(timpano(acorde[0] - 24, 0.3, 0.4 + k / 32), c * 4 + k * 0.25, 0.25)
            p.por(metais([acorde[0] + 12, acorde[1] + 12], p.segundos(2), 2600, 0.05), c * 4 + 2, 0.18)
            for k, nota in enumerate((73, 68, 64, 61)):
                p.por(sino(nota, 3, 2.0), c * 4 + k, 0.14)
    tema = [61, 64, 63, 61, 60, 61, 56, 0, 61, 64, 66, 68, 66, 64, 63, 0,                    # o tema (coro + órgão)
            64, 66, 68, 69, 68, 66, 64, 63, 61, 63, 64, 61, 60, 56, 61, 0]
    for i, nota in enumerate(tema):
        if nota:
            p.por(coro([nota + 12], p.segundos(2) * 0.95, "a"), 32 + i * 2, 0.35)
            p.por(orgao([nota + 12], p.segundos(2) * 0.95, 0.4), 32 + i * 2, 0.15)
    return p.render(2.4, 0.5)


def mercador():
    """O Mercador Mascarado: tango sorrateiro em Ré menor com sexta frígia (\"Tudo tem preço\").
    Baixo beliscado no ritmo de habanera, cravo nos contratempos, castanholas, moedas tilintando
    e o tema torto no 'acordeão' (órgão com tremolo), respondido pela flauta."""
    p = Partitura(112, 24, semente=161)
    harmonia = [[50, 53, 57], [51, 55, 58], [48, 52, 55], [45, 49, 52]] * 6                  # Dm Eb C A
    for c, acorde in enumerate(harmonia):
        raiz = acorde[0] - 12
        for b, nota in ((0, raiz), (1.5, raiz + 7), (2, raiz), (3, raiz + 12)):              # habanera
            p.por(alaude(nota, 0.4, 0.3, p.rng), c * 4 + b, 0.6)
        for b in (0.5, 1.5, 2.5, 3.5):                                                        # cravo nos contratempos
            for nota in acorde:
                p.por(cravo(nota + 12, 0.2, p.rng), c * 4 + b, 0.1)
        for b in (0, 0.75, 1, 2, 2.75, 3, 3.5):                                               # castanholas
            p.por(caixa(0.06, 3400, p.rng), c * 4 + b, 0.22 if b in (0, 2) else 0.14)
        if c % 4 == 3:                                                                        # moedas
            for k in range(3):
                p.por(sino(96 + k * 2, 0.4, 9), c * 4 + 3 + k * 0.15, 0.08)
    tema = [74, 75, 74, 73, 74, 0, 69, 70, 69, 67, 69, 0, 72, 70, 69, 67, 65, 64, 61, 0,     # o tema torto
            62, 65, 69, 74, 75, 74, 72, 70, 69, 0, 73, 74]
    batidas = [0, 1, 1.5, 2, 3, 4, 4.5, 5, 5.5, 6, 7, 8, 8.5, 9, 9.5, 10, 10.5, 11, 12, 13,
               16, 17, 17.5, 18, 19, 19.5, 20, 20.5, 21, 22, 23, 23.5]
    for volta in (0, 1):
        for nota, b in zip(tema, batidas):
            if nota:
                inicio = 16 + volta * 48 + b
                if volta == 0:
                    p.por(tremolo(orgao([nota], p.segundos(0.9), 0.15), 5.5, 0.4), inicio, 0.3)
                else:
                    p.por(flauta(nota + 12, p.segundos(0.9)), inicio, 0.28)
    return p.render(1.0, 0.25)


def primeiro_heroi():
    """O Primeiro Herói: nobre e triste, em Ré. Harpa e cordas em menor (a lembrança), depois o tema
    heroico nos metais vira maior com coro e tímpanos — e acaba numa resolução luminosa."""
    p = Partitura(76, 24, semente=171)
    harmonia = ([[50, 53, 57], [46, 50, 53], [41, 45, 48], [48, 52, 55]] * 2 +               # A: Dm Bb F C (lembrança)
                [[50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 49, 52]] * 2 +               # B: Dm Bb C A (a luta)
                [[50, 54, 57], [43, 47, 50], [45, 49, 52], [50, 54, 57]] * 2)                # C: D G A D (maior: a luz)
    for c, acorde in enumerate(harmonia):
        parte = 0 if c < 8 else (1 if c < 16 else 2)
        p.por(baixo(acorde[0] - 12, p.segundos(4)), c * 4, 0.5)
        p.por(pad(acorde, p.segundos(4), 1.2, 1.6, 1800 + 800 * parte), c * 4, 0.35)
        for k, nota in enumerate([acorde[0], acorde[1], acorde[2], acorde[0] + 12, acorde[2], acorde[1]]):   # harpa
            p.por(alaude(nota + 12, 1.2, 0.8, p.rng), c * 4 + k * (4 / 6), 0.3 if parte < 2 else 0.22)
        if parte >= 1:
            p.por(timpano(acorde[0] - 24, 1.4, 0.9), c * 4, 0.4)
            p.por(coro([n + 12 for n in acorde], p.segundos(4) + 0.4, "a"), c * 4, 0.35 if parte == 1 else 0.5)
        if parte == 2:
            p.por(timpano(acorde[0] - 24, 0.8, 0.7), c * 4 + 2.5, 0.3)
            p.por(timpano(acorde[0] - 24, 0.8, 0.8), c * 4 + 3, 0.32)
            p.por(sino(acorde[2] + 24, 3, 2.0), c * 4, 0.12)
    lembranca = [62, 65, 69, 67, 65, 64, 62, 0, 65, 67, 69, 72, 70, 69, 67, 0]               # flauta (parte A)
    for i, nota in enumerate(lembranca):
        if nota:
            p.por(flauta(nota + 12, p.segundos(2) * 0.95, 4.5), i * 2, 0.26)
    heroico = [62, 69, 74, 72, 70, 69, 67, 69, 65, 67, 69, 74, 73, 69, 73, 76]                # metais (B e C)
    for i, nota in enumerate(heroico):
        p.por(metais([nota, nota - 12], p.segundos(2) * 0.95, 1900, 0.06), 32 + i * 2, 0.24)
    for i, nota in enumerate(heroico[:8] + [74, 78, 81, 79, 78, 76, 78, 74]):                 # em maior, no agudo
        if 64 + i * 2 < p.duracao / p.batida:
            p.por(metais([nota + (1 if nota in (65, 72) else 0), nota - 5], p.segundos(2) * 0.95, 2600, 0.05),
                  64 + i * 2, 0.26)
    return p.render(2.0, 0.45)


# ============================================================
# REINO DOS RATOS (docs/planos/reino_dos_ratos.md): uma música por zona
# ============================================================

def guincho(duracao=0.12, de=2200, ate=3300):
    """Guincho de rato: um assobio agudo que sobe depressa."""
    t = tempo(duracao)
    return np.sin(2 * np.pi * np.cumsum(np.linspace(de, ate, len(t))) / TAXA) * envelope(len(t), 0.005, 0.06)


def guinchos(p, quantos, inicio, fim, volume=0.05):
    """Guinchos soltos ao longe (em pares, às vezes três), espalhados entre as batidas 'inicio' e 'fim'."""
    for _ in range(quantos):
        b = float(p.rng.uniform(inicio, fim))
        for k in range(int(p.rng.integers(2, 4))):
            de = float(p.rng.uniform(1900, 2600))
            p.por(guincho(float(p.rng.uniform(0.06, 0.14)), de, de * 1.4), b + k * 0.18, volume)


def reino_galerias():
    """Dó menor, úmido e lento: bordão grave, gotas ecoando no túnel, flauta desafinada e guinchos ao longe."""
    p = Partitura(58, 12, semente=211)
    p.por_em_segundos(vento(p.duracao + 2, p.rng, 0.35), 0, 0.25)
    for c in range(12):
        raiz = [36, 36, 35, 31][c % 4]
        p.por(pad([raiz, raiz + 7], p.segundos(4), 2.0, 2.0, 500), c * 4, 0.45)
        p.por(baixo(raiz - 12, p.segundos(2)), c * 4, 0.5)
        p.por(baixo(raiz - 12, p.segundos(2)), c * 4 + 2.5, 0.3)
    for _ in range(48):                                                     # gotas no túnel
        p.por(caixinha(int(p.rng.integers(86, 99)), 0.18), float(p.rng.uniform(0, 48)), 0.07)
    for i, nota in enumerate(melodia(p.rng, MENOR, 6, 2, inicio=60)):
        if p.rng.random() < 0.75:                                           # flauta "desafinada": às vezes um quarto de tom
            desvio = 0.5 if p.rng.random() < 0.3 else 0.0
            p.por(flauta(nota + desvio, 1.6, 4.0, 0.35), 12 + i * 2, 0.22)
    guinchos(p, 6, 0, 48)
    return p.render(2.0, 0.55)


def reino_mercado():
    """Ré frígio, feira grotesca a 104 bpm: cravo saltitante, chocalho, baixo beliscado, moedas e burburinho."""
    p = Partitura(104, 16, semente=221)
    p.por_em_segundos(vento(p.duracao + 2, p.rng, 0.25), 0, 0.2)            # burburinho da feira
    for c in range(16):
        raiz = [50, 51, 50, 48][c % 4]
        for k, nota in enumerate([raiz, raiz + 7, raiz + 12, raiz + 7, raiz + 3, raiz + 7, raiz + 10, raiz + 7]):
            p.por(cravo(nota, 0.4, p.rng), c * 4 + k * 0.5, 0.3)
        p.por(baixo(raiz - 24, p.segundos(0.5)), c * 4, 0.6)
        p.por(baixo(raiz - 17, p.segundos(0.5)), c * 4 + 2, 0.45)
        for k in (1, 3):
            p.por(caixa(0.12, 3000, p.rng), c * 4 + k, 0.25)
        if p.rng.random() < 0.5:                                            # moedas tilintando
            p.por(sino(int(p.rng.integers(88, 96)), 0.3, 12), c * 4 + float(p.rng.choice([0.5, 1.5, 2.5, 3.5])), 0.1)
    for i, nota in enumerate(melodia(p.rng, FRIGIO, 8, 2, inicio=62)):
        p.por(alaude(nota, 0.9, 0.7, p.rng), 32 + i * 2, 0.4)
        p.por(alaude(nota + 12, 0.5, 0.8, p.rng), 32 + i * 2 + 1, 0.2)
    guinchos(p, 8, 0, 64, 0.04)
    return p.render(1.2, 0.3)


def reino_catedral():
    """Si bemol menor, missa roída: coro e órgão que desafinam aos poucos, sino rachado e gotas no eco."""
    p = Partitura(50, 12, semente=231)
    acordes = [[46, 49, 53], [44, 48, 51], [42, 46, 49], [41, 45, 48]] * 3       # Bbm Ab Gb F
    for c, acorde in enumerate(acordes):
        desvio = 0.3 if c % 3 == 2 else 0.0                                     # a missa sai do tom de vez em quando
        p.por(coro([n + desvio for n in acorde], p.segundos(4) + 0.4, "o"), c * 4, 0.7)
        p.por(orgao([acorde[0] - 12], p.segundos(4)), c * 4, 0.25)
        p.por(baixo(acorde[0] - 12, p.segundos(4)), c * 4, 0.45)
    for c in range(0, 12, 2):
        p.por(sino(58, 4, 1.2), c * 4 + 1, 0.22)                                # sino rachado (grave e torto)
        p.por(sino(59, 3, 1.5), c * 4 + 1.05, 0.12)
    for _ in range(26):
        p.por(caixinha(int(p.rng.integers(84, 96)), 0.2), float(p.rng.uniform(0, 48)), 0.06)
    for i, nota in enumerate(melodia(p.rng, MENOR, 6, 2, inicio=70)):
        p.por(orgao([nota], p.segundos(2)), 24 + i * 2, 0.16)
    guinchos(p, 4, 0, 48, 0.035)
    return p.render(2.3, 0.6)


def reino_trono():
    """Sol menor, marcha real grotesca a 80 bpm: tímpanos, fanfarra torta (trítono), baixo pesado e coro grave."""
    p = Partitura(80, 16, semente=241)
    for c in range(16):
        raiz = [43, 43, 46, 42][c % 4]
        p.por(timpano(raiz - 12, 1.0, 1.0), c * 4, 0.55)
        p.por(timpano(raiz - 12, 0.6, 0.6), c * 4 + 2, 0.4)
        p.por(baixo(raiz - 12, p.segundos(4)), c * 4, 0.5)
        p.por(coro([raiz, raiz + 3, raiz + 7], p.segundos(4) + 0.3, "o"), c * 4, 0.35)
        p.por(caixa(0.1, 2600, p.rng), c * 4 + 3.5, 0.2)
        if c % 4 == 3:                                                       # a fanfarra do Rei, com a nota errada
            p.por(metais([raiz + 12, raiz + 18], p.segundos(1.5), 2200, 0.04), c * 4 + 1, 0.3)
    for i, nota in enumerate(melodia(p.rng, MENOR_HARMONICA, 8, 2, inicio=67)):
        p.por(metais([nota], p.segundos(1.8) * 0.95, 2400, 0.05), 32 + i * 2, 0.22)
    guinchos(p, 10, 0, 64, 0.045)
    return p.render(1.8, 0.45)


def arroto(duracao=0.5, de=33, ate=27):
    """O 'arroto' do Rei: um metal grave que escorrega para baixo (fase acumulada, como no guincho)."""
    t = tempo(duracao)
    f = np.linspace(hz(de), hz(ate), len(t))
    fase = 2 * np.pi * np.cumsum(f) / TAXA
    som = sum(np.sin(fase * k) / k for k in range(1, 9))
    return passa_baixa(som, 900) * envelope(len(t), 0.03, 0.2)


def reino_rei():
    """O Rei dos Ratos: minueto de corte gordo e torto em Sol menor (3/4, 96 bpm). Baixo de tuba no 'pum', cravo no
    'pa-pa', o tema cerimonioso no cravo e na flauta, moedas contadas e um arroto de metais no fim da frase. Na 2ª
    metade vem a Fúria Real: tímpanos, caixa e o tema nos metais, com a nota errada da fanfarra."""
    p = Partitura(96, 32, batidas_por_compasso=3, semente=251)
    harmonia = [[43, 46, 50], [48, 51, 55], [50, 54, 57], [43, 46, 50],
                [39, 43, 46], [48, 51, 55], [50, 54, 57], [50, 54, 57]] * 4               # Gm Cm D Gm Eb Cm D D
    for c, acorde in enumerate(harmonia):
        b, raiz, furia = c * 3, acorde[0] - 12, c >= 16
        p.por(baixo(raiz, p.segundos(1)), b, 0.65)                                         # pum
        p.por(metais([raiz + 12], p.segundos(0.9), 700, 0.02), b, 0.2)                      # (a tuba)
        for k in (1, 2):                                                                   # pa-pa
            for nota in acorde[1:]:
                p.por(cravo(nota, 0.25, p.rng), b + k, 0.14)
        if furia:
            p.por(timpano(raiz, 0.9, 1.0), b, 0.45)
            p.por(caixa(0.1, 2400, p.rng), b + 2.5, 0.18)
        if c % 4 == 1:                                                                    # o Rei conta as moedas
            for k in range(3):
                p.por(sino(int(p.rng.integers(90, 97)), 0.3, 12), b + 1 + k * 0.33, 0.07)
        if c % 8 == 7:                                                                    # fim da frase: arroto real
            p.por(arroto(), b + 1.5, 0.35)
    tema = [67, 70, 74, 72, 70, 67, 66, 69, 72, 70, 67, 0, 70, 67, 63, 72, 75, 72, 70, 69, 66, 69, 0, 0]
    for volta in range(4):
        for i, nota in enumerate(tema):
            if not nota:
                continue
            inicio = volta * 24 + i
            if volta < 2:                                                                 # o minueto cerimonioso
                p.por(cravo(nota + 12, 0.5, p.rng), inicio, 0.3)
                if volta == 1:
                    p.por(flauta(nota + 12, p.segundos(0.95)), inicio, 0.2)
            else:                                                                         # a Fúria: metais tortos
                torta = 1 if (i == 9 and volta == 3) else 0
                p.por(metais([nota + torta, nota - 12], p.segundos(0.95), 2300, 0.04), inicio, 0.24)
    guinchos(p, 8, 0, 96, 0.04)
    return p.render(1.5, 0.4)


def reino_rainha():
    """A Rainha dos Ratos: a roda que não para, em Mi frígio a 132 bpm. Oito notas por compasso (os oito ratos) num
    arpejo que gira uma casa a cada compasso, o coração do nó no tímpano, órgão grave e coro sussurrado; a flauta
    chora o lamento. Na 2ª metade a roda enlouquece: cordas em tremolo, cravo em contratempo, metais rangendo em
    semitom e cada vez mais guinchos."""
    p = Partitura(132, 32, semente=261)
    raizes = [40, 40, 41, 40, 38, 40, 41, 43] * 4                                         # E E F E D E F G
    roda = [0, 7, 12, 13, 12, 7, 3, 1]
    for c, raiz in enumerate(raizes):
        b, louca = c * 4, c >= 16
        p.por(orgao([raiz - 12, raiz - 5], p.segundos(4) + 0.2), b, 0.28)
        p.por(timpano(raiz - 12, 0.7, 0.9), b, 0.42)                                       # o nó pulsando: tum-tum
        p.por(timpano(raiz - 12, 0.5, 0.6), b + 0.5, 0.3)
        p.por(coro([raiz + 12, raiz + 15, raiz + 19], p.segundos(4) + 0.3, "u"), b, 0.32 if louca else 0.22)
        for k in range(8):                                                                 # a roda gira uma casa
            nota = raiz + 24 + roda[(k + c) % 8]
            p.por(caixinha(nota, 0.35), b + k * 0.5, 0.2 if k == 0 else 0.12)
            if louca:
                p.por(cravo(nota - 12, 0.2, p.rng), b + k * 0.5 + 0.25, 0.08)
        if louca:
            p.por(tremolo(pad([raiz + 12, raiz + 13, raiz + 19], p.segundos(4), 0.4, 0.8, 2600), 9.0, 0.7), b, 0.18)
            if c % 2 == 1:
                p.por(metais([raiz + 12, raiz + 13], p.segundos(1.5), 2000, 0.05), b + 2, 0.16)
    for i, nota in enumerate(melodia(p.rng, FRIGIO, 8, 2, inicio=64)):                    # o lamento da flauta
        p.por(flauta(nota, p.segundos(2) * 0.95, 6.0, 0.3), 32 + i * 2, 0.24)
    guinchos(p, 8, 0, 64, 0.04)
    guinchos(p, 20, 64, 128, 0.055)
    return p.render(1.6, 0.4)


MUSICAS = {"titulo": titulo, "acampamento": acampamento, "floresta": floresta, "minas": minas, "catedral": catedral,
           "circo": circo, "chefe": chefe, "vitoria": vitoria, "derrota": derrota,
           "bosque": bosque, "pantano": pantano, "catacumbas": catacumbas, "brasa": brasa, "cidadela": cidadela,
           "eclipse": eclipse, "mercador": mercador, "primeiro_heroi": primeiro_heroi,
           "reino_galerias": reino_galerias, "reino_mercado": reino_mercado, "reino_catedral": reino_catedral,
           "reino_trono": reino_trono, "reino_rei": reino_rei, "reino_rainha": reino_rainha}


def salvar(nome, audio):
    dados = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(PASTA, nome + ".wav"), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(dados.tobytes())
    return len(dados) / TAXA


def main():
    os.makedirs(PASTA, exist_ok=True)
    for nome in sys.argv[1:] or list(MUSICAS):
        print(f"{nome}: {salvar(nome, MUSICAS[nome]()):.1f} s")


if __name__ == "__main__":
    main()
