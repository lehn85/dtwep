from __future__ import annotations
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
import pandas as pd
from pyenergyplus.api import EnergyPlusAPI

from calibration_framework.schemas import OutputMappingConfig


class SQLiteOutputExtractor:
    """
    Dynamically queries and transforms EnergyPlus SQLite output database into pandas DataFrames
    based on declarative OutputMappingConfig rules.
    """

    def __init__(self, mappings: list[OutputMappingConfig]):
        self.mappings = mappings

    def extract(self, sql_path: str | Path) -> pd.DataFrame:
        sql_file = str(sql_path)
        if not os.path.exists(sql_file):
            raise FileNotFoundError(f"EnergyPlus SQLite output not found at: {sql_file}")

        # Fetch unique variable names to query
        unique_vars = list({m.var_name for m in self.mappings})
        if not unique_vars:
            return pd.DataFrame()

        placeholders = ", ".join(["?"] * len(unique_vars))
        query = f"""
        SELECT 
            r.TimeIndex,
            d.Name,
            d.KeyValue,
            r.Value
        FROM ReportData r
        JOIN ReportDataDictionary d ON r.ReportDataDictionaryIndex = d.ReportDataDictionaryIndex
        WHERE d.Name IN ({placeholders})
        """

        # Copy SQLite file to temp file to avoid locking/concurrency corruption
        fd, temp_sql_path = tempfile.mkstemp(suffix=".sql")
        os.close(fd)
        try:
            shutil.copy2(sql_file, temp_sql_path)
            conn = sqlite3.connect(temp_sql_path)
            df_raw = pd.read_sql_query(query, conn, params=unique_vars)
            conn.close()
        finally:
            try:
                os.remove(temp_sql_path)
            except Exception:
                pass

        if df_raw.empty:
            return pd.DataFrame()

        time_indices = sorted(df_raw["TimeIndex"].unique())
        result_df = pd.DataFrame({"TimeIndex": time_indices})

        for mapping in self.mappings:
            sub = df_raw[df_raw["Name"] == mapping.var_name]

            # KeyValue filtering
            if mapping.key_value != "*":
                sub = sub[sub["KeyValue"].str.upper() == mapping.key_value.upper()]

            if mapping.key_value_filter:
                sub = sub[sub["KeyValue"].str.contains(mapping.key_value_filter, case=False, regex=True)]

            if sub.empty:
                result_df[mapping.rename_to] = 0.0
                continue

            # Aggregation across multiple matching keys per time index
            if mapping.aggregation == "sum":
                agg_series = sub.groupby("TimeIndex")["Value"].sum()
            elif mapping.aggregation == "mean":
                agg_series = sub.groupby("TimeIndex")["Value"].mean()
            elif mapping.aggregation == "last":
                agg_series = sub.groupby("TimeIndex")["Value"].last()
            elif mapping.aggregation == "first":
                agg_series = sub.groupby("TimeIndex")["Value"].first()
            else:
                agg_series = sub.groupby("TimeIndex")["Value"].first()

            # Align with time indices
            values = result_df["TimeIndex"].map(agg_series).fillna(0.0).values

            # Apply scale and offset
            transformed = (values * mapping.scale_multiplier) + mapping.offset
            result_df[mapping.rename_to] = transformed

        return result_df


class EnergyPlusRunner:
    """
    Encapsulates EnergyPlus execution via PyEnergyPlus API.
    Supports both instance-based configuration and direct run() execution.
    """

    def __init__(
        self,
        idf_path: str | Path | None = None,
        epw_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        output_mappings: list[OutputMappingConfig] | None = None,
    ):
        self.idf_path = str(idf_path) if idf_path is not None else None
        self.epw_path = str(epw_path) if epw_path is not None else None
        self.output_dir = str(output_dir) if output_dir is not None else None
        self.output_mappings = output_mappings or []
        self.extractor = SQLiteOutputExtractor(self.output_mappings)
        self.api = EnergyPlusAPI()

    def run(
        self,
        mute: bool = True,
        idf_path: str | Path | None = None,
        epw_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        output_mappings: list[OutputMappingConfig] | None = None,
    ) -> int | tuple[pd.DataFrame, int]:
        """
        Executes simulation to completion.
        If idf_path, epw_path, or output_dir are passed to run(), executes with those paths
        and returns (df, return_code).
        Otherwise, executes with instance paths and returns return_code (int).
        """
        is_direct_call = (idf_path is not None) or (epw_path is not None) or (output_dir is not None)

        if idf_path is not None:
            self.idf_path = str(idf_path)
        if epw_path is not None:
            self.epw_path = str(epw_path)
        if output_dir is not None:
            self.output_dir = str(output_dir)
        if output_mappings is not None:
            self.output_mappings = output_mappings
            self.extractor = SQLiteOutputExtractor(self.output_mappings)

        if not self.idf_path or not self.epw_path or not self.output_dir:
            raise ValueError("idf_path, epw_path, and output_dir must be provided either in __init__ or run().")

        os.makedirs(self.output_dir, exist_ok=True)

        state = self.api.state_manager.new_state()
        if mute:
            self.api.runtime.set_console_output_status(state, False)

        args = ["-d", self.output_dir, "-w", self.epw_path, self.idf_path]
        ret = self.api.runtime.run_energyplus(state, args)
        self.api.state_manager.delete_state(state)

        if is_direct_call:
            if ret != 0:
                print(f"[WARNING] EnergyPlus simulation finished with non-zero exit code: {ret}")
            sql_file = os.path.join(self.output_dir, "eplusout.sql")
            df = self.extractor.extract(sql_file) if os.path.exists(sql_file) else pd.DataFrame()
            return df, ret

        return ret

    def get_results(self, output_dir: str | Path | None = None) -> pd.DataFrame:
        """Parses output SQLite database file using configured output mappings."""
        out_dir = str(output_dir) if output_dir is not None else self.output_dir
        if not out_dir:
            raise ValueError("output_dir must be provided either in __init__ or get_results().")
        sql_file = os.path.join(out_dir, "eplusout.sql")
        if not os.path.exists(sql_file):
            return pd.DataFrame()
        return self.extractor.extract(sql_file)
