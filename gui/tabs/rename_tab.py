import json
import base64
import random
from urllib.parse import urlparse, urlunparse, quote
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker
from gui.language_manager import LanguageManager

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
        self._setup_ui()
        self._load_groups()
        self.retranslate_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.target_group = QGroupBox()
        target_layout = QHBoxLayout(self.target_group)

        self.cmb_archive = QComboBox()
        self.cmb_archive.addItem("", "ALL_ARCHIVES")
        self.cmb_archive.setMinimumWidth(150)

        self.cmb_status = QComboBox()
        self.cmb_status.addItem("", "valid")
        self.cmb_status.addItem("", "all")

        self.btn_refresh_groups = QPushButton("🔄")
        self.btn_refresh_groups.setFixedWidth(40)
        self.btn_refresh_groups.clicked.connect(self._load_groups)

        self.lbl_archive = QLabel()
        self.lbl_status = QLabel()

        target_layout.addWidget(self.lbl_archive)
        target_layout.addWidget(self.cmb_archive)
        target_layout.addWidget(self.btn_refresh_groups)
        target_layout.addSpacing(20)
        target_layout.addWidget(self.lbl_status)
        target_layout.addWidget(self.cmb_status)
        target_layout.addStretch()
        layout.addWidget(self.target_group)

        self.settings_group = QGroupBox()
        form_layout = QFormLayout(self.settings_group)

        self.chk_clear_old = QCheckBox()
        self.chk_clear_old.setStyleSheet("color: #e84118; font-weight: bold;")
        self.lbl_clear = QLabel()
        form_layout.addRow(self.lbl_clear, self.chk_clear_old)

        self.txt_prefix = QLineEdit()
        self.lbl_prefix = QLabel()
        form_layout.addRow(self.lbl_prefix, self.txt_prefix)

        self.txt_suffix = QLineEdit()
        self.lbl_suffix = QLabel()
        form_layout.addRow(self.lbl_suffix, self.txt_suffix)

        emoji_layout = QHBoxLayout()
        self.cmb_emoji = QComboBox()
        self.cmb_emoji.addItem("", "none")
        self.cmb_emoji.addItem("", "random_food")
        self.cmb_emoji.addItem("", "random_animal")
        self.cmb_emoji.addItem("", "🔥")
        self.cmb_emoji.addItem("", "✅")
        self.cmb_emoji.addItem("", "🚀")
        self.cmb_emoji.addItem("", "⚡")
        self.cmb_emoji.addItem("", "👑")
        self.cmb_emoji.addItem("", "⭐")
        self.cmb_emoji.addItem("", "💎")

        self.cmb_emoji_pos = QComboBox()
        self.cmb_emoji_pos.addItem("", "start")
        self.cmb_emoji_pos.addItem("", "end")

        emoji_layout.addWidget(self.cmb_emoji)
        emoji_layout.addWidget(self.cmb_emoji_pos)

        self.lbl_emoji = QLabel()
        form_layout.addRow(self.lbl_emoji, emoji_layout)

        self.chk_number = QCheckBox()
        self.lbl_index = QLabel()
        form_layout.addRow(self.lbl_index, self.chk_number)
        layout.addWidget(self.settings_group)

        self.btn_apply = QPushButton()
        self.btn_apply.setMinimumHeight(45)
        self.btn_apply.setStyleSheet(
            "background-color: #8c7ae6; color: white; font-weight: bold; border-radius: 5px; font-size: 14px;"
        )
        self.btn_apply.clicked.connect(self.start_rename_process)

        layout.addStretch()
        layout.addWidget(self.btn_apply)

    def retranslate_ui(self):

        self.target_group.setTitle(LanguageManager.tr("ren_group_target"))
        self.settings_group.setTitle(LanguageManager.tr("ren_group_settings"))

        self.btn_refresh_groups.setToolTip(LanguageManager.tr("ren_tooltip_refresh"))
        self.lbl_archive.setText(LanguageManager.tr("ren_lbl_archive"))
        self.lbl_status.setText(LanguageManager.tr("ren_lbl_status"))

        self.lbl_clear.setText(LanguageManager.tr("ren_lbl_clear"))
        self.chk_clear_old.setText(LanguageManager.tr("ren_chk_clear_old"))

        self.lbl_prefix.setText(LanguageManager.tr("ren_lbl_prefix"))
        self.txt_prefix.setPlaceholderText(LanguageManager.tr("ren_placeholder_prefix"))

        self.lbl_suffix.setText(LanguageManager.tr("ren_lbl_suffix"))
        self.txt_suffix.setPlaceholderText(LanguageManager.tr("ren_placeholder_suffix"))

        self.lbl_emoji.setText(LanguageManager.tr("ren_lbl_emoji"))
        self.lbl_index.setText(LanguageManager.tr("ren_lbl_index"))
        self.chk_number.setText(LanguageManager.tr("ren_chk_number"))

        if self.cmb_status.count() > 0:
            self.cmb_status.setItemText(0, LanguageManager.tr("ren_cmb_valid_only"))
            self.cmb_status.setItemText(1, LanguageManager.tr("ren_cmb_all_configs"))

        if self.cmb_archive.count() > 0:
            self.cmb_archive.setItemText(0, LanguageManager.tr("ren_cmb_all_archives"))

        if self.cmb_emoji.count() > 0:
            self.cmb_emoji.setItemText(0, LanguageManager.tr("ren_cmb_emoji_none"))
            self.cmb_emoji.setItemText(1, LanguageManager.tr("ren_cmb_emoji_food"))
            self.cmb_emoji.setItemText(2, LanguageManager.tr("ren_cmb_emoji_animal"))
            self.cmb_emoji.setItemText(3, LanguageManager.tr("ren_cmb_emoji_fire"))
            self.cmb_emoji.setItemText(4, LanguageManager.tr("ren_cmb_emoji_check"))
            self.cmb_emoji.setItemText(5, LanguageManager.tr("ren_cmb_emoji_rocket"))
            self.cmb_emoji.setItemText(6, LanguageManager.tr("ren_cmb_emoji_lightning"))
            self.cmb_emoji.setItemText(7, LanguageManager.tr("ren_cmb_emoji_crown"))
            self.cmb_emoji.setItemText(8, LanguageManager.tr("ren_cmb_emoji_star"))
            self.cmb_emoji.setItemText(9, LanguageManager.tr("ren_cmb_emoji_diamond"))

        if self.cmb_emoji_pos.count() > 0:
            self.cmb_emoji_pos.setItemText(0, LanguageManager.tr("ren_cmb_emoji_start"))
            self.cmb_emoji_pos.setItemText(1, LanguageManager.tr("ren_cmb_emoji_end"))

        if self.btn_apply.isEnabled():
            self.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))
        else:
            self.btn_apply.setText(LanguageManager.tr("ren_btn_processing"))

    def _load_groups(self):
        self.btn_refresh_groups.setEnabled(False)
        self.worker_groups = AsyncTaskWorker(self.repository.get_groups())
        self.worker_groups.finished_signal.connect(self._on_groups_loaded)
        self.worker_groups.start()

    def _on_groups_loaded(self, groups):
        self.btn_refresh_groups.setEnabled(True)
        current = self.cmb_archive.currentData()

        self.cmb_archive.blockSignals(True)
        self.cmb_archive.clear()
        self.cmb_archive.addItem(
            LanguageManager.tr("ren_cmb_all_archives"), "ALL_ARCHIVES"
        )
        for g in groups:
            if g:
                self.cmb_archive.addItem(f"📂 {g}", g)

        idx = self.cmb_archive.findData(current)
        if idx >= 0:
            self.cmb_archive.setCurrentIndex(idx)
        self.cmb_archive.blockSignals(False)

    def start_rename_process(self):
        self.btn_apply.setEnabled(False)
        self.btn_apply.setText(LanguageManager.tr("ren_btn_processing"))
        self.worker = AsyncTaskWorker(self._async_rename_logic())
        self.worker.finished_signal.connect(self._on_process_finished)
        self.worker.error_signal.connect(self._on_process_error)
        self.worker.start()

    async def _async_rename_logic(self):
        proxies = await self.repository.get_all()

        target_archive = self.cmb_archive.currentData()
        if target_archive != "ALL_ARCHIVES":
            proxies = [p for p in proxies if p.group_name == target_archive]

        target_status = self.cmb_status.currentData()
        if target_status == "valid":
            proxies = [p for p in proxies if p.status == "Valid"]

        if not proxies:
            return 0

        prefix = self.txt_prefix.text()
        suffix = self.txt_suffix.text()
        clear_old = self.chk_clear_old.isChecked()
        add_number = self.chk_number.isChecked()

        updated_proxies = []
        for i, p in enumerate(proxies, start=1):
            old_remark = p.remark or ""

            if clear_old:
                new_remark = ""
            else:
                new_remark = old_remark

            new_remark = f"{prefix}{new_remark}{suffix}"

            emoji_choice = self.cmb_emoji.currentData()
            if emoji_choice == "random_food":
                emoji = random.choice(FOOD_EMOJIS)
            elif emoji_choice == "random_animal":
                emoji = random.choice(ANIMAL_EMOJIS)
            elif emoji_choice != "none":
                emoji = emoji_choice
            else:
                emoji = ""

            if emoji:
                if self.cmb_emoji_pos.currentData() == "start":
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
        self.btn_apply.setEnabled(True)
        self.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))
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

    def _on_process_error(self, err_msg):
        self.btn_apply.setEnabled(True)
        self.btn_apply.setText(LanguageManager.tr("ren_btn_apply"))
        QMessageBox.critical(
            self,
            LanguageManager.tr("ren_msg_error_title"),
            LanguageManager.tr("ren_msg_error_body").format(err_msg=err_msg),
        )
