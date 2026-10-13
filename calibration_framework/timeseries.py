from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any, Sequence
import pandas as pd
import numpy as np


def format_time_label(step_idx: int, interval_mins: int = 10) -> str:
    """Formats a 1-based step index into Day and Time representation (e.g. 'D1 00:00', 'D1 00:10')."""
    total_mins = max(0, (step_idx - 1)) * interval_mins
    day = (total_mins // 1440) + 1
    rem_mins = total_mins % 1440
    hours = rem_mins // 60
    mins = rem_mins % 60
    return f"D{day} {hours:02d}:{mins:02d}"


def build_timeseries_comparison_dataframe(
    df_true: pd.DataFrame,
    df_pred: pd.DataFrame | None = None,
    df_before: pd.DataFrame | None = None,
    df_after: pd.DataFrame | None = None,
    df_extra: pd.DataFrame | None = None,
    variables: Sequence[str] | None = None,
    interval_mins: int = 10,
    scenario_name: str | None = None,
) -> pd.DataFrame:
    """
    Constructs a unified, standardized timeseries comparison DataFrame.
    
    Output columns include:
      - 'step': 1-based integer index
      - 'time': formatted day/time string ('D1 00:00')
      - 'scenario': optional scenario label
      - For each evaluated variable <var>:
          * '<var>_a' or '<var>_true': Ground-truth / high-fidelity target
          * '<var>_b' or '<var>_after': Calibrated / prediction model
          * '<var>_before': Model baseline before calibration (if available)
          * '<var>_after': Calibrated model (if available)
          * '<var>_a_before': Model A prior to perturbation (for recalibration)
          * '<var>_residual': Difference (<var>_a - <var>_b)
          * '<var>_residual_before': Difference (<var>_a - <var>_before)
          * '<var>_residual_after': Difference (<var>_a - <var>_after)
    """
    all_dfs = [df for df in [df_true, df_pred, df_before, df_after, df_extra] if df is not None and not df.empty]
    if not all_dfs or df_true is None or df_true.empty:
        return pd.DataFrame()

    min_len = min(len(df) for df in all_dfs)
    if min_len <= 0:
        return pd.DataFrame()

    # Determine candidate variables dynamically across DataFrames
    ignore_cols = {
        "timeindex", "step", "time", "date/time", "datetime",
        "timestamp", "hour", "day", "minute", "index", "unnamed: 0",
        "scenario", "scenario_name",
    }
    if variables is None or len(variables) == 0:
        # Dynamically discover all numeric columns from df_true that are not time/index metadata
        vars_to_use = [
            c for c in df_true.columns
            if c.lower() not in ignore_cols and pd.api.types.is_numeric_dtype(df_true[c])
        ]
    else:
        vars_to_use = [c for c in variables if c in df_true.columns]

    rows: list[dict[str, Any]] = []

    for i in range(min_len):
        row_true = df_true.iloc[i]
        time_idx = int(row_true.get("TimeIndex", i + 1)) if "TimeIndex" in row_true else i + 1
        
        # Check if row already contains formatted time string, otherwise synthesize
        if "time" in row_true and isinstance(row_true["time"], str) and row_true["time"].strip():
            time_str = str(row_true["time"])
        elif "datetime" in row_true and isinstance(row_true["datetime"], str) and row_true["datetime"].strip():
            time_str = str(row_true["datetime"])
        elif "Date/Time" in row_true and isinstance(row_true["Date/Time"], str) and row_true["Date/Time"].strip():
            time_str = str(row_true["Date/Time"])
        else:
            time_str = format_time_label(time_idx, interval_mins=interval_mins)

        row_dict: dict[str, Any] = {
            "step": time_idx,
            "time": time_str,
        }
        if scenario_name:
            row_dict["scenario"] = scenario_name

        for var in vars_to_use:
            # Model A (Target)
            val_a = None
            if var in df_true.columns and not pd.isna(df_true[var].iloc[i]):
                val_a = round(float(df_true[var].iloc[i]), 4)
                row_dict[f"{var}_a"] = val_a
                row_dict[f"{var}_true"] = val_a

            # Model A Before Perturbation (Recalibration)
            if df_extra is not None and not df_extra.empty and var in df_extra.columns and not pd.isna(df_extra[var].iloc[i]):
                val_extra = round(float(df_extra[var].iloc[i]), 4)
                row_dict[f"{var}_a_before"] = val_extra

            # Model B Before Calibration
            val_before = None
            if df_before is not None and not df_before.empty and var in df_before.columns and not pd.isna(df_before[var].iloc[i]):
                val_before = round(float(df_before[var].iloc[i]), 4)
                row_dict[f"{var}_before"] = val_before
                if val_a is not None:
                    row_dict[f"{var}_residual_before"] = round(val_a - val_before, 4)

            # Model B After / Calibrated
            val_b = None
            target_after_df = df_after if (df_after is not None and not df_after.empty) else df_pred
            if target_after_df is not None and not target_after_df.empty and var in target_after_df.columns and not pd.isna(target_after_df[var].iloc[i]):
                val_b = round(float(target_after_df[var].iloc[i]), 4)
                row_dict[f"{var}_b"] = val_b
                row_dict[f"{var}_after"] = val_b
                if val_a is not None:
                    row_dict[f"{var}_residual"] = round(val_a - val_b, 4)
                    row_dict[f"{var}_residual_after"] = round(val_a - val_b, 4)

        rows.append(row_dict)

    return pd.DataFrame(rows)


def export_timeseries_table(
    df_true: pd.DataFrame,
    output_path: str | Path,
    df_pred: pd.DataFrame | None = None,
    df_before: pd.DataFrame | None = None,
    df_after: pd.DataFrame | None = None,
    df_extra: pd.DataFrame | None = None,
    variables: Sequence[str] | None = None,
    interval_mins: int = 10,
    scenario_name: str | None = None,
) -> pd.DataFrame:
    """Builds and exports a timeseries comparison table to the specified CSV file path."""
    df_ts = build_timeseries_comparison_dataframe(
        df_true=df_true,
        df_pred=df_pred,
        df_before=df_before,
        df_after=df_after,
        df_extra=df_extra,
        variables=variables,
        interval_mins=interval_mins,
        scenario_name=scenario_name,
    )
    if not df_ts.empty:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df_ts.to_csv(out, index=False)
        print(f"Exported timeseries data table ({len(df_ts)} steps) to {out.resolve()}")
    return df_ts


def export_fitness_history_table(
    source_history: str | Path | pd.DataFrame | list[dict[str, Any]] | None,
    output_path: str | Path,
) -> pd.DataFrame:
    """
    Extracts and standardizes optimization / GA calibration convergence history
    and writes it to the designated CSV output path.
    """
    df_history: pd.DataFrame | None = None

    if source_history is None:
        return pd.DataFrame()

    if isinstance(source_history, (str, Path)):
        p = Path(source_history)
        if p.is_dir():
            candidates = [p / "calibration_history.csv", p / "ga_results.csv"]
            for cand in candidates:
                if cand.exists():
                    try:
                        df_history = pd.read_csv(cand)
                        break
                    except Exception:
                        pass
        elif p.is_file() and p.exists():
            try:
                df_history = pd.read_csv(p)
            except Exception:
                pass
    elif isinstance(source_history, pd.DataFrame):
        df_history = source_history.copy()
    elif isinstance(source_history, list):
        df_history = pd.DataFrame(source_history)

    if df_history is None or df_history.empty:
        return pd.DataFrame()

    # Clean and standardize columns
    df_history = df_history.fillna(0).replace([float("inf"), float("-inf")], 0)
    if "generation" not in df_history.columns and "iteration" in df_history.columns:
        df_history["generation"] = df_history["iteration"]
    elif "generation" not in df_history.columns:
        df_history["generation"] = range(1, len(df_history) + 1)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df_history.to_csv(out, index=False)
    print(f"Exported calibration fitness history ({len(df_history)} generations) to {out.resolve()}")
    return df_history
