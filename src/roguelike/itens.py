"""Itens do roguelike (lidos do itens.json).

    Item (base: nome, raridade, preço, ícone)
    ├── Material      componentes, minérios, peças do circo e almas de chefe
    ├── Equipamento   bônus, passivas, set, restrições de classe/raça e às vezes um golpe
    │   ├── Arma          arma principal (uma ou duas mãos) ou secundária (escudo, lanterna, arma leve)
    │   ├── Armadura      cabeça, peitoral, calças, botas ou capa
    │   └── Acessorio     amuleto
    └── Consumivel    poções, comida, bombas e pergaminhos (usados como uma habilidade)
        └── Tomo

Cada subclasse de Equipamento sabe em que espaços entra (espacos_possiveis) e a que tipo de
afixo ela aceita (tipo_de_peca): por isso o resto do código não precisa de "if espaco == ...".

Os objetos Item são "fichas": existe um só objeto para cada tipo de item.
Os inventários guardam apenas a chave e a quantidade. Peças com afixos sorteados são "exemplares"
(roguelike/exemplares.py): cópias da ficha com chave própria, ex.: "espada_de_prata#K3D9Q".
"""

from roguelike.dados import carregar, sem_comentarios, regras
from roguelike.efeitos_habilidade import criar_efeito


class Item:
    tipo = "item"

    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.descricao = dados.get("descricao", "")
        self.raridade = dados.get("raridade", "comum")
        self.preco = dados.get("preco", 1)
        self.tier = dados.get("tier", 0)              # região a partir da qual aparece em lojas (0 = nunca)
        self.categoria = dados.get("categoria", "")
        self.icone = dados.get("icone", chave)
        self.modificadores = {}

    def preco_de_venda(self):
        return max(1, int(self.preco * regras()["economia"]["venda"]))

    def nome_da_raridade(self):
        return regras()["raridades"][self.raridade]["nome"]

    def cor_da_raridade(self):
        return tuple(regras()["raridades"][self.raridade]["cor"])

    def __repr__(self):
        return f"{type(self).__name__}({self.chave!r})"


class Material(Item):
    tipo = "material"

    def revela_receitas(self):
        """Minérios, peças do circo e almas revelam receitas escondidas."""
        return self.categoria in ("minerio", "peca_circo", "alma")


def ordem_da_raridade(raridade):
    """Posição da raridade (comum = 0 ... amaldiçoado = a última): para ordenar e comparar."""
    return list(regras()["raridades"]).index(raridade)


def afixos_da_raridade(raridade):
    return regras()["raridades"][raridade].get("afixos", 0)


class Equipamento(Item):
    tipo = "equipamento"
    tipo_de_peca = "equipamento"            # "arma", "armadura" ou "acessorio" (os afixos usam)

    def __init__(self, chave, dados):
        super().__init__(chave, dados)
        self.espaco = dados["espaco"]                  # espaço principal (regras.json "espacos")
        self.modificadores = dict(dados.get("modificadores", {}))
        self.passivas = list(dados.get("passivas", []))
        self.habilidade = dados.get("habilidade")      # habilidade extra enquanto equipado
        self.classes = list(dados.get("classes", []))  # vazio = qualquer classe
        self.racas = list(dados.get("racas", []))      # vazio = qualquer raça
        self.set = dados.get("set")                    # sets.json
        self.imune = list(dados.get("imune", []))      # status que o herói ignora enquanto usa a peça
        self.base = chave                              # exemplares guardam a ficha de origem
        self.afixos = []                               # [(chave do afixo, {valor: número})] (só exemplares)

    def espacos_possiveis(self):
        return [self.espaco]

    def pode_equipar(self, heroi):
        return self.motivo_de_nao_servir(heroi) is None

    def motivo_de_nao_servir(self, heroi):
        """Texto curto se o herói não pode usar a peça (classe ou raça), ou None."""
        if self.classes and heroi.classe.chave not in self.classes:
            return "Classe não pode usar"
        if self.racas and getattr(heroi, "raca", None) not in self.racas:
            return "Raça não pode usar"
        return None

    def travada(self):
        """Amaldiçoada: depois de equipada só sai na próxima fogueira."""
        return regras()["raridades"][self.raridade].get("travada", False)

    def eh_exemplar(self):
        return self.chave != self.base


class Arma(Equipamento):
    tipo_de_peca = "arma"

    def __init__(self, chave, dados):
        super().__init__(chave, dados)
        self.maos = dados.get("maos", 1)               # 2 = ocupa também a mão da arma secundária
        self.leve = dados.get("leve", False)           # arma leve: pode ir na mão secundária

    def espacos_possiveis(self):
        if self.espaco == "arma_secundaria":
            return ["arma_secundaria"]
        return ["arma", "arma_secundaria"] if self.leve else ["arma"]

    def duas_maos(self):
        return self.maos >= 2


class Armadura(Equipamento):
    tipo_de_peca = "armadura"


class Acessorio(Equipamento):
    tipo_de_peca = "acessorio"


CLASSE_POR_ESPACO = {"arma": Arma, "arma_secundaria": Arma, "amuleto": Acessorio}


def criar_equipamento(chave, dados):
    """A subclasse certa pelo espaço da peça (armas, acessórios; o resto é armadura)."""
    return CLASSE_POR_ESPACO.get(dados["espaco"], Armadura)(chave, dados)


class Consumivel(Item):
    tipo = "consumivel"

    def __init__(self, chave, dados):
        super().__init__(chave, dados)
        self.alvo = dados.get("alvo", "aliado")
        self.efeitos = [criar_efeito(e) for e in dados.get("efeitos", [])]
        self.fora_de_combate = dados.get("fora_de_combate", False)
        if dados.get("so_fora_de_combate"):              # ex.: Mapa Rasgado e Incenso (usados no mapa)
            self.usavel_em_combate = False

    def escolhe_alvo(self):
        return self.alvo in ("inimigo", "aliado", "aliado_caido")

    def resumo(self):
        return "; ".join(e.resumo(1) for e in self.efeitos if e.resumo(1))

    def descricao_curta(self, nivel=1):
        """Uma linha com efeito e alvo (itens não gastam energia)."""
        from roguelike.golpes import descricao_curta
        return descricao_curta(self.resumo(), "gasta o item", self.alvo)


class Tomo(Consumivel):
    """Livro que ensina um golpe a quem o ler (fora do combate). O golpe vai para os espaços,
    ou o jogador escolhe onde ele fica (o que sair vai para o grimório)."""

    usavel_em_combate = False

    def __init__(self, chave, dados):
        dados = {"alvo": "aliado", "fora_de_combate": True, "categoria": "tomo", **dados}
        super().__init__(chave, dados)
        self.ensina = dados["ensina"]

    def golpe(self):
        from roguelike.golpes import golpe
        return golpe(self.ensina)

    def resumo(self):
        return f"ensina {self.golpe().nome}"

    def pode_ler(self, heroi):
        return heroi.esta_vivo() and not heroi.golpes.sabe(self.ensina)


Consumivel.usavel_em_combate = True

_itens = {}


def todos_os_itens():
    """Dicionário chave -> Item com todos os itens do jogo."""
    if not _itens:
        dados = carregar("itens")
        secoes = (("materiais", Material), ("equipamentos", criar_equipamento), ("consumiveis", Consumivel), ("tomos", Tomo))
        for secao, classe in secoes:
            for chave, info in sem_comentarios(dados.get(secao, {})).items():
                if chave in _itens:
                    raise ValueError(f"Item repetido: {chave}")
                _itens[chave] = classe(chave, info)
    return _itens


def item(chave):
    try:
        return todos_os_itens()[chave]
    except KeyError:
        if "#" in chave:                               # peça com afixos (registrada pela run ou pelo arsenal)
            from roguelike.exemplares import exemplar
            encontrado = exemplar(chave)
            if encontrado is not None:
                return encontrado
        raise KeyError(f"Item desconhecido: {chave}") from None


def existe(chave):
    if "#" in chave:
        from roguelike.exemplares import exemplar
        return exemplar(chave) is not None
    return chave in todos_os_itens()
