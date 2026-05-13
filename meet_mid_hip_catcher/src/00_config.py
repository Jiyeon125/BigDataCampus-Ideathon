# -*- coding: utf-8 -*-
"""
프로젝트 공용 설정 및 유틸리티 모듈.

- 빅데이터 캠퍼스 반출정책에 맞춰
  outputs/export_safe 에 저장되는 산출물에는 원값/단순합계 계열 컬럼이
  들어가지 않도록 save_export_safe() 에서 사전 검사를 수행한다.

- 파일명이 "00_..." 처럼 숫자로 시작하므로
  다른 스크립트에서는 importlib 로 동적 로드한다.
  (각 스크립트 상단에 동적 import 헬퍼가 들어 있음)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# =====================================================================
# 1. 경로 설정
# =====================================================================

# 이 파일(00_config.py)은 src/ 안에 있다.
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent  # meet_mid_hip_catcher/

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = BASE_DIR / "outputs"
INTERNAL_DIR = OUTPUT_DIR / "internal_only"
EXPORT_SAFE_DIR = OUTPUT_DIR / "export_safe"
FIGURE_DIR = EXPORT_SAFE_DIR / "figures"
FIGURE_DIR_ALT = OUTPUT_DIR / "figures"

# 폴더가 없으면 생성 (데이터 폴더는 사용자가 직접 채우는 raw 만 보장)
for _p in [
    DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR,
    OUTPUT_DIR, INTERNAL_DIR, EXPORT_SAFE_DIR,
    FIGURE_DIR, FIGURE_DIR_ALT,
]:
    _p.mkdir(parents=True, exist_ok=True)


# =====================================================================
# 2. 도메인 상수
# =====================================================================

# F&B 업종 키워드 (B021 / B079 공용)
FNB_KEYWORDS = [
    "음식점", "일반음식", "휴게음식", "음식",
    "카페", "커피", "다방",
    "제과", "베이커리", "빵",
    "주점", "호프", "술집", "바", "펍",
    "분식", "한식", "양식", "중식", "일식",
    "패스트푸드", "치킨", "피자", "버거",
    "디저트", "아이스크림", "도넛",
    "식당", "레스토랑",
]

# 프랜차이즈 의심 키워드 (업소명 부분일치 기반 휴리스틱)
FRANCHISE_KEYWORDS = [
    # 카페
    "스타벅스", "투썸", "이디야", "폴바셋", "빽다방",
    "메가커피", "메가엠지씨", "컴포즈", "할리스", "커피빈",
    "탐앤탐스", "엔제리너스", "더벤티", "공차", "쥬씨",
    # 패스트푸드/햄버거
    "맥도날드", "버거킹", "롯데리아", "맘스터치", "노브랜드버거",
    "kfc", "케이에프씨", "써브웨이",
    # 치킨
    "교촌", "bbq", "비비큐", "굽네", "처갓집", "페리카나",
    "호식이", "네네", "자담치킨", "또래오래", "푸라닭", "후라이드참잘하는집",
    # 피자
    "도미노", "피자헛", "미스터피자", "파파존스", "피자스쿨", "피자마루",
    # 분식/도시락/한식
    "김밥천국", "김가네", "바르다김선생", "한솥", "본도시락",
    "본죽", "죽이야기", "이바돔", "놀부", "원할머니", "명륜진사갈비",
    # 패밀리/뷔페
    "빕스", "애슐리", "아웃백", "매드포갈릭", "더플레이스",
    # 디저트/아이스크림
    "베스킨라빈스", "배스킨라빈스", "던킨", "크리스피크림",
    # 주점
    "역전할머니", "감성타코", "하이드", "투다리",
]

# 2030 연령대 필터 (다양한 표기에 대응)
AGE_2030_TOKENS = [
    "20", "20대", "20s", "twenty",
    "30", "30대", "30s", "thirty",
]

# 외부유입 관련 장소 타입 (B076 start_arv_place_type)
HOME_TOKENS = ["주거", "집", "home", "거주"]


# =====================================================================
# 3. 점수 가중치
# =====================================================================

# 02_b079 소비성장점수 내부 가중치
W_CONSUMPTION = {
    "count_growth": 0.4,   # 소비건수 증가율
    "amount_growth": 0.3,  # 소비금액 증가율
    "ticket_growth": 0.3,  # 객단가 증가율
}

# 03_b076 2030유입점수 내부 가중치
W_MOBILITY = {
    "growth": 0.5,    # 2030 유입 증가율
    "ratio": 0.3,     # 외부유입 비율
    "scale": 0.2,     # 2030 유입 규모지수(표준화 후)
}

# 04_b021 로컬성점수 내부 가중치
# 로컬성 = (1 - 프랜차이즈비율) 가중 + 신규개업비율 가중
W_LOCALITY = {
    "non_franchise": 0.5,
    "local_ratio": 0.2,
    "new_open": 0.3,
}

# 06 최종점수 가중치
W_FINAL = {
    "consumption": 0.35,
    "mobility": 0.30,
    "locality": 0.20,
    "accessibility": 0.15,
}


# =====================================================================
# 4. 반출 금지 컬럼 (export_safe 저장 시 검사)
# =====================================================================

# 정확 일치 기준의 금지 컬럼명.
# (소비건수_증가율 등 파생지표는 차단되면 안 되므로 부분일치는 사용하지 않는다.)
BANNED_EXPORT_COLUMNS = {
    # B079 카드소비
    "amount", "total_amount", "recent_amount", "prev_amount",
    "card_amount", "amount_sum",
    "카드이용금액계", "카드이용금액", "이용금액",
    "count", "total_count", "recent_count", "prev_count",
    "card_count", "count_sum",
    "카드이용건수계", "카드이용건수", "이용건수",
    "ticket_amount", "객단가",
    # B076 생활이동
    "popl_cnt", "total_inflow", "inflow_count",
    "inflow_2030", "inflow_external", "inflow_total",
    "유입량", "유입수", "총유입량", "외부유입량", "전체유입량",
    # B021 위생업소
    "store_count", "fnb_store_count", "franchise_store_count",
    "fnb_count", "franchise_count", "new_open_count",
    "업소수", "업소_수", "프랜차이즈_수", "프랜차이즈수",
    "신규개업수", "신규개업_수",
    # B013 대중교통
    "bus_stop_count", "subway_station_count",
    "stop_count", "station_count",
    "정류장수", "정류장_수", "역수", "역_수",
}


# =====================================================================
# 5. 수치 계산 유틸
# =====================================================================

def safe_divide(numerator, denominator, default=0.0):
    """0 나눗셈 방지. Series/Scalar 모두 처리."""
    num = pd.Series(numerator) if not isinstance(numerator, pd.Series) else numerator
    den = pd.Series(denominator) if not isinstance(denominator, pd.Series) else denominator
    out = num / den.replace(0, np.nan)
    out = out.replace([np.inf, -np.inf], np.nan).fillna(default)
    if len(out) == 1 and not isinstance(numerator, pd.Series):
        return float(out.iloc[0])
    return out


def zscore(series: pd.Series) -> pd.Series:
    """Z-score 정규화. 표준편차가 0이면 0 반환."""
    s = pd.to_numeric(series, errors="coerce")
    mu = s.mean()
    sd = s.std(ddof=0)
    if sd is None or pd.isna(sd) or sd == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mu) / sd


def minmax(series: pd.Series) -> pd.Series:
    """0~1 min-max 정규화."""
    s = pd.to_numeric(series, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


def make_grade(score: pd.Series, scheme: str = "ABCD") -> pd.Series:
    """
    점수를 등급으로 변환.
    - scheme="ABCD": 상위 25/50/75% → A/B/C/D
    - scheme="HML": 상위 1/3, 중간 1/3, 하위 1/3 → 상/중/하
    """
    s = pd.to_numeric(score, errors="coerce")
    if s.isna().all():
        return pd.Series(["-"] * len(s), index=s.index)

    if scheme == "HML":
        q1, q2 = s.quantile(1 / 3), s.quantile(2 / 3)
        return s.apply(
            lambda v: "상" if pd.notna(v) and v >= q2
            else ("중" if pd.notna(v) and v >= q1 else "하")
        )
    # 기본: A/B/C/D
    q25, q50, q75 = s.quantile(0.25), s.quantile(0.50), s.quantile(0.75)

    def _to_grade(v):
        if pd.isna(v):
            return "-"
        if v >= q75:
            return "A"
        if v >= q50:
            return "B"
        if v >= q25:
            return "C"
        return "D"

    return s.apply(_to_grade)


# =====================================================================
# 6. 파일 입출력 유틸
# =====================================================================

def find_col(df: pd.DataFrame, candidates, required: bool = True):
    """
    DataFrame 에서 후보 컬럼명 중 첫 번째로 존재하는 컬럼명을 반환.

    매칭 우선순위:
        1) 정확 일치 (대소문자 무시)
        2) 부분 일치 (대소문자 무시)
    """
    if df is None or len(df.columns) == 0:
        if required:
            raise KeyError(f"DataFrame 이 비어 있어 컬럼 매칭 불가: {candidates}")
        return None

    col_map = {str(c).strip(): str(c) for c in df.columns}
    lower_map = {k.lower(): v for k, v in col_map.items()}

    for cand in candidates:
        key = str(cand).strip()
        # 정확 일치
        if key in col_map:
            return col_map[key]
        if key.lower() in lower_map:
            return lower_map[key.lower()]

    for cand in candidates:
        key = str(cand).strip().lower()
        for orig_lower, orig in lower_map.items():
            if key and key in orig_lower:
                return orig

    if required:
        raise KeyError(
            f"필요한 컬럼을 찾지 못했습니다. 후보={candidates} / 실제 컬럼 일부={list(df.columns)[:10]}"
        )
    return None


def read_table_safely(
    path,
    encoding_candidates=("utf-8", "utf-8-sig", "cp949"),
    sep_candidates=(",", "|", "\t"),
    nrows=None,
    dtype=None,
):
    """
    인코딩과 구분자를 순차적으로 시도하며 표 형태 파일을 읽는다.
    - 원본 데이터의 행 내용을 출력하지 않는다.
    - 성공 시 (df, meta) 반환. meta = {"encoding": ..., "sep": ...}
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {p}")

    last_error = None
    for enc in encoding_candidates:
        for sep in sep_candidates:
            try:
                df = pd.read_csv(
                    p,
                    encoding=enc,
                    sep=sep,
                    nrows=nrows,
                    dtype=dtype,
                    low_memory=False,
                    on_bad_lines="skip",
                )
                # 한 컬럼만 잡힌 경우는 구분자가 잘못 잡힌 것으로 간주
                if df.shape[1] >= 2:
                    return df, {"encoding": enc, "sep": sep}
            except Exception as e:  # noqa: BLE001
                last_error = e
                continue

    raise RuntimeError(
        f"파일을 읽지 못했습니다: {p.name}\n마지막 오류: {last_error}"
    )


def list_raw_files(patterns=None):
    """data/raw 아래 파일 목록을 반환. patterns 가 주어지면 부분일치 필터."""
    files = [p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix.lower() in {
        ".csv", ".txt", ".tsv", ".dat",
    }]
    if patterns:
        out = []
        for p in files:
            name = p.name.lower()
            if any(pat.lower() in name for pat in patterns):
                out.append(p)
        return out
    return files


# 확장자 없이 들어오는 캠퍼스 원본 데이터(예: B079_SEOUL_SIMIN_202401) 도
# 자동 탐색되도록 한 폴백 버전. list_raw_files() 가 0건이면 이걸로 재시도하면 된다.
_BINARY_EXT_SKIP = {
    ".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz",
    ".pdf", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".pptx", ".ppt", ".hwp", ".hwpx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".m4a",
    ".db", ".sqlite", ".parquet", ".feather", ".pkl", ".pickle",
    ".exe", ".dll", ".so", ".dylib", ".bin",
}
_SYSTEM_NAME_SKIP = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"}


def list_raw_files_loose(
    patterns=None,
    include_no_extension: bool = True,
    extra_extensions: list[str] | None = None,
):
    """
    list_raw_files() 의 예비용 폴백.

    - 캠퍼스에서 받은 원본이 확장자 없이 들어오는 경우(예: ``B079_SEOUL_SIMIN_202401``) 대응.
    - 기본 인식 확장자: ``.csv``, ``.txt``, ``.tsv``, ``.dat`` + (옵션) 확장자 없는 파일.
    - 명백한 비-텍스트 파일(zip / pdf / xlsx / 이미지 / 동영상 / 바이너리)은 제외.
    - 시스템 파일(.DS_Store / Thumbs.db / desktop.ini / .gitkeep) 도 제외.
    - patterns 가 주어지면 부분일치(대소문자 무시) 필터.
    - extra_extensions 로 추가 확장자 허용(예: ``["psv", "csv.gz"]``).

    실제 파일 내용 파싱은 ``read_table_safely()`` 가 인코딩/구분자를 자동 탐지하므로
    여기서는 “읽기 후보로 통과시킬지” 만 판단한다.
    """
    accepted_ext = {".csv", ".txt", ".tsv", ".dat"}
    if extra_extensions:
        for e in extra_extensions:
            e = str(e).strip().lower()
            if not e:
                continue
            if not e.startswith("."):
                e = "." + e
            accepted_ext.add(e)

    candidates = []
    for p in RAW_DIR.rglob("*"):
        if not p.is_file():
            continue
        if p.name in _SYSTEM_NAME_SKIP:
            continue
        suf = p.suffix.lower()
        if suf in _BINARY_EXT_SKIP:
            continue
        if suf in accepted_ext:
            candidates.append(p)
            continue
        if include_no_extension and suf == "":
            candidates.append(p)
            continue

    if patterns:
        out = []
        for p in candidates:
            name = p.name.lower()
            if any(str(pat).lower() in name for pat in patterns):
                out.append(p)
        return out
    return candidates


def find_raw_files_auto(patterns=None):
    """
    list_raw_files() → 0건이면 자동으로 list_raw_files_loose() 로 폴백.

    02~05 스크립트의 ``resolve_input_files()`` 가 ``list_raw_files`` 대신
    이걸 호출하도록 바꿔도 동작은 동일하다(엄격 모드가 비면 관대 모드로).
    """
    primary = list_raw_files(patterns=patterns)
    if primary:
        return primary
    fallback = list_raw_files_loose(patterns=patterns)
    if fallback:
        print(
            "[list_raw_files] 엄격 탐색 0건 → 확장자 없는 파일 포함 폴백으로 "
            f"{len(fallback)}건 탐지"
        )
    return fallback


# =====================================================================
# 7. 반출 안전성 검사 + 저장
# =====================================================================

def check_export_safe_columns(df: pd.DataFrame, banned=None):
    """
    DataFrame 컬럼이 반출 금지 컬럼명과 정확히 겹치는지 검사.
    겹치면 RuntimeError 발생.
    """
    banned = set(banned) if banned is not None else BANNED_EXPORT_COLUMNS
    cols = {str(c).strip() for c in df.columns}
    bad = sorted(cols & banned)
    if bad:
        raise RuntimeError(
            "[반출정책 위반] export_safe 에 저장 금지 컬럼이 포함되어 있습니다: "
            f"{bad}\n"
            "→ 원값/단순합계는 internal_only 로 옮기고, "
            "비율/순위/등급/점수만 남겨주세요."
        )


def save_export_safe(df: pd.DataFrame, filename: str, index: bool = False) -> Path:
    """
    outputs/export_safe 아래 CSV 로 저장. 저장 전 금지 컬럼 검사.
    """
    EXPORT_SAFE_DIR.mkdir(parents=True, exist_ok=True)
    check_export_safe_columns(df)
    out_path = EXPORT_SAFE_DIR / filename
    df.to_csv(out_path, index=index, encoding="utf-8-sig")
    print(f"[export_safe 저장] {out_path.name}  / shape={df.shape}")
    return out_path


def save_internal_only(df: pd.DataFrame, filename: str, index: bool = False) -> Path:
    """
    outputs/internal_only 아래에 저장. 파일명 앞에 DO_NOT_EXPORT_ 자동 부여.
    """
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    name = filename
    if not name.startswith("DO_NOT_EXPORT_"):
        name = f"DO_NOT_EXPORT_{name}"
    out_path = INTERNAL_DIR / name
    df.to_csv(out_path, index=index, encoding="utf-8-sig")
    print(f"[internal_only 저장] {out_path.name}  / shape={df.shape}")
    return out_path


def save_figure_export_safe(fig, filename: str) -> Path:
    """그래프를 outputs/export_safe/figures 에 PNG 저장."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURE_DIR / filename
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[figure 저장] {out_path.name}")
    return out_path


# =====================================================================
# 8. matplotlib 한글 폰트 설정 (Windows 우선)
# =====================================================================

def setup_matplotlib_korean():
    """그래프 한글 깨짐 방지. 환경에 따라 사용 가능한 폰트로 fallback."""
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # 환경별 후보 폰트
    candidates = [
        "Malgun Gothic",      # Windows
        "AppleGothic",        # macOS
        "NanumGothic",        # Linux 일반
        "Noto Sans CJK KR",   # Linux Noto
        "Arial Unicode MS",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates if c in available), None)
    if chosen:
        plt.rcParams["font.family"] = chosen
    plt.rcParams["axes.unicode_minus"] = False


# =====================================================================
# 9. 디버그용 메인
# =====================================================================

if __name__ == "__main__":
    print("[CONFIG] BASE_DIR =", BASE_DIR)
    print("[CONFIG] RAW_DIR =", RAW_DIR)
    print("[CONFIG] EXPORT_SAFE_DIR =", EXPORT_SAFE_DIR)
    print("[CONFIG] INTERNAL_DIR =", INTERNAL_DIR)
    print("[CONFIG] FIGURE_DIR =", FIGURE_DIR)
    print("[CONFIG] 금지 컬럼 수 =", len(BANNED_EXPORT_COLUMNS))
