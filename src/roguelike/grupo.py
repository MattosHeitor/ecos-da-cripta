"""O grupo: até 5 heróis, os jogadores que os comandam (cada um com a sua mochila e o seu ouro) e o baú da equipe.

Cada herói é comandado por um Jogador (roguelike/posse.py). No solo há um jogador só ("local"), dono de todos; no
multiplayer cada pessoa comanda os seus. Os heróis de um jogador dividem a mochila DELE (heroi.inventario é ela).
Itens passam de um jogador a outro pelo baú da equipe (colocar e retirar).

O ouro é de cada jogador. grupo.ouro é a soma, e mudar grupo.ouro (eventos, pedágio, roubos...) divide entre eles:
    ganhar   pelo número de heróis de cada um (quem tem 2 heróis ganha o dobro de quem tem 1)
    perder   pelo ouro de cada um (quem tem mais paga mais; ninguém fica negativo)
Quem compra, vende ou paga por um herói usa o próprio ouro (Jogador.ouro).
"""

from roguelike.dados import regras
from roguelike.itens import item
from roguelike.posse import BauDaEquipe, jogador_local

# Classes/subclasses que contam como "curandeiro" (o descanso maior cura menos se houver um)
CURANDEIROS = {"sacerdote", "druida", "bardo"}


def dividir(total, pesos):
    """Divide 'total' (inteiro) pelos 'pesos' (inteiros): partes inteiras que somam o total. O que sobra das divisões
    vai para os maiores restos (no empate, a ordem da lista). Tudo inteiro: dá igual em qualquer computador."""
    soma = sum(pesos)
    if total <= 0 or soma <= 0:
        return [0] * len(pesos)
    partes = [total * p // soma for p in pesos]
    restos = [total * p % soma for p in pesos]
    for i in sorted(range(len(pesos)), key=lambda k: (-restos[k], k))[:total - sum(partes)]:
        partes[i] += 1
    return partes


class Grupo:
    def __init__(self, herois=None, ouro=None, jogadores=None):
        self.herois = []
        self.jogadores = list(jogadores) if jogadores else [jogador_local()]
        self.bau = BauDaEquipe()         # baú da equipe, sem limite
        for i, jogador in enumerate(self.jogadores):         # cada um começa com o ouro inicial (ou 'ouro', no 1º)
            jogador.ouro = regras()["economia"]["ouro_inicial"] if ouro is None else (ouro if i == 0 else 0)
        for heroi in herois or []:
            self.adicionar(heroi)

    # ---------------- ouro ----------------
    @property
    def ouro(self):
        """O ouro de todos os jogadores somado."""
        return sum(j.ouro for j in self.jogadores)

    @ouro.setter
    def ouro(self, valor):
        """Muda o total: a diferença é dividida entre os jogadores (ganhar_ouro / perder_ouro)."""
        diferenca = valor - self.ouro
        if diferenca > 0:
            self.ganhar_ouro(diferenca)
        elif diferenca < 0:
            self.perder_ouro(-diferenca)

    def ganhar_ouro(self, total):
        """Divide o ouro ganho pelos heróis de cada jogador. Devolve {id do jogador: parte}."""
        com_herois = [j for j in self.jogadores if self.herois_de(j)] or self.jogadores[:1]
        partes = dividir(total, [max(1, len(self.herois_de(j))) for j in com_herois])
        for jogador, parte in zip(com_herois, partes):
            jogador.ouro += parte
        return {j.id: p for j, p in zip(com_herois, partes)}

    def perder_ouro(self, total):
        """Tira do grupo, de cada um pelo ouro que tem (nunca mais do que o grupo tem). Devolve {id: parte}."""
        partes = dividir(min(total, self.ouro), [j.ouro for j in self.jogadores])
        for jogador, parte in zip(self.jogadores, partes):
            jogador.ouro -= parte
        return {j.id: p for j, p in zip(self.jogadores, partes)}

    def enviar_ouro(self, de, para, quantidade):
        """Um jogador manda ouro a outro. Devolve True se deu certo."""
        if de == para or quantidade <= 0 or de.ouro < quantidade:
            return False
        de.ouro -= quantidade
        para.ouro += quantidade
        return True

    @property
    def bau(self):
        return self._bau

    @bau.setter
    def bau(self, inventario):
        """Aceita um Inventario comum (saves antigos, testes) e o transforma no baú da equipe."""
        self._bau = inventario if isinstance(inventario, BauDaEquipe) else BauDaEquipe.a_partir_de(inventario)

    # ---------------- membros ----------------
    def maximo(self):
        return regras()["grupo"]["maximo"]

    def cheio(self):
        return len(self.herois) >= self.maximo()

    def adicionar(self, heroi, jogador=None):
        """Entra no grupo comandado por 'jogador' (sem: o primeiro jogador, que no solo é o único)."""
        if self.cheio():
            return False
        self.herois.append(heroi)
        self.dar_heroi(heroi, jogador or self.jogadores[0])
        return True

    # ---------------- jogadores ----------------
    def jogador(self, identificador):
        """O Jogador com esse id (ou None)."""
        return next((j for j in self.jogadores if j.id == identificador), None)

    def entrar(self, jogador):
        """Mais um jogador na partida (multiplayer). Devolve o jogador."""
        if self.jogador(jogador.id) is None:
            self.jogadores.append(jogador)
        return self.jogador(jogador.id)

    def dar_heroi(self, heroi, jogador):
        """O herói passa a ser comandado por 'jogador' e a usar a mochila dele. Se o herói ainda tinha uma
        mochila própria (recém-criado, save antigo), o que havia nela vai para a do jogador (o que não couber, ao baú)."""
        jogador = self.entrar(jogador)
        anterior = getattr(heroi, "inventario", None)
        heroi.jogador = jogador
        heroi.inventario = jogador.mochila
        if anterior is not None and anterior is not jogador.mochila and \
                not any(anterior is j.mochila for j in self.jogadores):
            itens, anterior.itens = dict(anterior.itens), {}
            for chave, quantidade in itens.items():
                self.guardar_em(jogador.mochila, chave, quantidade)

    def herois_de(self, jogador):
        return [h for h in self.herois if h.jogador == jogador]

    def mochilas(self):
        """A mochila de cada jogador (cada uma uma vez só, mesmo com vários heróis)."""
        return [j.mochila for j in self.jogadores]

    def guardar_em(self, mochila, chave, quantidade=1):
        """Guarda na mochila; o que não couber vai para o baú. Devolve quanto foi para o baú."""
        if mochila is not None and mochila.adicionar(chave, quantidade):
            return 0
        self.bau.adicionar(chave, quantidade)
        return quantidade

    # ---------------- itens entre mochilas e o baú da equipe ----------------
    def colocar_no_bau(self, heroi, chave, quantidade=1):
        """O jogador do herói põe no baú itens da mochila dele."""
        return self.bau.colocar(heroi.jogador, heroi.inventario, chave, quantidade, heroi.nome)

    def pegar_do_bau(self, heroi, chave, quantidade=1):
        """O jogador do herói pega do baú para a mochila dele."""
        return self.bau.retirar(heroi.jogador, heroi.inventario, chave, quantidade, heroi.nome)

    def passar(self, de, para, chave, quantidade=1):
        """Itens da mochila de um jogador para a de outro (pelo baú: coloca e o outro retira).
        Heróis do mesmo jogador dividem a mochila: não há o que passar."""
        if de.inventario is para.inventario:
            return False
        return self.bau.passar(de.jogador, de.inventario, para.jogador, para.inventario, chave, quantidade)

    def vivos(self):
        return [h for h in self.herois if h.esta_vivo()]

    def caidos(self):
        return [h for h in self.herois if not h.esta_vivo()]

    def todos_caidos(self):
        return not self.vivos()

    def nivel_medio(self):
        return round(sum(h.nivel for h in self.herois) / len(self.herois)) if self.herois else 1

    def tem_curandeiro(self):
        for heroi in self.vivos():
            if heroi.classe.chave in CURANDEIROS or (heroi.subclasse and heroi.subclasse.chave in CURANDEIROS):
                return True
        return False

    # ---------------- cura e reviver ----------------
    def descansar(self, fracao=None):
        """Descanso entre áreas: cada vivo cura o maior entre 10 de vida ou 15% da vida máxima.

        Com 'fracao' (descanso maior), cura essa fração da vida máxima.
        Devolve {herói: vida curada}.
        """
        regra = regras()["descanso"]
        curados = {}
        for heroi in self.vivos():
            if fracao is None:
                valor = max(regra["cura_minima"], int(heroi.vida_maxima * regra["cura_percentual"]))
            else:
                valor = int(heroi.vida_maxima * fracao)
            antes = heroi.vida
            heroi.vida = min(heroi.vida_maxima, heroi.vida + valor)
            curados[heroi] = heroi.vida - antes
        return curados

    def reviver(self, heroi, fracao):
        if heroi.esta_vivo():
            return False
        heroi.vida = max(1, round(heroi.vida_maxima * fracao))
        return True

    # ---------------- equipamento e itens ----------------
    def equipar(self, heroi, chave, origem=None, espaco=None):
        """Equipa um item que está em 'origem' (inventário do herói ou baú), no 'espaco' pedido ou no livre.

        O item que sai vai para o inventário do herói (ou para o baú, se não couber).
        """
        origem = origem or heroi.inventario
        objeto = item(chave)
        if not origem.tem(chave):
            return False
        if objeto.tipo == "consumivel":
            # O espaço de consumível só "aponta" o item: as unidades ficam no inventário do herói
            return origem is heroi.inventario and heroi.equipar(objeto)[0]
        deu_certo, saiu = heroi.equipar(objeto, espaco)
        if not deu_certo:
            return False
        origem.remover(chave)
        for antigo in saiu:                     # (arma de duas mãos também tira a secundária)
            if antigo.tipo != "consumivel":
                self.guardar(heroi, antigo.chave)
        return True

    def desequipar(self, heroi, espaco):
        antigo = heroi.desequipar(espaco)
        if antigo is None:
            return False
        if antigo.tipo != "consumivel":
            self.guardar(heroi, antigo.chave)
        return True

    def guardar(self, heroi, chave, quantidade=1):
        """Guarda no inventário do herói; se estiver cheio, vai para o baú."""
        if not heroi.inventario.adicionar(chave, quantidade):
            self.bau.adicionar(chave, quantidade)

    def usar_fora_do_combate(self, chave, origem, alvo, rng):
        """Usa um consumível no acampamento (poções, comida, pena da fênix, tomos)."""
        objeto = item(chave)
        if objeto.tipo != "consumivel" or not objeto.fora_de_combate or not origem.tem(chave):
            return False
        if hasattr(objeto, "ensina"):                       # tomo: ensina um golpe
            if not objeto.pode_ler(alvo):
                return False
            alvo.aprender(objeto.ensina)
            origem.remover(chave)
            return True
        usou = False
        alvos = self.vivos() if getattr(objeto, "alvo", "") == "aliados" else [alvo]     # ex.: Ensopado da Taverna
        for efeito in objeto.efeitos:
            tipo = efeito.dados["tipo"]
            for quem in alvos:
                if tipo == "cura" and quem.esta_vivo() and quem.vida < quem.vida_maxima:
                    minimo, maximo = efeito.dados.get("cura", [0, 0])
                    valor = rng.randint(minimo, maximo) + quem.vida_maxima * efeito.dados.get("percentual", 0)
                    quem.vida = min(quem.vida_maxima, quem.vida + round(valor))
                    usou = True
                elif tipo == "reviver" and not quem.esta_vivo():
                    self.reviver(quem, efeito.dados.get("percentual", 0.5))
                    usou = True
                elif tipo == "purificar" and "peste" in efeito.dados.get("so", []) and quem.peste > 0:
                    quem.peste = 0                          # Tônico do Médico: a Peste segue entre as lutas
                    usou = True
        if usou:
            origem.remover(chave)
        return usou
