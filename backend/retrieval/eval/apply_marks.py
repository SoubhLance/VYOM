"""Apply marks from a compact marks file to a blank blind sheet.

Reads blind_sheet.blank.txt (all marks are [ ]) and marks_pass1.txt,
then writes blind_sheet.txt with [x] and [~] applied to the correct verses.

Run from repo root:
    python retrieval/eval/apply_marks.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")

BLANK_DEFAULT = ROOT / "retrieval" / "eval" / "blind_sheet.blank.txt"
MARKS_DEFAULT = ROOT / "retrieval" / "eval" / "marks_pass1.txt"
OUTPUT_DEFAULT = ROOT / "retrieval" / "eval" / "blind_sheet.txt"

_HEADER_RE = re.compile(r"^\s*\[(\d+)\]\s")
_VERSE_RE = re.compile(r"^(\s*)\[\s\]\s+(\d+\.\d+)\s*:")

# Marks line format: NN x: v1 v2 ... | ~: v3 v4 ...
_MARKS_LINE_RE = re.compile(
    r"^(\d+)\s+x:\s*([\d.\s]*?)\s*\|\s*~:\s*([\d.\s]*)$"
)


def parse_marks(marks_text: str) -> dict[int, dict]:
    """Parse marks_pass1.txt.

    Returns:
        dict: {section_num: {"x": set of verse ids, "~": set of verse ids}}
    """
    marks = {}
    for line_num, line in enumerate(marks_text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        m = _MARKS_LINE_RE.match(line)
        if not m:
            raise ValueError(f"Marks line {line_num}: cannot parse: {line!r}")
        sec = int(m.group(1))
        x_ids = set(m.group(2).split()) if m.group(2).strip() else set()
        tilde_ids = set(m.group(3).split()) if m.group(3).strip() else set()
        if sec in marks:
            raise ValueError(f"Marks line {line_num}: duplicate section [{sec:02d}]")
        marks[sec] = {"x": x_ids, "~": tilde_ids}
    return marks


def parse_sheet_sections(sheet_text: str) -> dict[int, list[tuple[int, str]]]:
    """Parse the blank sheet into sections.

    Returns:
        dict: {section_num: [(line_index, verse_id), ...]}
    """
    sections: dict[int, list[tuple[int, str]]] = {}
    cur_sec = None
    for idx, line in enumerate(sheet_text.splitlines()):
        hm = _HEADER_RE.match(line)
        if hm:
            cur_sec = int(hm.group(1))
            sections.setdefault(cur_sec, [])
            continue
        vm = _VERSE_RE.match(line)
        if vm and cur_sec is not None:
            vid = vm.group(2)
            sections[cur_sec].append((idx, vid))
    return sections


def validate(marks: dict[int, dict], sections: dict[int, list[tuple[int, str]]]):
    """Validate marks against sheet sections. Returns list of errors."""
    errors = []

    # Every section 01-20 must have a marks line
    for sec in range(1, 21):
        if sec not in marks:
            errors.append(f"Section [{sec:02d}]: no marks line found")
        if sec not in sections:
            errors.append(f"Section [{sec:02d}]: not found in sheet")

    # Per-section validation
    for sec, m in sorted(marks.items()):
        if sec not in sections:
            continue
        sheet_vids = {vid for _, vid in sections[sec]}
        x_set = m["x"]
        tilde_set = m["~"]

        # Every verse in marks must exist in that section of the sheet
        for vid in x_set:
            if vid not in sheet_vids:
                errors.append(f"Section [{sec:02d}]: x-marked verse {vid} not in sheet")
        for vid in tilde_set:
            if vid not in sheet_vids:
                errors.append(f"Section [{sec:02d}]: ~-marked verse {vid} not in sheet")

        # No verse in both x and ~
        overlap = x_set & tilde_set
        if overlap:
            errors.append(f"Section [{sec:02d}]: verse(s) in both x and ~: {sorted(overlap)}")

        # No duplicate ids (within a mark category they're sets, so check across)
        # Already handled by set intersection above

    return errors


def apply_marks(
    blank_path: Path = BLANK_DEFAULT,
    marks_path: Path = MARKS_DEFAULT,
    output_path: Path | None = OUTPUT_DEFAULT,
    dry_run: bool = False,
) -> tuple[str, dict]:
    """Apply marks to blank sheet. Returns (output_text, stats_dict)."""
    blank_text = blank_path.read_text(encoding="utf-8")
    marks_text = marks_path.read_text(encoding="utf-8")

    marks = parse_marks(marks_text)
    sections = parse_sheet_sections(blank_text)

    # Validate
    errors = validate(marks, sections)
    if errors:
        print("VALIDATION ERRORS (no output written):")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    # Build line_index -> mark mapping
    line_marks: dict[int, str] = {}
    for sec, m in marks.items():
        for line_idx, vid in sections[sec]:
            if vid in m["x"]:
                line_marks[line_idx] = "x"
            elif vid in m["~"]:
                line_marks[line_idx] = "~"

    # Apply marks
    lines = blank_text.splitlines(keepends=True)
    total_x = 0
    total_tilde = 0
    total_blank = 0
    stats: dict[int, dict] = {}
    cur_sec = None

    for idx, line in enumerate(lines):
        hm = _HEADER_RE.match(line)
        if hm:
            cur_sec = int(hm.group(1))
            stats[cur_sec] = {"x": 0, "~": 0, "blank": 0}

        vm = _VERSE_RE.match(line)
        if vm and cur_sec is not None:
            if idx in line_marks:
                mark = line_marks[idx]
                # Replace ONLY the first occurrence of "[ ]" with "[x]" or "[~]"
                lines[idx] = line.replace("[ ]", f"[{mark}]", 1)
                stats[cur_sec][mark] += 1
                if mark == "x":
                    total_x += 1
                else:
                    total_tilde += 1
            else:
                stats[cur_sec]["blank"] += 1
                total_blank += 1

    output_text = "".join(lines)

    # Print per-question stats
    print(f"{'Q':>3}  {'[x]':>5}  {'[~]':>5}  {'[ ]':>5}  {'pool':>5}")
    print("-" * 32)
    for sec in sorted(stats):
        s = stats[sec]
        pool = s["x"] + s["~"] + s["blank"]
        print(f"{sec:>3}  {s['x']:>5}  {s['~']:>5}  {s['blank']:>5}  {pool:>5}")
    print("-" * 32)
    total_pool = total_x + total_tilde + total_blank
    print(f"ALL  {total_x:>5}  {total_tilde:>5}  {total_blank:>5}  {total_pool:>5}")

    if not dry_run and output_path:
        output_path.write_text(output_text, encoding="utf-8")
        print(f"\nWrote {output_path}")

    return output_text, {
        "total_x": total_x,
        "total_tilde": total_tilde,
        "total_blank": total_blank,
        "per_section": stats,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Apply marks from marks file to blank sheet")
    ap.add_argument("--blank", type=Path, default=BLANK_DEFAULT, help="Blank sheet")
    ap.add_argument("--marks", type=Path, default=MARKS_DEFAULT, help="Marks file")
    ap.add_argument("--output", type=Path, default=OUTPUT_DEFAULT, help="Output sheet")
    ap.add_argument("--dry-run", action="store_true", help="Don't write output")
    args = ap.parse_args()

    apply_marks(
        blank_path=args.blank,
        marks_path=args.marks,
        output_path=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
