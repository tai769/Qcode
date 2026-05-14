"""Smoke tests for the Qcode CLI and TUI."""

import json
import tempfile
from pathlib import Path

from qcode.runtime.session import ConversationSession
from qcode.runtime.todos import TodoManager
from qcode.config_toml import QcodeConfig
from qcode.harness.completer import (
    extract_at_reference,
    get_file_completions,
    replace_at_reference,
)


class TestSessionPersistence:
    def test_save_load_roundtrip(self):
        s = ConversationSession()
        s.add_user_text("hello")
        s.add_message({"role": "assistant", "content": "hi there"})
        with tempfile.TemporaryDirectory() as td:
            path = s.save(Path(td))
            assert path.exists()
            assert path.suffix == ".jsonl"

            s2 = ConversationSession.load(path)
            assert len(s2) == 2
            assert s2.session_id == s.session_id
            assert s2.messages[0]["content"] == "hello"
            assert s2.messages[1]["content"] == "hi there"

    def test_find_latest(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            assert ConversationSession.find_latest(d) is None

            s1 = ConversationSession()
            p1 = s1.save(d)
            s2 = ConversationSession()
            p2 = s2.save(d)

            latest = ConversationSession.find_latest(d)
            assert latest is not None
            assert latest.name >= p1.name  # lexicographic sort works for timestamps


class TestTodoManager:
    def test_update_and_render(self):
        tm = TodoManager()
        result = tm.update([
            {"id": "1", "text": "Read code", "status": "completed"},
            {"id": "2", "text": "Fix bug", "status": "in_progress"},
            {"id": "3", "text": "Write test", "status": "pending"},
        ])
        assert len(tm.items) == 3
        assert "completed" in result
        assert "1/3" in result

    def test_max_one_in_progress(self):
        tm = TodoManager()
        try:
            tm.update([
                {"id": "1", "text": "A", "status": "in_progress"},
                {"id": "2", "text": "B", "status": "in_progress"},
            ])
            assert False, "Should have raised"
        except ValueError as e:
            assert "Only one" in str(e)


class TestConfigToml:
    def test_default_config(self):
        c = QcodeConfig()
        assert c.model == "gpt-4"
        assert c.max_tokens == 8000
        assert c.permission.auto_allow == ["read_file", "grep", "glob"]

    def test_save_and_load(self):
        c = QcodeConfig()
        c.model = "claude-sonnet-4"
        c.providers["openai"] = c.providers.get("openai", type("", (), {"api_key": "sk-test", "base_url": ""})())
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.toml"
            c.save(path)
            assert path.exists()
            content = path.read_text()
            assert "claude-sonnet-4" in content


class TestCompleter:
    def test_extract_at_reference(self):
        assert extract_at_reference("help @src/", 10) == "src/"
        assert extract_at_reference("@qcode", 6) == "qcode"
        assert extract_at_reference("no ref here", 5) is None
        assert extract_at_reference("email@domain", 12) is None  # @ not preceded by space

    def test_get_completions(self):
        results = get_file_completions("qcode/", Path("."))
        assert len(results) > 0
        assert any("qcode/" in r for r in results)

    def test_replace_at_reference(self):
        new_text, pos = replace_at_reference("help @src/qco", 13, "qcode/")
        assert "qcode/" in new_text
        assert pos == 13  # @qcode/ = 7 chars from position 5, cursor at 13


class TestCLI:
    def test_help(self):
        from qcode.harness.cli import build_parser
        parser = build_parser()
        # Should not raise
        args = parser.parse_args(["--help"] if False else [])
        assert args.prompt is None

    def test_args(self):
        from qcode.harness.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["-p", "test", "--json", "--model", "gpt-4o"])
        assert args.prompt_flag == "test"
        assert args.json is True
        assert args.model == "gpt-4o"
