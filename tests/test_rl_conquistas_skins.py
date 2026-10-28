"""Etapa 6 da fase 2: contador de abates, conquistas, skins em camadas e persistência."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from roguelike.classes import criar_heroi, heroi_para_dict, heroi_de_dict, todas_as_classes
from roguelike.conquistas import todas_as_conquistas, conquista_da_skin
from roguelike.piloto_automatico import grupo_padrao
from roguelike.progresso import Progresso
from roguelike.run import Run
from roguelike.skins import todas_as_skins

PASTA_SPRITES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sprites_macabros")


def catalogo():
    with open(os.path.join(PASTA_SPRITES, "catalogo.json"), encoding="utf-8") as arquivo:
        return json.load(arquivo)


def run_simples():
    return Run(grupo_padrao(["guerreiro"]), "CONQUISTAS")


# ---------------- conquistas ----------------
def test_conquista_por_abates_conta_entre_combates():
    progresso, run = Progresso(), run_simples()
    assert progresso.registrar_combate(run, ["esqueleto_cavaleiro"] * 9) == []
    conquista = todas_as_conquistas()["cacador_de_cavaleiros"]
    assert conquista.texto_do_progresso(progresso) == "9/10"
    novas = progresso.registrar_combate(run, ["esqueleto_cavaleiro", "goblin"])
    assert [c.chave for c in novas] == ["cacador_de_cavaleiros"]
    assert progresso.skin_liberada("elmo_ossudo")
    assert progresso.registrar_combate(run, ["esqueleto_cavaleiro"]) == []        # não conclui duas vezes


def test_conquista_por_familia_e_por_qualquer_inimigo():
    progresso, run = Progresso(), run_simples()
    progresso.registrar_combate(run, ["goblin", "goblin_xama", "gnarl"] * 8)       # 24 goblins
    assert not progresso.skin_liberada("capa_da_lua")
    novas = {c.chave for c in progresso.registrar_combate(run, ["goblin_bruto"])}
    assert "praga_dos_goblins" in novas
    assert todas_as_conquistas()["cem_tumulos"].progresso(progresso) == (25, 100)


def test_conquista_por_marco_de_chefe_e_regiao():
    progresso, run = Progresso(), run_simples()
    run.estatisticas["chefes"].append("aranha_mae")
    run.regioes_visitadas.append("minas")
    novas = {c.chave for c in progresso.registrar_combate(run, [])}
    assert {"orfa_da_teia", "fundo_das_minas"} <= novas
    assert "regiao:floresta" not in progresso.conquistas      # começar na Floresta não conta


def test_vitoria_libera_a_aureola_no_fim_da_run():
    progresso = Progresso()
    run = progresso.criar_run([criar_heroi("guerreiro", subclasse="cavaleiro")], "VENCEU")
    run.resultado = "vitoria"
    relatorio = progresso.registrar_fim_de_run(run)
    assert "santo_da_cripta" in [c.chave for c in relatorio.conquistas_feitas]
    assert progresso.skin_liberada("aureola")


# ---------------- skins ----------------
def test_equipar_skin_respeita_bloqueio_classe_e_camada():
    progresso = Progresso()
    assert not progresso.equipar_skin("guerreiro", "roupa", "elmo_ossudo")        # bloqueada
    progresso.conquistas_feitas.add("cacador_de_cavaleiros")
    assert not progresso.equipar_skin("mago", "roupa", "elmo_ossudo")             # outra classe
    assert not progresso.equipar_skin("guerreiro", "chapeu", "elmo_ossudo")       # outra camada
    assert progresso.equipar_skin("guerreiro", "roupa", "elmo_ossudo")
    assert progresso.visual_da_classe("guerreiro") == {"roupa": "elmo_ossudo"}
    assert progresso.equipar_skin("guerreiro", "roupa", None)
    assert progresso.visual_da_classe("guerreiro") == {}


def test_heroi_veste_camadas_e_salva():
    heroi = criar_heroi("guerreiro", subclasse="berserker")
    assert heroi.sprite == "guerreiro_berserker"                                   # roupa da subclasse
    heroi.vestir({"chapeu": "aureola", "arma": "brasa"})
    assert heroi.sprite == "guerreiro_berserker+@aureola+@brasa"
    heroi.vestir({"roupa": "elmo_ossudo", "chapeu": "aureola"})
    assert heroi.sprite == "skin_guerreiro_ossudo+@aureola"
    assert heroi_de_dict(heroi_para_dict(heroi)).sprite == heroi.sprite


def test_preparar_heroi_aplica_as_skins_da_classe():
    progresso = Progresso()
    progresso.conquistas_feitas.add("santo_da_cripta")
    progresso.equipar_skin("mago", "chapeu", "aureola")
    run = progresso.criar_run([criar_heroi("mago", subclasse="criomante")], "SKIN")
    assert run.grupo.herois[0].sprite == "mago_Gelo+@aureola"


def test_especializacao_troca_a_roupa():
    heroi = criar_heroi("guerreiro", subclasse="cavaleiro")
    for _ in range(4):
        heroi.subir_nivel()
    heroi.escolher_especializacao(heroi.subclasse.especializacoes["guardiao_juramentado"])
    assert heroi.sprite == "guerreiro_guardiao"


def test_sprite_com_camadas_e_composto_no_jogo():
    pygame.init()
    from visual.sprites_macabros import Sprites
    sprites = Sprites()
    base, camadas = sprites.partes("guerreiro_berserker+@aureola+@brasa")
    assert base == "guerreiro_berserker"
    assert camadas == ["camada_guerreiro_aureola", "camada_guerreiro_brasa"]       # geometria da roupa
    sozinho = sprites.quadro("guerreiro_berserker", "parado", 0, 1)
    composto = sprites.quadro("guerreiro_berserker+@aureola+@brasa", "parado", 0, 1)
    assert composto.get_size() == sozinho.get_size()
    assert pygame.image.tostring(composto, "RGBA") != pygame.image.tostring(sozinho, "RGBA")
    assert sprites.partes("guerreiro+@acessorio_que_nao_existe")[1] == []         # nunca quebra


# ---------------- dados ----------------
def test_todas_as_roupas_e_camadas_existem_no_catalogo():
    cat = catalogo()
    for classe in todas_as_classes().values():
        for sub in classe.subclasses.values():
            for esp in [sub] + list(sub.especializacoes.values()):
                if esp.sprite:
                    assert esp.sprite in cat and "geometria" in cat[esp.sprite], esp.chave
    geometrias = {m["geometria"] for m in cat.values() if m.get("familia") == "herois" and "geometria" in m}
    for skin in todas_as_skins().values():
        if skin.camada == "roupa":
            assert skin.sprite in cat, skin.chave
        else:
            for geometria in geometrias:
                assert f"camada_{geometria}_{skin.acessorio}" in cat, (geometria, skin.chave)


def test_toda_skin_tem_conquista_ou_preco_e_toda_conquista_libera_algo():
    from roguelike.golpes import golpe
    for chave, s in todas_as_skins().items():
        assert (conquista_da_skin(chave) is not None) != bool(s.preco), chave     # ou conquista, ou vitrine
    for conquista in todas_as_conquistas().values():
        assert conquista.skin or conquista.golpe, conquista.chave
        if conquista.skin:
            assert conquista.skin in todas_as_skins(), conquista.chave
        if conquista.golpe:
            assert golpe(conquista.golpe).raro, conquista.chave


def test_progresso_permanente_guarda_abates_conquistas_e_visual(tmp_path):
    progresso, run = Progresso(), run_simples()
    progresso.registrar_combate(run, ["esqueleto_cavaleiro"] * 10)
    progresso.equipar_skin("guerreiro", "roupa", "elmo_ossudo")
    caminho = str(tmp_path / "progresso.json")
    progresso.salvar(caminho)
    copia = Progresso.carregar(caminho)
    assert copia.abates == {"esqueleto_cavaleiro": 10}
    assert copia.conquistas_feitas == {"cacador_de_cavaleiros"}
    assert copia.visual_da_classe("guerreiro") == {"roupa": "elmo_ossudo"}


# ---------------- tela ----------------
def test_tela_de_visual_equipa_skin_liberada(tmp_path):
    from telas.base import App
    from telas.visual_heroi import TelaVisual
    app = App(janela=False)
    app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
    app.progresso.conquistas_feitas.add("orfa_da_teia")
    saiu = []
    tela = TelaVisual(app, "bobo", "arlequim", lambda: saiu.append(1))
    app.trocar(tela)
    for _ in range(3):
        app.passo(1 / 30, [])
    tela.escolher("chapeu", "coroa_partida")
    assert app.progresso.visual_da_classe("bobo") == {"chapeu": "coroa_partida"}
    assert tela.sprite_da_previa() == "bobo+@coroa_partida"
    assert tela.aba == "chapeu"                            # escolher um chapéu mostra a aba dos chapéus
    app.passo(1 / 30, [])
    bloqueado = next(b for b in tela.botoes if b.texto == "Auréola")
    assert not bloqueado.ativo and "bloqueada" in bloqueado.subtexto
