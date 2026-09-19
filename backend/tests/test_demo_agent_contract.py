from app.demo import bot
from app.tools import TOOLS, call_tool
from app.voice import codex


def test_demo_imports_exact_scored_codex_module():
    assert bot.codex is codex
    assert bot.codex.run_call is codex.run_call


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
