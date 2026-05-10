# -*- coding: utf-8 -*-
"""
src/*.py 를 그대로 셀 단위로 잘라 notebooks/*.ipynb 를 생성한다.

- 00_config.ipynb: %%writefile 로 notebooks/00_config.py 를 만든 뒤 import 검증.
- 01~09_*.ipynb : 동일 폴더의 00_config.py 를 동적 import 한 뒤 함수 정의 → main() 호출.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent          # meet_mid_hip_catcher/notebooks/
PROJECT = HERE.parent                            # meet_mid_hip_catcher/
SRC = PROJECT / "src"


# =====================================================================
# nbformat helpers
# =====================================================================
def make_nb(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "id": _new_id(), "metadata": {}, "source": text}


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "id": _new_id(),
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text,
    }


def write_nb(path: Path, nb: dict) -> None:
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  - {path.name}")


# =====================================================================
# .py → 셀 분해
# =====================================================================
DYNAMIC_IMPORT_BLOCK_RE = re.compile(
    r"# ---------------- 00_config 동적 로드 ----------------.*?"
    r"# -----------------------------------------------------\n",
    re.S,
)
MAIN_GUARD_RE = re.compile(r"\nif __name__ == \"__main__\":\s*\n\s*main\(\)\s*\n?$", re.S)


HELPER_IMPORT_CELL = '''\
# 00_config 동적 로드 (notebooks/, src/, 또는 같은 폴더에서 자동 탐색)
import sys, importlib.util
from pathlib import Path

_here = Path.cwd()
_search = [
    _here / "00_config.py",
    _here.parent / "src" / "00_config.py",
    _here / "src" / "00_config.py",
    _here.parent / "00_config.py",
    _here.parent / "notebooks" / "00_config.py",
]
_cfg_path = next((p for p in _search if p.exists()), None)
if _cfg_path is None:
    raise FileNotFoundError(
        "00_config.py 를 찾지 못했습니다.\\n"
        "→ 같은 폴더의 00_config.ipynb 를 먼저 실행해 주세요."
    )

_spec = importlib.util.spec_from_file_location("cfg", _cfg_path)
cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)
print(f"[cfg loaded] {_cfg_path}")
'''


def split_py_for_notebook(py_path: Path) -> tuple[str, str, str]:
    """
    .py 본문에서:
    - 모듈 docstring (제목/설명용)
    - 함수 정의 본문 (동적 import 블록 / main 가드 제거)
    - main() 호출 셀

    을 분리한다.
    """
    text = py_path.read_text(encoding="utf-8")

    # 모듈 docstring 추출 (첫 """...""" 블록)
    m = re.search(r'^# -\*-.*?\n"""(.*?)"""', text, re.S)
    docstring = m.group(1).strip() if m else py_path.stem

    # 동적 import 블록 제거
    body = DYNAMIC_IMPORT_BLOCK_RE.sub("", text)

    # main 가드 제거
    body = MAIN_GUARD_RE.sub("\n", body)

    # 본문 정리: 모듈 docstring/세이뱅도 그대로 두는 게 안전 (코드 셀에서는 docstring 형태로 무시됨)
    body = body.rstrip() + "\n"

    main_call = "main()\n"

    return docstring, body, main_call


# =====================================================================
# 00_config.ipynb (특수)
# =====================================================================
def build_config_notebook() -> dict:
    cfg_py = (SRC / "00_config.py").read_text(encoding="utf-8")

    md_intro = (
        "# 00. 공용 설정 (Config)\n"
        "\n"
        "이 노트북은 같은 폴더에 `00_config.py` 파일을 생성한다.\n"
        "이후 `01~09` 노트북들은 이 `00_config.py` 를 자동으로 import 해서 사용한다.\n"
        "\n"
        "## 반출정책 핵심\n"
        "- `cfg.save_export_safe()` 가 저장 직전 **금지 컬럼** 검사를 수행한다.\n"
        "- `cfg.save_internal_only()` 는 파일명 앞에 `DO_NOT_EXPORT_` 를 자동으로 붙인다.\n"
        "- 모든 노트북은 행 출력(`df.head()`, `print(df)`, `display(df)`)을 사용하지 않는다.\n"
        "\n"
        "## 사용법\n"
        "1. **이 노트북을 가장 먼저 실행** → `00_config.py` 가 생성된다.\n"
        "2. 이후 01~09 노트북을 순서대로 실행한다.\n"
    )

    write_cell = "%%writefile 00_config.py\n" + cfg_py

    verify_cell = (
        "# 생성된 00_config.py 가 정상 import 되는지 검증\n"
        "import importlib.util\n"
        "from pathlib import Path\n"
        "\n"
        '_cfg_path = Path.cwd() / "00_config.py"\n'
        'assert _cfg_path.exists(), "00_config.py 가 아직 만들어지지 않았습니다. 위 셀을 먼저 실행하세요."\n'
        "\n"
        '_spec = importlib.util.spec_from_file_location("cfg", _cfg_path)\n'
        "cfg = importlib.util.module_from_spec(_spec)\n"
        "_spec.loader.exec_module(cfg)\n"
        "\n"
        'print("BASE_DIR        =", cfg.BASE_DIR)\n'
        'print("RAW_DIR         =", cfg.RAW_DIR)\n'
        'print("EXPORT_SAFE_DIR =", cfg.EXPORT_SAFE_DIR)\n'
        'print("INTERNAL_DIR    =", cfg.INTERNAL_DIR)\n'
        'print("FIGURE_DIR      =", cfg.FIGURE_DIR)\n'
        'print("BANNED_COLUMNS  =", len(cfg.BANNED_EXPORT_COLUMNS), "개")\n'
    )

    return make_nb([
        md_cell(md_intro),
        code_cell(write_cell),
        code_cell(verify_cell),
    ])


# =====================================================================
# 01~09 노트북 (공통 패턴)
# =====================================================================
NOTEBOOK_TITLES = {
    "01_data_check": "01. 데이터 인벤토리 점검",
    "02_b079_consumption_score": "02. B079 카드소비 → 소비성장점수",
    "03_b076_mobility_score": "03. B076 KT 생활이동 → 2030유입점수",
    "04_b021_local_store_score": "04. B021 위생업소 → 로컬성점수",
    "05_b013_accessibility_score": "05. B013 대중교통(메타) → 접근성점수",
    "06_merge_final_score": "06. 4개 점수 병합 → 최종점수 + 후보유형",
    "07_visualize_results": "07. 발표용 시각화 (PNG 4종)",
    "08_candidate_report_table": "08. 후보지 발표용 해석문 자동 생성",
    "09_export_for_ppt": "09. PPT 발표용 요약표",
}


def build_step_notebook(stem: str) -> dict:
    py_path = SRC / f"{stem}.py"
    docstring, body, main_call = split_py_for_notebook(py_path)
    title = NOTEBOOK_TITLES.get(stem, stem)

    md_intro = (
        f"# {title}\n"
        "\n"
        "**이 노트북은 같은 폴더의 `00_config.py` 를 사용합니다.**\n"
        "먼저 `00_config.ipynb` 를 한 번 실행해 `00_config.py` 가 생성되어 있는지 확인하세요.\n"
        "\n"
        "## 단계 설명\n"
        f"```\n{docstring}\n```\n"
        "\n"
        "## 반출정책 메모\n"
        "- 원본 데이터 행을 출력하지 않는다 (`df.head()` / `print(df)` / `display(df)` 사용 금지).\n"
        "- 산출물 저장은 반드시 `cfg.save_export_safe()` / `cfg.save_internal_only()` 를 통해서만.\n"
    )

    return make_nb([
        md_cell(md_intro),
        code_cell(HELPER_IMPORT_CELL),
        code_cell(body),
        code_cell(main_call),
    ])


# =====================================================================
# 메인
# =====================================================================
def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    print("[build_notebooks] 노트북 생성 시작")
    print(f"  대상 폴더: {HERE}")

    # 00_config
    write_nb(HERE / "00_config.ipynb", build_config_notebook())

    # 01 ~ 09
    for stem in NOTEBOOK_TITLES.keys():
        write_nb(HERE / f"{stem}.ipynb", build_step_notebook(stem))

    print("[build_notebooks] 완료")


if __name__ == "__main__":
    main()
