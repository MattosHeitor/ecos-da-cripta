"""Fase 4, etapa 4: Catacumbas da Ordem Caída (escudo do 1º golpe, fogo sagrado, Inquisidor, skin nova)."""

from roguelike.classes import criar_heroi
from roguelike.conquistas import todas_as_conquistas
from roguelike.golpes import golpe
from roguelike.inimigos import criar_inimigo
from roguelike.skins import skin

from apoio_roguelike import combate_pronto


def test_cavaleiro_ossudo_apara_so_o_primeiro_golpe():
    heroi = criar_heroi("guerreiro")
    cavaleiro = criar_inimigo("cavaleiro_ossudo")
    combate = combate_pronto([heroi], [cavaleiro])
    assert cavaleiro.tem_status("guarda_erguida")
    assert combate.causar_dano(cavaleiro, 10, heroi) == 0
    assert not cavaleiro.tem_status("guarda_erguida")
    assert combate.causar_dano(cavaleiro, 10, heroi) > 0


def test_fogo_sagrado_queima_mais_demonios_e_mortos_vivos():
    efeito = golpe("fogo_sagrado").efeitos[0]
    humano, demonio = criar_heroi("guerreiro"), criar_heroi("guerreiro")
    demonio.definir_raca("meio_demonio")
    assert efeito.bonus_contra_natureza(humano) == 0
    assert efeito.bonus_contra_natureza(demonio) == 0.5
    assert efeito.bonus_contra_natureza(criar_inimigo("esqueleto")) == 0.5         # família mortos-vivos


def test_inquisidor_tem_duas_fases():
    herois = [criar_heroi("guerreiro"), criar_heroi("sacerdote")]
    inquisidor = criar_inimigo("inquisidor_penitente")
    combate = combate_pronto(herois, [inquisidor])
    combate.causar_dano(inquisidor, 99999, herois[0])
    assert inquisidor.esta_vivo() and inquisidor.tem_status("espinhos")
    assert "autoflagelo_do_inquisidor" in inquisidor.niveis_habilidade


def test_skin_do_cavaleiro_ossudo_por_abates():
    conquista = todas_as_conquistas()["terror_da_ordem"]
    assert conquista.skin == "elmo_do_cavaleiro_ossudo"
    assert skin("elmo_do_cavaleiro_ossudo").camada == "chapeu"
    assert skin("elmo_ossudo").nome == "Elmo Ossudo"                                 # a skin antiga continua
