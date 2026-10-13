from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import pandas as pd
import openstudio

from calibration_framework.schemas import (
    ScenarioSimulationModuleConfig,
    ScenarioItemConfig,
    CalibrationConfig,
)
from calibration_framework.model_adapter import (
    load_osm,
    translate_model_to_idf,
    OpenStudioModelAdapter,
)
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.modules.base import BaseModule


class BaseScenarioSimulationModule(BaseModule[ScenarioSimulationModuleConfig]):
    """
    Module 2: Operational Multi-Scenario Simulation & What-If Analysis on Model B.
    
    Executes:
      1. Loads calibrated parameter vector for Model B.
      2. For each scenario:
         - Applies scenario modifications to Model B (schedules, controls, weather).
         - Simulates Model B using EnergyPlusRunner.
         - Exports scenario simulation time-series results.
    """

    config_class = ScenarioSimulationModuleConfig

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

    def modify_surrogate_model(
        self,
        model: openstudio.openstudiomodel.Model,
        scenario: ScenarioItemConfig,
    ) -> None:
        """
        Hook for injecting scenario-specific modifications into Model B (e.g. schedules, setpoints).
        Subclasses can override to customize scenario behaviors.
        """
        pass

    # Alias for convenience
    modify_model_b = modify_surrogate_model

    def simulate_scenario(
        self,
        scenario: ScenarioItemConfig,
        calib_cfg: CalibrationConfig,
        calibrated_thetas: list[float],
        output_dir: Path,
        epw_path: Path,
        model_b_osm: Path | None = None,
    ) -> pd.DataFrame:
        """
        Applies calibrated parameters and scenario modifications to Model B,
        runs EnergyPlus simulation, and returns postprocessed DataFrame.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        if model_b_osm is None:
            model_b_cfg = self.config.model_b
            model_b_osm = self.resolve_path(
                getattr(model_b_cfg, "extended_osm", None) or getattr(model_b_cfg, "base_osm", "model_b.osm")
            )

        # 1. Prepare Model B with Calibrated Parameters & Scenario Mutations
        osm_b = load_osm(model_b_osm)
        adapter_b = OpenStudioModelAdapter()
        adapter_b.model = osm_b
        adapter_b.apply_parameters(calibrated_thetas, calib_cfg.parameters)

        # Apply scenario modifications
        self.modify_surrogate_model(osm_b, scenario)

        # Translate to IDF
        idf_b_path = output_dir / "in.idf"
        translate_model_to_idf(osm_b, idf_b_path)

        # 2. Run simulation
        runner = EnergyPlusRunner()
        df_b_raw, _ = runner.run(
            idf_path=idf_b_path,
            epw_path=epw_path,
            output_dir=output_dir,
            output_mappings=calib_cfg.output_mappings,
        )
        df_b = self.postprocess_dataframe(df_b_raw)
        sim_csv_path = output_dir / "simulation_results.csv"
        df_b.to_csv(sim_csv_path, index=False)
        return df_b

    def run(self) -> dict[str, Any]:
        """Executes multi-scenario simulations for Model B."""
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

        scenario_results: list[dict[str, Any]] = []

        for scenario in self.config.scenarios:
            print(f"\n=======================================================")
            print(f"--- Running Model B Scenario: {scenario.name} ---")
            print(f"=======================================================")

            scenario_dir = self.results_dir / scenario.name.lower().replace(" ", "_").replace("-", "_")
            weather_key = getattr(scenario, "weather_key", "standard") or "standard"
            epw_path = self.weather_provider.get_weather_file(
                context={"scenario": scenario, "weather_key": weather_key}
            )

            df_b = self.simulate_scenario(
                scenario=scenario,
                calib_cfg=calib_cfg,
                calibrated_thetas=calibrated_thetas,
                output_dir=scenario_dir,
                epw_path=epw_path,
                model_b_osm=model_b_osm,
            )

            scenario_results.append({
                "scenario": scenario.name,
                "output_dir": str(scenario_dir),
                "csv_path": str(scenario_dir / "simulation_results.csv"),
                "rows": len(df_b),
            })

        return {
            "scenarios_evaluated": len(self.config.scenarios),
            "results": scenario_results,
            "results_dir": str(self.results_dir),
        }

