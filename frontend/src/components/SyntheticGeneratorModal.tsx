import React, { useState } from 'react';
import { 
  Sparkles, 
  X, 
  Sliders, 
  Play, 
  Radio, 
  Activity, 
  Layers, 
  Cpu 
} from 'lucide-react';
import { generateSyntheticDemoSignal } from '../services/api';
import { AnalysisResponse, Job } from '../types/signal';

interface SyntheticGeneratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadSyntheticSignal: (job: Job, analysis: AnalysisResponse, samples: { i: number[]; q: number[] }) => void;
}

export const SyntheticGeneratorModal: React.FC<SyntheticGeneratorModalProps> = ({
  isOpen,
  onClose,
  onLoadSyntheticSignal,
}) => {
  const [modType, setModType] = useState<'BPSK' | 'FSK' | '16-QAM'>('BPSK');
  const [snrDb, setSnrDb] = useState<number>(25);
  const [sampleRate, setSampleRate] = useState<number>(1_000_000);
  const [sps, setSps] = useState<number>(16);
  const [numSymbols, setNumSymbols] = useState<number>(256);

  if (!isOpen) return null;

  const handleGenerate = () => {
    const result = generateSyntheticDemoSignal(modType, {
      snrDb,
      sampleRate,
      samplesPerSymbol: sps,
      numSymbols,
    });

    onLoadSyntheticSignal(result.job, result.analysis, result.samples);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg bg-[#101522] border border-amber-500/30 rounded-2xl p-6 shadow-[0_0_50px_rgba(0,0,0,0.8)]">
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-white rounded-lg bg-slate-900 border border-white/5"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-mono font-bold text-white uppercase tracking-wider">
              Synthetic RF Signal Studio
            </h2>
            <p className="text-xs font-mono text-slate-400">
              Synthesize IQ captures with parametric AWGN noise & custom symbol timing
            </p>
          </div>
        </div>

        {/* Modulation Scheme Selection */}
        <div className="mb-4">
          <label className="text-xs font-mono uppercase tracking-wider text-slate-400 block mb-2">
            Modulation Scheme
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['BPSK', 'FSK', '16-QAM'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setModType(m)}
                className={`py-2.5 px-3 rounded-lg border text-xs font-mono font-bold transition-all ${
                  modType === m
                    ? 'bg-amber-500/20 border-amber-500/60 text-amber-300 shadow-[0_0_15px_rgba(255,170,0,0.2)]'
                    : 'bg-slate-900 border-white/5 text-slate-400 hover:text-white'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* SNR Slider */}
        <div className="mb-4 p-3.5 rounded-lg bg-slate-900/60 border border-white/5">
          <div className="flex justify-between items-center text-xs font-mono mb-2">
            <span className="text-slate-300 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-amber-400" />
              Signal-to-Noise Ratio (SNR)
            </span>
            <span className="text-amber-300 font-bold">{snrDb} dB</span>
          </div>
          <input
            type="range"
            min="0"
            max="40"
            step="1"
            value={snrDb}
            onChange={(e) => setSnrDb(Number(e.target.value))}
            className="w-full accent-amber-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
            <span>0 dB (High Noise)</span>
            <span>20 dB</span>
            <span>40 dB (Clean RF)</span>
          </div>
        </div>

        {/* Parameters Grid */}
        <div className="grid grid-cols-2 gap-3 mb-5 font-mono text-xs">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
            <label className="text-slate-400 block mb-1 text-[11px]">Sample Rate ($F_s$)</label>
            <select
              value={sampleRate}
              onChange={(e) => setSampleRate(Number(e.target.value))}
              className="w-full bg-slate-900 border border-white/10 rounded px-2 py-1 text-slate-200 focus:outline-none"
            >
              <option value="500000">500 kHz</option>
              <option value="1000000">1.0 MHz</option>
              <option value="2000000">2.0 MHz</option>
            </select>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
            <label className="text-slate-400 block mb-1 text-[11px]">Samples / Symbol ($T_{'{sym}'}$)</label>
            <select
              value={sps}
              onChange={(e) => setSps(Number(e.target.value))}
              className="w-full bg-slate-900 border border-white/10 rounded px-2 py-1 text-slate-200 focus:outline-none"
            >
              <option value="8">8 sps (High Baud)</option>
              <option value="16">16 sps (Standard)</option>
              <option value="32">32 sps (Low Baud)</option>
            </select>
          </div>
        </div>

        {/* Summary Info */}
        <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/20 text-[11px] font-mono text-amber-200 mb-6">
          <div className="flex justify-between mb-1">
            <span className="text-amber-400/80">Resulting Baud Rate:</span>
            <span className="font-bold">{(sampleRate / sps).toLocaleString()} Baud</span>
          </div>
          <div className="flex justify-between">
            <span className="text-amber-400/80">Total Ingested Samples:</span>
            <span className="font-bold">{(numSymbols * sps).toLocaleString()} Samples</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleGenerate}
            className="flex items-center gap-2 px-5 py-2 text-xs font-mono font-bold rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black shadow-[0_0_20px_rgba(255,170,0,0.3)] transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate & Analyze</span>
          </button>
        </div>
      </div>
    </div>
  );
};
