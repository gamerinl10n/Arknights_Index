"""Raw script ingestion and conservative, evidence-first retrieval. Python 3.11+."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path


from catalog import aliases
from search_queries import search, context_window, LANGUAGES


def connect(path, ephemeral=False):
    db = sqlite3.connect(path)
    if ephemeral:
        db.execute("PRAGMA journal_mode=MEMORY")
    db.row_factory = sqlite3.Row
    db.executescript(
        """
    CREATE TABLE IF NOT EXISTS stories(id TEXT PRIMARY KEY, lang TEXT, path TEXT, revision TEXT, source TEXT, raw TEXT);
    CREATE TABLE IF NOT EXISTS snapshots(story TEXT, revision TEXT, raw TEXT, PRIMARY KEY(story,revision));
    CREATE TABLE IF NOT EXISTS lines(id TEXT PRIMARY KEY, story TEXT, ordinal INTEGER, speaker TEXT, text TEXT, branch TEXT, hash TEXT);
    CREATE INDEX IF NOT EXISTS story_path_idx ON stories(path,lang);
    CREATE INDEX IF NOT EXISTS speaker_idx ON lines(speaker);
    CREATE INDEX IF NOT EXISTS story_idx ON lines(story,ordinal);
    """
    )
    return db


# A closing bracket inside a quoted attribute is text, not the command boundary.
COMMAND = re.compile(r'^\[(\w+)((?:"(?:\\.|[^"\\])*"|[^"\]])*)\](.*)$')
ATTR = re.compile(r'(\w+)\s*=\s*(?:"((?:\\.|[^"\\])*)"|([^,\s)]+))')
TEXT_TAGS = {"name", "multiline", "subtitle", "sticker", "narration", "decision"}


def command_parts(line):
    match = COMMAND.match(line.strip())
    if not match:
        return None
    prop, attrs, trailing = match.groups()
    prop = prop.lower()
    if prop == "name" and attrs.lstrip().startswith("="):
        attrs = "name" + attrs
    pairs = {
        m[0].lower(): (m[1] or m[2]).replace('\\"', '"') for m in ATTR.findall(attrs)
    }
    return prop, attrs, pairs, trailing


def parse(raw):
    branch = "main"
    for n, line in enumerate(raw.splitlines()):
        command = command_parts(line)
        if not command:
            continue
        prop, attrs, pairs, text = command
        if prop in ("predicate", "decision", "label", "gotolabel"):
            # Include the physical boundary so repeated labels cannot join scenes.
            branch = f"{prop}@{n}:{attrs.strip()}"
        if prop not in TEXT_TAGS:
            continue
        speaker = pairs.get("name", "") if prop in ("name", "multiline") else ""
        if prop == "decision":
            # One source row, with separate options; do not invent a speaker.
            text = "\n".join(pairs.get("options", "").split(";"))
        else:
            text = text or pairs.get("content", "") or pairs.get("text", "")
        if text.strip():
            yield n, speaker, re.sub(r"<[^>]*>", "", text).replace("\\n", "\n"), branch


def ingest(db, root, revision, source):
    """Validate entire batch before transactional replacement; raw snapshots stay in SQLite."""
    root = Path(root)
    batch = []
    excluded = []
    report = {
        "files": 0,
        "dialogue_lines": 0,
        "unparsed_text_lines": 0,
        "unsupported_text_tags": {},
        "excluded_documents": 0,
    }

    for lang, folder in LANGUAGES.items():
        for f in sorted((root / folder / "gamedata/story").rglob("*.txt")):
            if f.name == "avg_segment_report.txt":
                excluded.append(
                    f"{lang}:{f.relative_to(root / folder / 'gamedata/story').as_posix()}"
                )
                report["excluded_documents"] += 1
                continue
            raw = f.read_text(encoding="utf-8-sig")
            for line in raw.splitlines():
                command = command_parts(line)
                if command:
                    prop, _, pairs, trailing = command
                    if prop not in TEXT_TAGS and (
                        trailing.strip()
                        or pairs.get("text")
                        or pairs.get("content")
                        or pairs.get("options")
                    ):
                        counts = report["unsupported_text_tags"]
                        counts[prop] = counts.get(prop, 0) + 1
            rows = list(parse(raw))
            report["files"] += 1
            report["dialogue_lines"] += len(rows)
            report["unparsed_text_lines"] += sum(
                bool(x.strip()) and not x.lstrip().startswith(("[", "//"))
                for x in raw.splitlines()
            )
            path = f.relative_to(root / folder / "gamedata/story").as_posix()
            batch.append((lang, path, raw, rows))
    if not batch or not any(x[0] == "ko_KR" and x[3] for x in batch):
        raise ValueError("한국어 대사가 없는 입력입니다. 기존 데이터를 유지합니다.")
    old_count = db.execute("SELECT count(*) FROM lines").fetchone()[0]
    if old_count >= 100 and report["dialogue_lines"] < old_count * 0.8:
        raise ValueError("대사 수가 20% 이상 감소했습니다. 기존 데이터를 유지합니다.")
    current_ids = {f"{lang}:{path}" for lang, path, _, _ in batch}
    previous = list(db.execute("SELECT id,lang FROM stories WHERE source=?", (source,)))
    incoming_languages = {lang for lang, _, _, _ in batch}
    if {
        row["lang"] for row in previous if row["id"] not in excluded
    } - incoming_languages:
        raise ValueError(
            "기존 언어 자료가 통째로 누락되었습니다. 기존 데이터를 유지합니다."
        )
    retired = {row["id"] for row in previous} - current_ids - set(excluded)
    report["retired_files"] = len(retired)
    with db:
        # Only the current inventory is searchable; immutable raw snapshots remain.
        db.executemany(
            "DELETE FROM lines WHERE story=?",
            ((sid,) for sid in retired | set(excluded)),
        )
        db.executemany("DELETE FROM stories WHERE id=?", ((sid,) for sid in retired))
        for lang, path, raw, rows in batch:
            sid = f"{lang}:{path}"
            db.execute(
                "INSERT OR REPLACE INTO stories VALUES(?,?,?,?,?,?)",
                (sid, lang, path, revision, source, raw),
            )
            db.execute(
                "INSERT OR IGNORE INTO snapshots VALUES(?,?,?)", (sid, revision, raw)
            )
            db.execute("DELETE FROM lines WHERE story=?", (sid,))
            for n, speaker, text, branch in rows:
                digest = hashlib.sha256(
                    json.dumps([speaker, text, branch], ensure_ascii=False).encode()
                ).hexdigest()
                db.execute(
                    "INSERT INTO lines VALUES(?,?,?,?,?,?,?)",
                    (f"{sid}:{n}", sid, n, speaker, text, branch, digest),
                )
        db.execute(
            "CREATE TABLE IF NOT EXISTS import_status(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT)"
        )
        db.execute(
            "INSERT OR REPLACE INTO import_status VALUES(1,?)",
            (json.dumps({**report, "revision": revision, "source": source}),),
        )
    return sum(len(x[3]) for x in batch)
