"""Rede (MP5): partidas em grupo pela rede local, só com a biblioteca padrão (socket, threading, json).

    protocolo   o formato das mensagens (uma linha JSON cada: tipo, versão do protocolo, dados) e o Leitor
    codigo      o "código da partida" (o IP e a porta do host em 7 ou 10 letras) e a leitura do que se digita
    conexao     Conexao (uma ponta TCP: uma thread lê e põe as mensagens numa fila), Servidor e conectar()
    descoberta  Anunciante (o host responde quem procura) e Procurador (acha as partidas na rede local, por UDP)
    lobby       o lobby em dados: jogadores (nome, cor, pronto, heróis) e o chat
    partida     PartidaHost e PartidaCliente: o protocolo do lobby e o começo da run
    sessoes     SessaoHost e SessaoCliente: os comandos da run passando pela rede

Nada aqui usa pygame: as telas (telas/multijogador.py, telas/lobby.py) só leem a partida e chamam os métodos dela.
O host é autoritativo: confere e ordena tudo; cada computador executa os mesmos comandos (roguelike/processador.py)
e compara a impressão digital do estado.
"""
