"""Signal Dashboard - Streamlit UI for browsing digests, trends, and articles."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from config import load_env
from storage.knowledge import KnowledgeStorage
import workspace as ws

st.set_page_config(
    page_title="Signal Dashboard",
    page_icon="📡",
    layout="wide",
)


def init_session():
    """Initialize session state with workspace selection."""
    if "workspace" not in st.session_state:
        st.session_state.workspace = ws.DEFAULT_WORKSPACE


@st.cache_resource
def get_storage(workspace: str):
    load_env()
    db_path = ws.get_db_path(workspace)
    storage = KnowledgeStorage(db_path=db_path)
    storage.initialize()
    return storage


def render_workspace_selector():
    """Render workspace selector in sidebar."""
    workspaces = ws.list_workspaces()
    with st.sidebar:
        st.header("🗂️ 工作区")
        current_idx = workspaces.index(st.session_state.workspace) if st.session_state.workspace in workspaces else 0
        selected = st.selectbox("选择工作区", workspaces, index=current_idx, label_visibility="collapsed")
        if selected != st.session_state.workspace:
            st.session_state.workspace = selected
            st.rerun()

        # Quick create
        with st.expander("➕ 新建工作区"):
            new_name = st.text_input("名称", key="new_ws_name", placeholder="如 finance、ai-papers")
            if st.button("创建", use_container_width=True) and new_name:
                try:
                    ws.create_workspace(new_name)
                    st.success(f"已创建 {new_name}")
                    st.session_state.workspace = new_name
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


def render_stats(storage: KnowledgeStorage):
    stats = storage.get_stats()
    cols = st.columns(4)
    labels = [("📄 文章", "articles"), ("📡 数据源", "sources"), ("📰 周报", "digests"), ("📅 周数", "weeks")]
    for col, (label, key) in zip(cols, labels):
        col.metric(label, stats[key])


def render_trends(storage: KnowledgeStorage):
    trends = storage.get_topic_trends(months=3)
    if not trends:
        st.info("暂无话题趋势数据")
        return

    st.subheader("📈 话题趋势")
    top_n = trends[:8]
    all_weeks = sorted({w["week"] for t in top_n for w in t["weeks"]})
    if not all_weeks:
        return

    chart_data = {}
    for t in top_n:
        week_map = {w["week"]: w["count"] for w in t["weeks"]}
        chart_data[t["topic"]] = [week_map.get(week, 0) for week in all_weeks]

    st.line_chart(chart_data, x_label="周", y_label="提及次数")

    rising = storage.get_rising_topics()
    if rising:
        st.subheader("🔥 上升趋势话题")
        for r in rising[:5]:
            st.write(f"- **{r['topic']}**：近期 {r['recent_count']} 次，此前平均 {r['avg_previous']} 次")


def render_source_distribution(storage: KnowledgeStorage):
    dist = storage.get_source_distribution(weeks=12)
    if not dist:
        st.info("暂无来源分布数据")
        return

    st.subheader("📊 来源分布（近 12 周）")
    st.bar_chart({d["source"]: d["count"] for d in dist[:10]})


def render_recent_digests(storage: KnowledgeStorage):
    digests = storage.get_digests(limit=5)
    if not digests:
        st.info("暂无周报数据")
        return

    st.subheader("📰 最近周报")
    for d in digests:
        with st.expander(f"{d['week']}（{d['article_count']} 篇文章）"):
            st.markdown(d["content"])


def main():
    init_session()
    render_workspace_selector()

    st.title("📡 Signal Dashboard")
    st.caption(f"工作区：{st.session_state.workspace}")

    storage = get_storage(st.session_state.workspace)

    prefs = storage.get_all_preferences()
    if not prefs.get("saved"):
        st.info("👋 欢迎使用 Signal！请先到 **设置** 页面选择你关注的领域。")
        st.page_link("pages/settings.py", label="⚙️ 前往设置", icon="⚙️")
        st.divider()

    render_stats(storage)
    st.divider()

    left, right = st.columns([2, 1])
    with left:
        render_trends(storage)
    with right:
        render_source_distribution(storage)

    st.divider()
    render_recent_digests(storage)


if __name__ == "__main__":
    main()
