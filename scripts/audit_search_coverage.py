"""Audit a local imported archive read-only; emit counts, never game dialogue."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import LANGUAGES, TEXT_TAGS, command_parts, parse


def audit(db):
    indexed = dict(db.execute("SELECT story, count(*) FROM lines GROUP BY story"))
    languages = {}
    revisions = set()
    issues = Counter()
    for lang, raw, revision, story_id in db.execute(
        "SELECT lang, raw, revision, id FROM stories ORDER BY lang, id"
    ):
        if lang not in LANGUAGES:
            raise ValueError("Unsupported archive language")
        stat = languages.setdefault(
            lang,
            {
                "files": 0,
                "parsed_rows": 0,
                "indexed_rows": 0,
                "unparsed_noncommand_lines": 0,
                "malformed_command_lines": 0,
                "unsupported_text_commands": Counter(),
            },
        )
        revisions.add(revision)
        parsed = sum(1 for _ in parse(raw))
        stored = indexed.pop(story_id, 0)
        stat["files"] += 1
        stat["parsed_rows"] += parsed
        stat["indexed_rows"] += stored
        if parsed != stored:
            issues["parser_index_count_mismatch_files"] += 1
        for line in raw.splitlines():
            text = line.strip()
            if not text or text.startswith("//"):
                continue
            command = command_parts(line)
            if not command:
                key = (
                    "malformed_command_lines"
                    if text.startswith("[")
                    else "unparsed_noncommand_lines"
                )
                stat[key] += 1
                continue
            tag, _, attrs, trailing = command
            if tag not in TEXT_TAGS and (
                trailing.strip()
                or any(attrs.get(key) for key in ("text", "content", "options"))
            ):
                stat["unsupported_text_commands"][tag] += 1
    if indexed:
        issues["orphan_indexed_stories"] = len(indexed)
    if not languages:
        issues["empty_archive"] = 1
    for stat in languages.values():
        stat["unsupported_text_commands"] = dict(
            sorted(stat["unsupported_text_commands"].items())
        )
    return {
        "scope": "active imported archive; possible text omissions are diagnostics, not confirmed missing dialogue",
        "release_scope": "Korean story-file presence remains a release-scope approximation",
        "source_revisions": sorted(revisions),
        "languages": dict(sorted(languages.items())),
        "issues": dict(issues),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with sqlite3.connect(args.archive.resolve().as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Invalid archive")
        report = audit(db)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf8")
    else:
        print(text, end="")
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
