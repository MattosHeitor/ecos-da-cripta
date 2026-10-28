"""Inicia o roguelike.

    python src/jogar.py                         abre o jogo (título -> acampamento -> run)

Combate de teste (abre direto uma luta, sem mexer no seu progresso):
    python src/jogar.py --teste guerreiro,mago:criomante,sacerdote aranha,goblin,goblin_xama
    python src/jogar.py --teste ladino aranha_mae --nivel 6
    python src/jogar.py --teste guerreiro@draconiano,mago@revenante esqueleto,goblin    (herói@raça)
    python src/jogar.py --teste guerreiro enxame_de_ratos --regiao reino_dos_ratos --area 6     (área: zona e cenário)
    python src/jogar.py --teste guerreiro enxame_de_ratos --regiao reino_dos_ratos --area chefe (a sala do chefe)
    python src/jogar.py --teste guerreiro,sacerdote,mago - --regiao reino_dos_ratos --area corte --nivel 10
        (--area corte: o modo difícil da fase, ex.: A Corte Completa; os inimigos vêm do regioes.json)

Saves e opções ficam em %APPDATA%\\Ecos da Cripta (caminhos.py). Outro save, separado do principal:
    python src/jogar.py --perfil B              (ex.: duas cópias do jogo abertas no mesmo PC)

Conferir se o jogo abre (sem janela, com um save temporário; o construtor do instalador roda no .exe):
    python src/jogar.py --verificar relatorio.txt      (grava "ok" ou o erro; sai com 0 se deu tudo certo)
Um erro que fecha o jogo fica em erros.txt, na pasta do jogador.
"""

import argparse
import os
import random
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from caminhos import CAMINHOS, pasta_para_mostrar
from roguelike.classes import criar_heroi
from roguelike.encontros import EncontroCombate, MontadorDeCombate, descrever_inimigos
from roguelike.progresso import Progresso
from telas.base import App
from telas.combate.tela import TelaCombate

ITENS_DE_TESTE = {"pocao_de_vida": 2, "bomba_de_fogo": 1, "pergaminho_do_lobo": 1}


def criar_combate_de_teste(app, classes, inimigos, regiao, nivel, semente, area="1"):
    from roguelike.classes import classe as buscar_classe
    from roguelike.racas import todas_as_racas
    herois = []
    for chave in classes:
        chave, _, chave_raca = chave.partition("@")
        extra = None
        if ":" in chave:
            chave, extra = chave.split(":")
        subclasses = buscar_classe(chave).subclasses
        # "mago:criomante" escolhe a subclasse; "mago:Gelo" (nome antigo de aparência) usa a 1ª subclasse
        subclasse = extra if extra in subclasses else next(iter(subclasses))
        heroi = criar_heroi(chave, aparencia=None if extra in subclasses else extra, subclasse=subclasse)
        heroi.raca = chave_raca or "humano"
        herois.append(heroi)
    progresso = Progresso()
    progresso.racas_compradas = list(todas_as_racas())      # no teste, qualquer raça vale
    run = progresso.criar_run(herois, semente)
    run.regiao_atual = regiao
    for heroi in herois:
        for _ in range(nivel - 1):
            heroi.subir_nivel()
        while heroi.pontos_atributo > 0:
            for atributo in heroi.classe.atributos_principais:
                heroi.distribuir_ponto(atributo)
        heroi.curar_tudo()
        for chave, quantidade in ITENS_DE_TESTE.items():
            heroi.inventario.adicionar(chave, quantidade)
    run.perigo = max(0, nivel - 1)
    categoria = "combate"
    if area in ("chefe", "corte"):              # a área do chefe (com a sala do chefe da fase)
        run.area, categoria = run.areas_da_regiao(), "chefe"
    else:                                       # outra área: muda a variante do cenário (e a zona, no Reino dos Ratos)
        run.area = max(1, min(int(area), run.areas_da_regiao()))
    if area == "corte" and run.regiao.modo_dificil:      # o modo difícil da fase (inimigos e passivas do regioes.json)
        encontro = MontadorDeCombate(run.regiao, run.area, random.Random(1), len(herois)).modo_dificil()
    else:
        encontro = EncontroCombate("Combate de teste", descrever_inimigos(inimigos), 2, inimigos, categoria)

    def de_novo(recompensa):
        app.trocar(criar_combate_de_teste(app, classes, inimigos, regiao, nivel, None, area))

    return TelaCombate(app, run, encontro, de_novo)


def verificar(relatorio=None):
    """Abre sem janela o título, o acampamento e uma luta por alguns quadros, com um save temporário. Grava "ok"
    (ou o erro) em 'relatorio' e devolve 0 (ou 1). É como o construtor confere o .exe empacotado."""
    import tempfile
    os.environ["SDL_VIDEODRIVER"] = os.environ["SDL_AUDIODRIVER"] = "dummy"
    resultado, codigo = "ok", 0
    with tempfile.TemporaryDirectory() as pasta:
        CAMINHOS.usar_pasta_do_jogador(pasta)
        try:
            from telas import fluxo
            app = App(janela=False)
            app.progresso = Progresso.carregar()

            def quadros(quantos):
                for _ in range(quantos):
                    app.passo(1 / 30, [])
            fluxo.ir_para_titulo(app)
            quadros(15)
            fluxo.ir_para_acampamento(app)
            quadros(15)
            app.trocar(criar_combate_de_teste(app, ["guerreiro", "mago"], ["goblin", "aranha"], "floresta", 3,
                                              "VERIFICAR"))
            quadros(90)
            app.audio.tocar("clique")
            verificar_partida_em_grupo(app.progresso)
        except Exception:
            resultado, codigo = traceback.format_exc(), 1
    if relatorio:
        with open(relatorio, "w", encoding="utf-8") as arquivo:
            arquivo.write(resultado)
    else:
        print(resultado)
    return codigo


def verificar_partida_em_grupo(progresso, tempo=15.0):
    """Uma partida em grupo só neste PC (127.0.0.1: o firewall não pergunta): o outro entra, os dois ficam prontos e
    a run começa com o mesmo estado nos dois. RuntimeError se algo não acontecer a tempo."""
    from rede.partida import PartidaCliente, PartidaHost

    def esperar(condicao, *partidas):
        fim = time.monotonic() + tempo
        while time.monotonic() < fim:
            for partida in partidas:
                partida.atualizar()
            if condicao():
                return
            time.sleep(0.01)
        raise RuntimeError("A partida em grupo de teste não andou a tempo.")

    outro = Progresso()
    for cada in (progresso, outro):                       # um herói de cada (o grupo tem no máximo 5)
        cada.expedicao_atual().vagas = cada.expedicao_atual().vagas[:1]
    host = PartidaHost(progresso, "Host", (214, 72, 72), porta=0, endereco="127.0.0.1", porta_descoberta=False)
    convidado = PartidaCliente(outro, "Convidado", (86, 146, 226), "127.0.0.1", host.porta)
    try:
        esperar(lambda: convidado.no_lobby() and len(host.lobby.jogadores) == 2, host, convidado)
        host.marcar_pronto(True, progresso.pacote_para_partida())
        convidado.marcar_pronto(True, outro.pacote_para_partida())
        esperar(lambda: host.motivo_para_nao_iniciar() is None, host, convidado)
        host.iniciar("VERIFICAR")
        esperar(lambda: convidado.run is not None and host.sincronia.get(convidado.eu) is True, host, convidado)
    finally:
        convidado.fechar()
        host.fechar()


def registrar_erro():
    """O jogo vai fechar por um erro: guarda o motivo em erros.txt (pasta do jogador) para quem for consertar."""
    from versao import VERSAO
    try:
        os.makedirs(CAMINHOS.jogador, exist_ok=True)
        with open(CAMINHOS.save("erros.txt"), "a", encoding="utf-8") as arquivo:
            arquivo.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} · versão {VERSAO}\n{traceback.format_exc()}\n")
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Roguelike sombrio por turnos")
    parser.add_argument("--teste", nargs=2, metavar=("HEROIS", "INIMIGOS"), help="abre um combate de teste")
    parser.add_argument("--regiao", default="floresta")
    parser.add_argument("--nivel", type=int, default=1)
    parser.add_argument("--semente", default=None)
    parser.add_argument("--area", default="1", help="número da área (zona/cenário) ou 'chefe'")
    parser.add_argument("--perfil", default=None, help="save separado do principal (letras, números, - e _)")
    parser.add_argument("--verificar", nargs="?", const="", default=None, metavar="RELATORIO",
                        help="confere se o jogo abre (sem janela) e sai")
    argumentos = parser.parse_args()
    if argumentos.verificar is not None:
        sys.exit(verificar(argumentos.verificar or None))
    try:
        CAMINHOS.usar_perfil(argumentos.perfil)
    except ValueError as erro:
        parser.error(str(erro))
    trazidos = [] if argumentos.perfil else CAMINHOS.trazer_saves_antigos()   # 1ª vez: saves/ do projeto
    if trazidos:
        print(f"Saves copiados de {CAMINHOS.pasta_antiga()} para {CAMINHOS.jogador}: {', '.join(trazidos)}")

    app = App()
    app.progresso = Progresso.carregar()
    if trazidos:
        app.notificar("Saves no lugar novo", pasta_para_mostrar(CAMINHOS.jogador), som=None)
    if argumentos.teste:
        classes = argumentos.teste[0].split(",")
        inimigos = argumentos.teste[1].split(",")
        app.trocar(criar_combate_de_teste(app, classes, inimigos, argumentos.regiao, argumentos.nivel, argumentos.semente,
                                          argumentos.area))
    else:
        from telas.titulo import TelaTitulo
        app.trocar(TelaTitulo(app))
    app.rodar()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        registrar_erro()
        raise
