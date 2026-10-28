"""Confere músicas e efeitos sem precisar ouvir: pico, volume por trecho, emenda do loop e espectrograma.

    python ferramentas/analisar_audio.py saida.png arquivo.wav [outro.wav ...]
"""
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw


def ler(caminho):
    with wave.open(caminho) as f:
        taxa = f.getframerate()
        dados = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    return dados, taxa


def espectrograma(dados, taxa, largura=900, altura=180):
    """Imagem tempo x frequência (escala log), mais claro = mais forte."""
    janela = 2048
    passo = max(1, (len(dados) - janela) // largura)
    colunas = []
    for i in range(largura):
        trecho = dados[i * passo:i * passo + janela]
        if len(trecho) < janela:
            trecho = np.pad(trecho, (0, janela - len(trecho)))
        colunas.append(np.abs(np.fft.rfft(trecho * np.hanning(janela))))
    m = np.array(colunas).T                                             # (freq, tempo)
    freqs = np.fft.rfftfreq(janela, 1 / taxa)
    linhas = np.geomspace(40, taxa / 2, altura)
    idx = np.clip(np.searchsorted(freqs, linhas), 0, len(freqs) - 1)
    m = 20 * np.log10(m[idx] + 1e-6)
    m = np.clip((m - m.max() + 70) / 70, 0, 1)[::-1]
    cor = np.stack([m ** 0.6 * 255, m ** 1.2 * 200, m ** 2.2 * 255], -1).astype(np.uint8)
    return Image.fromarray(cor, "RGB")


def main():
    saida, arquivos = sys.argv[1], sys.argv[2:]
    imagens = []
    for caminho in arquivos:
        dados, taxa = ler(caminho)
        n = int(taxa * 5)
        rms = [float(np.sqrt(np.mean(dados[i:i + n] ** 2))) for i in range(0, len(dados) - n + 1, n)]
        salto = abs(float(dados[-1]) - float(dados[0]))
        print(f"{caminho.split(chr(92))[-1]:28s} {len(dados) / taxa:5.1f}s  pico {np.max(np.abs(dados)):.2f}  "
              f"volume por 5 s: {' '.join(f'{r:.2f}' for r in rms)}  emenda {salto:.3f}")
        img = espectrograma(dados, taxa)
        ImageDraw.Draw(img).text((4, 2), caminho.split("\\")[-1], fill=(255, 255, 255))
        imagens.append(img)
    folha = Image.new("RGB", (900, 184 * len(imagens)), (10, 8, 12))
    for k, img in enumerate(imagens):
        folha.paste(img, (0, k * 184))
    folha.save(saida)


if __name__ == "__main__":
    main()
