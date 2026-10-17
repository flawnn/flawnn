from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
ASSETS = ROOT / "assets"

LASTFM_USER = "Flawn_"
ARENA_CHANNEL = "hard-pics-g2xhskd63oq"
GITHUB_USER = "flawnn"
EXCLUDE_STARS: set[str] = set()

ALBUM_COUNT = 4
STAR_COUNT = 3
STAR_POOL = 10

INK = {"light": (0x1F, 0x23, 0x28), "dark": (0xE6, 0xED, 0xF3)}
ROW_WIDTH, ROW_GAP = 1600, 24
BAND_SIZE = (1600, 440)
DITHER_SCALE = 3
