from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from app import create_app
from build import export_snapshot
from core import connect,ingest

class DeploymentTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        path=self.root/'kr/gamedata/story/test.txt';path.parent.mkdir(parents=True)
        path.write_text('[name="Mon3tr"]켈시 선생님.\n[name="켈시"]그래.',encoding='utf8')
        self.source=self.root/'source.sqlite';self.snapshot=self.root/'search.sqlite'
        with closing(connect(self.source)) as db:ingest(db,self.root,'test-revision','test/source')
        export_snapshot(self.source,self.snapshot)
        self.client=create_app(str(self.snapshot),readonly=True).test_client()
    def tearDown(self):self.tmp.cleanup()
    def test_root_assets_and_readonly_search(self):
        before=self.snapshot.read_bytes()
        for url in ('/','/app.js','/style.css','/api/status','/api/speakers'):
            with self.client.get(url) as response:self.assertEqual(response.status_code,200,url)
        response=self.client.get('/api/search?speaker=M3&target=켈시')
        self.assertEqual(response.json['total'],1)
        self.assertNotIn('reviews',response.json['items'][0])
        self.assertEqual(before,self.snapshot.read_bytes())
    def test_snapshot_has_only_search_tables(self):
        with closing(sqlite3.connect(self.snapshot)) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables,{'stories','lines','import_status','suggestion_counts','sqlite_stat1','translation_alignments'})
            self.assertNotIn('raw',[r[1] for r in db.execute('PRAGMA table_info(stories)')])
    def test_removed_admin_route_and_ui(self):
        self.assertEqual(self.client.post('/api/review',json={}).status_code,404)
        with self.client.get('/') as response:self.assertNotIn('관리자',response.text)
        with self.client.get('/app.js') as response:self.assertNotIn('/api/review',response.text)
    def test_old_environment_does_not_require_external_storage(self):
        with patch.dict(os.environ,{'ASI_REVIEW_DATABASE_URL':'invalid','ASI_ADMIN_TOKEN':'unused'}):
            client=create_app(str(self.snapshot),True).test_client()
            self.assertEqual(client.get('/api/search?speaker=M3').status_code,200)
    def test_bad_search_and_missing_data(self):
        self.assertEqual(self.client.get('/api/search?speaker=M3&offset=bad').status_code,400)
        self.assertEqual(self.client.get('/api/search').status_code,400)
        client=create_app(str(self.root/'missing.sqlite'),True).test_client()
        self.assertEqual(client.get('/api/status').status_code,503)
        self.assertFalse((self.root/'missing.sqlite').exists())
    def test_shared_pages_and_assets(self):
        for url in ('/privacy','/terms','/license','/changelog'):
            with self.client.get(url) as response:
                self.assertEqual(response.status_code,200,url)
                self.assertIn('id="themeButton"',response.text)
                self.assertIn('href="/privacy?ui=ko"',response.text)
                self.assertNotIn('/app.js',response.text)
        for url in ('/theme.js','/chrome.js','/theme-control.css'):
            with self.client.get(url) as response:self.assertEqual(response.status_code,200,url)
        with self.client.get('/privacy') as response:
            self.assertIn('검색 요청은 URL',response.text)
            self.assertIn('서버에 전송',response.text)
        for language, heading in [('ko','예제: 다른 언어의 표현 찾기'), ('en','Example: search another language'), ('ja','例：他言語の表現を探す'), ('zh','示例：搜索其他语言的表达')]:
            guide = self.client.get('/help?ui=' + language)
            self.assertEqual(guide.status_code,200)
            article = guide.text.split('<article',1)[1].split('</article>',1)[0]
            self.assertIn(heading, article)
            self.assertIn(heading, self.client.get('/?ui=' + language).text)
        self.assertIn('예제: 다른 언어의 표현 찾기', self.client.get('/help?ui=bad').text)
        self.assertEqual(self.client.get('/unknown-document').status_code,404)
    def test_suggestions_include_alias_and_count_without_spoilers(self):
        rows=self.client.get('/api/suggestions').json
        by_name={row['value']:row for row in rows}
        self.assertEqual(by_name['Mon3tr']['count'],1)
        self.assertIn('M3',by_name['Mon3tr']['lookup'])
        self.assertNotIn('凯尔希',by_name)
        self.assertIn('凯尔希',by_name['켈시']['lookup'])
        self.assertEqual(self.client.get('/api/suggestions?lang=bad').status_code,400)

    def test_versioned_modules_are_cacheable_and_private_routes_are_not(self):
        import re
        html=self.client.get('/').text
        module=re.search(r'src="([^"]+/app.js)"',html).group(1)
        response=self.client.get(module)
        self.assertIn('immutable',response.headers['Cache-Control'])
        response.close()
        dependency=module.rsplit('/',1)[0]+'/ui/results.mjs'
        with self.client.get(dependency) as dependency_response:
            self.assertEqual(dependency_response.status_code,200)
        self.assertIn('no-store',self.client.get('/api/status').headers['Cache-Control'])
        self.assertEqual(self.client.get('/assets/invalid/ui/results.mjs').status_code,404)
        self.assertEqual(self.client.get('/ui/../../app.py').status_code,404)

    def test_precomputed_suggestions_equal_mutable_archive_results(self):
        mutable=create_app(str(self.root/'source.sqlite'),False).test_client()
        for lang in ('ko_KR','zh_CN','ja_JP','en_US'):
            for spoilers in ('0','1'):
                query={'lang':lang,'spoilers':spoilers}
                self.assertEqual(self.client.get('/api/suggestions',query_string=query).json,mutable.get('/api/suggestions',query_string=query).json)

    def test_precomputed_suggestions_do_not_leak_advance_only_speakers(self):
        future=self.root/'cn/gamedata/story/future.txt'
        future.parent.mkdir(parents=True)
        future.write_text('[name="Mon3tr"]fixture future',encoding='utf8')
        with closing(connect(self.source)) as db:ingest(db,self.root,'v2','test/source')
        export_snapshot(self.source,self.snapshot)
        client=create_app(str(self.snapshot),True).test_client()
        self.assertEqual(client.get('/api/suggestions?lang=zh_CN').json,[])
        by_name={row['value']:row for row in client.get('/api/suggestions?lang=zh_CN&spoilers=1').json}
        self.assertEqual(by_name['Mon3tr']['count'],1)

    def test_light_api_and_lazy_context_preserve_source_and_parallel(self):
        response=self.client.get('/api/search?speaker=M3&details=0').json
        item=response['items'][0]
        self.assertNotIn('context',item)
        self.assertEqual(item['source'],'test/source')
        result=self.client.get('/api/context',query_string={'story':item['story'],'ordinal':item['ordinal'],'radius':3,'parallel':'1'}).json
        self.assertEqual(result['items'][0]['text'],item['text'])
        self.assertIn('parallel',result)
        self.assertIn('branch',result['items'][0])

    def test_compressed_bundle_is_unpacked_for_readonly_queries(self):
        import gzip
        from runtime_snapshot import materialize
        compressed=self.root/'search.sqlite.gz'
        with gzip.open(compressed,'wb') as f:f.write(self.snapshot.read_bytes())
        unpacked=materialize(compressed,self.root)
        self.assertEqual(unpacked.read_bytes(),self.snapshot.read_bytes())
        self.assertEqual(materialize(compressed,self.root),unpacked)
        client=create_app(str(compressed),True).test_client()
        self.assertEqual(client.get('/api/search?speaker=M3').json['total'],1)

    def test_adsense_publisher_file_and_production_nonce(self):
        import re
        with self.client.get('/ads.txt') as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/plain')
            self.assertEqual(response.text, 'google.com, pub-6317702529934048, DIRECT, f08c47fec0942fa0\n')
        self.assertNotIn('adsbygoogle.js', self.client.get('/').text)
        nonces = []
        for page in ('/help', '/help?ui=en', '/help?ui=ja'):
            response = self.client.get(page, base_url='https://www.arknightsindex.com')
            self.assertEqual(response.text.count('adsbygoogle.js?client=ca-pub-6317702529934048'), 1)
            nonce = re.search(r"'nonce-([^']+)'", response.headers['Content-Security-Policy']).group(1)
            nonces.append(nonce)
            scripts = re.findall(r'<script\b[^>]*>', response.text)
            self.assertTrue(all('nonce="' + nonce + '"' in tag for tag in scripts))
            self.assertIn("'strict-dynamic'", response.headers['Content-Security-Policy'])
        self.assertEqual(len(set(nonces)), 3)
        self.assertNotIn('광고 스크립트는 포함하지 않습니다', self.client.get('/privacy').text)
