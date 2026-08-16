import aiohttp
from utils.logger import get_logger

logger = get_logger("Updater")

class UpdateChecker:
    def __init__(self, current_version="1.2.0"):

        self.current_version = current_version

        self.update_url = "https://raw.githubusercontent.com/LuciarkLabs/LuciNet/refs/heads/main/version.json"

    async def check_for_updates(self):
\
\
\

        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(self.update_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        latest_version = data.get("version")
                        download_url = data.get("download_url")

                        if self._is_newer(latest_version, self.current_version):
                            return True, latest_version, download_url
                        return False, latest_version, None
                    else:
                        logger.error(
                            f"Failed to fetch update info. HTTP Status: {response.status}"
                        )
                        return False, None, None
        except Exception as e:
            logger.error(f"Update check error: {e}")
            return False, None, None

    def _is_newer(self, latest, current):
\
\

        if not latest or not current:
            return False
        try:

            latest_parts = tuple(map(int, latest.split(".")))
            current_parts = tuple(map(int, current.split(".")))
            return latest_parts > current_parts
        except ValueError:

            return latest > current
