"""Eventos de escolha (eventos.json): um texto e 2 a 4 opções com consequências.

Cada tipo de consequência ("ouro", "item", "combate"...) é uma subclasse
de Consequencia. Para criar um evento novo, basta escrever no JSON.

Os itens de um evento ("item", "item_aleatorio", "premio") vão para CADA jogador, cada um com o seu sorteio
(roguelike/gerador_de_loot.py): ninguém tira o prêmio de ninguém.
"""

import random

from roguelike.dados import carregar, sem_comentarios, regras
from roguelike.itens import todos_os_itens, item


class ResultadoEvento:
    def __init__(self):
        self.textos = []           # o que aconteceu (para a tela)
        self.combate = None        # EncontroCombate, se a opção levou a uma luta
        self.por_jogador = {}      # id do jogador -> {chave: quantidade} (os itens que cada um ganhou)
        self.no_bau = {}           # id do jogador -> {chave: quantidade} (o que não coube na mochila e foi ao baú)
        self.texto_dos_itens = None   # posição em 'textos' da frase "Recebeu: ..." (uma só, com tudo)

    def escrever(self, texto):
        if texto:
            self.textos.append(texto)


def entregar(run, resultado, por_jogador):
    """Dá os itens a cada jogador ({id: {chave: quantidade}}) e anota no resultado. O que cada um ganhou no evento
    inteiro fica numa frase só ("Recebeu: ..."), no lugar da primeira entrega. Mochila cheia: o resto vai ao baú."""
    from roguelike.loot import juntar
    recebidos, no_bau = run.guardar_loot(por_jogador)
    for jogador, itens in recebidos.items():
        resultado.por_jogador[jogador] = juntar(resultado.por_jogador.get(jogador, {}), itens)
    for jogador, itens in no_bau.items():
        resultado.no_bau[jogador] = juntar(resultado.no_bau.get(jogador, {}), itens)
    texto = texto_dos_itens(run, resultado.por_jogador)
    if not texto:
        return
    if resultado.no_bau:
        texto += " (Mochila cheia: o que não coube foi para o baú.)"
    if resultado.texto_dos_itens is None:
        resultado.texto_dos_itens = len(resultado.textos)
        resultado.textos.append(texto)
    else:
        resultado.textos[resultado.texto_dos_itens] = texto


def nome_no_texto(chave, quantidade):
    """"Osso x2", "Espada de Prata (Raro)": a raridade aparece nas peças e no que não é comum."""
    objeto = item(chave)
    nome = objeto.nome + (f" x{quantidade}" if quantidade > 1 else "")
    if objeto.tipo == "equipamento" or objeto.raridade != "comum":
        nome += f" ({objeto.nome_da_raridade()})"
    return nome


def texto_dos_itens(run, por_jogador):
    """"Recebeu: Osso x2, Espada de Prata (Raro)." (no multiplayer, uma frase por jogador: "Bia recebeu: ...")."""
    frases = []
    for jogador, itens in por_jogador.items():
        if not itens:
            continue
        lista = ", ".join(nome_no_texto(c, n) for c, n in itens.items())
        if len(por_jogador) == 1:
            frases.append(f"Recebeu: {lista}.")
        else:
            nome = run.grupo.jogador(jogador).nome if run.grupo.jogador(jogador) else jogador
            frases.append(f"{nome} recebeu: {lista}.")
    return " ".join(frases)


def para_cada_jogador(run, rng):
    """[(jogador, sorteio próprio)]: um sorteio por jogador, tirado do sorteio do evento (o mesmo em todo lugar)."""
    base = rng.randint(0, 2 ** 32 - 1)
    grupo = run.grupo
    return [(j, random.Random(f"{base}|{j.id}")) for j in grupo.jogadores if grupo.herois_de(j)]


# ============================================================
# CONSEQUÊNCIAS
# ============================================================

class Consequencia:
    def __init__(self, dados):
        self.dados = dict(dados)

    def aplicar(self, run, rng, resultado):
        raise NotImplementedError


class GanharOuro(Consequencia):
    def aplicar(self, run, rng, resultado):
        valor = self.dados["valor"]
        run.grupo.ouro = max(0, run.grupo.ouro + valor)
        resultado.escrever(f"{'+' if valor >= 0 else ''}{valor} de ouro.")


class GanharItem(Consequencia):
    """Cada jogador recebe o item (na quantidade pedida)."""

    def aplicar(self, run, rng, resultado):
        quantidade = self.dados.get("quantidade", 1)
        entregar(run, resultado, {j.id: {self.dados["chave"]: quantidade} for j, _ in para_cada_jogador(run, rng)})


class PerderItem(Consequencia):
    def aplicar(self, run, rng, resultado):
        for _ in range(self.dados.get("quantidade", 1)):
            run.gastar_item(self.dados["chave"])


class ItemAleatorio(Consequencia):
    """Cada jogador sorteia o seu item da raridade (e do tipo) pedidos."""

    def aplicar(self, run, rng, resultado):
        possiveis = [i for i in todos_os_itens().values()
                     if i.raridade == self.dados.get("raridade", "comum") and i.categoria != "alma"
                     and (not self.dados.get("item_tipo") or i.tipo == self.dados["item_tipo"])]
        if not possiveis:
            return
        por_jogador = {}
        for jogador, sorteio in para_cada_jogador(run, rng):
            itens = por_jogador.setdefault(jogador.id, {})
            for _ in range(self.dados.get("quantidade", 1)):
                escolhido = sorteio.choice(possiveis).chave
                itens[escolhido] = itens.get(escolhido, 0) + 1
        entregar(run, resultado, por_jogador)


class Premio(Consequencia):
    """Um prêmio de evento do tamanho de uma luta, separado por jogador (GeradorDeLoot.de_evento):
    por_jogador + por_heroi x heróis prêmios da bolsa da fase (+ "itens": linhas a mais), chance_de_equipamento
    (nunca abaixo de raridade_minima) e chance_de_lendario (uma peça lendária a mais)."""

    def aplicar(self, run, rng, resultado):
        from roguelike.gerador_de_loot import GeradorDeLoot
        entregar(run, resultado, GeradorDeLoot(run).de_evento(self.dados, rng))


class CurarGrupo(Consequencia):
    def aplicar(self, run, rng, resultado):
        run.grupo.descansar(self.dados["percentual"])
        resultado.escrever(f"O grupo recuperou {int(self.dados['percentual'] * 100)}% da vida.")


class DanoNoGrupo(Consequencia):
    """Tira uma porcentagem da vida máxima, mas nunca mata (deixa com 1)."""

    def alvos(self, run, rng):
        return run.grupo.vivos()

    def aplicar(self, run, rng, resultado):
        for heroi in self.alvos(run, rng):
            perda = max(1, int(heroi.vida_maxima * self.dados["percentual"]))
            heroi.vida = max(1, heroi.vida - perda)
            resultado.escrever(f"{heroi.nome} perdeu {perda} de vida.")


class DanoEmUm(DanoNoGrupo):
    def alvos(self, run, rng):
        vivos = run.grupo.vivos()
        return [rng.choice(vivos)] if vivos else []


class GanharXP(Consequencia):
    def aplicar(self, run, rng, resultado):
        for heroi in run.grupo.vivos():
            if heroi.ganhar_xp(self.dados["valor"]):
                resultado.escrever(f"{heroi.nome} subiu para o nível {heroi.nivel}!")
        resultado.escrever(f"+{self.dados['valor']} de experiência para o grupo.")


class PontosDeAtributo(Consequencia):
    def aplicar(self, run, rng, resultado):
        vivos = run.grupo.vivos()
        if vivos:
            heroi = rng.choice(vivos)
            heroi.pontos_atributo += self.dados.get("quantidade", 1)
            resultado.escrever(f"{heroi.nome} ganhou {self.dados.get('quantidade', 1)} pontos de atributo.")


class ProximoCombate(Consequencia):
    """Um status que vai valer no começo do próximo combate (bênção ou maldição)."""

    def aplicar(self, run, rng, resultado):
        run.efeitos_proximo_combate.append(dict(self.dados))
        from roguelike.status import dados_do_status
        quem = "o grupo" if self.dados.get("lado", "herois") == "herois" else "os inimigos"
        resultado.escrever(f"No próximo combate, {quem}: {dados_do_status(self.dados['status'])['nome']}.")


class Recrutar(Consequencia):
    def aplicar(self, run, rng, resultado):
        heroi = run.recrutar(rng)
        if heroi is not None:
            resultado.escrever(f"{heroi.nome} ({heroi.classe.nome}, nível {heroi.nivel}) entrou no grupo!")


class IniciarCombate(Consequencia):
    def aplicar(self, run, rng, resultado):
        from roguelike.encontros import combate_de_evento
        resultado.combate = combate_de_evento(run, rng, self.dados)


class ComecarOndas(IniciarCombate):
    """Combate em ondas (roguelike/ondas.py): a primeira onda começa já; as outras, se o grupo quiser continuar."""

    def aplicar(self, run, rng, resultado):
        from roguelike.ondas import CombateEmOndas
        run.ondas = CombateEmOndas.sortear(self.dados, rng)
        resultado.combate = run.ondas.encontro()


class RevelarReceita(Consequencia):
    def aplicar(self, run, rng, resultado):
        from roguelike.fabricacao import todas_as_receitas
        escondidas = [r for r in todas_as_receitas().values() if r.escondida and r.chave not in run.descobertas
                      and item(r.resultado).raridade != "lendario"]
        if escondidas:
            receita = rng.choice(escondidas)
            run.descobertas.add(receita.chave)
            resultado.escrever(f"Receita descoberta: {receita.nome()}.")


class ReviverTodos(Consequencia):
    def aplicar(self, run, rng, resultado):
        for heroi in run.grupo.caidos():
            run.grupo.reviver(heroi, self.dados.get("percentual", 0.3))
            resultado.escrever(f"{heroi.nome} voltou à vida!")


class AvancarSegredo(Consequencia):
    """Um passo a mais num segredo que atravessa as runs (ex.: seguir o Rato Branco). Fica no progresso."""

    def aplicar(self, run, rng, resultado):
        chave = self.dados["chave"]
        run.segredos[chave] = run.segredos.get(chave, 0) + 1
        resultado.escrever(self.dados.get("texto", ""))


class PegarPeste(Consequencia):
    """Cada herói vivo tem "chance" de pegar "niveis" de Peste (segue entre as lutas: heroi.peste). As raças
    contam como no combate ("resiste_peste": chance de escapar; negativo: chance de 1 nível a mais)."""

    def aplicar(self, run, rng, resultado):
        maximo = regras()["status"]["peste"].get("maximo", 5)
        for heroi in run.grupo.vivos():
            if rng.random() >= self.dados.get("chance", 1.0):
                continue
            resistencia = heroi.bonus("resiste_peste")
            if resistencia > 0 and rng.random() < resistencia:
                resultado.escrever(f"{heroi.nome} resistiu à Peste.")
                continue
            niveis = self.dados.get("niveis", 1) + (1 if resistencia < 0 and rng.random() < -resistencia else 0)
            heroi.peste = min(maximo, heroi.peste + niveis)
            resultado.escrever(f"{heroi.nome} pegou a Peste (nível {heroi.peste}).")
            run.vigiar_desafio({"peste"})                     # o Reino sem Peste (conquista "Imune") já era


class ReforcosNoProximoCombate(Consequencia):
    """Inimigos a mais que entram no próximo combate (ex.: os Guardas Reais atrás de quem roubou o Mercado)."""

    def aplicar(self, run, rng, resultado):
        run.inimigos_extra_proximo_combate += list(self.dados["inimigos"])
        resultado.escrever(self.dados.get("texto", ""))


class TrocarConsumivel(Consequencia):
    """Entrega um consumível qualquer do grupo (sorteado) e recebe um item aleatório (como "item_aleatorio")."""

    def aplicar(self, run, rng, resultado):
        consumiveis = sorted({c for c in run.todas_as_chaves() if item(c).tipo == "consumivel"})
        if not consumiveis:
            return
        entregue = rng.choice(consumiveis)
        run.gastar_item(entregue)
        resultado.escrever(f"Entregou {item(entregue).nome}.")
        ItemAleatorio(self.dados).aplicar(run, rng, resultado)


class AteOChefe(Consequencia):
    """Status que o grupo recebe no começo de cada combate até vencer o chefe da fase (ex.: Bênção do Queijo)."""

    def aplicar(self, run, rng, resultado):
        run.efeitos_ate_o_chefe += [dict(s) for s in self.dados["status"]]
        resultado.escrever(self.dados.get("texto", ""))


class AjusteDoChefe(Consequencia):
    """Muda o chefe da fase quando ele aparecer (ex.: sem o queijo do altar, o Rei começa mais fraco e mais furioso)."""

    def aplicar(self, run, rng, resultado):
        for chave, valor in self.dados["modificadores"].items():
            run.ajustes_do_chefe[chave] = run.ajustes_do_chefe.get(chave, 0) + valor
        resultado.escrever(self.dados.get("texto", ""))


class Sorte(Consequencia):
    """Chance de dar certo; cada lado tem a sua lista de consequências."""

    def deu_certo(self, run, rng):
        return rng.random() < self.dados.get("chance", 0.5)

    def aplicar(self, run, rng, resultado):
        sucesso = self.deu_certo(run, rng)
        resultado.escrever(self.dados.get("texto_sucesso" if sucesso else "texto_falha", ""))
        for dados in self.dados.get("sucesso" if sucesso else "falha", []):
            criar_consequencia(dados).aplicar(run, rng, resultado)


class Teste(Sorte):
    """Teste de atributo: o maior valor do grupo + 1d10 contra a dificuldade."""

    def deu_certo(self, run, rng):
        atributo = self.dados["atributo"]
        melhor = max((h.atributo(atributo) for h in run.grupo.vivos()), default=0)
        return melhor + rng.randint(1, 10) >= self.dados["dificuldade"]


TIPOS_DE_CONSEQUENCIA = {
    "ouro": GanharOuro, "item": GanharItem, "perder_item": PerderItem, "item_aleatorio": ItemAleatorio, "premio": Premio,
    "curar_grupo": CurarGrupo, "dano_grupo": DanoNoGrupo, "dano_aleatorio": DanoEmUm, "xp": GanharXP,
    "pontos_atributo": PontosDeAtributo, "proximo_combate": ProximoCombate, "recrutar": Recrutar,
    "combate": IniciarCombate, "revelar_receita": RevelarReceita, "reviver_todos": ReviverTodos,
    "sorte": Sorte, "teste": Teste, "segredo": AvancarSegredo,
    "peste": PegarPeste, "reforcos_proximo_combate": ReforcosNoProximoCombate, "trocar_consumivel": TrocarConsumivel,
    "ate_o_chefe": AteOChefe, "ajuste_do_chefe": AjusteDoChefe, "ondas": ComecarOndas,
}


def criar_consequencia(dados):
    try:
        return TIPOS_DE_CONSEQUENCIA[dados["tipo"]](dados)
    except KeyError:
        raise ValueError(f"Consequência desconhecida: {dados.get('tipo')}") from None


# ============================================================
# EVENTOS E OPÇÕES
# ============================================================

class OpcaoDeEvento:
    def __init__(self, dados):
        self.texto = dados["texto"]
        self.requisito = dict(dados.get("requisito", {}))
        self.consequencias = [criar_consequencia(c) for c in dados.get("efeitos", [])]
        self.resultado = dados.get("resultado", "")

    def disponivel(self, run):
        if "ouro" in self.requisito and run.grupo.ouro < self.requisito["ouro"]:
            return False
        if "item" in self.requisito and run.quantidade_de(self.requisito["item"]) < self.requisito.get("quantidade", 1):
            return False
        if self.requisito.get("consumivel") and not any(item(c).tipo == "consumivel" for c in run.todas_as_chaves()):
            return False
        if self.requisito.get("vaga_no_grupo") and run.grupo.cheio():
            return False
        if self.requisito.get("caido") and not run.grupo.caidos():
            return False
        return True


class EventoDeRun:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.texto = dados["texto"]
        self.regioes = dados.get("regioes")          # None = qualquer região
        self.opcoes = [OpcaoDeEvento(o) for o in dados["opcoes"]]
        self.so_por_guia = dados.get("so_por_guia", False)   # só aparece pelas mãos de um guia (guias.py)
        self.sprite = dados.get("sprite")            # quem aparece no lugar do "?" (e correndo ao fundo da tela)
        self.parado = dados.get("parado", False)     # True: o sprite fica só no lugar do "?" (não corre)
        self.zonas = dados.get("zonas")              # nomes das zonas onde aparece (fases com zonas); None = todas

    def aparece_em(self, chave_regiao):
        from roguelike.regioes import mesma_etapa
        if self.so_por_guia:
            return False
        return self.regioes is None or any(mesma_etapa(chave_regiao, r) for r in self.regioes)

    def aparece_na_zona(self, zona):
        """zona = Regiao.zona(...) da área (None nas fases sem zonas)."""
        return not self.zonas or (zona is not None and zona.get("nome") in self.zonas)

    def escolher(self, indice, run, rng):
        """Aplica a opção escolhida e devolve um ResultadoEvento (ou None se não vale)."""
        if not 0 <= indice < len(self.opcoes) or not self.opcoes[indice].disponivel(run):
            return None
        opcao = self.opcoes[indice]
        resultado = ResultadoEvento()
        resultado.escrever(opcao.resultado)
        for consequencia in opcao.consequencias:
            consequencia.aplicar(run, rng, resultado)
        if not resultado.textos:
            resultado.escrever("Vocês seguem caminho.")
        return resultado


_eventos = {}


def todos_os_eventos():
    if not _eventos:
        for chave, dados in sem_comentarios(carregar("eventos")).items():
            _eventos[chave] = EventoDeRun(chave, dados)
    return _eventos


def evento(chave):
    return todos_os_eventos()[chave]


def nomes_de_herois():
    return regras()["nomes_herois"]
