"""Apply human judgments from blind sheet to produce questions.v2.jsonl and questions.v2_lenient.jsonl.
Run from repo root:
    python retrieval/eval/apply_judgments.py
"""
import argparse
import json
import re
import sys
import warnings
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingestion"))
sys.path.insert(0, str(ROOT / "retrieval"))
sys.stdout.reconfigure(encoding="utf-8")

from clean import load_clean  # noqa: E402
from router import load_valid_ids, parse_verse_ref  # noqa: E402

QUESTIONS_DEFAULT = ROOT / "retrieval" / "eval" / "questions.jsonl"
SHEET_DEFAULT = ROOT / "retrieval" / "eval" / "blind_sheet.txt"
OUT_STRICT_DEFAULT = ROOT / "retrieval" / "eval" / "questions.v2.jsonl"
OUT_LENIENT_DEFAULT = ROOT / "retrieval" / "eval" / "questions.v2_lenient.jsonl"

_HEADER_RE = re.compile(r"^\s*\[(\d+)\]\s*(?:\(([^)]*)\)\s*)?(.*)$")
_VERSE_RE = re.compile(r"^\s*\[([^0-9\]]*)\]\s*([0-9]+\.[0-9]+)\s*:")


def normalize_q(text: str) -> str:
    """Normalize question text for matching: collapse whitespace, strip, lowercase."""
    return re.sub(r"\s+", " ", text.strip().lower())


def load_dataset_verse_ids():
    return {v["verse_id"] for v in load_clean()}


def parse_sheet(sheet_text: str, valid_verses: set[str] | None = None):
    """Parse judged blind_sheet text into structured judgments and collected warnings.

    Returns:
        dict: {normalize_q(q): {"original_q": q, "strict": [vid, ...], "lenient": [vid, ...], "all_marked": [(mark, vid), ...]}}
        list: list of warning message strings
    """
    lines = sheet_text.splitlines()
    parsed = {}
    warn_msgs = []

    cur_q = None
    cur_marks = []
    seen_verses = set()

    def finalize_current():
        if cur_q is None:
            return
        strict_gold = [vid for mark, vid in cur_marks if mark == "x"]
        lenient_gold = [vid for mark, vid in cur_marks if mark in ("x", "~")]
        norm_k = normalize_q(cur_q)
        parsed[norm_k] = {
            "original_q": cur_q,
            "strict": strict_gold,
            "lenient": lenient_gold,
            "all_marked": list(cur_marks),
        }

    for line_num, line in enumerate(lines, 1):
        sline = line.strip()
        if not sline or sline.startswith("#") or sline.startswith("Pool size:"):
            continue

        hm = _HEADER_RE.match(sline)
        if hm and not _VERSE_RE.match(sline):
            finalize_current()
            cur_q = hm.group(3).strip()
            cur_marks = []
            seen_verses = set()
            continue

        vm = _VERSE_RE.match(line)
        if vm:
            if cur_q is None:
                warn_msgs.append(f"Line {line_num}: verse entry found before any question header: {line}")
                continue

            raw_mark = vm.group(1)
            vid = vm.group(2)

            if valid_verses is not None:
                assert vid in valid_verses, f"Line {line_num}: verse id '{vid}' does not exist in dataset"

            if vid in seen_verses:
                warn_msgs.append(f"Duplicated verse: '{vid}' appears multiple times under question '{cur_q}'")
            seen_verses.add(vid)

            mark_strip = raw_mark.strip()
            if mark_strip in ("x", "X"):
                cur_marks.append(("x", vid))
            elif mark_strip == "~":
                cur_marks.append(("~", vid))
            elif mark_strip == "":
                cur_marks.append(("", vid))
            else:
                raise ValueError(
                    f"Line {line_num}: invalid mark '[{raw_mark}]' for verse '{vid}' under question '{cur_q}'. "
                    f"Accepted marks are [x], [X], [~], or blank [ ]."
                )

    finalize_current()
    return parsed, warn_msgs


def apply_judgments(
    sheet_path: Path,
    questions_path: Path,
    out_strict_path: Path | None = None,
    out_lenient_path: Path | None = None,
    valid_verses: set[str] | None = None,
    valid_ids_for_router: set[str] | None = None,
    allow_partial: bool = False,
):
    if valid_verses is None:
        valid_verses = load_dataset_verse_ids()
    if valid_ids_for_router is None:
        valid_ids_for_router = load_valid_ids()

    sheet_text = sheet_path.read_text(encoding="utf-8")
    judgments, warn_msgs = parse_sheet(sheet_text, valid_verses=valid_verses)

    with open(questions_path, encoding="utf-8") as f:
        original_questions = [json.loads(line) for line in f if line.strip()]

    # 1. Fail loudly if sheet contains entries that match no question in questions.jsonl
    q_norm_map = {normalize_q(q_item["q"]): q_item for q_item in original_questions}
    unknown_sheet_entries = [
        judgments[k]["original_q"] for k in judgments if k not in q_norm_map
    ]
    if unknown_sheet_entries:
        raise ValueError(
            f"Sheet contains {len(unknown_sheet_entries)} entry/entries that match no question in questions.jsonl:\n"
            + "\n".join(f"  - {q}" for q in sorted(unknown_sheet_entries))
        )

    # 2. Fail loudly if a non-routed question in questions.jsonl has no sheet entry
    missing_non_routed = [
        q_item["q"]
        for q_item in original_questions
        if not parse_verse_ref(q_item["q"], valid_ids_for_router)
        and normalize_q(q_item["q"]) not in judgments
    ]
    if missing_non_routed:
        raise ValueError(
            f"Non-routed question(s) in questions.jsonl missing from sheet ({len(missing_non_routed)}):\n"
            + "\n".join(f"  - {q}" for q in sorted(missing_non_routed))
        )

    # 3. Explicit check that questions keeping original gold are exactly the routed ones
    kept_original_gold = [
        q_item["q"]
        for q_item in original_questions
        if normalize_q(q_item["q"]) not in judgments
    ]
    routed_questions = [
        q_item["q"]
        for q_item in original_questions
        if bool(parse_verse_ref(q_item["q"], valid_ids_for_router))
    ]
    print(f"\nQuestions keeping original gold (routed lookups, n={len(kept_original_gold)}):")
    for q in kept_original_gold:
        print(f"  - {q}")
    if set(kept_original_gold) != set(routed_questions):
        raise ValueError(
            f"Questions keeping original gold do not match routed lookups exactly.\n"
            f"Kept original ({len(kept_original_gold)}): {kept_original_gold}\n"
            f"Routed ({len(routed_questions)}):        {routed_questions}"
        )

    for w in warn_msgs:
        warnings.warn(w, UserWarning, stacklevel=2)

    strict_rows = []
    lenient_rows = []
    dropped_strict = []
    dropped_lenient = []
    possibly_unjudged = []

    print("\n=== JUDGMENT APPLICATION SUMMARY ===")
    for q_item in original_questions:
        q_text = q_item["q"]
        norm_k = normalize_q(q_text)
        old_gold = q_item.get("gold", [])
        q_type = q_item.get("type", "")

        if norm_k in judgments:
            j_data = judgments[norm_k]
            new_strict = j_data["strict"]
            new_lenient = j_data["lenient"]

            # Check if all candidate marks were blank
            positive_marks = [m for m, _ in j_data["all_marked"] if m in ("x", "~")]
            if not positive_marks:
                possibly_unjudged.append((q_type, q_text))

            # Strict policy: drop if [x] is empty, do NOT fall back to old gold
            if not new_strict:
                dropped_strict.append((q_type, q_text))
            else:
                strict_rows.append({**q_item, "gold": new_strict})

            # Lenient policy: drop if [x]+[~] is empty, do NOT fall back to old gold
            if not new_lenient:
                dropped_lenient.append((q_type, q_text))
            else:
                lenient_rows.append({**q_item, "gold": new_lenient})

            old_set = set(old_gold)
            strict_set = set(new_strict)
            added = sorted(strict_set - old_set)
            removed = sorted(old_set - strict_set)

            print(f"\n[{q_type}] {q_text}")
            print(f"  old gold ({len(old_gold)}): {old_gold}")
            print(f"  v2 strict ({len(new_strict)}): {new_strict} | added: {added} | removed: {removed}")
            if new_lenient != new_strict:
                print(f"  v2 lenient ({len(new_lenient)}): {new_lenient}")
        else:
            # Questions not in sheet (routed lookups) keep original gold
            strict_rows.append({**q_item, "gold": list(old_gold)})
            lenient_rows.append({**q_item, "gold": list(old_gold)})
            print(f"\n[{q_type}] {q_text} [kept original gold - routed lookup]")
            print(f"  gold ({len(old_gold)}): {old_gold}")

    # Report dropped questions
    print("\n=== DROPPED QUESTIONS IN STRICT V2 (empty [x] gold) ===")
    if dropped_strict:
        for t, q in dropped_strict:
            print(f"  [{t}] {q}")
    else:
        print("  (None)")

    print("\n=== DROPPED QUESTIONS IN LENIENT V2 (empty [x]+[~] gold) ===")
    if dropped_lenient:
        for t, q in dropped_lenient:
            print(f"  [{t}] {q}")
    else:
        print("  (None)")

    # Separately list possibly unjudged questions
    print("\n=== POSSIBLY UNJUDGED QUESTIONS (in sheet, but 0 positive marks of any kind) ===")
    if possibly_unjudged:
        for t, q in possibly_unjudged:
            print(f"  [{t}] {q}")
    else:
        print("  (None)")

    # Print per-type n for each output file
    def print_counts(title, rows):
        counts = Counter(r["type"] for r in rows)
        print(f"\n=== {title} ===")
        print(f"{'type':<20}{'n':>4}")
        for t in sorted(counts):
            print(f"{t:<20}{counts[t]:>4}")
        print(f"{'ALL':<20}{len(rows):>4}")

    print_counts("questions.v2.jsonl (strict)", strict_rows)
    print_counts("questions.v2_lenient.jsonl (lenient)", lenient_rows)

    has_issues = bool(dropped_strict or dropped_lenient or possibly_unjudged)
    if has_issues:
        if not allow_partial:
            print("\nERROR: Incomplete judgments detected! No output files will be written.")
            print("Run with --allow-partial to force writing partial files.")
            sys.exit(1)
        else:
            print("\n" + "=" * 60)
            print("PARTIAL GOLD: do not run evals on these files")
            print("=" * 60 + "\n")

    if out_strict_path:
        out_strict_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_strict_path, "w", encoding="utf-8") as f:
            for r in strict_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if out_lenient_path:
        out_lenient_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_lenient_path, "w", encoding="utf-8") as f:
            for r in lenient_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return strict_rows, lenient_rows, warn_msgs, dropped_strict, dropped_lenient, possibly_unjudged


def main():
    ap = argparse.ArgumentParser(description="Apply judged blind sheet to generate questions.v2.jsonl")
    ap.add_argument("--sheet", type=Path, default=SHEET_DEFAULT, help="Judged blind sheet text file.")
    ap.add_argument("--questions", type=Path, default=QUESTIONS_DEFAULT, help="Original questions.jsonl.")
    ap.add_argument("--out-strict", type=Path, default=OUT_STRICT_DEFAULT, help="Output strict v2 questions.")
    ap.add_argument("--out-lenient", type=Path, default=OUT_LENIENT_DEFAULT, help="Output lenient v2 questions.")
    ap.add_argument("--allow-partial", action="store_true", help="Allow writing output files even if some questions are dropped or possibly unjudged.")
    args = ap.parse_args()

    apply_judgments(
        sheet_path=args.sheet,
        questions_path=args.questions,
        out_strict_path=args.out_strict,
        out_lenient_path=args.out_lenient,
        allow_partial=args.allow_partial,
    )
    print(f"\nSaved v2 strict to:  {args.out_strict}")
    print(f"Saved v2 lenient to: {args.out_lenient}")


if __name__ == "__main__":
    main()
