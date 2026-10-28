"""Bestiário do Estudioso: o que já se sabe de cada inimigo (pelos abates de todas as runs).

    0 abates                  silhueta "???"
    1 abate                   nome, família, golpes, número de abates e a história (lore.json, chefes; o resto
                              das histórias em partes chega com mais vitórias: regras.bestiario "partes_da_lore")
    regras.bestiario          fraquezas e resistências; depois o loot conhecido

As páginas são agrupadas pelas regiões onde o inimigo aparece; os chefes secretos ficam em "Segredos"
e o resto em "Outros". Fases seladas ("disponivel": false, ex.: o Reino dos Ratos antes de ficar pronto)
não ganham aba: não entregam o segredo antes da hora.
"""

from roguelike import elementos
from roguelike.dados import carregar, sem_comentarios, regras
from roguelike.golpes import golpe
from roguelike.inimigos import fichas
from roguelike.loot import tabela_de


def secoes():
    """[(chave, nome, [inimigos])]: uma por região + "outros" (inimigos de eventos e circo...)."""
    dados = carregar("regioes")
    vistos, resultado = set(), []
    for chave, regiao in sem_comentarios(dados["regioes"]).items():
        if not regiao.get("disponivel", True):
            continue
        lista = []
        for campo in ("inimigos", "elites", "nomeados", "mini_chefes"):
            lista += regiao.get(campo, [])
        for zona in regiao.get("zonas", []) + ([regiao["zona_do_chefe"]] if regiao.get("zona_do_chefe") else []):
            lista += zona.get("inimigos", []) + zona.get("mini_chefes", [])   # fases com zonas (o Reino dos Ratos)
        if regiao.get("chefe"):
            lista.append(regiao["chefe"])
        lista += regiao.get("formas_do_chefe", [])          # ex.: o Dragão do Eclipse, 3ª forma do Bispo
        lista += regiao.get("tambem_no_bestiario", [])      # quem não sai no sorteio (os ratos da roda, o Queijo Real)
        lista = [c for i, c in enumerate(lista) if c in fichas() and c not in lista[:i]]
        vistos |= set(lista)
        resultado.append((chave, regiao.get("nome_curto", regiao["nome"]), lista))
    secretos = [c for c in sem_comentarios(dados.get("chefes_secretos", {})) if c in fichas()]
    if secretos:
        vistos |= set(secretos)
        resultado.append(("segredos", "Segredos", secretos))
    outros = [c for c in fichas() if c not in vistos]
    if outros:
        resultado.append(("outros", "Outros", outros))
    return resultado


class Pagina:
    """A página de um inimigo no bestiário, do ponto de vista do progresso."""

    def __init__(self, chave, progresso):
        self.chave = chave
        self.ficha = fichas()[chave]
        self.abates = progresso.abates.get(chave, 0)
        especial = self.ficha.get("categoria", "comum") != "comum"
        self.limites = regras()["bestiario"]["chefes" if especial else "comum"]

    @property
    def conhecido(self):
        return self.abates >= 1

    @property
    def fraquezas_reveladas(self):
        return self.abates >= self.limites["fraquezas"]

    @property
    def loot_revelado(self):
        return self.abates >= self.limites["loot"]

    @property
    def nome(self):
        return self.ficha["nome"] if self.conhecido else "???"

    @property
    def sprite(self):
        return self.ficha.get("sprite", self.chave)

    def familia(self):
        return carregar("regioes")["familias"].get(self.ficha.get("familia"), self.ficha.get("familia", ""))

    def categoria(self):
        return {"comum": "comum", "elite": "elite", "nomeado": "nomeado", "mini_chefe": "mini-chefe",
                "chefe": "chefe"}.get(self.ficha.get("categoria", "comum"), "")

    def golpes(self):
        return [golpe(c).nome for c in self.ficha.get("habilidades", [])]

    def afinidades(self):
        """(fracos, resiste) a elementos, pelas resistências da família e do inimigo."""
        resistencias = elementos.resistencias_do_inimigo(self.chave, self.ficha.get("familia"), self.ficha.get("resistencias"))
        fracos = [e for e, v in resistencias.items() if v >= elementos.LIMIAR_EFETIVIDADE]
        resiste = [e for e, v in resistencias.items() if v <= -elementos.LIMIAR_EFETIVIDADE]
        return fracos, resiste

    def loot(self):
        """[(chave do item, chance)] da tabela própria do inimigo (sem as linhas que valem para todos)."""
        comuns = {linha["item"] for linha in carregar("loot").get("todos", [])}
        return [(linha["item"], linha["chance"]) for linha in tabela_de(self.chave) if linha["item"] not in comuns]

    def partes_da_lore(self):
        """As partes da história (lore.json: um texto = uma parte só)."""
        historia = sem_comentarios(carregar("lore")).get(self.chave)
        return [] if historia is None else ([historia] if isinstance(historia, str) else list(historia))

    def lore(self):
        """A história do chefe (lore.json), só depois de vencê-lo; None se não tiver. Em partes (o Rei e a Rainha dos
        Ratos), cada parte pede as vitórias de regras bestiario "partes_da_lore" (ex.: o resto só na 3ª)."""
        vitorias = regras()["bestiario"].get("partes_da_lore", [1])
        liberadas = [p for i, p in enumerate(self.partes_da_lore()) if self.abates >= vitorias[min(i, len(vitorias) - 1)]]
        return "\n\n".join(liberadas) if self.conhecido and liberadas else None

    def falta_para_a_lore(self):
        """Vitórias que faltam para a próxima parte da história (0 = já está inteira)."""
        vitorias = regras()["bestiario"].get("partes_da_lore", [1])
        for i in range(len(self.partes_da_lore())):
            precisa = vitorias[min(i, len(vitorias) - 1)]
            if self.abates < precisa:
                return precisa - self.abates
        return 0

    def falta_para(self, parte):
        return max(0, self.limites[parte] - self.abates)


def total_conhecido(progresso):
    """(inimigos já registrados, total)."""
    return sum(1 for c in fichas() if progresso.abates.get(c, 0) > 0), len(fichas())
