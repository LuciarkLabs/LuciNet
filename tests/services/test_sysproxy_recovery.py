import sys
import os
import json
import time
import pytest
from config import AppConfig
from pathlib import Path
from unittest.mock import patch, MagicMock
from services.core_manager import CoreManager
from PySide6.QtCore import QProcess

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows specific registry tests")

@pytest.fixture
def clean_backup():
    backup_path = AppConfig.DATA_DIR / "sysproxy_backup.json"
    if backup_path.exists():
        try:
            backup_path.unlink()
        except Exception:
            pass
    data_dir = AppConfig.DATA_DIR
    if data_dir.exists():
        for p in data_dir.glob("sysproxy_backup.*"):
            try:
                p.unlink()
            except Exception:
                pass
    yield backup_path
    if backup_path.exists():
        try:
            backup_path.unlink()
        except Exception:
            pass
    if data_dir.exists():
        for p in data_dir.glob("sysproxy_backup.*"):
            try:
                p.unlink()
            except Exception:
                pass

@pytest.fixture
def mock_winreg():
    with patch("winreg.OpenKey") as m_open, \
         patch("winreg.QueryValueEx") as m_query, \
         patch("winreg.SetValueEx") as m_set, \
         patch("winreg.DeleteValue") as m_del, \
         patch("winreg.CloseKey") as m_close:
         
        state = {
            "ProxyEnable": (4, 1),
            "ProxyServer": (1, "1.2.3.4:8080"),
            "ProxyOverride": (1, "<local>")
        }
        
        def mock_query_func(key, name):
            if name in state:
                t, val = state[name]
                return [val, t]
            raise FileNotFoundError(f"Key {name} not found")
            
        def mock_set_func(key, name, reserved, reg_type, value):
            state[name] = (reg_type, value)
            
        def mock_del_func(key, name):
            if name in state:
                del state[name]
            else:
                raise FileNotFoundError(f"Key {name} not found")
                
        m_query.side_effect = mock_query_func
        m_set.side_effect = mock_set_func
        m_del.side_effect = mock_del_func
        
        yield state

@pytest.fixture
def mock_ctypes():
    with patch("services.core_manager.ctypes") as m_ctypes:
        yield m_ctypes


def test_constructor_zero_registry_side_effects(clean_backup):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    with patch("winreg.OpenKey") as mock_open, \
         patch("winreg.QueryValueEx") as mock_query, \
         patch("winreg.SetValueEx") as mock_set, \
         patch("winreg.DeleteValue") as mock_del:
        cm = CoreManager("dummy.exe")
        mock_open.assert_not_called()
        mock_query.assert_not_called()
        mock_set.assert_not_called()
        mock_del.assert_not_called()

    assert clean_backup.exists()


def test_sysproxy_lifecycle(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    cm = CoreManager("dummy.exe")
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyEnable"] == (4, 1)
    
    cm.set_system_proxy(True, port=10811)
    
    assert os.path.exists(clean_backup)
    with open(clean_backup, "r", encoding="utf-8") as f:
        backup = json.load(f)
    assert backup["phase"] == "active"
    assert backup["owner"] == "LuciNet"
    assert backup["original"]["ProxyEnable"]["value"] == 1
    assert backup["original"]["ProxyServer"]["value"] == "1.2.3.4:8080"
    assert backup["managed"]["ProxyServer"]["value"] == "127.0.0.1:10811"
    
    assert reg_state["ProxyServer"] == (1, "127.0.0.1:10811")
    
    cm.set_system_proxy(False)
    
    assert reg_state["ProxyServer"] == (1, "1.2.3.4:8080")
    assert not os.path.exists(clean_backup)


def test_sysproxy_crash_recovery_startup(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    cm = CoreManager("dummy.exe")
    cm.set_system_proxy(True, port=10811)
    assert os.path.exists(clean_backup)
    
    del cm
    assert reg_state["ProxyServer"] == (1, "127.0.0.1:10811")
    
    recovered = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert recovered is True
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyServer"] == (1, "1.2.3.4:8080")


def test_state_machine_s0_rollback(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "applying",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "old:80"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "old:80")
    reg_state["ProxyOverride"] = (1, "<local>")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is True
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyEnable"] == (4, 0)


def test_state_machine_s1_rollback(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "applying",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "old:80"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "old:80")
    reg_state["ProxyOverride"] = (1, "<local>")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is True
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyEnable"] == (4, 0)


def test_state_machine_s2_rollback(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "applying",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "old:80"},
            "ProxyOverride": {"present": True, "type": 1, "value": "old_override"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "new_override"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "old_override")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is True
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "old:80")


def test_state_machine_s3_rollback(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "applying",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "old:80"},
            "ProxyOverride": {"present": True, "type": 1, "value": "old_override"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "new_override"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "new_override")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is True
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyEnable"] == (4, 0)


def test_state_machine_invalid_permutation_quarantined(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "applying",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "old:80"},
            "ProxyOverride": {"present": True, "type": 1, "value": "old_override"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "new_override"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "old:80")
    reg_state["ProxyOverride"] = (1, "new_override")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is False
    assert not os.path.exists(clean_backup)
    assert any("stale" in f for f in os.listdir(os.path.dirname(clean_backup)))


def test_active_mismatch_quarantined_as_stale(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:7890")
    reg_state["ProxyOverride"] = (1, "<local>")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is False
    assert not os.path.exists(clean_backup)
    assert any("stale" in f for f in os.listdir(os.path.dirname(clean_backup)))
    assert reg_state["ProxyServer"] == (1, "127.0.0.1:7890")


def test_present_false_vs_empty_string(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": True, "type": 1, "value": ""}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "<local>")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is True
    assert "ProxyServer" not in reg_state
    assert reg_state["ProxyOverride"] == (1, "")


def test_exact_proxyenable_2_preservation(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 2},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "<local>")
    
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is True
    assert reg_state["ProxyEnable"] == (4, 2)


def test_proxyenable_rejects_bool(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": True},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is False
    assert any("invalid" in f for f in os.listdir(os.path.dirname(clean_backup)))


def test_malformed_json_quarantined(clean_backup):
    with open(clean_backup, "w", encoding="utf-8") as f:
        f.write("{invalid_json: true,")
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is False
    assert any("corrupt" in f for f in os.listdir(os.path.dirname(clean_backup)))


def test_unrecognized_owner_quarantined(clean_backup):
    backup_data = {
        "version": 1,
        "owner": "OtherTool",
        "phase": "active",
        "original": {},
        "managed": {}
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is False
    assert any("unrecognized" in f for f in os.listdir(os.path.dirname(clean_backup)))


def test_unsupported_version_quarantined(clean_backup):
    backup_data = {
        "version": 2,
        "owner": "LuciNet",
        "phase": "active",
        "original": {},
        "managed": {}
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
    res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res is False
    assert any("unsupported_v" in f for f in os.listdir(os.path.dirname(clean_backup)))


def test_registry_permission_error_preserves_backup(clean_backup, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)
        
    with patch("winreg.OpenKey") as mock_open:
        mock_k_read = MagicMock()
        mock_k_write = MagicMock()
        def open_side_effect(hkey, subkey, reserved, access):
            if access == 0x00020019:
                return mock_k_read
            raise PermissionError("Access Denied to write")
        mock_open.side_effect = open_side_effect
        with patch("winreg.QueryValueEx") as mock_query:
            def q_side_effect(key, name):
                if name == "ProxyEnable": return [1, 4]
                if name == "ProxyServer": return ["127.0.0.1:10811", 1]
                if name == "ProxyOverride": return ["<local>", 1]
                raise FileNotFoundError()
            mock_query.side_effect = q_side_effect
            
            res = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
            assert res is False
            assert os.path.exists(clean_backup)


def test_repeated_recovery_idempotent(clean_backup, mock_winreg, mock_ctypes):
    cm = CoreManager("dummy.exe")
    cm.set_system_proxy(True, port=10811)
    
    res1 = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res1 is True
    assert not os.path.exists(clean_backup)
    
    res2 = CoreManager.recover_system_proxy_on_startup(os.path.dirname(clean_backup))
    assert res2 is False


def test_immediate_rollback_on_set_proxy_failure(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    cm = CoreManager("dummy.exe")
    
    original_set = mock_winreg["ProxyServer"]
    with patch("winreg.SetValueEx") as m_set:
        def set_side_effect(key, name, reserved, rtype, val):
            if name == "ProxyServer" and val == "127.0.0.1:10811":
                raise OSError("Disk / Registry write fault")
            reg_state[name] = (rtype, val)
        m_set.side_effect = set_side_effect
        
        with pytest.raises(OSError):
            cm.set_system_proxy(True, port=10811)
            
    assert not os.path.exists(clean_backup)
    assert reg_state["ProxyServer"] == (1, "1.2.3.4:8080")


def test_rollback_failure_retains_applying_backup(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    cm = CoreManager("dummy.exe")
    
    with patch("winreg.SetValueEx", side_effect=OSError("Permanent registry fault")):
        with pytest.raises(OSError):
            cm.set_system_proxy(True, port=10811)
            
    assert os.path.exists(clean_backup)
    with open(clean_backup, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["phase"] == "applying"


@patch("utils.win_job_object.assign_pid_to_job")
def test_core_manager_assign_success(mock_assign):
    mock_assign.return_value = True
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is True

@patch("utils.win_job_object.assign_pid_to_job")
def test_core_manager_assign_false(mock_assign):
    mock_assign.return_value = False
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is False
    cm.process.kill.assert_called()

@patch("utils.win_job_object.assign_pid_to_job")
def test_core_manager_assign_raises(mock_assign):
    mock_assign.side_effect = Exception("Boom")
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is False
    cm.process.kill.assert_called()

def test_core_manager_raw_xray_config_exact_payload(tmp_path):
    from domain.models.raw_config import RawXrayConfig
    from config import AppConfig
    
    raw_payload_text = json.dumps({"inbounds": [{"port": 12345, "protocol": "socks"}], "outbounds": [{"protocol": "freedom"}]})
    raw_cfg = RawXrayConfig(id=1, name="Test Raw", raw_payload=raw_payload_text)
    
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    
    cm.start_connection(raw_cfg, enable_sys_proxy=False, enable_tun=False)
    
    config_file = AppConfig.DATA_DIR / "client_config.json"
    assert config_file.exists()
    with open(config_file, "r", encoding="utf-8") as f:
        content_on_disk = f.read()
        
    assert content_on_disk == raw_payload_text


def test_reenable_does_not_overwrite_original_backup(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.original.proxy:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    cm = CoreManager("dummy.exe")

    cm.set_system_proxy(True, port=10811)
    assert clean_backup.exists()
    assert reg_state["ProxyEnable"] == (4, 1)
    assert reg_state["ProxyServer"] == (1, "127.0.0.1:10811")

    with open(clean_backup, "r", encoding="utf-8") as f:
        b1 = json.load(f)
    assert b1["original"]["ProxyServer"]["value"] == "user.original.proxy:8080"
    assert b1["managed"]["ProxyServer"]["value"] == "127.0.0.1:10811"

    cm.set_system_proxy(True, port=19811)

    assert reg_state["ProxyServer"] == (1, "127.0.0.1:19811")
    with open(clean_backup, "r", encoding="utf-8") as f:
        b2 = json.load(f)
    assert b2["original"]["ProxyServer"]["value"] == "user.original.proxy:8080"
    assert b2["managed"]["ProxyServer"]["value"] == "127.0.0.1:19811"

    cm.set_system_proxy(False)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.original.proxy:8080")
    assert reg_state["ProxyOverride"] == (1, "<local>")
    assert not clean_backup.exists()


def test_write_backup_atomic_operations_and_cleanup(tmp_path):
    target_file = tmp_path / "sysproxy_backup.json"
    dummy_data = {"version": 1, "owner": "LuciNet"}

    with patch("os.fsync", wraps=os.fsync) as mock_fsync, \
         patch("os.replace", wraps=os.replace) as mock_replace:
        CoreManager._write_backup_atomic(target_file, dummy_data)
        mock_fsync.assert_called_once()
        mock_replace.assert_called_once()

    assert target_file.exists()
    with open(target_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == dummy_data

    with patch("os.fsync", side_effect=OSError("Disk sync failed")), \
         pytest.raises(OSError, match="Disk sync failed"):
        CoreManager._write_backup_atomic(target_file, {"should": "fail"})

    stray_tmp = list(tmp_path.glob("*.tmp.*"))
    assert stray_tmp == []


def test_schema_invalid_present_false_with_non_null(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": 1, "value": ""},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert res is False
    assert not clean_backup.exists()

    quarantined = list(clean_backup.parent.glob("sysproxy_backup.invalid.*.json"))
    assert len(quarantined) == 1


def test_restore_success_delete_failure_quarantined_as_restored(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "1.2.3.4:8080"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "<local>")

    real_remove = os.remove
    def remove_side_effect(path):
        if "sysproxy_backup.json" in str(path):
            raise PermissionError("File locked by process")
        real_remove(path)

    with patch("os.remove", side_effect=remove_side_effect):
        recovered = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)

    assert recovered is True
    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "1.2.3.4:8080")
    assert not clean_backup.exists()
    restored_files = list(clean_backup.parent.glob("sysproxy_backup.restored.*.json"))
    assert len(restored_files) == 1


def test_rollback_failure_retains_applying_backup_realistic(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    cm = CoreManager("dummy.exe")

    attempt_count = 0
    with patch("winreg.SetValueEx") as m_set:
        def set_side_effect(key, name, reserved, rtype, val):
            nonlocal attempt_count
            attempt_count += 1
            if name == "ProxyEnable" and attempt_count == 1:
                reg_state[name] = (rtype, val)
                return
            if name == "ProxyServer":
                raise OSError("Disk error setting ProxyServer")
            if name == "ProxyEnable" and attempt_count > 1:
                raise OSError("Fatal error during rollback")
            reg_state[name] = (rtype, val)

        m_set.side_effect = set_side_effect

        with pytest.raises(OSError, match="Disk error setting ProxyServer"):
            cm.set_system_proxy(True, port=10811)

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["phase"] == "applying"


def test_reconnect_after_external_registry_change_does_not_reuse_stale_original(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "custom.proxy:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    cm = CoreManager("dummy.exe")

    cm.set_system_proxy(True, port=10811)
    assert clean_backup.exists()
    assert reg_state["ProxyServer"] == (1, "127.0.0.1:10811")

    reg_state["ProxyServer"] = (1, "external.override:9090")

    cm.set_system_proxy(True, port=19811)

    stale_files = list(clean_backup.parent.glob("sysproxy_backup.stale.*.json"))
    assert len(stale_files) == 1

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        new_backup = json.load(f)
    assert new_backup["original"]["ProxyServer"]["value"] == "external.override:9090"
    assert new_backup["managed"]["ProxyServer"]["value"] == "127.0.0.1:19811"

    cm.set_system_proxy(False)
    assert reg_state["ProxyServer"] == (1, "external.override:9090")
    assert not clean_backup.exists()


def test_corrupt_existing_backup_is_quarantined_before_new_backup(clean_backup, mock_winreg, mock_ctypes):
    with open(clean_backup, "w", encoding="utf-8") as f:
        f.write("{invalid json: incomplete")

    cm = CoreManager("dummy.exe")
    cm.set_system_proxy(True, port=10811)

    corrupt_files = list(clean_backup.parent.glob("sysproxy_backup.corrupt.*.json"))
    assert len(corrupt_files) == 1

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        new_b = json.load(f)
    assert new_b["owner"] == "LuciNet"
    assert new_b["phase"] == "active"


def test_foreign_existing_backup_is_not_silently_overwritten(clean_backup, mock_winreg, mock_ctypes):
    foreign_data = {
        "version": 1,
        "owner": "OtherVPN",
        "phase": "active",
        "original": {},
        "managed": {}
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(foreign_data, f)

    cm = CoreManager("dummy.exe")
    cm.set_system_proxy(True, port=10811)

    unrecognized_files = list(clean_backup.parent.glob("sysproxy_backup.unrecognized.*.json"))
    assert len(unrecognized_files) == 1
    with open(unrecognized_files[0], "r", encoding="utf-8") as f:
        quarantined_data = json.load(f)
    assert quarantined_data["owner"] == "OtherVPN"

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        new_b = json.load(f)
    assert new_b["owner"] == "LuciNet"


def test_stale_active_backup_is_quarantined_before_reconnect(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    active_backup = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(active_backup, f)

    reg_state["ProxyEnable"] = (4, 0)
    del reg_state["ProxyServer"]
    del reg_state["ProxyOverride"]

    cm = CoreManager("dummy.exe")
    cm.set_system_proxy(True, port=19811)

    stale_files = list(clean_backup.parent.glob("sysproxy_backup.stale.*.json"))
    assert len(stale_files) == 1

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        new_b = json.load(f)
    assert new_b["original"]["ProxyEnable"]["value"] == 0
    assert new_b["original"]["ProxyServer"]["present"] is False
    assert new_b["managed"]["ProxyServer"]["value"] == "127.0.0.1:19811"


def test_quarantine_failure_blocks_new_backup_and_registry_apply(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    initial_reg = dict(reg_state)

    foreign_data = {
        "version": 1,
        "owner": "ForeignApp",
        "phase": "active"
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(foreign_data, f)

    cm = CoreManager("dummy.exe")

    with patch.object(CoreManager, "_quarantine_backup", return_value=False), \
         patch("winreg.SetValueEx") as mock_set, \
         patch("winreg.DeleteValue") as mock_del:
        cm.set_system_proxy(True, port=10811)
        mock_set.assert_not_called()
        mock_del.assert_not_called()

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        content = json.load(f)
    assert content["owner"] == "ForeignApp"

    assert content.get("phase") == "active"
    assert "managed" not in content

    assert reg_state == initial_reg


def test_registry_changes_between_snapshot_and_apply_aborts_safely(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "initial.proxy:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    cm = CoreManager("dummy.exe")

    open_call_count = 0

    with patch("winreg.OpenKey") as mock_open:
        def open_hook(hkey, subkey, reserved, access):
            nonlocal open_call_count
            open_call_count += 1
            if open_call_count == 2:
                reg_state["ProxyServer"] = (1, "concurrent.external:9999")
            return MagicMock()

        mock_open.side_effect = open_hook

        with patch("winreg.SetValueEx") as mock_set, \
             patch("winreg.DeleteValue") as mock_del:
            cm.set_system_proxy(True, port=10811)
            mock_set.assert_not_called()
            mock_del.assert_not_called()

    assert not clean_backup.exists()
    assert reg_state["ProxyServer"] == (1, "concurrent.external:9999")


def test_schema_invalid_present_non_bool(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": 1, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert res is False
    assert not clean_backup.exists()
    invalid_files = list(clean_backup.parent.glob("sysproxy_backup.invalid.*.json"))
    assert len(invalid_files) == 1


def test_schema_invalid_version_bool(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": True,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": False, "type": None, "value": None},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert res is False
    assert not clean_backup.exists()
    unsupported_files = list(clean_backup.parent.glob("sysproxy_backup.unsupported_v.*.json"))
    assert len(unsupported_files) == 1


def test_schema_invalid_proxyserver_type_bool_true_quarantined(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": True, "value": "1.2.3.4:8080"},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert res is False
    assert not clean_backup.exists()
    invalid_files = list(clean_backup.parent.glob("sysproxy_backup.invalid.*.json"))
    assert len(invalid_files) == 1


def test_schema_invalid_proxyserver_type_float_1_0_quarantined(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1.0, "value": "1.2.3.4:8080"},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert res is False
    assert not clean_backup.exists()
    invalid_files = list(clean_backup.parent.glob("sysproxy_backup.invalid.*.json"))
    assert len(invalid_files) == 1


def test_schema_invalid_proxyserver_type_float_2_0_quarantined(clean_backup, mock_winreg, mock_ctypes):
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 2.0, "value": "1.2.3.4:8080"},
            "ProxyOverride": {"present": False, "type": None, "value": None}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert res is False
    assert not clean_backup.exists()
    invalid_files = list(clean_backup.parent.glob("sysproxy_backup.invalid.*.json"))
    assert len(invalid_files) == 1


def test_write_backup_atomic_replace_failure_cleans_up_and_preserves_target(tmp_path):
    target_file = tmp_path / "sysproxy_backup.json"
    initial_data = {"version": 1, "owner": "LuciNet", "initial": True}
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    new_data = {"version": 1, "owner": "LuciNet", "initial": False}

    with patch("os.replace", side_effect=OSError("Replace locked by filesystem")), \
         pytest.raises(OSError, match="Replace locked by filesystem"):
        CoreManager._write_backup_atomic(target_file, new_data)

    with open(target_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == initial_data

    stray_tmp = list(tmp_path.glob("*.tmp.*"))
    assert stray_tmp == []


def test_restore_success_both_remove_and_quarantine_fail_invalidates_backup(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "1.2.3.4:8080"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "<local>")

    with patch("os.remove", side_effect=PermissionError("Locked by process")), \
         patch.object(CoreManager, "_quarantine_backup", return_value=False):
        res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)

    assert res is False

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "1.2.3.4:8080")

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        inv = json.load(f)
    assert inv["phase"] == "restored_quarantine_failed"

    next_res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert next_res is False


def test_invalidate_backup_atomic_replace_failure_cleans_up_and_returns_false(tmp_path):
    target_file = tmp_path / "sysproxy_backup.json"
    initial_data = {"version": 1, "owner": "LuciNet", "phase": "active"}
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    with patch("os.replace", side_effect=OSError("Replace locked by AV")):
        res = CoreManager._invalidate_backup_atomic(target_file)

    assert res is False

    with open(target_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == initial_data

    stray_tmp = list(tmp_path.glob("*.tmp.*"))
    assert stray_tmp == []


def test_restore_success_when_both_cleanup_and_invalidation_fail_stale_on_next_startup(clean_backup, mock_winreg, mock_ctypes):
    reg_state = mock_winreg
    backup_data = {
        "version": 1,
        "owner": "LuciNet",
        "phase": "active",
        "created_at": time.time(),
        "original": {
            "ProxyEnable": {"present": True, "type": 4, "value": 0},
            "ProxyServer": {"present": True, "type": 1, "value": "1.2.3.4:8080"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        },
        "managed": {
            "ProxyEnable": {"present": True, "type": 4, "value": 1},
            "ProxyServer": {"present": True, "type": 1, "value": "127.0.0.1:10811"},
            "ProxyOverride": {"present": True, "type": 1, "value": "<local>"}
        }
    }
    with open(clean_backup, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    reg_state["ProxyEnable"] = (4, 1)
    reg_state["ProxyServer"] = (1, "127.0.0.1:10811")
    reg_state["ProxyOverride"] = (1, "<local>")

    with patch("os.remove", side_effect=PermissionError("Locked")), \
         patch.object(CoreManager, "_quarantine_backup", return_value=False), \
         patch.object(CoreManager, "_invalidate_backup_atomic", return_value=False):
        res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)

    assert res is False

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "1.2.3.4:8080")

    assert clean_backup.exists()
    with open(clean_backup, "r", encoding="utf-8") as f:
        data_after = json.load(f)
    assert data_after["phase"] == "active"

    with patch("os.replace", wraps=os.replace):
        next_res = CoreManager.recover_system_proxy_on_startup(clean_backup.parent)
    assert next_res is False
    assert not clean_backup.exists()
    stale_files = list(clean_backup.parent.glob("sysproxy_backup.stale.*.json"))
    assert len(stale_files) == 1


def test_xray_startup_error_occurred_rolls_back_system_proxy(clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Test Raw", raw_payload='{"inbounds": []}')
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    cm.process.state.return_value = QProcess.ProcessState.Starting

    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)
    assert clean_backup.exists()
    assert reg_state["ProxyServer"] == (1, f"127.0.0.1:{cm.local_port}")

    cm._handle_process_error(QProcess.ProcessError.FailedToStart)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False


def test_xray_startup_immediate_exit_before_running_rolls_back_system_proxy(clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Test Raw", raw_payload='{"inbounds": []}')
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    cm.process.state.return_value = QProcess.ProcessState.Starting

    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)

    assert reg_state["ProxyServer"] == (1, f"127.0.0.1:{cm.local_port}")
    assert clean_backup.exists()

    cm.process.state.return_value = QProcess.ProcessState.NotRunning
    cm._handle_state_change(QProcess.ProcessState.NotRunning)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False


def test_xray_startup_immediate_synchronous_failure_aborts_proxy(clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Test Raw", raw_payload='{"inbounds": []}')
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()
    cm.process.state.return_value = QProcess.ProcessState.NotRunning

    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False


@patch("utils.win_job_object.assign_pid_to_job", return_value=True)
def test_xray_reconnect_does_not_prematurely_rollback_system_proxy(mock_assign, clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg1 = RawXrayConfig(id=1, name="Server 1", raw_payload='{"inbounds": []}')
    raw_cfg2 = RawXrayConfig(id=2, name="Server 2", raw_payload='{"inbounds": []}')

    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()

    cm.process.state.return_value = QProcess.ProcessState.Starting
    cm.start_connection(raw_cfg1, enable_sys_proxy=True, enable_tun=False)
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is True

    cm.process.kill.side_effect = lambda: cm._handle_state_change(QProcess.ProcessState.NotRunning)
    cm.stop_connection(clear_sys_proxy=False)
    assert reg_state["ProxyServer"] == (1, f"127.0.0.1:{cm.local_port}")

    cm.local_port = 19811
    cm.process.kill.side_effect = None
    cm.process.state.return_value = QProcess.ProcessState.Starting
    cm.start_connection(raw_cfg2, enable_sys_proxy=True, enable_tun=False)
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is True
    assert reg_state["ProxyServer"] == (1, "127.0.0.1:19811")

    cm.stop_connection(clear_sys_proxy=True)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()


def test_xray_real_qprocess_nonexistent_binary_aborts_cleanly(clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Test Raw", raw_payload='{"inbounds": []}')
    cm = CoreManager("nonexistent_binary_for_test_12345.exe")

    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False


@patch("utils.win_job_object.assign_pid_to_job", return_value=True)
def test_xray_running_unexpected_termination_rolls_back_system_proxy(mock_assign, clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Server 1", raw_payload='{"inbounds": []}')
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()

    cm.process.state.return_value = QProcess.ProcessState.Starting
    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is True
    assert reg_state["ProxyServer"] == (1, f"127.0.0.1:{cm.local_port}")
    assert clean_backup.exists()

    cm.process.state.return_value = QProcess.ProcessState.NotRunning
    cm._handle_state_change(QProcess.ProcessState.NotRunning)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False


@patch("utils.win_job_object.assign_pid_to_job", return_value=True)
def test_xray_running_unexpected_error_occurred_rolls_back_system_proxy(mock_assign, clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Server 1", raw_payload='{"inbounds": []}')
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()

    cm.process.state.return_value = QProcess.ProcessState.Starting
    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is True
    assert reg_state["ProxyServer"] == (1, f"127.0.0.1:{cm.local_port}")
    assert clean_backup.exists()

    cm._handle_process_error(QProcess.ProcessError.Crashed)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False


@patch("utils.win_job_object.assign_pid_to_job", return_value=True)
def test_xray_running_normal_user_stop_restores_exactly_once(mock_assign, clean_backup, mock_winreg, mock_ctypes):
    from domain.models.raw_config import RawXrayConfig
    reg_state = mock_winreg
    reg_state["ProxyEnable"] = (4, 0)
    reg_state["ProxyServer"] = (1, "user.orig:8080")
    reg_state["ProxyOverride"] = (1, "<local>")

    raw_cfg = RawXrayConfig(id=1, name="Server 1", raw_payload='{"inbounds": []}')
    cm = CoreManager("dummy.exe")
    cm.process = MagicMock()

    cm.process.state.return_value = QProcess.ProcessState.Starting
    cm.start_connection(raw_cfg, enable_sys_proxy=True, enable_tun=False)
    cm.process.state.return_value = QProcess.ProcessState.Running
    cm._handle_state_change(QProcess.ProcessState.Running)
    assert cm.is_connected is True

    restore_spy = MagicMock(wraps=cm.recover_system_proxy_on_startup)
    with patch.object(CoreManager, "recover_system_proxy_on_startup", restore_spy):
        cm.process.kill.side_effect = lambda: cm._handle_state_change(QProcess.ProcessState.NotRunning)
        cm.stop_connection(clear_sys_proxy=True)

    assert reg_state["ProxyEnable"] == (4, 0)
    assert reg_state["ProxyServer"] == (1, "user.orig:8080")
    assert not clean_backup.exists()
    assert cm.is_connected is False
    assert restore_spy.call_count == 1







