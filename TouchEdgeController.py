# -*- coding: utf-8 -*-
import sys, os, time, ctypes, subprocess
from ctypes import wintypes

# Win32 API
import win32api, win32con, win32gui

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
    QInputDialog, QMessageBox, QWidget, QLabel
)
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter
from PyQt6.QtCore import Qt, QRect, QTimer
import TouchEdgeControllerLib

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建并启用触控助手
    manager = TouchEdgeControllerLib.TouchEdgeManager(app)
    manager.enable()

    # 保持事件循环运行
    sys.exit(app.exec())
