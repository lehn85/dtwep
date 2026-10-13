import React, { useState } from 'react';
import { Image as ImageIcon, Maximize2, Download, X } from 'lucide-react';
import { PlotItem } from '../types';

interface PlotGalleryProps {
  plots: PlotItem[];
}

export const PlotGallery: React.FC<PlotGalleryProps> = ({ plots }) => {
  const [selectedPlot, setSelectedPlot] = useState<PlotItem | null>(null);

  if (!plots || plots.length === 0) {
    return null;
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="glass-panel rounded-2xl p-5 flex-1 flex flex-col gap-4 shadow-xl min-h-[480px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/5">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
            High-Resolution Plot Artifacts Gallery ({plots.length})
          </h3>
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
          Matplotlib Publication-Ready Outputs
        </span>
      </div>

      {/* Grid of Plots */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {plots.map((plot) => (
          <div
            key={plot.name}
            className="glass-card rounded-xl overflow-hidden border border-slate-200/80 dark:border-white/5 hover:border-purple-400 dark:hover:border-purple-500/40 shadow-sm hover:shadow-md transition-all duration-300 group flex flex-col justify-between"
          >
            <div
              onClick={() => setSelectedPlot(plot)}
              className="relative aspect-video bg-slate-100 dark:bg-slate-950/80 cursor-pointer overflow-hidden flex items-center justify-center"
            >
              <img
                src={plot.url}
                alt={plot.title}
                className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-slate-950/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <span className="p-2 rounded-xl bg-purple-600/90 text-white backdrop-blur shadow-lg">
                  <Maximize2 className="w-4 h-4" />
                </span>
              </div>
            </div>

            <div className="p-3 bg-slate-50/90 dark:bg-slate-900/60 flex items-center justify-between border-t border-slate-100 dark:border-white/5">
              <div>
                <h4 className="text-xs font-semibold text-slate-900 dark:text-white truncate max-w-[200px]" title={plot.title}>
                  {plot.title}
                </h4>
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                  {formatFileSize(plot.size_bytes)}
                </span>
              </div>

              <a
                href={plot.url}
                download={plot.name}
                title="Download image"
                className="p-1.5 rounded-lg bg-white dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white border border-slate-200/80 dark:border-white/5 transition-colors shadow-sm"
              >
                <Download className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Fullscreen Lightbox Modal */}
      {selectedPlot && (
        <div
          onClick={() => setSelectedPlot(null)}
          className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-5xl w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-2xl overflow-hidden shadow-2xl p-4 flex flex-col gap-3"
          >
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/10 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white font-display">
                  {selectedPlot.title}
                </h3>
                <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  {selectedPlot.name} &bull; {formatFileSize(selectedPlot.size_bytes)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={selectedPlot.url}
                  download={selectedPlot.name}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </a>
                <button
                  onClick={() => setSelectedPlot(null)}
                  className="p-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-400 dark:hover:text-white transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="max-h-[80vh] flex items-center justify-center overflow-auto p-2 bg-slate-50 dark:bg-slate-950 rounded-xl">
              <img
                src={selectedPlot.url}
                alt={selectedPlot.title}
                className="max-h-[75vh] w-auto object-contain rounded-lg shadow-lg"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
