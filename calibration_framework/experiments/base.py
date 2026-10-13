from __future__ import annotations
import os
import sys
import argparse
from pathlib import Path
from typing import Any, TypeVar, Generic
import pandas as pd
import yaml

from calibration_framework.schemas import BaseExperimentConfig, CalibrationConfig
from calibration_framework.ground_truth import (
    BaseGroundTruthProvider,
    GroundTruthData,
    create_ground_truth_provider,
)
from calibration_framework.modules.base import BaseModule, find_workspace_root

TExpConfig = TypeVar("TExpConfig", bound=BaseExperimentConfig)


class BaseExperiment(BaseModule[TExpConfig]):
    """
    Abstract Base Class for Benchmark and Validation Experiments.
    Coordinates Ground Truth (Model A or physical data) vs Digital Twin (Model B)
    execution, computational benchmarking, error metrics calculation, and visual analytics.
    Delegates core digital twin simulation and calibration execution to corresponding BaseModule.
    """

    config_class: type[TExpConfig] = BaseExperimentConfig  # type: ignore
    module_class: type[BaseModule] | None = None

    def create_module(self, **kwargs: Any) -> BaseModule:
        """Instantiates and returns the underlying BaseModule instance configured with experiment parameters."""
        if self.module_class is None:
            raise ValueError(f"module_class is not defined on {self.__class__.__name__}")
        mod_kwargs: dict[str, Any] = {
            "config": self.config,
            "workspace_root": self.workspace_root,
            "force_rerun": self.force_rerun,
        }
        mod_kwargs.update(kwargs)
        module_inst = self.module_class(**mod_kwargs)
        # Inherit postprocess hook from experiment if overridden
        module_inst.postprocess_dataframe = self.postprocess_dataframe
        return module_inst
