from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd

from calibration_framework.schemas import InitialCalibrationModuleConfig, CalibrationConfig
from calibration_framework.model_adapter import translate_osm_to_idf
from calibration_framework.modules.base_calibration import BaseCalibrationModule


class BaseInitialCalibrationModule(BaseCalibrationModule[InitialCalibrationModuleConfig]):
    """
    Module 1: Operational Parameter Calibration of Model B.
    
    Executes:
      1. Model B preparation / geometry preprocessing hook.
      2. Target dataset resolution via Ground Truth Provider.
      3. Parameter Calibration Optimization via CalibrationEngine for Model B.
      4. Evaluation of Model B with optimal calibrated parameters.
      5. Export of calibrated model, optimal parameters, history, and convergence plot.
    """

    config_class = InitialCalibrationModuleConfig

    def prepare_models(self) -> None:
        """
        Hook for case-specific model geometry preprocessing.
        Subclasses can override this method to prepare Model B geometry.
        """
        pass

    def run(self) -> dict[str, Any]:
        """Executes the Model B parameter calibration workflow."""
        calib_cfg = self.get_calibration_config()

        # 1. Prepare / preprocess model geometry
        self.prepare_models()

        # Resolve paths
        model_b_idf, model_b_osm = self.resolve_model_b_paths()

        # Auto-translate OSM to IDF if needed
        if model_b_osm.exists() and (not model_b_idf.exists() or self.force_rerun):
            print(f"Translating Model B OpenStudio to IDF: {model_b_osm.name} -> {model_b_idf.name}")
            translate_osm_to_idf(model_b_osm, model_b_idf)

        # Resolve EPW weather file via Weather Provider
        epw_path = self.weather_provider.get_weather_file(
            context={"scenario": "initial_calibration", "key": "standard"}
        )

        # 2. Load Target Reference Dataset via Ground Truth Provider
        df_target = self.load_target_data(calib_cfg, epw_path)
        model_path = model_b_osm if model_b_osm.exists() else model_b_idf

        # 3. Perform Calibration & Post-Calibration Evaluation
        return self.calibrate(
            calib_cfg=calib_cfg,
            df_target=df_target,
            epw_path=epw_path,
            model_path=model_path,
            results_dir=self.results_dir,
            run_label="calibrated",
        )
