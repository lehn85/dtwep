from __future__ import annotations
from pathlib import Path
from typing import Any, Literal
import yaml
from pydantic import BaseModel, Field, field_validator


class ParameterTarget(BaseModel):
    """Specification of how a parameter connects to an OpenStudio / building model object."""
    object_type: str = Field(..., description="OpenStudio model class or target category (e.g. SpaceInfiltrationDesignFlowRates)")
    name_filter: str | None = Field(default=None, description="Optional name/filter for targeted objects")
    setter: str = Field(..., description="Setter method name on the OpenStudio object, e.g. setAirChangesperHour")
    hook_name: str | None = Field(default=None, description="Optional custom Python hook identifier")


class ParameterConfig(BaseModel):
    """Definition of a tunable parameter in the calibration process."""
    name: str
    bounds: list[float] = Field(..., description="[min, max] range for parameter")
    default: float | None = None
    target: ParameterTarget | None = None
    description: str | None = None

    @field_validator("bounds")
    @classmethod
    def validate_bounds(cls, v: list[float]) -> list[float]:
        if len(v) != 2 or v[0] >= v[1]:
            raise ValueError(f"Bounds must be a list of two floats [min, max] with min < max, got {v}")
        return [float(x) for x in v]


class ObjectiveConfig(BaseModel):
    """Definition of an evaluation objective / loss component."""
    name: str
    column: str = Field(..., description="Target DataFrame column name to evaluate against")
    weight: float = Field(default=1.0, description="Loss weight for this objective")
    normalization: Literal["z_score", "range", "mean", "none"] = Field(
        default="z_score", description="Normalization strategy before error aggregation"
    )
    unit_conversion: str | None = Field(
        default="none", description="Optional conversion before error calculation"
    )
    metric: Literal["rmse", "mae"] = Field(
        default="rmse", description="Error metric to compute"
    )
    description: str | None = None


class OutputMappingConfig(BaseModel):
    """Declarative mapping from EnergyPlus SQL ReportData to a DataFrame column."""
    name: str = Field(..., description="Logical identifier for this output mapping")
    var_name: str = Field(..., description="Exact EnergyPlus ReportData Name (e.g. 'Zone Air Temperature')")
    key_value: str = Field(default="*", description="ReportData KeyValue pattern")
    key_value_filter: str | None = Field(default=None, description="Optional regex or substring filter on KeyValue")
    reporting_frequency: str = Field(default="Timestep", description="Reporting frequency")
    aggregation: Literal["none", "mean", "sum", "last", "first"] = Field(
        default="none", description="Aggregation method across multiple matching KeyValues per timestep"
    )
    scale_multiplier: float = Field(default=1.0, description="Multiplication factor (e.g. 1 / Joules for battery capacity)")
    offset: float = Field(default=0.0, description="Offset added after scaling")
    rename_to: str = Field(..., description="Target column name in the output DataFrame")


class SimulationConfig(BaseModel):
    """Energy simulation environment configuration."""
    base_osm_path: str | None = None
    base_idf_path: str | None = None
    epw_path: str
    output_dir: str = "results"
    timesteps_per_hour: int = 6
    run_period: list[int] | None = Field(
        default=None, description="[begin_month, begin_day, end_month, end_day]"
    )


class OptimizerConfig(BaseModel):
    """Optimization algorithm configuration."""
    algorithm: str = "genetic_algorithm"
    pop_size: int = 16
    generations: int = 10
    mutation_rate: float = 0.15
    elite_count: int = 1
    tournament_size: int = 3
    max_workers: int | None = None
    seed: int | None = None
    model_config = {"extra": "allow"}


class CalibrationConfig(BaseModel):
    """Complete, self-contained calibration specification."""
    name: str = "Calibration Experiment"
    description: str | None = None
    simulation: SimulationConfig
    parameters: list[ParameterConfig]
    objectives: list[ObjectiveConfig]
    output_mappings: list[OutputMappingConfig] = Field(default_factory=list)
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> CalibrationConfig:
        """Loads and validates a CalibrationConfig from a YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML content in {path}: expected a dictionary mapping")
        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationConfig:
        """Instantiates and validates a CalibrationConfig from a dictionary."""
        return cls(**data)

    def to_yaml(self, yaml_path: str | Path) -> None:
        """Serializes this configuration to a YAML file."""
        path = Path(yaml_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(exclude_none=True), f, default_flow_style=False, sort_keys=False)


class ModelDefinitionConfig(BaseModel):
    """Configuration for a specific simulation model (e.g. Model A high-fidelity or Model B reduced-order)."""
    base_osm_path: str | None = None
    extended_osm_path: str | None = None
    extended_idf_path: str | None = None
    output_dir: str | None = None
    model_config = {"extra": "allow"}


class GroundTruthConfig(BaseModel):
    """
    Configuration for ground truth / reference dataset provider.
    Supports:
      - Virtual simulation ('simulation' / 'model_a' / 'energyplus')
      - CSV / File dataset ('csv' / 'file' / 'physical' / 'sensor')
      - Remote API ('api' / 'remote_api' / 'rest')
    """
    type: str = "simulation"
    name: str = "Ground Truth"
    description: str | None = None
    # Simulation provider parameters (Model A)
    base_osm_path: str | None = None
    extended_osm_path: str | None = None
    extended_idf_path: str | None = None
    output_dir: str | None = None
    # CSV / File provider parameters
    data_path: str | None = None
    file_path: str | None = None
    timestamp_col: str = "TimeIndex"
    resample_rule: str | None = None
    # Remote API provider parameters
    api_url: str | None = None
    api_method: str = "GET"
    api_headers: dict[str, str] = Field(default_factory=dict)
    api_params: dict[str, Any] = Field(default_factory=dict)
    api_timeout: float = 30.0
    data_key: str | None = None
    model_config = {"extra": "allow"}



class WeatherConfig(BaseModel):
    """
    Configuration for weather boundary condition provider (EPW).
    Supports:
      - Static EPW files / multi-scenario map ('file' / 'epw' / 'static' / 'tmy')
      - Synthetic extreme / shifted weather ('synthetic' / 'modified' / 'what_if' / 'extreme')
      - Weather station measurement CSV ('station' / 'station_csv' / 'measurement' / 'aws')
      - Remote / Forecast API ('api' / 'remote_api' / 'forecast')
    """
    type: str = "file"
    name: str = "Weather Data"
    description: str | None = None
    # File provider parameters
    epw_path: str | None = None
    files: dict[str, str] = Field(default_factory=dict)
    # Synthetic modifier parameters
    base_epw: str | None = None
    temp_shift: float = 0.0
    dew_point_shift: float | None = None
    solar_multiplier: float = 1.0
    wind_multiplier: float = 1.0
    # Station / CSV provider parameters
    data_path: str | None = None
    base_template_epw: str | None = None
    column_mappings: dict[str, str] = Field(default_factory=dict)
    # Remote API provider parameters
    api_url: str | None = None
    api_headers: dict[str, str] = Field(default_factory=dict)
    api_params: dict[str, Any] = Field(default_factory=dict)
    api_timeout: float = 30.0
    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeatherConfig:
        if "type" not in data:
            if "epw_path" in data and len(data) == 1:
                return cls(type="file", epw_path=data["epw_path"])
            return cls(type="file", files=dict(data))
        return cls(**data)


class TimeseriesSeriesConfig(BaseModel):
    """Specification of a single time-series curve to plot."""
    key: str = Field(..., description="Suffix or identifier for column lookup (e.g. 'a', 'b', 'before', 'after')")
    label: str = Field(..., description="Human-readable display name for this series")
    color: str | None = Field(default=None, description="Hex or CSS color string (e.g. '#2563eb')")
    dash: str = Field(default="solid", description="Stroke style for the line ('solid', 'dashed', 'dotted')")
    model_config = {"extra": "allow"}


class TimeseriesDisplayConfig(BaseModel):
    """Configuration for interactive co-simulation timeseries chart."""
    enabled: bool = True
    title: str = "Co-Simulation Timeseries"
    allow_scenarios: bool = False
    allow_residual: bool = True
    series: list[TimeseriesSeriesConfig] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class PerformanceDisplayConfig(BaseModel):
    """Configuration for simulation execution time & computational speedup visualization."""
    enabled: bool = False
    title: str = "Simulation Speedup & Execution Time"
    compare_labels: dict[str, str] = Field(
        default_factory=lambda: {
            "ground_truth": "Ground Truth (Model A / P)",
            "model_a": "Model A (High-Fidelity)",
            "model_b": "Model B (Digital Twin)",
        }
    )
    model_config = {"extra": "allow"}


class FitnessDisplayConfig(BaseModel):
    """Configuration for optimizer loss / convergence curve visualization."""
    enabled: bool = False
    title: str = "Optimization Convergence"
    step_label: str = "Step / Generation"
    fitness_label: str = "Fitness Score"
    show_diversity: bool = False
    model_config = {"extra": "allow"}


class MetricsTableDisplayConfig(BaseModel):
    """Configuration for statistical validation metrics table."""
    enabled: bool = True
    title: str = "Statistical Validation Metrics (ASHRAE Guideline 14)"
    source: str = "metrics"
    filter_condition: str | None = None
    show_condition_column: bool = False
    show_ashrae_summary: bool = True
    model_config = {"extra": "allow"}


class OutputDisplayConfig(BaseModel):
    """Central container for all declarative visual output and chart configurations."""
    timeseries: TimeseriesDisplayConfig = Field(default_factory=TimeseriesDisplayConfig)
    performance: PerformanceDisplayConfig = Field(default_factory=PerformanceDisplayConfig)
    fitness: FitnessDisplayConfig = Field(default_factory=FitnessDisplayConfig)
    metrics_table: MetricsTableDisplayConfig = Field(default_factory=MetricsTableDisplayConfig)
    model_config = {"extra": "allow"}


class BaseModuleConfig(BaseModel):
    """Base schema for module specifications."""
    name: str = "Module"
    description: str | None = None
    results_dir: str = "results"
    target_variables: list[str] | None = Field(
        default=None, description="Optional explicit list of DataFrame variable columns to evaluate & plot"
    )
    y_labels: dict[str, str] | None = Field(
        default=None, description="Optional custom axis labels for plotted variables"
    )
    outputs: OutputDisplayConfig | None = Field(
        default=None, description="Declarative configuration of output graphs, charts, and metrics tables"
    )
    ground_truth: GroundTruthConfig | None = None
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    model_config = {"extra": "allow"}

    @classmethod
    def from_yaml(cls, yaml_path: str | Path):
        """Loads and validates a module config from a YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML content in {path}: expected a dictionary mapping")
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Instantiates and validates a module config from a dictionary."""
        return cls(**_resolve_module_dict(dict(data)))

    def to_yaml(self, yaml_path: str | Path) -> None:
        """Serializes this module configuration to a YAML file."""
        path = Path(yaml_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(exclude_none=True), f, default_flow_style=False, sort_keys=False)


def _resolve_ground_truth_dict(data: Any) -> Any:
    """Helper to adapt ground_truth, model_a, and legacy target_data_path / target_path into GroundTruthConfig dict."""
    if isinstance(data, dict):
        if "ground_truth" not in data:
            if "model_a" in data:
                gt_data = data["model_a"]
                if isinstance(gt_data, dict):
                    gt_dict = dict(gt_data)
                    if "type" not in gt_dict:
                        gt_dict["type"] = "simulation"
                    data["ground_truth"] = gt_dict
                else:
                    data["ground_truth"] = {"type": "simulation"}
            elif "target_data_path" in data and data["target_data_path"]:
                data["ground_truth"] = {
                    "type": "csv",
                    "data_path": data["target_data_path"],
                }
            elif "target_path" in data and data["target_path"]:
                data["ground_truth"] = {
                    "type": "csv",
                    "data_path": data["target_path"],
                }
    return data


def _resolve_module_dict(data: Any) -> Any:
    """Helper to adapt ground_truth, model_a, legacy paths, and weather configurations into structured schemas."""
    if isinstance(data, dict):
        _resolve_ground_truth_dict(data)
        if "weather" in data:
            w = data["weather"]
            if isinstance(w, str):
                data["weather"] = WeatherConfig(type="file", epw_path=w)
            elif isinstance(w, dict) and not isinstance(w, WeatherConfig):
                data["weather"] = WeatherConfig.from_dict(w)
    return data


class InitialCalibrationModuleConfig(BaseModuleConfig):
    """Configuration schema for Module 1: Operational Parameter Calibration of Model B."""
    ground_truth: GroundTruthConfig
    model_b: ModelDefinitionConfig
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    calibration_config: str = ""

    def __init__(self, **data: Any):
        super().__init__(**_resolve_module_dict(data))


class ScenarioItemConfig(BaseModel):
    """
    Configuration for an individual scenario in multi-scenario testing.
    Supports arbitrary custom operational parameters, schedule modifications, and fault flags.
    """
    name: str
    start_month: int = 1
    start_day: int = 1
    end_month: int = 1
    end_day: int = 7
    weather_key: str = "standard"
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Custom parameter dictionary for scenario mutation"
    )
    actions: dict[str, Any] = Field(
        default_factory=dict, description="Custom operational actions / schedules"
    )
    variables: list[str] | None = Field(
        default=None, description="Optional override of evaluation variables specific to this scenario"
    )
    load_shift: bool = False
    degradation_fault: bool = False
    model_config = {"extra": "allow"}


class ScenarioSimulationModuleConfig(BaseModuleConfig):
    """Configuration schema for Module 2: Operational Multi-Scenario Simulation on Model B."""
    model_b: ModelDefinitionConfig
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    calibration_results_path: str = ""
    calibration_config: str = ""
    scenarios: list[ScenarioItemConfig] = Field(default_factory=list)
    ground_truth: GroundTruthConfig | None = None

    def __init__(self, **data: Any):
        super().__init__(**_resolve_module_dict(data))


class RecalibrationEventConfig(BaseModel):
    """
    Generic configuration for perturbations, equipment/envelope degradation,
    sensor drift, or operational shifts that trigger model recalibration.
    """
    event_type: str = "perturbation"
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "allow"}


PerturbationConfig = RecalibrationEventConfig


class DegradationFaultConfig(RecalibrationEventConfig):
    """Configuration schema for physical degradation fault injection parameters."""
    event_type: str = "degradation_fault"
    infiltration_ach: float = 2.5
    pv_active_fraction: float = 0.75
    model_config = {"extra": "allow"}


class PeriodicRecalibrationModuleConfig(BaseModuleConfig):
    """Configuration schema for Module 3: Operational Periodic Recalibration of Model B."""
    ground_truth: GroundTruthConfig
    model_b: ModelDefinitionConfig
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    calibration_results_path: str = ""
    calibration_config: str = ""

    def __init__(self, **data: Any):
        super().__init__(**_resolve_module_dict(data))



# =========================================================================
# Experiment Schemas (Benchmark, Accuracy, Speedup, Cross-Model Validation)
# =========================================================================

class BaseExperimentConfig(BaseModuleConfig):
    """Base configuration schema for benchmark and validation experiments."""
    pass


class InitialCalibrationExperimentConfig(BaseExperimentConfig):
    """Configuration schema for Experiment 1: GA Accuracy, Convergence & Speedup Validation."""
    ground_truth: GroundTruthConfig
    model_b: ModelDefinitionConfig
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    calibration_config: str = ""

    def __init__(self, **data: Any):
        super().__init__(**_resolve_module_dict(data))

    @property
    def model_a(self) -> GroundTruthConfig:
        return self.ground_truth


class ScenarioSimulationExperimentConfig(BaseExperimentConfig):
    """Configuration schema for Experiment 2: Multi-Scenario Cross-Validation & Generalization."""
    ground_truth: GroundTruthConfig
    model_b: ModelDefinitionConfig
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    calibration_results_path: str = ""
    calibration_config: str = ""
    scenarios: list[ScenarioItemConfig] = Field(default_factory=list)

    def __init__(self, **data: Any):
        super().__init__(**_resolve_module_dict(data))

    @property
    def model_a(self) -> GroundTruthConfig:
        return self.ground_truth


class PeriodicRecalibrationExperimentConfig(BaseExperimentConfig):
    """Configuration schema for Experiment 3: Degradation Tracking & Recalibration Capability."""
    ground_truth: GroundTruthConfig
    model_b: ModelDefinitionConfig
    weather: WeatherConfig | dict[str, Any] = Field(default_factory=lambda: WeatherConfig(type="file"))
    calibration_results_path: str = ""
    calibration_config: str = ""
    event: RecalibrationEventConfig | dict[str, Any] | None = None
    fault: Any = None

    def __init__(self, **data: Any):
        super().__init__(**_resolve_module_dict(data))

    @property
    def model_a(self) -> GroundTruthConfig:
        return self.ground_truth

    def get_event_config(self) -> Any:
        """Returns the active event or fault configuration."""
        if self.event is not None:
            return self.event
        if self.fault is not None:
            return self.fault
        return DegradationFaultConfig()
