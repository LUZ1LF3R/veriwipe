#!/usr/bin/env python3
"""
VeriWipe GUI - One-Click Secure Data Wiping Interface
"""

import sys
import os
import threading
import time
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QProgressBar, QTextEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                            QDialog, QDialogButtonBox, QCheckBox, QGroupBox, QFrame,
                            QScrollArea, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon

# Import our core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_engine.ai_wipe_engine import AIWipeEngine, DeviceInfo, DeviceType
from wipe_core.wipe_engine import WipeCore, WipeOperation, WipeStatus
from certificate_engine.certificate_generator import CertificateGenerator, TamperProofLogger

class DeviceDetectionThread(QThread):
    devices_detected = pyqtSignal(list)
    detection_error = pyqtSignal(str)
    
    def __init__(self, ai_engine):
        super().__init__()
        self.ai_engine = ai_engine
    
    def run(self):
        try:
            devices = self.ai_engine.detect_devices()
            self.devices_detected.emit(devices)
        except Exception as e:
            self.detection_error.emit(str(e))

class WipeThread(QThread):
    progress_updated = pyqtSignal(str, float, str)  # device_path, progress, message
    wipe_completed = pyqtSignal(str, bool, str)     # device_path, success, message
    
    def __init__(self, wipe_core, device_path):
        super().__init__()
        self.wipe_core = wipe_core
        self.device_path = device_path
        self.is_cancelled = False
    
    def run(self):
        try:
            success = self.wipe_core.execute_wipe(self.device_path)
            if not self.is_cancelled:
                message = "Wipe completed successfully" if success else "Wipe failed"
                self.wipe_completed.emit(self.device_path, success, message)
        except Exception as e:
            self.wipe_completed.emit(self.device_path, False, str(e))
    
    def cancel(self):
        self.is_cancelled = True

class DeviceWidget(QFrame):
    wipe_requested = pyqtSignal(str)  # device_path
    
    def __init__(self, device_info: DeviceInfo, parent=None):
        super().__init__(parent)
        self.device_info = device_info
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(2)
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 10px;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Device header
        header_layout = QHBoxLayout()
        
        # Device icon based on type
        icon_label = QLabel()
        icon_text = self._get_device_icon()
        icon_label.setText(icon_text)
        icon_label.setFont(QFont("Arial", 24))
        header_layout.addWidget(icon_label)
        
        # Device info
        info_layout = QVBoxLayout()
        
        name_label = QLabel(f"<b>{self.device_info.model}</b>")
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(name_label)
        
        path_label = QLabel(f"Path: {self.device_info.device_path}")
        info_layout.addWidget(path_label)
        
        size_label = QLabel(f"Size: {self.device_info.size_gb:.2f} GB")
        info_layout.addWidget(size_label)
        
        type_label = QLabel(f"Type: {self.device_info.device_type.value.replace('_', ' ').title()}")
        info_layout.addWidget(type_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Wipe button
        self.wipe_button = QPushButton("🗑️ Secure Wipe")
        self.wipe_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cc3333;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.wipe_button.clicked.connect(self._on_wipe_clicked)
        header_layout.addWidget(self.wipe_button)
        
        layout.addLayout(header_layout)
        
        # Device details
        details_layout = QHBoxLayout()
        
        left_details = QVBoxLayout()
        left_details.addWidget(QLabel(f"Interface: {self.device_info.interface}"))
        left_details.addWidget(QLabel(f"Serial: {self.device_info.serial[:16]}..."))
        details_layout.addLayout(left_details)
        
        right_details = QVBoxLayout()
        encryption_text = "🔒 Encrypted" if self.device_info.encryption_status != "None" else "🔓 Not Encrypted"
        right_details.addWidget(QLabel(encryption_text))
        secure_erase_text = "✅ Secure Erase" if self.device_info.secure_erase_supported else "❌ No Secure Erase"
        right_details.addWidget(QLabel(secure_erase_text))
        details_layout.addLayout(right_details)
        
        layout.addLayout(details_layout)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready for wiping")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def _get_device_icon(self) -> str:
        icons = {
            DeviceType.HDD: "💾",
            DeviceType.SSD_SATA: "💿",
            DeviceType.SSD_NVME: "⚡",
            DeviceType.EMMC: "📱",
            DeviceType.USB: "🔌",
            DeviceType.UNKNOWN: "❓"
        }
        return icons.get(self.device_info.device_type, "❓")
    
    def _on_wipe_clicked(self):
        # Show confirmation dialog
        reply = QMessageBox.question(self, 'Confirm Secure Wipe',
                                   f"Are you sure you want to securely wipe {self.device_info.device_path}?\\n\\n"
                                   f"⚠️ This action is IRREVERSIBLE!\\n"
                                   f"⚠️ ALL DATA will be permanently destroyed!\\n\\n"
                                   f"Device: {self.device_info.model}\\n"
                                   f"Size: {self.device_info.size_gb:.2f} GB",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.wipe_requested.emit(self.device_info.device_path)
    
    def set_wiping_state(self, is_wiping: bool):
        self.wipe_button.setEnabled(not is_wiping)
        self.progress_bar.setVisible(is_wiping)
        if is_wiping:
            self.status_label.setText("Wiping in progress...")
            self.status_label.setStyleSheet("color: #ff6600;")
        else:
            self.status_label.setText("Ready for wiping")
            self.status_label.setStyleSheet("color: #666;")
    
    def update_progress(self, progress: float, message: str):
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(message)
    
    def set_completed_state(self, success: bool, message: str):
        self.set_wiping_state(False)
        if success:
            self.status_label.setText("✅ " + message)
            self.status_label.setStyleSheet("color: #009900;")
            self.wipe_button.setText("✅ Wiped")
            self.wipe_button.setStyleSheet("""
                QPushButton {
                    background-color: #009900;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.wipe_button.setEnabled(False)
        else:
            self.status_label.setText("❌ " + message)
            self.status_label.setStyleSheet("color: #cc0000;")

class LogViewerDialog(QDialog):
    def __init__(self, logger: TamperProofLogger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.setWindowTitle("Operation Logs")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))
        
        # Populate logs
        self.refresh_logs()
        
        layout.addWidget(QLabel("Tamper-Proof Operation Logs:"))
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_logs)
        button_layout.addWidget(refresh_btn)
        
        verify_btn = QPushButton("Verify Chain Integrity")
        verify_btn.clicked.connect(self.verify_chain)
        button_layout.addWidget(verify_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def refresh_logs(self):
        log_text = ""
        for entry in self.logger.log_chain:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
            log_text += f"[{timestamp}] {entry.level}: {entry.message}\\n"
            log_text += f"  Entry ID: {entry.entry_id}\\n"
            log_text += f"  Hash: {entry.entry_hash[:16]}...\\n\\n"
        
        self.log_text.setPlainText(log_text)
    
    def verify_chain(self):
        is_valid = self.logger.verify_chain_integrity()
        if is_valid:
            QMessageBox.information(self, "Chain Verification", "✅ Log chain integrity verified successfully!")
        else:
            QMessageBox.warning(self, "Chain Verification", "❌ Log chain integrity verification failed!")

class VeriWipeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ai_engine = AIWipeEngine()
        self.wipe_core = WipeCore(self.ai_engine)
        self.logger = TamperProofLogger()
        self.cert_generator = CertificateGenerator(self.logger)
        
        self.devices: List[DeviceInfo] = []
        self.device_widgets: Dict[str, DeviceWidget] = {}
        self.wipe_threads: Dict[str, WipeThread] = {}
        
        # Set up progress callback
        self.wipe_core.add_progress_callback(self.on_wipe_progress)
        
        self.setup_ui()
        self.start_device_detection()
    
    def setup_ui(self):
        self.setWindowTitle("VeriWipe - AI-Powered Secure Data Wiping")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QVBoxLayout()
        
        title_label = QLabel("🛡️ VeriWipe")
        title_label.setFont(QFont("Arial", 28, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c5282; margin: 20px;")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("AI-Powered Secure Data Wiping for Trustworthy IT Asset Recycling")
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        header_layout.addWidget(subtitle_label)
        
        main_layout.addLayout(header_layout)
        
        # Control panel
        control_panel = QGroupBox("Controls")
        control_layout = QHBoxLayout()
        
        self.detect_btn = QPushButton("🔍 Detect Devices")
        self.detect_btn.clicked.connect(self.start_device_detection)
        control_layout.addWidget(self.detect_btn)
        
        self.logs_btn = QPushButton("📋 View Logs")
        self.logs_btn.clicked.connect(self.show_logs)
        control_layout.addWidget(self.logs_btn)
        
        self.about_btn = QPushButton("ℹ️ About")
        self.about_btn.clicked.connect(self.show_about)
        control_layout.addWidget(self.about_btn)
        
        control_layout.addStretch()
        
        self.status_label = QLabel("Ready - Click 'Detect Devices' to begin")
        self.status_label.setStyleSheet("color: #666; font-weight: bold;")
        control_layout.addWidget(self.status_label)
        
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel)
        
        # Device list area
        self.device_scroll = QScrollArea()
        self.device_scroll.setWidgetResizable(True)
        self.device_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.device_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.device_container = QWidget()
        self.device_layout = QVBoxLayout()
        self.device_container.setLayout(self.device_layout)
        self.device_scroll.setWidget(self.device_container)
        
        main_layout.addWidget(self.device_scroll)
        
        # Status bar
        self.statusBar().showMessage("VeriWipe initialized - Ready to detect storage devices")
        
        central_widget.setLayout(main_layout)
    
    def start_device_detection(self):
        self.status_label.setText("🔍 Detecting storage devices...")
        self.detect_btn.setEnabled(False)
        
        self.detection_thread = DeviceDetectionThread(self.ai_engine)
        self.detection_thread.devices_detected.connect(self.on_devices_detected)
        self.detection_thread.detection_error.connect(self.on_detection_error)
        self.detection_thread.finished.connect(lambda: self.detect_btn.setEnabled(True))
        self.detection_thread.start()
        
        self.logger.add_entry("Device detection started")
    
    def on_devices_detected(self, devices: List[DeviceInfo]):
        self.devices = devices
        self.logger.add_entry(f"Detected {len(devices)} storage devices")
        
        # Clear existing device widgets
        for widget in self.device_widgets.values():
            widget.setParent(None)
        self.device_widgets.clear()
        
        if not devices:
            self.status_label.setText("❌ No storage devices detected")
            no_devices_label = QLabel("No storage devices detected.\\nMake sure you have appropriate permissions and devices are connected.")
            no_devices_label.setAlignment(Qt.AlignCenter)
            no_devices_label.setStyleSheet("color: #666; font-size: 14px; margin: 50px;")
            self.device_layout.addWidget(no_devices_label)
            return
        
        self.status_label.setText(f"✅ Detected {len(devices)} device(s)")
        
        # Create device widgets
        for device in devices:
            widget = DeviceWidget(device)
            widget.wipe_requested.connect(self.start_wipe_operation)
            self.device_widgets[device.device_path] = widget
            self.device_layout.addWidget(widget)
        
        self.device_layout.addStretch()
        self.statusBar().showMessage(f"Ready - {len(devices)} devices available for wiping")
    
    def on_detection_error(self, error_message: str):
        self.status_label.setText("❌ Detection failed")
        self.logger.add_entry(f"Device detection error: {error_message}", "ERROR")
        QMessageBox.critical(self, "Detection Error", f"Failed to detect devices:\\n{error_message}")
    
    def start_wipe_operation(self, device_path: str):
        device_info = next((d for d in self.devices if d.device_path == device_path), None)
        if not device_info:
            return
        
        self.logger.add_entry(f"Starting wipe operation for {device_path}")
        
        # Prepare wipe operation
        operation = self.wipe_core.prepare_wipe_operation(device_info)
        
        # Update UI
        widget = self.device_widgets[device_path]
        widget.set_wiping_state(True)
        
        # Start wipe thread
        wipe_thread = WipeThread(self.wipe_core, device_path)
        wipe_thread.wipe_completed.connect(self.on_wipe_completed)
        self.wipe_threads[device_path] = wipe_thread
        wipe_thread.start()
        
        self.statusBar().showMessage(f"Wiping {device_path}...")
    
    def on_wipe_progress(self, device_path: str, progress: float, message: str):
        if device_path in self.device_widgets:
            self.device_widgets[device_path].update_progress(progress, message)
        
        self.statusBar().showMessage(f"{device_path}: {progress:.1f}% - {message}")
    
    def on_wipe_completed(self, device_path: str, success: bool, message: str):
        self.logger.add_entry(f"Wipe operation for {device_path} completed: {'success' if success else 'failed'}")
        
        # Update UI
        if device_path in self.device_widgets:
            self.device_widgets[device_path].set_completed_state(success, message)
        
        # Clean up thread
        if device_path in self.wipe_threads:
            del self.wipe_threads[device_path]
        
        if success:
            # Generate certificate
            try:
                operation = self.wipe_core.current_operations.get(device_path)
                if operation:
                    certificates = self.cert_generator.generate_certificate(operation)
                    
                    QMessageBox.information(self, "Wipe Completed", 
                                          f"✅ Device {device_path} wiped successfully!\\n\\n"
                                          f"Certificate generated:\\n"
                                          f"📄 PDF: {certificates['pdf_certificate']}\\n"
                                          f"📋 JSON: {certificates['json_certificate']}")
                    
                    self.logger.add_entry(f"Certificate generated for {device_path}: {certificates['certificate_id']}")
            except Exception as e:
                QMessageBox.warning(self, "Certificate Error", f"Wipe completed but certificate generation failed:\\n{str(e)}")
                self.logger.add_entry(f"Certificate generation failed for {device_path}: {str(e)}", "ERROR")
        else:
            QMessageBox.critical(self, "Wipe Failed", f"❌ Wipe operation failed for {device_path}:\\n{message}")
        
        self.statusBar().showMessage("Ready")
    
    def show_logs(self):
        dialog = LogViewerDialog(self.logger, self)
        dialog.exec_()
    
    def show_about(self):
        about_text = """
        <h2>VeriWipe v1.0.0</h2>
        <p><b>AI-Powered Secure Data Wiping for Trustworthy IT Asset Recycling</b></p>
        
        <p>VeriWipe is a cross-platform, one-click AI-powered secure data-wiping solution designed to build trust in IT asset recycling.</p>
        
        <h3>Features:</h3>
        <ul>
        <li>🤖 AI-powered adaptive wipe method selection</li>
        <li>🔒 NIST SP 800-88 compliant secure wiping</li>
        <li>📜 Tamper-proof digital certificates</li>
        <li>🌐 Offline-first design</li>
        <li>⚡ Support for ATA/NVMe secure erase</li>
        <li>🔍 HPA/DCO detection and removal</li>
        </ul>
        
        <p><b>Team:</b> 4× Cybersecurity | 1× Blockchain | 1× Quantum</p>
        <p><b>Event:</b> Smart India Hackathon 2025</p>
        <p><b>Problem Statement ID:</b> 25070</p>
        """
        
        QMessageBox.about(self, "About VeriWipe", about_text)

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("VeriWipe")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VeriWipe Team")
    
    # Apply dark theme
    app.setStyle('Fusion')
    
    window = VeriWipeMainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()