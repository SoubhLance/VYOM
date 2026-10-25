import json
import pytest
from pathlib import Path

from retrieval.eval.apply_judgments import apply_judgments, parse_sheet


def test_marks_parse_accepts_valid():
    sheet_content = """# Legend: [x], [X], [~], blank
[01] (conceptual) What does the Gita say about karma?
  [x] 2.47: Work without attachment
  [X] 3.19: Perform obligatory work
  [~] 2.48: Equanimity in action
  [ ] 4.20: Action without results
"""
    valid_verses = {"2.47", "3.19", "2.48", "4.20"}
    judgments, warnings_list = parse_sheet(sheet_content, valid_verses=valid_verses)

    norm_k = "what does the gita say about karma?"
    assert norm_k in judgments
    q_data = judgments[norm_k]
    assert q_data["strict"] == ["2.47", "3.19"]
    assert q_data["lenient"] == ["2.47", "3.19", "2.48"]
    assert len(warnings_list) == 0


def test_mark_parsing_rejects_invalid_marks():
    sheet_content = """[01] (conceptual) What is yoga?
  [?] 2.48: Equanimity is yoga
"""
    valid_verses = {"2.48"}
    with pytest.raises(ValueError, match="invalid mark '\\[\\?\\]'"):
        parse_sheet(sheet_content, valid_verses=valid_verses)


def test_numbering_different_from_file_order_matches_by_text(tmp_path):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) Second question in file
  [x] 2.48: Equanimity
[99] (conceptual) First question in file
  [x] 2.47: Duty
""",
        encoding="utf-8",
    )

    questions_file = tmp_path / "questions.jsonl"
    q_data = [
        {"q": "First question in file", "type": "conceptual", "gold": ["1.1"]},
        {"q": "Second question in file", "type": "conceptual", "gold": ["1.2"]},
    ]
    with open(questions_file, "w", encoding="utf-8") as f:
        for item in q_data:
            f.write(json.dumps(item) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"
    valid_verses = {"1.1", "1.2", "2.47", "2.48"}

    strict_rows, lenient_rows, _, _, _, _ = apply_judgments(
        sheet_path=sheet_file,
        questions_path=questions_file,
        out_strict_path=out_strict,
        out_lenient_path=out_lenient,
        valid_verses=valid_verses,
        valid_ids_for_router=set(),
    )

    assert strict_rows[0]["q"] == "First question in file"
    assert strict_rows[0]["gold"] == ["2.47"]

    assert strict_rows[1]["q"] == "Second question in file"
    assert strict_rows[1]["gold"] == ["2.48"]


def test_zero_gold_policy_drops_empty_and_records_unjudged(tmp_path):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) Only lenient question
  [~] 2.48: On topic
[02] (conceptual) Completely blank question
  [ ] 2.47: Not relevant
  [ ] 2.48: Not relevant
[03] (conceptual) Good question
  [x] 3.19: Answer
""",
        encoding="utf-8",
    )

    questions_file = tmp_path / "questions.jsonl"
    q_data = [
        {"q": "Only lenient question", "type": "conceptual", "gold": ["1.1"]},
        {"q": "Completely blank question", "type": "conceptual", "gold": ["1.2"]},
        {"q": "Good question", "type": "conceptual", "gold": ["1.3"]},
        {"q": "Verse 4.7", "type": "lookup", "gold": ["4.7"]},
    ]
    with open(questions_file, "w", encoding="utf-8") as f:
        for item in q_data:
            f.write(json.dumps(item) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"
    valid_verses = {"1.1", "1.2", "1.3", "4.7", "2.47", "2.48", "3.19"}
    valid_ids_router = {"4.7"}

    strict_rows, lenient_rows, _, dropped_strict, dropped_lenient, unjudged = apply_judgments(
        sheet_path=sheet_file,
        questions_path=questions_file,
        out_strict_path=out_strict,
        out_lenient_path=out_lenient,
        valid_verses=valid_verses,
        valid_ids_for_router=valid_ids_router,
        allow_partial=True,
    )

    strict_qs = [r["q"] for r in strict_rows]
    assert "Good question" in strict_qs
    assert "Verse 4.7" in strict_qs
    assert "Only lenient question" not in strict_qs
    assert "Completely blank question" not in strict_qs
    assert len(dropped_strict) == 2

    lenient_qs = [r["q"] for r in lenient_rows]
    assert "Good question" in lenient_qs
    assert "Verse 4.7" in lenient_qs
    assert "Only lenient question" in lenient_qs
    assert "Completely blank question" not in lenient_qs
    assert len(dropped_lenient) == 1

    unjudged_qs = [q for t, q in unjudged]
    assert "Completely blank question" in unjudged_qs
    assert "Only lenient question" not in unjudged_qs


def test_blank_sheet_exits_nonzero_no_files_written(tmp_path):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) Unjudged question
  [ ] 2.47: Candidate verse
""",
        encoding="utf-8",
    )
    questions_file = tmp_path / "questions.jsonl"
    with open(questions_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"q": "Unjudged question", "type": "conceptual", "gold": ["2.47"]}) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"

    with pytest.raises(SystemExit) as exc_info:
        apply_judgments(
            sheet_path=sheet_file,
            questions_path=questions_file,
            out_strict_path=out_strict,
            out_lenient_path=out_lenient,
            valid_verses={"2.47"},
            valid_ids_for_router=set(),
            allow_partial=False,
        )

    assert exc_info.value.code != 0
    assert not out_strict.exists()
    assert not out_lenient.exists()


def test_allow_partial_writes_files_plus_banner(tmp_path, capsys):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) Partial question
  [~] 2.47: On topic only
""",
        encoding="utf-8",
    )
    questions_file = tmp_path / "questions.jsonl"
    with open(questions_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"q": "Partial question", "type": "conceptual", "gold": ["2.47"]}) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"

    apply_judgments(
        sheet_path=sheet_file,
        questions_path=questions_file,
        out_strict_path=out_strict,
        out_lenient_path=out_lenient,
        valid_verses={"2.47"},
        valid_ids_for_router=set(),
        allow_partial=True,
    )

    assert out_strict.exists()
    assert out_lenient.exists()

    captured = capsys.readouterr()
    assert "PARTIAL GOLD: do not run evals on these files" in captured.out


def test_unknown_sheet_entry_fails_loudly_no_files_written(tmp_path):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) Question that does not exist in questions.jsonl
  [x] 2.47: Answer
""",
        encoding="utf-8",
    )
    questions_file = tmp_path / "questions.jsonl"
    with open(questions_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"q": "Actual question", "type": "conceptual", "gold": ["2.47"]}) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"

    with pytest.raises(ValueError, match="match no question in questions.jsonl"):
        apply_judgments(
            sheet_path=sheet_file,
            questions_path=questions_file,
            out_strict_path=out_strict,
            out_lenient_path=out_lenient,
            valid_verses={"2.47"},
            valid_ids_for_router=set(),
        )

    assert not out_strict.exists()
    assert not out_lenient.exists()


def test_missing_non_routed_question_fails_loudly_no_files_written(tmp_path):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) First question
  [x] 2.47: Answer
""",
        encoding="utf-8",
    )
    questions_file = tmp_path / "questions.jsonl"
    with open(questions_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"q": "First question", "type": "conceptual", "gold": ["2.47"]}) + "\n")
        f.write(json.dumps({"q": "Second non-routed question missing", "type": "conceptual", "gold": ["2.48"]}) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"

    with pytest.raises(ValueError, match="missing from sheet"):
        apply_judgments(
            sheet_path=sheet_file,
            questions_path=questions_file,
            out_strict_path=out_strict,
            out_lenient_path=out_lenient,
            valid_verses={"2.47", "2.48"},
            valid_ids_for_router=set(),
        )

    assert not out_strict.exists()
    assert not out_lenient.exists()


def test_assert_kept_original_gold_are_exactly_routed(tmp_path):
    sheet_file = tmp_path / "blind_sheet.txt"
    sheet_file.write_text(
        """[01] (conceptual) First question
  [x] 2.47: Answer
""",
        encoding="utf-8",
    )
    questions_file = tmp_path / "questions.jsonl"
    with open(questions_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"q": "First question", "type": "conceptual", "gold": ["2.47"]}) + "\n")
        f.write(json.dumps({"q": "Verse 4.7", "type": "lookup", "gold": ["4.7"]}) + "\n")

    out_strict = tmp_path / "questions.v2.jsonl"
    out_lenient = tmp_path / "questions.v2_lenient.jsonl"

    strict_rows, _, _, _, _, _ = apply_judgments(
        sheet_path=sheet_file,
        questions_path=questions_file,
        out_strict_path=out_strict,
        out_lenient_path=out_lenient,
        valid_verses={"2.47", "4.7"},
        valid_ids_for_router={"4.7"},
    )
    assert len(strict_rows) == 2


def test_verse_line_with_brackets_in_text():
    sheet_content = """[01] (conceptual) Question with note in verse
  [ ]    2.5: He said [a translator's note] and went on
  [x]    2.6: Another verse [extra note] here
"""
    valid_verses = {"2.5", "2.6"}
    judgments, warnings_list = parse_sheet(sheet_content, valid_verses=valid_verses)

    norm_k = "question with note in verse"
    assert norm_k in judgments
    q_data = judgments[norm_k]
    assert (" ", "2.5") in q_data["all_marked"] or ("", "2.5") in q_data["all_marked"]
    assert "2.5" not in q_data["strict"]
    assert "2.6" in q_data["strict"]
    assert len(warnings_list) == 0


def test_bad_verse_id_asserts():
    sheet_content = """[01] (conceptual) Unknown verse question
  [x] 99.99: Nonexistent verse
"""
    valid_verses = {"1.1", "2.47"}
    with pytest.raises(AssertionError, match="does not exist in dataset"):
        parse_sheet(sheet_content, valid_verses=valid_verses)


def test_duplicate_verse_warning():
    sheet_content = """[01] (conceptual) Repeated verse question
  [x] 2.47: Verse first time
  [ ] 2.47: Verse second time
"""
    valid_verses = {"2.47"}
    judgments, warnings_list = parse_sheet(sheet_content, valid_verses=valid_verses)

    assert any("Duplicated verse: '2.47'" in w for w in warnings_list)
