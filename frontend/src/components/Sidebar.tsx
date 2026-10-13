import React, { useState, useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  ChevronDown,
  ChevronRight,
  Layers,
  Info,
  BarChart3,
  Compass,
  AlertTriangle,
  FileCode2,
  PlayCircle,
  PieChart,
  LineChart,
  TableProperties,
  Images,
  Settings as SettingsIcon,
  Sparkles,
  Building,
  Sprout,
  Cpu,
  CheckCircle2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { CaseSummary, CaseDetail, ModuleInfo } from "../types";
import { WSStatus } from "../services/websocket";

export type NavViewType =
  | "case-info"
  | "case-config"
  | "exp-config"
  | "exp-run"
  | "exp-results"
  | "settings";

export type ResultSubTab = "all" | "charts" | "metrics" | "plots";

interface SidebarProps {
  cases: CaseSummary[];
  selectedCaseId: string;
  onSelectCase: (caseId: string) => void;
  caseDetail: CaseDetail | null;
  selectedModuleId: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  wsStatus: WSStatus;
}

export const Sidebar: React.FC<SidebarProps> = ({
  cases,
  selectedCaseId,
  onSelectCase,
  caseDetail,
  selectedModuleId,
  isCollapsed,
  onToggleCollapse,
  wsStatus,
}) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Track open state for module accordions and sections
  const [openModules, setOpenModules] = useState<Record<string, boolean>>(() => {
    return selectedModuleId ? { [selectedModuleId]: true } : {};
  });
  const [openResultsDropdown, setOpenResultsDropdown] = useState<Record<string, boolean>>(() => {
    return selectedModuleId ? { [selectedModuleId]: true } : {};
  });

  // Auto expand newly selected module and its result dropdown when selectedModuleId changes
  useEffect(() => {
    if (selectedModuleId) {
      setOpenModules((prev) => ({ ...prev, [selectedModuleId]: true }));
      setOpenResultsDropdown((prev) => ({ ...prev, [selectedModuleId]: true }));
    }
  }, [selectedModuleId]);

  // Auto expand results dropdown when navigating into results sub-page
  useEffect(() => {
    if (location.pathname.includes("/results")) {
      if (selectedModuleId) {
        setOpenResultsDropdown((prev) => ({ ...prev, [selectedModuleId]: true }));
      }
    }
  }, [location.pathname, selectedModuleId]);

  const toggleModuleAccordion = (modId: string, e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    setOpenModules((prev) => ({
      ...prev,
      [modId]: !prev[modId],
    }));
  };

  const toggleResultsAccordion = (modId: string, e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    setOpenResultsDropdown((prev) => ({
      ...prev,
      [modId]: !prev[modId],
    }));
  };

  const handleModuleHeaderClick = (modId: string) => {
    setOpenModules((prev) => ({ ...prev, [modId]: true }));
    setOpenResultsDropdown((prev) => ({ ...prev, [modId]: true }));

    const pathname = location.pathname;
    if (pathname.includes("/results/metrics")) {
      navigate(`/case/${selectedCaseId}/exp/${modId}/results/metrics`);
    } else if (pathname.includes("/results/charts")) {
      navigate(`/case/${selectedCaseId}/exp/${modId}/results/charts`);
    } else if (pathname.includes("/results/plots")) {
      navigate(`/case/${selectedCaseId}/exp/${modId}/results/plots`);
    } else if (pathname.includes("/results")) {
      navigate(`/case/${selectedCaseId}/exp/${modId}/results`);
    } else if (pathname.includes("/config")) {
      navigate(`/case/${selectedCaseId}/exp/${modId}/config`);
    } else {
      navigate(`/case/${selectedCaseId}/exp/${modId}/run`);
    }
  };

  const getCaseIcon = (iconName?: string) => {
    switch (iconName?.toLowerCase()) {
      case "sprout":
        return <Sprout className="w-4 h-4 text-emerald-500" />;
      case "cpu":
        return <Cpu className="w-4 h-4 text-cyan-500" />;
      default:
        return <Building className="w-4 h-4 text-purple-500" />;
    }
  };

  const getModuleIcon = (mod: ModuleInfo) => {
    if (mod.is_calibration || mod.id.includes("initial_calibration") || mod.id.includes("accuracy"))
      return <BarChart3 className="w-4 h-4 text-purple-500" />;
    if (mod.id.includes("scenario"))
      return <Compass className="w-4 h-4 text-cyan-500" />;
    if (mod.id.includes("recalibration") || mod.id.includes("degradation"))
      return <AlertTriangle className="w-4 h-4 text-rose-500" />;
    return <Layers className="w-4 h-4 text-indigo-500" />;
  };

  const modules = caseDetail?.modules || caseDetail?.experiments || [];
  const currentCase = cases.find((c) => c.id === selectedCaseId);

  const handleCaseChange = (newCaseId: string) => {
    onSelectCase(newCaseId);
    navigate(`/case/${newCaseId}/info`);
  };

  return (
    <aside
      className={`sticky top-0 h-screen shrink-0 flex flex-col justify-between transition-all duration-300 ease-in-out border-r z-30 select-none ${
        isCollapsed ? "w-20 min-w-[5rem]" : "w-72 min-w-[18rem]"
      } bg-white/90 dark:bg-slate-950/90 backdrop-blur-xl border-slate-200/90 dark:border-white/10 shadow-lg`}
    >
      {/* 1. TOP BRAND HEADER */}
      <div className="p-4 border-b border-slate-100 dark:border-white/10 flex items-center justify-between">
        {!isCollapsed ? (
          <NavLink
            to={`/case/${selectedCaseId || "greenhouse"}/info`}
            className="flex items-center gap-3 overflow-hidden group cursor-pointer"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 p-0.5 flex items-center justify-center shadow-md shadow-purple-500/20 shrink-0 group-hover:scale-105 transition-transform">
              <div className="w-full h-full bg-white dark:bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-purple-600 dark:text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div className="truncate">
              <h1 className="font-display font-black text-sm tracking-tight bg-gradient-to-r from-purple-700 via-indigo-700 to-cyan-600 dark:from-purple-300 dark:via-indigo-200 dark:to-cyan-300 bg-clip-text text-transparent truncate">
                DTEP
              </h1>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                Digital Twin Energy
              </p>
            </div>
          </NavLink>
        ) : (
          <NavLink
            to={`/case/${selectedCaseId || "greenhouse"}/info`}
            className="mx-auto w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 p-0.5 flex items-center justify-center shadow-md cursor-pointer hover:scale-105 transition-transform"
          >
            <div className="w-full h-full bg-white dark:bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-purple-600 dark:text-cyan-400" />
            </div>
          </NavLink>
        )}

        <button
          onClick={onToggleCollapse}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10 transition-colors"
        >
          {isCollapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* 2. SCROLLABLE NAVIGATION MENU */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-thin">
        {/* ======================================================== */}
        {/* SECTION 1: CASE SELECTOR & CASE INFO */}
        {/* ======================================================== */}
        <div className="space-y-2">
          {/* Case Selector Dropdown */}
          <div className="relative">
            {!isCollapsed ? (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-100/90 dark:bg-slate-900/90 border border-slate-200/90 dark:border-white/10 shadow-sm transition-colors">
                  <div className="p-1.5 rounded-lg bg-white dark:bg-slate-800 shadow-xs shrink-0">
                    {getCaseIcon(currentCase?.icon)}
                  </div>
                  <select
                    value={selectedCaseId}
                    onChange={(e) => handleCaseChange(e.target.value)}
                    className="w-full bg-transparent text-xs font-semibold text-slate-800 dark:text-slate-100 focus:outline-none cursor-pointer truncate"
                  >
                    {cases.map((c) => (
                      <option
                        key={c.id}
                        value={c.id}
                        className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                      >
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                {/* Case Type Badge */}
                <div className="flex items-center justify-between px-1">
                  <span
                    className={`text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded-md border ${
                      currentCase?.type === "physical"
                        ? "bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20"
                        : "bg-purple-100 dark:bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-500/20"
                    }`}
                  >
                    {currentCase?.type === "physical" ? "🏭 Physical Twin" : "🔬 Virtual Twin"}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {currentCase?.category || "Building Energy"}
                  </span>
                </div>
              </div>
            ) : (
              <div
                title={`${currentCase?.name || selectedCaseId} (${currentCase?.type === "physical" ? "Physical Twin" : "Virtual Twin"})`}
                className={`flex items-center justify-center p-2.5 rounded-xl border ${
                  currentCase?.type === "physical"
                    ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20"
                    : "bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-300 border-purple-200 dark:border-purple-500/20"
                }`}
              >
                {getCaseIcon(currentCase?.icon)}
              </div>
            )}
          </div>

          {/* Sub-item: Case Info */}
          <NavLink
            to={`/case/${selectedCaseId}/info`}
            title="Case Overview & Details"
            className={({ isActive }) =>
              `w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? "bg-purple-600 text-white font-semibold shadow-md shadow-purple-500/25"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5"
              } ${isCollapsed ? "justify-center px-2" : ""}`
            }
          >
            {({ isActive }) => (
              <>
                <Info
                  className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-purple-500"}`}
                />
                {!isCollapsed && <span>Case Info</span>}
              </>
            )}
          </NavLink>
        </div>

        {/* ======================================================== */}
        {/* SECTION 2: MODULES (Multi-level Tree with Routing) */}
        {/* ======================================================== */}
        <div className="space-y-2">
          {!isCollapsed && (
            <div className="flex items-center justify-between px-2 pt-2 border-t border-slate-100 dark:border-white/5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-display">
                {currentCase?.type === "physical" ? "Operational Workflow" : "Experiments List"}
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300">
                {modules.length} {currentCase?.type === "physical" ? "Modules" : "Experiments"}
              </span>
            </div>
          )}

          <div className="space-y-1">
            {modules.map((mod) => {
              const isSelectedMod = mod.id === selectedModuleId;
              const isAccordionOpen = !!openModules[mod.id];
              const isResultOpen = !!openResultsDropdown[mod.id];

              if (isCollapsed) {
                return (
                  <NavLink
                    key={mod.id}
                    to={`/case/${selectedCaseId}/exp/${mod.id}/run`}
                    title={`${mod.name} - ${mod.description}`}
                    className={({ isActive }) =>
                      `w-full flex items-center justify-center p-2.5 rounded-xl transition-all ${
                        isActive || isSelectedMod
                          ? "bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-300/50 shadow-sm"
                          : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5"
                      }`
                    }
                  >
                    {getModuleIcon(mod)}
                  </NavLink>
                );
              }

              return (
                <div
                  key={mod.id}
                  className={`rounded-xl border transition-all ${
                    isSelectedMod
                      ? "bg-slate-50/80 dark:bg-slate-900/60 border-purple-300/60 dark:border-purple-500/30 shadow-xs"
                      : "border-transparent hover:border-slate-200 dark:hover:border-white/5"
                  }`}
                >
                  {/* Module Header Item */}
                  <div
                    onClick={() => handleModuleHeaderClick(mod.id)}
                    className={`flex items-center justify-between p-2 rounded-xl text-xs font-semibold cursor-pointer select-none transition-colors ${
                      isSelectedMod
                        ? "text-purple-900 dark:text-purple-200"
                        : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      {getModuleIcon(mod)}
                      <span className="truncate">{mod.name}</span>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {mod.has_metrics && (
                        <span title="Has metrics results">
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={(e) => toggleModuleAccordion(mod.id, e)}
                        title={
                          isAccordionOpen
                            ? "Collapse Experiment"
                            : "Expand Experiment"
                        }
                        className="p-1 hover:bg-slate-200/80 dark:hover:bg-white/10 rounded-md transition-colors text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer"
                      >
                        {isAccordionOpen ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Multi-level Sub-items (Config, Run, Results) */}
                  {isAccordionOpen && (
                    <div className="pl-4 pr-1.5 py-1.5 space-y-1 text-xs border-t border-slate-100 dark:border-white/5">
                      {/* Sub-item: Configuration */}
                      <NavLink
                        to={`/case/${selectedCaseId}/exp/${mod.id}/config`}
                        className={({ isActive }) =>
                          `w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                            isActive
                              ? "bg-purple-600 text-white font-semibold shadow-xs"
                              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/5"
                          }`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <FileCode2
                              className={`w-3.5 h-3.5 ${isActive ? "text-white" : "text-indigo-500"}`}
                            />
                            <span>Configuration (Config)</span>
                          </>
                        )}
                      </NavLink>

                      {/* Sub-item: Run simulation */}
                      <NavLink
                        to={`/case/${selectedCaseId}/exp/${mod.id}/run`}
                        className={({ isActive }) =>
                          `w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                            isActive
                              ? "bg-purple-600 text-white font-semibold shadow-xs"
                              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/5"
                          }`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <PlayCircle
                              className={`w-3.5 h-3.5 ${isActive ? "text-white" : "text-emerald-500"}`}
                            />
                            <span>Run Simulation</span>
                          </>
                        )}
                      </NavLink>

                      {/* Sub-item: Results (Nested Dropdown) */}
                      <div className="space-y-0.5">
                        <div
                          className={`flex items-center justify-between rounded-lg transition-colors ${
                            location.pathname ===
                            `/case/${selectedCaseId}/exp/${mod.id}/results`
                              ? "bg-purple-600 text-white font-semibold shadow-xs"
                              : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/5"
                          }`}
                        >
                          <NavLink
                            to={`/case/${selectedCaseId}/exp/${mod.id}/results`}
                            end
                            className="flex items-center gap-2 flex-1 px-2.5 py-1.5 text-xs truncate"
                          >
                            <PieChart
                              className={`w-3.5 h-3.5 ${location.pathname === `/case/${selectedCaseId}/exp/${mod.id}/results` ? "text-white" : "text-cyan-500"}`}
                            />
                            <span className="truncate">Results (All)</span>
                          </NavLink>

                          <button
                            type="button"
                            onClick={(e) => toggleResultsAccordion(mod.id, e)}
                            title={
                              isResultOpen
                                ? "Collapse results menu"
                                : "Expand results menu"
                            }
                            className="p-1 mr-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors cursor-pointer text-current opacity-70 hover:opacity-100"
                          >
                            {isResultOpen ? (
                              <ChevronDown className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>

                        {/* Nested Results Sub-types */}
                        {isResultOpen && (
                          <div className="pl-4 space-y-0.5 pt-0.5 border-l-2 border-slate-200 dark:border-slate-800 ml-3">
                            <NavLink
                              to={`/case/${selectedCaseId}/exp/${mod.id}/results/charts`}
                              className={({ isActive }) =>
                                `w-full flex items-center gap-2 px-2 py-1 rounded text-[11px] transition-colors ${
                                  isActive
                                    ? "bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 font-semibold"
                                    : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5"
                                }`
                              }
                            >
                              <LineChart className="w-3 h-3 text-cyan-500" />
                              <span>Analysis Charts</span>
                            </NavLink>

                            <NavLink
                              to={`/case/${selectedCaseId}/exp/${mod.id}/results/metrics`}
                              className={({ isActive }) =>
                                `w-full flex items-center gap-2 px-2 py-1 rounded text-[11px] transition-colors ${
                                  isActive
                                    ? "bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 font-semibold"
                                    : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5"
                                }`
                              }
                            >
                              <TableProperties className="w-3 h-3 text-indigo-500" />
                              <span>Metrics Table</span>
                            </NavLink>

                            <NavLink
                              to={`/case/${selectedCaseId}/exp/${mod.id}/results/plots`}
                              className={({ isActive }) =>
                                `w-full flex items-center justify-between px-2 py-1 rounded text-[11px] transition-colors ${
                                  isActive
                                    ? "bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 font-semibold"
                                    : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5"
                                }`
                              }
                            >
                              <div className="flex items-center gap-2">
                                <Images className="w-3 h-3 text-rose-500" />
                                <span>Plot Gallery</span>
                              </div>
                              {mod.plot_count && mod.plot_count > 0 ? (
                                <span className="text-[9px] font-mono px-1 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                                  {mod.plot_count}
                                </span>
                              ) : null}
                            </NavLink>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 3. BOTTOM FOOTER STATUS */}
      <div className="p-3 border-t border-slate-100 dark:border-white/10 bg-slate-50/50 dark:bg-slate-900/40">
        <div className="space-y-2">                 
          {/* Settings Panel Nav Item */}
          <NavLink
            to="/settings"
            title="System Settings & Connection Status"
            className={({ isActive }) =>
              `w-full flex items-center gap-2.5 py-2 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? "bg-purple-600 text-white font-semibold shadow-md shadow-purple-500/25"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5"
              } ${isCollapsed ? "justify-center px-2" : ""}`
            }
          >
            {({ isActive }) => (
              <>
                <SettingsIcon
                  className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-slate-500"}`}
                />
                {!isCollapsed && <span>System Settings</span>}
              </>
            )}
          </NavLink>
        </div>
        {!isCollapsed ? (
          <div className="flex items-center justify-between text-xs mt-2">
            <div className="flex items-center gap-2">
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  wsStatus === "RUNNING"
                    ? "bg-cyan-500 animate-pulse"
                    : wsStatus === "CONNECTED"
                      ? "bg-emerald-500"
                      : "bg-rose-500"
                }`}
              />
              <span className="font-mono text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                {wsStatus}
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-400">v0.3.0</span>
          </div>
        ) : (
          <div
            className="flex justify-center mt-2"
            title={`Status: ${wsStatus}`}
          >
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                wsStatus === "RUNNING"
                  ? "bg-cyan-500 animate-pulse"
                  : wsStatus === "CONNECTED"
                    ? "bg-emerald-500"
                    : "bg-rose-500"
              }`}
            />
          </div>
        )}
      </div>
    </aside>
  );
};
