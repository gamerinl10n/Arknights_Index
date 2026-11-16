"""Synthetic evidence fixtures, never official dialogue."""

import unittest
from core import connect
from search_queries import search
from multilingual_search import search_all
from search_relations import validate_mentions


class MentionTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def story(self, path, rows, lang="ko_KR"):
        sid = lang + ":" + path
        self.db.execute(
            "INSERT INTO stories VALUES(?,?,?,?,?,?)",
            (sid, lang, path, "test", "fixture", ""),
        )
        for ordinal, (speaker, text, branch) in enumerate(rows, 1):
            self.db.execute(
                "INSERT INTO lines VALUES(?,?,?,?,?,?,?)",
                (sid + str(ordinal), sid, ordinal, speaker, text, branch, "test"),
            )

    def find(self, **options):
        return search(
            self.db,
            "A",
            "B",
            mention_mode="third_party_candidate",
            include_details=False,
            **options,
        )

    def test_positive_evidence_and_direct_reply_exclusion(self):
        self.story("candidate", [("C", "reply", "main"), ("A", "B mention", "main")])
        self.story(
            "direct",
            [
                ("C", "reply", "main"),
                ("A", "B mention", "main"),
                ("B", "reply", "main"),
            ],
        )
        self.story("alone", [("A", "B mention", "main")])
        self.story("branch", [("C", "reply", "other"), ("A", "B mention", "main")])
        self.story("unnamed", [("", "narration", "main"), ("A", "B mention", "main")])
        self.assertEqual(self.find()["total"], 1)
        self.assertEqual(self.find(interlocutor="C")["items"][0]["path"], "candidate")
        self.assertEqual(self.find(interlocutor="D")["total"], 0)
        self.assertEqual(search(self.db, "A", "B", include_details=False)["total"], 5)

    def test_no_skipping_other_speakers_and_physical_bounds(self):
        self.story(
            "blocked",
            [
                ("C", "reply", "main"),
                ("D", "reply", "main"),
                ("A", "B mention", "main"),
            ],
        )
        self.story(
            "far",
            [("C", "reply", "main")]
            + [("A", "filler", "main")] * 6
            + [("A", "B mention", "main")],
        )
        self.assertEqual(self.find(interlocutor="C")["total"], 0)
        self.assertEqual(self.find()["total"], 1)

    def test_counts_and_pages_filter_before_pagination(self):
        for i in range(55):
            self.story(f"{i:03}", [("C", "reply", "main"), ("A", "B mention", "main")])
        first, second = self.find(), self.find(offset=50)
        self.assertEqual(first["total"], 55)
        self.assertEqual(len(first["items"]), 50)
        self.assertEqual(len(second["items"]), 5)
        self.assertEqual(sum(x["count"] for x in first["stories"]), 55)
        self.assertFalse(
            {x["id"] for x in first["items"]} & {x["id"] for x in second["items"]}
        )

    def test_multilingual_with_and_without_query_uses_same_filter(self):
        for lang in ("ko_KR", "zh_CN", "ja_JP", "en_US"):
            self.story(
                "candidate", [("C", "reply", "main"), ("A", "B mention", "main")], lang
            )
            self.story(
                "direct", [("B", "reply", "main"), ("A", "B mention", "main")], lang
            )
        for query, expected in [("", 1), ("mention", 4)]:
            result = search_all(
                self.db,
                "A",
                "B",
                query=query,
                mention_mode="third_party_candidate",
                interlocutor="C",
            )
            self.assertEqual(result["total"], expected)
            self.assertTrue(all(x["path"] == "candidate" for x in result["items"]))

    def test_registered_aliases_validate_identity_and_match(self):
        self.story(
            "alias", [("C", "reply", "main"), ("켈시", "Mon3tr mention", "main")]
        )
        result = search(
            self.db,
            "凯尔希",
            "M3",
            mention_mode="third_party_candidate",
            interlocutor="C",
        )
        self.assertEqual(result["total"], 1)
        for args in [
            ("M3", "Mon3tr", "third_party_candidate", ""),
            ("A", "B", "third_party_candidate", "A"),
            ("", "B", "third_party_candidate", ""),
            ("A", "B", "invalid", ""),
            ("A", "B", "all", "C"),
        ]:
            with self.assertRaises(ValueError):
                validate_mentions(*args)

    def test_http_validation_and_forwarding(self):
        import tempfile
        from pathlib import Path
        from app import create_app

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite"
            db = connect(path)
            db.execute(
                "INSERT INTO stories VALUES('s','ko_KR','fixture','test','fixture','')"
            )
            for ordinal, speaker, text in [
                (1, "C", "reply"),
                (2, "A", "B mention"),
                (3, "B", "reply"),
            ]:
                db.execute(
                    "INSERT INTO lines VALUES(?,?,?,?,?,?,?)",
                    (str(ordinal), "s", ordinal, speaker, text, "main", "test"),
                )
            db.commit()
            db.close()
            client = create_app(database=path, readonly=False).test_client()
            base = "/api/search?speaker=A&target=B&details=0"
            self.assertEqual(client.get(base).json["total"], 1)
            for suffix in ["", "&all_languages=1", "&all_languages=1&q=mention"]:
                response = client.get(
                    base + "&mention_mode=third_party_candidate&interlocutor=C" + suffix
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["total"], 0)
            for suffix in [
                "&mention_mode=bad",
                "&interlocutor=C",
                "&mention_mode=third_party_candidate&interlocutor=A",
            ]:
                self.assertEqual(client.get(base + suffix).status_code, 400)

    def test_doctor_names_share_explicit_local_identity(self):
        from catalog import character_id, aliases, characters

        for name in ("박사", "博士", "ドクター", "Doctor"):
            self.assertEqual(character_id(name), "local:npc:doctor")
            self.assertEqual(aliases(name, "ko_KR"), ["박사"])
        self.assertIsNone(character_id("{nickname}"))
        doctor = next(row for row in characters() if row["id"] == "local:npc:doctor")
        self.assertEqual(len(doctor["source"]["paths"]), 4)
        self.story(
            "doctor", [("박사", "reply", "main"), ("켈시", "Mon3tr mention", "main")]
        )
        self.assertEqual(
            search(
                self.db,
                "凯尔希",
                "M3",
                mention_mode="third_party_candidate",
                interlocutor="Doctor",
            )["total"],
            1,
        )

    def test_two_direction_evidence_matrix_including_unknown_branches(self):
        from itertools import product

        # Independent truth table: B in either direction excludes; C is evidence.
        for left, right, branch in product(
            ["B", "C", "", None], ["B", "C", "", None], ["main", "other", None]
        ):
            # Use only string/null branch values, not character semantics.
            self.db.execute("DELETE FROM lines")
            self.db.execute("DELETE FROM stories")
            self.story(
                "matrix",
                [
                    (left, "reply", branch),
                    ("A", "B mention", "main"),
                    (right, "reply", "main"),
                ],
            )
            left_valid = branch == "main"
            expected = int(
                not (left_valid and left == "B")
                and right != "B"
                and ((left_valid and left == "C") or right == "C")
            )
            self.assertEqual(self.find()["total"], expected, (left, right, branch))
