import tempfile
import unittest
from pathlib import Path

from qcode.app import build_cli_harness
from qcode.config import AppConfig


class ModelSwitchingTests(unittest.TestCase):
    def test_slash_model_switches_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcode_dir = root / ".qcode"
            qcode_dir.mkdir(parents=True, exist_ok=True)
            (qcode_dir / "config.toml").write_text(
                "\n".join(
                    [
                        'version = 1',
                        'active_profile = "default"',
                        '',
                        '[profiles.default]',
                        'base_url = "https://example.com/v1"',
                        'model = "gpt-main"',
                        'api_wire_api = "responses"',
                        'auth = "main"',
                        '',
                        '[profiles.fast]',
                        'base_url = "https://example.com/v1"',
                        'model = "gpt-fast"',
                        'api_wire_api = "responses"',
                        'auth = "main"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (qcode_dir / "auth.json").write_text(
                '{"version":1,"auth":{"main":{"api_key":"test-key"}}}\n',
                encoding="utf-8",
            )

            config = AppConfig.from_env(workdir=root)
            harness = build_cli_harness(config)

            before = harness._handle_slash_command("/model")
            switch_result = harness._handle_slash_command("/model fast")
            after = harness._handle_slash_command("/model")
            models = harness._handle_slash_command("/models")

            self.assertIn("gpt-main", before or "")
            self.assertIn("Switched model to gpt-fast", switch_result or "")
            self.assertEqual(harness.config.profile, "fast")
            self.assertEqual(harness.config.model, "gpt-fast")
            self.assertIn("gpt-fast", after or "")
            self.assertIn("default: gpt-main", models or "")
            self.assertIn("fast: gpt-fast", models or "")


if __name__ == "__main__":
    unittest.main()
