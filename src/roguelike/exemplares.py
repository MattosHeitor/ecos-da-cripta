"""Exemplares: peças raras ou melhores com afixos sorteados (afixos.json).

Um exemplar é uma cópia da ficha do itens.json com chave própria ("espada_de_prata#K3D9Q"), nome
com o afixo ("Espada de Prata Lunar da Fúria") e os valores dos afixos somados aos modificadores.
Assim inventário, baú, loja e telas continuam lidando só com chaves.

Os exemplares ficam num registro (este módulo). A run e o arsenal salvam os seus com
exportar() e os devolvem ao registro com importar() ao carregar.
"""

import copy

from roguelike.dados import carregar, sem_comentarios

LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_registro = {}


class Afixo:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.em = list(dados["em"])                  # tipos de peça: arma, armadura, acessorio
        self.valores = dict(dados["valores"])        # valor -> [mínimo, máximo]

    def serve_em(self, peca):
        return peca.tipo_de_peca in self.em

    def sortear(self, rng):
        """{valor: número} sorteado dentro das faixas (inteiros ficam inteiros)."""
        resultado = {}
        for nome, (minimo, maximo) in self.valores.items():
            if isinstance(minimo, int) and isinstance(maximo, int):
                resultado[nome] = rng.randint(minimo, maximo)
            else:
                resultado[nome] = round(rng.uniform(minimo, maximo), 3)
        return resultado


_afixos = {}


def todos_os_afixos():
    if not _afixos:
        for chave, dados in sem_comentarios(carregar("afixos")).items():
            _afixos[chave] = Afixo(chave, dados)
    return _afixos


def montar(base, codigo, afixos):
    """O exemplar: cópia da ficha 'base' com os afixos [(chave, {valor: número})] aplicados."""
    from roguelike.itens import item
    ficha = item(base)
    peca = copy.copy(ficha)
    peca.chave = f"{base}#{codigo}"
    peca.base = base
    peca.afixos = [(chave, dict(valores)) for chave, valores in afixos]
    peca.modificadores = dict(ficha.modificadores)
    for _, valores in peca.afixos:
        for nome, valor in valores.items():
            peca.modificadores[nome] = round(peca.modificadores.get(nome, 0) + valor, 3)
    if peca.afixos:
        primeiro = todos_os_afixos()[peca.afixos[0][0]].nome
        extra = f" +{len(peca.afixos) - 1}" if len(peca.afixos) > 1 else ""
        peca.nome = f"{ficha.nome} {primeiro}{extra}"
    peca.preco = int(ficha.preco * (1 + 0.25 * len(peca.afixos)))
    return peca


def criar_exemplar(base, rng, quantidade=None):
    """Sorteia afixos para a peça 'base' (quantos a raridade manda) e registra o exemplar.

    Se o código sorteado já existe com a MESMA peça (a mesma partida refeita, ou o mesmo sorteio em outro
    computador), devolve a que já existe: o resultado depende só do sorteio, nunca do que o registro já tinha."""
    from roguelike.itens import item, afixos_da_raridade
    ficha = item(base)
    quantidade = afixos_da_raridade(ficha.raridade) if quantidade is None else quantidade
    possiveis = [a for a in todos_os_afixos().values() if a.serve_em(ficha)]
    escolhidos = rng.sample(possiveis, min(quantidade, len(possiveis)))
    codigo = "".join(rng.choice(LETRAS) for _ in range(5))
    afixos = [(a.chave, a.sortear(rng)) for a in escolhidos]
    while f"{base}#{codigo}" in _registro and not _mesma_peca(_registro[f"{base}#{codigo}"], base, afixos):
        codigo = "".join(rng.choice(LETRAS) for _ in range(5))
    if f"{base}#{codigo}" in _registro:
        return _registro[f"{base}#{codigo}"]
    peca = montar(base, codigo, afixos)
    _registro[peca.chave] = peca
    return peca


def _mesma_peca(peca, base, afixos):
    return peca.base == base and [(a, dict(v)) for a, v in peca.afixos] == [(a, dict(v)) for a, v in afixos]


def exemplar(chave):
    return _registro.get(chave)


def exportar(chaves):
    """{chave: {"base", "afixos"}} dos exemplares entre as chaves (para salvar)."""
    dados = {}
    for chave in chaves:
        peca = _registro.get(chave)
        if peca is not None:
            dados[chave] = {"base": peca.base, "afixos": [[a, v] for a, v in peca.afixos]}
    return dados


def importar(dados):
    """Registra exemplares salvos (ignora os de fichas que não existem mais)."""
    from roguelike.itens import existe
    for chave, info in (dados or {}).items():
        if chave in _registro or not existe(info["base"]):
            continue
        codigo = chave.split("#", 1)[1]
        _registro[chave] = montar(info["base"], codigo, [(a, v) for a, v in info.get("afixos", [])
                                                         if a in todos_os_afixos()])


def eh_exemplar(chave):
    return "#" in chave
