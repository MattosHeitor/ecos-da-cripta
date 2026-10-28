"""Gera os efeitos sonoros PROVISÓRIOS do jogo (sintetizados com numpy) em assets/sons/efeitos/.

    python ferramentas/gerar_sons.py            # gera todos
    python ferramentas/gerar_sons.py golpe cura # só esses

São sons simples, no clima sombrio, para o jogo não ficar mudo. Os 15 mais tocados (marcados "revisado")
ganharam camadas e eco de cripta; os demais continuam provisórios. Para trocar por sons de verdade,
basta pôr um arquivo com o MESMO nome (.wav ou .ogg) na pasta — o jogo pega sozinho.
"""

import os
import sys
import wave

import numpy as np
from scipy.signal import lfilter, butter, fftconvolve

TAXA = 22050
PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sons", "efeitos")
SORTEIO = np.random.default_rng(7)


# ---------------- peças ----------------
def tempo(segundos):
    return np.arange(int(TAXA * segundos)) / TAXA


def seno(freq, segundos, fase=0.0):
    return np.sin(2 * np.pi * freq * tempo(segundos) + fase)


def varredura(f0, f1, segundos):
    """Seno que desliza de f0 a f1 (subindo ou descendo)."""
    t = tempo(segundos)
    freq = np.geomspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(freq) / TAXA)


def ruido(segundos):
    return SORTEIO.uniform(-1, 1, int(TAXA * segundos))


def decaimento(n, velocidade):
    return np.exp(-np.linspace(0, velocidade, n))


def envelope(n, ataque=0.01, soltura=0.05):
    """Sobe rápido e desce no fim (evita estalos)."""
    env = np.ones(n)
    a, s = max(1, int(TAXA * ataque)), max(1, int(TAXA * soltura))
    env[:a] = np.linspace(0, 1, a)
    env[-s:] *= np.linspace(1, 0, s)
    return env


def grave(sinal, corte=0.08):
    """Filtro passa-baixa simples (deixa o ruído abafado)."""
    return lfilter([corte], [1, corte - 1], sinal)


def sino(freqs, segundos, velocidade=6):
    """Som de metal/sino: várias frequências desafinadas que somem aos poucos."""
    soma = sum(seno(f, segundos) / (i + 1) for i, f in enumerate(freqs))
    return soma * decaimento(len(soma), velocidade)


def juntar(*partes):
    tamanho = max(len(p) for p in partes)
    saida = np.zeros(tamanho)
    for p in partes:
        saida[:len(p)] += p
    return saida


def em_sequencia(notas, duracao, intervalo, velocidade=5):
    """Arpejo: cada nota começa 'intervalo' segundos depois da anterior."""
    total = intervalo * (len(notas) - 1) + duracao
    saida = np.zeros(int(TAXA * total) + 1)
    for i, freq in enumerate(notas):
        nota = sino([freq, freq * 2.01], duracao, velocidade)
        inicio = int(TAXA * intervalo * i)
        saida[inicio:inicio + len(nota)] += nota
    return saida


def estalos(segundos, quantidade):
    """Estalos de fogo espalhados no tempo."""
    saida = np.zeros(int(TAXA * segundos))
    for _ in range(quantidade):
        inicio = SORTEIO.integers(0, len(saida) - 200)
        saida[inicio:inicio + 200] += ruido(200 / TAXA) * decaimento(200, 9)
    return saida


def borbulhas(segundos):
    """Bolhas de veneno: senos curtos subindo de tom, um atrás do outro."""
    saida = np.zeros(int(TAXA * segundos))
    for k in range(7):
        bolha = varredura(SORTEIO.uniform(300, 500), SORTEIO.uniform(700, 1100), 0.06) * np.hanning(int(TAXA * 0.06))
        inicio = int(k / 7 * (len(saida) - len(bolha)))
        saida[inicio:inicio + len(bolha)] += bolha
    return saida


def rugido(segundos, base):
    """Rugido: ruído grave modulado por uma vibração irregular, subindo e caindo."""
    t = tempo(segundos)
    vibracao = 1 + 0.6 * np.sin(2 * np.pi * (25 + 10 * np.sin(2 * np.pi * 3 * t)) * t)
    corpo = juntar(grave(ruido(segundos), 0.06) * 4, seno(base, segundos) * 0.6, seno(base * 1.5, segundos) * 0.3)
    return corpo * vibracao * np.sin(np.pi * t / segundos) ** 0.7


def rangido(segundos):
    """Madeira rangendo (dobradiça do baú)."""
    t = tempo(segundos)
    freq = 180 + 60 * np.sin(2 * np.pi * 6 * t)
    return np.sign(np.sin(2 * np.pi * np.cumsum(freq) / TAXA)) * grave(ruido(segundos), 0.3) * envelope(len(t), 0.02, 0.1) * 2


# ---------------- peças dos sons de ataque ----------------
def faixa(sinal, baixo, alto):
    """Passa-faixa (só as frequências entre baixo e alto)."""
    b, a = butter(2, [baixo / (TAXA / 2), min(0.99, alto / (TAXA / 2))], btype="band")
    return lfilter(b, a, sinal)


def agudo(sinal, corte):
    b, a = butter(2, corte / (TAXA / 2), btype="high")
    return lfilter(b, a, sinal)


def sopro(segundos, f0, f1, largura=0.5):
    """Vento cortado por uma arma: ruído numa faixa que desliza de f0 a f1 (o "swoosh")."""
    n = int(TAXA * segundos)
    saida = np.zeros(n)
    bloco = 256
    centros = np.geomspace(f0, f1, n // bloco + 1)
    ruido_total = ruido(segundos + 0.05)
    for i, c in enumerate(centros):
        trecho = ruido_total[i * bloco:i * bloco + bloco * 3]
        if len(trecho) < 64:
            break
        filtrado = faixa(trecho, c * (1 - largura / 2), c * (1 + largura / 2))[bloco:bloco * 2]
        saida[i * bloco:i * bloco + len(filtrado)] = filtrado[:max(0, min(len(filtrado), n - i * bloco))]
    return saida * np.sin(np.linspace(0, np.pi, n)) ** 1.5


def corda(freq, segundos, brilho=0.6):
    """Corda dedilhada (Karplus-Strong): alaúde, corda do arco."""
    n = int(TAXA * segundos)
    atraso = max(2, int(TAXA / freq))
    excitacao = np.zeros(n)
    excitacao[:atraso] = grave(ruido(atraso / TAXA + 0.001)[:atraso], 0.2 + 0.6 * brilho)
    a = np.zeros(atraso + 2)
    a[0], a[atraso], a[atraso + 1] = 1, -0.497, -0.497
    return lfilter([1.0], a, excitacao) * envelope(n, 0.001, 0.08)


def estrondo(segundos, forca_rugido=1.0):
    """Ruído bem grave que treme e vai sumindo (trovão distante, explosão)."""
    t = tempo(segundos)
    rugido_ = grave(grave(ruido(segundos), 0.03), 0.05) * 12
    tremor = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 7 * t + np.sin(2 * np.pi * 2 * t) * 3))
    return rugido_ * tremor * np.exp(-t * 2.2) * forca_rugido


# ---------------- peças da revisão (sons mais tocados) ----------------
def atrasar(sinal, segundos):
    return np.concatenate([np.zeros(int(TAXA * segundos)), sinal])


def eco(sinal, segundos=0.6, mistura=0.2, abafar=0.25):
    """Reverberação de cripta: o som batendo em pedra e sumindo num salão vazio."""
    n = int(TAXA * segundos)
    cauda = grave(ruido(segundos), abafar) * np.exp(-np.linspace(0, 7, n))
    molhado = fftconvolve(sinal, cauda)
    molhado *= mistura * np.max(np.abs(sinal)) / (np.max(np.abs(molhado)) or 1)
    return juntar(sinal, molhado * envelope(len(molhado), 0.001, min(0.2, segundos / 2)))


def estalo(segundos=0.01, corte=2500):
    """Transiente seco do contato (o "tac" do começo de um impacto)."""
    return agudo(ruido(segundos), corte) * decaimento(int(TAXA * segundos), 5)


def baque(segundos, f0, f1, velocidade=8):
    """Corpo de um impacto: um grave que despenca de f0 a f1 e some rápido."""
    return varredura(f0, f1, segundos) * decaimento(int(TAXA * segundos), velocidade)


def metal(freqs, segundos, velocidade=6):
    """Metal golpeado: modos desafinados, os agudos somem antes dos graves."""
    t = tempo(segundos)
    return sum(np.sin(2 * np.pi * f * t + i) * np.exp(-t * velocidade * (1 + i * 0.6)) / (1 + i * 0.4)
               for i, f in enumerate(freqs))


def serrote(f0, f1, segundos, harmonicos=8):
    """Onda rica (vários harmônicos) deslizando de f0 a f1: base de gemidos."""
    fase = 2 * np.pi * np.cumsum(np.geomspace(f0, f1, int(TAXA * segundos))) / TAXA
    return sum(np.sin(h * fase) / h for h in range(1, harmonicos + 1))


def coro(notas, segundos, vibrato=5.0):
    """Vozes em "ahh": harmônicos moldados pelos formantes da vogal A, com vibrato leve."""
    t = tempo(segundos)
    saida = np.zeros(len(t))
    for k, f in enumerate(notas):
        fase = 2 * np.pi * np.cumsum(f * (1 + 0.006 * np.sin(2 * np.pi * (vibrato + k * 0.3) * t + k))) / TAXA
        for h in range(1, int(9000 / f) + 1):
            fh = h * f
            peso = (np.exp(-((fh - 700) / 250) ** 2) + 0.6 * np.exp(-((fh - 1200) / 300) ** 2)
                    + 0.25 * np.exp(-((fh - 2600) / 400) ** 2) + 0.04)
            saida += np.sin(h * fase) * peso
    return saida


# ---------------- os sons ----------------
SONS = {
    # revisados (Parte 2): botão de pedra; tique de madeira (também marca cada rodada)
    "clique": lambda: juntar(estalo(0.006, 2500) * 0.7, seno(880, 0.06) * decaimento(int(TAXA * 0.06), 8) * 0.6,
                             seno(440, 0.08) * decaimento(int(TAXA * 0.08), 7) * 0.4, baque(0.05, 200, 120, 8) * 0.4),
    "navegar": lambda: juntar(faixa(ruido(0.025), 900, 3000) * decaimento(int(TAXA * 0.025), 9) * 0.6,
                              seno(620, 0.045) * decaimento(int(TAXA * 0.045), 9) * 0.5),
    "voltar": lambda: varredura(900, 420, 0.08) * decaimento(int(TAXA * 0.08), 3),
    # revisados: carne (tac + grave que despenca + estofo); crítico = mais pesado, osso estalando e lâmina cantando
    "golpe": lambda: eco(juntar(estalo(0.01, 1800) * 0.9, baque(0.18, 150, 48, 9) * 1.1,
                                faixa(ruido(0.12), 250, 1400) * decaimento(int(TAXA * 0.12), 9) * 1.4,
                                atrasar(grave(ruido(0.08), 0.05) * decaimento(int(TAXA * 0.08), 6) * 2, 0.01)), 0.35, 0.12),
    "critico": lambda: eco(juntar(estalo(0.015, 1500) * 1.2, baque(0.32, 190, 40, 7) * 1.3,
                                  faixa(ruido(0.2), 200, 1800) * decaimento(int(TAXA * 0.2), 7) * 1.6,
                                  atrasar(agudo(ruido(0.03), 3000) * decaimento(int(TAXA * 0.03), 6) * 0.8, 0.03),
                                  atrasar(metal([1320, 1873, 2410, 3170], 0.6, 5) * 0.25, 0.01)), 0.7, 0.22),
    # revisado: escudo de ferro (modos de metal + baque surdo)
    "bloqueio": lambda: eco(juntar(estalo(0.008, 2000), metal([523, 797, 1171, 1649, 2311], 0.45, 7) * 0.55,
                                   baque(0.12, 120, 70, 8) * 0.8), 0.5, 0.18),
    "magia": lambda: juntar(varredura(260, 1250, 0.32) * envelope(int(TAXA * 0.32), 0.05, 0.15) * 0.6,
                            ruido(0.32) * envelope(int(TAXA * 0.32), 0.1, 0.2) * 0.08),
    # revisado: ar cortado + pano esvoaçando
    "esquiva": lambda: juntar(sopro(0.24, 500, 1600, 0.7) * 2.2,
                              faixa(ruido(0.2), 200, 900) * (0.6 + 0.4 * seno(28, 0.2)) * np.hanning(int(TAXA * 0.2)) * 0.6),
    # revisado: sinos subindo sobre um acorde morno, com eco de capela
    "cura": lambda: eco(juntar(em_sequencia([523, 659, 784, 1047], 0.5, 0.07, 5) * 0.5,
                               sum(seno(f, 0.6) for f in (262, 392, 523)) * envelope(int(TAXA * 0.6), 0.12, 0.35) * 0.18,
                               sopro(0.5, 1500, 4000, 0.3) * 0.25), 0.8, 0.25),
    # revisado: serve para bênçãos e maldições, então é neutro: brilho em quinta que desce + pulso surdo
    "status": lambda: eco(juntar((varredura(660, 494, 0.36) + varredura(990, 741, 0.36) * 0.5)
                                 * (0.75 + 0.25 * seno(12, 0.36)) * envelope(int(TAXA * 0.36), 0.02, 0.22) * 0.35,
                                 faixa(ruido(0.36), 1200, 4000) * envelope(int(TAXA * 0.36), 0.08, 0.25) * 0.5,
                                 baque(0.15, 110, 70, 6) * 0.45), 0.5, 0.2),
    # revisado: gemido que cai + último suspiro + corpo batendo no chão
    "morte": lambda: eco(juntar(faixa(serrote(170, 60, 0.6), 150, 1100) * (0.8 + 0.2 * seno(7, 0.6))
                                * envelope(int(TAXA * 0.6), 0.04, 0.35) * 0.9,
                                atrasar(faixa(ruido(0.35), 500, 2200) * envelope(int(TAXA * 0.35), 0.03, 0.3) * 0.35, 0.3),
                                atrasar(juntar(baque(0.25, 110, 40, 6) * 1.2,
                                               grave(ruido(0.2), 0.06) * decaimento(int(TAXA * 0.2), 6) * 2.5), 0.5)), 0.9, 0.25),
    "invocar": lambda: juntar(seno(110, 0.6) + seno(164.8, 0.6) * 0.7,
                              grave(ruido(0.6), 0.1)) * np.hanning(int(TAXA * 0.6)),
    "item": lambda: sino([2093, 3136], 0.18, 9) * 0.7,
    "moeda": lambda: juntar(sino([1760, 2640], 0.12, 9), np.concatenate([np.zeros(int(TAXA * 0.07)),
                                                                          sino([2349, 3520], 0.14, 9)])),
    "conquista": lambda: em_sequencia([523, 659, 784, 1047], 0.5, 0.09, 4) * 0.6,
    "vitoria": lambda: em_sequencia([220, 277, 330, 440], 0.7, 0.14, 3) * 0.7,
    "derrota": lambda: em_sequencia([330, 262, 196], 0.9, 0.22, 2) * 0.7,
    "erro": lambda: juntar(seno(150, 0.16), seno(159, 0.16)) * decaimento(int(TAXA * 0.16), 4) * 0.6,
    # ---------------- fase 3: elementos, raças e acampamento ----------------
    "elemento_fogo": lambda: juntar(grave(ruido(0.35), 0.25) * envelope(int(TAXA * 0.35), 0.03, 0.2) * 1.4,
                                    estalos(0.35, 9) * 0.6, seno(90, 0.2) * decaimento(int(TAXA * 0.2), 6)),
    "elemento_gelo": lambda: juntar(sino([2637, 3520, 4186, 5274], 0.4, 10) * 0.6,
                                    (ruido(0.12) - grave(ruido(0.12), 0.4)) * decaimento(int(TAXA * 0.12), 8)),
    "elemento_raio": lambda: juntar(np.sign(seno(70, 0.25)) * ruido(0.25) * decaimento(int(TAXA * 0.25), 7),
                                    varredura(2400, 300, 0.25) * decaimento(int(TAXA * 0.25), 5) * 0.5),
    "elemento_veneno": lambda: borbulhas(0.4) * 0.8,
    "elemento_luz": lambda: eco(juntar(metal([1568, 2349, 3136, 3951], 0.4, 6) * 0.4, estalo(0.01, 4000) * 0.5,
                                       em_sequencia([1319, 1760, 2637], 0.3, 0.035, 7) * 0.5,
                                       varredura(700, 2200, 0.18) * envelope(int(TAXA * 0.18), 0.01, 0.12) * 0.25), 0.6, 0.25),
    "elemento_sombra": lambda: juntar(varredura(180, 60, 0.45) * envelope(int(TAXA * 0.45), 0.05, 0.3),
                                      grave(ruido(0.45), 0.04) * envelope(int(TAXA * 0.45), 0.1, 0.3) * 2),
    "fraco": lambda: juntar(em_sequencia([880, 1319], 0.25, 0.05, 8) * 0.7, grave(ruido(0.1), 0.2) * 1.5),
    "resistente": lambda: juntar(seno(110, 0.15), seno(118, 0.15)) * decaimento(int(TAXA * 0.15), 5) * 0.8,
    "nivel": lambda: em_sequencia([523, 659, 784, 1047, 1319], 0.45, 0.07, 4) * 0.6,
    "renascer": lambda: juntar(varredura(80, 400, 0.7) * np.linspace(0, 1, int(TAXA * 0.7)) ** 2 * 0.7,
                               np.concatenate([np.zeros(int(TAXA * 0.55)), sino([659, 988, 1319], 0.6, 4) * 0.6])),
    "metamorfose": lambda: rugido(0.9, 70) * 1.2,
    "rugido": lambda: rugido(1.2, 55),
    "pagina": lambda: (grave(ruido(0.12), 0.5) - grave(ruido(0.12), 0.1)) * np.hanning(int(TAXA * 0.12)) * 1.5,
    "bau": lambda: juntar(rangido(0.35), np.concatenate([np.zeros(int(TAXA * 0.3)), sino([392, 523], 0.2, 12) * 0.6])),
    # ---------------- sons de ATAQUE (tocam quando o golpe é lançado) ----------------
    "ataque_fogo": lambda: juntar(sopro(0.75, 300, 1400, 0.9) * 2.5,
                                  grave(ruido(0.75), 0.15) * envelope(int(TAXA * 0.75), 0.15, 0.4) * 1.6,
                                  estalos(0.75, 14) * 0.5, seno(70, 0.75) * envelope(int(TAXA * 0.75), 0.1, 0.5) * 0.5),
    "ataque_trovao": lambda: juntar(agudo(ruido(0.12), 1500) * decaimento(int(TAXA * 0.12), 9) * 0.9,
                                    np.concatenate([np.zeros(int(TAXA * 0.05)), estrondo(1.4, 2.6)]),
                                    np.sign(seno(55, 0.3)) * ruido(0.3) * decaimento(int(TAXA * 0.3), 10) * 0.6),
    "ataque_gelo": lambda: juntar(sum(seno(f, 0.6) * (0.6 + 0.4 * seno(11 + i, 0.6)) for i, f in enumerate((2093, 2637, 3136, 3951)))
                                  * envelope(int(TAXA * 0.6), 0.25, 0.2) * 0.25,
                                  np.concatenate([np.zeros(int(TAXA * 0.5)), agudo(ruido(0.12), 3000) * decaimento(int(TAXA * 0.12), 12)]),
                                  sopro(0.6, 2000, 5000, 0.4) * 0.8),
    "ataque_veneno": lambda: juntar(borbulhas(0.55) * 0.9, agudo(ruido(0.55), 4000) * envelope(int(TAXA * 0.55), 0.05, 0.3) * 0.4,
                                    sopro(0.4, 500, 900, 0.6)),
    "ataque_luz": lambda: eco(juntar(coro([262, 330, 392, 523], 0.9) * envelope(int(TAXA * 0.9), 0.12, 0.45) * 0.2,
                                     atrasar(em_sequencia([1568, 2093, 2637, 3136], 0.4, 0.045, 6) * 0.35, 0.08),
                                     sopro(0.7, 1500, 4500, 0.4) * 0.5), 0.9, 0.3),
    "ataque_sombra": lambda: juntar(sopro(0.8, 900, 120, 0.8) * 2.2,
                                    (seno(73, 0.8) + seno(77.8, 0.8) + seno(110, 0.8) * 0.5) * envelope(int(TAXA * 0.8), 0.3, 0.3) * 0.5),
    "ataque_espada": lambda: juntar(sopro(0.3, 600, 2800, 0.6) * 2.4, atrasar(sopro(0.12, 2800, 1400, 0.5), 0.24),
                                    faixa(ruido(0.3), 150, 500) * np.hanning(int(TAXA * 0.3)) * 0.8,
                                    atrasar(metal([2400, 3610, 4730], 0.35, 9) * 0.12, 0.16)),
    "ataque_lamina": lambda: juntar(sopro(0.14, 1500, 5000, 0.5) * 2.4, atrasar(sopro(0.08, 4000, 2000, 0.4) * 0.8, 0.12),
                                    atrasar(metal([3100, 4650], 0.15, 14) * 0.1, 0.1)),
    "ataque_impacto": lambda: juntar(sopro(0.4, 200, 700, 0.8) * 2.6, seno(60, 0.4) * envelope(int(TAXA * 0.4), 0.2, 0.15) * 0.4),
    "ataque_flecha": lambda: juntar(corda(110, 0.4, 0.9) * 1.1, baque(0.08, 140, 90, 7) * 0.5,
                                    atrasar(sopro(0.32, 3200, 1400, 0.5) * 1.6 * (0.75 + 0.25 * seno(60, 0.32)), 0.04)),
    "ataque_soco": lambda: juntar(sopro(0.14, 400, 1200, 0.7) * 2.0, np.concatenate([np.zeros(int(TAXA * 0.1)),
                                                                                      seno(90, 0.12) * decaimento(int(TAXA * 0.12), 8)])),
    "ataque_garra": lambda: juntar(*(atrasar(sopro(0.11, 900 + k * 200, 4200, 0.7) * 2.0 * (0.6 + 0.4 * np.abs(seno(85 + k * 20, 0.11))),
                                             k * 0.055) for k in range(3)),
                                   grave(ruido(0.3), 0.08) * envelope(int(TAXA * 0.3), 0.02, 0.2) * (0.7 + 0.3 * seno(30, 0.3)) * 1.4),
    "ataque_musica": lambda: juntar(*(np.concatenate([np.zeros(int(TAXA * k * 0.035)), corda(f, 0.8, 0.5)])
                                      for k, f in enumerate((196, 247, 294, 392)))),
    "ataque_explosao": lambda: juntar(estrondo(1.0, 1.4), agudo(ruido(0.2), 800) * decaimento(int(TAXA * 0.2), 8) * 1.5,
                                      varredura(160, 40, 0.5) * decaimento(int(TAXA * 0.5), 4)),
    "ataque_cura": lambda: juntar(*(np.concatenate([np.zeros(int(TAXA * k * 0.07)), corda(f, 0.9, 0.3) * 0.7])
                                    for k, f in enumerate((523, 659, 784, 1047))), sopro(0.6, 2000, 4000, 0.3) * 0.3),
    "ataque_bencao": lambda: juntar(em_sequencia([784, 988, 1175], 0.6, 0.06, 4) * 0.5,
                                    sum(seno(f, 0.8) for f in (392, 494, 587)) * envelope(int(TAXA * 0.8), 0.2, 0.4) * 0.2),
    "ataque_maldicao": lambda: juntar(varredura(400, 180, 0.7) * (0.6 + 0.4 * seno(8, 0.7)) * envelope(int(TAXA * 0.7), 0.05, 0.3),
                                      varredura(424, 190, 0.7) * envelope(int(TAXA * 0.7), 0.05, 0.3) * 0.7),
}


def salvar(nome, sinal):
    sinal = np.asarray(sinal, dtype=float)
    pico = np.max(np.abs(sinal)) or 1.0
    sinal = sinal / pico * 0.8
    sinal = sinal[:np.nonzero(np.abs(sinal) > 0.003)[0][-1] + 1]          # corta o silêncio do fim do eco
    sinal = sinal * envelope(len(sinal), 0.002, 0.01)
    dados = (sinal * 32767).astype(np.int16)
    with wave.open(os.path.join(PASTA, nome + ".wav"), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(dados.tobytes())


def main():
    os.makedirs(PASTA, exist_ok=True)
    nomes = sys.argv[1:] or list(SONS)
    for nome in nomes:
        salvar(nome, SONS[nome]())
    print(f"{len(nomes)} sons gerados em {PASTA}")


if __name__ == "__main__":
    main()
