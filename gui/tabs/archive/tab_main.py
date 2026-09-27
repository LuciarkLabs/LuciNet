from domain.models.raw_config import RawXrayConfig
from PySide6.QtWidgets import (
    QWidget,
    QMessageBox,
    QInputDialog,
    QHeaderView,
    QPushButton,
)
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from gui.language_manager import LanguageManager
from gui.event_bus import event_bus
from gui.widgets.subscription_dialog import SubscriptionDialog
from .ui_layout import ArchiveUiLayout

from .managers.data_manager import DataManager
from .managers.sub_manager import SubManager
from .managers.tools_manager import ToolsManager
from .context_menu_handler import ContextMenuHandler


class ArchiveTab(QWidget):
    def __init__(self, repository, scan_service, subscription_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service
        self.sub_service = subscription_service

        self.is_db_locked = False
        self.is_connected = False

        self.current_group_filter = ""
        self.available_groups = []

        self.ui = ArchiveUiLayout()
        self.ui.setup_ui(self)

        self.model = ProxyTableModel([])
        self.proxy_model = ProxySortModel()
        self.proxy_model.setSourceModel(self.model)
        self.ui.table_view.setModel(self.proxy_model)
        self._setup_table_headers()

        self.data_manager = DataManager(repository)
        self.sub_manager = SubManager(repository, subscription_service)
        self.tools_manager = ToolsManager(repository)

        self.menu_handler = ContextMenuHandler(
            self,
            self.tools_manager,
            self.ui.table_view,
            self.model,
            self.proxy_model,
        )

        self._connect_signals()

        self.ui.btn_toggle_console.setChecked(False)
        self._toggle_console_visibility(False)
        self.retranslate_ui()
        self.data_manager.load_data(self.is_db_locked)

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
            lambda: self.data_manager.load_data(self.is_db_locked)
        )
        self.ui.btn_new_group.clicked.connect(self._request_new_group)
        self.ui.btn_rename_group.clicked.connect(self._request_rename_group)
        self.ui.btn_delete_group.clicked.connect(self._request_delete_group)

        self.data_manager.loading_state_changed.connect(self._refresh_ui_state)
        self.sub_manager.state_changed.connect(self._refresh_ui_state)
        self.tools_manager.action_state_changed.connect(self._refresh_ui_state)
        event_bus.scan_lock_changed.connect(self.on_scan_lock_changed)

        self.data_manager.data_loaded.connect(self._populate_table)
        self.data_manager.groups_loaded.connect(self._populate_groups)
        self.data_manager.group_created.connect(self._on_group_changed_by_action)
        self.data_manager.group_renamed.connect(self._on_group_changed_by_action)
        self.data_manager.group_deleted.connect(lambda: event_bus.data_changed.emit())
        self.data_manager.error_occurred.connect(self._show_error)

        self.ui.btn_manage_subs.clicked.connect(self.open_subscription_manager)
        self.ui.btn_update_current_sub.clicked.connect(self._request_update_current_sub)
        self.ui.btn_update_all_subs.clicked.connect(self._request_update_all_subs)

        self.sub_manager.group_subs_evaluated.connect(self._update_sub_button_state)
        self.sub_manager.update_started.connect(self._on_sub_update_started)
        self.sub_manager.update_finished.connect(self._on_sub_update_finished)
        self.sub_manager.update_result_ready.connect(self._show_sub_update_result)
        self.sub_manager.error_occurred.connect(self._show_translated_error)

        self.ui.action_move.triggered.connect(self._menu_action_move)
        self.ui.action_dedup.triggered.connect(
            lambda: self.tools_manager.prepare_remove_duplicates(
                self.model.proxies, self.current_group_filter
            )
        )
        self.ui.action_del_inv.triggered.connect(
            lambda: self.tools_manager.prepare_delete_invalid(
                self.model.proxies, self.current_group_filter
            )
        )
        self.ui.action_del_tout.triggered.connect(
            lambda: self.tools_manager.prepare_delete_timeout(
                self.model.proxies, self.current_group_filter
            )
        )

        self.ui.table_view.customContextMenuRequested.connect(self._on_context_menu)

        self.tools_manager.request_confirmation.connect(self._handle_tools_confirmation)
        self.tools_manager.action_finished.connect(self._on_tools_action_finished)
        self.tools_manager.error_occurred.connect(self._show_translated_error)

        self.ui.txt_search.textChanged.connect(self.apply_adv_filters)
        self.ui.cmb_status.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_protocol.currentIndexChanged.connect(self.apply_adv_filters)
        self.ui.cmb_ip_filter.currentIndexChanged.connect(self.apply_adv_filters)

        self.ui.btn_quick_connect.clicked.connect(self._on_quick_connect_clicked)
        self.ui.table_view.doubleClicked.connect(self._on_row_double_clicked)

        self.ui.btn_clear_log.clicked.connect(self.ui.txt_console.clear)
        self.ui.btn_toggle_console.toggled.connect(self._toggle_console_visibility)

        event_bus.connection_status_changed.connect(
            self._update_quick_connect_btn_state
        )
        event_bus.log_message.connect(self._append_log)
        event_bus.data_changed.connect(
            lambda: self.data_manager.load_data(self.is_db_locked)
        )

    def _refresh_ui_state(self, _=None):
        """مدیریت مرکزی وضعیت فعال/غیرفعال بودن دکمه‌ها و فرم‌ها بر اساس Stateهای مختلف"""
        is_loading = self.data_manager.is_loading or getattr(
            self.data_manager, "is_action_running", False
        )
        is_tools_busy = self.tools_manager.is_running
        is_sub_updating = getattr(self.sub_manager, "is_updating", False)

        is_busy = is_loading or is_tools_busy or is_sub_updating
        can_interact = not is_busy and not self.is_db_locked

        self.ui.btn_refresh.setEnabled(can_interact)
        self.ui.btn_new_group.setEnabled(can_interact)
        self.ui.btn_tools.setEnabled(can_interact)
        self.ui.btn_manage_subs.setEnabled(can_interact)
        self.ui.btn_update_all_subs.setEnabled(can_interact)

        self.ui.groups_widget.setEnabled(can_interact)

        is_specific_group = bool(self.current_group_filter)
        self.ui.btn_rename_group.setEnabled(can_interact and is_specific_group)
        self.ui.btn_delete_group.setEnabled(can_interact and is_specific_group)

        has_subs = self.sub_manager.current_subscription_count > 0
        self.ui.btn_update_current_sub.setEnabled(
            can_interact and is_specific_group and has_subs
        )

        if is_loading:
            self.ui.lbl_status.setText(LanguageManager.tr("arc_status_loading"))
            self.ui.lbl_status.show()
        elif not is_sub_updating and not is_tools_busy:
            self.ui.lbl_status.hide()

    def on_scan_lock_changed(self, is_locked, group_name):
        self.is_db_locked = is_locked
        self._refresh_ui_state()
        if not is_locked:
            self.sub_manager.evaluate_group_subscriptions(self.current_group_filter)

    def _on_context_menu(self, pos):
        """نمایش منو با عبور از گاردهای امنیتی یکپارچه"""
        is_loading = self.data_manager.is_loading or getattr(
            self.data_manager, "is_action_running", False
        )
        is_tools_busy = self.tools_manager.is_running
        is_sub_updating = getattr(self.sub_manager, "is_updating", False)

        if is_loading or is_tools_busy or is_sub_updating or self.is_db_locked:
            return

        groups = [g for g in self.available_groups if g]
        self.menu_handler.show_context_menu(pos, groups, self.is_db_locked)

    def _request_new_group(self):
        new_name, ok = QInputDialog.getText(
            self,
            LanguageManager.tr("arc_msg_new_title"),
            LanguageManager.tr("arc_msg_new_prompt"),
        )
        if ok and new_name.strip():
            self.data_manager.create_group(new_name.strip())

    def _request_rename_group(self):
        if not self.current_group_filter:
            return
        new_name, ok = QInputDialog.getText(
            self,
            LanguageManager.tr("arc_msg_rename_title"),
            LanguageManager.tr("arc_msg_rename_prompt").format(
                name=self.current_group_filter
            ),
        )
        if ok and new_name.strip() and new_name.strip() != self.current_group_filter:
            self.data_manager.rename_group(self.current_group_filter, new_name.strip())

    def _request_delete_group(self):
        if not self.current_group_filter:
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            LanguageManager.tr("arc_msg_delete_body").format(
                name=self.current_group_filter
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.data_manager.delete_group(self.current_group_filter)

    def _on_group_changed_by_action(self, new_name):
        self.current_group_filter = new_name
        event_bus.data_changed.emit()

    def _populate_table(self, proxies):
        self.model.update_data(proxies)
        self.update_visible_count()
        self.ui.btn_refresh.setText(LanguageManager.tr("arc_btn_refresh"))

    def _populate_groups(self, groups):
        self.available_groups = groups
        if (
            self.current_group_filter
            and self.current_group_filter not in self.available_groups
        ):
            self.current_group_filter = ""
        self._render_group_pills()
        self._apply_group_filter(self.current_group_filter)

    def _render_group_pills(self):
        while self.ui.groups_layout.count():
            item = self.ui.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.ui.groups_widget.setStyleSheet("""
            QPushButton { background-color: #2f3640; color: #f5f6fa; border: none; border-radius: 12px; padding: 6px 15px; font-weight: bold; }
            QPushButton:checked { background-color: #0097e6; color: white; }
            QPushButton:hover:!checked { background-color: #353b48; }
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
        if btn:
            self._apply_group_filter(btn.property("group_name"))

    def _apply_group_filter(self, group_name):
        self.current_group_filter = group_name
        self.proxy_model.set_group_filter(group_name)
        self._update_pills_ui_state()
        self.update_visible_count()

        self.sub_manager.evaluate_group_subscriptions(group_name)

        self._refresh_ui_state()

    def _update_pills_ui_state(self):
        for i in range(self.ui.groups_layout.count()):
            widget = self.ui.groups_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.blockSignals(True)
                widget.setChecked(
                    widget.property("group_name") == self.current_group_filter
                )
                widget.blockSignals(False)

    def open_subscription_manager(self):
        dialog = SubscriptionDialog(
            self.repository,
            self.sub_service,
            default_group=self.current_group_filter,
            parent=self,
        )
        dialog.exec()
        event_bus.data_changed.emit()

    def _update_sub_button_state(self, has_subs, count):
        self._refresh_ui_state()
        if has_subs:
            self.ui.btn_update_current_sub.setToolTip(
                LanguageManager.tr("arc_tooltip_has_subs").format(count=count)
            )
        else:
            self.ui.btn_update_current_sub.setToolTip(
                LanguageManager.tr("arc_tooltip_no_sub")
            )

    def _request_update_current_sub(self):
        count = self.sub_manager.current_subscription_count
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_update_cur_title"),
            LanguageManager.tr("arc_msg_update_cur_body").format(count=count),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.sub_manager.update_current()

    def _request_update_all_subs(self):
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_update_all_title"),
            LanguageManager.tr("arc_msg_update_all_body"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.sub_manager.update_all()

    def _on_sub_update_started(self, update_type, count):
        self.ui.lbl_status.show()
        self.ui.lbl_status.setStyleSheet("color: #e67e22; font-weight: bold;")

        if update_type == "current":
            self.ui.lbl_status.setText(
                LanguageManager.tr("arc_status_downloading_subs")
            )
        elif update_type == "fetch_all":
            self.ui.lbl_status.setText(LanguageManager.tr("arc_status_fetching_subs"))
        elif update_type == "update_all":
            self.ui.lbl_status.setText(
                LanguageManager.tr("arc_status_updating_all_subs").format(count=count)
            )

    def _on_sub_update_finished(self):
        self._refresh_ui_state()

    def _show_sub_update_result(self, total_added, errors):
        msg = LanguageManager.tr("arc_msg_sub_update_success").format(count=total_added)
        if errors:
            err_str = "\n".join(errors)
            msg += LanguageManager.tr("arc_msg_sub_update_warn").format(errors=err_str)
        QMessageBox.information(
            self, LanguageManager.tr("arc_msg_sub_update_report_title"), msg
        )
        event_bus.data_changed.emit()

    def _get_selected_items(self):
        selected_indexes = self.ui.table_view.selectionModel().selectedRows()
        items = []
        for idx in selected_indexes:
            if not idx.isValid():
                continue
            source_idx = self.proxy_model.mapToSource(idx)
            if not source_idx.isValid():
                continue
            proxy = self.model.proxies[source_idx.row()]
            items.append(proxy)
        return items

    def _menu_action_move(self):
        items = self._get_selected_items()
        proxy_ids = [p.id for p in items if p.id and not isinstance(p, RawXrayConfig)]
        raw_ids = [p.id for p in items if p.id and isinstance(p, RawXrayConfig)]
        
        if not proxy_ids and not raw_ids:
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
            LanguageManager.tr("arc_msg_move_prompt").format(count=len(proxy_ids) + len(raw_ids)),
            groups,
            0,
            True,
        )
        if ok and new_group.strip():
            self.tools_manager.execute_move(proxy_ids, raw_ids, new_group.strip())

    def _handle_tools_confirmation(self, action_type, count, proxy_ids, raw_ids):
        if action_type == "delete_invalid":
            msg = LanguageManager.tr("arc_msg_del_inv_body").format(count=count)
        elif action_type == "delete_timeout":
            msg = LanguageManager.tr("arc_msg_del_tout_body").format(count=count)
        elif action_type == "remove_duplicates":
            msg = LanguageManager.tr("arc_msg_del_dedup_body").format(count=count)
        else:
            msg = f"Are you sure you want to delete {count} items?"

        reply = QMessageBox.question(
            self,
            LanguageManager.tr("arc_msg_delete_title"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.tools_manager.execute_delete(proxy_ids, raw_ids, action_type)

    def _on_tools_action_finished(self, action_type, count):
        if action_type == "move":
            msg = LanguageManager.tr("arc_msg_move_success").format(count=count)
        else:
            msg = LanguageManager.tr("arc_msg_del_success").format(count=count)

        QMessageBox.information(self, LanguageManager.tr("arc_msg_op_success"), msg)
        event_bus.data_changed.emit()

    def _update_quick_connect_btn_state(self, is_connected):
        self.is_connected = is_connected
        if is_connected:
            self.ui.btn_quick_connect.setText(
                LanguageManager.tr("arc_btn_quick_connected")
            )
            self.ui.btn_quick_connect.setStyleSheet(
                "QPushButton { background-color: #20bf6b; color: white; font-weight: bold; border-radius: 6px; padding: 6px 18px; } QPushButton:hover { background-color: #26de81; }"
            )
        else:
            self.ui.btn_quick_connect.setText(
                LanguageManager.tr("arc_btn_quick_connect")
            )
            self.ui.btn_quick_connect.setStyleSheet(
                "QPushButton { background-color: #eb3b5a; color: white; font-weight: bold; border-radius: 6px; padding: 6px 18px; } QPushButton:hover { background-color: #fc5c65; }"
            )

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
        self.ui.lbl_count.setText(
            LanguageManager.tr("arc_lbl_count").format(
                count=self.proxy_model.rowCount()
            )
        )

    def _on_row_double_clicked(self, index):
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        proxy = self.model.proxies[source_index.row()]
        event_bus.proxy_selected.emit(proxy)
        event_bus.request_view_change.emit("connect")

    def _toggle_console_visibility(self, checked):
        self.ui.console_container.setVisible(checked)
        self.ui.btn_toggle_console.setText(
            LanguageManager.tr("arc_btn_hide_log")
            if checked
            else LanguageManager.tr("arc_btn_show_log")
        )

    def _append_log(self, msg):
        self.ui.txt_console.appendPlainText(msg)
        if hasattr(self.ui, "chk_auto_scroll") and self.ui.chk_auto_scroll.isChecked():
            scrollbar = self.ui.txt_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _show_error(self, err_msg):
        QMessageBox.critical(self, LanguageManager.tr("arc_msg_error_title"), err_msg)

    def _show_translated_error(self, msg_key):
        translated = (
            LanguageManager.tr(msg_key) if msg_key.startswith("arc_") else msg_key
        )
        QMessageBox.warning(self, LanguageManager.tr("arc_msg_error_title"), translated)

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

        self.ui.btn_toggle_console.setText(
            LanguageManager.tr("arc_btn_hide_log")
            if self.ui.btn_toggle_console.isChecked()
            else LanguageManager.tr("arc_btn_show_log")
        )
        self.ui.btn_quick_connect.setToolTip(
            LanguageManager.tr("arc_tooltip_quick_connect")
        )
        self._update_quick_connect_btn_state(self.is_connected)
        self._render_group_pills()
