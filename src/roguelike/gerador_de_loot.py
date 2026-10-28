"""GeradorDeLoot: o loot de um combate (ou de um evento), SEPARADO por jogador.

    gerador = GeradorDeLoot(run)
    por_jogador = gerador.do_combate(combate, encontro, rng)     # {"local": {"osso": 2, "espada_de_prata": 1}}

Regras (os números ficam em regras.json "loot"):
- cada jogador sorteia o SEU loot, com o seu próprio sorteio: ninguém tira nada de ninguém;
- quem tem o mesmo número de heróis recebe a mesma QUANTIDADE de prêmios (pilhas: um item com a sua quantidade);
- cada prêmio é uma peça de equipamento (com a chance da categoria do encontro) ou uma linha das tabelas dos
  inimigos vencidos e da fase (loot.json; a chance da linha vira peso; cada prêmio é um sorteio independente);
- linhas com chance 1 (a alma do chefe, peças únicas) e a peça garantida da categoria (chefe: lendária;
  mini-chefe: épica, às vezes lendária) vão para TODOS;
- as peças preferem quem ajuda os heróis do jogador (atributos principais da classe) e evitam repetir a peça
  que outro jogador acabou de ganhar;
- gnomos e "loot_extra" (ex.: Rato de Estimação) dão chance de prêmios a mais só ao dono do herói.

Tudo vem da semente: o mesmo combate dá o mesmo loot em todo computador.
"""

import random

from roguelike.dados import regras
from roguelike.loot import chance_final, materiais_da_fase, tabela_de

ATRIBUTOS = ("forca", "destreza", "constituicao", "inteligencia", "fe", "sorte", "carisma")


class Linha:
    """Uma linha de tabela de loot: o item, o peso (a chance) e a quantidade [mínimo, máximo]."""

    def __init__(self, chave, peso, quantidade=(1, 1)):
        self.chave = chave
        self.peso = peso
        self.quantidade = tuple(quantidade)

    def sortear_quantidade(self, rng):
        return rng.randint(*self.quantidade)


class BolsaDeLoot:
    """As linhas de onde saem os prêmios: as garantidas (todo jogador recebe) e as sorteadas (por peso)."""

    def __init__(self):
        self.garantidas = {}
        self.sorteaveis = {}

    def adicionar(self, chave, chance, quantidade=(1, 1)):
        """Linhas do mesmo item se juntam: os pesos somam (mais goblins, mais coisa de goblin)."""
        destino = self.garantidas if chance >= 1 else self.sorteaveis
        peso = 1.0 if chance >= 1 else chance_final(chave, chance)
        if chave in destino:
            atual = destino[chave]
            atual.peso += peso
            atual.quantidade = (max(atual.quantidade[0], quantidade[0]), max(atual.quantidade[1], quantidade[1]))
        elif peso > 0:
            destino[chave] = Linha(chave, peso, quantidade)

    def adicionar_tabela(self, linhas):
        for linha in linhas:
            self.adicionar(linha["item"], linha.get("chance", 0.2), linha.get("quantidade", [1, 1]))

    def sortear(self, rng):
        """Uma linha pelo peso (cada prêmio é um sorteio independente: a linha rara continua rara; a mesma linha
        pode sair de novo e soma na pilha). None = bolsa vazia."""
        linhas = list(self.sorteaveis.values())
        if not linhas:
            return None
        return rng.choices(linhas, weights=[l.peso for l in linhas])[0]


class GeradorDeLoot:
    def __init__(self, run):
        self.run = run
        self.regra = regras()["loot"]
        self.contagem = {}            # id do jogador -> quantos prêmios ganhou (a "mesma quantidade" da regra)

    # ============================================================
    # COMBATE
    # ============================================================
    def do_combate(self, combate, encontro, rng):
        """{id do jogador: {chave: quantidade}} do combate vencido. 'rng' é o sorteio do loot deste combate."""
        categoria = getattr(encontro, "tipo", "combate")
        regra = self.regra["categorias"].get(categoria, self.regra["categorias"]["combate"])
        bolsa = self.bolsa_do_combate(combate)
        estrelas = max(1, getattr(encontro, "estrelas", 1))
        dourados = [i for i in combate.derrotados if getattr(i, "dourado", False)]
        extra = getattr(encontro, "recompensa_extra", None) or {}       # modo difícil (A Corte Completa)
        base = rng.randint(0, 2 ** 32 - 1)
        pecas_dadas = set()
        resultado = {}
        for jogador, herois in self.jogadores_com_herois():
            sorteio = random.Random(f"{base}|{jogador.id}")
            itens = {}
            quantos = self.quantos_premios(herois, estrelas, regra)
            quantos += self.premios_do_dono(herois, sorteio)
            self.sortear_premios(itens, quantos, bolsa, regra, herois, sorteio, pecas_dadas)
            for linha in bolsa.garantidas.values():
                somar(itens, linha.chave, linha.sortear_quantidade(sorteio))
            if regra.get("garantido"):
                self.peca_garantida(itens, regra["garantido"], herois, sorteio, pecas_dadas)
            for _ in dourados:
                self.adicionar_peca(itens, self.peca(sorteio, herois, raridades=regras()["dourados"]["raridades"],
                                                     excluir=pecas_dadas), pecas_dadas)
            if extra.get("raridade_minima"):
                self.adicionar_peca(itens, self.peca(sorteio, herois, minima=extra["raridade_minima"],
                                                     excluir=pecas_dadas), pecas_dadas)
            resultado[jogador.id] = itens
            self.contagem[jogador.id] = quantos + len(bolsa.garantidas) + bool(regra.get("garantido")) + \
                len(dourados) + bool(extra.get("raridade_minima"))
        return resultado

    def bolsa_do_combate(self, combate):
        bolsa = BolsaDeLoot()
        for inimigo in combate.derrotados:
            bolsa.adicionar_tabela(tabela_de(inimigo.chave))
        regiao = self.run.regiao
        bolsa.adicionar_tabela(regiao.drops_da_area + materiais_da_fase(regiao.chave) + regiao.consumiveis_da_area)
        return bolsa

    def quantos_premios(self, herois, estrelas, regra):
        """Por jogador: base + por herói + por estrela acima de 1 (+ o extra da categoria), com o bônus da run."""
        premios = self.regra["premios"]
        total = premios["por_jogador"] + premios["por_heroi"] * len(herois) + \
            premios["por_estrela"] * (estrelas - 1) + regra.get("premios_extra", 0)
        return int(total * (1 + self.run.bonus_loot))

    def premios_do_dono(self, herois, rng):
        """Chance de prêmios a mais pelos heróis do jogador: dom de loot (gnomo) e "loot_extra" no equipamento."""
        extras = 0
        for heroi in herois:
            if not heroi.esta_vivo():
                continue
            chance = (heroi.dados_da_raca.chance_de_loot() if heroi.dados_da_raca else 0) + heroi.bonus("loot_extra")
            if chance and rng.random() < chance:
                extras += 1
        return extras

    def sortear_premios(self, itens, quantos, bolsa, regra, herois, rng, pecas_dadas):
        chance_de_peca = regra.get("chance_de_equipamento", 0)
        for _ in range(quantos):
            if rng.random() < chance_de_peca:
                peca = self.peca(rng, herois, minima=regra.get("raridade_minima"), excluir=pecas_dadas)
                if peca is not None:
                    self.adicionar_peca(itens, peca, pecas_dadas)
                    continue
            linha = bolsa.sortear(rng)
            if linha is not None:
                somar(itens, linha.chave, linha.sortear_quantidade(rng))

    def garantido_do_tier(self, garantido):
        """A regra da peça garantida para o tier da fase: {"raridade", "chance_de_lendario"} ou, por tier,
        {"1": {...}, "2": {...}} (vale a do maior tier até o da fase)."""
        if "raridade" in garantido:
            return garantido
        tier = max(1, self.run.regiao.tier)
        tiers = sorted(int(t) for t in garantido)
        escolhido = max((t for t in tiers if t <= tier), default=tiers[0])
        return garantido[str(escolhido)]

    def peca_garantida(self, itens, garantido, herois, rng, pecas_dadas):
        """A peça que a categoria garante a cada jogador (ex.: chefe: épica no Ato I, lendária depois)."""
        garantido = self.garantido_do_tier(garantido)
        raridade = garantido["raridade"]
        if rng.random() < garantido.get("chance_de_lendario", 0):
            raridade = "lendario"
        peca = self.peca(rng, herois, exata=raridade, excluir=pecas_dadas)
        self.adicionar_peca(itens, peca, pecas_dadas)

    @staticmethod
    def adicionar_peca(itens, peca, pecas_dadas):
        if peca is not None:
            somar(itens, peca, 1)
            pecas_dadas.add(peca)

    # ============================================================
    # EVENTOS
    # ============================================================
    def de_evento(self, dados, rng):
        """{id do jogador: {chave: quantidade}} de um prêmio de evento (eventos.json, consequência "premio"):
        por_jogador + por_heroi x heróis prêmios, da bolsa da fase (drops da fase + as tabelas dos inimigos dela +
        "itens"), com chance_de_equipamento (raridade_minima) e chance_de_lendario (uma peça lendária a mais)."""
        bolsa = BolsaDeLoot()
        regiao = self.run.regiao
        bolsa.adicionar_tabela(regiao.drops_da_area + materiais_da_fase(regiao.chave) + regiao.consumiveis_da_area)
        for chave in regiao.inimigos:          # o que se acha por aqui: as tabelas dos inimigos da fase (sem as únicas)
            bolsa.adicionar_tabela([linha for linha in tabela_de(chave) if linha.get("chance", 0.2) < 1])
        bolsa.adicionar_tabela(dados.get("itens", []))
        regra = {"chance_de_equipamento": dados.get("chance_de_equipamento", 0),
                 "raridade_minima": dados.get("raridade_minima")}
        base = rng.randint(0, 2 ** 32 - 1)
        pecas_dadas = set()
        resultado = {}
        for jogador, herois in self.jogadores_com_herois():
            sorteio = random.Random(f"{base}|{jogador.id}")
            itens = {}
            quantos = dados.get("por_jogador", 0) + dados.get("por_heroi", 0) * len(herois)
            self.sortear_premios(itens, quantos, bolsa, regra, herois, sorteio, pecas_dadas)
            for linha in bolsa.garantidas.values():
                somar(itens, linha.chave, linha.sortear_quantidade(sorteio))
            lendaria = sorteio.random() < dados.get("chance_de_lendario", 0)
            if lendaria:
                self.adicionar_peca(itens, self.peca(sorteio, herois, exata="lendario", excluir=pecas_dadas),
                                    pecas_dadas)
            resultado[jogador.id] = itens
            self.contagem[jogador.id] = quantos + len(bolsa.garantidas) + lendaria
        return resultado

    # ============================================================
    # PEÇAS
    # ============================================================
    def peca(self, rng, herois, minima=None, exata=None, raridades=None, excluir=()):
        """A chave de uma peça de equipamento, ou None se não houver nenhuma.

        Sem 'exata': raridade pelos pesos do tier da fase (só peças com tier de 1 até o da fase), nunca abaixo de
        'minima' (e só as 'raridades', se vier a lista). Com 'exata': essa raridade, do tier mais baixo em que ela
        existe (ou o da fase, se for maior): o chefe do Ato I também dá uma lendária.
        A peça prefere quem ajuda os heróis do jogador e evita as de 'excluir' (as que outros jogadores ganharam)."""
        tier = max(1, self.run.regiao.tier)
        if exata is not None:
            raridade = exata
            limite = max(tier, menor_tier(exata))
        else:
            raridade = self.sortear_raridade(rng, tier, minima, raridades)
            limite = tier
        if raridade is None:
            return None
        candidatas = [p for p in pecas_da_raridade(raridade) if p.tier <= limite]
        candidatas = [p for p in candidatas if p.chave not in excluir] or candidatas
        if not candidatas:
            return None
        pesos = [self.peso_da_peca(p, herois) for p in candidatas]
        if not any(pesos):
            pesos = [1] * len(candidatas)
        return rng.choices(candidatas, weights=pesos)[0].chave

    def sortear_raridade(self, rng, tier, minima=None, raridades=None):
        ordem = list(regras()["raridades"])
        tabela = regras()["drops"]["equipamento"]["pesos"]
        pesos = dict(tabela.get(str(min(tier, max(int(t) for t in tabela))), {}))
        if raridades:
            pesos = {r: p for r, p in pesos.items() if r in raridades}
        if minima in ordem:
            pesos = {r: p for r, p in pesos.items()
                     if r in ordem and ordem.index(r) >= ordem.index(minima) or r == "amaldicoado"}
        possiveis = [r for r, p in pesos.items() if p > 0 and any(x.tier <= tier for x in pecas_da_raridade(r))]
        if not possiveis:
            return None
        return rng.choices(possiveis, weights=[pesos[r] for r in possiveis])[0]

    def peso_da_peca(self, peca, herois):
        """Mais peso para as peças que ajudam os heróis do jogador (atributos principais nos modificadores);
        peso zero se nenhum herói dele pode usar (classe ou raça)."""
        pesos = self.regra["pesos_das_pecas"]
        if herois and not any(peca.pode_equipar(h) for h in herois):
            return 0
        atributos = {a for a in peca.modificadores if a in ATRIBUTOS}
        if not atributos:
            return pesos["neutra"]
        principais = {a for h in herois for a in h.classe.atributos_principais}
        return pesos["ajuda_o_jogador"] if atributos & principais else pesos["de_outra_classe"]

    def jogadores_com_herois(self):
        grupo = self.run.grupo
        return [(j, grupo.herois_de(j)) for j in grupo.jogadores if grupo.herois_de(j)]


# ============================================================
# AJUDANTES
# ============================================================

def somar(itens, chave, quantidade):
    if quantidade > 0:
        itens[chave] = itens.get(chave, 0) + quantidade


_por_raridade = {}


def pecas_da_raridade(raridade):
    """As peças sorteáveis (tier 1 ou mais) dessa raridade, em ordem de chave."""
    if not _por_raridade:
        from roguelike.itens import todos_os_itens, Equipamento
        for chave, objeto in sorted(todos_os_itens().items()):
            if isinstance(objeto, Equipamento) and objeto.tier >= 1:        # (forja anã e almas: tier 0)
                _por_raridade.setdefault(objeto.raridade, []).append(objeto)
    return _por_raridade.get(raridade, [])


def menor_tier(raridade):
    """O tier mais baixo em que existe peça dessa raridade (ex.: lendária: 3)."""
    return min((p.tier for p in pecas_da_raridade(raridade)), default=1)
