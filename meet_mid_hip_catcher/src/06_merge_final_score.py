# -*- coding: utf-8 -*-
"""
06_merge_final_score.py
4개 데이터셋의 점수(소비/2030유입/로컬성/접근성)를 병합하여
최종 만남 상권 후보 점수를 산출한다.

[반출정책 준수]
- 입력은 export_safe 의 4개 점수 CSV (이미 안전한 컬럼만 들어있음).
- 출력 산출물에도 점수/등급/순위/후보유형 외 다른 원값/단순집계 컬럼은 없다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------- 00_config 동적 로드 ----------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
_spec = importlib.util.spec_from_file_location("cfg", _HERE / "00_config.py")
cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)
# -----------------------------------------------------


B079_FILE = cfg.EXPORT_SAFE_DIR / "b079_consumption_score_export_safe.csv"
B076_FILE = cfg.EXPORT_SAFE_DIR / "b076_mobility_score_export_safe.csv"
B021_FILE = cfg.EXPORT_SAFE_DIR / "b021_local_store_score_export_safe.csv"
B013_FILE = cfg.EXPORT_SAFE_DIR / "b013_accessibility_score_export_safe.csv"


# 행정동코드 ↔ 행정동명 매핑이 가능한 lookup CSV (선택)
DONG_LOOKUP_FILE = cfg.RAW_DIR / "dong_lookup.csv"  # 컬럼: 행정동코드, 행정동명


# =====================================================================
# 1. 입력 점검
# =====================================================================
def load_or_warn(path: Path, label: str) -> pd.DataFrame | None:
    if not path.exists():
        print(f"  [경고] {label} 점수 파일이 없습니다: {path.name} (해당 점수는 0 으로 처리)")
        return None
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"행정동코드": str})
    print(f"  - 로드: {path.name} | shape={df.shape}")
    return df


def load_dong_lookup() -> pd.DataFrame | None:
    if not DONG_LOOKUP_FILE.exists():
        return None
    df = pd.read_csv(DONG_LOOKUP_FILE, encoding="utf-8-sig", dtype=str)
    code_col = cfg.find_col(df, ["행정동코드", "ADSTRD_CD", "EMD_CD"])
    name_col = cfg.find_col(df, ["행정동명", "ADSTRD_NM", "EMD_NM"])
    df = df[[code_col, name_col]].rename(
        columns={code_col: "행정동코드", name_col: "행정동명"}
    ).drop_duplicates()
    return df


# =====================================================================
# 2. 병합
# =====================================================================
def merge_scores(
    b079: pd.DataFrame | None,
    b076: pd.DataFrame | None,
    b021: pd.DataFrame | None,
    b013: pd.DataFrame | None,
    lookup: pd.DataFrame | None,
) -> pd.DataFrame:
    """행정동코드 기준 outer 병합. 이름 기반 점수(B021)는 lookup 으로 결합 시도."""
    base = pd.DataFrame(columns=["행정동코드"])

    if b079 is not None:
        base = base.merge(
            b079[["행정동코드", "소비성장점수", "소비성장등급"]],
            on="행정동코드", how="outer",
        )
    if b076 is not None:
        base = base.merge(
            b076[["행정동코드", "2030유입점수", "2030유입등급"]],
            on="행정동코드", how="outer",
        )
    if b013 is not None:
        base = base.merge(
            b013[["행정동코드", "접근성점수", "접근성등급"]],
            on="행정동코드", how="outer",
        )

    # 행정동명 결합
    if lookup is not None:
        base = base.merge(lookup, on="행정동코드", how="left")
    else:
        base["행정동명"] = pd.NA

    # 로컬성(이름 기반)
    if b021 is not None:
        b021_local = b021[["행정동명", "로컬성점수", "로컬성등급"]].copy()
        if "행정동명" not in base.columns or base["행정동명"].isna().all():
            # 코드 lookup 이 없는 경우 → 행정동명 기반 결합으로 우회
            base["행정동명"] = base["행정동코드"]  # placeholder
        base = base.merge(b021_local, on="행정동명", how="outer")

    return base


# =====================================================================
# 3. 정규화 + 최종점수 + 후보유형
# =====================================================================
SCORE_COLS = ["소비성장점수", "2030유입점수", "로컬성점수", "접근성점수"]


def normalize_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in SCORE_COLS:
        if c not in df.columns:
            df[c] = 0.0
        df[f"{c}_n"] = cfg.minmax(df[c].fillna(df[c].mean() if df[c].notna().any() else 0))
    return df


def compute_final(df: pd.DataFrame) -> pd.DataFrame:
    w = cfg.W_FINAL
    df["최종점수"] = (
        w["consumption"] * df["소비성장점수_n"]
        + w["mobility"] * df["2030유입점수_n"]
        + w["locality"] * df["로컬성점수_n"]
        + w["accessibility"] * df["접근성점수_n"]
    )
    df["최종순위"] = df["최종점수"].rank(ascending=False, method="min").astype("Int64")
    return df


def classify_type(row) -> str:
    """가장 강한 강점 1개로 후보유형을 라벨링. 모두 비슷하면 균형형."""
    parts = {
        "소비성장형": row.get("소비성장점수_n", 0),
        "2030유입형": row.get("2030유입점수_n", 0),
        "로컬상권형": row.get("로컬성점수_n", 0),
        "접근성우수형": row.get("접근성점수_n", 0),
    }
    vals = pd.Series(parts)
    if vals.isna().all():
        return "-"
    top_label = vals.idxmax()
    top_val = vals.max()
    others_mean = (vals.sum() - top_val) / 3
    # 1위 값이 나머지 평균보다 크게 높지 않으면 균형형
    if pd.notna(top_val) and pd.notna(others_mean) and (top_val - others_mean) < 0.10:
        return "균형형"
    return top_label


# =====================================================================
# 4. 메인
# =====================================================================
def main():
    print("[06_merge] 최종 점수 병합 시작")

    b079 = load_or_warn(B079_FILE, "소비성장")
    b076 = load_or_warn(B076_FILE, "2030유입")
    b021 = load_or_warn(B021_FILE, "로컬성")
    b013 = load_or_warn(B013_FILE, "접근성")
    lookup = load_dong_lookup()
    if lookup is None:
        print("  [안내] dong_lookup.csv 가 없어 행정동명 매칭이 비어 있을 수 있습니다.")

    if all(x is None for x in [b079, b076, b021, b013]):
        raise FileNotFoundError(
            "병합할 점수 파일이 하나도 없습니다. 02~05 스크립트를 먼저 실행하세요."
        )

    merged = merge_scores(b079, b076, b021, b013, lookup)
    merged = normalize_scores(merged)
    merged = compute_final(merged)
    merged["후보유형"] = merged.apply(classify_type, axis=1)

    out_cols = [
        "행정동코드", "행정동명",
        "소비성장점수", "소비성장등급",
        "2030유입점수", "2030유입등급",
        "로컬성점수", "로컬성등급",
        "접근성점수", "접근성등급",
        "최종점수", "최종순위", "후보유형",
    ]
    final = merged.copy()
    for c in out_cols:
        if c not in final.columns:
            final[c] = pd.NA
    final = final[out_cols].copy()

    # 라운딩
    for c in ["소비성장점수", "2030유입점수", "로컬성점수", "접근성점수", "최종점수"]:
        final[c] = pd.to_numeric(final[c], errors="coerce").round(4)

    final = final.sort_values("최종순위").reset_index(drop=True)

    cfg.save_export_safe(final, "final_meeting_spot_score_export_safe.csv")

    top10 = final.head(10).copy()
    cfg.save_export_safe(top10, "final_top10_export_safe.csv")

    print("[06_merge] 완료")


if __name__ == "__main__":
    main()
