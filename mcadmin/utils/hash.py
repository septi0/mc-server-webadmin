import hashlib
import base64

__all__ = ["hash_str"]


def hash_str(string: str, length: int = 8) -> str:
    digest = hashlib.sha1(string.encode()).digest()
    build = base64.b32encode(digest).decode("utf-8").rstrip("=")
    return build[:length]
