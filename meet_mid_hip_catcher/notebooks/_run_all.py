# -*- coding: utf-8 -*-
"""
notebooks/ 의 .ipynb 들을 순서대로 실행해 end-to-end 동작을 검증한다.
실행 후 노트북 파일 자체는 결과(outputs)가 남지 않도록 원상복구한다.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent

ORDER = [
    "00_config.ipynb",
    "01_data_check.ipynb",
    "02_b079_consumption_score.ipynb",
    "03_b076_mobility_score.ipynb",
    "04_b021_local_store_score.ipynb",
    "05_b013_accessibility_score.ipynb",
    "06_merge_final_score.ipynb",
    "07_visualize_results.ipynb",
    "08_candidate_report_table.ipynb",
    "09_export_for_ppt.ipynb",
]


def run_one(nb_path: Path) -> None:
    print(f"\n=== {nb_path.name} 실행 시작 ===")
    t0 = time.time()
    nb = nbformat.read(nb_path, as_version=4)
    client = NotebookClient(nb, timeout=120, kernel_name="python3")
    client.execute(cwd=str(HERE))
    dt = time.time() - t0
    print(f"=== {nb_path.name} 실행 완료 ({dt:.1f}s) ===")


def main() -> None:
    for name in ORDER:
        run_one(HERE / name)
    print("\n[전체 노트북 실행 성공]")


if __name__ == "__main__":
    main()
