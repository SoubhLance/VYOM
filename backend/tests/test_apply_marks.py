"""Tests for apply_marks.py."""
import textwrap
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "retrieval" / "eval"))

from apply_marks import parse_marks, parse_sheet_sections, validate, apply_marks  # noqa: E402


SAMPLE_BLANK = textwrap.dedent("""\
    # Legend
    # [x] answers

    [01] (conceptual) Sample question one?
    Pool size: 3
      [ ]   2.47: Some verse text about action.
      [ ]   3.19: Another verse about duty.
      [ ]   5.10: Third verse text here.

    [02] (lookup) Sample question two?
    Pool size: 2
      [ ]   1.1: First verse of the text.
      [ ]  18.66: Surrender verse text.

""")

SAMPLE_MARKS_GOOD = textwrap.dedent("""\
    01 x: 2.47 5.10 | ~: 3.19
    02 x: 1.1 | ~:
""")

SAMPLE_MARKS_UNKNOWN_VID = textwrap.dedent("""\
    01 x: 2.47 99.99 | ~: 3.19
    02 x: 1.1 | ~:
""")

SAMPLE_MARKS_CONFLICT = textwrap.dedent("""\
    01 x: 2.47 3.19 | ~: 3.19
    02 x: 1.1 | ~:
""")


class TestParseMarks:
    def test_basic_parse(self):
        marks = parse_marks(SAMPLE_MARKS_GOOD)
        assert marks[1]["x"] == {"2.47", "5.10"}
        assert marks[1]["~"] == {"3.19"}
        assert marks[2]["x"] == {"1.1"}
        assert marks[2]["~"] == set()

    def test_duplicate_section_raises(self):
        text = "01 x: 2.47 | ~:\n01 x: 3.19 | ~:\n"
        with pytest.raises(ValueError, match="duplicate section"):
            parse_marks(text)

    def test_bad_format_raises(self):
        text = "01 junk line\n"
        with pytest.raises(ValueError, match="cannot parse"):
            parse_marks(text)


class TestParseSheetSections:
    def test_basic_sections(self):
        sections = parse_sheet_sections(SAMPLE_BLANK)
        assert 1 in sections
        assert 2 in sections
        vids_1 = [vid for _, vid in sections[1]]
        assert vids_1 == ["2.47", "3.19", "5.10"]
        vids_2 = [vid for _, vid in sections[2]]
        assert vids_2 == ["1.1", "18.66"]


class TestValidate:
    def test_good_marks_pass(self):
        marks = parse_marks(SAMPLE_MARKS_GOOD)
        sections = parse_sheet_sections(SAMPLE_BLANK)
        # Adjust expected section range (our fabricated sheet only has 01 and 02)
        # validate checks 01-20, but for test purposes we only care about the
        # errors related to our specific data
        errors = validate(marks, sections)
        # We expect 18 "no marks line" errors for sections 03-20
        # Filter to only errors about our test sections
        relevant_errors = [e for e in errors if "[01]" in e or "[02]" in e]
        assert relevant_errors == []

    def test_unknown_verse_fails(self):
        marks = parse_marks(SAMPLE_MARKS_UNKNOWN_VID)
        sections = parse_sheet_sections(SAMPLE_BLANK)
        errors = validate(marks, sections)
        relevant = [e for e in errors if "99.99" in e]
        assert len(relevant) == 1
        assert "not in sheet" in relevant[0]

    def test_conflict_fails(self):
        marks = parse_marks(SAMPLE_MARKS_CONFLICT)
        sections = parse_sheet_sections(SAMPLE_BLANK)
        errors = validate(marks, sections)
        relevant = [e for e in errors if "both x and ~" in e]
        assert len(relevant) == 1


class TestApplyMarks:
    def test_marks_applied_correctly(self, tmp_path):
        blank_path = tmp_path / "blank.txt"
        marks_path = tmp_path / "marks.txt"
        output_path = tmp_path / "output.txt"

        # Use a two-section sheet so validation range [1..20] doesn't interfere
        # We'll monkey-patch validate to only check the sections we have
        blank_path.write_text(SAMPLE_BLANK, encoding="utf-8")
        marks_path.write_text(SAMPLE_MARKS_GOOD, encoding="utf-8")

        # We need to handle the sys.exit from validate; override validate temporarily
        import apply_marks as am
        orig_validate = am.validate

        def patched_validate(marks, sections):
            errors = []
            for sec, m in sorted(marks.items()):
                if sec not in sections:
                    continue
                sheet_vids = {vid for _, vid in sections[sec]}
                for vid in m["x"]:
                    if vid not in sheet_vids:
                        errors.append(f"Section [{sec:02d}]: x-marked {vid} not in sheet")
                for vid in m["~"]:
                    if vid not in sheet_vids:
                        errors.append(f"Section [{sec:02d}]: ~-marked {vid} not in sheet")
                overlap = m["x"] & m["~"]
                if overlap:
                    errors.append(f"Section [{sec:02d}]: both x and ~: {sorted(overlap)}")
            return errors

        am.validate = patched_validate
        try:
            output_text, stats = am.apply_marks(
                blank_path=blank_path,
                marks_path=marks_path,
                output_path=output_path,
            )
        finally:
            am.validate = orig_validate

        # Check marks applied
        assert "[x]   2.47:" in output_text
        assert "[~]   3.19:" in output_text
        assert "[x]   5.10:" in output_text
        assert "[x]   1.1:" in output_text
        assert "[ ]  18.66:" in output_text  # unmarked stays blank

        # Check verse text is byte-identical (not modified)
        assert "Some verse text about action." in output_text
        assert "Another verse about duty." in output_text
        assert "Surrender verse text." in output_text

        # Check stats
        assert stats["total_x"] == 3
        assert stats["total_tilde"] == 1
        assert stats["total_blank"] == 1

    def test_unknown_verse_no_write(self, tmp_path):
        blank_path = tmp_path / "blank.txt"
        marks_path = tmp_path / "marks.txt"
        output_path = tmp_path / "output.txt"
        blank_path.write_text(SAMPLE_BLANK, encoding="utf-8")
        marks_path.write_text(SAMPLE_MARKS_UNKNOWN_VID, encoding="utf-8")

        with pytest.raises(SystemExit):
            apply_marks(
                blank_path=blank_path,
                marks_path=marks_path,
                output_path=output_path,
            )
        assert not output_path.exists()

    def test_conflict_no_write(self, tmp_path):
        blank_path = tmp_path / "blank.txt"
        marks_path = tmp_path / "marks.txt"
        output_path = tmp_path / "output.txt"
        blank_path.write_text(SAMPLE_BLANK, encoding="utf-8")
        marks_path.write_text(SAMPLE_MARKS_CONFLICT, encoding="utf-8")

        with pytest.raises(SystemExit):
            apply_marks(
                blank_path=blank_path,
                marks_path=marks_path,
                output_path=output_path,
            )
        assert not output_path.exists()

    def test_text_untouched(self, tmp_path):
        """Verify that all non-mark characters are preserved exactly."""
        blank_path = tmp_path / "blank.txt"
        marks_path = tmp_path / "marks.txt"
        output_path = tmp_path / "output.txt"
        blank_path.write_text(SAMPLE_BLANK, encoding="utf-8")
        marks_path.write_text(SAMPLE_MARKS_GOOD, encoding="utf-8")

        import apply_marks as am
        orig_validate = am.validate

        def patched_validate(marks, sections):
            return []

        am.validate = patched_validate
        try:
            output_text, _ = am.apply_marks(
                blank_path=blank_path,
                marks_path=marks_path,
                output_path=output_path,
            )
        finally:
            am.validate = orig_validate

        # Replace marks back to blanks on verse lines only, not legend
        import re
        def restore_marks(text):
            def _sub(m):
                return m.group(0).replace("[x]", "[ ]").replace("[~]", "[ ]")
            return re.sub(r"^(\s*)\[[x~]\](\s+\d+\.\d+\s*:)", _sub, text, flags=re.MULTILINE)
        restored = restore_marks(output_text)
        assert restored == SAMPLE_BLANK
