# -*- coding: utf-8 -*-
"""
08_candidate_report_table.py
TOP10 후보 행정동에 대해 발표용 해석 문장과 활용방안을 자동 생성한다.

[반출정책 준수]
- 원본 금액/건수/인구수/업소수는 어떤 형태로도 인용하지 않는다.
- 점수, 등급, 순위, 비율, 증가율, 후보유형만 사용한다.
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


TOP_FILE = cfg.EXPORT_SAFE_DIR / "final_top10_export_safe.csv"
B079_FILE = cfg.EXPORT_SAFE_DIR / "b079_consumption_score_export_safe.csv"
B076_FILE = cfg.EXPORT_SAFE_DIR / "b076_mobility_score_export_safe.csv"
B021_FILE = cfg.EXPORT_SAFE_DIR / "b021_local_store_score_export_safe.csv"


# =====================================================================
# 1. 데이터 로드
# =====================================================================
def load_top10() -> pd.DataFrame:
    if not TOP_FILE.exists():
        raise FileNotFoundError(
            f"TOP10 파일이 없습니다: {TOP_FILE.name}\n"
            "→ 06_merge_final_score.py 를 먼저 실행하세요."
        )
    return pd.read_csv(TOP_FILE, encoding="utf-8-sig", dtype={"행정동코드": str})


def load_optional(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig", dtype={"행정동코드": str})


# =====================================================================
# 2. 문장 생성 헬퍼
# =====================================================================
def fmt_pct(v) -> str:
    try:
        return f"{float(v) * 100:+.1f}%"
    except Exception:
        return "-"


def fmt_ratio(v) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "-"


def grade_word(g: str) -> str:
    return {"A": "최상위", "B": "상위", "C": "중위", "D": "하위"}.get(str(g), str(g))


def build_evidence(row: pd.Series, b079: pd.DataFrame | None,
                   b076: pd.DataFrame | None, b021: pd.DataFrame | None) -> tuple[str, str, str]:
    code = row["행정동코드"]
    name = row.get("행정동명")

    parts = []

    # 근거1: 소비성장
    if b079 is not None:
        r = b079.loc[b079["행정동코드"] == code]
        if not r.empty:
            r = r.iloc[0]
            parts.append(
                f"소비성장 {grade_word(r.get('소비성장등급'))} "
                f"(소비건수 증가율 {fmt_pct(r.get('소비건수_증가율'))}, "
                f"객단가 증가율 {fmt_pct(r.get('객단가_증가율'))})"
            )

    # 근거2: 2030 유입
    if b076 is not None:
        r = b076.loc[b076["행정동코드"] == code]
        if not r.empty:
            r = r.iloc[0]
            parts.append(
                f"2030 유입 {grade_word(r.get('2030유입등급'))} "
                f"(증가율 {fmt_pct(r.get('2030유입_증가율'))}, "
                f"외부유입비율 {fmt_ratio(r.get('외부유입비율'))})"
            )

    # 근거3: 로컬성
    if b021 is not None and pd.notna(name):
        r = b021.loc[b021["행정동명"] == name]
        if not r.empty:
            r = r.iloc[0]
            parts.append(
                f"로컬성 {grade_word(r.get('로컬성등급'))} "
                f"(프랜차이즈비율 {fmt_ratio(r.get('프랜차이즈비율'))}, "
                f"신규개업비율 {fmt_ratio(r.get('신규개업비율'))})"
            )

    # 부족분 채우기
    while len(parts) < 3:
        parts.append("-")
    return parts[0], parts[1], parts[2]


def build_summary(row: pd.Series) -> str:
    name = row.get("행정동명") or row.get("행정동코드")
    typ = row.get("후보유형", "-")
    rank = row.get("최종순위", "-")
    return (
        f"{name} 은(는) 최종순위 {rank}위의 '{typ}' 후보 행정동입니다. "
        f"소비성장 {grade_word(row.get('소비성장등급'))}, "
        f"2030유입 {grade_word(row.get('2030유입등급'))}, "
        f"로컬성 {grade_word(row.get('로컬성등급'))}, "
        f"접근성 {grade_word(row.get('접근성등급'))} 등급으로 "
        "기존 1급지 상권을 대체할 수 있는 차세대 만남 후보지로 평가됩니다."
    )


def build_action(row: pd.Series) -> str:
    typ = str(row.get("후보유형", ""))
    table = {
        "소비성장형": "F&B 신규 출점/팝업 후보지로 추천. 객단가 상승 추세에 맞춰 중가 콘셉트 매장 집중.",
        "2030유입형": "Z세대·MZ 타겟 콘텐츠 마케팅 거점으로 활용. 약속 장소 컬렉션 큐레이션.",
        "로컬상권형": "로컬 브랜드 협업 페어/플리마켓 운영. 프랜차이즈 의존도가 낮아 차별화 가능.",
        "접근성우수형": "광역 접근성 기반 모임 거점. 지자체 캠페인·프로모션 베이스캠프로 적합.",
        "균형형": "리스크가 낮은 안정형 후보지. 시범 사업 1차 대상지로 추천.",
    }
    return table.get(typ, "유형 미분류 — 후속 정성 분석 후 판단 권장.")


# =====================================================================
# 3. 메인
# =====================================================================
def main():
    print("[08_report] 발표용 후보지 표 생성 시작")
    top = load_top10()
    b079 = load_optional(B079_FILE)
    b076 = load_optional(B076_FILE)
    b021 = load_optional(B021_FILE)

    rows = []
    for _, r in top.iterrows():
        e1, e2, e3 = build_evidence(r, b079, b076, b021)
        rows.append(
            {
                "최종순위": r.get("최종순위"),
                "행정동코드": r.get("행정동코드"),
                "행정동명": r.get("행정동명"),
                "후보유형": r.get("후보유형"),
                "핵심근거1": e1,
                "핵심근거2": e2,
                "핵심근거3": e3,
                "발표용_해석": build_summary(r),
                "활용방안": build_action(r),
            }
        )

    out = pd.DataFrame(rows).sort_values("최종순위").reset_index(drop=True)
    cfg.save_export_safe(out, "candidate_report_table_export_safe.csv")
    print("[08_report] 완료")


if __name__ == "__main__":
    main()
