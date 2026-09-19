#!/usr/bin/env python3
"""Write logos/marks/index.json: the gallery order for the brand page.
Current identity first, then the rest alphabetically by round of arrival."""
import json
from pathlib import Path

MARKS = Path(__file__).resolve().parent.parent / "logos" / "marks"
CURRENT = "dial-rose-ten"
names = sorted(p.stem for p in MARKS.glob("*.svg"))
names.remove(CURRENT)
(MARKS / "index.json").write_text(json.dumps([CURRENT, *names], indent=0) + "\n")
print(len(names) + 1, "marks indexed")
