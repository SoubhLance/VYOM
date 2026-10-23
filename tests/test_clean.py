"""Tests for ingestion/clean.py"""
import re
import unicodedata
import pytest
from clean import (
    norm, clean_verse, load_clean, EMBED_MIN_COMMENTARY_CHARS, clean_sivananda,
    strip_fix_label, strip_letter_markers, strip_leading_period, strip_hindi_footnote,
    clean_stray_danda, clean_ramsukhdas,
)


# ═══════════════════════════════════════════════════════════════════════
#  norm() unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestNorm:
    def test_none_returns_empty(self):
        assert norm(None) == ""

    def test_empty_returns_empty(self):
        assert norm("") == ""

    def test_verse_marker_removed(self):
        assert "।।" not in norm("hello ।। 2.47 ।। world")
        assert norm("hello ।। 2.47 ।। world") == "hello world"

    def test_whitespace_collapsed(self):
        assert norm("  foo   bar  ") == "foo bar"

    def test_keep_lines_preserves_line_breaks(self):
        result = norm("line one\nline two\n\nline three", keep_lines=True)
        assert result == "line one\nline two\nline three"

    def test_keep_lines_strips_each_line(self):
        result = norm("  foo  \n  bar  ", keep_lines=True)
        assert result == "foo\nbar"

    def test_idempotent(self):
        text = "  hello ।। 1.1 ।।   world  "
        assert norm(norm(text)) == norm(text)

    def test_nfc_applied(self):
        # é composed via NFD (e + combining acute)
        nfd = "e\u0301"
        result = norm(nfd)
        assert result == unicodedata.normalize("NFC", nfd)
        assert result == "é"


# ═══════════════════════════════════════════════════════════════════════
#  clean_verse() unit tests (synthetic data)
# ═══════════════════════════════════════════════════════════════════════

def _make_raw_verse():
    """Return a minimal synthetic raw verse dict resembling the real schema."""
    return {
        "chapter_number": 2,
        "verse_number": 47,
        "text": "कर्मण्येवाधिकारस्ते ।। 2.47 ।।",
        "transliteration": "karmanye vadhikaraste ।। 2.47 ।।",
        "word_meanings": "karmanye—in work; eva—only",
        "translations": [
            {"author_name": "Author A", "language": "english", "description": "You have a right to action."},
            {"author_name": "Author B", "language": "hindi", "description": "तुम्हारा अधिकार कर्म में है।"},
            {"author_name": "Author C", "language": "english", "description": ""},       # empty → dropped
        ],
        "commentaries": [
            {"author_name": "Long Author", "language": "sanskrit",
             "description": "This is a long commentary that exceeds forty characters in length easily."},
            {"author_name": "Short Author", "language": "sanskrit",
             "description": "short"},  # short but non-empty → KEPT
            {"author_name": "Empty Author", "language": "sanskrit",
             "description": ""},  # empty → DROPPED
            {"author_name": "None Author", "language": "sanskrit",
             "description": None},  # None → DROPPED
        ],
    }


class TestCleanVerse:
    def test_verse_id(self):
        v = clean_verse(_make_raw_verse())
        assert v["verse_id"] == "2.47"

    def test_marker_removed_from_sanskrit(self):
        v = clean_verse(_make_raw_verse())
        assert "2.47" not in v["sanskrit"]
        assert "।।" not in v["sanskrit"]

    def test_empty_translation_dropped(self):
        v = clean_verse(_make_raw_verse())
        # Author C had empty text and should be gone
        all_authors = [t["author"] for t in v["translations"]["english"]]
        assert "Author C" not in all_authors

    def test_english_hindi_split(self):
        v = clean_verse(_make_raw_verse())
        assert len(v["translations"]["english"]) == 1
        assert len(v["translations"]["hindi"]) == 1
        assert v["translations"]["english"][0]["author"] == "Author A"
        assert v["translations"]["hindi"][0]["author"] == "Author B"

    def test_empty_commentary_dropped(self):
        v = clean_verse(_make_raw_verse())
        authors = [c["author"] for c in v["commentaries"]]
        assert "Empty Author" not in authors
        assert "None Author" not in authors

    def test_short_nonempty_commentary_kept(self):
        v = clean_verse(_make_raw_verse())
        authors = [c["author"] for c in v["commentaries"]]
        assert "Short Author" in authors
        assert "Long Author" in authors

    def test_fix_prefix_stripped_from_translation(self):
        raw = _make_raw_verse()
        raw["translations"].append({
            "author_name": "Test Author",
            "language": "english",
            "description": "Fix: Holding the trunk, head, and neck erect",
        })
        v = clean_verse(raw)
        author_texts = {t["author"]: t["text"] for t in v["translations"]["english"]}
        assert author_texts["Test Author"] == "Holding the trunk, head, and neck erect"

    def test_legitimate_fix_word_preserved(self):
        raw = _make_raw_verse()
        raw["translations"].append({
            "author_name": "Test Author",
            "language": "english",
            "description": "Fix your mind on Me, be devoted to Me.",
        })
        v = clean_verse(raw)
        author_texts = {t["author"]: t["text"] for t in v["translations"]["english"]}
        assert author_texts["Test Author"] == "Fix your mind on Me, be devoted to Me."


# ═══════════════════════════════════════════════════════════════════════
#  strip_fix_label() unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestStripFixLabel:
    @pytest.mark.parametrize("label", ["Fix:", "Fixed:", "Corrected:", "Correction:", "Revised:"])
    def test_strip_editorial_labels(self, label):
        assert strip_fix_label(f"{label} Some text here") == "Some text here"
        assert strip_fix_label(f"{label}   Multiple spaces") == "Multiple spaces"
        assert strip_fix_label(f"{label}\nNewline after label") == "Newline after label"
        assert strip_fix_label(f"{label}NoSpace") == "NoSpace"

    def test_preserves_dialogue_attributions(self):
        assert strip_fix_label("Arjuna said: What is that Brahman?") == "Arjuna said: What is that Brahman?"
        assert strip_fix_label("The Lord said: Fearlessness, purity of heart...") == "The Lord said: Fearlessness, purity of heart..."
        assert strip_fix_label("Sanjaya said: Having spoken thus...") == "Sanjaya said: Having spoken thus..."

    def test_preserves_om_tat_sat(self):
        assert strip_fix_label("OM TAT SAT: This has been declared as the threefold designation.") == \
            "OM TAT SAT: This has been declared as the threefold designation."

    def test_preserves_sentences_without_colon(self):
        assert strip_fix_label("Fix your mind on Me alone") == "Fix your mind on Me alone"
        assert strip_fix_label("Fixed in meditation, he attains peace") == "Fixed in meditation, he attains peace"
        assert strip_fix_label("Correct action leads to purity of heart") == "Correct action leads to purity of heart"
        assert strip_fix_label("Correction of errors is necessary") == "Correction of errors is necessary"
        assert strip_fix_label("Revised editions contain updates") == "Revised editions contain updates"

    def test_preserves_other_prefixes_and_lowercase(self):
        assert strip_fix_label("fix: lowercase should not match") == "fix: lowercase should not match"
        assert strip_fix_label("fixed: lowercase should not match") == "fixed: lowercase should not match"
        assert strip_fix_label("corrected: lowercase should not match") == "corrected: lowercase should not match"
        assert strip_fix_label("Prefix: not touched") == "Prefix: not touched"
        assert strip_fix_label("Note: not touched") == "Note: not touched"

    def test_preserves_mid_sentence(self):
        assert strip_fix_label("Please Fix: this text") == "Please Fix: this text"
        assert strip_fix_label("Here is the Corrected: text") == "Here is the Corrected: text"

    def test_empty_and_none(self):
        assert strip_fix_label("") == ""
        assert strip_fix_label(None) == ""


# ═══════════════════════════════════════════════════════════════════════
#  strip_letter_markers() unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestStripLetterMarkers:
    def test_strips_leading_a_and_inline_markers(self):
        text = "(a) First part. (b) Second part. (c) Third part. (d) Fourth part."
        expected = "First part. Second part. Third part. Fourth part."
        assert strip_letter_markers(text) == expected

    def test_strips_adidevananda_without_b(self):
        text = "(a) Only part A without later markers"
        assert strip_letter_markers(text, author="Swami Adidevananda") == "Only part A without later markers"

    def test_preserves_leading_a_without_b_for_other_authors(self):
        text = "(a) Only part A without later markers"
        assert strip_letter_markers(text, author="Other Author") == "(a) Only part A without later markers"

    def test_preserves_leading_parentheticals_1_8(self):
        text = "(They are): Your venerable self, Bhisma, Karna, and Krpa, who is ever victorious"
        assert strip_letter_markers(text, author="Swami Gambirananda", language="english") == text

    def test_preserves_leading_parentheticals_17_6(self):
        text = "(And those who,) being non-discriminating, torture all the organs in the body as"
        assert strip_letter_markers(text, author="Swami Gambirananda", language="english") == text

    def test_preserves_hindi_parenthetical_gloss(self):
        text = "(संयमरहित) अयुक्त पुरुष को (आत्म) ज्ञान नहीं होता"
        assert strip_letter_markers(text, author="Swami Tejomayananda", language="hindi") == text

    def test_preserves_non_english(self):
        text = "(a) Some hindi text (b) more text"
        assert strip_letter_markers(text, language="hindi") == text


# ═══════════════════════════════════════════════════════════════════════
#  strip_leading_period() unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestStripLeadingPeriod:
    def test_strips_period_and_space(self):
        text = ". Taking, rejecting, receiving, opening, and closing the eyes"
        assert strip_leading_period(text) == "Taking, rejecting, receiving, opening, and closing the eyes"

    def test_strips_period_and_multiple_spaces(self):
        assert strip_leading_period(".   Focus here") == "Focus here"

    def test_preserves_ellipsis(self):
        assert strip_leading_period("... Taking") == "... Taking"

    def test_preserves_period_without_space(self):
        assert strip_leading_period(".Taking") == ".Taking"

    def test_preserves_mid_sentence_period(self):
        assert strip_leading_period("Word. Other") == "Word. Other"

    def test_empty_and_none(self):
        assert strip_leading_period("") == ""
        assert strip_leading_period(None) == ""


# ═══════════════════════════════════════════════════════════════════════
#  clean_stray_danda() unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestCleanStrayDanda:
    def test_clean_7_14_marker(self):
        text = "is hard to overcome. ৷৷ (b) ৷৷ But those who take refuge"
        assert clean_stray_danda(text) == "is hard to overcome. (b) But those who take refuge"

    def test_clean_11_40_marker(self):
        text = "Salutations to You from all sides, O All!৷৷. ৷৷. O You of infinite prowess"
        assert clean_stray_danda(text) == "Salutations to You from all sides, O All! O You of infinite prowess"

    def test_clean_trailing_in_commentary(self):
        text = "with his body, speech and mind৷৷."
        assert clean_stray_danda(text) == "with his body, speech and mind."

    def test_clean_inline_before_parens(self):
        text = "Which is isolated, as the agent৷৷. (XVIII.16)"
        assert clean_stray_danda(text) == "Which is isolated, as the agent. (XVIII.16)"

    def test_preserves_text_without_marker(self):
        text = "Normal sentence without stray marks. Another sentence."
        assert clean_stray_danda(text) == text

    def test_empty_and_none(self):
        assert clean_stray_danda("") == ""
        assert clean_stray_danda(None) == ""


# ═══════════════════════════════════════════════════════════════════════
#  clean_ramsukhdas() unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestCleanRamsukhdas:
    def test_strips_inline_footnotes_1_1(self):
        text = "धृतराष्ट्र बोले (टिप्पणी प0 1.2) - हे संजय! (टिप्पणी प0 1.3) धर्मभूमि कुरुक्षेत्र में"
        expected = "धृतराष्ट्र बोले - हे संजय! धर्मभूमि कुरुक्षेत्र में"
        assert clean_ramsukhdas(text, is_translation=True) == expected
        assert clean_ramsukhdas(text, is_translation=False) == expected

    def test_strips_verse_range_heading_and_footnote(self):
        text = "।।1.34 -- 1.35।। (टिप्पणी प0 24.1) आचार्य, पिता, पुत्र"
        assert clean_ramsukhdas(text, is_translation=True) == "आचार्य, पिता, पुत्र"

    def test_preserves_range_heading_when_not_translation(self):
        text = "।।1.34 -- 1.35।। व्याख्या"
        assert clean_ramsukhdas(text, is_translation=False) == "।।1.34 -- 1.35।। व्याख्या"

    def test_strips_footnote_with_spaces_inside_parens(self):
        text = "में भय बैठा हुआ है ( टिप्पणी प0 10 )।"
        assert clean_ramsukhdas(text, is_translation=False) == "में भय बैठा हुआ है।"

    def test_empty_and_none(self):
        assert clean_ramsukhdas("") == ""
        assert clean_ramsukhdas(None) == ""
        assert strip_hindi_footnote("") == ""


# ═══════════════════════════════════════════════════════════════════════
#  clean_sivananda() unit tests
# ═══════════════════════════════════════════════════════════════════════

def test_sivananda_drops_gloss():
    t = "2.47 कर्मणि in work? एव only? Commentary When you act, have no desire."
    assert clean_sivananda(t) == "When you act, have no desire."


def test_sivananda_no_commentary_is_none():
    assert clean_sivananda("2.1 तम् to him? तथा thus?No commentary.") is None


def test_sivananda_repairs_punctuation_and_spacing():
    out = clean_sivananda("1.1 x Commentary Sacrifice? austerity? gift.Next one andThen more")
    assert "?" not in out
    assert "gift. Next" in out
    assert "and Then" in out


# ═══════════════════════════════════════════════════════════════════════
#  Integration tests on real data via load_clean()
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def all_verses():
    return load_clean()


@pytest.fixture(scope="module")
def data(all_verses):
    return all_verses


def test_sivananda_real_data(data):
    texts = [c["text"] for v in data for c in v["commentaries"]
             if c["author"] == "Swami Sivananda" and c["language"] == "english"]
    assert 680 <= len(texts) <= 690            # audit showed 686
    for t in texts:
        assert "?" not in t
        assert not re.match(r"\d+\.\d+", t)    # gloss prefix gone


class TestIntegration:
    def test_exactly_701_verses(self, all_verses):
        assert len(all_verses) == 701

    def test_unique_verse_ids(self, all_verses):
        ids = [v["verse_id"] for v in all_verses]
        assert len(ids) == len(set(ids)), "Duplicate verse_ids found"

    @pytest.mark.parametrize("vid", ["1.1", "2.47", "4.7", "18.66", "18.78"])
    def test_expected_verses_exist(self, all_verses, vid):
        assert any(v["verse_id"] == vid for v in all_verses), f"Missing {vid}"

    def test_no_digits_in_sanskrit_or_transliteration(self, all_verses):
        """Cleaned sanskrit and transliteration must have no Arabic digits.

        Digits only appear as part of verse markers (e.g. ।।2.47।।) which
        should be fully stripped.  This test is independent of the MARKER
        regex used by clean.py.
        """
        digit = re.compile(r"[0-9]")
        for v in all_verses:
            assert not digit.search(v["sanskrit"]), \
                f"Digit in sanskrit of {v['verse_id']}: {v['sanskrit'][:120]}"
            assert not digit.search(v["transliteration"]), \
                f"Digit in transliteration of {v['verse_id']}: {v['transliteration'][:120]}"

    def test_verse_18_78_no_leftover_marker(self, all_verses):
        """Verse 18.78 had a malformed marker (।।18.78।) — must be fully removed."""
        v = next(v for v in all_verses if v["verse_id"] == "18.78")
        assert "18.78" not in v["sanskrit"]
        assert "18" not in v["sanskrit"]
        digit = re.compile(r"[0-9]")
        assert not digit.search(v["sanskrit"]), \
            f"Digit remains in 18.78 sanskrit: {v['sanskrit'][:120]}"
        assert not digit.search(v["transliteration"]), \
            f"Digit remains in 18.78 transliteration: {v['transliteration'][:120]}"

    def test_verse_2_47_danda_preserved(self, all_verses):
        """The danda (।) after कदाचन must survive cleaning — it is content, not a marker."""
        v = next(v for v in all_verses if v["verse_id"] == "2.47")
        assert "।" in v["sanskrit"], "Danda missing from 2.47 sanskrit"
        assert "कदाचन।" in v["sanskrit"], "Danda after कदाचन missing from 2.47 sanskrit"

    def test_verse_2_47_curly_apostrophe_preserved(self, all_verses):
        """The transliteration contains a curly apostrophe (’ / \u2019) in ’stvakarmaṇi."""
        v = next(v for v in all_verses if v["verse_id"] == "2.47")
        assert "\u2019" in v["transliteration"], \
            f"Curly apostrophe missing from 2.47 transliteration: {v['transliteration']!r}"

    def test_no_verse_loses_dandas(self, all_verses):
        """Every verse with raw dandas retains them; clean danda count == raw minus marker dandas."""
        from load import load_raw_verses
        from clean import MARKER
        raw_verses = [v for ch in load_raw_verses().values() for v in ch]
        raw_by_id = {f"{v['chapter_number']}.{v['verse_number']}": v for v in raw_verses}
        for v in all_verses:
            raw_v = raw_by_id[v["verse_id"]]
            raw_sanskrit = raw_v.get("text") or ""
            raw_dandas = raw_sanskrit.count("।")
            marker_dandas = sum(m.count("।") for m in MARKER.findall(raw_sanskrit))
            clean_dandas = v["sanskrit"].count("।")

            if raw_dandas > 0:
                assert clean_dandas > 0, f"Verse {v['verse_id']} lost all dandas"
            assert clean_dandas == raw_dandas - marker_dandas, \
                f"Danda count mismatch for {v['verse_id']}: expected {raw_dandas - marker_dandas}, got {clean_dandas}"


    def test_no_leading_trailing_whitespace(self, all_verses):
        for v in all_verses:
            for key in ("sanskrit", "transliteration", "word_meanings"):
                val = v[key]
                if val:
                    assert val == val.strip(), f"Whitespace in {v['verse_id']}.{key}"
            for lang in ("english", "hindi"):
                for t in v["translations"][lang]:
                    assert t["text"] == t["text"].strip()
            for c in v["commentaries"]:
                assert c["text"] == c["text"].strip()

    def test_no_double_spaces_in_single_line_fields(self, all_verses):
        for v in all_verses:
            for key in ("word_meanings",):
                assert "  " not in v[key], f"Double space in {v['verse_id']}.{key}"
            for lang in ("english", "hindi"):
                for t in v["translations"][lang]:
                    assert "  " not in t["text"], f"Double space in translation {v['verse_id']}"
            for c in v["commentaries"]:
                assert "  " not in c["text"], f"Double space in commentary {v['verse_id']}"

    def test_core_fields_nonempty(self, all_verses):
        for v in all_verses:
            assert v["sanskrit"], f"{v['verse_id']} missing sanskrit"
            assert v["transliteration"], f"{v['verse_id']} missing transliteration"
            assert v["word_meanings"], f"{v['verse_id']} missing word_meanings"

    def test_every_verse_has_english_translation(self, all_verses):
        for v in all_verses:
            assert len(v["translations"]["english"]) >= 1, \
                f"{v['verse_id']} has no english translation"

    def test_no_commentary_has_empty_text(self, all_verses):
        for v in all_verses:
            for c in v["commentaries"]:
                assert c["text"], f"Empty commentary in {v['verse_id']} by {c['author']}"

    def test_no_leading_editorial_label_in_any_translation(self, all_verses):
        labels = ("Fix:", "Fixed:", "Corrected:", "Correction:", "Revised:")
        for v in all_verses:
            for lang in ("english", "hindi"):
                for t in v["translations"][lang]:
                    for lbl in labels:
                        assert not t["text"].startswith(lbl), \
                            f"Verse {v['verse_id']} translation by {t['author']} starts with {lbl!r}: {t['text'][:80]}"

    @pytest.mark.parametrize("vid,expected_start", [
        ("1.26", "Then, Arjuna (son of Pritha) saw there"),
        ("1.28", "And his heart melted with pity"),
        ("1.35", '"These I do not wish to kill'),
        ("1.39", "Why should we not learn to shun this crime"),
        ("1.40", "With the ruin of a clan, its ancient traditions perish"),
        ("1.43", "By the destruction of our lineage"),
        ("2.32", "Blessed are the soldiers who find their opportunity"),
        ("2.48", "Perform all your actions with your mind concentrated"),
        ("6.13", "Holding the trunk, head, and neck erect"),
        ("11.40", "Salutations to You from before and behind"),
        ("13.11", "Constantly devote yourself to Me alone"),
        ("14.5", "Purity, passion, and ignorance are the qualities"),
        ("18.45", "Each person devoted to their own duty attains perfection"),
    ])
    def test_affected_verses_cleaned(self, all_verses, vid, expected_start):
        v = next(v for v in all_verses if v["verse_id"] == vid)
        texts = [t["text"] for t in v["translations"]["english"]]
        labels = ("Fix:", "Fixed:", "Corrected:", "Correction:", "Revised:")
        for t in texts:
            for lbl in labels:
                assert not t.startswith(lbl), f"{vid} still has {lbl}: {t[:60]}"
        assert any(t.startswith(expected_start) for t in texts), \
            f"{vid} does not contain translation starting with {expected_start!r}"

    def test_verse_5_9_no_leading_period(self, all_verses):
        v = next(v for v in all_verses if v["verse_id"] == "5.9")
        sank = next(t["text"] for t in v["translations"]["english"] if "Sankaranarayan" in t["author"])
        assert sank.startswith("Taking, rejecting, receiving")
        assert not sank.startswith(".")

    def test_verse_2_16_no_footnote(self, all_verses):
        v = next(v for v in all_verses if v["verse_id"] == "2.16")
        ram = next(t["text"] for t in v["translations"]["hindi"] if "Ramsukhdas" in t["author"])
        assert ram.startswith("असत् का तो भाव")
        assert not ram.startswith("(")

    @pytest.mark.parametrize("vid", ["7.14", "11.37", "11.38", "11.39", "11.40", "13.22", "14.15", "15.2", "18.5"])
    def test_adidevananda_letter_markers_stripped(self, all_verses, vid):
        v = next(v for v in all_verses if v["verse_id"] == vid)
        adidev = next(t["text"] for t in v["translations"]["english"] if t["author"] == "Swami Adidevananda")
        assert not adidev.startswith("(a)")
        assert "(b)" not in adidev
        assert "(c)" not in adidev
        assert "(d)" not in adidev

    def test_parenthetical_glosses_preserved(self, all_verses):
        # 1.8 Gambirananda
        v1_8 = next(v for v in all_verses if v["verse_id"] == "1.8")
        g1_8 = next(t["text"] for t in v1_8["translations"]["english"] if "Gambirananda" in t["author"])
        assert g1_8.startswith("(They are):")

        # 17.6 Gambirananda
        v17_6 = next(v for v in all_verses if v["verse_id"] == "17.6")
        g17_6 = next(t["text"] for t in v17_6["translations"]["english"] if "Gambirananda" in t["author"])
        assert g17_6.startswith("(And those who,)")

        # 2.66 Tejomayananda
        v2_66 = next(v for v in all_verses if v["verse_id"] == "2.66")
        t2_66 = next(t["text"] for t in v2_66["translations"]["hindi"] if "Tejomayananda" in t["author"])
        assert t2_66.startswith("(संयमरहित)")

    def test_verse_7_14_and_11_40_full_text(self, all_verses):
        v7_14 = next(v for v in all_verses if v["verse_id"] == "7.14")
        t7_14 = next(t["text"] for t in v7_14["translations"]["english"] if t["author"] == "Swami Adidevananda")
        expected_7_14 = (
            "For this divine Maya or Mine, consisting of the three Gunas (assumed for purposes of sport), "
            "is hard to overcome. But those who take refuge in Me alone shall pass beyond the Maya."
        )
        assert t7_14 == expected_7_14

        v11_40 = next(v for v in all_verses if v["verse_id"] == "11.40")
        t11_40 = next(t["text"] for t in v11_40["translations"]["english"] if t["author"] == "Swami Adidevananda")
        expected_11_40 = (
            "Salutations to You from before and behind! Salutations to You from all sides, O All! "
            "O You of infinite prowess and heroic action, which are measureless! You pervade all beings, "
            "and therefore, You are all."
        )
        assert t11_40 == expected_11_40

    def test_no_stray_danda_in_english_texts(self, all_verses):
        bengali_ishar = "\u09f7"
        for v in all_verses:
            for t in v["translations"]["english"]:
                assert bengali_ishar not in t["text"], f"U+09F7 in {v['verse_id']} translation by {t['author']}"
            for c in v["commentaries"]:
                if c["author"] == "Swami Sivananda" and c["language"] == "english":
                    assert bengali_ishar not in c["text"], f"U+09F7 in {v['verse_id']} Sivananda commentary"

    def test_hindi_sanskrit_u09f7_converted_to_danda(self, all_verses):
        bengali_ishar = "\u09f7"
        # 1. Check specific samples
        v1_11 = next(v for v in all_verses if v["verse_id"] == "1.11")
        c_ram = next(c["text"] for c in v1_11["commentaries"] if "Ramsukhdas" in c["author"])
        assert "अयनेषु च सर्वेषु ।।." in c_ram
        assert bengali_ishar not in c_ram

        v2_21 = next(v for v in all_verses if v["verse_id"] == "2.21")
        c_shank = next(c["text"] for c in v2_21["commentaries"] if "Shankaracharya" in c["author"])
        assert "वेदाविनाशिनं।।." in c_shank
        assert bengali_ishar not in c_shank

        v2_50 = next(v for v in all_verses if v["verse_id"] == "2.50")
        c_madh = next(c["text"] for c in v2_50["commentaries"] if "Madhavacharya" in c["author"])
        assert "यावदात्मभावित्वात्।।." in c_madh
        assert bengali_ishar not in c_madh

        # 2. Check that no U+09F7 exists in ANY field across all verses
        for v in all_verses:
            assert bengali_ishar not in v["sanskrit"], f"U+09F7 in {v['verse_id']} sanskrit"
            assert bengali_ishar not in v["transliteration"], f"U+09F7 in {v['verse_id']} transliteration"
            assert bengali_ishar not in v["word_meanings"], f"U+09F7 in {v['verse_id']} word_meanings"
            for lang in ("english", "hindi"):
                for t in v["translations"][lang]:
                    assert bengali_ishar not in t["text"], f"U+09F7 in {v['verse_id']} {lang} translation by {t['author']}"
            for c in v["commentaries"]:
                assert bengali_ishar not in c["text"], f"U+09F7 in {v['verse_id']} commentary by {c['author']}"

    def test_ramsukhdas_no_footnotes_or_range_headings(self, all_verses):
        range_re = re.compile(r"(?:।।|\|\|)\s*\d+\.\d+\s*(?:--|–|-)\s*\d+\.\d+\s*(?:।।|\|\|)")
        for v in all_verses:
            for t in v["translations"]["hindi"]:
                if "Ramsukhdas" in t["author"]:
                    assert "टिप्पणी" not in t["text"], f"Footnote in {v['verse_id']} translation: {t['text'][:80]}"
                    assert not range_re.search(t["text"]), f"Range heading in {v['verse_id']} translation: {t['text'][:80]}"
            for c in v["commentaries"]:
                if "Ramsukhdas" in c["author"]:
                    assert "टिप्पणी" not in c["text"], f"Footnote in {v['verse_id']} commentary: {c['text'][:80]}"


# ═══════════════════════════════════════════════════════════════════════
#  Non-failing report: Sivananda commentary coverage
# ═══════════════════════════════════════════════════════════════════════

class TestReports:
    def test_sivananda_commentary_report(self, all_verses):
        """Report (non-failing) — prints verses with no Sivananda english commentary."""
        missing = []
        for v in all_verses:
            has_siv = any(
                c["author"] == "Swami Sivananda" and c["language"] == "english"
                for c in v["commentaries"]
            )
            if not has_siv:
                missing.append(v["verse_id"])

        print(f"\n[REPORT] Verses without Sivananda english commentary: {len(missing)}")
        if missing:
            print(f"  Verse IDs: {missing}")

        # Count short Sivananda commentaries (below EMBED_MIN_COMMENTARY_CHARS)
        short_count = 0
        for v in all_verses:
            for c in v["commentaries"]:
                if c["author"] == "Swami Sivananda" and c["language"] == "english":
                    if len(c["text"]) < EMBED_MIN_COMMENTARY_CHARS:
                        short_count += 1
        print(f"  Sivananda english commentaries shorter than {EMBED_MIN_COMMENTARY_CHARS} chars: {short_count}")
        assert len(missing) == 15

