"""Reino dos Ratos, etapa 5C: A Corte Completa (o modo difícil do chefe: a 2ª carta depois da 1ª vitória; o Rei
governa do trono enquanto a Rainha luta e desce quando ela cai) e a fase aberta (bestiário com a aba do Reino)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from roguelike.bestiario import secoes
from roguelike.classes import criar_heroi
from roguelike.combate import Combate
from roguelike.encontros import GeradorDeEncontros, MontadorDeCombate, encontro_de_dict
from roguelike.golpes import golpe
from roguelike.progresso import Progresso
from roguelike.regioes import regiao
from roguelike.run import Run
from visual.sprites_macabros import Sprites

from test_telas_fluxo import app, quadros  # noqa: F401  (fixture e ajudantes)


def run_no_salao(conquistas=()):
    run = Run([criar_heroi(c) for c in ("guerreiro", "sacerdote", "mago")], "CORTE", "reino_dos_ratos")
    run.area = run.areas_da_regiao()
    run.conquistas_permanentes = set(conquistas)
    return run


def corte(run):
    run.encontro = MontadorDeCombate(run.regiao, run.area, random.Random(1), 3, False, run.area).modo_dificil()
    run.estado = "encontro"
    combate = run.criar_combate()
    rei = next(i for i in combate.inimigos if i.chave == "rei_dos_ratos")
    rainha = next(i for i in combate.inimigos if i.chave == "rainha_dos_ratos")
    return combate, rei, rainha


def derrubar_a_rainha(combate, rainha, quem):
    for rato in list(rainha.roda):
        combate.causar_dano(rato, 99999, quem)


# ---------------- a carta ----------------

def test_a_corte_completa_so_aparece_depois_de_vencer_o_rei():
    antes = GeradorDeEncontros(run_no_salao(), random.Random(1)).gerar()
    assert [o.inimigos[0] for o in antes] == ["rei_dos_ratos"]
    depois = GeradorDeEncontros(run_no_salao({"chefe:rei_dos_ratos"}), random.Random(1)).gerar()
    assert len(depois) == 2 and depois[0].inimigos[0] == "rei_dos_ratos"
    carta = depois[1]
    assert carta.nome == "A Corte Completa" and carta.tipo == "chefe" and carta.dificil
    assert carta.nome_do_tipo() == "Chefe · Modo Difícil" and "épico" in carta.texto_recompensa()
    assert set(carta.inimigos) == {"rei_dos_ratos", "rainha_dos_ratos"}
    copia = encontro_de_dict(carta.para_dict())                   # vai no save da run
    assert copia.passivas_extras == carta.passivas_extras and copia.feito == "corte_completa"


# ---------------- o Rei no trono ----------------

def test_rei_governa_do_trono_sem_poder_ser_atingido():
    combate, rei, rainha = corte(run_no_salao())
    guerreiro = combate.herois[0]
    assert rei.tem_status("no_trono") and getattr(rei, "retirada_feita", False)
    assert rei not in combate.alvos_validos(guerreiro, golpe("golpe"))
    assert rei not in combate.alvos_validos(guerreiro, golpe("redemoinho"))          # nem em área
    combate.nova_rodada()
    assert rei in combate.fila                                                       # mas age
    assert [r["habilidade"] for r in rei.padrao] == ["imposto_real", "contar_moedas"]
    assert rei.nivel_da("contar_moedas") == 1


def test_no_trono_o_edito_nao_sorteia_a_lei_que_nao_vale_nada():
    combate, rei, _ = corte(run_no_salao())
    sorteadas = set()
    for _ in range(30):
        combate.aplicar_efeitos(rei, golpe("edito_real").efeitos, [rei], 1)
        sorteadas.add(rei.ultimo_edito)
    assert "edito_sem_atacar" not in sorteadas and len(sorteadas) >= 2


def test_rainha_cai_e_o_rei_desce_com_metade_da_vida_em_furia():
    combate, rei, rainha = corte(run_no_salao())
    derrubar_a_rainha(combate, rainha, combate.herois[0])
    assert not rainha.esta_vivo() and not combate.verificar_fim() and combate.proxima_parte is None
    assert not rei.tem_status("no_trono") and abs(rei.fracao_vida() - 0.5) < 0.01
    assert rei.status["fase_do_chefe"].valor == 2                                    # a Fúria Real
    assert rei.nivel_da("contar_moedas") == 0 and "corte_real" in [r["habilidade"] for r in rei.padrao]
    assert any(e.tipo == "desceu_do_trono" for e in combate.eventos)
    assert rei in combate.alvos_validos(combate.herois[0], golpe("golpe"))
    for _ in range(3):                                                               # agora cai de verdade
        combate.causar_dano(rei, 99999, combate.herois[0])
    assert not rei.esta_vivo() and combate.verificar_fim() and combate.resultado == "vitoria"


def test_aliado_caiu_avisa_quem_ficou_vivo():
    from roguelike.passivas import Passiva
    vistos = []

    class Testemunha(Passiva):
        def aliado_caiu(self, dono, caido, combate):
            vistos.append(caido)
    from roguelike.inimigos import criar_inimigo
    dono, outro = criar_inimigo("goblin"), criar_inimigo("goblin")
    combate = Combate([criar_heroi("guerreiro")], [dono, outro], random.Random(1))
    combate.iniciar()
    dono.passivas.append(Testemunha({}))
    combate.causar_dano(outro, 99999, combate.herois[0])
    assert vistos == [outro]


# ---------------- a recompensa e o feito ----------------

def test_vencer_a_corte_da_mais_xp_um_item_epico_e_o_feito():
    run = run_no_salao({"chefe:rei_dos_ratos"})
    combate, rei, rainha = corte(run)
    derrubar_a_rainha(combate, rainha, combate.herois[0])
    for _ in range(3):
        combate.causar_dano(rei, 99999, combate.herois[0])
    combate.verificar_fim()
    xp_base = combate.xp_ganho()
    recompensa = run.concluir_combate(combate)
    assert recompensa.xp > xp_base * 1.5
    from roguelike.itens import item
    from roguelike.dados import regras
    ordem = list(regras()["raridades"])
    raridades = [item(c).raridade for c in recompensa.itens if hasattr(item(c), "raridade")]
    assert any(r in ordem and ordem.index(r) >= ordem.index("epico") for r in raridades)
    assert run.estatisticas["feitos"][0] == "corte_completa" and "feito:corte_completa" in run.marcos()   # (+ "imune": 7C)
    assert "feito:corte_completa" in Progresso().conquistas_da_run(run)


# ---------------- a fase aberta ----------------

def test_reino_aberto_com_a_aba_no_bestiario():
    assert regiao("reino_dos_ratos").disponivel
    abas = {chave: lista for chave, _, lista in secoes()}
    reino = abas["reino_dos_ratos"]
    for chave in ("medico_da_peste_corrompido", "flautista_caido", "rei_dos_ratos", "rainha_dos_ratos",
                  "mordedor_da_rainha", "curandeiro_da_rainha", "queijo_real", "carrasco_bubonico"):
        assert chave in reino, chave
        assert chave not in abas.get("outros", [])
    from telas.bestiario import ABAS_POR_LINHA
    assert len(abas) <= 2 * ABAS_POR_LINHA                                           # cabem em 2 fileiras


def test_sprite_do_rei_tem_as_linhas_sentadas():
    sprites = Sprites()
    for linha in ("trono_ataque", "trono_decreto"):
        assert sprites.tem_animacao("rei_dos_ratos", linha) and sprites.quadros_de("rei_dos_ratos", linha) == 4
    assert sprites.quadros_de("rei_dos_ratos", "ataque") == sprites.quadros_de("rei_dos_ratos", "trono_ataque")
    assert sprites.quadros_de("rei_dos_ratos", "decreto") == sprites.quadros_de("rei_dos_ratos", "trono_decreto")


# ---------------- a tela ----------------

def test_tela_mostra_o_rei_no_trono_e_troca_quando_ele_desce(app):  # noqa: F811
    from telas.combate.tela import TelaCombate
    from telas.combate.trono import VisualNoTrono
    run = run_no_salao()
    combate_de_teste = MontadorDeCombate(run.regiao, run.area, random.Random(1), 3, False, run.area).modo_dificil()
    run.encontro, run.estado = combate_de_teste, "encontro"
    tela = TelaCombate(app, run, combate_de_teste, lambda r: None)
    app.trocar(tela)
    quadros(app, 2)
    rei = next(i for i in tela.combate.inimigos if i.chave == "rei_dos_ratos")
    visual = tela.visual(rei)
    assert isinstance(visual, VisualNoTrono) and (visual.x, visual.y) == tela.trono_pes
    assert visual not in tela.chefes_no_topo() and not visual.tem_barra()
    visual.animador.tocar("ataque")
    assert visual.linha_desenhada()[0] == "trono_ataque"
    visual.investir(100)                                                             # do trono ele não sai
    assert visual.investida is None
    tela.desenhar(app.tela)                                                          # (o painel do trono)
    rainha = next(i for i in tela.combate.inimigos if i.chave == "rainha_dos_ratos")
    derrubar_a_rainha(tela.combate, rainha, tela.combate.herois[0])
    tela.enfileirar()
    for _ in range(400):
        quadros(app, 1)
        if not isinstance(tela.visual(rei), VisualNoTrono):
            break
    novo = tela.visual(rei)
    assert not isinstance(novo, VisualNoTrono) and novo in tela.lado_inimigos and novo in tela.chefes_no_topo()
    tela.desenhar(app.tela)
