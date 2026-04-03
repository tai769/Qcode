"""Workspace-safe file and shell helpers."""

from locale import getpreferredencoding
from pathlib import Path
import subprocess
from typing import Optional


MAX_OUTPUT_CHARS = 50000
DANGEROUS_PATTERNS = (
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "> /dev/",
    "mkfs",
)


class Workspace:
    """Encapsulates safe access to the current workspace."""

    def __init__(
        self,
        root: Path,
        shell_timeout: int = 120,
        max_output_chars: int = MAX_OUTPUT_CHARS,
    ) -> None:
        self.root = root.resolve()
        self.shell_timeout = shell_timeout
        self.max_output_chars = max_output_chars

    def safe_path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"Path escapes workspace: {relative_path}") from exc
        return candidate

    def run_bash(self, command: str, timeout_seconds: Optional[int] = None) -> str:
        if any(pattern in command for pattern in DANGEROUS_PATTERNS):
            return "Error: Dangerous command blocked"

        resolved_timeout = timeout_seconds or self.shell_timeout

        try:
            result = subprocess.run(
                ["bash", "-lc", command],
                cwd=self.root,
                capture_output=True,
                text=False,
                timeout=resolved_timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: Timeout ({resolved_timeout}s)"

        output = (
            self._decode_bytes(result.stdout) + self._decode_bytes(result.stderr)
        ).strip() or "(no output)"
        if result.returncode != 0:
            output = f"{output}\n[exit code: {result.returncode}]"
        return output[: self.max_output_chars]

    def read_text(self, relative_path: str, limit: Optional[int] = None) -> str:
        raw = self.safe_path(relative_path).read_bytes()
        text = self._decode_bytes(raw)
        lines = text.splitlines()
        if limit is not None and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[: self.max_output_chars]

    def write_text(self, relative_path: str, content: str) -> str:
        file_path = self.safe_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {relative_path}"

    def replace_text(self, relative_path: str, old_text: str, new_text: str) -> str:
        file_path = self.safe_path(relative_path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {relative_path}"

        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {relative_path}"

    @staticmethod
    def _decode_bytes(raw: bytes) -> str:
        if not raw:
            return ""

        encodings = [
            "utf-8",
            "utf-8-sig",
            getpreferredencoding(False) or "utf-8",
        ]
        seen: set[str] = set()
        for encoding in encodings:
            normalized = encoding.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
