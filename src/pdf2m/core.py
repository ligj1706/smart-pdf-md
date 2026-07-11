"""核心抽取与合并逻辑。"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ============================================================
# 常量
# ============================================================
SENT_END = "。！？；…」』"
SENT_END_ASCII = ".!?;'\""
TITLE_RE = re.compile(
    r"^(第[一二三四五六七八九十百\d]+[章讲篇节课卷目部集]|"
    r"[一二三四五六七八九十]+、|"
    r"序[一二三四五六七八九]?|"
    r"前言|引言|引论|导言|导论|"
    r"目录|目次|"
    r"后记|跋|附录|参考文献|"
    r"自序|序言|题记|凡例|"
    r"绪论|结论|总论|分论|"
    r"上篇|中篇|下篇|"
    r"正文|注释|译注|笺注"
    r")"
)
PAGE_NOISE_RE = [
    re.compile(r"^\s*[\-—]?\s*\d+\s*[\-—]?\s*$"),
    re.compile(r"^.{2,15}\s*\.{2,8}\s*\d+\s*$"),
    re.compile(r"^.{2,15}\s*\d+\s*$"),
]


# ============================================================
# 工具函数
# ============================================================
def is_short_title(line: str, prev_len: int = 0, next_len: int = 0) -> bool:
    s = line.strip()
    if not s or len(s) > 30:
        return False
    if TITLE_RE.match(s):
        return True
    if re.match(r"^\d+\.\s*\S", s):
        return True
    if len(s) <= 15 and prev_len > 50 and next_len > 50:
        return True
    return False


def is_page_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    for pat in PAGE_NOISE_RE:
        if pat.fullmatch(s):
            return True
    return False


def detect_title_from_pdf_meta(pdf_path: str) -> str:
    """从 PDF metadata 抽标题。"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        meta = doc.metadata or {}
        title = meta.get("title", "").strip()
        doc.close()
        return title or Path(pdf_path).stem
    except Exception:
        return Path(pdf_path).stem


# ============================================================
# 模式 1：PyMuPDF 文字层（最精准）
# ============================================================
def extract_pymupdf(pdf_path: str, title: str) -> str:
    """直接从 PDF 文字层抽，按页分页，零损耗。"""
    import fitz
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return f"# {title}\n\n> PDF 打开失败：{pdf_path}\n"
    out = [f"# {title}\n"]
    for pno in range(len(doc)):
        try:
            text = doc[pno].get_text("text").strip()
        except Exception:
            text = ""
        out.append(f"\n## 第 {pno + 1} 页\n")
        if text:
            out.append(text + "\n")
    doc.close()
    return "\n".join(out)


# ============================================================
# 模式 2：MinerU middle.json → 块结构合并
# ============================================================
def extract_mineru(json_path: str, title: str) -> str:
    """从 MinerU middle.json 读块结构，按字号分级 + 块间距离智能合并。"""
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""

    pdf_info = data.get("pdf_info", [])
    if not pdf_info:
        return ""

    all_sizes = []
    for pi in pdf_info:
        for blk in pi.get("preproc_blocks", []) + pi.get("discarded_blocks", []):
            for line in blk.get("lines", []):
                for sp in line.get("spans", []):
                    all_sizes.append(sp.get("size", 0))
    if not all_sizes:
        return ""
    body_sz = max(set(all_sizes), key=all_sizes.count)

    out = [f"# {title}\n"]
    for pi in pdf_info:
        page_idx = pi.get("page_idx", 0)
        blocks = pi.get("preproc_blocks", []) + pi.get("discarded_blocks", [])

        block_list = []
        for blk in blocks:
            try:
                x0, y0, x1, y1 = blk["bbox"]
            except (KeyError, TypeError, ValueError):
                continue
            txt = ""
            max_sz = 0
            for line in blk.get("lines", []):
                for sp in line.get("spans", []):
                    t = sp.get("content", "").strip()
                    if t:
                        txt += t
                        max_sz = max(max_sz, sp.get("size", 0))
            txt = txt.strip()
            if txt:
                block_list.append(((x0, y0, x1, y1), max_sz, txt))

        if not block_list:
            continue

        out.append(f"\n## 第 {page_idx + 1} 页\n")

        merged = []
        for i, (bbox, sz, txt) in enumerate(block_list):
            if merged:
                prev_bbox = block_list[i - 1][0]
                prev_text = merged[-1][1]
                same_x = abs(prev_bbox[0] - bbox[0]) < 8
                y_gap = bbox[1] - prev_bbox[3]
                line_h = max(12, prev_bbox[3] - prev_bbox[1])
                close = y_gap < line_h * 0.6
                prev_ends_punct = prev_text and prev_text[-1] in SENT_END

                # 以合并组首块字号为基线检测跳变，避免 max 累积后基线漂移
                grp_sz = merged[-1][0]
                size_jump = abs(sz - grp_sz) > 1.5

                if same_x and close and not prev_ends_punct and not size_jump:
                    merged[-1] = (merged[-1][0], merged[-1][1] + txt)
                    continue
            merged.append((sz, txt))

        for sz, txt in merged:
            if sz > body_sz * 1.3 and len(txt) <= 25:
                out.append(f"\n### {txt}\n")
            elif sz > body_sz * 1.15 and len(txt) <= 30:
                out.append(f"\n#### {txt}\n")
            else:
                out.append(txt + "\n")
        out.append("\n")

    return "\n".join(out)


# ============================================================
# 模式 3：现有 OCR md → 启发式合并
# ============================================================
def extract_ocr_md(md_path: str, title: str) -> str:
    """从已有 OCR 输出的 md 合并段落。兼容两种格式：
       A. 有 `## 第 N 页` 标记（按页切）
       B. 无分页标记（按 frontmatter 的 pages 字段伪分页）"""
    text = Path(md_path).read_text(encoding="utf-8")

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            text = text[end + 4:]

    has_page_marks = bool(re.search(r"^## 第\s*\d+\s*页", text, flags=re.MULTILINE))
    if has_page_marks:
        pages = re.split(r"^## 第\s*(\d+)\s*页\s*$", text, flags=re.MULTILINE)
        page_dict = {}
        for i in range(1, len(pages) - 1, 2):
            try:
                pno = int(pages[i])
            except ValueError:
                continue
            page_dict[pno] = pages[i + 1]
    else:
        total_chars = len(text)
        m = re.search(r"^pages:\s*(\d+)", text, flags=re.MULTILINE)
        est_pages = int(m.group(1)) if m else max(1, total_chars // 2000)
        if est_pages <= 1:
            page_dict = {1: text}
        else:
            per_page = total_chars // est_pages
            cuts = [0]
            for i in range(1, est_pages):
                guess = i * per_page
                # 在估计位置前后各 200 字符范围内找自然断点
                search_start = max(0, guess - 200)
                search_end = min(total_chars, guess + 200)
                snippet = text[search_start:search_end]
                # 优先找段落边界（连续换行）
                para = snippet.rfind("\n\n")
                if para > 0:
                    cuts.append(search_start + para + 2)
                    continue
                # 其次找句末标点
                best = -1
                for ch in SENT_END:
                    pos = snippet[:200].rfind(ch)
                    if pos > best:
                        best = pos
                if best >= 0:
                    cuts.append(search_start + best + 1)
                else:
                    cuts.append(guess)
            cuts.append(total_chars)
            page_dict = {}
            for i in range(est_pages):
                page_dict[i + 1] = text[cuts[i]:cuts[i + 1]]

    out = [f"# {title}\n"]
    for pno in sorted(page_dict.keys()):
        page_text = page_dict[pno]
        raw_lines = [ln.strip() for ln in page_text.split("\n") if ln.strip()]
        lines = [ln for ln in raw_lines if not is_page_noise(ln)]
        if not lines:
            continue

        out.append(f"\n## 第 {pno} 页\n")

        paragraphs = []
        i = 0
        while i < len(lines):
            cur = lines[i]
            prev_len = len(lines[i - 1]) if i > 0 else 0
            next_len = len(lines[i + 1]) if i + 1 < len(lines) else 0

            if is_short_title(cur, prev_len, next_len):
                paragraphs.append(("h3", cur))
                i += 1
                continue

            merged = cur
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if is_short_title(nxt, len(merged), len(lines[j + 1]) if j + 1 < len(lines) else 0):
                    break
                if merged and merged[-1] in SENT_END:
                    break
                if merged and merged[-1] in SENT_END_ASCII and len(nxt) > 15:
                    break
                merged += nxt
                j += 1

            paragraphs.append(("p", merged))
            i = j

        for kind, t in paragraphs:
            if kind == "h3":
                out.append(f"\n### {t}\n")
            else:
                out.append(t + "\n")
        out.append("\n")

    return "\n".join(out)


# ============================================================
# 模式选择
# ============================================================
def pick_mode(input_path: str, mode: str = "auto", ocr_dir: str | None = None):
    """返回 (mode_name, source_path, hint)。"""
    if mode != "auto":
        return mode, input_path, None

    if input_path.lower().endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(input_path)
            sample_chars = sum(len(doc[i].get_text()) for i in range(min(5, len(doc))))
            doc.close()
            if sample_chars > 200:
                return "pymupdf", input_path, None
        except Exception:
            # PDF 损坏或无文字层 → 继续尝试 OCR 路径
            pass

        dir_name = os.path.dirname(input_path)
        stem = Path(input_path).stem
        candidates = [
            os.path.join(dir_name, f"{stem}_middle.json"),
            os.path.join(dir_name, "_mineru", f"{stem}_middle.json"),
            os.path.join(dir_name, "_mineru_batch", f"{stem}", "ocr", f"{stem}_middle.json"),
        ]
        if ocr_dir:
            candidates.insert(0, os.path.join(ocr_dir, f"{stem}_middle.json"))
        for cand in candidates:
            if os.path.exists(cand):
                return "mineru", cand, None

        md_candidates = [
            os.path.join(dir_name, f"{stem}.md"),
            os.path.join(dir_name, "_ocr", f"{stem}.md"),
        ]
        if ocr_dir:
            md_candidates.insert(0, os.path.join(ocr_dir, f"{stem}.md"))
        for cand in md_candidates:
            if os.path.exists(cand):
                return "ocr", cand, None

        hint = (
            f"扫描版 PDF 无 OCR 输出。需要先用 OCR 工具（MinerU / PaddleOCR / Tesseract）"
            f"生成 {stem}_middle.json 或 {stem}.md，再放回本目录或 _mineru/ 下"
        )
        return "skip", "", hint

    if input_path.lower().endswith(".md"):
        return "ocr", input_path, None

    return "skip", "", f"不支持的文件类型: {input_path}"


# ============================================================
# 入口
# ============================================================
def process_one(
    input_path: str,
    output_dir: str,
    mode: str = "auto",
    ocr_dir: str | None = None,
) -> str | None:
    """处理单个文件，返回输出路径；跳过则返回 None。"""
    picked, source, hint = pick_mode(input_path, mode, ocr_dir)
    if picked == "skip":
        print(f"  [SKIP] {input_path}")
        if hint:
            print(f"         → {hint}")
        return None

    if picked == "pymupdf":
        title = detect_title_from_pdf_meta(source)
        md = extract_pymupdf(source, title)
    elif picked == "mineru":
        title = Path(source).stem.replace("_middle", "")
        md = extract_mineru(source, title)
    elif picked == "ocr":
        title = Path(source).stem
        md = extract_ocr_md(source, title)
    else:
        return None

    out_path = os.path.join(output_dir, f"{Path(input_path).stem}.md")
    Path(out_path).write_text(md, encoding="utf-8")
    print(f"  [{picked}] ✓ {out_path}  ({os.path.getsize(out_path) // 1024} KB)")
    return out_path


def process_batch(
    inputs: list[str],
    output_dir: str,
    mode: str = "auto",
    ocr_dir: str | None = None,
    workers: int = 1,
) -> list[str]:
    """批量处理；workers > 1 时启用线程池并行。"""
    os.makedirs(output_dir, exist_ok=True)
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(process_one, p, output_dir, mode, ocr_dir): p
                for p in inputs
            }
            for fut in as_completed(futures):
                fut.result()
    else:
        for p in inputs:
            process_one(p, output_dir, mode, ocr_dir)
    return inputs
