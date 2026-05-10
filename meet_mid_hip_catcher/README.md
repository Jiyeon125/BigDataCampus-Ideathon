# meet_mid_hip_catcher

> 서울시 빅데이터 캠퍼스 아이디어톤 프로젝트
> **차세대 만남 상권 후보지 선정** 분석 코드 베이스

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

### 6-B. Jupyter Notebook 만 가능한 경우

`notebooks/` 안에서 다음 순서로 노트북을 연다. **반드시 `00_config.ipynb` 부터** 실행한다.

1. `00_config.ipynb` ← **가장 먼저 실행** (`%%writefile` 매직으로 같은 폴더에 `00_config.py` 를 자동 생성)
2. `01_data_check.ipynb`
3. `02_b079_consumption_score.ipynb`
4. `03_b076_mobility_score.ipynb`
5. `04_b021_local_store_score.ipynb`
6. `05_b013_accessibility_score.ipynb`
7. `06_merge_final_score.ipynb`
8. `07_visualize_results.ipynb`
9. `08_candidate_report_table.ipynb`
10. `09_export_for_ppt.ipynb`

각 노트북은 같은 폴더의 `00_config.py` 를 자동 탐색해 import 한다.
캠퍼스 환경에서는 `notebooks/` 폴더 통째로 업로드하고 `data/` `outputs/` 폴더만 추가로 만들면 된다.

### 6-C. 공통 사용자 설정

각 스크립트/노트북 상단에 `B079_FILES`, `B076_FILES`, `B021_FILES`, `B013_BUS_FILES`, `B013_SUBWAY_FILES` 변수가 있어
실제 파일명이 다르면 사용자가 직접 지정할 수 있다. 비워 두면 `data/raw` 에서 키워드 자동 탐색.

행정동코드 ↔ 행정동명 매핑이 필요하면
`data/raw/dong_lookup.csv` 에 `행정동코드, 행정동명` 두 컬럼만 있는 CSV 를 두면 된다.

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
