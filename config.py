import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:

    BASE_DIR: Path = Path(__file__).parent.resolve()
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "lucinet_archive.db"

    XRAY_DIR: Path = BASE_DIR / "xray_core"
    XRAY_EXECUTABLE: Path = XRAY_DIR / ("xray.exe" if os.name == "nt" else "xray")

    MAX_CONCURRENT_SCANS: int = 50
    SCAN_TIMEOUT_SECONDS: int = 15
    TEST_URL: str = "http://www.gstatic.com/generate_204"
    BASE_LOCAL_PORT: int = 10800

    BASE_LOCAL_PORT: int = 10800

    @classmethod
    def ensure_directories(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.XRAY_DIR.mkdir(exist_ok=True)

AppConfig.ensure_directories()
