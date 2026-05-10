# -*- coding: utf-8 -*-
"""
01_data_check.py
data/raw 안의 파일을 인벤토리(목록/메타) 수준으로만 점검한다.

[반출정책 준수]
- 원본 데이터의 행 내용은 절대 출력/저장하지 않는다.
- 결과(파일별 행수/컬럼명/날짜 컬럼 후보 존재 여부)는
  outputs/internal_only/DO_NOT_EXPORT_data_inventory.csv 로만 저장한다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

# ---------------- 00_config 동적 로드 ----------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
_spec = importlib.util.spec_from_file_location("cfg", _HERE / "00_config.py")
cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)
# -----------------------------------------------------


# 날짜 컬럼으로 추정할 후보 키워드(부분일치)
DATE_HINTS = [
    "기준일자", "기준_일자", "기준일",
    "start_dt", "arv_dt", "ymd", "date", "일자", "년월", "ym",
    "stdr_ym", "stdr_de", "PRMISN_PRMISN_DE", "BIZQIT_DE",
]


def summarize_one(path: Path) -> dict:
    """파일 하나에 대해 안전한 메타 요약을 만든다.
    원본 행을 출력/반환하지 않는다.
    """
    info = {
        "file_name": path.name,
        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        "rows_estimate": None,
        "n_columns": None,
        "encoding": None,
        "sep_repr": None,
        "columns_preview": None,
        "has_date_column": False,
        "date_column_candidates": None,
        "missing_total": None,
        "read_status": "OK",
        "read_error": "",
    }
    try:
        # 1차 샘플 읽기로 인코딩/구분자 자동 탐지 (행 출력 없이)
        df_sample, meta = cfg.read_table_safely(path, nrows=5000)
        info["encoding"] = meta["encoding"]
        info["sep_repr"] = repr(meta["sep"])
        info["n_columns"] = df_sample.shape[1]
        info["columns_preview"] = ", ".join([str(c) for c in df_sample.columns[:30]])

        # 날짜 컬럼 후보 탐지 (컬럼명 부분일치)
        date_cols = []
        for c in df_sample.columns:
            cl = str(c).lower()
            if any(h.lower() in cl for h in DATE_HINTS):
                date_cols.append(str(c))
        info["has_date_column"] = bool(date_cols)
        info["date_column_candidates"] = ", ".join(date_cols) if date_cols else ""

        # 결측치 총합 (sample 기준 — 원값은 보지 않음)
        info["missing_total"] = int(df_sample.isna().sum().sum())

        # 행 수 추정 — 전체 카운트가 무거울 수 있어, 라인 카운트 시도 (실패 시 None)
        try:
            with open(path, "r", encoding=meta["encoding"], errors="ignore") as f:
                cnt = sum(1 for _ in f)
            info["rows_estimate"] = max(cnt - 1, 0)  # 헤더 1행 가정
        except Exception:
            info["rows_estimate"] = None

    except Exception as e:  # noqa: BLE001
        info["read_status"] = "FAIL"
        info["read_error"] = str(e)[:200]

    return info


def main():
    files = cfg.list_raw_files()
    print(f"[01_data_check] data/raw 탐색 → 파일 {len(files)}개")
    if not files:
        print("[안내] data/raw 폴더에 데이터 파일이 없습니다.")
        print(f"      경로: {cfg.RAW_DIR}")
        # 빈 인벤토리도 저장하여 다음 단계에서 동일한 인터페이스 보장
        empty = pd.DataFrame(columns=[
            "file_name", "file_size_mb", "rows_estimate", "n_columns",
            "encoding", "sep_repr", "columns_preview",
            "has_date_column", "date_column_candidates",
            "missing_total", "read_status", "read_error",
        ])
        cfg.save_internal_only(empty, "data_inventory.csv")
        return

    rows = []
    for p in files:
        print(f"  - 점검 중: {p.name} ({round(p.stat().st_size/1e6,2)} MB)")
        info = summarize_one(p)
        rows.append(info)
        # 원본 행은 절대 출력하지 않는다.
        # 메타 수준 로그만 남긴다.
        print(
            "    "
            f"status={info['read_status']} | "
            f"rows≈{info['rows_estimate']} | "
            f"ncol={info['n_columns']} | "
            f"date_col={info['has_date_column']} | "
            f"enc={info['encoding']}"
        )

    inv = pd.DataFrame(rows)
    cfg.save_internal_only(inv, "data_inventory.csv")
    print("[완료] 인벤토리 저장 → outputs/internal_only/DO_NOT_EXPORT_data_inventory.csv")


if __name__ == "__main__":
    main()
