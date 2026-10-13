from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from typing import Any, TypeVar
import pandas as pd

from calibration_framework.schemas import BaseModuleConfig, CalibrationConfig
from calibration_framework.engine import CalibrationEngine
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.model_adapter import translate_osm_to_idf
from calibration_framework.plotting import plot_convergence
from calibration_framework.modules.base import BaseModule

TConfig = TypeVar("TConfig", bound=BaseModuleConfig)


class BaseCalibrationModule(BaseModule[TConfig]):
    """
    Abstract Base Calibration Module for Model B Parameter Calibration.
    Encapsulates shared routines for:
      1. Resolving Model B paths (OSM / IDF) and translating if needed.
      2. Fetching Ground Truth observation target datasets.
      3. Setting up CalibrationEngine, applying optimizer overrides, and optional seeding.
      4. Executing optimization and post-calibration simulation validation.
      5. Exporting results, history, and convergence plots.
    """

    def resolve_model_b_paths(self) -> tuple[Path, Path]:
        """
        Resolves the IDF and OSM paths for Model B from module configuration.
        Returns a tuple: (model_b_idf, model_b_osm).
        """
        model_b_cfg = getattr(self.config, "model_b", None)
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
        return model_b_idf, model_b_osm

    def load_target_data(self, calib_cfg: CalibrationConfig, epw_path: Path) -> pd.DataFrame:
        """
        Loads the target reference dataset (ground truth) against which Model B will be calibrated.
        Retrieves reference observation timeseries via the configured Ground Truth Provider.
        """
        target_dir = self.results_dir / "target_data"
        gt_data = self.ground_truth_provider.get_truth_data(
            context={
                "target_dir": target_dir,
                "epw_path": epw_path,
                "output_mappings": calib_cfg.output_mappings,
                "postprocess_fn": self.postprocess_dataframe,
            }
        )
        return gt_data.df

    def calibrate(
        self,
        calib_cfg: CalibrationConfig,
        df_target: pd.DataFrame,
        epw_path: Path,
        initial_thetas: list[float] | None = None,
        model_path: Path | None = None,
        results_dir: Path | None = None,
        run_label: str = "calibrated",
    ) -> dict[str, Any]:
        """
        Runs calibration optimization of Model B against ground truth df_target,
        evaluates optimal calibrated model, and returns comprehensive calibration outputs.
        """
        out_dir = results_dir or self.results_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        if model_path is None:
            model_b_idf, model_b_osm = self.resolve_model_b_paths()
            model_path = model_b_osm if model_b_osm.exists() else model_b_idf

        # 1. Optimization Engine Setup & Execution
        print(f"\n--- Running Calibration Optimization Engine on Model B ({self.config.name}) ---")
        engine = CalibrationEngine(
            config=calib_cfg,
            ground_truth=df_target,
            model_adapter=None,
            runner=None,
            workspace_root=self.workspace_root,
        )

        # Override optimizer parameters from module config or CLI
        opt_overrides = getattr(self.config, "optimizer_overrides", None)
        if opt_overrides:
            if "population_size" in opt_overrides and hasattr(engine.optimizer, "population_size"):
                engine.optimizer.population_size = opt_overrides["population_size"]
            if "generations" in opt_overrides and hasattr(engine.optimizer, "generations"):
                engine.optimizer.generations = opt_overrides["generations"]
            if "mutation_rate" in opt_overrides and hasattr(engine.optimizer, "mutation_rate"):
                engine.optimizer.mutation_rate = opt_overrides["mutation_rate"]

        # Seed the optimizer with initial calibrated thetas if supported
        if initial_thetas and hasattr(engine.optimizer, "seed_population"):
            engine.optimizer.seed_population([initial_thetas])

        calib_results = engine.run(
            model_path=model_path,
            epw_path=epw_path,
            results_dir=out_dir,
        )

        best_params = calib_results["best_parameters"]
        best_fitness = calib_results["best_fitness"]
        history = calib_results.get("history", [])

        # 2. Evaluate Post-Calibration Model B with Optimal Parameters
        print(f"\n--- Running Calibrated Model B with Optimal Parameters: {best_params} ---")
        eval_run_dir = out_dir / f"{run_label}_run"
        eval_run_dir.mkdir(parents=True, exist_ok=True)

        adapter = engine.model_adapter
        adapter.load(model_path)
        adapter.apply_parameters(best_params, calib_cfg.parameters)
        calibrated_idf = eval_run_dir / "in.idf"
        adapter.save_idf(calibrated_idf)

        runner = EnergyPlusRunner()
        t0 = time.time()
        df_calibrated_raw, _ = runner.run(
            idf_path=calibrated_idf,
            epw_path=epw_path,
            output_dir=eval_run_dir,
            output_mappings=calib_cfg.output_mappings,
        )
        time_calibrated = time.time() - t0
        df_calibrated = self.postprocess_dataframe(df_calibrated_raw)
        df_calibrated.to_csv(out_dir / f"{run_label}_simulation_results.csv", index=False)

        # 3. Visual Plotting of Convergence
        if history:
            plot_convergence(
                history,
                save_path=out_dir / f"{run_label}_convergence.png",
                title=f"{self.config.name} - Optimizer Convergence",
            )
            if run_label.startswith("recalib"):
                plot_convergence(
                    history,
                    save_path=out_dir / "recalibration_convergence.png",
                    title=f"{self.config.name} - Optimizer Convergence",
                )
            if run_label != "ga":
                plot_convergence(
                    history,
                    save_path=out_dir / "ga_convergence.png",
                    title=f"{self.config.name} - Optimizer Convergence",
                )

        return {
            "best_parameters": best_params,
            "recalibrated_parameters": best_params,
            "initial_parameters": initial_thetas,
            "best_fitness": best_fitness,
            "history": history,
            "df_calibrated": df_calibrated,
            "df_post": df_calibrated,
            "execution_time_s": time_calibrated,
            "results_dir": str(out_dir),
            "calibrated_dir": str(eval_run_dir),
            "post_dir": str(eval_run_dir),
            "engine": engine,
        }
