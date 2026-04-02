from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = PROJECT_ROOT / "data"
RAW_DIR = DATA_ROOT / "raw"
INTERIM_DIR = DATA_ROOT / "interim"
PROCESSED_DIR = DATA_ROOT / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# 내일 실제 경로 확인 후 수정
CAMPUS_DATA_ROOT = RAW_DIR / "campus"

DATASET_CANDIDATES = {
    "subway_station": [
        {"code": "B013", "name": "서울시 대중교통 및 지하철 1회권 승하차 데이터", "file_hint": "CP11YYMMDD.gz"},
        {"code": "B404", "name": "수도권지하철역공간데이터", "file_hint": None},
    ],
    "mobility": [
        {"code": "B075", "name": "서울시 내국인 KT 생활이동 데이터", "file_hint": None},
        {"code": "B076", "name": "서울시 행정동별 내국인 KT 생활이동 데이터", "file_hint": None},
        {"code": "B078", "name": "수도권 생활이동 데이터", "file_hint": None},
        {"code": "B082", "name": "수도권 생활이동(수단) 데이터", "file_hint": None},
    ],
    "commerce": [
        {"code": "B079", "name": "서울시민의 업종별 카드소비 데이터", "file_hint": None},
        {"code": "B042", "name": "서울시 업종별 내외국인 신한카드 매출데이터", "file_hint": "SEOUL_KOR_BLCK_YYMM_EDIT.txt"},
        {"code": "B024", "name": "서울시 블록단위 분기별 추정매출액", "file_hint": "tn_ic_ecm_blck_selng_qu_YYYY_#분기.txt"},
    ],
    "franchise": [
        {"code": "B021", "name": "서울시 식품위생업소 및 공중위생업소 데이터", "file_hint": "TBDW_BSSH_FHYG_YYYY_#.txt"},
    ],
}

COMMON_CRS = {
    "wgs84": "EPSG:4326",
    "campus_5181": "EPSG:5181",
    "campus_5186": "EPSG:5186",
    "campus_5179": "EPSG:5179",
}

BRAND_KEYWORDS = [
    "스타벅스", "투썸", "파리바게뜨", "올리브영", "메가커피",
    "이디야", "컴포즈", "빽다방", "배스킨라빈스", "던킨"
]