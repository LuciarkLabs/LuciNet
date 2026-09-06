from PySide6.QtCore import QObject, Signal

class EventBus(QObject):

    data_changed = Signal()
    scan_lock_changed = Signal(bool, str)

    proxy_selected = Signal(object)

    request_quick_connect = Signal(object)
    log_message = Signal(str)
    request_view_change = Signal(
        str
    )

    connection_status_changed = Signal(bool)

event_bus = EventBus()
