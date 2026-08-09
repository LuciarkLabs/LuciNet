import aiohttp
import base64
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QComboBox,
    QLineEdit,
    QFileDialog,
)
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker
from parser.exceptions import ParseError
from utils.logger import get_logger
from gui.language_manager import LanguageManager

logger = get_logger("InputTab")

class InputTab(QWidget):
    def __init__(self, parser_factory, repository):
        super().__init__()
        self.parser_factory = parser_factory
        self.repository = repository
        self._setup_ui()
        self._load_groups()
        self.retranslate_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        group_layout = QHBoxLayout()
        self.lbl_group = QLabel()
        group_layout.addWidget(self.lbl_group)
        self.cmb_group = QComboBox()
        self.cmb_group.setEditable(True)
        self.cmb_group.setMinimumWidth(200)
        group_layout.addWidget(self.cmb_group)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        sub_layout = QHBoxLayout()
        self.lbl_sub = QLabel()
        sub_layout.addWidget(self.lbl_sub)

        self.txt_sub_link = QLineEdit()
        sub_layout.addWidget(self.txt_sub_link)

        self.btn_fetch_sub = QPushButton()
        self.btn_fetch_sub.setStyleSheet(
            "background-color: #fbc531; color: #2f3640; font-weight: bold; border-radius: 5px; padding: 5px 15px;"
        )
        self.btn_fetch_sub.clicked.connect(self.fetch_subscription)
        sub_layout.addWidget(self.btn_fetch_sub)

        layout.addLayout(sub_layout)

        txt_header_layout = QHBoxLayout()
        self.lbl_txt_header = QLabel()
        txt_header_layout.addWidget(self.lbl_txt_header)
        txt_header_layout.addStretch()

        self.btn_load_file = QPushButton()
        self.btn_load_file.setStyleSheet(
            "background-color: #dcdde1; color: #2f3640; font-weight: bold; border-radius: 5px; padding: 5px 15px;"
        )
        self.btn_load_file.clicked.connect(self.load_from_file)
        txt_header_layout.addWidget(self.btn_load_file)

        layout.addLayout(txt_header_layout)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("vless://...\nvmess://...\ntrojan://...")
        layout.addWidget(self.text_edit)

        bottom_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: gray;")

        self.import_btn = QPushButton()
        self.import_btn.setMinimumHeight(40)
        self.import_btn.setStyleSheet(
            "background-color: #0097e6; color: white; font-weight: bold; border-radius: 5px; padding: 0 20px;"
        )
        self.import_btn.clicked.connect(self.process_configs)

        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.import_btn)

        layout.addLayout(bottom_layout)

    def retranslate_ui(self):

        self.lbl_group.setText(LanguageManager.tr("input_lbl_group"))
        self.lbl_sub.setText(LanguageManager.tr("input_lbl_sub"))
        self.txt_sub_link.setPlaceholderText(
            LanguageManager.tr("input_placeholder_sub")
        )

        if self.btn_fetch_sub.isEnabled():
            self.btn_fetch_sub.setText(LanguageManager.tr("input_btn_fetch"))
        else:
            self.btn_fetch_sub.setText(LanguageManager.tr("input_btn_fetching"))

        self.lbl_txt_header.setText(LanguageManager.tr("input_lbl_text_header"))
        self.btn_load_file.setText(LanguageManager.tr("input_btn_load_file"))
        self.import_btn.setText(LanguageManager.tr("input_btn_import"))

        current_status = self.status_label.text()
        if not current_status or current_status in [
            "منتظر ورود اطلاعات...",
            "Waiting for input...",
        ]:
            self.status_label.setText(LanguageManager.tr("input_status_waiting"))
        elif current_status in ["آماده", "Ready"]:
            self.status_label.setText(LanguageManager.tr("input_status_ready"))

    def _load_groups(self):
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
        self.cmb_group.clear()
        for g in groups:
            self.cmb_group.addItem(g)
        if "Default" not in groups:
            self.cmb_group.addItem("Default")
        self.cmb_group.setCurrentText("Default")

    def load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            LanguageManager.tr("input_file_dialog_title"),
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                current_text = self.text_edit.toPlainText()
                if current_text.strip():
                    self.text_edit.setPlainText(current_text + "\n" + content)
                else:
                    self.text_edit.setPlainText(content)

                self.status_label.setText(LanguageManager.tr("input_msg_file_success"))
                self.status_label.setStyleSheet("color: green;")
            except Exception as e:
                err_msg = LanguageManager.tr("input_msg_error_file_read").format(e=e)
                QMessageBox.critical(
                    self, LanguageManager.tr("input_msg_error_title"), err_msg
                )

    def fetch_subscription(self):
        urls_text = self.txt_sub_link.text().strip()
        if not urls_text:
            QMessageBox.warning(
                self,
                LanguageManager.tr("input_msg_error_title"),
                LanguageManager.tr("input_msg_warn_no_sub"),
            )
            return

        raw_urls = urls_text.replace(",", " ").split()
        urls = [url.strip() for url in raw_urls if url.strip().startswith("http")]

        if not urls:
            QMessageBox.warning(
                self,
                LanguageManager.tr("input_msg_error_title"),
                LanguageManager.tr("input_msg_warn_invalid_sub"),
            )
            return

        self.btn_fetch_sub.setEnabled(False)
        self.btn_fetch_sub.setText(LanguageManager.tr("input_btn_fetching"))
        self.status_label.setText(LanguageManager.tr("input_status_downloading"))
        self.status_label.setStyleSheet("color: blue;")

        self.worker_sub = AsyncTaskWorker(self._async_fetch_subs(urls))
        self.worker_sub.finished_signal.connect(self._on_fetch_success)
        self.worker_sub.error_signal.connect(self._on_fetch_error)
        self.worker_sub.start()

    async def _async_fetch_subs(self, urls):
        configs = []
        errors = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:

                    headers = {
                        "User-Agent": "v2rayN/6.31 Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    }
                    async with session.get(
                        url, headers=headers, timeout=15
                    ) as response:
                        if response.status == 200:
                            text = await response.text()
                            text = text.strip()

                            if "://" not in text and not text.startswith("{"):
                                try:
                                    padded = text + "=" * ((4 - len(text) % 4) % 4)
                                    decoded = base64.b64decode(padded).decode("utf-8")
                                    if "://" in decoded:
                                        text = decoded
                                except Exception:
                                    pass
                            configs.append(text)
                        else:
                            errors.append(f"{url} -> HTTP {response.status}")
                except Exception as e:
                    errors.append(f"{url} -> {type(e).__name__}")

        if errors and not configs:
            raise Exception("\n".join(errors))

        return "\n".join(configs), errors

    def _on_fetch_success(self, result_tuple):
        configs_text, errors = result_tuple
        self.btn_fetch_sub.setEnabled(True)
        self.btn_fetch_sub.setText(LanguageManager.tr("input_btn_fetch"))

        if configs_text:
            current_text = self.text_edit.toPlainText()
            if current_text.strip():
                self.text_edit.setPlainText(current_text + "\n" + configs_text)
            else:
                self.text_edit.setPlainText(configs_text)

            self.status_label.setText(LanguageManager.tr("input_status_fetch_success"))
            self.status_label.setStyleSheet("color: green;")

            msg = LanguageManager.tr("input_msg_fetch_success_body")
            if errors:
                err_str = "\n".join(errors)
                msg += LanguageManager.tr("input_msg_fetch_warn_body").format(
                    errors=err_str
                )

            QMessageBox.information(
                self, LanguageManager.tr("input_msg_fetch_success_title"), msg
            )
        else:
            self.status_label.setText(
                LanguageManager.tr("input_status_fetch_no_config")
            )
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.warning(
                self,
                LanguageManager.tr("input_msg_error_title"),
                LanguageManager.tr("input_msg_fetch_no_config_body"),
            )

    def _on_fetch_error(self, err_msg):
        self.btn_fetch_sub.setEnabled(True)
        self.btn_fetch_sub.setText(LanguageManager.tr("input_btn_fetch"))
        self.status_label.setText(LanguageManager.tr("input_status_fetch_error"))
        self.status_label.setStyleSheet("color: red;")

        msg_body = LanguageManager.tr("input_msg_fetch_error_body").format(
            err_msg=err_msg
        )
        QMessageBox.critical(
            self, LanguageManager.tr("input_msg_fetch_error_title"), msg_body
        )

    def process_configs(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(
                self,
                LanguageManager.tr("input_msg_error_title"),
                LanguageManager.tr("input_msg_warn_no_links"),
            )
            return

        group_name = self.cmb_group.currentText().strip() or "Default"

        lines = text.split("\n")
        valid_configs = []
        errors = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                config = self.parser_factory.parse_url(line)
                if config:
                    config.group_name = group_name
                    valid_configs.append(config)
            except ParseError as e:
                logger.debug(f"Skipped invalid config: {e}")
                errors += 1
            except Exception as e:

                logger.error(f"Unexpected error parsing config: {e}")
                errors += 1

        if not valid_configs:
            msg_body = LanguageManager.tr("input_msg_warn_no_valid_configs").format(
                errors=errors
            )
            QMessageBox.warning(
                self, LanguageManager.tr("input_msg_error_title"), msg_body
            )
            return

        self.import_btn.setEnabled(False)
        self.status_label.setText(
            LanguageManager.tr("input_status_saving").format(count=len(valid_configs))
        )
        self.status_label.setStyleSheet("color: blue;")

        self.worker = AsyncTaskWorker(self.repository.save_many(valid_configs))
        self.worker.finished_signal.connect(
            lambda saved_count: self.on_import_finished(
                saved_count, errors, len(valid_configs)
            )
        )
        self.worker.error_signal.connect(self.on_import_error)
        self.worker.start()

    def on_import_finished(self, saved_count, error_count, total_valid):
        self.import_btn.setEnabled(True)
        msg = LanguageManager.tr("input_msg_import_success_body").format(
            total=total_valid
        )
        if error_count > 0:
            msg += LanguageManager.tr("input_msg_import_success_errors").format(
                errors=error_count
            )

        self.status_label.setText(LanguageManager.tr("input_status_ready"))
        self.status_label.setStyleSheet("color: green;")
        self.text_edit.clear()
        self._load_groups()

        self.txt_sub_link.clear()
        QMessageBox.information(
            self, LanguageManager.tr("input_msg_import_report_title"), msg
        )

    def on_import_error(self, err_msg):
        self.import_btn.setEnabled(True)
        self.status_label.setText(LanguageManager.tr("input_status_import_error"))
        self.status_label.setStyleSheet("color: red;")

        msg_body = LanguageManager.tr("input_msg_import_error_body").format(
            err_msg=err_msg
        )
        QMessageBox.critical(
            self, LanguageManager.tr("input_msg_error_title"), msg_body
        )
