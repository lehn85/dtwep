import React from 'react';
import {
  Sun,
  Moon,
  Server,
  Activity,
  Layers,
  Database,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { CaseSummary } from '../types';
import { WSStatus, getWebSocketUrl } from '../services/websocket';
import { API_BASE } from '../services/api';

interface SettingsPanelProps {
  cases: CaseSummary[];
  selectedCaseId: string;
  wsStatus: WSStatus;
  statusMessage?: string;
  onRefreshCases: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  cases,
  selectedCaseId,
  wsStatus,
  statusMessage,
  onRefreshCases,
}) => {
  const { theme, setTheme, isDark } = useTheme();

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      {/* Header */}
      <div className="glass-panel rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 p-0.5 flex items-center justify-center text-white shadow-md">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-2xl font-display font-black text-slate-900 dark:text-white tracking-tight">
              Settings & System
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Manage user interface, backend API connection, and Digital Twin runtime diagnostics.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. Theme Selection Card */}
        <div className="glass-panel rounded-2xl p-6 shadow-md flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
              <Sun className="w-5 h-5 text-amber-500" />
              <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                Application Theme
              </h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Select the color theme suited for your workstation environment.
            </p>

            <div className="grid grid-cols-2 gap-3 mt-4">
              {/* Light Theme Card */}
              <button
                onClick={() => setTheme('light')}
                className={`p-4 rounded-xl border flex flex-col items-center gap-2.5 transition-all cursor-pointer ${
                  !isDark
                    ? 'border-purple-500 bg-purple-50 text-purple-900 shadow-md ring-2 ring-purple-500/20'
                    : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/20 bg-slate-50/50 dark:bg-slate-900/40 text-slate-600 dark:text-slate-400'
                }`}
              >
                <div className="p-3 rounded-full bg-amber-100 text-amber-600 shadow-xs">
                  <Sun className="w-6 h-6" />
                </div>
                <div className="text-center">
                  <span className="text-xs font-bold block">Light Mode</span>
                  <span className="text-[10px] opacity-75">Clean & High-Contrast</span>
                </div>
                {!isDark && (
                  <CheckCircle2 className="w-4 h-4 text-purple-600 mt-1" />
                )}
              </button>

              {/* Dark Theme Card */}
              <button
                onClick={() => setTheme('dark')}
                className={`p-4 rounded-xl border flex flex-col items-center gap-2.5 transition-all cursor-pointer ${
                  isDark
                    ? 'border-purple-500 bg-purple-950/40 text-purple-300 shadow-md ring-2 ring-purple-500/20'
                    : 'border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/20 bg-slate-50/50 dark:bg-slate-900/40 text-slate-600 dark:text-slate-400'
                }`}
              >
                <div className="p-3 rounded-full bg-purple-900/40 text-purple-400 shadow-xs">
                  <Moon className="w-6 h-6" />
                </div>
                <div className="text-center">
                  <span className="text-xs font-bold block">Dark Mode</span>
                  <span className="text-[10px] opacity-75">Low-Eye-Strain</span>
                </div>
                {isDark && (
                  <CheckCircle2 className="w-4 h-4 text-purple-400 mt-1" />
                )}
              </button>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-900/60 p-2.5 rounded-xl">
            Current theme: <strong>{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</strong>
          </div>
        </div>

        {/* 2. Backend Connection & API Status */}
        <div className="glass-panel rounded-2xl p-6 shadow-md flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
              <Server className="w-5 h-5 text-indigo-500" />
              <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                API Server & WebSocket
              </h3>
            </div>
            
            <div className="space-y-3 mt-3">
              <div className="flex items-center justify-between text-xs font-mono p-2.5 rounded-xl bg-slate-100 dark:bg-slate-900/80">
                <span className="text-slate-600 dark:text-slate-400">API Base:</span>
                <span className="font-semibold text-slate-900 dark:text-slate-200 truncate max-w-[200px]" title={API_BASE}>{API_BASE}</span>
              </div>

              <div className="flex items-center justify-between text-xs font-mono p-2.5 rounded-xl bg-slate-100 dark:bg-slate-900/80">
                <span className="text-slate-600 dark:text-slate-400">WebSocket Endpoint:</span>
                <span className="font-semibold text-slate-900 dark:text-slate-200 truncate max-w-[200px]" title={getWebSocketUrl()}>{getWebSocketUrl()}</span>
              </div>

              <div className="flex items-center justify-between text-xs font-mono p-2.5 rounded-xl bg-slate-100 dark:bg-slate-900/80">
                <span className="text-slate-600 dark:text-slate-400">Connection Status:</span>
                <span className={`px-2 py-0.5 rounded-md font-bold text-[10px] uppercase ${
                  wsStatus === 'CONNECTED'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                    : wsStatus === 'RUNNING'
                    ? 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300 animate-pulse'
                    : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                }`}>
                  {wsStatus}
                </span>
              </div>

              {statusMessage && (
                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 px-1">
                  Status Message: {statusMessage}
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={onRefreshCases}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-xs font-medium text-slate-700 dark:text-slate-300 transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              <span>Reload Cases Data</span>
            </button>
          </div>
        </div>

        {/* 3. Cases Registry Summary */}
        <div className="glass-panel rounded-2xl p-6 shadow-md">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
            <Layers className="w-5 h-5 text-cyan-500" />
            <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
              Available Cases Registry ({cases.length})
            </h3>
          </div>

          <div className="space-y-2 mt-3 max-h-52 overflow-y-auto pr-1">
            {cases.map((c) => (
              <div
                key={c.id}
                className={`p-3 rounded-xl border flex items-center justify-between text-xs transition-colors ${
                  c.id === selectedCaseId
                    ? 'border-purple-300 bg-purple-50/50 dark:border-purple-500/30 dark:bg-purple-950/20'
                    : 'border-slate-200/80 dark:border-white/5 bg-slate-50/30 dark:bg-slate-900/30'
                }`}
              >
                <div>
                  <h4 className="font-bold text-slate-900 dark:text-white">{c.name}</h4>
                  <span className="font-mono text-[10px] text-slate-500 dark:text-slate-400">ID: {c.id} &bull; {c.category}</span>
                </div>
                {c.id === selectedCaseId && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-600 text-white font-semibold">
                    Active Case
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 4. Platform Overview */}
        <div className="glass-panel rounded-2xl p-6 shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-white/5">
              <Info className="w-5 h-5 text-purple-500" />
              <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                Platform Overview
              </h3>
            </div>

            <div className="space-y-2 mt-3 text-xs text-slate-600 dark:text-slate-300">
              <p>
                <strong>Digital Twin Energy Platform (DTEP)</strong> is a multi-model co-simulation and building energy calibration platform.
              </p>
              <ul className="list-disc list-inside space-y-1 text-slate-500 dark:text-slate-400 pt-1">
                <li>Supports high-fidelity Model A and calibrated digital twin Model B.</li>
                <li>Automated calculation of validation error metrics (MAE, RMSE, CVRMSE, NMBE, R²).</li>
                <li>Responsive UI layout tailored for desktop and ultrawide monitor setups.</li>
              </ul>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <span>Version v0.3.0</span>
            <span className="font-mono">Engine: EnergyPlus / OpenStudio</span>
          </div>
        </div>
      </div>
    </div>
  );
};
