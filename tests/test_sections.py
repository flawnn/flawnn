import re
from datetime import datetime

from PIL import Image

from daylight import PARIS, Day
from sections import band_section, has_tone, pick_band, sample_stars, listening_section, paris_section, stars_section
from sources import Album, Block, Star


def test_paris_line():
    day = Day(datetime(2026, 10, 17, 8, 13, tzinfo=PARIS), datetime(2026, 10, 17, 18, 57, tzinfo=PARIS), 2, "🌓")
    assert paris_section(day).body == "<samp>📍 paris · utc+2 · ☀ 08:13 → 18:57 · 🌓</samp>"


def test_stars_line_and_empty_state():
    stars = [Star("a/b", "https://github.com/a/b"), Star("c/d", "https://github.com/c/d")]
    assert stars_section(stars).body == "★ [a/b](https://github.com/a/b) · [c/d](https://github.com/c/d)"
    assert stars_section([]).body == "★ nothing new"


def test_listening_tiles_fill_the_row_and_link_out():
    albums = [Album(f'Al"bum {i}', "Artist", f"https://last.fm/{i}", "x") for i in range(4)]
    covers = [Image.new("RGB", (300, 300), (i * 60, 90, 120)) for i in range(4)]
    section = listening_section(albums, covers)
    widths = [float(w) for w in re.findall(r'width="([\d.]+)%"', section.body)]
    assert len(widths) == 4 and 99 < sum(widths) <= 100
    assert section.body.count('href="https://last.fm/') == 4
    assert "&quot;" in section.body and 'Al"bum' not in section.body
    assert sorted(section.assets) == sorted(f"listening-{i}-{m}.png" for i in range(4) for m in ("light", "dark"))


def test_band_skips_text_screenshots_and_is_stable_per_day():
    images = {
        "white": Image.new("RGB", (400, 300), (250, 250, 250)),
        "photo": Image.linear_gradient("L").resize((400, 300)).convert("RGB"),
    }
    blocks = [Block(1, "screenshot", "white"), Block(2, "photo", "photo")]
    for seed in ("2026-10-17", "2026-10-18", "2026-10-19"):
        assert pick_band(blocks, images.__getitem__, seed)[0].title == "photo"
    many = [Block(i, str(i), "photo") for i in range(20)]
    assert pick_band(many, images.__getitem__, "2026-10-17")[0] == pick_band(list(reversed(many)), images.__getitem__, "2026-10-17")[0]


def test_band_section_has_both_modes():
    section = band_section(Block(2, "photo", "u"), Image.effect_noise((800, 600), 80).convert("RGB"))
    assert set(section.assets) == {"band-light.png", "band-dark.png"}
    assert 'alt="photo' in section.body


def test_band_skips_text_on_black():
    assert not has_tone(Image.new("RGB", (400, 300), (5, 5, 5)))


def test_band_alt_ignores_filenames():
    section = band_section(Block(3, "b732ba1f.jpg", "u"), Image.linear_gradient("L").resize((800, 600)).convert("RGB"))
    assert "b732ba1f" not in section.body and "Today&#x27;s pick from the Are.na channel" in section.body


def test_star_sample_is_daily_stable_and_ordered():
    pool = [Star(f"u/r{i}", f"https://github.com/u/r{i}") for i in range(10)]
    today = sample_stars(pool, 3, "2026-10-17")
    assert today == sample_stars(pool, 3, "2026-10-17")
    assert len(today) == 3 and today == sorted(today, key=pool.index)
    assert sample_stars(pool[:2], 3, "2026-10-17") == pool[:2]
