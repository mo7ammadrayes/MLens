from pandas.api.types import is_numeric_dtype
from pathlib import Path
from io import BytesIO
from io import BytesIO

import pandas as pd
from backend.storage.service import download_file
from sqlalchemy.orm import Session

from backend.features.dataset.service import get_dataset_by_id

def load_dataset_by_id(db: Session, dataset_id: int):
    dataset = get_dataset_by_id(db, dataset_id)

    if dataset is None:
        raise LookupError(f"Dataset {dataset_id} not found")

    if dataset.storage_bucket != "datasets":
        raise ValueError(
            "This dataset must be uploaded to the datasets bucket"
        )

    contents = download_file(
        bucket=dataset.storage_bucket,
        path=dataset.storage_path,
    )

    return pd.read_csv(
        BytesIO(contents),
        encoding="utf-8-sig",
    )

def inspect_dataset(df):
    rows, cols = df.shape

    return {
        "rows": rows,
        "cols": cols,
        "column_names": df.columns.tolist(),
        "column_types": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isna().sum().to_dict(),
        # Distinct non-missing values per column; lets the UI spot ID-like
        # and high-cardinality columns before they are one-hot encoded.
        "unique_values": {
            column: int(count) for column, count in df.nunique().items()
        },
        "total_missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }

# if __name__ == "__main__":
#     df = load_dataset_by_id(8)
#     print(df.shape)


