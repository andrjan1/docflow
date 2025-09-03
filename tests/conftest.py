import sys
from pathlib import Path
import pytest

# ensure src in path
ROOT = Path(__file__).parent.parent
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

@pytest.fixture(autouse=True)
def cwd_tmp_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path
