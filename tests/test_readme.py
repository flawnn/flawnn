import pytest

from readme import MarkerError, splice

TEXT = "intro\n<!-- band:start -->\nold\nlines\n<!-- band:end -->\noutro\n"


def test_replaces_only_the_named_block():
    assert splice(TEXT, "band", "new") == "intro\n<!-- band:start -->\nnew\n<!-- band:end -->\noutro\n"


def test_multiline_body_and_idempotence():
    once = splice(TEXT, "band", "a\nb")
    assert splice(once, "band", "a\nb") == once


def test_body_with_regex_specials_is_literal():
    assert "¯\\\\\\_(ツ)\\_/¯ $1" in splice(TEXT, "band", "¯\\\\\\_(ツ)\\_/¯ $1")


def test_missing_marker_raises():
    with pytest.raises(MarkerError):
        splice(TEXT, "stars", "x")
