"""Peças das telas numa partida em grupo (MP6): votar, mostrar quem votou no quê e quanto tempo falta.

Uma escolha do grupo (o caminho, a opção de um evento, continuar as ondas) e o "seguir" (recompensas, loja,
serviços) são votações (rede/votacao.py). Cada tela:
    chave = "caminho|..."                         # sai do estado da run: igual em todo computador
    em_grupo.preparar(tela, chave, opcoes, ao_decidir)   # só o host: o que fazer com a opção vencedora
    em_grupo.votar(tela, chave, opcao)            # o clique de cada um
    em_grupo.desenhar_votos(...) / faixa(...)     # quem votou (na cor de cada um) e o tempo
"""

import pygame

from rede.protocolo import configuracao
from ui import tema
from ui.desenho import painel
from ui.texto import linha


def partida_da(tela):
    """A partida em grupo da run desta tela (ou None no solo)."""
    partida = tela.app.partida
    run = getattr(tela, "run", None)
    return partida if partida is not None and run is not None and partida.run is run else None


def preparar(tela, chave, opcoes, ao_decidir, seguir=False, chave_atual=None):
    """(Só no host) a tela chegou a uma escolha do grupo: abre a votação. seguir=True: "todos prontos para seguir"
    (o relógio começa no primeiro voto). chave_atual(): a chave que vale AGORA (sai do estado da run); se o grupo
    já seguiu (outra área, um Mapa Rasgado sorteou outros caminhos), a votação velha não faz nada."""
    partida = partida_da(tela)
    if partida is not None and partida.eh_host:
        prazo = configuracao()["tempo_para_seguir" if seguir else "tempo_de_votacao"]

        def decidir(opcao):
            if chave_atual is None or chave_atual() == chave:
                ao_decidir(opcao)
        partida.abrir_votacao(chave, opcoes, decidir, prazo, esperar_primeiro_voto=seguir)


def votar(tela, chave, opcao):
    partida = partida_da(tela)
    if partida is not None:
        partida.votar(chave, opcao)
        tela.app.audio.tocar("clique")


def meu_voto(tela, chave):
    partida = partida_da(tela)
    return partida.votos_de(chave).get(partida.eu) if partida is not None else None


def cor_de(partida, identificador):
    jogador = partida.lobby.jogador(identificador)
    return jogador.cor if jogador is not None else tema.TEXTO


def desenhar_votos(superficie, partida, chave, opcao, ponto, ancora="midbottom"):
    """Os nomes de quem votou nesta opção, cada um na sua cor, numa faixa (devolve o retângulo ou None)."""
    nomes = [(j.nome, j.cor) for j in partida.lobby.jogadores if partida.votos_de(chave).get(j.id) == opcao]
    if not nomes:
        return None
    fonte = tema.mini()
    largura = sum(fonte.size(n)[0] + 6 for n, _ in nomes) + 14 * len(nomes) + 10
    rect = pygame.Rect(0, 0, largura, 22)
    setattr(rect, ancora, ponto)
    fundo = pygame.Surface(rect.size, pygame.SRCALPHA)
    fundo.fill((10, 6, 12, 200))
    superficie.blit(fundo, rect)
    x = rect.x + 8
    for nome, cor in nomes:
        pygame.draw.circle(superficie, cor, (x + 3, rect.centery), 4)
        linha(superficie, nome, fonte, cor, (x + 10, rect.centery), fonte.size(nome)[0] + 6, "midleft")
        x += fonte.size(nome)[0] + 20
    return rect


def texto_da_votacao(partida, chave, pergunta="Votação"):
    """"Votação: faltam Bia, Caio · 18 s" (ou "Decidido!")."""
    if partida.decidida(chave) is not None:
        return "Decidido!"
    faltam = [j.nome for j in partida.faltam_votar(chave)]
    restante = partida.restante_de(chave)
    tempo = f" · {int(restante + 0.99)} s" if restante is not None else ""
    if not faltam:
        return f"{pergunta}: todos votaram{tempo}"
    return f"{pergunta}: faltam {', '.join(faltam)}{tempo}"


def abrir_envio_de_ouro(tela):
    """Mandar ouro a outro jogador: primeiro para quem, depois quanto (EnviarOuro)."""
    from roguelike.comandos import EnviarOuro
    partida = partida_da(tela)
    if partida is None:
        return
    meu = tela.meu_jogador()
    outros = [j for j in tela.run.grupo.jogadores if j.id != meu.id and j.id not in partida.desconectados]
    if not outros or meu.ouro <= 0:
        tela.app.notificar("Enviar ouro", "Sem ouro para mandar." if outros else "Não há para quem mandar.", som="voltar")
        return

    def mandar(jogador, quantia):
        resultado = tela.enviar(EnviarOuro(para=jogador.id, quantidade=quantia))
        tela.app.notificar("Enviar ouro", f"{quantia} de ouro para {jogador.nome}." if resultado else resultado.mensagem,
                           som="moeda" if resultado else "voltar")

    def quanto(jogador):
        quantias = sorted({q for q in (10, 50, meu.ouro // 2, meu.ouro) if 0 < q <= meu.ouro})
        opcoes = [(f"{q} de ouro" + (" (tudo)" if q == meu.ouro else ""), (lambda q=q: mandar(jogador, q)))
                  for q in quantias]
        tela.abrir_dialogo("Enviar ouro", f"Quanto mandar para {jogador.nome}? (você tem {meu.ouro})",
                           opcoes + [("Cancelar", None)])

    tela.abrir_dialogo("Enviar ouro", f"Para quem? (você tem {meu.ouro} de ouro)",
                       [(j.nome, (lambda j=j: quanto(j))) for j in outros] + [("Cancelar", None)])


def latencia(partida, identificador):
    """("48 ms", cor) da ida e volta desse jogador até o host (verde, amarelo se lenta, vermelho se muito lenta),
    ou None se não há medida (o próprio host, ou ainda medindo)."""
    if partida.eh_host and identificador == partida.eu:
        return None
    ms = partida.latencia_de(identificador)
    if ms is None:
        return None
    lenta = configuracao()["latencia_lenta"]
    cor = tema.CURA if ms < lenta else (tema.OURO_CLARO if ms < 2 * lenta else tema.SANGUE_CLARO)
    return f"{ms} ms", cor


def desenhar_conexao(superficie, partida):
    """Por cima de qualquer tela (App.passo): "sem conexão, tentando voltar" ou o aviso de conexão lenta."""
    from ui.desenho import escurecer_tela
    from ui.texto import CaixaTexto
    if getattr(partida, "reconectando", None) is not None:
        escurecer_tela(superficie, 160)
        rect = painel(superficie, pygame.Rect(0, 0, 600, 190).move(tema.LARGURA // 2 - 300, tema.ALTURA // 2 - 95),
                      "ferro")
        linha(superficie, "Conexão perdida", tema.media(), tema.SANGUE_CLARO, (rect.centerx, rect.y + 34),
              rect.width - 40, "center")
        segundos = int(partida.segundos_tentando_voltar())
        limite = configuracao()["tempo_para_voltar"]
        CaixaTexto(pygame.Rect(rect.x + 30, rect.y + 62, rect.width - 60, 80), tema.pequena(), tema.TEXTO,
                   alinhamento="centro").desenhar(
            superficie, f"Tentando voltar à partida... ({segundos} de {limite} s, tentativa "
                        f"{max(1, partida.reconectando['tentativas'])}). Seus heróis estão com a IA até você voltar.")
        linha(superficie, "ESC: desistir e sair da partida", tema.mini(), tema.TEXTO_FRACO,
              (rect.centerx, rect.bottom - 26), rect.width - 40, "center")
        return
    if partida.eh_host or not partida.jogando() and not partida.no_lobby():
        return
    medida = latencia(partida, partida.eu)
    if medida is None or partida.latencia_de(partida.eu) < configuracao()["latencia_lenta"]:
        return
    rect = painel(superficie, pygame.Rect(tema.LARGURA - 236, 62, 228, 26), "pedra")   # (logo abaixo da barra do topo)
    linha(superficie, f"Conexão lenta · {medida[0]}", tema.mini(), medida[1], rect.center, rect.width - 16, "center")


def faixa(superficie, rect, partida, chave, pergunta="Votação", estilo="pedra"):
    """Uma faixa com a situação da votação (quem falta e o tempo)."""
    rect = painel(superficie, rect, estilo)
    decidida = partida.decidida(chave) is not None
    linha(superficie, texto_da_votacao(partida, chave, pergunta), tema.pequena(), tema.CURA if decidida else tema.OURO_CLARO,
          rect.center, rect.width - 20, "center")
    return rect
