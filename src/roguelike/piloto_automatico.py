"""Piloto automático: joga uma run inteira sozinho.

Não faz parte do jogo em si. Serve para:
- os testes conferirem que uma run completa funciona do começo ao fim;
- balancear o jogo (ferramentas/simular_runs.py roda centenas de runs);
- o teste de determinismo: ele joga só por COMANDOS (os mesmos de quem joga na tela), então o registro do
  processador dele é a partida inteira, que dá para refazer do zero.

Ele joga de um jeito simples (bem pior que uma pessoa). No combate, decide como o DecisorIA (roguelike/condutor.py).
"""

import random

from roguelike.classes import criar_heroi
from roguelike.comandos import (AgirNoCombate, ComecarCombate, Comprar, ConcluirEncontro, DecidirGolpeNovo,
                                DescansoMaior, DistribuirPonto, EscolherEncontro, Equipar, Fabricar,
                                MelhorarHabilidade, MoverItem, ResolverEvento, Reviver, Treinar, UsarItem)
from roguelike.condutor import DecisorIA, ESPERANDO
from roguelike.encontros import TIPOS_DE_COMBATE
from roguelike.estado import BAU, EstadoDoJogo
from roguelike.processador import ProcessadorDeComandos

ORDEM_RARIDADE = {"comum": 0, "incomum": 1, "raro": 2, "epico": 3, "lendario": 4, "amaldicoado": 3}
POCOES = ("pocao_grande", "pocao_de_vida", "ensopado_suspeito", "pao_duro")
LIMITE_DE_DECISOES = 5000          # trava de segurança de uma luta (como antes da MP2: empate eterno = derrota)


class Piloto:
    def __init__(self, run, rng=None):
        self.run = run
        self.rng = rng or random.Random(run.semente)
        self.estado = EstadoDoJogo(run)
        self.processador = ProcessadorDeComandos(self.estado)
        self.decisor = DecisorIA()

    def enviar(self, comando):
        return self.processador.executar(comando)

    def numero(self, heroi):
        return self.estado.indice_do(heroi)

    def fontes(self, heroi):
        """[(origem no comando, inventário)]: de onde o herói tira itens (o baú da equipe e a mochila do jogador dele)."""
        return [(BAU, self.run.grupo.bau), (self.numero(heroi), heroi.inventario)]

    # ---------------- entre os encontros ----------------
    def cuidar_do_grupo(self):
        grupo = self.run.grupo
        for heroi in grupo.herois:
            while heroi.pontos_atributo > 0:
                for atributo in heroi.classe.atributos_principais:
                    self.enviar(DistribuirPonto(heroi=self.numero(heroi), atributo=atributo))
            # melhora primeiro as habilidades de dano mais baratas
            while heroi.pontos_habilidade > 0:
                opcoes = [h.chave for h, _ in heroi.habilidades() if heroi.pode_melhorar(h.chave)]
                if not opcoes:
                    break
                self.enviar(MelhorarHabilidade(heroi=self.numero(heroi), chave=self.rng.choice(opcoes)))
        for jogador in grupo.jogadores:                      # cada jogador fabrica com a mochila dele e o baú
            herois = grupo.herois_de(jogador)
            if not herois:
                continue
            estoque = self.run.estoque_de(herois[0])
            for receita in self.run.receitas_visiveis(herois[0]):
                if receita.pode_fabricar(estoque) and receita.item_resultado().tipo == "equipamento":
                    self.enviar(Fabricar(receita=receita.chave, heroi=self.numero(herois[0])))
        self.equipar_melhores()
        self.distribuir_pocoes()
        self.decidir_golpes()
        for heroi in grupo.vivos():
            if heroi.fracao_vida() < 0.5:
                self.beber_pocao(heroi)

    def beber_pocao(self, heroi):
        """Fora do combate: a primeira poção que houver (primeiro as do baú; a mochila fica para as lutas)."""
        for chave in POCOES:
            for origem, inventario in self.fontes(heroi):
                if inventario.tem(chave) and self.enviar(UsarItem(heroi=self.numero(heroi), chave=chave, origem=origem)):
                    return True
        return False

    def equipar_melhores(self):
        """As melhores peças (do baú e das mochilas) para quem tem uma pior no lugar."""
        grupo = self.run.grupo
        pecas = [(objeto, inventario) for inventario in self.run.inventarios()
                 for objeto, _ in inventario.pilhas("equipamento")]
        for objeto, inventario in sorted(pecas, key=lambda p: -ORDEM_RARIDADE[p[0].raridade]):
            for heroi in grupo.herois:
                if inventario is not grupo.bau and inventario is not heroi.inventario:
                    continue                                 # (a mochila de outro jogador)
                espacos = objeto.espacos_possiveis()
                livre = next((e for e in espacos if heroi.equipamento[e] is None), None)
                pior = min(espacos, key=lambda e: ORDEM_RARIDADE[heroi.equipamento[e].raridade]
                           if heroi.equipamento[e] else -1)
                atual = heroi.equipamento[livre or pior]
                if atual is None or ORDEM_RARIDADE[atual.raridade] < ORDEM_RARIDADE[objeto.raridade]:
                    origem = BAU if inventario is grupo.bau else self.numero(heroi)
                    if self.enviar(Equipar(heroi=self.numero(heroi), chave=objeto.chave, origem=origem)):
                        break

    def nota_fixa(self, heroi, chave):
        """Nota de um golpe fora do combate (para escolher os equipados)."""
        from roguelike.golpes import golpe
        atual, nivel = golpe(chave), heroi.nivel_da(chave)
        area = 2.5 if atual.alvo in ("inimigos", "aliados") else 1
        nota = 0.0
        for efeito in atual.efeitos:
            tipo = efeito.dados["tipo"]
            if tipo == "dano":
                minimo, maximo = efeito.no_nivel("dano", nivel)
                nota += (minimo + maximo) / 2 * efeito.no_nivel("golpes", nivel, 1) * area
            elif tipo == "cura":
                nota += 8 * area
            elif tipo in ("invocar", "reviver"):
                nota += 10
            else:
                nota += 3
        bonus_gratis = 6 if atual.custo == 0 and not atual.custo_vida else 0   # nunca ficar sem golpe grátis
        return nota - atual.custo * 0.8 + bonus_gratis

    def decidir_golpes(self):
        """Lê os tomos (do baú e das mochilas) e decide os golpes novos (troca pelo pior equipado, se for melhor)."""
        grupo = self.run.grupo
        tomos = [(objeto, inventario) for inventario in self.run.inventarios()
                 for objeto, _ in inventario.pilhas("consumivel") if not objeto.usavel_em_combate]
        for objeto, inventario in tomos:
            for heroi in grupo.vivos():
                if inventario is not grupo.bau and inventario is not heroi.inventario:
                    continue
                origem = BAU if inventario is grupo.bau else self.numero(heroi)
                if objeto.pode_ler(heroi) and \
                        self.enviar(UsarItem(heroi=self.numero(heroi), chave=objeto.chave, origem=origem)):
                    break
        for heroi in grupo.herois:
            for novo in list(heroi.golpes.pendentes):
                pior = min(heroi.golpes.equipados, key=lambda c: self.nota_fixa(heroi, c))
                esquecido = pior if self.nota_fixa(heroi, novo) > self.nota_fixa(heroi, pior) else None
                self.enviar(DecidirGolpeNovo(heroi=self.numero(heroi), novo=novo, esquecido=esquecido))

    def distribuir_pocoes(self):
        """Cada mochila com 2 poções de vida por herói vivo (as do baú vão para quem tem menos)."""
        grupo = self.run.grupo
        for jogador in grupo.jogadores:
            vivos = [h for h in grupo.herois_de(jogador) if h.esta_vivo()]
            while vivos and jogador.mochila.quantidade("pocao_de_vida") < 2 * len(vivos) and grupo.bau.tem("pocao_de_vida"):
                if not self.enviar(MoverItem(chave="pocao_de_vida", de=BAU, para=self.numero(vivos[0]))):
                    break

    def escolher_encontro(self):
        opcoes = self.run.opcoes_de_encontro()
        grupo = self.run.grupo
        fraco = grupo.nivel_medio() < self.run.perigo + 2            # nível baixo para a área
        ferido = sum(h.fracao_vida() for h in grupo.vivos()) / max(1, len(grupo.vivos())) < 0.5
        pesos = []
        for opcao in opcoes:
            if opcao.tipo == "portao":
                pesos.append(0 if opcao.bloqueado else 1)
            elif opcao.tipo in ("altar", "necromante") and grupo.caidos():
                pesos.append(20 if grupo.ouro >= opcao.preco() else 0.1)
            elif opcao.tipo == "treinador":
                pesos.append(10)
            elif opcao.tipo == "descanso":
                pesos.append(12 if ferido else 1)
            elif opcao.tipo in TIPOS_DE_COMBATE:
                if ferido:
                    pesos.append(0.5)
                elif opcao.estrelas <= 3:
                    pesos.append(8 if fraco else 4)
                else:
                    pesos.append(1 if fraco else 3)
            else:
                pesos.append(2)
        return self.rng.choices(range(len(opcoes)), weights=pesos)[0]

    # ---------------- encontros ----------------
    def lutar(self):
        """O combate do encontro atual: o condutor anda e o DecisorIA decide cada vez de herói (por comandos).
        Trava de segurança: uma luta em que ninguém consegue ferir ninguém acaba como derrota."""
        condutor = self.enviar(ComecarCombate()).valor
        for _ in range(LIMITE_DE_DECISOES):
            try:
                passo = condutor.avancar_ate_decisao()
            except RuntimeError:                       # (passos demais sem nenhum herói decidir)
                break
            if passo != ESPERANDO:
                return condutor.recompensa
            heroi = condutor.heroi_da_vez()
            if not self.enviar(self.decisor.comando(self.estado, heroi)):
                self.enviar(AgirNoCombate(heroi=self.numero(heroi), acao="concentrar"))
        condutor.combate.resultado = "derrota"         # empate eterno: o piloto desiste (só no simulador)
        condutor.passo()
        return condutor.recompensa

    def resolver(self, encontro):
        run = self.run
        if encontro.eh_combate():
            self.lutar()
        elif encontro.tipo == "evento":
            from roguelike.eventos_run import evento
            opcoes = evento(encontro.evento).opcoes
            validas = [i for i, o in enumerate(opcoes) if o.disponivel(run)]
            resultado = self.enviar(ResolverEvento(indice=self.rng.choice(validas))).valor
            if resultado is not None and resultado.combate is not None:
                self.lutar()
        elif encontro.tipo == "treinador":
            podem = encontro.herois_que_podem(run.grupo)
            if podem:
                self.enviar(Treinar(heroi=self.numero(podem[0])))
        elif encontro.tipo in ("altar", "necromante"):
            for heroi in run.grupo.caidos():
                self.enviar(Reviver(caido=self.numero(heroi)))
        elif encontro.tipo == "descanso":
            self.enviar(DescansoMaior())
        elif encontro.tipo in ("loja", "alquimista"):
            for jogador in run.grupo.jogadores:              # cada um com o próprio ouro
                for indice, oferta in enumerate(run.loja_atual.ofertas):
                    if oferta.chave in ("pocao_de_vida", "pocao_grande", "pena_da_fenix") and \
                            jogador.ouro > oferta.preco + 30:
                        self.enviar(Comprar(jogador=jogador.id, indice=indice))
        if not run.terminou():
            self.enviar(ConcluirEncontro())

    def jogar(self, limite_de_areas=200):
        for _ in range(limite_de_areas):
            if self.run.terminou():
                break
            self.cuidar_do_grupo()
            if self.enviar(EscolherEncontro(indice=self.escolher_encontro())):      # (passagem selada: tenta de novo)
                self.resolver(self.run.encontro)
        return self.run.resumo()


def grupo_padrao(classes):
    """Heróis prontos, cada um com a primeira subclasse da classe (a liberada desde o começo)."""
    from roguelike.classes import classe
    return [criar_heroi(chave, subclasse=next(iter(classe(chave).subclasses))) for chave in classes]
