from types import SimpleNamespace

__all__ = ["DiContainer"]


class DiContainer(SimpleNamespace):
    def __setattr__(self, name: str, value) -> None:
        if hasattr(self, name):
            raise AttributeError(f"Cannot override existing attribute '{name}'")
        super().__setattr__(name, value)
