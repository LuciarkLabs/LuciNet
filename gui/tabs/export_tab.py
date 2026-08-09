import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
    QComboBox,
    QGroupBox,
)
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker
from gui.language_manager import LanguageManager

class ExportTab(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.export_mode = "all"
        self._setup_ui()
        self._load_groups()
        self.retranslate_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.settings_group = QGroupBox()
        settings_layout = QVBoxLayout(self.settings_group)

        group_layout = QHBoxLayout()

        self.lbl_archive = QLabel()
        group_layout.addWidget(self.lbl_archive)

        self.cmb_group = QComboBox()
        self.cmb_group.addItem("", "")
        self.cmb_group.setMinimumWidth(250)
        group_layout.addWidget(self.cmb_group)

        self.btn_refresh_groups = QPushButton()
        self.btn_refresh_groups.clicked.connect(self._load_groups)
        group_layout.addWidget(self.btn_refresh_groups)
        group_layout.addStretch()

        settings_layout.addLayout(group_layout)

        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet("color: #7f8fa6; margin-top: 10px;")
        settings_layout.addWidget(self.lbl_info)

        layout.addWidget(self.settings_group)

        btn_layout = QHBoxLayout()

        self.btn_export_all = QPushButton()
        self.btn_export_all.setMinimumHeight(45)
        self.btn_export_all.setStyleSheet(
            "background-color: #0097e6; color: white; font-weight: bold; border-radius: 5px; padding: 0 20px;"
        )
        self.btn_export_all.clicked.connect(lambda: self.start_export(only_valid=False))

        self.btn_export_valid = QPushButton()
        self.btn_export_valid.setMinimumHeight(45)
        self.btn_export_valid.setStyleSheet(
            "background-color: #44bd32; color: white; font-weight: bold; border-radius: 5px; padding: 0 20px;"
        )
        self.btn_export_valid.clicked.connect(
            lambda: self.start_export(only_valid=True)
        )

        btn_layout.addWidget(self.btn_export_all)
        btn_layout.addWidget(self.btn_export_valid)
        layout.addLayout(btn_layout)
        layout.addStretch()

    def retranslate_ui(self):

        self.settings_group.setTitle(LanguageManager.tr("exp_group_settings"))
        self.lbl_archive.setText(LanguageManager.tr("exp_lbl_archive"))

        if self.cmb_group.count() > 0:
            self.cmb_group.setItemText(0, LanguageManager.tr("exp_cmb_all_archives"))

        self.btn_refresh_groups.setText(LanguageManager.tr("exp_btn_refresh"))
        self.lbl_info.setText(LanguageManager.tr("exp_lbl_info"))
        self.btn_export_all.setText(LanguageManager.tr("exp_btn_export_all"))
        self.btn_export_valid.setText(LanguageManager.tr("exp_btn_export_valid"))

        self._on_groups_loaded(
            [self.cmb_group.itemData(i) for i in range(1, self.cmb_group.count())]
        )

    def _load_groups(self):
        self.btn_refresh_groups.setEnabled(False)
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
        self.btn_refresh_groups.setEnabled(True)
        current = self.cmb_group.currentData()
        self.cmb_group.blockSignals(True)
        self.cmb_group.clear()

        self.cmb_group.addItem(LanguageManager.tr("exp_cmb_all_archives"), "")

        prefix = LanguageManager.tr("exp_cmb_archive_prefix")
        for g in groups:
            if g:

                display_name = g if len(g) < 40 else g[:37] + "..."
                formatted_name = prefix.format(name=display_name)
                self.cmb_group.addItem(formatted_name, g)

        idx = self.cmb_group.findData(current)
        if idx >= 0:
            self.cmb_group.setCurrentIndex(idx)
        self.cmb_group.blockSignals(False)

    def start_export(self, only_valid: bool):
        self.export_mode = "valid" if only_valid else "all"

        self.btn_export_all.setEnabled(False)
        self.btn_export_valid.setEnabled(False)

        self.worker = AsyncTaskWorker(self.repository.get_all())
        self.worker.finished_signal.connect(self._on_data_loaded)
        self.worker.error_signal.connect(self._on_data_error)
        self.worker.start()

    def _on_data_loaded(self, proxies):
        self.btn_export_all.setEnabled(True)
        self.btn_export_valid.setEnabled(True)

        selected_group = self.cmb_group.currentData()

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
        self.btn_export_all.setEnabled(True)
        self.btn_export_valid.setEnabled(True)
        err_body = LanguageManager.tr("exp_msg_db_error_body").format(err_msg=err_msg)
        QMessageBox.critical(
            self, LanguageManager.tr("exp_msg_db_error_title"), err_body
        )
