import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from html import escape

from PIL import Image, ImageChops, ImageOps, ImageStat

import art
from config import BAND_SIZE, DITHER_SCALE, INK, ROW_GAP, ROW_WIDTH
from daylight import Day
from sources import Album, Block, Star

MODES = ("light", "dark")


@dataclass
class Section:
    body: str
    assets: dict[str, Image.Image] = field(default_factory=dict)


def picture(name: str, alt: str, width: str) -> str:
    alt = escape(alt)
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="./assets/{name}-dark.png">'
        f'<img src="./assets/{name}-light.png" alt="{alt}" width="{width}"></picture>'
    )


def ink(img: Image.Image, mode: str, alpha: Image.Image | None = None) -> Image.Image:
    out = art.dither_ink(img.convert("RGB"), INK[mode], on_dark=mode == "dark", scale=DITHER_SCALE)
    if alpha is not None:
        out.putalpha(ImageChops.multiply(out.getchannel("A"), alpha))
    return out


def paris_section(day: Day) -> Section:
    return Section(
        f"<samp>📍 paris · utc+{day.utc_offset} · ☀ {day.sunrise:%H:%M} → {day.sunset:%H:%M} · {day.moon}</samp>"
    )


def stars_section(stars: list[Star]) -> Section:
    if not stars:
        return Section("★ nothing new")
    return Section("★ " + " · ".join(f"[{s.name}]({s.url})" for s in stars))


def listening_section(albums: list[Album], covers: list[Image.Image]) -> Section:
    tiles, html = {}, []
    for i, (album, (tile, share)) in enumerate(zip(albums, art.split_row(covers, ROW_WIDTH, ROW_GAP))):
        for mode in MODES:
            tiles[f"listening-{i}-{mode}.png"] = ink(tile, mode, tile.getchannel("A"))
        label = f"{album.title} — {album.artist}"
        # Floor so the row never sums past 100% and wraps.
        width = f"{math.floor(share * 100) / 100}%"
        html.append(f'<a href="{escape(album.url)}" title="{escape(label)}">{picture(f"listening-{i}", label, width)}</a>')
    return Section("".join(html), tiles)


def has_tone(img: Image.Image) -> bool:
    """Photos, not text screenshots: enough spread and not mostly paper-white."""
    gray = ImageOps.grayscale(img.resize((160, 120)))
    white_share = sum(gray.histogram()[236:]) / (160 * 120)
    return ImageStat.Stat(gray).stddev[0] > 25 and white_share < 0.5


def pick_band(blocks: list[Block], load: Callable[[str], Image.Image], seed: str) -> tuple[Block, Image.Image]:
    """Seeded daily pick: same day, same image. Loads lazily until one isn't a screenshot."""
    order = sorted(blocks, key=lambda b: b.id)
    random.Random(seed).shuffle(order)
    for block in order:
        image = load(block.image_url)
        if has_tone(image):
            return block, image
    raise LookupError("no photo-like block in the channel")


def band_section(block: Block, image: Image.Image) -> Section:
    fitted = ImageOps.fit(image, BAND_SIZE, Image.Resampling.LANCZOS, centering=(0.5, 0.4))
    assets = {f"band-{mode}.png": art.dissolve(ink(fitted, mode), edge=0.42, block=6) for mode in MODES}
    alt = f"{block.title or 'Untitled'}, from the Are.na channel hard pics"
    return Section(picture("band", alt, "100%"), assets)
