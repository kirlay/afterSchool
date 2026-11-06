# -*- coding: utf-8 -*-
"""设置与快捷键的单元测试。"""

import json
import os
import tempfile
import unittest

from aschool import hotkey
from aschool import settings


class DefaultTests(unittest.TestCase):
    def test_default_settings_are_valid(self):
        cfg = settings.validate(settings.default_settings())
        self.assertEqual(cfg["version"], settings.SETTINGS_VERSION)
        self.assertEqual(cfg["classes"], [3, 4, 4, 4, 4, 4])
        self.assertEqual(cfg["show"], {"begin": "14:50", "end": "16:25"})
        self.assertEqual(cfg["check_interval_seconds"], 120)
        self.assertEqual(cfg["daily_reset"], {"enabled": True, "time": "09:00"})
        self.assertFalse(cfg["hide_titlebar"])
        self.assertFalse(cfg["topmost"])
        self.assertTrue(cfg["reset_on_hide"])
        self.assertEqual(cfg["hotkey"], "F9")
        self.assertEqual(cfg["window"], {"x": 0, "y": 0})

    def test_default_settings_is_a_copy(self):
        first = settings.default_settings()
        first["classes"][0] = 9
        self.assertEqual(settings.default_settings()["classes"][0], 3)


class ValidateTests(unittest.TestCase):
    def base(self):
        return settings.default_settings()

    def test_classes_must_have_six_grades(self):
        cfg = self.base()
        cfg["classes"] = [3, 4, 4, 4, 4]
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("6 个年级", str(caught.exception))

    def test_classes_range(self):
        for bad in (-1, 13, "x"):
            cfg = self.base()
            cfg["classes"] = [bad, 4, 4, 4, 4, 4]
            with self.assertRaises(settings.SettingsError) as caught:
                settings.validate(cfg)
            self.assertTrue("0–12" in str(caught.exception) or "整数" in str(caught.exception))

    def test_classes_cannot_all_be_zero(self):
        cfg = self.base()
        cfg["classes"] = [0, 0, 0, 0, 0, 0]
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("至少", str(caught.exception))

    def test_end_must_be_after_begin(self):
        cfg = self.base()
        cfg["show"] = {"begin": "16:00", "end": "15:00"}
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("结束时间必须晚于开始时间", str(caught.exception))

    def test_same_begin_and_end(self):
        cfg = self.base()
        cfg["show"] = {"begin": "15:00", "end": "15:00"}
        with self.assertRaises(settings.SettingsError):
            settings.validate(cfg)

    def test_bad_time(self):
        cfg = self.base()
        cfg["show"] = {"begin": "25:00", "end": "16:00"}
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("显示时间不正确", str(caught.exception))

    def test_time_is_normalized(self):
        cfg = self.base()
        cfg["show"] = {"begin": "9:5", "end": "16:5"}
        clean = settings.validate(cfg)
        self.assertEqual(clean["show"], {"begin": "09:05", "end": "16:05"})

    def test_interval_range(self):
        for bad in (9, 3601, "abc", ""):
            cfg = self.base()
            cfg["check_interval_seconds"] = bad
            with self.assertRaises(settings.SettingsError):
                settings.validate(cfg)

    def test_daily_reset_default_when_missing(self):
        cfg = self.base()
        del cfg["daily_reset"]
        self.assertEqual(settings.validate(cfg)["daily_reset"], {"enabled": True, "time": "09:00"})

    def test_daily_reset_time_is_normalized(self):
        cfg = self.base()
        cfg["daily_reset"] = {"enabled": True, "time": "8:5"}
        self.assertEqual(settings.validate(cfg)["daily_reset"], {"enabled": True, "time": "08:05"})

    def test_daily_reset_can_be_disabled(self):
        cfg = self.base()
        cfg["daily_reset"] = {"enabled": False, "time": "09:00"}
        self.assertFalse(settings.validate(cfg)["daily_reset"]["enabled"])

    def test_daily_reset_bad_time(self):
        cfg = self.base()
        cfg["daily_reset"] = {"enabled": True, "time": "25:00"}
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("每日复位时间", str(caught.exception))

    def test_daily_reset_enabled_must_be_bool(self):
        cfg = self.base()
        cfg["daily_reset"] = {"enabled": "yes", "time": "09:00"}
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("每日复位", str(caught.exception))

    def test_flags_must_be_bool(self):
        cfg = self.base()
        cfg["hide_titlebar"] = "yes"
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("hide_titlebar", str(caught.exception))

    def test_hotkey_is_normalized(self):
        cfg = self.base()
        cfg["hotkey"] = "ctrl+alt+f9"
        self.assertEqual(settings.validate(cfg)["hotkey"], "Ctrl+Alt+F9")

    def test_bad_hotkey(self):
        cfg = self.base()
        cfg["hotkey"] = "Ctrl+Shift"
        with self.assertRaises(settings.SettingsError) as caught:
            settings.validate(cfg)
        self.assertIn("快捷键", str(caught.exception))

    def test_window_position(self):
        cfg = self.base()
        cfg["window"] = {"x": "abc", "y": 0}
        with self.assertRaises(settings.SettingsError):
            settings.validate(cfg)

    def test_window_position_ok(self):
        cfg = self.base()
        cfg["window"] = {"x": -20, "y": 300}
        self.assertEqual(settings.validate(cfg)["window"], {"x": -20, "y": 300})

    def test_unknown_keys_are_ignored(self):
        cfg = self.base()
        cfg["future_option"] = 123
        clean = settings.validate(cfg)
        self.assertNotIn("future_option", clean)


class MigrationTests(unittest.TestCase):
    def v1_settings(self):
        return {
            "version": 1,
            "classes": [3, 4, 4, 4, 4, 4],
            "show": {"begin": "15:00", "end": "16:30"},
            "check_interval_seconds": 60,
            "hide_titlebar": True,
            "topmost": True,
            "reset_on_hide": False,
            "hotkey": "F10",
            "window": {"x": 5, "y": 6},
        }

    def test_v1_restores_titlebar_and_drops_topmost(self):
        cfg = settings.validate(self.v1_settings())
        self.assertEqual(cfg["version"], settings.SETTINGS_VERSION)
        self.assertFalse(cfg["hide_titlebar"])
        self.assertFalse(cfg["topmost"])

    def test_v1_keeps_other_settings(self):
        cfg = settings.validate(self.v1_settings())
        self.assertEqual(cfg["classes"], [3, 4, 4, 4, 4, 4])
        self.assertEqual(cfg["show"], {"begin": "15:00", "end": "16:30"})
        self.assertEqual(cfg["check_interval_seconds"], 60)
        self.assertEqual(cfg["daily_reset"], {"enabled": True, "time": "09:00"})
        self.assertFalse(cfg["reset_on_hide"])
        self.assertEqual(cfg["hotkey"], "F10")
        self.assertEqual(cfg["window"], {"x": 5, "y": 6})

    def test_v2_respects_explicit_flags(self):
        raw = self.v1_settings()
        raw["version"] = 2
        cfg = settings.validate(raw)
        self.assertTrue(cfg["hide_titlebar"])
        self.assertTrue(cfg["topmost"])

    def test_missing_version_is_treated_as_v1(self):
        raw = self.v1_settings()
        del raw["version"]
        cfg = settings.validate(raw)
        self.assertFalse(cfg["hide_titlebar"])
        self.assertFalse(cfg["topmost"])

    def test_load_upgrades_file_on_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.v1_settings(), handle)

            loaded, warning = settings.load(path)
            self.assertIsNone(warning)
            self.assertFalse(loaded["hide_titlebar"])
            self.assertFalse(loaded["topmost"])

            with open(path, "r", encoding="utf-8") as handle:
                on_disk = json.load(handle)
            self.assertEqual(on_disk["version"], settings.SETTINGS_VERSION)
            self.assertFalse(on_disk["hide_titlebar"])
            self.assertFalse(on_disk["topmost"])
            self.assertEqual(on_disk["show"], {"begin": "15:00", "end": "16:30"})

    def test_file_with_utf8_bom_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            with open(path, "w", encoding="utf-8-sig") as handle:
                json.dump(self.v1_settings(), handle)
            loaded, warning = settings.load(path)
            self.assertIsNone(warning)
            self.assertFalse(loaded["hide_titlebar"])
            self.assertEqual(loaded["classes"], [3, 4, 4, 4, 4, 4])
            self.assertEqual(loaded["daily_reset"], {"enabled": True, "time": "09:00"})


class FileTests(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            loaded, warning = settings.load(path)
            self.assertIsNone(warning)
            self.assertEqual(loaded["classes"], [3, 4, 4, 4, 4, 4])

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            cfg = settings.default_settings()
            cfg["classes"] = [5, 4, 3, 2, 1, 0]
            saved = settings.save(cfg, path)
            loaded, warning = settings.load(path)
            self.assertIsNone(warning)
            self.assertEqual(loaded, saved)

    def test_saved_file_is_utf8_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            settings.save(settings.default_settings(), path)
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            self.assertEqual(raw["show"]["begin"], "14:50")

    def test_corrupt_file_is_backed_up(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{ 这不是 JSON")
            loaded, warning = settings.load(path)
            self.assertIsNotNone(warning)
            self.assertEqual(loaded["classes"], [3, 4, 4, 4, 4, 4])
            backups = [name for name in os.listdir(directory) if ".bak-" in name]
            self.assertEqual(len(backups), 1)
            self.assertFalse(os.path.exists(path))

    def test_invalid_content_is_treated_as_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "settings.json")
            cfg = settings.default_settings()
            cfg["classes"] = [0, 0, 0, 0, 0, 0]
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(cfg, handle)
            loaded, warning = settings.load(path)
            self.assertIsNotNone(warning)
            self.assertEqual(loaded["classes"], [3, 4, 4, 4, 4, 4])


class ClassCodeTests(unittest.TestCase):
    def test_codes(self):
        codes = settings.class_codes([3, 4, 0, 4, 4, 4])
        names = [code for code, _grade, _no in codes]
        self.assertEqual(names[:3], ["101", "102", "103"])
        self.assertEqual(names[3], "201")
        self.assertIn("401", names)
        self.assertNotIn("301", names)
        self.assertEqual(len(names), 3 + 4 + 0 + 4 + 4 + 4)

    def test_grade_and_class_index(self):
        codes = settings.class_codes([1, 1, 1, 1, 1, 1])
        self.assertEqual(codes[0], ("101", 0, 1))
        self.assertEqual(codes[5], ("601", 5, 1))


class HotkeyTests(unittest.TestCase):
    def test_simple_function_key(self):
        modifiers, vk, canonical = hotkey.parse("F9")
        self.assertEqual(modifiers, frozenset())
        self.assertEqual(vk, 0x78)
        self.assertEqual(canonical, "F9")

    def test_combination(self):
        modifiers, vk, canonical = hotkey.parse("ctrl+alt+f9")
        self.assertEqual(modifiers, frozenset({"Ctrl", "Alt"}))
        self.assertEqual(vk, 0x78)
        self.assertEqual(canonical, "Ctrl+Alt+F9")

    def test_letter_with_modifier(self):
        self.assertEqual(hotkey.parse("Ctrl+S")[2], "Ctrl+S")

    def test_fullwidth_plus(self):
        self.assertEqual(hotkey.parse("Ctrl＋Alt＋F9")[2], "Ctrl+Alt+F9")

    def test_modifier_order_is_fixed(self):
        self.assertEqual(hotkey.parse("Shift+Alt+Ctrl+F9")[2], "Ctrl+Alt+Shift+F9")

    def test_invalid(self):
        for text in ("", "   ", "Ctrl+Shift", "F13", "a", "Ctrl+Ctrl+F9", "Ctrl+Alt", "F9+F10", "Ctrl+"):
            with self.assertRaises(hotkey.HotkeyError, msg=text):
                hotkey.parse(text)

    def test_suggestions_are_valid(self):
        for text in hotkey.suggestions():
            hotkey.parse(text)


if __name__ == "__main__":
    unittest.main()
