from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd

from calibration_framework.schemas import CalibrationConfig
from calibration_framework.engine import CalibrationEngine


def main():
    parser = argparse.ArgumentParser(description="Generic Calibration Framework CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run calibration using a YAML configuration file")
    run_parser.add_argument("-c", "--config", required=True, help="Path to calibration YAML file")
    run_parser.add_argument("-t", "--target-csv", required=False, default=None, help="Path to target CSV data (if not generated)")

    args = parser.parse_args()

    if args.command == "run":
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)

        print(f"Loading configuration from {config_path}...")
        config = CalibrationConfig.from_yaml(config_path)

        target_df = None
        if args.target_csv:
            target_path = Path(args.target_csv)
            if not target_path.exists():
                print(f"Error: Target data CSV not found: {target_path}")
                sys.exit(1)
            target_df = pd.read_csv(target_path)

        engine = CalibrationEngine(config, target_data=target_df)
        if target_df is not None:
            best_params, best_fit = engine.run()
            print(f"Calibration completed! Best fitness: {best_fit:.6f}")
            print(f"Best parameters: {best_params}")
        else:
            print("Engine initialized successfully. (Target data required for execution)")


if __name__ == "__main__":
    main()
