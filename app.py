"""Flask entrypoint shared by local development and Vercel Functions."""

import argparse
from contextlib import closing
import json
import os
import secrets
from pathlib import Path
import sqlite3
from flask import (
    Flask,
    g,
    jsonify,
    request,
    send_file,
    render_template,
    abort,
    url_for,
    send_from_directory,
)
from core import connect, ingest
from search_queries import search, context_window, LANGUAGES
from pages import PAGES
from translations import STRINGS, UI_LANGS, tr
from localized_pages import get_page
import hashlib
from catalog import aliases
from search_service import SearchService
from translation_alignment import attach_comparisons, TARGET_LANGS
from multilingual_search import search_all, variants
from discovery import ROBOTS_TXT, canonical_url, sitemap_xml

ROOT = Path(__file__).resolve().parent


def create_app(database=None, readonly=None, portrait_root=None):
    app = Flask(__name__, static_folder=None, template_folder=str(ROOT / "web"))
    app.config["MAX_CONTENT_LENGTH"] = 16384
    readonly = bool(os.environ.get("VERCEL")) if readonly is None else readonly
    database = (
        database
        or os.environ.get("ASI_DB")
        or str(
            ROOT / ("generated/search.sqlite.gz" if readonly else "data/index.sqlite")
        )
    )
    service = SearchService(database, readonly, portrait_root)
    open_db = service.open_db

    version = (
        os.environ.get("VERCEL_DEPLOYMENT_ID")
        or os.environ.get("VERCEL_URL")
        or os.environ.get("VERCEL_GIT_COMMIT_SHA")
        or hashlib.sha256(
            b"".join(
                p.read_bytes() for p in sorted((ROOT / "web").rglob("*")) if p.is_file()
            )
        ).hexdigest()[:16]
    )

    @app.before_request
    def request_nonce():
        g.csp_nonce = secrets.token_urlsafe(24)

    @app.route("/ads.txt")
    def ads_txt():
        return send_file(ROOT / "web/ads.txt", mimetype="text/plain")

    @app.route("/robots.txt")
    def robots_txt():
        return app.response_class(ROBOTS_TXT, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap():
        return app.response_class(sitemap_xml(), mimetype="application/xml")

    @app.context_processor
    def template_context():
        ui = request.args.get("ui", "ko")
        if ui not in UI_LANGS:
            ui = "ko"
        return dict(
            canonical_url=(
                None
                if request.endpoint == "home"
                and any(request.args.get(key) for key in ("speaker", "target", "q"))
                else canonical_url(request.path, ui)
            ),
            csp_nonce=g.csp_nonce,
            adsense_enabled=request.host.split(":", 1)[0]
            in ("arknightsindex.com", "www.arknightsindex.com"),
            # Search shells/results and service notices are not ad inventory.
            adsense_content_page=request.endpoint == "document"
            and request.view_args.get("page") == "help",
            ui=ui,
            t=lambda key: tr(ui, key),
            ui_languages=UI_LANGS,
            corpus_languages={
                "ko_KR": "한국어",
                "zh_CN": "中文",
                "ja_JP": "日本語",
                "en_US": "English",
            },
            deployment_version=version,
            asset=lambda filename: url_for(
                "versioned_asset", asset_version=version, filename=filename
            ),
            help_page=get_page("help", ui),
        )

    @app.route("/version.json")
    def version_json():
        return jsonify(version=version)

    @app.route("/i18n.js")
    def ui_copy():
        ui = request.args.get("ui", "ko")
        if ui not in UI_LANGS:
            ui = "ko"
        return app.response_class(
            "window.ASI = "
            + json.dumps({"ui": ui, "strings": STRINGS[ui]}, ensure_ascii=False)
            + ";",
            mimetype="text/javascript",
        )

    @app.after_request
    def headers(response):
        if request.endpoint in (
            "versioned_asset",
            "portrait",
        ) and response.status_code in (200, 304):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.endpoint in (
            "javascript",
            "stylesheet",
            "shared_assets",
            "ui_module",
        ):
            response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
        else:
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'nonce-{g.csp_nonce}' 'strict-dynamic' 'self' https: 'unsafe-eval'; "
            "connect-src 'self' https:; img-src 'self' https: data:; "
            "frame-src https:; style-src 'self' 'unsafe-inline'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.errorhandler(ValueError)
    def bad_request(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(sqlite3.OperationalError)
    def unavailable(error):
        app.logger.error("Search database unavailable: %s", type(error).__name__)
        return (
            jsonify(
                error="검색 데이터가 준비되지 않았습니다. 배포 빌드와 데이터 생성을 확인하세요."
            ),
            503,
        )

    @app.route("/")
    @app.route("/search")
    def home():
        return render_template(
            "index.html",
            title=tr(
                request.args.get("ui") if request.args.get("ui") in UI_LANGS else "ko",
                "search",
            ),
            initial_view=(
                "results"
                if request.path == "/search"
                or (
                    any(request.args.get(key) for key in ("speaker", "target", "q"))
                    and request.args.get("view") != "home"
                )
                else "home"
            ),
        )

    @app.route("/assets/<asset_version>/<path:filename>")
    def versioned_asset(asset_version, filename):
        if asset_version != version or Path(filename).suffix not in (
            ".js",
            ".mjs",
            ".css",
            ".otf",
            ".woff2",
            ".txt",
            ".png",
            ".ico",
            ".svg",
        ):
            abort(404)
        return send_from_directory(ROOT / "web", filename)

    @app.route("/portraits/<filename>")
    def portrait(filename):
        if filename not in service.portraits.images.values():
            abort(404)
        return send_from_directory(
            service.portraits.root, filename, mimetype="image/webp"
        )

    @app.route("/app.js")
    def javascript():
        return send_file(ROOT / "web/app.js", mimetype="text/javascript")

    @app.route("/ui/<path:filename>")
    def ui_module(filename):
        return send_from_directory(
            ROOT / "web/ui", filename, mimetype="text/javascript"
        )

    @app.route("/style.css")
    def stylesheet():
        return send_file(ROOT / "web/style.css", mimetype="text/css")

    @app.route("/update-monitor.mjs")
    @app.route("/update-banner.mjs")
    @app.route("/update-banner.css")
    @app.route("/theme.js")
    @app.route("/chrome.js")
    @app.route("/theme-control.css")
    def shared_assets():
        filename = request.path.lstrip("/")
        return send_file(
            ROOT / "web" / filename,
            mimetype="text/css" if filename.endswith(".css") else "text/javascript",
        )

    @app.route("/<page>")
    def document(page):
        if page not in PAGES:
            abort(404)
        ui = request.args.get("ui", "ko")
        if ui not in UI_LANGS:
            ui = "ko"
        if page == "help":
            return render_template(
                "help.html", title=tr(ui, "help"), page=get_page("help", ui)
            )
        data = get_page(page, "ko")
        english = get_page(page, "en")
        return render_template(
            "document.html",
            title=data["title"] + " · " + english["title"],
            page=data,
            english_page=english,
            bilingual_document=True,
        )

    @app.route("/api/search")
    def find():
        q = request.args
        if not any(q.get(key, "").strip() for key in ("speaker", "target", "q")):
            raise ValueError("인물이나 대사 속 표현을 입력하세요.")
        if any(
            len(q.get(key, "")) > 300 for key in ("speaker", "target", "q", "story")
        ):
            raise ValueError("검색어가 너무 깁니다.")
        comparison = q.get("compare") == "1"
        translation_lang = q.get("translation_lang", "ko_KR")
        if comparison and translation_lang not in TARGET_LANGS:
            raise ValueError("Invalid translation language")
        with closing(open_db()) as db:
            result = (search_all if q.get("all_languages") == "1" else search)(
                db,
                q.get("speaker", "").strip(),
                q.get("target", "").strip(),
                q.get("q", "").strip(),
                q.get("lang", "ko_KR"),
                q.get("spoilers") == "1",
                max(0, int(q.get("offset", 0))),
                q.get("story", ""),
                include_details=q.get("details") != "0",
            )
            if comparison:
                attach_comparisons(
                    db, result["items"], q.get("lang", "ko_KR"), translation_lang
                )
        service.portraits.annotate(result["items"])
        for item in result["items"]:
            service.portraits.annotate(list(item.get("variants", {}).values()))
            if "comparison" in item:
                service.portraits.annotate(item["comparison"]["items"])
            service.portraits.annotate(item.get("context", []))
            service.portraits.annotate(item.get("parallel", []))
        if target := q.get("target", "").strip():
            result["highlights"] = {lang: aliases(target, lang) for lang in LANGUAGES}
        result["participants"] = {
            key: service.portraits.identity(q.get(key, "").strip())
            for key in ("speaker", "target")
        }
        return jsonify(result)

    @app.route("/api/context")
    def context():
        comparison = request.args.get("compare") == "1"
        translation_lang = request.args.get("translation_lang", "ko_KR")
        if comparison and translation_lang not in TARGET_LANGS:
            raise ValueError("Invalid translation language")
        story = request.args.get("story", "")
        with closing(open_db()) as db:
            result = context_window(
                db,
                story,
                int(request.args.get("ordinal", 0)),
                int(request.args.get("radius", 15)),
                parallel=request.args.get("parallel") == "1",
            )
            if comparison or request.args.get("all_languages") == "1":
                metadata = db.execute(
                    "SELECT lang,path,revision,source FROM stories WHERE id=?", (story,)
                ).fetchone()
                for row in result["items"]:
                    row.update(dict(metadata), story=story)
                if request.args.get("all_languages") == "1":
                    variants(db, result["items"])
                else:
                    attach_comparisons(
                        db, result["items"], metadata["lang"], translation_lang
                    )
        service.portraits.annotate(result["items"])
        for row in result["items"]:
            service.portraits.annotate(list(row.get("variants", {}).values()))
            if "comparison" in row:
                service.portraits.annotate(row["comparison"]["items"])
        service.portraits.annotate(result.get("parallel", []))
        return jsonify(result)

    @app.route("/api/status")
    def status():
        return jsonify(service.status())

    @app.route("/api/speakers")
    def speakers():
        lang = request.args.get("lang", "ko_KR")
        if lang not in LANGUAGES:
            raise ValueError("지원하지 않는 언어")
        spoilers = request.args.get("spoilers") == "1"
        return jsonify(
            [
                row["value"]
                for row in service.suggestions(lang, spoilers)
                if row["value"] == row["label"]
            ]
        )

    @app.route("/api/suggestions")
    def suggestions():
        lang = request.args.get("lang", "ko_KR")
        if lang not in LANGUAGES:
            raise ValueError("지원하지 않는 언어")
        spoilers = request.args.get("spoilers") == "1"
        return jsonify(service.suggestions(lang, spoilers))

    return app


app = create_app()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--import-root")
    p.add_argument("--revision")
    p.add_argument("--source", default="ArknightsAssets/ArknightsGamedata")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="127.0.0.1")
    a = p.parse_args()
    database = os.environ.get("ASI_DB", str(ROOT / "data/index.sqlite"))
    if not os.environ.get("VERCEL"):
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with closing(connect(database)) as db:
            if a.import_root:
                if not a.revision:
                    p.error("--revision is required for provenance")
                print(ingest(db, a.import_root, a.revision, a.source), "lines imported")
                raise SystemExit
    app.run(host=a.host, port=a.port)
