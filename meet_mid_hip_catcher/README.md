# meet_mid_hip_catcher

> 서울시 빅데이터 캠퍼스 아이디어톤 프로젝트
> **차세대 만남 상권 후보지 선정** 분석 코드 베이스

> - 각 스크립트가 **어떤 데이터를 어떻게 분석하는지** 에 대한 단계별 상세 설명: [`ANALYSIS.md`](./ANALYSIS.md)
> - 캠퍼스 **반출 신청 시 함께 제출하는 데이터 분석 보고서**(산출물별 원본·처리·시각화 정리): [`EXPORT_REPORT.md`](./EXPORT_REPORT.md)
> - 이 README 는 실행/폴더 구조/반출 정책 중심.

---

## 1. 프로젝트 개요

강남·홍대·성수 같은 이미 과밀한 1급지가 아닌,

- 대중교통 접근성은 확보되어 있고
- 2030 외부 유입과 F&B 소비가 증가하며
- 프랜차이즈 비율이 과도하지 않은

새로운 약속 장소(만남 상권) **후보 행정동**을 데이터로 찾는다.

분석 단위는 모두 **행정동**으로 통일한다.

---

## 2. 사용 데이터셋

| 코드 | 데이터 | 역할 | 반출용 산출물 |
|------|--------|------|----------------|
| B079 | 서울시민 업종별 카드소비 | 소비 성장성 | 소비금액/건수/객단가 증가율, 소비성장점수/순위/등급 |
| B076 | 행정동별 KT 생활이동 | 2030 외부 유입 성장성 | 2030유입 증가율, 외부유입비율, 2030유입점수/순위/등급 |
| B021 | 식품위생업소 / 공중위생업소 | 로컬성 / 프랜차이즈 의존도 | 프랜차이즈/로컬/신규개업 비율, 로컬성점수/순위/등급 |
| B013 | 대중교통(지하철역·버스정류장 정보) | 광역 접근성 | 접근성점수/순위/등급 |

> B013 의 **개별 승하차 거래내역은 사용하지 않는다.** 메타(역/정류장 정보)만 사용한다.

---

## 3. 반출정책 대응 원칙 (가장 중요)

`outputs/export_safe/` 에는 **응용집계와 시각화**만 넣는다. 다음은 절대 반출하지 않는다.

- `df.head()`, `print(df)`, `display(df)` 등 원본 샘플 행 출력 **금지**
- 카드이용금액계 / 카드이용건수계 **원값·단순합계** 미반출
- KT `popl_cnt` **원값·단순합계** 미반출
- 업소 수 / 정류장 수 / 역 수 **원값·단순합계** 미반출
- 업소명 등 **원목록** 미반출
- 모든 그래프 라벨에서도 위 수치를 노출하지 않음

`outputs/export_safe/` 저장은 **반드시 `save_export_safe()` 를 거쳐야** 하며,
이 함수는 `BANNED_EXPORT_COLUMNS` 목록과 비교해 위반 시 `RuntimeError` 를 발생시킨다.

내부 계산용 중간값은 `outputs/internal_only/` 에만 저장하고,
파일명에 자동으로 `DO_NOT_EXPORT_` 접두어가 붙는다.

---

## 4. 폴더 구조

```
meet_mid_hip_catcher/
├─ data/
│  ├─ raw/          # 원본 (캠퍼스 내부에서만 위치)
│  ├─ interim/
│  └─ processed/
├─ outputs/
│  ├─ internal_only/    # DO_NOT_EXPORT_*.csv  (반출 금지)
│  ├─ export_safe/      # 반출 가능한 점수/순위/등급/그래프
│  └─ figures/          # 보조 그래프 저장 위치
├─ src/                 # ★ 데스크탑/로컬에서 .py 로 실행할 때 사용
│  ├─ 00_config.py
│  ├─ 01_data_check.py
│  ├─ ...
│  └─ 09_export_for_ppt.py
├─ notebooks/           # ★ 캠퍼스에서 Jupyter 만 가능할 때 사용
│  ├─ 00_config.ipynb
│  ├─ 01_data_check.ipynb
│  ├─ ...
│  ├─ 09_export_for_ppt.ipynb
│  ├─ _build_notebooks.py   # src/*.py → notebooks/*.ipynb 자동 변환 헬퍼 (선택)
│  └─ _run_all.py           # 노트북 일괄 실행 검증 헬퍼 (선택)
└─ README.md
```

> `src/*.py` 와 `notebooks/*.ipynb` 는 동일한 로직이다.
> 실행 환경에 따라 둘 중 하나만 골라 사용하면 된다.

---

## 5. 실행 환경

- Python 3.10+
- 필수: `pandas`, `numpy`, `matplotlib`, `openpyxl`(xlsx 저장 시)
- 선택: `geopandas` (이 프로젝트는 H3 미사용)

```bash
pip install pandas numpy matplotlib openpyxl
```

`matplotlib` 한글 깨짐은 `cfg.setup_matplotlib_korean()` 이 자동 처리(Windows: Malgun Gothic).

---

## 6. 실행 순서

### 6-A. 로컬/데스크탑 (Python 실행 가능)

`meet_mid_hip_catcher/` 를 작업 디렉토리로 두고 차례로 실행한다.

```bash
python src/01_data_check.py
python src/02_b079_consumption_score.py
python src/03_b076_mobility_score.py
python src/04_b021_local_store_score.py
python src/05_b013_accessibility_score.py
python src/06_merge_final_score.py
python src/07_visualize_results.py
python src/08_candidate_report_table.py
python src/09_export_for_ppt.py
```

### 6-B. 빅데이터 캠퍼스 (Jupyter Notebook 만 가능한 경우) — 처음 사용자용 상세 가이드

#### B-1. 캠퍼스 분석실에서 Jupyter 시작하기

캠퍼스 분석실 PC 에는 보통 **Anaconda Navigator** 가 설치되어 있다. 그게 가장 쉬운 길.

**[방법 A] Anaconda Navigator 로 시작 (추천)**

1. 바탕화면 또는 시작 메뉴에서 `Anaconda Navigator` 실행
2. 화면 가운데 타일 중 **`Jupyter Notebook`** (또는 `JupyterLab`) 의 `Launch` 버튼 클릭
3. 브라우저(크롬/엣지)에 Jupyter 화면이 열린다 (URL 은 `http://localhost:8888/...` 형태)

**[방법 B] 명령창에서 직접 시작**

윈도우 시작 메뉴에서 `Anaconda Prompt` 를 열고:

```bash
cd C:\경로\meet_mid_hip_catcher
jupyter notebook
```

엔터를 치면 브라우저가 자동으로 열린다.

#### B-2. 프로젝트 폴더 구조 만들기

캠퍼스 PC 에 다음과 같이 파일을 둔다 (어떤 드라이브든 OK).

```
C:\분석\meet_mid_hip_catcher\         ← 임의의 작업 폴더
├─ notebooks\                          ← .ipynb 10개 통째로 업로드
├─ data\
│  └─ raw\                             ← 원본 데이터(.csv) 여기에
└─ outputs\                            ← 비어 있어도 됨 (노트북이 자동 생성)
```

**최소 준비물**

- `notebooks/` 안의 `.ipynb` 10개 (필수)
- 분석할 원본 데이터를 `data/raw/` 안에 둔다
- (선택) 행정동코드 ↔ 행정동명 매핑이 있으면 `data/raw/dong_lookup.csv` 로 둔다

#### B-3. 노트북 실행 — 클릭/단축키 하나씩

##### Step 1. 첫 노트북 `00_config.ipynb` 열기

1. Jupyter 화면(파일 브라우저) 에서 `notebooks` 폴더로 이동 (폴더 이름을 클릭)
2. `00_config.ipynb` 파일 이름을 클릭 → 새 탭에 노트북이 열린다

##### Step 2. 셀 실행 방법

**Jupyter 의 핵심 단축키:**

| 단축키 | 기능 |
|--------|------|
| `Shift + Enter` | 현재 셀 실행 + 다음 셀로 이동 (가장 많이 씀) |
| `Ctrl + Enter` | 현재 셀만 실행 |
| `Alt + Enter`  | 현재 셀 실행 + 아래에 새 셀 추가 |

마우스로는: 셀을 클릭한 뒤 상단 툴바의 **▶(Run)** 버튼.

##### Step 3. `00_config.ipynb` 안에서 차례대로 실행

`00_config.ipynb` 는 셀이 3개다.

1. 첫 번째 셀(설명) 클릭 → `Shift + Enter`
2. 두 번째 셀(`%%writefile 00_config.py` 로 시작) → `Shift + Enter`
   → 같은 폴더에 `00_config.py` 가 만들어진다 (출력에 `Writing 00_config.py` 표시)
3. 세 번째 셀(import 검증) → `Shift + Enter`
   → `BASE_DIR=...`, `BANNED_COLUMNS=51 개` 같은 출력이 뜨면 성공

> **또는 한 번에 다 돌리려면**: 상단 메뉴 **`Cell → Run All`** (JupyterLab 은 **`Run → Run All Cells`**) 클릭.

##### Step 4. `01_data_check.ipynb` 열고 실행

1. 브라우저 탭의 Jupyter 파일 브라우저로 돌아가서 `01_data_check.ipynb` 클릭
2. 메뉴 **`Cell → Run All`** 클릭 (또는 셀별로 `Shift+Enter`)
3. `data/raw/` 안의 파일을 점검한 결과가 출력에 뜬다

##### Step 5. 02 → 03 → … → 09 까지 같은 방식으로

| 순서 | 노트북 | 결과로 만들어지는 핵심 파일 |
|------|--------|------------------------------|
| 1 | `00_config.ipynb` | `notebooks/00_config.py` (헬퍼) |
| 2 | `01_data_check.ipynb` | `outputs/internal_only/DO_NOT_EXPORT_data_inventory.csv` |
| 3 | `02_b079_consumption_score.ipynb` | `outputs/export_safe/b079_consumption_score_export_safe.csv` |
| 4 | `03_b076_mobility_score.ipynb` | `outputs/export_safe/b076_mobility_score_export_safe.csv` |
| 5 | `04_b021_local_store_score.ipynb` | `outputs/export_safe/b021_local_store_score_export_safe.csv` |
| 6 | `05_b013_accessibility_score.ipynb` | `outputs/export_safe/b013_accessibility_score_export_safe.csv` |
| 7 | `06_merge_final_score.ipynb` | `outputs/export_safe/final_meeting_spot_score_export_safe.csv`, `final_top10_export_safe.csv` |
| 8 | `07_visualize_results.ipynb` | `outputs/export_safe/figures/*.png` (4종) |
| 9 | `08_candidate_report_table.ipynb` | `outputs/export_safe/candidate_report_table_export_safe.csv` |
| 10 | `09_export_for_ppt.ipynb` | `outputs/export_safe/ppt_*.csv` (요약표) |

각 노트북은 **마지막 셀까지 실행 → 다음 노트북 열기** 의 반복이다.

> **노트북별 입력 파일 경로를 직접 지정하고 싶다면**: 각 노트북의 함수 정의 셀 맨 위에 있는
> `B079_FILES = None`, `B076_FILES = None` 같은 변수에 `["실제파일명.csv"]` 식으로 적어 주면 된다.
> 비워두면 `data/raw` 에서 키워드(`B079`, `SEOUL_SIMIN`, `B076`, `생활이동` …)로 자동 탐색.

#### B-4. 자주 만나는 에러 & 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| `00_config.py 를 찾지 못했습니다` | `00_config.ipynb` 를 안 돌렸음 | `00_config.ipynb` 의 두 번째 셀(%%writefile)부터 다시 실행 |
| `B079 파일을 자동 탐색하지 못했습니다` | `data/raw` 가 비어 있거나 파일명이 키워드와 다름 | 파일을 `data/raw/` 에 두거나, 노트북 상단의 `B079_FILES = ["내파일명.csv"]` 로 직접 지정 |
| `반출정책 위반 ... 저장 금지 컬럼이 포함` | `save_export_safe()` 의 안전장치가 발동 | 정상 동작이다. 그 컬럼은 빼고 다시 점수만 남겨야 한다는 뜻 |
| 한글이 그래프에서 깨짐(□□□) | 폰트 미설정 | `cfg.setup_matplotlib_korean()` 이 호출되었는지 확인 (07 노트북 첫 코드 셀) |
| 커널이 응답 없음 | 데이터가 너무 큼 | 메뉴 `Kernel → Restart` 후 다시 시도, 필요시 `nrows=` 옵션으로 샘플링 |

#### B-5. 결과물 회수

분석이 끝나면 다음 폴더만 살펴보면 된다.

```
outputs/
├─ export_safe/      ← 반출 가능 (캠퍼스 외부로 가져갈 수 있는 파일)
│  ├─ *.csv          ← 점수/순위/등급/비율
│  └─ figures/*.png  ← 그래프
└─ internal_only/    ← 반출 금지 (캠퍼스 내부에서만 보고 폐기)
   └─ DO_NOT_EXPORT_*.csv
```

캠퍼스 데이터 반출 신청 시에는 **`outputs/export_safe/` 안의 파일만** 신청 목록에 넣는다.

### 6-C. 공통 사용자 설정

각 스크립트/노트북 상단에 `B079_FILES`, `B076_FILES`, `B021_FILES`, `B013_BUS_FILES`, `B013_SUBWAY_FILES` 변수가 있어
실제 파일명이 다르면 사용자가 직접 지정할 수 있다. 비워 두면 `data/raw` 에서 키워드 자동 탐색.

행정동코드 ↔ 행정동명 매핑이 필요하면
`data/raw/dong_lookup.csv` 에 `행정동코드, 행정동명` 두 컬럼만 있는 CSV 를 두면 된다.

### 6-C-1. 원본 데이터 확장자 처리 (캠퍼스 원본은 보통 확장자가 없음)

캠퍼스에서 신청한 원본 데이터는 `B079_SEOUL_SIMIN_202401` 처럼 애매하게 떨어지는 경우가 많다.
파일 자체는 텍스트(쉼표/파이프/탭 구분) 라 그대로 사용 가능하지만,
`data/raw` 의 자동 탐색은 기본적으로 `.csv / .txt / .tsv / .dat` 확장자만 인식한다.

#### 방법 A — 확장자만 일괄로 `.txt` 로 변경 (권장, 가장 빠름)

```text
data/raw/
├─ B079_SEOUL_SIMIN_202401          ← 인식 안 됨
└─ ...
                ▼ 이름 바꾸기
├─ B079_SEOUL_SIMIN_202401.txt      ← OK
└─ ...
```

→ 인코딩(`utf-8 / utf-8-sig / cp949`) 과 구분자(`,` / `|` / `\t`) 는 코드가 자동 탐지하므로 **내용 변환 불필요**.

#### 방법 B — 각 스크립트의 `XXX_FILES` 에 직접 지정 (이름 못 바꿀 때)

확장자 없는 파일명을 그대로 적어 주면 자동 탐색을 건너뛰고 즉시 로드된다.

```python
# 예: src/02_b079_consumption_score.py 또는 02 노트북 상단
B079_FILES = ["B079_SEOUL_SIMIN_202401", "B079_SEOUL_SIMIN_202402"]
```

02 (B079), 03 (B076), 04 (B021), 05 (B013 버스/지하철) 다섯 군데 모두 동일 패턴.

#### 방법 C — 자동 폴백 탐색기 사용 (확장자 없는 파일 자동 인식)

`00_config.py` 에 예비용 탐색 함수가 들어 있다.

| 함수 | 동작 |
|------|------|
| `cfg.list_raw_files(patterns)` | 기본. `.csv / .txt / .tsv / .dat` 만 잡는다. |
| `cfg.list_raw_files_loose(patterns, include_no_extension=True)` | 확장자 없는 파일도 포함. 명백한 바이너리(zip / pdf / xlsx / 이미지 / 동영상 등)와 시스템 파일(.DS_Store / Thumbs.db / .gitkeep) 은 자동 제외. |
| `cfg.find_raw_files_auto(patterns)` | 엄격 탐색 0건이면 자동으로 `list_raw_files_loose` 로 폴백. |

각 스크립트/노트북의 `resolve_input_files()` 안에서 호출을 한 줄만 바꾸면 폴백이 켜진다.

```python
# 변경 전
files = cfg.list_raw_files(patterns=B079_FILE_PATTERNS)
# 변경 후 (확장자 없는 파일도 자동 인식)
files = cfg.find_raw_files_auto(patterns=B079_FILE_PATTERNS)
```

#### 방법 D — 캠퍼스에서 잡힌 파일 목록 미리 확인

탐색이 의도대로 동작하는지 점검하고 싶을 때, 새 셀에서:

```python
for p in cfg.list_raw_files_loose():
    print(p.name, "→", p.suffix or "(확장자 없음)")
```

> 추가 확장자(예: `.psv`, `.csv.gz`) 가 섞여 있다면 `cfg.list_raw_files_loose(extra_extensions=["psv", "csv.gz"])` 로 허용할 수 있다.
> 또한 구분자가 세미콜론(`;`) 인 캠퍼스 데이터를 만났다면 `00_config.py` 의 `read_table_safely()` 의 `sep_candidates` 에 `";"` 를 추가해 두면 된다.

### 6-D. 노트북 재생성 (선택)

`src/*.py` 를 수정한 뒤 노트북에 반영하고 싶다면:

```bash
python notebooks/_build_notebooks.py
```

전체 노트북을 한 번에 검증하고 싶다면:

```bash
python notebooks/_run_all.py
```

---

## 7. export_safe vs internal_only

| 구분 | export_safe | internal_only |
|------|-------------|----------------|
| 저장 위치 | `outputs/export_safe/` | `outputs/internal_only/` |
| 파일명 | 자유 (`*_export_safe.csv`) | 자동 `DO_NOT_EXPORT_*.csv` |
| 컬럼 검사 | `save_export_safe()` 가 금지 컬럼 차단 | 없음 (원값 허용) |
| 반출 가능 여부 | **반출 가능** | **반출 금지 (캠퍼스 외부로 반입 X)** |
| 들어가는 것 | 비율, 순위, 등급, 점수, 후보유형, PNG | 행정동×월 집계, 카운트 등 중간값 |

---

## 8. 반출 시 주의사항

1. 반출 직전 `outputs/export_safe/` 의 모든 CSV 의 컬럼명을 다시 한 번 육안 확인.
2. PNG 그래프 안에 숫자 레이블이 들어간 경우, 그 숫자가 **점수/비율/순위**인지 확인.
   원값(금액·건수·인구수·업소수)이면 라벨을 제거.
3. xlsx 는 시트별 컬럼이 모두 안전한지 `cfg.check_export_safe_columns()` 가 통과한 상태인지 확인.
   캠퍼스 정책상 표 형태 반출이 제한될 경우 PPT/PNG 위주로 제출.
4. `internal_only/` 의 어떤 파일도 **외부로 반출하지 않는다.**

---

## 9. 최종 산출물 목록 (export_safe)

```
outputs/export_safe/
├─ b079_consumption_score_export_safe.csv
├─ b076_mobility_score_export_safe.csv
├─ b021_local_store_score_export_safe.csv
├─ b013_accessibility_score_export_safe.csv
├─ final_meeting_spot_score_export_safe.csv
├─ final_top10_export_safe.csv
├─ candidate_report_table_export_safe.csv
├─ ppt_dataset_summary.csv
├─ ppt_process_summary.csv
├─ ppt_top10_summary.csv
├─ ppt_insight_summary.csv
└─ figures/
   ├─ b079_consumption_top10.png
   ├─ b076_mobility_top10.png
   ├─ b021_local_score_top10.png
   ├─ b013_accessibility_top10.png
   ├─ final_top10_bar.png
   ├─ consumption_vs_mobility.png
   ├─ locality_vs_final_score.png
   └─ candidate_type_count.png
```
