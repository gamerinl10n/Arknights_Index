"""Shared bounded neighbour evidence; never a confirmed addressee."""

from catalog import aliases, character_id


def validate_mentions(speaker, target, mode, interlocutor):
    if mode not in ("all", "third_party_candidate", "reference_candidates"):
        raise ValueError("Invalid mention mode")
    if mode == "reference_candidates":
        if not target or interlocutor:
            raise ValueError(
                "Reference search needs a target and no conversation-partner filter"
            )
        if speaker and (character_id(speaker) or speaker.casefold()) == (
            character_id(target) or target.casefold()
        ):
            raise ValueError("Choose a speaker different from the target")
        return
    if mode == "all":
        if interlocutor:
            raise ValueError("Interlocutor requires third-party mode")
        return
    people = [speaker, target] + ([interlocutor] if interlocutor else [])
    identities = [character_id(value) or value.casefold() for value in people]
    if not speaker or not target or len(set(identities)) != len(identities):
        raise ValueError(
            "Choose distinct speaker, mentioned character and surrounding speaker"
        )


def neighbour_sql(comparator, direction):
    # Keep the existing physical/text bounds and stop at the first other turn
    # or branch boundary. Unnamed turns yield no positive evidence.
    return f"""COALESCE((SELECT CASE WHEN n.branch=l.branch THEN n.speaker ELSE '' END
        FROM (SELECT speaker,branch,ordinal FROM lines WHERE story=l.story
        AND ordinal {comparator} l.ordinal AND ordinal BETWEEN l.ordinal-60 AND l.ordinal+60
        ORDER BY ordinal {direction} LIMIT 6) n
        WHERE n.speaker!=l.speaker OR n.branch!=l.branch
        ORDER BY n.ordinal {direction} LIMIT 1),'')"""


def relation_sql(speaker, target, lang, mode="all", interlocutor=""):
    """Return rank SQL/args and optional candidate predicate/args."""
    if mode == "reference_candidates":
        return (
            "(SELECT CASE WHEN json_extract(evidence,'$.status')='source_checked' THEN 3 WHEN json_extract(evidence,'$.basis')='same_line_name' THEN 1 ELSE 2 END FROM reference_hits WHERE id=l.id)",
            [],
            "",
            [],
        )
    if not speaker or not target:
        return "0", [], "", []
    names = aliases(target, lang)
    marks = ",".join("?" for _ in names)
    neighbours = [neighbour_sql("<", "DESC"), neighbour_sql(">", "ASC")]
    rank = " + ".join(
        f"CASE WHEN {n} IN ({marks}) THEN 1 ELSE 0 END" for n in neighbours
    )
    if mode == "all":
        return rank, names * 2, "", []
    # Encode each direction once: 1 = mentioned character, 2 = third speaker.
    # OR must be exactly 2: positive third-party evidence and no target turn.
    others = aliases(interlocutor, lang) if interlocutor else aliases(speaker, lang)
    other_marks = ",".join("?" for _ in others)
    evidence = (
        f"n.speaker IN ({other_marks})"
        if interlocutor
        else f"n.speaker != '' AND n.speaker NOT IN ({other_marks})"
    )
    flags = []
    predicate_args = []
    for comparator, direction in (("<", "DESC"), (">", "ASC")):
        flags.append(
            f"""COALESCE((SELECT CASE
            WHEN n.branch=l.branch AND n.speaker IN ({marks}) THEN 1
            WHEN n.branch=l.branch AND ({evidence}) THEN 2 ELSE 0 END
            FROM (SELECT speaker,branch,ordinal FROM lines WHERE story=l.story
            AND ordinal {comparator} l.ordinal AND ordinal BETWEEN l.ordinal-60 AND l.ordinal+60
            ORDER BY ordinal {direction} LIMIT 6) n
            WHERE n.speaker!=l.speaker OR n.branch!=l.branch
            ORDER BY n.ordinal {direction} LIMIT 1),0)"""
        )
        predicate_args.extend(names + others)
    return "0", [], f"(({flags[0]}) | ({flags[1]})) = 2", predicate_args
