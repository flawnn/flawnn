import logging
import os
import sys
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from PIL import Image

import config
import sections
import sources
from daylight import PARIS, paris_day
from readme import splice

log = logging.getLogger("update")


def build_paris(today: date) -> sections.Section:
    return sections.paris_section(paris_day(today))


def build_band(today: date) -> sections.Section:
    block, image = sections.pick_band(sources.fetch_arena(config.ARENA_CHANNEL), sources.get_image, today.isoformat())
    return sections.band_section(block, image)


def build_listening(today: date) -> sections.Section:
    albums = sources.fetch_top_albums(config.LASTFM_USER, os.environ["LASTFM_API_KEY"])[: config.ALBUM_COUNT]
    if not albums:
        raise LookupError("no albums with cover art this week")
    return sections.listening_section(albums, [sources.get_image(a.image_url) for a in albums])


def build_stars(today: date) -> sections.Section:
    pool = sources.fetch_stars(config.GITHUB_USER, os.environ.get("GITHUB_TOKEN"), config.EXCLUDE_STARS, config.STAR_POOL)
    return sections.stars_section(sections.sample_stars(pool, config.STAR_COUNT, today.isoformat()))


BUILDERS: dict[str, Callable[[date], sections.Section]] = {
    "paris": build_paris,
    "band": build_band,
    "listening": build_listening,
    "stars": build_stars,
}


def write_asset(path: Path, image: Image.Image) -> bool:
    """Save as a small palette PNG; skip when the pixels already match, so re-encoding never shows up as a diff."""
    palette = image.convert("RGBA").quantize(colors=4, method=Image.Quantize.FASTOCTREE)
    if path.exists():
        with Image.open(path) as current:
            if current.convert("RGBA").tobytes() == palette.convert("RGBA").tobytes():
                return False
    palette.save(path, optimize=True)
    return True


def remove_stale_tiles(prefix: str, keep: set[str]) -> None:
    for path in config.ASSETS.glob(f"{prefix}-*.png"):
        if path.name not in keep:
            path.unlink()


def run(today: date) -> list[str]:
    readme = config.README.read_text()
    failed = []
    for name, build in BUILDERS.items():
        try:
            section = build(today)
            readme = splice(readme, name, section.body)
        except Exception:
            log.exception("section '%s' failed; keeping its previous content", name)
            failed.append(name)
            continue
        changed = [n for n, img in section.assets.items() if write_asset(config.ASSETS / n, img)]
        if name == "listening":
            remove_stale_tiles("listening", set(section.assets))
        log.info("%s: ok, %d asset(s) rewritten", name, len(changed))
    config.README.write_text(readme)
    return failed


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(PARIS).date()
    failed = run(today)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
