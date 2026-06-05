# 苏墨-巴菲特知识库

本项目基于 Karpathy 的 LLM Wiki 思路构建巴菲特投资思想知识图谱：

- `raw/` 保存原始资料，只读维护
- `wiki/` 保存结构化、可双向链接的知识页面
- `code/` 保存转换脚本、摄取脚本、前端与后端

推荐工作流：

1. 先将 `raw/concepts`、`raw/companies`、`raw/people` 通过 `code/convert_existing.py` 转换为 `wiki/`
2. 运行 `fix_headings.py`、`fix_headings2.py`、`fix_paragraphs.py` 修正文档结构
3. 运行 `update_index.py` 生成 `wiki/index.md`
4. 使用 `codex_refine_summaries.py` 为 `raw/letters` 与 `raw/interviews` 生成 Codex 精修摘要页
5. 在 `code/web/` 运行 `build-data.py` 和前后端服务
