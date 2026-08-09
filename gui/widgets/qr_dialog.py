import qrcode
from io import BytesIO
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

class QRDialog(QDialog):
    def __init__(self, title, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"QR Code: {title}")
        self.resize(450, 450)
        layout = QVBoxLayout(self)

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qimg = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimg)

        lbl = QLabel()

        scaled_pixmap = pixmap.scaled(
            420,
            420,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        lbl.setPixmap(scaled_pixmap)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
