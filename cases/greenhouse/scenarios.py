from __future__ import annotations
import os
import shutil
from pathlib import Path
import pandas as pd
import openstudio

from calibration_framework.model_adapter import load_osm, translate_model_to_idf
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.metrics import calc_metrics
from calibration_framework.schemas import OutputMappingConfig
from cases.greenhouse.adapters import (
    substitute_greenhouse_parameters_osm,
    apply_degradation_fault,
    apply_load_shift_schedule,
)


def run_greenhouse_scenario(
    scenario_name: str,
    extended_osm_a: str | Path,
    extended_osm_b: str | Path,
    epw_path: str | Path,
    output_dir: str | Path,
    start_m: int,
    start_d: int,
    end_m: int,
    end_d: int,
    model_b_thetas: list[float],
    output_mappings: list[OutputMappingConfig] | None = None,
    load_shift: bool = False,
    degradation_fault: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Executes a high-fidelity vs reduced-order greenhouse scenario simulation.
    Returns (df_true, df_pred, df_metrics).
    """
    scenario_dir = os.path.join(str(output_dir), scenario_name.replace(" ", "_").lower())
    os.makedirs(scenario_dir, exist_ok=True)

    # 1. Load extended OSM models
    model_a = load_osm(extended_osm_a)
    model_b = load_osm(extended_osm_b)

    # 2. Modify RunPeriod in both OSMs
    for m in [model_a, model_b]:
        rp = m.getRunPeriod()
        rp.setBeginMonth(start_m)
        rp.setBeginDayOfMonth(start_d)
        rp.setEndMonth(end_m)
        rp.setEndDayOfMonth(end_d)

    # 3. Apply load shift if requested
    if load_shift:
        apply_load_shift_schedule(model_a)
        apply_load_shift_schedule(model_b)

    # 4. Substitute parameters on Model A & Model B
    if degradation_fault:
        apply_degradation_fault(model_a, infiltration_ach=2.5, pv_active_fraction=0.75)

    substitute_greenhouse_parameters_osm(model_b, *model_b_thetas)

    # 5. Translate models to IDF in scenario dir
    idf_a_path = os.path.join(scenario_dir, "model_a.idf")
    idf_b_path = os.path.join(scenario_dir, "model_b.idf")
    translate_model_to_idf(model_a, idf_a_path)
    translate_model_to_idf(model_b, idf_b_path)

    # 6. Run Model A (Virtual World)
    dir_a = os.path.join(scenario_dir, "sim_a")
    runner_a = EnergyPlusRunner(idf_a_path, epw_path, dir_a, output_mappings=output_mappings)
    runner_a.run(mute=True)
    df_true = runner_a.get_results()

    # 7. Run Model B (Calibrated Digital Twin)
    dir_b = os.path.join(scenario_dir, "sim_b")
    runner_b = EnergyPlusRunner(idf_b_path, epw_path, dir_b, output_mappings=output_mappings)
    runner_b.run(mute=True)
    df_pred = runner_b.get_results()

    # 8. Compute metrics
    metrics = []
    variables = ["temp", "humidity", "indoor_solar", "t_glass", "grid_in", "grid_out", "pv", "soc"]
    min_len = min(len(df_true), len(df_pred))

    for col in variables:
        if col in df_true.columns and col in df_pred.columns:
            m = calc_metrics(
                df_true[col].iloc[:min_len].values,
                df_pred[col].iloc[:min_len].values,
                var_name=col,
            )
            m["Scenario"] = scenario_name
            m["Variable"] = col.upper()
            metrics.append(m)

    df_metrics = pd.DataFrame(metrics)
    if not df_metrics.empty:
        cols = [
            "Scenario",
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
        df_metrics = df_metrics[[c for c in cols if c in df_metrics.columns]]
        df_metrics.to_csv(os.path.join(scenario_dir, "metrics.csv"), index=False)

    return df_true, df_pred, df_metrics
