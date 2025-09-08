import secrets
import string

__all__ = ["random_password"]


def random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
