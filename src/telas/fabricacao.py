"""Fabricação: lista sozinha o que dá para fazer, para o herói escolhido.

    Receitas           três grupos: só com a mochila do herói / com mochila + baú da equipe / faltam
                       materiais (em cinza, com o que falta)
    Forja dos Anões    as peças lendárias que só um Anão no grupo forja (escondidas até a alma do chefe
                       revelar; liberadas para sempre depois de vencê-lo)

Os ingredientes saem primeiro da mochila do herói e depois do baú; o item feito vai para a mochila
dele (ou para o baú, se ela estiver cheia).
"""

import pygame

from roguelike.comandos import Fabricar
from roguelike.fabricacao import situacao, SO_MOCHILA, COM_BAU, FALTA, todas_as_receitas
from roguelike.itens import item
from roguelike.progresso import descrever_conquista
from telas.comum import TelaComBotoes, Fundo, cabecalho_da_run, desenhar_abas, texto_do_item, desenhar_rosto
from ui import tema
from ui.desenho import painel, titulo_de_painel
from ui.icones import icone_item
from ui.rolagem import PainelRolavel
from ui.texto import CaixaTexto, linha
from ui.widgets import Botao

RACA_DA_FORJA = "anao_das_profundezas"
GRUPOS = ((SO_MOCHILA, "Só com a mochila de {nome}", tema.CURA),
          (COM_BAU, "Com a mochila + o baú da equipe", tema.OURO_CLARO),
          (FALTA, "Faltam materiais", tema.TEXTO_APAGADO))
ALTURA_RECEITA, ALTURA_GRUPO = 58, 30
LISTA = pygame.Rect(16, 120, 540, 476)
DETALHE = pygame.Rect(568, 120, 696, 476)


class TelaFabricacao(TelaComBotoes):
    PAGINAS_ROLAM = True

    def __init__(self, app, run, ao_voltar, indice=0):
        super().__init__(app)
        self.run = run
        self.ao_voltar = ao_voltar
        self.indice = min(indice, len(run.grupo.herois) - 1)
        self.aba = "receitas"
        self.receita = None
        self.mensagem = ""
        self.fundo = Fundo.da_run(run, escurecer=170)
        self.lista = PainelRolavel(passo=ALTURA_RECEITA)

    @property
    def heroi(self):
        return self.run.grupo.herois[self.indice]

    def musica(self):
        return self.run.musica()

    def voltar(self):
        self.ao_voltar()

    def atualizar(self, dt):
        super().atualizar(dt)
        self.fundo.atualizar(dt)

    def trocar_heroi(self, indice):
        self.indice = indice % len(self.run.grupo.herois)
        self.mensagem = ""

    def trocar_aba(self, aba):
        self.aba = aba
        self.receita = None
        self.lista.ir_para(0, imediato=True)

    def tecla(self, e):
        if e.key == pygame.K_q:
            self.trocar_heroi(self.indice - 1)
        elif e.key == pygame.K_e:
            self.trocar_heroi(self.indice + 1)
        elif e.unicode and e.unicode.isdigit() and 1 <= int(e.unicode) <= len(self.run.grupo.herois):
            self.trocar_heroi(int(e.unicode) - 1)

    # ---------------- regras ----------------
    def tem_anao(self):
        return RACA_DA_FORJA in self.run.racas_do_grupo()

    def receitas_da_aba(self):
        """[(receita, situação)] da aba: as comuns (visíveis) ou as da forja anã (todas, para mostrar o que falta)."""
        mochila, bau = self.heroi.inventario, self.run.grupo.bau
        if self.aba == "receitas":
            receitas = [r for r in self.run.receitas_visiveis(self.heroi) if r.requer_raca is None]
        else:
            receitas = [r for r in todas_as_receitas().values() if r.requer_raca == RACA_DA_FORJA]
        return [(r, situacao(r, mochila, bau)) for r in receitas]

    def escondida(self, receita):
        return receita.escondida and receita.chave not in self.run.descobertas

    def pode(self, receita, estado):
        return estado != FALTA and receita.liberada_para(self.run.racas_do_grupo()) and not self.escondida(receita)

    def fabricar(self, chave):
        heroi = self.heroi
        cabia = heroi.inventario.cabe(todas_as_receitas()[chave].resultado)
        if self.enviar(Fabricar(receita=chave, heroi=self.indice)):
            destino = f"a mochila de {heroi.nome}" if cabia else "o baú da equipe (a mochila está cheia)"
            self.mensagem = f"Fabricado! Foi para {destino}."
            self.app.audio.tocar("item")
        else:
            self.mensagem = "Faltam ingredientes."

    # ---------------- desenho ----------------
    def desenhar_herois(self):
        abas = [(i, h.nome) for i, h in enumerate(self.run.grupo.herois)]
        largura = min(200, (tema.LARGURA - 32 - 10 * (len(abas) - 1)) // len(abas))
        desenhar_abas(self, (16, 68), abas, self.indice, self.trocar_heroi, largura=largura, altura=42)

    def desenhar_lista(self, tela):
        painel(tela, LISTA, "ferro")
        abas = [("receitas", "Receitas"), ("forja", "Forja dos Anões")]
        desenhar_abas(self, (LISTA.x + 14, LISTA.y + 14), abas, self.aba, self.trocar_aba,
                      largura=(LISTA.width - 38) // 2, altura=38)
        janela = pygame.Rect(LISTA.x + 14, LISTA.y + 64, LISTA.width - 28, LISTA.height - 78)
        receitas = self.receitas_da_aba()
        if self.aba == "forja" and not self.tem_anao():
            aviso = CaixaTexto((janela.x, janela.y, janela.width, 46), tema.pequena(), tema.VELA)
            aviso.desenhar(tela, "Só um Anão no grupo forja estas peças. Elas aparecem com a alma do chefe e ficam "
                                 "liberadas para sempre depois de vencê-lo.")
            janela = pygame.Rect(janela.x, janela.y + 54, janela.width, janela.height - 54)
        if not receitas:
            CaixaTexto(janela, tema.pequena(), tema.TEXTO_FRACO, padding=8).desenhar(
                tela, "Nenhuma receita ainda. Elas aparecem quando a mochila ou o baú têm algum ingrediente, "
                      "ou quando vocês acham minérios, peças do circo e almas de chefe (ou compram a receita).")
            return
        linhas = []                                 # (tipo, conteúdo): "grupo" ou "receita"
        for estado, titulo, cor in GRUPOS:
            do_grupo = [r for r, s in receitas if s == estado]
            if do_grupo:
                linhas.append(("grupo", (titulo.format(nome=self.heroi.nome), cor, len(do_grupo))))
                linhas += [("receita", (r, estado)) for r in sorted(do_grupo, key=lambda r: r.nome())]
        total = sum(ALTURA_GRUPO if t == "grupo" else ALTURA_RECEITA for t, _ in linhas) - 6
        largura = PainelRolavel.largura_util(janela, total)
        if self.receita not in [c[0] for t, c in linhas if t == "receita"]:
            self.receita = next((c[0] for t, c in linhas if t == "receita"), None)
        with self.rolavel(self.lista, janela, total) as y:
            for tipo, conteudo in linhas:
                if tipo == "grupo":
                    titulo, cor, quantos = conteudo
                    linha(tela, f"{titulo} ({quantos})", tema.pequena(), cor, (janela.x + 4, y + 4), largura - 8)
                    y += ALTURA_GRUPO
                else:
                    self.desenhar_receita(tela, pygame.Rect(janela.x, y, largura, ALTURA_RECEITA - 6), *conteudo)
                    y += ALTURA_RECEITA

    def desenhar_receita(self, tela, rect, receita, estado):
        """Uma linha: ícone, nome (cor da raridade) e o que ela pede ("pronta", "usa o baú" ou o que falta)."""
        escondida = self.escondida(receita)
        objeto = receita.item_resultado()
        disponivel = self.pode(receita, estado)
        self.botao(Botao(rect, "", (lambda r=receita: setattr(self, "receita", r)),
                         estilo="osso" if disponivel else "pedra", selecionado=self.receita is receita))
        tela.blit(icone_item(objeto, 2), (rect.x + 10, rect.y + 13))
        nome = "Receita escondida" if escondida else objeto.nome + (f" x{receita.quantidade}" if receita.quantidade > 1 else "")
        cor = tema.COR_RARIDADE[objeto.raridade] if disponivel else tema.TEXTO_APAGADO
        linha(tela, nome, tema.pequena(), cor, (rect.x + 48, rect.y + 6), rect.width - 60)
        if escondida:
            detalhe, cor_detalhe = "aparece com: " + ", ".join(item(c).nome for c in receita.revelada_por), tema.TEXTO_APAGADO
        elif estado == SO_MOCHILA:
            detalhe, cor_detalhe = "pronta: só com a mochila", tema.CURA
        elif estado == COM_BAU:
            detalhe, cor_detalhe = "pronta: usa o baú da equipe", tema.OURO
        else:
            falta = receita.faltando(self.run.estoque_de(self.heroi))
            detalhe = "faltam: " + ", ".join(f"{n} {item(c).nome}" for c, n in falta.items())
            cor_detalhe = tema.TEXTO_FRACO
        linha(tela, detalhe, tema.mini(), cor_detalhe, (rect.x + 48, rect.y + 28), rect.width - 60)

    def desenhar_detalhe(self, tela):
        painel(tela, DETALHE, "ferro")
        receita = self.receita
        if receita is None:
            titulo_de_painel(tela, DETALHE, "Receita")
            return
        objeto = receita.item_resultado()
        escondida = self.escondida(receita)
        topo = titulo_de_painel(tela, DETALHE, "Receita escondida" if escondida else objeto.nome)
        area = pygame.Rect(DETALHE.x + 20, topo, DETALHE.width - 40, DETALHE.bottom - topo - 16)
        tela.blit(icone_item(objeto, 5), (area.x, area.y))
        CaixaTexto((area.x + 84, area.y, area.width - 84, 140), tema.pequena(), tema.TEXTO).desenhar(
            tela, "Ainda não descoberta." if escondida else texto_do_item(objeto))
        y = area.y + 152
        linha(tela, "Ingredientes", tema.normal(), tema.TEXTO_TITULO, (area.x, y), 200)
        linha(tela, "mochila · baú · precisa", tema.mini(), tema.TEXTO_FRACO, (area.right, y + 6), 260, "topright")
        y += 32
        mochila, bau = self.heroi.inventario, self.run.grupo.bau
        for chave, precisa in receita.ingredientes.items():
            if y + 34 > area.bottom - 70:
                break
            ingrediente = item(chave)
            na_mochila, no_bau = mochila.quantidade(chave), bau.quantidade(chave)
            tela.blit(icone_item(ingrediente, 2), (area.x, y + 2))
            linha(tela, ingrediente.nome, tema.pequena(), tema.TEXTO, (area.x + 36, y + 4), area.width - 36 - 220)
            cor = tema.CURA if na_mochila >= precisa else (tema.OURO if na_mochila + no_bau >= precisa else tema.SANGUE_CLARO)
            linha(tela, f"{na_mochila} · {no_bau} · {precisa}", tema.pequena(), cor, (area.right, y + 4), 200, "topright")
            y += 34
        estado = situacao(receita, mochila, bau)
        pode = self.pode(receita, estado)
        if receita.requer_raca and not receita.liberada_para(self.run.racas_do_grupo()):
            aviso = "Só um Anão no grupo forja esta peça."
        elif escondida:
            aviso = "Aparece com: " + ", ".join(item(c).nome for c in receita.revelada_por)
            if receita.liberada_por:
                aviso += f" (liberada para sempre depois de: {descrever_conquista(receita.liberada_por)})"
        else:
            destino = "a mochila" if mochila.cabe(receita.resultado) else "o baú (mochila cheia)"
            aviso = f"Gasta primeiro da mochila de {self.heroi.nome}, depois do baú. Vai para {destino}."
        CaixaTexto((area.x, area.bottom - 60, area.width - 280, 60), tema.mini(), tema.TEXTO_FRACO,
                   vertical="meio").desenhar(tela, aviso)
        self.botao(Botao((area.right - 260, area.bottom - 52, 260, 48), "Fabricar",
                         (lambda c=receita.chave: self.fabricar(c)), ativo=pode, estilo="ouro"))

    def desenhar(self, tela):
        self.comecar_desenho(tela)
        self.fundo.desenhar(tela, frente=False)
        cabecalho_da_run(tela, self.run, "Fabricação", jogador=self.meu_jogador())
        self.desenhar_herois()
        self.desenhar_lista(tela)
        self.desenhar_detalhe(tela)
        voltar = pygame.Rect(tema.LARGURA - 176, 664, 160, 46)
        desenhar_rosto(tela, self.app.sprites, self.heroi.sprite, (16, 606, 52, 52))
        CaixaTexto((80, 606, voltar.x - 96, 52), tema.normal(), tema.OURO_CLARO, vertical="meio").desenhar(
            tela, self.mensagem or f"Fabricando para {self.heroi.nome} (Q/E ou 1 a 5 trocam de herói).")
        self.botao(Botao(voltar, "Voltar", self.voltar, "ESC"))
        self.terminar_desenho(tela)
