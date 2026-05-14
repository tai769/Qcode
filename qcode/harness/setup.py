"""Interactive setup wizard — protocol-driven, freeform model IDs."""

from __future__ import annotations

import os
from typing import Optional

from qcode.config_toml import ProviderConfig, QcodeConfig
from qcode.providers.registry import PRESETS, SUGGESTED_MODELS


def run_setup() -> None:
    """Interactive CLI setup."""
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║        Qcode Setup Wizard        ║")
    print("  ╚══════════════════════════════════╝")
    print()

    cfg = QcodeConfig.load()

    # ── Step 1: Choose provider preset or custom ──
    print("  Choose a provider:\n")
    preset_keys = list(PRESETS.keys())
    for i, key in enumerate(preset_keys, 1):
        p = PRESETS[key]
        env_val = os.environ.get(p["env"], "")
        env_hint = " ✓ (env found)" if env_val else ""
        print(f"    {i}. {p['name']}  [{p['protocol']}]{env_hint}")
    print(f"    {len(preset_keys) + 1}. Custom (any OpenAI-compatible endpoint)")
    print(f"    {len(preset_keys) + 2}. Custom (any Anthropic-compatible endpoint)")
    print()

    choice = input(f"  Select [1-{len(preset_keys) + 2}]: ").strip() or "1"
    try:
        idx = int(choice) - 1
    except ValueError:
        idx = 0

    if idx < len(preset_keys):
        prov_key = preset_keys[idx]
        preset = PRESETS[prov_key]
        protocol = preset["protocol"]
        default_url = preset["base_url"]
        env_key = preset["env"]
        prov_name = preset["name"]
    elif idx == len(preset_keys):
        protocol = "openai"
        default_url = ""
        env_key = ""
        prov_name = "custom-openai"
        prov_key = "custom-openai"
    else:
        protocol = "anthropic"
        default_url = ""
        env_key = ""
        prov_name = "custom-anthropic"
        prov_key = "custom-anthropic"

    # ── Step 2: API Key ──
    env_val = os.environ.get(env_key, "") if env_key else ""
    if env_val:
        print(f"\n  Found {env_key} in environment.")
        api_key = input(f"  API Key [use env]: ").strip() or env_val
    else:
        api_key = input(f"\n  API Key: ").strip()

    if not api_key:
        print("\n  Error: API key is required.")
        return

    # ── Step 3: Base URL (for custom or override) ──
    if not default_url:
        base_url = input(f"\n  Base URL (e.g. https://api.example.com/v1): ").strip()
        if not base_url:
            print("  Error: Base URL is required for custom providers.")
            return
    else:
        override_url = input(f"\n  Base URL [{default_url}]: ").strip()
        base_url = override_url or default_url

    # ── Step 4: Model ID (freeform) ──
    suggestions = SUGGESTED_MODELS.get(prov_key, SUGGESTED_MODELS.get(prov_key.split("-")[0], []))
    if suggestions:
        print(f"\n  Suggested models for {prov_name}:")
        for i, m in enumerate(suggestions[:5], 1):
            print(f"    {i}. {m}")
        print(f"\n  Enter a model ID (or number to pick from above)")
    else:
        print(f"\n  Enter any model ID your provider supports")

    model_input = input(f"  Model: ").strip()

    # Check if user entered a number
    try:
        model_idx = int(model_input) - 1
        if 0 <= model_idx < len(suggestions):
            model = suggestions[model_idx]
        else:
            model = model_input
    except ValueError:
        model = model_input

    if not model:
        if suggestions:
            model = suggestions[0]
            print(f"  Using default: {model}")
        else:
            print("  Error: Model ID is required.")
            return

    # ── Step 5: Save ──
    cfg.provider = prov_key
    cfg.model = model
    cfg.providers[prov_key] = ProviderConfig(
        protocol=protocol,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    path = cfg.save()
    print()
    print(f"  ✓ Saved to {path}")
    print(f"    Protocol: {protocol}")
    print(f"    Provider: {prov_name} ({prov_key})")
    print(f"    Model:    {model}")
    print(f"    URL:      {base_url}")
    print()
    print("  Run 'qcode' to start!")
    print()
