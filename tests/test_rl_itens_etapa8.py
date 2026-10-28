"""Etapa 8: 100+ peças novas (todos os espaços), uma por classe, ícone, visual, receita e a duração extra
de bênçãos e maldições."""

import json
import os

from roguelike.classes import criar_heroi
from roguelike.dados import carregar, sem_comentarios
from roguelike.fabricacao import todas_as_receitas
from roguelike.inimigos import criar_inimigo
from roguelike.itens import item, Equipamento

from apoio_roguelike import combate_pronto

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEM_DA_CLASSE = {"guerreiro": "bastiao_do_juramento", "ladino": "presas_da_vibora_gemea",
                  "mago": "cajado_da_brasa_cativa", "sacerdote": "turibulo_da_ultima_vigilia",
                  "barbaro": "manto_do_lobo_faminto", "patrulheira": "arco_longo_de_teixo_negro",
                  "bardo": "alaude_de_cordas_de_tripa", "bobo": "guizos_do_riso_final",
                  "monge": "rosario_de_contas_em_brasa", "feiticeira": "grimorio_de_pele_de_sapo"}


def pecas_da_etapa8():
    dados = json.load(open(os.path.join(RAIZ, "src", "roguelike", "dados", "itens.json"), encoding="utf-8"))["equipamentos"]
    chaves = list(dados)
    inicio = chaves.index("_etapa8_cabeca")
    return [c for c in chaves[inicio:] if not c.startswith("_")]


def test_mais_de_cem_pecas_em_todos_os_espacos_e_raridades():
    pecas = [item(c) for c in pecas_da_etapa8()]
    assert len(pecas) >= 100
    assert all(isinstance(p, Equipamento) for p in pecas)
    espacos = {p.espaco for p in pecas}
    assert espacos == {"cabeca", "peitoral", "calcas", "botas", "capa", "amuleto", "arma", "arma_secundaria"}
    assert {p.raridade for p in pecas} == {"comum", "incomum", "raro", "epico", "lendario", "amaldicoado"}
    for p in pecas:                                            # toda peça tem troca: algum bônus e algum custo
        valores = list(p.modificadores.values())
        assert any(v > 0 for v in valores), p.chave
        assert any(v < 0 for v in valores) or p.raridade == "epico" and p.passivas or p.raridade == "lendario" \
            or p.chave == "botas_da_brasa_andante", p.chave


def test_toda_peca_nova_tem_icone_visual_e_tier():
    visuais = sem_comentarios(carregar("visual_equipamentos")["pecas"])
    for chave in pecas_da_etapa8():
        assert chave in visuais, chave
        assert os.path.exists(os.path.join(RAIZ, "assets", "itens_macabros", chave + ".png")), chave
        assert item(chave).tier >= 1, chave


def test_cada_classe_tem_uma_peca_nova_com_receita():
    resultados = {r.resultado for r in todas_as_receitas().values()}
    for classe, chave in ITEM_DA_CLASSE.items():
        nome_da_classe = carregar("classes")[classe]["nome"]
        assert item(chave).descricao.startswith(nome_da_classe + ":"), chave
        assert chave in resultados, chave


def test_maioria_das_pecas_novas_e_fabricavel():
    resultados = {r.resultado for r in todas_as_receitas().values()}
    novas = pecas_da_etapa8()
    assert sum(1 for c in novas if c in resultados) >= 90


def test_alaude_alonga_os_buffs_e_grimorio_alonga_as_maldicoes():
    bardo, feiticeira = criar_heroi("bardo"), criar_heroi("feiticeira")
    goblin = criar_inimigo("goblin")
    combate = combate_pronto([bardo, feiticeira], [goblin])
    sem = combate.aplicar_status(bardo, "fortalecido", 2, origem=bardo).duracao
    bardo.status.pop("fortalecido")
    bardo.equipar(item("alaude_de_cordas_de_tripa"))
    assert combate.aplicar_status(feiticeira, "fortalecido", 2, origem=bardo).duracao == sem + 1
    feiticeira.equipar(item("grimorio_de_pele_de_sapo"))
    assert combate.aplicar_status(goblin, "enfraquecido", 2, origem=feiticeira).duracao == 3
    assert combate.aplicar_status(goblin, "atordoado", 1, origem=feiticeira).duracao == 1     # tirar a vez não alonga
