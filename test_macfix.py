import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from macfix.cli import main
from macfix.diagnostics import ClipboardError, read_clipboard


class CLITests(unittest.TestCase):
    def test_invalid_arguments(self):
        for args in ([], [""], ["   "], ["message", "--clipboard"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(args)
            self.assertEqual(exc.exception.code, 2)

    @patch("macfix.cli.read_clipboard", side_effect=ClipboardError("The clipboard contains no text."))
    def test_clipboard_failure_is_friendly(self, read):
        with contextlib.redirect_stderr(io.StringIO()) as output, self.assertRaises(SystemExit) as exc:
            main(["--clipboard"])
        self.assertEqual(exc.exception.code, 2)
        self.assertIn("contains no text", output.getvalue())


class ClipboardTests(unittest.TestCase):
    @patch("macfix.diagnostics.sys.platform", "darwin")
    @patch("macfix.diagnostics.subprocess.run")
    def test_pbpaste(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "  Disk not readable\n", "")
        self.assertEqual(read_clipboard(), "Disk not readable")
        run.assert_called_once_with(["/usr/bin/pbpaste"], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", check=True, timeout=5)

    @patch("macfix.diagnostics.sys.platform", "darwin")
    @patch("macfix.diagnostics.subprocess.run")
    def test_clipboard_errors(self, run):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired("pbpaste", 5),
                      subprocess.CalledProcessError(1, "pbpaste"), OSError()):
            run.side_effect = error
            with self.subTest(error=error), self.assertRaises(ClipboardError):
                read_clipboard()
        run.side_effect = None
        run.return_value = subprocess.CompletedProcess([], 0, " \n", "")
        with self.assertRaises(ClipboardError):
            read_clipboard()

    @patch("macfix.diagnostics.sys.platform", "linux")
    @patch("macfix.diagnostics.subprocess.run")
    def test_non_macos(self, run):
        with self.assertRaisesRegex(ClipboardError, "requires macOS"):
            read_clipboard()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
