"""单元 + 集成测试。"""

import json
from pathlib import Path

import pytest

from pdf2m.core import (
    SENT_END,
    SENT_END_ASCII,
    extract_mineru,
    extract_ocr_md,
    extract_pymupdf,
    is_page_noise,
    is_short_title,
    pick_mode,
    process_one,
)


# ============================================================
# 工具函数
# ============================================================
class TestIsShortTitle:
    def test_chapter_title(self):
        assert is_short_title("第一章  逍遥游")

    def test_short_with_neighbors(self):
        assert is_short_title("序", prev_len=100, next_len=100)

    def test_long_paragraph(self):
        assert not is_short_title("这是一段很长的正文，里面有很多很多文字" * 3)

    def test_empty(self):
        assert not is_short_title("")

    def test_arabic_numbered(self):
        assert is_short_title("1. 引言")

    def test_前言_引言(self):
        assert is_short_title("前言")
        assert is_short_title("引言")

    def test_目录(self):
        assert is_short_title("目录")


class TestIsPageNoise:
    def test_pure_number(self):
        assert is_page_noise("42")
        assert is_page_noise("— 42 —")

    def test_book_dot_page(self):
        assert is_page_noise("庄子集解 ........ 12")

    def test_real_text(self):
        assert not is_page_noise("庄子的思想博大精深")

    def test_empty(self):
        assert is_page_noise("")

    def test_short_chapter_is_not_noise(self):
        assert not is_page_noise("第一章 逍遥游")


class TestPickMode:
    def test_md_file_goes_to_ocr(self):
        mode, src, hint = pick_mode("/tmp/foo/bar.md")
        assert mode == "ocr"
        assert hint is None

    def test_unsupported_extension(self):
        mode, src, hint = pick_mode("/tmp/foo/bar.txt")
        assert mode == "skip"
        assert hint is not None

    def test_force_mode_short_circuits(self):
        mode, src, _ = pick_mode("/tmp/non/existent.pdf", mode="mineru")
        assert mode == "mineru"


# ============================================================
# 端到端：extract_pymupdf
# ============================================================
def _make_text_pdf(path: Path, pages: list[str], title: str | None = None) -> None:
    """用 pymupdf 构造一个真实的、带文字层的 PDF。"""
    import fitz
    doc = fitz.open()
    if title:
        doc.set_metadata({"title": title})
    for text in pages:
        page = doc.new_page()
        # 显式指定 ASCII 字体插入文本，规避 PyMuPDF 默认字体不支持中文的问题。
        page.insert_text((72, 72), text, fontname="helv", fontsize=11)
    doc.save(str(path))
    doc.close()


def test_extract_pymupdf_basic(tmp_path):
    """最简文字层 PDF → 标题 + 每页 H2 + 文本。"""
    pdf = tmp_path / "demo.pdf"
    _make_text_pdf(pdf, ["page-one text", "page-two text"], title="demo title")
    md = extract_pymupdf(str(pdf), "demo title")
    assert md.startswith("# demo title")
    assert "## 第 1 页" in md
    assert "## 第 2 页" in md
    assert "page-one text" in md
    assert "page-two text" in md


def test_extract_pymupdf_falls_back_to_filename(tmp_path):
    """没有 metadata 时用文件名当 title（通过 detect_title_from_pdf_meta）。"""
    from pdf2m.core import detect_title_from_pdf_meta

    pdf = tmp_path / "my_book.pdf"
    _make_text_pdf(pdf, ["x"])
    # 路径不存在时 detect_title_from_pdf_meta 应兜底用 stem
    assert detect_title_from_pdf_meta(str(pdf)) == "my_book"


# ============================================================
# 端到端：extract_ocr_md
# ============================================================
def test_extract_ocr_md_with_page_marks(tmp_path):
    """带 ## 第 N 页 标记的 OCR md。"""
    md_in = tmp_path / "input.md"
    md_in.write_text(
        "# 目录\n"
        "\n"
        "## 第 1 页\n"
        "\n"
        "北冥有鱼，其名为鲲。\n"
        "鲲之大，不知其几千里也。\n"
        "\n"
        "## 第 2 页\n"
        "\n"
        "鹏之背，不知其几千里也。\n",
        encoding="utf-8",
    )
    md = extract_ocr_md(str(md_in), "庄子")
    assert "# 庄子" in md
    assert "## 第 1 页" in md
    assert "## 第 2 页" in md
    assert "北冥有鱼，其名为鲲。" in md
    assert "鹏之背，不知其几千里也。" in md


def test_extract_ocr_md_strips_page_number(tmp_path):
    """页码噪声应被剔除。"""
    md_in = tmp_path / "input.md"
    md_in.write_text(
        "## 第 1 页\n"
        "\n"
        "正文中的一段很长的内容，应该保留下来不被过滤掉。\n"
        "12\n"
        "\n"
        "## 第 2 页\n"
        "\n"
        "另一段正文内容也比较长，达到合并阈值之上。\n",
        encoding="utf-8",
    )
    md = extract_ocr_md(str(md_in), "title")
    # 纯数字行被剥掉（"## 第 1 页" 这种 header 也含数字但不算 noise）
    # 这里检查正文数字"12"是页码，应被剔除
    lines = md.splitlines()
    assert "12" not in lines  # 单独一行 "12" 不会出现在输出
    assert "正文中的一段" in md


def test_extract_ocr_md_with_frontmatter(tmp_path):
    """带 YAML frontmatter 的输入。"""
    md_in = tmp_path / "input.md"
    md_in.write_text(
        "---\npages: 2\n---\n## 第 1 页\n正文章节一。\n",
        encoding="utf-8",
    )
    md = extract_ocr_md(str(md_in), "title")
    assert "正文章节一" in md


# ============================================================
# 端到端：extract_mineru（构造 fixture JSON）
# ============================================================
def test_extract_mineru_with_fixture(tmp_path):
    """构造一个最小 middle.json，跑完整流程。

    注意：fixture 里 body 字号必须出现多次才能让 body_sz 选对，
    否则 title 的字号会被误识别为 body。
    """
    json_path = tmp_path / "demo_middle.json"
    data = {
        "pdf_info": [
            {
                "page_idx": 0,
                "preproc_blocks": [
                    {
                        # 标题块：大字号
                        "bbox": [50, 50, 500, 90],
                        "lines": [
                            {"spans": [{"content": "TitleA", "size": 18.0}]},
                            {"spans": [{"content": "TitleB", "size": 18.0}]},
                        ],
                    },
                    {
                        # 多个 body 块，确保 body 字号占多数
                        "bbox": [50, 120, 500, 160],
                        "lines": [
                            {"spans": [{"content": "Body 1.", "size": 12.0}]},
                            {"spans": [{"content": "Body 2.", "size": 12.0}]},
                            {"spans": [{"content": "Body 3.", "size": 12.0}]},
                            {"spans": [{"content": "Body 4.", "size": 12.0}]},
                        ],
                    },
                ],
                "discarded_blocks": [],
            }
        ]
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    md = extract_mineru(str(json_path), "Book")
    assert "# Book" in md
    assert "## 第 1 页" in md
    assert "### TitleA" in md
    assert "Body 1." in md


# ============================================================
# 端到端：process_one 集成
# ============================================================
def test_process_one_skips_unavailable(tmp_path):
    """扫描版 PDF 但无 OCR 输出 → 应跳过 + 给出提示。"""
    out_dir = tmp_path / "out"
    scanned_pdf = tmp_path / "scanned.pdf"
    scanned_pdf.write_bytes(b"%PDF-1.4\nfake\n%%EOF\n")

    result = process_one(str(scanned_pdf), str(out_dir))
    assert result is None


def test_process_one_ocr_md_end_to_end(tmp_path):
    """完整跑一遍：ocr md 输入 → 写出文件。

    process_one 不会自动创建 output_dir，所以测试要手动 makedirs。
    """
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_in = tmp_path / "book.md"
    md_in.write_text(
        "## 第 1 页\n"
        "\n"
        "北冥有鱼，其名为鲲。\n"
        "鲲之大，不知其几千里也。\n",
        encoding="utf-8",
    )
    result = process_one(str(md_in), str(out_dir))
    assert result is not None
    out_file = Path(result)
    assert out_file.exists()
    assert out_file.parent == out_dir
    assert out_file.name == "book.md"
    content = out_file.read_text(encoding="utf-8")
    assert "# book" in content
    assert "北冥有鱼" in content


def test_pick_mode_force_pymupdf(tmp_path):
    """强制 mode 不应触发文字层检测。"""
    fake = tmp_path / "x.pdf"
    fake.write_bytes(b"")
    mode, src, _ = pick_mode(str(fake), mode="pymupdf")
    assert mode == "pymupdf"


# ============================================================
# 公共 API 一致性
# ============================================================
def test_constants_exposed():
    assert isinstance(SENT_END, str)
    assert "。" in SENT_END
    assert "." in SENT_END_ASCII
