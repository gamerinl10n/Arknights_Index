"""Catalog lookup caching must not cache mutable archive counts or leak lists."""

import unittest
from unittest.mock import patch
from catalog import characters, character_id
from search_service import SearchService


def original_lookup(character):
    return sorted(
        {
            value
            for value in [
                character["id"],
                *character.get("aliases", []),
                *(name for group in character["names"].values() for name in group),
            ]
            if character_id(value) == character["id"]
        }
    )


class SuggestionLookupTest(unittest.TestCase):
    def test_all_catalog_entries_preserve_sorted_unambiguous_keys(self):
        service = SearchService("unused", False)
        for character in characters():
            with self.subTest(character=character["id"]):
                self.assertEqual(
                    service._lookup_for(character), original_lookup(character)
                )

    def test_lookup_is_computed_once_but_response_lists_are_fresh(self):
        character = {
            "id": "test",
            "aliases": ["alias", "ambiguous"],
            "names": {"ko_KR": ["이름", "alias"], "en_US": ["Name"]},
        }

        def identity(value):
            return None if value == "ambiguous" else "test"

        service = SearchService("unused", False)
        with patch("search_service.character_id", side_effect=identity) as lookup:
            first = service._lookup_for(character)
            calls = lookup.call_count
            first.append("client mutation")
            second = service._lookup_for(character)
            self.assertEqual(lookup.call_count, calls)
            self.assertEqual(second, sorted(["test", "alias", "이름", "Name"]))
            self.assertIsNot(first, second)
            self.assertIsInstance(service._lookup_keys["test"], tuple)
        self.assertEqual(SearchService("unused", False)._lookup_keys, {})

    def test_mutable_archive_counts_refresh_without_rebuilding_catalog_keys(self):
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from core import connect, ingest

        with TemporaryDirectory() as directory:
            root = Path(directory)
            story = root / "kr/gamedata/story/test.txt"
            story.parent.mkdir(parents=True)
            story.write_text('[name="Mon3tr"]Synthetic.\n', encoding="utf8")
            database = root / "source.sqlite"
            with closing(connect(database)) as db:
                ingest(db, root, "first", "test/source")
            service = SearchService(database, False)
            first = service.suggestions("ko_KR", False)
            first_row = next(row for row in first if row["value"] == "Mon3tr")
            self.assertEqual(first_row["count"], 1)
            expected_lookup = first_row["lookup"].copy()
            first_row["lookup"].append("client mutation")
            story.write_text(
                '[name="Mon3tr"]Synthetic.\n[name="Mon3tr"]Second.\n', encoding="utf8"
            )
            with closing(connect(database)) as db:
                ingest(db, root, "second", "test/source")
            refreshed = service.suggestions("ko_KR", False)
            row = next(row for row in refreshed if row["value"] == "Mon3tr")
            self.assertEqual(row["count"], 2)
            self.assertEqual(row["lookup"], expected_lookup)
