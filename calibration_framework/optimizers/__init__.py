"""
Optimization subpackage for the Building Energy Calibration Framework.
Provides abstract BaseOptimizer and concrete algorithm implementations.
"""

from __future__ import annotations
from typing import Any
from pathlib import Path

from calibration_framework.schemas import OptimizerConfig, ParameterConfig
from calibration_framework.optimizers.base import BaseOptimizer
from calibration_framework.optimizers.genetic_algorithm import GeneticAlgorithm

# Registry mapping algorithm string keys to optimizer classes
OPTIMIZER_REGISTRY: dict[str, type[BaseOptimizer]] = {
    "genetic_algorithm": GeneticAlgorithm,
    "ga": GeneticAlgorithm,
}


def register_optimizer(name: str, optimizer_cls: type[BaseOptimizer]) -> None:
    """Registers a custom optimizer class under the given algorithm name."""
    OPTIMIZER_REGISTRY[name.lower()] = optimizer_cls


def get_optimizer_class(name: str) -> type[BaseOptimizer]:
    """Resolves an optimizer class from its registered algorithm name."""
    key = name.lower()
    if key not in OPTIMIZER_REGISTRY:
        raise ValueError(
            f"Unknown optimizer algorithm '{name}'. Available: {list(OPTIMIZER_REGISTRY.keys())}"
        )
    return OPTIMIZER_REGISTRY[key]


def get_optimizer(
    algorithm_name: str | None = None,
    parameters: list[ParameterConfig] | None = None,
    config: OptimizerConfig | None = None,
    results_dir: str | Path | None = None,
    **kwargs: Any,
) -> BaseOptimizer:
    """
    Factory function to instantiate an optimizer based on name, configuration, or defaults.
    """
    cfg = config or OptimizerConfig()
    algo_name = algorithm_name or getattr(cfg, "algorithm", "genetic_algorithm")
    opt_cls = get_optimizer_class(algo_name)
    return opt_cls(
        parameters=parameters or [],
        config=cfg,
        results_dir=results_dir,
        **kwargs,
    )


__all__ = [
    "BaseOptimizer",
    "GeneticAlgorithm",
    "OPTIMIZER_REGISTRY",
    "register_optimizer",
    "get_optimizer_class",
    "get_optimizer",
]
