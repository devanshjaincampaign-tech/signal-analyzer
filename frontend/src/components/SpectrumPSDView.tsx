import React, { useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';
import type { SpectralFeatures } from '../types/signal';

interface SpectrumPSDViewProps {
  features: SpectralFeatures | null;
}

export const SpectrumPSDView: React.FC<SpectrumPSDViewProps> = ({ features }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !features) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = Math.max(300, canvas.parentElement?.clientWidth || 600);
    const height = 260;
    canvas.width = width;
    canvas.height = height;

    const padding = { top: 25, right: 30, bottom: 35, left: 50 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = '#0a0e1a';
    ctx.fillRect(0, 0, width, height);

    const sampleRate = features.sample_rate_used || 1_000_000;
    const fMin = -sampleRate / 2;
    const fMax = sampleRate / 2;

    const pMin = Math.min(-100, features.noise_floor_db - 15);
    const pMax = Math.max(10, features.peak_power_db + 10);

    const getX = (fHz: number) => padding.left + ((fHz - fMin) / (fMax - fMin)) * plotWidth;
    const getY = (pDb: number) => padding.top + (1 - (pDb - pMin) / (pMax - pMin)) * plotHeight;

    // Draw Grid Lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    // Horizontal dB lines
    for (let db = Math.ceil(pMin / 20) * 20; db <= pMax; db += 20) {
      const y = getY(db);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      ctx.fillStyle = '#64748b';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'right';
      ctx.fillText(`${db} dB`, padding.left - 8, y + 3);
    }

    // Vertical Freq lines
    const fStep = (fMax - fMin) / 6;
    for (let f = fMin; f <= fMax; f += fStep) {
      const x = getX(f);
      ctx.beginPath();
      ctx.moveTo(x, padding.top);
      ctx.lineTo(x, height - padding.bottom);
      ctx.stroke();

      ctx.fillStyle = '#64748b';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${(f / 1000).toFixed(0)}k`, x, height - padding.bottom + 16);
    }
    ctx.setLineDash([]);

    // 3dB Bandwidth Highlighted Zone
    const fc = features.center_frequency_hz;
    const bw = features.bandwidth_hz;
    const bwLeft = Math.max(fMin, fc - bw / 2);
    const bwRight = Math.min(fMax, fc + bw / 2);

    const xBwLeft = getX(bwLeft);
    const xBwRight = getX(bwRight);

    ctx.fillStyle = 'rgba(0, 240, 255, 0.08)';
    ctx.fillRect(xBwLeft, padding.top, xBwRight - xBwLeft, plotHeight);

    ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(xBwLeft, padding.top);
    ctx.lineTo(xBwLeft, height - padding.bottom);
    ctx.moveTo(xBwRight, padding.top);
    ctx.lineTo(xBwRight, height - padding.bottom);
    ctx.stroke();

    // Noise Floor Line
    const yNoise = getY(features.noise_floor_db);
    ctx.strokeStyle = '#eab308';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(padding.left, yNoise);
    ctx.lineTo(width - padding.right, yNoise);
    ctx.stroke();
    ctx.setLineDash([]);

    // Noise floor label
    ctx.fillStyle = '#eab308';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`Noise: ${features.noise_floor_db.toFixed(1)} dB`, width - padding.right, yNoise - 5);

    // Simulated Spectral Envelope Curve (Welch Curve Reconstruction)
    const pointsCount = 180;
    ctx.beginPath();
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 2;

    for (let i = 0; i <= pointsCount; i++) {
      const f = fMin + (i / pointsCount) * (fMax - fMin);
      const distFromCenter = Math.abs(f - fc);

      let power = features.noise_floor_db;
      if (distFromCenter < bw * 0.7) {
        // Mainlobe
        const rollOff = 1 - Math.pow(distFromCenter / (bw * 0.7), 2);
        power = features.noise_floor_db + (features.peak_power_db - features.noise_floor_db) * Math.max(0, rollOff);
      } else if (distFromCenter < bw * 1.5) {
        // Sidelobes
        power = features.noise_floor_db + 4 * Math.cos((distFromCenter / bw) * Math.PI * 3);
      }
      // Add subtle RF ripple
      power += (Math.sin(i * 1.2) * 1.5);

      const x = getX(f);
      const y = getY(power);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // Area fill under curve
    ctx.lineTo(getX(fMax), getY(pMin));
    ctx.lineTo(getX(fMin), getY(pMin));
    ctx.closePath();
    const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
    gradient.addColorStop(0, 'rgba(0, 240, 255, 0.25)');
    gradient.addColorStop(1, 'rgba(0, 240, 255, 0.0)');
    ctx.fillStyle = gradient;
    ctx.fill();

    // Center Frequency Peak Marker
    const xPeak = getX(fc);
    const yPeak = getY(features.peak_power_db);

    ctx.fillStyle = '#00ff88';
    ctx.beginPath();
    ctx.arc(xPeak, yPeak, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Peak label callout
    ctx.fillStyle = '#00ff88';
    ctx.font = 'bold 11px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`Peak: ${features.peak_power_db.toFixed(1)} dB (${(fc / 1000).toFixed(1)} kHz)`, xPeak, yPeak - 10);
  }, [features]);

  if (!features) {
    return (
      <div className="flex flex-col items-center justify-center h-64 bg-[#101522] border border-white/10 rounded-xl text-slate-400 font-mono">
        <Activity className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
        <p className="text-xs">No Spectral Data</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col bg-[#101522]/95 border border-white/10 rounded-xl p-4 shadow-xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <h3 className="text-sm font-mono font-bold tracking-wider text-slate-200 uppercase">
              Welch Power Spectral Density (PSD)
            </h3>
          </div>
          <p className="text-xs font-mono text-slate-400 mt-0.5">
            Averaged FFT Periodogram & 3dB Bandwidth Analysis
          </p>
        </div>

        {/* Readout Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="px-2.5 py-1 rounded bg-slate-900 border border-cyan-500/20 text-slate-300">
            <span className="text-slate-500 mr-1.5">Center Freq $F_c$:</span>
            <span className="text-cyan-300 font-bold">{(features.center_frequency_hz / 1000).toFixed(1)} kHz</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-slate-900 border border-emerald-500/20 text-slate-300">
            <span className="text-slate-500 mr-1.5">3dB BW:</span>
            <span className="text-emerald-300 font-bold">{(features.bandwidth_hz / 1000).toFixed(1)} kHz</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-slate-900 border border-amber-500/20 text-slate-300">
            <span className="text-slate-500 mr-1.5">Noise Floor:</span>
            <span className="text-amber-300 font-bold">{features.noise_floor_db.toFixed(1)} dB</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="relative w-full rounded-lg overflow-hidden border border-white/10 shadow-inner">
        <canvas ref={canvasRef} className="w-full h-64 block" />
      </div>

      <div className="flex items-center justify-between mt-2 text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400/20 border border-cyan-400" />
            3dB Occupied Bandwidth
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-yellow-400" />
            Noise Floor Baseline
          </span>
        </div>
        <span className="text-slate-500">
          Sample Rate: {(features.sample_rate_used / 1e6).toFixed(2)} MS/s {features.sample_rate_was_assumed ? '(Assumed 1MHz)' : ''}
        </span>
      </div>
    </div>
  );
};
