import difflib
from pathlib import Path

bak_file = Path("backend/llm/client.py.bak")
cur_file = Path("backend/llm/client.py")

bak_lines = bak_file.read_text(encoding="utf-8").splitlines(keepends=True)
cur_lines = cur_file.read_text(encoding="utf-8").splitlines(keepends=True)

diff = difflib.unified_diff(
    bak_lines,
    cur_lines,
    fromfile="backend/llm/client.py.bak",
    tofile="backend/llm/client.py"
)

diff_text = "".join(diff)
print(diff_text)

