"""Read-only metadata audit; choices are never attributed to the Doctor."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import aliases
from languages import LANGUAGES


def audit(db):
    report = {
        "scope": "Korean-file release approximation; physical +/-30 source rows",
        "languages": {},
    }
    report["source_revisions"] = sorted(
        row[0] for row in db.execute("SELECT DISTINCT revision FROM stories")
    )
    for lang in LANGUAGES:
        speakers, targets = aliases("켈시", lang), aliases("M3", lang)
        sql = (
            "SELECT l.story,l.ordinal,l.branch FROM lines l JOIN stories s ON s.id=l.story WHERE s.lang=? AND l.speaker IN ("
            + ",".join("?" for _ in speakers)
            + ") AND ("
            + " OR ".join("instr(l.text,?)>0" for _ in targets)
            + ") AND EXISTS(SELECT 1 FROM stories kr WHERE kr.lang='ko_KR' AND kr.path=s.path)"
        )
        hits = db.execute(sql, [lang, *speakers, *targets]).fetchall()
        counts = {
            "matching_lines": len(hits),
            "with_choice_within_30_rows": 0,
            "with_named_doctor_within_30_rows": 0,
            "with_named_doctor_same_branch_within_30_rows": 0,
        }
        names = aliases("Doctor", lang)
        for hit in hits:
            rows = db.execute(
                "SELECT ordinal,speaker,branch FROM lines WHERE story=? AND ordinal BETWEEN ? AND ?",
                (hit["story"], hit["ordinal"] - 30, hit["ordinal"] + 30),
            ).fetchall()
            counts["with_choice_within_30_rows"] += any(
                row["branch"]
                and row["branch"].startswith(f"decision@{row['ordinal']}:")
                for row in rows
            )
            doctors = [row for row in rows if row["speaker"] in names]
            counts["with_named_doctor_within_30_rows"] += bool(doctors)
            counts["with_named_doctor_same_branch_within_30_rows"] += any(
                row["branch"] == hit["branch"] for row in doctors
            )
        report["languages"][lang] = counts
    report["interpretation"] = (
        "Nearby choices and named speakers are structural observations, not confirmed addressees or Doctor attribution."
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    args = parser.parse_args()
    with closing(
        sqlite3.connect(Path(args.database).resolve().as_uri() + "?mode=ro", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        print(json.dumps(audit(db), ensure_ascii=False, indent=2))
