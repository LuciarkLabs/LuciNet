
import aiosqlite
from typing import List, Union, Any
from domain.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from domain.subscription import Subscription
from repository.base_repo import BaseProxyRepository
from config import AppConfig
from utils.logger import get_logger

logger = get_logger("Database")

CURRENT_DB_VERSION = 10


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
        if current_version == 8:
            logger.info("Migrating to V9: Adding xray_raw_configs table...")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS xray_raw_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    raw_payload TEXT,
                    group_name TEXT DEFAULT 'Default',
                    source_type TEXT,
                    source_ref TEXT,
                    sub_id INTEGER,
                    created_at REAL
                )
            """)
            await db.execute("UPDATE schema_version SET version = 9")
            current_version = 9

        if current_version == 9:
            logger.info("Migrating to V10: Adding telemetry columns to xray_raw_configs table...")
            columns_to_add = [
                ("status", "TEXT DEFAULT 'Untested'"),
                ("ping", "REAL DEFAULT -1.0"),
                ("download_speed", "REAL DEFAULT 0.0"),
                ("country", "TEXT DEFAULT ''"),
                ("city", "TEXT DEFAULT ''"),
                ("isp", "TEXT DEFAULT ''"),
                ("real_ip", "TEXT DEFAULT ''"),
                ("last_scan", "REAL DEFAULT 0.0"),
                ("last_seen_alive", "REAL DEFAULT 0.0"),
                ("scan_count", "INTEGER DEFAULT 0"),
                ("error_message", "TEXT DEFAULT ''"),
            ]
            for col_name, col_def in columns_to_add:
                try:
                    await db.execute(f"ALTER TABLE xray_raw_configs ADD COLUMN {col_name} {col_def}")
                except Exception as e:
                    logger.debug(f"Column {col_name} already exists or error: {e}")
            await db.execute("UPDATE schema_version SET version = 10")
            current_version = 10

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
                            unique_hash=?, raw_url=?, remark=?, ping=?, download_speed=?, status=?, last_scan=?, last_seen_alive=?, scan_count=?,
                            country=?, city=?, isp=?, real_ip=?, path=?, host=?, pbk=?, sid=?, spx=?, group_name=?, sub_id=?
                        WHERE id=?
                        """,
                        (
                            proxy.unique_hash,
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

    async def save_many(self, proxies: List[Union[ProxyConfig, RawXrayConfig]]) -> int:
        if not proxies:
            return 0
        standard_proxies = [
            p for p in proxies if not isinstance(p, RawXrayConfig) and not getattr(p, "is_raw", False)
        ]
        raw_proxies = [
            p for p in proxies if isinstance(p, RawXrayConfig) or getattr(p, "is_raw", False)
        ]

        count = 0
        if standard_proxies:
            count += await self._save_many_standard(standard_proxies)
        if raw_proxies:
            count += await self._save_many_raw(raw_proxies)
        return count

    async def _save_many_standard(self, proxies: List[ProxyConfig]) -> int:
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
                            p.unique_hash,
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
                            unique_hash=?, raw_url=?, remark=?, ping=?, download_speed=?, status=?, last_scan=?, last_seen_alive=?, scan_count=?,
                            country=?, city=?, isp=?, real_ip=?, path=?, host=?, pbk=?, sid=?, spx=?, group_name=?, sub_id=?
                        WHERE id=?
                        """,
                        update_data,
                    )

                await db.commit()
            return len(proxies)
        except Exception as e:
            logger.error(f"DB SaveMany Standard Error: {e}")
            return 0

    async def _save_many_raw(self, raw_configs: List[RawXrayConfig]) -> int:
        if not raw_configs:
            return 0
        try:
            async with aiosqlite.connect(self.db_path) as db:
                groups = list(set(r.group_name for r in raw_configs if r.group_name))
                if groups:
                    await db.executemany(
                        "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                        [(g,) for g in groups],
                    )

                new_configs = [r for r in raw_configs if r.id is None]
                existing_configs = [r for r in raw_configs if r.id is not None]

                if new_configs:
                    for r in new_configs:
                        cursor = await db.execute(
                            """
                            INSERT INTO xray_raw_configs (
                                name, raw_payload, group_name, source_type, source_ref, sub_id, created_at,
                                status, ping, download_speed, country, city, isp, real_ip, last_scan, last_seen_alive, scan_count, error_message
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                r.name, r.raw_payload, r.group_name, r.source_type, r.source_ref,
                                r.sub_id, r.created_at, getattr(r, "status", "Untested"), getattr(r, "ping", -1.0),
                                getattr(r, "download_speed", 0.0), getattr(r, "country", ""), getattr(r, "city", ""),
                                getattr(r, "isp", ""), getattr(r, "real_ip", ""), getattr(r, "last_scan", 0.0),
                                getattr(r, "last_seen_alive", 0.0), getattr(r, "scan_count", 0), getattr(r, "error_message", "")
                            )
                        )
                        r.id = cursor.lastrowid

                if existing_configs:
                    update_data = [
                        (
                            r.name, r.raw_payload, r.group_name, r.source_type, r.source_ref, r.sub_id,
                            getattr(r, "status", "Untested"), getattr(r, "ping", -1.0), getattr(r, "download_speed", 0.0),
                            getattr(r, "country", ""), getattr(r, "city", ""), getattr(r, "isp", ""), getattr(r, "real_ip", ""),
                            getattr(r, "last_scan", 0.0), getattr(r, "last_seen_alive", 0.0), getattr(r, "scan_count", 0), getattr(r, "error_message", ""),
                            r.id
                        )
                        for r in existing_configs
                    ]
                    await db.executemany(
                        """
                        UPDATE xray_raw_configs SET 
                            name=?, raw_payload=?, group_name=?, source_type=?, source_ref=?, sub_id=?,
                            status=?, ping=?, download_speed=?, country=?, city=?, isp=?, real_ip=?,
                            last_scan=?, last_seen_alive=?, scan_count=?, error_message=?
                        WHERE id=?
                        """,
                        update_data,
                    )

                await db.commit()
            return len(raw_configs)
        except Exception as e:
            logger.error(f"DB SaveMany Raw Error: {e}")
            return 0

    async def get_all_unified(self) -> List[Union[ProxyConfig, RawXrayConfig]]:
        proxies = await self.get_all()
        raw_configs = await self.get_all_raw_configs()
        return list(proxies) + list(raw_configs)

    async def get_all(self) -> List[ProxyConfig]:
        proxies = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM proxies") as cursor:
                async for row in cursor:
                    p = ProxyConfig(
                        raw_url=row["raw_url"] or "",
                        protocol=row["protocol"] or "",
                        remark=row["remark"] or "",
                        server=row["server"] or "",
                        port=row["port"] or 0,
                    )
                    p.uuid_pwd = row["uuid_pwd"] or ""
                    p.sni = row["sni"] or ""
                    p.security = row["security"] or ""
                    p.network = row["network"] or ""
                    p.flow = row["flow"] or ""
                    p.alpn = row["alpn"] or ""
                    p.fingerprint = row["fingerprint"] or ""
                    p.path = row["path"] or ""
                    p.host = row["host"] or ""
                    p.pbk = row["pbk"] or ""
                    p.sid = row["sid"] or ""
                    p.spx = row["spx"] or ""
                    p.country = row["country"] or ""
                    p.city = row["city"] or ""
                    p.isp = row["isp"] or ""
                    p.ping = row["ping"] or -1.0
                    p.status = row["status"] or ""
                    p.first_seen = row["first_seen"] or 0.0
                    p.last_scan = row["last_scan"] or 0.0
                    p.last_seen_alive = row["last_seen_alive"] or 0.0
                    p.scan_count = row["scan_count"] or 0
                    p.id = row["id"]
                    p.group_name = row["group_name"] or "Default"

                    p.download_speed = (
                        row["download_speed"] if "download_speed" in row.keys() else 0.0
                    )
                    p.sub_id = row["sub_id"] if "sub_id" in row.keys() else None

                    p.real_ip = row["real_ip"] if "real_ip" in row.keys() else ""

                    if p.network == "xhttp" and p.raw_url and "?" in p.raw_url:
                        try:
                            from urllib.parse import parse_qs, unquote
                            q_str = p.raw_url.split("?", 1)[1].split("#", 1)[0]
                            if q_str:
                                qs = parse_qs(q_str)
                                if "mode" in qs and not p.mode:
                                    p.mode = qs["mode"][0]
                                if "extra" in qs and not p.extra:
                                    p.extra = unquote(qs["extra"][0])
                        except Exception:
                            pass

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
            raw_cursor = await db.execute(
                "UPDATE xray_raw_configs SET group_name = ? WHERE group_name = ?",
                (new_name, old_name),
            )
            await db.execute("DELETE FROM proxy_groups WHERE name = ?", (old_name,))
            await db.commit()
            return cursor.rowcount + raw_cursor.rowcount

    async def delete_group(self, group_name: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM proxies WHERE group_name = ?", (group_name,)
            )
            raw_cursor = await db.execute(
                "DELETE FROM xray_raw_configs WHERE group_name = ?", (group_name,)
            )
            await db.execute("DELETE FROM proxy_groups WHERE name = ?", (group_name,))
            await db.commit()
            return cursor.rowcount + raw_cursor.rowcount

    async def move_mixed_many(self, proxy_ids: List[int], raw_ids: List[int], new_group: str) -> int:
        if not proxy_ids and not raw_ids:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)", (new_group,)
                )
                if proxy_ids:
                    await db.executemany(
                        "UPDATE proxies SET group_name = ? WHERE id = ?",
                        [(new_group, pid) for pid in proxy_ids],
                    )
                if raw_ids:
                    await db.executemany(
                        "UPDATE xray_raw_configs SET group_name = ? WHERE id = ?",
                        [(new_group, rid) for rid in raw_ids],
                    )
                await db.commit()
                return len(proxy_ids) + len(raw_ids)
            except Exception as e:
                await db.rollback()
                raise e

    async def delete_mixed_many(self, proxy_ids: List[int], raw_ids: List[int]) -> int:
        if not proxy_ids and not raw_ids:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            try:
                if proxy_ids:
                    await db.executemany(
                        "DELETE FROM proxies WHERE id = ?", [(pid,) for pid in proxy_ids]
                    )
                if raw_ids:
                    await db.executemany(
                        "DELETE FROM xray_raw_configs WHERE id = ?", [(rid,) for rid in raw_ids]
                    )
                await db.commit()
                return len(proxy_ids) + len(raw_ids)
            except Exception as e:
                await db.rollback()
                raise e

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

    async def update_subscription_transactional(
        self, sub: Subscription, proxies: List[ProxyConfig] = None, raw_config: RawXrayConfig = None
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                if sub.id is None:
                    cursor = await db.execute(
                        "INSERT INTO subscriptions (name, url, last_update, auto_update) VALUES (?, ?, ?, ?)",
                        (sub.name, sub.url, sub.last_update, int(sub.auto_update)),
                    )
                    sub.id = cursor.lastrowid
                else:
                    await db.execute(
                        "UPDATE subscriptions SET name=?, url=?, last_update=?, auto_update=? WHERE id=?",
                        (sub.name, sub.url, sub.last_update, int(sub.auto_update), sub.id),
                    )

                await db.execute("DELETE FROM proxies WHERE sub_id = ?", (sub.id,))
                await db.execute("DELETE FROM xray_raw_configs WHERE sub_id = ?", (sub.id,))

                count = 0
                
                if proxies:
                    groups = list(set(p.group_name for p in proxies if p.group_name))
                    if groups:
                        await db.executemany(
                            "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                            [(g,) for g in groups],
                        )
                    
                    insert_data = []
                    for p in proxies:
                        p.sub_id = sub.id
                        insert_data.append((
                            p.unique_hash, p.raw_url, p.protocol, p.remark, p.server, p.port, p.uuid_pwd,
                            p.sni, p.security, p.network, p.flow, p.alpn, p.fingerprint, p.path, p.host,
                            p.pbk, p.sid, p.spx, p.country, p.city, p.isp, getattr(p, "real_ip", ""),
                            p.ping, getattr(p, "download_speed", 0.0), p.status, p.first_seen, p.last_scan,
                            p.last_seen_alive, p.scan_count, p.group_name, p.sub_id
                        ))
                        
                    if insert_data:
                        await db.executemany(
                            "INSERT INTO proxies (unique_hash, raw_url, protocol, remark, server, port, uuid_pwd, sni, security, network, flow, alpn, fingerprint, path, host, pbk, sid, spx, country, city, isp, real_ip, ping, download_speed, status, first_seen, last_scan, last_seen_alive, scan_count, group_name, sub_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            insert_data
                        )
                    count += len(insert_data)

                if raw_config:
                    raw_config.sub_id = sub.id
                    if raw_config.group_name:
                        await db.execute(
                            "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                            (raw_config.group_name,),
                        )
                    if getattr(raw_config, "id", None) is None:
                        cursor = await db.execute(
                            "INSERT INTO xray_raw_configs (name, raw_payload, group_name, source_type, source_ref, sub_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (raw_config.name, raw_config.raw_payload, raw_config.group_name, raw_config.source_type, raw_config.source_ref, raw_config.sub_id, raw_config.created_at)
                        )
                        raw_config.id = cursor.lastrowid
                    count += 1
                
                await db.commit()
                return count

            except Exception as e:
                await db.rollback()
                raise e

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
            await db.execute("DELETE FROM xray_raw_configs WHERE sub_id = ?", (sub_id,))
            await db.commit()
            return True

    async def delete_proxies_by_sub(self, sub_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM proxies WHERE sub_id = ?", (sub_id,))
            await db.commit()
            return cursor.rowcount


    async def save_raw_config(self, config: RawXrayConfig) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if config.group_name:
                await db.execute(
                    "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)",
                    (config.group_name,),
                )
            
            if config.id is None:
                cursor = await db.execute(
                    """
                    INSERT INTO xray_raw_configs (
                        name, raw_payload, group_name, source_type, source_ref, sub_id, created_at,
                        status, ping, download_speed, country, city, isp, real_ip, last_scan, last_seen_alive, scan_count, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        config.name, config.raw_payload, config.group_name, config.source_type, config.source_ref,
                        config.sub_id, config.created_at, getattr(config, "status", "Untested"), getattr(config, "ping", -1.0),
                        getattr(config, "download_speed", 0.0), getattr(config, "country", ""), getattr(config, "city", ""),
                        getattr(config, "isp", ""), getattr(config, "real_ip", ""), getattr(config, "last_scan", 0.0),
                        getattr(config, "last_seen_alive", 0.0), getattr(config, "scan_count", 0), getattr(config, "error_message", "")
                    )
                )
                config.id = cursor.lastrowid
            else:
                await db.execute(
                    """
                    UPDATE xray_raw_configs SET 
                        name=?, raw_payload=?, group_name=?, source_type=?, source_ref=?, sub_id=?,
                        status=?, ping=?, download_speed=?, country=?, city=?, isp=?, real_ip=?,
                        last_scan=?, last_seen_alive=?, scan_count=?, error_message=?
                    WHERE id=?
                    """,
                    (
                        config.name, config.raw_payload, config.group_name, config.source_type, config.source_ref, config.sub_id,
                        getattr(config, "status", "Untested"), getattr(config, "ping", -1.0), getattr(config, "download_speed", 0.0),
                        getattr(config, "country", ""), getattr(config, "city", ""), getattr(config, "isp", ""), getattr(config, "real_ip", ""),
                        getattr(config, "last_scan", 0.0), getattr(config, "last_seen_alive", 0.0), getattr(config, "scan_count", 0), getattr(config, "error_message", ""),
                        config.id
                    )
                )
            await db.commit()
            return config.id

    async def get_all_raw_configs(self) -> List[RawXrayConfig]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM xray_raw_configs")
            rows = await cursor.fetchall()
            configs = []
            for row in rows:
                col_keys = row.keys()
                cfg = RawXrayConfig(
                    id=row['id'],
                    name=row['name'] or "",
                    raw_payload=row['raw_payload'] or "",
                    group_name=row['group_name'] or "Default",
                    source_type=row['source_type'] or "import",
                    source_ref=row['source_ref'] or "",
                    sub_id=row['sub_id'],
                    created_at=row['created_at'] or 0.0,
                    status=row['status'] if 'status' in col_keys and row['status'] is not None else "Untested",
                    ping=row['ping'] if 'ping' in col_keys and row['ping'] is not None else -1.0,
                    download_speed=row['download_speed'] if 'download_speed' in col_keys and row['download_speed'] is not None else 0.0,
                    country=row['country'] if 'country' in col_keys and row['country'] is not None else "",
                    city=row['city'] if 'city' in col_keys and row['city'] is not None else "",
                    isp=row['isp'] if 'isp' in col_keys and row['isp'] is not None else "",
                    real_ip=row['real_ip'] if 'real_ip' in col_keys and row['real_ip'] is not None else "",
                    last_scan=row['last_scan'] if 'last_scan' in col_keys and row['last_scan'] is not None else 0.0,
                    last_seen_alive=row['last_seen_alive'] if 'last_seen_alive' in col_keys and row['last_seen_alive'] is not None else 0.0,
                    scan_count=row['scan_count'] if 'scan_count' in col_keys and row['scan_count'] is not None else 0,
                    error_message=row['error_message'] if 'error_message' in col_keys and row['error_message'] is not None else "",
                )
                configs.append(cfg)
            return configs

    async def delete_raw_config(self, config_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM xray_raw_configs WHERE id = ?", (config_id,))
            await db.commit()
            return True

    async def delete_raw_configs_by_sub(self, sub_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM xray_raw_configs WHERE sub_id = ?", (sub_id,))
            await db.commit()
            return cursor.rowcount

    async def delete_raw_many(self, raw_ids: List[int]) -> int:
        if not raw_ids:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                "DELETE FROM xray_raw_configs WHERE id = ?", [(rid,) for rid in raw_ids]
            )
            await db.commit()
            return len(raw_ids)

    async def update_raw_group_many(self, raw_ids: List[int], new_group: str) -> int:
        if not raw_ids:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO proxy_groups (name) VALUES (?)", (new_group,)
            )
            await db.executemany(
                "UPDATE xray_raw_configs SET group_name = ? WHERE id = ?",
                [(new_group, rid) for rid in raw_ids],
            )
            await db.commit()
            return len(raw_ids)
