"""Layout das telas: nada vaza da moldura, sai da tela, cruza com outra coisa ou é cortado com "...".

Abre todas as cenas de ferramentas/previa_telas.py (listas cheias, nomes longos, golpe novo pendente...)
sem janela e confere o que cada uma desenhou (ui/layout.py).
Também confere o painel rolável (ui/rolagem.py) e a navegação por teclado de TelaComBotoes.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ferramentas"))

import pygame  # noqa: E402

from ui.layout import conferir, colunas, linhas, grade, altura_da_grade  # noqa: E402
from ui.rolagem import PainelRolavel  # noqa: E402


def evento(tipo, **dados):
    return pygame.event.Event(tipo, **dados)


# ---------------- conferência de layout ----------------
def test_conferencia_acha_texto_vazando_e_saindo_da_tela():
    pygame.init()
    tela = pygame.Surface((1280, 720))
    registro = [("painel", pygame.Rect(10, 10, 100, 40), tela.get_clip(), tela, "ferro"),
                ("texto", pygame.Rect(20, 20, 150, 20), tela.get_clip(), tela, "comprido demais"),
                ("texto", pygame.Rect(1200, 700, 100, 30), tela.get_clip(), tela, "fora")]
    tipos = sorted(p.tipo for p in conferir(registro, tela))
    assert tipos == ["fora da tela", "vaza"]


def test_conferencia_aceita_o_que_o_recorte_esconde():
    pygame.init()
    tela = pygame.Surface((1280, 720))
    janela = pygame.Rect(10, 10, 100, 100)
    registro = [("painel", pygame.Rect(0, 0, 200, 200), tela.get_clip(), tela, "ferro"),
                ("texto", pygame.Rect(20, 400, 50, 20), janela, tela, "rolado para fora")]
    assert conferir(registro, tela) == []


def test_divisoes_do_layout_nao_se_cruzam():
    a, b, c = colunas(pygame.Rect(0, 0, 1000, 500), [200, None, 300], espaco=10)
    assert a.right + 10 == b.x and b.right + 10 == c.x and c.right == 1000
    cima, baixo = linhas(pygame.Rect(0, 0, 100, 300), [None, 50], espaco=10)
    assert cima.bottom + 10 == baixo.y and baixo.bottom == 300
    celulas = grade(pygame.Rect(0, 0, 210, 0), 5, colunas=2, altura=40, espaco=10)
    assert celulas[2].y == 50 and celulas[1].x == 110
    assert altura_da_grade(5, 2, 40, 10) == 140


# ---------------- painel rolável ----------------
def test_painel_rolavel_limita_mostra_e_responde_a_roda_e_as_teclas():
    pygame.init()
    tela = pygame.Surface((400, 400))
    painel = PainelRolavel(passo=50)
    painel.comecar(tela, pygame.Rect(0, 0, 200, 100), 500)
    painel.terminar(tela)
    assert painel.rola and painel.maximo == 400
    painel.rolar(10_000)
    assert painel.alvo == 400                                 # nunca passa do fim
    painel.ir_para(0, imediato=True)
    painel.mostrar(pygame.Rect(0, 300, 200, 40))              # item lá embaixo: rola até ele aparecer
    assert painel.alvo == 300 + 40 + 8 - 100
    assert painel.tecla(evento(pygame.KEYDOWN, key=pygame.K_HOME, mod=0)) and painel.alvo == 0
    assert painel.tecla(evento(pygame.KEYDOWN, key=pygame.K_END, mod=0)) and painel.alvo == 400


def test_painel_rolavel_recorta_o_desenho_na_janela():
    pygame.init()
    tela = pygame.Surface((400, 400))
    tela.fill((0, 0, 0))
    painel = PainelRolavel()
    y0 = painel.comecar(tela, pygame.Rect(10, 10, 100, 100), 50)
    tela.fill((255, 255, 255), (0, y0, 400, 400))             # pinta tudo: só a janela pode mudar
    painel.terminar(tela)
    assert tela.get_at((5, 50))[:3] == (0, 0, 0) and tela.get_at((50, 50))[:3] == (255, 255, 255)
    assert tela.get_clip() == tela.get_rect()                  # o recorte volta ao que era


def test_foco_do_teclado_rola_ate_o_botao_e_tab_troca_de_painel(tmp_path):
    from telas import comum
    from telas.base import App
    from roguelike.progresso import Progresso
    from ui.widgets import Botao

    class TelaDeTeste(comum.TelaComBotoes):
        def __init__(self, app):
            super().__init__(app)
            self.lista = PainelRolavel()

        def desenhar(self, tela):
            self.comecar_desenho(tela)
            with self.rolavel(self.lista, pygame.Rect(10, 10, 300, 200), 20 * 54) as y0:
                for i in range(20):
                    self.botao(Botao((10, y0 + i * 54, 280, 50), f"Item {i}", lambda: None))
            self.botao(Botao((400, 10, 200, 50), "Fora do painel", lambda: None))
            self.terminar_desenho(tela)

    app = App(janela=False)
    app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    tela = TelaDeTeste(app)
    app.trocar(tela)
    app.passo(0.1, [])
    for _ in range(12):                                       # desce 12 itens com a seta
        app.passo(0.1, [evento(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")])
    for _ in range(10):
        app.passo(0.1, [])
    focado = tela._botao_focado()
    assert focado is not None and focado.texto == "Item 11"
    assert tela.lista.visivel(focado.rect)                    # o painel rolou até o foco
    app.passo(0.1, [evento(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode="\t")])
    assert tela._botao_focado().texto == "Fora do painel"     # Tab: o outro grupo de botões


def test_clique_fora_da_janela_nao_aperta_botao_escondido(tmp_path):
    from ui.widgets import Botao
    botao = Botao((0, 300, 100, 40), "escondido", lambda: None)
    botao.recorte = pygame.Rect(0, 0, 200, 200)
    assert not botao.em_cima((10, 310))


# ---------------- arrastar e soltar (golpes) ----------------
def test_arrastar_o_golpe_novo_para_um_equipado_troca(tmp_path):
    import previa_telas
    from telas.base import App
    from telas.golpes import TelaGolpes
    from roguelike.progresso import Progresso
    app = App(janela=False)
    app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    heroi = previa_telas.heroi_com_golpe_novo(app)
    novo, primeiro = heroi.golpes.pendentes[0], heroi.golpes.equipados[0]
    tela = TelaGolpes(app, heroi, lambda: None)
    app.trocar(tela)
    for _ in range(3):
        app.passo(0.1, [])
    origem = next(r for r, tipo, _ in tela.alvos if tipo == "novo").center
    destino = next(r for r, tipo, chave in tela.alvos if tipo == "equipado" and chave == primeiro)
    alvo = (destino.centerx, destino.y + 20)                      # em cima da carta (longe do botão)
    app.passo(0.1, [evento(pygame.MOUSEBUTTONDOWN, pos=origem, button=1)])
    app.passo(0.1, [evento(pygame.MOUSEMOTION, pos=alvo, rel=(0, 0), buttons=(1, 0, 0))])
    assert tela.arrasto and tela.arrasto["ativo"]
    app.passo(0.1, [evento(pygame.MOUSEBUTTONUP, pos=alvo, button=1)])
    assert novo in heroi.golpes.equipados and primeiro in heroi.golpes.grimorio
    assert not heroi.golpes.pendentes


def test_arrastar_um_equipado_para_o_grimorio_guarda(tmp_path):
    import previa_telas
    from telas.base import App
    from telas.golpes import TelaGolpes
    from roguelike.progresso import Progresso
    app = App(janela=False)
    app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    heroi = previa_telas.heroi_com_golpe_novo(app)
    heroi.golpes.decidir(heroi.golpes.pendentes[0])               # sem golpe novo: só organizar
    guardado = heroi.golpes.equipados[1]
    tela = TelaGolpes(app, heroi, lambda: None)
    app.trocar(tela)
    for _ in range(3):
        app.passo(0.1, [])
    origem = next(r for r, tipo, chave in tela.alvos if tipo == "equipado" and chave == guardado)
    lista = next(r for r, tipo, _ in tela.alvos if tipo == "lista_grimorio")
    app.passo(0.1, [evento(pygame.MOUSEBUTTONDOWN, pos=(origem.centerx, origem.y + 20), button=1)])
    app.passo(0.1, [evento(pygame.MOUSEMOTION, pos=(lista.centerx, lista.bottom - 10), rel=(0, 0), buttons=(1, 0, 0))])
    app.passo(0.1, [evento(pygame.MOUSEBUTTONUP, pos=(lista.centerx, lista.bottom - 10), button=1)])
    assert guardado in heroi.golpes.grimorio and guardado not in heroi.golpes.equipados


# ---------------- todas as telas ----------------
def test_nenhuma_tela_vaza_corta_ou_sobrepoe():
    import previa_telas
    problemas, falhas = previa_telas.rodar_cenas()
    assert falhas == []
    com_problema = {nome: lista for nome, lista in problemas.items() if lista}
    assert com_problema == {}
