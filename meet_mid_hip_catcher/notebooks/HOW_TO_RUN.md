# 노트북 실행 빠른 가이드

> 처음 사용자용 1페이지 요약. 자세한 내용은 프로젝트 루트의 `README.md` 참고.

---

## 1. Jupyter 켜기

분석실 PC 에서 셋 중 하나:

- **Anaconda Navigator → Jupyter Notebook 의 `Launch` 클릭**
- 또는 `Anaconda Prompt` 에서:
  ```bash
  cd C:\분석\meet_mid_hip_catcher
  jupyter notebook
  ```
- 브라우저에 Jupyter 화면이 뜨면 OK.

## 2. 폴더 구성 확인

```
meet_mid_hip_catcher/
├─ notebooks/          ← 지금 이 폴더
├─ data/raw/           ← 원본 .csv 를 여기에 둔다
└─ outputs/            ← 결과 자동 생성 (없어도 됨)
```

## 3. 노트북 실행 단축키

| 단축키 | 의미 |
|--------|------|
| `Shift + Enter` | 셀 실행 + 다음 셀로 이동 (가장 자주 씀) |
| `Ctrl + Enter`  | 셀만 실행 |
| 메뉴 `Cell → Run All` | 노트북 안 모든 셀 한꺼번에 실행 |

## 4. 실행 순서 (반드시 위에서부터)

1. **`00_config.ipynb`** ← 가장 먼저! (`%%writefile` 매직이 같은 폴더에 `00_config.py` 를 만든다)
2. `01_data_check.ipynb`
3. `02_b079_consumption_score.ipynb`
4. `03_b076_mobility_score.ipynb`
5. `04_b021_local_store_score.ipynb`
6. `05_b013_accessibility_score.ipynb`
7. `06_merge_final_score.ipynb`
8. `07_visualize_results.ipynb`
9. `08_candidate_report_table.ipynb`
10. `09_export_for_ppt.ipynb`

각 노트북마다:
- (a) 노트북 파일 클릭해서 열기
- (b) 메뉴 `Cell → Run All` 클릭 (또는 셀마다 `Shift+Enter`)
- (c) 마지막 셀까지 에러 없으면 다음 노트북으로 이동

## 5. 입력 파일명이 다르면

각 노트북 위쪽 함수 정의 셀에 다음 같은 변수가 있다:

```python
B079_FILES = None  # 예: ["SEOUL_SIMIN_01.txt"]
```

`None` 은 자동 탐색. 정확한 파일명을 알면 리스트로 적어 주면 된다.

## 6. 결과 위치

- **반출 가능**: `outputs/export_safe/` 안의 모든 파일
- **반출 금지**: `outputs/internal_only/` 안의 `DO_NOT_EXPORT_*.csv` 들 (캠퍼스 내부에서만 보고 폐기)

## 7. 자주 막히는 곳

| 에러 메시지 | 의미 / 해결 |
|-------------|-------------|
| `00_config.py 를 찾지 못했습니다` | `00_config.ipynb` 를 먼저 끝까지 돌려야 함 |
| `B0XX 파일을 자동 탐색하지 못했습니다` | `data/raw/` 에 파일이 없거나 파일명에 키워드가 안 들어감 → 노트북 상단의 `BXXX_FILES` 에 직접 적기 |
| `[반출정책 위반] ... 저장 금지 컬럼` | 안전장치가 동작한 것. 정상. 해당 컬럼을 빼야 한다는 뜻 |
| 한글이 그래프에서 깨짐 | 노트북 위쪽의 `cfg.setup_matplotlib_korean()` 셀이 먼저 실행되었는지 확인 |
| 커널 응답 없음 | 메뉴 `Kernel → Restart` 후 처음 셀부터 다시 실행 |
