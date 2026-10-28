"""ProcessadorDeComandos: o único lugar que muda o estado do jogo.

    processador = ProcessadorDeComandos(EstadoDoJogo(run))
    processador.executar(Comprar(indice=0))       # confere, executa e anota no registro
    processador.registro                          # os comandos aceitos, em ordem (JSON)

O registro é a partida inteira: refazer() executa um registro num estado novo (mesma semente) e tem de chegar
ao mesmo estado (impressao_digital). É o que o multiplayer usa: o host confere e ordena os comandos, e cada
computador os executa do mesmo jeito.

Antes de cada comando, o combate em andamento anda até a próxima decisão de herói (ou até o fim, que dá a
recompensa): na tela isso já aconteceu passo a passo; ao refazer a partida, acontece aqui, na mesma ordem.
"""

from roguelike.comandos import Resultado, criar_comando


class ComandoRecusado(Exception):
    """Um comando do registro foi recusado ao refazer a partida (os estados já não batem)."""


class ProcessadorDeComandos:
    def __init__(self, estado):
        self.estado = estado
        self.registro = []            # comandos aceitos (para_dict), em ordem

    def executar(self, comando):
        """Confere e executa. Recusado (na conferência ou porque não deu na hora): Resultado(False, motivo) e nada
        entra no registro. O registro é só o que aconteceu: é exatamente o que o host manda aos outros."""
        self.estado.avancar_combate()
        motivo = comando.validar(self.estado)
        if motivo:
            return Resultado(False, motivo)
        resultado = comando.executar(self.estado)
        if resultado:
            self.registro.append(comando.para_dict())
        return resultado

    def refazer(self, registro, avancar_no_fim=True):
        """Executa, em ordem, comandos aceitos antes (ex.: uma partida inteira). Devolve os Resultados.
        Um comando recusado quer dizer que os estados já não batem: ComandoRecusado.
        avancar_no_fim=False: para logo depois do último comando, como o host estava ao executá-lo (quem volta a uma
        partida em grupo compara a impressão ali; a tela de combate anda dali em diante, com as animações)."""
        resultados = []
        for dados in registro:
            comando = criar_comando(dados)
            self.estado.avancar_combate()
            motivo = comando.validar(self.estado)
            if motivo:
                raise ComandoRecusado(f"{comando!r}: {motivo}")
            resultado = comando.executar(self.estado)
            if not resultado:
                raise ComandoRecusado(f"{comando!r}: {resultado.mensagem}")
            resultados.append(resultado)
            self.registro.append(comando.para_dict())
        if avancar_no_fim:
            self.estado.avancar_combate()         # o que acontece sozinho depois do último comando (ex.: a luta acaba)
        return resultados
