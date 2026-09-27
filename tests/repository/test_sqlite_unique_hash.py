import pytest
import aiosqlite
from domain.proxy import ProxyConfig
from repository.sqlite_repo import SQLiteProxyRepository
import os
import hashlib
from utils.url_normalizer import normalize_config_url

@pytest.mark.asyncio
async def test_sqlite_unique_hash_update(tmp_path):
    db_path = str(tmp_path / "test_unique_hash.db")
    repo = SQLiteProxyRepository(db_path=db_path)
    await repo.initialize()
    
    raw_a = "vless://abcd@1.1.1.1:443?security=tls#TestA"
    p = ProxyConfig(
        raw_url=raw_a,
        protocol="vless",
        remark="TestA",
        server="1.1.1.1",
        port=443
    )
    p.user_id = "abcd"
    await repo.save(p)
    
    proxies = await repo.get_all()
    assert len(proxies) == 1
    p_id = proxies[0].id
    p.id = p_id
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT unique_hash FROM proxies WHERE id=?", (p.id,)) as cursor:
            row = await cursor.fetchone()
            db_hash_a = row[0]
            
    expected_hash_a = hashlib.sha256(normalize_config_url(raw_a).encode('utf-8')).hexdigest()
    assert db_hash_a == expected_hash_a
    assert db_hash_a == p.unique_hash
    
    raw_b = "vless://efgh@2.2.2.2:443?security=tls#TestB"
    p.raw_url = raw_b
    await repo.save(p)
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT unique_hash FROM proxies WHERE id=?", (p.id,)) as cursor:
            row = await cursor.fetchone()
            db_hash_b = row[0]
            
    expected_hash_b = hashlib.sha256(normalize_config_url(raw_b).encode('utf-8')).hexdigest()
    assert db_hash_b == expected_hash_b
    assert db_hash_b == p.unique_hash
    
    raw_c = "vless://ijkl@3.3.3.3:443?security=tls#TestC"
    p.raw_url = raw_c
    await repo.save_many([p])
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT unique_hash FROM proxies WHERE id=?", (p.id,)) as cursor:
            row = await cursor.fetchone()
            db_hash_c = row[0]
            
    expected_hash_c = hashlib.sha256(normalize_config_url(raw_c).encode('utf-8')).hexdigest()
    assert db_hash_c == expected_hash_c
    assert db_hash_c == p.unique_hash

