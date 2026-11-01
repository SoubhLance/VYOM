import json
import logging
import os
import re
import sys
import time
from typing import Any
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "retrieval") not in sys.path:
    sys.path.insert(0, str(ROOT / "retrieval"))

# Load environment variables from backend/.env or root .env
_env_backend = ROOT / ".env"
_env_root = ROOT.parent / ".env"
if _env_backend.exists():
    load_dotenv(dotenv_path=_env_backend)
elif _env_root.exists():
    load_dotenv(dotenv_path=_env_root)
else:
    load_dotenv()

from llm.client import (
    generate_answer,
    get_last_finish_reason,
    get_last_usage,
    get_last_model,
    get_last_fallback_used,
)
from retrieval.prompt import SYSTEM_PROMPT, build_rag_prompt
from retrieval.router import load_valid_ids, parse_verse_ref
from retrieval.search import Searcher
from retrieval.multi import retrieve_multi, decompose, is_single_topic_query
from retrieval.prompt_v2 import SYSTEM_PROMPT_V2, build_rag_prompt_v2
from retrieval.verify_quotes import (
    check_quotes_by_citation,
    normalize_text,
    fuzzy_overlap_ratio,
    extract_candidate_translations_by_verse,
    extract_candidate_translations,
    resolve_quotes_and_citations,
    remove_sentence_with_quote,
    ensure_no_empty_sections,
)
from api.clips import clips_for, mount_audio, load_verse_clips

logger = logging.getLogger("vyom.api")
logging.basicConfig(level=logging.INFO)

VERSES_PATH = ROOT / "data" / "processed" / "verses.jsonl"


def load_verse_store() -> dict[str, dict]:
    """Load all 701 verse records into an in-memory dictionary for fast retrieval."""
    if not VERSES_PATH.exists():
        logger.warning("verses.jsonl not found at %s", VERSES_PATH)
        return {}
    verses = {}
    with open(VERSES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                item = json.loads(line)
                verses[item["verse_id"]] = item
    return verses


def get_verse_neighbors(verse_id: str, verse_store: dict[str, dict], offsets: tuple[int, ...] = (1, 2)) -> list[dict]:
    """Fetch forward neighboring verses (e.g. 2.10 and 2.11 for 2.9) if they exist in verse_store."""
    neighbors = []
    try:
        parts = verse_id.split(".")
        ch = int(parts[0])
        v_num = int(parts[1])
        for offset in offsets:
            neighbor_id = f"{ch}.{v_num + offset}"
            if neighbor_id in verse_store:
                n_rec = dict(verse_store[neighbor_id])
                n_rec["is_neighbor"] = True
                n_rec["neighbor_of"] = verse_id
                neighbors.append(n_rec)
    except (ValueError, IndexError):
        pass
    return neighbors


def expand_verses_with_neighbors(retrieved_verses: list[dict], verse_store: dict[str, dict]) -> list[dict]:
    """Expand retrieved verses with their immediate conversational neighbors without duplicates."""
    expanded = []
    seen = set()

    for v in retrieved_verses:
        vid = v.get("verse_id")
        if vid and vid not in seen:
            seen.add(vid)
            expanded.append(v)
            # Add neighbors for this verse
            neighbors = get_verse_neighbors(vid, verse_store, offsets=(1, 2))
            for n in neighbors:
                n_id = n.get("verse_id")
                if n_id and n_id not in seen:
                    seen.add(n_id)
                    expanded.append(n)

    return expanded


CRISIS_RESPONSE_TEXT = (
    "You are not alone, and you deserve support from a real person right now. "
    "Please know that help is available and there are people who care and want to support you through this difficult moment.\n\n"
    "• India: Call Tele-MANAS at 14416 (please confirm locally) or 1800-891-4416 (24/7, toll-free)\n"
    "• Outside India: Visit https://findahelpline.com to find free, confidential support in your country\n"
    "• If in immediate danger: Contact your local emergency services or reach out to a trusted person nearby."
)

CRISIS_PATTERNS = [
    r"\bsuicide\b",
    r"\bsuicidal\b",
    r"\bend(?:ing)?\s+my\s+life\b",
    r"\bkill(?:ing)?\s+myself\b",
    r"\bself[\s-]harm\b",
    r"\bwant\s+to\s+die\b",
    r"\bwanna\s+die\b",
    r"\bdo(?:n['’]?t|\s+not)\s+want\s+to\s+live\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bend\s+it\s+all\b",
    r"\bbetter\s+off\s+dead\b",
    r"\bca(?:n['’]?t|nnot)\s+go\s+on\b",
    r"\bhurt\s+myself\b",
    r"\btake\s+my\s+own\s+life\b",
    r"\bmarna\s+chahta\b",
    r"\bmarna\s+chahti\b",
    r"\bjeena\s+nahi\b",
    r"\bjeene\s+ka\s+mann\s+nahi\b",
    r"\baatmahatya\b",
    r"\batmahatya\b",
    r"\bmorte\s+chai\b",
]
CRISIS_REGEX = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)


def is_crisis_query(query: str, *args, **kwargs) -> bool:
    """Check if raw query relates to crisis/suicide/self-harm (case-insensitive, check raw query only)."""
    if not query:
        return False
    return bool(CRISIS_REGEX.search(query))


def is_despair_verse(vid: str) -> bool:
    """Check if verse is in Chapter 1 or Verses 2.1 to 2.10 (Arjuna's despair/narration)."""
    try:
        parts = vid.split(".")
        ch_int = int(parts[0])
        v_int = int(parts[1])
        if ch_int == 1 or (ch_int == 2 and 1 <= v_int <= 10):
            return True
    except (ValueError, IndexError):
        pass
    return False


def get_first_english_translation(verse_id: str, verse_store: dict[str, dict]) -> str | None:
    """Fetch the first English translation for a verse from verse_store."""
    rec = verse_store.get(verse_id)
    if not rec:
        return None
    translations = rec.get("translations")
    if isinstance(translations, dict):
        eng = translations.get("english", [])
        if eng and isinstance(eng, list):
            first = eng[0]
            if isinstance(first, dict) and "text" in first:
                return first["text"]
            elif isinstance(first, str):
                return first
    elif isinstance(translations, list):
        if translations:
            first = translations[0]
            if isinstance(first, dict) and "text" in first:
                return first["text"]
            elif isinstance(first, str):
                return first
    if rec.get("translation"):
        return rec["translation"]
    if rec.get("text"):
        return rec["text"]
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI:
    1. Preloads valid verse IDs from router.py into app.state.valid_ids.
    2. Preloads processed verse objects from data/processed/verses.jsonl into app.state.verse_store.
    3. Loads audio clips mapping once on startup via load_verse_clips().
    4. Initializes Searcher engine once with bge-m3.
    """
    logger.info("Initializing VYOM API resources...")

    # Load valid IDs for routing
    try:
        app.state.valid_ids = load_valid_ids()
        logger.info("Loaded %d valid verse IDs for routing.", len(app.state.valid_ids))
    except Exception as e:
        logger.error("Failed to load valid verse IDs: %s", e)
        app.state.valid_ids = set()

    # Load full verse dictionary
    try:
        app.state.verse_store = load_verse_store()
        logger.info("Loaded %d verse records into memory.", len(app.state.verse_store))
    except Exception as e:
        logger.error("Failed to load verse store: %s", e)
        app.state.verse_store = {}

    # Load audio clips index
    try:
        clips_map = load_verse_clips()
        logger.info("Loaded audio clips for %d verses.", len(clips_map))
    except Exception as e:
        logger.error("Failed to load verse clips: %s", e)

    # Initialize vector Searcher (bge-m3)
    try:
        logger.info("Initializing vector Searcher (bge-m3)...")
        app.state.searcher = Searcher("bge-m3")
        logger.info("Searcher initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Searcher: %s", e)
        app.state.searcher = None

    yield

    # Clean up Searcher on shutdown
    searcher = getattr(app.state, "searcher", None)
    if searcher is not None:
        try:
            searcher.close()
            logger.info("Searcher closed successfully.")
        except Exception as e:
            logger.warning("Error closing searcher: %s", e)


app = FastAPI(
    title="VYOM API",
    description="Ancient Wisdom. Infinite Understanding. Bhagavad Gita RAG Serving Layer.",
    version="0.1.0",
    lifespan=lifespan,
)

mount_audio(app)


class AskRequest(BaseModel):
    query: str = Field(..., description="User query or verse reference", min_length=1)
    top_k: int = Field(default=5, description="Number of verses to retrieve", ge=1, le=10)
    multi: bool = Field(default=False, description="Enable multi-topic decomposition and citation quote checking")


class AskResponse(BaseModel):
    query: str
    routed: bool | str = False
    cited_verses: list[str]
    answer: str
    sources: list[dict] = Field(default_factory=list)
    sub_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "searcher_ready": getattr(app.state, "searcher", None) is not None,
        "valid_ids_count": len(getattr(app.state, "valid_ids", [])),
    }


def replace_supplied_phrases(text: str) -> str:
    """Replace 'supplied/provided' + (verses|passages|context|text) with
    'verses retrieved for this question' (case-insensitive, preserving leading capital)."""
    pattern = re.compile(r'\b(supplied|provided)\s+(verses|passages|context|text)\b', re.IGNORECASE)
    def _repl(m: re.Match) -> str:
        word = m.group(1)
        if word[0].isupper():
            return "Verses retrieved for this question"
        else:
            return "verses retrieved for this question"
    return pattern.sub(_repl, text)


VERB_BASE_MAP = {
    "states": "state",
    "says": "say",
    "mentions": "mention",
    "discusses": "discuss",
    "addresses": "address",
    "prohibits": "prohibit",
    "requires": "require",
}


def rewrite_gita_does_not(text: str) -> str:
    """Rewrite 'The Gita (does not|doesn't|never) (state|say|mention|discuss|explicitly|address|prohibit|require)'
    to 'The verses retrieved for this question do not ...' keeping the verb.
    Case-insensitive, keep a leading capital.
    """
    pattern = re.compile(
        r'\bthe\s+gita\s+(?:does\s*not|doesn[\'’]t|never)\s+(state[s]?|say[s]?|mention[s]?|discuss(?:es)?|explicitly|address(?:es)?|prohibit[s]?|require[s]?)\b',
        re.IGNORECASE
    )
    def _repl(m: re.Match) -> str:
        raw_verb = m.group(1)
        base_verb = VERB_BASE_MAP.get(raw_verb.lower(), raw_verb)
        return f"The verses retrieved for this question do not {base_verb}"
    return pattern.sub(_repl, text)


def relabel_unquoted_prose_citations(
    answer: str,
    context_verses: list[dict[str, Any]],
    verse_store: dict[str, dict] = None,
) -> str:
    """For a '(BG x.y)' citation that is not directly after a closing quote AND whose
    sentence contains no verified quote for that same verse, rewrite it to '(paraphrase, BG x.y)'.
    Leave existing '(paraphrase, BG x.y)' alone.
    """
    by_verse = extract_candidate_translations_by_verse(context_verses)

    citation_pat = re.compile(
        r'\((?:BG\s*)?([0-9]{1,2}\.[0-9]{1,2})\)',
        re.IGNORECASE
    )

    matches = list(citation_pat.finditer(answer))
    if not matches:
        return answer

    # Process matches in reverse order so replacements do not invalidate earlier offsets
    res_text = answer
    for m in reversed(matches):
        cit_span = m.span()
        cit_str = m.group(0)
        vid = m.group(1)

        before_text = res_text[:cit_span[0]]
        # 1. Check if directly after a closing quote
        if re.search(r'["“”]\s*$', before_text):
            continue

        # 2. Check if already inside a paraphrase marker
        if re.search(r'\(\s*paraphrase\s*,\s*$', before_text, re.IGNORECASE) or "paraphrase" in cit_str.lower():
            continue

        # 3. Find enclosing sentence boundaries
        # Strip terminal punctuation right before citation so we don't truncate the sentence to just the citation
        trimmed_before = re.sub(r'[.!?]["”\'\)\]]*\s*$', '', before_text)
        s_start = 0
        for delim in ('. ', '.\n', '! ', '!\n', '? ', '?\n', '\n\n', '\n'):
            pos = trimmed_before.rfind(delim)
            if pos != -1 and pos + len(delim) > s_start:
                s_start = pos + len(delim)
        after_text = res_text[cit_span[1]:]
        end_match = re.search(r'(?:[.!?](?:\s|$))|\n', after_text)
        if end_match:
            s_end = cit_span[1] + end_match.end()
        else:
            s_end = len(res_text)

        sentence = res_text[s_start:s_end].strip()

        # 4. Check if sentence contains any verified quote for vid
        quotes_in_sent = re.findall(r'["“”]([^"“”]+?)["“”]', sentence)
        has_verified_quote = False

        cands = list(by_verse.get(vid, []))
        if not cands and verse_store and vid in verse_store:
            cands.extend(extract_candidate_translations([verse_store[vid]]))

        for q in quotes_in_sent:
            q_norm = normalize_text(q)
            if len(q_norm.split()) < 3:
                continue
            for cand in cands:
                c_norm = normalize_text(cand)
                if q_norm in c_norm or fuzzy_overlap_ratio(q_norm, c_norm) >= 0.70:
                    has_verified_quote = True
                    break
            if has_verified_quote:
                break

        if not has_verified_quote:
            new_cit = f"(paraphrase, BG {vid})"
            res_text = res_text[:cit_span[0]] + new_cit + res_text[cit_span[1]:]

    return res_text


def find_prose_citations(answer: str) -> tuple[int, list[tuple[str, str]]]:
    """Find every 'BG x.y' or '(BG x.y)' in the final answer that is NOT
    directly after a closing quotation mark (ignoring allowed '(paraphrase, BG x.y)' markers).
    Returns:
        (count, [(citation_str, sentence_text), ...])
    """
    citation_pat = re.compile(
        r'\b(?:BG|Śrī Bhagavad‑gītā|Bhagavad Gita)\s*[0-9]{1,2}\.[0-9]{1,2}\b|\((?:BG\s*)?[0-9]{1,2}\.[0-9]{1,2}\)',
        re.IGNORECASE
    )
    prose_refs: list[tuple[str, str]] = []

    for m in citation_pat.finditer(answer):
        before_text = answer[:m.start()]
        # Check if directly preceded by a closing quotation mark (allowing optional whitespace)
        is_after_quote = bool(re.search(r'["“”]\s*$', before_text))
        # Check if inside an allowed paraphrase marker, e.g. (paraphrase, BG x.y)
        is_paraphrase = bool(re.search(r'\(\s*paraphrase\s*,\s*$', before_text, re.IGNORECASE))

        if not is_after_quote and not is_paraphrase:
            s_start = 0
            for delim in ('. ', '.\n', '! ', '!\n', '? ', '?\n', '\n\n', '\n'):
                pos = before_text.rfind(delim)
                if pos != -1 and pos + len(delim) > s_start:
                    s_start = pos + len(delim)
            after_text = answer[m.end():]
            end_match = re.search(r'(?:[.!?](?:\s|$))|\n', after_text)
            if end_match:
                s_end = m.end() + end_match.end()
            else:
                s_end = len(answer)
            sentence = answer[s_start:s_end].strip()
            prose_refs.append((m.group(0), sentence))
            logger.warning("PROSE_CITATION_FLAGGED: citation='%s' | sentence='%s'", m.group(0), sentence)

    return len(prose_refs), prose_refs


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request, response: Response):
    """Endpoint to answer questions grounded in Bhagavad Gita verses:
    1. Check regex router for explicit verse references.
    2. If not routed, run dense search (or multi-query retrieval if req.multi is True).
    3. Expand retrieved hits with conversational neighbors.
    4. Build grounded RAG prompt and call generate_answer.
    5. Return structured JSON response with sanitized error handling.
    """
    # Handle optional reasoning effort header if provided
    reasoning_effort_hdr = request.headers.get("X-Groq-Reasoning-Effort")
    if reasoning_effort_hdr is not None:
        if reasoning_effort_hdr.strip() and reasoning_effort_hdr.strip().lower() != "unset":
            os.environ["GROQ_REASONING_EFFORT"] = reasoning_effort_hdr.strip()
        else:
            os.environ.pop("GROQ_REASONING_EFFORT", None)

    valid_ids: set[str] = getattr(request.app.state, "valid_ids", None)
    if valid_ids is None:
        valid_ids = load_valid_ids()

    verse_store: dict[str, dict] = getattr(request.app.state, "verse_store", None)
    if verse_store is None:
        verse_store = load_verse_store()

    # Step 1: Check parse_verse_ref from router.py (Verse routing skips decomposition)
    ref = parse_verse_ref(req.query, valid_ids)

    if ref:
        routed = True
        cited_verses = [ref]
        retrieved_verses = [verse_store.get(ref, {"verse_id": ref})]
        context_verses = expand_verses_with_neighbors(retrieved_verses, verse_store)
        sources = []
        for v in context_verses:
            vid = v.get("verse_id")
            sources.append({
                "verse_id": vid,
                "sanskrit": v.get("sanskrit"),
                "transliteration": v.get("transliteration"),
                "is_neighbor": v.get("is_neighbor", False),
                "neighbor_of": v.get("neighbor_of", None),
                "for_question": [0] if req.multi else [],
                "clips": clips_for(vid) if vid else [],
            })

        prompt = build_rag_prompt(req.query, context_verses)
        try:
            answer = generate_answer(prompt, system_prompt=SYSTEM_PROMPT)
        except Exception as e:
            logger.error("LLM generation failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="The guide is busy, please try again in a minute"
            )

        model_used = get_last_model() or getattr(answer, "model", None) or "unknown"
        fallback_fired = get_last_fallback_used() or getattr(answer, "fallback_used", False)
        logger.info("LLM_MODEL_USED: %s", model_used)
        if fallback_fired:
            logger.info("LLM_FALLBACK_USED")
        if response:
            response.headers["X-LLM-Model"] = str(model_used)

        return AskResponse(
            query=req.query,
            routed=True,
            cited_verses=cited_verses,
            answer=answer,
            sources=sources,
            sub_questions=[],
            warnings=[],
        )

    # Step 2: Non-routed queries
    routed = False
    searcher: Searcher = getattr(request.app.state, "searcher", None)
    if searcher is None:
        raise HTTPException(
            status_code=503,
            detail="Searcher engine is not ready or failed to initialize."
        )

    if not req.multi:
        # Default / Old path
        hits = searcher.search(req.query, k=req.top_k)
        if is_crisis_query(req.query):
            hits = [h for h in hits if not is_despair_verse(h.get("verse_id", ""))]
        cited_verses = [h["verse_id"] for h in hits]
        retrieved_verses = [verse_store.get(vid, {"verse_id": vid, **h}) for vid, h in zip(cited_verses, hits)]
        context_verses = expand_verses_with_neighbors(retrieved_verses, verse_store)
        if is_crisis_query(req.query):
            context_verses = [v for v in context_verses if not is_despair_verse(v.get("verse_id", ""))]

        sources = []
        for v in context_verses:
            vid = v.get("verse_id")
            sources.append({
                "verse_id": vid,
                "sanskrit": v.get("sanskrit"),
                "transliteration": v.get("transliteration"),
                "is_neighbor": v.get("is_neighbor", False),
                "neighbor_of": v.get("neighbor_of", None),
                "for_question": [],
                "clips": clips_for(vid) if vid else [],
            })

        prompt = build_rag_prompt(req.query, context_verses)
        try:
            answer = generate_answer(prompt, system_prompt=SYSTEM_PROMPT)
        except Exception as e:
            logger.error("LLM generation failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="The guide is busy, please try again in a minute"
            )

        model_used = get_last_model() or getattr(answer, "model", None) or "unknown"
        fallback_fired = get_last_fallback_used() or getattr(answer, "fallback_used", False)
        logger.info("LLM_MODEL_USED: %s", model_used)
        if fallback_fired:
            logger.info("LLM_FALLBACK_USED")
        if response:
            response.headers["X-LLM-Model"] = str(model_used)

        return AskResponse(
            query=req.query,
            routed=False,
            cited_verses=cited_verses,
            answer=answer,
            sources=sources,
            sub_questions=[],
            warnings=[],
        )

    # New path: req.multi is True
    if is_crisis_query(req.query):
        logger.info("Crisis query detected in multi path. Returning immediate fixed response.")
        return AskResponse(
            query=req.query,
            routed="crisis",
            cited_verses=[],
            answer=CRISIS_RESPONSE_TEXT,
            sources=[],
            sub_questions=[],
            warnings=[],
        )

    t_start = time.perf_counter()

    # Stage 1: Decomposition
    t_decomp_0 = time.perf_counter()
    if is_single_topic_query(req.query):
        logger.info("DECOMPOSITION_SKIPPED: query is single topic ('%s')", req.query)
        sub_questions = [req.query.strip()]
    else:
        logger.info("DECOMPOSITION_USED: query is compound/multi-topic ('%s')", req.query)
        sub_questions = decompose(req.query)
    t_decomp = time.perf_counter() - t_decomp_0

    # Stage 2: Retrieval & Context Assembly
    t_retrieval_0 = time.perf_counter()
    multi_res = retrieve_multi(searcher, req.query, per_q=5, cap=12, sub_questions=sub_questions)
    sub_questions = multi_res.get("sub_questions", sub_questions)
    multi_verses = multi_res.get("verses", [])

    if is_crisis_query(req.query, sub_questions):
        logger.info("Crisis query detected. Excluding chapter 1 and 2.1-2.10 verses.")
        multi_verses = [v for v in multi_verses if not is_despair_verse(v.get("verse_id", ""))]

    cited_verses = [v["verse_id"] for v in multi_verses]

    retrieved_verses = []
    for mv in multi_verses:
        vid = mv["verse_id"]
        base_rec = dict(verse_store.get(vid, {"verse_id": vid}))
        base_rec["for_question"] = mv.get("for_question", [])
        base_rec["score"] = mv.get("score", 0.0)
        retrieved_verses.append(base_rec)

    if os.getenv("VYOM_MULTI_NEIGHBORS", "0") == "1":
        context_verses = expand_verses_with_neighbors(retrieved_verses, verse_store)
        if is_crisis_query(req.query, sub_questions):
            context_verses = [v for v in context_verses if not is_despair_verse(v.get("verse_id", ""))]
    else:
        context_verses = retrieved_verses

    sources = []
    for v in context_verses:
        vid = v.get("verse_id")
        sources.append({
            "verse_id": vid,
            "sanskrit": v.get("sanskrit"),
            "transliteration": v.get("transliteration"),
            "is_neighbor": v.get("is_neighbor", False),
            "neighbor_of": v.get("neighbor_of", None),
            "for_question": v.get("for_question", []),
            "clips": clips_for(vid) if vid else [],
        })

    prompt = build_rag_prompt_v2(req.query, sub_questions, context_verses)
    t_retrieval = time.perf_counter() - t_retrieval_0

    # Stage 3: LLM Generation
    t_gen_0 = time.perf_counter()
    logger.info("MULTI PROMPT SIZE: %d characters", len(prompt))
    try:
        answer = generate_answer(prompt, system_prompt=SYSTEM_PROMPT_V2)
    except Exception as e:
        logger.error("LLM generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"LLM generation failed: {e}"
        )

    model_used = get_last_model() or getattr(answer, "model", None) or "unknown"
    fallback_fired = get_last_fallback_used() or getattr(answer, "fallback_used", False)
    logger.info("LLM_MODEL_USED: %s", model_used)
    if fallback_fired:
        logger.info("LLM_FALLBACK_USED")

    warnings: list[str] = []
    finish_reason = get_last_finish_reason()
    if finish_reason == "length":
        warnings.append("truncated")

    t_gen = time.perf_counter() - t_gen_0

    # Stage 4: Verification & Resolution
    t_verif_0 = time.perf_counter()
    answer, quote_warnings = resolve_quotes_and_citations(answer, context_verses, verse_store, strict_following=True)
    warnings.extend(quote_warnings)

    # Post-check quotes: any residual unverified or uncited quotes of 5+ words have their sentence removed
    chk_after = check_quotes_by_citation(answer, context_verses, strict_following=True)
    if chk_after["unverified"] or chk_after["uncited"]:
        for item in chk_after["unverified"]:
            q_txt = item.get("quote", "") if isinstance(item, dict) else str(item)
            cv = item.get("cited_verse", "") if isinstance(item, dict) else ""
            if len(q_txt.split()) >= 5:
                answer, rem = remove_sentence_with_quote(answer, q_txt, cv)
                logger.info("Removed residual unsupported quote statement for BG %s: %s", cv, repr(rem))
                warnings.append("One unsupported statement was removed from the answer.")

        for item in chk_after["uncited"]:
            q_txt = item.get("quote", "") if isinstance(item, dict) else str(item)
            if len(q_txt.split()) >= 5:
                answer, rem = remove_sentence_with_quote(answer, q_txt, None)
                logger.info("Removed residual unsupported uncited quote statement: %s", repr(rem))
                warnings.append("One unsupported statement was removed from the answer.")

        answer = ensure_no_empty_sections(answer)

    t_verif = time.perf_counter() - t_verif_0

    t_total = time.perf_counter() - t_start
    logger.info(
        "TIMING: decomposition=%.3fs, retrieval=%.3fs, generation=%.3fs, verification=%.3fs | total=%.3fs",
        t_decomp, t_retrieval, t_gen, t_verif, t_total
    )

    chk_final = check_quotes_by_citation(answer, context_verses, strict_following=True)
    logger.info(
        "QUOTE CHECK FINAL COUNTS: verified=%d, unverified=%d, uncited=%d",
        len(chk_final.get("verified", [])),
        len(chk_final.get("unverified", [])),
        len(chk_final.get("uncited", [])),
    )

    # Task 4 & 5: Post-check prose citations & relabelling
    prose_count_before, prose_refs = find_prose_citations(answer)
    for cit_str, sent in prose_refs:
        logger.warning("Prose citation '%s' not following quote: %s", cit_str, sent)
    logger.info("PROSE_CITATIONS_COUNT_BEFORE: %d", prose_count_before)

    # Post-processing:
    # 5a: Replace supplied/provided phrases
    answer = replace_supplied_phrases(answer)
    # 5b: Relabel unquoted prose citations
    answer = relabel_unquoted_prose_citations(answer, context_verses, verse_store)
    # 5c: Rewrite 'The Gita does not...' claims
    answer = rewrite_gita_does_not(answer)

    prose_count_after, prose_refs_after = find_prose_citations(answer)
    for cit_str, sent in prose_refs_after:
        logger.warning("REMAINING_PROSE_CITATION: citation='%s' | sentence='%s'", cit_str, sent)
    logger.info("PROSE_CITATIONS_COUNT_AFTER: %d", prose_count_after)
    logger.info("PROSE_CITATIONS_COUNT: %d (before: %d)", prose_count_after, prose_count_before)

    if response:
        response.headers["X-Prose-Citations-Count"] = str(prose_count_after)
        response.headers["X-Prose-Citations-Before"] = str(prose_count_before)
        response.headers["X-LLM-Model"] = str(model_used)
        if fallback_fired:
            response.headers["X-LLM-Fallback"] = "true"
        usage = get_last_usage()
        if usage.get("prompt_tokens") is not None:
            response.headers["X-Prompt-Tokens"] = str(usage["prompt_tokens"])
        if usage.get("completion_tokens") is not None:
            response.headers["X-Completion-Tokens"] = str(usage["completion_tokens"])
        if usage.get("total_tokens") is not None:
            response.headers["X-Total-Tokens"] = str(usage["total_tokens"])
        if usage.get("reasoning_tokens") is not None:
            response.headers["X-Reasoning-Tokens"] = str(usage["reasoning_tokens"])
        if usage.get("visible_word_count") is not None:
            response.headers["X-Visible-Word-Count"] = str(usage["visible_word_count"])

    return AskResponse(
        query=req.query,
        routed=False,
        cited_verses=cited_verses,
        answer=answer,
        sources=sources,
        sub_questions=sub_questions,
        warnings=warnings,
    )
