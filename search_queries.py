"""Bounded SQLite retrieval. Physical neighbours never establish addressees."""

from catalog import aliases

LANGUAGES = {"ko_KR": "kr", "zh_CN": "cn", "ja_JP": "jp", "en_US": "en"}


def search(
    db,
    speaker="",
    target="",
    query="",
    lang="ko_KR",
    spoilers=False,
    offset=0,
    story="",
    include_details=True,
):
    if lang not in LANGUAGES:
        raise ValueError("지원하지 않는 언어")
    clauses = ["s.lang=?"]
    args = [lang]
    if speaker:
        names = aliases(speaker, lang)
        clauses.append("l.speaker IN (" + ",".join("?" for _ in names) + ")")
        args.extend(names)
    if query:
        clauses.append("instr(l.text,?)>0")
        args.append(query)
    if not spoilers:
        clauses.append(
            "EXISTS(SELECT 1 FROM stories kr WHERE kr.lang='ko_KR' AND kr.path=s.path)"
        )
    if target:
        names = aliases(target, lang)
        clauses.append("(" + " OR ".join("instr(l.text,?)>0" for _ in names) + ")")
        args += names
    where = " AND ".join(clauses)
    facets = [
        dict(row)
        for row in db.execute(
            f"SELECT s.path,count(*) AS count FROM lines l JOIN stories s ON s.id=l.story WHERE {where} GROUP BY s.path ORDER BY s.path",
            args,
        )
    ]
    if story:
        where += " AND s.path=?"
        args.append(story)
    total = sum(row["count"] for row in facets if not story or row["path"] == story)
    # Unscoped word searches scan once for facets, then read only the files on this page.
    page_offset = offset
    if not speaker:
        paths = []
        needed = 50
        for facet in facets:
            if story and facet["path"] != story:
                continue
            if page_offset >= facet["count"]:
                page_offset -= facet["count"]
                continue
            paths.append(facet["path"])
            needed -= facet["count"] - (page_offset if len(paths) == 1 else 0)
            if needed <= 0:
                break
        if not paths:
            return {"total": total, "items": [], "stories": facets}
        where += " AND s.path IN (" + ",".join("?" for _ in paths) + ")"
        args.extend(paths)
    # Rank the complete match set before pagination, never just the visible page.
    # Nearby turns are evidence for ordering, not proof of an addressee.
    rank_sql = "0"
    rank_args = []
    if speaker and target:
        target_names = aliases(target, lang)
        placeholders = ",".join("?" for _ in target_names)
        turns = []
        for comparator, direction in (("<", "DESC"), (">", "ASC")):
            turns.append(
                f"""COALESCE((SELECT CASE WHEN n.branch=l.branch AND n.speaker IN ({placeholders}) THEN 1 ELSE 0 END
                FROM (SELECT speaker,branch,ordinal FROM lines WHERE story=l.story
                AND ordinal {comparator} l.ordinal AND ordinal BETWEEN l.ordinal-60 AND l.ordinal+60
                ORDER BY ordinal {direction} LIMIT 6) n
                WHERE n.speaker!=l.speaker OR n.branch!=l.branch ORDER BY n.ordinal {direction} LIMIT 1),0)"""
            )
            rank_args.extend(target_names)
        rank_sql = " + ".join(turns)
    rows = db.execute(
        f"SELECT l.id,l.story,l.ordinal,l.speaker,l.text,l.branch,l.hash,s.lang,s.path,s.revision,s.source,({rank_sql}) AS nearby_turns FROM lines l JOIN stories s ON s.id=l.story WHERE {where} ORDER BY nearby_turns DESC,s.path,l.ordinal LIMIT 50 OFFSET ?",
        rank_args + args + [page_offset],
    ).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        # Physical neighbours are explicitly not inferred conversation partners.
        if not include_details:
            results.append(item)
            continue
        item["context"] = [
            dict(r)
            for r in db.execute(
                "SELECT speaker,text,branch,ordinal FROM (SELECT speaker,text,branch,ordinal FROM lines WHERE story=? AND ordinal<? ORDER BY ordinal DESC LIMIT 3) UNION ALL SELECT speaker,text,branch,ordinal FROM (SELECT speaker,text,branch,ordinal FROM lines WHERE story=? AND ordinal>=? ORDER BY ordinal LIMIT 4) ORDER BY ordinal",
                (row["story"], row["ordinal"], row["story"], row["ordinal"]),
            )
        ]
        item["parallel"] = [
            dict(r)
            for r in db.execute(
                "SELECT l.speaker,l.text,s.lang FROM lines l JOIN stories s ON s.id=l.story WHERE s.path=? AND l.ordinal=? AND s.lang!=?",
                (row["path"], row["ordinal"], lang),
            )
        ]
        results.append(item)
    return {"total": total, "items": results, "stories": facets}


def context_window(db, story, ordinal, radius=15, parallel=False):
    row = db.execute("SELECT path,lang FROM stories WHERE id=?", (story,)).fetchone()
    if not row:
        raise ValueError("Story not found")
    radius = max(3, min(100, radius))
    before = db.execute(
        "SELECT speaker,text,branch,ordinal FROM lines WHERE story=? AND ordinal<? ORDER BY ordinal DESC LIMIT ?",
        (story, ordinal, radius),
    ).fetchall()
    after = db.execute(
        "SELECT speaker,text,branch,ordinal FROM lines WHERE story=? AND ordinal>=? ORDER BY ordinal LIMIT ?",
        (story, ordinal, radius + 1),
    ).fetchall()
    rows = list(reversed(before)) + list(after)
    result = {
        "items": [dict(r) for r in rows],
        "has_more": len(before) == radius or len(after) == radius + 1,
    }
    if parallel:
        result["parallel"] = [
            dict(r)
            for r in db.execute(
                "SELECT l.speaker,l.text,s.lang FROM lines l JOIN stories s ON s.id=l.story WHERE s.path=? AND l.ordinal=? AND s.lang!=?",
                (row["path"], ordinal, row["lang"]),
            )
        ]
    return result
