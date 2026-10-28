"""Reino dos Ratos, etapa 5R3: a Rainha dos Ratos refeita como coroa-ninho — a coroa presa no nó de caudas (com a
linha "exposto" e os olhos de quem espera lá dentro) e só os dois ratos da vez do lado de fora, de lado e presos pelo
rabo; quando a roda gira, um pula para dentro da coroa e o próximo pula para fora."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from roguelike.encontros import MontadorDeCombate
from roguelike.run import Run
from roguelike.classes import criar_heroi
from telas.combate.visual_roda import VisualRoda, VisualRatoDaRoda, LUGARES
from visual.sprites_macabros import Sprites

from test_telas_fluxo import app, quadros  # noqa: F401  (fixture e ajudantes)

RATOS = ("mordedor_da_rainha", "pestilento_da_rainha", "guincho_da_rainha", "curandeiro_da_rainha")


def test_sprites_da_coroa_e_dos_ratos_de_lado():
    sprites = Sprites()
    assert sprites.quadros_de("rainha_dos_ratos", "parado") == 6
    assert sprites.quadros_de("rainha_dos_ratos", "exposto") == 6
    for nome in RATOS:
        meta = sprites.meta(nome)
        assert sprites.quadros_de(nome, "correr") == 4 and sprites.tem_animacao(nome, "morte")
        assert meta["celula"][0] > meta["celula"][1] * 2                 # de lado (comprido), não visto de cima
        dx, dy = meta["rabo"]
        assert dx < 0 and dy < 0                                         # o toco do rabo fica atrás e acima dos pés


def tela_da_rainha(app):  # noqa: F811
    from telas.combate.tela import TelaCombate
    run = Run([criar_heroi(c) for c in ("guerreiro", "sacerdote", "mago")], "RAINHA", "reino_dos_ratos")
    total = run.areas_da_regiao()
    run.area = total
    run.encontro = MontadorDeCombate(run.regiao, total, run.rng("t"), 4, False, total).chefe()
    run.estado = "encontro"
    combate = run.criar_combate()
    rei = combate.inimigos[0]
    for _ in range(4):
        combate.causar_dano(rei, 9999, run.grupo.herois[0])
    for inimigo in list(combate.inimigos):
        combate.causar_dano(inimigo, 9999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    run.proxima_onda()
    tela = TelaCombate(app, run, run.encontro, lambda r: None)
    app.trocar(tela)
    quadros(app, 70)
    return tela


def ratos_de(tela):
    return [v for v in tela.lado_inimigos if isinstance(v, VisualRatoDaRoda)]


def test_so_os_dois_da_vez_ficam_do_lado_de_fora(app):  # noqa: F811
    tela = tela_da_rainha(app)
    coroa = next(v for v in tela.lado_inimigos if isinstance(v, VisualRoda))
    assert coroa.pronta() and "no_da_rainha" in tela.cenario.escondidas         # desceu do teto
    ratos = ratos_de(tela)
    fora = [v for v in ratos if v.lugar is not None]
    assert len(ratos) == 8 and len(fora) == 2 and all(v.viagem is None and v.alfa == 255 for v in fora)
    assert sorted((round(v.x), round(v.y)) for v in fora) == sorted(LUGARES)
    assert {v.lutador for v in fora} == set(coroa.lutador.frente(2)) and not any(v.atras() for v in fora)
    dentro = [v for v in ratos if v.dentro()]
    assert len(dentro) == 6 and all(v.alfa == 0 and v.atras() for v in dentro)  # os outros esperam na coroa
    assert all(v.tem_barra() for v in fora) and not any(v.tem_barra() for v in dentro)
    tela.desenhar(app.tela)


def test_a_roda_gira_um_entra_na_coroa_e_outro_sai(app):  # noqa: F811
    tela = tela_da_rainha(app)
    rainha = tela.combate.inimigos[0]
    antes = {v.lutador: v.lugar for v in ratos_de(tela) if v.lugar is not None}
    roda = next(p for p in rainha.passivas if hasattr(p, "proximo_giro"))
    roda.nova_rodada(rainha, tela.combate)
    app.passo(0.05, [])
    viajando = {v.viagem["tipo"] for v in ratos_de(tela) if v.viagem is not None}
    assert {"entra", "troca"} <= viajando
    tela.desenhar(app.tela)                                       # (no meio do pulo)
    quadros(app, 40)
    depois = {v.lutador: v.lugar for v in ratos_de(tela) if v.lugar is not None}
    assert set(depois) == set(rainha.frente(2)) and depois != antes
    assert all(v.viagem is None for v in ratos_de(tela))


def test_no_exposto_troca_a_linha_da_coroa(app):  # noqa: F811
    tela = tela_da_rainha(app)
    coroa = next(v for v in tela.lado_inimigos if isinstance(v, VisualRoda))
    assert not coroa.exposto()
    for rato in coroa.lutador.roda[1:8:2]:
        tela.combate.causar_dano(rato, 9999, tela.combate.herois[0])
    assert coroa.exposto()
    coroa.animador.anim = "parado"
    exposta = coroa.imagem_atual()
    assert exposta is coroa.sprites.quadro("rainha_dos_ratos", "exposto", int(coroa.tempo * 6) % 6, 2, False, None)


def test_rato_da_vez_afunda_na_agua_e_quem_pula_nao(app):  # noqa: F811
    tela = tela_da_rainha(app)
    fora = next(v for v in ratos_de(tela) if v.lugar is not None)
    dentro = next(v for v in ratos_de(tela) if v.dentro())
    assert not fora.no_ar and dentro.no_ar
    assert next(v for v in tela.lado_inimigos if isinstance(v, VisualRoda)).no_ar
