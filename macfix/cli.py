"""Command-line parsing and plain-text output."""

import argparse
import sys
import tempfile
from pathlib import Path
from contextlib import ExitStack
from .diagnostics import ClipboardError, read_clipboard, CaptureError, capture_screen, preview_capture
from .images import ImageError, load_image
from .llm import APIError, explain_with_groq


def render(meaning, severity, causes, steps, avoid) -> str:
    sections = (
        ("Meaning", meaning), ("Severity", severity),
        ("Likely causes", "\n".join(f"- {cause}" for cause in causes)),
        ("What to try", "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))),
        ("Avoid", avoid),
    )
    return "\n\n".join(f"{title}\n{'-' * len(title)}\n{body}" for title, body in sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explain macOS errors with Groq AI. Error text is sent to Groq.")
    parser.add_argument("message", nargs="?", help="the error message, in quotes")
    parser.add_argument("--clipboard", action="store_true", help="read text from the macOS clipboard")
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--image", metavar="PATH", help="send a PNG/JPEG screenshot with a required description")
    sources.add_argument("--capture", action="store_true", help="select a screen area, preview it, and confirm sending")
    args = parser.parse_args(argv)
    if (args.image or args.capture) and (args.clipboard or not args.message or not args.message.strip()):
        parser.error("--image and --capture require a quoted description and cannot be combined with --clipboard")
    if args.clipboard and args.message is not None:
        parser.error("use either a quoted message or --clipboard, not both")
    if args.clipboard:
        try:
            message = read_clipboard()
        except ClipboardError as exc:
            parser.error(str(exc))
    elif args.message is None or not args.message.strip():
        parser.error("provide a nonempty quoted error message or --clipboard")
    else:
        message = args.message
    try:
        with ExitStack() as stack:
            image = None
            if args.capture:
                if not sys.stdin.isatty():
                    parser.error("--capture requires an interactive terminal for confirmation")
                directory = stack.enter_context(tempfile.TemporaryDirectory(prefix="macfix-"))
                path = Path(directory) / "capture.png"
                print("Select an area of your screen; press Escape to cancel.", file=sys.stderr)
                if not capture_screen(path):
                    print("Capture cancelled. Nothing was sent.", file=sys.stderr)
                    return 0
                image = load_image(path)
                preview_capture(path)
                try:
                    confirmed = input("Review the screenshot in Preview. Send this image and description to Groq? [y/N] ")
                except EOFError:
                    confirmed = ""
                if confirmed.strip().lower() not in ("y", "yes"):
                    print("Cancelled. Nothing was sent.", file=sys.stderr)
                    return 0
            elif args.image:
                image = load_image(args.image)
            print("Sending " + ("screenshot and description" if image else "error text") +
                  " to Groq. AI advice may be incorrect; macfix does not execute repairs.", file=sys.stderr)
            result = explain_with_groq(message, image=image) if image else explain_with_groq(message)
            print(render(**result))
    except (APIError, ImageError, CaptureError) as exc:
        print(f"macfix: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
