import tempfile
import unittest
from pathlib import Path

from qcode.config import AppConfig
from qcode.config_profiles import render_profile_list


class ConfigProfileTests(unittest.TestCase):
    def test_app_config_uses_active_toml_profile_and_auth_json(self) -> None:
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
                        '[defaults]',
                        'max_tokens = 4096',
                        '',
                        '[profiles.default]',
                        'base_url = "https://example.com/v1"',
                        'model = "gpt-main"',
                        'api_wire_api = "responses"',
                        'reasoning_effort = "high"',
                        'verbosity = "high"',
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

            self.assertEqual(config.profile, "default")
            self.assertEqual(config.api_base_url, "https://example.com/v1")
            self.assertEqual(config.model, "gpt-main")
            self.assertEqual(config.api_wire_api, "responses")
            self.assertEqual(config.model_reasoning_effort, "high")
            self.assertEqual(config.model_verbosity, "high")
            self.assertEqual(config.api_key, "test-key")
            self.assertEqual(config.max_tokens, 4096)

    def test_app_config_can_select_profile_by_name(self) -> None:
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
                        'auth = "main"',
                        '',
                        '[profiles.fast]',
                        'base_url = "https://example.com/v1"',
                        'model = "gpt-fast"',
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

            config = AppConfig.from_env(workdir=root, profile="fast")

            self.assertEqual(config.profile, "fast")
            self.assertEqual(config.model, "gpt-fast")

    def test_render_profile_list_marks_active_profile(self) -> None:
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
                        '',
                        '[profiles.fast]',
                        'base_url = "https://example.com/v1"',
                        'model = "gpt-fast"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            rendered = render_profile_list(root, current_profile="fast")

            self.assertIn("* fast: gpt-fast", rendered)
            self.assertIn("- default: gpt-main", rendered)


if __name__ == "__main__":
    unittest.main()
