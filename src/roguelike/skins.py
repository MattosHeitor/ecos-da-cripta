"""Skins: só visual, em camadas (skins.json).

    roupa   troca a folha inteira do herói (sprite)
    chapeu  adorno desenhado sobre a cabeça (acessorio)
    arma    encantamento desenhado na arma (acessorio)

O herói guarda as escolhidas em heroi.visual = {"roupa": chave, "chapeu": chave, "arma": chave}
e o nome do sprite vira "base+@acessorio+@acessorio" (visual/sprites_macabros.py junta as camadas).
Skins de conquista são liberadas pelas conquistas; skins raras (com "preco") são compradas no Taverneiro.
"""

from roguelike.dados import carregar, sem_comentarios

CAMADAS = ("roupa", "chapeu", "arma")
SUFIXO_DESARMADO = "_desarmado"           # roupa sem a arma da classe (visual/sprites_macabros.py volta à normal se faltar)
NOMES_DAS_CAMADAS = {"roupa": "Roupa", "chapeu": "Chapéu", "arma": "Arma"}


class Skin:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.descricao = dados.get("descricao", "")
        self.camada = dados["camada"]
        self.classes = list(dados.get("classes", []))     # vazio = todas
        self.sprite = dados.get("sprite")                 # roupa: folha inteira
        self.acessorio = dados.get("acessorio")           # chapéu/arma: camada sobreposta
        self.preco = dados.get("preco", 0)                # skin rara: vendida na vitrine do Taverneiro (Brasas)

    def serve_para(self, chave_classe):
        return not self.classes or chave_classe in self.classes

    def __repr__(self):
        return f"Skin({self.chave!r})"


_skins = {}


def todas_as_skins():
    if not _skins:
        for chave, dados in sem_comentarios(carregar("skins")).items():
            _skins[chave] = Skin(chave, dados)
    return _skins


def skin(chave):
    return todas_as_skins()[chave]


def skins_a_venda():
    """Skins raras (com preço): o Taverneiro sorteia algumas a cada run."""
    return [s for s in todas_as_skins().values() if s.preco]


def skins_para(chave_classe, camada):
    return [s for s in todas_as_skins().values() if s.camada == camada and s.serve_para(chave_classe)]


def nome_do_sprite(base, visual, extras=(), desarmado=False):
    """Monta o nome do sprite com as camadas: "guerreiro+@raca_anao+@aureola+@brasa".

    extras = camadas que não são skins (traço da raça, peças equipadas), desenhadas logo acima da roupa.
    desarmado = a roupa sem a arma da classe ("<roupa>_desarmado"), quando há arma equipada.
    """
    partes = [base]
    roupa = visual.get("roupa")
    if roupa and roupa in todas_as_skins():
        partes[0] = skin(roupa).sprite
    if desarmado:
        partes[0] += SUFIXO_DESARMADO
    partes.extend("@" + extra for extra in extras)
    for camada in ("chapeu", "arma"):
        chave = visual.get(camada)
        if chave and chave in todas_as_skins():
            partes.append("@" + skin(chave).acessorio)
    return "+".join(partes)
