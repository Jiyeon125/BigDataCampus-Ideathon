# -*- coding: utf-8 -*-
"""
04_b021_local_store_score.py
B021 식품위생업소(+공중위생업소) 데이터로 행정동별 '로컬성점수'를 만든다.

[반출정책 준수]
- 원 업소명 목록은 export_safe 로 저장하지 않는다.
- F&B 업소 수, 프랜차이즈 의심 업소 수, 신규개업 업소 수의 원값은 export_safe 에 남기지 않는다.
- export_safe 산출물에는
  행정동명, 프랜차이즈비율, 로컬업소비율, 신규개업비율,
  로컬성점수, 로컬성순위, 로컬성등급
  만 포함한다.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
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
B021_FILES = None  # 예: ["B021_FOOD_HYG.csv"]
B021_FILE_PATTERNS = ["B021", "위생", "FOOD", "HYG", "BSSH", "식품위생", "공중위생"]


# =====================================================================
# 컬럼 후보
# =====================================================================
COL_BSSH_NM = ["BSSH_NM", "업소명", "사업장명"]
COL_INDUTY = ["SNITAT_INDUTY_NM", "업종명", "업태구분명", "INDUTY_NM"]
COL_BIZCND = ["SNITAT_BIZCND_NM", "업태명", "BIZCND_NM"]
COL_DONG = ["ADSTRD_NM", "행정동명", "동명", "EMD_NM"]
COL_DONG_CD = ["ADSTRD_CD", "행정동코드", "EMD_CD"]
COL_NEW_ADDR = ["NW_ADRES", "도로명주소", "신주소"]
COL_OLD_ADDR = ["OLD_ADRES", "지번주소", "구주소"]
COL_OPEN_DT = ["PRMISN_PRMISN_DE", "허가일자", "인허가일자", "개업일자"]
COL_CLOSE_DT = ["BIZQIT_DE", "폐업일자"]


NEW_OPEN_MONTHS = 12  # 최근 N개월 이내 개업 → 신규개업


# =====================================================================
# 1. 파일 입력
# =====================================================================
def resolve_input_files() -> list[Path]:
    if B021_FILES:
        out = []
        for f in B021_FILES:
            p = Path(f) if Path(f).is_absolute() else cfg.RAW_DIR / f
            if not p.exists():
                raise FileNotFoundError(f"지정된 B021 파일을 찾지 못했습니다: {p}")
            out.append(p)
        return out
    files = cfg.list_raw_files(patterns=B021_FILE_PATTERNS)
    if not files:
        raise FileNotFoundError(
            "B021 파일을 자동 탐색하지 못했습니다.\n"
            f"확인 경로: {cfg.RAW_DIR}\n"
            "→ 04_b021_local_store_score.py 상단 B021_FILES 에 파일명을 직접 지정하세요."
        )
    return files


def load_b021(paths: list[Path]) -> pd.DataFrame:
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
# 2. 분류 / 플래그
# =====================================================================
def is_fnb_row(df: pd.DataFrame, ind_col: str | None, biz_col: str | None) -> pd.Series:
    """업종/업태명 기준 F&B 여부."""
    parts = []
    if ind_col is not None:
        parts.append(df[ind_col].astype(str))
    if biz_col is not None:
        parts.append(df[biz_col].astype(str))
    if not parts:
        return pd.Series([True] * len(df), index=df.index)
    text = parts[0]
    for p in parts[1:]:
        text = text.str.cat(p, sep=" ", na_rep="")
    pat = "|".join(cfg.FNB_KEYWORDS)
    return text.str.contains(pat, case=False, na=False, regex=True)


def is_franchise_row(df: pd.DataFrame, name_col: str) -> pd.Series:
    """업소명 부분일치로 프랜차이즈 의심 여부 판정 (휴리스틱)."""
    s = df[name_col].astype(str).str.lower()
    pat = "|".join([k.lower() for k in cfg.FRANCHISE_KEYWORDS])
    return s.str.contains(pat, case=False, na=False, regex=True)


def is_open_row(df: pd.DataFrame, close_col: str | None) -> pd.Series:
    """폐업일자 결측이면 영업 중으로 간주."""
    if close_col is None or close_col not in df.columns:
        return pd.Series([True] * len(df), index=df.index)
    s = df[close_col].astype(str).str.strip()
    return s.isin(["", "nan", "NaN", "None", "0"]) | df[close_col].isna()


def is_new_open_row(df: pd.DataFrame, open_col: str | None) -> pd.Series:
    """최근 NEW_OPEN_MONTHS 이내 개업 여부."""
    if open_col is None or open_col not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    dt = pd.to_datetime(df[open_col].astype(str), errors="coerce", format="%Y%m%d")
    if dt.isna().mean() > 0.5:
        dt = pd.to_datetime(df[open_col].astype(str), errors="coerce")
    cutoff = pd.Timestamp.today() - pd.DateOffset(months=NEW_OPEN_MONTHS)
    return dt >= cutoff


# =====================================================================
# 3. 행정동별 집계
# =====================================================================
def aggregate_by_dong(
    df: pd.DataFrame, dong_col: str, fnb: pd.Series, fr: pd.Series, new: pd.Series
) -> pd.DataFrame:
    df = df.copy()
    df["_fnb"] = fnb.astype(int)
    df["_fr"] = (fnb & fr).astype(int)            # 프랜차이즈는 F&B 안에서만 집계
    df["_local"] = (fnb & ~fr).astype(int)        # 로컬업소 = F&B 중 비프랜차이즈
    df["_new"] = (fnb & new).astype(int)          # 신규개업도 F&B 안에서

    g = (
        df.groupby(dong_col, dropna=False)[["_fnb", "_fr", "_local", "_new"]]
        .sum()
        .reset_index()
    )
    g = g.rename(
        columns={
            "_fnb": "_fnb_cnt",
            "_fr": "_fr_cnt",
            "_local": "_local_cnt",
            "_new": "_new_cnt",
        }
    )
    return g


def to_ratios(agg: pd.DataFrame, dong_col: str, min_fnb: int = 5) -> pd.DataFrame:
    """비율 계산 + 표본 부족 행정동 제거."""
    agg = agg.loc[agg["_fnb_cnt"] >= min_fnb].copy()
    agg["프랜차이즈비율"] = cfg.safe_divide(agg["_fr_cnt"], agg["_fnb_cnt"])
    agg["로컬업소비율"] = cfg.safe_divide(agg["_local_cnt"], agg["_fnb_cnt"])
    agg["신규개업비율"] = cfg.safe_divide(agg["_new_cnt"], agg["_fnb_cnt"])
    return agg.rename(columns={dong_col: "행정동명"})


# =====================================================================
# 4. 점수화
# =====================================================================
def build_score(ratio_df: pd.DataFrame) -> pd.DataFrame:
    df = ratio_df.copy()
    # 비프랜차이즈성 = 1 - 프랜차이즈비율 → 표준화
    df["_z_nonfr"] = cfg.zscore(1 - df["프랜차이즈비율"])
    df["_z_local"] = cfg.zscore(df["로컬업소비율"])
    df["_z_new"] = cfg.zscore(df["신규개업비율"])

    w = cfg.W_LOCALITY
    df["로컬성점수"] = (
        w["non_franchise"] * df["_z_nonfr"]
        + w["local_ratio"] * df["_z_local"]
        + w["new_open"] * df["_z_new"]
    )
    df["로컬성순위"] = df["로컬성점수"].rank(ascending=False, method="min").astype("Int64")
    df["로컬성등급"] = cfg.make_grade(df["로컬성점수"], scheme="ABCD")

    out = df[
        [
            "행정동명",
            "프랜차이즈비율", "로컬업소비율", "신규개업비율",
            "로컬성점수", "로컬성순위", "로컬성등급",
        ]
    ].copy()
    for c in ["프랜차이즈비율", "로컬업소비율", "신규개업비율", "로컬성점수"]:
        out[c] = out[c].astype(float).round(4)
    return out.sort_values("로컬성순위").reset_index(drop=True)


# =====================================================================
# 5. 시각화
# =====================================================================
def plot_top10(score_df: pd.DataFrame):
    cfg.setup_matplotlib_korean()
    import matplotlib.pyplot as plt

    top = score_df.nsmallest(10, "로컬성순위")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top["행정동명"].astype(str), top["로컬성점수"], color="#f59e0b")
    ax.invert_yaxis()
    ax.set_title("B021 로컬성점수 TOP10")
    ax.set_xlabel("로컬성점수 (z-score 가중합)")
    ax.set_ylabel("행정동명")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "b021_local_score_top10.png")
    plt.close(fig)


# =====================================================================
# 6. 메인
# =====================================================================
def main():
    print("[04_b021] 로컬성 점수 계산 시작")

    paths = resolve_input_files()
    raw = load_b021(paths)
    print(f"  - 합본 행 수: {len(raw):,}")

    name_col = cfg.find_col(raw, COL_BSSH_NM)
    ind_col = cfg.find_col(raw, COL_INDUTY, required=False)
    biz_col = cfg.find_col(raw, COL_BIZCND, required=False)
    dong_col = cfg.find_col(raw, COL_DONG)
    open_col = cfg.find_col(raw, COL_OPEN_DT, required=False)
    close_col = cfg.find_col(raw, COL_CLOSE_DT, required=False)
    print(
        f"  - 매칭 컬럼: 업소명={name_col}, 업종={ind_col}, 업태={biz_col}, "
        f"행정동={dong_col}, 개업일={open_col}, 폐업일={close_col}"
    )

    fnb = is_fnb_row(raw, ind_col, biz_col)
    fr = is_franchise_row(raw, name_col)
    op = is_open_row(raw, close_col)
    new = is_new_open_row(raw, open_col)

    # 영업 중인 업소만
    df = raw.loc[op].copy()
    fnb = fnb.loc[op]
    fr = fr.loc[op]
    new = new.loc[op]
    print(f"  - F&B 행 비율: {fnb.mean():.1%}")
    print(f"  - 프랜차이즈 의심 비율(F&B 중): {(fr[fnb].mean() if fnb.any() else 0):.1%}")
    print(f"  - 신규개업 비율(F&B 중): {(new[fnb].mean() if fnb.any() else 0):.1%}")

    agg = aggregate_by_dong(df, dong_col, fnb, fr, new)
    cfg.save_internal_only(agg, "b021_dong_count_internal.csv")

    ratios = to_ratios(agg, dong_col)
    cfg.save_internal_only(ratios, "b021_dong_ratio_internal.csv")

    score = build_score(ratios)
    cfg.save_export_safe(score, "b021_local_store_score_export_safe.csv")

    plot_top10(score)
    print("[04_b021] 완료")


if __name__ == "__main__":
    main()
