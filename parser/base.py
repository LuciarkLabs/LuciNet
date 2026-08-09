from abc import ABC, abstractmethod
from domain.proxy import ProxyConfig
from parser.exceptions import ValidationError

class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw_url: str) -> ProxyConfig:

        pass

    def validate(self, config: ProxyConfig):

        if not config.server:
            raise ValidationError("آدرس سرور (Server/Host) یافت نشد.")

        try:
            port = int(config.port)
            if not (1 <= port <= 65535):
                raise ValueError
            config.port = port
        except (ValueError, TypeError):
            raise ValidationError(f"پورت نامعتبر است: {config.port}")

        if config.protocol in ("vless", "vmess", "trojan") and not config.uuid_pwd:
            raise ValidationError("UUID یا Password نمی‌تواند خالی باشد.")
