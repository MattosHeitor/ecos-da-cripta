"""Sessões em rede: por onde as telas mandam comandos quando a run é de um grupo (a tela não sabe a diferença).

    SessaoHost     executa na hora (é o host que decide) e manda o comando aceito a todos: "aplicar"
                   {seq, comando, impressao}; o comando de um cliente chega por receber() com o jogador da conexão
                   (nunca o que o cliente escreveu); recusado, só quem mandou fica sabendo ("recusa").
    SessaoCliente  confere o comando aqui (para avisar na hora o que não pode), manda ao host e espera:
                   o estado só muda quando o "aplicar" volta, na ordem do host. Depois de aplicar, compara a
                   impressão digital com a do host: diferente = dessincronizou (a partida pede o estado de novo ao
                   host: "ressincronizar" -> "retomar", rede/retomada.py).

seq: o número de ordem dos comandos aceitos (1, 2, 3...). Um buraco na sequência também é dessincronia; um número
que já passou (mensagem repetida ou atrasada, de antes de uma retomada) é ignorado.

pode_aplicar(): a tela de agora deixa executar o próximo comando? No combate, só quando as animações chegaram à
vez de um herói (senão o processador faria a luta andar na frente da tela). O que chega antes espera na fila
(processar() roda a cada quadro). aplicados: o que já foi executado aqui, para o fluxo trocar de tela
(rede/... -> telas/fluxo.reagir): (comando em dicionário, Resultado, retrato de antes: região e vidas).
"""

from roguelike.comandos import Resultado, criar_comando
from roguelike.processador import ProcessadorDeComandos
from roguelike.sessao import Sessao

# depois destes, a fila para até o próximo quadro: a tela nova (a luta, o mapa...) aparece antes do próximo comando
TROCAM_DE_TELA = {"escolher_encontro", "iniciar_fuga", "comecar_combate", "concluir_encontro", "prosseguir",
                  "continuar_ondas"}


class SessaoEmRede(Sessao):
    def __init__(self, estado, jogador):
        super().__init__(estado, jogador)
        self.processador = ProcessadorDeComandos(estado)
        self.aplicados = []
        self.refeitos = []                    # (comando, Resultado) refeitos ao voltar à run (rede/retomada.py)
        self.pode_aplicar = lambda: True

    def retrato(self):
        """O que o fluxo precisa saber de antes de um comando (a região e a vida de cada um: as mensagens do descanso)."""
        run = self.estado.run
        return {"regiao": run.regiao_atual, "vidas": [h.vida for h in run.grupo.herois]}

    def anotar(self, dados, resultado, antes):
        self.aplicados.append((dados, resultado, antes))

    def pegar_aplicados(self):
        aplicados, self.aplicados = self.aplicados, []
        return aplicados


class SessaoHost(SessaoEmRede):
    def __init__(self, estado, jogador, transmitir, recusar=None):
        super().__init__(estado, jogador)
        self.transmitir = transmitir          # transmitir(tipo, dados): para todos os clientes
        self.recusar = recusar or (lambda jogador, mensagem: None)
        self.ao_aceitar = lambda dados: None  # cada comando aceito (a partida guarda para quem voltar e no save)
        self.fila = []                        # (jogador, comando) dos clientes, esperando a tela daqui
        self.seq = 0
        self.ultima_impressao = estado.impressao_digital()   # logo depois do último comando (quem volta compara)

    def enviar(self, comando):
        """Um comando de quem joga no host."""
        comando.jogador = self.jogador
        return self.executar(comando)

    def receber(self, jogador, dados):
        """Um comando que chegou de um cliente (dados = para_dict): entra na fila; processar() executa."""
        self.fila.append((jogador, dados))

    def processar(self):
        while self.fila and self.pode_aplicar():
            jogador, dados = self.fila.pop(0)
            resultado = self.executar_de_fora(jogador, dados)
            if not resultado:
                self.recusar(jogador, resultado.mensagem)
            elif isinstance(dados, dict) and dados.get("tipo") in TROCAM_DE_TELA:
                break

    def executar_de_fora(self, jogador, dados):
        """O comando de um cliente, com o jogador DA CONEXÃO. Nada que venha de fora derruba a partida."""
        try:
            comando = criar_comando(dados)
        except (KeyError, TypeError, ValueError, AttributeError):
            return Resultado(False, "Comando inválido.")
        comando.jogador = jogador
        try:
            return self.executar(comando)
        except Exception as erro:
            return Resultado(False, f"Comando recusado ({type(erro).__name__}).")

    def executar(self, comando):
        antes = self.retrato()
        resultado = self.processador.executar(comando)
        if resultado:
            self.seq += 1
            dados = comando.para_dict()
            self.ultima_impressao = self.estado.impressao_digital()
            self.transmitir("aplicar", {"seq": self.seq, "comando": dados, "impressao": self.ultima_impressao})
            self.anotar(dados, resultado, antes)
            self.ao_aceitar(dados)
        return resultado

    def agir_por(self, heroi):
        """A IA age pelo herói da vez (o dono demorou demais ou caiu da partida), em nome do dono."""
        from roguelike.condutor import DecisorIA
        comando = DecisorIA().comando(self.estado, heroi)
        comando.jogador = heroi.jogador.id if getattr(heroi, "jogador", None) is not None else self.jogador
        return self.executar(comando)


class SessaoCliente(SessaoEmRede):
    def __init__(self, estado, jogador, mandar):
        super().__init__(estado, jogador)
        self.mandar = mandar                  # mandar(tipo, dados): para o host
        self.fila = []                        # "aplicar" do host esperando a tela daqui
        self.seq = 0
        self.divergiu = None                  # None = tudo certo; senão, o que deu errado
        self.enviados = 0                     # comandos mandados ao host
        self.recusas = 0                      # quantos o host recusou (a tela de combate reabre o menu)
        self.conectado = lambda: True         # sem conexão (tentando voltar), nada sai daqui

    def enviar(self, comando):
        """Confere aqui e manda ao host. O Resultado é o da conferência: o estado muda quando o host devolver."""
        comando.jogador = self.jogador
        if not self.conectado():
            return Resultado(False, "Sem conexão com o host: tentando voltar à partida...")
        motivo = comando.validar(self.estado)
        if motivo:
            return Resultado(False, motivo)
        self.mandar("comando", {"comando": comando.para_dict()})
        self.enviados += 1
        return Resultado(True, "", None)

    def aplicar(self, dados):
        """Um comando aceito pelo host: entra na fila (processar() executa quando a tela deixar)."""
        self.fila.append(dados)

    def processar(self):
        while self.fila and self.pode_aplicar():
            dados = self.fila.pop(0)
            if self._aplicar(dados) is None:
                continue                                  # (repetido: nada aconteceu)
            if dados.get("comando", {}).get("tipo") in TROCAM_DE_TELA:
                break

    def _aplicar(self, dados):
        """Executa um "aplicar" do host. None = repetido ou atrasado (seq que já passou): ignorado."""
        if isinstance(dados.get("seq"), int) and dados["seq"] <= self.seq:
            return None
        if dados.get("seq") != self.seq + 1:
            self.divergiu = f"Faltou um comando (esperava {self.seq + 1}, chegou {dados.get('seq')})."
            return Resultado(False, self.divergiu)
        self.seq += 1
        antes = self.retrato()
        try:
            resultado = self.processador.executar(criar_comando(dados["comando"]))
        except Exception as erro:
            self.divergiu = f"Comando do host não pôde ser feito aqui ({type(erro).__name__})."
            return Resultado(False, self.divergiu)
        if not resultado:
            self.divergiu = f"O host aceitou e aqui foi recusado: {resultado.mensagem}"
        elif dados.get("impressao") and dados["impressao"] != self.estado.impressao_digital():
            self.divergiu = "O estado daqui ficou diferente do host."
        self.anotar(dados["comando"], resultado, antes)
        return resultado
