from pathlib import Path

from django.test import SimpleTestCase

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


class EnvExampleTests(SimpleTestCase):
    def test_env_example_sem_bom(self):
        self.assertFalse(ENV_EXAMPLE.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_env_example_define_banco(self):
        self.assertIn(
            "DJANGO_DB_PATH=db.sqlite3",
            ENV_EXAMPLE.read_text(encoding="utf-8"),
        )
