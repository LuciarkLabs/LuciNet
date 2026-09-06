import aiosqlite
from typing import List
from domain.proxy import ProxyConfig
from domain.subscription import Subscription
from repository.base_repo import BaseProxyRepository
from config import AppConfig
from utils.logger import get_logger

logger = get_logger("Database")

CURRENT_DB_VERSION = 8

class SQLiteProxyRepository(BaseProxyRepository):
    def __init__(self, db_path: str = str(AppConfig.DB_PATH)):
        self.db_path = db_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"""
            )
            await db.commit()
            async with db.execute("SELECT MAX(version) FROM schema_version") as cursor:
                row = await cursor.fetchone()
                db_version = row[0] if row and row[0] is not None else 0

            if db_version < CURRENT_DB_VERSION:
                await self._migrate(db, db_version)

    async def _migrate(self, db: aiosqlite.Connection, current_version: int):
        logger.info(f"Migrating database to version {CURRENT_DB_VERSION}...")

        if current_version == 0:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, unique_hash TEXT, raw_url TEXT,
                    protocol TEXT, remark TEXT, server TEXT, port INTEGER, uuid_pwd TEXT,
                    sni TEXT, security TEXT, network TEXT, flow TEXT, alpn TEXT, fingerprint TEXT,
                    path TEXT, host TEXT, pbk TEXT, sid TEXT, spx TEXT,
                    country TEXT, city TEXT, isp TEXT, ping REAL, download_speed REAL DEFAULT 0.0, status TEXT,
                    first_seen REAL, last_scan REAL, last_seen_alive REAL, scan_count INTEGER,
                    group_name TEXT DEFAULT 'Default'
                )
            """)
            await db.execute("INSERT INTO schema_version (version) VALUES (?)", (4,))
            current_version = 4

        if current_version == 1:
            await db.execute(
                "ALTER TABLE proxies ADD COLUMN group_name TEXT DEFAULT 'Default'"
            )
            await db.execute("UPDATE schema_version SET version = 2")
            current_version = 2

        if current_version == 2:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS proxies_v3 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, unique_hash TEXT, raw_url TEXT,
                    protocol TEXT, remark TEXT, server TEXT, port INTEGER, uuid_pwd TEXT,
                    sni TEXT, security TEXT, network TEXT, flow TEXT, alpn TEXT, fingerprint TEXT,
                    path TEXT, host TEXT, pbk TEXT, sid TEXT, spx TEXT,
                    country TEXT, city TEXT, isp TEXT, ping REAL, status TEXT,
                    first_seen REAL, last_scan REAL, last_seen_alive REAL, scan_count INTEGER,
                    group_name TEXT DEFAULT 'Default'
                )
            """)
            await db.execute("INSERT INTO proxies_v3 SELECT * FROM proxies")
            await db.execute("DROP TABLE proxies")
            await db.execute("ALTER TABLE proxies_v3 RENAME TO proxies")
            await db.execute("UPDATE schema_version SET version = 3")
            current_version = 3

        if current_version == 3:
            logger.info("Migrating to V4: Adding download_speed column...")
            await db.execute(
                "ALTER TABLE proxies ADD COLUMN download_speed REAL DEFAULT 0.0"
            )
            await db.execute("UPDATE schema_version SET version = 4")
            current_version = 4

        if current_version == 4:
            logger.info("Migrating to V5: Adding indexes for performance...")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_group_name ON proxies(group_name);"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_status ON proxies(status);"
            )
            await db.execute("UPDATE schema_version SET version = 5")
            current_version = 5

        if current_version == 5:
            logger.info("Migrating to V6: Adding Subscriptions support...")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    url TEXT,
                    last_update REAL,
                    auto_update INTEGER DEFAULT 0
                )
            """)
            await db.execute(
                "ALTER TABLE proxies ADD COLUMN sub_id INTEGER DEFAULT NULL"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_sub_id ON proxies(sub_id);"
            )

            await db.execute("UPDATE schema_version SET version = 6")
            current_version = 6

        if current_version == 6:
            logger.info("Migrating to V7: Adding dedicated proxy_groups table...")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS proxy_groups (
                    name TEXT PRIMARY KEY
                )
            """)
            await db.execute("""
                INSERT OR IGNORE INTO proxy_groups (name)
                SELECT DISTINCT group_name FROM proxies WHERE group_name IS NOT NULL AND group_name != ''
            """)
            await db.execute(
                "INSERT OR IGNORE INTO proxy_groups (name) VALUES ('Default')"
            )

            await db.execute("UPDATE schema_version SET version = 7")
            current_version = 7

        if current_version == 7:
            logger.info("Migrating to V8: Adding real_ip column...")
            await db.execute("ALTER TABLE proxies ADD COLUMN real_ip TEXT DEFAULT ''")
            await db.execute("UPDATE schema_version SET version = 8")
            current_version = 8

        await db.commit()

    async def save(self, proxy: ProxyConfig) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if proxy.group_name:
                    await db.execute(
                        "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                        (proxy.group_name,),
                    )

                if proxy.id is None:
                    await db.execute(
                        """
                        INSERT INTO proxies (
                            unique_hash, raw_url, protocol, remark, server, port, uuid_pwd, sni,
                            security, network, flow, alpn, fingerprint, path, host, pbk, sid, spx,
                            country, city, isp, real_ip, ping, download_speed, status, first_seen, last_scan, last_seen_alive, scan_count, group_name, sub_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            proxy.unique_hash,
                            proxy.raw_url,
                            proxy.protocol,
                            proxy.remark,
                            proxy.server,
                            proxy.port,
                            proxy.uuid_pwd,
                            proxy.sni,
                            proxy.security,
                            proxy.network,
                            proxy.flow,
                            proxy.alpn,
                            proxy.fingerprint,
                            proxy.path,
                            proxy.host,
                            proxy.pbk,
                            proxy.sid,
                            proxy.spx,
                            proxy.country,
                            proxy.city,
                            proxy.isp,
                            getattr(proxy, "real_ip", ""),
                            proxy.ping,
                            proxy.download_speed,
                            proxy.status,
                            proxy.first_seen,
                            proxy.last_scan,
                            proxy.last_seen_alive,
                            proxy.scan_count,
                            proxy.group_name,
                            getattr(proxy, "sub_id", None),
                        ),
                    )
                else:
                    await db.execute(
                        """
                        UPDATE proxies SET
                            raw_url=?, remark=?, ping=?, download_speed=?, status=?, last_scan=?, last_seen_alive=?, scan_count=?,
                            country=?, city=?, isp=?, real_ip=?, path=?, host=?, pbk=?, sid=?, spx=?, group_name=?, sub_id=?
                        WHERE id=?
                        """,
                        (
                            proxy.raw_url,
                            proxy.remark,
                            proxy.ping,
                            proxy.download_speed,
                            proxy.status,
                            proxy.last_scan,
                            proxy.last_seen_alive,
                            proxy.scan_count,
                            proxy.country,
                            proxy.city,
                            proxy.isp,
                            getattr(proxy, "real_ip", ""),
                            proxy.path,
                            proxy.host,
                            proxy.pbk,
                            proxy.sid,
                            proxy.spx,
                            proxy.group_name,
                            getattr(proxy, "sub_id", None),
                            proxy.id,
                        ),
                    )
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"DB Save Error: {e}")
            return False

    async def save_many(self, proxies: List[ProxyConfig]) -> int:
        if not proxies:
            return 0
        try:
            async with aiosqlite.connect(self.db_path) as db:
                groups = list(set(p.group_name for p in proxies if p.group_name))
                await db.executemany(
                    "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                    [(g,) for g in groups],
                )

                new_proxies = [p for p in proxies if p.id is None]
                existing_proxies = [p for p in proxies if p.id is not None]

                if new_proxies:
                    insert_data = [
                        (
                            p.unique_hash,
                            p.raw_url,
                            p.protocol,
                            p.remark,
                            p.server,
                            p.port,
                            p.uuid_pwd,
                            p.sni,
                            p.security,
                            p.network,
                            p.flow,
                            p.alpn,
                            p.fingerprint,
                            p.path,
                            p.host,
                            p.pbk,
                            p.sid,
                            p.spx,
                            p.country,
                            p.city,
                            p.isp,
                            getattr(p, "real_ip", ""),
                            p.ping,
                            getattr(p, "download_speed", 0.0),
                            p.status,
                            p.first_seen,
                            p.last_scan,
                            p.last_seen_alive,
                            p.scan_count,
                            p.group_name,
                            getattr(p, "sub_id", None),
                        )
                        for p in new_proxies
                    ]
                    await db.executemany(
                        """
                        INSERT INTO proxies (
                            unique_hash, raw_url, protocol, remark, server, port, uuid_pwd, sni,
                            security, network, flow, alpn, fingerprint, path, host, pbk, sid, spx,
                            country, city, isp, real_ip, ping, download_speed, status, first_seen, last_scan, last_seen_alive, scan_count, group_name, sub_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        insert_data,
                    )

                if existing_proxies:
                    update_data = [
                        (
                            p.raw_url,
                            p.remark,
                            p.ping,
                            getattr(p, "download_speed", 0.0),
                            p.status,
                            p.last_scan,
                            p.last_seen_alive,
                            p.scan_count,
                            p.country,
                            p.city,
                            p.isp,
                            getattr(p, "real_ip", ""),
                            p.path,
                            p.host,
                            p.pbk,
                            p.sid,
                            p.spx,
                            p.group_name,
                            getattr(p, "sub_id", None),
                            p.id,
                        )
                        for p in existing_proxies
                    ]
                    await db.executemany(
                        """
                        UPDATE proxies SET
                            raw_url=?, remark=?, ping=?, download_speed=?, status=?, last_scan=?, last_seen_alive=?, scan_count=?,
                            country=?, city=?, isp=?, real_ip=?, path=?, host=?, pbk=?, sid=?, spx=?, group_name=?, sub_id=?
                        WHERE id=?
                        """,
                        update_data,
                    )

                await db.commit()
            return len(proxies)
        except Exception as e:
            logger.error(f"DB SaveMany Error: {e}")
            return 0

    async def get_all(self) -> List[ProxyConfig]:
        proxies = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM proxies") as cursor:
                async for row in cursor:
                    p = ProxyConfig(
                        raw_url=row["raw_url"],
                        protocol=row["protocol"],
                        remark=row["remark"],
                        server=row["server"],
                        port=row["port"],
                        uuid_pwd=row["uuid_pwd"],
                        sni=row["sni"],
                        security=row["security"],
                        network=row["network"],
                        flow=row["flow"],
                        alpn=row["alpn"],
                        fingerprint=row["fingerprint"],
                        path=row["path"],
                        host=row["host"],
                        pbk=row["pbk"],
                        sid=row["sid"],
                        spx=row["spx"],
                        country=row["country"],
                        city=row["city"],
                        isp=row["isp"],
                        ping=row["ping"],
                        status=row["status"],
                        first_seen=row["first_seen"],
                        last_scan=row["last_scan"],
                        last_seen_alive=row["last_seen_alive"],
                        scan_count=row["scan_count"],
                        id=row["id"],
                        group_name=row["group_name"],
                    )

                    p.download_speed = (
                        row["download_speed"] if "download_speed" in row.keys() else 0.0
                    )
                    p.sub_id = row["sub_id"] if "sub_id" in row.keys() else None

                    p.real_ip = row["real_ip"] if "real_ip" in row.keys() else ""

                    proxies.append(p)
        return proxies

    async def delete(self, proxy_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
            await db.commit()
            return True

    async def add_group(self, group_name: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                    (group_name,),
                )
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"DB Add Group Error: {e}")
            return False

    async def get_groups(self) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT name FROM proxy_groups ORDER BY name"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows if row[0]]

    async def rename_group(self, old_name: str, new_name: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)", (new_name,)
            )
            cursor = await db.execute(
                "UPDATE proxies SET group_name = ? WHERE group_name = ?",
                (new_name, old_name),
            )
            await db.execute("DELETE FROM proxy_groups WHERE name = ?", (old_name,))
            await db.commit()
            return cursor.rowcount

    async def delete_group(self, group_name: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM proxies WHERE group_name = ?", (group_name,)
            )
            await db.execute("DELETE FROM proxy_groups WHERE name = ?", (group_name,))
            await db.commit()
            return cursor.rowcount

    async def delete_many(self, proxy_ids: List[int]) -> int:
        if not proxy_ids:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                "DELETE FROM proxies WHERE id = ?", [(pid,) for pid in proxy_ids]
            )
            await db.commit()
            return len(proxy_ids)

    async def update_group_many(self, proxy_ids: List[int], new_group: str) -> int:
        if not proxy_ids:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)", (new_group,)
            )
            await db.executemany(
                "UPDATE proxies SET group_name = ? WHERE id = ?",
                [(new_group, pid) for pid in proxy_ids],
            )
            await db.commit()
            return len(proxy_ids)

    async def get_subscriptions(self) -> List[Subscription]:
        subs = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM subscriptions") as cursor:
                async for row in cursor:
                    subs.append(
                        Subscription(
                            id=row["id"],
                            name=row["name"],
                            url=row["url"],
                            last_update=row["last_update"],
                            auto_update=bool(row["auto_update"]),
                        )
                    )
        return subs

    async def save_subscription(self, sub: Subscription) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if sub.id is None:
                cursor = await db.execute(
                    "INSERT INTO subscriptions (name, url, last_update, auto_update) VALUES (?, ?, ?, ?)",
                    (sub.name, sub.url, sub.last_update, int(sub.auto_update)),
                )
                sub_id = cursor.lastrowid
            else:
                await db.execute(
                    "UPDATE subscriptions SET name=?, url=?, last_update=?, auto_update=? WHERE id=?",
                    (sub.name, sub.url, sub.last_update, int(sub.auto_update), sub.id),
                )
                sub_id = sub.id
            await db.commit()
            return sub_id

    async def delete_subscription(self, sub_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
            await db.execute("DELETE FROM proxies WHERE sub_id = ?", (sub_id,))
            await db.commit()
            return True

    async def delete_proxies_by_sub(self, sub_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM proxies WHERE sub_id = ?", (sub_id,))
            await db.commit()
            return cursor.rowcount
