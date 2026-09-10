"""Read the single API key from the environment or this installation's .env."""

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def get_api_key() -> str:
    # An explicit environment setting overrides the file, including an empty value.
    if "GROQ_API_KEY" in os.environ:
        return os.environ["GROQ_API_KEY"].strip()
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return ""
    for line in lines:
        name, separator, value = line.strip().partition("=")
        if separator and name.strip() == "GROQ_API_KEY":
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value.strip()
    return ""
