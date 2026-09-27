import sys
import os
import subprocess
import time
import pytest
import asyncio
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Objects are specific to Windows.")

@pytest.fixture
def test_executable(tmp_path):
    exe_path = tmp_path / "dummy_xray.py"
    exe_path.write_text("import time\nwhile True:\n    time.sleep(1)\n")
    return sys.executable, str(exe_path)

def test_win_job_object_kills_child_on_parent_crash(tmp_path, test_executable):
    python_exe, dummy_script = test_executable
    
    parent_script = tmp_path / "parent_crasher.py"
    parent_code = f"""
import sys
import subprocess
import time
import os

sys.path.insert(0, r"{os.path.abspath('L:/My projects/LuciNet')}")
from utils.win_job_object import assign_pid_to_job

# Start child
child = subprocess.Popen([r"{python_exe}", r"{dummy_script}"])
assign_pid_to_job(child.pid)

# Write child pid to file so test can verify it
with open(r"{tmp_path / 'child_pid.txt'}", 'w') as f:
    f.write(str(child.pid))

# Wait a tiny bit to ensure it's running
time.sleep(1)
# Hard crash
os._exit(1)
"""
    parent_script.write_text(parent_code)

    parent = subprocess.Popen([python_exe, str(parent_script)])
    parent.wait(timeout=5)
    
    child_pid_file = tmp_path / 'child_pid.txt'
    assert child_pid_file.exists()
    child_pid = int(child_pid_file.read_text().strip())
    
    time.sleep(1)
    try:
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32')
        h_process = kernel32.OpenProcess(0x0400, False, child_pid)
        if h_process:
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code))
            kernel32.CloseHandle(h_process)
            is_alive = (exit_code.value == 259)
        else:
            is_alive = False
    except OSError:
        is_alive = False
        
    assert not is_alive, "Child process survived parent crash!"


def test_setup_job_object_failure_closes_handle():
    import utils.win_job_object as wjo
    wjo._job_handle = None
    with patch("ctypes.WinDLL") as mock_windll:
        mock_kernel32 = MagicMock()
        mock_windll.return_value = mock_kernel32
        
        mock_kernel32.CreateJobObjectW.return_value = 12345
        mock_kernel32.SetInformationJobObject.return_value = 0
        
        res = wjo._setup_job_object()
        
        assert res is False
        assert wjo._job_handle is None
        mock_kernel32.CloseHandle.assert_called_once_with(12345)

def test_assign_pid_returns_false():
    import utils.win_job_object as wjo
    with patch("utils.win_job_object._setup_job_object") as mock_setup:
        wjo._job_handle = None
        res = wjo.assign_pid_to_job(100)
        assert res is False


def test_job_object_concurrent_init():
    import utils.win_job_object as wjo
    import threading
    wjo._job_handle = None
    
    if hasattr(wjo, "_job_lock") and wjo._job_lock.locked():
        wjo._job_lock.release()
        
    with patch("ctypes.WinDLL") as mock_windll:
        mock_k32 = MagicMock()
        mock_windll.return_value = mock_k32
        mock_k32.CreateJobObjectW.return_value = 999
        mock_k32.SetInformationJobObject.return_value = 1
        
        num_threads = 20
        barrier = threading.Barrier(num_threads)
        
        def worker():
            barrier.wait()
            wjo._setup_job_object()
            
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert mock_k32.CreateJobObjectW.call_count == 1
        assert mock_k32.SetInformationJobObject.call_count == 1
        assert wjo._job_handle == 999
        mock_k32.CloseHandle.assert_not_called()


def test_openprocess_failure():
    import utils.win_job_object as wjo
    try:
        with patch("utils.win_job_object._setup_job_object", return_value=True):
            wjo._job_handle = 123
            with patch("ctypes.WinDLL") as mock_windll:
                mock_k32 = MagicMock()
                mock_windll.return_value = mock_k32
                mock_k32.OpenProcess.return_value = 0
                
                res = wjo.assign_pid_to_job(10)
                assert res is False
                mock_k32.AssignProcessToJobObject.assert_not_called()
    finally:
        wjo._job_handle = None

def test_assignprocess_failure():
    import utils.win_job_object as wjo
    try:
        with patch("utils.win_job_object._setup_job_object", return_value=True):
            wjo._job_handle = 123
            with patch("ctypes.WinDLL") as mock_windll:
                mock_k32 = MagicMock()
                mock_windll.return_value = mock_k32
                mock_k32.OpenProcess.return_value = 456
                mock_k32.AssignProcessToJobObject.return_value = 0
                
                res = wjo.assign_pid_to_job(10)
                assert res is False
                mock_k32.CloseHandle.assert_called_with(456)
    finally:
        wjo._job_handle = None
