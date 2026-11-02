"""Conservative build-time correspondences, not line-number or semantic guesses."""

from collections import Counter
import hashlib
import json
import struct
import zlib
from catalog import character_id

METHOD = "strict-command-structure-v2"
TARGET_LANGS = ("ko_KR", "ja_JP", "en_US")


def command_structure(raw):
    # Local import keeps legacy core -> search_queries imports acyclic.
    from core import command_parts, TEXT_TAGS

    localized = {"options", "content", "text"}
    return [
        (
            command[0],
            tuple(
                sorted(
                    (k, v)
                    for k, v in command[2].items()
                    if not (
                        command[0] in TEXT_TAGS
                        and (
                            k in localized
                            or (k == "name" and command[0] in {"name", "multiline"})
                        )
                    )
                )
            ),
        )
        for line in raw.splitlines()
        if (command := command_parts(line))
    ]


def text_slots(raw, rows):
    """Map parsed text to command positions; physical line offsets may differ."""
    from core import command_parts

    ordinals = {row[0] for row in rows}
    slots, choices = [], {}
    index = 0
    for ordinal, line in enumerate(raw.splitlines()):
        command = command_parts(line)
        if not command:
            continue
        if ordinal in ordinals:
            slots.append(index)
            if command[0] == "decision":
                choices[index] = len(command[2].get("options", "").split(";"))
        index += 1
    return slots, choices


def verified_pairs(source_raw, target_raw):
    from core import parse

    if command_structure(source_raw) != command_structure(target_raw):
        return None, "structure"
    source, target = list(parse(source_raw)), list(parse(target_raw))
    if not source or len(source) != len(target):
        return None, "text_count"
    source_slots, source_choices = text_slots(source_raw, source)
    target_slots, target_choices = text_slots(target_raw, target)
    if source_slots != target_slots:
        return None, "text_slots"
    pairs = []
    for slot, a, b in zip(source_slots, source, target, strict=True):
        left, right = character_id(a[1]), character_id(b[1])
        if left and right and left != right:
            return None, "speaker"
        if bool(a[1]) != bool(b[1]):
            return None, "speaker"
        # A translated semicolon may be punctuation or an extra option. Do not
        # guess the choice grouping; omit that row without shifting later rows.
        if source_choices.get(slot) == target_choices.get(slot):
            pairs.append((a[0], b[0]))
    if not pairs:
        return None, "decision_options"
    return pairs, "matched" if len(pairs) == len(source) else "partial"


def build_alignments(src, dst):
    dst.execute(
        """CREATE TABLE translation_alignments(
        path TEXT,lang TEXT,cn_story TEXT,target_story TEXT,
        cn_revision TEXT,target_revision TEXT,cn_hash TEXT,target_hash TEXT,
        method TEXT,ordinal_map BLOB,PRIMARY KEY(path,lang)) WITHOUT ROWID"""
    )
    stats = {lang: Counter() for lang in TARGET_LANGS}
    for cn_id, path, cn_revision, raw in src.execute(
        "SELECT id,path,revision,raw FROM stories WHERE lang='zh_CN' ORDER BY path"
    ):
        for lang in TARGET_LANGS:
            stats[lang]["source_files"] += 1
            row = src.execute(
                "SELECT id,revision,raw FROM stories WHERE path=? AND lang=?",
                (path, lang),
            ).fetchone()
            if not row:
                stats[lang]["unavailable_files"] += 1
                continue
            target_id, target_revision, translated = row
            if cn_revision != target_revision:
                stats[lang]["revision_files"] += 1
                continue
            pairs, status = verified_pairs(raw, translated)
            stats[lang][status + "_files"] += 1
            if pairs is None:
                continue
            # Persist the actual correspondence; physical offsets may differ.
            packed = b"".join(struct.pack("<II", a, b) for a, b in pairs)
            dst.execute(
                "INSERT INTO translation_alignments VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    path,
                    lang,
                    cn_id,
                    target_id,
                    cn_revision,
                    target_revision,
                    hashlib.sha256(raw.encode()).hexdigest(),
                    hashlib.sha256(translated.encode()).hexdigest(),
                    METHOD,
                    zlib.compress(packed),
                ),
            )
            stats[lang]["matched_rows"] += len(pairs)
            if status == "partial":
                from core import parse

                stats[lang]["excluded_choice_rows"] += len(list(parse(raw))) - len(
                    pairs
                )
    report = {lang: dict(counts) for lang, counts in stats.items()}
    row = dst.execute("SELECT payload FROM import_status WHERE id=1").fetchone()
    payload = json.loads(row[0]) if row else {}
    payload["translation_alignment"] = {"method": METHOD, "languages": report}
    dst.execute(
        "INSERT OR REPLACE INTO import_status VALUES(1,?)", (json.dumps(payload),)
    )
    return report


def attach_comparisons(db, items, search_lang, translation_lang):
    """Two batched queries per page/window; no raw archive or eager context fetch."""
    if not items:
        return
    counterpart = translation_lang if search_lang == "zh_CN" else "zh_CN"
    pair_lang = translation_lang if search_lang == "zh_CN" else search_lang
    exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='translation_alignments'"
    ).fetchone()
    for item in items:
        item["comparison"] = {"lang": counterpart, "status": "unsupported", "items": []}
    if not exists:
        return
    paths = list(dict.fromkeys(item["path"] for item in items))
    marks = ",".join("?" for _ in paths)
    available = {
        row["path"]: dict(row)
        for row in db.execute(
            f"""SELECT s.path,s.id AS counterpart_story,s.revision AS counterpart_revision,
            a.cn_revision,a.target_revision,a.method,a.ordinal_map
            FROM stories s LEFT JOIN translation_alignments a ON a.path=s.path AND a.lang=?
            WHERE s.lang=? AND s.path IN ({marks})""",
            [pair_lang, counterpart, *paths],
        )
    }
    maps, wanted, linked = {}, set(), []
    for item in items:
        result = item["comparison"]
        match = available.get(item["path"])
        if match is None:
            result["status"] = "unavailable"
            continue
        result["status"] = "unverified"
        if not match["ordinal_map"] or match["method"] != METHOD:
            continue
        source_revision, opposite_revision = (
            (match["cn_revision"], match["target_revision"])
            if search_lang == "zh_CN"
            else (match["target_revision"], match["cn_revision"])
        )
        if (
            item["revision"] != source_revision
            or match["counterpart_revision"] != opposite_revision
        ):
            continue
        path = item["path"]
        if path not in maps:
            pairs = struct.iter_unpack("<II", zlib.decompress(match["ordinal_map"]))
            maps[path] = (
                {a: b for a, b in pairs}
                if search_lang == "zh_CN"
                else {b: a for a, b in pairs}
            )
        target_ordinal = maps[path].get(item["ordinal"])
        if target_ordinal is None:
            continue
        key = (match["counterpart_story"], target_ordinal)
        wanted.add(key)
        linked.append((result, key))
    if not wanted:
        return
    values = ",".join("(?,?)" for _ in wanted)
    rows = {
        (row["story"], row["ordinal"]): dict(row)
        for row in db.execute(
            f"""WITH wanted(story,ordinal) AS (VALUES {values})
            SELECT l.id,l.story,l.ordinal,l.speaker,l.text,l.branch,l.hash,s.lang,s.path,s.revision,s.source FROM wanted w
            JOIN lines l ON l.story=w.story AND l.ordinal=w.ordinal
            JOIN stories s ON s.id=l.story""",
            [v for pair in wanted for v in pair],
        )
    }
    for result, key in linked:
        if key in rows:
            rows[key]["alignment_method"] = METHOD
            result.update(status="matched", items=[rows[key]], method=METHOD)
