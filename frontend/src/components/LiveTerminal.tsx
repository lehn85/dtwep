import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Trash2, Copy, Check, ArrowDownCircle } from 'lucide-react';
import { LogMessage } from '../types';

interface LiveTerminalProps {
  logs: LogMessage[];
  onClear: () => void;
  isRunning: boolean;
}

export const LiveTerminal: React.FC<LiveTerminalProps> = ({
  logs,
  onClear,
  isRunning,
}) => {
  const [filter, setFilter] = useState<'all' | 'stdout' | 'stderr' | 'system'>('all');
  const [copied, setCopied] = useState<boolean>(false);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((l) => {
    if (filter === 'all') return true;
    return l.stream === filter;
  });

  const handleCopy = () => {
    const text = filteredLogs.map((l) => `[${l.timestamp}] ${l.text}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatLogLine = (text: string, stream: string) => {
    if (stream === 'stderr' || text.includes('[ERROR]') || text.includes('[FAILED]')) {
      return <span className="text-rose-600 dark:text-rose-400 font-medium">{text}</span>;
    }
    if (text.includes('[SUCCESS]') || text.includes('[PASSED]') || text.includes('completed')) {
      return <span className="text-emerald-700 dark:text-emerald-400 font-semibold">{text}</span>;
    }
    if (text.includes('[RUNNING]') || text.includes('[GA Gen]') || text.includes('Starting')) {
      return <span className="text-cyan-700 dark:text-cyan-400 font-medium">{text}</span>;
    }
    if (text.includes('[INFO]') || text.includes('[STATUS]') || text.includes('[SYSTEM]')) {
      return <span className="text-purple-700 dark:text-purple-300 font-medium">{text}</span>;
    }
    return <span className="text-slate-800 dark:text-slate-300">{text}</span>;
  };

  const getStreamBadgeStyle = (stream: string) => {
    switch (stream.toLowerCase()) {
      case 'system':
        return 'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800/50';
      case 'stderr':
        return 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/50';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:border-slate-800';
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-4 flex flex-col gap-3 shadow-xl">
      {/* Terminal Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-100 dark:border-white/10 text-xs">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span className="font-mono font-bold text-slate-900 dark:text-slate-100 tracking-wide">
            REAL-TIME EXECUTION LOGS & DIAGNOSTICS
          </span>
          {isRunning && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono font-semibold text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-500/15 px-2 py-0.5 rounded-full border border-cyan-200 dark:border-cyan-500/30 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 dark:bg-cyan-400" />
              STREAMING
            </span>
          )}
        </div>

        {/* Filter & Actions */}
        <div className="flex items-center gap-2">
          {/* Stream Filter */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-900 rounded-lg p-0.5 border border-slate-200/80 dark:border-slate-800 text-[11px] font-mono shadow-sm">
            {(['all', 'stdout', 'stderr', 'system'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded-md uppercase transition-colors cursor-pointer ${
                  filter === f
                    ? 'bg-purple-600 text-white font-semibold shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Auto scroll toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            title={autoScroll ? 'Disable Auto-scroll' : 'Enable Auto-scroll'}
            className={`p-1.5 rounded-lg border transition-colors cursor-pointer shadow-sm ${
              autoScroll
                ? 'bg-purple-100 border-purple-300 text-purple-700 dark:bg-purple-500/20 dark:border-purple-500/30 dark:text-purple-300'
                : 'bg-slate-100 border-slate-200 text-slate-600 hover:text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            <ArrowDownCircle className="w-3.5 h-3.5" />
          </button>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            title="Copy logs"
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 border border-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 dark:text-slate-400 dark:hover:text-white dark:border-slate-800 transition-colors shadow-sm cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          {/* Clear Button */}
          <button
            onClick={onClear}
            title="Clear terminal"
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-rose-600 border border-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 dark:text-slate-400 dark:hover:text-rose-400 dark:border-slate-800 transition-colors shadow-sm cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Log Area */}
      <div
        ref={logContainerRef}
        className="font-mono text-xs max-h-56 min-h-36 overflow-y-auto space-y-1 pr-2 select-text"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-slate-400 dark:text-slate-500 italic py-4 text-center">
            Terminal standby. Ready for experiment execution...
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-2 leading-relaxed hover:bg-slate-100/80 dark:hover:bg-slate-900/60 px-1.5 py-0.5 rounded transition-colors"
            >
              <span className="text-slate-400 dark:text-slate-500 select-none text-[10px] pt-0.5 shrink-0">
                {log.timestamp}
              </span>
              <span className={`text-[10px] font-semibold uppercase px-1 rounded border shrink-0 ${getStreamBadgeStyle(log.stream)}`}>
                {log.stream}
              </span>
              <div className="flex-1 break-all">
                {formatLogLine(log.text, log.stream)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
