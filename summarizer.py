"""LLM summarizer - generates Chinese tech digest from fetched entries."""

import os
from openai import OpenAI


SYSTEM_PROMPT = """你是一位资深技术编辑，专注于将英文技术博客文章转化为高质量的中文技术周报。

## 输出要求
1. 按信息源分组，每组用 ## 标题标注来源
2. 每篇文章用 **加粗标题** + 2-3 句正文概括
3. 保留关键术语的英文原文（如 API、Kubernetes、LLM 等）
4. 突出"为什么这个重要"——技术意义或行业影响
5. 每篇附上原文链接，格式为 [原文链接](URL)
6. 不要用翻译腔，用自然流畅的中文表达
7. 如果不同源的文章有关联，在末尾用"### 本周看点"段落指出

## 输出格式（严格遵守）
- 标题: # 一级标题, ## 二级标题, ### 三级标题
- 加粗: **文字**
- 链接: [原文链接](https://...)  —— 必须用标准 markdown 链接格式
- 列表: 1. 或 -
- 每篇文章之间用空行分隔
- 不要输出任何 HTML 标签
"""


def _build_user_prompt(feed_results: list[dict], language: str) -> str:
    """Build the user prompt from fetched feed results."""
    parts = []
    total = 0
    for feed in feed_results:
        if feed["error"]:
            parts.append(f"### {feed['name']}（拉取失败: {feed['error']}）")
            continue
        if not feed["entries"]:
            parts.append(f"### {feed['name']}（本周无新文章）")
            continue

        parts.append(f"### {feed['name']}（{len(feed['entries'])} 篇）")
        for entry in feed["entries"]:
            parts.append(f"- **{entry['title']}**")
            if entry["summary"]:
                # Strip HTML tags for cleaner input
                import re
                clean = re.sub(r"<[^>]+>", "", entry["summary"])[:300]
                parts.append(f"  摘要: {clean}")
            parts.append(f"  链接: {entry['link']}")
            total += 1

    if total == 0:
        return "本周所有订阅源均无新文章发布。"

    header = f"以下是本周（最近 7 天）从 {len(feed_results)} 个技术博客收集到的 {total} 篇新文章。\n"
    header += f"请生成一份中文技术周报。目标语言: {language}\n\n"
    return header + "\n".join(parts)


def summarize(feed_results: list[dict], language: str = "zh-CN", trend_context: str = "") -> str:
    """Call LLM API to generate a Chinese tech digest."""
    client = OpenAI(
        api_key=os.environ["API_KEY"],
        base_url=os.environ["API_BASE_URL"],
    )
    model = os.environ.get("MODEL_NAME", "deepseek-chat")

    user_prompt = _build_user_prompt(feed_results, language)

    if "本周所有订阅源均无新文章" in user_prompt:
        return "本周所有订阅源均无新文章发布。\n"

    # Inject historical trend context if available
    if trend_context:
        user_prompt = trend_context + "\n\n" + user_prompt

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    return response.choices[0].message.content
