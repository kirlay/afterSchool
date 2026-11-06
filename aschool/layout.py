# -*- coding: utf-8 -*-
"""界面布局计算（纯函数，不依赖 Tk），便于单元测试。

窗口尺寸、字号、行距都由设置里的具体数值决定：
    layout.width / layout.height  —— 客户区像素
    layout.font_size              —— 班级文字磅值
    layout.row_spacing            —— 每行之间的像素
"""

MARGIN_X = 30

DEFAULT_WIDTH = 548
DEFAULT_HEIGHT = 416
DEFAULT_FONT_SIZE = 16
DEFAULT_ROW_SPACING = 44

MIN_FONT = 8


def title_font_size(font_size):
    """顶部标题字号：比班级字号大 4 磅。"""
    return max(MIN_FONT, int(font_size) + 4)


def hint_font_size(font_size):
    """输入框、提示文字字号：比班级字号小 4 磅。"""
    return max(MIN_FONT, int(font_size) - 4)


def row_start(font_size):
    """第一行班级的 y 坐标（给标题留位置）。"""
    return int(round(int(font_size) * 5.94))


def entry_y(height, font_size):
    """输入框的 y 坐标：贴近窗口底部。"""
    return int(height) - int(round(int(font_size) * 3.5))


def column_pitch(width, columns):
    """列间距：把窗口宽度平均分给各列。"""
    columns = max(1, int(columns))
    return (float(width) - 2.0 * MARGIN_X) / columns


def column_x(width, columns, index):
    """第 index 列（从 1 开始）的 x 坐标。"""
    return int(round(MARGIN_X + column_pitch(width, columns) * (int(index) - 1)))


def row_y(font_size, row_spacing, row_index):
    """第 row_index 行（从 0 开始）的 y 坐标。"""
    return row_start(font_size) + int(row_spacing) * int(row_index)


def title_text(school_name):
    """顶部两行标题文字。"""
    name = (school_name or "").strip()
    return name + "\n放学情况" if name else "放学情况"
