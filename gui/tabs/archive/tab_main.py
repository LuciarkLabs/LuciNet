from PySide6.QtWidgets import (
    QWidget,
    QMessageBox,
    QInputDialog,
    QMenu,
    QApplication,
    QHeaderView,
    QPushButton,
    QHBoxLayout,
)
from gui.workers import AsyncTaskWorker, SpeedTestWorker
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from gui.widgets.qr_dialog import QRDialog
from gui.language_manager import LanguageManager
from .ui_layout import ArchiveUiLayout
from gui.event_bus import event_bus
from gui.widgets.subscription_dialog import SubscriptionDialog

class ArchiveTab(QWidget):
    def __init__(self, repository, scan_service, subscription_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service
        self.sub_service = subscription_service

        self.is_db_locked = False
        self.current_subs_in_group = []

        self.is_connected = False

        self.current_group_filter = ""
        self.available_groups = []

        self.ui = ArchiveUiLayout()
        self.ui.setup_ui(self)

        self.model = ProxyTableModel([])
        self.proxy_model = ProxySortModel()
        self.proxy_model.setSourceModel(self.model)
        self.ui.table_view.setModel(self.proxy_model)

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

        self._connect_signals()

        self.load_data()
        self.retranslate_ui()

        self.ui.btn_toggle_console.setChecked(False)
        self._toggle_console_visibility(False)

    def _connect_signals(self):

        self.ui.btn_new_group.clicked.connect(self.create_new_group)
        self.ui.btn_rename_group.clicked.connect(self.rename_current_group)
        self.ui.btn_delete_group.clicked.connect(self.delete_current_group)
        self.ui.btn_refresh.clicked.connect(self.load_data)

        self.ui.btn_quick_connect.clicked.connect(self._on_quick_connect_clicked)
        event_bus.connection_status_changed.connect(
            self._update_quick_connect_btn_state
        )

        self.ui.txt_search.textChanged.connect(self.apply_adv_filters)
        self.ui.cmb_status.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_protocol.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_ip_filter.currentIndexChanged.connect(self.apply_adv_filters)

        self.ui.action_move.triggered.connect(self.move_selected)
        self.ui.action_dedup.triggered.connect(self.remove_duplicates)
        self.ui.action_del_inv.triggered.connect(self.delete_invalid)
        self.ui.action_del_tout.triggered.connect(self.delete_timeout)

        self.ui.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.table_view.doubleClicked.connect(self._on_row_double_clicked)

        event_bus.log_message.connect(self._append_log)
        event_bus.data_changed.connect(self.load_data)
        event_bus.scan_lock_changed.connect(self.on_scan_lock_changed)

        self.ui.btn_manage_subs.clicked.connect(self.open_subscription_manager)
        self.ui.btn_update_current_sub.clicked.connect(self.update_current_subscription)
        self.ui.btn_update_all_subs.clicked.connect(self.update_all_subscriptions)

        self.ui.btn_clear_log.clicked.connect(self.ui.txt_console.clear)
        self.ui.btn_toggle_console.toggled.connect(self._toggle_console_visibility)

    def _update_quick_connect_btn_state(self, is_connected):

        self.is_connected = is_connected
        if is_connected:
            self.ui.btn_quick_connect.setText(
                LanguageManager.tr("arc_btn_quick_connected")
            )
            self.ui.btn_quick_connect.setStyleSheet("""
                QPushButton {
                    background-color: #20bf6b;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 6px 18px;
                }
                QPushButton:hover { background-color: #26de81; }
            """)
        else:
            self.ui.btn_quick_connect.setText(
                LanguageManager.tr("arc_btn_quick_connect")
            )
            self.ui.btn_quick_connect.setStyleSheet("""
                QPushButton {
                    background-color: #eb3b5a;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 6px 18px;
                }
                QPushButton:hover { background-color: #fc5c65; }
            """)

    def _on_quick_connect_clicked(self):

        if self.is_connected:
            event_bus.request_quick_connect.emit(None)
            return

        selected_indexes = self.ui.table_view.selectionModel().selectedRows()

        if not selected_indexes:
            QMessageBox.warning(
                self,
                LanguageManager.tr("arc_msg_error_title"),
                LanguageManager.tr("arc_msg_quick_connect_err"),
            )
            return

        source_index = self.proxy_model.mapToSource(selected_indexes[0])
        proxy = self.model.proxies[source_index.row()]
        event_bus.request_quick_connect.emit(proxy)

    def _toggle_console_visibility(self, checked):
        self.ui.console_container.setVisible(checked)
        self._update_console_btn_text()

    def _update_console_btn_text(self):
        if self.ui.btn_toggle_console.isChecked():
            self.ui.btn_toggle_console.setText(LanguageManager.tr("arc_btn_hide_log"))
        else:
            self.ui.btn_toggle_console.setText(LanguageManager.tr("arc_btn_show_log"))

    def retranslate_ui(self):
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

        self.ui.lbl_ip_filter.setText(LanguageManager.tr("arc_lbl_ip_filter"))

        if self.ui.cmb_status.count() > 0:
            self.ui.cmb_status.setItemText(
                0, LanguageManager.tr("arc_cmb_all_statuses")
            )
        if self.ui.cmb_protocol.count() > 0:
            self.ui.cmb_protocol.setItemText(
                0, LanguageManager.tr("arc_cmb_all_protocols")
            )

        if self.ui.cmb_ip_filter.count() > 0:
            self.ui.cmb_ip_filter.setItemText(0, LanguageManager.tr("arc_cmb_all_ips"))

        self.ui.btn_manage_subs.setText(LanguageManager.tr("arc_btn_manage_subs"))
        self.ui.btn_update_current_sub.setText(
            LanguageManager.tr("arc_btn_update_cur_sub")
        )
        self.ui.btn_update_all_subs.setText(
            LanguageManager.tr("arc_btn_update_all_subs")
        )

        self.update_visible_count()

        if self.ui.btn_refresh.isEnabled():
            self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))
        else:
            self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_loading"))

        status_text = self.ui.lbl_status.text()
        if status_text in ["آماده", "Ready"]:
            self.ui.lbl_status.setText(LanguageManager.tr("arc_status_ready"))

        self._update_console_btn_text()

        self.ui.btn_quick_connect.setToolTip(
            LanguageManager.tr("arc_tooltip_quick_connect")
        )
        self._update_quick_connect_btn_state(self.is_connected)
        self._render_group_pills()

    def _render_group_pills(self):
        while self.ui.groups_layout.count():
            item = self.ui.groups_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.ui.groups_widget.setStyleSheet("""
            QPushButton {
                background-color: #2f3640;
                color: #f5f6fa;
                border: none;
                border-radius: 12px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #0097e6;
                color: white;
            }
            QPushButton:hover:!checked {
                background-color: #353b48;
            }
        """)

        btn_all = QPushButton(LanguageManager.tr("arc_cmb_all_archives"))
        btn_all.setCheckable(True)
        btn_all.setProperty("group_name", "")
        btn_all.clicked.connect(self._on_group_pill_clicked)
        self.ui.groups_layout.addWidget(btn_all)

        for g in self.available_groups:
            if not g:
                continue
            btn = QPushButton(f"📂 {g}")
            btn.setCheckable(True)
            btn.setProperty("group_name", g)
            btn.clicked.connect(self._on_group_pill_clicked)
            self.ui.groups_layout.addWidget(btn)

        self.ui.groups_layout.addStretch()
        self._update_pills_ui_state()

    def _on_group_pill_clicked(self):
        btn = self.sender()
        if not btn:
            return
        group_name = btn.property("group_name")
        self.on_group_changed(group_name)

    def _update_pills_ui_state(self):
        for i in range(self.ui.groups_layout.count()):
            widget = self.ui.groups_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                g_name = widget.property("group_name")
                widget.blockSignals(True)
                widget.setChecked(g_name == self.current_group_filter)
                widget.blockSignals(False)

    def on_group_changed(self, group_name):
        self.current_group_filter = group_name
        self.proxy_model.set_group_filter(group_name)
        is_specific_group = bool(group_name)

        self._update_pills_ui_state()
        self.current_subs_in_group = []

        if is_specific_group:
            self.check_subs_worker = AsyncTaskWorker(
                self.repository.get_subscriptions()
            )
            self.check_subs_worker.finished_signal.connect(
                lambda subs: self._eval_group_subs(subs, group_name)
            )
            self.check_subs_worker.start()
        else:
            if not self.is_db_locked:
                self.ui.btn_update_current_sub.setEnabled(False)
                self.ui.btn_update_current_sub.setToolTip("")

        if not self.is_db_locked:
            self.ui.btn_rename_group.setEnabled(is_specific_group)
            self.ui.btn_delete_group.setEnabled(is_specific_group)

        self.update_visible_count()

    def on_scan_lock_changed(self, is_locked, group_name):
        self.is_db_locked = is_locked

        self.ui.btn_new_group.setEnabled(not is_locked)
        self.ui.btn_tools.setEnabled(not is_locked)
        self.ui.btn_refresh.setEnabled(not is_locked)

        self.ui.btn_manage_subs.setEnabled(not is_locked)
        self.ui.btn_update_all_subs.setEnabled(not is_locked)

        if is_locked:
            self.ui.btn_rename_group.setEnabled(False)
            self.ui.btn_delete_group.setEnabled(False)
            self.ui.btn_update_current_sub.setEnabled(False)
        else:
            is_specific_group = bool(self.current_group_filter)
            self.ui.btn_rename_group.setEnabled(is_specific_group)
            self.ui.btn_delete_group.setEnabled(is_specific_group)

            has_subs = len(self.current_subs_in_group) > 0
            self.ui.btn_update_current_sub.setEnabled(is_specific_group and has_subs)

    def _eval_group_subs(self, all_subs, current_group):
        self.current_subs_in_group = [s for s in all_subs if s.name == current_group]
        if self.current_subs_in_group and not self.is_db_locked:
            self.ui.btn_update_current_sub.setEnabled(True)
            self.ui.btn_update_current_sub.setToolTip(
                LanguageManager.tr("arc_tooltip_has_subs").format(
                    count=len(self.current_subs_in_group)
                )
            )
        else:
            self.ui.btn_update_current_sub.setEnabled(False)
            self.ui.btn_update_current_sub.setToolTip(
                LanguageManager.tr("arc_tooltip_no_sub")
            )

    def open_subscription_manager(self):
        current_group = self.current_group_filter
        dialog = SubscriptionDialog(
            self.repository, self.sub_service, default_group=current_group, parent=self
        )
        dialog.exec()
        self.on_group_changed(self.current_group_filter)
        self.load_data()

    def update_current_subscription(self):
        if not self.current_subs_in_group:
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_update_cur_title"),
            LanguageManager.tr("arc_msg_update_cur_body").format(
                count=len(self.current_subs_in_group)
            ),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.ui.btn_refresh.setEnabled(False)
            self.ui.lbl_status.show()
            self.ui.lbl_status.setText(
                LanguageManager.tr("arc_status_downloading_subs")
            )
            self.ui.lbl_status.setStyleSheet("color: #e67e22; font-weight: bold;")

            self.worker_update = AsyncTaskWorker(
                self._update_subs_task(self.current_subs_in_group)
            )
            self.worker_update.finished_signal.connect(self._on_update_finished)
            self.worker_update.start()

    def update_all_subscriptions(self):
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_update_all_title"),
            LanguageManager.tr("arc_msg_update_all_body"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.ui.btn_refresh.setEnabled(False)
            self.ui.lbl_status.show()
            self.ui.lbl_status.setText(LanguageManager.tr("arc_status_fetching_subs"))
            self.ui.lbl_status.setStyleSheet("color: #e67e22; font-weight: bold;")

            self.worker_fetch_all = AsyncTaskWorker(self.repository.get_subscriptions())
            self.worker_fetch_all.finished_signal.connect(self._start_update_all)
            self.worker_fetch_all.start()

    def _start_update_all(self, all_subs):
        if not all_subs:
            QMessageBox.information(
                self,
                LanguageManager.tr("arc_msg_error_title"),
                LanguageManager.tr("arc_msg_no_subs"),
            )
            self.ui.lbl_status.hide()
            self.ui.btn_refresh.setEnabled(True)
            return

        self.ui.lbl_status.setText(
            LanguageManager.tr("arc_status_updating_all_subs").format(
                count=len(all_subs)
            )
        )
        self.worker_update = AsyncTaskWorker(self._update_subs_task(all_subs))
        self.worker_update.finished_signal.connect(self._on_update_finished)
        self.worker_update.start()

    async def _update_subs_task(self, subs_list):
        total_added = 0
        errors = []
        for sub in subs_list:
            success, count, err_msg = await self.sub_service.fetch_and_update(sub)
            if success:
                total_added += count
            else:
                errors.append(f"{sub.name}: {err_msg}")
        return total_added, errors

    def _on_update_finished(self, result):
        total_added, errors = result
        self.ui.btn_refresh.setEnabled(True)
        self.ui.lbl_status.hide()

        msg = LanguageManager.tr("arc_msg_sub_update_success").format(count=total_added)
        if errors:
            err_str = "\n".join(errors)
            msg += LanguageManager.tr("arc_msg_sub_update_warn").format(errors=err_str)

        QMessageBox.information(
            self, LanguageManager.tr("arc_msg_sub_update_report_title"), msg
        )
        event_bus.data_changed.emit()

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
            self.worker_add_group = AsyncTaskWorker(self.repository.add_group(new_name))
            self.worker_add_group.finished_signal.connect(
                lambda _: self._on_group_created(new_name)
            )
            self.worker_add_group.start()

    def _on_group_created(self, new_name):
        QMessageBox.information(
            self,
            LanguageManager.tr("arc_msg_created_title"),
            LanguageManager.tr("arc_msg_created_body").format(name=new_name),
        )
        self.current_group_filter = new_name
        event_bus.data_changed.emit()

    def rename_current_group(self):
        current_group = self.current_group_filter
        if not current_group:
            return
        new_name, ok = QInputDialog.getText(
            self,
            LanguageManager.tr("arc_msg_rename_title"),
            LanguageManager.tr("arc_msg_rename_prompt").format(name=current_group),
        )
        if ok and new_name.strip() and new_name.strip() != current_group:
            clean_new_name = new_name.strip()
            self.worker_rename = AsyncTaskWorker(
                self.repository.rename_group(current_group, clean_new_name)
            )
            self.worker_rename.finished_signal.connect(
                lambda _: self._on_group_renamed(clean_new_name)
            )
            self.worker_rename.start()

    def _on_group_renamed(self, new_name):
        self.current_group_filter = new_name
        event_bus.data_changed.emit()

    def delete_current_group(self):
        current_group = self.current_group_filter
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

        groups = [g for g in self.available_groups if g]
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
        current_group = self.current_group_filter
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
        current_group = self.current_group_filter
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
        current_group = self.current_group_filter
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

        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded_for_archive)
        self.worker_groups.start()

    def _on_groups_loaded_for_archive(self, groups):
        self.available_groups = sorted(list(set(groups)))

        if (
            self.current_group_filter
            and self.current_group_filter not in self.available_groups
        ):
            self.current_group_filter = ""

        self._render_group_pills()
        self.on_group_changed(self.current_group_filter)

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
            self.move_selected()
        elif action == action_delete:
            self.delete_selected()

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

    def _on_row_double_clicked(self, index):
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        proxy = self.model.proxies[source_index.row()]

        event_bus.proxy_selected.emit(proxy)
        event_bus.request_view_change.emit("connect")

    def _append_log(self, msg):
        self.ui.txt_console.appendPlainText(msg)
        if hasattr(self.ui, "chk_auto_scroll") and self.ui.chk_auto_scroll.isChecked():
            scrollbar = self.ui.txt_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
