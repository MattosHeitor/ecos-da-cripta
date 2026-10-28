"""Golpes: ataques, magias, curas e canções que os lutadores usam no combate.

- Golpe: os dados de um golpe (habilidades.json) + a evolução dele (evolucoes.json);
- GerenciadorDeGolpes: os golpes de UM herói — os espaços equipados (regras: 6), o grimório
  (golpes guardados) e os golpes novos esperando o jogador decidir onde ficam.

Tipos de alvo:
    "inimigo"       um oponente escolhido
    "inimigos"      todos os oponentes
    "aleatorio"     cada golpe acerta um oponente sorteado
    "aliado"        um aliado escolhido (pode ser ele mesmo)
    "aliados"       todos os aliados
    "si"            o próprio usuário
    "aliado_caido"  um aliado derrotado (para reviver)
"""

from roguelike.dados import carregar, sem_comentarios, regras
from roguelike.efeitos_habilidade import criar_efeito
from roguelike.elementos import PADRAO as ELEMENTO_PADRAO

ALVOS_OFENSIVOS = ("inimigo", "inimigos", "aleatorio")
ALVOS_VALIDOS = ALVOS_OFENSIVOS + ("aliado", "aliados", "si", "aliado_caido")
NOMES_DE_ALVO = {"inimigo": "1 inimigo", "inimigos": "todos os inimigos", "aleatorio": "inimigos sorteados",
                 "aliado": "1 aliado", "aliados": "todos os aliados", "si": "em si", "aliado_caido": "1 aliado caído"}
NOMES_DE_TIPO = {"fisico": "Físico", "magico": "Mágico", "suporte": "Suporte"}
ATRIBUTOS_MAGICOS = {"inteligencia", "fe", "carisma"}


def descricao_curta(resumo, custo, alvo):
    """Junta as partes numa linha: "8-12 de dano · 2 energia · 1 inimigo"."""
    return " · ".join(p for p in (resumo, custo, NOMES_DE_ALVO.get(alvo, alvo)) if p)


class Golpe:
    def __init__(self, chave, dados, evolucao=None):
        self.chave = chave
        self.nome = dados["nome"]
        self.descricao = dados.get("descricao", "")
        self.custo = dados.get("custo", 0)               # energia
        self.custo_vida = dados.get("custo_vida", 0)
        self.alvo = dados.get("alvo", "inimigo")
        self.nivel_maximo = dados.get("nivel_maximo", regras()["nivel"]["maximo_habilidade_classe"])
        self.icone = dados.get("icone", "")
        self.elemento = dados.get("elemento", ELEMENTO_PADRAO)
        self.recarga = dados.get("recarga", 0)          # turnos de espera depois de usar (golpes raciais)
        self.som = dados.get("som")                      # efeito sonoro próprio (senão a tela escolhe pelo tipo)
        self.animacao = dados.get("animacao")            # linha própria do sprite de quem usa (ex.: "decreto")
        # Golpe raro: liberado por uma conquista (conquistas.json "golpe"); na run, as classes de
        # "raro.classes" o aprendem no nível "raro.nivel"
        raro = dados.get("raro") or {}
        self.raro = bool(raro)
        self.classes_do_raro = list(raro.get("classes", []))
        self.nivel_do_raro = raro.get("nivel", 1)
        # O elemento do golpe vale para os efeitos de dano que não dizem outro
        self.efeitos = [criar_efeito({"elemento": self.elemento, **e} if e.get("tipo") == "dano" else e)
                        for e in dados.get("efeitos", [])]
        self._tipo = dados.get("tipo")
        evolucao = evolucao or {}
        self.evolucao_para = evolucao.get("para")        # chave do golpe aprimorado (ou None)
        self.requisito_evolucao = evolucao.get("requisito", {})
        if self.alvo not in ALVOS_VALIDOS:
            raise ValueError(f"Alvo inválido em {chave}: {self.alvo}")

    # ---------------- consultas ----------------
    def ofensiva(self):
        return self.alvo in ALVOS_OFENSIVOS

    def escolhe_alvo(self):
        """True se o jogador precisa escolher um alvo."""
        return self.alvo in ("inimigo", "aliado", "aliado_caido")

    def pode_usar(self, usuario):
        silenciado = self.custo > 0 and any(s.silencia() for s in usuario.status.values())
        return (usuario.energia >= self.custo and usuario.vida > self.custo_vida
                and usuario.recarga_de(self.chave) <= 0 and not silenciado)

    def tem_efeito(self, tipo):
        return any(e.dados["tipo"] == tipo for e in self.efeitos)

    @property
    def tipo(self):
        """"fisico", "magico" ou "suporte" (o JSON pode dizer; senão, vem dos efeitos)."""
        if self._tipo:
            return self._tipo
        for efeito in self.efeitos:
            if efeito.dados["tipo"] == "dano":
                escala = set(efeito.dados.get("escala", {}))
                return "magico" if escala & ATRIBUTOS_MAGICOS else "fisico"
        return "suporte"

    def dano(self, nivel=1):
        """(mínimo, máximo, golpes) do primeiro efeito de dano, ou None."""
        for efeito in self.efeitos:
            if efeito.dados["tipo"] == "dano":
                minimo, maximo = efeito.no_nivel("dano", nivel)
                return minimo, maximo, efeito.no_nivel("golpes", nivel, 1)
        return None

    def texto_custo(self):
        partes = []
        if self.custo:
            partes.append(f"{self.custo} energia")
        if self.custo_vida:
            partes.append(f"{self.custo_vida} vida")
        texto = " + ".join(partes) or "grátis"
        if self.recarga:
            texto += f", recarga {self.recarga}"
        return texto

    def resumo(self, nivel=1):
        """Descrição gerada a partir dos efeitos, ex.: "2-4 de dano; Veneno 3 por 3 turnos"."""
        partes = [e.resumo(nivel) for e in self.efeitos]
        return "; ".join(p for p in partes if p)

    def descricao_curta(self, nivel=1):
        """Uma linha com efeito, custo e alvo (para a tela de combate)."""
        return descricao_curta(self.resumo(nivel), self.texto_custo(), self.alvo)

    # ---------------- evolução ----------------
    def requisito_cumprido(self, heroi, marcos=()):
        """O herói já pode aprimorar este golpe? marcos = conquistas da run ("chefe:aranha_mae"...)."""
        requisito = self.requisito_evolucao
        if not self.evolucao_para or not requisito:
            return False
        if heroi.nivel < requisito.get("nivel", 0):
            return False
        if "subclasse" in requisito and getattr(heroi.subclasse, "chave", None) != requisito["subclasse"]:
            return False
        if "especializacao" in requisito and \
                getattr(getattr(heroi, "especializacao", None), "chave", None) != requisito["especializacao"]:
            return False
        if "marco" in requisito and requisito["marco"] not in marcos:
            return False
        return True

    def texto_do_requisito(self):
        """Ex.: "nível 8", "virar Piromante", "vencer Mãe Aranha"."""
        requisito = self.requisito_evolucao
        partes = []
        if "nivel" in requisito:
            partes.append(f"nível {requisito['nivel']}")
        for chave in ("subclasse", "especializacao"):
            if chave in requisito:
                partes.append(f"virar {nome_da_especialidade(requisito[chave])}")
        if "marco" in requisito:
            from roguelike.progresso import descrever_conquista
            partes.append(descrever_conquista(requisito["marco"]).lower())
        return " e ".join(partes)

    def __repr__(self):
        return f"Golpe({self.chave!r})"


def nome_da_especialidade(chave):
    """Nome legível de uma subclasse ou especialização (para os textos de evolução)."""
    for classe in sem_comentarios(carregar("classes")).values():
        for sub_chave, sub in classe.get("subclasses", {}).items():
            if sub_chave == chave:
                return sub["nome"]
            for esp_chave, esp in sub.get("especializacoes", {}).items():
                if esp_chave == chave:
                    return esp["nome"]
    return chave.replace("_", " ").title()

_golpes = {}


def golpe(chave):
    """Devolve o Golpe com essa chave (criado uma vez só)."""
    if chave not in _golpes:
        todos = sem_comentarios(carregar("habilidades"))
        if chave not in todos:
            raise KeyError(f"Golpe desconhecido: {chave}")
        _golpes[chave] = Golpe(chave, todos[chave], evolucoes().get(chave))
    return _golpes[chave]


def todas_as_chaves():
    return list(sem_comentarios(carregar("habilidades")))


def evolucoes():
    """{golpe: {"para": golpe_aprimorado, "requisito": {...}}} (evolucoes.json)."""
    return sem_comentarios(carregar("evolucoes"))


# ============================================================
# OS GOLPES DE UM HERÓI
# ============================================================

class ResultadoAprendizado:
    """O que aconteceu ao tentar aprender um golpe.

    situacao: "equipado" (havia espaço), "escolher" (espaços cheios: o jogador decide),
    "grimorio" (foi direto para o grimório) ou "ja_sabe".
    """

    def __init__(self, situacao, chave):
        self.situacao = situacao
        self.chave = chave

    def __repr__(self):
        return f"ResultadoAprendizado({self.situacao!r}, {self.chave!r})"


class GerenciadorDeGolpes:
    """Espaços de golpes (regras.json golpes.espacos) + grimório. Nada se perde: o golpe tirado de um espaço vai para o grimório,
    e fora do combate dá para trocar à vontade.

    Os níveis de TODOS os golpes aprendidos ficam em dono.niveis_habilidade.
    """

    def __init__(self, dono):
        self.dono = dono
        self.equipados = []              # na ordem do menu de combate
        self.grimorio = []
        self.pendentes = []              # golpes novos esperando decisão (espaços cheios)
        self.avisos = []                 # (título, texto) para a tela mostrar ("Golpe aprimorado!")

    @property
    def niveis(self):
        return self.dono.niveis_habilidade

    @staticmethod
    def espacos_base():
        return regras()["golpes"]["espacos"]

    def espacos(self):
        """Espaços de regras.json + os de itens ("espacos_de_golpe", ex.: Grimório Sem Nome = 7º golpe)."""
        try:
            extra = int(self.dono.stat("espacos_de_golpe"))
        except AttributeError:                       # dono ainda sendo montado
            extra = 0
        return self.espacos_base() + max(0, extra)

    def ajustar_espacos(self):
        """Perdeu um espaço (tirou o item): os golpes que sobram voltam ao grimório."""
        while len(self.equipados) > max(1, self.espacos()):
            self.grimorio.append(self.equipados.pop())

    def sabe(self, chave):
        return chave in self.niveis

    def aprender(self, chave, nivel=1, perguntar=True):
        """Aprende um golpe. Com os espaços cheios, ele espera a decisão (ou vai ao grimório)."""
        golpe(chave)                      # confere se existe
        if self.sabe(chave):
            return ResultadoAprendizado("ja_sabe", chave)
        self.niveis[chave] = nivel
        if len(self.equipados) < self.espacos():
            self.equipados.append(chave)
            return ResultadoAprendizado("equipado", chave)
        if perguntar:
            self.pendentes.append(chave)
            return ResultadoAprendizado("escolher", chave)
        self.grimorio.append(chave)
        return ResultadoAprendizado("grimorio", chave)

    def decidir(self, novo, esquecido=None):
        """Golpe pendente: troca pelo 'esquecido' (que vai ao grimório) ou, sem esquecido, guarda o novo."""
        if novo not in self.pendentes or (esquecido is not None and esquecido not in self.equipados):
            return False
        self.pendentes.remove(novo)
        if esquecido is None:
            self.grimorio.append(novo)
        else:
            self.equipados[self.equipados.index(esquecido)] = novo
            self.grimorio.append(esquecido)
        return True

    def trocar(self, do_grimorio, equipado=None):
        """Fora do combate: equipa um golpe do grimório (no lugar de 'equipado', se os espaços estiverem cheios)."""
        if do_grimorio not in self.grimorio:
            return False
        if equipado is None:
            if len(self.equipados) >= self.espacos():
                return False
            self.grimorio.remove(do_grimorio)
            self.equipados.append(do_grimorio)
            return True
        if equipado not in self.equipados:
            return False
        self.grimorio[self.grimorio.index(do_grimorio)] = equipado
        self.equipados[self.equipados.index(equipado)] = do_grimorio
        return True

    def guardar(self, chave):
        """Tira um golpe dos espaços (sempre fica pelo menos 1 equipado)."""
        if chave not in self.equipados or len(self.equipados) <= 1:
            return False
        self.equipados.remove(chave)
        self.grimorio.append(chave)
        return True

    # ---------------- evolução ----------------
    def verificar_evolucoes(self, marcos=()):
        """Aprimora os golpes cujo requisito foi cumprido. Devolve [(antigo, novo)]."""
        feitas = []
        for chave in list(self.niveis):
            atual = golpe(chave)
            novo = atual.evolucao_para
            if novo and not self.sabe(novo) and atual.requisito_cumprido(self.dono, marcos):
                self.substituir(chave, novo)
                feitas.append((chave, novo))
                self.avisos.append(("Golpe aprimorado!", f"{self.dono.nome}: {atual.nome} virou {golpe(novo).nome}"))
        return feitas

    def substituir(self, antigo, novo):
        """Troca um golpe pela versão aprimorada (no mesmo lugar e com o mesmo nível)."""
        self.niveis[novo] = self.niveis.pop(antigo)
        for lista in (self.equipados, self.grimorio, self.pendentes):
            if antigo in lista:
                lista[lista.index(antigo)] = novo

    def pegar_avisos(self):
        avisos, self.avisos = self.avisos, []
        return avisos

    # ---------------- salvar ----------------
    def para_dict(self):
        return {"equipados": list(self.equipados), "grimorio": list(self.grimorio), "pendentes": list(self.pendentes)}

    def carregar_dict(self, dados):
        """dados=None (save antigo): os primeiros golpes ficam equipados e o resto vai ao grimório."""
        if dados is None:
            chaves = list(self.niveis)
            dados = {"equipados": chaves[:self.espacos()], "grimorio": chaves[self.espacos():], "pendentes": []}
        conhecidos = set(self.niveis)
        self.equipados = [c for c in dados.get("equipados", []) if c in conhecidos]
        self.grimorio = [c for c in dados.get("grimorio", []) if c in conhecidos]
        self.pendentes = [c for c in dados.get("pendentes", []) if c in conhecidos]
        soltos = conhecidos - set(self.equipados) - set(self.grimorio) - set(self.pendentes)
        self.grimorio.extend(sorted(soltos))
