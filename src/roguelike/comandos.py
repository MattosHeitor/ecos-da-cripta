"""Comandos: toda ação de um jogador sobre a run vira um objeto Comando.

    comando = Comprar(indice=2)                  # o que a tela (ou a rede, ou o piloto) quer fazer
    resultado = processador.executar(comando)    # o ProcessadorDeComandos confere, executa e anota

Cada comando sabe:
    validar(estado)    por que NÃO pode (um texto) ou None; não muda nada
    executar(estado)   faz e devolve um Resultado (ok, mensagem, valor)
    para_dict()        os dados em JSON: {"tipo": "comprar", "jogador": "local", "indice": 2}

Os dados são só números e textos (herói = número no grupo; inventário = "bau" ou o número do herói; lutador =
["herois" | "inimigos", número]): o mesmo comando vale em outro computador e ao refazer a partida do zero.
validar() confere se o jogador do comando comanda os heróis envolvidos. As regras continuam na run (run.py,
grupo.py, combate.py...): o comando só confere os números e chama.

    Comando
    ├── no mapa:       EscolherEncontro, IniciarFuga, ConcluirEncontro, Prosseguir (só a ordem das telas no co-op)
    ├── nos encontros: ResolverEvento, ContinuarOndas, EncerrarOndas, DescansoMaior, Treinar, Reviver,
    │                  Comprar, Vender, EnviarOuro (o ouro é de cada jogador)
    ├── no grupo:      Equipar, Desequipar, MoverItem, Descartar, UsarItem, Fabricar, DistribuirPonto,
    │                  MelhorarHabilidade, DecidirGolpeNovo, TrocarGolpe, GuardarGolpe
    └── no combate:    ComecarCombate, AgirNoCombate
"""

from roguelike.estado import BAU
from roguelike.itens import item
from roguelike.posse import JOGADOR_LOCAL

CAMPOS_DE_HEROI = ("heroi", "origem", "de", "para")     # campos que podem apontar um herói (número)


class Resultado:
    """O que um comando fez: ok (deu certo?), a mensagem para a tela e um valor (ex.: o ouro da venda)."""

    def __init__(self, ok=True, mensagem="", valor=None):
        self.ok = bool(ok)
        self.mensagem = mensagem
        self.valor = valor

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"Resultado({self.ok}, {self.mensagem!r})"


class Comando:
    """Uma ação de um jogador. 'campos' = {nome: valor padrão}: os dados do comando (vão no JSON)."""

    tipo = ""
    campos = {}
    precisa_de_run = True
    CAMPOS_QUE_NAO_SAO_HEROI = ()       # campos com nome de herói que guardam outra coisa (ex.: "para" = um jogador)

    def __init__(self, jogador=JOGADOR_LOCAL, **dados):
        desconhecidos = set(dados) - set(self.campos)
        if desconhecidos:
            raise TypeError(f"{type(self).__name__} não tem: {', '.join(sorted(desconhecidos))}")
        self.jogador = jogador
        for nome, padrao in self.campos.items():
            setattr(self, nome, dados.get(nome, padrao))

    def __repr__(self):
        return f"{type(self).__name__}({', '.join(f'{n}={getattr(self, n)!r}' for n in self.campos)})"

    def para_dict(self):
        return {"tipo": self.tipo, "jogador": self.jogador, **{nome: getattr(self, nome) for nome in self.campos}}

    # ---------------- conferir ----------------
    def validar(self, estado):
        """Por que o comando não vale (texto) ou None. Confere a run, os heróis e de quem eles são."""
        if self.precisa_de_run and estado.run is None:
            return "Não há uma run em andamento."
        for nome in CAMPOS_DE_HEROI:
            if nome in self.CAMPOS_QUE_NAO_SAO_HEROI:
                continue
            valor = getattr(self, nome, None) if nome in self.campos else None
            if valor is None or valor == BAU:
                continue
            heroi = estado.heroi(valor)
            if heroi is None:
                return "Esse herói não existe."
            if not estado.pode_comandar(self.jogador, heroi):
                return f"{heroi.nome} é comandado por outro jogador."
        return self.conferir(estado)

    def conferir(self, estado):
        """As regras próprias do comando (as subclasses completam). None = pode."""
        return None

    def executar(self, estado):
        raise NotImplementedError


def conferir_inventario(estado, origem):
    return None if estado.inventario(origem) is not None else "Esse lugar não existe."


# ============================================================
# NO MAPA
# ============================================================

class EscolherEncontro(Comando):
    tipo = "escolher_encontro"
    campos = {"indice": 0}

    def conferir(self, estado):
        run = estado.run
        if run.estado != "escolha":
            return "Agora não dá para escolher o caminho."
        if not isinstance(self.indice, int) or not 0 <= self.indice < len(run.opcoes_de_encontro()):
            return "Esse caminho não existe."
        return None

    def executar(self, estado):
        run = estado.run
        opcao = run.opcoes_de_encontro()[self.indice]
        encontro = run.escolher(self.indice)
        if encontro is None:
            selada = "Passagem selada" if opcao.tipo == "entrada" else "Portão selado"
            return Resultado(False, selada if getattr(opcao, "bloqueado", False) else "Não deu.")
        return Resultado(True, valor=encontro)


class IniciarFuga(Comando):
    """Sair da run: o grupo enfrenta o guardião da saída."""
    tipo = "iniciar_fuga"

    def executar(self, estado):
        encontro = estado.run.iniciar_fuga()
        return Resultado(encontro is not None, valor=encontro)


class Prosseguir(Comando):
    """Não muda a run: numa partida em grupo, leva todos à mesma tela, na ordem do host ("entre_ondas" ou "fim").
    (Sem ele, um computador poderia trocar de tela antes de executar os comandos que vieram antes.)"""
    tipo = "prosseguir"
    campos = {"tela": ""}

    def conferir(self, estado):
        return None if self.tela in ("entre_ondas", "fim") else "Tela desconhecida."

    def executar(self, estado):
        return Resultado(True)


class ConcluirEncontro(Comando):
    """Fecha o encontro e segue (pular_passagem: a passagem foi ignorada, só avança a área)."""
    tipo = "concluir_encontro"
    campos = {"pular_passagem": False}

    def executar(self, estado):
        run = estado.run
        if self.pular_passagem:
            run.encontro = None
        run.concluir_encontro()
        estado.condutor = None                  # a luta (se houve) acabou de vez: o estado é só a run de novo
        return Resultado(True)


# ============================================================
# NOS ENCONTROS
# ============================================================

class ResolverEvento(Comando):
    tipo = "resolver_evento"
    campos = {"indice": 0}

    def conferir(self, estado):
        encontro = estado.run.encontro
        return None if encontro is not None and encontro.tipo == "evento" else "Não há um evento aqui."

    def executar(self, estado):
        resultado = estado.run.resolver_evento(self.indice)
        return Resultado(resultado is not None, valor=resultado)


class ContinuarOndas(Comando):
    tipo = "continuar_ondas"

    def conferir(self, estado):
        return None if estado.run.ondas is not None else "Não há ondas aqui."

    def executar(self, estado):
        encontro = estado.run.proxima_onda()
        return Resultado(encontro is not None, valor=encontro)


class EncerrarOndas(Comando):
    """Fugir com o que já ganhou ou, depois da última onda, recolher o prêmio."""
    tipo = "encerrar_ondas"

    def executar(self, estado):
        return Resultado(True, valor=estado.run.encerrar_ondas())


class DescansoMaior(Comando):
    tipo = "descanso_maior"

    def executar(self, estado):
        return Resultado(True, valor=estado.run.descanso_maior())


class Treinar(Comando):
    tipo = "treinar"
    campos = {"heroi": 0}

    def executar(self, estado):
        heroi = estado.heroi(self.heroi)
        if not estado.run.treinar(heroi):
            return Resultado(False, "Não dá para treinar agora.")
        return Resultado(True, f"{heroi.nome} agora é {heroi.subclasse.nome}! Novos golpes aprendidos.")


class Reviver(Comando):
    """Altar ou necromante: quem manda paga, com o próprio ouro, a volta do herói 'caido' (pode ser de outro jogador)."""
    tipo = "reviver"
    campos = {"caido": 0}

    def conferir(self, estado):
        return None if estado.heroi(self.caido) is not None else "Esse herói não existe."

    def executar(self, estado):
        heroi = estado.heroi(self.caido)
        if not estado.run.reviver_pago(heroi, estado.grupo.jogador(self.jogador)):
            return Resultado(False, "Ouro insuficiente.")
        return Resultado(True, f"{heroi.nome} voltou à vida!")


class Comprar(Comando):
    tipo = "comprar"
    campos = {"indice": 0}

    def conferir(self, estado):
        loja = estado.run.loja_atual
        if loja is None:
            return "Não há loja aqui."
        if not isinstance(self.indice, int) or not 0 <= self.indice < len(loja.ofertas):
            return "Essa oferta não existe."
        return None

    def executar(self, estado):
        loja, jogador = estado.run.loja_atual, estado.grupo.jogador(self.jogador)
        oferta = loja.ofertas[self.indice]
        cheia = jogador is not None and not jogador.mochila.cabe(oferta.chave) and oferta.tipo != "receita"
        if loja.comprar(self.indice, estado.run, jogador):
            return Resultado(True, f"Comprou {oferta.nome()}." + (" (Mochila cheia: foi para o baú.)" if cheia else ""))
        return Resultado(False, "Esgotado." if oferta.esgotada() else "Ouro insuficiente.")


class Vender(Comando):
    tipo = "vender"
    campos = {"origem": BAU, "chave": "", "quantidade": 1}

    def conferir(self, estado):
        return conferir_inventario(estado, self.origem)

    def executar(self, estado):
        from roguelike.loja import Loja
        ganho = Loja.vender(estado.inventario(self.origem), self.chave, estado.run, self.quantidade,
                            estado.grupo.jogador(self.jogador))
        return Resultado(ganho > 0, f"Vendeu {item(self.chave).nome} por {ganho} de ouro." if ganho else
                         "Não deu para vender.", ganho)


class EnviarOuro(Comando):
    """Quem manda passa 'quantidade' do próprio ouro para o jogador 'para' (id)."""
    tipo = "enviar_ouro"
    campos = {"para": "", "quantidade": 0}
    CAMPOS_QUE_NAO_SAO_HEROI = ("para",)

    def conferir(self, estado):
        de, para = estado.grupo.jogador(self.jogador), estado.grupo.jogador(self.para)
        if de is None or para is None or de == para:
            return "Esse jogador não está na partida."
        if not isinstance(self.quantidade, int) or self.quantidade <= 0:
            return "Quantia inválida."
        if de.ouro < self.quantidade:
            return "Ouro insuficiente."
        return None

    def executar(self, estado):
        para = estado.grupo.jogador(self.para)
        estado.grupo.enviar_ouro(estado.grupo.jogador(self.jogador), para, self.quantidade)
        return Resultado(True, f"Mandou {self.quantidade} de ouro para {para.nome}.")


# ============================================================
# NO GRUPO (itens, pontos e golpes)
# ============================================================

class Equipar(Comando):
    """Equipa uma peça (ou aponta o consumível de uso automático) no herói, vinda de 'origem'."""
    tipo = "equipar"
    campos = {"heroi": 0, "chave": "", "origem": BAU, "espaco": None}

    def conferir(self, estado):
        return conferir_inventario(estado, self.origem)

    def executar(self, estado):
        heroi, objeto = estado.heroi(self.heroi), item(self.chave)
        if objeto.tipo == "equipamento":
            motivo = heroi.equipamentos.motivo_para_nao_equipar(objeto, self.espaco)
            if motivo:
                return Resultado(False, motivo)
        if not estado.grupo.equipar(heroi, self.chave, estado.inventario(self.origem), self.espaco):
            return Resultado(False, "Não dá para equipar isso.")
        if objeto.tipo == "consumivel":
            return Resultado(True, f"{objeto.nome}: uso automático no começo do combate.")
        return Resultado(True, f"{heroi.nome} equipou {objeto.nome}.")


class Desequipar(Comando):
    tipo = "desequipar"
    campos = {"heroi": 0, "espaco": ""}

    def executar(self, estado):
        heroi = estado.heroi(self.heroi)
        if self.espaco in heroi.equipamentos.travados:
            return Resultado(False, "Amaldiçoado: preso até a próxima fogueira.")
        peca = heroi.equipamento.get(self.espaco)
        cheia = peca is not None and not heroi.inventario.cabe(peca.chave)
        if peca is None or not estado.grupo.desequipar(heroi, self.espaco):
            return Resultado(False, "Nada para tirar.")
        return Resultado(True, f"{peca.nome} foi para o baú (mochila cheia)." if cheia else f"{peca.nome} foi para a mochila.")


class MoverItem(Comando):
    """Entre o baú ("bau") e as mochilas (número do herói): o herói coloca, retira ou passa (pelo baú)."""
    tipo = "mover_item"
    campos = {"chave": "", "de": BAU, "para": BAU, "quantidade": 1}

    def conferir(self, estado):
        if self.de == self.para or estado.inventario(self.de) is estado.inventario(self.para):
            return "Já está aí (os heróis de um jogador dividem a mesma mochila)."
        return conferir_inventario(estado, self.de) or conferir_inventario(estado, self.para)

    def executar(self, estado):
        grupo, nome = estado.grupo, item(self.chave).nome
        de, para = estado.heroi(self.de), estado.heroi(self.para)
        if self.de == BAU:
            ok = grupo.pegar_do_bau(para, self.chave, self.quantidade)
            return Resultado(ok, f"{para.nome} pegou {nome} do baú." if ok else f"A mochila de {para.nome} está cheia.")
        if self.para == BAU:
            ok = grupo.colocar_no_bau(de, self.chave, self.quantidade)
            return Resultado(ok, f"{de.nome} guardou {nome} no baú." if ok else "Não deu.")
        ok = grupo.passar(de, para, self.chave, self.quantidade)
        return Resultado(ok, f"{de.nome} deu {nome} para {para.nome} (pelo baú)." if ok else
                         f"A mochila de {para.nome} está cheia.")


class Descartar(Comando):
    tipo = "descartar"
    campos = {"origem": BAU, "chave": "", "quantidade": 1}

    def conferir(self, estado):
        return conferir_inventario(estado, self.origem)

    def executar(self, estado):
        ok = estado.inventario(self.origem).remover(self.chave, self.quantidade)
        return Resultado(ok, f"{item(self.chave).nome} foi descartado." if ok else "Não há esse item aí.")


class UsarItem(Comando):
    """Consumível fora do combate (poção, comida, tomo, Mapa Rasgado...) no herói, vindo de 'origem'."""
    tipo = "usar_item"
    campos = {"heroi": 0, "chave": "", "origem": BAU}

    def conferir(self, estado):
        return conferir_inventario(estado, self.origem)

    def executar(self, estado):
        heroi, objeto = estado.heroi(self.heroi), item(self.chave)
        usou = estado.run.usar_fora_do_combate(self.chave, estado.inventario(self.origem), heroi)
        return Resultado(usou, f"{heroi.nome} usou {objeto.nome}." if usou else "Não teve efeito agora.")


class Fabricar(Comando):
    """Fabrica a receita gastando da mochila do herói e depois do baú (sem herói: só o baú)."""
    tipo = "fabricar"
    campos = {"receita": "", "heroi": None}

    def executar(self, estado):
        ok = estado.run.fabricar(self.receita, estado.heroi(self.heroi))
        return Resultado(ok, "Fabricado!" if ok else "Faltam ingredientes.")


class DistribuirPonto(Comando):
    tipo = "distribuir_ponto"
    campos = {"heroi": 0, "atributo": ""}
    precisa_de_run = False

    def executar(self, estado):
        return Resultado(estado.heroi(self.heroi).distribuir_ponto(self.atributo))


class MelhorarHabilidade(Comando):
    tipo = "melhorar_habilidade"
    campos = {"heroi": 0, "chave": ""}
    precisa_de_run = False

    def executar(self, estado):
        return Resultado(estado.heroi(self.heroi).melhorar_habilidade(self.chave))


class DecidirGolpeNovo(Comando):
    """Golpe novo com os espaços cheios: troca pelo 'esquecido' (vai ao grimório) ou, sem ele, guarda o novo."""
    tipo = "decidir_golpe_novo"
    campos = {"heroi": 0, "novo": "", "esquecido": None}
    precisa_de_run = False

    def executar(self, estado):
        return Resultado(estado.heroi(self.heroi).golpes.decidir(self.novo, self.esquecido))


class TrocarGolpe(Comando):
    """Equipa um golpe do grimório (no lugar de 'equipado', se os espaços estiverem cheios)."""
    tipo = "trocar_golpe"
    campos = {"heroi": 0, "chave": "", "equipado": None}
    precisa_de_run = False

    def executar(self, estado):
        return Resultado(estado.heroi(self.heroi).golpes.trocar(self.chave, self.equipado))


class GuardarGolpe(Comando):
    tipo = "guardar_golpe"
    campos = {"heroi": 0, "chave": ""}
    precisa_de_run = False

    def executar(self, estado):
        ok = estado.heroi(self.heroi).golpes.guardar(self.chave)
        return Resultado(ok, "" if ok else "Precisa ficar pelo menos um golpe equipado.")


# ============================================================
# NO COMBATE
# ============================================================

class ComecarCombate(Comando):
    """Monta o combate do encontro da run (ou de 'encontro', um encontro em dicionário: combate de teste)."""
    tipo = "comecar_combate"
    campos = {"encontro": None}

    def encontro_do_combate(self, estado):
        from roguelike.encontros import encontro_de_dict
        return encontro_de_dict(self.encontro) if self.encontro else estado.run.encontro

    def conferir(self, estado):
        encontro = self.encontro_do_combate(estado)
        return None if encontro is not None and encontro.eh_combate() else "Este encontro não é um combate."

    def executar(self, estado):
        return Resultado(True, valor=estado.comecar_combate(self.encontro_do_combate(estado)))


ACOES_DE_COMBATE = ("golpe", "item", "concentrar")


class AgirNoCombate(Comando):
    """A ação do herói da vez: um golpe (chave), um item (chave) ou concentrar. alvo = ["herois"|"inimigos", n]."""
    tipo = "agir_no_combate"
    campos = {"heroi": 0, "acao": "golpe", "chave": None, "alvo": None}

    def conferir(self, estado):
        condutor = estado.condutor
        if condutor is None or not condutor.esperando():
            return "Não é hora de agir."
        if condutor.heroi_da_vez() is not estado.heroi(self.heroi):
            return "Não é a vez desse herói."
        if self.acao not in ACOES_DE_COMBATE:
            return "Ação desconhecida."
        if self.acao == "item" and not getattr(item(self.chave), "usavel_em_combate", False):
            return "Esse item não se usa no combate."
        return None

    def executar(self, estado):
        heroi, combate, alvo = estado.heroi(self.heroi), estado.combate, estado.lutador(self.alvo)
        if self.acao == "concentrar":
            ok = combate.concentrar(heroi)
        elif self.acao == "item":
            ok = heroi.inventario.tem(self.chave) and combate.usar_item(heroi, item(self.chave), alvo)
            if ok:
                heroi.inventario.remover(self.chave)
        else:
            ok = combate.usar_habilidade(heroi, self.chave, alvo)
        return Resultado(ok, "" if ok else "Não dá para fazer isso agora.")


COMANDOS = {classe.tipo: classe for classe in (
    EscolherEncontro, IniciarFuga, Prosseguir, ConcluirEncontro, ResolverEvento, ContinuarOndas, EncerrarOndas, DescansoMaior,
    Treinar, Reviver, Comprar, Vender, EnviarOuro, Equipar, Desequipar, MoverItem, Descartar, UsarItem, Fabricar,
    DistribuirPonto, MelhorarHabilidade, DecidirGolpeNovo, TrocarGolpe, GuardarGolpe, ComecarCombate, AgirNoCombate)}


def criar_comando(dados):
    """O contrário de para_dict(): {"tipo": "comprar", "jogador": "local", "indice": 2} -> Comprar(indice=2)."""
    dados = dict(dados)
    classe = COMANDOS[dados.pop("tipo")]
    return classe(jogador=dados.pop("jogador", JOGADOR_LOCAL), **dados)
