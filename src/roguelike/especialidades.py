"""Classe, subclasse e especialização: a "árvore" de um herói.

    Especialidade (base: nome, descrição, passivas, modificadores, golpes, roupa)
     ├── ClasseDeHeroi   Mago                  (classes.py: atributos, vida, iniciativa)
     ├── Subclasse       Piromante             escolhida na Capitã (liberada pelo prestígio)
     └── Especializacao  Arauto das Cinzas     aprendida na run, com o treinador

Herança: as três são Especialidades e compartilham o mesmo jeito de dar bônus ao herói.
Composição: o herói TEM uma TrilhaDeClasse (classe + subclasse + especialização). Assim ele
pode "se transformar" no meio da run trocando uma peça, sem virar outro objeto — algo que a
herança direta (Heroi -> Mago -> Piromante) não permitiria.
"""

from roguelike.dados import regras


class Especialidade:
    """O que classe, subclasse e especialização têm em comum."""

    tipo = "especialidade"

    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.descricao = dados.get("descricao", "")
        self.passivas = list(dados.get("passivas", []))
        self.modificadores = dict(dados.get("modificadores", {}))
        self.sprite = dados.get("sprite")              # roupa própria (None = a de quem vem antes)
        self.golpes = list(dados.get("golpes", dados.get("habilidades", [])))

    def __repr__(self):
        return f"{type(self).__name__}({self.chave!r})"


class Subclasse(Especialidade):
    """Escolhida antes de partir. Dá um golpe-assinatura e mais golpes ao subir de nível."""

    tipo = "subclasse"

    def __init__(self, chave, classe, dados):
        super().__init__(chave, dados)
        self.classe = classe
        self.prestigio = dados.get("prestigio", 0)    # nível de prestígio da classe que libera
        self.niveis_golpes = list(dados.get("niveis_golpes", regras()["subclasse"]["niveis_golpes"]))
        self.nivel_maximo = regras()["nivel"]["maximo_habilidade_subclasse"]
        self.especializacoes = {chave_esp: Especializacao(chave_esp, self, dados_esp)
                                for chave_esp, dados_esp in dados.get("especializacoes", {}).items()}

    @property
    def assinatura(self):
        """O primeiro golpe: vem junto com a subclasse."""
        return self.golpes[0] if self.golpes else None

    def golpes_no_nivel(self, nivel):
        """Golpes que chegam exatamente neste nível do herói."""
        return [g for g, n in zip(self.golpes, self.niveis_golpes) if n == nivel]

    def golpes_ate_o_nivel(self, nivel):
        return [g for g, n in zip(self.golpes, self.niveis_golpes) if n <= nivel]

    def nivel_do_golpe(self, chave):
        for g, n in zip(self.golpes, self.niveis_golpes):
            if g == chave:
                return n
        return None


class Especializacao(Especialidade):
    """Forma avançada de uma subclasse, ensinada por um treinador durante a run."""

    tipo = "especializacao"

    def __init__(self, chave, subclasse, dados):
        super().__init__(chave, dados)
        self.subclasse = subclasse
        self.regiao = dados.get("regiao", "floresta")     # onde aparece o treinador
        self.nivel_minimo = dados.get("nivel_minimo", regras()["subclasse"]["nivel_especializacao"])

    @property
    def golpe(self):
        return self.golpes[0] if self.golpes else None


class TrilhaDeClasse:
    """Classe + subclasse + especialização de um herói (as peças trocam, o herói continua o mesmo)."""

    def __init__(self, classe):
        self.classe = classe
        self.subclasse = None
        self.especializacao = None

    def ativas(self):
        """As especialidades que valem agora, da mais geral à mais específica."""
        return [e for e in (self.classe, self.subclasse, self.especializacao) if e is not None]

    def atual(self):
        return self.ativas()[-1]

    def nome(self):
        return self.atual().nome

    def sprite(self, padrao):
        """A roupa mais específica que existir (especialização > subclasse > aparência da classe)."""
        for especialidade in reversed(self.ativas()[1:]):
            if especialidade.sprite:
                return especialidade.sprite
        return padrao
