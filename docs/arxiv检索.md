# arXiv 论文检索

> 日期：2026-08-26
> 定位：集中说明 arXiv REST API 与 `search_arxiv.py` 的检索、解析和阅读方法。
> 关联：[README.md](../README.md)（项目入口）｜ [search_arxiv.py](../scripts/search_arxiv.py)（检索脚本）｜ [调研链路.md](调研链路.md)（证据验证流程）

---

## 结论

优先使用 `scripts/search_arxiv.py` 获取可读结果；需要组合查询或保留 Atom XML 时直接调用 arXiv REST API。两种方式得到的内容都属于候选，进入报告前必须确认发布日期不早于 2025 年，并按调研链路复核摘要、版本和原文。

## 基础搜索

arXiv API 返回 Atom XML，不需要 API 密钥。以下命令按全部字段检索关键词并返回 5 条结果：

```bash
curl -s "https://export.arxiv.org/api/query?search_query=all:multi+agent&max_results=5"
```

常用字段前缀如下：

| 前缀 | 检索范围 | 示例 |
| --- | --- | --- |
| `all:` | 全部字段 | `all:multi+agent` |
| `ti:` | 标题 | `ti:large+language+models` |
| `au:` | 作者 | `au:lecun` |
| `abs:` | 摘要 | `abs:reinforcement+learning` |
| `cat:` | 分类 | `cat:cs.AI` |

组合条件可使用 `AND`、`OR` 和 `ANDNOT`。查询参数还支持 `sortBy`、`sortOrder`、`start` 与 `max_results`。完整语法以 [arXiv API 用户手册](https://info.arxiv.org/help/api/user-manual.html)为准。

## 干净输出解析

直接解析 XML 时，需要读取 Atom 命名空间中的 `entry`，再提取标题、ID、发布日期、作者、摘要与分类。仓库脚本已经用 Python 标准库完成这一步，直接运行即可得到适合人工阅读的输出：

```bash
python3 scripts/search_arxiv.py "multi agent orchestration" --sort date --max 10
```

每条结果包含标题、版本化 ID、首次发布日期、更新时间、作者、分类、摘要节选，以及摘要页和 PDF 链接。脚本仅负责解析和展示，论文质量及年份仍需人工判断与过滤。

## 按 ID 查询论文

REST API 的 `id_list` 支持单个或多个 arXiv ID：

```bash
curl -s "https://export.arxiv.org/api/query?id_list=2501.12948"
curl -s "https://export.arxiv.org/api/query?id_list=2501.12948,2502.03300"
```

脚本提供相同入口：

```bash
python3 scripts/search_arxiv.py --id 2501.12948
python3 scripts/search_arxiv.py --id 2501.12948,2502.03300
```

保留版本后缀可以固定所读版本，例如 `2501.12948v1`。省略版本后缀时，arXiv 摘要页通常指向最新版本。

## 阅读摘要与 PDF

摘要页适合先核对元数据和摘要，PDF 用于阅读全文：

```text
https://arxiv.org/abs/2501.12948
https://arxiv.org/pdf/2501.12948
```

需要保存 PDF 时可运行：

```bash
curl -L "https://arxiv.org/pdf/2501.12948" --output /tmp/2501.12948.pdf
```

引用时记录实际阅读的版本号。摘要出现撤稿说明，或元数据不完整时，把结果标记为待验证，不进入确定性结论。

## search_arxiv.py 参数

```bash
python3 scripts/search_arxiv.py "transformer attention" --max 10 --sort date
python3 scripts/search_arxiv.py --author "Yann LeCun" --max 5
python3 scripts/search_arxiv.py --category cs.AI --sort updated --max 10
python3 scripts/search_arxiv.py --id 2501.12948
```

| 参数 | 作用 |
| --- | --- |
| 位置参数 | 按全部字段检索一个或多个关键词。 |
| `--author` | 按作者检索，可与关键词或分类组合。 |
| `--category` | 按 arXiv 分类检索，例如 `cs.AI`。 |
| `--id` | 按一个或多个逗号分隔的 ID 查询。 |
| `--max` | 控制返回数量，默认 5。 |
| `--sort` | 支持 `relevance`、`date`、`updated`，默认按相关度。 |

脚本只有 Python 标准库依赖。运行 `python3 scripts/search_arxiv.py --help` 可查看内置示例。

## 只保留 2025 年及以后论文

本项目的时间边界是首次发布日期不早于 2025-01-01。常规检索先按提交日期倒序扩大候选数，再人工检查脚本输出中的 `Published` 字段：

```bash
python3 scripts/search_arxiv.py "agent orchestration" --sort date --max 30
```

需要在 API 查询阶段缩小范围时，使用 `submittedDate` 条件，并让 curl 负责 URL 编码：

```bash
curl -sG "https://export.arxiv.org/api/query" \
  --data-urlencode "search_query=all:agent orchestration AND submittedDate:[202501010000 TO 999912312359]" \
  --data "sortBy=submittedDate" \
  --data "sortOrder=descending" \
  --data "max_results=30"
```

最终过滤以 Atom 响应或脚本输出中的首次发布日期为准。更新时间晚于 2025 年不能替代首次发布日期条件。分类名称可从 [arXiv 分类目录](https://arxiv.org/category_taxonomy)核对。
