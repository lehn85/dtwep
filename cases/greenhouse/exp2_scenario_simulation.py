from __future__ import annotations
import sys
from pathlib import Path
import openstudio

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from calibration_framework import (
    BaseScenarioSimulationExperiment,
    ScenarioItemConfig,
)
from cases.greenhouse.adapters import (
    apply_degradation_fault,
    apply_load_shift_schedule,
)


class GreenhouseScenarioSimulationExperiment(BaseScenarioSimulationExperiment):
    """Greenhouse Digital Twin Experiment 2: Multi-Scenario Testing & Cross-Model Validation."""

    def modify_target_model(
        self,
        model: openstudio.model.Model,
        scenario: ScenarioItemConfig,
    ) -> None:
        """Applies scenario modifications (schedules, degradation faults) to Target Model A."""
        load_shift = getattr(scenario, "load_shift", False) or scenario.parameters.get("load_shift", False)
        deg_fault = getattr(scenario, "degradation_fault", False) or scenario.parameters.get("degradation_fault", False)

        if load_shift:
            apply_load_shift_schedule(model)
        if deg_fault:
            apply_degradation_fault(model, infiltration_ach=2.5, pv_active_fraction=0.75)

    def modify_surrogate_model(
        self,
        model: openstudio.model.Model,
        scenario: ScenarioItemConfig,
    ) -> None:
        """Applies scenario modifications (schedules, load shifting) to Surrogate Model B."""
        load_shift = getattr(scenario, "load_shift", False) or scenario.parameters.get("load_shift", False)
        if load_shift:
            apply_load_shift_schedule(model)

    def postprocess_dataframe(self, df):
        """Greenhouse postprocessing: computes net grid power = grid_in - grid_out."""
        if df is not None and not df.empty:
            if "grid_in" in df.columns and "grid_out" in df.columns and "grid" not in df.columns:
                df["grid"] = df["grid_in"] - df["grid_out"]
        return df


def run_exp2():
    """Runs Experiment 2 with CLI arguments or default configuration."""
    default_config = Path(__file__).parent / "configs" / "exp2_scenario_simulation.yaml"
    GreenhouseScenarioSimulationExperiment.cli(default_config=default_config)


if __name__ == "__main__":
    run_exp2()


