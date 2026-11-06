# -*- coding: utf-8 -*-
"""全局快捷键：组合键解析 + GetAsyncKeyState 轮询。

Fn 键由键盘固件/厂商驱动处理，Windows 收不到，所以不能绑定 Fn；
单独的普通字母键也不允许，避免在其它窗口打字时误触发。
"""

import ctypes
import sys

_MODIFIER_ALIASES = {
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "alt": "Alt",
    "shift": "Shift",
    "win": "Win",
    "windows": "Win",
    "meta": "Win",
    "cmd": "Win",
}

_MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Win")

_MODIFIER_VK = {"Ctrl": 0x11, "Alt": 0x12, "Shift": 0x10, "Win": 0x5B}

_KEY_VK = {}
for _code in range(ord("A"), ord("Z") + 1):
    _KEY_VK[chr(_code)] = _code
for _digit in "0123456789":
    _KEY_VK[_digit] = ord(_digit)
for _number in range(1, 13):
    _KEY_VK["F%d" % _number] = 0x6F + _number

_SUGGESTIONS = (
    "F9",
    "F10",
    "F11",
    "F12",
    "Ctrl+Alt+F9",
    "Ctrl+Alt+F10",
    "Ctrl+Shift+F9",
    "Ctrl+Alt+F12",
)


class HotkeyError(ValueError):
    """快捷键写法不合法。"""


def suggestions():
    """设置界面里推荐的快捷键。"""
    return list(_SUGGESTIONS)


def parse(text):
    """解析快捷键，返回 (修饰键集合, 虚拟键码, 规范写法)。"""
    if not isinstance(text, str) or not text.strip():
        raise HotkeyError("快捷键不能为空")

    parts = [part.strip() for part in text.replace("＋", "+").split("+")]
    if any(part == "" for part in parts):
        raise HotkeyError("快捷键格式不对：%s" % text)

    modifiers = []
    main_key = None
    for part in parts:
        lowered = part.lower()
        if lowered in _MODIFIER_ALIASES:
            name = _MODIFIER_ALIASES[lowered]
            if name in modifiers:
                raise HotkeyError("修饰键重复：%s" % part)
            modifiers.append(name)
            continue
        if main_key is not None:
            raise HotkeyError("快捷键只能有一个主键：%s" % text)
        main_key = part.upper()

    if main_key is None:
        raise HotkeyError("快捷键缺少主键：%s" % text)
    if main_key not in _KEY_VK:
        raise HotkeyError("不支持的按键：%s（可用 A–Z、0–9、F1–F12）" % main_key)
    if not modifiers and not main_key.startswith("F"):
        raise HotkeyError("单独按键只允许 F1–F12；其它按键请加 Ctrl/Alt/Shift")

    canonical = "+".join([m for m in _MODIFIER_ORDER if m in modifiers] + [main_key])
    return frozenset(modifiers), _KEY_VK[main_key], canonical


def _key_down(vk):
    if sys.platform != "win32":
        raise RuntimeError("全局快捷键只在 Windows 上可用")
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


class HotkeyPoller(object):
    """轮询式全局快捷键：窗口没有焦点、甚至被隐藏时也能触发。"""

    def __init__(self, text):
        modifiers, vk, canonical = parse(text)
        self.modifiers = modifiers
        self.vk = vk
        self.canonical = canonical
        self._was_down = False

    def triggered(self):
        """按下瞬间返回一次 True；按住不会重复触发。"""
        pressed = _key_down(self.vk)
        if pressed:
            if self.modifiers:
                pressed = all(_key_down(_MODIFIER_VK[m]) for m in self.modifiers)
            else:
                pressed = not any(_key_down(vk) for vk in _MODIFIER_VK.values())
        if pressed and not self._was_down:
            self._was_down = True
            return True
        if not pressed:
            self._was_down = False
        return False
