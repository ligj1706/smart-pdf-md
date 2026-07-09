"""pdf2m 命令行入口。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pdf2m import __version__, process_batch


def collect_inputs(input_arg: str) -> list[str]:
    inp = Path(input_arg)
    if inp.is_dir():
        return sorted(
            str(p)
            for p in inp.iterdir()
            if p.suffix.lower() in (".pdf", ".md")
        )
    return [str(inp)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf2m",
        description="pdf2m — 智能 PDF/OCR 多源路由转 Markdown（自动选择最佳抽取路径）",
    )
    parser.add_argument("input", help="输入：PDF 文件 / md 文件 / 目录")
    parser.add_argument(
        "-o", "--output",
        default="./_md_output",
        help="输出目录（默认 ./ _md_output）",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "pymupdf", "mineru", "ocr"],
        default="auto",
        help="抽取模式（默认 auto 自动选择）",
    )
    parser.add_argument(
        "--ocr-dir",
        default=None,
        help="OCR 输出目录（包含 *_middle.json 或 *.md），扫描版 PDF 自动从这里找",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="并行 worker 数（默认 1；CPU 密集建议 = CPU 核数）",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"pdf2m {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    inputs = collect_inputs(args.input)
    if not inputs:
        print(f"❌ 无可用输入：{args.input}")
        return 1

    print(f"📄 处理 {len(inputs)} 个文件 → {args.output}（并行度={args.workers}）")
    os.makedirs(args.output, exist_ok=True)
    process_batch(
        inputs=inputs,
        output_dir=args.output,
        mode=args.mode,
        ocr_dir=args.ocr_dir,
        workers=args.workers,
    )
    print("\n✅ 完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
