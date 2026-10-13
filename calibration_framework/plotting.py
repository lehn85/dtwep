from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Sequence
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_convergence(
    history_or_generations: Any,
    fitness_history: Sequence[float] | None = None,
    save_path: str | Path = "ga_convergence.png",
    title: str = "Optimization Fitness Convergence",
) -> None:
    """Plots the optimization fitness convergence curve over iterations / generations."""
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    y_best: list[float] = []
    y_mean: list[float] = []
    x_axis: list[int] = []

    if isinstance(history_or_generations, int) and fitness_history is not None:
        generations = history_or_generations
        y_best = list(fitness_history[:generations])
        x_axis = list(range(1, len(y_best) + 1))
    elif isinstance(history_or_generations, pd.DataFrame):
        df_hist = history_or_generations
        if "best_fitness" in df_hist.columns:
            y_best = df_hist["best_fitness"].tolist()
            if "mean_fitness" in df_hist.columns:
                y_mean = df_hist["mean_fitness"].tolist()
            x_col = "generation" if "generation" in df_hist.columns else ("iteration" if "iteration" in df_hist.columns else None)
            x_axis = df_hist[x_col].tolist() if x_col else list(range(1, len(y_best) + 1))
    elif isinstance(history_or_generations, (list, tuple)):
        items = list(history_or_generations)
        if items and isinstance(items[0], dict):
            y_best = [float(r["best_fitness"]) for r in items if "best_fitness" in r]
            y_mean = [float(r["mean_fitness"]) for r in items if "mean_fitness" in r]
            x_axis = [r.get("generation", r.get("iteration", i + 1)) for i, r in enumerate(items)]
        elif items and isinstance(items[0], (int, float)):
            y_best = [float(x) for x in items]
            x_axis = list(range(1, len(y_best) + 1))

    if not y_best:
        return

    plt.figure(figsize=(8, 5))
    plt.plot(
        x_axis,
        y_best,
        marker="o",
        linestyle="-",
        color="#1f77b4",
        linewidth=2,
        markersize=5,
        label="Best Fitness",
    )
    if y_mean and len(y_mean) == len(x_axis):
        plt.plot(
            x_axis,
            y_mean,
            linestyle="--",
            color="#ff7f0e",
            linewidth=1.5,
            alpha=0.75,
            label="Mean Fitness",
        )
        plt.legend(loc="lower right", fontsize=9)

    plt.title(title, fontsize=12, fontweight="bold")
    plt.xlabel("Iteration / Generation", fontsize=10)
    plt.ylabel("Fitness (-Loss)", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(str(save_path), dpi=300)
    plt.close()


def plot_computational_performance(
    time_a: float,
    time_b: float,
    speedup: float | None = None,
    save_path: str | Path = "computational_performance.png",
    title: str | None = None,
    labels: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Plots a bar chart comparing Model A and Model B execution times."""
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if speedup is None:
        speedup = time_a / max(time_b, 1e-3)

    labels_list = list(labels) if labels else ["Model A (HFM)", "Model B (ROM)"]
    times = [time_a, time_b]

    plt.figure(figsize=(6, 5))
    bars = plt.bar(labels_list, times, color=["#e74c3c", "#2ecc71"], width=0.55)
    plt.ylabel("Execution Time (seconds)", fontsize=10)
    default_title = f"Computational Performance (Speedup: {speedup:.2f}x)"
    plt.title(title or default_title, fontsize=11, fontweight="bold")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + max(times) * 0.01,
            f"{yval:.2f}s",
            va="bottom",
            ha="center",
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(str(save_path), dpi=300)
    plt.close()


DEFAULT_Y_LABELS: dict[str, str] = {
    "temp": "Temperature (°C)",
    "temperature": "Temperature (°C)",
    "humidity": "Relative Humidity (%)",
    "rel_humidity": "Relative Humidity (%)",
    "indoor_solar": "Solar Heat Gain (W)",
    "solar_gain": "Solar Heat Gain (W)",
    "t_glass": "Surface Temperature (°C)",
    "surf_temp": "Surface Temperature (°C)",
    "grid": "Net Grid Power (W)",
    "grid_in": "Grid Import (W)",
    "grid_out": "Grid Export (W)",
    "pv": "PV Power (W)",
    "soc": "State of Charge (%)",
    "load": "Load Power (W)",
    "cooling": "Cooling Rate (W)",
    "heating": "Heating Rate (W)",
    "co2": "CO2 Concentration (ppm)",
    "flow_rate": "Flow Rate (m3/s)",
    "chw_temp": "Chilled Water Temp (°C)",
}


def plot_timeseries_comparison(
    df_or_series_dict: pd.DataFrame | dict[str, pd.Series | Sequence[float]],
    df_before: pd.DataFrame | None = None,
    df_after: pd.DataFrame | None = None,
    n_points: int | None = None,
    save_path: str | Path = "timeseries_validation.png",
    columns: list[str] | None = None,
    y_labels: dict[str, str] | None = None,
    ylabel: str | None = None,
    timesteps_per_hour: int = 6,
    df_extra: pd.DataFrame | None = None,
    label_extra: str = "Model A (Before)",
    label_true: str = "Model A (Target)",
    label_before: str = "Model B (Baseline)",
    label_after: str = "Model B (Calibrated)",
    title_suffix: str = "",
    title: str | None = None,
) -> None:
    """
    Plots timeseries comparisons. Supports both:
    1. A dictionary mapping series labels to pd.Series / sequences:
       plot_timeseries_comparison({"Model A": s1, "Model B": s2}, title="...", ylabel="...", save_path="...")
    2. Multi-panel comparison across multiple DataFrames (df_true, df_before, df_after).
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Branch 1: Dictionary of named Series
    if isinstance(df_or_series_dict, dict):
        series_dict = df_or_series_dict
        valid_series = {k: pd.Series(v).dropna() for k, v in series_dict.items() if v is not None}
        if not valid_series:
            return

        min_len = min(len(s) for s in valid_series.values())
        points = min(n_points, min_len) if n_points is not None else min_len
        time_axis = [i / timesteps_per_hour for i in range(points)]

        plt.figure(figsize=(11, 4.5))
        palette = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#d97706", "#0891b2"]
        styles = ["-", "--", "-.", ":", "-"]

        for idx, (label, s) in enumerate(valid_series.items()):
            color = palette[idx % len(palette)]
            ls = styles[idx % len(styles)]
            plt.plot(
                time_axis,
                s.iloc[:points].values,
                label=label,
                color=color,
                linestyle=ls,
                linewidth=1.8 if idx == 0 else 1.5,
                alpha=0.9,
            )

        chart_title = title or f"Timeseries Validation {title_suffix}".strip()
        plt.title(chart_title, fontsize=11, fontweight="bold")
        plt.xlabel("Time (Hours)", fontsize=10)
        plt.ylabel(ylabel or "Value", fontsize=10)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend(loc="upper right", fontsize=8.5, framealpha=0.85)
        plt.tight_layout()
        plt.savefig(str(save_path), dpi=300)
        plt.close()
        return

    # Branch 2: Multi-DataFrame Comparison
    df_true = df_or_series_dict
    dfs = [df for df in [df_true, df_before, df_after, df_extra] if df is not None and not df.empty]
    if not dfs:
        return

    max_len = min(len(df) for df in dfs)
    if n_points is None or n_points > max_len:
        n_points = max_len

    if columns is None:
        common = set(df_true.columns)
        for df in dfs[1:]:
            common = common.intersection(set(df.columns))
        ignore = {"timeindex", "time", "date", "step", "index"}
        columns = [
            c for c in df_true.columns
            if c in common and c.lower() not in ignore and pd.api.types.is_numeric_dtype(df_true[c])
        ]

    columns = [c for c in columns if c in df_true.columns]
    if not columns:
        return

    y_label_map = {**DEFAULT_Y_LABELS, **(y_labels or {})}

    n_subplots = len(columns)
    fig, axs = plt.subplots(n_subplots, 1, figsize=(12, max(2.8 * n_subplots, 4)), sharex=True)
    if n_subplots == 1:
        axs = [axs]

    time_axis = [i / timesteps_per_hour for i in range(n_points)]

    for idx, col in enumerate(columns):
        ax = axs[idx]

        if df_extra is not None and col in df_extra.columns:
            ax.plot(
                time_axis,
                df_extra[col].iloc[:n_points],
                label=label_extra,
                color="gray",
                linestyle=":",
                alpha=0.85,
            )

        if col in df_true.columns:
            ax.plot(
                time_axis,
                df_true[col].iloc[:n_points],
                label=label_true,
                color="black",
                linewidth=1.8,
            )

        if df_before is not None and col in df_before.columns and df_before is not df_after:
            ax.plot(
                time_axis,
                df_before[col].iloc[:n_points],
                label=label_before,
                color="#e74c3c",
                linestyle="--",
                alpha=0.75,
            )

        if df_after is not None and col in df_after.columns:
            after_label = label_after if df_before is not df_after else "Model B (Simulated)"
            ax.plot(
                time_axis,
                df_after[col].iloc[:n_points],
                label=after_label,
                color="#2ecc71" if df_before is not df_after else "#3498db",
                linestyle="-",
                linewidth=1.4,
            )

        col_ylabel = ylabel or y_label_map.get(col, col.replace("_", " ").title())
        ax.set_ylabel(col_ylabel, fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.8)

    chart_title = title or f"Timeseries Validation {title_suffix}".strip()
    axs[0].set_title(chart_title, fontsize=11, fontweight="bold")
    axs[-1].set_xlabel("Time (Hours)", fontsize=10)

    plt.tight_layout()
    plt.savefig(str(save_path), dpi=300)
    plt.close()


def plot_scenario_metrics_summary(
    df_metrics_or_scenarios: pd.DataFrame | list[str] | None = None,
    save_path: str | Path = "scenarios_metrics_summary.png",
    metric: str = "CVRMSE (%)",
    title: str | None = None,
    scenarios: list[str] | None = None,
    cvrmse_values: list[float] | None = None,
    nmbe_values: list[float] | None = None,
    metric_name: str | None = None,
    **kwargs: Any,
) -> None:
    """Plots cross-scenario performance comparison charts. Supports both:
    1. Direct list of scenarios with CVRMSE and optional NMBE values.
    2. Consolidated metrics DataFrame with Scenario and Variable columns.
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Branch 1: Explicit scenario lists
    scen_list = scenarios if scenarios is not None else (df_metrics_or_scenarios if isinstance(df_metrics_or_scenarios, list) else None)
    if scen_list is not None and cvrmse_values is not None:
        c_vals = [float(v) for v in cvrmse_values]
        n_vals = [float(v) for v in nmbe_values] if nmbe_values is not None else None

        x = np.arange(len(scen_list))
        width = 0.35 if n_vals else 0.55

        fig, ax = plt.subplots(figsize=(max(8, 2 * len(scen_list)), 5))
        if n_vals:
            rects1 = ax.bar(x - width / 2, c_vals, width, label="CVRMSE (%)", color="#3b82f6", edgecolor="black", linewidth=0.5)
            rects2 = ax.bar(x + width / 2, n_vals, width, label="NMBE (%)", color="#f97316", edgecolor="black", linewidth=0.5)
            ax.axhline(30, color="#ef4444", linestyle="--", alpha=0.7, label="ASHRAE CVRMSE Limit (30%)")
            ax.axhline(10, color="#f59e0b", linestyle=":", alpha=0.7, label="ASHRAE NMBE Limit (±10%)")
            ax.axhline(-10, color="#f59e0b", linestyle=":", alpha=0.7)
        else:
            rects1 = ax.bar(x, c_vals, width, label="CVRMSE (%)", color="#3b82f6", edgecolor="black", linewidth=0.5)
            ax.axhline(30, color="#ef4444", linestyle="--", alpha=0.7, label="ASHRAE CVRMSE Limit (30%)")

        chart_title = title or metric_name or "Cross-Scenario Accuracy Metrics"
        ax.set_title(chart_title, fontsize=12, fontweight="bold")
        ax.set_ylabel("Error (%)", fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(scen_list, rotation=15, ha="right", fontsize=9, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.85)

        for rect in rects1:
            h = rect.get_height()
            ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        if n_vals and rects2 is not None:
            for rect in rects2:
                h = rect.get_height()
                ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 3 if h >= 0 else -10),
                            textcoords="offset points", ha="center", va="bottom" if h >= 0 else "top", fontsize=8, fontweight="bold")

        plt.tight_layout()
        plt.savefig(str(save_path), dpi=300)
        plt.close()
        return

    # Branch 2: DataFrame with Scenario and Variable columns
    if isinstance(df_metrics_or_scenarios, pd.DataFrame):
        df_metrics = df_metrics_or_scenarios
        if df_metrics.empty or "Scenario" not in df_metrics.columns or "Variable" not in df_metrics.columns:
            return

        target_metric = metric
        if target_metric not in df_metrics.columns:
            target_metric = "CVRMSE (%)" if "CVRMSE (%)" in df_metrics.columns else ("RMSE" if "RMSE" in df_metrics.columns else df_metrics.columns[2])

        pivot_df = df_metrics.pivot(index="Variable", columns="Scenario", values=target_metric)
        if pivot_df.empty:
            return

        fig, ax = plt.subplots(figsize=(11, 5.5))
        pivot_df.plot(kind="bar", ax=ax, width=0.75, colormap="tab10", edgecolor="black", linewidth=0.6)
        ax.set_title(title or f"Multi-Scenario Performance Comparison ({target_metric})", fontsize=12, fontweight="bold")
        ax.set_ylabel(target_metric, fontsize=10)
        ax.set_xlabel("Variable", fontsize=10)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.6)
        ax.legend(title="Scenario", framealpha=0.85, fontsize=8, title_fontsize=9)
        plt.tight_layout()
        plt.savefig(str(save_path), dpi=300)
        plt.close()

