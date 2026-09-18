#!/usr/bin/env python3
"""PreToolUse guard: agents may never make the final HackSpain submission.

Each team gets exactly ONE submission and it freezes the project. With --json
the CLI skips its own confirmation, so a single agent command would deliver.
This hook blocks any Bash command that runs `hackspain ... submit` without
`--draft`. Drafts and `--help` stay allowed. The final submit is done by a
human in their own terminal.

Exit 2 blocks the tool call and shows stderr to the agent.
"""

import json
import re
import sys

STRIP = "\"'`()${}"
BLOCK_MSG = (
    "BLOCKED by repo guardrail (.claude/hooks/guard_hackspain_submit.py): "
    "a final `hackspain submit` is one-shot; the team gets exactly ONE submission "
    "and it freezes the project. Agents may only run `hackspain submit --draft ...`. "
    "Save or refresh the draft, show the user `hackspain --json project show`, and "
    "ask them to run the final `hackspain submit` themselves in their own terminal."
)


def is_final_submit(command: str) -> bool:
    for segment in re.split(r"&&|\|\||[;|&\n]", command):
        tokens = [t.strip(STRIP) for t in segment.split()]
        names = [t.rsplit("/", 1)[-1] for t in tokens]
        if "hackspain" not in names:
            continue
        rest = tokens[names.index("hackspain") + 1 :]
        if "submit" not in rest:
            continue
        if not {"--draft", "--help", "-h"} & set(rest):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if isinstance(command, str) and is_final_submit(command):
        print(BLOCK_MSG, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
