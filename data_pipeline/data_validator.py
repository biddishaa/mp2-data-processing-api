# src/data_validator.py
import logging
import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """
    rows_before = len(df)
    df = df.copy()  # do not modify the caller's DataFrame

    # 1. Required columns must exist
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Required column missing: {col}")
            raise ValueError(f"Required column missing: {col}")

    # 2. Numeric columns: remove rows with non-numeric values, then convert
    for col in numeric_columns:
        if col not in df.columns:
            logger.error(f"Numeric column missing: {col}")
            raise ValueError(f"Numeric column missing: {col}")

        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    logger.warning(f"Invalid numeric value in {col} at row {i}: {value!r}")
                    invalid_rows.append(i)

        if invalid_rows:
            logger.warning(
                f"Removed {len(invalid_rows)} rows with invalid numeric values in {col}"
            )
            df = df.drop(index=invalid_rows)

        # convert to a numeric data type
        df[col] = pd.to_numeric(df[col])

    logger.debug(
        f"Validation: {rows_before} -> {len(df)} rows "
        f"(valid={len(df)}, removed={rows_before - len(df)})"
    )
    return df
