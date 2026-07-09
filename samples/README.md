# Samples

## 内容

- `sample.md`：模拟一个 OCR 工具输出的 md（带 frontmatter + 分页符）
- `zhuangzi-study.md`：真实案例展示文档（不是被处理的输入）
- `run_demo.py`：一键跑示例脚本

> ⚠️ **不要把整个 `samples/` 目录喂给 CLI**：`pdf2m samples/` 会把所有 `.md` 都当成 OCR 输出处理。
> 想批量跑示例时，单独指定文件，或准备一个独立的 `inputs/` 目录。

## 跑法

```bash
# 方式 1：脚本
python samples/run_demo.py

# 方式 2：CLI（处理单个文件）
pdf2m samples/sample.md -o ./out
```

## 验证输出

跑完你会看到分页清晰、章节结构合理的 Markdown。
