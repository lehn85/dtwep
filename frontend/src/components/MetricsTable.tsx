import React, { useState, useMemo, useEffect } from 'react';
import { Award, CheckCircle2, XCircle, AlertTriangle, Table as TableIcon } from 'lucide-react';
import { MetricRow, OutputDisplayConfig, MetricsTableDisplayConfig } from '../types';

interface MetricsTableProps {
  metrics: MetricRow[];
  scenariosMetrics?: MetricRow[];
  outputs?: OutputDisplayConfig;
  tableConfig?: MetricsTableDisplayConfig;
}

export const MetricsTable: React.FC<MetricsTableProps> = ({
  metrics = [],
  scenariosMetrics = [],
  outputs,
  tableConfig: directTableConfig,
}) => {
  const tableConfig = directTableConfig || outputs?.metrics_table || {};

  const sourceConfig = tableConfig.source || (metrics.length > 0 ? 'metrics' : 'scenarios_metrics');
  const filterCondition = tableConfig.filter_condition;
  const showConditionColumn = tableConfig.show_condition_column;
  const showAshraeSummary = tableConfig.show_ashrae_summary !== false;
  const customTitle = tableConfig.title;

  const hasCalibrationMetrics = Array.isArray(metrics) && metrics.length > 0;
  const hasScenarioMetrics = Array.isArray(scenariosMetrics) && scenariosMetrics.length > 0;

  // 1. All hooks called unconditionally at top of component
  const [activeTab, setActiveTab] = useState<'calibration' | 'scenarios'>(
    sourceConfig === 'scenarios_metrics' ? 'scenarios' : 'calibration'
  );
  const [filterExp, setFilterExp] = useState<string>('all');

  // Reset filterExp when metrics data or configured source changes
  useEffect(() => {
    setFilterExp('all');
  }, [metrics, scenariosMetrics, sourceConfig]);

  // Sync tab state whenever configured source or data availability changes
  useEffect(() => {
    if (sourceConfig === 'scenarios_metrics' || (!hasCalibrationMetrics && hasScenarioMetrics)) {
      setActiveTab('scenarios');
    } else {
      setActiveTab('calibration');
    }
  }, [sourceConfig, hasCalibrationMetrics, hasScenarioMetrics]);

  // Extract distinct experiment conditions dynamically
  const availableConditions = useMemo(() => {
    const set = new Set<string>();
    if (Array.isArray(metrics)) {
      metrics.forEach((m) => {
        if (m && m.Experiment) set.add(m.Experiment);
      });
    }
    return Array.from(set);
  }, [metrics]);

  // Filter display metrics based on declarative config or user filter
  const displayMetrics = useMemo(() => {
    if (activeTab === 'scenarios') {
      if (Array.isArray(scenariosMetrics) && scenariosMetrics.length > 0) {
        return scenariosMetrics;
      }
      return Array.isArray(metrics) ? metrics : [];
    }

    // Calibration metrics
    let list = Array.isArray(metrics) ? metrics : [];

    // 1. If YAML explicitly specified filter_condition (e.g. "Calibrated" or "After Calibration")
    if (filterCondition) {
      const targetCond = String(filterCondition).toLowerCase().trim();
      const isAfterTarget = targetCond.includes('after') || targetCond.includes('post') || targetCond.includes('calibrated') || targetCond.includes('recovered');
      const isBeforeTarget = targetCond.includes('before') || targetCond.includes('pre') || targetCond.includes('baseline') || targetCond.includes('degraded');

      list = list.filter((m) => {
        if (!m) return false;
        const expName = String(m.Experiment || '').toLowerCase().trim();
        if (expName === targetCond || expName.includes(targetCond) || targetCond.includes(expName)) {
          return true;
        }
        const isAfterExp = expName.includes('after') || expName.includes('post') || expName.includes('calibrated') || expName.includes('recovered');
        if (isAfterTarget && isAfterExp) return true;

        const isBeforeExp = expName.includes('before') || expName.includes('pre') || expName.includes('baseline') || expName.includes('degraded');
        if (isBeforeTarget && isBeforeExp) return true;

        return false;
      });
    } else if (filterExp !== 'all') {
      // 2. Otherwise respect user manual filter dropdown if active
      list = list.filter((m) => m && m.Experiment === filterExp);
    }

    return list;
  }, [activeTab, metrics, scenariosMetrics, filterCondition, filterExp]);

  // Calculate summary metrics for displayed rows safely
  const summarySource = displayMetrics.length > 0 ? displayMetrics : Array.isArray(metrics) ? metrics : [];

  const avgCvrmse = useMemo(() => {
    if (summarySource.length === 0) return 0;
    return (
      summarySource.reduce((acc, row) => {
        const val = typeof row?.['CVRMSE (%)'] === 'number' && !isNaN(row['CVRMSE (%)']) ? Math.abs(row['CVRMSE (%)']) : 0;
        return acc + val;
      }, 0) / summarySource.length
    );
  }, [summarySource]);

  const avgNmbe = useMemo(() => {
    if (summarySource.length === 0) return 0;
    return (
      summarySource.reduce((acc, row) => {
        const val = typeof row?.['NMBE (%)'] === 'number' && !isNaN(row['NMBE (%)']) ? Math.abs(row['NMBE (%)']) : 0;
        return acc + val;
      }, 0) / summarySource.length
    );
  }, [summarySource]);

  const avgR2 = useMemo(() => {
    if (summarySource.length === 0) return 0;
    return (
      summarySource.reduce((acc, row) => {
        const val = typeof row?.R2 === 'number' && !isNaN(row.R2) ? row.R2 : 0;
        return acc + val;
      }, 0) / summarySource.length
    );
  }, [summarySource]);

  const isAshraePass = avgCvrmse <= 30 && avgNmbe <= 10;

  const formatNumber = (val: any, decimals = 3): string => {
    if (typeof val === 'number' && !isNaN(val) && isFinite(val)) {
      return val.toFixed(decimals);
    }
    return '-';
  };

  const getCvrmseBadge = (val?: any) => {
    if (typeof val !== 'number' || isNaN(val) || !isFinite(val)) return <span className="text-slate-400">-</span>;
    const absVal = Math.abs(val);
    const pass = absVal <= 30.0;
    return (
      <span
        className={`font-mono text-xs font-semibold px-2 py-0.5 rounded-md border flex items-center gap-1 w-fit ${
          pass
            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20'
            : 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-500/20'
        }`}
      >
        {pass ? <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> : <XCircle className="w-3 h-3 text-rose-600 dark:text-rose-400" />}
        {val.toFixed(2)}%
      </span>
    );
  };

  const getNmbeBadge = (val?: any) => {
    if (typeof val !== 'number' || isNaN(val) || !isFinite(val)) return <span className="text-slate-400">-</span>;
    const absVal = Math.abs(val);
    const pass = absVal <= 10.0;
    return (
      <span
        className={`font-mono text-xs font-semibold px-2 py-0.5 rounded-md border flex items-center gap-1 w-fit ${
          pass
            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20'
            : 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-500/20'
        }`}
      >
        {pass ? <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> : <AlertTriangle className="w-3 h-3 text-rose-600 dark:text-rose-400" />}
        {val.toFixed(2)}%
      </span>
    );
  };

  const getR2Badge = (val?: any) => {
    if (typeof val !== 'number' || isNaN(val) || !isFinite(val)) return <span className="text-slate-400">-</span>;
    const pass = val >= 0.70;
    return (
      <span
        className={`font-mono text-xs font-semibold px-2 py-0.5 rounded-md border ${
          pass
            ? 'bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-500/20'
            : val >= 0.50
            ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/20'
            : 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-500/20'
        }`}
      >
        {val.toFixed(3)}
      </span>
    );
  };

  // 2. Early return AFTER all hooks have executed
  if (!hasCalibrationMetrics && !hasScenarioMetrics) {
    return (
      <div className="glass-panel rounded-2xl p-6 text-center text-slate-500 dark:text-slate-400 text-sm">
        No empirical evaluation metrics available yet. Run an experiment to generate statistical and validation metrics.
      </div>
    );
  }

  // Determine whether to display tab switch buttons
  const shouldShowTabs =
    !filterCondition &&
    !tableConfig.source &&
    hasCalibrationMetrics &&
    hasScenarioMetrics;

  const shouldRenderConditionColumn =
    activeTab === 'calibration' &&
    (showConditionColumn !== undefined
      ? showConditionColumn
      : !filterCondition && availableConditions.length > 1);

  const titleToRender =
    customTitle ||
    (activeTab === 'scenarios'
      ? 'Cross-Scenario Validation Metrics Table'
      : filterCondition
      ? `Validation Metrics Table (${filterCondition})`
      : 'Statistical Validation Metrics (ASHRAE Guideline 14)');

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4 shadow-xl">
      {/* Header & ASHRAE Compliance Summary Bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-3 border-b border-slate-100 dark:border-white/5">
        <div>
          <div className="flex items-center gap-2">
            <TableIcon className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
              {titleToRender}
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Standard Criteria: CVRMSE &le; 30%, NMBE &le; &plusmn;10%, R&sup2; &ge; 0.70
          </p>
        </div>

        {/* ASHRAE Overall Compliance Badge */}
        {showAshraeSummary && summarySource.length > 0 && (
          <div className="flex items-center gap-3 bg-slate-100/90 dark:bg-slate-900/80 p-2 px-3.5 rounded-xl border border-slate-200/80 dark:border-white/10 text-xs shadow-sm">
            <div className="flex items-center gap-1.5 font-display font-semibold">
              <Award className="w-4 h-4 text-amber-500 dark:text-amber-400" />
              <span className="text-slate-700 dark:text-slate-300">Guideline 14:</span>
              <span
                className={`font-bold px-2 py-0.5 rounded-md border uppercase text-[11px] ${
                  isAshraePass
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/30'
                    : 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500/30'
                }`}
              >
                {isAshraePass ? 'Passed (ASHRAE 14)' : 'Partial Compliance'}
              </span>
            </div>

            <div className="h-4 w-px bg-slate-200 dark:bg-white/10 hidden sm:block" />

            <div className="hidden sm:flex items-center gap-3 text-slate-700 dark:text-slate-300 font-mono text-[11px]">
              <span>Avg CVRMSE: <strong className="text-cyan-700 dark:text-cyan-400">{avgCvrmse.toFixed(1)}%</strong></span>
              <span>Avg NMBE: <strong className="text-emerald-700 dark:text-emerald-400">{avgNmbe.toFixed(1)}%</strong></span>
              <span>Avg R&sup2;: <strong className="text-purple-700 dark:text-purple-400">{avgR2.toFixed(2)}</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs & Filters (Rendered only when multi-source or multi-condition is allowed) */}
      {(shouldShowTabs || (activeTab === 'calibration' && !filterCondition && availableConditions.length > 1)) && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          {shouldShowTabs && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('calibration')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === 'calibration'
                    ? 'bg-purple-600 text-white shadow-md shadow-purple-500/20'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200/80 dark:bg-white/5 dark:text-slate-400 dark:hover:text-white dark:border-white/5'
                }`}
              >
                Model & Calibration Metrics
              </button>
              <button
                onClick={() => setActiveTab('scenarios')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === 'scenarios'
                    ? 'bg-purple-600 text-white shadow-md shadow-purple-500/20'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200/80 dark:bg-white/5 dark:text-slate-400 dark:hover:text-white dark:border-white/5'
                }`}
              >
                Cross-Scenario Metrics
              </button>
            </div>
          )}

          {activeTab === 'calibration' && !filterCondition && availableConditions.length > 1 && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-slate-600 dark:text-slate-400 font-medium">Filter Condition:</span>
              <select
                value={filterExp}
                onChange={(e: any) => setFilterExp(e.target.value)}
                className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-white/10 rounded-lg px-2 py-1 text-slate-800 dark:text-slate-200 text-xs font-mono focus:outline-none shadow-sm cursor-pointer"
              >
                <option value="all">All Conditions</option>
                {availableConditions.map((cond: string) => (
                  <option key={cond} value={cond}>
                    {cond}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Metrics Table */}
      <div className="overflow-x-auto max-h-96 rounded-xl border border-slate-200/80 dark:border-white/5 shadow-sm">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100/95 dark:bg-slate-900/90 text-slate-600 dark:text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-slate-200/80 dark:border-white/10 sticky top-0 z-10 backdrop-blur-md">
              <th className="p-3">Variable</th>
              {shouldRenderConditionColumn && <th className="p-3">Condition</th>}
              {activeTab === 'scenarios' && <th className="p-3">Scenario</th>}
              <th className="p-3">MAE</th>
              <th className="p-3">RMSE</th>
              <th className="p-3">Max Error</th>
              <th className="p-3">R&sup2; Score</th>
              <th className="p-3">CVRMSE (%)</th>
              <th className="p-3">NMBE (%)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-white/5 font-mono">
            {displayMetrics.map((row, idx) => {
              if (!row) return null;
              const expName = String(row.Experiment || '');
              const isAfter = expName.toLowerCase().includes('after') || expName.toLowerCase().includes('calibrated');
              return (
                <tr
                  key={idx}
                  className={`hover:bg-slate-50/80 dark:hover:bg-white/5 transition-colors ${
                    isAfter ? 'bg-purple-50/70 dark:bg-purple-950/20' : ''
                  }`}
                >
                  <td className="p-3 font-semibold text-slate-900 dark:text-slate-100 font-sans">
                    {row.Variable || '-'}
                  </td>
                  {shouldRenderConditionColumn && (
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          isAfter
                            ? 'bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-500/20 dark:text-purple-300 dark:border-purple-500/30'
                            : 'bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-white/5'
                        }`}
                      >
                        {row.Experiment || 'Default'}
                      </span>
                    </td>
                  )}
                  {activeTab === 'scenarios' && (
                    <td className="p-3 text-cyan-700 dark:text-cyan-300 font-semibold font-sans">
                      {row.Scenario || 'Standard'}
                    </td>
                  )}
                  <td className="p-3 text-slate-700 dark:text-slate-300">{formatNumber(row.MAE, 3)}</td>
                  <td className="p-3 text-slate-900 dark:text-slate-100 font-bold">{formatNumber(row.RMSE, 3)}</td>
                  <td className="p-3 text-slate-600 dark:text-slate-400">{formatNumber(row['Max Error'], 2)}</td>
                  <td className="p-3">{getR2Badge(row.R2)}</td>
                  <td className="p-3">{getCvrmseBadge(row['CVRMSE (%)'])}</td>
                  <td className="p-3">{getNmbeBadge(row['NMBE (%)'])}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
