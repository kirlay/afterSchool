# -*- coding: utf-8 -*-
"""程序入口：命令行参数、单实例、启动界面。"""

import argparse
import os
import tkinter as tk
from tkinter import messagebox

from aschool import __version__
from aschool import app as app_module
from aschool import settings as st
from aschool import winutil


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="樱花校区放学情况 v%s" % __version__)
    parser.add_argument("--settings", action="store_true", help="启动后直接打开设置窗口")
    parser.add_argument("--show", action="store_true", help="本次运行不按时间自动隐藏")
    parser.add_argument("--decorated", action="store_true", help="强制显示标题栏（默认已显示）")
    parser.add_argument("--no-titlebar", dest="no_titlebar", action="store_true", help="隐藏标题栏（排查问题用）")
    parser.add_argument("--now", metavar="HH:MM", help="把当前时间模拟成指定时刻（调试用）")
    return parser.parse_args(argv)


def notify_already_running():
    try:
        cfg, _warning = st.load()
        message = "“放学情况”已经在运行。\n\n按 %s 打开设置，或双击“设置”快捷方式。" % cfg["hotkey"]
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("已经在运行", message, parent=root)
        root.destroy()
    except Exception as exc:
        winutil.write_log(os.path.join(st.data_dir(), st.LOG_NAME), "提示已运行失败：%s" % exc)


def main(argv=None):
    args = parse_args(argv)
    log_path = os.path.join(st.data_dir(), st.LOG_NAME)
    winutil.install_exception_hook(log_path)

    mutex = winutil.acquire_single_instance(st.MUTEX_NAME)
    if mutex is None:
        if args.settings:
            winutil.touch_flag(os.path.join(st.data_dir(), st.FLAG_NAME))
        else:
            notify_already_running()
        return 0

    cfg, warning = st.load()
    root = tk.Tk()
    application = app_module.Application(
        root,
        cfg,
        options={
            "settings": args.settings,
            "force_show": args.show,
            "decorated": args.decorated,
            "no_titlebar": args.no_titlebar,
            "now": args.now,
        },
    )
    root.report_callback_exception = application.report_exception
    if warning:
        root.after(300, lambda: messagebox.showwarning("设置文件提示", warning, parent=root))

    application.start()
    try:
        root.mainloop()
    finally:
        winutil.release_single_instance(mutex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
