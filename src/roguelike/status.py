"""Efeitos de status: sangramento, veneno, atordoado, escudo, provocação...

Os números e textos ficam em regras.json ("status"). Aqui fica só o
COMPORTAMENTO, uma subclasse de Status para cada tipo:

- StatusModificador: só muda valores (ex.: fortalecido = +25% de dano);
- DanoPorTurno: sangramento, veneno e queimadura;
- PerdeVez: atordoado e congelado;
- Regeneracao, Energizado, Escudo, Provocacao, Furtivo, ContraAtaque, Espinhos;
- Peste: doença em níveis que segue entre as lutas (Reino dos Ratos);
- Encantado: no próximo turno ataca um aliado (a flauta do Flautista Caído);
- EditoReal: uma lei do Rei dos Ratos (proibido curar, usar magia...); quem desobedece é punido (Combate);
- ModificadorAcumulado: cada acúmulo soma de novo os modificadores (Cofre Real do Rei);
- Intocavel e Silencio: a roda da Rainha dos Ratos (ratos de trás e nó fechado; o Guincho silencia).

A duração conta os turnos do DONO do status: diminui 1 no fim de cada
turno dele.
"""

from roguelike import elementos
from roguelike.dados import regras


def dados_do_status(chave):
    try:
        return regras()["status"][chave]
    except KeyError:
        raise ValueError(f"Status desconhecido: {chave}") from None


class Status:
    """Classe base. Subclasses mudam só os métodos que precisam."""

    def __init__(self, chave, duracao=None, valor=0, acumulos=1, origem=None):
        dados = dados_do_status(chave)
        self.chave = chave
        self.nome = dados["nome"]
        self.tipo = dados["tipo"]                  # "positivo" ou "negativo"
        self.descricao = dados.get("descricao", "")
        self.duracao = duracao if duracao is not None else dados.get("duracao", 1)
        self.valor = valor
        self.acumulos = acumulos
        self.origem = origem                       # quem aplicou
        # Aplicado no próprio turno do dono? Então o fim deste turno não conta.
        self.pular_proximo_fim = False

    # ---------------- consulta ----------------
    def modificadores(self):
        """Bônus enquanto o status durar, ex.: {"dano_causado": 0.25}."""
        return dados_do_status(self.chave).get("modificadores", {})

    def impede_acao(self):
        return False

    def perde_a_vez(self, rng):
        """No início do turno: o dono perde a vez? (Medo sorteia; atordoado sempre.)"""
        return self.impede_acao()

    def provoca(self):
        return False

    def esconde(self):
        return False

    def intocavel(self):
        """Ninguém pode mirar o dono, nem com golpe em área (ex.: os ratos de trás da roda da Rainha)."""
        return False

    def fora_da_fila(self):
        """O dono não entra na fila de turnos enquanto durar."""
        return False

    def silencia(self):
        """O dono só pode usar golpes sem custo de energia."""
        return False

    def delira(self):
        """No início do turno: o dono age sem rumo (Febre Negra da Peste, Encantado)?"""
        return False

    def delirio(self):
        """Como é o delírio (Combate.delirar): evento, texto ("{nome}" = o dono), em quem bate ("todos" ou
        "aliados") e se só usa golpes de um alvo só."""
        return {"evento": "febre", "texto": "{nome} age sem rumo!", "alvos": "todos", "so_golpes": False}

    def ao_delirar(self):
        """Depois de delirar (a Peste volta a um nível mais baixo)."""

    def proibe(self, dono, usuario, tipo, coisa, alvos):
        """Uma lei do dono (Édito Real): esta ação de um oponente é proibida? tipo = "habilidade", "item" ou
        "concentrar"; coisa = o golpe ou o item; alvos = quem ele mirou."""
        return False

    def sprite(self):
        """Sprite de transformação (ex.: forma_de_dragao -> "dragao_filhote"), ou None."""
        return dados_do_status(self.chave).get("sprite")

    def rotulo(self):
        """Texto curto para a tela, ex.: "Sangramento x3 (2)"."""
        texto = self.nome
        if dados_do_status(self.chave).get("acumula"):
            texto += f" x{self.acumulos}"
        elif self.valor:
            texto += f" {self.valor}"
        return f"{texto} ({self.duracao})"

    # ---------------- quando é aplicado de novo ----------------
    def juntar(self, novo):
        """O mesmo status foi aplicado de novo: renova a duração e fica com o maior valor."""
        self.duracao = max(self.duracao, novo.duracao)
        self.valor = max(self.valor, novo.valor)
        if dados_do_status(self.chave).get("acumula"):
            self.acumulos += novo.acumulos

    def aliviar(self, niveis=1):
        """Purificar ou cura de luz: devolve True se o status sai inteiro (a Peste só perde níveis)."""
        return True

    # ---------------- ganchos chamados pelo combate ----------------
    def inicio_do_turno(self, dono, combate):
        """Acontece antes do dono agir (dano de veneno, cura de regeneração...)."""

    def ao_ser_golpeado(self, dono, atacante, combate):
        """Acontece quando o dono recebe um golpe direto (não em área)."""

    def absorver(self, dano):
        """Escudos absorvem dano. Devolve o dano que sobrou."""
        return dano

    def fim_do_turno(self):
        """Diminui a duração. Devolve True quando o status acabou."""
        if self.pular_proximo_fim:
            self.pular_proximo_fim = False
            return self.duracao <= 0
        self.duracao -= 1
        return self.duracao <= 0


class StatusModificador(Status):
    """Status que só muda valores (fortalecido, enfraquecido, amaldiçoado...)."""


class DanoPorTurno(Status):
    """Sangramento (dano = acúmulos), veneno e queimadura (dano = valor)."""

    def dano_do_turno(self):
        if dados_do_status(self.chave).get("acumula"):
            return self.acumulos
        return self.valor

    def inicio_do_turno(self, dono, combate):
        dano = self.dano_do_turno()
        if dano <= 0:
            return
        elemento = elementos.do_status(self.chave)          # queimadura = fogo, veneno = veneno...
        efetividade = None
        if elemento:
            dano = max(1, round(dano * elementos.multiplicador(self.origem, dono, elemento)))
            efetividade = elementos.efetividade(dono, elemento)
        combate.causar_dano_direto(dono, dano, self.origem, motivo=self.chave, elemento=elemento,
                                   efetividade=efetividade)


class PerdeVez(Status):
    """Atordoado e congelado: o dono perde a próxima vez."""

    def impede_acao(self):
        return True


class Medo(Status):
    """Amedrontado: menos dano e uma chance (regras.json "chance_perder_vez") de perder a vez."""

    def perde_a_vez(self, rng):
        return rng.random() < dados_do_status(self.chave).get("chance_perder_vez", 0.3)


class Regeneracao(Status):
    def inicio_do_turno(self, dono, combate):
        combate.curar(dono, self.valor, self.origem, motivo="regeneracao")


class Energizado(Status):
    def inicio_do_turno(self, dono, combate):
        combate.dar_energia(dono, max(1, self.valor), motivo="energizado")


class Escudo(Status):
    """Absorve dano. Some quando o valor chega a zero."""

    def juntar(self, novo):
        self.valor += novo.valor
        self.duracao = max(self.duracao, novo.duracao)

    def absorver(self, dano):
        absorvido = min(self.valor, dano)
        self.valor -= absorvido
        if self.valor <= 0:
            self.duracao = 0
        return dano - absorvido


class Provocacao(Status):
    def provoca(self):
        return True


class Furtivo(Status):
    def esconde(self):
        return True


class Marcador(Status):
    """Só mostra algo controlado por uma passiva (escudo elemental, fase do chefe): não acaba sozinho."""

    def fim_do_turno(self):
        return False

    def rotulo(self):
        return f"{self.nome} {self.valor}" if self.valor else self.nome


class ContraAtaque(Status):
    """Revida golpes diretos com o valor do status."""

    def ao_ser_golpeado(self, dono, atacante, combate):
        if dono.esta_vivo() and atacante.esta_vivo() and self.valor > 0:
            combate.golpear(dono, atacante, self.valor, revide=True)


class Espinhos(Status):
    """Quem golpear o dono sofre dano direto."""

    def ao_ser_golpeado(self, dono, atacante, combate):
        if atacante.esta_vivo() and self.valor > 0:
            combate.causar_dano_direto(atacante, self.valor, dono, motivo="espinhos")


class Peste(Status):
    """Doença em níveis (acúmulos de 1 até o "maximo"). Não acaba sozinha e segue entre as lutas
    (o Heroi guarda o nível em heroi.peste).

    1-2: perde vida no início do turno; 3-4: e recebe menos cura; no máximo: Febre Negra (o combate
    faz o dono agir sem rumo 1 turno e a doença volta ao nível "febre_volta_para").
    """

    def dados(self):
        return dados_do_status(self.chave)

    @property
    def nivel(self):
        return self.acumulos

    def maximo(self):
        return self.dados().get("maximo", 5)

    def juntar(self, novo):
        self.acumulos = min(self.maximo(), self.acumulos + novo.acumulos)

    def modificadores(self):
        if self.acumulos >= self.dados().get("cura_reduzida_a_partir", 3):
            return self.dados().get("modificadores_graves", {})
        return {}

    def dano_do_turno(self):
        tabela = self.dados()["dano_por_nivel"]
        return tabela[max(1, min(self.acumulos, len(tabela))) - 1]

    def inicio_do_turno(self, dono, combate):
        combate.causar_dano_direto(dono, self.dano_do_turno(), self.origem, motivo="peste")

    def delira(self):
        return self.acumulos >= self.maximo()

    def delirio(self):
        return {"evento": "febre", "texto": "{nome} arde em Febre Negra e age sem rumo!", "alvos": "todos",
                "so_golpes": False}

    def ao_delirar(self):
        self.passou_a_febre()

    def passou_a_febre(self):
        self.acumulos = self.dados().get("febre_volta_para", 3)

    def aliviar(self, niveis=1):
        self.acumulos -= niveis
        return self.acumulos <= 0

    def fim_do_turno(self):
        self.pular_proximo_fim = False
        return False

    def rotulo(self):
        return f"{self.nome} {self.acumulos}" + (" (Febre Negra)" if self.delira() else "")


class Encantado(Status):
    """A flauta do Flautista Caído: no próximo turno o dono ataca um aliado (golpe de um alvo só sorteado).
    Num bando de ratos (Flauta do Caçador de Ratos), os ratos mordem os próprios companheiros."""

    def delira(self):
        return True

    def delirio(self):
        return {"evento": "encanto", "texto": "{nome} dança ao som da flauta e ataca um aliado!", "alvos": "aliados",
                "so_golpes": True}


def cura_alguem(coisa):
    return any(e.dados["tipo"] in ("cura", "reviver") for e in getattr(coisa, "efeitos", []))


def eh_magia(coisa):
    """Golpe mágico: do tipo "magico" (escala com INT, FÉ ou CAR) ou com um elemento que não é o físico."""
    if getattr(coisa, "tipo", None) == "magico":                    # (Golpe.tipo é uma propriedade)
        return True
    elementos_usados = [getattr(coisa, "elemento", None)] + [e.dados.get("elemento") for e in getattr(coisa, "efeitos", [])]
    return any(e not in (None, elementos.PADRAO) for e in elementos_usados)


class EditoReal(Status):
    """Uma lei do Rei dos Ratos enquanto durar (regras.json: "proibe"):
        cura          golpe ou item que cura (ou revive)
        magia         golpe que não é físico
        atacar_dono   acertar o Rei (de um alvo só ou em área)
        agir          qualquer coisa além de Concentrar (Ajoelhem-se!)
    Quem desobedece leva o castigo do Combate (punir_desobediencia). A duração conta os turnos do Rei."""

    def proibe(self, dono, usuario, tipo, coisa, alvos):
        regra = dados_do_status(self.chave)["proibe"]
        if regra == "agir":
            return tipo != "concentrar"
        if tipo == "concentrar":
            return False
        if regra == "cura":
            return cura_alguem(coisa)
        if regra == "magia":
            return tipo == "habilidade" and eh_magia(coisa)
        if regra == "atacar_dono":
            return dono in alvos
        return False


class Intocavel(Marcador):
    """Fora de alcance enquanto a passiva quiser (Atrás da Roda, Nó Fechado); "fora_da_fila": true no regras.json
    também tira o dono da fila de turnos."""

    def intocavel(self):
        return True

    def fora_da_fila(self):
        return dados_do_status(self.chave).get("fora_da_fila", False)


class Silencio(Status):
    """Silenciado (o Guincho da roda da Rainha): só golpes sem custo de energia."""

    def silencia(self):
        return True


class ModificadorAcumulado(StatusModificador):
    """Cada acúmulo soma os modificadores de novo, até "maximo" acúmulos (ex.: Cofre Real: +2 de defesa por imposto)."""

    def modificadores(self):
        return {chave: valor * self.acumulos for chave, valor in super().modificadores().items()}

    def juntar(self, novo):
        super().juntar(novo)
        self.acumulos = min(self.acumulos, dados_do_status(self.chave).get("maximo", 99))

    def rotulo(self):
        return f"{self.nome} x{self.acumulos}"


# Nome da "classe" no regras.json -> classe Python
CLASSES_DE_STATUS = {
    "modificador": StatusModificador,
    "dano_por_turno": DanoPorTurno,
    "perde_vez": PerdeVez,
    "medo": Medo,
    "regeneracao": Regeneracao,
    "energizado": Energizado,
    "escudo": Escudo,
    "provocacao": Provocacao,
    "furtivo": Furtivo,
    "contra_ataque": ContraAtaque,
    "espinhos": Espinhos,
    "marcador": Marcador,
    "peste": Peste,
    "encanto": Encantado,
    "edito": EditoReal,
    "modificador_acumulado": ModificadorAcumulado,
    "intocavel": Intocavel,
    "silencio": Silencio,
}


def criar_status(chave, duracao=None, valor=0, acumulos=1, origem=None):
    """Cria o status certo a partir do nome, ex.: criar_status("veneno", valor=3)."""
    classe = CLASSES_DE_STATUS[dados_do_status(chave)["classe"]]
    return classe(chave, duracao, valor, acumulos, origem)
