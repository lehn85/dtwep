from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import Callable, Any
from pathlib import Path
import pandas as pd

from calibration_framework.schemas import ParameterConfig, OptimizerConfig


class BaseOptimizer(ABC):
    """
    Abstract base optimizer class for digital twin model calibration.
    Provides standard parameter bounds extraction, configuration handling, and execution interface.
    """

    def __init__(
        self,
        parameters: list[ParameterConfig],
        config: OptimizerConfig | None = None,
        results_dir: str | Path | None = None,
        **kwargs: Any,
    ):
        self.parameters = parameters
        self.param_names = [p.name for p in parameters]
        self.bounds = [p.bounds for p in parameters]
        self.config = config or OptimizerConfig()
        self.results_dir = str(results_dir) if results_dir else "results/calibration"
        self.history: list[dict[str, Any]] = []
        os.makedirs(self.results_dir, exist_ok=True)

    @abstractmethod
    def run(
        self,
        evaluate_fn: Callable[[list[float], int, int], tuple[float, float, pd.DataFrame]],
        initial_parameters: list[list[float]] | None = None,
        on_progress_callback: Callable[[int, list[float], float, list[float]], None] | None = None,
        **kwargs: Any,
    ) -> tuple[list[float], float]:
        """
        Executes the optimization process against the candidate evaluation function.

        Args:
            evaluate_fn: Callable taking (candidate_parameters, candidate_idx, iteration_no)
                         and returning (fitness, execution_time_s, results_dataframe).
            initial_parameters: Optional initial parameter vectors to seed the optimizer.
            on_progress_callback: Optional progress callback taking (iteration_no, best_params, best_fitness, history).
            **kwargs: Algorithm-specific parameters.

        Returns:
            tuple[list[float], float]: (best_parameters, best_fitness)
        """
        pass
