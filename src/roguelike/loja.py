"""Lojas: mercador (itens, materiais e receitas) e alquimista (poções e comida).

O estoque é sorteado pela semente da run. Dá para comprar e vender;
o preço de venda é 40% do preço de compra (regras.json "economia").
"""

from roguelike.dados import regras
from roguelike.fabricacao import todas_as_receitas
from roguelike.itens import todos_os_itens, item


class Oferta:
    """Uma coisa à venda: um item ou uma receita escondida."""

    def __init__(self, tipo, chave, preco, estoque=1):
        self.tipo = tipo            # "item" ou "receita"
        self.chave = chave
        self.preco = preco
        self.estoque = estoque

    def nome(self):
        if self.tipo == "receita":
            return "Receita: " + todas_as_receitas()[self.chave].nome()
        return item(self.chave).nome

    def esgotada(self):
        return self.estoque <= 0


class Loja:
    """Mercador comum. Subclasses mudam o que é vendido."""

    nome = "Mercador Errante"
    sprite = "mercador"
    QUANTIDADE_ITENS = 7

    def __init__(self, rng, tier, descobertas=(), da_regiao=()):
        self.ofertas = []
        self.preencher(rng, tier, set(descobertas))
        self.adicionar_da_regiao(rng, da_regiao)

    def adicionar_da_regiao(self, rng, chaves):
        """Consumíveis típicos da fase (o mercador comum não vende: fica com o alquimista)."""

    def itens_possiveis(self, tier):
        return [i for i in todos_os_itens().values() if 0 < i.tier <= tier]

    def preencher(self, rng, tier, descobertas):
        possiveis = self.itens_possiveis(tier)
        pesos = [regras()["raridades"][i.raridade]["peso_loja"] for i in possiveis]
        escolhidos = []
        while possiveis and len(escolhidos) < self.QUANTIDADE_ITENS:
            escolhido = rng.choices(possiveis, weights=pesos)[0]
            indice = possiveis.index(escolhido)
            possiveis.pop(indice)
            pesos.pop(indice)
            escolhidos.append(escolhido)
        for objeto in escolhidos:
            unico = objeto.tipo == "equipamento" or objeto.categoria == "tomo"
            estoque = 1 if unico else rng.randint(2, 4)
            self.ofertas.append(Oferta("item", objeto.chave, objeto.preco, estoque))
        self.adicionar_receitas(rng, tier, descobertas)

    def adicionar_receitas(self, rng, tier, descobertas):
        escondidas = [r for r in todas_as_receitas().values()
                      if r.escondida and r.chave not in descobertas and item(r.resultado).raridade != "lendario"]
        if escondidas:
            receita = rng.choice(escondidas)
            preco = int(item(receita.resultado).preco * 0.6)
            self.ofertas.append(Oferta("receita", receita.chave, preco))

    # ---------------- compra e venda ----------------
    def comprar(self, indice, run, jogador=None):
        """O 'jogador' (sem ele, o primeiro) compra a oferta com o próprio ouro; o item vai para a mochila dele
        (cheia: para o baú). Devolve True se deu certo."""
        jogador = jogador or run.grupo.jogadores[0]
        if not 0 <= indice < len(self.ofertas):
            return False
        oferta = self.ofertas[indice]
        if oferta.esgotada() or jogador.ouro < oferta.preco:
            return False
        jogador.ouro -= oferta.preco
        oferta.estoque -= 1
        if oferta.tipo == "receita":
            run.descobertas.add(oferta.chave)
        else:
            run.receber_itens({oferta.chave: 1}, jogador.mochila)
        return True

    @staticmethod
    def vender(inventario, chave, run, quantidade=1, jogador=None):
        """Vende itens de um inventário; o ouro vai para o 'jogador' (sem ele, o primeiro). Devolve o ganho."""
        if not inventario.remover(chave, quantidade):
            return 0
        ganho = item(chave).preco_de_venda() * quantidade
        (jogador or run.grupo.jogadores[0]).ouro += ganho
        return ganho


class Alquimista(Loja):
    """Vende só poções, comida e bombas (mais baratas)."""

    nome = "Alquimista"
    sprite = "alquimista"
    QUANTIDADE_ITENS = 6

    def itens_possiveis(self, tier):
        return [i for i in todos_os_itens().values()
                if i.tipo == "consumivel" and i.categoria in ("pocao", "comida", "bomba") and 0 < i.tier <= tier]

    def preencher(self, rng, tier, descobertas):
        super().preencher(rng, tier, descobertas)
        for oferta in self.ofertas:
            oferta.preco = max(1, int(oferta.preco * 0.85))

    def adicionar_receitas(self, rng, tier, descobertas):
        pass

    def adicionar_da_regiao(self, rng, chaves):
        vendidos = {o.chave for o in self.ofertas}
        for chave in chaves:
            if chave not in vendidos:
                self.ofertas.append(Oferta("item", chave, max(1, int(item(chave).preco * 0.85)), rng.randint(2, 3)))
