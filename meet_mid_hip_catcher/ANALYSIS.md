# 분석 코드별 데이터 처리 설명서

> `meet_mid_hip_catcher/` 프로젝트의 각 스크립트가 **어떤 원본 데이터를** 받아서
> **어떤 전처리 → 파생지표 → 점수화** 단계를 거치는지 정리한 문서.
>
> 실행 순서·환경·반출 정책 등 운영 가이드는 [`README.md`](./README.md) 참고.

---

## 0. 분석 단위와 공통 원칙

- 모든 분석의 단위는 **행정동(행정동코드 또는 행정동명)** 으로 통일한다.
- 각 데이터셋별로 1차 점수를 만들고(02~05), 마지막에 가중합으로 **최종점수**(06)를 산출한다.
- 점수화는 모두 동일한 패턴을 따른다.
  1. 행정동별 파생지표(증가율·비율 등) 계산
  2. 각 파생지표에 **z-score 표준화** 적용
  3. 도메인 가중치로 가중합 → 점수
  4. `rank()` 로 순위, 사분위 기반으로 등급(A/B/C/D) 부여
- 반출정책상 **원값(금액·건수·인구수·업소수 등) 은 export_safe 로 절대 내보내지 않는다.**
  내부 집계는 `outputs/internal_only/DO_NOT_EXPORT_*.csv` 로만 저장한다.

---

## 1. `00_config.py` — 공용 설정과 안전장치

직접적인 분석은 하지 않지만, 모든 스크립트가 동적으로 import 해서 쓰는 인프라.

| 영역 | 내용 |
|------|------|
| 경로 | `data/raw`, `data/interim`, `outputs/internal_only`, `outputs/export_safe`, `outputs/export_safe/figures` 자동 생성 |
| 도메인 상수 | `FNB_KEYWORDS` (F&B 업종 키워드), `FRANCHISE_KEYWORDS` (프랜차이즈 의심 업소명 휴리스틱), `AGE_2030_TOKENS` (2030 연령대 표기 변형) |
| 점수 가중치 | `W_CONSUMPTION`, `W_MOBILITY`, `W_LOCALITY`, `W_FINAL` |
| 반출 금지 컬럼 | `BANNED_EXPORT_COLUMNS` 셋(약 50개): 카드이용금액계·이용건수계·popl_cnt·업소수·정류장수 등 |
| 수치 유틸 | `safe_divide`, `zscore`, `minmax`, `make_grade` (ABCD / 상중하) |
| 입출력 유틸 | `read_table_safely` (인코딩/구분자 자동 탐지), `list_raw_files` (키워드 부분일치), `find_col` (컬럼명 매칭) |
| 반출 검증 | `check_export_safe_columns` → 금지 컬럼명이 섞이면 `RuntimeError` |
| 저장 | `save_export_safe` (반출용, 검증 후 저장), `save_internal_only` (자동으로 `DO_NOT_EXPORT_` 접두어), `save_figure_export_safe` (PNG, DPI 150) |
| 시각화 | `setup_matplotlib_korean()` 으로 Windows/macOS/Linux 한글 폰트 자동 fallback |

---

## 2. `01_data_check.py` — `data/raw` 인벤토리 점검

**입력**: `data/raw/` 안의 모든 `.csv / .txt / .tsv / .dat` 파일.

**처리 로직**

1. 파일별로 앞 5,000행만 샘플 로딩 (`read_table_safely(nrows=5000)`).
   - 인코딩(`utf-8`, `utf-8-sig`, `cp949`) × 구분자(`,`, `|`, `\t`) 모두 시도하며 컬럼 2개 이상 잡히는 조합 채택.
2. 컬럼명에 `기준일자 / STDR_DE / start_dt / ymd / ym / 일자 / 년월 / PRMISN_PRMISN_DE / BIZQIT_DE` 등 **날짜 후보 키워드**가 들어 있는지 부분일치 검사 → 날짜 컬럼 존재 여부 플래그.
3. 파일 라인 카운트로 행 수 추정(헤더 1행 가정).
4. 결측치 총합(샘플 기준).

**산출물 (반출 금지)**

- `outputs/internal_only/DO_NOT_EXPORT_data_inventory.csv`
  - 컬럼: `file_name, file_size_mb, rows_estimate, n_columns, encoding, sep_repr, columns_preview, has_date_column, date_column_candidates, missing_total, read_status, read_error`

> 원본 데이터 행(row)은 절대 출력/저장하지 않는다. 메타정보만 본다.

---

## 3. `02_b079_consumption_score.py` — B079 카드소비 → 소비성장점수

**입력**: 서울시민 업종별 카드소비 (B079). 파일명 키워드 `SEOUL_SIMIN / B079 / 카드소비 / SIMIN` 으로 자동 탐색.

**주요 컬럼 매칭**

| 항목 | 후보 |
|------|------|
| 기준일자 | `기준일자, STDR_DE, STDR_YM, ymd, date` |
| 행정동코드 | `고객행정동코드, 가맹점행정동코드, ADSTRD_CD, EMD_CD, HDONG_CD` |
| 업종 | `업종대분류, 업종명, MCT_CAT_CD_NM, INDUTY_NM` |
| 금액 | `카드이용금액계, 이용금액, USE_AMT, AMT` |
| 건수 | `카드이용건수계, 이용건수, USE_CNT, CNT` |

**처리 단계**

1. **업종 필터**: 업종 텍스트에 `cfg.FNB_KEYWORDS` (음식점/카페/제과/주점/치킨/피자 등) 가 부분일치하는 행만 남김. 매칭 0건이면 전체로 fallback.
2. **월 단위 변환**: 다양한 일자 표기(`YYYYMMDD / YYYYMM / 하이픈 포함`) 를 `YYYY-MM` 으로 통일 (`to_year_month`).
3. **행정동 × 월 집계**: `금액 sum`, `건수 sum`, 그리고 `객단가 = 금액/건수` (`safe_divide`).
4. **최근/이전 기간 분할** (`split_recent_prev`):
   - 6개월 이상 → 최근 3개월 vs 직전 3개월
   - 2~5개월 → 절반씩 분할
   - 1개월 → 비교 불가, 증가율 0
5. **증가율 산출** (반출용):
   - `소비금액_증가율 = (recent − prev) / prev`
   - `소비건수_증가율 = (recent − prev) / prev`
   - `객단가_증가율 = (recent − prev) / prev`
6. **점수화**: 세 증가율을 각각 z-score 표준화한 뒤 가중합.

```text
소비성장점수 = 0.4·z(건수증가율) + 0.3·z(금액증가율) + 0.3·z(객단가증가율)
```

7. `rank(ascending=False)` 로 `소비성장순위`, 사분위로 `소비성장등급(A/B/C/D)` 부여.

**산출물**

- `outputs/internal_only/DO_NOT_EXPORT_b079_monthly_internal.csv` (행정동×월 합계, 반출 금지)
- `outputs/internal_only/DO_NOT_EXPORT_b079_growth_internal.csv` (최근/이전 평균, 반출 금지)
- `outputs/export_safe/b079_consumption_score_export_safe.csv`
  - 컬럼: `행정동코드, 소비금액_증가율, 소비건수_증가율, 객단가_증가율, 소비성장점수, 소비성장순위, 소비성장등급`
- `outputs/export_safe/figures/b079_consumption_top10.png`

---

## 4. `03_b076_mobility_score.py` — B076 KT 생활이동 → 2030유입점수

**입력**: 행정동별 KT 생활이동 (B076). 키워드 `B076 / 생활이동 / KT / MIGRATION / MIG`.

**주요 컬럼 매칭**

| 항목 | 후보 |
|------|------|
| 일자 | `start_dt, STDR_DE, 기준일자, ymd` (없으면 `arv_dt`) |
| 출발 행정동 | `start_emd, ORG_ADSTRD_CD, ORIGIN_EMD` |
| 도착 행정동 | `arv_emd, DEST_ADSTRD_CD, DEST_EMD` |
| 연령 | `agegrd_nm, agegrp_nm, 연령대, AGE` |
| 인구수 | `popl_cnt, 유동인구, POP_CNT` |

**처리 단계**

1. **2030 필터**: 연령 컬럼에 `20 / 20대 / 20s / 30 / 30대 / 30s` 등 키워드가 들어가는 행만. 텍스트 매칭이 안 되면 숫자형(20~39) 범위로 재시도.
2. **외부 유입 플래그**: `start_emd ≠ arv_emd` 인 행을 외부 유입으로 표시.
3. **도착 행정동 × 월 집계**:
   - `_inflow_2030` = (2030 필터된 데이터의 `popl_cnt` sum)
   - `_inflow_external` = (위 + 외부유입 플래그까지 적용된 sum)
4. **최근/이전 분할** (B079 와 동일한 3개월 vs 3개월 룰).
5. **파생지표**:
   - `2030유입_증가율 = (recent − prev) / prev`
   - `외부유입비율 = 외부유입_recent / 2030유입_recent`
   - `2030유입_규모지수 = z-score(2030유입_recent)` — 원값을 노출하지 않기 위해 표준화 후 사용
6. **점수화** (`W_MOBILITY` 가중치):

```text
2030유입점수 = 0.5·z(증가율) + 0.3·z(외부유입비율) + 0.2·규모지수_z
```

7. 순위·등급 부여.

**산출물**

- `outputs/internal_only/DO_NOT_EXPORT_b076_monthly_internal.csv`
- `outputs/internal_only/DO_NOT_EXPORT_b076_growth_internal.csv`
- `outputs/export_safe/b076_mobility_score_export_safe.csv`
  - 컬럼: `행정동코드, 2030유입_증가율, 외부유입비율, 2030유입점수, 2030유입순위, 2030유입등급`
- `outputs/export_safe/figures/b076_mobility_top10.png`

---

## 5. `04_b021_local_store_score.py` — B021 식품위생업소 → 로컬성점수

**입력**: 식품위생업소 / 공중위생업소 (B021). 키워드 `B021 / 위생 / FOOD / HYG / BSSH / 식품위생 / 공중위생`.

**주요 컬럼 매칭**

| 항목 | 후보 |
|------|------|
| 업소명 | `BSSH_NM, 업소명, 사업장명` |
| 업종 | `SNITAT_INDUTY_NM, 업종명, INDUTY_NM` |
| 업태 | `SNITAT_BIZCND_NM, 업태명` |
| 행정동명 | `ADSTRD_NM, 행정동명, EMD_NM` |
| 개업일자 | `PRMISN_PRMISN_DE, 허가일자, 개업일자` |
| 폐업일자 | `BIZQIT_DE, 폐업일자` |

**플래그 산정 (휴리스틱)**

1. **F&B 플래그**: 업종/업태 텍스트에 `FNB_KEYWORDS` 부분일치.
2. **프랜차이즈 플래그**: 업소명에 `FRANCHISE_KEYWORDS` (스타벅스/투썸/맥도날드/교촌/도미노/김밥천국/베스킨라빈스 ...) 부분일치 — **이름 기반 휴리스틱**임에 주의.
3. **영업 중**: 폐업일자가 결측/공백이면 영업 중으로 간주.
4. **신규개업**: 개업일자가 **최근 12개월(`NEW_OPEN_MONTHS = 12`) 이내**.

> **프랜차이즈/로컬/신규개업 카운트는 모두 F&B 업소 내부에서만 계산** 한다.
> - `_fr_cnt` = F&B ∩ 프랜차이즈
> - `_local_cnt` = F&B ∩ 비프랜차이즈
> - `_new_cnt` = F&B ∩ 신규개업

**비율 계산** (표본 부족 행정동 제외: `_fnb_cnt < 5` 제거)

```text
프랜차이즈비율 = 프랜차이즈수 / F&B수
로컬업소비율  = 로컬수      / F&B수
신규개업비율  = 신규개업수  / F&B수
```

**점수화** (`W_LOCALITY` 가중치, 비프랜차이즈성을 가장 중요시)

```text
로컬성점수 = 0.5·z(1 − 프랜차이즈비율) + 0.2·z(로컬업소비율) + 0.3·z(신규개업비율)
```

순위·등급 부여.

**산출물**

- `outputs/internal_only/DO_NOT_EXPORT_b021_dong_count_internal.csv`
- `outputs/internal_only/DO_NOT_EXPORT_b021_dong_ratio_internal.csv`
- `outputs/export_safe/b021_local_store_score_export_safe.csv`
  - 컬럼: `행정동명, 프랜차이즈비율, 로컬업소비율, 신규개업비율, 로컬성점수, 로컬성순위, 로컬성등급`
- `outputs/export_safe/figures/b021_local_score_top10.png`

> 이 점수만 식별자가 **행정동코드가 아니라 행정동명**. 06 단계에서 `dong_lookup.csv` 또는 이름 기반으로 다른 점수와 합친다.

---

## 6. `05_b013_accessibility_score.py` — B013 대중교통(메타) → 접근성점수

**입력**: 지하철역 정보 / 버스정류장 정보 메타 파일. 키워드:
- 버스: `BUS_STOP / 버스정류장 / 정류장정보 / BUSSTOP / BSTP`
- 지하철: `SUBWAY_STATION / 지하철역 / 역정보 / SUBWAY`
- **자동 제외 키워드**: `TRANS / TRADE / USE / 이용 / 거래 / 승하차 / 탑승 / RIDER / TRIP / AFC` 가 들어간 거래내역 파일은 절대 사용 안 함.

**처리 단계**

1. 각 메타 파일에서 행정동 컬럼(`ADSTRD_CD` 또는 `행정동명`) 과 ID 컬럼(`STATION_ID / STOP_ID`) 매칭.
2. ID 기준 중복 제거 후 **행정동별 정류장/역 카운트**.
3. **점수화**:
   - 둘 다 있을 때:
     ```text
     접근성점수 = 0.4·z(버스정류장 수) + 0.6·z(지하철역 수)
     ```
     (지하철이 광역 접근성에 더 결정적이라는 도메인 판단)
   - 한 쪽만 있으면 `z-score(있는 카운트)` 만으로 점수.
4. 순위·등급 부여.

**산출물**

- `outputs/internal_only/DO_NOT_EXPORT_b013_bus_count_internal.csv`
- `outputs/internal_only/DO_NOT_EXPORT_b013_subway_count_internal.csv`
- `outputs/export_safe/b013_accessibility_score_export_safe.csv`
  - 컬럼: `행정동코드, 접근성점수, 접근성순위, 접근성등급` (정류장/역 수 원값은 절대 포함 안 함)
- `outputs/export_safe/figures/b013_accessibility_top10.png`

---

## 7. `06_merge_final_score.py` — 4개 점수 병합 → 최종점수 + 후보유형

**입력**: 02~05 의 export_safe CSV 4종. (선택) `data/raw/dong_lookup.csv` 로 행정동코드 ↔ 행정동명 매핑.

**병합 로직**

1. 행정동코드 기준으로 B079·B076·B013 점수를 outer join.
2. `dong_lookup.csv` 가 있으면 행정동명 결합. 없으면 placeholder 로 코드를 이름 자리에 둠.
3. B021(로컬성)은 **행정동명 키** 라서 lookup 으로 매칭. lookup 이 없으면 코드 placeholder 와 매칭 시도.
4. 각 점수를 `cfg.minmax()` 로 0~1 정규화 → `_n` 접미사 컬럼 생성.
5. **최종점수** (`W_FINAL` 가중치):

```text
최종점수 = 0.35·소비성장점수_n + 0.30·2030유입점수_n + 0.20·로컬성점수_n + 0.15·접근성점수_n
```

6. **후보유형 분류** (`classify_type`):
   - 4개 정규화 점수 중 1위의 값과 나머지 3개 평균을 비교
   - 차이 `< 0.10` 이면 `균형형`
   - 그 외엔 1위 점수가 무엇이냐에 따라
     `소비성장형 / 2030유입형 / 로컬상권형 / 접근성우수형`

**산출물**

- `outputs/export_safe/final_meeting_spot_score_export_safe.csv`
  - 컬럼: `행정동코드, 행정동명, 소비성장점수, 소비성장등급, 2030유입점수, 2030유입등급, 로컬성점수, 로컬성등급, 접근성점수, 접근성등급, 최종점수, 최종순위, 후보유형`
- `outputs/export_safe/final_top10_export_safe.csv` (위 표 head(10))

---

## 8. `07_visualize_results.py` — 발표용 PNG 4종

`final_meeting_spot_score_export_safe.csv` 만 입력으로 사용. 모든 그래프는 **점수/순위/유형 라벨만** 표시한다(원값 노출 금지).

| PNG | 의미 |
|-----|------|
| `final_top10_bar.png` | 최종점수 TOP10 가로 막대 (행정동명 우선, 없으면 행정동코드) |
| `consumption_vs_mobility.png` | x=소비성장점수, y=2030유입점수 산점도. 색=최종점수(viridis). TOP5 행정동명 annotate. 0선 가이드라인. |
| `locality_vs_final_score.png` | x=로컬성점수, y=최종점수 산점도. 색=최종점수(plasma). TOP5 annotate. |
| `candidate_type_count.png` | 후보유형별 행정동 개수 막대(개수 텍스트 라벨 OK — 행정동 개수는 비원값). |

`cfg.setup_matplotlib_korean()` 가 호출되어 한글 깨짐 방지.

---

## 9. `08_candidate_report_table.py` — TOP10 발표용 해석 표

**입력**: `final_top10_export_safe.csv` + 02/03/04 의 export_safe 점수표.

**처리 로직** — 각 TOP10 행정동에 대해

1. `build_evidence`: B079/B076/B021 결과를 행정동코드(또는 이름) 로 lookup 해 **3가지 핵심 근거** 문장 생성.
   - 예: `"소비성장 상위 (소비건수 증가율 +12.3%, 객단가 증가율 +5.4%)"`
   - 등급은 `A→최상위 / B→상위 / C→중위 / D→하위` 로 단어 변환 (`grade_word`).
2. `build_summary`: `<이름> 은(는) 최종순위 N위의 '<유형>' 후보 행정동입니다. ...` 형식의 한 문단 자동 작성.
3. `build_action`: 후보유형별 정해진 활용방안 매핑.
   - `소비성장형` → "F&B 신규 출점/팝업, 중가 콘셉트 매장"
   - `2030유입형` → "MZ 타겟 콘텐츠 마케팅 거점"
   - `로컬상권형` → "로컬 브랜드 협업 페어/플리마켓"
   - `접근성우수형` → "광역 모임 거점, 지자체 캠페인 베이스캠프"
   - `균형형` → "리스크 낮은 시범사업 1차 대상"

**산출물**

- `outputs/export_safe/candidate_report_table_export_safe.csv`
  - 컬럼: `최종순위, 행정동코드, 행정동명, 후보유형, 핵심근거1, 핵심근거2, 핵심근거3, 발표용_해석, 활용방안`

---

## 10. `09_export_for_ppt.py` — PPT용 요약표 4종

`outputs/export_safe/` 의 결과들을 PPT에 바로 붙일 수 있도록 압축 요약.

| CSV | 시트/내용 |
|-----|----------|
| `ppt_dataset_summary.csv` | 4개 데이터셋(B079/B076/B021/B013) 각각의 역할·사용 파생지표·반출 허용 범위 |
| `ppt_process_summary.csv` | 01~09 단계별 한 줄 설명 |
| `ppt_top10_summary.csv` | TOP10 에서 `최종순위, 행정동코드, 행정동명, 후보유형, 각 등급, 최종점수` 만 추린 표 |
| `ppt_insight_summary.csv` | TOP10 평균 최종점수, 최다 후보유형, 신흥 후보지 비중(정성), 반출 안전성 |

추가로 `ppt_summary_export_safe.xlsx` 를 시도 저장(시트별 `check_export_safe_columns` 통과 시에만). 캠퍼스 정책상 xlsx 가 막히면 자동으로 스킵.

---

## 11. 점수 파이프라인 요약 (한눈 보기)

```text
B079 ─► [02] FNB 필터 → 행정동×월 sum → 최근/이전 증가율 → z(건수,금액,객단가) → 소비성장점수
B076 ─► [03] 2030 필터 → 도착동×월 sum → 증가율·외부비율·규모z → 가중합        → 2030유입점수
B021 ─► [04] FNB 플래그·프랜차이즈/신규 휴리스틱 → 행정동 비율 → 가중합         → 로컬성점수
B013 ─► [05] 정류장/역 메타 카운트(거래내역 제외) → z 가중합(0.4 버스 +0.6 지하철) → 접근성점수

         ▼ minmax 정규화 후 가중합
[06] 최종점수 = 0.35·소비_n + 0.30·2030유입_n + 0.20·로컬성_n + 0.15·접근성_n
     + 후보유형(가장 강한 강점 또는 균형형)

[07] PNG 4종 / [08] TOP10 해석표 / [09] PPT 요약표 4종
```

---

## 12. 결과 해석 시 주의사항

- **B021 의 프랜차이즈 판정은 업소명 부분일치 휴리스틱**이라 오탐/누락이 있을 수 있다. 새 브랜드가 등장하면 `FRANCHISE_KEYWORDS` 보강 필요.
- **B076 의 2030 필터**는 연령 컬럼 표기에 따라 텍스트→숫자 fallback 이 동작한다. 데이터별로 `2030 행 비율` 로그를 반드시 확인.
- **최근/이전 기간 분할**은 데이터 수집 기간에 따라 자동 조정되므로, 분석 보고서에는 실제 분할 결과(`최근 기간: [...]`)를 명시할 것.
- **B013 거래내역 사용 금지** — 자동 탐색에서도 제외하지만, 수동 지정 시(`B013_BUS_FILES`, `B013_SUBWAY_FILES`) 거래내역 파일을 넣지 않도록 주의.
- **B021 ↔ 다른 점수 결합**은 행정동명 기반이므로 `dong_lookup.csv` 가 없으면 매칭이 비어 보일 수 있다.
