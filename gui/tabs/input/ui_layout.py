from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QLabel,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
)

class InputUiLayout:
    def setup_ui(self, parent_widget):
\
\
\

        layout = QVBoxLayout(parent_widget)

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

        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.import_btn)

        layout.addLayout(bottom_layout)
