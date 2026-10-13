import React from 'react';
import { Box, CheckCircle2, FileCode, MapPin, Sparkles, XCircle, Radio, Gauge, Activity } from 'lucide-react';
import { CaseDetail } from '../types';

interface CaseOverviewProps {
  caseDetail: CaseDetail | null;
}

export const CaseOverview: React.FC<CaseOverviewProps> = ({ caseDetail }) => {
  if (!caseDetail) return null;

  const isPhysical = caseDetail.type === 'physical';
  const modelA = caseDetail.models?.model_a;
  const modelB = caseDetail.models?.model_b;
  const modelStatus = caseDetail.model_status || {};
  const telemetry = caseDetail.telemetry;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Case Description & Badges */}
      <div className="glass-panel rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span
              className={`text-[11px] font-mono font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-md border ${
                isPhysical
                  ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/20'
                  : 'bg-purple-100 dark:bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-500/20'
              }`}
            >
              {isPhysical ? '🏭 Physical Twin Case' : '🔬 Virtual Twin Case'}
            </span>
            {caseDetail.location && (
              <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 font-mono">
                <MapPin className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />
                {caseDetail.location}
              </span>
            )}
          </div>
          <h2 className="text-xl font-display font-bold text-slate-900 dark:text-white tracking-tight">
            {caseDetail.name}
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-2 leading-relaxed font-normal">
            {caseDetail.description}
          </p>
        </div>

        {caseDetail.tags && caseDetail.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-4 pt-3 border-t border-slate-100 dark:border-white/5">
            {caseDetail.tags.map((tag, idx) => (
              <span
                key={idx}
                className="text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 px-2 py-0.5 rounded-md border border-slate-200/80 dark:border-white/5 transition-colors"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Center Card: Model A (Virtual) OR Field Sensors / IoT Telemetry (Physical) */}
      {!isPhysical ? (
        <div className="glass-card rounded-2xl p-5 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-rose-500 via-pink-500 to-transparent" />
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Box className="w-5 h-5 text-rose-500 dark:text-rose-400" />
              <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                {modelA?.name || 'Model A (Virtual World)'}
              </h3>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-500/20">
              High Fidelity (GT)
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed min-h-[36px]">
            {modelA?.description || 'High-order complex geometry representing the ground truth virtual world.'}
          </p>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/5 space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-slate-400" />
                Base Model (OSM):
              </span>
              {modelStatus.model_a?.base_osm?.exists ? (
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Ready
                </span>
              ) : (
                <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold">
                  <XCircle className="w-3.5 h-3.5" /> Missing
                </span>
              )}
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-rose-500 dark:text-rose-400" />
                Extended IDF:
              </span>
              {modelStatus.model_a?.extended_idf?.exists ? (
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Ready
                </span>
              ) : (
                <span className="flex items-center gap-1 text-slate-400 dark:text-slate-500">Auto-generated</span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-card rounded-2xl p-5 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-transparent" />
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Radio className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                Physical Ground Truth (Sensors)
              </h3>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/20">
              Field Telemetry
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed min-h-[36px]">
            In-situ IoT sensors, weather station, and power meters field telemetry measurement system.
          </p>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/5 space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-emerald-500" />
                Data Source:
              </span>
              <span className="text-slate-700 dark:text-slate-300 font-semibold truncate max-w-[140px]">
                {telemetry?.data_source || 'Sensors Stream / Log'}
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <Gauge className="w-3.5 h-3.5 text-teal-500" />
                Measured Channels:
              </span>
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {telemetry?.measured_variables?.length || 'Live Sensors'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Right Card: Model B (Digital Twin) */}
      <div className="glass-card rounded-2xl p-5 relative overflow-hidden group">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-indigo-500 to-transparent" />
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Box className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
              {modelB?.name || (isPhysical ? 'Operational Digital Twin' : 'Model B (Digital Twin)')}
            </h3>
          </div>
          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-500/20">
            {isPhysical ? 'Operational Twin' : 'Calibrated Model'}
          </span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed min-h-[36px]">
          {modelB?.description ||
            (isPhysical
              ? 'Operational Digital Twin model optimized for fast predictive inference and virtual sensor estimation.'
              : 'Surrogate low-order geometry calibrated in real-time for fast parallel execution.')}
        </p>

        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/5 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-700 dark:text-slate-300">
            <span className="flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-slate-400" />
              Base Model (OSM):
            </span>
            {modelStatus.model_b?.base_osm?.exists ? (
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Ready
              </span>
            ) : (
              <span className="flex items-center gap-1 text-slate-400 dark:text-slate-500">Auto-generated</span>
            )}
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-700 dark:text-slate-300">
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
              Extended IDF:
            </span>
            {modelStatus.model_b?.extended_idf?.exists ? (
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Ready
              </span>
            ) : (
              <span className="flex items-center gap-1 text-slate-400 dark:text-slate-500">Auto-generated</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
