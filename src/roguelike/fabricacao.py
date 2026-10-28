"""Fabricação: transforma materiais em itens (receitas.json).

Uma receita aparece quando o grupo tem algum dos ingredientes. As
receitas escondidas só aparecem depois de "descobertas" (ao pegar um
minério, peça do circo ou alma de chefe, ou ao comprar a receita).

Os ingredientes podem vir de mais de um lugar (Estoque): a mochila do herói e o baú da equipe.
situacao() diz se a receita sai só com a mochila, se precisa do baú ou o que falta.
"""

SO_MOCHILA, COM_BAU, FALTA = "mochila", "com_bau", "falta"


class Estoque:
    """Vários inventários vistos como um só (ex.: mochila + baú), na ordem em que são gastos."""

    def __init__(self, *inventarios):
        self.inventarios = [i for i in inventarios if i is not None]

    def quantidade(self, chave):
        return sum(i.quantidade(chave) for i in self.inventarios)

    def tem(self, chave, quantidade=1):
        return self.quantidade(chave) >= quantidade

    def remover(self, chave, quantidade=1):
        """Gasta do primeiro inventário e, se faltar, dos seguintes."""
        if not self.tem(chave, quantidade):
            return False
        for inventario in self.inventarios:
            tirar = min(quantidade, inventario.quantidade(chave))
            if tirar:
                inventario.remover(chave, tirar)
                quantidade -= tirar
        return True

from roguelike.dados import carregar, sem_comentarios
from roguelike.itens import item


class Receita:
    def __init__(self, chave, dados):
        self.chave = chave
        self.resultado = dados["resultado"]
        self.quantidade = dados.get("quantidade", 1)
        self.ingredientes = dict(dados["ingredientes"])
        self.escondida = dados.get("escondida", False)
        self.revelada_por = list(dados.get("revelada_por", []))
        self.requer_raca = dados.get("requer_raca")       # só quem tem essa raça no grupo forja (Anão)
        self.liberada_por = dados.get("liberada_por")     # marco (ex.: "chefe:forjador_antigo") que a libera para sempre

    def liberada_para(self, racas):
        return self.requer_raca is None or self.requer_raca in racas

    def item_resultado(self):
        return item(self.resultado)

    def nome(self):
        return self.item_resultado().nome

    def faltando(self, inventario):
        """{ingrediente: quantos faltam} (vazio = dá para fabricar)."""
        falta = {}
        for chave, quantidade in self.ingredientes.items():
            if inventario.quantidade(chave) < quantidade:
                falta[chave] = quantidade - inventario.quantidade(chave)
        return falta

    def pode_fabricar(self, inventario):
        return not self.faltando(inventario)

    def __repr__(self):
        return f"Receita({self.chave!r})"


_receitas = {}


def todas_as_receitas():
    if not _receitas:
        for chave, dados in sem_comentarios(carregar("receitas")).items():
            _receitas[chave] = Receita(chave, dados)
    return _receitas


def receita(chave):
    return todas_as_receitas()[chave]


def receitas_reveladas_por(chave_item):
    """Receitas escondidas que o item revela."""
    return [r.chave for r in todas_as_receitas().values() if r.escondida and chave_item in r.revelada_por]


def receitas_visiveis(inventario, descobertas, racas=()):
    """Receitas que aparecem na tela de fabricação, as que dá para fazer primeiro.

    racas = raças dos heróis do grupo: as receitas exclusivas (requer_raca) aparecem sempre para elas.
    """
    visiveis = []
    for r in todas_as_receitas().values():
        if not r.liberada_para(racas):
            continue
        if r.requer_raca is not None:
            visiveis.append(r)
            continue
        if r.escondida and r.chave not in descobertas:
            continue
        if r.chave in descobertas or any(inventario.tem(chave) for chave in r.ingredientes):
            visiveis.append(r)
    visiveis.sort(key=lambda r: (not r.pode_fabricar(inventario), r.nome()))
    return visiveis


def fabricar(receita_escolhida, inventario, destino=None):
    """Gasta os ingredientes (de um inventário ou de um Estoque) e guarda o resultado em 'destino'
    (padrão: o próprio inventário; se não couber lá, no último do estoque). Devolve False se faltar algo."""
    if not receita_escolhida.pode_fabricar(inventario):
        return False
    for chave, quantidade in receita_escolhida.ingredientes.items():
        inventario.remover(chave, quantidade)
    destino = destino or (inventario.inventarios[-1] if isinstance(inventario, Estoque) else inventario)
    if not destino.adicionar(receita_escolhida.resultado, receita_escolhida.quantidade) and isinstance(inventario, Estoque):
        inventario.inventarios[-1].adicionar(receita_escolhida.resultado, receita_escolhida.quantidade)
    return True


def situacao(receita_escolhida, mochila, bau):
    """SO_MOCHILA (dá só com a mochila), COM_BAU (precisa do baú) ou FALTA (nem com os dois)."""
    if mochila is not None and receita_escolhida.pode_fabricar(mochila):
        return SO_MOCHILA
    if receita_escolhida.pode_fabricar(Estoque(mochila, bau)):
        return COM_BAU
    return FALTA
