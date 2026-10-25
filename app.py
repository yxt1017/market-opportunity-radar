from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from core import (FIELDS, METRICS, OPPORTUNITY_TYPES, PLATFORMS, SOURCES,
                  add_rows, analyze, connect, export_csv, import_csv,
                  read_rows, seed_demo)

BASE = Path(__file__).resolve().parent
DATABASE = BASE / "data" / "opportunity_radar.sqlite3"

st.set_page_config(page_title="市场机会雷达 · V1", page_icon="📡", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1320px;}
h1,h2,h3 {letter-spacing: -.6px;}
div[data-testid="stMetric"] {background:rgba(128,128,128,.055);border:1px solid rgba(128,128,128,.14);padding:16px;border-radius:14px;}
div[data-testid="stAlert"] {border-radius:12px;}
</style>
""", unsafe_allow_html=True)

conn = connect(DATABASE)
seed_demo(conn)

with st.sidebar:
    st.title("📡 市场机会雷达")
    st.caption("V1 · 本地离线分析 / 手动导入")
    view = st.radio("数据区域", ["真实导入数据", "模拟演示数据"], index=0)
    is_demo = view == "模拟演示数据"
    st.markdown("---")
    st.caption("数据采集状态")
    st.info("尚未接入任何平台的实时采集；不包含自动爬虫。")
    st.caption("分析口径：最新观测日期向前7日均值，对比此前7日均值；每段至少2次观察。")
    st.caption("数据源真实性需人工核查。标注‘官方导出’不等于本系统已核验。")

rows = read_rows(conn, is_demo=is_demo)
result = analyze(rows)

st.title("市场机会雷达")
st.caption("将真实观察与猜测分开 · 商品机会 × 软件机会 · 来源可追溯")
if is_demo:
    st.error("🚧 当前为【模拟演示数据】：所有词、数值、趋势均为虚构，绝不代表真实平台表现。")
else:
    st.success("📁 当前为【真实数据区】：仅显示你导入的数据；其来源真实性仍需人工核查。")

if not is_demo and not rows:
    st.warning("真实数据区尚无记录。打开「导入数据」上传 CSV，或切换左侧「模拟演示数据」体验界面。")

tab_all, tab_product, tab_software, tab_import, tab_provenance = st.tabs(
    ["📊 统一分析", "📦 商品机会", "💻 软件机会", "📥 导入数据", "🔍 来源与质量"]
)


def candidate_table(items):
    if not items:
        st.info("暂无可展示的关键词。")
        return
    df = pd.DataFrame([{
        "关键词": item["keyword"],
        "类别": item["opportunity_type"],
        "涉及平台": item["platforms"],
        "趋势判断": item["status"],
        "有效需求来源": item["demand_sources"],
        "趋势上涨平台数": item["up_platforms"],
        "需求线索变化中位数": f"{item['median_change_pct']:+.1f}%" if item["median_change_pct"] is not None else "无可比需求数据",
    } for item in items])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("表格是【候选复核顺序】，不是市场规模榜：先看上涨平台数，再看已比较的需求指标变化中位数。各来源指标口径可能不同，变化率只能作为筛选线索。")


def show_chart(kind: str | None = None):
    candidates = result["candidates"]
    if kind:
        candidates = [x for x in candidates if x["opportunity_type"] == kind]
    if not candidates:
        return
    labels = [f"{x['keyword']}（{x['opportunity_type']}）" for x in candidates]
    chosen = st.selectbox("查看关键词的原始观察历史", labels, key=f"keyword_{kind or 'all'}")
    item = candidates[labels.index(chosen)]
    filtered = [r for r in rows if r["keyword"] == item["keyword"] and r["opportunity_type"] == item["opportunity_type"]]
    if not filtered:
        return
    series_keys = list(dict.fromkeys(
        (x["platform"], x["metric_type"], x["source_name"], x["source_scope"]) for x in filtered
    ))
    choices = [f"{p} | {METRICS[m][0]} | {s} | {scope}" for p, m, s, scope in series_keys]
    series_chosen = st.selectbox("数据系列（指标、来源和范围必须一致才能比较）", choices, key=f"series_{kind or 'all'}")
    p, m, s, scope = series_keys[choices.index(series_chosen)]
    points = [r for r in filtered if
              (r["platform"], r["metric_type"], r["source_name"], r["source_scope"]) == (p, m, s, scope)]
    df = pd.DataFrame(points)
    df["observed_date"] = pd.to_datetime(df["observed_date"])
    df = df.sort_values("observed_date").set_index("observed_date")
    st.line_chart(df[["metric_value"]].rename(columns={"metric_value": METRICS[m][0]}))
    st.caption(f"指标说明：{METRICS[m][1]}。数据源标记：{SOURCES[points[0]['source_type']]}")

with tab_all:
    a, b, c, d = st.columns(4)
    a.metric("独立关键词", len({(r["keyword"],r["opportunity_type"]) for r in rows}))
    b.metric("商品候选", sum(x["opportunity_type"] == "商品" for x in result["candidates"]))
    c.metric("软件候选", sum(x["opportunity_type"] == "软件" for x in result["candidates"]))
    d.metric("历史观察条数", len(rows))
    st.caption(f"最近观测日期：{result['asof'] or '无'}；不是自动实时更新时间。")
    st.subheader("综合候选榜（供下一步人工复核）")
    candidate_table(result["candidates"])
    show_chart()

with tab_product:
    st.subheader("商品机会候选榜")
    st.caption("关注需求是否上行；没有成本、订单和利润数据时不推断盈利。")
    candidate_table([x for x in result["candidates"] if x["opportunity_type"] == "商品"])
    show_chart("商品")

with tab_software:
    st.subheader("软件机会候选榜")
    st.caption("搜索热度不等于愿意付费。需后续验证具体痛点、付费意愿及开发成本。")
    candidate_table([x for x in result["candidates"] if x["opportunity_type"] == "软件"])
    show_chart("软件")

with tab_import:
    st.subheader("导入真实观察数据")
    if is_demo:
        st.info("演示区不允许混入真实记录；CSV 总是导入真实数据区。导入后请切换左侧数据区域。")
    st.write("只接受 UTF-8 CSV；每一行是一个关键词在某日期、某数据源、某种指标下的观察。")
    template = [{
        "observed_date": date.today().isoformat(),
        "platform": "拼多多", "keyword": "示例词（请替换）", "opportunity_type": "商品",
        "metric_type": "shop_search_visitors", "metric_value": "10",
        "source_type": "manual_observation", "source_name": "我的店铺后台人工记录",
        "source_scope": "店铺A·搜索来源访客", "source_url": "",
        "notes": "仅用于说明格式；并非真实数据",
    }]
    st.download_button("⬇️ 下载 CSV 空间格式示例（含一行占位示例）",
                       export_csv(template), "导入模板.csv", "text/csv")
    uploaded = st.file_uploader("选择 CSV 文件", type=["csv"])
    if uploaded is not None:
        try:
            content = uploaded.getvalue()
            preview = pd.read_csv(__import__("io").BytesIO(content), encoding="utf-8-sig", nrows=20)
            st.dataframe(preview, hide_index=True, use_container_width=True)
            if st.button("确认导入真实数据区", type="primary"):
                count = import_csv(conn, content)
                st.success(f"已导入或更新 {count} 行。相同日期、来源和指标会更新原观察。请刷新界面查看结果。")
        except Exception as exc:
            st.error(f"文件不能读取：{exc}")
    st.markdown("---")
    st.subheader("新增一条手工观察")
    with st.form("single_entry", clear_on_submit=True):
        x1, x2, x3 = st.columns(3)
        obs_day = x1.date_input("观察日期", value=date.today())
        platform = x2.selectbox("平台", PLATFORMS)
        kind = x3.selectbox("机会类别", OPPORTUNITY_TYPES)
        keyword = st.text_input("关键词")
        metric = st.selectbox("指标类型", list(METRICS), format_func=lambda x: METRICS[x][0])
        value = st.number_input("记录数值（原始数据，不要自行换算）", min_value=0.0, value=0.0, step=1.0)
        source_type = st.selectbox("来源类型", list(SOURCES)[:-1],
                                   format_func=lambda x: SOURCES[x])
        source_name = st.text_input("来源名称（必填）", placeholder="例如：我的拼多多店铺后台")
        source_scope = st.text_input("统计范围（必填）", placeholder="例如：手机壳店·搜索来源访客")
        source_url = st.text_input("来源链接（可留空）")
        notes = st.text_area("观察说明（可留空）")
        submitted = st.form_submit_button("保存观察")
        if submitted:
            try:
                add_rows(conn, [{
                    "observed_date": obs_day.isoformat(), "platform": platform,
                    "keyword": keyword, "opportunity_type": kind,
                    "metric_type": metric, "metric_value": value,
                    "source_type": source_type, "source_name": source_name,
                    "source_scope": source_scope, "source_url": source_url, "notes": notes,
                }])
                st.success("保存成功。刷新网页后可查看更新的榜单。")
            except ValueError as exc:
                st.error(str(exc))

with tab_provenance:
    st.subheader("数据完整性与出处")
    st.write("以下只是【导入者声明的数据来源】，不代表程序已核实原始文件的真实性。")
    if rows:
        data = pd.DataFrame(rows)
        data["来源声明"] = data["source_type"].map(SOURCES)
        data["指标含义"] = data["metric_type"].map(lambda m: METRICS[m][1])
        st.dataframe(data[["observed_date", "platform", "keyword", "opportunity_type",
                           "metric_type", "metric_value", "来源声明", "source_name", "source_scope", "指标含义", "source_url"]],
                     use_container_width=True, hide_index=True)
        st.download_button("⬇️ 导出当前区历史数据", export_csv(rows),
                           "市场机会雷达_演示数据.csv" if is_demo else "市场机会雷达_真实记录.csv", "text/csv")
    else:
        st.info("没有记录可以审核。")
    st.markdown("""
**数据约束**

- 官方店铺数据只代表该店铺或账号；不能推成全网搜索量。
- 搜索指数是相对量，不是搜索次数；展示位次的变化不是搜索量变化。
- 商品数量、内容发布量属于供给侧指标，不会自动进入需求上涨排名。
- 只有同平台、同来源、同范围、同指标、前后两个7日各至少2次观察，才计算趋势。
- 导入的“官方后台”是导入者声明；未验真、不保证覆盖率、样本无偏或数据及时性。
- 目前没有平台实时 API、没有登录授权，也没有自动采集。任何外部数据必须合法取得。
""")

st.markdown("---")
st.caption("V1 本地版 · 不包含付费服务 · 演示与真实数据物理标记隔离 · 无未经授权自动采集")
