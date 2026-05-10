# -*- coding: utf-8 -*-
"""
09_export_for_ppt.py
PPT 발표용 요약 표 3종을 export_safe 에 CSV(+xlsx 선택) 로 저장한다.

[반출정책 준수]
- 어떤 표에도 원값/단순합계/금액/건수/인구수/업소수/정류장수가 들어가지 않는다.
- 점수, 등급, 순위, 비율, 후보유형 + 정성 텍스트만 사용.
- 반출정책상 스프레드시트 자체가 제한될 수 있으므로 최종 제출은 PPT/PNG 권장.
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


FINAL_FILE = cfg.EXPORT_SAFE_DIR / "final_meeting_spot_score_export_safe.csv"
TOP_FILE = cfg.EXPORT_SAFE_DIR / "final_top10_export_safe.csv"
REPORT_FILE = cfg.EXPORT_SAFE_DIR / "candidate_report_table_export_safe.csv"


# =====================================================================
# 1. 표 정의
# =====================================================================
def make_dataset_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "데이터셋": "B079 카드소비",
                "역할": "F&B 소비 성장성",
                "사용한_파생지표": "소비금액/건수/객단가 증가율, 소비성장점수",
                "반출_허용여부": "비율·점수만 반출",
            },
            {
                "데이터셋": "B076 KT 생활이동",
                "역할": "2030 외부 유입 성장성",
                "사용한_파생지표": "2030유입 증가율, 외부유입비율, 2030유입점수",
                "반출_허용여부": "비율·점수만 반출 (popl_cnt 원값 미반출)",
            },
            {
                "데이터셋": "B021 식품위생업소",
                "역할": "로컬성 / 프랜차이즈 의존도",
                "사용한_파생지표": "프랜차이즈비율, 로컬업소비율, 신규개업비율, 로컬성점수",
                "반출_허용여부": "비율·점수만 반출 (업소명/원목록 미반출)",
            },
            {
                "데이터셋": "B013 대중교통(메타)",
                "역할": "광역 접근성",
                "사용한_파생지표": "버스/지하철 수 표준화 가중합 → 접근성점수",
                "반출_허용여부": "점수만 반출 (정류장/역 수 원값 미반출, 거래내역 미사용)",
            },
        ]
    )


def make_process_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"단계": "01", "내용": "data/raw 인벤토리 점검 (행/컬럼/날짜 후보, 원본 행 출력 금지)"},
            {"단계": "02", "내용": "B079 → 행정동×월 집계 → 최근/이전 비교 → 소비성장점수"},
            {"단계": "03", "내용": "B076 → 2030 필터 → 외부/2030 유입 비교 → 2030유입점수"},
            {"단계": "04", "내용": "B021 → F&B/프랜차이즈/신규개업 비율 → 로컬성점수"},
            {"단계": "05", "내용": "B013 → 정류장/역 수 표준화 → 접근성점수"},
            {"단계": "06", "내용": "4개 점수 정규화 가중합 → 최종점수, 후보유형 분류"},
            {"단계": "07", "내용": "TOP10 / 산점도 / 후보유형 분포 PNG 시각화"},
            {"단계": "08", "내용": "후보지 발표용 해석문/활용방안 자동 생성"},
            {"단계": "09", "내용": "PPT 요약표(데이터/프로세스/인사이트) 저장"},
        ]
    )


def make_topn_table() -> pd.DataFrame:
    if not TOP_FILE.exists():
        print(f"  [경고] TOP10 파일 없음: {TOP_FILE.name}")
        return pd.DataFrame()
    df = pd.read_csv(TOP_FILE, encoding="utf-8-sig", dtype={"행정동코드": str})
    keep = [
        "최종순위", "행정동코드", "행정동명", "후보유형",
        "소비성장등급", "2030유입등급", "로컬성등급", "접근성등급", "최종점수",
    ]
    keep = [c for c in keep if c in df.columns]
    return df[keep].copy()


def make_insight_summary(top: pd.DataFrame) -> pd.DataFrame:
    if top.empty:
        return pd.DataFrame()
    type_counts = top["후보유형"].value_counts() if "후보유형" in top.columns else pd.Series(dtype=int)
    rows = [
        {
            "인사이트": "TOP10 평균 최종점수",
            "값": round(float(top["최종점수"].mean()), 4) if "최종점수" in top.columns else "-",
            "비고": "0~1 정규화 가중합 기준",
        },
        {
            "인사이트": "최다 후보유형",
            "값": (type_counts.index[0] if len(type_counts) else "-"),
            "비고": (f"{int(type_counts.iloc[0])}개" if len(type_counts) else "-"),
        },
        {
            "인사이트": "기존 1급지 외 신흥 후보지 비중",
            "값": "정성 검토 필요",
            "비고": "강남/홍대/성수 외 신규 등장 행정동 비율은 PPT 본문에서 별도 언급",
        },
        {
            "인사이트": "반출 안전성",
            "값": "OK",
            "비고": "원값/단순합계 컬럼 미포함 (save_export_safe 검증 통과)",
        },
    ]
    return pd.DataFrame(rows)


# =====================================================================
# 2. 저장
# =====================================================================
def try_save_xlsx(tables: dict[str, pd.DataFrame]):
    """반출정책상 xlsx 도 권장되지 않으나 내부 점검용으로 저장 시도."""
    out = cfg.EXPORT_SAFE_DIR / "ppt_summary_export_safe.xlsx"
    try:
        with pd.ExcelWriter(out, engine="openpyxl") as xw:
            for name, df in tables.items():
                # 모든 시트도 사전 검사
                cfg.check_export_safe_columns(df)
                df.to_excel(xw, sheet_name=name[:31], index=False)
        print(f"[xlsx 저장] {out.name}")
    except Exception as e:  # noqa: BLE001
        print(f"[xlsx 저장 스킵] {e}")


def main():
    print("[09_ppt] PPT 요약 표 생성 시작")

    ds = make_dataset_summary()
    proc = make_process_summary()
    topn = make_topn_table()
    ins = make_insight_summary(topn)

    cfg.save_export_safe(ds, "ppt_dataset_summary.csv")
    cfg.save_export_safe(proc, "ppt_process_summary.csv")
    cfg.save_export_safe(ins, "ppt_insight_summary.csv")

    if not topn.empty:
        cfg.save_export_safe(topn, "ppt_top10_summary.csv")

    try_save_xlsx(
        {
            "dataset": ds,
            "process": proc,
            "top10": topn,
            "insight": ins,
        }
    )
    print("[09_ppt] 완료")


if __name__ == "__main__":
    main()
