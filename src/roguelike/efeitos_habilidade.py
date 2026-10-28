"""Efeitos: as "peças" de que são feitas as habilidades e os itens.

No JSON, uma habilidade tem uma lista de efeitos, por exemplo:

    "efeitos": [
        {"tipo": "dano", "dano": [2, 4], "golpes": 2, "escala": {"forca": 0.3}},
        {"tipo": "status", "status": "sangramento", "acumulos": 2, "chance": 0.6}
    ]

Cada "tipo" é uma subclasse de Efeito. "por_nivel" diz quanto cada número
aumenta a cada nível da habilidade, ex.: "por_nivel": {"dano": [1, 1]}.
"""

from roguelike.atributos import sigla
from roguelike.elementos import PADRAO as ELEMENTO_PADRAO, nome as nome_do_elemento
from roguelike.status import dados_do_status


class Contexto:
    """O que já aconteceu durante o uso de uma habilidade."""

    def __init__(self):
        self.teve_dano = False      # a habilidade tentou causar dano?
        self.acertados = []         # quem levou pelo menos um golpe (sem esquivar)
        self.dano_total = 0


class Efeito:
    """Classe base de todos os efeitos."""

    def __init__(self, dados):
        self.dados = dict(dados)

    def no_nivel(self, chave, nivel, padrao=None):
        """Valor de um número já com o aumento dos níveis acima do 1º."""
        valor = self.dados.get(chave, padrao)
        aumento = self.dados.get("por_nivel", {}).get(chave)
        if aumento is None or nivel <= 1 or valor is None:
            return valor
        vezes = nivel - 1
        if isinstance(valor, list):
            return [v + a * vezes for v, a in zip(valor, aumento)]
        return valor + aumento * vezes

    def em_quem(self, usuario, alvos, contexto):
        """Em quem o efeito acontece: no usuário ou nos alvos da habilidade."""
        if self.dados.get("em") == "usuario":
            return [usuario]
        if contexto.teve_dano and self.dados.get("se_acertar", True):
            return [alvo for alvo in alvos if alvo in contexto.acertados]
        return list(alvos)

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        raise NotImplementedError

    def resumo(self, nivel=1):
        """Texto curto para a tela."""
        return ""


def texto_escala(escala):
    if not escala:
        return ""
    partes = [f"{int(peso * 100)}% {sigla(atributo)}" for atributo, peso in escala.items()]
    return " (+" + ", ".join(partes) + ")"


def bonus_de_atributos(lutador, escala):
    return sum(lutador.atributo(atributo) * peso for atributo, peso in (escala or {}).items())


class EfeitoDano(Efeito):
    """Golpes de dano. Cada golpe rola esquiva, crítico e bloqueio separados."""

    @property
    def elemento(self):
        return self.dados.get("elemento", ELEMENTO_PADRAO)

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        contexto.teve_dano = True
        minimo, maximo = self.no_nivel("dano", nivel)
        golpes = self.no_nivel("golpes", nivel, 1)
        if "golpes_por_caido" in self.dados and hasattr(usuario, "caidos"):    # a Roda Furiosa: mais golpes sem ratos
            golpes += int(usuario.caidos() * self.dados["golpes_por_caido"])
        aleatorio = self.dados.get("aleatorio", False)

        if aleatorio:
            # Cada golpe vai para um alvo sorteado
            ordem = [None] * golpes
        else:
            ordem = [alvo for alvo in alvos for _ in range(golpes)]

        for alvo in ordem:
            if alvo is None:
                vivos = [a for a in alvos if a.esta_vivo()]
                if not vivos:
                    break
                alvo = combate.rng.choice(vivos)
            if not alvo.esta_vivo() or not usuario.esta_vivo():
                continue

            base = combate.rng.randint(minimo, maximo) + bonus_de_atributos(usuario, self.dados.get("escala"))
            multiplicador = 1.0
            for chave_status, extra in self.dados.get("bonus_contra", {}).items():
                if alvo.tem_status(chave_status):
                    multiplicador += extra
            if "bonus_vida_baixa" in self.dados and alvo.fracao_vida() <= self.dados.get("limite_vida_baixa", 0.3):
                multiplicador += self.dados["bonus_vida_baixa"]
            multiplicador += self.bonus_contra_natureza(alvo)

            resultado = combate.golpear(
                usuario, alvo, base * multiplicador,
                ignora_esquiva=self.dados.get("ignora_esquiva", False),
                ignora_bloqueio=self.dados.get("ignora_bloqueio", False),
                roubo=self.no_nivel("roubo", nivel, 0),
                direto=len(alvos) == 1 or aleatorio,
                elemento=self.elemento,
            )
            if resultado.acertou and alvo not in contexto.acertados:
                contexto.acertados.append(alvo)
            contexto.dano_total += resultado.dano

    def bonus_contra_natureza(self, alvo):
        """Fogo sagrado: dano extra contra raças (meio_demonio, revenante...) ou famílias (mortos_vivos...)."""
        tabela = self.dados.get("bonus_contra_natureza", {})
        if not tabela:
            return 0.0
        naturezas = {getattr(alvo, "raca", None)}
        ficha = getattr(alvo, "ficha", None)
        if ficha:
            naturezas.add(ficha.get("familia"))
        return max((extra for natureza, extra in tabela.items() if natureza in naturezas), default=0.0)

    def resumo(self, nivel=1):
        minimo, maximo = self.no_nivel("dano", nivel)
        golpes = self.no_nivel("golpes", nivel, 1)
        de_elemento = f" de {nome_do_elemento(self.elemento)}" if self.elemento != ELEMENTO_PADRAO else ""
        texto = f"{minimo}-{maximo} de dano{de_elemento}{texto_escala(self.dados.get('escala'))}"
        if golpes > 1:
            texto = f"{golpes} golpes de " + texto
        if self.dados.get("aleatorio"):
            texto += " em alvos aleatórios"
        if "golpes_por_caido" in self.dados:
            texto += f", +1 golpe a cada {round(1 / self.dados['golpes_por_caido'])} ratos caídos da roda"
        roubo = self.no_nivel("roubo", nivel, 0)
        if roubo:
            texto += f", rouba {int(roubo * 100)}% como vida"
        if self.dados.get("ignora_bloqueio"):
            texto += ", ignora bloqueio"
        if self.dados.get("ignora_esquiva"):
            texto += ", não pode ser esquivado"
        for chave_status, extra in self.dados.get("bonus_contra", {}).items():
            texto += f", +{int(extra * 100)}% contra {dados_do_status(chave_status)['nome'].lower()}"
        if "limite_vida_baixa" in self.dados:
            texto += (f", +{int(self.dados['bonus_vida_baixa'] * 100)}% em alvos abaixo de "
                      f"{int(self.dados['limite_vida_baixa'] * 100)}% da vida")
        elif "bonus_vida_baixa" in self.dados:
            texto += f", +{int(self.dados['bonus_vida_baixa'] * 100)}% em alvos com pouca vida"
        if self.dados.get("bonus_contra_natureza"):
            texto += ", " + self.dados.get("texto_contra", "mais forte contra demônios e mortos-vivos")
        return texto


class EfeitoCura(Efeito):
    """Cura um valor fixo e/ou uma porcentagem da vida máxima."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        minimo, maximo = self.no_nivel("cura", nivel, [0, 0])
        percentual = self.no_nivel("percentual", nivel, 0)
        for alvo in self.em_quem(usuario, alvos, contexto):
            if not alvo.esta_vivo():
                continue
            valor = combate.rng.randint(minimo, maximo) + bonus_de_atributos(usuario, self.dados.get("escala"))
            valor += alvo.vida_maxima * percentual
            valor *= usuario.stat("cura_causada")
            combate.curar(alvo, round(valor), usuario, motivo="cura")
            if usuario.bonus("cura_purifica") > 0:                 # o Traje do Médico completo
                combate.aliviar(alvo, "peste", 1, usuario)
                combate.aliviar(alvo, "veneno", 1, usuario)

    def resumo(self, nivel=1):
        minimo, maximo = self.no_nivel("cura", nivel, [0, 0])
        partes = []
        if maximo:
            partes.append(f"{minimo}-{maximo}{texto_escala(self.dados.get('escala'))}")
        percentual = self.no_nivel("percentual", nivel, 0)
        if percentual:
            partes.append(f"{int(percentual * 100)}% da vida máxima")
        texto = "cura " + " + ".join(partes)
        if self.dados.get("em") == "usuario":
            texto += " (em si)"
        return texto


class EfeitoStatus(Efeito):
    """Aplica um status. Carisma (potência de suporte) aumenta chance e valor.

    "so_familias": ["pestes"] limita a quem é dessas famílias de inimigo (ex.: a isca do Queijo Mofado).
    "so_bandos": true limita aos bandos (ex.: a Flauta do Caçador de Ratos encanta os bandos de ratos)."""

    def pega_em(self, alvo):
        if self.dados.get("so_bandos") and not getattr(alvo, "eh_bando", False):
            return False
        familias = self.dados.get("so_familias")
        return not familias or (getattr(alvo, "ficha", None) or {}).get("familia") in familias

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        potencia = usuario.stat("potencia_suporte")
        chance = min(1.0, self.no_nivel("chance", nivel, 1.0) * potencia)
        valor = self.no_nivel("valor", nivel, 0) + bonus_de_atributos(usuario, self.dados.get("escala"))
        valor = round(valor * potencia)
        acumulos = max(1, int(self.no_nivel("acumulos", nivel, 1) * potencia))
        duracao = self.no_nivel("duracao", nivel)

        for alvo in self.em_quem(usuario, alvos, contexto):
            if not alvo.esta_vivo() or not self.pega_em(alvo):
                continue
            if chance < 1 and combate.rng.random() >= chance:
                continue
            combate.aplicar_status(alvo, self.dados["status"], duracao, valor, acumulos, usuario)

    def resumo(self, nivel=1):
        dados = dados_do_status(self.dados["status"])
        texto = dados["nome"]
        acumulos = self.no_nivel("acumulos", nivel, 1)
        if dados.get("acumula") and acumulos > 1:
            texto += f" x{acumulos}"
        valor = self.no_nivel("valor", nivel, 0)
        if valor:
            texto += f" {valor}{texto_escala(self.dados.get('escala'))}"
        duracao = self.no_nivel("duracao", nivel) or dados.get("duracao")
        texto += f" por {duracao} turno{'s' if duracao != 1 else ''}"
        chance = self.no_nivel("chance", nivel, 1.0)
        if chance < 1:
            texto = f"{int(chance * 100)}% de chance: " + texto
        if self.dados.get("em") == "usuario":
            texto += " (em si)"
        if self.dados.get("so_familias"):
            from roguelike.dados import carregar
            nomes = carregar("regioes")["familias"]
            texto += " (só em " + ", ".join(nomes.get(f, f) for f in self.dados["so_familias"]) + ")"
        if self.dados.get("so_bandos"):
            texto += " (só em bandos)"
        return texto


class EfeitoEnergia(Efeito):
    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        quantidade = self.no_nivel("quantidade", nivel, 1)
        chance = self.no_nivel("chance", nivel, 1.0)
        for alvo in self.em_quem(usuario, alvos, contexto):
            if alvo.esta_vivo() and (chance >= 1 or combate.rng.random() < chance):
                combate.dar_energia(alvo, quantidade, motivo="habilidade")

    def resumo(self, nivel=1):
        texto = f"+{self.no_nivel('quantidade', nivel, 1)} de energia"
        chance = self.no_nivel("chance", nivel, 1.0)
        if chance < 1:
            texto = f"{int(chance * 100)}% de chance de " + texto
        if self.dados.get("em") == "usuario":
            texto += " (em si)"
        return texto


class EfeitoInvocar(Efeito):
    """Chama uma ou mais invocações para o lado do usuário."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        for _ in range(self.no_nivel("quantidade", nivel, 1)):
            combate.invocar(usuario, self.dados["invocacao"], nivel)

    def resumo(self, nivel=1):
        from roguelike.inimigos import ficha_de_invocacao
        nome = ficha_de_invocacao(self.dados["invocacao"])["nome"]
        quantidade = self.no_nivel("quantidade", nivel, 1)
        return f"invoca {quantidade}x {nome}" if quantidade > 1 else f"invoca {nome}"


class EfeitoPurificar(Efeito):
    """Remove status negativos."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        so = self.dados.get("so")                        # ex.: ["arma_desgastada"]: tira só esses
        for alvo in self.em_quem(usuario, alvos, contexto):
            if so:
                for chave in so:
                    combate.remover_status(alvo, chave)
            else:
                combate.purificar(alvo, self.no_nivel("quantidade", nivel, 99))

    def resumo(self, nivel=1):
        if self.dados.get("so"):
            return "remove " + ", ".join(dados_do_status(s)["nome"] for s in self.dados["so"])
        quantidade = self.no_nivel("quantidade", nivel, 99)
        return "remove todos os status negativos" if quantidade >= 99 else f"remove {quantidade} status negativo(s)"


class EfeitoReviver(Efeito):
    """Traz de volta um aliado caído com parte da vida."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        for alvo in alvos:
            combate.reviver(alvo, self.no_nivel("percentual", nivel, 0.5), usuario)

    def resumo(self, nivel=1):
        return f"revive com {int(self.no_nivel('percentual', nivel, 0.5) * 100)}% da vida"


class EfeitoFimDaFila(Efeito):
    """Arrasta o alvo para o fim da fila de turnos desta rodada (o Afogado puxa para o fundo)."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        from roguelike.eventos import Evento
        chance = self.no_nivel("chance", nivel, 1.0)
        for alvo in self.em_quem(usuario, alvos, contexto):
            if alvo.esta_vivo() and alvo in combate.fila and (chance >= 1 or combate.rng.random() < chance):
                combate.fila.remove(alvo)
                combate.fila.append(alvo)
                combate.registrar(Evento("aviso", usuario, alvo, texto=f"{alvo.nome} foi arrastado para o fim da fila!"))

    def resumo(self, nivel=1):
        chance = self.no_nivel("chance", nivel, 1.0)
        texto = "puxa o alvo para o fim da fila"
        return f"{int(chance * 100)}% de chance: {texto}" if chance < 1 else texto


class EfeitoRoubarItem(Efeito):
    """Rato Ladrão: leva 1 consumível da mochila de quem acertou (guardado em usuario.roubados).
    A passiva "fugir_com_roubo" decide o que acontece depois (fugir ou devolver ao cair)."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        from roguelike.eventos import Evento
        from roguelike.itens import item
        chance = self.no_nivel("chance", nivel, 1.0)
        for alvo in self.em_quem(usuario, alvos, contexto):
            inventario = getattr(alvo, "inventario", None)
            if inventario is None or not alvo.esta_vivo() or (chance < 1 and combate.rng.random() >= chance):
                continue
            consumiveis = sorted(c for c in inventario.itens if item(c).tipo == "consumivel")
            if not consumiveis:
                continue
            chave = combate.rng.choice(consumiveis)
            inventario.remover(chave)
            usuario.roubados = getattr(usuario, "roubados", []) + [(chave, alvo)]
            combate.registrar(Evento("roubo", usuario, alvo, texto=f"{usuario.nome} roubou {item(chave).nome} de {alvo.nome}!",
                                     item=chave))

    def resumo(self, nivel=1):
        chance = self.no_nivel("chance", nivel, 1.0)
        texto = "rouba 1 consumível da mochila"
        return f"{int(chance * 100)}% de chance: {texto}" if chance < 1 else texto


class EfeitoExplodir(Efeito):
    """O usuário se explode (Pavio Aceso do Rato Bombardeiro): cai na hora, e a passiva "ao_morrer" faz o resto."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        if usuario.esta_vivo():
            combate.morrer(usuario)

    def resumo(self, nivel=1):
        return "quem usa explode junto (cai na hora)"


class EfeitoEdito(Efeito):
    """Rei dos Ratos: proclama um Édito Real sorteado de "editos" (status de classe "edito" no regras.json), diferente
    do último. A lei fica nele e vale para os oponentes por "duracao" turnos dele, contando o turno da proclamação.

        {"tipo": "edito", "editos": ["edito_sem_cura", "edito_sem_magia", ...], "duracao": 2}
    """

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        from roguelike.eventos import Evento
        from roguelike.status import dados_do_status
        editos = self.dados["editos"]
        if any(s.intocavel() for s in usuario.status.values()):    # no trono ninguém o ataca: essa lei não vale nada
            editos = [c for c in editos if dados_do_status(c).get("proibe") != "atacar_dono"] or editos
        for chave in self.dados["editos"]:                      # uma lei por vez
            if usuario.tem_status(chave):
                combate.remover_status(usuario, chave)
        opcoes = [c for c in editos if c != getattr(usuario, "ultimo_edito", None)] or editos
        chave = combate.rng.choice(opcoes)
        usuario.ultimo_edito = chave
        status = combate.aplicar_status(usuario, chave, self.dados.get("duracao"), origem=usuario)
        if status is not None:
            status.pular_proximo_fim = False                    # o turno em que ele proclama já conta
            combate.registrar(Evento("edito", usuario, usuario, status.duracao, texto=f"Édito Real: {status.nome}!",
                                     status=chave))

    def resumo(self, nivel=1):
        return f"proclama um Édito Real (uma lei por {self.dados.get('duracao', 2)} turnos dele)"


class EfeitoRoubarOuro(Efeito):
    """Leva parte do ouro do grupo ("fracao" [mín, máx], no mínimo "minimo"), se o golpe acertou. Fica guardado em
    usuario.ouro_roubado: a passiva "devolver_ouro" devolve quando ele cai (o Imposto Real volta em dobro)."""

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        from roguelike.eventos import Evento
        grupo = combate.grupo
        if grupo is None or grupo.ouro <= 0 or (contexto.teve_dano and not contexto.acertados):
            return
        minimo, maximo = self.dados.get("fracao", [0.08, 0.12])
        quanto = min(grupo.ouro, max(self.dados.get("minimo", 5), round(grupo.ouro * combate.rng.uniform(minimo, maximo))))
        grupo.ouro -= quanto
        usuario.ouro_roubado = getattr(usuario, "ouro_roubado", 0) + quanto
        combate.registrar(Evento("roubo_de_ouro", usuario, usuario, quanto,
                                 texto=f"{usuario.nome} cobrou {quanto} de ouro em impostos!"))

    def resumo(self, nivel=1):
        minimo, maximo = self.dados.get("fracao", [0.08, 0.12])
        return f"leva {int(minimo * 100)}-{int(maximo * 100)}% do ouro do grupo"


class EfeitoReforcos(Efeito):
    """Chama inimigos novos de verdade para o lado do usuário (Combate.reforcar): os de "sempre" e mais 1 de "um_de".

        {"tipo": "reforcos", "sempre": ["rato_guarda_real"], "um_de": ["rato_comum"], "maximo_na_luta": 6}
    """

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        from roguelike.eventos import Evento
        chaves = list(self.dados.get("sempre", []))
        if self.dados.get("um_de"):
            chaves.append(combate.rng.choice(self.dados["um_de"]))
        if not combate.reforcar(usuario, chaves, limite_na_luta=self.dados.get("maximo_na_luta"),
                                texto=self.dados.get("texto", "{nome} atende ao chamado!")):
            combate.registrar(Evento("aviso", usuario, usuario, texto="Ninguém mais atende ao chamado."))

    def resumo(self, nivel=1):
        from roguelike.inimigos import ficha
        nomes = [ficha(c)["nome"] for c in self.dados.get("sempre", [])]
        if self.dados.get("um_de"):
            nomes.append("um reforço")
        return "chama " + " e ".join(nomes)


class EfeitoDevorar(Efeito):
    """O usuário come um aliado-objeto ("chave", ex.: o Queijo Real) e cura "cura" da vida máxima. Sem ele, nada.

        {"tipo": "devorar", "chave": "queijo_real", "cura": 0.3}
    """

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        from roguelike.eventos import Evento
        comida = next((a for a in combate.aliados_de(usuario) if getattr(a, "chave", None) == self.dados["chave"]), None)
        if comida is None:
            combate.registrar(Evento("aviso", usuario, usuario, texto="Não sobrou nada para comer!"))
            return
        combate.lado(comida).remove(comida)
        if comida in combate.fila:
            combate.fila.remove(comida)
        combate.registrar(Evento("devorou", usuario, comida, texto=f"{usuario.nome} devorou {comida.nome}!"))
        combate.curar(usuario, int(usuario.vida_maxima * self.dados.get("cura", 0.3)), usuario, motivo="banquete")

    def resumo(self, nivel=1):
        from roguelike.inimigos import ficha
        return f"come {ficha(self.dados['chave'])['nome']} e cura {int(self.dados.get('cura', 0.3) * 100)}% da vida"


class EfeitoDaRun(Efeito):
    """Efeito que só vale fora do combate, na run (Run.usar_fora_do_combate): no combate não faz nada.

        {"tipo": "novos_caminhos"}                                    Mapa Rasgado: sorteia outros caminhos
        {"tipo": "proximo_combate", "lado": "inimigos", "status": "amedrontado", "duracao": 2}   Incenso
    """

    def aplicar(self, combate, usuario, alvos, nivel, contexto):
        pass

    def resumo(self, nivel=1):
        if self.dados["tipo"] == "novos_caminhos":
            return "troca os caminhos à frente no mapa"
        lado = "os inimigos" if self.dados.get("lado", "inimigos") == "inimigos" else "o grupo"
        return f"o próximo combate começa com {lado} sob {self.dados.get('status', '')}"


TIPOS_DE_EFEITO = {
    "novos_caminhos": EfeitoDaRun,
    "proximo_combate": EfeitoDaRun,
    "dano": EfeitoDano,
    "cura": EfeitoCura,
    "status": EfeitoStatus,
    "energia": EfeitoEnergia,
    "invocar": EfeitoInvocar,
    "purificar": EfeitoPurificar,
    "reviver": EfeitoReviver,
    "fim_da_fila": EfeitoFimDaFila,
    "roubar_item": EfeitoRoubarItem,
    "explodir": EfeitoExplodir,
    "edito": EfeitoEdito,
    "roubar_ouro": EfeitoRoubarOuro,
    "reforcos": EfeitoReforcos,
    "devorar": EfeitoDevorar,
}


def criar_efeito(dados):
    try:
        return TIPOS_DE_EFEITO[dados["tipo"]](dados)
    except KeyError:
        raise ValueError(f"Tipo de efeito desconhecido: {dados.get('tipo')}") from None
