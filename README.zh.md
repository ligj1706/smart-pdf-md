# pdf2m

智能 PDF / OCR 多源路由 → Markdown 工具：自动选择**最精准**的抽取路径。

目前为初版，还有不少问题。

[English](README.md) | [中文](README.zh.md)

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

传统 PDF 抽取工具对**扫描版 PDF** 无能为力；OCR 工具输出又有**段落错乱**的问题。
`pdf2m` 把这两件事优雅地缝合在一起：

- ✅ 有文字层的 PDF → 直接抽（**0 损耗**）
- ✅ 有 OCR 中间结果 → 智能合并段落、识别标题
- ✅ 扫描版无 OCR → 给出**明确指引**

## ✨ 特性

- **3 种自动检测模式**：`pymupdf` / `mineru` / `ocr`，一键兜底
- **章节识别**：自动判断 H1（书名）、H2（页）、H3（章/节）
- **段落智能合并**：行间距离 + 句末标点 + 标题特征三合一
- **噪声过滤**：自动剔除页眉、页脚、孤立页码
- **并行处理**：可选 `-w N` 启用线程池加速
- **OCR 工具无关**：MinerU、PaddleOCR、Tesseract 都能吃
- **纯单依赖**（只需要 PyMuPDF）

## 📦 安装

从源码安装（PyPI 包即将发布）：

```bash
git clone https://github.com/ligj1706/pdf2m
cd pdf2m
pip install -e .
```

或者仅装运行时依赖，直接使用：

```bash
pip install pymupdf>=1.23
```

## 🚀 快速上手

```bash
# 单文件
pdf2m book.pdf -o ./output

# 整目录（自动扫 PDF + md）
pdf2m ./my_pdfs -o ./output --ocr-dir ./ocr_results

# 并行 8 worker
pdf2m ./my_pdfs -o ./output -w 8

# 强制模式
pdf2m book.pdf --mode pymupdf
pdf2m book.pdf --mode mineru
pdf2m book.md   --mode ocr
```

Python API：

```python
from pdf2m import process_one, process_batch

process_one("book.pdf", output_dir="./output")
process_batch(["a.pdf", "b.md"], output_dir="./output", workers=4)
```

## 🛣️ 路由策略

`pdf2m` 按以下顺序自动判断（`--mode auto` 时）：

```
┌─────────────────────────────────────────────────────┐
│ 1️⃣ PyMuPDF 文字层（PDF 自带文本）  →  最精准        │
│    抽样检测：前 5 页 get_text() 总字符 > 200         │
├─────────────────────────────────────────────────────┤
│ 2️⃣ MinerU middle.json  →  块结构 + 字号             │
│    自动找：同目录 / _mineru/ / 用户指定 ocr-dir     │
├─────────────────────────────────────────────────────┤
│ 3️⃣ OCR md（任何 OCR 工具输出）   →  启发式合并      │
│    自动找：同目录 / _ocr/ / 用户指定 ocr-dir        │
├─────────────────────────────────────────────────────┤
│ 4️⃣ 扫描版无 OCR 输出  →  跳过 + 提示                │
└─────────────────────────────────────────────────────┘
```

## 📂 真实案例

`pdf2m` 已在实际项目里处理过**6 本庄子研究专著**（王先谦、刘笑敢、钟泰等），
全部产出干净 Markdown，章节结构清晰，页码噪声自动过滤。

详见：[`samples/zhuangzi-study.md`](samples/zhuangzi-study.md)

## 🛠️ 开发

```bash
pip install -e ".[dev]"
pytest
ruff check src/ && ruff format --check src/
```

## 与现有工具的差异

| 工具 | OCR | 自动选源 | 多 OCR 通用 | 中文友好 |
|---|---|---|---|---|
| `pdfminer.six` | ✗ | ✗ | ✗ | ✓ |
| `marker-pdf` | ✓ | ✗ | ✗ | ✓ |
| `nougat` | ✓ | ✗ | ✗ | ✗ |
| `pdf2md-tool` | ✓ | ✗ | ✗ | ✓ |
| `pdf2md-converter` | ✓ | ✗ | ✗ | ✓ |
| **pdf2m** | ✓ | ✓ | ✓ | ✓ |

## 📜 许可证

[MIT](LICENSE)

## 🙏 致谢

本项目借鉴并参考了以下开源项目的思路：

- [**opendocsg/pdf2md**](https://github.com/opendocsg/pdf2md) — JavaScript 实现的 PDF→Markdown 思路
- [**zyocum/pdf2md**](https://github.com/zyocum/pdf2md) — 多模态 OCR 后处理策略
- [**pdf2md-tool**](https://pypi.org/project/pdf2md-tool/) — CLI 工具的设计经验
- [**pdf2md-converter**](https://pypi.org/project/pdf2md-converter/) — OCR 工具链整合思路
- [**pdf2md-llm**](https://pypi.org/project/pdf2md-llm/) — 启发式合并的设计参考
- [**PyMuPDF**](https://github.com/pymupdf/PyMuPDF) — 文字层抽取的底层依赖
- [**MinerU**](https://github.com/opendatalab/MinerU) — middle.json 块结构格式的来源

感谢以上项目和它们的所有贡献者。