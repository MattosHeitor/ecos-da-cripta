"""Os 12 atributos de equipamento de um herói e a comparação de uma peça com o que está equipado.

Os nomes e a ordem vêm do regras.json ("atributos_de_equipamento"); aqui fica como calcular cada um.
A comparação equipa a peça "de mentira" (só nos espaços), mede e desfaz.
"""

from roguelike.dados import regras

CALCULOS = {
    "hp": lambda h: h.vida_maxima,
    "energia": lambda h: h.energia_maxima,
    "ataque": lambda h: h.stat("dano_causado") + h.stat("dano_causado_fisico"),
    "magia": lambda h: h.stat("dano_magico"),
    "defesa": lambda h: h.stat("defesa"),
    "resistencia_magica": lambda h: h.stat("resistencia_magica"),
    "velocidade": lambda h: h.faixa_de_iniciativa()[1],
    "precisao": lambda h: h.stat("precisao"),
    "esquiva": lambda h: h.stat("chance_esquiva"),
    "critico": lambda h: h.stat("chance_critico"),
    "furtividade": lambda h: h.stat("furtividade"),
    "sorte": lambda h: h.atributo("sorte"),
}
PERCENTUAIS = {"ataque", "magia", "resistencia_magica", "precisao", "esquiva", "critico", "furtividade"}


def nomes_dos_atributos():
    """{chave: nome} na ordem do regras.json."""
    return {chave: dados["nome"] for chave, dados in regras()["atributos_de_equipamento"].items()}


def valores(heroi):
    """{chave: número} dos 12 atributos agora."""
    return {chave: CALCULOS[chave](heroi) for chave in nomes_dos_atributos()}


def formatar(chave, valor):
    """Ex.: ("critico", 0.12) -> "12%"; ("hp", 40) -> "40"."""
    if chave in PERCENTUAIS:
        return f"{round(valor * 100)}%"
    return str(round(valor)) if float(valor).is_integer() else f"{valor:.1f}"


def formatar_diferenca(chave, diferenca):
    """Ex.: +5% / -2 (sinal sempre)."""
    texto = formatar(chave, abs(diferenca))
    return ("+" if diferenca > 0 else "-") + texto


def comparar(heroi, peca, espaco=None):
    """{chave: diferença} se o herói trocasse para a peça (só as que mudam), ou None se ela não entra."""
    equipamentos = heroi.equipamentos
    if equipamentos.motivo_para_nao_equipar(peca, espaco) is not None:
        return None
    antes = valores(heroi)
    guardados, travados = dict(equipamentos.espacos), set(equipamentos.travados)
    try:
        equipamentos.equipar(peca, espaco)
        depois = valores(heroi)
    finally:
        equipamentos.espacos, equipamentos.travados = guardados, travados
    return {c: round(depois[c] - antes[c], 4) for c in antes if abs(depois[c] - antes[c]) > 1e-9}


# ============================================================
# QUEM SE BENEFICIA (MP7: o indicador do inventário)
# ============================================================

def pesos_do_heroi(heroi):
    """O peso de cada um dos 12 atributos para este herói (os do foco da classe valem mais)."""
    regra = regras()["beneficio_de_pecas"]
    pesos = dict(regra["pesos"])
    for principal in heroi.classe.atributos_principais:
        for chave in regra["foco"].get(principal, []):
            pesos[chave] = pesos.get(chave, 0) * regra["multiplicador_do_foco"]
    return pesos


def nota_da_troca(heroi, diferencas):
    """Um número: quanto a troca melhora (positivo) ou piora o herói."""
    pesos = pesos_do_heroi(heroi)
    return sum(pesos.get(chave, 0) * diferenca for chave, diferenca in diferencas.items())


def melhor_troca(heroi, peca):
    """(nota, espaço, diferenças) do melhor espaço para a peça neste herói, ou None se ele não pode usá-la."""
    melhor = None
    for espaco in peca.espacos_possiveis():
        diferencas = comparar(heroi, peca, espaco)
        if diferencas is None:
            continue
        nota = nota_da_troca(heroi, diferencas)
        if melhor is None or nota > melhor[0]:
            melhor = (nota, espaco, diferencas)
    return melhor


def beneficiados(peca, herois):
    """[(herói, nota, diferenças)] de quem fica MELHOR com a peça (nota acima do mínimo), do que mais ganha ao que
    menos. Peça que não é equipamento: lista vazia."""
    if getattr(peca, "tipo", None) != "equipamento":
        return []
    minimo = regras()["beneficio_de_pecas"]["minimo"]
    lista = []
    for heroi in herois:
        troca = melhor_troca(heroi, peca)
        if troca is not None and troca[0] > minimo:
            lista.append((heroi, troca[0], troca[2]))
    return sorted(lista, key=lambda par: -par[1])
