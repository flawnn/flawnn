import json
from pathlib import Path

from sources import LASTFM_PLACEHOLDER, parse_arena, parse_stars, parse_top_albums

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_top_albums_keep_rank_order_and_links():
    albums = parse_top_albums(load("lastfm_topalbums.json"))
    assert albums[0].title == "Memory Bomb" and albums[0].artist == "Kiefer"
    assert albums[0].url.startswith("https://www.last.fm/music/")
    assert albums[0].image_url.endswith(".jpg")


def test_top_albums_skip_missing_art():
    payload = load("lastfm_topalbums.json")
    first, second = payload["topalbums"]["album"][:2]
    first["image"][-1]["#text"] = ""
    second["image"][-1]["#text"] = f"https://lastfm.freetls.fastly.net/i/u/300x300/{LASTFM_PLACEHOLDER}.png"
    titles = [a.title for a in parse_top_albums(payload)]
    assert "Memory Bomb" not in titles and "The Last Flower To Bloom" not in titles


def test_arena_keeps_image_blocks_only():
    payload = load("arena_channel.json")
    payload["contents"].append({"id": 1, "class": "Text", "title": "note", "image": None})
    blocks = parse_arena(payload)
    assert len(blocks) == 3 and all(b.image_url.startswith("https://") for b in blocks)


def test_stars_respect_exclusions():
    payload = load("github_starred.json")
    assert [s.name for s in parse_stars(payload)] == ["vemonet/alt-tab-macos-free"]
    assert parse_stars(payload, exclude={"vemonet/alt-tab-macos-free"}) == []
