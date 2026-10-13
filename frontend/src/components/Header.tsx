import React, { useState, useEffect } from 'react';
import {
  Clock,
  RefreshCw,
  Sun,
  Moon,
  ChevronRight,
  Play,
  Square,
  PanelLeft,
  Info,
  FileCode2,
  PlayCircle,
  PieChart,
  Settings as SettingsIcon,
  Sliders,
} from 'lucide-react';
import { CaseSummary, ModuleInfo } from '../types';
import { WSStatus } from '../services/websocket';
import { useTheme } from '../context/ThemeContext';
import { NavViewType, ResultSubTab } from './Sidebar';

interface HeaderProps {
  cases: CaseSummary[];
  selectedCaseId: string;
  onSelectCase: (caseId: string) => void;
  selectedModule: ModuleInfo | undefined;
  activeView: NavViewType;
  activeResultSubTab: ResultSubTab;
  wsStatus: WSStatus;
  statusMessage?: string;
  onRefresh: () => void;
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  isRunning: boolean;
  onRun: () => void;
  onStop: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  cases,
  selectedCaseId,
  selectedModule,
  activeView,
  activeResultSubTab,
  wsStatus,
  statusMessage: _statusMessage,
  onRefresh,
  isSidebarCollapsed,
  onToggleSidebar,
  isRunning,
  onRun,
  onStop,
}) => {
  const { theme, toggleTheme } = useTheme();
  const [time, setTime] = useState<string>('');
  const isDark = theme === 'dark';

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: WSStatus) => {
    switch (status) {
      case 'RUNNING':
        return 'bg-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.8)] animate-pulse';
      case 'CONNECTED':
        return 'bg-emerald-500 shadow-[0_0_12px_rgba(10,185,129,0.8)]';
      case 'CONNECTING':
        return 'bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.8)] animate-pulse';
      default:
        return 'bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.8)]';
    }
  };

  const currentCase = cases.find((c) => c.id === selectedCaseId);

  const getViewTitle = () => {
    switch (activeView) {
      case 'case-info':
        return { label: 'Case Info', icon: <Info className="w-3.5 h-3.5 text-purple-500" /> };
      case 'case-config':
        return { label: 'Case Config (calibration.yaml)', icon: <Sliders className="w-3.5 h-3.5 text-purple-500" /> };
      case 'exp-config':
        return { label: 'Experiment Config (Config YAML)', icon: <FileCode2 className="w-3.5 h-3.5 text-indigo-500" /> };
      case 'exp-run':
        return { label: 'Run Experiment', icon: <PlayCircle className="w-3.5 h-3.5 text-emerald-500" /> };
      case 'exp-results':
        let subText = '';
        if (activeResultSubTab === 'charts') subText = ' (Charts)';
        else if (activeResultSubTab === 'metrics') subText = ' (Metrics)';
        else if (activeResultSubTab === 'plots') subText = ' (Plot Gallery)';
        return { label: `Results${subText}`, icon: <PieChart className="w-3.5 h-3.5 text-cyan-500" /> };
      case 'settings':
        return { label: 'System Settings', icon: <SettingsIcon className="w-3.5 h-3.5 text-slate-500" /> };
      default:
        return { label: '', icon: null };
    }
  };

  const viewInfo = getViewTitle();

  return (
    <header className="glass-panel sticky top-0 z-20 px-4 md:px-6 py-3.5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4 transition-all shadow-md">
      {/* Left: Sidebar Toggle & Breadcrumb Navigation */}
      <div className="flex items-center gap-3 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
        <button
          onClick={onToggleSidebar}
          title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-300 transition-colors shrink-0"
        >
          <PanelLeft className="w-4 h-4" />
        </button>

        {/* Breadcrumbs */}
        <nav className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
          {/* Case Name & Type */}
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-slate-900 dark:text-white">
              {currentCase?.name || selectedCaseId}
            </span>
            <span
              className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border ${
                currentCase?.type === 'physical'
                  ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20'
                  : 'bg-purple-100 dark:bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-500/20'
              }`}
            >
              {currentCase?.type === 'physical' ? '🏭 Physical' : '🔬 Virtual'}
            </span>
          </div>

          {/* Module Name (if applicable) */}
          {activeView !== 'case-info' && activeView !== 'case-config' && activeView !== 'settings' && selectedModule && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-purple-600 dark:text-purple-400 font-semibold">
                {selectedModule.name}
              </span>
            </>
          )}

          {/* Current Action / View */}
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="flex items-center gap-1.5 text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-white/10 px-2 py-0.5 rounded-md font-mono text-[11px]">
            {viewInfo.icon}
            <span>{viewInfo.label}</span>
          </span>
        </nav>
      </div>

      {/* Right: Quick Run Action, Theme Switch, Status & Clock */}
      <div className="flex items-center flex-wrap gap-2.5 w-full md:w-auto justify-end">
        {/* Quick Run / Stop button if in module view */}
        {activeView !== 'case-info' && activeView !== 'case-config' && activeView !== 'settings' && (
          <div className="shrink-0">
            {isRunning ? (
              <button
                onClick={onStop}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs shadow-md shadow-rose-500/20 transition-all cursor-pointer animate-pulse"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Stop</span>
              </button>
            ) : (
              <button
                onClick={onRun}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs shadow-md shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run</span>
              </button>
            )}
          </div>
        )}

        {/* Server Status Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 text-xs">
          <div className={`w-2 h-2 rounded-full ${getStatusColor(wsStatus)}`} />
          <span className="font-mono text-[11px] text-slate-700 dark:text-slate-300 font-medium">
            {wsStatus}
          </span>
        </div>

        {/* Refresh Action */}
        <button
          onClick={onRefresh}
          title="Reload Data"
          className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-300 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>

        {/* Dark/Light Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-300 transition-colors"
        >
          {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-indigo-500" />}
        </button>

        {/* Clock */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-white/5 border border-slate-200/80 dark:border-white/5 text-xs text-slate-600 dark:text-slate-400 font-mono">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>{time}</span>
        </div>
      </div>
    </header>
  );
};
