import io
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import connect, add_rows, read_rows, analyze, demo_rows, import_csv, export_csv


def row(day, value, metric="search_index", kind="商品", word="甲"):
    return {"observed_date": day.isoformat(), "platform": "拼多多",
            "keyword": word, "opportunity_type": kind, "metric_type": metric,
            "metric_value": value, "source_type": "manual_observation",
            "source_name": "我的观察", "source_scope": "固定范围",
            "source_url": "", "notes": ""}


class TestCore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self.tmp.name) / "db.sqlite3")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_no_real_data_when_demo(self):
        add_rows(self.conn, demo_rows(), is_demo=True)
        self.assertEqual([], read_rows(self.conn, is_demo=False))
        self.assertGreater(len(read_rows(self.conn, is_demo=True)), 0)

    def test_trend_valid_and_not_zero_invented(self):
        anchor = date.today()
        points = [row(anchor - timedelta(days=13-i), 10 if i < 7 else 15) for i in range(14)]
        out = analyze(points)
        self.assertEqual(out["series"][0]["change_pct"], 50)
        self.assertEqual(out["candidates"][0]["status"], "需求指标上行（仅样本内）")

    def test_insufficient_evidence(self):
        out = analyze([row(date.today(), 8), row(date.today()-timedelta(days=8), 3)])
        self.assertIsNone(out["series"][0]["change_pct"])
        self.assertEqual(out["candidates"][0]["status"], "样本不足")

    def test_supply_does_not_count_as_demand(self):
        anchor = date.today()
        out = analyze([row(anchor - timedelta(days=13-i), 100 if i < 7 else 200,
                           metric="search_result_count") for i in range(14)])
        self.assertFalse(out["candidates"][0]["rankable"])
        self.assertEqual(out["candidates"][0]["status"], "仅有供给/位置线索")

    def test_csv_export_import(self):
        sample = [row(date.today(), 5)]
        contents = export_csv(sample)
        self.assertEqual(import_csv(self.conn, contents), 1)
        self.assertEqual(len(read_rows(self.conn, is_demo=False)), 1)
        self.assertEqual(import_csv(self.conn, contents), 1)
        self.assertEqual(len(read_rows(self.conn, is_demo=False)), 1)

    def test_csv_rejects_fake_demo_and_partial_transaction(self):
        base = row(date.today(), 5)
        false = dict(base, keyword="错行", source_type="demo")
        try:
            add_rows(self.conn, [base, false])
        except ValueError:
            pass
        self.assertEqual([], read_rows(self.conn, is_demo=False))

    def test_formula_escape(self):
        content = export_csv([dict(row(date.today(), 5), notes="=evil()")]).decode("utf-8-sig")
        self.assertIn("'=evil()", content)


if __name__ == "__main__":
    unittest.main()
