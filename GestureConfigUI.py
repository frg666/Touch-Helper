# -*- coding: utf-8 -*-
import sys, os, json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QPushButton, QGroupBox,
    QMessageBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget, QListWidget,
    QListWidgetItem, QLineEdit, QFileDialog, QColorDialog, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter, QBrush

CONFIG_FILE = "gesture_config.json"

ACTION_OPTIONS = [
    ("win", "Win（开始菜单）"),
    ("win_tab", "Win+Tab（任务视图）"),
    ("win_n", "Win+N（通知中心）"),
    ("win_a", "Win+A（操作中心）"),
    ("win_d", "Win+D（显示桌面）"),
    ("win_e", "Win+E（文件资源管理器）"),
    ("win_i", "Win+I（系统设置）"),
    ("win_l", "Win+L（锁定屏幕）"),
    ("win_m", "Win+M（最小化所有窗口）"),
    ("alt_f4", "Alt+F4（关闭窗口）"),
    ("close_window", "双击滑动关闭窗口"),
    ("minimize_window", "最小化窗口"),
    ("ctrl_c", "Ctrl+C（复制）"),
    ("ctrl_v", "Ctrl+V（粘贴）"),
    ("ctrl_x", "Ctrl+X（剪切）"),
    ("ctrl_z", "Ctrl+Z（撤销）"),
    ("ctrl_y", "Ctrl+Y（重做）"),
    ("ctrl_s", "Ctrl+S（保存）"),
    ("ctrl_a", "Ctrl+A（全选）"),
    ("enter", "Enter（回车）"),
    ("none", "无动作"),
]

EDGE_ZONES = [
    ("top1", "顶部左侧", False),
    ("top2", "顶部中间", True),
    ("top3", "顶部右侧", False),
    ("bottom1", "底部左侧", False),
    ("bottom2", "底部中间", True),
    ("bottom3", "底部右侧", False),
    ("left", "左侧边缘", True),
    ("right", "右侧边缘", True),
]


def get_action_label(action_key):
    for value, label in ACTION_OPTIONS:
        if value == action_key:
            return label
    return action_key


def load_gesture_config():
    if not os.path.exists(CONFIG_FILE):
        return get_default_config()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return get_default_config()


def get_default_config():
    return {
        "gestures": {
            "top1": {"name": "顶部左侧", "action": "win_tab", "threshold": 25, "direction": "down"},
            "top2": {"name": "顶部中间", "action_short": "win_m",
                "threshold_short": 25, "action_long": "win",
                "threshold_long": 100, "direction": "down", "double_slide": True},
            "top3": {"name": "顶部右侧", "action": "win_n", "threshold": 25, "direction": "down"},
            "bottom1": {"name": "底部左侧", "action": "win_tab", "threshold": 25, "direction": "up"},
            "bottom2": {"name": "底部中间", "action_short": "win_m",
                "threshold_short": 25, "action_long": "win",
                "threshold_long": 100, "direction": "up", "double_slide": True},
            "bottom3": {"name": "底部右侧", "action": "win_n", "threshold": 25, "direction": "up"},
            "left": {
                "name": "左侧边缘", "action_short": "close_window",
                "threshold_short": 25, "action_long": "win_tab",
                "threshold_long": 100, "direction": "right", "double_slide": True
            },
            "right": {
                "name": "右侧边缘", "action_short": "close_window",
                "threshold_short": 25, "action_long": "win_tab",
                "threshold_long": 100, "direction": "left", "double_slide": True
            },
        },
        "close_zone_top": -1,
        "app_overrides": {},
        "animation": {
            "burst_duration": 350,
            "burst_max_radius": 70,
            "hold_max_radius": 60,
            "durations": {
                "danger": None,
                "navigate": None,
                "edit": None,
                "reminder": None,
                "other": None,
            },
            "colors": {
                "danger": "#FF6464",
                "navigate": "#64C8FF",
                "edit": "#64FFB4",
                "reminder": "#FFC832",
                "other": "#B4B4FF",
                "hold_normal": "#C8C8FF",
                "hold_long": "#FFA03C",
            }
        },
    }


def save_gesture_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


BLACKLIST_FILE = "blacklist.txt"


def get_installed_software():
    """从开始菜单和注册表获取已安装软件列表"""
    softwares = set()
    paths = [
        os.path.expandvars("%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs"),
        os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"),
    ]
    for base in paths:
        if os.path.exists(base):
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.endswith(".lnk"):
                        softwares.add(os.path.splitext(f)[0])
    try:
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for subkey in [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]:
                try:
                    key = winreg.OpenKey(hive, subkey)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
                            name = winreg.QueryValueEx(sub, "DisplayName")[0]
                            if name:
                                softwares.add(name)
                            winreg.CloseKey(sub)
                        except:
                            pass
                    winreg.CloseKey(key)
                except:
                    pass
    except:
        pass
    return sorted(softwares, key=str.casefold)


def load_blacklist_file():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_blacklist_file(blacklist):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        for item in blacklist:
            f.write(item + "\n")


COLOR_CATEGORIES = [
    ("danger", "危险操作\n(关闭/最小化/Alt+F4)"),
    ("navigate", "导航操作\n(Win/Win+Tab/Win+D/Win+M)"),
    ("edit", "编辑操作\n(Ctrl+C/V/X/Z/S/A)"),
    ("reminder", "提醒/待确认\n(双击确认提醒)"),
    ("other", "其他操作\n(默认颜色)"),
    ("hold_normal", "普通按下\n(Hold 短按)"),
    ("hold_long", "长滑就绪\n(Hold 长距离)"),
]


class GestureConfigUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义手势配置")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.resize(800, 600)

        self.config = load_gesture_config()
        self.edge_widgets = {}
        self.app_widgets = {}

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        title = QLabel("触控助手 - 手势配置")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        main_layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { font-size: 13px; padding: 6px 16px; }")

        self.tab_default = QWidget()
        self._setup_default_tab()
        self.tabs.addTab(self.tab_default, "默认手势配置")

        self.tab_app = QWidget()
        self._setup_app_tab()
        self.tabs.addTab(self.tab_app, "应用定制")

        self.tab_blacklist = QWidget()
        self._setup_blacklist_tab()
        self.tabs.addTab(self.tab_blacklist, "黑名单")

        self.tab_animation = QWidget()
        self._setup_animation_tab()
        self.tabs.addTab(self.tab_animation, "动画配置")

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def _setup_default_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["边缘区域", "滑动方向", "动作", "触发阈值(px)", "长滑动作", "长滑阈值(px)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(len(EDGE_ZONES))

        for row, (edge_key, display_name, is_side) in enumerate(EDGE_ZONES):
            gesture = self.config["gestures"].get(edge_key, {})

            name_item = QTableWidgetItem(display_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            direction = gesture.get("direction", "down" if "top" in edge_key else "up" if "bottom" in edge_key else "right")
            dir_text = {"down": "向下滑动", "up": "向上滑动", "right": "向右滑动", "left": "向左滑动"}.get(direction, direction)
            dir_item = QTableWidgetItem(dir_text)
            dir_item.setFlags(dir_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, dir_item)

            if is_side:
                action_short = gesture.get("action_short", "close_window")
                threshold_short = gesture.get("threshold_short", 25)
                action_long = gesture.get("action_long", "win_tab")
                threshold_long = gesture.get("threshold_long", 100)

                combo_short = QComboBox()
                for action_value, action_label in ACTION_OPTIONS:
                    combo_short.addItem(action_label, action_value)
                index = combo_short.findData(action_short)
                if index >= 0:
                    combo_short.setCurrentIndex(index)
                self.table.setCellWidget(row, 2, combo_short)

                spin_short = QSpinBox()
                spin_short.setRange(5, 300)
                spin_short.setValue(threshold_short)
                spin_short.setSuffix(" px")
                self.table.setCellWidget(row, 3, spin_short)

                combo_long = QComboBox()
                for action_value, action_label in ACTION_OPTIONS:
                    combo_long.addItem(action_label, action_value)
                index = combo_long.findData(action_long)
                if index >= 0:
                    combo_long.setCurrentIndex(index)
                self.table.setCellWidget(row, 4, combo_long)

                spin_long = QSpinBox()
                spin_long.setRange(30, 500)
                spin_long.setValue(threshold_long)
                spin_long.setSuffix(" px")
                self.table.setCellWidget(row, 5, spin_long)

                self.edge_widgets[edge_key] = {
                    "is_side": True,
                    "combo_short": combo_short,
                    "spin_short": spin_short,
                    "combo_long": combo_long,
                    "spin_long": spin_long,
                }
            else:
                action = gesture.get("action", "none")
                threshold = gesture.get("threshold", 25)

                combo = QComboBox()
                for action_value, action_label in ACTION_OPTIONS:
                    combo.addItem(action_label, action_value)
                index = combo.findData(action)
                if index >= 0:
                    combo.setCurrentIndex(index)
                self.table.setCellWidget(row, 2, combo)

                spin = QSpinBox()
                spin.setRange(5, 300)
                spin.setValue(threshold)
                spin.setSuffix(" px")
                self.table.setCellWidget(row, 3, spin)

                self.table.setCellWidget(row, 4, QLabel("—"))
                self.table.setCellWidget(row, 5, QLabel("—"))

                self.edge_widgets[edge_key] = {
                    "is_side": False,
                    "combo": combo,
                    "spin": spin,
                }

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_save = QPushButton("保存配置")
        btn_save.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_save.clicked.connect(self.save_config)
        btn_layout.addWidget(btn_save)

        btn_reset = QPushButton("恢复默认")
        btn_reset.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_reset.clicked.connect(self.reset_config)
        btn_layout.addWidget(btn_reset)

        btn_reload = QPushButton("重新加载")
        btn_reload.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_reload.clicked.connect(self.reload_config)
        btn_layout.addWidget(btn_reload)

        layout.addLayout(btn_layout)
        self.tab_default.setLayout(layout)

    def _setup_app_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 关闭区域高度
        zone_group = QGroupBox("关闭/最小化区域高度")
        zone_layout = QHBoxLayout()
        zone_layout.addWidget(QLabel("左右侧边缘顶部区域高度（在此区域内滑动才触发关闭/最小化操作）："))
        self.zone_spin = QSpinBox()
        self.zone_spin.setRange(-1, 500)
        self.zone_spin.setValue(self.config.get("close_zone_top", -1))
        self.zone_spin.setSuffix(" px")
        self.zone_spin.setSpecialValueText("全屏高度")
        self.zone_spin.valueChanged.connect(self._on_zone_changed)
        zone_layout.addWidget(self.zone_spin)
        zone_group.setLayout(zone_layout)
        layout.addWidget(zone_group)

        # 应用定制列表
        app_group = QGroupBox("应用定制操作")
        app_layout = QVBoxLayout()
        app_layout.setSpacing(6)

        # 应用列表 + 添加/删除
        list_row = QHBoxLayout()
        list_row.setSpacing(8)

        self.app_list = QListWidget()
        self.app_list.setMinimumHeight(100)
        self.app_list.currentRowChanged.connect(self._on_app_selected)
        list_row.addWidget(self.app_list)

        btn_col = QVBoxLayout()
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("输入应用exe名称，如 notepad.exe")
        btn_col.addWidget(self.app_input)

        btn_add_app = QPushButton("添加应用")
        btn_add_app.clicked.connect(self._add_app)
        btn_col.addWidget(btn_add_app)

        btn_remove_app = QPushButton("删除选定应用")
        btn_remove_app.clicked.connect(self._remove_app)
        btn_col.addWidget(btn_remove_app)

        list_row.addLayout(btn_col)
        app_layout.addLayout(list_row)

        # 边缘覆盖配置表
        self.app_table = QTableWidget()
        self.app_table.setColumnCount(4)
        self.app_table.setHorizontalHeaderLabels(["边缘区域", "短滑动作", "长滑动作", "操作"])
        self.app_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.app_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.app_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.app_table.verticalHeader().setVisible(False)
        self.app_table.setRowCount(len(EDGE_ZONES))
        app_layout.addWidget(self.app_table)

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_save_app = QPushButton("保存应用定制配置")
        btn_save_app.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_save_app.clicked.connect(self._save_app_overrides)
        btn_layout.addWidget(btn_save_app)

        btn_reload = QPushButton("重新加载")
        btn_reload.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_reload.clicked.connect(self.reload_config)
        btn_layout.addWidget(btn_reload)

        layout.addLayout(btn_layout)
        self.tab_app.setLayout(layout)

        # 刷新应用列表
        self._refresh_app_list()

    def _on_zone_changed(self, value):
        self.config["close_zone_top"] = value

    def _refresh_app_list(self):
        self.app_list.blockSignals(True)
        self.app_list.clear()
        overrides = self.config.get("app_overrides", {})
        for app_exe in sorted(overrides.keys()):
            self.app_list.addItem(QListWidgetItem(app_exe))
        self.app_list.blockSignals(False)
        if self.app_list.count() > 0:
            self.app_list.setCurrentRow(0)
            self._on_app_selected(0)
        else:
            self._clear_app_table()

    def _clear_app_table(self):
        for row in range(self.app_table.rowCount()):
            for col in range(self.app_table.columnCount()):
                self.app_table.setCellWidget(row, col, None)
                self.app_table.setItem(row, col, QTableWidgetItem(""))

    def _on_app_selected(self, row):
        self._populate_app_table(row)

    def _populate_app_table(self, row):
        self.app_table.blockSignals(True)
        self._clear_app_table()
        if row < 0:
            self.app_table.blockSignals(False)
            return

        item = self.app_list.item(row)
        if not item:
            self.app_table.blockSignals(False)
            return
        app_exe = item.text()
        overrides = self.config.get("app_overrides", {}).get(app_exe, {})

        for r, (edge_key, display_name, is_side) in enumerate(EDGE_ZONES):
            name_item = QTableWidgetItem(display_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.app_table.setItem(r, 0, name_item)

            edge_override = overrides.get(edge_key, {})

            if is_side:
                orig_short = self.config["gestures"].get(edge_key, {}).get("action_short", "none")
                orig_long = self.config["gestures"].get(edge_key, {}).get("action_long", "none")
                ov_short = edge_override.get("action_short", orig_short) if isinstance(edge_override, dict) else (edge_override if isinstance(edge_override, str) else orig_short)
                ov_long = edge_override.get("action_long", orig_long) if isinstance(edge_override, dict) else orig_long

                combo_short = QComboBox()
                for av, al in ACTION_OPTIONS:
                    combo_short.addItem(al, av)
                idx = combo_short.findData(ov_short)
                if idx >= 0:
                    combo_short.setCurrentIndex(idx)
                self.app_table.setCellWidget(r, 1, combo_short)

                combo_long = QComboBox()
                for av, al in ACTION_OPTIONS:
                    combo_long.addItem(al, av)
                idx = combo_long.findData(ov_long)
                if idx >= 0:
                    combo_long.setCurrentIndex(idx)
                self.app_table.setCellWidget(r, 2, combo_long)
            else:
                orig_action = self.config["gestures"].get(edge_key, {}).get("action", "none")
                ov_action = edge_override.get("action", orig_action) if isinstance(edge_override, dict) else (edge_override if isinstance(edge_override, str) else orig_action)
                unused_label = QLabel("—")
                unused_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.app_table.setCellWidget(r, 1, unused_label)
                self.app_table.setCellWidget(r, 2, unused_label)

            btn_clear = QPushButton("清除")
            btn_clear.clicked.connect(lambda checked, er=edge_key: self._clear_edge_override(er))
            self.app_table.setCellWidget(r, 3, btn_clear)

        self.app_table.blockSignals(False)

    def _clear_edge_override(self, edge_key):
        current_row = self.app_list.currentRow()
        if current_row < 0:
            return
        app_exe = self.app_list.item(current_row).text()
        overrides = self.config.get("app_overrides", {})
        if app_exe in overrides and edge_key in overrides[app_exe]:
            del overrides[app_exe][edge_key]
            if not overrides[app_exe]:
                del overrides[app_exe]
        self._populate_app_table(current_row)
        if not overrides.get(app_exe):
            self._refresh_app_list()
        else:
            self._refresh_app_list()

    def _add_app(self):
        app_exe = self.app_input.text().strip().lower()
        if not app_exe:
            QMessageBox.warning(self, "提示", "请输入应用exe名称")
            return
        if not app_exe.endswith(".exe"):
            app_exe += ".exe"

        overrides = self.config.get("app_overrides", {})
        if app_exe not in overrides:
            overrides[app_exe] = {}

        self.app_input.clear()
        self._refresh_app_list()
        for i in range(self.app_list.count()):
            if self.app_list.item(i).text() == app_exe:
                self.app_list.setCurrentRow(i)
                break

    def _remove_app(self):
        current_row = self.app_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个应用")
            return
        app_exe = self.app_list.item(current_row).text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除「{app_exe}」的所有定制配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            overrides = self.config.get("app_overrides", {})
            if app_exe in overrides:
                del overrides[app_exe]
            self._refresh_app_list()

    def _save_app_overrides(self):
        overrides = {}
        current_row = self.app_list.currentRow()

        if current_row >= 0:
            app_exe = self.app_list.item(current_row).text()
            app_data = {}
            for r, (edge_key, display_name, is_side) in enumerate(EDGE_ZONES):
                if is_side:
                    w_short = self.app_table.cellWidget(r, 1)
                    w_long = self.app_table.cellWidget(r, 2)
                    if w_short and isinstance(w_short, QComboBox):
                        ov_short = w_short.currentData()
                        orig_short = self.config["gestures"].get(edge_key, {}).get("action_short", "none")
                        if ov_short != orig_short:
                            app_data[edge_key] = app_data.get(edge_key, {})
                            app_data[edge_key]["action_short"] = ov_short
                    if w_long and isinstance(w_long, QComboBox):
                        ov_long = w_long.currentData()
                        orig_long = self.config["gestures"].get(edge_key, {}).get("action_long", "none")
                        if ov_long != orig_long:
                            app_data[edge_key] = app_data.get(edge_key, {})
                            app_data[edge_key]["action_long"] = ov_long
                # 简单的边缘（top1/3, bottom1/3）用小表格无实际动作控件，跳过
            if app_data:
                overrides[app_exe] = app_data
            else:
                pass  # 用户没改任何值

        # 合并已保存的其他应用
        saved_overrides = self.config.get("app_overrides", {})
        for exe, data in saved_overrides.items():
            if exe != app_exe:
                overrides[exe] = data

        self.config["app_overrides"] = overrides
        self.config["close_zone_top"] = self.zone_spin.value()
        save_gesture_config(self.config)
        self._refresh_app_list()
        QMessageBox.information(self, "保存成功", "应用定制配置已保存！\n请点击「重新加载」使配置立即生效。")

    def collect_config(self):
        new_config = {"gestures": {}}
        for row, (edge_key, display_name, is_side) in enumerate(EDGE_ZONES):
            widgets = self.edge_widgets[edge_key]
            if is_side:
                if edge_key == "left":
                    direction = "right"
                elif edge_key == "right":
                    direction = "left"
                elif "top" in edge_key:
                    direction = "down"
                else:
                    direction = "up"
                new_config["gestures"][edge_key] = {
                    "name": display_name,
                    "action_short": widgets["combo_short"].currentData(),
                    "threshold_short": widgets["spin_short"].value(),
                    "action_long": widgets["combo_long"].currentData(),
                    "threshold_long": widgets["spin_long"].value(),
                    "direction": direction,
                    "double_slide": True,
                }
            else:
                direction = "down"
                if "bottom" in edge_key:
                    direction = "up"
                new_config["gestures"][edge_key] = {
                    "name": display_name,
                    "action": widgets["combo"].currentData(),
                    "threshold": widgets["spin"].value(),
                    "direction": direction,
                }
        return new_config

    def save_config(self):
        new_config = self.collect_config()
        new_config["close_zone_top"] = self.config.get("close_zone_top", -1)
        new_config["app_overrides"] = self.config.get("app_overrides", {})
        new_config["animation"] = self.config.get("animation", {})
        save_gesture_config(new_config)
        self.config = new_config
        QMessageBox.information(self, "保存成功", "手势配置已保存！\n请点击「重新加载」使配置立即生效，或重启触控助手。")

    def reset_config(self):
        reply = QMessageBox.question(
            self, "确认恢复默认",
            "确定要恢复所有手势配置为默认值吗？\n（应用定制配置也将被清除）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config = get_default_config()
            save_gesture_config(self.config)
            self.reload_ui()
            self.zone_spin.setValue(self.config.get("close_zone_top", -1))
            self._refresh_app_list()
            QMessageBox.information(self, "已恢复", "已恢复默认手势配置。")

    def reload_config(self):
        self.config = load_gesture_config()
        self.reload_ui()
        self.zone_spin.setValue(self.config.get("close_zone_top", -1))
        self._refresh_app_list()
        QMessageBox.information(self, "已重新加载", "手势配置已从文件重新加载。")

    def _setup_animation_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        anim_cfg = self.config.get("animation", {})

        # ── Burst 参数 ──
        burst_group = QGroupBox("Burst 动画（扩张淡出）")
        burst_layout = QGridLayout()
        burst_layout.setSpacing(8)

        burst_layout.addWidget(QLabel("动画时长："), 0, 0)
        self.anim_burst_duration = QSpinBox()
        self.anim_burst_duration.setRange(50, 2000)
        self.anim_burst_duration.setValue(anim_cfg.get("burst_duration", 350))
        self.anim_burst_duration.setSuffix(" ms")
        self.anim_burst_duration.setSingleStep(10)
        burst_layout.addWidget(self.anim_burst_duration, 0, 1)

        burst_layout.addWidget(QLabel("最大半径："), 1, 0)
        self.anim_burst_radius = QSpinBox()
        self.anim_burst_radius.setRange(20, 200)
        self.anim_burst_radius.setValue(anim_cfg.get("burst_max_radius", 70))
        self.anim_burst_radius.setSuffix(" px")
        burst_layout.addWidget(self.anim_burst_radius, 1, 1)

        burst_layout.setColumnStretch(2, 1)
        burst_group.setLayout(burst_layout)
        layout.addWidget(burst_group)

        # ── Hold 参数 ──
        hold_group = QGroupBox("Hold 动画（保持指示器）")
        hold_layout = QHBoxLayout()
        hold_layout.setSpacing(8)

        hold_layout.addWidget(QLabel("最大半径："))
        self.anim_hold_radius = QSpinBox()
        self.anim_hold_radius.setRange(10, 120)
        self.anim_hold_radius.setValue(anim_cfg.get("hold_max_radius", 60))
        self.anim_hold_radius.setSuffix(" px")
        hold_layout.addWidget(self.anim_hold_radius)
        hold_layout.addStretch()

        hold_group.setLayout(hold_layout)
        layout.addWidget(hold_group)

        # ── 颜色 + 时长配置 ──
        color_group = QGroupBox("动效颜色与时长配置")
        color_layout = QVBoxLayout()
        color_layout.setSpacing(6)

        colors = anim_cfg.get("colors", {})
        durations = anim_cfg.get("durations", {})
        self.color_widgets = {}

        # 哪些分类支持 burst 时长覆盖
        burst_categories = {"danger", "navigate", "edit", "reminder", "other"}

        for key, display in COLOR_CATEGORIES:
            row = QHBoxLayout()
            row.setSpacing(10)

            label = QLabel(display)
            label.setMinimumWidth(180)
            row.addWidget(label)

            # 颜色预览框
            hex_color = colors.get(key, "")
            preview = QFrame()
            preview.setFixedSize(28, 28)
            preview.setFrameShape(QFrame.Shape.Box)
            preview.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #888; border-radius: 4px;")
            row.addWidget(preview)

            hex_label = QLabel(hex_color)
            hex_label.setMinimumWidth(70)
            row.addWidget(hex_label)

            btn = QPushButton("选择颜色")
            btn.setFixedWidth(90)
            row.addWidget(btn)

            # 时长覆盖（仅 burst 分类）
            if key in burst_categories:
                sep = QLabel("|")
                sep.setStyleSheet("color: #888;")
                row.addWidget(sep)

                row.addWidget(QLabel("时长："))
                duration_spin = QSpinBox()
                duration_spin.setRange(0, 2000)
                duration_spin.setSingleStep(10)
                duration_spin.setSuffix(" ms")
                duration_spin.setSpecialValueText("全局")
                raw_val = durations.get(key)
                if raw_val is not None:
                    duration_spin.setValue(raw_val)
                else:
                    duration_spin.setValue(0)  # 0 = 未设置，显示"全局"
                duration_spin.setFixedWidth(100)
                row.addWidget(duration_spin)
            else:
                duration_spin = None

            row.addStretch()
            color_layout.addLayout(row)

            self.color_widgets[key] = {
                "preview": preview,
                "hex_label": hex_label,
                "button": btn,
                "duration_spin": duration_spin,
            }

            # 用闭包绑定 key, preview, hex_label
            def make_picker(k, pv, hl):
                def pick():
                    old = colors.get(k, "#000000")
                    qc = QColorDialog.getColor(QColor(old), self, f"选择 {display}")
                    if qc.isValid():
                        hex_str = qc.name()
                        pv.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #888; border-radius: 4px;")
                        hl.setText(hex_str)
                return pick

            btn.clicked.connect(make_picker(key, preview, hex_label))

        # 重置颜色按钮
        reset_color_btn = QPushButton("恢复默认颜色")
        reset_color_btn.setFixedWidth(140)
        reset_color_btn.clicked.connect(self._reset_animation_colors)
        color_layout.addWidget(reset_color_btn)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_save = QPushButton("保存动画配置")
        btn_save.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_save.clicked.connect(self._save_animation_config)
        btn_layout.addWidget(btn_save)

        btn_reload = QPushButton("重新加载")
        btn_reload.setStyleSheet("QPushButton { font-size: 14px; padding: 8px 20px; }")
        btn_reload.clicked.connect(self.reload_config)
        btn_layout.addWidget(btn_reload)

        layout.addLayout(btn_layout)
        layout.addStretch()
        self.tab_animation.setLayout(layout)

    def _reset_animation_colors(self):
        """重置所有颜色为默认值"""
        defaults = {
            "danger": "#FF6464",
            "navigate": "#64C8FF",
            "edit": "#64FFB4",
            "reminder": "#FFC832",
            "other": "#B4B4FF",
            "hold_normal": "#C8C8FF",
            "hold_long": "#FFA03C",
        }
        for key, hex_str in defaults.items():
            if key in self.color_widgets:
                w = self.color_widgets[key]
                w["preview"].setStyleSheet(f"background-color: {hex_str}; border: 1px solid #888; border-radius: 4px;")
                w["hex_label"].setText(hex_str)

    def _save_animation_config(self):
        """收集动画配置并保存"""
        anim_cfg = {
            "burst_duration": self.anim_burst_duration.value(),
            "burst_max_radius": self.anim_burst_radius.value(),
            "hold_max_radius": self.anim_hold_radius.value(),
            "durations": {},
            "colors": {},
        }
        burst_categories = {"danger", "navigate", "edit", "reminder", "other"}
        for key in self.color_widgets:
            hex_str = self.color_widgets[key]["hex_label"].text()
            anim_cfg["colors"][key] = hex_str
            spin = self.color_widgets[key].get("duration_spin")
            if key in burst_categories and spin is not None:
                val = spin.value()
                anim_cfg["durations"][key] = val if val > 0 else None
            else:
                anim_cfg["durations"][key] = None

        self.config["animation"] = anim_cfg
        save_gesture_config(self.config)
        QMessageBox.information(self, "保存成功", "动画配置已保存！\n请点击「重新加载」使配置立即生效。")

    def _setup_blacklist_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        hint = QLabel("在以下列表中选中软件名加入黑名单，或手动选择文件（exe/dll）。黑名单中的窗口不会被手势操作干扰。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 已安装软件列表
        soft_group = QGroupBox("已安装软件")
        soft_layout = QVBoxLayout()
        self.software_list = QListWidget()
        self.software_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        softwares = get_installed_software()
        for s in softwares:
            self.software_list.addItem(s)
        soft_layout.addWidget(self.software_list)

        btn_layout = QHBoxLayout()
        self.btn_add_soft = QPushButton("加入黑名单（应用名）")
        self.btn_add_soft.clicked.connect(self._blacklist_add_software)
        btn_layout.addWidget(self.btn_add_soft)

        self.btn_add_file = QPushButton("选择文件加入黑名单")
        self.btn_add_file.clicked.connect(self._blacklist_add_file)
        btn_layout.addWidget(self.btn_add_file)

        self.btn_remove_black = QPushButton("移除选中项")
        self.btn_remove_black.clicked.connect(self._blacklist_remove)
        btn_layout.addWidget(self.btn_remove_black)
        soft_layout.addLayout(btn_layout)
        soft_group.setLayout(soft_layout)
        layout.addWidget(soft_group)

        # 当前黑名单
        bl_group = QGroupBox("当前黑名单")
        bl_layout = QVBoxLayout()
        self.blacklist_list = QListWidget()
        self.blacklist_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._refresh_blacklist_list()
        bl_layout.addWidget(self.blacklist_list)
        bl_group.setLayout(bl_layout)
        layout.addWidget(bl_group)

        self.tab_blacklist.setLayout(layout)

    def _refresh_blacklist_list(self):
        self.blacklist_list.clear()
        blacklist = load_blacklist_file()
        for item in blacklist:
            self.blacklist_list.addItem(item)

    def _blacklist_add_software(self):
        selected = self.software_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先在已安装软件列表中选择要加入黑名单的软件")
            return
        blacklist = load_blacklist_file()
        for item in selected:
            entry = item.text().strip()
            if entry and entry not in blacklist:
                blacklist.append(entry)
        save_blacklist_file(blacklist)
        self._refresh_blacklist_list()

    def _blacklist_add_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要加入黑名单的文件", "", "可执行文件 (*.exe *.dll)")
        if not files:
            return
        blacklist = load_blacklist_file()
        for fpath in files:
            fname = os.path.basename(fpath).strip()
            if fname and fname not in blacklist:
                blacklist.append(fname)
        save_blacklist_file(blacklist)
        self._refresh_blacklist_list()

    def _blacklist_remove(self):
        selected = self.blacklist_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先在当前黑名单列表中选择要移除的项")
            return
        blacklist = load_blacklist_file()
        for item in selected:
            entry = item.text()
            if entry in blacklist:
                blacklist.remove(entry)
        save_blacklist_file(blacklist)
        self._refresh_blacklist_list()

    def reload_ui(self):
        for row, (edge_key, display_name, is_side) in enumerate(EDGE_ZONES):
            gesture = self.config["gestures"].get(edge_key, {})
            widgets = self.edge_widgets[edge_key]
            if is_side:
                action_short = gesture.get("action_short", "close_window")
                threshold_short = gesture.get("threshold_short", 25)
                action_long = gesture.get("action_long", "win_tab")
                threshold_long = gesture.get("threshold_long", 100)
                idx = widgets["combo_short"].findData(action_short)
                if idx >= 0:
                    widgets["combo_short"].setCurrentIndex(idx)
                widgets["spin_short"].setValue(threshold_short)
                idx = widgets["combo_long"].findData(action_long)
                if idx >= 0:
                    widgets["combo_long"].setCurrentIndex(idx)
                widgets["spin_long"].setValue(threshold_long)
            else:
                action = gesture.get("action", "none")
                threshold = gesture.get("threshold", 25)
                idx = widgets["combo"].findData(action)
                if idx >= 0:
                    widgets["combo"].setCurrentIndex(idx)
                widgets["spin"].setValue(threshold)
        # 重新加载动画配置
        self._reload_animation_ui()

    def _reload_animation_ui(self):
        anim_cfg = self.config.get("animation", {})
        # 只在对应控件存在时刷新
        if hasattr(self, "anim_burst_duration"):
            self.anim_burst_duration.setValue(anim_cfg.get("burst_duration", 350))
            self.anim_burst_radius.setValue(anim_cfg.get("burst_max_radius", 70))
            self.anim_hold_radius.setValue(anim_cfg.get("hold_max_radius", 60))
            durations = anim_cfg.get("durations", {})
            colors = anim_cfg.get("colors", {})
            if hasattr(self, "color_widgets"):
                for key, w in self.color_widgets.items():
                    hex_str = colors.get(key, "")
                    if hex_str:
                        w["preview"].setStyleSheet(f"background-color: {hex_str}; border: 1px solid #888; border-radius: 4px;")
                        w["hex_label"].setText(hex_str)
                    spin = w.get("duration_spin")
                    if spin is not None:
                        raw_val = durations.get(key)
                        if raw_val is not None:
                            spin.setValue(raw_val)
                        else:
                            spin.setValue(0)  # 0 → 显示"全局"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = GestureConfigUI()
    w.show()
    sys.exit(app.exec())