import json
import urllib.request
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

LASTFM_PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"
USER_AGENT = "flawnn-readme (+https://github.com/flawnn/flawnn)"


@dataclass(frozen=True)
class Album:
    title: str
    artist: str
    url: str
    image_url: str


@dataclass(frozen=True)
class Block:
    id: int
    title: str
    image_url: str


@dataclass(frozen=True)
class Star:
    name: str
    url: str


def _get(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def get_json(url: str, headers: dict[str, str] | None = None):
    return json.loads(_get(url, headers))


def get_image(url: str) -> Image.Image:
    return Image.open(BytesIO(_get(url))).convert("RGB")


def parse_top_albums(payload: dict) -> list[Album]:
    albums = []
    for a in payload["topalbums"]["album"]:
        image = a["image"][-1]["#text"] if a.get("image") else ""
        if image and LASTFM_PLACEHOLDER not in image:
            albums.append(Album(a["name"], a["artist"]["name"], a["url"], image))
    return albums


def fetch_top_albums(user: str, api_key: str, limit: int = 10) -> list[Album]:
    url = (
        "https://ws.audioscrobbler.com/2.0/?method=user.gettopalbums"
        f"&user={user}&period=7day&limit={limit}&api_key={api_key}&format=json"
    )
    return parse_top_albums(get_json(url))


def parse_arena(payload: dict) -> list[Block]:
    return [
        Block(b["id"], b.get("title") or "", b["image"]["display"]["url"])
        for b in payload["contents"]
        if b.get("class") == "Image" and b.get("image")
    ]


def fetch_arena(slug: str) -> list[Block]:
    return parse_arena(get_json(f"https://api.are.na/v2/channels/{slug}?per=100"))


def parse_stars(payload: list, exclude: set[str] = frozenset()) -> list[Star]:
    return [Star(s["repo"]["full_name"], s["repo"]["html_url"]) for s in payload if s["repo"]["full_name"] not in exclude]


def fetch_stars(user: str, token: str | None = None, exclude: set[str] = frozenset(), count: int = 3) -> list[Star]:
    headers = {"Accept": "application/vnd.github.star+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = get_json(f"https://api.github.com/users/{user}/starred?per_page={count + len(exclude)}", headers)
    return parse_stars(payload, exclude)[:count]
