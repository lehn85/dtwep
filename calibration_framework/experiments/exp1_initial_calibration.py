from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from typing import Any
import pandas as pd

from calibration_framework.schemas import InitialCalibrationExperimentConfig, CalibrationConfig
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.metrics import generate_metrics_report
from calibration_framework.model_adapter import translate_osm_to_idf
from calibration_framework.plotting import (
    plot_convergence,
    plot_computational_performance,
    plot_timeseries_comparison,
)
from calibration_framework.modules.initial_calibration import BaseInitialCalibrationModule
from calibration_framework.experiments.base import BaseExperiment


class BaseInitialCalibrationExperiment(BaseExperiment[InitialCalibrationExperimentConfig]):
    """
    Experiment 1: Model Accuracy, Initial Parameter Calibration & Computational Speedup Validation.
    Coordinates Ground Truth vs Model B benchmark validation by delegating calibration execution
    to BaseInitialCalibrationModule.
    """

    config_class = InitialCalibrationExperimentConfig
    module_class = BaseInitialCalibrationModule

    def prepare_models(self) -> None:
        """Hook for case-specific model geometry preprocessing, extension, and simplification."""
        pass

    def run_target_model(
        self,
        calib_cfg: CalibrationConfig,
        epw_path: Path,
        target_dir: Path,
    ) -> tuple[pd.DataFrame, float]:
        """Retrieves ground truth reference dataset (Model A simulation or Model P measurements)."""
        gt_data = self.ground_truth_provider.get_truth_data(
            context={
                "target_dir": target_dir,
                "epw_path": epw_path,
                "output_mappings": calib_cfg.output_mappings,
                "postprocess_fn": self.postprocess_dataframe,
            }
        )
        return gt_data.df, gt_data.execution_time

    def run_baseline_model_b(
        self,
        calib_cfg: CalibrationConfig,
        model_b_idf: Path,
        epw_path: Path,
        baseline_dir: Path,
    ) -> tuple[pd.DataFrame, float]:
        """Runs uncalibrated baseline simulation of Model B with default parameters."""
        print("\n--- Running Baseline Model B (Uncalibrated) ---")
        runner_b = EnergyPlusRunner()
        t0 = time.time()
        df_b_raw, _ = runner_b.run(
            idf_path=model_b_idf,
            epw_path=epw_path,
            output_dir=baseline_dir,
            output_mappings=calib_cfg.output_mappings,
        )
        time_b_baseline = time.time() - t0
        df_b_baseline = self.postprocess_dataframe(df_b_raw)
        return df_b_baseline, time_b_baseline

    def run(self) -> dict[str, Any]:
        """Executes the complete Experiment 1 workflow."""
        calib_cfg = self.get_calibration_config()

        # 1. Prepare / preprocess model geometry
        self.prepare_models()

        # Resolve paths
        model_b_cfg = self.config.model_b
        model_b_idf = self.resolve_path(
            getattr(model_b_cfg, "extended_idf_path", None)
            or getattr(model_b_cfg, "extended_idf", None)
            or getattr(model_b_cfg, "base_idf_path", None)
            or getattr(model_b_cfg, "base_idf", None)
            or "model_b.idf"
        )
        model_b_osm = self.resolve_path(
            getattr(model_b_cfg, "extended_osm_path", None)
            or getattr(model_b_cfg, "extended_osm", None)
            or getattr(model_b_cfg, "base_osm_path", None)
            or getattr(model_b_cfg, "base_osm", None)
            or "model_b.osm"
        )

        # Auto-translate OSM to IDF if needed
        if model_b_osm.exists() and (not model_b_idf.exists() or self.force_rerun):
            print(f"Translating Model B OpenStudio to IDF: {model_b_osm.name} -> {model_b_idf.name}")
            translate_osm_to_idf(model_b_osm, model_b_idf)

        # Resolve EPW weather file via Weather Provider
        epw_path = self.weather_provider.get_weather_file(
            context={"scenario": "initial_calibration", "key": "standard"}
        )

        # 2. Run / fetch Ground Truth (Model A or sensor data) reference dataset
        target_dir = self.results_dir / "target_run"
        df_target, time_target = self.run_target_model(calib_cfg, epw_path, target_dir)

        # 3. Run uncalibrated Baseline Model B
        baseline_dir = self.results_dir / "baseline_b_run"
        df_b_baseline, time_b_baseline = self.run_baseline_model_b(
            calib_cfg, model_b_idf, epw_path, baseline_dir
        )

        # 4. Delegate Parameter Calibration Optimization & Model B Evaluation to Module
        calib_dir = self.results_dir / "calibrated_b_run"
        module = self.create_module()
        model_path = model_b_osm if model_b_osm.exists() else model_b_idf

        calib_res = module.calibrate(
            calib_cfg=calib_cfg,
            df_target=df_target,
            epw_path=epw_path,
            model_path=model_path,
            results_dir=calib_dir,
        )

        best_params = calib_res["best_parameters"]
        best_fitness = calib_res["best_fitness"]
        history = calib_res.get("history", [])
        df_b_calibrated = calib_res["df_calibrated"]
        time_b_calibrated = calib_res["execution_time_s"]

        # Copy calibrated outputs / plots to main experiment directory if needed
        calib_history_src = calib_dir / "calibration_history.csv"
        if calib_history_src.exists() and not (self.results_dir / "calibration_history.csv").exists():
            shutil.copy(calib_history_src, self.results_dir / "calibration_history.csv")

        # 5. Generate Validation Metrics Reports
        eval_vars = self.get_evaluation_variables(calib_cfg)
        metrics_baseline = generate_metrics_report(
            df_target,
            df_b_baseline,
            variables=eval_vars,
            prefix="Baseline",
        )
        metrics_calibrated = generate_metrics_report(
            df_target,
            df_b_calibrated,
            variables=eval_vars,
            prefix="Calibrated",
        )

        df_metrics_all = pd.concat([metrics_baseline, metrics_calibrated], ignore_index=True)
        metrics_csv_path = self.results_dir / "accuracy_metrics.csv"
        df_metrics_all.to_csv(metrics_csv_path, index=False)
        print(f"Saved accuracy metrics report to {metrics_csv_path.resolve()}")

        # 6. Speedup & Computational Performance Analytics
        speedup = time_target / time_b_calibrated if time_b_calibrated > 0 else 1.0
        perf_csv_path = self.results_dir / "computational_performance.csv"
        df_perf = pd.DataFrame([
            {"Model": "Model A (Ground Truth)", "Execution_Time_s": time_target, "Speedup": 1.0},
            {"Model": "Model B (Digital Twin)", "Execution_Time_s": time_b_calibrated, "Speedup": speedup},
        ])
        df_perf.to_csv(perf_csv_path, index=False)

        # 7. Visual Plotting
        if history:
            plot_convergence(
                history,
                save_path=self.results_dir / "ga_convergence.png",
                title=f"{self.config.name} - Optimizer Convergence",
            )

        gt_label = getattr(getattr(self.config, "ground_truth", None), "name", "Model A") or "Model A"
        plot_computational_performance(
            time_target,
            time_b_calibrated,
            labels=(gt_label, "Model B (Calibrated)"),
            save_path=self.results_dir / "speedup_performance.png",
        )

        for var in eval_vars:
            if var in df_target.columns and var in df_b_calibrated.columns:
                series_dict = {
                    f"{gt_label}": df_target[var],
                    "Model B (Baseline)": df_b_baseline[var] if var in df_b_baseline.columns else None,
                    "Model B (Calibrated)": df_b_calibrated[var],
                }
                active_series = {k: v for k, v in series_dict.items() if v is not None}
                y_label = (self.config.y_labels or {}).get(var, var)
                plot_timeseries_comparison(
                    active_series,
                    title=f"Initial Calibration - {var.upper()} Validation",
                    ylabel=y_label,
                    save_path=self.results_dir / f"timeseries_{var}_comparison.png",
                )

        # 8. Export Synchronized Timeseries CSV
        ts_rows = []
        n_pts = min(len(df_target), len(df_b_calibrated))
        for i in range(n_pts):
            time_idx = int(df_target.iloc[i].get("TimeIndex", i + 1))
            total_mins = max(0, time_idx - 1) * 10
            day = (total_mins // 1440) + 1
            rem = total_mins % 1440
            time_str = f"D{day} {rem // 60:02d}:{rem % 60:02d}"
            row = {"step": time_idx, "time": time_str}
            for v in eval_vars:
                if v in df_target.columns:
                    row[f"{v}_a"] = round(float(df_target.iloc[i][v]), 3)
                if df_b_baseline is not None and v in df_b_baseline.columns:
                    row[f"{v}_before"] = round(float(df_b_baseline.iloc[i][v]), 3)
                    row[f"{v}_baseline"] = round(float(df_b_baseline.iloc[i][v]), 3)
                if v in df_b_calibrated.columns:
                    row[f"{v}_b"] = round(float(df_b_calibrated.iloc[i][v]), 3)
                    row[f"{v}_after"] = round(float(df_b_calibrated.iloc[i][v]), 3)
            ts_rows.append(row)
        if ts_rows:
            pd.DataFrame(ts_rows).to_csv(self.results_dir / "timeseries.csv", index=False)

        return {
            "best_parameters": best_params,
            "best_fitness": best_fitness,
            "speedup": speedup,
            "time_target": time_target,
            "time_calibrated": time_b_calibrated,
            "metrics": df_metrics_all.to_dict(orient="records"),
            "results_dir": str(self.results_dir),
        }
