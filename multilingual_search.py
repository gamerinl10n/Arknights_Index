"""Cross-corpus literal search with verified identity, bounded result payloads."""

from itertools import groupby
import struct
import zlib
from catalog import aliases
from search_queries import LANGUAGES, search
from translation_alignment import METHOD, TARGET_LANGS, attach_comparisons


def variants(db, items):
    """Attach verified variants only; never join physical line numbers."""
    for item in items:
        item["variants"] = {item["lang"]: dict(item)}
    for source_lang in LANGUAGES:
        group = [item for item in items if item["lang"] == source_lang]
        if not group:
            continue
        if source_lang == "zh_CN":
            originals = group
        else:
            attach_comparisons(db, group, source_lang, "ko_KR")
            originals = []
            for item in group:
                comparison = item.pop("comparison")
                if comparison["items"]:
                    original = comparison["items"][0]
                    item["variants"]["zh_CN"] = dict(original)
                    originals.append(original)
        for target_lang in TARGET_LANGS:
            attach_comparisons(db, originals, "zh_CN", target_lang)
            for original in originals:
                comparison = original.pop("comparison")
                if comparison["items"]:
                    original.setdefault("_variants", {})[target_lang] = comparison[
                        "items"
                    ][0]
        by_key = {(row["story"], row["ordinal"]): row for row in originals}
        for item in group:
            original = item if source_lang == "zh_CN" else item["variants"].get("zh_CN")
            if original:
                found = by_key[(original["story"], original["ordinal"])]
                item["variants"].update(found.get("_variants", {}))
        for original in originals:
            original.pop("_variants", None)


def search_all(
    db,
    speaker="",
    target="",
    query="",
    lang="ko_KR",
    spoilers=False,
    offset=0,
    story="",
    include_details=False,
):
    if lang not in LANGUAGES:
        raise ValueError("Unsupported language")
    # Character-only searches already resolve official aliases in the main corpus.
    if not query:
        result = search(
            db,
            speaker,
            target,
            query,
            lang,
            spoilers,
            offset,
            story,
            include_details=False,
        )
        variants(db, result["items"])
        return result
    has_alignment = db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='translation_alignments'"
    ).fetchone()
    db.execute(
        "CREATE TEMP TABLE IF NOT EXISTS multilingual_hits(story TEXT,ordinal INTEGER,rank INTEGER,PRIMARY KEY(story,ordinal)) WITHOUT ROWID"
    )
    db.execute("DELETE FROM multilingual_hits")
    clauses, args = [], []
    for corpus in LANGUAGES:
        where = ["s.lang=?", "instr(l.text,?)>0"]
        values = [corpus, query]
        if speaker:
            names = aliases(speaker, corpus)
            where.append("l.speaker IN (" + ",".join("?" for _ in names) + ")")
            values.extend(names)
        if target:
            names = aliases(target, corpus)
            where.append("(" + " OR ".join("instr(l.text,?)>0" for _ in names) + ")")
            values.extend(names)
        if not spoilers:
            where.append(
                "EXISTS(SELECT 1 FROM stories kr WHERE kr.lang='ko_KR' AND kr.path=s.path)"
            )
        if story:
            where.append("s.path=?")
            values.append(story)
        rank = "0"
        rank_args = []
        if speaker and target:
            turns = []
            for comparator, direction in (("<", "DESC"), (">", "ASC")):
                marks = ",".join("?" for _ in names)
                turns.append(
                    f"""COALESCE((SELECT CASE WHEN n.branch=l.branch AND n.speaker IN ({marks}) THEN 1 ELSE 0 END
                FROM (SELECT speaker,branch,ordinal FROM lines WHERE story=l.story
                AND ordinal {comparator} l.ordinal AND ordinal BETWEEN l.ordinal-60 AND l.ordinal+60
                ORDER BY ordinal {direction} LIMIT 6) n
                WHERE n.speaker!=l.speaker OR n.branch!=l.branch ORDER BY n.ordinal {direction} LIMIT 1),0)"""
                )
                rank_args.extend(names)
            rank = " + ".join(turns)
        clauses.append(
            "SELECT l.story,l.ordinal,s.path,s.lang,s.revision,("
            + rank
            + ") AS rank FROM lines l JOIN stories s ON s.id=l.story WHERE "
            + " AND ".join(where)
        )
        args.extend(rank_args + values)
    # Stream matches by file. Keep only that file's maps in memory; deduplicate in
    # a connection-local temporary table instead of retaining the corpus in Python.
    cursor = db.execute(
        "SELECT * FROM (" + " UNION ALL ".join(clauses) + ") ORDER BY path", args
    )
    for path, matches in groupby(cursor, key=lambda row: row["path"]):
        # Buffer one file, not the whole match set. Read only the maps needed to
        # connect foreign hits to the display language, and insert each identity once.
        hits = list(matches)
        foreign = {row["lang"] for row in hits} - {lang}
        metadata, maps = {}, {}
        if foreign and has_alignment:
            metadata = {
                row["lang"]: dict(row)
                for row in db.execute(
                    "SELECT id,lang,revision FROM stories WHERE path=?", (path,)
                )
            }
            needed = (foreign | {lang}) - {"zh_CN"}
            marks = ",".join("?" for _ in needed)
            for pair in db.execute(
                f"SELECT lang,method,cn_revision,target_revision,ordinal_map FROM translation_alignments WHERE path=? AND lang IN ({marks})",
                [path, *sorted(needed)],
            ):
                cn, translated = metadata.get("zh_CN"), metadata.get(pair["lang"])
                if (
                    not cn
                    or not translated
                    or pair["method"] != METHOD
                    or cn["revision"] != pair["cn_revision"]
                    or translated["revision"] != pair["target_revision"]
                ):
                    continue
                pairs = dict(
                    struct.iter_unpack("<II", zlib.decompress(pair["ordinal_map"]))
                )
                maps[pair["lang"]] = (pairs, {b: a for a, b in pairs.items()})
        identities = {}
        for row in hits:
            source_lang, ordinal, source_story = (
                row["lang"],
                row["ordinal"],
                row["story"],
            )
            cn_ordinal = (
                ordinal
                if source_lang == "zh_CN"
                else maps.get(source_lang, ({}, {}))[1].get(ordinal)
            )
            main_story, main_ordinal = source_story, ordinal
            if source_lang != lang and cn_ordinal is not None and metadata:
                destination = (
                    cn_ordinal
                    if lang == "zh_CN"
                    else maps.get(lang, ({}, {}))[0].get(cn_ordinal)
                )
                if destination is not None:
                    main_story, main_ordinal = metadata[lang]["id"], destination
                else:
                    main_story, main_ordinal = metadata["zh_CN"]["id"], cn_ordinal
            key = (main_story, main_ordinal)
            identities[key] = max(identities.get(key, 0), row["rank"])
        db.executemany(
            "INSERT INTO multilingual_hits VALUES(?,?,?)",
            [
                (story_id, ordinal, rank)
                for (story_id, ordinal), rank in identities.items()
            ],
        )
    total = db.execute("SELECT count(*) FROM multilingual_hits").fetchone()[0]
    # Select the page before reading dialogue bodies; keep the final order explicit.
    rows = db.execute(
        """SELECT l.*,s.lang,s.path,s.revision,s.source,s.rank AS nearby_turns
        FROM (
            SELECT h.story,h.ordinal,h.rank,s.lang,s.path,s.revision,s.source
            FROM multilingual_hits h JOIN stories s ON s.id=h.story
            ORDER BY h.rank DESC,s.path,h.ordinal,s.lang LIMIT 50 OFFSET ?
        ) s JOIN lines l ON l.story=s.story AND l.ordinal=s.ordinal
        ORDER BY s.rank DESC,s.path,l.ordinal,s.lang""",
        (offset,),
    )
    items = [dict(row) for row in rows]
    variants(db, items)
    for item in items:
        item["main_language_missing"] = item["lang"] != lang
    return {"total": total, "items": items, "stories": []}
