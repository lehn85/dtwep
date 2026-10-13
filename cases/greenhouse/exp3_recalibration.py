from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
import openstudio

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from calibration_framework import (
    BasePeriodicRecalibrationExperiment,
    CalibrationConfig,
)
from cases.greenhouse.adapters import apply_degradation_fault


class GreenhouseRecalibrationExperiment(BasePeriodicRecalibrationExperiment):
    """Greenhouse Digital Twin Experiment 3: Physical Degradation Tracking & Recalibration Capability Benchmark."""

    def inject_target_perturbation(
        self,
        model: openstudio.model.Model,
        event_cfg: Any,
    ) -> None:
        """Injects physical infiltration leak and PV degradation faults into greenhouse Model A."""
        params = getattr(event_cfg, "parameters", {}) if hasattr(event_cfg, "parameters") else {}
        if isinstance(event_cfg, dict):
            infil = event_cfg.get("infiltration_ach", event_cfg.get("parameters", {}).get("infiltration_ach", 2.5))
            pv_frac = event_cfg.get("pv_active_fraction", event_cfg.get("parameters", {}).get("pv_active_fraction", 0.75))
        else:
            infil = getattr(event_cfg, "infiltration_ach", params.get("infiltration_ach", 2.5))
            pv_frac = getattr(event_cfg, "pv_active_fraction", params.get("pv_active_fraction", 0.75))

        apply_degradation_fault(
            model,
            infiltration_ach=float(infil),
            pv_active_fraction=float(pv_frac),
        )

    def postprocess_dataframe(self, df):
        """Greenhouse postprocessing: computes net grid power = grid_in - grid_out."""
        if df is not None and not df.empty:
            if "grid_in" in df.columns and "grid_out" in df.columns and "grid" not in df.columns:
                df["grid"] = df["grid_in"] - df["grid_out"]
        return df


def run_exp3():
    """Runs Experiment 3 with CLI arguments or default configuration."""
    default_config = Path(__file__).parent / "configs" / "exp3_recalibration.yaml"
    GreenhouseRecalibrationExperiment.cli(default_config=default_config)


if __name__ == "__main__":
    run_exp3()


