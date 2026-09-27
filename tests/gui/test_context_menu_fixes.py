import sys
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import QModelIndex, QPoint

from domain.models.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from gui.tabs.archive.context_menu_handler import ContextMenuHandler

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

@pytest.fixture
def mock_clipboard():
    with patch('PySide6.QtWidgets.QApplication.clipboard') as mock_clip:
        clip_instance = MagicMock()
        
        storage = {}
        def set_text(text): storage['text'] = text
        def get_text(): return storage.get('text', '')
        
        clip_instance.setText.side_effect = set_text
        clip_instance.text.side_effect = get_text
        
        mock_clip.return_value = clip_instance
        yield clip_instance

@pytest.fixture
def make_handler(qapp):
    def _make(proxies):
        from PySide6.QtWidgets import QWidget
        parent = QWidget()
        tools_manager = MagicMock()
        tools_manager.is_running = False
        
        table_view = MagicMock()
        from PySide6.QtCore import QPoint
        table_view.viewport().mapToGlobal.return_value = QPoint(0, 0)
        
        idx = MagicMock(spec=QModelIndex)
        idx.isValid.return_value = True
        table_view.indexAt.return_value = idx
        
        sel_model = MagicMock()
        sel_model.selectedRows.return_value = [MagicMock(spec=QModelIndex) for _ in proxies]
        table_view.selectionModel.return_value = sel_model
        
        proxy_model = MagicMock()
        def mapToSource(index):
            idx2 = MagicMock(spec=QModelIndex)
            idx2.isValid.return_value = True
            idx2.row.return_value = sel_model.selectedRows.return_value.index(index)
            return idx2
            
        proxy_model.mapToSource.side_effect = mapToSource
        
        model = MagicMock()
        model.proxies = proxies
        
        return ContextMenuHandler(parent, tools_manager, table_view, model, proxy_model)
    return _make


def test_copy_proxy(make_handler, mock_clipboard):
    p = ProxyConfig(raw_url="vmess://proxy_test", protocol="vmess", remark="Proxy 1")
    handler = make_handler([p])
    
    with patch("gui.tabs.archive.context_menu_handler.QMessageBox.information") as mock_msg:
        handler._copy_to_clipboard(p)
        assert QApplication.clipboard().text() == "vmess://proxy_test"
        mock_msg.assert_called_once()


def test_copy_raw(make_handler, mock_clipboard):
    r = RawXrayConfig(name="Raw 1", raw_payload='{"test": 123}')
    handler = make_handler([r])
    
    with patch("gui.tabs.archive.context_menu_handler.QMessageBox.information") as mock_msg:
        handler._copy_to_clipboard(r)
        assert QApplication.clipboard().text() == '{"test": 123}'
        mock_msg.assert_called_once()


def test_raw_copy_preserves_exact_payload(make_handler, mock_clipboard):
    complex_payload = '''{
  "inbounds": [],
  "outbounds": [
    {
      "protocol": "freedom"
    }
  ]
}'''
    r = RawXrayConfig(name="Raw Exact", raw_payload=complex_payload)
    handler = make_handler([r])
    
    with patch("gui.tabs.archive.context_menu_handler.QMessageBox.information") as mock_msg:
        handler._copy_to_clipboard(r)
        assert QApplication.clipboard().text() == complex_payload


def test_proxy_qr_available(make_handler, qapp):
    p = ProxyConfig(raw_url="vmess://test", protocol="vmess", remark="Test")
    handler = make_handler([p])
    
    with patch("PySide6.QtWidgets.QMenu.exec") as mock_exec, \
         patch("PySide6.QtWidgets.QMenu.addAction") as mock_add_action:
        
        handler.show_context_menu(QPoint(0, 0), [], False)
        
        calls = [c[0][0] for c in mock_add_action.call_args_list]
        assert any("qr" in str(c).lower() or "QR" in str(c) for c in calls)


def test_raw_qr_hidden(make_handler, qapp):
    r = RawXrayConfig(name="Raw", raw_payload="{}")
    handler = make_handler([r])
    
    with patch("PySide6.QtWidgets.QMenu.exec") as mock_exec, \
         patch("PySide6.QtWidgets.QMenu.addAction") as mock_add_action:
        
        handler.show_context_menu(QPoint(0, 0), [], False)
        
        calls = [c[0][0] for c in mock_add_action.call_args_list]
        assert not any("qr" in str(c).lower() or "QR" in str(c) for c in calls)


def test_mixed_move_delete_regression(make_handler):
    p = ProxyConfig(raw_url="vmess://", protocol="vmess", remark="P1")
    p.id = 1
    r = RawXrayConfig(name="R1", raw_payload="{}")
    r.id = 2
    
    handler = make_handler([p, r])
    
    with patch("gui.tabs.archive.context_menu_handler.QInputDialog.getItem") as mock_input:
        mock_input.return_value = ("NewGroup", True)
        handler._request_move([p, r], ["Group1"])
        handler.tools_manager.execute_move.assert_called_once_with([1], [2], "NewGroup")
        
    with patch("gui.tabs.archive.context_menu_handler.QMessageBox.question") as mock_q:
        mock_q.return_value = 16384
        handler._request_delete([p, r])
        handler.tools_manager.execute_delete.assert_called_once_with([1], [2], action_type="delete_selected")

