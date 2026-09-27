
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QCheckBox
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt
from gui.language_manager import LanguageManager


class AnimatedToggle(QCheckBox):
    """سوییچ کشویی سفارشی هوشمند (داینامیک)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(170, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._padding = 4
        self._thumb_size = self.height() - (self._padding * 2)
        self._left_pos = self._padding
        self._right_pos = self.width() - self._thumb_size - self._padding

        self._thumb_pos = self._right_pos

        self.animation = QPropertyAnimation(self, b"thumb_pos")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutBack)
        self.animation.setDuration(400)
        self.stateChanged.connect(self.setup_animation)

    @Property(float)
    def thumb_pos(self):
        return self._thumb_pos

    @thumb_pos.setter
    def thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()

    def setup_animation(self, state):
        self.animation.stop()
        if state:
            self.animation.setEndValue(self._left_pos)
        else:
            self.animation.setEndValue(self._right_pos)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor("#0097e6") if self.isChecked() else QColor("#2f3640")
        p.setBrush(bg_color)
        p.setPen(Qt.PenStyle.NoPen)
        radius = self.height() / 2
        p.drawRoundedRect(0, 0, self.width(), self.height(), radius, radius)

        font = p.font()
        font.setBold(True)
        font.setPointSize(10)
        p.setFont(font)
        p.setPen(QColor("white"))

        if self.isChecked():
            text_rect = QRectF(
                self._thumb_size + self._padding,
                0,
                self.width() - self._thumb_size - (self._padding * 2),
                self.height(),
            )
            text = LanguageManager.tr("conn_mode_tun")
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        else:
            text_rect = QRectF(
                self._padding,
                0,
                self.width() - self._thumb_size - (self._padding * 2),
                self.height(),
            )
            text = LanguageManager.tr("conn_mode_proxy")
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        p.setBrush(QColor("white"))
        p.drawEllipse(
            int(self._thumb_pos), self._padding, self._thumb_size, self._thumb_size
        )
        p.end()

    def hitButton(self, pos):
        return self.rect().contains(pos)


class ConnectUiLayout:
    def setup_ui(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_status = QLabel()
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        layout.addSpacing(30)

        self.btn_power = QPushButton()
        self.btn_power.setFixedSize(150, 150)
        self.btn_power.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_power, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(25)

        self.chk_tun = AnimatedToggle()
        layout.addWidget(self.chk_tun, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(25)

        self.lbl_node_title = QLabel()
        self.lbl_node_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_node_title.setStyleSheet("color: #a4b0be; font-size: 14px;")
        layout.addWidget(self.lbl_node_title)

        self.lbl_selected_node = QLabel()
        self.lbl_selected_node.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_selected_node.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #00a8ff;"
        )
        layout.addWidget(self.lbl_selected_node)
