# -*- coding: utf-8 -*-
"""布局计算的单元测试。"""

import unittest

from aschool import layout


class DefaultTests(unittest.TestCase):
    def test_fonts(self):
        self.assertEqual(layout.title_font_size(16), 20)
        self.assertEqual(layout.hint_font_size(16), 12)
        self.assertEqual(layout.title_font_size(10), 14)
        self.assertEqual(layout.hint_font_size(10), 8)
        self.assertEqual(layout.hint_font_size(48), 44)

    def test_row_start(self):
        self.assertEqual(layout.row_start(16), 95)
        self.assertEqual(layout.row_start(24), 143)

    def test_entry_y(self):
        self.assertEqual(layout.entry_y(416, 16), 360)
        self.assertEqual(layout.entry_y(500, 24), 416)

    def test_columns(self):
        self.assertEqual(layout.column_x(548, 4, 1), 30)
        self.assertEqual(layout.column_pitch(548, 4), 122.0)
        self.assertEqual(layout.column_x(548, 4, 4), 396)

    def test_row_y(self):
        self.assertEqual(layout.row_y(16, 44, 0), 95)
        self.assertEqual(layout.row_y(16, 44, 2), 183)
        self.assertEqual(layout.row_y(16, 60, 2), 215)

    def test_title_text(self):
        self.assertEqual(layout.title_text("某某小学"), "某某小学\n放学情况")
        self.assertEqual(layout.title_text("  某某小学  "), "某某小学\n放学情况")
        self.assertEqual(layout.title_text(""), "放学情况")
        self.assertEqual(layout.title_text(None), "放学情况")


class SizingTests(unittest.TestCase):
    def test_wider_columns_are_farther_apart(self):
        narrow = layout.column_pitch(548, 4)
        wide = layout.column_pitch(700, 4)
        self.assertTrue(wide > narrow)
        self.assertGreaterEqual(wide - narrow, 30)

    def test_big_font_keeps_columns_separated(self):
        font = 24
        pitch = layout.column_pitch(700, 4)
        self.assertGreaterEqual(pitch, font * 5)

    def test_entry_stays_inside_window(self):
        for height in (240, 416, 1080):
            y = layout.entry_y(height, 16)
            self.assertGreater(y, 0)
            self.assertLess(y, height)

    def test_rows_do_not_overlap(self):
        font, spacing = 16, 44
        first = layout.row_y(font, spacing, 0)
        second = layout.row_y(font, spacing, 1)
        self.assertEqual(second - first, spacing)


if __name__ == "__main__":
    unittest.main()
