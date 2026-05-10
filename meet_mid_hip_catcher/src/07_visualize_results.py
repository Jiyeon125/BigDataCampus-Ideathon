# -*- coding: utf-8 -*-
"""
07_visualize_results.py
final_meeting_spot_score_export_safe.csv 를 읽어 발표용 그래프 4종을 생성한다.

[반출정책 준수]
- 그래프 안에 원본 단순합계 수치(금액/건수/유입량/업소수/정류장수)를 표시하지 않는다.
- 라벨/축 단위는 점수, 등급, 순위, 비율 중심.
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


FINAL_FILE = cfg.EXPORT_SAFE_DIR / "final_meeting_spot_score_export_safe.csv"


def load_final() -> pd.DataFrame:
    if not FINAL_FILE.exists():
        raise FileNotFoundError(
            f"최종 점수 파일이 없습니다: {FINAL_FILE.name}\n"
            "→ 06_merge_final_score.py 를 먼저 실행하세요."
        )
    df = pd.read_csv(FINAL_FILE, encoding="utf-8-sig", dtype={"행정동코드": str})
    print(f"  - 로드: {FINAL_FILE.name} | shape={df.shape}")
    return df


def label_for(df: pd.DataFrame) -> pd.Series:
    """행정동명이 있으면 행정동명, 없으면 행정동코드를 라벨로."""
    if "행정동명" in df.columns and df["행정동명"].notna().any():
        out = df["행정동명"].fillna(df["행정동코드"].astype(str))
    else:
        out = df["행정동코드"].astype(str)
    return out.astype(str)


# =====================================================================
# 그래프 1. 최종점수 TOP10
# =====================================================================
def plot_final_top10(df: pd.DataFrame):
    import matplotlib.pyplot as plt

    top = df.nsmallest(10, "최종순위")
    labels = label_for(top)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(labels, top["최종점수"], color="#ef4444")
    ax.invert_yaxis()
    ax.set_title("최종 후보 행정동 TOP10 (최종점수)")
    ax.set_xlabel("최종점수 (0~1 정규화 가중합)")
    ax.set_ylabel("행정동")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "final_top10_bar.png")
    plt.close(fig)


# =====================================================================
# 그래프 2. 소비성장 vs 2030유입
# =====================================================================
def plot_consumption_vs_mobility(df: pd.DataFrame):
    import matplotlib.pyplot as plt

    sub = df.dropna(subset=["소비성장점수", "2030유입점수"])
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        sub["소비성장점수"], sub["2030유입점수"],
        c=sub["최종점수"], cmap="viridis", s=30, alpha=0.7,
    )
    # TOP5만 라벨링
    top5 = sub.nsmallest(5, "최종순위")
    for _, r in top5.iterrows():
        nm = r.get("행정동명") or str(r["행정동코드"])
        ax.annotate(str(nm), (r["소비성장점수"], r["2030유입점수"]), fontsize=8)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_title("소비성장점수 × 2030유입점수")
    ax.set_xlabel("소비성장점수")
    ax.set_ylabel("2030유입점수")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "consumption_vs_mobility.png")
    plt.close(fig)


# =====================================================================
# 그래프 3. 로컬성 vs 최종점수
# =====================================================================
def plot_locality_vs_final(df: pd.DataFrame):
    import matplotlib.pyplot as plt

    sub = df.dropna(subset=["로컬성점수", "최종점수"])
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(
        sub["로컬성점수"], sub["최종점수"],
        c=sub["최종점수"], cmap="plasma", s=30, alpha=0.7,
    )
    top5 = sub.nsmallest(5, "최종순위")
    for _, r in top5.iterrows():
        nm = r.get("행정동명") or str(r["행정동코드"])
        ax.annotate(str(nm), (r["로컬성점수"], r["최종점수"]), fontsize=8)
    ax.set_title("로컬성점수 × 최종점수")
    ax.set_xlabel("로컬성점수")
    ax.set_ylabel("최종점수")
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "locality_vs_final_score.png")
    plt.close(fig)


# =====================================================================
# 그래프 4. 후보유형 분포
# =====================================================================
def plot_candidate_type(df: pd.DataFrame):
    import matplotlib.pyplot as plt

    cnt = df["후보유형"].fillna("미분류").value_counts()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(cnt.index, cnt.values, color="#0ea5e9")
    ax.set_title("후보유형별 행정동 개수")
    ax.set_xlabel("후보유형")
    ax.set_ylabel("행정동 수")
    for i, v in enumerate(cnt.values):
        ax.text(i, v, str(int(v)), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    cfg.save_figure_export_safe(fig, "candidate_type_count.png")
    plt.close(fig)


def main():
    print("[07_visualize] 결과 시각화 시작")
    cfg.setup_matplotlib_korean()
    df = load_final()

    plot_final_top10(df)
    plot_consumption_vs_mobility(df)
    plot_locality_vs_final(df)
    plot_candidate_type(df)
    print("[07_visualize] 완료")


if __name__ == "__main__":
    main()
