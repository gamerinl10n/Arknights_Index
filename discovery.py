"""Public entry URLs only; never derive discovery metadata from a request host."""

from xml.etree.ElementTree import Element, SubElement, tostring

from translations import UI_LANGS

PUBLIC_ORIGIN = "https://www.arknightsindex.com"
LOCALIZED_PATHS = ("/", "/help")
BILINGUAL_PATHS = ("/privacy", "/terms", "/license", "/changelog")


def canonical_url(path, ui="ko"):
    if path in LOCALIZED_PATHS:
        # Korean is the default document; avoid a duplicate ?ui=ko entry.
        suffix = f"?ui={ui}" if ui in UI_LANGS and ui != "ko" else ""
        return PUBLIC_ORIGIN + path + suffix
    if path in BILINGUAL_PATHS:
        # These documents have the same Korean/English body in every UI locale.
        return PUBLIC_ORIGIN + path
    return None


def sitemap_xml():
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    urls = [canonical_url(path, ui) for path in LOCALIZED_PATHS for ui in UI_LANGS] + [
        canonical_url(path) for path in BILINGUAL_PATHS
    ]
    for url in urls:
        SubElement(SubElement(root, "url"), "loc").text = url
    return tostring(root, encoding="utf-8", xml_declaration=True)


ROBOTS_TXT = f"User-agent: *\nAllow: /\n\nSitemap: {PUBLIC_ORIGIN}/sitemap.xml\n"
