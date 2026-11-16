"""Synthetic indexed Decision grammar and conservative cross-language alignment."""

import unittest
from core import decision_options, parse, connect, ingest
from contextlib import closing
from pathlib import Path
import tempfile
from app import create_app
from build import export_snapshot
from translation_alignment import verified_pairs


class IndexedChoiceTest(unittest.TestCase):
    def test_indexed_order_literal_semicolon_and_unknown_speaker(self):
        raw = '[Decision(option2="Second",value2="2",option1="First; literal",value1="1")]\n[Predicate(references="1;2")]\n[name="A"]Reply'
        rows = list(parse(raw))
        self.assertEqual(rows[0][0], 0)
        self.assertEqual(rows[0][1], "")
        self.assertEqual(rows[0][2], "First; literal\nSecond")
        self.assertTrue(rows[0][3].startswith("decision@0:"))
        self.assertNotEqual(rows[0][3], rows[1][3])

    def test_modern_priority_empty_slots_and_non_option_keys(self):
        self.assertEqual(
            decision_options({"options": "A;;B", "option1": "Ignored"}), ["A", "", "B"]
        )
        self.assertEqual(
            decision_options(
                {
                    "option1": "",
                    "option3": "C",
                    "option10": "J",
                    "option0": "Ignored",
                    "option01": "Ignored",
                    "value1": "1",
                }
            ),
            ["", "C", "J"],
        )
        self.assertEqual(list(parse('[Decision(value1="1")]')), [])

    def test_translated_indexed_choices_align_by_structure(self):
        cn = '[Decision(option1="合成甲",value1="1",option2="合成乙",value2="2")]\n[Predicate(references="1;2")]\n[name="凯尔希"]合成回应'
        ko = '// shifted synthetic source\n[Decision(option1="합성 갑",value1="1",option2="합성 을",value2="2")]\n[Predicate(references="1;2")]\n[name="켈시"]합성 응답'
        pairs, status = verified_pairs(cn, ko)
        self.assertEqual(status, "matched")
        self.assertEqual(pairs, [(0, 1), (2, 3)])
        for changed in (
            ko.replace('value2="2"', 'value2="3"'),
            ko.replace("option2=", "option3="),
            ko.replace('references="1;2"', 'references="2;1"'),
        ):
            self.assertEqual(verified_pairs(cn, changed), (None, "structure"))

    def test_modern_and_indexed_formats_are_not_guessed_equivalent(self):
        self.assertEqual(
            verified_pairs(
                '[Decision(options="A",values="1")]',
                '[Decision(option1="B",value1="1")]',
            ),
            (None, "structure"),
        )

    def test_indexed_text_is_imported_into_readonly_search_with_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "kr/gamedata/story/indexed.txt"
            script.parent.mkdir(parents=True)
            script.write_text(
                '[Decision(option1="INDEXED_ONLY_LITERAL",value1="1")]',
                encoding="utf-8",
            )
            source, snapshot = root / "archive.sqlite", root / "snapshot.sqlite"
            with closing(connect(source)) as db:
                ingest(db, root, "synthetic", "fixture")
            export_snapshot(source, snapshot)
            client = create_app(database=snapshot, readonly=True).test_client()
            response = client.get(
                "/api/search",
                query_string={
                    "q": "INDEXED_ONLY_LITERAL",
                    "all_languages": "1",
                    "details": "0",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["total"], 1)
            row = response.json["items"][0]
            self.assertEqual(row["speaker"], "")
            self.assertEqual(row["ordinal"], 0)
            self.assertTrue(row["branch"].startswith("decision@0:"))
            self.assertEqual(row["path"], "indexed.txt")
            self.assertEqual(row["revision"], "synthetic")

    def test_changed_source_between_validation_and_import_rolls_back(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "kr/gamedata/story/indexed.txt"
            path.parent.mkdir(parents=True)
            extra = path.with_name("a.txt")
            extra.write_text('[name="Z"]Earlier synthetic text', encoding="utf-8")
            original = '[name="A"]Original synthetic text'
            path.write_text(original, encoding="utf-8")
            with closing(connect(":memory:")) as db:
                self.assertEqual(ingest(db, root, "before", "fixture"), 2)
                calls = 0
                read = Path.read_text

                def changing_read(filename, *args, **kwargs):
                    nonlocal calls
                    if filename == path:
                        calls += 1
                        if calls == 2:
                            return '[name="B"]Changed synthetic text'
                    return read(filename, *args, **kwargs)

                with patch.object(Path, "read_text", changing_read):
                    with self.assertRaisesRegex(ValueError, "Source changed"):
                        ingest(db, root, "after", "fixture")
                row = db.execute(
                    "SELECT speaker,text FROM lines WHERE story LIKE '%:indexed.txt'"
                ).fetchone()
                self.assertEqual(tuple(row), ("A", "Original synthetic text"))
                self.assertEqual(
                    db.execute("SELECT revision FROM stories").fetchone()[0], "before"
                )
