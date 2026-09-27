import pytest
import os
from domain.models.raw_config import RawXrayConfig
from repository.sqlite_repo import SQLiteProxyRepository

@pytest.mark.asyncio
async def test_sqlite_raw_config_crud(tmp_path):
    db_path = str(tmp_path / "test.db")
    repo = SQLiteProxyRepository(db_path=db_path)
    await repo.initialize()
    
    cfg = RawXrayConfig(
        name="test cfg",
        raw_payload='{"inbounds": []}',
        group_name="TestGroup",
        source_type="file",
        source_ref="/path/to/file.json",
        sub_id=99
    )
    new_id = await repo.save_raw_config(cfg)
    assert new_id is not None
    
    configs = await repo.get_all_raw_configs()
    assert len(configs) == 1
    c = configs[0]
    assert c.id == new_id
    assert c.name == "test cfg"
    assert c.raw_payload == '{"inbounds": []}'
    assert c.source_type == "file"
    assert c.sub_id == 99
    
    deleted_count = await repo.delete_raw_configs_by_sub(99)
    assert deleted_count == 1
    
    configs = await repo.get_all_raw_configs()
    assert len(configs) == 0
