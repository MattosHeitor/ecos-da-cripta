"""Elementos de dano (elementos.json): físico, fogo, gelo, raio, veneno, luz e sombra.

Cada golpe tem um elemento. O dano de um golpe é multiplicado por

    (1 + atacante.stat("dano_causado_<elemento>")) * (1 + alvo.stat("dano_recebido_<elemento>"))

As resistências dos inimigos (família + exceções) viram modificadores dano_recebido_<elemento>;
raças, itens e status usam os mesmos nomes. Valor positivo em dano_recebido = FRACO; negativo = RESISTE.
"""

from roguelike.dados import carregar, sem_comentarios

PADRAO = "fisico"
LIMIAR_EFETIVIDADE = 0.15          # a partir daqui a tela mostra "Fraco!" ou "Resistiu"
MULTIPLICADOR_MINIMO = 0.1         # nem a maior resistência zera o dano
RESISTENCIA_MAGICA_MAXIMA = 0.75   # "resistencia_magica" corta o dano dos elementos (não o físico)


def dados():
    return carregar("elementos")


def todos():
    """{elemento: {"nome", "cor"}} na ordem do JSON."""
    return sem_comentarios(dados()["elementos"])


def nome(elemento):
    return todos().get(elemento or PADRAO, {}).get("nome", elemento)


def cor(elemento):
    return tuple(todos().get(elemento or PADRAO, {}).get("cor", (226, 218, 204)))


def do_status(chave_status):
    """Elemento do dano por turno de um status (queimadura -> fogo), ou None."""
    return dados()["status"].get(chave_status)


def resistencias_do_inimigo(chave, familia=None, extras=None):
    """Soma as resistências da família, as exceções do inimigo e as da ficha ("resistencias")."""
    total = {}
    for fonte in (dados()["familias"].get(familia, {}), dados()["inimigos"].get(chave, {}), extras or {}):
        for elemento, valor in fonte.items():
            total[elemento] = round(total.get(elemento, 0) + valor, 3)
    return {e: v for e, v in total.items() if v}


def como_modificadores(resistencias):
    """{"fogo": 0.5} -> {"dano_recebido_fogo": 0.5} (para o stat() do lutador)."""
    return {f"dano_recebido_{elemento}": valor for elemento, valor in resistencias.items()}


def multiplicador(atacante, alvo, elemento):
    """Quanto o elemento muda o dano deste atacante neste alvo (atacante pode ser None)."""
    elemento = elemento or PADRAO
    fator = 1 + alvo.stat(f"dano_recebido_{elemento}")
    if atacante is not None:
        fator *= 1 + atacante.stat(f"dano_causado_{elemento}")
    if elemento != PADRAO:                       # magia (equipamento) e resistência mágica
        fator *= 1 - min(RESISTENCIA_MAGICA_MAXIMA, max(0.0, alvo.stat("resistencia_magica")))
        if atacante is not None:
            fator *= 1 + atacante.stat("dano_magico")
    return max(MULTIPLICADOR_MINIMO, fator)


def efetividade(alvo, elemento):
    """"fraco", "resiste" ou None, olhando só o alvo."""
    valor = alvo.stat(f"dano_recebido_{elemento or PADRAO}")
    if valor >= LIMIAR_EFETIVIDADE:
        return "fraco"
    if valor <= -LIMIAR_EFETIVIDADE:
        return "resiste"
    return None


def fraquezas_e_resistencias(lutador):
    """([elementos fracos], [elementos resistidos]) do lutador agora (para dicas e bestiário)."""
    fracos, resiste = [], []
    for elemento in todos():
        situacao = efetividade(lutador, elemento)
        if situacao == "fraco":
            fracos.append(elemento)
        elif situacao == "resiste":
            resiste.append(elemento)
    return fracos, resiste


def texto_de_afinidades(fracos, resiste):
    """Ex.: "Fraco a: luz, fogo · Resiste a: veneno" (vazio se não tiver nada)."""
    partes = []
    if fracos:
        partes.append("Fraco a: " + ", ".join(nome(e) for e in fracos))
    if resiste:
        partes.append("Resiste a: " + ", ".join(nome(e) for e in resiste))
    return " · ".join(partes)
