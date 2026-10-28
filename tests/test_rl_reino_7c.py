"""Reino dos Ratos, etapa 7C: skins e conquistas do Reino (Duzentos Rabos, Quarentena, A Flauta Calada, Roda Quebrada,
Regicida Roedor e Imune), a história do Rei e da Rainha em duas partes, as músicas próprias e o Rato Branco no
acampamento (com a opção de esconder)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from roguelike.bestiario import Pagina
from roguelike.classes import criar_heroi
from roguelike.conquistas import todas_as_conquistas
from roguelike.encontros import MontadorDeCombate
from roguelike.eventos_run import criar_consequencia, ResultadoEvento
from roguelike.insignias import InsigniaDeConquista
from roguelike.inimigos import fichas
from roguelike.progresso import Progresso
from roguelike.run import Run
from roguelike.skins import skin
from ui.opcoes import Opcoes
from visual.pet_do_acampamento import PetDoAcampamento

from test_telas_fluxo import app, quadros  # noqa: F401  (fixture e ajudantes)

PREMIOS = {"duzentos_rabos": "coroa_de_tampinhas", "quarentena": "mascara_do_doutor", "a_flauta_calada": "chapeu_de_flautista",
           "roda_quebrada": "manto_da_roda", "regicida_roedor": "coroa_do_esgoto", "imune": "luz_limpa"}


def run_no_salao():
    run = Run([criar_heroi(c) for c in ("guerreiro", "sacerdote", "mago")], "IMUNE", "reino_dos_ratos")
    run.area = run.areas_da_regiao()
    return run


def vencer_a_corte(run, antes=None):
    """A Corte Completa inteira: a Rainha cai, o Rei desce e cai. 'antes' mexe no combate antes dos golpes."""
    run.encontro = MontadorDeCombate(run.regiao, run.area, random.Random(1), 3, False, run.area).modo_dificil()
    run.estado = "encontro"
    combate = run.criar_combate()
    if antes:
        antes(combate)
    rainha = next(i for i in combate.inimigos if i.chave == "rainha_dos_ratos")
    for rato in list(rainha.roda):
        combate.causar_dano(rato, 99999, combate.herois[0])
    rei = next(i for i in combate.inimigos if i.chave == "rei_dos_ratos")
    for _ in range(3):
        combate.causar_dano(rei, 99999, combate.herois[0])
    combate.verificar_fim()
    run.concluir_combate(combate)
    return run


# ---------------- conquistas e skins ----------------

def test_conquistas_do_reino_liberam_as_skins():
    conquistas = todas_as_conquistas()
    for chave, premio in PREMIOS.items():
        assert conquistas[chave].skin == premio and skin(premio).nome, chave
    assert conquistas["a_flauta_calada"].golpe == "rei_de_tudo_que_rasteja"                # o golpe raro continua
    assert skin("manto_da_roda").camada == "roupa" and skin("manto_da_roda").serve_para("senhor_dos_ratos")
    assert not skin("manto_da_roda").serve_para("guerreiro")
    assert skin("luz_limpa").camada == "arma" and skin("coroa_do_esgoto").camada == "chapeu"
    insignia = InsigniaDeConquista(conquistas["a_flauta_calada"], Progresso())
    assert insignia.premio == "Chapéu de Flautista + golpe raro"


def test_duzentos_ratos_contam_todos_os_ratos_e_os_bandos_por_bicho():
    progresso = Progresso()
    assert all(fichas()[c]["familia"] == "pestes" for c in ("rato_comum", "ratazana_gigante", "rato_da_peste", "rainha_dos_ratos"))
    progresso.abates = {"rato_comum": 150, "ratazana_gigante": 30, "rato_da_peste": 19}

    def do_reino():
        return {c.chave for c in progresso.verificar_conquistas()} & set(PREMIOS)
    assert not do_reino()
    progresso.abates["rato_da_peste"] += 31                                            # 200 ratos e 50 da Peste
    assert do_reino() == {"duzentos_rabos", "quarentena"}
    assert progresso.skin_liberada("coroa_de_tampinhas") and progresso.skin_liberada("mascara_do_doutor")
    progresso.abates["rainha_dos_ratos"] = 3
    assert do_reino() == {"roda_quebrada"}
    assert progresso.equipar_skin("senhor_dos_ratos", "roupa", "manto_da_roda")


# ---------------- Imune: vencer o Reino sem pegar a Peste ----------------

def test_vencer_o_reino_sem_peste_da_o_feito_imune():
    run = vencer_a_corte(run_no_salao())
    assert run.estatisticas["feitos"] == ["corte_completa", "imune"]
    progresso = Progresso()
    progresso.conquistas |= progresso.conquistas_da_run(run)
    assert {c.chave for c in progresso.verificar_conquistas()} >= {"regicida_roedor", "imune"}
    assert progresso.skin_liberada("luz_limpa") and progresso.skin_liberada("coroa_do_esgoto")


def test_quem_pegou_peste_no_reino_perde_o_imune():
    run = vencer_a_corte(run_no_salao(), antes=lambda c: c.aplicar_status(c.herois[1], "peste"))
    assert "imune" not in run.estatisticas["feitos"] and "corte_completa" in run.estatisticas["feitos"]
    assert run.estatisticas["desafios_perdidos"] == ["reino_dos_ratos"]


def test_peste_de_evento_tambem_conta_e_fora_do_reino_nao_ha_desafio():
    run = run_no_salao()
    criar_consequencia({"tipo": "peste", "niveis": 1, "chance": 1.0}).aplicar(run, random.Random(1), ResultadoEvento())
    assert run.estatisticas["desafios_perdidos"] == ["reino_dos_ratos"]
    floresta = Run([criar_heroi("guerreiro")], "IMUNE", "floresta")
    floresta.vigiar_desafio({"peste"})
    assert not floresta.estatisticas.get("desafios_perdidos")


# ---------------- a história em duas partes ----------------

def test_lore_do_rei_e_da_rainha_em_duas_partes():
    progresso = Progresso()
    for chave in ("rei_dos_ratos", "rainha_dos_ratos"):
        assert Pagina(chave, progresso).lore() is None
        progresso.abates[chave] = 1
        pagina = Pagina(chave, progresso)
        primeira, segunda = pagina.partes_da_lore()
        assert pagina.lore() == primeira and pagina.falta_para_a_lore() == 2
        progresso.abates[chave] = 3
        pagina = Pagina(chave, progresso)
        assert pagina.lore() == primeira + "\n\n" + segunda and pagina.falta_para_a_lore() == 0
    progresso.abates["aranha_mae"] = 1                                               # lore de uma parte só: igual
    assert Pagina("aranha_mae", progresso).lore() and Pagina("aranha_mae", progresso).falta_para_a_lore() == 0


# ---------------- o Rato Branco no acampamento ----------------

def test_rato_branco_liberado_ao_vencer_o_reino():
    progresso = Progresso()
    assert progresso.pets_liberados() == []
    progresso.conquistas.add("chefe:rei_dos_ratos")
    assert progresso.pets_liberados() == ["rato_branco"]
    opcoes = Opcoes()
    opcoes.mostrar_pets = False
    assert Opcoes.de_dict(opcoes.para_dict()).mostrar_pets is False


def test_pet_senta_perto_do_fogo_e_corre_para_outro_lugar():
    pet = PetDoAcampamento("rato_branco", [(100, 100), (300, 100)], olhar_para=(200, 0))
    assert pet.pe == (100, 100) and not pet.espelhar and pet.anim in ("sentado", "parado")
    vistos = set()
    for _ in range(110):
        pet.atualizar(0.1)
        vistos.add(pet.anim)
        if pet.correndo:
            assert not pet.espelhar                                                    # correndo para a direita
    assert "correr" in vistos and pet.pe == (300, 100) and pet.lugar == 1
    assert pet.espelhar and not pet.correndo                                           # chegou: olha para o fogo


def test_acampamento_e_opcoes_com_o_rato_branco(app):  # noqa: F811
    from telas.acampamento import TelaAcampamento
    from telas.opcoes import TelaOpcoes
    assert "pets" not in TelaOpcoes(app, lambda: None).linhas and not TelaAcampamento(app).pets
    app.progresso.conquistas.add("chefe:rei_dos_ratos")
    acampamento = TelaAcampamento(app)
    assert [p.sprite for p in acampamento.pets] == ["rato_branco"]
    assert any(tipo == "pet" for _, tipo, _ in acampamento.atores())
    app.trocar(acampamento)
    quadros(app, 3)
    opcoes = TelaOpcoes(app, lambda: None)
    assert opcoes.linhas.index("pets") == 5 and opcoes.valor("pets") == "Mostrar"
    opcoes.mudar("pets", 1)
    assert not app.opcoes.mostrar_pets and opcoes.valor("pets") == "Esconder"
    assert not TelaAcampamento(app).pets
