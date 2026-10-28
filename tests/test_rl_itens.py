"""Testes de itens, inventário, equipamento, loot, fabricação e lojas."""

import random

from roguelike.classes import criar_heroi
from roguelike.dados import carregar, sem_comentarios
from roguelike.encontros import EncontroCombate
from roguelike.fabricacao import todas_as_receitas, receitas_visiveis, fabricar, receita
from roguelike.grupo import Grupo
from roguelike.inimigos import fichas
from roguelike.inventario import Inventario
from roguelike.itens import item, todos_os_itens, Equipamento, Consumivel, Material, Arma, Armadura, Acessorio
from roguelike.loja import Loja, Alquimista
from roguelike.loot import sortear_loot, tabela_de
from roguelike.run import Run

from apoio_roguelike import SorteControlado


# ---------------- itens ----------------

def test_itens_tem_os_quatro_tipos():
    from roguelike.itens import Tomo
    tipos = {type(i) for i in todos_os_itens().values()}
    assert tipos == {Material, Arma, Armadura, Acessorio, Consumivel, Tomo}
    assert issubclass(Tomo, Consumivel)          # tomo é um consumível que se lê fora do combate
    assert all(issubclass(c, Equipamento) for c in (Arma, Armadura, Acessorio))


def test_preco_de_venda_e_40_por_cento():
    assert item("pena_da_fenix").preco_de_venda() == int(item("pena_da_fenix").preco * 0.4)


def test_cada_peca_sabe_seus_espacos():
    assert item("anel_de_sangue").espacos_possiveis() == ["amuleto"]
    assert item("faca_enferrujada").espacos_possiveis() == ["arma", "arma_secundaria"]     # arma leve
    assert item("escudo_de_madeira").espacos_possiveis() == ["arma_secundaria"]
    assert item("elmo_berserker").espacos_possiveis() == ["cabeca"]


# ---------------- inventário ----------------

def test_inventario_empilha_e_respeita_o_limite_de_pilhas():
    mochila = Inventario(capacidade=2)
    assert mochila.adicionar("osso", 3)
    assert mochila.adicionar("seda")
    assert mochila.adicionar("osso")              # mesma pilha: cabe
    assert not mochila.adicionar("quitina")       # terceira pilha: não cabe
    assert mochila.quantidade("osso") == 4


def test_remover_mais_do_que_tem_nao_faz_nada():
    mochila = Inventario()
    mochila.adicionar("osso", 2)
    assert not mochila.remover("osso", 3)
    assert mochila.remover("osso", 2)
    assert mochila.vazio()


def test_mover_entre_inventarios():
    bau, mochila = Inventario(), Inventario(1)
    bau.adicionar("pocao_de_vida", 3)
    assert bau.mover_para(mochila, "pocao_de_vida", 2)
    assert (bau.quantidade("pocao_de_vida"), mochila.quantidade("pocao_de_vida")) == (1, 2)


def test_inventario_salva_e_carrega():
    mochila = Inventario(5)
    mochila.adicionar("osso", 2)
    copia = Inventario.de_dict(mochila.para_dict())
    assert copia.itens == mochila.itens and copia.capacidade == 5


# ---------------- equipamento ----------------

def test_equipar_arma_muda_os_atributos_e_devolve_a_antiga():
    heroi = criar_heroi("guerreiro")
    grupo = Grupo([heroi])
    grupo.bau.adicionar("espada_enferrujada")
    grupo.bau.adicionar("machado_orc")
    forca = heroi.atributo("forca")
    assert grupo.equipar(heroi, "espada_enferrujada", grupo.bau)
    assert heroi.atributo("forca") == forca + 2
    assert grupo.equipar(heroi, "machado_orc", grupo.bau)
    assert heroi.atributo("forca") == forca + 4
    assert heroi.inventario.tem("espada_enferrujada")      # a antiga voltou para a mochila


def test_um_amuleto_por_vez():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("anel_de_sangue"))
    ok, saiu = heroi.equipar(item("olho_de_vidro"))
    assert ok and heroi.equipamento["amuleto"].chave == "olho_de_vidro" and saiu[0].chave == "anel_de_sangue"


def test_item_com_habilidade_ensina_enquanto_equipado():
    heroi = criar_heroi("mago")
    heroi.equipar(item("cetro_do_lich"))
    assert heroi.nivel_da("erguer_esqueleto") == 1
    assert "erguer_esqueleto" in [h.chave for h, _ in heroi.habilidades()]
    heroi.desequipar("arma")
    assert heroi.nivel_da("erguer_esqueleto") == 0


def test_item_com_passiva():
    heroi = criar_heroi("guerreiro")
    heroi.equipar(item("relicario_partido"))
    assert any(p.nome == "Última Prece" for p in heroi.passivas)
    heroi.desequipar("amuleto")
    assert not any(p.nome == "Última Prece" for p in heroi.passivas)


def test_constituicao_do_equipamento_aumenta_vida_atual():
    heroi = criar_heroi("guerreiro")
    vida = heroi.vida
    heroi.equipar(item("gibao_de_couro"))           # +2 CON e +3 de vida
    assert heroi.vida == vida + 5


def test_espaco_de_consumivel_nao_gasta_o_item():
    heroi = criar_heroi("guerreiro")
    grupo = Grupo([heroi])
    heroi.inventario.adicionar("oleo_de_pedra", 2)
    assert grupo.equipar(heroi, "oleo_de_pedra")
    assert heroi.inventario.quantidade("oleo_de_pedra") == 2


def test_consumivel_automatico_e_usado_no_inicio_do_combate():
    heroi = criar_heroi("guerreiro")
    run = Run([heroi], semente="TESTE")
    heroi.inventario.adicionar("oleo_de_pedra", 2)
    run.grupo.equipar(heroi, "oleo_de_pedra")
    run.criar_combate(EncontroCombate("Teste", "", 1, ["goblin"]))
    assert heroi.tem_status("escudo")
    assert heroi.inventario.quantidade("oleo_de_pedra") == 1


def test_pocao_fora_do_combate():
    heroi = criar_heroi("guerreiro")
    grupo = Grupo([heroi])
    heroi.vida = 10
    grupo.bau.adicionar("pocao_de_vida")
    assert grupo.usar_fora_do_combate("pocao_de_vida", grupo.bau, heroi, SorteControlado())
    assert heroi.vida > 10 and not grupo.bau.tem("pocao_de_vida")


def test_pena_da_fenix_revive_fora_do_combate():
    heroi = criar_heroi("guerreiro")
    grupo = Grupo([heroi])
    heroi.vida = 0
    grupo.bau.adicionar("pena_da_fenix")
    assert grupo.usar_fora_do_combate("pena_da_fenix", grupo.bau, heroi, SorteControlado())
    assert heroi.vida == round(heroi.vida_maxima * 0.5)


# ---------------- loot ----------------

def test_todo_inimigo_tem_tabela_de_loot_propria():
    tabelas = sem_comentarios(carregar("loot")["inimigos"])
    for chave in fichas():
        assert chave in tabelas, chave
    # as tabelas não são todas iguais
    assert len({str(t) for t in tabelas.values()}) == len(tabelas)


def test_loot_aponta_para_itens_existentes():
    for chave in fichas():
        for linha in tabela_de(chave):
            item(linha["item"])


def test_chefes_sempre_dao_a_alma():
    resultado = sortear_loot("aranha_mae", SorteControlado(padrao=0.99))
    assert resultado.get("alma_da_mae_aranha") == 1


def test_sorte_baixa_nao_da_drops_incertos():
    resultado = sortear_loot("goblin", SorteControlado(padrao=0.99))
    assert resultado == {}


# ---------------- fabricação ----------------

def test_receitas_apontam_para_itens_existentes():
    for r in todas_as_receitas().values():
        item(r.resultado)
        for chave in r.ingredientes:
            item(chave)
        for chave in r.revelada_por:
            item(chave)


def test_fabricar_gasta_ingredientes_e_cria_o_item():
    bau = Inventario()
    bau.adicionar("erva_do_pantano", 3)
    bau.adicionar("olho_de_sapo", 1)
    assert fabricar(receita("pocao_de_vida"), bau)
    assert bau.quantidade("pocao_de_vida") == 1
    assert bau.quantidade("erva_do_pantano") == 1
    assert not fabricar(receita("pocao_de_vida"), bau)


def test_receita_escondida_so_aparece_depois_de_descoberta():
    bau = Inventario()
    bau.adicionar("ferro_negro", 3)
    bau.adicionar("couro_grosso", 2)
    assert receita("armadura_de_ferro_negro") not in receitas_visiveis(bau, set())
    assert receita("armadura_de_ferro_negro") in receitas_visiveis(bau, {"armadura_de_ferro_negro"})


def test_pegar_minerio_revela_receita_na_run():
    run = Run([criar_heroi("guerreiro")], semente="ABC")
    run.receber_itens({"ferro_negro": 1})
    assert "armadura_de_ferro_negro" in run.descobertas


# ---------------- lojas ----------------

def test_loja_com_a_mesma_semente_tem_o_mesmo_estoque():
    a = Loja(random.Random("x"), 2)
    b = Loja(random.Random("x"), 2)
    assert [(o.chave, o.preco) for o in a.ofertas] == [(o.chave, o.preco) for o in b.ofertas]


def test_comprar_e_vender():
    run = Run([criar_heroi("guerreiro")], semente="LOJA")
    loja = Loja(random.Random(1), 1)
    indice = next(i for i, o in enumerate(loja.ofertas) if o.tipo == "item")
    oferta = loja.ofertas[indice]
    run.grupo.ouro = oferta.preco
    assert loja.comprar(indice, run)
    mochila = run.grupo.herois[0].inventario
    assert run.grupo.ouro == 0 and mochila.tem(oferta.chave)                    # (na mochila de quem comprou)
    ganho = Loja.vender(mochila, oferta.chave, run)
    assert ganho == item(oferta.chave).preco_de_venda()


def test_sem_ouro_nao_compra():
    run = Run([criar_heroi("guerreiro")], semente="LOJA")
    loja = Loja(random.Random(1), 1)
    run.grupo.ouro = 0
    assert not loja.comprar(0, run)


def test_comprar_receita_revela_ela():
    run = Run([criar_heroi("guerreiro")], semente="LOJA")
    loja = Loja(random.Random(5), 3)
    indice = next(i for i, o in enumerate(loja.ofertas) if o.tipo == "receita")
    run.grupo.ouro = 9999
    assert loja.comprar(indice, run)
    assert loja.ofertas[indice].chave in run.descobertas


def test_alquimista_so_vende_consumiveis():
    loja = Alquimista(random.Random(2), 3)
    assert loja.ofertas
    assert all(item(o.chave).tipo == "consumivel" for o in loja.ofertas)
