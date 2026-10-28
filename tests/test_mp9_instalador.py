"""MP9: o jogo instalável para Windows. O ícone (gerado por código), o ícone da janela, a conferência sem janela que o
construtor roda no .exe, o registro de erros e as receitas do PyInstaller e do Inno Setup.

Construir de verdade (PyInstaller + Inno Setup, ~1,5 min) fica fora do pytest: python ferramentas/instalador/construir.py
(ele mesmo confere o .exe com --verificar).
"""

import os
import re
import subprocess
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALADOR = os.path.join(RAIZ, "ferramentas", "instalador")
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))
sys.path.insert(0, INSTALADOR)

import construir  # noqa: E402
import gerar_icone  # noqa: E402


def ler(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read()


# ---------------- o ícone ----------------
def test_o_icone_do_jogo_e_o_que_o_gerador_faz():
    """assets/icone está igual ao gerador (mudou o desenho: python ferramentas/gerar_icone.py)."""
    imagens = gerar_icone.todos_os_tamanhos()
    pasta = os.path.join(RAIZ, "assets", "icone")
    for nome, tamanho in (("icone_32.png", 32), ("icone_256.png", 256)):
        assert Image.open(os.path.join(pasta, nome)).convert("RGBA").tobytes() == imagens[tamanho].tobytes(), nome
    ico = Image.open(os.path.join(pasta, gerar_icone.NOME_DO_ICO))
    assert sorted(ico.info["sizes"]) == [(t, t) for t in gerar_icone.TAMANHOS_DO_ICO]
    for tamanho in gerar_icone.TAMANHOS_DO_ICO:
        ico.size = (tamanho, tamanho)
        assert ico.convert("RGBA").tobytes() == imagens[tamanho].tobytes(), tamanho


def test_o_icone_e_pixel_art_com_fundo_transparente():
    imagens = gerar_icone.todos_os_tamanhos()
    assert imagens[64].tobytes() == imagens[32].resize((64, 64), Image.NEAREST).tobytes()   # ampliado sem borrar
    for tamanho in (16, 24, 32):
        imagem = imagens[tamanho]
        assert imagem.getpixel((0, 0))[3] == 0 and imagem.getpixel((tamanho - 1, 0))[3] == 0     # cantos vazios
        assert imagem.getpixel((tamanho // 2, tamanho // 2))[3] == 255
        olhos = [(x, y) for y in range(tamanho) for x in range(tamanho)
                 if imagem.getpixel((x, y))[:3] == gerar_icone.COR["olho"]]
        esquerdos = {(x, y) for x, y in olhos if x < tamanho / 2}
        direitos = {(tamanho - 1 - x, y) for x, y in olhos if x >= tamanho / 2}
        assert esquerdos and esquerdos == direitos, tamanho                                       # dois olhos, iguais


def test_a_janela_usa_o_icone():
    pygame.init()
    from telas.base import colocar_icone
    assert colocar_icone()


# ---------------- o jogo empacotado ----------------
def test_verificar_abre_o_jogo_sem_janela(tmp_path):
    """O que o construtor roda no .exe: título, acampamento e uma luta, sem janela e sem mexer nos saves."""
    relatorio = tmp_path / "relatorio.txt"
    ambiente = dict(os.environ, ECOS_DA_CRIPTA_DADOS=str(tmp_path / "jogador"))
    processo = subprocess.run([sys.executable, os.path.join(RAIZ, "src", "jogar.py"), "--verificar", str(relatorio)],
                              cwd=RAIZ, env=ambiente, timeout=180)
    assert processo.returncode == 0 and relatorio.read_text(encoding="utf-8") == "ok"
    assert not (tmp_path / "jogador").exists()                     # (o save da conferência é temporário)


def test_erro_que_fecha_o_jogo_fica_em_erros_txt():
    import jogar
    from caminhos import CAMINHOS
    try:
        raise ValueError("teste do registro de erros")
    except ValueError:
        jogar.registrar_erro()
    texto = ler(CAMINHOS.save("erros.txt"))
    assert "teste do registro de erros" in texto and "versão" in texto


# ---------------- o jogo sem o que não precisa ----------------
def test_o_jogo_nao_usa_numpy():
    """As luzes do salão (título) vêm prontas em PNG: o numpy fica só nas ferramentas e não vai no instalador."""
    for raiz, _, nomes in os.walk(os.path.join(RAIZ, "src")):
        for nome in nomes:
            if nome.endswith(".py"):
                texto = ler(os.path.join(raiz, nome))
                assert "import numpy" not in texto and "surfarray" not in texto, nome


def test_as_luzes_do_salao_sao_as_que_a_ferramenta_calcula():
    sys.path.insert(0, os.path.join(RAIZ, "ferramentas", "sprites_macabros"))
    import gerar_luzes_do_salao
    pygame.init()
    for nome, calculada in gerar_luzes_do_salao.luzes().items():
        carregada = pygame.image.load(os.path.join(gerar_luzes_do_salao.PASTA, nome))
        assert carregada.get_size() == calculada.get_size(), nome
        assert pygame.image.tobytes(carregada, "RGBA") == pygame.image.tobytes(calculada, "RGBA"), nome


# ---------------- as receitas da construção ----------------
def test_a_receita_do_pyinstaller_leva_o_jogo_inteiro():
    spec = ler(os.path.join(INSTALADOR, "ecos_da_cripta.spec"))
    assert '"assets"), "assets")' in spec                          # a mesma árvore que caminhos.py procura
    assert 'os.path.join("src", "roguelike", "dados")' in spec
    assert "console=False" in spec and "ecos_da_cripta.ico" in spec and "exclude_binaries=True" in spec
    for fora in ("numpy", "PIL", "pytest", "_ssl", "_hashlib"):    # (o que só as ferramentas e os testes usam)
        assert f'"{fora}"' in spec
    assert "DO_PYGAME" in spec                                     # as DLLs do pygame não vão duas vezes


def test_o_tutorial_vira_um_arquivo_so():
    html = construir.tutorial_pronto(versao="9.9.9")
    assert "9.9.9" in html and "{{" not in html and 'src="imagens/' not in html
    assert html.count('src="data:image/jpeg;base64,') == len(os.listdir(os.path.join(INSTALADOR, "tutorial", "imagens")))
    assert "https://www.radmin-vpn.com/br/" in html and "Criar rede" in html and "Entrar em rede" in html
    iss = ler(os.path.join(INSTALADOR, "ecos_da_cripta.iss"))
    assert f'#define Tutorial "{construir.NOME_DO_TUTORIAL}"' in iss   # o tutorial também vai na instalação


def test_o_instalador_tem_atalhos_desinstalador_e_portugues():
    from telas.base import ID_DO_APP
    iss = ler(os.path.join(INSTALADOR, "ecos_da_cripta.iss"))
    assert "PrivilegesRequired=lowest" in iss                      # sem pedir administrador
    assert "BrazilianPortuguese.isl" in iss
    assert re.search(r"AppId=\{\{[0-9A-F-]{36}\}", iss)            # o mesmo id em toda versão (reinstalar = atualizar)
    assert "{autodesktop}" in iss and "{autoprograms}" in iss and "UninstallDisplayIcon" in iss
    assert f'#define IdDoApp "{ID_DO_APP}"' in iss                 # o atalho e a janela na mesma barra de tarefas
    assert "%APPDATA%" in iss and "{userappdata}" not in iss       # os saves ficam (nada apaga a pasta do jogador)


def test_a_versao_do_exe_sai_de_versao_py():
    from versao import VERSAO
    assert construir.numeros_da_versao("2.3") == (2, 3, 0, 0)
    assert construir.numeros_da_versao("1.1.0") == (1, 1, 0, 0)
    texto = construir.texto_do_arquivo_de_versao()
    assert f"FileVersion', '{VERSAO}'" in texto and str(construir.numeros_da_versao()) in texto
    iscc = construir.achar_iscc()
    assert iscc is None or iscc.lower().endswith("iscc.exe")
