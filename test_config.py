import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from macfix.config import get_api_key


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '.env'
        env = patch.dict(os.environ, {}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        location = patch('macfix.config.ENV_FILE', self.path)
        location.start()
        self.addCleanup(location.stop)

    def test_saved_key_and_quotes(self):
        for value in ('test-key', '"test-key"', "'test-key'"):
            self.path.write_text(f'# comment\nOTHER=ignored\nGROQ_API_KEY={value}\n')
            self.assertEqual(get_api_key(), 'test-key')

    def test_environment_overrides_file(self):
        self.path.write_text('GROQ_API_KEY=file-key\n')
        with patch.dict(os.environ, {'GROQ_API_KEY': 'env-key'}):
            self.assertEqual(get_api_key(), 'env-key')

    def test_missing_empty_and_unrelated(self):
        self.assertEqual(get_api_key(), '')
        for content in ('', 'GROQ_API_KEY=\n', 'OTHER=value\n'):
            self.path.write_text(content)
            self.assertEqual(get_api_key(), '')

    def test_file_reread_after_edit(self):
        self.path.write_text('GROQ_API_KEY=first\n')
        self.assertEqual(get_api_key(), 'first')
        self.path.write_text('GROQ_API_KEY=second\n')
        self.assertEqual(get_api_key(), 'second')
