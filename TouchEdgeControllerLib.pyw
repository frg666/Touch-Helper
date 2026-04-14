# -*- coding: utf-8 -*-
import sys, os, time, ctypes

# Win32 API
import win32api, win32con, win32gui

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import Qt, QRect, QTimer

user32 = ctypes.windll.user32

EDGE_THRESHOLD = 25
SLIDE_THRESHOLD = 100
VK_A = ord('A')
VK_N = ord('N')
BLACKLIST_FILE = "blacklist.txt"
TOUCH_STATE_FILE = "last_touch_state.txt"

blacklist = None
tip_window = None
tip_timer = None
tip_shown = False
last_state = None
cur_state = None

# 初始化触控优化黑名单应用文件
def init_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        default_apps = [
            "Shell_TrayWnd","Progman","Button","WorkerW",
            "TaskManagerWindow","Windows.UI.Core.CoreWindow"
        ]
        with open(BLACKLIST_FILE,"w",encoding="utf-8") as f:
            for app in default_apps:
                f.write(app+"\n")

# 加载触控优化黑名单应用列表-
def load_blacklist():
    global blacklist
    with open(BLACKLIST_FILE,"r",encoding="utf-8") as f:
        blacklist = [line.strip() for line in f if line.strip()]

# 获取上一次触摸状态，当前版本暂时弃用功能
def get_last_touch_state():
    if os.path.exists(TOUCH_STATE_FILE):
        with open(TOUCH_STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

# 获取当前实际希望进行触控操作的页面
def get_window_under_cursor():
    pt = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint(pt)
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    return hwnd

# 对前台应用触发关闭命令
def send_command_to_foreground():
    global blacklist
    hwnd = get_window_under_cursor()
    if hwnd:
        title = win32gui.GetWindowText(hwnd)
        clsname = win32gui.GetClassName(hwnd)
        for item in blacklist:
            if item.lower() in title.lower() or item.lower() in clsname.lower():
                return
        user32.PostMessageW(hwnd, win32con.WM_CLOSE, 0, 0)

# 边缘手势遮蔽层组件
class EdgeBlocker(QWidget):
    def __init__(self, rect: QRect, edge: str):
        super().__init__()
        self.edge = edge
        self.start_pos = None
        self.slide_count = 0
        self.last_slide_time = 0

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setGeometry(rect)
        self.setWindowOpacity(0.01)
        # 触摸状态恢复定时器
        #self.timer = QTimer()
        #self.timer.timeout.connect(self.check_state)
        #self.timer.start(200)

    # 检查当前触摸状态
    def check_state(self):
        global last_state, cur_state
        cur_state = get_last_touch_state()
        if (cur_state in ["按下", "按下-移动", "按下-驻留"] or not (last_state == cur_state)) and self.windowOpacity() == 0:
            self.restore_bg()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            global last_state
            last_state = get_last_touch_state()
            #if last_state not in ["按下", "按下-移动","按下-驻留"]:
                #self.setWindowOpacity(0)
                #show_tip("触控手势已关闭", 1000)
                #return
            self.start_pos = event.pos()

    def restore_bg(self):
        self.setWindowOpacity(0.01)
        show_tip("触控手势已恢复", 1000)

    def mouseReleaseEvent(self, event):
        global blacklist
        hwnd1 = get_window_under_cursor()
        title = win32gui.GetWindowText(hwnd1)
        clsname = win32gui.GetClassName(hwnd1)
        for item in blacklist:
            if item.lower() in title.lower() or item.lower() in clsname.lower():
                return

        if self.start_pos:
            global last_state
            last_state = get_last_touch_state()
            #if last_state not in ["松开"]:
                #return
            delta_x = event.pos().x() - self.start_pos.x()
            delta_y = event.pos().y() - self.start_pos.y()
            triggered = False
            # 边缘短滑手势判断，左右滑向内！！！
            if self.edge == "top2" and delta_y >= EDGE_THRESHOLD:
                trigger_win()
            elif self.edge == "top3" and delta_y >= EDGE_THRESHOLD:
                trigger_win_N()
            elif self.edge == "top1" and delta_y >= EDGE_THRESHOLD:
                trigger_win_tab()
            elif self.edge == "bottom2" and -delta_y >= EDGE_THRESHOLD:
                trigger_win()
            elif self.edge == "bottom3" and -delta_y >= EDGE_THRESHOLD:
                trigger_win_N()
            elif self.edge == "bottom1" and -delta_y >= EDGE_THRESHOLD:
                trigger_win_tab()
            elif self.edge == "left" and delta_x >= EDGE_THRESHOLD:
            #and delta_x <= SLIDE_THRESHOLD:
                triggered = True
            elif self.edge == "right" and -delta_x >= EDGE_THRESHOLD:
            #and -delta_x <= SLIDE_THRESHOLD:
                triggered = True
            # 用于全屏体验模式关闭了边缘手势后上滑开启优化的任务视图
            elif self.edge == "bottom" and -delta_y >= EDGE_THRESHOLD and -delta_y <= SLIDE_THRESHOLD:
                trigger_win_tab()
            # 边缘长滑手势判断，左右滑向内！！！

            if self.edge == "left" and delta_x > SLIDE_THRESHOLD:
                trigger_win_tab()    
                
            if triggered and self.edge != "bottom":
                now = time.time()
                if now - self.last_slide_time <= 1.5:
                    self.slide_count += 1
                else:
                    self.slide_count = 1
                    show_tip("再次滑动以关闭")
                self.last_slide_time = now

                if self.slide_count == 2:
                    send_command_to_foreground()
                    close_tip()
                    self.slide_count = 0
                    self.last_slide_time = 0

            self.start_pos = None


# 透明提示框
class TipWindow(QWidget):
    def __init__(self, text, time=1500, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 30px; padding: 20px;")
        self.label.adjustSize()
        self.resize(self.label.width() + 40, self.label.height() + 40)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2,
                  screen.center().y() - self.height() // 2)

        global tip_timer
        tip_timer = QTimer(self)
        tip_timer.setSingleShot(True)
        tip_timer.timeout.connect(close_tip)
        tip_timer.start(time)


# 显示提示内容
def show_tip(text, time=1500):
    global tip_shown, tip_window
    if tip_window:
        close_tip()
    tip_window = TipWindow(text, time)
    tip_window.show()
    tip_shown = True

# 关闭提示信息
def close_tip():
    global tip_shown, tip_window, tip_timer
    try:
        if tip_window:
            tip_window.close()
            tip_timer.stop()
            tip_window = None
        tip_shown = False
    except Exception as e:
        tip_window = None
        tip_shown = False

# 校验当前系统版本号
def get_windows_version():
    if sys.platform != 'win32':
        return "非 Windows 系统"

    build = sys.getwindowsversion().build
    if build >= 22000:
        return "Windows 11"
    elif 10240 <= build <= 19045:
        return "Windows 10"
    else:
        return f"未知 Windows 版本 (Build {build})"

# 打开任务视图
def trigger_win_tab():
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)
    win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    
# 打开开始菜单
def trigger_win():
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)

# 打开通知
def trigger_win_N():
    windows_version = get_windows_version()
    if windows_version == "Windows 11" or windows_version == "Windows 10":
        win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
        if windows_version == "Windows 10":
            win32api.keybd_event(VK_A, 0, 0, 0)
            win32api.keybd_event(VK_A, 0, win32con.KEYEVENTF_KEYUP, 0)
        else:
            win32api.keybd_event(VK_N, 0, 0, 0)
            win32api.keybd_event(VK_N, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    else:
        show_tip(windows_version + "is unabled", 1000)

# 将widget窗体置于顶层
def force_above_taskbar(widget):
    hwnd = int(widget.winId())
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                          0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)


# 触摸优化管理器(启用和调整边缘触摸功能的地方)
class TouchEdgeManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.edge_blockers = []
        init_blacklist()
        load_blacklist()

    def enable(self):
        screen = self.app.primaryScreen()
        geometry = screen.geometry()
        screen_width = geometry.width()
        screen_height = geometry.height()
        edge_width = 1

        left_rect = QRect(0, 0, edge_width, screen_height // 10)
        right_rect = QRect(screen_width - edge_width, 0, edge_width, screen_height // 10)
        #bottom_rect = QRect(0, screen_height - edge_width, screen_width, edge_width)
        top_rect1 = QRect(0, 0, screen_width // 4, edge_width)
        top_rect2 = QRect(screen_width // 4, 0, screen_width // 2, edge_width)
        top_rect3 = QRect(screen_width // 4 * 3, 0, screen_width // 4, edge_width)
        bottom_rect1 = QRect(0, screen_height - edge_width, screen_width // 4, edge_width)
        bottom_rect2 = QRect(screen_width // 4, screen_height - edge_width, screen_width // 2, edge_width)
        bottom_rect3 = QRect(screen_width // 4 * 3, screen_height - edge_width, screen_width // 4, edge_width)

        self.edge_blockers = [
            EdgeBlocker(left_rect, "left"),
            EdgeBlocker(right_rect, "right"),
            EdgeBlocker(top_rect1, "top1"),
            EdgeBlocker(top_rect2, "top2"),
            EdgeBlocker(top_rect3, "top3"),
            EdgeBlocker(bottom_rect1, "bottom1"),
            EdgeBlocker(bottom_rect2, "bottom2"),
            EdgeBlocker(bottom_rect3, "bottom3")
        ]
        for blocker in self.edge_blockers:
            blocker.show()
            force_above_taskbar(blocker)
        show_tip("触控助手已启用", 1000)

    def disable(self):
        for blocker in self.edge_blockers:
            blocker.close()
        self.edge_blockers = [] # 清空引用，避免残留
        show_tip("触控助手已禁用", 1000)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建并启用触控助手
    manager = TouchEdgeManager(app)
    manager.enable()
    # 保持事件循环运行
    sys.exit(app.exec())
