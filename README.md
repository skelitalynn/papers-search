# papers-search

结论：这是一个可重复使用的论文与技术框架调研骨架。复制模板、执行七步调研链路、用脚本留下可复核证据，即可完成一次“调研、验证、沉淀”闭环。

适用场景包括技术框架选型、2025 年及以后论文检索、竞品对比。项目不替代研究判断，而是约束证据来源、源码验证和交付质量。

## 目录结构

```text
.
├── AGENTS.md                  # AI agent 自动读取的核心规则
├── README.md                  # 项目入口
├── docs/
│   ├── 调研链路.md            # 七步方法论详解
│   └── 用户偏好与记忆.md      # 长期协作偏好与背景
├── scripts/
│   ├── search.py              # 可信证据候选搜集与过滤
│   ├── verify_source.py       # 官方 GitHub 源码机制验证
│   └── quality_check.py       # 中文文档质量检查
└── templates/
    └── 调研报告模板.md         # 结论优先的报告模板
```

## 快速上手

1. 从[调研报告模板](templates/调研报告模板.md)复制一份报告到 `docs/`。
2. 按[调研链路](docs/调研链路.md)拆问题，先写决策标准，再搜证据。
3. 搜索 2025 年及以后的原始论文：

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
   python3 scripts/quality_check.py README.md AGENTS.md docs templates
   python3 scripts/quality_check.py docs/某次调研.md --check-external
   ```

所有脚本都只使用 Python 标准库，并提供 `--help`。网络访问失败会明确写入标准错误并返回非零状态，不会静默跳过。

## 证据边界

只接受官方文档、官方 GitHub 源码、官方博客、官方 case study 和 2025 年及以后的原始论文。未知 GitHub owner、未知站点、SEO 博客、二手媒体、star 数和无法复核的性能数字不得进入结论。

详细规则以 [AGENTS.md](AGENTS.md) 为准。
