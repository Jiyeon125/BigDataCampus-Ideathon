from pathlib import Path
import pandas as pd

def read_table_flexible(path: str | Path, encoding_candidates=None, sep_candidates=None, nrows=None):
    path = Path(path)
    encoding_candidates = encoding_candidates or ["utf-8", "cp949", "euc-kr"]
    sep_candidates = sep_candidates or [",", "|", "\t"]

    last_error = None
    for enc in encoding_candidates:
        for sep in sep_candidates:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, nrows=nrows)
                if df.shape[1] >= 2:
                    return df, {"encoding": enc, "sep": sep}
            except Exception as e:
                last_error = e
                continue

    raise RuntimeError(f"파일을 읽지 못했습니다: {path}\n마지막 오류: {last_error}")


def safe_make_dir(path: str | Path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path