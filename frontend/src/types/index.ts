export type CaseType = 'virtual' | 'physical';

export interface MeasuredSensorInfo {
  key: string;
  label: string;
  unit: string;
  sensor_id?: string;
  is_measured?: boolean;
}

export interface TelemetryConfig {
  data_source?: string;
  measured_variables?: MeasuredSensorInfo[];
}

export interface CaseSummary {
  id: string;
  name: string;
  type?: CaseType;
  description: string;
  category: string;
  icon?: string;
  tags?: string[];
  location?: string;
  has_manifest?: boolean;
  modules?: ModuleInfo[];
  experiments?: ModuleInfo[];
  configs?: string[];
  telemetry?: TelemetryConfig;
}

export interface ModelPathInfo {
  path: string;
  exists: boolean;
}

export interface CaseDetail extends CaseSummary {
  available_configs: string[];
  models?: {
    model_a?: {
      name: string;
      description: string;
      base_osm?: string;
      extended_osm?: string;
      extended_idf?: string;
    };
    model_b?: {
      name: string;
      description: string;
      base_osm?: string;
      extended_osm?: string;
      extended_idf?: string;
    };
  };
  model_status?: Record<string, Record<string, ModelPathInfo>>;
  modules: ModuleInfo[];
  experiments: ModuleInfo[];
}

export interface ModuleInfo {
  id: string;
  name: string;
  description: string;
  config_file?: string;
  script?: string;
  results_dir?: string;
  badge?: string;
  color?: string;
  has_results?: boolean;
  has_metrics?: boolean;
  plot_count?: number;
  plots?: string[];
  is_calibration?: boolean;
}

export type ExperimentInfo = ModuleInfo;

export interface ConfigInfo {
  case_id: string;
  config_name: string;
  file_path: string;
  raw_yaml: string;
  parsed: Record<string, any>;
  error?: string;
}

export interface MetricRow {
  Module?: string;
  Experiment?: string;
  Scenario?: string;
  Variable: string;
  MAE: number;
  RMSE: number;
  "Max Error"?: number;
  "MAPE (%)"?: number;
  R2: number;
  "CVRMSE (%)": number;
  "NRMSE_range (%)"?: number;
  "NMBE (%)": number;
}

export interface PlotItem {
  name: string;
  title: string;
  url: string;
  size_bytes: number;
}

export interface CalibrationHistoryItem {
  generation: number;
  best_fitness: number;
  mean_fitness?: number;
  diversity?: number;
  mean_exec_time_s?: number;
}

export interface TimeSeriesPoint {
  step: number;
  time: string;
  temp_a?: number;
  temp_b?: number;
  pv_a?: number;
  pv_b?: number;
  soc_a?: number;
  soc_b?: number;
  grid_a?: number;
  grid_b?: number;
  humidity_a?: number;
  humidity_b?: number;
  indoor_solar_a?: number;
  indoor_solar_b?: number;
  t_glass_a?: number;
  t_glass_b?: number;
  [key: string]: any;
}

export interface VariableMeta {
  label: string;
  unit: string;
  full_label?: string;
  description?: string;
  icon?: string;
  is_measured?: boolean;
}

export interface ScenarioTimeSeries {
  name: string;
  title: string;
  points: TimeSeriesPoint[];
  variables: string[];
}

export interface TimeSeriesData {
  available: boolean;
  points: TimeSeriesPoint[];
  variables: string[];
  variable_meta?: Record<string, VariableMeta>;
  scenarios?: Record<string, ScenarioTimeSeries>;
  selected_scenario?: string;
}

export interface TimeseriesSeriesConfig {
  key: string;
  label: string;
  color?: string;
  dash?: 'solid' | 'dashed' | 'dotted' | string;
}

export interface TimeseriesDisplayConfig {
  enabled?: boolean;
  title?: string;
  allow_scenarios?: boolean;
  allow_residual?: boolean;
  series?: TimeseriesSeriesConfig[];
}

export interface PerformanceDisplayConfig {
  enabled?: boolean;
  title?: string;
  compare_labels?: {
    model_a?: string;
    model_b?: string;
  };
}

export interface FitnessDisplayConfig {
  enabled?: boolean;
  title?: string;
  step_label?: string;
  fitness_label?: string;
  show_diversity?: boolean;
}

export interface MetricsTableDisplayConfig {
  enabled?: boolean;
  title?: string;
  source?: 'metrics' | 'scenarios_metrics' | string;
  filter_condition?: string | null;
  show_condition_column?: boolean;
  show_ashrae_summary?: boolean;
}

export interface OutputDisplayConfig {
  timeseries?: TimeseriesDisplayConfig;
  performance?: PerformanceDisplayConfig;
  fitness?: FitnessDisplayConfig;
  metrics_table?: MetricsTableDisplayConfig;
}

export interface PerformanceData {
  time_a: number;
  time_b: number;
  speedup: number;
  unit?: string;
}

export interface ResultsData {
  case_id: string;
  mod_id?: string;
  exp_id: string;
  has_results: boolean;
  results_dir?: string;
  message?: string;
  metrics: MetricRow[];
  scenarios_metrics?: MetricRow[];
  plots: PlotItem[];
  calibration_history?: CalibrationHistoryItem[];
  performance?: PerformanceData;
  timeseries?: TimeSeriesData;
  mod_config?: Record<string, any>;
  exp_config?: Record<string, any>;
  outputs?: OutputDisplayConfig;
  variable_meta?: Record<string, VariableMeta>;
  models?: {
    model_a?: {
      name: string;
      description?: string;
    };
    model_b?: {
      name: string;
      description?: string;
    };
  };
  case_name?: string;
  mod_name?: string;
  exp_name?: string;
}

export interface LogMessage {
  id: string;
  timestamp: string;
  stream: 'stdout' | 'stderr' | 'system';
  text: string;
}

export interface GenerationUpdate {
  generation: number;
  best_chromosome: number[];
  best_fitness: number;
  history?: {
    generations: number[];
    best_fitness: number[];
    avg_fitness?: number[];
  };
}
