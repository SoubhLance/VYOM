"""Quote verification against supplied Bhagavad Gita verse translations."""

import logging
import re
from difflib import SequenceMatcher
from typing import Any

logger = logging.getLogger("vyom.retrieval.verify_quotes")

QUOTE_PATTERN = re.compile(r'["“”]([^"“”]+?)["“”]')
CITATION_PATTERN = re.compile(
    r'\b(?:BG|Śrī Bhagavad‑gītā|Bhagavad Gita)\s*([0-9]{1,2}\.[0-9]{1,2})\b|\((?:BG\s*)?([0-9]{1,2}\.[0-9]{1,2})\)',
    re.IGNORECASE
)
DANGLING_PREFIXES = ('This verse', 'This passage', 'This suggests', 'Here,', 'It ')


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, stripping markdown asterisks and underscores,
    removing punctuation, and collapsing whitespace."""
    # Strip markdown asterisks and underscores before comparing
    text = re.sub(r"[\*_]+", " ", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fuzzy_overlap_ratio(q: str, t: str) -> float:
    """Calculate maximum fuzzy overlap ratio between normalized quote q and translation t.
    Returns value between 0.0 and 1.0."""
    if not q or not t:
        return 0.0
    direct = SequenceMatcher(None, q, t).ratio()
    if direct >= 0.6:
        return direct
    q_words = q.split()
    t_words = t.split()
    if not q_words or not t_words:
        return direct
    k = len(q_words)
    if k <= len(t_words):
        best_window = 0.0
        for w_len in (k, max(1, k - 2), k + 2):
            if w_len > len(t_words):
                continue
            for i in range(len(t_words) - w_len + 1):
                window = " ".join(t_words[i:i + w_len])
                r = SequenceMatcher(None, q, window).ratio()
                if r > best_window:
                    best_window = r
                    if best_window >= 0.8:
                        return best_window
        return max(direct, best_window)
    else:
        matcher = SequenceMatcher(None, q, t)
        match = matcher.find_longest_match(0, len(q), 0, len(t))
        sub_ratio = match.size / len(q)
        return max(direct, sub_ratio)


def extract_quotes(text: str, min_words: int = 5) -> list[str]:
    """Extract quoted substrings enclosed in straight (\"...\") or curly (“...”, ”...”)
    quotation marks that contain at least `min_words` words (default 5, ignoring scare quotes)."""
    matches = QUOTE_PATTERN.findall(text)
    quotes = []
    for m in matches:
        cleaned = m.strip()
        words = cleaned.split()
        if len(words) >= min_words:
            quotes.append(cleaned)
    return quotes


def extract_candidate_translations(verses: list[dict[str, Any]]) -> list[str]:
    """Extract English translation strings from verses, reading fields
    exactly as build_rag_prompt / build_rag_prompt_v2 reads them."""
    candidates = []
    for v in verses:
        translations = v.get("translations")
        if isinstance(translations, dict):
            english = translations.get("english", [])
            if isinstance(english, list):
                for item in english:
                    if isinstance(item, dict) and "text" in item:
                        candidates.append(item["text"])
                    elif isinstance(item, str):
                        candidates.append(item)
        elif isinstance(translations, list):
            for item in translations:
                if isinstance(item, dict) and "text" in item:
                    candidates.append(item["text"])
                elif isinstance(item, str):
                    candidates.append(item)
        elif v.get("translation"):
            candidates.append(v["translation"])
        elif v.get("text"):
            candidates.append(v["text"])
        elif v.get("embed_text"):
            candidates.append(v["embed_text"])
    return candidates


def extract_candidate_translations_by_verse(verses: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Extract normalized English translation strings keyed by verse_id."""
    by_verse: dict[str, list[str]] = {}
    for v in verses:
        vid = str(v.get("verse_id", "")).strip()
        candidates: list[str] = []
        translations = v.get("translations")
        if isinstance(translations, dict):
            english = translations.get("english", [])
            if isinstance(english, list):
                for item in english:
                    if isinstance(item, dict) and "text" in item:
                        candidates.append(item["text"])
                    elif isinstance(item, str):
                        candidates.append(item)
        elif isinstance(translations, list):
            for item in translations:
                if isinstance(item, dict) and "text" in item:
                    candidates.append(item["text"])
                elif isinstance(item, str):
                    candidates.append(item)
        if v.get("translation"):
            candidates.append(v["translation"])
        if v.get("text"):
            candidates.append(v["text"])
        if v.get("embed_text"):
            candidates.append(v["embed_text"])

        by_verse[vid] = [normalize_text(t) for t in candidates if t]
    return by_verse


def check_quotes(answer_text: str, verses: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Extract quoted strings (inside \"...\" or “...”) of 6 or more words from the answer,
    normalize them, and verify whether each is a substring of any English translation
    text of any supplied verse.

    Returns:
        {
            "verified": [str, ...],
            "unverified": [str, ...]
        }
    """
    candidate_quotes = extract_quotes(answer_text, min_words=6)
    candidate_translations = extract_candidate_translations(verses)
    normalized_translations = [normalize_text(t) for t in candidate_translations if t]

    verified: list[str] = []
    unverified: list[str] = []

    for q in candidate_quotes:
        norm_q = normalize_text(q)
        matched = False
        for norm_t in normalized_translations:
            if norm_q in norm_t:
                matched = True
                break
        if matched:
            verified.append(q)
        else:
            unverified.append(q)

    return {
        "verified": verified,
        "unverified": unverified,
    }


def check_quotes_by_citation(
    answer_text: str,
    verses: list[dict[str, Any]],
    strict_following: bool = False
) -> dict[str, list[Any]]:
    """For every quote of 4 or more words, find the nearest following 'BG x.y' or '(BG x.y)'
    citation in the same paragraph (falling back to preceding in the same paragraph if
    strict_following is False), and require the quote to be a substring of an English
    translation of THAT verse. Deduplicate identical quotes.

    Returns:
        {
            "verified": [{"quote": str, "cited_verse": str}, ...],
            "unverified": [{"quote": str, "cited_verse": str, "actual_verse": str | None}, ...],
            "uncited": [str, ...]
        }
    """
    trans_by_verse = extract_candidate_translations_by_verse(verses)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', answer_text) if p.strip()]

    citation_pattern = re.compile(
        r'\b(?:BG|Śrī Bhagavad‑gītā|Bhagavad Gita)\s*([0-9]{1,2}\.[0-9]{1,2})\b|\((?:BG\s*)?([0-9]{1,2}\.[0-9]{1,2})\)',
        re.IGNORECASE
    )

    seen_quotes: set[str] = set()
    verified: list[dict[str, str]] = []
    unverified: list[dict[str, Any]] = []
    uncited: list[str] = []

    for p in paragraphs:
        matches = list(QUOTE_PATTERN.finditer(p))
        for m in matches:
            quote = m.group(1).strip()
            words = quote.split()
            # Rule 1(b): Ignore quoted passages shorter than 5 words (scare quotes)
            if len(words) < 5:
                continue
            # Deduplicate identical quotes
            if quote in seen_quotes:
                continue
            seen_quotes.add(quote)

            # 1. Search nearest following citation in same paragraph
            after_text = p[m.end():]
            cit_match = citation_pattern.search(after_text)
            cited_vid = None
            if cit_match:
                cited_vid = cit_match.group(1) or cit_match.group(2)
            elif not strict_following:
                # Fallback: check preceding citation in same paragraph
                before_text = p[:m.start()]
                pre_matches = list(citation_pattern.finditer(before_text))
                if pre_matches:
                    last_m = pre_matches[-1]
                    cited_vid = last_m.group(1) or last_m.group(2)

            if not cited_vid:
                uncited.append(quote)
                continue

            # 2. Check if quote is substring of an English translation of THAT cited verse
            norm_q = normalize_text(quote)
            target_trans = trans_by_verse.get(cited_vid, [])
            matched = any(norm_q in t for t in target_trans)

            if matched:
                verified.append({
                    "quote": quote,
                    "cited_verse": cited_vid
                })
            else:
                # Find if it was actually present in any other supplied verse
                found_in = None
                for other_vid, other_trans in trans_by_verse.items():
                    if other_vid != cited_vid and any(norm_q in t for t in other_trans):
                        found_in = other_vid
                        break
                if not found_in:
                    # Also check if it has clear fuzzy overlap (>= 0.6) with any other supplied verse
                    best_score = 0.0
                    for other_vid, other_trans in trans_by_verse.items():
                        if other_vid != cited_vid:
                            score = max((fuzzy_overlap_ratio(norm_q, t) for t in other_trans), default=0.0)
                            if score >= 0.6 and score > best_score:
                                best_score = score
                                found_in = other_vid

                unverified.append({
                    "quote": quote,
                    "cited_verse": cited_vid,
                    "actual_verse": found_in
                })

    return {
        "verified": verified,
        "unverified": unverified,
        "uncited": uncited
    }


def remove_sentence_with_quote(text: str, quote_str: str, cit_str: str | None = None) -> tuple[str, str | None]:
    """Find and cleanly remove the whole sentence containing the given quote and its citation.
    Also removes the immediately following sentence if it begins with
    'This verse', 'This passage', 'This suggests', 'Here,', or 'It '
    AND contains no quote or BG citation.
    """
    q_pat = re.compile(r'["“”]' + re.escape(quote_str) + r'["“”]')
    m = q_pat.search(text)
    if not m:
        return text, None

    q_start = m.start()
    q_end = m.end()

    # Match following citation if present
    cit_end = q_end
    if cit_str:
        c_pat = re.compile(r'^\s*(?:\((?:BG\s*)?' + re.escape(cit_str) + r'\)|(?:BG\s*)' + re.escape(cit_str) + r'\b)', re.IGNORECASE)
    else:
        c_pat = re.compile(r'^\s*(?:\((?:BG\s*)?[0-9]{1,2}\.[0-9]{1,2}\)|(?:BG\s*)[0-9]{1,2}\.[0-9]{1,2}\b)', re.IGNORECASE)

    cm = c_pat.search(text[q_end:])
    if cm:
        cit_end = q_end + cm.end()

    # Find start of sentence (scanning backwards from q_start within line/paragraph)
    before = text[:q_start]
    sent_start = 0
    # Boundary before sentence: paragraph break (\n\n), header line, bullet point, or [.!?] followed by whitespace
    term_matches = list(re.finditer(r'(?:(?<!\d)[.!?]["\'”\)]*|\n)\s*', before))
    if term_matches:
        last_term = term_matches[-1]
        sent_start = last_term.end()

    # Find end of primary sentence
    after = text[cit_end:]
    m_after_punct = re.match(r'^\s*["\'”\)]*([.!?])["\'”\)]*', after)
    if m_after_punct:
        sent_end = cit_end + m_after_punct.end()
        m_space = re.match(r'^[ \t]+', text[sent_end:])
        if m_space:
            sent_end += m_space.end()
    elif re.match(r'^\s*,\s*[a-z]', after):
        m_next_term = re.search(r'(?:(?<!\d)[.!?]["\'”\)]*|\n)', after)
        if m_next_term:
            sent_end = cit_end + m_next_term.end()
            m_space = re.match(r'^[ \t]+', text[sent_end:])
            if m_space:
                sent_end += m_space.end()
        else:
            sent_end = len(text)
    else:
        sent_end = cit_end
        m_space = re.match(r'^[ \t]+', text[sent_end:])
        if m_space:
            sent_end += m_space.end()

    # Task 2: Check immediately following sentence for dangling commentary
    rest = text[sent_end:]
    lead_ws = re.match(r'^\s*', rest)
    ws_len = lead_ws.end() if lead_ws else 0
    next_body = rest[ws_len:]

    if any(next_body.startswith(p) for p in DANGLING_PREFIXES):
        m_next_term = re.search(r'(?:(?<!\d)[.!?]["\'”\)]*|\n)', next_body)
        if m_next_term:
            next_sent_end_rel = ws_len + m_next_term.end()
            m_sp2 = re.match(r'^[ \t]+', rest[next_sent_end_rel:])
            if m_sp2:
                next_sent_end_rel += m_sp2.end()
        else:
            next_sent_end_rel = len(rest)

        candidate_sentence = rest[ws_len:next_sent_end_rel].strip()
        has_quote = bool(re.search(r'["“”]', candidate_sentence))
        has_citation = bool(CITATION_PATTERN.search(candidate_sentence))

        if not has_quote and not has_citation:
            logger.info("Also removed dangling commentary following unverified quote: %s", repr(candidate_sentence))
            sent_end = sent_end + next_sent_end_rel

    removed = text[sent_start:sent_end].strip()
    new_text = text[:sent_start] + text[sent_end:]
    return new_text, removed


def ensure_no_empty_sections(text: str) -> str:
    """If removal leaves a sub-question section empty of text, leave single sentence:
    'No verse could be reliably quoted for this part of the question.'"""
    EMPTY_MSG = "No verse could be reliably quoted for this part of the question."
    if not text.strip():
        return EMPTY_MSG

    # Pattern for headings: markdown headings (### ...) or bold numbered headers (**1. ...**)
    heading_pattern = re.compile(r'(?m)^(#{1,6}\s+.*|\*\*[0-9]+\..*?\*\*)$')
    matches = list(heading_pattern.finditer(text))
    if not matches:
        return text

    # Check if any section is actually empty
    has_empty = False
    for i, m in enumerate(matches):
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if not body:
            has_empty = True
            break

    if not has_empty:
        return text

    parts = []
    intro = text[:matches[0].start()]
    if intro.strip():
        parts.append(intro.rstrip() + "\n\n")

    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if not body:
            body = EMPTY_MSG
        parts.append(f"{heading}\n{body}\n\n")

    return "".join(parts).strip()


def resolve_quotes_and_citations(
    answer: str,
    context_verses: list[dict[str, Any]],
    verse_store: dict[str, dict[str, Any]],
    strict_following: bool = True
) -> tuple[str, list[str]]:
    """Resolve and verify quotes in the answer according to the following rules:
    (a) If a quoted passage is a verbatim substring (normalized) of any retrieved verse's English
        translation, leave the text and quotation marks unchanged; if it has no citation,
        append that verse's (BG x.y) after it.
    (b) Ignore quoted passages shorter than 5 words (scare quotes).
    (c) If a quote is cited to a verse and has clear overlap (>= 0.6) with that verse,
        replace it with the verified first translation of that verse.
    (d) If a quote matches a DIFFERENT retrieved verse, correct the following citation to that verse.
    (e) For quotes of 5+ words that match no retrieved verse and have fuzzy overlap with cited verse < 0.6:
        remove the whole sentence containing that quote and its citation. Do not keep text or add (paraphrase).
    (f) If removal leaves a sub-question section empty of text, leave single sentence:
        'No verse could be reliably quoted for this part of the question.'
    (g) Log removed text server-side only. Client warning must NOT contain removed text;
        use: 'One unsupported statement was removed from the answer.'
    (h) Do not send warnings to the client for quotes that were corrected or left in place;
        log them server-side.
    """
    ctx_trans = extract_candidate_translations_by_verse(context_verses)
    warnings: list[str] = []
    modified_answer = answer
    sentences_removed = 0

    citation_pattern = re.compile(
        r'\b(?:BG|Śrī Bhagavad‑gītā|Bhagavad Gita)\s*([0-9]{1,2}\.[0-9]{1,2})\b|\((?:BG\s*)?([0-9]{1,2}\.[0-9]{1,2})\)',
        re.IGNORECASE
    )

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', modified_answer) if p.strip()]
    seen_quotes: set[str] = set()

    for p in paragraphs:
        matches = list(QUOTE_PATTERN.finditer(p))
        for m in matches:
            quote_text = m.group(1).strip()
            words = quote_text.split()
            word_count = len(words)

            # Rule 1(b): Ignore quoted passages shorter than 5 words (scare quotes)
            if word_count < 5:
                continue

            if quote_text in seen_quotes:
                continue
            seen_quotes.add(quote_text)

            # Check following citation
            after_text = p[m.end():]
            cit_match = citation_pattern.search(after_text)
            cited_vid = (cit_match.group(1) or cit_match.group(2)) if cit_match else None

            norm_q = normalize_text(quote_text)

            # Case A: Quote has a citation
            if cited_vid:
                target_trans = ctx_trans.get(cited_vid, [])
                is_exact = any(norm_q in t for t in target_trans)
                if is_exact:
                    logger.info("Quote '%s...' is verbatim verified for BG %s", quote_text[:30], cited_vid)
                    continue

                cv_overlap = max((fuzzy_overlap_ratio(norm_q, t) for t in target_trans), default=0.0)

                # Check if it matches a different retrieved verse
                diff_vid = None
                best_diff_score = 0.0
                for ovid, otrans in ctx_trans.items():
                    if ovid != cited_vid:
                        if any(norm_q in t for t in otrans):
                            diff_vid = ovid
                            break
                        score = max((fuzzy_overlap_ratio(norm_q, t) for t in otrans), default=0.0)
                        if score >= 0.6 and score > best_diff_score:
                            best_diff_score = score
                            diff_vid = ovid

                # Branch 1: clear overlap >= 0.6 with cited verse -> replace with first translation
                if cv_overlap >= 0.6:
                    rec = verse_store.get(cited_vid, {})
                    eng = rec.get("translations", {}).get("english", [])
                    first_trans = eng[0]["text"] if (eng and isinstance(eng[0], dict) and "text" in eng[0]) else None
                    if first_trans:
                        pat = re.compile(r'["“”]' + re.escape(quote_text) + r'["“”]')
                        modified_answer = pat.sub(f'“{first_trans}”', modified_answer, count=1)
                        logger.info("Replaced quote with verified translation for BG %s: %s...", cited_vid, quote_text[:30])
                    # Corrected in place: log server-side, do not send warning to client

                # Branch 2: matches a DIFFERENT retrieved verse -> correct the citation
                elif diff_vid:
                    pat = re.compile(
                        r'(["“”]' + re.escape(quote_text) + r'["“”][^()\n]*?\((?:BG\s*)?)' + re.escape(cited_vid) + r'(\))'
                    )
                    if pat.search(modified_answer):
                        modified_answer = pat.sub(r'\g<1>' + diff_vid + r'\g<2>', modified_answer, count=1)
                    else:
                        pat2 = re.compile(
                            r'(["“”]' + re.escape(quote_text) + r'["“”][^\n]*?\b(?:BG\s*|Śrī Bhagavad‑gītā\s*|Bhagavad Gita\s*)?)' + re.escape(cited_vid) + r'\b'
                        )
                        modified_answer = pat2.sub(r'\g<1>' + diff_vid, modified_answer, count=1)
                    logger.info("Corrected citation for quote from BG %s to BG %s: %s...", cited_vid, diff_vid, quote_text[:30])
                    # Corrected in place: log server-side, do not send warning to client

                # Branch 3: matches no retrieved verse and cv_overlap < 0.6
                else:
                    if word_count >= 5:
                        modified_answer, removed = remove_sentence_with_quote(modified_answer, quote_text, cited_vid)
                        sentences_removed += 1
                        logger.info("Removed unsupported quote statement for BG %s: %s", cited_vid, repr(removed))
                        warnings.append("One unsupported statement was removed from the answer.")

            # Case B: Quote has NO citation (uncited)
            else:
                found_vid = None
                best_diff_score = 0.0
                for ovid, otrans in ctx_trans.items():
                    if any(norm_q in t for t in otrans):
                        found_vid = ovid
                        break
                    score = max((fuzzy_overlap_ratio(norm_q, t) for t in otrans), default=0.0)
                    if score >= 0.6 and score > best_diff_score:
                        best_diff_score = score
                        found_vid = ovid

                # Rule 1(a): matches a retrieved verse -> leave text and quotes unchanged, append (BG x.y)
                if found_vid:
                    pat = re.compile(r'(["“”]' + re.escape(quote_text) + r'["“”])(\s*[.,;!?])?')
                    def repl_cit(match_obj):
                        quote_part = match_obj.group(1)
                        punct = match_obj.group(2) or ''
                        if punct.strip() == '.':
                            return f'{quote_part} (BG {found_vid}).'
                        elif punct.strip():
                            return f'{quote_part} (BG {found_vid}){punct}'
                        else:
                            return f'{quote_part} (BG {found_vid})'
                    modified_answer = pat.sub(repl_cit, modified_answer, count=1)
                    logger.info("Appended citation (BG %s) to uncited quote: %s...", found_vid, quote_text[:30])
                    # Corrected in place: log server-side, do not send warning to client

                else:
                    if word_count >= 5:
                        modified_answer, removed = remove_sentence_with_quote(modified_answer, quote_text, None)
                        sentences_removed += 1
                        logger.info("Removed unsupported uncited quote statement: %s", repr(removed))
                        warnings.append("One unsupported statement was removed from the answer.")

    if sentences_removed > 0 or not modified_answer.strip():
        modified_answer = ensure_no_empty_sections(modified_answer)
    return modified_answer, warnings
