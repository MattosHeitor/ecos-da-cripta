"""Fase 4, etapa 1: mecânicas de chefe reutilizáveis (passivas configuradas no inimigos.json)."""

from roguelike.classes import criar_heroi
from roguelike.inimigos import ficha
from roguelike.lutador import Inimigo
from roguelike.ia import ia_do

from apoio_roguelike import combate_pronto


def chefe_com(*passivas, vida_extra=0.0):
    dados = dict(ficha("aranha_mae"))
    dados["passivas"] = list(passivas)
    chefe = Inimigo("aranha_mae", dados)
    chefe.ajustes["vida_percentual"] = vida_extra
    return chefe


def luta(chefe, *aliados):
    herois = [criar_heroi("guerreiro"), criar_heroi("sacerdote")]
    return herois, combate_pronto(herois, [chefe, *aliados])


def tipos(combate):
    return [e.tipo for e in combate.eventos]


def test_fases_de_vida_seguram_o_golpe_e_mudam_o_chefe():
    fases = {"tipo": "fases_de_vida", "fases": [
        {"limiar": 0.5, "nome": "Fúria", "padrao": [{"energia": 0, "habilidade": "teia"}], "sprite": "dragao_osseo",
         "curar": 0.1, "modificadores": {"dano_causado": 0.3}, "aprender": ["chuva_de_veneno"]},
        {"limiar": 0.2, "nome": "Desespero", "texto": "A mãe grita!"}]}
    chefe = chefe_com(fases)
    herois, combate = luta(chefe)
    assert chefe.status["fase_do_chefe"].valor == 1
    dano_antes = chefe.stat("dano_causado")
    combate.causar_dano(chefe, 99999, herois[0])            # não pula a fase: para em 50%
    assert chefe.esta_vivo() and "fase_do_chefe" in tipos(combate)
    curas = [e.valor for e in combate.eventos if e.tipo == "cura"]
    assert curas and chefe.vida == int(chefe.vida_maxima * 0.5) + curas[-1]    # parou no limiar e curou
    assert chefe.padrao == [{"energia": 0, "habilidade": "teia"}] and chefe.sprite_atual() == "dragao_osseo"
    assert round(chefe.stat("dano_causado") - dano_antes, 2) == 0.3
    assert ia_do(chefe).regra_para(chefe, 9)["habilidade"] == "teia"
    combate.causar_dano(chefe, 99999, herois[0])            # para em 20%: fase 3
    assert chefe.esta_vivo() and chefe.status["fase_do_chefe"].valor == 3
    combate.causar_dano(chefe, 99999, herois[0])            # sem mais fases: cai
    assert not chefe.esta_vivo()


def test_invocar_periodico_respeita_o_maximo():
    chefe = chefe_com({"tipo": "invocar_periodico", "a_cada": 2, "invocacao": "esqueleto_menor", "maximo": 1})
    _, combate = luta(chefe)
    passiva = chefe.passivas[0]
    passiva.inicio_do_turno(chefe, combate)
    assert combate.invocacoes_de(chefe) == []
    passiva.inicio_do_turno(chefe, combate)
    assert len(combate.invocacoes_de(chefe)) == 1
    for _ in range(4):
        passiva.inicio_do_turno(chefe, combate)
    assert len(combate.invocacoes_de(chefe)) == 1


def test_escudo_elemental_so_quebra_com_o_elemento_certo_e_se_refaz():
    escudo = {"tipo": "escudo_elemental", "elementos": ["fogo"], "golpes": 2, "reducao": 0.9, "refazer_a_cada": 2}
    chefe = chefe_com(escudo, vida_extra=20)
    herois, combate = luta(chefe)
    assert chefe.status["escudo_elemental"].valor == 2
    assert combate.causar_dano(chefe, 100, herois[0]) == 10                  # físico: quase nada passa
    assert combate.causar_dano(chefe, 100, herois[0], elemento="fogo") == 100
    assert chefe.status["escudo_elemental"].valor == 1
    combate.causar_dano(chefe, 100, herois[0], elemento="fogo")
    assert "escudo_elemental" not in chefe.status and "escudo_quebrou" in tipos(combate)
    assert combate.causar_dano(chefe, 100, herois[0]) == 100                 # sem escudo: tudo passa
    passiva = chefe.passivas[0]
    passiva.inicio_do_turno(chefe, combate)
    passiva.inicio_do_turno(chefe, combate)
    assert chefe.status["escudo_elemental"].valor == 2


def test_a_cada_n_turnos_congela_a_fila_toda():
    chefe = chefe_com({"tipo": "a_cada_n_turnos", "a_cada": 3, "alvo": "oponentes",
                       "status": [{"status": "congelado", "duracao": 1}], "texto": "O frio toma a sala!"})
    herois, combate = luta(chefe)
    passiva = chefe.passivas[0]
    passiva.inicio_do_turno(chefe, combate)
    passiva.inicio_do_turno(chefe, combate)
    assert not any(h.tem_status("congelado") for h in herois)
    passiva.inicio_do_turno(chefe, combate)
    assert all(h.tem_status("congelado") for h in herois) and "aviso" in tipos(combate)


def test_a_cada_n_turnos_com_golpe_extra():
    chefe = chefe_com({"tipo": "a_cada_n_turnos", "a_cada": 1, "golpe": "teia"})
    _, combate = luta(chefe)
    chefe.passivas[0].inicio_do_turno(chefe, combate)
    usados = [e for e in combate.eventos if e.tipo == "habilidade"]
    assert usados and usados[0].extras["habilidade"].chave == "teia"


def test_regenera_enquanto_as_criaturas_vivem():
    chefe = chefe_com({"tipo": "regenerar_com_invocacoes", "fracao": 0.1})
    chefe.ajustes["max_invocacoes"] = 2
    _, combate = luta(chefe)
    chefe.vida = chefe.vida_maxima // 2
    passiva = chefe.passivas[0]
    passiva.inicio_do_turno(chefe, combate)
    assert chefe.vida == chefe.vida_maxima // 2                              # sem criaturas: nada
    criatura = combate.invocar(chefe, "esqueleto_menor")
    passiva.inicio_do_turno(chefe, combate)
    assert chefe.vida > chefe.vida_maxima // 2
    combate.morrer(criatura)
    vida = chefe.vida
    passiva.inicio_do_turno(chefe, combate)
    assert chefe.vida == vida


def test_regenera_com_aliados_comuns_de_uma_chave():
    from roguelike.inimigos import criar_inimigo
    chefe = chefe_com({"tipo": "regenerar_com_invocacoes", "fracao": 0.1, "de": ["goblin"]})
    goblin = criar_inimigo("goblin")
    _, combate = luta(chefe, goblin)
    chefe.vida = chefe.vida_maxima // 2
    chefe.passivas[0].inicio_do_turno(chefe, combate)
    assert chefe.vida > chefe.vida_maxima // 2

