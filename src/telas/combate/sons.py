"""Qual som cada golpe faz ao ser lançado (assets/sons/efeitos/ataque_*.wav).

Golpes mágicos soam pelo elemento (fogo ruge, raio troveja, gelo cristaliza...). Os físicos, pelo
tipo de arma que o nome sugere (arco, lâmina, martelo, punho, garra, canção, bomba). Um golpe pode
escolher o próprio som no habilidades.json com "som": "ataque_trovao".
"""

from roguelike.elementos import PADRAO

SOM_DO_ELEMENTO = {"fogo": "ataque_fogo", "gelo": "ataque_gelo", "raio": "ataque_trovao", "veneno": "ataque_veneno",
                   "luz": "ataque_luz", "sombra": "ataque_sombra"}

# (pedaços da chave do golpe, som) — o primeiro que combinar vale
SOM_POR_NOME = [
    (("bomba", "explos", "granada", "confete", "meteoro"), "ataque_explosao"),
    (("flecha", "tiro", "saraivada", "disparo", "chuva_de_mil"), "ataque_flecha"),
    (("acorde", "cancao", "melodia", "hino", "nota", "lamento", "aria", "balada", "sussurro", "refrao",
      "marcha", "requiem", "canto"), "ataque_musica"),
    (("soco", "punho", "palma", "chute", "punhos", "cabecada"), "ataque_soco"),
    (("mordida", "garra", "arranh", "bicada", "picada", "ferrao", "mandib", "lingua", "frenesi_animal"), "ataque_garra"),
    (("martelo", "escudo", "pancada", "esmagar", "pisao", "terremoto", "clava", "pesado", "tita", "investida",
      "malabares", "tropeco", "soco_de_pedra", "cajado"), "ataque_impacto"),
    (("faca", "punhal", "adaga", "estocada", "lamina", "corte", "execucao", "cortes", "golpe_baixo", "ferida"),
     "ataque_lamina"),
]


def som_do_golpe(golpe):
    """Nome do efeito que acompanha o golpe (ou None)."""
    escolhido = getattr(golpe, "som", None)
    if escolhido:
        return escolhido
    if not golpe.ofensiva():
        if golpe.tem_efeito("invocar"):
            return "invocar"
        if golpe.tem_efeito("cura") or golpe.tem_efeito("reviver"):
            return "ataque_cura"
        return "ataque_bencao"
    if golpe.elemento != PADRAO:
        return SOM_DO_ELEMENTO.get(golpe.elemento, "ataque_espada")
    if not golpe.tem_efeito("dano"):
        return "ataque_maldicao"                  # golpe que só amaldiçoa/enfraquece
    for pedacos, som in SOM_POR_NOME:
        if any(p in golpe.chave for p in pedacos):
            return som
    return "ataque_espada"
