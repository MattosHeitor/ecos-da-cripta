"""Equipamentos de um herói: os 8 espaços do boneco + o consumível de uso automático.

O herói TEM um Equipamentos (composição). Aqui ficam as regras de equipar e o total de bônus:

    - cada peça só entra nos espaços dela (Arma/Armadura/Acessorio.espacos_possiveis);
    - classe e raça podem impedir a peça;
    - arma de duas mãos tira a arma secundária (e o contrário);
    - peça amaldiçoada trava o espaço até a próxima fogueira (liberar_malditos);
    - sets: bônus com 2, 3 e 4 peças do mesmo set equipadas.

Para o resto do código ele se comporta como o dicionário antigo: equipamento["arma"], .items()...
"""

from roguelike.dados import regras
from roguelike.sets import todos_os_sets


def espacos():
    return list(regras()["espacos"])


def nome_do_espaco(espaco):
    return regras()["nomes_espacos"].get(espaco, espaco)


class Equipamentos:
    def __init__(self, dono):
        self.dono = dono
        self.espacos = {espaco: None for espaco in espacos()}
        self.travados = set()                 # espaços com peça amaldiçoada (só soltam na fogueira)

    # ---------------- como dicionário ----------------
    def __getitem__(self, espaco):
        return self.espacos[espaco]

    def get(self, espaco, padrao=None):
        return self.espacos.get(espaco, padrao)

    def items(self):
        return self.espacos.items()

    def values(self):
        return self.espacos.values()

    def keys(self):
        return self.espacos.keys()

    def __iter__(self):
        return iter(self.espacos)

    def pecas(self):
        """[(espaço, peça)] equipadas (sem o consumível automático)."""
        return [(e, p) for e, p in self.espacos.items() if p is not None and p.tipo == "equipamento"]

    # ---------------- regras ----------------
    def espacos_para(self, objeto):
        if objeto.tipo == "consumivel":
            return ["consumivel"] if objeto.usavel_em_combate else []
        if objeto.tipo == "equipamento":
            return objeto.espacos_possiveis()
        return []

    def motivo_para_nao_equipar(self, objeto, espaco=None):
        """Texto curto explicando por que a peça não entra (ou None se pode)."""
        possiveis = self.espacos_para(objeto)
        if not possiveis:
            return "Não é equipável"
        if objeto.tipo == "equipamento":
            motivo = objeto.motivo_de_nao_servir(self.dono)
            if motivo:
                return motivo
        espaco = espaco or self.espaco_livre(objeto)
        if espaco not in possiveis:
            return "Não cabe nesse espaço"
        for afetado in self.espacos_afetados(objeto, espaco):
            if afetado in self.travados and self.espacos[afetado] is not None:
                return "Peça amaldiçoada presa até a próxima fogueira"
        return None

    def espaco_livre(self, objeto):
        possiveis = self.espacos_para(objeto)
        return next((e for e in possiveis if self.espacos[e] is None), possiveis[0] if possiveis else None)

    def arma_principal_de_duas_maos(self):
        arma = self.espacos.get("arma")
        return arma is not None and getattr(arma, "maos", 1) >= 2

    def espacos_afetados(self, objeto, espaco):
        """O espaço que recebe a peça e os que ela esvazia (duas mãos <-> mão secundária)."""
        afetados = [espaco]
        if espaco == "arma" and getattr(objeto, "maos", 1) >= 2 and self.espacos.get("arma_secundaria"):
            afetados.append("arma_secundaria")
        if espaco == "arma_secundaria" and self.arma_principal_de_duas_maos():
            afetados.append("arma")
        return afetados

    # ---------------- mudanças ----------------
    def equipar(self, objeto, espaco=None):
        """Coloca a peça. Devolve (deu_certo, [peças que saíram])."""
        espaco = espaco or self.espaco_livre(objeto)
        if self.motivo_para_nao_equipar(objeto, espaco) is not None:
            return False, []
        saiu = []
        for afetado in self.espacos_afetados(objeto, espaco):
            if self.espacos[afetado] is not None:
                saiu.append(self.espacos[afetado])
                self.espacos[afetado] = None
            self.travados.discard(afetado)
        self.espacos[espaco] = objeto
        if objeto.tipo == "equipamento" and objeto.travada():
            self.travados.add(espaco)
        return True, saiu

    def desequipar(self, espaco):
        """Tira a peça do espaço e a devolve (None se vazio ou se a peça amaldiçoada está presa)."""
        if espaco in self.travados or self.espacos.get(espaco) is None:
            return None
        peca, self.espacos[espaco] = self.espacos[espaco], None
        return peca

    def liberar_malditos(self):
        """Fogueira (Descanso Maior ou fase nova): as amaldiçoadas podem sair."""
        self.travados.clear()

    def esvaziar(self):
        """Tira tudo, até as amaldiçoadas (fim da run). Devolve as peças."""
        pecas = [p for p in self.espacos.values() if p is not None]
        self.espacos = {espaco: None for espaco in self.espacos}
        self.travados.clear()
        return pecas

    # ---------------- bônus ----------------
    def sets_ativos(self):
        """[(ConjuntoDeEquipamento, peças equipadas, [bônus ativos])] dos sets com pelo menos 1 peça."""
        contagem = {}
        for _, peca in self.pecas():
            if peca.set:
                contagem[peca.set] = contagem.get(peca.set, 0) + 1
        sets = todos_os_sets()
        return [(sets[c], n, sets[c].ativos(n)) for c, n in contagem.items() if c in sets]

    def modificadores(self):
        """Os dicionários de bônus: de cada peça e de cada bônus de set ativo."""
        fontes = [peca.modificadores for _, peca in self.pecas()]
        for _, _, ativos in self.sets_ativos():
            fontes.extend(b.modificadores for b in ativos)
        return fontes

    def passivas(self):
        """{origem: [dados de passiva]}: das peças e dos bônus de set."""
        resultado = {espaco: list(peca.passivas) for espaco, peca in self.pecas() if peca.passivas}
        for conjunto, _, ativos in self.sets_ativos():
            lista = [p for b in ativos for p in b.passivas]
            if lista:
                resultado["set:" + conjunto.chave] = lista
        return resultado

    # ---------------- salvar ----------------
    def para_dict(self):
        return {espaco: (peca.chave if peca else None) for espaco, peca in self.espacos.items()}
