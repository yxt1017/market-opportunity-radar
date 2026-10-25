"""市场机会雷达：可信的导入、存储、可比趋势分析。不包含未经授权的爬虫。"""
from __future__ import annotations

import csv
import io
import math
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median

PLATFORMS = ("拼多多", "小红书", "闲鱼", "其他")
OPPORTUNITY_TYPES = ("商品", "软件")
METRICS = {
    "search_index": ("平台搜索指数", "需求线索（相对指数）", "越高越强"),
    "platform_searches": ("平台披露的搜索次数", "需求线索（仅限明确授权数据）", "越高越强"),
    "shop_search_visitors": ("本店搜索来源访问量", "局部需求线索（仅本店）", "越高越强"),
    "search_result_count": ("观察到的搜索结果数", "供给观察（不是需求）", "越高不代表需求越强"),
    "content_count": ("观察到的相关内容数", "内容供给观察（不是需求）", "越高不代表需求越强"),
    "suggestion_rank": ("搜索建议词位置", "曝光位置观察（不是搜索量）", "数字越小位置越靠前"),
}
SOURCES = {
    "official_export": "用户声明：官方后台导出（未经系统验证）",
    "authorized_api": "用户声明：授权接口（未经系统验证）",
    "manual_observation": "人工观察记录",
    "third_party_estimate": "第三方提供/估算（待核验）",
    "demo": "模拟演示，非真实平台数据",
}
DEMAND_METRICS = {"search_index", "platform_searches", "shop_search_visitors"}
FIELDS = (
    "observed_date", "platform", "keyword", "opportunity_type", "metric_type",
    "metric_value", "source_type", "source_name", "source_scope", "source_url", "notes",
)


def connect(path: str | Path) -> sqlite3.Connection:
    dbpath = Path(path)
    dbpath.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(dbpath), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY,
        observed_date TEXT NOT NULL,
        platform TEXT NOT NULL,
        keyword TEXT NOT NULL,
        opportunity_type TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        metric_value REAL NOT NULL,
        source_type TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_scope TEXT NOT NULL,
        source_url TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        is_demo INTEGER NOT NULL DEFAULT 0,
        imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(observed_date, platform, keyword, opportunity_type,
               metric_type, source_name, source_scope, is_demo)
    )""")
    connection.commit()
    return connection


def validate_row(row: dict, *, is_demo: bool = False) -> dict:
    out = {key: str(row.get(key, "") if row.get(key) is not None else "").strip() for key in FIELDS}
    try:
        parsed_date = date.fromisoformat(out["observed_date"])
    except ValueError as exc:
        raise ValueError("observed_date 必须是 YYYY-MM-DD") from exc
    if parsed_date > date.today() + timedelta(days=1):
        raise ValueError("观察日期不能在未来超过一天")
    if out["platform"] not in PLATFORMS:
        raise ValueError(f"platform 必须是：{', '.join(PLATFORMS)}")
    if not out["keyword"] or len(out["keyword"]) > 80:
        raise ValueError("keyword 必须是1至80个字符")
    if out["opportunity_type"] not in OPPORTUNITY_TYPES:
        raise ValueError("opportunity_type 应为 商品 或 软件")
    if out["metric_type"] not in METRICS:
        raise ValueError(f"metric_type 未知：{out['metric_type']}")
    try:
        value = float(out["metric_value"])
    except ValueError as exc:
        raise ValueError("metric_value 必须是数字") from exc
    if not math.isfinite(value) or value < 0 or value > 10**15:
        raise ValueError("metric_value 必须是合理的非负有限数")
    if out["metric_type"] == "suggestion_rank" and (value < 1 or int(value) != value):
        raise ValueError("建议词排名必须是正整数")
    if out["source_type"] not in SOURCES:
        raise ValueError(f"source_type 未知：{out['source_type']}")
    if out["source_type"] == "demo" and not is_demo:
        raise ValueError("模拟数据不得导入真实数据区")
    if not out["source_name"] or not out["source_scope"]:
        raise ValueError("source_name 和 source_scope 必填，用于保障可比性")
    if len(out["source_name"]) > 120 or len(out["source_scope"]) > 160:
        raise ValueError("来源名称或统计范围过长")
    if out["source_url"] and not out["source_url"].startswith(("https://", "http://")):
        raise ValueError("source_url 需为 http(s) 地址或留空")
    if len(out["notes"]) > 600:
        raise ValueError("notes 不能超过600字符")
    out["metric_value"] = value
    out["is_demo"] = int(is_demo)
    return out


def add_rows(conn: sqlite3.Connection, rows: list[dict], *, is_demo: bool = False) -> int:
    cleaned = [validate_row(row, is_demo=is_demo) for row in rows]
    # 先全部验证再执行事务，避免一半导入成功一半失败。
    with conn:
        conn.executemany("""
        INSERT INTO observations (
            observed_date,platform,keyword,opportunity_type,metric_type,
            metric_value,source_type,source_name,source_scope,source_url,notes,is_demo
        ) VALUES (
            :observed_date,:platform,:keyword,:opportunity_type,:metric_type,
            :metric_value,:source_type,:source_name,:source_scope,:source_url,:notes,:is_demo
        ) ON CONFLICT(observed_date,platform,keyword,opportunity_type,metric_type,
                      source_name,source_scope,is_demo) DO UPDATE SET
            metric_value=excluded.metric_value,
            source_type=excluded.source_type,
            source_url=excluded.source_url,
            notes=excluded.notes,
            imported_at=CURRENT_TIMESTAMP
        """, cleaned)
    return len(cleaned)


def import_csv(conn: sqlite3.Connection, content: bytes) -> int:
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("文件不能超过2MB")
    try:
        stream = io.StringIO(content.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ValueError("文件请保存为 UTF-8 CSV 编码") from exc
    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise ValueError("CSV 没有表头")
    missing = set(FIELDS) - set(reader.fieldnames)
    if missing:
        raise ValueError("CSV 缺少字段：" + ", ".join(sorted(missing)))
    rows = []
    for i, row in enumerate(reader, start=2):
        if i > 20_001:
            raise ValueError("每次最多导入20000行")
        if None in row:  # 多出的未命名列
            raise ValueError(f"第{i}行含多余列")
        rows.append(row)
    if not rows:
        raise ValueError("CSV 内容为空")
    return add_rows(conn, rows)


def read_rows(conn: sqlite3.Connection, *, is_demo: bool) -> list[dict]:
    cur = conn.execute("""SELECT observed_date,platform,keyword,opportunity_type,
                         metric_type,metric_value,source_type,source_name,source_scope,
                         source_url,notes,is_demo
                         FROM observations WHERE is_demo=?
                         ORDER BY observed_date DESC, platform, keyword""", (int(is_demo),))
    return [dict(row) for row in cur.fetchall()]


def export_csv(rows: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    # CSV可能被Excel打开；对可能触发公式的用户可控文本作前缀转义。
    for row in rows:
        safe = {field: row.get(field, "") for field in FIELDS}
        for field in FIELDS:
            if field == "metric_value":
                continue
            val = str(safe[field])
            if val.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                safe[field] = "'" + val
        writer.writerow(safe)
    return output.getvalue().encode("utf-8-sig")


def demo_rows() -> list[dict]:
    # 全部为合成样本！不可被解释为平台真实趋势。
    configs = [
        ("小红书", "AI简历优化", "软件", "search_index", 45, .58),
        ("小红书", "图片批量处理", "软件", "search_index", 62, .26),
        ("小红书", "自学英语打卡", "软件", "search_index", 70, -.05),
        ("拼多多", "磁吸手机支架", "商品", "shop_search_visitors", 26, .65),
        ("拼多多", "透明手机壳", "商品", "shop_search_visitors", 34, .21),
        ("拼多多", "桌面理线器", "商品", "shop_search_visitors", 18, .34),
        ("闲鱼", "二手电脑升级", "软件", "search_result_count", 90, .20),
        ("闲鱼", "桌面收纳盒", "商品", "search_result_count", 70, .38),
    ]
    end_date = date.today() - timedelta(days=1)
    result = []
    for platform, keyword, kind, metric, baseline, growth in configs:
        for day_idx in range(14):
            observation_date = end_date - timedelta(days=13 - day_idx)
            value = baseline * (1 + ((day_idx % 3) - 1) * .035)
            if day_idx >= 7:
                value *= (1 + growth)
            result.append({
                "observed_date": observation_date.isoformat(),
                "platform": platform, "keyword": keyword,
                "opportunity_type": kind, "metric_type": metric,
                "metric_value": round(value, 1), "source_type": "demo",
                "source_name": "模拟数据生成器", "source_scope": f"{platform}的虚构观察样本",
                "source_url": "", "notes": "虚构样本；不代表任何平台实际趋势",
            })
    return result


def seed_demo(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM observations WHERE is_demo=1").fetchone()[0]
    if count == 0:
        add_rows(conn, demo_rows(), is_demo=True)


def analyze(rows: list[dict]) -> dict:
    """前7天 vs 更早7天同来源、同范围、同类型的均值变化。

    不把商品供给数当搜索需求；不把不同口径的绝对量相加。
    """
    if not rows:
        return {"asof": None, "series": [], "candidates": []}
    asof = max(date.fromisoformat(str(x["observed_date"])) for x in rows)
    current_from = asof - timedelta(days=6)
    previous_from = asof - timedelta(days=13)
    grouped = defaultdict(list)
    for row in rows:
        key = (row["platform"], row["keyword"], row["opportunity_type"],
               row["metric_type"], row["source_type"], row["source_name"], row["source_scope"])
        grouped[key].append(row)
    series = []
    for key, points in grouped.items():
        by_day = {}
        for point in points:
            by_day[str(point["observed_date"])] = float(point["metric_value"])
        before = [v for day, v in by_day.items() if previous_from <= date.fromisoformat(day) < current_from]
        after = [v for day, v in by_day.items() if current_from <= date.fromisoformat(day) <= asof]
        valid = len(before) >= 2 and len(after) >= 2 and mean(before) > 0
        change = None
        if valid:
            change = (mean(after) / mean(before) - 1) * 100
            if key[3] == "suggestion_rank":
                change = (1 - mean(after) / mean(before)) * 100
        series.append({
            "platform": key[0], "keyword": key[1], "opportunity_type": key[2],
            "metric_type": key[3], "source_type": key[4], "source_name": key[5],
            "source_scope": key[6], "metric_name": METRICS[key[3]][0],
            "metric_description": METRICS[key[3]][1],
            "current_value": mean(after) if after else None,
            "previous_value": mean(before) if before else None,
            "current_n": len(after), "previous_n": len(before),
            "change_pct": change, "valid": valid,
            "latest_date": max(by_day),
            "is_demand": key[3] in DEMAND_METRICS,
            "is_demo": key[4] == "demo",
        })
    candidates_group = defaultdict(list)
    for item in series:
        candidates_group[(item["keyword"], item["opportunity_type"])].append(item)
    candidates = []
    for (keyword, kind), elements in candidates_group.items():
        demand = [v for v in elements if v["valid"] and v["is_demand"]]
        up = [v for v in demand if v["change_pct"] > 0]
        platforms_up = len(set(v["platform"] for v in up))
        median_change = median(v["change_pct"] for v in demand) if demand else None
        sources = ", ".join(sorted(set(f"{v['platform']}·{v['metric_name']}" for v in elements)))
        label = (
            "需求指标上行（仅样本内）" if demand and median_change > 0 else
            "需求指标未上行" if demand else
            "仅有供给/位置线索" if any(v["valid"] for v in elements) else
            "样本不足"
        )
        candidates.append({
            "keyword": keyword, "opportunity_type": kind,
            "platforms": ", ".join(sorted(set(v["platform"] for v in elements))),
            "up_platforms": platforms_up, "median_change_pct": median_change,
            "demand_sources": len(demand), "sources": sources,
            "status": label, "rankable": bool(demand),
        })
    # 探索性排序：跨平台有独立的上涨信号优先，其次是样本内增幅。
    # 不称作“市场规模”、“利润预测”，也不将不同来源的绝对量加总。
    candidates.sort(key=lambda x: (not x["rankable"], -x["up_platforms"],
                                   -(x["median_change_pct"] if x["median_change_pct"] is not None else -10**6),
                                   x["keyword"]))
    return {"asof": asof.isoformat(), "series": series, "candidates": candidates}
