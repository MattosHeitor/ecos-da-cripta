"""Etapa 5: o acampamento novo (cena noturna, nomes só no destaque, teclado e atalhos)."""

import pygame

from test_telas_fluxo import app, quadros, tecla  # noqa: F401  (fixture e ajudantes)


def abrir_acampamento(app):  # noqa: F811
    from telas.acampamento import TelaAcampamento
    tela = TelaAcampamento(app)
    app.trocar(tela)
    quadros(app, 3)
    return tela


def test_atalhos_de_1_a_8_abrem_cada_personagem(app):  # noqa: F811
    esperado = {"1": "TelaEspelho", "3": "TelaBestiario", "4": "TelaTaverna", "5": "TelaCapitao",
                "6": "TelaMagoAnciao", "7": "TelaBau", "8": "TelaInventario"}
    for numero, nome in esperado.items():
        abrir_acampamento(app)
        tecla(app, getattr(pygame, f"K_{numero}"), numero)
        assert type(app.atual).__name__ == nome, numero


def test_mouse_em_cima_destaca_e_clique_abre(app):  # noqa: F811
    from telas.acampamento import NPCS
    tela = abrir_acampamento(app)
    assert tela.em_destaque is None                        # sem mouse em cima, nenhum nome aparece
    mago = next(p for p in NPCS if p.chave == "mago")
    centro = tela.area_do_ponto(mago).center
    quadros(app, 2, [pygame.event.Event(pygame.MOUSEMOTION, pos=centro, rel=(0, 0), buttons=(0, 0, 0))])
    assert tela.em_destaque == "mago"
    quadros(app, 2, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=centro, button=1)])
    assert type(app.atual).__name__ == "TelaMagoAnciao"


def test_setas_andam_pelos_personagens_e_enter_abre(app):  # noqa: F811
    tela = abrir_acampamento(app)
    vistos = set()
    for _ in range(12):
        tecla(app, pygame.K_RIGHT)
        if tela.em_destaque is not None:
            vistos.add(tela.em_destaque)
    assert len(vistos) >= 3                                 # passou por vários personagens
    for _ in range(12):                                     # (a última seta pode parar no botão Opções, no canto)
        if tela.em_destaque is not None:
            break
        tecla(app, pygame.K_LEFT)
    assert tela.em_destaque is not None
    tecla(app, pygame.K_RETURN)
    assert app.atual is not tela


def test_clicar_num_heroi_da_fogueira_abre_a_capita(app):  # noqa: F811
    from telas.acampamento import LUGARES
    from telas.comum import area_do_sprite, sprite_da_vaga
    tela = abrir_acampamento(app)
    vaga = tela.vagas()[0]
    pe, espelhar = LUGARES[0]
    centro = area_do_sprite(app.sprites, sprite_da_vaga(app.progresso, vaga), pe, 2, espelhar).center
    quadros(app, 2, [pygame.event.Event(pygame.MOUSEMOTION, pos=centro, rel=(0, 0), buttons=(0, 0, 0))])
    assert tela.em_destaque == ("heroi", 0)
    quadros(app, 2, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=centro, button=1)])
    assert type(app.atual).__name__ == "TelaCapitao"


def test_paisagem_e_luz_do_acampamento():
    from visual.acampamento_noturno import PaisagemNoturna, Iluminacao, Luz
    paisagem = PaisagemNoturna()
    assert set(paisagem.camadas) >= {"ceu", "montanhas", "colina", "floresta", "chao", "frente"}
    luz = Iluminacao()
    luz.luzes = [Luz(640, 540, 400, (255, 160, 90))]
    mapa = luz.mapa()
    perto, longe = mapa.get_at((640, 540)), mapa.get_at((40, 40))
    assert perto[0] > longe[0] + 60                          # perto do fogo é bem mais claro e quente
