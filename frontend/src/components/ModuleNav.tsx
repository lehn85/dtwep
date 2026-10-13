import React from 'react';
import { Play, Square, CheckCircle, BarChart3, Image, Compass, AlertTriangle, Layers } from 'lucide-react';
import { ModuleInfo } from '../types';

interface ModuleNavProps {
  modules: ModuleInfo[];
  selectedModuleId: string;
  onSelectModule: (modId: string) => void;
  isRunning: boolean;
  onRun: () => void;
  onStop: () => void;
  forceModelA: boolean;
  onToggleForceModelA: (val: boolean) => void;
}

export const ModuleNav: React.FC<ModuleNavProps> = ({
  modules,
  selectedModuleId,
  onSelectModule,
  isRunning,
  onRun,
  onStop,
  forceModelA,
  onToggleForceModelA,
}) => {
  const getIcon = (mod: ModuleInfo) => {
    if (mod.is_calibration || mod.id.includes('initial_calibration') || mod.id.includes('accuracy')) {
      return <BarChart3 className="w-4 h-4 text-purple-600 dark:text-purple-400" />;
    }
    if (mod.id.includes('scenario')) {
      return <Compass className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />;
    }
    if (mod.id.includes('recalibration') || mod.id.includes('degradation')) {
      return <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400" />;
    }
    return <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />;
  };

  const selectedMod = modules.find((m) => m.id === selectedModuleId);

  return (
    <div className="glass-panel rounded-2xl p-3 flex flex-col md:flex-row items-center justify-between gap-3 shadow-xl">
      {/* Module Tabs */}
      <div className="flex items-center flex-wrap gap-2 w-full md:w-auto">
        {modules.map((mod) => {
          const isSelected = mod.id === selectedModuleId;
          return (
            <button
              key={mod.id}
              onClick={() => onSelectModule(mod.id)}
              className={`flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer ${
                isSelected
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-500/25 border border-purple-400/40 font-display'
                  : 'bg-slate-100 hover:bg-slate-200/80 text-slate-700 hover:text-slate-900 border border-slate-200/80 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-300 dark:hover:text-white dark:border-white/5'
              }`}
            >
              {getIcon(mod)}
              <span>{mod.name}</span>

              {/* Status Badges */}
              {mod.has_metrics && (
                <span className={`flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border ${
                  isSelected
                    ? 'bg-emerald-400/20 text-emerald-100 border-emerald-300/30'
                    : 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30'
                }`}>
                  <CheckCircle className="w-2.5 h-2.5" />
                  Metrics
                </span>
              )}
              {mod.plot_count && mod.plot_count > 0 ? (
                <span className={`flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full border ${
                  isSelected
                    ? 'bg-cyan-400/20 text-cyan-100 border-cyan-300/30'
                    : 'bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-500/30'
                }`}>
                  <Image className="w-2.5 h-2.5" />
                  {mod.plot_count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {/* Execution Actions */}
      <div className="flex items-center gap-3 w-full md:w-auto justify-end">
        {/* Force Model A toggle */}
        {!selectedMod?.is_calibration && (
          <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer bg-slate-100/90 dark:bg-slate-900/60 px-3 py-1.5 rounded-xl border border-slate-200/80 dark:border-white/5 select-none hover:border-slate-300 dark:hover:border-white/20 transition-colors shadow-sm">
            <input
              type="checkbox"
              checked={forceModelA}
              onChange={(e) => onToggleForceModelA(e.target.checked)}
              className="rounded bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-purple-600 focus:ring-purple-500 focus:ring-offset-slate-100 dark:focus:ring-offset-slate-900 cursor-pointer"
            />
            <span className="text-[11px] font-mono text-slate-600 dark:text-slate-400">Force Ground Truth Run</span>
          </label>
        )}

        {/* Run / Stop Button */}
        {isRunning ? (
          <button
            onClick={onStop}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-semibold text-xs shadow-lg shadow-rose-500/30 border border-rose-400/30 transition-all cursor-pointer animate-pulse"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>Stop Execution</span>
          </button>
        ) : (
          <button
            onClick={onRun}
            className="flex items-center gap-2 px-6 py-2 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-semibold text-xs shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 border border-emerald-400/30 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run Experiment</span>
          </button>
        )}
      </div>
    </div>
  );
};

export const ExperimentNav = ModuleNav;
