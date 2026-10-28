# Adiciona src/ ao sys.path para que os módulos de src/ possam importar
# uns aos outros (ex.: "from roguelike.run import Run") durante os testes.
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture(autouse=True)
def pasta_do_jogador_temporaria(tmp_path, monkeypatch):
    """Os testes nunca leem nem gravam os saves de verdade: opções, progresso e run vão para uma pasta temporária."""
    from caminhos import CAMINHOS
    monkeypatch.setattr(CAMINHOS, "base_do_jogador", str(tmp_path / "jogador"))
    monkeypatch.setattr(CAMINHOS, "perfil", None)
