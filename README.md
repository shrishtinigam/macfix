# macfix

Explain macOS errors and screenshots in plain English using Groq AI.

## Get started

Requires Python 3.10+, internet access, and a [Groq API key](https://console.groq.com/keys).

Open Terminal, go to the project folder, then install:

```bash
cd /path/to/macfix
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Replace `/path/to/macfix` with the folder containing `pyproject.toml`.

Create a file named `.env` in that folder and add your key:

```dotenv
GROQ_API_KEY=your_key_here
```

Replace `your_key_here` with your actual key and save. The key loads automatically; you only set it once. `.env` is Git-ignored—keep it private.

## Explain an error

Paste the error in quotes after `macfix`:

```bash
macfix "The disk you attached was not readable by this computer"
```

Example output (AI wording varies):

```text
Meaning
-------
Your Mac cannot read the attached disk. The message alone does not tell us why.

Severity
--------
High

Likely causes
-------------
- A connection problem
- An unsupported or damaged file system

What to try
-----------
1. If the drive clicks or repeatedly disconnects, stop using it.
2. Inspect whether it appears in Disk Utility without running repairs.
3. Seek recovery advice if important files are not backed up.

Avoid
-----
Do not erase, format, or attempt repairs before protecting important data.
```

## Use copied text

Copy an error message with **Command+C**, then run:

```bash
macfix --clipboard
```

This sends the current clipboard **text** to Groq; it does not read copied images.

## Use a screenshot

For a saved screenshot, supply its path and describe what happened:

```bash
macfix --image ~/Desktop/error.png "This happens when I open the app"
```

Replace the path with your screenshot. Quote paths containing spaces:

```bash
macfix --image "$HOME/Desktop/Screenshot 1.png" "Why can't this app open?"
```

Or capture a new screenshot:

```bash
macfix --capture "My external drive isn't appearing"
```

Drag to select an area, review it in Preview, then return to Terminal and type `y` to send. Any other answer cancels. macOS may ask you to allow Screen Recording for Terminal.

Use one PNG or JPEG up to 8 MB with a description. Clipboard and capture require macOS. All input methods return the same five answer sections.

## Run it again later

In a new Terminal window, activate the environment before using `macfix`:

```bash
cd /path/to/macfix
source .venv/bin/activate
macfix "Permission denied"
```

You do not need to reinstall or re-enter your saved key. Run `macfix --help` for options.

Text and images are sent to Groq. Remove private information first. AI advice can be wrong; macfix never executes repairs. An internet connection and available API quota are required.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use mocked API calls and consume no Groq quota.
# Native Mac app

The new menu-bar app source and build instructions are in [native/](native/README.md).
It needs Apple's Command Line Tools to build; the Python CLI below remains available.

This is a small environment and IDE test project I built while transitioning from
Linux to Mac. It is intentionally lightweight and useful for trying native Mac
development, screenshots, keyboard shortcuts, Keychain storage, and a Groq API
workflow in one practical tool.
