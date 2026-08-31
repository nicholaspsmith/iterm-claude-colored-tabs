#!/usr/bin/env python3
"""Unit tests for transcript parsing and color mapping."""
import importlib.util
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "iterm-claude-tab-color")

spec = importlib.util.spec_from_loader(
    "ictc", importlib.machinery.SourceFileLoader("ictc", SCRIPT)
)
ictc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ictc)


def entry(content, typ="user"):
    return json.dumps({"type": typ, "message": {"role": "user", "content": content}})


COLOR_CMD = (
    "<command-name>/color</command-name>\n"
    "            <command-message>color</command-message>\n"
    "            <command-args>{}</command-args>"
)


def system_entry(content, subtype="local_command"):
    return json.dumps({"type": "system", "subtype": subtype, "content": content})


class TestParseLine(unittest.TestCase):
    def test_system_local_command_entry(self):
        # The shape Claude Code >= 2.1.x actually writes (verified live).
        self.assertEqual(ictc.parse_line(system_entry(COLOR_CMD.format("blue"))), "blue")

    def test_system_entry_wrong_subtype_ignored(self):
        self.assertIsNone(
            ictc.parse_line(system_entry(COLOR_CMD.format("blue"), subtype="info"))
        )

    def test_system_entry_no_content_ignored(self):
        self.assertIsNone(ictc.parse_line(json.dumps({"type": "system", "subtype": "local_command"})))

    def test_genuine_color_command_string_content(self):
        self.assertEqual(ictc.parse_line(entry(COLOR_CMD.format("pink"))), "pink")

    def test_genuine_color_command_list_content(self):
        content = [{"type": "text", "text": COLOR_CMD.format("blue")}]
        self.assertEqual(ictc.parse_line(entry(content)), "blue")

    def test_default(self):
        self.assertEqual(ictc.parse_line(entry(COLOR_CMD.format("default"))), "default")

    def test_random_empty_args_ignored(self):
        self.assertIsNone(ictc.parse_line(entry(COLOR_CMD.format(""))))

    def test_unknown_color_ignored(self):
        self.assertIsNone(ictc.parse_line(entry(COLOR_CMD.format("chartreuse"))))

    def test_tool_result_false_positive_ignored(self):
        # A tool result that merely CONTAINS the marker text must not match.
        content = [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_x",
                "content": "grep found: " + COLOR_CMD.format("red"),
            }
        ]
        self.assertIsNone(ictc.parse_line(entry(content)))

    def test_assistant_entry_ignored(self):
        self.assertIsNone(ictc.parse_line(entry(COLOR_CMD.format("red"), typ="assistant")))

    def test_other_command_ignored(self):
        self.assertIsNone(
            ictc.parse_line(entry("<command-name>/exit</command-name>"))
        )

    def test_garbage_line_ignored(self):
        self.assertIsNone(ictc.parse_line("not json at all"))


class TestPalette(unittest.TestCase):
    def test_all_eight_colors_present(self):
        self.assertEqual(
            set(ictc.PALETTE),
            {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"},
        )

    def test_orange_is_claude_clay(self):
        self.assertEqual(ictc.PALETTE["orange"], (217, 119, 87))


class TestEscapes(unittest.TestCase):
    def test_set_sequence(self):
        seq = ictc.tab_color_sequence((217, 119, 87))
        self.assertIn(b"\033]6;1;bg;red;brightness;217\a", seq)
        self.assertIn(b"\033]6;1;bg;green;brightness;119\a", seq)
        self.assertIn(b"\033]6;1;bg;blue;brightness;87\a", seq)

    def test_reset_sequence(self):
        self.assertEqual(ictc.tab_reset_sequence(), b"\033]6;1;bg;*;default\a")

    def test_tmux_wrap(self):
        seq = ictc.wrap_tmux(b"\033]6;1;bg;*;default\a")
        self.assertTrue(seq.startswith(b"\033Ptmux;"))
        self.assertTrue(seq.endswith(b"\033\\"))
        self.assertIn(b"\033\033]6;1", seq)


class TestLastColorInFile(unittest.TestCase):
    def test_last_wins(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(entry(COLOR_CMD.format("red")) + "\n")
            f.write(entry("hello there") + "\n")
            f.write(entry(COLOR_CMD.format("cyan")) + "\n")
            path = f.name
        try:
            with open(path) as fh:
                colors = [c for c in (ictc.parse_line(l) for l in fh) if c]
            self.assertEqual(colors[-1], "cyan")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
