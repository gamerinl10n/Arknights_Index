"""All dialogue in these fixtures is synthetic."""

from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from core import connect, ingest
from build import export_snapshot
from app import create_app


class UnifiedSearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        for lang, speaker, text in [
            ("cn", "凯尔希", "synthetic 合成"),
            ("kr", "켈시", "synthetic 합성"),
            ("jp", "ケルシー", "synthetic 合成"),
            ("en", "Kal'tsit", "synthetic English"),
        ]:
            base = root / lang / "gamedata/story"
            base.mkdir(parents=True)
            (base / "matched.txt").write_text(
                '[name="' + speaker + '"]' + text, encoding="utf8"
            )
            (base / "pages.txt").write_text(
                "\n".join(
                    '[name="' + speaker + '"]synthetic ' + str(i) for i in range(60)
                ),
                encoding="utf8",
            )
        (root / "cn/gamedata/story/missing.txt").write_text(
            '[name="凯尔希"]unpublished synthetic', encoding="utf8"
        )
        source = root / "source.sqlite"
        self.snapshot = root / "snapshot.sqlite"
        with closing(connect(source)) as db:
            ingest(db, root, "synthetic-rev", "synthetic/source")
        export_snapshot(source, self.snapshot)
        self.client = create_app(str(self.snapshot), readonly=True).test_client()

    def tearDown(self):
        self.temp.cleanup()

    def find(self, **params):
        return self.client.get(
            "/api/search",
            query_string={
                "all_languages": "1",
                "lang": "ko_KR",
                "details": "0",
                **params,
            },
        )

    def test_foreign_query_displays_main_language_and_all_verified_variants(self):
        response = self.find(q="合成")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["total"], 1)  # Chinese/Japanese hits collapse
        row = response.json["items"][0]
        self.assertEqual(row["lang"], "ko_KR")
        self.assertIn("합성", row["text"])
        self.assertEqual(set(row["variants"]), {"zh_CN", "ko_KR", "ja_JP", "en_US"})
        self.assertEqual(row["variants"]["zh_CN"]["source"], "synthetic/source")

    def test_unique_pagination_is_after_deduplication(self):
        first = self.find(q="synthetic").json
        second = self.find(q="synthetic", offset="50").json
        self.assertEqual(first["total"], 61)
        self.assertEqual(len(first["items"]), 50)
        self.assertEqual(len(second["items"]), 11)
        keys = lambda result: {(r["story"], r["ordinal"]) for r in result["items"]}
        self.assertFalse(keys(first) & keys(second))
        self.assertTrue(
            all(r["lang"] == "ko_KR" for r in first["items"] + second["items"])
        )

    def test_spoilers_and_unverified_pairs_are_not_guessed(self):
        self.assertEqual(self.find(q="unpublished").json["total"], 0)
        row = self.find(q="unpublished", spoilers="1").json["items"][0]
        self.assertTrue(row["main_language_missing"])
        self.assertEqual(set(row["variants"]), {"zh_CN"})
        with closing(connect(self.snapshot)) as db:
            db.execute("UPDATE stories SET revision='stale' WHERE lang='ko_KR'")
            db.commit()
        response = self.find(q="合成").json
        self.assertEqual(response["total"], 1)
        self.assertEqual(response["items"][0]["lang"], "zh_CN")
        self.assertNotIn("ko_KR", response["items"][0]["variants"])

    def test_context_and_character_filters(self):
        row = self.find(q="合成", speaker="켈시").json["items"][0]
        response = self.client.get(
            "/api/context",
            query_string=dict(
                story=row["story"], ordinal=row["ordinal"], all_languages="1"
            ),
        )
        self.assertEqual(
            set(response.json["items"][0]["variants"]),
            {"zh_CN", "ko_KR", "ja_JP", "en_US"},
        )
        self.assertEqual(self.find(q="合成", speaker="아미야").json["total"], 0)

    def test_every_display_language_keeps_unique_pagination(self):
        for lang in ("ko_KR", "zh_CN", "ja_JP", "en_US"):
            with self.subTest(lang=lang):
                result = self.find(q="synthetic", lang=lang, offset="50").json
                self.assertEqual(result["total"], 61)
                self.assertEqual(len(result["items"]), 11)
                self.assertTrue(all(row["lang"] == lang for row in result["items"]))

    def test_old_snapshot_keeps_foreign_hits_separate(self):
        with closing(connect(self.snapshot)) as db:
            db.execute("DROP TABLE translation_alignments")
            db.commit()
        result = self.find(q="合成").json
        self.assertEqual(result["total"], 2)
        self.assertEqual({row["lang"] for row in result["items"]}, {"zh_CN", "ja_JP"})
        self.assertTrue(all(row["main_language_missing"] for row in result["items"]))

    def test_unaligned_pages_preserve_path_ordinal_and_language_order(self):
        with closing(connect(self.snapshot)) as db:
            db.execute("DROP TABLE translation_alignments")
            db.commit()
        rows = []
        for offset in range(0, 244, 50):
            result = self.find(q="synthetic", offset=str(offset)).json
            self.assertEqual(result["total"], 244)
            rows.extend(result["items"])
        keys = [(row["path"], row["ordinal"], row["lang"]) for row in rows]
        self.assertEqual(len(keys), 244)
        self.assertEqual(len(set(keys)), 244)
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(self.find(q="synthetic", offset="244").json["items"], [])

    def test_name_highlights_use_the_same_localized_aliases_as_search(self):
        result = self.find(speaker="아미야", target="凯尔希").json
        self.assertIn("켈시", result["highlights"]["ko_KR"])
        self.assertIn("凯尔希", result["highlights"]["zh_CN"])
        self.assertIn("ケルシー", result["highlights"]["ja_JP"])
        self.assertNotIn("凯尔希", result["highlights"]["ko_KR"])
        self.assertEqual(
            self.find(target="synthetic NPC").json["highlights"]["en_US"],
            ["synthetic NPC"],
        )
