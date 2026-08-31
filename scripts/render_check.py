#!/usr/bin/env python3
"""调用 mermaid.ink 实测 Markdown 中的 Mermaid 代码块。"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.error
import urllib.request


MERMAID_PATTERN = re.compile(
    r"^[ \t]*```mermaid[ \t]*\r?\n(.*?)^[ \t]*```[ \t]*$",
    flags=re.DOTALL | re.IGNORECASE | re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(
        description="提取 Markdown 中的 Mermaid 代码块，并逐个请求 mermaid.ink 验证渲染。",
        epilog="示例：python3 scripts/render_check.py docs/调研链路.md",
    )
    parser.add_argument("markdown", help="要验证的 Markdown 文件")
    parser.add_argument("--timeout", type=float, default=30.0, help="单个渲染请求超时秒数，默认 30")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    return args


def extract_mermaid_blocks(content: str) -> list[str]:
    """提取闭合且语言标记为 mermaid 的围栏代码块。"""

    return [match.group(1).strip() for match in MERMAID_PATTERN.finditer(content)]


def render_block(block: str, timeout: float) -> tuple[bool, str]:
    """请求 mermaid.ink，返回渲染状态与结果摘要。"""

    encoded = base64.urlsafe_b64encode(block.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{encoded}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "papers-search/1.0 render-check", "Accept": "image/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            if not 200 <= response.status < 300:
                return False, f"HTTP {response.status}"
            if not data:
                return False, "响应内容为空"
            return True, f"{len(data)} 字节"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}：{exc.reason}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, str(exc)


def main() -> int:
    args = parse_args()
    try:
        with open(args.markdown, encoding="utf-8") as file:
            content = file.read()
    except (OSError, UnicodeError) as exc:
        print(f"读取失败：{args.markdown}：{exc}", file=sys.stderr)
        return 1

    blocks = extract_mermaid_blocks(content)
    if not blocks:
        print(f"未发现 Mermaid 代码块：{args.markdown}")
        return 0

    failed = False
    for index, block in enumerate(blocks, start=1):
        ok, detail = render_block(block, args.timeout)
        status = "OK" if ok else "FAIL"
        print(f"[{status}] Mermaid 块 {index}：{detail}")
        failed = failed or not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
