import pandas as pd
from pandas.api.types import is_numeric_dtype

import pandas as pd
from pandas.api.types import is_numeric_dtype


def validate_cleaning_columns(df, columns):
    selected = (
        list(df.columns)
        if columns is None
        else list(columns)
    )

    if not selected:
        raise ValueError("Select at least one cleaning column")

    if len(selected) != len(set(selected)):
        raise ValueError("Cleaning columns must not contain duplicates")

    for column in selected:
        if column not in df.columns:
            raise ValueError(f"Column '{column}' is not present")

    return selected


def remove_all_rows(df, columns=None):
    selected = validate_cleaning_columns(df, columns)

    return df.dropna(subset=selected).copy()


def fill_numeric_missing(df, strategy, columns=None):
    if strategy not in ("mean", "median"):
        raise ValueError("Strategy must be mean or median")

    if columns is None:
        selected = [
            column
            for column in df.columns
            if is_numeric_dtype(df[column])
            and not pd.api.types.is_bool_dtype(df[column])
        ]

        if not selected:
            raise ValueError("No numerical columns are available")
    else:
        selected = validate_cleaning_columns(df, columns)

    cleaned = df.copy()

    for column in selected:
        if (
            not is_numeric_dtype(cleaned[column])
            or pd.api.types.is_bool_dtype(cleaned[column])
        ):
            raise ValueError(
                f"Column '{column}' must be numerical"
            )

        if cleaned[column].isna().all():
            raise ValueError(
                f"Column '{column}' has no values "
                f"from which to calculate its {strategy}"
            )

        if strategy == "mean":
            replacement = cleaned[column].mean()
        else:
            replacement = cleaned[column].median()

        cleaned[column] = cleaned[column].fillna(replacement)

    return cleaned


def replace_with_avg(df, columns=None):
    return fill_numeric_missing(df, "mean", columns)


def replace_with_median(df, columns=None):
    return fill_numeric_missing(df, "median", columns)


def clean_missing_values(df, strategy, columns=None):
    if strategy == "drop":
        return remove_all_rows(df, columns)

    if strategy == "mean":
        return replace_with_avg(df, columns)

    if strategy == "median":
        return replace_with_median(df, columns)

    raise ValueError("Invalid missing-value strategy")