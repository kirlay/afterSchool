# -*- coding: utf-8 -*-
"""主窗口、设置对话框与帮助窗口。"""

import datetime
import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox

from . import hotkey
from . import layout
from . import schedule
from . import settings as st
from . import winutil

BG = "black"
COLOR_PENDING = "green"
COLOR_DONE = "red"
COLOR_TITLE = "#f26522"
FONT_HINT = ("黑体", 12)

HIDDEN_CAP_MS = 30 * 60 * 1000
EPSILON_MS = 50
POLL_INTERVAL_MS = 150
POLL_FLAG_EVERY = 7
STARTUP_SHOW_MS = 3000

HELP_TEXT = """樱花校区放学情况  v2.3.0

一、班号怎么输入
    101 = 一年级 1 班，102 = 一年级 2 班，以此类推；
    二年级是 201、202……，班级数以设置里的为准。
    窗口出现时光标会自动停在输入框，直接输入即可。
    输入 101 后按回车，一1班变红并显示“放学”。

二、输错了怎么撤销
    输入 -101 后按回车，一1班恢复绿色“未放学”。
    （前面加一个减号，数字不变）

三、一次全部复位
    输入 000 后按回车，确认后所有班级都变回“未放学”。
    另外每天上午 9:00（时间可在设置里改，也可以关掉）会自动复位一次。

四、打开设置（快捷键 {hotkey}）
    默认 F9；也可以是 F10、F11、F12，或 Ctrl+Alt+F9 这类组合，
    在设置里可以改。窗口最小化到任务栏时按同样有效。
    校名：显示在窗口顶部（默认“宁波市四眼碶小学樱花校区”）；
    窗口宽度/高度：像素，默认 548×416；
    字号：班级文字大小（磅），默认 16；行距：行与行之间像素，默认 44；
    字号调大时，窗口宽度/高度和行距也要一起调大，否则会挤在一起；
    班级数：每个年级 0–12 个班，0 表示没有这个年级；
    显示时段：窗口在这个时间段内显示，其余时间最小化到任务栏；
    每日复位：每天到这个时间自动把所有班级恢复为未放学；
    校准间隔：默认 120 秒，越大越省电，到点仍会准时切换；
    还可以设置窗口置顶、隐藏时自动复位、窗口位置复位。

五、打开本帮助（快捷键 F1）
    按 F1 随时打开，窗口最小化时也能按。

六、退出程序
    按 {hotkey} 打开设置，点右下角的“退出程序”；也可以点窗口右上角的 ×。

七、显示时段与任务栏
    到开始时间窗口自动出现（标题栏默认在屏幕外，任务栏里能看到“放学情况”）；
    到结束时间自动最小化到任务栏，不是消失；
    点任务栏上的“放学情况”可以随时还原查看；
    本程序不会一直压在最上面，点其它大屏软件，它会到前面来。

八、替换图标
    把新的 xb.ico 覆盖到程序所在文件夹，重启程序即可；
    屏幕左上角的 logo 由同目录的 logo.png 决定。

九、设置文件
    程序文件夹里的 settings.json；
    更新程序时保留这个文件，设置就不会丢。

十、其他
    宁波市四眼碶小学樱花校区
    软件设计：严科磊    联系电话：13777145451
"""


class Application(object):
    def __init__(self, root, cfg, base_dir=None, options=None):
        self.root = root
        self.cfg = cfg
        self.base_dir = base_dir or st.app_base_dir()
        self.options = options or {}
        self._log_path = os.path.join(st.data_dir(), st.LOG_NAME)
        self._flag_path = os.path.join(st.data_dir(), st.FLAG_NAME)

        self.labels = []
        self.label_by_code = {}
        self._visible = False
        self._drag = None
        self._settings_dialog = None
        self._help_window = None
        self._tick_job = None
        self._poll_count = 0
        self._next_reset = None
        self._offset_seconds = self._parse_now_offset(self.options.get("now"))
        self._logo_image = None

        self._setup_window()
        self._setup_widgets()
        self._settings_hotkey = hotkey.HotkeyPoller(self.cfg["hotkey"])

    # ------------------------------------------------------------------ 窗口

    def _setup_window(self):
        root = self.root
        root.title("放学情况（樱花校区）")
        root.configure(bg=BG)
        root.resizable(width=False, height=False)
        self._hide_titlebar = self._resolve_hide_titlebar()
        if self._hide_titlebar:
            root.overrideredirect(True)
        root.withdraw()
        self._apply_topmost()
        self._load_icon()

        self._logo_image = self._load_logo()
        if self._logo_image is not None:
            self.logo_label = tk.Label(root, image=self._logo_image, bg=BG, bd=0)
            self.logo_label.place(x=40, y=8)
            for event_name in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"):
                self.logo_label.bind(event_name, getattr(self, "_drag_" + _EVENT_SUFFIX[event_name]))
            title_x = 140
        else:
            self.logo_label = None
            title_x = 40

        self.title_label = tk.Label(
            root,
            text=layout.title_text(self.cfg["school_name"]),
            font=self._fonts()[0],
            bg=BG,
            fg=COLOR_TITLE,
            justify="center",
        )
        self.title_label.place(x=title_x, y=12)
        for event_name in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"):
            self.title_label.bind(event_name, getattr(self, "_drag_" + _EVENT_SUFFIX[event_name]))

    def _load_icon(self):
        path = os.path.join(self.base_dir, "xb.ico")
        if not os.path.exists(path):
            winutil.write_log(self._log_path, "找不到窗口图标：%s" % path)
            return None
        try:
            self.root.iconbitmap(default=path)
        except tk.TclError as exc:
            winutil.write_log(self._log_path, "设置窗口图标失败：%s" % exc)
            return None
        return path

    def _load_logo(self):
        path = os.path.join(self.base_dir, "logo.png")
        if not os.path.exists(path):
            winutil.write_log(self._log_path, "找不到屏幕 logo：%s" % path)
            return None
        try:
            return tk.PhotoImage(file=path)
        except tk.TclError as exc:
            winutil.write_log(self._log_path, "加载屏幕 logo 失败：%s" % exc)
            return None

    def _apply_topmost(self):
        try:
            self.root.attributes("-topmost", bool(self.cfg["topmost"]))
        except tk.TclError:
            pass

    def _fonts(self):
        """当前字号设置对应的 (标题, 班级, 提示) 三种字体。"""
        size = int(self.cfg["layout"]["font_size"])
        return (
            ("黑体", layout.title_font_size(size)),
            ("黑体", size),
            ("黑体", layout.hint_font_size(size)),
        )

    def _setup_widgets(self):
        hint_font = self._fonts()[2]
        self.counter_label = tk.Label(self.root, text="读取班级编号：", font=hint_font, bg=BG, fg=COLOR_PENDING)
        self.entry_var = tk.StringVar(self.root)
        self.entry = tk.Entry(self.root, textvariable=self.entry_var, width=15, font=hint_font, justify="center")
        self.entry.bind("<Return>", self.on_enter)
        self.root.bind("<Button-1>", self._on_click)
        self.root.bind("<FocusIn>", self._on_focus_in)

    # ------------------------------------------------------------------ 布局

    def _layout(self):
        width = int(self.cfg["layout"]["width"])
        height = int(self.cfg["layout"]["height"])
        # 配置里存的是"客户区"左上角：默认 0,0 时客户区贴屏幕左上角，
        # 标题栏和边框被挤到屏幕外（任务栏里仍然正常显示）。
        # --decorated 用于排查问题：按"窗口左上角"摆放，标题栏可见。
        client_x = int(self.cfg["window"].get("x", 0))
        client_y = int(self.cfg["window"].get("y", 0))
        if self.options.get("decorated"):
            left = top = 0
        else:
            left, top = self._frame_offsets()
        self.root.geometry("%dx%d+%d+%d" % (width, height, client_x - left, client_y - top))
        return width, height

    def _frame_offsets(self):
        """边框/标题栏占掉的像素：能实测就实测，否则用系统度量。"""
        if self._hide_titlebar:
            return 0, 0
        try:
            if self.root.winfo_ismapped():
                left = self.root.winfo_rootx() - self.root.winfo_x()
                top = self.root.winfo_rooty() - self.root.winfo_y()
                if left >= 0 and top > 0:
                    return left, top
        except tk.TclError:
            pass
        return winutil.frame_border_width(), winutil.caption_height()

    def _align_after_show(self):
        """窗口真正显示后，按实测边框把客户区对齐到配置的位置。"""
        if self._hide_titlebar or self.options.get("decorated"):
            return
        try:
            if not self.root.winfo_ismapped():
                return
        except tk.TclError:
            return
        client_x = int(self.cfg["window"].get("x", 0))
        client_y = int(self.cfg["window"].get("y", 0))
        left, top = self._frame_offsets()
        if self.root.winfo_rootx() != client_x or self.root.winfo_rooty() != client_y:
            try:
                self.root.geometry("+%d+%d" % (client_x - left, client_y - top))
            except tk.TclError:
                pass

    def _rebuild(self):
        for _code, label, _grade, _no in self.labels:
            label.destroy()
        self.labels = []
        self.label_by_code = {}

        title_font, class_font, hint_font = self._fonts()
        self.title_label.config(
            text=layout.title_text(self.cfg["school_name"]),
            font=title_font,
        )
        self.counter_label.config(font=hint_font)
        self.entry.config(font=hint_font)

        classes = self.cfg["classes"]
        columns = max(classes) if classes else 1
        font_size = int(self.cfg["layout"]["font_size"])
        row_spacing = int(self.cfg["layout"]["row_spacing"])
        width, height = self._layout()

        row = 0
        for grade_index, count in enumerate(classes):
            if count <= 0:
                continue
            for class_no in range(1, int(count) + 1):
                code = "%d0%d" % (grade_index + 1, class_no)
                label = tk.Label(
                    self.root,
                    text=self._class_text(grade_index, class_no, False),
                    font=class_font,
                    bg=BG,
                    fg=COLOR_PENDING,
                )
                label.place(
                    x=layout.column_x(width, columns, class_no),
                    y=layout.row_y(font_size, row_spacing, row),
                )
                self.labels.append((code, label, grade_index, class_no))
                self.label_by_code[code] = (label, grade_index, class_no)
            row += 1

        entry_y = layout.entry_y(height, font_size)
        self.counter_label.place(x=20, y=entry_y + 4)
        self.root.update_idletasks()
        entry_x = 20 + self.counter_label.winfo_reqwidth() + 12
        self.entry.place(x=entry_x, y=entry_y)

    @staticmethod
    def _class_text(grade_index, class_no, done):
        text = "%s%d班" % (st.GRADE_NAMES[grade_index], class_no)
        return text + "放学" if done else text

    def _set_done(self, code, done):
        label, grade_index, class_no = self.label_by_code[code]
        label.config(text=self._class_text(grade_index, class_no, done), fg=COLOR_DONE if done else COLOR_PENDING)

    def reset_all(self):
        for code in self.label_by_code:
            self._set_done(code, False)
        self.entry_var.set("")

    # ------------------------------------------------------------------ 输入

    @staticmethod
    def _normalize(text):
        table = {}
        for index in range(10):
            table[ord("０") + index] = ord("0") + index
        table[ord("－")] = ord("-")
        return text.translate(table).replace(" ", "").replace("\u3000", "").strip()

    def _bell(self):
        try:
            self.root.bell()
        except tk.TclError:
            pass

    def on_enter(self, event=None):
        code = self._normalize(self.entry.get())
        self.entry_var.set("")
        if not code:
            return "break"

        if code == "000":
            if messagebox.askyesno("确认操作", "是否将所有班级设置成“未放学”的状态？", parent=self._dialog_parent()):
                self.reset_all()
            self.entry.focus_set()
            return "break"

        if code.startswith("-"):
            target = code[1:]
            if target in self.label_by_code:
                self._set_done(target, False)
            else:
                self._bell()
        elif code in self.label_by_code:
            self._set_done(code, True)
        else:
            self._bell()

        self.entry.focus_set()
        return "break"

    def _on_click(self, event=None):
        if self._dialog_open():
            return
        if self._visible:
            self.entry.focus_set()

    # ------------------------------------------------------------------ 显示

    def _dialog_open(self):
        return self._window_alive(self._settings_dialog) or self._window_alive(self._help_window)

    @staticmethod
    def _window_alive(window):
        return window is not None and window.winfo_exists()

    def _dialog_parent(self):
        if self._window_alive(self._settings_dialog):
            return self._settings_dialog
        return self.root

    def show_window(self):
        self._visible = True
        self.root.deiconify()
        self._apply_topmost()
        winutil.bring_to_front(self.root)
        self._focus_entry()
        # Win7 上窗口映射/前台切换有延迟，多补几次
        self.root.after(80, self._align_after_show)
        self.root.after(150, self._focus_entry)
        self.root.after(600, self._focus_entry)

    def hide_window(self):
        self._visible = False
        if self.cfg["reset_on_hide"]:
            self.reset_all()
        self.entry_var.set("")
        if self._hide_titlebar:
            self.root.withdraw()
        else:
            # 有标题栏时最小化到任务栏，老师一眼能看到程序在运行
            self.root.iconify()

    def _resolve_hide_titlebar(self):
        hide = bool(self.cfg["hide_titlebar"])
        if self.options.get("decorated"):
            hide = False
        if self.options.get("no_titlebar"):
            hide = True
        return hide

    def _focus_entry(self):
        if not self._visible or self._dialog_open():
            return
        try:
            if not self.root.winfo_exists():
                return
            self.entry.focus_force()
            self.entry.icursor("end")
        except tk.TclError:
            pass

    def _on_focus_in(self, event):
        if event.widget is self.root and self._visible and not self._dialog_open():
            self.entry.focus_set()

    # ------------------------------------------------------------------ 定时

    def _parse_now_offset(self, text):
        if not text:
            return 0
        try:
            fake = schedule.parse_hhmm(text)
        except ValueError:
            winutil.write_log(self._log_path, "--now 参数不正确：%s" % text)
            return 0
        fake_dt = datetime.datetime.combine(datetime.date.today(), fake)
        return (fake_dt - datetime.datetime.now()).total_seconds()

    def _now(self):
        return datetime.datetime.now() + datetime.timedelta(seconds=self._offset_seconds)

    def _begin_end(self):
        show = self.cfg["show"]
        return schedule.parse_hhmm(show["begin"]), schedule.parse_hhmm(show["end"])

    def _delay_ms(self, now, begin, end):
        if self.options.get("force_show"):
            return 60000
        interval = int(self.cfg["check_interval_seconds"]) * 1000
        reset_time = self._reset_time()
        extra = (reset_time,) if reset_time is not None else ()
        return schedule.next_delay_ms(now, begin, end, interval, HIDDEN_CAP_MS, extra)

    def _reset_time(self):
        daily = self.cfg.get("daily_reset") or {}
        if not daily.get("enabled", True):
            return None
        try:
            return schedule.parse_hhmm(daily.get("time", "09:00"))
        except ValueError:
            return None

    def _schedule_next_reset(self, now):
        moment = self._reset_time()
        self._next_reset = schedule.next_occurrence(now, moment) if moment is not None else None

    def _maybe_daily_reset(self, now):
        if self._next_reset is None or now < self._next_reset:
            return
        self.reset_all()
        self._schedule_next_reset(now)

    def _schedule_tick(self, delay_ms):
        if self._tick_job is not None:
            try:
                self.root.after_cancel(self._tick_job)
            except Exception:
                pass
        self._tick_job = self.root.after(max(1, int(delay_ms) + EPSILON_MS), self.tick)

    def tick(self):
        self._tick_job = None
        now = self._now()
        self._maybe_daily_reset(now)
        if self._dialog_open():
            # 弹窗打开期间不要突然把主窗口藏掉
            self._schedule_tick(60000)
            return
        begin, end = self._begin_end()
        visible = self.options.get("force_show") or schedule.is_visible(now, begin, end)
        if visible and not self._visible:
            self.show_window()
        elif not visible and self._visible:
            self.hide_window()
        self._schedule_tick(self._delay_ms(now, begin, end))

    # ------------------------------------------------------------------ 快捷键

    def _setup_hotkeys(self):
        self._help_hotkey = hotkey.HotkeyPoller("F1")

    def _poll(self):
        try:
            if self._help_hotkey.triggered():
                self.show_help()
            if self._settings_hotkey.triggered():
                self.open_settings()
        except Exception:
            self.report_exception(*sys.exc_info())
        self._poll_count += 1
        if self._poll_count % POLL_FLAG_EVERY == 0:
            self._check_flag()
        self.root.after(POLL_INTERVAL_MS, self._poll)

    def _check_flag(self):
        if not os.path.exists(self._flag_path):
            return
        try:
            os.remove(self._flag_path)
        except OSError:
            return
        self.open_settings()

    # ------------------------------------------------------------------ 弹窗

    def open_settings(self):
        if self._window_alive(self._settings_dialog):
            self._settings_dialog.lift()
            self._settings_dialog.focus_force()
            return
        self._reveal_for_dialog()
        self._settings_dialog = SettingsDialog(self)

    def show_help(self):
        if self._window_alive(self._help_window):
            self._help_window.lift()
            self._help_window.focus_force()
            return
        self._reveal_for_dialog()
        self._help_window = HelpWindow(self)

    def _reveal_for_dialog(self):
        # 主窗口被隐藏/最小化时先还原；已经在显示的话也抬一下，别让弹窗藏在别的软件后面
        if not self._visible:
            self.show_window()
        else:
            try:
                self.root.lift()
            except tk.TclError:
                pass

    def on_dialog_closed(self):
        self.root.after(200, self.tick)

    # ------------------------------------------------------------------ 设置

    def apply_settings(self, new_cfg):
        self.cfg = st.save(new_cfg)
        self._rebuild()
        self._apply_topmost()
        try:
            self._settings_hotkey = hotkey.HotkeyPoller(self.cfg["hotkey"])
        except hotkey.HotkeyError:
            pass

        now = self._now()
        begin, end = self._begin_end()
        visible = self.options.get("force_show") or schedule.is_visible(now, begin, end)
        if visible and not self._visible:
            self.show_window()
        elif not visible and self._visible:
            self.hide_window()
        self._schedule_next_reset(now)
        self._schedule_tick(self._delay_ms(now, begin, end))

    def move_to_home(self):
        self.cfg["window"] = {"x": 0, "y": 0}
        self._layout()
        try:
            st.save(self.cfg)
        except Exception as exc:
            winutil.write_log(self._log_path, "保存窗口位置失败：%s" % exc)

    def quit(self):
        if not messagebox.askyesno("退出", "确定要退出“放学情况”吗？", parent=self._dialog_parent()):
            return
        try:
            st.save(self.cfg)
        except Exception as exc:
            winutil.write_log(self._log_path, "退出前保存设置失败：%s" % exc)
        self.root.destroy()

    # ------------------------------------------------------------------ 拖动

    def _drag_start(self, event):
        self._drag = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag_move(self, event):
        if not self._drag:
            return
        delta_x = event.x_root - self._drag[0]
        delta_y = event.y_root - self._drag[1]
        self.root.geometry("+%d+%d" % (self._drag[2] + delta_x, self._drag[3] + delta_y))

    def _drag_end(self, event):
        if not self._drag:
            return
        self._drag = None
        # 保存"客户区"位置，重启后标题栏依旧在屏幕外的相对位置
        self.cfg["window"] = {"x": self.root.winfo_rootx(), "y": self.root.winfo_rooty()}
        try:
            st.save(self.cfg)
        except Exception as exc:
            winutil.write_log(self._log_path, "保存窗口位置失败：%s" % exc)

    # ------------------------------------------------------------------ 启动

    def report_exception(self, exc_type, exc_value, tb):
        winutil.write_log(self._log_path, "".join(traceback.format_exception(exc_type, exc_value, tb)))

    def start(self):
        self._rebuild()
        self._setup_hotkeys()
        now = self._now()
        self._schedule_next_reset(now)
        begin, end = self._begin_end()
        visible = self.options.get("force_show") or schedule.is_visible(now, begin, end)
        self.show_window()
        if visible:
            self._schedule_tick(self._delay_ms(now, begin, end))
        else:
            self._schedule_tick(STARTUP_SHOW_MS)
        self._poll()
        if self.options.get("settings"):
            self.root.after(100, self.open_settings)


_EVENT_SUFFIX = {
    "<ButtonPress-1>": "start",
    "<B1-Motion>": "move",
    "<ButtonRelease-1>": "end",
}


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        tk.Toplevel.__init__(self, app.root)
        self.app = app
        self.title("设置 - 放学情况")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(app.root)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self._build()
        self._center()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_force()

    def _hint(self, parent, text):
        return tk.Label(parent, text=text, font=FONT_HINT, bg=BG, fg=COLOR_PENDING)

    def _entry(self, parent, variable, width=8):
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            justify="center",
            font=FONT_HINT,
            bg="white",
            relief="flat",
        )

    def _button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_HINT,
            bg="#222222",
            fg="white",
            activebackground="#444444",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=2,
        )

    def _build(self):
        display_frame = tk.Frame(self, bg=BG, padx=16, pady=12)
        display_frame.pack(fill="x")
        self._hint(display_frame, "显示").grid(row=0, column=0, columnspan=8, sticky="w", pady=(0, 6))

        self._hint(display_frame, "校名").grid(row=1, column=0, sticky="e")
        self.school_var = tk.StringVar(value=self.app.cfg.get("school_name", ""))
        self._entry(display_frame, self.school_var, width=30).grid(
            row=1, column=1, columnspan=5, padx=(4, 0), sticky="w"
        )

        layout_cfg = self.app.cfg["layout"]
        self.layout_vars = {}
        for column, (key, label, width) in enumerate(
            (
                ("width", "窗口宽度(像素)", 6),
                ("height", "窗口高度(像素)", 6),
                ("font_size", "字号(磅)", 5),
                ("row_spacing", "行距(像素)", 6),
            )
        ):
            self._hint(display_frame, label).grid(row=2, column=column * 2, sticky="e", pady=(8, 0), padx=(0, 4))
            variable = tk.StringVar(value=str(layout_cfg[key]))
            self._entry(display_frame, variable, width=width).grid(
                row=2, column=column * 2 + 1, sticky="w", pady=(8, 0)
            )
            self.layout_vars[key] = variable

        self._hint(display_frame, "字号调大时，窗口宽度/高度和行距也要一起调大").grid(
            row=3, column=0, columnspan=8, sticky="w", pady=(6, 0)
        )

        class_frame = tk.Frame(self, bg=BG, padx=16, pady=12)
        class_frame.pack(fill="x")
        title = self._hint(class_frame, "班级数（0 表示该年级没有班级）")
        title.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 6))

        self.class_vars = []
        for index, name in enumerate(st.GRADE_NAMES):
            row = 1 + index // 3
            column = (index % 3) * 2
            self._hint(class_frame, "%s年级" % name).grid(row=row, column=column, sticky="e", padx=(0, 4), pady=2)
            variable = tk.StringVar(value=str(self.app.cfg["classes"][index]))
            tk.Spinbox(
                class_frame,
                from_=0,
                to=12,
                width=4,
                textvariable=variable,
                font=FONT_HINT,
                justify="center",
            ).grid(row=row, column=column + 1, sticky="w", padx=(0, 14), pady=2)
            self.class_vars.append(variable)

        time_frame = tk.Frame(self, bg=BG, padx=16, pady=4)
        time_frame.pack(fill="x")
        self._hint(time_frame, "显示时段（开始要早于结束）").grid(row=0, column=0, columnspan=6, sticky="w", pady=(4, 4))

        self._hint(time_frame, "开始").grid(row=1, column=0, sticky="e")
        self.begin_var = tk.StringVar(value=self.app.cfg["show"]["begin"])
        self._entry(time_frame, self.begin_var).grid(row=1, column=1, padx=(4, 16), sticky="w")

        self._hint(time_frame, "结束").grid(row=1, column=2, sticky="e")
        self.end_var = tk.StringVar(value=self.app.cfg["show"]["end"])
        self._entry(time_frame, self.end_var).grid(row=1, column=3, padx=(4, 0), sticky="w")

        self._hint(time_frame, "校准间隔(秒)").grid(row=2, column=0, sticky="e", pady=(8, 0))
        self.interval_var = tk.StringVar(value=str(self.app.cfg["check_interval_seconds"]))
        self._entry(time_frame, self.interval_var).grid(row=2, column=1, padx=(4, 16), pady=(8, 0), sticky="w")
        self._hint(time_frame, "10–3600，越大越省电，到点仍准时").grid(
            row=2, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )

        daily = self.app.cfg.get("daily_reset") or {}
        self.daily_reset_var = tk.BooleanVar(value=bool(daily.get("enabled", True)))
        tk.Checkbutton(
            time_frame,
            text="每天定时复位",
            variable=self.daily_reset_var,
            font=FONT_HINT,
            bg=BG,
            fg=COLOR_PENDING,
            activebackground=BG,
            activeforeground=COLOR_PENDING,
            selectcolor=BG,
            highlightthickness=0,
            bd=0,
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.reset_time_var = tk.StringVar(value=str(daily.get("time", "09:00")))
        self._entry(time_frame, self.reset_time_var).grid(row=3, column=1, padx=(4, 16), pady=(8, 0), sticky="w")
        self._hint(time_frame, "每天到这个时间把所有班级恢复为未放学").grid(
            row=3, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )

        extra_frame = tk.Frame(self, bg=BG, padx=16, pady=4)
        extra_frame.pack(fill="x")
        self._hint(extra_frame, "设置快捷键").grid(row=0, column=0, sticky="e", pady=(4, 0))
        self.hotkey_var = tk.StringVar(value=self.app.cfg["hotkey"])
        self._entry(extra_frame, self.hotkey_var, width=12).grid(row=0, column=1, padx=(4, 12), pady=(4, 0), sticky="w")
        self._hint(extra_frame, "推荐：" + " / ".join(hotkey.suggestions())).grid(
            row=0, column=2, sticky="w", pady=(4, 0)
        )

        self.topmost_var = tk.BooleanVar(value=self.app.cfg["topmost"])
        tk.Checkbutton(
            extra_frame,
            text="窗口置顶（一般不用勾）",
            variable=self.topmost_var,
            font=FONT_HINT,
            bg=BG,
            fg=COLOR_PENDING,
            activebackground=BG,
            activeforeground=COLOR_PENDING,
            selectcolor=BG,
            highlightthickness=0,
            bd=0,
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))

        self.reset_var = tk.BooleanVar(value=self.app.cfg["reset_on_hide"])
        tk.Checkbutton(
            extra_frame,
            text="隐藏时自动复位",
            variable=self.reset_var,
            font=FONT_HINT,
            bg=BG,
            fg=COLOR_PENDING,
            activebackground=BG,
            activeforeground=COLOR_PENDING,
            selectcolor=BG,
            highlightthickness=0,
            bd=0,
        ).grid(row=1, column=2, sticky="w", pady=(4, 0))

        button_frame = tk.Frame(self, bg=BG, padx=16, pady=10)
        button_frame.pack(fill="x")
        self._button(button_frame, "保存并应用", self.save).pack(side="left")
        self._button(button_frame, "取消", self.cancel).pack(side="left", padx=8)
        self._button(button_frame, "窗口位置复位", self.app.move_to_home).pack(side="left")
        self._button(button_frame, "退出程序", self.app.quit).pack(side="right")

    def _center(self):
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry("+%d+%d" % (x, y))

    @staticmethod
    def _int_value(variable, name):
        text = variable.get().strip()
        if not text:
            raise st.SettingsError("%s不能为空" % name)
        try:
            return int(text)
        except ValueError:
            raise st.SettingsError("%s必须是整数" % name)

    def save(self):
        try:
            candidate = {
                "version": self.app.cfg.get("version", st.SETTINGS_VERSION),
                "school_name": self.school_var.get(),
                "classes": [self._int_value(variable, "班级数") for variable in self.class_vars],
                "show": {"begin": self.begin_var.get(), "end": self.end_var.get()},
                "check_interval_seconds": self._int_value(self.interval_var, "校准间隔"),
                "daily_reset": {
                    "enabled": bool(self.daily_reset_var.get()),
                    "time": self.reset_time_var.get().strip() or "09:00",
                },
                "layout": {
                    "width": self._int_value(self.layout_vars["width"], "窗口宽度"),
                    "height": self._int_value(self.layout_vars["height"], "窗口高度"),
                    "font_size": self._int_value(self.layout_vars["font_size"], "字号"),
                    "row_spacing": self._int_value(self.layout_vars["row_spacing"], "行距"),
                },
                "hide_titlebar": self.app.cfg["hide_titlebar"],
                "topmost": bool(self.topmost_var.get()),
                "reset_on_hide": bool(self.reset_var.get()),
                "hotkey": self.hotkey_var.get(),
                "window": dict(self.app.cfg["window"]),
            }
            candidate = st.validate(candidate)
        except st.SettingsError as exc:
            messagebox.showerror("设置不正确", str(exc), parent=self)
            return

        try:
            self.app.apply_settings(candidate)
        except (OSError, st.SettingsError) as exc:
            messagebox.showerror("保存失败", "无法保存设置：\n%s" % exc, parent=self)
            return
        self.cancel()

    def cancel(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app._settings_dialog = None
        self.destroy()
        self.app.on_dialog_closed()


class HelpWindow(tk.Toplevel):
    def __init__(self, app):
        tk.Toplevel.__init__(self, app.root)
        self.app = app
        self.title("帮助 - 放学情况")
        self.configure(bg=BG)
        self.transient(app.root)
        self.protocol("WM_DELETE_WINDOW", self.close)

        frame = tk.Frame(self, bg=BG, padx=8, pady=8)
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            frame,
            width=66,
            height=26,
            bg="black",
            fg=COLOR_PENDING,
            font=("宋体", 11),
            wrap="word",
            relief="flat",
            padx=8,
            pady=6,
        )
        scrollbar = tk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.text.insert("1.0", HELP_TEXT.format(hotkey=self.app.cfg["hotkey"]))
        self.text.configure(state="disabled")

        tk.Button(
            self,
            text="关闭",
            command=self.close,
            font=FONT_HINT,
            bg="#222222",
            fg="white",
            activebackground="#444444",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=2,
        ).pack(pady=(0, 10))

        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2)
        y = max(0, (self.winfo_screenheight() - self.winfo_reqheight()) // 2)
        self.geometry("+%d+%d" % (x, y))
        self.focus_force()

    def close(self):
        self.app._help_window = None
        self.destroy()
        self.app.on_dialog_closed()
