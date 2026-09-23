import React from 'react';
import { 
  CheckCircle2, 
  RotateCw, 
  AlertCircle, 
  FileAudio, 
  Layers, 
  Activity, 
  Timer, 
  Cpu, 
  Binary, 
  Grid3X3 
} from 'lucide-react';
import { AnalysisResponse, Job } from '../types/signal';

interface PipelineStepperProps {
  job: Job | null;
  analysis: AnalysisResponse | null;
  isAnalyzing: boolean;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  job,
  analysis,
  isAnalyzing,
}) => {
  const stages = [
    {
      id: 'ingestion',
      label: 'Ingestion & Sniffing',
      icon: FileAudio,
      status: job ? (job.status === 'error' ? 'error' : 'completed') : 'idle',
      detail: job ? `${job.file_type.toUpperCase()} • ${job.metadata?.format || 'Captured'}` : 'Waiting for capture',
    },
    {
      id: 'loader',
      label: 'Signal Loader & Framing',
      icon: Layers,
      status: analysis ? 'completed' : isAnalyzing ? 'active' : 'idle',
      detail: analysis ? `${(analysis.features.sample_rate_used / 1e6).toFixed(2)} MS/s` : 'Framing & Normalization',
    },
    {
      id: 'features',
      label: 'Welch PSD & Spectrogram',
      icon: Activity,
      status: analysis?.features ? 'completed' : isAnalyzing ? 'active' : 'idle',
      detail: analysis?.features ? `Fc: ${(analysis.features.center_frequency_hz / 1e3).toFixed(1)} kHz • BW: ${(analysis.features.bandwidth_hz / 1e3).toFixed(1)} kHz` : 'FFT & Power Spectrum',
    },
    {
      id: 'symbol_rate',
      label: 'Symbol Timing / Baud Rate',
      icon: Timer,
      status: analysis?.symbol_rate ? 'completed' : isAnalyzing ? 'active' : 'idle',
      detail: analysis?.symbol_rate?.symbol_rate_baud ? `${Math.round(analysis.symbol_rate.symbol_rate_baud).toLocaleString()} Baud (${analysis.symbol_rate.samples_per_symbol} sps)` : 'Cyclostationary Search',
    },
    {
      id: 'classification',
      label: 'Modulation Classifier',
      icon: Cpu,
      status: analysis?.classification ? 'completed' : isAnalyzing ? 'active' : 'idle',
      detail: analysis?.classification?.modulation ? `${analysis.classification.modulation} (${Math.round((analysis.classification.confidence || 0) * 100)}% Conf)` : 'Higher-Order Cumulants',
    },
    {
      id: 'demod',
      label: 'Demodulation Core',
      icon: Binary,
      status: analysis?.demod ? (analysis.demod.success ? 'completed' : 'warning') : isAnalyzing ? 'active' : 'idle',
      detail: analysis?.demod?.success ? (analysis.demod.num_bits ? `${analysis.demod.num_bits} bits decoded` : 'Symbols decoded') : 'Bit Recovery',
    },
    {
      id: 'interleaving',
      label: 'Interleaving Detection',
      icon: Grid3X3,
      status: analysis?.interleaving ? (analysis.interleaving.success ? 'completed' : 'idle') : isAnalyzing ? 'active' : 'idle',
      detail: analysis?.interleaving?.success ? `Stride: ${analysis.interleaving.stride} • Depth: ${analysis.interleaving.depth}` : 'Matrix Autocorrelation',
    },
  ];

  return (
    <div className="w-full bg-[#101522]/90 border border-white/10 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase">
            DSP Analysis Pipeline Execution Flow
          </h3>
        </div>
        <div className="text-[11px] font-mono text-slate-400">
          {isAnalyzing ? (
            <span className="text-cyan-400 flex items-center gap-1.5 font-semibold">
              <RotateCw className="w-3.5 h-3.5 animate-spin" />
              RUNNING DSP WORKFLOW...
            </span>
          ) : analysis ? (
            <span className="text-emerald-400 flex items-center gap-1 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              PIPELINE EXECUTED (7/7 Stages Complete)
            </span>
          ) : (
            <span className="text-slate-500">READY FOR ANALYSIS</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
        {stages.map((st, idx) => {
          const Icon = st.icon;
          return (
            <div
              key={st.id}
              className={`relative flex flex-col justify-between p-2.5 rounded-lg border text-left transition-all ${
                st.status === 'completed'
                  ? 'bg-slate-900/90 border-cyan-500/30 text-slate-100 shadow-[0_0_12px_rgba(0,240,255,0.08)]'
                  : st.status === 'active'
                  ? 'bg-cyan-950/40 border-cyan-400 text-cyan-200 animate-pulse'
                  : st.status === 'warning'
                  ? 'bg-amber-950/30 border-amber-500/40 text-amber-200'
                  : st.status === 'error'
                  ? 'bg-rose-950/30 border-rose-500/40 text-rose-200'
                  : 'bg-slate-900/40 border-white/5 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono font-bold text-slate-400">
                  0{idx + 1}
                </span>
                {st.status === 'completed' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                ) : st.status === 'active' ? (
                  <RotateCw className="w-3.5 h-3.5 text-cyan-300 animate-spin" />
                ) : st.status === 'error' ? (
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                ) : (
                  <Icon className="w-3.5 h-3.5 text-slate-600" />
                )}
              </div>

              <div>
                <p className="text-xs font-semibold leading-tight mb-1 truncate text-slate-200">
                  {st.label}
                </p>
                <p className="text-[10px] font-mono text-slate-400 truncate" title={st.detail}>
                  {st.detail}
                </p>
              </div>

              {/* Progress bar connector */}
              <div className="mt-2 w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    st.status === 'completed'
                      ? 'bg-cyan-400 w-full'
                      : st.status === 'active'
                      ? 'bg-cyan-400 w-2/3 animate-pulse'
                      : 'w-0'
                  }`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
