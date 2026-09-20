"""Validated, atomically replaced Studio settings; missing files use call defaults."""

import os
import tempfile
from pathlib import Path

from app.voice.codex.settings import VoiceSettings

SETTINGS_PATH = Path("logs/demo/voice-settings.json")


def load_settings() -> VoiceSettings:
    try:
        data = SETTINGS_PATH.read_bytes()
    except FileNotFoundError:
        return VoiceSettings()
    # Invalid, inaccessible or unreadable files must stop activation, not reset preferences.
    return VoiceSettings.model_validate_json(data)


def save_settings(settings: VoiceSettings) -> VoiceSettings:
    validated = VoiceSettings.model_validate(settings.model_dump())
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=SETTINGS_PATH.parent,
            prefix=".voice-settings-", suffix=".tmp", delete=False,
        ) as file:
            temporary = Path(file.name)
            file.write(validated.model_dump_json() + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, SETTINGS_PATH)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return validated
