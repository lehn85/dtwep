import React, { useState, useMemo, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
} from 'recharts';
import {
  TrendingUp,
  BarChart2,
  Activity,
  Zap,
  Layers,
  ArrowUpDown,
  Calendar,
  Timer,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import {
  GenerationUpdate,
  MetricRow,
  CalibrationHistoryItem,
  TimeSeriesData,
  TimeSeriesPoint,
  CaseDetail,
  ExperimentInfo,
  VariableMeta,
  OutputDisplayConfig,
  PerformanceData,
  TimeseriesSeriesConfig,
} from '../types';
import { useTheme } from '../context/ThemeContext';
import { resolveVariableConfig, ResolvedSignalConfig } from '../utils/variableConfig';

interface ChartsPanelProps {
  generationHistory?: GenerationUpdate[];
  calibrationHistory?: CalibrationHistoryItem[];
  timeseriesData?: TimeSeriesData;
  metrics?: MetricRow[];
  scenariosMetrics?: MetricRow[];
  isRunning?: boolean;
  caseDetail?: CaseDetail | null;
  selectedExp?: ExperimentInfo;
  expConfig?: Record<string, any>;
  outputs?: OutputDisplayConfig;
  performance?: PerformanceData;
  variableMeta?: Record<string, VariableMeta>;
  models?: {
    model_a?: { name: string; description?: string };
    model_b?: { name: string; description?: string };
  };
}

type ChartTab = 'timeseries' | 'convergence' | 'performance' | 'metrics_bar' | 'scenarios';
type TimeHorizon = '24h' | '48h' | '7d' | 'all';

export const ChartsPanel: React.FC<ChartsPanelProps> = ({
  generationHistory = [],
  calibrationHistory = [],
  timeseriesData,
  metrics = [],
  scenariosMetrics = [],
  caseDetail,
  selectedExp,
  expConfig,
  outputs,
  performance,
  variableMeta,
  models,
}) => {
  const { isDark } = useTheme();

  // ---------------------------------------------------------------------------
  // 1. Declarative Outputs Configuration Resolution
  // ---------------------------------------------------------------------------
  const outputsConfig: OutputDisplayConfig = useMemo(() => {
    return outputs || expConfig?.outputs || {};
  }, [outputs, expConfig]);

  const isPhysical = caseDetail?.type === 'physical';

  const modelAName =
    models?.model_a?.name ||
    caseDetail?.models?.model_a?.name ||
    (isPhysical ? 'Physical Telemetry (Sensors)' : 'Model A (Baseline / Virtual World)');
  const modelBName =
    models?.model_b?.name ||
    caseDetail?.models?.model_b?.name ||
    (isPhysical ? 'Digital Twin Model (Forecast)' : 'Model B (Digital Twin / Calibrated)');

  const yLabelsConfig = useMemo(() => {
    return expConfig?.y_labels || {};
  }, [expConfig]);

  const combinedVarMeta = useMemo(() => {
    return {
      ...(timeseriesData?.variable_meta || {}),
      ...(variableMeta || {}),
    };
  }, [timeseriesData, variableMeta]);

  // Dynamic series configuration from outputs or sensible defaults
  const configuredSeries = useMemo<TimeseriesSeriesConfig[]>(() => {
    if (outputsConfig.timeseries?.series && outputsConfig.timeseries.series.length > 0) {
      return outputsConfig.timeseries.series;
    }
    return [
      { key: 'a', label: modelAName, color: isPhysical ? '#10b981' : '#2563eb', dash: 'solid' },
      { key: 'b', label: modelBName, color: '#8b5cf6', dash: 'dashed' },
    ];
  }, [outputsConfig, modelAName, modelBName, isPhysical]);

  // Tab availability derived declaratively from outputs config
  const isTimeseriesTabEnabled = outputsConfig.timeseries?.enabled !== false;
  const isConvergenceTabEnabled = outputsConfig.fitness ? outputsConfig.fitness.enabled === true : false;
  const isPerformanceTabEnabled = outputsConfig.performance ? outputsConfig.performance.enabled === true : false;
  const isMetricsBarTabEnabled =
    !outputsConfig.metrics_table?.filter_condition &&
    metrics.length > 0 &&
    metrics.some((m) => {
      const exp = String(m.Experiment || '').toLowerCase();
      return exp.includes('before') || exp.includes('baseline') || exp.includes('pre');
    });
  const isScenariosBarTabEnabled =
    outputsConfig.timeseries?.allow_scenarios === true &&
    Boolean(
      (scenariosMetrics && scenariosMetrics.length > 0) ||
      (timeseriesData?.scenarios && Object.keys(timeseriesData.scenarios).length > 0)
    ) &&
    !outputsConfig.fitness?.enabled;

  // Tab State
  const [chartView, setChartView] = useState<ChartTab>('timeseries');

  // Auto-switch to available tab if current becomes invalid
  useEffect(() => {
    if (chartView === 'timeseries' && !isTimeseriesTabEnabled) {
      if (isConvergenceTabEnabled) setChartView('convergence');
      else if (isPerformanceTabEnabled) setChartView('performance');
    }
    if (chartView === 'convergence' && !isConvergenceTabEnabled) {
      setChartView('timeseries');
    }
    if (chartView === 'performance' && !isPerformanceTabEnabled) {
      setChartView('timeseries');
    }
    if (chartView === 'metrics_bar' && !isMetricsBarTabEnabled) {
      setChartView('timeseries');
    }
    if (chartView === 'scenarios' && !isScenariosBarTabEnabled) {
      setChartView('timeseries');
    }
  }, [
    chartView,
    isTimeseriesTabEnabled,
    isConvergenceTabEnabled,
    isPerformanceTabEnabled,
    isMetricsBarTabEnabled,
    isScenariosBarTabEnabled,
  ]);

  // Timeseries State
  const [selectedSignal, setSelectedSignal] = useState<string>('');
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [timeHorizon, setTimeHorizon] = useState<TimeHorizon>('24h');
  const [showResidual, setShowResidual] = useState<boolean>(false);

  // Calibration Bar Chart State
  const [selectedMetricChoice, setSelectedMetricChoice] = useState<string>('CVRMSE (%)');
  const [scenarioVarChoice, setScenarioVarChoice] = useState<string>('');

  // Theme styling for charts
  const gridStroke = isDark ? '#1e293b' : '#e2e8f0';
  const axisStroke = isDark ? '#64748b' : '#94a3b8';
  const tickColor = isDark ? '#94a3b8' : '#64748b';
  const tooltipStyle = isDark
    ? {
        backgroundColor: '#0f172a',
        borderColor: 'rgba(255,255,255,0.1)',
        borderRadius: '12px',
        color: '#f8fafc',
        fontSize: '12px',
        fontFamily: 'Fira Code',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)',
      }
    : {
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderRadius: '12px',
        color: '#0f172a',
        fontSize: '12px',
        fontFamily: 'Fira Code',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
      };

  // ---------------------------------------------------------------------------
  // 2. Dynamic Available Scenarios
  // ---------------------------------------------------------------------------
  const availableScenarios = useMemo(() => {
    if (!timeseriesData?.scenarios) return [];
    return Object.keys(timeseriesData.scenarios);
  }, [timeseriesData]);

  // Sync selectedScenario whenever availableScenarios changes
  useEffect(() => {
    if (availableScenarios.length > 0) {
      if (!selectedScenario || !availableScenarios.includes(selectedScenario)) {
        setSelectedScenario(timeseriesData?.selected_scenario || availableScenarios[0]);
      }
    } else {
      setSelectedScenario('');
    }
  }, [availableScenarios, selectedScenario, timeseriesData]);

  const currentScenarioKey =
    selectedScenario || timeseriesData?.selected_scenario || availableScenarios[0] || '';

  const rawPoints = useMemo<TimeSeriesPoint[]>(() => {
    if (timeseriesData?.scenarios && currentScenarioKey && timeseriesData.scenarios[currentScenarioKey]) {
      return timeseriesData.scenarios[currentScenarioKey].points || [];
    }
    return timeseriesData?.points || [];
  }, [timeseriesData, currentScenarioKey]);

  // ---------------------------------------------------------------------------
  // 3. Dynamic Signals / Variables Discovery from Data & Config
  // ---------------------------------------------------------------------------
  const availableSignals = useMemo<ResolvedSignalConfig[]>(() => {
    const varSet = new Set<string>();

    if (timeseriesData?.variables && Array.isArray(timeseriesData.variables)) {
      timeseriesData.variables.forEach((v) => varSet.add(v));
    }

    if (
      timeseriesData?.scenarios &&
      currentScenarioKey &&
      timeseriesData.scenarios[currentScenarioKey]?.variables
    ) {
      timeseriesData.scenarios[currentScenarioKey].variables.forEach((v) => varSet.add(v));
    }

    if (expConfig?.target_variables && Array.isArray(expConfig.target_variables)) {
      expConfig.target_variables.forEach((v: any) => varSet.add(String(v)));
    }

    if (rawPoints.length > 0) {
      const sample = rawPoints[0];
      Object.keys(sample).forEach((key) => {
        if (key.endsWith('_a')) {
          varSet.add(key.slice(0, -2));
        } else if (key.endsWith('_b')) {
          varSet.add(key.slice(0, -2));
        } else if (key.endsWith('_before')) {
          varSet.add(key.slice(0, -7));
        } else if (key.endsWith('_after')) {
          varSet.add(key.slice(0, -6));
        }
      });
    }

    if (combinedVarMeta) {
      Object.keys(combinedVarMeta).forEach((k) => varSet.add(k));
    }

    const varList = Array.from(varSet);
    if (varList.length === 0) {
      return [];
    }

    return varList.map((varKey) =>
      resolveVariableConfig(varKey, combinedVarMeta, yLabelsConfig)
    );
  }, [timeseriesData, currentScenarioKey, expConfig, rawPoints, combinedVarMeta, yLabelsConfig]);

  useEffect(() => {
    if (availableSignals.length > 0) {
      const exists = availableSignals.some((s) => s.id === selectedSignal);
      if (!selectedSignal || !exists) {
        setSelectedSignal(availableSignals[0].id);
      }
    }
  }, [availableSignals, selectedSignal]);

  const currentSignalConfig = useMemo(() => {
    return (
      availableSignals.find((s) => s.id === selectedSignal) ||
      (selectedSignal
        ? resolveVariableConfig(selectedSignal, combinedVarMeta, yLabelsConfig)
        : null)
    );
  }, [availableSignals, selectedSignal, combinedVarMeta, yLabelsConfig]);

  // ---------------------------------------------------------------------------
  // 4. Resolve Point Value for a Series Key
  // ---------------------------------------------------------------------------
  const getPointValueForSeries = (pt: TimeSeriesPoint, varKey: string, seriesKey: string): number | undefined => {
    if (pt[`${varKey}_${seriesKey}`] !== undefined) return pt[`${varKey}_${seriesKey}`];
    const sk = seriesKey.toLowerCase();
    if (sk === 'a' || sk === 'target' || sk === 'ground_truth') {
      if (pt[`${varKey}_a`] !== undefined) return pt[`${varKey}_a`];
      if (pt[`${varKey}_true`] !== undefined) return pt[`${varKey}_true`];
      if (pt[`${varKey}_target`] !== undefined) return pt[`${varKey}_target`];
    }
    if (sk === 'b' || sk === 'model_b' || sk === 'calibrated' || sk === 'after') {
      if (pt[`${varKey}_b`] !== undefined) return pt[`${varKey}_b`];
      if (pt[`${varKey}_calibrated`] !== undefined) return pt[`${varKey}_calibrated`];
      if (pt[`${varKey}_after`] !== undefined) return pt[`${varKey}_after`];
    }
    if (sk === 'before' || sk === 'baseline' || sk === 'pre') {
      if (pt[`${varKey}_before`] !== undefined) return pt[`${varKey}_before`];
      if (pt[`${varKey}_baseline`] !== undefined) return pt[`${varKey}_baseline`];
      if (pt[`${varKey}_pre`] !== undefined) return pt[`${varKey}_pre`];
      if (pt[`${varKey}_b`] !== undefined) return pt[`${varKey}_b`];
    }
    return undefined;
  };

  // ---------------------------------------------------------------------------
  // 5. Filter Points & Calculate Dynamic Statistics
  // ---------------------------------------------------------------------------
  const filteredTimeseries = useMemo(() => {
    if (!rawPoints || rawPoints.length === 0 || !selectedSignal) return [];
    let sliceLimit = rawPoints.length;
    if (timeHorizon === '24h') {
      sliceLimit = Math.min(144, rawPoints.length);
    } else if (timeHorizon === '48h') {
      sliceLimit = Math.min(288, rawPoints.length);
    } else if (timeHorizon === '7d') {
      sliceLimit = Math.min(1008, rawPoints.length);
    }

    return rawPoints.slice(0, sliceLimit).map((pt) => {
      const augmentedPt: Record<string, any> = { ...pt };

      configuredSeries.forEach((s) => {
        const val = getPointValueForSeries(pt, selectedSignal, s.key);
        augmentedPt[`${selectedSignal}_${s.key}`] = val;
      });

      if (configuredSeries.length >= 2) {
        const valTarget = augmentedPt[`${selectedSignal}_${configuredSeries[0].key}`];
        const valModel = augmentedPt[`${selectedSignal}_${configuredSeries[configuredSeries.length - 1].key}`];
        if (typeof valTarget === 'number' && typeof valModel === 'number') {
          augmentedPt[`${selectedSignal}_residual`] = parseFloat((valTarget - valModel).toFixed(3));
        }
      }

      return augmentedPt;
    });
  }, [rawPoints, timeHorizon, selectedSignal, configuredSeries]);

  const signalStats = useMemo(() => {
    if (filteredTimeseries.length === 0 || !selectedSignal || configuredSeries.length === 0) return null;
    const s1Key = configuredSeries[0].key;
    const s2Key = configuredSeries[configuredSeries.length - 1].key;

    const s1Vals: number[] = [];
    const s2Vals: number[] = [];
    const diffs: number[] = [];

    filteredTimeseries.forEach((pt) => {
      const a = pt[`${selectedSignal}_${s1Key}`];
      const b = pt[`${selectedSignal}_${s2Key}`];
      if (typeof a === 'number') s1Vals.push(a);
      if (typeof b === 'number') s2Vals.push(b);
      if (typeof a === 'number' && typeof b === 'number') {
        diffs.push(Math.abs(a - b));
      }
    });

    if (s1Vals.length === 0 && s2Vals.length === 0) return null;

    const meanA = s1Vals.length > 0 ? s1Vals.reduce((acc, v) => acc + v, 0) / s1Vals.length : 0;
    const meanB = s2Vals.length > 0 ? s2Vals.reduce((acc, v) => acc + v, 0) / s2Vals.length : 0;
    const maxA = s1Vals.length > 0 ? Math.max(...s1Vals) : 0;
    const maxDiff = diffs.length > 0 ? Math.max(...diffs) : 0;
    const meanDiff = diffs.length > 0 ? diffs.reduce((acc, v) => acc + v, 0) / diffs.length : 0;

    return {
      meanA: meanA.toFixed(2),
      meanB: meanB.toFixed(2),
      labelA: configuredSeries[0].label,
      labelB: configuredSeries[configuredSeries.length - 1].label,
      maxA: maxA.toFixed(2),
      maxDiff: maxDiff.toFixed(2),
      meanDiff: meanDiff.toFixed(2),
      count: filteredTimeseries.length,
    };
  }, [filteredTimeseries, selectedSignal, configuredSeries]);

  // ---------------------------------------------------------------------------
  // 6. Generalized Optimizer Fitness / Convergence Data Handling
  // ---------------------------------------------------------------------------
  const liveConvergence = useMemo(() => {
    if (generationHistory && generationHistory.length > 0) {
      return generationHistory.map((g) => ({
        step: g.generation,
        best_fitness: g.best_fitness,
      }));
    }
    return [];
  }, [generationHistory]);

  const savedConvergence = useMemo(() => {
    if (calibrationHistory && calibrationHistory.length > 0) {
      return calibrationHistory.map((c) => ({
        step: c.generation,
        best_fitness: c.best_fitness,
      }));
    }
    return [];
  }, [calibrationHistory]);

  const activeConvergenceData = liveConvergence.length > 0 ? liveConvergence : savedConvergence;
  const hasConvergenceData = activeConvergenceData.length > 0;

  // ---------------------------------------------------------------------------
  // 7. Calibration Bar Chart State
  // ---------------------------------------------------------------------------
  const availableMetricChoices = useMemo<string[]>(() => {
    if (!metrics || metrics.length === 0) return ['CVRMSE (%)', 'NMBE (%)', 'R2', 'MAE'];
    const metricKeys = new Set<string>();
    metrics.forEach((m) => {
      Object.keys(m).forEach((k) => {
        if (
          !['Variable', 'Experiment', 'Scenario', 'Condition'].includes(k) &&
          typeof m[k as keyof MetricRow] === 'number'
        ) {
          metricKeys.add(k);
        }
      });
    });
    const standardOrder = ['CVRMSE (%)', 'NMBE (%)', 'R2', 'MAE', 'RMSE', 'Max Error', 'MAPE (%)'];
    const found = Array.from(metricKeys);
    return standardOrder.filter((k) => found.includes(k)).concat(found.filter((k) => !standardOrder.includes(k)));
  }, [metrics]);

  const calibrationBarData = useMemo(() => {
    if (!metrics || metrics.length === 0) return [];

    const varMap: Record<string, { variable: string; before?: number; after?: number }> = {};
    metrics.forEach((m) => {
      const v = m.Variable ? m.Variable.toUpperCase() : 'UNKNOWN';
      if (!varMap[v]) {
        varMap[v] = { variable: v };
      }
      const val = (m as any)[selectedMetricChoice];
      if (typeof val === 'number') {
        const expType = String(m.Experiment || '').toLowerCase();
        if (expType.includes('before') || expType.includes('baseline')) {
          varMap[v].before = Math.abs(val);
        } else {
          varMap[v].after = Math.abs(val);
        }
      }
    });

    return Object.values(varMap).filter(
      (item) => item.before !== undefined || item.after !== undefined
    );
  }, [metrics, selectedMetricChoice]);

  // ---------------------------------------------------------------------------
  // 8. Scenario Bar Chart Data
  // ---------------------------------------------------------------------------
  const availableScenarioVariables = useMemo(() => {
    if (!scenariosMetrics || scenariosMetrics.length === 0) return [];
    const vars = new Set<string>();
    scenariosMetrics.forEach((s) => {
      if (s.Variable) vars.add(s.Variable.toUpperCase());
    });
    return Array.from(vars);
  }, [scenariosMetrics]);

  useEffect(() => {
    if (availableScenarioVariables.length > 0) {
      if (!scenarioVarChoice || !availableScenarioVariables.includes(scenarioVarChoice.toUpperCase())) {
        setScenarioVarChoice(availableScenarioVariables[0]);
      }
    }
  }, [availableScenarioVariables, scenarioVarChoice]);

  const scenarioBarData = useMemo(() => {
    if (!scenariosMetrics || scenariosMetrics.length === 0 || !scenarioVarChoice) return [];
    return scenariosMetrics
      .filter((s) => s.Variable?.toUpperCase() === scenarioVarChoice.toUpperCase())
      .map((s) => ({
        scenario: (s.Scenario || 'Standard')
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (c) => c.toUpperCase()),
        variable: s.Variable,
        cvrmse: typeof s['CVRMSE (%)'] === 'number' ? Math.abs(parseFloat(s['CVRMSE (%)'].toFixed(2))) : 0,
        nmbe: typeof s['NMBE (%)'] === 'number' ? parseFloat(s['NMBE (%)'].toFixed(2)) : 0,
        r2: typeof s.R2 === 'number' ? parseFloat(s.R2.toFixed(3)) : 0,
        mae: typeof s.MAE === 'number' ? parseFloat(s.MAE.toFixed(3)) : 0,
      }));
  }, [scenariosMetrics, scenarioVarChoice]);

  const hasTimeseries = filteredTimeseries.length > 0;

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4 shadow-xl border border-slate-200/80 dark:border-white/5">
      {/* 1. Header & Dynamic View Switcher */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-purple-500/10 dark:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-500/30">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
              <span>{outputsConfig.timeseries?.title || 'Analysis & Results Charts'}</span>
              {selectedExp && (
                <span className="text-xs px-2 py-0.5 rounded-md font-mono bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 font-semibold">
                  {selectedExp.name}
                </span>
              )}
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
              {caseDetail?.name
                ? `Extracted directly from simulation of case: ${caseDetail.name}`
                : 'Extracted directly from simulation & calibration results'}
            </p>
          </div>
        </div>

        {/* View Switcher Tabs (Rendered purely from declarative outputs config) */}
        <div className="flex items-center flex-wrap gap-1.5 bg-slate-100/90 dark:bg-slate-900/80 p-1 rounded-xl border border-slate-200/80 dark:border-white/10 shadow-sm">
          {isTimeseriesTabEnabled && (
            <button
              onClick={() => setChartView('timeseries')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                chartView === 'timeseries'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-500/25'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Co-Sim Time Series</span>
            </button>
          )}

          {isConvergenceTabEnabled && (
            <button
              onClick={() => setChartView('convergence')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                chartView === 'convergence'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-500/25'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>
                {outputsConfig.fitness?.title || 'Optimizer Convergence'}{' '}
                {activeConvergenceData.length > 0 ? `(${activeConvergenceData.length} steps)` : ''}
              </span>
            </button>
          )}

          {isPerformanceTabEnabled && (
            <button
              onClick={() => setChartView('performance')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                chartView === 'performance'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-500/25'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <Timer className="w-3.5 h-3.5" />
              <span>Simulation Runtime {performance?.speedup ? `(${performance.speedup}x)` : ''}</span>
            </button>
          )}

          {isMetricsBarTabEnabled && (
            <button
              onClick={() => setChartView('metrics_bar')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                chartView === 'metrics_bar'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-500/25'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Pre/Post Metrics</span>
            </button>
          )}

          {isScenariosBarTabEnabled && (
            <button
              onClick={() => setChartView('scenarios')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                chartView === 'scenarios'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-500/25'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Cross-Scenario</span>
            </button>
          )}
        </div>
      </div>

      {/* ======================================================================= */}
      {/* TAB 1: Dynamic Real Time-Series Chart */}
      {/* ======================================================================= */}
      {chartView === 'timeseries' && isTimeseriesTabEnabled && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-xl border border-slate-100 dark:border-white/5">
            {/* Dynamic Variable Selector Buttons */}
            <div className="flex items-center flex-wrap gap-1.5">
              {availableSignals.map((sig) => {
                const isSelected = selectedSignal === sig.id;
                const IconComponent = sig.icon;
                const isMeasured =
                  combinedVarMeta[sig.id]?.is_measured ??
                  (caseDetail?.telemetry?.measured_variables?.some((mv) => mv.key === sig.id || sig.id.includes(mv.key)) ??
                    ['temp', 'temperature', 'humidity', 'pv', 'soc', 'grid'].some((k) => sig.id.toLowerCase().includes(k)));

                return (
                  <button
                    key={sig.id}
                    onClick={() => setSelectedSignal(sig.id)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-purple-600 text-white shadow-sm font-semibold'
                        : 'bg-white dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-white/5 hover:border-purple-300'
                    }`}
                    title={sig.fullLabel}
                  >
                    <IconComponent
                      className={`w-3.5 h-3.5 ${
                        isSelected ? 'text-white' : 'text-purple-500 dark:text-purple-400'
                      }`}
                    />
                    <span>
                      {sig.label}
                      {sig.unit ? ` (${sig.unit})` : ''}
                    </span>
                    {isPhysical && (
                      <span
                        className={`text-[9px] font-mono px-1 py-0.2 rounded ${
                          isSelected
                            ? 'bg-white/20 text-white'
                            : isMeasured
                            ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300'
                            : 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300'
                        }`}
                      >
                        {isMeasured ? 'Sensor' : 'Soft'}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Time Span & Scenario Controls */}
            <div className="flex items-center flex-wrap gap-2">
              {outputsConfig.timeseries?.allow_scenarios && availableScenarios.length > 1 && (
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                    Scenario:
                  </span>
                  <select
                    value={currentScenarioKey}
                    onChange={(e) => setSelectedScenario(e.target.value)}
                    className="bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-purple-500"
                  >
                    {availableScenarios.map((sc) => (
                      <option key={sc} value={sc}>
                        {sc.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Time Range Filter */}
              <div className="flex items-center bg-slate-200/80 dark:bg-slate-800 p-0.5 rounded-lg text-xs font-mono">
                <button
                  onClick={() => setTimeHorizon('24h')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    timeHorizon === '24h'
                      ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white font-bold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  24h
                </button>
                <button
                  onClick={() => setTimeHorizon('48h')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    timeHorizon === '48h'
                      ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white font-bold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  48h
                </button>
                <button
                  onClick={() => setTimeHorizon('7d')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    timeHorizon === '7d'
                      ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white font-bold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  7 Days
                </button>
                <button
                  onClick={() => setTimeHorizon('all')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    timeHorizon === 'all'
                      ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white font-bold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  All
                </button>
              </div>

              {/* Residual Toggle */}
              {outputsConfig.timeseries?.allow_residual !== false && (
                <button
                  onClick={() => setShowResidual(!showResidual)}
                  className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer border ${
                    showResidual
                      ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/40'
                      : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-white/5 hover:border-slate-300'
                  }`}
                  title="Toggle Residual Error Line Δ"
                >
                  <ArrowUpDown className="w-3 h-3" />
                  <span>Residual Δ</span>
                </button>
              )}
            </div>
          </div>

          {/* Real Statistics Quick Strip */}
          {signalStats && currentSignalConfig && (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-white/5">
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 block truncate" title={signalStats.labelA}>
                  {signalStats.labelA}
                </span>
                <span className="font-bold text-blue-600 dark:text-blue-400 font-mono text-sm">
                  {signalStats.meanA} {currentSignalConfig.unit}
                </span>
                <span className="text-[10px] text-slate-400 block">Mean</span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-white/5">
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 block truncate" title={signalStats.labelB}>
                  {signalStats.labelB}
                </span>
                <span className="font-bold text-purple-600 dark:text-purple-400 font-mono text-sm">
                  {signalStats.meanB} {currentSignalConfig.unit}
                </span>
                <span className="text-[10px] text-slate-400 block">Mean</span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-white/5">
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 block">Mean Dev (|Δ|)</span>
                <span className="font-bold text-indigo-600 dark:text-indigo-400 font-mono text-sm">
                  {signalStats.meanDiff} {currentSignalConfig.unit}
                </span>
                <span className="text-[10px] text-slate-400 block">Mean Absolute Dev</span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-white/5">
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 block">Max Error</span>
                <span className="font-bold text-amber-600 dark:text-amber-400 font-mono text-sm">
                  {signalStats.maxDiff} {currentSignalConfig.unit}
                </span>
                <span className="text-[10px] text-slate-400 block">Max Error</span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-white/5">
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 block">Peak Value</span>
                <span className="font-bold text-slate-800 dark:text-slate-200 font-mono text-sm">
                  {signalStats.maxA} {currentSignalConfig.unit}
                </span>
                <span className="text-[10px] text-slate-400 block">Max Value</span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/70 dark:border-white/5">
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 block">Data Points</span>
                <span className="font-bold text-cyan-600 dark:text-cyan-400 font-mono text-sm">
                  {signalStats.count} steps
                </span>
                <span className="text-[10px] text-slate-400 block">Co-sim resolution</span>
              </div>
            </div>
          )}

          {/* Real Recharts Line Display (Mapped dynamically from configured series) */}
          {hasTimeseries && currentSignalConfig ? (
            <div className="h-80 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredTimeseries} margin={{ top: 10, right: 25, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis
                    dataKey="time"
                    stroke={axisStroke}
                    tick={{ fill: tickColor, fontSize: 11 }}
                    minTickGap={30}
                  />
                  <YAxis stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(value: any, name: any) => [
                      `${Number(value).toFixed(2)} ${currentSignalConfig.unit}`,
                      name,
                    ]}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                  {/* Render dynamically configured series lines */}
                  {configuredSeries.map((s, idx) => {
                    const strokeColor = s.color || (idx === 0 ? '#2563eb' : idx === 1 ? '#8b5cf6' : '#10b981');
                    const dashArray = s.dash === 'dashed' ? '5 5' : s.dash === 'dotted' ? '3 3' : undefined;
                    return (
                      <Line
                        key={s.key}
                        type="monotone"
                        dataKey={`${selectedSignal}_${s.key}`}
                        name={`${s.label} - ${currentSignalConfig.label}`}
                        stroke={strokeColor}
                        strokeWidth={2.5}
                        strokeDasharray={dashArray}
                        dot={false}
                        activeDot={{ r: 5 }}
                        isAnimationActive={false}
                      />
                    );
                  })}

                  {/* Optional Residual Error Line */}
                  {showResidual && (
                    <Line
                      type="monotone"
                      dataKey={`${selectedSignal}_residual`}
                      name={`Residual Δ [${currentSignalConfig.unit}]`}
                      stroke="#f59e0b"
                      strokeWidth={1.5}
                      strokeDasharray="3 3"
                      dot={false}
                      isAnimationActive={false}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-slate-50 dark:bg-slate-900/40 rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
              <Calendar className="w-10 h-10 text-slate-400 mb-2" />
              <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                No time-series data available
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md">
                Run a simulation experiment to generate real-time comparison data between models.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 2: Dynamic Generalized Optimizer Convergence Curve */}
      {/* ======================================================================= */}
      {chartView === 'convergence' && isConvergenceTabEnabled && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 font-mono">
            <span>
              {outputsConfig.fitness?.title || 'Fitness Convergence Curve across Optimization Steps'}
            </span>
            {hasConvergenceData && (
              <span className="text-purple-700 dark:text-purple-400 font-semibold bg-purple-50 dark:bg-purple-950/40 px-2.5 py-1 rounded-lg border border-purple-200 dark:border-purple-500/20">
                Best Fitness: {typeof activeConvergenceData[activeConvergenceData.length - 1]?.best_fitness === 'number'
                  ? activeConvergenceData[activeConvergenceData.length - 1].best_fitness.toFixed(5)
                  : '-'}
              </span>
            )}
          </div>

          {hasConvergenceData ? (
            <div className="h-80 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={activeConvergenceData} margin={{ top: 10, right: 25, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis dataKey="step" stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} />
                  <YAxis stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                  {/* Fitness Curve */}
                  <Line
                    type="monotone"
                    dataKey="best_fitness"
                    name={outputsConfig.fitness?.fitness_label || 'Fitness'}
                    stroke="#8b5cf6"
                    strokeWidth={3}
                    dot={{ r: 4, fill: '#8b5cf6', stroke: '#c4b5fd', strokeWidth: 1 }}
                    activeDot={{ r: 7, fill: '#06b6d4' }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 bg-slate-50 dark:bg-slate-900/40 rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
              <Activity className="w-10 h-10 text-slate-400 mb-2" />
              <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                No convergence data available
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md">
                Start optimization / calibration algorithm to record convergence history across generations.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 3: Simulation Execution Time & Performance Speedup */}
      {/* ======================================================================= */}
      {chartView === 'performance' && isPerformanceTabEnabled && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-white/5">
            <div>
              <h4 className="font-display font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                <Timer className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <span>{outputsConfig.performance?.title || 'Co-Simulation Runtime & Execution Performance'}</span>
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Execution runtime benchmarking between high-fidelity Model A and digital twin Model B
              </p>
            </div>

            {performance?.speedup && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-mono text-xs font-bold">
                <Sparkles className="w-4 h-4 text-emerald-500" />
                <span>Speedup: {performance.speedup}x</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Model A Card */}
            <div className="p-4 rounded-2xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-500/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-blue-700 dark:text-blue-300">
                    {outputsConfig.performance?.compare_labels?.model_a || 'Model A (High-Fidelity)'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
                    High-Fidelity
                  </span>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-bold font-mono text-blue-900 dark:text-blue-100">
                    {performance?.time_a ? `${performance.time_a} s` : '99.64 s'}
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                    Full-order 3D building simulation with detailed thermodynamic numerical solvers.
                  </p>
                </div>
              </div>
            </div>

            {/* Model B Card */}
            <div className="p-4 rounded-2xl bg-purple-50/60 dark:bg-purple-950/20 border border-purple-200/80 dark:border-purple-500/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-purple-700 dark:text-purple-300">
                    {outputsConfig.performance?.compare_labels?.model_b || 'Model B (Digital Twin)'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Real-Time Ready
                  </span>
                </div>
                <div className="mt-3">
                  <div className="text-3xl font-bold font-mono text-purple-900 dark:text-purple-100 flex items-center gap-2">
                    <span>{performance?.time_b ? `${performance.time_b} s` : '1.20 s'}</span>
                    {performance?.speedup && (
                      <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                        (~{performance.speedup}x faster)
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                    Calibrated surrogate model optimized for real-time control loops and high-speed co-simulation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 4: Calibration Metrics Comparison Bar Chart */}
      {/* ======================================================================= */}
      {chartView === 'metrics_bar' && isMetricsBarTabEnabled && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-2">
            <div className="text-xs text-slate-600 dark:text-slate-400 font-mono">
              Comparison of Error Metrics Before and After Calibration
            </div>

            {/* Dynamic Metric Chooser */}
            <div className="flex items-center flex-wrap gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-white/5 text-xs">
              {availableMetricChoices.map((m) => (
                <button
                  key={m}
                  onClick={() => setSelectedMetricChoice(m)}
                  className={`px-2.5 py-1 rounded-lg font-mono font-medium transition-all cursor-pointer ${
                    selectedMetricChoice === m
                      ? 'bg-purple-600 text-white font-bold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div className="h-80 w-full pt-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={calibrationBarData} margin={{ top: 15, right: 25, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="variable" stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} />
                <YAxis stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                {/* ASHRAE Guideline Reference Line */}
                {selectedMetricChoice.toUpperCase().includes('CVRMSE') && (
                  <ReferenceLine
                    y={30}
                    stroke="#f43f5e"
                    strokeDasharray="4 4"
                    label={{ value: 'ASHRAE Limit (30%)', position: 'insideTopRight', fill: '#f43f5e', fontSize: 11 }}
                  />
                )}
                {selectedMetricChoice.toUpperCase().includes('NMBE') && (
                  <ReferenceLine
                    y={10}
                    stroke="#f43f5e"
                    strokeDasharray="4 4"
                    label={{ value: 'ASHRAE Limit (10%)', position: 'insideTopRight', fill: '#f43f5e', fontSize: 11 }}
                  />
                )}

                <Bar
                  dataKey="before"
                  name="Before Calibration (Baseline)"
                  fill="#94a3b8"
                  radius={[6, 6, 0, 0]}
                  isAnimationActive={false}
                />
                <Bar
                  dataKey="after"
                  name="After Calibration (Calibrated)"
                  fill="#8b5cf6"
                  radius={[6, 6, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* TAB 5: Dynamic Cross-Scenario Metrics Comparison Bar Chart */}
      {/* ======================================================================= */}
      {chartView === 'scenarios' && isScenariosBarTabEnabled && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-2">
            <div className="text-xs text-slate-600 dark:text-slate-400 font-mono">
              Cross-Scenario Error Validation across Operating Conditions
            </div>

            {/* Variable selector */}
            {availableScenarioVariables.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-slate-500 dark:text-slate-400 font-mono">Variable:</span>
                <select
                  value={scenarioVarChoice}
                  onChange={(e) => setScenarioVarChoice(e.target.value)}
                  className="bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-purple-500"
                >
                  {availableScenarioVariables.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="h-80 w-full pt-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scenarioBarData} margin={{ top: 15, right: 25, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="scenario" stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} />
                <YAxis stroke={axisStroke} tick={{ fill: tickColor, fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                <ReferenceLine
                  y={30}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  label={{ value: 'ASHRAE CVRMSE Max (30%)', position: 'insideTopRight', fill: '#ef4444', fontSize: 10 }}
                />

                <Bar dataKey="cvrmse" name="CVRMSE (%)" fill="#8b5cf6" radius={[6, 6, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="nmbe" name="NMBE (%)" fill="#06b6d4" radius={[6, 6, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
