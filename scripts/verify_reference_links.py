"""Verify source-linked occurrences against a pinned source checkout.

Checks provenance and explicit portrait commands, not semantic interpretation.
Never prints game dialogue. No database or source download is required.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import command_parts, parse
from languages import LANGUAGES
from search_references import reference_links


def verify(root):
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    checked = 0
    for link in reference_links():
        if link["revision"] != revision:
            raise ValueError("Reference evidence requires its pinned source revision")
        raw = (
            root / LANGUAGES[link["lang"]] / "gamedata/story" / link["path"]
        ).read_text(encoding="utf-8-sig")
        rows = {
            ordinal: (speaker, text, branch)
            for ordinal, speaker, text, branch in parse(raw)
        }
        for ordinal, expected in [
            (link["ordinal"], link["line_hash"]),
            (link["anchor_ordinal"], link["anchor_hash"]),
        ]:
            digest = hashlib.sha256(
                json.dumps(list(rows[ordinal]), ensure_ascii=False).encode()
            ).hexdigest()
            if digest != expected:
                raise ValueError("Reference evidence line hash mismatch")
        if link["expression"] not in rows[link["ordinal"]][1]:
            raise ValueError("Reference expression absent from original line")
        evidence = link["evidence"]
        command = command_parts(raw.splitlines()[evidence["ordinal"]])
        if not command or command[0] != "character":
            raise ValueError("Portrait source command missing")
        pairs = command[2]
        focus = int(pairs.get("focus", "1"))
        if (
            focus != evidence["focus"]
            or pairs.get("name" if focus == 1 else f"name{focus}") != evidence["asset"]
        ):
            raise ValueError("Focused portrait source mismatch")
        if not evidence["asset"].startswith(link["target_id"] + "_"):
            raise ValueError("Portrait identity is not the linked target")
        if rows[link["ordinal"]][2] != rows[link["anchor_ordinal"]][2]:
            raise ValueError("Reference evidence crosses a branch")
        checked += 1
    return {"source_checked_occurrences": checked, "issues": 0}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), ensure_ascii=False))
