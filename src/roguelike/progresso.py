"""Progressão permanente: o que fica guardado entre uma run e outra.

- Brasas: moeda permanente ganha ao avançar nas runs;
- Prestígio por classe (máx. 25): cada nível dá 3 pontos para a árvore de talentos da classe;
- Árvores de talentos (talentos.json): nós que desbloqueiam os vizinhos;
- Bênçãos (bencaos.json): até 5 espaços de modificadores de run;
- Raças (racas.json): escolhidas no Espelho para cada herói;
- Conquistas: chefes vencidos, subclasses aprendidas, almas... liberam bênçãos escondidas.

Tudo é salvo em progresso.json, na pasta do jogador (caminhos.py).
"""

import json
import os
import random

from caminhos import CAMINHOS, gravar_json
from roguelike.classes import todas_as_classes
from roguelike.dados import carregar, sem_comentarios, regras
from roguelike.golpes import golpe
from roguelike.run import Run
from versao import VERSAO

ARQUIVO_DO_PROGRESSO = "progresso.json"


# ============================================================
# DADOS: TALENTOS, BÊNÇÃOS E RAÇAS
# ============================================================

class NoDeTalento:
    def __init__(self, chave, dados):
        self.chave = chave
        self.nome = dados["nome"]
        self.posicao = tuple(dados.get("pos", (0, 0)))
        self.custo = dados.get("custo", 1)
        self.maximo = dados.get("maximo", 1)
        self.requer = list(dados.get("requer", []))
        self.efeito = dict(dados["efeito"])

    def descricao(self):
        """Texto do efeito de cada nível, ex.: "+1 FOR por nível"."""
        from roguelike.atributos import sigla
        tipo = self.efeito["tipo"]
        if tipo == "atributos":
            partes = [f"+{v} {sigla(a)}" for a, v in self.efeito["atributos"].items()]
            return ", ".join(partes) + (" por nível" if self.maximo > 1 else "")
        if tipo == "bonus":
            partes = [texto_de_modificador(c, v) for c, v in self.efeito["modificadores"].items()]
            return ", ".join(partes) + (" por nível" if self.maximo > 1 else "")
        if tipo == "nivel_habilidade":
            return f"{golpe(self.efeito['habilidade']).nome} começa 1 nível acima (por nível do talento)"
        passiva = self.efeito.get("passiva", {})
        return passiva.get("descricao") or f"Passiva: {passiva.get('nome', '')}"


def texto_de_modificador(chave, valor):
    """Ex.: ("chance_critico", 0.05) -> "+5% de crítico"."""
    from roguelike.atributos import sigla, nomes_dos_atributos
    nomes = {"chance_critico": "de crítico", "dano_critico": "de dano crítico", "chance_bloqueio": "de bloqueio",
             "reducao_bloqueio": "de força do bloqueio", "chance_esquiva": "de esquiva", "ganho_energia": "de ganho de energia",
             "cura_causada": "de cura causada", "cura_recebida": "de cura recebida", "potencia_suporte": "de força dos buffs",
             "roubo_vida": "de roubo de vida", "dano_causado": "de dano", "dano_recebido": "de dano recebido",
             "vida_percentual": "de vida máxima"}
    from roguelike.elementos import todos as elementos, nome as nome_do_elemento
    for elemento in elementos():                         # "dano_causado_fogo" -> "de dano de fogo"
        nomes[f"dano_causado_{elemento}"] = f"de dano de {nome_do_elemento(elemento)}"
        nomes[f"dano_recebido_{elemento}"] = f"de dano de {nome_do_elemento(elemento)} recebido"
    nomes.update({"furtividade": "de furtividade", "xp_ganho": "de XP", "precisao": "de precisão",
                  "dano_magico": "de dano mágico", "resistencia_magica": "de resistência mágica",
                  "resiste_peste": "de resistência à Peste", "resiste_veneno": "de resistência ao veneno",
                  "ouro_extra": "de ouro", "loot_extra": "de chance de loot",
                  "dano_vida_baixa": "de dano em quem está abaixo de 25% da vida"})
    sinal = "+" if valor >= 0 else ""
    if chave in nomes_dos_atributos():
        return f"{sinal}{valor} {sigla(chave)}"
    if chave in nomes:
        return f"{sinal}{round(valor * 100)}% {nomes[chave]}"
    legiveis = {"vida_maxima": "de vida", "defesa": "de defesa", "iniciativa": "de iniciativa", "max_invocacoes": "invocação",
                "energia_maxima": "de energia máxima", "espacos_de_golpe": "espaço de golpe",
                "duracao_bencaos": "turno nos buffs que aplica", "duracao_maldicoes": "turno nas maldições que aplica",
                "penetracao": "de defesa do alvo ignorada"}
    return f"{sinal}{valor} {legiveis.get(chave, chave)}"


def arvore_da_classe(chave_classe):
    """Dicionário chave do nó -> NoDeTalento."""
    dados = sem_comentarios(carregar("talentos")).get(chave_classe, {})
    return {chave: NoDeTalento(chave, info) for chave, info in dados.items()}


def descrever_conquista(chave):
    """Texto legível de uma conquista, ex.: "chefe:aranha_mae" -> "Vença: Mãe Aranha"."""
    from roguelike.inimigos import ficha
    from roguelike.itens import item
    tipo, _, valor = chave.partition(":")
    try:
        if tipo == "chefe":
            return f"Vença: {ficha(valor)['nome']}"
        if tipo == "derrotou":
            return f"Derrote: {ficha(valor)['nome']}"
        if tipo == "item":
            return f"Obtenha: {item(valor).nome}"
        if tipo == "subclasse":
            for classe in todas_as_classes().values():
                if valor in classe.subclasses:
                    return f"Torne-se {classe.subclasses[valor].nome}"
        if tipo == "regiao":
            from roguelike.regioes import regiao
            return f"Chegue a: {regiao(valor).nome}"
    except KeyError:
        pass
    return {"vitoria": "Vença uma run", "vitoria_solo": "Vença uma run sozinho"}.get(chave, chave)


def bencaos():
    return sem_comentarios(carregar("bencaos"))


def racas():
    return sem_comentarios(carregar("racas"))


def dados_da_taverna():
    return carregar("taverna")


# ============================================================
# PROGRESSO
# ============================================================

class RelatorioDeFim:
    """O que a run trouxe para o progresso permanente (tela de fim de run)."""

    def __init__(self):
        self.brasas = 0
        self.prestigio = {}           # classe -> (xp ganho, níveis subidos)
        self.conquistas_novas = []
        self.subclasses_novas = []
        self.conquistas_feitas = []    # Conquista (conquistas.json) concluídas no fim da run
        self.itens_guardados = []      # chaves das peças que foram para o arsenal (vitória ou fuga)
        self.herois_novos = []         # classes secretas liberadas que o acampamento vai anunciar


class Progresso:
    def __init__(self):
        self.brasas = 0
        self.prestigio = {}                 # classe -> {"nivel": 0, "xp": 0}
        self.talentos = {}                  # classe -> {nó: níveis comprados}
        self.bencaos_compradas = []
        self.bencaos_equipadas = []
        self.racas_compradas = ["humano"]
        self.conquistas = set()
        self.subclasses_liberadas = set()
        self.estatisticas = {"runs": 0, "vitorias": 0, "melhor_areas": 0, "brasas_totais": 0, "inimigos": 0}
        self.abates = {}                    # inimigo -> quantos já foram derrotados (todas as runs)
        self.conquistas_feitas = set()      # conquistas.json já concluídas (liberam skins)
        self.visuais = {}                   # classe -> {"roupa": skin, "chapeu": skin, "arma": skin}
        self.golpes_descobertos = set()     # golpes que algum herói já teve numa run (Mestre do Grimório)
        self.provisoes = {}                 # item -> quantidade comprada no Taverneiro para a próxima run
        self.skins_compradas = set()        # skins raras compradas na vitrine do Taverneiro
        self.segredos = {}                  # passos de segredos entre runs (ex.: vezes que seguiu o Rato Branco)
        self.herois_anunciados = set()      # classes secretas que o acampamento já anunciou (tela de herói novo)
        self.expedicao = None               # grupo sendo montado no acampamento (roguelike/expedicao.py)
        from roguelike.arsenal import Arsenal
        self.arsenal = Arsenal()            # equipamentos guardados entre runs (estande de armas)
        self.caminho = CAMINHOS.save(ARQUIVO_DO_PROGRESSO)      # onde este progresso é salvo

    # ============================================================
    # CLASSES SECRETAS
    # ============================================================

    def classes_liberadas(self):
        """chave -> classe que o jogador já pode usar (as secretas pedem a conquista de "requer")."""
        from roguelike.classes import classes_liberadas
        return classes_liberadas(self.conquistas)

    def herois_para_anunciar(self):
        """Classes secretas liberadas que o acampamento ainda não anunciou (na ordem do JSON)."""
        return [c for c, classe in self.classes_liberadas().items() if classe.requer and c not in self.herois_anunciados]

    def anunciar_heroi(self, chave):
        self.herois_anunciados.add(chave)

    def pets_liberados(self):
        """Bichos que já ficam no acampamento (regras.json "pets"; ex.: o Rato Branco depois de vencer o Reino)."""
        return [chave for chave, pet in regras().get("pets", {}).items() if pet.get("requer") in self.conquistas]

    # ============================================================
    # PRESTÍGIO
    # ============================================================

    def _prestigio(self, classe):
        return self.prestigio.setdefault(classe, {"nivel": 0, "xp": 0})

    def nivel_de_prestigio(self, classe):
        return self._prestigio(classe)["nivel"]

    def xp_de_prestigio(self, classe):
        return self._prestigio(classe)["xp"]

    def xp_para_proximo_prestigio(self, classe):
        regra = regras()["progresso"]
        return regra["prestigio_base"] + regra["prestigio_por_nivel"] * self.nivel_de_prestigio(classe)

    def ganhar_prestigio(self, classe, xp):
        """Soma XP de prestígio. Devolve quantos níveis a classe subiu."""
        dados = self._prestigio(classe)
        maximo = regras()["progresso"]["prestigio_maximo"]
        dados["xp"] += xp
        subiu = 0
        while dados["nivel"] < maximo and dados["xp"] >= self.xp_para_proximo_prestigio(classe):
            dados["xp"] -= self.xp_para_proximo_prestigio(classe)
            dados["nivel"] += 1
            subiu += 1
        if dados["nivel"] >= maximo:
            dados["xp"] = 0
        return subiu

    # ============================================================
    # TALENTOS
    # ============================================================

    def niveis_do_no(self, classe, no):
        return self.talentos.get(classe, {}).get(no, 0)

    def pontos_totais(self, classe):
        return self.nivel_de_prestigio(classe) * regras()["progresso"]["pontos_por_prestigio"]

    def pontos_gastos(self, classe):
        arvore = arvore_da_classe(classe)
        return sum(arvore[no].custo * n for no, n in self.talentos.get(classe, {}).items() if no in arvore)

    def pontos_livres(self, classe):
        return self.pontos_totais(classe) - self.pontos_gastos(classe)

    def no_liberado(self, classe, no):
        """Um nó fica liberado quando algum nó de "requer" já tem ponto (a raiz sempre está)."""
        requer = arvore_da_classe(classe)[no].requer
        return not requer or any(self.niveis_do_no(classe, r) > 0 for r in requer)

    def pode_comprar_talento(self, classe, no):
        arvore = arvore_da_classe(classe)
        if no not in arvore:
            return False
        no_talento = arvore[no]
        return (self.niveis_do_no(classe, no) < no_talento.maximo and self.no_liberado(classe, no)
                and self.pontos_livres(classe) >= no_talento.custo)

    def comprar_talento(self, classe, no):
        if not self.pode_comprar_talento(classe, no):
            return False
        nos = self.talentos.setdefault(classe, {})
        nos[no] = nos.get(no, 0) + 1
        return True

    def reiniciar_arvore(self, classe):
        """Devolve todos os pontos da árvore (custa Brasas)."""
        preco = regras()["progresso"]["preco_reiniciar_arvore"]
        if not self.talentos.get(classe) or self.brasas < preco:
            return False
        self.brasas -= preco
        self.talentos[classe] = {}
        return True

    # ============================================================
    # BÊNÇÃOS
    # ============================================================

    def bencao_visivel(self, chave):
        dados = bencaos()[chave]
        return not dados.get("escondida") or dados.get("conquista") in self.conquistas

    def pode_comprar_bencao(self, chave):
        return (self.bencao_visivel(chave) and chave not in self.bencaos_compradas
                and self.brasas >= bencaos()[chave]["preco"])

    def comprar_bencao(self, chave):
        if not self.pode_comprar_bencao(chave):
            return False
        self.brasas -= bencaos()[chave]["preco"]
        self.bencaos_compradas.append(chave)
        return True

    def espacos_usados(self):
        return sum(bencaos()[c]["espacos"] for c in self.bencaos_equipadas)

    def espacos_livres(self):
        return regras()["progresso"]["espacos_de_bencao"] - self.espacos_usados()

    def equipar_bencao(self, chave):
        if (chave not in self.bencaos_compradas or chave in self.bencaos_equipadas
                or bencaos()[chave]["espacos"] > self.espacos_livres()):
            return False
        self.bencaos_equipadas.append(chave)
        return True

    def desequipar_bencao(self, chave):
        if chave not in self.bencaos_equipadas:
            return False
        self.bencaos_equipadas.remove(chave)
        return True

    # ============================================================
    # RAÇAS
    # ============================================================

    def raca_visivel(self, chave):
        conquista = racas()[chave].get("conquista")
        return conquista is None or conquista in self.conquistas

    def tem_raca(self, chave):
        return chave in self.racas_compradas

    def comprar_raca(self, chave):
        dados = racas()[chave]
        if self.tem_raca(chave) or not self.raca_visivel(chave) or self.brasas < dados["preco"]:
            return False
        self.brasas -= dados["preco"]
        self.racas_compradas.append(chave)
        return True

    # ============================================================
    # COMEÇO DA RUN
    # ============================================================

    def especiais_equipados(self):
        return {bencaos()[c].get("especial") for c in self.bencaos_equipadas} - {None}

    # ============================================================
    # ABATES, CONQUISTAS E SKINS
    # ============================================================

    def registrar_combate(self, run, abates):
        """Soma os abates de um combate e os marcos da run. Devolve as conquistas concluídas agora."""
        for chave in abates:
            self.abates[chave] = self.abates.get(chave, 0) + 1
        self.descobrir_golpes(run.grupo.herois)
        from roguelike.regioes import fases_iniciais
        self.conquistas |= {m for m in run.marcos() if m not in {f"regiao:{f}" for f in fases_iniciais()}}
        return self.verificar_conquistas()

    def verificar_conquistas(self):
        """Conclui as conquistas que já bateram a meta (e libera as skins delas)."""
        from roguelike.conquistas import todas_as_conquistas
        novas = [c for c in todas_as_conquistas().values()
                 if c.chave not in self.conquistas_feitas and c.concluida(self)]
        self.conquistas_feitas |= {c.chave for c in novas}
        return novas

    def skin_liberada(self, chave):
        """Skins de conquista: a conquista feita. Skins raras (com preço): compradas no Taverneiro."""
        from roguelike.conquistas import conquista_da_skin
        from roguelike.skins import skin
        if skin(chave).preco:
            return chave in self.skins_compradas
        conquista = conquista_da_skin(chave)
        return conquista is None or conquista.chave in self.conquistas_feitas

    # ============================================================
    # TAVERNEIRO: VITRINE DE SKINS RARAS, PROVISÕES E BOATOS
    # ============================================================

    def sorteio_da_semana(self, proposito):
        """Sorteio que muda a cada run terminada (vitrine e boatos do Taverneiro)."""
        return random.Random(f"{proposito}|{self.estatisticas['runs']}")

    def vitrine(self):
        """As skins raras à venda agora (mudam depois de cada run)."""
        from roguelike.skins import skins_a_venda
        a_venda = [s.chave for s in skins_a_venda()]
        quantidade = min(len(a_venda), dados_da_taverna()["vitrine"]["quantidade"])
        return self.sorteio_da_semana("vitrine").sample(a_venda, quantidade)

    def comprar_skin(self, chave):
        from roguelike.skins import skin
        preco = skin(chave).preco
        if chave not in self.vitrine() or chave in self.skins_compradas or self.brasas < preco:
            return False
        self.brasas -= preco
        self.skins_compradas.add(chave)
        return True

    def boatos(self):
        """Os boatos que o Taverneiro conta nesta visita (mudam depois de cada run)."""
        todos = dados_da_taverna()["boatos"]
        return self.sorteio_da_semana("boatos").sample(todos, min(3, len(todos)))

    def total_de_provisoes(self, loja=None):
        """Provisões guardadas (de uma loja da taverna só, se "loja" vier: "provisoes" ou "mascarado")."""
        if loja is None:
            return sum(self.provisoes.values())
        itens = dados_da_taverna()[loja]["itens"]
        return sum(q for c, q in self.provisoes.items() if c in itens)

    def loja_liberada(self, loja):
        """A loja da taverna está aberta? (a do Mercador Mascarado só depois de vencê-lo)"""
        regra = dados_da_taverna().get(loja)
        return regra is not None and (not regra.get("liberada_por") or regra["liberada_por"] in self.conquistas)

    def comprar_provisao(self, chave, loja="provisoes"):
        if not self.loja_liberada(loja):
            return False
        regra = dados_da_taverna()[loja]
        preco = regra["itens"].get(chave)
        if preco is None or self.brasas < preco or self.total_de_provisoes(loja) >= regra["maximo"]:
            return False
        self.brasas -= preco
        self.provisoes[chave] = self.provisoes.get(chave, 0) + 1
        return True

    def entregar_provisoes(self, run):
        """No começo da run, as provisões vão para a mochila de quem as comprou (o jogador deste progresso: no solo, o
        único; o que não couber vai para o baú)."""
        if self.provisoes:
            run.receber_itens(dict(self.provisoes), run.grupo.jogadores[0].mochila)
            run.estatisticas["itens_obtidos"] -= self.total_de_provisoes()      # não contam como loot
        self.provisoes = {}

    # ============================================================
    # GOLPES DESCOBERTOS E GOLPES RAROS
    # ============================================================

    def descobrir_golpes(self, herois):
        """Tudo o que os heróis sabem entra no catálogo do Mestre do Grimório."""
        novos = set()
        for heroi in herois:
            novos |= set(heroi.niveis_habilidade) - self.golpes_descobertos
        self.golpes_descobertos |= novos
        return novos

    def golpe_descoberto(self, chave):
        return chave in self.golpes_descobertos

    def golpes_raros_liberados(self, chave_classe):
        """Golpes raros que heróis desta classe podem aprender na run (conquista já feita)."""
        from roguelike.conquistas import todas_as_conquistas
        return [c.golpe for c in todas_as_conquistas().values()
                if c.golpe and c.chave in self.conquistas_feitas and chave_classe in golpe(c.golpe).classes_do_raro]

    # ============================================================
    # EXPEDIÇÃO (grupo montado no acampamento)
    # ============================================================

    def expedicao_atual(self):
        from roguelike.expedicao import Expedicao
        if self.expedicao is None:
            self.expedicao = Expedicao.padrao()
        return self.expedicao.validar(self)

    def visual_da_classe(self, classe):
        """Skins escolhidas para a classe (só as que continuam liberadas)."""
        return {camada: chave for camada, chave in self.visuais.get(classe, {}).items()
                if chave and self.skin_liberada(chave)}

    def equipar_skin(self, classe, camada, chave=None):
        """chave=None tira a skin daquela camada."""
        from roguelike.skins import skin
        if chave is not None and (not self.skin_liberada(chave) or not skin(chave).serve_para(classe)
                                  or skin(chave).camada != camada):
            return False
        visual = self.visuais.setdefault(classe, {})
        if chave is None:
            visual.pop(camada, None)
        else:
            visual[camada] = chave
        return True

    def preparar_heroi(self, heroi, quantidade_no_grupo):
        """Aplica raça, árvore de talentos, bênçãos, skins e golpes raros em um herói novo."""
        heroi.vestir(self.visual_da_classe(heroi.classe.chave))
        heroi.golpes_raros = self.golpes_raros_liberados(heroi.classe.chave)
        especiais = self.especiais_equipados()

        heroi.definir_raca(heroi.raca if self.tem_raca(heroi.raca) else "humano")

        if "aprendiz" in especiais:
            # Os golpes básicos de todas as classes (no grimório), mas sem árvore e sem subclasse
            heroi.subclasse_bloqueada = True
            for classe in todas_as_classes().values():
                for chave in classe.habilidades:
                    heroi.aprender(chave, perguntar=False)
        else:
            self.aplicar_arvore(heroi)

        for chave in self.bencaos_equipadas:
            dados = bencaos()[chave]
            if dados.get("especial") == "solitario" and quantidade_no_grupo != 1:
                continue
            for passiva in dados.get("passivas", []):
                heroi.adicionar_passiva(passiva)
        heroi.curar_tudo()

    def aplicar_arvore(self, heroi):
        classe = heroi.classe.chave
        arvore = arvore_da_classe(classe)
        for no, niveis in self.talentos.get(classe, {}).items():
            if no not in arvore or niveis <= 0:
                continue
            efeito = arvore[no].efeito
            tipo = efeito["tipo"]
            nome = "Talento: " + arvore[no].nome
            if tipo == "atributos":
                heroi.adicionar_passiva({"tipo": "bonus", "nome": nome,
                                         "modificadores": {a: v * niveis for a, v in efeito["atributos"].items()}})
            elif tipo == "bonus":
                heroi.adicionar_passiva({"tipo": "bonus", "nome": nome,
                                         "modificadores": {c: v * niveis for c, v in efeito["modificadores"].items()}})
            elif tipo == "nivel_habilidade":
                chave = efeito["habilidade"]
                if chave in heroi.niveis_habilidade:
                    heroi.niveis_habilidade[chave] = min(heroi.nivel_maximo_da(chave), 1 + niveis)
            elif tipo == "passiva":
                heroi.adicionar_passiva(efeito["passiva"])

    def subclasses_disponiveis(self, chave_classe):
        """Subclasses que a Capitã deixa escolher (liberadas pelo prestígio da classe)."""
        return todas_as_classes()[chave_classe].subclasses_ate_o_prestigio(self.nivel_de_prestigio(chave_classe))

    def criar_run(self, herois, semente=None):
        """Cria a run já com tudo do progresso aplicado."""
        for heroi in herois:
            self.preparar_heroi(heroi, len(herois))
        run = Run(herois, semente)
        run.ameaca = self.nivel_de_ameaca()
        self.equipar_do_arsenal(run)
        from roguelike.fabricacao import todas_as_receitas
        run.descobertas |= {r.chave for r in todas_as_receitas().values() if r.liberada_por in self.conquistas}
        run.conquistas_permanentes = set(self.conquistas)
        run.segredos = dict(self.segredos)
        for chave in self.bencaos_equipadas:
            efeitos = bencaos()[chave].get("run", {})
            run.grupo.ouro += efeitos.get("ouro_inicial", 0)
            run.bonus_loot += efeitos.get("bonus_loot", 0)
        self.entregar_provisoes(run)
        self.descobrir_golpes(herois)
        return run

    def nivel_de_ameaca(self):
        """Runs vencidas até o máximo de regras "ameaca": cada vitória deixa as próximas runs mais difíceis."""
        return min(regras()["ameaca"]["maximo"], self.estatisticas.get("vitorias", 0))

    def equipar_do_arsenal(self, run):
        """Equipamento inicial escolhido no arsenal: emprestado (continua no arsenal)."""
        run.emprestados = self.equipar_pecas_iniciais(run.grupo.herois)

    def equipar_pecas_iniciais(self, herois):
        """Equipa nos heróis as peças escolhidas no arsenal. Devolve {chave: quantas foram emprestadas}."""
        from roguelike.itens import item, existe
        usados = {}
        for heroi in herois:
            for espaco, chave in getattr(heroi, "equipamento_inicial", {}).items():
                if not existe(chave) or usados.get(chave, 0) >= self.arsenal.quantidade(chave):
                    continue
                if heroi.equipar(item(chave), espaco)[0]:
                    usados[chave] = usados.get(chave, 0) + 1
            heroi.curar_tudo()
        return usados

    # ============================================================
    # PARTIDA EM GRUPO (MP5: cada um traz os seus heróis; o host cria a run)
    # ============================================================

    def pacote_para_partida(self):
        """O que este jogador leva para uma partida em grupo: os heróis da expedição já prontos (raça, talentos,
        bênçãos, skins e as peças do arsenal), as peças de afixos deles, as provisões e o ouro das bênçãos.
        No co-op o grupo nunca tem 1 herói só: a bênção do Solitário não vale."""
        from roguelike.classes import heroi_para_dict
        from roguelike.exemplares import exportar
        herois = self.expedicao_atual().criar_herois(self)
        for heroi in herois:
            self.preparar_heroi(heroi, max(2, len(herois)))
        emprestados = self.equipar_pecas_iniciais(herois)
        chaves = [peca.chave for heroi in herois for _, peca in heroi.equipamentos.pecas()]
        ouro = sum(bencaos()[c].get("run", {}).get("ouro_inicial", 0) for c in self.bencaos_equipadas)
        return {"herois": [heroi_para_dict(h, com_mochila=False) for h in herois],
                "exemplares": exportar([c for c in chaves if "#" in c]), "emprestados": emprestados,
                "provisoes": dict(self.provisoes), "ouro_extra": ouro}

    def criar_run_em_grupo(self, participantes, semente=None):
        """A run de uma partida em grupo, criada pelo host com o progresso DELE (ameaça, conquistas, segredos,
        receitas e o bônus de loot das bênçãos). participantes = [(Jogador, pacote)], o host primeiro: cada um
        com os seus heróis, o ouro inicial (+ o das bênçãos dele) e as provisões na própria mochila."""
        from roguelike.classes import heroi_de_dict
        from roguelike.exemplares import importar
        from roguelike.fabricacao import todas_as_receitas
        grupos = []
        for jogador, pacote in participantes:
            importar(pacote.get("exemplares"))
            grupos.append((jogador, pacote, [heroi_de_dict(d) for d in pacote["herois"]]))
        run = Run([h for _, _, herois in grupos for h in herois], semente)
        run.grupo.jogadores = [jogador for jogador, _, _ in grupos]
        run.emprestados = {}
        for jogador, pacote, herois in grupos:
            jogador.ouro = regras()["economia"]["ouro_inicial"] + max(0, int(pacote.get("ouro_extra", 0)))
            for heroi in herois:
                run.grupo.dar_heroi(heroi, jogador)
            for chave, quantidade in (pacote.get("emprestados") or {}).items():
                run.emprestados[chave] = run.emprestados.get(chave, 0) + quantidade
            run.emprestados_de[jogador.id] = dict(pacote.get("emprestados") or {})
        run.ameaca = self.nivel_de_ameaca()
        run.descobertas |= {r.chave for r in todas_as_receitas().values() if r.liberada_por in self.conquistas}
        run.conquistas_permanentes = set(self.conquistas)
        run.segredos = dict(self.segredos)
        run.bonus_loot += sum(bencaos()[c].get("run", {}).get("bonus_loot", 0) for c in self.bencaos_equipadas)
        for jogador, pacote, _ in grupos:
            provisoes = {c: q for c, q in (pacote.get("provisoes") or {}).items() if q > 0}
            if provisoes:
                run.receber_itens(provisoes, jogador.mochila)
                run.estatisticas["itens_obtidos"] -= sum(provisoes.values())     # não contam como loot
        return run

    def partiu_em_grupo(self, run, meu_jogador):
        """A partida em grupo começou: as provisões levadas acabam e os golpes dos meus heróis vão ao Grimório."""
        self.provisoes = {}
        self.descobrir_golpes([h for h in run.grupo.herois if getattr(h.jogador, "id", None) == meu_jogador])

    # ============================================================
    # FIM DA RUN
    # ============================================================

    def conquistas_da_run(self, run):
        estatisticas = run.estatisticas
        conquistas = set()
        for chave in estatisticas["chefes"] + estatisticas["mini_chefes"]:
            conquistas.add(f"chefe:{chave}")
        for chave in estatisticas.get("derrotados_especiais", []):
            conquistas.add(f"derrotou:{chave}")
        for chave in estatisticas.get("feitos", []):                   # ex.: venceu A Corte Completa
            conquistas.add(f"feito:{chave}")
        for chave in run.subclasses_aprendidas:
            conquistas.add(f"subclasse:{chave}")
        for chave in getattr(run, "especializacoes_aprendidas", []):
            conquistas.add(f"especializacao:{chave}")
        for chave in estatisticas.get("itens_especiais", []):
            conquistas.add(f"item:{chave}")
        from roguelike.regioes import fases_iniciais
        for chave in run.regioes_visitadas:
            if chave not in fases_iniciais():       # toda run começa numa fase do 1º ato: não é conquista
                conquistas.add(f"regiao:{chave}")
        if run.resultado == "vitoria":
            conquistas.add("vitoria")
            if len(run.grupo.herois) == 1:
                conquistas.add("vitoria_solo")
        return conquistas

    def guardar_segredos(self, run):
        """Traz para o progresso os passos de segredo dados na run (fica o maior). Devolve as chaves que andaram."""
        andaram = []
        for chave, passos in getattr(run, "segredos", {}).items():
            if passos > self.segredos.get(chave, 0):
                self.segredos[chave] = passos
                andaram.append(chave)
        return andaram

    def registrar_fim_de_run(self, run, jogador=None):
        """Guarda as Brasas, o prestígio, as conquistas e as subclasses da run. Numa partida em grupo ('jogador': o
        deste computador), o prestígio é o das classes DELE e o arsenal recebe só as peças dele."""
        self.guardar_segredos(run)
        relatorio = RelatorioDeFim()
        relatorio.brasas = run.brasas_ganhas()
        self.brasas += relatorio.brasas
        for classe, xp in run.prestigio_ganho(jogador).items():
            antes = self.nivel_de_prestigio(classe)
            relatorio.prestigio[classe] = (xp, self.ganhar_prestigio(classe, xp))
            depois = self.nivel_de_prestigio(classe)
            for sub in todas_as_classes()[classe].subclasses.values():   # subclasses liberadas pelo prestígio
                if antes < sub.prestigio <= depois:
                    relatorio.subclasses_novas.append(sub.chave)
                    self.subclasses_liberadas.add(sub.chave)
        novas = self.conquistas_da_run(run) - self.conquistas
        self.conquistas |= novas
        relatorio.conquistas_novas = sorted(novas)
        relatorio.conquistas_feitas = self.verificar_conquistas()      # ex.: "vença uma run" libera a Auréola
        relatorio.herois_novos = self.herois_para_anunciar()            # ex.: a Rainha caiu: o Médico da Peste
        if run.resultado in ("vitoria", "fuga"):                        # só quem saiu vivo leva os itens
            relatorio.itens_guardados = self.arsenal.guardar(run.equipamentos_conquistados(jogador))

        self.estatisticas["runs"] += 1
        self.estatisticas["vitorias"] += 1 if run.resultado == "vitoria" else 0
        self.estatisticas["melhor_areas"] = max(self.estatisticas["melhor_areas"], run.estatisticas["areas"])
        self.estatisticas["brasas_totais"] += relatorio.brasas
        self.estatisticas["inimigos"] += run.estatisticas["inimigos_derrotados"]
        return relatorio

    # ============================================================
    # SALVAR E CARREGAR
    # ============================================================

    def para_dict(self):
        return {
            "brasas": self.brasas,
            "prestigio": self.prestigio,
            "talentos": self.talentos,
            "bencaos_compradas": self.bencaos_compradas,
            "bencaos_equipadas": self.bencaos_equipadas,
            "racas_compradas": self.racas_compradas,
            "conquistas": sorted(self.conquistas),
            "subclasses_liberadas": sorted(self.subclasses_liberadas),
            "estatisticas": self.estatisticas,
            "abates": self.abates,
            "conquistas_feitas": sorted(self.conquistas_feitas),
            "visuais": self.visuais,
            "golpes_descobertos": sorted(self.golpes_descobertos),
            "provisoes": self.provisoes,
            "skins_compradas": sorted(self.skins_compradas),
            "segredos": dict(self.segredos),
            "herois_anunciados": sorted(self.herois_anunciados),
            "expedicao": self.expedicao.para_dict() if self.expedicao is not None else None,
            "arsenal": self.arsenal.para_dict(),
        }

    @classmethod
    def de_dict(cls, dados):
        progresso = cls()
        progresso.brasas = dados.get("brasas", 0)
        progresso.prestigio = dados.get("prestigio", {})
        progresso.talentos = dados.get("talentos", {})
        progresso.bencaos_compradas = list(dados.get("bencaos_compradas", []))
        progresso.bencaos_equipadas = list(dados.get("bencaos_equipadas", []))
        progresso.racas_compradas = list(dados.get("racas_compradas", ["humano"]))
        progresso.conquistas = set(dados.get("conquistas", []))
        progresso.subclasses_liberadas = set(dados.get("subclasses_liberadas", []))
        progresso.estatisticas.update(dados.get("estatisticas", {}))
        progresso.abates = dict(dados.get("abates", {}))
        progresso.conquistas_feitas = set(dados.get("conquistas_feitas", []))
        progresso.visuais = {classe: dict(v) for classe, v in dados.get("visuais", {}).items()}
        progresso.golpes_descobertos = set(dados.get("golpes_descobertos", []))
        progresso.provisoes = dict(dados.get("provisoes", {}))
        progresso.skins_compradas = set(dados.get("skins_compradas", []))
        progresso.segredos = dict(dados.get("segredos", {}))
        progresso.herois_anunciados = set(dados.get("herois_anunciados", []))
        from roguelike.arsenal import Arsenal
        progresso.arsenal = Arsenal.de_dict(dados.get("arsenal"))      # antes da expedição (que usa as peças)
        if dados.get("expedicao"):
            from roguelike.expedicao import Expedicao
            progresso.expedicao = Expedicao.de_dict(dados["expedicao"])
        return progresso

    def salvar(self, caminho=None):
        gravar_json(caminho or self.caminho, {**self.para_dict(), "versao_do_jogo": VERSAO})

    @classmethod
    def carregar(cls, caminho=None):
        """Lê o progresso salvo (ou começa um novo, se não houver arquivo). Sem caminho: o da pasta do jogador."""
        caminho = caminho or CAMINHOS.save(ARQUIVO_DO_PROGRESSO)
        if not os.path.exists(caminho):
            progresso = cls()
        else:
            with open(caminho, encoding="utf-8") as arquivo:
                progresso = cls.de_dict(json.load(arquivo))
        progresso.caminho = caminho
        return progresso
