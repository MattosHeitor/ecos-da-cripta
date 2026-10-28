"""Onde fica cada arquivo do jogo: um lugar só para todas as pastas.

    CAMINHOS.asset("sprites_macabros")    assets/sprites_macabros (imagens, sons, fontes: só leitura)
    CAMINHOS.dados                         src/roguelike/dados (o conteúdo em JSON: só leitura)
    CAMINHOS.save("progresso.json")        pasta do jogador (progresso, run e opções: leitura e escrita)

Pasta do jogo (só leitura): rodando pelo código, a raiz do projeto; empacotado (PyInstaller), a pasta que o
executável abre (sys._MEIPASS), com a mesma árvore dentro (assets/ e src/roguelike/dados/).

Pasta do jogador: fora da pasta do jogo, porque a pasta de programas não deixa gravar e porque assim o save
sobrevive a reinstalar ou trocar de versão:
    Windows   %APPDATA%\\Ecos da Cripta
    outros    ~/.ecos_da_cripta
Com um perfil (python src/jogar.py --perfil B) cada um tem a sua subpasta (perfis/B): duas cópias do jogo
abertas no mesmo PC não gravam no mesmo save.
"""

import json
import os
import re
import shutil
import sys
import time

NOME_DA_PASTA = "Ecos da Cripta"
ARQUIVOS_DO_JOGADOR = ("progresso.json", "run.json", "opcoes.json")
VARIAVEL_DA_PASTA = "ECOS_DA_CRIPTA_DADOS"      # troca a pasta do jogador (ex.: jogar com um save de teste)
PERFIL_VALIDO = re.compile(r"[A-Za-z0-9_-]{1,24}")
TENTATIVAS_DE_GRAVAR = 5                       # no Windows o antivírus às vezes segura o arquivo por um instante


def pasta_do_jogo():
    """A raiz com assets/ e src/: a do projeto ou, empacotado, a que o executável abre."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pasta_padrao_do_jogador():
    """%APPDATA%\\Ecos da Cripta no Windows (ou a pasta da variável ECOS_DA_CRIPTA_DADOS, se existir)."""
    escolhida = os.environ.get(VARIAVEL_DA_PASTA)
    if escolhida:
        return os.path.abspath(escolhida)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, NOME_DA_PASTA)
    return os.path.join(os.path.expanduser("~"), ".ecos_da_cripta")


def gravar_json(caminho, dados):
    """Grava sem risco de deixar o arquivo pela metade: escreve num .tmp e troca de uma vez."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    temporario = caminho + ".tmp"
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=1)
    for tentativa in range(TENTATIVAS_DE_GRAVAR):
        try:
            os.replace(temporario, caminho)
            return
        except PermissionError:
            if tentativa == TENTATIVAS_DE_GRAVAR - 1:
                raise
            time.sleep(0.05)


def pasta_para_mostrar(pasta):
    """O caminho curto para a tela: "%APPDATA%\\Ecos da Cripta" (ou "...\\as\\duas últimas" pastas)."""
    appdata = os.environ.get("APPDATA")
    if appdata and os.path.normcase(pasta).startswith(os.path.normcase(appdata) + os.sep):
        return "%APPDATA%" + pasta[len(appdata):]
    partes = os.path.normpath(pasta).split(os.sep)
    return pasta if len(partes) <= 3 else os.path.join("...", *partes[-2:])


def abrir_pasta(pasta):
    """Abre a pasta no Explorador de Arquivos (cria antes, se faltar). Devolve False se não deu."""
    try:
        os.makedirs(pasta, exist_ok=True)
        os.startfile(pasta)
        return True
    except (AttributeError, OSError):          # (startfile só existe no Windows)
        return False


class Caminhos:
    """As pastas do jogo (só leitura) e a do jogador (saves), com o perfil escolhido."""

    def __init__(self, raiz=None, jogador=None):
        self.raiz = raiz or pasta_do_jogo()
        self.assets = os.path.join(self.raiz, "assets")
        self.dados = os.path.join(self.raiz, "src", "roguelike", "dados")
        self.base_do_jogador = jogador or pasta_padrao_do_jogador()
        self.perfil = None

    # ---------------- só leitura ----------------
    def asset(self, *partes):
        """Arquivo ou pasta dentro de assets/."""
        return os.path.join(self.assets, *partes)

    # ---------------- pasta do jogador ----------------
    @property
    def jogador(self):
        """A pasta dos saves (a do perfil, se houver um)."""
        if self.perfil:
            return os.path.join(self.base_do_jogador, "perfis", self.perfil)
        return self.base_do_jogador

    def save(self, nome):
        """Arquivo na pasta do jogador (ex.: "progresso.json")."""
        return os.path.join(self.jogador, nome)

    def usar_perfil(self, nome):
        """Troca para o perfil (None = o principal). Só letras, números, "-" e "_" (vira nome de pasta)."""
        if nome and not PERFIL_VALIDO.fullmatch(nome):
            raise ValueError(f"Perfil inválido: {nome!r} (use até 24 letras, números, - ou _)")
        self.perfil = nome or None

    def usar_pasta_do_jogador(self, pasta):
        """Saves numa pasta escolhida (testes e prévias usam uma pasta temporária)."""
        self.base_do_jogador = os.path.abspath(pasta)
        self.perfil = None

    def pasta_antiga(self):
        """Onde o jogo salvava antes (saves/ dentro do projeto)."""
        return os.path.join(self.raiz, "saves")

    def trazer_saves_antigos(self, pasta_antiga=None):
        """Na primeira vez, copia os saves de saves/ (dentro do projeto) para a pasta do jogador.

        Só copia se a pasta do jogador ainda não existe: depois de um "começar do zero" nada volta.
        Os arquivos antigos ficam onde estão, como cópia de segurança. Devolve os nomes copiados."""
        origem = pasta_antiga or self.pasta_antiga()
        destino = self.jogador
        if os.path.exists(destino) or not os.path.isdir(origem):
            return []
        achados = [nome for nome in ARQUIVOS_DO_JOGADOR if os.path.isfile(os.path.join(origem, nome))]
        if not achados:
            return []
        os.makedirs(destino)
        for nome in achados:
            shutil.copy2(os.path.join(origem, nome), os.path.join(destino, nome))
        return achados


CAMINHOS = Caminhos()
