# 认证探测脚本归档

> 日期：2026-08-26
> 定位：保存 Codex 与 OpenAI API 认证探测的临时脚本，供故障复盘使用，不属于论文检索功能。
> 关联：[README.md](../README.md)（项目入口）｜ [AGENTS.md](../AGENTS.md)（执行约定）

---

## 归档内容

| 文件 | 用途 |
| --- | --- |
| `codex_probe.py` | 读取本机 Codex 与 Hermes 的认证配置，分别探测中转服务和 OpenAI 模型列表接口。 |
| `codex_run.sh` | 使用本机 Codex 登录态，在指定目录执行一次性任务，并提供超时控制。 |
| `oa_test.py` | 使用 Hermes 环境中的 API 凭据，探测 Responses API 与 Chat Completions API。 |

这些脚本依赖固定的本机路径和认证状态，可能发起计费 API 请求，也会输出凭据前缀。仅在明确排查认证问题时人工运行，不纳入论文检索流程或自动化测试。
