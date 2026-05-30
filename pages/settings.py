"""Settings page - interactive preference configuration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import load_env
from storage.knowledge import KnowledgeStorage
import workspace as ws

st.set_page_config(page_title="设置 - Signal", page_icon="⚙️")

TOPICS = [
    "AI/ML", "后端开发", "前端开发", "数据库", "云原生",
    "DevOps", "安全", "编程语言", "开源项目", "架构设计",
    "移动开发", "大数据", "区块链", "游戏开发", "硬件/嵌入式",
]

DETAIL_LEVELS = ["精简（一句话）", "标准", "详细"]
LANGUAGES = ["中文", "英文", "双语"]


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


def load_preferences(storage: KnowledgeStorage) -> dict:
    raw = storage.get_preference("topics", "[]")
    topics = json.loads(raw) if raw else []
    return {
        "topics": topics,
        "detail_level": storage.get_preference("detail_level", "标准"),
        "language": storage.get_preference("language", "中文"),
        "saved": storage.get_preference("saved", "") == "true",
    }


def save_preferences(storage: KnowledgeStorage, prefs: dict):
    storage.set_preference("topics", json.dumps(prefs["topics"], ensure_ascii=False))
    storage.set_preference("detail_level", prefs["detail_level"])
    storage.set_preference("language", prefs["language"])
    storage.set_preference("saved", "true")


def main():
    init_session()
    render_workspace_selector()

    st.title("⚙️ 设置")
    st.caption(f"工作区：{st.session_state.workspace}")
    st.write("选择你关注的领域和偏好，系统会据此定制周报内容。")

    storage = get_storage(st.session_state.workspace)
    prefs = load_preferences(storage)

    # Topic selection
    st.subheader("🎯 关注领域")
    st.write("选择你感兴趣的话题（可多选）：")

    selected_topics = []
    cols = st.columns(3)
    for i, topic in enumerate(TOPICS):
        with cols[i % 3]:
            if st.checkbox(topic, value=topic in prefs["topics"], key=f"topic_{topic}"):
                selected_topics.append(topic)

    # Detail level
    st.subheader("📝 摘要详细度")
    detail_level = st.radio(
        "选择摘要的详细程度：",
        DETAIL_LEVELS,
        index=DETAIL_LEVELS.index(prefs["detail_level"]) if prefs["detail_level"] in DETAIL_LEVELS else 1,
        horizontal=True,
    )

    # Language
    st.subheader("🌐 语言偏好")
    language = st.radio(
        "周报输出语言：",
        LANGUAGES,
        index=LANGUAGES.index(prefs["language"]) if prefs["language"] in LANGUAGES else 0,
        horizontal=True,
    )

    st.divider()

    if selected_topics:
        st.subheader("📋 偏好预览")
        st.write(f"**关注领域**：{', '.join(selected_topics)}")
        st.write(f"**摘要详细度**：{detail_level}")
        st.write(f"**语言**：{language}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存偏好", type="primary", use_container_width=True):
            new_prefs = {
                "topics": selected_topics,
                "detail_level": detail_level,
                "language": language,
                "saved": True,
            }
            save_preferences(storage, new_prefs)
            st.success("✅ 偏好已保存！生成周报时会参考你的偏好。")
            st.rerun()

    with col2:
        if st.button("🗑️ 清除偏好", use_container_width=True):
            storage.set_preference("saved", "false")
            storage.set_preference("topics", "[]")
            st.info("偏好已清除。")
            st.rerun()

    if prefs["saved"]:
        st.divider()
        st.caption(f"当前已保存偏好：{', '.join(prefs['topics']) or '未选择'} | {prefs['detail_level']} | {prefs['language']}")


if __name__ == "__main__":
    main()
