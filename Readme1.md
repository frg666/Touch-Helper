# TouchFlow — Windows 触控手势引擎

### 项目概述
一款自主研发的 Windows 触控增强系统，通过底层 HID 协议解析 + 上层手势识别引擎，为触摸屏设备提供类 iPad 的边缘滑动多任务交互体验。支持屏幕四边 8 区域的差异化手势识别，涵盖应用切换、窗口关闭、通知中心唤起等高频操作。

### 技术栈
| 层次 | 技术 |
|------|------|
| 系统编程 | Win32 API / Raw Input / HID 协议 / P/Invoke |
| 底层采集 | C# .NET Framework 4.7.2 |
| 上层交互 | Python 3 / PyQt6 |
| 进程通信 | 文件状态共享 / 跨进程消息传递 |

### 架构总览

四层架构设计：C# 数据采集层 → 系统集成层（Win32 API） → 手势引擎层（PyQt6） → 用户交互层（系统托盘 + 透明覆盖层）
跨语言混合架构：C# 负责高频率触摸数据采集，Python 负责手势判定和 UI，通过文件状态共享实现松耦合通信。

### 个人角色
独立完成全项目开发，包括：底层 HID 数据解析与触摸状态机设计、Win32 全局钩子与窗口消息处理、PyQt6 手势引擎与透明覆盖层开发、多进程守护与管理工具开发。

### 成果概要
- 手势识别覆盖屏幕 4 边 8 个区域
- 触摸数据以 ~60Hz 频率采样，毫秒级响应
- 日志自动压缩归档，支持 50MB 自动轮转
- 兼容所有 Windows HID 触摸屏与触控笔

### 一、项目文件结构
| 文件 | 职责 |
|------|------|
| TouchHelper.py | 主控程序，系统托盘常驻，负责启停各子进程；右键菜单含"自定义手势配置"入口 |
| TouchEdgeController.py | 入口，实例化 TouchEdgeManager 并启动事件循环 |
| TouchEdgeControllerLib.py | 手势核心库，边缘检测 + 配置驱动的手势判定 + 键盘模拟 |
| TouchStartMenu.py | 任务栏底部透明覆盖层，支持上滑触发自定义操作 |
| 1.py | 全局鼠标钩子，检测 DV2ControlHost 窗口快速点击方向 |
| add_blackList.py | 黑名单管理器 GUI，可手动添加应用或 exe 文件 |
| GestureConfigUI.py | 自定义手势配置 UI（双选项卡：默认手势配置 + 应用定制），表格展示 8 区域并提供动作/阈值/应用覆盖配置 |
| gesture_config.json | 手势配置数据文件，JSON 格式存储各边缘区域的动作映射、关闭区域高度、应用定制覆盖 |
| Program.cs | C# 触摸状态机，通过 Raw Input 读取触摸数据并写日志 |

### 二、C# 触摸状态机（Program.cs）
**功能**：通过 RegisterRawInputDevice 注册 HID Digitizer 设备，监听 WM_INPUT 消息。

**触摸状态四态转换**：
- 按下 → 检测到 pressState = 0x07，触笔/手指接触屏幕
- 按下-移动 → 状态为空时，速度 > 0.01，表示正在滑动
- 按下-驻留 → 状态为空时，速度 ≤ 0.01，表示按住不动
- 松开 → pressState = 0x04，手指/触笔离开

**坐标映射算法**：
- 设备原始坐标（Raw X/Y）→ 屏幕坐标映射
- DeviceMaxX / DeviceMaxY 对应触摸屏硬件分辨率
- ScreenWidth / ScreenHeight 对应实际屏幕分辨率

**输出**：
- 实时写入 last_touch_state.txt（当前状态，供 Python 读取）
- 增量写入 all_touch_log.txt（全量日志，含时间戳、坐标、状态、速度）
- 日志超过 50MB 或跨日自动 .gz 压缩归档，最多保留 20 个

### 三、边缘手势引擎（TouchEdgeControllerLib.py）

#### 3.1 屏幕划分（8 个检测区）
每个检测区是 1px 宽的透明无边框窗口，SetWindowPos(HWND_TOPMOST) 保持在最顶层。

#### 3.2 配置驱动的手势判定
手势判定采用 **配置驱动架构**：运行时从 `gesture_config.json` 加载各边缘区域的动作映射，通过 ACTION_MAP 字典动态派发到对应的触发函数。

**判定流程**（EdgeBlocker.mouseReleaseEvent()）：
1. 黑名单过滤 → 检查光标下窗口是否受保护
2. 读取手势配置 → `get_edge_config(edge)` 获取当前边缘的配置
3. **应用定制检查** → `get_effective_action()` 获取当前前台应用的覆盖动作（如果已配置）
4. **关闭区域检测**（左右侧边缘） → 若触发 `close_window` / `minimize_window`，检查触摸起始Y坐标 ≤ `close_zone_top`
5. 区分边缘类型：
   - **顶部/底部边缘**（top1/3, bottom1/3）：检测垂直滑动距离是否达到 threshold
   - **顶部/底部中间边缘**（top2, bottom2）：区分短滑（threshold_short）和长滑（threshold_long），支持双击滑动机制
   - **左右侧边缘**（left/right）：区分短滑（threshold_short）和长滑（threshold_long），支持双击滑动机制
6. 调用 `dispatch_action(action_key)` 从 ACTION_MAP 查找并执行对应函数

**默认手势映射**（可在 UI 中自定义修改）：

| 边缘 | 滑动方向 | 默认动作 |
|------|----------|----------|
| top1 (顶部左侧) | 向下 | Win+Tab（任务视图） |
| top2 (顶部中间) | 向下 | 短滑双击 Win+M（最小化所有窗口）；长滑 Win（开始菜单） |
| top3 (顶部右侧) | 向下 | Win+A（控制中心） |
| bottom1 (底部左侧) | 向上 | Win+Tab |
| bottom2 (底部中间) | 向上 | 短滑双击 Win+M（最小化所有窗口）；长滑 Win（开始菜单） |
| bottom3 (底部右侧) | 向上 | Win+N |
| left (左侧) 短滑 | 向右 | 双击滑动关闭窗口 |
| left (左侧) 长滑 | 向右 | Win+Tab |
| right (右侧) 短滑 | 向左 | 双击滑动关闭窗口 |
| right (右侧) 长滑 | 向左 | Win+Tab |

#### 3.3 双击关闭机制
- 1.5 秒内同一边缘连续滑动 2 次
- 第一次提示"再次滑动以触发: xxx"，累计计数
- 第二次触发配置的动作（默认关闭光标下窗口）
- 超时 1.5 秒重置计数
- 可通过配置关闭双击机制（double_slide: false），改为单次直接触发

#### 3.4 黑名单过滤
blacklist.txt 存储要保护的窗口类和标题关键词。每次手势触发前检查光标下的窗口：
- 匹配窗口类名（ClassName）或窗口标题
- 默认保护：Shell_TrayWnd（任务栏）、Progman（桌面）、TaskManagerWindow 等
- add_blackList.py 提供 GUI 管理工具

#### 3.5 键盘模拟实现
使用 win32api.keybd_event() 模拟按键，核心函数 `send_key_combo(modifier, key)` 统一处理修饰键+普通键的组合按下和释放。

**ACTION_MAP 支持的 21 种动作**：

| 动作 key | 函数 | 说明 |
|----------|------|------|
| win | trigger_win() | Win 键（开始菜单） |
| win_tab | trigger_win_tab() | Win+Tab（任务视图） |
| win_n | trigger_win_N() | Win+N（通知中心） |
| win_a | trigger_win_A() | Win+A（操作中心） |
| win_d | trigger_win_D() | Win+D（显示桌面） |
| win_e | trigger_win_E() | Win+E（文件资源管理器） |
| win_i | trigger_win_I() | Win+I（系统设置） |
| win_l | trigger_win_L() | Win+L（锁定屏幕） |
| win_m | trigger_win_M() | Win+M（最小化所有窗口） |
| alt_f4 | trigger_alt_f4() | Alt+F4 / WM_SYSCOMMAND SC_CLOSE |
| close_window | trigger_close_window() | PostMessage WM_CLOSE 关闭窗口 |
| minimize_window | trigger_minimize_window() | PostMessage WM_SYSCOMMAND SC_MINIMIZE 最小化窗口 |
| ctrl_c | trigger_ctrl_c() | Ctrl+C（复制） |
| ctrl_v | trigger_ctrl_v() | Ctrl+V（粘贴） |
| ctrl_x | trigger_ctrl_x() | Ctrl+X（剪切） |
| ctrl_z | trigger_ctrl_z() | Ctrl+Z（撤销） |
| ctrl_y | trigger_ctrl_y() | Ctrl+Y（重做） |
| ctrl_s | trigger_ctrl_s() | Ctrl+S（保存） |
| ctrl_a | trigger_ctrl_a() | Ctrl+A（全选） |
| enter | trigger_enter() | Enter（回车） |
| none | trigger_none() | 无动作 |

### 四、系统托盘主控（TouchHelper.py）
**功能**：
- 常驻系统托盘，图标切换表示启用/禁用状态
- 启动时自动拉起：TouchEdgeController.exe、TouchStartMenu.exe、TouchStateController.exe
- 双击托盘图标：切换启用/禁用
- 右键菜单：
  - 启用触控助手
  - 禁用触控助手
  - 重启所有外部程序
  - ─────
  - **自定义手势配置**（打开 GestureConfigUI 配置窗口）
  - ─────
  - 退出

**进程管理**：
- is_process_running() — 调用 tasklist 检测进程是否存在
- kill_process_by_name() — 调用 taskkill /f 强制结束进程
- 启动时隐藏控制台窗口（CREATE_NO_WINDOW + STARTF_USESHOWWINDOW）

### 五、鼠标方向拦截器（1.py）
**用途**：针对 DV2ControlHost 窗口的快速连续点击优化。

**逻辑**：
- SetWindowsHookEx(WH_MOUSE_LL) 安装全局低级鼠标钩子
- 每次左键点击记录坐标位置和方向（左半屏/右半屏）
- 140ms 内同方向连续点击 2 次 → 发送 Ctrl+左/右方向键

### 六、任务栏覆盖层（TouchStartMenu.py）
**功能**：屏幕底部 40px 高的半透明覆盖层。

**手势**：
- 底部区域上滑（delta_y < -20）→ 触发自定义动作（当前为打开记事本）

**特性**：
- WA_TransparentForMouseEvents 默认为 True，不拦截普通点击
- 仅捕获从底部向上滑动的操作

### 七、自定义手势配置 UI（GestureConfigUI.py）
**功能**：提供图形化界面，允许用户自定义每个边缘区域的手势动作和触发阈值。界面采用双选项卡布局。

#### 7.0 双选项卡结构
- **选项卡「默认手势配置」**：配置 8 个边缘区域的默认动作和阈值
- **选项卡「应用定制」**：配置关闭区域高度、按应用定制手势动作覆盖

#### 7.1 默认手势配置选项卡
- **标题**：顶部说明文字
- **配置表格**（QTableWidget）：
  - 8 行，每行对应一个边缘区域
  - 6 列：边缘区域、滑动方向、动作、触发阈值(px)、长滑动作、长滑阈值(px)
  - 顶部/底部边缘：动作 + 阈值可配
  - 左右侧边缘：短滑动作 + 短滑阈值 + 长滑动作 + 长滑阈值可配
- **操作按钮**：
  - 保存配置 → 写入 gesture_config.json
  - 恢复默认 → 重置为出厂默认值
  - 重新加载 → 从文件重新读取配置

#### 7.2 应用定制选项卡
- **关闭区域高度**（close_zone_top）：左右侧边缘的顶部像素阈值，仅在此区域内滑动才触发 `close_window` / `minimize_window` 操作（默认 200px，防误触）
- **应用定制列表**：
  - 左侧：已添加应用列表（QListWidget）
  - 右侧：添加/删除按钮 + 应用 exe 名称输入框
- **边缘覆盖配置表**：
  - 选中应用后，表格展示 8 个边缘区域
  - 侧边类型边缘（left/right/top2/bottom2）可分别设置短滑和长滑的覆盖动作
  - 「清除」按钮可清除单个边缘的覆盖配置
- **保存应用定制配置**：写入 gesture_config.json 的 `app_overrides` 字段

#### 7.3 配置存储
- 文件：gesture_config.json
- JSON 结构示例：
```json
{
  "gestures": {
    "top1": { "name": "顶部左侧", "action": "win_tab", "threshold": 25, "direction": "down" },
    "left": {
      "name": "左侧边缘",
      "action_short": "close_window", "threshold_short": 25,
      "action_long": "win_tab", "threshold_long": 100,
      "direction": "right", "double_slide": true
    }
  },
  "close_zone_top": 200,
  "app_overrides": {
    "notepad.exe": {
      "left": { "action_short": "ctrl_c", "action_long": "ctrl_v" },
      "top2": { "action_short": "ctrl_s", "action_long": "win" }
    }
  }
}
```
	- `close_zone_top`：左右侧边缘关闭/最小化操作的触发区域高度
	- `app_overrides`：按应用 exe 名称索引的动作覆盖配置
	- 每个应用可对任意边缘设置覆盖动作（键为边缘 key，值为动作字符串或含 action/action_long 的对象）
	- 若某应用无覆盖配置或某边缘无对应覆盖，使用默认手势配置

#### 7.4 热加载机制
- 保存配置后无需重启触控助手
- 在配置界面点击"重新加载"，或调用 TouchEdgeManager.reload_config() 即可生效
- reload_config() 重新读取 JSON 文件并更新全局 gesture_config

### 八、需要注意的技术细节
1. **触摸状态读取时机**：C# 每秒多次写入 last_touch_state.txt，Python 通过文件读取存在延迟，手势逻辑中其实未严格依赖该状态（相关代码被注释了）
2. **窗口置顶问题**：WA_TransparentForMouseEvents = False 时透明覆盖层会拦截鼠标事件，而设为 True 则无法接收手势。当前方案是 False + 极低透明度（0.01）
3. **多进程同步**：各 exe 独立进程，通过文件传递状态，无进程间锁，极端情况下可能读到不完整数据
4. **HID 设备兼容性**：不同的触摸屏原始坐标范围不同，DeviceMaxX/DeviceMaxY 需要针对设备校准
5. **配置热加载**：gesture_config.json 仅在启动和调用 reload_config() 时读取，运行时修改文件需手动重新加载

### 九、快捷键对照速查
| 手势操作 | 快捷键 | 功能 |
|----------|--------|------|
| 顶部中间下滑（短滑双击） | Win+M | 最小化所有窗口 |
| 顶部中间下滑（长滑） | Win | 开始菜单 |
| 顶部右侧下滑 | Win+A | 控制中心 |
| 顶部左侧下滑 | Win+Tab | 任务视图 |
| 底部中间上滑（短滑双击） | Win+M | 最小化所有窗口 |
| 底部中间上滑（长滑） | Win | 开始菜单 |
| 底部右侧上滑 | Win+A | 控制中心 |
| 底部左侧上滑 | Win+Tab | 任务视图 |
| 左右边缘短滑（双击） | WM_CLOSE / 自定义 | 关闭应用 |
| 左右边缘长滑 | Win+Tab / 自定义 | 任务视图 |
| 最小化窗口手势 | WM_SYSCOMMAND SC_MINIMIZE / 自定义 | 最小化窗口 |
| DV2ControlHost 同向双击 | Ctrl+←/→ | 桌面切换 |
> 以上为默认配置，所有动作均可通过 GestureConfigUI 自定义修改。

### 十、未来改进方向
1. 增加多点触控手势识别（当前仅单指）
2. 优化触摸状态读取逻辑，减少延迟，进一步优化对离电续航的影响
3. 增加触控反馈动画（当前仅文字提示）
4. 优化多进程同步机制，避免数据不一致
5. 自动适配不同分辨率的屏幕