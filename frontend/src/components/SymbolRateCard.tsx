import React from 'react';
import { Timer, Gauge, Zap, CheckCircle2 } from 'lucide-react';
import { SymbolRateResult } from '../types/signal';

interface SymbolRateCardProps {
  symbolRate: SymbolRateResult | null;
  sampleRate: number;
}

export const SymbolRateCard: React.FC<SymbolRateCardProps> = ({
  symbolRate,
  sampleRate,
}) => {
  if (!symbolRate) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-[#101522] border border-white/10 rounded-xl text-slate-400 font-mono">
        <Timer className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
        <p className="text-xs">No Symbol Rate Data</p>
      </div>
    );
  }

  const baud = symbolRate.symbol_rate_baud ? Math.round(symbolRate.symbol_rate_baud) : null;
  const sps = symbolRate.samples_per_symbol;
  const confidencePct = Math.round((symbolRate.confidence || 0) * 100);

  return (
    <div className="flex flex-col bg-[#101522]/95 border border-white/10 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Timer className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-mono font-bold tracking-wider text-slate-200 uppercase">
            Symbol Timing & Baud Rate
          </h3>
        </div>
        <div className="flex items-center gap-1 text-[11px] font-mono text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Locked</span>
        </div>
      </div>

      {/* Main Baud Rate Metric */}
      <div className="p-4 rounded-lg bg-slate-900/90 border border-white/5 mb-4">
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400">Estimated Symbol Rate</span>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-3xl font-mono font-bold text-cyan-300">
            {baud !== null ? baud.toLocaleString() : 'Undetermined'}
          </span>
          <span className="text-xs font-mono text-slate-400 uppercase font-semibold">Baud (sym/s)</span>
        </div>
      </div>

      {/* Timing Details Grid */}
      <div className="grid grid-cols-2 gap-3 font-mono">
        <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">
            <Gauge className="w-3.5 h-3.5 text-cyan-400" />
            <span>Samples / Symbol ($T_{'{sym}'}$)</span>
          </div>
          <div className="text-lg font-bold text-white">
            {sps !== null ? `${sps} sps` : 'N/A'}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span>Timing Confidence</span>
          </div>
          <div className="text-lg font-bold text-emerald-400">
            {confidencePct}%
          </div>
        </div>
      </div>

      {/* Algorithm Method Tag */}
      <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span>Method:</span>
        <span className="text-slate-300 font-semibold truncate max-w-[200px]" title={symbolRate.method || 'Cyclostationary'}>
          {symbolRate.method || 'Cyclostationary Spectrum Peak'}
        </span>
      </div>
    </div>
  );
};
