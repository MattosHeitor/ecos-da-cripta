"""Reino dos Ratos, etapa 6A: classes secretas (liberadas por conquista e anunciadas no acampamento) e o Médico da
Peste (suporte que cura com INT, tira males e Peste; subclasses Doutor da Peste, Boticário e Cirurgião do Esgoto)."""

import json
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from roguelike.classes import criar_heroi, todas_as_classes, classes_liberadas
from roguelike.combate import Combate
from roguelike.expedicao import Expedicao
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo
from roguelike.progresso import Progresso, arvore_da_classe
from roguelike.run import Run

from test_telas_fluxo import app, quadros, tecla  # noqa: F401  (fixture e ajudantes)

RAINHA = "chefe:rainha_dos_ratos"
CATALOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sprites_macabros",
                        "catalogo.json")


# ---------------- a classe secreta ----------------

def test_medico_so_aparece_depois_da_rainha():
    medico = todas_as_classes()["medico_da_peste"]
    assert medico.requer == RAINHA and medico.anuncio
    assert "medico_da_peste" not in classes_liberadas(set())
    assert "medico_da_peste" in classes_liberadas({RAINHA})
    secretas = {"medico_da_peste", "senhor_dos_ratos"}                    # (o Senhor dos Ratos chegou na 6B)
    assert all(c.requer is None for chave, c in todas_as_classes().items() if chave not in secretas)


def test_expedicao_e_recrutamento_nao_usam_classe_secreta():
    progresso = Progresso()
    expedicao = Expedicao.padrao()
    for _ in range(3):
        expedicao.adicionar(sorteio=random.Random(1), permitidas=progresso.classes_liberadas())
    assert "medico_da_peste" not in {v.classe for v in expedicao.vagas}
    expedicao.vagas[0].trocar_classe("medico_da_peste")                   # (um save de antes, por exemplo)
    expedicao.validar(progresso)
    assert "medico_da_peste" not in {v.classe for v in expedicao.vagas}
    run = Run([criar_heroi("guerreiro")], "RECRUTA")
    for k in range(30):
        run.grupo.herois = run.grupo.herois[:1]
        assert run.recrutar(random.Random(k)).classe.chave != "medico_da_peste"
    progresso.conquistas.add(RAINHA)
    expedicao.vagas[0].trocar_classe("medico_da_peste")
    assert expedicao.validar(progresso).vagas[0].classe == "medico_da_peste"


def test_heroi_novo_e_anunciado_uma_vez_no_caminho_do_acampamento(app):  # noqa: F811
    from telas import fluxo
    from telas.novo_heroi import TelaNovoHeroi
    assert app.progresso.herois_para_anunciar() == []
    app.progresso.conquistas.add(RAINHA)
    assert app.progresso.herois_para_anunciar() == ["medico_da_peste"]
    fluxo.ir_para_acampamento(app)
    quadros(app, 3)
    assert isinstance(app.atual, TelaNovoHeroi) and "medico_da_peste" in app.progresso.herois_anunciados
    app.atual.desenhar(app.tela)
    quadros(app, 60)                                                     # (o herói sai da sombra)
    app.atual.desenhar(app.tela)
    tecla(app, pygame.K_RETURN, "\r")
    quadros(app, 3)
    assert type(app.atual).__name__ == "TelaAcampamento"
    assert Progresso.de_dict(json.loads(json.dumps(app.progresso.para_dict()))).herois_anunciados == {"medico_da_peste"}


def test_fim_de_run_avisa_o_heroi_novo():
    progresso = Progresso()
    run = progresso.criar_run([criar_heroi("guerreiro")], "FIM")
    run.estatisticas["chefes"].append("rainha_dos_ratos")
    run.resultado = "vitoria"
    relatorio = progresso.registrar_fim_de_run(run)
    assert relatorio.herois_novos == ["medico_da_peste"]


# ---------------- tudo o que uma classe precisa ----------------

def test_medico_tem_tudo_que_uma_classe_precisa():
    classe = todas_as_classes()["medico_da_peste"]
    assert len(classe.subclasses) == 3 and [s.prestigio for s in classe.subclasses.values()] == [0, 3, 6]
    assert arvore_da_classe("medico_da_peste")
    for sub in classe.subclasses.values():
        heroi = criar_heroi("medico_da_peste", subclasse=sub.chave)
        assert heroi.golpes.sabe(sub.assinatura)
        for esp in sub.especializacoes.values():
            assert esp.sprite and all(golpe(g) for g in esp.golpes)
    assert golpe("panaceia").raro and golpe("panaceia").classes_do_raro == ["medico_da_peste"]
    from roguelike.conquistas import conquista_do_golpe
    assert conquista_do_golpe("panaceia").marco == "chefe:medico_da_peste_corrompido"


def test_mascara_de_bico_resiste_a_peste():
    medico, guerreiro = criar_heroi("medico_da_peste"), criar_heroi("guerreiro")
    assert medico.bonus("resiste_peste") == 0.5 and guerreiro.bonus("resiste_peste") == 0
    combate = Combate([medico, guerreiro], [criar_inimigo("goblin")], random.Random(3))
    combate.iniciar()
    pegou = sum(1 for _ in range(40) if combate.aplicar_status(medico, "peste") is not None and
                not combate.remover_status(medico, "peste"))
    assert 5 < pegou < 35


def combate_do_medico(subclasse=None):
    medico, guerreiro = criar_heroi("medico_da_peste", subclasse=subclasse), criar_heroi("guerreiro")
    combate = Combate([medico, guerreiro], [criar_inimigo("goblin")], random.Random(5))
    combate.iniciar()
    return combate, medico, guerreiro


def test_tonico_amargo_cura_e_tira_um_nivel_de_peste():
    combate, medico, guerreiro = combate_do_medico()
    guerreiro.vida = 5
    combate.aplicar_status(guerreiro, "peste", acumulos=3)
    combate.aplicar_efeitos(medico, golpe("tonico_amargo").efeitos, [guerreiro], 1)
    assert guerreiro.vida > 5 and guerreiro.acumulos_de("peste") == 2


def test_cauterizar_tira_sangramento_e_veneno_e_a_reanimacao_levanta():
    combate, medico, guerreiro = combate_do_medico("doutor_da_peste")
    combate.aplicar_status(guerreiro, "sangramento", acumulos=3)
    combate.aplicar_status(guerreiro, "veneno", valor=2)
    combate.aplicar_efeitos(medico, golpe("cauterizar").efeitos, [guerreiro], 1)
    assert not guerreiro.tem_status("sangramento") and not guerreiro.tem_status("veneno")
    combate.causar_dano(guerreiro, 99999, combate.inimigos[0])
    assert guerreiro in combate.alvos_validos(medico, golpe("reanimacao"))
    combate.aplicar_efeitos(medico, golpe("reanimacao").efeitos, [guerreiro], 1)
    assert guerreiro.esta_vivo() and abs(guerreiro.fracao_vida() - 0.35) < 0.05


def test_frasco_letal_pesa_mais_em_quem_esta_envenenado():
    from roguelike.efeitos_habilidade import EfeitoDano
    efeito = next(e for e in golpe("frasco_letal").efeitos if isinstance(e, EfeitoDano))
    assert efeito.dados["bonus_contra"] == {"veneno": 0.6} and efeito.elemento == "veneno"
    assert all(e.dados.get("bonus_contra", {}).get("sangramento") for e in golpe("amputar").efeitos)


# ---------------- sprites e telas ----------------

def test_sprites_do_medico_e_da_geometria_nova():
    with open(CATALOGO, encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)
    for nome in ("medico_da_peste", "medico_boticario", "medico_cirurgiao", "medico_quarentena", "medico_envenenador",
                 "medico_anatomista"):
        assert nome in catalogo and nome + "_desarmado" in catalogo, nome
        assert "sentado" in catalogo[nome]["animacoes"]
    for camada in ("raca_gnomo", "eq_capuz", "aureola"):
        assert f"camada_medico_da_peste_{camada}" in catalogo
    classe = todas_as_classes()["medico_da_peste"]
    for sub in classe.subclasses.values():
        for sprite in [sub.sprite] + [e.sprite for e in sub.especializacoes.values()]:
            assert sprite is None or sprite in catalogo, sprite


def test_telas_do_acampamento_escondem_e_depois_mostram_o_medico(app):  # noqa: F811
    from telas.bau import TelaBau
    from telas.espelho import TelaEspelho
    from telas.grimorio import TelaGrimorio

    def textos(tela):
        app.trocar(tela)
        quadros(app, 2)
        return {b.texto for b in tela.botoes} | {b.dica[0] for b in tela.botoes if isinstance(b.dica, tuple)}
    app.progresso.herois_anunciados.add("medico_da_peste")                # (sem a tela de herói novo no caminho)
    for Tela in (TelaBau, TelaEspelho, TelaGrimorio):
        assert "Médico da Peste" not in textos(Tela(app)), Tela.__name__
    app.progresso.conquistas.add(RAINHA)
    for Tela in (TelaBau, TelaEspelho, TelaGrimorio):
        assert "Médico da Peste" in textos(Tela(app)), Tela.__name__
    grimorio = TelaGrimorio(app, "medico_da_peste")
    textos(grimorio)
    assert all(b.rect.right <= 1280 for b in grimorio.botoes)
