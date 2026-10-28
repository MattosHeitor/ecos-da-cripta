"""Combate em ondas (ex.: o Enxame de Ratos das Galerias): várias lutas seguidas, sem descanso entre elas.

Depois de cada onda vencida o grupo escolhe: continuar (cada onda vale mais estrelas: mais XP, ouro e loot) ou
fugir com o que já ganhou. Quem vence a última leva o "premio" (consequências de evento, como no eventos.json).

    eventos.json, consequência "ondas":
        {"tipo": "ondas", "nome": "Enxame de Ratos", "folego": 0.25,
         "ondas": [{"estrelas": 2, "inimigos": [...], "sorteados": {"quantos": 1, "de": [...]}}, ...],
         "premio": [consequências], "textos": {"entre": "...", "fim": "...", "premio": "...", "fuga": "..."}}

Os inimigos sorteados são decididos no começo (a tela mostra a próxima onda). Não vai no save: como em todo evento
que vira luta, fechar o jogo no meio volta ao começo do evento, sem o que as ondas deram (Run.pode_salvar).
"""

from roguelike.encontros import EncontroCombate, descrever_inimigos


class CombateEmOndas:
    def __init__(self, nome, ondas, premio=None, textos=None, folego=0.0, vencidas=0, atual=1, sem_fuga=False):
        self.nome = nome
        # cada onda: "estrelas", "inimigos" e, se quiser, "categoria" (ex.: "chefe"), "nome" (na trilha da tela),
        # "titulo" (o nome do encontro) e "trono" (quem espera no trono e volta: Combate.de_volta)
        self.ondas = [dict(o, inimigos=list(o["inimigos"])) for o in ondas]
        self.premio = [dict(p) for p in premio or []]       # consequências ao vencer a última onda
        self.textos = dict(textos or {})                    # entre as ondas, antes e depois do prêmio, na fuga
        self.folego = folego                                # fração da vida que os vivos recuperam entre as ondas
        self.vencidas = vencidas
        self.atual = atual                                  # a onda em luta (ou a última vencida, entre as ondas)
        self.sem_fuga = sem_fuga                            # True: entre as partes só dá para usar itens e seguir

    @classmethod
    def sortear(cls, dados, rng):
        """Monta as ondas do JSON: "inimigos" fixos + "sorteados" ({"quantos", "de"})."""
        ondas = []
        for onda in dados["ondas"]:
            chaves = list(onda.get("inimigos", []))
            sorteio = onda.get("sorteados")
            if sorteio:
                chaves += [rng.choice(sorteio["de"]) for _ in range(sorteio["quantos"])]
            ondas.append({"estrelas": onda.get("estrelas", 2), "inimigos": chaves})
        return cls(dados.get("nome", "Ondas"), ondas, dados.get("premio"), dados.get("textos"), dados.get("folego", 0.0))

    @classmethod
    def continuacao(cls, encontro, parte):
        """Uma luta que continua em outra parte (o Rei dos Ratos fugiu para o trono e vem a Rainha): a 1ª parte (o
        encontro) já está vencida; entre as duas, só usar itens. "parte" vem de Combate.proxima_parte."""
        ondas = [{"estrelas": encontro.estrelas, "inimigos": encontro.inimigos, "categoria": encontro.tipo,
                  "nome": parte.get("nome_da_primeira", encontro.nome), "titulo": encontro.nome},
                 {"estrelas": parte.get("estrelas", encontro.estrelas), "inimigos": parte["inimigos"],
                  "categoria": parte.get("categoria", encontro.tipo), "nome": parte.get("nome", "Parte 2"),
                  "titulo": parte.get("titulo"), "trono": parte.get("trono")}]
        return cls(parte.get("nome_da_luta", encontro.nome), ondas, textos=parte.get("textos"),
                   folego=parte.get("folego", 0.0), sem_fuga=True)       # (a Run marca a 1ª como vencida, com o fôlego)

    @property
    def total(self):
        return len(self.ondas)

    def nome_da_onda(self, numero):
        return self.ondas[numero - 1].get("nome") or f"Onda {numero}"

    def encontro(self, numero=None):
        """O EncontroCombate de uma onda (padrão: a atual). O nome diz qual é ("Enxame de Ratos · Onda 2/3")."""
        numero = numero or self.atual
        onda = self.ondas[numero - 1]
        titulo = onda.get("titulo") or f"{self.nome} · Onda {numero}/{self.total}"
        encontro = EncontroCombate(titulo, descrever_inimigos(onda["inimigos"]), onda["estrelas"], onda["inimigos"],
                                   onda.get("categoria", "combate"))
        if onda.get("trono"):
            encontro.trono = dict(onda["trono"])            # quem espera no trono (Run.criar_combate)
        return encontro

    def proxima(self):
        """A próxima onda ({"estrelas", "inimigos"}) ou None se a atual é a última."""
        return self.ondas[self.atual] if self.atual < self.total else None

    def em_luta(self):
        return self.vencidas < self.atual

    def terminou(self):
        return self.vencidas >= self.total

    def vencer(self):
        self.vencidas = self.atual

    def continuar(self):
        """Vai para a próxima onda (só entre as ondas). Devolve o encontro dela, ou None."""
        if self.em_luta() or self.terminou():
            return None
        self.atual += 1
        return self.encontro()

    def texto(self, chave):
        """Um dos "textos" do JSON ("entre", "fim", "premio", "fuga"), com {vencidas}, {total} e {folego} trocados."""
        return self.textos.get(chave, "").format(vencidas=self.vencidas, total=self.total, folego=round(self.folego * 100))
