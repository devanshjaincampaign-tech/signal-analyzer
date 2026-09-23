import React from 'react';
import { Cpu, ShieldCheck, BarChart3, Binary, Info } from 'lucide-react';
import { ClassificationResult } from '../types/signal';

interface ModulationCardProps {
  classification: ClassificationResult | null;
}

export const ModulationCard: React.FC<ModulationCardProps> = ({ classification }) => {
  if (!classification) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-[#101522] border border-white/10 rounded-xl text-slate-400 font-mono">
        <Cpu className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
        <p className="text-xs">No Modulation Result</p>
      </div>
    );
  }

  const modName = classification.modulation || 'UNKNOWN';
  const confidencePct = Math.round((classification.confidence || 0) * 100);

  const getFullName = (mod: string) => {
    switch (mod) {
      case 'PSK': return 'BPSK (Binary Phase Shift Keying)';
      case 'FSK': return '2-FSK (Frequency Shift Keying)';
      case 'QAM': return '16-QAM (Quadrature Amplitude Modulation)';
      default: return mod;
    }
  };

  const getModBadgeColor = (mod: string) => {
    switch (mod) {
      case 'PSK': return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-[0_0_15px_rgba(0,240,255,0.25)]';
      case 'FSK': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-[0_0_15px_rgba(0,255,136,0.25)]';
      case 'QAM': return 'bg-purple-500/20 text-purple-300 border-purple-500/40 shadow-[0_0_15px_rgba(157,78,221,0.25)]';
      default: return 'bg-slate-700/30 text-slate-300 border-white/10';
    }
  };

  return (
    <div className="flex flex-col bg-[#101522]/95 border border-white/10 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-mono font-bold tracking-wider text-slate-200 uppercase">
            Modulation Classification
          </h3>
        </div>
        <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Rule-Based Classifier</span>
        </div>
      </div>

      {/* Main Modulation Banner */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-lg bg-slate-900/90 border border-white/5 mb-4">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400">Detected Modulation</span>
          <div className="flex items-center gap-3 mt-1">
            <span className={`px-3 py-1 text-lg font-mono font-bold rounded-md border ${getModBadgeColor(modName)}`}>
              {modName}
            </span>
            <span className="text-xs font-mono text-slate-300">
              {getFullName(modName)}
            </span>
          </div>
        </div>

        {/* Confidence Percentage Badge */}
        <div className="flex flex-col items-center sm:items-end">
          <span className="text-[10px] font-mono text-slate-400">Confidence</span>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-emerald-400">{confidencePct}%</span>
          </div>
        </div>
      </div>

      {/* Candidate Probability Bars */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
          <span className="flex items-center gap-1.5">
            <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
            Candidate Probabilities
          </span>
        </div>

        {classification.candidates && classification.candidates.map((cand) => {
          const pct = Math.round(cand.score * 100);
          const isTop = cand.label === modName;
          return (
            <div key={cand.label} className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono">
                <span className={isTop ? 'text-white font-bold' : 'text-slate-400'}>
                  {cand.label}
                </span>
                <span className={isTop ? 'text-cyan-300 font-bold' : 'text-slate-500'}>
                  {pct}%
                </span>
              </div>
              <div className="w-full bg-slate-800/80 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    isTop ? 'bg-gradient-to-r from-cyan-500 to-emerald-400' : 'bg-slate-600'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Extracted Higher-Order Physical Features */}
      {classification.features_used && classification.features_used.applicable && (
        <div className="pt-3 border-t border-white/5">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-2 block">
            Extracted Statistical Cumulants & Variance
          </span>
          <div className="grid grid-cols-3 gap-2 text-center font-mono">
            <div className="p-2 rounded bg-slate-900/60 border border-white/5">
              <div className="text-[10px] text-slate-500">Envelope Var</div>
              <div className="text-xs font-bold text-slate-200 mt-0.5">
                {classification.features_used.envelope_variance ?? 'N/A'}
              </div>
            </div>
            <div className="p-2 rounded bg-slate-900/60 border border-white/5">
              <div className="text-[10px] text-slate-500">Inst Freq Var</div>
              <div className="text-xs font-bold text-slate-200 mt-0.5">
                {classification.features_used.inst_freq_variance ?? 'N/A'}
              </div>
            </div>
            <div className="p-2 rounded bg-slate-900/60 border border-white/5">
              <div className="text-[10px] text-slate-500">$C_{42}$ Cumulant</div>
              <div className="text-xs font-bold text-slate-200 mt-0.5">
                {classification.features_used.c42_cumulant ?? 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
