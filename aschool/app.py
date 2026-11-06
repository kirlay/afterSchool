# -*- coding: utf-8 -*-
"""主窗口、设置对话框与帮助窗口。"""

import datetime
import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox

from . import hotkey
from . import schedule
from . import settings as st
from . import winutil

BG = "black"
COLOR_PENDING = "green"
COLOR_DONE = "red"
COLOR_TITLE = "#f26522"
FONT_TITLE = ("黑体", 20)
FONT_CLASS = ("黑体", 16)
FONT_HINT = ("黑体", 12)

HIDDEN_CAP_MS = 30 * 60 * 1000
EPSILON_MS = 50
POLL_INTERVAL_MS = 150
POLL_FLAG_EVERY = 7
STARTUP_SHOW_MS = 3000

HELP_TEXT = """樱花校区放学情况  v2.0

一、班号怎么输入
    101 = 一年级 1 班，102 = 一年级 2 班，以此类推；
    二年级是 201、202……，班级数以设置里的为准。
    输入 101 后按回车，一1班变红并显示“放学”。

二、输错了怎么撤销
    输入 -101 后按回车，一1班恢复绿色“未放学”。
    （前面加一个减号，数字不变）

三、一次全部复位
    输入 000 后按回车，确认后所有班级都变回“未放学”。

四、打开设置（快捷键 {hotkey}）
    默认 F9；也可以是 F10、F11、F12，或 Ctrl+Alt+F9 这类组合，
    在设置里可以改。窗口隐藏时按同样有效。
    班级数：每个年级 0–12 个班，0 表示没有这个年级；
    显示时段：窗口在这个时间段内显示，其余时间自动隐藏；
    校准间隔：默认 120 秒，越大越省电，到点仍会准时切换；
    还可以设置窗口置顶、隐藏时自动复位、窗口位置复位。

五、打开本帮助（快捷键 F1）
    按 F1 随时打开，窗口隐藏时也能按。

六、退出程序
    按 {hotkey} 打开设置，点右下角的“退出程序”。

七、显示时段
    到开始时间窗口自动出现，到结束时间自动隐藏；
    在设置里改完时间、保存后立即生效。

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
        self._offset_seconds = self._parse_now_offset(self.options.get("now"))
        self._logo_image = None

        self._setup_window()
        self._setup_widgets()
        self._settings_hotkey = hotkey.HotkeyPoller(self.cfg["hotkey"])

    # ------------------------------------------------------------------ 窗口

    def _setup_window(self):
        root = self.root
        root.title("放学情况")
        root.configure(bg=BG)
        root.resizable(width=False, height=False)
        if self.cfg["hide_titlebar"] and not self.options.get("decorated"):
            root.overrideredirect(True)
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
            text="宁波市四眼碶小学樱花校区\n放学情况",
            font=FONT_TITLE,
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

    def _setup_widgets(self):
        self.counter_label = tk.Label(self.root, text="读取班级编号：", font=FONT_HINT, bg=BG, fg=COLOR_PENDING)
        self.entry_var = tk.StringVar(self.root)
        self.entry = tk.Entry(self.root, textvariable=self.entry_var, width=15, font=FONT_HINT, justify="center")
        self.entry.bind("<Return>", self.on_enter)
        self.root.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------ 布局

    def _layout(self):
        classes = self.cfg["classes"]
        columns = max(classes) if classes else 1
        rows = max(1, len([count for count in classes if count > 0]))
        width = max(548, 179 + 123 * (columns - 1))
        entry_y = 140 + 44 * (rows - 1)
        height = max(416, entry_y + 56)
        x = int(self.cfg["window"].get("x", 0))
        y = int(self.cfg["window"].get("y", 0))
        self.root.geometry("%dx%d+%d+%d" % (width, height, x, y))
        return entry_y

    def _rebuild(self):
        for _code, label, _grade, _no in self.labels:
            label.destroy()
        self.labels = []
        self.label_by_code = {}

        row = 0
        for grade_index, count in enumerate(self.cfg["classes"]):
            if count <= 0:
                continue
            for class_no in range(1, int(count) + 1):
                code = "%d0%d" % (grade_index + 1, class_no)
                label = tk.Label(
                    self.root,
                    text=self._class_text(grade_index, class_no, False),
                    font=FONT_CLASS,
                    bg=BG,
                    fg=COLOR_PENDING,
                )
                label.place(x=30 + 123 * (class_no - 1), y=95 + 44 * row)
                self.labels.append((code, label, grade_index, class_no))
                self.label_by_code[code] = (label, grade_index, class_no)
            row += 1

        entry_y = self._layout()
        self.counter_label.place(x=20, y=entry_y + 4)
        self.entry.place(x=150, y=entry_y)

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
        try:
            self.root.lift()
        except tk.TclError:
            pass
        try:
            self.root.focus_force()
        except tk.TclError:
            pass
        self.entry.focus_set()

    def hide_window(self):
        self._visible = False
        if self.cfg["reset_on_hide"]:
            self.reset_all()
        self.entry_var.set("")
        self.root.withdraw()

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
        return schedule.next_delay_ms(now, begin, end, interval, HIDDEN_CAP_MS)

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
        self._settings_dialog = SettingsDialog(self)

    def show_help(self):
        if self._window_alive(self._help_window):
            self._help_window.lift()
            self._help_window.focus_force()
            return
        self._help_window = HelpWindow(self)

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
        self.cfg["window"] = {"x": self.root.winfo_x(), "y": self.root.winfo_y()}
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
            text="窗口置顶",
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
                "version": self.app.cfg.get("version", 1),
                "classes": [self._int_value(variable, "班级数") for variable in self.class_vars],
                "show": {"begin": self.begin_var.get(), "end": self.end_var.get()},
                "check_interval_seconds": self._int_value(self.interval_var, "校准间隔"),
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
