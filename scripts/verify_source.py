#!/usr/bin/env python3
"""抓取官方 GitHub 文件的 raw 内容并验证机制关键词。"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KeywordResult:
    """单个机制关键词的匹配结果。"""

    keyword: str
    found: bool
    lines: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="接收官方 GitHub 文件 URL，抓取 raw 内容并检查指定机制关键词。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python3 scripts/verify_source.py \\
    https://github.com/owner/repo/blob/main/path/file.py spawn_agent
  python3 scripts/verify_source.py \\
    https://raw.githubusercontent.com/owner/repo/COMMIT/path/file.py \\
    resource_lock acquire --require all --ignore-case

建议最终证据使用固定 commit SHA，而不是会变化的分支名。
""",
    )
    parser.add_argument("url", help="github.com 的 blob 文件 URL 或 raw.githubusercontent.com URL")
    parser.add_argument("keywords", nargs="+", help="要验证的一个或多个机制关键词")
    parser.add_argument(
        "--require",
        choices=("any", "all"),
        default="all",
        help="判定成功所需命中方式，默认 all",
    )
    parser.add_argument("--ignore-case", action="store_true", help="忽略关键词大小写")
    parser.add_argument("--timeout", type=float, default=15.0, help="网络超时秒数，默认 15")
    parser.add_argument("--max-lines", type=int, default=20, help="每个关键词最多报告的命中行号，默认 20")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出验证报告")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    if args.max_lines < 1:
        parser.error("--max-lines 必须大于 0")
    return args


def to_raw_url(url: str) -> str:
    """把 GitHub blob 链接转换成 raw 链接，并拒绝其他站点。"""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("只接受 HTTPS URL")
    host = (parsed.hostname or "").lower()
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]

    if host == "raw.githubusercontent.com":
        if len(parts) < 4:
            raise ValueError("raw URL 缺少 owner、repo、ref 或文件路径")
        return urllib.parse.urlunparse(("https", host, parsed.path, "", "", ""))

    if host != "github.com":
        raise ValueError("只接受 github.com 或 raw.githubusercontent.com")
    if len(parts) < 5 or parts[2] != "blob":
        raise ValueError("GitHub URL 必须指向具体 blob 文件")

    owner, repo, _, ref, *file_parts = parts
    raw_path = "/".join(urllib.parse.quote(part, safe="") for part in [owner, repo, ref, *file_parts])
    return f"https://raw.githubusercontent.com/{raw_path}"


def fetch_text(url: str, timeout: float) -> tuple[str, int, str]:
    """抓取文本，同时返回 HTTP 状态和响应字符集。"""

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/plain, application/octet-stream;q=0.9",
            "User-Agent": "papers-search/1.0 source-verifier",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="replace"), response.status, charset


def find_keywords(
    content: str,
    keywords: list[str],
    ignore_case: bool,
    max_lines: int,
) -> list[KeywordResult]:
    """返回关键词是否命中及其行号，不输出源码内容。"""

    lines = content.splitlines()
    searchable_lines = [line.casefold() for line in lines] if ignore_case else lines
    results: list[KeywordResult] = []
    for keyword in keywords:
        needle = keyword.casefold() if ignore_case else keyword
        matches = [index for index, line in enumerate(searchable_lines, start=1) if needle in line]
        results.append(KeywordResult(keyword, bool(matches), matches[:max_lines]))
    return results


def main() -> int:
    args = parse_args()
    try:
        raw_url = to_raw_url(args.url)
    except ValueError as exc:
        print(f"URL 校验失败：{exc}", file=sys.stderr)
        return 2

    try:
        content, status, charset = fetch_text(raw_url, args.timeout)
    except (urllib.error.URLError, TimeoutError, UnicodeError) as exc:
        print(f"源码抓取失败：{exc}；raw_url={raw_url}", file=sys.stderr)
        return 2

    results = find_keywords(content, args.keywords, args.ignore_case, args.max_lines)
    verified = all(item.found for item in results) if args.require == "all" else any(item.found for item in results)
    report = {
        "source_url": args.url,
        "raw_url": raw_url,
        "http_status": status,
        "charset": charset,
        "content_bytes": len(content.encode(charset, errors="replace")),
        "require": args.require,
        "verified": verified,
        "keywords": [asdict(item) for item in results],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("源码验证报告")
        print(f"来源：{args.url}")
        print(f"Raw：{raw_url}")
        print(f"HTTP：{status}")
        print(f"判定：{'通过' if verified else '未通过'}（要求 {args.require}）")
        for item in results:
            line_text = ", ".join(str(line) for line in item.lines) or "无"
            print(f"- {item.keyword}: {'命中' if item.found else '未命中'}；行号：{line_text}")

    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
