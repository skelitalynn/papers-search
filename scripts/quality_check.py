#!/usr/bin/env python3
"""检查中文 Markdown 调研文档的基础质量。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_PATHS = ["README.md", "AGENTS.md", "docs", "templates"]
SENSITIVE_PATTERNS = {
    "私钥": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b"),
    "Bearer token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
    "疑似密钥赋值": re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        re.IGNORECASE,
    ),
}
MERMAID_STARTS = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "gitGraph",
    "quadrantChart",
    "xychart",
    "block-beta",
    "packet-beta",
    "architecture-beta",
    "kanban",
    "sankey-beta",
    "requirementDiagram",
    "C4Context",
)


@dataclass
class FileReport:
    """单份文档的检查结果。"""

    path: str
    dash_count: int = 0
    mermaid_blocks: int = 0
    relative_links: int = 0
    external_links: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统计破折号、扫描敏感词、检查 Markdown 链接并提取 Mermaid 块数量。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python3 scripts/quality_check.py
  python3 scripts/quality_check.py README.md docs templates
  python3 scripts/quality_check.py docs/调研报告.md --check-external

默认只离线检查外链格式。--check-external 会真实访问外网，不应在自动化测试中启用。
Mermaid 仅做块数量和首行结构检查，最终仍需在目标渲染器中实测。
""",
    )
    parser.add_argument("paths", nargs="*", default=DEFAULT_PATHS, help="Markdown 文件或目录")
    parser.add_argument("--max-dashes", type=int, default=2, help="每份文档允许的破折号字符上限，默认 2")
    parser.add_argument(
        "--sensitive-word",
        action="append",
        default=[],
        metavar="词",
        help="增加要扫描的敏感词，可重复使用",
    )
    parser.add_argument("--check-external", action="store_true", help="真实请求外部链接并检查 HTTP 状态")
    parser.add_argument("--timeout", type=float, default=10.0, help="外链请求超时秒数，默认 10")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出报告")
    args = parser.parse_args()
    if args.max_dashes < 0:
        parser.error("--max-dashes 不能小于 0")
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    return args


def collect_markdown_files(paths: list[str]) -> tuple[list[Path], list[str]]:
    """展开文件和目录，返回去重后的 Markdown 文件。"""

    files: set[Path] = set()
    errors: list[str] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            errors.append(f"路径不存在：{path}")
        elif path.is_dir():
            files.update(item for item in path.rglob("*.md") if item.is_file())
        elif path.is_file() and path.suffix.lower() == ".md":
            files.add(path)
        else:
            errors.append(f"不是 Markdown 文件或目录：{path}")
    return sorted(files, key=lambda item: str(item)), errors


def markdown_links(content: str) -> list[str]:
    """提取普通 Markdown 链接目标，忽略图片。"""

    pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
    targets: list[str] = []
    for match in pattern.finditer(content):
        raw = match.group(1).strip()
        if raw.startswith("<") and ">" in raw:
            target = raw[1 : raw.index(">")]
        else:
            target = raw.split(maxsplit=1)[0]
        targets.append(target)
    return targets


def check_external_link(url: str, timeout: float) -> str | None:
    """先 HEAD，必要时用小范围 GET 验证外链。"""

    headers = {"User-Agent": "papers-search/1.0 link-checker"}
    attempts = [
        urllib.request.Request(url, headers=headers, method="HEAD"),
        urllib.request.Request(url, headers={**headers, "Range": "bytes=0-0"}, method="GET"),
    ]
    last_error: Exception | None = None
    for request in attempts:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if 200 <= response.status < 400:
                    return None
                last_error = RuntimeError(f"HTTP {response.status}")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
    return str(last_error or "未知错误")


def check_mermaid(content: str, report: FileReport) -> None:
    """统计 Mermaid 块并做不依赖渲染器的最小结构检查。"""

    blocks = re.findall(r"```mermaid\s*\n(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    report.mermaid_blocks = len(blocks)
    opening_count = len(re.findall(r"```mermaid\b", content, flags=re.IGNORECASE))
    if opening_count != len(blocks):
        report.errors.append("存在未闭合或格式异常的 Mermaid 代码块")
    for index, block in enumerate(blocks, start=1):
        first_line = next((line.strip() for line in block.splitlines() if line.strip()), "")
        if not first_line.startswith(MERMAID_STARTS):
            report.errors.append(f"Mermaid 块 {index} 的首行图类型不可识别：{first_line or '空'}")
    if blocks:
        report.warnings.append("Mermaid 只完成结构检查，仍需在目标渲染器中实测")


def check_file(
    path: Path,
    max_dashes: int,
    custom_words: list[str],
    check_external: bool,
    timeout: float,
) -> FileReport:
    """检查一份 Markdown 文档。"""

    report = FileReport(path=str(path))
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.errors.append(f"读取失败：{exc}")
        return report

    report.dash_count = content.count("—")
    if report.dash_count > max_dashes:
        report.errors.append(f"破折号数量 {report.dash_count} 超过上限 {max_dashes}")

    for name, pattern in SENSITIVE_PATTERNS.items():
        for match in pattern.finditer(content):
            line = content.count("\n", 0, match.start()) + 1
            report.errors.append(f"第 {line} 行命中敏感模式：{name}")
    for word in custom_words:
        if not word:
            continue
        for match in re.finditer(re.escape(word), content, flags=re.IGNORECASE):
            line = content.count("\n", 0, match.start()) + 1
            report.errors.append(f"第 {line} 行命中自定义敏感词：{word}")

    for target in markdown_links(content):
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme in {"http", "https"}:
            report.external_links += 1
            if not parsed.hostname:
                report.errors.append(f"外链缺少域名：{target}")
            elif check_external:
                error = check_external_link(target, timeout)
                if error:
                    report.errors.append(f"外链访问失败：{target}；{error}")
        elif parsed.scheme or target.startswith("//"):
            report.errors.append(f"不支持的链接协议：{target}")
        elif target.startswith("#"):
            report.relative_links += 1
        else:
            report.relative_links += 1
            decoded_path = urllib.parse.unquote(parsed.path)
            destination = (path.parent / decoded_path).resolve()
            if not destination.exists():
                report.errors.append(f"相对链接目标不存在：{target}")

    check_mermaid(content, report)
    return report


def print_text(reports: list[FileReport], global_errors: list[str]) -> None:
    """输出适合人工检查的中文报告。"""

    for error in global_errors:
        print(f"错误：{error}")
    for report in reports:
        status = "通过" if not report.errors else "失败"
        print(
            f"[{status}] {report.path}：破折号 {report.dash_count}，"
            f"相对链接 {report.relative_links}，外链 {report.external_links}，"
            f"Mermaid {report.mermaid_blocks}"
        )
        for error in report.errors:
            print(f"  错误：{error}")
        for warning in report.warnings:
            print(f"  提醒：{warning}")


def main() -> int:
    args = parse_args()
    files, global_errors = collect_markdown_files(args.paths)
    if not files:
        global_errors.append("没有找到可检查的 Markdown 文件")
    reports = [
        check_file(
            path,
            args.max_dashes,
            args.sensitive_word,
            args.check_external,
            args.timeout,
        )
        for path in files
    ]

    if args.json:
        payload = {
            "files": [asdict(report) for report in reports],
            "global_errors": global_errors,
            "passed": not global_errors and all(not report.errors for report in reports),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(reports, global_errors)

    return 0 if not global_errors and all(not report.errors for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
