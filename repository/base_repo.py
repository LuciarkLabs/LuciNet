from abc import ABC, abstractmethod
from typing import List
from domain.proxy import ProxyConfig

class BaseProxyRepository(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def save(self, proxy: ProxyConfig) -> bool:
        pass

    @abstractmethod
    async def save_many(self, proxies: List[ProxyConfig]) -> int:
        pass

    @abstractmethod
    async def get_all(self) -> List[ProxyConfig]:
        pass

    @abstractmethod
    async def delete(self, proxy_id: int) -> bool:
        pass

    @abstractmethod
    async def get_groups(self) -> List[str]:
        pass

    @abstractmethod
    async def rename_group(self, old_name: str, new_name: str) -> int:
        pass

    @abstractmethod
    async def delete_group(self, group_name: str) -> int:
        pass

    @abstractmethod
    async def delete_many(self, proxy_ids: List[int]) -> int:
        pass

    @abstractmethod
    async def update_group_many(self, proxy_ids: List[int], new_group: str) -> int:
        pass
