__all__ = ["str_to_bool"]


def str_to_bool(data: str) -> bool:
    """
    Convert a string to a boolean value.
    """
    if data.lower() in ("true", "1", "yes"):
        return True
    elif data.lower() in ("false", "0", "no"):
        return False
    raise ValueError(f"Invalid boolean string: {data}")
