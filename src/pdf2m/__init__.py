"""pdf2m — 智能 PDF/OCR 多源路由转 Markdown.

按优先级自动选择最佳抽取路径：
  1. PyMuPDF 文字层（PDF 自带文本）
  2. MinerU middle.json（带 bbox + 字号信息）
  3. OCR md（任何外部 OCR 工具的输出）
  4. 跳过并提示
"""

from pdf2m.core import (
    SENT_END,
    SENT_END_ASCII,
    TITLE_RE,
    is_short_title,
    is_page_noise,
    detect_title_from_pdf_meta,
    extract_pymupdf,
    extract_mineru,
    extract_ocr_md,
    pick_mode,
    process_one,
    process_batch,
)

__version__ = "0.1.0"
__all__ = [
    "SENT_END",
    "SENT_END_ASCII",
    "TITLE_RE",
    "is_short_title",
    "is_page_noise",
    "detect_title_from_pdf_meta",
    "extract_pymupdf",
    "extract_mineru",
    "extract_ocr_md",
    "pick_mode",
    "process_one",
    "process_batch",
    "__version__",
]