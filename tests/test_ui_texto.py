"""Fase 3, etapa 1: caixas de texto (nada sai da caixa), botões, registro rolável e auditoria das telas."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

pygame.init()

from ui import tema
from ui import texto as T
from ui.componentes import RegistroRolavel
from ui.widgets import Botao

FUNDO = (255, 0, 255)


def nada_fora(superficie, rect):
    """True se nenhum pixel fora do retângulo foi pintado."""
    for x in range(superficie.get_width()):
        for y in range(superficie.get_height()):
            if not rect.collidepoint(x, y) and superficie.get_at((x, y))[:3] != FUNDO:
                return False
    return True


def test_largura_conta_o_contorno_e_o_ajuste_do_fi():
    fonte = tema.pequena()
    assert T.largura_do_texto("fio", fonte) > fonte.size("fio")[0]          # contorno + separador do "fi"


def test_quebra_respeita_a_largura_real_e_parte_palavras_gigantes():
    fonte = tema.pequena()
    conteudo = "Melodia Dissonante (nv 1): 70% de chance: Enfraquecido por 2 turnos · 2 energia · todos os inimigos"
    for largura in (120, 200, 333):
        for linha in T.quebrar_linhas(conteudo, fonte, largura):
            assert T.largura_do_texto(linha, fonte) <= largura
    pedacos = T.quebrar_linhas("A" * 80, fonte, 100)
    assert len(pedacos) > 1 and all(T.largura_do_texto(p, fonte) <= 100 for p in pedacos)
    assert T.quebrar_linhas("um\ndois", fonte, 500) == ["um", "dois"]


def test_caixa_encolhe_a_fonte_antes_de_cortar():
    conteudo = "Uma descrição comprida que não cabe na fonte normal em duas linhas, mas cabe numa fonte menor."
    menor = tema.pequena()
    altura = len(T.quebrar_linhas(conteudo, menor, 300)) * T.altura_da_linha(menor) - 2      # cabe só na menor
    assert len(T.quebrar_linhas(conteudo, tema.normal(), 300)) * T.altura_da_linha(tema.normal()) - 2 > altura
    caixa = T.CaixaTexto(pygame.Rect(0, 0, 300, altura), tema.normal())
    fonte, linhas, cortou = caixa.ajustar([(conteudo, tema.TEXTO)])
    assert not cortou and fonte.get_height() < tema.normal().get_height()


def test_caixa_corta_com_reticencias_e_anota():
    antes = len(T.TRUNCAMENTOS)
    caixa = T.CaixaTexto(pygame.Rect(0, 0, 120, 20), tema.normal(), maximo_linhas=1)
    fonte, linhas, cortou = caixa.ajustar([("palavras " * 30, tema.TEXTO)])
    assert cortou and linhas[-1][0].endswith("...")
    assert T.largura_do_texto(linhas[-1][0], fonte) <= 120
    assert len(T.TRUNCAMENTOS) == antes + 1


def test_texto_da_caixa_nunca_sai_do_retangulo():
    superficie = pygame.Surface((400, 200))
    superficie.fill(FUNDO)
    rect = pygame.Rect(40, 40, 220, 90)
    T.CaixaTexto(rect, tema.normal(), alinhamento="centro", vertical="meio", padding=6).desenhar(
        superficie, "Um texto bem comprido " * 12)
    assert nada_fora(superficie, rect)


@pytest.mark.parametrize("rotulo,subtexto,atalho", [
    ("Melodia Dissonante", "2 energia · nv 1", "3"),
    ("Pergaminho da Tempestade Ancestral do Rei", "3 energia · nv 5", "6"),
    ("Brado do Senhor da Guerra", None, "1"),
    ("Sair (novo ao grimório)", None, "ESC"),
])
def test_botoes_mantem_o_texto_dentro(rotulo, subtexto, atalho):
    superficie = pygame.Surface((400, 120))
    superficie.fill(FUNDO)
    rect = pygame.Rect(30, 30, 200, 46)
    Botao(rect, rotulo, atalho=atalho, subtexto=subtexto).desenhar(superficie, (-1, -1))
    assert nada_fora(superficie, rect)


def test_registro_quebra_rola_e_volta_ao_fim():
    mensagens = [(f"Morcego Gigante usa Mordida Sangrenta em Corvo, o bardo ({i})", tema.TEXTO) for i in range(30)]
    registro = RegistroRolavel(mensagens)
    superficie = pygame.Surface((300, 200))
    superficie.fill(FUNDO)
    rect = pygame.Rect(20, 20, 220, 120)
    registro.desenhar(superficie, rect)
    assert nada_fora(superficie, rect)
    assert all(T.largura_do_texto(l, registro.fonte) <= rect.width - 2 * registro.padding
               for l, _ in registro.linhas(rect.width - 2 * registro.padding))
    registro.rolar(5)
    assert registro.rolagem == 5
    mensagens.append(("Mensagem nova", tema.TEXTO))
    registro.desenhar(superficie, rect)
    assert registro.rolagem == 0                       # chegou mensagem: volta a mostrar as mais recentes


def test_descricao_de_todo_golpe_cabe_na_caixa_do_combate():
    """As 3 seções (nome/nível, efeito, custo · alvo) de qualquer golpe cabem sem cortar."""
    from roguelike.golpes import golpe, todas_as_chaves, NOMES_DE_ALVO
    antes = len(T.TRUNCAMENTOS)
    caixa = T.CaixaTexto(pygame.Rect(0, 0, 600, 140), tema.pequena(), alinhamento="centro", padding=8, maximo_linhas=6)
    for chave in todas_as_chaves():
        g = golpe(chave)
        caixa.ajustar([(f"{g.nome} (nível 5)", tema.TEXTO), (g.resumo(5), tema.TEXTO),
                       (f"{g.texto_custo()}  ·  {NOMES_DE_ALVO[g.alvo]}", tema.TEXTO)])
    assert len(T.TRUNCAMENTOS) == antes


def test_telas_nao_cortam_texto(tmp_path):
    """Abre as telas principais e confere que nenhuma caixa precisou cortar texto."""
    from roguelike import encontros as E
    from roguelike.classes import criar_heroi
    from roguelike.classes import todas_as_classes
    from roguelike.progresso import Progresso
    from telas import comum, fluxo
    from telas.base import App
    comum.ArquivoDaRun.caminho = str(tmp_path / "run.json")
    try:
        app = App(janela=False)
        app.progresso = Progresso.carregar(str(tmp_path / "progresso.json"))
        antes = len(T.TRUNCAMENTOS)

        def mostrar(tela, quadros=3):
            app.trocar(tela)
            for _ in range(quadros):
                app.passo(1 / 30, [])

        from telas.titulo import TelaTitulo
        from telas.acampamento import TelaAcampamento
        from telas.espelho import TelaEspelho
        from telas.taverna import TelaTaverna
        from telas.capitao import TelaCapitao
        from telas.opcoes import TelaOpcoes, TelaControles
        from telas.visual_heroi import TelaVisual
        from telas.golpes import TelaGolpes
        from telas.mago_anciao import TelaMagoAnciao
        from telas.bestiario import TelaBestiario
        from telas.grimorio import TelaGrimorio
        from telas.bau import TelaBau
        from telas.insignias import TelaInsignias
        mostrar(TelaInsignias(app))
        mostrar(TelaInsignias(app, "prestigio"))
        app.progresso.expedicao_atual().adicionar("monge")
        app.progresso.expedicao_atual().adicionar("feiticeira")
        mago = TelaMagoAnciao(app)
        for chave in ("gnomo", "draconiano", "revenante", "meio_demonio", "hemofago"):
            mago.ver(chave)
            mostrar(mago, 2)
        for indice in range(len(app.progresso.expedicao_atual().vagas)):
            mago.escolher_vaga(indice)
            mago.trocar_aba("subclasse")
            for sub in list(todas_as_classes()[mago.vaga.classe].subclasses):
                mago.ver(sub)
                mostrar(mago, 2)
            mago.trocar_aba("raca")
        for aba in ("bencaos", "provisoes", "boatos", "raridades", "mascarado"):
            mostrar(TelaTaverna(app, aba))
        app.progresso.conquistas.add("chefe:mercador_mascarado")
        mostrar(TelaTaverna(app, "mascarado"))
        app.progresso.abates.update({"bispo_eclipsado": 1})
        lore = TelaBestiario(app)
        lore.trocar_secao("catedral_do_eclipse")
        lore.ver("bispo_eclipsado")
        lore.lendo = True
        mostrar(lore, 2)
        bestiario = TelaBestiario(app)
        app.progresso.abates.update({"goblin": 10, "aranha_mae": 3, "lich": 1})
        for chave, _, _ in bestiario.secoes:
            bestiario.trocar_secao(chave)
            mostrar(bestiario, 2)
        for classe in ("guerreiro", "mago", "monge", "feiticeira"):
            grimorio = TelaGrimorio(app, classe)
            app.progresso.golpes_descobertos |= {"golpe", "palma_aberta", "bola_de_fogo", "faisca_maldita"}
            for secao in [s.chave for s in __import__("roguelike.grimorio", fromlist=["x"]).secoes_da_classe(classe)]:
                grimorio.trocar_secao(secao)
                mostrar(grimorio, 2)
        for tela in (TelaTitulo(app), TelaAcampamento(app), TelaEspelho(app), TelaCapitao(app), TelaBau(app),
                     TelaOpcoes(app, lambda: None), TelaControles(app, lambda: None),
                     TelaVisual(app, "bardo", "menestrel_das_laminas", lambda: None)):
            mostrar(tela)
        heroi = criar_heroi("mago", subclasse="necromante")
        heroi.aprender("exercito_dos_mortos")
        mostrar(TelaGolpes(app, heroi, lambda: None))
        run = app.progresso.criar_run([criar_heroi("bardo", subclasse="menestrel_das_laminas"), heroi], "TEXTO")
        fluxo.ir_para_mapa(app, run)
        for _ in range(3):
            app.passo(1 / 30, [])
        for encontro in (E.EncontroLoja(), E.EncontroAlquimista(), E.EncontroEvento("altar_esquecido"), E.EncontroAltar()):
            run.estado, run.opcoes = "escolha", [encontro]
            run.escolher(0)
            fluxo.resolver_encontro(app, run)
            for _ in range(3):
                app.passo(1 / 30, [])
        from telas.grupo import TelaGrupo
        for aba in ("herois", "bau", "fabricacao"):
            mostrar(TelaGrupo(app, run, aba, lambda: None))
        assert T.TRUNCAMENTOS[antes:] == []
    finally:
        comum.ArquivoDaRun.caminho = None
