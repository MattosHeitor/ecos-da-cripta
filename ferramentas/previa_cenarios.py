"""Prévia dos cenários como o jogo desenha (camadas, luzes, partículas, névoa e paleta da fase).

    python previa_cenarios.py saida.png cena:variante:fase ...    ex.: cidadela_congelada:0:cidadela_congelada
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from visual.cenario_macabro import CenarioMacabro, paleta_do_lugar  # noqa: E402


def foto(nome, variante, fase, segundos=2.0):
    cena = CenarioMacabro(nome, variante, 1280, 720, 1.0, paleta_do_lugar(fase) if fase else None)
    for _ in range(int(segundos * 30)):
        cena.atualizar(1 / 30)
    tela = pygame.Surface((1280, 720))
    cena.desenhar(tela)
    cena.desenhar_frente(tela)
    return tela


def main():
    saida, pedidos = sys.argv[1], sys.argv[2:]
    fotos = []
    for pedido in pedidos:
        nome, variante, *fase = pedido.split(":")
        fotos.append(foto(nome, int(variante), fase[0] if fase and fase[0] else None))
    colunas = 2
    folha = pygame.Surface((640 * colunas, 360 * ((len(fotos) + 1) // colunas)))
    for k, f in enumerate(fotos):
        folha.blit(pygame.transform.smoothscale(f, (640, 360)), ((k % colunas) * 640, (k // colunas) * 360))
    pygame.image.save(folha, saida)
    print("ok")


if __name__ == "__main__":
    main()
