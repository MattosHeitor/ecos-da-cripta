"""Testes de classes, nível, subclasses, passivas e IA dos chefes."""

from roguelike.classes import criar_heroi, todas_as_classes
from roguelike.golpes import golpe
from roguelike.ia import ia_do, IAChefe
from roguelike.inimigos import criar_inimigo

from apoio_roguelike import combate_pronto, vez_de


# ---------------- classes e nível ----------------

def test_todas_as_classes_criam_heroi_com_habilidades():
    for chave, classe in todas_as_classes().items():
        sem_subclasse = criar_heroi(chave)
        assert sem_subclasse.vida == sem_subclasse.vida_maxima > 0
        assert len(sem_subclasse.habilidades()) >= 3, chave
        assert 3 <= len(classe.subclasses) <= 4, chave
        for sub in classe.subclasses.values():
            heroi = criar_heroi(chave, subclasse=sub.chave)
            espacos = heroi.golpes.espacos()
            assert len(heroi.habilidades()) == min(espacos, len(heroi.niveis_habilidade)), (chave, sub.chave)
            assert heroi.golpes.sabe(sub.assinatura)
            assert len(sub.especializacoes) == 1, sub.chave


def test_subclasse_do_mago_muda_roupa_e_golpe():
    gelo = criar_heroi("mago", subclasse="criomante")
    assert gelo.sprite == "mago_Gelo"
    assert "lanca_de_gelo" in gelo.golpes.equipados
    assert not gelo.golpes.sabe("bola_de_fogo")
    fogo = criar_heroi("mago", subclasse="piromante")
    assert fogo.sprite == "mago_Fogo" and fogo.nome_da_classe() == "Piromante"


def test_subir_de_nivel_da_pontos_e_vida():
    heroi = criar_heroi("guerreiro")
    vida = heroi.vida_maxima
    subiu = heroi.ganhar_xp(heroi.xp_para_proximo_nivel())
    assert subiu == 1 and heroi.nivel == 2
    assert heroi.pontos_atributo == 3 and heroi.pontos_habilidade == 1
    assert heroi.vida_maxima == vida + 2


def test_nivel_maximo_e_respeitado():
    heroi = criar_heroi("guerreiro")
    heroi.ganhar_xp(10 ** 6)
    assert heroi.nivel == heroi.nivel_maximo()


def test_habilidade_da_classe_vai_ate_o_nivel_5():
    heroi = criar_heroi("guerreiro")
    heroi.pontos_habilidade = 10
    while heroi.melhorar_habilidade("golpe"):
        pass
    assert heroi.nivel_da("golpe") == 5


def test_subclasse_so_uma_vez_e_habilidades_vao_ate_8():
    heroi = criar_heroi("guerreiro")
    cavaleiro = heroi.classe.subclasses["cavaleiro"]
    berserker = heroi.classe.subclasses["berserker"]
    assert heroi.escolher_subclasse(cavaleiro)
    assert not heroi.escolher_subclasse(berserker)
    assert heroi.nivel_da("baluarte") == 1
    heroi.pontos_habilidade = 20
    while heroi.melhorar_habilidade("baluarte"):
        pass
    assert heroi.nivel_da("baluarte") == 8
    assert heroi.nome_da_classe() == "Cavaleiro"


def test_subclasse_de_outra_classe_nao_vale():
    guerreiro = criar_heroi("guerreiro")
    sombra = criar_heroi("ladino").classe.subclasses["sombra"]
    assert not guerreiro.escolher_subclasse(sombra)


def test_nivel_da_habilidade_aumenta_o_dano():
    heroi = criar_heroi("guerreiro")
    goblin = criar_inimigo("goblin")
    goblin.vida_da_ficha = 200
    goblin.curar_tudo()
    heroi.niveis_habilidade["golpe"] = 3
    combate = combate_pronto([heroi], [goblin])
    vez_de(combate, heroi)
    combate.usar_habilidade(heroi, "golpe", goblin)
    # dano máximo 5 + 2 níveis = 7, mais 6 x 0,3 = 8,8 (e o bônus de dano dos heróis)
    assert goblin.vida == goblin.vida_maxima - round(8.8 * (1 + heroi.stat("dano_causado")))


# ---------------- passivas ----------------

def test_passiva_sobreviver_salva_uma_vez_por_combate():
    heroi = criar_heroi("guerreiro")
    heroi.adicionar_passiva({"tipo": "sobreviver", "vida": 5})
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    combate.causar_dano(heroi, 999, None)
    assert heroi.vida == 5
    combate.causar_dano(heroi, 999, None)
    assert not heroi.esta_vivo()


def test_passiva_vida_baixa_so_vale_abaixo_do_limiar():
    heroi = criar_heroi("guerreiro")
    heroi.escolher_subclasse(heroi.classe.subclasses["berserker"])
    normal = heroi.stat("dano_causado")
    heroi.vida = 1
    assert heroi.stat("dano_causado") > normal


def test_passiva_adiar_dano_guarda_parte_para_o_proximo_turno():
    heroi = criar_heroi("guerreiro")
    heroi.adicionar_passiva({"tipo": "adiar_dano", "fracao": 0.5})
    combate = combate_pronto([heroi], [criar_inimigo("goblin")])
    vida = heroi.vida
    combate.causar_dano(heroi, 10, None)
    assert heroi.vida == vida - 5
    vez_de(combate, heroi)
    assert heroi.vida == vida - 10


# ---------------- IA ----------------

def test_chefe_segue_o_padrao_pela_energia():
    heroi = criar_heroi("guerreiro")
    mae = criar_inimigo("aranha_mae")
    combate = combate_pronto([heroi], [mae])
    vez_de(combate, mae)
    mae.energia = 6
    escolha = ia_do(mae).escolher(mae, combate)
    assert escolha.habilidade.chave == "chuva_de_veneno"
    mae.energia = 1
    assert ia_do(mae).escolher(mae, combate).habilidade.chave == "mordida_venenosa"


def test_chefe_revela_a_intencao():
    mae = criar_inimigo("aranha_mae")
    combate = combate_pronto([criar_heroi("guerreiro")], [mae])
    mae.energia = 3              # +1 garantido no próximo turno = 4
    assert isinstance(ia_do(mae), IAChefe)
    assert ia_do(mae).intencao(mae, combate).chave == "chamar_filhotes"


def test_ia_de_suporte_cura_o_aliado_mais_ferido():
    xama, goblin = criar_inimigo("goblin_xama"), criar_inimigo("goblin")
    combate = combate_pronto([criar_heroi("guerreiro")], [xama, goblin])
    goblin.vida = 1
    vez_de(combate, xama)
    xama.energia = 5
    alvo = ia_do(xama).escolher_alvo(xama, combate, golpe("cura_tribal"))
    assert alvo is goblin
