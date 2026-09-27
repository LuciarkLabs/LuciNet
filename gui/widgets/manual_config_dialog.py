from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
    QCheckBox,
    QGroupBox,
    QTextEdit,
    QScrollArea,
    QWidget
)
from PySide6.QtGui import QIntValidator
import json
from gui.language_manager import LanguageManager
from gui.builders.manual_config_builder import ManualConfigBuilder, ManualConfigInput
from parser.exceptions import ParseError, ValidationError, UnsupportedProtocolError

class ManualConfigDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle(LanguageManager.tr("menu_add_manual"))
        self.setMinimumWidth(550)
        self.setMinimumHeight(650)
        self.generated_url = None
        self._setup_ui()
        self._connect_signals()
        self._update_fields_visibility()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        proto_group = QGroupBox("Protocol")
        proto_layout = QFormLayout(proto_group)
        self.cmb_protocol = QComboBox()
        self.cmb_protocol.addItems(["vless", "vmess", "trojan", "ss"])
        proto_layout.addRow("Type:", self.cmb_protocol)
        
        self.cmb_vmess_mode = QComboBox()
        self.cmb_vmess_mode.addItems(["aead", "legacy"])
        self.lbl_vmess_mode = QLabel("VMess Mode:")
        proto_layout.addRow(self.lbl_vmess_mode, self.cmb_vmess_mode)
        
        self.cmb_vmess_enc = QComboBox()
        self.cmb_vmess_enc.addItems(["auto", "aes-128-gcm", "chacha20-poly1305", "none"])
        self.lbl_vmess_enc = QLabel("VMess AEAD Encryption:")
        proto_layout.addRow(self.lbl_vmess_enc, self.cmb_vmess_enc)

        self.cmb_vmess_legacy_scy = QComboBox()
        self.cmb_vmess_legacy_scy.addItems(["auto", "aes-128-gcm", "chacha20-poly1305", "none", "zero"])
        self.lbl_vmess_legacy_scy = QLabel("VMess Legacy Security (scy):")
        proto_layout.addRow(self.lbl_vmess_legacy_scy, self.cmb_vmess_legacy_scy)
        
        layout.addWidget(proto_group)

        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)
        self.txt_remark = QLineEdit()
        self.txt_server = QLineEdit()
        self.txt_port = QLineEdit()
        self.txt_port.setValidator(QIntValidator(1, 65535, self))
        
        basic_layout.addRow("Remark:", self.txt_remark)
        basic_layout.addRow("Server (IP/Domain):", self.txt_server)
        basic_layout.addRow("Port:", self.txt_port)
        layout.addWidget(basic_group)

        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout(auth_group)
        self.lbl_auth = QLabel("UUID:")
        self.txt_auth = QLineEdit()
        
        self.lbl_ss_method = QLabel("Method:")
        self.cmb_ss_method = QComboBox()
        self.cmb_ss_method.setEditable(True)
        self.cmb_ss_method.addItems([
            "aes-128-gcm", "aes-256-gcm", "chacha20-ietf-poly1305",
            "xchacha20-ietf-poly1305", "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm"
        ])
        
        auth_layout.addRow(self.lbl_ss_method, self.cmb_ss_method)
        auth_layout.addRow(self.lbl_auth, self.txt_auth)
        layout.addWidget(auth_group)

        self.transport_group = QGroupBox("Transport")
        transport_layout = QFormLayout(self.transport_group)
        
        self.cmb_network = QComboBox()
        self.cmb_network.addItems(["raw", "websocket", "xhttp", "mkcp", "grpc", "httpupgrade", "hysteria"])
        transport_layout.addRow("Network:", self.cmb_network)
        
        self.lbl_path = QLabel("Path:")
        self.txt_path = QLineEdit()
        self.lbl_host = QLabel("Host:")
        self.txt_host = QLineEdit()
        
        transport_layout.addRow(self.lbl_path, self.txt_path)
        transport_layout.addRow(self.lbl_host, self.txt_host)
        
        self.lbl_grpc_mode = QLabel("gRPC Mode:")
        self.cmb_grpc_mode = QComboBox()
        self.cmb_grpc_mode.addItems(["", "gun", "multi", "guna"])
        self.lbl_grpc_auth = QLabel("Authority:")
        self.txt_grpc_auth = QLineEdit()
        
        transport_layout.addRow(self.lbl_grpc_mode, self.cmb_grpc_mode)
        transport_layout.addRow(self.lbl_grpc_auth, self.txt_grpc_auth)
        
        self.lbl_xhttp_mode = QLabel("XHTTP Mode:")
        self.cmb_xhttp_mode = QComboBox()
        self.cmb_xhttp_mode.addItems(["", "auto"])
        self.cmb_xhttp_mode.setEditable(True)
        self.lbl_xhttp_extra = QLabel("XHTTP Extra:")
        self.txt_xhttp_extra = QLineEdit()
        
        transport_layout.addRow(self.lbl_xhttp_mode, self.cmb_xhttp_mode)
        transport_layout.addRow(self.lbl_xhttp_extra, self.txt_xhttp_extra)
        
        self.lbl_mkcp_mtu = QLabel("MTU:")
        self.txt_mkcp_mtu = QLineEdit()
        self.lbl_mkcp_tti = QLabel("TTI:")
        self.txt_mkcp_tti = QLineEdit()
        
        transport_layout.addRow(self.lbl_mkcp_mtu, self.txt_mkcp_mtu)
        transport_layout.addRow(self.lbl_mkcp_tti, self.txt_mkcp_tti)
        
        layout.addWidget(self.transport_group)

        self.sec_group = QGroupBox("Security")
        sec_layout = QFormLayout(self.sec_group)
        
        self.cmb_security = QComboBox()
        self.cmb_security.addItems(["none", "tls", "reality"])
        sec_layout.addRow("Security:", self.cmb_security)
        
        self.lbl_sni = QLabel("SNI:")
        self.txt_sni = QLineEdit()
        self.lbl_fp = QLabel("Fingerprint (fp):")
        self.cmb_fp = QComboBox()
        self.cmb_fp.setEditable(True)
        self.cmb_fp.addItems(["", "chrome", "firefox", "safari", "edge", "ios", "android", "random"])
        self.lbl_alpn = QLabel("ALPN:")
        self.txt_alpn = QLineEdit()
        self.lbl_ech = QLabel("ECH:")
        self.txt_ech = QLineEdit()
        self.lbl_pcs = QLabel("PCS:")
        self.txt_pcs = QLineEdit()
        self.lbl_vcn = QLabel("VCN:")
        self.txt_vcn = QLineEdit()
        
        sec_layout.addRow(self.lbl_sni, self.txt_sni)
        sec_layout.addRow(self.lbl_fp, self.cmb_fp)
        sec_layout.addRow(self.lbl_alpn, self.txt_alpn)
        sec_layout.addRow(self.lbl_ech, self.txt_ech)
        sec_layout.addRow(self.lbl_pcs, self.txt_pcs)
        sec_layout.addRow(self.lbl_vcn, self.txt_vcn)
        
        self.lbl_pbk = QLabel("Public Key (pbk):")
        self.txt_pbk = QLineEdit()
        self.lbl_sid = QLabel("Short ID (sid):")
        self.txt_sid = QLineEdit()
        self.lbl_spx = QLabel("Spider X (spx):")
        self.txt_spx = QLineEdit()
        self.lbl_pqv = QLabel("PQV:")
        self.txt_pqv = QLineEdit()
        
        sec_layout.addRow(self.lbl_pbk, self.txt_pbk)
        sec_layout.addRow(self.lbl_sid, self.txt_sid)
        sec_layout.addRow(self.lbl_spx, self.txt_spx)
        sec_layout.addRow(self.lbl_pqv, self.txt_pqv)
        
        layout.addWidget(self.sec_group)
        
        adv_group = QGroupBox("Advanced / Optional")
        adv_layout = QFormLayout(adv_group)
        
        self.lbl_vless_flow = QLabel("VLESS Flow:")
        self.cmb_vless_flow = QComboBox()
        self.cmb_vless_flow.addItems(["", "xtls-rprx-vision", "xtls-rprx-vision-udp443"])
        
        self.lbl_vless_enc = QLabel("VLESS Encryption (ML-KEM):")
        self.txt_vless_enc = QLineEdit()
        self.txt_vless_enc.setPlaceholderText("mlkem768x25519plus.native.1rtt....")
        
        adv_layout.addRow(self.lbl_vless_flow, self.cmb_vless_flow)
        adv_layout.addRow(self.lbl_vless_enc, self.txt_vless_enc)
        
        self.chk_ss_uot = QCheckBox("Enable UOT")
        self.lbl_ss_plugin = QLabel("SS Plugin:")
        self.txt_ss_plugin = QLineEdit()
        
        adv_layout.addRow("SS UOT:", self.chk_ss_uot)
        adv_layout.addRow(self.lbl_ss_plugin, self.txt_ss_plugin)
        
        self.chk_allow_insecure = QCheckBox("Allow Insecure (Deprecated)")
        self.lbl_allow_insecure = QLabel("Legacy:")
        adv_layout.addRow(self.lbl_allow_insecure, self.chk_allow_insecure)
        
        self.lbl_fm = QLabel("FinalMask JSON:")
        self.txt_fm = QTextEdit()
        self.txt_fm.setMaximumHeight(60)
        adv_layout.addRow(self.lbl_fm, self.txt_fm)
        
        layout.addWidget(adv_group)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Generate & Validate")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def _connect_signals(self):
        self.cmb_protocol.currentIndexChanged.connect(self._update_fields_visibility)
        self.cmb_vmess_mode.currentIndexChanged.connect(self._update_fields_visibility)
        self.cmb_network.currentIndexChanged.connect(self._update_fields_visibility)
        self.cmb_security.currentIndexChanged.connect(self._update_fields_visibility)
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save_clicked)

    def _update_fields_visibility(self):
        protocol = self.cmb_protocol.currentText()
        vmess_mode = self.cmb_vmess_mode.currentText()
        network = self.cmb_network.currentText()
        security = self.cmb_security.currentText()
        
        is_ss = (protocol == "ss")
        is_vless = (protocol == "vless")
        is_vmess = (protocol == "vmess")
        is_trojan = (protocol == "trojan")
        
        is_vmess_aead = (is_vmess and vmess_mode == "aead")
        is_vmess_legacy = (is_vmess and vmess_mode == "legacy")

        current_network = self.cmb_network.currentText()
        current_sec = self.cmb_security.currentText()
        
        self.cmb_network.blockSignals(True)
        self.cmb_security.blockSignals(True)
        
        self.cmb_network.clear()
        self.cmb_security.clear()
        
        if is_vmess_legacy:
            valid_networks = ["raw", "websocket", "httpupgrade"]
        else:
            if current_sec == "reality":
                valid_networks = ["raw", "xhttp", "grpc"]
            else:
                valid_networks = ["raw", "websocket", "xhttp", "mkcp", "grpc", "httpupgrade", "hysteria"]
                
        self.cmb_network.addItems(valid_networks)
        if current_network in valid_networks:
            self.cmb_network.setCurrentText(current_network)
        else:
            self.cmb_network.setCurrentIndex(0)
            
        network = self.cmb_network.currentText()
        
        if is_vmess_legacy:
            valid_securities = ["none", "tls"]
        else:
            if network == "hysteria":
                valid_securities = ["tls"]
            elif network in ("websocket", "ws", "mkcp", "httpupgrade"):
                valid_securities = ["none", "tls"]
            else:
                valid_securities = ["none", "tls", "reality"]
                
        self.cmb_security.addItems(valid_securities)
        if current_sec in valid_securities:
            self.cmb_security.setCurrentText(current_sec)
        else:
            self.cmb_security.setCurrentIndex(0)
            
        security = self.cmb_security.currentText()
        
        self.cmb_network.blockSignals(False)
        self.cmb_security.blockSignals(False)
        
        self.lbl_vmess_mode.setVisible(is_vmess)
        self.cmb_vmess_mode.setVisible(is_vmess)
        
        self.lbl_vmess_enc.setVisible(is_vmess_aead)
        self.cmb_vmess_enc.setVisible(is_vmess_aead)

        self.lbl_vmess_legacy_scy.setVisible(is_vmess_legacy)
        self.cmb_vmess_legacy_scy.setVisible(is_vmess_legacy)
        
        self.lbl_ss_method.setVisible(is_ss)
        self.cmb_ss_method.setVisible(is_ss)
        
        self.chk_ss_uot.setVisible(is_ss)
        self.lbl_ss_plugin.setVisible(is_ss)
        self.txt_ss_plugin.setVisible(is_ss)
        
        self.transport_group.setVisible(not is_ss)
        self.sec_group.setVisible(not is_ss)
        
        if is_vless or is_vmess:
            self.lbl_auth.setText("UUID:")
        else:
            self.lbl_auth.setText("Password:")
            
        self.lbl_vless_flow.setVisible(is_vless)
        self.cmb_vless_flow.setVisible(is_vless)
        self.lbl_vless_enc.setVisible(is_vless)
        self.txt_vless_enc.setVisible(is_vless)
        
        show_allow_insecure = (not is_ss) and (security in ("tls", "reality"))
        self.lbl_allow_insecure.setVisible(show_allow_insecure)
        self.chk_allow_insecure.setVisible(show_allow_insecure)

        show_fm = is_vless or is_vmess_aead or is_trojan
        self.lbl_fm.setVisible(show_fm)
        self.txt_fm.setVisible(show_fm)

        is_http_like = network in ("websocket", "ws", "httpupgrade")
        self.lbl_path.setVisible(is_http_like or network == "xhttp")
        self.txt_path.setVisible(is_http_like or network == "xhttp")
        
        self.lbl_host.setVisible(is_http_like or network == "xhttp")
        self.txt_host.setVisible(is_http_like or network == "xhttp")
        
        is_grpc = network == "grpc"
        self.lbl_grpc_mode.setVisible(is_grpc)
        self.cmb_grpc_mode.setVisible(is_grpc)
        self.lbl_grpc_auth.setVisible(is_grpc)
        self.txt_grpc_auth.setVisible(is_grpc)
        
        if is_grpc:
            self.lbl_path.setVisible(not is_ss)
            self.txt_path.setVisible(not is_ss)
            self.lbl_path.setText("Service Name:")
        else:
            self.lbl_path.setText("Path:")
            
        is_xhttp = network == "xhttp"
        self.lbl_xhttp_mode.setVisible(is_xhttp and not is_ss)
        self.cmb_xhttp_mode.setVisible(is_xhttp and not is_ss)
        self.lbl_xhttp_extra.setVisible(is_xhttp and not is_ss)
        self.txt_xhttp_extra.setVisible(is_xhttp and not is_ss)
        
        is_mkcp = network == "mkcp"
        self.lbl_mkcp_mtu.setVisible(is_mkcp and not is_ss)
        self.txt_mkcp_mtu.setVisible(is_mkcp and not is_ss)
        self.lbl_mkcp_tti.setVisible(is_mkcp and not is_ss)
        self.txt_mkcp_tti.setVisible(is_mkcp and not is_ss)
        
        is_tls = security in ("tls", "reality")
        self.lbl_sni.setVisible(is_tls and not is_ss)
        self.txt_sni.setVisible(is_tls and not is_ss)
        self.lbl_fp.setVisible(is_tls and not is_ss)
        self.cmb_fp.setVisible(is_tls and not is_ss)
        self.lbl_alpn.setVisible(is_tls and not is_ss)
        self.txt_alpn.setVisible(is_tls and not is_ss)
        self.lbl_ech.setVisible(is_tls and not is_ss)
        self.txt_ech.setVisible(is_tls and not is_ss)
        self.lbl_pcs.setVisible(is_tls and not is_ss)
        self.txt_pcs.setVisible(is_tls and not is_ss)
        self.lbl_vcn.setVisible(is_tls and not is_ss)
        self.txt_vcn.setVisible(is_tls and not is_ss)
        
        is_reality = security == "reality"
        self.lbl_pbk.setVisible(is_reality and not is_ss)
        self.txt_pbk.setVisible(is_reality and not is_ss)
        self.lbl_sid.setVisible(is_reality and not is_ss)
        self.txt_sid.setVisible(is_reality and not is_ss)
        self.lbl_spx.setVisible(is_reality and not is_ss)
        self.txt_spx.setVisible(is_reality and not is_ss)
        self.lbl_pqv.setVisible(is_reality and not is_ss)
        self.txt_pqv.setVisible(is_reality and not is_ss)

    def _on_save_clicked(self):
        protocol = self.cmb_protocol.currentText()
        server = self.txt_server.text().strip()
        port = self.txt_port.text().strip()
        auth = self.txt_auth.text().strip()
        
        if not server or not port or not auth:
            QMessageBox.warning(self, "Validation Error", "Server, Port, and UUID/Password are required.")
            return
            
        fm_text = self.txt_fm.toPlainText().strip()
        if fm_text:
            try:
                fm_obj = json.loads(fm_text)
                if not isinstance(fm_obj, dict):
                    raise ValueError("FinalMask JSON must be a dictionary/object")
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Validation Error", f"Invalid FinalMask JSON:\n{e}")
                return
            except ValueError as e:
                QMessageBox.warning(self, "Validation Error", str(e))
                return
                
        security = self.cmb_security.currentText()
        network = self.cmb_network.currentText()

        config = ManualConfigInput(
            protocol=protocol,
            server=server,
            port=int(port) if port.isdigit() else 0,
            auth=auth,
            remark=self.txt_remark.text().strip(),
            network=network,
            security=security,
            
            flow=self.cmb_vless_flow.currentText() if protocol == "vless" else "",
            encryption=self.txt_vless_enc.text().strip() or "none",
            
            vmess_mode=self.cmb_vmess_mode.currentText(),
            vmess_encryption=self.cmb_vmess_enc.currentText(),
            vmess_legacy_scy=self.cmb_vmess_legacy_scy.currentText(),
            
            ss_method=self.cmb_ss_method.currentText(),
            ss_uot=self.chk_ss_uot.isChecked(),
            ss_plugin=self.txt_ss_plugin.text().strip(),
            
            path=self.txt_path.text().strip(),
            host=self.txt_host.text().strip(),
            service_name=self.txt_path.text().strip(),
            grpc_mode=self.cmb_grpc_mode.currentText(),
            grpc_authority=self.txt_grpc_auth.text().strip(),
            xhttp_mode=self.cmb_xhttp_mode.currentText(),
            xhttp_extra=self.txt_xhttp_extra.text().strip(),
            mkcp_mtu=self.txt_mkcp_mtu.text().strip(),
            mkcp_tti=self.txt_mkcp_tti.text().strip(),
            
            sni=self.txt_sni.text().strip(),
            fp=self.cmb_fp.currentText(),
            alpn=self.txt_alpn.text().strip(),
            ech=self.txt_ech.text().strip(),
            pcs=self.txt_pcs.text().strip(),
            vcn=self.txt_vcn.text().strip(),
            allow_insecure=self.chk_allow_insecure.isChecked(),
            
            pbk=self.txt_pbk.text().strip(),
            sid=self.txt_sid.text().strip(),
            spx=self.txt_spx.text().strip(),
            pqv=self.txt_pqv.text().strip(),
            
            final_mask=fm_text
        )
        
        try:
            url = ManualConfigBuilder.build(config)
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Builder Error", f"Unexpected error building URL:\n{e}")
            return
            
        try:
            self.main_window.parser_factory.parse_url(url)
            self.generated_url = url
            self.accept()
        except AttributeError:
            QMessageBox.critical(self, "System Error", "ParserFactory is missing from the main window. Cannot validate configuration.")
            return
        except (ParseError, ValidationError, UnsupportedProtocolError) as e:
            QMessageBox.warning(self, "Parser Validation Failed", f"The generated configuration was rejected by the parser:\n\n{str(e)}\n\nGenerated URL:\n{url}")
        except Exception as e:
            QMessageBox.critical(self, "Critical Parser Crash", f"Unhandled exception during parsing:\n{str(e)}")
