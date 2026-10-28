"""Para onde o jogo vai depois de cada tela.

Fica num lugar só para as telas não precisarem conhecer umas às outras:

    título -> acampamento (NPCs) -> [título da fase] -> mapa da área -> encontro -> mapa -> ... -> fim da run

Ao entrar numa fase (começo da run, portão do fim de ato, passagem ou retorno) aparece a tela
de título da área antes do mapa.
"""

import os

from roguelike.comandos import ConcluirEncontro, EncerrarOndas
from telas.comum import salvar_run, apagar_save_da_run, carregar_run


def ir_para_titulo(app):
    from telas.titulo import TelaTitulo
    app.trocar(TelaTitulo(app))


def comecar_do_zero(app):
    """Apaga o progresso permanente e a run salva e volta ao título com um progresso novo.
    As opções (volume, teclas, tela cheia) ficam: são preferências, não progresso."""
    from roguelike.progresso import Progresso
    caminho = app.progresso.caminho
    for arquivo in (caminho, caminho + ".tmp"):
        if os.path.exists(arquivo):
            os.remove(arquivo)
    apagar_save_da_run()
    app.progresso = Progresso()
    app.progresso.caminho = caminho
    ir_para_titulo(app)


def ir_para_acampamento(app):
    """O acampamento. Antes, a tela de herói novo para cada classe secreta liberada que ainda não foi anunciada.
    Numa partida em grupo ainda no lobby, o acampamento É o lobby (os NPCs voltam para ele)."""
    novos = app.progresso.herois_para_anunciar()
    if novos:
        from telas.novo_heroi import TelaNovoHeroi
        app.progresso.anunciar_heroi(novos[0])
        app.progresso.salvar()
        app.trocar(TelaNovoHeroi(app, novos[0], lambda: ir_para_acampamento(app)))
        return
    if app.partida is not None and app.partida.no_lobby():
        from telas.lobby import TelaLobby
        app.trocar(TelaLobby(app))
        return
    from telas.acampamento import TelaAcampamento
    app.trocar(TelaAcampamento(app))


# ============================================================
# PARTIDA EM GRUPO
# ============================================================

def abrir_multijogador(app, erro=None):
    """A tela de criar ou entrar numa partida em grupo (com o motivo, se a anterior acabou)."""
    from telas.multijogador import TelaMultijogador
    app.trocar(TelaMultijogador(app, erro))


def seguir_a_partida(app):
    """A cada quadro (App.passo): trata a rede, mostra os avisos e troca de tela quando a partida começa ou acaba,
    e quando um comando (de qualquer jogador) leva o grupo a outra tela (reagir)."""
    partida = app.partida
    if partida.sessao is not None:                       # o combate não deixa um comando pular as animações
        partida.sessao.pode_aplicar = lambda: getattr(app.atual, "aceita_comandos", lambda: True)()
    partida.atualizar()
    for titulo, conteudo in partida.pegar_avisos():
        app.notificar(titulo, conteudo, som="navegar")
    volta = partida.pegar_volta() if not partida.eh_host else None
    if volta is not None:                                # a chave para voltar a esta partida (se o jogo fechar)
        app.opcoes.volta = volta
        app.salvar_opcoes()
    if partida.encerrada:
        app.partida = None
        abrir_multijogador(app, partida.motivo_do_fim)
        return
    run, retomou = partida.pegar_run_nova()
    if run is not None and retomou:
        if partida.eh_host and partida.esperando_o_grupo:
            from telas.retomada import TelaRetomada
            app.trocar(TelaRetomada(app))                # (o host espera o grupo voltar antes de seguir)
        else:
            retomar_em_grupo(app, run)
    elif run is not None:
        app.progresso.partiu_em_grupo(run, partida.eu)
        app.progresso.salvar()
        mostrar_titulo_da_area(app, run, ["A expedição do grupo parte."])
    while partida.sessao is not None and app.partida is partida:
        aplicados = partida.sessao.pegar_aplicados()
        if not aplicados:
            break
        for dados, resultado, antes in aplicados:
            reagir(app, partida.run, dados, resultado, antes)
    mostrar_avisos_do_bau(app)


def ultima_troca_de_tela(refeitos):
    """O índice do último comando (em (comando, Resultado)) que levou o grupo a outra tela, ou None."""
    from rede.sessoes import TROCAM_DE_TELA
    return next((i for i in range(len(refeitos) - 1, -1, -1) if refeitos[i][0].get("tipo") in TROCAM_DE_TELA), None)


def retomar_em_grupo(app, run):
    """Voltou à run do grupo (caiu e voltou, entrou de novo com a chave, dessincronizou ou o host retomou a partida
    salva): abre a tela em que o grupo está, pelo último comando que trocou de tela, e mostra nela o que veio depois
    (o resultado de um evento, de um descanso...), como reagir() teria feito."""
    from roguelike.comandos import ComecarCombate
    sessao = app.partida.sessao
    refeitos = getattr(sessao, "refeitos", [])
    indice = ultima_troca_de_tela(refeitos)
    ultimo = refeitos[indice][0] if indice is not None else {}
    tipo, condutor = ultimo.get("tipo"), sessao.estado.condutor
    app.notificar("De volta à partida", "Você está no mesmo ponto que o grupo.", som="navegar")
    if tipo == "prosseguir" and ultimo.get("tela") == "fim":
        fim_de_run(app, run)
        return
    if condutor is not None and tipo in ("comecar_combate", None):
        from telas.combate.tela import TelaCombate
        condutor.combate.pegar_eventos()                 # (a luta já aconteceu até aqui: nada para animar de novo)
        app.trocar(TelaCombate(app, run, run.encontro, condutor=condutor))
    elif tipo == "prosseguir" and ultimo.get("tela") == "entre_ondas":
        mostrar_entre_ondas(app, run)
    elif run.estado == "encontro" and run.encontro is not None:
        if run.encontro.eh_combate():                     # a luta ainda não começou: o host começa (todos reagem)
            if app.partida.eh_host:
                sessao.enviar(ComecarCombate())
            else:
                ir_para_mapa(app, run)
            return
        resolver_encontro(app, run)
    else:
        ir_para_mapa(app, run)
        return
    ao_aplicar = getattr(app.atual, "ao_aplicar", None)
    for dados, resultado in refeitos[(indice + 1) if indice is not None else 0:]:
        if ao_aplicar is not None and dados.get("tipo") not in ("agir_no_combate",):
            ao_aplicar(dados, resultado)


# ---------------- avisos do que os outros fazem ----------------
def anotar_aviso_do_bau(app, dados):
    """Outro jogador pôs ou pegou algo do baú: junta por alguns segundos e avisa uma vez (mostrar_avisos_do_bau)."""
    from roguelike.estado import BAU
    partida = app.partida
    jogador, tipo = dados.get("jogador"), dados.get("tipo")
    if jogador in (None, partida.eu):
        return
    if tipo == "mover_item" and (dados.get("de") == BAU) != (dados.get("para") == BAU):
        verbo, quantidade = ("pegou do baú" if dados.get("de") == BAU else "pôs no baú"), dados.get("quantidade", 1)
    elif tipo == "equipar" and dados.get("origem") == BAU:
        verbo, quantidade = "pegou do baú", 1
    else:
        return
    juntos = app.avisos_do_bau.setdefault((jogador, verbo), {"itens": {}, "quando": 0.0})
    juntos["itens"][dados.get("chave")] = juntos["itens"].get(dados.get("chave"), 0) + quantidade
    juntos["quando"] = app.relogio_total


def mostrar_avisos_do_bau(app):
    from rede.protocolo import configuracao
    from roguelike.itens import item
    partida = app.partida
    for (jogador, verbo), juntos in list(app.avisos_do_bau.items()):
        if app.relogio_total - juntos["quando"] < configuracao()["juntar_avisos_do_bau"]:
            continue
        del app.avisos_do_bau[(jogador, verbo)]
        quem = partida.lobby.jogador(jogador) if partida is not None else None
        if quem is None:
            continue
        itens = juntos["itens"]
        if len(itens) == 1:
            chave, quantidade = next(iter(itens.items()))
            try:
                nome = item(chave).nome
            except KeyError:
                nome = chave
            texto = nome + (f" x{quantidade}" if quantidade > 1 else "")
        else:
            texto = f"{sum(itens.values())} itens"
        app.notificar("Baú da equipe", f"{quem.nome} {verbo}: {texto}", som=None)


def avisar_lendarios(app, por_jogador):
    """Em grupo: quem ganhou uma peça lendária (no fim de uma luta ou num evento)."""
    from roguelike.itens import item
    partida = app.partida
    if partida is None or not isinstance(por_jogador, dict):
        return
    for jogador, itens in por_jogador.items():
        quem = partida.lobby.jogador(jogador)
        for chave in itens:
            try:
                peca = item(chave)
            except KeyError:
                continue
            if getattr(peca, "raridade", "") != "lendario":
                continue
            if jogador == partida.eu:
                app.notificar("Lendário!", f"Você ganhou: {peca.nome}", som="conquista")
            elif quem is not None:
                app.notificar(f"{quem.nome} ganhou um lendário!", peca.nome, som="conquista")


def em_grupo(app, run):
    """A run é a de uma partida em grupo?"""
    return app.partida is not None and run is not None and app.partida.run is run


def reagir(app, run, dados, resultado, antes):
    """Partida em grupo: um comando executado aqui (de qualquer jogador, na ordem do host) pode levar todos a outra
    tela. As telas do co-op não trocam sozinhas: votam, o host manda o comando e cada computador reage aqui."""
    from roguelike.comandos import ComecarCombate
    partida = app.partida
    tipo, sessao = dados.get("tipo"), partida.sessao
    anotar_aviso_do_bau(app, dados)
    if tipo == "resolver_evento" and resultado:
        avisar_lendarios(app, getattr(resultado.valor, "por_jogador", None))
    if tipo in ("escolher_encontro", "iniciar_fuga", "continuar_ondas"):
        encontro = run.encontro
        if encontro is None:
            return
        if encontro.eh_combate():
            if partida.eh_host:                            # (os clientes abrem a luta quando o combate começar)
                sessao.enviar(ComecarCombate())
        elif encontro.tipo == "portao":
            if partida.eh_host:
                sessao.enviar(ConcluirEncontro())
        else:
            resolver_encontro(app, run)
    elif tipo == "comecar_combate":
        from telas.combate.tela import TelaCombate
        app.trocar(TelaCombate(app, run, run.encontro, condutor=sessao.estado.condutor))
    elif tipo == "concluir_encontro":
        mostrar_proxima_area(app, run, antes["regiao"], antes["vidas"])
    elif tipo == "prosseguir":
        if dados.get("tela") == "entre_ondas":
            mostrar_entre_ondas(app, run)
        elif dados.get("tela") == "fim":
            fim_de_run(app, run)
    else:
        if tipo == "resolver_evento":
            guardar_segredos(app, run)
        ao_aplicar = getattr(app.atual, "ao_aplicar", None)
        if ao_aplicar is not None:                         # a tela mostra o resultado (evento, descanso, ondas)
            ao_aplicar(dados, resultado)


def depois_do_combate_em_grupo(app, run):
    """(Só o host) todos confirmaram a janela de recompensas: o próximo passo, como comando para todos."""
    from roguelike.comandos import Prosseguir
    sessao = app.partida.sessao
    if run.terminou():
        sessao.enviar(Prosseguir(tela="fim"))
        return
    if run.ondas is not None and run.ondas.terminou() and not run.ondas.premio:
        sessao.enviar(EncerrarOndas())                     # acabou sem prêmio (ex.: o Rei e a Rainha caíram)
    if run.ondas is not None:
        sessao.enviar(Prosseguir(tela="entre_ondas"))
    else:
        sessao.enviar(ConcluirEncontro())


def sair_da_partida(app):
    """Sair (ou fechar, se for o host) e voltar ao título."""
    if app.partida is not None:
        app.partida.fechar()
        app.partida = None
    ir_para_titulo(app)


def continuar_run_salva(app):
    """Abre a run salva: no mapa, ou direto no encontro que estava em andamento."""
    run = carregar_run()
    if run.estado == "encontro":
        resolver_encontro(app, run)
    else:
        ir_para_mapa(app, run, ["Run carregada."])


def comecar_run(app, herois, semente):
    run = app.progresso.criar_run(herois, semente)
    app.progresso.salvar()
    mostrar_titulo_da_area(app, run, [f"A expedição parte. Semente: {run.semente}"])


def mostrar_titulo_da_area(app, run, mensagens=None, retorno=False):
    """Tela de entrada da fase e, depois dela, o mapa."""
    from telas.titulo_da_area import TelaTituloDaArea
    salvar_run(run)
    app.trocar(TelaTituloDaArea(app, run, lambda: ir_para_mapa(app, run, mensagens), retorno))


def abrir_inventario(app, run, ao_voltar=None, aba=None, loja=None, indice=0):
    """Inventário da run: o herói com os espaços, a mochila do jogador e o baú da equipe.

    aba: "mochila" (padrão) ou "bau". loja: aberta pela loja (o menu de ações ganha "Vender")."""
    from telas.inventario import TelaInventario, FonteDaRun
    voltar = ao_voltar or (lambda: ir_para_mapa(app, run))

    def fabricar(i):                         # a fabricação volta para este inventário, no mesmo herói
        abrir_fabricacao(app, run, lambda: abrir_inventario(app, run, voltar, aba, loja, i), i)

    app.trocar(TelaInventario(app, FonteDaRun(run, loja), voltar, run, indice, aba, ao_fabricar=fabricar))


def abrir_fabricacao(app, run, ao_voltar=None, indice=0):
    """Fabricação: o que sai só com a mochila do herói, com mochila + baú, e a Forja dos Anões."""
    from telas.fabricacao import TelaFabricacao
    app.trocar(TelaFabricacao(app, run, ao_voltar or (lambda: ir_para_mapa(app, run)), indice))


def abrir_arsenal(app):
    """Estande de armas do acampamento: o mesmo inventário, com as peças do arsenal para a expedição."""
    from telas.inventario import TelaInventario, FonteDoAcampamento
    app.trocar(TelaInventario(app, FonteDoAcampamento(app.progresso), lambda: ir_para_acampamento(app)))


def mostrar_avisos(app, run):
    """Notificações guardadas pelos heróis (ex.: "Golpe aprimorado!"). Em grupo, só as dos meus heróis."""
    meus = meus_herois(app, run)
    for heroi in run.grupo.herois:
        for titulo, conteudo in heroi.golpes.pegar_avisos():
            if heroi in meus:
                app.notificar(titulo, conteudo)


def meus_herois(app, run):
    """Os heróis de quem joga neste computador (no solo, todos)."""
    if not em_grupo(app, run):
        return list(run.grupo.herois)
    return [h for h in run.grupo.herois if getattr(h.jogador, "id", None) == app.partida.eu]


def heroi_com_golpe_novo(run, herois=None):
    return next((h for h in (run.grupo.herois if herois is None else herois) if h.golpes.pendentes), None)


def ir_para_mapa(app, run, mensagens=None):
    """Tela de escolha do próximo encontro (salva a run antes).

    Se algum herói aprendeu um golpe com os espaços cheios, a escolha aparece antes do mapa.
    """
    from telas.mapa import TelaMapa
    mostrar_avisos(app, run)
    heroi = heroi_com_golpe_novo(run, meus_herois(app, run))      # (em grupo, cada um decide os seus)
    if heroi is not None and em_grupo(app, run):                   # em grupo, sem parar o grupo: pelo Grupo (G)
        app.notificar("Golpe novo!", f"{heroi.nome} aprendeu um golpe: escolha no Grupo (G).", som="nivel")
    elif heroi is not None:
        from telas.golpes import TelaGolpes
        app.trocar(TelaGolpes(app, heroi, lambda: ir_para_mapa(app, run, mensagens), run))
        return
    salvar_run(run)
    app.trocar(TelaMapa(app, run, mensagens or []))


def resolver_encontro(app, run):
    """Abre a tela certa para o encontro escolhido (e salva a escolha)."""
    salvar_run(run)
    encontro = run.encontro
    if encontro.eh_combate():
        from telas.combate.tela import TelaCombate
        app.trocar(TelaCombate(app, run, encontro, lambda recompensa: depois_do_combate(app, run, recompensa)))
    elif encontro.tipo == "portao":
        concluir_e_seguir(app, run)                 # o portão escolhido no mapa leva direto à fase
    elif encontro.tipo == "evento":
        from telas.evento import TelaEvento
        app.trocar(TelaEvento(app, run))
    elif encontro.tipo in ("loja", "alquimista"):
        from telas.loja import TelaLoja
        app.trocar(TelaLoja(app, run))
    else:
        from telas.servicos import TelaServico
        app.trocar(TelaServico(app, run))


TITULO_DA_DESCOBERTA = "Passagem secreta descoberta!"


def guardar_segredos(app, run):
    """Leva para o progresso os passos de segredo dados na run (ex.: seguir o Rato Branco) e avisa quando
    um guia leva até o fim: a passagem foi descoberta. Vale mesmo que a run acabe mal depois."""
    progresso = getattr(app, "progresso", None)
    if progresso is None:
        return
    from roguelike.guias import todos_os_guias
    andaram = progresso.guardar_segredos(run)
    if not andaram:
        return
    progresso.salvar()
    for chave in andaram:
        guia = todos_os_guias().get(chave)
        if guia is not None and guia.completo(progresso.segredos):
            app.notificar(TITULO_DA_DESCOBERTA, guia.descoberta)


def registrar_conquistas(app, run, abates):
    """Conta os abates no progresso permanente e avisa as conquistas (e skins) liberadas."""
    progresso = getattr(app, "progresso", None)
    if progresso is None:
        return
    from roguelike.golpes import golpe
    from roguelike.skins import skin
    for conquista in progresso.registrar_combate(run, abates):
        if conquista.skin:
            premio = f"Skin liberada: {skin(conquista.skin).nome}"
        elif conquista.golpe:
            premio = f"Golpe raro liberado: {golpe(conquista.golpe).nome} (a partir da próxima run)"
        else:
            premio = conquista.descricao
        app.notificar(f"Conquista: {conquista.nome}", premio)
    progresso.salvar()


def depois_do_combate(app, run, recompensa):
    registrar_conquistas(app, run, getattr(recompensa, "abates", []))
    if run.terminou():
        fim_de_run(app, run)
        return
    if run.ondas is not None and run.ondas.terminou() and not run.ondas.premio:
        app.sessao_da(run).enviar(EncerrarOndas())         # acabou sem prêmio (ex.: o Rei e a Rainha caíram)
    if run.ondas is not None:                               # combate em ondas: continuar ou fugir (ou o prêmio)
        seguir = lambda: mostrar_entre_ondas(app, run)
    else:
        seguir = lambda: concluir_e_seguir(app, run)
    if getattr(recompensa, "abrir_bau", False):            # "I" na janela de recompensas: o loot está na mochila
        abrir_inventario(app, run, ao_voltar=seguir, aba="mochila")
        return
    seguir()


def mostrar_entre_ondas(app, run):
    """Entre as ondas de um combate em ondas (ex.: Enxame de Ratos) e, depois da última, o prêmio."""
    from telas.entre_ondas import TelaEntreOndas
    mostrar_avisos(app, run)
    app.trocar(TelaEntreOndas(app, run))


def concluir_e_seguir(app, run, mensagens=None, pular_passagem=False):
    """Fecha o encontro, descansa e mostra a próxima área (ou o fim, se a run acabou).
    pular_passagem: a passagem do encontro foi ignorada (só avança a área)."""
    regiao_antes = run.regiao_atual
    vidas_antes = [h.vida for h in run.grupo.herois]
    app.sessao_da(run).enviar(ConcluirEncontro(pular_passagem=pular_passagem))
    mostrar_proxima_area(app, run, regiao_antes, vidas_antes, mensagens)


def mostrar_proxima_area(app, run, regiao_antes, vidas_antes, mensagens=None):
    """Depois de fechar um encontro: o fim (se a run acabou), o título da fase nova ou o mapa, com o descanso."""
    if run.terminou():
        fim_de_run(app, run)
        return
    mensagens = list(mensagens or [])
    mudou = run.regiao_atual != regiao_antes
    if mudou:
        mensagens.append(f"Vocês chegam a: {run.regiao.nome}")
    curas = [f"{h.nome} +{h.vida - antes}" for h, antes in zip(run.grupo.herois, vidas_antes) if h.vida > antes]
    if curas:
        mensagens.append("Descanso: " + ", ".join(curas))
    if mudou:
        mostrar_titulo_da_area(app, run, mensagens, retorno=run.area > 1)
    else:
        ir_para_mapa(app, run, mensagens)


def fim_de_run(app, run):
    """O fim da run: o progresso guarda Brasas, prestígio, conquistas e as peças. Em grupo, cada um no seu
    progresso (o prestígio das classes e as peças de quem joga aqui) e a run salva do solo fica como está."""
    from telas.fim_de_run import TelaFimDeRun
    if em_grupo(app, run):
        relatorio = app.progresso.registrar_fim_de_run(run, run.grupo.jogador(app.partida.eu))
    else:
        relatorio = app.progresso.registrar_fim_de_run(run)
        apagar_save_da_run()
    app.progresso.salvar()
    app.trocar(TelaFimDeRun(app, run, relatorio))
