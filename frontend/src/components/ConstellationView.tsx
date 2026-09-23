import React, { useEffect, useRef, useState } from 'react';
import { Target, RefreshCw, ZoomIn, ZoomOut, Compass } from 'lucide-react';
import { DemodResult, ClassificationResult } from '../types/signal';

interface ConstellationViewProps {
  demod: DemodResult | null;
  classification: ClassificationResult | null;
  samplePoints?: { i: number[]; q: number[] };
}

export const ConstellationView: React.FC<ConstellationViewProps> = ({
  demod,
  classification,
  samplePoints,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState<number>(1.2);
  const [persistence, setPersistence] = useState<boolean>(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const size = Math.min(canvas.parentElement?.clientWidth || 320, 320);
    canvas.width = size;
    canvas.height = size;

    const center = size / 2;
    const scale = (size / 2 - 30) * zoom;

    // Clear
    ctx.fillStyle = '#0a0e1a';
    ctx.fillRect(0, 0, size, size);

    // Radar Concentric Circles
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.07)';
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75, 1.0].forEach((r) => {
      ctx.beginPath();
      ctx.arc(center, center, r * scale, 0, 2 * Math.PI);
      ctx.stroke();
    });

    // Crosshair Axes
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.25)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(15, center);
    ctx.lineTo(size - 15, center);
    ctx.moveTo(center, 15);
    ctx.lineTo(center, size - 15);
    ctx.stroke();

    // Axis Labels
    ctx.fillStyle = '#64748b';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText('+Q (Quad)', center - 6, 20);
    ctx.textAlign = 'left';
    ctx.fillText('+I (In-Phase)', size - 70, center - 6);

    // Modulation specific ideal reference targets
    const mod = classification?.modulation || 'PSK';
    let idealTargets: Array<{ i: number; q: number }> = [];

    if (mod === 'PSK') {
      // BPSK targets at (-1, 0) and (+1, 0)
      idealTargets = [{ i: -1, q: 0 }, { i: 1, q: 0 }];
    } else if (mod === 'FSK') {
      // FSK phase trajectory circle points
      idealTargets = [{ i: -1, q: 0 }, { i: 1, q: 0 }, { i: 0, q: 1 }, { i: 0, q: -1 }];
    } else if (mod === 'QAM') {
      // 16-QAM grid
      const levels = [-1, -0.333, 0.333, 1];
      for (const iVal of levels) {
        for (const qVal of levels) {
          idealTargets.push({ i: iVal, q: qVal });
        }
      }
    }

    // Draw ideal decision grid boxes / rings
    idealTargets.forEach((target) => {
      const x = center + target.i * scale;
      const y = center - target.q * scale;

      ctx.strokeStyle = 'rgba(0, 255, 136, 0.4)';
      ctx.setLineDash([2, 2]);
      ctx.strokeRect(x - 8, y - 8, 16, 16);
      ctx.setLineDash([]);

      ctx.fillStyle = 'rgba(0, 255, 136, 0.6)';
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
      ctx.fill();
    });

    // Generate constellation points to plot
    const pointsToPlot: Array<{ i: number; q: number }> = [];

    if (samplePoints && samplePoints.i.length > 0) {
      const step = Math.max(1, Math.floor(samplePoints.i.length / 500));
      for (let k = 0; k < samplePoints.i.length; k += step) {
        pointsToPlot.push({
          i: samplePoints.i[k],
          q: samplePoints.q[k] ?? 0,
        });
      }
    } else if (demod?.bits && demod.bits.length > 0) {
      // Synthesize noisy constellation from decoded bits
      demod.bits.slice(0, 400).forEach((bit) => {
        const symbolI = bit === 1 ? 1.0 : -1.0;
        const noiseI = (Math.random() - 0.5) * 0.25;
        const noiseQ = (Math.random() - 0.5) * 0.25;
        pointsToPlot.push({ i: symbolI + noiseI, q: noiseQ });
      });
    } else if (demod?.i_levels && demod.i_levels.length > 0) {
      demod.i_levels.slice(0, 400).forEach((iVal, idx) => {
        const qVal = demod.q_levels?.[idx] ?? 0;
        const noiseI = (Math.random() - 0.5) * 0.15;
        const noiseQ = (Math.random() - 0.5) * 0.15;
        pointsToPlot.push({ i: iVal + noiseI, q: qVal + noiseQ });
      });
    }

    // Plot symbol points
    pointsToPlot.forEach((pt) => {
      const x = center + pt.i * scale;
      const y = center - pt.q * scale;

      ctx.fillStyle = 'rgba(0, 240, 255, 0.7)';
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = 4;
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
      ctx.fill();
      ctx.shadowBlur = 0;
    });

  }, [demod, classification, samplePoints, zoom, persistence]);

  return (
    <div className="flex flex-col bg-[#101522]/95 border border-white/10 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-mono font-bold tracking-wider text-slate-200 uppercase">
            I/Q Constellation Diagram
          </h3>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setZoom((z) => Math.min(2.0, z + 0.2))}
            className="p-1 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/5"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
            className="p-1 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/5"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoom(1.2)}
            className="p-1 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/5 text-[10px] font-mono px-1.5"
            title="Reset Zoom"
          >
            1x
          </button>
        </div>
      </div>

      {/* Canvas container */}
      <div className="flex justify-center items-center relative rounded-lg overflow-hidden border border-white/10 bg-[#0a0e1a]">
        <canvas ref={canvasRef} className="block cursor-pointer" />
      </div>

      {/* Legend & Stats */}
      <div className="flex items-center justify-between mt-3 text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_#00f0ff]" />
            Symbol Clusters
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 border border-emerald-400" />
            Decision Region
          </span>
        </div>
        <span className="text-slate-500 font-semibold">
          Scheme: {classification?.modulation || 'Auto'}
        </span>
      </div>
    </div>
  );
};
