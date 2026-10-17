import re


class MarkerError(LookupError):
    pass


def splice(text: str, name: str, body: str) -> str:
    """Replace everything between `<!-- name:start -->` and `<!-- name:end -->`."""
    pattern = re.compile(rf"(<!-- {re.escape(name)}:start -->\n).*?(\n<!-- {re.escape(name)}:end -->)", re.S)
    if not pattern.search(text):
        raise MarkerError(f"markers for '{name}' not found")
    return pattern.sub(lambda m: m[1] + body + m[2], text, count=1)
