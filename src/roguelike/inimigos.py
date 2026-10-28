"""Fichas dos inimigos e invocações (inimigos.json).

Cada ficha tem: nome, sprite, família, tamanho, papel (o mesmo do
catálogo de sprites), vida, defesa, atributos, iniciativa, habilidades,
IA, XP e ouro. Chefes têm "padrao" (ataques pela energia).
"""

from roguelike.dados import carregar, sem_comentarios, regras
from roguelike.lutador import Inimigo, Invocacao


def fichas():
    return sem_comentarios(carregar("inimigos")["inimigos"])


def fichas_de_invocacao():
    return sem_comentarios(carregar("inimigos")["invocacoes"])


def ficha(chave):
    try:
        return fichas()[chave]
    except KeyError:
        raise KeyError(f"Inimigo desconhecido: {chave}") from None


def ficha_de_invocacao(chave):
    try:
        return fichas_de_invocacao()[chave]
    except KeyError:
        raise KeyError(f"Invocação desconhecida: {chave}") from None


def criar_inimigo(chave):
    """Inimigo da ficha; com "bando" na ficha, um Bando (vários bichos num lutador só); com "no_da_roda", o nó da
    Rainha dos Ratos (roguelike/roda.py)."""
    dados = ficha(chave)
    if "bando" in dados:
        from roguelike.bando import Bando
        return Bando(chave, dados)
    if dados.get("no_da_roda"):
        from roguelike.roda import NoDeCaudas
        return NoDeCaudas(chave, dados)
    return Inimigo(chave, dados)


def ajuste_de_tier(dados, tier_da_fase):
    """Ajustes de um inimigo que veio de outra fase (ex.: goblin no Pântano), para ele ter a força média
    dos inimigos desta fase (regras.json "ajuste_de_tier"). {} se ele é do mesmo tier."""
    tabela = regras().get("ajuste_de_tier")
    tier = dados.get("tier")
    if not tabela or not tier or not tier_da_fase or tier == tier_da_fase:
        return {}
    de, para = str(tier), str(tier_da_fase)
    if de not in tabela["vida"] or para not in tabela["vida"]:
        return {}
    # o dano final é (1 + bônus): multiplicar o dano por (poder da fase / poder dele) = somar este tanto ao bônus
    dano = (1 + dados.get("bonus", {}).get("dano_causado", 0)) * (tabela["poder"][para] / tabela["poder"][de] - 1)
    return {"vida_percentual": tabela["vida"][para] / tabela["vida"][de] - 1, "dano_causado": dano,
            "defesa": round(tabela["defesa"][para] - tabela["defesa"][de])}


def ajustar_recompensa_de_tier(inimigo, tier_da_fase):
    """O visitante de outra fase também dá o XP e o ouro de um inimigo desta fase (regras "ajuste_de_tier")."""
    tabela = regras().get("ajuste_de_tier")
    de, para = str(inimigo.ficha.get("tier")), str(tier_da_fase)
    if not tabela or de == para or de not in tabela.get("xp", {}) or para not in tabela.get("xp", {}):
        return
    inimigo.recompensa_xp = max(1, round(inimigo.recompensa_xp * tabela["xp"][para] / tabela["xp"][de]))
    fator = tabela["ouro"][para] / tabela["ouro"][de]
    inimigo.recompensa_ouro = tuple(max(1, round(o * fator)) for o in inimigo.recompensa_ouro)


def criar_invocacao(chave, dono, nivel=1):
    return Invocacao(chave, ficha_de_invocacao(chave), dono, nivel)


def buscar(familia=None, tamanho=None, papel=None, categoria=None, tier=None):
    """Chaves dos inimigos que combinam com os filtros (None = qualquer um)."""
    resultado = []
    for chave, dados in fichas().items():
        if familia and dados["familia"] != familia:
            continue
        if tamanho and dados["tamanho"] != tamanho:
            continue
        if papel and dados["papel"] != papel:
            continue
        if categoria and dados.get("categoria", "comum") != categoria:
            continue
        if tier and dados.get("tier") != tier:
            continue
        resultado.append(chave)
    return resultado
