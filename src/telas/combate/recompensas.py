"""Janela de recompensas do fim do combate: XP, ouro e o loot em ícones, separado por tipo.

    painel = PainelDeRecompensas(recompensa, jogadores, local="local")
    painel.desenhar(tela, mouse)          # devolve o item sob o mouse (para a dica) ou None
    painel.clicar(posicao)                # clicou numa aba de jogador? (troca e devolve True)

O loot vem separado por jogador (Recompensa.por_jogador). Com mais de um jogador aparece uma aba para cada um
("Você · 9 itens", "Bia · 9 itens"), começando pela de quem está jogando aqui; Tab troca de aba.
Cada ícone tem a moldura na cor da raridade e a quantidade no canto. Tudo vai para a mochila de cada um; o que não
coube foi para o baú da equipe (Recompensa.no_bau) e o rodapé avisa.
"""

import pygame

from roguelike.itens import item
from ui import tema
from ui.desenho import painel, texto, desenhar_placa, anotar
from ui.icones import icone_item
from ui.texto import linha

LARGURA = 860
CELULA = 52                      # quadradinho de cada item
ESPACO = 6
CARTAO = (LARGURA - 48 - 2 * ESPACO) // 3      # cartão das peças de equipamento (ícone + nome), 3 por fileira
MAX_FILEIRAS = {"equipamento": 3, "consumivel": 1, "material": 2}    # o que passar vira "+N" (cabe em 720 px)
SECOES = [("equipamento", "Equipamentos"), ("consumivel", "Consumíveis"), ("material", "Materiais")]
ORDEM_RARIDADE = ["amaldicoado", "lendario", "epico", "raro", "incomum", "comum"]


ALTURA_DAS_ABAS = 34


class PainelDeRecompensas:
    def __init__(self, recompensa, jogadores=(), local=None):
        self.recompensa = recompensa
        por_jogador = getattr(recompensa, "por_jogador", {}) or {}
        nomes = {j.id: j.nome for j in jogadores}
        # (id, nome) de cada jogador que ganhou algo, o daqui primeiro
        self.jogadores = sorted(((i, nomes.get(i, i)) for i in por_jogador), key=lambda par: par[0] != local)
        self.local = local
        self.aba = 0
        self.abas = []                           # (rect, índice) do último desenho
        self.celulas = []                        # (rect, objeto) do último desenho
        self.secoes = self.separar(self.itens_da_aba())

    @property
    def varios(self):
        return len(self.jogadores) > 1

    def itens_da_aba(self):
        if not self.varios:
            return self.recompensa.itens
        return self.recompensa.por_jogador[self.jogadores[self.aba][0]]

    def foram_ao_bau(self):
        """Quantos itens do jogador da aba não couberam na mochila (e foram para o baú)."""
        no_bau = getattr(self.recompensa, "no_bau", {}) or {}
        if not self.jogadores:
            return 0
        return sum(no_bau.get(self.jogadores[self.aba][0], {}).values())

    def trocar_aba(self, indice):
        if self.varios:
            self.aba = indice % len(self.jogadores)
            self.secoes = self.separar(self.itens_da_aba())

    def clicar(self, posicao):
        """Clique numa aba de jogador: troca para ela e devolve True."""
        for rect, indice in self.abas:
            if rect.collidepoint(posicao):
                self.trocar_aba(indice)
                return True
        return False

    @staticmethod
    def separar(itens):
        """{tipo: [(objeto, quantidade)]}, dos mais raros para os mais simples."""
        secoes = {tipo: [] for tipo, _ in SECOES}
        for chave, quantidade in itens.items():
            objeto = item(chave)
            secoes.setdefault(objeto.tipo if objeto.tipo in secoes else "material", []).append((objeto, quantidade))
        for lista in secoes.values():
            lista.sort(key=lambda par: (ORDEM_RARIDADE.index(par[0].raridade) if par[0].raridade in ORDEM_RARIDADE else 9,
                                        par[0].nome))
        return secoes

    @staticmethod
    def largura_da_celula(tipo):
        """Equipamento ganha cartão com nome; o resto, só o ícone."""
        return CARTAO if tipo == "equipamento" else CELULA

    def por_fileira(self, tipo=None):
        return (LARGURA - 48 + ESPACO) // (self.largura_da_celula(tipo) + ESPACO)

    def fileiras(self, lista, tipo=None):
        return min(MAX_FILEIRAS.get(tipo, 2), (len(lista) + self.por_fileira(tipo) - 1) // self.por_fileira(tipo))

    def altura(self):
        altura = 96 + 34 + (ALTURA_DAS_ABAS if self.varios else 0)         # título + XP/ouro (+ as abas)
        for tipo, _ in SECOES:
            lista = self.secoes.get(tipo, [])
            if lista:
                altura += 28 + self.fileiras(lista, tipo) * (CELULA + ESPACO)
        if not any(self.secoes.values()):
            altura += 30
        altura += len(self.recompensa.niveis) * 24 + 58
        return altura

    def desenhar(self, tela, mouse):
        rect = pygame.Rect(0, 0, LARGURA, self.altura())
        rect.center = (tema.LARGURA // 2, tema.ALTURA // 2 - 10)
        painel(tela, rect, "ouro")
        desenhar_placa(tela, (rect.centerx, rect.y + 34), "VITÓRIA", tema.grande(), tema.OURO_CLARO)
        r = self.recompensa
        ouro = f"+{r.ouro} de ouro"
        partes = getattr(r, "ouro_por_jogador", {}) or {}
        if self.varios and self.local in partes:                  # o ouro é dividido pelos heróis de cada um
            ouro += f" (sua parte: +{partes[self.local]})"
        texto(tela, f"+{r.xp} de experiência      {ouro}", tema.normal(), tema.TEXTO, (rect.centerx, rect.y + 76), "midtop")
        y = rect.y + 112
        if self.varios:
            y = self.desenhar_abas(tela, rect, y)
        self.celulas = []
        sob_o_mouse = None
        for tipo, titulo in SECOES:
            lista = self.secoes.get(tipo, [])
            if not lista:
                continue
            total = sum(q for _, q in lista)
            texto(tela, f"{titulo} ({total})", tema.pequena(), tema.OURO, (rect.x + 24, y))
            y += 26
            achado = self.desenhar_grade(tela, lista, pygame.Rect(rect.x + 24, y, rect.width - 48, 0), mouse, tipo)
            sob_o_mouse = sob_o_mouse or achado
            y += self.fileiras(lista, tipo) * (CELULA + ESPACO) + 2
        if not any(self.secoes.values()):
            texto(tela, "Nenhum item desta vez.", tema.pequena(), tema.TEXTO_FRACO, (rect.centerx, y), "midtop")
            y += 30
        for heroi, _ in r.niveis:
            texto(tela, f"{heroi.nome} subiu para o nível {heroi.nivel}!", tema.pequena(), tema.XP, (rect.centerx, y + 4), "midtop")
            y += 24
        rodape, cor = "Tudo foi para a sua mochila   ·   Enter: continuar   ·   I: abrir a mochila", tema.TEXTO_FRACO
        if self.varios:
            rodape = "Cada um ganhou o seu (na própria mochila)   ·   Tab: outro jogador   ·   Enter: continuar"
        sobra = self.foram_ao_bau()
        if sobra:
            rodape = f"Mochila cheia: {sobra} {'item foi' if sobra == 1 else 'itens foram'} para o baú da equipe   ·   " \
                     + ("Tab: outro jogador" if self.varios else "I: abrir a mochila") + "   ·   Enter: continuar"
            cor = tema.SANGUE_CLARO
        linha(tela, rodape, tema.pequena(), cor, (rect.centerx, rect.bottom - 16), rect.width - 40, "midbottom")
        return sob_o_mouse

    def desenhar_abas(self, tela, rect, y):
        """Uma aba por jogador ("Você · 9 prêmios": pilhas); a escolhida em ouro. Devolve o y de baixo."""
        self.abas = []
        largura = min(220, (rect.width - 48 - ESPACO * (len(self.jogadores) - 1)) // len(self.jogadores))
        x = rect.centerx - (largura * len(self.jogadores) + ESPACO * (len(self.jogadores) - 1)) // 2
        for i, (jogador, nome) in enumerate(self.jogadores):
            aba = pygame.Rect(x + i * (largura + ESPACO), y, largura, ALTURA_DAS_ABAS - 6)
            escolhida = i == self.aba
            painel(tela, aba, "ouro" if escolhida else "pedra")
            premios = getattr(self.recompensa, "premios", {}).get(jogador, len(self.recompensa.por_jogador[jogador]))
            linha(tela, f"{nome} · {premios} prêmios", tema.pequena(), tema.OURO_CLARO if escolhida else tema.TEXTO,
                  aba.center, aba.width - 16, "center")
            self.abas.append((aba, i))
        return y + ALTURA_DAS_ABAS

    def desenhar_grade(self, tela, lista, area, mouse, tipo=None):
        """Os ícones (ou cartões) em fileiras; devolve o item sob o mouse."""
        colunas = self.por_fileira(tipo)
        largura = self.largura_da_celula(tipo)
        limite = colunas * MAX_FILEIRAS.get(tipo, 2)
        mostrados = lista if len(lista) <= limite else lista[:limite - 1]
        sob_o_mouse = None
        for i, (objeto, quantidade) in enumerate(mostrados):
            celula = pygame.Rect(area.x + (i % colunas) * (largura + ESPACO), area.y + (i // colunas) * (CELULA + ESPACO),
                                 largura, CELULA)
            self.desenhar_celula(tela, celula, objeto, quantidade, celula.collidepoint(mouse))
            self.celulas.append((celula, objeto))
            if celula.collidepoint(mouse):
                sob_o_mouse = objeto
        if len(mostrados) < len(lista):
            i = len(mostrados)
            celula = pygame.Rect(area.x + (i % colunas) * (largura + ESPACO), area.y + (i // colunas) * (CELULA + ESPACO),
                                 largura, CELULA)
            painel(tela, celula, "pedra")
            texto(tela, f"+{len(lista) - len(mostrados)}", tema.normal(), tema.TEXTO, celula.center, "center")
        return sob_o_mouse

    @staticmethod
    def desenhar_celula(tela, celula, objeto, quantidade, destaque):
        cor = tema.COR_RARIDADE.get(objeto.raridade, tema.TEXTO)
        pygame.draw.rect(tela, (22, 16, 20), celula, border_radius=6)
        pygame.draw.rect(tela, cor, celula, 3 if destaque else 2, border_radius=6)
        anotar("painel", celula, tela, "celula")
        icone = icone_item(objeto, 3)
        quadrado = pygame.Rect(celula.x, celula.y, CELULA, CELULA)
        tela.blit(icone, icone.get_rect(center=quadrado.center))
        if quantidade > 1:
            texto(tela, f"x{quantidade}", tema.mini(), tema.TEXTO, (quadrado.right - 4, quadrado.bottom - 2), "bottomright")
        if celula.width > CELULA:                                 # cartão: nome na cor da raridade + espaço
            from roguelike.dados import regras
            from ui.texto import CaixaTexto, largura_do_texto
            largura = celula.width - CELULA - 8
            espaco = regras()["nomes_espacos"].get(getattr(objeto, "espaco", ""), "")
            nome_raridade = regras()["raridades"].get(objeto.raridade, {}).get("nome", "")
            if largura_do_texto(objeto.nome, tema.mini()) <= largura:
                linha(tela, objeto.nome, tema.pequena(), cor, (quadrado.right + 2, celula.y + 7), largura)
                linha(tela, f"{espaco} · {nome_raridade}", tema.mini(), tema.TEXTO_FRACO, (quadrado.right + 2, celula.y + 29), largura)
            else:          # nome comprido (peça com afixos): duas linhas; a raridade fica na cor da borda e na dica
                CaixaTexto(pygame.Rect(quadrado.right + 2, celula.y + 4, largura, celula.height - 8), tema.mini(), cor,
                           vertical="meio", espaco=0, maximo_linhas=2).desenhar(tela, objeto.nome)
