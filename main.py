import io
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    ProcessConfig,
    ProcessingReport,
    log_requests,
    setup_logging,
)

setup_logging(verbose=True)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Processing API",
    version="1.0.0",
)
app.middleware("http")(log_requests)

storage = DatasetStorage()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
    }


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    filename = file.filename or ""

    if Path(filename).suffix.lower() != ".csv":
        logger.warning("Rejected unsupported file: %s", filename)
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        logger.warning("Uploaded CSV is empty: %s", filename)
        raise HTTPException(
            status_code=400,
            detail="The uploaded CSV file is empty or has no columns.",
        )
    except pd.errors.ParserError:
        logger.warning("Could not parse CSV: %s", filename)
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid CSV.",
        )
    except UnicodeDecodeError:
        logger.warning("CSV has an unsupported text encoding: %s", filename)
        raise HTTPException(
            status_code=400,
            detail="The CSV file must use a supported text encoding.",
        )

    dataset_id = storage.save(filename, df)
    metadata = storage.get_metadata(dataset_id)

    logger.info(
        "Uploaded dataset %s (%s): %s rows",
        dataset_id,
        filename,
        len(df),
    )

    return metadata


@app.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    limit: int = Query(default=100, ge=1),
):
    df = storage.get(dataset_id)

    if df is None:
        logger.warning("Dataset %s not found", dataset_id)
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID {dataset_id} not found.",
        )

    records = json.loads(
        df.head(limit).to_json(orient="records")
    )

    logger.info(
        "Returning %s rows from dataset %s",
        len(records),
        dataset_id,
    )

    return {
        "id": dataset_id,
        "data": records,
        "total_rows": len(df),
    }


@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    #  Retrieve a copy (404 if missing)
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset %s not found", dataset_id)
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID {dataset_id} not found.",
        )

    #  Request model -> dict
    settings = config.model_dump()
    required_columns = settings["validation"]["required_columns"]
    numeric_columns = settings["validation"]["numeric_columns"]

    # Every numeric column must exist
    missing = [c for c in numeric_columns if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Numeric columns not found in dataset: {missing}",
        )

    try:
        # validate
        validated = validate_dataframe(df, required_columns, numeric_columns)

        # rows removed by validation; copy before processing
        validation_removed = len(df) - len(validated)
        validated = validated.copy()

        #  Process with the full configuration dictionary
        processed = process_data(validated, settings)

        # validated copy vs processed
        report = create_cleaning_report(validated, processed)
    except ValueError as error:
        logger.warning("Processing failed for dataset %s: %s", dataset_id, error)
        raise HTTPException(status_code=400, detail=str(error))

    # only update storage only after everything succeeded
    storage.update(dataset_id, processed)

    logger.info(
        "Processed dataset: id=%s, validation_removed=%s, "
        "rows_before=%s, rows_after=%s",
        dataset_id,
        validation_removed,
        report["rows_before"],
        report["rows_after"],
    )

    # Return dict matching ProcessingReport
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_removed,
        "cleaning_report": report,
    }