"""Encontros: o que o grupo pode escolher depois de cada descanso.

    Encontro
    ├── EncontroCombate      combate, horda, elite, nomeado, mini-chefe ou chefe (com estrelas)
    ├── EncontroEvento       texto com escolhas (eventos.json)
    ├── EncontroTreinador    ensina a especialização da subclasse de um herói
    ├── EncontroLoja         mercador
    │   └── EncontroAlquimista
    ├── EncontroAltar        revive um herói com vida cheia (caro)
    │   └── EncontroNecromante   revive com metade da vida (barato)
    ├── EncontroDescanso     cura maior
    ├── EncontroEntrada      passagem para uma região opcional (selada se a fase ainda não existe)
    └── EncontroPortao       no fim de um ato: a fase do próximo ato (selado se a fase ainda não existe)

GeradorDeEncontros sorteia 3 opções diferentes para cada área. Uma passagem pode vir pelas mãos de um
guia (guias.py): enquanto o segredo não está completo, a carta é o evento do guia.
"""

from roguelike.dados import carregar, regras
from roguelike.inimigos import ficha
from roguelike.regioes import regiao as buscar_regiao, tipos_de_encontro, progressao, mesma_etapa, chefes_secretos

TIPOS_DE_COMBATE = ("combate", "horda", "elite", "nomeado", "mini_chefe", "chefe", "fuga", "secreto")


def nome_da_familia(familia):
    return carregar("regioes")["familias"].get(familia, familia)


def descrever_inimigos(chaves):
    """Ex.: "Aranha Gigante x2, Vespa Sangrenta"."""
    contagem = {}
    for chave in chaves:
        contagem[chave] = contagem.get(chave, 0) + 1
    partes = []
    for chave, quantidade in contagem.items():
        nome = ficha(chave)["nome"]
        partes.append(f"{nome} x{quantidade}" if quantidade > 1 else nome)
    return ", ".join(partes)


# ============================================================
# TIPOS DE ENCONTRO
# ============================================================

class Encontro:
    tipo = "encontro"

    def __init__(self, nome, descricao="", estrelas=0):
        self.nome = nome
        self.descricao = descricao
        self.estrelas = estrelas

    def icone(self):
        return tipos_de_encontro().get(self.tipo, {}).get("icone", "interrogacao")

    def nome_do_tipo(self):
        return tipos_de_encontro().get(self.tipo, {}).get("nome", self.tipo)

    def eh_combate(self):
        return False

    def para_dict(self):
        # "_encontro" guarda qual classe Python recriar (não pode ser "classe": o treinador já usa esse nome)
        return {**vars(self), "_encontro": type(self).__name__}

    def __repr__(self):
        return f"{type(self).__name__}({self.nome!r})"


class EncontroCombate(Encontro):
    def __init__(self, nome, descricao, estrelas, inimigos, categoria="combate"):
        super().__init__(nome, descricao, estrelas)
        self.inimigos = list(inimigos)
        self.tipo = categoria              # combate, horda, elite, nomeado, mini_chefe ou chefe

    def eh_combate(self):
        return True

    def nome_do_tipo(self):
        if getattr(self, "dificil", False):            # a 2ª carta do chefe (regioes.json "modo_dificil")
            return "Chefe · Modo Difícil"
        return super().nome_do_tipo()

    def texto_recompensa(self):
        extra = getattr(self, "recompensa_extra", None) or {}
        if extra.get("texto"):
            return extra["texto"]
        regra = regras()["estrelas"]
        extra = int(regra["ouro_por_estrela"] * (self.estrelas - 1) * 100)
        return f"+{extra}% de ouro e mais loot" if extra else "recompensa normal"


class EncontroEvento(Encontro):
    tipo = "evento"

    def __init__(self, chave_evento):
        from roguelike.eventos_run import evento
        dados = evento(chave_evento)
        super().__init__(dados.nome, "Um acontecimento estranho no caminho...")
        self.evento = chave_evento


class EncontroTreinador(Encontro):
    tipo = "treinador"

    def __init__(self, classe, subclasse):
        from roguelike.classes import classe as buscar_classe
        sub = buscar_classe(classe).subclasses[subclasse]
        esp = next(iter(sub.especializacoes.values()))
        super().__init__(f"Mestre {esp.nome}",
                         f"Transforma um {sub.nome} em {esp.nome} (a partir do nível {esp.nivel_minimo}). {esp.descricao}")
        self.classe = classe
        self.subclasse = subclasse

    def especializacao_de(self, heroi):
        return next(iter(heroi.subclasse.especializacoes.values()))

    def herois_que_podem(self, grupo):
        return [h for h in grupo.vivos() if h.subclasse is not None and h.subclasse.chave == self.subclasse
                and h.pode_especializar(self.especializacao_de(h))]


class EncontroLoja(Encontro):
    tipo = "loja"

    def __init__(self):
        super().__init__("Mercador Errante", "Compre, venda e fabrique. Ele não faz perguntas.")

    def criar_loja(self, rng, tier, descobertas, da_regiao=()):
        from roguelike.loja import Loja
        return Loja(rng, tier, descobertas, da_regiao)


class EncontroAlquimista(EncontroLoja):
    tipo = "alquimista"

    def __init__(self):
        Encontro.__init__(self, "Alquimista", "Poções, comida e bombas por bom preço.")

    def criar_loja(self, rng, tier, descobertas, da_regiao=()):
        from roguelike.loja import Alquimista
        return Alquimista(rng, tier, descobertas, da_regiao)


class EncontroAltar(Encontro):
    tipo = "altar"
    CHAVE_PRECO, CHAVE_VIDA = "altar_preco", "altar_vida"

    def __init__(self):
        regra = regras()["reviver"]
        super().__init__("Altar da Ressurreição",
                         f"Revive um herói caído com vida cheia por {regra[self.CHAVE_PRECO]} de ouro.")

    def preco(self):
        return regras()["reviver"][self.CHAVE_PRECO]

    def fracao(self):
        return regras()["reviver"][self.CHAVE_VIDA]


class EncontroNecromante(EncontroAltar):
    tipo = "necromante"
    CHAVE_PRECO, CHAVE_VIDA = "necromante_preco", "necromante_vida"

    def __init__(self):
        regra = regras()["reviver"]
        Encontro.__init__(self, "Necromante",
                          f"Arranca um herói da morte com metade da vida por {regra[self.CHAVE_PRECO]} de ouro.")


class EncontroDescanso(Encontro):
    tipo = "descanso"

    def __init__(self):
        super().__init__("Descanso Maior", "Uma fogueira segura. Cura mais quando o grupo não tem curandeiro.")

    def fracao(self, grupo):
        regra = regras()["descanso"]
        return regra["descanso_maior"] if grupo.tem_curandeiro() else regra["descanso_maior_sem_curandeiro"]


class EncontroEntrada(Encontro):
    tipo = "entrada"

    def __init__(self, destino):
        alvo = buscar_regiao(destino)
        super().__init__(f"Passagem: {alvo.nome}", alvo.descricao + " (região opcional)")
        self.destino = destino
        self.bloqueado = not alvo.disponivel           # fase secreta ainda sem conteúdo: passagem selada
        if self.bloqueado:
            self.descricao = alvo.selado or "Selada. Esta passagem ainda está sendo preparada."


class EncontroPortao(Encontro):
    tipo = "portao"

    def __init__(self, destino, aberto=True):
        alvo = buscar_regiao(destino)
        ato = progressao().atos[alvo.ato] if alvo.ato is not None else None
        descricao = alvo.descricao if aberto else "Selado. Esta fase ainda está sendo preparada."
        super().__init__(alvo.nome, descricao)
        self.destino = destino
        self.bloqueado = not aberto
        self.ato = ato.nome if ato else ""


CLASSES_DE_ENCONTRO = {c.__name__: c for c in (EncontroCombate, EncontroEvento, EncontroTreinador, EncontroLoja,
                                               EncontroAlquimista, EncontroAltar, EncontroNecromante,
                                               EncontroDescanso, EncontroEntrada, EncontroPortao)}


def encontro_de_dict(dados):
    dados = dict(dados)
    classe = CLASSES_DE_ENCONTRO[dados.pop("_encontro")]
    encontro = classe.__new__(classe)
    encontro.__dict__.update(dados)
    return encontro


# ============================================================
# MONTAGEM DOS COMBATES
# ============================================================

class MontadorDeCombate:
    """Escolhe os inimigos de cada tipo de combate de uma região."""

    MAXIMO = 6

    def __init__(self, regiao, area, rng, tamanho_do_grupo=3, noite=False, total=None):
        self.regiao = regiao
        self.area = area
        self.total = total                   # tamanho da fase nesta run (as zonas dependem dele)
        self.rng = rng
        self.noite = noite                   # à noite entram os inimigos noturnos da fase
        # Grupos pequenos enfrentam menos inimigos de uma vez (no máximo o grupo + 2)
        self.limite = min(self.MAXIMO, tamanho_do_grupo + 2)

    def comuns(self, quantidade):
        """Inimigos comuns sorteados; quem anda em "matilha" ([mín, máx]) chega com companheiros."""
        inimigos = []
        while len(inimigos) < quantidade:
            chave = self.regiao.sortear_inimigo(self.rng, self.noite, self.area, self.total)
            matilha = ficha(chave).get("matilha")
            juntos = self.rng.randint(*matilha) if matilha else 1
            inimigos += [chave] * min(juntos, max(1, self.limite - len(inimigos)))
        return inimigos[:max(quantidade, min(len(inimigos), self.limite))]

    def combate(self, estrelas=None):
        extra = self.area // 4
        if estrelas is None:
            estrelas = self.rng.choice([1, 2])
        quantidade = min(self.limite, (self.rng.randint(1, 2) if estrelas == 1 else self.rng.randint(2, 3)) + extra)
        inimigos = self.comuns(quantidade)
        nome = self.rng.choice(["Emboscada", "Patrulha", "Encontro na Névoa", "Criaturas Famintas", "Caçadores"])
        return EncontroCombate(nome, descrever_inimigos(inimigos), estrelas, inimigos, "combate")

    def horda(self, estrelas=None):
        # Famílias com pelo menos 2 tipos diferentes nesta região
        candidatos = self.regiao.inimigos_possiveis(self.noite, self.area, self.total) + self.regiao.elites
        familias = {}
        for chave in candidatos:
            familias.setdefault(ficha(chave)["familia"], []).append(chave)
        familias = {f: c for f, c in familias.items() if len(c) >= 2}
        if not familias:
            return self.combate(2)
        familia = self.rng.choice(sorted(familias))
        membros = familias[familia]
        lideres = [c for c in membros if c in self.regiao.elites or ficha(c)["papel"] == "chefe_de_horda"]
        tropa = [c for c in membros if c not in lideres] or membros
        if estrelas is None:
            estrelas = self.rng.choice([3, 4]) if self.area >= 4 else 3
        quantidade = min(self.limite, 3 + (estrelas - 3) + self.rng.randint(0, 1) + self.area // 5)
        inimigos = []
        if estrelas >= 4 and lideres:
            inimigos.append(self.rng.choice(lideres))
        # Pequenos aparecem mais, grandes menos (usa o "tamanho" do catálogo)
        pesos = {"pequeno": 3, "medio": 2, "grande": 1, "enorme": 0.5}
        while len(inimigos) < quantidade:
            inimigos.append(self.rng.choices(tropa, weights=[pesos[ficha(c)["tamanho"]] for c in tropa])[0])
        return EncontroCombate(f"Horda: {nome_da_familia(familia)}", descrever_inimigos(inimigos), estrelas, inimigos, "horda")

    def elite(self, estrelas=None):
        if estrelas is None:
            estrelas = self.rng.choice([3, 4]) if self.area >= 4 else 3
        inimigos = [self.rng.choice(self.regiao.elites)] + self.comuns(min(estrelas - 2, self.limite - 1))
        return EncontroCombate(f"Elite: {ficha(inimigos[0])['nome']}", descrever_inimigos(inimigos), estrelas, inimigos, "elite")

    def nomeado(self, estrelas=4):
        principal = self.rng.choice(self.regiao.nomeados)
        inimigos = [principal] + self.comuns(min(self.rng.randint(1, 2), self.limite - 2))
        return EncontroCombate(ficha(principal)["nome"], descrever_inimigos(inimigos), estrelas, inimigos, "nomeado")

    def mini_chefe(self, estrelas=5, excluir=()):
        """Um mini-chefe (os da zona, nas fases com zonas), com a "escolta" da ficha, se tiver."""
        todos = self.regiao.mini_chefes_da_area(self.area, self.total)
        possiveis = [c for c in todos if c not in excluir] or todos
        principal = self.rng.choice(possiveis)
        inimigos = [principal] + list(ficha(principal).get("escolta", []))
        return EncontroCombate(ficha(principal)["nome"], "Um inimigo terrível guarda o caminho.", estrelas, inimigos, "mini_chefe")

    def chefe(self):
        """O chefe da fase, com a "escolta" da ficha (ex.: o Queijo Real ao lado do Rei dos Ratos)."""
        chefe = self.regiao.chefe
        return EncontroCombate(ficha(chefe)["nome"], f"O senhor de {self.regiao.nome}.", 5,
                               [chefe] + list(ficha(chefe).get("escolta", [])), "chefe")

    def modo_dificil(self):
        """O chefe no modo difícil (regioes.json "modo_dificil", ex.: A Corte Completa): os inimigos, as passivas a
        mais de cada um só neste encontro, a recompensa extra e o feito que fica guardado no progresso."""
        dados = self.regiao.modo_dificil
        encontro = EncontroCombate(dados["nome"], dados.get("descricao", ""), dados.get("estrelas", 5),
                                   list(dados["inimigos"]), "chefe")
        encontro.dificil = True
        encontro.passivas_extras = {chave: list(lista) for chave, lista in dados.get("passivas_extras", {}).items()}
        encontro.recompensa_extra = dict(dados.get("recompensa", {}))
        encontro.feito = dados.get("feito")
        return encontro

    def montar(self, categoria, estrelas=None):
        if categoria == "horda":
            return self.horda(estrelas)
        if categoria == "elite" and self.regiao.elites:
            return self.elite(estrelas)
        if categoria == "nomeado" and self.regiao.nomeados:
            return self.nomeado(estrelas or 4)
        if categoria == "mini_chefe" and self.regiao.mini_chefes_da_area(self.area, self.total):
            return self.mini_chefe(estrelas or 5)
        if categoria == "chefe":
            return self.chefe()
        return self.combate(min(estrelas or 2, 2))


def combate_de_evento(run, rng, dados):
    """Combate causado por um evento (lista fixa de inimigos ou uma categoria)."""
    estrelas = dados.get("estrelas", 2)
    if "inimigos" in dados:
        return EncontroCombate("Emboscada!", descrever_inimigos(dados["inimigos"]), estrelas, dados["inimigos"], "combate")
    montador = MontadorDeCombate(run.regiao, run.area, rng, len(run.grupo.vivos()), run.eh_noite(), run.areas_da_regiao())
    return montador.montar(dados.get("categoria", "combate"), estrelas)


# ============================================================
# GERADOR DAS 3 OPÇÕES
# ============================================================

class GeradorDeEncontros:
    QUANTIDADE = 3

    def __init__(self, run, rng):
        self.run = run
        self.rng = rng
        self.regiao = run.regiao
        self.area = run.area
        self.total = run.areas_da_regiao()
        self.montador = MontadorDeCombate(self.regiao, self.area, rng, len(run.grupo.vivos()), run.eh_noite(), self.total)

    def disponivel(self, tipo):
        dados = tipos_de_encontro()[tipo]
        if dados.get("peso", 0) <= 0 or self.area < dados.get("area_minima", 1):
            return False
        grupo = self.run.grupo
        if tipo == "elite":
            return bool(self.regiao.elites)
        if tipo == "nomeado":
            return bool(self.regiao.nomeados)
        if tipo == "mini_chefe":
            return any(c not in self.run.mini_chefes_derrotados for c in self.regiao.mini_chefes_da_area(self.area, self.total))
        if tipo in ("altar", "necromante"):
            return bool(grupo.caidos())
        if tipo == "treinador":
            return bool(self.treinos_possiveis())
        if tipo == "evento":
            return bool(self.eventos_possiveis())
        return True

    def treinos_possiveis(self):
        """(classe, subclasse) com treinador nesta região para heróis prontos para se especializar.

        Cada especialização tem a sua região; a Catedral (caminho obrigatório) ensina todas.
        """
        possiveis = []
        for heroi in self.run.grupo.vivos():
            if heroi.subclasse is None or heroi.especializacao is not None:
                continue
            for esp in heroi.subclasse.especializacoes.values():
                ensina = mesma_etapa(esp.regiao, self.regiao.chave) or self.regiao.final       # o fim ensina todas
                if heroi.pode_especializar(esp) and ensina:
                    par = (heroi.classe.chave, heroi.subclasse.chave)
                    if par not in possiveis:
                        possiveis.append(par)
        return possiveis

    def eventos_possiveis(self):
        from roguelike.eventos_run import todos_os_eventos
        zona = self.regiao.zona(self.area, self.total)
        return [c for c, e in todos_os_eventos().items()
                if e.aparece_em(self.regiao.chave) and e.aparece_na_zona(zona) and c not in self.run.eventos_vistos]

    def criar(self, tipo):
        if tipo in TIPOS_DE_COMBATE:
            excluir = self.run.mini_chefes_derrotados
            if tipo == "mini_chefe":
                return self.montador.mini_chefe(excluir=excluir)
            return self.montador.montar(tipo)
        if tipo == "evento":
            return EncontroEvento(self.rng.choice(self.eventos_possiveis()))
        if tipo == "treinador":
            classe, subclasse = self.rng.choice(self.treinos_possiveis())
            return EncontroTreinador(classe, subclasse)
        return {"loja": EncontroLoja, "alquimista": EncontroAlquimista, "altar": EncontroAltar,
                "necromante": EncontroNecromante, "descanso": EncontroDescanso}[tipo]()

    def portoes(self):
        return [EncontroPortao(destino, aberto) for destino, aberto in self.run.portoes]

    def passagem(self, destino, regra):
        """A carta da passagem: direta (Circo) ou pelas mãos de um guia (Rato Branco: evento até o segredo
        estar completo). None = o guia não aparece aqui nesta run."""
        if not regra.get("guia"):
            return EncontroEntrada(destino)
        from roguelike.guias import guia
        return guia(regra["guia"]).encontro(self.run, destino)

    def modo_dificil(self):
        """A carta do modo difícil, se a fase tem um e o chefe já foi vencido (a conquista "requer" do progresso)."""
        dados = self.regiao.modo_dificil
        if not dados or dados.get("requer") not in getattr(self.run, "conquistas_permanentes", set()):
            return []
        return [self.montador.modo_dificil()]

    def secretos(self, no_chefe=False):
        """Chefes secretos que aparecem aqui (sorteio próprio: não muda o resto das opções).

        no_chefe=True: os que surgem ao lado do chefe de uma fase final (ex.: O Primeiro Herói).
        """
        achados = []
        conquistas = getattr(self.run, "conquistas_permanentes", set())
        for chave, dados in chefes_secretos().items():
            if chave in self.run.estatisticas["chefes"] or bool(dados.get("so_no_chefe_final")) != no_chefe:
                continue
            if no_chefe and not self.regiao.final:
                continue
            if not no_chefe and (self.regiao.ato not in dados.get("atos", []) or self.area < dados.get("area_minima", 1)):
                continue
            if not set(dados.get("requer", [])) <= set(conquistas):
                continue
            if self.run.rng(f"secreto|{chave}|{self.regiao.chave}|{self.area}").random() < dados.get("chance", 0):
                achados.append(EncontroCombate(dados["nome"], dados["descricao"], 5, [chave], "secreto"))
        return achados

    def gerar(self):
        if self.run.portoes:
            return self.portoes()
        if self.regiao.area_do_chefe(self.area, self.total):
            return [self.montador.chefe()] + self.modo_dificil() + self.secretos(no_chefe=True)

        tipos = [t for t in tipos_de_encontro() if self.disponivel(t)]
        pesos = [tipos_de_encontro()[t]["peso"] for t in tipos]
        escolhidos = []
        while tipos and len(escolhidos) < self.QUANTIDADE:
            tipo = self.rng.choices(tipos, weights=pesos)[0]
            indice = tipos.index(tipo)
            tipos.pop(indice)
            pesos.pop(indice)
            escolhidos.append(tipo)

        # Sempre pelo menos uma luta (para não faltar experiência)
        if not any(t in TIPOS_DE_COMBATE for t in escolhidos):
            escolhidos[-1] = "combate"
        # Antes do chefe, sempre uma chance de se preparar
        if self.area == self.total - 1 and not any(t in ("descanso", "loja", "alquimista") for t in escolhidos):
            escolhidos[0] = self.rng.choice(["descanso", "loja", "alquimista"])

        opcoes = [self.criar(t) for t in escolhidos]

        # Passagem para uma região opcional (substitui uma opção que não é luta). As fases dos atos
        # só se alcançam pelos portões; as áreas do JSON contam no tamanho original da região.
        area_original = self.regiao.area_original(self.area, self.total)
        for destino, regra in self.regiao.entradas.items():
            if buscar_regiao(destino).ato is not None:
                continue
            if (area_original in regra["areas"] and destino not in self.run.regioes_visitadas
                    and self.rng.random() < regra["chance"]):
                passagem = self.passagem(destino, regra)
                if passagem is None:
                    continue
                indice = next((i for i, o in enumerate(opcoes) if not o.eh_combate()), len(opcoes) - 1)
                opcoes[indice] = passagem
                break
        # Chefe secreto: toma o lugar da última opção que não é passagem
        for secreto in self.secretos():
            indice = max((i for i, o in enumerate(opcoes) if o.tipo != "entrada"), default=len(opcoes) - 1)
            opcoes[indice] = secreto
            break
        return opcoes
