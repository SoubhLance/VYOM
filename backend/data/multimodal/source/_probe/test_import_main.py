import sys
from pathlib import Path

ROOT = Path("backend").resolve()
sys.path.insert(0, str(ROOT))

from api.main import app
print("App import successful!")

