import base64
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from macfix.cli import main
from macfix.images import load_image, ImageError
from macfix.diagnostics import capture_screen, preview_capture, CaptureError
from macfix.llm import APIError
from test_llm import ANSWER


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.png'

    def test_png_and_jpeg(self):
        for fmt in ('PNG', 'JPEG'):
            Image.new('RGB', (20, 20), 'white').save(self.path, format=fmt)
            data = load_image(self.path)
            self.assertTrue(data.startswith('data:image/png;base64,'))
            decoded = Image.open(io.BytesIO(base64.b64decode(data.split(',')[1])))
            self.assertEqual(decoded.size, (20, 20))
            self.assertFalse(decoded.getexif())

    def test_bad_missing_and_oversized(self):
        with self.assertRaises(ImageError):
            load_image(self.path)
        self.path.write_bytes(b'not an image')
        with self.assertRaises(ImageError):
            load_image(self.path)
        Image.new('RGB', (20,20)).save(self.path, format='GIF')
        with self.assertRaisesRegex(ImageError, 'PNG or JPEG'):
            load_image(self.path)
        with patch('macfix.images.MAX_BYTES', 2), self.assertRaises(ImageError):
            load_image(self.path)
        Image.new('RGB', (20,20)).save(self.path, format='PNG')
        with patch('macfix.images.MAX_PIXELS', 2), self.assertRaises(ImageError):
            load_image(self.path)

    @patch('macfix.cli.explain_with_groq', return_value=ANSWER)
    def test_image_cli(self, api):
        Image.new('RGB', (20,20)).save(self.path)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--image', str(self.path), 'What happened?']), 0)
        self.assertEqual(api.call_args.args, ('What happened?',))
        self.assertTrue(api.call_args.kwargs['image'].startswith('data:image/png;base64,'))

    @patch('macfix.cli.explain_with_groq')
    def test_invalid_combinations_no_api(self, api):
        for args in (['--image', 'x'], ['--capture'], ['--capture', '--clipboard', 'why'],
                     ['--image', 'x', '--capture', 'why']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(args)
            self.assertEqual(exc.exception.code, 2)
        api.assert_not_called()

    @patch('macfix.cli.explain_with_groq')
    def test_invalid_image_no_api(self, api):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--image', str(self.path), 'why']), 1)
        api.assert_not_called()

    @patch('macfix.cli.sys.stdin.isatty', return_value=True)
    @patch('macfix.cli.preview_capture')
    @patch('macfix.cli.capture_screen')
    @patch('macfix.cli.explain_with_groq', return_value=ANSWER)
    def test_capture_confirmation_and_cleanup(self, api, capture, preview, tty):
        paths = []
        def take(path):
            paths.append(path)
            Image.new('RGB', (20,20), 'white').save(path)
            return True
        capture.side_effect = take
        for answer in ('n', 'y'):
            api.reset_mock()
            with patch('builtins.input', return_value=answer), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--capture', 'why']), 0)
            self.assertEqual(api.call_count, int(answer == 'y'))
            self.assertFalse(paths[-1].parent.exists())
        api.side_effect = APIError('failure')
        with patch('builtins.input', return_value='y'), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--capture', 'why']), 1)
        self.assertFalse(paths[-1].parent.exists())

    @patch('macfix.cli.sys.stdin.isatty', return_value=True)
    @patch('macfix.cli.capture_screen', return_value=False)
    @patch('macfix.cli.explain_with_groq')
    def test_capture_escape(self, api, capture, tty):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--capture', 'why']), 0)
        api.assert_not_called()
        self.assertFalse(capture.call_args.args[0].parent.exists())

    @patch('macfix.diagnostics.sys.platform', 'linux')
    def test_capture_platform(self):
        with self.assertRaises(CaptureError):
            capture_screen(self.path)

    @patch('macfix.diagnostics.sys.platform', 'darwin')
    @patch('macfix.diagnostics.subprocess.run')
    def test_capture_command(self, run):
        run.return_value.returncode = 0
        self.assertFalse(capture_screen(self.path))
        self.assertIn('-i', run.call_args.args[0])
        self.assertEqual(run.call_args.args[0][0], '/usr/sbin/screencapture')
        run.side_effect = OSError()
        with self.assertRaises(CaptureError):
            capture_screen(self.path)
        with self.assertRaises(CaptureError):
            preview_capture(self.path)
