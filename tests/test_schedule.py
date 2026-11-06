# -*- coding: utf-8 -*-
"""时间调度单元测试：python -m unittest discover -s tests -v"""

import datetime
import unittest

from aschool import schedule

BEGIN = datetime.time(14, 50)
END = datetime.time(16, 25)


def at(hour, minute, second=0, day=6):
    return datetime.datetime(2026, 11, day, hour, minute, second)


class ParseTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schedule.parse_hhmm("14:50"), datetime.time(14, 50))
        self.assertEqual(schedule.parse_hhmm("9:5"), datetime.time(9, 5))
        self.assertEqual(schedule.parse_hhmm(" 07:00 "), datetime.time(7, 0))
        self.assertEqual(schedule.parse_hhmm("14：50"), datetime.time(14, 50))

    def test_invalid(self):
        for text in ("", "14", "14:60", "24:00", "ab:cd", "14:5:0", "-1", "1:2:3"):
            with self.assertRaises(ValueError, msg=text):
                schedule.parse_hhmm(text)

    def test_non_text(self):
        for value in (None, 1450, b"14:50"):
            with self.assertRaises(ValueError):
                schedule.parse_hhmm(value)

    def test_format(self):
        self.assertEqual(schedule.format_hhmm(datetime.time(9, 5)), "09:05")
        self.assertEqual(schedule.format_hhmm(datetime.time(16, 25)), "16:25")


class VisibilityTests(unittest.TestCase):
    def test_before_begin(self):
        self.assertFalse(schedule.is_visible(at(14, 49, 59), BEGIN, END))

    def test_exactly_begin(self):
        self.assertTrue(schedule.is_visible(at(14, 50, 0), BEGIN, END))

    def test_inside(self):
        self.assertTrue(schedule.is_visible(at(15, 30), BEGIN, END))

    def test_just_before_end(self):
        self.assertTrue(schedule.is_visible(at(16, 24, 59), BEGIN, END))

    def test_exactly_end(self):
        self.assertFalse(schedule.is_visible(at(16, 25, 0), BEGIN, END))

    def test_morning(self):
        self.assertFalse(schedule.is_visible(at(9, 0), BEGIN, END))


class NextTransitionTests(unittest.TestCase):
    def test_before_begin(self):
        now = at(14, 49, 59)
        self.assertEqual(schedule.next_transition(now, BEGIN, END), at(14, 50, 0))
        self.assertEqual(schedule.milliseconds_until(schedule.next_transition(now, BEGIN, END), now), 1000)

    def test_inside(self):
        now = at(15, 0, 0)
        self.assertEqual(schedule.next_transition(now, BEGIN, END), at(16, 25, 0))

    def test_at_end_goes_to_next_day(self):
        now = at(16, 25, 0)
        self.assertEqual(schedule.next_transition(now, BEGIN, END), at(14, 50, 0, day=7))

    def test_evening(self):
        now = at(17, 0, 0)
        self.assertEqual(schedule.next_transition(now, BEGIN, END), at(14, 50, 0, day=7))

    def test_early_morning(self):
        now = at(0, 30, 0)
        self.assertEqual(schedule.next_transition(now, BEGIN, END), at(14, 50, 0))


class DelayTests(unittest.TestCase):
    INTERVAL = 120000
    HIDDEN_CAP = 1800000

    def test_visible_uses_interval(self):
        self.assertEqual(
            schedule.next_delay_ms(at(15, 0), BEGIN, END, self.INTERVAL, self.HIDDEN_CAP),
            120000,
        )

    def test_visible_wakes_for_end(self):
        self.assertEqual(
            schedule.next_delay_ms(at(16, 24, 30), BEGIN, END, self.INTERVAL, self.HIDDEN_CAP),
            30000,
        )

    def test_hidden_wakes_for_begin(self):
        self.assertEqual(
            schedule.next_delay_ms(at(14, 49, 30), BEGIN, END, self.INTERVAL, self.HIDDEN_CAP),
            30000,
        )

    def test_hidden_uses_cap(self):
        self.assertEqual(
            schedule.next_delay_ms(at(17, 0), BEGIN, END, self.INTERVAL, self.HIDDEN_CAP),
            self.HIDDEN_CAP,
        )

    def test_hidden_overnight_uses_cap(self):
        self.assertEqual(
            schedule.next_delay_ms(at(23, 0), BEGIN, END, self.INTERVAL, self.HIDDEN_CAP),
            self.HIDDEN_CAP,
        )


class ExtraTimeTests(unittest.TestCase):
    RESET = datetime.time(9, 0)

    def test_next_occurrence_today(self):
        self.assertEqual(schedule.next_occurrence(at(8, 0), self.RESET), at(9, 0))

    def test_next_occurrence_at_exact_time_goes_tomorrow(self):
        self.assertEqual(schedule.next_occurrence(at(9, 0), self.RESET), at(9, 0, day=7))

    def test_next_occurrence_later_today_goes_tomorrow(self):
        self.assertEqual(schedule.next_occurrence(at(10, 0), self.RESET), at(9, 0, day=7))

    def test_transition_includes_reset_boundary(self):
        self.assertEqual(schedule.next_transition(at(8, 59), BEGIN, END, (self.RESET,)), at(9, 0))

    def test_transition_ignores_later_reset(self):
        self.assertEqual(schedule.next_transition(at(10, 0), BEGIN, END, (self.RESET,)), at(14, 50))

    def test_delay_wakes_for_reset(self):
        self.assertEqual(
            schedule.next_delay_ms(at(8, 59, 30), BEGIN, END, 120000, 1800000, (self.RESET,)),
            30000,
        )


if __name__ == "__main__":
    unittest.main()
