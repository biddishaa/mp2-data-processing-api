import logging

import pandas as pd


logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, filename: str, df: pd.DataFrame) -> int:
        self._counter += 1
        dataset_id = self._counter

        self._store[dataset_id] = {
            "filename": filename,
            "df": df.copy(),
        }

        logger.debug("Saved dataset %s: %s", dataset_id, filename)
        return dataset_id

    def get(self, dataset_id: int):
        dataset = self._store.get(dataset_id)

        if dataset is None:
            return None

        return dataset["df"].copy()

    def get_metadata(self, dataset_id: int):
        dataset = self._store.get(dataset_id)

        if dataset is None:
            return None

        df = dataset["df"]

        return {
            "id": dataset_id,
            "filename": dataset["filename"],
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
        }

    def update(self, dataset_id: int, df: pd.DataFrame) -> bool:
        if dataset_id not in self._store:
            return False

        self._store[dataset_id]["df"] = df.copy()
        logger.debug("Updated dataset %s", dataset_id)
        return True

    def clear(self):
        self._store.clear()
        self._counter = 0
        logger.debug("Cleared dataset storage")
        