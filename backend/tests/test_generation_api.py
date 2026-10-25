"""Tests for Generation (llm/client.py, retrieval/prompt.py) and Serving (api/main.py)."""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import (
    app,
    AskRequest,
    AskResponse,
    load_verse_store,
    get_verse_neighbors,
    expand_verses_with_neighbors,
)
from llm.client import generate_answer, _call_gemini, _call_groq, _call_ollama
from retrieval.prompt import SYSTEM_PROMPT, build_rag_prompt


# ============================================================================
# LLM Client Tests
# ============================================================================

def test_prompt_system_prompt_content():
    """Verify SYSTEM_PROMPT contains required grounding and citation instructions."""
    assert "VYOM" in SYSTEM_PROMPT
    assert "Bhagavad Gita" in SYSTEM_PROMPT
    assert "cite" in SYSTEM_PROMPT.lower()
    assert "ground" in SYSTEM_PROMPT.lower()


def test_build_rag_prompt_formatting():
    """Verify build_rag_prompt correctly formats verses and query."""
    sample_verses = [
        {
            "verse_id": "2.47",
            "sanskrit": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन",
            "transliteration": "karmaṇy-evādhikāras te mā phaleṣhu kadāchana",
            "translations": {
                "english": [{"author": "Swami Sivananda", "text": "Thy right is to work only, but never to its fruits."}]
            },
            "commentaries": [
                {"author": "Swami Sivananda", "language": "english", "text": "Perform duty without expectation of fruits."}
            ]
        }
    ]
    prompt = build_rag_prompt("What is Nishkama Karma?", sample_verses)
    assert "=== Bhagavad Gita Verse 2.47 ===" in prompt
    assert "कर्मण्येवाधिकारस्ते" in prompt
    assert "Swami Sivananda" in prompt
    assert "What is Nishkama Karma?" in prompt


def test_generate_answer_gemini_success():
    """Verify generate_answer calls Gemini when GEMINI_API_KEY is available."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}, clear=True):
        with patch("llm.client._call_gemini", return_value="Gemini generated response") as mock_gemini:
            ans = generate_answer("Test question", "Test system prompt")
            assert ans == "Gemini generated response"
            mock_gemini.assert_called_once_with("Test question", "Test system prompt", "test-gemini-key")


def test_generate_answer_fallback_to_groq():
    """Verify generate_answer falls back to Groq when Gemini fails."""
    env = {"GEMINI_API_KEY": "bad-key", "GROQ_API_KEY": "good-groq-key"}
    with patch.dict(os.environ, env, clear=True):
        with patch("llm.client._call_gemini", side_effect=Exception("Gemini quota exceeded")):
            with patch("llm.client._call_groq", return_value="Groq generated response") as mock_groq:
                ans = generate_answer("Test question", "Test system prompt")
                assert ans == "Groq generated response"
                mock_groq.assert_called_once_with("Test question", "Test system prompt", "good-groq-key")


def test_generate_answer_fallback_to_ollama():
    """Verify generate_answer falls back to Ollama when Gemini and Groq both fail or are unset."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("llm.client._call_ollama", return_value="Ollama local response") as mock_ollama:
            ans = generate_answer("Test question", "Test system prompt")
            assert ans == "Ollama local response"
            mock_ollama.assert_called_once_with("Test question", "Test system prompt")


def test_call_gemini_sdk():
    """Verify _call_gemini configures genai and calls GenerativeModel."""
    with patch("llm.client.genai.configure") as mock_conf, patch("llm.client.genai.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini SDK output"
        mock_instance.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_instance

        res = _call_gemini("What is dharma?", "Be precise.", "fake-api-key")
        assert res == "Gemini SDK output"
        mock_conf.assert_called_once_with(api_key="fake-api-key")
        mock_model_cls.assert_called_once_with(model_name="gemini-1.5-flash", system_instruction="Be precise.")
        mock_instance.generate_content.assert_called_once_with("What is dharma?")


def test_call_groq_sdk():
    """Verify _call_groq initializes Groq client and calls chat.completions.create."""
    with patch("llm.client.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Groq SDK output"
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_groq_cls.return_value = mock_client

        res = _call_groq("What is yoga?", "Be wise.", "fake-groq-key")
        assert res == "Groq SDK output"
        mock_groq_cls.assert_called_once_with(api_key="fake-groq-key")
        mock_client.chat.completions.create.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Be wise."},
                {"role": "user", "content": "What is yoga?"},
            ],
            temperature=0.3,
        )


def test_generate_answer_all_fail():
    """Verify RuntimeError is raised when all providers fail."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("llm.client._call_ollama", side_effect=Exception("Connection refused")):
            with pytest.raises(RuntimeError, match="All LLM generation providers in fallback chain failed"):
                generate_answer("Test question", "Test system prompt")


# ============================================================================
# API Endpoint Tests
# ============================================================================

@pytest.fixture
def mock_app_state():
    """Configure FastAPI app state with mock searcher and valid verse IDs."""
    mock_searcher = MagicMock()
    mock_searcher.search.return_value = [
        {"verse_id": "6.26", "score": 0.89, "chunks": [("6.26:v", 0.89)]},
        {"verse_id": "6.35", "score": 0.84, "chunks": [("6.35:v", 0.84)]},
        {"verse_id": "6.34", "score": 0.79, "chunks": [("6.34:v", 0.79)]},
    ]

    app.state.searcher = mock_searcher
    app.state.valid_ids = {"1.1", "2.47", "4.7", "6.26", "6.34", "6.35", "9.22", "18.66"}
    app.state.verse_store = {
        "4.7": {
            "verse_id": "4.7",
            "sanskrit": "यदा यदा हि धर्मस्य ग्लानिर्भवति भारत",
            "translations": {"english": [{"author": "Swami Sivananda", "text": "Whenever righteousness wanes, O Bharata..."}]}
        },
        "6.26": {
            "verse_id": "6.26",
            "sanskrit": "ततो नियम्यैतदात्मन्येव वशं नयेत्",
            "translations": {"english": [{"author": "Swami Sivananda", "text": "Restrain the restless wandering mind..."}]}
        }
    }
    yield app.state


def test_health_endpoint(mock_app_state):
    """Test /api/health endpoint."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["searcher_ready"] is True


def test_ask_endpoint_routed(mock_app_state):
    """Test /api/ask with explicit verse reference query (routed = True)."""
    client = TestClient(app)
    with patch("api.main.generate_answer", return_value="Lord Krishna appears in every age to protect dharma.") as mock_llm:
        response = client.post("/api/ask", json={"query": "Show me chapter 4 verse 7", "top_k": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Show me chapter 4 verse 7"
        assert data["routed"] is True
        assert data["cited_verses"] == ["4.7"]
        assert "Lord Krishna" in data["answer"]
        mock_llm.assert_called_once()
        # Ensure searcher was NOT called for routed query
        app.state.searcher.search.assert_not_called()


def test_ask_endpoint_non_routed(mock_app_state):
    """Test /api/ask with conceptual query (routed = False)."""
    client = TestClient(app)
    with patch("api.main.generate_answer", return_value="Control the mind with practice and detachment.") as mock_llm:
        response = client.post("/api/ask", json={"query": "How to control a restless mind?", "top_k": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "How to control a restless mind?"
        assert data["routed"] is False
        assert data["cited_verses"] == ["6.26", "6.35", "6.34"]
        assert "practice and detachment" in data["answer"]
        app.state.searcher.search.assert_called_once_with("How to control a restless mind?", k=3)
        mock_llm.assert_called_once()


def test_ask_endpoint_validation():
    """Test request body validation."""
    client = TestClient(app)
    # Empty query should fail
    response = client.post("/api/ask", json={"query": "", "top_k": 3})
    assert response.status_code == 422

    # Invalid top_k (< 1) should fail
    response = client.post("/api/ask", json={"query": "karma", "top_k": 0})
    assert response.status_code == 422


def test_ask_request_default_top_k():
    """Verify default top_k is 5."""
    req = AskRequest(query="test query")
    assert req.top_k == 5


def test_neighbor_expansion_logic():
    """Verify neighbor lookup helper fetches +1 and +2 forward neighbors."""
    mock_store = {
        "2.9": {"verse_id": "2.9", "text": "Arjuna said: I will not fight."},
        "2.10": {"verse_id": "2.10", "text": "Sanjaya said: Krishna smiled."},
        "2.11": {"verse_id": "2.11", "text": "Krishna spoke words of wisdom."},
    }
    neighbors = get_verse_neighbors("2.9", mock_store, offsets=(1, 2))
    assert [n["verse_id"] for n in neighbors] == ["2.10", "2.11"]
    assert all(n.get("is_neighbor") is True for n in neighbors)
    assert all(n.get("neighbor_of") == "2.9" for n in neighbors)

    expanded = expand_verses_with_neighbors([mock_store["2.9"]], mock_store)
    assert [v["verse_id"] for v in expanded] == ["2.9", "2.10", "2.11"]


def test_cited_verses_subset_of_expanded_verses(mock_app_state):
    """Verify cited verses in the response are a strict subset of the expanded context verses."""
    # Add 2.9, 2.10, 2.11 to mock_app_state
    mock_app_state.valid_ids.update({"2.9", "2.10", "2.11"})
    mock_app_state.verse_store.update({
        "2.9": {"verse_id": "2.9", "sanskrit": "न योत्स्य इति गोविन्दम्"},
        "2.10": {"verse_id": "2.10", "sanskrit": "तमुवाच हृषीकेशः प्रहसन्निव भारत"},
        "2.11": {"verse_id": "2.11", "sanskrit": "अशोच्यानन्वशोचस्त्वं प्रज्ञावादांश्च भाषसे"},
    })
    mock_app_state.searcher.search.return_value = [
        {"verse_id": "2.9", "score": 0.95, "chunks": [("2.9:v", 0.95)]}
    ]

    captured_prompt = None

    def fake_generate(prompt, system_prompt=""):
        nonlocal captured_prompt
        captured_prompt = prompt
        return "Krishna comforts Arjuna who resolved not to fight."

    client = TestClient(app)
    with patch("api.main.generate_answer", side_effect=fake_generate):
        response = client.post("/api/ask", json={"query": "I will not fight"})
        assert response.status_code == 200
        data = response.json()

        cited = data["cited_verses"]
        assert "2.9" in cited

        # Verify neighbor expansion included 2.10 and 2.11 in prompt
        assert "=== Bhagavad Gita Verse 2.9 ===" in captured_prompt
        assert "=== Bhagavad Gita Verse 2.10 (Conversational Context following BG 2.9) ===" in captured_prompt
        assert "=== Bhagavad Gita Verse 2.11 (Conversational Context following BG 2.9) ===" in captured_prompt

        # Cited verses must be a subset of the retrieved & expanded verses
        all_expanded_ids = {"2.9", "2.10", "2.11"}
        assert set(cited).issubset(all_expanded_ids)


def test_ask_endpoint_error_masking(mock_app_state):
    """Verify LLM failure returns a generic 502 error and never leaks internal keys/URLs."""
    client = TestClient(app)
    sensitive_error = (
        "404 models/gemini-1.5-flash?key=placeholder_gemini_test_key&leak=true; "
        "Groq failed: auth=placeholder_groq_test_token at https://api.groq.com/v1"
    )

    with patch("api.main.generate_answer", side_effect=RuntimeError(sensitive_error)):
        response = client.post("/api/ask", json={"query": "Tell me about dharma"})
        assert response.status_code == 502
        body = response.json()

        # Must return the exact generic detail message
        assert body == {"detail": "Generation failed. Please try again later."}

        # Must NOT leak secrets or internal provider URLs in response
        assert "placeholder_gemini_test_key" not in response.text
        assert "placeholder_groq_test_token" not in response.text
        assert "https://api.groq.com" not in response.text
        assert "gemini-1.5-flash" not in response.text

