import urllib.parse

__all__ = ["sanitize_url_path"]


def sanitize_url_path(url: str) -> str:
    if not url or not isinstance(url, str):
        return "/"

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme or parsed.netloc:
        return "/"

    path = parsed.path
    if not path.startswith("/"):
        path = "/" + path

    return path
