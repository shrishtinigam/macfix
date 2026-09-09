# macfix

A small Python CLI that sends a macOS error to **Groq's LLM API** and prints
Meaning, Severity, Likely causes, What to try, and Avoid. Groq is the only explanation source; an internet connection and API key are required.
No GUI, database, or agents. Python 3.10+ required; Pillow validates images and removes metadata.

## Install

From this project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure Groq

Create an API key at https://console.groq.com/keys and stay on the Free plan if
you want free-tier usage. The app cannot determine your billing plan; API usage
on a paid account can incur charges. Model availability and quotas can change.

Open `.env` in this project directory, paste your key after `=`, and save:

```dotenv
GROQ_API_KEY=your_key_here
```

macfix automatically reads this file on each Groq request, including when you
run the command from another directory. This location is tied to this editable
installation: the `.env` alongside `pyproject.toml`. No shell export is needed.
An existing `GROQ_API_KEY` environment variable overrides the file; run
`unset GROQ_API_KEY` if you want to use the saved key instead.

The file is excluded from Git and created with owner-only permissions. It still
stores your key as plain text: do not share it or include it in a project archive.
The parser reads only `GROQ_API_KEY=value` (optional matching quotes), not shell
commands, variable expansion, or general dotenv syntax. It never executes the file.
Text model: `openai/gpt-oss-120b`. Image model: `qwen/qwen3.6-27b`. Both are hosted by Groq and use the same saved API key.

## Use

```bash
macfix "The disk you attached was not readable by this computer"
macfix --clipboard
macfix --image ~/Desktop/error.png "This happens when I open the app"
macfix --capture "My external drive is not appearing"
macfix --help
```

`--clipboard` reads the current text using macOS `pbpaste` and sends it to Groq. Copy only the intended error text first.
Direct text input works on other operating systems too.

The app sends the supplied text, optional image, and safety instructions over HTTPS.
It does not scan your Mac, save conversations, or execute generated advice.
Remove passwords, API keys, and confidential information before sending text.
There is no automatic redaction or text-clipboard preview in this version.
Groq's retention controls: https://console.groq.com/docs/your-data
API reference: https://console.groq.com/docs/api-reference

AI answers may be wrong; safety instructions are not a guarantee. The model is
asked to acknowledge uncertainty, avoid destructive steps and shell commands,
and warn about data risks. macfix validates response structure, not diagnostic
accuracy. It cannot verify your Mac's condition. Unknown severity is supported.

Input is limited to 8,000 characters; requests have a 30-second timeout. Missing
keys, network failures, quotas, and malformed responses produce a clear error.
There are no automatic retries or silent local fallbacks. Exit codes: 0 for an
explanation, 1 for API/configuration failures, 2 for argument/clipboard errors.

## Screenshots

Use one PNG or JPEG with a required quoted problem description. The vision model
reads the screenshot and description together and returns the same five sections
in one API call. Text-only commands still use the text model. Images are limited
to 8 MB and 20 million pixels, validated, and re-encoded as PNG with metadata
removed. Visible private information is not redacted; crop it out yourself.

`--image` sends the file you explicitly select without another confirmation.
`--capture` requires an interactive macOS terminal: select an area, review it in
Preview, then type `y` to send. Any other answer cancels. Escape cancels selection;
macOS may report cancellation as a capture error. Failed capture or preview sends
nothing. The capture command may need Screen Recording permission for the terminal
in System Settings → Privacy & Security. Restart the terminal if macOS requests it.

macfix deletes its temporary capture file on completion, cancellation, or errors.
Preview may remain open; close its window when finished. This cleanup is not a
guarantee against copies or caches maintained by macOS or Preview. Existing files
supplied through `--image` are never altered or deleted. Confirmation approves the
original captured image; editing it in Preview does not change the pending upload.
Cancel and use `--image` with the saved edited copy if you need changes.

`--image` and `--capture` cannot be combined with each other or `--clipboard`.
No automatic model fallback, repeated API calls, or repair execution is added.
Vision documentation: https://console.groq.com/docs/vision

## Test

```bash
python -m unittest discover -s tests -v
```

Tests mock Groq and clipboard calls. They cover request construction, output
validation, API failures, direct/clipboard input, unknown responses and rejection of unsupported options.
They do not spend API quota; a live request requires a configured key. Image tests
cover validation, model routing, capture confirmation, cancellation, and cleanup.

Files: `cli.py` parses and formats; `llm.py` handles Groq; `diagnostics.py`
isolates clipboard/capture/preview commands; `images.py` prepares screenshots;
`config.py` loads the saved API key.
