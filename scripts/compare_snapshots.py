"""Compare lossless snapshot storage and public search responses; no dialogue output."""

import argparse
from contextlib import closing
import json
from itertools import zip_longest
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


def compare(before, after):
    report = {}
    with closing(sqlite3.connect(before)) as a, closing(sqlite3.connect(after)) as b:
        for db in (a, b):
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Snapshot integrity failed")
        for table, columns, order in [
            ("lines", "id,story,ordinal,speaker,text,branch,hash", "story,ordinal"),
            ("stories", "*", "id"),
            ("translation_alignments", "*", "path,lang"),
            ("suggestion_counts", "*", "lang,spoilers,speaker"),
            ("import_status", "*", "id"),
        ]:
            sql = f"SELECT {columns} FROM {table} ORDER BY {order}"
            count = 0
            for left, right in zip_longest(a.execute(sql), b.execute(sql)):
                if left != right:
                    raise ValueError(f"{table}: row mismatch at {count}")
                count += 1
            report[table] = count
    clients = [
        create_app(str(Path(p).resolve()), readonly=True).test_client()
        for p in (before, after)
    ]
    cases = []
    for lang in ("ko_KR", "zh_CN", "ja_JP", "en_US"):
        for spoilers in ("0", "1"):
            cases.append(("/api/suggestions", {"lang": lang, "spoilers": spoilers}))
            for query in (
                {"speaker": "M3", "target": "켈시"},
                {"speaker": "아미야"},
                {"q": "zzzznotfound"},
                {"q": "你好", "all_languages": "1"},
                {"q": "안녕", "all_languages": "1", "offset": "50"},
            ):
                cases.append(
                    (
                        "/api/search",
                        dict(query, lang=lang, spoilers=spoilers, details="0"),
                    )
                )
    for lang in ("ko_KR", "zh_CN", "ja_JP", "en_US"):
        for translation in ("ko_KR", "ja_JP", "en_US"):
            cases.append(
                (
                    "/api/search",
                    {
                        "speaker": "M3",
                        "lang": lang,
                        "compare": "1",
                        "translation_lang": translation,
                    },
                )
            )
    for route, params in cases:
        responses = [client.get(route, query_string=params) for client in clients]
        if (
            any(r.status_code != 200 for r in responses)
            or responses[0].json != responses[1].json
        ):
            raise ValueError(f"API mismatch: {route} {params}")
        if route == "/api/search":
            for item in responses[0].json["items"][:1]:
                params = {
                    "story": item["story"],
                    "ordinal": item["ordinal"],
                    "all_languages": "1",
                }
                contexts = [
                    client.get("/api/context", query_string=params)
                    for client in clients
                ]
                if (
                    any(r.status_code != 200 for r in contexts)
                    or contexts[0].json != contexts[1].json
                ):
                    raise ValueError("Context mismatch")
    report["api_cases"] = len(cases)
    report["size_mib"] = [
        round(Path(p).stat().st_size / 1024**2, 3) for p in (before, after)
    ]
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args()
    print(json.dumps(compare(args.before, args.after), indent=2))
