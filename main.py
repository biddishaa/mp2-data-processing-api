import io
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from src import DatasetInfo, DatasetStorage, HealthResponse, setup_logging


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Processing API",
    version="1.0.0",
)

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