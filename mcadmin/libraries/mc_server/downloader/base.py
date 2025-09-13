from abc import ABC, abstractmethod

__all__ = ["BaseMcServerDownloader"]


class BaseMcServerDownloader(ABC):
    @abstractmethod
    async def download(self) -> None:
        pass

    @abstractmethod
    async def get_jvm_args(self) -> list[str]:
        pass

    @abstractmethod
    def get_link_paths(self) -> list[str]:
        pass