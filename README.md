# MP2: Data Processing REST API

This project is a FastAPI application that wraps my MP1 data-processing pipeline in a REST API. It supports `GET /health` for a status check, `POST /upload` to upload a CSV into in-memory storage and receive a dataset ID, `GET /datasets/{id}` to retrieve stored rows (with an optional `limit`), and `POST /datasets/{id}/process` to validate and clean a stored dataset using a JSON configuration (required/numeric columns, duplicate removal, missing-value handling, optional outlier removal). A logging middleware assigns each request an `X-Request-ID` and logs the method, path, status code, and duration. API behavior is tested with pytest and FastAPI's TestClient.

## Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to try the endpoints.

## Test

```bash
python -m pytest tests -v
```
