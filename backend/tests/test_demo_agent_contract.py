from app.demo import bot
from app.tools import TOOLS, call_tool
from app.voice import codex, gptlive
from integrations.local_session import LocalCallSession


def test_demo_uses_gptlive_and_persistent_phone_session():
    assert bot.gptlive is gptlive
    assert issubclass(bot.DemoCallSession, LocalCallSession)


def test_codex_voice_uses_canonical_tool_contract():
    assert codex.TOOLS is TOOLS
    assert codex.call_tool is call_tool


def test_demo_defines_no_prompt_or_tool_copy():
    assert not hasattr(bot, "VOICE_PROMPT")
    assert not hasattr(bot, "BRAIN_PREAMBLE")
    assert not hasattr(bot, "TOOLS")


def test_codex_composes_canonical_session_instructions():
    names = codex.run_call.__code__.co_names
    assert "instructions" in names
    assert "VOICE_PROMPT" in names
    assert "BRAIN_PREAMBLE" in names
