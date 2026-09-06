from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog, QInputDialog
from gui.language_manager import LanguageManager
from gui.workers import AsyncTaskWorker
from gui.event_bus import event_bus
import base64

class ImportManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def import_from_clipboard(self):

        clipboard_text = QApplication.clipboard().text().strip()
        if not clipboard_text:
            QMessageBox.warning(
                self.main_window,
                LanguageManager.tr("msg_error"),
                LanguageManager.tr("msg_clipboard_empty"),
            )
            return
        self._process_imported_text(clipboard_text)

    def import_from_file(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            LanguageManager.tr("msg_select_file"),
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read().strip()
                self._process_imported_text(file_content)
            except Exception as e:
                QMessageBox.critical(
                    self.main_window,
                    LanguageManager.tr("msg_error"),
                    LanguageManager.tr("msg_file_read_err").format(err=e),
                )

    def _process_imported_text(self, text):

        target_group = self.main_window.archive_tab.current_group_filter
        if not target_group:
            target_group = "Default"

        try:
            clean_b64 = text.replace("\n", "").replace("\r", "").strip()
            padded = clean_b64 + "=" * (-len(clean_b64) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")
            if "://" in decoded or "http" in decoded:
                text = decoded
        except Exception:
            pass

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        raw_configs = []
        sub_links = []

        for line in lines:
            if line.startswith(("http://", "https://")):
                sub_links.append(line)
            elif "://" in line:
                raw_configs.append(line)
            else:
                try:
                    padded = line + "=" * (-len(line) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8").strip()
                    if "://" in decoded:
                        raw_configs.append(decoded)
                except Exception:
                    pass

        if not raw_configs and not sub_links:
            QMessageBox.warning(
                self.main_window,
                LanguageManager.tr("msg_error"),
                LanguageManager.tr("msg_no_valid_config"),
            )
            return

        added_subs_count = 0
        parse_errors = []
        user_cancelled_sub = False

        subs_to_add = []
        if sub_links:
            groups = [g for g in self.main_window.archive_tab.available_groups if g]
            if target_group in groups:
                groups.remove(target_group)
            groups.insert(0, target_group)

            sub_group, ok = QInputDialog.getItem(
                self.main_window,
                LanguageManager.tr("sub_import_title"),
                LanguageManager.tr("sub_import_prompt"),
                groups,
                0,
                True,
            )

            if ok and sub_group.strip():
                final_sub_group = sub_group.strip()
                from domain.subscription import Subscription

                for link in sub_links:
                    sub = Subscription(name=final_sub_group, url=link)
                    subs_to_add.append(sub)
                    added_subs_count += 1

                self.main_window.archive_tab.on_group_changed(final_sub_group)
                target_group = final_sub_group
            else:
                user_cancelled_sub = True

        proxies_to_add = []
        if raw_configs:
            for raw in raw_configs:
                try:
                    proxy = self.main_window.parser_factory.parse_url(raw)
                    if isinstance(proxy, list):
                        for p in proxy:
                            p.group_name = target_group
                            proxies_to_add.append(p)
                    elif proxy:
                        proxy.group_name = target_group
                        proxies_to_add.append(proxy)
                except Exception as e:
                    parse_errors.append(f"{raw[:20]}... -> {str(e)}")

        if not proxies_to_add and not subs_to_add:
            if not user_cancelled_sub:
                err_msg = LanguageManager.tr("msg_parser_err_body")
                if parse_errors:
                    unique_errors = list(set(parse_errors))[:3]
                    err_msg += LanguageManager.tr("msg_parser_err_details") + "\n".join(
                        unique_errors
                    )
                QMessageBox.warning(
                    self.main_window,
                    LanguageManager.tr("msg_parser_err_title"),
                    err_msg,
                )
            return

        async def save_all_data():
            saved_proxies = 0
            if proxies_to_add:
                saved_proxies = await self.main_window.repository.save_many(
                    proxies_to_add
                )

            for sub in subs_to_add:
                await self.main_window.repository.save_subscription(sub)

            return saved_proxies

        self.worker = AsyncTaskWorker(save_all_data())

        self.worker.finished_signal.connect(
            lambda saved_count: self._on_import_finished(
                saved_count, added_subs_count, target_group
            )
        )
        self.worker.error_signal.connect(
            lambda err: QMessageBox.critical(
                self.main_window,
                LanguageManager.tr("msg_error"),
                LanguageManager.tr("msg_db_save_err").format(err=err),
            )
        )
        self.worker.start()

    def _on_import_finished(self, saved_count, added_subs_count, target_group):

        event_bus.data_changed.emit()

        msg = ""
        if saved_count > 0:
            msg += LanguageManager.tr("msg_import_success_configs").format(
                count=saved_count, group=target_group
            )
        if added_subs_count > 0:
            msg += LanguageManager.tr("msg_import_success_subs").format(
                count=added_subs_count
            )

        QMessageBox.information(
            self.main_window, LanguageManager.tr("msg_import_success_title"), msg
        )

    def show_manual_config_window(self):
        QMessageBox.information(
            self.main_window,
            LanguageManager.tr("msg_dev_title"),
            LanguageManager.tr("msg_dev_body"),
        )
