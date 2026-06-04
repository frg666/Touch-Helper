import sys
import os
import winreg
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QListWidget,
    QPushButton, QMessageBox, QFileDialog
)

BLACKLIST_FILE = "blacklist.txt"

FILTER_KEYWORDS = [
    "python", "anaconda", "visual c++", "redistributable",
    ".net", "runtime", "framework", "microsoft edge update",
    "microsoft visual studio", "developer", "sdk",
    "java", "jdk", "kotlin", "dart",
    "targeting pack", "application verifier", "certification kit"
]

def get_installed_software():
    """读取已安装软件列表，并过滤掉运行库内容"""
    software_list = []
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
    ]
    for root, path in reg_paths:
        try:
            key = winreg.OpenKey(root, path)
            for i in range(0, winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                try:
                    name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                    if name:
                        name_lower = name.lower()
                        if not any(keyword in name_lower for keyword in FILTER_KEYWORDS):
                            software_list.append(name)
                except FileNotFoundError:
                    pass
                finally:
                    subkey.Close()
            key.Close()
        except Exception:
            pass
    return sorted(set(software_list))

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        for item in blacklist:
            f.write(item + "\n")

class BlacklistManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("黑名单管理器（应用名 + 文件名）")
        self.resize(600, 400)

        layout = QVBoxLayout()

        # 软件列表
        self.list_widget = QListWidget()
        softwares = get_installed_software()
        for s in softwares:
            self.list_widget.addItem(s)
        layout.addWidget(self.list_widget)

        # 按钮：加入黑名单（应用名）
        self.btn_add = QPushButton("加入黑名单（应用名）")
        self.btn_add.clicked.connect(self.add_to_blacklist)
        layout.addWidget(self.btn_add)

        # 按钮：选择文件名加入黑名单
        self.btn_add_file = QPushButton("选择文件名加入黑名单")
        self.btn_add_file.clicked.connect(self.add_file_to_blacklist)
        layout.addWidget(self.btn_add_file)

        self.setLayout(layout)

    def add_to_blacklist(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择一个软件")
            return
        blacklist = load_blacklist()
        for item in selected_items:
            entry = item.text()
            if entry not in blacklist:
                blacklist.append(entry)
        save_blacklist(blacklist)
        QMessageBox.information(self, "成功", "已加入黑名单（应用名）！")

    def add_file_to_blacklist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用文件", "", "Executable Files (*.exe *.dll);;All Files (*)"
        )
        if file_path:
            file_name = os.path.basename(file_path)  # 只保存文件名
            blacklist = load_blacklist()
            if file_name not in blacklist:
                blacklist.append(file_name)
                save_blacklist(blacklist)
                QMessageBox.information(self, "成功", f"已将文件名加入黑名单:\n{file_name}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = BlacklistManager()
    w.show()
    sys.exit(app.exec())
