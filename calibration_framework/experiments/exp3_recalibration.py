from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any
import pandas as pd
import openstudio

from calibration_framework.schemas import (
    PeriodicRecalibrationExperimentConfig,
    CalibrationConfig,
)
from calibration_framework.model_adapter import (
    load_osm,
    translate_model_to_idf,
    OpenStudioModelAdapter,
)
from calibration_framework.engine import CalibrationEngine
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.metrics import generate_metrics_report
from calibration_framework.plotting import (
    plot_convergence,
    plot_timeseries_comparison,
)
from calibration_framework.modules.periodic_recalibration import BasePeriodicRecalibrationModule
from calibration_framework.experiments.base import BaseExperiment


class BasePeriodicRecalibrationExperiment(BaseExperiment[PeriodicRecalibrationExperimentConfig]):
    """
    Experiment 3: Physical Degradation Tracking & Periodic Recalibration Benchmark.
    Verifies the digital twin's adaptive recalibration capability when the physical asset
    experiences drift, structural degradation, operational shifts, or equipment fault injection,
    delegating the core recalibration optimization to BasePeriodicRecalibrationModule.
    """

    config_class = PeriodicRecalibrationExperimentConfig
    module_class = BasePeriodicRecalibrationModule

    def load_calibrated_parameters(self, calib_cfg: CalibrationConfig | None = None) -> list[float]:
        """Loads baseline calibrated parameter vector from prior calibration results."""
        res_path_str = getattr(self.config, "calibration_results_path", None)
        if not res_path_str:
            raise ValueError(
                "No 'calibration_results_path' specified in configuration. "
                "Please configure 'calibration_results_path' pointing to prior calibration results."
            )

        results_path = self.resolve_path(res_path_str)
        if not results_path.exists():
            raise FileNotFoundError(
                f"Calibration results file not found at '{results_path.resolve()}'. "
                f"Please ensure prior calibration experiment has run and check 'calibration_results_path' in your config."
            )

        try:
            df_history = pd.read_csv(results_path)
            if "best_fitness" not in df_history.columns:
                raise ValueError(f"'best_fitness' column not found in {results_path}.")
            best_row = df_history.loc[df_history["best_fitness"].idxmax()]
            if calib_cfg:
                thetas = [
                    float(best_row[f"best_{p.name}"]) if f"best_{p.name}" in best_row else (p.default or 1.0)
                    for p in calib_cfg.parameters
                ]
            else:
                param_cols = [c for c in df_history.columns if c.startswith("best_") and c != "best_fitness"]
                thetas = [float(best_row[c]) for c in param_cols]
            print(f"Loaded initial calibrated parameters from {results_path.resolve()}: {thetas}")
            return thetas
        except Exception as e:
            raise RuntimeError(f"Failed to parse calibration results from '{results_path}': {e}") from e

    def inject_target_perturbation(
        self,
        model: openstudio.openstudiomodel.Model,
        event_cfg: Any,
    ) -> None:
        """
        Hook for injecting degradation faults, drift, or structural changes into Ground Truth Model A.
        Subclasses must override this method.
        """
        pass

    def run(self) -> dict[str, Any]:
        """Executes the complete Experiment 3 workflow."""
        calib_cfg = self.get_calibration_config()
        initial_thetas = self.load_calibrated_parameters(calib_cfg)

        model_b_cfg = self.config.model_b
        model_b_osm = self.resolve_path(
            getattr(model_b_cfg, "extended_osm_path", None)
            or getattr(model_b_cfg, "extended_osm", None)
            or getattr(model_b_cfg, "base_osm_path", None)
            or getattr(model_b_cfg, "base_osm", None)
            or "model_b.osm"
        )

        epw_path = self.weather_provider.get_weather_file(
            context={"scenario": "recalibration", "key": "standard"}
        )

        event_cfg = self.config.get_event_config()

        # 1. Run Ground Truth (Model A or IoT) with Perturbation / Degradation Fault Injected
        print("\n--- Running Perturbed Ground Truth (Model A with Degradation / Drift) ---")
        perturbed_target_dir = self.results_dir / "target_perturbed_run"
        gt_data = self.ground_truth_provider.get_truth_data(
            context={
                "target_dir": perturbed_target_dir,
                "epw_path": epw_path,
                "output_mappings": calib_cfg.output_mappings,
                "postprocess_fn": self.postprocess_dataframe,
                "event_config": event_cfg,
                "model_modifier_fn": lambda m: self.inject_target_perturbation(m, event_cfg),
            }
        )
        df_target_perturbed = gt_data.df

        # 2. Run Model B with Pre-Recalibration Initial Parameters against Perturbed Ground Truth
        print(f"\n--- Running Model B with Initial Parameters {initial_thetas} against Perturbed Target ---")
        uncalibrated_dir = self.results_dir / "model_b_pre_recalibration"
        uncalibrated_dir.mkdir(parents=True, exist_ok=True)

        osm_b = load_osm(model_b_osm)
        adapter_b = OpenStudioModelAdapter()
        adapter_b.model = osm_b
        adapter_b.apply_parameters(initial_thetas, calib_cfg.parameters)

        idf_uncalibrated = uncalibrated_dir / "in.idf"
        translate_model_to_idf(osm_b, idf_uncalibrated)

        runner = EnergyPlusRunner()
        df_b_pre_raw, _ = runner.run(
            idf_path=idf_uncalibrated,
            epw_path=epw_path,
            output_dir=uncalibrated_dir,
            output_mappings=calib_cfg.output_mappings,
        )
        df_b_pre = self.postprocess_dataframe(df_b_pre_raw)

        # 3. Delegate Parameter Re-Calibration Optimization to Module
        recalib_dir = self.results_dir / "recalibration_run"
        module = self.create_module()

        recalib_res = module.recalibrate(
            df_target=df_target_perturbed,
            calib_cfg=calib_cfg,
            initial_thetas=initial_thetas,
            epw_path=epw_path,
            model_b_osm=model_b_osm,
            results_dir=recalib_dir,
        )

        recalibrated_thetas = recalib_res["recalibrated_parameters"]
        best_fitness = recalib_res["best_fitness"]
        history = recalib_res.get("history", [])
        df_b_post = recalib_res["df_post"]

        # Copy recalibration history to main results dir
        recalib_history_src = recalib_dir / "calibration_history.csv"
        if recalib_history_src.exists() and not (self.results_dir / "calibration_history.csv").exists():
            shutil.copy(recalib_history_src, self.results_dir / "calibration_history.csv")

        # 4. Generate Accuracy Comparison Reports (Pre- vs Post-Recalibration)
        eval_vars = self.get_evaluation_variables(calib_cfg)
        metrics_pre = generate_metrics_report(
            df_target_perturbed,
            df_b_pre,
            variables=eval_vars,
            prefix="Pre-Recalibration (Degraded)",
        )
        metrics_post = generate_metrics_report(
            df_target_perturbed,
            df_b_post,
            variables=eval_vars,
            prefix="Post-Recalibration (Recovered)",
        )

        df_metrics_all = pd.concat([metrics_pre, metrics_post], ignore_index=True)
        metrics_csv_path = self.results_dir / "recalibration_metrics.csv"
        df_metrics_all.to_csv(metrics_csv_path, index=False)
        print(f"Saved recalibration metrics report to {metrics_csv_path.resolve()}")

        # 5. Visual Plotting
        if history:
            plot_convergence(
                history,
                save_path=self.results_dir / "recalibration_convergence.png",
                title=f"{self.config.name} - Recalibration Convergence",
            )

        gt_label = getattr(getattr(self.config, "ground_truth", None), "name", "Model A") or "Model A"
        for var in eval_vars:
            if var in df_target_perturbed.columns and var in df_b_post.columns:
                series_dict = {
                    f"{gt_label} (Perturbed Ground Truth)": df_target_perturbed[var],
                    "Model B (Pre-Recalibration)": df_b_pre[var] if var in df_b_pre.columns else None,
                    "Model B (Post-Recalibration)": df_b_post[var],
                }
                active_series = {k: v for k, v in series_dict.items() if v is not None}
                y_label = (self.config.y_labels or {}).get(var, var)
                plot_timeseries_comparison(
                    active_series,
                    title=f"Periodic Recalibration - {var.upper()} Tracking",
                    ylabel=y_label,
                    save_path=self.results_dir / f"recalibration_timeseries_{var}.png",
                )

        # 6. Export Synchronized Timeseries CSV
        ts_rows = []
        n_pts = min(len(df_target_perturbed), len(df_b_post))
        for i in range(n_pts):
            time_idx = int(df_target_perturbed.iloc[i].get("TimeIndex", i + 1))
            total_mins = max(0, time_idx - 1) * 10
            day = (total_mins // 1440) + 1
            rem = total_mins % 1440
            time_str = f"D{day} {rem // 60:02d}:{rem % 60:02d}"
            row = {"step": time_idx, "time": time_str}
            for v in eval_vars:
                if v in df_target_perturbed.columns:
                    row[f"{v}_a"] = round(float(df_target_perturbed.iloc[i][v]), 3)
                if df_b_pre is not None and v in df_b_pre.columns:
                    row[f"{v}_before"] = round(float(df_b_pre.iloc[i][v]), 3)
                if v in df_b_post.columns:
                    row[f"{v}_b"] = round(float(df_b_post.iloc[i][v]), 3)
                    row[f"{v}_after"] = round(float(df_b_post.iloc[i][v]), 3)
            ts_rows.append(row)
        if ts_rows:
            pd.DataFrame(ts_rows).to_csv(self.results_dir / "timeseries.csv", index=False)

        return {
            "initial_parameters": initial_thetas,
            "recalibrated_parameters": recalibrated_thetas,
            "best_fitness": best_fitness,
            "metrics": df_metrics_all.to_dict(orient="records"),
            "results_dir": str(self.results_dir),
        }
