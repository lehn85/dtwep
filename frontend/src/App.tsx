import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Routes,
  Route,
  Navigate,
  useLocation,
  useNavigate,
  useParams,
  NavLink,
} from 'react-router-dom';
import {
  fetchCases,
  fetchCaseDetail,
  fetchConfig,
  fetchResults,
  saveConfig,
  stopProcesses,
} from './services/api';
import { ExecutionWebSocket, WSStatus } from './services/websocket';
import {
  CaseDetail,
  CaseSummary,
  ConfigInfo,
  GenerationUpdate,
  LogMessage,
  ResultsData,
  ModuleInfo,
} from './types';
import { Sidebar, NavViewType, ResultSubTab } from './components/Sidebar';
import { Header } from './components/Header';
import { CaseOverview } from './components/CaseOverview';
import { ConfigEditor } from './components/ConfigEditor';
import { SimulationRunner } from './components/SimulationRunner';
import { ChartsPanel } from './components/ChartsPanel';
import { MetricsTable } from './components/MetricsTable';
import { PlotGallery } from './components/PlotGallery';
import { SettingsPanel } from './components/SettingsPanel';
import {
  AlertCircle,
  Loader2,
  LineChart,
  TableProperties,
  Images,
  LayoutGrid,
  Sliders,
} from 'lucide-react';

interface ResultsViewProps {
  selectedModule: ModuleInfo | undefined;
  selectedCaseId: string;
  selectedModuleId: string;
  activeResults: ResultsData | null;
  generationHistory: GenerationUpdate[];
  isRunning: boolean;
  activeSubTab?: ResultSubTab;
  caseDetail?: CaseDetail | null;
}

const ResultsView: React.FC<ResultsViewProps> = ({
  selectedModule,
  selectedCaseId,
  selectedModuleId,
  activeResults,
  generationHistory,
  isRunning,
  activeSubTab: propSubTab,
  caseDetail,
}) => {
  const { caseId: paramCaseId, expId: paramExpId, subTab: paramSubTab } = useParams<{ caseId?: string; expId?: string; subTab?: string }>();
  const currentCaseId = paramCaseId || selectedCaseId;
  const currentModId = paramExpId || selectedModuleId;
  const currentMod = selectedModule?.id === currentModId ? selectedModule : (caseDetail?.modules || caseDetail?.experiments)?.find((e) => e.id === currentModId);
  const subTab = (propSubTab || paramSubTab || 'all') as ResultSubTab;

  const isCurrentResults = activeResults?.exp_id === currentModId || activeResults?.mod_id === currentModId;
  const displayResults = isCurrentResults ? activeResults : null;

  return (
    <div className="space-y-6">
      {/* Results Header with Sub-tabs Filter */}
      <div className="glass-panel rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-md">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              Experiment Results:
            </span>
            <span className="text-sm font-bold font-display text-purple-700 dark:text-purple-300">
              {currentMod?.name || currentModId}
            </span>
          </div>
          <h2 className="text-xl font-display font-black text-slate-900 dark:text-white tracking-tight mt-0.5">
            Analysis & Result Charts
          </h2>
        </div>

        {/* Sub-tab Filter Navigation Links */}
        <div className="flex items-center flex-wrap gap-1.5 bg-slate-100 dark:bg-slate-900/80 p-1.5 rounded-xl border border-slate-200/80 dark:border-white/5">
          <NavLink
            to={`/case/${currentCaseId}/exp/${currentModId}/results`}
            end
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive && subTab === 'all'
                  ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`
            }
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>All</span>
          </NavLink>

          <NavLink
            to={`/case/${currentCaseId}/exp/${currentModId}/results/charts`}
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`
            }
          >
            <LineChart className="w-3.5 h-3.5" />
            <span>Analysis Charts</span>
          </NavLink>

          <NavLink
            to={`/case/${currentCaseId}/exp/${currentModId}/results/metrics`}
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`
            }
          >
            <TableProperties className="w-3.5 h-3.5" />
            <span>Metrics Table</span>
          </NavLink>

          <NavLink
            to={`/case/${currentCaseId}/exp/${currentModId}/results/plots`}
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-white dark:bg-purple-600 text-purple-700 dark:text-white shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`
            }
          >
            <Images className="w-3.5 h-3.5" />
            <span>Plot Gallery ({displayResults?.plots?.length || 0})</span>
          </NavLink>
        </div>
      </div>

      {/* Render Results Content based on filter */}
      <div className="space-y-6">
        {(subTab === 'all' || subTab === 'charts') && (
          <ChartsPanel
            key={`charts-${currentModId}-${displayResults?.exp_id}`}
            generationHistory={generationHistory}
            calibrationHistory={displayResults?.calibration_history}
            timeseriesData={displayResults?.timeseries}
            metrics={displayResults?.metrics || []}
            scenariosMetrics={displayResults?.scenarios_metrics}
            isRunning={isRunning}
            caseDetail={caseDetail}
            selectedExp={currentMod}
            expConfig={displayResults?.exp_config || displayResults?.mod_config}
            outputs={displayResults?.outputs}
            performance={displayResults?.performance}
            variableMeta={displayResults?.variable_meta}
            models={displayResults?.models || caseDetail?.models}
          />
        )}

        {(subTab === 'all' || subTab === 'metrics') && (
          <MetricsTable
            key={`metrics-${currentModId}-${displayResults?.exp_id}`}
            metrics={displayResults?.metrics || []}
            scenariosMetrics={displayResults?.scenarios_metrics}
            outputs={displayResults?.outputs}
          />
        )}

        {(subTab === 'all' || subTab === 'plots') && (
          displayResults?.plots && displayResults.plots.length > 0 ? (
            <PlotGallery key={`plots-${currentModId}-${displayResults?.exp_id}`} plots={displayResults.plots} />
          ) : (
            subTab === 'plots' && (
              <div className="glass-panel rounded-2xl p-12 text-center text-slate-500 dark:text-slate-400 font-mono text-xs">
                No plot artifacts have been generated for this module yet. Please run the simulation first.
              </div>
            )
          )
        )}
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // 1. App State
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('greenhouse');
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);

  // Active module
  const [selectedModuleId, setSelectedModuleId] = useState<string>('mod1_initial_calibration');

  // Case calibration config (calibration.yaml)
  const [caseCalibrationConfig, setCaseCalibrationConfig] = useState<ConfigInfo | null>(null);
  const [isSavingCaseConfig, setIsSavingCaseConfig] = useState<boolean>(false);

  // Active module config & results
  const [activeConfig, setActiveConfig] = useState<ConfigInfo | null>(null);
  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);
  const [activeResults, setActiveResults] = useState<ResultsData | null>(null);

  // UI state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // WebSocket execution state
  const [wsStatus, setWsStatus] = useState<WSStatus>('DISCONNECTED');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [generationHistory, setGenerationHistory] = useState<GenerationUpdate[]>([]);
  const [forceModelA, setForceModelA] = useState<boolean>(false);

  const wsRef = useRef<ExecutionWebSocket | null>(null);

  // Derive Active View from URL pathname
  const activeView: NavViewType = useMemo(() => {
    const p = location.pathname;
    if (p.includes('/info')) return 'case-info';
    if (p.includes('/case/') && p.includes('/config') && !p.includes('/exp/')) return 'case-config';
    if (p.includes('/config')) return 'exp-config';
    if (p.includes('/run')) return 'exp-run';
    if (p.includes('/results')) return 'exp-results';
    if (p.includes('/settings')) return 'settings';
    return 'case-info';
  }, [location.pathname]);

  // Derive Active Result Sub-tab from URL
  const activeResultSubTab: ResultSubTab = useMemo(() => {
    const p = location.pathname;
    if (p.includes('/results/charts')) return 'charts';
    if (p.includes('/results/metrics')) return 'metrics';
    if (p.includes('/results/plots')) return 'plots';
    return 'all';
  }, [location.pathname]);

  // Sync state with URL params
  useEffect(() => {
    const matchCase = location.pathname.match(/\/case\/([^\/]+)/);
    if (matchCase && matchCase[1] && matchCase[1] !== selectedCaseId) {
      setSelectedCaseId(matchCase[1]);
    }

    const matchExp = location.pathname.match(/\/exp\/([^\/]+)/);
    if (matchExp && matchExp[1] && matchExp[1] !== selectedModuleId) {
      setSelectedModuleId(matchExp[1]);
    }
  }, [location.pathname]);

  // 2. Initialize WebSocket
  useEffect(() => {
    const ws = new ExecutionWebSocket({
      onStatusChange: (status, message) => {
        setWsStatus(status);
        if (message) setStatusMessage(message);
      },
      onLog: (log) => {
        setLogs((prev) => [...prev.slice(-300), log]);
      },
      onGeneration: (gen) => {
        setGenerationHistory((prev) => [...prev, gen]);
      },
      onFinished: (_exitCode, _success, _message, results) => {
        if (results) {
          setActiveResults(results);
        } else {
          refreshResults();
        }
      },
      onError: (err) => {
        setErrorBanner(err);
      },
    });

    ws.connect();
    wsRef.current = ws;

    return () => {
      ws.disconnect();
    };
  }, []);

  // 3. Load Cases & Case Details
  const loadCases = useCallback(async () => {
    try {
      setIsLoading(true);
      const caseList = await fetchCases();
      setCases(caseList);

      if (caseList.length > 0) {
        const found = caseList.find((c) => c.id === selectedCaseId);
        if (!found) {
          setSelectedCaseId(caseList[0].id);
        }
      }
    } catch (err: any) {
      setErrorBanner(`Failed to load digital twin cases: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    let isMounted = true;
    async function loadDetail() {
      if (!selectedCaseId) return;
      try {
        const detail = await fetchCaseDetail(selectedCaseId);
        if (!isMounted) return;
        setCaseDetail(detail);

        // Check if selectedModuleId exists in new case
        const mods = detail.modules || detail.experiments || [];
        if (mods.length > 0) {
          const modExists = mods.some((e) => e.id === selectedModuleId);
          if (!modExists) {
            setSelectedModuleId(mods[0].id);
          }
        }
      } catch (err: any) {
        if (isMounted) setErrorBanner(`Failed to load case detail: ${err.message}`);
      }
    }

    loadDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedCaseId]);

  // 4. Fetch Case Calibration Config (calibration.yaml)
  const refreshCaseConfig = useCallback(async () => {
    if (!selectedCaseId) return;
    try {
      const cfg = await fetchConfig(selectedCaseId, 'calibration.yaml');
      setCaseCalibrationConfig(cfg);
    } catch (err) {
      setCaseCalibrationConfig(null);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    refreshCaseConfig();
  }, [refreshCaseConfig]);

  const handleSaveCaseConfig = async (yamlContent: string) => {
    if (!selectedCaseId) return;
    setIsSavingCaseConfig(true);
    try {
      await saveConfig(selectedCaseId, 'calibration.yaml', yamlContent);
      const updated = await fetchConfig(selectedCaseId, 'calibration.yaml');
      setCaseCalibrationConfig(updated);
    } catch (err: any) {
      setErrorBanner(`Failed to save case config: ${err.message}`);
    } finally {
      setIsSavingCaseConfig(false);
    }
  };

  // 5. Fetch Module Config & Results when selectedModuleId or selectedCaseId changes
  const refreshModuleData = useCallback(async () => {
    if (!selectedCaseId || !selectedModuleId || !caseDetail) return;

    const modules = caseDetail.modules || caseDetail.experiments || [];
    const mod = modules.find((e) => e.id === selectedModuleId);
    if (!mod) return;

    // Load config
    if (mod.config_file) {
      try {
        const cfg = await fetchConfig(selectedCaseId, mod.config_file);
        setActiveConfig(cfg);
      } catch (err) {
        setActiveConfig(null);
      }
    } else {
      setActiveConfig(null);
    }

    // Load results
    try {
      const res = await fetchResults(selectedCaseId, selectedModuleId);
      setActiveResults(res);
    } catch (err) {
      setActiveResults(null);
    }
  }, [selectedCaseId, selectedModuleId, caseDetail]);

  useEffect(() => {
    refreshModuleData();
  }, [refreshModuleData]);

  const refreshResults = async () => {
    if (selectedCaseId && selectedModuleId) {
      try {
        const res = await fetchResults(selectedCaseId, selectedModuleId);
        setActiveResults(res);
      } catch (err) {
        console.error('Error refreshing results:', err);
      }
    }
  };

  // Run Module / Calibration
  const handleRun = (options?: { forceModelA?: boolean; gaParams?: { pop_size: number; generations: number; mutation_rate: number } }) => {
    if (!wsRef.current || !selectedCaseId || !selectedModuleId) return;
    setErrorBanner(null);

    const modules = caseDetail?.modules || caseDetail?.experiments || [];
    const mod = modules.find((e) => e.id === selectedModuleId);
    if (mod?.is_calibration) {
      setGenerationHistory([]);
      wsRef.current.startCalibration(selectedCaseId, options?.gaParams || {
        pop_size: 8,
        generations: 5,
        mutation_rate: 0.15,
      });
    } else {
      const isForce = options?.forceModelA !== undefined ? options.forceModelA : forceModelA;
      wsRef.current.startModule(selectedCaseId, selectedModuleId, isForce);
    }
  };

  // Stop Execution
  const handleStop = async () => {
    if (wsRef.current) {
      wsRef.current.stop();
    }
    if (selectedCaseId) {
      await stopProcesses(selectedCaseId);
    }
  };

  // Save Config
  const handleSaveConfig = async (yamlContent: string) => {
    if (!selectedCaseId || !activeConfig?.config_name) return;
    setIsSavingConfig(true);
    try {
      await saveConfig(selectedCaseId, activeConfig.config_name, yamlContent);
      const updated = await fetchConfig(selectedCaseId, activeConfig.config_name);
      setActiveConfig(updated);
    } catch (err: any) {
      setErrorBanner(`Failed to save config: ${err.message}`);
    } finally {
      setIsSavingConfig(false);
    }
  };

  const isRunning = wsStatus === 'RUNNING';
  const modules = caseDetail?.modules || caseDetail?.experiments || [];
  const selectedModule = modules.find((e) => e.id === selectedModuleId);

  const handleSelectCase = (cId: string) => {
    setSelectedCaseId(cId);
  };

  return (
    <div className="flex min-h-screen w-full bg-slate-50 text-slate-900 dark:bg-[#030712] dark:text-slate-100 transition-colors duration-200 relative">
      {/* 1. SIDEBAR (Multi-level menu with React Router) */}
      <Sidebar
        cases={cases}
        selectedCaseId={selectedCaseId}
        onSelectCase={handleSelectCase}
        caseDetail={caseDetail}
        selectedModuleId={selectedModuleId}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        wsStatus={wsStatus}
      />

      {/* 2. MAIN LAYOUT (Header + Routed Content Area) */}
      <div className="flex-1 min-w-0 min-h-screen flex flex-col relative z-10">
        <div className="p-4 md:p-6 flex flex-col gap-6 max-w-[1600px] w-full mx-auto flex-1 pb-12">
          
          {/* Header */}
          <Header
            cases={cases}
            selectedCaseId={selectedCaseId}
            onSelectCase={handleSelectCase}
            selectedModule={selectedModule}
            activeView={activeView}
            activeResultSubTab={activeResultSubTab}
            wsStatus={wsStatus}
            statusMessage={statusMessage}
            onRefresh={loadCases}
            isSidebarCollapsed={isSidebarCollapsed}
            onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            isRunning={isRunning}
            onRun={() => handleRun()}
            onStop={handleStop}
          />

          {/* Global Error Banner */}
          {errorBanner && (
            <div className="flex items-center justify-between p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs font-mono shadow-sm">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-500 dark:text-rose-400 shrink-0" />
                <span>{errorBanner}</span>
              </div>
              <button
                onClick={() => setErrorBanner(null)}
                className="text-rose-600 hover:text-rose-800 dark:text-rose-400 dark:hover:text-white text-xs px-2 py-0.5 cursor-pointer font-sans"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Loading Spinner */}
          {isLoading ? (
            <div className="glass-panel rounded-2xl p-16 flex flex-col items-center justify-center gap-4 text-slate-600 dark:text-slate-400">
              <Loader2 className="w-8 h-8 text-purple-600 dark:text-purple-400 animate-spin" />
              <span className="text-sm font-medium">Discovering Digital Twin Cases...</span>
            </div>
          ) : (
            /* 3. REACT ROUTER CONTENT */
            <div className="transition-all duration-300 flex-1 flex flex-col">
              <Routes>
                {/* Default route -> redirect to selected case info */}
                <Route
                  path="/"
                  element={<Navigate to={`/case/${selectedCaseId || 'greenhouse'}/info`} replace />}
                />

                {/* Case Info Route */}
                <Route
                  path="/case/:caseId"
                  element={<Navigate to="info" replace />}
                />
                <Route
                  path="/case/:caseId/info"
                  element={
                    <div className="space-y-8">
                      <div>
                        <h2 className="text-2xl font-display font-black text-slate-900 dark:text-white tracking-tight">
                          Case Overview & Models Architecture
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {caseDetail?.type === 'physical'
                            ? 'Building architecture, geographic location, field IoT telemetry sensors, and operational Digital Twin.'
                            : 'Building geometry, geographic location, high-fidelity Model A, and digital twin Model B.'}
                        </p>
                      </div>
                      <CaseOverview caseDetail={caseDetail} />

                      {/* Global Case Configuration (calibration.yaml) */}
                      <div className="space-y-4 pt-6 border-t border-slate-200/80 dark:border-white/10">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <Sliders className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                              <h3 className="text-lg font-display font-bold text-slate-900 dark:text-white tracking-tight">
                                Global Case Configuration
                              </h3>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-300/40">
                                calibration.yaml
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                              Configure GA Calibration, physical parameter bounds, and shared simulation parameters for the case.
                            </p>
                          </div>
                        </div>

                        <ConfigEditor
                          configInfo={caseCalibrationConfig}
                          onSave={handleSaveCaseConfig}
                          isSaving={isSavingCaseConfig}
                        />
                      </div>
                    </div>
                  }
                />

                {/* Case Calibration / Config Dedicated Route */}
                <Route
                  path="/case/:caseId/config"
                  element={
                    <div className="space-y-6">
                      <div>
                        <div className="flex items-center gap-2.5">
                          <Sliders className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                          <h2 className="text-2xl font-display font-black text-slate-900 dark:text-white tracking-tight">
                            Global Case Configuration (calibration.yaml)
                          </h2>
                          <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-300/40">
                            Global Case Config
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Directly edit the YAML configuration for Genetic Algorithm, physical parameter bounds, and case-wide simulation settings.
                        </p>
                      </div>
                      <ConfigEditor
                        configInfo={caseCalibrationConfig}
                        onSave={handleSaveCaseConfig}
                        isSaving={isSavingCaseConfig}
                      />
                    </div>
                  }
                />
                <Route
                  path="/case/:caseId/calibration"
                  element={<Navigate to="config" replace />}
                />

                {/* Module Config Route */}
                <Route
                  path="/case/:caseId/exp/:expId/config"
                  element={
                    <div className="space-y-6">
                      <div>
                        <h2 className="text-2xl font-display font-black text-slate-900 dark:text-white tracking-tight">
                          Experiment Configuration (YAML)
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          Directly edit the YAML configuration for simulation parameters, calibration bounds, and boundary conditions.
                        </p>
                      </div>
                      <ConfigEditor
                        configInfo={activeConfig}
                        onSave={handleSaveConfig}
                        isSaving={isSavingConfig}
                      />
                    </div>
                  }
                />

                {/* Module Run Route */}
                <Route
                  path="/case/:caseId/exp/:expId"
                  element={<Navigate to="run" replace />}
                />
                <Route
                  path="/case/:caseId/exp/:expId/run"
                  element={
                    <SimulationRunner
                      module={selectedModule}
                      caseId={selectedCaseId}
                      isRunning={isRunning}
                      wsStatus={wsStatus}
                      statusMessage={statusMessage}
                      logs={logs}
                      onClearLogs={() => setLogs([])}
                      onRunModule={handleRun}
                      onStopModule={handleStop}
                      forceModelA={forceModelA}
                      onToggleForceModelA={setForceModelA}
                      onViewResults={() => navigate(`/case/${selectedCaseId}/exp/${selectedModuleId}/results`)}
                      hasResults={!!activeResults?.has_results}
                      generationHistory={generationHistory}
                    />
                  }
                />

                {/* Module Results Route */}
                <Route
                  path="/case/:caseId/exp/:expId/results"
                  element={
                    <ResultsView
                      selectedModule={selectedModule}
                      selectedCaseId={selectedCaseId}
                      selectedModuleId={selectedModuleId}
                      activeResults={activeResults}
                      generationHistory={generationHistory}
                      isRunning={isRunning}
                      activeSubTab="all"
                      caseDetail={caseDetail}
                    />
                  }
                />
                <Route
                  path="/case/:caseId/exp/:expId/results/:subTab"
                  element={
                    <ResultsView
                      selectedModule={selectedModule}
                      selectedCaseId={selectedCaseId}
                      selectedModuleId={selectedModuleId}
                      activeResults={activeResults}
                      generationHistory={generationHistory}
                      isRunning={isRunning}
                      caseDetail={caseDetail}
                    />
                  }
                />

                {/* System Settings Route */}
                <Route
                  path="/settings"
                  element={
                    <SettingsPanel
                      cases={cases}
                      selectedCaseId={selectedCaseId}
                      wsStatus={wsStatus}
                      statusMessage={statusMessage}
                      onRefreshCases={loadCases}
                    />
                  }
                />

                {/* Fallback route */}
                <Route
                  path="*"
                  element={<Navigate to={`/case/${selectedCaseId || 'greenhouse'}/info`} replace />}
                />
              </Routes>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default App;
