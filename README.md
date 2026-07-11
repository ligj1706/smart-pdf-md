# pdf2m

Smart PDF/OCR multi-source router to Markdown: auto-pick the most accurate extraction path.

[English](README.md) | [中文](README.zh.md)

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Traditional PDF extractors fail on **scanned PDFs**; OCR outputs suffer from **broken paragraphs**.
`pdf2m` elegantly bridges these two:

- ✅ PDFs with a text layer → extract directly (**0 loss**)
- ✅ PDFs with OCR intermediate results → smart merge + heading detection
- ✅ Scanned PDFs without OCR → clear guidance on what to do

## ✨ Features

- **3 auto-detection modes**: `pymupdf` / `mineru` / `ocr`, with smart fallback
- **Heading detection**: H1 (book title), H2 (page), H3 (chapter)
- **Smart paragraph merging**: line gap + sentence-ending punctuation + heading heuristics
- **Noise filtering**: headers, footers, isolated page numbers
- **Parallel processing**: `-w N` for thread-pool speedup
- **OCR-tool agnostic**: works with outputs from MinerU, PaddleOCR, Tesseract, and more
- **Single dependency** (just PyMuPDF)

## 📦 Installation

Install from source (PyPI release coming soon):

```bash
git clone https://github.com/ligj1706/pdf2m
cd pdf2m
pip install -e .
```

Or, if you prefer a faster installer ([uv](https://github.com/astral-sh/uv)):

```bash
git clone https://github.com/ligj1706/pdf2m
cd pdf2m
uv pip install -e .
```

`uv pip` is a drop-in replacement for `pip` — same flags, same `pyproject.toml`,
just ~10-100x faster. No code changes required.

Or just install the runtime dependency and use the package directly:

```bash
pip install pymupdf>=1.23
```

## 🚀 Quick Start

```bash
# Single file
pdf2m book.pdf -o ./output

# Whole directory
pdf2m ./my_pdfs -o ./output --ocr-dir ./ocr_results

# 8 parallel workers
pdf2m ./my_pdfs -o ./output -w 8

# Force a specific mode
pdf2m book.pdf --mode pymupdf
pdf2m book.pdf --mode mineru
pdf2m book.md   --mode ocr
```

Python API:

```python
from pdf2m import process_one, process_batch

process_one("book.pdf", output_dir="./output")
process_batch(["a.pdf", "b.md"], output_dir="./output", workers=4)
```

## 🛣️ Routing Strategy

`pdf2m` auto-detects in this order (with `--mode auto`):

```
┌─────────────────────────────────────────────────────┐
│ 1️⃣ PyMuPDF text layer (PDF native text)  →  Best     │
│    Heuristic: first 5 pages get_text() > 200 chars   │
├─────────────────────────────────────────────────────┤
│ 2️⃣ MinerU middle.json  →  Block + font-size          │
│    Lookup: same dir / _mineru/ / user ocr-dir        │
├─────────────────────────────────────────────────────┤
│ 3️⃣ OCR md (any OCR tool output)  →  Heuristic merge │
│    Lookup: same dir / _ocr/ / user ocr-dir           │
├─────────────────────────────────────────────────────┤
│ 4️⃣ Scanned PDF without OCR output  →  Skip + hint   │
└─────────────────────────────────────────────────────┘
```

## 📂 Real-World Case

`pdf2m` has processed **6 monographs on Zhuangzi philosophy** (by Wang Xianqian,
Liu Xiaogan, Zhong Tai, etc.) — all producing clean Markdown with clear chapter structure
and filtered page-number noise.

See: [`samples/zhuangzi-study.md`](samples/zhuangzi-study.md)

## 🛠️ Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ && ruff format --check src/
```

Thanks to the following open-source projects:

- [**PyMuPDF**](https://github.com/pymupdf/PyMuPDF)
- [**MinerU**](https://github.com/opendatalab/MinerU)
- [**PaddleOCR / PaddlePaddle**](https://github.com/PaddlePaddle/PaddleOCR)
- [**Tesseract**](https://github.com/tesseract-ocr/tesseract)
- [**marker-pdf**](https://github.com/datalab-to/marker)
- [**GLM-OCR (zai-org)**](https://github.com/zai-org/GLM-OCR)

## 📜 License

[MIT](LICENSE)