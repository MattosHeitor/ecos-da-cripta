"""As imagens do tutorial para os amigos (tutorial/imagens/*.jpg), tiradas das prévias das telas.

    python ferramentas/instalador/capturas_do_tutorial.py

Roda as cenas do previa_telas (sem janela, com nomes e IPs de exemplo: nada do seu PC aparece) e guarda as telas
que o tutorial mostra em 960x540, JPEG. Rode de novo quando essas telas mudarem; o construir.py só as embute.
"""

import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))

from PIL import Image  # noqa: E402

PASTA = os.path.join(AQUI, "tutorial", "imagens")
CENAS = ("titulo", "multijogador", "lobby", "mapa_votacao", "combate_em_grupo", "robustez")
# imagem do tutorial -> print da prévia
CAPTURAS = {
    "titulo": "titulo",
    "firewall": "aviso_do_firewall",
    "lobby_codigo": "lobby_vpn",
    "entrar": "multijogador",
    "mapa": "mapa_votacao",
    "combate": "combate_vez_da_bia",
    "voltar": "multijogador_com_partida_salva",
}
TAMANHO = (960, 540)


def main():
    import previa_telas
    with tempfile.TemporaryDirectory() as pasta:
        previa_telas.PASTA_ATUAL = pasta
        _, falhas = previa_telas.rodar_cenas(CENAS)
        if falhas:
            raise SystemExit(f"Cenas que falharam: {falhas}")
        os.makedirs(PASTA, exist_ok=True)
        for destino, origem in CAPTURAS.items():
            imagem = Image.open(os.path.join(pasta, origem + ".png")).convert("RGB").resize(TAMANHO, Image.LANCZOS)
            caminho = os.path.join(PASTA, destino + ".jpg")
            imagem.save(caminho, quality=84, optimize=True)
            print(f"{destino}.jpg ({os.path.getsize(caminho) // 1024} KB)")


if __name__ == "__main__":
    main()
