"""Classes de herói (classes.json) e a criação de heróis.

Cada classe tem atributos iniciais, vida base, faixa de iniciativa, golpes iniciais e 3 ou 4
subclasses (escolhidas na Capitã, liberadas pelo prestígio). Cada subclasse tem uma
especialização, aprendida com um treinador durante a run. Ver especialidades.py.

Classes secretas têm "requer" (uma conquista do progresso, ex.: "chefe:rainha_dos_ratos"): até lá não aparecem
em lugar nenhum (classes_liberadas). Quando liberadas, o acampamento anuncia o herói novo ("anuncio").

Para criar um herói pronto: criar_heroi("mago", "Wren", subclasse="piromante").
"""

from roguelike.atributos import Atributos
from roguelike.dados import carregar, sem_comentarios
from roguelike.especialidades import Especialidade, Subclasse
from roguelike.golpes import todas_as_chaves
from roguelike.lutador import Heroi


class ClasseDeHeroi(Especialidade):
    tipo = "classe"

    def __init__(self, chave, dados):
        super().__init__(chave, dados)
        self.papel = dados.get("papel", "")
        self.atributos_principais = list(dados.get("atributos_principais", []))
        self.atributos_iniciais = Atributos(dados["atributos"])
        self.vida_base = dados["vida_base"]
        self.iniciativa = tuple(dados.get("iniciativa", (3, 8)))
        self.aparencias = dict(dados["aparencias"])         # aparência -> sprite
        self.aparencia_padrao = dados.get("aparencia_padrao", next(iter(self.aparencias)))
        self.habilidades = list(dados["habilidades"])
        self.habilidades_por_aparencia = dict(dados.get("habilidades_por_aparencia", {}))
        # golpes que qualquer herói da classe aprende ao chegar no nível: {"3": golpe, "6": golpe}
        self.golpes_por_nivel = {int(n): chave for n, chave in dados.get("golpes_por_nivel", {}).items()}
        self.subclasses = {chave_sub: Subclasse(chave_sub, self, dados_sub)
                           for chave_sub, dados_sub in sem_comentarios(dados.get("subclasses", {})).items()}
        self.requer = dados.get("requer")                   # conquista que libera a classe (None = desde o começo)
        self.anuncio = dados.get("anuncio", "")             # a frase da tela de herói novo
        self.nome_curto = dados.get("nome_curto", self.nome)   # nas caixas estreitas (Grimório, prestígio do grupo)

    def liberada(self, conquistas):
        return not self.requer or self.requer in conquistas

    def nome_que_cabe(self, fonte, largura):
        """O nome inteiro, se couber na largura com essa fonte; senão o nome curto."""
        return self.nome if fonte.size(self.nome)[0] <= largura else self.nome_curto

    def sprite_da_aparencia(self, aparencia):
        return self.aparencias.get(aparencia, self.aparencias[self.aparencia_padrao])

    def habilidades_iniciais(self, aparencia):
        return self.habilidades + self.habilidades_por_aparencia.get(aparencia, [])

    def golpes_no_nivel(self, nivel):
        chave = self.golpes_por_nivel.get(nivel)
        return [chave] if chave else []

    def subclasses_ate_o_prestigio(self, prestigio):
        """Subclasses liberadas com esse nível de prestígio da classe."""
        return [s for s in self.subclasses.values() if s.prestigio <= prestigio]

    def especializacao(self, chave):
        for sub in self.subclasses.values():
            if chave in sub.especializacoes:
                return sub.especializacoes[chave]
        raise KeyError(f"Especialização desconhecida: {chave}")


_classes = {}


def todas_as_classes():
    """Dicionário chave -> ClasseDeHeroi, na ordem do JSON."""
    if not _classes:
        for chave, dados in sem_comentarios(carregar("classes")).items():
            _classes[chave] = ClasseDeHeroi(chave, dados)
    return _classes


def classes_liberadas(conquistas):
    """As classes que o jogador já tem (as secretas só depois da conquista de "requer"), na ordem do JSON."""
    return {chave: c for chave, c in todas_as_classes().items() if c.liberada(conquistas)}


def classe(chave):
    try:
        return todas_as_classes()[chave]
    except KeyError:
        raise KeyError(f"Classe desconhecida: {chave}") from None


def criar_heroi(chave_classe, nome=None, aparencia=None, subclasse=None):
    """Herói novo. Com 'subclasse', já parte com ela (como na Capitã)."""
    classe_escolhida = classe(chave_classe)
    heroi = Heroi(classe_escolhida, nome or classe_escolhida.nome, aparencia)
    if subclasse is not None:
        heroi.escolher_subclasse(classe_escolhida.subclasses[subclasse], inicial=True)
    return heroi

# ============================================================
# SALVAR E CARREGAR
# ============================================================

def heroi_para_dict(heroi, com_mochila=True):
    """O herói em dados simples. com_mochila=False: sem o inventário (num grupo, a mochila é do jogador e vai no
    save dele; repetir em cada herói duplicaria os itens)."""
    dados = {
        "classe": heroi.classe.chave,
        "nome": heroi.nome,
        "aparencia": heroi.aparencia,
        "raca": heroi.raca,
        "subclasse_bloqueada": heroi.subclasse_bloqueada,
        "subclasse": heroi.subclasse.chave if heroi.subclasse else None,
        "especializacao": heroi.especializacao.chave if heroi.especializacao else None,
        "visual": dict(heroi.visual),
        "golpes_raros": list(heroi.golpes_raros),
        "nivel": heroi.nivel,
        "xp": heroi.xp,
        "pontos_atributo": heroi.pontos_atributo,
        "pontos_habilidade": heroi.pontos_habilidade,
        "atributos": heroi.atributos.para_dict(),
        "habilidades": dict(heroi.niveis_habilidade),
        "golpes": heroi.golpes.para_dict(),
        "equipamento": heroi.equipamentos.para_dict(),
        "travados": sorted(heroi.equipamentos.travados),
        "inventario": heroi.inventario.para_dict(),
        "passivas_extras": list(heroi.passivas_extras),
        "vida": heroi.vida,
        "peste": heroi.peste,
        "jogador": getattr(getattr(heroi, "jogador", None), "id", None),     # quem comanda (multiplayer)
    }
    if not com_mochila:
        del dados["inventario"]
    return dados


def heroi_de_dict(dados):
    from roguelike.inventario import Inventario
    from roguelike.itens import item

    heroi = criar_heroi(dados["classe"], dados["nome"], dados.get("aparencia"))
    heroi.nivel = dados["nivel"]
    heroi.xp = dados["xp"]
    heroi.pontos_atributo = dados["pontos_atributo"]
    heroi.pontos_habilidade = dados["pontos_habilidade"]
    heroi.atributos = Atributos(dados["atributos"])
    heroi.subclasse_bloqueada = dados.get("subclasse_bloqueada", False)
    heroi.golpes_raros = [c for c in dados.get("golpes_raros", []) if c in todas_as_chaves()]
    if dados.get("subclasse"):
        heroi.escolher_subclasse(heroi.classe.subclasses[dados["subclasse"]], inicial=True)
    if dados.get("especializacao"):
        heroi.escolher_especializacao(heroi.classe.especializacao(dados["especializacao"]), forcar=True)
    heroi.niveis_habilidade = dict(dados["habilidades"])
    heroi.golpes.carregar_dict(dados.get("golpes"))       # saves antigos: os primeiros equipados, o resto no grimório
    from roguelike.racas import PASSIVAS_ANTIGAS
    for passiva in dados.get("passivas_extras", []):
        if passiva not in PASSIVAS_ANTIGAS:           # saves da fase 2 guardavam a raça como passivas
            heroi.adicionar_passiva(passiva)
    heroi.definir_raca(dados.get("raca", "humano"))
    if "inventario" in dados:                         # (num save de run, a mochila vem com o jogador)
        heroi.inventario = Inventario.de_dict(dados["inventario"])
    from roguelike.itens import existe
    for espaco, chave in dados.get("equipamento", {}).items():
        if not chave or not existe(chave):
            continue
        objeto = item(chave)
        # saves antigos: "armadura", "amuleto1"/"amuleto2" viram o espaço da peça; o que não couber vai para a mochila
        destino = espaco if espaco in heroi.equipamentos.espacos else heroi.equipamentos.espaco_livre(objeto)
        livre = destino is not None and heroi.equipamentos.get(destino) is None
        if not (livre and heroi.equipar(objeto, destino)[0]) and objeto.tipo == "equipamento":
            heroi.inventario.itens[chave] = heroi.inventario.quantidade(chave) + 1
    heroi.equipamentos.travados = {e for e in dados.get("travados", []) if heroi.equipamentos.get(e) is not None}
    heroi.vestir(dados.get("visual", {}))
    heroi.vida = min(dados["vida"], heroi.vida_maxima)
    heroi.peste = dados.get("peste", 0)
    return heroi
