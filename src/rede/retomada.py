"""Voltar a uma run em grupo: quem caiu volta para o mesmo ponto, e o host retoma a partida depois de fechar o jogo.

O Combate inteiro não é salvo (decisão 4 do plano): o host guarda a run num PONTO SEGURO (no mapa, sem luta, ondas
ou encontro em andamento) e os comandos aceitos desde então. Refazer esses comandos sobre a run do ponto dá
exatamente o estado de agora, até no meio de uma luta (as regras são determinísticas: mesma run + mesmos comandos =
mesmo estado, MP2).

    retomada = Retomada(run.para_dict())          # o começo da run já é um ponto seguro
    retomada.anotar(comando_em_dict, estado)      # cada comando aceito (no mapa, às vezes vira o ponto novo)
    run, sessao_refeita = retomada.refazer(...)   # quem volta: a run do ponto + os comandos = o estado de agora

O ponto só é trocado se a run vai e volta do JSON com a mesma impressão digital (senão fica o anterior).

A partida salva do host (partida_em_grupo.json na pasta do jogador) é a Retomada + quem estava no grupo (com a chave
de volta de cada um). Ela é regravada a cada comando aceito e apagada quando a run acaba.
"""

import copy
import json
import time

from caminhos import CAMINHOS, gravar_json

ARQUIVO_DA_PARTIDA = "partida_em_grupo.json"
VERSAO_DA_PARTIDA_SALVA = 1


def ponto_seguro(estado):
    """No mapa, sem luta, ondas nem encontro em andamento: a run sozinha (Run.para_dict) é o estado inteiro."""
    run = estado.run
    return (run is not None and not run.terminou() and run.estado == "escolha" and run.ondas is None
            and estado.condutor is None)


def impressao_da_run(dados):
    """A impressão digital de uma run carregada de 'dados' (sem combate)."""
    from roguelike.estado import EstadoDoJogo
    from roguelike.run import Run
    return EstadoDoJogo(Run.de_dict(copy.deepcopy(dados))).impressao_digital()


class Retomada:
    def __init__(self, base, seq_da_base=0, comandos=()):
        self.base = base                     # Run.para_dict() num ponto seguro
        self.seq_da_base = seq_da_base       # quantos comandos o host já tinha aceitado naquele ponto
        self.comandos = list(comandos)       # os aceitos depois (para_dict), em ordem

    @property
    def seq(self):
        return self.seq_da_base + len(self.comandos)

    def anotar(self, dados, estado, comandos_por_ponto=40):
        """Um comando aceito pelo host. No mapa, depois de fechar um encontro (ou de muitos comandos), vira o ponto novo."""
        self.comandos.append(dados)
        if ponto_seguro(estado) and (dados.get("tipo") == "concluir_encontro" or len(self.comandos) >= comandos_por_ponto):
            self.marcar(estado)

    def marcar(self, estado):
        """O estado de agora vira o ponto (se for seguro e a run for e voltar igual). Devolve True se marcou."""
        if not ponto_seguro(estado):
            return False
        base = json.loads(json.dumps(estado.run.para_dict(), ensure_ascii=False))
        if impressao_da_run(base) != estado.impressao_digital():
            return False                         # (algo da run não vai para o JSON aqui: fica o ponto anterior)
        self.base, self.seq_da_base, self.comandos = base, self.seq, []
        return True

    def refazer(self, comecar_run):
        """A run do ponto + os comandos: comecar_run(run) monta a sessão (Partida.comecar_run) e devolve a sessão,
        cujo processador refaz os comandos. Devolve a sessão no estado de agora; sessao.refeitos = [(comando,
        Resultado)] (o fluxo abre a tela certa e mostra nela o que aconteceu depois)."""
        from roguelike.run import Run
        run = Run.de_dict(copy.deepcopy(self.base))
        sessao = comecar_run(run)
        comandos = copy.deepcopy(self.comandos)
        resultados = sessao.processador.refazer(comandos, avancar_no_fim=False)   # (onde o host estava)
        sessao.refeitos = list(zip(comandos, resultados))
        sessao.seq = self.seq
        sessao.ultima_impressao = sessao.estado.impressao_digital()
        return sessao

    def para_dict(self):
        return {"base": self.base, "seq_da_base": self.seq_da_base, "comandos": self.comandos}

    @classmethod
    def de_dict(cls, dados):
        if not isinstance(dados, dict) or not isinstance(dados.get("base"), dict):
            raise ValueError("retomada sem a run")
        comandos = dados.get("comandos") or []
        if not isinstance(comandos, list) or not all(isinstance(c, dict) for c in comandos):
            raise ValueError("comandos inválidos")
        return cls(dados["base"], int(dados.get("seq_da_base", 0)), comandos)


# ============================================================
# A PARTIDA SALVA DO HOST
# ============================================================

def caminho_da_partida_salva():
    return CAMINHOS.save(ARQUIVO_DA_PARTIDA)


def salvar_partida(dados):
    dados = dict(dados, versao_do_arquivo=VERSAO_DA_PARTIDA_SALVA, salva_em=time.time())
    gravar_json(caminho_da_partida_salva(), dados)


def carregar_partida_salva():
    """A partida salva (dicionário) ou None (não há, ou é de outra versão do jogo / dos dados)."""
    from rede.protocolo import assinatura_dos_dados
    from versao import VERSAO
    try:
        with open(caminho_da_partida_salva(), encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or dados.get("versao_do_arquivo") != VERSAO_DA_PARTIDA_SALVA:
        return None
    if dados.get("versao") != VERSAO or dados.get("assinatura") != assinatura_dos_dados():
        return None                              # (o jogo mudou depois de salvar: a run não refaria igual)
    if not isinstance(dados.get("jogadores"), list) or not isinstance(dados.get("retomada"), dict):
        return None
    return dados


def apagar_partida_salva():
    import os
    for caminho in (caminho_da_partida_salva(), caminho_da_partida_salva() + ".tmp"):
        try:
            os.remove(caminho)
        except OSError:
            pass


def resumo_da_partida_salva(dados):
    """"Floresta Morta, área 3 · Ana, Bia · 20/10 21:14" para a tela de Jogar em grupo."""
    from roguelike.regioes import regiao as buscar_regiao
    base = dados["retomada"]["base"]
    try:
        lugar = f"{buscar_regiao(base['regiao_atual']).nome}, área {base['area']}"
    except (KeyError, TypeError):
        lugar = "run em andamento"
    nomes = ", ".join(str(j.get("nome", "?")) for j in dados["jogadores"] if isinstance(j, dict))
    quando = time.strftime("%d/%m %H:%M", time.localtime(dados.get("salva_em", time.time())))
    return f"{lugar} · {nomes} · {quando}"
