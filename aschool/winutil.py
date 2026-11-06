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
