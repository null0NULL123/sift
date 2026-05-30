"""Articles page - browse, search, and filter articles."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import load_env
from storage.knowledge import KnowledgeStorage
import workspace as ws

st.set_page_config(page_title="文章 - Signal", page_icon="📄")


def init_session():
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
    workspaces = ws.list_workspaces()
    with st.sidebar:
        st.header("🗂️ 工作区")
        current_idx = workspaces.index(st.session_state.workspace) if st.session_state.workspace in workspaces else 0
        selected = st.selectbox("选择工作区", workspaces, index=current_idx, label_visibility="collapsed")
        if selected != st.session_state.workspace:
            st.session_state.workspace = selected
            st.rerun()


def render_article_card(article):
    with st.container(border=True):
        st.markdown(f"**[{article.title}]({article.link})**")
        meta_parts = []
        if article.source:
            meta_parts.append(f"📡 {article.source}")
        if article.week:
            meta_parts.append(f"📅 {article.week}")
        if article.published:
            meta_parts.append(f"🕐 {article.published[:10]}")
        if meta_parts:
            st.caption(" | ".join(meta_parts))
        if article.summary:
            clean = re.sub(r"<[^>]+>", "", article.summary)
            st.write(clean[:300] + ("..." if len(clean) > 300 else ""))
        if article.tags:
            st.write(" ".join(f"`{t}`" for t in article.tags))


def main():
    init_session()
    render_workspace_selector()

    st.title("📄 文章浏览")
    st.caption(f"工作区：{st.session_state.workspace}")

    storage = get_storage(st.session_state.workspace)

    # Sidebar filters
    with st.sidebar:
        st.divider()
        st.header("筛选")
        weeks = st.slider("回溯周数", 1, 24, 4)
        keyword = st.text_input("关键词搜索")

    # Get articles
    articles = storage.get_articles(weeks=weeks)

    # Apply keyword filter
    if keyword:
        kw = keyword.lower()
        articles = [a for a in articles if kw in a.title.lower() or kw in (a.summary or "").lower()]

    # Stats
    st.caption(f"共 {len(articles)} 篇文章")

    if not articles:
        st.info("没有找到匹配的文章。试试扩大回溯周数或换个关键词。")
        return

    # Source filter
    sources = sorted({a.source for a in articles if a.source})
    if sources:
        selected_sources = st.multiselect("按来源筛选", sources, default=sources)
        articles = [a for a in articles if a.source in selected_sources]

    # Display
    for article in articles[:50]:
        render_article_card(article)

    if len(articles) > 50:
        st.caption(f"仅显示前 50 篇，共 {len(articles)} 篇")


if __name__ == "__main__":
    main()
