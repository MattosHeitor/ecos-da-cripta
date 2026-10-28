"""MP4: a mochila (50 pilhas) e o ouro de cada jogador, o baú da equipe e o save.

O critério de aceite: dois jogadores mexendo nas mochilas e no baú ao mesmo tempo (comandos intercalados) nunca
perdem nem duplicam um item, e a mochila nunca passa do limite; o que não cabe vai para o baú.
"""

import json
import random

from roguelike import comandos as C
from roguelike.classes import criar_heroi
from roguelike.dados import regras
from roguelike.encontros import EncontroAltar
from roguelike.estado import EstadoDoJogo
from roguelike.grupo import dividir
from roguelike.inventario import Inventario
from roguelike.itens import todos_os_itens
from roguelike.loja import Loja, Oferta
from roguelike.posse import Jogador
from roguelike.processador import ProcessadorDeComandos
from roguelike.progresso import Progresso
from roguelike.run import Run

DORAN, ILSE, BRAM = 0, 1, 2


def run_de_dois(semente="MP4"):
    """Doran e Ilse com o jogador local; Bram com a Bia."""
    run = Progresso().criar_run([criar_heroi("guerreiro", "Doran"), criar_heroi("mago", "Ilse"),
                                 criar_heroi("sacerdote", "Bram")], semente)
    run.grupo.dar_heroi(run.grupo.herois[BRAM], Jogador("bia", "Bia"))
    for mochila in run.inventarios():
        mochila.itens.clear()
    return run


def chaves_simples(quantas, evitar=()):
    """Itens de verdade (não equipamento) para encher mochilas."""
    chaves = [c for c, i in todos_os_itens().items() if i.tipo != "equipamento" and c not in evitar]
    assert len(chaves) >= quantas
    return chaves[:quantas]


def encher(mochila, livres=0, evitar=()):
    """Enche a mochila de pilhas diferentes, deixando 'livres' espaços."""
    faltam = mochila.capacidade - livres - len(mochila.itens)
    for chave in chaves_simples(faltam + len(mochila.itens) + len(evitar), evitar=set(evitar) | set(mochila.itens)):
        if len(mochila.itens) >= mochila.capacidade - livres:
            break
        mochila.adicionar(chave)


def total_de_itens(run):
    """Tudo o que a equipe tem (mochilas + baú), por chave."""
    soma = {}
    for inventario in run.inventarios():
        for chave, n in inventario.itens.items():
            soma[chave] = soma.get(chave, 0) + n
    return soma


# ---------------- mochila ----------------
def test_mochila_e_do_jogador_tem_50_pilhas_e_os_herois_dele_dividem():
    run = run_de_dois()
    doran, ilse, bram = run.grupo.herois
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    assert doran.inventario is ilse.inventario is local.mochila
    assert bram.inventario is bia.mochila and bia.mochila is not local.mochila
    assert local.mochila.capacidade == 50 == regras()["inventario"]["pilhas_por_jogador"]
    assert run.grupo.mochilas() == [local.mochila, bia.mochila]


def test_loot_que_nao_cabe_vai_para_o_bau_e_nada_se_perde():
    run = run_de_dois()
    local = run.grupo.jogador("local")
    local.mochila.adicionar("osso")
    encher(local.mochila, evitar=("pocao_de_vida",))
    assert local.mochila.cheia()
    recebidos, no_bau = run.guardar_loot({"local": {"osso": 2, "pocao_de_vida": 1}, "bia": {"osso": 1}})
    assert recebidos == {"local": {"osso": 2, "pocao_de_vida": 1}, "bia": {"osso": 1}}
    assert no_bau == {"local": {"pocao_de_vida": 1}}                  # pilha nova: não coube
    assert local.mochila.quantidade("osso") == 3                       # na pilha que já havia, coube
    assert run.grupo.bau.quantidade("pocao_de_vida") == 1 and run.grupo.jogador("bia").mochila.tem("osso")
    assert len(local.mochila.itens) == 50


def test_comprar_com_a_mochila_cheia_vai_para_o_bau_e_cada_um_paga_o_seu():
    run = run_de_dois()
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    loja = Loja(random.Random(1), 1)
    loja.ofertas = [Oferta("item", "pocao_de_vida", 10, 3)]
    run.loja_atual = loja
    encher(local.mochila, evitar=("pocao_de_vida",))
    local.ouro, bia.ouro = 25, 5
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    comprou = processador.executar(C.Comprar(jogador="local", indice=0))
    assert comprou and "baú" in comprou.mensagem and run.grupo.bau.tem("pocao_de_vida")
    assert local.ouro == 15 and bia.ouro == 5
    assert not processador.executar(C.Comprar(jogador="bia", indice=0))      # a Bia não tem ouro bastante
    assert bia.ouro == 5 and loja.ofertas[0].estoque == 2


def test_vender_da_o_ouro_a_quem_vende_e_so_da_propria_mochila():
    run = run_de_dois()
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    bia.mochila.adicionar("osso", 2)
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    antes_local, antes_bia = local.ouro, bia.ouro
    assert not processador.executar(C.Vender(jogador="local", origem=BRAM, chave="osso"))   # mochila da Bia
    venda = processador.executar(C.Vender(jogador="bia", origem=BRAM, chave="osso"))
    assert venda and bia.ouro == antes_bia + venda.valor and local.ouro == antes_local


# ---------------- ouro ----------------
def test_dividir_soma_o_total_e_reparte_pelos_pesos():
    sorteio = random.Random(5)
    for _ in range(300):
        pesos = [sorteio.randint(0, 9) for _ in range(sorteio.randint(1, 5))]
        total = sorteio.randint(0, 500)
        partes = dividir(total, pesos)
        if sum(pesos) == 0:
            assert partes == [0] * len(pesos)
            continue
        assert sum(partes) == total
        for parte, peso in zip(partes, pesos):
            exato = total * peso / sum(pesos)
            assert exato - 1 < parte < exato + 1


def test_ouro_ganho_e_dividido_pelos_herois_e_perdido_pelo_que_cada_um_tem():
    run = run_de_dois()
    grupo = run.grupo
    local, bia = grupo.jogador("local"), grupo.jogador("bia")
    local.ouro, bia.ouro = 0, 0
    assert grupo.ganhar_ouro(31) == {"local": 21, "bia": 10}             # 2 heróis contra 1
    assert grupo.ouro == 31
    partes = grupo.perder_ouro(12)
    assert sum(partes.values()) == 12 and partes["local"] > partes["bia"]   # quem tem mais paga mais
    grupo.ouro = grupo.ouro + 3                                          # (eventos mexem no total)
    assert grupo.ouro == 22
    assert sum(grupo.perder_ouro(999).values()) == 22                    # nunca mais do que há
    assert local.ouro == 0 and bia.ouro == 0


def test_o_ouro_do_combate_vai_para_cada_jogador():
    from roguelike.condutor import ESPERANDO, FIM, DecisorIA
    from roguelike.encontros import EncontroCombate
    run = run_de_dois()
    estado = EstadoDoJogo(run)
    processador = ProcessadorDeComandos(estado)
    antes = {j.id: j.ouro for j in run.grupo.jogadores}
    condutor = processador.executar(C.ComecarCombate(encontro=EncontroCombate("t", "", 1, ["goblin"]).para_dict())).valor
    while condutor.avancar_ate_decisao() == ESPERANDO:
        heroi = condutor.heroi_da_vez()
        comando = DecisorIA().comando(estado, heroi)
        comando.jogador = heroi.jogador.id
        assert processador.executar(comando)
    assert condutor.passo() == FIM and condutor.combate.resultado == "vitoria"
    recompensa = condutor.recompensa
    assert recompensa.ouro > 0 and sum(recompensa.ouro_por_jogador.values()) == recompensa.ouro
    for jogador in run.grupo.jogadores:
        assert jogador.ouro == antes[jogador.id] + recompensa.ouro_por_jogador[jogador.id]


def test_enviar_ouro_por_comando():
    run = run_de_dois()
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    local.ouro, bia.ouro = 40, 0
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    assert processador.executar(C.EnviarOuro(jogador="local", para="bia", quantidade=15))
    assert (local.ouro, bia.ouro) == (25, 15)
    assert not processador.executar(C.EnviarOuro(jogador="bia", para="local", quantidade=16))   # não tem
    assert not processador.executar(C.EnviarOuro(jogador="local", para="local", quantidade=1))
    assert not processador.executar(C.EnviarOuro(jogador="local", para="ninguem", quantidade=1))
    assert not processador.executar(C.EnviarOuro(jogador="local", para="bia", quantidade=0))
    assert [d["tipo"] for d in processador.registro] == ["enviar_ouro"]


def test_quem_manda_paga_o_altar_ate_pelo_heroi_do_outro():
    run = run_de_dois()
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    run.encontro = EncontroAltar()
    preco = run.encontro.preco()
    doran, _, bram = run.grupo.herois
    doran.vida = bram.vida = 0
    local.ouro, bia.ouro = preco + 5, preco - 1
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    assert processador.executar(C.Reviver(jogador="local", caido=BRAM))          # o local paga a volta do Bram
    assert bram.esta_vivo() and local.ouro == 5 and bia.ouro == preco - 1
    recusado = processador.executar(C.Reviver(jogador="bia", caido=DORAN))
    assert not recusado and "Ouro" in recusado.mensagem and not doran.esta_vivo()


# ---------------- o critério de aceite ----------------
def preparar_para_mexer(run):
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    local.mochila.adicionar("osso", 5)
    local.mochila.adicionar("pocao_de_vida", 3)
    bia.mochila.adicionar("osso", 2)
    bia.mochila.adicionar("pocao_grande", 1)
    run.grupo.bau.adicionar("pena_da_fenix", 2)
    encher(bia.mochila, livres=1, evitar=("pocao_de_vida", "pena_da_fenix"))   # a Bia quase sem espaço


def test_dois_jogadores_mexendo_juntos_nada_some_nem_duplica():
    run = run_de_dois()
    preparar_para_mexer(run)
    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    inicial = total_de_itens(run)
    sorteio = random.Random(7)
    chaves = ["osso", "pocao_de_vida", "pocao_grande", "pena_da_fenix"]
    herois_de = {"local": [DORAN, ILSE], "bia": [BRAM]}
    aceitos = recusados = 0
    for _ in range(400):
        jogador = sorteio.choice(["local", "bia"])
        meu, outro = sorteio.choice(herois_de[jogador]), sorteio.choice([DORAN, ILSE, BRAM])
        de, para = sorteio.choice([(meu, "bau"), ("bau", meu), (meu, outro), (outro, "bau"), ("bau", outro)])
        comando = C.MoverItem(jogador=jogador, chave=sorteio.choice(chaves), de=de, para=para,
                              quantidade=sorteio.randint(1, 3))
        if processador.executar(comando):
            aceitos += 1
        else:
            recusados += 1
        assert total_de_itens(run) == inicial                         # nada sumiu, nada apareceu
        assert all(len(m.itens) <= m.capacidade for m in run.grupo.mochilas())
        assert all(n > 0 for i in run.inventarios() for n in i.itens.values())
    assert aceitos > 50 and recusados > 50                            # (as duas coisas aconteceram)
    jogadores = {m.jogador.id for m in run.grupo.bau.registro}
    assert jogadores == {"local", "bia"}
    refeita = run_de_dois()                                           # e dá para refazer do zero
    preparar_para_mexer(refeita)
    outro = ProcessadorDeComandos(EstadoDoJogo(refeita))
    outro.refazer(processador.registro)
    assert outro.estado.impressao_digital() == processador.estado.impressao_digital()


# ---------------- save ----------------
def test_save_guarda_a_mochila_e_o_ouro_de_cada_jogador():
    run = run_de_dois()
    local, bia = run.grupo.jogador("local"), run.grupo.jogador("bia")
    local.mochila.adicionar("osso", 3)
    bia.mochila.adicionar("pocao_de_vida")
    local.ouro, bia.ouro = 40, 12
    run.grupo.colocar_no_bau(run.grupo.herois[DORAN], "osso")
    copia = Run.de_dict(json.loads(json.dumps(run.para_dict())))
    doran, ilse, bram = copia.grupo.herois
    assert doran.inventario is ilse.inventario and doran.inventario.itens == {"osso": 2}
    assert bram.inventario.itens == {"pocao_de_vida": 1} and copia.grupo.bau.itens == {"osso": 1}
    assert {j.id: j.ouro for j in copia.grupo.jogadores} == {"local": 40, "bia": 12}
    assert [(m.jogador.id, m.heroi, m.acao) for m in copia.grupo.bau.registro] == [("local", "Doran", "colocar")]
    assert copia.para_dict() == run.para_dict()


def test_save_de_antes_da_mp4_junta_as_mochilas_dos_herois_no_jogador():
    run = run_de_dois()
    dados = json.loads(json.dumps(run.para_dict()))
    dados["versao"] = 3
    dados["ouro"] = 77
    for jogador in dados["jogadores"]:                                # (na MP3, o jogador não tinha mochila nem ouro)
        jogador.pop("mochila")
        jogador.pop("ouro")
    chaves = chaves_simples(60)
    mochilas = [Inventario(10), Inventario(10), Inventario(10)]
    for i, chave in enumerate(chaves[:30]):                           # (em saves antigos dava para ter mais)
        mochilas[DORAN].itens[chave] = 1
    for chave in chaves[25:55]:                                       # 5 iguais às do Doran
        mochilas[ILSE].itens[chave] = 2
    mochilas[BRAM].itens["osso"] = 4
    for heroi, mochila in zip(dados["herois"], mochilas):
        heroi["inventario"] = mochila.para_dict()
    velha = Run.de_dict(dados)
    local, bia = velha.grupo.jogador("local"), velha.grupo.jogador("bia")
    assert len(local.mochila.itens) == 50 and len(velha.grupo.bau.itens) == 5      # 55 pilhas: 5 foram ao baú
    esperado = {}
    for mochila in mochilas:
        for chave, n in mochila.itens.items():
            esperado[chave] = esperado.get(chave, 0) + n
    assert total_de_itens(velha) == esperado                          # nada se perdeu
    assert bia.mochila.itens == {"osso": 4} and velha.grupo.ouro == 77
