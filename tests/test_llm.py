import contextlib
import io
import json
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

from macfix.cli import main
from macfix.llm import APIError, ENDPOINT, MODEL, explain_with_groq, validate

ANSWER = {"meaning": "The cause cannot be identified from this message.", "severity": "Unknown",
          "causes": ["Not enough information."], "steps": ["Record the exact error and affected app."],
          "avoid": "Do not erase disks or delete files."}


@patch.dict("os.environ", {"GROQ_API_KEY": "test-only-key"}, clear=True)
class APITests(unittest.TestCase):
    def response(self, opener, content=ANSWER, finish="stop"):
        opener.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(content)}}]}).encode()

    @patch("macfix.llm.urllib.request.build_opener")
    def test_request_and_unknown(self, opener):
        self.response(opener)
        self.assertEqual(explain_with_groq("Unfamiliar error 917"), ANSWER)
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, ENDPOINT)
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], MODEL)
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "Unfamiliar error 917"})
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-key")
        self.assertNotIn("tools", payload)
        self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 30)

    @patch("macfix.llm.urllib.request.build_opener")
    def test_vision_payload(self, opener):
        self.response(opener)
        explain_with_groq("What happened?", image="data:image/png;base64,AAAA")
        payload = json.loads(opener.return_value.open.call_args.args[0].data)
        self.assertEqual(payload["model"], "qwen/qwen3.6-27b")
        self.assertEqual(payload["reasoning_effort"], "none")
        content = payload["messages"][1]["content"]
        self.assertEqual(content[0]["text"], "What happened?")
        self.assertEqual(content[1]["image_url"]["url"], "data:image/png;base64,AAAA")

    @patch("macfix.llm.urllib.request.build_opener")
    def test_no_key_no_request(self, opener):
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}, clear=True), self.assertRaisesRegex(APIError, "Set GROQ_API_KEY"):
            explain_with_groq("disk error")
        opener.assert_not_called()

    @patch("macfix.llm.urllib.request.build_opener")
    def test_invalid_input_no_request(self, opener):
        for message in ("", " " * 3, "a" * 8001):
            with self.assertRaises(APIError):
                explain_with_groq(message)
        opener.assert_not_called()

    @patch("macfix.llm.urllib.request.build_opener")
    def test_http_errors_do_not_expose_body_or_key(self, opener):
        for code in (401, 403, 429, 500, 302):
            opener.return_value.open.side_effect = urllib.error.HTTPError(ENDPOINT, code, "secret", {}, None)
            with self.subTest(code=code), self.assertRaises(APIError) as exc:
                explain_with_groq("disk error")
            self.assertNotIn("secret", str(exc.exception))
            self.assertNotIn("test-only-key", str(exc.exception))

    @patch("macfix.llm.urllib.request.build_opener")
    def test_connection_errors(self, opener):
        for error in (TimeoutError(), urllib.error.URLError("private detail")):
            opener.return_value.open.side_effect = error
            with self.assertRaisesRegex(APIError, "Could not reach"):
                explain_with_groq("disk error")

    @patch("macfix.llm.urllib.request.build_opener")
    def test_bad_responses(self, opener):
        for data in ({}, {**ANSWER, "severity": "Definitely broken"}, {**ANSWER, "steps": []}, None):
            self.response(opener, data)
            with self.subTest(data=data), self.assertRaisesRegex(APIError, "invalid explanation"):
                explain_with_groq("disk error")
        self.response(opener, finish="length")
        with self.assertRaises(APIError):
            explain_with_groq("disk error")
        for raw in (b"not json", b"x" * 128001):
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = raw
            with self.assertRaises(APIError):
                explain_with_groq("disk error")

    def test_terminal_controls_removed(self):
        result = validate({**ANSWER, "meaning": "hello\x1b\x07world"})
        self.assertEqual(result["meaning"], "helloworld")


class GroqCLITests(unittest.TestCase):
    @patch("macfix.cli.explain_with_groq", return_value=ANSWER)
    def test_default_uses_groq(self, api):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["Unfamiliar error"]), 0)
        api.assert_called_once_with("Unfamiliar error")
        self.assertIn("Severity\n--------\nUnknown", output.getvalue())

    @patch("macfix.cli.read_clipboard", return_value="clipboard error")
    @patch("macfix.cli.explain_with_groq", return_value=ANSWER)
    def test_clipboard_uses_groq(self, api, clipboard):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--clipboard"]), 0)
        api.assert_called_once_with("clipboard error")

    @patch("macfix.cli.explain_with_groq", side_effect=APIError("Rate limit reached"))
    def test_failure_no_silent_fallback(self, api):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main(["disk error"]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Rate limit reached", errors.getvalue())

    @patch("macfix.cli.explain_with_groq")
    def test_removed_offline_option_is_rejected(self, api):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            main(["--offline", "Permission denied"])
        self.assertEqual(exc.exception.code, 2)
        api.assert_not_called()
