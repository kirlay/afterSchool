# -*- coding: utf-8 -*-
"""显示时段判断与下一次切换时间。

全部是纯函数，不依赖 Tk，便于单元测试。
每天只有一段显示时间：begin <= 现在 < end，不支持跨零点。
"""

import datetime

_TIME_FORMAT = "%02d:%02d"


def parse_hhmm(text):
    """把 "14:50" / "9:5" 解析成 datetime.time；不合法时抛 ValueError。"""
    if not isinstance(text, str):
        raise ValueError("时间必须是文本")
    stripped = text.strip().replace("：", ":")
    if ":" not in stripped:
        raise ValueError("时间格式应为 时:分，例如 14:50")
    hour_text, minute_text = stripped.split(":", 1)
    if not hour_text.isdigit() or not minute_text.isdigit():
        raise ValueError("时间格式应为 时:分，例如 14:50")
    hour = int(hour_text)
    minute = int(minute_text)
    if hour > 23:
        raise ValueError("小时必须在 0–23 之间")
    if minute > 59:
        raise ValueError("分钟必须在 0–59 之间")
    return datetime.time(hour, minute)


def format_hhmm(value):
    """把 datetime.time 格式化成 "HH:MM"。"""
    return _TIME_FORMAT % (value.hour, value.minute)


def is_visible(now, begin, end):
    """当前时刻是否处于显示时段（含开始、不含结束）。"""
    current = now.time()
    return begin <= current < end


def next_transition(now, begin, end):
    """严格晚于 now 的下一个边界时刻（开始或结束）。"""
    best = None
    for offset in (0, 1, 2):
        day = now.date() + datetime.timedelta(days=offset)
        for moment in (begin, end):
            candidate = datetime.datetime.combine(day, moment)
            if candidate > now and (best is None or candidate < best):
                best = candidate
    return best


def milliseconds_until(target, now):
    """target - now 的毫秒数，不会小于 0。"""
    delta = (target - now).total_seconds() * 1000.0
    return int(delta) if delta > 0 else 0


def next_delay_ms(now, begin, end, visible_interval_ms, hidden_cap_ms):
    """下一次检查要睡多久（毫秒）。

    可见时最多睡 visible_interval_ms，隐藏时最多睡 hidden_cap_ms；
    两种情况都会在边界时刻之前醒来，保证准时切换。
    """
    target = next_transition(now, begin, end)
    remaining = milliseconds_until(target, now)
    cap = visible_interval_ms if is_visible(now, begin, end) else hidden_cap_ms
    return int(min(cap, remaining))
