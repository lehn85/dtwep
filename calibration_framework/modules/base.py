from __future__ import annotations
import os
import sys
import argparse
from pathlib import Path
from typing import Any, TypeVar, Generic
import pandas as pd
import yaml

from calibration_framework.schemas import BaseModuleConfig, CalibrationConfig
from calibration_framework.optimizers import BaseOptimizer
from calibration_framework.ground_truth import (
    BaseGroundTruthProvider,
    GroundTruthData,
    create_ground_truth_provider,
)
from calibration_framework.weather import (
    BaseWeatherProvider,
    WeatherData,
    create_weather_provider,
)


def find_workspace_root(start_path: Path | None = None) -> Path:
    """Finds workspace root containing pyproject.toml, .git, or fallback to current dir."""
    cur = (start_path or Path.cwd()).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return cur


TConfig = TypeVar("TConfig", bound=BaseModuleConfig)


class BaseModule(Generic[TConfig]):
    """
    Abstract Base Class for Digital Twin Execution Modules in the Calibration Framework.
    Provides standard lifecycle management, path resolution, config loading, and CLI execution.
    """

    config_class: type[TConfig] = BaseModuleConfig  # type: ignore

    def __init__(
        self,
        config: str | Path | dict[str, Any] | TConfig,
        workspace_root: str | Path | None = None,
        force_rerun: bool = False,
    ):
        self.workspace_root = (
            Path(workspace_root).resolve() if workspace_root else find_workspace_root()
        )
        self.force_rerun = force_rerun

        # Load and parse module configuration
        if isinstance(config, (str, Path)):
            self.config_path = self.resolve_path(config)
            self.config: TConfig = self.config_class.from_yaml(self.config_path)  # type: ignore
        elif isinstance(config, dict):
            self.config_path = None
            self.config: TConfig = self.config_class.from_dict(config)  # type: ignore
        else:
            self.config_path = None
            self.config = config

        self.results_dir = self.resolve_path(self.config.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self._calib_cfg: CalibrationConfig | None = None
        self._ground_truth_provider: BaseGroundTruthProvider | None = None
        self._weather_provider: BaseWeatherProvider | None = None

    @property
    def ground_truth_provider(self) -> BaseGroundTruthProvider:
        """Lazily initializes and caches the reference ground truth provider."""
        if self._ground_truth_provider is None:
            gt_cfg = getattr(self.config, "ground_truth", None) or getattr(self.config, "model_a", None)
            if gt_cfg is None:
                raise ValueError("No ground_truth or model_a configuration specified in module configuration.")
            self._ground_truth_provider = create_ground_truth_provider(
                gt_cfg,
                workspace_root=self.workspace_root,
                force_rerun=self.force_rerun,
            )
        return self._ground_truth_provider

    @property
    def weather_provider(self) -> BaseWeatherProvider:
        """Lazily initializes and caches the weather data provider."""
        if self._weather_provider is None:
            w_cfg = getattr(self.config, "weather", None)
            self._weather_provider = create_weather_provider(
                w_cfg,
                workspace_root=self.workspace_root,
                cache_dir=self.results_dir / ".weather_cache",
            )
        return self._weather_provider

    def resolve_path(self, path: str | Path) -> Path:
        """Resolves a relative path against the workspace root."""
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.workspace_root / p).resolve()

    def get_calibration_config(self, calib_cfg_path: str | Path | None = None) -> CalibrationConfig:
        """Loads and caches the underlying CalibrationConfig."""
        if self._calib_cfg is None:
            if calib_cfg_path is None:
                calib_cfg_attr = getattr(self.config, "calibration_config", None)
                if not calib_cfg_attr:
                    raise ValueError("No calibration_config path specified in module configuration.")
                calib_cfg_path = calib_cfg_attr
            resolved = self.resolve_path(calib_cfg_path)
            self._calib_cfg = CalibrationConfig.from_yaml(resolved)
        return self._calib_cfg

    def get_evaluation_variables(
        self,
        calib_cfg: CalibrationConfig | None = None,
        scenario_vars: list[str] | None = None,
    ) -> list[str]:
        """Determines variable list for error metrics calculation and plotting."""
        if scenario_vars:
            return scenario_vars
        if self.config.target_variables:
            return self.config.target_variables
        if calib_cfg and calib_cfg.objectives:
            return [obj.variable for obj in calib_cfg.objectives]
        return ["temp", "pv"]

    def postprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Hook for case-specific DataFrame transformation (e.g. converting Wh to kW, derived fields).
        Subclasses can override this method. Default returns DataFrame as is.
        """
        return df

    def run(self) -> dict[str, Any]:
        """
        Executes the module workflow. Must be implemented by subclasses.
        Returns a dictionary of execution results and summary metrics.
        """
        raise NotImplementedError("Subclasses must implement run().")

    @classmethod
    def cli(cls, default_config: str | Path | None = None) -> None:
        """
        Standard Command Line Interface for running this module.
        Parses CLI arguments, instantiates the module class, and executes run().
        """
        parser = argparse.ArgumentParser(description=cls.__doc__ or f"Run {cls.__name__}")
        parser.add_argument(
            "--config",
            type=str,
            default=str(default_config) if default_config else None,
            help="Path to module YAML configuration file",
        )
        parser.add_argument(
            "--workspace-root",
            type=str,
            default=None,
            help="Root directory of the workspace (defaults to auto-discovery)",
        )
        parser.add_argument(
            "--force-model-a",
            "--force-rerun-target",
            dest="force_rerun",
            action="store_true",
            help="Force re-running target reference simulation (Ground Truth / Model A)",
        )
        parser.add_argument(
            "--pop-size",
            type=int,
            default=None,
            help="Override Genetic Algorithm population size",
        )
        parser.add_argument(
            "--generations",
            type=int,
            default=None,
            help="Override Genetic Algorithm number of generations",
        )
        parser.add_argument(
            "--mutation-rate",
            type=float,
            default=None,
            help="Override Genetic Algorithm mutation rate",
        )

        args, unknown = parser.parse_known_args()

        if not args.config:
            if default_config:
                args.config = str(default_config)
            else:
                parser.error("A configuration file must be specified via --config")

        # Load config dictionary to allow CLI overrides
        config_path = Path(args.config)
        workspace_root = (
            Path(args.workspace_root).resolve() if args.workspace_root else find_workspace_root()
        )
        resolved_cfg_path = config_path if config_path.is_absolute() else (workspace_root / config_path)
        
        with open(resolved_cfg_path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f)

        # Inject optimizer overrides into raw config if provided
        if any([args.pop_size, args.generations, args.mutation_rate is not None]):
            raw_cfg.setdefault("optimizer_overrides", {})
            if args.pop_size is not None:
                raw_cfg["optimizer_overrides"]["population_size"] = args.pop_size
            if args.generations is not None:
                raw_cfg["optimizer_overrides"]["generations"] = args.generations
            if args.mutation_rate is not None:
                raw_cfg["optimizer_overrides"]["mutation_rate"] = args.mutation_rate

        module = cls(
            config=raw_cfg,
            workspace_root=args.workspace_root,
            force_rerun=args.force_rerun,
        )
        # Store original config path if needed
        module.config_path = resolved_cfg_path
        
        results = module.run()
        print(f"\n[SUCCESS] {cls.__name__} completed successfully.")
        return results
