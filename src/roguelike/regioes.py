"""Regiões (fases) da campanha e a progressão por atos (regioes.json).

    Regiao          uma fase: inimigos com peso, inimigos da noite, chefe, cenário, paleta,
                    ciclo dia -> noite, drops e consumíveis da área
    Ato             um grupo de fases alternativas (a run passa por uma fase de cada ato)
    Progressao      a ordem dos atos, o tamanho sorteado das fases e os portões do fim de cada ato
"""

from roguelike.dados import carregar, sem_comentarios

LIMIAR_DA_NOITE = 0.7             # a partir desta hora (0 = dia, 1 = noite) os inimigos noturnos aparecem


class Regiao:
    """Uma fase. 'areas' é o tamanho original; numa run de atos o tamanho é sorteado (ver Progressao)."""

    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.descricao = dados.get("descricao", "")
        self.titulo = dados.get("titulo", self.descricao)   # frase da tela de entrada
        self.areas = dados["areas"]                 # a última área é a do chefe
        self.tier = dados["tier"]
        self.cenario = dados.get("cenario", chave)
        self.cenario_provisorio = dados.get("cenario_provisorio")
        self.paleta = dict(dados.get("paleta", {}))
        self.ciclo = dados.get("ciclo", False)      # céu aberto: a hora anda do dia à noite
        self.variantes = list(dados.get("variantes", [0]))
        self.sala_do_chefe = dados.get("sala_do_chefe")
        self.musica = dados.get("musica", chave)
        self.disponivel = dados.get("disponivel", True)
        self.selado = dados.get("selado", "")       # texto da passagem enquanto a fase não está pronta
        self.etapa = dados.get("etapa")             # etapa da fase 4 em que o conteúdo chega
        self.opcional = dados.get("opcional", False)
        self.retorna = dados.get("retorna", False)  # volta para a região de onde veio
        self.inimigos = list(dados["inimigos"])
        self.pesos = dict(dados.get("pesos", {}))
        self.inimigos_noturnos = list(dados.get("inimigos_noturnos", []))
        self.elites = list(dados.get("elites", []))
        self.nomeados = list(dados.get("nomeados", []))
        self.mini_chefes = list(dados.get("mini_chefes", []))
        self.chefe = dados.get("chefe")
        self.proxima = dados.get("proxima")
        self.entradas = dict(dados.get("entradas", {}))
        self.drops_da_area = list(dados.get("drops_da_area", []))
        self.consumiveis_da_area = list(dados.get("consumiveis_da_area", []))
        self.multiplicador_inimigos = dict(dados.get("multiplicador_inimigos", {}))   # equilíbrio só desta fase
        self.zonas = list(dados.get("zonas", []))   # uma por variante: {"nome", "musica"} (ex.: Reino dos Ratos)
        self.zona_do_chefe = dados.get("zona_do_chefe")
        self.modo_dificil = dados.get("modo_dificil")   # 2ª carta na área do chefe, depois de vencê-lo (ex.: A Corte Completa)
        self.desafio = dados.get("desafio")         # vencer o chefe sem um status: {"feito", "sem_status"} (ex.: Imune)

    # ---------------- zonas ----------------
    def zona(self, area, total=None):
        """A zona da área ({"nome", "musica"}) ou None nas fases sem zonas. A área do chefe tem a dela."""
        if self.zona_do_chefe and self.area_do_chefe(area, total):
            return self.zona_do_chefe
        if not self.zonas:
            return None
        indice = self.variantes.index(self.variante(area, total))
        return self.zonas[min(indice, len(self.zonas) - 1)]

    def musica_da_area(self, area, total=None):
        """A música da área: a da zona, se a fase tiver zonas; senão, a da fase."""
        zona = self.zona(area, total)
        return zona.get("musica", self.musica) if zona else self.musica

    # ---------------- áreas e hora ----------------
    def area_do_chefe(self, area, total=None):
        return area >= (total or self.areas)

    def hora(self, area, total=None):
        """0 = dia, 1 = noite. Fases cobertas ficam sempre na noite (como foram desenhadas)."""
        if not self.ciclo:
            return 1.0
        total = total or self.areas
        return max(0.0, min(1.0, (area - 1) / max(1, total - 1)))

    def eh_noite(self, area, total=None):
        return self.hora(area, total) >= LIMIAR_DA_NOITE

    def variante(self, area, total=None):
        """Cena do cenário nesta área: as variantes se sucedem em partes iguais ao longo da fase."""
        total = total or self.areas
        indice = int((area - 1) / max(1, total) * len(self.variantes))
        return self.variantes[max(0, min(len(self.variantes) - 1, indice))]

    def area_original(self, area, total=None):
        """A área equivalente no tamanho original (as passagens do JSON usam esse número)."""
        total = total or self.areas
        return max(1, -(-area * self.areas // max(1, total)))

    # ---------------- inimigos ----------------
    def inimigos_possiveis(self, noite=False, area=None, total=None):
        """Os comuns que podem aparecer. Com a área, numa fase com zonas que tenham "inimigos", só os da zona."""
        zona = self.zona(area, total) if area is not None else None
        base = list(zona["inimigos"]) if zona and zona.get("inimigos") else self.inimigos
        return base + (self.inimigos_noturnos if noite else [])

    def sortear_inimigo(self, rng, noite=False, area=None, total=None):
        """Um inimigo comum: sorteio com os pesos do JSON (os noturnos só entram à noite; zonas: os da zona)."""
        possiveis = self.inimigos_possiveis(noite, area, total)
        if not self.pesos and not (noite and self.inimigos_noturnos):
            return rng.choice(possiveis)
        return rng.choices(possiveis, weights=[self.pesos.get(c, 1) for c in possiveis])[0]

    def mini_chefes_da_area(self, area=None, total=None):
        """Os mini-chefes que podem aparecer: os da zona da área (se ela tiver "mini_chefes") ou os da fase."""
        zona = self.zona(area, total) if area is not None else None
        return list(zona["mini_chefes"]) if zona and zona.get("mini_chefes") else list(self.mini_chefes)

    def todos_os_inimigos(self):
        """Todas as chaves que a fase usa (para validar e para o bestiário)."""
        chaves = self.inimigos + self.inimigos_noturnos + self.elites + self.nomeados + self.mini_chefes
        for zona in self.zonas + ([self.zona_do_chefe] if self.zona_do_chefe else []):
            chaves += [c for c in zona.get("inimigos", []) + zona.get("mini_chefes", []) if c not in chaves]
        return chaves + ([self.chefe] if self.chefe else [])

    # ---------------- drops ----------------
    def sortear_drops(self, rng, bonus=0.0):
        """Materiais e consumíveis da fase depois de um combate: {item: quantidade}."""
        from roguelike.loot import chance_final, materiais_da_fase
        achados = {}
        for drop in self.drops_da_area + materiais_da_fase(self.chave) + self.consumiveis_da_area:
            if rng.random() < chance_final(drop["item"], drop.get("chance", 0.2), bonus):
                minimo, maximo = drop.get("quantidade", [1, 1])
                achados[drop["item"]] = achados.get(drop["item"], 0) + rng.randint(minimo, maximo)
        return achados

    def consumiveis_a_venda(self):
        return [c["item"] for c in self.consumiveis_da_area]

    # ---------------- progressão ----------------
    @property
    def ato(self):
        """Índice do ato desta fase (None = fora dos atos, como o Circo)."""
        return progressao().ato_da_fase(self.chave)

    @property
    def final(self):
        indice = self.ato
        return indice is not None and progressao().atos[indice].final

    def __repr__(self):
        return f"Regiao({self.chave!r})"


# Nome do prompt da fase 4: uma "fase" é uma região
Fase = Regiao


class Ato:
    def __init__(self, indice, dados):
        self.indice = indice
        self.nome = dados["nome"]
        self.fases = list(dados["fases"])
        self.portoes = dados.get("portoes", 2)
        self.final = dados.get("final", False)
        self.secretos = sem_comentarios(dados.get("secretos", {}))
        # equilíbrio do ato: multiplica o total de vida/dano dos inimigos (ex.: {"vida_percentual": 0.6})
        self.multiplicador_inimigos = dict(dados.get("multiplicador_inimigos", {}))

    def disponiveis(self):
        return [f for f in self.fases if regiao(f).disponivel]

    def secretos_abertos(self, marcos):
        """Fases secretas ligadas, já criadas e com todos os marcos pedidos cumpridos."""
        return [chave for chave, dados in self.secretos.items()
                if dados.get("ativo") and chave in todas_as_regioes() and set(dados.get("marcos", [])) <= set(marcos)]

    def __repr__(self):
        return f"Ato({self.nome!r})"


class Progressao:
    def __init__(self, dados):
        self.atos = [Ato(i, a) for i, a in enumerate(dados["atos"])]
        self.areas_por_fase = tuple(dados.get("areas_por_fase", (4, 8)))
        self.areas_do_final = dados.get("areas_do_final", 3)          # um número fixo ou [mínimo, máximo]

    def ato_da_fase(self, chave):
        for ato in self.atos:
            if chave in ato.fases or chave in ato.secretos:
                return ato.indice
        return None

    def sortear_tamanho(self, chave, rng):
        """Quantas áreas a fase terá nesta run ("areas_por_fase"; as do ato final usam "areas_do_final")."""
        indice = self.ato_da_fase(chave)
        minimo, maximo = self.areas_por_fase
        if indice is not None and self.atos[indice].final:
            if isinstance(self.areas_do_final, (list, tuple)):
                minimo, maximo = self.areas_do_final
            else:
                return self.areas_do_final
        return rng.randint(minimo, maximo)

    def fase_inicial(self, rng):
        disponiveis = self.atos[0].disponiveis()
        return rng.choice(disponiveis) if disponiveis else "floresta"

    def proximo_ato(self, indice_atual):
        """O próximo ato com alguma fase disponível (pula os vazios), ou None."""
        for ato in self.atos[indice_atual + 1:]:
            if ato.disponiveis():
                return ato
        return None

    def portoes(self, ato, rng, marcos=()):
        """[(fase, aberta)] do fim de um ato: as disponíveis primeiro, completando com as seladas."""
        abertas = ato.disponiveis()
        rng.shuffle(abertas)
        escolhidas = [(f, True) for f in abertas[:ato.portoes]]
        seladas = [f for f in ato.fases if f not in abertas]
        rng.shuffle(seladas)
        escolhidas += [(f, False) for f in seladas[:ato.portoes - len(escolhidas)]]
        rng.shuffle(escolhidas)
        escolhidas += [(f, True) for f in ato.secretos_abertos(marcos)]
        return escolhidas


_regioes = {}
_progressao = []


def todas_as_regioes():
    if not _regioes:
        for chave, dados in sem_comentarios(carregar("regioes")["regioes"]).items():
            _regioes[chave] = Regiao(chave, dados)
    return _regioes


def regiao(chave):
    return todas_as_regioes()[chave]


def progressao():
    if not _progressao:
        _progressao.append(Progressao(carregar("regioes")["progressao"]))
    return _progressao[0]


def mesma_etapa(a, b):
    """A mesma fase, ou fases alternativas do mesmo ato (ex.: Floresta e Bosque): dividem eventos e treinadores."""
    if a == b:
        return True
    fases = todas_as_regioes()
    return a in fases and b in fases and fases[a].ato is not None and fases[a].ato == fases[b].ato


def fases_iniciais():
    """Fases do 1º ato (toda run começa numa delas: chegar lá não é conquista)."""
    return set(progressao().atos[0].fases)


def tipos_de_encontro():
    return sem_comentarios(carregar("regioes")["encontros"])


def chefes_secretos():
    """Chefes secretos (regioes.json "chefes_secretos"): chave do inimigo -> onde e quando aparecem."""
    return sem_comentarios(carregar("regioes").get("chefes_secretos", {}))
