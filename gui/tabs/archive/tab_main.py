from PySide6.QtWidgets import (
    QWidget,
    QMessageBox,
    QInputDialog,
    QMenu,
    QApplication,
    QHeaderView,
)
from gui.workers import AsyncTaskWorker, SpeedTestWorker
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from gui.widgets.qr_dialog import QRDialog
from gui.language_manager import LanguageManager
from .ui_layout import ArchiveUiLayout
from gui.event_bus import event_bus

class ArchiveTab(QWidget):
    def __init__(self, repository, scan_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service

        self.is_db_locked = False

        self.ui = ArchiveUiLayout()
        self.ui.setup_ui(self)

        self.model = ProxyTableModel([])
        self.proxy_model = ProxySortModel()
        self.proxy_model.setSourceModel(self.model)
        self.ui.table_view.setModel(self.proxy_model)

        header = self.ui.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self._connect_signals()

        self.load_data()
        self.retranslate_ui()

    def _connect_signals(self):

        self.ui.cmb_filter.currentIndexChanged.connect(self.on_filter_changed)
        self.ui.btn_new_group.clicked.connect(self.create_new_group)
        self.ui.btn_rename_group.clicked.connect(self.rename_current_group)
        self.ui.btn_delete_group.clicked.connect(self.delete_current_group)
        self.ui.btn_refresh.clicked.connect(self.load_data)

        self.ui.txt_search.textChanged.connect(self.apply_adv_filters)
        self.ui.cmb_status.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_protocol.currentIndexChanged.connect(self.apply_adv_filters)

        self.ui.action_move.triggered.connect(self.move_selected)
        self.ui.action_dedup.triggered.connect(self.remove_duplicates)

        self.ui.action_del_inv.triggered.connect(self.delete_invalid)
        self.ui.action_del_tout.triggered.connect(self.delete_timeout)

        self.ui.table_view.customContextMenuRequested.connect(self.show_context_menu)

        event_bus.data_changed.connect(self.load_data)

        event_bus.scan_lock_changed.connect(self.on_scan_lock_changed)

    def retranslate_ui(self):

        self.ui.lbl_archive.setText(LanguageManager.tr("arc_lbl_archive"))
        self.ui.btn_new_group.setText(LanguageManager.tr("arc_btn_new_archive"))
        self.ui.btn_rename_group.setText(LanguageManager.tr("arc_btn_rename"))
        self.ui.btn_delete_group.setText(LanguageManager.tr("arc_btn_delete"))
        self.ui.btn_tools.setText(LanguageManager.tr("arc_btn_tools"))

        self.ui.action_move.setText(LanguageManager.tr("arc_menu_move"))
        self.ui.action_dedup.setText(LanguageManager.tr("arc_menu_dedup"))
        self.ui.action_del_inv.setText(LanguageManager.tr("arc_menu_del_inv"))
        self.ui.action_del_tout.setText(LanguageManager.tr("arc_menu_del_tout"))

        self.ui.filter_group.setTitle(LanguageManager.tr("arc_group_filter"))
        self.ui.txt_search.setPlaceholderText(
            LanguageManager.tr("arc_placeholder_search")
        )
        self.ui.lbl_search.setText(LanguageManager.tr("arc_lbl_search"))
        self.ui.lbl_status_filter.setText(LanguageManager.tr("arc_lbl_status"))
        self.ui.lbl_protocol_filter.setText(LanguageManager.tr("arc_lbl_protocol"))

        if self.ui.cmb_filter.count() > 0:
            self.ui.cmb_filter.setItemText(
                0, LanguageManager.tr("arc_cmb_all_archives")
            )
        if self.ui.cmb_status.count() > 0:
            self.ui.cmb_status.setItemText(
                0, LanguageManager.tr("arc_cmb_all_statuses")
            )
        if self.ui.cmb_protocol.count() > 0:
            self.ui.cmb_protocol.setItemText(
                0, LanguageManager.tr("arc_cmb_all_protocols")
            )

        self.update_visible_count()

        if self.ui.btn_refresh.isEnabled():
            self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        else:
            self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_loading"))

        status_text = self.ui.lbl_status.text()
        if status_text in ["آماده", "Ready"]:
            self.ui.lbl_status.setText(LanguageManager.tr("arc_status_ready"))

    def on_scan_lock_changed(self, is_locked, group_name):

        self.is_db_locked = is_locked

        self.ui.btn_new_group.setEnabled(not is_locked)
        self.ui.btn_tools.setEnabled(not is_locked)
        self.ui.btn_refresh.setEnabled(
            not is_locked
        )

        if is_locked:
            self.ui.btn_rename_group.setEnabled(False)
            self.ui.btn_delete_group.setEnabled(False)
        else:

            is_specific_group = bool(self.ui.cmb_filter.currentData())
            self.ui.btn_rename_group.setEnabled(is_specific_group)
            self.ui.btn_delete_group.setEnabled(is_specific_group)

    def on_filter_changed(self):
        group = self.ui.cmb_filter.currentData()
        self.proxy_model.set_group_filter(group)
        is_specific_group = bool(group)

        if not self.is_db_locked:
            self.ui.btn_rename_group.setEnabled(is_specific_group)
            self.ui.btn_delete_group.setEnabled(is_specific_group)

        self.update_visible_count()

    def apply_adv_filters(self):
        status_idx = self.ui.cmb_status.currentIndex()
        status = self.ui.cmb_status.currentText() if status_idx > 0 else ""

        protocol_idx = self.ui.cmb_protocol.currentIndex()
        protocol = self.ui.cmb_protocol.currentText() if protocol_idx > 0 else ""

        search_txt = self.ui.txt_search.text().strip()

        self.proxy_model.set_status_filter(status)
        self.proxy_model.set_protocol_filter(protocol)
        self.proxy_model.set_search_text(search_txt)

        self.update_visible_count()

    def update_visible_count(self):
        visible_count = self.proxy_model.rowCount()
        self.ui.lbl_count.setText(
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
                self.ui.cmb_filter.itemData(i)
                for i in range(self.ui.cmb_filter.count())
            ]
            if new_name not in existing_groups:
                self.ui.cmb_filter.addItem(new_name, new_name)

            idx = self.ui.cmb_filter.findData(new_name)
            if idx >= 0:
                self.ui.cmb_filter.setCurrentIndex(idx)

            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_created_title"),
                LanguageManager.tr("arc_msg_created_body").format(name=new_name),
            )

    def rename_current_group(self):
        current_group = self.ui.cmb_filter.currentData()
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
            self.worker_rename.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_rename.start()

    def delete_current_group(self):
        current_group = self.ui.cmb_filter.currentData()
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
            self.worker_delete.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_delete.start()

    def get_selected_ids(self):
        selected_indexes = self.ui.table_view.selectionModel().selectedRows()
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
            self.ui.cmb_filter.itemData(i) for i in range(1, self.ui.cmb_filter.count())
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
        current_group = self.ui.cmb_filter.currentData()
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
        current_group = self.ui.cmb_filter.currentData()
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
        current_group = self.ui.cmb_filter.currentData()
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
        event_bus.data_changed.emit()

    def load_data(self):
        if self.is_db_locked:
            return
        self.ui.btn_refresh.setEnabled(False)
        self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_loading"))
        self.worker = AsyncTaskWorker(self.repository.get_all())
        self.worker.finished_signal.connect(self._on_data_loaded)
        self.worker.error_signal.connect(self._on_data_error)
        self.worker.start()

    def _on_data_loaded(self, proxies):
        self.ui.btn_refresh.setEnabled(True)
        self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        self.model.update_data(proxies)

        current_filter = self.ui.cmb_filter.currentData()
        groups = sorted(list(set(p.group_name for p in proxies)))

        if current_filter and current_filter not in groups:
            groups.append(current_filter)

        self.ui.cmb_filter.blockSignals(True)
        self.ui.cmb_filter.clear()
        self.ui.cmb_filter.addItem(LanguageManager.tr("arc_cmb_all_archives"), "")
        for g in groups:
            if g:
                self.ui.cmb_filter.addItem(f"📂 {g}", g)

        index = self.ui.cmb_filter.findData(current_filter)
        if index >= 0:
            self.ui.cmb_filter.setCurrentIndex(index)
        else:
            self.ui.cmb_filter.setCurrentIndex(0)
        self.ui.cmb_filter.blockSignals(False)

        self.on_filter_changed()

    def _on_data_error(self, err_msg):
        self.ui.btn_refresh.setEnabled(True)
        self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        self.ui.lbl_status.show()
        self.ui.lbl_status.setText(LanguageManager.tr("arc_status_db_error"))
        self.ui.lbl_status.setStyleSheet("color: red;")

    def show_context_menu(self, pos):

        if self.is_db_locked:
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
            action_copy = menu.addAction(LanguageManager.tr("arc_ctx_copy"))
            action_qr = menu.addAction(LanguageManager.tr("arc_ctx_qr"))
        else:
            action_copy = None
            action_qr = None

        menu.addSeparator()
        action_move = menu.addAction(
            LanguageManager.tr("arc_ctx_move").format(count=len(selected_proxies))
        )
        action_delete = menu.addAction(
            LanguageManager.tr("arc_ctx_delete").format(count=len(selected_proxies))
        )

        action = menu.exec(self.ui.table_view.viewport().mapToGlobal(pos))

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
        elif action == action_move:
            self._move_multiple_proxies(selected_proxies)
        elif action == action_delete:
            self._delete_multiple_proxies(selected_proxies)

    def _test_speed_multiple(self, proxies):
        self.speed_test_total = len(proxies)
        self.speed_test_current = 0

        self.ui.lbl_status.show()
        self.ui.progress_bar.show()
        self.ui.progress_bar.setMaximum(self.speed_test_total)
        self.ui.progress_bar.setValue(0)
        self.ui.lbl_status.setText(
            LanguageManager.tr("arc_status_speed_init").format(
                total=self.speed_test_total
            )
        )
        self.ui.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")

        self.speed_worker = SpeedTestWorker(self.scan_service, proxies)
        self.speed_worker.progress_signal.connect(self._on_speed_progress)
        self.speed_worker.finished_signal.connect(self._on_speed_finished)
        self.speed_worker.start()

    def _on_speed_progress(self, proxy):
        self.speed_test_current += 1
        self.ui.progress_bar.setValue(self.speed_test_current)
        self.ui.lbl_status.setText(
            LanguageManager.tr("arc_status_speed_prog").format(
                current=self.speed_test_current, total=self.speed_test_total
            )
        )
        self.model.update_proxy(proxy)

    def _on_speed_finished(self):
        self.ui.lbl_status.setText(LanguageManager.tr("arc_status_speed_done"))
        self.ui.lbl_status.setStyleSheet("color: #44bd32; font-weight: bold;")
        QMessageBox.information(
            self,
            LanguageManager.tr("arc_msg_speed_done_title"),
            LanguageManager.tr("arc_msg_speed_done_body"),
        )
        self.ui.lbl_status.hide()
        self.ui.progress_bar.hide()
        event_bus.data_changed.emit()

    def _move_multiple_proxies(self, proxies):
        ids = [p.id for p in proxies if p.id]
        groups = [
            self.ui.cmb_filter.itemData(i) for i in range(1, self.ui.cmb_filter.count())
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
                lambda _: event_bus.data_changed.emit()
            )
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
            self.worker_action.finished_signal.connect(
                lambda _: event_bus.data_changed.emit()
            )
            self.worker_action.start()
