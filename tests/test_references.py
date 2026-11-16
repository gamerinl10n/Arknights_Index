"""Synthetic referent evidence tests; not game quotations."""

import unittest
from unittest.mock import patch
from core import connect
from search_queries import search
from multilingual_search import search_all
from search_relations import validate_mentions
from search_references import expressions


class ReferenceTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def story(self, path, rows, lang="ko_KR", revision="test"):
        sid = lang + ":" + path
        self.db.execute(
            "INSERT INTO stories VALUES(?,?,?,?,?,?)",
            (sid, lang, path, revision, "fixture", ""),
        )
        for ordinal, speaker, text, branch in rows:
            self.db.execute(
                "INSERT INTO lines VALUES(?,?,?,?,?,?,?)",
                (
                    sid + str(ordinal),
                    sid,
                    ordinal,
                    speaker,
                    text,
                    branch,
                    "hash" + str(ordinal),
                ),
            )
        return sid

    def find(self, **kwargs):
        return search(
            self.db,
            target="아미야",
            mention_mode="reference_candidates",
            include_details=False,
            **kwargs,
        )

    def test_target_only_finds_unnamed_references_without_rewriting_text(self):
        self.story(
            "fixture",
            [
                (1, "아미야", "시험 발화", "main"),
                (2, "A", "당나귀 녀석, 저 녀석을 보라.", "main"),
                (3, "B", "그 아이와 이야기했어.", "main"),
                (4, "A", "아미야라는 이름.", "main"),
                (5, "아미야", "그 아이가 나인가?", "main"),
                (6, "", "그 아이", "main"),
            ],
        )
        result = self.find()
        self.assertEqual(result["total"], 3)
        row = next(x for x in result["items"] if x["ordinal"] == 2)
        self.assertIn("당나귀 녀석", row["references"][0]["expressions"])
        self.assertEqual(row["references"][0]["status"], "candidate")
        self.assertEqual(row["text"], "당나귀 녀석, 저 녀석을 보라.")
        self.assertEqual(row["references"][0]["anchor"]["branch"], "main")
        self.assertEqual(self.find(speaker="B")["total"], 1)
        self.assertEqual(self.find(query="당나귀")["total"], 1)
        self.assertEqual(
            search(self.db, target="아미야", include_details=False)["total"], 1
        )

    def test_branch_barriers_unknown_branches_and_text_physical_bounds(self):
        cases = {
            "branch": [
                (1, "아미야", "fixture", "main"),
                (2, "A", "barrier", "other"),
                (3, "A", "저 녀석", "main"),
            ],
            "far": [(1, "아미야", "fixture", "main"), (62, "A", "저 녀석", "main")],
            "unknown": [(1, "아미야", "fixture", None), (2, "A", "저 녀석", None)],
            "many": [
                (
                    n,
                    "아미야" if n == 1 else "A",
                    "저 녀석" if n == 5 else "fixture",
                    "main",
                )
                for n in range(1, 6)
            ],
            "no-anchor": [(1, "A", "그 아이", "main")],
            "unknown-speaker": [
                (1, "아미야", "fixture", "main"),
                (2, "???", "그 아이", "main"),
            ],
        }
        for path, rows in cases.items():
            self.story(path, rows)
        self.assertEqual(self.find()["total"], 0)

    def test_unknown_epithet_query_is_local_to_context_not_a_global_alias(self):
        self.story(
            "near", [(1, "아미야", "fixture", "main"), (2, "A", "수수께끼별명", "main")]
        )
        self.story("unrelated", [(1, "A", "수수께끼별명", "main")])
        self.assertEqual(self.find()["total"], 0)
        result = self.find(query="수수께끼별명")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["path"], "near")

    def test_four_languages_and_latin_name_boundaries(self):
        for lang, name, phrase in [
            ("ko_KR", "아미야", "저 녀석"),
            ("zh_CN", "阿米娅", "那家伙"),
            ("ja_JP", "アーミヤ", "あの子"),
            ("en_US", "Amiya", "that girl"),
        ]:
            self.story(
                "fixture",
                [(1, name, "fixture", "main"), (2, "A", phrase, "main")],
                lang,
            )
            result = search_all(
                self.db, target="아미야", lang=lang, mention_mode="reference_candidates"
            )
            self.assertEqual(result["total"], 1)
            self.assertIn(phrase, result["items"][0]["references"][0]["expressions"])
        self.assertEqual(expressions("Sheryl studies a theme", ["Amiya"], "en_US"), [])
        self.story(
            "not-name",
            [(1, "A", "Amiyanna arrived", "main"), (2, "A", "that girl", "main")],
            "en_US",
        )
        self.assertEqual(
            search(
                self.db,
                target="Amiya",
                lang="en_US",
                spoilers=True,
                mention_mode="reference_candidates",
            )["total"],
            1,
        )
        result = search_all(
            self.db,
            target="Amiya",
            query="girl",
            mention_mode="reference_candidates",
            spoilers=True,
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["references"][0]["lang"], "en_US")

    def test_counts_pagination_dedup_and_connection_reuse(self):
        for i in range(56):
            self.story(
                f"{i:03}",
                [
                    (1, "아미야", "fixture", "main"),
                    (2, "A", "저 녀석", "main"),
                    (3, "아미야", "fixture", "main"),
                ],
            )
        first = self.find()
        second = self.find(offset=50)
        self.assertEqual(first["total"], 56)
        self.assertEqual(sum(x["count"] for x in first["stories"]), 56)
        self.assertEqual(len(first["items"]), 50)
        self.assertEqual(len(second["items"]), 6)
        self.assertFalse(
            {x["id"] for x in first["items"]} & {x["id"] for x in second["items"]}
        )
        self.assertEqual(self.find(speaker="missing")["total"], 0)
        self.assertEqual(self.find(story="000")["total"], 1)
        self.assertEqual(self.find()["total"], 56)

    def test_validation(self):
        validate_mentions("", "아미야", "reference_candidates", "")
        for speaker, target, partner in [
            ("A", "", ""),
            ("Amiya", "아미야", ""),
            ("", "아미야", "C"),
        ]:
            with self.assertRaises(ValueError):
                validate_mentions(speaker, target, "reference_candidates", partner)

    def test_documented_occurrence_hash_revision_and_unchanged_anonymous_speaker(self):
        self.story(
            "linked", [(1, "A", "별명", "main"), (9, "???", "익명 응답", "main")]
        )
        self.db.execute("ALTER TABLE lines ADD COLUMN hash_bytes BLOB")
        self.db.execute("UPDATE lines SET hash_bytes=x'00'")
        link = {
            "target_id": "char_002_amiya",
            "lang": "ko_KR",
            "path": "linked",
            "revision": "test",
            "source": "fixture",
            "ordinal": 1,
            "line_hash": "hash1",
            "expression": "별명",
            "anchor_ordinal": 9,
            "anchor_hash": "hash9",
            "evidence": {
                "kind": "portrait_response",
                "ordinal": 8,
                "asset": "char_002_amiya_1#8",
                "focus": 1,
            },
        }
        with patch("search_references.reference_links", return_value=[link]):
            result = self.find()
            self.assertEqual(result["total"], 1)
            ref = result["items"][0]["references"][0]
            self.assertEqual(ref["status"], "source_checked")
            self.assertEqual(ref["anchor"]["speaker"], "???")
            for key, value in [
                ("revision", "changed"),
                ("line_hash", "changed"),
                ("anchor_hash", "changed"),
                ("expression", "not in text"),
            ]:
                with patch(
                    "search_references.reference_links",
                    return_value=[{**link, key: value}],
                ):
                    self.assertEqual(self.find()["total"], 0)
            self.assertEqual(self.find(speaker="missing")["total"], 0)

    def test_http_reference_query_does_not_require_a_speaker(self):
        import tempfile
        from pathlib import Path
        from app import create_app

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.sqlite"
            self.db.close()
            self.db = connect(path)
            self.story(
                "fixture",
                [(1, "아미야", "fixture", "main"), (2, "A", "저 녀석", "main")],
            )
            self.db.commit()
            client = create_app(database=path, readonly=False).test_client()
            response = client.get(
                "/api/search",
                query_string={
                    "target": "아미야",
                    "mention_mode": "reference_candidates",
                    "all_languages": "1",
                    "details": "0",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["total"], 1)
            self.assertEqual(
                response.json["items"][0]["references"][0]["status"], "candidate"
            )

    def test_verified_translation_keeps_original_reference_evidence(self):
        import tempfile
        from pathlib import Path
        from core import ingest
        from build import export_snapshot
        from app import create_app

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder, name, caller, phrase in [
                ("kr", "아미야", "켈시", "그 아이"),
                ("cn", "阿米娅", "凯尔希", "那家伙"),
                ("jp", "アーミヤ", "ケルシー", "あの子"),
                ("en", "Amiya", "Kal'tsit", "that girl"),
            ]:
                path = root / folder / "gamedata/story/fixture.txt"
                path.parent.mkdir(parents=True)
                path.write_text(
                    f'[name="{name}"]Synthetic target turn\n[name="{caller}"]{phrase}',
                    encoding="utf-8",
                )
            source = root / "source.sqlite"
            snapshot = root / "snapshot.sqlite"
            database = connect(source)
            ingest(database, root, "synthetic", "fixture")
            database.close()
            export_snapshot(source, snapshot)
            client = create_app(database=snapshot, readonly=True).test_client()
            response = client.get(
                "/api/search",
                query_string={
                    "target": "아미야",
                    "q": "girl",
                    "all_languages": "1",
                    "mention_mode": "reference_candidates",
                    "details": "0",
                },
            )
            self.assertEqual(response.status_code, 200)
            row = response.json["items"][0]
            self.assertEqual(row["lang"], "ko_KR")
            self.assertEqual(row["text"], "그 아이")
            self.assertEqual(row["references"][0]["lang"], "en_US")
            self.assertEqual(row["references"][0]["expressions"], ["that girl", "girl"])
            self.assertEqual(row["references"][0]["anchor"]["speaker"], "Amiya")
