from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import pandas as pd
import openstudio

from calibration_framework.schemas import (
    ScenarioSimulationExperimentConfig,
    ScenarioItemConfig,
    CalibrationConfig,
)
from calibration_framework.metrics import calc_metrics
from calibration_framework.plotting import (
    plot_timeseries_comparison,
    plot_scenario_metrics_summary,
)
from calibration_framework.modules.scenario_simulation import BaseScenarioSimulationModule
from calibration_framework.experiments.base import BaseExperiment


class BaseScenarioSimulationExperiment(BaseExperiment[ScenarioSimulationExperimentConfig]):
    """
    Experiment 2: Multi-Scenario Testing & Cross-Model Validation.
    Evaluates how accurately the calibrated digital twin generalizes against Model A across
    different operating conditions, delegating Model B simulations to BaseScenarioSimulationModule.
    """

    config_class = ScenarioSimulationExperimentConfig
    module_class = BaseScenarioSimulationModule

    def load_calibrated_parameters(self, calib_cfg: CalibrationConfig | None = None) -> list[float]:
        """Loads optimal parameter vector from prior calibration results."""
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
            print(f"Loaded calibrated parameters from {results_path.resolve()}: {thetas}")
            return thetas
        except Exception as e:
            raise RuntimeError(f"Failed to parse calibration results from '{results_path}': {e}") from e

    def modify_target_model(
        self,
        model: openstudio.openstudiomodel.Model,
        scenario: ScenarioItemConfig,
    ) -> None:
        """
        Hook for injecting scenario-specific modifications into High-Fidelity Model A.
        Subclasses can override to mutate schedules, operational profiles, or fault injections.
        """
        pass

    def modify_surrogate_model(
        self,
        model: openstudio.openstudiomodel.Model,
        scenario: ScenarioItemConfig,
    ) -> None:
        """
        Hook for injecting scenario-specific modifications into Reduced-Order Model B.
        Subclasses can override to align Model B with scenario conditions.
        """
        pass

    def run(self) -> dict[str, Any]:
        """Executes multi-scenario simulations and cross-validation comparisons."""
        calib_cfg = self.get_calibration_config()
        calibrated_thetas = self.load_calibrated_parameters(calib_cfg)

        model_b_cfg = self.config.model_b
        model_b_osm = self.resolve_path(
            getattr(model_b_cfg, "extended_osm_path", None)
            or getattr(model_b_cfg, "extended_osm", None)
            or getattr(model_b_cfg, "base_osm_path", None)
            or getattr(model_b_cfg, "base_osm", None)
            or "model_b.osm"
        )

        all_scenario_metrics: list[dict[str, Any]] = []
        module = self.create_module()
        # Ensure module uses experiment's modify_surrogate_model hook if overridden
        module.modify_surrogate_model = self.modify_surrogate_model

        for scenario in self.config.scenarios:
            print(f"\n=======================================================")
            print(f"--- Running Scenario: {scenario.name} ---")
            print(f"=======================================================")

            scenario_dir = self.results_dir / scenario.name.lower().replace(" ", "_").replace("-", "_")
            scenario_dir.mkdir(parents=True, exist_ok=True)

            weather_key = getattr(scenario, "weather_key", "standard") or "standard"
            epw_path = self.weather_provider.get_weather_file(
                context={"scenario": scenario, "weather_key": weather_key}
            )

            # 1. Run Scenario on Target Ground Truth via Ground Truth Provider
            target_scenario_dir = scenario_dir / "target_run"
            gt_data = self.ground_truth_provider.get_truth_data(
                context={
                    "target_dir": target_scenario_dir,
                    "epw_path": epw_path,
                    "output_mappings": calib_cfg.output_mappings,
                    "postprocess_fn": self.postprocess_dataframe,
                    "scenario": scenario,
                    "model_modifier_fn": lambda m: self.modify_target_model(m, scenario),
                }
            )
            df_target = gt_data.df

            # 2. Delegate Model B Scenario Simulation to Module
            model_b_scenario_dir = scenario_dir / "model_b_run"
            df_b = module.simulate_scenario(
                scenario=scenario,
                calib_cfg=calib_cfg,
                calibrated_thetas=calibrated_thetas,
                output_dir=model_b_scenario_dir,
                epw_path=epw_path,
                model_b_osm=model_b_osm,
            )

            # 3. Calculate Error Metrics for this scenario
            eval_vars = self.get_evaluation_variables(calib_cfg, getattr(scenario, "variables", None))
            for var in eval_vars:
                if var in df_target.columns and var in df_b.columns:
                    m = calc_metrics(df_target[var].values, df_b[var].values)
                    m["Scenario"] = scenario.name
                    m["Variable"] = var.upper()
                    all_scenario_metrics.append(m)

            # 4. Generate Timeseries Plots for this scenario
            gt_label = getattr(getattr(self.config, "ground_truth", None), "name", "Model A") or "Model A"
            for var in eval_vars:
                if var in df_target.columns and var in df_b.columns:
                    plot_timeseries_comparison(
                        {
                            f"{gt_label}": df_target[var],
                            "Model B (Calibrated)": df_b[var],
                        },
                        title=f"{scenario.name} - {var.upper()} Validation",
                        ylabel=(self.config.y_labels or {}).get(var, var),
                        save_path=scenario_dir / f"timeseries_{var}.png",
                    )

            # Export synchronized scenario timeseries CSV
            ts_rows = []
            n_pts = min(len(df_target), len(df_b))
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
                    if v in df_b.columns:
                        row[f"{v}_b"] = round(float(df_b.iloc[i][v]), 3)
                ts_rows.append(row)
            if ts_rows:
                pd.DataFrame(ts_rows).to_csv(scenario_dir / "timeseries.csv", index=False)

        # 5. Export Summary Metrics Table
        df_summary = pd.DataFrame(all_scenario_metrics)
        metrics_csv_path = self.results_dir / "scenarios_metrics_summary.csv"
        df_summary.to_csv(metrics_csv_path, index=False)
        print(f"\n[SUMMARY] Exported cross-scenario metrics to {metrics_csv_path.resolve()}")

        # 6. Generate Cross-Scenario Bar Chart Visualizations
        eval_vars = self.get_evaluation_variables(calib_cfg)
        for var in eval_vars:
            var_upper = var.upper()
            df_var = df_summary[df_summary["Variable"] == var_upper]
            if not df_var.empty and "CVRMSE (%)" in df_var.columns:
                plot_scenario_metrics_summary(
                    scenarios=df_var["Scenario"].tolist(),
                    cvrmse_values=df_var["CVRMSE (%)"].tolist(),
                    nmbe_values=df_var["NMBE (%)"].tolist() if "NMBE (%)" in df_var.columns else None,
                    metric_name=f"{var_upper} ASHRAE Metrics",
                    save_path=self.results_dir / f"scenarios_cvrmse_{var}.png",
                )

        return {
            "scenarios_evaluated": len(self.config.scenarios),
            "metrics": all_scenario_metrics,
            "results_dir": str(self.results_dir),
        }
