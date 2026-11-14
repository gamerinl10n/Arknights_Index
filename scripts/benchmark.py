"""Read-only local benchmark; reports timings/counts, never dialogue text."""

import argparse
import hashlib
import tracemalloc
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from core import search
from runtime_snapshot import materialize


def response_fingerprint(data):
    """Compare complete responses without persisting dialogue or query contents."""
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def profile_allocations(call):
    """Separate untimed pass: Python allocations, not SQLite/native/RSS memory."""
    if tracemalloc.is_tracing():
        raise RuntimeError("Memory profiling requires an isolated tracing session")
    tracemalloc.start()
    try:
        data = call()
        _, peak = tracemalloc.get_traced_memory()
        return data, peak
    finally:
        tracemalloc.stop()


def benchmark(database, rounds=15, unified=False, profile_memory=False):
    if rounds < 2:
        raise ValueError("At least two rounds are required")
    path = materialize(database)
    report = {}
    with closing(
        sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        for label, args in [("pair_ko", ("M3", "켈시")), ("solo_ko", ("아미야",))]:
            for detailed in (True, False):
                times = []
                statements = []
                fingerprints = set()
                for _ in range(rounds):
                    seen = []
                    db.set_trace_callback(seen.append)
                    start = perf_counter()
                    data = search(db, *args, include_details=detailed)
                    times.append((perf_counter() - start) * 1000)
                    statements.append(len(seen))
                    fingerprints.add(response_fingerprint(data))
                db.set_trace_callback(None)
                if len(fingerprints) != 1:
                    raise RuntimeError(
                        "Search response changed between benchmark rounds"
                    )
                key = label + ("_detailed" if detailed else "_light")
                report[key] = {
                    "response_sha256": next(iter(fingerprints)),
                    "total": data["total"],
                    "page_items": len(data["items"]),
                    "sql_statements": max(statements),
                    "response_bytes": len(
                        json.dumps(data, ensure_ascii=False).encode()
                    ),
                    "median_ms": round(statistics.median(times), 2),
                    "p95_ms": round(
                        sorted(times)[min(len(times) - 1, int(len(times) * 0.95))], 2
                    ),
                }
                if profile_memory:
                    profiled, peak = profile_allocations(
                        lambda: search(db, *args, include_details=detailed)
                    )
                    if response_fingerprint(profiled) not in fingerprints:
                        raise RuntimeError("Profiled search response changed")
                    report[key]["python_peak_bytes"] = peak
    client = create_app(str(path), readonly=True).test_client()
    times = []
    for _ in range(rounds):
        start = perf_counter()
        response = client.get("/api/suggestions?lang=ko_KR")
        if response.status_code != 200:
            raise RuntimeError("Suggestions unavailable")
        times.append((perf_counter() - start) * 1000)
    report["suggestions_ko"] = {
        "items": len(response.json),
        "first_ms": round(times[0], 2),
        "warm_median_ms": round(statistics.median(times[1:]), 2),
    }
    if unified:
        for label, query, offset in [
            ("unified_cn", "你好", 0),
            ("unified_ko", "안녕", 0),
            ("unified_common", "the", 0),
            ("unified_missing", "zzzznotfound", 0),
            ("unified_next", "the", 50),
        ]:
            times = []
            fingerprints = set()
            params = {
                "q": query,
                "lang": "ko_KR",
                "all_languages": "1",
                "details": "0",
                "offset": offset,
            }
            for _ in range(rounds):
                start = perf_counter()
                response = client.get(
                    "/api/search",
                    query_string=params,
                )
                if response.status_code != 200:
                    raise RuntimeError("Unified search unavailable")
                times.append((perf_counter() - start) * 1000)
                fingerprints.add(response_fingerprint(response.json))
            if len(fingerprints) != 1:
                raise RuntimeError("Unified response changed between benchmark rounds")
            report[label] = {
                "response_sha256": next(iter(fingerprints)),
                "total": response.json["total"],
                "page_items": len(response.json["items"]),
                "response_bytes": response.calculate_content_length(),
                "median_ms": round(statistics.median(times), 2),
                "p95_ms": round(
                    sorted(times)[min(len(times) - 1, int(len(times) * 0.95))], 2
                ),
            }
            if profile_memory:
                profiled, peak = profile_allocations(
                    lambda: client.get("/api/search", query_string=params)
                )
                if (
                    profiled.status_code != 200
                    or response_fingerprint(profiled.json) not in fingerprints
                ):
                    raise RuntimeError("Profiled unified response changed")
                report[label]["python_peak_bytes"] = peak
    report["measurement"] = {
        "rounds": rounds,
        "database_bytes": path.stat().st_size,
        "scope": "local; excludes network, deployment cold start and snapshot unpacking",
        "memory": (
            "separate untimed Python allocation peak; excludes SQLite/native memory and process RSS"
            if profile_memory
            else "not measured"
        ),
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database")
    parser.add_argument("--rounds", type=int, default=15)
    parser.add_argument(
        "--unified",
        action="store_true",
        help="Also measure cross-language word searches",
    )
    parser.add_argument(
        "--profile-memory",
        action="store_true",
        help="Measure Python peak allocations in a separate untimed pass",
    )
    args = parser.parse_args()
    if args.rounds < 2:
        parser.error("At least two rounds are required")
    print(
        json.dumps(
            benchmark(args.database, args.rounds, args.unified, args.profile_memory),
            ensure_ascii=False,
            indent=2,
        )
    )
