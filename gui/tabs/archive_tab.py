from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QHeaderView,
    QLabel,
    QComboBox,
    QMessageBox,
    QInputDialog,
    QMenu,
    QLineEdit,
    QGroupBox,
    QProgressBar,
)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker, ScanWorker, SpeedTestWorker
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from gui.widgets.qr_dialog import QRDialog
from gui.language_manager import LanguageManager

class ArchiveTab(QWidget):
    def __init__(self, repository, scan_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service
        self.model = ProxyTableModel([])
        self._setup_ui()
        self.load_data()
        self.retranslate_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        self.lbl_archive = QLabel()
        toolbar.addWidget(self.lbl_archive)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItem("")
        self.cmb_filter.currentIndexChanged.connect(self.on_filter_changed)
        toolbar.addWidget(self.cmb_filter)

        self.btn_new_group = QPushButton()
        self.btn_new_group.setStyleSheet("color: #44bd32; font-weight: bold;")
        self.btn_new_group.clicked.connect(self.create_new_group)
        toolbar.addWidget(self.btn_new_group)

        self.btn_rename_group = QPushButton()
        self.btn_rename_group.clicked.connect(self.rename_current_group)
        self.btn_delete_group = QPushButton()
        self.btn_delete_group.setStyleSheet("color: #e84118; font-weight: bold;")
        self.btn_delete_group.clicked.connect(self.delete_current_group)

        toolbar.addWidget(self.btn_rename_group)
        toolbar.addWidget(self.btn_delete_group)

        self.btn_tools = QPushButton()
        self.btn_tools.setStyleSheet("font-weight: bold;")
        tools_menu = QMenu(self)

        self.action_move = tools_menu.addAction("")
        self.action_move.triggered.connect(self.move_selected)
        tools_menu.addSeparator()

        self.action_dedup = tools_menu.addAction("")
        self.action_dedup.triggered.connect(self.remove_duplicates)
        tools_menu.addSeparator()

        self.action_del_sel = tools_menu.addAction("")
        self.action_del_sel.triggered.connect(self.delete_selected)
        self.action_del_inv = tools_menu.addAction("")
        self.action_del_inv.triggered.connect(self.delete_invalid)
        self.action_del_tout = tools_menu.addAction("")
        self.action_del_tout.triggered.connect(self.delete_timeout)

        self.btn_tools.setMenu(tools_menu)
        toolbar.addWidget(self.btn_tools)
        toolbar.addStretch()
        layout.addLayout(toolbar)

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

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table_view)

        bottom_layout = QHBoxLayout()

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("font-weight: bold;")
        bottom_layout.addWidget(self.lbl_count)

        bottom_layout.addSpacing(20)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")
        self.lbl_status.hide()
        bottom_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        bottom_layout.addWidget(self.progress_bar)

        bottom_layout.addStretch()

        self.btn_refresh = QPushButton()
        self.btn_refresh.clicked.connect(self.load_data)
        bottom_layout.addWidget(self.btn_refresh)

        layout.addLayout(bottom_layout)

    def retranslate_ui(self):

        self.lbl_archive.setText(LanguageManager.tr("arc_lbl_archive"))
        self.btn_new_group.setText(LanguageManager.tr("arc_btn_new_archive"))
        self.btn_rename_group.setText(LanguageManager.tr("arc_btn_rename"))
        self.btn_delete_group.setText(LanguageManager.tr("arc_btn_delete"))
        self.btn_tools.setText(LanguageManager.tr("arc_btn_tools"))

        self.action_move.setText(LanguageManager.tr("arc_menu_move"))
        self.action_dedup.setText(LanguageManager.tr("arc_menu_dedup"))
        self.action_del_sel.setText(LanguageManager.tr("arc_menu_del_sel"))
        self.action_del_inv.setText(LanguageManager.tr("arc_menu_del_inv"))
        self.action_del_tout.setText(LanguageManager.tr("arc_menu_del_tout"))

        self.filter_group.setTitle(LanguageManager.tr("arc_group_filter"))
        self.txt_search.setPlaceholderText(LanguageManager.tr("arc_placeholder_search"))
        self.lbl_search.setText(LanguageManager.tr("arc_lbl_search"))
        self.lbl_status_filter.setText(LanguageManager.tr("arc_lbl_status"))
        self.lbl_protocol_filter.setText(LanguageManager.tr("arc_lbl_protocol"))

        if self.cmb_filter.count() > 0:
            self.cmb_filter.setItemText(0, LanguageManager.tr("arc_cmb_all_archives"))
        if self.cmb_status.count() > 0:
            self.cmb_status.setItemText(0, LanguageManager.tr("arc_cmb_all_statuses"))
        if self.cmb_protocol.count() > 0:
            self.cmb_protocol.setItemText(
                0, LanguageManager.tr("arc_cmb_all_protocols")
            )

        self.update_visible_count()

        if self.btn_refresh.isEnabled():
            self.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        else:
            self.btn_refresh.setText(LanguageManager.tr("arc_btn_loading"))

        status_text = self.lbl_status.text()
        if status_text in ["آماده", "Ready"]:
            self.lbl_status.setText(LanguageManager.tr("arc_status_ready"))

    def on_filter_changed(self):
        group = self.cmb_filter.currentData()
        self.proxy_model.set_group_filter(group)
        is_specific_group = bool(group)
        self.btn_rename_group.setEnabled(is_specific_group)
        self.btn_delete_group.setEnabled(is_specific_group)
        self.update_visible_count()

    def apply_adv_filters(self):
        status_idx = self.cmb_status.currentIndex()
        status = self.cmb_status.currentText() if status_idx > 0 else ""

        protocol_idx = self.cmb_protocol.currentIndex()
        protocol = self.cmb_protocol.currentText() if protocol_idx > 0 else ""

        search_txt = self.txt_search.text().strip()

        self.proxy_model.set_status_filter(status)
        self.proxy_model.set_protocol_filter(protocol)
        self.proxy_model.set_search_text(search_txt)

        self.update_visible_count()

    def update_visible_count(self):
        visible_count = self.proxy_model.rowCount()
        self.lbl_count.setText(
            LanguageManager.tr("arc_lbl_count").format(count=visible_count)
        )

    def create_new_group(self):
        new_name, ok = QInputDialog.getText(
            self,
            LanguageManager.tr("arc_msg_new_title"),
            LanguageManager.tr("arc_msg_new_prompt"),
        )
        if ok and new_name.strip():
            new_name = new_name.strip()
            existing_groups = [
                self.cmb_filter.itemData(i) for i in range(self.cmb_filter.count())
            ]
            if new_name not in existing_groups:
                self.cmb_filter.addItem(new_name, new_name)

            idx = self.cmb_filter.findData(new_name)
            if idx >= 0:
                self.cmb_filter.setCurrentIndex(idx)

            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_created_title"),
                LanguageManager.tr("arc_msg_created_body").format(name=new_name),
            )

    def rename_current_group(self):
        current_group = self.cmb_filter.currentData()
        if not current_group:
            return
        new_name, ok = QInputDialog.getText(
            self,
            LanguageManager.tr("arc_msg_rename_title"),
            LanguageManager.tr("arc_msg_rename_prompt").format(name=current_group),
        )
        if ok and new_name.strip() and new_name.strip() != current_group:
            self.worker_rename = AsyncTaskWorker(
                self.repository.rename_group(current_group, new_name.strip())
            )
            self.worker_rename.finished_signal.connect(lambda _: self.load_data())
            self.worker_rename.start()

    def delete_current_group(self):
        current_group = self.cmb_filter.currentData()
        if not current_group:
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            LanguageManager.tr("arc_msg_delete_body").format(name=current_group),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.worker_delete = AsyncTaskWorker(
                self.repository.delete_group(current_group)
            )
            self.worker_delete.finished_signal.connect(lambda _: self.load_data())
            self.worker_delete.start()

    def get_selected_ids(self):
        selected_indexes = self.table_view.selectionModel().selectedRows()
        ids = []
        for index in selected_indexes:
            source_index = self.proxy_model.mapToSource(index)
            proxy = self.model.proxies[source_index.row()]
            if proxy.id:
                ids.append(proxy.id)
        return ids

    def move_selected(self):
        ids = self.get_selected_ids()
        if not ids:
            QMessageBox.warning(
                self,
                LanguageManager.tr("arc_msg_error_title"),
                LanguageManager.tr("arc_msg_no_selection"),
            )
            return

        groups = [
            self.cmb_filter.itemData(i) for i in range(1, self.cmb_filter.count())
        ]
        if "Default" not in groups:
            groups.insert(0, "Default")

        new_group, ok = QInputDialog.getItem(
            self,
            LanguageManager.tr("arc_msg_move_title"),
            LanguageManager.tr("arc_msg_move_prompt").format(count=len(ids)),
            groups,
            0,
            True,
        )
        if ok and new_group.strip():
            self.worker_action = AsyncTaskWorker(
                self.repository.update_group_many(ids, new_group.strip())
            )
            self.worker_action.finished_signal.connect(
                lambda count: self._on_action_finished(
                    LanguageManager.tr("arc_msg_move_success").format(count=count)
                )
            )
            self.worker_action.start()

    def delete_selected(self):
        ids = self.get_selected_ids()
        if not ids:
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            LanguageManager.tr("arc_msg_del_sel_body").format(count=len(ids)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._execute_delete(ids)

    def delete_invalid(self):
        current_group = self.cmb_filter.currentData()
        ids = [
            p.id
            for p in self.model.proxies
            if p.status in ("Invalid", "Error")
            and (not current_group or p.group_name == current_group)
            and p.id
        ]
        if not ids:
            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_clean_title"),
                LanguageManager.tr("arc_msg_no_invalid"),
            )
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            LanguageManager.tr("arc_msg_del_inv_body").format(count=len(ids)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._execute_delete(ids)

    def delete_timeout(self):
        current_group = self.cmb_filter.currentData()
        ids = [
            p.id
            for p in self.model.proxies
            if p.status == "Timeout"
            and (not current_group or p.group_name == current_group)
            and p.id
        ]
        if not ids:
            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_clean_title"),
                LanguageManager.tr("arc_msg_no_timeout"),
            )
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            LanguageManager.tr("arc_msg_del_tout_body").format(count=len(ids)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._execute_delete(ids)

    def remove_duplicates(self):
        current_group = self.cmb_filter.currentData()
        proxies_to_check = [
            p
            for p in self.model.proxies
            if not current_group or p.group_name == current_group
        ]

        if not proxies_to_check:
            return

        sorted_proxies = sorted(
            proxies_to_check,
            key=lambda x: (
                0 if x.status == "Valid" else 1,
                x.ping if x.ping > 0 else float("inf"),
            ),
        )

        seen_signatures = set()
        to_delete_ids = []

        for p in sorted_proxies:
            signature = (
                p.protocol.lower(),
                p.server.lower(),
                p.port,
                p.uuid_pwd,
                p.network.lower() if p.network else "",
                p.security.lower() if p.security else "",
                p.path.strip() if p.path else "",
                p.sni.lower() if p.sni else "",
                p.pbk.strip() if p.pbk else "",
            )
            if signature in seen_signatures:
                if p.id:
                    to_delete_ids.append(p.id)
            else:
                seen_signatures.add(signature)

        if not to_delete_ids:
            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_dedup_title"),
                LanguageManager.tr("arc_msg_no_dedup"),
            )
            return

        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_del_dedup_title"),
            LanguageManager.tr("arc_msg_del_dedup_body").format(
                count=len(to_delete_ids)
            ),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._execute_delete(to_delete_ids)

    def _execute_delete(self, ids):
        self.worker_action = AsyncTaskWorker(self.repository.delete_many(ids))
        self.worker_action.finished_signal.connect(
            lambda count: self._on_action_finished(
                LanguageManager.tr("arc_msg_del_success").format(count=count)
            )
        )
        self.worker_action.start()

    def _on_action_finished(self, msg):
        QMessageBox.information(self, LanguageManager.tr("arc_msg_op_success"), msg)
        self.load_data()

    def load_data(self):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText(LanguageManager.tr("arc_btn_loading"))
        self.worker = AsyncTaskWorker(self.repository.get_all())
        self.worker.finished_signal.connect(self._on_data_loaded)
        self.worker.error_signal.connect(self._on_data_error)
        self.worker.start()

    def _on_data_loaded(self, proxies):
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        self.model.update_data(proxies)

        current_filter = self.cmb_filter.currentData()
        groups = sorted(list(set(p.group_name for p in proxies)))

        if current_filter and current_filter not in groups:
            groups.append(current_filter)

        self.cmb_filter.blockSignals(True)
        self.cmb_filter.clear()
        self.cmb_filter.addItem(LanguageManager.tr("arc_cmb_all_archives"), "")
        for g in groups:
            if g:
                self.cmb_filter.addItem(g, g)

        index = self.cmb_filter.findData(current_filter)
        if index >= 0:
            self.cmb_filter.setCurrentIndex(index)
        else:
            self.cmb_filter.setCurrentIndex(0)
        self.cmb_filter.blockSignals(False)

        self.on_filter_changed()

    def _on_data_error(self, err_msg):
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        self.lbl_status.show()
        self.lbl_status.setText(LanguageManager.tr("arc_status_db_error"))
        self.lbl_status.setStyleSheet("color: red;")

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
            action_copy = menu.addAction(LanguageManager.tr("arc_ctx_copy"))
            action_qr = menu.addAction(LanguageManager.tr("arc_ctx_qr"))
        else:
            action_copy = None
            action_qr = None

        action_speed = menu.addAction(
            LanguageManager.tr("arc_ctx_speed").format(count=len(selected_proxies))
        )
        menu.addSeparator()
        action_move = menu.addAction(
            LanguageManager.tr("arc_ctx_move").format(count=len(selected_proxies))
        )
        action_delete = menu.addAction(
            LanguageManager.tr("arc_ctx_delete").format(count=len(selected_proxies))
        )

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))

        if action_copy and action == action_copy:
            QApplication.clipboard().setText(proxy.raw_url)
            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_copied_title"),
                LanguageManager.tr("arc_msg_copied_body"),
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

        self.lbl_status.show()
        self.progress_bar.show()
        self.progress_bar.setMaximum(self.speed_test_total)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(
            LanguageManager.tr("arc_status_speed_init").format(
                total=self.speed_test_total
            )
        )
        self.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")

        self.speed_worker = SpeedTestWorker(self.scan_service, proxies)
        self.speed_worker.progress_signal.connect(self._on_speed_progress)
        self.speed_worker.finished_signal.connect(self._on_speed_finished)
        self.speed_worker.start()

    def _on_speed_progress(self, proxy):
        self.speed_test_current += 1
        self.progress_bar.setValue(self.speed_test_current)
        self.lbl_status.setText(
            LanguageManager.tr("arc_status_speed_prog").format(
                current=self.speed_test_current, total=self.speed_test_total
            )
        )
        self.model.update_proxy(proxy)

    def _on_speed_finished(self):
        self.lbl_status.setText(LanguageManager.tr("arc_status_speed_done"))
        self.lbl_status.setStyleSheet("color: #44bd32; font-weight: bold;")
        QMessageBox.information(
            self,
            LanguageManager.tr("arc_msg_speed_done_title"),
            LanguageManager.tr("arc_msg_speed_done_body"),
        )
        self.lbl_status.hide()
        self.progress_bar.hide()
        self.load_data()

    def _move_multiple_proxies(self, proxies):
        ids = [p.id for p in proxies if p.id]
        groups = [
            self.cmb_filter.itemData(i) for i in range(1, self.cmb_filter.count())
        ]
        if "Default" not in groups:
            groups.insert(0, "Default")

        new_group, ok = QInputDialog.getItem(
            self,
            LanguageManager.tr("arc_msg_move_title"),
            LanguageManager.tr("arc_msg_move_prompt").format(count=len(ids)),
            groups,
            0,
            True,
        )
        if ok and new_group.strip():
            self.worker_action = AsyncTaskWorker(
                self.repository.update_group_many(ids, new_group.strip())
            )
            self.worker_action.finished_signal.connect(lambda _: self.load_data())
            self.worker_action.start()

    def _delete_multiple_proxies(self, proxies):
        ids = [p.id for p in proxies if p.id]
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            LanguageManager.tr("arc_msg_del_sel_body").format(count=len(ids)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.worker_action = AsyncTaskWorker(self.repository.delete_many(ids))
            self.worker_action.finished_signal.connect(lambda _: self.load_data())
            self.worker_action.start()
