"""Reino dos Ratos, etapa 6B: o Senhor dos Ratos (classe secreta liberada ao vencer A Corte Completa): invocador e
amaldiçoador que chama ratos e moscas, espalha a Peste e drena vida; subclasses Rei dos Bandos, Senhor das Moscas e
Profeta da Praga."""

import json
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from roguelike.classes import criar_heroi, todas_as_classes, classes_liberadas
from roguelike.combate import Combate
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo, ficha_de_invocacao
from roguelike.progresso import Progresso, arvore_da_classe

from test_telas_fluxo import app, quadros  # noqa: F401  (fixture e ajudantes)

CORTE = "feito:corte_completa"
CATALOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sprites_macabros",
                        "catalogo.json")


def test_senhor_so_aparece_depois_da_corte_completa():
    senhor = todas_as_classes()["senhor_dos_ratos"]
    assert senhor.requer == CORTE and senhor.anuncio
    assert "senhor_dos_ratos" not in classes_liberadas({"chefe:rainha_dos_ratos", "chefe:rei_dos_ratos"})
    assert "senhor_dos_ratos" in classes_liberadas({CORTE})


def test_vencer_a_corte_anuncia_o_senhor_dos_ratos():
    progresso = Progresso()
    run = progresso.criar_run([criar_heroi("guerreiro")], "CORTE")
    run.estatisticas["chefes"] += ["rainha_dos_ratos", "rei_dos_ratos"]
    run.estatisticas["feitos"].append("corte_completa")
    run.resultado = "vitoria"
    relatorio = progresso.registrar_fim_de_run(run)
    assert relatorio.herois_novos == ["medico_da_peste", "senhor_dos_ratos"]


def test_senhor_tem_tudo_que_uma_classe_precisa():
    classe = todas_as_classes()["senhor_dos_ratos"]
    assert len(classe.subclasses) == 3 and [s.prestigio for s in classe.subclasses.values()] == [0, 3, 6]
    assert arvore_da_classe("senhor_dos_ratos")
    for sub in classe.subclasses.values():
        heroi = criar_heroi("senhor_dos_ratos", subclasse=sub.chave)
        assert heroi.golpes.sabe(sub.assinatura)
        for esp in sub.especializacoes.values():
            assert esp.sprite and all(golpe(g) for g in esp.golpes)
    assert golpe("rei_de_tudo_que_rasteja").classes_do_raro == ["senhor_dos_ratos"]
    from roguelike.conquistas import conquista_do_golpe
    assert conquista_do_golpe("rei_de_tudo_que_rasteja").marco == "chefe:flautista_caido"
    assert criar_heroi("senhor_dos_ratos").bonus("resiste_peste") >= 1.0


def combate_do_senhor(subclasse="rei_dos_bandos"):
    senhor = criar_heroi("senhor_dos_ratos", subclasse=subclasse)
    combate = Combate([senhor, criar_heroi("guerreiro")], [criar_inimigo("goblin"), criar_inimigo("orc")],
                      random.Random(4))
    combate.iniciar()
    return combate, senhor


def test_chama_ratos_ratazana_e_moscas_que_lutam_do_lado_dele():
    combate, senhor = combate_do_senhor()
    assert senhor.stat("max_invocacoes") == 3                                      # Ninho Grande
    combate.aplicar_efeitos(senhor, golpe("chamar_ratos").efeitos, [senhor], 1)
    combate.aplicar_efeitos(senhor, golpe("nuvem_de_moscas").efeitos, [senhor], 1)
    nomes = sorted(i.nome for i in combate.invocacoes_de(senhor))
    assert nomes == ["Enxame de Moscas", "Rato do Bando", "Rato do Bando"]
    assert all(i.lado == "herois" for i in combate.invocacoes_de(senhor))
    combate.aplicar_efeitos(senhor, golpe("chamar_ratazana").efeitos, [senhor], 1)
    assert "Ratazana Leal" in [i.nome for i in combate.invocacoes_de(senhor)] and len(combate.invocacoes_de(senhor)) == 3
    for chave in ("rato_servo", "ratazana_leal", "enxame_de_moscas"):
        assert "peste" in ficha_de_invocacao(chave)["imune"]


def test_peste_nos_inimigos_e_o_beijo_que_bebe_dela():
    combate, senhor = combate_do_senhor("profeta_da_praga")
    goblin = combate.inimigos[0]
    combate.aplicar_efeitos(senhor, golpe("febre_rogada").efeitos, [goblin], 1)
    assert goblin.acumulos_de("peste") == 3 and goblin.tem_status("definhando")
    efeito = golpe("beijo_da_peste").efeitos[0]
    assert efeito.dados["bonus_contra"] == {"peste": 0.6} and efeito.dados["roubo"] == 0.4
    senhor.vida = 10
    combate.aplicar_efeitos(senhor, golpe("sugar_a_vida").efeitos, [goblin], 1)
    assert senhor.vida > 10 or not any(e.tipo == "dano" and e.alvo is goblin for e in combate.eventos[-3:])


def test_sprites_do_senhor_do_enxame_e_da_geometria_nova():
    with open(CATALOGO, encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)
    for nome in ("senhor_dos_ratos", "senhor_moscas", "senhor_profeta", "senhor_pai_dos_ratos", "senhor_enxame",
                 "senhor_arauto"):
        assert nome in catalogo and nome + "_desarmado" in catalogo, nome
        assert "sentado" in catalogo[nome]["animacoes"]
    assert "enxame_de_moscas" in catalogo and catalogo["enxame_de_moscas"]["familia"] == "invocacoes"
    for camada in ("raca_gnomo", "eq_capuz", "aureola"):
        assert f"camada_senhor_dos_ratos_{camada}" in catalogo


def test_grimorio_com_as_doze_classes_cabe(app):  # noqa: F811
    from telas.grimorio import TelaGrimorio
    app.progresso.conquistas |= {"chefe:rainha_dos_ratos", CORTE}
    app.progresso.herois_anunciados |= {"medico_da_peste", "senhor_dos_ratos"}
    tela = TelaGrimorio(app, "senhor_dos_ratos")
    app.trocar(tela)
    quadros(app, 2)
    classes = [b for b in tela.botoes if b.rect.y == 64]
    assert len(classes) == 12 and all(b.rect.right <= 1280 for b in classes)
