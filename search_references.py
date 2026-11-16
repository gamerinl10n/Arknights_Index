"""Auditable reference candidates, never automatic referent/addressee assertions.

Anchor in an explicit name or the target's own turn; inspect at most three text
rows in either direction, within 60 physical rows, without crossing a branch.
No aliases are learned from these candidates and no game data is written.
"""

import json
import re

from catalog import aliases, character_id
from functools import lru_cache
from pathlib import Path

METHOD = "bounded-reference-candidates-v1"
# Language rules identify expressions, not identities. Query text can find an
# unlisted epithet without adding that epithet as a global character alias.
PATTERNS = {
    "ko_KR": r"(?:그|저|이)\s*(?:녀석|사람|아이|애|분|소녀|소년|여자|남자)|[가-힣A-Za-z0-9]{1,12}\s*(?:녀석|자식|놈|소녀|소년)|(?:리더|대장|꼬맹이|애송이)",
    "zh_CN": r"(?:这|那)(?:个|位|只)?(?:家伙|孩子|女孩|男孩|丫头|小子|人)|[\u4e00-\u9fff]{1,6}(?:小子|丫头)|(?:首领|队长|小姑娘)",
    "ja_JP": r"(?:あの|その|この)(?:子|人|少女|少年|女|男)|(?:あいつ|こいつ|そいつ|リーダー|隊長|お嬢ちゃん|小僧)",
    "en_US": r"\b(?:(?:that|this|the)\s+(?:kid|girl|boy|woman|man|brat|bastard|one|leader)|she|her|he|him|they|them|leader|captain)\b",
}
RULES = {lang: re.compile(pattern, re.IGNORECASE) for lang, pattern in PATTERNS.items()}


def expressions(text, names, lang, query=""):
    terms = []
    for name in names:
        pattern = re.escape(name)
        if name.isascii() and name[0].isalnum():
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        terms.extend(m.group() for m in re.finditer(pattern, text, re.IGNORECASE))
    terms.extend(m.group() for m in RULES[lang].finditer(text))
    if query and query in text:
        terms.append(query)
    return list(dict.fromkeys(terms))


def prepare_references(
    db, target, lang, speaker="", query="", spoilers=False, story=""
):
    """Connection-local hit index, filtered before counts and pagination.

    Keep one strongest/nearest anchor per line. Iterating anchors avoids scanning
    every dialogue for every pronoun. Mutable archives are never process-cached.
    """
    db.execute(
        "CREATE TEMP TABLE IF NOT EXISTS reference_hits("
        "id TEXT PRIMARY KEY,story TEXT,ordinal INTEGER,lang TEXT,evidence TEXT) WITHOUT ROWID"
    )
    db.execute("DELETE FROM reference_hits WHERE lang=?", (lang,))
    names = aliases(target, lang)
    speakers = set(aliases(speaker, lang)) if speaker else None
    clauses = ["s.lang=?"]
    args = [lang]
    if not spoilers:
        clauses.append(
            "EXISTS(SELECT 1 FROM stories kr WHERE kr.lang='ko_KR' AND kr.path=s.path)"
        )
    if story:
        clauses.append("s.path=?")
        args.append(story)
    clauses.append(
        "(l.speaker IN ("
        + ",".join("?" for _ in names)
        + ") OR "
        + " OR ".join("instr(lower(l.text),lower(?))>0" for _ in names)
        + ")"
    )
    args.extend(names + names)
    anchors = db.execute(
        "SELECT l.*,s.lang,s.path,s.revision,s.source FROM lines l JOIN stories s ON s.id=l.story WHERE "
        + " AND ".join(clauses)
        + " ORDER BY s.path,l.ordinal",
        args,
    )
    for anchor in anchors:
        if not anchor["branch"]:
            continue
        explicit = any(
            re.search(
                (
                    r"(?<!\w)" + re.escape(name) + r"(?!\w)"
                    if name.isascii()
                    else re.escape(name)
                ),
                anchor["text"],
                re.I,
            )
            for name in names
        )
        if not explicit and anchor["speaker"] not in names:
            continue
        candidates = [(anchor, 0)]
        for comparator, order in (("<", "DESC"), (">", "ASC")):
            for distance, row in enumerate(
                db.execute(
                    f"SELECT * FROM lines WHERE story=? AND ordinal {comparator} ? AND ordinal BETWEEN ? AND ? ORDER BY ordinal {order} LIMIT 3",
                    (
                        anchor["story"],
                        anchor["ordinal"],
                        anchor["ordinal"] - 60,
                        anchor["ordinal"] + 60,
                    ),
                ),
                1,
            ):
                if row["branch"] != anchor["branch"]:
                    break
                candidates.append((row, distance))
        for row, distance in candidates:
            if (
                not row["speaker"]
                or re.fullmatch(r"[?？\s]+", row["speaker"])
                or row["speaker"] in names
            ):
                continue
            if speakers is not None and row["speaker"] not in speakers:
                continue
            if query and query not in row["text"]:
                continue
            terms = expressions(row["text"], names, lang, query)
            if not terms:
                continue
            basis = (
                "same_line_name"
                if distance == 0 and explicit
                else "nearby_name" if explicit else "nearby_turn"
            )
            quality = (
                0 if basis == "same_line_name" else 1 if explicit else 2,
                distance,
                anchor["ordinal"],
            )
            previous = db.execute(
                "SELECT evidence FROM reference_hits WHERE id=?", (row["id"],)
            ).fetchone()
            if previous and tuple(json.loads(previous[0])["quality"]) <= quality:
                continue
            evidence = {
                "method": METHOD,
                "status": "candidate",
                "target": target,
                "expressions": terms,
                "basis": basis,
                "lang": lang,
                "quality": quality,
                "anchor": {
                    key: anchor[key]
                    for key in (
                        "id",
                        "story",
                        "ordinal",
                        "speaker",
                        "text",
                        "branch",
                        "path",
                        "lang",
                        "revision",
                        "source",
                        "hash",
                    )
                },
            }
            db.execute(
                "INSERT OR REPLACE INTO reference_hits VALUES(?,?,?,?,?)",
                (
                    row["id"],
                    row["story"],
                    row["ordinal"],
                    lang,
                    json.dumps(evidence, ensure_ascii=False),
                ),
            )

    documented_references(db, target, lang, speakers, query, spoilers, story)


@lru_cache(maxsize=1)
def reference_links():
    document = json.loads(
        (Path(__file__).parent / "reference-links.json").read_text(encoding="utf-8")
    )
    if document["schema"] != 1:
        raise ValueError("Unsupported reference-link schema")
    return document["links"]


def documented_references(db, target, lang, speakers, query, spoilers, story):
    """Reuse source-checked occurrence links only while their provenance matches.

    These are editorial occurrence-level links, never global character aliases.
    Portrait evidence does not rename the original anonymous speaker.
    """
    identity = character_id(target)
    for link in reference_links():
        if (
            link["target_id"] != identity
            or link["lang"] != lang
            or (story and link["path"] != story)
        ):
            continue
        metadata = db.execute(
            "SELECT * FROM stories WHERE lang=? AND path=? AND revision=? AND source=?",
            (lang, link["path"], link["revision"], link["source"]),
        ).fetchone()
        if not metadata:
            continue
        if (
            not spoilers
            and not db.execute(
                "SELECT 1 FROM stories WHERE lang='ko_KR' AND path=?", (link["path"],)
            ).fetchone()
        ):
            continue
        row = db.execute(
            "SELECT * FROM lines WHERE story=? AND ordinal=? AND hash=?",
            (metadata["id"], link["ordinal"], link["line_hash"]),
        ).fetchone()
        anchor = db.execute(
            "SELECT * FROM lines WHERE story=? AND ordinal=? AND hash=?",
            (metadata["id"], link["anchor_ordinal"], link["anchor_hash"]),
        ).fetchone()
        if (
            not row
            or not anchor
            or link["expression"] not in row["text"]
            or row["branch"] != anchor["branch"]
        ):
            continue
        if (
            not row["speaker"]
            or row["speaker"] in aliases(target, lang)
            or (speakers is not None and row["speaker"] not in speakers)
            or (query and query not in row["text"])
        ):
            continue
        evidence = {
            "method": "source-linked-reference-v1",
            "status": "source_checked",
            "target": target,
            "expressions": [link["expression"]],
            "basis": "portrait_response",
            "lang": lang,
            "quality": [-1, 0, anchor["ordinal"]],
            "source_evidence": link["evidence"],
            "anchor": {
                **{
                    key: anchor[key]
                    for key in (
                        "id",
                        "story",
                        "ordinal",
                        "speaker",
                        "text",
                        "branch",
                        "hash",
                    )
                },
                **{
                    key: metadata[key] for key in ("path", "lang", "revision", "source")
                },
            },
        }
        db.execute(
            "INSERT OR REPLACE INTO reference_hits VALUES(?,?,?,?,?)",
            (
                row["id"],
                row["story"],
                row["ordinal"],
                lang,
                json.dumps(evidence, ensure_ascii=False),
            ),
        )


def attach_references(db, items, normalized=False):
    """Visible page only; include original evidence even after verified translation."""
    for item in items:
        if normalized:
            rows = db.execute(
                "SELECT h.evidence FROM reference_origins o JOIN reference_hits h ON h.id=o.source_id WHERE o.story=? AND o.ordinal=? ORDER BY h.lang,h.ordinal",
                (item["story"], item["ordinal"]),
            )
        else:
            rows = db.execute(
                "SELECT evidence FROM reference_hits WHERE id=?", (item["id"],)
            )
        item["references"] = [json.loads(row[0]) for row in rows]
