from PySide6.QtCore import QAbstractTableModel, Qt
from typing import List
from domain.proxy import ProxyConfig
from PySide6.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel
from PySide6.QtGui import QColor
import re

class ProxyTableModel(QAbstractTableModel):
    def __init__(self, proxies: List[ProxyConfig] = None):
        super().__init__()
        self.proxies = proxies or []
        self.headers = [
            "ID",
            "Group",
            "Remark",
            "Protocol",
            "Server",
            "Port",
            "Network",
            "Security",
            "Country",
            "Ping (ms)",
            "Status",
            "Speed (MB/s)",
        ]

    def update_data(self, new_proxies: List[ProxyConfig]):

        self.beginResetModel()
        self.proxies = new_proxies
        self.endResetModel()

    def update_proxy(self, updated_proxy: ProxyConfig):

        for row, proxy in enumerate(self.proxies):
            if proxy.id == updated_proxy.id:
                self.proxies[row] = updated_proxy

                index_start = self.index(row, 0)
                index_end = self.index(row, len(self.headers) - 1)
                self.dataChanged.emit(
                    index_start,
                    index_end,
                    [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ForegroundRole],
                )
                break

    def rowCount(self, parent=None):
        return len(self.proxies)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.proxies)):
            return None

        proxy = self.proxies[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(proxy.id)
            if col == 1:
                return proxy.group_name
            if col == 2:
                return proxy.remark
            if col == 3:
                return proxy.protocol.upper()
            if col == 4:
                return proxy.server
            if col == 5:
                return str(proxy.port)
            if col == 6:
                return proxy.network.upper() if proxy.network else "-"
            if col == 7:
                return proxy.security.upper() if proxy.security else "-"
            if col == 8:
                return proxy.country or "-"
            if col == 9:
                return f"{proxy.ping} ms" if proxy.ping > 0 else "-"
            if col == 10:
                return proxy.status
            if col == 11:
                spd = getattr(proxy, "download_speed", 0.0)
                return f"{spd} MB/s" if spd > 0 else "-"

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 10:
                if proxy.status == "Valid":
                    return QColor("#44bd32")
                elif proxy.status == "Error":
                    return QColor("#e84118")
                elif proxy.status == "Timeout":
                    return QColor("#fbc531")
                elif proxy.status == "Invalid":
                    return QColor("#e15f41")
                return Qt.GlobalColor.darkGray
            if col == 9 and proxy.ping > 0:
                if proxy.ping < 300:
                    return Qt.GlobalColor.darkGreen
                elif proxy.ping < 700:
                    return Qt.GlobalColor.darkYellow
                else:
                    return Qt.GlobalColor.darkRed
            if col == 11 and getattr(proxy, "download_speed", 0.0) > 0:
                spd = proxy.download_speed
                if spd > 2.0:
                    return Qt.GlobalColor.darkGreen
                elif spd > 0.5:
                    return Qt.GlobalColor.darkYellow
                else:
                    return Qt.GlobalColor.darkRed

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.headers[section]
        return None

class ProxySortModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.group_filter = ""
        self.search_text = ""
        self.status_filter = ""
        self.protocol_filter = ""

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        proxy = model.proxies[source_row]

        if self.group_filter and proxy.group_name != self.group_filter:
            return False

        if self.status_filter and proxy.status != self.status_filter:
            return False

        if (
            self.protocol_filter
            and proxy.protocol.lower() != self.protocol_filter.lower()
        ):
            return False

        if self.search_text:
            search_lower = self.search_text.lower()
            remark_lower = (proxy.remark or "").lower()
            server_lower = (proxy.server or "").lower()

            if search_lower not in remark_lower and search_lower not in server_lower:
                return False

        return True

    def set_group_filter(self, group_name):
        self.group_filter = group_name
        self.invalidateFilter()

    def set_status_filter(self, status):
        self.status_filter = status
        self.invalidateFilter()

    def set_protocol_filter(self, protocol):
        self.protocol_filter = protocol
        self.invalidateFilter()

    def set_search_text(self, text):
        self.search_text = text
        self.invalidateFilter()

    def lessThan(self, left, right):
        source_model = self.sourceModel()
        if not source_model:
            return super().lessThan(left, right)

        left_proxy = source_model.proxies[left.row()]
        right_proxy = source_model.proxies[right.row()]
        col = left.column()

        if col == 0:
            return (left_proxy.id or 0) < (right_proxy.id or 0)
        elif col == 5:
            return (left_proxy.port or 0) < (right_proxy.port or 0)
        elif col == 9:
            p1 = left_proxy.ping if left_proxy.ping > 0 else float("inf")
            p2 = right_proxy.ping if right_proxy.ping > 0 else float("inf")
            return p1 < p2
        elif col == 11:
            s1 = getattr(left_proxy, "download_speed", 0.0)
            s2 = getattr(right_proxy, "download_speed", 0.0)
            return s1 < s2

        left_data = str(source_model.data(left) or "")
        right_data = str(source_model.data(right) or "")

        def natural_keys(text):

            return [
                int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)
            ]

        return natural_keys(left_data) < natural_keys(right_data)
