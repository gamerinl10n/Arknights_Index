"""Shared bounded neighbour evidence; never a confirmed addressee."""

from catalog import aliases, character_id


def validate_mentions(speaker, target, mode, interlocutor):
    if mode not in ("all", "third_party_candidate"):
        raise ValueError("Invalid mention mode")
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
    # Both directions must lack the mentioned person's turn. A positive third
    # speaker is required; mere absence of the mentioned person is insufficient.
    exclusions = [f"{n} NOT IN ({marks})" for n in neighbours]
    if interlocutor:
        others = aliases(interlocutor, lang)
        other_marks = ",".join("?" for _ in others)
        evidence = [f"{n} IN ({other_marks})" for n in neighbours]
        evidence_args = others * 2
    else:
        own = aliases(speaker, lang)
        other_marks = ",".join("?" for _ in own)
        evidence = [f"({n} != '' AND {n} NOT IN ({other_marks}))" for n in neighbours]
        evidence_args = own * 2
    predicate = " AND ".join(exclusions) + " AND (" + " OR ".join(evidence) + ")"
    return "0", [], predicate, names * 2 + evidence_args
