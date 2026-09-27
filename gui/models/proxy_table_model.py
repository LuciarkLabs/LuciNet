from PySide6.QtCore import QAbstractTableModel, Qt
from typing import List
from domain.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from typing import Union
from PySide6.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel
from PySide6.QtGui import QColor
import re
import ipaddress


def get_address_type(address: str) -> str:
    """تشخیص نوع آدرس سرور (IPv4, IPv6, Domain)"""
    if not address:
        return "Unknown"
    try:
        ip = ipaddress.ip_address(address)
        if isinstance(ip, ipaddress.IPv4Address):
            return "IPv4"
        elif isinstance(ip, ipaddress.IPv6Address):
            return "IPv6"
    except ValueError:
        return "Domain"
    return "Unknown"


class ProxyTableModel(QAbstractTableModel):
    def __init__(self, proxies: List[Union[ProxyConfig, RawXrayConfig]] = None):
        super().__init__()
        self.proxies = proxies or []
        self.headers = [
            "Group",
            "Remark",
            "Protocol",
            "Server",
            "Real IP",
            "Port",
            "Network",
            "Security",
            "Country",
            "Ping (ms)",
            "Status",
            "Speed (MB/s)",
        ]

    def update_data(self, new_proxies: List[Union[ProxyConfig, RawXrayConfig]]):
        """لود کردن دیتای جدید در جدول"""
        self.beginResetModel()
        self.proxies = new_proxies
        self.endResetModel()

    def update_proxy(self, updated_proxy: Union[ProxyConfig, RawXrayConfig]):
        for row, proxy in enumerate(self.proxies):
            if type(proxy) == type(updated_proxy) and proxy.id == updated_proxy.id:
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
        is_raw = isinstance(proxy, RawXrayConfig)

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return proxy.group_name
            if col == 1:
                return proxy.name if is_raw else proxy.remark
            if col == 2:
                if is_raw:
                    return "RAW JSON"
                p_up = proxy.protocol.upper()
                return "SS" if p_up == "SHADOWSOCKS" else p_up
            if col == 3:
                if is_raw:
                    return proxy.server if proxy.server else f"[{proxy.source_type}] {proxy.source_ref}"
                return proxy.server
            if col == 4:
                return getattr(proxy, "real_ip", "") or "-"
            if col == 5:
                if is_raw:
                    return str(proxy.port) if proxy.port else "-"
                return str(proxy.port)
            if col == 6:
                return proxy.network.upper() if getattr(proxy, "network", "") else "-"
            if col == 7:
                return proxy.security.upper() if getattr(proxy, "security", "") else "-"
            if col == 8:
                return proxy.country or "-"
            if col == 9:
                ping_val = getattr(proxy, "ping", -1.0)
                return f"{ping_val} ms" if ping_val > 0 else "-"
            if col == 10:
                return getattr(proxy, "status", "Untested") or "Untested"
            if col == 11:
                spd = getattr(proxy, "download_speed", 0.0)
                return f"{spd} MB/s" if spd > 0 else "-"

        if role == Qt.ItemDataRole.ForegroundRole:
            if is_raw and col == 2:
                return QColor("#17a2b8")

            status = getattr(proxy, "status", "")
            if col == 10:
                if status == "Valid":
                    return QColor("#44bd32")
                elif status == "Error":
                    return QColor("#e84118")
                elif status == "Timeout":
                    return QColor("#fbc531")
                elif status == "Invalid":
                    return QColor("#e15f41")
                elif status == "Unsupported":
                    return QColor("#8854d0")
                return Qt.GlobalColor.darkGray

            ping_val = getattr(proxy, "ping", -1.0)
            if col == 9 and ping_val > 0:
                if ping_val < 300:
                    return Qt.GlobalColor.darkGreen
                elif ping_val < 700:
                    return Qt.GlobalColor.darkYellow
                else:
                    return Qt.GlobalColor.darkRed

            spd_val = getattr(proxy, "download_speed", 0.0)
            if col == 11 and spd_val > 0:
                if spd_val > 2.0:
                    return Qt.GlobalColor.darkGreen
                elif spd_val > 0.5:
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
        self.ip_type_filter = ""

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        proxy = model.proxies[source_row]
        is_raw = isinstance(proxy, RawXrayConfig)

        if self.group_filter and proxy.group_name != self.group_filter:
            return False

        if self.status_filter:
            cur_status = getattr(proxy, "status", "Untested") or "Untested"
            if cur_status != self.status_filter:
                return False

        if self.protocol_filter:
            prot = "raw json" if is_raw else proxy.protocol.lower()
            filt = self.protocol_filter.lower()
            if filt in ("ss", "shadowsocks"):
                if prot not in ("ss", "shadowsocks"):
                    return False
            elif filt in ("raw", "raw json"):
                if prot not in ("raw", "raw json"):
                    return False
            elif prot != filt:
                return False

        if self.search_text:
            search_lower = self.search_text.lower()
            if is_raw:
                remark_lower = (proxy.name or "").lower()
                server_lower = (proxy.server or "").lower()
                ref_lower = (proxy.source_ref or "").lower()
                if (
                    search_lower not in remark_lower
                    and search_lower not in server_lower
                    and search_lower not in ref_lower
                ):
                    return False
            else:
                remark_lower = (proxy.remark or "").lower()
                server_lower = (proxy.server or "").lower()
                if search_lower not in remark_lower and search_lower not in server_lower:
                    return False

        if self.ip_type_filter:
            srv = proxy.server
            if not srv:
                return False
            addr_type = get_address_type(srv)
            if addr_type != self.ip_type_filter:
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

    def set_ip_type_filter(self, ip_type):
        if ip_type in [
            "همه آدرس‌ها",
            "All Types",
            "All Addresses",
            "-- All Addresses --",
            "-- همه آدرس‌ها --",
        ]:
            self.ip_type_filter = ""
        else:
            self.ip_type_filter = ip_type
        self.invalidateFilter()

    def lessThan(self, left, right):
        source_model = self.sourceModel()
        if not source_model:
            return super().lessThan(left, right)

        left_proxy = source_model.proxies[left.row()]
        right_proxy = source_model.proxies[right.row()]
        col = left.column()

        left_is_raw = isinstance(left_proxy, RawXrayConfig)
        right_is_raw = isinstance(right_proxy, RawXrayConfig)

        if col == 4:
            ip1_str = getattr(left_proxy, "real_ip", "") if not left_is_raw else ""
            ip2_str = getattr(right_proxy, "real_ip", "") if not right_is_raw else ""

            def ip_sort_key(ip_string):
                if not ip_string or ip_string == "-":
                    return (0, 0)
                try:
                    ip_obj = ipaddress.ip_address(ip_string)
                    return (ip_obj.version, int(ip_obj))
                except ValueError:
                    return (99, ip_string)

            return ip_sort_key(ip1_str) < ip_sort_key(ip2_str)

        elif col == 5:
            p1 = left_proxy.port if not left_is_raw else 0
            p2 = right_proxy.port if not right_is_raw else 0
            return (p1 or 0) < (p2 or 0)
        elif col == 9:
            p1 = left_proxy.ping if not left_is_raw and left_proxy.ping > 0 else float("inf")
            p2 = right_proxy.ping if not right_is_raw and right_proxy.ping > 0 else float("inf")
            return p1 < p2
        elif col == 11:
            s1 = getattr(left_proxy, "download_speed", 0.0) if not left_is_raw else 0.0
            s2 = getattr(right_proxy, "download_speed", 0.0) if not right_is_raw else 0.0
            return s1 < s2

        left_data = str(source_model.data(left) or "")
        right_data = str(source_model.data(right) or "")

        def natural_keys(text):
            return [
                int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)
            ]

        return natural_keys(left_data) < natural_keys(right_data)
