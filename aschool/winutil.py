# -*- coding: utf-8 -*-
"""Windows 相关的小工具：单实例互斥体、异常日志、通知文件。"""

import ctypes
import os
import sys
import time
import traceback

ERROR_ALREADY_EXISTS = 183


def acquire_single_instance(name):
    """拿到互斥体返回句柄，已有实例在运行则返回 None。"""
    if sys.platform != "win32":
        return 1
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return 1
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_single_instance(handle):
    if sys.platform != "win32" or not handle or handle == 1:
        return
    try:
        ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


def write_log(path, text):
    """追加写日志；写失败就算了，绝不能再抛异常。"""
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except OSError:
        pass


def install_exception_hook(log_path):
    def hook(exc_type, exc_value, tb):
        write_log(log_path, "".join(traceback.format_exception(exc_type, exc_value, tb)))

    sys.excepthook = hook
    return hook


def touch_flag(path):
    """请正在运行的实例打开设置窗口。"""
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%d\n" % os.getpid())
    except OSError:
        pass


def bring_to_front(window):
    """尽量把窗口带到前台；Windows 可能拒绝 SetForegroundWindow，失败就忽略。"""
    try:
        window.lift()
    except Exception:
        pass
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT
        if hwnd:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def caption_height():
    """标题栏 + 上边框的高度（像素），用来把标题栏放到屏幕外。"""
    if sys.platform != "win32":
        return 0
    try:
        user32 = ctypes.windll.user32
        return int(
            user32.GetSystemMetrics(4)   # SM_CYCAPTION
            + user32.GetSystemMetrics(33)  # SM_CYSIZEFRAME
            + user32.GetSystemMetrics(92)  # SM_CXPADDEDBORDER
        )
    except Exception:
        return 0


def frame_border_width():
    """窗口左右边框的宽度（像素）。"""
    if sys.platform != "win32":
        return 0
    try:
        user32 = ctypes.windll.user32
        return int(
            user32.GetSystemMetrics(32)   # SM_CXSIZEFRAME
            + user32.GetSystemMetrics(92)  # SM_CXPADDEDBORDER
        )
    except Exception:
        return 0
