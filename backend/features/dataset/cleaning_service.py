from sqlalchemy.orm import Session

from backend.features.dataset.service import (
    get_dataset_by_id,
    upload_dataset,
)
from backend.services.data_analysis_service import load_dataset_by_id
from backend.services.data_cleaning_service import (
    clean_missing_values,
    validate_cleaning_columns,
)


def clean_and_save_dataset(
    db: Session,
    *,
    dataset_id: int,
    user_id: int,
    name: str,
    drop_duplicates: bool = False,
    missing_strategy: str = "none",
    columns: list[str] | None = None,
) -> dict:
    source = get_dataset_by_id(db, dataset_id)

    if source is None:
        raise LookupError(f"Dataset {dataset_id} not found")

    if source.added_by != user_id:
        raise ValueError("Dataset does not belong to this user")

    if missing_strategy not in ("none", "drop", "mean", "median"):
        raise ValueError("Unsupported missing-value strategy")

    if not drop_duplicates and missing_strategy == "none":
        raise ValueError("Select at least one cleaning operation")

    if missing_strategy == "none" and columns is not None:
        raise ValueError(
            "Columns are only used with a missing-value strategy"
        )

    df = load_dataset_by_id(db, dataset_id)
    cleaned = df.copy()

    selected_columns = None

    if columns is not None:
        selected_columns = validate_cleaning_columns(df, columns)

    rows_before = len(cleaned)
    missing_before = int(cleaned.isna().sum().sum())

    if drop_duplicates:
        cleaned = cleaned.drop_duplicates().copy()

    duplicates_removed = rows_before - len(cleaned)
    rows_after_duplicates = len(cleaned)

    if missing_strategy != "none":
        cleaned = clean_missing_values(
            cleaned,
            strategy=missing_strategy,
            columns=selected_columns,
        )

    missing_rows_removed = rows_after_duplicates - len(cleaned)

    if cleaned.empty:
        raise ValueError("Cleaning would leave an empty dataset")

    missing_after = int(cleaned.isna().sum().sum())

    warnings = []

    if missing_strategy in ("mean", "median"):
        warnings.append(
            "Imputation used the full dataset. For ML evaluation, "
            "prefer the original dataset with training-pipeline imputation."
        )

    if missing_after:
        warnings.append(
            "Missing values remain in the cleaned dataset."
        )

    metadata = {
        "source_dataset_id": dataset_id,
        "drop_duplicates": drop_duplicates,
        "missing_strategy": missing_strategy,
        "columns": selected_columns,
        "rows_before": rows_before,
        "rows_after": len(cleaned),
        "duplicates_removed": duplicates_removed,
        "missing_rows_removed": missing_rows_removed,
        "missing_values_before": missing_before,
        "missing_values_after": missing_after,
        "warnings": warnings,
    }

    contents = cleaned.to_csv(index=False).encode("utf-8")

    saved = upload_dataset(
        db=db,
        name=name,
        added_by=user_id,
        original_filename=f"cleaned_dataset_{dataset_id}.csv",
        contents=contents,
        cleaning_metadata=metadata,
    )

    return {
        "dataset_id": saved.dataset_id,
        "name": saved.name,
        "rows": saved.rows,
        "cols": saved.cols,
        "cleaning_metadata": metadata,
    }