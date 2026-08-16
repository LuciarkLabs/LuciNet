from PySide6.QtWidgets import QWidget, QMessageBox, QFileDialog
from gui.workers import AsyncTaskWorker
from gui.language_manager import LanguageManager
from .ui_layout import ExportUiLayout
from gui.event_bus import event_bus

class ExportTab(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.export_mode = "all"
        self.is_db_locked = False

        self.ui = ExportUiLayout()
        self.ui.setup_ui(self)

        self.ui.btn_refresh_groups.clicked.connect(self._load_groups)
        self.ui.btn_export_all.clicked.connect(
            lambda: self.start_export(only_valid=False)
        )
        self.ui.btn_export_valid.clicked.connect(
            lambda: self.start_export(only_valid=True)
        )

        event_bus.data_changed.connect(self._load_groups)

        event_bus.scan_lock_changed.connect(self.on_scan_lock_changed)

        self._load_groups()
        self.retranslate_ui()

    def retranslate_ui(self):

        self.ui.settings_group.setTitle(LanguageManager.tr("exp_group_settings"))
        self.ui.lbl_archive.setText(LanguageManager.tr("exp_lbl_archive"))

        if self.ui.cmb_group.count() > 0:
            self.ui.cmb_group.setItemText(0, LanguageManager.tr("exp_cmb_all_archives"))

        self.ui.btn_refresh_groups.setText(LanguageManager.tr("exp_btn_refresh"))
        self.ui.lbl_info.setText(LanguageManager.tr("exp_lbl_info"))
        self.ui.btn_export_all.setText(LanguageManager.tr("exp_btn_export_all"))
        self.ui.btn_export_valid.setText(LanguageManager.tr("exp_btn_export_valid"))

        self._on_groups_loaded(
            [self.ui.cmb_group.itemData(i) for i in range(1, self.ui.cmb_group.count())]
        )

    def on_scan_lock_changed(self, is_locked, group_name):

        self.is_db_locked = is_locked

        self.ui.btn_export_all.setEnabled(not is_locked)
        self.ui.btn_export_valid.setEnabled(not is_locked)
        self.ui.btn_refresh_groups.setEnabled(not is_locked)

    def _load_groups(self):
        if self.is_db_locked:
            return
        self.ui.btn_refresh_groups.setEnabled(False)
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
        self.ui.btn_refresh_groups.setEnabled(True)
        current = self.ui.cmb_group.currentData()
        self.ui.cmb_group.blockSignals(True)
        self.ui.cmb_group.clear()

        self.ui.cmb_group.addItem(LanguageManager.tr("exp_cmb_all_archives"), "")

        prefix = LanguageManager.tr("exp_cmb_archive_prefix")
        for g in groups:
            if g:

                display_name = g if len(g) < 40 else g[:37] + "..."
                formatted_name = prefix.format(name=display_name)
                self.ui.cmb_group.addItem(f"📂 {formatted_name}", g)

        idx = self.ui.cmb_group.findData(current)
        if idx >= 0:
            self.ui.cmb_group.setCurrentIndex(idx)
        self.ui.cmb_group.blockSignals(False)

    def start_export(self, only_valid: bool):

        if self.is_db_locked:
            return
        self.export_mode = "valid" if only_valid else "all"

        self.ui.btn_export_all.setEnabled(False)
        self.ui.btn_export_valid.setEnabled(False)

        self.worker = AsyncTaskWorker(self.repository.get_all())
        self.worker.finished_signal.connect(self._on_data_loaded)
        self.worker.error_signal.connect(self._on_data_error)
        self.worker.start()

    def _on_data_loaded(self, proxies):
        self.ui.btn_export_all.setEnabled(True)
        self.ui.btn_export_valid.setEnabled(True)

        selected_group = self.ui.cmb_group.currentData()

        if selected_group:
            filtered_proxies = [p for p in proxies if p.group_name == selected_group]
            prefix_name = selected_group
        else:
            filtered_proxies = proxies
            prefix_name = "All_Archives"

        if self.export_mode == "valid":
            filtered_proxies = [p for p in filtered_proxies if p.status == "Valid"]
            file_suggest = f"LuciNet_{prefix_name}_Valid.txt"
        else:
            file_suggest = f"LuciNet_{prefix_name}_All.txt"

        if not filtered_proxies:
            QMessageBox.warning(
                self,
                LanguageManager.tr("exp_msg_no_config_title"),
                LanguageManager.tr("exp_msg_no_config_body"),
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            LanguageManager.tr("exp_dialog_title"),
            file_suggest,
            "Text Files (*.txt)",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for p in filtered_proxies:
                        f.write(f"{p.raw_url}\n")

                msg_body = LanguageManager.tr("exp_msg_success_body").format(
                    count=len(filtered_proxies), path=file_path
                )
                QMessageBox.information(
                    self,
                    LanguageManager.tr("exp_msg_success_title"),
                    msg_body,
                )
            except Exception as e:
                err_body = LanguageManager.tr("exp_msg_error_body").format(err_msg=e)
                QMessageBox.critical(
                    self, LanguageManager.tr("exp_msg_error_title"), err_body
                )

    def _on_data_error(self, err_msg):
        self.ui.btn_export_all.setEnabled(True)
        self.ui.btn_export_valid.setEnabled(True)
        err_body = LanguageManager.tr("exp_msg_db_error_body").format(err_msg=err_msg)
        QMessageBox.critical(
            self, LanguageManager.tr("exp_msg_db_error_title"), err_body
        )
