"""Unit tests for document_content_tree — no DB or network required."""

import pytest
from app.services.standard_format import (
    make_node,
    build_document_content_tree,
    get_ancestors,
    build_summary_sections,
)


# ── make_node ─────────────────────────────────────────────────────────────────

def test_make_node_required_fields():
    node = make_node("paragraph", text="Hello")
    assert node["type"] == "paragraph"
    assert node["text"] == "Hello"
    assert "id" in node and node["id"]  # UUID assigned
    assert node["children"] == []


def test_make_node_heading_with_level():
    node = make_node("heading", text="Introduction", level=1, page=1)
    assert node["type"] == "heading"
    assert node["level"] == 1
    assert node["page"] == 1


def test_make_node_defaults_to_empty_children():
    node = make_node("paragraph")
    assert node["children"] == []


def test_make_node_unique_ids():
    a = make_node("paragraph")
    b = make_node("paragraph")
    assert a["id"] != b["id"]


# ── build_document_content_tree ─────────────────────────────────────────────────────

def test_build_document_content_tree_structure():
    node = make_node("paragraph", text="Body")
    doc = build_document_content_tree(
        title="Test Doc",
        nodes=[node],
        source="digital",
        page_count=2,
        author="Alice",
    )
    assert doc["version"] == "1.0"
    assert doc["meta"]["title"] == "Test Doc"
    assert doc["meta"]["author"] == "Alice"
    assert doc["meta"]["page_count"] == 2
    assert doc["meta"]["source"] == "digital"
    assert doc["nodes"] == [node]
    assert "created_at" in doc["meta"]


def test_build_document_content_tree_default_theme():
    doc = build_document_content_tree(title="T", nodes=[], source="digital", page_count=1)
    assert doc["theme"] == "default"


# ── get_ancestors ─────────────────────────────────────────────────────────────

def _make_doc():
    """
    Build a small document tree:
      H1 (id=h1)
        H2 (id=h2)
          paragraph (id=p1)
        paragraph (id=p2)
    """
    p1 = make_node("paragraph", text="Deep para")
    p1["id"] = "p1"
    h2 = make_node("heading", text="Section", level=2, children=[p1])
    h2["id"] = "h2"
    p2 = make_node("paragraph", text="Shallow para")
    p2["id"] = "p2"
    h1 = make_node("heading", text="Chapter", level=1, children=[h2, p2])
    h1["id"] = "h1"
    return build_document_content_tree(title="Doc", nodes=[h1], source="digital", page_count=1)


def test_get_ancestors_returns_heading_chain():
    doc = _make_doc()
    ancestors = get_ancestors(doc, ["p1"])
    # p1 is under h2 which is under h1 — both are headings
    assert ancestors == ["h1", "h2"]


def test_get_ancestors_shallow_node():
    doc = _make_doc()
    ancestors = get_ancestors(doc, ["p2"])
    # p2 is directly under h1
    assert ancestors == ["h1"]


def test_get_ancestors_top_level_heading_has_no_ancestors():
    doc = _make_doc()
    ancestors = get_ancestors(doc, ["h1"])
    assert ancestors == []


def test_get_ancestors_deduplicates_across_nodes():
    doc = _make_doc()
    # Both p1 and p2 share h1 as ancestor; h1 should appear once
    ancestors = get_ancestors(doc, ["p1", "p2"])
    assert ancestors.count("h1") == 1


def test_get_ancestors_unknown_node_id():
    doc = _make_doc()
    ancestors = get_ancestors(doc, ["nonexistent"])
    assert ancestors == []


# ── build_summary_sections ────────────────────────────────────────────────────

class _FakeHighlight:
    def __init__(self, id, node_ids, ancestor_node_ids, color="yellow", note=None):
        self.id = id
        self.node_ids = node_ids
        self.ancestor_node_ids = ancestor_node_ids
        self.color = color
        self.note = note


def test_build_summary_sections_basic():
    doc = _make_doc()
    hl = _FakeHighlight(id="hl1", node_ids=["p1"], ancestor_node_ids=["h1", "h2"])
    sections = build_summary_sections(doc, [hl])
    assert len(sections) == 1
    s = sections[0]
    assert s["highlight_id"] == "hl1"
    assert s["color"] == "yellow"
    assert len(s["nodes"]) == 1
    assert s["nodes"][0]["id"] == "p1"
    ancestor_ids = [a["node_id"] for a in s["ancestors"]]
    assert ancestor_ids == ["h1", "h2"]


def test_build_summary_sections_no_headings():
    doc = _make_doc()
    hl = _FakeHighlight(id="hl2", node_ids=["p1"], ancestor_node_ids=["h1", "h2"])
    sections = build_summary_sections(doc, [hl], include_headings=False)
    assert sections[0]["ancestors"] == []


def test_build_summary_sections_missing_node_id_skipped():
    doc = _make_doc()
    hl = _FakeHighlight(id="hl3", node_ids=["p1", "ghost"], ancestor_node_ids=[])
    sections = build_summary_sections(doc, [hl])
    node_ids = [n["id"] for n in sections[0]["nodes"]]
    assert "ghost" not in node_ids
    assert "p1" in node_ids
