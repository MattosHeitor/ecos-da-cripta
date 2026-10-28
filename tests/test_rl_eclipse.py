"""Fase 4, etapa 7: Catedral do Eclipse (Sombra do Herói, Bispo em 3 fases, Draconiano x Dragão, 7º golpe)."""

from roguelike.classes import criar_heroi
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item
from roguelike.piloto_automatico import grupo_padrao
from roguelike.progresso import Progresso
from roguelike.regioes import regiao

from apoio_roguelike import combate_pronto
from test_rl_run import run_de_teste


def test_catedral_do_eclipse_e_um_final_alternativo():
    eclipse = regiao("catedral_do_eclipse")
    assert eclipse.disponivel and eclipse.final and eclipse.chefe == "bispo_eclipsado"


def test_vencer_o_bispo_vence_a_run():
    run = run_de_teste()
    run.regiao_atual = "catedral_do_eclipse"
    run.area = run.areas_da_regiao()
    run.encontro = run.opcoes_de_encontro()[0]
    combate = run.criar_combate(run.encontro)
    for _ in range(6):                                   # as fases seguram a vida: bate até tudo cair
        for inimigo in list(combate.inimigos):
            combate.causar_dano(inimigo, 99999, run.grupo.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    run.concluir_encontro()
    assert run.resultado == "vitoria"


def test_sombra_copia_um_heroi_do_grupo():
    heroi = criar_heroi("guerreiro")
    sombra = criar_inimigo("sombra_do_heroi")
    combate_pronto([heroi], [sombra])
    assert sombra.sombra_de == heroi.nome and sombra.sprite == heroi.sprite
    assert heroi.nome in sombra.nome
    assert set(heroi.golpes.equipados[:2]) <= set(sombra.niveis_habilidade)


def test_bispo_vira_vitral_invoca_sombras_e_depois_dragao():
    herois = [criar_heroi("guerreiro"), criar_heroi("mago")]
    bispo = criar_inimigo("bispo_eclipsado")
    combate = combate_pronto(herois, [bispo])
    combate.causar_dano(bispo, 99999, herois[0])
    assert bispo.sprite == "bispo_eclipsado_vitral"
    sombras = combate.invocacoes_de(bispo)
    assert len(sombras) == 2 and all(getattr(s, "sombra_de", None) for s in sombras)
    combate.causar_dano(bispo, 99999, herois[0])
    assert bispo.sprite == "dragao_do_eclipse" and "sopro_do_eclipse" in bispo.niveis_habilidade


def test_draconiano_transformado_fere_mais_o_dragao():
    heroi = criar_heroi("guerreiro")
    bispo = criar_inimigo("bispo_eclipsado")
    combate = combate_pronto([heroi], [bispo])
    combate.aplicar_status(bispo, "fase_do_chefe", valor=3)
    normal = combate.causar_dano(bispo, 10, heroi)
    combate.aplicar_status(heroi, "forma_de_dragao", duracao=3)
    assert combate.causar_dano(bispo, 10, heroi) > normal


def test_grimorio_sem_nome_da_o_setimo_golpe_e_devolve_ao_tirar():
    heroi = criar_heroi("mago")
    base = heroi.golpes.espacos()
    heroi.equipar(item("grimorio_sem_nome"))
    assert heroi.golpes.espacos() == base + 1
    while len(heroi.golpes.equipados) < base + 1:
        heroi.golpes.equipados.append(f"falso{len(heroi.golpes.equipados)}")
    heroi.desequipar("arma_secundaria")
    assert len(heroi.golpes.equipados) == base


def test_vencer_o_bispo_libera_as_lendarias_anas():
    progresso = Progresso()
    progresso.conquistas.add("chefe:bispo_eclipsado")
    run = progresso.criar_run(grupo_padrao(("guerreiro",)), "ECLIPSE")
    assert {"lamina_do_alvorecer", "grimorio_sem_nome"} <= run.descobertas
