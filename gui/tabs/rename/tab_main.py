import json
import base64
import random
from urllib.parse import urlparse, urlunparse, quote
from PySide6.QtWidgets import QWidget, QMessageBox
from gui.workers import AsyncTaskWorker
from gui.language_manager import LanguageManager
from .ui_layout import RenameUiLayout
from gui.event_bus import event_bus

FOOD_EMOJIS = [
    "🍏",
    "🍎",
    "🍐",
    "🍊",
    "🍋",
    "🍌",
    "🍉",
    "🍇",
    "🍓",
    "🍈",
    "🍒",
    "🍑",
    "🥭",
    "🍍",
    "🥥",
    "🥝",
    "🍅",
    "🍆",
    "🥑",
    "🥦",
    "🥬",
    "🥒",
    "🌶",
    "🌽",
    "🥕",
    "🧄",
    "🧅",
    "🥔",
    "🍠",
    "🥐",
    "🥯",
    "🍞",
    "🥖",
    "🥨",
    "🧀",
    "🥚",
]
ANIMAL_EMOJIS = [
    "🐶",
    "🐱",
    "🐭",
    "🐹",
    "🐰",
    "🦊",
    "🐻",
    "🐼",
    "🐻‍❄️",
    "🐨",
    "🐯",
    "🦁",
    "🐮",
    "🐷",
    "🐸",
    "🐵",
    "🙈",
    "🙉",
    "🙊",
    "🐒",
    "🐔",
    "🐧",
    "🐦",
    "🐤",
    "🐣",
    "🐥",
    "🦆",
    "🦅",
    "🦉",
    "🦇",
    "🐺",
    "🐗",
    "🐴",
    "🦄",
    "🐝",
    "🪱",
    "🐛",
    "🦋",
    "🐌",
    "🐞",
    "🐜",
    "🪰",
    "🪲",
    "🪳",
    "🦟",
    "🦗",
    "🕷",
    "🕸",
    "🦂",
    "🐢",
]

def update_config_url(config) -> str:

    raw_url = config.raw_url
    protocol = config.protocol.lower()
    new_remark = config.remark
    if protocol == "vmess":
        try:
            b64_str = raw_url[8:]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode("utf-8")
            data = json.loads(decoded)
            data["ps"] = new_remark
            new_b64 = base64.b64encode(
                json.dumps(data, separators=(",", ":")).encode("utf-8")
            ).decode("utf-8")
            return f"vmess://{new_b64}"
        except Exception:
            return raw_url
    else:
        try:
            parsed = urlparse(raw_url)
            encoded_remark = quote(new_remark)
            return urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    encoded_remark,
                )
            )
        except Exception:
            return raw_url

class RenameTab(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.is_db_locked = False

        self.ui = RenameUiLayout()
        self.ui.setup_ui(self)

        self.ui.btn_refresh_groups.clicked.connect(self._load_groups)
        self.ui.btn_apply.clicked.connect(self.start_rename_process)

        event_bus.data_changed.connect(self._load_groups)

        event_bus.scan_lock_changed.connect(self.on_scan_lock_changed)

        self._load_groups()
        self.retranslate_ui()

    def retranslate_ui(self):

        self.ui.target_group.setTitle(LanguageManager.tr("ren_group_target"))
        self.ui.settings_group.setTitle(LanguageManager.tr("ren_group_settings"))

        self.ui.btn_refresh_groups.setToolTip(LanguageManager.tr("ren_tooltip_refresh"))
        self.ui.lbl_archive.setText(LanguageManager.tr("ren_lbl_archive"))
        self.ui.lbl_status.setText(LanguageManager.tr("ren_lbl_status"))

        self.ui.lbl_clear.setText(LanguageManager.tr("ren_lbl_clear"))
        self.ui.chk_clear_old.setText(LanguageManager.tr("ren_chk_clear_old"))

        self.ui.lbl_prefix.setText(LanguageManager.tr("ren_lbl_prefix"))
        self.ui.txt_prefix.setPlaceholderText(
            LanguageManager.tr("ren_placeholder_prefix")
        )

        self.ui.lbl_suffix.setText(LanguageManager.tr("ren_lbl_suffix"))
        self.ui.txt_suffix.setPlaceholderText(
            LanguageManager.tr("ren_placeholder_suffix")
        )

        self.ui.lbl_emoji.setText(LanguageManager.tr("ren_lbl_emoji"))
        self.ui.lbl_index.setText(LanguageManager.tr("ren_lbl_index"))
        self.ui.chk_number.setText(LanguageManager.tr("ren_chk_number"))

        if self.ui.cmb_status.count() > 0:
            self.ui.cmb_status.setItemText(0, LanguageManager.tr("ren_cmb_valid_only"))
            self.ui.cmb_status.setItemText(1, LanguageManager.tr("ren_cmb_all_configs"))

        if self.ui.cmb_archive.count() > 0:
            self.ui.cmb_archive.setItemText(
                0, LanguageManager.tr("ren_cmb_all_archives")
            )

        if self.ui.cmb_emoji.count() > 0:
            self.ui.cmb_emoji.setItemText(0, LanguageManager.tr("ren_cmb_emoji_none"))
            self.ui.cmb_emoji.setItemText(1, LanguageManager.tr("ren_cmb_emoji_food"))
            self.ui.cmb_emoji.setItemText(2, LanguageManager.tr("ren_cmb_emoji_animal"))
            self.ui.cmb_emoji.setItemText(3, LanguageManager.tr("ren_cmb_emoji_fire"))
            self.ui.cmb_emoji.setItemText(4, LanguageManager.tr("ren_cmb_emoji_check"))
            self.ui.cmb_emoji.setItemText(5, LanguageManager.tr("ren_cmb_emoji_rocket"))
            self.ui.cmb_emoji.setItemText(
                6, LanguageManager.tr("ren_cmb_emoji_lightning")
            )
            self.ui.cmb_emoji.setItemText(7, LanguageManager.tr("ren_cmb_emoji_crown"))
            self.ui.cmb_emoji.setItemText(8, LanguageManager.tr("ren_cmb_emoji_star"))
            self.ui.cmb_emoji.setItemText(
                9, LanguageManager.tr("ren_cmb_emoji_diamond")
            )

        if self.ui.cmb_emoji_pos.count() > 0:
            self.ui.cmb_emoji_pos.setItemText(
                0, LanguageManager.tr("ren_cmb_emoji_start")
            )
            self.ui.cmb_emoji_pos.setItemText(
                1, LanguageManager.tr("ren_cmb_emoji_end")
            )

        if self.ui.btn_apply.isEnabled():
            self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))
        else:
            self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_processing"))

        self.ui.btn_refresh_groups.setText(LanguageManager.tr("ren_btn_refresh_groups"))

    def on_scan_lock_changed(self, is_locked, group_name):

        self.is_db_locked = is_locked

        self.ui.btn_apply.setEnabled(not is_locked)
        self.ui.btn_refresh_groups.setEnabled(not is_locked)

        if is_locked:

            self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_processing"))
        else:
            self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))

    def _load_groups(self):
        if self.is_db_locked:
            return
        self.ui.btn_refresh_groups.setEnabled(False)
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
        self.ui.btn_refresh_groups.setEnabled(True)
        current = self.ui.cmb_archive.currentData()

        self.ui.cmb_archive.blockSignals(True)
        self.ui.cmb_archive.clear()
        self.ui.cmb_archive.addItem(
            LanguageManager.tr("ren_cmb_all_archives"), "ALL_ARCHIVES"
        )
        for g in groups:
            if g:
                self.ui.cmb_archive.addItem(f"📂 {g}", g)

        idx = self.ui.cmb_archive.findData(current)
        if idx >= 0:
            self.ui.cmb_archive.setCurrentIndex(idx)
        self.ui.cmb_archive.blockSignals(False)

    def start_rename_process(self):
        self.ui.btn_apply.setEnabled(False)
        self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_processing"))
        self.worker = AsyncTaskWorker(self._async_rename_logic())
        self.worker.finished_signal.connect(self._on_process_finished)
        self.worker.error_signal.connect(self._on_process_error)
        self.worker.start()

    async def _async_rename_logic(self):
        if self.is_db_locked:
            return

        self.ui.btn_apply.setEnabled(False)
        self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_processing"))
        proxies = await self.repository.get_all()

        target_archive = self.ui.cmb_archive.currentData()
        if target_archive != "ALL_ARCHIVES":
            proxies = [p for p in proxies if p.group_name == target_archive]

        target_status = self.ui.cmb_status.currentData()
        if target_status == "valid":
            proxies = [p for p in proxies if p.status == "Valid"]

        if not proxies:
            return 0

        prefix = self.ui.txt_prefix.text()
        suffix = self.ui.txt_suffix.text()
        clear_old = self.ui.chk_clear_old.isChecked()
        add_number = self.ui.chk_number.isChecked()

        updated_proxies = []
        for i, p in enumerate(proxies, start=1):
            old_remark = p.remark or ""

            if clear_old:
                new_remark = ""
            else:
                new_remark = old_remark

            new_remark = f"{prefix}{new_remark}{suffix}"

            emoji_choice = self.ui.cmb_emoji.currentData()
            if emoji_choice == "random_food":
                emoji = random.choice(FOOD_EMOJIS)
            elif emoji_choice == "random_animal":
                emoji = random.choice(ANIMAL_EMOJIS)
            elif emoji_choice != "none":
                emoji = emoji_choice
            else:
                emoji = ""

            if emoji:
                if self.ui.cmb_emoji_pos.currentData() == "start":
                    new_remark = f"{emoji} {new_remark}"
                else:
                    new_remark = f"{new_remark} {emoji}"

            if add_number:
                if new_remark.strip():
                    new_remark = f"{i:02d} | {new_remark.strip()}"
                else:
                    new_remark = f"{new_remark} {emoji}"

            p.remark = " ".join(new_remark.split())
            p.raw_url = update_config_url(p)
            updated_proxies.append(p)

        if updated_proxies:
            await self.repository.save_many(updated_proxies)
        return len(updated_proxies)

    def _on_process_finished(self, updated_count):
        self.ui.btn_apply.setEnabled(True)
        self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))
        if updated_count == 0:
            QMessageBox.warning(
                self,
                LanguageManager.tr("ren_msg_no_change_title"),
                LanguageManager.tr("ren_msg_no_change_body"),
            )
        else:
            QMessageBox.information(
                self,
                LanguageManager.tr("ren_msg_success_title"),
                LanguageManager.tr("ren_msg_success_body").format(count=updated_count),
            )

            event_bus.data_changed.emit()

    def _on_process_error(self, err_msg):
        self.ui.btn_apply.setEnabled(True)
        self.ui.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))
        QMessageBox.critical(
            self,
            LanguageManager.tr("ren_msg_error_title"),
            LanguageManager.tr("ren_msg_error_body").format(err_msg=err_msg),
        )
