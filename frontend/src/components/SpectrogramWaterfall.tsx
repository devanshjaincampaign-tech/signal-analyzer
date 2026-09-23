import React, { useEffect, useRef, useState } from 'react';
import { 
  Palette, 
  Sliders, 
  Layers
} from 'lucide-react';
import type { SpectrogramData, ColormapTheme } from '../types/signal';
import { getColormapColor } from '../utils/colormaps';

interface SpectrogramWaterfallProps {
  spectrogram: SpectrogramData | null;
  sampleRate: number;
}

export const SpectrogramWaterfall: React.FC<SpectrogramWaterfallProps> = ({
  spectrogram,
  sampleRate,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [colormap, setColormap] = useState<ColormapTheme>('turbo');
  const [minDb, setMinDb] = useState<number>(-80);
  const [maxDb, setMaxDb] = useState<number>(-10);
  const [hoverData, setHoverData] = useState<{
    freqKhz: number;
    timeSec: number;
    powerDb: number;
    x: number;
    y: number;
  } | null>(null);

  // Compute dynamic stats if spectrogram changes
  useEffect(() => {
    if (!spectrogram || !spectrogram.power_db_matrix.length) return;
    let computedMin = Infinity;
    let computedMax = -Infinity;

    for (const row of spectrogram.power_db_matrix) {
      for (const val of row) {
        if (val < computedMin) computedMin = val;
        if (val > computedMax) computedMax = val;
      }
    }

    if (computedMin !== Infinity && computedMax !== -Infinity) {
      setMinDb(Math.floor(computedMin) - 5);
      setMaxDb(Math.ceil(computedMax) + 2);
    }
  }, [spectrogram]);

  // Render Spectrogram on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !spectrogram || !spectrogram.power_db_matrix.length) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = Math.max(300, canvas.parentElement?.clientWidth || 600);
    const height = 300;
    canvas.width = width;
    canvas.height = height;

    // Clear
    ctx.fillStyle = '#0a0d14';
    ctx.fillRect(0, 0, width, height);

    const matrix = spectrogram.power_db_matrix;
    const nFreqs = matrix.length;
    const nTimes = matrix[0].length;

    const cellW = width / nTimes;
    const cellH = height / nFreqs;
    const range = maxDb - minDb || 1;

    for (let f = 0; f < nFreqs; f++) {
      // Invert frequency axis so highest frequency is at the top of the canvas
      const srcF = nFreqs - 1 - f;
      const row = matrix[srcF];
      const y = f * cellH;

      for (let t = 0; t < nTimes; t++) {
        const val = row[t];
        const normalized = (val - minDb) / range;
        const [r, g, b] = getColormapColor(normalized, colormap);

        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect(
          Math.floor(t * cellW),
          Math.floor(y),
          Math.ceil(cellW) + 1,
          Math.ceil(cellH) + 1
        );
      }
    }
  }, [spectrogram, colormap, minDb, maxDb]);

  // Handle canvas mouse move for interactive coordinate tracking
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!spectrogram || !spectrogram.power_db_matrix.length) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;

    const nFreqs = spectrogram.power_db_matrix.length;
    const nTimes = spectrogram.power_db_matrix[0].length;

    const relX = Math.max(0, Math.min(1, clientX / rect.width));
    const relY = Math.max(0, Math.min(1, clientY / rect.height));

    const tIdx = Math.min(nTimes - 1, Math.floor(relX * nTimes));
    const fIdx = Math.min(nFreqs - 1, Math.floor((1 - relY) * nFreqs));

    const freqHz = spectrogram.freq_bins[fIdx] ?? (-sampleRate / 2 + relY * sampleRate);
    const timeS = spectrogram.time_bins[tIdx] ?? relX * 0.1;
    const power = spectrogram.power_db_matrix[fIdx]?.[tIdx] ?? -50;

    setHoverData({
      freqKhz: freqHz / 1000,
      timeSec: timeS,
      powerDb: power,
      x: clientX,
      y: clientY,
    });
  };

  const handleMouseLeave = () => {
    setHoverData(null);
  };

  if (!spectrogram || !spectrogram.power_db_matrix.length) {
    return (
      <div className="flex flex-col items-center justify-center h-80 bg-[#101522] border border-white/10 rounded-xl text-slate-400 font-mono">
        <Layers className="w-10 h-10 text-slate-600 mb-2 animate-pulse" />
        <p className="text-sm font-semibold">Spectrogram Ready</p>
        <p className="text-xs text-slate-500 mt-1">Upload a capture and run DSP analysis to generate 2D frequency-time waterfall</p>
      </div>
    );
  }

  const freqStartKhz = ((spectrogram.freq_bins[0] ?? -sampleRate / 2) / 1000).toFixed(1);
  const freqEndKhz = ((spectrogram.freq_bins[spectrogram.freq_bins.length - 1] ?? sampleRate / 2) / 1000).toFixed(1);
  const timeEndMs = ((spectrogram.time_bins[spectrogram.time_bins.length - 1] ?? 0.1) * 1000).toFixed(2);

  return (
    <div className="flex flex-col bg-[#101522]/95 border border-white/10 rounded-xl p-4 shadow-xl">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <h3 className="text-sm font-mono font-bold tracking-wider text-slate-200 uppercase">
              2D Spectrogram & Waterfall Heatmap
            </h3>
          </div>
          <p className="text-xs font-mono text-slate-400 mt-0.5">
            Time vs. Frequency Energy Distribution ($S_{'{xx}'}$ in dB)
          </p>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Colormap Selector */}
          <div className="flex items-center gap-1.5 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-white/5 text-xs font-mono">
            <Palette className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Palette:</span>
            <select
              value={colormap}
              onChange={(e) => setColormap(e.target.value as ColormapTheme)}
              className="bg-transparent text-cyan-300 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="turbo" className="bg-slate-900 text-slate-200">Turbo</option>
              <option value="viridis" className="bg-slate-900 text-slate-200">Viridis</option>
              <option value="inferno" className="bg-slate-900 text-slate-200">Inferno</option>
              <option value="plasma" className="bg-slate-900 text-slate-200">Plasma</option>
              <option value="matrix" className="bg-slate-900 text-slate-200">Matrix Green</option>
              <option value="cyan" className="bg-slate-900 text-slate-200">Electric Cyan</option>
            </select>
          </div>

          {/* Dynamic Range dB Slider */}
          <div className="flex items-center gap-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-white/5 text-xs font-mono text-slate-400">
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span>Range:</span>
            <input
              type="range"
              min="-120"
              max="-30"
              value={minDb}
              onChange={(e) => setMinDb(Number(e.target.value))}
              className="w-16 accent-cyan-400 cursor-pointer h-1 bg-slate-700 rounded-lg"
              title={`Min dB Threshold: ${minDb} dB`}
            />
            <span className="text-cyan-300 w-10">{minDb} dB</span>
          </div>
        </div>
      </div>

      {/* Main Spectrogram Area */}
      <div className="relative flex gap-2 w-full" ref={containerRef}>
        {/* Y-Axis (Frequency) Label */}
        <div className="flex flex-col justify-between py-2 text-[10px] font-mono text-slate-400 text-right w-16 select-none">
          <span>{freqEndKhz} kHz</span>
          <span className="text-slate-500 font-bold">0.0 kHz</span>
          <span>{freqStartKhz} kHz</span>
        </div>

        {/* Heatmap Canvas Container */}
        <div className="relative flex-1 bg-black rounded-lg overflow-hidden border border-white/10 shadow-inner group">
          <canvas
            ref={canvasRef}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="w-full h-72 sm:h-80 block cursor-crosshair"
          />

          {/* Interactive Cursor crosshair overlay */}
          {hoverData && (
            <>
              <div
                className="absolute top-0 bottom-0 w-[1px] bg-cyan-400/80 pointer-events-none"
                style={{ left: `${hoverData.x}px` }}
              />
              <div
                className="absolute left-0 right-0 h-[1px] bg-cyan-400/80 pointer-events-none"
                style={{ top: `${hoverData.y}px` }}
              />
              <div
                className="absolute pointer-events-none px-2 py-1 rounded bg-slate-900/90 border border-cyan-500/40 text-[10px] font-mono text-cyan-200 shadow-xl"
                style={{
                  left: Math.min(hoverData.x + 12, (containerRef.current?.clientWidth || 400) - 180),
                  top: Math.max(10, hoverData.y - 45),
                }}
              >
                <div>Freq: <span className="font-bold text-white">{hoverData.freqKhz.toFixed(2)} kHz</span></div>
                <div>Time: <span className="font-bold text-white">{(hoverData.timeSec * 1000).toFixed(2)} ms</span></div>
                <div>Power: <span className="font-bold text-cyan-400">{hoverData.powerDb.toFixed(1)} dB</span></div>
              </div>
            </>
          )}

          {/* Center Zero Frequency Reference Line */}
          <div className="absolute top-1/2 left-0 right-0 border-t border-dashed border-white/20 pointer-events-none" />
        </div>

        {/* Colorbar Scale on Right */}
        <div className="flex flex-col items-center justify-between py-2 text-[10px] font-mono text-slate-400 w-10 select-none">
          <span className="text-cyan-300">{maxDb} dB</span>
          <div
            className="w-3 flex-1 my-1 rounded-sm border border-white/10"
            style={{
              background: colormap === 'turbo' 
                ? 'linear-gradient(to top, #30123b, #4686fb, #1be5b5, #a4fc3c, #fbb938, #e34422)'
                : colormap === 'viridis'
                ? 'linear-gradient(to top, #440154, #3b528b, #21918c, #5ec962, #fde725)'
                : colormap === 'inferno'
                ? 'linear-gradient(to top, #000004, #57106e, #bb3754, #f98e09, #fcffa4)'
                : 'linear-gradient(to top, #0d121f, #00f0ff)',
            }}
          />
          <span>{minDb} dB</span>
        </div>
      </div>

      {/* X-Axis (Time) Label */}
      <div className="flex justify-between pl-16 pr-12 mt-1.5 text-[10px] font-mono text-slate-400 select-none">
        <span>0.0 ms</span>
        <span className="text-slate-500 font-semibold tracking-wider uppercase">Time (Duration: {timeEndMs} ms)</span>
        <span>{timeEndMs} ms</span>
      </div>
    </div>
  );
};
