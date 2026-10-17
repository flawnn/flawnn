from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Palette:
    surface: tuple[int, int, int]
    ink: tuple[int, int, int]


LIGHT = Palette(surface=(0xFF, 0xF4, 0xDF), ink=(0x28, 0x36, 0x18))
DARK = Palette(surface=(0x28, 0x36, 0x18), ink=(0xFF, 0xF4, 0xDF))
MODES = {"light": LIGHT, "dark": DARK}


def square(img: Image.Image, size: int) -> Image.Image:
    return ImageOps.fit(img.convert("RGB"), (size, size), Image.Resampling.LANCZOS)


def duotone(img: Image.Image) -> Image.Image:
    # Shadows stay olive in both modes; mapping them to cream would print a negative.
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    return ImageOps.colorize(gray, black=LIGHT.ink, white=LIGHT.surface)


def dither(img: Image.Image, p: Palette, scale: int = 2) -> Image.Image:
    w, h = img.size
    small = ImageOps.autocontrast(img.convert("L"), cutoff=2).resize((w // scale, h // scale))
    bits = small.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    bits = bits.resize((w, h), Image.Resampling.NEAREST).convert("L")
    return ImageOps.colorize(bits, black=p.ink, white=p.surface)


def dither_ink(img: Image.Image, ink: tuple[int, int, int], on_dark: bool, scale: int = 2) -> Image.Image:
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


def halftone(img: Image.Image, p: Palette, cell: int = 8) -> Image.Image:
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=2)
    w, h = gray.size
    out = Image.new("RGB", (w, h), p.surface)
    draw = ImageDraw.Draw(out)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            darkness = 1 - gray.getpixel((min(x + cell // 2, w - 1), min(y + cell // 2, h - 1))) / 255
            r = darkness * cell * 0.62
            cx, cy = x + cell / 2, y + cell / 2
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=p.ink)
    return out


def grain(img: Image.Image, strength: float = 0.08) -> Image.Image:
    noise = Image.effect_noise(img.size, 64).convert("RGB")
    return ImageChops.blend(img.convert("RGB"), ImageChops.overlay(img.convert("RGB"), noise), strength)


def polaroid(img: Image.Image, border: int = 18, chin: int = 56) -> Image.Image:
    w, h = img.size
    frame = Image.new("RGB", (w + border * 2, h + border + chin), LIGHT.surface)
    frame.paste(img, (border, border))
    ImageDraw.Draw(frame).rectangle((0, 0, *[s - 1 for s in frame.size]), outline=LIGHT.ink, width=2)
    return frame


def tilt(img: Image.Image, degrees: float, shadow: bool = True) -> Image.Image:
    rgba = img.convert("RGBA")
    rotated = rgba.rotate(degrees, expand=True, resample=Image.Resampling.BICUBIC)
    if not shadow:
        return rotated
    pad = 24
    canvas = Image.new("RGBA", (rotated.width + pad * 2, rotated.height + pad * 2), (0, 0, 0, 0))
    alpha = rotated.getchannel("A").point(lambda a: int(a * 0.28))
    shade = Image.new("RGBA", rotated.size, (0x14, 0x1A, 0x0C, 0))
    shade.putalpha(alpha)
    canvas.alpha_composite(shade.filter(ImageFilter.GaussianBlur(8)), (pad + 4, pad + 8))
    canvas.alpha_composite(rotated, (pad, pad))
    return canvas


BAYER_4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


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


def row(tiles: list[Image.Image], gap: int, pad: int = 0, background: RGB | None = None, rule: RGB | None = None) -> Image.Image:
    rule_space = gap if rule else 0
    h = max(t.height for t in tiles)
    w = sum(t.width for t in tiles) + gap * (len(tiles) - 1) + pad * 2
    out = Image.new("RGBA", (w, h + pad * 2 + rule_space), (*background, 255) if background else (0, 0, 0, 0))
    x = pad
    for t in tiles:
        out.alpha_composite(t.convert("RGBA"), (x, pad + h - t.height))
        x += t.width + gap
    if rule:
        y = pad + h + gap // 2
        ImageDraw.Draw(out).line((0, y, w, y), fill=(*rule, 255), width=4)
    return out


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
