"""Expedição: o grupo que está sendo montado no acampamento (antes de partir).

Cada NPC mexe numa parte da mesma Expedicao, que fica salva no progresso:
    Capitã          quantos heróis, classe, aparência, nome e semente
    Mago Ancião     raça e subclasse de cada herói
    Arsenal         equipamento inicial de cada herói (peças emprestadas do arsenal)

    expedicao = progresso.expedicao
    expedicao.adicionar("monge")
    expedicao.validar(progresso)          # corrige o que deixou de valer (raça não comprada...)
    herois = expedicao.criar_herois(progresso)
"""

import random

from roguelike.classes import todas_as_classes, criar_heroi
from roguelike.dados import regras

GRUPO_INICIAL = ("guerreiro", "sacerdote", "patrulheira")


class Vaga:
    """Um herói sendo montado."""

    def __init__(self, classe, nome="", aparencia=None, subclasse=None, raca="humano"):
        dados = todas_as_classes()[classe]
        self.classe = classe
        self.nome = nome
        self.aparencia = aparencia if aparencia in dados.aparencias else dados.aparencia_padrao
        self.subclasse = subclasse if subclasse in dados.subclasses else next(iter(dados.subclasses))
        self.raca = raca
        self.equipamento = {}             # espaço -> chave da peça do arsenal (equipamento inicial)

    def trocar_classe(self, classe):
        """Outra classe: aparência e subclasse voltam ao padrão dela (a raça e o nome ficam)."""
        self.classe = classe
        dados = todas_as_classes()[classe]
        self.aparencia = dados.aparencia_padrao
        self.subclasse = next(iter(dados.subclasses))

    def para_dict(self):
        return {"classe": self.classe, "nome": self.nome, "aparencia": self.aparencia,
                "subclasse": self.subclasse, "raca": self.raca, "equipamento": dict(self.equipamento)}

    @classmethod
    def de_dict(cls, dados):
        vaga = cls(dados["classe"], dados.get("nome", ""), dados.get("aparencia"), dados.get("subclasse"),
                   dados.get("raca", "humano"))
        vaga.equipamento = dict(dados.get("equipamento", {}))
        return vaga

    def __repr__(self):
        return f"Vaga({self.classe!r}, {self.nome!r})"


class Expedicao:
    def __init__(self, vagas=None, semente=""):
        self.vagas = list(vagas or [])
        self.semente = semente

    @classmethod
    def padrao(cls, sorteio=None):
        expedicao = cls()
        for classe in GRUPO_INICIAL:
            expedicao.adicionar(classe, sorteio)
        return expedicao

    @staticmethod
    def maximo():
        return regras()["grupo"]["maximo"]

    def cheia(self):
        return len(self.vagas) >= self.maximo()

    def adicionar(self, classe=None, sorteio=None, permitidas=None):
        """Mais um herói (classe que ainda não está no grupo e um nome livre). Devolve a vaga ou None.
        permitidas: as classes que o jogador já tem (Progresso.classes_liberadas); sem ela, todas."""
        if self.cheia():
            return None
        sorteio = sorteio or random.Random()
        classes = list(permitidas if permitidas is not None else todas_as_classes())
        no_grupo = {v.classe for v in self.vagas}
        classe = classe or next((c for c in classes if c not in no_grupo), classes[0])
        usados = {v.nome for v in self.vagas}
        nomes = [n for n in regras()["nomes_herois"] if n not in usados] or regras()["nomes_herois"]
        vaga = Vaga(classe, sorteio.choice(nomes))
        self.vagas.append(vaga)
        return vaga

    def remover(self, vaga):
        """Tira um herói (sempre fica pelo menos um)."""
        if len(self.vagas) > 1 and vaga in self.vagas:
            self.vagas.remove(vaga)
            return True
        return False

    # ---------------- regras do progresso ----------------
    def validar(self, progresso):
        """Corrige o que o progresso não deixa mais: subclasse sem prestígio, raça não comprada, classe que sumiu
        (ou ainda secreta)."""
        classes = progresso.classes_liberadas()
        self.vagas = [v for v in self.vagas if v.classe in classes] or Expedicao.padrao().vagas
        for vaga in self.vagas:
            liberadas = [s.chave for s in progresso.subclasses_disponiveis(vaga.classe)]
            if vaga.subclasse not in liberadas:
                vaga.subclasse = liberadas[0]
            if not progresso.tem_raca(vaga.raca):
                vaga.raca = "humano"
        self.validar_equipamento(progresso.arsenal)
        return self

    def em_uso(self, chave, menos=None):
        """Quantas vagas (fora 'menos') já levam esta peça do arsenal."""
        return sum(1 for v in self.vagas if v is not menos for c in v.equipamento.values() if c == chave)

    def escolher_peca(self, vaga, chave, arsenal, espaco=None):
        """Dá uma peça do arsenal à vaga (no 'espaco' pedido ou no dela). Devolve None se deu certo ou o motivo."""
        from roguelike.itens import item
        peca = item(chave)
        if peca.tipo != "equipamento":
            return "Não é equipável"
        if self.em_uso(chave) >= arsenal.quantidade(chave):
            return "Todas as unidades já estão com alguém"
        if peca.classes and vaga.classe not in peca.classes:
            return "Classe não pode usar"
        if peca.racas and vaga.raca not in peca.racas:
            return "Raça não pode usar"
        espacos = peca.espacos_possiveis()
        if espaco is not None and espaco not in espacos:
            return "Não cabe nesse espaço"
        espaco = espaco or next((e for e in espacos if e not in vaga.equipamento), espacos[0])
        vaga.equipamento[espaco] = chave
        principal = vaga.equipamento.get("arma")
        if espaco == "arma" and getattr(peca, "maos", 1) >= 2:
            vaga.equipamento.pop("arma_secundaria", None)          # duas mãos ocupam a secundária
        elif espaco == "arma_secundaria" and principal and getattr(item(principal), "maos", 1) >= 2:
            vaga.equipamento.pop("arma", None)
        return None

    def validar_equipamento(self, arsenal):
        """Tira do equipamento inicial o que não está mais no arsenal (ou foi escolhido mais vezes do que existe)."""
        from roguelike.equipamentos import espacos
        usados = {}
        for vaga in self.vagas:                       # quem escolheu primeiro fica com a peça
            for espaco, chave in list(vaga.equipamento.items()):
                if espaco not in espacos() or usados.get(chave, 0) >= arsenal.quantidade(chave):
                    del vaga.equipamento[espaco]
                else:
                    usados[chave] = usados.get(chave, 0) + 1

    def criar_herois(self, progresso):
        """Os heróis da run (o progresso aplica raça, talentos e bênçãos em criar_run)."""
        sem_subclasse = "aprendiz" in progresso.especiais_equipados()
        herois = []
        for vaga in self.vagas:
            heroi = criar_heroi(vaga.classe, vaga.nome.strip() or None, vaga.aparencia,
                                None if sem_subclasse else vaga.subclasse)
            heroi.raca = vaga.raca
            heroi.equipamento_inicial = dict(vaga.equipamento)     # o progresso equipa em criar_run
            herois.append(heroi)
        return herois

    # ---------------- salvar ----------------
    def para_dict(self):
        return {"vagas": [v.para_dict() for v in self.vagas], "semente": self.semente}

    @classmethod
    def de_dict(cls, dados):
        if not dados:
            return cls.padrao()
        vagas = []
        for vaga in dados.get("vagas", []):
            try:
                vagas.append(Vaga.de_dict(vaga))
            except KeyError:                      # classe que não existe mais
                continue
        return cls(vagas, dados.get("semente", "")) if vagas else cls.padrao()
