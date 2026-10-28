"""Como o equipamento aparece no herói (só visual; dados/visual_equipamentos.json).

Cada peça vira uma ou mais camadas "eq_<tipo>:rrggbb" no nome do sprite, com a cor da peça em
hexadecimal. visual/sprites_macabros.py junta as camadas na roupa (capas e estandarte atrás, o resto
por cima, na ordem do corpo: pernas, tronco, pescoço, cabeça, mãos) e tinge cada uma com a cor.
Com arma equipada a roupa troca para a versão desarmada: a arma de verdade vem na camada.

    "guerreiro_berserker_desarmado+@eq_placas:404c4c+@eq_espada:d4def2"
"""

from roguelike.dados import carregar, sem_comentarios

# ordem em que as camadas são coladas (de baixo para cima)
ORDEM = ("calcas", "botas", "peitoral", "amuleto", "capa", "cabeca", "arma_secundaria", "arma")
ESPACOS_DE_ARMA = ("arma", "arma_secundaria")
COM_GOLA = {"capa": "capa_gola", "manto": "manto_gola"}       # a capa fica atrás; a gola, na frente
SEM_TINTA = {"elmo_ossudo": "elmo_cavaleiro_ossudo"}          # desenhos com cor própria


def dados():
    return carregar("visual_equipamentos")


def visual_da_peca(peca):
    """{"tipo", "cor"?} da peça (exemplares com afixos usam a ficha de origem), ou None."""
    return sem_comentarios(dados()["pecas"]).get(getattr(peca, "base", peca.chave))


def cor_da_peca(peca, visual):
    """A cor própria da peça; sem ela, a do set; sem set, a da raridade. Em hexadecimal."""
    d = dados()
    cor = visual.get("cor") or d["cores_set"].get(peca.set) or d["cores_raridade"].get(peca.raridade, (150, 150, 150))
    return "%02x%02x%02x" % tuple(cor)


def camadas_da_peca(peca, espaco):
    visual = visual_da_peca(peca)
    if visual is None:
        return []
    tipo = visual["tipo"]
    if tipo in SEM_TINTA:
        return [SEM_TINTA[tipo]]
    if espaco == "arma_secundaria":                       # arma leve na outra mão
        tipo = dados()["na_outra_mao"].get(tipo, tipo)
    cor = cor_da_peca(peca, visual)
    nomes = ["eq_" + tipo] + (["eq_" + COM_GOLA[tipo]] if tipo in COM_GOLA else [])
    return [f"{nome}:{cor}" for nome in nomes]


def camadas_do_equipamento(equipamentos, sem_cabeca=False):
    """As camadas de todas as peças equipadas, na ordem de colar. sem_cabeca: a skin de chapéu manda."""
    por_espaco = dict(equipamentos.pecas())
    camadas = []
    for espaco in ORDEM:
        peca = por_espaco.get(espaco)
        if peca is not None and not (sem_cabeca and espaco == "cabeca"):
            camadas += camadas_da_peca(peca, espaco)
    return camadas


def tem_arma(equipamentos):
    """Com arma equipada, a roupa do herói vem sem a arma da classe (a da peça é que aparece)."""
    return any(equipamentos.get(espaco) is not None and visual_da_peca(equipamentos.get(espaco))
               for espaco in ESPACOS_DE_ARMA)
