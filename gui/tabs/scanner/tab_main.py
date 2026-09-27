from PySide6.QtWidgets import QWidget, QMessageBox, QHeaderView
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from gui.language_manager import LanguageManager
from gui.event_bus import event_bus
from .ui_layout import ScannerUiLayout

from .managers.data_manager import DataManager
from .managers.scan_manager import ScanManager
from .managers.speed_manager import SpeedManager
from .context_menu_handler import ContextMenuHandler


class ScannerTab(QWidget):
    def __init__(self, repository, scan_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service

        self.ui = ScannerUiLayout()
        self.ui.setup_ui(self)

        self.model = ProxyTableModel([])
        self.proxy_model = ProxySortModel()
        self.proxy_model.setSourceModel(self.model)
        self.ui.table_view.setModel(self.proxy_model)

        self._setup_table_headers()

        self.data_manager = DataManager(repository)
        self.scan_manager = ScanManager(scan_service)
        self.speed_manager = SpeedManager(scan_service, repository)

        self.menu_handler = ContextMenuHandler(
            self,
            repository,
            self.speed_manager,
            self.scan_manager,
            self.ui.table_view,
            self.model,
            self.proxy_model,
        )

        self._last_group_data = ""

        self._connect_signals()
        self.retranslate_ui()
        self.data_manager.load_groups()

    def _setup_table_headers(self):
        header = self.ui.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.table_view.setColumnWidth(0, 100)
        self.ui.table_view.setColumnWidth(2, 70)
        self.ui.table_view.setColumnWidth(3, 140)
        self.ui.table_view.setColumnWidth(4, 130)
        self.ui.table_view.setColumnWidth(5, 60)
        self.ui.table_view.setColumnWidth(6, 70)
        self.ui.table_view.setColumnWidth(7, 80)
        self.ui.table_view.setColumnWidth(8, 70)
        self.ui.table_view.setColumnWidth(9, 90)
        self.ui.table_view.setColumnWidth(10, 80)
        self.ui.table_view.setColumnWidth(11, 100)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def _connect_signals(self):
        self.ui.btn_refresh.clicked.connect(
            lambda: self.data_manager.refresh(self.ui.cmb_group.currentData())
        )
        self.ui.btn_load_untested.clicked.connect(
            lambda: self.data_manager.load_untested(self.ui.cmb_group.currentData())
        )
        self.ui.btn_load_all.clicked.connect(
            lambda: self.data_manager.load_all(self.ui.cmb_group.currentData())
        )
        self.ui.btn_start.clicked.connect(self._start_full_scan)
        self.ui.btn_scan_selected.clicked.connect(self._start_selected_scan)
        self.ui.btn_stop.clicked.connect(self._stop_all)
        self.ui.btn_speed_valid.clicked.connect(self._start_speed_test)

        self.ui.cmb_group.currentIndexChanged.connect(self._on_group_changed)
        self.ui.txt_search.textChanged.connect(self.apply_adv_filters)
        self.ui.cmb_status.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_protocol.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_ip_filter.currentIndexChanged.connect(self.apply_adv_filters)

        self.ui.table_view.selectionModel().selectionChanged.connect(
            self._update_button_states
        )
        self.ui.table_view.customContextMenuRequested.connect(self._on_context_menu)
        event_bus.data_changed.connect(self.safe_refresh_data)

        self.data_manager.loading_state_changed.connect(self._refresh_ui_state)
        self.scan_manager.state_changed.connect(self._refresh_ui_state)
        self.speed_manager.state_changed.connect(self._refresh_ui_state)
        self.menu_handler.state_changed.connect(self._refresh_ui_state)

        self.data_manager.groups_loaded.connect(self._populate_groups)
        self.data_manager.data_loaded.connect(self._populate_table)
        self.data_manager.error_occurred.connect(self._show_error)

        self.scan_manager.scan_started.connect(self._on_scan_started)
        self.scan_manager.progress_updated.connect(self.model.update_proxy)
        self.scan_manager.progress_text_updated.connect(self._update_scan_progress_text)
        self.scan_manager.finished.connect(self._on_scan_finished)
        self.scan_manager.error_occurred.connect(self._show_error)

        self.speed_manager.progress_updated.connect(self._update_speed_progress_text)
        self.speed_manager.finished.connect(self._on_speed_finished)
        self.speed_manager.single_result_ready.connect(self._on_single_speed_done)
        self.speed_manager.error_occurred.connect(self._show_error)

        self.menu_handler.error_occurred.connect(self._show_error)

    def _refresh_ui_state(self, _=None):
        """مدیریت مرکزی تمام دکمه‌ها و فرم‌ها با تفکیک Loading و Operations"""
        is_loading = self.data_manager.is_loading

        is_stoppable_operation = (
            self.scan_manager.is_running or self.speed_manager.is_running
        )

        is_busy = (
            is_loading or is_stoppable_operation or self.menu_handler.action_running
        )

        can_load = not is_busy
        self.ui.btn_refresh.setEnabled(can_load)
        self.ui.btn_load_untested.setEnabled(can_load)
        self.ui.btn_load_all.setEnabled(can_load)
        self.ui.cmb_group.setEnabled(can_load)

        self.ui.spin_concurrent.setEnabled(not is_busy)
        self.ui.spin_timeout.setEnabled(not is_busy)
        self.ui.cmb_speed_size.setEnabled(not is_busy)
        self.ui.chk_deep_scan.setEnabled(not is_busy)
        self.ui.rb_probe_http.setEnabled(not is_busy)
        self.ui.rb_probe_https.setEnabled(not is_busy)

        has_data = len(self.model.proxies) > 0
        self.ui.btn_start.setEnabled(not is_busy and has_data)
        self.ui.btn_speed_valid.setEnabled(not is_busy and has_data)

        self.ui.btn_stop.setEnabled(is_stoppable_operation)

        self._update_button_states()

        if is_stoppable_operation or self.menu_handler.action_running:
            self.ui.lbl_status.show()
            self.ui.progress_bar.show()
            self._broadcast_lock(True)
        elif is_loading:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_loading"))
            self.ui.progress_bar.hide()
            self._broadcast_lock(False)
        else:
            self._broadcast_lock(False)

    def _start_full_scan(self):
        self._pass_scan_params()
        self.scan_manager.start_scan(self.model.proxies)

    def _start_selected_scan(self):
        proxies = self._get_selected_proxies()
        self._pass_scan_params()
        self.scan_manager.start_scan(proxies)

    def _pass_scan_params(self):
        probe_mode = "https" if self.ui.rb_probe_https.isChecked() else "http"
        self.scan_manager.set_scan_params(
            self.ui.spin_concurrent.value(),
            self.ui.spin_timeout.value(),
            self.ui.chk_deep_scan.isChecked(),
            probe_mode=probe_mode,
        )

    def _start_speed_test(self):
        valid_proxies = [p for p in self.model.proxies if p.status == "Valid"]
        if not valid_proxies:
            QMessageBox.warning(
                self,
                LanguageManager.tr("scn_msg_no_valid_title"),
                LanguageManager.tr("scn_msg_no_valid_body"),
            )
            return
        self.speed_manager.test_multiple(
            valid_proxies, self.ui.cmb_speed_size.currentData()
        )

    def _stop_all(self):
        self.ui.btn_stop.setEnabled(False)
        self.ui.lbl_status.setText(LanguageManager.tr("scn_status_stopping"))
        self.scan_manager.stop()
        self.speed_manager.stop()

    def _on_context_menu(self, pos):
        if self.data_manager.is_loading:
            return

        groups = [
            self.ui.cmb_group.itemData(i) for i in range(1, self.ui.cmb_group.count())
        ]
        self.menu_handler.show_context_menu(
            pos, groups, self.ui.cmb_speed_size.currentData()
        )

    def _on_scan_started(self, total, is_deep_scan):
        self.ui.progress_bar.setMaximum(total)
        if is_deep_scan:
            self.ui.lbl_status.setText(
                LanguageManager.tr("scn_status_deep_start").format(count=total)
            )
            self.ui.lbl_status.setStyleSheet("color: #8c7ae6; font-weight: bold;")
        else:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_scan_start"))
            self.ui.lbl_status.setStyleSheet("")

    def _update_scan_progress_text(self, current, total, ping):
        self.ui.progress_bar.setValue(current)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_scanning").format(
                current=current, total=total, ping=ping
            )
        )

    def _update_speed_progress_text(self, current, total, proxy):
        self.ui.progress_bar.setValue(current)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_speed_prog").format(
                current=current, total=total
            )
        )
        self.model.update_proxy(proxy)

    def _on_scan_finished(self, was_stopped):
        if not was_stopped:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_scan_done"))
        self.ui.lbl_status.setStyleSheet("")
        event_bus.data_changed.emit()

    def _on_speed_finished(self, was_stopped):
        if not was_stopped:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_speed_done"))
            self.ui.lbl_status.setStyleSheet("color: #44bd32; font-weight: bold;")
            QMessageBox.information(
                self,
                LanguageManager.tr("scn_msg_speed_done_title"),
                LanguageManager.tr("scn_msg_speed_done_body"),
            )
        self.ui.lbl_status.setStyleSheet("")
        event_bus.data_changed.emit()

    def _on_single_speed_done(self, proxy, speed):
        self.model.update_proxy(proxy)
        event_bus.data_changed.emit()

        if speed > 0:
            QMessageBox.information(
                self,
                LanguageManager.tr("scn_msg_speed_res_title"),
                LanguageManager.tr("scn_msg_speed_res_body").format(speed=speed),
            )
        else:
            QMessageBox.warning(
                self,
                LanguageManager.tr("scn_msg_error_title"),
                LanguageManager.tr("scn_msg_speed_fail_body"),
            )

    def _populate_table(self, proxies):
        self.model.update_data(proxies)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_loaded").format(count=len(proxies))
        )
        self.ui.progress_bar.setMaximum(len(proxies))
        self.ui.progress_bar.setValue(0)
        self._refresh_ui_state()
        self.data_manager.load_groups()

    def _populate_groups(self, groups):
        current = self.ui.cmb_group.currentData()
        self.ui.cmb_group.blockSignals(True)
        self.ui.cmb_group.clear()
        self.ui.cmb_group.addItem(LanguageManager.tr("scn_cmb_all_archives"), "")
        for g in groups:
            if g:
                self.ui.cmb_group.addItem(f"📂 {g}", g)

        idx = self.ui.cmb_group.findData(current)
        if idx >= 0:
            self.ui.cmb_group.setCurrentIndex(idx)
        self.ui.cmb_group.blockSignals(False)

        self._last_group_data = self.ui.cmb_group.currentData()

    def _show_error(self, err_msg):
        QMessageBox.critical(self, LanguageManager.tr("scn_msg_error_title"), err_msg)

    def safe_refresh_data(self):
        if (
            self.scan_manager.is_running
            or self.speed_manager.is_running
            or self.menu_handler.action_running
        ):
            return
        self.data_manager.refresh(self.ui.cmb_group.currentData())

    def _on_group_changed(self, index):
        if (
            self.scan_manager.is_running
            or self.speed_manager.is_running
            or self.menu_handler.action_running
        ):
            QMessageBox.warning(
                self,
                LanguageManager.tr("scn_msg_scan_running_title"),
                LanguageManager.tr("scn_msg_scan_running_body"),
            )
            self.ui.cmb_group.blockSignals(True)
            idx = self.ui.cmb_group.findData(self._last_group_data)
            if idx >= 0:
                self.ui.cmb_group.setCurrentIndex(idx)
            self.ui.cmb_group.blockSignals(False)
            return

        self._last_group_data = self.ui.cmb_group.currentData()
        self.data_manager.refresh(self._last_group_data)

    def apply_adv_filters(self):
        status_idx = self.ui.cmb_status.currentIndex()
        status = self.ui.cmb_status.currentText() if status_idx > 0 else ""
        protocol_idx = self.ui.cmb_protocol.currentIndex()
        protocol = self.ui.cmb_protocol.currentText() if protocol_idx > 0 else ""
        ip_idx = self.ui.cmb_ip_filter.currentIndex()
        ip_type = self.ui.cmb_ip_filter.currentText() if ip_idx > 0 else ""
        search_txt = self.ui.txt_search.text().strip()

        self.proxy_model.set_status_filter(status)
        self.proxy_model.set_protocol_filter(protocol)
        self.proxy_model.set_search_text(search_txt)
        self.proxy_model.set_ip_type_filter(ip_type)
        self._update_button_states()

    def _get_selected_proxies(self):
        selected_indexes = self.ui.table_view.selectionModel().selectedRows()
        selected = []
        for idx in selected_indexes:
            if not idx.isValid():
                continue
            source_idx = self.proxy_model.mapToSource(idx)
            if not source_idx.isValid():
                continue
            selected.append(self.model.proxies[source_idx.row()])
        return selected

    def _update_button_states(self):
        has_selection = len(self.ui.table_view.selectionModel().selectedRows()) > 0
        is_busy = (
            self.scan_manager.is_running
            or self.speed_manager.is_running
            or self.menu_handler.action_running
            or self.data_manager.is_loading
        )
        self.ui.btn_scan_selected.setEnabled(has_selection and not is_busy)

    def _broadcast_lock(self, is_locked):
        group_name = self.ui.cmb_group.currentData()
        event_bus.scan_lock_changed.emit(
            is_locked, str(group_name) if group_name else ""
        )

    def retranslate_ui(self):
        self.ui.lbl_archive.setText(LanguageManager.tr("scn_lbl_archive"))
        self.ui.btn_refresh.setText(LanguageManager.tr("scn_btn_refresh"))
        self.ui.btn_load_untested.setText(LanguageManager.tr("scn_btn_load_untested"))
        self.ui.btn_load_all.setText(LanguageManager.tr("scn_btn_load_all"))
        self.ui.lbl_concurrent.setText(LanguageManager.tr("scn_lbl_concurrent"))
        self.ui.lbl_timeout.setText(LanguageManager.tr("scn_lbl_timeout"))
        self.ui.lbl_speed_size.setText(LanguageManager.tr("scn_lbl_speed_size"))
        self.ui.btn_scan_selected.setText(LanguageManager.tr("scn_btn_scan_sel"))
        self.ui.btn_start.setText(LanguageManager.tr("scn_btn_scan_all"))
        self.ui.btn_stop.setText(LanguageManager.tr("scn_btn_stop"))
        self.ui.btn_speed_valid.setText(LanguageManager.tr("scn_btn_speed_valid"))
        self.ui.filter_group.setTitle(LanguageManager.tr("scn_group_filter"))
        self.ui.txt_search.setPlaceholderText(
            LanguageManager.tr("scn_placeholder_search")
        )
        self.ui.lbl_search.setText(LanguageManager.tr("scn_lbl_search"))
        self.ui.lbl_status_filter.setText(LanguageManager.tr("scn_lbl_status"))
        self.ui.lbl_protocol_filter.setText(LanguageManager.tr("scn_lbl_protocol"))
        self.ui.lbl_ip_filter.setText(LanguageManager.tr("scn_lbl_ip_filter"))
        self.ui.chk_deep_scan.setText(LanguageManager.tr("scn_chk_deep_scan"))
        self.ui.rb_probe_http.setText(LanguageManager.tr("scn_probe_http"))
        self.ui.rb_probe_https.setText(LanguageManager.tr("scn_probe_https"))

        if self.ui.cmb_group.count() > 0:
            self.ui.cmb_group.setItemText(0, LanguageManager.tr("scn_cmb_all_archives"))
        if self.ui.cmb_status.count() > 0:
            self.ui.cmb_status.setItemText(
                0, LanguageManager.tr("scn_cmb_all_statuses")
            )
        if self.ui.cmb_protocol.count() > 0:
            self.ui.cmb_protocol.setItemText(
                0, LanguageManager.tr("scn_cmb_all_protocols")
            )
        if self.ui.cmb_ip_filter.count() > 0:
            self.ui.cmb_ip_filter.setItemText(0, LanguageManager.tr("scn_cmb_all_ips"))

        status_text = self.ui.lbl_status.text()
        if not status_text or status_text in ["آماده", "Ready"]:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_ready"))

        if self.ui.cmb_speed_size.count() == 0:
            self.ui.cmb_speed_size.addItem(LanguageManager.tr("scn_speed_200"), 200)
            self.ui.cmb_speed_size.addItem(LanguageManager.tr("scn_speed_500"), 500)
            self.ui.cmb_speed_size.addItem(LanguageManager.tr("scn_speed_2000"), 2000)
            self.ui.cmb_speed_size.setCurrentIndex(1)
        else:
            self.ui.cmb_speed_size.setItemText(0, LanguageManager.tr("scn_speed_200"))
            self.ui.cmb_speed_size.setItemText(1, LanguageManager.tr("scn_speed_500"))
            self.ui.cmb_speed_size.setItemText(2, LanguageManager.tr("scn_speed_2000"))
