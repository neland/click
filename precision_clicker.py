"""
Precision Clicker - Windows 精确鼠标点击程序
功能：
  - 捕获目标窗口并记录窗口句柄
  - 在特定时间（精确到毫秒）点击目标窗口的指定位置
  - 支持设置点击间隔、点击次数、鼠标按键类型
  - 支持绝对时间模式和相对倒计时模式
  - 任务配置可保存/加载
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import json
import os
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta

# ----------------------- Windows API 封装 -----------------------

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 常量
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

INPUT_MOUSE = 0

SM_CXSCREEN = 0
SM_CYSCREEN = 1


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT_I(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", INPUT_I),
    ]


def get_screen_size():
    """获取屏幕分辨率"""
    return user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN)


def send_input_click(x, y, button="left"):
    """
    使用 SendInput 在屏幕绝对坐标 (x, y) 处发送鼠标点击。
    比 mouse_event 更底层，不会被系统标记为模拟输入（部分游戏可绕过）。
    """
    width, height = get_screen_size()
    # 转换为绝对坐标（0-65535）
    abs_x = int(x * 65535 / (width - 1)) if width > 1 else 0
    abs_y = int(y * 65535 / (height - 1)) if height > 1 else 0

    if button == "left":
        down_flag = MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_LEFTUP
    elif button == "right":
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    elif button == "middle":
        down_flag = MOUSEEVENTF_MIDDLEDOWN
        up_flag = MOUSEEVENTF_MIDDLEUP
    else:
        raise ValueError(f"Unknown button: {button}")

    # 使用数组索引赋值，避免 ctypes 构造函数对 union/anonymous 字段解析出错
    inputs = (INPUT * 3)()
    inputs[0].type = INPUT_MOUSE
    inputs[0].mi = MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE, 0, None)
    inputs[1].type = INPUT_MOUSE
    inputs[1].mi = MOUSEINPUT(abs_x, abs_y, 0, down_flag, 0, None)
    inputs[2].type = INPUT_MOUSE
    inputs[2].mi = MOUSEINPUT(abs_x, abs_y, 0, up_flag, 0, None)

    user32.SendInput(3, inputs, ctypes.sizeof(INPUT))


def get_window_rect(hwnd):
    """获取窗口矩形 (left, top, right, bottom)"""
    rect = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def get_client_rect(hwnd):
    """获取客户区矩形 (left, top, right, bottom)，left/top 始终为 0,0"""
    rect = wintypes.RECT()
    if user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def client_to_screen(hwnd, cx, cy):
    """将窗口客户区坐标转换为屏幕坐标"""
    pt = wintypes.POINT()
    pt.x = cx
    pt.y = cy
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def screen_to_client(hwnd, sx, sy):
    """将屏幕坐标转换为窗口客户区坐标"""
    pt = wintypes.POINT()
    pt.x = sx
    pt.y = sy
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def find_window_by_title(title_substring):
    """模糊查找窗口标题，返回第一个匹配的 hwnd"""
    result = []

    def enum_callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if title_substring.lower() in buf.value.lower():
                    result.append((hwnd, buf.value))
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(EnumWindowsProc(enum_callback), 0)
    return result[0] if result else (None, None)


def get_foreground_window():
    """获取当前前台窗口句柄"""
    return user32.GetForegroundWindow()


def get_window_title(hwnd):
    """获取窗口标题"""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def force_foreground_window(hwnd):
    """强制将窗口置顶到前台，使用多种 Windows API 组合确保成功。"""
    if not hwnd or not is_window(hwnd):
        return
    # 1. 恢复窗口（如果最小化）
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    # 2. SwitchToThisWindow（内部 API，限制最少）
    try:
        user32.SwitchToThisWindow(hwnd, True)
    except AttributeError:
        pass
    # 3. SetForegroundWindow
    user32.SetForegroundWindow(hwnd)
    # 4. 临时设为 TOPMOST 再取消（强制刷新 Z-Order）
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    # 5. BringWindowToTop
    user32.BringWindowToTop(hwnd)


def is_window(hwnd):
    """判断句柄是否有效"""
    return bool(user32.IsWindow(hwnd))


# ----------------------- 点击任务 -----------------------

class ClickTask:
    """单个点击任务的配置"""

    def __init__(self, hwnd=None, window_title="", client_x=0, client_y=0,
                 target_time=None, countdown_ms=None,
                 interval_ms=100, repeat_count=1, button="left",
                 task_name="", active=True):
        self.hwnd = hwnd  # 窗口句柄
        self.window_title = window_title  # 窗口标题（用于重新查找）
        self.client_x = client_x  # 相对于窗口客户区的 X
        self.client_y = client_y  # 相对于窗口客户区的 Y
        self.target_time = target_time  # datetime 对象，绝对时间
        self.countdown_ms = countdown_ms  # 倒计时毫秒（与 target_time 二选一）
        self.interval_ms = interval_ms  # 点击间隔毫秒
        self.repeat_count = repeat_count  # 重复次数，0 表示无限
        self.button = button  # left/right/middle
        self.task_name = task_name
        self.active = active
        self._cancelled = False
        self._thread = None

    def to_dict(self):
        return {
            "window_title": self.window_title,
            "client_x": self.client_x,
            "client_y": self.client_y,
            "target_time": self.target_time.isoformat() if self.target_time else None,
            "countdown_ms": self.countdown_ms,
            "interval_ms": self.interval_ms,
            "repeat_count": self.repeat_count,
            "button": self.button,
            "task_name": self.task_name,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, d):
        t = cls()
        t.window_title = d.get("window_title", "")
        t.client_x = d.get("client_x", 0)
        t.client_y = d.get("client_y", 0)
        ts = d.get("target_time")
        t.target_time = datetime.fromisoformat(ts) if ts else None
        t.countdown_ms = d.get("countdown_ms")
        t.interval_ms = d.get("interval_ms", 100)
        t.repeat_count = d.get("repeat_count", 1)
        t.button = d.get("button", "left")
        t.task_name = d.get("task_name", "")
        t.active = d.get("active", True)
        return t

    def resolve_hwnd(self):
        """如果 hwnd 无效，尝试通过标题重新查找"""
        if self.hwnd and is_window(self.hwnd):
            return self.hwnd
        if self.window_title:
            hwnd, _ = find_window_by_title(self.window_title)
            if hwnd:
                self.hwnd = hwnd
                return hwnd
        return None

    def perform_click(self):
        """执行一次点击"""
        try:
            hwnd = self.resolve_hwnd()
            if not hwnd:
                return False, "窗口未找到"
            # 如果窗口最小化，先恢复并置顶，确保能接收点击
            force_foreground_window(hwnd)
            sx, sy = client_to_screen(hwnd, self.client_x, self.client_y)
            send_input_click(sx, sy, self.button)
            return True, f"点击 ({sx}, {sy})"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"点击异常: {e}"

    def _spin_wait_until(self, target_timestamp):
        """使用忙等待精确到毫秒的等待"""
        while time.perf_counter() < target_timestamp:
            if self._cancelled:
                return False
            # 在最后 5ms 内使用忙等待，其余时间用 sleep 降低 CPU
            remaining = target_timestamp - time.perf_counter()
            if remaining > 0.005:
                time.sleep(max(0, remaining - 0.005))
        return not self._cancelled

    def run(self, on_log=None):
        """在后台线程中运行任务"""
        self._cancelled = False
        self._thread = threading.Thread(target=self._run_impl, args=(on_log,), daemon=True)
        self._thread.start()

    def _run_impl(self, on_log):
        def log(msg):
            if on_log:
                on_log(f"[{self.task_name}] {msg}")

        try:
            # 计算目标时间戳（统一使用 time.perf_counter() 基准，避免与 datetime.timestamp() 混用）
            if self.countdown_ms is not None:
                target_ts = time.perf_counter() + self.countdown_ms / 1000.0
                log(f"倒计时 {self.countdown_ms}ms 后开始点击")
            elif self.target_time:
                delta = (self.target_time - datetime.now()).total_seconds()
                if delta <= 0:
                    log("目标时间已过，跳过任务")
                    return
                target_ts = time.perf_counter() + delta
                log(f"等待绝对时间 {self.target_time.strftime('%H:%M:%S.%f')[:-3]}")
            else:
                log("未设置时间")
                return

            # 第一阶段：粗等待（秒级，低 CPU）
            # 当剩余时间 > 1 秒时，每秒检查一次，避免单次 sleep 过长导致 OverflowError
            while True:
                remaining = target_ts - time.perf_counter()
                if remaining <= 1.0 or self._cancelled:
                    break
                sleep_time = min(1.0, remaining - 1.0)
                time.sleep(sleep_time)

            if self._cancelled:
                log("任务已取消")
                return

            # 第二阶段：高精度等待（最后 1 秒内用忙等待）
            remaining = target_ts - time.perf_counter()
            if remaining > 0:
                log(f">>> 任务即将在 {remaining:.1f} 秒内开始 <<<")
                if not self._spin_wait_until(target_ts):
                    log("任务已取消")
                    return

            count = 0
            while True:
                if self._cancelled:
                    log("任务已取消")
                    break
                ok, msg = self.perform_click()
                if not ok:
                    log(f"点击失败: {msg}")
                    break
                count += 1
                log(f"第 {count} 次点击完成")
                if self.repeat_count > 0 and count >= self.repeat_count:
                    log("达到设定次数，任务完成")
                    break
                # 等待间隔
                next_ts = time.perf_counter() + self.interval_ms / 1000.0
                if not self._spin_wait_until(next_ts):
                    log("任务已取消")
                    break
        except Exception as e:
            import traceback
            traceback.print_exc()
            log(f"任务执行异常: {e}")

    def stop(self):
        self._cancelled = True


# ----------------------- GUI -----------------------

class PositionPicker:
    """辅助类：让用户点击屏幕以选取相对于某窗口的坐标。
    启动后会将目标窗口置顶，然后监听下一次鼠标左键点击并自动记录坐标。
    """

    def __init__(self, master, on_picked):
        self.master = master
        self.on_picked = on_picked
        self._polling = False
        self._hwnd = None
        self._tip_window = None
        self._thread = None

    def start(self, hwnd=None):
        """启动取点模式。hwnd 为参考窗口，若为 None 则使用点击时的鼠标下方窗口"""
        self._hwnd = hwnd
        # 置顶目标窗口（如果已指定且有效）
        if hwnd and is_window(hwnd):
            force_foreground_window(hwnd)
        self._show_tip()
        self._polling = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _show_tip(self):
        self._tip_window = tk.Toplevel(self.master)
        self._tip_window.title("选取位置")
        self._tip_window.geometry("320x100")
        self._tip_window.attributes("-topmost", True)
        self._tip_window.resizable(False, False)
        self._tip_window.protocol("WM_DELETE_WINDOW", self._cancel)
        lbl = ttk.Label(
            self._tip_window,
            text="目标窗口已置顶\n请在目标窗口内点击想要的位置\n点击后自动记录坐标",
            justify="center"
        )
        lbl.pack(pady=5)
        ttk.Label(self._tip_window, text="按 ESC 取消", foreground="gray").pack()
        # 将提示窗口放到屏幕中央偏上
        self._tip_window.update_idletasks()
        sw = self._tip_window.winfo_screenwidth()
        sh = self._tip_window.winfo_screenheight()
        w = self._tip_window.winfo_width()
        h = self._tip_window.winfo_height()
        self._tip_window.geometry(f"+{(sw - w) // 2}+{(sh // 3)}")

    def _poll_loop(self):
        VK_LBUTTON = 0x01
        VK_ESCAPE = 0x1B

        # 先等待鼠标左键松开，避免把点击"选取位置"按钮的动作算进去
        while self._polling and (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000):
            time.sleep(0.01)

        waiting_down = True
        while self._polling:
            lbutton_down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            if waiting_down and lbutton_down:
                waiting_down = False
            if not waiting_down and not lbutton_down:
                # 左键抬起时记录位置
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                # 使用 after 回到主线程更新 UI
                self.master.after(0, lambda sx=pt.x, sy=pt.y: self._on_picked_at(sx, sy))
                self._polling = False
                break
            if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                self.master.after(0, self._cancel)
                self._polling = False
                break
            time.sleep(0.01)  # 10ms 轮询

    def _on_picked_at(self, sx, sy):
        try:
            self._cleanup()
            # 优先使用预设的 hwnd，若无效则取鼠标下方的窗口
            hwnd = self._hwnd
            if not hwnd or not is_window(hwnd):
                pt = wintypes.POINT()
                pt.x = sx
                pt.y = sy
                hwnd = user32.WindowFromPoint(pt)
            title = get_window_title(hwnd)
            cx, cy = screen_to_client(hwnd, sx, sy)
            if self.on_picked:
                self.on_picked(hwnd, title, sx, sy, cx, cy)
        except Exception as e:
            import traceback
            print(f"[PositionPicker] _on_picked_at error: {e}")
            traceback.print_exc()

    def _cancel(self):
        self._polling = False
        self._cleanup()

    def _cleanup(self):
        self._polling = False
        if self._tip_window:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None


class CaptureDialog:
    """捕获窗口对话框：显示当前所有可见窗口供选择"""

    def __init__(self, master, on_select):
        self.master = master
        self.on_select = on_select
        self.win = tk.Toplevel(master)
        self.win.title("选择目标窗口")
        self.win.geometry("500x400")
        self.win.transient(master)
        self.win.grab_set()

        ttk.Label(self.win, text="双击选择窗口，或点击刷新").pack(pady=5)
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=5)
        ttk.Button(btn_frame, text="刷新列表", command=self._refresh).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="使用前台窗口", command=self._use_foreground).pack(side="left", padx=2)

        columns = ("hwnd", "title")
        self.tree = ttk.Treeview(self.win, columns=columns, show="headings")
        self.tree.heading("hwnd", text="句柄")
        self.tree.heading("title", text="窗口标题")
        self.tree.column("hwnd", width=80, anchor="center")
        self.tree.column("title", width=350)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self._on_double)

        ttk.Button(self.win, text="取消", command=self.win.destroy).pack(pady=5)
        self._refresh()

    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        windows = []

        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                t = get_window_title(hwnd)
                if t.strip():
                    windows.append((hwnd, t))
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(cb), 0)
        for hwnd, t in windows:
            self.tree.insert("", "end", values=(f"0x{hwnd:X}", t))

    def _use_foreground(self):
        hwnd = get_foreground_window()
        if hwnd:
            self._select(hwnd, get_window_title(hwnd))

    def _on_double(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        try:
            hwnd = int(vals[0], 16)
        except Exception:
            return
        self._select(hwnd, vals[1])

    def _select(self, hwnd, title):
        self.win.destroy()
        if self.on_select:
            self.on_select(hwnd, title)


class TaskEditDialog:
    """添加/编辑任务对话框"""

    def __init__(self, master, task=None, on_save=None):
        self.master = master
        self.on_save = on_save
        self.result_task = None
        self.picker = PositionPicker(master, self._on_position_picked)

        self.win = tk.Toplevel(master)
        self.win.title("编辑点击任务" if task else "添加点击任务")
        self.win.geometry("450x500")
        self.win.transient(master)
        self.win.grab_set()

        frame = ttk.Frame(self.win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        row = 0
        # 任务名称
        ttk.Label(frame, text="任务名称:").grid(row=row, column=0, sticky="w", pady=3)
        self.var_name = tk.StringVar(value=task.task_name if task else "")
        ttk.Entry(frame, textvariable=self.var_name).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        # 窗口选择
        ttk.Label(frame, text="目标窗口:").grid(row=row, column=0, sticky="w", pady=3)
        win_frame = ttk.Frame(frame)
        win_frame.grid(row=row, column=1, sticky="ew", pady=3)
        self.var_win_title = tk.StringVar(value=task.window_title if task else "")
        self.ent_win = ttk.Entry(win_frame, textvariable=self.var_win_title, state="readonly")
        self.ent_win.pack(side="left", fill="x", expand=True)
        ttk.Button(win_frame, text="捕获", width=6, command=self._pick_window).pack(side="left", padx=2)
        ttk.Button(win_frame, text="刷新", width=6, command=self._refresh_hwnd).pack(side="left", padx=2)
        self._hwnd = task.hwnd if task else None
        row += 1

        # 坐标
        ttk.Label(frame, text="点击位置:").grid(row=row, column=0, sticky="w", pady=3)
        pos_frame = ttk.Frame(frame)
        pos_frame.grid(row=row, column=1, sticky="ew", pady=3)
        self.var_cx = tk.IntVar(value=task.client_x if task else 0)
        self.var_cy = tk.IntVar(value=task.client_y if task else 0)
        ttk.Label(pos_frame, text="X").pack(side="left")
        ttk.Spinbox(pos_frame, from_=0, to=9999, textvariable=self.var_cx, width=6).pack(side="left", padx=2)
        ttk.Label(pos_frame, text="Y").pack(side="left")
        ttk.Spinbox(pos_frame, from_=0, to=9999, textvariable=self.var_cy, width=6).pack(side="left", padx=2)
        ttk.Button(pos_frame, text="选取位置", command=self._pick_position).pack(side="left", padx=5)
        row += 1

        # 时间模式
        ttk.Label(frame, text="触发模式:").grid(row=row, column=0, sticky="w", pady=3)
        self.var_mode = tk.StringVar(value="absolute" if (task and task.target_time) else "countdown")
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=row, column=1, sticky="w", pady=3)
        ttk.Radiobutton(mode_frame, text="绝对时间", variable=self.var_mode, value="absolute", command=self._mode_changed).pack(side="left")
        ttk.Radiobutton(mode_frame, text="倒计时", variable=self.var_mode, value="countdown", command=self._mode_changed).pack(side="left")
        row += 1

        # 绝对时间
        self.frame_abs = ttk.Frame(frame)
        self.frame_abs.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)
        ttk.Label(self.frame_abs, text="目标时间 (HH:MM:SS.ms):").pack(side="left")
        self.var_time = tk.StringVar(value=task.target_time.strftime("%H:%M:%S.%f")[:-3] if task and task.target_time else "12:00:00.000")
        ttk.Entry(self.frame_abs, textvariable=self.var_time, width=16).pack(side="left", padx=3)
        ttk.Button(self.frame_abs, text="设为当前+1s", command=self._set_now_plus_1s).pack(side="left", padx=2)
        row += 1

        # 倒计时
        self.frame_count = ttk.Frame(frame)
        self.frame_count.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)
        ttk.Label(self.frame_count, text="倒计时 (毫秒):").pack(side="left")
        self.var_countdown = tk.IntVar(value=task.countdown_ms if task and task.countdown_ms else 5000)
        ttk.Spinbox(self.frame_count, from_=0, to=99999999, textvariable=self.var_countdown, width=10).pack(side="left", padx=3)
        row += 1

        # 点击配置
        ttk.Label(frame, text="点击配置:").grid(row=row, column=0, sticky="nw", pady=3)
        cfg_frame = ttk.Frame(frame)
        cfg_frame.grid(row=row, column=1, sticky="w", pady=3)
        ttk.Label(cfg_frame, text="间隔(ms)").grid(row=0, column=0, sticky="w")
        self.var_interval = tk.IntVar(value=task.interval_ms if task else 100)
        ttk.Spinbox(cfg_frame, from_=1, to=999999, textvariable=self.var_interval, width=8).grid(row=0, column=1, padx=3)
        ttk.Label(cfg_frame, text="次数(0=无限)").grid(row=0, column=2, sticky="w")
        self.var_repeat = tk.IntVar(value=task.repeat_count if task else 1)
        ttk.Spinbox(cfg_frame, from_=0, to=999999, textvariable=self.var_repeat, width=8).grid(row=0, column=3, padx=3)
        ttk.Label(cfg_frame, text="按键").grid(row=1, column=0, sticky="w", pady=5)
        self.var_button = tk.StringVar(value=task.button if task else "left")
        ttk.Combobox(cfg_frame, textvariable=self.var_button, values=["left", "right", "middle"], width=8, state="readonly").grid(row=1, column=1, pady=5)
        row += 1

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="取消", command=self.win.destroy).pack(side="left", padx=10)

        frame.columnconfigure(1, weight=1)
        self._mode_changed()

    def _mode_changed(self):
        if self.var_mode.get() == "absolute":
            self.frame_abs.grid()
            self.frame_count.grid_remove()
        else:
            self.frame_abs.grid_remove()
            self.frame_count.grid()

    def _set_now_plus_1s(self):
        t = datetime.now() + timedelta(seconds=1)
        self.var_time.set(t.strftime("%H:%M:%S.%f")[:-3])

    def _pick_window(self):
        CaptureDialog(self.master, self._on_window_selected)

    def _on_window_selected(self, hwnd, title):
        self._hwnd = hwnd
        self.var_win_title.set(title)

    def _refresh_hwnd(self):
        if not self.var_win_title.get():
            return
        hwnd, _ = find_window_by_title(self.var_win_title.get())
        if hwnd:
            self._hwnd = hwnd
            messagebox.showinfo("刷新", f"已重新定位窗口: {self.var_win_title.get()}")
        else:
            messagebox.showwarning("刷新", "未找到该窗口")

    def _pick_position(self):
        # 不再隐藏编辑对话框，直接启动取点；提示窗会置顶显示在目标窗口上方
        self.picker.start(self._hwnd)

    def _on_position_picked(self, hwnd, title, sx, sy, cx, cy):
        self._hwnd = hwnd
        self.var_win_title.set(title)
        self.var_cx.set(cx)
        self.var_cy.set(cy)
        self.win.lift()
        self.win.focus_force()
        messagebox.showinfo("位置已选取", f"屏幕: ({sx}, {sy})\n相对于窗口客户区: ({cx}, {cy})")

    def _save(self):
        try:
            name = self.var_name.get().strip() or "未命名任务"
            if self.var_mode.get() == "absolute":
                t_str = self.var_time.get().strip()
                # 解析时间
                now = datetime.now()
                try:
                    if "." in t_str:
                        t = datetime.strptime(t_str, "%H:%M:%S.%f")
                    else:
                        t = datetime.strptime(t_str, "%H:%M:%S")
                    target_time = now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=t.microsecond)
                    if target_time < now:
                        target_time += timedelta(days=1)
                except ValueError:
                    messagebox.showerror("格式错误", "时间格式应为 HH:MM:SS.ms，例如 12:00:00.100")
                    return
                countdown = None
            else:
                target_time = None
                countdown = self.var_countdown.get()

            task = ClickTask(
                hwnd=self._hwnd,
                window_title=self.var_win_title.get(),
                client_x=self.var_cx.get(),
                client_y=self.var_cy.get(),
                target_time=target_time,
                countdown_ms=countdown,
                interval_ms=self.var_interval.get(),
                repeat_count=self.var_repeat.get(),
                button=self.var_button.get(),
                task_name=name,
            )
            self.result_task = task
            if self.on_save:
                self.on_save(task)
            self.win.destroy()
        except Exception as e:
            messagebox.showerror("错误", str(e))


class PrecisionClickerApp:
    """主应用程序"""

    CONFIG_FILE = "precision_clicker_config.json"

    def __init__(self, master):
        self.master = master
        master.title("Precision Clicker - 精确鼠标点击")
        master.geometry("800x550")
        self.tasks = []
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        # 顶部工具栏
        toolbar = ttk.Frame(self.master)
        toolbar.pack(fill="x", padx=5, pady=5)
        ttk.Button(toolbar, text="+ 添加任务", command=self._add_task).pack(side="left", padx=2)
        ttk.Button(toolbar, text="编辑", command=self._edit_task).pack(side="left", padx=2)
        ttk.Button(toolbar, text="删除", command=self._delete_task).pack(side="left", padx=2)
        ttk.Button(toolbar, text="启动选中", command=self._start_selected).pack(side="left", padx=2)
        ttk.Button(toolbar, text="停止选中", command=self._stop_selected).pack(side="left", padx=2)
        ttk.Button(toolbar, text="启动全部", command=self._start_all).pack(side="left", padx=2)
        ttk.Button(toolbar, text="停止全部", command=self._stop_all).pack(side="left", padx=2)
        ttk.Button(toolbar, text="保存配置", command=self._save_config).pack(side="left", padx=2)
        ttk.Button(toolbar, text="加载配置", command=self._load_config).pack(side="left", padx=2)
        # 当前时间显示
        self.lbl_clock = ttk.Label(toolbar, text="", font=("Consolas", 11, "bold"))
        self.lbl_clock.pack(side="right", padx=10)
        self._update_clock()
        # 快捷键
        self.master.bind_all("<F5>", lambda e: self._start_all())
        self.master.bind_all("<F6>", lambda e: self._stop_all())

        # 任务列表
        columns = ("name", "window", "pos", "trigger", "cfg", "status")
        self.tree = ttk.Treeview(self.master, columns=columns, show="headings")
        self.tree.heading("name", text="任务名称")
        self.tree.heading("window", text="目标窗口")
        self.tree.heading("pos", text="位置(相对)")
        self.tree.heading("trigger", text="触发时间")
        self.tree.heading("cfg", text="点击配置")
        self.tree.heading("status", text="状态")
        self.tree.column("name", width=120)
        self.tree.column("window", width=180)
        self.tree.column("pos", width=80, anchor="center")
        self.tree.column("trigger", width=120, anchor="center")
        self.tree.column("cfg", width=100, anchor="center")
        self.tree.column("status", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", lambda e: self._edit_task())

        # 日志区域
        ttk.Label(self.master, text="运行日志:").pack(anchor="w", padx=5)
        log_frame = ttk.Frame(self.master)
        log_frame.pack(fill="both", expand=False, padx=5, pady=5)
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _update_clock(self):
        self.lbl_clock.config(text=datetime.now().strftime("%H:%M:%S"))
        self.master.after(1000, self._update_clock)

    def _log(self, msg):
        self.log_text.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, t in enumerate(self.tasks):
            pos = f"({t.client_x}, {t.client_y})"
            if t.countdown_ms is not None:
                trigger = f"倒计时 {t.countdown_ms}ms"
            elif t.target_time:
                trigger = t.target_time.strftime("%H:%M:%S.%f")[:-3]
            else:
                trigger = "未设置"
            cfg = f"{t.button}/{t.interval_ms}ms/{'∞' if t.repeat_count==0 else t.repeat_count}次"
            status = "就绪" if t.active else "禁用"
            self.tree.insert("", "end", iid=str(i), values=(t.task_name, t.window_title or "未指定", pos, trigger, cfg, status))

    def _get_selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _add_task(self):
        def on_save(task):
            self.tasks.append(task)
            self._refresh_list()
            self._log(f"添加任务: {task.task_name}")
        TaskEditDialog(self.master, task=None, on_save=on_save)

    def _edit_task(self):
        idx = self._get_selected_index()
        if idx is None:
            messagebox.showwarning("提示", "请先选择一个任务")
            return
        old = self.tasks[idx]

        def on_save(task):
            self.tasks[idx] = task
            self._refresh_list()
            self._log(f"编辑任务: {task.task_name}")
        TaskEditDialog(self.master, task=old, on_save=on_save)

    def _delete_task(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        t = self.tasks.pop(idx)
        t.stop()
        self._refresh_list()
        self._log(f"删除任务: {t.task_name}")

    def _start_selected(self):
        idx = self._get_selected_index()
        if idx is None:
            messagebox.showwarning("提示", "请先选择一个任务")
            return
        self._start_task(idx)

    def _start_task(self, idx):
        t = self.tasks[idx]
        t.stop()
        t.run(on_log=self._log)
        self._log(f"启动任务: {t.task_name}")

    def _stop_selected(self):
        idx = self._get_selected_index()
        if idx is None:
            return
        self.tasks[idx].stop()
        self._log(f"停止任务: {self.tasks[idx].task_name}")

    def _start_all(self):
        for i in range(len(self.tasks)):
            self._start_task(i)

    def _stop_all(self):
        for t in self.tasks:
            t.stop()
        self._log("停止所有任务")

    def _save_config(self):
        try:
            data = [t.to_dict() for t in self.tasks]
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CONFIG_FILE)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._log(f"配置已保存: {path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _load_config(self):
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CONFIG_FILE)
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.tasks = [ClickTask.from_dict(d) for d in data]
            # 尝试重新解析 hwnd
            for t in self.tasks:
                t.resolve_hwnd()
            self._refresh_list()
            self._log(f"配置已加载: {path} ({len(self.tasks)} 个任务)")
        except Exception as e:
            self._log(f"加载配置失败: {e}")


def main():
    root = tk.Tk()
    app = PrecisionClickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
