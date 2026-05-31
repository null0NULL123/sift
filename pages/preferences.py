"""Preferences page - view feedback history and smart recommendations."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import load_env
from storage.knowledge import KnowledgeStorage
import workspace as ws

st.set_page_config(page_title="我的偏好 - Signal", page_icon="🎯")


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


def render_feedback_stats(storage: KnowledgeStorage):
    """Render feedback statistics."""
    st.subheader("📊 反馈统计")

    stats = storage.get_feedback_stats()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("👍 喜欢", stats.get("like", 0))
    with col2:
        st.metric("👎 不喜欢", stats.get("dislike", 0))
    with col3:
        st.metric("⭐ 收藏", stats.get("bookmark", 0))


def render_preference_analysis(storage: KnowledgeStorage):
    """Render preference analysis based on feedback."""
    st.subheader("🎯 偏好分析")

    # Liked sources
    liked_sources = storage.get_liked_sources(5)
    if liked_sources:
        st.write("**偏好来源**：")
        for s in liked_sources:
            st.write(f"- {s['source']}（{s['count']} 篇）")

    # Liked tags
    liked_tags = storage.get_liked_tags(10)
    if liked_tags:
        st.write("**偏好话题**：")
        tags_str = " ".join(f"`{t['tag']}`" for t in liked_tags[:10])
        st.write(tags_str)


def render_article_card_simple(article):
    """Render a simple article card without feedback buttons."""
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
            st.write(clean[:200] + ("..." if len(clean) > 200 else ""))


def render_feedback_history(storage: KnowledgeStorage):
    """Render feedback history tabs."""
    st.subheader("📜 反馈历史")

    tab1, tab2, tab3 = st.tabs(["👍 喜欢", "⭐ 收藏", "👎 不喜欢"])

    with tab1:
        liked = storage.get_feedback_articles("like", limit=20)
        if liked:
            for article in liked:
                render_article_card_simple(article)
        else:
            st.info("还没有喜欢的文章。去文章浏览页面点赞吧！")

    with tab2:
        bookmarked = storage.get_feedback_articles("bookmark", limit=20)
        if bookmarked:
            for article in bookmarked:
                render_article_card_simple(article)
        else:
            st.info("还没有收藏的文章。去文章浏览页面收藏吧！")

    with tab3:
        disliked = storage.get_feedback_articles("dislike", limit=20)
        if disliked:
            for article in disliked:
                render_article_card_simple(article)
        else:
            st.info("还没有不喜欢的文章。")


def render_recommendations(storage: KnowledgeStorage):
    """Render smart recommendations based on feedback."""
    st.subheader("✨ 猜你喜欢")

    recommended = storage.get_recommended_articles(limit=10)
    if recommended:
        st.write("基于你喜欢和收藏的文章，为你推荐：")
        for article in recommended:
            render_article_card_simple(article)
    else:
        st.info("点赞或收藏一些文章后，系统会为你推荐相似内容。")


def main():
    init_session()
    render_workspace_selector()

    st.title("🎯 我的偏好")
    st.caption(f"工作区：{st.session_state.workspace}")
    st.write("通过点赞、收藏文章来训练你的偏好模型，系统会为你推荐更精准的内容。")

    storage = get_storage(st.session_state.workspace)

    # Feedback stats
    render_feedback_stats(storage)
    st.divider()

    # Preference analysis
    render_preference_analysis(storage)
    st.divider()

    # Feedback history
    render_feedback_history(storage)
    st.divider()

    # Recommendations
    render_recommendations(storage)


if __name__ == "__main__":
    main()
