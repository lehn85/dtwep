from __future__ import annotations
import numpy as np
import pandas as pd
from calibration_framework.schemas import ObjectiveConfig


class ObjectiveEvaluator:
    """
    Generic multi-objective evaluator for calibration algorithms.
    Supports Z-score, range, mean, and weighted multi-metric loss aggregation (RMSE, MAE).
    """

    def __init__(self, objectives: list[ObjectiveConfig], target_data: pd.DataFrame, epsilon: float = 1e-5):
        self.objectives = objectives
        self.target_data = target_data
        self.epsilon = epsilon

        # Precompute target statistics for normalization
        self.stats: dict[str, dict[str, float]] = {}
        for obj in self.objectives:
            col = obj.column
            if col not in target_data.columns:
                continue

            series = target_data[col].astype(float).values

            self.stats[col] = {
                "mean": float(np.mean(series)),
                "std": float(np.std(series)) + epsilon,
                "min": float(np.min(series)),
                "max": float(np.max(series)),
                "range": float(np.max(series) - np.min(series)) + epsilon,
            }

    def evaluate(self, estimated_data: pd.DataFrame) -> tuple[float, dict[str, float]]:
        """
        Evaluates simulation results against target data.
        Returns:
            fitness: Negative weighted loss (higher is better).
            metrics_breakdown: Dictionary of computed error per objective.
        """
        if estimated_data.empty or len(estimated_data) != len(self.target_data):
            return -1e9, {obj.name: 1e9 for obj in self.objectives}

        total_loss = 0.0
        breakdown: dict[str, float] = {}

        for obj in self.objectives:
            col = obj.column
            if col not in self.target_data.columns or col not in estimated_data.columns:
                continue

            y_true = self.target_data[col].astype(float).values
            y_pred = estimated_data[col].astype(float).values

            stat = self.stats[col]

            # Apply normalization
            if obj.normalization == "z_score":
                y_t_norm = (y_true - stat["mean"]) / stat["std"]
                y_p_norm = (y_pred - stat["mean"]) / stat["std"]
            elif obj.normalization == "range":
                y_t_norm = (y_true - stat["min"]) / stat["range"]
                y_p_norm = (y_pred - stat["min"]) / stat["range"]
            elif obj.normalization == "mean":
                denom = abs(stat["mean"]) if abs(stat["mean"]) > self.epsilon else 1.0
                y_t_norm = y_true / denom
                y_p_norm = y_pred / denom
            else:
                y_t_norm = y_true
                y_p_norm = y_pred

            # Calculate error metric
            if obj.metric == "mae":
                err = float(np.mean(np.abs(y_t_norm - y_p_norm)))
            else:  # rmse default
                err = float(np.sqrt(np.mean((y_t_norm - y_p_norm) ** 2)))

            breakdown[obj.name] = err
            total_loss += obj.weight * err

        fitness = -total_loss
        return fitness, breakdown
