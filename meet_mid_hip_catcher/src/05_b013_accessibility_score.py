# -*- coding: utf-8 -*-
"""
05_b013_accessibility_score.py
B013 대중교통 데이터 중 '지하철역 정보' / '버스정류장 정보' 메타파일만 사용하여
행정동별 '접근성점수'를 만든다.

[반출정책 준수]
- 개별 승하차 거래내역 파일은 사용하지 않는다.
- 정류장 수, 역 수의 원값은 export_safe 로 저장하지 않는다.
- 정류장/역 목록도 export_safe 로 저장하지 않는다.
- export_safe 산출물에는
  행정동코드, 접근성점수, 접근성순위, 접근성등급
  만 포함한다.
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


# =====================================================================
# 사용자 설정
# =====================================================================
B013_BUS_FILES = None      # 예: ["BUS_STOP_INFO.csv"]
B013_SUBWAY_FILES = None   # 예: ["SUBWAY_STATION_INFO.csv"]

# 자동 탐색 키워드 (거래내역 파일은 명시적으로 제외 처리)
BUS_PATTERNS = ["BUS_STOP", "버스정류장", "정류장정보", "BUSSTOP", "BSTP"]
SUBWAY_PATTERNS = ["SUBWAY_STATION", "지하철역", "역정보", "SUBWAY"]

# 거래내역 의심 키워드 (자동 탐색 시 제외)
EXCLUDE_PATTERNS = [
    "TRANS", "TRADE", "USE", "이용", "거래", "승하차", "탑승",
    "RIDER", "TRIP", "AFC",
]


# =====================================================================
# 컬럼 후보
# =====================================================================
COL_DONG_CD = ["ADSTRD_CD", "행정동코드", "EMD_CD", "DONG_CD", "HDONG_CD"]
COL_DONG_NM = ["ADSTRD_NM", "행정동명", "EMD_NM", "DONG_NM"]
COL_STATION_ID = ["STATION_ID", "역ID", "STATN_ID"]
COL_STOP_ID = ["STOP_ID", "정류장ID", "BSTP_ID", "BUS_STOP_ID"]


# =====================================================================
# 1. 파일 입력
# =====================================================================
def is_excluded(name: str) -> bool:
    s = name.lower()
    return any(k.lower() in s for k in EXCLUDE_PATTERNS)


def find_files(explicit: list[str] | None, patterns: list[str]) -> list[Path]:
    if explicit:
        out = []
        for f in explicit:
            p = Path(f) if Path(f).is_absolute() else cfg.RAW_DIR / f
            if not p.exists():
                raise FileNotFoundError(f"지정된 B013 파일을 찾지 못했습니다: {p}")
            out.append(p)
        return out
    cands = cfg.list_raw_files(patterns=patterns)
    cands = [p for p in cands if not is_excluded(p.name)]
    return cands


def load_files(paths: list[Path]) -> pd.DataFrame | None:
    if not paths:
        return None
    frames = []
    for p in paths:
        df, meta = cfg.read_table_safely(p)
        print(
            f"  - 로드: {p.name} | rows={len(df)} | ncol={df.shape[1]} | "
            f"enc={meta['encoding']} | sep={repr(meta['sep'])}"
        )
        frames.append(df)
    return pd.concat(frames, axis=0, ignore_index=True)


# =====================================================================
# 2. 행정동별 카운트
# =====================================================================
def count_by_dong(df: pd.DataFrame, id_candidates: list[str]) -> pd.DataFrame:
    """행정동코드/행정동명 단위로 ID 카운트 (중복 제거)."""
    code_col = cfg.find_col(df, COL_DONG_CD, required=False)
    name_col = cfg.find_col(df, COL_DONG_NM, required=False)
    id_col = cfg.find_col(df, id_candidates, required=False)

    if code_col is None and name_col is None:
        raise KeyError("정류장/역 파일에서 행정동 컬럼을 찾지 못했습니다.")

    key = code_col or name_col
    df = df.copy()
    if id_col is not None:
        df = df.drop_duplicates(subset=[id_col])
    g = df.groupby(key, dropna=False).size().reset_index(name="_cnt")
    g = g.rename(columns={key: "행정동코드"})
    return g


# =====================================================================
# 3. 점수화
# =====================================================================
def build_score(bus: pd.DataFrame | None, subway: pd.DataFrame | None) -> pd.DataFrame:
    if bus is None and subway is None:
        raise FileNotFoundError(
            "B013 정류장/역 메타 파일을 찾지 못했습니다. "
            "raw 폴더에 BUS_STOP / SUBWAY_STATION 정보 파일을 두거나 "
            "05_b013_accessibility_score.py 상단에 파일을 직접 지정하세요."
        )

    if bus is not None and subway is not None:
        merged = bus.merge(
            subway, on="행정동코드", how="outer", suffixes=("_bus", "_sub")
        )
        merged["_cnt_bus"] = merged["_cnt_bus"].fillna(0)
        merged["_cnt_sub"] = merged["_cnt_sub"].fillna(0)
        # z-score 표준화 후 가중합 (지하철 가중을 약간 높게)
        merged["_z_bus"] = cfg.zscore(merged["_cnt_bus"])
        merged["_z_sub"] = cfg.zscore(merged["_cnt_sub"])
        merged["접근성점수"] = 0.4 * merged["_z_bus"] + 0.6 * merged["_z_sub"]
    elif bus is not None:
        merged = bus.copy()
        merged["접근성점수"] = cfg.zscore(merged["_cnt"])
    else:
        merged = subway.copy()
        merged["접근성점수"] = cfg.zscore(merged["_cnt"])

    merged["접근성순위"] = merged["접근성점수"].rank(ascending=False, method="min").astype("Int64")
    merged["접근성등급"] = cfg.make_grade(merged["접근성점수"], scheme="ABCD")

    out = merged[["행정동코드", "접근성점수", "접근성순위", "접근성등급"]].copy()
    out["접근성점수"] = out["접근성점수"].astype(float).round(4)
    return out.sort_values("접근성순위").reset_index(drop=True)


# =====================================================================
# 4. 시각화
# =====================================================================
def plot_top10(score_df: pd.DataFrame):
    cfg.setup_matplotlib_korean()
    import matplotlib.pyplot as plt

    top = score_df.nsmallest(10, "접근성순위")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top["행정동코드"].astype(str), top["접근성점수"], color="#8b5cf6")
    ax.invert_yaxis()
    ax.set_title("B013 접근성점수 TOP10")
    ax.set_xlabel("접근성점수 (정류장/역 표준화 가중합)")
    ax.set_ylabel("행정동코드")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "b013_accessibility_top10.png")
    plt.close(fig)


# =====================================================================
# 5. 메인
# =====================================================================
def main():
    print("[05_b013] 접근성 점수 계산 시작")

    bus_paths = find_files(B013_BUS_FILES, BUS_PATTERNS)
    sub_paths = find_files(B013_SUBWAY_FILES, SUBWAY_PATTERNS)
    print(f"  - 버스정류장 파일: {[p.name for p in bus_paths]}")
    print(f"  - 지하철역 파일: {[p.name for p in sub_paths]}")

    bus_raw = load_files(bus_paths)
    sub_raw = load_files(sub_paths)

    bus_cnt = count_by_dong(bus_raw, COL_STOP_ID) if bus_raw is not None else None
    sub_cnt = count_by_dong(sub_raw, COL_STATION_ID) if sub_raw is not None else None

    # 내부 카운트는 internal_only 로만 저장
    if bus_cnt is not None:
        cfg.save_internal_only(bus_cnt.rename(columns={"_cnt": "_bus_stop_count"}),
                               "b013_bus_count_internal.csv")
    if sub_cnt is not None:
        cfg.save_internal_only(sub_cnt.rename(columns={"_cnt": "_subway_station_count"}),
                               "b013_subway_count_internal.csv")

    score = build_score(bus_cnt, sub_cnt)
    cfg.save_export_safe(score, "b013_accessibility_score_export_safe.csv")

    plot_top10(score)
    print("[05_b013] 완료")


if __name__ == "__main__":
    main()
