"""A run: uma tentativa completa, do primeiro passo na Floresta até a morte (ou a vitória).

Fluxo de cada área:
    1. descanso automático (cura o maior entre 10 de vida ou 15% da vida máxima);
    2. o jogador mexe em pontos, inventário, baú e fabricação;
    3. escolhe 1 entre 3 encontros (opcoes_de_encontro / escolher);
    4. resolve o encontro (combate, evento, loja...) e chama concluir_encontro().

Tudo o que é sorteado usa a SEMENTE: rng("encontros"), rng("loja")... Assim a
mesma semente gera as mesmas opções em cada área.
"""

import json
import random

from caminhos import gravar_json
from roguelike.classes import criar_heroi, heroi_para_dict, heroi_de_dict, todas_as_classes, classes_liberadas
from roguelike.combate import Combate, somar_ajustes
from roguelike.dados import regras
from roguelike.eventos import Evento
from roguelike.encontros import GeradorDeEncontros, encontro_de_dict, EncontroAltar, EncontroLoja, EncontroCombate
from roguelike.exemplares import exportar, importar
from roguelike.eventos_run import evento as buscar_evento, nomes_de_herois
from roguelike.fabricacao import (receitas_reveladas_por, receitas_visiveis, fabricar as fabricar_receita,
                                  receita as buscar_receita)
from roguelike.grupo import Grupo
from roguelike.inimigos import criar_inimigo, ajuste_de_tier, ajustar_recompensa_de_tier
from roguelike.inventario import Inventario
from roguelike.itens import item
from roguelike.loot import juntar
from roguelike.passivas import criar_passiva
from roguelike.regioes import regiao as buscar_regiao, progressao
from versao import VERSAO

LETRAS_DA_SEMENTE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
VERSAO_DO_SAVE = 4       # 2 = fase 2 (golpes, subclasse, skins); 3 = fase 4 (atos, portões, fases de tamanho sorteado);
                         # 4 = MP4 (a mochila e o ouro são de cada jogador; os heróis não guardam mochila)


def nova_semente():
    sorteio = random.SystemRandom()
    return "".join(sorteio.choice(LETRAS_DA_SEMENTE) for _ in range(6))


def normalizar_semente(texto):
    """Deixa a semente em maiúsculas e sem espaços (vazia = sorteia uma nova)."""
    texto = "".join(str(texto or "").upper().split())
    return texto or nova_semente()


def tornar_dourado(inimigo, regra):
    """Elite de aura dourada: mais vida e dano, mais XP e loot garantido (a tela desenha o brilho)."""
    inimigo.dourado = True
    somar_ajustes(inimigo, regra.get("modificadores", {}))
    inimigo.recompensa_xp = round(inimigo.recompensa_xp * regra.get("xp", 1))
    inimigo.curar_tudo()


def eventos_sazonais_ativos():
    return [e for e in regras()["eventos_sazonais"].values() if e.get("ativo")]


class Recompensa:
    """O que o grupo ganhou num combate. O loot vem separado por jogador (por_jogador); 'itens' é a soma."""

    def __init__(self):
        self.xp = 0
        self.ouro = 0
        self.itens = {}
        self.por_jogador = {}     # id do jogador -> {chave: quantidade} (o que cada um ganhou)
        self.premios = {}         # id do jogador -> quantos prêmios (igual para quem tem o mesmo número de heróis)
        self.no_bau = {}          # id do jogador -> {chave: quantidade} que não coube na mochila e foi para o baú
        self.ouro_por_jogador = {}   # id do jogador -> a parte do ouro (pelos heróis de cada um)
        self.niveis = []          # (herói, níveis que subiu)
        self.abates = []          # chaves dos inimigos derrotados (contador permanente de abates)


class Run:
    def __init__(self, herois, semente=None, regiao_inicial=None):
        self.semente = normalizar_semente(semente)
        if regiao_inicial is None:          # a fase do 1º ato é sorteada pela semente
            regiao_inicial = progressao().fase_inicial(random.Random(f"{self.semente}|inicio"))
        self.grupo = Grupo(herois)
        self.regiao_atual = regiao_inicial
        self.area = 1
        self.perigo = 0                     # quantas áreas já foram vencidas (deixa os inimigos mais fortes)
        self.ameaca = 0                     # nível de ameaça: runs já vencidas (regras "ameaca"), fixo na run
        self.estado = "escolha"             # "escolha", "encontro" ou "fim"
        self.opcoes = None
        self.encontro = None
        self.escolhido = None               # índice da opção escolhida (vai no save: fechar o jogo não foge do encontro)
        self.loja_atual = None
        self.resultado = None               # None, "vitoria" ou "derrota"
        self.descobertas = set()            # receitas escondidas já reveladas
        self.eventos_vistos = []
        self.mini_chefes_derrotados = []
        self.regioes_visitadas = [regiao_inicial]
        self.retorno = None                 # (região, área) para voltar depois de uma região que "retorna"
        self.tamanhos = {}                  # região -> quantas áreas ela tem nesta run (sorteado na 1ª visita)
        self.portoes = None                 # [[fase, aberta]] oferecidos no fim de um ato (None = fora do fim de ato)
        self.efeitos_proximo_combate = []
        self.inimigos_extra_proximo_combate = []   # entram junto no próximo combate (ex.: Guardas Reais do Mercado)
        self.efeitos_ate_o_chefe = []        # status no começo de cada combate até vencer o chefe (Altar do Queijo)
        self.ajustes_do_chefe = {}           # bônus/penalidades do chefe da fase quando ele aparecer
        self.ondas = None                    # combate em ondas em andamento (roguelike/ondas.py; ex.: Enxame de Ratos)
        self.numero_do_combate = 0
        self.conquistas_permanentes = set()  # do progresso (chefes secretos pedem conquistas)
        self.segredos = {}                   # segredos que atravessam as runs (ex.: {"rato_branco": 1}); vêm do progresso
        self.mapas_usados = 0                # Mapas Rasgados usados (cada um sorteia outros caminhos)
        self.subclasses_aprendidas = [h.subclasse.chave for h in herois if h.subclasse]   # conquistas "subclasse:x"
        self.especializacoes_aprendidas = []
        self.bonus_loot = 0.0                # bênçãos podem aumentar a chance dos drops
        self.emprestados = {}                # peças levadas do arsenal (não voltam para ele de novo no fim)
        self.emprestados_de = {}             # partida em grupo: id do jogador -> as peças emprestadas do arsenal DELE
        self.exemplares_criados = 0          # contador para sortear os afixos sempre igual com a mesma semente
        self.estatisticas = {"inimigos_derrotados": 0, "combates": 0, "areas": 0, "itens_obtidos": 0,
                             "ouro_ganho": 0, "chefes": [], "mini_chefes": [],
                             "derrotados_especiais": [], "itens_especiais": [],
                             "feitos": []}            # encontros especiais vencidos (ex.: "corte_completa"): marco "feito:x"

    # ============================================================
    # CONSULTAS
    # ============================================================

    @property
    def regiao(self):
        return buscar_regiao(self.regiao_atual)

    def areas_da_regiao(self, chave=None):
        """Tamanho da região nesta run (sorteado na 1ª visita; regioes.json "areas_por_fase" e "areas_do_final")."""
        chave = chave or self.regiao_atual
        if chave not in self.tamanhos:
            rng = random.Random(f"{self.semente}|tamanho|{chave}")
            self.tamanhos[chave] = progressao().sortear_tamanho(chave, rng)
        return self.tamanhos[chave]

    def area_do_chefe(self):
        return self.regiao.area_do_chefe(self.area, self.areas_da_regiao())

    def hora(self):
        """0 = dia, 1 = noite (só as fases a céu aberto passam pelo dia)."""
        return self.regiao.hora(self.area, self.areas_da_regiao())

    def eh_noite(self):
        return self.regiao.eh_noite(self.area, self.areas_da_regiao())

    def zona(self):
        """A zona da área atual ({"nome", "musica"}), nas fases com zonas (ex.: Reino dos Ratos); senão None."""
        return self.regiao.zona(self.area, self.areas_da_regiao())

    def musica(self):
        """A música da área atual: a da zona (Reino dos Ratos) ou a da fase."""
        return self.regiao.musica_da_area(self.area, self.areas_da_regiao())

    def nome_do_ato(self):
        indice = self.regiao.ato
        return progressao().atos[indice].nome if indice is not None else None

    def rng(self, proposito):
        """Gerador de sorteio próprio para cada coisa de cada área (sempre o mesmo para a mesma semente)."""
        return random.Random(f"{self.semente}|{self.regiao_atual}|{self.area}|{proposito}")

    def terminou(self):
        return self.resultado is not None

    def pode_salvar(self):
        """Salvar só no mapa ou logo depois de escolher um encontro.

        Se o encontro mudou (um evento que virou combate), o save antigo continua valendo:
        assim não dá para fechar o jogo e escolher outra opção do evento com o prêmio já no bolso.
        """
        if self.estado != "encontro":
            return True
        return self.opcoes is not None and self.escolhido is not None and self.encontro is self.opcoes[self.escolhido]

    def inventarios(self):
        """O baú e a mochila de cada jogador (cada uma uma vez só)."""
        return [self.grupo.bau] + self.grupo.mochilas()

    def tem_item(self, chave):
        return any(inventario.tem(chave) for inventario in self.inventarios())

    def quantidade_de(self, chave):
        """Quantos o grupo tem (baú e mochilas)."""
        return sum(inventario.quantidade(chave) for inventario in self.inventarios())

    def gastar_item(self, chave):
        """Gasta um do baú ou, se não houver, da primeira mochila que tiver."""
        return any(inventario.remover(chave) for inventario in self.inventarios())

    # ============================================================
    # ITENS
    # ============================================================

    def receber_itens(self, itens, mochila=None, no_bau=None):
        """Guarda itens na 'mochila' (sem ela, no baú) e revela as receitas escondidas que eles abrem.
        O que não couber na mochila vai para o baú e é anotado em 'no_bau' ({chave: quantidade}).

        Equipamento raro ou melhor ganha afixos sorteados (vira um exemplar com chave própria).
        Devolve o que entrou de fato ({chave: quantidade})."""
        recebidos = {}
        for chave, quantidade in itens.items():
            for chave_final, n in self.com_afixos(chave, quantidade):
                foi_ao_bau = self.grupo.guardar_em(mochila, chave_final, n)
                if foi_ao_bau and mochila is not None and no_bau is not None:
                    no_bau[chave_final] = no_bau.get(chave_final, 0) + foi_ao_bau
                recebidos[chave_final] = recebidos.get(chave_final, 0) + n
            self.estatisticas["itens_obtidos"] += quantidade
            self.descobertas.update(receitas_reveladas_por(chave))
            if item(chave).categoria == "alma" and chave not in self.estatisticas["itens_especiais"]:
                self.estatisticas["itens_especiais"].append(chave)
        return recebidos

    def guardar_loot(self, por_jogador):
        """Entrega o loot de cada jogador ({id: {chave: quantidade}}) na mochila dele; o que não couber vai para o
        baú. Devolve (recebidos, no_bau), os dois no mesmo formato (peças com afixos viram exemplares)."""
        recebidos, no_bau = {}, {}
        for jogador_id, itens in por_jogador.items():
            jogador = self.grupo.jogador(jogador_id)
            sobra = {}
            recebidos[jogador_id] = self.receber_itens(itens, jogador.mochila if jogador else None, sobra)
            if sobra:
                no_bau[jogador_id] = sobra
        return recebidos, no_bau

    def com_afixos(self, chave, quantidade):
        """[(chave, quantidade)]: peças com afixos viram um exemplar por unidade."""
        from roguelike.exemplares import criar_exemplar
        from roguelike.itens import afixos_da_raridade
        objeto = item(chave)
        if objeto.tipo != "equipamento" or objeto.eh_exemplar() or not afixos_da_raridade(objeto.raridade):
            return [(chave, quantidade)]
        resultado = []
        for _ in range(quantidade):
            rng = random.Random(f"{self.semente}|exemplar|{self.exemplares_criados}")
            self.exemplares_criados += 1
            resultado.append((criar_exemplar(chave, rng).chave, 1))
        return resultado

    def todas_as_chaves(self):
        """Chaves de tudo o que o grupo tem: baú, mochilas e equipamento (repetidas pela quantidade)."""
        chaves = []
        for inventario in self.inventarios():
            for chave, n in inventario.itens.items():
                chaves += [chave] * n
        for heroi in self.grupo.herois:
            chaves += [p.chave for _, p in heroi.equipamentos.pecas()]
        return chaves

    def chaves_do_jogador(self, jogador):
        """O que é de um jogador numa partida em grupo: a mochila dele, o equipamento dos heróis dele e a parte dele
        das peças do baú (repartidas uma a uma, na ordem dos jogadores: igual em todo computador)."""
        chaves = [c for c, n in jogador.mochila.itens.items() for _ in range(n)]
        for heroi in self.grupo.herois_de(jogador):
            chaves += [p.chave for _, p in heroi.equipamentos.pecas()]
        pecas_do_bau = sorted(c for c, n in self.grupo.bau.itens.items() for _ in range(n)
                              if item(c).tipo == "equipamento")
        posicao = self.grupo.jogadores.index(jogador)
        chaves += pecas_do_bau[posicao::len(self.grupo.jogadores)]
        return chaves

    def equipamentos_conquistados(self, jogador=None):
        """Peças de equipamento que a run ganhou (sem as emprestadas do arsenal): vão para o arsenal.
        Com 'jogador' (partida em grupo), só as dele."""
        if jogador is None:
            sobra, chaves = dict(self.emprestados), self.todas_as_chaves()
        else:
            sobra, chaves = dict(self.emprestados_de.get(jogador.id, {})), self.chaves_do_jogador(jogador)
        conquistados = []
        for chave in chaves:
            if item(chave).tipo != "equipamento":
                continue
            if sobra.get(chave, 0) > 0:
                sobra[chave] -= 1
                continue
            conquistados.append(chave)
        return conquistados

    def fogueira(self):
        """Descanso Maior ou fase nova: as peças amaldiçoadas soltam e a Peste passa."""
        for heroi in self.grupo.herois:
            heroi.equipamentos.liberar_malditos()
            heroi.peste = 0

    def racas_do_grupo(self):
        return {h.raca for h in self.grupo.vivos()}

    def estoque_de(self, heroi=None):
        """De onde saem os ingredientes: a mochila do herói (se houver) e depois o baú da equipe."""
        from roguelike.fabricacao import Estoque
        return Estoque(heroi.inventario if heroi is not None else None, self.grupo.bau)

    def receitas_visiveis(self, heroi=None):
        """Receitas que aparecem (com a mochila do herói, se for dado, junto com o baú)."""
        return receitas_visiveis(self.estoque_de(heroi), self.descobertas, self.racas_do_grupo())

    def fabricar(self, chave_receita, heroi=None):
        """Fabrica gastando primeiro da mochila do herói e depois do baú. O resultado vai para a mochila
        dele (se couber) ou para o baú. Sem herói, usa só o baú (como antes)."""
        receita = buscar_receita(chave_receita)
        if not receita.liberada_para(self.racas_do_grupo()):
            return False
        if receita.escondida and chave_receita not in self.descobertas:
            return False
        estoque = self.estoque_de(heroi)
        destino = heroi.inventario if heroi is not None and heroi.inventario.cabe(receita.resultado) else self.grupo.bau
        if fabricar_receita(receita, estoque, destino):
            self.descobertas.update(receitas_reveladas_por(receita.resultado))
            return True
        return False

    # ============================================================
    # ENCONTROS
    # ============================================================

    def opcoes_de_encontro(self):
        if self.opcoes is None:
            self.opcoes = GeradorDeEncontros(self, self.rng("encontros")).gerar()
        return self.opcoes

    def escolher(self, indice):
        opcoes = self.opcoes_de_encontro()
        if self.estado != "escolha" or not 0 <= indice < len(opcoes):
            return None
        if getattr(opcoes[indice], "bloqueado", False):
            return None                     # portão selado (fase ainda sem conteúdo)
        self.encontro = opcoes[indice]
        self.escolhido = indice
        self.estado = "encontro"
        if self.encontro.tipo == "evento" and self.encontro.evento not in self.eventos_vistos:
            self.eventos_vistos.append(self.encontro.evento)
        if isinstance(self.encontro, EncontroLoja):
            self.loja_atual = self.encontro.criar_loja(self.rng("loja"), self.regiao.tier, self.descobertas,
                                                       self.regiao.consumiveis_a_venda())
        return self.encontro

    def concluir_encontro(self):
        """Fecha o encontro atual e avança para a próxima área (se a run continuar)."""
        if self.terminou():
            return
        if self.encontro is not None and self.encontro.tipo == "entrada":
            self.entrar_na_regiao(self.encontro.destino)
            return
        if self.encontro is not None and self.encontro.tipo == "portao":
            self.seguir_pelo_portao(self.encontro.destino)
            return
        self.avancar_area()

    def avancar_area(self):
        self.perigo += 1
        self.estatisticas["areas"] += 1
        if self.area_do_chefe():
            self.sair_da_regiao()
        else:
            self.area += 1
        self.comecar_area()

    def comecar_area(self):
        self.encontro = None
        self.escolhido = None
        self.loja_atual = None
        self.opcoes = None
        self.ondas = None
        if self.terminou():
            self.estado = "fim"
            return
        self.estado = "escolha"
        self.grupo.descansar()

    def sair_da_regiao(self):
        """Depois do chefe: volta (regiões que retornam), abre os portões do próximo ato ou vence a run."""
        indice = self.regiao.ato
        if self.regiao.retorna and self.retorno is not None:
            self.regiao_atual, area = self.retorno
            self.area = area + 1
            self.retorno = None
        elif indice is not None:
            ato = progressao().atos[indice]
            proximo = None if ato.final else progressao().proximo_ato(indice)
            if proximo is None:
                self.resultado = "vitoria"
            else:                           # o grupo fica no fim da fase escolhendo o portão
                self.portoes = [[fase, aberta] for fase, aberta in
                                progressao().portoes(proximo, self.rng("portoes"), self.marcos())]
        elif self.regiao.proxima:
            self.regiao_atual = self.regiao.proxima
            self.area = 1
        else:
            self.resultado = "vitoria"
        if self.regiao_atual not in self.regioes_visitadas:
            self.regioes_visitadas.append(self.regiao_atual)

    def seguir_pelo_portao(self, destino):
        """Começa a fase escolhida no fim do ato (a área do chefe já contou para o perigo)."""
        self.portoes = None
        self.fogueira()
        self.regiao_atual = destino
        self.area = 1
        if destino not in self.regioes_visitadas:
            self.regioes_visitadas.append(destino)
        self.comecar_area()

    def entrar_na_regiao(self, destino):
        self.fogueira()
        if buscar_regiao(destino).retorna:
            self.retorno = (self.regiao_atual, self.area)
        self.perigo += 1
        self.estatisticas["areas"] += 1
        self.regiao_atual = destino
        self.area = 1
        if destino not in self.regioes_visitadas:
            self.regioes_visitadas.append(destino)
        self.comecar_area()

    # ---------------- fuga: sair da run levando os itens ----------------
    def chefes_de_fuga(self):
        """Chefes e mini-chefes das fases prontas até o nível da fase atual (o guardião é sorteado entre eles)."""
        from roguelike.regioes import todas_as_regioes
        candidatos = set()
        for fase in todas_as_regioes().values():
            if fase.disponivel and fase.tier <= self.regiao.tier:
                candidatos.update(([fase.chefe] if fase.chefe else []) + fase.mini_chefes)
        return sorted(candidatos) or [self.regiao.chefe]

    def iniciar_fuga(self):
        """Sair da run: o grupo enfrenta um chefe sorteado, mais forte que o normal. Vencendo, a run acaba
        e os equipamentos vão para o arsenal; perdendo, é derrota."""
        from roguelike.inimigos import ficha
        if self.estado != "escolha" or self.terminou():
            return None
        chefe = self.rng("fuga").choice(self.chefes_de_fuga())
        encontro = EncontroCombate(f"Fuga: {ficha(chefe)['nome']}", "O guardião da saída não deixa ninguém passar.",
                                   regras()["fuga"]["estrelas"], [chefe], "fuga")
        self.opcoes = list(self.opcoes_de_encontro()) + [encontro]
        return self.escolher(len(self.opcoes) - 1)

    # ---------------- encontros sem luta ----------------
    def resolver_evento(self, indice):
        """Escolhe uma opção do evento atual. Se ela levar a um combate, o encontro vira esse combate."""
        if self.encontro is None or self.encontro.tipo != "evento":
            return None
        resultado = buscar_evento(self.encontro.evento).escolher(indice, self, self.rng("evento"))
        if resultado is not None and resultado.combate is not None:
            self.encontro = resultado.combate
        return resultado

    def proxima_onda(self):
        """Combate em ondas: o grupo decidiu continuar. O encontro passa a ser a próxima onda (None se não há)."""
        encontro = self.ondas.continuar() if self.ondas is not None else None
        if encontro is not None:
            self.encontro = encontro
        return encontro

    def encerrar_ondas(self):
        """Fim do combate em ondas: vencida a última, o prêmio; antes disso, a fuga com o que já ganhou.
        Devolve um ResultadoEvento (os textos para a tela)."""
        from roguelike.eventos_run import ResultadoEvento, criar_consequencia
        ondas, self.ondas = self.ondas, None
        resultado = ResultadoEvento()
        if ondas is None:
            return resultado
        if ondas.terminou():
            resultado.escrever(ondas.texto("premio"))
            rng = self.rng(f"ondas|{self.numero_do_combate}")
            for dados in ondas.premio:
                criar_consequencia(dados).aplicar(self, rng, resultado)
        else:
            resultado.escrever(ondas.texto("fuga"))
        return resultado

    def treinar(self, heroi):
        """O treinador ensina a especialização da subclasse do herói."""
        encontro = self.encontro
        if encontro is None or encontro.tipo != "treinador" or heroi not in encontro.herois_que_podem(self.grupo):
            return False
        especializacao = encontro.especializacao_de(heroi)
        if heroi.escolher_especializacao(especializacao):
            self.especializacoes_aprendidas.append(especializacao.chave)
            self.verificar_evolucoes()
            return True
        return False

    def reviver_pago(self, heroi, pagador=None):
        """Altar ou necromante: 'pagador' (sem ele, o jogador do herói) paga com o próprio ouro e o herói revive.
        No co-op dá para pagar a volta do herói de outro jogador."""
        encontro = self.encontro
        pagador = pagador or heroi.jogador
        if not isinstance(encontro, EncontroAltar) or heroi.esta_vivo() or pagador.ouro < encontro.preco():
            return False
        pagador.ouro -= encontro.preco()
        return self.grupo.reviver(heroi, encontro.fracao())

    def descanso_maior(self):
        if self.encontro is None or self.encontro.tipo != "descanso":
            return {}
        self.fogueira()
        return self.grupo.descansar(self.encontro.fracao(self.grupo))

    def recrutar(self, rng):
        """Um herói novo entra no grupo, no nível médio do grupo."""
        if self.grupo.cheio():
            return None
        no_grupo = {h.classe.chave for h in self.grupo.herois}
        liberadas = list(classes_liberadas(self.conquistas_permanentes))      # (as secretas só depois da conquista)
        classes = [c for c in liberadas if c not in no_grupo] or liberadas
        chave = rng.choice(classes)
        usados = {h.nome for h in self.grupo.herois}
        nome = rng.choice([n for n in nomes_de_herois() if n not in usados] or nomes_de_herois())
        aparencia = rng.choice(list(todas_as_classes()[chave].aparencias))
        heroi = criar_heroi(chave, nome, aparencia)
        for _ in range(self.grupo.nivel_medio() - 1):
            heroi.subir_nivel()
        while heroi.pontos_atributo > 0:
            for atributo in heroi.classe.atributos_principais:
                heroi.distribuir_ponto(atributo)
        heroi.curar_tudo()
        self.grupo.adicionar(heroi)
        return heroi

    # ============================================================
    # COMBATE
    # ============================================================

    def criar_combate(self, encontro=None):
        """Monta o Combate do encontro: inimigos mais fortes a cada área, bênçãos/maldições e consumíveis."""
        encontro = encontro or self.encontro
        escala = regras()["escala_inimigos"]
        inimigos = []
        chaves = list(encontro.inimigos)
        if self.inimigos_extra_proximo_combate and encontro.tipo != "fuga":     # ex.: Guardas Reais atrás do ladrão
            chaves += self.inimigos_extra_proximo_combate
            self.inimigos_extra_proximo_combate = []
        extras = getattr(encontro, "passivas_extras", None) or {}
        for chave in chaves:
            inimigo = criar_inimigo(chave)
            inimigo.passivas += [criar_passiva(p) for p in extras.get(chave, [])]   # só neste encontro (A Corte Completa)
            somar_ajustes(inimigo, ajuste_de_tier(inimigo.ficha, self.regiao.tier))    # visitante de outra fase
            ajustar_recompensa_de_tier(inimigo, self.regiao.tier)
            if encontro.tipo == "mini_chefe" and inimigo.categoria == "chefe":          # chefe de outra fase como mini-chefe
                somar_ajustes(inimigo, regras().get("chefe_como_mini_chefe", {}))
            somar_ajustes(inimigo, {"vida_percentual": escala["vida_por_area"] * self.perigo,
                                    "dano_causado": escala["dano_por_area"] * self.perigo})
            if self.ameaca:                             # cada run vencida deixa as próximas mais difíceis
                somar_ajustes(inimigo, {chave: valor * self.ameaca
                                        for chave, valor in regras()["ameaca"]["por_nivel"].items()})
            for sazonal in eventos_sazonais_ativos():
                somar_ajustes(inimigo, sazonal.get("ajuste_inimigos", {}))
            if encontro.tipo == "fuga":                 # o guardião da saída é mais forte que o normal
                somar_ajustes(inimigo, regras()["fuga"]["ajuste"])
            if inimigo.categoria == "chefe" and self.ajustes_do_chefe:   # ex.: roubaram o queijo do altar
                somar_ajustes(inimigo, self.ajustes_do_chefe)
            inimigos.append(inimigo)
        self.dourar(encontro, inimigos)

        self.numero_do_combate += 1
        combate = Combate(self.grupo.herois, inimigos, random.Random(f"{self.semente}|combate|{self.numero_do_combate}"))
        combate.grupo = self.grupo                  # (o pedágio do Barqueiro mexe no ouro)
        if getattr(encontro, "trono", None):        # o Rei dos Ratos espera no trono e volta quando a Rainha cair
            combate.de_volta = dict(encontro.trono)
        zona = self.zona()                          # Reino dos Ratos: água subindo, escuridão (roguelike/ambiente.py)
        if zona:
            from roguelike.ambiente import criar_ambientes
            combate.ambientes = criar_ambientes(zona.get("ambiente"))
        self.equilibrar_pelo_ato(combate.inimigos)
        combate.iniciar()
        for inimigo in combate.inimigos:
            if getattr(inimigo, "dourado", False):
                combate.registrar(Evento("aviso", inimigo, inimigo, texto=f"{inimigo.nome} brilha com uma aura dourada!"))

        for efeito in self.efeitos_proximo_combate:
            alvos = combate.aliados_de(self.grupo.herois[0]) if efeito.get("lado", "herois") == "herois" else combate.inimigos
            for alvo in list(alvos):
                combate.aplicar_status(alvo, efeito["status"], efeito.get("duracao"), efeito.get("valor", 0),
                                       efeito.get("acumulos", 1))
        self.efeitos_proximo_combate = []
        for efeito in self.efeitos_ate_o_chefe:                   # ex.: Bênção do Queijo
            for heroi in combate.aliados_de(self.grupo.herois[0]):
                combate.aplicar_status(heroi, efeito["status"], efeito.get("duracao"), efeito.get("valor", 0))
        self.usar_consumiveis_automaticos(combate)
        return combate

    def dourar(self, encontro, inimigos):
        """Às vezes um inimigo de um combate comum, horda ou elite vem com aura dourada (regras "dourados"):
        mais forte e com um equipamento garantido quando cai."""
        regra = regras().get("dourados")
        if not regra or encontro.tipo not in ("combate", "horda", "elite") or self.area < regra.get("area_minima", 1):
            return
        sorteio = self.rng(f"dourado|{self.numero_do_combate + 1}")
        candidatos = [i for i in inimigos if i.categoria != "chefe"]
        if not candidatos or sorteio.random() >= regra["chance"]:
            return
        tornar_dourado(sorteio.choice(candidatos), regra)

    def usar_fora_do_combate(self, chave, origem, alvo):
        """Consumível usado fora do combate. Mapa Rasgado e Incenso mexem na run; o resto vai para o grupo."""
        objeto = item(chave)
        tipos = {e.dados["tipo"] for e in getattr(objeto, "efeitos", [])}
        if "novos_caminhos" in tipos:
            if self.estado != "escolha" or self.portoes or self.area_do_chefe() or not origem.tem(chave):
                return False
            self.mapas_usados += 1
            self.opcoes = GeradorDeEncontros(self, self.rng(f"encontros|mapa{self.mapas_usados}")).gerar()
            origem.remover(chave)
            return True
        if "proximo_combate" in tipos:
            if not origem.tem(chave):
                return False
            for efeito in objeto.efeitos:
                dados = {k: v for k, v in efeito.dados.items() if k != "tipo"}
                self.efeitos_proximo_combate.append(dados)
            origem.remover(chave)
            return True
        return self.grupo.usar_fora_do_combate(chave, origem, alvo, self.rng(f"uso|{self.numero_do_combate}|{chave}"))

    def equilibrar_pelo_ato(self, inimigos):
        """Multiplica o total de vida/dano dos inimigos pelo "multiplicador_inimigos" da fase (ou do ato)."""
        indice = self.regiao.ato
        multiplicador = self.regiao.multiplicador_inimigos or \
            (progressao().atos[indice].multiplicador_inimigos if indice is not None else {})
        if not multiplicador:
            return
        for inimigo in inimigos:
            for chave, fator in multiplicador.items():
                total = 1 + inimigo.bonus(chave)            # (1 + soma de tudo): ficha, grupo, perigo...
                inimigo.ajustes[chave] = inimigo.ajustes.get(chave, 0) + total * (fator - 1)
            inimigo.curar_tudo()

    def usar_consumiveis_automaticos(self, combate):
        """O consumível do espaço automático de cada herói é usado no início do combate."""
        for heroi in self.grupo.vivos():
            consumivel = heroi.equipamento.get("consumivel")
            if consumivel is None or not heroi.inventario.tem(consumivel.chave):
                continue
            if consumivel.alvo in ("aliado", "si"):
                alvos = [heroi]
            elif consumivel.alvo == "inimigo":
                alvos = combate.oponentes_de(heroi)[:1]
            elif consumivel.alvo == "aliado_caido":
                alvos = [h for h in self.grupo.caidos()][:1]
            else:
                alvos = combate.alvos_validos(heroi, consumivel)
            if not alvos:
                continue
            heroi.inventario.remover(consumivel.chave)
            combate.registrar(Evento("item", heroi, alvos[0], texto=f"{heroi.nome} usou {consumivel.nome} (automático).",
                                     item=consumivel, alvos=list(alvos)))
            combate.aplicar_efeitos(heroi, consumivel.efeitos, alvos, 1)

    def concluir_combate(self, combate, encontro=None):
        """Distribui XP, ouro e loot. Em derrota, a run acaba.
        encontro: o da luta (o CondutorDoCombate passa o dele; sem ele, o encontro atual da run)."""
        encontro = encontro or self.encontro
        recompensa = Recompensa()
        self.estatisticas["combates"] += 1
        self.estatisticas["inimigos_derrotados"] += sum(i.abates() for i in combate.derrotados)   # (bando: por bicho)
        self.vigiar_desafio(combate.status_nos_herois | {s for h in combate.herois for s in h.status})
        if combate.resultado != "vitoria":
            self.resultado = "derrota"
            self.estado = "fim"
            return recompensa

        regra = regras()
        estrelas = max(1, getattr(encontro, "estrelas", 1))
        mais_estrelas = estrelas - 1
        extra = getattr(encontro, "recompensa_extra", None) or {}   # modo difícil (A Corte Completa)

        multiplicador_xp = regra["escala_inimigos"]["xp_multiplicador"] * \
            (1 + regra["estrelas"]["xp_por_estrela"] * mais_estrelas) * \
            (1 + regra["escala_inimigos"]["xp_por_area"] * self.perigo) * (1 + extra.get("xp", 0))
        recompensa.xp = round(combate.xp_ganho() * multiplicador_xp)

        multiplicador_ouro = (1 + regra["estrelas"]["ouro_por_estrela"] * mais_estrelas) * \
                             (1 + regra["escala_inimigos"]["ouro_por_area"] * self.perigo) * (1 + extra.get("ouro", 0))
        multiplicador_ouro *= 1 + sum(h.bonus("ouro_extra") for h in self.grupo.vivos())      # ex.: Realeza Roedora
        for sazonal in eventos_sazonais_ativos():
            multiplicador_ouro *= sazonal.get("multiplicador_ouro", 1)
        recompensa.ouro = round(combate.ouro_ganho() * multiplicador_ouro)

        from roguelike.gerador_de_loot import GeradorDeLoot              # loot separado por jogador (regras "loot")
        gerador = GeradorDeLoot(self)
        loot = gerador.do_combate(combate, encontro, self.rng(f"loot{self.numero_do_combate}"))
        recompensa.premios = dict(gerador.contagem)
        recompensa.abates =[i.chave for i in combate.derrotados if not i.eh_invocacao for _ in range(i.abates())]
        recompensa.abates += [forma for i in combate.derrotados for forma in getattr(i, "formas", [])]   # ex.: Dragão do Eclipse

        recompensa.ouro_por_jogador = self.grupo.ganhar_ouro(recompensa.ouro)   # pelos heróis de cada um
        self.estatisticas["ouro_ganho"] += recompensa.ouro
        recompensa.por_jogador, recompensa.no_bau = self.guardar_loot(loot)    # na mochila de cada um (o resto: baú)
        recompensa.itens = juntar(*recompensa.por_jogador.values())
        for heroi in self.grupo.vivos():
            heroi.peste = heroi.acumulos_de("peste")        # a Peste segue para a próxima luta
            heroi.status = {}
            niveis = heroi.ganhar_xp(recompensa.xp)
            if niveis:
                recompensa.niveis.append((heroi, niveis))

        for inimigo in combate.derrotados:
            if inimigo.categoria != "comum" and inimigo.chave not in self.estatisticas["derrotados_especiais"]:
                self.estatisticas["derrotados_especiais"].append(inimigo.chave)
            if inimigo.categoria == "chefe":
                self.estatisticas["chefes"].append(inimigo.chave)
                self.efeitos_ate_o_chefe, self.ajustes_do_chefe = [], {}     # o que valia "até o chefe" acaba aqui
            elif inimigo.categoria == "mini_chefe":
                self.estatisticas["mini_chefes"].append(inimigo.chave)
                self.mini_chefes_derrotados.append(inimigo.chave)
        feito = getattr(encontro, "feito", None)
        if feito and feito not in self.estatisticas.setdefault("feitos", []):
            self.estatisticas["feitos"].append(feito)
        self.cumprir_desafio(combate)
        self.verificar_evolucoes()
        if combate.proxima_parte and self.ondas is None:          # o Rei fugiu para o trono: a luta continua
            from roguelike.ondas import CombateEmOndas
            self.ondas = CombateEmOndas.continuacao(encontro, combate.proxima_parte)
        if self.ondas is not None and self.ondas.em_luta():      # combate em ondas: esta onda está vencida
            self.ondas.vencer()
            if not self.ondas.terminou() and self.ondas.folego:   # um fôlego antes da próxima
                self.grupo.descansar(self.ondas.folego)
        if getattr(encontro, "tipo", None) == "fuga":       # venceu o guardião: a run acaba com os itens
            self.resultado = "fuga"
            self.estado = "fim"
        return recompensa

    def vigiar_desafio(self, status_pegos):
        """Desafio da fase (regioes.json "desafio", ex.: vencer o Reino sem pegar Peste): se um herói pegou o status
        aqui, a fase não vale mais o feito nesta run."""
        desafio = self.regiao.desafio
        perdidos = self.estatisticas.setdefault("desafios_perdidos", [])
        if desafio and desafio["sem_status"] in status_pegos and self.regiao_atual not in perdidos:
            perdidos.append(self.regiao_atual)

    def cumprir_desafio(self, combate):
        """O chefe da fase caiu e o desafio continua de pé: ganha o feito (ex.: "feito:imune")."""
        desafio = self.regiao.desafio
        if not desafio or self.regiao_atual in self.estatisticas.get("desafios_perdidos", []):
            return
        feitos = self.estatisticas.setdefault("feitos", [])
        if any(i.chave == self.regiao.chefe for i in combate.derrotados) and desafio["feito"] not in feitos:
            feitos.append(desafio["feito"])

    def marcos(self):
        """O que já aconteceu nesta run (requisitos de evolução): "chefe:aranha_mae", "regiao:minas"..."""
        marcos = {f"chefe:{c}" for c in self.estatisticas["chefes"] + self.estatisticas["mini_chefes"]}
        marcos |= {f"regiao:{r}" for r in self.regioes_visitadas}
        marcos |= {f"feito:{f}" for f in self.estatisticas.get("feitos", [])}      # ex.: "feito:corte_completa"
        return marcos

    def verificar_evolucoes(self):
        """Aprimora os golpes de todos os heróis que cumpriram o requisito. Devolve [(herói, antigo, novo)]."""
        marcos = self.marcos()
        return [(heroi, antigo, novo) for heroi in self.grupo.herois
                for antigo, novo in heroi.golpes.verificar_evolucoes(marcos)]

    # ============================================================
    # FIM DA RUN
    # ============================================================

    def brasas_ganhas(self):
        """Moeda permanente ganha nesta run (mais quanto mais longe for)."""
        regra = regras()["recompensa_meta"]
        brasas = self.estatisticas["areas"] * regra["brasas_por_area"]
        brasas += len(self.estatisticas["chefes"]) * regra["brasas_por_chefe"]
        brasas += len(self.estatisticas["mini_chefes"]) * regra["brasas_por_mini_chefe"]
        if self.resultado == "vitoria":
            brasas += regra["brasas_vitoria"]
        if self.ameaca:                                 # mais risco, mais Brasas
            brasas = round(brasas * (1 + regras()["ameaca"]["brasas_por_nivel"] * self.ameaca))
        return brasas

    def prestigio_ganho(self, jogador=None):
        """XP de prestígio para cada classe que esteve no grupo (com 'jogador': só as dos heróis dele)."""
        regra = regras()["recompensa_meta"]
        valor = self.estatisticas["areas"] * regra["prestigio_por_area"] + \
            len(self.estatisticas["chefes"]) * regra["prestigio_por_chefe"]
        herois = self.grupo.herois if jogador is None else self.grupo.herois_de(jogador)
        return {h.classe.chave: valor for h in herois}

    def resumo(self):
        return {
            "resultado": self.resultado,
            "regiao": self.regiao.nome,
            "area": self.area,
            "areas_vencidas": self.estatisticas["areas"],
            "inimigos_derrotados": self.estatisticas["inimigos_derrotados"],
            "itens_obtidos": self.estatisticas["itens_obtidos"],
            "ouro_ganho": self.estatisticas["ouro_ganho"],
            "chefes": list(self.estatisticas["chefes"]),
            "semente": self.semente,
            "brasas": self.brasas_ganhas(),
            "prestigio": self.prestigio_ganho(),
        }

    # ============================================================
    # SALVAR E CARREGAR
    # ============================================================

    def para_dict(self):
        return {
            "versao": VERSAO_DO_SAVE,
            "semente": self.semente,
            "jogadores": [j.para_dict() for j in self.grupo.jogadores],        # com a mochila e o ouro de cada um
            "herois": [heroi_para_dict(h, com_mochila=False) for h in self.grupo.herois],
            "bau": self.grupo.bau.para_dict(),
            "registro_do_bau": self.grupo.bau.registro_para_dict(),
            "ouro": self.grupo.ouro,                                            # (a soma: para saves antigos)
            "regiao_atual": self.regiao_atual,
            "area": self.area,
            "perigo": self.perigo,
            "ameaca": self.ameaca,
            "resultado": self.resultado,
            "opcoes": [o.para_dict() for o in self.opcoes] if self.opcoes is not None else None,
            "escolhido": self.escolhido if self.estado == "encontro" else None,
            "descobertas": sorted(self.descobertas),
            "eventos_vistos": list(self.eventos_vistos),
            "mini_chefes_derrotados": list(self.mini_chefes_derrotados),
            "regioes_visitadas": list(self.regioes_visitadas),
            "retorno": list(self.retorno) if self.retorno else None,
            "tamanhos": dict(self.tamanhos),
            "portoes": [list(p) for p in self.portoes] if self.portoes is not None else None,
            "efeitos_proximo_combate": list(self.efeitos_proximo_combate),
            "inimigos_extra_proximo_combate": list(self.inimigos_extra_proximo_combate),
            "efeitos_ate_o_chefe": list(self.efeitos_ate_o_chefe),
            "ajustes_do_chefe": dict(self.ajustes_do_chefe),
            "numero_do_combate": self.numero_do_combate,
            "conquistas_permanentes": sorted(self.conquistas_permanentes),
            "segredos": dict(self.segredos),
            "mapas_usados": self.mapas_usados,
            "subclasses_aprendidas": list(self.subclasses_aprendidas),
            "especializacoes_aprendidas": list(self.especializacoes_aprendidas),
            "bonus_loot": self.bonus_loot,
            "emprestados": dict(self.emprestados),
            "emprestados_de": {j: dict(e) for j, e in self.emprestados_de.items()},
            "exemplares_criados": self.exemplares_criados,
            "exemplares": exportar([c for c in self.todas_as_chaves() if "#" in c]),
            "estatisticas": dict(self.estatisticas),
        }

    @classmethod
    def de_dict(cls, dados):
        importar(dados.get("exemplares", {}))       # antes dos heróis: o equipamento pode ser um exemplar
        herois = [heroi_de_dict(h) for h in dados["herois"]]
        # saves de antes da MP4: cada herói tinha a sua mochila; ela vai para a do jogador dele (o resto, ao baú)
        antigas = [h.inventario if "inventario" in info else None for h, info in zip(herois, dados["herois"])]
        for heroi in herois:
            heroi.inventario = None
        run = cls(herois, dados["semente"], dados["regiao_atual"])
        if dados.get("jogadores"):                  # quem comanda cada herói (saves antigos: o jogador local)
            from roguelike.posse import Jogador
            run.grupo.jogadores = [Jogador.de_dict(j) for j in dados["jogadores"]]
        for heroi, info, antiga in zip(run.grupo.herois, dados["herois"], antigas):
            run.grupo.dar_heroi(heroi, run.grupo.jogador(info.get("jogador")) or run.grupo.jogadores[0])
            for chave, quantidade in (antiga.itens if antiga is not None else {}).items():
                run.grupo.guardar_em(heroi.inventario, chave, quantidade)
        run.emprestados = dict(dados.get("emprestados", {}))
        run.emprestados_de = {str(j): dict(e) for j, e in (dados.get("emprestados_de") or {}).items()}
        run.exemplares_criados = dados.get("exemplares_criados", 0)
        for chave, quantidade in Inventario.de_dict(dados["bau"]).itens.items():   # (somando ao que já sobrou)
            run.grupo.bau.adicionar(chave, quantidade)
        run.grupo.bau.carregar_registro(dados.get("registro_do_bau"), run.grupo.jogadores)
        if dados.get("versao", 1) < 4:              # save de antes da MP4: o ouro era um só (fica com o local)
            run.grupo.ouro = dados["ouro"]
        run.area = dados["area"]
        run.perigo = dados["perigo"]
        run.ameaca = dados.get("ameaca", 0)
        run.resultado = dados.get("resultado")
        run.estado = "fim" if run.resultado else "escolha"
        if dados.get("opcoes") is not None:
            run.opcoes = [encontro_de_dict(o) for o in dados["opcoes"]]
        run.descobertas = set(dados.get("descobertas", []))
        run.eventos_vistos = list(dados.get("eventos_vistos", []))
        run.mini_chefes_derrotados = list(dados.get("mini_chefes_derrotados", []))
        run.regioes_visitadas = list(dados.get("regioes_visitadas", [run.regiao_atual]))
        run.retorno = tuple(dados["retorno"]) if dados.get("retorno") else None
        run.tamanhos = dict(dados.get("tamanhos", {}))
        run.portoes = [list(p) for p in dados["portoes"]] if dados.get("portoes") is not None else None
        if dados.get("versao", 1) < 3:
            # save de antes dos atos: as regiões em andamento mantêm o tamanho original
            for chave in [run.regiao_atual] + ([run.retorno[0]] if run.retorno else []):
                run.tamanhos.setdefault(chave, buscar_regiao(chave).areas)
        run.efeitos_proximo_combate = list(dados.get("efeitos_proximo_combate", []))
        run.inimigos_extra_proximo_combate = list(dados.get("inimigos_extra_proximo_combate", []))
        run.efeitos_ate_o_chefe = list(dados.get("efeitos_ate_o_chefe", []))
        run.ajustes_do_chefe = dict(dados.get("ajustes_do_chefe", {}))
        run.numero_do_combate = dados.get("numero_do_combate", 0)
        run.conquistas_permanentes = set(dados.get("conquistas_permanentes", []))
        run.segredos = dict(dados.get("segredos", {}))
        run.mapas_usados = dados.get("mapas_usados", 0)
        run.subclasses_aprendidas = list(dados.get("subclasses_aprendidas", run.subclasses_aprendidas))
        run.especializacoes_aprendidas = list(dados.get("especializacoes_aprendidas", []))
        run.bonus_loot = dados.get("bonus_loot", 0.0)
        run.estatisticas.update(dados.get("estatisticas", {}))
        if dados.get("versao", 1) < 2:
            # save antigo: herói sem subclasse ganha a primeira da classe (o treinador agora ensina especialização)
            for heroi in run.grupo.herois:
                if heroi.subclasse is None and not heroi.subclasse_bloqueada:
                    heroi.escolher_subclasse(next(iter(heroi.classe.subclasses.values())))
        if dados.get("escolhido") is not None and not run.terminou():
            run.escolher(dados["escolhido"])        # volta para o encontro que estava em andamento
        return run

    def salvar(self, caminho):
        """Salva a run. É chamado no mapa e ao escolher um encontro (nunca no meio dele).

        Se o jogo fechar durante um encontro, ao carregar a run volta para o começo desse mesmo
        encontro: não dá para fugir de um combate difícil nem "voltar no tempo" depois dele.
        """
        gravar_json(caminho, {**self.para_dict(), "versao_do_jogo": VERSAO})

    @classmethod
    def carregar(cls, caminho):
        with open(caminho, encoding="utf-8") as arquivo:
            return cls.de_dict(json.load(arquivo))
