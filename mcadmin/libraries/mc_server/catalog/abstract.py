from abc import ABC, abstractmethod

__all__ = ["McServerSpecializedCatalog"]


class McServerSpecializedCatalog(ABC):
    @abstractmethod
    async def download(self) -> None:
        pass

    @abstractmethod
    async def get_jvm_args(self) -> list[str]:
        pass