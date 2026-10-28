"""Ambientes de combate: o lugar também luta (Reino dos Ratos, docs/planos/reino_dos_ratos.md, etapa 2B).

    Ambiente            base: ganchos que o Combate chama (por padrão, nada muda)
    ├── AguaSubindo     a água sobe a cada N rodadas: Seca → Rasa → Funda → Alta
    └── Escuridao       sem luz, quem "some no escuro" não pode ser alvo de golpes de um alvo só

Cada zona escolhe os seus no regioes.json ("ambiente": [{"tipo": "agua", "sobe_a_cada": 5}, ...]);
os números padrão ficam em regras.json → "ambientes". O Combate chama:

    iniciar(combate)                          no começo da luta
    nova_rodada(combate)                      a cada rodada nova
    multiplicador_de_dano(atacante, alvo, elemento, combate)
    esquiva_extra(atacante, alvo, combate)    golpe às cegas num oculto: o alvo esquiva mais
    oculto(lutador, combate)                  não pode ser escolhido como alvo (se houver outro)
    depois_da_acao(lutador, habilidade, combate)   depois de cada golpe (ex.: o Rato Nadador vem à tona)

e a tela lê resumo() e descricao() para o painel do ambiente.
Inimigos que usam os ambientes (etapa 3): "nadador", "mergulha" e "some_no_escuro" na ficha.
"""

from roguelike.dados import regras
from roguelike.eventos import Evento


class Ambiente:
    tipo = "ambiente"
    nome = "Ambiente"

    def __init__(self, dados=None):
        self.dados = dict(dados or {})

    def regra(self):
        return regras()["ambientes"].get(self.tipo, {})

    def valor(self, chave):
        """Um número da zona (regioes.json) ou o padrão (regras.json)."""
        return self.dados.get(chave, self.regra().get(chave))

    def iniciar(self, combate):
        """No começo do combate."""

    def nova_rodada(self, combate):
        """A cada rodada nova (depois da iniciativa)."""

    def multiplicador_de_dano(self, atacante, alvo, elemento, combate):
        return 1.0

    def esquiva_extra(self, atacante, alvo, combate):
        return 0.0

    def oculto(self, lutador, combate):
        return False

    def depois_da_acao(self, lutador, habilidade, combate):
        """Depois de cada golpe usado no combate."""

    def resumo(self, combate):
        """Uma linha curta para o painel do combate."""
        return self.nome

    def descricao(self, combate):
        """O que este ambiente faz agora (a dica do painel)."""
        return ""

    def __repr__(self):
        return f"{type(self).__name__}({self.dados})"


class AguaSubindo(Ambiente):
    """A água sobe a cada N rodadas. Funda: o fogo enfraquece. Alta: o fogo enfraquece mais, os heróis ficam
    Encharcados (lentos) e os inimigos nadadores ficam à vontade (Nadando).

    Quem "mergulha" (Rato Nadador) fica submerso a partir de "mergulha_a_partir": oculto como no escuro. O golpe
    que ele dá saindo da água causa +"surpresa" de dano, e ele fica Na Superfície (visível) até o fim do próximo
    turno dele."""

    tipo = "agua"
    nome = "Água"
    ALTA = 3

    def __init__(self, dados=None):
        super().__init__(dados)
        self.nivel = min(self.ALTA, self.valor("nivel_inicial"))
        self.sobe_a_cada = max(1, self.valor("sobe_a_cada"))
        self.rodadas_ate_subir = self.sobe_a_cada

    @property
    def nome_do_nivel(self):
        return self.regra()["nomes"][self.nivel]

    @property
    def alta(self):
        return self.nivel >= self.ALTA

    def iniciar(self, combate):
        self.aplicar(combate)

    def nova_rodada(self, combate):
        if combate.rodada > 1 and not self.alta:              # a 1ª rodada só começa a contagem
            self.rodadas_ate_subir -= 1
            if self.rodadas_ate_subir <= 0:
                self.nivel += 1
                self.rodadas_ate_subir = self.sobe_a_cada
                texto = f"A água sobe: {self.nome_do_nivel}!"
                if self.nivel == self.valor("mergulha_a_partir") and self.submersos(combate):
                    texto += " Algo mergulhou..."
                combate.registrar(Evento("ambiente", texto=texto, ambiente=self.tipo, nivel=self.nivel))
        self.aplicar(combate)

    def aplicar(self, combate):
        """Na água alta: heróis Encharcados e nadadores Nadando (de novo a cada rodada, se alguém tirou)."""
        if not self.alta:
            return
        for heroi in combate.herois:
            if heroi.esta_vivo() and not heroi.tem_status("encharcado") and not heroi.imune("encharcado"):
                combate.aplicar_status(heroi, "encharcado")      # (imune: Botas de Esgoto, sem "Resistiu!" toda rodada)
        for inimigo in combate.inimigos:
            if inimigo.esta_vivo() and (getattr(inimigo, "ficha", None) or {}).get("nadador") \
                    and not inimigo.tem_status("nadando"):
                combate.aplicar_status(inimigo, "nadando")

    def menos_fogo(self):
        return self.regra()["fogo"][self.nivel]

    def multiplicador_de_dano(self, atacante, alvo, elemento, combate):
        multiplicador = 1.0 - self.menos_fogo() if elemento == "fogo" else 1.0
        if self.oculto(atacante, combate):                      # ataque surpresa, saindo da água
            multiplicador *= 1 + self.valor("surpresa")
        return multiplicador

    # ---------------- quem mergulha (Rato Nadador) ----------------
    def mergulha(self, lutador):
        return lutador.lado == "inimigos" and bool((getattr(lutador, "ficha", None) or {}).get("mergulha"))

    def funda_para_mergulhar(self):
        return self.nivel >= self.valor("mergulha_a_partir")

    def oculto(self, lutador, combate):
        return (lutador is not None and self.funda_para_mergulhar() and lutador.esta_vivo() and self.mergulha(lutador)
                and not lutador.tem_status("na_superficie"))

    def submersos(self, combate):
        return [i for i in combate.inimigos if self.oculto(i, combate)]

    def esquiva_extra(self, atacante, alvo, combate):
        return self.valor("esquiva_contra_submerso") if self.oculto(alvo, combate) else 0.0

    def depois_da_acao(self, lutador, habilidade, combate):
        """Quem mergulha e golpeia fica Na Superfície (pode ser alvo) até o fim do próximo turno dele."""
        if (self.funda_para_mergulhar() and self.mergulha(lutador) and lutador.esta_vivo() and habilidade.ofensiva()
                and not lutador.tem_status("na_superficie")):
            combate.aplicar_status(lutador, "na_superficie", origem=lutador)

    def resumo(self, combate):
        if self.alta:
            return f"Água: {self.nome_do_nivel}"
        return f"Água: {self.nome_do_nivel} · sobe em {self.rodadas_ate_subir}"

    def descricao(self, combate):
        partes = [f"A água sobe a cada {self.sobe_a_cada} rodadas (Rasa → Funda → Alta)."]
        if self.menos_fogo():
            partes.append(f"Agora: o fogo causa {int(self.menos_fogo() * 100)}% a menos.")
        if self.alta:
            partes.append("Água alta: os heróis ficam Encharcados (lentos) e os ratos nadadores ganham força.")
        else:
            partes.append("Na água alta os heróis ficam Encharcados e os ratos nadadores ganham força.")
        submersos = len(self.submersos(combate))
        if submersos:
            partes.append(f"{submersos} rato(s) submerso(s): só golpes em área os alcançam; o bote deles machuca mais.")
        return "\n".join(partes)


class Escuridao(Ambiente):
    """Sem luz, quem "some no escuro" não pode ser escolhido como alvo de golpes de um alvo só (golpes em área
    pegam). Luz: algum herói com lanterna ou tocha equipada (que fica Iluminado) ou com o status Iluminado."""

    tipo = "escuridao"
    nome = "Escuridão"

    def carrega_luz(self, heroi):
        """Uma peça equipada que ilumina (lanterna, tocha) ou o status Iluminado (vela, óleo de lamparina)."""
        if heroi.tem_status("iluminado"):
            return True
        equipamentos = getattr(heroi, "equipamentos", None)
        if equipamentos is None:
            return False
        from roguelike.visual_equipamento import visual_da_peca
        tipos = set(self.valor("luz"))
        return any((visual_da_peca(peca) or {}).get("tipo") in tipos for _, peca in equipamentos.pecas())

    def portadores_de_luz(self, combate):
        return [h for h in combate.herois if h.esta_vivo() and self.carrega_luz(h)]

    def tem_luz(self, combate):
        return bool(self.portadores_de_luz(combate))

    def iniciar(self, combate):
        self.acender(combate)
        ocultos = [i for i in combate.inimigos if self.oculto(i, combate)]
        if ocultos:
            combate.registrar(Evento("ambiente", texto=f"Algo se mexe no escuro... ({len(ocultos)} oculto(s))",
                                     ambiente=self.tipo))

    def nova_rodada(self, combate):
        self.acender(combate)

    def acender(self, combate):
        """Quem carrega lanterna ou tocha fica Iluminado (+precisão) enquanto durar a escuridão."""
        for heroi in combate.herois:
            if heroi.esta_vivo() and not heroi.tem_status("iluminado") and self.carrega_luz(heroi):
                combate.aplicar_status(heroi, "iluminado", 2)

    def some_no_escuro(self, lutador):
        return lutador.lado == "inimigos" and bool((getattr(lutador, "ficha", None) or {}).get("some_no_escuro"))

    def oculto(self, lutador, combate):
        return lutador.esta_vivo() and self.some_no_escuro(lutador) and not self.tem_luz(combate)

    def esquiva_extra(self, atacante, alvo, combate):
        return self.valor("esquiva_contra_oculto") if self.oculto(alvo, combate) else 0.0

    def resumo(self, combate):
        luz = self.portadores_de_luz(combate)
        if luz:
            return f"Escuridão · luz: {luz[0].nome}" + (f" +{len(luz) - 1}" if len(luz) > 1 else "")
        ocultos = sum(1 for i in combate.inimigos if self.oculto(i, combate))
        return f"Escuridão · {ocultos} oculto(s)" if ocultos else "Escuridão · sem luz"

    def descricao(self, combate):
        return ("Sem luz, alguns inimigos somem no escuro: não podem ser alvo de golpes de um alvo só (golpes em área "
                "acertam). Lanternas e tochas equipadas, velas e óleo de lamparina dão luz: revelam os ocultos e dão "
                "+precisão a quem carrega.")


TIPOS_DE_AMBIENTE = {"agua": AguaSubindo, "escuridao": Escuridao}


def criar_ambientes(lista):
    """[{"tipo": "agua", ...}, ...] (regioes.json, na zona) -> [Ambiente]."""
    ambientes = []
    for dados in lista or []:
        try:
            ambientes.append(TIPOS_DE_AMBIENTE[dados["tipo"]](dados))
        except KeyError:
            raise ValueError(f"Ambiente desconhecido: {dados.get('tipo')}") from None
    return ambientes
