import datetime
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
)
from PySide6.QtCore import Qt

from gui.workers import AsyncTaskWorker
from domain.subscription import Subscription

class SubscriptionDialog(QDialog):
    def __init__(self, repository, sub_service, default_group="", parent=None):
        super().__init__(parent)
        self.repository = repository
        self.sub_service = sub_service
        self.default_group = default_group

        self.setWindowTitle("مدیریت سابسکریپشن‌ها")
        self.resize(700, 450)

        self.setLayoutDirection(Qt.RightToLeft)

        self.setup_ui()

        self.btn_add.clicked.connect(self.add_subscription)
        self.btn_delete.clicked.connect(self.delete_subscription)

        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QHBoxLayout()

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("نام گروه (مثلاً: VIP Servers)")
        if self.default_group:
            self.txt_name.setText(self.default_group)

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("لینک سابسکریپشن (http://...)")

        self.btn_add = QPushButton("افزودن لینک")
        self.btn_add.setStyleSheet(
            "background-color: #27ae60; color: white; padding: 5px;"
        )

        form_layout.addWidget(QLabel("نام آرشیو:"))
        form_layout.addWidget(self.txt_name)
        form_layout.addWidget(QLabel("لینک:"))
        form_layout.addWidget(self.txt_url, stretch=1)
        form_layout.addWidget(self.btn_add)

        layout.addLayout(form_layout)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["ID", "نام آرشیو", "لینک سابسکریپشن", "آخرین به‌روزرسانی"]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()

        self.btn_delete = QPushButton("حذف لینک انتخاب شده")
        self.btn_delete.setStyleSheet("background-color: #e74c3c; color: white;")

        self.btn_close = QPushButton("بستن")

        bottom_layout.addWidget(self.btn_delete)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_close)

        layout.addLayout(bottom_layout)

        self.btn_close.clicked.connect(self.close)

    def load_data(self):

        self.worker_load = AsyncTaskWorker(self.repository.get_subscriptions())
        self.worker_load.finished_signal.connect(self._on_data_loaded)
        self.worker_load.start()

    def _on_data_loaded(self, subs):

        self.table.setRowCount(len(subs))
        for row, sub in enumerate(subs):
            item_id = QTableWidgetItem(str(sub.id))
            item_id.setTextAlignment(Qt.AlignCenter)

            item_name = QTableWidgetItem(sub.name)
            item_url = QTableWidgetItem(sub.url)

            if sub.last_update == 0:
                date_str = "هرگز (نیازمند آپدیت)"
            else:
                date_str = datetime.datetime.fromtimestamp(sub.last_update).strftime(
                    "%Y-%m-%d %H:%M"
                )

            item_date = QTableWidgetItem(date_str)
            item_date.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_name)
            self.table.setItem(row, 2, item_url)
            self.table.setItem(row, 3, item_date)

    def add_subscription(self):

        name = self.txt_name.text().strip()
        url = self.txt_url.text().strip()

        if not name or not url:
            QMessageBox.warning(
                self, "خطا", "لطفاً نام آرشیو و لینک را به درستی وارد کنید."
            )
            return

        if not url.lower().startswith("http"):
            QMessageBox.warning(
                self,
                "خطا",
                "لینک سابسکریپشن نامعتبر است (باید با http یا https شروع شود).",
            )
            return

        self.btn_add.setEnabled(False)
        self.btn_add.setText("در حال ثبت...")

        new_sub = Subscription(name=name, url=url)

        self.worker_add = AsyncTaskWorker(self.repository.save_subscription(new_sub))
        self.worker_add.finished_signal.connect(self._on_add_finished)
        self.worker_add.start()

    def _on_add_finished(self, sub_id):
        self.btn_add.setEnabled(True)
        self.btn_add.setText("افزودن لینک")
        self.txt_url.clear()

        QMessageBox.information(
            self,
            "موفق",
            "لینک با موفقیت ذخیره شد. برای دریافت کانفیگ‌ها، دکمه آپدیت را در صفحه قبل بزنید.",
        )
        self.load_data()

    def delete_subscription(self):

        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "خطا", "لطفاً ابتدا یک لینک را از جدول انتخاب کنید."
            )
            return

        row = selected_items[0].row()
        sub_id_str = self.table.item(row, 0).text()
        sub_name = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self,
            "تایید حذف",
            f"آیا از حذف لینک سابسکریپشن مربوط به گروه '{sub_name}' مطمئن هستید؟\n\n(دقت کنید: با حذف این لینک، تمام کانفیگ‌های متصل به آن نیز از دیتابیس حذف خواهند شد!)",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            sub_id = int(sub_id_str)
            self.btn_delete.setEnabled(False)

            self.worker_delete = AsyncTaskWorker(
                self.repository.delete_subscription(sub_id)
            )
            self.worker_delete.finished_signal.connect(self._on_delete_finished)
            self.worker_delete.start()

    def _on_delete_finished(self, success):
        self.btn_delete.setEnabled(True)
        if success:
            QMessageBox.information(
                self,
                "موفق",
                "لینک سابسکریپشن و کانفیگ‌های متصل به آن با موفقیت حذف شدند.",
            )
            self.load_data()
        else:
            QMessageBox.critical(self, "خطا", "خطایی در حذف لینک رخ داد.")
