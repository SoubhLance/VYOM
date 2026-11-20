from pathlib import Path

def list_keys(file_path):
    p = Path(file_path)
    if not p.exists():
        print(f"{file_path} does not exist")
        return
    print(f"--- Keys in {file_path} ---")
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key = line.split("=", 1)[0].strip()
                print(f"  {key}")

list_keys("backend/.env")
list_keys(".env")

