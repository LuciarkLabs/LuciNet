from PySide6.QtCore import QObject, Signal

class _EventBus(QObject):

    data_changed = Signal()

event_bus = _EventBus()

from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    data_changed = Signal()

    scan_lock_changed = Signal(bool, str)

event_bus = EventBus()
