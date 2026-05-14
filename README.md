# Qcode

AI coding agent with team collaboration — CLI + TUI.

## Quick Start

```bash
# Install
pip install -e .

# Interactive TUI
python -m qcode

# One-shot mode
python -m qcode "explain this function"
echo "refactor this" | python -m qcode -p -

# Resume last session
python -m qcode -c

# Specify working directory
python -m qcode --cwd ~/myproject
```

## Features

- **Multi-agent team**: Lead + coder/tester/reviewer/architect/devops/dba
- **Task graph**: Durable task state with role-based claiming
- **Verification loops**: Coder-tester cycles until checks pass
- **Session persistence**: Save/resume conversations
- **Permission system**: Confirm dangerous tool calls
- **Slash commands**: /help /clear /compact /model /team /task /verify /save /load

## Configuration

```bash
# ~/.qcode/config.toml
[default]
model = "gpt-4"
max_tokens = 8000

[provider.openai]
api_key = "sk-..."
base_url = "https://api.openai.com/v1"

[permission]
auto_allow = ["read_file", "grep", "glob"]
always_ask = ["bash", "write", "edit"]

[ui]
theme = "monokai"
auto_compact_at = 0.8
```

## Project Structure

```
qcode/
├── api/            # FastAPI Web API (future)
├── core/           # Core abstractions
├── harness/        # CLI + TUI entry points
│   ├── cli.py      # CLI argument parsing
│   ├── tui.py      # Textual TUI application
│   └── cli_legacy.py  # Legacy interactive CLI
├── providers/      # LLM provider adapters
├── runtime/        # Agent engine, session, tools
├── telemetry/      # Event logging
├── tools/          # Built-in tool implementations
└── utils/          # Utilities
```

## Environment Variables

```bash
QCODE_API_KEY=sk-...        # API key
QCODE_API_BASE_URL=...      # API base URL
QCODE_MODEL=gpt-4           # Default model
QCODE_MAX_TOKENS=8000       # Max output tokens
```
