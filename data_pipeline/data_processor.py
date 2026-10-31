# data_processor.py
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    logger.debug(f"remove_duplicates: {before} -> {len(df)} rows")
    return df


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    if axis == "rows":
        before = len(df)
        df = df.dropna()
        logger.debug(f"handle_missing: {before} -> {len(df)} rows")
    elif axis == "columns":
        before = df.shape[1]
        df = df.dropna(axis=1)
        logger.debug(f"handle_missing: {before} -> {df.shape[1]} columns")
    else:
        logger.error(f"Unsupported missing-value axis: {axis}")
        raise ValueError(f"Unsupported missing-value axis: {axis}")
    return df


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    # Check the method first so a bad config fails even if no column is valid
    if method not in ["iqr", "zscore"]:
        logger.error(f"Unsupported outlier method: {method}")
        raise ValueError(f"Unsupported outlier method: {method}")

    for col in columns:
        if col not in df.columns:
            logger.warning(f"Column not found: {col}")
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.warning(f"Column is not numeric: {col}")
            continue

        before = len(df)

        if method == "iqr":
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            is_outlier = (df[col] < lower) | (df[col] > upper)
        else:  # zscore
            mean = df[col].mean()
            std = df[col].std()
            z_scores = (df[col] - mean) / std
            is_outlier = z_scores.abs() > threshold

        df = df[~is_outlier]
        removed = before - len(df)

        if method == "iqr":
            logger.debug(
                f"{col}: method={method}, threshold={threshold}, "
                f"lower={lower}, upper={upper}, removed={removed}"
            )
        else:
            logger.debug(
                f"{col}: method={method}, threshold={threshold}, removed={removed}"
            )

    return df


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    processing = config["processing"]

    # 1. Remove duplicates
    if processing.get("remove_duplicates"):
        df = remove_duplicates(df)

    # 2. Handle missing values
    missing = processing.get("missing", {})
    if missing.get("enabled"):
        df = handle_missing(df, axis=missing["axis"])

    # 3. Remove outliers
    outliers = processing.get("outliers", {})
    if outliers.get("enabled"):
        df = remove_outliers(
            df,
            columns=outliers["columns"],
            method=outliers["method"],
            threshold=outliers["threshold"],
        )

    return df


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    return {
        "rows_before": df_before.shape[0],
        "rows_after": df_after.shape[0],
        "rows_removed": df_before.shape[0] - df_after.shape[0],
        "columns_before": df_before.shape[1],
        "columns_after": df_after.shape[1],
        "columns_removed": df_before.shape[1] - df_after.shape[1],
    }
