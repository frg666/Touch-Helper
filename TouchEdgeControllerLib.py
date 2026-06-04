# -*- coding: utf-8 -*-
import sys, os, time, ctypes, json
from ctypes import wintypes

# Win32 API
import win32api, win32con, win32gui, win32process

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
    QInputDialog, QMessageBox, QWidget, QLabel
)
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, QRect, QTimer, QVariantAnimation

user32 = ctypes.windll.user32

CONFIG_FILE = "gesture_config.json"
BLACKLIST_FILE = "blacklist.txt"
TOUCH_STATE_FILE = "last_touch_state.txt"

blacklist = None
tip_window = None
tip_timer = None
tip_shown = False
last_state = None
cur_state = None
gesture_config = None


def load_gesture_config():
    global gesture_config
    default_config = {
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
        "close_zone_top": -1,  # -1 表示使用屏幕高度
        "app_overrides": {},
        "animation": {
            "burst_duration": 350,
            "burst_max_radius": 70,
            "hold_max_radius": 60,
            "durations": {
                "danger": null,
                "navigate": null,
                "edit": null,
                "reminder": null,
                "other": null,
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
    if not os.path.exists(CONFIG_FILE):
        gesture_config = default_config
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            gesture_config = json.load(f)
        return gesture_config
    except (json.JSONDecodeError, Exception):
        gesture_config = default_config
        return default_config


def init_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        default_apps = [
            "Shell_TrayWnd","Progman","Button","WorkerW",
            "TaskManagerWindow","Windows.UI.Core.CoreWindow"
        ]
        with open(BLACKLIST_FILE,"w",encoding="utf-8") as f:
            for app in default_apps:
                f.write(app+"\n")

def load_blacklist():
    global blacklist
    with open(BLACKLIST_FILE,"r",encoding="utf-8") as f:
        blacklist = [line.strip() for line in f if line.strip()]

def get_last_touch_state():
    if os.path.exists(TOUCH_STATE_FILE):
        with open(TOUCH_STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def get_window_under_cursor():
    pt = win32api.GetCursorPos()
    hwnd = win32gui.WindowFromPoint(pt)
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    return hwnd

def get_foreground_app_exe():
    hwnd = get_window_under_cursor()
    if not hwnd:
        return ""
    try:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h_process = win32api.OpenProcess(0x0400 | 0x0010, False, pid.value)
        if h_process:
            exe_name = win32process.GetModuleFileNameEx(h_process, 0)
            win32api.CloseHandle(h_process)
            return os.path.basename(exe_name).lower()
    except:
        pass
    return ""

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

def minimize_window_foreground():
    global blacklist
    hwnd = get_window_under_cursor()
    if hwnd:
        title = win32gui.GetWindowText(hwnd)
        clsname = win32gui.GetClassName(hwnd)
        for item in blacklist:
            if item.lower() in title.lower() or item.lower() in clsname.lower():
                return
        user32.PostMessageW(hwnd, win32con.WM_SYSCOMMAND, 0xF020, 0)

def send_alt_f4():
    hwnd = get_window_under_cursor()
    if hwnd:
        user32.PostMessageW(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, 0)

def send_key_combo(modifier, key):
    if modifier:
        win32api.keybd_event(modifier, 0, 0, 0)
    if key:
        win32api.keybd_event(key, 0, 0, 0)
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
    if modifier:
        win32api.keybd_event(modifier, 0, win32con.KEYEVENTF_KEYUP, 0)

VK_A = ord('A')
VK_D = ord('D')
VK_E = ord('E')
VK_I = ord('I')
VK_L = ord('L')
VK_M = ord('M')
VK_N = ord('N')
VK_S = ord('S')
VK_X = ord('X')
VK_Y = ord('Y')
VK_Z = ord('Z')
VK_C = ord('C')
VK_V = ord('V')

def trigger_win_tab():
    send_key_combo(win32con.VK_LWIN, win32con.VK_TAB)

def trigger_win():
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)

def trigger_win_A():
    send_key_combo(win32con.VK_LWIN, VK_A)

def trigger_win_N():
    send_key_combo(win32con.VK_LWIN, VK_N)

def trigger_win_D():
    send_key_combo(win32con.VK_LWIN, VK_D)

def trigger_win_E():
    send_key_combo(win32con.VK_LWIN, VK_E)

def trigger_win_I():
    send_key_combo(win32con.VK_LWIN, VK_I)

def trigger_win_L():
    send_key_combo(win32con.VK_LWIN, VK_L)

def trigger_win_M():
    send_key_combo(win32con.VK_LWIN, VK_M)

def trigger_alt_f4():
    send_alt_f4()

def trigger_close_window():
    send_command_to_foreground()

def trigger_minimize_window():
    minimize_window_foreground()

def trigger_ctrl_c():
    send_key_combo(win32con.VK_CONTROL, VK_C)

def trigger_ctrl_v():
    send_key_combo(win32con.VK_CONTROL, VK_V)

def trigger_ctrl_x():
    send_key_combo(win32con.VK_CONTROL, VK_X)

def trigger_ctrl_z():
    send_key_combo(win32con.VK_CONTROL, VK_Z)

def trigger_ctrl_y():
    send_key_combo(win32con.VK_CONTROL, VK_Y)

def trigger_ctrl_s():
    send_key_combo(win32con.VK_CONTROL, VK_S)

def trigger_ctrl_a():
    send_key_combo(win32con.VK_CONTROL, VK_A)

def trigger_enter():
    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)

def trigger_none():
    pass

ACTION_MAP = {
    "win": trigger_win,
    "win_tab": trigger_win_tab,
    "win_n": trigger_win_N,
    "win_a": trigger_win_A,
    "win_d": trigger_win_D,
    "win_e": trigger_win_E,
    "win_i": trigger_win_I,
    "win_l": trigger_win_L,
    "win_m": trigger_win_M,
    "alt_f4": trigger_alt_f4,
    "close_window": trigger_close_window,
    "minimize_window": trigger_minimize_window,
    "ctrl_c": trigger_ctrl_c,
    "ctrl_v": trigger_ctrl_v,
    "ctrl_x": trigger_ctrl_x,
    "ctrl_z": trigger_ctrl_z,
    "ctrl_y": trigger_ctrl_y,
    "ctrl_s": trigger_ctrl_s,
    "ctrl_a": trigger_ctrl_a,
    "enter": trigger_enter,
    "none": trigger_none,
}


def dispatch_action(action_key):
    func = ACTION_MAP.get(action_key)
    if func:
        func()


def get_edge_config(edge):
    global gesture_config
    if gesture_config is None:
        load_gesture_config()
    return gesture_config.get("gestures", {}).get(edge, {})


def get_close_zone_top():
    global gesture_config
    if gesture_config is None:
        load_gesture_config()
    val = gesture_config.get("close_zone_top", -1)
    if val <= 0:
        return user32.GetSystemMetrics(1)  # SM_CYSCREEN 屏幕高度
    return val


def get_app_overrides():
    global gesture_config
    if gesture_config is None:
        load_gesture_config()
    return gesture_config.get("app_overrides", {})


def get_animation_config():
    global gesture_config
    if gesture_config is None:
        load_gesture_config()
    return gesture_config.get("animation", {})


def is_in_close_zone(y_pos):
    return y_pos <= get_close_zone_top()


def get_effective_action(edge, default_action, default_action_long=None):
    app_exe = get_foreground_app_exe()
    if not app_exe:
        return default_action, default_action_long
    overrides = get_app_overrides()
    app_cfg = overrides.get(app_exe, {})
    edge_override = app_cfg.get(edge, {})
    if isinstance(edge_override, str):
        return edge_override, default_action_long
    if isinstance(edge_override, dict):
        action = edge_override.get("action", default_action)
        action_long = edge_override.get("action_long", default_action_long)
        return action, action_long
    return default_action, default_action_long


class EdgeBlocker(QWidget):
    def __init__(self, rect: QRect, edge: str):
        super().__init__()
        self.edge = edge
        self.start_pos = None
        self.global_start_pos = None
        self.hold_indicator = None
        self.slide_count = 0
        self.last_slide_time = 0

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self.setGeometry(rect)
        self.setWindowOpacity(0.01)
        #self.timer = QTimer()
        #self.timer.timeout.connect(self.check_state)
        #self.timer.start(200)

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
            self.global_start_pos = event.globalPosition().toPoint()

            # 显示按下保持指示器（淡紫色小圆环）
            if self.hold_indicator:
                self.hold_indicator.close()
            pos = self.global_start_pos
            self.hold_indicator = TouchFeedback(pos.x(), pos.y(), mode="hold")
            _feedback_refs.append(self.hold_indicator)
            self.hold_indicator.show()

    def mouseMoveEvent(self, event):
        if self.start_pos and self.hold_indicator and self.global_start_pos:
            delta_x = event.pos().x() - self.start_pos.x()
            delta_y = event.pos().y() - self.start_pos.y()
            dist = abs(delta_x) if self.edge in ("left", "right") else abs(delta_y)
            # 滑动距离→半径：0px→15, 100px→60，位置始终在按下点
            radius = 15 + dist * 0.45
            # 达到长滑阈值变色
            cfg = get_edge_config(self.edge)
            long_threshold = cfg.get("threshold_long", 100) if cfg else 100
            long_press = dist >= long_threshold
            self.hold_indicator.update_hold(self.global_start_pos.x(), self.global_start_pos.y(), radius, long_press)

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
            cfg = get_edge_config(self.edge)

            if not cfg:
                self.start_pos = None
                return

            is_side = "action_short" in cfg

            if is_side:
                threshold_short = cfg.get("threshold_short", 25)
                threshold_long = cfg.get("threshold_long", 100)
                action_short = cfg.get("action_short", "none")
                action_long = cfg.get("action_long", "none")
                double_slide = cfg.get("double_slide", True)

                # 应用定制：检查当前前台应用是否有覆盖配置
                override_short, override_long = get_effective_action(self.edge, action_short, action_long)
                if override_short is not None:
                    action_short = override_short
                if override_long is not None:
                    action_long = override_long

                # 获取触摸起始Y坐标，用于关闭/最小化区域检测
                touch_y = self.start_pos.y()
                in_zone = is_in_close_zone(touch_y)

                def _check_allowed(act, edge):
                    if edge in ("left", "right") and act in ("close_window", "minimize_window"):
                        return in_zone
                    return True

                def _do_dispatch(act):
                    dispatch_action(act)
                    if self.global_start_pos:
                        show_feedback_at(self.global_start_pos.x(), self.global_start_pos.y(), act)

                if self.edge == "left" and delta_x >= threshold_short:
                    if double_slide:
                        if _check_allowed(action_short, self.edge):
                            self._handle_double_slide(action_short)
                    elif delta_x > threshold_long:
                        if _check_allowed(action_long, self.edge):
                            _do_dispatch(action_long)
                    else:
                        if _check_allowed(action_short, self.edge):
                            _do_dispatch(action_short)
                elif self.edge == "right" and -delta_x >= threshold_short:
                    if double_slide:
                        if _check_allowed(action_short, self.edge):
                            self._handle_double_slide(action_short)
                    elif -delta_x > threshold_long:
                        if _check_allowed(action_long, self.edge):
                            _do_dispatch(action_long)
                    else:
                        if _check_allowed(action_short, self.edge):
                            _do_dispatch(action_short)
                elif self.edge == "top2" and delta_y >= threshold_short:
                    if double_slide:
                        self._handle_double_slide(action_short)
                    elif delta_y > threshold_long:
                        _do_dispatch(action_long)
                    else:
                        _do_dispatch(action_short)
                elif self.edge == "bottom2" and -delta_y >= threshold_short:
                    if double_slide:
                        self._handle_double_slide(action_short)
                    elif -delta_y > threshold_long:
                        _do_dispatch(action_long)
                    else:
                        _do_dispatch(action_short)
            else:
                action = cfg.get("action", "none")
                threshold = cfg.get("threshold", 25)

                # 应用定制：检查当前前台应用是否有覆盖配置
                override_action, _ = get_effective_action(self.edge, action, None)
                if override_action is not None:
                    action = override_action

                if self.edge in ("top1", "top2", "top3") and delta_y >= threshold:
                    dispatch_action(action)
                    if self.global_start_pos:
                        show_feedback_at(self.global_start_pos.x(), self.global_start_pos.y(), action)
                elif self.edge in ("bottom1", "bottom2", "bottom3") and -delta_y >= threshold:
                    dispatch_action(action)
                    if self.global_start_pos:
                        show_feedback_at(self.global_start_pos.x(), self.global_start_pos.y(), action)

            # 关闭按下保持指示器
            if self.hold_indicator:
                self.hold_indicator.close()
                self.hold_indicator = None
            self.start_pos = None

    def _handle_double_slide(self, action_short):
        now = time.time()
        if now - self.last_slide_time <= 1.5:
            self.slide_count += 1
        else:
            self.slide_count = 1
            show_tip(f"再次滑动以触发: {get_action_display_name(action_short)}")
            # 第一次滑动提醒动画（琥珀色 burst，缩短为175ms）
            if self.global_start_pos:
                show_feedback_at(self.global_start_pos.x(), self.global_start_pos.y(), "reminder", mode="burst", duration_ms=175)
        self.last_slide_time = now

        if self.slide_count == 2:
            dispatch_action(action_short)
            if self.global_start_pos:
                show_feedback_at(self.global_start_pos.x(), self.global_start_pos.y(), action_short, mode="burst")
            show_tip(get_action_display_name(action_short))
            close_tip()
            self.slide_count = 0
            self.last_slide_time = 0

    def restore_bg(self):
        self.setWindowOpacity(0.01)
        show_tip("触控手势已恢复", 1000)

def get_action_display_name(action_key):
    names = {
        "win": "Win（开始菜单）",
        "win_tab": "Win+Tab（任务视图）",
        "win_n": "Win+N（通知中心）",
        "win_a": "Win+A（操作中心）",
        "win_d": "Win+D（显示桌面）",
        "win_e": "Win+E（文件资源管理器）",
        "win_i": "Win+I（系统设置）",
        "win_l": "Win+L（锁定屏幕）",
        "win_m": "Win+M（最小化所有窗口）",
        "alt_f4": "Alt+F4（关闭窗口）",
        "close_window": "关闭窗口",
        "minimize_window": "最小化窗口",
        "ctrl_c": "Ctrl+C（复制）",
        "ctrl_v": "Ctrl+V（粘贴）",
        "ctrl_x": "Ctrl+X（剪切）",
        "ctrl_z": "Ctrl+Z（撤销）",
        "ctrl_y": "Ctrl+Y（重做）",
        "ctrl_s": "Ctrl+S（保存）",
        "ctrl_a": "Ctrl+A（全选）",
        "enter": "Enter（回车）",
        "none": "无动作",
    }
    return names.get(action_key, action_key)


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


def show_tip(text, time=1500):
    global tip_shown, tip_window
    if tip_window:
        close_tip()
    tip_window = TipWindow(text, time)
    tip_window.show()
    tip_shown = True

def close_tip():
    global tip_shown, tip_window, tip_timer
    if tip_window:
        tip_window.close()
        tip_timer.stop()
        tip_window = None
    tip_shown = False


# 全局引用列表，防止 TouchFeedback 被 GC 回收
_feedback_refs = []

# 动作键 → 颜色分类映射（也用于 per-category 时长覆盖）
ACTION_CATEGORY_MAP = {
    "close_window": "danger",
    "minimize_window": "danger",
    "alt_f4": "danger",
    "win": "navigate",
    "win_tab": "navigate",
    "win_d": "navigate",
    "win_m": "navigate",
    "ctrl_c": "edit",
    "ctrl_v": "edit",
    "ctrl_x": "edit",
    "ctrl_z": "edit",
    "ctrl_y": "edit",
    "ctrl_s": "edit",
    "ctrl_a": "edit",
    "reminder": "reminder",
}


class TouchFeedback(QWidget):
    """触摸反馈—— hold: 保持小圆环 | burst: 扩张淡出动画 """
    def __init__(self, global_x, global_y, action_key="", mode="burst", duration_ms=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.mode = mode

        # 从配置读取动画参数
        anim_cfg = get_animation_config()
        colors = anim_cfg.get("colors", {})
        burst_max_radius = anim_cfg.get("burst_max_radius", 70)
        hold_max_radius = anim_cfg.get("hold_max_radius", 60)

        # 颜色映射
        color_map = {
            "close_window": colors.get("danger", "#FF6464"),
            "minimize_window": colors.get("danger", "#FF6464"),
            "alt_f4": colors.get("danger", "#FF6464"),
            "win": colors.get("navigate", "#64C8FF"),
            "win_tab": colors.get("navigate", "#64C8FF"),
            "win_d": colors.get("navigate", "#64C8FF"),
            "win_m": colors.get("navigate", "#64C8FF"),
            "reminder": colors.get("reminder", "#FFC832"),
        }

        # 颜色
        if mode == "hold":
            self.base_color = QColor(colors.get("hold_normal", "#C8C8FF"))
            self.radius = 15
            self.max_radius = hold_max_radius
            self.opacity = 0.45
            # 固定 widget 大小以支持半径动态变化
            self.setGeometry(global_x - 80, global_y - 80, 160, 160)
        else:
            hex_color = color_map.get(action_key, colors.get("other", "#B4B4FF"))
            self.base_color = QColor(hex_color)
            self.radius = 8
            self.max_radius = burst_max_radius
            self.opacity = 0.9
            size = self.max_radius * 2 + 20
            self.setGeometry(global_x - size // 2, global_y - size // 2, size, size)

        if mode == "burst":
            if duration_ms is None:
                # 先查 per-category 覆盖，再回退到全局时长
                category = ACTION_CATEGORY_MAP.get(action_key)
                per_category = anim_cfg.get("durations", {}).get(category) if category else None
                duration_ms = per_category if per_category is not None else anim_cfg.get("burst_duration", 350)
            self.anim = QVariantAnimation(self)
            self.anim.setDuration(duration_ms)
            self.anim.setStartValue(0.0)
            self.anim.setEndValue(1.0)
            self.anim.valueChanged.connect(self._on_burst_step)
            self.anim.finished.connect(self._on_burst_end)
            self.anim.start()
        # hold 模式无动画，保持显示直到外部 close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self.base_color)
        c.setAlphaF(max(self.opacity, 0.0))
        painter.setPen(QPen(c, 3))
        painter.setBrush(QBrush(c))
        center = self.rect().center()
        painter.drawEllipse(center, int(self.radius), int(self.radius))

        # 内圈高光（仅 burst 模式）
        if self.mode == "burst":
            inner = QColor(255, 255, 255)
            inner.setAlphaF(max(self.opacity * 0.4, 0.0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(inner))
            painter.drawEllipse(center, int(self.radius * 0.35), int(self.radius * 0.35))

    def _on_burst_step(self, progress):
        self.radius = 8 + (self.max_radius - 8) * progress
        self.opacity = 0.9 * (1.0 - progress * progress)
        self.update()

    def _on_burst_end(self):
        self.close()

    def update_hold(self, global_x, global_y, radius, long_press=False):
        """hold 模式下动态更新位置和半径（随手指滑动）"""
        if self.mode != "hold":
            return
        anim_cfg = get_animation_config()
        colors = anim_cfg.get("colors", {})
        self.setGeometry(global_x - 80, global_y - 80, 160, 160)
        self.radius = max(15, min(self.max_radius, radius))
        if long_press:
            self.base_color = QColor(colors.get("hold_long", "#FFA03C"))
            self.opacity = 0.55
        else:
            self.base_color = QColor(colors.get("hold_normal", "#C8C8FF"))
            self.opacity = 0.45
        self.update()

    def closeEvent(self, event):
        if self in _feedback_refs:
            _feedback_refs.remove(self)
        super().closeEvent(event)


def show_feedback_at(global_x, global_y, action_key="", mode="burst", duration_ms=None):
    fb = TouchFeedback(global_x, global_y, action_key, mode, duration_ms)
    _feedback_refs.append(fb)
    fb.show()

def force_above_taskbar(widget):
    hwnd = int(widget.winId())
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                          0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)


class TouchEdgeManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.edge_blockers = []
        init_blacklist()
        load_blacklist()
        load_gesture_config()

    def enable(self):
        screen = self.app.primaryScreen()
        geometry = screen.geometry()
        screen_width = geometry.width()
        screen_height = geometry.height()
        edge_width = 1

        left_rect = QRect(0, 0, edge_width, screen_height)
        right_rect = QRect(screen_width - edge_width, 0, edge_width, screen_height)
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
        self.edge_blockers = []
        show_tip("触控助手已禁用", 1000)

    def reload_config(self):
        load_gesture_config()
        show_tip("手势配置已重新加载", 1000)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建并启用触控助手
    manager = TouchEdgeManager(app)
    manager.enable()
    # 保持事件循环运行
    sys.exit(app.exec())