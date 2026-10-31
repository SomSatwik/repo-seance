import os
import unittest
from unittest.mock import patch

from ghosttrace_cli import render
from ghosttrace_cli.render import render_explanation


class RenderExplanationTests(unittest.TestCase):
    def test_wraps_at_terminal_width_without_splitting_words(self):
        explanation = (
            "The repository history contains evidence that explains why this "
            "particular command may affect important generated artifacts."
        )
        terminal_width = 34

        with patch(
            "ghosttrace_cli.render.shutil.get_terminal_size",
            return_value=os.terminal_size((terminal_width, 24)),
        ):
            with patch("ghosttrace_cli.render.supports_color", return_value=False):
                rendered = render_explanation(explanation, "DESTRUCTIVE")

        lines = rendered.splitlines()
        reconstructed = " ".join(
            word for line in lines for word in line.strip().split()
        )

        self.assertEqual(reconstructed, explanation)
        self.assertTrue(all(len(line) <= terminal_width for line in lines))

    def test_waiting_lines_are_short_and_do_not_repeat_consecutively(self):
        render._last_waiting_message = ""
        with patch("ghosttrace_cli.render.supports_color", return_value=False):
            messages = [render.render_waiting() for _ in range(3)]

        self.assertEqual(len(set(messages)), 3)
        self.assertTrue(all(len(message.strip()) <= 40 for message in messages))


if __name__ == "__main__":
    unittest.main()
