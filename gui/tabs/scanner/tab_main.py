from PySide6.QtWidgets import (
    QWidget,
    QMessageBox,
    QInputDialog,
    QMenu,
    QApplication,
    QHeaderView,
)
from gui.workers import AsyncTaskWorker, ScanWorker, SpeedTestWorker
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from gui.widgets.qr_dialog import QRDialog
from gui.language_manager import LanguageManager
from .ui_layout import ScannerUiLayout
from gui.event_bus import event_bus

class ScannerTab(QWidget):
    def __init__(self, repository, scan_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service
        self.scan_worker = None
        self.speed_worker = None
        self.last_load_type = "all"
        self.last_selected_group_idx = 0
        self.is_deep_scan_phase = False
        self.is_stopped = False
        self.current_scan_list = []

        self.ui = ScannerUiLayout()
        self.ui.setup_ui(self)

        self.model = ProxyTableModel([])
        self.proxy_model = ProxySortModel()
        self.proxy_model.setSourceModel(self.model)
        self.ui.table_view.setModel(self.proxy_model)

        header = self.ui.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self._connect_signals()

        self._load_groups()
        self.retranslate_ui()

    def _connect_signals(self):

        self.ui.btn_refresh.clicked.connect(self.refresh_data)
        self.ui.btn_load_untested.clicked.connect(self.load_untested)
        self.ui.btn_load_all.clicked.connect(self.load_all)
        self.ui.btn_scan_selected.clicked.connect(self.start_scan_selected)
        self.ui.btn_start.clicked.connect(self.start_scan_all)
        self.ui.btn_stop.clicked.connect(self.stop_scan)
        self.ui.cmb_group.currentIndexChanged.connect(self.on_group_changed)
        self.ui.btn_speed_valid.clicked.connect(self.start_speed_test_valid)

        self.ui.txt_search.textChanged.connect(self.apply_adv_filters)
        self.ui.cmb_status.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_protocol.currentIndexChanged.connect(self.apply_adv_filters)

        self.ui.table_view.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )
        self.ui.table_view.customContextMenuRequested.connect(self.show_context_menu)

        event_bus.data_changed.connect(self.safe_refresh_data)

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

        self.ui.chk_deep_scan.setText(LanguageManager.tr("scn_chk_deep_scan"))

    def _broadcast_lock(self, is_locked):

        group_name = self.ui.cmb_group.currentData()
        event_bus.scan_lock_changed.emit(
            is_locked, str(group_name) if group_name else ""
        )

    def start_speed_test_valid(self):

        valid_proxies = [p for p in self.model.proxies if p.status == "Valid"]
        if not valid_proxies:
            QMessageBox.warning(
                self,
                LanguageManager.tr("scn_msg_no_valid_title"),
                LanguageManager.tr("scn_msg_no_valid_body"),
            )
            return
        self._test_speed_multiple(valid_proxies)

    def _load_groups(self):
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
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
        self.last_selected_group_idx = self.ui.cmb_group.currentIndex()

    def on_selection_changed(self):
        has_selection = len(self.ui.table_view.selectionModel().selectedRows()) > 0
        self.ui.btn_scan_selected.setEnabled(
            has_selection and not (self.scan_worker and self.scan_worker.isRunning())
        )

    def refresh_data(self):
        if self.last_load_type == "untested":
            self.load_untested()
        else:
            self.load_all()

    def safe_refresh_data(self):

        if self.scan_worker and self.scan_worker.isRunning():
            return
        if self.speed_worker and self.speed_worker.isRunning():
            return
        self.refresh_data()

    def on_group_changed(self, index):

        is_running = (self.scan_worker and self.scan_worker.isRunning()) or (
            self.speed_worker and self.speed_worker.isRunning()
        )

        if is_running:

            QMessageBox.warning(
                self,
                LanguageManager.tr("scn_msg_scan_running_title"),
                LanguageManager.tr("scn_msg_scan_running_body"),
            )

            self.ui.cmb_group.blockSignals(True)
            self.ui.cmb_group.setCurrentIndex(self.last_selected_group_idx)
            self.ui.cmb_group.blockSignals(False)
            return

        self.last_selected_group_idx = index
        self.refresh_data()

    def _set_loading_state(self, is_loading):
        if is_loading:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_loading"))
        self.ui.btn_refresh.setEnabled(not is_loading)
        self.ui.btn_load_untested.setEnabled(not is_loading)
        self.ui.btn_load_all.setEnabled(not is_loading)
        self.ui.cmb_group.setEnabled(not is_loading)

    def load_untested(self):
        self.last_load_type = "untested"
        self._set_loading_state(True)
        target_group = self.ui.cmb_group.currentData()
        self.worker = AsyncTaskWorker(self.repository.get_all())
        self.worker.finished_signal.connect(
            lambda proxies: self._on_data_loaded(
                [
                    p
                    for p in proxies
                    if p.status == "Untested"
                    and (not target_group or p.group_name == target_group)
                ]
            )
        )
        self.worker.start()

    def load_all(self):
        self.last_load_type = "all"
        self._set_loading_state(True)
        target_group = self.ui.cmb_group.currentData()
        self.worker = AsyncTaskWorker(self.repository.get_all())
        self.worker.finished_signal.connect(
            lambda proxies: self._on_data_loaded(
                [
                    p
                    for p in proxies
                    if (not target_group or p.group_name == target_group)
                ]
            )
        )
        self.worker.start()

    def _on_data_loaded(self, proxies):
        self._set_loading_state(False)
        self.model.update_data(proxies)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_loaded").format(count=len(proxies))
        )
        self.ui.progress_bar.setMaximum(len(proxies))
        self.ui.progress_bar.setValue(0)
        self.ui.btn_start.setEnabled(len(proxies) > 0)
        self.on_selection_changed()
        self._load_groups()

    def start_scan_selected(self):
        selected_indexes = self.ui.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return
        selected_proxies = []
        for index in selected_indexes:
            source_index = self.proxy_model.mapToSource(index)
            selected_proxies.append(self.model.proxies[source_index.row()])
        self._execute_scan(selected_proxies)

    def start_scan_all(self):
        self._execute_scan(self.model.proxies)

    def _execute_scan(self, proxies_to_scan, is_deep_scan_phase=False):
        if not proxies_to_scan:
            return

        self.is_stopped = False

        self.is_deep_scan_phase = is_deep_scan_phase
        if not is_deep_scan_phase:

            self.current_scan_list = proxies_to_scan
            self._broadcast_lock(True)

        self.ui.btn_load_untested.setEnabled(False)
        self.ui.btn_load_all.setEnabled(False)
        self.ui.btn_refresh.setEnabled(False)
        self.ui.btn_start.setEnabled(False)
        self.ui.btn_scan_selected.setEnabled(False)
        self.ui.btn_stop.setEnabled(True)
        self.ui.spin_concurrent.setEnabled(False)
        self.ui.spin_timeout.setEnabled(False)
        self.ui.cmb_group.setEnabled(False)
        self.ui.cmb_speed_size.setEnabled(False)
        self.ui.chk_deep_scan.setEnabled(False)
        self.ui.btn_scan_selected.setEnabled(False)
        self.ui.btn_speed_valid.setEnabled(False)

        self.scanned_count = 0
        self.total_to_scan = len(proxies_to_scan)

        self.ui.lbl_status.show()
        self.ui.progress_bar.show()
        self.ui.lbl_status.setStyleSheet("")

        self.ui.progress_bar.setMaximum(self.total_to_scan)
        self.ui.progress_bar.setValue(0)

        if is_deep_scan_phase:
            self.ui.lbl_status.setText(
                LanguageManager.tr("scn_status_deep_start").format(
                    count=self.total_to_scan
                )
            )
            self.ui.lbl_status.setStyleSheet("color: #8c7ae6; font-weight: bold;")
        else:
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_scan_start"))

        concurrent = self.ui.spin_concurrent.value()
        timeout = self.ui.spin_timeout.value()
        self.scan_worker = ScanWorker(
            self.scan_service,
            proxies_to_scan,
            concurrent_scans=concurrent,
            timeout_seconds=timeout,
        )
        self.scan_worker.progress_signal.connect(self.on_scan_progress)
        self.scan_worker.finished_signal.connect(self.on_scan_finished)
        self.scan_worker.error_signal.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scan_progress(self, proxy, meta):
        self.scanned_count += 1
        self.ui.progress_bar.setValue(self.scanned_count)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_scanning").format(
                current=self.scanned_count, total=self.total_to_scan, ping=proxy.ping
            )
        )
        self.model.update_proxy(proxy)

    def on_scan_finished(self):

        if not self.is_stopped:

            if self.ui.chk_deep_scan.isChecked() and not self.is_deep_scan_phase:

                failed_proxies = [
                    p
                    for p in self.current_scan_list
                    if p.status in ["Timeout", "Invalid", "Error"]
                ]

                if failed_proxies:

                    self._execute_scan(failed_proxies, is_deep_scan_phase=True)
                    return

        self.is_deep_scan_phase = False
        self._broadcast_lock(False)
        self.ui.lbl_status.setText(LanguageManager.tr("scn_status_scan_done"))
        self.ui.lbl_status.setStyleSheet("")
        self._reset_buttons()
        event_bus.data_changed.emit()

    def on_scan_error(self, err_msg):
        self._broadcast_lock(False)
        self.ui.lbl_status.setText(LanguageManager.tr("scn_status_scan_error"))
        QMessageBox.critical(
            self, LanguageManager.tr("scn_msg_error_title"), str(err_msg)
        )
        self._reset_buttons()

    def stop_scan(self):
        is_scanning = self.scan_worker and self.scan_worker.isRunning()
        is_speeding = self.speed_worker and self.speed_worker.isRunning()

        if is_scanning or is_speeding:
            self.is_stopped = True
            self.ui.btn_stop.setEnabled(False)
            self.ui.lbl_status.setText(LanguageManager.tr("scn_status_stopping"))

            self.scan_service.cancel()

    def _reset_buttons(self):
        self.ui.btn_load_untested.setEnabled(True)
        self.ui.btn_load_all.setEnabled(True)
        self.ui.btn_refresh.setEnabled(True)
        self.ui.cmb_group.setEnabled(True)
        self.ui.btn_start.setEnabled(len(self.model.proxies) > 0)
        self.ui.btn_speed_valid.setEnabled(len(self.model.proxies) > 0)
        self.on_selection_changed()
        self.ui.btn_stop.setEnabled(False)
        self.ui.spin_concurrent.setEnabled(True)
        self.ui.spin_timeout.setEnabled(True)
        self.ui.cmb_speed_size.setEnabled(True)
        self.ui.chk_deep_scan.setEnabled(True)

    def show_context_menu(self, pos):

        is_scanning = self.scan_worker and self.scan_worker.isRunning()
        is_speeding = self.speed_worker and self.speed_worker.isRunning()
        if is_scanning or is_speeding:
            return

        index = self.ui.table_view.indexAt(pos)
        if not index.isValid():
            return
        selected_indexes = self.ui.table_view.selectionModel().selectedRows()
        selected_proxies = []
        for idx in selected_indexes:
            source_index = self.proxy_model.mapToSource(idx)
            selected_proxies.append(self.model.proxies[source_index.row()])

        proxy = selected_proxies[0]
        menu = QMenu(self)

        if len(selected_proxies) == 1:
            action_copy = menu.addAction(LanguageManager.tr("scn_ctx_copy"))
            action_qr = menu.addAction(LanguageManager.tr("scn_ctx_qr"))
        else:
            action_copy = None
            action_qr = None

        action_speed = menu.addAction(
            LanguageManager.tr("scn_ctx_speed").format(count=len(selected_proxies))
        )
        menu.addSeparator()
        action_move = menu.addAction(
            LanguageManager.tr("scn_ctx_move").format(count=len(selected_proxies))
        )
        action_delete = menu.addAction(
            LanguageManager.tr("scn_ctx_delete").format(count=len(selected_proxies))
        )

        action = menu.exec(self.ui.table_view.viewport().mapToGlobal(pos))

        if action_copy and action == action_copy:
            QApplication.clipboard().setText(proxy.raw_url)
            QMessageBox.information(
                self,
                LanguageManager.tr("scn_msg_copied_title"),
                LanguageManager.tr("scn_msg_copied_body"),
            )
        elif action_qr and action == action_qr:
            dialog = QRDialog(proxy.remark or "Config", proxy.raw_url, self)
            dialog.exec()
        elif action == action_speed:
            self._test_speed_multiple(selected_proxies)
        elif action == action_move:
            self._move_multiple_proxies(selected_proxies)
        elif action == action_delete:
            self._delete_multiple_proxies(selected_proxies)

    def _test_speed_multiple(self, proxies):
        self.speed_test_total = len(proxies)
        self.speed_test_current = 0
        self.is_stopped = False
        self._broadcast_lock(True)

        self.ui.btn_load_untested.setEnabled(False)
        self.ui.btn_load_all.setEnabled(False)
        self.ui.btn_refresh.setEnabled(False)
        self.ui.btn_start.setEnabled(False)
        self.ui.btn_scan_selected.setEnabled(False)
        self.ui.btn_speed_valid.setEnabled(False)
        self.ui.cmb_group.setEnabled(False)
        self.ui.cmb_speed_size.setEnabled(False)
        self.ui.btn_stop.setEnabled(
            True
        )

        self.ui.lbl_status.show()
        self.ui.progress_bar.show()
        self.ui.progress_bar.setMaximum(self.speed_test_total)
        self.ui.progress_bar.setValue(0)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_speed_init").format(
                total=self.speed_test_total
            )
        )
        self.ui.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")

        selected_size = self.ui.cmb_speed_size.currentData()
        self.speed_worker = SpeedTestWorker(
            self.scan_service, proxies, max_size_kb=selected_size
        )
        self.speed_worker.progress_signal.connect(self._on_speed_progress)
        self.speed_worker.finished_signal.connect(self._on_speed_finished)
        self.speed_worker.start()

    def _on_speed_progress(self, proxy):
        self.speed_test_current += 1
        self.ui.progress_bar.setValue(self.speed_test_current)
        self.ui.lbl_status.setText(
            LanguageManager.tr("scn_status_speed_prog").format(
                current=self.speed_test_current, total=self.speed_test_total
            )
        )
        self.model.update_proxy(proxy)

    def _on_speed_finished(self):
        self._broadcast_lock(False)
        self.ui.lbl_status.setText(LanguageManager.tr("scn_status_speed_done"))
        self.ui.lbl_status.setStyleSheet("color: #44bd32; font-weight: bold;")

        if not self.is_stopped:
            QMessageBox.information(
                self,
                LanguageManager.tr("scn_msg_speed_done_title"),
                LanguageManager.tr("scn_msg_speed_done_body"),
            )

        self.ui.lbl_status.setStyleSheet("")
        self._reset_buttons()
        event_bus.data_changed.emit()

    def _move_multiple_proxies(self, proxies):
        ids = [p.id for p in proxies if p.id]
        groups = [
            self.ui.cmb_group.itemData(i) for i in range(1, self.ui.cmb_group.count())
        ]
        if "Default" not in groups:
            groups.insert(0, "Default")

        new_group, ok = QInputDialog.getItem(
            self,
            LanguageManager.tr("scn_msg_move_title"),
            LanguageManager.tr("scn_msg_move_multi_prompt").format(count=len(ids)),
            groups,
            0,
            True,
        )
        if ok and new_group.strip():
            self.worker_action = AsyncTaskWorker(
                self.repository.update_group_many(ids, new_group.strip())
            )
            self.worker_action.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_action.start()

    def _delete_multiple_proxies(self, proxies):
        ids = [p.id for p in proxies if p.id]
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("scn_msg_del_title"),
            LanguageManager.tr("scn_msg_del_multi_prompt").format(count=len(ids)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.worker_action = AsyncTaskWorker(self.repository.delete_many(ids))
            self.worker_action.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_action.start()

    def _move_single_proxy(self, proxy):
        groups = [
            self.ui.cmb_group.itemData(i) for i in range(1, self.ui.cmb_group.count())
        ]
        if "Default" not in groups:
            groups.insert(0, "Default")

        new_group, ok = QInputDialog.getItem(
            self,
            LanguageManager.tr("scn_msg_move_title"),
            LanguageManager.tr("scn_msg_move_single_prompt").format(
                remark=proxy.remark
            ),
            groups,
            0,
            True,
        )
        if ok and new_group.strip():
            self.worker_action = AsyncTaskWorker(
                self.repository.update_group_many([proxy.id], new_group.strip())
            )
            self.worker_action.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_action.start()

    def _delete_single_proxy(self, proxy):
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("scn_msg_del_title"),
            LanguageManager.tr("scn_msg_del_single_prompt").format(remark=proxy.remark),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.worker_action = AsyncTaskWorker(
                self.repository.delete_many([proxy.id])
            )
            self.worker_action.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_action.start()

    def apply_adv_filters(self):
        status_idx = self.ui.cmb_status.currentIndex()
        status = self.ui.cmb_status.currentText() if status_idx > 0 else ""
        protocol_idx = self.ui.cmb_protocol.currentIndex()
        protocol = self.ui.cmb_protocol.currentText() if protocol_idx > 0 else ""
        search_txt = self.ui.txt_search.text().strip()

        self.proxy_model.set_status_filter(status)
        self.proxy_model.set_protocol_filter(protocol)
        self.proxy_model.set_search_text(search_txt)
        self.on_selection_changed()

    def _test_proxy_speed(self, proxy):
        QMessageBox.information(
            self,
            LanguageManager.tr("scn_msg_speed_test_title"),
            LanguageManager.tr("scn_msg_speed_test_body"),
        )
        selected_size = self.ui.cmb_speed_size.currentData()
        self.worker_speed = AsyncTaskWorker(
            self.scan_service.test_speed(proxy, max_size_kb=selected_size)
        )
        self.worker_speed.finished_signal.connect(
            lambda speed: self._on_speed_tested(proxy, speed)
        )
        self.worker_speed.start()

    def _on_speed_tested(self, proxy, speed):
        self.worker_save = AsyncTaskWorker(self.repository.save(proxy))
        self.worker_save.finished_signal.connect(
            lambda _: event_bus.data_changed.emit()
        )
        self.worker_save.start()
        self.model.update_proxy(proxy)
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
