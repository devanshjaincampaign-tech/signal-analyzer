import React, { useState, useRef } from 'react';
import { 
  Upload, 
  X, 
  FileAudio, 
  FileCode, 
  CheckCircle2, 
  AlertCircle, 
  RotateCw,
  Info
} from 'lucide-react';
import { uploadSignalFile } from '../services/api';
import { Job } from '../types/signal';

interface CaptureDropzoneProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (job: Job) => void;
}

export const CaptureDropzone: React.FC<CaptureDropzoneProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [signalFile, setSignalFile] = useState<File | null>(null);
  const [sidecarFile, setSidecarFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const signalInputRef = useRef<HTMLInputElement | null>(null);
  const sidecarInputRef = useRef<HTMLInputElement | null>(null);

  if (!isOpen) return null;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setErrorMessage(null);

    const files = Array.from(e.dataTransfer.files);
    for (const f of files) {
      const name = f.name.toLowerCase();
      if (name.endsWith('.iq') || name.endsWith('.wav')) {
        setSignalFile(f);
      } else if (name.endsWith('.sigmf-meta') || name.endsWith('.json')) {
        setSidecarFile(f);
      }
    }
  };

  const handleUpload = async () => {
    if (!signalFile) {
      setErrorMessage('Please select a .wav or .iq RF signal file to upload');
      return;
    }

    setIsUploading(true);
    setProgress(10);
    setErrorMessage(null);

    try {
      const result = await uploadSignalFile(signalFile, sidecarFile, (pct) => {
        setProgress(pct);
      });

      const newJob: Job = {
        job_id: result.job_id,
        filename: signalFile.name,
        file_type: signalFile.name.split('.').pop() || 'iq',
        status: (result.status as any) || 'validated',
        metadata: {
          file_size_bytes: signalFile.size,
          format: signalFile.name.endsWith('.wav') ? 'WAV Audio' : 'Raw IQ Complex',
        },
      };

      onUploadSuccess(newJob);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload signal capture');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-xl bg-[#101522] border border-cyan-500/30 rounded-2xl p-6 shadow-[0_0_50px_rgba(0,0,0,0.8)]">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-white rounded-lg bg-slate-900 border border-white/5"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Upload className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-mono font-bold text-white uppercase tracking-wider">
              Ingest RF Signal Capture
            </h2>
            <p className="text-xs font-mono text-slate-400">
              Supports raw IQ (.iq) with optional SigMF metadata (.sigmf-meta) or audio WAV (.wav)
            </p>
          </div>
        </div>

        {/* Dropzone Area */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => signalInputRef.current?.click()}
          className={`cursor-pointer flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl transition-all ${
            isDragging
              ? 'border-cyan-400 bg-cyan-500/10 scale-[1.01]'
              : signalFile
              ? 'border-emerald-500/50 bg-emerald-950/10'
              : 'border-white/10 bg-slate-900/60 hover:border-cyan-500/40'
          }`}
        >
          <input
            type="file"
            ref={signalInputRef}
            onChange={(e) => {
              if (e.target.files?.[0]) setSignalFile(e.target.files[0]);
            }}
            accept=".iq,.wav"
            className="hidden"
          />

          {signalFile ? (
            <div className="flex flex-col items-center text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mb-2" />
              <p className="text-sm font-mono font-bold text-white truncate max-w-sm">
                {signalFile.name}
              </p>
              <p className="text-xs font-mono text-slate-400 mt-1">
                {(signalFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for ingestion
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center">
              <FileAudio className="w-10 h-10 text-slate-500 mb-2 group-hover:text-cyan-400 transition-colors" />
              <p className="text-sm font-mono font-semibold text-slate-200">
                Drag & Drop Signal File Here
              </p>
              <p className="text-xs font-mono text-slate-400 mt-1">
                or click to browse from your filesystem (.iq, .wav)
              </p>
            </div>
          )}
        </div>

        {/* Optional SigMF Sidecar upload */}
        <div className="mt-4 p-3 rounded-lg bg-slate-900/60 border border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCode className="w-4 h-4 text-cyan-400" />
            <div>
              <span className="text-xs font-mono font-semibold text-slate-300 block">
                Optional SigMF Sidecar (.sigmf-meta)
              </span>
              <span className="text-[11px] font-mono text-slate-500">
                {sidecarFile ? sidecarFile.name : 'Provides exact center frequency & sample rate metadata'}
              </span>
            </div>
          </div>
          <input
            type="file"
            ref={sidecarInputRef}
            onChange={(e) => {
              if (e.target.files?.[0]) setSidecarFile(e.target.files[0]);
            }}
            accept=".sigmf-meta,.json"
            className="hidden"
          />
          <button
            type="button"
            onClick={() => sidecarInputRef.current?.click()}
            className="px-2.5 py-1 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10"
          >
            {sidecarFile ? 'Change' : 'Select'}
          </button>
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="mt-3 p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Upload Progress Bar */}
        {isUploading && (
          <div className="mt-4 space-y-1">
            <div className="flex justify-between text-xs font-mono text-slate-400">
              <span>Uploading to Storage & Sniffing Header...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-cyan-400 to-blue-500 h-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 mt-6">
          <button
            type="button"
            onClick={onClose}
            disabled={isUploading}
            className="px-4 py-2 text-xs font-mono font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={!signalFile || isUploading}
            className="flex items-center gap-2 px-5 py-2 text-xs font-mono font-bold rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-[0_0_20px_rgba(0,240,255,0.3)] disabled:opacity-50 transition-all"
          >
            {isUploading ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin" />
                <span>Ingesting...</span>
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                <span>Submit Capture</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
