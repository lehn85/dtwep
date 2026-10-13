from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd

from calibration_framework.schemas import (
    PeriodicRecalibrationModuleConfig,
    CalibrationConfig,
)
from calibration_framework.modules.base_calibration import BaseCalibrationModule


class BasePeriodicRecalibrationModule(BaseCalibrationModule[PeriodicRecalibrationModuleConfig]):
    """
    Module 3: Operational Periodic / Continuous Recalibration of Model B.
    
    Executes:
      1. Loads prior/initial parameter vector for Model B.
      2. Loads new monitored/target dataset for the current operational period.
      3. Re-calibrates Model B parameters seeded with prior parameters.
      4. Evaluates Model B with recovered/recalibrated parameters.
      5. Exports recalibrated parameters, history, and convergence plot.
    """

    config_class = PeriodicRecalibrationModuleConfig

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

    def recalibrate(
        self,
        df_target: pd.DataFrame,
        calib_cfg: CalibrationConfig,
        initial_thetas: list[float] | None = None,
        epw_path: Path | None = None,
        model_b_osm: Path | None = None,
        results_dir: Path | None = None,
    ) -> dict[str, Any]:
        """
        Executes seeded recalibration optimization of Model B against df_target,
        evaluates post-recalibration Model B simulation, and returns results.
        """
        if initial_thetas is None:
            initial_thetas = self.load_calibrated_parameters(calib_cfg)

        if model_b_osm is None:
            model_b_idf, resolved_osm = self.resolve_model_b_paths()
            model_b_osm = resolved_osm if resolved_osm.exists() else model_b_idf

        if epw_path is None:
            epw_path = self.weather_provider.get_weather_file(
                context={"scenario": "recalibration", "key": "standard"}
            )

        return self.calibrate(
            calib_cfg=calib_cfg,
            df_target=df_target,
            epw_path=epw_path,
            initial_thetas=initial_thetas,
            model_path=model_b_osm,
            results_dir=results_dir or self.results_dir,
            run_label="recalibrated",
        )

    def run(self) -> dict[str, Any]:
        """Executes Model B periodic recalibration."""
        calib_cfg = self.get_calibration_config()
        initial_thetas = self.load_calibrated_parameters(calib_cfg)

        model_b_idf, model_b_osm = self.resolve_model_b_paths()
        model_path = model_b_osm if model_b_osm.exists() else model_b_idf

        epw_path = self.weather_provider.get_weather_file(
            context={"scenario": "recalibration", "key": "standard"}
        )

        # 1. Load current target/monitored dataset via Ground Truth Provider
        df_target = self.load_target_data(calib_cfg, epw_path)

        # 2. Recalibrate Model B
        return self.recalibrate(
            df_target=df_target,
            calib_cfg=calib_cfg,
            initial_thetas=initial_thetas,
            epw_path=epw_path,
            model_b_osm=model_path,
            results_dir=self.results_dir,
        )
