import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
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

from llm.client import generate_answer
from retrieval.prompt import SYSTEM_PROMPT, build_rag_prompt
from retrieval.router import load_valid_ids, parse_verse_ref
from retrieval.search import Searcher

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
        if len(parts) == 2:
            ch, v = int(parts[0]), int(parts[1])
            for offset in offsets:
                nid = f"{ch}.{v + offset}"
                if nid in verse_store:
                    n_rec = dict(verse_store[nid])
                    n_rec["is_neighbor"] = True
                    n_rec["neighbor_of"] = verse_id
                    neighbors.append(n_rec)
    except (ValueError, TypeError):
        pass
    return neighbors


def expand_verses_with_neighbors(
    retrieved_verses: list[dict],
    verse_store: dict[str, dict],
    offsets: tuple[int, ...] = (1, 2),
) -> list[dict]:
    """Expand retrieved verses with conversational neighbor contexts (e.g. 2.10 and 2.11 for 2.9)
    so dialogue context (Arjuna asking -> Krishna answering) is never broken.
    """
    seen_ids = set()
    expanded = []

    # 1. Primary retrieved hits
    for v in retrieved_verses:
        vid = v.get("verse_id")
        if vid and vid not in seen_ids:
            seen_ids.add(vid)
            expanded.append(v)

    # 2. Immediate forward neighbors
    for v in retrieved_verses:
        vid = v.get("verse_id")
        if not vid:
            continue
        for neighbor in get_verse_neighbors(vid, verse_store, offsets=offsets):
            n_vid = neighbor.get("verse_id")
            if n_vid and n_vid not in seen_ids:
                seen_ids.add(n_vid)
                expanded.append(neighbor)

    return expanded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: initialize searcher and verse store on startup, close on shutdown."""
    logger.info("Initializing VYOM services...")
    app.state.valid_ids = load_valid_ids()
    app.state.verse_store = load_verse_store()
    
    # Initialize Searcher (model_key='bge-m3')
    try:
        app.state.searcher = Searcher(model_key="bge-m3")
        logger.info("Searcher(bge-m3) initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Searcher: %s", e)
        app.state.searcher = None

    yield

    # Clean shutdown
    if getattr(app.state, "searcher", None):
        logger.info("Closing Searcher client...")
        try:
            app.state.searcher.close()
        except Exception as e:
            logger.warning("Error closing searcher: %s", e)


app = FastAPI(
    title="VYOM API",
    description="Ancient Wisdom. Infinite Understanding. Bhagavad Gita RAG Serving Layer.",
    version="0.1.0",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    query: str = Field(..., description="User query or verse reference", min_length=1)
    top_k: int = Field(default=5, description="Number of verses to retrieve", ge=1, le=10)


class AskResponse(BaseModel):
    query: str
    routed: bool
    cited_verses: list[str]
    answer: str


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "searcher_ready": getattr(app.state, "searcher", None) is not None,
        "valid_ids_count": len(getattr(app.state, "valid_ids", [])),
    }


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request):
    """Endpoint to answer questions grounded in Bhagavad Gita verses:
    1. Check regex router for explicit verse references.
    2. If not routed, run dense search with top_k.
    3. Expand retrieved hits with conversational neighbors (e.g. +1, +2).
    4. Build grounded RAG prompt and call generate_answer.
    5. Return structured JSON response with sanitized error handling.
    """
    valid_ids: set[str] = getattr(request.app.state, "valid_ids", None)
    if valid_ids is None:
        valid_ids = load_valid_ids()

    verse_store: dict[str, dict] = getattr(request.app.state, "verse_store", None)
    if verse_store is None:
        verse_store = load_verse_store()

    # Step 1: Check parse_verse_ref from router.py
    ref = parse_verse_ref(req.query, valid_ids)

    if ref:
        routed = True
        cited_verses = [ref]
        retrieved_verses = [verse_store.get(ref, {"verse_id": ref})]
    else:
        routed = False
        # Step 2: If not routed, run searcher.search(query, k=top_k)
        searcher: Searcher = getattr(request.app.state, "searcher", None)
        if searcher is None:
            raise HTTPException(
                status_code=503,
                detail="Searcher engine is not ready or failed to initialize."
            )
        hits = searcher.search(req.query, k=req.top_k)
        cited_verses = [h["verse_id"] for h in hits]
        retrieved_verses = [verse_store.get(vid, {"verse_id": vid, **h}) for vid, h in zip(cited_verses, hits)]

    # Step 3: Expand with conversational neighbors (e.g. 2.10, 2.11 for 2.9)
    context_verses = expand_verses_with_neighbors(retrieved_verses, verse_store)

    # Step 4: Build prompt and call generate_answer
    prompt = build_rag_prompt(req.query, context_verses)
    try:
        answer = generate_answer(prompt, system_prompt=SYSTEM_PROMPT)
    except Exception as e:
        logger.error("LLM generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Generation failed. Please try again later."
        )

    # Step 5: Return JSON response with query, routed, cited_verses, and answer
    return AskResponse(
        query=req.query,
        routed=routed,
        cited_verses=cited_verses,
        answer=answer,
    )
