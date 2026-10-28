"""Constrói o instalador do Ecos da Cripta para Windows e o pacote para mandar aos amigos: um comando só (MP9).

    python ferramentas/instalador/construir.py              -> dist/Ecos da Cripta <versão> - para enviar.zip
    python ferramentas/instalador/construir.py --so-pasta   -> só a pasta dist/Ecos da Cripta/ (sem o Inno Setup)

Passos:
    1. o ícone (ferramentas/gerar_icone.py), o arquivo de versão do .exe (build/versao_do_exe.txt, de src/versao.py)
       e o tutorial (tutorial/como_instalar_e_jogar.html com as imagens embutidas: um arquivo só)
    2. a pasta do jogo com o PyInstaller (ecos_da_cripta.spec): o .exe + o Python + pygame + assets + dados
    3. confere o .exe: roda "Ecos da Cripta.exe --verificar" sem janela (título, acampamento, uma luta e uma
       partida em grupo só neste PC)
    4. o instalador com o Inno Setup (ecos_da_cripta.iss): atalhos, desinstalador, português, o tutorial junto
    5. o pacote para enviar: o instalador + o tutorial, numa pasta e num .zip (nada do código, dos testes ou das
       ferramentas)

Precisa (só para construir; quem joga não precisa de nada): PyInstaller no venv e o Inno Setup 6.
As imagens do tutorial: capturas_do_tutorial.py (rodar de novo quando as telas mudarem).
"""

import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(RAIZ, "src"))
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))

from versao import NOME_DO_JOGO, VERSAO  # noqa: E402

DIST = os.path.join(RAIZ, "dist")
BUILD = os.path.join(RAIZ, "build")
PASTA_DO_JOGO = os.path.join(DIST, NOME_DO_JOGO)
EXECUTAVEL = os.path.join(PASTA_DO_JOGO, f"{NOME_DO_JOGO}.exe")
ONDE_PROCURAR_O_ISCC = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),   # (winget, por usuário)
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Inno Setup 6", "ISCC.exe"),
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Inno Setup 6", "ISCC.exe"),
]
TEMPO_PARA_VERIFICAR = 180
TUTORIAL_FONTE = os.path.join(AQUI, "tutorial", "como_instalar_e_jogar.html")
NOME_DO_TUTORIAL = "Como instalar e jogar.html"           # (o mesmo nome no .iss: #define Tutorial)
NOME_DO_INSTALADOR = f"Instalar {NOME_DO_JOGO} {VERSAO}.exe"
NOME_DO_PACOTE = f"{NOME_DO_JOGO} {VERSAO} - para enviar"


def numeros_da_versao(versao=VERSAO):
    """"1.1.0" -> (1, 1, 0, 0) (o Windows quer 4 números)."""
    numeros = [int(parte) for parte in versao.split(".") if parte.isdigit()][:4]
    return tuple(numeros + [0] * (4 - len(numeros)))


def texto_do_arquivo_de_versao(versao=VERSAO):
    """As propriedades do .exe (botão direito > Propriedades > Detalhes), no formato do PyInstaller."""
    numeros = numeros_da_versao(versao)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={numeros}, prodvers={numeros}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041604B0', [
      StringStruct('CompanyName', '{NOME_DO_JOGO}'),
      StringStruct('FileDescription', '{NOME_DO_JOGO}'),
      StringStruct('FileVersion', '{versao}'),
      StringStruct('InternalName', '{NOME_DO_JOGO}'),
      StringStruct('OriginalFilename', '{NOME_DO_JOGO}.exe'),
      StringStruct('ProductName', '{NOME_DO_JOGO}'),
      StringStruct('ProductVersion', '{versao}')])]),
    VarFileInfo([VarStruct('Translation', [0x0416, 1200])])
  ]
)
"""


def achar_iscc():
    """O compilador do Inno Setup (ISCC.exe) ou None."""
    no_path = shutil.which("ISCC") or shutil.which("iscc")
    if no_path:
        return no_path
    return next((caminho for caminho in ONDE_PROCURAR_O_ISCC if os.path.isfile(caminho)), None)


def tamanho_da_pasta(pasta):
    return sum(os.path.getsize(os.path.join(raiz, nome)) for raiz, _, nomes in os.walk(pasta) for nome in nomes)


def passo(texto):
    print(f"\n=== {texto}", flush=True)


def tutorial_pronto(fonte=TUTORIAL_FONTE, versao=VERSAO):
    """O HTML do tutorial num arquivo só: a versão no texto e as imagens (imagens/x.jpg) embutidas."""
    with open(fonte, encoding="utf-8") as arquivo:
        html = arquivo.read().replace("{{VERSAO}}", versao)
    pasta = os.path.dirname(fonte)

    def embutir(achado):
        caminho = os.path.join(pasta, achado.group(1))
        tipo = "image/jpeg" if caminho.lower().endswith((".jpg", ".jpeg")) else "image/png"
        with open(caminho, "rb") as imagem:
            return f'src="data:{tipo};base64,{base64.b64encode(imagem.read()).decode("ascii")}"'
    html = re.sub(r'src="(imagens/[^"]+)"', embutir, html)
    if "{{" in html or 'src="imagens/' in html:
        raise RuntimeError("O tutorial ficou com uma marca ou imagem sem trocar.")
    return html


def preparar():
    from gerar_icone import gerar
    passo("Ícone, versão do .exe e tutorial")
    for nome, caminho in gerar().items():
        print(f"  {nome}: {os.path.relpath(caminho, RAIZ)}")
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "versao_do_exe.txt"), "w", encoding="utf-8") as arquivo:
        arquivo.write(texto_do_arquivo_de_versao())
    with open(os.path.join(BUILD, NOME_DO_TUTORIAL), "w", encoding="utf-8") as arquivo:
        arquivo.write(tutorial_pronto())
    print(f"  {NOME_DO_JOGO} {VERSAO}; tutorial: {os.path.getsize(os.path.join(BUILD, NOME_DO_TUTORIAL)) // 1024} KB")


def empacotar():
    passo("PyInstaller (a pasta do jogo)")
    comando = [sys.executable, "-m", "PyInstaller", os.path.join(AQUI, "ecos_da_cripta.spec"), "--noconfirm",
               "--clean", "--log-level", "WARN", "--distpath", DIST, "--workpath", os.path.join(BUILD, "pyinstaller")]
    subprocess.run(comando, cwd=RAIZ, check=True, env=dict(os.environ, PYGAME_HIDE_SUPPORT_PROMPT="1"))
    print(f"  {os.path.relpath(PASTA_DO_JOGO, RAIZ)}: {tamanho_da_pasta(PASTA_DO_JOGO) / 2 ** 20:.0f} MB")


def conferir_o_exe(executavel=EXECUTAVEL):
    """Roda o .exe com --verificar (sem janela e com um save temporário). Erro: RuntimeError com o motivo."""
    passo("Conferindo o .exe (título, acampamento, uma luta e uma partida em grupo, sem janela)")
    relatorio = os.path.join(tempfile.mkdtemp(prefix="ecos_verificar_"), "relatorio.txt")
    ambiente = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    inicio = time.monotonic()
    processo = subprocess.run([executavel, "--verificar", relatorio], env=ambiente, timeout=TEMPO_PARA_VERIFICAR)
    texto = open(relatorio, encoding="utf-8").read() if os.path.exists(relatorio) else "(sem relatório)"
    if processo.returncode != 0 or texto.strip() != "ok":
        raise RuntimeError(f"O .exe não abriu direito (código {processo.returncode}):\n{texto}")
    print(f"  ok ({time.monotonic() - inicio:.1f} s)")


def fazer_o_instalador():
    passo("Inno Setup (o instalador)")
    iscc = achar_iscc()
    if iscc is None:
        raise RuntimeError("Não achei o Inno Setup 6 (ISCC.exe). Instale com: winget install JRSoftware.InnoSetup")
    subprocess.run([iscc, "/Q", f"/DVersao={VERSAO}", f"/DRaiz={RAIZ}", os.path.join(AQUI, "ecos_da_cripta.iss")],
                   check=True)                                       # (/Q: só avisos e erros)
    instalador = os.path.join(DIST, NOME_DO_INSTALADOR)
    print(f"  {os.path.relpath(instalador, RAIZ)}: {os.path.getsize(instalador) / 2 ** 20:.0f} MB")
    return instalador


def montar_pacote(instalador):
    """O que se manda aos amigos: só o instalador e o tutorial, numa pasta e num .zip. Devolve o caminho do .zip."""
    passo("Pacote para enviar")
    pasta = os.path.join(DIST, NOME_DO_PACOTE)
    arquivo_zip = pasta + ".zip"
    shutil.rmtree(pasta, ignore_errors=True)
    if os.path.exists(arquivo_zip):
        os.remove(arquivo_zip)
    os.makedirs(pasta)
    shutil.copy2(instalador, os.path.join(pasta, NOME_DO_INSTALADOR))
    shutil.copy2(os.path.join(BUILD, NOME_DO_TUTORIAL), os.path.join(pasta, NOME_DO_TUTORIAL))
    with zipfile.ZipFile(arquivo_zip, "w") as pacote:
        pacote.write(os.path.join(pasta, NOME_DO_INSTALADOR), NOME_DO_INSTALADOR, zipfile.ZIP_STORED)   # (já comprimido)
        pacote.write(os.path.join(pasta, NOME_DO_TUTORIAL), NOME_DO_TUTORIAL, zipfile.ZIP_DEFLATED)
    print(f"  {os.path.relpath(pasta, RAIZ)}\\ (o instalador + o tutorial)")
    print(f"  {os.path.relpath(arquivo_zip, RAIZ)}: {os.path.getsize(arquivo_zip) / 2 ** 20:.0f} MB")
    return arquivo_zip


def main(argumentos):
    so_pasta = "--so-pasta" in argumentos
    preparar()
    empacotar()
    conferir_o_exe()
    if so_pasta:
        print(f"\nPronto: {EXECUTAVEL}")
        return
    instalador = fazer_o_instalador()
    arquivo_zip = montar_pacote(instalador)
    print(f"\nPronto para mandar: {arquivo_zip}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        sys.exit(1)
