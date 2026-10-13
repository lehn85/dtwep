from __future__ import annotations
import sys
from pathlib import Path

# Workspace root in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from calibration_framework import (
    BaseInitialCalibrationExperiment,
    translate_osm_to_idf,
)
from cases.greenhouse.model_transform import (
    extend_greenhouse_osm,
    simplify_to_model_b,
)


class GreenhouseInitialCalibrationExperiment(BaseInitialCalibrationExperiment):
    """Greenhouse Digital Twin Experiment 1: GA Accuracy, Convergence & Speedup Benchmark."""

    def prepare_models(self) -> None:
        """Transforms and extends OpenStudio models for the greenhouse (Model A and Model B)."""
        cfg = self.config
        gt = getattr(cfg, "ground_truth", None)
        base_a = self.resolve_path(gt.base_osm_path) if gt and getattr(gt, "base_osm_path", None) else None
        base_b = self.resolve_path(cfg.model_b.base_osm_path) if cfg.model_b.base_osm_path else None
        ext_a_osm = self.resolve_path(gt.extended_osm_path) if gt and getattr(gt, "extended_osm_path", None) else None
        ext_a_idf = self.resolve_path(gt.extended_idf_path) if gt and getattr(gt, "extended_idf_path", None) else None
        ext_b_osm = self.resolve_path(cfg.model_b.extended_osm_path) if cfg.model_b.extended_osm_path else None
        ext_b_idf = self.resolve_path(cfg.model_b.extended_idf_path) if cfg.model_b.extended_idf_path else None

        # 1. Simplify Model A base to create Model B base if needed
        if base_a and base_a.exists() and base_b and (not base_b.exists() or self.force_rerun):
            simplify_to_model_b(base_a, base_b)

        # 2. Extend Model B
        if base_b and base_b.exists() and ext_b_osm:
            ext_b_osm.parent.mkdir(parents=True, exist_ok=True)
            if not ext_b_osm.exists() or self.force_rerun:
                print("Extending Greenhouse Model B OpenStudio model...")
                extend_greenhouse_osm(base_b, ext_b_osm)
            if ext_b_idf and (not ext_b_idf.exists() or self.force_rerun):
                translate_osm_to_idf(ext_b_osm, ext_b_idf)

        # 3. Extend Model A if simulation ground truth
        if base_a and base_a.exists() and ext_a_osm:
            ext_a_osm.parent.mkdir(parents=True, exist_ok=True)
            if not ext_a_osm.exists() or self.force_rerun:
                extend_greenhouse_osm(base_a, ext_a_osm)
            if ext_a_idf and (not ext_a_idf.exists() or self.force_rerun):
                translate_osm_to_idf(ext_a_osm, ext_a_idf)

    def postprocess_dataframe(self, df):
        """Greenhouse postprocessing: computes net grid power = grid_in - grid_out."""
        if df is not None and not df.empty:
            if "grid_in" in df.columns and "grid_out" in df.columns and "grid" not in df.columns:
                df["grid"] = df["grid_in"] - df["grid_out"]
        return df


def run_exp1():
    """Runs Experiment 1 with CLI arguments or default configuration."""
    default_config = Path(__file__).parent / "configs" / "exp1_initial_calibration.yaml"
    GreenhouseInitialCalibrationExperiment.cli(default_config=default_config)


if __name__ == "__main__":
    run_exp1()


