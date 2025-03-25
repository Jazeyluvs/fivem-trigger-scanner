import sys
import os
import re
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, 
    QTableWidget, QTableWidgetItem, QHBoxLayout, QProgressBar, QLineEdit, QHeaderView, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# 🛠️ Discord Bot Configuration (Replace with actual values)
DISCORD_BOT_TOKEN = "MTM1Mzc5OTE4NjE0NzE4MDY1NA.GjLAz_.hb-BXIKVM03_TiFE5wZYFYb11drxoh3PI3L08k"
CHANNEL_ID = "1353833374535385198"

class TriggerScannerThread(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(list)

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

    def run(self):
        triggers = []
        pattern = re.compile(r"TriggerServerEvent\(['\"]([^'\"]+)['\"].*?\)", re.IGNORECASE)

        all_files = [os.path.join(root, file)
                     for root, _, files in os.walk(self.folder)
                     for file in files if file.endswith(".lua")]

        total_files = len(all_files)
        for index, file_path in enumerate(all_files):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    for match in matches:
                        full_command = f'TriggerServerEvent("{match}")'
                        triggers.append((full_command, os.path.basename(file_path)))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

            self.progress.emit(int((index + 1) / total_files * 100))

        triggers.sort()
        self.result.emit(triggers)

class TriggerFinderApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("FiveM Trigger Scanner 🚀")
        self.showMaximized()
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: white; font-size: 16px; }
            QPushButton { background-color: #333; color: white; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background-color: #444; }
            QProgressBar { border: 1px solid #555; height: 10px; border-radius: 4px; }
            QProgressBar::chunk { background: #00c853; }
            QTableWidget { border: 1px solid #333; color: white; font-size: 14px; }
            QTableWidget::item { background-color: #1e1e1e; color: #ff5f5f; }
            QTableWidget::item:selected { background-color: #333; color: #ffcccc; }
            QHeaderView::section { background-color: #222; color: white; font-size: 14px; }
            QLineEdit { background-color: #222; color: #E0E0E0; border: 1px solid #555; padding: 6px; font-size: 14px; }
            QTextEdit { background-color: #1e1e1e; color: #00ff00; border: 1px solid #555; font-size: 14px; }
        """)

        layout = QVBoxLayout()

        # Folder Selection
        self.folder_label = QLabel("📂 Dump Selected: None")
        layout.addWidget(self.folder_label)

        btn_layout = QHBoxLayout()
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        btn_layout.addWidget(self.select_folder_btn)

        self.start_scan_btn = QPushButton("Start Scan")
        self.start_scan_btn.setEnabled(False)
        self.start_scan_btn.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.start_scan_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.reset)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search (e.g., playerSpawn, payment, vehicle)")
        self.search_bar.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_bar)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Trigger Table
        self.triggers_table = QTableWidget()
        self.triggers_table.setColumnCount(2)
        self.triggers_table.setHorizontalHeaderLabels(["Trigger Command", "Resource"])
        self.triggers_table.setSortingEnabled(True)
        self.triggers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.triggers_table)

        # 🔥 Update Notifications
        self.update_label = QLabel("🔄 Checking for updates...")
        layout.addWidget(self.update_label)

        self.update_text = QTextEdit()
        self.update_text.setReadOnly(True)
        layout.addWidget(self.update_text)

        self.refresh_update_btn = QPushButton("🔄 Refresh Updates")
        self.refresh_update_btn.clicked.connect(self.check_for_updates)
        layout.addWidget(self.refresh_update_btn)

        self.setLayout(layout)

        self.dump_folder = None
        self.triggers_found = []

        # Fetch updates on launch
        self.check_for_updates()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Dump Folder")
        if folder:
            self.dump_folder = folder
            self.folder_label.setText(f"🟢 Dump Selected: {folder}")
            self.start_scan_btn.setEnabled(True)

    def start_scan(self):
        if not self.dump_folder:
            self.folder_label.setText("⚠ Please select a dump folder first!")
            return

        self.start_scan_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.triggers_table.setRowCount(0)
        self.progress_bar.setValue(0)

        self.scan_thread = TriggerScannerThread(self.dump_folder)
        self.scan_thread.progress.connect(self.progress_bar.setValue)
        self.scan_thread.result.connect(self.update_results)
        self.scan_thread.start()

    def reset(self):
        self.dump_folder = None
        self.folder_label.setText("📂 Dump Selected: None")
        self.triggers_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.start_scan_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

    def update_results(self, results):
        self.triggers_found = results
        self.triggers_table.setRowCount(len(results))

        for row, (trigger_command, resource) in enumerate(results):
            trigger_item = QTableWidgetItem(trigger_command)
            resource_item = QTableWidgetItem(resource)
            trigger_item.setForeground(Qt.GlobalColor.red)
            resource_item.setForeground(Qt.GlobalColor.green)
            self.triggers_table.setItem(row, 0, trigger_item)
            self.triggers_table.setItem(row, 1, resource_item)

        self.progress_bar.setValue(100)
        self.reset_btn.setEnabled(True)
        self.start_scan_btn.setEnabled(True)

    def filter_table(self):
        search_text = self.search_bar.text().lower()
        for row in range(self.triggers_table.rowCount()):
            item = self.triggers_table.item(row, 0)
            self.triggers_table.setRowHidden(row, search_text not in item.text().lower())

    def check_for_updates(self):
        """Fetch the latest update from Discord."""
        self.update_label.setText("🔄 Checking for updates...")
        url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
        headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                messages = response.json()
                if messages:
                    latest_update = messages[0]["content"]
                    self.update_text.setText(latest_update)
                else:
                    self.update_text.setText("✅ No new updates available.")
            else:
                self.update_text.setText(f"❌ Error fetching updates: {response.status_code}")
        except Exception as e:
            self.update_text.setText(f"❌ Error fetching updates: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TriggerFinderApp()
    window.showMaximized()
    sys.exit(app.exec())
