import React from 'react';
import { 
  Radio, 
  Upload, 
  Sparkles, 
  History, 
  Activity, 
  Server, 
  CheckCircle2, 
  AlertCircle,
  Play,
  RotateCw
} from 'lucide-react';
import { Job } from '../types/signal';

interface HeaderProps {
  backendConnected: boolean;
  activeJob: Job | null;
  onOpenUpload: () => void;
  onOpenGenerator: () => void;
  onOpenHistory: () => void;
  onLoadPreset: (preset: 'BPSK' | 'FSK' | '16-QAM') => void;
  onRunAnalysis: () => void;
  isAnalyzing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  backendConnected,
  activeJob,
  onOpenUpload,
  onOpenGenerator,
  onOpenHistory,
  onLoadPreset,
  onRunAnalysis,
  isAnalyzing,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-[#0c101c]/90 backdrop-blur-md border-b border-white/10 px-4 lg:px-8 py-3 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & Identity */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <Radio className="w-5 h-5 animate-pulse" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-wider text-white font-mono uppercase">
                SIGNAL<span className="text-cyan-400">ANALYZER</span>
              </span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono tracking-widest bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 rounded">
                DSP v3.0
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
              <span>RF Ingestion</span>
              <span className="text-slate-600">•</span>
              <span>Modulation Classification</span>
              <span className="text-slate-600">•</span>
              <span>Demodulation</span>
            </p>
          </div>
        </div>

        {/* Center / Presets & Active Job Quick Badge */}
        <div className="flex items-center flex-wrap gap-2 text-xs">
          {activeJob ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/80 border border-cyan-500/20 text-slate-300 font-mono">
              <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span className="text-slate-400">Capture:</span>
              <span className="text-white font-semibold truncate max-w-[160px]" title={activeJob.filename}>
                {activeJob.filename}
              </span>
              <span className={`px-1.5 py-0.2 text-[10px] rounded uppercase font-bold ${
                activeJob.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                activeJob.status === 'validated' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' :
                activeJob.status === 'error' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}>
                {activeJob.status}
              </span>
            </div>
          ) : null}

          {/* Quick Presets Menu */}
          <div className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-lg border border-white/5">
            <span className="text-[11px] font-mono text-slate-400 px-2">Presets:</span>
            <button
              onClick={() => onLoadPreset('BPSK')}
              className="px-2.5 py-1 text-xs font-mono font-medium rounded hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-300 border border-transparent hover:border-cyan-500/30 transition-colors"
            >
              BPSK
            </button>
            <button
              onClick={() => onLoadPreset('FSK')}
              className="px-2.5 py-1 text-xs font-mono font-medium rounded hover:bg-emerald-500/20 hover:text-emerald-300 text-slate-300 border border-transparent hover:border-emerald-500/30 transition-colors"
            >
              2-FSK
            </button>
            <button
              onClick={() => onLoadPreset('16-QAM')}
              className="px-2.5 py-1 text-xs font-mono font-medium rounded hover:bg-purple-500/20 hover:text-purple-300 text-slate-300 border border-transparent hover:border-purple-500/30 transition-colors"
            >
              16-QAM
            </button>
          </div>
        </div>

        {/* Action Controls & Backend Status */}
        <div className="flex items-center gap-2.5">
          {/* Analyze CTA button */}
          {activeJob && activeJob.status === 'validated' && (
            <button
              onClick={onRunAnalysis}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-[0_0_15px_rgba(0,240,255,0.4)] disabled:opacity-50 transition-all"
            >
              {isAnalyzing ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing DSP...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-black" />
                  <span>Run Analysis</span>
                </>
              )}
            </button>
          )}

          {/* Synthetic Studio */}
          <button
            onClick={onOpenGenerator}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800/90 hover:bg-slate-700 text-slate-200 border border-white/10 hover:border-cyan-500/30 transition-all"
            title="Open Synthetic Signal Generator"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">Signal Lab</span>
          </button>

          {/* Upload Button */}
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800/90 hover:bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 hover:border-cyan-400 transition-all"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload IQ/WAV</span>
          </button>

          {/* History */}
          <button
            onClick={onOpenHistory}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg bg-slate-800/60 hover:bg-slate-700/80 border border-white/5 transition-all"
            title="View Capture History"
          >
            <History className="w-4 h-4" />
          </button>

          {/* Backend Status Indicator */}
          <div 
            className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-900/90 border border-white/5 text-[11px] font-mono"
            title={backendConnected ? "Connected to FastAPI Backend (port 8000)" : "Backend offline or unreachable (Demo Mode Active)"}
          >
            <Server className="w-3 h-3 text-slate-400" />
            {backendConnected ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                API LIVE
              </span>
            ) : (
              <span className="flex items-center gap-1 text-amber-400">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                DEMO MODE
              </span>
            )}
          </div>
        </div>

      </div>
    </header>
  );
};
