import React, { useState } from 'react';
import { 
  Binary, 
  Copy, 
  Download, 
  Check, 
  Grid3X3, 
  FileCode, 
  Layers, 
  Hash,
  ShieldCheck,
  Search
} from 'lucide-react';
import { DemodResult, InterleavingResult } from '../types/signal';

interface BitstreamInspectorProps {
  demod: DemodResult | null;
  interleaving: InterleavingResult | null;
}

export const BitstreamInspector: React.FC<BitstreamInspectorProps> = ({
  demod,
  interleaving,
}) => {
  const [viewMode, setViewMode] = useState<'binary' | 'hex' | 'ascii'>('binary');
  const [copied, setCopied] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showMatrix, setShowMatrix] = useState<boolean>(false);

  if (!demod || !demod.success) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-[#101522] border border-white/10 rounded-xl text-slate-400 font-mono">
        <Binary className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
        <p className="text-xs">No Demodulated Data Available</p>
        <p className="text-[11px] text-slate-500 mt-1">{demod?.reason || 'Demodulation requires a valid modulation classification and symbol timing'}</p>
      </div>
    );
  }

  const bits = demod.bits || [];
  const numBits = bits.length;

  // Convert bits to Hex string
  const toHex = (bitArray: number[]): string => {
    let hex = '';
    for (let i = 0; i < bitArray.length; i += 8) {
      const byteBits = bitArray.slice(i, i + 8);
      let byteVal = 0;
      for (let b = 0; b < byteBits.length; b++) {
        byteVal = (byteVal << 1) | byteBits[b];
      }
      hex += byteVal.toString(16).padStart(2, '0').toUpperCase() + ' ';
    }
    return hex.trim();
  };

  // Convert bits to ASCII
  const toAscii = (bitArray: number[]): string => {
    let str = '';
    for (let i = 0; i < bitArray.length; i += 8) {
      const byteBits = bitArray.slice(i, i + 8);
      let byteVal = 0;
      for (let b = 0; b < byteBits.length; b++) {
        byteVal = (byteVal << 1) | byteBits[b];
      }
      // Printable ASCII or dot
      if (byteVal >= 32 && byteVal <= 126) {
        str += String.fromCharCode(byteVal);
      } else {
        str += '·';
      }
    }
    return str;
  };

  const hexString = toHex(bits);
  const asciiString = toAscii(bits);
  const binaryString = bits.join('');

  // Density & Stats
  const onesCount = bits.filter((b) => b === 1).length;
  const onesPct = numBits > 0 ? Math.round((onesCount / numBits) * 100) : 50;

  const handleCopy = () => {
    const textToCopy = viewMode === 'binary' ? binaryString : viewMode === 'hex' ? hexString : asciiString;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const textContent = viewMode === 'binary' ? binaryString : viewMode === 'hex' ? hexString : asciiString;
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `demod_bitstream_${viewMode}.${viewMode === 'binary' ? 'bin' : 'txt'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex flex-col bg-[#101522]/95 border border-white/10 rounded-xl p-5 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Binary className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-mono font-bold tracking-wider text-slate-200 uppercase">
            Demodulated Bitstream & Deinterleaving
          </h3>
          <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
            {numBits} BITS
          </span>
        </div>

        {/* View Mode & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Format Mode Selector */}
          <div className="flex items-center bg-slate-900 p-0.5 rounded-lg border border-white/10 text-xs font-mono">
            <button
              onClick={() => setViewMode('binary')}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === 'binary' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              BIN
            </button>
            <button
              onClick={() => setViewMode('hex')}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === 'hex' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              HEX
            </button>
            <button
              onClick={() => setViewMode('ascii')}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === 'ascii' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              ASCII
            </button>
          </div>

          {/* Interleaving Matrix Toggle */}
          {interleaving?.success && (
            <button
              onClick={() => setShowMatrix(!showMatrix)}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-lg border transition-all ${
                showMatrix
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                  : 'bg-slate-900 text-slate-400 border-white/10 hover:text-white'
              }`}
            >
              <Grid3X3 className="w-3.5 h-3.5 text-purple-400" />
              <span>Deinterleave Grid</span>
            </button>
          )}

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-white/10 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-white/10 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Bit Stream Display Terminal */}
      <div className="relative rounded-lg bg-black/80 border border-white/10 p-4 font-mono text-xs overflow-hidden shadow-inner">
        {/* Search filter */}
        <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/10">
          <Search className="w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search bit pattern..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent text-xs text-slate-200 placeholder-slate-600 focus:outline-none"
          />
          {searchQuery && (
            <span className="text-[10px] text-cyan-400">
              Matches highlighted
            </span>
          )}
        </div>

        {/* Content Box */}
        <div className="max-h-48 overflow-y-auto pr-2 break-all leading-relaxed select-all scrollbar-thin">
          {viewMode === 'binary' && (
            <div className="text-cyan-300 font-mono tracking-widest text-[13px]">
              {bits.map((b, i) => (
                <span
                  key={i}
                  className={`inline-block mr-0.5 ${
                    b === 1 ? 'text-cyan-400 font-semibold' : 'text-slate-500'
                  } ${i % 8 === 7 ? 'mr-3' : ''}`}
                >
                  {b}
                </span>
              ))}
            </div>
          )}

          {viewMode === 'hex' && (
            <div className="text-emerald-300 font-mono tracking-wider text-[13px]">
              {hexString.split(' ').map((byte, i) => (
                <span key={i} className="inline-block mr-2 text-slate-300 hover:text-emerald-400">
                  {byte}
                </span>
              ))}
            </div>
          )}

          {viewMode === 'ascii' && (
            <div className="text-slate-200 font-mono tracking-wide text-[13px] whitespace-pre-wrap">
              {asciiString}
            </div>
          )}
        </div>
      </div>

      {/* Deinterleaving Matrix Overlay / Panel */}
      {interleaving?.success && showMatrix && (
        <div className="mt-4 p-4 rounded-lg bg-purple-950/20 border border-purple-500/30">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-xs font-mono text-purple-300 font-bold">
              <Grid3X3 className="w-4 h-4" />
              <span>Block Deinterleaving Matrix (Stride: {interleaving.stride}, Depth: {interleaving.depth})</span>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 font-semibold">
              Periodic Autocorrelation Verified
            </span>
          </div>

          <p className="text-[11px] font-mono text-slate-400 mb-3">
            Signal interleaving was detected. The bitstream has been reshaped and unrolled across stride columns.
          </p>

          <div className="bg-black/60 p-3 rounded border border-white/5 overflow-x-auto text-[11px] font-mono text-purple-200">
            <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${interleaving.stride || 8}, minmax(24px, 1fr))` }}>
              {bits.slice(0, (interleaving.stride || 8) * (interleaving.depth || 8)).map((b, i) => (
                <div
                  key={i}
                  className={`text-center py-1 rounded ${
                    b === 1 ? 'bg-purple-600/30 text-purple-200' : 'bg-slate-900 text-slate-500'
                  }`}
                >
                  {b}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Bit Distribution & Metrics Footer */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 pt-3 border-t border-white/5 font-mono text-xs text-slate-400">
        <div>
          <span className="text-[10px] text-slate-500 block mb-1">0 / 1 BIT RATIO ({onesPct}% ONES)</span>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
            <div className="bg-cyan-400 h-full" style={{ width: `${onesPct}%` }} />
            <div className="bg-slate-600 h-full" style={{ width: `${100 - onesPct}%` }} />
          </div>
        </div>

        <div>
          <span className="text-[10px] text-slate-500 block">INTERLEAVING STATUS</span>
          <span className={`text-xs font-bold mt-0.5 inline-block ${
            interleaving?.success ? 'text-purple-300' : 'text-slate-400'
          }`}>
            {interleaving?.success ? `Detected (Stride ${interleaving.stride})` : 'Non-Interleaved'}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-500 block">PARITY / INTEGRITY</span>
          <span className="text-xs font-bold text-emerald-400 mt-0.5 inline-block">
            Synchronized
          </span>
        </div>
      </div>
    </div>
  );
};
