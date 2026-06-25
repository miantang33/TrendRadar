# coding=utf-8
"""
GitHub 推送模块

将热点报告以 Markdown 格式直接写入 GitHub 仓库。
文件命名：YYYYMMDD_HHmm.md
"""

import base64
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import requests


def send_to_github(
    github_token: str,
    github_repo: str,
    report_data: Dict,
    report_type: str,
    update_info: Optional[Dict] = None,
    proxy_url: Optional[str] = None,
    mode: str = "daily",
    account_label: str = "",
    *,
    get_time_func: Callable = None,
    rss_items: Optional[list] = None,
    rss_new_items: Optional[list] = None,
    ai_analysis: Any = None,
    display_regions: Optional[Dict] = None,
    standalone_data: Optional[Dict] = None,
    repo_path: str = "头条写作/hotspots",
) -> bool:
    """
    将热点报告直接写入 GitHub 仓库（Markdown 文件）
    """
    log_prefix = f"GitHub{account_label}" if account_label else "GitHub"
    now = get_time_func() if get_time_func else datetime.now()

    timestamp = now.strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}.md"

    # 构建 Markdown 内容
    lines = []
    lines.append(f"# 热点推送 {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total_news = sum(
        len(stat.get("titles", [])) for stat in report_data.get("stats", [])
    )
    lines.append(f"总新闻数：{total_news}")
    lines.append(f"类型：{report_type}")

    new_titles = report_data.get("new_titles", [])
    if new_titles:
        new_count = sum(len(src.get("titles", [])) for src in new_titles)
        lines.append(f"🆕 本次新增热点新闻 (共 {new_count} 条)")
    lines.append("")

    for stat in report_data.get("stats", []):
        source_titles = stat.get("titles", [])
        if not source_titles:
            continue

        # 优先从 stat 取，fallback 到第一个 title 的 source_name
        source_name = stat.get("source_name") or stat.get("name")
        if not source_name and source_titles:
            source_name = source_titles[0].get("source_name", "")
        if not source_name:
            source_name = "未知来源"
        lines.append(f"## {source_name} ({len(source_titles)} 条)")
        lines.append("")

        for item in source_titles:
            title = item.get("title", "").strip()
            if not title:
                continue

            link_url = item.get("mobile_url") or item.get("url", "")

            if link_url:
                formatted = f"- [{title}]({link_url})"
            else:
                formatted = f"- {title}"

            ranks = item.get("ranks", [])
            if ranks:
                rank_str = ",".join(str(r) for r in ranks[:3])
                formatted += f" [热度{rank_str}]"

            if item.get("is_new"):
                formatted += " 🆕"

            lines.append(formatted)

        lines.append("")

    if update_info:
        lines.append("---")
        lines.append(f"版本更新：{update_info.get('version', '')}")
        lines.append("")

    markdown_content = "\n".join(lines)

    api_url = (
        f"https://api.github.com/repos/{github_repo}/contents/{repo_path}/{filename}"
    )

    content_bytes = markdown_content.encode("utf-8")
    content_base64 = base64.b64encode(content_bytes).decode("ascii")

    commit_message = (
        f"hotspots: {now.strftime('%Y-%m-%d %H:%M')} {report_type} ({total_news} 条)"
    )

    payload = {
        "message": commit_message,
        "content": content_base64,
    }

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "TrendRadar/2.2",
    }

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        print(f"📡 {log_prefix} 正在写入：{repo_path}/{filename}")
        response = requests.put(
            api_url, headers=headers, json=payload, proxies=proxies, timeout=30
        )
        if response.status_code in (200, 201):
            result = response.json()
            html_url = result.get("content", {}).get("html_url", "")
            print(f"✅ {log_prefix} 写入成功：{html_url}")
            return True
        else:
            print(f"❌ {log_prefix} 写入失败 [{response.status_code}]：{response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ {log_prefix} 写入异常：{e}")
        return False
