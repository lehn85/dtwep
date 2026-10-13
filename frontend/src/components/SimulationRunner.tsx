import React, { useState } from 'react';
import {
  Play,
  Square,
  Dna,
  Layers,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { ModuleInfo, LogMessage, GenerationUpdate } from '../types';
import { WSStatus } from '../services/websocket';
import { LiveTerminal } from './LiveTerminal';

interface SimulationRunnerProps {
  module: ModuleInfo | undefined;
  caseId: string;
  isRunning: boolean;
  wsStatus: WSStatus;
  statusMessage?: string;
  logs: LogMessage[];
  onClearLogs: () => void;
  onRunModule: (options?: { forceModelA?: boolean; gaParams?: { pop_size: number; generations: number; mutation_rate: number } }) => void;
  onStopModule: () => void;
  forceModelA: boolean;
  onToggleForceModelA: (val: boolean) => void;
  onViewResults: () => void;
  hasResults: boolean;
  generationHistory: GenerationUpdate[];
}

export const SimulationRunner: React.FC<SimulationRunnerProps> = ({
  module,
  caseId,
  isRunning,
  wsStatus,
  statusMessage,
  logs,
  onClearLogs,
  onRunModule,
  onStopModule,
  forceModelA,
  onToggleForceModelA,
  onViewResults,
  hasResults,
  generationHistory,
}) => {
  // GA Calibration Parameters State
  const [popSize, setPopSize] = useState<number>(8);
  const [generations, setGenerations] = useState<number>(5);
  const [mutationRate, setMutationRate] = useState<number>(0.15);

  const handleStartRun = () => {
    if (module?.is_calibration) {
      onRunModule({
        gaParams: {
          pop_size: popSize,
          generations: generations,
          mutation_rate: mutationRate,
        },
      });
    } else {
      onRunModule({
        forceModelA: forceModelA,
      });
    }
  };

  const latestGen = generationHistory[generationHistory.length - 1];

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Header & Module Overview Card */}
      <div className="glass-panel rounded-2xl p-6 relative overflow-hidden shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-500/30">
                {module?.is_calibration ? 'Genetic Algorithm Calibration' : 'Digital Twin Engine'}
              </span>
              <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                Case: <strong className="text-slate-700 dark:text-slate-200">{caseId}</strong>
              </span>
            </div>
            <h2 className="text-2xl font-display font-black text-slate-900 dark:text-white tracking-tight">
              {module?.name || 'Benchmark Experiment'}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 max-w-2xl leading-relaxed">
              {module?.description || 'Execute experiment and monitor live streaming logs from backend.'}
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center flex-wrap gap-3">
            {hasResults && (
              <button
                onClick={onViewResults}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-200 dark:hover:text-white border border-slate-200/90 dark:border-white/10 text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <span>View Results</span>
                <ArrowRight className="w-4 h-4 text-purple-500" />
              </button>
            )}

            {isRunning ? (
              <button
                onClick={onStopModule}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-semibold text-xs shadow-lg shadow-rose-500/30 border border-rose-400/30 transition-all cursor-pointer animate-pulse"
              >
                <Square className="w-4 h-4 fill-current" />
                <span>Stop Execution</span>
              </button>
            ) : (
              <button
                onClick={handleStartRun}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-bold text-xs shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 border border-emerald-400/30 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>{module?.is_calibration ? 'Start GA Calibration' : 'Run Simulation'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. Simulation Configuration Parameters */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Execution Controls & Parameters */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {module?.is_calibration ? (
            /* Calibration GA Parameters Card */
            <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4 shadow-md">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
                <Dna className="w-5 h-5 text-emerald-500" />
                <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                  Genetic Algorithm Parameters
                </h3>
              </div>

              <div className="space-y-4 text-xs">
                {/* Population Size */}
                <div className="space-y-1.5">
                  <div className="flex justify-between font-mono">
                    <span className="text-slate-600 dark:text-slate-400">Population Size:</span>
                    <span className="font-bold text-purple-600 dark:text-purple-400">{popSize}</span>
                  </div>
                  <input
                    type="range"
                    min={4}
                    max={20}
                    step={2}
                    value={popSize}
                    disabled={isRunning}
                    onChange={(e) => setPopSize(Number(e.target.value))}
                    className="w-full accent-purple-600 cursor-pointer"
                  />
                </div>

                {/* Generations */}
                <div className="space-y-1.5">
                  <div className="flex justify-between font-mono">
                    <span className="text-slate-600 dark:text-slate-400">Generations:</span>
                    <span className="font-bold text-cyan-600 dark:text-cyan-400">{generations}</span>
                  </div>
                  <input
                    type="range"
                    min={2}
                    max={20}
                    step={1}
                    value={generations}
                    disabled={isRunning}
                    onChange={(e) => setGenerations(Number(e.target.value))}
                    className="w-full accent-cyan-600 cursor-pointer"
                  />
                </div>

                {/* Mutation Rate */}
                <div className="space-y-1.5">
                  <div className="flex justify-between font-mono">
                    <span className="text-slate-600 dark:text-slate-400">Mutation Rate:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">{mutationRate}</span>
                  </div>
                  <input
                    type="range"
                    min={0.05}
                    max={0.5}
                    step={0.05}
                    value={mutationRate}
                    disabled={isRunning}
                    onChange={(e) => setMutationRate(Number(e.target.value))}
                    className="w-full accent-emerald-600 cursor-pointer"
                  />
                </div>
              </div>

              {/* Real-time GA Progress if running */}
              {generationHistory.length > 0 && (
                <div className="mt-2 p-3 rounded-xl bg-purple-50/80 dark:bg-purple-950/30 border border-purple-200/80 dark:border-purple-500/20 font-mono text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-600 dark:text-slate-400">Current Generation:</span>
                    <strong className="text-purple-600 dark:text-purple-300">#{latestGen?.generation}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600 dark:text-slate-400">Best Fitness:</span>
                    <strong className="text-emerald-600 dark:text-emerald-400">{latestGen?.best_fitness?.toFixed(4)}</strong>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Standard Module Execution Settings Card */
            <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4 shadow-md">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
                <Zap className="w-5 h-5 text-indigo-500" />
                <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                  Simulation Run Options
                </h3>
              </div>

              <div className="space-y-3">
                <label className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-white/5 cursor-pointer hover:border-purple-300 transition-colors">
                  <input
                    type="checkbox"
                    checked={forceModelA}
                    disabled={isRunning}
                    onChange={(e) => onToggleForceModelA(e.target.checked)}
                    className="mt-0.5 rounded bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-purple-600 focus:ring-purple-500 cursor-pointer"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 block">
                      Force Ground Truth Execution
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight block mt-0.5">
                      Force re-run ground truth model even if results exist on disk.
                    </span>
                  </div>
                </label>

                <div className="p-3 rounded-xl bg-slate-50/80 dark:bg-slate-900/40 border border-slate-200/80 dark:border-white/5 text-[11px] text-slate-600 dark:text-slate-400 space-y-1.5">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300">
                    <Layers className="w-3.5 h-3.5 text-purple-500" />
                    <span>Execution Pipeline:</span>
                  </div>
                  <p>1. Parallel co-simulation of Ground Truth and Digital Twin on EnergyPlus engine.</p>
                  <p>2. Computed results automatically generate MAE/RMSE metrics table and high-res Matplotlib plots.</p>
                </div>
              </div>
            </div>
          )}

          {/* Execution Status Card */}
          <div className="glass-panel rounded-2xl p-5 flex flex-col gap-3 shadow-md">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 dark:text-slate-300">Connection Status:</span>
              <span className={`px-2 py-0.5 rounded-full font-mono font-bold text-[10px] uppercase ${
                wsStatus === 'RUNNING'
                  ? 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300 animate-pulse'
                  : wsStatus === 'CONNECTED'
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                  : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
              }`}>
                {wsStatus}
              </span>
            </div>

            {statusMessage && (
              <div className="text-[11px] font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-900/80 p-2.5 rounded-xl border border-slate-200/80 dark:border-white/5">
                {statusMessage}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Terminal logs */}
        <div className="lg:col-span-8">
          <LiveTerminal
            logs={logs}
            onClear={onClearLogs}
            isRunning={isRunning}
          />
        </div>
      </div>
    </div>
  );
};
