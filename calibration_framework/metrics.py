from __future__ import annotations
import os
from pathlib import Path
from typing import Literal, Sequence
import numpy as np
import pandas as pd


# Default keyword patterns for automatic variable classification
DEFAULT_TEMPERATURE_KEYWORDS = [
    "temp",
    "temperature",
    "drybulb",
    "wetbulb",
    "dewpoint",
    "t_zone",
    "t_air",
    "t_surface",
    "t_mean",
    "t_in",
    "t_out",
    "t_indoor",
    "t_outdoor",
    "t_glass",
    "degc",
    "deg_c",
    "_t",
    "t_",
]

DEFAULT_ZERO_CROSSING_KEYWORDS = [
    "grid",
    "net",
    "flux",
    "flow",
    "power_net",
    "charge",
    "discharge",
    "current",
    "balance",
    "delta",
]


def calc_metrics(
    y_true: np.ndarray | list[float] | pd.Series,
    y_pred: np.ndarray | list[float] | pd.Series,
    var_name: str | None = None,
    variable_type: Literal["auto", "temperature", "zero_crossing", "standard"] = "auto",
    epsilon: float = 1e-5,
    custom_temp_keywords: list[str] | None = None,
    custom_zero_crossing_keywords: list[str] | None = None,
) -> dict[str, float]:
    """Calculates comprehensive accuracy and calibration quality metrics for simulation time-series.

    The metric evaluation logic accounts for physical properties and scaling behavior:
      1. Temperature / Affine Thermal Variables:
         - Percentage metrics (CVRMSE, MAPE, NMBE) are computed on the absolute thermodynamic
           scale (Kelvin: T_K = T_C + 273.15) to prevent numerical distortion caused by zero-crossings
           or near-zero values on relative scales (such as Celsius).
      2. Zero-Crossing / Bidirectional Flux Variables (e.g. Net Grid Power, Energy Storage Flow):
         - Variables spanning both positive and negative values can cause division-by-zero or
           asymptotic explosions with standard mean-normalized metrics.
         - NRMSE_range (%) normalizes RMSE by the full dynamic operating span (y_max - y_min).
         - MAPE is computed via Range-Normalized Mean Absolute Error (NMAE = MAE / Range * 100%).
      3. Standard Positive Physical Quantities (e.g. Solar Radiation, Energy Use, Mass Flow):
         - Evaluated using standard engineering calibration metrics (MAE, RMSE, Max Error,
           MAPE, R2, CVRMSE, NRMSE_range, NMBE).

    Args:
        y_true: Ground truth or high-fidelity target values.
        y_pred: Predicted or calibrated model output values.
        var_name: Optional variable identifier used for automatic type detection.
        variable_type: Strategy for metric calculation ('auto', 'temperature', 'zero_crossing', 'standard').
        epsilon: Small numerical stability constant to prevent division-by-zero.
        custom_temp_keywords: Optional custom substrings to match for temperature variables.
        custom_zero_crossing_keywords: Optional custom substrings to match for zero-crossing variables.

    Returns:
        Dictionary containing calculated metrics: MAE, RMSE, Max Error, MAPE (%), R2,
        CVRMSE (%), NRMSE_range (%), and NMBE (%).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if len(y_true) != len(y_pred):
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true[:min_len]
        y_pred = y_pred[:min_len]

    mae = float(np.mean(np.abs(y_true - y_pred))) if len(y_true) > 0 else 0.0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2))) if len(y_true) > 0 else 0.0
    max_err = float(np.max(np.abs(y_true - y_pred))) if len(y_true) > 0 else 0.0

    # Range-Normalized RMSE (NRMSE_range) across dynamic range
    val_range = float(np.max(y_true) - np.min(y_true)) if len(y_true) > 0 else 0.0
    nrmse_range = (rmse / val_range * 100.0) if val_range > epsilon else 0.0

    # Coefficient of Determination (R2)
    ss_res = float(np.sum((y_true - y_pred) ** 2)) if len(y_true) > 0 else 0.0
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2)) if len(y_true) > 0 else 0.0
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > epsilon else 0.0

    # Determine variable category
    var_str = str(var_name).lower() if var_name is not None else ""
    temp_kw = custom_temp_keywords if custom_temp_keywords is not None else DEFAULT_TEMPERATURE_KEYWORDS
    zero_kw = custom_zero_crossing_keywords if custom_zero_crossing_keywords is not None else DEFAULT_ZERO_CROSSING_KEYWORDS

    if variable_type == "temperature":
        is_temp = True
        is_zero_crossing = False
    elif variable_type == "zero_crossing":
        is_temp = False
        is_zero_crossing = True
    elif variable_type == "standard":
        is_temp = False
        is_zero_crossing = False
    else:  # "auto"
        is_temp = any(k in var_str for k in temp_kw)
        if not is_temp:
            has_bipolar_data = bool(np.any(y_true < -epsilon) and np.any(y_true > epsilon))
            has_zero_kw = any(k in var_str for k in zero_kw)
            is_zero_crossing = has_bipolar_data or has_zero_kw or bool(np.any(y_true < 0))
        else:
            is_zero_crossing = False

    if is_temp:
        # Convert Celsius to absolute thermodynamic Kelvin (T_K = T_C + 273.15)
        # Prevents distortion in ratio metrics (CVRMSE, MAPE, NMBE) when Celsius values cross/approach 0
        y_true_k = y_true + 273.15
        y_pred_k = y_pred + 273.15
        mean_true_k = float(np.mean(y_true_k)) if len(y_true_k) > 0 else 0.0
        sum_true_k = float(np.sum(y_true_k)) if len(y_true_k) > 0 else 0.0

        cvrmse = float((rmse / mean_true_k) * 100.0) if abs(mean_true_k) > epsilon else 0.0
        nmbe = float((np.sum(y_true_k - y_pred_k) / sum_true_k) * 100.0) if abs(sum_true_k) > epsilon else 0.0
        mape = float(np.mean(np.abs((y_true_k - y_pred_k) / (np.abs(y_true_k) + epsilon))) * 100.0) if len(y_true_k) > 0 else 0.0

    elif is_zero_crossing:
        # Zero-crossing / bidirectional physical quantities (e.g. net power, storage flow)
        mean_true = float(np.mean(y_true)) if len(y_true) > 0 else 0.0
        sum_true = float(np.sum(y_true)) if len(y_true) > 0 else 0.0

        cvrmse = float((rmse / mean_true) * 100.0) if abs(mean_true) > epsilon else 0.0
        nmbe = float((np.sum(y_true - y_pred) / sum_true) * 100.0) if abs(sum_true) > epsilon else 0.0
        # Use Range-Normalized MAE (NMAE) to avoid division by near-zero instantaneous values
        mape = float((mae / val_range) * 100.0) if val_range > epsilon else 0.0

    else:
        # Standard positive continuous physical variables (e.g. load, solar flux, flow rates)
        mean_true = float(np.mean(y_true)) if len(y_true) > 0 else 0.0
        sum_true = float(np.sum(y_true)) if len(y_true) > 0 else 0.0

        cvrmse = float((rmse / mean_true) * 100.0) if abs(mean_true) > epsilon else 0.0
        nmbe = float((np.sum(y_true - y_pred) / sum_true) * 100.0) if abs(sum_true) > epsilon else 0.0
        mape = float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + epsilon))) * 100.0) if len(y_true) > 0 else 0.0

    return {
        "MAE": mae,
        "RMSE": rmse,
        "Max Error": max_err,
        "MAPE (%)": mape,
        "R2": r2,
        "CVRMSE (%)": cvrmse,
        "NRMSE_range (%)": nrmse_range,
        "NMBE (%)": nmbe,
    }


def calc_dataframe_metrics(
    df_true: pd.DataFrame,
    df_pred: pd.DataFrame,
    variables: list[str] | None = None,
    label: str = "Model",
    uppercase_var_names: bool = True,
    epsilon: float = 1e-5,
) -> pd.DataFrame:
    """Calculates evaluation metrics across multiple DataFrame columns for a given model/run.

    Args:
        df_true: Target ground-truth DataFrame.
        df_pred: Model prediction DataFrame.
        variables: Optional subset of column names to evaluate. If None, common columns are used.
        label: Descriptive label for this model/experiment stage.
        uppercase_var_names: Whether to format variable names in uppercase in the output table.
        epsilon: Numerical stability constant.

    Returns:
        DataFrame containing computed metrics for all evaluated columns.
    """
    if variables is None:
        variables = [c for c in df_true.columns if c in df_pred.columns and c != "TimeIndex"]

    min_len = min(len(df_true), len(df_pred))
    results = []

    for col in variables:
        if col not in df_true.columns or col not in df_pred.columns:
            continue

        y_true = df_true[col].iloc[:min_len].values
        y_pred = df_pred[col].iloc[:min_len].values

        m = calc_metrics(y_true, y_pred, var_name=col, epsilon=epsilon)
        m["Experiment"] = label
        m["Variable"] = col.upper() if uppercase_var_names else col
        results.append(m)

    df_metrics = pd.DataFrame(results)
    if not df_metrics.empty:
        col_order = [
            "Experiment",
            "Variable",
            "MAE",
            "RMSE",
            "Max Error",
            "MAPE (%)",
            "R2",
            "CVRMSE (%)",
            "NRMSE_range (%)",
            "NMBE (%)",
        ]
        df_metrics = df_metrics[[c for c in col_order if c in df_metrics.columns]]

    return df_metrics


def generate_metrics_report(
    df_true: pd.DataFrame,
    df_before: pd.DataFrame | None = None,
    df_after: pd.DataFrame | None = None,
    output_path: str | Path | None = None,
    variables: list[str] | None = None,
    models: dict[str, pd.DataFrame] | None = None,
    labels: list[str] | None = None,
    prefix: str | None = None,
    label: str | None = None,
    uppercase_var_names: bool = True,
    verbose: bool = True,
    epsilon: float = 1e-5,
    **kwargs: Any,
) -> pd.DataFrame:
    """Generates a structured accuracy and calibration evaluation report comparing one or more models against ground truth.

    Supports both:
      1. Classic Before/After comparison: `generate_metrics_report(df_true, df_before, df_after, output_path)`
      2. Arbitrary multi-model comparison dictionary: `generate_metrics_report(df_true, models={"Baseline": df_b, "Calibrated": df_c}, output_path=...)`
      3. Single model comparison with prefix/label: `generate_metrics_report(df_true, df_pred, prefix="Baseline")`

    Args:
        df_true: Ground-truth / high-fidelity target DataFrame.
        df_before: Optional baseline model prediction DataFrame (before calibration).
        df_after: Optional calibrated model prediction DataFrame (after calibration).
        output_path: Optional file path where the resulting CSV report will be saved.
        variables: List of target variable column names to evaluate. If None, common columns are detected automatically.
        models: Optional dictionary mapping model/experiment names to prediction DataFrames.
        labels: Optional custom label names for `[df_before, df_after]`. Defaults to `["Before Calibration", "After Calibration"]`.
        prefix: Optional experiment/model label (alias for single model evaluation).
        label: Optional experiment/model label.
        uppercase_var_names: Whether to format variable column names in uppercase.
        verbose: Whether to print summary table and save confirmation logs to console.
        epsilon: Numerical stability constant.

    Returns:
        Consolidated pandas DataFrame containing computed metrics for all evaluated models and variables.
    """
    model_dict: dict[str, pd.DataFrame] = {}

    if models is not None:
        model_dict.update(models)
    else:
        custom_single_label = prefix or label
        before_label = custom_single_label or (labels[0] if labels and len(labels) > 0 else "Before Calibration")
        after_label = labels[1] if labels and len(labels) > 1 else "After Calibration"

        if df_before is not None:
            model_dict[before_label] = df_before
        if df_after is not None:
            model_dict[after_label] = df_after

    if not model_dict:
        if verbose:
            print("[Metrics] Warning: No prediction DataFrames provided for evaluation.")
        return pd.DataFrame()

    # Determine common variables across true dataset and all models if not provided
    if variables is None:
        common = set(df_true.columns)
        for df_m in model_dict.values():
            common = common.intersection(set(df_m.columns))
        common.discard("TimeIndex")
        variables = sorted(list(common))

    all_results: list[pd.DataFrame] = []
    for model_name, df_pred in model_dict.items():
        df_m = calc_dataframe_metrics(
            df_true=df_true,
            df_pred=df_pred,
            variables=variables,
            label=model_name,
            uppercase_var_names=uppercase_var_names,
            epsilon=epsilon,
        )
        if not df_m.empty:
            all_results.append(df_m)

    df_metrics = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df_metrics.to_csv(out_p, index=False)
        if verbose:
            print(f"\n[Metrics] Evaluation report saved to: {out_p.resolve()}")

    if verbose:
        print("\n[Metrics] Evaluation Results:")
        print(df_metrics.to_string(index=False) if not df_metrics.empty else "No metrics generated.")

    return df_metrics


def check_ashrae_compliance(
    df_metrics: pd.DataFrame,
    frequency: Literal["hourly", "monthly"] = "hourly",
) -> pd.DataFrame:
    """Evaluates whether simulation accuracy metrics satisfy ASHRAE Guideline 14 calibration criteria.

    ASHRAE Guideline 14 Thresholds:
      - Hourly Timestep: |NMBE| <= 10% and CVRMSE <= 30%
      - Monthly Timestep: |NMBE| <= 5% and CVRMSE <= 15%

    Args:
        df_metrics: Metrics DataFrame containing 'NMBE (%)' and 'CVRMSE (%)' columns.
        frequency: Simulation data frequency ('hourly' or 'monthly').

    Returns:
        DataFrame with an added 'ASHRAE_14_Compliant' boolean column.
    """
    df_out = df_metrics.copy()
    if "NMBE (%)" not in df_out.columns or "CVRMSE (%)" not in df_out.columns:
        return df_out

    nmbe_limit = 10.0 if frequency == "hourly" else 5.0
    cvrmse_limit = 30.0 if frequency == "hourly" else 15.0

    df_out["ASHRAE_14_Compliant"] = (
        (df_out["NMBE (%)"].abs() <= nmbe_limit) &
        (df_out["CVRMSE (%)"] <= cvrmse_limit)
    )
    return df_out
