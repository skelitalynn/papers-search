# papers-search

> 日期：2026-08-26
> 定位：汇总分散的论文检索能力，形成 2025 年及以后论文发现、验证与沉淀的专门项目。
> 关联：[docs/arxiv检索.md](docs/arxiv检索.md)（arXiv 用法）｜ [docs/调研链路.md](docs/调研链路.md)（方法论）｜ [templates/调研报告模板.md](templates/调研报告模板.md)（报告模板）

---

结论：papers-search 是论文检索专门项目。它集中管理论文发现、官方来源过滤、源码验证、文档质量检查与 Mermaid 渲染实测，保留可复核的证据链。

项目只收录 2025 年及以后的论文与资料，也支持围绕论文开展技术框架选型和竞品调研。研究判断由人负责，脚本负责稳定执行检索、筛选与检查动作。

## 目录结构

```text
.
├── AGENTS.md                  # AI agent 自动读取的核心规则
├── README.md                  # 项目入口
├── docs/
│   ├── arxiv检索.md           # arXiv REST API 与检索脚本用法
│   ├── 调研链路.md            # 七步方法论详解
│   └── 用户偏好与记忆.md      # 长期协作偏好与背景
├── legacy/
│   ├── README.md              # 认证探测脚本归档说明
│   ├── codex_probe.py         # Codex 与中转认证探测
│   ├── codex_run.sh           # Codex 一次性任务入口
│   └── oa_test.py             # OpenAI API 认证探测
├── scripts/
│   ├── search.py              # 证据候选搜集与官方来源过滤
│   ├── search_arxiv.py        # arXiv REST API 直接检索
│   ├── verify_source.py       # 官方 GitHub 源码机制验证
│   ├── quality_check.py       # 中文文档质量检查
│   └── render_check.py        # Mermaid 联网渲染实测
└── templates/
    └── 调研报告模板.md         # 结论优先的报告模板
```

## 快速上手

1. 按 [arXiv 检索说明](docs/arxiv检索.md)直接搜索论文：

   ```bash
   python3 scripts/search_arxiv.py "关键词" --sort date --max 10
   ```

2. 从[调研报告模板](templates/调研报告模板.md)复制一份报告到 `docs/`。
3. 按[调研链路](docs/调研链路.md)拆问题，先写决策标准，再搜证据候选：

   ```bash
   python3 scripts/search.py "multi agent orchestration"
   ```

4. 离线筛选已有候选，并严格声明官方域名或官方 GitHub owner：

   ```bash
   python3 scripts/search.py "resource lock" --offline \
     --official-domain docs.python.org \
     --official-github-owner python \
     --candidate 'urllib.request 官方文档|https://docs.python.org/3/library/urllib.request.html|2026' \
     --candidate 'urllib.request 官方实现|https://github.com/python/cpython/blob/main/Lib/urllib/request.py|2026'
   ```

5. 对官方 GitHub 文件做源码验证：

   ```bash
   python3 scripts/verify_source.py \
     https://github.com/python/cpython/blob/main/Lib/urllib/request.py \
     Request urlopen
   ```

6. 完稿前执行离线质量检查；需要验证外链 HTTP 状态时再加 `--check-external`：

   ```bash
   python3 scripts/quality_check.py README.md AGENTS.md docs templates legacy
   python3 scripts/quality_check.py docs/某次调研.md --check-external
   ```

7. 文档含 Mermaid 图时执行联网渲染实测：

   ```bash
   python3 scripts/render_check.py docs/调研链路.md
   ```

## 两个检索脚本的分工

| 脚本 | 负责范围 | 适用时机 |
| --- | --- | --- |
| `scripts/search.py` | 搜集证据候选，按年份、官方域名和官方 GitHub owner 过滤。 | 需要跨官方文档、源码与原始论文建立证据链时。 |
| `scripts/search_arxiv.py` | 直接调用 arXiv REST API，按关键词、作者、分类或 ID 返回论文元数据。 | 需要快速发现或定位 arXiv 论文时。 |

`scripts/` 中的 Python 脚本只使用标准库。`legacy/` 保存原样归档的临时认证脚本，论文检索和自动化流程排除该目录。

## 证据边界

只接受官方文档、官方 GitHub 源码、官方博客、官方 case study 和 2025 年及以后的原始论文。未知 GitHub owner、未知站点、SEO 博客、二手媒体、star 数和无法复核的性能数字不得进入结论。

详细规则以 [AGENTS.md](AGENTS.md) 为准。
