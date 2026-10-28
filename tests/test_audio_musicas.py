"""Fase 3, etapa 5: músicas geradas por código e os efeitos sonoros novos."""

import glob
import os
import re
import wave

import numpy as np

from audio import MUSICAS, PASTA_MUSICA, PASTA_EFEITOS, procurar, EXTENSOES_MUSICA, EXTENSOES_EFEITO

RAIZ = os.path.join(os.path.dirname(__file__), "..", "src")


def ler(caminho):
    with wave.open(caminho) as arquivo:
        return np.frombuffer(arquivo.readframes(arquivo.getnframes()), dtype=np.int16).astype(float) / 32767


def test_toda_musica_existe_e_tem_som():
    for nome in MUSICAS:
        caminho = procurar(PASTA_MUSICA, nome, EXTENSOES_MUSICA)
        assert caminho is not None, nome
        if caminho.endswith(".wav"):
            audio = ler(caminho)
            assert len(audio) > 22050 * 5 and 0.05 < np.sqrt(np.mean(audio ** 2)) < 0.35, nome


def test_loops_emendam_sem_estalo():
    for nome in ("titulo", "acampamento", "floresta", "minas", "catedral", "circo", "chefe"):
        audio = ler(procurar(PASTA_MUSICA, nome, (".wav",)))
        assert abs(audio[-1] - audio[0]) < 0.05, nome


def test_chefes_com_tema_proprio():
    from roguelike.inimigos import fichas
    temas = {chave: f["musica"] for chave, f in fichas().items() if "musica" in f}
    assert temas == {"mercador_mascarado": "mercador", "primeiro_heroi": "primeiro_heroi",
                     "rei_dos_ratos": "reino_rei", "rainha_dos_ratos": "reino_rainha"}   # (temas próprios: etapa 7C)
    assert set(temas.values()) <= set(MUSICAS)
    for nome in ("cidadela", "eclipse", "mercador", "primeiro_heroi", "reino_rei", "reino_rainha"):
        audio = ler(procurar(PASTA_MUSICA, nome, (".wav",)))
        assert abs(audio[-1] - audio[0]) < 0.05, nome


def test_todo_efeito_pedido_pelo_codigo_existe():
    """Procura app.audio.tocar("...") e os sons do combate no código e confere o arquivo de cada um."""
    pedidos = set()
    for arquivo in glob.glob(os.path.join(RAIZ, "**", "*.py"), recursive=True):
        texto = open(arquivo, encoding="utf-8").read()
        pedidos |= set(re.findall(r'audio\.tocar\("([a-z_]+)"', texto))
        pedidos |= set(re.findall(r'som="([a-z_]+)"', texto))
    pedidos |= {"golpe", "critico", "bloqueio", "fraco", "resistente", "metamorfose", "rugido", "renascer", "nivel",
                "vitoria", "derrota", "esquiva", "cura", "status", "morte", "invocar", "item", "magia", "navegar"}
    pedidos |= {f"elemento_{e}" for e in ("fogo", "gelo", "raio", "veneno", "luz", "sombra")}
    faltando = [nome for nome in sorted(pedidos) if procurar(PASTA_EFEITOS, nome, EXTENSOES_EFEITO) is None]
    assert not faltando, faltando


def test_cada_golpe_tem_um_som_de_ataque_que_existe():
    from roguelike.golpes import golpe, todas_as_chaves
    from telas.combate.sons import som_do_golpe
    sons = {chave: som_do_golpe(golpe(chave)) for chave in todas_as_chaves()}
    assert sons["bola_de_fogo"] == "ataque_fogo" and sons["descarga"] == "ataque_trovao"
    assert sons["lanca_de_gelo"] == "ataque_gelo" and sons["flecha"] == "ataque_flecha"
    assert sons["punhalada"] == "ataque_lamina" and sons["palma_aberta"] == "ataque_soco"
    assert sons["acorde_cortante"] == "ataque_musica" and sons["cura_sagrada"] == "ataque_cura"
    for chave, som in sons.items():
        assert som and procurar(PASTA_EFEITOS, som, EXTENSOES_EFEITO), (chave, som)
