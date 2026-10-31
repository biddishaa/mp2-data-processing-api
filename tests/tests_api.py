def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    # NOTE: change "rows"/"columns" if your DatasetInfo uses other field names
    assert body["rows"] == 6
    assert body["columns"] == 2
    assert isinstance(body["id"], int) and body["id"] > 0


def test_process_and_retrieve(client, uploaded_dataset_id, processing_body):
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 1
    assert body["cleaning_report"]["rows_before"] == 5
    assert body["cleaning_report"]["rows_after"] == 3

    response = client.get(f"/datasets/{uploaded_dataset_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    records = data["data"]
    assert [r["student_id"] for r in records] == [1, 2, 5]
    assert [r["score"] for r in records] == [80, 90, 85]


def test_retrieve_missing_dataset(client):
    response = client.get("/datasets/9999")
    assert response.status_code == 404