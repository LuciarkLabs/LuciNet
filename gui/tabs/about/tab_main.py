from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from gui.language_manager import LanguageManager
from gui.workers import AsyncTaskWorker
from services.updater import UpdateChecker
from .ui_layout import AboutUiLayout

class AboutTab(QWidget):
    def __init__(self):
        super().__init__()

        self.updater = UpdateChecker(current_version="1.2.0")

        self.ui = AboutUiLayout()
        self.ui.setup_ui(self)

        self.ui.btn_github.clicked.connect(self.open_github)
        self.ui.btn_telegram.clicked.connect(self.open_telegram)

        self.ui.btn_update.clicked.connect(lambda: self.check_for_update(silent=False))

        self.retranslate_ui()

        self.check_for_update(silent=True)

    def retranslate_ui(self):

        self.ui.lbl_desc.setText(LanguageManager.tr("abt_desc"))
        self.ui.btn_github.setText(LanguageManager.tr("abt_btn_github"))
        self.ui.btn_telegram.setText(LanguageManager.tr("abt_btn_telegram"))

        if self.ui.btn_update.isEnabled():
            self.ui.btn_update.setText(LanguageManager.tr("abt_btn_update"))
        else:
            self.ui.btn_update.setText(LanguageManager.tr("abt_msg_checking"))

    def open_github(self):

        QDesktopServices.openUrl(QUrl("https://github.com/LuciarkLabs/LuciNet"))

    def open_telegram(self):

        QDesktopServices.openUrl(QUrl("https://t.me/LuciarkLabs"))

    def check_for_update(self, silent=False):

        self.is_silent_update = silent

        self.ui.btn_update.setEnabled(False)
        self.ui.btn_update.setText(LanguageManager.tr("abt_msg_checking"))

        self.worker = AsyncTaskWorker(self.updater.check_for_updates())
        self.worker.finished_signal.connect(self._on_update_result)
        self.worker.start()

    def _on_update_result(self, result):

        self.ui.btn_update.setEnabled(True)
        self.ui.btn_update.setText(LanguageManager.tr("abt_btn_update"))

        has_update, latest_version, download_url = result

        if has_update:

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(LanguageManager.tr("abt_msg_update_avail_title"))
            msg_box.setText(
                LanguageManager.tr("abt_msg_update_avail_body").format(
                    version=latest_version
                )
            )

            btn_download = msg_box.addButton(
                LanguageManager.tr("abt_btn_download"), QMessageBox.ActionRole
            )
            btn_close = msg_box.addButton(
                LanguageManager.tr("abt_btn_close"), QMessageBox.RejectRole
            )

            msg_box.exec()

            if msg_box.clickedButton() == btn_download:
                QDesktopServices.openUrl(QUrl(download_url))
        else:

            if not self.is_silent_update:
                QMessageBox.information(
                    self,
                    LanguageManager.tr("abt_msg_up_to_date_title"),
                    LanguageManager.tr("abt_msg_up_to_date_body"),
                )
