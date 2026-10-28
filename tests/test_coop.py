"""MP6: batalha co-op e run compartilhada.

O critério de aceite: uma run de 2 jogadores até o primeiro chefe, com estados idênticos nas duas telas. Aqui são
duas App de verdade (as telas do jogo, sem janela) no mesmo processo, ligadas por 127.0.0.1: cada uma vota no
mapa e nos eventos, confirma as recompensas e joga os SEUS heróis pela tela de combate (com o DecisorIA no lugar da
pessoa). A cada mapa, as duas impressões digitais têm de ser iguais.
"""

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelike.condutor import DecisorIA
from roguelike.dados import regras
from roguelike.progresso import Progresso
from rede.partida import PartidaCliente, PartidaHost
from rede.votacao import Votacao

LOCAL = "127.0.0.1"
SEMENTE = "COOP"                     # (a run do teste é sempre a mesma: os votos, o loot e as lutas saem dela)


# ---------------- votação (lógica) ----------------
def test_votacao_maioria_empate_e_tempo():
    votacao = Votacao("caminho|x", [0, 1, 2], prazo=30)
    votacao.votar("j1", 1)
    votacao.votar("j2", 1)
    votacao.votar("j3", 2)
    assert not votacao.votar("j4", 7)                         # opção que não existe não conta
    assert votacao.vencedora() == 1 and votacao.decidida(["j1", "j2", "j3"])
    assert not votacao.decidida(["j1", "j2", "j3", "j4"]) and votacao.faltam(["j1", "j4"]) == ["j4"]
    empate = Votacao("caminho|y", [0, 1, 2], prazo=30, votos={"j1": 0, "j2": 2})
    assert empate.vencedora() in (0, 2) and empate.vencedora() == Votacao("caminho|y", [0, 1, 2], 30,
                                                                          {"j1": 0, "j2": 2}).vencedora()
    assert Votacao("z", [0, 1], prazo=0).decidida(["j1"])     # o tempo acabou: decide mesmo sem votos
    assert Votacao("z", [0, 1], prazo=0).vencedora() in (0, 1)


def esperar(condicao, *partidas, tempo=6.0):
    fim = time.monotonic() + tempo
    while time.monotonic() < fim:
        for partida in partidas:
            partida.atualizar()
        if condicao():
            return True
        time.sleep(0.01)
    return False


def test_votacao_pela_rede_e_o_relogio_do_seguir():
    host = PartidaHost(Progresso(), "Ana", (214, 72, 72), porta=0, endereco=LOCAL, porta_descoberta=False)
    bia = PartidaCliente(Progresso(), "Bia", (86, 146, 226), LOCAL, host.porta)
    try:
        assert esperar(lambda: bia.no_lobby(), host, bia)
        host.estado = bia.estado = "jogando"                   # (as votações só valem durante a run)
        decidido = []
        bia.votar("caminho|a", 2)                              # chegou antes da tela do host: fica guardado
        assert esperar(lambda: host.votos_de("caminho|a") == {"j2": 2}, host, bia)
        host.abrir_votacao("caminho|a", [0, 1, 2], decidido.append)
        host.votar("caminho|a", 2)
        assert esperar(lambda: decidido == [2] and bia.decidida("caminho|a") == 2, host, bia)
        host.votar("caminho|a", 0)                             # voto atrasado: não reabre
        assert decidido == [2]
        host.abrir_votacao("seguir|loja", [0], decidido.append, prazo=0.2, esperar_primeiro_voto=True)
        time.sleep(0.3)
        assert esperar(lambda: True, host) and decidido == [2]          # ninguém votou: o relógio nem começou
        bia.votar("seguir|loja", 0)
        assert esperar(lambda: decidido == [2, 0], host, bia)            # o primeiro voto liga o relógio (0,2 s)
    finally:
        bia.fechar()
        host.fechar()


# ---------------- a run inteira pelas telas ----------------
class Jogador:
    """Uma App (as telas) com a sua partida, jogando sozinha: vota, confirma e deixa a IA escolher pelos seus
    heróis no combate (como uma pessoa faria pela tela)."""

    ORDEM = {"comum": 0, "incomum": 1, "raro": 2, "epico": 3, "lendario": 4, "amaldicoado": -1}

    def __init__(self, app, desempate):
        self.app = app
        self.desempate = desempate                             # 0 ou -1: quando há duas boas, cada um vota numa
        self.esperando = None                                  # o tamanho do registro quando mandei o último comando

    @property
    def partida(self):
        return self.app.partida

    def meus_feitos(self):
        """Quantos comandos meus já aconteceram (+ quantos o host recusou)."""
        sessao = self.partida.sessao
        return sum(1 for d in sessao.processador.registro if d.get("jogador") == self.partida.eu) + \
            getattr(sessao, "recusas", 0)

    def mandar(self, tela, comando):
        """Um comando por vez (em quem entrou, o estado só muda quando o host devolver)."""
        antes = self.meus_feitos()
        if tela.enviar(comando):
            self.esperando = antes
            return True
        return False

    def cuidar_dos_meus(self, tela):
        """Pontos de atributo e de habilidade e as melhores peças da mochila nos MEUS heróis. True se mandou algo."""
        from roguelike.comandos import DistribuirPonto, Equipar, MelhorarHabilidade
        sessao = self.partida.sessao
        if self.esperando is not None and self.meus_feitos() <= self.esperando:
            return True                                        # (o último ainda não voltou do host)
        self.esperando = None
        estado = sessao.estado
        meus = [h for h in tela.run.grupo.herois if h.jogador.id == self.partida.eu]
        for heroi in meus:
            numero = estado.indice_do(heroi)
            if heroi.pontos_atributo > 0:
                return self.mandar(tela, DistribuirPonto(heroi=numero, atributo=heroi.classe.atributos_principais[0]))
            melhoraveis = [h.chave for h, _ in heroi.habilidades() if heroi.pode_melhorar(h.chave)]
            if heroi.pontos_habilidade > 0 and melhoraveis:
                return self.mandar(tela, MelhorarHabilidade(heroi=numero, chave=melhoraveis[0]))
            for objeto, _ in sorted(heroi.inventario.pilhas("equipamento"), key=lambda p: -self.ORDEM[p[0].raridade]):
                espacos = objeto.espacos_possiveis()
                pior = min(espacos, key=lambda e: self.ORDEM[heroi.equipamento[e].raridade] if heroi.equipamento[e] else -2)
                atual = heroi.equipamento[pior]
                if self.ORDEM[objeto.raridade] > (self.ORDEM[atual.raridade] if atual else -2) and \
                        heroi.equipamentos.motivo_para_nao_equipar(objeto, pior) is None:
                    if self.mandar(tela, Equipar(heroi=numero, chave=objeto.chave, origem=numero, espaco=pior)):
                        return True
        return False

    def escolher_caminho(self, tela):
        """Descanso com o grupo ferido; senão a luta mais fácil (empate entre as boas: cada um vota numa)."""
        opcoes = tela.run.opcoes_de_encontro()
        validas = [i for i, o in enumerate(opcoes) if not getattr(o, "bloqueado", False)]
        vivos = tela.run.grupo.vivos()
        ferido = sum(h.fracao_vida() for h in vivos) / max(1, len(vivos)) < 0.6
        descanso = [i for i in validas if opcoes[i].tipo in ("descanso", "altar")]
        if (ferido or tela.run.grupo.caidos()) and descanso:
            return descanso[0]
        lutas = sorted((i for i in validas if opcoes[i].eh_combate()), key=lambda i: opcoes[i].estrelas)
        boas = [i for i in lutas if opcoes[i].estrelas == opcoes[lutas[0]].estrelas] if lutas else validas
        return boas[self.desempate]

    def jogar(self):
        from telas import em_grupo
        tela, nome = self.app.atual, type(self.app.atual).__name__
        partida = self.partida
        if partida is None or partida.sessao is None:
            return
        sessao = partida.sessao
        if not sessao.decisores:                               # os meus heróis: a IA escolhe por mim
            sessao.decisores = {i: DecisorIA() for i, h in enumerate(partida.run.grupo.herois)
                                if h.jogador.id == partida.eu}
        if nome == "TelaTituloDaArea" and tela.tempo > 0.4:
            tela.seguir()
        elif nome == "TelaMapa":
            chave = tela.chave_do_caminho()
            if em_grupo.meu_voto(tela, chave) is None and not self.cuidar_dos_meus(tela):
                tela.escolher(self.escolher_caminho(tela))
        elif nome == "TelaEvento":
            tela.narracao.pular()
            if tela.resultado is None:
                if em_grupo.meu_voto(tela, tela.chave()) is None:
                    tela.escolher(tela.opcoes_validas()[0])
            elif em_grupo.meu_voto(tela, tela.chave("seguir")) is None:
                tela.continuar()
        elif nome == "TelaLoja" and em_grupo.meu_voto(tela, tela.chave_de_seguir()) is None:
            tela.sair()
        elif nome == "TelaServico" and em_grupo.meu_voto(tela, tela.chave()) is None:
            (tela.ignorar_passagem if tela.encontro.tipo == "entrada" else tela.seguir)()
        elif nome == "TelaEntreOndas":
            tela.narracao.pular()
            chave = tela.chave("seguir") if tela.resultado is not None else tela.chave()
            if em_grupo.meu_voto(tela, chave) is None:
                (tela.seguir if tela.resultado is not None else
                 tela.encerrar if tela.ondas.terminou() else tela.continuar_lutando)()
        elif nome == "TelaCombate" and tela.estado == "fim" and not tela.fila:
            if em_grupo.meu_voto(tela, tela.chave_de_seguir()) is None:
                tela.seguir_em_grupo()


def criar_app(tmp_path, nome):
    from telas.base import App
    app = App(janela=False)
    app.tela = app.janela = pygame.Surface((1280, 720))        # (cada App desenha na sua)
    app.progresso = Progresso.carregar(str(tmp_path / f"progresso_{nome}.json"))
    app.velocidade = 4.0
    return app


class Dupla:
    """A Ana (host) e a Bia, cada uma com a sua App, do lobby até a run começar (fase curta, heróis de nível 5)."""

    def __init__(self, tmp_path, ia_da_bia=True):
        from telas import comum, fluxo
        from telas.lobby import resumos_da_expedicao
        comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
        self.host_app, self.bia_app = criar_app(tmp_path, "ana"), criar_app(tmp_path, "bia")
        for app, classes in ((self.host_app, ("guerreiro", "sacerdote", "patrulheira")), (self.bia_app, ("mago", "bardo"))):
            expedicao = app.progresso.expedicao_atual()
            expedicao.vagas = []
            for classe in classes:
                expedicao.adicionar(classe, __import__("random").Random(len(expedicao.vagas)))
        self.host_app.progresso.expedicao_atual().semente = SEMENTE
        self.host_app.partida = PartidaHost(self.host_app.progresso, "Ana", (214, 72, 72), porta=0, endereco=LOCAL,
                                            porta_descoberta=False)
        self.bia_app.partida = PartidaCliente(self.bia_app.progresso, "Bia", (86, 146, 226), LOCAL,
                                              self.host_app.partida.porta, resumos_da_expedicao(self.bia_app))
        self.apps = (self.host_app, self.bia_app)
        self.jogadores = (Jogador(self.host_app, 0), Jogador(self.bia_app, -1))
        self.host, self.bia = self.host_app.partida, self.bia_app.partida
        fluxo.ir_para_acampamento(self.host_app)
        assert self.rodar(lambda: self.bia.no_lobby(), 10)
        fluxo.ir_para_acampamento(self.bia_app)
        for app in self.apps:
            app.passo(0.1, [])
            app.atual.alternar_pronto()
        assert self.rodar(lambda: self.host.motivo_para_nao_iniciar() is None, 10)
        assert self.host_app.atual.iniciar() is None
        assert self.rodar(lambda: self.bia.run is not None and type(self.bia_app.atual).__name__ == "TelaTituloDaArea", 10)
        for partida in (self.host, self.bia):             # (o teste caber no tempo: uma fase curta e heróis
            run = partida.run                             #  de nível 5, do mesmo jeito nos dois computadores)
            run.tamanhos[run.regiao_atual] = 5
            for heroi in run.grupo.herois:
                for _ in range(4):
                    heroi.subir_nivel()
                heroi.curar_tudo()
        assert self.bia.sessao.estado.impressao_digital() == self.host.sessao.estado.impressao_digital()

    def passo(self, quem=None):
        for jogador, app in zip(self.jogadores, self.apps):
            if quem is None or app in quem:
                jogador.jogar()
                app.passo(0.1, [])

    def rodar(self, condicao, segundos, quem=None):
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            self.passo(quem)
            if condicao():
                return True
        return False

    def mesmo_estado(self):
        return self.bia.sessao.seq == self.host.sessao.seq and not self.bia.sessao.fila and \
            self.bia.sessao.estado.impressao_digital() == self.host.sessao.estado.impressao_digital()

    def fechar(self):
        from telas import comum
        for app in self.apps:
            if app.partida is not None and not app.partida.encerrada:
                app.partida.fechar()
        comum.ArquivoDaRun.caminho = None


def test_run_de_dois_jogadores_ate_o_primeiro_chefe(tmp_path):
    """O critério de aceite da MP6."""
    dupla = Dupla(tmp_path)
    host, bia, apps = dupla.host, dupla.bia, dupla.apps
    try:
        comparados, telas_vistas = 0, set()
        fim = time.monotonic() + 300
        while time.monotonic() < fim:
            dupla.passo()
            telas_vistas |= {type(a.atual).__name__ for a in apps}
            run_do_host = host.run
            if run_do_host is None or run_do_host.terminou() or run_do_host.estatisticas["chefes"]:
                break
            if all(type(a.atual).__name__ == "TelaMapa" for a in apps) and not bia.sessao.fila and \
                    host.sessao.seq == bia.sessao.seq and apps[1].atual.run.area == apps[0].atual.run.area:
                assert bia.sessao.estado.impressao_digital() == host.sessao.estado.impressao_digital()
                comparados += 1
        run = host.run
        assert run is not None, "a run acabou antes do chefe"
        assert run.estatisticas["chefes"], f"não venceu o chefe (área {run.area}, {run.resultado})"
        assert dupla.rodar(dupla.mesmo_estado, 30)
        assert bia.sessao.divergiu is None and comparados >= 3
        assert {"TelaMapa", "TelaCombate"} <= telas_vistas
        do_host, da_bia = host.sessao.processador.registro, bia.sessao.processador.registro
        diferente = next((i for i, (a, b) in enumerate(zip(do_host, da_bia)) if a != b), None)
        assert len(do_host) == len(da_bia) and diferente is None, \
            (len(do_host), len(da_bia), diferente, diferente is not None and (do_host[diferente], da_bia[diferente]))
        donos = {d["jogador"] for d in host.sessao.processador.registro if d["tipo"] == "agir_no_combate"}
        assert donos == {"j1", "j2"}                         # cada um jogou com os seus heróis
    finally:
        dupla.fechar()


def test_portoes_do_fim_do_ato_sao_votados_e_o_grupo_segue(tmp_path):
    """Vencido o chefe, o grupo vota no portão do próximo ato. A votação do chefe (mesma fase e mesma área) já foi
    decidida: os votos do portão não podem cair nela (o grupo ficava parado no mapa)."""
    from telas import fluxo
    from telas.mapa import TelaMapa
    dupla = Dupla(tmp_path)
    try:
        inicio = dupla.host.run.regiao_atual
        for partida, app in ((dupla.host, dupla.host_app), (dupla.bia, dupla.bia_app)):
            run = partida.run                                 # (igual nos dois: o chefe vencido, os portões abertos)
            run.area = run.tamanhos[run.regiao_atual]
            if partida.eh_host:                               # a votação do chefe, já decidida
                partida.decididas.append(TelaMapa(app, run).chave_do_caminho())
            run.portoes = [["minas", True], ["pantano_dos_afogados", True]]
            run.opcoes = None
            fluxo.ir_para_mapa(app, run)
        assert dupla.mesmo_estado()
        assert dupla.rodar(lambda: dupla.host.run.regiao_atual != inicio and dupla.mesmo_estado() and
                           all(type(a.atual).__name__ == "TelaMapa" for a in dupla.apps), 60)
        assert dupla.host.run.regiao_atual in ("minas", "pantano_dos_afogados") and dupla.host.run.portoes is None
    finally:
        dupla.fechar()


def ate_a_luta(dupla):
    return dupla.rodar(lambda: all(type(a.atual).__name__ == "TelaCombate" for a in dupla.apps), 60)


def test_quem_demora_na_vez_passa_para_a_ia(tmp_path, monkeypatch):
    """A Bia para de jogar no meio da luta (a tela dela congela): na vez dos heróis dela, o host espera
    tempo_da_vez e a IA joga por ela. Quando a Bia volta, alcança o mesmo estado."""
    dupla = Dupla(tmp_path)
    try:
        assert ate_a_luta(dupla)
        monkeypatch.setitem(regras()["multiplayer"], "tempo_da_vez", 0.5)
        host = dupla.host
        da_ia = lambda: [d for d in host.sessao.processador.registro if d["tipo"] == "agir_no_combate"
                         and d["jogador"] == "j2"]
        antes = len(da_ia())
        assert dupla.rodar(lambda: len(da_ia()) >= antes + 2, 30, quem=[dupla.host_app])   # só o host roda
        assert dupla.rodar(dupla.mesmo_estado, 30)                                          # a Bia volta e alcança
    finally:
        dupla.fechar()


def test_quem_cai_no_meio_da_luta_vira_ia_e_o_grupo_segue(tmp_path):
    dupla = Dupla(tmp_path)
    try:
        assert ate_a_luta(dupla)
        dupla.bia.conexao.fechar()                          # caiu (sem tchau)
        host = dupla.host
        assert dupla.rodar(lambda: "j2" in host.desconectados, 10, quem=[dupla.host_app])
        area = host.run.area
        assert dupla.rodar(lambda: host.run.area > area or host.run.terminou(), 120, quem=[dupla.host_app])
        agiu_pela_bia = [d for d in host.sessao.processador.registro if d["tipo"] == "agir_no_combate"
                         and d["jogador"] == "j2"]
        assert agiu_pela_bia                                 # a IA jogou com os heróis da Bia
        assert any("Bia caiu" in m.texto for m in host.lobby.chat)
    finally:
        dupla.fechar()
