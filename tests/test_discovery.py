from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree

from app import create_app
from translations import UI_LANGS


ORIGIN = "https://www.arknightsindex.com"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class HeadLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonicals = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs["href"])


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "missing.sqlite"
        database_guard = patch(
            "app.SearchService.open_db",
            side_effect=AssertionError("Discovery must not open the search database"),
        )
        database_guard.start()
        self.addCleanup(database_guard.stop)
        self.client = create_app(str(self.database), readonly=True).test_client()

    def test_sitemap_contains_only_canonical_public_entries(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/xml")
        self.assertTrue(response.data.startswith(b"<?xml"))
        root = ElementTree.fromstring(response.data)
        self.assertEqual(root.tag, SITEMAP_NS + "urlset")
        urls = [
            element.text for element in root.findall(f"{SITEMAP_NS}url/{SITEMAP_NS}loc")
        ]
        expected = {
            ORIGIN + path + (f"?ui={ui}" if ui != "ko" else "")
            for path in ("/", "/help")
            for ui in UI_LANGS
        } | {ORIGIN + path for path in ("/privacy", "/terms", "/license", "/changelog")}
        self.assertEqual(set(urls), expected)
        self.assertEqual(len(urls), len(expected))
        self.assertFalse(root.findall(f".//{SITEMAP_NS}lastmod"))
        for url in urls:
            with self.subTest(url=url):
                parsed = urlsplit(url)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, "www.arknightsindex.com")
                self.assertFalse(parsed.fragment)
                self.assertLessEqual(set(parse_qs(parsed.query)), {"ui"})
                page = self.client.get(url)
                self.assertEqual(page.status_code, 200)
                self.assertEqual(HeadLinks(page.text).canonicals, [url])
        self.assertFalse(self.database.exists())

    def test_robots_advertises_the_exact_sitemap_and_keeps_public_crawling(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(
            response.text,
            f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n",
        )
        for path in ("/robots.txt", "/sitemap.xml"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(self.client.head(path).status_code, 200)
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertIn(
                    "'strict-dynamic'", response.headers["Content-Security-Policy"]
                )
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_discovery_does_not_trust_hosts_or_request_parameters(self):
        for host in (
            "https://attacker.example",
            "https://preview.vercel.app",
            "http://localhost",
        ):
            for path in ("/robots.txt", "/sitemap.xml"):
                with self.subTest(host=host, path=path):
                    response = self.client.get(
                        path + "?q=private-term&ui=bad&url=https://attacker.example",
                        base_url=host,
                        headers={
                            "X-Forwarded-Host": "attacker.example",
                            "Forwarded": "host=attacker.example",
                        },
                    )
                    self.assertEqual(response.data, self.client.get(path).data)
            response = self.client.get("/?ui=en", base_url=host)
            self.assertEqual(HeadLinks(response.text).canonicals, [ORIGIN + "/?ui=en"])

    def test_canonicals_preserve_page_locale_but_not_tracking_or_search_state(self):
        cases = {
            "/": ORIGIN + "/",
            "/?ui=ko&lang=ko_KR": ORIGIN + "/",
            "/?ui=bad": ORIGIN + "/",
            "/?ui=en&lang=en_US&utm_source=test&show=ja_JP": ORIGIN + "/?ui=en",
            "/help?ui=ja&lang=ja_JP&utm_source=test": ORIGIN + "/help?ui=ja",
        }
        cases.update({f"/privacy?ui={ui}": ORIGIN + "/privacy" for ui in UI_LANGS})
        for path, expected in cases.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(HeadLinks(response.text).canonicals, [expected])
        for path in (
            "/search",
            "/search?ui=en&q=private-term",
            "/?ui=en&q=private-term",
            "/?speaker=private-name&view=home",
            "/?target=private-name",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(HeadLinks(response.text).canonicals, [])
        self.assertEqual(self.client.get("/missing-page").status_code, 404)
