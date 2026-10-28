# -*- mode: python ; coding: utf-8 -*-
# A pasta do jogo para Windows (dist/Ecos da Cripta/), feita pelo PyInstaller. Não rode direto: use
#     python ferramentas/instalador/construir.py
# (ele gera o arquivo de versão do .exe, confere o .exe e faz o instalador com o Inno Setup).
#
# Dentro da pasta fica a mesma árvore do projeto (assets/ e src/roguelike/dados/): caminhos.py lê de sys._MEIPASS.
# Modo pasta ("onedir") e não um .exe único: o jogo abre na hora (o .exe único desempacota ~100 MB a cada vez).

import os
import sys

RAIZ = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
SRC = os.path.join(RAIZ, "src")
sys.path.insert(0, SRC)
from versao import NOME_DO_JOGO  # noqa: E402

ICONE = os.path.join(RAIZ, "assets", "icone", "ecos_da_cripta.ico")
ARQUIVO_DE_VERSAO = os.path.join(RAIZ, "build", "versao_do_exe.txt")      # (o construir.py escreve)

# Fora do pacote: o que só as ferramentas e os testes usam (Pillow, numpy, pytest...) e a criptografia do OpenSSL
# (ssl/_hashlib: o jogo não usa conexão segura e o SHA-256 da impressão digital é o embutido do Python).
FORA = ["tkinter", "pytest", "PIL", "setuptools", "numpy", "ssl", "_ssl", "_hashlib"]

a = Analysis(
    [os.path.join(SRC, "jogar.py")],
    pathex=[SRC],
    datas=[(os.path.join(RAIZ, "assets"), "assets"),
           (os.path.join(SRC, "roguelike", "dados"), os.path.join("src", "roguelike", "dados"))],
    hiddenimports=[],
    excludes=FORA,
    noarchive=False,
)
# As DLLs do pygame iam duas vezes (na pasta do pygame e na raiz): ficam só na do pygame, onde ele as procura.
DO_PYGAME = {os.path.basename(destino).lower() for destino, _, _ in a.binaries + a.datas
             if os.path.dirname(destino).lower() == "pygame" and destino.lower().endswith(".dll")}
a.binaries = [b for b in a.binaries if not (os.path.dirname(b[0]) == "" and b[0].lower() in DO_PYGAME)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NOME_DO_JOGO,
    icon=ICONE,
    version=ARQUIVO_DE_VERSAO if os.path.exists(ARQUIVO_DE_VERSAO) else None,
    console=False,                                            # (sem a janela preta do terminal)
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NOME_DO_JOGO, upx=False)
