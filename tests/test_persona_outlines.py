"""Structural tests for per-persona outlines."""
from __future__ import annotations

import pytest

from src.crawler.persona_outlines import OutlineItem, outline_for
from src.rag.personas import ALL_PERSONA_IDS


@pytest.mark.parametrize("persona", list(ALL_PERSONA_IDS))
def test_outline_defined_for_every_persona(persona):
    items = outline_for(persona)
    assert len(items) >= 4, f"{persona} outline too thin"
    assert all(isinstance(it, OutlineItem) for it in items)
    # IDs must be unique within a persona.
    ids = [it.id for it in items]
    assert len(ids) == len(set(ids)), f"{persona} has duplicate section ids"


@pytest.mark.parametrize("persona", list(ALL_PERSONA_IDS))
def test_rag_items_have_a_query(persona):
    for it in outline_for(persona):
        if it.source == "rag":
            assert it.query, f"{persona}.{it.id} is source=rag but has no query"
        else:
            # Non-RAG items may optionally define a query, but most won't.
            pass


def test_unknown_persona_raises():
    with pytest.raises(KeyError):
        outline_for("ceo")  # type: ignore[arg-type]
