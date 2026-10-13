from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from typing import Callable, Any
import pandas as pd
import openstudio

from calibration_framework.schemas import (
    CalibrationConfig,
    ParameterConfig,
    OutputMappingConfig,
)
from calibration_framework.model_adapter import (
    OpenStudioModelAdapter,
    load_osm,
    translate_model_to_idf,
)
from calibration_framework.evaluator import ObjectiveEvaluator
from calibration_framework.runner import EnergyPlusRunner
from calibration_framework.optimizers import BaseOptimizer, get_optimizer


def evaluate_candidate_worker(
    candidate_params: list[float],
    thread_id: int,
    iteration: int,
    base_osm_path: str,
    epw_path: str,
    output_dir: str,
    parameters: list[ParameterConfig],
    output_mappings: list[OutputMappingConfig] | None,
    evaluator: ObjectiveEvaluator,
) -> tuple[float, float, pd.DataFrame]:
    """Top-level picklable worker function for evaluating a single candidate parameter vector in a process pool."""
    start_time = time.time()
    thread_dir = os.path.join(output_dir, f"gen_{iteration}", f"individual_{thread_id}")

    if os.path.exists(thread_dir):
        try:
            shutil.rmtree(thread_dir)
        except Exception:
            pass
    os.makedirs(thread_dir, exist_ok=True)

    try:
        # 1. Load base OSM model
        model = load_osm(base_osm_path)

        # 2. Substitute parameters via generic model adapter
        adapter = OpenStudioModelAdapter(parameters)
        adapter.apply_parameters(model, candidate_params)

        # 3. Translate modified OSM model to IDF
        candidate_idf_path = os.path.join(thread_dir, "candidate.idf")
        translate_model_to_idf(model, candidate_idf_path)

        # 4. Execute simulation runner
        runner = EnergyPlusRunner(
            candidate_idf_path,
            epw_path,
            thread_dir,
            output_mappings=output_mappings,
        )
        ret = runner.run(mute=True)
        if ret != 0:
            return -1e9, time.time() - start_time, pd.DataFrame()

        # 5. Extract simulation outputs
        df_est = runner.get_results()
        if df_est.empty:
            return -1e9, time.time() - start_time, df_est

        # Save individual output CSV
        df_est.to_csv(os.path.join(thread_dir, "results.csv"), index=False)

        # 6. Evaluate multi-objective fitness
        fitness, _ = evaluator.evaluate(df_est)
        exec_time = time.time() - start_time
        return float(fitness), exec_time, df_est

    except Exception as e:
        print(f"Error evaluating candidate in worker {thread_id}: {e}")
        return -1e9, time.time() - start_time, pd.DataFrame()


# Backward-compatibility alias
evaluate_chromosome_worker = evaluate_candidate_worker


class EvaluationWorker:
    """Top-level picklable callable worker for parallel candidate evaluation."""

    def __init__(
        self,
        base_osm_path: str,
        epw_path: str,
        output_dir: str,
        parameters: list[ParameterConfig],
        output_mappings: list[OutputMappingConfig] | None,
        evaluator: ObjectiveEvaluator,
    ):
        self.base_osm_path = base_osm_path
        self.epw_path = epw_path
        self.output_dir = output_dir
        self.parameters = parameters
        self.output_mappings = output_mappings
        self.evaluator = evaluator

    def __call__(
        self, candidate_params: list[float], idx: int, iteration: int
    ) -> tuple[float, float, pd.DataFrame]:
        return evaluate_candidate_worker(
            candidate_params=candidate_params,
            thread_id=idx,
            iteration=iteration,
            base_osm_path=self.base_osm_path,
            epw_path=self.epw_path,
            output_dir=self.output_dir,
            parameters=self.parameters,
            output_mappings=self.output_mappings,
            evaluator=self.evaluator,
        )


class CalibrationResult(dict):
    """
    Result dictionary from CalibrationEngine.
    Supports dictionary access (e.g. res["best_parameters"]), attribute access,
    and tuple unpacking: best_params, best_fitness = engine.run().
    """

    def __init__(
        self,
        best_parameters: list[float],
        best_fitness: float,
        history: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            best_parameters=best_parameters,
            best_fitness=best_fitness,
            history=history or [],
            **kwargs,
        )

    def __iter__(self):
        return iter((self["best_parameters"], self["best_fitness"]))

    @property
    def best_parameters(self) -> list[float]:
        return self["best_parameters"]

    @property
    def best_fitness(self) -> float:
        return self["best_fitness"]

    @property
    def history(self) -> list[dict[str, Any]]:
        return self["history"]


class CalibrationEngine:
    """
    High-level orchestrator for configuration-driven building model calibration.
    Decoupled from specific optimizer algorithms: accepts any BaseOptimizer instance, class,
    or resolves dynamically via configuration.
    """

    def __init__(
        self,
        config: CalibrationConfig,
        target_data: pd.DataFrame | None = None,
        optimizer: BaseOptimizer | type[BaseOptimizer] | None = None,
        ground_truth: pd.DataFrame | None = None,
        model_adapter: OpenStudioModelAdapter | None = None,
        runner: Any = None,
        workspace_root: Path | str | None = None,
        **kwargs: Any,
    ):
        self.config = config
        self.target_data = target_data if target_data is not None else ground_truth
        self.optimizer_override = optimizer
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.model_adapter = model_adapter or OpenStudioModelAdapter(config.parameters)
        self.evaluator: ObjectiveEvaluator | None = None
        if self.target_data is not None:
            self.evaluator = ObjectiveEvaluator(config.objectives, self.target_data)
        self.optimizer: BaseOptimizer | None = None

    def set_target_data(self, target_data: pd.DataFrame) -> None:
        self.target_data = target_data
        self.evaluator = ObjectiveEvaluator(self.config.objectives, target_data)

    def _resolve_path(self, path_val: str | Path | None) -> str:
        if not path_val:
            return ""
        p = Path(path_val)
        if not p.is_absolute():
            root = self.workspace_root or Path.cwd()
            p = (root / p).resolve()
        return str(p)

    def evaluate_candidate_worker(
        self,
        candidate_params: list[float],
        thread_id: int,
        iteration: int,
        base_osm_path: str,
        epw_path: str,
        output_dir: str,
    ) -> tuple[float, float, pd.DataFrame]:
        """Convenience method delegating to top-level worker function."""
        if self.evaluator is None:
            raise ValueError("Target data and evaluator not set.")
        return evaluate_candidate_worker(
            candidate_params=candidate_params,
            thread_id=thread_id,
            iteration=iteration,
            base_osm_path=base_osm_path,
            epw_path=epw_path,
            output_dir=output_dir,
            parameters=self.config.parameters,
            output_mappings=self.config.output_mappings,
            evaluator=self.evaluator,
        )

    # Backward-compatibility alias
    evaluate_chromosome_worker = evaluate_candidate_worker

    def resolve_optimizer(
        self,
        optimizer: BaseOptimizer | type[BaseOptimizer] | None = None,
        output_dir: str | Path | None = None,
    ) -> BaseOptimizer:
        """Resolves and instantiates the optimizer to use for calibration."""
        target_opt = optimizer or self.optimizer_override

        if isinstance(target_opt, BaseOptimizer):
            return target_opt
        elif isinstance(target_opt, type) and issubclass(target_opt, BaseOptimizer):
            return target_opt(
                parameters=self.config.parameters,
                config=self.config.optimizer,
                results_dir=output_dir or self.config.simulation.output_dir,
            )
        else:
            return get_optimizer(
                algorithm_name=self.config.optimizer.algorithm,
                parameters=self.config.parameters,
                config=self.config.optimizer,
                results_dir=output_dir or self.config.simulation.output_dir,
            )

    def run(
        self,
        target_data: pd.DataFrame | None = None,
        initial_population: list[list[float]] | None = None,
        initial_parameters: list[list[float]] | None = None,
        on_generation_callback: Callable[[int, list[float], float, list[float]], None] | None = None,
        on_progress_callback: Callable[[int, list[float], float, list[float]], None] | None = None,
        optimizer: BaseOptimizer | type[BaseOptimizer] | None = None,
        model_path: str | Path | None = None,
        epw_path: str | Path | None = None,
        results_dir: str | Path | None = None,
        **kwargs: Any,
    ) -> CalibrationResult:
        """
        Runs model calibration using the configured or injected optimizer.

        Args:
            target_data: Optional target dataset DataFrame (if not already set).
            initial_population: Seed candidate parameter vectors (alias for initial_parameters).
            initial_parameters: Seed candidate parameter vectors.
            on_generation_callback: Progress callback (alias for on_progress_callback).
            on_progress_callback: Progress callback.
            optimizer: Optional BaseOptimizer instance or subclass to use.
            model_path: Path to OSM model to calibrate.
            epw_path: Path to EPW weather file.
            results_dir: Path to directory for simulation outputs.

        Returns:
            CalibrationResult: (best_parameters, best_fitness, history)
        """
        if target_data is not None:
            self.set_target_data(target_data)

        if self.target_data is None or self.evaluator is None:
            raise ValueError("Target data must be provided before running calibration.")

        base_osm = self._resolve_path(model_path or self.config.simulation.base_osm_path)
        if not base_osm or not os.path.exists(base_osm):
            raise FileNotFoundError(f"Base OSM file not found: {base_osm}")

        epw = self._resolve_path(epw_path or self.config.simulation.epw_path)
        output_dir = self._resolve_path(results_dir or self.config.simulation.output_dir)
        os.makedirs(output_dir, exist_ok=True)

        active_optimizer = self.resolve_optimizer(optimizer=optimizer, output_dir=output_dir)
        self.optimizer = active_optimizer

        worker = EvaluationWorker(
            base_osm_path=base_osm,
            epw_path=epw,
            output_dir=output_dir,
            parameters=self.config.parameters,
            output_mappings=self.config.output_mappings,
            evaluator=self.evaluator,
        )

        seed_params = initial_parameters if initial_parameters is not None else initial_population
        progress_cb = on_progress_callback if on_progress_callback is not None else on_generation_callback

        best_params, best_fitness = active_optimizer.run(
            evaluate_fn=worker,
            initial_parameters=seed_params,
            on_progress_callback=progress_cb,
        )

        history = getattr(active_optimizer, "history", [])

        return CalibrationResult(
            best_parameters=best_params,
            best_fitness=best_fitness,
            history=history,
        )
