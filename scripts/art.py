from PIL import Image, ImageChops, ImageOps

RGB = tuple[int, int, int]

BAYER_4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def dither_ink(img: Image.Image, ink: RGB, on_dark: bool, scale: int = 2) -> Image.Image:
    """1-bit dither where only the ink dots are opaque, so the page shows through.

    Ink marks whatever contrasts with the page: shadows on a light page, highlights on a dark one.
    """
    w, h = img.size
    small = ImageOps.autocontrast(img.convert("L"), cutoff=2).resize((w // scale, h // scale))
    bits = small.convert("1", dither=Image.Dither.FLOYDSTEINBERG).resize((w, h), Image.Resampling.NEAREST)
    out = Image.new("RGBA", (w, h), (*ink, 255))
    mask = bits.convert("L")
    out.putalpha(mask if on_dark else ImageOps.invert(mask))
    return out


def dissolve(img: Image.Image, edge: float = 0.3, block: int = 4) -> Image.Image:
    """Ordered-dither the top and bottom edges into transparency."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    ramp = max(1, int(h * edge))
    mask = Image.new("L", (w // block + 1, h // block + 1), 255)
    px = mask.load()
    for by in range(mask.height):
        y = by * block
        coverage = min(1.0, min(y, h - 1 - y) / ramp)
        for bx in range(mask.width):
            threshold = (BAYER_4[by % 4][bx % 4] + 0.5) / 16
            px[bx, by] = 255 if coverage > threshold else 0
    edge_mask = mask.resize((mask.width * block, mask.height * block), Image.Resampling.NEAREST).crop((0, 0, w, h))
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), edge_mask))
    return rgba


def fill_row(tiles: list[Image.Image], width: int, gap: int) -> Image.Image:
    """Scale tiles to one shared height so the row spans exactly `width`, edge to edge."""
    ratios = [t.width / t.height for t in tiles]
    height = round((width - gap * (len(tiles) - 1)) / sum(ratios))
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    x = 0
    for i, (t, r) in enumerate(zip(tiles, ratios)):
        w = width - x if i == len(tiles) - 1 else round(height * r)
        out.alpha_composite(t.convert("RGBA").resize((w, height), Image.Resampling.LANCZOS), (x, 0))
        x += w + gap
    return out


def split_row(tiles: list[Image.Image], width: int, gap: int) -> list[tuple[Image.Image, float]]:
    """fill_row cut into per-tile images (gap baked in as transparent right margin) with each one's share of the row in %."""
    row = fill_row(tiles, width, gap)
    ratios = [t.width / t.height for t in tiles]
    parts, x = [], 0
    for i, r in enumerate(ratios):
        last = i == len(tiles) - 1
        w = width - x if last else round(row.height * r) + gap
        parts.append((row.crop((x, 0, x + w, row.height)), w / width * 100))
        x += w
    return parts
