"""
PySpark-compatible DataFrame API and SparkSession engine implemented with Python/Pandas.
Provides fluent API transformations, typed operations, and lakehouse partition writer.
"""
from typing import List, Dict, Any, Optional, Callable, Union
from pathlib import Path
import json
import pandas as pd
import numpy as np


class DataFrameWriter:
    """Mirrors PySpark's DataFrameWriter API."""

    def __init__(self, df: "SparkDataFrame"):
        self.df = df
        self._mode = "overwrite"
        self._format = "jsonl"
        self._partition_by: List[str] = []

    def mode(self, save_mode: str) -> "DataFrameWriter":
        self._mode = save_mode.lower()
        return self

    def format(self, source: str) -> "DataFrameWriter":
        self._format = source.lower()
        return self

    def partitionBy(self, *cols: str) -> "DataFrameWriter":
        self._partition_by = list(cols)
        return self

    def save(self, path: Union[str, Path]):
        target_path = Path(path)
        target_path.mkdir(parents=True, exist_ok=True)
        pdf = self.df.to_pandas()

        if self._partition_by:
            # Group by partition columns and save to partitioned subdirectories
            for keys, sub_df in pdf.groupby(self._partition_by):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                part_dir = target_path
                for col_name, val in zip(self._partition_by, keys):
                    part_dir = part_dir / f"{col_name}={val}"
                part_dir.mkdir(parents=True, exist_ok=True)
                file_dest = part_dir / f"part-00000.{self._format}"
                if self._format in ("json", "jsonl"):
                    sub_df.drop(columns=self._partition_by).to_json(file_dest, orient="records", lines=True)
                elif self._format == "csv":
                    sub_df.drop(columns=self._partition_by).to_csv(file_dest, index=False)
                elif self._format == "parquet":
                    sub_df.drop(columns=self._partition_by).to_parquet(file_dest, index=False)
        else:
            file_dest = target_path / f"part-00000.{self._format}"
            if self._format in ("json", "jsonl"):
                pdf.to_json(file_dest, orient="records", lines=True)
            elif self._format == "csv":
                pdf.to_csv(file_dest, index=False)
            elif self._format == "parquet":
                pdf.to_parquet(file_dest, index=False)


class GroupedData:
    """Mirrors PySpark's GroupedData for aggregations."""

    def __init__(self, df: "SparkDataFrame", group_cols: List[str]):
        self.df = df
        self.group_cols = group_cols

    def agg(self, agg_dict: Dict[str, str]) -> "SparkDataFrame":
        """Accepts agg mappings such as {'amount': 'sum', 'dpd': 'max'}."""
        pdf = self.df.to_pandas()
        grouped = pdf.groupby(self.group_cols).agg(agg_dict).reset_index()
        # Flatten column names if multi-index
        if isinstance(grouped.columns, pd.MultiIndex):
            grouped.columns = [f"{c[0]}_{c[1]}" if c[1] else c[0] for c in grouped.columns]
        return SparkDataFrame(grouped)

    def count(self) -> "SparkDataFrame":
        pdf = self.df.to_pandas()
        res = pdf.groupby(self.group_cols).size().reset_index(name="count")
        return SparkDataFrame(res)


class SparkDataFrame:
    """PySpark-style DataFrame API over deterministic vectorized operations."""

    def __init__(self, data: Union[pd.DataFrame, List[Dict[str, Any]]]):
        if isinstance(data, pd.DataFrame):
            self._df = data.copy()
        else:
            self._df = pd.DataFrame(data)

    def to_pandas(self) -> pd.DataFrame:
        return self._df.copy()

    @property
    def columns(self) -> List[str]:
        return list(self._df.columns)

    @property
    def write(self) -> DataFrameWriter:
        return DataFrameWriter(self)

    def count(self) -> int:
        return len(self._df)

    def select(self, *cols: str) -> "SparkDataFrame":
        existing = [c for c in cols if c in self._df.columns]
        return SparkDataFrame(self._df[existing])

    def filter(self, condition: Union[str, Callable[[pd.DataFrame], pd.Series]]) -> "SparkDataFrame":
        """Filters rows by query string expression or boolean mask callable."""
        if isinstance(condition, str):
            filtered = self._df.query(condition)
        elif callable(condition):
            filtered = self._df[condition(self._df)]
        else:
            raise TypeError("Filter condition must be a query string or callable")
        return SparkDataFrame(filtered)

    def where(self, condition: Union[str, Callable[[pd.DataFrame], pd.Series]]) -> "SparkDataFrame":
        return self.filter(condition)

    def withColumn(self, col_name: str, col_value: Union[Any, Callable[[pd.DataFrame], pd.Series]]) -> "SparkDataFrame":
        pdf = self._df.copy()
        if callable(col_value):
            pdf[col_name] = col_value(pdf)
        else:
            pdf[col_name] = col_value
        return SparkDataFrame(pdf)

    def withColumnRenamed(self, existing: str, new_name: str) -> "SparkDataFrame":
        pdf = self._df.rename(columns={existing: new_name})
        return SparkDataFrame(pdf)

    def drop(self, *cols: str) -> "SparkDataFrame":
        pdf = self._df.drop(columns=list(cols), errors="ignore")
        return SparkDataFrame(pdf)

    def dropDuplicates(self, subset: Optional[List[str]] = None) -> "SparkDataFrame":
        pdf = self._df.drop_duplicates(subset=subset)
        return SparkDataFrame(pdf)

    def groupBy(self, *cols: str) -> GroupedData:
        return GroupedData(self, list(cols))

    def join(self, other: "SparkDataFrame", on: Union[str, List[str]], how: str = "inner") -> "SparkDataFrame":
        pdf_other = other.to_pandas()
        merged = pd.merge(self._df, pdf_other, on=on, how=how)
        return SparkDataFrame(merged)

    def orderBy(self, *cols: str, ascending: bool = True) -> "SparkDataFrame":
        pdf = self._df.sort_values(by=list(cols), ascending=ascending)
        return SparkDataFrame(pdf)

    def collect(self) -> List[Dict[str, Any]]:
        return self._df.to_dict(orient="records")

    def show(self, n: int = 10):
        print(self._df.head(n).to_string())


class DataFrameReader:
    """Mirrors PySpark's DataFrameReader API."""

    def __init__(self):
        self._format = "jsonl"

    def format(self, fmt: str) -> "DataFrameReader":
        self._format = fmt.lower()
        return self

    def load(self, path: Union[str, Path]) -> SparkDataFrame:
        target_path = Path(path)
        if not target_path.exists():
            return SparkDataFrame([])

        files: List[Path] = []
        if target_path.is_file():
            files = [target_path]
        else:
            files = list(target_path.glob("**/*.*"))

        dfs = []
        for f in files:
            try:
                if f.name.endswith(".jsonl") or f.name.endswith(".json"):
                    dfs.append(pd.read_json(f, lines=True))
                elif f.name.endswith(".csv"):
                    dfs.append(pd.read_csv(f))
                elif f.name.endswith(".parquet"):
                    dfs.append(pd.read_parquet(f))
            except Exception:
                continue

        if not dfs:
            return SparkDataFrame([])
        return SparkDataFrame(pd.concat(dfs, ignore_index=True))


class SparkSession:
    """Simulates a PySpark SparkSession for local batch execution."""

    class Builder:
        def __init__(self):
            self._app_name = "CollectionsLakehouse"

        def appName(self, name: str) -> "SparkSession.Builder":
            self._app_name = name
            return self

        def getOrCreate(self) -> "SparkSession":
            return SparkSession(self._app_name)

    builder = Builder()

    def __init__(self, app_name: str = "CollectionsLakehouse"):
        self.appName = app_name
        self.read = DataFrameReader()

    def createDataFrame(self, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> SparkDataFrame:
        return SparkDataFrame(data)

    def stop(self):
        pass


# Global spark session helper
spark = SparkSession.builder.appName("CollectionsCopilotLakehouse").getOrCreate()
