
from abc import ABC, abstractmethod
from typing import List, Any, Union
from domain.proxy import ProxyConfig
from domain.subscription import Subscription


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
    async def get_all_unified(self) -> List[Any]:
        pass

    @abstractmethod
    async def delete(self, proxy_id: int) -> bool:
        pass

    @abstractmethod
    async def get_groups(self) -> List[str]:
        pass

    @abstractmethod
    async def add_group(self, group_name: str) -> bool:
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

    @abstractmethod
    async def move_mixed_many(self, proxy_ids: List[int], raw_ids: List[int], new_group: str) -> int:
        pass

    @abstractmethod
    async def delete_mixed_many(self, proxy_ids: List[int], raw_ids: List[int]) -> int:
        pass


    @abstractmethod
    async def get_subscriptions(self) -> List[Subscription]:
        pass

    @abstractmethod
    async def save_subscription(self, sub: Subscription) -> int:
        pass

    @abstractmethod
    async def update_subscription_transactional(self, sub: Subscription, proxies: List[ProxyConfig] = None, raw_config: "RawXrayConfig" = None) -> int:
        pass


    @abstractmethod
    async def delete_subscription(self, sub_id: int) -> bool:
        pass

    @abstractmethod
    async def delete_proxies_by_sub(self, sub_id: int) -> int:
        pass
