import importlib.util
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('collector', Path(__file__).resolve().parents[1]/'scripts/update_public_data.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 15, 11, 23, tzinfo=C.SHANGHAI)
        self.entry = {'keyword': '测试词', 'type': '商品', 'article': '测试条目'}

    def test_missing_days_not_fabricated(self):
        response = {'items': [{'timestamp': '2026011400', 'views': 0, 'article': '测试条目', 'agent': 'user', 'access': 'all-access'}]}
        with patch.object(C, 'resolve_article', return_value='测试条目'), patch.object(C, 'get_json', return_value=response):
            rows, evidence = C.wikipedia(self.entry, self.now)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['metric_value'], 0)
        self.assertEqual(rows[0]['observed_date'], '2026-01-14')
        self.assertTrue(evidence['response_sha256'])

    def test_failure_retains_date_and_does_not_mark_success(self):
        response = {'full_name': 'owner/repo', 'private': False, 'stargazers_count': 20, 'html_url': 'https://github.com/owner/repo'}
        entry = {'keyword': '测试项目', 'type': '软件', 'repo': 'owner/repo'}
        with patch.object(C, 'get_json', return_value=response):
            rows, evidence = C.github(entry, self.now)
        previous = {'rows': rows, 'sources': [{'id':'github:owner/repo','status':'ok','last_success_at':self.now.isoformat(),'latest_observation':'2026-01-15'}]}
        with patch.object(C, 'github', side_effect=ValueError('Upstream HTTP 503')):
            result = C.collect({'wikipedia': [], 'github': [entry]}, previous, self.now.replace(day=16))
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['rows'][0]['observed_date'], '2026-01-15')
        self.assertEqual(result['sources'][0]['last_success_at'], self.now.isoformat())
        self.assertEqual(result['sources'][0]['status'], 'error')

    def test_same_day_upsert_not_duplicate(self):
        row={'observed_date':'2026-01-15','platform':'GitHub','keyword':'测试','opportunity_type':'软件','metric_type':'github_stars','source_type':'public_api','source_name':'API','source_scope':'repo','metric_value':2,'is_demo':0}
        merged=C.merge_history([row],[dict(row,metric_value=3)],'2026-01-01')
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['metric_value'],3)

    def test_invalid_or_other_repo_response_rejected(self):
        entry = {'keyword':'测试','type':'软件','repo':'owner/repo'}
        with patch.object(C,'get_json',return_value={'stargazers_count':20,'full_name':'other/repo','private':False}):
            with self.assertRaises(ValueError): C.github(entry,self.now)

    def test_compact_storage_preserves_provenance(self):
        row={'observed_date':'2026-01-15','platform':'GitHub','keyword':'测试','opportunity_type':'软件','metric_type':'github_stars','source_type':'public_api','source_name':'API','source_scope':'repo','metric_value':2,'is_demo':0,'fetched_at':self.now.isoformat(),'api_url':'https://api.github.com/repos/owner/repo','response_sha256':'hash'}
        original={'schema_version':1,'rows':[row,dict(row,observed_date='2026-01-16',metric_value=3)],'sources':[]}
        packed=C.pack_dataset(original)
        self.assertEqual(len(packed['receipts']),1)
        self.assertEqual(C.unpack_dataset(packed)['rows'],original['rows'])

if __name__ == '__main__':
    unittest.main()
