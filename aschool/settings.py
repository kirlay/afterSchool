# -*- coding: utf-8 -*-
"""设置文件：默认值、校验、读取与原子保存。"""

import json
import os
import sys
import time

from . import hotkey
from . import schedule

APP_DIR_NAME = "AfterSchool"
MUTEX_NAME = "Local\\AfterSchoolYinghua"
SETTINGS_NAME = "settings.json"
LOG_NAME = "error.log"
FLAG_NAME = "request_settings.flag"

GRADE_NAMES = ("一", "二", "三", "四", "五", "六")

DEFAULT = {
    "version": 1,
    "classes": [3, 4, 4, 4, 4, 4],
    "show": {"begin": "14:50", "end": "16:25"},
    "check_interval_seconds": 120,
    "hide_titlebar": True,
    "topmost": True,
    "reset_on_hide": True,
    "hotkey": "F9",
    "window": {"x": 0, "y": 0},
}


class SettingsError(ValueError):
    """设置内容不合法。"""


def default_settings():
    """返回一份全新的默认设置。"""
    return json.loads(json.dumps(DEFAULT))


def app_base_dir():
    """程序所在目录：打包后是 exe 目录，源码运行时是项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def appdata_dir():
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(root, APP_DIR_NAME)


def _is_writable(directory):
    probe = os.path.join(directory, ".write-test-%d" % os.getpid())
    try:
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("x")
        os.remove(probe)
        return True
    except OSError:
        return False


_data_dir = None


def data_dir():
    """设置与日志所在目录：优先程序目录，不可写时回退 %APPDATA%。"""
    global _data_dir
    if _data_dir:
        return _data_dir
    base = app_base_dir()
    if os.path.exists(os.path.join(base, SETTINGS_NAME)) or _is_writable(base):
        _data_dir = base
    else:
        fallback = appdata_dir()
        try:
            os.makedirs(fallback)
        except OSError:
            pass
        _data_dir = fallback
    return _data_dir


def settings_path(directory=None):
    return os.path.join(directory or data_dir(), SETTINGS_NAME)


def class_codes(classes):
    """把每个年级的班级数展开成 (编号, 年级序号, 班号)。"""
    codes = []
    for grade_index, count in enumerate(classes):
        for class_no in range(1, int(count) + 1):
            codes.append(("%d0%d" % (grade_index + 1, class_no), grade_index, class_no))
    return codes


def _validate_classes(raw):
    if not isinstance(raw, list) or len(raw) != len(GRADE_NAMES):
        raise SettingsError("班级设置必须是 6 个年级的列表")
    cleaned = []
    for index, value in enumerate(raw):
        try:
            count = int(value)
        except (TypeError, ValueError):
            raise SettingsError("%s年级的班级数不是整数" % GRADE_NAMES[index])
        if count < 0 or count > 12:
            raise SettingsError("%s年级的班级数必须在 0–12 之间" % GRADE_NAMES[index])
        cleaned.append(count)
    if sum(cleaned) == 0:
        raise SettingsError("至少要有一个班级")
    return cleaned


def _validate_show(raw, fallback):
    if not isinstance(raw, dict):
        raise SettingsError("显示时间设置不正确")
    try:
        begin = schedule.parse_hhmm(str(raw.get("begin", fallback["begin"])))
        end = schedule.parse_hhmm(str(raw.get("end", fallback["end"])))
    except ValueError as exc:
        raise SettingsError("显示时间不正确：%s" % exc)
    if begin >= end:
        raise SettingsError("结束时间必须晚于开始时间")
    return {"begin": schedule.format_hhmm(begin), "end": schedule.format_hhmm(end)}


def _validate_interval(raw):
    try:
        interval = int(raw)
    except (TypeError, ValueError):
        raise SettingsError("校准间隔必须是整数秒")
    if interval < 10 or interval > 3600:
        raise SettingsError("校准间隔必须在 10–3600 秒之间")
    return interval


def _validate_window(raw):
    if not isinstance(raw, dict):
        raw = {}
    window = {}
    for axis in ("x", "y"):
        try:
            value = int(raw.get(axis, 0))
        except (TypeError, ValueError):
            raise SettingsError("窗口位置必须是整数")
        if value < -10000 or value > 10000:
            raise SettingsError("窗口位置超出范围")
        window[axis] = value
    return window


def validate(raw):
    """校验并规范化设置，返回一份干净的新字典。"""
    if not isinstance(raw, dict):
        raise SettingsError("设置内容必须是 JSON 对象")

    result = default_settings()
    result["classes"] = _validate_classes(raw.get("classes", result["classes"]))
    result["show"] = _validate_show(raw.get("show", {}), result["show"])
    result["check_interval_seconds"] = _validate_interval(
        raw.get("check_interval_seconds", result["check_interval_seconds"])
    )

    for flag in ("hide_titlebar", "topmost", "reset_on_hide"):
        value = raw.get(flag, result[flag])
        if not isinstance(value, bool):
            raise SettingsError("%s 必须是 true 或 false" % flag)
        result[flag] = value

    try:
        _mods, _vk, canonical = hotkey.parse(str(raw.get("hotkey", result["hotkey"])))
    except hotkey.HotkeyError as exc:
        raise SettingsError("快捷键设置不正确：%s" % exc)
    result["hotkey"] = canonical

    result["window"] = _validate_window(raw.get("window", {}))
    return result


def load(path=None):
    """读取设置，返回 (设置, 警告文本或 None)。"""
    path = path or settings_path()
    if not os.path.exists(path):
        return default_settings(), None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return validate(raw), None
    except Exception as exc:  # 语法错误、编码错误、校验失败都按损坏处理
        backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d%H%M%S"))
        try:
            os.replace(path, backup)
        except OSError:
            backup = path
        warning = "设置文件无法使用，已改用默认设置。\n备份位置：%s\n原因：%s" % (backup, exc)
        return default_settings(), warning


def save(settings, path=None):
    """原子写入设置，返回规范化后的设置。"""
    path = path or settings_path()
    clean = validate(settings)
    directory = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(directory):
        os.makedirs(directory)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(clean, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)
    return clean
