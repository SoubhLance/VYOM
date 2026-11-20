import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("backend/data/multimodal/source/_probe/test_cit_inspection.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace header
code = "import sys\nsys.stdout.reconfigure(encoding='utf-8')\n" + code

