"""Sorteio de loot: cada inimigo tem a sua própria tabela (loot.json)."""

from roguelike.dados import carregar, regras, sem_comentarios


def tabela_de(chave_inimigo):
    """As linhas de loot do inimigo + os materiais-base dele + as que valem para todos."""
    dados = carregar("loot")
    return list(sem_comentarios(dados["inimigos"]).get(chave_inimigo, [])) + \
        list(sem_comentarios(dados.get("materiais_base", {})).get(chave_inimigo, [])) + list(dados.get("todos", []))


def multiplicador_de(chave_item):
    """Quanto a chance de um drop é multiplicada (regras.json "drops"): materiais e consumíveis à parte;
    peças de equipamento das tabelas ficam como estão (já existe o sorteio de peça por combate)."""
    from roguelike.itens import item
    drops = regras().get("drops", {})
    try:
        tipo = item(chave_item).tipo
    except KeyError:
        tipo = "material"
    return {"consumivel": drops.get("multiplicador_consumiveis", 1.0),
            "material": drops.get("multiplicador_materiais", 1.0)}.get(tipo, 1.0)


def chance_final(chave_item, chance, bonus_de_chance=0.0):
    """Chance de verdade de uma linha de drop (as garantidas, 1.0, ficam como estão; as incertas não passam
    do "teto_de_chance" de regras.json "drops", para continuarem incertas)."""
    if chance >= 1:
        return chance
    teto = regras().get("drops", {}).get("teto_de_chance", 1.0)
    return min(teto, chance * multiplicador_de(chave_item) * (1 + bonus_de_chance))


def sortear_loot(chave_inimigo, rng, bonus_de_chance=0.0):
    """Devolve {chave do item: quantidade} sorteado da tabela do inimigo.

    bonus_de_chance: chance extra (encontros com mais estrelas sorteiam melhor).
    """
    resultado = {}
    for linha in tabela_de(chave_inimigo):
        if rng.random() < chance_final(linha["item"], linha["chance"], bonus_de_chance):
            minimo, maximo = linha.get("quantidade", [1, 1])
            quantidade = rng.randint(minimo, maximo)
            resultado[linha["item"]] = resultado.get(linha["item"], 0) + quantidade
    return resultado


def materiais_da_fase(chave_regiao):
    """Materiais-base extras que caem pela fase (loot.json "materiais_da_fase")."""
    return list(sem_comentarios(carregar("loot").get("materiais_da_fase", {})).get(chave_regiao, []))


def juntar(*listas):
    """Soma vários resultados de loot em um só."""
    total = {}
    for loot in listas:
        for chave, quantidade in loot.items():
            total[chave] = total.get(chave, 0) + quantidade
    return total
