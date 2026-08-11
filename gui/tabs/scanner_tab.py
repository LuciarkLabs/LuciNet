from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QHeaderView,
    QLabel,
    QProgressBar,
    QMessageBox,
    QSpinBox,
    QComboBox,
    QLineEdit,
    QGroupBox,
)
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker, ScanWorker
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from PySide6.QtWidgets import QApplication, QMenu, QInputDialog
from gui.widgets.qr_dialog import QRDialog
from gui.workers import AsyncTaskWorker, ScanWorker, SpeedTestWorker
from gui.language_manager import LanguageManager

class ScannerTab(QWidget):
    def __init__(self, repository, scan_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service
        self.model = ProxyTableModel([])
        self.scan_worker = None
        self.last_load_type = "all"
        self._setup_ui()
        self._load_groups()
        self.retranslate_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        self.lbl_archive = QLabel()
        toolbar.addWidget(self.lbl_archive)

        self.cmb_group = QComboBox()
        self.cmb_group.addItem("")
        self.cmb_group.setMinimumWidth(120)
        toolbar.addWidget(self.cmb_group)

        self.btn_refresh = QPushButton()
        self.btn_refresh.clicked.connect(self.refresh_data)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addSpacing(10)

        self.btn_load_untested = QPushButton()
        self.btn_load_untested.clicked.connect(self.load_untested)
        self.btn_load_all = QPushButton()
        self.btn_load_all.clicked.connect(self.load_all)

        safe_spinbox_style = """
            QSpinBox { padding-right: 25px; }
            QSpinBox::up-button, QSpinBox::down-button { width: 20px; }
        """

        self.spin_concurrent = QSpinBox()
        self.spin_concurrent.setRange(1, 1000)
        self.spin_concurrent.setValue(50)
        self.spin_concurrent.setMinimumWidth(90)
        self.spin_concurrent.setFixedHeight(32)
        self.spin_concurrent.setStyleSheet(safe_spinbox_style)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 60)
        self.spin_timeout.setValue(15)
        self.spin_timeout.setMinimumWidth(90)
        self.spin_timeout.setFixedHeight(32)
        self.spin_timeout.setStyleSheet(safe_spinbox_style)

        self.lbl_concurrent = QLabel()
        self.lbl_timeout = QLabel()

        self.lbl_speed_size = QLabel("حجم تست سرعت:")
        self.cmb_speed_size = QComboBox()
        self.cmb_speed_size.addItem(LanguageManager.tr("scn_speed_200"), 200)
        self.cmb_speed_size.addItem(LanguageManager.tr("scn_speed_500"), 500)
        self.cmb_speed_size.addItem(LanguageManager.tr("scn_speed_2000"), 2000)
        self.cmb_speed_size.setCurrentIndex(1)
        self.cmb_speed_size.setFixedHeight(32)

        toolbar.addWidget(self.btn_load_untested)
        toolbar.addWidget(self.btn_load_all)
        toolbar.addStretch()

        toolbar.addWidget(self.lbl_concurrent)
        toolbar.addWidget(self.spin_concurrent)

        toolbar.addWidget(self.lbl_timeout)
        toolbar.addWidget(self.spin_timeout)
        toolbar.addSpacing(10)

        toolbar.addWidget(self.lbl_speed_size)
        toolbar.addWidget(self.cmb_speed_size)
        toolbar.addSpacing(10)

        self.btn_scan_selected = QPushButton()
        self.btn_scan_selected.setStyleSheet(
            "background-color: #fbc531; color: #2f3640; font-weight: bold;"
        )
        self.btn_scan_selected.setEnabled(False)
        self.btn_scan_selected.clicked.connect(self.start_scan_selected)

        self.btn_start = QPushButton()
        self.btn_start.setStyleSheet(
            "background-color: #44bd32; color: white; font-weight: bold;"
        )
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_scan_all)

        self.btn_stop = QPushButton()
        self.btn_stop.setStyleSheet(
            "background-color: #e84118; color: white; font-weight: bold;"
        )
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_scan)

        toolbar.addWidget(self.btn_scan_selected)
        toolbar.addWidget(self.btn_start)
        toolbar.addWidget(self.btn_stop)
        layout.addLayout(toolbar)

        progress_layout = QHBoxLayout()
        self.lbl_status = QLabel()
        self.lbl_status.setMinimumWidth(250)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.lbl_status)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

        self.filter_group = QGroupBox()
        self.filter_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 30px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                top: 0px;
                padding: 4px 10px;
            }
        """)

        filter_layout = QHBoxLayout(self.filter_group)

        self.lbl_search = QLabel()
        self.txt_search = QLineEdit()
        self.txt_search.textChanged.connect(self.apply_adv_filters)

        self.lbl_status_filter = QLabel()
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(
            ["", "Valid", "Invalid", "Timeout", "Error", "Untested"]
        )
        self.cmb_status.currentIndexChanged.connect(self.apply_adv_filters)

        self.lbl_protocol_filter = QLabel()
        self.cmb_protocol = QComboBox()
        self.cmb_protocol.addItems(["", "vless", "vmess", "trojan", "ss"])
        self.cmb_protocol.currentIndexChanged.connect(self.apply_adv_filters)

        filter_layout.addWidget(self.lbl_search)
        filter_layout.addWidget(self.txt_search)
        filter_layout.addWidget(self.lbl_status_filter)
        filter_layout.addWidget(self.cmb_status)
        filter_layout.addWidget(self.lbl_protocol_filter)
        filter_layout.addWidget(self.cmb_protocol)

        layout.addWidget(self.filter_group)

        self.table_view = QTableView()
        self.proxy_model = ProxySortModel()
        self.proxy_model.setSourceModel(self.model)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_view.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table_view)

    def retranslate_ui(self):
        self.lbl_archive.setText(LanguageManager.tr("scn_lbl_archive"))
        self.btn_refresh.setText(LanguageManager.tr("scn_btn_refresh"))
        self.btn_load_untested.setText(LanguageManager.tr("scn_btn_load_untested"))
        self.btn_load_all.setText(LanguageManager.tr("scn_btn_load_all"))
        self.lbl_concurrent.setText(LanguageManager.tr("scn_lbl_concurrent"))
        self.lbl_timeout.setText(LanguageManager.tr("scn_lbl_timeout"))
        self.lbl_speed_size.setText(LanguageManager.tr("scn_lbl_speed_size"))
        self.btn_scan_selected.setText(LanguageManager.tr("scn_btn_scan_sel"))
        self.btn_start.setText(LanguageManager.tr("scn_btn_scan_all"))
        self.btn_stop.setText(LanguageManager.tr("scn_btn_stop"))

        self.filter_group.setTitle(LanguageManager.tr("scn_group_filter"))
        self.txt_search.setPlaceholderText(LanguageManager.tr("scn_placeholder_search"))
        self.lbl_search.setText(LanguageManager.tr("scn_lbl_search"))
        self.lbl_status_filter.setText(LanguageManager.tr("scn_lbl_status"))
        self.lbl_protocol_filter.setText(LanguageManager.tr("scn_lbl_protocol"))

        if self.cmb_group.count() > 0:
            self.cmb_group.setItemText(0, LanguageManager.tr("scn_cmb_all_archives"))
        if self.cmb_status.count() > 0:
            self.cmb_status.setItemText(0, LanguageManager.tr("scn_cmb_all_statuses"))
        if self.cmb_protocol.count() > 0:
            self.cmb_protocol.setItemText(
                0, LanguageManager.tr("scn_cmb_all_protocols")
            )

        status_text = self.lbl_status.text()
        if not status_text or status_text in ["آماده", "Ready"]:
            self.lbl_status.setText(LanguageManager.tr("scn_status_ready"))

        if hasattr(self, "cmb_speed_size") and self.cmb_speed_size.count() >= 3:
            self.cmb_speed_size.setItemText(0, LanguageManager.tr("scn_speed_200"))
            self.cmb_speed_size.setItemText(1, LanguageManager.tr("scn_speed_500"))
            self.cmb_speed_size.setItemText(2, LanguageManager.tr("scn_speed_2000"))

    def _load_groups(self):
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
        current = self.cmb_group.currentData()
        self.cmb_group.blockSignals(True)
        self.cmb_group.clear()
        self.cmb_group.addItem(LanguageManager.tr("scn_cmb_all_archives"), "")
        for g in groups:
            if g:
                self.cmb_group.addItem(g, g)
        idx = self.cmb_group.findData(current)
        if idx >= 0:
            self.cmb_group.setCurrentIndex(idx)
        self.cmb_group.blockSignals(False)

    def on_selection_changed(self):
        has_selection = len(self.table_view.selectionModel().selectedRows()) > 0
        self.btn_scan_selected.setEnabled(
            has_selection and not (self.scan_worker and self.scan_worker.isRunning())
        )

    def refresh_data(self):
        if self.last_load_type == "untested":
            self.load_untested()
        else:
            self.load_all()

    def _set_loading_state(self, is_loading):
        if is_loading:
            self.lbl_status.setText(LanguageManager.tr("scn_status_loading"))
        self.btn_refresh.setEnabled(not is_loading)
        self.btn_load_untested.setEnabled(not is_loading)
        self.btn_load_all.setEnabled(not is_loading)
        self.cmb_group.setEnabled(not is_loading)

    def load_untested(self):
        self.last_load_type = "untested"
        self._set_loading_state(True)
        target_group = self.cmb_group.currentData()
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
        target_group = self.cmb_group.currentData()
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
        self.lbl_status.setText(
            LanguageManager.tr("scn_status_loaded").format(count=len(proxies))
        )
        self.progress_bar.setMaximum(len(proxies))
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(len(proxies) > 0)
        self.on_selection_changed()
        self._load_groups()

    def start_scan_selected(self):
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return
        selected_proxies = []
        for index in selected_indexes:
            source_index = self.proxy_model.mapToSource(index)
            selected_proxies.append(self.model.proxies[source_index.row()])
        self._execute_scan(selected_proxies)

    def start_scan_all(self):
        self._execute_scan(self.model.proxies)

    def _execute_scan(self, proxies_to_scan):
        if not proxies_to_scan:
            return
        self.btn_load_untested.setEnabled(False)
        self.btn_load_all.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_scan_selected.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.spin_concurrent.setEnabled(False)
        self.spin_timeout.setEnabled(False)
        self.cmb_group.setEnabled(False)
        self.cmb_speed_size.setEnabled(False)

        self.scanned_count = 0
        self.total_to_scan = len(proxies_to_scan)

        self.lbl_status.show()
        self.progress_bar.show()
        self.lbl_status.setStyleSheet("")

        self.progress_bar.setMaximum(self.total_to_scan)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(LanguageManager.tr("scn_status_scan_start"))

        concurrent = self.spin_concurrent.value()
        timeout = self.spin_timeout.value()
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
        self.progress_bar.setValue(self.scanned_count)
        self.lbl_status.setText(
            LanguageManager.tr("scn_status_scanning").format(
                current=self.scanned_count, total=self.total_to_scan, ping=proxy.ping
            )
        )
        self.model.update_proxy(proxy)

    def on_scan_finished(self):
        self.lbl_status.setText(LanguageManager.tr("scn_status_scan_done"))
        self._reset_buttons()

    def on_scan_error(self, err_msg):
        self.lbl_status.setText(LanguageManager.tr("scn_status_scan_error"))
        QMessageBox.critical(
            self, LanguageManager.tr("scn_msg_error_title"), str(err_msg)
        )
        self._reset_buttons()

    def stop_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_service.cancel()
            self.lbl_status.setText(LanguageManager.tr("scn_status_stopping"))
            self.btn_stop.setEnabled(False)

    def _reset_buttons(self):
        self.btn_load_untested.setEnabled(True)
        self.btn_load_all.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.cmb_group.setEnabled(True)
        self.btn_start.setEnabled(len(self.model.proxies) > 0)
        self.on_selection_changed()
        self.btn_stop.setEnabled(False)
        self.spin_concurrent.setEnabled(True)
        self.spin_timeout.setEnabled(True)
        self.cmb_speed_size.setEnabled(True)

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        selected_indexes = self.table_view.selectionModel().selectedRows()
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

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))
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

        self.btn_load_untested.setEnabled(False)
        self.btn_load_all.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_scan_selected.setEnabled(False)
        self.cmb_group.setEnabled(False)
        self.cmb_speed_size.setEnabled(False)

        self.lbl_status.show()
        self.progress_bar.show()
        self.progress_bar.setMaximum(self.speed_test_total)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(
            LanguageManager.tr("scn_status_speed_init").format(
                total=self.speed_test_total
            )
        )
        self.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")

        selected_size = self.cmb_speed_size.currentData()
        self.speed_worker = SpeedTestWorker(
            self.scan_service, proxies, max_size_kb=selected_size
        )

        self.speed_worker.progress_signal.connect(self._on_speed_progress)
        self.speed_worker.finished_signal.connect(self._on_speed_finished)
        self.speed_worker.start()

    def _on_speed_progress(self, proxy):
        self.speed_test_current += 1
        self.progress_bar.setValue(self.speed_test_current)
        self.lbl_status.setText(
            LanguageManager.tr("scn_status_speed_prog").format(
                current=self.speed_test_current, total=self.speed_test_total
            )
        )
        self.model.update_proxy(proxy)

    def _on_speed_finished(self):
        self.lbl_status.setText(LanguageManager.tr("scn_status_speed_done"))
        self.lbl_status.setStyleSheet("color: #44bd32; font-weight: bold;")
        QMessageBox.information(
            self,
            LanguageManager.tr("scn_msg_speed_done_title"),
            LanguageManager.tr("scn_msg_speed_done_body"),
        )
        self.lbl_status.setStyleSheet("")
        self._reset_buttons()
        self.refresh_data()

    def _move_multiple_proxies(self, proxies):
        ids = [p.id for p in proxies if p.id]
        groups = [self.cmb_group.itemData(i) for i in range(1, self.cmb_group.count())]
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
            self.worker_action.finished_signal.connect(lambda _: self.refresh_data())
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
            self.worker_action.finished_signal.connect(lambda _: self.refresh_data())
            self.worker_action.start()

    def _move_single_proxy(self, proxy):
        groups = [self.cmb_group.itemData(i) for i in range(1, self.cmb_group.count())]
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
            self.worker_action.finished_signal.connect(lambda _: self.refresh_data())
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
            self.worker_action.finished_signal.connect(lambda _: self.refresh_data())
            self.worker_action.start()

    def apply_adv_filters(self):
        status_idx = self.cmb_status.currentIndex()
        status = self.cmb_status.currentText() if status_idx > 0 else ""
        protocol_idx = self.cmb_protocol.currentIndex()
        protocol = self.cmb_protocol.currentText() if protocol_idx > 0 else ""
        search_txt = self.txt_search.text().strip()
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

        selected_size = self.cmb_speed_size.currentData()
        self.worker_speed = AsyncTaskWorker(
            self.scan_service.test_speed(proxy, max_size_kb=selected_size)
        )

        self.worker_speed.finished_signal.connect(
            lambda speed: self._on_speed_tested(proxy, speed)
        )
        self.worker_speed.start()

    def _on_speed_tested(self, proxy, speed):
        self.worker_save = AsyncTaskWorker(self.repository.save(proxy))
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
