"""跑 samples 目录的演示（自动 OCR-md 模式）。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pdf2m import process_one  # noqa: E402

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    sample = os.path.join(here, "sample.md")
    out_dir = os.path.join(here, "output")
    os.makedirs(out_dir, exist_ok=True)

    print(f"demo: 处理 {sample}\n")
    result = process_one(sample, out_dir)
    if result:
        print(f"\n输出已写到: {result}")