"""2026-11-19: serving embedding model comes from VYOM_EMBED_MODEL (default bge-base)."""

import os
from unittest.mock import patch

import pytest

from api.main import DEFAULT_EMBED_MODEL, embed_model_name


def test_default_is_bge_base():
    with patch.dict(os.environ, {}, clear=True):
        assert embed_model_name() == DEFAULT_EMBED_MODEL == "bge-base"


@pytest.mark.parametrize("value", ["bge-m3", "bge-base", " bge-m3 "])
def test_valid_values_are_used(value):
    with patch.dict(os.environ, {"VYOM_EMBED_MODEL": value}, clear=True):
        assert embed_model_name() == value.strip()


def test_unknown_value_falls_back_to_default():
    with patch.dict(os.environ, {"VYOM_EMBED_MODEL": "bge-large"}, clear=True):
        assert embed_model_name() == "bge-base"


# ---------------------------------------------------------------- script-based routing (Devanagari -> bge-m3)
from types import SimpleNamespace  # noqa: E402

from api.main import pick_searcher, script_routing_enabled  # noqa: E402


def test_devanagari_query_uses_multilingual_searcher():
    state = SimpleNamespace(searcher="base", searcher_multilingual="m3")
    assert pick_searcher(state, "आत्मा अमर है") == "m3"
    assert pick_searcher(state, "karma yoga kya hai") == "base"  # Hinglish in Latin script stays on default
    assert pick_searcher(state, "How do I control my mind?") == "base"


def test_without_multilingual_searcher_everything_uses_default():
    state = SimpleNamespace(searcher="base", searcher_multilingual=None)
    assert pick_searcher(state, "आत्मा अमर है") == "base"
    assert pick_searcher(SimpleNamespace(searcher="base"), "आत्मा") == "base"


def test_script_routing_switch():
    with patch.dict(os.environ, {}, clear=True):
        assert script_routing_enabled() is True
    with patch.dict(os.environ, {"VYOM_SCRIPT_ROUTING": "0"}, clear=True):
        assert script_routing_enabled() is False


def test_searchers_can_share_one_qdrant_client():
    from retrieval import search

    with patch.object(search, "load_model"), patch.object(search, "QdrantClient") as qc:
        owner = search.Searcher("bge-base")
        guest = search.Searcher("bge-m3", client=owner.client)
        assert qc.call_count == 1 and guest.client is owner.client
        guest.close()
        owner.client.close.assert_not_called()
        owner.close()
        owner.client.close.assert_called_once()
