from ostraca_cli.frontmatter import extract_frontmatter


def test_valid_frontmatter():
    raw = """---
title: "A \\"Special\\" Note"
para: Area
tags: [python, sqlite, cli]
---
# Content starts here
Body of the note."""
    metadata, body = extract_frontmatter(raw)
    assert metadata["title"] == 'A "Special" Note'
    assert metadata["para"] == "Area"
    assert metadata["tags"] == ["python", "sqlite", "cli"]
    assert body.strip() == "# Content starts here\nBody of the note."


def test_comma_separated_tags():
    raw = """---
title: Simple Note
para: Project
tags: python, sqlite
---
Body"""
    metadata, body = extract_frontmatter(raw)
    assert metadata["title"] == "Simple Note"
    assert metadata["para"] == "Project"
    assert metadata["tags"] == ["python", "sqlite"]
    assert body.strip() == "Body"


def test_no_frontmatter():
    raw = "# No Frontmatter here\nSome text."
    metadata, body = extract_frontmatter(raw)
    assert not metadata
    assert body == raw


def test_invalid_frontmatter():
    raw = """---
title A Note
para Project
---
Body"""
    metadata, body = extract_frontmatter(raw)
    assert not metadata
    assert body.strip() == "Body"


def test_empty_content():
    metadata, body = extract_frontmatter("")
    assert not metadata
    assert body == ""
