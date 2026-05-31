"""Settings page - edit .env configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import DEFAULT_ENV_PATH

st.set_page_config(page_title="设置 - Sift", page_icon=":material/settings:")


def load_env_file() -> dict[str, str]:
    """Load .env file into a dict."""
    env_path = Path(DEFAULT_ENV_PATH)
    if not env_path.exists():
        return {}

    result = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def save_env_file(env: dict[str, str]) -> None:
    """Save dict back to .env file, preserving comments and order."""
    env_path = Path(DEFAULT_ENV_PATH)
    if not env_path.exists():
        # Create new file
        lines = [f"{k}={v}" for k, v in env.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Read existing file to preserve structure
    original = env_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    new_lines = []
    written_keys: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in stripped:
            key, _, _ = stripped.partition("=")
            key = key.strip()
            if key in env:
                new_lines.append(f"{key}={env[key]}")
                written_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append new keys that weren't in the original file
    for key, value in env.items():
        if key not in written_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def render_section(title: str, fields: list[tuple[str, str, str, str, bool]]):
    """Render a section of settings fields.

    Each field: (key, label, help_text, default, is_password)
    Returns dict of values.
    """
    st.subheader(title)
    values = {}
    for key, label, help_text, default, is_password in fields:
        input_type = "password" if is_password else "default"
        values[key] = st.text_input(
            label,
            value=st.session_state.env.get(key, default),
            help=help_text,
            key=f"env_{key}",
            type=input_type,
        )
    return values


def main():
    st.title("设置")
    st.caption("修改 .env 配置文件")

    # Initialize session state
    if "env" not in st.session_state:
        st.session_state.env = load_env_file()

    env = st.session_state.env

    # LLM API
    llm_values = render_section("LLM API", [
        ("API_BASE_URL", "API 地址", "OpenAI 兼容格式，支持 DeepSeek / 通义千问 / Kimi 等", "https://api.deepseek.com/v1", False),
        ("API_KEY", "API Key", "", "", True),
        ("MODEL_NAME", "模型名称", "", "deepseek-chat", False),
    ])

    st.divider()

    # Embedding API
    embedding_values = render_section("Embedding API", [
        ("EMBEDDING_API_BASE_URL", "Embedding API 地址", "用于知识库语义搜索", "https://api.siliconflow.cn/v1", False),
        ("EMBEDDING_API_KEY", "Embedding API Key", "", "", True),
        ("EMBEDDING_MODEL", "Embedding 模型", "", "Qwen/Qwen3-Embedding-4B", False),
        ("EMBEDDING_DIM", "向量维度", "需与模型匹配（默认 2560）", "2560", False),
    ])

    st.divider()

    # SMTP Email
    smtp_values = render_section("SMTP 邮件（可选）", [
        ("SMTP_SERVER", "SMTP 服务器", "如 smtp.qq.com", "", False),
        ("SMTP_PORT", "SMTP 端口", "如 587", "587", False),
        ("SMTP_SENDER", "发件人邮箱", "", "", False),
        ("SMTP_AUTH_CODE", "邮箱授权码", "QQ 邮箱需开启 POP3/SMTP 并生成授权码", "", True),
        ("SMTP_RECEIVER", "收件人邮箱", "", "", False),
    ])

    st.divider()

    # Summary settings
    summary_values = render_section("摘要设置", [
        ("SUMMARY_DAYS", "回溯天数", "默认 7 天", "7", False),
        ("SUMMARY_LANGUAGE", "输出语言", "zh-CN / en", "zh-CN", False),
        ("PROMPT_NAME", "提示词模板", "默认 tech-weekly", "tech-weekly", False),
    ])

    st.divider()

    # LLM parameters
    llm_params = render_section("LLM 参数（可选）", [
        ("LLM_TEMPERATURE", "生成温度", "0-2，默认 0.3", "0.3", False),
        ("LLM_MAX_TOKENS", "最大输出 token", "默认 4096", "4096", False),
    ])

    st.divider()

    # Other
    other_values = render_section("其他", [
        ("GITHUB_REPO_URL", "GitHub 仓库地址", "用于 GitHub Pages 页面链接", "", False),
        ("FETCH_MAX_WORKERS", "并发抓取线程数", "默认 8", "8", False),
    ])

    st.divider()

    # Save button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存配置", type="primary", use_container_width=True):
            # Merge all values
            all_values = {}
            for d in [llm_values, embedding_values, smtp_values, summary_values, llm_params, other_values]:
                for k, v in d.items():
                    if v:  # Only save non-empty values
                        all_values[k] = v

            save_env_file(all_values)
            st.session_state.env = load_env_file()
            st.success("配置已保存到 .env")

    with col2:
        if st.button("重新加载", use_container_width=True):
            st.session_state.env = load_env_file()
            st.rerun()

    # Show raw .env
    with st.expander("查看原始 .env 文件"):
        env_path = Path(DEFAULT_ENV_PATH)
        if env_path.exists():
            st.code(env_path.read_text(encoding="utf-8"), language="bash")
        else:
            st.info(".env 文件不存在")


if __name__ == "__main__":
    main()
