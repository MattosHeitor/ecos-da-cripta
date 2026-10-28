"""O ícone do jogo em pixel art, gerado por código (como as forjas): uma caveira dentro do arco de uma cripta, com
duas velas, brilho roxo e pedra de tijolos com filete dourado.

    python ferramentas/gerar_icone.py        -> assets/icone/ (icone_32.png da janela, icone_256.png e o .ico)

Cada tamanho pequeno é desenhado no próprio grid (16, 24 e 32 pixels, com menos detalhe nos menores); os grandes
são o de 32 ampliado sem suavizar (64, 128, 256), para continuar pixel art. O .ico leva todos (16 a 256).
"""

import math
import os
import sys

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "assets", "icone")
NOME_DO_ICO = "ecos_da_cripta.ico"
TAMANHOS_DO_ICO = (16, 24, 32, 48, 64, 128, 256)

COR = {
    "contorno": (14, 8, 18),
    "pedra_escura": (56, 48, 72), "pedra": (86, 78, 104), "pedra_clara": (116, 108, 134),
    "ouro": (230, 182, 80), "ouro_escuro": (156, 106, 42),
    "fundo": (22, 12, 32), "brilho": (78, 40, 120), "brilho_claro": (128, 78, 182),
    "osso": (234, 222, 194), "osso_sombra": (178, 160, 134), "osso_escuro": (96, 74, 70),
    "olho_fundo": (40, 14, 34), "olho": (255, 210, 100),
    "vela": (238, 228, 206), "vela_sombra": (186, 172, 148), "chama": (255, 236, 150), "chama_fora": (242, 140, 48),
}


# ---------------- formas (no espaço de 32x32; u, v = centro do pixel) ----------------
def no_arco(u, v, raio, esquerda, direita, base, centro_y=13.0):
    if v < centro_y:
        return (u - 16) ** 2 + (v - centro_y) ** 2 <= raio ** 2
    return esquerda <= u <= direita and v <= base


def no_arco_de_fora(u, v):
    degrau = 27.4 <= v <= 30.6 and 1.4 <= u <= 30.6                  # a soleira, mais larga
    return no_arco(u, v, 12.6, 3.4, 28.6, 29.6) or degrau


def no_arco_de_dentro(u, v, folga=0.0):
    return no_arco(u, v, 9.4 + folga, 6.6 - folga, 25.4 + folga, 27.4 + folga * 0.4)


def no_cranio(u, v):
    return ((u - 16) / 5.6) ** 2 + ((v - 14.4) / 5.3) ** 2 <= 1


def na_mandibula(u, v):
    if not (12.8 <= u <= 19.2 and 18.2 <= v <= 22.4):
        return False
    return not ((u < 13.8 or u > 18.2) and v > 21.4)                  # cantos arredondados


def no_olho(u, v, meia_largura=1.7, meia_altura=1.5):
    """O olho esquerdo (u já espelhado: o direito é o reflexo)."""
    return abs(u - CENTRO_DO_OLHO) <= meia_largura and abs(v - 15.4) <= meia_altura


CENTRO_DO_OLHO = 13.4
CENTRO_DA_VELA = 8.0


def cor_da_pedra(x, y, detalhe):
    """Tijolos com argamassa (só nos tamanhos com detalhe)."""
    if not detalhe:
        return "pedra"
    linha = y // 3
    if y % 3 == 0:
        return "pedra_escura"
    if (x + (linha % 2) * 3) % 6 == 0:
        return "pedra_escura"
    return "pedra_clara" if (linha + (x + (linha % 2) * 3) // 6) % 3 == 0 else "pedra"


def cor_do_fundo(u, v, x, y):
    """O escuro de dentro da cripta, com o brilho roxo atrás da caveira (borda pontilhada, como pixel art)."""
    distancia = math.hypot(u - 16, v - 16.5)
    if v > 25.6:
        return "pedra_escura"                                         # o chão
    if distancia < 5.0:
        return "brilho_claro"
    if distancia < 6.0:
        return "brilho_claro" if (x + y) % 2 == 0 else "brilho"
    if distancia < 8.2:
        return "brilho"
    if distancia < 9.2:
        return "brilho" if (x + y) % 2 == 0 else "fundo"
    return "fundo"


def cor_da_vela(u, v, lado_de_fora):
    """A vela da esquerda (u espelhado), com a chama em cima (None: fora dela). lado_de_fora: o pixel mais perto da
    parede (a sombra da cera fica do lado de dentro)."""
    perto = abs(u - CENTRO_DA_VELA) <= 0.7
    if perto and 22.0 <= v <= 27.4:
        return "vela" if lado_de_fora else "vela_sombra"
    if 18.0 <= v < 19.0 and CENTRO_DA_VELA <= u <= CENTRO_DA_VELA + 0.8:
        return "chama_fora"                                           # a ponta
    if perto and 19.0 <= v < 20.0:
        return "chama_fora" if lado_de_fora else "chama"
    if perto and 20.0 <= v < 21.0:
        return "chama"
    if perto and 21.0 <= v < 22.0:
        return "chama_fora"
    return None


def cor_da_caveira(u, espelho, v, tamanho):
    """A caveira: as formas usam u espelhado (simétrica); a sombra usa o u de verdade (luz de cima à esquerda)."""
    if no_cranio(espelho, v) or na_mandibula(espelho, v):
        if no_olho(espelho, v):
            miolo = abs(espelho - CENTRO_DO_OLHO) <= (0.6 if tamanho >= 24 else 1.0) and abs(v - 15.6) <= 0.7
            return "olho" if miolo else "olho_fundo"
        if espelho >= 15.1 and 18.0 <= v <= 19.3:
            return "osso_escuro"                                      # o nariz
        if na_mandibula(espelho, v) and 20.2 <= v <= 20.9 and espelho >= 13.5:
            return "osso_escuro"                                      # a linha dos dentes
        if na_mandibula(espelho, v) and tamanho >= 24 and 20.9 < v <= 21.9 and espelho >= 13.5 and int(u) % 2 == 0:
            return "osso_escuro"                                      # os vãos entre os dentes
        sombra = (u - 16) * 0.55 + (v - 14.4) > 3.4 or (na_mandibula(espelho, v) and u > 18.0)
        return "osso_sombra" if sombra else "osso"
    return None


# ---------------- o de 16 pixels, à mão (a forma calculada não cabe em 16) ----------------
LETRAS = {"K": "contorno", "S": "pedra", "s": "pedra_escura", "G": "ouro", "g": "ouro_escuro", "D": "fundo",
          "P": "brilho", "Q": "brilho_claro", "B": "osso", "b": "osso_sombra", "d": "osso_escuro", "E": "olho"}
DESENHO_16 = [
    "......KKKK......",
    "....KKSGGSKK....",
    "...KSSgGGgSSK...",
    "..KSSGDDDDGSSK..",
    "..KSGDDPPDDGSK..",
    ".KSGDPBBBBPDGSK.",
    ".KSGPBBBBBBPGSK.",
    ".KSGPBEBBEBPGSK.",
    ".KSGPBBddBbPGSK.",
    ".KSGPQBBBbQPGSK.",
    ".KSGDPdBdbPDGSK.",
    ".KSGDDPPPPDDGSK.",
    ".KSGDDDDDDDDGSK.",
    ".KSGssssssssGSK.",
    "KSSSSSSSSSSSSSSK",
    "KKKKKKKKKKKKKKKK",
]


def desenhar_16():
    imagem = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pixels = imagem.load()
    for y, linha_do_desenho in enumerate(DESENHO_16):
        for x, letra in enumerate(linha_do_desenho):
            if letra in LETRAS:
                pixels[x, y] = COR[LETRAS[letra]] + (255,)
    return imagem


# ---------------- o ícone ----------------
def desenhar(tamanho):
    """O ícone desenhado num grid de 'tamanho' pixels (16 à mão; 24 e 32 calculados)."""
    if tamanho == 16:
        return desenhar_16()
    escala = tamanho / 32
    detalhe = tamanho >= 24
    nomes = [[None] * tamanho for _ in range(tamanho)]
    for y in range(tamanho):
        for x in range(tamanho):
            u, v = (x + 0.5) / escala, (y + 0.5) / escala
            espelho = min(u, 32 - u)                                  # o pixel x e o (tamanho-1-x) caem no mesmo
            if not no_arco_de_fora(u, v):
                continue
            if abs(u - 16) + abs(v - 2.0) <= 2.4:
                nome = "ouro" if abs(u - 16) + abs(v - 2.0) <= 1.4 else "ouro_escuro"   # a pedra-chave
            elif no_arco_de_dentro(u, v):
                nome = cor_da_caveira(u, espelho, v, tamanho)
                if nome is None and detalhe:
                    nome = cor_da_vela(espelho, v, lado_de_fora=espelho < CENTRO_DA_VELA)
                if nome is None:
                    nome = cor_do_fundo(u, v, x, y)
            elif no_arco_de_dentro(u, v, folga=1.0 / escala if not detalhe else 1.0):
                nome = "ouro"                                         # o filete dourado na boca do arco
            else:
                nome = cor_da_pedra(x, y, detalhe)
            nomes[y][x] = nome
    imagem = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    pixels = imagem.load()
    for y in range(tamanho):
        for x in range(tamanho):
            if nomes[y][x] is not None:
                pixels[x, y] = COR[nomes[y][x]] + (255,)
            elif any(0 <= x + dx < tamanho and 0 <= y + dy < tamanho and nomes[y + dy][x + dx] is not None
                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                pixels[x, y] = COR["contorno"] + (255,)              # o contorno escuro em volta
    return imagem


def ampliar(imagem, tamanho):
    """Ampliação sem suavizar (pixel art)."""
    return imagem.resize((tamanho, tamanho), Image.NEAREST)


def todos_os_tamanhos():
    """{tamanho: imagem} para o .ico: 16, 24 e 32 desenhados; o resto ampliado do 24 ou do 32."""
    proprios = {t: desenhar(t) for t in (16, 24, 32)}
    imagens = dict(proprios)
    imagens[48] = ampliar(proprios[24], 48)
    for tamanho in (64, 128, 256):
        imagens[tamanho] = ampliar(proprios[32], tamanho)
    return imagens


def gerar(pasta=PASTA):
    """Grava icone_32.png (janela), icone_256.png e o .ico com todos os tamanhos. Devolve os caminhos."""
    os.makedirs(pasta, exist_ok=True)
    imagens = todos_os_tamanhos()
    caminhos = {"janela": os.path.join(pasta, "icone_32.png"), "grande": os.path.join(pasta, "icone_256.png"),
                "ico": os.path.join(pasta, NOME_DO_ICO)}
    imagens[32].save(caminhos["janela"])
    imagens[256].save(caminhos["grande"])
    maior = imagens[256]
    maior.save(caminhos["ico"], format="ICO", sizes=[(t, t) for t in TAMANHOS_DO_ICO],
               append_images=[imagens[t] for t in TAMANHOS_DO_ICO if t != 256])
    return caminhos


if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else PASTA
    for nome, caminho in gerar(destino).items():
        print(f"{nome}: {caminho}")
