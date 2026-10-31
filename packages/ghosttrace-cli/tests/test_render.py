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

    def test_waiting_message_is_chosen_fresh_for_each_request(self):
        chosen = [
            "the repository stirs...",
            "tracing what came before...",
            "old commits are speaking...",
        ]
        with patch("ghosttrace_cli.render.supports_color", return_value=False):
            with patch(
                "ghosttrace_cli.render.random.choice", side_effect=chosen
            ) as choice:
                messages = [render.render_waiting() for _ in range(3)]

        self.assertEqual(
            messages,
            [f"  [analyzing] {message}" for message in chosen],
        )
        self.assertEqual(choice.call_count, 3)
        self.assertTrue(all(len(message) <= 40 for message in chosen))


if __name__ == "__main__":
    unittest.main()
