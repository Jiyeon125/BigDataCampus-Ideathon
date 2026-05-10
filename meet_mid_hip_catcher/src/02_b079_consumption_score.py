# -*- coding: utf-8 -*-
"""
02_b079_consumption_score.py
B079 카드소비 데이터로 행정동별 '소비성장점수'를 만든다.

[반출정책 준수]
- 카드이용금액계, 카드이용건수계 원값/단순합계는 export_safe 로 절대 보내지 않는다.
- export_safe 산출물에는
  행정동코드, 소비금액_증가율, 소비건수_증가율, 객단가_증가율,
  소비성장점수, 소비성장순위, 소비성장등급
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
# 사용자 설정: 파일 경로
# =====================================================================
# - 정확한 파일명을 모르면 None 으로 두면 data/raw 에서 자동 탐색.
# - 직접 지정하려면 절대경로 또는 RAW_DIR 기준 상대경로의 파일명을 적는다.
B079_FILES = None  # 예: ["SEOUL_SIMIN_01.txt", "SEOUL_SIMIN_07.csv"]

# 자동 탐색 시 사용할 파일명 키워드 (부분일치, 대소문자 무시)
B079_FILE_PATTERNS = ["SEOUL_SIMIN", "B079", "카드소비", "SIMIN"]


# =====================================================================
# 컬럼 후보 (실제 파일마다 다를 수 있어 풍부하게)
# =====================================================================
COL_DATE = ["기준일자", "기준_일자", "기준일", "STDR_DE", "STDR_YM", "ymd", "date"]
COL_HDONG_CODE = [
    "고객행정동코드", "가맹점행정동코드",
    "행정동코드", "ADSTRD_CD", "EMD_CD", "DONG_CD", "HDONG_CD",
]
COL_HDONG_NAME = [
    "고객행정동명", "가맹점행정동명", "행정동명",
    "ADSTRD_NM", "EMD_NM", "DONG_NM",
]
COL_INDUTY = ["업종대분류", "업종명", "업종", "MCT_CAT_CD_NM", "INDUTY_NM"]
COL_AMOUNT = ["카드이용금액계", "이용금액", "amount", "USE_AMT", "AMT"]
COL_COUNT = ["카드이용건수계", "이용건수", "count", "USE_CNT", "CNT"]


# =====================================================================
# 1. 파일 탐색 / 로드
# =====================================================================
def resolve_input_files() -> list[Path]:
    if B079_FILES:
        out = []
        for f in B079_FILES:
            p = Path(f)
            if not p.is_absolute():
                p = cfg.RAW_DIR / f
            if not p.exists():
                raise FileNotFoundError(f"지정된 B079 파일을 찾지 못했습니다: {p}")
            out.append(p)
        return out
    files = cfg.list_raw_files(patterns=B079_FILE_PATTERNS)
    if not files:
        raise FileNotFoundError(
            "B079 파일을 자동 탐색하지 못했습니다.\n"
            f"확인 경로: {cfg.RAW_DIR}\n"
            "→ 02_b079_consumption_score.py 상단 B079_FILES 에 파일명을 직접 지정하세요."
        )
    return files


def load_b079(paths: list[Path]) -> pd.DataFrame:
    """여러 파일을 합쳐 단일 DataFrame 반환. 원본 행은 출력하지 않는다."""
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
# 2. 전처리 (내부 계산용)
# =====================================================================
def to_year_month(series: pd.Series) -> pd.Series:
    """다양한 일자 표기를 'YYYY-MM' 으로 변환."""
    s = series.astype(str).str.strip()
    # 숫자 8자리 (YYYYMMDD) / 6자리 (YYYYMM) / 하이픈 포맷 모두 처리
    ym = pd.to_datetime(s, errors="coerce", format="%Y%m%d")
    if ym.isna().mean() > 0.5:
        ym = pd.to_datetime(s, errors="coerce", format="%Y%m")
    if ym.isna().mean() > 0.5:
        ym = pd.to_datetime(s, errors="coerce")
    return ym.dt.strftime("%Y-%m")


def filter_fnb(df: pd.DataFrame, ind_col: str) -> pd.DataFrame:
    """업종명에 F&B 키워드가 포함된 행만 남기되, 0건이면 전체로 fallback."""
    s = df[ind_col].astype(str)
    mask = s.str.contains("|".join(cfg.FNB_KEYWORDS), case=False, na=False)
    if mask.sum() == 0:
        print("  [경고] F&B 키워드 매칭 0건 → 업종 전체로 fallback")
        return df
    print(f"  - F&B 행 비율: {mask.mean():.1%}")
    return df.loc[mask].copy()


def aggregate_monthly(
    df: pd.DataFrame, code_col: str, ym_col: str, amt_col: str, cnt_col: str
) -> pd.DataFrame:
    """행정동 × 월 단위 내부 집계."""
    df = df.copy()
    df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce")
    df[cnt_col] = pd.to_numeric(df[cnt_col], errors="coerce")
    g = (
        df.groupby([code_col, ym_col], dropna=False)
          .agg(_amt=(amt_col, "sum"), _cnt=(cnt_col, "sum"))
          .reset_index()
    )
    g["_ticket"] = cfg.safe_divide(g["_amt"], g["_cnt"])  # 객단가 (내부값)
    return g


def split_recent_prev(monthly: pd.DataFrame, ym_col: str) -> tuple[set, set]:
    """
    월 정렬 후 최근 3개월 / 직전 3개월 구분.
    데이터가 6개월 미만이면 가능한 만큼 균등 분할.
    """
    ymset = sorted(monthly[ym_col].dropna().unique())
    if len(ymset) >= 6:
        recent = set(ymset[-3:])
        prev = set(ymset[-6:-3])
    elif len(ymset) >= 2:
        half = len(ymset) // 2
        prev = set(ymset[:half])
        recent = set(ymset[half:])
    else:
        recent = set(ymset)
        prev = set()
    return recent, prev


def compute_growth(monthly: pd.DataFrame, code_col: str, ym_col: str) -> pd.DataFrame:
    """행정동별 최근/이전 평균 비교 → 증가율 산출 (내부값)."""
    recent, prev = split_recent_prev(monthly, ym_col)
    print(f"  - 최근 기간: {sorted(recent)}")
    print(f"  - 이전 기간: {sorted(prev) if prev else '(없음)'}")

    monthly = monthly.assign(
        _period=monthly[ym_col].apply(
            lambda v: "recent" if v in recent else ("prev" if v in prev else None)
        )
    ).dropna(subset=["_period"])

    pivot = (
        monthly.groupby([code_col, "_period"])[["_amt", "_cnt", "_ticket"]]
        .mean()
        .unstack("_period")
    )
    pivot.columns = [f"{a}_{b}" for a, b in pivot.columns]
    pivot = pivot.reset_index()

    # 증가율 계산 (반출용 결과 컬럼)
    pivot["소비금액_증가율"] = cfg.safe_divide(
        pivot.get("_amt_recent", 0) - pivot.get("_amt_prev", 0),
        pivot.get("_amt_prev", 0),
    )
    pivot["소비건수_증가율"] = cfg.safe_divide(
        pivot.get("_cnt_recent", 0) - pivot.get("_cnt_prev", 0),
        pivot.get("_cnt_prev", 0),
    )
    pivot["객단가_증가율"] = cfg.safe_divide(
        pivot.get("_ticket_recent", 0) - pivot.get("_ticket_prev", 0),
        pivot.get("_ticket_prev", 0),
    )

    return pivot


# =====================================================================
# 3. 점수화
# =====================================================================
def build_score(growth_df: pd.DataFrame, code_col: str) -> pd.DataFrame:
    df = growth_df.copy()
    df["_z_amt"] = cfg.zscore(df["소비금액_증가율"])
    df["_z_cnt"] = cfg.zscore(df["소비건수_증가율"])
    df["_z_tk"] = cfg.zscore(df["객단가_증가율"])

    w = cfg.W_CONSUMPTION
    df["소비성장점수"] = (
        w["count_growth"] * df["_z_cnt"]
        + w["amount_growth"] * df["_z_amt"]
        + w["ticket_growth"] * df["_z_tk"]
    )
    df["소비성장순위"] = df["소비성장점수"].rank(ascending=False, method="min").astype("Int64")
    df["소비성장등급"] = cfg.make_grade(df["소비성장점수"], scheme="ABCD")

    out = df.rename(columns={code_col: "행정동코드"})[
        [
            "행정동코드",
            "소비금액_증가율", "소비건수_증가율", "객단가_증가율",
            "소비성장점수", "소비성장순위", "소비성장등급",
        ]
    ]
    # 증가율은 비율(%)이지만 소수로 유지하고, 라운딩만 적용
    for c in ["소비금액_증가율", "소비건수_증가율", "객단가_증가율", "소비성장점수"]:
        out[c] = out[c].astype(float).round(4)
    return out.sort_values("소비성장순위").reset_index(drop=True)


# =====================================================================
# 4. 시각화
# =====================================================================
def plot_top10(score_df: pd.DataFrame):
    cfg.setup_matplotlib_korean()
    import matplotlib.pyplot as plt

    top = score_df.nsmallest(10, "소비성장순위")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top["행정동코드"].astype(str), top["소비성장점수"], color="#3b82f6")
    ax.invert_yaxis()
    ax.set_title("B079 소비성장점수 TOP10")
    ax.set_xlabel("소비성장점수 (z-score 가중합)")
    ax.set_ylabel("행정동코드")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "b079_consumption_top10.png")
    plt.close(fig)


# =====================================================================
# 5. 메인
# =====================================================================
def main():
    print("[02_b079] 카드소비 점수 계산 시작")

    paths = resolve_input_files()
    raw = load_b079(paths)
    print(f"  - 합본 행 수: {len(raw):,}")

    # 컬럼 매칭
    date_col = cfg.find_col(raw, COL_DATE)
    code_col = cfg.find_col(raw, COL_HDONG_CODE)
    ind_col = cfg.find_col(raw, COL_INDUTY, required=False)
    amt_col = cfg.find_col(raw, COL_AMOUNT)
    cnt_col = cfg.find_col(raw, COL_COUNT)
    print(
        f"  - 매칭 컬럼: 일자={date_col}, 행정동={code_col}, "
        f"업종={ind_col}, 금액={amt_col}, 건수={cnt_col}"
    )

    # 업종 필터 (없으면 전체 사용)
    df = raw.copy()
    if ind_col is not None:
        df = filter_fnb(df, ind_col)

    # 월 컬럼 생성
    df["_ym"] = to_year_month(df[date_col])
    df = df.dropna(subset=["_ym", code_col])

    # 내부 집계
    monthly = aggregate_monthly(df, code_col, "_ym", amt_col, cnt_col)
    cfg.save_internal_only(monthly, "b079_monthly_internal.csv")

    growth = compute_growth(monthly, code_col, "_ym")
    cfg.save_internal_only(growth, "b079_growth_internal.csv")

    score = build_score(growth, code_col)
    cfg.save_export_safe(score, "b079_consumption_score_export_safe.csv")

    plot_top10(score)
    print("[02_b079] 완료")


if __name__ == "__main__":
    main()
