# -*- coding: utf-8 -*-
"""
03_b076_mobility_score.py
B076 KT 생활이동 데이터로 행정동별 '2030유입점수'를 만든다.

[반출정책 준수]
- popl_cnt 원값/단순합계는 export_safe 로 절대 보내지 않는다.
- 2030유입_규모지수는 표준화 후 점수 계산에만 사용하고, 원 유입량은 노출하지 않는다.
- export_safe 산출물에는
  행정동코드, 2030유입_증가율, 외부유입비율,
  2030유입점수, 2030유입순위, 2030유입등급
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
B076_FILES = None  # 예: ["KT_LIFE_MIG_202401.csv", ...]
B076_FILE_PATTERNS = ["B076", "생활이동", "KT", "MIGRATION", "MIG"]


# =====================================================================
# 컬럼 후보
# =====================================================================
COL_START_DT = ["start_dt", "STDR_DE", "기준일자", "출발일자", "ymd", "date"]
COL_ARV_DT = ["arv_dt", "도착일자"]
COL_START_EMD = ["start_emd", "출발행정동", "출발_행정동", "ORG_ADSTRD_CD", "ORIGIN_EMD"]
COL_ARV_EMD = ["arv_emd", "도착행정동", "도착_행정동", "DEST_ADSTRD_CD", "DEST_EMD"]
COL_AGE = ["agegrd_nm", "agegrp_nm", "연령대", "age_grp", "AGE"]
COL_SEX = ["sex_nm", "성별"]
COL_PLACE_TYPE = ["start_arv_place_type", "place_type", "장소유형"]
COL_POPL = ["popl_cnt", "유동인구", "이동인구", "POP_CNT", "POPULATION"]


# =====================================================================
# 1. 파일 입력
# =====================================================================
def resolve_input_files() -> list[Path]:
    if B076_FILES:
        out = []
        for f in B076_FILES:
            p = Path(f) if Path(f).is_absolute() else cfg.RAW_DIR / f
            if not p.exists():
                raise FileNotFoundError(f"지정된 B076 파일을 찾지 못했습니다: {p}")
            out.append(p)
        return out
    files = cfg.list_raw_files(patterns=B076_FILE_PATTERNS)
    if not files:
        raise FileNotFoundError(
            "B076 파일을 자동 탐색하지 못했습니다.\n"
            f"확인 경로: {cfg.RAW_DIR}\n"
            "→ 03_b076_mobility_score.py 상단 B076_FILES 에 파일명을 직접 지정하세요."
        )
    return files


def load_b076(paths: list[Path]) -> pd.DataFrame:
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
# 2. 전처리
# =====================================================================
def to_year_month(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    ym = pd.to_datetime(s, errors="coerce", format="%Y%m%d")
    if ym.isna().mean() > 0.5:
        ym = pd.to_datetime(s, errors="coerce", format="%Y%m")
    if ym.isna().mean() > 0.5:
        ym = pd.to_datetime(s, errors="coerce")
    return ym.dt.strftime("%Y-%m")


def filter_2030(df: pd.DataFrame, age_col: str) -> pd.DataFrame:
    s = df[age_col].astype(str).str.lower()
    pat = "|".join(cfg.AGE_2030_TOKENS)
    mask = s.str.contains(pat, case=False, na=False, regex=True)
    if mask.sum() == 0:
        # 숫자형(20, 30) 단독값 케이스
        try:
            num = pd.to_numeric(df[age_col], errors="coerce")
            mask = num.between(20, 39)
        except Exception:
            pass
    print(f"  - 2030 행 비율: {mask.mean():.1%}")
    return df.loc[mask].copy()


def aggregate_monthly(
    df: pd.DataFrame,
    arv_col: str,
    ym_col: str,
    popl_col: str,
    is_external_col: str,
) -> pd.DataFrame:
    df = df.copy()
    df[popl_col] = pd.to_numeric(df[popl_col], errors="coerce").fillna(0)

    # 도착 행정동 × 월 단위 (이미 2030 으로 필터링된 df)
    base = df.groupby([arv_col, ym_col], dropna=False)[popl_col].sum().reset_index()
    base = base.rename(columns={popl_col: "_inflow_2030"})

    # 외부 유입량 (start != arv)
    ext_df = df.loc[df[is_external_col]]
    ext = (
        ext_df.groupby([arv_col, ym_col], dropna=False)[popl_col]
        .sum()
        .reset_index()
        .rename(columns={popl_col: "_inflow_external"})
    )
    out = base.merge(ext, on=[arv_col, ym_col], how="left")
    out["_inflow_external"] = out["_inflow_external"].fillna(0)
    return out


def split_recent_prev(monthly: pd.DataFrame, ym_col: str) -> tuple[set, set]:
    ymset = sorted(monthly[ym_col].dropna().unique())
    if len(ymset) >= 6:
        return set(ymset[-3:]), set(ymset[-6:-3])
    if len(ymset) >= 2:
        half = len(ymset) // 2
        return set(ymset[half:]), set(ymset[:half])
    return set(ymset), set()


def compute_growth(monthly: pd.DataFrame, arv_col: str, ym_col: str) -> pd.DataFrame:
    recent, prev = split_recent_prev(monthly, ym_col)
    print(f"  - 최근 기간: {sorted(recent)}")
    print(f"  - 이전 기간: {sorted(prev) if prev else '(없음)'}")

    monthly = monthly.assign(
        _period=monthly[ym_col].apply(
            lambda v: "recent" if v in recent else ("prev" if v in prev else None)
        )
    ).dropna(subset=["_period"])

    pivot = (
        monthly.groupby([arv_col, "_period"])[["_inflow_2030", "_inflow_external"]]
        .mean()
        .unstack("_period")
    )
    pivot.columns = [f"{a}_{b}" for a, b in pivot.columns]
    pivot = pivot.reset_index()

    # 증가율
    pivot["2030유입_증가율"] = cfg.safe_divide(
        pivot.get("_inflow_2030_recent", 0) - pivot.get("_inflow_2030_prev", 0),
        pivot.get("_inflow_2030_prev", 0),
    )
    # 최근 기간 기준 외부유입비율
    pivot["외부유입비율"] = cfg.safe_divide(
        pivot.get("_inflow_external_recent", 0),
        pivot.get("_inflow_2030_recent", 0),
    )
    # 규모지수: 최근 기간 2030 유입량을 z-score 표준화 (원값은 노출하지 않음)
    pivot["_2030_규모_z"] = cfg.zscore(pivot.get("_inflow_2030_recent", 0))
    return pivot


# =====================================================================
# 3. 점수화
# =====================================================================
def build_score(growth_df: pd.DataFrame, arv_col: str) -> pd.DataFrame:
    df = growth_df.copy()
    df["_z_growth"] = cfg.zscore(df["2030유입_증가율"])
    df["_z_ratio"] = cfg.zscore(df["외부유입비율"])
    df["_z_scale"] = df["_2030_규모_z"]  # 이미 z-score

    w = cfg.W_MOBILITY
    df["2030유입점수"] = (
        w["growth"] * df["_z_growth"]
        + w["ratio"] * df["_z_ratio"]
        + w["scale"] * df["_z_scale"]
    )
    df["2030유입순위"] = df["2030유입점수"].rank(ascending=False, method="min").astype("Int64")
    df["2030유입등급"] = cfg.make_grade(df["2030유입점수"], scheme="ABCD")

    out = df.rename(columns={arv_col: "행정동코드"})[
        [
            "행정동코드",
            "2030유입_증가율", "외부유입비율",
            "2030유입점수", "2030유입순위", "2030유입등급",
        ]
    ]
    for c in ["2030유입_증가율", "외부유입비율", "2030유입점수"]:
        out[c] = out[c].astype(float).round(4)
    return out.sort_values("2030유입순위").reset_index(drop=True)


# =====================================================================
# 4. 시각화
# =====================================================================
def plot_top10(score_df: pd.DataFrame):
    cfg.setup_matplotlib_korean()
    import matplotlib.pyplot as plt

    top = score_df.nsmallest(10, "2030유입순위")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top["행정동코드"].astype(str), top["2030유입점수"], color="#10b981")
    ax.invert_yaxis()
    ax.set_title("B076 2030유입점수 TOP10")
    ax.set_xlabel("2030유입점수 (z-score 가중합)")
    ax.set_ylabel("행정동코드")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "b076_mobility_top10.png")
    plt.close(fig)


# =====================================================================
# 5. 메인
# =====================================================================
def main():
    print("[03_b076] 2030 유입 점수 계산 시작")

    paths = resolve_input_files()
    raw = load_b076(paths)
    print(f"  - 합본 행 수: {len(raw):,}")

    # 컬럼 매칭 (start_dt 우선, 없으면 arv_dt)
    date_col = cfg.find_col(raw, COL_START_DT, required=False) or cfg.find_col(raw, COL_ARV_DT)
    start_col = cfg.find_col(raw, COL_START_EMD)
    arv_col = cfg.find_col(raw, COL_ARV_EMD)
    age_col = cfg.find_col(raw, COL_AGE)
    popl_col = cfg.find_col(raw, COL_POPL)
    print(
        f"  - 매칭 컬럼: date={date_col}, start={start_col}, arv={arv_col}, "
        f"age={age_col}, popl={popl_col}"
    )

    df = raw.copy()
    df["_ym"] = to_year_month(df[date_col])
    df = df.dropna(subset=["_ym", arv_col])
    df = filter_2030(df, age_col)

    df["_is_external"] = df[start_col].astype(str) != df[arv_col].astype(str)

    monthly = aggregate_monthly(df, arv_col, "_ym", popl_col, "_is_external")
    cfg.save_internal_only(monthly, "b076_monthly_internal.csv")

    growth = compute_growth(monthly, arv_col, "_ym")
    cfg.save_internal_only(growth, "b076_growth_internal.csv")

    score = build_score(growth, arv_col)
    cfg.save_export_safe(score, "b076_mobility_score_export_safe.csv")

    plot_top10(score)
    print("[03_b076] 완료")


if __name__ == "__main__":
    main()
