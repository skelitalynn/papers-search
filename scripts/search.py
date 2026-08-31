#!/usr/bin/env python3
"""搜集并筛选可信调研来源。"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable


MIN_YEAR = 2025
PAPER_HOSTS = {
    "arxiv.org",
    "doi.org",
    "openreview.net",
}
SEO_HOSTS = {
    "medium.com",
    "towardsdatascience.com",
    "dev.to",
    "geeksforgeeks.org",
    "tutorialspoint.com",
}


@dataclass(frozen=True)
class Candidate:
    """一个待复核的来源候选。"""

    title: str
    url: str
    source_type: str
    year: int | None
    accepted: bool
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "按关键词检索 2025 年及以后的原始论文，并筛选用户提供的官方候选来源。"
            "输出只是候选清单，不能替代人工证据验证。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python3 scripts/search.py "multi agent orchestration"
  python3 scripts/search.py "resource lock" --offline \\
    --official-domain docs.python.org \\
    --official-github-owner python \\
    --candidate 'urllib.request 文档|https://docs.python.org/3/library/urllib.request.html|2026'

候选格式为“标题|URL|年份”。严格模式下，年份缺失或早于 2025 会被过滤。
只有显式声明的官方域名和 GitHub owner 才会被视为官方来源。
""",
    )
    parser.add_argument("keywords", nargs="+", help="检索关键词，可传一个短语或多个词")
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        metavar="标题|URL|年份",
        help="加入一个待筛选链接，可重复使用",
    )
    parser.add_argument(
        "--official-domain",
        action="append",
        default=[],
        metavar="域名",
        help="声明项目官方文档或博客域名，可重复使用",
    )
    parser.add_argument(
        "--official-github-owner",
        action="append",
        default=[],
        metavar="OWNER",
        help="声明官方 GitHub 组织或用户；联网时也会检索该 owner 的仓库",
    )
    parser.add_argument("--limit", type=int, default=10, help="每类在线来源的最大结果数，默认 10")
    parser.add_argument("--timeout", type=float, default=15.0, help="网络超时秒数，默认 15")
    parser.add_argument("--offline", action="store_true", help="不访问网络，只筛选 --candidate")
    parser.add_argument("--show-rejected", action="store_true", help="同时显示被过滤来源及原因")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，便于后续处理")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit 必须大于 0")
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    return args


def normalized_host(value: str) -> str:
    """规范化域名，去掉端口和 www 前缀。"""

    host = urllib.parse.urlparse(value if "://" in value else f"https://{value}").hostname
    if not host:
        return ""
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def host_matches(host: str, trusted_domains: set[str]) -> bool:
    """仅允许目标域名本身或其子域名。"""

    return any(host == domain or host.endswith(f".{domain}") for domain in trusted_domains)


def github_owner(url: str) -> str | None:
    """从 GitHub 或 raw URL 中提取 owner。"""

    parsed = urllib.parse.urlparse(url)
    host = normalized_host(url)
    parts = [part for part in parsed.path.split("/") if part]
    if host == "github.com" and len(parts) >= 2:
        return parts[0].lower()
    if host == "raw.githubusercontent.com" and len(parts) >= 3:
        return parts[0].lower()
    return None


def classify_candidate(
    title: str,
    url: str,
    year: int | None,
    official_domains: set[str],
    official_owners: set[str],
) -> Candidate:
    """分类候选，并执行来源和时间过滤。"""

    parsed = urllib.parse.urlparse(url)
    host = normalized_host(url)
    if parsed.scheme not in {"http", "https"} or not host:
        return Candidate(title, url, "blog", year, False, "不是有效的 HTTP(S) 链接")

    if host_matches(host, SEO_HOSTS):
        return Candidate(title, url, "seo", year, False, "命中 SEO 或通用内容平台黑名单")

    owner = github_owner(url)
    if owner is not None:
        accepted = owner in official_owners
        reason = "GitHub owner 已显式确认为官方" if accepted else "GitHub owner 未声明为官方"
        source_type = "official-github"
    elif host_matches(host, PAPER_HOSTS):
        accepted = True
        reason = "原始论文平台"
        source_type = "paper"
    elif host_matches(host, official_domains):
        blog_markers = {"blog", "blogs", "news", "posts", "case-studies", "case-study"}
        path_parts = {part.lower() for part in parsed.path.split("/") if part}
        source_type = "blog" if path_parts & blog_markers else "official-doc"
        accepted = True
        reason = "域名已显式确认为官方"
    else:
        return Candidate(title, url, "blog", year, False, "非官方域名或未声明的来源")

    if year is None:
        return Candidate(title, url, source_type, year, False, "无法确认资料年份")
    if year < MIN_YEAR:
        return Candidate(title, url, source_type, year, False, f"资料早于 {MIN_YEAR} 年")
    return Candidate(title, url, source_type, year, accepted, reason)


def parse_candidate(raw: str) -> tuple[str, str, int | None]:
    """解析“标题|URL|年份”格式。"""

    parts = [part.strip() for part in raw.split("|")]
    if len(parts) == 1:
        return parts[0], parts[0], None
    if len(parts) not in {2, 3}:
        raise ValueError("候选必须是“标题|URL|年份”格式")
    title, url = parts[0], parts[1]
    year = None
    if len(parts) == 3 and parts[2]:
        if not parts[2].isdigit() or len(parts[2]) != 4:
            raise ValueError(f"年份无效：{parts[2]}")
        year = int(parts[2])
    return title or url, url, year


def request_bytes(url: str, timeout: float, accept: str) -> bytes:
    """执行带明确身份和响应类型的 GET 请求。"""

    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "papers-search/1.0 evidence-research",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def search_arxiv(query: str, limit: int, timeout: float) -> list[Candidate]:
    """通过 arXiv 官方 API 搜索原始论文。"""

    params = urllib.parse.urlencode(
        {
            "search_query": f'all:"{query}"',
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    data = request_bytes(
        f"https://export.arxiv.org/api/query?{params}",
        timeout,
        "application/atom+xml",
    )
    root = ET.fromstring(data)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[Candidate] = []
    for entry in root.findall("atom:entry", namespace):
        title = " ".join((entry.findtext("atom:title", default="", namespaces=namespace)).split())
        url = entry.findtext("atom:id", default="", namespaces=namespace).strip()
        published = entry.findtext("atom:published", default="", namespaces=namespace).strip()
        try:
            year = datetime.fromisoformat(published.replace("Z", "+00:00")).year
        except ValueError:
            year = None
        accepted = year is not None and year >= MIN_YEAR
        reason = "arXiv 原始论文" if accepted else f"论文早于 {MIN_YEAR} 年或日期不可识别"
        results.append(Candidate(title or url, url, "paper", year, accepted, reason))
    return results


def search_github_owner(query: str, owner: str, limit: int, timeout: float) -> list[Candidate]:
    """只在已声明为官方的 owner 范围内搜索仓库。"""

    params = urllib.parse.urlencode(
        {
            "q": f"{query} user:{owner}",
            "per_page": limit,
            "sort": "updated",
            "order": "desc",
        }
    )
    data = request_bytes(
        f"https://api.github.com/search/repositories?{params}",
        timeout,
        "application/vnd.github+json",
    )
    payload = json.loads(data.decode("utf-8"))
    results: list[Candidate] = []
    for item in payload.get("items", []):
        pushed_at = str(item.get("pushed_at") or "")
        year = int(pushed_at[:4]) if pushed_at[:4].isdigit() else None
        accepted = year is not None and year >= MIN_YEAR
        reason = "官方 owner 下的开源仓库" if accepted else "仓库更新时间早于时间边界或不可识别"
        results.append(
            Candidate(
                str(item.get("full_name") or item.get("name") or "未命名仓库"),
                str(item.get("html_url") or ""),
                "official-github",
                year,
                accepted,
                reason,
            )
        )
    return results


def unique_candidates(items: Iterable[Candidate]) -> list[Candidate]:
    """按规范 URL 去重，并保留首次出现的证据。"""

    seen: set[str] = set()
    result: list[Candidate] = []
    for item in items:
        key = item.url.rstrip("/")
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def markdown_escape(value: object) -> str:
    """转义 Markdown 表格中的分隔符。"""

    return str(value if value is not None else "未知").replace("|", "\\|").replace("\n", " ")


def print_markdown(items: list[Candidate], show_rejected: bool) -> None:
    """输出便于复制进调研记录的表格。"""

    visible = [item for item in items if item.accepted or show_rejected]
    print("| 状态 | 来源类型 | 年份 | 标题 | 链接 | 说明 |")
    print("|---|---|---:|---|---|---|")
    for item in visible:
        status = "候选" if item.accepted else "过滤"
        link = f"[{markdown_escape(item.url)}]({item.url})" if item.url else ""
        print(
            f"| {status} | {item.source_type} | {markdown_escape(item.year)} | "
            f"{markdown_escape(item.title)} | {link} | {markdown_escape(item.reason)} |"
        )


def main() -> int:
    args = parse_args()
    query = " ".join(args.keywords).strip()
    official_domains = {normalized_host(value) for value in args.official_domain}
    official_domains.discard("")
    official_owners = {value.strip().lower() for value in args.official_github_owner if value.strip()}

    items: list[Candidate] = []
    input_errors = 0
    for raw in args.candidate:
        try:
            title, url, year = parse_candidate(raw)
            items.append(classify_candidate(title, url, year, official_domains, official_owners))
        except ValueError as exc:
            input_errors += 1
            print(f"候选格式错误：{exc}；输入={raw!r}", file=sys.stderr)

    network_errors = 0
    if not args.offline:
        try:
            items.extend(search_arxiv(query, args.limit, args.timeout))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            network_errors += 1
            print(f"arXiv 检索失败：{exc}", file=sys.stderr)
        for owner in sorted(official_owners):
            try:
                items.extend(search_github_owner(query, owner, args.limit, args.timeout))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                network_errors += 1
                print(f"GitHub owner {owner} 检索失败：{exc}", file=sys.stderr)

    items = unique_candidates(items)
    accepted = [item for item in items if item.accepted]
    rejected = [item for item in items if not item.accepted]

    if args.json:
        payload = {
            "query": query,
            "minimum_year": MIN_YEAR,
            "accepted": [asdict(item) for item in accepted],
            "rejected": [asdict(item) for item in rejected] if args.show_rejected else [],
            "network_errors": network_errors,
            "input_errors": input_errors,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_markdown(items, args.show_rejected)
        print(f"\n保留 {len(accepted)} 条，过滤 {len(rejected)} 条。", file=sys.stderr)
        if rejected and not args.show_rejected:
            print("使用 --show-rejected 查看过滤原因。", file=sys.stderr)

    if input_errors or network_errors:
        return 2
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
